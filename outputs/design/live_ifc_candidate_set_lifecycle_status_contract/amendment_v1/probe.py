"""Deterministically reduce the bounded lifecycle amendment fixtures."""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import Any


def _validate_timestamp(value: str) -> None:
    """Require canonical second-precision UTC timestamps for lexical ordering."""
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError(f"non-canonical UTC timestamp: {value}")


def _event_order(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort events by the declared timestamp, sequence, and stable ID keys."""
    seen_ids: set[str] = set()
    for event in events:
        event_id = event["event_id"]
        if type(event_id) is not str or not event_id:
            raise ValueError("event_id must be a non-empty string")
        if event_id in seen_ids:
            raise ValueError(f"duplicate event_id: {event_id}")
        if not event_id.isascii():
            raise ValueError(f"event_id must be ASCII for stable tie-breaking: {event_id}")
        if type(event["sequence"]) is not int:
            raise ValueError("event sequence must be an integer")
        _validate_timestamp(event["occurred_at"])
        seen_ids.add(event_id)
    # The stable ID tie-break makes replay reproducible without claiming event authority.
    return sorted(events, key=lambda event: (event["occurred_at"], event["sequence"], event["event_id"]))


def _assignment(status: str, domain_id: str | None, source_domain_ids: list[str], reason: str | None) -> dict[str, Any]:
    """Build the separate authored-domain assignment record."""
    return {
        "status": status,
        "domain_id": domain_id,
        "source_domain_ids": list(source_domain_ids),
        "reason": reason,
    }


def _snapshot(state: dict[str, Any], event_id: str) -> dict[str, Any]:
    """Capture the active version and assignment after one replayed event."""
    active_id = state["active_candidate_version_id"]
    active = next(version for version in state["candidate_versions"] if version["candidate_version_id"] == active_id)
    return {
        "event_id": event_id,
        "active_candidate_version_id": active_id,
        "active_lifecycle_state": active["lifecycle_state"],
        "active_user_confirmed": active["user_confirmed"],
        "active_evidence_state": active["evidence_state"],
        "assignment": copy.deepcopy(state["authored_domain_assignment"]),
    }


def _apply_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    """Apply one explicit event without coupling assignment and confirmation."""
    event_type = event["event_type"]
    if event_type == "assign_authored_domain":
        if event["actor_type"] != "user" or not event["domain_id"]:
            raise ValueError("authored-domain assignment requires a user and a domain ID")
        state["authored_domain_assignment"] = _assignment(
            "assigned", event["domain_id"], [event["domain_id"]], None
        )
        return

    if event_type == "record_unresolved_authored_domain_assignment":
        sources = event["source_domain_ids"]
        if event["actor_type"] != "user" or not sources or len(set(sources)) != len(sources):
            raise ValueError("unresolved assignment requires a user and unique source domain IDs")
        state["authored_domain_assignment"] = _assignment(
            "unresolved", None, sorted(sources), event["reason"]
        )
        return

    if event_type == "confirm_candidate":
        if event["actor_type"] != "user":
            raise ValueError("user_confirmed changes only on an explicit user confirmation")
        if event["candidate_version_id"] != state["active_candidate_version_id"]:
            raise ValueError("confirmation must target the active candidate version")
        active = next(
            version for version in state["candidate_versions"]
            if version["candidate_version_id"] == state["active_candidate_version_id"]
        )
        if active["user_confirmed"]:
            raise ValueError("candidate version is already user-confirmed")
        active["user_confirmed"] = True
        active["lifecycle_state"] = "user_confirmed"
        return

    if event_type == "replace_candidate_version":
        if event["actor_type"] != "user":
            raise ValueError("replacement requires an explicit user event in this fixture contract")
        prior_id = event["prior_candidate_version_id"]
        if prior_id != state["active_candidate_version_id"]:
            raise ValueError("replacement must reference the active prior version")
        versions = state["candidate_versions"]
        prior = next(version for version in versions if version["candidate_version_id"] == prior_id)
        replacement = copy.deepcopy(event["replacement_version"])
        next_ordinal = max(version["version_ordinal"] for version in versions) + 1
        if replacement["candidate_id"] != state["candidate_id"]:
            raise ValueError("replacement must retain the logical candidate_id")
        if replacement["version_ordinal"] != next_ordinal:
            raise ValueError("candidate version ordinals must increase monotonically by one")
        if replacement["candidate_version_id"] != f"{state['candidate_id']}@{next_ordinal}":
            raise ValueError("candidate_version_id must encode the logical ID and monotonic ordinal")
        if replacement["candidate_version_id"] in {version["candidate_version_id"] for version in versions}:
            raise ValueError("replacement candidate_version_id must be distinct")
        if replacement["user_confirmed"] or replacement["lifecycle_state"] != "provisional":
            raise ValueError("replacement confirmation does not transfer from the prior version")
        provenance = replacement["provenance"]
        if (
            provenance["prior_candidate_version_id"] != prior_id
            or provenance["replacement_event_id"] != event["event_id"]
        ):
            raise ValueError("replacement provenance must retain its prior version and event")
        # Retain the prior record and its confirmation fact while linking the replacement.
        prior["lifecycle_state"] = "replaced"
        prior["provenance"]["replaced_by_candidate_version_id"] = replacement["candidate_version_id"]
        versions.append(replacement)
        state["active_candidate_version_id"] = replacement["candidate_version_id"]
        return

    raise ValueError(f"unsupported lifecycle event type: {event_type}")


def reduce_case(case: dict[str, Any]) -> dict[str, Any]:
    """Return a stable event trace and final state for one synthetic case."""
    state = copy.deepcopy(case["initial_state"])
    events = _event_order(case["events"])
    tie_groups = []
    for (timestamp, sequence), grouped in groupby(events, key=lambda event: (event["occurred_at"], event["sequence"])):
        event_ids = [event["event_id"] for event in grouped]
        if len(event_ids) > 1:
            tie_groups.append({"occurred_at": timestamp, "sequence": sequence, "event_ids": event_ids})

    snapshots = []
    for event in events:
        _apply_event(state, event)
        snapshots.append(_snapshot(state, event["event_id"]))

    version_summaries = [
        {
            "candidate_version_id": version["candidate_version_id"],
            "version_ordinal": version["version_ordinal"],
            "lifecycle_state": version["lifecycle_state"],
            "user_confirmed": version["user_confirmed"],
            "evidence_state": version["evidence_state"],
            "provenance": version["provenance"],
        }
        for version in sorted(state["candidate_versions"], key=lambda item: item["version_ordinal"])
    ]
    return {
        "case_id": case["case_id"],
        "ordered_event_ids": [event["event_id"] for event in events],
        "tie_groups": tie_groups,
        "after_each_event": snapshots,
        "final_state": {
            "candidate_id": state["candidate_id"],
            "active_candidate_version_id": state["active_candidate_version_id"],
            "candidate_versions": version_summaries,
            "authored_domain_assignment": state["authored_domain_assignment"],
        },
    }


def evaluate(fixture: dict[str, Any]) -> dict[str, Any]:
    """Reduce every fixture case in declared order."""
    return {
        "artifact_type": "d6_lifecycle_status_contract_amendment_result_v1",
        "cases": [reduce_case(case) for case in fixture["cases"]],
    }


def main() -> int:
    """Read one fixture file and write canonical JSON to standard output."""
    fixture_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("fixtures.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    output = json.dumps(evaluate(fixture), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
