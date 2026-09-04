"""Tests for weight-free analyzer-derived boundary evidence."""

from __future__ import annotations

from dataclasses import replace
import json
import pytest

from ..features.boundary_evidence import (
    derive_boundary_evidence,
    derive_boundary_evidence_for_collection,
)
from ..features.geometry_substitutes import mass_patch_from_mesh, surface_patch_from_fact
from ..features.scene_contract import AnalysisPlane, SurfaceFact
from .test_geometry_substitutes import _box_mesh


def test_boundary_evidence_keeps_four_channels_separate():
    """A physical patch exposes independent factual channel records."""
    patch = mass_patch_from_mesh(_box_mesh(mesh_id="low-cabinet", top=1.0))

    evidence = derive_boundary_evidence(
        (patch,),
        body_profiles=({"id": "adult", "height_band": (0.0, 1.8), "radius": 0.3},),
        visual_bands=({"id": "eye", "height_band": (1.5, 1.8)},),
    )[0]

    assert evidence.source_refs == (patch.id,)
    assert evidence.physical_continuity["occupied_height"] == (0.0, 1.0)
    assert evidence.walking_permeability[0]["status"] == "blocked"
    assert evidence.visual_permeability[0]["status"] == "clear"
    assert "alignment" in evidence.gestalt_continuity
    assert "boundary_strength" not in evidence.to_dict()
    assert "walk_block" not in evidence.to_dict()
    json.dumps(evidence.to_dict())


def test_surface_boundary_has_no_mass_and_is_geometrically_clear():
    """A carpet can be a surface cue without becoming a collision solid."""
    surface = surface_patch_from_fact(
        SurfaceFact(
            id="carpet",
            source_id="carpet-source",
            host_refs=(),
            identity="carpet",
            color="#aa0000",
            finish=None,
            texture=None,
            elevation={"constant": 0.0},
            slope=None,
            geometry_refs=(),
        )
    )

    evidence = derive_boundary_evidence((surface,))[0]

    assert evidence.physical_continuity["mass_present"] is False
    assert evidence.walking_permeability[0]["status"] == "clear"
    assert evidence.visual_permeability[0]["status"] == "clear"
    assert evidence.gestalt_continuity["surface_identity"] == "carpet"


def test_subject_relation_marks_out_of_range_without_zeroing_evidence():
    """A range limit controls evaluation and never fabricates a zero relation."""
    patch = mass_patch_from_mesh(_box_mesh(mesh_id="wall"))
    evidence = derive_boundary_evidence((patch,))[0]

    relation = evidence.relate_subject(
        {"id": "chair-group", "centroid": (20.0, 20.0)},
        max_distance=1.0,
    )

    assert relation["status"] == "not_evaluated"
    assert "score" not in relation


def test_disconnected_components_contribute_all_local_height_intervals():
    """Boundary channels must inspect every disconnected mass component."""
    first = _box_mesh(mesh_id="split", top=1.0)
    second = _box_mesh(mesh_id="split", top=2.0)
    second = replace(
        second,
        vertices=tuple((x + 5.0, y, z) for x, y, z in second.vertices),
    )
    offset = len(first.vertices)
    combined = replace(
        first,
        vertices=first.vertices + second.vertices,
        triangle_indices=first.triangle_indices
        + tuple(
            tuple(index + offset for index in triangle)
            for triangle in second.triangle_indices
        ),
    )

    evidence = derive_boundary_evidence(
        (mass_patch_from_mesh(combined),),
        visual_bands=({"id": "eye", "height_band": (1.5, 1.8)},),
        optical_transmittance_by_source={"split": 0.0},
    )[0]

    assert evidence.physical_continuity["occupied_height"] == ((0.0, 1.0), (0.0, 2.0))
    assert evidence.visual_permeability[0]["status"] == "blocked"
    assert evidence.provenance["method"] == "mesh_geometry_transport"
    assert json.loads(json.dumps(evidence.to_dict()))["provenance"]["method"] == (
        "mesh_geometry_transport"
    )


def test_visual_channel_distinguishes_unknown_opaque_and_transmitting_optics():
    """Eye-band intersections require measured optics for a resolved state."""
    patches = tuple(
        mass_patch_from_mesh(_box_mesh(mesh_id=mesh_id, top=2.0))
        for mesh_id in ("unknown", "opaque", "glass")
    )

    evidence = derive_boundary_evidence(
        patches,
        visual_bands=({"id": "eye", "height_band": (1.5, 1.8)},),
        optical_transmittance_by_source={"opaque": 0.0, "glass": 0.7},
    )

    by_source = {item.source_refs[0]: item.visual_permeability[0] for item in evidence}
    assert by_source["mass-patch:unknown"]["status"] == "unknown"
    assert by_source["mass-patch:opaque"]["status"] == "blocked"
    assert by_source["mass-patch:glass"]["status"] == "transmitting"
    assert by_source["mass-patch:glass"]["optical_transmittance"] == 0.7


