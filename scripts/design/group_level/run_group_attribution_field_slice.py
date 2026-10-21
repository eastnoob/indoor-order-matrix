"""Run a small design-only authored-group attribution-field diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("group_attribution_field_slice_fixture.json")
DEFAULT_OUTPUT = ROOT / "docs/project/evidence/group-attribution-field-slice.json"


def _load_fixture(path: Path) -> tuple[dict[str, Any], bytes]:
    """Load and decode the frozen diagnostic fixture while retaining its exact bytes."""
    raw = path.read_bytes()
    return json.loads(raw), raw


def _profile(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize observed member readouts without imputing missing values."""
    values = [
        float(member["readout"])
        for member in members
        if member["status"] == "computed" and member.get("readout") is not None
    ]
    expected = len(members)
    return {
        "members": members,
        "expected_member_count": expected,
        "valid_member_count": len(values),
        "coverage": len(values) / expected if expected else None,
        "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "weakest_member": min(values) if values else None,
    }


def _require(condition: bool, message: str) -> None:
    """Fail immediately when a frozen design invariant is violated."""
    if not condition:
        raise AssertionError(message)


def run(fixture: dict[str, Any], raw_fixture: bytes) -> dict[str, Any]:
    """Evaluate field-domain, overlap, status, and profile invariants."""
    groups = fixture["scope"]["eligible_groups"]
    out_of_scope = fixture["scope"]["out_of_scope_groups"]
    out_of_scope_records = fixture["scope"]["out_of_scope_records"]
    scale_query_id = fixture["scale_query_id"]
    candidates = fixture["candidates"]
    field_cells: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for candidate in candidates:
        candidate_id = candidate["id"]
        proposal = set(candidate["proposal_extent"])
        attribution = candidate["attribution"]
        _require(set(attribution) == set(groups), f"{candidate_id} does not cover the frozen eligible scope")
        _require(not (set(candidate["proposal_evidence_refs"]) & {
            source for record in attribution.values() for source in record.get("source_refs", [])
        }), f"{candidate_id} reuses proposal evidence as attribution evidence")
        for group_id in groups:
            record = attribution[group_id]
            cell = {
                "candidate_id": candidate_id,
                "group_id": group_id,
                "scale_query_id": scale_query_id,
                "in_proposal_extent": group_id in proposal,
                "status": record["status"],
                "readout": record.get("readout"),
                "reason": record.get("reason"),
                "source_refs": record.get("source_refs", []),
                "boundary_tension": bool(record.get("boundary_tension", False)),
            }
            field_cells.append(cell)
            by_key[(candidate_id, group_id)] = cell

    expected_cell_count = len(candidates) * len(groups)
    _require(len(field_cells) == expected_cell_count, "field cell count does not match candidate × scope")
    _require(len(by_key) == expected_cell_count, "duplicate candidate/group field cell found")
    _require(not any(cell["group_id"] in out_of_scope for cell in field_cells), "out-of-scope group got a field cell")
    _require(all(record.get("source_ref") and record.get("reason") for record in out_of_scope_records),
             "out-of-scope group lost its source or reason")

    overlap_ids = set.intersection(*(set(candidate["proposal_extent"]) for candidate in candidates))
    _require("G2" in overlap_ids, "fixture no longer exercises overlapping proposals")
    overlap_readouts = [by_key[(candidate["id"], "G2")]["readout"] for candidate in candidates]
    _require(overlap_readouts == [0.56, 0.67], "overlap readouts were altered or normalized")
    _require(not math.isclose(sum(overlap_readouts), 1.0), "overlap values were normalized to a partition")

    outside_cell = by_key[("K1", "G3")]
    _require(not outside_cell["in_proposal_extent"], "K1/G3 should be outside the proposal extent")
    _require(outside_cell["status"] == "computed" and outside_cell["readout"] == 0.31,
             "in-scope extent-external readout was lost or zero-filled")
    _require(outside_cell["boundary_tension"], "extent-external field cell lacks boundary-tension marker")

    unknown_cell = by_key[("K2", "G1")]
    conditional_cell = by_key[("K2", "G3")]
    for cell, expected_status in ((unknown_cell, "unknown"), (conditional_cell, "conditional")):
        _require(cell["status"] == expected_status and cell["readout"] is None,
                 f"{expected_status} status was coerced into a numeric value")
        _require(bool(cell["reason"]), f"{expected_status} status lost its reason")

    bridge = fixture["weak_bridge_profile"]
    complete_profile = _profile(bridge["members"])
    _require(math.isclose(complete_profile["mean"], 0.44), "weak-bridge mean did not match the diagnostic reference")
    _require(math.isclose(complete_profile["median"], 0.5125), "weak-bridge median did not match the diagnostic reference")
    _require(math.isclose(complete_profile["weakest_member"], 0.15), "weak-bridge tail was hidden")

    masked_members = [dict(member) for member in bridge["members"]]
    masked_id = bridge["mask_member_for_coverage_case"]
    masked_member = next(member for member in masked_members if member["id"] == masked_id)
    masked_member.update(status="unknown", readout=None)
    masked_profile = _profile(masked_members)
    _require(masked_profile["valid_member_count"] == complete_profile["valid_member_count"] - 1,
             "masked readout did not reduce the valid denominator")
    _require(masked_profile["coverage"] < complete_profile["coverage"], "masked readout did not reduce coverage")
    expected_masked_mean = statistics.fmean(
        member["readout"] for member in masked_members
        if member["status"] == "computed" and member.get("readout") is not None
    )
    _require(math.isclose(expected_masked_mean, 0.421875), "masked arithmetic reference changed unexpectedly")
    _require(masked_profile["mean"] is not None and math.isclose(masked_profile["mean"], 0.421875),
             "masked profile does not summarize only its observed readouts")

    return {
        "schema": "group-attribution-field-slice-result/v1",
        "fixture_id": fixture["id"],
        "fixture_sha256": hashlib.sha256(raw_fixture).hexdigest(),
        "design_only": True,
        "field_domain": {
            "eligible_group_ids": groups,
            "scale_query_id": scale_query_id,
            "candidate_ids": [candidate["id"] for candidate in candidates],
            "expected_cells": expected_cell_count,
            "observed_cells": len(field_cells),
            "cells": field_cells,
            "out_of_scope_records_without_cells": out_of_scope_records,
            "cross_candidate_normalization": "none",
        },
        "checks": [
            {"id": "complete_scope_and_overlap", "result": "passed", "overlap_group": "G2",
             "candidate_local_readouts": overlap_readouts},
            {"id": "extent_external_field_cell", "result": "passed", "cell": outside_cell},
            {"id": "categorical_unknown_and_conditional", "result": "passed",
             "unknown_cell": unknown_cell, "conditional_cell": conditional_cell,
             "K2_valid_readout_coverage": 1 / len(groups)},
            {"id": "weak_bridge_and_missing_coverage", "result": "passed",
             "complete_profile": complete_profile, "masked_profile": masked_profile},
        ],
        "limitations": [
            "Readouts are supplied diagnostic inputs; no evidence-to-readout rule is tested or selected.",
            "Candidate proposals are frozen inputs; candidate generation, driver/modifier effects, and search completeness are not tested.",
            "The synthetic arithmetic does not validate a real-world scale or calibration.",
            "Proposal-evidence leakage requires a separate same-source/ablation/independent comparison.",
        ],
    }


def main() -> None:
    """Run the fixture and write a stable JSON result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    fixture, raw = _load_fixture(args.fixture)
    result = run(fixture, raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(result['checks'])} diagnostic checks passed; wrote {args.output}")


if __name__ == "__main__":
    main()
