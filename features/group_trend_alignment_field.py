"""Adapt existing group trend descriptors into auditable field envelopes."""

from __future__ import annotations

from typing import Any, Mapping

from .field_core import (
    EvidenceChannelRecord,
    FieldQuery,
    FieldResultEnvelope,
    FieldResultStatus,
    build_field_result_cache_identity,
)
from .group_self_description import describe_group_relations


_CHANNELS = {
    "overall_group_axis": "Area-weighted total-geometry axis descriptor.",
    "layout_axis": "Between-member centroid layout-axis descriptor.",
}

# These descriptors remain in the lower-level description for provenance and
# future recovery, but they are intentionally silent at the evidence-package
# boundary while a furniture group is treated as the smallest public unit.
_SUPPRESSED_CHANNELS = {
    "member_frame": "Four-angle member-frame consensus descriptor.",
    "member_axis": "Two-angle member-axis consensus descriptor.",
}


def _status(value: object) -> FieldResultStatus:
    """Map a group descriptor status without turning undefined direction into missing data."""
    return {
        "computed": FieldResultStatus.COMPUTED,
        "partial": FieldResultStatus.PARTIAL,
        "invalid": FieldResultStatus.INVALID,
        "not_available": FieldResultStatus.NOT_AVAILABLE,
    }.get(str(value), FieldResultStatus.NOT_EVALUATED)


def _source_ids(group: Mapping[str, Any], descriptors: Mapping[str, Any]) -> tuple[str, ...]:
    """Collect stable group/member/binding IDs for source audit."""
    values = {str(group.get("target_id"))}
    for binding in descriptors.get("member_bindings", ()):
        if not isinstance(binding, Mapping):
            continue
        for key in ("source_object_id", "substitute_source_object_id", "substitute_id"):
            value = binding.get(key)
            if value:
                values.add(str(value))
    for member in group.get("member_geometry", ()):
        if isinstance(member, Mapping) and member.get("member_id"):
            values.add(str(member["member_id"]))
    return tuple(sorted(values))


def build_group_trend_alignment_envelopes(
    scene: Any,
    *,
    query: FieldQuery,
    input_fingerprint: str,
    source_fingerprint: str,
    recipe_fingerprint: str,
    algorithm_version: str,
    schema_version: str,
) -> tuple[FieldResultEnvelope, ...]:
    """Wrap current group trend descriptors without composing potential or strength."""
    if not isinstance(query, FieldQuery):
        raise TypeError("query must be a FieldQuery")
    if query.plane != scene.context.analysis_plane:
        raise ValueError("query plane must equal the scene analysis plane")

    description = describe_group_relations(scene)
    if description.get("status") != "computed":
        return ()
    declarations = tuple(
        {"channel": name, "polarity": "descriptive", "units": "degrees_or_coherence"}
        for name in _CHANNELS
    )
    envelopes = []
    for group in description.get("group_geometry", ()):
        descriptors = group.get("trend_descriptors", {})
        status = _status(descriptors.get("status"))
        target_id = str(group["target_id"])
        target = {"kind": "furniture_group", "id": target_id, "identity": target_id}
        channels = []
        for channel, explanation in _CHANNELS.items():
            descriptor = descriptors.get(channel, {"direction_status": "not_available"})
            channels.append(
                EvidenceChannelRecord(
                    channel=channel,
                    required=True,
                    polarity="descriptive",
                    observation={
                        "descriptor": descriptor,
                        "suppressed_member_channels": {
                            name: descriptors.get(name)
                            for name in _SUPPRESSED_CHANNELS
                        },
                        "member_bindings_audit": tuple(descriptors.get("member_bindings", ())),
                        "diagnostic_evidence_audit": descriptors.get("diagnostic_evidence"),
                    },
                    units="degrees_or_coherence",
                    status=status,
                    source_ids=_source_ids(group, descriptors),
                    provenance={"inherits_top_level": True, "method": "existing_group_trend_descriptor"},
                    explanation=explanation + " Geometric descriptor only; not a potential or strength score.",
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
        provenance = {
            "algorithm_version": algorithm_version,
            "schema_version": schema_version,
            "source_fingerprint": source_fingerprint,
            "method": "group_self_description_trend_descriptors",
            "analysis_frame": description.get("analysis_frame"),
            "geometry_status": group.get("geometry_status"),
            "geometry_completeness": group.get("geometry_completeness"),
            "trend_status": descriptors.get("status"),
            "member_bindings_audit": descriptors.get("member_bindings", ()),
            "diagnostic_evidence_audit": descriptors.get("diagnostic_evidence"),
            "suppressed_channels": {
                name: {
                    "status": "suppressed",
                    "reason": "public_unit_is_furniture_group",
                    "descriptor": descriptors.get(name),
                }
                for name in _SUPPRESSED_CHANNELS
            },
        }
        explanation = (
            "Group-level trend descriptors remain separate descriptive channels; "
            "member-frame and member-axis channels are suppressed at this package boundary. "
            "No channel composition, potential, membership, strength, candidate, or winner is produced."
        )
        envelopes.append(
            FieldResultEnvelope(
                target=target,
                query=query,
                raw_status=status,
                channel_set=tuple(_CHANNELS),
                value={"channels": tuple(channels)},
                source_ids=_source_ids(group, descriptors),
                provenance=provenance,
                cache_identity=identity,
                explanation=explanation if status is not FieldResultStatus.COMPUTED else "",
            )
        )
    return tuple(sorted(envelopes, key=lambda item: item.target["id"]))


__all__ = ["build_group_trend_alignment_envelopes"]
