"""Run the remaining bounded design-only attribution protocol diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("group_attribution_protocol_followup_fixture.json")
DEFAULT_OUTPUT = ROOT / "docs/project/evidence/group-attribution-protocol-followup.json"


def _require(condition: bool, message: str) -> None:
    """Stop the replay on the first violated contract invariant."""
    if not condition:
        raise AssertionError(message)


def _resolve_endpoint(reference: str, matches: dict[str, list[str]], scope: set[str]) -> str | None:
    """Resolve only a unique endpoint inside the frozen eligible scope."""
    resolved = matches.get(reference, [])
    if len(resolved) != 1 or resolved[0] not in scope:
        return None
    return resolved[0]


def _profile(candidate: dict[str, Any], readouts: dict[str, float]) -> dict[str, Any]:
    """Summarize one candidate's supplied member readouts without cross-candidate normalization."""
    values = [readouts[group_id] for group_id in candidate["members"]]
    return {
        "candidate_id": candidate["id"],
        "kind": candidate["kind"],
        "members": candidate["members"],
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "weakest_member": min(values),
        "valid_member_count": len(values),
        "expected_member_count": len(values),
        "coverage": 1.0,
    }


def run(fixture: dict[str, Any], fixture_bytes: bytes) -> dict[str, Any]:
    """Evaluate driver separation, provenance dependence, status, coverage, and profiles."""
    scope = set(fixture["scope"])
    scale_query_id = fixture["scale_query_id"]
    checks: list[dict[str, Any]] = []

    cases = {case["id"]: case for case in fixture["driver_modifier_cases"]}
    baseline = cases["baseline"]
    driver_removed = cases["driver_removed"]
    modifier_removed = cases["modifier_removed"]
    _require(baseline["proposal_extent"] != driver_removed["proposal_extent"],
             "driver perturbation did not change proposal output")
    _require(baseline["proposal_extent"] == modifier_removed["proposal_extent"],
             "modifier perturbation unexpectedly changed proposal output")
    _require(baseline["attribution_channels"] != modifier_removed["attribution_channels"],
             "modifier perturbation was not represented in attribution evidence")
    for case in (baseline, modifier_removed):
        field_statuses = case["attribution_field_status_by_group"]
        _require(set(field_statuses) == scope,
                 f"{case['id']} field does not cover the frozen scope")
        _require(all(record["status"] and (record["status"] == "computed" or record.get("reason"))
                     for record in field_statuses.values()),
                 f"{case['id']} field status or reason is missing")
    checks.append({"id": "driver_modifier_separation", "result": "passed",
                   "baseline_proposal_extent": baseline["proposal_extent"],
                   "driver_removed_proposal_extent": driver_removed["proposal_extent"],
                   "modifier_removed_proposal_extent": modifier_removed["proposal_extent"],
                   "attribution_channels_by_case": {key: value["attribution_channels"] for key, value in cases.items()},
                   "complete_field_status_by_proposed_case": {
                       key: value["attribution_field_status_by_group"]
                       for key, value in cases.items() if value["proposal_status"] == "proposed"
                   }})

    dependence = fixture["proposal_attribution_dependence"]
    proposal_sources = set(dependence["proposal_source_refs"])
    dependence_rows = []
    for scenario in dependence["scenarios"]:
        attribution_sources = set(scenario["attribution_source_refs"])
        shared_sources = sorted(proposal_sources & attribution_sources)
        dependence_rows.append({
            "scenario_id": scenario["id"],
            "proposal_source_refs": sorted(proposal_sources),
            "attribution_source_refs": sorted(attribution_sources),
            "shared_source_refs": shared_sources,
            "discovery_exposure": "exposed" if shared_sources else "not_shared_in_fixture",
            "supplied_readout": scenario["readout"],
            "readout_mapping": dependence["illustrative_mapping"],
        })
    _require(dependence_rows[0]["shared_source_refs"] == ["observation:gap-G1-G2"],
             "same-source exposure was not detected")
    _require(not dependence_rows[1]["shared_source_refs"] and not dependence_rows[2]["shared_source_refs"],
             "ablated or holdout evidence still shares proposal sources")
    checks.append({"id": "proposal_attribution_dependency", "result": "passed", "scenarios": dependence_rows,
                   "interpretation": "dependency is visible; causal inflation is unresolved because readouts are supplied synthetic inputs"})

    endpoint_contract = fixture["exclusion_endpoint_cases"]
    veto_results = []
    for case in endpoint_contract["cases"]:
        resolved = [_resolve_endpoint(ref, endpoint_contract["endpoint_matches"], scope) for ref in case["endpoints"]]
        hard_veto = all(value is not None for value in resolved) and len(set(resolved)) == len(resolved)
        _require(hard_veto == case["expected_hard_veto"], f"unexpected endpoint handling for {case['id']}")
        veto_results.append({"case_id": case["id"], "resolved_endpoints": resolved,
                             "hard_veto": hard_veto,
                             "declaration_retained": True,
                             "status": "resolved" if hard_veto else "unresolved_endpoint"})
    checks.append({"id": "invalid_exclusion_endpoints", "result": "passed", "cases": veto_results})

    search = fixture["search_and_evidence_status"]
    _require(search["search_status"] == "incomplete" and search["closure_claim"] == "not_claimed",
             "incomplete search was represented as closed")
    _require(any(cell["evidence_status"] == "computed" for cell in search["field_cells"])
             and any(cell["evidence_status"] == "unknown" for cell in search["field_cells"]),
             "search completeness was conflated with field evidence status")
    checks.append({"id": "search_completeness_separate_from_evidence", "result": "passed", "search_status": search["search_status"],
                   "closure_claim": search["closure_claim"], "field_cells": search["field_cells"]})

    coverage = []
    for family in fixture["coverage"]["evidence_families"]:
        observed = len(set(family["observed_source_refs"]))
        coverage.append({"family_id": family["id"], "expected": family["expected_observations"],
                         "observed_unique_sources": observed,
                         "coverage": observed / family["expected_observations"] if family["expected_observations"] else None})
    cell_source_refs = fixture["coverage"]["cell_source_refs"]
    shared_source_refs = sorted({record["source_ref"] for record in cell_source_refs
                                 if sum(item["source_ref"] == record["source_ref"] for item in cell_source_refs) > 1})
    _require(coverage == [
        {"family_id": "geometry_relation", "expected": 4, "observed_unique_sources": 2, "coverage": 0.5},
        {"family_id": "semantic_role", "expected": 4, "observed_unique_sources": 1, "coverage": 0.25},
    ], "family-specific coverage denominator changed unexpectedly")
    _require(shared_source_refs == ["physical:shared-gap-23"], "shared physical observation was not dependency-deduplicated")
    checks.append({"id": "family_coverage_and_shared_source", "result": "passed", "coverage_by_family": coverage,
                   "shared_source_refs_counted_once": shared_source_refs})

    singleton = fixture["singleton_case"]
    _require(len(singleton["members"]) == 1 and singleton["within_candidate_pair_count"] == 0,
             "singleton diagnostic unexpectedly invented internal pairs")
    _require(singleton["member_readout"] is None and singleton["status"] == "not_available"
             and bool(singleton["reason"]), "singleton absence of pairs was treated as perfect support")
    singleton_field = [
        {
            "candidate_id": singleton["candidate_id"],
            "group_id": group_id,
            "scale_query_id": scale_query_id,
            "in_proposal_extent": group_id in singleton["members"],
            "status": "not_available",
            "readout": None,
            "reason": singleton["reason"] if group_id in singleton["members"] else "no_attribution_observation_in_fixture",
        }
        for group_id in fixture["scope"]
    ]
    _require(len(singleton_field) == len(scope) and all(cell["readout"] is None for cell in singleton_field),
             "singleton field did not cover scope with explicit missingness")
    checks.append({"id": "singleton_low_evidence", "result": "passed", "case": singleton,
                   "complete_scope_field_cells": singleton_field})

    profile_comparison = fixture["profile_comparison"]
    profiles = [_profile(candidate, profile_comparison["group_readouts"])
                for candidate in profile_comparison["candidates"]]
    profile_field_views = []
    for candidate in profile_comparison["candidates"]:
        members = set(candidate["members"])
        cells = [
            {
                "candidate_id": candidate["id"],
                "group_id": group_id,
                "scale_query_id": scale_query_id,
                "in_proposal_extent": group_id in members,
                "status": "computed",
                "readout": profile_comparison["group_readouts"][group_id],
                "source_ref": f"profile-input:{group_id}",
                "boundary_tension": "not_evaluated" if group_id not in members else None,
            }
            for group_id in fixture["scope"]
        ]
        profile_field_views.append({"candidate_id": candidate["id"], "cells": cells})
    _require({profile["kind"] for profile in profiles} == {"original", "overlapping_merge", "broad"},
             "profile comparison omitted an original, overlapping merge, or broad candidate")
    _require(all(0.0 <= profile["coverage"] <= 1.0 for profile in profiles), "invalid profile coverage")
    _require(len({tuple(profile["members"]) for profile in profiles}) == len(profiles), "candidate profiles collapsed together")
    expected_profile_cells = len(profile_comparison["candidates"]) * len(scope)
    _require(sum(len(view["cells"]) for view in profile_field_views) == expected_profile_cells,
             "profile comparison omitted an in-scope field cell")
    _require(all(math.isfinite(cell["readout"]) for view in profile_field_views for cell in view["cells"]),
             "profile comparison contains a non-finite readout")
    checks.append({"id": "original_merge_broad_profiles", "result": "passed", "profiles": profiles,
                   "complete_scope_field_views": profile_field_views,
                   "normalization": "none_across_candidates"})

    return {
        "schema": "group-attribution-protocol-followup-result/v1",
        "fixture_id": fixture["id"],
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "design_only": True,
        "checks": checks,
        "limitations": [
            "The driver/modifier and endpoint cases validate declared contract handling, not a selected production recipe.",
            "Proposal-dependence readouts are supplied synthetic inputs; the comparison exposes dependencies but does not estimate causal inflation.",
            "Coverage uses source references as diagnostic denominators and does not select cross-family weights.",
            "Profile values are supplied synthetic observations; they do not calibrate a real-world intensity scale.",
        ],
    }


def main() -> None:
    """Run the frozen follow-up fixture and write its deterministic result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    raw = args.fixture.read_bytes()
    result = run(json.loads(raw), raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(result['checks'])} follow-up checks passed; wrote {args.output}")


if __name__ == "__main__":
    main()
