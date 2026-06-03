from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import ceil
from typing import Iterable

from .models import Polygon, Rect

# Only furniture occupancy uses this threshold because it blocks BFS movement.
# Road/clearance/affordance are thin semantic bands and still use intersection sampling.
OCCUPIED_CELL_COVERAGE_THRESHOLD = 0.5


@dataclass
class GridCell:
    # Cell tags are sets because one sampled cell can belong to multiple
    # affordance regions, and future evaluators need owner IDs for violations.
    occupied_by: set[str] = field(default_factory=set)
    affordance_for: set[str] = field(default_factory=set)
    conflict_for: set[str] = field(default_factory=set)
    aisle_for: set[str] = field(default_factory=set)
    aisle_conflict_for: set[str] = field(default_factory=set)
    road_for: set[str] = field(default_factory=set)
    clearance_for: set[str] = field(default_factory=set)
    clearance_conflict_for: set[str] = field(default_factory=set)
    reachable: bool = False


class SpatialGridBackend:
    # MVP computational backend. This is not a semantic grid; it samples the
    # continuous scene so evaluators can mark occupancy, affordance, conflicts,
    # and reachability with predictable integer cells.
    def __init__(self, *, width: float, height: float, resolution: float = 50) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        if resolution <= 0:
            raise ValueError("resolution must be positive")

        self.width = float(width)
        self.height = float(height)
        self.resolution = float(resolution)
        self.n_cols = int(ceil(self.width / self.resolution))
        self.n_rows = int(ceil(self.height / self.resolution))
        self.cells = [
            [GridCell() for _ in range(self.n_cols)] for _ in range(self.n_rows)
        ]

    def cell_center(self, row: int, col: int) -> tuple[float, float]:
        self._validate_index(row, col)
        # Use cell centers for deterministic marking. Clamping handles partial
        # cells at the right/bottom scene boundary when size is not divisible.
        x = min((col + 0.5) * self.resolution, self.width)
        y = min((row + 0.5) * self.resolution, self.height)
        return x, y

    def cell_rect(self, row: int, col: int) -> Rect:
        self._validate_index(row, col)
        # Sampling cells are area rectangles. Right/bottom boundary cells may be
        # smaller when scene size is not divisible by resolution.
        left = col * self.resolution
        top = row * self.resolution
        right = min(left + self.resolution, self.width)
        bottom = min(top + self.resolution, self.height)
        return Rect(
            cx=(left + right) / 2,
            cy=(top + bottom) / 2,
            width=right - left,
            height=bottom - top,
        )

    def iter_indices_in_rect(self, rect: Rect) -> Iterable[tuple[int, int]]:
        # Intersection sampling is kept for thin road/clearance/affordance bands;
        # otherwise narrow continuous geometry can disappear at coarse resolution.
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                if self.cell_rect(row, col).intersects(rect):
                    yield row, col

    def iter_indices_in_polygon(self, polygon: Polygon) -> Iterable[tuple[int, int]]:
        # First restrict to polygon bounds, then test cell-area intersection.
        # This prevents thin geometry from disappearing between sample centers;
        # furniture movement blocking applies an extra coverage threshold later.
        bounds = polygon.bounds
        for row, col in self.iter_indices_in_rect(bounds):
            if _rect_intersects_polygon(self.cell_rect(row, col), polygon):
                yield row, col

    def iter_indices_covered_by_shape(
        self,
        shape: Rect | Polygon,
        *,
        min_coverage: float,
    ) -> Iterable[tuple[int, int]]:
        # Occupancy blocks movement, so tiny slivers should not turn a whole
        # sampled cell into an obstacle. The ratio is overlap area / cell area.
        indices = (
            self.iter_indices_in_polygon(shape)
            if isinstance(shape, Polygon)
            else self.iter_indices_in_rect(shape)
        )
        for row, col in indices:
            cell = self.cell_rect(row, col)
            if _shape_cell_coverage_ratio(shape, cell) >= min_coverage:
                yield row, col

    def mark_occupied(self, object_id: str, shape: Rect | Polygon) -> None:
        # Occupied cells are a movement approximation, not the furniture body.
        # Tiny edge slivers do not block a whole sampled cell.
        indices = self.iter_indices_covered_by_shape(
            shape,
            min_coverage=OCCUPIED_CELL_COVERAGE_THRESHOLD,
        )
        for row, col in indices:
            self.cells[row][col].occupied_by.add(object_id)

    def mark_affordance(self, object_id: str, shape: Rect | Polygon) -> None:
        indices = (
            self.iter_indices_in_polygon(shape)
            if isinstance(shape, Polygon)
            else self.iter_indices_in_rect(shape)
        )
        for row, col in indices:
            self.cells[row][col].affordance_for.add(object_id)

    def mark_aisle(self, object_id: str, rect: Rect) -> None:
        # Aisle corridor is a reserved evaluation band around furniture. It is
        # not furniture geometry; it marks sampled cells that should stay clear.
        for row, col in self.iter_indices_in_rect(rect):
            self.cells[row][col].aisle_for.add(object_id)

    def mark_road(self, road_id: str, rect: Rect) -> None:
        # Road cells are sampled from a continuous RoadBand; they are not the
        # road itself, only the evaluation/debug layer.
        for row, col in self.iter_indices_in_rect(rect):
            self.cells[row][col].road_for.add(road_id)

    def mark_clearance(self, clearance_id: str, rect: Rect) -> None:
        # Clearance cells are sampled from a continuous ClearanceBand generated
        # by min_clearance rules.
        for row, col in self.iter_indices_in_rect(rect):
            self.cells[row][col].clearance_for.add(clearance_id)

    def mark_conflicts(self) -> None:
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                cell = self.cells[row][col]
                for object_id in cell.affordance_for:
                    # A furniture's own footprint can overlap its expanded
                    # affordance envelope; only other occupiers block it.
                    blockers = cell.occupied_by - {object_id}
                    if blockers:
                        cell.conflict_for.add(object_id)

    def mark_aisle_conflicts(self) -> None:
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                cell = self.cells[row][col]
                if not cell.aisle_for:
                    continue
                # Any overlap between reserved aisle cells and affordance cells
                # is a soft planning conflict: both want the same sampled space.
                if cell.affordance_for:
                    cell.aisle_conflict_for.update(cell.aisle_for)

    def mark_clearance_conflicts(self) -> None:
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                cell = self.cells[row][col]
                if cell.clearance_for and (cell.occupied_by or cell.affordance_for):
                    cell.clearance_conflict_for.update(cell.clearance_for)

    def cells_with(self, key: str, value: str) -> list[tuple[int, int]]:
        result = []
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                member = getattr(self.cells[row][col], key)
                if value in member:
                    result.append((row, col))
        return result

    def free(self, row: int, col: int) -> bool:
        self._validate_index(row, col)
        return not self.cells[row][col].occupied_by

    def compute_reachability(self, starts: Iterable[tuple[int, int]]) -> None:
        # Four-neighbor BFS is enough for aisle MVP. Diagonal travel can be
        # added later as a policy option if the domain needs it.
        queue: deque[tuple[int, int]] = deque()
        for row, col in starts:
            if self._in_bounds(row, col) and self.free(row, col):
                self.cells[row][col].reachable = True
                queue.append((row, col))

        while queue:
            row, col = queue.popleft()
            for next_row, next_col in self._neighbors(row, col):
                cell = self.cells[next_row][next_col]
                if not cell.reachable and self.free(next_row, next_col):
                    cell.reachable = True
                    queue.append((next_row, next_col))

    def debug_matrix(self, key: str) -> list[list[object]]:
        return [
            [getattr(self.cells[row][col], key) for col in range(self.n_cols)]
            for row in range(self.n_rows)
        ]

    def _neighbors(self, row: int, col: int) -> Iterable[tuple[int, int]]:
        for next_row, next_col in (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        ):
            if self._in_bounds(next_row, next_col):
                yield next_row, next_col

    def _in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.n_rows and 0 <= col < self.n_cols

    def _validate_index(self, row: int, col: int) -> None:
        if not self._in_bounds(row, col):
            raise IndexError("grid index out of bounds")


