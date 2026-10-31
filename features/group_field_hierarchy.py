"""Exact circular hierarchy derivation for the group axis evidence package."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from math import atan2, cos, degrees, hypot, isfinite, radians, sin
from typing import Any, Mapping

from .field_core import (
    EvidenceChannelReference,
    EvidenceOutputChannel,
    EvidenceOutputScale,
    FieldResultEnvelope,
    FieldResultStatus,
)


RECIPE_ID = "source-axis-circular-arc-lt90-v1"
OUTPUT_FUNCTION_VERSION = "axis-with-hierarchy-v1"
OUTPUT_SCHEMA = "group-axis-field-hierarchy-output/v1"
_DEGREE_90 = Fraction(90)
_DEGREE_180 = Fraction(180)


def _json(value: Any) -> str:
    """Serialize nested values deterministically for logical identities."""
    def plain(item: Any) -> Any:
        """Convert immutable containers and exact fractions to JSON values."""
        if isinstance(item, Mapping):
            return {str(key): plain(value) for key, value in sorted(item.items(), key=lambda pair: str(pair[0]))}
        if isinstance(item, (tuple, list)):
            return [plain(value) for value in item]
        if isinstance(item, Fraction):
            return {"numerator": item.numerator, "denominator": item.denominator}
        return item

    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _pair(value: Fraction) -> list[int]:
    """Return a reduced numerator/denominator pair without float conversion."""
    value = Fraction(value)
    return [value.numerator, value.denominator]


def _float(value: Fraction) -> float:
    """Return a display float for an exact value."""
    return float(value)


def _status(value: Any) -> str:
    """Normalize a retained raw status to its wire value."""
    return value.value if isinstance(value, FieldResultStatus) else str(value)


def _scale(meaning: str, units: str | None = None, bounded: bool = False) -> EvidenceOutputScale:
    """Describe hierarchy output units and optional support bounds."""
    return EvidenceOutputScale(
        meaning=meaning,
        units=units,
        value_range=(0.0, 1.0) if bounded else None,
        endpoint_meanings=("none", "complete") if bounded else None,
    )


def _source_axis(envelope: FieldResultEnvelope) -> dict[str, Any] | None:
    """Read one admitted overall axis while preserving invalid-source exclusion."""
    record = next(
        (item for item in (envelope.value["channels"] if envelope.value else ()) if item.channel == "overall_group_axis"),
        None,
    )
    descriptor = record.observation.get("descriptor", {}) if record and isinstance(record.observation, Mapping) else {}
    angle = descriptor.get("angle")
    clarity = descriptor.get("strength")
    reason = None
    if record is None:
        reason = "missing_overall_group_axis"
    elif record.status is not FieldResultStatus.COMPUTED:
        reason = f"channel_status_{_status(record.status)}"
    elif descriptor.get("direction_status") in {"undefined", "degenerate"} or angle is None:
        reason = "undefined_axis" if descriptor.get("direction_status") == "undefined" else "degenerate_axis"
    elif descriptor.get("direction_status") == "invalid":
        reason = "invalid_axis"
    elif isinstance(angle, bool) or not isinstance(angle, (int, float)) or not isfinite(float(angle)):
        reason = "invalid_axis_angle"
    elif isinstance(clarity, bool) or not isinstance(clarity, (int, float)) or not isfinite(float(clarity)) or not 0.0 <= float(clarity) <= 1.0:
        reason = "invalid_clarity"
    if reason:
        return {"group_id": envelope.target["identity"], "reason": reason, "status": _status(record.status) if record else "not_available"}
    theta = float(angle) % 180.0
    # Binary64 modulo can round a tiny negative angle to the excluded endpoint.
    if theta == 180.0 or theta == 0.0:
        theta = 0.0
    return {
        "group_id": envelope.target["identity"],
        "angle": theta,
        "theta": Fraction.from_float(theta),
        "clarity": float(clarity),
        "status": "computed",
        "result_identity": envelope.cache_identity["identity"],
    }


def _lineage(envelopes: tuple[FieldResultEnvelope, ...]) -> tuple[EvidenceChannelReference, ...]:
    """Reference the real source-axis channel for every derived output."""
    return tuple(
        EvidenceChannelReference.from_envelope(envelope, "overall_group_axis")
        for envelope in envelopes
        if "overall_group_axis" in envelope.channel_set
    )


def _family_id(namespace: str, query: Any, anchors: tuple[str, ...]) -> str:
    """Build the namespace/query/anchor logical family identity."""
    payload = {"namespace": namespace, "query": query, "recipe": RECIPE_ID, "anchors": anchors}
    digest = hashlib.sha256(_json(payload).encode()).hexdigest()
    return f"axis-family:{digest}"


def _family_target(family_id: str) -> dict[str, str]:
    """Return a stable family target mapping."""
    return {"kind": "furniture_group_axis_family", "id": family_id, "identity": family_id}


def _output(
    target: Mapping[str, str],
    channel: str,
    observation: Mapping[str, Any],
    status: FieldResultStatus,
    scale: EvidenceOutputScale,
    lineage: tuple[EvidenceChannelReference, ...],
    source_ids: tuple[str, ...],
    provenance: Mapping[str, Any],
    explanation: str = "",
) -> EvidenceOutputChannel:
    """Construct a validated additive hierarchy channel."""
    if status is not FieldResultStatus.COMPUTED and not explanation:
        explanation = "Hierarchy evidence is incomplete for the supplied source scope."
    return EvidenceOutputChannel(
        target=dict(target),
        channel=channel,
        observation=dict(observation),
        status=status,
        scale=scale,
        derived_from=lineage,
        source_ids=source_ids,
        provenance=dict(provenance),
        explanation=explanation,
    )


def _profile(rows: Mapping[str, Mapping[str, Any]], expected_ids: tuple[str, ...]) -> tuple[dict[str, Any], FieldResultStatus]:
    """Summarize known family rows over a declared scope domain."""
    known = [rows[group_id] for group_id in expected_ids if rows[group_id]["status"] == "computed"]
    values = [float(item["value"]) for item in known]
    expected = len(expected_ids)
    known_count = len(known)
    coverage = known_count / expected if expected else None
    # Cell coverage preserves missing leaf evidence even when a family maximum is known.
    leaf_cells = [cell for group_id in expected_ids for cell in rows[group_id]["leaf_cells"]]
    known_leaf_count = sum(cell["status"] == "computed" for cell in leaf_cells)
    mass = sum(values) if values else None
    square = sum(value * value for value in values)
    n_eff = mass * mass / square if square else None
    lower_sum = sum(float(rows[group_id]["lower"]) for group_id in expected_ids)
    upper_sum = sum(float(rows[group_id]["upper"]) for group_id in expected_ids)
    mean = sum(values) / known_count if known_count else None
    status = (
        FieldResultStatus.NOT_AVAILABLE
        if expected == 0 or known_count == 0
        else FieldResultStatus.COMPUTED
        if known_count == expected
        else FieldResultStatus.PARTIAL
    )
    return {
        "row_ids": list(expected_ids),
        "values": {group_id: rows[group_id]["value"] for group_id in expected_ids},
        "status_counts": {
            state: sum(rows[group_id]["status"] == state for group_id in expected_ids)
            for state in ("computed", "partial", "not_available", "invalid", "outside", "ambiguous", "not_evaluated")
        },
        "known_count": known_count,
        "expected_count": expected,
        "coverage": coverage,
        "known_leaf_cell_count": known_leaf_count,
        "expected_leaf_cell_count": len(leaf_cells),
        "leaf_cell_coverage": known_leaf_count / len(leaf_cells) if leaf_cells else None,
        "leaf_cell_status_counts": {
            state: sum(cell["status"] == state for cell in leaf_cells)
            for state in ("computed", "partial", "not_available", "invalid", "outside", "ambiguous", "not_evaluated")
        },
        "known_mean": mean,
        "mean_bounds": [lower_sum / expected, upper_sum / expected] if expected else None,
        "support_mass": mass,
        "support_mass_bounds": [lower_sum, upper_sum] if expected else None,
        "n_eff": n_eff,
        "missing_count": expected - known_count,
        "interpretation": "known rows only" if status is FieldResultStatus.PARTIAL else "full declared scope",
    }, status


def build_axis_field_hierarchy(
    source_envelopes: tuple[FieldResultEnvelope, ...],
    source_axis_outputs: tuple[EvidenceOutputChannel, ...],
    *,
    scene_namespace: str,
) -> tuple[EvidenceOutputChannel, ...]:
    """Build exact circular direction families and additive support diagnostics.

    The helper consumes the already computed source-axis cells and references only
    real envelope channels in ``derived_from``. Exact ``Fraction`` values are used
    for topology/events; source support values remain their original floats.
    """
    if not isinstance(scene_namespace, str) or not scene_namespace.strip():
        raise ValueError("scene_namespace must be a non-empty string")
    envelopes = tuple(source_envelopes)
    if not envelopes:
        raise ValueError("source_envelopes must not be empty")
    target_ids = [str(envelope.target["identity"]) for envelope in envelopes]
    if len(set(target_ids)) != len(target_ids):
        raise ValueError("source_envelopes cannot contain duplicate group identities")
    axes = {envelope.target["identity"]: _source_axis(envelope) for envelope in envelopes}
    group_ids = tuple(sorted(axes))
    lineage = _lineage(envelopes)
    source_ids = tuple(sorted({source_id for envelope in envelopes for source_id in envelope.source_ids}))
    query = envelopes[0].query
    query_payload = {
        "domain_id": query.domain_id,
        "frame": query.frame,
        "plane": query.plane,
        "height_band": query.height_band,
        "demand": query.demand,
        "tolerance": query.tolerance,
        "revision": query.revision,
    }
    provenance = {
        "algorithm_version": OUTPUT_FUNCTION_VERSION,
        "schema_version": OUTPUT_SCHEMA,
        "recipe_id": RECIPE_ID,
        "scene_namespace": scene_namespace,
        "numeric_policy": "Fraction.from_float for topology/events; source float support preserved",
    }

    # Reuse the exact source-axis output rows, keyed by field and target group.
    cells: dict[tuple[str, str], Mapping[str, Any]] = {}
    cell_ids: dict[tuple[str, str], str] = {}
    fields: dict[str, str] = {}
    source_refs: dict[tuple[str, str], tuple[str, ...]] = {}
    for output in source_axis_outputs:
        if output.channel != "axis_field_support":
            continue
        observation = output.observation
        field_id = str(observation["field_id"])
        target_id = str(observation["target_group_id"])
        cells[(field_id, target_id)] = observation
        cell_ids[(field_id, target_id)] = str(output.target["identity"])
        fields[field_id] = str(observation["anchor_group_id"])
        source_refs[(field_id, target_id)] = tuple(
            ref.result_identity for ref in output.derived_from
        )
    field_by_anchor = {anchor: field_id for field_id, anchor in fields.items()}
    # Exclusion records retain their raw channel status, including computed.
    valid_axes = [item for item in axes.values() if item and item.get("status") == "computed" and "theta" in item and not item.get("reason")]
    admitted_axis_ids = {item["group_id"] for item in valid_axes}
    valid_axes.sort(key=lambda item: (item["theta"], item["group_id"]))
    classes: list[dict[str, Any]] = []
    for item in valid_axes:
        if classes and classes[-1]["theta"] == item["theta"]:
            classes[-1]["anchors"].append(item["group_id"])
        else:
            classes.append({"theta": item["theta"], "angle": item["angle"], "anchors": [item["group_id"]]})
    for item in classes:
        item["anchors"] = tuple(sorted(item["anchors"]))
        item["leaf_ids"] = tuple(field_by_anchor.get(anchor, anchor) for anchor in item["anchors"])

    family_candidates: dict[tuple[str, ...], dict[str, Any]] = {}
    n = len(classes)
    for start in range(n):
        for length in range(1, n + 1):
            end = start + length - 1
            end_angle = classes[end % n]["theta"] + _DEGREE_180 * (end // n)
            birth = end_angle - classes[start]["theta"]
            if length == n:
                death = _DEGREE_90
            else:
                left_index = start - 1
                left_angle = classes[left_index % n]["theta"] + _DEGREE_180 * (left_index // n)
                right_index = end + 1
                right_angle = classes[right_index % n]["theta"] + _DEGREE_180 * (right_index // n)
                death = min(end_angle - left_angle, right_angle - classes[start]["theta"], _DEGREE_90)
            if birth >= death:
                continue
            selected = tuple(sorted({anchor for index in range(start, end + 1) for anchor in classes[index % n]["anchors"]}))
            candidate = {
                "anchors": selected,
                "class_indices": tuple(index % n for index in range(start, end + 1)),
                "birth": birth,
                "death": death,
                "start": classes[start]["theta"],
            }
            key = (birth, classes[start]["theta"], selected)
            existing = family_candidates.get(selected)
            if existing is None or key < (existing["birth"], existing["start"], existing["anchors"]):
                family_candidates[selected] = candidate

    families: dict[str, dict[str, Any]] = {}
    for anchors, candidate in sorted(family_candidates.items(), key=lambda pair: (pair[1]["birth"], pair[1]["start"], pair[0])):
        family_id = _family_id(scene_namespace, query_payload, anchors)
        families[family_id] = {**candidate, "family_id": family_id, "leaf_ids": tuple(field_by_anchor.get(anchor, anchor) for anchor in anchors)}
    by_anchors = {family["anchors"]: family for family in families.values()}

    # Direct parent edges are the immediate contiguous one-class supersets.
    for family in families.values():
        family["parent_ids"] = []
        anchor_set = set(family["anchors"])
        class_indices = set(family["class_indices"])
        for index in class_indices:
            for neighbor in ((index - 1) % n, (index + 1) % n):
                parent_classes = class_indices | {neighbor}
                parent_anchors = tuple(sorted({anchor for class_index in parent_classes for anchor in classes[class_index]["anchors"]}))
                parent = by_anchors.get(parent_anchors)
                if parent and set(parent["anchors"]) > anchor_set:
                    family["parent_ids"].append(parent["family_id"])
        family["parent_ids"] = sorted(set(family["parent_ids"]))

    outputs: list[EvidenceOutputChannel] = []
    event_values = sorted({value for family in families.values() for value in (family["birth"], family["death"])})
    event_records = [
        {
            "value_exact": _pair(value),
            "value": _float(value),
            "birth_family_ids": sorted(family["family_id"] for family in families.values() if family["birth"] == value),
            "death_family_ids": sorted(family["family_id"] for family in families.values() if family["death"] == value),
        }
        for value in event_values
    ]
    # Direction aliases are emitted once per exact class.
    for index, item in enumerate(classes):
        target_id = f"axis-direction:{hashlib.sha256(_json([scene_namespace, item['anchors'], _pair(item['theta'])]).encode()).hexdigest()}"
        outputs.append(_output(
            {"kind": "furniture_group_axis_direction_class", "id": target_id, "identity": target_id},
            "axis_direction_aliases",
            {"theta": item["angle"], "theta_exact": _pair(item["theta"]), "anchor_group_ids": list(item["anchors"]), "leaf_field_ids": list(item["leaf_ids"]), "class_index": index, "alias_only": True},
            FieldResultStatus.COMPUTED,
            _scale("Exact undirected source-axis direction class", "degrees_mod_180"),
            lineage,
            source_ids,
            provenance,
        ))

    family_rows: dict[str, dict[str, dict[str, Any]]] = {}
    for family in families.values():
        rows: dict[str, dict[str, Any]] = {}
        leaf_refs = []
        for group_id in group_ids:
            known_values = []
            members = []
            for leaf_id in family["leaf_ids"]:
                cell = cells.get((leaf_id, group_id))
                if cell is None:
                    members.append({"cell_id": None, "status": "not_available", "value": None, "reason": "missing_source_axis_cell"})
                    continue
                state = str(cell.get("status", "not_available"))
                value = cell.get("axis_field_support")
                members.append({"cell_id": cell_ids[(leaf_id, group_id)], "status": state, "value": value, "reason": cell.get("reason")})
                if state == "computed" and isinstance(value, (int, float)):
                    known_values.append(float(value))
                leaf_refs.extend(source_refs.get((leaf_id, group_id), ()))
            lower = max(known_values) if known_values else 0.0
            upper = max(lower, 1.0 if len(known_values) < len(family["leaf_ids"]) else lower)
            value = max(known_values) if len(known_values) == len(family["leaf_ids"]) and known_values else None
            state = FieldResultStatus.COMPUTED if value is not None else FieldResultStatus.PARTIAL if known_values else FieldResultStatus.NOT_AVAILABLE
            rows[group_id] = {"value": value, "known_max": max(known_values) if known_values else None, "lower": lower, "upper": upper, "status": state.value, "leaf_cells": members}
        family_rows[family["family_id"]] = rows

    for family in families.values():
        family_id = family["family_id"]
        target = _family_target(family_id)
        rows = family_rows[family_id]
        leaf_refs = tuple(sorted(set(family["leaf_ids"])))
        definition = {
            "family_id": family_id,
            "anchor_group_ids": list(family["anchors"]),
            "leaf_field_ids": list(family["leaf_ids"]),
            "class_indices": list(family["class_indices"]),
            "direction_classes": [
                {
                    "class_index": index,
                    "theta": classes[index]["angle"],
                    "theta_exact": _pair(classes[index]["theta"]),
                    "anchor_group_ids": list(classes[index]["anchors"]),
                    "leaf_field_ids": list(classes[index]["leaf_ids"]),
                }
                for index in family["class_indices"]
            ],
            "birth": _float(family["birth"]),
            "death": _float(family["death"]),
            "birth_exact": _pair(family["birth"]),
            "death_exact": _pair(family["death"]),
            "scale_persistence": _float((family["death"] - family["birth"]) / _DEGREE_90),
            "scale_persistence_exact": _pair((family["death"] - family["birth"]) / _DEGREE_90),
            "interval": "[birth,death)",
            "parent_ids": list(family["parent_ids"]),
            "singleton_anchor": len(family["anchors"]) == 1,
            "two_anchor": len(family["anchors"]) == 2,
            "generation_complete_over_available_axes": True,
            "events": event_records,
        }
        family_provenance = {**provenance, "leaf_output_refs": list(leaf_refs), "child_family_refs": list(family["parent_ids"])}
        outputs.append(_output(target, "axis_family_definition", definition, FieldResultStatus.COMPUTED, _scale("Exact circular direction-family lifespan", "degrees"), lineage, source_ids, family_provenance))
        for group_id, row in rows.items():
            cell_target_id = f"{family_id}:group:{group_id}"
            outputs.append(_output(
                {"kind": "furniture_group_axis_family_cell", "id": cell_target_id, "identity": cell_target_id},
                "axis_family_support",
                {"family_id": family_id, "group_id": group_id, "J": row["value"], "support": row["value"], **row},
                FieldResultStatus(row["status"]),
                _scale("Maximum support over the family's actual leaf axes", "unitless", True),
                lineage,
                source_ids,
                {**provenance, "leaf_output_refs": list(leaf_refs)},
                "All required leaf cells are unavailable." if row["status"] == "not_available" else "Some required leaf cells are unavailable." if row["status"] == "partial" else "",
            ))
        full_profile, full_status = _profile(rows, group_ids)
        non_anchor_ids = tuple(group_id for group_id in group_ids if group_id not in family["anchors"])
        non_profile, non_status = _profile(rows, non_anchor_ids)
        profile_status = FieldResultStatus.COMPUTED if full_status is FieldResultStatus.COMPUTED and non_status is FieldResultStatus.COMPUTED else FieldResultStatus.PARTIAL if full_status is not FieldResultStatus.NOT_AVAILABLE or non_status is not FieldResultStatus.NOT_AVAILABLE else FieldResultStatus.NOT_AVAILABLE
        outputs.append(_output(target, "axis_family_profile", {"family_id": family_id, "domains": {"full_scope": full_profile, "non_anchor": non_profile}}, profile_status, _scale("Full and non-anchor family support profiles", "unitless"), lineage, source_ids, family_provenance, "One or more profile domains are incomplete."))

        # Q_F is descriptive only and is computed from known rows with valid target axes.
        q_rows = {group_id: rows[group_id] for group_id in group_ids if rows[group_id]["status"] == "computed" and group_id in admitted_axis_ids}
        rx = sum(float(row["value"]) * cos(radians(2.0 * axes[group_id]["angle"])) for group_id, row in q_rows.items())
        ry = sum(float(row["value"]) * sin(radians(2.0 * axes[group_id]["angle"])) for group_id, row in q_rows.items())
        mass = sum(float(row["value"]) for row in q_rows.values())
        positive_ids = [group_id for group_id, row in q_rows.items() if float(row["value"]) > 0.0]
        anchor_mass = sum(float(row["value"]) for group_id, row in q_rows.items() if group_id in family["anchors"])
        norm = hypot(rx, ry)
        direction = None if not mass else degrees(0.5 * atan2(ry, rx)) % 180.0 if norm / mass > 1e-12 else None
        # Zero-valued known rows count toward coverage but cannot supply a direction.
        direction_status = "not_available" if not mass else "ambiguous" if direction is None else "anchor_only" if all(group_id in family["anchors"] for group_id in positive_ids) else "computed"
        dir_status = FieldResultStatus.NOT_AVAILABLE if not mass else FieldResultStatus.AMBIGUOUS if direction_status == "ambiguous" else FieldResultStatus.COMPUTED
        outputs.append(_output(target, "axis_family_direction", {"family_id": family_id, "Q": [rx, ry], "direction": direction, "direction_status": direction_status, "coherence": norm / mass if mass else None, "support_mass": mass if q_rows else None, "known_count": len(q_rows), "expected_count": len(group_ids), "coverage": len(q_rows) / len(group_ids) if group_ids else 0.0, "anchor_group_ids": list(family["anchors"]), "anchors_included": any(group_id in family["anchors"] for group_id in q_rows), "anchor_contribution_mass": anchor_mass if q_rows else None, "anchor_contribution_fraction": anchor_mass / mass if mass else None, "positive_contribution_group_ids": positive_ids}, dir_status, _scale("Read-only support-weighted family direction", "degrees_mod_180"), lineage, source_ids, family_provenance, "No known family support rows have valid source axes." if not q_rows else "No positive family support is available for a direction." if not mass else "Known family support vectors cancel." if direction_status == "ambiguous" else ""))

    # Leaf-pair descriptive relation channels.
    anchor_groups = tuple(sorted(anchor for item in classes for anchor in item["anchors"]))
    for index, group_a in enumerate(anchor_groups):
        for group_b in anchor_groups[index + 1 :]:
            field_a, field_b = field_by_anchor.get(group_a), field_by_anchor.get(group_b)
            rows = []
            for group_id in group_ids:
                if group_id in {group_a, group_b}:
                    continue
                left, right = cells.get((field_a, group_id)), cells.get((field_b, group_id))
                if left and right and left.get("status") == right.get("status") == "computed":
                    rows.append({"group_id": group_id, "difference": abs(float(left["axis_field_support"]) - float(right["axis_field_support"]))})
            expected = len(group_ids) - 2
            known = len(rows)
            relation_status = FieldResultStatus.NOT_AVAILABLE if known == 0 else FieldResultStatus.COMPUTED if known == expected else FieldResultStatus.PARTIAL
            mean = sum(item["difference"] for item in rows) / known if known else None
            target_id = f"axis-field-relation:{group_a}:{group_b}"
            outputs.append(_output({"kind": "furniture_group_axis_field_pair", "id": target_id, "identity": target_id}, "axis_field_relation", {"group_a": group_a, "group_b": group_b, "rows": rows, "expected_count": expected, "known_count": known, "coverage": known / expected if expected else None, "profile_l1_mean": mean, "profile_similarity": 1.0 - mean if mean is not None else None}, relation_status, _scale("Descriptive difference between source-axis support profiles", "unitless", True), lineage, source_ids, provenance, "No common known profile rows." if known == 0 else "Partial common profile coverage." if relation_status is FieldResultStatus.PARTIAL else ""))

    # Parent residuals compare child support with the parent's newly added leaves.
    for child in families.values():
        for parent_id in child["parent_ids"]:
            parent = families[parent_id]
            complement = tuple(leaf for leaf in parent["leaf_ids"] if leaf not in child["leaf_ids"])
            rows = []
            expected_ids = tuple(group_id for group_id in group_ids if group_id not in parent["anchors"])
            for group_id in expected_ids:
                child_row = family_rows[child["family_id"]][group_id]
                parent_values = [cells.get((leaf, group_id)) for leaf in complement]
                known_parent = [float(cell["axis_field_support"]) for cell in parent_values if cell and cell.get("status") == "computed"]
                complement_lower = max(known_parent) if known_parent else 0.0
                complement_upper = max(complement_lower, 1.0 if len(known_parent) < len(complement) else complement_lower)
                residual_lower = max(0.0, float(child_row["lower"]) - complement_upper)
                residual_upper = max(0.0, float(child_row["upper"]) - complement_lower)
                if child_row["status"] == "computed" and len(known_parent) == len(complement):
                    residual = max(0.0, float(child_row["value"]) - max(known_parent, default=0.0))
                    state = "computed"
                else:
                    residual = None
                    state = "not_available" if not known_parent else "partial"
                rows.append({"group_id": group_id, "value": residual, "status": state, "lower": residual_lower, "upper": residual_upper, "complement_lower": complement_lower, "complement_upper": complement_upper})
            known = [row for row in rows if row["status"] == "computed"]
            residual_mass = sum(float(row["value"]) for row in known) if known else None
            status = FieldResultStatus.NOT_AVAILABLE if not known else FieldResultStatus.COMPUTED if len(known) == len(rows) else FieldResultStatus.PARTIAL
            target_id = f"axis-family-residual:{child['family_id']}:{parent_id}"
            outputs.append(_output({"kind": "furniture_group_axis_family_edge", "id": target_id, "identity": target_id}, "axis_family_residual", {"child_family_id": child["family_id"], "parent_family_id": parent_id, "complement_leaf_field_ids": list(complement), "rows": rows, "expected_count": len(rows), "known_count": len(known), "coverage": len(known) / len(rows) if rows else None, "known_residual_mass": residual_mass, "known_residual_mean": residual_mass / len(known) if known else None}, status, _scale("Residual support from child leaves against parent complement", "unitless", True), lineage, source_ids, provenance, "No comparable parent-complement rows." if not known else "Partial parent-complement coverage." if status is FieldResultStatus.PARTIAL else ""))

    excluded = [item for group_id, item in axes.items() if group_id not in admitted_axis_ids]
    scope_status = FieldResultStatus.NOT_AVAILABLE if not valid_axes else FieldResultStatus.COMPUTED if not excluded else FieldResultStatus.PARTIAL
    outputs.append(_output({"kind": "furniture_group_axis_hierarchy_scope", "id": "axis-family-scope", "identity": "axis-family-scope"}, "axis_family_scope_diagnostics", {"scope_group_ids": list(group_ids), "scope_group_count": len(group_ids), "admitted_anchor_ids": [item["group_id"] for item in valid_axes], "excluded_anchors": excluded, "axis_coverage": len(valid_axes) / len(group_ids) if group_ids else 0.0, "family_count": len(families), "complete_over_available_axes": True, "scope_evidence_status": scope_status.value}, scope_status, _scale("Hierarchy scope and admitted-axis diagnostics", "count"), lineage, source_ids, provenance, "No usable source axes are available for hierarchy enumeration." if not valid_axes else "Some source axes were excluded from hierarchy enumeration." if excluded else ""))
    return tuple(outputs)
