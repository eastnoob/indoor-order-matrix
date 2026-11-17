"""Package-owned calculation reuse and independent processed receipt checks."""

from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from features import field_core, group_axis_potential_field as potential
from features import group_distance_evidence_package as distance
from .test_group_distance import _missing_bundle
from .test_evidence_package_output import _source_envelope

# This isolated workspace has a hyphenated directory name, so explicitly bind
# its package for the pre-existing package-relative scene fixtures.
_workspace = ModuleType("lifecycle_workspace")
_workspace.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules.setdefault("lifecycle_workspace", _workspace)
_fixtures = importlib.import_module("lifecycle_workspace.test.test_analysis_requests")
_scene, _object, _request = _fixtures._scene, _fixtures._object, _fixtures._request
free_space = importlib.import_module("lifecycle_workspace.adapters.free_space_evidence_package")


RESULT_KEYS = {"raw_output", "processed_output", "contract", "status", "cache_key", "cache_hit", "cache_status"}


def _potential_sources():
    """Provide two tiny typed, usable parallel-axis observations."""
    original = _source_envelope()
    sources = []
    for group in ("a", "b"):
        target = {"kind": "furniture_group", "id": group, "identity": group}
        record = field_core.EvidenceChannelRecord("overall_group_axis", True, "descriptive",
            {"descriptor": {"angle": 0.0, "strength": 0.5, "direction_status": "defined"}},
            source_ids=("source-" + group,), provenance={"algorithm_version": "test/1", "schema_version": "test/1"})
        identity = field_core.build_field_result_cache_identity(target=target, query=original.query,
            channel_declarations=({"channel": "overall_group_axis"},), input_fingerprint=group,
            source_fingerprint=group, recipe_fingerprint="axis-test", algorithm_version="test/1", schema_version="test/1")
        sources.append(replace(original, target=target, channel_set=("overall_group_axis",),
            raw_status=field_core.FieldResultStatus.COMPUTED, value={"channels": (record,)},
            source_ids=record.source_ids, cache_identity=identity, explanation=""))
    return tuple(sources)


def _forbidden(*args, **kwargs):
    """Fail if a cache hit crosses its expensive calculation boundary."""
    pytest.fail("cache hit recalculated its raw result")


def _check_publication(result, *, hit):
    """Check current freshness separately from the saved precomputation decision."""
    assert set(result) == RESULT_KEYS
    assert result["cache_hit"] is hit
    assert result["status"]["freshness"] == "fresh"
    assert result["status"]["recompute_required"] is False
    assert result["cache_status"]["recompute_required"] is not hit
    if not hit:
        assert result["cache_status"]["reasons"]
        assert result["cache_status"]["affected_targets"]
    assert result["processed_output"].error_code == "OUTPUT_FUNCTION_NOT_CONFIGURED"
    assert result["processed_output"].outputs == ()


@pytest.mark.parametrize("producer", ["distance", "potential", "free_space"])
def test_package_entry_owns_real_calculation_and_hit(tmp_path, monkeypatch, producer):
    """Deleting the reuse branch would rerun a real producer and trip the sentinel."""
    module, name = {"distance": (distance, "run_group_distance_package"),
                    "potential": (potential, "run_group_axis_potential_package"),
                    "free_space": (free_space, "run_free_space_package")}[producer]
    assert hasattr(module, name), "package-owned entry is missing"
    arguments = ((_missing_bundle(),) if producer == "distance" else
                 (_potential_sources(),) if producer == "potential" else
                 (lambda scene: (scene, _request(scene)))(_scene(_object("chair"))))
    run = getattr(module, name)
    first = run(*arguments, cache_directory=tmp_path)
    _check_publication(first, hit=False)
    if producer == "distance":
        assert len(first["raw_output"].outputs) == 6
        assert {item.channel for item in first["raw_output"].outputs} == {"euclidean_distance", "path_distance"}
        monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    elif producer == "potential":
        assert first["raw_output"].package_id == "group-axis-potential"
        monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    else:
        values = {item.observation["cell_locator"]["cell_index"]: item.observation["value"] for item in first["raw_output"].outputs}
        assert values[0] is False and values[10] is True
        monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    again = run(*arguments, cache_directory=tmp_path)
    _check_publication(again, hit=True)
    assert again["cache_key"] == first["cache_key"]
    assert again["raw_output"] == first["raw_output"]


@pytest.mark.parametrize("producer", ["distance", "potential"])
@pytest.mark.parametrize("location", ["model", "model_override", "temporary_override"])
def test_model_locator_uses_sidecar_store_and_reports_reuse(tmp_path, monkeypatch, producer, location):
    """Locator-aware calls use the selected Store root, including explicit overrides."""
    model = tmp_path / "layout.ifc"
    model.write_bytes(b"model locator")
    sidecar = model.with_suffix(".order_analyzer")
    locator = {"model_path": model}
    if location == "model_override":
        sidecar = tmp_path / "chosen"
        locator["cache_directory"] = sidecar
    elif location == "temporary_override":
        sidecar = tmp_path / "chosen"
        locator = {"temporary_cache_root": tmp_path / "temporary", "cache_directory": sidecar}
    if producer == "distance":
        run = distance.run_group_distance_package
        arguments = (_missing_bundle(),)
        owner, boundary = distance, "calculate_group_pair_distances"
    else:
        run = potential.run_group_axis_potential_package
        arguments = (_potential_sources(),)
        owner, boundary = potential, "aggregate_group_axis_potential_outputs"
    first = run(*arguments, **locator)
    assert first["cache_reuse"] == "computed"
    assert first["cache_location"] == str(sidecar.resolve())
    assert tuple(sidecar.glob("sources/*/outputs/*/combined/raw/*/receipt.json"))
    for compatibility in sidecar.glob("*.json"):
        compatibility.unlink()
    monkeypatch.setattr(owner, boundary, _forbidden)
    second = run(*arguments, **locator)
    assert second["cache_hit"] is True
    assert second["cache_reuse"] == "exact_hit"
    assert second["raw_output"] == first["raw_output"]
    if location != "model":
        assert not model.with_suffix(".order_analyzer").exists()
        assert not (tmp_path / "temporary").exists()


