"""Red contract tests for the standalone field visualization manifest."""

from __future__ import annotations

import json

import pytest

from ..features.field_core import (
    EvidenceChannelRecord,
    FieldQuery,
    FieldResultEnvelope,
    FieldResultStatus,
    FieldSample,
    FieldStatus,
    build_field_result_cache_identity,
)
from ..features.space_field_visualization import (
    build_field_layer_manifest,
    build_field_result_layer_manifest,
)


ALGORITHM_VERSION = "visualization-test/1"
SCHEMA_VERSION = "field-core-test/1"


def _sample(status: FieldStatus, value=None, *, explanation: str = "") -> FieldSample:
    """Build one immutable sample for manifest state-isolation checks."""
    if status is FieldStatus.CONDITIONAL and not explanation:
        explanation = "limited to the declared section scope"
    return FieldSample(
        value=value,
        status=status,
        query=FieldQuery(
            domain_id="room-a",
            frame="world-xy",
            plane={"axis": "z", "value": 1.6, "units": "m"},
            revision="visual-r1",
        ),
        support={"units": "m", "count": 1},
        source_ids=("source-1",),
        provenance={
            "algorithm_version": ALGORITHM_VERSION,
            "schema_version": SCHEMA_VERSION,
            "units": "m",
            "tolerance": 0.005,
        },
        explanation=explanation,
    )


def _result(raw_status: FieldResultStatus, *, projection=None, value=True, channels=None, explanation=""):
    """Build a valid envelope for manifest adapter contract tests."""
    query = FieldQuery(domain_id="room-a", frame="world-xy", revision="visual-r1")
    channels = channels or (EvidenceChannelRecord("geometry", True, "positive", value, provenance={"algorithm_version": ALGORITHM_VERSION, "schema_version": SCHEMA_VERSION}),)
    cache = build_field_result_cache_identity(
        target={"kind": "object", "id": "obj-1", "identity": "obj-1"}, query=query,
        channel_declarations=[{"channel": record.channel} for record in channels],
        input_fingerprint="input-r1", source_fingerprint="source-r1", recipe_fingerprint="recipe-r1",
        algorithm_version=ALGORITHM_VERSION, schema_version=SCHEMA_VERSION,
    )
    return FieldResultEnvelope(
        target={"kind": "object", "id": "obj-1", "identity": "obj-1"}, query=query,
        raw_status=raw_status, channel_set=tuple(record.channel for record in channels),
        value={"channels": channels} if value is not None else None,
        support={"count": 1}, source_ids=("source-1",), field_projection=projection,
        provenance={"algorithm_version": ALGORITHM_VERSION, "schema_version": SCHEMA_VERSION, "units": "m"},
        cache_identity=cache, explanation=explanation or ("evidence incomplete" if raw_status is not FieldResultStatus.COMPUTED else ""),
    )


def test_result_manifest_projects_established_envelope_and_preserves_raw_evidence():
    """Complete envelopes use the legacy display fields and retain relation evidence."""
    result = _result(FieldResultStatus.COMPUTED, projection={"status": "established", "mapping_reason": "complete evidence"})
    record = build_field_result_layer_manifest(layer_id="relations", channel="occupancy", results=(result,))["samples"][0]
    assert record["status"] == "established"
    assert record["visual_state"] == "established"
    assert record["raw_status"] == "computed"
    assert record["channel_set"] == ["geometry"]
    assert record["channel_records"][0]["status"] == "computed"
    assert record["explanation"] == "complete evidence"


def test_result_manifest_uses_unknown_fallback_for_partial_and_unavailable_channels():
    """Unprojectable results stay conservative while preserving unavailable evidence."""
    unavailable = EvidenceChannelRecord("semantic", False, "descriptive", None, status=FieldResultStatus.NOT_AVAILABLE, provenance={"inherits_top_level": True}, explanation="channel unavailable")
    result = _result(FieldResultStatus.PARTIAL, value=False, channels=(unavailable,), explanation="semantic evidence is unavailable")
    record = build_field_result_layer_manifest(layer_id="relations", channel="occupancy", results=(result,))["samples"][0]
    assert record["status"] == record["visual_state"] == "unknown"
    assert record["raw_status"] == "partial"
    assert record["channel_set"] == ["semantic"]
    assert record["channel_records"][0]["status"] == "not_available"
    assert record["explanation"] == "semantic evidence is unavailable"


def test_manifest_retains_layer_channel_coordinates_status_sources_and_provenance():
    """A manifest record carries the audit fields needed by a standalone renderer."""
    samples = (_sample(FieldStatus.CONDITIONAL, True),)

    manifest = build_field_layer_manifest(
        layer_id="b3-occupancy",
        channel="physical_occupancy",
        samples=samples,
    )

    assert manifest["layer_id"] == "b3-occupancy"
    assert manifest["semantic_channel"] == "physical_occupancy"
    record = manifest["samples"][0]
    assert record["status"] == "conditional"
    assert record["value"] is True
    assert record["source_ids"] == ["source-1"]
    assert record["frame"] == "world-xy"
    assert record["plane"] == {"axis": "z", "value": 1.6, "units": "m"}
    assert record["units"] == "m"
    assert record["tolerance"] == 0.005
    assert record["algorithm_version"] == ALGORITHM_VERSION
    assert record["schema_version"] == SCHEMA_VERSION


def test_manifest_keeps_unknown_invalid_outside_and_conditional_visually_distinct():
    """Non-empty statuses receive distinct visual states and never become free."""
    samples = (
        _sample(FieldStatus.UNKNOWN),
        _sample(FieldStatus.INVALID),
        _sample(FieldStatus.OUTSIDE),
        _sample(FieldStatus.CONDITIONAL, True),
    )

    manifest = build_field_layer_manifest(
        layer_id="status-isolation",
        channel="physical_occupancy",
        samples=samples,
    )

    records = manifest["samples"]
    assert [record["status"] for record in records] == [
        "unknown",
        "invalid",
        "outside",
        "conditional",
    ]
    assert len({record["visual_state"] for record in records}) == 4
    assert records[0]["value"] is None
    assert records[1]["value"] is None
    assert records[2]["value"] is None
    assert records[3]["value"] is True
    assert all(record["visual_state"] not in {"empty", "free"} for record in records[:3])


def test_manifest_serialization_is_deterministic():
    """Equivalent manifests produce byte-identical canonical JSON."""
    samples = (
        _sample(FieldStatus.OUTSIDE),
        _sample(FieldStatus.CONDITIONAL, False),
    )
    first = build_field_layer_manifest(
        layer_id="deterministic",
        channel="physical_occupancy",
        samples=samples,
    )
    second = build_field_layer_manifest(
        layer_id="deterministic",
        channel="physical_occupancy",
        samples=samples,
    )

    encode = lambda value: json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    assert encode(first) == encode(second)


def test_result_manifest_serialization_is_deterministic():
    """Equivalent envelope manifests serialize identically with nested evidence."""
    first = build_field_result_layer_manifest(
        layer_id="deterministic-results",
        channel="relation",
        results=(_result(FieldResultStatus.PARTIAL, value=False, explanation="semantic evidence is unavailable"),),
    )
    second = build_field_result_layer_manifest(
        layer_id="deterministic-results",
        channel="relation",
        results=(_result(FieldResultStatus.PARTIAL, value=False, explanation="semantic evidence is unavailable"),),
    )
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    assert encode(first) == encode(second)
