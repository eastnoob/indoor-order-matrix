"""Axis-only potential aggregation for furniture-group trend envelopes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
from math import atan2, cos, degrees, hypot, isfinite, radians, sin
from typing import Any

from .field_core import (
    EvidenceChannelReference,
    EvidenceOutputChannel,
    EvidenceOutputScale,
    EvidencePackage,
    FieldResultEnvelope,
    FieldResultStatus,
)


PACKAGE_ID = "group-axis-potential"
OUTPUT_FUNCTION_ID = "aggregate_group_axis_potential"
OUTPUT_FUNCTION_VERSION = "axis-with-relations-v1"
AGGREGATE_TARGET = {
    "kind": "furniture_group_axis_potential_summary",
    "id": "all_supplied_authored_groups_diagnostic",
    "identity": "furniture_group_axis_potential_summary:all_supplied_authored_groups_diagnostic",
}
RELATION_CHANNELS = (
    "axis_angle_gap",
    "direction_similarity",
    "clarity_similarity",
    "clarity_support",
)
FIELD_CELL_KIND = "furniture_group_axis_field_cell"
FIELD_VIEW_KIND = "furniture_group_axis_field"
FIELD_RECIPE_ID = "source-axis-g-to-k-v1"
FIELD_OUTPUT_SCHEMA = "group-axis-potential-field-output/v1"


def _overall_record(envelope: FieldResultEnvelope) -> Any | None:
    """Return the admitted overall-group-axis channel record, if present."""
    if envelope.value is None:
        return None
    return next(
        (record for record in envelope.value["channels"] if record.channel == "overall_group_axis"),
        None,
    )


def _axis_observation(envelope: FieldResultEnvelope) -> tuple[dict[str, Any] | None, str | None]:
    """Extract one valid axis observation or an explicit exclusion reason."""
    record = _overall_record(envelope)
    if record is None:
        return None, "missing_overall_group_axis"
    descriptor = record.observation.get("descriptor") if isinstance(record.observation, Mapping) else None
    if not isinstance(descriptor, Mapping):
        return None, "missing_axis_descriptor"
    direction_status = str(descriptor.get("direction_status", "undefined"))
    angle = descriptor.get("angle")
    clarity = descriptor.get("strength")
    if record.status is not FieldResultStatus.COMPUTED:
        return None, f"channel_status_{record.status.value}"
    if direction_status in {"undefined", "degenerate"} or angle is None:
        return None, "undefined_axis" if direction_status == "undefined" else "degenerate_axis"
    if direction_status == "invalid":
        return None, "invalid_axis"
    if isinstance(angle, bool) or not isinstance(angle, (int, float)) or not isfinite(float(angle)):
        return None, "invalid_axis_angle"
    # PCA anisotropy is a bounded clarity measure; reject out-of-range input rather than clamping it.
    if isinstance(clarity, bool) or not isinstance(clarity, (int, float)) or not isfinite(float(clarity)) or not 0.0 <= float(clarity) <= 1.0:
        return None, "invalid_clarity"
    return {
        "group_id": envelope.target["id"],
        "angle": float(angle) % 180.0,
        "clarity": float(clarity),
        "direction_status": direction_status,
        "source_ids": tuple(record.source_ids),
        "result_identity": envelope.cache_identity["identity"],
    }, None


def _lineage(envelopes: tuple[FieldResultEnvelope, ...]) -> tuple[EvidenceChannelReference, ...]:
    """Reference every source envelope's overall axis channel for traceability."""
    return tuple(
        EvidenceChannelReference.from_envelope(envelope, "overall_group_axis")
        for envelope in envelopes
        if "overall_group_axis" in envelope.channel_set
    )


def _axis_reference(envelope: FieldResultEnvelope) -> EvidenceChannelReference:
    """Return the source reference used by every axis-field derivation."""
    return EvidenceChannelReference.from_envelope(envelope, "overall_group_axis")


def _field_id(anchor: FieldResultEnvelope) -> str:
    """Build a stable source-axis field identity without timestamps or revisions."""
    query_fingerprint = anchor.cache_identity["query_fingerprint"]
    return f"{PACKAGE_ID}:{FIELD_RECIPE_ID}:{query_fingerprint}:{anchor.target['identity']}"


