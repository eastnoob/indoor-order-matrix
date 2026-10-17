"""Build a partial historical-S3 diagnostic from frozen actual Body meshes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from shapely.geometry import GeometryCollection, MultiPoint, Point, box, mapping, shape
from shapely.errors import GEOSException
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from features.geometry_substitutes import mass_patch_from_mesh
from features.geometry_views import component_shape, plan_projection
from features.scene_contract import AnalysisPlane, MeshGeometry3D

CAPTURE = ROOT / "outputs/design/b3_real_source_field/run_001"
BLENDER = Path("D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")
SYNTHETIC = ROOT / "scripts/design/space_field/run_b3_space_field_exploratory.py"
SPEC = importlib.util.spec_from_file_location("b3_accepted_samples", SYNTHETIC)
ACCEPTED = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ACCEPTED
SPEC.loader.exec_module(ACCEPTED)
EMPTY = GeometryCollection()


def read_json(path):
    """Reject duplicate keys and nonfinite constants at the file boundary."""
    def reject(value):
        """Reject JSON constants which are not finite numbers."""
        raise ValueError(f"Nonfinite JSON: {value}")

    def unique(pairs):
        """Prevent duplicate keys from silently replacing evidence."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate key: {key}")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject, object_pairs_hook=unique)


def file_ref(path):
    """Hash the bytes of an input or delivered artifact without loading meshes."""
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def write_json(path, value):
    """Persist strict JSON, never replacing an existing attempt artifact."""
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, allow_nan=False, separators=(",", ":"))


def mesh_patch(record):
    """Transport already-world-metre meshes without scaling or adapter extraction."""
    assert record["units"] == "m" and record["transform_applied"] is True
    mesh = MeshGeometry3D(
        id=f"blender-mesh:{record['id']}", vertices=record["vertices"],
        triangle_indices=record["triangles"], normals=(), is_manifold=record["is_manifold"],
        is_closed=record["is_closed"], local_to_world_provenance={"world_transform_applied_once": True},
        source_representation_id=record["representation_id"],
        tessellation_settings=record["tessellation_settings"], units="m",
    )
    return mass_patch_from_mesh(mesh)


def source_query(row, patch, hull, domain, band, candidate):
    """Keep unknown solids null while extracting an explicitly approximate target."""
    common = {"world_band_m": band, "complete_physical_occupancy_status": "unsupported",
              "complete_physical_occupancy_geometry": None, "exact_section_status": "unsupported",
              "exact_section_geometry": None, "positive_observed_height_range_overlap": candidate,
              "helper_uncertainty": None, "raw_projection_geometry": None, "clipped_projection_geometry": None,
              "raw_projection_area_m2": None, "clipped_projection_area_m2": None,
              "uncertainty_support_geometry": None}
    if not row["solid_query_eligible"]:
        # A vertex hull encloses every source triangle, including collapsed XY faces.
        # It is only a conservative support for unassessed geometry, never occupancy.
        support = hull if candidate else EMPTY
        common.update(status="unsupported_mesh", diagnostic_projection_status="not_available",
                      uncertainty_support_geometry=mapping(support), uncertainty_support_area_m2=support.area,
                      clipped_uncertainty_support_geometry=mapping(support.intersection(domain)),
                      support_method="full_height_convex_hull_of_actual_XY_vertices_plus_observed_height_candidacy_not_occupancy")
        return common, None, support
    projection = plan_projection(patch, height_band=tuple(band))
    polygon = component_shape(projection.components)
    common["helper_uncertainty"] = projection.uncertainty
    common["helper_projection"] = projection.to_dict()
    common["method"] = "existing_plan_projection_surface_clipping_or_cross_section_reconstruction_or_full_footprint_fallback"
    common["internal_stage"] = "not_exposed_by_helper; uncertainty_null_is_not_certification"
    if polygon is None and candidate:
        common.update(status="projection_missing", diagnostic_projection_status="not_available",
                      uncertainty_support_geometry=mapping(hull),
                      clipped_uncertainty_support_geometry=mapping(hull.intersection(domain)))
        return common, None, hull
    polygon = polygon if polygon is not None else EMPTY
    common.update(status="diagnostic_projection", diagnostic_projection_status="computed_approximation_only",
                  raw_projection_geometry=mapping(polygon), clipped_projection_geometry=mapping(polygon.intersection(domain)),
                  raw_projection_area_m2=polygon.area, clipped_projection_area_m2=polygon.intersection(domain).area)
    return common, polygon, EMPTY


