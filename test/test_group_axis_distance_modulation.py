"""Actual retained IFC checks for the opt-in distance-axis diagnostic."""

from dataclasses import replace

import pytest

from features import group_axis_potential_field as potential
from features.group_axis_output_ports import bind_port_distance_modulation
from features.field_core import FieldResultStatus
from scripts.design.group_level.run_group_axis_distance_modulation_ifc import load_modulation_inputs


@pytest.fixture(scope="module")
def actual_inputs():
    """Authenticate the pinned axis and distance packages once for this module."""
    return load_modulation_inputs()


def _by_key(outputs):
    """Index package outputs by their stable target/channel address."""
    return {(item.target["identity"], item.channel): item for item in outputs}


def test_actual_full_scope_preserves_axis_and_adds_1369_addressed_cells(actual_inputs):
    """All 1,332 directional values use exact processed pairs and preserve pure-axis outputs."""
    _, envelopes, raw, processed, modulation, _ = actual_inputs
    baseline = potential.run_group_axis_potential_package(envelopes)["raw_output"]
    opted = potential.run_group_axis_potential_package(envelopes, distance_modulation=modulation)["raw_output"]
    base_channels = _by_key(baseline.outputs)
    opted_channels = _by_key(opted.outputs)
    assert all(opted_channels[key] == value for key, value in base_channels.items())
    diagnostic = [item for item in opted.outputs if item.channel == "distance_modulated_axis_support"]
    cells = [item for item in opted.outputs if item.channel == "axis_field_support"]
    assert len(cells) == len(diagnostic) == 37 * 37
    raw_pairs = {item.target["identity"]: item for item in raw.outputs if item.channel == "euclidean_distance"}
    proximity = {item.target["identity"]: item for item in processed.outputs
                 if item.channel == "euclidean_symmetric_reciprocal_relative_proximity"}
    pair_refs = {(ref.target_identity, ref.channel): ref for ref in modulation.dependency.channels}
    assert len(raw_pairs) == len(proximity) == len(pair_refs) == 666
    self_cells = [item for item in diagnostic if item.explanation == "distance_self_not_applicable"]
    assert len(self_cells) == 37
    assert all(item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE for item in self_cells)
    checked = 0
    for axis in cells:
        result = opted_channels[(axis.target["identity"], "distance_modulated_axis_support")]
        observation = axis.observation
        anchor, group = observation["anchor_group_id"], observation["target_group_id"]
        if anchor == group:
            continue
        pair_id, distance = next((key, value) for key, value in raw_pairs.items()
                                 if set(value.observation["group_ids"]) == {anchor, group})
        p = proximity[pair_id]
        reference = pair_refs[(pair_id, p.channel)]
        assert result.status is FieldResultStatus.COMPUTED
        assert result.observation == observation["axis_field_support"] * p.observation
        assert set(result.derived_from) == set(axis.derived_from) | {reference}
        assert p.observation > 0 and distance.observation["units"] == "m"
        checked += 1
    assert checked == 1_332


def test_current_cache_reuses_and_stale_dependency_redacts_values(actual_inputs, tmp_path):
    """A full typed hit is reusable, while stale processed input has no numeric fallback."""
    _, envelopes, _, _, modulation, _ = actual_inputs
    first = potential.run_group_axis_potential_package(envelopes, cache_directory=tmp_path,
                                                        distance_modulation=modulation)
    second = potential.run_group_axis_potential_package(envelopes, cache_directory=tmp_path,
                                                         distance_modulation=modulation)
    assert first["cache_hit"] is False and second["cache_hit"] is True
    assert first["raw_output"] == second["raw_output"]
    stale_dependency = replace(modulation.dependency, package_freshness="stale")
    stale = replace(modulation, dependency=stale_dependency)
    stale_result = potential.run_group_axis_potential_package(envelopes, cache_directory=tmp_path,
                                                               distance_modulation=stale)["raw_output"]
    unavailable = [item for item in stale_result.outputs
                   if item.channel == "distance_modulated_axis_support"
                   and item.explanation != "distance_self_not_applicable"]
    assert len(unavailable) == 1_332
    assert all(item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE for item in unavailable)


def test_compatibility_or_recipe_drift_cannot_use_prior_values(actual_inputs):
    """Changed member registration and a noncurrent fresh recipe fail closed."""
    _, envelopes, _, _, modulation, _ = actual_inputs
    changed_refs = dict(modulation.compatibility["distance_member_refs"])
    group = next(iter(changed_refs))
    changed_refs[group] = ("foreign-member",)
    invalid = replace(modulation, compatibility={**modulation.compatibility, "distance_member_refs": changed_refs})
    with pytest.raises(ValueError, match="member refs"):
        potential.run_group_axis_potential_package(envelopes, distance_modulation=invalid)
    wrong_recipe = replace(modulation, current_processing_identity="foreign-current-recipe")
    with pytest.raises(ValueError, match="does not match"):
        potential.run_group_axis_potential_package(envelopes, distance_modulation=wrong_recipe)


