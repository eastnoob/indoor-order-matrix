"""Tests for conservative source-independent MassPatch generation."""

from __future__ import annotations

import pytest

from ..features.scene_contract import MeshGeometry3D
from ..features.mass_patch_generation import generate_mass_patches


def _box_mesh(*, mesh_id: str = "box", top: float = 1.0) -> MeshGeometry3D:
    """Build a deterministic closed box fixture."""
    vertices = (
        (0.0, 0.0, 0.0),
        (2.0, 0.0, 0.0),
        (2.0, 2.0, 0.0),
        (0.0, 2.0, 0.0),
        (0.0, 0.0, top),
        (2.0, 0.0, top),
        (2.0, 2.0, top),
        (0.0, 2.0, top),
    )
    triangles = (
        (0, 1, 2), (0, 0, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0),
    )
    return MeshGeometry3D(
        id=mesh_id,
        vertices=vertices,
        triangle_indices=triangles,
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"fixture": "synthetic_box"},
        source_representation_id=mesh_id,
        tessellation_settings={},
        units="m",
    )


def _mesh_without_triangles() -> MeshGeometry3D:
    """Build a valid contract record that contains no faces."""
    return MeshGeometry3D(
        id="empty",
        vertices=((0.0, 0.0, 0.0),),
        triangle_indices=(),
        normals=(),
        is_manifold=None,
        is_closed=None,
        local_to_world_provenance={"fixture": "empty"},
        source_representation_id="empty",
        tessellation_settings={},
        units="m",
    )


def _two_disconnected_boxes() -> MeshGeometry3D:
    """Build two closed boxes that share no vertices or faces."""
    first = _box_mesh(mesh_id="two-boxes")
    second_vertices = tuple((x + 5.0, y, z) for x, y, z in first.vertices)
    vertices = first.vertices + second_vertices
    triangles = first.triangle_indices + tuple(
        tuple(index + len(first.vertices) for index in triangle)
        for triangle in first.triangle_indices
    )
    return MeshGeometry3D(
        id="two-boxes",
        vertices=vertices,
        triangle_indices=triangles,
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"fixture": "two_disconnected_boxes"},
        source_representation_id="two-boxes",
        tessellation_settings={},
        units="m",
    )


def test_generator_returns_exact_baseline_for_a_valid_box():
    """A valid source always produces an addressable exact baseline."""
    result = generate_mass_patches(_box_mesh())

    assert result.source_mesh_id == "box"
    assert len(result.patches) == 1
    assert result.component_reports[0].selected_candidate == "exact_component"


def test_generator_rejects_empty_mesh():
    """A mesh without triangles fails before candidate generation."""
    with pytest.raises(ValueError, match="at least one triangle"):
        generate_mass_patches(_mesh_without_triangles())


def test_disconnected_components_remain_independently_addressable():
    """Disconnected source geometry is not merged by the generator."""
    result = generate_mass_patches(_two_disconnected_boxes())

    assert len(result.patches) == 2
    assert [report.component_index for report in result.component_reports] == [0, 1]


def test_repeated_generation_is_deterministic():
    """The same source produces byte-equivalent result records."""
    first = generate_mass_patches(_two_disconnected_boxes()).to_dict()
    second = generate_mass_patches(_two_disconnected_boxes()).to_dict()

    assert first == second
