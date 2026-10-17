"""Compare accepted 3D convex proxies with the accepted B3 eye-plane field."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import mapping, shape
import trimesh

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.design.space_field import run_b3_eye_plane_field as EYE
from features.neutral_scene_views import _resolve_boundary_member_ids

PRIOR = EYE.PRIOR
BASE = ROOT / "outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3"
PROXIES = ROOT / "outputs/design/b3_deferred_convex_meshes/run_20261008T225203Z_aa8aaa"
OUTPUT = ROOT / "outputs/design/b3_proxy_eye_plane_comparison"
BOUNDARY_MEMBERSHIP = ROOT / "docs/project/evidence/b3-domain-boundary-membership.json"
QUALIFIED = {"qualified_closed_section", "qualified_empty_section", "valid_empty_below_plane", "valid_empty_above_plane"}


def accepted_inputs():
    """Load only accepted serialized evidence and verify its recorded fingerprints."""
    from features.discrete_space_field import load_discrete_space_field

    # The accepted A loader verifies both baseline payload hashes before this scenario reads them.
    load_discrete_space_field(BASE, spacing_m=.25, origin_offset_m=(0., 0.))
    baseline = PRIOR.read_json(BASE / "field_samples.json")
    sections = PRIOR.read_json(BASE / "source_sections.json")
    manifest = PRIOR.read_json(PROXIES / "artifact_manifest.json")
    expected = {Path(ref["path"]).name: ref for ref in manifest["artifacts"]}
    metadata_path = PROXIES / "mesh_proxies.json"
    actual = PRIOR.file_ref(metadata_path)
    ref = expected[metadata_path.name]
    assert (actual["bytes"], actual["sha256"]) == (ref["bytes"], ref["sha256"])
    metadata = PRIOR.read_json(metadata_path)
    for group in metadata["groups"]:
        path = PROXIES / group["obj"]
        actual = PRIOR.file_ref(path)
        ref = expected[path.name]
        assert (actual["bytes"], actual["sha256"]) == (ref["bytes"], ref["sha256"])
    assert len(sections["records"]) == 358 and baseline["primary_plane_world_z_m"] == EYE.PLANE_Z
    assert {tuple(v["origin_offset_m"]) for v in baseline["variants"] if v["spacing_m"] == .25} >= {(0., 0.)}
    declaration = PRIOR.read_json(BOUNDARY_MEMBERSHIP)
    boundary_membership(baseline, sections, declaration)
    return baseline, sections, metadata, declaration


def boundary_membership(baseline, sections, declaration):
    """Bind human membership to this frozen scope and uniquely retained source IDs."""
    if (declaration.get("schema") != "b3-selected-domain-boundary-membership/v1"
            or declaration.get("scope_binding") != baseline["scope_binding"]
            or declaration.get("baseline_source_sections_ref") != baseline["source_sections"]
            or declaration.get("authority") != "explicit_user_instruction"):
        raise ValueError("boundary_membership_scope_or_source_mismatch")
    records = sections["records"]
    resolved, diagnostics = _resolve_boundary_member_ids(
        declaration.get("boundary_member_source_ids"),
        ((row["id"], row.get("source_id")) for row in records),
        {row["id"] for row in records},
    )
    if not resolved or len(resolved) != len(declaration["boundary_member_source_ids"]):
        raise ValueError("boundary_member_identity_unresolved")
    return resolved, diagnostics


def proxy_section(group):
    """Transport one ordinary OBJ without mesh processing or coordinate repair."""
    scene = trimesh.load_scene(PROXIES / group["obj"], file_type="obj", process=False,
                               maintain_order=True, group_material=False, skip_materials=True)
    assert len(scene.geometry) == 1
    mesh = next(iter(scene.geometry.values()))
    assert isinstance(mesh, trimesh.Trimesh)
    checks = group["generated_mesh_checks"]
    assert len(mesh.vertices) == checks["vertex_count"] and len(mesh.faces) == checks["triangle_count"]
    record = {"id": f"proxy:{group['id']}", "units": "m", "transform_applied": True,
              "vertices": mesh.vertices.tolist(), "triangles": mesh.faces.tolist(),
              "is_closed": bool(mesh.is_watertight), "is_manifold": bool(mesh.is_watertight)}
    result = EYE.section_source(record)
    return {"id": record["id"], "status": result["status"], **result,
            "evidence_kind": "generated_3d_convex_mesh_section_comparison_only",
            "proxy_role": group["proxy_role"], "analysis_enrollment": "deferred_excluded",
            "represented_source_ids": [f"live-step-{s['step_id']}" for s in group["sources"]],
            "original_source_refs": group["sources"], "proxy_obj_ref": PRIOR.file_ref(PROXIES / group["obj"]),
            "proxy_metadata_ref": PRIOR.file_ref(PROXIES / "mesh_proxies.json"),
            "comparison_override": "replace represented-source uncertainty only if this proxy section qualifies",
            "approximation_limit": "User-selected 3D convex hull fills original gaps and concavities; no exact original material, orientation, or canonical enrollment claim",
            "obj_transport": {"process": False, "maintain_order": True, "vertex_count": len(mesh.vertices),
                              "triangle_count": len(mesh.faces), "is_watertight": bool(mesh.is_watertight),
                              "is_winding_consistent": bool(mesh.is_winding_consistent)}}


def scenario_geometry(original, qualified_ids, boundary_member_ids):
    """Build active original supports and ambiguity boundaries for this scope."""
    supports = [(row["id"], None if row["unknown_support_geometry"] is None
                 else shape(row["unknown_support_geometry"]))
                for row in original
                if "unknown_support_geometry" in row
                and row["id"] not in qualified_ids | boundary_member_ids]
    supports = [(sid, support) for sid, support in supports if support is None or not support.is_empty]
    boundaries = [shape(row["occupied_geometry"]).boundary for row in original
                  if row["id"] not in boundary_member_ids
                  and row.get("occupied_geometry") is not None
                  and not shape(row["occupied_geometry"]).is_empty]
    return supports, boundaries


def comparison_field(baseline, sections, proxy_records, declaration):
    """Apply qualified proxies and exact selected-boundary membership to one scenario."""
    original = sections["records"]
    by_id = {row["id"]: row for row in original}
    assert len(by_id) == 358 and len(proxy_records) == 3
    represented = [sid for proxy in proxy_records for sid in proxy["represented_source_ids"]]
    assert len(set(represented)) == 7 and all(sid in by_id for sid in represented)
    member_ids, membership_diagnostics = boundary_membership(baseline, sections, declaration)
    qualified_ids = {sid for proxy in proxy_records if proxy["status"] in QUALIFIED
                     for sid in proxy["represented_source_ids"]}
    overrides = [{"source_id": sid, "proxy_id": proxy["id"], "original_status": by_id[sid]["status"],
                  "scenario_uncertainty_omitted": sid in qualified_ids,
                  "reason": "qualified proxy section" if sid in qualified_ids else "proxy qualification failed; original uncertainty retained"}
                 for proxy in proxy_records for sid in proxy["represented_source_ids"]]
    domain = shape(baseline["domain_geometry"])
    # Reuse serialized per-source sections so a selected boundary member can
    # leave occupancy without recomputing any original mesh or source error.
    occupied_parts = [shape(row["occupied_geometry"]) for row in original
                      if row["id"] not in member_ids and row.get("occupied_geometry") is not None]
    occupied_parts += [shape(p["occupied_geometry"]) for p in proxy_records
                       if p["status"] in QUALIFIED and p["occupied_geometry"] is not None]
    raw_audit, unknown_audit = {}, {}
    raw = PRIOR.polygonal_union(occupied_parts, raw_audit)
    supports, boundaries = scenario_geometry(original, qualified_ids, member_ids)
    unknown = PRIOR.polygonal_union([domain if support is None else support for _, support in supports], unknown_audit)
    boundaries += [shape(p["occupied_geometry"]).boundary for p in proxy_records
                   if p["status"] in QUALIFIED and p["occupied_geometry"] is not None
                   and not shape(p["occupied_geometry"]).is_empty]
    variants = [EYE.sample_variant(domain, raw, supports, boundaries, v["spacing_m"],
                                   tuple(v["origin_offset_m"])) for v in baseline["variants"]]
    for before, after in zip(baseline["variants"], variants):
        # Reuse accepted lattice/domain evidence and guard against drift in unchanged sample channels.
        assert [(s["cell_i"], s["cell_j"], s["x_m"], s["y_m"], s["domain_mask"],
                 s["distance_to_domain_boundary_m"]) for s in before["samples"]] == [
                 (s["cell_i"], s["cell_j"], s["x_m"], s["y_m"], s["domain_mask"],
                  s["distance_to_domain_boundary_m"]) for s in after["samples"]]
    field = {**baseline, "status": "design_only_proxy_comparison_not_enrolled_owner_review_required",
             "algorithm": {**baseline["algorithm"], "identity": "accepted original sections plus three process=False OBJ proxy sections via existing exact world-z=1.6m section_source and sample_variant",
                           "endpoint_policy": "Accepted original indexed-edge sections are reused; three OBJ proxies use their own indexed edges without weld, snap, or repair",
                           "probe_policy": "Accepted original parity results are reused; proxy sections use the existing three-ray parity and shell audits",
                           "qualification": "Accepted original section statuses are historical; only the three OBJ proxy sections are newly qualified in this scenario",
                           "limit": "Generated convex substitutes qualify only this comparison; original source material and complete physical occupancy remain unresolved"},
             "baseline_source_counts": baseline["source_counts"],
             "source_counts": dict(Counter(r["status"] for r in [*original, *proxy_records])),
             "source_total_body_meshes": baseline["source_total_body_meshes"],
             "proxy_record_count": 3, "original_source_record_count": 358,
             "scenario_overrides": overrides,
             "domain_boundary_policy": {
                 "authority": declaration["authority"], "local_date": declaration["local_date"],
                 "policy": declaration["policy"], "membership_basis": declaration["membership_basis"],
                 "scope_binding": declaration["scope_binding"],
                 "baseline_source_sections_ref": declaration["baseline_source_sections_ref"],
                 "boundary_member_source_ids": declaration["boundary_member_source_ids"],
                 "resolved_record_ids": sorted(member_ids), "identity_diagnostics": membership_diagnostics,
                 "declaration_ref": PRIOR.file_ref(BOUNDARY_MEMBERSHIP)},
             "baseline_field_ref": PRIOR.file_ref(BASE / "field_samples.json"),
             "baseline_sections_ref": PRIOR.file_ref(BASE / "source_sections.json"),
             "proxy_metadata_ref": PRIOR.file_ref(PROXIES / "mesh_proxies.json"),
             "source_integrity": {"historical_baseline_source_integrity": baseline["source_integrity"],
                                  "comparison_input_checks": "A loader verified accepted baseline payload hashes; accepted proxy manifest fingerprints verified for metadata and three OBJ files; original inventory was not rechecked"},
             "raw_qualified_occupied_geometry": mapping(raw),
             "clipped_qualified_occupied_geometry": mapping(raw.intersection(domain)),
             "raw_qualified_occupied_area_m2": raw.area,
             "clipped_qualified_occupied_area_m2": raw.intersection(domain).area,
             "raw_unknown_support_geometry": mapping(unknown),
             "clipped_unknown_support_geometry": mapping(unknown.intersection(domain)),
             "clipped_unknown_support_area_m2": unknown.intersection(domain).area,
             "qualified_occupied_union_audit": raw_audit, "unknown_support_union_audit": unknown_audit,
             "channel_contract": {**baseline["channel_contract"],
                                  "occupancy_value": "Comparison-only True: qualified original or generated proxy interior; False: conditional empty after qualified scenario overrides; null: unknown/outside",
                                  "unknown_propagation": "Qualified proxies override seven represented originals; exact selected-domain boundary members contribute no interior uncertainty; all other original support is retained",
                                  "distance_to_raw_qualified_occupied_subset_m": "Unsigned metres to original plus qualified proxy raw subset; comparison target incomplete, not physical clearance",
                                  "complete_physical_clearance_m": "null; original physical completeness remains unavailable",
                                  "Gaussian": "not_available_no_qualified_groups"},
             "complete_occupancy_geometry": None,
             "sources": [*baseline["sources"], PRIOR.file_ref(BASE / "field_samples.json"),
                         PRIOR.file_ref(BASE / "source_sections.json"), PRIOR.file_ref(PROXIES / "mesh_proxies.json"),
                         PRIOR.file_ref(BOUNDARY_MEMBERSHIP),
                         *(p["proxy_obj_ref"] for p in proxy_records)],
             "code": [*baseline["code"], PRIOR.file_ref(Path(__file__)),
                      PRIOR.file_ref(ROOT / "features/neutral_scene_views.py")],
             "variants": variants}
    assert all(row == by_id[row["id"]] for row in original)
    return field, {**sections, "records": [*original, *proxy_records]}


def render_preview(path, baseline, comparison):
    """Show accepted and proxy scenario samples side by side on the same S3 frame."""
    domain = shape(baseline["domain_geometry"])
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), sharex=True, sharey=True)
    palette = {"established_empty_under_qualification": "#259790", "unknown": "#d97808",
               "established_occupied": "#a60076", "outside_domain": "#cbd2d5"}
    for ax, field, title in zip(axes, (baseline, comparison), ("Accepted baseline", "3D convex proxy comparison")):
        EYE.PRIOR.draw_geometry(ax, domain, "#007f88", linewidth=1.2)
        variant = next(v for v in field["variants"] if v["spacing_m"] == .25 and v["origin_offset_m"] == [0., 0.])
        for status, color in palette.items():
            points = [(s["x_m"], s["y_m"]) for s in variant["samples"] if s["status"] == status]
            if points:
                ax.scatter(*zip(*points), s=5, c=color, label=f"{status}: {len(points)}", rasterized=True)
        ax.set_title(title)
        ax.set_aspect("equal")
        ax.set_xlabel("World X (m)")
        ax.legend(loc="upper right", fontsize=7, markerscale=2)
    axes[0].set_ylabel("World Y (m)")
    fig.suptitle("World z=1.6 m | 0.25 m lattice, origin [0,0] | comparison only")
    fig.text(.5, .02, "Confirmed selected-domain boundary members leave interior occupancy and uncertainty; original source facts remain. No canonical enrollment or complete clearance.", ha="center")
    fig.tight_layout(rect=(0, .04, 1, .95))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    """Write one unique, independently loadable comparison package and preview."""
    assert __debug__, "Comparison lineage checks require ordinary Python execution"
    out = OUTPUT / (datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ_") + uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    execution = {"status": "running", "output": str(out)}
    try:
        baseline, sections, metadata, declaration = accepted_inputs()
        proxies = [proxy_section(group) for group in metadata["groups"]]
        field, records = comparison_field(baseline, sections, proxies, declaration)
        PRIOR.write_json(out / "source_sections.json", records)
        field["source_sections"] = PRIOR.file_ref(out / "source_sections.json")
        PRIOR.write_json(out / "field_samples.json", field)
        render_preview(out / "baseline_vs_proxy_025_zero.png", baseline, field)
        execution.update(status="exit_0", proxy_statuses={p["id"]: p["status"] for p in proxies},
                         baseline_counts=baseline["variants"][2]["status_counts"],
                         comparison_counts=field["variants"][2]["status_counts"],
                         clipped_occupied_area_m2=field["clipped_qualified_occupied_area_m2"],
                         clipped_unknown_support_area_m2=field["clipped_unknown_support_area_m2"])
    except Exception as error:
        execution.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        PRIOR.write_json(out / "execution.json", execution)
        PRIOR.write_json(out / "artifact_manifest.json", {"schema": "b3-primary-eye-artifacts/v1",
                         "status": execution["status"], "artifacts": [PRIOR.file_ref(p) for p in out.iterdir() if p.is_file()],
                         "execution": execution})
        print(json.dumps(execution, indent=2), flush=True)


if __name__ == "__main__":
    main()