def test_missing_processed_address_does_not_fall_back(actual_inputs):
    """An incomplete exact pair scope is rejected rather than read as raw distance."""
    _, envelopes, _, _, modulation, _ = actual_inputs
    dependency = replace(modulation.dependency, channels=modulation.dependency.channels[:-1])
    invalid = replace(modulation, dependency=dependency)
    with pytest.raises(ValueError, match="one processed reference"):
        potential.run_group_axis_potential_package(envelopes, distance_modulation=invalid)


def potential_processor_for_port(publication):
    """Configure the existing symmetric processor for the complete selected pair scope."""
    from features.group_distance_evidence_package import build_euclidean_symmetric_reciprocal_proximity_processor
    return build_euclidean_symmetric_reciprocal_proximity_processor(
        expected_target_ids=publication.contract.target_ids)


def _forbidden(*args, **kwargs):
    """Fail if a cache or currentness probe invokes a numerical producer."""
    raise AssertionError("numerical callback must not run")


@pytest.fixture(scope="module")
def semantic_distance_inputs(actual_inputs, tmp_path_factory):
    """Save one authenticated selected Euclidean publication and its actual processing."""
    from features.cache_store import CacheStore
    from features.group_distance_evidence_package import (
        build_group_distance_evidence_package, build_group_distance_parameter_snapshot)
    from features.group_distance_output_ports import evaluate_euclidean_port, euclidean_port_contract
    from features.output_port_cache import run_port_processor, save_raw_port
    inputs, envelopes, _, _, modulation, _ = actual_inputs
    parameters = build_group_distance_parameter_snapshot(inputs.bundle)
    contract = euclidean_port_contract(inputs.bundle, parameters=parameters)
    raw = evaluate_euclidean_port(inputs.bundle, parameters=parameters)
    root = tmp_path_factory.mktemp("semantic-distance")
    store = CacheStore(root)
    save_raw_port(store, raw)
    processor = potential_processor_for_port(raw)
    processed = run_port_processor(raw, build_group_distance_evidence_package(output_processor=processor),
        store=store, current_raw_contract=contract, requested_raw_parameters=parameters).publication
    return {"root": root, "store": store, "envelopes": envelopes, "raw": raw,
        "processed": processed, "processor": processor, "contract": contract,
        "parameters": parameters, "compatibility": modulation.compatibility,
        "dependency_graph": modulation.dependency_graph}


def _port_kwargs(saved, *, store=None):
    """Keep independently current distance arguments separate from potential's owner."""
    return {"store": saved["store"] if store is None else store,
        "distance_raw": saved["raw"], "distance_processed": saved["processed"],
        "distance_processor": saved["processor"], "current_distance_contract": saved["contract"],
        "requested_distance_parameters": saved["parameters"],
        "compatibility": saved["compatibility"], "dependency_graph": saved["dependency_graph"]}


def _copied_port_store(saved, tmp_path):
    """Isolate deletion and invalid-receipt cases from the module's authentic baseline."""
    import shutil
    from features.cache_store import CacheStore
    root = tmp_path / "cache"
    shutil.copytree(saved["root"], root)
    return CacheStore(root)


def test_port_modulation_rejects_route_ref_and_freezes_upstream(semantic_distance_inputs):
    """Only the exact processed Euclidean binding can enter the modulation consumer."""
    from dataclasses import FrozenInstanceError
    from features.output_port_cache import ProcessedPortPublication, processed_port_key
    saved = semantic_distance_inputs
    raw, processed = saved["raw"], saved["processed"]
    binding = {"store": saved["store"], "processor": saved["processor"],
        "current_raw_contract": saved["contract"], "requested_raw_parameters": saved["parameters"],
        "compatibility": saved["compatibility"], "dependency_graph": saved["dependency_graph"]}
    wrong_kind = replace(raw, contract=replace(raw.contract, output_port="path_distance"))
    with pytest.raises(ValueError, match="euclidean_distance"):
        bind_port_distance_modulation(wrong_kind, processed, **binding)
    with pytest.raises(TypeError, match="ProcessedPortPublication"):
        bind_port_distance_modulation(raw, raw, **binding)
    foreign_raw = replace(raw, contract=replace(raw.contract, algorithm_version="other/1"))
    foreign_processed = ProcessedPortPublication(foreign_raw.ref, processed.processed_output,
        processed_port_key(foreign_raw, saved["processor"]))
    with pytest.raises(ValueError, match="exact Euclidean raw ref"):
        bind_port_distance_modulation(raw, foreign_processed, **binding)
    for reference in (raw.ref, processed.ref):
        with pytest.raises(FrozenInstanceError):
            reference.identity = "changed"
    members = dict(saved["compatibility"]["distance_member_refs"])
    group = next(iter(members))
    for changed in ({key: refs for key, refs in members.items() if key != group},
                    {**members, group: (*members[group], "foreign-member")}):
        with pytest.raises(ValueError, match="member refs"):
            bind_port_distance_modulation(raw, processed, **{**binding,
                "compatibility": {**saved["compatibility"], "distance_member_refs": changed}})
    valid = bind_port_distance_modulation(raw, processed, **binding)
    assert valid.dependency.package_freshness == "fresh"
    assert "distance_query" not in valid.compatibility