def sample_variant(domain, projection, uncertainty_support, spacing, origin):
    """Reuse accepted lattice/comparison logic against the same diagnostic target."""
    samples = []
    for i, j, x, y in ACCEPTED._sample_grid(domain, spacing, origin):
        point = Point(x, y)
        inside = bool(domain.covers(point))
        samples.append({
            "cell_i": i, "cell_j": j, "x_m": x, "y_m": y, "domain_mask": inside,
            "clearance_to_domain_boundary_m": point.distance(domain.boundary) if inside else None,
            "domain_distance_status": "computed" if inside else "outside_domain",
            "physical_occupancy_mask": None, "physical_occupancy_status": "partial_unsupported",
            "exact_section_mask": None, "exact_section_status": "unsupported",
            "known_free_mask": None, "clearance_to_complete_physical_occupancy_m": None,
            "complete_occupancy_distance_status": "unsupported",
            "diagnostic_projection_mask": bool(inside and projection.covers(point)),
            "diagnostic_complement_mask": bool(inside and not projection.covers(point)),
            "diagnostic_complement_meaning": "complement_of_approximation_not_known_free",
            "clearance_to_diagnostic_projection_m": point.distance(projection) if inside and not projection.is_empty else None,
            "diagnostic_distance_status": "computed_to_raw_projection_only" if inside and not projection.is_empty else "not_available",
            "unassessed_support_mask": bool(inside and uncertainty_support.covers(point)),
            "complete_field_unassessed_mask": inside,
            "gaussian_group_support_raw": None, "gaussian_group_support_status": "not_available_no_qualified_groups",
        })
    # Adapt only the temporary keys required by the accepted comparison helper.
    adapter = [{**cell, "projection_occupancy_mask": cell["diagnostic_projection_mask"],
                "clearance_to_projection_occupancy_m": cell["clearance_to_diagnostic_projection_m"]} for cell in samples]
    try:
        observed = ACCEPTED._observation(domain, projection, adapter, "projection", spacing)
        reconstruction = observed["reconstructed_center_labeled_cells"]
        reconstruction_status = "computed_against_diagnostic_target"
        reconstruction_error = None
    except GEOSException as exc:
        # Exact S3 boundary contacts can produce mixed-dimensional GEOS overlays.
        # Keep masks and connectivity; never snap the historical scope to force a result.
        clipped = domain.intersection(projection)
        free = domain.difference(projection)
        vector = len(ACCEPTED._polygon_parts(free))
        four = ACCEPTED._sampled_components(adapter, "projection_occupancy_mask", False)
        eight = ACCEPTED._sampled_components(adapter, "projection_occupancy_mask", True)
        sampled_domain = sum(c["domain_mask"] for c in samples) * spacing ** 2
        sampled_projection = sum(c["diagnostic_projection_mask"] for c in samples) * spacing ** 2
        observed = {"vector_free_components": vector, "sampled_4_neighbor_free_components": four,
                    "sampled_8_neighbor_free_components": eight, "occupancy_area_error_m2": sampled_projection - clipped.area,
                    "domain_area_error_m2": sampled_domain - domain.area,
                    "sampled_free_area_error_m2": sampled_domain - sampled_projection - free.area,
                    "connectivity_discrepancy": vector != four or vector != eight}
        cells = [box(c["x_m"] - spacing / 2, c["y_m"] - spacing / 2, c["x_m"] + spacing / 2, c["y_m"] + spacing / 2) for c in samples]
        reconstruction = {"false_free_area_m2": None, "false_occupied_area_m2": None, "symmetric_difference_area_m2": None,
                          "unrepresented_domain_area_m2": domain.difference(unary_union(cells)).area, "polygons": None}
        reconstruction_status = "not_available_GEOS_overlay_error_no_scope_repair"
        reconstruction_error = str(exc)
    comparison = {
        "reference": "same_approximate_eligible_mesh_band_projection_not_physical_truth",
        "vector_diagnostic_complement_components": observed["vector_free_components"],
        "sampled4_diagnostic_complement_components": observed["sampled_4_neighbor_free_components"],
        "sampled8_diagnostic_complement_components": observed["sampled_8_neighbor_free_components"],
        "eight_neighbor_policy": "unrestricted_diagonals_no_corner_cut_filter",
        "signed_projection_point_area_error_m2": observed["occupancy_area_error_m2"],
        "signed_domain_point_area_error_m2": observed["domain_area_error_m2"],
        "signed_complement_point_area_error_m2": observed["sampled_free_area_error_m2"],
        "directional_errors_target": "diagnostic_projection_only; false_free_is_missed_projection_not_known_free",
        "false_free_vs_diagnostic_target_m2": reconstruction["false_free_area_m2"],
        "false_occupied_vs_diagnostic_target_m2": reconstruction["false_occupied_area_m2"],
        "symmetric_difference_vs_diagnostic_target_m2": reconstruction["symmetric_difference_area_m2"],
        "unrepresented_domain_area_m2": reconstruction["unrepresented_domain_area_m2"],
        "reconstructed_projection_geometry": reconstruction["polygons"],
        "connectivity_discrepancy": observed["connectivity_discrepancy"],
        "stability": "no_passed_threshold_selected", "conservative_coverage": False,
        "reconstruction_status": reconstruction_status, "reconstruction_operation_error": reconstruction_error,
    }
    return {"spacing_m": spacing, "origin_offset_m": origin, "index_frame": "relative_to_domain_bbox_min; world_XY_metres",
            "sample_count": len(samples), "domain_sample_count": sum(c["domain_mask"] for c in samples),
            "samples": samples, "comparison": comparison}


