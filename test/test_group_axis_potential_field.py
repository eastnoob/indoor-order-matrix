"""Pure scalar tests for the axis-only aggregation operator.

These tests cover only the mathematical rule. IFC source envelopes, provenance,
and serialization are verified by the pinned-IFC integration runner.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from features.field_core import FieldResultStatus, serialize_evidence_package_output
from features.group_axis_potential_field import (
    _soft_view_result,
    aggregate_axis_observations,
    build_axis_relation_records,
    build_group_axis_potential_package,
)
from scripts.design.group_level.run_group_axis_potential_ifc_replay import _load_envelope


def _aggregate(*items):
    """Apply the scalar operator without constructing scene or IFC records."""
    return aggregate_axis_observations(items)


def _retained_envelopes(limit: int | None = None):
    """Load verified trend envelopes without running IFC extraction."""
    artifact = Path(__file__).parents[1] / "outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/envelopes.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    items = payload["envelopes"] if limit is None else payload["envelopes"][:limit]
    return tuple(_load_envelope(item) for item in items)


def test_scalar_operator_treats_zero_and_180_as_equivalent():
    """Pure scalar axes use an undirected modulo-180 convention."""
    result = _aggregate(
        {"group_id": "a", "angle": 0.0, "clarity": 1.0},
        {"group_id": "b", "angle": 180.0, "clarity": 1.0},
    )
    assert result["angle"] == pytest.approx(0.0)
    assert result["direction_coherence"] == pytest.approx(1.0)


def test_scalar_operator_weights_direction_and_support_by_clarity_only():
    """Pure scalar inputs verify clarity weighting without any area term."""
    result = _aggregate(
        {"group_id": "a", "angle": 0.0, "clarity": 1.0},
        {"group_id": "b", "angle": 90.0, "clarity": 0.25},
    )
    assert result["angle"] == pytest.approx(0.0)
    assert result["direction_coherence"] == pytest.approx(0.75 / 1.25)
    assert result["clarity_weighted_directional_support"] == pytest.approx(0.375)


def test_scalar_operator_marks_equal_orthogonal_axes_ambiguous():
    """Pure scalar orthogonal cancellation cannot fabricate a float direction."""
    result = _aggregate(
        {"group_id": "a", "angle": 0.0, "clarity": 1.0},
        {"group_id": "b", "angle": 90.0, "clarity": 1.0},
    )
    assert result["aggregate_status"] == "ambiguous"
    assert result["angle"] is None
    assert result["direction_coherence"] == pytest.approx(0.0)


def test_scalar_operator_excludes_degenerate_axis_and_reports_coverage():
    """Pure scalar undefined axes are excluded instead of becoming zero degrees."""
    result = _aggregate(
        {"group_id": "a", "angle": 0.0, "clarity": 1.0},
        {"group_id": "b", "angle": None, "clarity": None, "direction_status": "undefined"},
    )
    assert result["angle"] == pytest.approx(0.0)
    assert result["valid_axis_count"] == 1
    assert result["total_group_count"] == 2
    assert result["excluded"][0]["reason"] == "undefined_axis"


def test_scalar_operator_distinguishes_no_axis_from_all_zero_clarity():
    """Pure scalar all-zero clarity remains valid data without direction support."""
    unavailable = _aggregate({"group_id": "a", "angle": None, "clarity": None, "direction_status": "undefined"})
    assert unavailable["aggregate_status"] == "not_available"
    zero = _aggregate({"group_id": "a", "angle": 30.0, "clarity": 0.0})
    assert zero["aggregate_status"] == "not_evaluated"
    assert zero["direction_coherence"] is None
    assert zero["clarity_weighted_directional_support"] == pytest.approx(0.0)


def test_scalar_operator_does_not_call_one_positive_axis_group_consensus():
    """One positive clarity contribution cannot claim between-group coherence."""
    result = _aggregate(
        {"group_id": "a", "angle": 35.0, "clarity": 0.5},
        {"group_id": "b", "angle": 80.0, "clarity": 0.0},
    )
    assert result["direction_coherence"] is None
    assert result["direction_coherence_status"] == "not_evaluated"


def test_scalar_operator_retains_very_small_positive_clarity():
    """Positive clarity remains weak evidence instead of being rounded to zero."""
    result = _aggregate(
        {"group_id": "a", "angle": 0.0, "clarity": 1e-15},
        {"group_id": "b", "angle": 0.0, "clarity": 1e-15},
    )
    assert result["aggregate_status"] == "computed"
    assert result["angle"] == pytest.approx(0.0)
    assert result["direction_coherence"] == pytest.approx(1.0)


def test_scalar_operator_rejects_clarity_outside_pca_anisotropy_range():
    """Clarity outside PCA anisotropy's closed unit interval is invalid."""
    result = _aggregate({"group_id": "a", "angle": 0.0, "clarity": 1.1})
    assert result["valid_axis_count"] == 0
    assert result["excluded"][0]["reason"] == "invalid_clarity"