def test_modulation_requires_current_distance_owner_before_loading(semantic_distance_inputs, monkeypatch):
    """Omission cannot silently declare a schema-less upstream or invoke a binding callback."""
    from features import group_axis_output_ports as ports
    saved = semantic_distance_inputs
    kwargs = _port_kwargs(saved)
    del kwargs["requested_distance_parameters"]
    monkeypatch.setattr(ports, "bind_port_distance_modulation", _forbidden)
    with pytest.raises(ValueError, match="requested_distance_parameters"):
        ports.run_group_axis_output_ports(saved["envelopes"], parameters=
            potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True), **kwargs)


def test_semantic_modulation_preserves_all_real_values_and_reuses_pure_switch(
    actual_inputs, semantic_distance_inputs, tmp_path, monkeypatch,
):
    """Preserve all real products, validate graphs before reuse, and retain pure switch hits."""
    from features import group_axis_output_ports as ports
    from features.output_port_cache import selected_raw_bytes
    saved = semantic_distance_inputs
    store = _copied_port_store(saved, tmp_path)
    kwargs = _port_kwargs(saved, store=store)
    on = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True)
    off = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=False)
    graph = dict(saved["dependency_graph"])
    upstream = saved["raw"].raw_view.package_id
    invalid_graphs = (
        ({**graph, upstream: (potential.PACKAGE_ID,)}, "dependency cycle"),
        ({package: edges for package, edges in graph.items() if package != potential.PACKAGE_ID},
         "contain the current package"),
        ({**graph, potential.PACKAGE_ID: ()}, "current package graph edges"),
        ({**graph, upstream: ("foreign-upstream",), "foreign-upstream": ()}, "upstream graph edges"),
    )

    def reject_invalid_graphs():
        """Require identical graph rejection on cold and warm caches before any producer."""
        with monkeypatch.context() as blocked:
            blocked.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
            blocked.setattr(potential, "_distance_modulated_outputs", _forbidden)
            for invalid, message in invalid_graphs:
                with pytest.raises(ValueError, match=message):
                    ports.run_group_axis_output_ports(saved["envelopes"], parameters=on,
                        **{**kwargs, "dependency_graph": invalid})

    reject_invalid_graphs()
    # A miss must retain normalized edges for the later EvidencePackage evaluation.
    first = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on,
        **{**kwargs, "dependency_graph": {package: (edge for edge in edges)
                                        for package, edges in graph.items()}})
    pure = first["axis_potential"].publication
    diagnostic = first["distance_modulated_axis_support"].publication
    old_raw = actual_inputs[2]
    old_pairs = {tuple(sorted(item.observation["group_ids"])): item.observation["value"]
                 for item in old_raw.outputs if item.channel == "euclidean_distance"}
    new_pairs = {tuple(sorted(item.observation["group_ids"])): item.observation["value"]
                 for item in saved["raw"].raw_view.outputs}
    assert new_pairs == old_pairs
    pair_by_id = {item.target["identity"]: tuple(sorted(item.observation["group_ids"]))
                  for item in saved["raw"].raw_view.outputs}
    proximity = {pair_by_id[item.target["identity"]]: item.observation
                 for item in saved["processed"].processed_output.outputs}
    axis = _by_key(pure.raw_view.outputs)
    assert len(diagnostic.raw_view.outputs) == 1_369
    computed, self_count = 0, 0
    for item in diagnostic.raw_view.outputs:
        support = axis[(item.target["identity"], "axis_field_support")].observation
        pair = tuple(sorted((support["anchor_group_id"], support["target_group_id"])))
        if support["self_reference"]:
            assert item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE
            assert item.explanation == "distance_self_not_applicable"
            self_count += 1
        else:
            assert item.status is FieldResultStatus.COMPUTED
            assert item.observation == support["axis_field_support"] * proximity[pair]
            computed += 1
    assert (computed, self_count) == (1_332, 37)
    before = selected_raw_bytes(pure.raw_view)
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    monkeypatch.setattr(potential, "_distance_modulated_outputs", _forbidden)
    reject_invalid_graphs()
    disabled = ports.run_group_axis_output_ports(saved["envelopes"], store=store, parameters=off)
    enabled = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on,
        **{**kwargs, "dependency_graph": {package: (edge for edge in edges)
                                        for package, edges in graph.items()}})
    assert set(disabled) == {"axis_potential"}
    assert disabled["axis_potential"].cache_hit and enabled["axis_potential"].cache_hit
    assert enabled["distance_modulated_axis_support"].cache_hit
    assert disabled["axis_potential"].publication.ref == enabled["axis_potential"].publication.ref == pure.ref
    assert selected_raw_bytes(disabled["axis_potential"].publication.raw_view) == before
    assert selected_raw_bytes(enabled["axis_potential"].publication.raw_view) == before
    assert enabled["distance_modulated_axis_support"].publication.ref == diagnostic.ref


