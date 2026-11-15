"""Saved processed consumption requires independent current raw and recipe context."""

from dataclasses import replace
import hashlib
import json

import pytest

import features.field_core as core
from features.evidence_package_storage import processed_cache_key
from features.field_core import (
    EvidenceOutputProcessor, EvidencePackage, EvidencePackageChannelReference,
    FieldResultStatus, serialize_evidence_package_output, serialize_evidence_processed_output,
)
from scripts.design.group_level import replay_evidence_package_readback as adapter
from .test_evidence_package_freshness import _contract
from .test_evidence_package_readback import _saved


def _save(path, payload):
    """Write real serialized records and separately pin their exact transport bytes."""
    data = json.dumps(payload, allow_nan=False).encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _saved_processed(tmp_path):
    """Materialize two same-channel targets through the real processed publication API."""
    path, digest, raw = _saved(tmp_path, statuses=(FieldResultStatus.COMPUTED, FieldResultStatus.PARTIAL))

    def process(source, parameters):
        """Publish literal transformed observations while preserving each raw channel's limits."""
        return tuple(replace(channel, observation=value, derived_from=(EvidencePackageChannelReference(
            source.package_id, source.output_identity, channel.target["identity"], channel.channel),))
            for channel, value in zip(source.outputs, (0.25, 0.75)))

    processor = EvidenceOutputProcessor("saved-consumer-trial", "1", process, {"scope": "two-targets"})
    package = EvidencePackage(raw.package_id, raw.output_function, raw.output_function_version,
                              process, output_processor=processor)
    processed = package.process_output(raw, package_freshness="fresh")
    assert processed.error_code is None
    processed_path = tmp_path / "processed.json"
    processed_digest = _save(processed_path, serialize_evidence_processed_output(processed))
    contract = _contract(package_id=raw.package_id, target_ids=("target-0", "target-1"))
    arguments = dict(
        expected_sha256=digest, cached_contract=contract, current_contract=contract,
        current_source_envelopes=raw.source_envelopes, selections=(),
        dependency_graph={adapter.PACKAGE_ID: (raw.package_id,), raw.package_id: ()},
        processed_path=processed_path, expected_processed_sha256=processed_digest,
        # Derive the expected recipe from independently configured metadata, never saved JSON.
        current_processing_identity=processed_cache_key(raw, processor),
        processed_selections=(("target-0", "path_distance", "proximity"),
                              ("target-1", "path_distance", "proximity")),
    )
    return path, raw, processed, arguments


def test_saved_processed_channels_preserve_two_targets_and_complete_metadata(tmp_path):
    """Dropping a same-named target or replacing its scale/lineage breaks faithful readback."""
    path, raw, processed, arguments = _saved_processed(tmp_path)
    original_bytes = path.read_bytes(), arguments["processed_path"].read_bytes()
    result = adapter.consume_saved_evidence_package(path, **arguments)
    assert [(channel.target["identity"], channel.channel, channel.observation, channel.status.value)
            for channel in result.outputs] == [
        ("target-0", "proximity", 0.25, "computed"),
        ("target-1", "proximity", 0.75, "partial"),
    ]
    assert result.source_envelopes == raw.source_envelopes
    for actual, saved in zip(result.outputs, processed.outputs):
        assert (actual.scale, actual.source_ids, actual.provenance, actual.explanation) == (
            saved.scale, saved.source_ids, saved.provenance, saved.explanation)
        reference = actual.derived_from[0]
        assert (reference.port, reference.processing_identity, reference.channel) == (
            "processed", processed.processing_identity, "path_distance")
    assert original_bytes == (path.read_bytes(), arguments["processed_path"].read_bytes())


def test_saved_processed_consumer_binds_complete_raw_payload_once(tmp_path, monkeypatch):
    """Many exact processed selections reuse one validated raw binding."""
    path, raw, processed, arguments = _saved_processed(tmp_path)
    arguments["processed_selections"] = (
        ("target-0", "path_distance", "proximity-0"),
        ("target-1", "path_distance", "proximity-1"),
    )
    calls = 0
    serialize = core.serialize_evidence_package_output
    binding_calls = 0
    validate_binding = core._validate_processed_binding

    def counted_serialize(output):
        """Count complete raw publication serializations at the shared validation boundary."""
        nonlocal calls
        calls += 1
        return serialize(output)

    def counted_binding(processed_output, raw_output):
        """Count complete processed/raw binding validations during package consumption."""
        nonlocal binding_calls
        binding_calls += 1
        return validate_binding(processed_output, raw_output)

    monkeypatch.setattr(core, "serialize_evidence_package_output", counted_serialize)
    monkeypatch.setattr(core, "_validate_processed_binding", counted_binding)
    result = adapter.consume_saved_evidence_package(path, **arguments)

    assert calls == 2
    # One validation belongs to saved processed decoding; the second is the single
    # dependency-level runtime binding shared by both exact requested addresses.
    assert binding_calls == 2
    assert [(item.channel, item.observation) for item in result.outputs] == [
        ("proximity-0", 0.25),
        ("proximity-1", 0.75),
    ]


def test_mixed_ports_keep_same_address_with_explicit_output_alias(tmp_path):
    """The raw and processed readings must both survive when their saved addresses coincide."""
    path, _, _, arguments = _saved_processed(tmp_path)
    arguments.update(selections=(("target-0", "path_distance"),),
                     processed_selections=(("target-0", "path_distance", "proximity"),))
    result = adapter.consume_saved_evidence_package(path, **arguments)
    assert [(item.channel, item.observation, item.derived_from[0].port) for item in result.outputs] == [
        ("path_distance", 2.5, "raw"), ("proximity", 0.25, "processed")]


