"""Contract tests for source-independent Neutral Scene v2 records."""

import inspect
import json
import math

import pytest

from ..features.scene_contract import (
    NEUTRAL_SCENE_V2,
    AnalysisContext,
    AnalysisDomain,
    AnalysisPlane,
    AuthoredAffordanceZone,
    AuthoredGrid,
    AuthoredGridAxis,
    AuthoredGroup,
    MaterialFact,
    MeshGeometry3D,
    NeutralSceneV2,
    SourceObject,
    SourceOpening,
    SurfaceFact,
    UncertaintyRecord,
)
from ..features import scene_contract as scene_contract_module


def _uncertainty() -> UncertaintyRecord:
    """Return representative missing-evidence metadata."""
    return UncertaintyRecord(
        code="optical_data_unavailable",
        message="No measured visible transmittance was supplied.",
        source_refs=("material:glass",),
        operation="material_extraction",
        severity="warning",
        details={"requested_property": "visible_transmittance"},
    )


def _context(**overrides: object) -> AnalysisContext:
    """Return a complete valid analysis context with optional replacements."""
    values = {
        "contract_version": NEUTRAL_SCENE_V2,
        "source_schema": "IFC4",
        "adapter_version": "0.1.0",
        "source_length_unit": "mm",
        "analysis_length_unit": "m",
        "world_coordinate_system": {"name": "IFC world", "handedness": "right"},
        "level_references": ("level:ground",),
        "analysis_plane": AnalysisPlane(
            name="ground-plan",
            origin=(10.0, 20.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        "geometry_tolerance": 0.001,
        "topology_tolerance": 0.005,
        "walking_body_profiles": ({"id": "adult", "radius": 0.3, "height": 1.8},),
        "visual_height_bands": ({"id": "seated", "min": 0.8, "max": 1.25},),
        "capability_flags": {
            "has_3d_geometry": True,
            "has_optical_facts": False,
            "has_authored_grid": True,
        },
        "input_mode": "ifc",
    }
    values.update(overrides)
    return AnalysisContext(**values)


def _mesh(**overrides: object) -> MeshGeometry3D:
    """Return a valid triangular transport mesh with optional replacements."""
    values = {
        "id": "geometry:chair",
        "vertices": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        "triangle_indices": ((0, 1, 2),),
        "normals": ((0.0, 0.0, 1.0),),
        "is_manifold": False,
        "is_closed": False,
        "local_to_world_provenance": {"method": "ifc-placement-chain"},
        "source_representation_id": "ifc-representation:42",
        "tessellation_settings": {"deflection_tolerance": 0.001},
        "units": "m",
    }
    values.update(overrides)
    return MeshGeometry3D(**values)


def _representative_scene(domain: AnalysisDomain | None = None) -> NeutralSceneV2:
    """Build one scene exercising every Gate 1 record type."""
    warning = _uncertainty()
    domain = domain or AnalysisDomain(
        id="domain:room",
        geometry_refs=("geometry:room",),
        source_id="ifc:space:1",
        selection_method="explicit_ifc_space",
        provenance={"adapter": "ifc"},
        uncertainties=(),
    )
    axis_x = AuthoredGridAxis(
        id="grid-axis:x:a",
        source_id="ifc:grid-axis:a",
        curve_points=((0.0, 0.0, 0.0), (10.0, 0.0, 0.0)),
        branch_identifier="x",
        list_identifier="A",
        provenance={"axis_tag": "A"},
    )
    return NeutralSceneV2(
        context=_context(),
        analysis_domain=domain,
        source_objects=(
            SourceObject(
                id="object:chair",
                source_id="ifc:chair:1",
                source_role="furniture",
                source_class="IfcFurniture",
                world_transform=(
                    (1.0, 0.0, 0.0, 10.0),
                    (0.0, 1.0, 0.0, 20.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                ),
                level_ref="level:ground",
                container_refs=("domain:room",),
                geometry_refs=("geometry:chair",),
                type_ref="type:chair",
                group_refs=("group:table-chair",),
                material_refs=("material:glass",),
                surface_refs=("surface:carpet",),
                opening_refs=("opening:door",),
                authored_local_frame={"x_axis": [1.0, 0.0, 0.0]},
                provenance={"global_id": "chair-guid"},
                uncertainties=(warning,),
            ),
        ),
        geometries=(_mesh(),),
        materials=(
            MaterialFact(
                id="material:glass",
                source_id="ifc:material:1",
                identity="clear glass",
                visible_transmittance=None,
                viewport_transparency=0.7,
                provenance={"source": "viewport-style"},
                uncertainties=(warning,),
            ),
        ),
        surfaces=(
            SurfaceFact(
                id="surface:carpet",
                source_id="ifc:covering:1",
                host_refs=("object:floor",),
                identity="carpet-zone",
                color={"space": "sRGB", "value": [0.2, 0.4, 0.6]},
                finish="woven",
                texture="low-pile",
                elevation={"value": 0.0, "unit": "m"},
                slope={"rise_over_run": 0.0},
                geometry_refs=("geometry:carpet",),
                provenance={"source": "IfcCovering"},
                uncertainties=(),
            ),
        ),
        authored_groups=(
            AuthoredGroup(
                id="group:table-chair",
                source_id="ifc:group:1",
                member_refs=("object:chair", "object:table"),
                group_role="furniture_group",
                provenance={"relationship": "IfcRelAssignsToGroup"},
            ),
        ),
        authored_grids=(
            AuthoredGrid(
                id="grid:main",
                source_id="ifc:grid:1",
                axis_refs=("grid-axis:x:a",),
                provenance={"source_class": "IfcGrid"},
            ),
        ),
        authored_grid_axes=(axis_x,),
        authored_affordances=(
            AuthoredAffordanceZone(
                id="affordance:chair-pullback",
                geometry_refs=("geometry:chair-affordance",),
                vertical_extent=(0.0, 1.2),
                purpose="chair_pullback",
                task_facts={"occupancy": "temporary"},
                source_furniture_refs=("object:chair",),
                provenance={"authored_by": "designer"},
                uncertainties=(),
            ),
        ),
        openings=(
            SourceOpening(
                id="opening:door",
                source_id="ifc:opening:1",
                host_refs=("object:wall",),
                geometry_refs=("geometry:door-opening",),
                opening_kind="doorway",
                provenance={"source_class": "IfcOpeningElement"},
                uncertainties=(),
            ),
        ),
        uncertainties=(warning,),
    )


def test_complete_scene_round_trips_through_json() -> None:
    """Every nested record must survive a plain JSON round trip exactly."""
    scene = _representative_scene()

    payload = scene.to_dict()
    reopened = NeutralSceneV2.from_dict(json.loads(json.dumps(payload)))

    assert reopened == scene
    assert reopened.to_dict() == payload
    assert reopened.context.source_length_unit == "mm"
    assert reopened.context.analysis_plane.origin == (10.0, 20.0, 0.0)
    assert reopened.source_objects[0].provenance["global_id"] == "chair-guid"
    assert reopened.geometries[0].triangle_indices == ((0, 1, 2),)


def test_missing_domain_and_capabilities_are_explicit() -> None:
    """Unavailable evidence must remain distinct from an empty or zero value."""
    context = _context(
        capability_flags={
            "has_3d_geometry": False,
            "has_optical_facts": False,
            "has_authored_grid": False,
        }
    )
    scene = NeutralSceneV2(context=context, analysis_domain=None)

    payload = scene.to_dict()
    reopened = NeutralSceneV2.from_dict(payload)

    assert payload["analysis_domain"] is None
    assert reopened.analysis_domain is None
    assert reopened.context.capability_flags["has_3d_geometry"] is False
    assert "domain:zero" not in json.dumps(payload)


@pytest.mark.parametrize("version", ["v2", "neutral-scene-v1", "", None])
def test_context_rejects_invalid_contract_version(version: object) -> None:
    """Only the single published Neutral Scene v2 identifier is valid."""
    with pytest.raises(ValueError, match="contract_version"):
        _context(contract_version=version)


@pytest.mark.parametrize("mode", ["IFC", "blender", "", None])
def test_context_rejects_invalid_input_mode(mode: object) -> None:
    """Input modes are exact adapter-boundary values."""
    with pytest.raises(ValueError, match="input_mode"):
        _context(input_mode=mode)


@pytest.mark.parametrize("value", [0.0, -0.1, math.inf, math.nan, True])
@pytest.mark.parametrize("field_name", ["geometry_tolerance", "topology_tolerance"])
def test_context_rejects_invalid_tolerances(
    value: object,
    field_name: str,
) -> None:
    """Geometry and topology tolerances must be positive finite numbers."""
    with pytest.raises(ValueError, match=field_name):
        _context(**{field_name: value})


@pytest.mark.parametrize(
    ("name", "origin", "basis"),
    [
        (
            "bad-origin",
            (0.0, math.inf, 0.0),
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        (
            "scaled",
            (0.0, 0.0, 0.0),
            ((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        (
            "not-orthogonal",
            (0.0, 0.0, 0.0),
            ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        ),
    ],
)
def test_analysis_plane_rejects_nonfinite_or_nonorthonormal_data(
    name: str,
    origin: tuple[float, float, float],
    basis: tuple[tuple[float, float, float], ...],
) -> None:
    """Analysis planes require a finite origin and orthonormal 3D basis."""
    with pytest.raises(ValueError, match="analysis_plane"):
        AnalysisPlane(name=name, origin=origin, basis=basis)


@pytest.mark.parametrize("unit", ["", "metres", "parsec", None])
def test_context_and_mesh_reject_unsupported_units(unit: object) -> None:
    """Length units must use the contract's normalized unit vocabulary."""
    with pytest.raises(ValueError, match="length_unit"):
        _context(source_length_unit=unit)
    with pytest.raises(ValueError, match="units"):
        _mesh(units=unit)


@pytest.mark.parametrize("bad_id", ["", "   ", None, 42])
def test_records_reject_empty_or_non_string_stable_ids(bad_id: object) -> None:
    """Addressable records require non-empty stable string identifiers."""
    with pytest.raises(ValueError, match="id"):
        AnalysisDomain(
            id=bad_id,
            geometry_refs=(),
            source_id=None,
            selection_method="explicit",
            provenance={},
            uncertainties=(),
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"vertices": ((0.0, 0.0, math.nan),)}, "vertices"),
        ({"triangle_indices": ((0, 1),)}, "triangle_indices"),
        ({"triangle_indices": ((0, 1, 3),)}, "triangle_indices"),
        ({"triangle_indices": ((0, True, 2),)}, "triangle_indices"),
        ({"normals": ((0.0, 1.0),)}, "normals"),
    ],
)
def test_mesh_rejects_invalid_geometry(overrides: dict[str, object], message: str) -> None:
    """Transport meshes reject malformed finite geometry and triangle indices."""
    with pytest.raises(ValueError, match=message):
        _mesh(**overrides)


def test_source_object_rejects_nonfinite_world_transform() -> None:
    """Object placement matrices cannot carry nonfinite coordinates."""
    with pytest.raises(ValueError, match="world_transform"):
        SourceObject(
            id="object:bad",
            source_id="source:bad",
            source_role="furniture",
            source_class="IfcFurniture",
            world_transform=((1.0, 0.0), (0.0, math.inf)),
        )


class RawMeshWrapper:
    """Stand in for an unsupported application-owned geometry object."""


def test_serializer_rejects_raw_objects_with_precise_record_path() -> None:
    """Application objects cannot leak through open provenance payloads."""
    scene = _representative_scene()
    scene.source_objects[0].provenance["adapter"] = {"raw_mesh": RawMeshWrapper()}

    with pytest.raises(
        TypeError,
        match=r"source_objects\[0\]\.provenance\.adapter\.raw_mesh.*RawMeshWrapper",
    ):
        scene.to_dict()


def test_from_dict_rejects_raw_objects_with_precise_record_path() -> None:
    """Deserialization validates nested payloads before constructing records."""
    payload = _representative_scene().to_dict()
    payload["materials"][0]["provenance"] = {"ifc_entity": RawMeshWrapper()}

    with pytest.raises(
        TypeError,
        match=r"materials\[0\]\.provenance\.ifc_entity.*RawMeshWrapper",
    ):
        NeutralSceneV2.from_dict(payload)


def test_contract_module_has_no_optional_integration_imports() -> None:
    """The neutral contract remains importable without source applications."""
    source = inspect.getsource(scene_contract_module)

    for forbidden in ("bpy", "bonsai", "ifcopenshell", "svgwrite", "svgpathtools", "octa"):
        assert forbidden not in source.lower()


def test_contract_payload_has_no_weight_or_collapsed_boundary_fields() -> None:
    """Neutral records must not contain model weights, scores, or collapsed channels."""
    payload_text = json.dumps(_representative_scene().to_dict())

    for forbidden in (
        "perceptual_weight",
        "final_score",
        "boundary_strength",
        "walk_block",
        "see_block",
        "grouping_strength",
    ):
        assert forbidden not in payload_text


def test_every_record_declares_an_explicit_from_dict() -> None:
    """Concrete records keep visible deserialization entry points after refactors."""
    record_types = (
        AnalysisPlane,
        UncertaintyRecord,
        AnalysisContext,
        AnalysisDomain,
        SourceObject,
        MeshGeometry3D,
        MaterialFact,
        SurfaceFact,
        AuthoredGroup,
        AuthoredGridAxis,
        AuthoredGrid,
        AuthoredAffordanceZone,
        SourceOpening,
        NeutralSceneV2,
    )

    assert all("from_dict" in record_type.__dict__ for record_type in record_types)