def _cell_target(field_id: str, group_id: str) -> dict[str, str]:
    """Return the stable target identity for one group-to-field support cell."""
    identity = f"{field_id}:group:{group_id}"
    return {"kind": FIELD_CELL_KIND, "id": identity, "identity": identity}


def _field_target(field_id: str) -> dict[str, str]:
    """Return the stable target identity for one anchored field view."""
    return {"kind": FIELD_VIEW_KIND, "id": field_id, "identity": field_id}


def _field_provenance() -> dict[str, Any]:
    """Declare the source-axis support formula and its non-probabilistic meaning."""
    return {
        "method": "source_axis_g_to_k_support",
        "formula": "axis_field_support=group_clarity*cos^2(min_undirected_axis_delta)",
        "axis_convention": "undirected_mod_180",
        "support_semantics": "non_probability_reference_conditioned_support",
        "algorithm_version": OUTPUT_FUNCTION_VERSION,
        "schema_version": FIELD_OUTPUT_SCHEMA,
    }


def _soft_view_result(cells: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], FieldResultStatus, str]:
    """Describe one support-weighted undirected view without reweighting clarity."""
    cells = tuple(cells)
    valid_cells = tuple(item for item in cells if item.get("status") == FieldResultStatus.COMPUTED.value)
    total_support = sum(float(item["axis_field_support"]) for item in valid_cells)
    positive_cells = tuple(item for item in valid_cells if float(item["axis_field_support"]) > 0.0)
    rx = sum(float(item["axis_field_support"]) * cos(radians(2.0 * float(item["group_axis_angle"]))) for item in valid_cells)
    ry = sum(float(item["axis_field_support"]) * sin(radians(2.0 * float(item["group_axis_angle"]))) for item in valid_cells)
    norm = hypot(rx, ry)
    coherence = norm / total_support if total_support > 0.0 else None
    direction = None if total_support == 0.0 or (coherence is not None and coherence <= 1e-12) else degrees(0.5 * atan2(ry, rx)) % 180.0
    if direction is not None and abs(direction - 180.0) <= 1e-12:
        direction = 0.0
    if direction is None and total_support == 0.0:
        status, explanation = FieldResultStatus.NOT_AVAILABLE, "No positive support is available for a view direction."
    elif direction is None:
        status, explanation = FieldResultStatus.AMBIGUOUS, "Weighted undirected directions cancel within numeric tolerance."
    else:
        status, explanation = FieldResultStatus.COMPUTED, ""
    self_cell = next((item for item in valid_cells if item.get("self_reference")), None)
    self_weight = float(self_cell["axis_field_support"]) if self_cell is not None else None
    observation = {
        "direction": direction,
        "direction_status": "anchor_only" if len(positive_cells) == 1 and direction is not None else status.value,
        "direction_coherence": coherence,
        "total_support": total_support,
        "valid_count": len(valid_cells),
        "expected_count": len(cells),
        "coverage": len(valid_cells) / len(cells) if cells else 0.0,
        "positive_weight_count": len(positive_cells),
        "self_included": self_cell is not None,
        "self_weight": self_weight,
        "self_weight_fraction": self_weight / total_support if self_weight is not None and total_support > 0.0 else None,
    }
    return observation, status, explanation


