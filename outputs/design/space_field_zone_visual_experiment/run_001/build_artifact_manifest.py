"""Validate experiment outputs and write a byte-accurate artifact manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[3]
MANIFEST_PATH = ROOT / "artifact_manifest.json"
EVIDENCE_PATH = REPOSITORY / "docs/project/evidence/d6-space-field-zone-visual-experiment.md"
PNG_NAMES = [
    "candidate_baseline_one_region.png",
    "candidate_mst_gap_cut_2_regions.png",
    "candidate_mst_gap_cut_3_regions.png",
    "candidate_mst_gap_cut_4_regions.png",
]


def _sha256(path: Path) -> str:
    """Hash one artifact in bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict:
    """Read one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _file_record(path: Path, command_id: str, role: str) -> dict:
    """Record path, byte length, digest, and producing command for one file."""
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "role": role,
        "command_id": command_id,
    }


def main() -> None:
    """Run bounded artifact checks and serialize the requested manifest."""
    summary = _json(ROOT / "source_summary.json")
    candidates = _json(ROOT / "zone_candidates.json")["candidates"]
    render_checks = _json(ROOT / "blender_render_checks.json")
    readback = _json(ROOT / "blend_readback.json")
    wall_projection = _json(ROOT / "physical_wall_plan_projection.json")
    source_ifc = Path(summary["source_ifc"]["path"])

    if not summary["current_blender_identity"]["source_path_match"]:
        raise RuntimeError("Current Blender source identity is not confirmed.")
    if _sha256(source_ifc) != summary["source_ifc"]["sha256"]:
        raise RuntimeError("Source IFC hash changed after input extraction.")
    if wall_projection["source_sha256"] != summary["source_ifc"]["sha256"]:
        raise RuntimeError("Wall mesh projection provenance does not match source IFC.")
    if [candidate["region_count"] for candidate in candidates] != [1, 2, 3, 4]:
        raise RuntimeError("The baseline and 2/3/4-region candidates are incomplete.")
    if not all(item["labels_inside_frame_with_1pct_margin"] for item in render_checks["scenes"]):
        raise RuntimeError("At least one candidate render has an out-of-frame label.")
    if readback["scene_count"] != 4 or readback["source_scene_opened_or_saved"]:
        raise RuntimeError("Disposable blend readback did not pass the scene-scope audit.")

    png_records = []
    for name in PNG_NAMES:
        path = ROOT / name
        with Image.open(path) as image_file:
            image_file.verify()
        with Image.open(path) as image_file:
            if image_file.size != (2400, 1200) or image_file.mode != "RGBA":
                raise RuntimeError(f"Unexpected PNG metadata for {name}.")
            if image_file.getbbox() != (0, 0, 2400, 1200):
                raise RuntimeError(f"PNG is blank or has unexpected empty extent: {name}.")
        png_records.append(_file_record(path, "portable_blender_render", "owner-view PNG"))

    command_log = [
        {
            "id": "portable_blender_render",
            "command": "D:\\Blender\\BlenderPortableLTS5.2\\App\\Blender64\\blender.exe -b --factory-startup --python outputs/design/space_field_zone_visual_experiment/run_001/render_zone_candidates.py",
            "exit_code": 0,
            "result": "Rendered four candidate PNGs and saved d6_zone_candidates_disposable.blend. Blender logged an optional thumbnail-cache write warning outside the experiment directory; requested outputs succeeded.",
        },
        {
            "id": "wall_projection_extract",
            "command": ".pixi\\envs\\default\\python.exe outputs/design/space_field_zone_visual_experiment/run_001/extract_wall_plan_projection.py",
            "exit_code": 0,
            "result": "Projected all 11 source wall Body meshes into plan geometry and verified source hash.",
        },
        {
            "id": "compile_visualization_scripts",
            "command": ".pixi\\envs\\default\\python.exe -m py_compile outputs/design/space_field_zone_visual_experiment/run_001/extract_wall_plan_projection.py outputs/design/space_field_zone_visual_experiment/run_001/render_zone_candidates.py",
            "exit_code": 0,
            "result": "Visualization scripts compiled successfully.",
        },
        {
            "id": "blend_readback",
            "command": "D:\\Blender\\BlenderPortableLTS5.2\\App\\Blender64\\blender.exe -b --factory-startup outputs/design/space_field_zone_visual_experiment/run_001/d6_zone_candidates_disposable.blend --python outputs/design/space_field_zone_visual_experiment/run_001/inspect_saved_blend.py",
            "exit_code": 0,
            "result": "Reopened disposable blend and verified all four scenes, 37 group labels and 11 wall meshes per scene, candidate fills, orthographic cameras, and render size.",
        },
        {
            "id": "manifest_validation",
            "command": ".pixi\\envs\\default\\python.exe outputs/design/space_field_zone_visual_experiment/run_001/build_artifact_manifest.py",
            "exit_code": 0,
            "result": "Verified source identity, candidate counts, render label bounds, blend readback, and PNG metadata; wrote this manifest.",
        },
        {
            "id": "initial_ifc_group_extraction",
            "command": "Completed before this continuation; exact process command was not retained in the handoff state.",
            "exit_code": None,
            "result": "Input inventory and candidate JSON files were present at continuation start and retain the source IFC SHA-256.",
        },
        {
            "id": "manual_render_inspection",
            "command": "Opened the four final PNG artifacts with the local image inspection tool.",
            "exit_code": 0,
            "result": "Visually checked plan content, required legends, candidate distinction, labels, and crop.",
        },
    ]

    files = []
    files.extend(png_records)
    files.extend([
        _file_record(ROOT / "d6_zone_candidates_disposable.blend", "portable_blender_render", "disposable editable Blender scenes"),
        _file_record(EVIDENCE_PATH, "manual_evidence_record", "owner-facing experiment record"),
        _file_record(ROOT / "render_zone_candidates.py", "compile_visualization_scripts", "render source script"),
        _file_record(ROOT / "extract_wall_plan_projection.py", "compile_visualization_scripts", "read-only wall projection source script"),
        _file_record(ROOT / "inspect_saved_blend.py", "blend_readback", "disposable blend readback verifier"),
        _file_record(ROOT / "build_artifact_manifest.py", "manifest_validation", "manifest and artifact validator"),
        _file_record(ROOT / "owner_visual_review_record.md", "manual_evidence_record", "owner-facing output-directory summary"),
    ])
    for name in (
        "source_summary.json",
        "furniture_group_nodes.json",
        "group_relation_evidence.json",
        "zone_candidates.json",
        "provenance.json",
        "scope_audit.json",
        "render_input.json",
    ):
        files.append(_file_record(ROOT / name, "initial_ifc_group_extraction", "IFC facts, candidate inputs, or scope audit"))
    for path in sorted((ROOT / "candidate_records").glob("*.json")):
        files.append(_file_record(path, "portable_blender_render", "candidate-specific input, boundary, partition, status, and provenance record"))
    for name in ("physical_wall_plan_projection.json", "blender_render_checks.json"):
        files.append(_file_record(ROOT / name, "wall_projection_extract" if name.startswith("physical_wall") else "portable_blender_render", "render evidence JSON"))
    files.append(_file_record(ROOT / "blend_readback.json", "blend_readback", "disposable blend readback result"))

    manifest = {
        "schema": "d6-space-field-zone-visual-artifact-manifest/v1",
        "created_at": "2026-10-02",
        "output_directory": str(ROOT.resolve()),
        "manifest_self_hash_excluded": True,
        "source_ifc": {
            "path": str(source_ifc.resolve()),
            "bytes": source_ifc.stat().st_size,
            "sha256": summary["source_ifc"]["sha256"],
        },
        "current_blender_scene": {
            "observed": True,
            "source_path_match": True,
            "modified": False,
            "saved": False,
            "disposable_preview_process": "portable Blender --background --factory-startup",
        },
        "commands": command_log,
        "files": sorted(files, key=lambda item: item["path"]),
        "checks": {
            "candidate_region_counts": [item["region_count"] for item in candidates],
            "png_metadata": {record["path"]: {"width": 2400, "height": 1200, "mode": "RGBA", "verified": True} for record in png_records},
            "all_render_text_inside_safe_camera_frame": True,
            "disposable_blend_readback_passed": True,
            "source_hash_unchanged": True,
            "production_code_and_formal_tests_modified": False,
            "unrelated_full_test_suite_run": False,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "pass", "manifest": str(MANIFEST_PATH), "files": len(files)}))


if __name__ == "__main__":
    main()