@pytest.mark.parametrize("producer", ["distance", "potential", "free_space"])
def test_content_edit_misses_and_restoring_content_hits(tmp_path, monkeypatch, producer):
    """A key based only on prior source IDs would incorrectly reuse edited input."""
    if producer == "distance":
        assert hasattr(distance, "run_group_distance_package"), "package-owned entry is missing"
        run, original = distance.run_group_distance_package, (_missing_bundle(),)
        changed = (replace(original[0], query=replace(original[0].query, revision="meaningful-edit")),)
        boundary, owner = "calculate_group_pair_distances", distance
    elif producer == "potential":
        assert hasattr(potential, "run_group_axis_potential_package"), "package-owned entry is missing"
        run, original = potential.run_group_axis_potential_package, (_potential_sources(),)
        changed = ((replace(original[0][0], support={"edited": True}), original[0][1]),)
        boundary, owner = "aggregate_group_axis_potential_outputs", potential
    else:
        assert hasattr(free_space, "run_free_space_package"), "package-owned entry is missing"
        scene = _scene(_object("chair"))
        run, original = free_space.run_free_space_package, (scene, _request(scene))
        changed = (_scene(_object("chair", (0, 0, 0, 2, 1, 3))), original[1])
        boundary, owner = "execute_analysis_request", free_space.requests
    first = run(*original, cache_directory=tmp_path)
    edited = run(*changed, cache_directory=tmp_path)
    _check_publication(edited, hit=False)
    assert edited["cache_key"] != first["cache_key"]
    monkeypatch.setattr(owner, boundary, _forbidden)
    restored = run(*original, cache_directory=tmp_path)
    _check_publication(restored, hit=True)
    assert restored["raw_output"] == first["raw_output"]


def test_free_space_plane_publication_revision_reuses_with_current_metadata(tmp_path, monkeypatch):
    """Plane publication counters must not recalculate geometry or erase its origin."""
    assert hasattr(free_space, "run_free_space_package"), "package-owned entry is missing"
    scene = _scene(_object("chair"))
    request = _request(scene)
    first = free_space.run_free_space_package(scene, request, cache_directory=tmp_path)
    original = first["raw_output"].source_envelopes[0].value["channels"][0].observation["document"]
    updated = replace(request, plane=replace(request.plane, revision=request.plane.revision + 1))
    scene = replace(scene, context=replace(scene.context, analysis_plane=updated.plane))
    monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    again = free_space.run_free_space_package(scene, updated, cache_directory=tmp_path)
    assert again["cache_hit"] is True
    assert again["cache_key"] == first["cache_key"]
    document = again["raw_output"].source_envelopes[0].value["channels"][0].observation["document"]
    assert document["identity"]["plane_revision"] == updated.plane.revision
    assert document["tables"]["snapshot"]["request"]["plane"]["revision"] == updated.plane.revision
    sample = free_space.wire.decode_cell(document, row=0, column=0)
    assert sample["query"]["frame"] == f"analysis-plane:{updated.plane.identity}:{updated.plane.revision}"
    assert sample["query"]["plane"]["revision"] == updated.plane.revision
    assert sample["query"]["revision"] == document["semantic_key"]
    assert sample["support"]["plane"]["revision"] == updated.plane.revision
    assert sample["value"] is True
    assert dict(document["content_cache"]["origin_result_ref"]) == {"kind": original["kind"], "result_id": original["result_id"], "digest": original["digest"]}
    restored = free_space.run_free_space_package(replace(scene, context=replace(scene.context, analysis_plane=request.plane)), request, cache_directory=tmp_path)
    assert restored["cache_hit"] is True
    assert restored["raw_output"] == first["raw_output"]


def test_free_space_plane_publication_name_reuses_with_current_metadata(tmp_path, monkeypatch):
    """Plane display names must not force a second geometry calculation."""
    assert hasattr(free_space, "run_free_space_package"), "package-owned entry is missing"
    scene = _scene(_object("chair"))
    request = _request(scene)
    first = free_space.run_free_space_package(scene, request, cache_directory=tmp_path)
    updated = replace(request, plane=replace(request.plane, name="renamed display plane"))
    scene = replace(scene, context=replace(scene.context, analysis_plane=updated.plane))
    monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    again = free_space.run_free_space_package(scene, updated, cache_directory=tmp_path)
    assert again["cache_hit"] is True
    assert again["cache_key"] == first["cache_key"]
    document = again["raw_output"].source_envelopes[0].value["channels"][0].observation["document"]
    assert document["tables"]["snapshot"]["request"]["plane"]["name"] == updated.plane.name


def test_parameter_source_change_does_not_recalculate_distance(tmp_path, monkeypatch):
    """A source label changes audit information while preserving the calculation."""
    bundle = _missing_bundle()
    first = distance.run_group_distance_package(bundle, cache_directory=tmp_path)
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    again = distance.run_group_distance_package(
        bundle, cache_directory=tmp_path,
        parameter_sources={"clearance_mode": "gui"},
    )
    assert again["cache_key"] == first["cache_key"]
    assert again["cache_hit"] is True
    assert again["raw_output"] == first["raw_output"]


