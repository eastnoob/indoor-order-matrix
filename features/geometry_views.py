"""Deterministic task views over functional geometry substitutes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Mapping
from typing import Iterable

from .geometry_substitutes import MassPatch, SurfacePatch


@dataclass(frozen=True)
class PlanProjection:
    """A serializable XY projection tied to one substitute."""

    source_patch_id: str
    coordinates: tuple[tuple[float, float], ...]
    uncertainty: str | None = None
    components: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable plan projection."""
        return {
            "source_patch_id": self.source_patch_id,
            "coordinates": self.coordinates,
            "uncertainty": self.uncertainty,
            "components": self.components,
        }


@dataclass(frozen=True)
class VerticalIntervalResult:
    """Local occupied vertical intervals and explicit query uncertainty."""

    intervals: tuple[tuple[float, float], ...]
    uncertainties: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable local interval result."""
        return {"intervals": self.intervals, "uncertainties": self.uncertainties}


@dataclass(frozen=True)
class VerticalProfileResult:
    """A deterministic collection of local vertical samples."""

    samples: tuple[tuple[tuple[float, float], VerticalIntervalResult], ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable vertical profile."""
        return {
            "samples": tuple(
                (point, result.to_dict()) for point, result in self.samples
            )
        }


@dataclass(frozen=True)
class ClearanceResult:
    """Planar clearance evidence without a fabricated navigable graph."""

    obstacle_patch_ids: tuple[str, ...]
    body_radius: float
    uncertainties: tuple[str, ...]
    obstacle_projections: tuple[PlanProjection, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable clearance description."""
        return {
            "obstacle_patch_ids": self.obstacle_patch_ids,
            "body_radius": self.body_radius,
            "uncertainties": self.uncertainties,
            "obstacle_projections": tuple(
                projection.to_dict() for projection in self.obstacle_projections
            ),
        }


def component_shape(components: Iterable[Mapping[str, object]]):
    """Build exact polygonal geometry from disconnected exteriors and holes."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    polygons = []
    for component in components:
        exterior = component.get("exterior", ())
        holes = component.get("holes", ())
        if len(exterior) < 3:
            continue
        polygon = Polygon(exterior, holes)
        if polygon.is_valid and not polygon.is_empty:
            polygons.append(polygon)
    return unary_union(polygons) if polygons else None


def plan_projection(
    patch: MassPatch,
    analysis_plane: object | None = None,
    height_band: tuple[float, float] | None = None,
    *,
    height_tolerance: float = 1e-9,
) -> PlanProjection:
    """Project substitute faces while preserving disconnected plan topology.

    Height-band projections require positive vertical overlap beyond the
    supplied tolerance; contact with a support plane is not a collision.
    """
    if not math.isfinite(height_tolerance) or height_tolerance < 0.0:
        raise ValueError("height_tolerance must be finite and non-negative")
    plane = analysis_plane
    clipped_polygons = []
    if height_band is None:
        # Face union preserves disconnected solids and holes; joining unique
        # vertices in source order can fabricate edges across empty space.
        projected_polygons = []
        for first, second, third in patch.triangle_indices:
            projected_polygons.append(
                tuple(
                    _project_to_plane(patch.vertices[index], plane)[:2]
                    for index in (first, second, third)
                )
            )
        components = _polygon_components(projected_polygons)
    else:
        if not _patch_overlaps_height_band(
            patch,
            plane,
            height_band,
            tolerance=height_tolerance,
        ):
            return PlanProjection(
                patch.id,
                (),
                "no_positive_vertical_overlap_with_height_band",
                (),
            )
        # Clip each face against both height planes so a thin slice through a
        # sloped face is represented even when no source vertex lies in it.
        for first, second, third in patch.triangle_indices:
            triangle = [_project_to_plane(patch.vertices[index], plane) for index in (first, second, third)]
            clipped = _clip_triangle_to_band(triangle, height_band)
            if len(clipped) >= 3:
                clipped_polygons.append(tuple((point[0], point[1]) for point in clipped))
        components = _polygon_components(clipped_polygons)
        if not components and patch.is_closed is True:
            # Vertical shell faces collapse to plan lines after band clipping.
            # Reconstruct the occupied cross-section before considering a full
            # footprint fallback, so local high parts stay spatially local.
            components = _height_band_cross_section_components(
                patch,
                plane,
                height_band,
            )
        if (
            not components
            and patch.is_closed is True
            and _patch_overlaps_height_band(patch, plane, height_band)
        ):
            # A closed shell may expose only vertical faces at a thin slice;
            # use its footprint only when the requested band actually crosses
            # the patch. This avoids promoting a low seat into an eye blocker.
            footprint_polygons = []
            for first, second, third in patch.triangle_indices:
                footprint_polygons.append(
                    tuple(
                        _project_to_plane(patch.vertices[index], plane)[:2]
                        for index in (first, second, third)
                    )
                )
            components = _polygon_components(footprint_polygons)
    points = list(components[0]["exterior"]) if components else []
    uncertainty = None if points else "no_vertices_in_height_band"
    if height_band is not None and components and not clipped_polygons:
        uncertainty = "height_band_surface_projection_fallback"
    return PlanProjection(patch.id, tuple(points), uncertainty, tuple(components))


def _patch_overlaps_height_band(
    patch: MassPatch,
    analysis_plane: object | None,
    height_band: tuple[float, float],
    *,
    tolerance: float = 1e-9,
) -> bool:
    """Return whether local height ranges overlap by more than tolerance."""
    heights = [
        _project_to_plane(vertex, analysis_plane)[2]
        for vertex in patch.vertices
    ]
    if not heights:
        return False
    overlap = min(max(heights), height_band[1]) - max(
        min(heights), height_band[0]
    )
    return overlap > tolerance


def vertical_intervals_at(
    patch: MassPatch,
    point: tuple[float, float],
    direction: tuple[float, float, float] = (0.0, 0.0, 1.0),
    *,
    analysis_plane: object | None = None,
) -> VerticalIntervalResult:
    """Intersect a vertical query ray with triangle geometry at one plan point."""
    if analysis_plane is not None:
        # Transform the query into the local plane frame, where the normal is
        # the third axis; this keeps the intersection algorithm source-neutral.
        local_patch = MassPatch(
            id=patch.id,
            source_geometry_id=patch.source_geometry_id,
            vertices=tuple(_project_to_plane(vertex, analysis_plane) for vertex in patch.vertices),
            triangle_indices=patch.triangle_indices,
            is_manifold=patch.is_manifold,
            is_closed=patch.is_closed,
            provenance=patch.provenance,
        )
        local_direction = tuple(
            sum(direction[index] * analysis_plane.basis[axis][index] for index in range(3))
            for axis in range(3)
        )
        return vertical_intervals_at(local_patch, point, local_direction)
    if not math.isfinite(direction[2]) or math.isclose(direction[2], 0.0):
        return VerticalIntervalResult((), ("only_vertical_queries_supported",))
    if not math.isclose(direction[0], 0.0, abs_tol=1e-9) or not math.isclose(
        direction[1], 0.0, abs_tol=1e-9
    ):
        return VerticalIntervalResult((), ("only_vertical_queries_supported",))
    x, y = point
    heights: list[float] = []
    for first, second, third in patch.triangle_indices:
        triangle = (patch.vertices[first], patch.vertices[second], patch.vertices[third])
        if _point_in_triangle_xy(x, y, triangle):
            heights.append(_interpolated_height(x, y, triangle))
    # Shared triangle edges produce duplicate hits; deduplicate before pairing
    # lower and upper crossings into occupied intervals.
    unique_heights = _unique_sorted(heights)
    # Pairing assumes a closed, consistently oriented shell. Open meshes keep
    # the observed intersections but also carry an explicit uncertainty below.
    intervals = tuple(
        (unique_heights[index], unique_heights[index + 1])
        for index in range(0, len(unique_heights) - 1, 2)
        if unique_heights[index + 1] > unique_heights[index]
    )
    uncertainties = []
    if patch.is_closed is not True or patch.is_manifold is not True:
        uncertainties.append("open_or_nonmanifold_geometry")
    if not intervals:
        uncertainties.append("no_vertical_interval")
    return VerticalIntervalResult(intervals, tuple(uncertainties))


def vertical_profile(
    patch: MassPatch,
    sample_geometry: Iterable[tuple[float, float]],
) -> VerticalProfileResult:
    """Evaluate local vertical intervals at an ordered sample set."""
    return VerticalProfileResult(
        tuple((point, vertical_intervals_at(patch, point)) for point in sample_geometry)
    )


def surface_elevation_at(
    surface: SurfacePatch,
    point: tuple[float, float],
) -> object:
    """Return authored surface elevation evidence without inventing a height."""
    del point
    if isinstance(surface.elevation, Mapping) and "constant" in surface.elevation:
        return surface.elevation["constant"]
    return None


def occlusion_intersections(
    patch: MassPatch,
    ray_or_band: object,
) -> tuple[str, ...]:
    """Return conservative occlusion evidence for a patch query."""
    if patch.is_closed is not True or patch.is_manifold is not True:
        return ("open_or_nonmanifold_geometry",)
    point = None
    origin = None
    direction = None
    height_band = None
    if isinstance(ray_or_band, Mapping):
        point = ray_or_band.get("point")
        if isinstance(ray_or_band.get("origin"), (tuple, list)):
            origin = ray_or_band["origin"]
            if point is None:
                point = origin[:2]
            direction = ray_or_band.get("direction")
        height_band = ray_or_band.get("height_band")
    if origin is not None or direction is not None:
        if (
            not isinstance(origin, (tuple, list))
            or len(origin) != 3
            or not isinstance(direction, (tuple, list))
            or len(direction) != 3
        ):
            return ("unsupported_occlusion_query",)
        if not all(math.isfinite(float(value)) for value in (*origin, *direction)):
            return ("unsupported_occlusion_query",)
        if all(math.isclose(float(value), 0.0, abs_tol=1e-12) for value in direction):
            return ("unsupported_occlusion_query",)
        if height_band is not None:
            if (
                not isinstance(height_band, (tuple, list))
                or len(height_band) != 2
                or not all(math.isfinite(float(value)) for value in height_band)
                or float(height_band[0]) > float(height_band[1])
            ):
                return ("unsupported_occlusion_query",)
        # All directions use the same forward ray test so origin height and
        # direction sign cannot be lost in a special vertical-query branch.
        normalized_origin = tuple(float(value) for value in origin)
        normalized_direction = tuple(float(value) for value in direction)
        normalized_band = (
            tuple(float(value) for value in height_band)
            if height_band is not None
            else None
        )
        return (
            ("occluded",)
            if _ray_hits_mesh(
                patch, normalized_origin, normalized_direction, normalized_band
            )
            else ()
        )
    if not isinstance(point, (tuple, list)) or len(point) != 2:
        return ("unsupported_occlusion_query",)
    result = vertical_intervals_at(patch, (float(point[0]), float(point[1])))
    if height_band is not None:
        if not isinstance(height_band, (tuple, list)) or len(height_band) != 2:
            return ("unsupported_occlusion_query",)
        result = VerticalIntervalResult(
            tuple(
                interval
                for interval in result.intervals
                if interval[1] >= height_band[0] and interval[0] <= height_band[1]
            ),
            result.uncertainties,
        )
    return ("occluded",) if result.intervals else ()


def clearance_geometry(
    patches: Iterable[MassPatch],
    body_radius: float,
    analysis_plane: object | None = None,
) -> ClearanceResult:
    """Describe clearance inputs without claiming a route or medial axis."""
    if not math.isfinite(body_radius) or body_radius <= 0.0:
        raise ValueError("body_radius must be finite and positive")
    patches = tuple(patches)
    uncertainties = tuple(
        sorted(
            {
                "open_or_nonmanifold_geometry"
                for patch in patches
                if patch.is_closed is not True or patch.is_manifold is not True
            }
        )
    )
    projections = tuple(plan_projection(patch, analysis_plane) for patch in patches)
    return ClearanceResult(
        tuple(patch.id for patch in patches),
        body_radius,
        uncertainties,
        projections,
    )


def _point_in_triangle_xy(
    x: float,
    y: float,
    triangle: tuple[tuple[float, float, float], ...],
) -> bool:
    """Test XY containment using barycentric coordinates with edge tolerance."""
    (ax, ay, _), (bx, by, _), (cx, cy, _) = triangle
    denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if math.isclose(denominator, 0.0):
        return False
    first = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / denominator
    second = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / denominator
    third = 1.0 - first - second
    return first >= -1e-9 and second >= -1e-9 and third >= -1e-9


def _project_to_plane(
    vertex: tuple[float, float, float],
    analysis_plane: object | None,
) -> tuple[float, float, float]:
    """Project one world point onto the requested plane's local basis."""
    if analysis_plane is None:
        return vertex
    origin = analysis_plane.origin
    first, second, normal = analysis_plane.basis
    delta = tuple(vertex[index] - origin[index] for index in range(3))
    return (
        sum(delta[index] * first[index] for index in range(3)),
        sum(delta[index] * second[index] for index in range(3)),
        sum(delta[index] * normal[index] for index in range(3)),
    )


def _clip_triangle_to_band(
    triangle: list[tuple[float, float, float]],
    height_band: tuple[float, float],
) -> tuple[tuple[float, float, float], ...]:
    """Clip one projected triangle against lower and upper height planes."""
    polygon = triangle
    polygon = _clip_polygon_height(polygon, height_band[0], keep_above=True)
    polygon = _clip_polygon_height(polygon, height_band[1], keep_above=False)
    return tuple(polygon)


def _clip_polygon_height(
    polygon: list[tuple[float, float, float]],
    boundary: float,
    *,
    keep_above: bool,
) -> list[tuple[float, float, float]]:
    """Apply one linear height half-plane to a polygon edge by edge."""
    if not polygon:
        return []
    result: list[tuple[float, float, float]] = []
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        start_inside = start[2] >= boundary if keep_above else start[2] <= boundary
        end_inside = end[2] >= boundary if keep_above else end[2] <= boundary
        if start_inside != end_inside:
            ratio = (boundary - start[2]) / (end[2] - start[2])
            result.append(tuple(start[index] + ratio * (end[index] - start[index]) for index in range(3)))
        if end_inside:
            result.append(end)
    return result


def _height_band_cross_section_components(
    patch: MassPatch,
    analysis_plane: object | None,
    height_band: tuple[float, float],
) -> tuple[dict[str, object], ...]:
    """Recover local occupied plan faces from closed-mesh band cross-sections."""
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union

    local_vertices = tuple(
        _project_to_plane(vertex, analysis_plane)
        for vertex in patch.vertices
    )
    if not local_vertices:
        return ()
    minimum = max(height_band[0], min(vertex[2] for vertex in local_vertices))
    maximum = min(height_band[1], max(vertex[2] for vertex in local_vertices))
    if maximum <= minimum + 1e-12:
        return ()
    events = sorted(
        {minimum, maximum}
        | {
            vertex[2]
            for vertex in local_vertices
            if minimum < vertex[2] < maximum
        }
    )
    sample_heights = [
        (lower + upper) / 2.0
        for lower, upper in zip(events, events[1:])
        if upper > lower + 1e-12
    ]
    local_patch = MassPatch(
        id=patch.id,
        source_geometry_id=patch.source_geometry_id,
        vertices=local_vertices,
        triangle_indices=patch.triangle_indices,
        is_manifold=patch.is_manifold,
        is_closed=patch.is_closed,
        provenance=patch.provenance,
    )
    occupied_faces = []
    for height in sample_heights:
        lines = []
        for indices in patch.triangle_indices:
            triangle = tuple(local_vertices[index] for index in indices)
            points = _triangle_height_intersections(triangle, height)
            if len(points) == 2:
                lines.append(LineString(points))
        if not lines:
            continue
        # Polygonized linework contains both occupied faces and enclosed holes;
        # a 3D parity probe keeps only the physically occupied planar faces.
        for face in polygonize(unary_union(lines)):
            point = face.representative_point()
            if _point_inside_closed_mesh(
                local_patch,
                (float(point.x), float(point.y), height),
            ):
                occupied_faces.append(face)
    if not occupied_faces:
        return ()
    return _shapely_polygon_components(unary_union(occupied_faces))


def _triangle_height_intersections(
    triangle: tuple[tuple[float, float, float], ...],
    height: float,
) -> tuple[tuple[float, float], ...]:
    """Return the two plan points where one triangle crosses a sample height."""
    points = []
    for start, end in zip(triangle, triangle[1:] + triangle[:1]):
        if (start[2] < height < end[2]) or (end[2] < height < start[2]):
            ratio = (height - start[2]) / (end[2] - start[2])
            point = (
                start[0] + ratio * (end[0] - start[0]),
                start[1] + ratio * (end[1] - start[1]),
            )
            if not any(
                math.isclose(point[0], existing[0], abs_tol=1e-9)
                and math.isclose(point[1], existing[1], abs_tol=1e-9)
                for existing in points
            ):
                points.append(point)
    return tuple(points)


def _polygon_components(
    polygons: Iterable[tuple[tuple[float, float], ...]],
) -> tuple[dict[str, object], ...]:
    """Union clipped faces while retaining disconnected components and holes."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    candidates = [Polygon(polygon) for polygon in polygons if len(polygon) >= 3]
    valid = [polygon for polygon in candidates if polygon.is_valid and polygon.area > 1e-12]
    if not valid:
        return ()
    union = unary_union(valid)
    return _shapely_polygon_components(union)


def _shapely_polygon_components(union: object) -> tuple[dict[str, object], ...]:
    """Serialize Shapely polygon components while preserving interior holes."""
    geometries = union.geoms if union.geom_type == "MultiPolygon" else (union,)
    components = []
    for geometry in geometries:
        if geometry.is_empty or geometry.geom_type != "Polygon":
            continue
        components.append(
            {
                "exterior": _canonical_ring(geometry.exterior.coords),
                "holes": tuple(
                    _canonical_ring(ring.coords)
                    for ring in geometry.interiors
                ),
            }
        )
    return tuple(sorted(components, key=lambda item: item["exterior"]))


def _canonical_ring(coordinates: Iterable[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    """Normalize ring orientation and start point for deterministic output."""
    points = tuple((float(x), float(y)) for x, y in coordinates)
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    points = _without_collinear_vertices(points)
    signed_area = sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(points, points[1:] + points[:1])
    )
    if signed_area < 0.0:
        points = tuple(reversed(points))
    start_index = min(range(len(points)), key=points.__getitem__)
    return points[start_index:] + points[:start_index]


def _without_collinear_vertices(
    points: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    """Remove triangulation split points that do not change a closed ring."""
    if len(points) <= 3:
        return points
    retained = []
    for previous, current, following in zip(
        points[-1:] + points[:-1],
        points,
        points[1:] + points[:1],
    ):
        cross = (
            (current[0] - previous[0]) * (following[1] - current[1])
            - (current[1] - previous[1]) * (following[0] - current[0])
        )
        if math.isclose(cross, 0.0, abs_tol=1e-9):
            continue
        retained.append(current)
    return tuple(retained) if len(retained) >= 3 else points


def _ray_hits_mesh(
    patch: MassPatch,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    height_band: tuple[float, float] | None = None,
) -> bool:
    """Test a forward ray and optional height band against triangle faces."""
    distances: list[float] = []
    for first, second, third in patch.triangle_indices:
        distance = _ray_intersection_distance(
            origin,
            direction,
            patch.vertices[first],
            patch.vertices[second],
            patch.vertices[third],
        )
        if distance is not None:
            distances.append(distance)
    unique_distances = _unique_sorted(distances)
    if height_band is None:
        return bool(unique_distances)
    if not unique_distances:
        return False

    # Test each segment between surface contacts independently. This rejects a
    # tangent vertex contact, which creates a hit without toggling solid state.
    boundaries = (0.0,) + unique_distances
    occupied_distance_intervals = []
    for start, end in zip(boundaries, boundaries[1:]):
        if math.isclose(start, end, abs_tol=1e-12):
            continue
        midpoint_distance = (start + end) / 2.0
        midpoint = tuple(
            origin[index] + midpoint_distance * direction[index]
            for index in range(3)
        )
        if _point_inside_closed_mesh(patch, midpoint):
            occupied_distance_intervals.append((start, end))
    for start, end in occupied_distance_intervals:
        first_height = origin[2] + start * direction[2]
        second_height = origin[2] + end * direction[2]
        occupied_band = (min(first_height, second_height), max(first_height, second_height))
        if occupied_band[1] >= height_band[0] and occupied_band[0] <= height_band[1]:
            return True
    return False


def _point_inside_closed_mesh(
    patch: MassPatch,
    point: tuple[float, float, float],
) -> bool:
    """Classify a point with orientation-independent parity ray tests."""
    probe_directions = (
        (1.0, 0.371234, 0.173891),
        (0.193, 1.0, 0.417),
        (0.311, 0.271, 1.0),
    )
    votes = 0
    for direction in probe_directions:
        distances = []
        for first, second, third in patch.triangle_indices:
            distance = _ray_intersection_distance(
                point,
                direction,
                patch.vertices[first],
                patch.vertices[second],
                patch.vertices[third],
            )
            if distance is not None:
                distances.append(distance)
        # Shared edges and vertices appear in several faces; parity must use
        # unique crossings, and repeated probes reduce tangent degeneracies.
        if len(_unique_sorted(distances)) % 2 == 1:
            votes += 1
    return votes >= 2


def _ray_hits_triangle(origin, direction, first, second, third) -> bool:
    """Return whether one forward ray intersects one triangle."""
    return _ray_intersection_distance(origin, direction, first, second, third) is not None


def _ray_intersection_distance(origin, direction, first, second, third) -> float | None:
    """Return the forward distance to a triangle or ``None`` when missed."""
    edge_one = tuple(second[index] - first[index] for index in range(3))
    edge_two = tuple(third[index] - first[index] for index in range(3))
    cross_direction = (
        direction[1] * edge_two[2] - direction[2] * edge_two[1],
        direction[2] * edge_two[0] - direction[0] * edge_two[2],
        direction[0] * edge_two[1] - direction[1] * edge_two[0],
    )
    determinant = sum(edge_one[index] * cross_direction[index] for index in range(3))
    if math.isclose(determinant, 0.0, abs_tol=1e-12):
        return None
    inverse = 1.0 / determinant
    offset = tuple(origin[index] - first[index] for index in range(3))
    barycentric_u = inverse * sum(offset[index] * cross_direction[index] for index in range(3))
    if barycentric_u < 0.0 or barycentric_u > 1.0:
        return None
    cross_offset = (
        offset[1] * edge_one[2] - offset[2] * edge_one[1],
        offset[2] * edge_one[0] - offset[0] * edge_one[2],
        offset[0] * edge_one[1] - offset[1] * edge_one[0],
    )
    barycentric_v = inverse * sum(direction[index] * cross_offset[index] for index in range(3))
    if barycentric_v < 0.0 or barycentric_u + barycentric_v > 1.0:
        return None
    distance = inverse * sum(edge_two[index] * cross_offset[index] for index in range(3))
    return distance if distance >= 0.0 else None


def _interpolated_height(
    x: float,
    y: float,
    triangle: tuple[tuple[float, float, float], ...],
) -> float:
    """Interpolate triangle height at an XY point."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = triangle
    denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    first = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / denominator
    second = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / denominator
    third = 1.0 - first - second
    return first * az + second * bz + third * cz


def _unique_sorted(values: Iterable[float]) -> tuple[float, ...]:
    """Sort and deduplicate ray hits from shared triangle edges."""
    result: list[float] = []
    for value in sorted(float(value) for value in values):
        if not result or not math.isclose(value, result[-1], abs_tol=1e-9):
            result.append(value)
    return tuple(result)
