"""Run a deterministic comparison of relative-order design candidates.

This design-only probe keeps the external reference sequence separate from
geometry, compares pairwise and transitive tie semantics, and reports anchor
sensitivity without entering the production import path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _mean_vertex(vertices: list[list[float]]) -> tuple[float, float]:
    """Return the arithmetic mean of all finite projected vertices."""
    if len(vertices) < 3:
        raise ValueError("fewer than three projected vertices")
    if any(len(vertex) != 2 or not all(math.isfinite(value) for value in vertex) for vertex in vertices):
        raise ValueError("non-finite or malformed projected vertex")
    return (
        sum(vertex[0] for vertex in vertices) / len(vertices),
        sum(vertex[1] for vertex in vertices) / len(vertices),
    )


def _area_weighted_triangle_centroid(record: dict[str, Any]) -> tuple[float, float]:
    """Return an area-weighted centroid from explicitly supplied plan triangles."""
    triangles = record.get("triangles")
    if not triangles:
        raise ValueError("triangle representation is not available")
    total_area = 0.0
    weighted_x = 0.0
    weighted_y = 0.0
    for triangle in triangles:
        if len(triangle) != 3 or any(len(vertex) != 2 for vertex in triangle):
            raise ValueError("malformed triangle representation")
        if any(not all(math.isfinite(value) for value in vertex) for vertex in triangle):
            raise ValueError("non-finite triangle coordinate")
        first, second, third = triangle
        signed_area = (
            (second[0] - first[0]) * (third[1] - first[1])
            - (second[1] - first[1]) * (third[0] - first[0])
        ) / 2.0
        area = abs(signed_area)
        if area <= 0.0:
            continue
        centroid_x = (first[0] + second[0] + third[0]) / 3.0
        centroid_y = (first[1] + second[1] + third[1]) / 3.0
        total_area += area
        weighted_x += area * centroid_x
        weighted_y += area * centroid_y
    if total_area <= 0.0:
        raise ValueError("triangle representation has no positive area")
    return weighted_x / total_area, weighted_y / total_area


def _axis_reason(axis: Any) -> str | None:
    """Return a validation reason when an explicit axis is absent or invalid."""
    if axis is None:
        return "reference axis is missing"
    if not isinstance(axis, list) or len(axis) != 2:
        return "axis is not a finite unit vector"
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in axis):
        return "axis is not a finite unit vector"
    norm = math.hypot(axis[0], axis[1])
    if abs(norm - 1.0) > 1e-9:
        return "axis is not a finite unit vector"
    return None


def _reference_order(case: dict[str, Any], default_order: list[str]) -> tuple[list[str] | None, dict[str, Any]]:
    """Resolve only explicit reference-order fields and preserve their provenance."""
    if "reference_order" in case:
        order = case["reference_order"]
        provenance = {"source": "case.reference_order", "override": True}
    else:
        order = default_order
        provenance = {"source": "fixture.reference_order", "override": False}
    if order is None:
        return None, provenance
    if not isinstance(order, list) or len(order) < 2 or len(set(order)) != len(order):
        return None, {**provenance, "invalid": True}
    return list(order), provenance


def _tie_edges(ids: list[str], positions: dict[str, float], tolerance: float) -> list[list[str]]:
    """Return direct tolerance edges in reference-order traversal order."""
    edges: list[list[str]] = []
    for left, left_id in enumerate(ids):
        for right_id in ids[left + 1 :]:
            difference = abs(positions[left_id] - positions[right_id])
            # Preserve the inclusive boundary despite binary rounding at exactly tolerance.
            if difference <= tolerance or math.isclose(difference, tolerance, abs_tol=1e-12):
                edges.append([left_id, right_id])
    return edges


def _transitive_blocks(ids: list[str], edges: list[list[str]]) -> list[list[str]]:
    """Return connected tolerance blocks for comparison only, never silently."""
    parent = list(range(len(ids)))
    index = {object_id: position for position, object_id in enumerate(ids)}

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        left_root, right_root = find(index[left]), find(index[right])
        if left_root != right_root:
            parent[right_root] = left_root

    for left, right in edges:
        union(left, right)
    groups: dict[int, list[str]] = {}
    for object_id in ids:
        groups.setdefault(find(index[object_id]), []).append(object_id)
    return [groups[root] for root in sorted(groups, key=lambda root: index[groups[root][0]]) if len(groups[root]) > 1]


def _candidate_a(
    ids: list[str],
    positions: dict[str, float],
    tolerance: float,
    tie_semantics: str,
) -> dict[str, Any]:
    """Evaluate order consistency under an explicit tie interpretation."""
    edges = _tie_edges(ids, positions, tolerance)
    edge_pairs = {tuple(edge) for edge in edges}
    blocks = _transitive_blocks(ids, edges)
    block_index = {
        object_id: block_index
        for block_index, block in enumerate(blocks)
        for object_id in block
    }
    comparable_pairs = 0
    inversions = 0
    for left, left_id in enumerate(ids):
        for right_id in ids[left + 1 :]:
            pair_tied = (left_id, right_id) in edge_pairs
            block_tied = (
                left_id in block_index
                and right_id in block_index
                and block_index[left_id] == block_index[right_id]
            )
            if (pair_tied if tie_semantics == "pairwise_edges" else block_tied):
                continue
            comparable_pairs += 1
            inversions += int(positions[left_id] > positions[right_id])
    if comparable_pairs == 0:
        value = None
        status = "undefined"
    else:
        value = 1.0 - inversions / comparable_pairs
        status = "computed"
    return {
        "status": status,
        "value": value,
        "inversions": inversions,
        "comparable_pairs": comparable_pairs,
        "tie_semantics": tie_semantics,
        "tie_edges": edges,
        "transitive_blocks": blocks,
    }


def _candidate_b(ids: list[str], positions: dict[str, float], tolerance: float) -> dict[str, Any]:
    """Evaluate normalized adjacent spacing while retaining zero tie gaps."""
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


def _status_for_geometry(
    usable_ids: list[str],
    excluded: dict[str, str],
    invalid: dict[str, str],
) -> tuple[str, str, str]:
    """Assign the smallest state that preserves missing, invalid, and count causes."""
    if invalid:
        return "invalid", "invalid geometry reached descriptor", "not_computable"
    if not usable_ids:
        return "not_available", "no usable geometry", "not_applicable"
    if len(usable_ids) < 2:
        return "undefined", "fewer than two usable objects", "not_applicable"
    if excluded:
        return "computed", "some reference-order members were excluded", "partial"
    return "computed", "all reference-order members are usable", "complete"


def _evaluate_method(
    case: dict[str, Any],
    default_order: list[str],
    tolerance: float,
    anchor_method: str,
) -> dict[str, Any]:
    """Evaluate one anchor method with explicit status and provenance details."""
    reference_order, order_provenance = _reference_order(case, default_order)
    if reference_order is None:
        reason = "reference order is missing" if case.get("reference_order") is None else "reference order is invalid"
        return {
            "status": "not_evaluated",
            "completeness": "not_applicable",
            "reason": reason,
            "reference_order": None,
            "reference_order_provenance": order_provenance,
            "candidate_a": {"status": "not_evaluated", "value": None},
            "candidate_b": {"status": "not_evaluated", "value": None},
        }
    axis_reason = _axis_reason(case.get("axis"))
    if axis_reason:
        status = "not_evaluated" if case.get("axis") is None else "invalid"
        return {
            "status": status,
            "completeness": "not_applicable",
            "reason": axis_reason,
            "reference_order": reference_order,
            "reference_order_provenance": order_provenance,
            "candidate_a": {"status": status, "value": None},
            "candidate_b": {"status": status, "value": None},
        }
    scale = case.get("unit_to_analysis")
    if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0.0:
        return {
            "status": "invalid",
            "completeness": "not_computable",
            "reason": "source-to-analysis unit conversion is not positive and finite",
            "reference_order": reference_order,
            "reference_order_provenance": order_provenance,
            "candidate_a": {"status": "invalid", "value": None},
            "candidate_b": {"status": "invalid", "value": None},
        }

    objects = case["objects"]
    origin = case["frame_origin"]
    axis = case["axis"]
    anchors: dict[str, tuple[float, float]] = {}
    positions: dict[str, float] = {}
    excluded: dict[str, str] = {}
    invalid: dict[str, str] = {}
    for object_id in reference_order:
        record = objects.get(object_id)
        if record is None:
            invalid[object_id] = "reference-order object has no geometry record"
            continue
        geometry_status = record.get("geometry_status")
        if geometry_status == "not_available":
            excluded[object_id] = "geometry not available"
            continue
        if geometry_status != "computed":
            invalid[object_id] = record.get("reason", "geometry status is invalid")
            continue
        try:
            source_anchor = (
                _mean_vertex(record["vertices"])
                if anchor_method == "arithmetic_mean"
                else _area_weighted_triangle_centroid(record)
            )
        except (KeyError, TypeError, ValueError) as error:
            if anchor_method == "area_weighted_triangle_centroid" and "triangles" not in record:
                excluded[object_id] = str(error)
            else:
                invalid[object_id] = str(error)
            continue
        anchor = (source_anchor[0] * scale, source_anchor[1] * scale)
        anchors[object_id] = anchor
        positions[object_id] = (anchor[0] - origin[0]) * axis[0] + (anchor[1] - origin[1]) * axis[1]

    usable_ids = [object_id for object_id in reference_order if object_id in positions]
    status, reason, completeness = _status_for_geometry(usable_ids, excluded, invalid)
    result: dict[str, Any] = {
        "status": status,
        "completeness": completeness,
        "reason": reason,
        "anchor_method": anchor_method,
        "anchors": anchors,
        "positions": positions,
        "excluded": excluded,
        "invalid": invalid,
        "reference_order": reference_order,
        "reference_order_provenance": order_provenance,
    }
    if status in {"not_available", "undefined", "invalid"}:
        result["candidate_a"] = {"status": status, "value": None}
        result["candidate_b"] = {"status": status, "value": None}
        if status == "undefined" and len(usable_ids) >= 2:
            result["candidate_a"] = _candidate_a(usable_ids, positions, tolerance, "pairwise_edges")
            result["candidate_b"] = _candidate_b(usable_ids, positions, tolerance)
            result["status"] = "undefined"
            result["reason"] = "no comparable pair remains"
        return result
    result["candidate_a"] = _candidate_a(usable_ids, positions, tolerance, "pairwise_edges")
    result["candidate_b"] = _candidate_b(usable_ids, positions, tolerance)
    result["tie_semantics_comparison"] = {
        "pairwise_edges": result["candidate_a"],
        "transitive_blocks": _candidate_a(usable_ids, positions, tolerance, "transitive_blocks"),
    }
    if result["candidate_a"]["status"] == "undefined":
        result["status"] = "undefined"
        result["completeness"] = "not_applicable"
        result["reason"] = "no comparable pair remains"
    return result


def evaluate_case(case: dict[str, Any], default_order: list[str], tolerance: float) -> dict[str, Any]:
    """Evaluate arithmetic and supported area-weighted anchors without hiding limits."""
    arithmetic = _evaluate_method(case, default_order, tolerance, "arithmetic_mean")
    area_weighted = _evaluate_method(case, default_order, tolerance, "area_weighted_triangle_centroid")
    result = dict(arithmetic)
    result["anchor_methods"] = {
        "arithmetic_mean": arithmetic,
        "area_weighted_triangle_centroid": area_weighted,
    }
    return result


def _assert_value(actual: Any, expected: Any) -> None:
    """Compare numeric oracle values with a small tolerance for floating arithmetic."""
    if expected is None:
        assert actual is None, (actual, expected)
    else:
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9), (actual, expected)


def assert_expected(fixture: dict[str, Any], results: dict[str, dict[str, Any]]) -> None:
    """Run fixture-declared expected checks and design-specific tie/anchor checks."""
    for case in fixture["cases"]:
        result = results[case["id"]]
        expected = case["expected"]
        assert result["status"] == expected["status"], (case["id"], result["status"], expected)
        assert result["completeness"] == expected["completeness"], case["id"]
        assert result["candidate_a"]["status"] == expected["candidate_a_status"], case["id"]
        _assert_value(result["candidate_a"]["value"], expected["candidate_a_value"])
        assert result["candidate_b"]["status"] == expected["candidate_b_status"], case["id"]
        _assert_value(result["candidate_b"]["value"], expected["candidate_b_value"])
        assert isinstance(expected["reason_contains"], str) and expected["reason_contains"], case["id"]
    chain = results["chained_ties"]
    assert chain["candidate_a"]["tie_edges"] == [["A", "B"], ["B", "C"]]
    assert chain["tie_semantics_comparison"]["transitive_blocks"]["status"] == "undefined"
    assert chain["candidate_a"]["status"] == "computed"
    assert results["tolerance_boundary"]["candidate_a"]["tie_edges"] == [["A", "B"]]
    assert results["non_dictionary_reference_order"]["reference_order"] == ["zeta", "alpha", "middle"]
    assert results["missing_reference_order"]["status"] == "not_evaluated"
    sparse = results["tessellation_sparse"]
    dense = results["tessellation_dense"]
    _assert_value(sparse["candidate_a"]["value"], 1.0)
    _assert_value(dense["candidate_a"]["value"], 2.0 / 3.0)
    _assert_value(
        sparse["anchor_methods"]["area_weighted_triangle_centroid"]["candidate_a"]["value"],
        1.0,
    )
    _assert_value(
        dense["anchor_methods"]["area_weighted_triangle_centroid"]["candidate_a"]["value"],
        1.0,
    )
    assert dense["anchors"]["A"] != sparse["anchors"]["A"]


def main() -> None:
    """Run the deterministic probe and write a self-checking JSON oracle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=Path(__file__).with_name("fixtures.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    default_order = fixture["reference_order"]
    tolerance = fixture["tolerance"]
    results = {
        case["id"]: evaluate_case(case, default_order, tolerance)
        for case in fixture["cases"]
    }
    assert_expected(fixture, results)
    output = {
        "schema": "relative-order-design-oracle/v2",
        "fixture": str(args.fixture.resolve()).replace("\\", "/"),
        "fixture_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
        "reference_order": default_order,
        "reference_order_provenance": fixture["reference_order_provenance"],
        "tolerance": tolerance,
        "anchor_methods": ["arithmetic_mean", "area_weighted_triangle_centroid"],
        "selected_tie_semantics_for_candidate_a": "pairwise_edges",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        case_id: {
            "status": result["status"],
            "candidate_a": result["candidate_a"],
            "candidate_b": result["candidate_b"],
        }
        for case_id, result in results.items()
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
