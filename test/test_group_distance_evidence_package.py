"""Focused checks for the minimal group-walk-distance evidence package."""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace

import pytest

from .test_group_distance import _missing_bundle
from features.field_core import serialize_evidence_package_output
from features.group_distance import calculate_group_pair_distances, group_distance_input_fingerprints
from features.group_distance import serialize_group_distance_result
from features import group_distance_evidence_package as package_module
from features.group_distance_evidence_package import (
    SOURCE_CHANNEL,
    build_group_distance_evidence_package,
    build_group_distance_package_contract,
    build_group_distance_source_envelopes,
    build_group_distance_visualization_manifest,
)
from scripts.design.group_level.run_group_distance_evidence_package import write_visualization_manifest


def test_distance_package_emits_only_two_additive_channels() -> None:
    """The package keeps pair scope and exposes Euclidean/path readings only."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    sources = build_group_distance_source_envelopes(result, bundle)
    output = build_group_distance_evidence_package().evaluate(sources)

    assert len(sources) == len(result.observations) == 3
    assert all(envelope.channel_set == (SOURCE_CHANNEL,) for envelope in sources)
    assert {item.channel for item in output.outputs} == {"euclidean_distance", "path_distance"}
    assert len(output.outputs) == 2 * len(result.observations)
    assert all(item.channel != "free_space" for item in output.outputs)
    assert {item.target["identity"] for item in output.outputs} == {
        observation.pair_id for observation in result.observations
    }


def test_free_space_is_dependency_metadata_and_output_serializes() -> None:
    """Free-space identity remains auditable without becoming a third channel."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    output = build_group_distance_evidence_package().evaluate(
        build_group_distance_source_envelopes(result, bundle)
    )
    serialized = serialize_evidence_package_output(output)
    json.dumps(serialized, allow_nan=False)

    source = output.source_envelopes[0]
    assert "dependency_fingerprints" in source.provenance
    assert source.value["channels"][0].channel == SOURCE_CHANNEL
    assert "free_space" not in source.channel_set
    assert all("free_space_dependency_fingerprint" in item.provenance for item in output.outputs)


def test_package_contract_declares_pair_targets_and_visual_binding() -> None:
    """The package contract includes stable targets, channels, and artifact binding."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    contract = build_group_distance_package_contract(
        result,
        bundle,
        visualization_manifest={"overview": "overview.html", "blender": "scene.blend"},
    )

    assert contract["package_id"] == "group-walk-distance"
    assert contract["target_ids"] == sorted(item.pair_id for item in result.observations)
    assert contract["artifacts"]["output_channels"] == ["euclidean_distance", "path_distance"]
    assert contract["artifacts"]["visualization_manifest"]["overview"] == "overview.html"


def test_visualization_manifest_references_existing_artifacts_without_recompute() -> None:
    """A manifest binds existing overview/Blender artifacts and never reruns distance."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    output = build_group_distance_evidence_package().evaluate(
        build_group_distance_source_envelopes(result, bundle)
    )
    manifest = build_group_distance_visualization_manifest(
        output,
        overview="overview.html",
        blender="distance_scene.blend",
        preview="preview/index.html",
    )

    assert manifest["distance_recomputed"] is False
    assert manifest["artifact_bindings"] == {
        "overview": "overview.html",
        "blender": "distance_scene.blend",
        "preview": "preview/index.html",
    }
    assert manifest["channels"] == ["euclidean_distance", "path_distance"]
    assert len(manifest["pair_ids"]) == len(result.observations)


