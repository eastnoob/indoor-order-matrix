"""Run the design-only furniture-group trend and neighbor comparison.

The probe expands compact rectangle fixtures into explicit plan triangles, then
compares geometry PCA, member-frame consensus, vertex-sensitive PCA, k-nearest
centers, and normalized boundary gaps. It never imports production adapters.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EPS = 1e-9


def _mat_add(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    """Add two 2x2 matrices."""
    return [[left[i][j] + right[i][j] for j in range(2)] for i in range(2)]


def _mat_scale(matrix: list[list[float]], factor: float) -> list[list[float]]:
    """Scale a 2x2 matrix by a scalar."""
    return [[factor * matrix[i][j] for j in range(2)] for i in range(2)]


def _rectangle_geometry(rectangle: dict[str, Any], sampling: str = "sparse") -> tuple[list[list[float]], list[list[list[float]]]]:
    """Expand a rectangle recipe into vertices and two canonical triangles."""
    cx, cy = rectangle["center"]
    width, height = rectangle["size"]
    angle = rectangle["angle"]
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    corners = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        corners.append([cx + sx * width * ux / 2 + sy * height * vx / 2,
                        cy + sx * width * uy / 2 + sy * height * vy / 2])
    triangles = [[corners[0], corners[1], corners[2]], [corners[0], corners[2], corners[3]]]
    if sampling == "dense_left":
        # Uneven boundary samples deliberately stress vertex-unweighted PCA.
        left = corners[0]
        right = corners[3]
        extra = [[left[0] * (1 - t) + right[0] * t, left[1] * (1 - t) + right[1] * t]
                 for t in (0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09)]
        return corners + extra, triangles
    return corners, triangles


def _member_geometry(member: dict[str, Any]) -> tuple[list[list[float]], list[list[list[float]]]] | None:
    """Return explicit member vertices and triangles, or None for unavailable geometry."""
    if member.get("geometry_status") != "computed":
        return None
    return _rectangle_geometry(member["rectangle"], member.get("vertex_sampling", "sparse"))


def _triangle_stats(triangle: list[list[float]]) -> tuple[float, tuple[float, float], list[list[float]]]:
    """Return area, centroid, and exact uniform-triangle covariance."""
    a, b, c = triangle
    cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    area = abs(cross) / 2.0
    centroid = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)
    second = [[0.0, 0.0], [0.0, 0.0]]
    for first in triangle:
        for i in range(2):
            for j in range(2):
                # Dirichlet triangle moments use E[lambda_i^2]=1/6 and
                # E[lambda_i lambda_j]=1/12; doubling the diagonal terms
                # keeps the area-weighted covariance tessellation invariant.
                second[i][j] += 2.0 * first[i] * first[j]
    for first in range(3):
        for second_index in range(first + 1, 3):
            for i in range(2):
                for j in range(2):
                    second[i][j] += triangle[first][i] * triangle[second_index][j]
                    second[i][j] += triangle[second_index][i] * triangle[first][j]
    second = _mat_scale(second, 1.0 / 12.0)
    covariance = [[second[i][j] - centroid[i] * centroid[j] for j in range(2)] for i in range(2)]
    return area, centroid, covariance


def _weighted_stats(triangles: list[list[list[float]]]) -> dict[str, Any]:
    """Combine triangle moments into area, centroid, and covariance."""
    total_area = 0.0
    weighted_center = [0.0, 0.0]
    moments = [[0.0, 0.0], [0.0, 0.0]]
    for triangle in triangles:
        area, center, covariance = _triangle_stats(triangle)
        total_area += area
        for i in range(2):
            weighted_center[i] += area * center[i]
            for j in range(2):
                moments[i][j] += area * (covariance[i][j] + center[i] * center[j])
    if total_area <= EPS:
        raise ValueError("no positive-area triangles")
    center = [value / total_area for value in weighted_center]
    covariance = [[moments[i][j] / total_area - center[i] * center[j] for j in range(2)] for i in range(2)]
    return {"area": total_area, "center": center, "covariance": covariance}


def _eigen_2x2(covariance: list[list[float]]) -> tuple[float, float, float]:
    """Return descending eigenvalues and the primary-axis angle for a symmetric 2x2 matrix."""
    xx, xy, yy = covariance[0][0], covariance[0][1], covariance[1][1]
    angle = 0.5 * math.atan2(2.0 * xy, xx - yy)
    trace = xx + yy
    discriminant = math.sqrt(max(0.0, (xx - yy) ** 2 + 4.0 * xy * xy))
    return (trace + discriminant) / 2.0, (trace - discriminant) / 2.0, angle % math.pi


def _axis_result(stats: dict[str, Any], basis: str) -> dict[str, Any]:
    """Convert covariance evidence into an undirected trend result."""
    primary, secondary, angle = _eigen_2x2(stats["covariance"])
    trace = primary + secondary
    strength = (primary - secondary) / trace if trace > EPS else 0.0
    if strength <= 0.05:
        return {"status": "undefined", "basis": basis, "angle": None, "strength": strength}
    return {"status": "computed", "basis": basis, "angle": angle, "strength": strength}


def _member_stats(member: dict[str, Any]) -> dict[str, Any] | None:
    """Build area-weighted statistics for one usable member."""
    geometry = _member_geometry(member)
    if geometry is None:
        return None
    vertices, triangles = geometry
    stats = _weighted_stats(triangles)
    stats["vertices"] = vertices
    stats["triangles"] = triangles
    return stats


def _group_representative(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a multi-part group representative without silently unioning overlaps."""
    usable = []
    excluded = {}
    for member in members:
        stats = _member_stats(member)
        if stats is None:
            excluded[member["id"]] = member.get("reason", "geometry unavailable")
        else:
            usable.append((member, stats))
    if not usable:
        return {"status": "not_available", "completeness": "not_applicable", "excluded": excluded}
    total_area = sum(stats["area"] for _, stats in usable)
    center = [sum(stats["area"] * stats["center"][i] for _, stats in usable) / total_area for i in range(2)]
    moments = [[0.0, 0.0], [0.0, 0.0]]
    for _, stats in usable:
        within = stats["covariance"]
        point = stats["center"]
        for i in range(2):
            for j in range(2):
                moments[i][j] += stats["area"] * (within[i][j] + point[i] * point[j])
    covariance = [[moments[i][j] / total_area - center[i] * center[j] for j in range(2)] for i in range(2)]
    return {
        "status": "computed",
        "completeness": "partial" if excluded else "complete",
        "center": center,
        "support_area": total_area,
        "covariance": covariance,
        "members": {member["id"]: stats for member, stats in usable},
        "excluded": excluded,
    }