@pytest.mark.parametrize("invalid_clarity", [1.1, -0.1])
def test_envelope_operator_excludes_invalid_clarity_from_real_ifc_envelope(invalid_clarity):
    """The FieldResultEnvelope path rejects invalid clarity on a retained IFC record."""
    artifact = Path(__file__).parents[1] / "outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/envelopes.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    envelope = _load_envelope(payload["envelopes"][0])
    records = []
    for record in envelope.value["channels"]:
        if record.channel != "overall_group_axis":
            records.append(record)
            continue
        descriptor = dict(record.observation["descriptor"])
        descriptor["strength"] = invalid_clarity
        records.append(replace(record, observation={**record.observation, "descriptor": descriptor}))
    corrupted = replace(envelope, value={"channels": tuple(records)})

    result = build_group_axis_potential_package().evaluate((corrupted,))
    diagnostics = next(output for output in result.outputs if output.channel == "excluded_axis_diagnostics")
    assert diagnostics.observation["excluded"][0]["reason"] == "invalid_clarity"
    assert diagnostics.observation["excluded"][0]["clarity"] == invalid_clarity


def test_scalar_operator_marks_singleton_as_insufficient_consensus():
    """Pure scalar singleton direction is retained with its consensus caveat."""
    result = _aggregate({"group_id": "a", "angle": 35.0, "clarity": 0.5})
    assert result["angle"] == pytest.approx(35.0)
    assert result["consensus_status"] == "singleton/insufficient-consensus"


def test_scalar_operator_rejects_non_mapping_observations():
    """The mathematical boundary rejects malformed scalar records."""
    with pytest.raises(TypeError, match="mappings"):
        aggregate_axis_observations((1,))


def test_package_adds_four_independent_relation_channels_for_every_pair():
    """The active package emits 666 pair addresses while retaining all source channels."""
    envelopes = _retained_envelopes()
    result = build_group_axis_potential_package().evaluate(envelopes)
    relation_outputs = [
        output for output in result.outputs if output.target["kind"] == "furniture_group_pair"
    ]
    assert len(envelopes) == 37
    assert len(relation_outputs) == 666 * 4
    assert {output.channel for output in relation_outputs} == {
        "axis_angle_gap",
        "direction_similarity",
        "clarity_similarity",
        "clarity_support",
    }
    assert len({output.target["identity"] for output in relation_outputs}) == 666
    assert all("combined_relation" not in output.observation for output in relation_outputs)
    assert all(output.provenance["global_resultant_vote"] is False for output in relation_outputs)
    serialized = serialize_evidence_package_output(result)
    assert len(serialized["source_envelopes"]) == 37
    source_by_identity = {item.cache_identity["identity"]: item for item in envelopes}
    output_sources = {item.cache_identity["identity"]: item for item in result.source_envelopes}
    assert output_sources == source_by_identity
    assert all(
        "overall_group_axis" in envelope.channel_set
        and tuple(record.channel for record in envelope.value["channels"]) == envelope.channel_set
        for envelope in result.source_envelopes
    )
    assert len([output for output in result.outputs if output.target["kind"] == "furniture_group_axis_field_cell"]) == 37 * 37
    assert len([output for output in result.outputs if output.channel == "non_self_profile"]) == 37
    assert len([output for output in result.outputs if output.channel == "soft_view_direction"]) == 37


def test_source_axis_fields_keep_full_scope_and_self_exclusion():
    """Every real source axis becomes one overlapping field view over the full scope."""
    envelopes = _retained_envelopes()
    result = build_group_axis_potential_package().evaluate(envelopes)
    cells = [output for output in result.outputs if output.target["kind"] == "furniture_group_axis_field_cell"]
    assert len(cells) == 37 * 37
    assert len({output.observation["field_id"] for output in cells}) == 37
    assert all(output.observation["status"] == "computed" for output in cells)
    self_cells = [output for output in cells if output.observation["self_reference"]]
    assert len(self_cells) == 37
    assert all(
        output.observation["axis_field_support"] == pytest.approx(output.observation["group_clarity"])
        for output in self_cells
    )
    profiles = [output for output in result.outputs if output.channel == "non_self_profile"]
    assert all(output.observation["expected_count"] == 36 for output in profiles)
    assert all(output.observation["valid_count"] == 36 for output in profiles)
    directions = [output for output in result.outputs if output.channel == "soft_view_direction"]
    assert all(output.observation["expected_count"] == 37 for output in directions)


def test_nonempty_scope_without_usable_axis_emits_source_axis_diagnostic():
    """The real source scope remains visible when every anchor axis is unavailable."""
    envelopes = []
    for envelope in _retained_envelopes(2):
        records = []
        for record in envelope.value["channels"]:
            if record.channel == "overall_group_axis":
                descriptor = dict(record.observation["descriptor"])
                descriptor.update({"direction_status": "undefined", "angle": None})
                record = replace(
                    record,
                    observation={**record.observation, "descriptor": descriptor},
                    status=FieldResultStatus.NOT_AVAILABLE,
                )
            records.append(record)
        envelopes.append(replace(envelope, value={"channels": tuple(records)}))

    result = build_group_axis_potential_package().evaluate(tuple(envelopes))
    diagnostic = next(
        output for output in result.outputs if output.channel == "source_axis_scope_diagnostics"
    )
    assert diagnostic.status is FieldResultStatus.NOT_AVAILABLE
    assert diagnostic.observation["scope_group_count"] == 2
    assert diagnostic.observation["valid_anchor_count"] == 0
    assert len(diagnostic.derived_from) == 2


