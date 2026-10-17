"""Build a design-only, qualified-subset field on the fixed world z=1.6 m plane."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import shapely
import trimesh
from shapely.geometry import GeometryCollection, LineString, MultiPoint, Point, mapping, shape
from shapely.ops import polygonize_full, unary_union

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
import run_b3_real_field_diagnostic as PRIOR
from features.geometry_substitutes import MassPatch
from features.section_views import exact_plane_section

PLANE_Z = 1.6
EMPTY = GeometryCollection()


def section_source(record):
    """Keep the historical B3 record interface over shared MassPatch sectioning."""
    patch = MassPatch(
        id=record.get("id", "unidentified-mesh"), source_geometry_id=record.get("id", "unidentified-mesh"),
        vertices=record.get("vertices", ()), triangle_indices=record.get("triangles", ()),
        is_closed=record.get("is_closed"), is_manifold=record.get("is_manifold"),
        provenance={"units": record.get("units"), "world_transform_applied": record.get("transform_applied")},
    )
    return exact_plane_section(patch, world_z_m=PLANE_Z)


def sample_variant(domain, occupied, unknown_supports, source_boundaries, spacing, origin):
    """Sample the accepted indexed lattice with three-state qualified-geometry evidence."""
    samples = []
    for i, j, x, y in PRIOR.ACCEPTED._sample_grid(domain, spacing, origin):
        point = Point(x, y)
        inside = bool(domain.covers(point))
        uncertain_ids = [sid for sid, support in unknown_supports if support is None or support.covers(point)] if inside else []
        boundary = inside and any(geometry.covers(point) for geometry in source_boundaries)
        positive = inside and occupied.contains(point)
        # Positive established mass survives another source's missingness; negative evidence cannot become free there.
        value = True if positive else None if not inside or uncertain_ids or boundary else False
        state = "outside_domain" if not inside else "established_occupied" if positive else "unknown" if value is None else "established_empty_under_qualification"
        samples.append({"cell_i": i, "cell_j": j, "x_m": x, "y_m": y, "world_z_m": PLANE_Z,
                        "domain_mask": inside, "qualified_occupied_subset_mask": bool(positive),
                        "unresolved_source_ids": uncertain_ids, "unresolved_source_support_mask": bool(uncertain_ids),
                        "section_boundary_ambiguity_mask": bool(boundary), "occupancy_value": value,
                        "known_free_under_qualification": None if value is None else not value,
                        "unknown_mask": inside and value is None, "status": state,
                        "distance_to_domain_boundary_m": point.distance(domain.boundary) if inside else None,
                        "distance_to_raw_qualified_occupied_subset_m": point.distance(occupied) if inside and not occupied.is_empty else None,
                        "complete_physical_clearance_m": None})
    return {"spacing_m": spacing, "origin_offset_m": list(origin), "sample_count": len(samples),
            "domain_sample_count": sum(s["domain_mask"] for s in samples),
            "status_counts": dict(Counter(s["status"] for s in samples)), "samples": samples}


def render_primary(out, field, sources):
    """Show the primary plane, holes and uncertainty over actual frozen vertex audits."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    domain = shape(field["domain_geometry"])
    occupied = shape(field["clipped_qualified_occupied_geometry"])
    support = shape(field["clipped_unknown_support_geometry"])
    fig, ax = plt.subplots(figsize=(14, 9))
    for source in sources:
        points = np.asarray(source.get("vertex_audit_xy", []))
        if len(points):
            ax.scatter(points[:, 0], points[:, 1], s=.4, color="#8b9198", alpha=.25, rasterized=True)
    PRIOR.draw_geometry(ax, domain, "#e8f2f3", fill=True)
    PRIOR.draw_geometry(ax, support, "#d97808", fill=True, hatch="///", alpha=.30)
    PRIOR.draw_geometry(ax, occupied, "#a60076", fill=True, linewidth=1.6)
    PRIOR.draw_geometry(ax, domain, "#007f88", linewidth=1.3)
    variant = field["variants"][2]
    for state, color in (("established_empty_under_qualification", "#259790"), ("unknown", "#d97808"), ("established_occupied", "#a60076")):
        points = [(s["x_m"], s["y_m"]) for s in variant["samples"] if s["status"] == state]
        if points:
            ax.scatter(*np.asarray(points).T, s=4, color=color, alpha=.55)
    ax.set_aspect("equal", adjustable="box")
    xmin, ymin, xmax, ymax = domain.bounds
    ax.set_xlim(xmin - .65, xmax + .65)
    ax.set_ylim(ymin - .65, ymax + .65)
    ax.set_xlabel("World X (m)")
    ax.set_ylabel("World Y (m)")
    ax.set_title("PRIMARY eye plane: world z = 1.6 m\nHistorical S3 / two holes / qualified Body subset and localized unknown")
    ax.legend(handles=[Patch(color="#007f88", label="Historical S3 boundary, including holes"),
                       Patch(color="#a60076", label="Qualified occupied evidence (may be empty/tiny)"),
                       Patch(facecolor="#d97808", alpha=.35, hatch="///", label="Unresolved source support; not occupancy"),
                       Patch(color="#259790", label="Empty point under declared qualification"),
                       Patch(color="#8b9198", label="Frozen actual Body vertex audit; not occupancy")], loc="lower left", fontsize=9)
    ax.grid(alpha=.2)
    fig.text(.07, .025, "0.25 m zero-shift point samples. Boundary contacts stay unknown. Raw-subset distance is not complete physical clearance.", fontsize=10)
    fig.tight_layout(rect=(0, .045, 1, 1))
    fig.savefig(out / "primary_eye_plane.png", dpi=160)
    plt.close(fig)