def _source_axis_field_outputs(
    source_envelopes: tuple[FieldResultEnvelope, ...],
) -> tuple[EvidenceOutputChannel, ...]:
    """Emit complete source-axis fields, profiles, and read-only view directions."""
    endpoint_by_group = {
        envelope.target["identity"]: _axis_observation(envelope)
        for envelope in source_envelopes
    }
    valid_anchors = tuple(
        envelope
        for envelope in source_envelopes
        if endpoint_by_group[envelope.target["identity"]][0] is not None
    )
    outputs: list[EvidenceOutputChannel] = []
    provenance = _field_provenance()
    if not valid_anchors:
        excluded = tuple(
            {
                "group_id": envelope.target["identity"],
                "reason": endpoint_by_group[envelope.target["identity"]][1] or "axis_unavailable",
            }
            for envelope in source_envelopes
        )
        outputs.append(
            EvidenceOutputChannel(
                target=AGGREGATE_TARGET,
                channel="source_axis_scope_diagnostics",
                observation={
                    "scope_group_count": len(source_envelopes),
                    "valid_anchor_count": 0,
                    "excluded": excluded,
                    "status": FieldResultStatus.NOT_AVAILABLE.value,
                },
                status=FieldResultStatus.NOT_AVAILABLE,
                scale=EvidenceOutputScale(
                    meaning="Availability diagnostic for source-axis reference views over the supplied scope",
                    units="count",
                ),
                derived_from=tuple(_axis_reference(envelope) for envelope in source_envelopes),
                source_ids=tuple(sorted({source_id for envelope in source_envelopes for source_id in envelope.source_ids})),
                provenance=provenance,
                explanation="No usable overall_group_axis anchor is available in the non-empty source scope.",
            )
        )
    for anchor in valid_anchors:
        anchor_observation, _ = endpoint_by_group[anchor.target["identity"]]
        assert anchor_observation is not None
        anchor_group_id = anchor.target["identity"]
        field_id = _field_id(anchor)
        field_target = _field_target(field_id)
        anchor_reference = _axis_reference(anchor)
        cell_values: list[dict[str, Any]] = []
        for target in source_envelopes:
            target_group_id = target.target["identity"]
            target_observation, target_reason = endpoint_by_group[target_group_id]
            lineage = (anchor_reference,) if target is anchor else (anchor_reference, _axis_reference(target))
            source_ids = tuple(sorted(set(anchor.source_ids) | set(target.source_ids)))
            if target_observation is None:
                status = FieldResultStatus.NOT_AVAILABLE
                reason = target_reason or "target_axis_unavailable"
                cell = {
                    "field_id": field_id,
                    "anchor_group_id": anchor_group_id,
                    "target_group_id": target_group_id,
                    "anchor_axis_angle": anchor_observation["angle"],
                    "anchor_clarity": anchor_observation["clarity"],
                    "group_axis_angle": None,
                    "group_clarity": None,
                    "delta": None,
                    "direction_alignment": None,
                    "axis_field_support": None,
                    "self_reference": target is anchor,
                    "excluded_from_nonself_profile": target is anchor,
                    "status": status.value,
                    "reason": reason,
                }
            else:
                delta = axis_angle_gap(float(target_observation["angle"]), float(anchor_observation["angle"]))
                alignment = cos(radians(delta)) ** 2
                support = float(target_observation["clarity"]) * alignment
                status = FieldResultStatus.COMPUTED
                cell = {
                    "field_id": field_id,
                    "anchor_group_id": anchor_group_id,
                    "target_group_id": target_group_id,
                    "anchor_axis_angle": anchor_observation["angle"],
                    "anchor_clarity": anchor_observation["clarity"],
                    "group_axis_angle": target_observation["angle"],
                    "group_clarity": target_observation["clarity"],
                    "delta": delta,
                    "direction_alignment": alignment,
                    "axis_field_support": support,
                    "self_reference": target is anchor,
                    "excluded_from_nonself_profile": target is anchor,
                    "status": status.value,
                    "reason": None,
                }
            cell_values.append(cell)
            outputs.append(
                EvidenceOutputChannel(
                    target=_cell_target(field_id, target_group_id),
                    channel="axis_field_support",
                    observation=cell,
                    status=status,
                    scale=EvidenceOutputScale(
                        meaning="Reference-conditioned support of one furniture group for one anchored axis field",
                        units="unitless",
                        normalization_method="group_clarity*cos^2(undirected_axis_delta)",
                        value_range=(0.0, 1.0),
                        endpoint_meanings=("no directional support", "full directional support"),
                    ),
                    derived_from=lineage,
                    source_ids=source_ids,
                    provenance=provenance,
                    explanation="Target overall_group_axis is unavailable or invalid." if status is not FieldResultStatus.COMPUTED else "",
                )
            )

        non_self = [item for item in cell_values if not item["self_reference"]]
        valid_non_self = [item for item in non_self if item["status"] == FieldResultStatus.COMPUTED]
        expected = len(non_self)
        valid_count = len(valid_non_self)
        profile_status = (
            FieldResultStatus.NOT_AVAILABLE
            if expected == 0 or valid_count == 0
            else FieldResultStatus.COMPUTED
            if valid_count == expected
            else FieldResultStatus.PARTIAL
        )
        profile = {
            "field_id": field_id,
            "anchor_group_id": anchor_group_id,
            "anchor_axis_angle": anchor_observation["angle"],
            "anchor_clarity": anchor_observation["clarity"],
            "value": sum(item["axis_field_support"] for item in valid_non_self) / valid_count if valid_count else None,
            "valid_count": valid_count,
            "expected_count": expected,
            "coverage": valid_count / expected if expected else None,
            "self_excluded": True,
            "status": profile_status.value,
        }
        outputs.append(
            EvidenceOutputChannel(
                target=field_target,
                channel="non_self_profile",
                observation=profile,
                status=profile_status,
                scale=EvidenceOutputScale(
                    meaning="Arithmetic mean of known non-self group support values",
                    units="unitless",
                    normalization_method="sum(valid_non_self_support)/N_valid_non_self",
                    value_range=(0.0, 1.0),
                    endpoint_meanings=("no support", "full support"),
                ),
                derived_from=tuple(_axis_reference(item) for item in source_envelopes),
                source_ids=tuple(sorted({source_id for item in source_envelopes for source_id in item.source_ids})),
                provenance=provenance,
                explanation="No non-self support value is available." if profile_status is not FieldResultStatus.COMPUTED else "",
            )
        )

        direction_values, direction_status, explanation = _soft_view_result(cell_values)
        direction_observation = {
            "field_id": field_id,
            "anchor_group_id": anchor_group_id,
            **direction_values,
        }
        outputs.append(
            EvidenceOutputChannel(
                target=field_target,
                channel="soft_view_direction",
                observation=direction_observation,
                status=direction_status,
                scale=EvidenceOutputScale(
                    meaning="Read-only support-weighted undirected direction description for one anchored field view",
                    units="degrees_mod_180",
                    normalization_method="arg(sum(support*exp(i*2*theta)))/2; coherence=|Q|/sum(support)",
                ),
                derived_from=tuple(_axis_reference(item) for item in source_envelopes),
                source_ids=tuple(sorted({source_id for item in source_envelopes for source_id in item.source_ids})),
                provenance=provenance,
                explanation=explanation,
            )
        )
    return tuple(outputs)


