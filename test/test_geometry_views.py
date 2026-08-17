"""Tests for deterministic task views over functional substitutes."""

from __future__ import annotations

from dataclasses import replace
import json

from ..features.geometry_substitutes import mass_patch_from_mesh, surface_patch_from_fact
from ..features.geometry_views import (
    clearance_geometry,
    occlusion_intersections,
    plan_projection,
    surface_elevation_at,
    vertical_intervals_at,
)
from ..features.scene_contract import AnalysisPlane, SurfaceFact
from .test_geometry_substitutes import _box_mesh


def test_plan_projection_is_source_independent_and_deterministic():
    """Plan projection exposes the footprint without returning backend geometry."""
    patch = mass_patch_from_mesh(_box_mesh())

    projection = plan_projection(patch)

    assert projection.coordinates == ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0))
    assert projection.source_patch_id == patch.id
    json.dumps(projection.to_dict())


def test_plan_projection_preserves_disconnected_mesh_components():
    """A single substitute with separate solids must not bridge their plan gap."""
    first = _box_mesh(mesh_id="disconnected")
    second_vertices = tuple((x + 5.0, y, z) for x, y, z in first.vertices)
    vertex_offset = len(first.vertices)
    combined = replace(
        first,
        vertices=first.vertices + second_vertices,
        triangle_indices=first.triangle_indices
        + tuple(
            tuple(index + vertex_offset for index in triangle)
            for triangle in first.triangle_indices
        ),
    )

    projection = plan_projection(mass_patch_from_mesh(combined))

    assert len(projection.components) == 2
    assert all(component["holes"] == () for component in projection.components)


