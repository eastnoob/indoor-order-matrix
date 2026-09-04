"""Tests for the upright occupancy representation used by cuboid covers."""

from __future__ import annotations

import pytest

from ..features.mass_patch_cuboid_cover import (
    CuboidCoverConfig,
    build_upright_occupancy,
    cuboid_collection_from_mesh,
)
from ..features.geometry_views import vertical_intervals_at
from .test_mass_patch_generation import _box_mesh, _hollow_frame_mesh


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
