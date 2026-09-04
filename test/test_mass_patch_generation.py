"""Tests for conservative source-independent MassPatch generation."""

from __future__ import annotations

import pytest

from ..features.geometry_views import vertical_intervals_at
from ..features.scene_contract import MeshGeometry3D
from ..features.mass_patch_generation import (
    MassPatchGenerationConfig,
    validate_mass_patch_collection_candidate,
    generate_mass_patches,
)
from ..features.geometry_substitutes import mass_patch_from_mesh


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


def _box_with_duplicate_vertex_indices() -> MeshGeometry3D:
    """Build a box whose faces use duplicate coordinate vertices."""
    source = _box_mesh(mesh_id="duplicate-index-box")
    vertices = []
    triangles = []
    for triangle in source.triangle_indices:
        offset = len(vertices)
        vertices.extend(source.vertices[index] for index in triangle)
        triangles.append((offset, offset + 1, offset + 2))
    return MeshGeometry3D(
        id="duplicate-index-box",
        vertices=tuple(vertices),
        triangle_indices=tuple(triangles),
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"fixture": "duplicate_vertex_indices"},
        source_representation_id="duplicate-index-box",
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


def _merge_meshes(meshes: tuple[MeshGeometry3D, ...], mesh_id: str) -> MeshGeometry3D:
    """Merge fixture meshes without joining their factual connectivity."""
    vertices = []
    triangles = []
    for mesh in meshes:
        offset = len(vertices)
        vertices.extend(mesh.vertices)
        triangles.extend(
            tuple(index + offset for index in triangle)
            for triangle in mesh.triangle_indices
        )
    return MeshGeometry3D(
        id=mesh_id,
        vertices=tuple(vertices),
        triangle_indices=tuple(triangles),
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"fixture": mesh_id},
        source_representation_id=mesh_id,
        tessellation_settings={},
        units="m",
    )


def _translated_box(
    *,
    mesh_id: str,
    offset: tuple[float, float, float],
    size: tuple[float, float, float],
) -> MeshGeometry3D:
    """Build an axis-aligned box fixture at a requested location."""
    base = _box_mesh(mesh_id=mesh_id, top=size[2])
    scale_x, scale_y = size[0] / 2.0, size[1] / 2.0
    vertices = tuple(
        (
            x * scale_x + offset[0],
            y * scale_y + offset[1],
            z + offset[2],
        )
        for x, y, z in base.vertices
    )
    return MeshGeometry3D(
        id=mesh_id,
        vertices=vertices,
        triangle_indices=base.triangle_indices,
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"fixture": mesh_id},
        source_representation_id=mesh_id,
        tessellation_settings={},
        units="m",
    )


def _chair_mesh() -> MeshGeometry3D:
    """Build a chair with explicit seat, back, and four separated legs."""
    parts = (
        _translated_box(
            mesh_id="seat",
            offset=(0.0, 0.0, 1.0),
            size=(2.0, 2.0, 0.2),
        ),
        _translated_box(
            mesh_id="back",
            offset=(0.0, 1.8, 1.2),
            size=(2.0, 0.2, 1.5),
        ),
        _translated_box(
            mesh_id="leg-nw",
            offset=(0.1, 0.1, 0.0),
            size=(0.2, 0.2, 1.0),
        ),
        _translated_box(
            mesh_id="leg-ne",
            offset=(1.7, 0.1, 0.0),
            size=(0.2, 0.2, 1.0),
        ),
        _translated_box(
            mesh_id="leg-sw",
            offset=(0.1, 1.7, 0.0),
            size=(0.2, 0.2, 1.0),
        ),
        _translated_box(
            mesh_id="leg-se",
            offset=(1.7, 1.7, 0.0),
            size=(0.2, 0.2, 1.0),
        ),
    )
    return _merge_meshes(parts, "chair")


def _hollow_frame_mesh() -> MeshGeometry3D:
    """Build one connected square frame with a true central opening."""
    outer = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0))
    inner = ((1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0))
    vertices = tuple(
        (x, y, z)
        for z in (0.0, 1.0)
        for loop in (outer, inner)
        for x, y in loop
    )
    triangles = []
    for index in range(4):
        next_index = (index + 1) % 4
        outer_bottom = index
        outer_next_bottom = next_index
        inner_bottom = 4 + index
        inner_next_bottom = 4 + next_index
        outer_top = 8 + index
        outer_next_top = 8 + next_index
        inner_top = 12 + index
        inner_next_top = 12 + next_index
        triangles.extend(
            (
                (outer_bottom, outer_next_bottom, inner_next_bottom),
                (outer_bottom, inner_next_bottom, inner_bottom),
                (outer_top, inner_next_top, outer_next_top),
                (outer_top, inner_top, inner_next_top),
                (outer_bottom, outer_top, outer_next_top),
                (outer_bottom, outer_next_top, outer_next_bottom),
                (inner_bottom, inner_next_top, inner_top),
                (inner_bottom, inner_next_bottom, inner_next_top),
            )
        )
    return MeshGeometry3D(
        id="hollow-frame",
        vertices=vertices,
        triangle_indices=tuple(triangles),
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"fixture": "hollow_frame"},
        source_representation_id="hollow-frame",
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


def test_duplicate_coordinate_vertices_are_welded_before_connectivity_split():
    """Duplicate face-local vertices must not fragment one physical solid."""
    result = generate_mass_patches(_box_with_duplicate_vertex_indices())

    assert len(result.patches) == 1


def test_box_component_produces_a_smaller_oriented_box_candidate():
    """A box exposes an OBB candidate before candidate validation selects it."""
    result = generate_mass_patches(_box_mesh())
    report = result.component_reports[0]

    assert "oriented_bounding_box" in report.candidate_methods
    assert result.patches[0].provenance["source_component_index"] == 0


