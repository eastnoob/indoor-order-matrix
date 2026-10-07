"""Tests for explicit Blender geometry and hybrid Neutral Scene input modes."""

from __future__ import annotations

import json

import pytest

from ..features.scene_contract import (
    AnalysisContext,
    AnalysisDomain,
    AnalysisPlane,
    AuthoredGroup,
    MeshGeometry3D,
    NEUTRAL_SCENE_V2,
    NeutralSceneV2,
    SourceOpening,
    SourceObject,
)
from ..adapters.blender_geometry import load_blender_neutral_scene


def _context(input_mode: str) -> AnalysisContext:
    """Build a minimal context for adapter-isolation tests."""
    return AnalysisContext(
        contract_version=NEUTRAL_SCENE_V2,
        source_schema="IFC4",
        adapter_version="fixture/1.0",
        source_length_unit="m",
        analysis_length_unit="m",
        world_coordinate_system={"fixture": True},
        level_references=(),
        analysis_plane=AnalysisPlane(
            name="fixture-plane",
            origin=(0.0, 0.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        geometry_tolerance=1e-6,
        topology_tolerance=1e-6,
        walking_body_profiles=(),
        visual_height_bands=(),
        capability_flags={"height": True},
        input_mode=input_mode,
    )


def _ifc_scene() -> NeutralSceneV2:
    """Build a small IFC scene used as the immutable hybrid baseline."""
    mesh = MeshGeometry3D(
        id="ifc-mesh:chair",
        vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        triangle_indices=((0, 1, 2),),
        normals=((0.0, 0.0, 1.0),),
        is_manifold=True,
        is_closed=False,
        local_to_world_provenance={"coordinate_space": "world"},
        source_representation_id=None,
        tessellation_settings={},
        units="m",
    )
    source_object = SourceObject(
        id="ifc-object:chair",
        source_id="chair-global-id",
        source_role="furniture",
        source_class="IfcFurniture",
        geometry_refs=(mesh.id,),
        provenance={"fixture": True},
    )
    return NeutralSceneV2(
        context=_context("ifc"),
        source_objects=(source_object,),
        geometries=(mesh,),
    )


def _blender_source() -> dict[str, object]:
    """Return selected and unselected evaluated mesh snapshots."""
    triangle = {
        "vertices": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        "triangles": ((0, 1, 2),),
    }
    return {
        "objects": (
            {"id": "chair-helper", "name": "Chair", "selected": True, **triangle},
            {"id": "distractor", "name": "Chair", "selected": False, **triangle},
        )
    }


def test_blender_geometry_mode_reads_only_selected_objects_and_explicit_roles():
    """Selection is the geometry allowlist and names do not become semantics."""
    scene = load_blender_neutral_scene(
        _blender_source(),
        mode="blender_geometry",
        roles={"chair-helper": "furniture"},
    )

    assert [item.id for item in scene.source_objects] == [
        "blender-object:chair-helper"
    ]
    assert scene.source_objects[0].source_id is None
    assert scene.source_objects[0].source_role == "furniture"
    assert scene.source_objects[0].source_class is None
    assert scene.context.input_mode == "blender_geometry"
    assert scene.context.capability_flags["blender_geometry"] is True


def test_ifc_mode_ignores_all_blender_objects_and_returns_ifc_scene():
    """Opening a Blender payload cannot alter an explicitly selected IFC scene."""
    ifc_scene = _ifc_scene()

    result = load_blender_neutral_scene(
        _blender_source(),
        mode="ifc",
        ifc_scene=ifc_scene,
    )

    assert result is ifc_scene
    assert result.source_objects == ifc_scene.source_objects


def test_ifc_mode_short_circuits_before_validating_blender_payload():
    """IFC mode remains usable even when no Blender payload is supplied."""
    ifc_scene = _ifc_scene()

    result = load_blender_neutral_scene(object(), mode="ifc", ifc_scene=ifc_scene)

    assert result is ifc_scene


def test_hybrid_mode_includes_only_explicitly_linked_helpers():
    """Hybrid input keeps IFC facts and adds only named helper links."""
    ifc_scene = _ifc_scene()
    source = _blender_source()

    result = load_blender_neutral_scene(
        source,
        mode="hybrid",
        ifc_scene=ifc_scene,
        hybrid_links={"chair-helper": "chair-global-id"},
        roles={"chair-helper": "furniture"},
    )

    assert {item.id for item in result.source_objects} == {
        "ifc-object:chair",
        "blender-object:chair-helper",
    }
    helper = next(
        item for item in result.source_objects if item.id == "blender-object:chair-helper"
    )
    assert helper.provenance["linked_ifc_source_id"] == "chair-global-id"
    assert "blender-object:distractor" not in {
        item.id for item in result.source_objects
    }
    assert result.context.input_mode == "hybrid"


def test_blender_geometry_requires_explicit_role_and_preserves_json_round_trip():
    """Missing roles stay unavailable and the adapter output remains JSON-safe."""
    scene = load_blender_neutral_scene(
        _blender_source(),
        mode="blender_geometry",
    )

    assert scene.source_objects[0].source_role is None
    assert scene.source_objects[0].provenance["object_name"] == "Chair"
    payload = scene.to_dict()
    assert NeutralSceneV2.from_dict(json.loads(json.dumps(payload))) == scene


def test_blender_geometry_rejects_unknown_explicit_selection_id():
    """An explicit selection must not silently omit an unknown object id."""
    with pytest.raises(ValueError, match="unknown selected Blender object"):
        load_blender_neutral_scene(
            _blender_source(),
            mode="blender_geometry",
            selected_ids=("missing",),
        )


def test_blender_geometry_rejects_unknown_explicit_role_id():
    """An explicit role mapping must identify a selected Blender object."""
    with pytest.raises(ValueError, match="unknown Blender role ids"):
        load_blender_neutral_scene(
            _blender_source(),
            mode="blender_geometry",
            roles={"missing": "furniture"},
        )


def test_blender_geometry_does_not_fabricate_bbox_for_missing_mesh():
    """A selected object without evaluated mesh becomes explicit uncertainty."""
    scene = load_blender_neutral_scene(
        {"objects": ({"id": "empty", "name": "Table", "selected": True},)},
        mode="blender_geometry",
        roles={"empty": "furniture"},
    )

    assert scene.source_objects[0].geometry_refs == ()
    assert scene.source_objects[0].uncertainties[0].code == "missing_geometry"


def test_blender_geometry_rejects_invalid_mode():
    """The Blender adapter does not silently reinterpret unsupported modes."""
    with pytest.raises(ValueError, match="ifc.*blender_geometry.*hybrid"):
        load_blender_neutral_scene(_blender_source(), mode="svg")


def test_blender_geometry_rejects_duplicate_object_ids():
    """Duplicate object ids cannot produce ambiguous source or mesh references."""
    source = _blender_source()
    duplicate = dict(source["objects"][0])
    with pytest.raises(ValueError, match="duplicate"):
        load_blender_neutral_scene(
            {"objects": (source["objects"][0], duplicate)},
            mode="blender_geometry",
        )


def test_hybrid_rejects_unknown_helper_links():
    """A link allowlist entry must identify an actual Blender helper object."""
    with pytest.raises(ValueError, match="unknown Blender"):
        load_blender_neutral_scene(
            _blender_source(),
            mode="hybrid",
            ifc_scene=_ifc_scene(),
            hybrid_links={"missing-helper": "chair-global-id"},
        )


def test_blender_geometry_rejects_dangling_explicit_domain_reference():
    """Explicit records cannot reference geometry absent from the final scene."""
    domain = AnalysisDomain(
        id="domain:room",
        geometry_refs=("blender-mesh:missing",),
        source_id=None,
        selection_method="explicit_blender_input",
    )
    with pytest.raises(ValueError, match="dangling"):
        load_blender_neutral_scene(
            _blender_source(),
            mode="blender_geometry",
            analysis_domain=domain,
        )


def test_blender_geometry_rejects_dangling_explicit_opening_host_reference():
    """A dangling opening host remains a rejected adapter reference."""
    opening = SourceOpening(
        id="opening:dangling-host",
        source_id=None,
        host_refs=("blender-object:missing-host",),
        geometry_refs=("blender-mesh:chair-helper",),
        opening_kind="doorway",
    )

    with pytest.raises(ValueError, match="dangling opening host"):
        load_blender_neutral_scene(
            _blender_source(),
            mode="blender_geometry",
            openings=(opening,),
        )


def test_blender_geometry_marks_explicit_domain_capability_available():
    """A valid explicit domain must be advertised as usable in the context."""
    domain = AnalysisDomain(
        id="domain:room",
        geometry_refs=("blender-mesh:chair-helper",),
        source_id=None,
        selection_method="explicit_blender_input",
    )

    scene = load_blender_neutral_scene(
        _blender_source(),
        mode="blender_geometry",
        analysis_domain=domain,
    )

    assert scene.context.capability_flags["analysis_domain"] is True


def test_hybrid_rejects_duplicate_ids_across_explicit_record_layers():
    """Hybrid composition cannot make one id resolve to multiple record layers."""
    group = AuthoredGroup(
        id="ifc-object:chair",
        source_id=None,
        member_refs=("ifc-object:chair",),
        group_role="furniture_group",
    )
    with pytest.raises(ValueError, match="duplicate record id"):
        load_blender_neutral_scene(
            _blender_source(),
            mode="hybrid",
            ifc_scene=_ifc_scene(),
            hybrid_links={"chair-helper": "chair-global-id"},
            authored_groups=(group,),
        )


def test_blender_geometry_rejects_domain_id_collision():
    """An analysis domain id cannot shadow an object or geometry record id."""
    domain = AnalysisDomain(
        id="blender-object:chair-helper",
        geometry_refs=("blender-mesh:chair-helper",),
        source_id=None,
        selection_method="explicit_blender_input",
    )
    with pytest.raises(ValueError, match="duplicate record id"):
        load_blender_neutral_scene(
            _blender_source(),
            mode="blender_geometry",
            analysis_domain=domain,
        )