def _vertex_unweighted_result(representative: dict[str, Any]) -> dict[str, Any]:
    """Compute a diagnostic PCA from vertices to expose tessellation sensitivity."""
    vertices = [vertex for stats in representative.get("members", {}).values() for vertex in stats["vertices"]]
    if len(vertices) < 2:
        return {"status": "undefined", "basis": "vertex_unweighted_pca"}
    center = [sum(vertex[i] for vertex in vertices) / len(vertices) for i in range(2)]
    covariance = [[sum((vertex[i] - center[i]) * (vertex[j] - center[j]) for vertex in vertices) / len(vertices)
                   for j in range(2)] for i in range(2)]
    return _axis_result({"covariance": covariance}, "vertex_unweighted_pca")


def _member_consensus(representative: dict[str, Any]) -> dict[str, Any]:
    """Compute an undirected doubled-angle consensus from member terminal geometry."""
    usable = representative.get("members", {})
    if not usable:
        return {"status": "not_available", "basis": "member_frame_consensus"}
    cosine = sine = total_weight = 0.0
    support = 0
    for stats in usable.values():
        primary, secondary, angle = _eigen_2x2(stats["covariance"])
        anisotropy = (primary - secondary) / (primary + secondary) if primary + secondary > EPS else 0.0
        if anisotropy <= 0.05:
            continue
        weight = stats["area"] * anisotropy
        cosine += weight * math.cos(2.0 * angle)
        sine += weight * math.sin(2.0 * angle)
        total_weight += weight
        support += 1
    if total_weight <= EPS:
        return {"status": "undefined", "basis": "member_frame_consensus", "member_support": 0, "strength": 0.0}
    resultant = math.hypot(cosine, sine) / total_weight
    result = {"status": "computed" if resultant > 0.05 else "undefined",
              "basis": "member_frame_consensus", "member_support": support,
              "strength": resultant, "angle": (0.5 * math.atan2(sine, cosine)) % math.pi}
    if result["status"] == "undefined":
        result["angle"] = None
    return result


