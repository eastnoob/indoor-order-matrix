"""Semantic publications preserve selected bytes and independent current authority."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import json

import pytest

from features.cache_paths import CacheAddress
from features.cache_store import CacheStore, CacheValidationContext
from features.evidence_package_parameters import (
    ParameterImpact, ParameterSchema, ParameterSpec,
)
from features.evidence_package_storage import write_receipt
from features.field_core import (
    EvidenceOutputProcessor, _canonical_json, _json_value, fingerprint_evidence_dependency,
    serialize_evidence_package_output, serialize_evidence_processed_output,
)
from features.output_port_cache import (
    OutputPortContract, OutputPortRef, PortRun, bind_raw_port, load_raw_port,
    load_processed_port, processed_port_key, run_port_processor, save_raw_port,
    selected_processed_bytes, selected_raw_bytes, serialize_raw_port_publication,
    validate_port_payload,
)
from .test_evidence_package_processing import _package, _process, _raw


def _contract(raw, output_port="reading"):
    """Declare the complete selected scope of the existing contract fixture."""
    return OutputPortContract(
        package_id=raw.package_id, output_port=output_port,
        source_fingerprint="c" * 64,
        input_fingerprints={"source": "c" * 64},
        parameter_projection={"schema": "contract/port-parameters/1", "selected_names": [],
                              "values": {}, "value_contracts": {}},
        upstream_refs=(), algorithm_version="contract-port/1", schema_version="contract-port/v1",
        addresses=tuple((item.target["identity"], item.channel) for item in raw.outputs),
    )


def test_semantic_address_is_distinct_from_calculation_layer():
    """The semantic kind and calculation layer remain independent immutable fields."""
    raw = _raw()
    publication = bind_raw_port(_contract(raw), raw)
    assert publication.ref.output_port == "reading"
    assert publication.ref.layer == "raw"
    with pytest.raises(FrozenInstanceError):
        publication.ref.output_port = "other"
    assert bind_raw_port(_contract(raw, "other"), raw).ref.identity != publication.ref.identity


def test_wrong_selected_channel_scope_is_rejected():
    """The selected publication must cover exactly its declared target/channel pairs."""
    raw = _raw()
    with pytest.raises(ValueError, match="channel"):
        bind_raw_port(replace(_contract(raw), addresses=tuple(
            (item.target["identity"], "foreign") for item in raw.outputs)), raw)


def _owner():
    """Declare a tiny independently resolved owner for historical/current comparisons."""
    return ParameterSchema("contract-package", "typed-owner/1", (
        ParameterSpec("review_m", float, 1.0, unit="m"),
    ))


def _context(publication):
    """Build the same opaque wrapper facts B supplies to the package validator."""
    return CacheValidationContext(publication.ref.address, None, None, {
        "port_contract": _json_value(publication.contract),
        "parameter_snapshot": (None if publication.parameter_snapshot is None
                               else publication.parameter_snapshot.to_json()),
    })


def _rewrite(entry, document):
    """Refresh storage integrity so package semantic rejection is tested independently."""
    payload = _canonical_json(document).encode("utf-8")
    entry.payload_paths[0].write_bytes(payload)
    receipt = json.loads(entry.receipt_path.read_bytes())
    receipt["payload"]["size"] = len(payload)
    receipt["payload"]["sha256"] = hashlib.sha256(payload).hexdigest()
    receipt["receipt_fingerprint"] = fingerprint_evidence_dependency({
        key: value for key, value in receipt.items() if key != "receipt_fingerprint"})
    write_receipt(entry.receipt_path, receipt)


def _projection(snapshot, names):
    """Declare selected names while projecting only recompute-required owner values."""
    selected = [name for name in names if snapshot.parameter_impacts[name]
                == ParameterImpact.RECOMPUTE_REQUIRED.value]
    return {"schema": "contract/selected-parameters/1", "selected_names": sorted(names),
            "values": {name: snapshot.effective_parameters[name] for name in selected},
            "value_contracts": {name: snapshot.parameter_value_contracts[name] for name in selected}}


def test_raw_round_trip_and_three_distinct_digest_bindings(tmp_path):
    """Inner integrity, selected bytes and the stored envelope bind different content."""
    raw = _raw()
    publication = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    entry = save_raw_port(store, publication)
    restored = load_raw_port(store, publication.contract, requested_parameters=None)
    assert restored == publication
    assert entry.address == CacheAddress("c" * 64, raw.package_id, "reading", "raw",
                                         publication.contract.identity)
    inner = serialize_evidence_package_output(raw)
    inner_digest = inner.pop("payload_fingerprint")
    assert inner_digest == hashlib.sha256(_canonical_json(inner).encode()).hexdigest()
    selected_digest = hashlib.sha256(selected_raw_bytes(raw)).hexdigest()
    envelope_digest = hashlib.sha256(entry.payload_paths[0].read_bytes()).hexdigest()
    assert selected_digest == publication.ref.payload_fingerprint
    assert envelope_digest == entry.receipt["payload"]["sha256"]
    assert len({inner_digest, selected_digest, envelope_digest}) == 3
    assert entry.payload_paths[0].read_bytes() == serialize_raw_port_publication(publication)


def test_corrupt_payload_is_a_miss_and_keeps_rejected_bytes(tmp_path):
    """A failed byte-integrity check never returns the former typed publication."""
    raw = _raw()
    publication = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    entry = save_raw_port(store, publication)
    corrupted = entry.payload_paths[0].read_bytes() + b" "
    entry.payload_paths[0].write_bytes(corrupted)
    assert load_raw_port(store, publication.contract, requested_parameters=None) is None
    assert entry.payload_paths[0].read_bytes() == corrupted


def test_missing_entry_does_not_create_storage(tmp_path):
    """A current contract with no publication remains an inert miss."""
    root = tmp_path / "missing"
    assert load_raw_port(CacheStore(root), _contract(_raw()), requested_parameters=None) is None
    assert not root.exists()


def test_exact_addresses_do_not_require_a_cartesian_product(tmp_path):
    """Two selected pairs need not imply every target has every channel."""
    raw = _raw()
    first = raw.outputs[0]
    other = replace(first, target={**first.target, "id": "other-target", "identity": "other-target"},
                    channel="other-channel")
    raw = replace(raw, outputs=(first, other))
    publication = bind_raw_port(_contract(raw), raw)
    assert publication.contract.target_ids == tuple(sorted((first.target["identity"], "other-target")))
    assert publication.contract.channels == tuple(sorted((first.channel, "other-channel")))
    assert len(publication.contract.addresses) == 2
    store = CacheStore(tmp_path)
    save_raw_port(store, publication)
    assert load_raw_port(store, publication.contract, requested_parameters=None) == publication


def test_nested_contract_and_run_status_are_detached_and_frozen():
    """Caller mutation cannot rewrite declared inputs or a returned status audit."""
    raw = _raw()
    snapshot = ParameterSchema(raw.package_id, "nested/1", (
        ParameterSpec("settings", dict, {"items": [1, 2]}),)).resolve()
    projection = _projection(snapshot, ["settings"])
    contract = replace(_contract(raw), parameter_projection=projection)
    projection["values"]["settings"] = {"items": [3]}
    publication = bind_raw_port(contract, raw, parameter_snapshot=snapshot)
    assert contract.parameter_projection["values"]["settings"]["items"] == (1, 2)
    with pytest.raises(TypeError):
        contract.parameter_projection["values"]["settings"]["items"][0] = 9
    status = {"freshness": "fresh", "recompute_required": False, "exact_match": True,
              "reasons": [{"detail": ["original"]}], "affected_targets": ["one"],
              "parameter_status": None, "processed_parameter_status": None}
    run = PortRun(publication, True, "fresh", status, "exact_hit", None)
    status["reasons"][0]["detail"].append("changed")
    assert run.cache_status["reasons"][0]["detail"] == ("original",)
    assert set(run.cache_status) == set(status)
    with pytest.raises(TypeError):
        run.cache_status["reasons"][0]["detail"] = ()


@pytest.mark.parametrize("field,value", [
    ("package_id", ""), ("output_port", " "), ("source_fingerprint", "../scene"),
    ("algorithm_version", ""), ("schema_version", " "),
    ("input_fingerprints", {"source": ""}),
    ("addresses", ()), ("addresses", (("", "channel"),)),
])
def test_contract_rejects_invalid_declarations(field, value):
    """Malformed identity and scope fields fail before any storage side effect."""
    with pytest.raises((TypeError, ValueError)):
        replace(_contract(_raw()), **{field: value})


def test_duplicate_addresses_and_upstream_versions_are_rejected():
    """A different payload digest cannot disguise the same upstream address twice."""
    raw = _raw()
    contract = _contract(raw)
    with pytest.raises(ValueError, match="duplicate"):
        replace(contract, addresses=contract.addresses * 2)
    reference = bind_raw_port(contract, raw).ref
    with pytest.raises(ValueError, match="duplicate upstream"):
        replace(contract, upstream_refs=(reference, replace(reference, payload_fingerprint="a" * 64)))


@pytest.mark.parametrize("changes", [
    {"layer": "intermediate"}, {"payload_fingerprint": "broken"},
    {"layer": "processed"}, {"processing_identity": "unexpected"},
])
def test_reference_rejects_ambiguous_layer_bindings(changes):
    """Processed refs require a recipe identity and raw refs cannot carry one."""
    reference = bind_raw_port(_contract(_raw()), _raw()).ref
    with pytest.raises(ValueError):
        replace(reference, **changes)
    processed = replace(reference, layer="processed", processing_identity="recipe/1")
    assert processed.address.layer == "processed"
    assert processed.processing_identity == "recipe/1"


def test_foreign_package_view_or_snapshot_is_rejected():
    """Neither selected values nor parameter audit may belong to another package."""
    raw = _raw()
    with pytest.raises(ValueError, match="foreign package"):
        bind_raw_port(replace(_contract(raw), package_id="foreign"), raw)
    foreign = replace(_owner(), package_id="foreign").resolve()
    with pytest.raises(ValueError, match="foreign package"):
        bind_raw_port(_contract(raw), raw, parameter_snapshot=foreign)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_projection_is_rejected(bad):
    """Nonfinite input data cannot become a canonical semantic identity."""
    projection = {"schema": "bad/1", "selected_names": ["value"],
                  "values": {"value": bad}, "value_contracts": {"value": {}}}
    with pytest.raises(ValueError, match="non-finite"):
        replace(_contract(_raw()), parameter_projection=projection)


@pytest.mark.parametrize("names", [["b", "a"], ["a", "a"], [""]])
def test_selected_parameter_names_must_be_explicit_sorted_and_distinct(names):
    """A canonical projection cannot silently discard or reorder dependency names."""
    projection = {"schema": "bad/1", "selected_names": names, "values": {}, "value_contracts": {}}
    with pytest.raises(ValueError):
        replace(_contract(_raw()), parameter_projection=projection)


def test_typed_load_requires_independent_requested_snapshot(tmp_path):
    """Typed history cannot establish the current owner schema by itself."""
    raw = _raw()
    owner = _owner()
    selected = bind_raw_port(_contract(raw), raw, parameter_snapshot=owner.resolve())
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    with pytest.raises(TypeError):
        load_raw_port(store, _contract(raw))
    with pytest.raises(ValueError, match="requested_parameters"):
        load_raw_port(store, _contract(raw), requested_parameters=None)
    assert load_raw_port(store, _contract(raw), requested_parameters=owner.resolve()).ref == selected.ref


def test_schemaless_history_cannot_authorize_current_typed_owner(tmp_path):
    """An absent calculated snapshot is historical rather than a typed exact hit."""
    raw = _raw()
    store = CacheStore(tmp_path)
    save_raw_port(store, bind_raw_port(_contract(raw), raw))
    with pytest.raises(ValueError, match="owner schema"):
        load_raw_port(store, _contract(raw), requested_parameters=_owner().resolve())


@pytest.mark.parametrize("drift", ["schema", "fields", "type", "unit", "nullable", "impact"])
def test_raw_owner_contract_rejects_independent_schema_drift(tmp_path, drift):
    """Self-consistent snapshots still require the independently declared current schema."""
    raw = _raw()
    owner = _owner()
    original = owner.specs[0]
    changed = {
        "schema": replace(owner, schema_version="typed-owner/2"),
        "fields": replace(owner, specs=owner.specs + (ParameterSpec("extra", bool, False),)),
        "type": replace(owner, specs=(replace(original, value_type=int, default=1),)),
        "unit": replace(owner, specs=(replace(original, unit="rad"),)),
        "nullable": replace(owner, specs=(replace(original, nullable=True),)),
        "impact": replace(owner, specs=(replace(original, impact=ParameterImpact.METADATA_ONLY),)),
    }[drift]
    store = CacheStore(tmp_path)
    save_raw_port(store, bind_raw_port(_contract(raw), raw, parameter_snapshot=owner.resolve()))
    with pytest.raises(ValueError, match="owner schema"):
        load_raw_port(store, _contract(raw), requested_parameters=changed.resolve())


def test_typed_load_rejects_self_consistent_forged_impact(tmp_path):
    """Valid saved checksums do not authorize an altered owner impact declaration."""
    raw = _raw()
    owner = replace(_owner(), specs=(replace(_owner().specs[0],
                    impact=ParameterImpact.REUSE_WITH_WARNING),))
    forged = replace(owner, specs=(replace(owner.specs[0], impact=ParameterImpact.METADATA_ONLY),))
    store = CacheStore(tmp_path)
    save_raw_port(store, bind_raw_port(_contract(raw), raw, parameter_snapshot=forged.resolve()))
    with pytest.raises(ValueError, match="owner schema"):
        load_raw_port(store, _contract(raw), requested_parameters=owner.resolve())


def test_selected_parameter_reuse_preserves_original_audit_and_bytes(tmp_path):
    """Only selected computation values miss; warning/unselected edits retain history."""
    raw = _raw()
    owner = ParameterSchema(raw.package_id, "selected/1", (
        ParameterSpec("compute", float, 1.0),
        ParameterSpec("review", float, 1.0, impact=ParameterImpact.REUSE_WITH_WARNING),
        ParameterSpec("other", float, 1.0),
        ParameterSpec("note", str, "old", impact=ParameterImpact.METADATA_ONLY),
    ))
    original = owner.resolve()
    contract = replace(_contract(raw), parameter_projection=_projection(original, ["compute", "review"]))
    publication = bind_raw_port(contract, raw, parameter_snapshot=original)
    store = CacheStore(tmp_path)
    entry = save_raw_port(store, publication)
    before = entry.payload_paths[0].read_bytes()
    for changes in ({"other": 2.0}, {"review": 2.0}, {"note": "new"}):
        requested = owner.resolve(changes)
        restored = load_raw_port(store, contract, requested_parameters=requested)
        assert restored.ref == publication.ref
        assert restored.parameter_snapshot == original
        assert entry.payload_paths[0].read_bytes() == before
    changed = owner.resolve({"compute": 2.0})
    current = replace(contract, parameter_projection=_projection(changed, ["compute", "review"]))
    assert load_raw_port(store, current, requested_parameters=changed) is None


def test_snapshot_validation_uses_actual_value_type_and_original_fingerprint():
    """Direct construction cannot bypass A's complete historical-value validation."""
    snapshot = _owner().resolve()
    raw = _raw()
    malformed = replace(snapshot, effective_parameters={"review_m": "wrong"},
                        calculated_parameters={"review_m": "wrong"})
    with pytest.raises(TypeError, match="float"):
        bind_raw_port(_contract(raw), raw, parameter_snapshot=malformed)
    with pytest.raises(ValueError, match="fingerprint"):
        bind_raw_port(_contract(raw), raw, parameter_snapshot=replace(snapshot, parameter_fingerprint="a" * 64))