def _relation_endpoint(envelope: FieldResultEnvelope) -> dict[str, Any]:
    """Extract endpoint values and provenance for pairwise relation output."""
    record = _overall_record(envelope)
    descriptor = record.observation.get("descriptor", {}) if record and isinstance(record.observation, Mapping) else {}
    return {
        "group_id": envelope.target["id"],
        "angle": descriptor.get("angle"),
        "clarity": descriptor.get("strength"),
        "axis_status": record.status.value if record else "not_available",
        "direction_status": descriptor.get("direction_status"),
        "source_ids": tuple(record.source_ids) if record else tuple(envelope.source_ids),
        "source_cache_identity": dict(envelope.cache_identity),
        "source_channel": "overall_group_axis",
    }


def _relation_scale(channel: str) -> EvidenceOutputScale:
    """Declare the reviewed scale for one pairwise relation channel."""
    if channel == "axis_angle_gap":
        return EvidenceOutputScale(
            meaning="Minimum undirected angle gap between endpoint group axes",
            units="degrees_mod_180",
            normalization_method="min(abs(theta_a-theta_b) mod 180, 180-gap)",
            value_range=(0.0, 90.0),
            endpoint_meanings=("parallel", "perpendicular"),
        )
    meanings = {
        "direction_similarity": "Cosine-squared similarity of the undirected endpoint axes",
        "clarity_similarity": "Similarity of endpoint axis clarity values",
        "clarity_support": "Minimum clarity shared by the two endpoint axes",
    }
    return EvidenceOutputScale(
        meaning=meanings[channel],
        units="unitless",
        normalization_method={
            "direction_similarity": "cos^2(axis_angle_gap)",
            "clarity_similarity": "1-abs(clarity_a-clarity_b)",
            "clarity_support": "min(clarity_a,clarity_b)",
        }[channel],
        value_range=(0.0, 1.0),
        endpoint_meanings=("none", "complete"),
    )