def test_runner_retains_historical_raw_warning_values(tmp_path, monkeypatch):
    """The runner compares saved and requested warning parameters separately."""
    from features.evidence_package_parameters import ParameterImpact, ParameterSchema, ParameterSpec

    schema = ParameterSchema(distance.PACKAGE_ID, "contract-warning/1", (
        ParameterSpec("review_m", float, 0.01, unit="m", impact=ParameterImpact.REUSE_WITH_WARNING),
    ))
    monkeypatch.setattr(distance, "build_group_distance_parameter_snapshot",
                        lambda *args, **kwargs: schema.resolve())
    first = distance.run_group_distance_package(_missing_bundle(), cache_directory=tmp_path)
    monkeypatch.setattr(distance, "build_group_distance_parameter_snapshot",
                        lambda *args, **kwargs: schema.resolve({"review_m": 0.02}))
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    again = distance.run_group_distance_package(_missing_bundle(), cache_directory=tmp_path)
    status = again["cache_status"]["parameter_status"]
    assert again["raw_output"] == first["raw_output"] and again["cache_hit"]
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert status["exact_match"] is False
    assert [item["parameter"] for item in status["warnings"]] == ["review_m"]


def test_potential_raw_warning_uses_historical_contract_status(tmp_path, monkeypatch):
    """Publication target expansion must not hide a raw warning-only reuse."""
    from features.evidence_package_parameters import ParameterImpact, ParameterSchema, ParameterSpec

    schema = ParameterSchema(potential.PACKAGE_ID, "raw-warning/1", (
        ParameterSpec("review_m", float, 0.01, unit="m", impact=ParameterImpact.REUSE_WITH_WARNING),
    ))
    monkeypatch.setattr(potential, "build_group_axis_parameter_snapshot",
                        lambda *args, **kwargs: schema.resolve())
    first = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path,
    )
    monkeypatch.setattr(potential, "build_group_axis_parameter_snapshot",
                        lambda *args, **kwargs: schema.resolve({"review_m": 0.02}))
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    again = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path,
    )
    status = again["cache_status"]["parameter_status"]
    assert again["cache_hit"] is True
    assert again["cache_status"]["recompute_required"] is False
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert status["exact_match"] is False and status["warnings"]


def test_runner_retains_historical_processed_warning_values(tmp_path, monkeypatch):
    """Warning reuse preserves transform parameters and skips both callbacks."""
    from features.evidence_package_parameters import ParameterImpact, ParameterSchema, ParameterSpec

    schema = ParameterSchema(potential.PACKAGE_ID, "processed-warning/1", (
        ParameterSpec("review_m", float, 0.01, unit="m", impact=ParameterImpact.REUSE_WITH_WARNING),
    ))
    base = _processor()
    old = field_core.EvidenceOutputProcessor(
        base.function_id, base.version, base.function, parameter_schema=schema,
    )
    first = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path, output_processor=old,
    )
    current = field_core.EvidenceOutputProcessor(
        base.function_id, base.version, _forbidden, {"review_m": 0.02},
        parameter_schema=schema,
    )
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    again = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path, output_processor=current,
    )
    status = again["cache_status"]["processed_parameter_status"]
    assert again["processed_output"] == first["processed_output"]
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert status["exact_match"] is False and status["warnings"]


def _processor(version="1", function=None, core=field_core):
    """Configure one explicit transform with independently hand-checked scalar output."""
    def transform(raw, parameters):
        """Publish a scalar while retaining an exact raw channel lineage address."""
        source = next(item for item in raw.outputs if item.status is core.FieldResultStatus.COMPUTED and item.observation is not None)
        return (core.EvidenceOutputChannel(
            target=source.target, channel="processed_test", observation=0.25,
            status=source.status, explanation=source.explanation,
            scale=core.EvidenceOutputScale(meaning="Test scale", value_range=(0, 1),
                endpoint_meanings={"0": "zero", "1": "one"}),
            derived_from=(core.EvidencePackageChannelReference(raw.package_id, raw.output_identity,
                source.target["identity"], source.channel),), source_ids=source.source_ids,
        ),)
    return core.EvidenceOutputProcessor("lifecycle-test", version, function or transform)


def test_processed_receipt_skips_callback_and_recipe_change_reuses_raw(tmp_path, monkeypatch):
    """Running a cached callback or using an obsolete recipe would change visible output."""
    assert hasattr(potential, "run_group_axis_potential_package"), "package-owned entry is missing"
    sources = _potential_sources()
    first = potential.run_group_axis_potential_package(sources, cache_directory=tmp_path, output_processor=_processor())
    assert first["processed_output"].error_code is None
    assert first["processed_output"].outputs[0].observation == 0.25
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    second = potential.run_group_axis_potential_package(sources, cache_directory=tmp_path, output_processor=_processor(function=_forbidden))
    assert second["processed_output"] == first["processed_output"]
    changed = potential.run_group_axis_potential_package(sources, cache_directory=tmp_path, output_processor=_processor("2"))
    assert changed["cache_hit"] is True
    assert changed["cache_key"] == first["cache_key"]
    assert changed["processed_output"].processing_identity != first["processed_output"].processing_identity


def test_processed_versions_restore_independently_after_parameter_round_trip(tmp_path, monkeypatch):
    """Each processed recipe version remains addressable after switching away and back."""
    sources = _potential_sources()
    first = potential.run_group_axis_potential_package(
        sources, cache_directory=tmp_path, output_processor=_processor("1"),
    )
    second = potential.run_group_axis_potential_package(
        sources, cache_directory=tmp_path, output_processor=_processor("2"),
    )
    assert first["processed_output"].processing_identity != second["processed_output"].processing_identity
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    restored = potential.run_group_axis_potential_package(
        sources, cache_directory=tmp_path, output_processor=_processor("1", function=_forbidden),
    )
    assert restored["processed_output"] == first["processed_output"]
    assert restored["cache_status"]["processed_reuse_origin"]["mode"] == "cache_hit"


