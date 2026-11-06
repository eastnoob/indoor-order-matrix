"""Free-space package preservation, explicit semantics, and authenticated cache reuse."""

from dataclasses import replace
import importlib
import json

import pytest

from ..adapters import blender_analysis_result_wire as wire
from ..features import free_space_evidence_package as package_module
from ..features.field_core import serialize_evidence_package_output, evaluate_evidence_package_freshness
from .test_analysis_requests import _scene, _object, _request, _plane
from .test_blender_analysis_session import _compact_document, _read_context


def _modules():
    """Load the new feature at test execution so absence is an explicit RED assertion."""
    package = __package__.rsplit(".", 1)[0]
    assert importlib.util.find_spec(package + ".features.free_space_evidence_package"), "free-space package is missing"
    core = importlib.import_module(package + ".features.free_space_evidence_package")
    adapter = importlib.import_module(package + ".adapters.free_space_evidence_package")
    return core, adapter


def _open(document):
    """Authenticate exact fixture bytes with declared historical consumer expectations."""
    ref = wire.ResultRef(document["kind"], document["result_id"], document["digest"])
    return wire.open_analysis_result([document], result_ref=ref, context=_read_context(document))


def _document(result):
    """Read the one compact source document through the promised package path."""
    return result.source_envelopes[0].value["channels"][0].observation["document"]


def test_single_source_preserves_every_raw_sample_and_cell_lineage():
    """Package cells remain exact references to all seven original sample fields."""
    core, adapter = _modules()
    run, document = _compact_document()
    before = wire.canonical_json(document)
    result = adapter.evaluate_saved_free_space_package(_open(document))
    assert len(result.source_envelopes) == 1
    envelope = result.source_envelopes[0]
    assert envelope.target["kind"] == "free_space_field_scope"
    assert envelope.channel_set == ("physical_occupancy",)
    retained = _document(result)
    assert wire.canonical_json(retained) == before
    assert len(result.outputs) == len(document["cells"])
    outputs = {(item.observation["cell_locator"]["row"], item.observation["cell_locator"]["column"]): item
               for item in result.outputs}
    for cell in document["cells"]:
        row, column = cell["row"], cell["column"]
        original = wire.decode_cell(document, row=row, column=column)
        assert wire.decode_cell(retained, row=row, column=column) == original
        assert set(original) == {"value", "status", "query", "support", "source_ids", "provenance", "explanation"}
        output = outputs[row, column]
        assert output.channel == "free_space"
        assert output.observation["physical_occupancy"] is original["value"]
        assert output.observation["raw_status"] == original["status"]
        assert output.observation["value"] is (None if original["value"] is None else not original["value"])
        assert output.derived_from[0].channel == "physical_occupancy"
        assert output.derived_from[0].result_identity == envelope.cache_identity["identity"]
        assert output.source_ids == tuple(original["source_ids"])
        assert "selected_records" not in output.provenance
        assert output.observation["cell_locator"]["result_ref"]["digest"] == document["digest"]
    assert wire.canonical_json(document) == before
    with pytest.raises(TypeError):
        retained["cells"][0]["value"] = False
    assert "walkability" in result.outputs[0].scale.meaning
    assert core.build_free_space_evidence_package().package_id == result.package_id


def test_six_statuses_keep_nulls_and_explanations():
    """Only Boolean known/conditional occupancies have a Boolean complement."""
    _, adapter = _modules()
    _, document = _compact_document()
    statuses = wire.STATUSES
    for index, cell in enumerate(document["cells"]):
        status = statuses[index % len(statuses)]
        cell["status"] = status
        cell["value"] = (index % 2 == 0) if status in statuses[:2] else None
        cell["explanation_ref"] = len(document["tables"]["values"])
        document["tables"]["values"].append("fixture reason: " + status)
    document["digest"] = wire.document_digest(document)
    result = adapter.evaluate_saved_free_space_package(_open(document))
    expected = {"established": "computed", "conditional": "partial", "unknown": "partial",
                "outside": "outside", "invalid": "invalid", "not_available": "not_available"}
    assert {item.observation["raw_status"] for item in result.outputs} == set(statuses)
    for item in result.outputs:
        raw = item.observation["raw_status"]
        assert item.status.value == expected[raw]
        if raw != "established":
            assert "fixture reason: " + raw in item.explanation
        if raw not in statuses[:2]:
            assert item.observation["value"] is None


