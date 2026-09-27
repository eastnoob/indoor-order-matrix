"""Normalized frame and plan-projection operations for canonical layout facts."""

from __future__ import annotations

import math
from typing import Sequence, cast

from .canonical_layout_contract import (
    AnalysisFrame,
    PlanGeometry,
    ResultStatus,
    SourceGeometry3D,
    Vector2,
    Vector3,
    unit_scale,
)


Matrix4 = tuple[tuple[float, float, float, float], ...]


def _matrix4(matrix: Sequence[Sequence[float]]) -> Matrix4:
    """Validate a finite homogeneous transform matrix."""
    if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
        raise ValueError("matrix must be a finite 4x4 matrix")
    rows = tuple(tuple(float(value) for value in row) for row in matrix)
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("matrix must contain finite numbers")
    return rows


def normalize_analysis_frame(frame: AnalysisFrame) -> AnalysisFrame:
    """Rebuild a validated frame so its immutable basis and metadata are canonical."""
    if not isinstance(frame, AnalysisFrame):
        raise TypeError("frame must be an AnalysisFrame")
    # Reconstructing through the contract keeps normalization idempotent and
    # ensures callers cannot pass mutable or non-orthonormal frame state.
    return AnalysisFrame(
        frame_id=frame.frame_id,
        origin=frame.origin,
        basis=frame.basis,
        source_unit=frame.source_unit,
        analysis_unit=frame.analysis_unit,
        geometry_tolerance=frame.geometry_tolerance,
        topology_tolerance=frame.topology_tolerance,
        plane=frame.plane,
        provenance=dict(frame.provenance),
    )


def transform_points(points: Sequence[Vector3], matrix: Sequence[Sequence[float]]) -> tuple[Vector3, ...]:
    """Apply a finite 4x4 homogeneous transform to an ordered point sequence."""
    transform = _matrix4(matrix)
    result: list[Vector3] = []
    for index, point in enumerate(points):
        if len(point) != 3 or any(not math.isfinite(float(value)) for value in point):
            raise ValueError(f"points[{index}] must contain finite three-dimensional coordinates")
        x, y, z = (float(value) for value in point)
        values = (x, y, z, 1.0)
        transformed = tuple(sum(transform[row][column] * values[column] for column in range(4)) for row in range(4))
        w = transformed[3]
        if not math.isfinite(w) or abs(w) <= 1e-12:
            raise ValueError(f"points[{index}] has a non-projectable homogeneous coordinate")
        result.append(cast(Vector3, tuple(value / w for value in transformed[:3])))
    return tuple(result)


def _failure_geometry(
    source: SourceGeometry3D,
    frame: AnalysisFrame,
    conversion: float,
    status: ResultStatus,
    reason: str,
) -> PlanGeometry:
    """Create a value-free projection result while retaining handoff provenance."""
    provenance = {
        "frame_id": frame.frame_id,
        "source_unit": source.source_unit,
        "analysis_unit": frame.analysis_unit,
        "unit_conversion": conversion,
        "source_representation": source.source_representation,
        "method": "project_plan_geometry",
        "plane": frame.plane,
    }
    return PlanGeometry(
        object_id=source.object_id,
        vertices=(),
        triangles=(),
        frame_id=frame.frame_id,
        unit=frame.analysis_unit,
        source_representation=source.source_representation,
        method="project_plan_geometry",
        unit_conversion=conversion,
        status=status,
        reason=reason,
        provenance=provenance,
    )


def project_plan_geometry(source: SourceGeometry3D, frame: AnalysisFrame) -> PlanGeometry:
    """Transform source mesh vertices into a frame plane with explicit status."""
    if not isinstance(source, SourceGeometry3D):
        raise TypeError("source must be a SourceGeometry3D")
    frame = normalize_analysis_frame(frame)
    conversion = unit_scale(source.source_unit, frame.analysis_unit)
    if "unsupported" in source.source_representation.casefold():
        return _failure_geometry(source, frame, conversion, ResultStatus.NOT_AVAILABLE, "unsupported_source_geometry")
    if not source.vertices:
        return _failure_geometry(source, frame, conversion, ResultStatus.NOT_AVAILABLE, "empty_geometry")
    if len(source.vertices) < 3:
        return _failure_geometry(source, frame, conversion, ResultStatus.UNDEFINED, "insufficient_vertices")
    if not source.triangles:
        return _failure_geometry(source, frame, conversion, ResultStatus.UNDEFINED, "insufficient_triangles")
    try:
        world_points = transform_points(source.vertices, source.world_transform)
    except ValueError:
        return _failure_geometry(source, frame, conversion, ResultStatus.INVALID, "non_finite_coordinates")

    plane_axes = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}[frame.plane]
    # Convert coordinates before subtracting the frame origin so source and
    # analysis units cannot silently mix in the projected footprint.
    analysis_points = tuple(tuple(value * conversion for value in point) for point in world_points)
    projected: tuple[Vector2, ...] = tuple(
        cast(
            Vector2,
            tuple(
                sum((analysis_points[index][component] - frame.origin[component]) * frame.basis[axis][component] for component in range(3))
                for axis in plane_axes
            ),
        )
        for index in range(len(analysis_points))
    )
    for triangle in source.triangles:
        first, second, third = (projected[index] for index in triangle)
        area_twice = abs(
            (second[0] - first[0]) * (third[1] - first[1])
            - (second[1] - first[1]) * (third[0] - first[0])
        )
        if area_twice <= frame.topology_tolerance * 2.0:
            return _failure_geometry(source, frame, conversion, ResultStatus.INVALID, "degenerate_triangle")

    provenance = {
        "frame_id": frame.frame_id,
        "source_unit": source.source_unit,
        "analysis_unit": frame.analysis_unit,
        "unit_conversion": conversion,
        "source_representation": source.source_representation,
        "method": "project_plan_geometry",
        "plane": frame.plane,
    }
    return PlanGeometry(
        object_id=source.object_id,
        vertices=projected,
        triangles=source.triangles,
        frame_id=frame.frame_id,
        unit=frame.analysis_unit,
        source_representation=source.source_representation,
        method="project_plan_geometry",
        unit_conversion=conversion,
        status=ResultStatus.COMPUTED,
        provenance=provenance,
    )


def plan_anchor(geometry: PlanGeometry) -> Vector2 | None:
    """Return the arithmetic vertex anchor for usable projected geometry."""
    if not isinstance(geometry, PlanGeometry):
        raise TypeError("geometry must be a PlanGeometry")
    if geometry.status is not ResultStatus.COMPUTED or not geometry.vertices:
        return None
    count = len(geometry.vertices)
    return cast(Vector2, (sum(point[0] for point in geometry.vertices) / count, sum(point[1] for point in geometry.vertices) / count))


__all__ = [
    "normalize_analysis_frame",
    "plan_anchor",
    "project_plan_geometry",
    "transform_points",
]