def _drifted_distance_owner(saved, drift):
    """Resolve a self-consistent current declaration independently from saved metadata."""
    from features.evidence_package_parameters import ParameterImpact, ParameterSpec
    from features.group_distance_evidence_package import GROUP_DISTANCE_PARAMETER_SCHEMA
    from features.field_core import _json_value
    schema = GROUP_DISTANCE_PARAMETER_SCHEMA
    specs = list(schema.specs)
    index = next(index for index, spec in enumerate(specs) if spec.name == "clearance_mode")
    values = _json_value(saved["parameters"].effective_parameters)
    if drift == "schema":
        schema = replace(schema, schema_version="group-distance-parameters/independent-current")
    elif drift == "fields":
        specs.append(ParameterSpec("current_extra", bool, False))
    elif drift == "type":
        specs[index] = replace(specs[index], value_type=int, choices=None)
        values["clearance_mode"] = 1
    elif drift == "unit":
        specs[index] = replace(specs[index], unit="rad")
    elif drift == "nullable":
        specs[index] = replace(specs[index], nullable=True)
    elif drift == "impact":
        specs[index] = replace(specs[index], impact=ParameterImpact.METADATA_ONLY)
    return replace(schema, specs=tuple(specs)).resolve(values)


@pytest.mark.parametrize("drift", [
    "schema", "fields", "type", "unit", "nullable", "impact", "typed_to_none",
    "none_to_typed", "input", "processor",
])
def test_modulation_forwards_current_owner_and_recipe(
    semantic_distance_inputs, drift, monkeypatch,
):
    """Independent owner, input and recipe drift fail before modulation produces values."""
    from features import group_axis_output_ports as ports
    saved = semantic_distance_inputs
    kwargs = _port_kwargs(saved)
    if drift in {"schema", "fields", "type", "unit", "nullable", "impact"}:
        kwargs["requested_distance_parameters"] = _drifted_distance_owner(saved, drift)
    elif drift == "typed_to_none":
        kwargs["requested_distance_parameters"] = None
    elif drift == "none_to_typed":
        kwargs["distance_raw"] = replace(saved["raw"], parameter_snapshot=None)
    elif drift == "input":
        kwargs["current_distance_contract"] = replace(saved["contract"], input_fingerprints={
            **saved["contract"].input_fingerprints, "geometry": "independent-current-input"})
    else:
        kwargs["distance_processor"] = replace(saved["processor"], version="independent-current-version")
    before = {(item.address, item.status) for item in saved["store"].list()}
    monkeypatch.setattr(potential, "_distance_modulated_outputs", _forbidden)
    with pytest.raises(ValueError, match="(owner schema|requested_parameters|current raw contract|current processor)"):
        ports.run_group_axis_output_ports(saved["envelopes"], parameters=
            potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True), **kwargs)
    assert {(item.address, item.status) for item in saved["store"].list()} == before
    assert not saved["store"].list(package_id=potential.PACKAGE_ID,
                                   output_port="distance_modulated_axis_support")


@pytest.mark.parametrize("layer", ["raw", "processed"])
def test_semantic_modulation_missing_upstream_redacts_nonself(
    semantic_distance_inputs, tmp_path, monkeypatch, layer,
):
    """Deleted exact dependencies redact every nonself cell and leave pure-axis usable."""
    from features import group_axis_output_ports as ports
    saved = semantic_distance_inputs
    store = _copied_port_store(saved, tmp_path)
    kwargs = _port_kwargs(saved, store=store)
    on = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True)
    first = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **kwargs)
    reference = saved["raw"].ref if layer == "raw" else saved["processed"].ref
    assert store.delete_exact(reference.address)
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    again = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **kwargs)
    assert again["axis_potential"].cache_hit
    assert again["axis_potential"].publication.ref == first["axis_potential"].publication.ref
    missing = again["distance_modulated_axis_support"]
    assert missing.status == "unavailable" and not missing.cache_hit
    nonself = [item for item in missing.publication.raw_view.outputs
               if item.explanation != "distance_self_not_applicable"]
    assert len(nonself) == 1_332
    assert all(item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE for item in nonself)
    assert not any(item.status == "complete" for item in store.list(
        package_id=potential.PACKAGE_ID, output_port="distance_modulated_axis_support"))


