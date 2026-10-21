"""Contract tests for the planned immutable Field kernel."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import pytest

from features.field_core import (
    EvidenceChannelRecord,
    Field,
    FieldQuery,
    FieldResultEnvelope,
    FieldResultStatus,
    FieldSample,
    FieldStatus,
    build_field_result_cache_identity,
    project_field_sample,
)


ALGORITHM_VERSION = "dict-field-test/1"
SCHEMA_VERSION = "field-core-test/1"


def _query(
    *,
    domain_id: str | None = "room-a",
    frame: str | None = "world-xy",
    revision: str = "query-r1",
    tolerance: float = 0.01,
    **extra: Any,
) -> FieldQuery:
    """Build a query with stable audit metadata for focused contract tests."""
    return FieldQuery(
        domain_id=domain_id,
        frame=frame,
        plane=extra.pop("plane", None),
        height_band=extra.pop("height_band", None),
        demand=extra.pop("demand", None),
        tolerance=tolerance,
        revision=revision,
        **extra,
    )


def _provenance(**extra: Any) -> dict[str, Any]:
    """Build the minimum provenance envelope required by every sample."""
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "schema_version": SCHEMA_VERSION,
        **extra,
    }


class DictField(Field[str | tuple[str, str], float]):
    """Small relation/spatial-neutral field used only to exercise the contract."""

    def __init__(
        self,
        values: dict[str | tuple[str, str], float | None],
        *,
        domain: Iterable[str] | None = ("a", "b", "c"),
        channel_available: bool = True,
    ) -> None:
        """Store exact values and explicit domain/channel availability."""
        self.values = values
        self.domain = None if domain is None else frozenset(domain)
        self.frame = "world-xy"
        self.value_schema = "scalar"
        self.representation = "dict"
        self.provenance = MappingProxyType(_provenance())
        self.channel_available = channel_available

    def evaluate(
        self,
        target: str | tuple[str, str],
        query: FieldQuery,
    ) -> FieldSample[float]:
        """Return one status-bearing sample without coercing relation targets."""
        if not isinstance(target, (str, tuple)):
            return FieldSample(
                value=None,
                status=FieldStatus.INVALID,
                query=query,
                source_ids=(),
                provenance=_provenance(),
                explanation="target must be a string or relation tuple",
            )
        if not self.channel_available or self.domain is None or query.domain_id is None:
            return FieldSample(
                value=None,
                status=FieldStatus.NOT_AVAILABLE,
                query=query,
                source_ids=(),
                provenance=_provenance(),
                explanation="requested channel or domain is unavailable",
            )
        if isinstance(target, str) and target not in self.domain:
            return FieldSample(
                value=None,
                status=FieldStatus.OUTSIDE,
                query=query,
                source_ids=(),
                provenance=_provenance(),
                explanation="target is outside the available domain",
            )
        if target not in self.values or self.values[target] is None:
            return FieldSample(
                value=None,
                status=FieldStatus.UNKNOWN,
                query=query,
                source_ids=("evidence-missing",),
                provenance=_provenance(),
                explanation="evidence is insufficient",
            )
        status = (
            FieldStatus.CONDITIONAL
            if query.plane is not None or query.height_band is not None
            else FieldStatus.ESTABLISHED
        )
        return FieldSample(
            value=self.values[target],
            status=status,
            query=query,
            support={"count": 1, "units": "sample"},
            source_ids=(str(target),),
            provenance=_provenance(
                query_revision=query.revision,
                units="scalar",
                tolerance=query.tolerance,
            ),
            explanation=(
                "value is limited to the declared section scope"
                if status is FieldStatus.CONDITIONAL
                else "complete declared lookup"
            ),
        )


def test_field_status_exposes_exact_unordered_six_state_vocabulary() -> None:
    """The enum contains exactly the six frozen status names and string values."""
    assert {status.value for status in FieldStatus} == {
        "established",
        "conditional",
        "unknown",
        "outside",
        "invalid",
        "not_available",
    }
    assert all(isinstance(status, str) for status in FieldStatus)


def test_field_sample_enforces_value_availability_by_status() -> None:
    """Missingness states reject values while qualified states require values."""
    query = _query()
    for status in (
        FieldStatus.INVALID,
        FieldStatus.NOT_AVAILABLE,
        FieldStatus.OUTSIDE,
        FieldStatus.UNKNOWN,
    ):
        sample = FieldSample(
            value=None,
            status=status,
            query=query,
            provenance=_provenance(),
        )
        assert sample.value is None
        with pytest.raises((TypeError, ValueError)):
            FieldSample(
                value=0.0,
                status=status,
                query=query,
                provenance=_provenance(),
            )
    for status in (FieldStatus.CONDITIONAL, FieldStatus.ESTABLISHED):
        sample = FieldSample(
            value=1.0,
            status=status,
            query=query,
            provenance=_provenance(),
            explanation="limited section scope" if status is FieldStatus.CONDITIONAL else "",
        )
        assert sample.value == 1.0
        with pytest.raises((TypeError, ValueError)):
            FieldSample(
                value=None,
                status=status,
                query=query,
                provenance=_provenance(),
            )


def test_field_sample_requires_algorithm_and_schema_provenance() -> None:
    """Samples cannot discard the two version markers needed for replay."""
    with pytest.raises((TypeError, ValueError)):
        FieldSample(
            value=1.0,
            status=FieldStatus.ESTABLISHED,
            query=_query(),
            provenance={"algorithm_version": ALGORITHM_VERSION},
        )
    with pytest.raises((TypeError, ValueError)):
        FieldSample(
            value=1.0,
            status=FieldStatus.ESTABLISHED,
            query=_query(),
            provenance={"schema_version": SCHEMA_VERSION},
        )


def test_conditional_sample_requires_scope_explanation() -> None:
    """Conditional values must declare the limited scope they represent."""
    with pytest.raises(ValueError):
        FieldSample(
            value=1.0,
            status=FieldStatus.CONDITIONAL,
            query=_query(),
            provenance=_provenance(),
            explanation="   ",
        )


def test_query_and_sample_are_deeply_immutable() -> None:
    """Nested query, support, source, and provenance values cannot be mutated."""
    query = _query(
        demand={"clearance": {"units": "m", "values": [0.9, 1.2]}},
        plane={"axis": "z", "value": 1.6},
    )
    sample = FieldSample(
        value={"score": 1.0},
        status=FieldStatus.ESTABLISHED,
        query=query,
        support={"evidence": [{"id": "s1"}]},
        source_ids=["source-1"],
        provenance=_provenance(metadata={"nested": ["immutable"]}),
    )
    with pytest.raises((AttributeError, TypeError)):
        query.demand["clearance"]["values"][0] = 2.0
    with pytest.raises((AttributeError, TypeError)):
        sample.support["evidence"][0]["id"] = "changed"
    with pytest.raises((AttributeError, TypeError)):
        sample.provenance["metadata"]["nested"][0] = "changed"
    with pytest.raises((AttributeError, TypeError)):
        sample.source_ids[0] = "changed"
    assert isinstance(sample.source_ids, tuple)


def test_scalar_and_batch_lookup_are_canonically_equivalent() -> None:
    """The default batch path preserves exact scalar semantics and order."""
    field = DictField({"a": 1.0, "b": 2.0})
    query = _query()
    targets = ["b", "a", "b"]
    scalar = tuple(field.evaluate(target, query) for target in targets)
    batch = field.evaluate_many(targets, query)
    assert batch == scalar
    assert tuple(sample.value for sample in batch) == (2.0, 1.0, 2.0)


def test_batch_preserves_relation_targets_order_and_cardinality() -> None:
    """Relation-native tuple targets remain opaque and duplicate results remain distinct."""
    field = DictField({("chair-1", "group-a"): 0.75})
    query = _query(domain_id="relations", frame=None)
    targets = [("chair-1", "group-a"), ("chair-1", "group-a"), ("missing", "group-a")]
    samples = field.evaluate_many(targets, query)
    assert len(samples) == len(targets)
    assert [sample.value for sample in samples[:2]] == [0.75, 0.75]
    assert samples[2].status is FieldStatus.UNKNOWN


def test_missing_domain_or_channel_is_not_available() -> None:
    """Absent domain/channel evidence is unavailable rather than outside or free."""
    query = _query()
    assert DictField({"a": 1.0}, domain=None).evaluate("a", query).status is FieldStatus.NOT_AVAILABLE
    assert (
        DictField({"a": 1.0}, channel_available=False).evaluate("a", query).status
        is FieldStatus.NOT_AVAILABLE
    )
    assert DictField({"a": 1.0}).evaluate("a", _query(domain_id=None)).status is FieldStatus.NOT_AVAILABLE


def test_outside_requires_an_available_domain() -> None:
    """A valid target outside a declared domain is outside, never unavailable."""
    sample = DictField({"a": 1.0}, domain=("a",)).evaluate("z", _query())
    assert sample.status is FieldStatus.OUTSIDE
    assert sample.value is None


def test_unknown_is_not_coerced_to_zero_or_free() -> None:
    """Insufficient evidence keeps an explicit unknown status and null value."""
    sample = DictField({"a": None}).evaluate("a", _query())
    assert sample.status is FieldStatus.UNKNOWN
    assert sample.value is None
    assert sample.value != 0


def test_conditional_sample_retains_scope_explanation_and_audit_context() -> None:
    """Section-limited values preserve scope, revision, units, and tolerance."""
    query = _query(
        plane={"axis": "z", "value": 1.6, "units": "m"},
        revision="section-r7",
        tolerance=0.005,
    )
    sample = DictField({"a": 1.0}).evaluate("a", query)
    assert sample.status is FieldStatus.CONDITIONAL
    assert sample.value == 1.0
    assert "section" in sample.explanation.lower()
    assert sample.query == query
    assert sample.provenance["query_revision"] == "section-r7"
    assert sample.provenance["units"] == "scalar"
    assert sample.provenance["tolerance"] == 0.005
    assert sample.provenance["algorithm_version"] == ALGORITHM_VERSION
    assert sample.provenance["schema_version"] == SCHEMA_VERSION


def test_structural_errors_raise_but_evidence_shortfall_returns_a_sample() -> None:
    """Malformed records raise while ordinary lookup gaps remain status-bearing."""
    with pytest.raises((TypeError, ValueError)):
        FieldQuery(domain_id="room-a", tolerance="not-a-number", revision="r1")
    with pytest.raises((TypeError, ValueError)):
        FieldSample(
            value=None,
            status="not-a-real-status",
            query=_query(),
            provenance=_provenance(),
        )
    result = DictField({}).evaluate("a", _query())
    assert isinstance(result, FieldSample)
    assert result.status is FieldStatus.UNKNOWN


def _cache(query: FieldQuery, channels: list[dict[str, Any]], *, source: str = "source-r1", recipe: str = "recipe-r1") -> dict[str, str]:
    """Build a cache identity for envelope-focused tests."""
    return build_field_result_cache_identity(
        target={"kind": "object", "id": "obj-1", "identity": "obj-1"},
        query=query,
        channel_declarations=channels,
        input_fingerprint="input-r1",
        source_fingerprint=source,
        recipe_fingerprint=recipe,
        algorithm_version=ALGORITHM_VERSION,
        schema_version=SCHEMA_VERSION,
    )


def test_result_envelope_preserves_sorted_channels_and_raw_status() -> None:
    """Envelope records remain immutable and admitted channels are canonicalized."""
    query = _query()
    declarations = [{"channel": "semantic", "version": 1}, {"channel": "geometry", "version": 1}]
    records = [
        EvidenceChannelRecord("semantic", False, "descriptive", None, status=FieldResultStatus.NOT_AVAILABLE, provenance={"inherits_top_level": True}),
        EvidenceChannelRecord("geometry", True, "positive", {"distance": 1}, provenance=_provenance()),
    ]
    result = FieldResultEnvelope(
        target={"kind": "object", "id": "obj-1", "identity": "obj-1"}, query=query,
        raw_status=FieldResultStatus.PARTIAL, channel_set=("semantic", "geometry"),
        value={"channels": records}, provenance=_provenance(), cache_identity=_cache(query, declarations),
        explanation="semantic evidence is unavailable",
    )
    assert result.channel_set == ("geometry", "semantic")
    assert result.value["channels"][0].channel == "geometry"
    assert project_field_sample(result) is None


def test_result_envelope_projects_complete_structured_value() -> None:
    """A complete computed envelope projects with raw status and mapping reason."""
    query = _query()
    channel = EvidenceChannelRecord("geometry", True, "positive", {"distance": 1}, provenance=_provenance())
    result = FieldResultEnvelope(
        target={"kind": "object", "id": "obj-1", "identity": "obj-1"}, query=query,
        raw_status=FieldResultStatus.COMPUTED, channel_set=("geometry",), value={"channels": (channel,)},
        support={"count": 1}, source_ids=("src-1",), field_projection={"status": "established", "mapping_reason": "complete evidence"},
        provenance=_provenance(), cache_identity=_cache(query, [{"channel": "geometry", "version": 1}]),
    )
    sample = project_field_sample(result)
    assert sample is not None
    assert sample.value == result.value
    assert sample.provenance["raw_status"] == "computed"
    assert sample.provenance["mapping_reason"] == "complete evidence"


def test_cache_identity_is_order_independent_but_input_sensitive() -> None:
    """Canonical declarations hash independently of traversal order and vary on inputs."""
    query = _query()
    a = [{"channel": "geometry", "version": 1}, {"channel": "semantic", "version": 1}]
    b = list(reversed(a))
    first = _cache(query, a)
    assert first == _cache(query, b)
    assert first["identity"] != _cache(query, a, source="source-r2")["identity"]
    assert first["identity"] != _cache(_query(revision="query-r2"), a)["identity"]


def test_mutable_dataclass_payload_is_rejected() -> None:
    """Mutable dataclasses cannot bypass the envelope's immutable payload boundary."""
    @dataclass
    class MutableEvidence:
        score: float

    with pytest.raises(TypeError):
        EvidenceChannelRecord(
            "geometry",
            True,
            "positive",
            MutableEvidence(1.0),
            provenance=_provenance(),
        )