def test_singleton_nonself_profile_is_unavailable_but_view_direction_is_anchor_only():
    """A retained singleton has no non-self coverage and only a self-supported view."""
    result = build_group_axis_potential_package().evaluate(_retained_envelopes(1))
    profile = next(output for output in result.outputs if output.channel == "non_self_profile")
    direction = next(output for output in result.outputs if output.channel == "soft_view_direction")
    assert profile.status is FieldResultStatus.NOT_AVAILABLE
    assert profile.observation["expected_count"] == 0
    assert profile.observation["coverage"] is None
    assert direction.observation["direction_status"] == "anchor_only"
    assert direction.observation["expected_count"] == 1
    assert direction.observation["self_weight_fraction"] == pytest.approx(1.0)


def test_soft_view_math_distinguishes_zero_support_and_cancellation():
    """Pure vector checks cover unavailable support and doubled-angle cancellation."""
    zero = {"status": "computed", "axis_field_support": 0.0, "group_axis_angle": 0.0}
    observation, status, _ = _soft_view_result((zero,))
    assert status is FieldResultStatus.NOT_AVAILABLE
    assert observation["direction"] is None
    assert observation["direction_coherence"] is None

    opposing = (
        {"status": "computed", "axis_field_support": 1.0, "group_axis_angle": 0.0},
        {"status": "computed", "axis_field_support": 1.0, "group_axis_angle": 90.0},
    )
    observation, status, _ = _soft_view_result(opposing)
    assert status is FieldResultStatus.AMBIGUOUS
    assert observation["direction"] is None
    assert observation["direction_coherence"] == pytest.approx(0.0)


def test_package_output_identity_is_deterministic_for_retained_content():
    """Restoring the same retained source content restores its output cache identity."""
    envelopes = _retained_envelopes()
    package = build_group_axis_potential_package()
    assert package.evaluate(envelopes).output_identity == package.evaluate(envelopes).output_identity
    assert package.evaluate(envelopes).output_identity == package.evaluate(tuple(reversed(envelopes))).output_identity


def test_relation_status_keeps_clarity_when_direction_is_unavailable():
    """Unavailable endpoint direction leaves independently valid clarity readings computed."""
    envelopes = list(_retained_envelopes(2))
    first = envelopes[0]
    records = []
    for record in first.value["channels"]:
        if record.channel != "overall_group_axis":
            records.append(record)
            continue
        descriptor = dict(record.observation["descriptor"])
        descriptor["direction_status"] = "undefined"
        records.append(
            replace(
                record,
                observation={**record.observation, "descriptor": descriptor},
                status=FieldResultStatus.NOT_AVAILABLE,
            )
        )
    envelopes[0] = replace(first, value={"channels": tuple(records)})

    result = build_group_axis_potential_package().evaluate(tuple(envelopes))
    relation_outputs = {
        output.channel: output
        for output in result.outputs
        if output.target["kind"] == "furniture_group_pair"
    }
    assert relation_outputs["axis_angle_gap"].status is FieldResultStatus.NOT_AVAILABLE
    assert relation_outputs["direction_similarity"].status is FieldResultStatus.NOT_AVAILABLE
    assert relation_outputs["clarity_similarity"].status is FieldResultStatus.COMPUTED
    assert relation_outputs["clarity_support"].status is FieldResultStatus.COMPUTED
    assert len(relation_outputs["axis_angle_gap"].derived_from) == 2


def test_relation_records_are_symmetric_and_modulo_180():
    """Pure relation records use sorted pair addresses and treat 0/180 as equal."""
    observations = {
        "b": {"angle": 180.0, "clarity": 0.4, "axis_status": "computed", "direction_status": "computed"},
        "a": {"angle": 0.0, "clarity": 0.8, "axis_status": "computed", "direction_status": "computed"},
    }
    record = build_axis_relation_records(observations)[0]
    reverse = build_axis_relation_records(dict(reversed(tuple(observations.items()))))[0]
    assert record["group_a"] == "a"
    assert record["group_b"] == "b"
    assert reverse["pair_id"] == record["pair_id"]
    assert reverse["channels"] == record["channels"]
    assert record["channels"]["axis_angle_gap"]["value"] == pytest.approx(0.0)
    assert record["channels"]["direction_similarity"]["value"] == pytest.approx(1.0)
    assert record["channels"]["clarity_similarity"]["value"] == pytest.approx(0.6)
    assert record["channels"]["clarity_support"]["value"] == pytest.approx(0.4)

