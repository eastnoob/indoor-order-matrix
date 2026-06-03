from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians, sin
from typing import Any


@dataclass(frozen=True)
class Rect:
    # Axis-aligned rectangle in scene coordinates. cx/cy are center points;
    # y grows downward to match the existing layout/report coordinate style.
    cx: float
    cy: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.cx - self.width / 2

    @property
    def right(self) -> float:
        return self.cx + self.width / 2

    @property
    def top(self) -> float:
        return self.cy - self.height / 2

    @property
    def bottom(self) -> float:
        return self.cy + self.height / 2

    @property
    def area(self) -> float:
        return self.width * self.height

    def intersects(self, other: "Rect") -> bool:
        # Touching edges are not counted as intersection; this keeps clearance
        # tests from treating exact adjacency as overlap.
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )

    def expanded(
        self,
        *,
        left: float = 0,
        right: float = 0,
        top: float = 0,
        bottom: float = 0,
    ) -> "Rect":
        new_left = self.left - left
        new_right = self.right + right
        new_top = self.top - top
        new_bottom = self.bottom + bottom
        return Rect(
            cx=(new_left + new_right) / 2,
            cy=(new_top + new_bottom) / 2,
            width=new_right - new_left,
            height=new_bottom - new_top,
        )


@dataclass(frozen=True)
class Polygon:
    # Lightweight polygon for rotated furniture/affordance geometry. Points are
    # scene coordinates in drawing order; current MVP targets convex rectangles.
    points: tuple[tuple[float, float], ...]

    @property
    def bounds(self) -> Rect:
        xs = [point[0] for point in self.points]
        ys = [point[1] for point in self.points]
        left, right = min(xs), max(xs)
        top, bottom = min(ys), max(ys)
        return Rect(
            cx=(left + right) / 2,
            cy=(top + bottom) / 2,
            width=right - left,
            height=bottom - top,
        )

    def contains_point(self, x: float, y: float) -> bool:
        # Ray casting treats boundary points as inside enough for sampled-grid
        # use; the explicit edge check avoids flicker on grid-aligned cells.
        px = float(x)
        py = float(y)
        inside = False
        points = self.points
        count = len(points)
        for index in range(count):
            x1, y1 = points[index]
            x2, y2 = points[(index + 1) % count]
            if _point_on_segment(px, py, x1, y1, x2, y2):
                return True
            if (y1 > py) != (y2 > py):
                cross_x = (x2 - x1) * (py - y1) / (y2 - y1) + x1
                if px < cross_x:
                    inside = not inside
        return inside

    @classmethod
    def from_local_rect(
        cls,
        *,
        cx: float,
        cy: float,
        width: float,
        height: float,
        orientation: float = 0.0,
        local_cx: float = 0.0,
        local_cy: float = 0.0,
    ) -> "Polygon":
        # Build a local rectangle, then rotate/translate it into scene space.
        half_w = float(width) / 2
        half_h = float(height) / 2
        local_points = (
            (local_cx - half_w, local_cy - half_h),
            (local_cx + half_w, local_cy - half_h),
            (local_cx + half_w, local_cy + half_h),
            (local_cx - half_w, local_cy + half_h),
        )
        theta = radians(float(orientation))
        c = cos(theta)
        s = sin(theta)
        points = tuple(
            (
                float(cx) + x * c - y * s,
                float(cy) + x * s + y * c,
            )
            for x, y in local_points
        )
        return cls(points=points)


def _point_on_segment(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> bool:
    epsilon = 1e-9
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > epsilon:
        return False
    return (
        min(x1, x2) - epsilon <= px <= max(x1, x2) + epsilon
        and min(y1, y2) - epsilon <= py <= max(y1, y2) + epsilon
    )


@dataclass
class SpatialEntity:
    # Base spatial concept for furniture and future room fixtures.
    # affordance/aisle hold instance-level overrides, not computed results.
    id: str
    type_id: str
    role: str
    rect: Rect
    parent_id: str = "root"
    orientation: float = 0.0
    footprint: Polygon | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    affordance: dict[str, Any] = field(default_factory=dict)
    aisle: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.footprint is None:
            self.footprint = Polygon.from_local_rect(
                cx=self.rect.cx,
                cy=self.rect.cy,
                width=self.rect.width,
                height=self.rect.height,
                orientation=self.orientation,
            )


@dataclass
class Furniture(SpatialEntity):
    pass


@dataclass
class AffordanceBand:
    # Continuous affordance geometry owned by one furniture instance. It is an
    # entity attribute in geometry space; sampled affordance cells are only a
    # later evaluation/debug representation.
    id: str
    owner_id: str
    edge: str
    rect: Rect
    polygon: Polygon | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.polygon is None:
            self.polygon = Polygon.from_local_rect(
                cx=self.rect.cx,
                cy=self.rect.cy,
                width=self.rect.width,
                height=self.rect.height,
            )


@dataclass
class GridFrame:
    # Semantic design grid, e.g. furniture grid or column grid. This is distinct
    # from SpatialGridBackend, which is only the computational sampling backend.
    id: str
    kind: str = "furniture_grid"
    parent_id: str = "root"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoadBand:
    # Continuous circulation geometry. It is sampled later; it is not itself a
    # SpatialGridBackend cell layer.
    id: str
    rect: Rect
    axis: str = "vertical"
    level: str = "primary"
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClearanceBand:
    # Continuous clearance-check geometry generated from min_clearance. The
    # current MVP uses Rect; future polygon bands can keep this public shape.
    id: str
    road_id: str
    rect: Rect
    required_width: float
    metadata: dict[str, Any] = field(default_factory=dict)


class SceneModel:
    def __init__(
        self,
        *,
        entities: list[SpatialEntity] | None = None,
        grids: list[GridFrame] | None = None,
        affordance_bands: list[AffordanceBand] | None = None,
        road_bands: list[RoadBand] | None = None,
        clearance_bands: list[ClearanceBand] | None = None,
    ) -> None:
        self.entities = list(entities or [])
        self.grids = list(grids or [])
        self.affordance_bands = list(affordance_bands or [])
        self.road_bands = list(road_bands or [])
        self.clearance_bands = list(clearance_bands or [])
        # Keep simple indexes here; richer spatial indexes can be added later
        # without changing evaluator-facing APIs.
        self.entity_by_id = {entity.id: entity for entity in self.entities}
        self.grid_by_id = {grid.id: grid for grid in self.grids}
        self.affordance_band_by_id = {
            band.id: band for band in self.affordance_bands
        }
        self.affordance_bands_by_owner: dict[str, list[AffordanceBand]] = {}
        for band in self.affordance_bands:
            self.affordance_bands_by_owner.setdefault(band.owner_id, []).append(band)
        self.road_band_by_id = {band.id: band for band in self.road_bands}
        self.clearance_band_by_id = {
            band.id: band for band in self.clearance_bands
        }

    def get_entity(self, entity_id: str) -> SpatialEntity | None:
        return self.entity_by_id.get(entity_id)

    def entities_by_role(self, role: str) -> list[SpatialEntity]:
        return [entity for entity in self.entities if entity.role == role]

    def entities_by_parent(self, parent_id: str) -> list[SpatialEntity]:
        return [entity for entity in self.entities if entity.parent_id == parent_id]