def _relation_outputs(source_envelopes: tuple[FieldResultEnvelope, ...]) -> tuple[EvidenceOutputChannel, ...]:
    """Create additive pair outputs while keeping the global resultant separate."""
    endpoint_map = {
        envelope.target["id"]: _relation_endpoint(envelope)
        for envelope in source_envelopes
    }
    records = build_axis_relation_records(endpoint_map)
    by_id = {envelope.target["id"]: envelope for envelope in source_envelopes}
    outputs: list[EvidenceOutputChannel] = []
    provenance = {
        "method": "independent_undirected_group_axis_relation_channels",
        "formulae": {
            "axis_angle_gap": "minimum undirected gap modulo 180 degrees",
            "direction_similarity": "cos^2(axis_angle_gap)",
            "clarity_similarity": "1-abs(clarity_a-clarity_b)",
            "clarity_support": "min(clarity_a,clarity_b)",
        },
        "relation_address_only": True,
        "combined_relation_emitted": False,
        "global_resultant_vote": False,
        "algorithm_version": OUTPUT_FUNCTION_VERSION,
        "schema_version": "group-axis-relation-output/v1",
    }
    for record in records:
        group_a, group_b = record["group_a"], record["group_b"]
        envelope_a, envelope_b = by_id[group_a], by_id[group_b]
        target = {
            "kind": "furniture_group_pair",
            "id": record["pair_id"],
            "identity": record["pair_id"],
        }
        lineage = (
            EvidenceChannelReference.from_envelope(envelope_a, "overall_group_axis"),
            EvidenceChannelReference.from_envelope(envelope_b, "overall_group_axis"),
        )
        source_ids = tuple(sorted(set(record["endpoint_a"]["source_ids"]) | set(record["endpoint_b"]["source_ids"])))
        for channel in RELATION_CHANNELS:
            reading = record["channels"][channel]
            status = FieldResultStatus(reading["status"])
            outputs.append(
                EvidenceOutputChannel(
                    target=target,
                    channel=channel,
                    observation={
                        "pair_id": record["pair_id"],
                        "group_a": group_a,
                        "group_b": group_b,
                        "value": reading["value"],
                        "status": reading["status"],
                        "reason": reading["reason"],
                        "endpoint_a": record["endpoint_a"],
                        "endpoint_b": record["endpoint_b"],
                    },
                    status=status,
                    scale=_relation_scale(channel),
                    derived_from=lineage,
                    source_ids=source_ids,
                    provenance=provenance,
                    explanation=(
                        "One or both endpoint values are unavailable or invalid."
                        if status is not FieldResultStatus.COMPUTED
                        else ""
                    ),
                )
            )
    return tuple(outputs)


def _scale(meaning: str, *, units: str | None = None, normalization: str | None = None, bounded: bool = False) -> EvidenceOutputScale:
    """Declare the interpretation of one derived axis-potential channel."""
    if bounded:
        return EvidenceOutputScale(
            meaning=meaning,
            units=units,
            normalization_method=normalization,
            value_range=(0.0, 1.0),
            endpoint_meanings=("none", "complete"),
        )
    return EvidenceOutputScale(meaning=meaning, units=units, normalization_method=normalization)


def axis_angle_gap(angle_a: float, angle_b: float) -> float:
    """Return the minimum angular gap for undirected axes modulo 180 degrees."""
    difference = abs(float(angle_a) - float(angle_b)) % 180.0
    return min(difference, 180.0 - difference)