def test_raw_envelope_rejects_unknown_schema_with_valid_digests(tmp_path):
    """A refreshed B byte digest cannot admit an unsupported semantic envelope."""
    raw = _raw()
    publication = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    entry = save_raw_port(store, publication)
    assert load_raw_port(store, publication.contract, requested_parameters=None) == publication
    original = selected_raw_bytes(raw)
    document = json.loads(entry.payload_paths[0].read_bytes())
    document["schema"] = "semantic-output-receipt/v999"
    _rewrite(entry, document)
    assert hashlib.sha256(entry.payload_paths[0].read_bytes()).hexdigest() == json.loads(
        entry.receipt_path.read_bytes())["payload"]["sha256"]
    with pytest.raises(ValueError, match="schema"):
        load_raw_port(store, publication.contract, requested_parameters=None)
    assert selected_raw_bytes(raw) == original


@pytest.mark.parametrize("field,value", [
    ("type", "untrusted.module.Type"), ("unit", "cm"), ("nullable", "false"),
    ("impact", "ignore"), ("value", "wrong"), ("extra", True),
])
def test_saved_snapshot_declarations_are_validated_through_raw_loader(tmp_path, field, value):
    """Storage-valid bytes still pass A's restricted historical declaration/value parser."""
    raw = _raw()
    publication = bind_raw_port(_contract(raw), raw, parameter_snapshot=_owner().resolve())
    store = CacheStore(tmp_path)
    entry = save_raw_port(store, publication)
    document = json.loads(entry.payload_paths[0].read_bytes())
    snapshot = document["parameter_snapshot"]
    if field in {"type", "unit", "nullable"}:
        snapshot["parameter_value_contracts"]["review_m"][field] = value
    elif field == "impact":
        snapshot["parameter_impacts"]["review_m"] = value
    elif field == "value":
        snapshot["effective_parameters"]["review_m"] = value
        snapshot["calculated_parameters"]["review_m"] = value
    else:
        snapshot["extra"] = value
    _rewrite(entry, document)
    with pytest.raises((TypeError, ValueError)):
        load_raw_port(store, publication.contract, requested_parameters=_owner().resolve())


