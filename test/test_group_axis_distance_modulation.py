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
    """All 1,332 nonself products survive exact binding and switch changes reuse pure bytes."""
    from features import group_axis_output_ports as ports
    from features.output_port_cache import selected_raw_bytes
    saved = semantic_distance_inputs
    store = _copied_port_store(saved, tmp_path)
    kwargs = _port_kwargs(saved, store=store)
    on = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True)
    off = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=False)
    first = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **kwargs)
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
    disabled = ports.run_group_axis_output_ports(saved["envelopes"], store=store, parameters=off)
    enabled = ports.run_group_axis_output_ports(saved["envelopes"], parameters=on, **kwargs)
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