def _valid_relation_number(value: Any, low: float, high: float) -> bool:
    """Return whether a relation endpoint contains a finite value in range."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
        and low <= float(value) <= high
    )


def build_axis_relation_records(
    observations: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build every unordered pair's independent axis and clarity readings."""
    group_ids = sorted(observations)
    records: list[dict[str, Any]] = []
    for index, group_a in enumerate(group_ids):
        source_a = observations[group_a]
        for group_b in group_ids[index + 1 :]:
            source_b = observations[group_b]
            angle_endpoints_valid = all(
                item.get("axis_status") == "computed"
                and item.get("direction_status") == "computed"
                and _valid_relation_number(item.get("angle"), 0.0, 180.0)
                for item in (source_a, source_b)
            )
            if angle_endpoints_valid:
                gap = axis_angle_gap(float(source_a["angle"]), float(source_b["angle"]))
                angle_status, angle_reason = "computed", None
            else:
                gap = None
                angle_status, angle_reason = "not_available", "one_or_both_endpoint_axes_not_computed"

            clarity_endpoints_valid = all(
                _valid_relation_number(item.get("clarity"), 0.0, 1.0)
                for item in (source_a, source_b)
            )
            if clarity_endpoints_valid:
                clarity_status, clarity_reason = "computed", None
                clarity_similarity = 1.0 - abs(float(source_a["clarity"]) - float(source_b["clarity"]))
                clarity_support = min(float(source_a["clarity"]), float(source_b["clarity"]))
            else:
                clarity_status, clarity_reason = "not_available", "one_or_both_endpoint_values_unavailable_or_invalid"
                clarity_similarity = clarity_support = None

            pair_id = json.dumps([group_a, group_b], ensure_ascii=False, separators=(",", ":"))
            records.append(
                {
                    "pair_id": pair_id,
                    "group_a": group_a,
                    "group_b": group_b,
                    "endpoint_a": dict(source_a),
                    "endpoint_b": dict(source_b),
                    "channels": {
                        "axis_angle_gap": {
                            "status": angle_status,
                            "value": gap,
                            "unit": "degrees",
                            "range": [0.0, 90.0],
                            "reason": angle_reason,
                        },
                        "direction_similarity": {
                            "status": angle_status,
                            "value": cos(radians(gap)) ** 2 if gap is not None else None,
                            "range": [0.0, 1.0],
                            "reason": angle_reason,
                        },
                        "clarity_similarity": {
                            "status": clarity_status,
                            "value": clarity_similarity,
                            "range": [0.0, 1.0],
                            "reason": clarity_reason,
                        },
                        "clarity_support": {
                            "status": clarity_status,
                            "value": clarity_support,
                            "range": [0.0, 1.0],
                            "reason": clarity_reason,
                        },
                    },
                }
            )
    return records


