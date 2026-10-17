"""Keep physical sections separate from qualified default-closed enclosure carriers."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback

from shapely.geometry import GeometryCollection, LineString, Polygon, mapping, shape
from shapely.ops import linemerge, unary_union

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from features.geometry_views import component_shape, plan_projection
from scripts.design.space_field import run_boundary_height_view as boundary
from scripts.design.space_field import run_floor_plan_3d_comparison as sections

BUDGET = 1e-6


def source_extent(row):
    """Project actual source faces or collapsed edges without a solid prerequisite."""
    projection = plan_projection(row["patch"])
    geometry = component_shape(projection.components)
    if geometry is None:
        # Vertical surface triangles can collapse to lines, which still carry
        # a meaningful planar span. No bbox or ordered-vertex hull is created.
        edges = []
        for triangle in row["patch"].triangle_indices:
            points = [row["patch"].vertices[index][:2] for index in triangle]
            for first, second in zip(points, points[1:] + points[:1]):
                if first != second:
                    edges.append(LineString([first, second]))
        geometry = unary_union(edges)
        method = "actual_projected_triangle_edges_for_collapsed_surface"
    else:
        method = "actual_projected_triangle_face_union"
    return geometry, method


def line_parts(geometry):
    """Merge connected contact segments so one tessellated jamb stays one side."""
    pending, lines = [geometry], []
    while pending:
        part = pending.pop()
        if part.geom_type in {"LineString", "LinearRing"} and part.length > 0:
            lines.append(LineString(part.coords))
        else:
            pending.extend(getattr(part, "geoms", ()))
    if not lines:
        return []
    merged = linemerge(lines)
    parts = [merged] if merged.geom_type == "LineString" else list(merged.geoms)
    return sorted(parts, key=lambda item: (item.bounds, item.wkb_hex))


def locate_apertures(rows, records):
    """Localize host projection-minus-cut residuals without filling them as walls."""
    sources = {row["id"]: row for row in rows}
    apertures, host_projections = [], []
    for record in records:
        if record["source_class"] != "IfcWall":
            continue
        footprint, method = source_extent(sources[record["id"]])
        cut = shape(record["section"]["geometry"]["geojson"])
        host_projections.append({"source_ref": record["id"], "geometry": sections.geometry_report(footprint),
                                 "method": method, "enclosure_input": False})
        if not record["eligibility"]["usable_section_for_support"]:
            continue
        # The full host projection is ONLY an aperture locator. Each individual
        # residual needs door/window evidence before becoming scenario carrier.
        residual = footprint.difference(cut)
        for component in boundary.polygon_parts(residual):
            jambs = line_parts(component.boundary.intersection(cut.boundary))
            apertures.append({"id": f"A{len(apertures) + 1}", "host_ref": record["id"],
                              "geometry": sections.geometry_report(component),
                              "jamb_sides": [mapping(jamb) for jamb in jambs],
                              "jamb_lengths_m": [jamb.length for jamb in jambs],
                              "status": "localized_projection_minus_cut_residual_not_yet_semantic_opening",
                              "within_one_source": True,
                              "above_comparison_area_budget": component.area > BUDGET,
                              "method": "actual_host_face_projection_minus_exact_material_section"})
    return apertures, host_projections


def associate_spans(rows, records, apertures, snapshot):
    """Qualify unique source-span/host-aperture mappings independently of mass."""
    sources = {row["id"]: row for row in rows}
    originals = {row["id"]: row for row in snapshot.get("objects", [])}
    treatments, carriers = [], []
    for record in records:
        if record["source_class"] not in {"IfcWindow", "IfcDoor"}:
            continue
        extent, method = source_extent(sources[record["id"]])
        authored = (record.get("identity") or {}).get("authored_host_object_ids", [])
        alternatives = []
        for aperture in apertures:
            geometry = shape(aperture["geometry"]["geojson"])
            overlap = extent.intersection(geometry)
            if overlap.is_empty:
                continue
            contacts = []
            for index, jamb in enumerate(aperture["jamb_sides"]):
                side = shape(jamb)
                contact = extent.intersection(side)
                distance = extent.distance(side)
                contacts.append({"jamb_index": index, "geometry": mapping(contact),
                                 "contact_length_m": contact.length, "intersects": not contact.is_empty,
                                 "source_extent_distance_m": distance,
                                 "span_meets_fixed_comparison_budget": distance <= BUDGET})
            # The frozen metre comparison budget qualifies a measured span;
            # neither source coordinates nor the exact host-derived carrier is
            # widened, snapped or buffered to make contact. Save exact failure.
            touched = [index for index, contact in enumerate(contacts) if contact["span_meets_fixed_comparison_budget"]]
            # Connected line merging prevents counting two triangles on one
            # jamb as both sides. Separate positive-length jambs must bound a
            # positive-area aperture, and actual extent must reach both sides.
            qualified = (geometry.is_valid and aperture["above_comparison_area_budget"]
                         and len(touched) >= 2 and all(aperture["jamb_lengths_m"][index] > BUDGET for index in touched)
                         and (not authored or aperture["host_ref"] in authored))
            alternatives.append({"aperture_ref": aperture["id"], "host_ref": aperture["host_ref"],
                                 "overlap_geometry": mapping(overlap), "overlap_area_m2": overlap.area,
                                 "overlap_length_m": overlap.length, "jamb_contacts": contacts,
                                 "distinct_jamb_sides_reached": len(touched),
                                 "exact_jamb_intersections": sum(contact["intersects"] for contact in contacts),
                                 "qualification_budget_m": BUDGET, "source_or_carrier_coordinates_changed": False,
                                 "qualified": qualified})
        qualified = [alternative for alternative in alternatives if alternative["qualified"]]
        association = "authored" if authored and len(qualified) == 1 else "inferred" if len(qualified) == 1 else "ambiguous" if len(qualified) > 1 else "missing"
        chosen = qualified[0] if len(qualified) == 1 else None
        reason = None if chosen else "multiple_qualified_host_aperture_alternatives" if qualified else "no_unique_extent_reaching_distinct_host_jambs"
        if chosen:
            aperture = next(aperture for aperture in apertures if aperture["id"] == chosen["aperture_ref"])
            carriers.append({"id": f"closed:{record['id']}", "source_ref": record["id"], "host_ref": chosen["host_ref"],
                             "aperture_ref": chosen["aperture_ref"], "geometry": aperture["geometry"],
                             "association": association, "scenario": "authorized_default_closed_not_observed",
                             "physical_mass_added": False})
        properties = originals.get(record["id"], {}).get("factual_properties", {})
        treatments.append({"source_ref": record["id"], "source_class": record["source_class"],
                           "identity": record.get("identity"), "authored_properties_unchanged": properties,
                           "host_mapping": association, "authored_host_refs": authored, "alternatives": alternatives,
                           "selected_aperture_ref": chosen["aperture_ref"] if chosen else None,
                           "extent_source": method, "actual_visible_source_extent": sections.geometry_report(extent),
                           "source_mesh_qualification": record["qualification"],
                           "old_material_section_status": record["section"]["status"],
                           "old_material_section_area_m2": record["section"]["geometry"]["area_m2"],
                           "old_enclosure_treatment": "not_structural_support; no_qualified_scenario_carrier",
                           "closed_scenario_assumption": True, "observed_state": None,
                           "semantic_contribution": "qualified_local_aperture_carrier" if chosen else "unresolved_no_carrier",
                           "refusal_reason": reason, "physical_occupancy_changed": False,
                           "scenario_eligibility": "task_specific_authorized_enclosure_not_generic_analysis_participation",
                           "affected_scope_ids": [], "affected_contour_ids": []})
    sealed = {carrier["aperture_ref"] for carrier in carriers}
    for aperture in apertures:
        refs = [treatment["source_ref"] for treatment in treatments if any(alternative["aperture_ref"] == aperture["id"] for alternative in treatment["alternatives"])]
        aperture.update({"related_source_refs": refs, "scenario_closed": aperture["id"] in sealed,
                         "semantic_status": "qualified_default_closed_scenario" if aperture["id"] in sealed else "unresolved_or_unfilled_no_carrier",
                         "affected_scope_ids": [], "affected_contour_ids": []})
    return treatments, carriers


def semantic_candidate_assembly(records, treatments, carriers, apertures):
    """Reuse exact candidate assembly with private carrier inputs, preserving sources."""
    physical_bytes = json.dumps(records, sort_keys=True)
    carrier_inputs = []
    for record in records:
        additions = [shape(carrier["geometry"]["geojson"]) for carrier in carriers if carrier["host_ref"] == record["id"]]
        if additions:
            carrier_geometry = unary_union([shape(record["section"]["geometry"]["geojson"]), *additions])
            # This geometry-only assembly copy is a semantic carrier, NOT an
            # altered factual material section or physical-occupancy record.
            carrier_inputs.append(record | {"section": record["section"] | {"geometry": sections.geometry_report(carrier_geometry)}})
        else:
            carrier_inputs.append(record)
    result = boundary.infer_candidates(carrier_inputs, [])
    result["method"] = "qualified_semantic_carrier_reuses_exact_component_ring_assembly/v1"
    result["enclosure_carrier"] = result.pop("eligible_mass_union")
    result["carrier_source_observations"] = result.pop("source_observations")
    result["carrier_source_contact_graph"] = result.pop("eligible_source_contact_graph")
    result["counts"]["assembly_source_records"] = result["counts"].pop("physical_source_records")
    result["counts"]["structural_carrier_inputs"] = result["counts"].pop("usable_boundary_sections")
    for observation in result["carrier_source_observations"]:
        observation.pop("physical_occupancy_retained")
        observation["carrier_contour_contribution"] = observation.pop("demonstrated_contour_contribution")
        observation["no_carrier_contour_contribution"] = observation.pop("occupancy_only_in_this_boundary_run")
    result["scenario_evidence"] = carriers
    for scope in result["scope_proposals"]:
        scope["supporting_carrier"] = scope.pop("supporting_mass")
        scope["support_carrier_outside_scope_area_m2"] = scope.pop("support_mass_outside_scope_area_m2")
        scope["semantic_completeness"] = "conditional_scenario_with_local_and_global_unresolved_dependencies"
        scope["construction"] = "actual_semantic_carrier_component_exterior_with_bounded_holes_filled_after_qualified_closure"
        scope["carrier_source_connectedness"] = scope.pop("source_connectedness")
        scope.pop("local_unresolved_doors")
        scope["carrier_presence_source_refs"] = []
        scope["semantic_contribution_refs"] = []
        scope["local_unresolved_aperture_refs"] = []
        extent = shape(scope["geometry"]["geojson"])
        for aperture in apertures:
            if not extent.intersection(shape(aperture["geometry"]["geojson"])).is_empty:
                aperture["affected_scope_ids"].append(scope["id"])
                if not aperture["scenario_closed"] and aperture["above_comparison_area_budget"]:
                    scope["local_unresolved_aperture_refs"].append(aperture["id"])
        for carrier in carriers:
            if extent.intersection(shape(carrier["geometry"]["geojson"])).area > 0:
                scope["carrier_presence_source_refs"].append(carrier["source_ref"])
    for contour in result["enclosure_contours"]:
        line = shape(contour["geometry"]["geojson"]).boundary
        contour["semantic_contribution_refs"] = [carrier["source_ref"] for carrier in carriers
                                                  if line.intersection(shape(carrier["geometry"]["geojson"]).boundary).length > 0]
        for aperture in apertures:
            if not line.intersection(shape(aperture["geometry"]["geojson"])).is_empty:
                aperture["affected_contour_ids"].append(contour["id"])
    for treatment in treatments:
        treatment["affected_contour_ids"] = [contour["id"] for contour in result["enclosure_contours"] if treatment["source_ref"] in contour["semantic_contribution_refs"]]
        treatment["demonstrated_semantic_contour_support"] = bool(treatment["affected_contour_ids"])
        treatment["affected_scope_ids"] = sorted({contour["scope_ref"] for contour in result["enclosure_contours"]
                                                  if contour["id"] in treatment["affected_contour_ids"]})
        if not treatment["affected_scope_ids"]:
            related = [aperture for aperture in apertures if treatment["source_ref"] in aperture["related_source_refs"]]
            treatment["affected_scope_ids"] = sorted({ref for aperture in related for ref in aperture["affected_scope_ids"]})
            treatment["affected_contour_ids"] = sorted({ref for aperture in related for ref in aperture["affected_contour_ids"]})
    for scope in result["scope_proposals"]:
        scope["semantic_contribution_refs"] = sorted({ref for contour in result["enclosure_contours"]
                                                      if contour["scope_ref"] == scope["id"] for ref in contour["semantic_contribution_refs"]})
        scope["local_door_window_treatment_refs"] = [treatment["source_ref"] for treatment in treatments
                                                     if scope["id"] in treatment["affected_scope_ids"]]
    assert json.dumps(records, sort_keys=True) == physical_bytes
    result["physical_source_sections_unchanged"] = True
    result["unattributed_unresolved_sources"] = [treatment["source_ref"] for treatment in treatments
                                                if treatment["refusal_reason"] and not treatment["affected_scope_ids"]]
    result["global_limits"] = ["unknown_authored_floor_datum", "disk_live_geometry_parity_unverified",
                               "default_closed_scenario_not_observed_state", "apertures_are_host_projection_residuals_not_authored_openings",
                               "source_geometry_capture_changes_disclosed_separately", "no_active_domain_or_free_space_or_routes"]
    return result


def control_rows():
    """Reuse box dimensions with a single multipart host and no-cut window surface."""
    definition = sections.fixture_definitions()[0]
    rows = boundary.synthetic_rows(definition)
    south = [row for row in rows if row["id"] in {"south_left", "south_right"}]
    lintel = boundary.synthetic_rows({"boxes": [["lintel", "wall", [2.75, 0, 2.1, 3.25, .25, 3]]]})[0]
    import trimesh
    from features.geometry_substitutes import mass_patch_from_mesh
    from features.scene_contract import MeshGeometry3D
    mesh = trimesh.util.concatenate([row["mesh"] for row in [*south, lintel]])
    geometry = MeshGeometry3D(id="host", vertices=tuple(map(tuple, mesh.vertices)), triangle_indices=tuple(tuple(int(index) for index in triangle) for triangle in mesh.faces),
                              is_closed=True, is_manifold=True, units="m", normals=(),
                              local_to_world_provenance={"method": "synthetic_exact_dimension_parts"},
                              source_representation_id="host", tessellation_settings={})
    patch = mass_patch_from_mesh(geometry)
    host = {"id": "host", "role": "wall", "synthetic_class": "IfcWall", "patch": patch, "mesh": mesh,
            "qualification": sections.qualify(patch, mesh)}
    vertices = ((2.75, .1, 2.2), (3.25, .1, 2.2), (3.25, .15, 2.2), (2.75, .15, 2.2))
    surface = MeshGeometry3D(id="window", vertices=vertices, triangle_indices=((0, 1, 2), (0, 2, 3)),
                             is_closed=False, is_manifold=False, units="m", normals=(),
                             local_to_world_provenance={"method": "synthetic_nonwatertight_window_surface_above_cut"},
                             source_representation_id="window", tessellation_settings={})
    window_patch = mass_patch_from_mesh(surface)
    window_mesh = trimesh.Trimesh(vertices, surface.triangle_indices, process=False)
    window = {"id": "window", "role": "window", "synthetic_class": "IfcWindow", "patch": window_patch,
              "mesh": window_mesh, "qualification": sections.qualify(window_patch, window_mesh)}
    return [row for row in rows if row["id"] not in {"south_left", "south_right", "boundary_column"}] + [host, window]


def controls(out):
    """Pin only semantic no-cut-window, unfilled-opening and ambiguity behavior."""
    sections.write_json(out / "control_oracles_before_queries.json", {
        "window_source": "window", "unique_host": "host", "material_contours": 0,
        "semantic_contours": 1, "semantic_scopes": 1, "scope_area_m2": 24,
        "true_unfilled_contours": 0, "ambiguous_contours": 0,
        "window_cut_material_area_m2": 0, "window_watertight": False})
    outcomes = {}
    original = control_rows()
    for case in ("qualified_window", "true_unfilled", "ambiguous_host"):
        rows = [row for row in original if case != "true_unfilled" or row["id"] != "window"]
        if case == "ambiguous_host":
            rows.append(next(row for row in rows if row["id"] == "host") | {"id": "duplicate_host"})
        records = boundary.section_sources(rows, 1.5)
        apertures, projections = locate_apertures(rows, records)
        treatments, carriers = associate_spans(rows, records, apertures, {})
        material = boundary.infer_candidates(records, [])
        semantic = semantic_candidate_assembly(records, treatments, carriers, apertures)
        assert material["counts"]["enclosure_contours"] == 0
        assert semantic["counts"]["enclosure_contours"] == (1 if case == "qualified_window" else 0)
        if case == "qualified_window":
            assert carriers[0]["source_ref"] == "window" and carriers[0]["host_ref"] == "host"
            assert treatments[0]["old_material_section_area_m2"] == 0
            assert not treatments[0]["source_mesh_qualification"]["trimesh_watertight"]
            assert abs(semantic["scope_proposals"][0]["geometry"]["area_m2"] - 24) <= BUDGET
        elif case == "ambiguous_host":
            assert not carriers and treatments[0]["host_mapping"] == "ambiguous"
        else:
            assert not treatments and not carriers and any(not aperture["scenario_closed"] for aperture in apertures)
        outcomes[case] = {"physical_sections": records, "apertures": apertures, "treatments": treatments,
                          "carriers": carriers, "material_result": material, "semantic_result": semantic}
    sections.write_json(out / "controls.json", {"passed": True, "cases": outcomes})


def outline(ax, geometry, color, style="-", width=1):
    """Render actual polygon boundaries or source line spans without an envelope."""
    pending = [geometry]
    while pending:
        part = pending.pop()
        if part.geom_type == "Polygon":
            pending.extend([part.exterior, *part.interiors])
        elif part.geom_type in {"LineString", "LinearRing"}:
            x, y = part.xy
            ax.plot(x, y, color=color, linestyle=style, linewidth=width)
        else:
            pending.extend(getattr(part, "geoms", ()))


def render(records, treatments, carriers, apertures, material, semantic, out, height):
    """Show material cuts, real window spans and separate semantic scenario closures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    fig = plt.figure(figsize=(19, 10))
    grid = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.15, 1])
    axes = [fig.add_subplot(grid[0, index]) for index in (0, 1)]
    table = fig.add_subplot(grid[0, 2])
    table.axis("off")
    for record in records:
        cls = record["source_class"]
        color = "#326aa1" if cls == "IfcWall" else "#d9b68a" if cls == "IfcColumn" else "#388e71" if cls == "IfcDoor" else "#23a9c1"
        geometry = shape(record["section"]["geometry"]["geojson"])
        for ax in axes:
            sections.plot_polygon(ax, geometry, color)
            if record["section"]["status"] != "qualified_section":
                for line in record["section"]["contour_segments_xyz"]:
                    ax.plot([point[0] for point in line], [point[1] for point in line], color=color, linewidth=.5)
    windows = [treatment for treatment in treatments if treatment["source_class"] == "IfcWindow"]
    doors = [treatment for treatment in treatments if treatment["source_class"] == "IfcDoor"]
    labels = {treatment["source_ref"]: f"W{index}" for index, treatment in enumerate(windows, 1)}
    labels.update({treatment["source_ref"]: f"D{index}" for index, treatment in enumerate(doors, 1)})
    for treatment in treatments:
        extent = shape(treatment["actual_visible_source_extent"]["geojson"])
        color = "#008ba8" if treatment["source_class"] == "IfcWindow" else "#287957"
        if extent.is_empty:
            continue
        center = extent.representative_point()
        for ax in axes:
            outline(ax, extent, color, ":", 1.5)
            ax.annotate(labels[treatment["source_ref"]], (center.x, center.y), xytext=(0, 10),
                        textcoords="offset points", ha="center", fontsize=9, color=color)
    for aperture in apertures:
        geometry = shape(aperture["geometry"]["geojson"])
        if aperture["above_comparison_area_budget"]:
            outline(axes[0], geometry, "#d44c43", "--", 1)
            if not aperture["scenario_closed"]:
                outline(axes[1], geometry, "#d44c43", "--", 1)
                center = geometry.representative_point()
                axes[1].text(center.x, center.y, aperture["id"], color="#a52721", fontsize=8)
    for carrier in carriers:
        geometry = shape(carrier["geometry"]["geojson"])
        sections.plot_polygon(axes[1], geometry, "#cf62af")
        outline(axes[1], geometry, "#be278c", "--", 1.7)
    for scope in semantic["scope_proposals"]:
        geometry = shape(scope["geometry"]["geojson"])
        outline(axes[1], geometry, "#7b3db1", "--", 1.6)
        center = geometry.representative_point()
        axes[1].annotate(scope["id"], (center.x, center.y), xytext=(0, -18), textcoords="offset points",
                         ha="center", fontsize=11, color="#7b3db1")
    for contour in semantic["enclosure_contours"]:
        geometry = shape(contour["geometry"]["geojson"])
        outline(axes[1], geometry, "#8b357c", ":", 1)
        center = geometry.representative_point()
        axes[1].text(center.x, center.y, contour["id"], ha="center", fontsize=10, color="#8b357c")
    structural = [shape(record["section"]["geometry"]["geojson"]) for record in records
                  if record["eligibility"]["usable_section_for_support"]]
    extent = unary_union(structural).bounds
    for ax, title in zip(axes, ("Same-cohort physical material at cut", "Default-closed semantic carrier / provisional scopes")):
        ax.set_xlim(extent[0] - 1, extent[2] + 1)
        ax.set_ylim(extent[1] - 1, extent[3] + 1)
        ax.set_aspect("equal")
        ax.grid(alpha=.15)
        ax.set_xlabel("World x (m)")
        ax.set_ylabel("World y (m)")
        ax.set_title(title, fontsize=11)
    lines = ["SAME COHERENT 38-SOURCE COHORT", "11 walls / 16 columns / 6 doors / 5 windows", "",
             f"Material: {material['counts']['enclosure_contours']} contours / {material['counts']['compound_scope_proposals']} scopes",
             f"Semantic: {semantic['counts']['enclosure_contours']} contours / {semantic['counts']['compound_scope_proposals']} scopes",
             f"Qualified scenario carriers: {len(carriers)}", "", "Source → association / aperture / scopes"]
    for treatment in windows + doors:
        scopes = ",".join(treatment["affected_scope_ids"]) or "none"
        lines.append(f"{labels[treatment['source_ref']]} #{treatment['identity']['step_id']}: {treatment['host_mapping']}")
        lines.append(f"  {treatment['selected_aperture_ref'] or 'unresolved'}; scopes {scopes}")
    unresolved = [aperture for aperture in apertures if not aperture["scenario_closed"] and aperture["above_comparison_area_budget"]]
    lines += ["", f"Unsealed residual apertures: {len(unresolved)}", "Window AnalysisParticipation=exclude", "preserved; enclosure scenario authorized.",
              "", "World z0 datum ASSUMED; cut localization", f"at {height:g} m; semantic spans height-independent.",
              "Disk/live shape parity UNVERIFIED.", "Carrier ≠ physical wall/glass mass.", "Unknown/true openings stay unresolved/open.",
              "No accepted domain / free-space / route."]
    table.text(0, 1, "\n".join(lines), va="top", fontsize=9)
    fig.suptitle("Semantic enclosure repair: real windows and doors under an authorized closed scenario\n"
                 "Fresh coherent source capture; source state unknown; physical sectional occupancy preserved", fontsize=14)
    fig.legend(handles=[Patch(color="#326aa1", label="Physical wall cut"), Patch(color="#d9b68a", label="Physical column cut"),
                        Line2D([], [], color="#008ba8", linestyle=":", label="Actual projected window surface/span"),
                        Line2D([], [], color="#287957", linestyle=":", label="Actual projected door surface/span"),
                        Line2D([], [], color="#be278c", linestyle="--", label="Qualified scenario closure; no added mass"),
                        Line2D([], [], color="#d44c43", linestyle="--", label="Localized residual / unsealed aperture"),
                        Line2D([], [], color="#7b3db1", linestyle="--", label="Provisional compound scope exterior")],
               loc="lower center", ncol=3, fontsize=10)
    fig.subplots_adjust(top=.85, bottom=.18, wspace=.25)
    fig.savefig(out / "real_semantic_enclosure.png", dpi=150)
    plt.close(fig)


