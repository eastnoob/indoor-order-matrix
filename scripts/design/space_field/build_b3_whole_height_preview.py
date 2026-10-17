"""Project locked B3 meshes and render an isolated whole-height plan preview."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import warnings

from shapely.errors import GEOSException
from shapely.geometry import GeometryCollection, MultiPoint, Point, mapping, shape

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from features.geometry_substitutes import mass_patch_from_mesh
from features.geometry_views import component_shape, plan_projection
from features.scene_contract import MeshGeometry3D
from features.section_views import polygonal_union

BASE = ROOT / "outputs/design/b3_shared_occupancy_enrollment"
PACKAGE = BASE / "run_20261009T142454Z_0d7308"
CAPTURE = ROOT / "outputs/design/b3_real_source_field/run_001"
BLENDER = Path("D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")
MANIFEST_SHA256 = "7029c01cf0883ce30819194aa75f66bbb6d991140794c704632abe067a777118"


def sha256(path):
    """Fingerprint the frozen inputs and new output artifacts."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    """Write finite preview data without replacing an existing artifact."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def frozen_mesh(row, fingerprints):
    """Load authenticated world-metre arrays without a second transform."""
    reference = row["geometry"]
    path = (CAPTURE / reference["path"]).resolve()
    if not path.is_relative_to(CAPTURE):
        raise ValueError("Capture mesh path escaped the frozen root")
    raw = path.read_bytes()
    if len(raw) != reference["bytes"] or hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError(f"Frozen mesh fingerprint mismatch: {row['id']}")
    fingerprints[str(path)] = reference["sha256"]
    record = json.loads(raw)
    assert record["units"] == "m" and record["transform_applied"] is True
    return MeshGeometry3D(
        id=row["id"], vertices=record["vertices"], triangle_indices=record["triangles"],
        normals=(), is_manifold=record["is_manifold"], is_closed=record["is_closed"],
        local_to_world_provenance={"world_transform_applied": True, "capture_sha256": reference["sha256"]},
        source_representation_id=record["representation_id"],
        tessellation_settings=record["tessellation_settings"], units="m",
    )


