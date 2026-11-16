"""Saved processed ports retain explicit identities and the runtime validation boundary."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

import features.field_core as core
from .test_evidence_package_output import _snapshot_output, _source_envelope
from .test_evidence_package_processing import _channel, _package, _process, _raw


def _processed(raw=None):
    """Produce a real processed channel with the same address as the raw port."""
    raw = _raw() if raw is None else raw

    def process(source, parameters):
        """Retain the raw channel name to expose ambiguous port selection."""
        return (_channel(source, channel=source.outputs[0].channel, observation=0.75),)

    return _package(core.EvidenceOutputProcessor("saved-process", "1", process,
                    {"nested": {"items": [1, 2]}})).process_output(raw, package_freshness="fresh")


def _reference(raw, processed):
    """Address the processed port explicitly, never by channel-name inference."""
    return core.EvidencePackageChannelReference(raw.package_id, raw.output_identity,
        raw.outputs[0].target["identity"], raw.outputs[0].channel,
        port="processed", processing_identity=processed.processing_identity)


def _resign(payload):
    """Recompute only transport integrity so semantic decoder checks remain exercised."""
    payload.pop("payload_fingerprint", None)
    payload["payload_fingerprint"] = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return payload


def test_raw_v1_identity_and_complete_json_remain_historically_pinned():
    """New reference fields cannot perturb existing raw publications or fingerprints."""
    payload = core.serialize_evidence_package_output(_snapshot_output())
    assert payload["output_identity"] == "75c7c12b6e7e7fad88dbd692d919b240bb90c05bbf3f149774bc619a21652dd2"
    assert hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False).encode()).hexdigest() == "d3b4784491d6b6dbfac8531f63e926d6429a0d065682540ced547dbd230b837b"
    assert set(payload["dependencies"][0]["channels"][0]) == {
        "package_id", "output_identity", "target_identity", "channel"}


def test_processed_json_roundtrip_never_executes_callback_and_freezes_parameters():
    """Saved successful channels retain all metadata and independently checked payload integrity."""
    raw = _raw()
    processed = _processed(raw)
    saved = core.serialize_evidence_processed_output(processed)
    assert saved["schema"] == "evidence-processed-output/v1"
    assert saved["processing_identity"] == processed.processing_identity
    assert _resign(dict(saved))["payload_fingerprint"] == saved["payload_fingerprint"]
    restored = core.deserialize_evidence_processed_output(json.loads(json.dumps(saved)), raw_output=raw)
    assert restored == processed
    assert restored.outputs[0].observation == 0.75
    assert restored.parameters["nested"]["items"] == (1, 2)
    with pytest.raises(TypeError):
        restored.parameters["nested"]["items"][0] = 9


def test_legacy_processed_receipt_keeps_legacy_attestation():
    """Old receipts stay readable without inventing a typed parameter history."""
    raw = _raw()
    old = core.serialize_evidence_processed_output(_processed(raw))
    assert "parameter_snapshot" not in old
    restored = core.deserialize_evidence_processed_output(old, raw_output=raw)
    assert restored.parameter_snapshot is None
    assert core.serialize_evidence_processed_output(restored) == old


@pytest.mark.parametrize("variant,expected", [
    ("foreign-owner", "parameter snapshot must belong to this package"),
    ("effective-values", "parameter snapshot effective values must match parameters"),
])
def test_resigned_typed_snapshot_still_requires_semantic_validation(variant, expected):
    """A valid outer digest cannot admit an independently valid but incompatible snapshot."""
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec, ParameterSnapshot

    raw = _raw()
    schema = ParameterSchema(
        "contract-package",
        "processor-parameters/1",
        (ParameterSpec("value", float, 0.25, minimum=0.0, maximum=1.0),),
    )
    processor = core.EvidenceOutputProcessor(
        "typed-process", "1", _process, {"value": 0.25}, parameter_schema=schema,
    )
    processed = _package(processor).process_output(raw, package_freshness="fresh")
    saved = core.serialize_evidence_processed_output(processed)
    snapshot_schema = replace(schema, package_id="foreign-package") if variant == "foreign-owner" else schema
    snapshot = snapshot_schema.resolve({"value": 0.75 if variant == "effective-values" else 0.25})
    saved["parameter_snapshot"] = ParameterSnapshot.from_json(snapshot.to_json()).to_json()
    _resign(saved)

    with pytest.raises(ValueError, match=expected):
        core.deserialize_evidence_processed_output(saved, raw_output=raw)


def test_pre_a_processed_fixture_roundtrips_legacy_bytes():
    """Public readers preserve independently retained PRE-A raw and processed publications."""
    fixture = (
        Path(__file__).parent / "fixtures" / "cache_migration" / "pre_parameter_sidecar"
        / "raw_processed"
        / "processed-9bfb2a3d1e34c71025b174bc673547fbf2353b5a76de32e3eecf634f4a651b26.json"
    )
    original_bytes = fixture.read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == \
        "90bd3740b0bcfc745ce0c3f3f52737fb75e808ebb86cb2c01b7293d38646eeab"
    original = json.loads(original_bytes)

    raw_originals = []
    for path in fixture.parent.glob("*.json"):
        receipt = json.loads(path.read_bytes())
        if (
            receipt.get("schema") == "evidence-package-cache/v1"
            and receipt.get("cache_key") ==
            "12a42760a9d8c2a9e021ba17505ba11fa4d816f2ef92c20339cd0d0b1260a283"
        ):
            raw_originals.append(receipt["raw_output"])
    assert len(raw_originals) == 1, (
        "A unique retained PRE-A raw receipt is required for "
        f"{original['raw_output_identity']} / {original['raw_payload_fingerprint']}; "
        "raw bytes must not be reconstructed."
    )
    raw_original = raw_originals[0]
    assert raw_original["package_id"] == original["package_id"]
    assert raw_original["output_identity"] == original["raw_output_identity"]
    assert raw_original["payload_fingerprint"] == original["raw_payload_fingerprint"], (
        "The retained raw receipt belongs to another publication; the matching raw fixture is missing."
    )
    raw_original_bytes = json.dumps(
        raw_original, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    assert _resign(json.loads(raw_original_bytes)) == raw_original, (
        "The retained raw content does not match its declared digest; "
        "the matching PRE-A raw fixture is required."
    )

    # Decode separate copies so reader mutation cannot alter either retained oracle.
    raw = core.deserialize_evidence_package_output(json.loads(raw_original_bytes))
    raw_saved = core.serialize_evidence_package_output(raw)
    assert raw_saved == raw_original
    assert json.dumps(
        raw_saved, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8") == raw_original_bytes

    restored = core.deserialize_evidence_processed_output(
        json.loads(original_bytes), raw_output=raw,
    )
    assert "parameter_snapshot" not in original
    assert restored.parameter_snapshot is None
    legacy = core.serialize_evidence_processed_output(restored)
    assert legacy == original
    assert json.dumps(
        legacy, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8") == original_bytes


@pytest.mark.parametrize("state", ["unconfigured", "stale", "failure"])
def test_empty_processing_errors_roundtrip_without_raw_fallback(state):
    """All supported closed-port outcomes survive persistence with no usable channel."""
    raw = _raw()

    def fail(source, parameters):
        """Expose execution through a real processing failure before serialization."""
        raise ValueError("fixture failure")

    processor = None if state == "unconfigured" else core.EvidenceOutputProcessor(
        "saved-process", "1", fail if state == "failure" else _process)
    result = _package(processor).process_output(raw, package_freshness="stale" if state == "stale" else "fresh")
    restored = core.deserialize_evidence_processed_output(core.serialize_evidence_processed_output(result), raw_output=raw)
    assert restored == result and restored.outputs == ()
    assert restored.error_code == {"unconfigured": "OUTPUT_FUNCTION_NOT_CONFIGURED",
        "stale": "OUTPUT_SOURCE_NOT_FRESH", "failure": "OUTPUT_PROCESSING_FAILED"}[state]


@pytest.mark.parametrize("port,identity", [("other", None), ("raw", "recipe"), ("processed", None), ("processed", " ")])
def test_reference_rejects_ambiguous_or_incomplete_port_addresses(port, identity):
    """Malformed ports cannot silently select a raw or unrelated processed value."""
    with pytest.raises(ValueError):
        core.EvidencePackageChannelReference("p", "o", "t", "c", port=port, processing_identity=identity)


def test_same_target_and_channel_select_only_the_explicit_port():
    """A processed selection requires the exact typed recipe and never falls back to raw."""
    raw = _raw()
    processed = _processed(raw)
    reference = _reference(raw, processed)
    raw_ref = replace(reference, port="raw", processing_identity=None)
    assert core.read_evidence_package_channel(raw, raw_ref, processed_output=processed) is raw.outputs[0]
    assert core.read_evidence_package_channel(raw, reference, processed_output=processed) is processed.outputs[0]
    for supplied in (None, replace(processed, processor_version="2")):
        with pytest.raises((TypeError, ValueError)):
            core.read_evidence_package_channel(raw, reference, processed_output=supplied)


@pytest.mark.parametrize("freshness", ["fresh", "stale", "unavailable"])
def test_saved_processed_selection_requires_current_freshness(freshness):
    """A saved successful recipe grants no numeric permission without an explicit fresh gate."""
    raw = _raw()
    restored = core.deserialize_evidence_processed_output(core.serialize_evidence_processed_output(_processed(raw)), raw_output=raw)
    resolved = core.resolve_evidence_package_channel(raw, _reference(raw, restored),
        package_freshness=freshness, processed_output=restored)
    assert resolved.channel_status is core.FieldResultStatus.COMPUTED
    if freshness == "fresh":
        assert resolved.channel.observation == 0.75
    else:
        assert resolved.channel is None and resolved.audit_channel.observation is None
        assert resolved.effective_status is core.FieldResultStatus.NOT_AVAILABLE


@pytest.mark.parametrize("change", ["schema", "unknown", "missing-fingerprint", "missing-identity", "tamper", "identity", "parameters", "raw-binding", "lineage-port", "lineage-target", "range", "status", "nonfinite"])
def test_processed_reader_rejects_tampered_or_semantically_invalid_saved_channels(change):
    """Integrity and semantic checks reject edited observations, recipes, lineage, range and status."""
    raw = _raw()
    saved = core.serialize_evidence_processed_output(_processed(raw))
    if change == "schema":
        saved["schema"] = "evidence-processed-output/v2"
    elif change == "unknown":
        saved["future"] = True
    elif change == "missing-fingerprint":
        saved.pop("payload_fingerprint")
    elif change == "missing-identity":
        saved.pop("processing_identity")
    elif change == "tamper":
        saved["outputs"][0]["observation"] = 0.6
    elif change == "identity":
        saved["processing_identity"] = "foreign"
    elif change == "parameters":
        saved["parameters"]["nested"]["items"].append(3)
    elif change == "raw-binding":
        saved["raw_payload_fingerprint"] = "foreign"
    elif change == "lineage-port":
        saved["outputs"][0]["derived_from"][0].update(port="processed", processing_identity="foreign")
    elif change == "lineage-target":
        saved["outputs"][0]["derived_from"][0]["target_identity"] = "missing"
    elif change == "range":
        saved["outputs"][0]["scale"].update(value_range=[0, 0.5], endpoint_meanings=["low", "high"])
    elif change == "status":
        saved["outputs"][0].update(status="invalid", explanation="invalid source")
    else:
        saved["outputs"][0]["observation"] = float("inf")
    if change not in {"missing-fingerprint", "tamper"}:
        _resign(saved)
    with pytest.raises((TypeError, ValueError)):
        core.deserialize_evidence_processed_output(saved, raw_output=raw)


@pytest.mark.parametrize("change", ["observation", "producer", "package", "version"])
def test_processed_reader_binds_exact_raw_publication_content(change):
    """Even an unchanged calculation identity cannot admit a foreign raw reading."""
    raw = _raw()
    saved = core.serialize_evidence_processed_output(_processed(raw))
    foreign = replace(raw, outputs=(replace(raw.outputs[0], observation=4),)) if change == "observation" else replace(
        raw, **{{"producer": "output_function", "package": "package_id", "version": "output_function_version"}[change]: "foreign"})
    with pytest.raises(ValueError):
        core.deserialize_evidence_processed_output(saved, raw_output=foreign)


def test_processed_dependencies_consume_both_ports_and_strip_runtime_handles():
    """Downstream context keeps two same-address ports distinct and publishes compact references."""
    raw = _raw()
    processed = _processed(raw)
    reference = _reference(raw, processed)
    raw_ref = replace(reference, port="raw", processing_identity=None)
    dependency = core.EvidencePackageDependency(raw.package_id, raw.output_identity, (reference, raw_ref),
        raw, "fresh", source_processed_output=processed)

    def consume(context):
        """Copy actual processed data through declared dependency lineage."""
        assert len(context.resolved_dependencies) == 2
        resolved = next(item for item in context.resolved_dependencies if item.ref.port == "processed")
        assert resolved.channel.observation == 0.75
        return (replace(resolved.channel, derived_from=(reference, raw_ref)),)

    result = core.EvidencePackage("consumer", "consume", "1", None, consume).evaluate(
        (_source_envelope(),), dependencies=(dependency,), dependency_graph={"consumer": (raw.package_id,), raw.package_id: ()})
    assert result.outputs[0].observation == 0.75
    assert result.dependencies[0].source_output is None and result.dependencies[0].source_processed_output is None
    saved = core.serialize_evidence_package_output(result)
    assert "source_output" not in saved["dependencies"][0]
    assert "source_processed_output" not in saved["dependencies"][0]
    assert core.deserialize_evidence_package_output(saved) == result


@pytest.mark.parametrize("reference_count", [1, 12])
@pytest.mark.parametrize("freshness", ["fresh", "stale", "unavailable"])
def test_dependency_resolver_validates_raw_binding_once_and_matches_single_reads(
    reference_count, freshness, monkeypatch,
):
    """A batch verifies one complete raw binding while preserving each single-address result."""
    raw = _raw()

    def produce_many(source, parameters):
        """Publish multiple exact processed addresses over one authenticated raw channel."""
        return tuple(_channel(source, channel=f"processed-{index}", observation=index / 12)
                     for index in range(12))

    processor = core.EvidenceOutputProcessor("many-addresses", "1", produce_many)
    processed = _package(processor).process_output(raw, package_freshness="fresh")
    references = tuple(core.EvidencePackageChannelReference(
        raw.package_id,
        raw.output_identity,
        output.target["identity"],
        output.channel,
        port="processed",
        processing_identity=processed.processing_identity,
    ) for output in processed.outputs[:reference_count])
    dependency = core.EvidencePackageDependency(
        raw.package_id,
        raw.output_identity,
        references,
        raw,
        freshness,
        source_processed_output=processed,
    )
    expected = tuple(core.resolve_evidence_package_channel(
        raw,
        reference,
        package_freshness=freshness,
        processed_output=processed,
    ) for reference in dependency.channels)

    calls = 0
    serialize = core.serialize_evidence_package_output

    def counted_serialize(output):
        """Count complete raw payload fingerprint operations at the binding boundary."""
        nonlocal calls
        calls += 1
        return serialize(output)

    monkeypatch.setattr(core, "serialize_evidence_package_output", counted_serialize)
    actual = core._resolve_package_dependencies((dependency,))

    assert actual == expected
    assert calls == 1
    if freshness == "fresh":
        assert all(item.channel is not None and item.audit_channel.observation is not None for item in actual)
    else:
        assert all(item.channel is None and item.audit_channel.observation is None for item in actual)
        assert all(item.effective_status is core.FieldResultStatus.NOT_AVAILABLE for item in actual)


def test_dependency_resolver_rejects_missing_processed_binding():
    """A processed dependency without its typed source remains unusable and fails closed."""
    raw = _raw()
    processed = _processed(raw)
    dependency = core.EvidencePackageDependency(
        raw.package_id,
        raw.output_identity,
        (_reference(raw, processed),),
        raw,
        "fresh",
    )

    with pytest.raises(TypeError, match="processed_output must be an EvidenceProcessedOutput"):
        core._resolve_package_dependencies((dependency,))


@pytest.mark.parametrize("change", ["range", "status", "lineage", "raw-value"])
def test_direct_processed_objects_cannot_bypass_read_boundary_validation(change):
    """Typed construction is no substitute for validating the exact supplied raw binding."""
    raw = _raw()
    processed = _processed(raw)
    channel = processed.outputs[0]
    if change == "range":
        channel = replace(channel, scale=core.EvidenceOutputScale("bounded", value_range=(0, 0.5), endpoint_meanings=("low", "high")))
    elif change == "status":
        channel = replace(channel, status=core.FieldResultStatus.INVALID, explanation="invalid")
    elif change == "lineage":
        channel = replace(channel, derived_from=(replace(channel.derived_from[0], target_identity="missing"),))
    else:
        raw = replace(raw, outputs=(replace(raw.outputs[0], observation=None),))
    malformed = replace(processed, outputs=(channel,))
    with pytest.raises(ValueError):
        core.read_evidence_package_channel(raw, _reference(raw, malformed), processed_output=malformed)


@pytest.mark.parametrize("source_status,source_value,output_status,output_value,accepted", [
    ("computed", None, "computed", 0, False),
    ("partial", 1, "computed", 0, False),
    ("partial", 1, "partial", 0, True),
    ("partial", None, "partial", 0, False),
    ("not_available", None, "partial", 0, False),
    ("invalid", 1, "partial", 0, False),
    ("outside", 1, "partial", 0, False),
    ("ambiguous", 1, "partial", 0, False),
    ("not_evaluated", 1, "partial", 0, False),
    ("not_available", None, "not_available", None, True),
])
def test_decoded_processing_preserves_raw_missing_and_partial_limits(
    source_status, source_value, output_status, output_value, accepted,
):
    """A resigned snapshot cannot promote limited raw sources or invent their missing values."""
    raw = _raw()
    processed = _processed(raw)
    raw = replace(raw, outputs=(replace(raw.outputs[0], observation=source_value,
        status=source_status, explanation="source limit"),))
    channel = replace(processed.outputs[0], observation=output_value, status=output_status,
                      explanation="retained limit")
    forged = replace(processed, raw_payload_fingerprint=core.serialize_evidence_package_output(raw)["payload_fingerprint"],
                     outputs=(channel,))
    saved = core.serialize_evidence_processed_output(forged)
    if accepted:
        restored = core.deserialize_evidence_processed_output(saved, raw_output=raw)
        assert restored.outputs[0].observation == output_value
        assert restored.outputs[0].status == core.FieldResultStatus(output_status)
    else:
        with pytest.raises(ValueError):
            core.deserialize_evidence_processed_output(saved, raw_output=raw)


def test_runtime_processing_rejects_a_processed_port_as_its_raw_lineage():
    """A same-name processed port cannot masquerade as the processor's exact raw input."""
    raw = _raw()
    existing = _processed(raw)

    def process(source, parameters):
        """Cite the prior processed recipe instead of the supplied raw publication."""
        return (_channel(source, derived_from=(_reference(source, existing),)),)

    result = _package(core.EvidenceOutputProcessor("next", "1", process)).process_output(raw, package_freshness="fresh")
    assert result.error_code == "OUTPUT_PROCESSING_FAILED" and result.outputs == ()