def test_plan_projection_uses_analysis_plane_and_intersects_height_band():
    """Plane coordinates and a crossing height band retain a box footprint."""
    patch = mass_patch_from_mesh(_box_mesh(top=2.0))
    plane = AnalysisPlane(
        name="rotated",
        origin=(0.0, 0.0, 0.0),
        basis=((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    )

    projection = plan_projection(patch, plane, height_band=(0.5, 0.6))

    assert set(projection.coordinates) == {
        (0.0, 0.0),
        (0.0, -2.0),
        (2.0, -2.0),
        (2.0, 0.0),
    }


def test_surface_elevation_reads_frozen_authored_mapping():
    """Surface elevation remains available after Neutral Scene freezing."""
    surface = surface_patch_from_fact(
        SurfaceFact(
            id="floor",
            source_id="floor-source",
            host_refs=(),
            identity="floor",
            color=None,
            finish=None,
            texture=None,
            elevation={"constant": 0.35},
            slope=None,
            geometry_refs=(),
        )
    )

    assert surface_elevation_at(surface, (0.0, 0.0)) == 0.35


def test_vertical_intervals_are_local_not_one_global_object_height():
    """A query at a plan point returns the local occupied height interval."""
    patch = mass_patch_from_mesh(_box_mesh(top=2.0))

    result = vertical_intervals_at(patch, (1.0, 1.0))

    assert result.intervals == ((0.0, 2.0),)
    assert result.uncertainties == ()
    assert json.loads(json.dumps(result.to_dict()))["intervals"] == [[0.0, 2.0]]


def test_normalized_vertical_direction_is_accepted():
    """Equivalent non-unit vertical directions produce the same interval."""
    patch = mass_patch_from_mesh(_box_mesh(top=2.0))

    assert vertical_intervals_at(patch, (1.0, 1.0), (0.0, 0.0, 2.0)).intervals == (
        (0.0, 2.0),
    )


def test_sofa_seat_and_back_can_keep_distinct_local_height_views():
    """Separate functional patches preserve a sofa seat/back height difference."""
    seat = mass_patch_from_mesh(_box_mesh(mesh_id="sofa-seat", top=0.45))
    back_mesh = _box_mesh(mesh_id="sofa-back", top=1.8)
    back_mesh = replace(
        back_mesh,
        vertices=tuple((x + 2.0, y, z) for x, y, z in back_mesh.vertices),
    )
    back = mass_patch_from_mesh(back_mesh)

    seat_result = vertical_intervals_at(seat, (1.0, 1.0))
    back_result = vertical_intervals_at(back, (3.0, 1.0))

    assert seat_result.intervals == ((0.0, 0.45),)
    assert back_result.intervals == ((0.0, 1.8),)


def test_open_mesh_reports_uncertainty_instead_of_false_solid_clearance():
    """Missing closure must remain explicit when computing clearance evidence."""
    patch = mass_patch_from_mesh(
        _box_mesh().__class__(
            **{**_box_mesh().__dict__, "is_closed": False, "is_manifold": False}
        )
    )

    result = clearance_geometry((patch,), body_radius=0.25)

    assert "open_or_nonmanifold_geometry" in result.uncertainties
    assert json.dumps(result.to_dict())


def test_closed_mesh_occlusion_query_reports_hit_and_nonmanifold_uncertainty():
    """Occlusion uses the query point and refuses unreliable topology."""
    closed = mass_patch_from_mesh(_box_mesh())
    open_mesh = replace(_box_mesh(mesh_id="open"), is_manifold=False, is_closed=True)
    open_patch = mass_patch_from_mesh(open_mesh)

    assert occlusion_intersections(closed, {"point": (1.0, 1.0)}) == ("occluded",)
    assert occlusion_intersections(
        closed,
        {"origin": (1.0, 1.0, 0.0), "direction": (0.0, 0.0, 1.0), "height_band": (0.5, 0.6)},
    ) == ("occluded",)
    assert occlusion_intersections(
        closed,
        {"origin": (-1.0, 1.0, 0.5), "direction": (1.0, 0.0, 0.0)},
    ) == ("occluded",)
    assert occlusion_intersections(open_patch, {"point": (1.0, 1.0)}) == (
        "open_or_nonmanifold_geometry",
    )


def test_vertical_occlusion_ray_respects_origin_direction_and_rejects_zero_vector():
    """Vertical ray evidence must describe the forward half-line, not its XY point."""
    patch = mass_patch_from_mesh(_box_mesh(top=1.0))

    assert occlusion_intersections(
        patch,
        {"origin": (1.0, 1.0, 2.0), "direction": (0.0, 0.0, 1.0)},
    ) == ()
    assert occlusion_intersections(
        patch,
        {"origin": (1.0, 1.0, 2.0), "direction": (0.0, 0.0, -1.0)},
    ) == ("occluded",)
    assert occlusion_intersections(
        patch,
        {"origin": (1.0, 1.0, 2.0), "direction": (0.0, 0.0, 0.0)},
    ) == ("unsupported_occlusion_query",)


def test_occlusion_ray_height_band_filters_the_actual_forward_intersection():
    """A valid ray hit outside the requested vertical band is not evidence."""
    patch = mass_patch_from_mesh(_box_mesh(top=1.0))

    assert occlusion_intersections(
        patch,
        {
            "origin": (1.0, 1.0, 2.0),
            "direction": (0.0, 0.0, -1.0),
            "height_band": (1.5, 1.75),
        },
    ) == ()


def test_tangent_vertex_contact_does_not_fabricate_an_occupied_ray_interval():
    """Touching one box vertex without entering it leaves the prior band clear."""
    patch = mass_patch_from_mesh(_box_mesh(top=1.0))

    assert occlusion_intersections(
        patch,
        {
            "origin": (-1.0, 1.0, 2.0),
            "direction": (1.0, -1.0, -1.0),
            "height_band": (1.5, 1.75),
        },
    ) == ()


def test_height_band_occlusion_is_independent_of_triangle_winding():
    """Closed manifold facts need not provide consistently oriented faces."""
    mesh = _box_mesh(top=1.0)
    mixed_winding = replace(
        mesh,
        triangle_indices=tuple(
            (first, third, second) if index % 2 else (first, second, third)
            for index, (first, second, third) in enumerate(mesh.triangle_indices)
        ),
    )
    patch = mass_patch_from_mesh(mixed_winding)

    assert occlusion_intersections(
        patch,
        {
            "origin": (1.0, 1.0, 2.0),
            "direction": (0.0, 0.0, -1.0),
            "height_band": (0.5, 0.6),
        },
    ) == ("occluded",)


def test_clearance_keeps_local_obstacle_projections():
    """Clearance output retains plan evidence instead of only patch ids."""
    result = clearance_geometry(
        (mass_patch_from_mesh(_box_mesh()),),
        body_radius=0.25,
        analysis_plane=AnalysisPlane(
            name="plan",
            origin=(0.0, 0.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
    )

    assert result.obstacle_projections[0].coordinates
    assert json.dumps(result.to_dict())
