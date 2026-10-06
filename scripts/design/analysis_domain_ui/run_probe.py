"""Replay the bounded AnalysisDomain/UI handoff fixtures deterministically.

This module is a design probe only. It does not import production adapters or
claim to implement a public AnalysisDomain API.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FIXTURES_PATH = ROOT / "fixtures.json"


def load_json(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON object with strict duplicate-key rejection."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    """Write stable, UTF-8 JSON with sorted keys and LF line endings."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def clone(value: Any) -> Any:
    """Copy JSON-compatible data without sharing mutable state."""

    return json.loads(json.dumps(value, ensure_ascii=False))


def event_signature(event: dict[str, Any]) -> tuple[Any, ...]:
    """Return the semantic payload used to distinguish duplicate events."""

    replacement = event.get("replacement")
    replacement_version = replacement.get("version_id") if replacement else None
    return (
        event.get("event_type"),
        event.get("candidate_id"),
        replacement_version,
        event.get("reason"),
    )


def make_state(candidate: dict[str, Any]) -> dict[str, Any]:
    """Normalize a fixture candidate into a mutable replay state."""

    state = clone(candidate)
    state.setdefault("event_ids", [])
    state.setdefault("ever_confirmed", False)
    state.setdefault("conflict_ids", [])
    state.setdefault("lineage", [])
    return state


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    """Apply one non-conflicting lifecycle event to a candidate state."""

    event_type = event["event_type"]
    state["event_ids"].append(event["event_id"])
    if event_type in {"confirm", "draw_boundary"}:
        state["user_confirmed"] = True
        state["accepted"] = True
        state["ever_confirmed"] = True
        state["lifecycle"] = "confirmed"
    elif event_type == "assign":
        state["assignment"] = "assigned"
    elif event_type == "reject":
        state["user_confirmed"] = False
        state["accepted"] = False
        state["assignment"] = "unassigned"
        state["lifecycle"] = "rejected"
    else:
        raise ValueError(f"unsupported lifecycle event: {event_type}")


def qualified(state: dict[str, Any], unresolved_conflict_ids: set[str]) -> bool:
    """Return whether a candidate can support a domain promotion gate."""

    return (
        state["evidence_state"] == "available"
        and state["geometry_state"] == "valid"
        and state["lifecycle"] not in {"rejected", "replaced"}
        and not set(state.get("conflict_ids", [])) & unresolved_conflict_ids
    )


