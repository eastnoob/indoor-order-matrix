"""Single-furniture local frame inference from an analysis MassPatch."""

from __future__ import annotations

from math import atan2, degrees, hypot, sqrt
from typing import Any

from .scene_contract import MeshGeometry3D


def _triangle_plan_facts(
    vertices: tuple[tuple[float, float, float], ...],
    triangle: tuple[int, int, int],
) -> tuple[float, tuple[float, float], tuple[tuple[float, float], ...]]:
    """Return area, centroid, and planar vertices for one triangle."""
    points = tuple((vertices[index][0], vertices[index][1]) for index in triangle)
    (x0, y0), (x1, y1), (x2, y2) = points
    area = abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0
    centroid = (
        (x0 + x1 + x2) / 3.0,
        (y0 + y1 + y2) / 3.0,
    )
    return area, centroid, points


def _vertex_covariance(points: tuple[tuple[float, float], ...]) -> tuple[float, float, float, float, float]:
    """Return mean, covariance terms, and total mass for a point fallback."""
    if not points:
        raise ValueError("furniture frame requires at least one planar point")
    center = (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )
    xx = sum((point[0] - center[0]) ** 2 for point in points) / len(points)
    yy = sum((point[1] - center[1]) ** 2 for point in points) / len(points)
    xy = sum(
        (point[0] - center[0]) * (point[1] - center[1]) for point in points
    ) / len(points)
    return center[0], center[1], xx, yy, xy


def _area_weighted_covariance(
    mesh: MeshGeometry3D,
) -> tuple[float, float, float, float, float, str]:
    """Compute planar covariance using triangle area as geometric mass."""
    triangle_facts = [
        _triangle_plan_facts(mesh.vertices, triangle)
        for triangle in mesh.triangle_indices
    ]
    valid = [facts for facts in triangle_facts if facts[0] > 1e-12]
    if not valid:
        points = tuple((vertex[0], vertex[1]) for vertex in mesh.vertices)
        cx, cy, xx, yy, xy = _vertex_covariance(points)
        return cx, cy, xx, yy, xy, "vertex_pca_fallback"

    total_area = sum(facts[0] for facts in valid)
    cx = sum(area * centroid[0] for area, centroid, _points in valid) / total_area
    cy = sum(area * centroid[1] for area, centroid, _points in valid) / total_area
    xx = yy = xy = 0.0
    for area, centroid, points in valid:
        # The covariance of a uniform triangle is one twelfth of the sum of
        # its vertex deviations. This removes tessellation-density bias while
        # preserving the actual planar area represented by each face.
        local_xx = local_yy = local_xy = 0.0
        for x, y in points:
            dx = x - centroid[0]
            dy = y - centroid[1]
            local_xx += dx * dx
            local_yy += dy * dy
            local_xy += dx * dy
        dx = centroid[0] - cx
        dy = centroid[1] - cy
        xx += area * (local_xx / 12.0 + dx * dx)
        yy += area * (local_yy / 12.0 + dy * dy)
        xy += area * (local_xy / 12.0 + dx * dy)
    return cx, cy, xx / total_area, yy / total_area, xy / total_area, "area_weighted_pca"


def _frame_extents(mesh: MeshGeometry3D, angle_degrees: float) -> tuple[float, float]:
    """Return planar extents along one frame's orthogonal axes."""
    from math import cos, radians, sin

    theta = radians(angle_degrees)
    c = cos(theta)
    s = sin(theta)
    primary = [vertex[0] * c + vertex[1] * s for vertex in mesh.vertices]
    secondary = [-vertex[0] * s + vertex[1] * c for vertex in mesh.vertices]
    return max(primary) - min(primary), max(secondary) - min(secondary)


def infer_furniture_frame(mesh: MeshGeometry3D) -> dict[str, Any]:
    """Infer a two-axis local furniture frame from one analysis MassPatch.

    The returned strength is a continuous eigenvalue concentration value in
    ``[0, 1]``. It describes directional evidence in the proxy's plan shape;
    it is not a perceptual weight, a group alignment score, or a region trend.
    """
    if not mesh.vertices:
        raise ValueError("furniture frame requires non-empty MassPatch geometry")
    _cx, _cy, covariance_xx, covariance_yy, covariance_xy, covariance_basis = (
        _area_weighted_covariance(mesh)
    )
    trace = covariance_xx + covariance_yy
    discriminant = hypot(covariance_xx - covariance_yy, 2.0 * covariance_xy)
    if trace <= 1e-12:
        primary_angle = 0.0
        strength = 0.0
    else:
        strength = max(0.0, min(1.0, discriminant / trace))
        # The angle is intentionally not snapped. A square or circular proxy
        # gets zero strength but retains a deterministic angle for rendering.
        primary_angle = degrees(0.5 * atan2(2.0 * covariance_xy, covariance_xx - covariance_yy)) % 180.0
        if discriminant <= 1e-12 * trace:
            primary_angle = 0.0
    primary_extent, secondary_extent = _frame_extents(mesh, primary_angle)
    return {
        "basis": f"analysis_masspatch_{covariance_basis}",
        "analysis_mesh_id": mesh.id,
        "primary_angle_degrees": primary_angle,
        "secondary_angle_degrees": (primary_angle + 90.0) % 180.0,
        "orientation_strength": strength,
        "primary_extent": primary_extent,
        "secondary_extent": secondary_extent,
        "eigenvalue_primary": (trace + discriminant) / 2.0,
        "eigenvalue_secondary": (trace - discriminant) / 2.0,
        "plan_area_evidence": sum(
            _triangle_plan_facts(mesh.vertices, triangle)[0]
            for triangle in mesh.triangle_indices
        ),
        "vertex_count": len(mesh.vertices),
        "triangle_count": len(mesh.triangle_indices),
    }


__all__ = ["infer_furniture_frame"]