def test_free_space_grid_versions_restore_without_recalculation(tmp_path, monkeypatch):
    """Changing lattice spacing creates a separate raw version and restores the first one."""
    scene = _scene(_object("chair"))
    request_one = _request(scene)
    request_two = replace(request_one, sampling=replace(request_one.sampling, spacing=2.0))
    first = free_space.run_free_space_package(scene, request_one, cache_directory=tmp_path)
    second = free_space.run_free_space_package(scene, request_two, cache_directory=tmp_path)
    assert first["cache_key"] != second["cache_key"]
    monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    restored = free_space.run_free_space_package(scene, request_one, cache_directory=tmp_path)
    assert restored["cache_hit"] is True
    assert restored["cache_key"] == first["cache_key"]
    assert restored["raw_output"] == first["raw_output"]


def test_free_space_receipt_persists_typed_parameter_snapshot(tmp_path, monkeypatch):
    """New authenticated receipts compare typed parameters without legacy adoption."""
    scene = _scene(_object("chair"))
    request = _request(scene)
    first = free_space.run_free_space_package(scene, request, cache_directory=tmp_path)
    path = tmp_path / (first["cache_key"] + ".json")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert "parameter_snapshot" in receipt["contract"]
    monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    again = free_space.run_free_space_package(scene, request, cache_directory=tmp_path)
    assert again["cache_status"]["reuse_origin"]["mode"] == "cache_hit"
    assert again["cache_status"]["parameter_status"]["exact_match"] is True


def test_distance_legacy_raw_receipt_requires_owner_adoption_and_preserves_bytes(tmp_path, monkeypatch):
    """A known legacy filename is adopted only after the distance owner rebuilds parameters."""
    from features import evidence_package_storage as storage

    bundle = _missing_bundle()
    first = distance.run_group_distance_package(bundle)
    legacy_contract = storage.legacy_candidate_contract(first["contract"])
    legacy_key = legacy_contract["package_identity"]
    legacy_path = tmp_path / (legacy_key + ".json")
    storage.save_raw_output(
        legacy_path, cache_key=legacy_key, contract=legacy_contract,
        raw_output=first["raw_output"],
    )
    original_bytes = legacy_path.read_bytes()
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    adopted = distance.run_group_distance_package(bundle, cache_directory=tmp_path)
    assert adopted["cache_hit"] is True
    assert adopted["raw_output"] == first["raw_output"]
    assert adopted["cache_status"]["reuse_origin"]["mode"] == "adopted_legacy"
    assert legacy_path.read_bytes() == original_bytes


def test_potential_legacy_processed_receipt_is_owner_verified(tmp_path, monkeypatch):
    """A schema-less processed receipt is reopened only after parameter reconstruction."""
    from features import evidence_package_storage as storage
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec

    schema = ParameterSchema(potential.PACKAGE_ID, "legacy-processed/1", (
        ParameterSpec("review_m", float, 0.01, unit="m"),
    ))
    base = _processor()
    typed_processor = field_core.EvidenceOutputProcessor(
        base.function_id, base.version, base.function, {"review_m": 0.01},
        parameter_schema=schema,
    )
    first = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path, output_processor=typed_processor,
    )
    raw = first["raw_output"]
    legacy_output = replace(first["processed_output"], parameter_snapshot=None)
    legacy_key = storage.legacy_processed_cache_key(raw, typed_processor)
    legacy_path = tmp_path / ("processed-" + legacy_key + ".json")
    storage.save_processed_output(legacy_path, legacy_output)
    typed_path = tmp_path / ("processed-" + storage.processed_cache_key(raw, typed_processor) + ".json")
    typed_path.unlink()
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    adopted = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path,
        output_processor=replace(typed_processor, function=_forbidden),
    )
    assert adopted["processed_output"].outputs == first["processed_output"].outputs
    assert adopted["cache_status"]["processed_reuse_origin"]["mode"] == "adopted_legacy"
    assert adopted["cache_status"]["processed_parameter_status"]["exact_match"] is False


def test_legacy_processed_parameter_mismatch_is_a_miss(tmp_path):
    """An old processed identity for a different effective value cannot inherit defaults."""
    from features import evidence_package_storage as storage
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec

    schema = ParameterSchema(potential.PACKAGE_ID, "legacy-processed/2", (
        ParameterSpec("review_m", float, 0.01, unit="m"),
    ))
    base = _processor()
    old_processor = field_core.EvidenceOutputProcessor(
        base.function_id, base.version, base.function, {"review_m": 0.01},
        parameter_schema=schema,
    )
    current_processor = field_core.EvidenceOutputProcessor(
        base.function_id, base.version, base.function, {"review_m": 0.02},
        parameter_schema=schema,
    )
    first = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path, output_processor=old_processor,
    )
    legacy_output = replace(first["processed_output"], parameter_snapshot=None)
    wrong_path = tmp_path / ("processed-" + storage.legacy_processed_cache_key(first["raw_output"], current_processor) + ".json")
    storage.save_processed_output(wrong_path, legacy_output)
    result = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path, output_processor=current_processor,
    )
    assert result["processed_output"].processing_identity != first["processed_output"].processing_identity