def build_input(fingerprints):
    """Derive one plan representative per selected source and retain failed supports."""
    field, sections, audit, transport = [json.loads((PACKAGE / name).read_text(encoding="utf-8"))
                                      for name in ("field_samples.json", "source_sections.json",
                                                   "selection_audit.json", "transport_audit.json")]
    capture_ref = next(ref for ref in field["sources"] if ref["path"].endswith("capture_manifest.json"))
    capture_path = ROOT / capture_ref["path"]
    assert capture_path.stat().st_size == capture_ref["bytes"]
    assert sha256(capture_path) == capture_ref["sha256"]
    fingerprints[str(capture_path)] = capture_ref["sha256"]
    rows = {row["id"]: row for row in sections["records"]}
    furniture_ids = {key for key, row in rows.items() if row.get("ifc_class") == "IfcFurniture"}
    selected = set(audit["selected_source_ids"])
    proxy_ids = set(audit["proxy_target_ids"])
    represented = {owner for key in proxy_ids for owner in rows[key]["represented_source_ids"]}
    assert len(furniture_ids) == 95 and furniture_ids <= selected
    assert len(proxy_ids) == 3 and len(represented) == 7
    assert not selected & represented and not selected & set(audit["unknown_source_ids"])
    assert audit["boundary_scoped_ids"] == ["live-step-6231"]
    assert "live-step-6231" not in selected
    domain = shape(field["domain_geometry"])
    assert domain.is_valid and len(domain.interiors) == 2
    proxy_meshes = {mesh["id"]: MeshGeometry3D.from_dict(mesh) for mesh in transport["proxy_meshes"]}
    sources = {source["id"]: source for source in transport["source_objects"]}
    projections, failures, unknowns = [], [], []
    positives, furniture_shapes = [], []
    for index, source_id in enumerate(sorted(selected), 1):
        row = rows[source_id]
        mesh = (proxy_meshes[sources[source_id]["geometry_refs"][0]] if source_id in proxy_ids
                else frozen_mesh(row, fingerprints))
        kind = ("chair" if row.get("name", "").startswith("CHAIR_") else "table") if source_id in furniture_ids else (
            "proxy" if source_id in proxy_ids else "physical_context")
        record = {"id": source_id, "name": row.get("name", source_id), "kind": kind,
                  "ifc_class": row.get("ifc_class"), "previous_eye_section_status": row["status"],
                  "height_range_m": [min(p[2] for p in mesh.vertices), max(p[2] for p in mesh.vertices)],
                  "represented_source_ids": row.get("represented_source_ids", [])}
        # Whole-height selection reuses the locked enrollment identities, not its eye-plane emptiness.
        with warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter("always")
            try:
                projection = plan_projection(mass_patch_from_mesh(mesh), height_band=None)
                geometry = component_shape(projection.components)
                if projection.uncertainty or geometry is None or geometry.is_empty or not geometry.is_valid:
                    raise ValueError(projection.uncertainty or "invalid_or_empty_plan_projection")
            except (GEOSException, ValueError) as error:
                record.update(status="unknown_projection_failure", error=str(error), error_type=type(error).__name__)
                failures.append(record)
                # A vertex hull is a conservative unknown support, never replacement occupied mass.
                support = MultiPoint([p[:2] for p in mesh.vertices]).convex_hull
                unknowns.append({"id": source_id, "reason": "projection_failure", "geometry": mapping(support)})
            else:
                record.update(status="projected", geometry=mapping(geometry), area_m2=geometry.area,
                              component_count=len(projection.components),
                              numerical_retry_warnings=[str(item.message) for item in notices])
                projections.append(record)
                positives.append(geometry)
                if source_id in furniture_ids:
                    furniture_shapes.append(geometry)
        if index % 40 == 0:
            print(f"Projected {index}/{len(selected)} selected records", flush=True)
    # Frozen unqualified sources stay unknown even if their surface could be projected.
    for source_id in audit["unknown_source_ids"]:
        mesh = frozen_mesh(rows[source_id], fingerprints)
        support = MultiPoint([p[:2] for p in mesh.vertices]).convex_hull
        unknowns.append({"id": source_id, "reason": "frozen_unqualified_open_or_nonmanifold", "geometry": mapping(support)})
    boundary_mesh = frozen_mesh(rows["live-step-6231"], fingerprints)
    boundary_support = MultiPoint([p[:2] for p in boundary_mesh.vertices]).convex_hull
    occupancy = polygonal_union(positives)
    furniture = polygonal_union(furniture_shapes)
    unknown = polygonal_union([shape(row["geometry"]) for row in unknowns])
    clipped = occupancy.intersection(domain)
    complement = domain.difference(occupancy)
    conditional_free = complement.difference(unknown)
    clipped_unknown = unknown.intersection(domain)
    assert abs(domain.area - clipped.area - complement.area) < 1e-8
    assert conditional_free.intersection(occupancy).area < 1e-10
    assert conditional_free.intersection(unknown).area < 1e-10
    assert len(projections) + len(failures) == len(selected) == 343
    kinds = Counter(("chair" if rows[key]["name"].startswith("CHAIR_") else "table") for key in furniture_ids)
    assert kinds == {"chair": 58, "table": 37}
    successful_furniture = [row for row in projections if row["id"] in furniture_ids]
    failed_furniture = [row for row in failures if row["id"] in furniture_ids]
    assert len(successful_furniture) + len(failed_furniture) == 95
    stats = {"furniture_count": 95, "chair_count": kinds["chair"], "table_count": kinds["table"],
             "furniture_projection_success_count": len(successful_furniture),
             "furniture_projection_failure_count": len(failed_furniture),
             "selected_record_count": len(selected), "projection_success_count": len(projections),
             "projection_failure_count": len(failures), "proxy_count": 3, "represented_owner_count": 7,
             "numerical_retry_source_ids": [r["id"] for r in projections if r["numerical_retry_warnings"]],
             "domain_area_m2": domain.area, "furniture_footprint_union_area_m2": furniture.area,
             "clipped_furniture_footprint_union_area_m2": furniture.intersection(domain).area,
             "clipped_whole_height_occupancy_area_m2": clipped.area,
             "domain_minus_occupancy_conditional_free_area_m2": complement.area,
             "unknown_masked_conditional_free_area_m2": conditional_free.area,
             "raw_unknown_support_area_m2": unknown.area, "clipped_unknown_support_area_m2": clipped_unknown.area}
    # Display markers describe points only; no arbitrary polygon fill or cell-wide claim.
    samples = {"conditional_free": [], "occupied": [], "unknown": []}
    spacing = .15
    xmin, ymin, xmax, ymax = domain.bounds
    for ix in range(int(xmin / spacing), int(xmax / spacing) + 2):
        for iy in range(int(ymin / spacing), int(ymax / spacing) + 2):
            xy = (round(ix * spacing, 9), round(iy * spacing, 9))
            point = Point(xy)
            if not domain.covers(point):
                continue
            status = "occupied" if occupancy.covers(point) else (
                "unknown" if unknown.covers(point) else "conditional_free")
            samples[status].append(xy)
    return {"schema": "b3-whole-height-plan-preview/v1", "title": "B3 / whole-height plan occupancy/free-space",
            "query": {"frame": "world_xy", "units": "m", "height_band": None},
            "complete_occupancy": None, "complete_clearance": None, "statistics": stats,
            "domain": mapping(domain), "clipped_occupancy": mapping(clipped), "furniture_union": mapping(furniture),
            "domain_minus_occupancy": mapping(complement), "conditional_free": mapping(conditional_free),
            "unknown_supports": unknowns, "projections": projections, "projection_failures": failures,
            "boundary_door": {"id": "live-step-6231", "status": "excluded_from_interior_mass_and_unknown",
                              "reference_support": mapping(boundary_support)},
            "represented_owner_ids": sorted(represented), "selected_source_ids": sorted(selected),
            "sample_spacing_m": spacing, "sample_marker_side_m": .055, "samples": samples,
            "limits": ["Whole-height projections include overhead geometry; no traversability or clearance inference",
                       "Three convex proxies fill gaps and concavities; conditional design approximation",
                       "Unknown supports retained; complete occupancy and complete clearance remain null",
                       "Markers represent points; rings preserve holes and concavities; stroke widths are display only"]}