@pytest.mark.parametrize("mutation", ["selected-digest", "inner-digest", "inner-schema", "inner-reading",
                                       "address", "extra-field", "missing-inner-digest"])
def test_resigned_storage_rejects_inconsistent_package_payload(tmp_path, mutation):
    """Each package binding remains mandatory after outer storage checks pass."""
    raw = _raw()
    publication = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    entry = save_raw_port(store, publication)
    document = json.loads(entry.payload_paths[0].read_bytes())
    if mutation == "selected-digest":
        document["ref"]["payload_fingerprint"] = "a" * 64
    elif mutation == "inner-digest":
        document["raw_view"]["payload_fingerprint"] = "a" * 64
    elif mutation == "inner-schema":
        document["raw_view"]["schema"] = "unsupported"
    elif mutation == "inner-reading":
        document["raw_view"]["outputs"][0]["observation"] = {"changed": True}
    elif mutation == "address":
        document["ref"]["source_fingerprint"] = "a" * 64
    elif mutation == "extra-field":
        document["unexpected"] = True
    else:
        del document["raw_view"]["payload_fingerprint"]
    _rewrite(entry, document)
    with pytest.raises(ValueError):
        load_raw_port(store, publication.contract, requested_parameters=None)


def test_validator_checks_opaque_storage_contract_and_full_address():
    """B's storage address and declared package context must agree with the envelope."""
    publication = bind_raw_port(_contract(_raw()), _raw())
    payload = serialize_raw_port_publication(publication)
    context = _context(publication)
    assert validate_port_payload(payload, context) is None
    with pytest.raises(ValueError, match="address"):
        validate_port_payload(payload, replace(context, address=replace(context.address, output_port="other")))
    with pytest.raises(ValueError, match="storage contract"):
        validate_port_payload(payload, replace(context, contract={}))