def test_output_only_runner_writes_manifest_from_saved_package(tmp_path: Path) -> None:
    """The artifact runner binds saved JSON and does not need a distance input bundle."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    output = build_group_distance_evidence_package().evaluate(
        build_group_distance_source_envelopes(result, bundle)
    )
    saved = json.loads(json.dumps(serialize_evidence_package_output(output), allow_nan=False))
    path = tmp_path / "package_visualization_manifest.json"
    manifest = write_visualization_manifest(saved, path, overview="overview.html")

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["distance_recomputed"] is False
    assert manifest["artifact_bindings"]["overview"] == "overview.html"


def test_saved_global_repair_result_is_adapted_without_recomputing(monkeypatch) -> None:
    """The saved-result adapter rejects an incomplete claimed route without search."""
    bundle = _missing_bundle()
    baseline = serialize_group_distance_result(calculate_group_pair_distances(bundle))
    for row in baseline["observations"]:
        row["directional_repair"] = {
            "quality": "exact_route_verified",
            "candidate_distance_m": 1.25,
            "exact_witness": {"cell_keys": ((0, 0),)},
        }
    baseline["schema_version"] = "route-repair/2"

    def forbidden(_bundle):
        """Fail if the repaired-result adapter starts the ordinary kernel."""
        raise AssertionError("ordinary distance calculation was repeated")

    monkeypatch.setattr(package_module, "calculate_group_pair_distances", forbidden)
    with pytest.raises(ValueError, match="route cells and both endpoint offsets"):
        package_module.evaluate_group_distance_package(bundle, repaired_result=baseline)


def test_empty_scope_is_explicitly_unavailable() -> None:
    """No target pairs produce one unavailable scope record instead of fake emptiness."""
    bundle = replace(_missing_bundle(), groups=())
    output = package_module.evaluate_group_distance_package(bundle)

    assert len(output.outputs) == 2
    assert {item.status.value for item in output.outputs} == {"not_available"}
    assert all("no target group pairs" in item.explanation for item in output.outputs)
    result = calculate_group_pair_distances(bundle)
    contract = build_group_distance_package_contract(result, bundle)
    assert contract["target_ids"] == sorted({item.target["identity"] for item in output.outputs})


def _unresolved_repair(result) -> dict:
    """Provide repair metadata only, retaining the nonspatial unavailable readings."""
    saved = serialize_group_distance_result(result)
    saved.update(schema_version="route-repair/2", method="contract-repair/1", policy={"min_total_m": .55})
    for row in saved["observations"]:
        row["directional_repair"] = {"quality": "unresolved_unknown", "method": "contract-repair/1"}
    return saved


def test_typed_result_accepts_matching_repair_scope_and_preserves_unknown() -> None:
    """A typed baseline and separate repair retain unknown as partial/null output."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    sources = build_group_distance_source_envelopes(result, bundle, repaired_result=_unresolved_repair(result))
    output = build_group_distance_evidence_package().evaluate(sources)
    paths = [item for item in output.outputs if item.channel == "path_distance"]
    assert len(paths) == len(result.observations)
    assert all(item.status.value == "partial" for item in paths)
    assert all(item.observation["raw_status"] == "unknown" and item.observation["value"] is None for item in paths)
    assert all("repair_result" in source.provenance["dependency_fingerprints"] for source in sources)