@pytest.mark.parametrize("layer", ["raw", "processed"])
def test_modulation_rejects_unknown_semantic_schema_before_numeric_use(
    semantic_distance_inputs, tmp_path, monkeypatch, layer,
):
    """Self-consistent outer byte digests cannot bypass the supported schema gate."""
    import json
    from features import group_axis_output_ports as ports
    from test.test_output_port_cache import _rewrite
    saved = semantic_distance_inputs
    store = _copied_port_store(saved, tmp_path)
    entry = next(item for item in store.list() if item.address.layer == layer)
    document = json.loads(entry.payload_paths[0].read_bytes())
    document["schema"] = "semantic-output-receipt/v99"
    _rewrite(entry, document)
    before = entry.payload_paths[0].read_bytes()
    monkeypatch.setattr(potential, "_distance_modulated_outputs", _forbidden)
    with pytest.raises(ValueError, match="schema"):
        ports.run_group_axis_output_ports(saved["envelopes"], parameters=
            potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True),
            **_port_kwargs(saved, store=store))
    assert entry.payload_paths[0].read_bytes() == before
    assert not store.list(package_id=potential.PACKAGE_ID,
                           output_port="distance_modulated_axis_support")


@pytest.mark.parametrize("damaged_port", ["axis_potential", "distance_modulated_axis_support"])
def test_corrupt_axis_port_retains_bytes_and_recomputes_only_its_producer(
    semantic_distance_inputs, tmp_path, monkeypatch, damaged_port,
):
    """Each owning runner retains corruption before rebuilding exactly one selected port."""
    from features import group_axis_output_ports as ports
    from features import group_distance_output_ports as distance_ports
    from features.output_port_cache import validate_port_payload
    saved = semantic_distance_inputs
    store = _copied_port_store(saved, tmp_path)
    kwargs = _port_kwargs(saved, store=store)
    on = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True)
    first = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **kwargs)
    reference = first[damaged_port].publication.ref
    entry = store.get(reference.address, validator=validate_port_payload)
    corrupted = entry.payload_paths[0].read_bytes() + b" "
    entry.payload_paths[0].write_bytes(corrupted)
    original_axis = potential.aggregate_group_axis_potential_outputs
    original_modulation = potential._distance_modulated_outputs
    calls = {"axis_potential": 0, "distance_modulated_axis_support": 0}

    def count_axis(*args, **arguments):
        """Count actual pure-axis evaluations after corrupting only its stored publication."""
        calls["axis_potential"] += 1
        return original_axis(*args, **arguments)

    def count_modulation(*args, **arguments):
        """Count actual modulation evaluations without hiding any pure-axis recalculation."""
        calls["distance_modulated_axis_support"] += 1
        return original_modulation(*args, **arguments)

    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs",
                        count_axis if damaged_port == "axis_potential" else _forbidden)
    monkeypatch.setattr(potential, "_distance_modulated_outputs",
                        count_modulation if damaged_port == "distance_modulated_axis_support" else _forbidden)
    monkeypatch.setattr(distance_ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(distance_ports, "evaluate_path_port", _forbidden)
    kwargs["distance_processor"] = replace(saved["processor"], function=_forbidden)
    rebuilt = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **kwargs)
    assert calls == {name: int(name == damaged_port) for name in calls}
    assert not rebuilt[damaged_port].cache_hit
    intact_port = next(name for name in calls if name != damaged_port)
    assert rebuilt[intact_port].cache_hit
    assert {name: run.publication.ref for name, run in rebuilt.items()} == {
        name: run.publication.ref for name, run in first.items()}
    assert [path.read_bytes() for path in (tmp_path / "cache" / "quarantine").rglob("payload.json")] == [corrupted]
    again = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **kwargs)
    assert all(run.cache_hit for run in again.values())
    assert calls == {name: int(name == damaged_port) for name in calls}


from .test_free_space_distance import actual_publication, actual_bundle, stored_distance_free_space


def _lifecycle_bytes(store):
    """Snapshot immutable addressed bytes while leaving advisory lifecycle state separate."""
    return {entry.address: (entry.receipt_path.read_bytes(), entry.payload_paths[0].read_bytes())
            for entry in store.list()}


