"""Tests for open and mixed-topology MassPatch generation."""

from __future__ import annotations

from ..features.scene_contract import MeshGeometry3D
from ..features.mass_patch_generation import generate_mass_patches
from .test_mass_patch_generation import _box_mesh, _translated_box


def _open_top_box_mesh() -> MeshGeometry3D:
    """Build an open box by removing the top face from a solid box."""
    closed = _box_mesh(mesh_id="open-top-box")
    triangles = tuple(
        triangle
        for index, triangle in enumerate(closed.triangle_indices)
        if index not in {3, 4}
    )
    return MeshGeometry3D(
        id="open-top-box",
        vertices=closed.vertices,
        triangle_indices=triangles,
        normals=closed.normals,
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "open_top_box"},
        source_representation_id=closed.source_representation_id,
        tessellation_settings=closed.tessellation_settings,
        units=closed.units,
    )


def _mixed_topology_mesh() -> MeshGeometry3D:
    """Build one closed box component plus one open plate component."""
    closed = _translated_box(
        mesh_id="mixed-closed",
        offset=(0.0, 0.0, 0.0),
        size=(1.0, 1.0, 1.0),
    )
    open_plate = MeshGeometry3D(
        id="mixed-open",
        vertices=((5.0, 0.0, 0.0), (6.0, 0.0, 0.0), (6.0, 1.0, 0.0), (5.0, 1.0, 0.0)),
        triangle_indices=((0, 1, 2), (0, 2, 3)),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "mixed_open_plate"},
        source_representation_id="mixed-open",
        tessellation_settings={},
        units="m",
    )
    return MeshGeometry3D(
        id="mixed-topology",
        vertices=closed.vertices + open_plate.vertices,
        triangle_indices=closed.triangle_indices + tuple(
            tuple(index + len(closed.vertices) for index in triangle)
            for triangle in open_plate.triangle_indices
        ),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "mixed_topology"},
        source_representation_id="mixed-topology",
        tessellation_settings={},
        units="m",
    )


def _mixed_with_open_volume_mesh() -> MeshGeometry3D:
    """Build a parent-open object containing a solid and an open volume."""
    closed = _translated_box(
        mesh_id="mixed-solid",
        offset=(0.0, 0.0, 0.0),
        size=(1.0, 1.0, 1.0),
    )
    open_box = _open_top_box_mesh()
    open_vertices = tuple((x + 3.0, y, z) for x, y, z in open_box.vertices)
    return MeshGeometry3D(
        id="mixed-open-volume",
        vertices=closed.vertices + open_vertices,
        triangle_indices=closed.triangle_indices + tuple(
            tuple(index + len(closed.vertices) for index in triangle)
            for triangle in open_box.triangle_indices
        ),
        normals=(),
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"fixture": "mixed_open_volume"},
        source_representation_id="mixed-open-volume",
        tessellation_settings={},
        units="m",
    )


def test_component_topology_is_derived_per_split_component():
    """Each factual split component keeps its own topology facts."""
    result = generate_mass_patches(_mixed_topology_mesh())

    assert [report.component_index for report in result.component_reports] == [0, 1]
    assert result.component_reports[0].uncertainties == ()
    assert "source_topology_uncertain" in result.component_reports[1].uncertainties


def test_mixed_object_keeps_closed_components_as_cuboid_patches():
    """An open component must not force closed components back to source meshes."""
    result = generate_mass_patches(_mixed_topology_mesh())

    methods = {
        patch.provenance.get("candidate_method")
        for patch in result.patches
    }

    assert "cuboid_collection" in methods or "open_envelope_collection" in methods
    assert result.component_reports[0].selected_candidate in {
        "cuboid_collection",
        "open_envelope_collection",
    }
    assert result.component_reports[1].selected_candidate in {
        "open_envelope_collection",
        "exact_component",
    }


def test_parent_open_object_prefers_compact_proxy_for_open_component():
    """An available uncertain envelope must replace copied open source mesh data."""
    result = generate_mass_patches(_mixed_with_open_volume_mesh())

    assert result.component_reports[0].selected_candidate in {
        "cuboid_collection",
        "open_envelope_collection",
    }
    assert result.component_reports[1].selected_candidate in {
        "cuboid_collection",
        "open_envelope_collection",
    }
    assert all(
        patch.provenance.get("candidate_method") != "exact_component"
        for patch in result.patches
    )


def test_open_mesh_can_select_a_conservative_envelope_collection():
    """An open mesh can choose a conservative envelope substitute."""
    result = generate_mass_patches(_open_top_box_mesh())

    assert result.selected_collection_method == "open_envelope_collection"
    assert result.collection_report is not None
    assert result.collection_report.accepted is True
    assert result.collection_report.rejection_reason is None
    assert result.collection_report.uncertainties == ("open_envelope_uncertain",)
    assert result.patches[0].provenance["validation_result"]["uncertainties"] == (
        "open_envelope_uncertain",
    )
