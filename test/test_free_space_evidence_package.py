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


@pytest.mark.parametrize("change", ["same", "geometry", "backend"])
def test_flat_cache_adoption_binds_independent_current_facts(tmp_path, monkeypatch, change):
    """Locator-aware adoption reuses the same facts and misses foreign geometry or backends."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    first = adapter.run_free_space_package(scene, _request(scene), cache_directory=tmp_path)
    path = tmp_path / (first["cache_key"] + ".json")
    original = path.read_bytes()
    if change == "geometry":
        scene = _scene(_object("chair", (2, 2, 0, 3, 3, 3)))
    elif change == "backend":
        versions = adapter.requests._backend_versions()
        versions["packages"]["numpy"] = "unknown-adoption-backend"
        monkeypatch.setattr(adapter.requests, "_backend_versions", lambda: versions)

    def forbidden(*args, **kwargs):
        """Expose a genuine miss at the numerical executor boundary."""
        raise AssertionError("adoption calculation sentinel")

    monkeypatch.setattr(adapter.requests, "execute_analysis_request", forbidden)
    if change == "same":
        adopted = adapter.run_free_space_package(scene, _request(scene), temporary_cache_root=tmp_path)
        assert adopted["cache_hit"] is True
        assert adopted["cache_reuse"] == "legacy_adopted"
    else:
        with pytest.raises(AssertionError, match="adoption calculation sentinel"):
            adapter.run_free_space_package(scene, _request(scene), temporary_cache_root=tmp_path)
    assert path.read_bytes() == original


@pytest.mark.parametrize("model_sidecar", [False, True])
def test_unused_package_context_preserves_raw_query_and_warm_cache(tmp_path, monkeypatch, model_sidecar):
    """Selection metadata may be unused while raw content keeps its real P1 query."""
    from ..features.package_analysis_context import PackageAnalysisContext
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    options = {"temporary_cache_root": tmp_path} if model_sidecar else {"cache_directory": tmp_path}
    first = adapter.run_free_space_package(scene, request, **options)
    context = PackageAnalysisContext((_plane(origin=(3, 4, 5), identity="unused-P2"),))

    def forbidden(*_args, **_kwargs):
        """A supplied unused context must not regenerate the actual request result."""
        pytest.fail("unused package context repeated numerical analysis")

    monkeypatch.setattr(adapter.requests, "execute_analysis_request", forbidden)
    current = adapter.run_free_space_package(scene, request, analysis_context=context, **options)
    assert current["cache_hit"] is True and current["cache_key"] == first["cache_key"]
    assert current["raw_output"].source_envelopes[0].query.plane == first["raw_output"].source_envelopes[0].query.plane
    assert wire.plain(_document(current["raw_output"])["tables"]["snapshot"]["request"]["plane"]) == request.plane.to_dict()


@pytest.mark.parametrize("allow_multiple_planes", [False, True])
def test_free_space_context_gate_precedes_warm_lookup(tmp_path, monkeypatch, allow_multiple_planes):
    """Unsupported multi-plane context is rejected before a retained receipt can be read."""
    from ..features.package_analysis_context import PackageAnalysisContext
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    adapter.run_free_space_package(scene, request, cache_directory=tmp_path)
    context = PackageAnalysisContext((request.plane, _plane(identity="second-plane")))

    def forbidden(*_args, **_kwargs):
        """Invalid call metadata must not reach a cache seam."""
        pytest.fail("multi-plane context reached cache lookup")

    monkeypatch.setattr(adapter, "_read_cache_entry", forbidden)
    with pytest.raises(ValueError, match="multiple planes"):
        adapter.run_free_space_package(scene, request, cache_directory=tmp_path,
            analysis_context=context, allow_multiple_planes=allow_multiple_planes)


def test_free_space_native_camera_projection_preserves_numeric_source_and_content(tmp_path, monkeypatch):
    """A camera source can enter the full scene without invalidating physical free space."""
    from ..adapters.blender_analysis_capture import CanonicalCaptureInput
    from ..adapters.bonsai_live import load_bonsai_capture
    from .test_blender_analysis_session import _unused_native_camera_record
    from .test_bonsai_live import capture
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    first = adapter.run_free_space_package(scene, request, temporary_cache_root=tmp_path)
    data = capture("furniture").to_dict()
    data["records"] = [_unused_native_camera_record()]
    camera = load_bonsai_capture(CanonicalCaptureInput(**data), plane=request.plane).scene.source_objects[0]
    changed = replace(scene, source_objects=scene.source_objects + (camera,))

    def forbidden(*_args, **_kwargs):
        """The numerical projection must reuse the original physical computation."""
        pytest.fail("native camera repeated free-space calculation")

    monkeypatch.setattr(adapter.requests, "execute_analysis_request", forbidden)
    current = adapter.run_free_space_package(changed, request, temporary_cache_root=tmp_path)
    assert current["cache_hit"] is True
    assert current["cache_key"] == first["cache_key"]
    assert current["source_fingerprint"] == first["source_fingerprint"]


def test_legacy_cache_secret_concurrent_creation_keeps_winner(tmp_path, monkeypatch):
    """Racing legacy writers return the same retained HMAC key without replacing it."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    _, adapter = _modules()
    barrier = Barrier(2)
    token_bytes = adapter.secrets.token_bytes

    def synchronized_secret(size):
        """Make both callers pass the absent-key check before either publishes."""
        secret = token_bytes(size)
        barrier.wait(timeout=5)
        return secret

    monkeypatch.setattr(adapter.secrets, "token_bytes", synchronized_secret)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = tuple(workers.map(adapter._cache_secret, (tmp_path, tmp_path)))
    assert results[0] == results[1] == (tmp_path / ".free_space_cache_key").read_bytes()
    assert not list(tmp_path.glob("*.partial"))


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