@pytest.fixture(scope="module")
def lifecycle_graph(actual_inputs, semantic_distance_inputs, stored_distance_free_space, tmp_path_factory):
    """Build one real nonempty dependency graph and preserve its independent source stores."""
    import json
    from features.cache_paths import CacheAddress
    from features import group_distance as kernel, group_distance_evidence_package as distance
    from features import group_distance_output_ports as distance_ports, group_axis_output_ports as axis_ports
    from features.evidence_package_storage import serialize_raw_output_bytes
    from features.output_port_cache import run_port_processor, save_raw_port, validate_port_payload

    saved = semantic_distance_inputs
    store = _copied_port_store(saved, tmp_path_factory.mktemp("lifecycle-seed"))
    native_store, native_ref, native_validator = stored_distance_free_space
    native = native_store.get(native_ref.address, validator=native_validator)
    assert native is not None
    native_payload = native.payload_paths[0].read_bytes()
    assert len(json.loads(native_payload)["cells"]) == 24_442
    store.put(native_ref.address, contract=native.receipt["contract"], payload=native_payload,
              payload_format="json", validator=native_validator)

    bundle = actual_inputs[0].bundle
    usable = next(item for item in actual_inputs[2].outputs if item.channel == "path_distance"
                  and item.observation["value"] is not None)
    group_ids = set(usable.observation["group_ids"])
    path_bundle = replace(bundle, groups=tuple(group for group in bundle.groups if group.group_id in group_ids),
                          dependency_fingerprints={})
    path_bundle = replace(path_bundle, dependency_fingerprints=kernel.group_distance_input_fingerprints(path_bundle))
    path_parameters = distance.build_group_distance_parameter_snapshot(path_bundle)
    path = distance_ports.evaluate_path_port(path_bundle, parameters=path_parameters, store=store,
        free_space_ref=native_ref, free_space_validator=native_validator)
    assert path.raw_view.outputs and any(item.observation["value"] is not None for item in path.raw_view.outputs)
    save_raw_port(store, path)

    on = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True)
    axis = axis_ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **_port_kwargs(saved, store=store))
    pure, modulation = axis["axis_potential"].publication, axis["distance_modulated_axis_support"].publication
    assert sum(item.status is FieldResultStatus.COMPUTED for item in modulation.raw_view.outputs) == 1_332

    sibling_bundle = replace(bundle, groups=tuple(sorted(bundle.groups, key=lambda item: item.group_id)[:3]),
                             dependency_fingerprints={})
    sibling_bundle = replace(sibling_bundle, dependency_fingerprints=kernel.group_distance_input_fingerprints(sibling_bundle))
    sibling_parameters = distance.build_group_distance_parameter_snapshot(sibling_bundle)
    sibling = distance_ports.evaluate_euclidean_port(sibling_bundle, parameters=sibling_parameters)
    save_raw_port(store, sibling)
    sibling_processor = potential_processor_for_port(sibling)
    sibling_processed = run_port_processor(sibling, distance.build_group_distance_evidence_package(
        output_processor=sibling_processor), store=store, current_raw_contract=sibling.contract,
        requested_raw_parameters=sibling_parameters).publication
    assert len(sibling.raw_view.outputs) == 3 and sibling.ref != saved["raw"].ref

    # Preserve the existing combined codec in the same owner family as semantic raw entries.
    legacy_contract = potential.build_group_axis_potential_package_contract(saved["envelopes"])
    legacy_address = CacheAddress(potential._potential_dependency_fingerprint(legacy_contract, "source"),
        potential.PACKAGE_ID, "combined", "raw", legacy_contract["package_identity"])
    legacy_validator = potential._potential_raw_validator(potential.build_group_axis_potential_package(), legacy_contract)
    store.put(legacy_address, contract=legacy_contract, payload=serialize_raw_output_bytes(
        cache_key=legacy_address.identity, contract=legacy_contract, raw_output=pure.raw_view),
        payload_format="evidence-package-cache/v1", validator=legacy_validator)
    potential._potential_bind_source(store, legacy_contract, model_path=None, cache_root=store.root)

    processed_by_address = {item.ref.address: item for item in (saved["processed"], sibling_processed)}
    raw_by_ref = {item.ref: item for item in (saved["raw"], sibling)}

    def validate_processed(payload, context):
        """Bind copied processed bytes to an independently known actual raw publication."""
        expected = processed_by_address.get(context.address)
        if expected is None:
            raise ValueError("unknown lifecycle processed address")
        validate_port_payload(payload, context, raw_publication=raw_by_ref[expected.raw_ref])

    def validate_axis(payload, context):
        """Dispatch only the explicit supported semantic and unchanged combined codecs."""
        schema = json.loads(payload).get("schema")
        if schema == "semantic-output-receipt/v1":
            validate_port_payload(payload, context)
        elif schema == "evidence-package-cache/v1":
            legacy_validator(payload, context)
        else:
            raise ValueError("unsupported lifecycle axis schema")

    validators = {"blender-analysis:raw": native_validator, "group-walk-distance:raw": validate_port_payload,
        "group-walk-distance:processed": validate_processed, "group-axis-potential:raw": validate_axis}
    refs = {"free_space": native_ref, "path": path.ref, "euclidean_raw": saved["raw"].ref,
        "euclidean_processed": saved["processed"].ref, "pure_axis": pure.ref, "modulation": modulation.ref,
        "sibling_raw": sibling.ref, "sibling_processed": sibling_processed.ref}
    entries = {entry.address: entry for entry in store.list()}
    assert len(entries) == 9 and all(entry.status == "complete" for entry in entries.values())
    for entry in entries.values():
        assert store.get(entry.address, validator=validators[f"{entry.address.package_id}:{entry.address.layer}"]) is not None
    edges = {address: {CacheAddress(**dict(item)) for item in entry.receipt["upstream_refs"]}
             for address, entry in entries.items()}
    assert edges[path.ref.address] == {native_ref.address}
    assert edges[saved["raw"].ref.address] == set()
    assert edges[saved["processed"].ref.address] == {saved["raw"].ref.address}
    assert edges[pure.ref.address] == set()
    assert edges[modulation.ref.address] == {pure.ref.address, saved["processed"].ref.address}
    return {**saved, "root": store.root, "store": store, "refs": refs, "validators": validators,
        "axis_parameters": on, "axis": axis, "path": path, "path_parameters": path_parameters,
        "bundle": bundle, "sibling_bundle": sibling_bundle, "sibling": sibling,
        "sibling_parameters": sibling_parameters, "sibling_processor": sibling_processor,
        "sibling_processed": sibling_processed, "legacy_address": legacy_address,
        "native_store": native_store, "native_before": _lifecycle_bytes(native_store),
        "before": _lifecycle_bytes(store)}


