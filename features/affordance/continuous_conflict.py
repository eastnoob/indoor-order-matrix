from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .grid_backend import SpatialGridBackend
from .models import Polygon, Rect, SceneModel

Geometry = Rect | Polygon


@dataclass(frozen=True)
class ContinuousConflict:
    # Continuous conflict source. source_shape/target_shape stay internal because
    # report JSON should describe the conflict, not serialize geometry objects.
    type: str
    severity: str
    source_id: str
    target_id: str
    object_ids: list[str]
    source_kind: str
    target_kind: str
    source_shape: Geometry
    target_shape: Geometry
    metadata: dict[str, Any]

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "object_ids": list(self.object_ids),
            "source_kind": self.source_kind,
            "target_kind": self.target_kind,
            "metadata": dict(self.metadata),
        }


def geometry_overlaps(left: Geometry, right: Geometry) -> bool:
    """Return true only for positive-area continuous overlap.

    Touching edges are intentionally false. This keeps exact adjacency from
    becoming a clearance/affordance conflict.
    """
    left_polygon = _as_polygon(left)
    right_polygon = _as_polygon(right)
    if not left_polygon.bounds.intersects(right_polygon.bounds):
        return False
    return _polygons_overlap(left_polygon, right_polygon)


def sample_overlap_cells(
    grid: SpatialGridBackend,
    left: Geometry,
    right: Geometry,
) -> set[tuple[int, int]]:
    """Rasterize an already-continuous overlap for debug/highlight only."""
    bounds = _intersection_bounds(left, right)
    if bounds is None:
        return set()
    cells = set()
    for row, col in grid.iter_indices_in_rect(bounds):
        cell = grid.cell_rect(row, col)
        if geometry_overlaps(cell, left) and geometry_overlaps(cell, right):
            cells.add((row, col))
    return cells


class ContinuousConflictEvaluator:
    def evaluate(self, scene: SceneModel) -> dict[str, Any]:
        conflicts: list[ContinuousConflict] = []
        conflicts.extend(self._affordance_blockers(scene))
        conflicts.extend(self._clearance_blockers(scene))
        conflicts.extend(self._road_affordance_conflicts(scene))

        affordance_conflicts = [
            conflict
            for conflict in conflicts
            if conflict.type == "affordance_blocked_by_furniture"
        ]
        aisle_conflicts = [
            conflict
            for conflict in conflicts
            if conflict.type in {"clearance_blocked", "road_affordance_conflict"}
        ]
        return {
            "conflicts": conflicts,
            "affordance_violations": [
                self._affordance_violation(conflict)
                for conflict in affordance_conflicts
            ],
            "aisle_bottlenecks": [
                self._aisle_bottleneck(conflict)
                for conflict in aisle_conflicts
            ],
            "debug": {
                "all": [conflict.to_debug_dict() for conflict in conflicts],
                "affordance": [
                    conflict.to_debug_dict() for conflict in affordance_conflicts
                ],
                "aisle": [conflict.to_debug_dict() for conflict in aisle_conflicts],
            },
        }

    def _affordance_blockers(self, scene: SceneModel) -> list[ContinuousConflict]:
        conflicts = []
        for band in scene.affordance_bands:
            band_shape = band.polygon or band.rect
            for entity in scene.entities:
                # A furniture's affordance belongs to itself; its own footprint
                # should never be reported as the blocker.
                if entity.id == band.owner_id:
                    continue
                entity_shape = entity.footprint or entity.rect
                if not geometry_overlaps(band_shape, entity_shape):
                    continue
                conflicts.append(
                    ContinuousConflict(
                        type="affordance_blocked_by_furniture",
                        severity="soft",
                        source_id=band.id,
                        target_id=entity.id,
                        object_ids=[band.owner_id, entity.id],
                        source_kind="affordance",
                        target_kind="furniture",
                        source_shape=band_shape,
                        target_shape=entity_shape,
                        metadata={"owner_id": band.owner_id, "edge": band.edge},
                    )
                )
        return conflicts

    def _clearance_blockers(self, scene: SceneModel) -> list[ContinuousConflict]:
        conflicts = []
        for band in scene.clearance_bands:
            for entity in scene.entities:
                entity_shape = entity.footprint or entity.rect
                if not geometry_overlaps(band.rect, entity_shape):
                    continue
                conflicts.append(
                    ContinuousConflict(
                        type="clearance_blocked",
                        severity="hard",
                        source_id=band.id,
                        target_id=entity.id,
                        object_ids=[band.id, entity.id],
                        source_kind="clearance",
                        target_kind="furniture",
                        source_shape=band.rect,
                        target_shape=entity_shape,
                        metadata={"road_id": band.road_id},
                    )
                )
        return conflicts

    def _road_affordance_conflicts(self, scene: SceneModel) -> list[ContinuousConflict]:
        conflicts = []
        corridor_sources: Iterable[tuple[str, str, Rect, dict[str, Any]]]
        if scene.clearance_bands:
            corridor_sources = (
                (
                    band.id,
                    "clearance",
                    band.rect,
                    {"road_id": band.road_id},
                )
                for band in scene.clearance_bands
            )
        else:
            corridor_sources = (
                (band.id, "road", band.rect, {})
                for band in scene.road_bands
            )

        for source_id, source_kind, source_shape, metadata in corridor_sources:
            for band in scene.affordance_bands:
                band_shape = band.polygon or band.rect
                if not geometry_overlaps(source_shape, band_shape):
                    continue
                conflicts.append(
                    ContinuousConflict(
                        type="road_affordance_conflict",
                        severity="soft",
                        source_id=source_id,
                        target_id=band.id,
                        object_ids=[source_id, band.owner_id],
                        source_kind=source_kind,
                        target_kind="affordance",
                        source_shape=source_shape,
                        target_shape=band_shape,
                        metadata={
                            **metadata,
                            "owner_id": band.owner_id,
                            "edge": band.edge,
                        },
                    )
                )
        return conflicts

    def _affordance_violation(self, conflict: ContinuousConflict) -> dict[str, Any]:
        return {
            "type": conflict.type,
            "severity": conflict.severity,
            "object_ids": list(conflict.object_ids),
            "source_id": conflict.source_id,
            "target_id": conflict.target_id,
            "edge": conflict.metadata.get("edge"),
            "suggestion_hint": "move_blocker_or_reduce_affordance_overlap",
        }

    def _aisle_bottleneck(self, conflict: ContinuousConflict) -> dict[str, Any]:
        hint = (
            "increase_clearance_band"
            if conflict.type == "clearance_blocked"
            else "separate_road_from_affordance"
        )
        return {
            "type": conflict.type,
            "severity": conflict.severity,
            "object_ids": list(conflict.object_ids),
            "source_id": conflict.source_id,
            "target_id": conflict.target_id,
            "suggestion_hint": hint,
        }