def test_upstream_refs_keep_full_addresses_and_real_deletion_edges(tmp_path):
    """Deleting a selected raw upstream orphans its true semantic dependent."""
    raw = _raw()
    store = CacheStore(tmp_path)
    upstream = bind_raw_port(_contract(raw, "source"), raw)
    save_raw_port(store, upstream)
    contract = replace(_contract(raw), upstream_refs=(upstream.ref,))
    selected = bind_raw_port(contract, raw)
    entry = save_raw_port(store, selected)
    assert _canonical_json(entry.receipt["upstream_refs"]) == _canonical_json((upstream.ref.address,))
    assert load_raw_port(store, contract, requested_parameters=None) == selected
    assert store.delete_exact(upstream.ref.address)
    assert load_raw_port(store, contract, requested_parameters=None) is None


def test_resigned_storage_cannot_drop_declared_upstream_edges(tmp_path):
    """A valid wrapper checksum does not permit receipt/semantic graph disagreement."""
    raw = _raw()
    store = CacheStore(tmp_path)
    upstream = bind_raw_port(_contract(raw, "source"), raw)
    save_raw_port(store, upstream)
    contract = replace(_contract(raw), upstream_refs=(upstream.ref,))
    entry = save_raw_port(store, bind_raw_port(contract, raw))
    receipt = json.loads(entry.receipt_path.read_bytes())
    receipt["upstream_refs"] = []
    receipt["receipt_fingerprint"] = fingerprint_evidence_dependency({
        key: value for key, value in receipt.items() if key != "receipt_fingerprint"})
    write_receipt(entry.receipt_path, receipt)
    with pytest.raises(ValueError, match="upstream"):
        load_raw_port(store, contract, requested_parameters=None)


