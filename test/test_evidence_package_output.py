"""Tests for additive, traceable evidence-package output records."""

from __future__ import annotations

import json

import pytest

from ..features.field_core import (
    EvidenceChannelRecord,
    EvidenceChannelReference,
    EvidenceOutputChannel,
    EvidenceOutputScale,
    EvidencePackage,
    EvidencePackageOutput,
    FieldQuery,
    FieldResultEnvelope,
    FieldResultStatus,
    build_field_result_cache_identity,
    serialize_evidence_package_output,
)


def _source_envelope(*, source_fingerprint: str = "source-1") -> FieldResultEnvelope:
    """Build contract-only evidence without creating spatial or IFC data."""
    query = FieldQuery(domain_id="contract-domain", revision="contract-r1")
    records = (
        EvidenceChannelRecord(
            "source_a",
            True,
            "descriptive",
            {"raw": "a"},
            source_ids=("source-a",),
            provenance={"algorithm_version": "contract-test/1", "schema_version": "contract-test/1"},
        ),
        EvidenceChannelRecord(
            "source_b",
            False,
            "descriptive",
            None,
            status=FieldResultStatus.NOT_AVAILABLE,
            source_ids=("source-b",),
            provenance={"algorithm_version": "contract-test/1", "schema_version": "contract-test/1"},
            explanation="source channel is unavailable",
        ),
    )
    target = {"kind": "contract_target", "id": "target-1", "identity": "target-1"}
    identity = build_field_result_cache_identity(
        target=target,
        query=query,
        channel_declarations=tuple({"channel": record.channel} for record in records),
        input_fingerprint="input-1",
        source_fingerprint=source_fingerprint,
        recipe_fingerprint="recipe-1",
        algorithm_version="contract-test/1",
        schema_version="contract-test/1",
    )
    return FieldResultEnvelope(
        target=target,
        query=query,
        raw_status=FieldResultStatus.PARTIAL,
        channel_set=("source_a", "source_b"),
        value={"channels": records},
        source_ids=("source-a", "source-b"),
        provenance={"algorithm_version": "contract-test/1", "schema_version": "contract-test/1"},
        cache_identity=identity,
        explanation="one admitted source channel is unavailable",
    )


def _output(
    evidence: FieldResultEnvelope,
    *,
    output_version: str = "1",
    channel: str = "derived_a",
    scale: EvidenceOutputScale | None = None,
) -> EvidencePackageOutput:
    """Build one output from declared source channels for contract checks."""
    return EvidencePackageOutput(
        package_id="contract-package",
        output_function="contract-output",
        output_function_version=output_version,
        source_envelopes=(evidence,),
        outputs=(
            EvidenceOutputChannel(
                target=evidence.target,
                channel=channel,
                observation={"derived": "value"},
                status=FieldResultStatus.COMPUTED,
                scale=scale or EvidenceOutputScale(
                    meaning="contract-only derived observation",
                    units="unitless",
                    normalization_method="identity",
                ),
                derived_from=(EvidenceChannelReference.from_envelope(evidence, "source_a"),),
                source_ids=("source-a",),
                provenance={"method": "contract-only"},
            ),
        ),
    )


def _package_output_function(
    source_envelopes: tuple[FieldResultEnvelope, ...],
) -> tuple[EvidenceOutputChannel, ...]:
    """Return one valid additive channel for the package-template test."""
    evidence = source_envelopes[0]
    return (
        EvidenceOutputChannel(
            target=evidence.target,
            channel="derived_a",
            observation={"derived": "value"},
            status=FieldResultStatus.COMPUTED,
            scale=EvidenceOutputScale(
                meaning="contract-only derived observation",
                units="unitless",
                normalization_method="identity",
            ),
            derived_from=(EvidenceChannelReference.from_envelope(evidence, "source_a"),),
            source_ids=("source-a",),
            provenance={"method": "contract-only"},
        ),
    )


def test_package_template_requires_callable_and_validates_output_shape() -> None:
    """The generic package template requires a callable and shared output contract."""
    evidence = _source_envelope()
    package = EvidencePackage(
        package_id="contract-package",
        output_function_id="contract-output",
        output_function_version="1",
        output_function=_package_output_function,
    )

    output = package.evaluate((evidence,))
    assert output.output_function == "contract-output"
    assert output.source_envelopes == (evidence,)
    assert output.source_envelopes[0].channel_set == ("source_a", "source_b")
    assert output.outputs[0].channel == "derived_a"

    with pytest.raises(TypeError, match="callable"):
        EvidencePackage(
            package_id="contract-package",
            output_function_id="contract-output",
            output_function_version="1",
            output_function=None,
        )

    with pytest.raises(TypeError, match="iterable"):
        EvidencePackage(
            package_id="contract-package",
            output_function_id="contract-output",
            output_function_version="1",
            output_function=lambda _sources: None,
        ).evaluate((evidence,))

    with pytest.raises(ValueError, match="EvidenceOutputChannel"):
        EvidencePackage(
            package_id="contract-package",
            output_function_id="contract-output",
            output_function_version="1",
            output_function=lambda _sources: (object(),),
        ).evaluate((evidence,))


