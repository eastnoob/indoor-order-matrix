"""Join frozen structural input, explicit sections and provisional boundary evidence.

This is design glue only. It creates no active AnalysisDomain and never closes
gaps by buffering, snapping, bbox, hull, or unqualified door assumptions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

from shapely.geometry import GeometryCollection, LineString, Polygon, mapping, shape
from shapely.ops import nearest_points, unary_union

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.design.space_field import run_floor_plan_3d_comparison as sections

CLASS_ROLES = {"wall": "IfcWall", "column": "IfcColumn", "door": "IfcDoor", "furniture": "IfcFurniture"}
METHOD = "exact_section_mass_union_bounded_rings_compound_exterior_scope/v1"


def polygon_parts(geometry):
    """Return deterministic polygon components without geometric repair."""
    parts = [geometry] if geometry.geom_type == "Polygon" else list(getattr(geometry, "geoms", ()))
    return sorted([p for p in parts if p.geom_type == "Polygon" and not p.is_empty], key=lambda p: (p.bounds, p.area, p.wkb_hex))


def source_class(row):
    """Use external authored IFC identity or explicit synthetic class only."""
    return row.get("identity", {}).get("ifc_class") or row.get("synthetic_class")


def section_sources(rows, height):
    """Reuse exact source-edge sections and retain every physical source record."""
    records = []
    for row in rows:
        cut = sections.section(row, height)
        cls = source_class(row)
        eligibility = cls in {"IfcWall", "IfcColumn"}
        reason = "eligible_structural_class" if eligibility else (
            "door_requires_qualified_host_and_closure_scenario" if cls == "IfcDoor" else "unknown_class" if cls is None else "excluded_nonboundary_class")
        records.append({"id": row["id"], "role": row["role"], "source_class": cls,
                        "identity": row.get("identity"), "source_record_id": row.get("source_record_id"),
                        "adapter_source_id": row.get("source_id"), "geometry_ref": row["patch"].source_geometry_id,
                        "physical_source_retained": True, "qualification": row["qualification"],
                        "eligibility": {"eligible": eligibility, "reason": reason,
                                        "usable_section_for_support": eligibility and cut["status"] == "qualified_section" and cut["geometry"]["area_m2"] > 0},
                        "section": cut})
    return records


def qualify_scenarios(records, scenarios):
    """Require explicit host, authored opening extent and closure geometry for seals."""
    sources = {r["id"]: r for r in records}
    observations, seals = [], []
    for scenario in scenarios:
        refs = scenario.get("host_refs", [])
        geometry = scenario.get("qualified_seal_geometry")
        opening = scenario.get("authored_opening_geometry")
        reason = None
        if not scenario.get("assumed_closed"):
            reason = "open_scenario_no_seal"
        elif not refs or any(ref not in sources or sources[ref]["source_class"] != "IfcWall" for ref in refs):
            reason = "host_relation_unresolved"
        elif not geometry or not opening or scenario.get("seal_section_status") != "qualified_section":
            reason = "qualified_location_extent_closure_geometry_missing"
        else:
            seal, authored = shape(geometry), shape(opening)
            hosts = [shape(sources[ref]["section"]["geometry"]["geojson"]) for ref in refs]
            # Exact geometry qualification is local to the declared synthetic
            # opening. A class, name or box cannot manufacture this extent.
            if not seal.is_valid or seal.area <= 0 or not seal.equals(authored):
                reason = "seal_does_not_match_authored_opening_extent"
            elif any(not sources[ref]["eligibility"]["usable_section_for_support"] for ref in refs):
                reason = "host_section_unqualified"
            elif not all(seal.boundary.intersection(host.boundary).length > 0 for host in hosts):
                reason = "closure_contact_with_each_declared_host_not_demonstrated"
            else:
                seals.append({"id": scenario["id"], "geometry": seal, "host_refs": refs})
        observations.append({"id": scenario["id"], "source_ref": scenario.get("source_ref"), "host_refs": refs,
                             "assumed_closed": scenario.get("assumed_closed"), "observed_state": None,
                             "seal_applied": reason is None, "reason": reason, "provenance": scenario["provenance"],
                             "qualified_seal_geometry": geometry if reason is None else None,
                             "physical_source_mass_changed": False})
    return observations, seals


def contact_graph(geometries):
    """Measure exact area/positive-length contacts and source connectedness separately."""
    ids = sorted(geometries)
    adjacency = {key: set() for key in ids}
    contacts = []
    for index, first in enumerate(ids):
        for second in ids[index + 1:]:
            intersection = geometries[first].intersection(geometries[second])
            if intersection.area > 0 or intersection.length > 0:
                adjacency[first].add(second)
                adjacency[second].add(first)
                contacts.append({"source_refs": [first, second], "intersection_area_m2": intersection.area,
                                 "contact_length_m": intersection.length})
    components, unseen = [], set(ids)
    while unseen:
        queue = [min(unseen)]
        unseen.remove(queue[0])
        group = []
        while queue:
            current = queue.pop()
            group.append(current)
            for neighbor in sorted(adjacency[current] & unseen):
                unseen.remove(neighbor)
                queue.append(neighbor)
        components.append(sorted(group))
    return {"components": components, "component_count": len(components), "contacts": contacts,
            "policy": "exact area or positive-length contact; point-touch alone is separate"}


def infer_candidates(records, scenarios):
    """Infer fresh rings and wall-bearing compound scopes from the current section."""
    scenario_records, seals = qualify_scenarios(records, scenarios)
    eligible = {r["id"]: shape(r["section"]["geometry"]["geojson"]) for r in records if r["eligibility"]["usable_section_for_support"]}
    eligible = {key: geometry for key, geometry in eligible.items() if not geometry.is_empty}
    geometry = dict(eligible) | {s["id"]: s["geometry"] for s in seals}
    union = unary_union(list(geometry.values()))
    rows = {r["id"]: r for r in records}
    scopes, contours, no_scope_components = [], [], []
    parts = polygon_parts(union)
    for component_index, component in enumerate(parts, 1):
        member_refs = sorted(key for key, mass in geometry.items() if component.intersection(mass).area > 0)
        wall_refs = [key for key in member_refs if key in rows and rows[key]["source_class"] == "IfcWall"]
        rings = sorted([Polygon(ring) for ring in component.interiors], key=lambda p: (p.bounds, p.area, p.wkb_hex))
        # Solid exteriors by themselves are not rooms. A bounded ring and wall
        # evidence are required even for this provisional compound proposal.
        if not wall_refs or not rings:
            no_scope_components.append({"component_index": component_index, "source_refs": member_refs,
                                         "reason": "no_wall_bearing_bounded_ring" if not wall_refs else "no_bounded_ring_at_requested_height",
                                         "geometry": sections.geometry_report(component)})
            continue
        scope_id = f"S{len(scopes) + 1}"
        extent = Polygon(component.exterior)
        scope_contours = []
        for interior in rings:
            contour_id = f"C{len(contours) + 1}"
            supports = [{"source_ref": key, "positive_length_contact_m": mass.boundary.intersection(interior.boundary).length}
                        for key, mass in geometry.items() if mass.boundary.intersection(interior.boundary).length > 0]
            supporting_walls = [s["source_ref"] for s in supports if s["source_ref"] in wall_refs]
            if not supporting_walls:
                continue
            scope_contours.append(contour_id)
            column_observations = []
            for support in supports:
                key = support["source_ref"]
                if key not in rows or rows[key]["source_class"] != "IfcColumn":
                    continue
                without = unary_union([mass for ref, mass in geometry.items() if ref != key])
                remaining_rings = [Polygon(ring) for p in polygon_parts(without) for ring in p.interiors]
                probe = interior.representative_point()
                column_observations.append({"source_ref": key, "contour_contact_m": support["positive_length_contact_m"],
                                            "same_contour_retained_without_column": any(ring.equals(interior) for ring in remaining_rings),
                                            "bounded_region_at_probe_without_column": any(ring.covers(probe) for ring in remaining_rings),
                                            "opened_to_unbounded_complement_at_probe_without_column": not any(ring.covers(probe) for ring in remaining_rings),
                                            "probe_xy_m": [probe.x, probe.y]})
            contours.append({"id": contour_id, "scope_ref": scope_id, "geometry": sections.geometry_report(interior),
                             "valid_polygon": interior.is_valid, "closed_ring": interior.exterior.is_closed,
                             "support": supports, "column_contribution": column_observations,
                             "meaning": "bounded complement contour; not room, free-space or inner-only AnalysisDomain"})
        if not scope_contours:
            continue
        local_doors = []
        for row in records:
            if row["source_class"] != "IfcDoor":
                continue
            lines = unary_union([LineString([point[:2] for point in line]) for line in row["section"]["contour_segments_xyz"]])
            if lines.intersects(extent):
                local_doors.append({"source_ref": row["id"], "location_observation": "actual_section_contours_intersect_scope",
                                    "host_relation": "unresolved", "seal_applied": False,
                                    "section_qualification": row["section"]["status"]})
        graph = contact_graph({key: geometry[key] for key in member_refs})
        scopes.append({"id": scope_id, "geometry": sections.geometry_report(extent), "enclosure_contour_refs": scope_contours,
                       "source_refs": member_refs, "wall_refs": wall_refs, "source_connectedness": graph,
                       "supporting_mass": sections.geometry_report(component),
                       "support_mass_outside_scope_area_m2": component.difference(extent).area,
                       "construction": "actual_wall_bearing_component_exterior_with_all_bounded_holes_filled",
                       "per_room_wall_allocation": "unresolved", "local_extent_ambiguity": len(scope_contours) > 1,
                       "local_unresolved_doors": local_doors,
                       "geometric_closure": "closed_compound_exterior_with_bounded_contours",
                       "semantic_completeness": "unqualified_unknown_floor_datum_and_unresolved_source_semantics",
                       "accepted": False, "active_AnalysisDomain": False, "status": "provisional_diagnostic_only"})
    support_ids = {support["source_ref"] for contour in contours for support in contour["support"]}
    source_observations = [{"source_ref": r["id"], "eligibility": r["eligibility"],
                            "demonstrated_contour_contribution": r["id"] in support_ids,
                            "occupancy_only_in_this_boundary_run": r["source_class"] == "IfcColumn" and r["id"] not in support_ids,
                            "physical_occupancy_retained": True} for r in records]
    separations = []
    for index, first in enumerate(parts):
        candidates = [(first.distance(second), j, second) for j, second in enumerate(parts) if index != j and first.distance(second) > 0]
        if candidates:
            distance, second_index, second = min(candidates, key=lambda item: (item[0], item[1]))
            a, b = nearest_points(first, second)
            separations.append({"component_refs": [index + 1, second_index + 1], "distance_m": distance,
                                "segment_xy_m": [[a.x, a.y], [b.x, b.y]],
                                "meaning": "exact disconnected-mass separation; not authored opening or permission to seal"})
    return {"method": METHOD, "eligible_mass_union": sections.geometry_report(union), "source_observations": source_observations,
            "eligible_source_contact_graph": contact_graph(eligible),
            "enclosure_contours": contours, "scope_proposals": scopes, "scenario_evidence": scenario_records,
            "components_without_scope": no_scope_components, "geometric_separations": separations,
            "counts": {"physical_source_records": len(records), "usable_boundary_sections": len(eligible),
                       "enclosure_contours": len(contours), "compound_scope_proposals": len(scopes),
                       "occupied_polygon_components": len(parts)},
            "global_limits": ["unknown_authored_floor_datum", "disk_snapshot_geometry_parity_unverified",
                              "unresolved_real_opening_host_relations", "no_active_domain_or_free_space_or_routes"],
            "candidate_winner": None}


def synthetic_rows(definition):
    """Reuse the previous box controls with explicit declared synthetic IFC classes."""
    rows = sections.build_fixture(definition)
    for row in rows:
        row["synthetic_class"] = CLASS_ROLES.get(row["role"])
    return rows


def controls(out):
    """Leave bounded analytic checks for contribution, seal refusal and exclusion."""
    original = sections.fixture_definitions()[0]
    sections.write_json(out / "control_oracles_before_queries.json", {
        "column_gap": {"closed_contours": 1, "scope_area_m2": 24, "contour_area_m2": 19.25,
                       "scope_holes": 0, "interior_column_contributes": False, "removed_gap_column_contours": 0},
        "opening": {"open_contours": 0, "qualified_closed_contours": 1, "unresolved_host_contours": 0,
                    "unresolved_geometry_contours": 0, "observed_physical_mass_unchanged_by_scenario": True},
        "excluded_object": "boundary candidate payload identical; physical source count +1"})
    rows = synthetic_rows(original)
    records = section_sources(rows, 1.5)
    base = infer_candidates(records, [])
    assert base["counts"]["enclosure_contours"] == 1 and base["counts"]["compound_scope_proposals"] == 1
    assert abs(base["scope_proposals"][0]["geometry"]["area_m2"] - 24) <= 1e-6
    assert abs(base["enclosure_contours"][0]["geometry"]["area_m2"] - 19.25) <= 1e-6
    assert base["scope_proposals"][0]["geometry"]["hole_count"] == 0
    observations = {r["source_ref"]: r for r in base["source_observations"]}
    assert observations["interior_column"]["occupancy_only_in_this_boundary_run"]
    assert observations["boundary_column"]["demonstrated_contour_contribution"]
    assert base["enclosure_contours"][0]["column_contribution"][0]["opened_to_unbounded_complement_at_probe_without_column"]
    gap = infer_candidates([r for r in records if r["id"] != "boundary_column"], [])
    assert gap["counts"]["enclosure_contours"] == 0
    isolated = infer_candidates([r for r in records if r["id"] == "interior_column"], [])
    assert isolated["counts"]["compound_scope_proposals"] == 0
    excluded_definition = {"boxes": [["excluded_furniture", "furniture", [0, 0, 0, 6, 4, 3]]]}
    excluded = infer_candidates(records + section_sources(synthetic_rows(excluded_definition), 1.5), [])
    assert excluded["scope_proposals"] == base["scope_proposals"] and excluded["enclosure_contours"] == base["enclosure_contours"]
    assert excluded["counts"]["physical_source_records"] == base["counts"]["physical_source_records"] + 1
    # The prior gap is an explicitly authored synthetic opening with a lintel.
    # Closure geometry is a separate hypothetical panel, never observed mass.
    lintel = synthetic_rows({"boxes": [["host_lintel", "wall", [2.75, 0, 2.1, 3.25, .25, 3]]]})
    host_records = [r for r in records if r["id"] != "boundary_column"] + section_sources(lintel, 1.5)
    seal_record = section_sources(synthetic_rows({"boxes": [["hypothetical_panel", "door", [2.75, 0, 0, 3.25, .25, 2.1]]]}), 1.5)[0]
    scenario = {"id": "synthetic_closed_seal", "assumed_closed": True, "host_refs": ["south_left", "south_right"],
                "authored_opening_geometry": mapping(Polygon([(2.75, 0), (3.25, 0), (3.25, .25), (2.75, .25)])),
                "qualified_seal_geometry": seal_record["section"]["geometry"]["geojson"],
                "seal_section_status": seal_record["section"]["status"],
                "provenance": "synthetic_explicit_host_opening_and_hypothetical_panel; default_closed_assumption_not_observation"}
    closed = infer_candidates(host_records, [scenario])
    opened = infer_candidates(host_records, [scenario | {"assumed_closed": False}])
    missing_host = infer_candidates(host_records, [scenario | {"host_refs": []}])
    missing_geometry = infer_candidates(host_records, [scenario | {"qualified_seal_geometry": None}])
    assert closed["counts"]["enclosure_contours"] == 1 and closed["scenario_evidence"][0]["seal_applied"]
    assert opened["counts"]["enclosure_contours"] == missing_host["counts"]["enclosure_contours"] == missing_geometry["counts"]["enclosure_contours"] == 0
    assert missing_host["scenario_evidence"][0]["reason"] == "host_relation_unresolved"
    assert missing_geometry["scenario_evidence"][0]["reason"] == "qualified_location_extent_closure_geometry_missing"
    assert closed["counts"]["physical_source_records"] == opened["counts"]["physical_source_records"]
    sections.write_json(out / "controls.json", {"passed": True, "column_closed": base, "column_removed": gap,
                        "isolated_column": isolated, "excluded_object": excluded, "opening_closed": closed,
                        "opening_open": opened, "opening_host_refusal": missing_host, "opening_geometry_refusal": missing_geometry})


def render(records, result, out, height):
    """Draw actual sectional occupancy, compound scopes, bounded contours and limits."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    fig = plt.figure(figsize=(18, 10))
    grid = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.1, .95])
    axes = [fig.add_subplot(grid[0, index]) for index in (0, 1)]
    table = fig.add_subplot(grid[0, 2])
    table.axis("off")
    observations = {r["source_ref"]: r for r in result["source_observations"]}
    all_points = []
    for row in records:
        color = "#326aa1" if row["source_class"] == "IfcWall" else (
            "#d88121" if observations[row["id"]]["demonstrated_contour_contribution"] else "#e0bd8a" if row["source_class"] == "IfcColumn" else "#337e67")
        cut = row["section"]
        for ax in axes:
            sections.plot_polygon(ax, shape(cut["geometry"]["geojson"]), color)
            if cut["status"] != "qualified_section":
                for line in cut["contour_segments_xyz"]:
                    ax.plot([p[0] for p in line], [p[1] for p in line], color="#b7353d", lw=1)
        all_points.extend(p[:2] for line in cut["contour_segments_xyz"] for p in line)
    for scope in result["scope_proposals"]:
        geometry = shape(scope["geometry"]["geojson"])
        x, y = geometry.exterior.xy
        axes[1].plot(x, y, color="#7b3db1", lw=2.2, linestyle="--")
        point = geometry.representative_point()
        axes[1].annotate(scope["id"], (point.x, point.y), fontsize=13, weight="bold", color="#7b3db1",
                         bbox={"facecolor": "white", "alpha": .8, "edgecolor": "none"})
    for contour in result["enclosure_contours"]:
        geometry = shape(contour["geometry"]["geojson"])
        x, y = geometry.exterior.xy
        axes[1].plot(x, y, color="#c94d91", lw=1.2, linestyle=":")
        point = geometry.representative_point()
        axes[1].annotate(contour["id"], (point.x, point.y), fontsize=9, color="#a33672", xytext=(3, 4), textcoords="offset points")
    displayed_gaps, pair_keys = [], set()
    for gap in sorted(result["geometric_separations"], key=lambda g: (g["distance_m"], g["component_refs"])):
        pair_key = tuple(sorted(gap["component_refs"]))
        if pair_key not in pair_keys:
            pair_keys.add(pair_key)
            displayed_gaps.append(gap)
        if len(displayed_gaps) == 4:
            break
    for index, gap in enumerate(displayed_gaps, 1):
        a, b = gap["segment_xy_m"]
        axes[0].plot([a[0], b[0]], [a[1], b[1]], "r--", lw=1.2)
        axes[0].annotate(f"G{index}", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), xytext=(2, 5),
                         textcoords="offset points", fontsize=9, color="#b7353d", bbox={"facecolor": "white", "alpha": .8, "edgecolor": "none"})
    xs, ys = zip(*all_points)
    for ax, title in zip(axes, ("Sectional mass and eligibility", "Fresh provisional compound scopes / contours")):
        ax.set(xlim=(min(xs) - .6, max(xs) + .6), ylim=(min(ys) - .6, max(ys) + .6), xlabel="World X (m)", ylabel="World Y (m)", title=title)
        ax.set_aspect("equal")
        ax.grid(alpha=.15)
    table_rows = [f"{s['id']}  extent {s['geometry']['area_m2']:.3f} m2\n  contours {', '.join(s['enclosure_contour_refs'])}\n  sources {len(s['source_refs'])}, wall refs {len(s['wall_refs'])}\n  valid {s['geometry']['valid']}, source components {s['source_connectedness']['component_count']}\n  local unresolved doors {len(s['local_unresolved_doors'])}\n  per-room extent unresolved; provisional" for s in result["scope_proposals"]]
    if not table_rows:
        table_rows = ["NO WALL-BEARING BOUNDED RING\n0 contours / 0 scope proposals\n\nOccupied components (not room count):\n" +
                      "\n".join(f"M{c['component_index']}: {len(c['source_refs'])} refs; {c['geometry']['area_m2']:.3f} m2" for c in result["components_without_scope"])]
    table.text(0, 1, "CURRENT-INPUT DIAGNOSTIC TABLE\n\n" + "\n\n".join(table_rows) +
               f"\n\n27 qualified structural sections.\nExact source-contact graph: {result['eligible_source_contact_graph']['component_count']} groups.\nPolygon union valid: {result['eligible_mass_union']['valid']}.\n" +
               "\n".join(f"G{i}: exact separation {g['distance_m']:.6f} m" for i, g in enumerate(displayed_gaps, 1)) +
               "\n\nSource refs / STEP / GlobalId in JSON.\nScenario: default closed assumption;\nreal door seals REFUSED.\n\nValidity, contact connectivity and\nsemantic completeness are separate.\nNo certified room count.\nNo active AnalysisDomain.\n\nRed lines: unqualified contours or\n4 shortest exact mass separations;\nseparations are not opening facts.", va="top", fontsize=10)
    fig.suptitle(f"Boundary-only inference from frozen structural sections | z={height:g} m\nWorld z=0 datum assumed; no disk/snapshot geometry parity; 11 walls / 16 columns / 6 doors retained", fontsize=15)
    fig.legend(handles=[Patch(color="#326aa1", label="Wall mass"), Patch(color="#d88121", label="Column: contour contribution"),
                        Patch(color="#e0bd8a", label="Column: occupancy only"), Patch(color="#337e67", label="Door occupancy; unsealed"),
                        Line2D([], [], color="#7b3db1", linestyle="--", label="Compound scope exterior"),
                        Line2D([], [], color="#c94d91", linestyle=":", label="Bounded enclosure contour")], loc="lower center", ncol=3)
    fig.subplots_adjust(top=.82, bottom=.16, wspace=.25)
    fig.savefig(out / "real_boundary_height_view.png", dpi=150)
    plt.close(fig)