@pytest.mark.parametrize("damage", ["json", "binding", "output"])
def test_raw_receipt_corruption_forces_real_recomputation(tmp_path, monkeypatch, damage):
    """Corrupt bytes or a mismatched input binding must never become a typed hit."""
    assert hasattr(potential, "run_group_axis_potential_package"), "package-owned entry is missing"
    first = potential.run_group_axis_potential_package(_potential_sources(), cache_directory=tmp_path)
    path = tmp_path / (first["cache_key"] + ".json")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if damage == "json":
        path.write_text("{", encoding="utf-8")
    else:
        if damage == "binding":
            receipt["cache_key"] = "foreign"
        else:
            receipt["raw_output"]["package_id"] = "foreign"
        path.write_text(json.dumps(receipt), encoding="utf-8")
    again = potential.run_group_axis_potential_package(_potential_sources(), cache_directory=tmp_path)
    assert again["cache_hit"] is False
    assert again["raw_output"] == first["raw_output"]


def test_potential_value_and_order_changes_invalidate_actual_output(tmp_path):
    """Reusing old IDs alone would hide edited axis values or producer audit order."""
    sources = _potential_sources()
    first = potential.run_group_axis_potential_package(iter(sources), cache_directory=tmp_path)
    record = sources[0].value["channels"][0]
    changed_record = replace(record, observation={"descriptor": {"angle": 90., "strength": .5, "direction_status": "defined"}})
    edited_sources = (replace(sources[0], value={"channels": (changed_record,)}), sources[1])
    edited = potential.run_group_axis_potential_package(edited_sources, cache_directory=tmp_path)
    assert edited["cache_hit"] is False
    assert edited["cache_key"] != first["cache_key"]
    coherence = next(item for item in edited["raw_output"].outputs if item.channel == "direction_coherence")
    assert coherence.observation["value"] == pytest.approx(0, abs=1e-15)
    reordered = potential.run_group_axis_potential_package(tuple(reversed(sources)), cache_directory=tmp_path)
    assert reordered["cache_hit"] is False
    assert reordered["cache_key"] != first["cache_key"]


def test_distance_full_repair_content_changes_key_without_running_kernel(tmp_path, monkeypatch):
    """Nonselected saved repair evidence still belongs to the complete cache input."""
    from features.group_distance import calculate_group_pair_distances
    from .test_group_distance_evidence_package import _unresolved_repair
    bundle = _missing_bundle()
    saved = _unresolved_repair(calculate_group_pair_distances(bundle))
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    first = distance.run_group_distance_package(bundle, repaired_result=saved, cache_directory=tmp_path)
    edited_saved = {**saved, "audit_note": "complete supplied repair input changed"}
    edited = distance.run_group_distance_package(bundle, repaired_result=edited_saved, cache_directory=tmp_path)
    assert edited["cache_hit"] is False
    assert edited["cache_key"] != first["cache_key"]
    assert distance.run_group_distance_package(bundle, repaired_result=saved, cache_directory=tmp_path)["cache_hit"] is True


@pytest.mark.parametrize("producer", ["distance", "potential"])
def test_package_algorithm_version_invalidates_cache(tmp_path, monkeypatch, producer):
    """A producer version change must not reuse a prior typed raw publication."""
    module, run, arguments = ((distance, distance.run_group_distance_package, (_missing_bundle(),))
        if producer == "distance" else (potential, potential.run_group_axis_potential_package, (_potential_sources(),)))
    first = run(*arguments, cache_directory=tmp_path)
    monkeypatch.setattr(module, "OUTPUT_FUNCTION_VERSION", module.OUTPUT_FUNCTION_VERSION + "-changed")
    second = run(*arguments, cache_directory=tmp_path)
    assert second["cache_hit"] is False
    assert second["cache_key"] != first["cache_key"]


@pytest.mark.parametrize("damage", ["corrupt", "foreign_recipe", "foreign_raw"])
def test_processed_receipt_rejects_corrupt_or_foreign_content(tmp_path, monkeypatch, damage):
    """A processed file needs exact raw content and independently current recipe binding."""
    sources = _potential_sources()
    first = potential.run_group_axis_potential_package(sources, cache_directory=tmp_path, output_processor=_processor())
    path, = tmp_path.glob("processed-*.json")
    if damage == "corrupt":
        path.write_text("{", encoding="utf-8")
    else:
        foreign = (replace(first["processed_output"], processor_version="obsolete") if damage == "foreign_recipe" else
                   replace(first["processed_output"], raw_payload_fingerprint="foreign"))
        path.write_text(json.dumps(field_core.serialize_evidence_processed_output(foreign)), encoding="utf-8")
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    result = potential.run_group_axis_potential_package(sources, cache_directory=tmp_path, output_processor=_processor())
    assert result["cache_hit"] is True
    assert result["processed_output"] == first["processed_output"]
    assert json.loads(path.read_text(encoding="utf-8"))["raw_payload_fingerprint"] == first["processed_output"].raw_payload_fingerprint


def test_processing_error_is_empty_and_not_cached(tmp_path):
    """A failed configured callback must retry later and never fall back to raw channels."""
    def broken(raw, parameters):
        """Model a real configured transformation failure."""
        raise ValueError("failed transformation")
    first = potential.run_group_axis_potential_package(_potential_sources(), cache_directory=tmp_path,
        output_processor=_processor(function=broken))
    assert first["processed_output"].error_code == "OUTPUT_PROCESSING_FAILED"
    assert first["processed_output"].outputs == ()
    assert not list(tmp_path.glob("processed-*.json"))
    second = potential.run_group_axis_potential_package(_potential_sources(), cache_directory=tmp_path, output_processor=_processor())
    assert second["cache_hit"] is True
    assert second["processed_output"].outputs[0].observation == .25