def test_free_space_snapshot_captures_required_request_geometry():
    """Required context comes from the validated request without new defaults."""
    _, document = _compact_document()
    request = document["tables"]["snapshot"]["request"]
    snapshot = package_module.build_free_space_parameter_snapshot(request)
    values = snapshot.to_json()["effective_parameters"]
    assert values["analysis_plane"] == {
        key: value for key, value in request["plane"].items()
        if key not in {"name", "revision"}}
    assert values["plane_publication_metadata"] == {
        key: request["plane"][key] for key in ("name", "revision")
        if key in request["plane"]}
    assert values["grid_spacing_m"] == request["sampling"]["spacing"]
    assert values["geometry_query"] == request["geometry_query"]
    assert values["height_band_datum"] == request.get("height_band_datum")
    incomplete = dict(request)
    incomplete.pop("plane")
    with pytest.raises((KeyError, TypeError, ValueError)):
        package_module.build_free_space_parameter_snapshot(incomplete)


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


def test_model_locator_uses_sidecar_and_preserves_source_namespace(tmp_path, monkeypatch):
    """A saved model locator selects its sidecar while keeping calculation identity stable."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    model = tmp_path / "layout.ifc"
    first = adapter.run_free_space_package(scene, request, model_path=model)
    def forbidden(*args, **kwargs):
        """Ensure the second request reuses the sidecar publication."""
        pytest.fail("model-side cache hit reached occupancy executor")
    monkeypatch.setattr(adapter.requests, "execute_analysis_request", forbidden)
    second = adapter.run_free_space_package(scene, replace(request, request_id="relocated-job"), model_path=model)
    assert first["cache_reuse"] == "computed"
    assert second["cache_reuse"] == "exact_hit"
    assert second["cache_location"] == str(model.with_suffix(".order_analyzer"))
    assert first["source_fingerprint"] == second["source_fingerprint"]


def test_model_sidecar_relocation_preserves_free_space_identity(tmp_path, monkeypatch):
    """Moving a model together with its sidecar preserves the validated source namespace."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    old_model = tmp_path / "old.ifc"
    new_model = tmp_path / "renamed.ifc"
    first = adapter.run_free_space_package(scene, request, model_path=old_model)
    old_model.with_suffix(".order_analyzer").rename(new_model.with_suffix(".order_analyzer"))
    monkeypatch.setattr(adapter.requests, "execute_analysis_request",
                        lambda *args, **kwargs: pytest.fail("relocated sidecar reached occupancy executor"))
    second = adapter.run_free_space_package(
        scene, replace(request, request_id="relocated"), model_path=new_model,
    )
    assert second["cache_key"] == first["cache_key"]
    assert second["source_fingerprint"] == first["source_fingerprint"]
    assert second["cache_reuse"] == "exact_hit"


