"""Runtime-only processing keeps raw evidence publication intact."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from typing import Any

import pytest

import features.field_core as core
from features.field_core import (
    EvidenceChannelReference,
    EvidenceOutputChannel,
    EvidenceOutputScale,
    EvidencePackage,
    EvidencePackageChannelReference,
    EvidencePackageOutput,
    FieldResultStatus,
    serialize_evidence_package_output,
)
from features.free_space_evidence_package import build_free_space_evidence_package
from features.group_axis_potential_field import build_group_axis_potential_package
from features.group_distance_evidence_package import build_group_distance_evidence_package
from .test_evidence_package_output import _package_output_function, _source_envelope


def _raw() -> EvidencePackageOutput:
    """Build the existing contract publication without retained spatial fixtures."""
    return EvidencePackage("contract-package", "contract-output", "1", _package_output_function).evaluate(
        (_source_envelope(),)
    )


def _channel(raw: EvidencePackageOutput, **changes: Any) -> EvidenceOutputChannel:
    """Build one processed channel with a complete address into the supplied raw output."""
    source = raw.outputs[0]
    return replace(EvidenceOutputChannel(
        target=source.target,
        channel="processed",
        observation=0.25,
        status=FieldResultStatus.COMPUTED,
        scale=EvidenceOutputScale(meaning="contract processing"),
        derived_from=(EvidencePackageChannelReference(
            raw.package_id, raw.output_identity, source.target["identity"], source.channel
        ),),
    ), **changes)


def _process(raw: EvidencePackageOutput, parameters: Mapping[str, Any]) -> tuple[EvidenceOutputChannel, ...]:
    """Return one channel while making configured parameters observable."""
    return (_channel(raw, observation=parameters.get("value", 0.25)),)


def _package(processor: Any = None) -> EvidencePackage:
    """Keep the historical producer fixed while varying only optional processing."""
    return EvidencePackage(
        "contract-package", "contract-output", "1", _package_output_function,
        output_processor=processor,
    )


@pytest.mark.parametrize("freshness", ["fresh", "stale", "unavailable"])
def test_unconfigured_processing_is_explicit_and_has_no_raw_fallback(freshness: str) -> None:
    """A package without a processor must expose no processed observations."""
    package = EvidencePackage("contract-package", "contract-output", "1", _package_output_function)
    raw = package.evaluate((_source_envelope(),))

    result = package.process_output(raw, package_freshness=freshness)

    assert result.error_code == "OUTPUT_FUNCTION_NOT_CONFIGURED"
    assert result.outputs == ()
    assert result.explanation
    assert result.processor_id is None and result.processor_version is None
    assert result.parameters == {}
    assert result.raw_output_identity == raw.output_identity


def test_processing_reads_exact_raw_once_without_repeating_the_producer() -> None:
    """Optional processing calls only its configured callback and preserves raw bytes."""
    calls = {"producer": 0, "processor": 0}
    raw_seen = []

    def produce(sources: tuple) -> tuple[EvidenceOutputChannel, ...]:
        """Count publication calls so processing cannot silently recompute evidence."""
        calls["producer"] += 1
        return _package_output_function(sources)

    def process(raw: EvidencePackageOutput, parameters: Mapping[str, Any]) -> tuple[EvidenceOutputChannel, ...]:
        """Record exact input identity and consume immutable configured parameters."""
        calls["processor"] += 1
        raw_seen.append(raw)
        return _process(raw, parameters)

    processor = core.EvidenceOutputProcessor("test-process", "1", process, {"value": 0.75})
    package = EvidencePackage("contract-package", "contract-output", "1", produce, output_processor=processor)
    raw = package.evaluate((_source_envelope(),))
    before = serialize_evidence_package_output(raw)
    result = package.process_output(raw, package_freshness="fresh")

    assert isinstance(result, core.EvidenceProcessedOutput)
    assert result.error_code is None
    assert result.outputs[0].observation == 0.75
    assert raw_seen == [raw] and raw_seen[0] is raw
    assert calls == {"producer": 1, "processor": 1}
    assert serialize_evidence_package_output(raw) == before
    assert result.raw_payload_fingerprint == before["payload_fingerprint"]
    assert result.raw_output_identity == before["output_identity"]
    assert result.processor_id == "test-process" and result.processor_version == "1"
    with pytest.raises(FrozenInstanceError):
        result.error_code = "changed"


@pytest.mark.parametrize("freshness", [None, "stale", "unavailable"])
def test_unconfirmed_source_skips_processing(freshness: str | None) -> None:
    """The default unavailable and explicit stale gates expose no processed value."""
    calls = []

    def process(raw: EvidencePackageOutput, parameters: Mapping[str, Any]) -> tuple:
        """Expose an incorrect callback call through both a call log and valid result."""
        calls.append(raw)
        return _process(raw, parameters)

    package = _package(core.EvidenceOutputProcessor("test-process", "1", process))
    arguments = {} if freshness is None else {"package_freshness": freshness}
    result = package.process_output(_raw(), **arguments)

    assert result.error_code == "OUTPUT_SOURCE_NOT_FRESH"
    assert result.outputs == () and result.explanation
    assert calls == []


@pytest.mark.parametrize("change", ["type", "package", "function", "version", "freshness"])
def test_invalid_processing_arguments_raise_before_callback(change: str) -> None:
    """A processor cannot accept another publication or an unknown freshness state."""
    calls = []

    def process(raw: EvidencePackageOutput, parameters: Mapping[str, Any]) -> tuple:
        """Record any callback that incorrectly runs before API validation."""
        calls.append(raw)
        return _process(raw, parameters)

    raw = _raw()
    if change == "type":
        raw = object()
    elif change == "package":
        raw = replace(raw, package_id="another-package")
    elif change == "function":
        raw = replace(raw, output_function="another-producer")
    elif change == "version":
        raw = replace(raw, output_function_version="2")
    package = _package(core.EvidenceOutputProcessor("test-process", "1", process))

    with pytest.raises((TypeError, ValueError)):
        package.process_output(raw, package_freshness="unknown" if change == "freshness" else "fresh")
    assert calls == []


@pytest.mark.parametrize("kind", [
    "exception", "none", "mapping", "text", "bytes", "empty", "untyped",
    "wrong-package", "wrong-output", "wrong-target", "wrong-channel", "envelope-ref",
    "duplicate", "nonfinite", "range", "generator-failure",
])
def test_callback_failure_and_invalid_channels_have_no_raw_fallback(kind: str) -> None:
    """Any invalid callback result becomes one explicit empty processing failure."""
    def process(raw: EvidencePackageOutput, _parameters: Mapping[str, Any]) -> Any:
        """Supply independently malformed callback results at the processing boundary."""
        if kind == "exception":
            raise RuntimeError("callback failed")
        if kind == "none":
            return None
        if kind == "mapping":
            return {"processed": _channel(raw)}
        if kind == "text":
            return "processed"
        if kind == "bytes":
            return b"processed"
        if kind == "empty":
            return ()
        if kind == "untyped":
            return (object(),)
        channel = _channel(raw)
        if kind.startswith("wrong-"):
            field = {"wrong-package": "package_id", "wrong-output": "output_identity",
                     "wrong-target": "target_identity", "wrong-channel": "channel"}[kind]
            return (replace(channel, derived_from=(replace(channel.derived_from[0], **{field: "missing"}),)),)
        if kind == "envelope-ref":
            return (replace(channel, derived_from=(EvidenceChannelReference.from_envelope(
                raw.source_envelopes[0], "source_a"
            ),)),)
        if kind == "duplicate":
            return (channel, channel)
        if kind == "nonfinite":
            return (replace(channel, observation={"nested": [float("nan")]}),)
        if kind == "range":
            return (replace(channel, observation=2, scale=EvidenceOutputScale(
                "bounded score", value_range=(0, 1), endpoint_meanings=("none", "all")
            )),)

        def broken_generator() -> Any:
            """Fail during iteration after yielding a channel that must be discarded."""
            yield channel
            raise RuntimeError("iteration failed")

        return broken_generator()

    result = _package(core.EvidenceOutputProcessor("test-process", "1", process)).process_output(
        _raw(), package_freshness="fresh"
    )

    assert result.error_code == "OUTPUT_PROCESSING_FAILED"
    assert result.outputs == () and result.explanation


@pytest.mark.parametrize("source_status,source_value,output_status,output_value,accepted", [
    (FieldResultStatus.COMPUTED, None, FieldResultStatus.COMPUTED, 0, False),
    (FieldResultStatus.PARTIAL, 1, FieldResultStatus.COMPUTED, 0, False),
    (FieldResultStatus.PARTIAL, 1, FieldResultStatus.PARTIAL, 0, True),
    (FieldResultStatus.PARTIAL, None, FieldResultStatus.PARTIAL, 0, False),
    (FieldResultStatus.NOT_AVAILABLE, None, FieldResultStatus.PARTIAL, 0, False),
    (FieldResultStatus.INVALID, 1, FieldResultStatus.PARTIAL, 0, False),
    (FieldResultStatus.OUTSIDE, 1, FieldResultStatus.PARTIAL, 0, False),
    (FieldResultStatus.AMBIGUOUS, 1, FieldResultStatus.PARTIAL, 0, False),
    (FieldResultStatus.NOT_EVALUATED, 1, FieldResultStatus.PARTIAL, 0, False),
    (FieldResultStatus.NOT_AVAILABLE, None, FieldResultStatus.NOT_AVAILABLE, None, True),
    (FieldResultStatus.PARTIAL, 1, FieldResultStatus.COMPUTED, None, False),
    (FieldResultStatus.PARTIAL, 1, FieldResultStatus.AMBIGUOUS, 0, False),
    (FieldResultStatus.COMPUTED, 1, FieldResultStatus.INVALID, 0, False),
])
def test_processing_preserves_missing_and_partial_source_limits(
    source_status: FieldResultStatus, source_value: Any, output_status: FieldResultStatus,
    output_value: Any, accepted: bool,
) -> None:
    """A processor cannot invent missing observations or promote partial source status."""
    raw = _raw()
    raw = replace(raw, outputs=(replace(raw.outputs[0], observation=source_value,
                                      status=source_status, explanation="source status reason"),))

    def process(source: EvidencePackageOutput, _parameters: Mapping[str, Any]) -> tuple:
        """Return the requested status/value pair against the actual limited source."""
        return (_channel(source, observation=output_value, status=output_status,
                         explanation="processing status reason"),)

    result = _package(core.EvidenceOutputProcessor("test-process", "1", process)).process_output(
        raw, package_freshness="fresh"
    )

    assert result.error_code == (None if accepted else "OUTPUT_PROCESSING_FAILED")
    assert tuple(item.observation for item in result.outputs) == ((output_value,) if accepted else ())


def test_declared_scalar_ranges_allow_units_outside_the_unit_interval() -> None:
    """Optional processing respects its declared physical range without normalizing."""
    def process(raw: EvidencePackageOutput, _parameters: Mapping[str, Any]) -> tuple:
        """Publish a bounded distance rather than a normalized support score."""
        return (_channel(raw, observation=25, scale=EvidenceOutputScale(
            "distance", units="m", value_range=(0, 100), endpoint_meanings=("origin", "limit")
        )),)

    result = _package(core.EvidenceOutputProcessor("distance", "1", process)).process_output(
        _raw(), package_freshness="fresh"
    )

    assert result.error_code is None and result.outputs[0].observation == 25


def test_packages_can_choose_different_callbacks_for_the_same_raw_publication() -> None:
    """Package-local processors produce distinct channels without changing raw computation."""
    def alternative(raw: EvidencePackageOutput, _parameters: Mapping[str, Any]) -> tuple:
        """Use a different explicitly configured operation and channel."""
        return (_channel(raw, channel="alternative", observation=0.9),)

    raw = _raw()
    first = _package(core.EvidenceOutputProcessor("first", "1", _process)).process_output(raw, package_freshness="fresh")
    second = _package(core.EvidenceOutputProcessor("second", "1", alternative)).process_output(raw, package_freshness="fresh")

    assert (first.outputs[0].channel, first.outputs[0].observation) == ("processed", 0.25)
    assert (second.outputs[0].channel, second.outputs[0].observation) == ("alternative", 0.9)
    assert first.processing_identity != second.processing_identity
    assert first.raw_output_identity == second.raw_output_identity == raw.output_identity


def test_processing_resolves_same_channel_name_at_distinct_raw_targets() -> None:
    """A full target/channel address keeps different raw targets from being conflated."""
    raw = _raw()
    second_target = {"kind": "contract_target", "id": "target-2", "identity": "target-2"}
    raw = replace(raw, outputs=(replace(raw.outputs[0], observation=1),
                               replace(raw.outputs[0], target=second_target, observation=None)))

    def process(source: EvidencePackageOutput, _parameters: Mapping[str, Any]) -> tuple:
        """Cite the second target that has no observation despite the first being usable."""
        reference = EvidencePackageChannelReference(source.package_id, source.output_identity,
                                                    "target-2", source.outputs[0].channel)
        return (_channel(source, derived_from=(reference,)),)

    result = _package(core.EvidenceOutputProcessor("test-process", "1", process)).process_output(
        raw, package_freshness="fresh"
    )

    assert result.error_code == "OUTPUT_PROCESSING_FAILED" and result.outputs == ()


def test_processor_parameters_are_frozen_and_recipe_changes_processing_identity_only() -> None:
    """Nested caller mutation cannot change the processor recipe or raw publication."""
    parameters = {"value": 0.5, "details": {"items": [1, 2]}}
    processor = core.EvidenceOutputProcessor(" test-process ", " 1 ", _process, parameters)
    parameters["details"]["items"].append(3)
    parameters["value"] = 0.9
    with pytest.raises(TypeError):
        processor.parameters["details"]["items"][0] = 4
    with pytest.raises(TypeError):
        processor.parameters["value"] = 0.7
    with pytest.raises(FrozenInstanceError):
        processor.version = "2"
    assert processor.parameters["details"]["items"] == (1, 2)
    assert processor.function_id == "test-process" and processor.version == "1"
    raw = _raw()
    result = _package(processor).process_output(raw, package_freshness="fresh")
    variants = (
        replace(processor, function_id="other-process"),
        replace(processor, version="2"),
        replace(processor, parameters={"value": 0.75}),
    )
    results = [result] + [_package(item).process_output(raw, package_freshness="fresh") for item in variants]

    assert len({item.processing_identity for item in results}) == 4
    assert result.parameters is processor.parameters or result.parameters == processor.parameters
    assert {item.raw_output_identity for item in results} == {raw.output_identity}
    assert serialize_evidence_package_output(_package(processor).evaluate(raw.source_envelopes)) == serialize_evidence_package_output(raw)
    assert result.outputs[0].observation == 0.5


def test_typed_processor_sources_identity_and_roundtrip() -> None:
    """Receipts keep source labels while computation identity excludes them."""
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec

    schema = ParameterSchema("contract-package", "processor-parameters/1", (
        ParameterSpec("value", float, 0.25, minimum=0.0, maximum=1.0),))
    first_processor = core.EvidenceOutputProcessor(
        "typed-process", "1", _process, parameter_schema=schema)
    cli_processor = core.EvidenceOutputProcessor(
        "typed-process", "1", _process, {"value": 0.25},
        parameter_schema=schema, parameter_sources={"value": "cli"})
    raw = _raw()
    first = _package(first_processor).process_output(raw, package_freshness="fresh")
    cli = _package(cli_processor).process_output(raw, package_freshness="fresh")
    assert first.processing_identity == cli.processing_identity
    assert first.parameter_snapshot.parameter_sources != cli.parameter_snapshot.parameter_sources
    saved = core.serialize_evidence_processed_output(cli)
    restored = core.deserialize_evidence_processed_output(
        json.loads(json.dumps(saved)), raw_output=raw)
    assert restored == cli
    assert restored.parameter_snapshot.calculated_parameters["value"] == 0.25


def test_processed_cache_key_matches_identity_without_invoking_callback() -> None:
    """The storage key shares the receipt projection and never executes processing."""
    from features.evidence_package_storage import processed_cache_key

    def forbidden(raw: EvidencePackageOutput, parameters: Mapping[str, Any]) -> tuple:
        """Fail if key calculation accidentally calls the processor callback."""
        raise AssertionError("processed_cache_key invoked the callback")

    raw = _raw()
    processor = core.EvidenceOutputProcessor("typed-process", "1", forbidden, {"value": 0.25})
    result = _package(processor).process_output(raw, package_freshness="stale")
    assert processed_cache_key(raw, processor) == result.processing_identity


def test_processing_identity_binds_full_raw_readings_and_audit_content() -> None:
    """Equal calculation identities cannot hide changed raw values or provenance."""
    raw = _raw()
    processor = core.EvidenceOutputProcessor("test-process", "1", _process)
    revised = replace(raw, outputs=(replace(raw.outputs[0], observation={"derived": "changed"}),))
    audited = replace(raw, outputs=(replace(raw.outputs[0], provenance={"audit": "changed"}),))
    results = [_package(processor).process_output(item, package_freshness="fresh") for item in (raw, revised, audited)]

    assert len({item.raw_output_identity for item in results}) == 1
    assert len({item.raw_payload_fingerprint for item in results}) == 3
    assert len({item.processing_identity for item in results}) == 3
    payload = serialize_evidence_package_output(raw)
    fingerprint = payload.pop("payload_fingerprint")
    assert fingerprint == hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


@pytest.mark.parametrize("arguments", [
    ("", "1", _process, {}), ("process", "", _process, {}),
    ("process", "1", None, {}), ("process", "1", _process, []),
    ("process", "1", _process, {"nested": [float("inf")]}),
    ("process", "1", _process, {1: "invalid key"}),
    ("process", "1", _process, {"object": object()}),
])
def test_invalid_processor_configuration_is_rejected(arguments: tuple) -> None:
    """Only named, callable processors with immutable JSON-safe mappings are admitted."""
    with pytest.raises((TypeError, ValueError)):
        core.EvidenceOutputProcessor(*arguments)


def test_legacy_context_callback_and_positional_construction_remain_compatible() -> None:
    """Adding the optional port preserves both old constructor call shapes."""
    def context_output(context: Any) -> tuple:
        """Use the legacy context callback without opting into processing."""
        return _package_output_function(context.source_envelopes)

    package = EvidencePackage("contract-package", "contract-output", "1", None, context_output)
    assert serialize_evidence_package_output(package.evaluate((_source_envelope(),))) == serialize_evidence_package_output(_raw())
    with pytest.raises(TypeError):
        EvidencePackage("contract-package", "contract-output", "1", None, context_output, None)
    with pytest.raises(TypeError):
        _package(object())


@pytest.mark.parametrize("factory,options", [
    (build_free_space_evidence_package, {}),
    (build_group_distance_evidence_package, {}),
    (build_group_axis_potential_package, {}),
    (build_group_axis_potential_package, {"scene_namespace": "contract-scene"}),
])
def test_factories_forward_optional_configuration_and_default_to_disabled(factory: Any, options: dict) -> None:
    """Each factory and potential branch reaches the same runtime processing port."""
    processor = core.EvidenceOutputProcessor("test-process", "1", _process)
    default = factory(**options)
    configured = factory(**options, output_processor=processor)
    raw = replace(_raw(), package_id=default.package_id, output_function=default.output_function_id,
                  output_function_version=default.output_function_version)

    assert default.process_output(raw, package_freshness="fresh").error_code == "OUTPUT_FUNCTION_NOT_CONFIGURED"
    result = configured.process_output(raw, package_freshness="fresh")
    assert result.error_code is None and result.outputs[0].observation == 0.25
    assert configured.output_processor is processor
    assert default.output_function_id == configured.output_function_id
    assert default.output_function_version == configured.output_function_version
    assert serialize_evidence_package_output(raw)["output_identity"] == raw.output_identity