def run(args):
    """Execute frozen source/association rules and compare the same physical cohort."""
    out = args.output_dir
    contract_dir = args.contract.parent
    decisions = {name: sections.fingerprint(contract_dir / name) for name in
                 ("association_ruling.json", "window_eligibility_ruling.json", "cohort_decision.json")}
    cohort = json.loads((contract_dir / "cohort_decision.json").read_bytes())
    snapshot_fp = sections.fingerprint(args.snapshot)
    assert snapshot_fp["sha256"] == "96f40383297fdebb12ed7a26ef9dac38188ed05fcfa7def43c202fceaeb3daad" and snapshot_fp["bytes"] == 5692042
    snapshot = json.loads(args.snapshot.read_bytes())
    helpers = {str(path): sections.fingerprint(ROOT / path) for path in
               ("scripts/design/space_field/run_boundary_height_view.py", "scripts/design/space_field/run_floor_plan_3d_comparison.py",
                "features/geometry_views.py", "features/geometry_substitutes.py", "adapters/blender_geometry.py")}
    old_snapshot = json.loads((ROOT / "outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json").read_bytes())
    current = {record["id"]: record for record in snapshot["objects"]}
    identical_fields = ("vertices", "triangles", "world_transform", "units", "transform_applied")
    assert all(all(current[record["id"]][field] == record[field] for field in identical_fields) for record in old_snapshot["objects"])
    provenance = {"snapshot": snapshot_fp, "contract": sections.fingerprint(args.contract), "decisions": decisions,
                  "runner": sections.fingerprint(__file__), "helpers": helpers, "cohort_decision": cohort,
                  "datum_world_z_m": args.datum, "material_localization_height_relative_m": args.cut_height,
                  "section_world_z_m": args.datum + args.cut_height, "plane": "world XY", "units": "m",
                  "datum_status": "experiment_assumption_not_authored_floor", "semantic_height": "source_span_not_cut_material",
                  "historical_comparison": {"old_sources": 33, "new_sources": 38, "old_geometry_equal_fields": identical_fields,
                                            "all_33_identical": True, "added_window_sources": 5,
                                            "disk_live_shape_parity": "not_established"},
                  "source_identity": snapshot["identity"], "gap_repair": "none", "scenario": "default_closed_doors_and_windows_not_observed"}
    sections.write_json(out / "provenance.json", provenance)
    (out / "contract_snapshot.md").write_bytes(args.contract.read_bytes())
    for name in decisions:
        (out / name).write_bytes((contract_dir / name).read_bytes())
    controls(out)
    assert len(snapshot["objects"]) == 38 and all(record["vertices"] and record["triangles"] for record in snapshot["objects"])
    rows = sections.normalize(snapshot)
    assert len(rows) == 38 and {row["id"] for row in rows} == set(current)
    records = boundary.section_sources(rows, args.datum + args.cut_height)
    assert Counter(record["source_class"] for record in records) == {"IfcWall": 11, "IfcColumn": 16, "IfcDoor": 6, "IfcWindow": 5}
    material = boundary.infer_candidates(records, [])
    apertures, host_projections = locate_apertures(rows, records)
    treatments, carriers = associate_spans(rows, records, apertures, snapshot)
    semantic = semantic_candidate_assembly(records, treatments, carriers, apertures)
    physical = unary_union([shape(record["section"]["geometry"]["geojson"]) for record in records])
    sections.write_json(out / "source_sections.json", records)
    sections.write_json(out / "physical_occupancy.json", {"source_refs": [record["id"] for record in records],
                        "qualified_section_mass_union": sections.geometry_report(physical), "sources_retained": 38,
                        "semantic_carrier_added": False, "unqualified_source_contours_in": "source_sections.json"})
    sections.write_json(out / "material_result.json", material)
    sections.write_json(out / "host_projection_aperture_locator.json", host_projections)
    sections.write_json(out / "apertures.json", apertures)
    sections.write_json(out / "opening_treatment_table.json", {"sources": treatments, "residual_apertures": apertures,
                        "unknown_true_unfilled_distinction": "no_authoritative_opening_semantics_for_unassociated_residuals; never_sealed"})
    sections.write_json(out / "semantic_carriers.json", carriers)
    sections.write_json(out / "semantic_result.json", semantic)
    render(records, treatments, carriers, apertures, material, semantic, out, args.datum + args.cut_height)
    checks = {"analytic_controls": "passed", "physical_sources_retained": 38, "source_sections_unchanged": True,
              "material_counts": material["counts"], "semantic_counts": semantic["counts"],
              "window_treatments": len([treatment for treatment in treatments if treatment["source_class"] == "IfcWindow"]),
              "door_treatments": len([treatment for treatment in treatments if treatment["source_class"] == "IfcDoor"]),
              "carriers": len(carriers), "provisional_only": True}
    if args.reproduce_of:
        files = ("source_sections.json", "physical_occupancy.json", "material_result.json", "host_projection_aperture_locator.json",
                 "apertures.json", "opening_treatment_table.json", "semantic_carriers.json", "semantic_result.json",
                 "controls.json", "control_oracles_before_queries.json", "provenance.json", "contract_snapshot.md",
                 "association_ruling.json", "window_eligibility_ruling.json", "cohort_decision.json", "real_semantic_enclosure.png", "runner_snapshot.py")
        assert all((out / name).read_bytes() == (args.reproduce_of / name).read_bytes() for name in files)
        checks["separate_process_byte_identical_files"] = files
    sections.write_json(out / "checks.json", checks)
    print(json.dumps(checks), flush=True)