def build_field(out):
    """Check frozen lineage once, then write per-source sections and complete point samples."""
    index = PRIOR.read_json(PRIOR.CAPTURE / "artifact_index.json")
    for ref in index["files"]:
        actual = PRIOR.file_ref(ROOT / ref["path"])
        assert (actual["bytes"], actual["sha256"]) == (ref["bytes"], ref["sha256"]), ref["path"]
    capture = PRIOR.read_json(PRIOR.CAPTURE / "capture_manifest.json")
    scope = PRIOR.read_json(PRIOR.CAPTURE / "s3_scope.json")
    inventory = PRIOR.read_json(PRIOR.CAPTURE / "scope_inventory.json")["records"]
    qualification = PRIOR.read_json(PRIOR.CAPTURE / "qualification.json")
    domain = shape(scope["candidate"]["outline"])
    assert domain.is_valid and len(domain.interiors) == 2 and domain.area == 206.5209234821732
    assert capture["world_units"] == "m" and scope["floor_datum"]["value_m"] == 0
    sources, occupied_parts, supports, boundaries = [], [], [], []
    for row in inventory:
        base = {key: row.get(key) for key in ("id", "step_id", "global_id", "name", "ifc_class", "category", "participation", "geometry", "quality", "scope", "solid_query_eligible")}
        if row["geometry"] is None or row["category"] == "support_excluded_from_occupancy":
            base["status"] = "excluded_support_slab" if row["geometry"] else "excluded_semantic_nonmass"
            sources.append(base)
            continue
        result = section_source(PRIOR.read_json(PRIOR.CAPTURE / row["geometry"]["path"]))
        base.update(result)
        sources.append(base)
        if result["occupied_geometry"] is not None:
            geometry = shape(result["occupied_geometry"])
            occupied_parts.append(geometry)
            if not geometry.is_empty:
                boundaries.append(geometry.boundary)
            base["clipped_occupied_area_m2"] = geometry.intersection(domain).area
        support = None if result["unknown_support_geometry"] is None else shape(result["unknown_support_geometry"])
        if support is None or not support.is_empty:
            supports.append((row["id"], support))
        if len(sources) % 40 == 0:
            print(f"Qualified {len(sources)}/{len(inventory)} source records", flush=True)
    occupied_audit, support_audit = {}, {}
    raw = PRIOR.polygonal_union(occupied_parts, occupied_audit)
    unknown = PRIOR.polygonal_union([domain if support is None else support for _, support in supports], support_audit)
    clipped = raw.intersection(domain)
    clipped_unknown = unknown.intersection(domain)
    assert clipped.is_valid and clipped_unknown.is_valid
    prior_candidates = qualification["unsupported_band_candidates"]["provisional_eye"]
    plane_candidates = [r["id"] for r in sources if r.get("crossing_triangle_count", 0) and r.get("solid_query_eligible") is False and r["scope"]["status"] == "positive_area_overlap"]
    variants = [sample_variant(domain, raw, supports, boundaries, spacing, (shift * spacing, shift * spacing)) for spacing in (.5, .25) for shift in (0, .25)]
    source_counts = dict(Counter(r["status"] for r in sources))
    field = {
        "schema": "b3-primary-eye-plane-discrete-field/v1", "status": "design_only_partial_qualified_subset_owner_review_required",
        "plane_rule": "IFC storey-bound datum plus eye-height offset is PRIMARY; no competing height", "storey_step": 13,
        "floor_datum": scope["floor_datum"], "eye_height_offset_m": 1.6, "primary_plane_world_z_m": PLANE_Z,
        "units": "m", "frame": scope["frame"], "scope_binding": scope["binding"], "domain_geometry": mapping(domain),
        "domain_area_m2": domain.area, "domain_holes": 2, "current_live_binding": "not_rebound", "vertical_extent": "unknown",
        "algorithm": {"identity": "single intersection per shared original indexed edge + polygonize_full + existing parity ray primitives; raw private-helper failures retained; trimesh quality only",
                      "trimesh_version": trimesh.__version__, "shapely_version": shapely.__version__, "numpy_version": np.__version__,
                      "endpoint_policy": "one intersection per sorted original indexed edge; exact float equality; no proximity weld/snap/closure or alternative slice fallback",
                      "vertex_contact_guard_m": 1e-9, "probe_policy": "three existing directions; deduplicate only within original connected shell; combine only audited disjoint plane interiors; each shell must be unanimous; whole-object failure probes retained",
                      "qualification": "finite indexed geometry entirely above/below proves plane absence while retaining degeneracy separately; crossing qualification requires nondegenerate triangles, capture closed/manifold AND independent indexed watertight/consistent winding, complete degree-2 section with no residuals, valid planar faces, no ambiguous compound-shell interiors, unanimous parity",
                      "limit": "Floating-point geometric qualification, not certified exact arithmetic or 3D self-intersection certification; Body mass branch only, canonical Analysis policy unchanged"},
        "source_counts": source_counts, "source_total_body_meshes": sum(bool(r.get("geometry")) for r in sources),
        "prior_eye_band_unsupported_candidates": prior_candidates, "actual_plane_crossing_prior_unsupported_in_scope_ids": plane_candidates,
        "prior_band_candidates_without_plane_crossing": [sid for sid in prior_candidates if sid not in plane_candidates],
        "raw_qualified_occupied_geometry": mapping(raw), "clipped_qualified_occupied_geometry": mapping(clipped),
        "raw_qualified_occupied_area_m2": raw.area, "clipped_qualified_occupied_area_m2": clipped.area,
        "raw_unknown_support_geometry": mapping(unknown), "clipped_unknown_support_geometry": mapping(clipped_unknown),
        "clipped_unknown_support_area_m2": clipped_unknown.area, "qualified_occupied_union_audit": occupied_audit,
        "unknown_support_union_audit": support_audit, "complete_occupancy_geometry": None,
        "channel_contract": {"occupancy_value": "True: qualified interior evidence; False: empty under qualification only with no unresolved support or section boundary; null: unknown/outside",
                             "unknown_propagation": "unresolved source actual XY hull only localizes uncertainty; invalid missing support makes entire domain unknown; positive evidence remains positive",
                             "negative_limit": "No known-free claim where unresolved source support covers the point. Outside is separately masked.",
                             "boundary": "Qualified per-source polygon boundaries stay ambiguous unless another qualified interior establishes positive evidence",
                             "distance_to_raw_qualified_occupied_subset_m": "Unsigned metres to raw subset including outside-domain mass; target incomplete. Null for empty target/outside. Not complete physical clearance.",
                             "distance_to_domain_boundary_m": "Independent unsigned metres to historical S3 exterior or either hole; outside null",
                             "complete_physical_clearance_m": "null; incomplete source qualification", "Gaussian": "not_available_no_qualified_groups"},
        "sources": [PRIOR.file_ref(PRIOR.CAPTURE / name) for name in ("artifact_index.json", "capture_manifest.json", "scope_inventory.json", "s3_scope.json", "qualification.json", "structural_parity.json")],
        "code": [PRIOR.file_ref(Path(__file__)), PRIOR.file_ref(ROOT / "features/geometry_views.py"), PRIOR.file_ref(ROOT / "features/geometry_substitutes.py"), PRIOR.file_ref(PRIOR.SYNTHETIC)],
        "previous_band_field": PRIOR.file_ref(PRIOR.CAPTURE / "worker_b/attempt_004/field_samples.json"),
        "accepted_synthetic_evidence": PRIOR.file_ref(ROOT / "outputs/design/b3_space_field_exploratory/run_002/result.json"),
        "source_integrity": {"immutable_index_entries_checked": len(index["files"]), "source_geometry_rescaled": False},
        "variants": variants}
    PRIOR.write_json(out / "source_sections.json", {"schema": "b3-primary-eye-source-sections/v1", "primary_plane_world_z_m": PLANE_Z, "records": sources})
    field["source_sections"] = PRIOR.file_ref(out / "source_sections.json")
    PRIOR.write_json(out / "field_samples.json", field)
    render_primary(out, field, sources)
    PRIOR.write_json(out / "preview_input.json", {"capture": PRIOR.file_ref(PRIOR.CAPTURE / "capture_manifest.json"),
                     "field": PRIOR.file_ref(out / "field_samples.json"), "source_meshes": capture["inventory"],
                     "domain": mapping(domain), "occupied": mapping(clipped), "unknown": mapping(clipped_unknown)})
    return field