def _as_polygon(shape: Geometry) -> Polygon:
    if isinstance(shape, Polygon):
        return shape
    return Polygon.from_local_rect(
        cx=shape.cx,
        cy=shape.cy,
        width=shape.width,
        height=shape.height,
    )


def _intersection_bounds(left: Geometry, right: Geometry) -> Rect | None:
    left_bounds = left.bounds if isinstance(left, Polygon) else left
    right_bounds = right.bounds if isinstance(right, Polygon) else right
    if not left_bounds.intersects(right_bounds):
        return None
    x1 = max(left_bounds.left, right_bounds.left)
    x2 = min(left_bounds.right, right_bounds.right)
    y1 = max(left_bounds.top, right_bounds.top)
    y2 = min(left_bounds.bottom, right_bounds.bottom)
    if x1 >= x2 or y1 >= y2:
        return None
    return Rect(cx=(x1 + x2) / 2, cy=(y1 + y2) / 2, width=x2 - x1, height=y2 - y1)


def _polygons_overlap(left: Polygon, right: Polygon) -> bool:
    # Current MVP polygons are convex rectangles. SAT catches positive-area
    # overlap even when edges are aligned and no vertex is strictly inside.
    for axis in _separating_axes(left):
        if not _projections_overlap_with_area(left, right, axis):
            return False
    for axis in _separating_axes(right):
        if not _projections_overlap_with_area(left, right, axis):
            return False
    return True


def _polygon_edges(
    polygon: Polygon,
) -> Iterable[tuple[tuple[float, float], tuple[float, float]]]:
    points = polygon.points
    for index, point in enumerate(points):
        yield point, points[(index + 1) % len(points)]


def _separating_axes(polygon: Polygon) -> Iterable[tuple[float, float]]:
    for start, end in _polygon_edges(polygon):
        edge_x = end[0] - start[0]
        edge_y = end[1] - start[1]
        yield -edge_y, edge_x


def _projections_overlap_with_area(
    left: Polygon,
    right: Polygon,
    axis: tuple[float, float],
    *,
    epsilon: float = 1e-9,
) -> bool:
    left_min, left_max = _project_polygon(left, axis)
    right_min, right_max = _project_polygon(right, axis)
    return left_min < right_max - epsilon and left_max > right_min + epsilon


def _project_polygon(
    polygon: Polygon,
    axis: tuple[float, float],
) -> tuple[float, float]:
    values = [point[0] * axis[0] + point[1] * axis[1] for point in polygon.points]
    return min(values), max(values)


def _point_in_polygon_strict(x: float, y: float, polygon: Polygon) -> bool:
    if _point_on_polygon_boundary(x, y, polygon):
        return False
    return polygon.contains_point(x, y)


def _point_on_polygon_boundary(x: float, y: float, polygon: Polygon) -> bool:
    for start, end in _polygon_edges(polygon):
        if _point_on_segment(x, y, start, end):
            return True
    return False


def _point_on_segment(
    x: float,
    y: float,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    epsilon: float = 1e-9,
) -> bool:
    cross = (x - start[0]) * (end[1] - start[1]) - (y - start[1]) * (end[0] - start[0])
    if abs(cross) > epsilon:
        return False
    return (
        min(start[0], end[0]) - epsilon <= x <= max(start[0], end[0]) + epsilon
        and min(start[1], end[1]) - epsilon <= y <= max(start[1], end[1]) + epsilon
    )


def _segments_cross(
    left: tuple[tuple[float, float], tuple[float, float]],
    right: tuple[tuple[float, float], tuple[float, float]],
    *,
    epsilon: float = 1e-9,
) -> bool:
    a, b = left
    c, d = right
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    # Strict crossing only. Endpoint touch or collinear edge overlap is a
    # boundary contact, not a positive-area conflict by itself.
    return (
        (o1 > epsilon and o2 < -epsilon or o1 < -epsilon and o2 > epsilon)
        and (o3 > epsilon and o4 < -epsilon or o3 < -epsilon and o4 > epsilon)
    )


def _orientation(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
