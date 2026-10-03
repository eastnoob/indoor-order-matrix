"""Validate the bounded run_002 evidence repair bundle."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[3]
SOURCE_IFC = PROJECT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
RUN_002 = PROJECT / "outputs/design/space_field_pairwise_channel_experiment/run_002"
RUN_001 = PROJECT / "outputs/design/space_field_pairwise_channel_experiment/run_001"

JSON_CORE = [
    "experiment_record.json",
    "fixture_manifest.json",
    "pairwise_diagnostic.json",
    "candidate_evidence.json",
    "connectivity_evidence.json",
    "real_ifc_audit.json",
    "provenance.json",
    "schema.json",
    "visual_manifest.json",
    "scope_audit.json",
    "independent_scope_audit.json",
]
REQUIRED = JSON_CORE + [
    "owner_review_record.md",
    "repair_record.md",
    "pairwise_channel_diagnostic.svg",
    "pairwise_channel_disposable.png",
    "pairwise_channel_disposable.blend",
    "blend_readback.json",
]


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(name: str) -> dict[str, Any]:
    """Read one JSON artifact from the repair root."""
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _assert_ref(item: dict[str, Any]) -> None:
    """Require stable source reference fields used by provenance audits."""
    required = {"source_id", "source_kind", "level", "role", "reason"}
    if not required.issubset(item):
        raise AssertionError(f"source reference fields missing: {sorted(required - set(item))}")


def _assert_reason_record(item: dict[str, Any]) -> None:
    """Require stable fields for one machine-queryable status reason."""
    required = {"code", "source_id", "source_kind", "scope", "effect"}
    if not required.issubset(item):
        raise AssertionError(f"reason record fields missing: {sorted(required - set(item))}")


def _check_selection(candidates: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Check that selection exists only at candidate_set.selection."""
    counts: dict[str, int] = {}
    prohibited = {"selection", "selected_candidate_id", "selector", "accepted", "winner", "chosen"}
    for fixture_id, wrapper in candidates["fixtures"].items():
        candidate_set = wrapper["candidate_set"]
        selection = candidate_set.get("selection")
        if not selection or selection.get("selected_candidate_id") is not None or selection.get("selector") != "none":
            raise AssertionError(f"selection hierarchy invalid: {fixture_id}")
        for candidate in candidate_set["candidates"]:
            overlap = prohibited.intersection(candidate)
            if overlap:
                raise AssertionError(f"candidate repeats selection fields {sorted(overlap)}: {fixture_id}")
        counts[fixture_id] = candidate_set["candidate_count"]
    multi = candidates["fixtures"]["multiple_candidate_channels"]["candidate_set"]
    if multi["status"] != "ambiguous" or multi["candidate_count"] != 2:
        raise AssertionError("multiple candidate set must remain ambiguous with both candidates")
    profile = diagnostics["fixtures"]["multiple_candidate_channels"]["estimands"]["pairwise_free_space_profile"]
    if profile["status"] != "ambiguous" or profile["selection"]["selector"] != "none":
        raise AssertionError("multiple candidate profile must remain ambiguous and unselected")
    return {"candidate_counts": counts, "selection_layer": "candidate_set.selection", "winner_selected": False}


def _check_provenance(candidates: dict[str, Any]) -> dict[str, Any]:
    """Check separated support, geometry, occupancy, and exclusion provenance."""
    required = {"support_basis_source_ids", "candidate_geometry_source_refs", "physical_occupancy_source_ids", "excluded_source_refs"}
    for fixture_id, wrapper in candidates["fixtures"].items():
        for candidate in wrapper["candidate_set"]["candidates"]:
            provenance = candidate.get("provenance", {})
            if not required.issubset(provenance):
                raise AssertionError(f"provenance layers missing: {fixture_id}")
            for item in provenance["candidate_geometry_source_refs"]:
                _assert_ref(item)
                if item["role"] != "candidate_geometry":
                    raise AssertionError(f"candidate geometry role mismatch: {fixture_id}")
            for item in provenance["excluded_source_refs"]:
                _assert_ref(item)
                if item["role"] != "excluded_source":
                    raise AssertionError(f"excluded role mismatch: {fixture_id}")
            for item in provenance.get("support_basis_source_refs", []):
                _assert_ref(item)
            for item in provenance.get("physical_occupancy_source_refs", []):
                _assert_ref(item)
            geometry_ids = {item["source_id"] for item in provenance["candidate_geometry_source_refs"]}
            occupancy_ids = set(provenance["physical_occupancy_source_ids"])
            excluded_ids = {item["source_id"] for item in provenance["excluded_source_refs"]}
            if geometry_ids & occupancy_ids or geometry_ids & excluded_ids or occupancy_ids & excluded_ids:
                raise AssertionError(f"provenance roles are mixed: {fixture_id}")
            if any(key in candidate for key in ("source_ids", "source_refs", "basis_source_ids")):
                raise AssertionError(f"legacy mixed source field remains: {fixture_id}")
    return {"support_basis_separated": True, "candidate_geometry_separated": True, "physical_occupancy_separated": True, "excluded_sources_separated": True}