@pytest.mark.parametrize("identity,reason", [(None, "current_processing_identity_missing"),
                                             ("changed-current-recipe", "processing_recipe_changed")])
def test_current_recipe_missing_or_changed_redacts_only_processed_port(tmp_path, identity, reason):
    """Equal raw contracts cannot authorize an absent or obsolete current processing recipe."""
    path, _, _, arguments = _saved_processed(tmp_path)
    arguments.update(current_processing_identity=identity, selections=(("target-0", "path_distance"),),
                     processed_selections=(("target-0", "path_distance", "proximity"),))
    result = adapter.consume_saved_evidence_package(path, **arguments)
    raw, processed = result.outputs
    assert raw.observation == 2.5 and raw.status is FieldResultStatus.COMPUTED
    assert processed.observation is None and processed.status is FieldResultStatus.NOT_AVAILABLE
    assert reason in processed.explanation


@pytest.mark.parametrize("context", ["stale-contract", "missing-contract", "missing-sources"])
def test_processed_saved_fresh_receipt_cannot_override_current_raw_freshness(tmp_path, context):
    """A valid processed file remains unusable whenever independent raw freshness is absent."""
    path, raw, _, arguments = _saved_processed(tmp_path)
    if context == "stale-contract":
        arguments["current_contract"] = _contract(package_id=raw.package_id,
            target_ids=("target-0", "target-1"), changes={"query": {"scope": "other"}})
    elif context == "missing-contract":
        arguments["current_contract"] = None
    else:
        arguments["current_source_envelopes"] = None
    result = adapter.consume_saved_evidence_package(path, **arguments)
    assert all(item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE
               for item in result.outputs)


def test_changed_current_sources_reject_equal_raw_contracts_for_processed_use(tmp_path):
    """A caller cannot bind saved processed data to another reading with the same cache identity."""
    path, raw, _, arguments = _saved_processed(tmp_path)
    source = raw.source_envelopes[0]
    arguments["current_source_envelopes"] = (replace(source, source_ids=("changed-current-source",)),)
    with pytest.raises(ValueError, match="source context"):
        adapter.consume_saved_evidence_package(path, **arguments)


@pytest.mark.parametrize("artifact", ["raw", "processed"])
def test_saved_consumer_checks_each_separately_pinned_artifact_before_decode(tmp_path, artifact):
    """Tampering either transport must fail even though the other exact file remains intact."""
    path, _, _, arguments = _saved_processed(tmp_path)
    target = path if artifact == "raw" else arguments["processed_path"]
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SHA-256"):
        adapter.consume_saved_evidence_package(path, **arguments)


@pytest.mark.parametrize("artifact", ["raw-content", "processed-content"])
def test_updated_file_sha_cannot_hide_wrong_content_binding(tmp_path, artifact):
    """Transport authorization cannot bypass processed raw binding or the content fingerprint."""
    path, raw, processed, arguments = _saved_processed(tmp_path)
    if artifact == "raw-content":
        changed = replace(raw, outputs=(replace(raw.outputs[0], observation=9), *raw.outputs[1:]))
        arguments["expected_sha256"] = _save(path, serialize_evidence_package_output(changed))
    else:
        payload = serialize_evidence_processed_output(processed)
        payload["outputs"][0]["observation"] = 0.9
        arguments["expected_processed_sha256"] = _save(arguments["processed_path"], payload)
    with pytest.raises(ValueError, match="fingerprint|raw"):
        adapter.consume_saved_evidence_package(path, **arguments)


@pytest.mark.parametrize("selection", [(("absent", "path_distance", "proximity"),),
                                         (("target-0", "absent", "proximity"),)])
def test_unknown_processed_address_never_falls_back_to_raw(tmp_path, selection):
    """Missing processed targets/channels cannot become a raw or first-match result."""
    path, _, _, arguments = _saved_processed(tmp_path)
    arguments["processed_selections"] = selection
    with pytest.raises(ValueError, match="channel|target|reference"):
        adapter.consume_saved_evidence_package(path, **arguments)


def test_mixed_output_alias_collision_fails_instead_of_dropping_a_port(tmp_path):
    """Duplicate consumer addresses need a different explicit alias before numeric use."""
    path, _, _, arguments = _saved_processed(tmp_path)
    arguments.update(selections=(("target-0", "path_distance"),),
                     processed_selections=(("target-0", "path_distance", "path_distance"),))
    with pytest.raises(ValueError, match="alias|duplicate|distinct"):
        adapter.consume_saved_evidence_package(path, **arguments)


@pytest.mark.parametrize("missing", ["processed_path", "expected_processed_sha256"])
def test_processed_selection_requires_its_saved_file_and_external_hash(tmp_path, missing):
    """A processed selection cannot silently reuse only the valid raw artifact."""
    path, _, _, arguments = _saved_processed(tmp_path)
    arguments[missing] = None
    with pytest.raises(ValueError, match="processed|SHA-256"):
        adapter.consume_saved_evidence_package(path, **arguments)


def test_processed_consumption_preserves_explicit_graph_validation(tmp_path):
    """Processed bytes cannot bypass the upstream declaration and graph closure check."""
    path, _, _, arguments = _saved_processed(tmp_path)
    arguments["dependency_graph"] = {adapter.PACKAGE_ID: ()}
    with pytest.raises(ValueError, match="graph|depend"):
        adapter.consume_saved_evidence_package(path, **arguments)