def test_model_locator_adopts_legacy_flat_raw_receipt(tmp_path, monkeypatch):
    """A validated flat receipt is adopted into the namespaced sidecar without recomputation."""
    _, adapter = _modules()
    scene = _scene(_object("chair"))
    request = _request(scene)
    model = tmp_path / "layout.ifc"
    sidecar = model.with_suffix(".order_analyzer")
    first = adapter.run_free_space_package(scene, request, cache_directory=sidecar)
    monkeypatch.setattr(adapter.requests, "execute_analysis_request",
                        lambda *args, **kwargs: pytest.fail("legacy adoption reached occupancy executor"))
    second = adapter.run_free_space_package(
        scene, replace(request, request_id="legacy-adopted"), model_path=model,
    )
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["cache_reuse"] == "legacy_adopted"
    assert list(sidecar.rglob("payload.json"))


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
    calculations = []
    original = adapter.requests.execute_analysis_request

    def counted(*args, **kwargs):
        """Prove both the cold publication and forced rewrite execute real occupancy."""
        calculations.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(adapter.requests, "execute_analysis_request", counted)
    adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    assert calculations == [True]
    path, = tmp_path.glob("*.json")
    prior = path.read_bytes()
    replacements = []

    def refused(*args, **kwargs):
        """Force the final atomic publication boundary to fail."""
        replacements.append(args)
        raise OSError("atomic replacement refused")
    monkeypatch.setattr(adapter.os, "replace", refused)
    def force_recompute(*args, **kwargs):
        """Exercise replacement of the same existing final file rather than a new key."""
        return None
    monkeypatch.setattr(adapter, "_read_cache_entry", force_recompute)
    with pytest.raises(OSError, match="atomic replacement refused"):
        adapter.evaluate_free_space_package(scene, request, cache_directory=tmp_path)
    assert calculations == [True, True]
    assert len(replacements) == 1 and replacements[0][1] == path
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


def test_calculation_identity_resolves_original_table_indices_before_sorting():
    """Remapped compact-table permutations retain both cell meaning and identity."""
    _, document = _compact_document()
    reordered = wire.plain(document)
    values = reordered["tables"]["values"]
    permutation = tuple(reversed(range(len(values))))
    remapped = {old: new for new, old in enumerate(permutation)}
    reordered["tables"]["values"] = [values[index] for index in permutation]
    for cell in reordered["cells"]:
        for name in ("query_ref", "source_ids_ref", "explanation_ref"):
            if type(cell[name]) is int:
                cell[name] = remapped[cell[name]]
        for name in ("support_delta", "provenance_delta"):
            changes = cell.get(name, {}).get("changes", {})
            for key, value in tuple(changes.items()):
                if type(value) is int:
                    changes[key] = remapped[value]
    provenance = reordered["tables"].get("sample_provenance", {})
    for name, value in tuple(provenance.items()):
        if type(value) is int:
            provenance[name] = remapped[value]
    reordered["digest"] = wire.document_digest(reordered)
    wire.validate_document(reordered)
    original_cells = [
        wire.decode_cell(document, row=cell["row"], column=cell["column"])
        for cell in document["cells"]
    ]
    reordered_cells = [
        wire.decode_cell(reordered, row=cell["row"], column=cell["column"])
        for cell in reordered["cells"]
    ]
    # Standard JSON independently distinguishes Boolean, integer and float values.
    assert json.dumps(original_cells, sort_keys=True, separators=(",", ":")) == json.dumps(
        reordered_cells, sort_keys=True, separators=(",", ":"))
    assert package_module.build_free_space_package_contract(document)["package_identity"] == \
        package_module.build_free_space_package_contract(reordered)["package_identity"]