def _trend_case(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate all trend candidates for one authored group fixture."""
    representative = _group_representative(case["members"])
    if representative["status"] != "computed":
        return {"representative": representative, "geometry_pca": {"status": "not_available"},
                "member_consensus": {"status": "not_available"}, "vertex_unweighted_pca": {"status": "not_available"}}
    member_consensus = _member_consensus(representative)
    trend_completeness = representative["completeness"] if member_consensus["status"] == "computed" else "not_applicable"
    return {
        "representative": {key: value for key, value in representative.items() if key != "members"},
        "geometry_pca": _axis_result(representative, "area_weighted_group_pca"),
        "member_consensus": member_consensus,
        "trend_completeness": trend_completeness,
        "vertex_unweighted_pca": _vertex_unweighted_result(representative),
    }


def _point_segment_distance(point: list[float], first: list[float], second: list[float]) -> float:
    """Return the Euclidean distance from a point to a line segment."""
    dx, dy = second[0] - first[0], second[1] - first[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= EPS:
        return math.hypot(point[0] - first[0], point[1] - first[1])
    t = max(0.0, min(1.0, ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy) / length_sq))
    return math.hypot(point[0] - (first[0] + t * dx), point[1] - (first[1] + t * dy))


def _orientation(first: list[float], second: list[float], third: list[float]) -> float:
    """Return the signed 2D cross product used by segment intersection."""
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0])


def _segments_intersect(a: list[float], b: list[float], c: list[float], d: list[float]) -> bool:
    """Return whether two closed segments intersect, including collinear contact."""
    values = (_orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b))
    if values[0] * values[1] < -EPS and values[2] * values[3] < -EPS:
        return True
    def on_segment(p: list[float], q: list[float], r: list[float]) -> bool:
        """Return whether q lies inside the axis-aligned bounds of p-r."""
        return min(p[0], r[0]) - EPS <= q[0] <= max(p[0], r[0]) + EPS and min(p[1], r[1]) - EPS <= q[1] <= max(p[1], r[1]) + EPS
    return any(abs(value) <= EPS and on_segment(pair[0], pair[1], pair[2]) for value, pair in (
        (values[0], (a, c, b)), (values[1], (a, d, b)), (values[2], (c, a, d)), (values[3], (c, b, d))))


def _point_in_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    """Use a ray crossing test for the convex rectangle polygons in the fixtures."""
    inside = False
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if (first[1] > point[1]) != (second[1] > point[1]):
            x_cross = (second[0] - first[0]) * (point[1] - first[1]) / (second[1] - first[1]) + first[0]
            if point[0] < x_cross:
                inside = not inside
    return inside


def _polygon_gap(first: list[list[float]], second: list[list[float]]) -> tuple[float, bool]:
    """Return boundary gap and overlap flag for two convex polygons."""
    edges_first = list(zip(first, first[1:] + first[:1]))
    edges_second = list(zip(second, second[1:] + second[:1]))
    overlap = any(_point_in_polygon(point, second) for point in first) or any(_point_in_polygon(point, first) for point in second)
    overlap = overlap or any(_segments_intersect(a, b, c, d) for a, b in edges_first for c, d in edges_second)
    if overlap:
        return 0.0, True
    gap = min(_point_segment_distance(point, a, b) for point in first for a, b in edges_second)
    gap = min(gap, min(_point_segment_distance(point, a, b) for point in second for a, b in edges_first))
    return gap, False


def _neighbor_representatives(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build group representatives after applying the fixture's positive scale."""
    scale = case["scale"]
    representatives = {}
    for group in case["groups"]:
        scaled_members = []
        for member in group["members"]:
            copied = json.loads(json.dumps(member))
            if "rectangle" in copied:
                copied["rectangle"]["center"] = [value * scale for value in copied["rectangle"]["center"]]
                copied["rectangle"]["size"] = [value * scale for value in copied["rectangle"]["size"]]
            scaled_members.append(copied)
        representatives[group["id"]] = _group_representative(scaled_members)
    return representatives


def _group_distance(first: dict[str, Any], second: dict[str, Any]) -> float:
    """Return Euclidean distance between group representative centers."""
    return math.hypot(first["center"][0] - second["center"][0], first["center"][1] - second["center"][1])


def _knn_edges(representatives: dict[str, dict[str, Any]], k: int) -> dict[str, Any]:
    """Return symmetrized k-nearest edges while retaining all kth-distance ties."""
    directed = {}
    for group_id, representative in representatives.items():
        distances = sorted((_group_distance(representative, other), other_id)
                           for other_id, other in representatives.items() if other_id != group_id)
        if not distances:
            continue
        cutoff = distances[min(k, len(distances)) - 1][0]
        directed[group_id] = [other_id for distance, other_id in distances if distance <= cutoff + EPS]
    edges = set()
    for source, targets in directed.items():
        for target in targets:
            edges.add("--".join(sorted((source, target))))
    return {"edges": sorted(edges), "directed": directed}


def _boundary_gap_edges(representatives: dict[str, dict[str, Any]], threshold: float) -> dict[str, Any]:
    """Return normalized boundary-gap edges and preserve member-pair provenance."""
    edges = []
    ids = sorted(representatives)
    for index, first_id in enumerate(ids):
        for second_id in ids[index + 1:]:
            first, second = representatives[first_id], representatives[second_id]
            minimum_gap = math.inf
            overlap = False
            provenance = None
            for first_member, first_stats in first.get("members", {}).items():
                for second_member, second_stats in second.get("members", {}).items():
                    first_vertices = first_stats["vertices"]
                    second_vertices = second_stats["vertices"]
                    gap, pair_overlap = _polygon_gap(first_vertices, second_vertices)
                    if gap < minimum_gap:
                        minimum_gap = gap
                        provenance = {"first_member": first_member, "second_member": second_member}
                    overlap = overlap or pair_overlap
            denominator = math.sqrt(first["support_area"] + second["support_area"])
            normalized_gap = minimum_gap / denominator if denominator > EPS else math.inf
            if normalized_gap <= threshold + EPS:
                edges.append({"edge": f"{first_id}--{second_id}", "gap": minimum_gap,
                              "normalized_gap": normalized_gap, "overlap": overlap,
                              "member_pair": provenance})
    return {"edges": [record["edge"] for record in edges], "relations": edges}


def _raw_gap_edges(representatives: dict[str, dict[str, Any]], threshold: float) -> list[str]:
    """Return a raw-distance boundary-gap candidate used only as a scale diagnostic."""
    result = []
    ids = sorted(representatives)
    for index, first_id in enumerate(ids):
        for second_id in ids[index + 1:]:
            minimum_gap = math.inf
            first, second = representatives[first_id], representatives[second_id]
            for first_stats in first.get("members", {}).values():
                for second_stats in second.get("members", {}).values():
                    gap, _ = _polygon_gap(first_stats["vertices"], second_stats["vertices"])
                    minimum_gap = min(minimum_gap, gap)
            if minimum_gap <= threshold + EPS:
                result.append(f"{first_id}--{second_id}")
    return result


def _neighbor_case(case: dict[str, Any]) -> dict[str, Any]:
    """Compare center-kNN, raw gap, and normalized boundary-gap relations."""
    representatives = _neighbor_representatives(case)
    return {
        "representative_centers": {group_id: value.get("center") for group_id, value in representatives.items()},
        "knn": _knn_edges(representatives, case["knn_k"]),
        "raw_gap": {"edges": _raw_gap_edges(representatives, case["raw_gap_threshold"])},
        "normalized_gap": _boundary_gap_edges(representatives, case["normalized_gap_threshold"]),
        "truth_edges": case["truth_edges"],
    }


def _assert_expected(fixtures: dict[str, Any], trends: dict[str, Any], neighbors: dict[str, Any]) -> None:
    """Check the declared synthetic truth and the design claims before writing output."""
    for case in fixtures["trend_cases"]:
        result = trends[case["id"]]
        expected = case["expected"]
        consensus = result["member_consensus"]
        assert consensus["status"] == expected["status"], case["id"]
        assert result["trend_completeness"] == expected["completeness"], case["id"]
        if expected.get("angle") is not None:
            assert consensus["angle"] is not None and min(abs(consensus["angle"] - expected["angle"]), math.pi - abs(consensus["angle"] - expected["angle"])) < 1e-6, case["id"]
    sparse = trends["tessellation_sparse"]
    dense = trends["tessellation_dense"]
    assert abs(sparse["member_consensus"]["angle"] - dense["member_consensus"]["angle"]) < 1e-6
    assert abs(sparse["vertex_unweighted_pca"]["angle"] - dense["vertex_unweighted_pca"]["angle"]) > 1e-3
    first, scaled = neighbors["local_components"], neighbors["local_components_scaled"]
    assert first["normalized_gap"]["edges"] == first["truth_edges"]
    assert scaled["normalized_gap"]["edges"] == scaled["truth_edges"]
    assert first["normalized_gap"]["edges"] == scaled["normalized_gap"]["edges"]
    assert first["raw_gap"]["edges"] != scaled["raw_gap"]["edges"]
    assert any("A--F" == edge for edge in first["normalized_gap"]["edges"])
    assert any(record["overlap"] for record in first["normalized_gap"]["relations"] if record["edge"] == "A--F")
    tie = neighbors["knn_tie"]
    assert set(tie["knn"]["directed"]["T0"]) == {"T1", "T2"}


def main() -> None:
    """Run the deterministic comparison and write an auditable JSON result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=Path(__file__).with_name("fixtures.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture_bytes = args.fixture.read_bytes()
    fixtures = json.loads(fixture_bytes)
    trends = {case["id"]: _trend_case(case) for case in fixtures["trend_cases"]}
    neighbors = {case["id"]: _neighbor_case(case) for case in fixtures["neighbor_cases"]}
    _assert_expected(fixtures, trends, neighbors)
    output = {
        "schema": "group-level-design-probe/v1",
        "fixture": str(args.fixture.resolve()).replace("\\", "/"),
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "selected_trend_baseline": "member_frame_consensus",
        "selected_neighbor_baseline": "normalized_boundary_gap",
        "results": {"trend_cases": trends, "neighbor_cases": neighbors},
        "limitations": [
            "synthetic geometry truth is computational and contains no human labels",
            "rectangle fixture shorthand is expanded before the comparison",
            "member support is retained as a multi-part collection; overlaps are not unioned",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"trend_cases": list(trends), "neighbor_cases": list(neighbors)}, indent=2))


if __name__ == "__main__":
    main()