def replay_case(case: dict[str, Any]) -> dict[str, Any]:
    """Replay one fixture and derive lifecycle, visual, and refusal states."""

    states_by_version: dict[str, dict[str, Any]] = {}
    current_by_candidate: dict[str, str] = {}
    for candidate in case.get("candidates", []):
        state = make_state(candidate)
        version_id = state["version_id"]
        states_by_version[version_id] = state
        current_by_candidate[state["candidate_id"]] = version_id

    explicit_conflicts = clone(case.get("conflict_relations", []))
    unresolved_conflict_ids = {
        conflict["conflict_id"]
        for conflict in explicit_conflicts
        if conflict.get("status") == "unresolved"
    }
    for conflict in explicit_conflicts:
        if conflict.get("status") != "unresolved":
            continue
        for candidate_id in conflict.get("candidate_ids", []):
            version_id = current_by_candidate.get(candidate_id)
            if version_id is not None:
                states_by_version[version_id]["conflict_ids"].append(conflict["conflict_id"])

    events = sorted(case.get("events", []), key=lambda item: (item["order_key"], item["event_id"]))
    event_provenance: list[dict[str, Any]] = []
    generated_conflicts: list[dict[str, Any]] = []
    hover_candidate_id: str | None = None
    pre_hover_projection: dict[str, Any] | None = None

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in events:
        # Grouping by the declared ordering key preserves all same-key evidence before any lifecycle mutation.
        groups.setdefault((event["order_key"], event["relation_scope"]), []).append(event)

    for event in events:
        if event["event_type"] == "hover":
            if pre_hover_projection is None:
                pre_hover_projection = project_state(states_by_version, current_by_candidate, unresolved_conflict_ids)
            hover_candidate_id = event["candidate_id"]
            event_provenance.append({"event_id": event["event_id"], "status": "display_only", "provenance": clone(event["provenance"])})
            continue

        group = groups[(event["order_key"], event["relation_scope"])]
        conflicting = [item for item in group if event_signature(item) != event_signature(event)]
        if conflicting and event["event_type"] in {"confirm", "assign", "draw_boundary", "reject", "replace"}:
            conflict_id = f"conflict:event-tie:{event['relation_scope']}:{event['order_key']}"
            if conflict_id not in unresolved_conflict_ids:
                unresolved_conflict_ids.add(conflict_id)
                all_events = sorted(group, key=lambda item: item["event_id"])
                generated_conflicts.append(
                    {
                        "conflict_id": conflict_id,
                        "candidate_ids": sorted({item["candidate_id"] for item in all_events}),
                        "reason": "incompatible semantic events share one ordering key and relation scope",
                        "status": "unresolved",
                        "event_ids": [item["event_id"] for item in all_events],
                        "provenance": [value for item in all_events for value in item["provenance"]],
                    }
                )
                for item in all_events:
                    version_id = current_by_candidate.get(item["candidate_id"])
                    if version_id is not None:
                        states_by_version[version_id]["conflict_ids"].append(conflict_id)
            event_provenance.append({"event_id": event["event_id"], "status": "retained_conflict", "provenance": clone(event["provenance"])})
            continue

        if event["event_type"] == "replace":
            old_version_id = current_by_candidate[event["candidate_id"]]
            old_state = states_by_version[old_version_id]
            old_state["lifecycle"] = "replaced"
            old_state["accepted"] = False
            replacement = clone(event["replacement"])
            replacement["lineage"] = [
                {
                    "relation": "replaces",
                    "from_version_id": old_version_id,
                    "to_version_id": replacement["version_id"],
                    "event_id": event["event_id"],
                }
            ]
            replacement_state = make_state(replacement)
            states_by_version[replacement_state["version_id"]] = replacement_state
            current_by_candidate[replacement_state["candidate_id"]] = replacement_state["version_id"]
            event_provenance.append({"event_id": event["event_id"], "status": "applied", "provenance": clone(event["provenance"])})
            continue

        version_id = current_by_candidate.get(event["candidate_id"])
        if version_id is None:
            raise ValueError(f"event targets unknown candidate: {event['event_id']}")
        apply_event(states_by_version[version_id], event)
        event_provenance.append({"event_id": event["event_id"], "status": "applied", "provenance": clone(event["provenance"])})

    explicit_conflicts.extend(generated_conflicts)
    projection = project_state(states_by_version, current_by_candidate, unresolved_conflict_ids)
    projection["case_id"] = case["case_id"]
    projection["events_replayed"] = event_provenance
    projection["conflicts"] = explicit_conflicts
    projection["lineage"] = [lineage for state in states_by_version.values() for lineage in state.get("lineage", [])]
    projection["roles"] = clone(case.get("role_records", []))
    if pre_hover_projection is not None:
        projection["pre_hover_projection"] = pre_hover_projection
        projection["hover_candidate_id"] = hover_candidate_id
        for row in projection["candidate_states"]:
            if row["candidate_id"] == hover_candidate_id:
                row["visual_state"] = "hover_only"
                projection["visual_states"][row["version_id"]] = "hover_only"
    return projection


def project_state(
    states_by_version: dict[str, dict[str, Any]],
    current_by_candidate: dict[str, str],
    unresolved_conflict_ids: set[str],
) -> dict[str, Any]:
    """Derive selection, visual state, and downstream availability from replay state."""

    current_states = [states_by_version[version_id] for version_id in current_by_candidate.values()]
    # Promotion requires both qualified evidence and an explicit user action; provenance alone is insufficient.
    active_states = [
        state
        for state in current_states
        if (state.get("user_confirmed") or state.get("assignment") == "assigned")
        and qualified(state, unresolved_conflict_ids)
    ]
    priority = {"user_authored": 0, "explicit_ifc": 1, "automatic_candidate": 2, "diagnostic_only": 3}
    selected_candidate_id: str | None = None
    if not unresolved_conflict_ids and active_states:
        # Source priority is only applied after conflict and qualification gates; ties stay unselected.
        best_priority = min(priority.get(state["source_kind"], 99) for state in active_states)
        best = [state for state in active_states if priority.get(state["source_kind"], 99) == best_priority]
        if len(best) == 1:
            selected_candidate_id = best[0]["candidate_id"]

    domain_status = "available" if selected_candidate_id is not None else "not_available"
    downstream_status = "available" if domain_status == "available" else "not_available"
    candidate_views: list[dict[str, Any]] = []
    visual_states: dict[str, str] = {}
    for state in sorted(states_by_version.values(), key=lambda item: item["version_id"]):
        visual = visual_state(state, selected_candidate_id, current_by_candidate, unresolved_conflict_ids)
        visual_states[state["version_id"]] = visual
        candidate_views.append(
            {
                "candidate_id": state["candidate_id"],
                "version_id": state["version_id"],
                "source_kind": state["source_kind"],
                "evidence_state": state["evidence_state"],
                "geometry_state": state["geometry_state"],
                "lifecycle": state["lifecycle"],
                "assignment": state["assignment"],
                "user_confirmed": state["user_confirmed"],
                "accepted": state["accepted"],
                "event_ids": sorted(state.get("event_ids", [])),
                "provenance": sorted(state.get("provenance", [])),
                "conflict_ids": sorted(set(state.get("conflict_ids", []))),
                "visual_state": visual,
                "active": state["candidate_id"] in {item["candidate_id"] for item in active_states} and selected_candidate_id == state["candidate_id"],
                "lineage": clone(state.get("lineage", [])),
            }
        )
    return {
        "candidate_states": candidate_views,
        "selection": {
            "domain_status": domain_status,
            "selected_candidate_id": selected_candidate_id,
            "active_candidate_ids": sorted(state["candidate_id"] for state in active_states if selected_candidate_id == state["candidate_id"]),
            "unresolved_conflict_ids": sorted(unresolved_conflict_ids),
        },
        "downstream": {
            "free_space": downstream_status,
            "connectivity": downstream_status,
            "membership": downstream_status,
            "route": downstream_status,
        },
        "visual_states": visual_states,
    }