def test_source_mesh_is_not_mutated_by_candidate_generation():
    """Candidate construction does not mutate the source mesh record."""
    source = _box_mesh()
    before = source.to_dict()

    generate_mass_patches(source)

    assert source.to_dict() == before


def test_box_candidate_is_validated_with_near_zero_error():
    """A rectangular solid can accept its oriented-box candidate."""
    result = generate_mass_patches(_box_mesh())
    candidates = result.component_reports[0].candidate_reports

    obb = next(report for report in candidates if report.candidate_method == "oriented_bounding_box")
    assert obb.accepted is True
    assert obb.plan_recall >= 0.98
    assert obb.plan_overreach <= 0.02


def test_hollow_frame_rejects_a_filled_box():
    """A bounding box must not fill a real central opening."""
    result = generate_mass_patches(_hollow_frame_mesh())
    report = result.component_reports[0]

    assert report.selected_candidate == "exact_component"
    assert report.rejections["oriented_bounding_box"] == "plan_overreach"


def test_chair_leg_gaps_are_not_filled():
    """Separated chair legs leave the central floor position unoccupied."""
    source = _chair_mesh()
    result = generate_mass_patches(source)

    assert len(result.patches) == 6
    assert all(
        not any(
            lower < 0.9 and upper > 0.0
            for lower, upper in vertical_intervals_at(patch, (1.0, 1.0)).intervals
        )
        for patch in result.patches
    )


def test_sloped_component_falls_back_when_height_error_is_too_large():
    """A sloped source falls back when an OBB changes its height profile."""
    source = _translated_box(mesh_id="sloped", offset=(0.0, 0.0, 0.0), size=(2.0, 2.0, 1.0))
    vertices = tuple(
        (x, y, z + x * 1.5)
        for x, y, z in source.vertices
    )
    sloped = MeshGeometry3D(
        id="sloped",
        vertices=vertices,
        triangle_indices=source.triangle_indices,
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"fixture": "sloped"},
        source_representation_id="sloped",
        tessellation_settings={},
        units="m",
    )

    result = generate_mass_patches(sloped)

    assert result.component_reports[0].selected_candidate == "exact_component"


def test_uncertain_source_topology_is_reported_without_silent_simplification():
    """Open source topology remains exact and exposes an uncertainty record."""
    closed = _box_mesh()
    source = MeshGeometry3D(
        id=closed.id,
        vertices=closed.vertices,
        triangle_indices=closed.triangle_indices,
        normals=closed.normals,
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance=closed.local_to_world_provenance,
        source_representation_id=closed.source_representation_id,
        tessellation_settings=closed.tessellation_settings,
        units=closed.units,
    )

    result = generate_mass_patches(source)

    assert result.component_reports[0].selected_candidate == "exact_component"
    assert "source_topology_uncertain" in result.component_reports[0].uncertainties


def test_selected_patch_provenance_contains_validation_configuration():
    """Selected patches retain the settings used for candidate validation."""
    config = MassPatchGenerationConfig(
        linear_tolerance=1e-5,
        sample_spacing=0.25,
    )

    patch = generate_mass_patches(_box_mesh(), config).patches[0]

    assert patch.provenance["validation_config"]["sample_spacing"] == 0.25
    assert "validation_result" in patch.provenance


def test_obb_failure_falls_back_to_exact_component(monkeypatch):
    """A failed OBB solver must not abort exact MassPatch generation."""
    import trimesh

    def fail_obb(_mesh):
        """Raise the same class of failure produced by an underconstrained fragment."""
        raise ValueError("insufficient independent points")

    monkeypatch.setattr(
        trimesh.base.Trimesh,
        "bounding_box_oriented",
        property(fail_obb),
    )

    result = generate_mass_patches(_box_mesh())

    assert len(result.patches) == 1
    assert result.component_reports[0].selected_candidate == "exact_component"


def test_overlapping_seat_and_back_boxes_use_collection_union():
    """Overlapping candidate boxes remain one logical occupancy collection."""
    source = _merge_meshes(
        (
            _translated_box(mesh_id="seat-source", offset=(0.0, 0.0, 1.0), size=(2.0, 2.0, 0.2)),
            _translated_box(mesh_id="back-source", offset=(0.0, 1.8, 1.2), size=(2.0, 0.2, 1.5)),
        ),
        "seat-back-source",
    )
    candidates = (
        mass_patch_from_mesh(
            _translated_box(mesh_id="seat-candidate", offset=(0.0, 0.0, 1.0), size=(2.0, 2.0, 0.2))
        ),
        mass_patch_from_mesh(
            _translated_box(mesh_id="back-candidate", offset=(0.0, 1.8, 1.2), size=(2.0, 0.2, 1.5))
        ),
    )

    report = validate_mass_patch_collection_candidate(
        source,
        candidates,
        MassPatchGenerationConfig(sample_spacing=0.1),
    )

    assert report.accepted is True
    assert report.overlap_report["overlap_pair_count"] == 1


def test_enclosing_box_that_fills_chair_leg_gap_is_rejected():
    """A full chair envelope is rejected because it fills empty floor space."""
    source = _chair_mesh()
    enclosing = mass_patch_from_mesh(
        _translated_box(
            mesh_id="enclosing-chair",
            offset=(0.0, 0.0, 0.0),
            size=(2.0, 2.0, 2.7),
        )
    )

    report = validate_mass_patch_collection_candidate(
        source,
        (enclosing,),
        MassPatchGenerationConfig(sample_spacing=0.1),
    )

    assert report.accepted is False
    assert report.rejection_reason in {
        "plan_overreach",
        "vertical_endpoint_error",
        "occlusion_disagreement",
    }