def test_pair_dependency_validation_is_shared_across_envelopes(monkeypatch) -> None:
    """One result binding is validated once rather than once for every pair."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    original = package_module._dependencies
    calls = []

    def counted(*args, **kwargs):
        """Record dependency traversals without changing the real validation."""
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(package_module, "_dependencies", counted)
    assert len(build_group_distance_source_envelopes(result, bundle)) == 3
    assert len(calls) == 1


@pytest.mark.parametrize("builder", [build_group_distance_source_envelopes, build_group_distance_package_contract])
@pytest.mark.parametrize("mutation", ["duplicate", "wrong_pair", "foreign_group", "row_dependencies", "manifest_scope"])
def test_saved_result_rejects_invalid_pair_bindings(builder, mutation) -> None:
    """Adapters and contracts reject duplicate, foreign, or inconsistently bound pairs."""
    bundle = _missing_bundle()
    saved = serialize_group_distance_result(calculate_group_pair_distances(bundle))
    if mutation == "duplicate":
        saved["observations"].append(saved["observations"][0])
    elif mutation == "wrong_pair":
        saved["observations"][0]["pair_id"] = "group-pair:foreign"
    elif mutation == "foreign_group":
        saved["observations"][0]["group_ids"] = ["a", "foreign"]
    elif mutation == "row_dependencies":
        saved["observations"][0]["dependencies"]["occupancy"] = "foreign"
    else:
        saved["manifest"]["expected_pair_ids"] = []
    with pytest.raises(ValueError):
        builder(saved, bundle)


@pytest.mark.parametrize("mutation", ["domain", "grid", "occupancy", "free_space_ref"])
def test_changed_input_content_rejects_stale_saved_result(mutation) -> None:
    """Saved pair declarations cannot hide changed geometry or retained field refs."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    if mutation == "domain":
        changed = replace(bundle, domain={"binding": "changed"})
    elif mutation == "grid":
        changed = replace(bundle, grid=replace(bundle.grid, spacing=.5))
    elif mutation == "occupancy":
        changed = replace(bundle, physical_occupancy=())
    else:
        changed = replace(bundle, free_space_samples={"result_ref": "changed"})
    for builder in (build_group_distance_source_envelopes, build_group_distance_package_contract):
        with pytest.raises(ValueError, match="current input bundle"):
            builder(result, changed)


def test_stale_declared_bundle_fingerprints_are_rejected() -> None:
    """A bundle's declared binding must match its actual immutable contents."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    stale = replace(bundle, dependency_fingerprints={"source": "stale"})
    with pytest.raises(ValueError, match="input bundle dependency fingerprints are stale"):
        build_group_distance_source_envelopes(result, stale)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "dependencies"])
def test_separate_repair_rejects_inconsistent_scope_or_dependencies(mutation) -> None:
    """A repair must bind every baseline pair exactly once to the same input."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    repair = _unresolved_repair(result)
    if mutation == "duplicate":
        repair["observations"].append(repair["observations"][0])
    elif mutation == "missing":
        repair["observations"].pop()
    else:
        repair["observations"][0]["dependencies"]["grid"] = "stale"
    with pytest.raises(ValueError):
        build_group_distance_source_envelopes(result, bundle, repaired_result=repair)