def test_frozen_dataclass_payload_is_deeply_frozen() -> None:
    """Frozen dataclasses cannot retain mutable nested containers in evidence."""

    @dataclass(frozen=True)
    class FrozenEvidence:
        metadata: dict[str, str]

    record = EvidenceChannelRecord(
        "geometry",
        True,
        "positive",
        FrozenEvidence({"unit": "m"}),
        provenance=_provenance(),
    )
    with pytest.raises((AttributeError, TypeError)):
        record.observation.metadata["unit"] = "cm"


def test_nonempty_channel_set_requires_records_but_empty_set_may_be_null() -> None:
    """Admitted channels retain explicit null records while an empty set stays representable."""
    query = _query()
    with pytest.raises(ValueError):
        FieldResultEnvelope(
            target={"kind": "object", "id": "obj-1", "identity": "obj-1"},
            query=query,
            raw_status=FieldResultStatus.PARTIAL,
            channel_set=("geometry",),
            value=None,
            provenance=_provenance(),
            cache_identity=_cache(query, [{"channel": "geometry"}]),
            explanation="geometry was not evaluated",
        )
    empty = FieldResultEnvelope(
        target={"kind": "object", "id": "obj-1", "identity": "obj-1"},
        query=query,
        raw_status=FieldResultStatus.NOT_EVALUATED,
        channel_set=(),
        value=None,
        provenance=_provenance(),
        cache_identity=_cache(query, []),
        explanation="evaluation was skipped",
    )
    assert empty.value is None