def test_native_upstream_payloads_do_not_require_a_semantic_codec(tmp_path):
    """An exact B native/legacy entry remains a valid generic upstream address."""
    store = CacheStore(tmp_path)
    address = CacheAddress("native-source", "native-owner", "combined", "raw", "native-id")
    payload = b'{"schema":"native/v1","value":1}'

    def native_validator(value, context):
        """Retain the owning codec rather than applying semantic validation to native bytes."""
        assert context.address == address
        if value != payload:
            raise ValueError("native payload mismatch")

    store.put(address, contract={}, payload=payload, payload_format="json", validator=native_validator)
    reference = OutputPortRef(address.source_fingerprint, address.package_id, address.output_port,
                              address.identity, address.layer, hashlib.sha256(payload).hexdigest())
    raw = _raw()
    contract = replace(_contract(raw), upstream_refs=(reference,))
    publication = bind_raw_port(contract, raw)
    save_raw_port(store, publication)
    assert load_raw_port(store, contract, requested_parameters=None) == publication


@pytest.mark.parametrize("semantic", [True, False], ids=["semantic", "native"])
def test_upstream_reference_digest_must_match_actual_selected_bytes(tmp_path, semantic):
    """An intact B entry cannot satisfy a ref that names different selected content."""
    raw = _raw()
    store = CacheStore(tmp_path)
    if semantic:
        upstream = bind_raw_port(_contract(raw, "source"), raw)
        save_raw_port(store, upstream)
        reference = upstream.ref
    else:
        address = CacheAddress("native-source", "native-owner", "combined", "raw", "native-id")
        payload = b"native binary content"

        def validate_native(value, context):
            """Allow only the original native payload through its own owner boundary."""
            if value != payload:
                raise ValueError("native payload mismatch")

        store.put(address, contract={}, payload=payload, payload_format="native", validator=validate_native)
        reference = OutputPortRef(address.source_fingerprint, address.package_id, address.output_port,
                                  address.identity, address.layer, hashlib.sha256(payload).hexdigest())
    wrong = replace(reference, payload_fingerprint="a" * 64)
    contract = replace(_contract(raw), upstream_refs=(wrong,))
    save_raw_port(store, bind_raw_port(contract, raw))
    with pytest.raises(ValueError, match="upstream.*(fingerprint|ref)"):
        load_raw_port(store, contract, requested_parameters=None)


def _forbidden_processor(view, parameters):
    """Detect any callback invocation on a read-only or reusable selected result."""
    pytest.fail("the selected processor ran unexpectedly")


def test_selected_processing_hits_without_reinvoking_callback(tmp_path):
    """A persisted processor binds selected raw bytes and preserves all three digests."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    calls = []

    def process(view, parameters):
        """Record exactly which selected view reaches the existing processor."""
        calls.append(view)
        return _process(view, parameters)

    processor = EvidenceOutputProcessor("selected-process", "1", process, {"value": 0.75})
    first = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    second = run_port_processor(selected, _package(replace(processor, function=_forbidden_processor)),
        store=store, current_raw_contract=_contract(raw), requested_raw_parameters=None)
    assert not first.cache_hit and second.cache_hit
    assert calls == [selected.raw_view]
    assert first.publication == second.publication
    assert first.publication.raw_ref == selected.ref
    assert second.publication.ref.output_port == "reading"
    assert second.publication.ref.layer == "processed"
    assert first.cache_reuse == "computed" and second.cache_reuse == "exact_hit"
    assert second.cache_status["freshness"] == "fresh"
    assert second.cache_status["recompute_required"] is False
    assert second.publication.identity == processed_port_key(selected, processor)
    inner = serialize_evidence_processed_output(second.publication.processed_output)
    assert second.publication.ref.processing_identity == inner["processing_identity"]
    assert second.publication.identity != inner["processing_identity"]
    entry = next(item for item in store.list() if item.address.layer == "processed")
    assert _canonical_json(entry.receipt["upstream_refs"]) == _canonical_json((selected.ref.address,))
    digests = {inner["payload_fingerprint"], second.publication.ref.payload_fingerprint,
               entry.receipt["payload"]["sha256"]}
    assert len(digests) == 3
    assert second.publication.ref.payload_fingerprint == hashlib.sha256(
        selected_processed_bytes(second.publication.processed_output)).hexdigest()
    assert second.cache_location == str(entry.payload_paths[0].parent)


@pytest.mark.parametrize("change", ["version", "value", "raw-observation"])
def test_selected_processing_key_changes_for_actual_recipe_or_selected_bytes(tmp_path, change):
    """Recipe computation changes and selected raw readings each require a distinct result."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _process, {"value": 0.75})
    first = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    if change == "version":
        processor = replace(processor, version="2")
    elif change == "value":
        processor = replace(processor, parameters={"value": 0.5})
    else:
        changed_raw = replace(raw, outputs=(replace(raw.outputs[0], observation=0.4),))
        selected = bind_raw_port(replace(_contract(changed_raw),
            input_fingerprints={"source": "d" * 64}), changed_raw)
        save_raw_port(store, selected)
    second = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=selected.contract, requested_raw_parameters=None)
    assert second.cache_hit is False
    assert second.publication.identity != first.publication.identity