def main():
    """Create one unique run and render only a genuinely supported primary-plane field."""
    out = ROOT / "outputs/design/b3_eye_plane_field" / (datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ_") + uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    print(f"OUTPUT={out}", flush=True)
    field = build_field(out)
    execution = {"field_generation": "exit_0", "blender_exit_code": None, "image_content_inspection": "pending"}
    if field["source_counts"].get("qualified_closed_section", 0) or field["source_counts"].get("qualified_empty_section", 0):
        renderer = Path(__file__).with_name("render_b3_eye_plane_field.py")
        command = [str(PRIOR.BLENDER), "--background", "--factory-startup", "--python", str(renderer), "--", str(out)]
        with (out / "blender_stdout.log").open("x", encoding="utf-8") as stdout, (out / "blender_stderr.log").open("x", encoding="utf-8") as stderr:
            run = subprocess.run(command, stdout=stdout, stderr=stderr, check=False)
        execution.update(blender_command=command, blender_exit_code=run.returncode)
    PRIOR.write_json(out / "execution.json", execution)
    PRIOR.write_json(out / "artifact_manifest.json", {"schema": "b3-primary-eye-artifacts/v1", "status": field["status"],
                     "artifacts": [PRIOR.file_ref(p) for p in out.iterdir() if p.is_file()], "execution": execution})
    print(json.dumps({"out": str(out), "source_counts": field["source_counts"],
                      "raw_qualified_area_m2": field["raw_qualified_occupied_area_m2"], "clipped_qualified_area_m2": field["clipped_qualified_occupied_area_m2"],
                      "unknown_support_area_m2": field["clipped_unknown_support_area_m2"],
                      "variant_counts": [v["status_counts"] for v in field["variants"]], "execution": execution}, indent=2), flush=True)
    return 0 if execution["blender_exit_code"] in (None, 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