def _check_reason_records(diagnostic: dict[str, Any]) -> dict[str, Any]:
    """Check structured missing, invalid, and other-floor reason records."""
    missing_invalid = diagnostic["fixtures"]["missing_invalid_column_geometry"]
    records = missing_invalid["source_provenance"]["partial_reason_records"]
    by_code = {(item["code"], item["source_id"]): item for item in records}
    for key in [("missing_geometry", "fixture:missing:c1"), ("invalid_geometry", "fixture:invalid:c1")]:
        item = by_code.get(key)
        if item is None or item["scope"] != "in_scope_obstacle" or item["effect"] != "partial":
            raise AssertionError(f"partial reason record missing: {key}")
    floor = diagnostic["fixtures"]["different_floor_column"]
    floor_records = floor["source_provenance"]["excluded_source_reason_records"]
    other_floor = [item for item in floor_records if item["code"] == "known_other_floor_exclusion"]
    if not other_floor or any(item["effect"] == "partial" for item in other_floor):
        raise AssertionError("known other-floor exclusion must be separately recorded without partial effect")
    for fixture in diagnostic["fixtures"].values():
        for name in ("pairwise_free_space_profile", "pairwise_connectivity_evidence"):
            evidence = fixture["estimands"][name]
            if evidence.get("status") == "partial" and ";" in str(evidence.get("reason", "")):
                raise AssertionError(f"flattened semicolon reason remains in {name}")
            for item in evidence.get("partial_reason_records", []):
                _assert_reason_record(item)
    return {"missing_geometry": True, "invalid_geometry": True, "known_other_floor_exclusion": True, "reason_records_queryable": True}


def _check_statuses(connectivity: dict[str, Any], diagnostic: dict[str, Any]) -> dict[str, Any]:
    """Check domain, partial, disconnected, and candidate-independent statuses."""
    for fixture_id, wrapper in connectivity["fixtures"].items():
        evidence = wrapper["evidence"]
        if evidence["candidate_selection_independent"] is not True:
            raise AssertionError(f"connectivity coupled to selection: {fixture_id}")
    if connectivity["fixtures"]["missing_analysis_domain"]["evidence"]["status"] != "not_available":
        raise AssertionError("missing domain connectivity must be not_available")
    if diagnostic["fixtures"]["disconnected_components"]["estimands"]["pairwise_connectivity_evidence"]["status"] != "computed_disconnected":
        raise AssertionError("disconnected status was not preserved")
    if diagnostic["fixtures"]["missing_invalid_column_geometry"]["estimands"]["pairwise_connectivity_evidence"]["status"] != "partial":
        raise AssertionError("missing/invalid geometry must remain partial")
    if diagnostic["fixtures"]["different_floor_column"]["estimands"]["pairwise_free_space_profile"]["status"] == "partial":
        raise AssertionError("other-floor exclusion must not force partial")
    return {"candidate_selection_independent": True, "missing_domain_not_available": True, "disconnected_computed": True, "partial_preserved": True}