def test_atomic_raw_replacement_failure_preserves_final_bytes(tmp_path, monkeypatch):
    """A failed shared storage replacement cannot destroy a previously valid receipt."""
    from features import evidence_package_storage as storage
    first = potential.run_group_axis_potential_package(_potential_sources(), cache_directory=tmp_path)
    path = tmp_path / (first["cache_key"] + ".json")
    prior = path.read_bytes()
    def refused(*args, **kwargs):
        """Fail only at the final atomic publication boundary."""
        raise OSError("atomic replacement refused")
    monkeypatch.setattr(storage.os, "replace", refused)
    with pytest.raises(OSError, match="atomic replacement refused"):
        storage.save_raw_output(path, cache_key=first["cache_key"], contract=first["contract"], raw_output=first["raw_output"])
    assert path.read_bytes() == prior
    assert list(tmp_path.glob("*.partial")) == []


def test_foreign_typed_raw_content_cannot_use_current_contract(tmp_path):
    """A coherent receipt still cannot attach foreign raw sources to current inputs."""
    from features import evidence_package_storage as storage
    first = potential.run_group_axis_potential_package(_potential_sources(), cache_directory=tmp_path)
    foreign_sources = (replace(_potential_sources()[0], support={"foreign": True}), _potential_sources()[1])
    foreign = potential.run_group_axis_potential_package(foreign_sources)
    storage.save_raw_output(tmp_path / (first["cache_key"] + ".json"), cache_key=first["cache_key"],
        contract=first["contract"], raw_output=foreign["raw_output"])
    restored = potential.run_group_axis_potential_package(_potential_sources(), cache_directory=tmp_path)
    assert restored["cache_hit"] is False
    assert restored["raw_output"] == first["raw_output"]


def test_distance_empty_contract_targets_match_returned_publication(tmp_path):
    """A diagnostic target must use the same dependency recipe as its source envelope."""
    result = distance.run_group_distance_package(replace(_missing_bundle(), groups=()), cache_directory=tmp_path)
    assert result["contract"]["target_ids"] == sorted({item.target["identity"] for item in result["raw_output"].outputs})


@pytest.mark.parametrize("namespace", [None, "lifecycle-scene"])
def test_potential_publication_status_names_actual_outputs(tmp_path, monkeypatch, namespace):
    """UI invalidation must name field/family addresses rather than input group IDs."""
    result = potential.run_group_axis_potential_package(_potential_sources(), scene_namespace=namespace, cache_directory=tmp_path)
    targets = sorted({item.target["identity"] for item in result["raw_output"].outputs})
    assert result["contract"]["target_ids"] == targets
    assert result["cache_status"]["affected_targets"] == targets
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    again = potential.run_group_axis_potential_package(_potential_sources(), scene_namespace=namespace, cache_directory=tmp_path)
    assert again["cache_hit"] is True
    assert again["contract"] == result["contract"]


def test_free_space_rehashed_processed_tamper_requires_authentication(tmp_path, monkeypatch):
    """Recomputing a public SHA cannot authorize changed free-space processed readings."""
    core = importlib.import_module("lifecycle_workspace.features.field_core")
    scene = _scene(_object("chair"))
    first = free_space.run_free_space_package(scene, _request(scene), cache_directory=tmp_path,
        output_processor=_processor(core=core))
    assert first["processed_output"].outputs[0].observation == .25
    path, = tmp_path.glob("processed-*.json")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    payload = receipt.get("processed_output", receipt)
    payload["outputs"][0]["observation"] = .75
    payload["payload_fingerprint"] = core.fingerprint_evidence_dependency({
        key: value for key, value in payload.items() if key != "payload_fingerprint"})
    path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    second = free_space.run_free_space_package(scene, _request(scene), cache_directory=tmp_path,
        output_processor=_processor(core=core))
    assert second["cache_hit"] is True
    assert second["processed_output"].outputs[0].observation == .25


def test_distance_foreign_raw_cannot_be_rebound_to_current_bundle(tmp_path):
    """Saved output queries and source dependency bindings must match the supplied bundle."""
    from features import evidence_package_storage as storage
    bundle = _missing_bundle()
    first = distance.run_group_distance_package(bundle, cache_directory=tmp_path)
    foreign = distance.run_group_distance_package(replace(bundle, query=replace(bundle.query, revision="foreign")))
    storage.save_raw_output(tmp_path / (first["cache_key"] + ".json"), cache_key=first["cache_key"],
        contract=first["contract"], raw_output=foreign["raw_output"])
    restored = distance.run_group_distance_package(bundle, cache_directory=tmp_path)
    assert restored["cache_hit"] is False
    assert restored["raw_output"] == first["raw_output"]


def test_free_space_authenticated_processed_hit_skips_callback(tmp_path, monkeypatch):
    """The authenticated processing port reuses successful recipes without geometry or callbacks."""
    core = importlib.import_module("lifecycle_workspace.features.field_core")
    scene = _scene(_object("chair"))
    first = free_space.run_free_space_package(scene, _request(scene), cache_directory=tmp_path,
        output_processor=_processor(core=core))
    monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    again = free_space.run_free_space_package(scene, _request(scene), cache_directory=tmp_path,
        output_processor=_processor(core=core, function=_forbidden))
    assert again["processed_output"] == first["processed_output"]
    edited = free_space.run_free_space_package(scene, _request(scene), cache_directory=tmp_path,
        output_processor=_processor("2", core=core))
    assert edited["cache_hit"] is True
    assert edited["cache_key"] == first["cache_key"]
    assert edited["processed_output"].processing_identity != first["processed_output"].processing_identity