def main():
    """Verify immutable inputs, create fresh artifacts, and launch the specified background Blender."""
    manifest_path = PACKAGE / "artifact_manifest.json"
    assert sha256(manifest_path) == MANIFEST_SHA256
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fingerprints = {str(manifest_path): MANIFEST_SHA256}
    for reference in manifest["artifacts"]:
        path = (ROOT / reference["path"]).resolve()
        assert path.parent == PACKAGE and sha256(path) == reference["sha256"]
        fingerprints[str(path)] = reference["sha256"]
    out = BASE / ("preview_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(exist_ok=False)
    print(f"OUTPUT {out}", flush=True)
    preview = build_input(fingerprints)
    preview["package"] = str(PACKAGE)
    preview["frozen_input_fingerprints"] = fingerprints
    write_json(out / "preview_input.json", preview)
    renderer = Path(__file__).with_name("render_b3_whole_height_blender_preview.py")
    process = subprocess.run([str(BLENDER), "--background", "--factory-startup", "--disable-autoexec",
                              "--python-exit-code", "1", "--python", str(renderer), "--", "--out", str(out)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    (out / "blender_process.log").write_text(process.stdout + "\nSTDERR\n" + process.stderr, encoding="utf-8")
    assert all(sha256(Path(path)) == digest for path, digest in fingerprints.items())
    metadata = {"schema": preview["schema"], "title": preview["title"], "query": preview["query"],
                "statistics": preview["statistics"], "frozen_input_fingerprints": fingerprints,
                "frozen_input_integrity_before_and_after": "verified", "blender_executable": str(BLENDER),
                "blender_process_returncode": process.returncode, "live_blender_scene": "not_loaded_or_modified",
                "source_geometry_retessellation": "none", "complete_occupancy": None, "complete_clearance": None,
                "boundary_door": preview["boundary_door"], "projection_failures": preview["projection_failures"],
                "limits": preview["limits"], "code_fingerprints": {str(path): sha256(path) for path in (
                    Path(__file__), renderer, ROOT / "features/geometry_views.py")}}
    if process.returncode != 0:
        write_json(out / "preview_metadata.json", metadata)
        raise RuntimeError(f"Background Blender failed; see {out / 'blender_process.log'}")
    metadata["render_verification"] = json.loads((out / "render_verification.json").read_text(encoding="utf-8"))
    artifacts = [out / name for name in ("b3_whole_height_plan.png", "b3_whole_height_disposable.blend",
                                        "preview_input.json", "blender_process.log", "render_verification.json")]
    assert all(path.stat().st_size > 0 for path in artifacts)
    metadata["artifacts"] = [{"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts]
    write_json(out / "preview_metadata.json", metadata)
    stats = preview["statistics"]
    report = ["# B3 whole-height plan occupancy/free-space", "", f"Frozen package: `{PACKAGE}`", "",
              "World XY / metres / whole height / no height band. Disposable background Blender preview.", "",
              "| Measure | Value |", "|---|---:|"]
    report.extend(f"| {key} | {value} |" for key, value in stats.items())
    report.extend(["", "Boundary door `live-step-6231` is excluded from interior mass and unknown.",
                   "Seven proxy owners are represented once by three active proxies.",
                   "Domain-minus-occupancy is conditional; the display additionally excludes unknown supports.",
                   "Furniture union is the union of successful full mesh projections, with clipped area reported separately.",
                   "", "## Limits", ""] + [f"- {limit}" for limit in preview["limits"]])
    (out / "preview_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "statistics": stats}), flush=True)


if __name__ == "__main__":
    main()