def test_processed_payload_digest_covers_readings_independently_of_recipe_identity():
    """Two different observations from the same recipe need distinct full payload fingerprints."""
    raw = _raw()
    processed = _processed(raw)
    changed = replace(processed, outputs=(replace(processed.outputs[0], observation=0.5),))
    first = core.serialize_evidence_processed_output(processed)
    second = core.serialize_evidence_processed_output(changed)
    assert first["processing_identity"] == second["processing_identity"]
    assert first["payload_fingerprint"] != second["payload_fingerprint"]
    assert core.deserialize_evidence_processed_output(second, raw_output=raw).outputs[0].observation == 0.5


def test_dependency_addresses_sort_and_keep_distinct_processing_recipes():
    """Two processed recipes may declare the same target/channel without collapsing their address."""
    raw = _raw()
    processed = _processed(raw)
    first = _reference(raw, processed)
    second = replace(first, processing_identity="another-recipe")
    forward = core.EvidencePackageDependency(raw.package_id, raw.output_identity, (first, second))
    backward = core.EvidencePackageDependency(raw.package_id, raw.output_identity, (second, first))
    assert forward == backward and len(forward.channels) == 2
    with pytest.raises(ValueError, match="unique"):
        core.EvidencePackageDependency(raw.package_id, raw.output_identity, (first, first))