@pytest.mark.parametrize("deleted", ["path", "free_space", "euclidean_raw", "euclidean_processed"])
def test_real_dependency_deletion_preserves_only_independent_ports(lifecycle_graph, tmp_path, monkeypatch, deleted):
    """Real exact deletion invalidates true descendants and preserves independent numeric versions."""
    from features import field_core, group_axis_output_ports as axis_ports, group_distance_output_ports as distance_ports
    from features.output_port_cache import load_processed_port, load_raw_port

    graph = lifecycle_graph
    store = _copied_port_store(graph, tmp_path)
    refs = graph["refs"]
    assert all(entry.status == "complete" for entry in store.list())
    euclidean_versions = store.list(package_id="group-walk-distance", output_port="euclidean_distance")
    assert {entry.address for entry in euclidean_versions} == {
        refs[name].address for name in ("euclidean_raw", "euclidean_processed", "sibling_raw", "sibling_processed")}
    monkeypatch.setattr(distance_ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(distance_ports, "evaluate_path_port", _forbidden)
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    if deleted in {"path", "free_space"}:
        monkeypatch.setattr(potential, "_distance_modulated_outputs", _forbidden)
    monkeypatch.setattr(field_core.EvidencePackage, "process_output", _forbidden)
    assert store.delete_exact(refs[deleted].address) is True

    descendants = ({"path"} if deleted == "free_space" else
                   {"euclidean_processed", "modulation"} if deleted == "euclidean_raw" else
                   {"modulation"} if deleted == "euclidean_processed" else set())
    after = {entry.address: entry for entry in store.list()}
    assert set(after) == set(graph["before"]) - {refs[deleted].address}
    assert {address for address, entry in after.items() if entry.status == "orphaned"} == {
        refs[name].address for name in descendants}
    path = load_raw_port(store, graph["path"].contract, requested_parameters=graph["path_parameters"])
    assert (path is None) == (deleted in {"path", "free_space"})
    if path is not None:
        assert path.ref == refs["path"]
    if deleted != "euclidean_raw":
        assert load_raw_port(store, graph["contract"], requested_parameters=graph["parameters"]).ref == refs["euclidean_raw"]
        processed = load_processed_port(store, refs["euclidean_processed"], current_raw_contract=graph["contract"],
            requested_raw_parameters=graph["parameters"], processor=graph["processor"])
        assert (processed is None) == (deleted == "euclidean_processed")
    else:
        assert load_raw_port(store, graph["contract"], requested_parameters=graph["parameters"]) is None
        with pytest.raises(ValueError, match="current raw contract"):
            load_processed_port(store, refs["euclidean_processed"], current_raw_contract=graph["contract"],
                requested_raw_parameters=graph["parameters"], processor=graph["processor"])
    sibling = load_processed_port(store, refs["sibling_processed"], current_raw_contract=graph["sibling"].contract,
        requested_raw_parameters=graph["sibling_parameters"], processor=graph["sibling_processor"])
    assert sibling.ref == refs["sibling_processed"]

    result = axis_ports.run_group_axis_output_ports(graph["envelopes"], parameters=graph["axis_parameters"],
        **_port_kwargs(graph, store=store))
    assert result["axis_potential"].cache_hit
    assert result["axis_potential"].publication.ref == refs["pure_axis"]
    modulation = result["distance_modulated_axis_support"]
    nonself = [item for item in modulation.publication.raw_view.outputs if item.explanation != "distance_self_not_applicable"]
    assert len(nonself) == 1_332
    if deleted in {"euclidean_raw", "euclidean_processed"}:
        assert modulation.status == "unavailable" and modulation.cache_hit is False
        assert all(item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE for item in nonself)
        assert load_raw_port(store, graph["axis"]["distance_modulated_axis_support"].publication.contract,
                             requested_parameters=graph["axis_parameters"]) is None
    else:
        assert modulation.cache_hit and modulation.publication.ref == refs["modulation"]
        assert all(item.observation is not None and item.status is FieldResultStatus.COMPUTED for item in nonself)
    assert _lifecycle_bytes(store) == {address: content for address, content in graph["before"].items()
                                     if address != refs[deleted].address}
    assert _lifecycle_bytes(graph["store"]) == graph["before"]
    assert _lifecycle_bytes(graph["native_store"]) == graph["native_before"]


def test_mixed_port_cache_migrates_original_owner_codecs_without_producers(lifecycle_graph, tmp_path, monkeypatch):
    """One existing B migration retains native, legacy and semantic refs with zero producers."""
    from features.cache_store import CacheStore
    from features import field_core, group_axis_output_ports as axis_ports, group_distance_output_ports as distance_ports
    from features.output_port_cache import load_raw_port

    original_process_output = field_core.EvidencePackage.process_output
    graph = lifecycle_graph
    monkeypatch.setattr(distance_ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(distance_ports, "evaluate_path_port", _forbidden)
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    monkeypatch.setattr(potential, "_distance_modulated_outputs", _forbidden)
    monkeypatch.setattr(field_core.EvidencePackage, "process_output", _forbidden)
    report = graph["store"].migrate_to(tmp_path / "moved", validators=graph["validators"])
    assert report.failed == () and set(report.copied) == set(graph["before"])
    assert report.old_directory_retained and report.index_rebuilt
    store = CacheStore(tmp_path / "moved")
    assert all(entry.status == "complete" for entry in store.list())
    for entry in store.list():
        validated = store.get(entry.address, validator=graph["validators"][f"{entry.address.package_id}:{entry.address.layer}"])
        assert validated is not None and validated.reuse_origin == "migrated"
    assert load_raw_port(store, graph["path"].contract, requested_parameters=graph["path_parameters"]).ref == graph["refs"]["path"]
    for bundle, parameters, processor, reference in (
        (graph["bundle"], graph["parameters"], graph["processor"], graph["refs"]["euclidean_processed"]),
        (graph["sibling_bundle"], graph["sibling_parameters"], graph["sibling_processor"], graph["refs"]["sibling_processed"]),
    ):
        moved = distance_ports.run_euclidean_processed_port(bundle, store=store, parameters=parameters, processor=processor)
        assert moved.cache_hit and moved.cache_reuse == "migrated_reuse" and moved.publication.ref == reference
    result = axis_ports.run_group_axis_output_ports(graph["envelopes"], parameters=graph["axis_parameters"],
        **_port_kwargs(graph, store=store))
    assert all(item.cache_hit and item.cache_reuse == "migrated_reuse" for item in result.values())
    assert {name: item.publication.ref for name, item in result.items()} == {
        name: item.publication.ref for name, item in graph["axis"].items()}
    source_id = graph["legacy_address"].source_fingerprint
    assert store.get_source_binding(source_id) == graph["store"].get_source_binding(source_id)
    legacy_facade_calls = []

    def process_unconfigured(package, raw, *, package_freshness):
        """Allow only the legacy empty status facade while numerical processing stays forbidden."""
        assert package.output_processor is None
        legacy_facade_calls.append(package_freshness)
        return original_process_output(package, raw, package_freshness=package_freshness)

    with monkeypatch.context() as legacy_patch:
        legacy_patch.setattr(field_core.EvidencePackage, "process_output", process_unconfigured)
        legacy = potential.run_group_axis_potential_package(graph["envelopes"], temporary_cache_root=store.root)
    assert legacy_facade_calls == ["fresh"]
    assert legacy["cache_hit"] and legacy["cache_reuse"] == "migrated_reuse"
    assert legacy["processed_output"].error_code == "OUTPUT_FUNCTION_NOT_CONFIGURED"
    assert legacy["processed_output"].outputs == ()
    assert _lifecycle_bytes(store) == _lifecycle_bytes(graph["store"]) == graph["before"]
    assert _lifecycle_bytes(graph["native_store"]) == graph["native_before"]