def geometry_audit(geometry):
    """Record validity and leaf types before any derived area-view conversion."""
    def leaves(item):
        """Retain linear and point leaves so discarded contacts stay measurable."""
        return [leaf for child in item.geoms for leaf in leaves(child)] if hasattr(item, "geoms") else [item]
    parts = leaves(geometry)
    removed = [part for part in parts if part.geom_type != "Polygon" or part.area <= 0]
    return {"geometry_type": geometry.geom_type, "is_valid": bool(geometry.is_valid),
            "area_m2": geometry.area, "leaf_type_counts": dict(Counter(p.geom_type for p in parts)),
            "non_positive_polygon_leaf_types": dict(Counter(p.geom_type for p in removed)),
            "removable_area_m2": sum(p.area for p in removed),
            "removable_length_m": sum(p.length for p in removed)}


def polygonal_union(geometries, audit=None):
    """Union valid inputs and explicitly account for zero-area contact removal."""
    inputs = [geometry_audit(item) for item in geometries]
    # Invalid positive-area inputs must fail visibly rather than disappear from the field.
    if any(not item["is_valid"] for item in inputs):
        raise ValueError("Invalid union input; no repair or positive-area filtering permitted")
    # Linear contacts remain source audit evidence but cannot carry an area mask.
    union = unary_union(geometries) if geometries else EMPTY
    assert union.is_valid, "Invalid derived union; no automatic repair"
    result = unary_union(ACCEPTED._polygon_parts(union))
    assert result.is_valid
    if audit is not None:
        audit.update(inputs=inputs, union_before_area_view=geometry_audit(union),
                     output=geometry_audit(result), make_valid_applied=False,
                     processing="unary_union_then_positive_area_polygon_view; no_precision_or_source_change",
                     removed_area_m2=union.area - result.area)
    return result