def test_processed_dependency_graph_checks_raw_upstream_declarations_before_callback():
    """The processed handle cannot hide dependencies retained on its matching raw publication."""
    raw = _raw()
    ancestor_ref = core.EvidencePackageChannelReference("ancestor", "ancestor-output", "t", "c")
    raw = replace(raw, dependencies=(core.EvidencePackageDependency("ancestor", "ancestor-output", (ancestor_ref,)),))
    processed = _processed(raw)
    dependency = core.EvidencePackageDependency(raw.package_id, raw.output_identity, (_reference(raw, processed),),
        raw, "fresh", source_processed_output=processed)
    called = []

    def consume(context):
        """Reveal an incorrectly admitted graph through a callback side effect."""
        called.append(True)
        return ()

    package = core.EvidencePackage("consumer", "consume", "1", None, consume)
    with pytest.raises(ValueError, match="upstream.*declared dependencies"):
        package.evaluate((_source_envelope(),), dependencies=(dependency,), dependency_graph={
            "consumer": (raw.package_id,), raw.package_id: (), "ancestor": ()})
    assert called == []


@pytest.mark.parametrize("field", ["source_output", "source_processed_output"])
def test_raw_saved_dependency_schema_forbids_all_runtime_handles(field):
    """Neither typed upstream handle may be smuggled through raw publication JSON."""
    saved = core.serialize_evidence_package_output(_snapshot_output())
    saved["dependencies"][0][field] = None
    _resign(saved)
    with pytest.raises(ValueError):
        core.deserialize_evidence_package_output(saved)


