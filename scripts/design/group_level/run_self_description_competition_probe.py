"""Run the D6 evidence-interaction probe without production imports.

The formulas in this file are deliberately probe-local. They expose separate
channels and invariants for design comparison; they do not define a production
candidate selector or a psychological probability.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
from typing import Any

EPS = 1e-9


def _bounds(group: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return an axis-aligned box around one probe group."""
    cx, cy = group["center"]
    sx, sy = group["size"]
    return cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2


def _area(group: dict[str, Any]) -> float:
    """Return the probe rectangle area."""
    sx, sy = group["size"]
    return sx * sy


def _pair_geometry(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compute gap, overlap, and relative shape mismatch for one pair."""
    lx0, lx1, ly0, ly1 = _bounds(left)
    rx0, rx1, ry0, ry1 = _bounds(right)
    dx = max(lx0 - rx1, rx0 - lx1, 0.0)
    dy = max(ly0 - ry1, ry0 - ly1, 0.0)
    gap = math.hypot(dx, dy)
    overlap = max(0.0, min(lx1, rx1) - max(lx0, rx0)) * max(0.0, min(ly1, ry1) - max(ly0, ry0))
    scale_ratio = min(_area(left), _area(right)) / max(_area(left), _area(right), EPS)
    return {
        "raw_gap": gap,
        "normalized_gap": gap / math.sqrt(_area(left) + _area(right)),
        "overlap_area": overlap,
        "shape_similarity": scale_ratio,
    }


def _barrier(left: dict[str, Any], right: dict[str, Any], walls: list[dict[str, Any]]) -> str:
    """Return clear, opening, or blocked for a center-line wall crossing."""
    x1, y1 = left["center"]
    x2, y2 = right["center"]
    for wall in walls:
        wx = wall["x"]
        if min(x1, x2) - EPS <= wx <= max(x1, x2) + EPS:
            ratio = 0.0 if abs(x2 - x1) <= EPS else (wx - x1) / (x2 - x1)
            y = y1 + ratio * (y2 - y1)
            low, high = wall["y_range"]
            if low - EPS <= y <= high + EPS:
                return "opening" if wall.get("opening", False) else "blocked"
    return "clear"


def _pair_record(left: dict[str, Any], right: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    """Return separated physical and semantic pair evidence."""
    geometry = _pair_geometry(left, right)
    labels = (left.get("label"), right.get("label"))
    semantic = "not_available" if None in labels else ("compatible" if labels[0] == labels[1] else "soft_negative")
    return {
        "groups": [left["id"], right["id"]],
        "geometry": geometry,
        "space": {
            "domain_status": "computed" if fixture.get("domain", False) else "not_available",
            "barrier": _barrier(left, right, fixture.get("walls", [])) if fixture.get("domain", False) else "not_available",
            "context_alignment_reference": bool(fixture.get("context")) if fixture.get("domain", False) else False,
        },
        "semantic": semantic,
    }


def _candidate_record(candidate: list[str], groups: dict[str, dict[str, Any]], fixture: dict[str, Any]) -> dict[str, Any]:
    """Summarize one candidate while retaining channel-level evidence."""
    members = [groups[item] for item in candidate]
    pairs = [_pair_record(left, right, fixture) for left, right in itertools.combinations(members, 2)]
    veto_pairs = {tuple(sorted(pair)) for pair in fixture.get("mutual_exclusion", [])}
    conflicts = [pair for pair in veto_pairs if set(pair).issubset(candidate)]
    geometry = [pair["geometry"] for pair in pairs]
    semantic_values = [pair["semantic"] for pair in pairs]
    blocked = [pair for pair in pairs if pair["space"]["barrier"] == "blocked"]
    invalid = any(member.get("status") == "invalid" for member in members)
    if invalid:
        status = "invalid"
    elif conflicts:
        status = "vetoed_mutual_exclusion"
    elif blocked:
        status = "space_conflict"
    else:
        status = "computed"
    geometry_support = sum(item["shape_similarity"] for item in geometry) / len(geometry) if geometry else 1.0
    gap_support = sum(1.0 / (1.0 + item["normalized_gap"]) for item in geometry) / len(geometry) if geometry else 1.0
    semantic_support = sum(1.0 if value == "compatible" else -0.25 if value == "soft_negative" else 0.0 for value in semantic_values) / len(semantic_values) if semantic_values else 0.0
    space_support = 0.0 if not fixture.get("domain", False) else (-1.0 if blocked else 1.0)
    return {
        "candidate": candidate,
        "status": status,
        "support": {
            "geometry_similarity": round(geometry_support, 8),
            "gap_proximity": round(gap_support, 8),
            "semantic": round(semantic_support, 8),
            "space": space_support,
        },
        "negative_evidence": {
            "geometry_mismatch": round(1.0 - geometry_support, 8),
            "semantic_disagreement": semantic_values.count("soft_negative"),
            "barrier": len(blocked),
        },
        "pair_observations": pairs,
        "mutual_exclusion_conflicts": [list(pair) for pair in conflicts],
        "provenance": {
            "formula_scope": "probe_only",
            "domain_available": bool(fixture.get("domain", False)),
            "context_count": len(fixture.get("context", [])),
        },
    }


def _run_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run all declared candidates in one fixture."""
    groups = {group["id"]: group for group in fixture["groups"]}
    return {
        "fixture_id": fixture["id"],
        "question": fixture["question"],
        "candidates": [_candidate_record(candidate, groups, fixture) for candidate in fixture["candidates"]],
    }


def _candidate(result: dict[str, Any], ids: list[str]) -> dict[str, Any]:
    """Find one candidate record by member ids."""
    wanted = set(ids)
    return next(item for item in result["candidates"] if set(item["candidate"]) == wanted)


def _assertions(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Check design invariants and return auditable assertion records."""
    by_id = {result["fixture_id"]: result for result in results}
    checks: list[dict[str, Any]] = []

    mixed = _candidate(by_id["minority_mixed"], ["R2", "C1"])
    checks.append({"id": "minority_label_is_soft", "pass": mixed["status"] == "computed" and mixed["negative_evidence"]["semantic_disagreement"] == 1})
    independent = _candidate(by_id["independent_minority"], ["C1", "C2"])
    cross = _candidate(by_id["independent_minority"], ["R2", "C1"])
    checks.append({"id": "independent_minority_has_more_gap_support", "pass": independent["support"]["gap_proximity"] > cross["support"]["gap_proximity"]})
    geometry = _candidate(by_id["geometry_conflict"], ["A", "B"])
    checks.append({"id": "geometry_mismatch_is_negative_evidence", "pass": geometry["negative_evidence"]["geometry_mismatch"] > 0.5})
    barrier = _candidate(by_id["space_barrier"], ["A", "B"])
    checks.append({"id": "closed_barrier_is_separate_channel", "pass": barrier["status"] == "space_conflict" and barrier["support"]["gap_proximity"] > 0})
    semantic = _candidate(by_id["semantic_conflict"], ["A", "B"])
    checks.append({"id": "explicit_mutual_exclusion_vetoes_candidate", "pass": semantic["status"] == "vetoed_mutual_exclusion"})
    missing = _candidate(by_id["missing_channels"], ["A", "B"])
    checks.append({"id": "missing_semantic_and_domain_are_unavailable", "pass": missing["support"]["semantic"] == 0.0 and missing["support"]["space"] == 0.0 and missing["provenance"]["domain_available"] is False})
    invalid = _candidate(by_id["invalid_geometry"], ["A", "B"])
    checks.append({"id": "invalid_geometry_is_not_missing", "pass": invalid["status"] == "invalid"})
    context = _candidate(by_id["context_reference"], ["A", "B"])
    checks.append({"id": "context_keeps_candidate_eligibility", "pass": context["status"] == "computed" and context["provenance"]["context_count"] == 1 and context["pair_observations"][0]["space"]["context_alignment_reference"]})
    return checks


def main() -> None:
    """Run the probe, assert invariants, and write JSON evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("self_description_competition_fixtures.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/project/evidence/d6-self-description-competition-probe.json"))
    args = parser.parse_args()
    payload = json.loads(args.fixtures.read_text(encoding="utf-8"))
    results = [_run_fixture(fixture) for fixture in payload["fixtures"]]
    checks = _assertions(results)
    if not all(check["pass"] for check in checks):
        raise AssertionError(checks)
    output = {
        "schema": "d6-self-description-competition-evidence/v1",
        "formula_scope": "probe_only_not_production",
        "fixture_schema": payload["schema"],
        "checks": checks,
        "fixtures": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": len(checks), "passed": sum(check["pass"] for check in checks), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