@pytest.mark.parametrize("change", ["contract", "missing", "deleted", "supplied-ref"])
def test_processing_requires_independent_current_raw_before_callback(tmp_path, change):
    """Saved typed objects cannot bypass changed, absent or deleted current raw entries."""
    raw = _raw()
    contract = _contract(raw)
    selected = bind_raw_port(contract, raw)
    store = CacheStore(tmp_path)
    if change != "missing":
        save_raw_port(store, selected)
    if change == "contract":
        contract = replace(contract, input_fingerprints={"source": "d" * 64})
    elif change == "deleted":
        assert store.delete_exact(selected.ref.address)
    elif change == "supplied-ref":
        selected = bind_raw_port(replace(contract, output_port="foreign"), raw)
    processor = EvidenceOutputProcessor("selected-process", "1", _forbidden_processor)
    with pytest.raises(ValueError, match="current raw contract"):
        run_port_processor(selected, _package(processor), store=store,
            current_raw_contract=contract, requested_raw_parameters=None)
    assert not any(entry.address.layer == "processed" for entry in store.list())


@pytest.mark.parametrize("drift", ["schema", "fields", "type", "unit", "nullable", "impact", "none"])
def test_processing_forwards_independent_raw_owner_context(tmp_path, drift):
    """The processing adapter retains all independent owner declaration checks."""
    raw = _raw()
    owner = _owner()
    original = owner.specs[0]
    changed = {
        "schema": replace(owner, schema_version="typed-owner/2"),
        "fields": replace(owner, specs=owner.specs + (ParameterSpec("extra", bool, False),)),
        "type": replace(owner, specs=(replace(original, value_type=int, default=1),)),
        "unit": replace(owner, specs=(replace(original, unit="rad"),)),
        "nullable": replace(owner, specs=(replace(original, nullable=True),)),
        "impact": replace(owner, specs=(replace(original, impact=ParameterImpact.METADATA_ONLY),)),
        "none": None,
    }[drift]
    selected = bind_raw_port(_contract(raw), raw, parameter_snapshot=owner.resolve())
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _forbidden_processor)
    with pytest.raises(ValueError, match="(owner schema|requested_parameters)"):
        run_port_processor(selected, _package(processor), store=store,
            current_raw_contract=_contract(raw),
            requested_raw_parameters=None if changed is None else changed.resolve())
    assert not any(entry.address.layer == "processed" for entry in store.list())


def test_processing_rejects_schemaless_history_for_current_typed_owner(tmp_path):
    """Schema-less historical bytes cannot substitute for a newly declared raw owner."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _forbidden_processor)
    with pytest.raises(ValueError, match="owner schema"):
        run_port_processor(selected, _package(processor), store=store,
            current_raw_contract=_contract(raw), requested_raw_parameters=_owner().resolve())
    assert not any(entry.address.layer == "processed" for entry in store.list())


@pytest.mark.parametrize("layer", ["raw", "processed"])
def test_processed_envelope_rejects_unknown_schema_with_valid_digests(tmp_path, layer):
    """Refreshed outer storage hashes never authorize an unsupported semantic schema."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _process)
    first = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    entry = next(item for item in store.list() if item.address.layer == layer)
    document = json.loads(entry.payload_paths[0].read_bytes())
    document["schema"] = "semantic-output-receipt/v99"
    _rewrite(entry, document)
    before = entry.payload_paths[0].read_bytes()
    blocked = replace(processor, function=_forbidden_processor)
    with pytest.raises(ValueError, match="schema"):
        run_port_processor(selected, _package(blocked), store=store,
            current_raw_contract=_contract(raw), requested_raw_parameters=None)
    assert entry.payload_paths[0].read_bytes() == before
    if layer == "processed":
        with pytest.raises(ValueError, match="schema"):
            load_processed_port(store, first.publication.ref,
                current_raw_contract=_contract(raw), requested_raw_parameters=None, processor=blocked)


