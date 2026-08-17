"""Tests for weight-free analyzer-derived boundary evidence."""

from __future__ import annotations

from dataclasses import replace
import json
import pytest

from ..features.boundary_evidence import derive_boundary_evidence
from ..features.geometry_substitutes import mass_patch_from_mesh, surface_patch_from_fact
from ..features.scene_contract import SurfaceFact
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


def test_surface_boundary_has_no_mass_but_has_surface_and_unknown_optics():
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
    assert evidence.visual_permeability[0]["status"] == "unknown"
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
    )[0]

    assert evidence.physical_continuity["occupied_height"] == ((0.0, 1.0), (0.0, 2.0))
    assert evidence.visual_permeability[0]["status"] == "blocked"
    assert evidence.provenance["method"] == "mesh_geometry_transport"
    assert json.loads(json.dumps(evidence.to_dict()))["provenance"]["method"] == (
        "mesh_geometry_transport"
    )


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