def visual_state(
    state: dict[str, Any],
    selected_candidate_id: str | None,
    current_by_candidate: dict[str, str],
    unresolved_conflict_ids: set[str],
) -> str:
    """Map state to a redundant visual label without changing lifecycle."""

    if set(state.get("conflict_ids", [])) & unresolved_conflict_ids:
        return "conflict"
    if state["lifecycle"] == "rejected":
        return "rejected"
    if state["lifecycle"] == "replaced":
        return "replaced_history"
    if state.get("lineage"):
        return "replacement_provisional"
    if state["candidate_id"] == selected_candidate_id:
        return "active_green"
    if state["version_id"] != current_by_candidate.get(state["candidate_id"]):
        return "replaced_history"
    if state["evidence_state"] in {"missing", "partial", "invalid", "unsupported", "diagnostic_only"}:
        return state["evidence_state"]
    if selected_candidate_id is not None and state["source_kind"] == "automatic_candidate":
        return "automatic_provenance"
    if state["evidence_state"] == "ambiguous" or state["assignment"] == "unassigned":
        if state["source_kind"] == "automatic_candidate" and state["evidence_state"] == "available":
            return "automatic_provisional"
        return "ambiguous_unassigned"
    if state["source_kind"] == "automatic_candidate":
        return "automatic_provenance"
    return "provisional"


