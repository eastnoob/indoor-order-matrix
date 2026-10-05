"""Reduce synthetic lifecycle ties into auditable, conflict-preserving outcomes."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _validate_events(events: list[dict[str, Any]]) -> None:
    """Validate stable IDs, event keys, and canonical timestamps before sorting."""
    seen: set[str] = set()
    for event in events:
        event_id = event["event_id"]
        if not isinstance(event_id, str) or not event_id or not event_id.isascii() or event_id in seen:
            raise ValueError(f"invalid or duplicate event_id: {event_id!r}")
        seen.add(event_id)
        timestamp = event["occurred_at"]
        parsed = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != timestamp:
            raise ValueError(f"non-canonical UTC timestamp: {timestamp}")
        if type(event["sequence"]) is not int or event["sequence"] < 0:
            raise ValueError(f"invalid event sequence for {event_id}")


def _semantic_signature(event: dict[str, Any]) -> str:
    """Return canonical event meaning while excluding ordering and provenance IDs."""
    semantic = {
        key: value
        for key, value in event.items()
        if key not in {"event_id", "occurred_at", "sequence", "provenance"}
    }
    return json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _conflict_class(events: list[dict[str, Any]], active_versions: set[str]) -> str:
    """Name the bounded conflict class represented by one relation tie."""
    event_types = {event["event_type"] for event in events}
    stale_targets = {
        event["target_candidate_version_id"]
        for event in events
        if event.get("target_candidate_version_id") is not None
        and event["target_candidate_version_id"] not in active_versions
    }
    if stale_targets and event_types & {"confirm_candidate", "replace_candidate_version"}:
        return "replacement_confirmation_stale_or_inactive_target"
    if event_types == {"confirm_candidate"} and len(
        {event.get("target_candidate_version_id") for event in events}
    ) > 1:
        return "same_key_incompatible_candidate_confirmations"
    if event_types == {"assign_authored_domain"} and len(
        {event.get("authored_domain_id") for event in events}
    ) > 1:
        return "same_key_incompatible_authored_domain_assignments"
    return "same_key_contradictory_events"


def _reduce_case(case: dict[str, Any]) -> dict[str, Any]:
    """Group tied events before effects, retaining every original event record."""
    events = case["events"]
    _validate_events(events)
    ordered = sorted(events, key=lambda item: (item["occurred_at"], item["sequence"], item["event_id"]))
    active_versions = set(case["initial_state"]["active_candidate_versions"])
    tie_groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for event in ordered:
        tie_groups.setdefault((event["occurred_at"], event["sequence"]), []).append(event)

    outcomes: list[dict[str, Any]] = []
    for tie_events in tie_groups.values():
        by_relation: dict[str, list[dict[str, Any]]] = {}
        for event in tie_events:
            by_relation.setdefault(event["relation_key"], []).append(event)
        # A complete tied relation is classified before applying anything, so lexical order cannot decide truth.
        for relation_key, relation_events in by_relation.items():
            signatures = {_semantic_signature(event) for event in relation_events}
            stale = any(
                event.get("target_candidate_version_id") is not None
                and event["target_candidate_version_id"] not in active_versions
                for event in relation_events
            )
            if stale or len(signatures) > 1:
                outcome = "unresolved_conflict"
                conflict_class = _conflict_class(relation_events, active_versions)
                effective_count = 0
                downstream = "blocked_unresolved_conflict"
            elif len(relation_events) > 1:
                outcome = "applied_idempotently"
                conflict_class = None
                effective_count = 1
                downstream = "not_promoted_by_this_evidence"
            else:
                outcome = "applied"
                conflict_class = None
                effective_count = 1
                downstream = "not_promoted_by_this_evidence"
            outcomes.append(
                {
                    "relation_key": relation_key,
                    "outcome": outcome,
                    "conflict_class": conflict_class,
                    "event_ids": [event["event_id"] for event in relation_events],
                    "preserved_event_ids": [event["event_id"] for event in relation_events],
                    "preserved_event_records": relation_events,
                    "effective_event_count": effective_count,
                    "lexical_winner_event_id": None,
                    "downstream_promotion": downstream,
                }
            )
    return {
        "case_id": case["case_id"],
        "ordered_event_ids": [event["event_id"] for event in ordered],
        "tie_order_groups": [
            {
                "occurred_at": key[0],
                "sequence": key[1],
                "event_ids": [event["event_id"] for event in group],
            }
            for key, group in tie_groups.items()
        ],
        "relation_outcomes": outcomes,
    }


def main() -> int:
    """Read the adjacent synthetic fixtures and emit deterministic JSON."""
    fixture_path = Path(__file__).with_name("fixtures.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = {
        "artifact_type": "d6_lifecycle_conflict_preservation_probe_v1",
        "cases": [_reduce_case(case) for case in fixture["cases"]],
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