def test_non_xy_analysis_plane_matches_equivalent_xy_channel_evidence():
    """Height bands must be evaluated along the authored plane normal."""
    xy_patch = mass_patch_from_mesh(_box_mesh(mesh_id="xy", top=2.0))
    rotated_mesh = _box_mesh(mesh_id="rotated", top=2.0)
    rotated_mesh = replace(
        rotated_mesh,
        vertices=tuple((x, -z, y) for x, y, z in rotated_mesh.vertices),
    )
    rotated_patch = mass_patch_from_mesh(rotated_mesh)
    rotated_plane = AnalysisPlane(
        name="vertical-local-plane",
        origin=(0.0, 0.0, 0.0),
        basis=((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    )
    query = ({"id": "eye", "height_band": (1.5, 1.8)},)

    xy = derive_boundary_evidence(
        (xy_patch,), visual_bands=query,
        optical_transmittance_by_source={"xy": 0.0},
    )[0]
    rotated = derive_boundary_evidence(
        (rotated_patch,), visual_bands=query,
        optical_transmittance_by_source={"rotated": 0.0},
        analysis_plane=rotated_plane,
    )[0]

    assert rotated.visual_permeability[0]["status"] == xy.visual_permeability[0]["status"]
    assert (
        rotated.visual_permeability[0]["query_projection"]["components"]
        == xy.visual_permeability[0]["query_projection"]["components"]
    )
    assert rotated.projection.components == xy.projection.components


def test_surface_uses_referenced_geometry_for_location_without_acquiring_mass():
    """A surface cue can be spatially related through its referenced geometry."""
    mesh_patch = mass_patch_from_mesh(_box_mesh(mesh_id="carpet-geometry", top=0.01))
    surface = surface_patch_from_fact(
        SurfaceFact(
            id="carpet",
            source_id="carpet-source",
            host_refs=(),
            identity="carpet",
            color="#aa0000",
            finish=None,
            texture=None,
            elevation={"constant": 0.0},
            slope=None,
            geometry_refs=("carpet-geometry",),
        )
    )

    evidence = derive_boundary_evidence((mesh_patch, surface))
    surface_evidence = next(item for item in evidence if item.source_refs == (surface.id,))
    relation = surface_evidence.relate_subject(
        {"id": "chair", "centroid": (-0.1, 1.0)},
        max_distance=0.2,
    )

    assert surface_evidence.projection is not None
    assert surface_evidence.physical_continuity["mass_present"] is False
    assert relation["status"] == "evaluated"


def test_subject_range_uses_nearest_boundary_geometry_not_interior_sample():
    """A subject near a long edge remains in range regardless of polygon size."""
    mesh = _box_mesh(mesh_id="long-wall")
    mesh = replace(mesh, vertices=tuple((x * 50.0, y, z) for x, y, z in mesh.vertices))
    evidence = derive_boundary_evidence((mass_patch_from_mesh(mesh),))[0]

    relation = evidence.relate_subject(
        {"id": "chair", "centroid": (-0.1, 1.0)},
        max_distance=0.2,
    )

    assert relation["status"] == "evaluated"
    assert relation["distance"] == pytest.approx(0.1)
    assert relation["nearest_side"] == pytest.approx((0.1, 0.0))


@pytest.mark.parametrize("height_band", [(1.0,), (2.0, 1.0), (0.0, float("inf"))])
def test_invalid_query_height_bands_are_rejected(height_band):
    """Malformed query bands cannot silently create permeability evidence."""
    patch = mass_patch_from_mesh(_box_mesh())

    with pytest.raises(ValueError, match="height_band"):
        derive_boundary_evidence(
            (patch,),
            body_profiles=({"id": "invalid", "height_band": height_band},),
        )


def test_collection_boundary_evidence_uses_union_height_and_plan():
    """An explicit logical collection yields one non-duplicated boundary record."""
    first = mass_patch_from_mesh(_box_mesh(mesh_id="seat", top=1.0))
    second_mesh = _box_mesh(mesh_id="back", top=2.0)
    second = mass_patch_from_mesh(
        replace(
            second_mesh,
            vertices=tuple((x + 1.0, y, z) for x, y, z in second_mesh.vertices),
        )
    )

    evidence = derive_boundary_evidence_for_collection(
        (first, second),
        body_profiles=({"id": "adult", "height_band": (0.0, 1.8), "radius": 0.3},),
        visual_bands=({"id": "eye", "height_band": (1.5, 1.8)},),
        optical_transmittance=0.0,
    )

    assert evidence.source_refs == (first.id, second.id)
    assert evidence.physical_continuity["mass_present"] is True
    assert evidence.physical_continuity["component_count"] == 1
    assert evidence.walking_permeability[0]["status"] == "blocked"
    assert evidence.visual_permeability[0]["status"] == "blocked"