def aggregate_axis_observations(observations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply the clarity-weighted undirected-axis operator to scalar observations.

    This mathematical boundary intentionally carries no IFC, geometry, or source
    identity; package integration adds those facts from real evidence envelopes.
    """
    valid: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item in observations:
        if not isinstance(item, Mapping):
            raise TypeError("axis observations must be mappings")
        group_id = str(item.get("group_id", ""))
        angle = item.get("angle")
        clarity = item.get("clarity")
        status = str(item.get("status", "computed"))
        direction_status = str(item.get("direction_status", "computed"))
        reason = None
        if status != "computed":
            reason = f"channel_status_{status}"
        elif direction_status in {"undefined", "degenerate"} or angle is None:
            reason = "undefined_axis" if direction_status == "undefined" else "degenerate_axis"
        elif direction_status == "invalid":
            reason = "invalid_axis"
        elif isinstance(angle, bool) or not isinstance(angle, (int, float)) or not isfinite(float(angle)):
            reason = "invalid_axis_angle"
        elif isinstance(clarity, bool) or not isinstance(clarity, (int, float)) or not isfinite(float(clarity)) or not 0.0 <= float(clarity) <= 1.0:
            reason = "invalid_clarity"
        if reason is not None:
            excluded.append({"group_id": group_id, "reason": reason, "status": status, "direction_status": direction_status, "angle": angle, "clarity": clarity})
            continue
        valid.append({"group_id": group_id, "angle": float(angle) % 180.0, "clarity": float(clarity), "direction_status": direction_status})
    count = len(valid)
    total = count + len(excluded)
    epsilon = 1e-12
    sum_clarity = sum(item["clarity"] for item in valid)
    positive_count = sum(1 for item in valid if item["clarity"] > 0.0)
    rx = sum(item["clarity"] * cos(radians(2.0 * item["angle"])) for item in valid)
    ry = sum(item["clarity"] * sin(radians(2.0 * item["angle"])) for item in valid)
    resultant = hypot(rx, ry)
    relative_resultant = resultant / sum_clarity if sum_clarity > 0.0 else 0.0
    angle = None if count == 0 or sum_clarity == 0.0 or (relative_resultant <= epsilon) else degrees(0.5 * atan2(ry, rx)) % 180.0
    if angle is not None and abs(angle - 180.0) <= epsilon:
        angle = 0.0
    coherence = resultant / sum_clarity if positive_count >= 2 else None
    support = resultant / count if count else None
    return {
        "angle": angle,
        "aggregate_status": "not_available" if count == 0 else "not_evaluated" if sum_clarity == 0.0 else "computed" if angle is not None else "ambiguous",
        "direction_coherence": coherence,
        "direction_coherence_status": "computed" if coherence is not None else "not_available" if count == 0 else "not_evaluated",
        "clarity_weighted_directional_support": support,
        "support_status": "computed" if count else "not_available",
        "valid": tuple(valid),
        "excluded": tuple(excluded),
        "valid_axis_count": count,
        "total_group_count": total,
        "sum_clarity": sum_clarity,
        "resultant_norm": resultant,
        "positive_clarity_count": positive_count,
        "consensus_status": "no-valid-axis" if count == 0 else "singleton/insufficient-consensus" if count == 1 else "multi-axis",
    }


def aggregate_group_axis_potential_outputs(
    source_envelopes: tuple[FieldResultEnvelope, ...],
) -> tuple[EvidenceOutputChannel, ...]:
    """Aggregate valid overall-group axes with clarity-weighted undirected vectors."""
    if not source_envelopes:
        raise ValueError("source_envelopes must not be empty")
    observations: list[dict[str, Any]] = []
    excluded_details: dict[str, dict[str, Any]] = {}
    for envelope in source_envelopes:
        observation, reason = _axis_observation(envelope)
        if observation is None:
            record = _overall_record(envelope)
            descriptor = record.observation.get("descriptor", {}) if record and isinstance(record.observation, Mapping) else {}
            excluded_details[str(envelope.target["id"])] = {
                "group_id": envelope.target["id"],
                "reason": reason,
                "status": record.status.value if record else "not_available",
                "direction_status": descriptor.get("direction_status"),
                "angle": descriptor.get("angle"),
                "clarity": descriptor.get("strength"),
                "source_ids": tuple(record.source_ids) if record else (),
            }
        else:
            observations.append(observation)
    aggregate = aggregate_axis_observations(observations + list(excluded_details.values()))
    valid = aggregate["valid"]
    excluded = tuple(excluded_details.get(str(item["group_id"]), item) for item in aggregate["excluded"])
    total = aggregate["total_group_count"]
    count = aggregate["valid_axis_count"]
    sum_clarity = aggregate["sum_clarity"]
    resultant = aggregate["resultant_norm"]
    aggregate_angle = aggregate["angle"]
    aggregate_status = FieldResultStatus(aggregate["aggregate_status"])
    coherence_value = aggregate["direction_coherence"]
    coherence_status = FieldResultStatus(aggregate["direction_coherence_status"])
    support_value = aggregate["clarity_weighted_directional_support"]
    support_status = FieldResultStatus(aggregate["support_status"])
    consensus = aggregate["consensus_status"]
    per_group = tuple({**item, "source_ids": next((observation["source_ids"] for observation in observations if observation["group_id"] == item["group_id"]), ())} for item in valid)
    lineage = _lineage(source_envelopes)
    source_ids = tuple(sorted({source_id for envelope in source_envelopes for source_id in envelope.source_ids}))
    common = {
        "scope_status": "diagnostic_only",
        "scope": "all currently supplied authored furniture groups; no membership or candidate is inferred",
        "valid_axis_count": count,
        "total_group_count": total,
        "sum_clarity": sum_clarity,
        "resultant_norm": resultant,
        "per_group": per_group,
        "excluded": tuple(excluded),
        "consensus_status": consensus,
    }
    provenance = {
        "method": "clarity_weighted_undirected_axis_resultant",
        "formula": "R=sum(c_i*(cos(2*theta_i),sin(2*theta_i)))",
        "axis_source": "overall_group_axis",
        "excluded_inputs_do_not_contribute": True,
        "area_weighting": False,
        "algorithm_version": OUTPUT_FUNCTION_VERSION,
        "schema_version": "group-axis-potential-output/v1",
    }
    outputs = [
        EvidenceOutputChannel(
            target=AGGREGATE_TARGET,
            channel="aggregate_direction",
            observation={**common, "angle": aggregate_angle, "axis_convention": "undirected_mod_180"},
            status=aggregate_status,
            scale=_scale("Clarity-weighted aggregate undirected axis direction", units="degrees_mod_180"),
            derived_from=lineage,
            source_ids=source_ids,
            provenance=provenance,
            explanation="No valid axis is available." if count == 0 else "Valid axes have zero total clarity, so direction support was not evaluated." if aggregate["sum_clarity"] == 0.0 else "Resultant cancels to an ambiguous direction." if aggregate_angle is None else "",
        ),
        EvidenceOutputChannel(
            target=AGGREGATE_TARGET,
            channel="direction_coherence",
            observation={**common, "value": coherence_value},
            status=coherence_status,
            scale=_scale("Clarity-weighted undirected direction coherence", units="unitless", normalization="|R|/sum(c_i)", bounded=True),
            derived_from=lineage,
            source_ids=source_ids,
            provenance=provenance,
            explanation="No valid axis is available." if count == 0 else "Fewer than two positive-clarity axes are available for between-group coherence.",
        ),
        EvidenceOutputChannel(
            target=AGGREGATE_TARGET,
            channel="resultant_strength",
            observation={**common, "value": support_value, "alias": "clarity_weighted_directional_support", "interpretation": "directional evidence per valid computed axis; not physical force or temporal stability"},
            status=support_status,
            scale=_scale("Clarity-weighted directional support per valid axis", units="clarity_units", normalization="|R|/N_valid"),
            derived_from=lineage,
            source_ids=source_ids,
            provenance=provenance,
            explanation="No valid axis is available." if count == 0 else "",
        ),
        EvidenceOutputChannel(
            target=AGGREGATE_TARGET,
            channel="coverage",
            observation={
                "valid_axis_count": count,
                "total_group_count": total,
                "coverage": count / total,
                "excluded_axis_count": len(excluded),
                "excluded_group_ids": tuple(item["group_id"] for item in excluded),
            },
            status=FieldResultStatus.COMPUTED,
            scale=_scale("Fraction of source furniture groups with a valid overall axis", units="fraction", normalization="N_valid/N_total", bounded=True),
            derived_from=lineage,
            source_ids=source_ids,
            provenance=provenance,
        ),
        EvidenceOutputChannel(
            target=AGGREGATE_TARGET,
            channel="excluded_axis_diagnostics",
            observation={"excluded": tuple(excluded), "excluded_axis_count": len(excluded)},
            status=FieldResultStatus.COMPUTED,
            scale=_scale("Excluded-axis status and reason inventory"),
            derived_from=lineage,
            source_ids=source_ids,
            provenance=provenance,
        ),
    ]
    return tuple(outputs) + _relation_outputs(source_envelopes) + _source_axis_field_outputs(source_envelopes)


def build_group_axis_potential_package() -> EvidencePackage:
    """Return the reviewed axis-only package execution template."""
    return EvidencePackage(
        package_id=PACKAGE_ID,
        output_function_id=OUTPUT_FUNCTION_ID,
        output_function_version=OUTPUT_FUNCTION_VERSION,
        output_function=aggregate_group_axis_potential_outputs,
    )


__all__ = [
    "aggregate_axis_observations",
    "aggregate_group_axis_potential_outputs",
    "axis_angle_gap",
    "build_axis_relation_records",
    "build_group_axis_potential_package",
]
