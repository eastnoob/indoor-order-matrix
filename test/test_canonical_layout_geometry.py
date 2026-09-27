"""Tests for clean-room frame normalization and plan projection."""

from __future__ import annotations

import math

import pytest

from ..features.canonical_layout_contract import AnalysisFrame, ResultStatus, SourceGeometry3D
from ..features.canonical_layout_geometry import (
    normalize_analysis_frame,
    plan_anchor,
    project_plan_geometry,
    transform_points,
)


IDENTITY_4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def _frame(**changes: object) -> AnalysisFrame:
    """Build a valid XY analysis frame and apply focused test overrides."""
    values: dict[str, object] = {
        "frame_id": "frame-main",
        "origin": (0.0, 0.0, 0.0),
        "basis": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "source_unit": "m",
        "analysis_unit": "m",
        "geometry_tolerance": 1e-6,
        "topology_tolerance": 1e-6,
        "plane": "xy",
    }
    values.update(changes)
    return AnalysisFrame(**values)


def _triangle_source(*, unit: str = "m", transform=IDENTITY_4, vertices=None, triangles=None) -> SourceGeometry3D:
    """Build one source triangle with explicit representation provenance."""
    return SourceGeometry3D(
        geometry_id="geometry-1",
        object_id="object-1",
        vertices=vertices if vertices is not None else ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)),
        triangles=triangles if triangles is not None else ((0, 1, 2),),
        source_representation="fixture_triangle",
        source_unit=unit,
        world_transform=transform,
        provenance={"fixture": "canonical_geometry"},
    )


def test_normalize_frame_is_idempotent_and_transform_points_handles_identity_translation_rotation() -> None:
    """Frame normalization preserves a validated frame and matrix transforms are explicit."""
    frame = _frame(origin=(2.0, 3.0, 0.0))
    assert normalize_analysis_frame(frame) == frame
    assert transform_points(((1.0, 2.0, 3.0),), IDENTITY_4) == ((1.0, 2.0, 3.0),)
    translated = (
        (1.0, 0.0, 0.0, 4.0),
        (0.0, 1.0, 0.0, -2.0),
        (0.0, 0.0, 1.0, 0.5),
        (0.0, 0.0, 0.0, 1.0),
    )
    assert transform_points(((1.0, 2.0, 3.0),), translated) == ((5.0, 0.0, 3.5),)
    quarter_turn = (
        (0.0, -1.0, 0.0, 0.0),
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    assert transform_points(((1.0, 0.0, 0.0),), quarter_turn) == ((0.0, 1.0, 0.0),)


def test_transform_points_rejects_nonfinite_matrix_and_zero_homogeneous_coordinate() -> None:
    """Matrix transforms reject non-finite values and non-projectable homogeneous points."""
    with pytest.raises(ValueError, match="finite"):
        transform_points(((0.0, 0.0, 0.0),), ((math.nan,) * 4,) * 4)
    zero_w = (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 0.0),
    )
    with pytest.raises(ValueError, match="homogeneous"):
        transform_points(((1.0, 2.0, 3.0),), zero_w)


def test_projection_applies_world_transform_and_unit_conversion_with_provenance() -> None:
    """Projection returns analysis-unit XY geometry and retains auditable handoff facts."""
    source = _triangle_source(
        unit="mm",
        transform=(
            (1.0, 0.0, 0.0, 1000.0),
            (0.0, 1.0, 0.0, 2000.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        vertices=((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (0.0, 1000.0, 0.0)),
    )
    geometry = project_plan_geometry(source, _frame())

    assert geometry.status is ResultStatus.COMPUTED
    assert geometry.unit == "m"
    assert geometry.unit_conversion == pytest.approx(0.001)
    assert [point for point in geometry.vertices] == [(1.0, 2.0), (2.0, 2.0), (1.0, 3.0)]
    assert geometry.provenance["frame_id"] == "frame-main"
    assert geometry.provenance["source_representation"] == "fixture_triangle"
    assert geometry.provenance["method"] == "project_plan_geometry"
    assert plan_anchor(geometry) == pytest.approx((4.0 / 3.0, 7.0 / 3.0))


@pytest.mark.parametrize(
    ("source", "status", "reason"),
    (
        (_triangle_source(vertices=(), triangles=()), ResultStatus.NOT_AVAILABLE, "empty_geometry"),
        (_triangle_source(vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), triangles=()), ResultStatus.UNDEFINED, "insufficient_vertices"),
        (_triangle_source(vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)), triangles=((0, 1, 2),)), ResultStatus.INVALID, "degenerate_triangle"),
        (_triangle_source(vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)), triangles=()), ResultStatus.UNDEFINED, "insufficient_triangles"),
        (_triangle_source(vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)), triangles=((0, 1, 2),),), ResultStatus.INVALID, "degenerate_triangle"),
    ),
)
def test_projection_reports_explicit_failure_status_and_reason(source, status, reason) -> None:
    """Empty, insufficient, and degenerate source geometry never becomes numeric zero."""
    result = project_plan_geometry(source, _frame())
    assert result.status is status
    assert result.reason == reason
    assert plan_anchor(result) is None


def test_projection_reports_unsupported_representation_as_not_available() -> None:
    """Unsupported source representations remain unavailable without fabricated geometry."""
    source = SourceGeometry3D(
        geometry_id="geometry-unsupported",
        object_id="object-1",
        vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        triangles=((0, 1, 2),),
        source_representation="unsupported_representation",
    )
    result = project_plan_geometry(source, _frame())
    assert result.status is ResultStatus.NOT_AVAILABLE
    assert result.reason == "unsupported_source_geometry"
    assert result.vertices == ()


def test_projection_module_has_no_legacy_or_adapter_imports() -> None:
    """The geometry layer remains independent of IFC, SVG, and legacy scene helpers."""
    from ..features import canonical_layout_geometry

    source = open(canonical_layout_geometry.__file__, encoding="utf-8").read()
    assert "adapters" not in source
    assert "scene_contract" not in source
