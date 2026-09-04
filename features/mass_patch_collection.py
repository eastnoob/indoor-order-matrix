"""Union-aware queries for several MassPatch records owned by one object."""

from __future__ import annotations

import math
from collections.abc import Iterable

from .geometry_substitutes import MassPatch
from .geometry_views import (
    PlanProjection,
    VerticalIntervalResult,
    occlusion_intersections,
    plan_projection,
    vertical_intervals_at,
)


def merge_vertical_intervals(
    intervals: Iterable[tuple[float, float]],
    tolerance: float = 1e-9,
) -> tuple[tuple[float, float], ...]:
    """Merge overlapping or touching occupied height intervals."""
    if not math.isfinite(float(tolerance)) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and non-negative")
    normalized = []
    for lower, upper in intervals:
        lower = float(lower)
        upper = float(upper)
        if not math.isfinite(lower) or not math.isfinite(upper):
            raise ValueError("interval endpoints must be finite")
        if upper < lower:
            lower, upper = upper, lower
        if upper > lower:
            normalized.append((lower, upper))
    merged: list[list[float]] = []
    for lower, upper in sorted(normalized):
        if not merged or lower > merged[-1][1] + tolerance:
            merged.append([lower, upper])
        else:
            merged[-1][1] = max(merged[-1][1], upper)
    return tuple((lower, upper) for lower, upper in merged)


def _projection_shape(projection: PlanProjection):
    """Convert a plan projection's serialized components into Shapely geometry."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    polygons = []
    for component in projection.components:
        exterior = component.get("exterior", ())
        holes = component.get("holes", ())
        if len(exterior) < 3:
            continue
        polygon = Polygon(exterior, holes)
        if polygon.is_valid and not polygon.is_empty and polygon.area > 0.0:
            polygons.append(polygon)
    return unary_union(polygons) if polygons else None


def union_plan_geometry(
    patches: Iterable[MassPatch],
    analysis_plane: object | None = None,
):
    """Return the 2D union of all patch plan projections."""
    from shapely.ops import unary_union

    geometries = []
    for patch in patches:
        geometry = _projection_shape(plan_projection(patch, analysis_plane))
        if geometry is not None and not geometry.is_empty:
            geometries.append(geometry)
    # The union is the physical occupancy fact; summing member areas would
    # double-count an overlapping seat/back or table/leg interface.
    return unary_union(geometries) if geometries else None


def _patch_xy_bounds(patch: MassPatch) -> tuple[float, float, float, float]:
    """Return an axis-aligned XY broad-phase bound for one patch."""
    if not patch.vertices:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [float(vertex[0]) for vertex in patch.vertices]
    ys = [float(vertex[1]) for vertex in patch.vertices]
    return min(xs), min(ys), max(xs), max(ys)


def _contains_xy(
    bounds: tuple[float, float, float, float],
    point: tuple[float, float],
) -> bool:
    """Return whether a broad-phase bound contains a plan query point."""
    return (
        bounds[0] <= point[0] <= bounds[2]
        and bounds[1] <= point[1] <= bounds[3]
    )


def vertical_intervals_at_collection(
    patches: Iterable[MassPatch],
    point: tuple[float, float],
    analysis_plane: object | None = None,
) -> VerticalIntervalResult:
    """Return merged occupied heights for all patches at one plan point."""
    intervals = []
    uncertainties = set()
    for patch in patches:
        if not _contains_xy(_patch_xy_bounds(patch), point):
            continue
        result = vertical_intervals_at(
            patch,
            point,
            analysis_plane=analysis_plane,
        )
        intervals.extend(result.intervals)
        uncertainties.update(result.uncertainties)
    merged = merge_vertical_intervals(intervals)
    if not merged:
        uncertainties.add("no_vertical_interval")
    return VerticalIntervalResult(merged, tuple(sorted(uncertainties)))


def collection_occludes(
    patches: Iterable[MassPatch],
    query: object,
) -> bool:
    """Return whether any member patch blocks the supplied query."""
    for patch in patches:
        result = occlusion_intersections(patch, query)
        # Occlusion is existential: duplicate member hits do not increase a
        # boolean result, while an uncertain patch is kept visible to callers
        # through the lower-level query API.
        if "occluded" in result:
            return True
    return False


def _patch_aabb_volume(patch: MassPatch) -> float:
    """Return the axis-aligned volume proxy for one patch."""
    if not patch.vertices:
        return 0.0
    coordinates = tuple(
        (
            min(float(vertex[axis]) for vertex in patch.vertices),
            max(float(vertex[axis]) for vertex in patch.vertices),
        )
        for axis in range(3)
    )
    return math.prod(max(0.0, upper - lower) for lower, upper in coordinates)


def _aabb_intersection_volume(first: MassPatch, second: MassPatch) -> float:
    """Return the pairwise AABB intersection volume proxy."""
    if not first.vertices or not second.vertices:
        return 0.0
    total = 1.0
    for axis in range(3):
        first_bounds = (
            min(float(vertex[axis]) for vertex in first.vertices),
            max(float(vertex[axis]) for vertex in first.vertices),
        )
        second_bounds = (
            min(float(vertex[axis]) for vertex in second.vertices),
            max(float(vertex[axis]) for vertex in second.vertices),
        )
        total *= max(
            0.0,
            min(first_bounds[1], second_bounds[1])
            - max(first_bounds[0], second_bounds[0]),
        )
    return total


def collection_overlap_report(
    patches: Iterable[MassPatch],
    tolerance: float = 1e-9,
) -> dict[str, object]:
    """Report overlap diagnostics separately from union occupancy facts."""
    patches = tuple(patches)
    if not math.isfinite(float(tolerance)) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and non-negative")
    union = union_plan_geometry(patches)
    plan_areas = []
    overlap_pairs = []
    pairwise_volume_proxy = 0.0
    for index, patch in enumerate(patches):
        projection = _projection_shape(plan_projection(patch))
        plan_areas.append(float(projection.area) if projection is not None else 0.0)
        for other_index in range(index):
            other = patches[other_index]
            other_projection = _projection_shape(plan_projection(other))
            if projection is not None and other_projection is not None:
                overlap_area = float(projection.intersection(other_projection).area)
            else:
                overlap_area = 0.0
            volume_overlap = _aabb_intersection_volume(patch, other)
            if overlap_area > tolerance or volume_overlap > tolerance:
                overlap_pairs.append(
                    {
                        "first_patch_id": other.id,
                        "second_patch_id": patch.id,
                        "plan_overlap_area": overlap_area,
                        "volume_overlap_proxy": volume_overlap,
                    }
                )
            pairwise_volume_proxy += volume_overlap
    member_plan_area = sum(plan_areas)
    union_plan_area = float(union.area) if union is not None else 0.0
    member_volume_proxy = sum(_patch_aabb_volume(patch) for patch in patches)
    return {
        "patch_count": len(patches),
        "overlap_pair_count": len(overlap_pairs),
        "overlap_pairs": tuple(overlap_pairs),
        "member_plan_area_sum": member_plan_area,
        "union_plan_area": union_plan_area,
        "plan_overlap_area": max(0.0, member_plan_area - union_plan_area),
        "member_volume_proxy_sum": member_volume_proxy,
        "pairwise_volume_overlap_proxy": pairwise_volume_proxy,
        "union_volume_proxy": max(0.0, member_volume_proxy - pairwise_volume_proxy),
    }


__all__ = [
    "collection_occludes",
    "collection_overlap_report",
    "merge_vertical_intervals",
    "union_plan_geometry",
    "vertical_intervals_at_collection",
]
