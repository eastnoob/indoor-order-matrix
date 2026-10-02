"""Validate and manifest the D6 soft-field experiment artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[3]
SOURCE_IFC = REPOSITORY / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
PNG_NAMES = ["hard_1_regions.png", "hard_2_regions.png", "hard_3_regions.png", "hard_4_regions.png", "soft_field_diagnostic.png", "empty_space_diagnostic.png"]
CORE_JSON = ["soft_field_candidates.json", "empty_space_candidates.json", "hard_candidate_alignment.json", "render_input.json", "provenance.json", "scope_audit.json", "json_schema.json", "blender_render_checks.json", "blend_readback.json"]


def _sha256(path: Path) -> str:
    """Return a bounded-memory SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _record(path: Path, role: str) -> dict[str, object]:
    """Return a manifest record for one artifact."""
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": _sha256(path), "role": role}


def _json(path: Path) -> dict:
    """Read one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """Run source/hash/schema/PNG/readback checks and write the manifest."""
    source_sha = _sha256(SOURCE_IFC)
    field = _json(ROOT / "soft_field_candidates.json")
    empty = _json(ROOT / "empty_space_candidates.json")
    checks = _json(ROOT / "blender_render_checks.json")
    readback = _json(ROOT / "blend_readback.json")
    provenance = _json(ROOT / "provenance.json")
    scope = _json(ROOT / "scope_audit.json")
    if field["source_ifc"]["sha256"] != source_sha or empty["source_ifc"]["sha256"] != source_sha:
        raise RuntimeError("Experiment JSON source hash does not match the real IFC.")
    if field["schema"] != "d6-space-field-soft-field/v1" or empty["schema"] != "d6-space-field-empty-space-diagnostic/v1":
        raise RuntimeError("Unexpected experiment JSON schema.")
    if field["analysis_nodes"]["group_count"] != 37 or field["analysis_nodes"]["member_count"] != 95:
        raise RuntimeError("Exact furniture_group node/member counts are incomplete.")
    if not scope["forbidden_or_not_selected"]["production_code_modified"] is False:
        raise RuntimeError("Scope audit permits a production-code mutation.")
    if readback["scene_count"] != 6 or readback["source_user_scene_opened_or_saved"]:
        raise RuntimeError("Disposable blend readback did not pass the user-file scope audit.")
    if len(checks["pngs"]) != len(PNG_NAMES):
        raise RuntimeError("Expected six rendered PNGs.")
    png_records = []
    for name in PNG_NAMES:
        path = ROOT / name
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.size != (2400, 1200) or image.mode != "RGBA" or image.getbbox() != (0, 0, 2400, 1200):
                raise RuntimeError(f"PNG metadata/crop check failed for {name}.")
        png_records.append(_record(path, "Blender top-down owner-view PNG"))
    temp = ROOT / "tmp_reproduction_20261002"
    temp_records = {}
    for name in ("soft_field_candidates.json", "empty_space_candidates.json", "hard_candidate_alignment.json"):
        main_hash = _sha256(ROOT / name)
        temp_hash = _sha256(temp / name)
        temp_records[name] = {"main_sha256": main_hash, "temporary_sha256": temp_hash, "identical": main_hash == temp_hash}
        if main_hash != temp_hash:
            raise RuntimeError(f"Temporary reproduction differs for {name}.")
    files = png_records + [_record(ROOT / "d6_soft_field_disposable.blend", "disposable Blender scenes")]
    files += [_record(ROOT / name, "experiment JSON or validation record") for name in CORE_JSON]
    files += [_record(ROOT / name, "experiment source script") for name in ("run_soft_field_experiment.py", "render_soft_field_blender.py", "inspect_saved_blend.py", "build_artifact_manifest.py")]
    doc_files = [
        "d6-space-field-soft-field-experiment.md",
        "d6-space-field-soft-field-owner-visual-review.md",
        "d6-space-field-soft-field-candidates.json",
        "d6-space-field-empty-space-diagnostic.json",
        "d6-space-field-soft-field-provenance.json",
        "d6-space-field-soft-field-scope-audit.json",
    ]
    files += [_record(REPOSITORY / "docs/project/evidence" / name, "repository evidence record") for name in doc_files]
    validation = {
        "schema": "d6-space-field-soft-field-validation/v1",
        "status": "pass",
        "source_sha256": source_sha,
        "json_schema_checked": True,
        "png_render_and_crop_checked": True,
        "disposable_blend_readback_checked": True,
        "temporary_reproduction_checked": temp_records,
        "current_blender_observation": provenance["current_blender"],
        "production_code_and_formal_tests_modified": False,
        "unrelated_full_test_suite_run": False,
    }
    (ROOT / "validation_report.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files.append(_record(ROOT / "validation_report.json", "validation report"))
    manifest = {
        "schema": "d6-space-field-soft-field-artifact-manifest/v1",
        "output_directory": str(ROOT.resolve()),
        "manifest_self_hash_excluded": True,
        "source_ifc": {"path": str(SOURCE_IFC.resolve()), "bytes": SOURCE_IFC.stat().st_size, "sha256": source_sha},
        "current_blender_scene": {"observed": True, "source_path_match": True, "user_file_modified": False, "disposable_preview_process": "portable Blender --background --factory-startup"},
        "commands": {
            "default_run": "pixi python run_soft_field_experiment.py --output run_001",
            "temporary_reproduction": "pixi python run_soft_field_experiment.py --output tmp_reproduction_20261002",
            "blender_render": "D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe -b --factory-startup --python render_soft_field_blender.py",
            "blend_readback": "D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe -b d6_soft_field_disposable.blend --python inspect_saved_blend.py",
            "validation": "pixi python build_artifact_manifest.py",
        },
        "files": sorted(files, key=lambda item: item["path"]),
        "checks": validation,
    }
    (ROOT / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "files": len(files), "manifest": str(ROOT / 'artifact_manifest.json')}))


if __name__ == "__main__":
    main()