@pytest.mark.parametrize("dependency", ["domain", "grid", "occupancy", "free_space_ref"])
def test_contract_identity_binds_all_input_dependencies(dependency) -> None:
    """Each actual dependency changes identity even when raw readings remain missing."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    original = build_group_distance_package_contract(result, bundle)
    if dependency == "domain":
        changed = replace(bundle, domain={"binding": "changed"})
    elif dependency == "grid":
        changed = replace(bundle, grid=replace(bundle.grid, spacing=.5))
    elif dependency == "occupancy":
        changed = replace(bundle, physical_occupancy=())
    else:
        changed = replace(bundle, free_space_samples={"result_ref": "changed"})
    # Rebind only contract metadata: no spatial result is invented or evaluated.
    saved = serialize_group_distance_result(result)
    fingerprints = group_distance_input_fingerprints(changed)
    saved["manifest"]["dependency_fingerprints"] = fingerprints
    for row in saved["observations"]:
        row["dependencies"] = dict(fingerprints)
    contract = build_group_distance_package_contract(saved, changed)
    assert contract["package_identity"] != original["package_identity"]


@pytest.mark.parametrize("version", ["algorithm_version", "schema_version", "edge_support_version", "arithmetic_version", "clearance_policy_version"])
def test_numerical_model_versions_change_contract_and_source_identity(version) -> None:
    """Numerical version changes cannot reuse an old package or source cache identity."""
    bundle = _missing_bundle()
    result = calculate_group_pair_distances(bundle)
    saved = serialize_group_distance_result(result)
    saved["manifest"][version] = "changed-version"
    assert (build_group_distance_package_contract(saved, bundle)["package_identity"]
            != build_group_distance_package_contract(result, bundle)["package_identity"])
    assert (build_group_distance_source_envelopes(saved, bundle)[0].cache_identity["identity"]
            != build_group_distance_source_envelopes(result, bundle)[0].cache_identity["identity"])


@pytest.mark.parametrize("metadata", ["method", "policy", "checkpoint_fingerprint", "pair_method"])
def test_repair_recipe_metadata_changes_package_identity(metadata) -> None:
    """Repair algorithms, policy, checkpoints, and pair methods bind the contract."""
    bundle = _missing_bundle()
    repair = _unresolved_repair(calculate_group_pair_distances(bundle))
    original = build_group_distance_package_contract(repair, bundle)
    if metadata == "pair_method":
        repair["observations"][0]["directional_repair"]["method"] = "changed-method"
    elif metadata == "policy":
        repair[metadata] = {"min_total_m": .6}
    else:
        repair[metadata] = "changed"
    assert build_group_distance_package_contract(repair, bundle)["package_identity"] != original["package_identity"]


def test_saved_free_space_audit_ref_must_match_supplied_ref() -> None:
    """A correct dependency hash cannot authorize a foreign provenance reference."""
    bundle = replace(_missing_bundle(), free_space_samples={"result_ref": "input-ref"})
    result = serialize_group_distance_result(calculate_group_pair_distances(_missing_bundle()))
    fingerprints = group_distance_input_fingerprints(bundle)
    result["manifest"]["dependency_fingerprints"] = fingerprints
    result["manifest"]["free_space_result"] = {"result_ref": "foreign-ref"}
    for row in result["observations"]:
        row["dependencies"] = dict(fingerprints)
    with pytest.raises(ValueError, match="free-space reference differs"):
        build_group_distance_package_contract(result, bundle)


@pytest.mark.parametrize("policy", [None, {}, {"min_left_m": True, "min_right_m": .225, "min_total_m": .55},
                                    {"min_left_m": .225, "min_right_m": -1, "min_total_m": .55},
                                    {"min_left_m": .225, "min_right_m": .225, "min_total_m": float("nan")}])
def test_verified_witness_requires_valid_policy_before_route_reading(policy) -> None:
    """Malformed policy metadata is refused without inventing a spatial witness."""
    with pytest.raises(ValueError, match="clearance policy"):
        package_module._validate_repair_witness({}, {}, (), _missing_bundle(), policy)


def test_verified_witness_requires_complete_edge_and_turn_metadata() -> None:
    """Absent exact record containers cannot be treated as verification evidence."""
    policy = {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55}
    with pytest.raises(ValueError, match="every route edge"):
        package_module._validate_repair_witness({}, {}, (), _missing_bundle(), policy)


@pytest.mark.parametrize("outcome", ["quality", "raw_reading", "candidate", "selected_metadata", "retained_sha256"])
def test_saved_repair_outcome_changes_contract_identity(outcome) -> None:
    """A saved recipe cannot hide changed outcomes or retained artifact contents."""
    bundle = _missing_bundle()
    repair = _unresolved_repair(calculate_group_pair_distances(bundle))
    repair["retained_result_ref"] = {"path": "retained.json", "sha256": "original"}
    original = build_group_distance_package_contract(repair, bundle)
    row = repair["observations"][0]
    if outcome == "quality":
        row["directional_repair"]["quality"] = "infeasible_observed"
    elif outcome == "raw_reading":
        row["center_to_center_euclidean"]["status"] = "unknown"
    elif outcome == "candidate":
        row["directional_repair"]["candidate_distance_m"] = 1.0
    elif outcome == "selected_metadata":
        row["directional_repair"]["exact_witness"] = {"retained_note": "changed"}
    else:
        repair["retained_result_ref"]["sha256"] = "changed"
    assert build_group_distance_package_contract(repair, bundle)["package_identity"] != original["package_identity"]
