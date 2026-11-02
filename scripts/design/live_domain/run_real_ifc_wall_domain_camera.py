"""Run the real IFC camera-to-wall-domain prerequisite diagnostic."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import subprocess
import sys

from shapely.geometry import mapping, shape as shapely_shape


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SOURCE = Path(
    r"D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/"
    r"full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
)
BINARY = Path(r"D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")
EXPECTED_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"


def fingerprint(path: Path) -> dict[str, object]:
    """Return the source identity before launching native Blender."""
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": checksum}


def svg_polygon(geometry: dict, *, stroke: str, fill: str, opacity: float, width: float) -> str:
    """Render one plane-local polygon or multipolygon without changing geometry."""
    kind = geometry.get("type")
    polygons = geometry.get("coordinates", ()) if kind == "MultiPolygon" else (geometry.get("coordinates", ()),)
    paths = []
    for polygon in polygons:
        if not polygon:
            continue
        commands = []
        for ring in polygon:
            if not ring:
                continue
            commands.append("M " + " L ".join(f"{x:.6f},{-y:.6f}" for x, y in ring) + " Z")
        if commands:
            paths.append(f'<path d="{" ".join(commands)}" fill="{fill}" fill-opacity="{opacity}" '
                         f'stroke="{stroke}" stroke-width="{width}" fill-rule="evenodd"/>')
    return "".join(paths)


def geometry_metrics(geometry: dict) -> dict[str, object]:
    """Summarize supplied GeoJSON without changing its rings or topology."""
    value = shapely_shape(geometry)
    parts = tuple(value.geoms) if value.geom_type == "MultiPolygon" else (value,)
    return {
        "geometry_type": value.geom_type,
        "area_m2": float(value.area),
        "polygon_components": len(parts),
        "hole_count": sum(len(part.interiors) for part in parts),
        "bounds_m": [float(item) for item in value.bounds],
    }


def write_preview(output: Path, result: dict) -> None:
    """Write a plane-local SVG from captured walls and existing B4 candidates."""
    from adapters.bonsai_live import _mesh
    from features._analysis_domain_handoff import _polygon
    from features.geometry_substitutes import mass_patch_from_mesh
    from features.geometry_views import component_shape, plan_projection
    from features.scene_contract import AnalysisPlane

    capture = result["capture"]
    plane = AnalysisPlane.from_dict(result["analysis_plane"])
    polygons = []
    wall_audit = []
    for row in capture["records"]:
        # The IFC class and canonical record identity are authoritative; skip
        # unrelated furniture meshes without constructing a full live scene.
        if row.get("ifc_class") != "IfcWall":
            continue
        audit = {"source_id": row.get("id"), "global_id": row.get("global_id"),
                 "capture_status": row.get("status"), "projected": False}
        try:
            mesh = _mesh(row)
            if mesh is None:
                audit["reason"] = "verified_wall_mesh_unavailable"
            else:
                polygon = component_shape(plan_projection(mass_patch_from_mesh(mesh), plane).components)
                if polygon is None:
                    audit["reason"] = "wall_projection_unavailable"
                else:
                    polygons.append((row["id"], mapping(polygon)))
                    audit["projected"] = True
                    audit["projected_components"] = len(polygon.geoms) if polygon.geom_type == "MultiPolygon" else 1
        except (KeyError, TypeError, ValueError) as exc:
            audit["reason"] = f"{type(exc).__name__}: {exc}"[:300]
        wall_audit.append(audit)
    candidates = []
    for item in result["domain_result"].get("candidates", ()):
        if item.get("outline"):
            candidates.append({
                "version_id": item["version_id"],
                "outline": item["outline"],
                "status": item.get("status"),
                "reason": item.get("reason"),
                "source_refs": tuple(item.get("source_refs", ())),
                "unresolved_aperture_refs": tuple(item.get("unresolved_aperture_refs", ())),
                "metrics": geometry_metrics(item["outline"]),
            })
    all_geometries = [shapely_shape(geometry) for _, geometry in polygons] + [
        _polygon(item["outline"]) for item in candidates]
    bounds = [geometry.bounds for geometry in all_geometries if geometry is not None]
    if not bounds:
        raise RuntimeError("the real wall projection produced no drawable geometry")
    min_x = min(item[0] for item in bounds) - 1.0
    min_y = min(item[1] for item in bounds) - 1.0
    max_x = max(item[2] for item in bounds) + 1.0
    max_y = max(item[3] for item in bounds) + 1.0
    width, height = 1600, 1000
    stroke_width = max(max_x - min_x, max_y - min_y) / 700
    wall_paths = "".join(svg_polygon(geometry, stroke="#475569", fill="#94a3b8", opacity=.22, width=stroke_width)
                          for _, geometry in polygons)
    colors = ("#2563eb", "#16a34a", "#d97706", "#9333ea", "#dc2626", "#0891b2")
    candidate_paths = "".join(
        svg_polygon(item["outline"], stroke=colors[index % len(colors)], fill=colors[index % len(colors)],
                    opacity=.10, width=stroke_width * 1.7)
        for index, item in enumerate(candidates))
    legend_x, legend_y = min_x + .12, -max_y + .24
    legend_font = stroke_width * 8
    labels = (f'<text x="{legend_x:.6f}" y="{legend_y:.6f}" font-size="{legend_font:.6f}" '
              f'fill="#334155">Walls: {len(polygons)} · B4 candidates: {len(candidates)} · '
              f'plane: {plane.name}</text>')
    candidate_labels = "".join(
        f'<text x="{_polygon(item["outline"]).representative_point().x:.6f}" '
        f'y="{-_polygon(item["outline"]).representative_point().y:.6f}" '
        f'font-size="{legend_font * .8:.6f}" fill="{colors[index % len(colors)]}">'
        f'{escape(item["version_id"].split(":")[1])} · {escape(item["status"] or "unknown")}'
        f'{" · " + escape(item["reason"]) if item["reason"] else ""}'
        f' · holes={item["metrics"]["hole_count"]}</text>'
        for index, item in enumerate(candidates))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x} {-max_y} {max_x-min_x} {max_y-min_y}" '
           f'width="{width}" height="{height}"><rect x="{min_x}" y="{-max_y}" width="{max_x-min_x}" '
           f'height="{max_y-min_y}" fill="white"/>{wall_paths}{candidate_paths}{labels}{candidate_labels}'
           f'</svg>')
    (output / "wall_domain_camera_candidates.svg").write_text(svg, encoding="utf-8")
    projected_wall_ids = {source_id for source_id, _ in polygons}
    inventory = {"plane": plane.to_dict(), "wall_count": len(wall_audit),
         "wall_projected_count": len(polygons), "wall_source_ids": [source_id for source_id, _ in polygons],
         "walls": wall_audit,
         "candidate_count": len(candidates), "candidates": [
             {"candidate_id": item["version_id"], "status": item["status"], "reason": item["reason"],
              "source_refs": list(item["source_refs"]),
              "unresolved_aperture_refs": list(item["unresolved_aperture_refs"]),
              "source_coverage": {
                  "matched_wall_count": len(set(item["source_refs"]) & projected_wall_ids),
                  "projected_wall_count": len(projected_wall_ids),
                  "ratio": (len(set(item["source_refs"]) & projected_wall_ids) / len(projected_wall_ids)
                            if projected_wall_ids else None),
              },
              **item["metrics"]}
             for item in candidates]}
    (output / "wall_projection_inventory.json").write_text(json.dumps(
        inventory,
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["preview_inventory"] = inventory


def finalize_existing_run(output: Path, *, capture_data: dict | None = None,
                          domain_result: dict | None = None) -> dict[str, object]:
    """Finish preview and manifest from an existing capture without relaunching Blender."""
    capture_path = output / "canonical_capture.json"
    result_path = output / "domain_result.json"
    capture_data = capture_data or json.loads(capture_path.read_text(encoding="utf-8"))
    domain_result = domain_result or json.loads(result_path.read_text(encoding="utf-8"))
    captured = capture_data | {"domain_result": domain_result}
    write_preview(output, captured)
    source = fingerprint(SOURCE)
    if source != capture_data.get("source_fingerprint"):
        raise RuntimeError("authorized source bytes changed after native capture")
    projected_wall_ids = set(captured["preview_inventory"]["wall_source_ids"])
    candidate_summaries = []
    for item in domain_result.get("candidates", ()):
        refs = set(item.get("source_refs", ()))
        metrics = geometry_metrics(item["outline"]) if item.get("outline") else {}
        candidate_summaries.append({
            "candidate_id": item["version_id"], "status": item.get("status"),
            "reason": item.get("reason"), "source_refs": sorted(refs),
            "unresolved_aperture_refs": list(item.get("unresolved_aperture_refs", ())),
            "source_coverage": {
                "matched_wall_count": len(refs & projected_wall_ids),
                "projected_wall_count": len(projected_wall_ids),
                "ratio": (len(refs & projected_wall_ids) / len(projected_wall_ids)
                          if projected_wall_ids else None),
            },
            **metrics,
        })
    manifest = {"schema": "wall-domain-camera-prerequisite-run/v1",
                "status": "candidates_unconfirmed", "source": source,
                "native_binary": str(BINARY), "capture": str(capture_path),
                "domain_result": str(result_path),
                "candidate_preview": str(output / "wall_domain_camera_candidates.svg"),
                "camera": capture_data["camera_binding"],
                "analysis_plane": capture_data["analysis_plane"],
                "observed_counts": capture_data["observed_counts"],
                "candidate_count": len(domain_result.get("candidates", ())),
                "candidates": candidate_summaries,
                "projected_wall_count": captured["preview_inventory"]["wall_projected_count"],
                "wall_inventory": str(output / "wall_projection_inventory.json"),
                "loaded_ifc": capture_data["bonsai"],
                "blender": capture_data["blender"],
                "capture_complete": capture_data["capture"].get("capture_complete"),
                "candidate_statuses": {status: sum(item.get("status") == status
                                                     for item in domain_result.get("candidates", ()))
                                        for status in sorted({item.get("status", "unknown")
                                                              for item in domain_result.get("candidates", ())})},
                "confirmed": False, "confirmation_required": True,
                "generated_utc": datetime.now(timezone.utc).isoformat()}
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    return manifest


def run(output: Path) -> dict:
    """Launch Blender once, evaluate the captured wall candidates, and write diagnostics."""
    source = fingerprint(SOURCE)
    if source["sha256"] != EXPECTED_SHA256:
        raise RuntimeError(f"authorized IFC fingerprint changed: {source['sha256']}")
    output.mkdir(parents=True, exist_ok=False)
    capture_path = output / "canonical_capture.json"
    capture_script = Path(__file__).with_name("capture_real_ifc_wall_domain_blender.py")
    env = {**dict(__import__("os").environ),
           "BLENDER_USER_EXTENSIONS": r"D:\Blender\BlenderPortableLTS5.2\Data\user_extensions",
           "BLENDER_SYSTEM_EXTENSIONS": r"D:\Blender\BlenderPortableLTS5.2\App\Blender64\5.2\extensions"}
    command = [str(BINARY), "-b", "--python", str(capture_script), "--", "--output", str(capture_path)]
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    (output / "blender_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output / "blender_stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"native Blender capture failed with {completed.returncode}")
    captured = json.loads(capture_path.read_text(encoding="utf-8"))
    request = {"canonical_capture": captured["capture"], "analysis_plane": captured["analysis_plane"],
               "tolerance_mm2": 1.0}
    request_path = output / "domain_request.json"
    result_path = output / "domain_result.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/design/live_domain/run_live_domain.py"),
                             str(request_path), str(result_path)], cwd=ROOT, capture_output=True, text=True)
    (output / "domain_stdout.log").write_text(result.stdout, encoding="utf-8")
    (output / "domain_stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"domain evaluation failed with {result.returncode}: {result.stderr[-500:]}")
    domain_result = json.loads(result_path.read_text(encoding="utf-8"))
    captured["domain_result"] = domain_result
    manifest = finalize_existing_run(output, capture_data=captured, domain_result=domain_result)
    return manifest


def main() -> None:
    """Create a new run or finish preview artifacts from an existing native capture."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--finalize-existing", type=Path)
    args = parser.parse_args()
    if args.finalize_existing is not None:
        manifest = finalize_existing_run(args.finalize_existing.resolve())
        print(json.dumps({"status": manifest["status"], "output": str(args.finalize_existing.resolve()),
                          "candidates": manifest["candidate_count"]}))
        return
    output = args.output or (ROOT / "outputs/design/wall_domain_camera_prerequisite" /
                             ("run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    manifest = run(output.resolve())
    print(json.dumps({"status": manifest["status"], "output": str(output.resolve()),
                      "candidates": manifest["candidate_count"]}))


if __name__ == "__main__":
    main()
