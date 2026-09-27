"""Run a reproducible, design-only comparison of relative-order candidates.

The probe computes anchors from projected vertices and evaluates two candidate
summaries.  It is intentionally outside the production import path so that the
experiment can be changed or discarded without changing the contract.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _mean_vertex(vertices: list[list[float]]) -> tuple[float, float]:
    """Return the arithmetic mean anchor for finite plan vertices."""
    if len(vertices) < 3:
        raise ValueError("fewer than three projected vertices")
    if any(len(vertex) != 2 or not all(math.isfinite(value) for value in vertex) for vertex in vertices):
        raise ValueError("non-finite or malformed projected vertex")
    return (
        sum(vertex[0] for vertex in vertices) / len(vertices),
        sum(vertex[1] for vertex in vertices) / len(vertices),
    )


def _tie_blocks(ids: list[str], positions: dict[str, float], tolerance: float) -> list[list[str]]:
    """Return stable connected tie blocks without using object IDs as order."""
    parent = list(range(len(ids)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left, left_id in enumerate(ids):
        for right in range(left + 1, len(ids)):
            if abs(positions[left_id] - positions[ids[right]]) <= tolerance:
                union(left, right)

    blocks: dict[int, list[str]] = {}
    for index, object_id in enumerate(ids):
        blocks.setdefault(find(index), []).append(object_id)
    return [blocks[root] for root in sorted(blocks, key=lambda root: ids.index(blocks[root][0])) if len(blocks[root]) > 1]


def _candidate_a(ids: list[str], positions: dict[str, float], tolerance: float) -> dict[str, Any]:
    """Evaluate inversion-rate order consistency with tied pairs excluded."""
    comparable = 0
    inversions = 0
    for left, left_id in enumerate(ids):
        for right_id in ids[left + 1 :]:
            difference = positions[left_id] - positions[right_id]
            if abs(difference) <= tolerance:
                continue
            comparable += 1
            inversions += int(difference > 0)
    if comparable == 0:
        return {"status": "undefined", "value": None, "inversions": 0, "comparable_pairs": 0}
    return {
        "status": "computed",
        "value": 1.0 - inversions / comparable,
        "inversions": inversions,
        "comparable_pairs": comparable,
    }


def _candidate_b(ids: list[str], positions: dict[str, float], tolerance: float) -> dict[str, Any]:
    """Evaluate normalized adjacent spacing consistency in declared sequence."""
    gaps = [abs(positions[right] - positions[left]) for left, right in zip(ids, ids[1:])]
    mean_gap = sum(gaps) / len(gaps) if gaps else 0.0
    if not gaps or mean_gap <= tolerance:
        return {
            "status": "undefined",
            "value": None,
            "gaps": gaps,
            "mean_gap": mean_gap,
            "normalized_deviation": None,
        }
    deviation = sum(abs(gap - mean_gap) for gap in gaps) / len(gaps) / mean_gap
    return {
        "status": "computed",
        "value": 1.0 - min(1.0, deviation),
        "gaps": gaps,
        "mean_gap": mean_gap,
        "normalized_deviation": deviation,
    }


def evaluate_case(case: dict[str, Any], object_ids: list[str], tolerance: float) -> dict[str, Any]:
    """Evaluate one fixture while retaining exclusion and provenance details."""
    axis = case.get("axis")
    objects = case["objects"]
    if axis is None:
        return {
            "status": "not_evaluated",
            "reason": "explicit AxisSpec is missing",
            "candidate_a": {"status": "not_evaluated", "value": None},
            "candidate_b": {"status": "not_evaluated", "value": None},
        }
    axis_norm = math.hypot(axis[0], axis[1])
    if not math.isfinite(axis_norm) or abs(axis_norm - 1.0) > 1e-9:
        return {
            "status": "invalid",
            "reason": "axis is not a finite unit vector",
            "candidate_a": {"status": "invalid", "value": None},
            "candidate_b": {"status": "invalid", "value": None},
        }

    origin = case["frame_origin"]
    scale = case["unit_to_analysis"]
    positions: dict[str, float] = {}
    excluded: dict[str, str] = {}
    invalid: dict[str, str] = {}
    anchors: dict[str, tuple[float, float]] = {}
    for object_id in object_ids:
        record = objects[object_id]
        status = record["geometry_status"]
        if status == "not_available":
            excluded[object_id] = "geometry not available"
            continue
        if status != "computed":
            invalid[object_id] = record.get("reason", "geometry status is invalid")
            continue
        try:
            source_anchor = _mean_vertex(record["vertices"])
        except ValueError as error:
            invalid[object_id] = str(error)
            continue
        anchor = (source_anchor[0] * scale, source_anchor[1] * scale)
        anchors[object_id] = anchor
        positions[object_id] = (anchor[0] - origin[0]) * axis[0] + (anchor[1] - origin[1]) * axis[1]

    if invalid:
        return {
            "status": "invalid",
            "reason": "invalid geometry reached descriptor",
            "anchors": anchors,
            "positions": positions,
            "excluded": excluded,
            "invalid": invalid,
            "candidate_a": {"status": "invalid", "value": None},
            "candidate_b": {"status": "invalid", "value": None},
        }
    usable_ids = [object_id for object_id in object_ids if object_id in positions]
    if len(usable_ids) < 2:
        candidate_a = {"status": "undefined", "value": None, "inversions": 0, "comparable_pairs": 0}
        candidate_b = {"status": "undefined", "value": None, "gaps": [], "mean_gap": 0.0, "normalized_deviation": None}
    else:
        candidate_a = _candidate_a(usable_ids, positions, tolerance)
        candidate_b = _candidate_b(usable_ids, positions, tolerance)
    overall_status = "computed" if candidate_a["status"] == "computed" else "undefined"
    return {
        "status": overall_status,
        "anchors": anchors,
        "positions": positions,
        "excluded": excluded,
        "tie_blocks": _tie_blocks(usable_ids, positions, tolerance),
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
    }


def assert_expected(results: dict[str, dict[str, Any]]) -> None:
    """Check the hand-computable oracle so accidental probe drift is visible."""
    assert results["aligned"]["candidate_a"]["value"] == 1.0
    assert results["reversed"]["candidate_a"]["value"] == 0.0
    assert results["reversed"]["candidate_b"]["value"] == 1.0
    assert results["uneven_spacing"]["candidate_a"]["value"] == 1.0
    assert math.isclose(results["uneven_spacing"]["candidate_b"]["value"], 0.8)
    assert results["partial_ties"]["tie_blocks"] == [["A", "B"]]
    assert results["partial_ties"]["candidate_a"]["value"] == 1.0
    assert results["all_ties"]["status"] == "undefined"
    assert results["translation"]["candidate_a"]["value"] == results["aligned"]["candidate_a"]["value"]
    assert results["positive_scale_unit_conversion"]["candidate_a"]["value"] == results["aligned"]["candidate_a"]["value"]
    assert results["geometry_frame_rotation"]["candidate_a"]["value"] == results["aligned"]["candidate_a"]["value"]
    assert results["geometry_rotation_fixed_axis"]["status"] == "undefined"
    assert results["axis_reversal"]["candidate_a"]["value"] == 0.0
    assert results["degenerate_geometry"]["status"] == "invalid"
    assert results["missing_geometry"]["status"] == "computed"
    assert results["missing_geometry"]["excluded"] == {"B": "geometry not available"}


def main() -> None:
    """Load fixtures, run the oracle, assert invariants, and write JSON output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=Path(__file__).with_name("fixtures.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    object_ids = fixture["declared_object_ids"]
    tolerance = fixture["tolerance"]
    results = {
        case["id"]: evaluate_case(case, object_ids, tolerance)
        for case in fixture["cases"]
    }
    assert_expected(results)
    payload = {
        "schema": "relative-order-design-oracle/v1",
        "fixture": str(args.fixture).replace("\\", "/"),
        "declared_object_ids": object_ids,
        "tolerance": tolerance,
        "candidate_a": "inversion-rate/order-consistency",
        "candidate_b": "normalized-adjacent-spacing-consistency",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({case_id: {"status": result["status"], "a": result["candidate_a"], "b": result["candidate_b"]} for case_id, result in results.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
