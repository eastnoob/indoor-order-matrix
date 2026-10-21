"""Build an auditable inventory of explicitly authored furniture groups."""

from __future__ import annotations

from collections import defaultdict

from .scene_contract import NeutralSceneV2


def _build_authored_group_inventory(scene: NeutralSceneV2) -> dict[str, object]:
    """Resolve authored group references without collapsing shared membership."""
    if not isinstance(scene, NeutralSceneV2):
        raise TypeError("scene must be a NeutralSceneV2")

    sources_by_id = defaultdict(list)
    for source in scene.source_objects:
        sources_by_id[source.id].append(source)

    authored_groups = []
    eligible_groups = []
    excluded_groups = []
    input_audit = []
    member_group_ids = defaultdict(list)

    for group in scene.authored_groups:
        if group.group_role != "furniture_group":
            excluded_groups.append({
                "group_id": group.id,
                "source_id": group.source_id,
                "reason": "non_furniture_group_role",
                "group_role": group.group_role,
                "provenance": dict(group.provenance),
                "member_refs": list(group.member_refs),
            })
            continue

        seen = set()
        unique_member_ids = []
        duplicate_refs = []
        unresolved_refs = []
        ambiguous_refs = []
        for member_ref in group.member_refs:
            if member_ref in seen:
                duplicate_refs.append(member_ref)
                continue
            seen.add(member_ref)
            matches = sources_by_id.get(member_ref, ())
            if len(matches) != 1:
                unresolved_refs.append(member_ref)
                if len(matches) > 1:
                    ambiguous_refs.append(member_ref)
                continue
            unique_member_ids.append(member_ref)

        if not group.member_refs:
            completeness_status = "empty_group"
        elif unique_member_ids and unresolved_refs:
            completeness_status = "partial"
        elif unique_member_ids:
            completeness_status = "computed"
        else:
            completeness_status = "invalid"

        record = {
            "group_id": group.id,
            "source_id": group.source_id,
            "provenance": dict(group.provenance),
            "member_refs": list(group.member_refs),
            "unique_member_ids": unique_member_ids,
            "duplicate_refs": duplicate_refs,
            "unresolved_refs": unresolved_refs,
            "ambiguous_refs": ambiguous_refs,
            "completeness_status": completeness_status,
        }
        authored_groups.append(record)

        if completeness_status == "empty_group":
            excluded_groups.append({
                "group_id": group.id,
                "source_id": group.source_id,
                "reason": "empty_group",
                "group_role": group.group_role,
                "provenance": dict(group.provenance),
                "member_refs": list(group.member_refs),
            })
            input_audit.append(record)
            continue

        eligible_groups.append({
            "id": group.id,
            "group_id": group.id,
            # Geometry consumers must see only uniquely resolved source IDs.
            # Ambiguous and unresolved refs remain available in the audit record.
            "member_refs": list(unique_member_ids),
            "declared_member_refs": list(dict.fromkeys(group.member_refs)),
            "unresolved_member_refs": list(unresolved_refs),
            "provenance": dict(group.provenance),
            "source_id": group.source_id,
            "input_completeness_status": completeness_status,
        })
        for member_id in unique_member_ids:
            member_group_ids[member_id].append(group.id)
        if unresolved_refs or duplicate_refs:
            input_audit.append(record)

    return {
        "authored_groups": authored_groups,
        "eligible_groups": eligible_groups,
        "excluded_groups": excluded_groups,
        "input_audit": input_audit,
        "member_group_ids": dict(member_group_ids),
    }