def _rect_contains_point(rect: Rect, x: float, y: float) -> bool:
    # Boundary counts as contained here because the final intersection test also
    # requires area overlap through Rect.intersects before this function is used.
    return rect.left <= x <= rect.right and rect.top <= y <= rect.bottom


def _rect_corners(rect: Rect) -> tuple[tuple[float, float], ...]:
    return (
        (rect.left, rect.top),
        (rect.right, rect.top),
        (rect.right, rect.bottom),
        (rect.left, rect.bottom),
    )


def _polygon_edges(polygon: Polygon) -> Iterable[tuple[tuple[float, float], tuple[float, float]]]:
    points = polygon.points
    for index, start in enumerate(points):
        yield start, points[(index + 1) % len(points)]


def _rect_edges(rect: Rect) -> Iterable[tuple[tuple[float, float], tuple[float, float]]]:
    corners = _rect_corners(rect)
    for index, start in enumerate(corners):
        yield start, corners[(index + 1) % len(corners)]


def _segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p, q, r):
        epsilon = 1e-9
        return (
            min(p[0], r[0]) - epsilon <= q[0] <= max(p[0], r[0]) + epsilon
            and min(p[1], r[1]) - epsilon <= q[1] <= max(p[1], r[1]) + epsilon
            and abs(orient(p, q, r)) <= epsilon
        )

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)
    if (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0):
        return True
    return (
        on_segment(a1, b1, a2)
        or on_segment(a1, b2, a2)
        or on_segment(b1, a1, b2)
        or on_segment(b1, a2, b2)
    )