def test_calculation_identity_changes_when_cell_value_associations_change():
    """Sorting a shared table cannot erase which source list belongs to each cell."""
    _, document = _compact_document()
    first = len(document["tables"]["values"])
    document["tables"]["values"].extend([["association-a"], ["association-b"]])
    document["cells"][0]["source_ids_ref"] = first
    document["cells"][1]["source_ids_ref"] = first + 1
    document["digest"] = wire.document_digest(document)
    changed = wire.plain(document)
    values = changed["tables"]["values"]
    values[first], values[first + 1] = values[first + 1], values[first]
    changed["digest"] = wire.document_digest(changed)
    wire.validate_document(document)
    wire.validate_document(changed)
    before = wire.decode_cell(document, row=0, column=0)["source_ids"]
    after = wire.decode_cell(changed, row=0, column=0)["source_ids"]
    assert json.dumps(before) != json.dumps(after)
    assert package_module.build_free_space_package_contract(document)["package_identity"] != \
        package_module.build_free_space_package_contract(changed)["package_identity"]


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("damage", [
    "producer", "algorithm_version", "package_schema", "schema_version",
    "query_dependency", "document",
])
def test_authenticated_lookup_requires_document_and_nonparameter_compatibility(
    tmp_path, legacy, damage,
):
    """Valid HMACs cannot authorize stale versions, foreign queries or contract/document drift."""
    core, adapter = _modules()
    storage = importlib.import_module(core.__package__ + ".evidence_package_storage")
    scene = _scene(_object("chair"))
    request = _request(scene)
    first = adapter.run_free_space_package(scene, request, cache_directory=tmp_path)
    path = tmp_path / (first["cache_key"] + ".json")
    receipt = wire.load_json(path.read_text(encoding="utf-8"))
    if legacy:
        receipt["contract"] = storage.legacy_candidate_contract(receipt["contract"])
    contract = receipt["contract"]
    arguments = {name: contract[name] for name in (
        "package_id", "package_schema", "producer", "target_ids",
        "dependencies", "algorithm_version", "schema_version",
    )}
    if damage == "query_dependency":
        arguments["dependencies"] = [
            {**item, "fingerprint": "foreign-query"} if item["name"] == "query" else item
            for item in contract["dependencies"]
        ]
    elif damage == "document":
        cell = next(cell for cell in receipt["document"]["cells"]
                    if type(cell["value"]) is bool)
        cell["value"] = not cell["value"]
        receipt["document"]["digest"] = wire.document_digest(receipt["document"])
        receipt["document_digest"] = receipt["document"]["digest"]
        wire.validate_document(receipt["document"])
    else:
        arguments[damage] += "-foreign"
    if damage != "document":
        snapshot = (None if legacy else core.ParameterSnapshot.from_json(
            contract["parameter_snapshot"]))
        receipt["contract"] = core.build_evidence_package_contract(
            **arguments, parameter_snapshot=snapshot,
        )
    secret = (tmp_path / ".free_space_cache_key").read_bytes()
    receipt["auth_tag"] = adapter._receipt_tag(receipt, secret)
    adapter._write_cache(path, receipt)
    rejected_bytes = path.read_bytes()
    assert adapter._read_cache(path, first["cache_key"], secret) is None
    assert adapter._read_cache_entry(
        path, first["cache_key"], secret,
        expected_parameter_snapshot=core.build_free_space_parameter_snapshot(request.to_dict()),
        legacy_adopter=adapter._reconstruct_legacy_free_space_contract,
    ) is None
    assert path.read_bytes() == rejected_bytes
    if damage != "document":
        assert storage.compare_receipt_parameters(
            receipt["contract"], first["contract"])["recompute_required"] is True