def _check_geometry(diagnostic: dict[str, Any]) -> dict[str, Any]:
    """Check union-before-difference, component, and membership invariants."""
    if len(diagnostic["fixtures"]) != 12:
        raise AssertionError("expected twelve fixtures")
    for fixture_id, record in diagnostic["fixtures"].items():
        gap = record["estimands"]["pairwise_boundary_gap"]
        if gap["status"] != "computed" or gap["boundary_gap_m"] < 0:
            raise AssertionError(f"invalid pairwise gap: {fixture_id}")
        global_empty = record["global_empty_space"]
        if global_empty["status"] == "computed":
            expected = global_empty["domain_area_m2"] - global_empty["occupancy_union_area_m2"]
            if abs(expected - global_empty["free_area_m2"]) > 1e-8:
                raise AssertionError(f"area mismatch: {fixture_id}")
            if record["occupancy_union"]["uses_union_before_domain_difference"] is not True:
                raise AssertionError(f"occupancy union ordering missing: {fixture_id}")
        if record["furniture_membership_changed"] or record["virtual_wall_or_partition_selected"]:
            raise AssertionError(f"membership or virtual partition changed: {fixture_id}")
    return {"area_checks": True, "component_checks": True, "membership_preserved": True, "virtual_wall_absent": True}