def test_package_template_rejects_function_output_that_breaks_lineage() -> None:
    """The template routes malformed function output through the shared validator."""
    evidence = _source_envelope()

    def malformed_output(_sources: tuple[FieldResultEnvelope, ...]) -> tuple[EvidenceOutputChannel, ...]:
        """Return a channel that cites a source not admitted by the envelope."""
        return (
            EvidenceOutputChannel(
                target=evidence.target,
                channel="derived_a",
                observation=1,
                status=FieldResultStatus.COMPUTED,
                scale=EvidenceOutputScale(meaning="contract test"),
                derived_from=(EvidenceChannelReference("missing-result", "target-1", "source_a"),),
            ),
        )

    package = EvidencePackage(
        package_id="contract-package",
        output_function_id="malformed-output",
        output_function_version="1",
        output_function=malformed_output,
    )
    with pytest.raises(ValueError, match="lineage"):
        package.evaluate((evidence,))


def test_output_keeps_every_source_channel_and_serializes_the_additive_result() -> None:
    """Package output serialization retains the original envelope unchanged."""
    evidence = _source_envelope()
    output = _output(evidence)

    assert output.source_envelopes == (evidence,)
    assert output.source_envelopes[0] is evidence
    assert output.source_envelopes[0].channel_set == ("source_a", "source_b")
    assert [record.channel for record in output.source_envelopes[0].value["channels"]] == [
        "source_a",
        "source_b",
    ]
    assert output.source_envelopes[0].value["channels"][1].status is FieldResultStatus.NOT_AVAILABLE
    assert output.source_envelopes[0].value["channels"][1].source_ids == ("source-b",)
    assert output.outputs[0].derived_from == (
        EvidenceChannelReference.from_envelope(evidence, "source_a"),
    )

    serialized = serialize_evidence_package_output(output)
    round_tripped = json.loads(json.dumps(serialized, sort_keys=True))
    assert [record["channel"] for record in round_tripped["source_envelopes"][0]["value"]["channels"]] == [
        "source_a",
        "source_b",
    ]
    assert round_tripped["source_envelopes"][0]["raw_status"] == "partial"
    assert round_tripped["source_envelopes"][0]["value"]["channels"][1]["status"] == "not_available"
    assert round_tripped["source_envelopes"][0]["value"]["channels"][1]["source_ids"] == ["source-b"]
    assert round_tripped["outputs"][0]["channel"] == "derived_a"
    assert round_tripped["outputs"][0]["derived_from"][0]["channel"] == "source_a"
    assert round_tripped["output_identity"] == output.output_identity


def test_output_identity_tracks_function_version_and_scale_contract() -> None:
    """Changing output rules or declared scale produces a distinct cache identity."""
    evidence = _source_envelope()
    first = _output(evidence)
    revised_function = _output(evidence, output_version="2")
    revised_source = _output(_source_envelope(source_fingerprint="source-2"))
    revised_scale = _output(
        evidence,
        scale=EvidenceOutputScale(
            meaning="contract-only derived observation",
            scale_id="reviewed-scale-x",
            units="unitless",
            normalization_method="identity",
        ),
    )

    assert first.output_identity != revised_function.output_identity
    assert first.output_identity != revised_source.output_identity
    assert first.output_identity != revised_scale.output_identity


def test_output_rejects_unknown_or_replacement_source_channels() -> None:
    """Derived outputs must reference admitted evidence and cannot overwrite it."""
    evidence = _source_envelope()
    unknown_reference = EvidenceOutputChannel(
        target=evidence.target,
        channel="derived_a",
        observation=1,
        status=FieldResultStatus.COMPUTED,
        scale=EvidenceOutputScale(meaning="contract test"),
        derived_from=(EvidenceChannelReference("missing-result", "target-1", "source_a"),),
    )
    with pytest.raises(ValueError, match="lineage"):
        EvidencePackageOutput(
            package_id="contract-package",
            output_function="contract-output",
            output_function_version="1",
            source_envelopes=(evidence,),
            outputs=(unknown_reference,),
        )

    with pytest.raises(ValueError, match="must not replace"):
        _output(evidence, channel="source_a")


def test_bounded_output_scale_requires_explicit_endpoint_meanings() -> None:
    """A numeric range alone cannot claim semantic comparability."""
    with pytest.raises(ValueError, match="endpoint_meanings"):
        EvidenceOutputScale(meaning="bounded contract test", value_range=(0.0, 1.0))

    scale = EvidenceOutputScale(
        meaning="bounded contract test",
        value_range=(0.0, 1.0),
        endpoint_meanings=("lower meaning", "upper meaning"),
    )
    assert scale.value_range == (0.0, 1.0)
