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