def _rect_intersects_polygon(rect: Rect, polygon: Polygon) -> bool:
    # AABB rejection keeps the detailed polygon checks cheap and preserves the
    # "touching only is not area conflict" behavior of Rect.intersects().
    if not rect.intersects(polygon.bounds):
        return False
    if any(polygon.contains_point(x, y) for x, y in _rect_corners(rect)):
        return True
    if any(_rect_contains_point(rect, x, y) for x, y in polygon.points):
        return True
    return any(
        _segments_intersect(poly_a, poly_b, rect_a, rect_b)
        for poly_a, poly_b in _polygon_edges(polygon)
        for rect_a, rect_b in _rect_edges(rect)
    )


def _shape_cell_coverage_ratio(shape: Rect | Polygon, cell: Rect) -> float:
    # Coverage ratio is only used for sampled occupancy/BFS blocking. Continuous
    # conflict detection compares the original shapes directly.
    if cell.area <= 0:
        return 0.0
    if isinstance(shape, Rect):
        return _rect_overlap_area(shape, cell) / cell.area
    return _polygon_rect_overlap_area(shape, cell) / cell.area


def _rect_overlap_area(left: Rect, right: Rect) -> float:
    x1 = max(left.left, right.left)
    x2 = min(left.right, right.right)
    y1 = max(left.top, right.top)
    y2 = min(left.bottom, right.bottom)
    if x1 >= x2 or y1 >= y2:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def _polygon_rect_overlap_area(polygon: Polygon, rect: Rect) -> float:
    clipped = list(polygon.points)
    # Clip polygon to the sampled cell rectangle. This gives actual occupied
    # area for rotated furniture without introducing a geometry dependency.
    # Current polygons are convex rectangles, so Sutherland-Hodgman is enough.
    for boundary in (
        ("left", rect.left),
        ("right", rect.right),
        ("top", rect.top),
        ("bottom", rect.bottom),
    ):
        clipped = _clip_polygon_to_rect_boundary(clipped, boundary)
        if len(clipped) < 3:
            return 0.0
    return abs(_polygon_area(tuple(clipped)))


def _clip_polygon_to_rect_boundary(
    points: list[tuple[float, float]],
    boundary: tuple[str, float],
) -> list[tuple[float, float]]:
    if not points:
        return []
    result: list[tuple[float, float]] = []
    previous = points[-1]
    previous_inside = _inside_boundary(previous, boundary)
    for current in points:
        current_inside = _inside_boundary(current, boundary)
        if current_inside:
            if not previous_inside:
                result.append(_line_boundary_intersection(previous, current, boundary))
            result.append(current)
        elif previous_inside:
            result.append(_line_boundary_intersection(previous, current, boundary))
        previous = current
        previous_inside = current_inside
    return result


def _inside_boundary(point: tuple[float, float], boundary: tuple[str, float]) -> bool:
    kind, value = boundary
    epsilon = 1e-9
    if kind == "left":
        return point[0] >= value - epsilon
    if kind == "right":
        return point[0] <= value + epsilon
    if kind == "top":
        return point[1] >= value - epsilon
    if kind == "bottom":
        return point[1] <= value + epsilon
    return False


def _line_boundary_intersection(
    start: tuple[float, float],
    end: tuple[float, float],
    boundary: tuple[str, float],
) -> tuple[float, float]:
    kind, value = boundary
    x1, y1 = start
    x2, y2 = end
    if kind in {"left", "right"}:
        if abs(x2 - x1) <= 1e-12:
            return value, y1
        t = (value - x1) / (x2 - x1)
        return value, y1 + t * (y2 - y1)
    if abs(y2 - y1) <= 1e-12:
        return x1, value
    t = (value - y1) / (y2 - y1)
    return x1 + t * (x2 - x1), value


def _polygon_area(points: tuple[tuple[float, float], ...]) -> float:
    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return area / 2
