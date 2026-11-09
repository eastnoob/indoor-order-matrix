"""Tests for additive, traceable evidence-package output records."""

from __future__ import annotations

import json

import pytest

from features.field_core import (
    EvidenceChannelRecord,
    EvidenceChannelReference,
    EvidencePackageChannelReference,
    EvidencePackageDependency,
    EvidencePackageInput,
    EvidenceOutputChannel,
    EvidenceOutputScale,
    EvidencePackage,
    EvidencePackageOutput,
    FieldQuery,
    FieldResultEnvelope,
    FieldResultStatus,
    build_field_result_cache_identity,
    read_evidence_package_channel,
    resolve_evidence_package_channel,
    serialize_evidence_package_output,
    validate_evidence_package_dependency_graph,
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


def test_external_lineage_requires_declared_package_dependency_and_round_trips() -> None:
    """External channel lineage is admitted only through an explicit dependency."""
    evidence = _source_envelope()
    published = EvidencePackageOutput(
        package_id="upstream-package",
        output_function="upstream-output",
        output_function_version="1",
        source_envelopes=(evidence,),
        outputs=(EvidenceOutputChannel(
            target=evidence.target,
            channel="published_a",
            observation={"published": True},
            status=FieldResultStatus.COMPUTED,
            scale=EvidenceOutputScale(meaning="upstream contract output"),
            derived_from=(EvidenceChannelReference.from_envelope(evidence, "source_a"),),
        ),),
    )
    external = EvidencePackageChannelReference(
        package_id="upstream-package",
        output_identity=published.output_identity,
        target_identity="target-1",
        channel="published_a",
    )
    dependency = EvidencePackageDependency(
        package_id="upstream-package",
        output_identity=published.output_identity,
        channels=(external,),
        source_output=published,
        package_freshness="fresh",
    )
    output_channel = EvidenceOutputChannel(
        target=evidence.target,
        channel="derived_external",
        observation=1,
        status=FieldResultStatus.COMPUTED,
        scale=EvidenceOutputScale(meaning="external contract test"),
        derived_from=(external,),
    )

    with pytest.raises(ValueError, match="dependencies"):
        EvidencePackageOutput(
            package_id="contract-package",
            output_function="contract-output",
            output_function_version="1",
            source_envelopes=(evidence,),
            outputs=(output_channel,),
        )

    output = EvidencePackageOutput(
        package_id="contract-package",
        output_function="contract-output",
        output_function_version="1",
        source_envelopes=(evidence,),
        outputs=(output_channel,),
        dependencies=(dependency,),
    )
    serialized = serialize_evidence_package_output(output)
    assert serialized["dependencies"][0]["channels"][0]["package_id"] == "upstream-package"
    assert output.dependencies[0].source_output is None
    assert read_evidence_package_channel(published, external) is published.outputs[0]
    fresh_read = resolve_evidence_package_channel(published, external, package_freshness="fresh")
    assert fresh_read.channel is published.outputs[0]
    assert fresh_read.audit_channel is published.outputs[0]
    stale_read = resolve_evidence_package_channel(published, external, package_freshness="stale")
    assert stale_read.channel is None
    assert stale_read.audit_channel is not published.outputs[0]
    assert stale_read.audit_channel.status is published.outputs[0].status
    assert stale_read.audit_channel.channel == published.outputs[0].channel
    assert stale_read.audit_channel.observation is None
    assert stale_read.effective_status is FieldResultStatus.NOT_AVAILABLE
    unavailable_read = resolve_evidence_package_channel(
        published, external, package_freshness="unavailable"
    )
    assert unavailable_read.channel is None
    assert unavailable_read.audit_channel.observation is None
    assert unavailable_read.audit_channel.status is published.outputs[0].status
    assert unavailable_read.effective_status is FieldResultStatus.NOT_AVAILABLE
    assert output.output_identity != _output(evidence).output_identity


def test_dependency_and_reader_reject_identity_mismatches() -> None:
    """Dependency references and typed readers reject ambiguous package identities."""
    with pytest.raises(ValueError, match="same package_id"):
        EvidencePackageDependency(
            package_id="package-a",
            output_identity="output-a",
            channels=(
                EvidencePackageChannelReference("package-a", "output-a", "target", "a"),
                EvidencePackageChannelReference("package-b", "output-a", "target", "b"),
            ),
        )

    evidence = _source_envelope()
    output = _output(evidence)
    reference = EvidencePackageChannelReference("other-package", output.output_identity, "target-1", "derived_a")
    with pytest.raises(ValueError, match="package_id"):
        read_evidence_package_channel(output, reference)
    with pytest.raises(TypeError, match="EvidencePackageOutput"):
        read_evidence_package_channel(serialize_evidence_package_output(output), reference)


def test_package_evaluate_accepts_keyword_only_dependencies() -> None:
    """Package evaluation carries declared dependencies into the immutable output."""
    evidence = _source_envelope()
    external = EvidencePackageChannelReference("upstream", "upstream-output", "target-1", "published")
    dependency = EvidencePackageDependency("upstream", "upstream-output", (external,), package_freshness="unavailable")

    def produce(_sources: tuple[FieldResultEnvelope, ...]) -> tuple[EvidenceOutputChannel, ...]:
        """Produce an output that consumes one published external channel."""
        return (
            EvidenceOutputChannel(
                target=evidence.target,
                channel="derived_external",
                observation=None,
                status=FieldResultStatus.NOT_AVAILABLE,
                scale=EvidenceOutputScale(meaning="external contract test"),
                derived_from=(external,),
                explanation="upstream package output is unavailable",
            ),
        )

    package = EvidencePackage("contract-package", "contract-output", "1", produce)
    result = package.evaluate((evidence,), dependencies=(dependency,))
    assert result.dependencies == (dependency,)


def test_context_consumer_reads_fresh_channel_and_gates_stale_channel() -> None:
    """Context consumers receive observations while freshness controls usable status."""
    evidence = _source_envelope()
    upstream = EvidencePackageOutput(
        package_id="upstream",
        output_function="upstream-output",
        output_function_version="1",
        source_envelopes=(evidence,),
        outputs=(EvidenceOutputChannel(
            target=evidence.target,
            channel="published",
            observation={"score": 7},
            status=FieldResultStatus.PARTIAL,
            scale=EvidenceOutputScale(meaning="upstream score"),
            derived_from=(EvidenceChannelReference.from_envelope(evidence, "source_a"),),
            explanation="partial upstream evidence",
        ),),
    )
    reference = EvidencePackageChannelReference("upstream", upstream.output_identity, "target-1", "published")
    fresh_dependency = EvidencePackageDependency("upstream", upstream.output_identity, (reference,), upstream, "fresh")
    stale_dependency = EvidencePackageDependency("upstream", upstream.output_identity, (reference,), upstream, "stale")
    seen: list[EvidencePackageInput] = []

    def consume(context: EvidencePackageInput) -> tuple[EvidenceOutputChannel, ...]:
        """Read the resolved dependency context without changing source status semantics."""
        seen.append(context)
        resolved = context.resolved_dependencies[0]
        if resolved.package_freshness == "unavailable":
            assert resolved.channel is None
            assert resolved.audit_channel is None
            assert resolved.channel_status is None
        else:
            if resolved.package_freshness == "fresh":
                assert resolved.audit_channel is upstream.outputs[0]
            else:
                assert resolved.audit_channel is not upstream.outputs[0]
                assert resolved.audit_channel.observation is None
            assert resolved.channel_status is FieldResultStatus.PARTIAL
            assert resolved.channel is (upstream.outputs[0] if resolved.package_freshness == "fresh" else None)
        if resolved.package_freshness == "fresh":
            return (_output(evidence).outputs[0],)
        return (
            EvidenceOutputChannel(
                target=evidence.target,
                channel="derived_a",
                observation=None,
                status=FieldResultStatus.NOT_AVAILABLE,
                scale=EvidenceOutputScale(meaning="upstream package is not current"),
                derived_from=(reference,),
                explanation=resolved.explanation,
            ),
        )

    package = EvidencePackage("consumer", "consumer-output", "1", None, consume)
    result = package.evaluate((evidence,), dependencies=(fresh_dependency,))
    assert seen[0].resolved_dependencies[0].channel.observation == {"score": 7}
    assert seen[0].resolved_dependencies[0].effective_status is FieldResultStatus.PARTIAL
    stale = package.evaluate((evidence,), dependencies=(stale_dependency,))
    assert seen[1].resolved_dependencies[0].channel is None
    assert seen[1].resolved_dependencies[0].audit_channel.observation is None
    assert seen[1].resolved_dependencies[0].channel_status is FieldResultStatus.PARTIAL
    assert seen[1].resolved_dependencies[0].effective_status is FieldResultStatus.NOT_AVAILABLE
    serialized = serialize_evidence_package_output(stale)
    assert "source_output" not in json.dumps(serialized)
    assert result.dependencies[0].package_freshness == "fresh"
    assert result.output_identity != stale.output_identity
    unavailable_dependency = EvidencePackageDependency(
        "upstream", upstream.output_identity, (reference,), package_freshness="unavailable"
    )
    package.evaluate((evidence,), dependencies=(unavailable_dependency,))
    assert seen[2].resolved_dependencies[0].effective_status is FieldResultStatus.NOT_AVAILABLE


def test_dependency_graph_rejects_self_and_multi_node_cycles() -> None:
    """Dependency graph validation reports both direct and indirect cycles."""
    with pytest.raises(ValueError, match=r"a -> a"):
        validate_evidence_package_dependency_graph({"a": ("a",)})
    with pytest.raises(ValueError, match=r"a -> b -> c -> a"):
        validate_evidence_package_dependency_graph({"a": ("b",), "b": ("c",), "c": ("a",)})
    with pytest.raises(ValueError, match=r"a -> a"):
        validate_evidence_package_dependency_graph({"a": ("a ",)})


def test_package_output_rejects_direct_self_dependency() -> None:
    """A package cannot publish an output that depends on its own package id."""
    evidence = _source_envelope()
    reference = EvidencePackageChannelReference("contract-package", "prior-output", "target-1", "published")
    dependency = EvidencePackageDependency(
        "contract-package", "prior-output", (reference,), package_freshness="stale"
    )
    output_channel = EvidenceOutputChannel(
        target=evidence.target,
        channel="derived_external",
        observation=None,
        status=FieldResultStatus.NOT_AVAILABLE,
        scale=EvidenceOutputScale(meaning="self-dependency rejection"),
        derived_from=(reference,),
        explanation="The referenced prior package output is not current.",
    )

    with pytest.raises(ValueError, match="cannot depend on itself"):
        EvidencePackageOutput(
            package_id="contract-package",
            output_function="contract-output",
            output_function_version="1",
            source_envelopes=(evidence,),
            outputs=(output_channel,),
            dependencies=(dependency,),
        )


def test_package_output_rejects_computed_result_from_stale_dependency() -> None:
    """A stale external channel cannot be republished as a current computed value."""
    evidence = _source_envelope()
    upstream = _output(evidence)
    reference = EvidencePackageChannelReference(
        "contract-package", upstream.output_identity, "target-1", "derived_a"
    )
    dependency = EvidencePackageDependency(
        "contract-package", upstream.output_identity, (reference,), upstream, "stale"
    )
    output_channel = EvidenceOutputChannel(
        target=evidence.target,
        channel="derived_external",
        observation=1,
        status=FieldResultStatus.COMPUTED,
        scale=EvidenceOutputScale(meaning="invalid stale computation"),
        derived_from=(reference,),
    )

    with pytest.raises(ValueError, match="stale or unavailable"):
        EvidencePackageOutput(
            package_id="consumer",
            output_function="consumer-output",
            output_function_version="1",
            source_envelopes=(evidence,),
            outputs=(output_channel,),
            dependencies=(dependency,),
        )


def test_package_output_normalizes_id_before_self_dependency_check() -> None:
    """Whitespace normalization cannot bypass the direct self-dependency guard."""
    evidence = _source_envelope()
    reference = EvidencePackageChannelReference("consumer", "prior-output", "target-1", "published")
    dependency = EvidencePackageDependency("consumer", "prior-output", (reference,), package_freshness="stale")
    output_channel = EvidenceOutputChannel(
        target=evidence.target,
        channel="derived_external",
        observation=None,
        status=FieldResultStatus.NOT_AVAILABLE,
        scale=EvidenceOutputScale(meaning="self-dependency normalization"),
        derived_from=(reference,),
        explanation="The referenced package is not current.",
    )

    with pytest.raises(ValueError, match="cannot depend on itself"):
        EvidencePackageOutput(
            package_id="consumer ",
            output_function="consumer-output",
            output_function_version="1",
            source_envelopes=(evidence,),
            outputs=(output_channel,),
            dependencies=(dependency,),
        )


def test_package_output_rejects_duplicate_external_channel_declarations() -> None:
    """One published channel cannot be declared through multiple dependency records."""
    evidence = _source_envelope()
    upstream = _output(evidence)
    reference = EvidencePackageChannelReference(
        "contract-package", upstream.output_identity, "target-1", "derived_a"
    )
    output_channel = EvidenceOutputChannel(
        target=evidence.target,
        channel="derived_external",
        observation=None,
        status=FieldResultStatus.NOT_AVAILABLE,
        scale=EvidenceOutputScale(meaning="duplicate dependency rejection"),
        derived_from=(reference,),
        explanation="the upstream channel was declared twice",
    )
    dependencies = (
        EvidencePackageDependency(
            "contract-package", upstream.output_identity, (reference,), package_freshness="unavailable"
        ),
        EvidencePackageDependency(
            "contract-package", upstream.output_identity, (reference,), package_freshness="stale"
        ),
    )

    with pytest.raises(ValueError, match="redeclare the same external channel"):
        EvidencePackageOutput(
            package_id="consumer",
            output_function="consumer-output",
            output_function_version="1",
            source_envelopes=(evidence,),
            outputs=(output_channel,),
            dependencies=dependencies,
        )


def test_evaluate_validates_explicit_dependency_graph_before_callback() -> None:
    """Evaluation rejects normalized direct and indirect cycles before producing outputs."""
    evidence = _source_envelope()
    called = False

    def produce(_sources: tuple[FieldResultEnvelope, ...]) -> tuple[EvidenceOutputChannel, ...]:
        """Record callback execution and return a valid legacy output."""
        nonlocal called
        called = True
        return _output(evidence).outputs

    package = EvidencePackage("consumer", "consumer-output", "1", produce)
    with pytest.raises(ValueError, match=r"a -> b -> a"):
        package.evaluate(
            (evidence,),
            dependency_graph={" a ": (" b ",), "b": ("a",)},
        )
    assert called is False