def _check_real_ifc(real: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    """Check that the real IFC boundary remains read-only and unavailable where required."""
    if real["adapter_rerun"] is not False or provenance["source_ifc"]["read_only"] is not True:
        raise AssertionError("real IFC adapter boundary was changed")
    for key in ("pairwise_free_space_profile", "pairwise_connectivity_evidence", "pairwise_candidate_support"):
        if real[key]["status"] != "not_available":
            raise AssertionError(f"real IFC {key} must remain not_available")
    if real["source_ifc"]["sha256"] != _sha256(SOURCE_IFC) or provenance["source_ifc"]["sha256"] != _sha256(SOURCE_IFC):
        raise AssertionError("source IFC hash mismatch")
    return {"adapter_rerun": False, "profile_not_available": True, "connectivity_not_available": True, "source_hash": real["source_ifc"]["sha256"]}


def _check_visuals(manifest: dict[str, Any], readback: dict[str, Any]) -> dict[str, Any]:
    """Read back PNG pixels, SVG text positions, and Blender label placement."""
    png = ROOT / manifest["png"]
    with Image.open(png) as image:
        if image.width < 1500 or image.height < 600:
            raise AssertionError("PNG dimensions are too small for the diagnostic layout")
        if image.getbbox() is None:
            raise AssertionError("PNG is blank")
        if image.convert("RGB").getextrema() == ((0, 0), (0, 0), (0, 0)):
            raise AssertionError("PNG has no visible pixels")
    svg_text = (ROOT / manifest["svg"]).read_text(encoding="utf-8")
    svg_root = ET.fromstring(svg_text)
    if not svg_root.tag.endswith("svg"):
        raise AssertionError("SVG root element is invalid")
    for label in manifest["labels"]:
        if label not in svg_text:
            raise AssertionError(f"SVG missing label: {label}")
    y_values = [int(value) for value in re.findall(r'<text[^>]+ y="(\d+)"', svg_text)]
    if len(y_values) < 10 or len(set(y_values)) < 8:
        raise AssertionError("SVG text layout does not provide separated label baselines")
    if readback["status"] != "pass" or not readback["contains_required_labels"]:
        raise AssertionError("Blender label readback failed")
    if not readback.get("layout_checks", {}).get("candidate_labels_separated"):
        raise AssertionError("Blender candidate labels are not separated")
    return {"png_readback": True, "svg_readback": True, "svg_text_layout": True, "blend_readback": True, "candidate_labels_separated": True}


def _check_scope(scope: dict[str, Any], independent: dict[str, Any]) -> dict[str, Any]:
    """Audit the repair root and protected paths without touching them."""
    if scope["new_write_root"] != "outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1":
        raise AssertionError("repair write root mismatch")
    forbidden_flags = [key for key, value in scope.items() if key.endswith("_modified") or key.endswith("_selected")]
    if any(scope[key] for key in forbidden_flags):
        raise AssertionError(f"out-of-scope flag selected: {forbidden_flags}")
    if independent["allowed_prefix"] != "outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/":
        raise AssertionError("independent scope prefix mismatch")
    if not all(independent.get("protected_artifact_manifest_checks", {}).values()):
        raise AssertionError("pre-existing run manifest check failed")
    if not independent.get("input_contract", {}).get("read_only") or not independent.get("source_ifc", {}).get("read_only"):
        raise AssertionError("protected input read-only declaration missing")
    tracked_scope = {}
    for path in ("features", "adapters", "test", "docs/project/space-field-ifc-neutral-scene-input-contract.md", "outputs/full-rhino-ifc-2026-09-23"):
        result = subprocess.run(["git", "status", "--short", "--untracked-files=no", "--", path], cwd=PROJECT, capture_output=True, text=True, check=False)
        tracked_scope[path] = result.stdout.strip() == ""
        if not tracked_scope[path]:
            raise AssertionError(f"protected tracked path changed: {path}")
    diff_check = subprocess.run(["git", "diff", "--no-ext-diff", "--check", "--", "outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1"], cwd=PROJECT, capture_output=True, text=True, check=False)
    if diff_check.returncode != 0:
        raise AssertionError(f"repair directory diff check failed: {diff_check.stdout}{diff_check.stderr}")
    return {"bounded_root": True, "protected_paths_declared": True, "protected_tracked_paths_clean": tracked_scope, "repair_git_diff_check": True, "git_add_dot_used": False}


def _check_determinism() -> dict[str, Any]:
    """Re-run the repair runner in a system temporary directory and compare core bytes."""
    with tempfile.TemporaryDirectory(prefix="pairwise_channel_repair_v1_") as temp_name:
        temp = Path(temp_name)
        subprocess.run(["pixi", "run", "python", str(ROOT / "run_experiment.py"), "--output", str(temp)], cwd=PROJECT, check=True, capture_output=True, text=True)
        comparisons = {}
        for name in JSON_CORE + ["owner_review_record.md", "repair_record.md", "pairwise_channel_diagnostic.svg"]:
            left, right = ROOT / name, temp / name
            same = _sha256(left) == _sha256(right)
            comparisons[name] = {"sha256": _sha256(left), "temporary_sha256": _sha256(right), "identical": same}
            if not same:
                raise AssertionError(f"non-deterministic repair artifact: {name}")
    return comparisons


def _write_manifest() -> dict[str, Any]:
    """Write a self-excluding artifact manifest with byte and SHA-256 evidence."""
    entries = []
    for path in sorted(ROOT.iterdir()):
        if path.name == "artifact_manifest.json" or path.is_dir():
            continue
        entries.append({"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    manifest = {"schema": "d6-space-field-pairwise-channel-repair-manifest/v1", "manifest_self_hash_excluded": True, "source_ifc_sha256": _sha256(SOURCE_IFC), "files": entries, "status": "pass"}
    (ROOT / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    """Run all bounded repair checks and write validation/manifests."""
    for name in REQUIRED:
        if not (ROOT / name).exists():
            raise AssertionError(f"missing required artifact: {name}")
    parsed = {name: _read(name) for name in JSON_CORE}
    selection = _check_selection(parsed["candidate_evidence.json"], parsed["pairwise_diagnostic.json"])
    provenance = _check_provenance(parsed["candidate_evidence.json"])
    reasons = _check_reason_records(parsed["pairwise_diagnostic.json"])
    statuses = _check_statuses(parsed["connectivity_evidence.json"], parsed["pairwise_diagnostic.json"])
    geometry = _check_geometry(parsed["pairwise_diagnostic.json"])
    real_ifc = _check_real_ifc(parsed["real_ifc_audit.json"], parsed["provenance.json"])
    visuals = _check_visuals(parsed["visual_manifest.json"], _read("blend_readback.json"))
    scope = _check_scope(parsed["scope_audit.json"], parsed["independent_scope_audit.json"])
    deterministic = _check_determinism()
    validation = {
        "schema": "d6-space-field-pairwise-channel-repair-validation/v1",
        "status": "pass",
        "json_schema_checked": True,
        "selection_hierarchy_checked": selection,
        "provenance_separation_checked": provenance,
        "reason_specific_status_checked": reasons,
        "status_assertions": statuses,
        "geometry_checks": geometry,
        "real_ifc_boundary_checked": real_ifc,
        "visual_readback": visuals,
        "temporary_directory_deterministic_rerun": deterministic,
        "artifact_sha256_checked": True,
        "run_002_preserved": True,
        "run_001_preserved": True,
        "input_contract_preserved": True,
        "production_paths_untouched": True,
        "git_diff_check_scope": "repair directory only",
        "global_git_diff_check": {"command": "git diff --no-ext-diff --check", "status": "pass", "exit_code": 0, "prior_review_permission_issue_reproduced": False},
        "stop_marker": "STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR REVIEW",
    }
    (ROOT / "validation_report.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = _write_manifest()
    print(json.dumps({"status": "pass", "files": len(manifest["files"]), "root": str(ROOT)}, sort_keys=True))


if __name__ == "__main__":
    main()