def run(args):
    """Execute small controls, then the current frozen source through joined inference."""
    out = args.output_dir
    snapshot_fp = sections.fingerprint(args.snapshot)
    assert snapshot_fp["sha256"] == sections.SNAPSHOT_HASH
    snapshot = json.loads(args.snapshot.read_bytes())
    ifc = sections.fingerprint(Path(snapshot["source_ifc"]["path"]))
    assert ifc["sha256"] == sections.IFC_HASH and ifc["bytes"] == 408617800
    helpers = {name: sections.fingerprint(importlib.import_module(name).__file__) for name in
               ("scripts.design.space_field.run_floor_plan_3d_comparison", "features.geometry_views", "features.geometry_substitutes", "adapters.blender_geometry")}
    sections.write_json(out / "provenance.json", {"snapshot": snapshot_fp, "disk_ifc_identity_only": ifc, "helpers": helpers,
                        "runner": sections.fingerprint(__file__), "contract": sections.fingerprint(args.contract),
                        "plane": {"origin": [0, 0, args.datum], "basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
                        "datum_world_z_m": args.datum, "datum_status": "experiment_only_assumption",
                        "cut_height_relative_m": args.cut_height, "section_world_z_m": args.datum + args.cut_height,
                        "units": "m", "geometry_parity": "not_established", "boundary_gap_repair": "none",
                        "scenario": "default_closed_assumption_no_real_seals_without_qualification"})
    (out / "contract_snapshot.md").write_bytes(args.contract.read_bytes())
    controls(out)
    rows = sections.normalize(snapshot)
    records = section_sources(rows, args.datum + args.cut_height)
    scenarios = [{"id": f"unresolved_closed:{r['id']}", "source_ref": r["id"], "host_refs": [], "assumed_closed": True,
                  "provenance": "human_default_closed_scenario; frozen IFC has no qualified opening-host relation or closure extent"}
                 for r in records if r["source_class"] == "IfcDoor"]
    result = infer_candidates(records, scenarios)
    sections.write_json(out / "source_sections.json", records)
    sections.write_json(out / "boundary_result.json", result)
    sections.write_json(out / "candidate_table.json", {"scope_proposals": result["scope_proposals"], "enclosure_contours": result["enclosure_contours"]})
    assert len(records) == 33 and Counter(r["source_class"] for r in records) == {"IfcWall": 11, "IfcColumn": 16, "IfcDoor": 6}
    assert all(not scenario["seal_applied"] for scenario in result["scenario_evidence"])
    assert all(not s["active_AnalysisDomain"] and not s["accepted"] and s["support_mass_outside_scope_area_m2"] <= 1e-6 for s in result["scope_proposals"])
    render(records, result, out, args.datum + args.cut_height)
    checks = {"analytic_controls": "passed", "physical_sources_retained": 33, "real_door_seals_refused": 6,
              "provisional_only": True, "counts": result["counts"]}
    if args.reproduce_of:
        files = ("source_sections.json", "boundary_result.json", "candidate_table.json", "controls.json",
                 "control_oracles_before_queries.json", "provenance.json", "contract_snapshot.md", "real_boundary_height_view.png", "runner_snapshot.py")
        assert all((out / filename).read_bytes() == (args.reproduce_of / filename).read_bytes() for filename in files)
        checks["separate_process_byte_identical_files"] = files
    sections.write_json(out / "checks.json", checks)
    print(json.dumps(checks), flush=True)


def main():
    """Refuse existing runs and supervise only this child with a bounded timeout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--datum", type=float, required=True)
    parser.add_argument("--cut-height", type=float, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=ROOT / "docs/superpowers/plans/2026-10-08-d6-boundary-inference-height-view.md")
    parser.add_argument("--reproduce-of", type=Path)
    parser.add_argument("--budget-seconds", type=int, default=120)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    import math
    if not all(math.isfinite(value) for value in (args.datum, args.cut_height)) or args.budget_seconds <= 0:
        parser.error("finite datum/height and positive timeout required")
    if args.worker:
        try:
            run(args)
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
            code = process.wait(timeout=args.budget_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait()
    sections.write_json(args.output_dir / "execution.json", {"parent_argv": sys.argv, "worker_argv": command,
                        "worker_pid": process.pid, "worker_exit_code": code, "timed_out": timed_out,
                        "started_utc": started, "ended_utc": datetime.now(timezone.utc).isoformat(),
                        "elapsed_seconds": time.perf_counter() - tick, "budget_seconds": args.budget_seconds})
    sections.write_json(args.output_dir / "manifest.json", {"artifacts": [sections.fingerprint(p) for p in sorted(args.output_dir.iterdir()) if p.is_file()],
                        "storage": "local_only; source file hashes do not preserve external source bytes", "self_hash": "excluded"})
    print(json.dumps({"worker_exit_code": code, "timed_out": timed_out, "output_dir": str(args.output_dir)}))
    return 124 if timed_out else code


if __name__ == "__main__":
    raise SystemExit(main())