@pytest.mark.parametrize("field", ["observation", "parameters", "provenance"])
def test_processed_decoder_rejects_python_only_and_nested_nonfinite_json(field):
    """Saved values must be actual finite JSON throughout data and audit metadata."""
    raw = _raw()
    saved = core.serialize_evidence_processed_output(_processed(raw))
    if field == "parameters":
        saved[field] = {"nested": [float("nan")]}
    else:
        saved["outputs"][0][field] = {"nested": [object()]}
    with pytest.raises((ValueError, TypeError)):
        core.deserialize_evidence_processed_output(saved, raw_output=raw)


@pytest.mark.parametrize("boundary", ["construction", "readback"])
def test_processed_parameters_cannot_hide_nested_boolean_numeric_mismatch(boundary):
    """A typed processing identity must attest the exact callback-visible JSON values."""
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec

    raw = _raw()
    schema = ParameterSchema(raw.package_id, "nested-processing/1", (
        ParameterSpec("context", dict),
    ))
    processor = core.EvidenceOutputProcessor(
        "saved-process", "1", _process,
        {"context": {"nested": [{"x": 1}]}}, parameter_schema=schema,
    )
    processed = _package(processor).process_output(raw, package_freshness="fresh")
    assert processed.error_code is None
    changed = {"context": {"nested": [{"x": True}]}}
    assert json.dumps(changed, sort_keys=True) != json.dumps(
        schema.resolve(processor.parameters).to_json()["effective_parameters"],
        sort_keys=True,
    )
    with pytest.raises(ValueError, match="effective values must match parameters"):
        if boundary == "construction":
            replace(processed, parameters=changed)
        else:
            payload = core.serialize_evidence_processed_output(processed)
            payload["parameters"] = changed
            core.deserialize_evidence_processed_output(
                _resign(payload), raw_output=raw)


