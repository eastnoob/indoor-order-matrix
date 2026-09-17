"""Tests for single-furniture two-axis frame inference."""

from math import isclose

import pytest

from ..features.furniture_frame import infer_furniture_frame
from ..features.scene_contract import MeshGeometry3D
from ..features.affordance.models import Rect
from ..features.scene_inference import _furniture_group_frame


def _plan_mesh(width: float, depth: float, angle: float = 0.0) -> MeshGeometry3D:
    """Build a triangulated planar rectangle for deterministic frame tests."""
    from math import cos, radians, sin

    base = ((0.0, 0.0), (width, 0.0), (width, depth), (0.0, depth))
    c = cos(radians(angle))
    s = sin(radians(angle))
    vertices = tuple((x * c - y * s, x * s + y * c, 0.0) for x, y in base)
    return MeshGeometry3D(
        id="fixture-masspatch",
        vertices=vertices,
        triangle_indices=((0, 1, 2), (0, 2, 3)),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"source": "unit-test"},
        source_representation_id="fixture-masspatch",
        tessellation_settings={},
        units="m",
    )


def test_long_axis_and_secondary_axis_are_reported_for_masspatch() -> None:
    """A rectangular proxy exposes its major axis, minor axis, and clarity."""
    frame = infer_furniture_frame(_plan_mesh(4.0, 1.0))

    assert frame["primary_angle_degrees"] == pytest.approx(0.0)
    assert frame["secondary_angle_degrees"] == pytest.approx(90.0)
    assert frame["primary_extent"] == pytest.approx(4.0)
    assert frame["secondary_extent"] == pytest.approx(1.0)
    assert frame["orientation_strength"] > 0.8


def test_frame_angle_rotates_with_the_masspatch() -> None:
    """The frame follows an oblique furniture proxy instead of world axes."""
    frame = infer_furniture_frame(_plan_mesh(4.0, 1.0, angle=30.0))

    assert frame["primary_angle_degrees"] == pytest.approx(30.0)
    assert frame["secondary_angle_degrees"] == pytest.approx(120.0)
    assert frame["orientation_strength"] > 0.8


def test_square_proxy_has_weak_direction_without_an_angle_threshold() -> None:
    """A square has a continuous low clarity rather than a forced direction."""
    frame = infer_furniture_frame(_plan_mesh(2.0, 2.0))

    assert isclose(frame["orientation_strength"], 0.0, abs_tol=1e-9)
    assert frame["basis"] == "analysis_masspatch_area_weighted_pca"


def test_group_frame_ignores_stale_orientation_when_terminal_points_are_oblique() -> None:
    """Group trend follows terminal member geometry even when orientation says zero."""
    points = list(_plan_mesh(4.0, 1.0, angle=30.0).vertices)
    member = {
        "id": "member",
        "orientation": 0.0,
        "points": [(x, y) for x, y, _z in points],
        "rect": Rect(cx=0.0, cy=0.0, width=4.0, height=1.0),
        "metadata": {
            "frame-primary-extent": "4.0",
            "frame-secondary-extent": "1.0",
            "frame-source": "terminal_projected_analysis_geometry",
        },
    }
    extent = {"rect": Rect(cx=0.0, cy=0.0, width=4.0, height=1.0)}

    frame = _furniture_group_frame([member], [extent])

    assert frame["angle"] == pytest.approx(30.0, abs=1.0)