@pytest.mark.parametrize("changes,warning", [
    ({"review": 2.0}, "review"),
    ({"other": 2.0}, None),
    ({"other_review": 2.0}, None),
    ({"note": "new"}, None),
])
def test_raw_warning_comparison_uses_current_selected_names(tmp_path, changes, warning):
    """Only selected raw knobs affect reuse while complete requested audit stays visible."""
    raw = _raw()
    owner = ParameterSchema(raw.package_id, "selected-processing/1", (
        ParameterSpec("compute", float, 1.0),
        ParameterSpec("review", float, 1.0, impact=ParameterImpact.REUSE_WITH_WARNING),
        ParameterSpec("other", float, 1.0),
        ParameterSpec("other_review", float, 1.0, impact=ParameterImpact.REUSE_WITH_WARNING),
        ParameterSpec("note", str, "old", impact=ParameterImpact.METADATA_ONLY),
    ))
    calculated = owner.resolve()
    contract = replace(_contract(raw), parameter_projection=_projection(calculated, ["compute", "review"]))
    selected = bind_raw_port(contract, raw, parameter_snapshot=calculated)
    store = CacheStore(tmp_path)
    entry = save_raw_port(store, selected)
    before = entry.payload_paths[0].read_bytes()
    processor = EvidenceOutputProcessor("selected-process", "1", _process)
    first = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=contract, requested_raw_parameters=calculated)
    requested = owner.resolve(changes)
    current = replace(contract, parameter_projection=_projection(requested, ["compute", "review"]))
    second = run_port_processor(selected, _package(replace(processor, function=_forbidden_processor)),
        store=store, current_raw_contract=current, requested_raw_parameters=requested)
    assert second.cache_hit and second.publication.ref == first.publication.ref
    status = second.cache_status["parameter_status"]
    assert status["recompute_required"] is False
    assert status["exact_match"] is (warning is None)
    assert [item["parameter"] for item in status["warnings"]] == ([] if warning is None else [warning])
    assert _json_value(status["calculated_parameters"]) == calculated.to_json()["calculated_parameters"]
    assert _json_value(status["requested_parameters"]) == requested.to_json()["effective_parameters"]
    assert entry.payload_paths[0].read_bytes() == before
    changed = owner.resolve({"compute": 2.0})
    newer = replace(contract, parameter_projection=_projection(changed, ["compute", "review"]))
    assert load_raw_port(store, newer, requested_parameters=changed) is None
    with pytest.raises(ValueError, match="current raw contract"):
        run_port_processor(selected, _package(replace(processor, function=_forbidden_processor)),
            store=store, current_raw_contract=newer, requested_raw_parameters=changed)


@pytest.mark.parametrize("change", ["warning", "metadata"])
def test_processed_warning_hit_reports_historical_and_requested_values(tmp_path, change):
    """Warning and metadata edits reuse historical bytes with a separate current audit."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    schema = ParameterSchema(raw.package_id, "warning-process/1", (
        ParameterSpec("value", float, 0.75),
        ParameterSpec("review_m", float, 0.01, unit="m", impact=ParameterImpact.REUSE_WITH_WARNING),
        ParameterSpec("note", str, "old", impact=ParameterImpact.METADATA_ONLY),
    ))
    processor = EvidenceOutputProcessor("warning-process", "1", _process, parameter_schema=schema)
    first = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    edits = {"review_m": 0.02} if change == "warning" else {"note": "new"}
    requested = replace(processor, function=_forbidden_processor,
                        parameters={**processor.parameters, **edits})
    second = run_port_processor(selected, _package(requested), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    assert second.cache_hit and second.publication.ref == first.publication.ref
    assert second.publication.processed_output.parameter_snapshot == processor.parameter_snapshot
    assert selected_processed_bytes(second.publication.processed_output) == selected_processed_bytes(
        first.publication.processed_output)
    status = second.cache_status["processed_parameter_status"]
    assert status["reuse"] == ("reuse_with_warning" if change == "warning" else "exact")
    assert status["exact_match"] is (change != "warning")
    assert [item["parameter"] for item in status["warnings"]] == (["review_m"] if change == "warning" else [])
    for name, value in edits.items():
        assert status["calculated_parameters"][name] == processor.parameters[name]
        assert status["requested_parameters"][name] == value


@pytest.mark.parametrize("case", ["present", "missing", "deleted", "wrong-recipe", "raw-deleted"])
def test_read_only_processed_loader_never_calculates_missing_selection(tmp_path, case):
    """Saved selection reads stay inert for hits, absent versions and deleted dependencies."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _process)
    first = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    reference = first.publication.ref
    if case == "missing":
        reference = replace(reference, identity="absent-version")
    elif case == "deleted":
        assert store.delete_exact(reference.address)
    elif case == "raw-deleted":
        assert store.delete_exact(selected.ref.address)
    requested = replace(processor, function=_forbidden_processor,
                        version="2" if case == "wrong-recipe" else "1")
    if case == "raw-deleted":
        with pytest.raises(ValueError, match="current raw contract"):
            load_processed_port(store, reference, current_raw_contract=_contract(raw),
                requested_raw_parameters=None, processor=requested)
    else:
        actual = load_processed_port(store, reference, current_raw_contract=_contract(raw),
            requested_raw_parameters=None, processor=requested)
        assert actual == (first.publication if case == "present" else None)