def test_processed_float_parameters_allow_declared_integer_normalization():
    """Scalar float compatibility uses the owner value contract rather than wire spelling."""
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec

    raw = _raw()
    schema = ParameterSchema(raw.package_id, "float-processing/1", (
        ParameterSpec("value", float, 1.0),
    ))
    processed = _package(core.EvidenceOutputProcessor(
        "saved-process", "1", _process, parameter_schema=schema,
    )).process_output(raw, package_freshness="fresh")
    payload = core.serialize_evidence_processed_output(processed)
    payload["parameters"]["value"] = 1
    restored = core.deserialize_evidence_processed_output(
        _resign(payload), raw_output=raw)
    assert restored.error_code is None
    assert type(restored.parameter_snapshot.effective_parameters["value"]) is float


def test_explicit_legacy_processed_warning_path_uses_saved_origin_parameters(tmp_path):
    """A located historical warning variant is adopted without changing its bytes."""
    from features import evidence_package_storage as storage
    from features.evidence_package_parameters import (
        ParameterImpact, ParameterSchema, ParameterSpec,
    )

    raw = _raw()
    saved = _package(core.EvidenceOutputProcessor(
        "saved-process", "1", _process, {"review_m": 0.01},
    )).process_output(raw, package_freshness="fresh")
    old_path = tmp_path / "explicit-historical-warning.json"
    storage.save_processed_output(old_path, saved)
    retained = old_path.read_bytes()
    payload = json.loads(retained)
    # Independently attest the original full-parameter identity, not today's recipe.
    original_identity = hashlib.sha256(json.dumps({
        "package_id": raw.package_id,
        "raw_output_identity": payload["raw_output_identity"],
        "raw_payload_fingerprint": payload["raw_payload_fingerprint"],
        "processor_id": payload["processor_id"],
        "processor_version": payload["processor_version"],
        "parameters": payload["parameters"],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert original_identity == saved.processing_identity
    schema = ParameterSchema(raw.package_id, "historical-warning/1", (
        ParameterSpec("review_m", float, 0.02, unit="m",
                      impact=ParameterImpact.REUSE_WITH_WARNING),
    ))

    def forbidden(*args, **kwargs):
        """Expose an accidental transform during receipt-only reconstruction."""
        pytest.fail("legacy processed lookup executed a transform")

    processor = core.EvidenceOutputProcessor(
        "saved-process", "1", forbidden, parameter_schema=schema,
    )
    assert storage.legacy_processed_cache_key(raw, processor) != original_identity
    lookup = storage.load_processed_entry(
        tmp_path / "typed-missing.json", raw_output=raw, processor=processor,
        legacy_path=old_path,
        legacy_processed_adopter=storage.reconstruct_legacy_processed_snapshot,
    )
    assert lookup is not None
    assert lookup.processed_output.outputs == saved.outputs
    assert json.dumps(
        lookup.processed_output.parameter_snapshot.to_json()["calculated_parameters"],
        sort_keys=True,
    ) == json.dumps({"review_m": 0.01}, sort_keys=True)
    assert lookup.parameter_status["requested_parameters"]["review_m"] == 0.02
    assert lookup.parameter_status["warnings"]
    assert lookup.parameter_status["exact_match"] is False
    assert lookup.reuse_origin["mode"] == "adopted_legacy"
    assert lookup.reuse_origin["origin_processing_identity"] == original_identity
    assert lookup.reuse_origin["origin_payload_fingerprint"] == payload["payload_fingerprint"]

    # The same historical bytes cannot authorize a computation-affecting change.
    calculation_schema = replace(schema, specs=(
        replace(schema.specs[0], impact=ParameterImpact.RECOMPUTE_REQUIRED),
    ))
    calculation_processor = core.EvidenceOutputProcessor(
        processor.function_id, processor.version, forbidden,
        parameter_schema=calculation_schema,
    )
    assert storage.load_processed_entry(
        tmp_path / "typed-missing.json", raw_output=raw,
        processor=calculation_processor, legacy_path=old_path,
        legacy_processed_adopter=storage.reconstruct_legacy_processed_snapshot,
    ) is None
    assert old_path.read_bytes() == retained