@pytest.mark.parametrize("observation_count", [1, 0])
def test_distance_saved_subset_scope_matches_publication_and_reuses_cache(tmp_path, monkeypatch, observation_count):
    """Accepted saved subsets own their actual target scope, including the empty diagnostic."""
    from features.group_distance import calculate_group_pair_distances
    from .test_group_distance_evidence_package import _unresolved_repair
    bundle = _missing_bundle()
    saved = _unresolved_repair(calculate_group_pair_distances(bundle))
    saved["observations"] = saved["observations"][:observation_count]
    saved["manifest"]["expected_pair_ids"] = [row["pair_id"] for row in saved["observations"]]
    saved["manifest"]["expected_pair_count"] = observation_count
    legacy = distance.evaluate_group_distance_package(bundle, repaired_result=saved)
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    first = distance.run_group_distance_package(bundle, repaired_result=saved, cache_directory=tmp_path)
    targets = sorted({item.target["identity"] for item in legacy.outputs})
    assert len(legacy.outputs) == 2
    assert first["raw_output"] == legacy
    assert first["contract"]["target_ids"] == targets
    assert first["cache_status"]["affected_targets"] == targets
    assert first["cache_status"]["recompute_required"] is True
    monkeypatch.setattr(distance, "evaluate_group_distance_package", _forbidden)
    again = distance.run_group_distance_package(bundle, repaired_result=saved, cache_directory=tmp_path)
    assert again["cache_hit"] is True
    assert again["cache_status"]["recompute_required"] is False
    assert again["raw_output"] == legacy
    assert again["contract"] == first["contract"]


def test_potential_reverse_producer_order_reuses_cache_and_retains_audit_order(tmp_path, monkeypatch):
    """Canonical saved source order must not invalidate the original producer-order receipt."""
    sources = _potential_sources()
    reversed_sources = tuple(reversed(sources))
    first = potential.run_group_axis_potential_package(reversed_sources, cache_directory=tmp_path)
    aggregate = next(item for item in first["raw_output"].outputs if item.channel == "aggregate_direction")
    assert tuple(item["group_id"] for item in aggregate.observation["per_group"]) == ("b", "a")
    forward = potential.run_group_axis_potential_package(sources, cache_directory=tmp_path)
    assert forward["cache_key"] != first["cache_key"]
    assert field_core.serialize_evidence_package_output(forward["raw_output"]) != field_core.serialize_evidence_package_output(first["raw_output"])
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    again = potential.run_group_axis_potential_package(reversed_sources, cache_directory=tmp_path)
    assert again["cache_hit"] is True
    assert again["cache_key"] == first["cache_key"]
    assert again["raw_output"] == first["raw_output"]


def test_typed_effective_values_one_two_one_route_values_and_callback_counts(tmp_path, monkeypatch):
    """One fixed processor version computes each effective value once and restores its receipt."""
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec

    schema = ParameterSchema(potential.PACKAGE_ID, "effective-values/1", (
        ParameterSpec("value", float, 1.0),
    ))
    base = _processor()
    calls = []

    def scaled(raw, parameters):
        """Expose the actual typed effective value through a bounded numeric channel."""
        calls.append(parameters["value"])
        return tuple(replace(item, observation=item.observation * parameters["value"])
                     for item in base.function(raw, parameters))

    def configured(value, function):
        """Keep recipe identity/version fixed while changing its owned effective value."""
        return field_core.EvidenceOutputProcessor(
            base.function_id, base.version, function, {"value": value},
            parameter_schema=schema,
        )

    first = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path,
        output_processor=configured(1, scaled))
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    second = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path,
        output_processor=configured(2, scaled))
    assert first["processed_output"].error_code is None
    assert second["processed_output"].error_code is None
    assert first["processed_output"].processor_version == second["processed_output"].processor_version
    assert first["processed_output"].outputs[0].observation == 0.25
    assert second["processed_output"].outputs[0].observation == 0.5
    assert calls == [1.0, 2.0]
    assert all(type(value) is float for value in calls)
    assert first["processed_output"].processing_identity != second["processed_output"].processing_identity
    retained_path = tmp_path / (
        "processed-" + first["processed_output"].processing_identity + ".json")
    retained = retained_path.read_bytes()
    restored = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path,
        output_processor=configured(1, _forbidden))
    assert restored["processed_output"] == first["processed_output"]
    assert restored["processed_output"].outputs[0].observation == 0.25
    assert calls == [1.0, 2.0]
    assert retained_path.read_bytes() == retained


def test_free_space_grid_parameters_reach_real_execution_and_samples(tmp_path, monkeypatch):
    """Two real lattices execute separately and restoring the first reuses its exact bytes."""
    scene = _scene(_object("chair"))
    coarse = _request(scene)
    fine = replace(coarse, sampling=replace(
        coarse.sampling, spacing=0.5, n_rows=8, n_cols=8))
    execute = free_space.requests.execute_analysis_request
    calls = []

    def counted(scene_value, request_value, *args, **kwargs):
        """Observe the real executor's effective sampling without manufacturing results."""
        sampling = request_value.sampling
        calls.append((sampling.spacing, sampling.n_rows, sampling.n_cols))
        return execute(scene_value, request_value, *args, **kwargs)

    monkeypatch.setattr(free_space.requests, "execute_analysis_request", counted)
    first = free_space.run_free_space_package(scene, coarse, cache_directory=tmp_path)
    raw_path = tmp_path / (first["cache_key"] + ".json")
    retained = raw_path.read_bytes()
    second = free_space.run_free_space_package(scene, fine, cache_directory=tmp_path)
    assert calls == [(1.0, 4, 4), (0.5, 8, 8)]
    assert not first["cache_hit"] and not second["cache_hit"]
    assert len(first["raw_output"].outputs) == 16
    assert len(second["raw_output"].outputs) == 64
    for result, spacing, count in ((first, 1.0, 16), (second, 0.5, 64)):
        document = result["raw_output"].source_envelopes[0].value["channels"][0].observation["document"]
        assert document["tables"]["lattice"]["spacing"] == spacing
        assert len(document["cells"]) == count
        assert result["contract"]["parameter_snapshot"]["calculated_parameters"]["grid_spacing_m"] == spacing
        for output in result["raw_output"].outputs:
            locator = output.observation["cell_locator"]
            sample = free_space.wire.decode_cell(
                document, row=locator["row"], column=locator["column"])
            assert output.observation["physical_occupancy"] is sample["value"]
            assert output.observation["value"] is (
                None if sample["value"] is None else not sample["value"])
    assert first["cache_key"] != second["cache_key"]
    monkeypatch.setattr(free_space.requests, "execute_analysis_request", _forbidden)
    restored = free_space.run_free_space_package(scene, coarse, cache_directory=tmp_path)
    assert restored["cache_hit"] is True
    assert restored["raw_output"] == first["raw_output"]
    assert restored["cache_key"] == first["cache_key"]
    assert calls == [(1.0, 4, 4), (0.5, 8, 8)]
    assert raw_path.read_bytes() == retained


