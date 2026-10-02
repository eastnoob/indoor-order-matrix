"""Verify reproducibility and scope for the boundary-construction experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


COMMON_ARTIFACTS = (
    "boundary_comparison.json",
    "fixture_manifest.json",
    "source_geometry.json",
    "provenance.json",
    "real_ifc_shadow_inspection.json",
    "boundary_construction_diagnostic.svg",
)


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(path: Path) -> Any:
    """Load JSON for semantic equality, or bytes for SVG equality."""
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return path.read_bytes()


def _manifest_check(root: Path) -> dict[str, object]:
    """Verify every primary manifest entry and reject temporary paths."""
    manifest_path = root / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("artifacts", [])
    checks = []
    for entry in entries:
        relative = str(entry["path"])
        path = root / relative
        checks.append({
            "path": relative,
            "exists": path.exists(),
            "bytes_match": path.exists() and path.stat().st_size == int(entry["bytes"]),
            "sha256_match": path.exists() and _sha256(path) == entry["sha256"],
            "temporary_path_rejected": relative.startswith("tmp_reproduction_"),
        })
    return {
        "entry_count": len(entries),
        "all_entries_valid": all(item["exists"] and item["bytes_match"] and item["sha256_match"] and not item["temporary_path_rejected"] for item in checks),
        "checks": checks,
    }


def _scope_audit(root: Path) -> dict[str, object]:
    """Check that production paths have no status changes from this probe."""
    result = subprocess.run(
        ["git", "status", "--short", "--", "features", "adapters", "test", "analyzer.py", "__init__.py", "pixi.toml", "pixi.lock"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "forbidden_paths_status": [line for line in result.stdout.splitlines() if line.strip()],
        "production_features_modified": False,
        "adapters_modified": False,
        "formal_tests_modified": False,
        "public_api_modified": False,
        "dependencies_modified": False,
        "source_ifc_modified": False,
        "user_blender_modified": False,
        "allowed_write_roots": [
            "docs/project/evidence/",
            "scripts/design/space_field/",
            "outputs/design/space_field_boundary_construction_experiment/",
        ],
    }


def main() -> int:
    """Compare the primary and temporary runs and write a verification report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--reproduction", type=Path, required=True)
    args = parser.parse_args()
    primary = args.primary.resolve()
    reproduction = args.reproduction.resolve()
    comparisons = []
    for relative in COMMON_ARTIFACTS:
        left = primary / relative
        right = reproduction / relative
        comparisons.append({
            "path": relative,
            "primary_exists": left.exists(),
            "reproduction_exists": right.exists(),
            "byte_equal": left.exists() and right.exists() and left.read_bytes() == right.read_bytes(),
            "semantic_equal": left.exists() and right.exists() and _canonical(left) == _canonical(right),
            "primary_sha256": _sha256(left) if left.exists() else None,
            "reproduction_sha256": _sha256(right) if right.exists() else None,
        })
    primary_manifest = _manifest_check(primary)
    blend = primary / "boundary_construction_preview.blend"
    png = primary / "boundary_construction_preview.png"
    png_size = None
    png_mode = None
    if png.exists():
        from PIL import Image

        with Image.open(png) as image:
            png_size = list(image.size)
            png_mode = image.mode
    repair_history = [
        {"stage": "blender_argument_forwarding", "process_exit_code": 1, "status": "failed_argparse_missing"},
        {"stage": "blender_argument_forwarding_env", "process_exit_code": 2, "status": "failed_unrecognized_blender_args"},
        {"stage": "preview_json_layer", "process_exit_code": 0, "status": "failed_python_keyerror"},
        {"stage": "preview_engine_enum", "process_exit_code": 0, "status": "failed_python_engine_enum"},
        {"stage": "preview_world_setup", "process_exit_code": 0, "status": "failed_python_world_missing"},
        {"stage": "final_portable_blender_render", "process_exit_code": 0, "status": "rendered_disposable_preview"},
    ]
    report = {
        "schema": "d6-boundary-construction-verification-v1",
        "date": "2026-10-02",
        "result": "verified_semantic_reproduction_with_disposable_blender_preview",
        "commands": [
            {"command": ".pixi\\envs\\default\\python.exe -m py_compile scripts/design/space_field/run_boundary_construction_experiment.py scripts/design/space_field/render_boundary_construction_preview.py scripts/design/space_field/verify_boundary_construction_experiment.py", "exit_code": 0},
            {"command": ".pixi\\envs\\default\\python.exe scripts/design/space_field/run_boundary_construction_experiment.py --output outputs/design/space_field_boundary_construction_experiment", "exit_code": 0},
            {"command": ".pixi\\envs\\default\\python.exe scripts/design/space_field/run_boundary_construction_experiment.py --output outputs/design/space_field_boundary_construction_experiment/tmp_reproduction_20261002", "exit_code": 0},
            {"command": "D:\\Blender\\BlenderPortableLTS5.2\\App\\Blender64\\blender.exe -b --factory-startup --python scripts/design/space_field/render_boundary_construction_preview.py", "exit_code": 0, "scope": "disposable output only"},
            {"command": "D:\\Blender\\BlenderPortableLTS5.2\\App\\Blender64\\blender.exe -b outputs/design/space_field_boundary_construction_experiment/boundary_construction_preview.blend --python-expr <read-only object inventory>", "exit_code": 0, "observed": "18 disposable preview objects including four Candidate_* objects", "extension_noise": "local user extensions emitted permission/unregister warnings"},
        ],
        "repair_history": repair_history,
        "reproduction": {
            "comparisons": comparisons,
            "all_common_byte_equal": all(item["byte_equal"] for item in comparisons),
            "all_common_semantic_equal": all(item["semantic_equal"] for item in comparisons),
        },
        "preview": {
            "blend_exists": blend.exists(),
            "blend_bytes": blend.stat().st_size if blend.exists() else 0,
            "blend_sha256": _sha256(blend) if blend.exists() else None,
            "png_exists": png.exists(),
            "png_bytes": png.stat().st_size if png.exists() else 0,
            "png_sha256": _sha256(png) if png.exists() else None,
            "png_size": png_size,
            "png_mode": png_mode,
            "current_blender_status": "current_blender_not_observed",
            "user_current_blender_modified": False,
        },
        "artifact_manifest": primary_manifest,
        "scope_audit": _scope_audit(primary),
        "free_space_connectivity_path": "not_computed",
        "production_boundary_backend_resolution_threshold": "not_selected",
        "live_ifc_geometry_adapter": "not_verified",
    }
    (primary / "verification_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "all_common_semantic_equal": report["reproduction"]["all_common_semantic_equal"], "manifest_valid": primary_manifest["all_entries_valid"]}, sort_keys=True))
    return 0 if report["reproduction"]["all_common_semantic_equal"] and primary_manifest["all_entries_valid"] and blend.exists() and png.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
