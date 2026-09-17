"""Normalize serialized VisualARQ Guide instances for IFC grid export."""

from __future__ import annotations

from math import atan2, hypot, pi
from typing import Iterable, Mapping, Sequence


def _points(value: object) -> tuple[tuple[float, float, float], ...]:
    """Validate and freeze one serialized three-dimensional curve polyline."""
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise ValueError("VisualARQ Guide curve needs at least two points")
    points: list[tuple[float, float, float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            raise ValueError("VisualARQ Guide points need at least x and y")
        points.append(
            (
                float(point[0]),
                float(point[1]),
                float(point[2]) if len(point) > 2 else 0.0,
            )
        )
    return tuple(points)


def _curve_length(points: Sequence[tuple[float, float, float]]) -> float:
    """Return polyline length so decorative Guide geometry can be ignored."""
    return sum(
        hypot(
            hypot(end[0] - start[0], end[1] - start[1]),
            end[2] - start[2],
        )
        for start, end in zip(points, points[1:])
    )


def _axis_angle(points: Sequence[tuple[float, float, float]]) -> float:
    """Return an undirected planar angle in the half-turn interval."""
    start, end = points[0], points[-1]
    if start[:2] == end[:2]:
        raise ValueError("VisualARQ Guide axis has no planar direction")
    return atan2(end[1] - start[1], end[0] - start[0]) % pi


def _angular_distance(left: float, right: float) -> float:
    """Measure the shortest undirected angle between two grid axes."""
    difference = abs(left - right) % pi
    return min(difference, pi - difference)


def _normalized_axis(record: Mapping[str, object]) -> dict[str, object]:
    """Extract the authored label and longest axis curve from one Guide record."""
    definition_name = str(record.get("definition_name") or "")
    if not definition_name.startswith("*Guide{"):
        raise ValueError(f"Not a serialized VisualARQ Guide: {definition_name!r}")
    raw_curves = record.get("curves")
    if not isinstance(raw_curves, (list, tuple)) or not raw_curves:
        raise ValueError("VisualARQ Guide has no serialized curves")

    # A VisualARQ Guide block also contains labels and small endpoint arcs;
    # the longest curve is the authored datum axis that IFC must preserve.
    candidates = [
        _points(curve.get("points"))
        for curve in raw_curves
        if isinstance(curve, Mapping) and curve.get("points")
    ]
    if not candidates:
        raise ValueError("VisualARQ Guide has no usable curve geometry")
    curve_points = max(candidates, key=_curve_length)
    return {
        "id": str(record.get("id") or definition_name),
        "tag": str(record.get("name") or record.get("id") or "").strip(),
        "curve_points": curve_points,
        "same_sense": True,
        "angle": _axis_angle(curve_points),
        "source_definition": definition_name,
    }


def normalize_visualarq_guides(
    records: Iterable[Mapping[str, object]],
    *,
    grid_id: str = "visualarq-grid",
    grid_name: str = "VisualARQ Grid",
) -> dict[str, object]:
    """Convert Guide records into one rotation-independent two-family grid."""
    axes = [_normalized_axis(record) for record in records]
    if not axes:
        raise ValueError("At least one VisualARQ Guide is required")

    # Seed the second family with the direction most distinct from the first.
    # Classification is relative to authored axes, never to world X/Y.
    first_angle = float(axes[0]["angle"])
    second = max(axes[1:], key=lambda axis: _angular_distance(first_angle, float(axis["angle"])), default=None)
    second_angle = float(second["angle"]) if second is not None else first_angle
    has_second_family = second is not None and _angular_distance(first_angle, second_angle) > 1e-9

    u_axes: list[dict[str, object]] = []
    v_axes: list[dict[str, object]] = []
    for axis in axes:
        target = u_axes
        if has_second_family and _angular_distance(float(axis["angle"]), second_angle) < _angular_distance(float(axis["angle"]), first_angle):
            target = v_axes
        target.append({key: value for key, value in axis.items() if key != "angle"})
    return {
        "id": grid_id,
        "name": grid_name,
        "u_axes": tuple(u_axes),
        "v_axes": tuple(v_axes),
        "w_axes": (),
        "provenance": {"method": "visualarq_guide_block_longest_curve"},
    }