def test_authenticated_explicit_legacy_processed_warning_adopts_saved_values(tmp_path):
    """Authenticated explicit-path adoption verifies historical parameters before warning reuse."""
    core = importlib.import_module("lifecycle_workspace.features.field_core")
    parameters = importlib.import_module(
        "lifecycle_workspace.features.evidence_package_parameters")
    storage = importlib.import_module(
        "lifecycle_workspace.features.evidence_package_storage")
    scene = _scene(_object("chair"))
    base = _processor(core=core)
    old_processor = core.EvidenceOutputProcessor(
        base.function_id, base.version, base.function, {"review_m": 0.01})
    first = free_space.run_free_space_package(
        scene, _request(scene), cache_directory=tmp_path,
        output_processor=old_processor)
    saved = first["processed_output"]
    assert saved.error_code is None and saved.parameter_snapshot is None
    path = tmp_path / ("processed-" + saved.processing_identity + ".json")
    retained = path.read_bytes()
    receipt = json.loads(retained)
    original_identity = __import__("hashlib").sha256(json.dumps({
        "package_id": saved.package_id,
        "raw_output_identity": saved.raw_output_identity,
        "raw_payload_fingerprint": saved.raw_payload_fingerprint,
        "processor_id": saved.processor_id,
        "processor_version": saved.processor_version,
        "parameters": receipt["processed_output"]["parameters"],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert original_identity == saved.processing_identity
    schema = parameters.ParameterSchema(saved.package_id, "authenticated-warning/1", (
        parameters.ParameterSpec(
            "review_m", float, 0.02, unit="m",
            impact=parameters.ParameterImpact.REUSE_WITH_WARNING),
    ))
    processor = core.EvidenceOutputProcessor(
        base.function_id, base.version, _forbidden, parameter_schema=schema)
    assert storage.legacy_processed_cache_key(first["raw_output"], processor) != original_identity
    secret = (tmp_path / ".free_space_cache_key").read_bytes()
    lookup = free_space._read_processed_cache_entry(
        tmp_path / "typed-missing.json", raw_output=first["raw_output"],
        processor=processor, secret=secret, legacy_path=path,
        legacy_processed_adopter=storage.reconstruct_legacy_processed_snapshot)
    assert lookup is not None and lookup.processed_output.outputs == saved.outputs
    assert json.dumps(
        lookup.processed_output.parameter_snapshot.to_json()["calculated_parameters"],
        sort_keys=True,
    ) == json.dumps({"review_m": 0.01}, sort_keys=True)
    assert lookup.parameter_status["requested_parameters"]["review_m"] == 0.02
    assert lookup.parameter_status["warnings"] and not lookup.parameter_status["exact_match"]
    assert lookup.reuse_origin["mode"] == "adopted_legacy"
    assert lookup.reuse_origin["origin_processing_identity"] == original_identity
    assert lookup.reuse_origin["origin_payload_fingerprint"] == \
        receipt["processed_output"]["payload_fingerprint"]
    calculation_schema = replace(schema, specs=(replace(
        schema.specs[0], impact=parameters.ParameterImpact.RECOMPUTE_REQUIRED),))
    incompatible = core.EvidenceOutputProcessor(
        base.function_id, base.version, _forbidden,
        parameter_schema=calculation_schema)
    assert free_space._read_processed_cache_entry(
        tmp_path / "typed-missing.json", raw_output=first["raw_output"],
        processor=incompatible, secret=secret, legacy_path=path,
        legacy_processed_adopter=storage.reconstruct_legacy_processed_snapshot,
    ) is None
    assert path.read_bytes() == retained


def test_authenticated_processed_outer_identity_must_match_its_payload(tmp_path):
    """An authenticated envelope cannot relabel an otherwise valid processed receipt."""
    core = importlib.import_module("lifecycle_workspace.features.field_core")
    scene = _scene(_object("chair"))
    processor = _processor(core=core)
    result = free_space.run_free_space_package(
        scene, _request(scene), cache_directory=tmp_path,
        output_processor=processor)
    path = tmp_path / ("processed-" + result["processed_output"].processing_identity + ".json")
    receipt = json.loads(path.read_bytes())
    receipt["processing_identity"] = "foreign-envelope-identity"
    secret = (tmp_path / ".free_space_cache_key").read_bytes()
    receipt["auth_tag"] = free_space._receipt_tag(receipt, secret)
    free_space._write_cache(path, receipt)
    retained = path.read_bytes()
    assert free_space._read_processed_cache_entry(
        path, raw_output=result["raw_output"], processor=processor, secret=secret,
    ) is None
    assert path.read_bytes() == retained