@pytest.mark.parametrize("configured", [True, False])
def test_failed_processing_is_explicit_and_never_published(tmp_path, configured):
    """Missing or failed processors keep empty core failure outcomes without cache hits."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)

    def failed(view, parameters):
        """Exercise the existing callback-failure result instead of raw fallback."""
        raise RuntimeError("expected processing failure")

    processor = EvidenceOutputProcessor("failed", "1", failed) if configured else None
    result = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    assert result.cache_hit is False and result.status == "unavailable"
    assert result.publication.processed_output.outputs == ()
    assert result.publication.processed_output.error_code == (
        "OUTPUT_PROCESSING_FAILED" if configured else "OUTPUT_FUNCTION_NOT_CONFIGURED")
    assert result.cache_location is None
    assert not any(entry.address.layer == "processed" for entry in store.list())


@pytest.mark.parametrize("field,value", [
    ("package_id", "other-package"),
    ("output_function_id", "other-producer"),
    ("output_function_version", "2"),
])
def test_processed_hit_still_requires_matching_package_producer(tmp_path, field, value):
    """An existing processed entry cannot bypass the core producer ownership contract."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _process)
    run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    changed = replace(_package(replace(processor, function=_forbidden_processor)), **{field: value})
    with pytest.raises(ValueError, match="producer"):
        run_port_processor(selected, changed, store=store,
            current_raw_contract=_contract(raw), requested_raw_parameters=None)


def test_semantic_processed_dependency_is_reopened_without_recalculation(tmp_path):
    """A downstream raw entry validates selected processed bytes and the live raw chain."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _process)
    processed = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None).publication
    dependent = bind_raw_port(replace(_contract(raw, "modulation"), upstream_refs=(processed.ref,)), raw)
    save_raw_port(store, dependent)
    assert load_raw_port(store, dependent.contract, requested_parameters=None) == dependent
    assert store.delete_exact(selected.ref.address)
    assert load_raw_port(store, dependent.contract, requested_parameters=None) is None


@pytest.mark.parametrize("mutation", ["semantic-kind", "raw-ref", "inner-digest", "inner-identity", "target"])
def test_selected_processed_wrapper_validates_exact_bindings(tmp_path, mutation):
    """Valid outer storage bytes cannot conceal broken semantic or inner bindings."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    processor = EvidenceOutputProcessor("selected-process", "1", _process)
    publication = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None).publication
    entry = next(item for item in store.list() if item.address.layer == "processed")
    document = json.loads(entry.payload_paths[0].read_bytes())
    if mutation == "semantic-kind":
        document["ref"]["output_port"] = "path_distance"
    elif mutation == "raw-ref":
        document["raw_ref"]["payload_fingerprint"] = "a" * 64
    elif mutation == "inner-digest":
        document["processed_view"]["outputs"][0]["observation"] = 0.4
    elif mutation == "inner-identity":
        document["processed_view"]["processing_identity"] = "a" * 64
    else:
        output = publication.processed_output
        changed = replace(output, outputs=(replace(output.outputs[0],
            target={"kind": "contract_target", "id": "foreign", "identity": "foreign"}),))
        document["processed_view"] = serialize_evidence_processed_output(changed)
        document["ref"]["payload_fingerprint"] = hashlib.sha256(selected_processed_bytes(changed)).hexdigest()
    _rewrite(entry, document)
    with pytest.raises(ValueError):
        load_processed_port(store, publication.ref, current_raw_contract=_contract(raw),
            requested_raw_parameters=None, processor=replace(processor, function=_forbidden_processor))


def test_corrupt_processed_entry_is_read_only_then_preserved_before_recalculation(tmp_path):
    """Only the owning processing runner may retain and rebuild corrupt selected bytes."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    raw_entry = save_raw_port(store, selected)
    raw_before = raw_entry.payload_paths[0].read_bytes()
    calls = []

    def process(view, parameters):
        """Count only the transformation that owns the corrupted processed address."""
        calls.append(view)
        return _process(view, parameters)

    def forbidden_producer(sources):
        """Detect re-running unrelated raw calculation while repairing processed storage."""
        pytest.fail("processed repair invoked the raw producer")

    processor = EvidenceOutputProcessor("selected-process", "1", process)
    package = replace(_package(processor), output_function=forbidden_producer)
    first = run_port_processor(selected, package, store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    entry = next(item for item in store.list() if item.address.layer == "processed")
    corrupted = entry.payload_paths[0].read_bytes() + b" "
    entry.payload_paths[0].write_bytes(corrupted)
    assert load_processed_port(store, first.publication.ref, current_raw_contract=_contract(raw),
        requested_raw_parameters=None, processor=replace(processor, function=_forbidden_processor)) is None
    assert entry.payload_paths[0].read_bytes() == corrupted
    assert not (tmp_path / "quarantine").exists()
    repaired = run_port_processor(selected, package, store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    assert repaired.cache_hit is False and repaired.publication.ref == first.publication.ref
    assert len(calls) == 2 and raw_entry.payload_paths[0].read_bytes() == raw_before
    assert [path.read_bytes() for path in (tmp_path / "quarantine").rglob("payload.json")] == [corrupted]