def test_deterministic_saved_replay_contract_and_json_identity():
    """The actual document, exact publication and declared dependencies bind identity."""
    core, adapter = _modules()
    _, document = _compact_document()
    first = adapter.evaluate_saved_free_space_package(_open(document))
    second = adapter.evaluate_saved_free_space_package(_open(wire.load_json(wire.canonical_json(document))))
    assert serialize_evidence_package_output(first) == serialize_evidence_package_output(second)
    json.dumps(serialize_evidence_package_output(first), allow_nan=False)
    assert first.source_envelopes[0].provenance["source_freshness"] == "historical"
    contract = core.build_free_space_package_contract(document)
    assert {row["name"] for row in contract["dependencies"]} == {"scene", "model", "source", "plane", "query", "recipe", "channels"}
    assert set(contract["target_ids"]) == {item.target["identity"] for item in first.outputs}
    assert evaluate_evidence_package_freshness(cached_contract=contract, current_contract=contract)["freshness"] == "fresh"
    visual = core.build_free_space_package_contract(document, visualization_manifest={"renderer": "test"})
    assert visual["package_identity"] == contract["package_identity"]
    changed = wire.plain(document)
    boolean_cell = next(cell for cell in changed["cells"] if type(cell["value"]) is bool)
    boolean_cell["value"] = not boolean_cell["value"]
    changed["digest"] = wire.document_digest(changed)
    assert core.build_free_space_package_contract(changed)["package_identity"] != contract["package_identity"]
    declared = core.build_free_space_package_contract(document, dependency_fingerprints={"scene": "supplied"})
    assert declared["package_identity"] != contract["package_identity"]


def test_real_compute_and_hit_skip_executor_and_ignore_request_job_id(tmp_path, monkeypatch):
    """Real geometry runs once; disk reuse never reaches the occupancy executor."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    before = scene.to_dict()
    first = adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    values = {tuple(item.observation["cell_locator"][key] for key in ("row", "column")): item.observation["value"]
              for item in first.outputs}
    assert values[(0, 0)] is False and values[(2, 2)] is True
    assert first.source_envelopes[0].provenance["source_freshness"] == "supplied_scene"
    def forbidden(*args, **kwargs):
        """Catch an actual cache miss instead of trusting an exposed hit flag."""
        pytest.fail("cache hit reached occupancy executor")
    monkeypatch.setattr(adapter.requests, "execute_analysis_request", forbidden)
    second = adapter.evaluate_free_space_package(scene, replace(request, request_id="different-job"), cache_directory=tmp_path)
    assert serialize_evidence_package_output(first) == serialize_evidence_package_output(second)
    assert scene.to_dict() == before
    assert len(list(tmp_path.glob("*.json"))) == 1


@pytest.mark.parametrize("change", ["geometry", "query", "grid", "plane", "rules", "scope", "uncertainty", "backend", "version"])
def test_real_input_and_package_version_changes_miss(tmp_path, monkeypatch, change):
    """Bind all factual scene content, including scope facts omitted by legacy identity."""
    core, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    first = adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    if change == "geometry":
        scene = _scene(_object("chair", (0, 0, 0, 2, 1, 3)))
    elif change == "query":
        request = replace(request, geometry_query=adapter.requests.GeometryQuery("finite_height_band", height_band=(0.5, 1.5)))
    elif change == "grid":
        request = replace(request, sampling=replace(request.sampling, spacing=0.5))
    elif change == "plane":
        request = replace(request, plane=_plane(origin=(0, 0, 1)))
    elif change == "rules":
        request = replace(request, source_rules={**dict(request.source_rules), "test_rule": True})
    elif change == "scope":
        scene = replace(scene, source_objects=(replace(scene.source_objects[0], factual_properties={
            "analysis_scope_exclusion": {"reason": "verified_support_binding"}}),))
    elif change == "uncertainty":
        from ..features.scene_contract import UncertaintyRecord
        scene = replace(scene, source_objects=(replace(scene.source_objects[0], uncertainties=(UncertaintyRecord(
            "test", "A factual uncertainty", (), "test", "warning"),)),))
    elif change == "backend":
        versions = adapter.requests._backend_versions()
        def changed_versions():
            """Model a numerical backend update while keeping the supported executor version."""
            return {**versions, "test_backend_revision": "changed"}
        monkeypatch.setattr(adapter.requests, "_backend_versions", changed_versions)
    else:
        monkeypatch.setattr(core, "OUTPUT_FUNCTION_VERSION", core.OUTPUT_FUNCTION_VERSION + "-changed")
    called = []
    original = adapter.requests.execute_analysis_request
    def counted(*args, **kwargs):
        """Observe recomputation without replacing its real field implementation."""
        called.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(adapter.requests, "execute_analysis_request", counted)
    second = adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    assert called == [True]
    assert len(list(tmp_path.glob("*.json"))) == 2
    if change == "scope":
        assert next(item for item in first.outputs if item.observation["cell_locator"]["cell_index"] == 0).observation["value"] is False
        assert next(item for item in second.outputs if item.observation["cell_locator"]["cell_index"] == 0).observation["value"] is True


@pytest.mark.parametrize("damage", ["json", "digest", "foreign", "foreign_document", "rehash_malformed", "contract", "version"])
def test_corrupt_foreign_or_contract_mismatch_is_miss(tmp_path, monkeypatch, damage):
    """A cache filename alone cannot authenticate cached evidence or its receipt."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    path, = tmp_path.glob("*.json")
    receipt = wire.load_json(path.read_text(encoding="utf-8"))
    if damage == "json":
        path.write_text("{", encoding="utf-8")
    else:
        if damage == "digest":
            receipt["document"]["digest"] = "0" * 64
        elif damage == "foreign":
            receipt["cache_key"] = "other-key"
        elif damage == "foreign_document":
            core, _ = _modules()
            receipt["document"] = _compact_document()[1]
            receipt["contract"] = core.build_free_space_package_contract(receipt["document"])
        elif damage == "rehash_malformed":
            receipt["document"]["cells"][0]["source_ids_ref"] = -1
            receipt["document"]["digest"] = wire.document_digest(receipt["document"])
        elif damage == "contract":
            receipt["contract"]["package_identity"] = "0" * 64
        else:
            receipt["schema"] = "old-version"
        path.write_text(wire.canonical_json(receipt), encoding="utf-8")
    called = []
    original = adapter.requests.execute_analysis_request
    def counted(*args, **kwargs):
        """Confirm damaged evidence causes actual recomputation."""
        called.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(adapter.requests, "execute_analysis_request", counted)
    adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    assert called == [True]
    wire.validate_document(wire.load_json(path.read_text(encoding="utf-8"))["document"])