def test_same_channel_supports_distinct_polarities_but_not_duplicate_keys() -> None:
    """Positive and negative evidence share a channel while each polarity key stays unique."""
    query = _query()
    positive = EvidenceChannelRecord("semantic", False, "positive", True, provenance=_provenance())
    negative = EvidenceChannelRecord("semantic", False, "negative", False, provenance=_provenance())
    result = FieldResultEnvelope(
        target={"kind": "object", "id": "obj-1", "identity": "obj-1"},
        query=query,
        raw_status=FieldResultStatus.AMBIGUOUS,
        channel_set=("semantic",),
        value={"channels": (positive, negative)},
        provenance=_provenance(),
        cache_identity=_cache(query, [{"channel": "semantic"}]),
        explanation="positive and negative evidence conflict",
    )
    assert [record.polarity for record in result.value["channels"]] == ["negative", "positive"]
    with pytest.raises(ValueError):
        FieldResultEnvelope(
            target={"kind": "object", "id": "obj-1", "identity": "obj-1"},
            query=query,
            raw_status=FieldResultStatus.AMBIGUOUS,
            channel_set=("semantic",),
            value={"channels": (positive, positive)},
            provenance=_provenance(),
            cache_identity=_cache(query, [{"channel": "semantic"}]),
            explanation="duplicate positive evidence",
        )