def render_svg(result: dict[str, Any]) -> str:
    """Render a deterministic static UI contract figure from probe results."""

    width = 1440
    panel_width = 450
    panel_height = 270
    columns = 3
    rows = (len(result["cases"]) + columns - 1) // columns
    height = 150 + rows * panel_height
    colors = {
        "automatic_provisional": ("#f4b183", "#7f4f24"),
        "automatic_provenance": ("#f7d7b5", "#7f4f24"),
        "active_green": ("#a9d18e", "#1b5e20"),
        "ambiguous_unassigned": ("#ffd966", "#7f6000"),
        "conflict": ("#f4cccc", "#990000"),
        "rejected": ("#d9d9d9", "#595959"),
        "replaced_history": ("#eeeeee", "#666666"),
        "replacement_provisional": ("#f4b183", "#7f4f24"),
        "missing": ("#e7e6e6", "#666666"),
        "partial": ("#fce4d6", "#c65911"),
        "invalid": ("#f4cccc", "#990000"),
        "unsupported": ("#d9e1f2", "#1f4e79"),
        "diagnostic_only": ("#e7e6e6", "#666666"),
        "hover_only": ("#d9ead3", "#00a6d6"),
        "provisional": ("#fce4d6", "#7f4f24"),
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<title>AnalysisDomain to UI handoff design states</title>',
        '<desc>Static design evidence showing lifecycle and visual states. Hover is display-only; grey downstream controls are refused when no qualified domain is active.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="28" y="32" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#1f1f1f">AnalysisDomain → UI handoff (design evidence)</text>',
        '<text x="28" y="58" font-family="Arial, sans-serif" font-size="14" fill="#444444">Lifecycle, evidence state, provenance, and downstream refusal remain separate. Static SVG; no production UI.</text>',
    ]
    legend = [
        ("#a9d18e", "active green: qualified + explicit confirmation/assignment"),
        ("#f4b183", "automatic singleton/provisional"),
        ("#ffd966", "ambiguous or unassigned"),
        ("#f4cccc", "conflict: promotion disabled"),
        ("#d9d9d9", "rejected/replaced history"),
        ("#d9ead3", "hover-only focus"),
    ]
    legend_x = 28
    for index, (fill, label) in enumerate(legend):
        x = legend_x + (index % 3) * 450
        y = 82 + (index // 3) * 24
        parts.append(f'<rect x="{x}" y="{y - 12}" width="16" height="16" rx="3" fill="{fill}" stroke="#444444"/>')
        parts.append(f'<text x="{x + 24}" y="{y}" font-family="Arial, sans-serif" font-size="12" fill="#333333">{html.escape(label)}</text>')

    for index, case in enumerate(result["cases"]):
        x = 20 + (index % columns) * (panel_width + 20)
        y = 145 + (index // columns) * panel_height
        parts.append(f'<rect x="{x}" y="{y}" width="{panel_width}" height="{panel_height - 12}" rx="10" fill="#fafafa" stroke="#b7b7b7"/>')
        parts.append(f'<text x="{x + 14}" y="{y + 24}" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#222222">{html.escape(case["case_id"])}</text>')
        parts.append(f'<text x="{x + 14}" y="{y + 46}" font-family="Arial, sans-serif" font-size="12" fill="#555555">domain: {html.escape(case["selection"]["domain_status"])}; selected: {html.escape(str(case["selection"]["selected_candidate_id"] or "none"))}</text>')
        candidate_y = y + 60
        for c_index, candidate in enumerate(case["candidate_states"]):
            cy = candidate_y + c_index * 34
            visual = candidate["visual_state"]
            fill, stroke = colors.get(visual, ("#ffffff", "#444444"))
            stroke_width = 3 if case.get("hover_candidate_id") == candidate["candidate_id"] else 1
            parts.append(f'<rect x="{x + 14}" y="{cy}" width="{panel_width - 28}" height="26" rx="5" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
            label = f'{candidate["version_id"]} · {visual}'
            parts.append(f'<text x="{x + 24}" y="{cy + 17}" font-family="Arial, sans-serif" font-size="11" fill="#222222">{html.escape(label)}</text>')
        downstream_y = y + panel_height - 62
        status = case["selection"]["domain_status"]
        fill = "#e2f0d9" if status == "available" else "#d9d9d9"
        stroke = "#548235" if status == "available" else "#666666"
        parts.append(f'<rect x="{x + 14}" y="{downstream_y}" width="{panel_width - 28}" height="36" rx="6" fill="{fill}" stroke="{stroke}"/>')
        downstream_label = "free-space · connectivity · membership · route: " + ("available" if status == "available" else "not_available")
        parts.append(f'<text x="{x + 24}" y="{downstream_y + 22}" font-family="Arial, sans-serif" font-size="11" fill="#222222">{html.escape(downstream_label)}</text>')
        if case.get("hover_candidate_id"):
            parts.append(f'<text x="{x + 14}" y="{y + panel_height - 18}" font-family="Arial, sans-serif" font-size="11" fill="#007c91">hover: focus only; lifecycle unchanged</text>')
        if case["lineage"]:
            parts.append(f'<text x="{x + 14}" y="{y + panel_height - 18}" font-family="Arial, sans-serif" font-size="11" fill="#666666">lineage retained; new version re-enters provisional</text>')
        if case["conflicts"]:
            parts.append(f'<text x="{x + 14}" y="{y + panel_height - 18}" font-family="Arial, sans-serif" font-size="11" fill="#990000">conflict provenance retained; promotion disabled</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def run(fixtures_path: Path, output_dir: Path) -> dict[str, Any]:
    """Run all fixtures and write the JSON result and static SVG."""

    fixtures = load_json(fixtures_path)
    cases = [replay_case(case) for case in fixtures["cases"]]
    result = {
        "schema_version": "d6.analysis_domain_ui.result.v1",
        "fixture_schema_version": fixtures["schema_version"],
        "provenance": clone(fixtures["provenance"]),
        "cases": cases,
    }
    write_json(output_dir / "result.json", result)
    svg = render_svg(result)
    with (output_dir / "handoff.svg").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(svg)
    return result


def main() -> int:
    """Parse arguments, run the deterministic probe, and return an exit code."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.fixtures, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
