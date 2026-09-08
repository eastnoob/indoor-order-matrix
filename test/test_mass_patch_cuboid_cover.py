"""Tests for the upright occupancy representation used by cuboid covers."""

from __future__ import annotations

import pytest

from ..features.mass_patch_cuboid_cover import (
    CuboidCoverConfig,
    build_upright_occupancy,
    cuboid_from_grid_bounds,
    cuboid_collection_from_mesh,
)
from ..features.geometry_views import vertical_intervals_at
from ..features.mass_patch_generation import split_cuboid_patch
from ..features.scene_contract import MeshGeometry3D
from .test_mass_patch_generation import _box_mesh, _hollow_frame_mesh


def _signed_volume(patch) -> float:
    """Return the signed tetrahedral volume of a closed triangle mesh."""
    import numpy as np

    return sum(
        float(np.dot(patch.vertices[first], np.cross(
            patch.vertices[second],
            patch.vertices[third],
        )))
        for first, second, third in patch.triangle_indices
    ) / 6.0


def test_box_occupancy_has_occupied_cells_without_false_empty_interior():
    """A solid box samples as occupied throughout its bounded volume."""
    grid = build_upright_occupancy(
        _box_mesh(),
        CuboidCoverConfig(pitch=0.25),
    )

    assert grid.occupied_count > 0
    assert grid.empty_count == 0
    assert grid.is_occupied((1.0, 1.0, 0.5)) is True


def test_hollow_source_retains_an_empty_center():
    """Sampling preserves an actual central opening instead of filling it."""
    grid = build_upright_occupancy(
        _hollow_frame_mesh(),
        CuboidCoverConfig(pitch=0.25),
    )

    assert grid.is_occupied((2.0, 2.0, 0.5)) is False
    assert grid.empty_count > 0


def test_occupancy_config_rejects_non_positive_pitch():
    """A non-positive pitch cannot define a finite sampling grid."""
    with pytest.raises(ValueError, match="pitch"):
        CuboidCoverConfig(pitch=0.0)


def test_box_source_produces_one_box():
    """A solid rectangular object is represented by one maximal cuboid."""
    patches = cuboid_collection_from_mesh(
        _box_mesh(),
        CuboidCoverConfig(pitch=0.25),
    )

    assert len(patches) == 1


def test_hollow_frame_collection_preserves_center_opening():
    """A frame collection keeps its central empty area instead of filling it."""
    patches = cuboid_collection_from_mesh(
        _hollow_frame_mesh(),
        CuboidCoverConfig(pitch=0.25),
    )

    assert len(patches) > 1
    assert all(
        not vertical_intervals_at(patch, (2.0, 2.0)).intervals
        for patch in patches
    )


def test_hollow_frame_collection_uses_compact_rectangular_bars():
    """A rectangular frame is simplified as a few bars, not a voxel shell."""
    patches = cuboid_collection_from_mesh(
        _hollow_frame_mesh(),
        CuboidCoverConfig(pitch=0.25),
    )

    assert len(patches) <= 4


def test_mixed_parent_topology_uses_closed_component_occupancy():
    """An uncertain parent still preserves openings in closed components."""
    frame = _hollow_frame_mesh()
    plate = MeshGeometry3D(
        id="open-plate",
        vertices=((6.0, 0.0, 0.0), (7.0, 0.0, 0.0), (7.0, 1.0, 0.0), (6.0, 1.0, 0.0)),
        triangle_indices=((0, 1, 2), (0, 2, 3)),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "mixed_open_plate"},
        source_representation_id="open-plate",
        tessellation_settings={},
        units="m",
    )
    source = MeshGeometry3D(
        id="mixed-frame-parent",
        vertices=frame.vertices + plate.vertices,
        triangle_indices=frame.triangle_indices + tuple(
            tuple(index + len(frame.vertices) for index in triangle)
            for triangle in plate.triangle_indices
        ),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "mixed-frame-parent"},
        source_representation_id="mixed-frame-parent",
        tessellation_settings={},
        units="m",
    )

    patches = cuboid_collection_from_mesh(
        source,
        CuboidCoverConfig(pitch=0.25),
    )

    assert len(patches) > 1
    assert not any(
        vertical_intervals_at(patch, (2.0, 2.0)).intervals
        for patch in patches
    )


def test_component_occupancy_adapts_when_parent_pitch_is_coarse():
    """A small closed frame is not swallowed by a parent-scale sample cell."""
    frame = _hollow_frame_mesh()
    plate = MeshGeometry3D(
        id="coarse-open-plate",
        vertices=((6.0, 0.0, 0.0), (7.0, 0.0, 0.0), (7.0, 1.0, 0.0), (6.0, 1.0, 0.0)),
        triangle_indices=((0, 1, 2), (0, 2, 3)),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "coarse-open-plate"},
        source_representation_id="coarse-open-plate",
        tessellation_settings={},
        units="m",
    )
    source = MeshGeometry3D(
        id="coarse-parent-frame",
        vertices=frame.vertices + plate.vertices,
        triangle_indices=frame.triangle_indices + tuple(
            tuple(index + len(frame.vertices) for index in triangle)
            for triangle in plate.triangle_indices
        ),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "coarse-parent-frame"},
        source_representation_id="coarse-parent-frame",
        tessellation_settings={},
        units="m",
    )

    patches = cuboid_collection_from_mesh(
        source,
        CuboidCoverConfig(pitch=4.0),
    )

    assert len(patches) > 1
    assert not any(
        vertical_intervals_at(patch, (2.0, 2.0)).intervals
        for patch in patches
    )


def test_generated_cuboids_have_outward_winding():
    """Grid and split cuboids have positive signed volume."""
    grid = build_upright_occupancy(
        _box_mesh(),
        CuboidCoverConfig(pitch=0.25),
    )
    patch = cuboid_from_grid_bounds(
        grid,
        (0, grid.shape[0] - 1, 0, grid.shape[1] - 1, 0, grid.shape[2] - 1),
    )
    split = split_cuboid_patch(patch)

    assert _signed_volume(patch) > 0.0
    assert split is not None
    assert all(_signed_volume(part) > 0.0 for part in split)


def test_separated_parts_do_not_get_a_bridge_box():
    """Disconnected solids remain separate when their outer bounds are far apart."""
    from .test_mass_patch_generation import _two_disconnected_boxes

    patches = cuboid_collection_from_mesh(
        _two_disconnected_boxes(),
        CuboidCoverConfig(pitch=0.25),
    )

    assert len(patches) >= 2


def test_chair_cover_preserves_the_center_leg_gap():
    """A chair cover does not fill the floor-level gap between its legs."""
    from .test_mass_patch_generation import _chair_mesh

    patches = cuboid_collection_from_mesh(
        _chair_mesh(),
        CuboidCoverConfig(pitch=0.1),
    )

    assert patches
    assert all(
        not any(lower < 0.9 and upper > 0.0 for lower, upper in vertical_intervals_at(
            patch,
            (1.0, 1.0),
        ).intervals)
        for patch in patches
    )