def main():
    """Refuse overwrites and bound only the current diagnostic worker process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--datum", type=float, default=0)
    parser.add_argument("--cut-height", type=float, default=1.5)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reproduce-of", type=Path)
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not all(math.isfinite(value) for value in (args.datum, args.cut_height)):
        parser.error("finite datum and cut-height required")
    if not args.controls_only and (args.snapshot is None or args.contract is None):
        parser.error("real inference needs frozen snapshot and execution contract")
    if args.worker:
        try:
            controls(args.output_dir) if args.controls_only else run(args)
        except Exception:
            (args.output_dir / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "runner_snapshot.py").write_bytes(Path(__file__).read_bytes())
    command = [sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:], "--worker"]
    tick, started = time.perf_counter(), datetime.now(timezone.utc).isoformat()
    timed_out = False
    with (args.output_dir / "stdout.log").open("wb") as stdout, (args.output_dir / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait()
    sections.write_json(args.output_dir / "execution.json", {"parent_argv": sys.argv, "worker_argv": command,
                        "worker_pid": process.pid, "worker_exit_code": code, "timed_out": timed_out,
                        "started_utc": started, "ended_utc": datetime.now(timezone.utc).isoformat(),
                        "elapsed_seconds": time.perf_counter() - tick, "budget_seconds": 120})
    sections.write_json(args.output_dir / "manifest.json", {"artifacts": [sections.fingerprint(path) for path in sorted(args.output_dir.iterdir()) if path.is_file()],
                        "scope": "local_design_evidence", "self_hash": "excluded"})
    print(json.dumps({"worker_exit_code": code, "timed_out": timed_out, "output_dir": str(args.output_dir)}))
    return 124 if timed_out else code


if __name__ == "__main__":
    raise SystemExit(main())
