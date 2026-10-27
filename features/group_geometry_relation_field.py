"""Adapt authored-group pair observations into immutable field envelopes.

The public target is always a furniture-group pair.  Member-pair geometry is
retained for provenance and replay, but it is explicitly audit-only until a
reviewed group-level aggregation rule is approved.
"""

from __future__ import annotations

import json
from typing import Any

from .field_core import (
    EvidenceChannelRecord,
    FieldQuery,
    FieldResultEnvelope,
    FieldResultStatus,
    build_field_result_cache_identity,
)
from .group_self_description import describe_group_relations


_CHANNELS = {
    "boundary_gap": "Boundary-gap measurements between authored member pairs.",
    "contact": "Contact observations between authored member pairs.",
    "positive_area_overlap": "Positive-area overlap observations between authored member pairs.",
}


def _pair_id(group_a: str, group_b: str) -> str:
    """Encode unordered group IDs without delimiter collisions."""
    return json.dumps(sorted((group_a, group_b)), ensure_ascii=False, separators=(",", ":"))


def _result_status(statuses: list[str]) -> FieldResultStatus:
    """Preserve the availability shape of member observations at channel level."""
    if statuses and all(status == "computed" for status in statuses):
        return FieldResultStatus.COMPUTED
    if any(status == "computed" for status in statuses):
        return FieldResultStatus.PARTIAL
    if statuses and all(status == "invalid" for status in statuses):
        return FieldResultStatus.INVALID
    if statuses and all(status == "not_available" for status in statuses):
        return FieldResultStatus.NOT_AVAILABLE
    return FieldResultStatus.PARTIAL if statuses else FieldResultStatus.NOT_EVALUATED


def build_group_geometry_relation_envelopes(
    scene: Any,
    *,
    query: FieldQuery,
    input_fingerprint: str,
    source_fingerprint: str,
    recipe_fingerprint: str,
    algorithm_version: str,
    schema_version: str,
) -> tuple[FieldResultEnvelope, ...]:
    """Wrap existing IFC-derived member-pair geometry without inferring support."""
    if not isinstance(query, FieldQuery):
        raise TypeError("query must be a FieldQuery")
    if query.plane != scene.context.analysis_plane:
        raise ValueError("query plane must equal the scene analysis plane")

    description = describe_group_relations(scene)
    if description.get("status") != "computed":
        return ()

    declarations = tuple(
        {"channel": name, "polarity": "descriptive", "units": "source_analysis_length"}
        for name in _CHANNELS
    )
    envelopes = []
    for relation in description["group_relations"]:
        group_a, group_b = str(relation["group_a"]), str(relation["group_b"])
        pair_id = _pair_id(group_a, group_b)
        target = {"kind": "furniture_group_pair", "id": pair_id, "identity": pair_id}
        member_observations = sorted(
            relation["member_pair_observations"],
            key=lambda item: _pair_id(str(item["member_a"]), str(item["member_b"])),
        )
        source_ids = sorted(
            {
                str(source_id)
                for observation in member_observations
                for source_id in observation.get("witness", {}).get("source_refs", ())
            }
        )
        channel_records = []
        for channel, fields in (
            ("boundary_gap", ("raw_boundary_gap", "normalized_boundary_gap", "normalization")),
            ("contact", ("contact",)),
            ("positive_area_overlap", ("overlap", "overlap_area")),
        ):
            observations = []
            statuses = []
            channel_sources = set()
            for member_observation in member_observations:
                status = str(member_observation.get("status", "not_available"))
                statuses.append(status)
                witness = member_observation.get("witness", {})
                refs = tuple(sorted(str(value) for value in witness.get("source_refs", ())))
                channel_sources.update(refs)
                observations.append(
                    {
                        "member_pair_id": _pair_id(
                            str(member_observation["member_a"]),
                            str(member_observation["member_b"]),
                        ),
                        "status": status,
                        "reason": member_observation.get("reason"),
                        "values": {field: member_observation.get(field) for field in fields},
                        "witness": witness,
                        "source_refs": refs,
                    }
                )
            channel_records.append(
                EvidenceChannelRecord(
                    channel=channel,
                    required=True,
                    polarity="descriptive",
                    observation={
                        # The public target is the furniture-group pair.  The
                        # raw member observations stay available only as an
                        # audit trail until a reviewed group-level aggregate
                        # rule exists.
                        "group_pair_aggregation": {
                            "status": "deferred",
                            "reason": "group_aggregation_policy_deferred",
                            "value": None,
                        },
                        "member_pairs": tuple(observations),
                        "member_pairs_role": "audit_only",
                    },
                    units=relation.get("unit"),
                    status=_result_status(statuses),
                    source_ids=tuple(sorted(channel_sources)),
                    provenance={
                        "inherits_top_level": True,
                        "method": "existing_member_pair_boundary_observation",
                    },
                    explanation=(
                        _CHANNELS[channel]
                        + " Group-level aggregation is deferred; member-pair values are audit-only."
                    ),
                )
            )

        identity = build_field_result_cache_identity(
            target=target,
            query=query,
            channel_declarations=declarations,
            input_fingerprint=input_fingerprint,
            source_fingerprint=source_fingerprint,
            recipe_fingerprint=recipe_fingerprint,
            algorithm_version=algorithm_version,
            schema_version=schema_version,
        )
        raw_status = {
            "computed": FieldResultStatus.COMPUTED,
            "partial": FieldResultStatus.PARTIAL,
            "invalid": FieldResultStatus.INVALID,
            "not_available": FieldResultStatus.NOT_AVAILABLE,
            "diagnostic_only": FieldResultStatus.AMBIGUOUS,
        }.get(str(relation.get("status")), FieldResultStatus.NOT_EVALUATED)
        envelopes.append(
            FieldResultEnvelope(
                target=target,
                query=query,
                raw_status=raw_status,
                channel_set=tuple(_CHANNELS),
                value={"channels": tuple(channel_records)},
                source_ids=tuple(source_ids),
                provenance={
                    "algorithm_version": algorithm_version,
                    "schema_version": schema_version,
                    "source_fingerprint": source_fingerprint,
                    "method": "describe_group_relations_member_pair_observations",
                    "analysis_frame": relation.get("analysis_frame"),
                    "unit": relation.get("unit"),
                    "tolerance": relation.get("tolerance"),
                    "shared_member_dependency": relation.get("shared_member_dependency"),
                    "relation_status": relation.get("status"),
                    "member_pair_role": "audit_only",
                    "historical_relation_inventory": {
                        "semantic_relation": {
                            "status": relation.get("semantic_channel_status"),
                            "negative_evidence": relation.get("negative_evidence"),
                            "conflicts": relation.get("semantic_conflicts"),
                        },
                        "local_neighborhood": {
                            "status": relation.get("status"),
                            "symmetric": True,
                            "formal_membership_edge": relation.get("formal_membership_edge"),
                        },
                        "position_grammar": {
                            "status": "not_attached",
                            "reason": "scope_is_group_or_region_pattern_evidence",
                        },
                        "column_grid": {
                            "status": "not_attached",
                            "reason": "independent_structural_evidence_scope",
                        },
                    },
                },
                cache_identity=identity,
                explanation=(
                    "Shared membership makes this pair diagnostic-only."
                    if raw_status is FieldResultStatus.AMBIGUOUS
                    else "Member-pair geometry observations are descriptive and do not infer group support."
                ),
            )
        )
    return tuple(sorted(envelopes, key=lambda envelope: envelope.target["id"]))


__all__ = ["build_group_geometry_relation_envelopes"]
