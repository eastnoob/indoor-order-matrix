"""Tests for source-independent functional geometry substitutes."""

from __future__ import annotations

import json

from ..features.geometry_substitutes import (
    AffordanceZone,
    MassPatch,
    SurfacePatch,
    mass_patch_from_mesh,
    surface_patch_from_fact,
)
from ..features.scene_contract import MeshGeometry3D, SurfaceFact


def _box_mesh(*, mesh_id: str = "box", top: float = 1.0) -> MeshGeometry3D:
    """Build a deterministic closed box mesh for substitute tests."""
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


def test_mass_patch_preserves_source_and_supports_multiple_functional_views():
    """A mass substitute retains factual geometry and provenance."""
    patch = mass_patch_from_mesh(_box_mesh())

    assert isinstance(patch, MassPatch)
    assert patch.source_geometry_id == "box"
    assert patch.is_closed is True
    assert patch.to_dict()["source_geometry_id"] == "box"


def test_surface_patch_keeps_color_and_elevation_separate_from_mass():
    """A surface substitute can describe a carpet without inventing mass."""
    fact = SurfaceFact(
        id="carpet",
        source_id="carpet-source",
        host_refs=(),
        identity="carpet",
        color="#aa0000",
        finish=None,
        texture=None,
        elevation={"constant": 0.0},
        slope=None,
        geometry_refs=("box",),
    )

    patch = surface_patch_from_fact(fact)

    assert isinstance(patch, SurfacePatch)
    assert patch.source_surface_id == "carpet"
    assert patch.color == "#aa0000"
    assert patch.to_dict()["mass_geometry_refs"] == ()
    json.dumps(patch.to_dict())


def test_affordance_zone_is_explicit_and_json_serializable():
    """An affordance substitute carries authored purpose and vertical extent."""
    zone = AffordanceZone(
        id="chair-pullback",
        source_zone_id="chair-pullback",
        geometry_refs=("box",),
        vertical_extent=(0.0, 1.2),
        purpose="chair_pullback",
        source_furniture_refs=("chair",),
    )

    assert zone.to_dict()["purpose"] == "chair_pullback"
    assert zone.vertical_extent == (0.0, 1.2)
    json.dumps(zone.to_dict())