def test_semantically_rewritten_document_with_new_self_digest_is_still_a_miss(tmp_path, monkeypatch):
    """A receipt-level digest prevents altered sample bytes from becoming a cache hit."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    path, = tmp_path.glob("*.json")
    receipt = wire.load_json(path.read_text(encoding="utf-8"))
    document = receipt["document"]
    for cell in document["cells"]:
        if cell["value"] is not None:
            cell["value"] = not cell["value"]
            break
    document["digest"] = wire.document_digest(document)
    receipt["contract"] = package_module.build_free_space_package_contract(document)
    path.write_text(wire.canonical_json(receipt), encoding="utf-8")
    original = adapter.requests.execute_analysis_request
    calls = []
    def counted(*args, **kwargs):
        """Confirm altered cached bytes force a real calculation."""
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(adapter.requests, "execute_analysis_request", counted)
    adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    assert calls == [True]


def test_atomic_cache_failure_preserves_prior_final_and_cleans_partial(tmp_path, monkeypatch):
    """A failed replacement propagates and preserves existing finalized bytes."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    path, = tmp_path.glob("*.json")
    prior = path.read_bytes()
    def refused(*args, **kwargs):
        """Force the final atomic publication boundary to fail."""
        raise OSError("atomic replacement refused")
    monkeypatch.setattr(adapter.os, "replace", refused)
    def force_recompute(*args, **kwargs):
        """Exercise replacement of the same existing final file rather than a new key."""
        return None
    monkeypatch.setattr(adapter, "_read_cache", force_recompute)
    with pytest.raises(OSError, match="atomic replacement refused"):
        adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    assert path.read_bytes() == prior
    assert list(tmp_path.glob("*.partial")) == []


def test_source_envelope_detaches_caller_document_and_rejects_bad_digest():
    """Caller mutations cannot alter a retained source or already produced output."""
    core, _ = _modules()
    _, document = _compact_document()
    source = core.build_free_space_source_envelope(document)
    result = core.build_free_space_evidence_package().evaluate((source,))
    before = serialize_evidence_package_output(result)
    document["tables"]["snapshot"]["provenance"]["caller_mutation"] = True
    assert serialize_evidence_package_output(result) == before
    with pytest.raises(ValueError, match="digest"):
        core.build_free_space_package_contract(document)


def test_package_rejects_source_document_replaced_under_old_identity():
    """An intact envelope cache identity cannot be reused for different retained cell bytes."""
    core, _ = _modules()
    _, document = _compact_document()
    source = core.build_free_space_source_envelope(document)
    boolean_cell = next(cell for cell in document["cells"] if type(cell["value"]) is bool)
    boolean_cell["value"] = not boolean_cell["value"]
    document["digest"] = wire.document_digest(document)
    changed = core.build_free_space_source_envelope(document)
    forged = replace(source, value=changed.value)
    with pytest.raises(ValueError, match="identity"):
        core.build_free_space_evidence_package().evaluate((forged,))