def draw_geometry(ax, geometry, color, *, fill=False, hatch=None, alpha=1.0, linewidth=1.0):
    """Draw all polygon interiors without filling structural holes."""
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath
    from shapely.geometry.polygon import orient
    for polygon in ACCEPTED._polygon_parts(geometry):
        polygon = orient(polygon, sign=1)
        vertices, codes = [], []
        for ring in [polygon.exterior, *polygon.interiors]:
            coords = list(ring.coords)
            vertices.extend(coords)
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor=color if fill else "none", edgecolor=color,
                               linewidth=linewidth, hatch=hatch, alpha=alpha))


def render_plans(out, field, source_hulls):
    """Export readable equal-aspect world-coordinate plans with explicit limits."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    domain = shape(field["domain_geometry"])
    limits = domain.bounds
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 12})
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    for ax in axes.flat:
        ax.set(xlim=(limits[0] - .8, limits[2] + .8), ylim=(limits[1] - .8, limits[3] + .8),
               xlabel="World X (m)", ylabel="World Y (m)")
        ax.set_aspect("equal")
        ax.grid(alpha=.12)
    for hull in source_hulls:
        draw_geometry(axes[0, 0], hull, "#9ba5b4", linewidth=.4, alpha=.7)
    draw_geometry(axes[0, 0], domain, "#007f8b", linewidth=2)
    axes[0, 0].set_title("Frozen Body source audit + historical S3 / two holes\nGray outlines are vertex hull supports, not occupancy")
    cells = field["queries"]["provisional_eye"]["variants"][2]["samples"]
    valid = [c for c in cells if c["domain_mask"]]
    scatter = axes[0, 1].scatter([c["x_m"] for c in valid], [c["y_m"] for c in valid],
                                 c=[c["clearance_to_domain_boundary_m"] for c in valid], s=20, cmap="viridis", marker="s")
    draw_geometry(axes[0, 1], domain, "#007f8b", linewidth=1.5)
    fig.colorbar(scatter, ax=axes[0, 1], label="Distance to S3 boundary including holes (m)", shrink=.7)
    axes[0, 1].set_title("Established domain distance channel\n0.25 m samples / zero origin; independent of occupancy")
    for ax, name, title in [(axes[1, 0], "provisional_eye", "Eye diagnostic: 1.55–1.65 m; reference 1.60 m"),
                             (axes[1, 1], "independent_lower_diagnostic", "Independent lower diagnostic: 0.45–0.55 m")]:
        query = field["queries"][name]
        draw_geometry(ax, domain, "#e9edf3", fill=True, linewidth=0)
        draw_geometry(ax, shape(query["clipped_uncertainty_support_geometry"]), "#bd7600", hatch="////", alpha=.65)
        draw_geometry(ax, shape(query["clipped_projection_geometry"]), "#a52c93", fill=True, alpha=.8, linewidth=.5)
        draw_geometry(ax, domain, "#007f8b", linewidth=1.5)
        ax.set_title(f"{title}\nApproximate target {query['clipped_projection_area_m2']:.3f} m²; {len(query['unsupported_in_scope_height_candidate_ids'])} unsupported candidates")
    fig.legend(handles=[Patch(facecolor="#a52c93", label="Eligible-mesh band projection (approximate)"),
                        Patch(edgecolor="#bd7600", facecolor="none", hatch="////", label="Unassessed height candidates / conservative vertex hulls"),
                        Patch(facecolor="#e9edf3", label="Complement is NOT known free; complete field unassessed everywhere")],
               loc="outside lower center", ncol=1, fontsize=10)
    fig.suptitle("B3 PARTIAL DIAGNOSTIC / historical snapshot with verified structural geometry parity\nHuman Level 1 datum 0 m at floor top; complete occupancy and exact plane section unsupported", fontsize=14)
    fig.savefig(out / "real_field_overview.png", dpi=160)
    plt.close(fig)
    # These plots distinguish metres to an approximation from the domain metric.
    for name, query in field["queries"].items():
        fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
        for ax in axes:
            ax.set(xlim=(limits[0] - .5, limits[2] + .5), ylim=(limits[1] - .5, limits[3] + .5), xlabel="World X (m)", ylabel="World Y (m)")
            ax.set_aspect("equal")
            draw_geometry(ax, domain, "#007f8b", linewidth=1.8)
        draw_geometry(axes[0], shape(query["clipped_projection_geometry"]), "#a52c93", fill=True, alpha=.8)
        draw_geometry(axes[0], shape(query["clipped_uncertainty_support_geometry"]), "#bd7600", hatch="////", alpha=.6)
        axes[0].set_title("Magenta: approximate band projection\nOrange hatching: unassessed candidate support")
        valid = [c for c in query["variants"][3]["samples"] if c["domain_mask"] and c["clearance_to_diagnostic_projection_m"] is not None]
        scatter = axes[1].scatter([c["x_m"] for c in valid], [c["y_m"] for c in valid], c=[c["clearance_to_diagnostic_projection_m"] for c in valid], cmap="magma", marker="s", s=20)
        fig.colorbar(scatter, ax=axes[1], label="Distance to RAW diagnostic projection only (m)", shrink=.75)
        axes[1].set_title("0.25 m samples; quarter-spacing shifted origin\nNo complete nearest-physical-occupancy distance")
        band = query["band_z_m"]
        fig.suptitle(f"{name}: world height {band[0]:.2f}–{band[1]:.2f} m / datum 0 m\nPARTIAL: complement is not known free; no walkability, body clearance or visibility", fontsize=14)
        fig.savefig(out / f"{name}_diagnostic.png", dpi=160)
        plt.close(fig)


def build_field(out):
    """Verify frozen lineage and persist actual samples and per-source missingness."""
    index = read_json(CAPTURE / "artifact_index.json")
    for ref in index["files"]:
        actual = file_ref(ROOT / ref["path"])
        assert (actual["sha256"], actual["bytes"]) == (ref["sha256"], ref["bytes"]), ref["path"]
    capture = read_json(CAPTURE / "capture_manifest.json")
    scope = read_json(CAPTURE / "s3_scope.json")
    inventory = read_json(CAPTURE / "scope_inventory.json")["records"]
    qualification = read_json(CAPTURE / "qualification.json")
    read_json(CAPTURE / "height_probes.json")
    parity = read_json(CAPTURE / "structural_parity.json")
    assert qualification["geometry_parity"] is True
    parity_ref = file_ref(ROOT / scope["geometry_parity"]["path"])
    assert (parity_ref["sha256"], parity_ref["bytes"]) == (scope["geometry_parity"]["sha256"], scope["geometry_parity"]["bytes"])
    domain = shape(scope["candidate"]["outline"])
    assert domain.is_valid and len(domain.interiors) == 2 and domain.area == scope["area_recomputed_m2"]
    assert capture["world_units"] == "m" and scope["floor_datum"]["value_m"] == 0
    bands = scope["height_queries"]
    targets = {name: {"projections": [], "supports": [], "records": []} for name in bands}
    source_hulls, source_audit = [], []
    for n, row in enumerate(inventory):
        if row["geometry"] is None:
            source_audit.append({"id": row["id"], "category": row["category"], "status": "excluded_semantic_nonmass"})
            continue
        record = read_json(CAPTURE / row["geometry"]["path"])
        vertices = np.asarray(record["vertices"], dtype=float)
        assert np.isfinite(vertices).all() and record["units"] == "m" and record["transform_applied"] is True
        hull = MultiPoint(vertices[:, :2]).convex_hull
        source_hulls.append(hull)
        audit = {k: row.get(k) for k in ("id", "global_id", "step_id", "ifc_class", "category", "participation", "function", "geometry", "solid_query_eligible", "quality", "observed_z_range_m", "scope")}
        audit["full_height_vertex_hull_audit_geometry"] = mapping(hull)
        audit["geometry_branch"] = "frozen_actual_Body_design_only; canonical_Analysis_policy_unchanged"
        source_audit.append(audit)
        if row["category"] == "support_excluded_from_occupancy":
            audit["status"] = "excluded_support_slab"
            continue
        patch = mesh_patch(record) if row["solid_query_eligible"] else None
        for name, band in bands.items():
            candidate = row["bands"][name]["positive_observed_height_range_overlap"]
            result, projection, support = source_query(row, patch, hull, domain, band, candidate)
            result["id"] = row["id"]
            result["scope_status"] = row["scope"]["status"]
            targets[name]["records"].append(result)
            if projection is not None:
                targets[name]["projections"].append(projection)
            if not support.is_empty:
                targets[name]["supports"].append(support)
        if n % 30 == 0:
            print(f"Processed {n + 1}/{len(inventory)} capture records", flush=True)
    field = {
        "schema": "b3-real-partial-diagnostic-field/v1", "status": "partial_diagnostic_historical_snapshot_only",
        "domain_status": "qualified_horizontal_historical_S3_with_verified_structural_geometry_parity",
        "domain_geometry": mapping(domain), "domain_area_m2": domain.area, "domain_holes": 2,
        "scope_binding": scope["binding"], "domain_frame": scope["frame"], "vertical_extent": "unknown",
        "floor_datum": scope["floor_datum"], "eye_offset_m": 1.6, "eye_world_z_m": 1.6,
        "complete_physical_occupancy_status": "partial_unsupported", "complete_physical_occupancy_geometry": None,
        "exact_plane_section_status": "unsupported", "exact_plane_section_geometry": None,
        "gaussian_group_support_status": "not_available_no_qualified_groups", "source_audit": source_audit,
        "qualification": "all190_global_eligible_includes_support_slab; passing_mesh_flags_not_exactness",
        "source_capture": file_ref(CAPTURE / "capture_manifest.json"), "capture_index": file_ref(CAPTURE / "artifact_index.json"),
        "source_ifc": {"path": capture["source_path"], "bytes": capture["source_ifc_bytes"], "sha256": capture["source_ifc_sha256"]},
        "captured_structural_revision": qualification["current_revision"], "structural_parity": file_ref(CAPTURE / "structural_parity.json"),
        "accepted_synthetic_evidence": file_ref(ROOT / "outputs/design/b3_space_field_exploratory/run_002/result.json"),
        "queries": {},
    }
    for name, target in targets.items():
        projection_union_audit, support_union_audit = {}, {}
        raw = polygonal_union(target["projections"], projection_union_audit)
        support = polygonal_union(target["supports"], support_union_audit)
        records = target["records"]
        query = {"band_z_m": bands[name], "plane_reference_z_m": 1.6 if name == "provisional_eye" else None,
                 "exact_plane_section_status": "unsupported", "query_role": "provisional_eye" if name == "provisional_eye" else "independent_diagnostic_not_production_policy",
                 "projection_status": "partial_approximate_surface_projection_only", "complete_occupancy_status": "partial_unsupported",
                 "projection_union_processing": projection_union_audit, "support_union_processing": support_union_audit,
                 "raw_projection_geometry": mapping(raw), "clipped_projection_geometry": mapping(raw.intersection(domain)),
                 "raw_projection_area_m2": raw.area, "clipped_projection_area_m2": raw.intersection(domain).area,
                 "diagnostic_complement_geometry": mapping(domain.difference(raw)),
                 "complement_role": "not_known_free", "raw_uncertainty_support_geometry": mapping(support),
                 "clipped_uncertainty_support_geometry": mapping(support.intersection(domain)),
                 "uncertainty_support_area_m2": support.intersection(domain).area,
                 "uncertainty_policy": "complete_field_unknown_everywhere; hulls_only_localize_unassessed_source_candidates_not_total_error",
                 "source_records": records, "source_status_counts": dict(Counter(r["status"] for r in records)),
                 "successful_projection_source_ids": [r["id"] for r in records if r["status"] == "diagnostic_projection"],
                 "missing_projection_source_ids": [r["id"] for r in records if r["status"] == "projection_missing"],
                 "unsupported_source_ids": [r["id"] for r in records if r["status"] == "unsupported_mesh"],
                 "unsupported_in_scope_height_candidate_ids": [r["id"] for r in records if r["status"] == "unsupported_mesh" and r["positive_observed_height_range_overlap"] and r["scope_status"] == "positive_area_overlap"],
                 "variants": [sample_variant(domain, raw, support, spacing, (shift * spacing, shift * spacing)) for spacing in (.5, .25) for shift in (0, .25)]}
        assert query["unsupported_in_scope_height_candidate_ids"] == qualification["unsupported_band_candidates"][name]
        field["queries"][name] = query
    write_json(out / "field_samples.json", field)
    render_plans(out, field, source_hulls)
    # The Blender renderer only consumes this manifest and immutable capture files.
    write_json(out / "preview_input.json", {"field": file_ref(out / "field_samples.json"), "capture": file_ref(CAPTURE / "capture_manifest.json"), "source_meshes": capture["inventory"], "domain": mapping(domain), "queries": {name: {k: q[k] for k in ("band_z_m", "clipped_projection_geometry", "clipped_uncertainty_support_geometry")} for name, q in field["queries"].items()}})
    return field


def main():
    """Generate one fresh attempt, then invoke only the approved portable Blender."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    out = CAPTURE / "worker_b" / f"attempt_{args.attempt:03d}"
    out.mkdir(exist_ok=False)
    started = time.time()
    field = build_field(out)
    command = [str(BLENDER), "--background", "--factory-startup", "--python", str(ROOT / "scripts/design/space_field/render_b3_real_field_blender.py"), "--", str(out)]
    with (out / "blender_render.log").open("x", encoding="utf-8") as log:
        render = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, check=False)
    execution = {"host_command": f"pixi run python scripts/design/space_field/run_b3_real_field_diagnostic.py --attempt {args.attempt}",
                 "blender_command": command, "blender_exit_code": render.returncode, "elapsed_seconds": time.time() - started,
                 "image_content_inspection": "pending_actual_image_view", "source_scene_mutation": "none_independent_factory_startup_process"}
    write_json(out / "execution.json", execution)
    references = [file_ref(path) for path in out.iterdir() if path.is_file()]
    write_json(out / "field_visualization_manifest.json", {"schema": "b3-real-field-visualization-manifest/v1",
        "status": field["status"], "capture_index": field["capture_index"], "source_capture": field["source_capture"],
        "source_ifc": field["source_ifc"], "accepted_synthetic_evidence": field["accepted_synthetic_evidence"],
        "inputs": [file_ref(CAPTURE / name) for name in ("qualification.json", "s3_scope.json", "structural_parity.json", "scope_inventory.json", "height_probes.json")],
        "code": [file_ref(path) for path in (Path(__file__), ROOT / "scripts/design/space_field/render_b3_real_field_blender.py", ROOT / "features/geometry_views.py", ROOT / "features/geometry_substitutes.py", SYNTHETIC)],
        "artifacts": references, "execution": execution,
        "review": "STOP FOR B3 REAL-SOURCE FIELD AND VISUAL INSPECTION REVIEW; partial diagnostic does not close B3"})
    print(json.dumps({"output": str(out), "blender_exit_code": render.returncode, "query_status_counts": {n: q["source_status_counts"] for n, q in field["queries"].items()}}), flush=True)
    if render.returncode:
        raise SystemExit(render.returncode)


if __name__ == "__main__":
    main()
