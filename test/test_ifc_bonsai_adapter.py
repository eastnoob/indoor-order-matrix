"""Tests for the read-only IFC4-to-Neutral-Scene adapter boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from ..adapters.ifc_bonsai import IfcDependencyUnavailable, load_ifc_neutral_scene


def _write_reopenable_ifc4(path: Path) -> str:
    """Write a minimal real IFC4 file containing one source product."""
    import ifcopenshell

    model = ifcopenshell.file(schema="IFC4")
    # A real serialized IFC file proves the adapter does not rely on the
    # private normalized payload used by the isolated boundary fixture.
    furniture = model.create_entity("IfcFurniture", Name="Table")
    furniture.GlobalId = ifcopenshell.guid.new()
    model.write(str(path))
    return furniture.GlobalId


class _FakeIfcFile:
    """A minimal IFC backend fixture with pre-normalized factual extraction data."""

    schema = "IFC4"

    def __init__(self) -> None:
        """Build stable source facts without exposing a mutable application object."""
        self.payload = {
            "source_length_unit": "m",
            "objects": (
                {
                    "global_id": "furniture-001",
                    "ifc_class": "IfcFurniture",
                    "geometry": {
                        "vertices": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                        "triangles": ((0, 1, 2),),
                    },
                },
            ),
        }

    def snapshot(self) -> str:
        """Return a stable JSON digest surrogate for no-mutation assertions."""
        return json.dumps(self.payload, sort_keys=True)


def test_adapter_reports_missing_injected_ifcopenshell_dependency():
    """A path input gives a focused error when the injected runtime is unavailable."""
    with pytest.raises(IfcDependencyUnavailable, match="IfcOpenShell"):
        load_ifc_neutral_scene("fixture.ifc", ifc_module=False)


def test_adapter_reads_a_serialized_ifc4_file_after_reopen(tmp_path):
    """A real IFC4 file is read without requiring a private payload attribute."""
    path = tmp_path / "fixture.ifc"
    expected_id = _write_reopenable_ifc4(path)

    scene = load_ifc_neutral_scene(path)

    assert scene.context.source_schema == "IFC4"
    assert scene.source_objects[0].source_id == expected_id
    assert scene.source_objects[0].source_class == "IfcFurniture"


def test_comprehensive_ifc4_fixture_round_trips_all_gate5_facts(tmp_path):
    """The deterministic IFC4 fixture covers every factual Gate 5 mapping."""
    from .fixtures.ifc4_description_fixture import write_ifc4_description_fixture

    path = tmp_path / "description-fixture.ifc"
    ids = write_ifc4_description_fixture(path)

    scene = load_ifc_neutral_scene(
        path,
        analysis_domain_source_id=ids["room"],
    )
    source_ids = {record.source_id for record in scene.source_objects}

    assert {
        ids["room"],
        ids["wall"],
        ids["slab"],
        ids["opening"],
        ids["furniture_a"],
        ids["furniture_b"],
        ids["covering"],
        ids["surface_feature"],
        ids["affordance"],
    }.issubset(source_ids)
    assert scene.analysis_domain is not None
    assert len(scene.authored_groups) == 1
    assert len(scene.authored_grids) == 1
    assert len(scene.authored_grid_axes) == 2
    axis_extents = sorted(
        max(max(abs(value) for value in point) for point in axis.curve_points)
        for axis in scene.authored_grid_axes
    )
    assert axis_extents == pytest.approx([6.0, 8.0])
    assert len(scene.openings) == 1
    assert len(scene.surfaces) == 2
    assert len(scene.authored_affordances) == 1
    assert scene.authored_affordances[0].task_facts["OM_Affordance"] == {
        "Purpose": "chair_pull_back"
    }
    assert scene.materials[0].visible_transmittance == pytest.approx(0.82)
    assert scene.materials[0].viewport_transparency == pytest.approx(0.25)
    roles = {record.source_id: record.source_role for record in scene.source_objects}
    assert roles[ids["furniture_a"]] == "furniture"
    assert roles[ids["room"]] == "space"
    assert roles[ids["wall"]] == "wall"
    assert roles[ids["slab"]] == "slab"
    assert roles[ids["grid"]] == "grid"
    assert roles[ids["opening"]] == "opening"
    assert roles[ids["covering"]] == "surface"
    assert roles[ids["surface_feature"]] == "surface"
    assert roles[ids["affordance"]] == "affordance_zone"


def test_path_adapter_loads_ifcopenshell_geometry_in_clean_process(tmp_path):
    """Path adaptation tessellates without relying on prior geometry API imports."""
    from .fixtures.ifc4_description_fixture import write_ifc4_description_fixture

    path = tmp_path / "clean-process.ifc"
    write_ifc4_description_fixture(path)
    code = "\n".join(
        (
            "import json, sys",
            "from adapters.ifc_bonsai import load_ifc_neutral_scene",
            "scene = load_ifc_neutral_scene(sys.argv[1])",
            "print(json.dumps({'geometries': len(scene.geometries), 'axes': len(scene.authored_grid_axes)}))",
        )
    )

    result = subprocess.run(
        [sys.executable, "-c", code, str(path)],
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.strip())

    assert payload["geometries"] > 0
    assert payload["axes"] == 2


def test_adapter_tessellates_real_ifc_geometry_in_world_coordinates(tmp_path):
    """Serialized IFC mesh geometry and placement become world-coordinate triangles."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import (
        add_mesh_representation,
        assign_representation,
        edit_object_placement,
    )
    from ifcopenshell.api.root import create_entity

    path = tmp_path / "mesh.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    model_context = add_context(model, context_type="Model")
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    furniture = create_entity(model, ifc_class="IfcFurniture", name="Table")
    representation = add_mesh_representation(
        model,
        context=body_context,
        vertices=[[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]],
        faces=[[[0, 1, 2]]],
        unit_scale=1.0,
    )
    assign_representation(model, product=furniture, representation=representation)
    transform = np.identity(4)
    transform[:3, 3] = (2.0, 3.0, 0.5)
    edit_object_placement(model, product=furniture, matrix=transform, is_si=True)
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert len(scene.geometries[0].triangle_indices) == 1
    assert set(scene.geometries[0].triangle_indices[0]) == {0, 1, 2}
    assert set(scene.geometries[0].vertices) == {
        (2.0, 3.0, 0.5),
        (3.0, 3.0, 0.5),
        (2.0, 4.0, 0.5),
    }
    assert scene.source_objects[0].world_transform[0][3] == pytest.approx(2.0)
    assert scene.geometries[0].local_to_world_provenance["coordinate_space"] == "world"
    assert scene.geometries[0].local_to_world_provenance["transform_applied"] is True
    assert scene.source_objects[0].provenance["mesh_coordinate_space"] == "world"
    assert scene.source_objects[0].provenance["mesh_transform_applied"] is True


def test_adapter_reports_invalid_ifc_placement_without_losing_source_identity(
    monkeypatch,
):
    """A placement failure keeps identity geometry uncertainty and placement evidence."""
    import ifcopenshell
    import ifcopenshell.util.placement
    from ifcopenshell.api.geometry import edit_object_placement
    from ifcopenshell.api.root import create_entity

    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    furniture = create_entity(model, ifc_class="IfcFurniture", name="Table")
    edit_object_placement(model, product=furniture, matrix=np.identity(4), is_si=True)

    def fail_placement(_placement):
        """Represent one backend placement parser failure."""
        raise RuntimeError("broken placement")

    monkeypatch.setattr(
        ifcopenshell.util.placement,
        "get_local_placement",
        fail_placement,
    )

    scene = load_ifc_neutral_scene(model)
    record = next(item for item in scene.source_objects if item.source_id == furniture.GlobalId)

    assert record.world_transform == (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    uncertainty = next(item for item in record.uncertainties if item.code == "invalid_ifc_placement")
    assert uncertainty.source_refs == (furniture.GlobalId,)
    assert uncertainty.details["failure_type"] == "RuntimeError"
    assert uncertainty.details["failure_message"] == "broken placement"


def test_adapter_reports_invalid_grid_placement_as_scene_uncertainty(monkeypatch):
    """A grid placement failure remains distinct from an authored origin grid."""
    import ifcopenshell
    import ifcopenshell.util.placement
    from ifcopenshell.api.geometry import edit_object_placement
    from ifcopenshell.api.root import create_entity

    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    grid = create_entity(model, ifc_class="IfcGrid", name="Grid")
    edit_object_placement(model, product=grid, matrix=np.identity(4), is_si=True)
    curve = model.create_entity(
        "IfcPolyline",
        Points=[
            model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0)),
            model.create_entity("IfcCartesianPoint", Coordinates=(1.0, 0.0)),
        ],
    )
    grid.UAxes = [
        model.create_entity("IfcGridAxis", AxisTag="A", AxisCurve=curve, SameSense=True)
    ]

    def fail_placement(_placement):
        """Represent one grid placement parser failure."""
        raise RuntimeError("broken grid placement")

    monkeypatch.setattr(
        ifcopenshell.util.placement,
        "get_local_placement",
        fail_placement,
    )

    scene = load_ifc_neutral_scene(model)
    uncertainty = next(item for item in scene.uncertainties if item.code == "invalid_ifc_placement")

    assert uncertainty.source_refs == (grid.GlobalId,)
    assert uncertainty.details["failure_message"] == "broken grid placement"


def test_adapter_treats_nonfinite_ifc_placement_as_invalid(monkeypatch):
    """A nonfinite backend matrix becomes uncertainty instead of aborting adaptation."""
    import ifcopenshell
    import ifcopenshell.util.placement
    from ifcopenshell.api.geometry import edit_object_placement
    from ifcopenshell.api.root import create_entity

    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    furniture = create_entity(model, ifc_class="IfcFurniture", name="Table")
    edit_object_placement(model, product=furniture, matrix=np.identity(4), is_si=True)
    invalid_matrix = np.identity(4)
    invalid_matrix[0, 3] = np.nan
    monkeypatch.setattr(
        ifcopenshell.util.placement,
        "get_local_placement",
        lambda _placement: invalid_matrix,
    )

    scene = load_ifc_neutral_scene(model)
    record = next(item for item in scene.source_objects if item.source_id == furniture.GlobalId)

    assert record.world_transform[0][3] == 0.0
    uncertainty = next(item for item in record.uncertainties if item.code == "invalid_ifc_placement")
    assert uncertainty.details["failure_type"] == "ValueError"


def test_native_ifc_mesh_uses_analysis_metres_and_actual_representation_id(tmp_path):
    """A millimetre IFC keeps source units while tessellated vertices report SI metres."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import (
        add_mesh_representation,
        assign_representation,
        edit_object_placement,
    )
    from ifcopenshell.api.root import create_entity
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    path = tmp_path / "millimetre-mesh.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    length_unit = add_si_unit(model, unit_type="LENGTHUNIT", prefix="MILLI")
    assign_unit(model, units=[length_unit])
    model_context = add_context(model, context_type="Model")
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    furniture = create_entity(model, ifc_class="IfcFurniture", name="Table")
    representation = add_mesh_representation(
        model,
        context=body_context,
        # IfcOpenShell authoring APIs accept SI coordinates and serialize them
        # using the project's declared millimetre unit.
        vertices=[[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]],
        faces=[[[0, 1, 2]]],
    )
    assign_representation(model, product=furniture, representation=representation)
    transform = np.identity(4)
    transform[:3, 3] = (2.0, 0.0, 0.0)
    edit_object_placement(model, product=furniture, matrix=transform, is_si=True)
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.context.source_length_unit == "mm"
    assert scene.context.analysis_length_unit == "m"
    assert scene.geometries[0].units == "m"
    assert max(vertex[0] for vertex in scene.geometries[0].vertices) == pytest.approx(3.0)
    assert scene.geometries[0].source_representation_id == (
        f"ifc-step:{representation.id()}"
    )
    assert scene.source_objects[0].world_transform[0][3] == pytest.approx(2.0)


def test_adapter_records_representation_used_for_tessellation_not_first_candidate(
    tmp_path,
):
    """An Axis-first product records the Body representation used for its mesh."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import (
        add_axis_representation,
        add_mesh_representation,
        assign_representation,
    )
    from ifcopenshell.api.root import create_entity

    path = tmp_path / "multiple-representations.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    model_context = add_context(model, context_type="Model")
    axis_context = add_context(
        model,
        context_type="Model",
        context_identifier="Axis",
        target_view="GRAPH_VIEW",
        parent=model_context,
    )
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    furniture = create_entity(model, ifc_class="IfcFurniture", name="Table")
    axis = add_axis_representation(
        model,
        context=axis_context,
        axis=((0.0, 0.0), (1.0, 0.0)),
    )
    body = add_mesh_representation(
        model,
        context=body_context,
        vertices=[[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]],
        faces=[[[0, 1, 2]]],
    )
    assign_representation(model, product=furniture, representation=axis)
    assign_representation(model, product=furniture, representation=body)
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.geometries[0].source_representation_id == f"ifc-step:{body.id()}"


def test_adapter_uses_ifc_scale_for_micro_metre_grid_coordinates(tmp_path):
    """An explicit MICRO metre unit scales authored grid coordinates to metres."""
    import ifcopenshell

    path = tmp_path / "micro-grid.ifc"
    model = ifcopenshell.file(schema="IFC4")
    unit = model.create_entity(
        "IfcSIUnit",
        UnitType="LENGTHUNIT",
        Prefix="MICRO",
        Name="METRE",
    )
    model.create_entity("IfcUnitAssignment", Units=[unit])
    grid = model.create_entity("IfcGrid", Name="Micro grid")
    grid.GlobalId = ifcopenshell.guid.new()
    line = model.create_entity(
        "IfcPolyline",
        Points=[
            model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0)),
            model.create_entity("IfcCartesianPoint", Coordinates=(1_000_000.0, 0.0)),
        ],
    )
    grid.UAxes = [
        model.create_entity(
            "IfcGridAxis",
            AxisTag="A",
            AxisCurve=line,
            SameSense=True,
        )
    ]
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.context.source_length_unit == "um"
    assert scene.authored_grid_axes[0].curve_points[-1][0] == pytest.approx(1.0)


def test_adapter_uses_conversion_factor_for_noncanonical_ifc_unit(tmp_path):
    """A conversion-based unit keeps correct scale and explicit token uncertainty."""
    import ifcopenshell

    path = tmp_path / "yard-grid.ifc"
    model = ifcopenshell.file(schema="IFC4")
    dimensions = model.create_entity(
        "IfcDimensionalExponents",
        LengthExponent=1,
        MassExponent=0,
        TimeExponent=0,
        ElectricCurrentExponent=0,
        ThermodynamicTemperatureExponent=0,
        AmountOfSubstanceExponent=0,
        LuminousIntensityExponent=0,
    )
    metre = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
    factor = model.create_entity(
        "IfcMeasureWithUnit",
        ValueComponent=model.create_entity("IfcReal", 0.9144),
        UnitComponent=metre,
    )
    yard = model.create_entity(
        "IfcConversionBasedUnit",
        Dimensions=dimensions,
        UnitType="LENGTHUNIT",
        Name="YARD",
        ConversionFactor=factor,
    )
    model.create_entity("IfcUnitAssignment", Units=[yard])
    grid = model.create_entity("IfcGrid", Name="Yard grid")
    grid.GlobalId = ifcopenshell.guid.new()
    line = model.create_entity(
        "IfcPolyline",
        Points=[
            model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0)),
            model.create_entity("IfcCartesianPoint", Coordinates=(1.0, 0.0)),
        ],
    )
    grid.UAxes = [
        model.create_entity(
            "IfcGridAxis",
            AxisTag="A",
            AxisCurve=line,
            SameSense=True,
        )
    ]
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.context.source_length_unit == "custom"
    assert scene.authored_grid_axes[0].curve_points[-1][0] == pytest.approx(0.9144)
    unit_warning = next(
        item for item in scene.uncertainties if item.code == "noncanonical_ifc_length_unit"
    )
    assert unit_warning.details["ifc_name"] == "YARD"
    assert unit_warning.details["scale_to_metres"] == pytest.approx(0.9144)


def test_adapter_rejects_unconvertible_ifc_context_dependent_length_unit(tmp_path):
    """A context-dependent unit without SI conversion cannot masquerade as metres."""
    import ifcopenshell

    path = tmp_path / "context-unit.ifc"
    model = ifcopenshell.file(schema="IFC4")
    dimensions = model.create_entity(
        "IfcDimensionalExponents",
        LengthExponent=1,
        MassExponent=0,
        TimeExponent=0,
        ElectricCurrentExponent=0,
        ThermodynamicTemperatureExponent=0,
        AmountOfSubstanceExponent=0,
        LuminousIntensityExponent=0,
    )
    unit = model.create_entity(
        "IfcContextDependentUnit",
        Dimensions=dimensions,
        UnitType="LENGTHUNIT",
        Name="PROJECT_FOOT",
    )
    model.create_entity("IfcUnitAssignment", Units=[unit])
    model.write(str(path))

    with pytest.raises(ValueError, match="cannot be converted to metres"):
        load_ifc_neutral_scene(path)


def test_native_ifc_analysis_is_read_only_and_json_serializable(tmp_path):
    """Loading a serialized IFC leaves source bytes unchanged and emits plain JSON."""
    path = tmp_path / "read-only.ifc"
    _write_reopenable_ifc4(path)
    before = path.read_bytes()

    scene = load_ifc_neutral_scene(path)
    serialized = json.dumps(scene.to_dict(), sort_keys=True)

    assert path.read_bytes() == before
    assert "IfcFurniture" in serialized
    assert "boundary_strength" not in serialized
    assert "inferred_regions" not in serialized


def test_native_in_memory_ifc_is_not_mutated_by_adapter(tmp_path):
    """Rich native IFC adaptation preserves entity facts and serialized content."""
    import ifcopenshell
    from .fixtures.ifc4_description_fixture import write_ifc4_description_fixture

    path = tmp_path / "in-memory-read-only.ifc"
    ids = write_ifc4_description_fixture(path)
    model = ifcopenshell.open(str(path))

    def entity_snapshot():
        """Capture stable entity ids classes and STEP facts from the same model."""
        return tuple(sorted((item.id(), item.is_a(), str(item)) for item in model))

    before_entities = entity_snapshot()
    before_digest = hashlib.sha256(model.to_string().encode("utf-8")).hexdigest()

    load_ifc_neutral_scene(model, analysis_domain_source_id=ids["room"])

    after_entities = entity_snapshot()
    after_digest = hashlib.sha256(model.to_string().encode("utf-8")).hexdigest()
    assert after_entities == before_entities
    assert after_digest == before_digest


def test_adapter_preserves_native_ifc_group_and_grid_axis_facts(tmp_path):
    """Serialized IFC4 group and grid relations enter the neutral contract unchanged."""
    import ifcopenshell

    path = tmp_path / "relations.ifc"
    model = ifcopenshell.file(schema="IFC4")
    furniture = model.create_entity("IfcFurniture", Name="Chair")
    furniture.GlobalId = ifcopenshell.guid.new()
    group = model.create_entity("IfcGroup", Name="Dining set")
    group.GlobalId = ifcopenshell.guid.new()
    model.create_entity("IfcRelAssignsToGroup", RelatingGroup=group, RelatedObjects=[furniture])
    grid = model.create_entity("IfcGrid", Name="Structural axes")
    grid.GlobalId = ifcopenshell.guid.new()
    line = model.create_entity(
        "IfcPolyline",
        Points=[
            model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
            model.create_entity("IfcCartesianPoint", Coordinates=(5.0, 0.0, 0.0)),
        ],
    )
    axis = model.create_entity("IfcGridAxis", AxisTag="A", AxisCurve=line, SameSense=True)
    grid.UAxes = [axis]
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.authored_groups[0].source_id == group.GlobalId
    assert scene.authored_groups[0].member_refs == (f"ifc-object:{furniture.GlobalId}",)
    assert scene.authored_grids[0].source_id == grid.GlobalId
    assert scene.authored_grid_axes[0].branch_identifier is None
    assert scene.authored_grid_axes[0].provenance["axis_tag"] == "A"
    assert scene.authored_grid_axes[0].curve_points == ((0.0, 0.0, 0.0), (5.0, 0.0, 0.0))
    furniture_record = next(
        record for record in scene.source_objects if record.source_id == furniture.GlobalId
    )
    assert furniture_record.group_refs == (f"ifc-group:{group.GlobalId}",)


def test_adapter_applies_grid_placement_and_same_sense(tmp_path):
    """Grid axes enter world metres with authored direction semantics preserved."""
    import ifcopenshell
    from ifcopenshell.api.geometry import edit_object_placement

    path = tmp_path / "placed-grid.ifc"
    model = ifcopenshell.file(schema="IFC4")
    grid = model.create_entity("IfcGrid", Name="Placed grid")
    grid.GlobalId = ifcopenshell.guid.new()
    line = model.create_entity(
        "IfcPolyline",
        Points=[
            model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0)),
            model.create_entity("IfcCartesianPoint", Coordinates=(5.0, 0.0)),
        ],
    )
    axis = model.create_entity(
        "IfcGridAxis",
        AxisTag="A",
        AxisCurve=line,
        SameSense=False,
    )
    grid.UAxes = [axis]
    transform = np.identity(4)
    transform[:3, :3] = (
        (0.0, -1.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    transform[:3, 3] = (2.0, 3.0, 0.0)
    edit_object_placement(model, product=grid, matrix=transform, is_si=True)
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    axis_record = scene.authored_grid_axes[0]

    assert axis_record.same_sense is False
    assert np.allclose(
        axis_record.curve_points,
        ((2.0, 8.0, 0.0), (2.0, 3.0, 0.0)),
    )


def test_adapter_tessellates_non_polyline_grid_axis_curve(tmp_path):
    """A native curved grid axis is retained through IfcOpenShell tessellation."""
    import ifcopenshell

    path = tmp_path / "radial-grid.ifc"
    model = ifcopenshell.file(schema="IFC4")
    grid = model.create_entity("IfcGrid", Name="Radial grid")
    grid.GlobalId = ifcopenshell.guid.new()
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    placement = model.create_entity("IfcAxis2Placement2D", Location=origin)
    circle = model.create_entity("IfcCircle", Position=placement, Radius=2.0)
    axis = model.create_entity(
        "IfcGridAxis",
        AxisTag="R2",
        AxisCurve=circle,
        SameSense=True,
    )
    grid.UAxes = [axis]
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    points = scene.authored_grid_axes[0].curve_points

    assert len(points) > 8
    assert max((point[0] ** 2 + point[1] ** 2) ** 0.5 for point in points) == (
        pytest.approx(2.0)
    )
    assert scene.authored_grid_axes[0].same_sense is True


def test_adapter_does_not_rescale_tessellated_curved_axis_in_mm_project(tmp_path):
    """IfcOpenShell SI curve tessellation is not scaled a second time."""
    import ifcopenshell
    from ifcopenshell.api.root import create_entity
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    path = tmp_path / "radial-grid-mm.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    length_unit = add_si_unit(model, unit_type="LENGTHUNIT", prefix="MILLI")
    assign_unit(model, units=[length_unit])
    grid = create_entity(model, ifc_class="IfcGrid", name="Radial grid")
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    placement = model.create_entity("IfcAxis2Placement2D", Location=origin)
    circle = model.create_entity("IfcCircle", Position=placement, Radius=2000.0)
    grid.UAxes = [
        model.create_entity(
            "IfcGridAxis",
            AxisTag="R2",
            AxisCurve=circle,
            SameSense=True,
        )
    ]
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    points = scene.authored_grid_axes[0].curve_points

    radius = max((point[0] ** 2 + point[1] ** 2) ** 0.5 for point in points)
    assert radius == pytest.approx(2.0)


def test_adapter_reports_unusable_authored_grid_axis_curve(tmp_path):
    """A malformed authored axis becomes explicit uncertainty instead of disappearing."""
    import ifcopenshell

    path = tmp_path / "bad-axis.ifc"
    model = ifcopenshell.file(schema="IFC4")
    grid = model.create_entity("IfcGrid", Name="Broken grid")
    grid.GlobalId = ifcopenshell.guid.new()
    line = model.create_entity(
        "IfcPolyline",
        Points=[model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))],
    )
    axis = model.create_entity(
        "IfcGridAxis",
        AxisTag="bad",
        AxisCurve=line,
        SameSense=True,
    )
    grid.UAxes = [axis]
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.authored_grid_axes == ()
    assert "unsupported_grid_axis_curve" in {
        uncertainty.code for uncertainty in scene.uncertainties
    }


def test_adapter_preserves_native_ifc_opening_and_host_facts(tmp_path):
    """A serialized IFC4 opening retains its source id and voided host reference."""
    import ifcopenshell

    path = tmp_path / "opening.ifc"
    model = ifcopenshell.file(schema="IFC4")
    wall = model.create_entity("IfcWall", Name="Wall")
    wall.GlobalId = ifcopenshell.guid.new()
    opening = model.create_entity("IfcOpeningElement", Name="Door void")
    opening.GlobalId = ifcopenshell.guid.new()
    model.create_entity(
        "IfcRelVoidsElement",
        RelatingBuildingElement=wall,
        RelatedOpeningElement=opening,
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.openings[0].source_id == opening.GlobalId
    assert scene.openings[0].host_refs == (f"ifc-object:{wall.GlobalId}",)
    assert scene.openings[0].opening_kind == "IfcOpeningElement"
    wall_record = next(
        record for record in scene.source_objects if record.source_id == wall.GlobalId
    )
    assert wall_record.opening_refs == (f"ifc-opening:{opening.GlobalId}",)


def test_native_ifc_capabilities_reflect_available_geometry(tmp_path):
    """A geometry-free IFC reports height evidence unavailable instead of true."""
    path = tmp_path / "no-geometry.ifc"
    _write_reopenable_ifc4(path)

    scene = load_ifc_neutral_scene(path)

    assert scene.context.capability_flags["height"] is False


def test_adapter_reports_missing_unit_grid_and_domain_as_uncertainty(tmp_path):
    """Absent optional IFC context is explicit rather than guessed or scored zero."""
    path = tmp_path / "partial-context.ifc"
    _write_reopenable_ifc4(path)

    scene = load_ifc_neutral_scene(path)
    codes = {record.code for record in scene.uncertainties}

    assert "missing_ifc_length_unit" in codes
    assert "missing_authored_grid" in codes
    assert "missing_analysis_domain" in codes
    assert scene.context.capability_flags["authored_grid"] is False
    assert scene.context.capability_flags["analysis_domain"] is False


def test_adapter_preserves_native_geometry_failure_provenance():
    """A tessellation exception remains visible in source-object uncertainty details."""
    import ifcopenshell

    model = ifcopenshell.file(schema="IFC4")
    wall = model.create_entity("IfcWall", Name="Unsupported wall")
    wall.GlobalId = ifcopenshell.guid.new()
    wall.Representation = model.create_entity(
        "IfcProductDefinitionShape",
        Representations=[],
    )

    class _FailingSettings:
        """Provide the settings API used before the synthetic geometry failure."""

        USE_WORLD_COORDS = "use-world-coords"

        def set(self, _name, _value):
            """Accept a setting so the test reaches tessellation."""

    class _FailingGeom:
        """Raise a deterministic backend failure for provenance verification."""

        settings = _FailingSettings

        @staticmethod
        def create_shape(_settings, _entity):
            """Simulate an unsupported IFC representation backend failure."""
            raise RuntimeError("unsupported representation fixture")

    class _FailingIfcModule:
        """Expose only the geometry namespace used by the adapter."""

        geom = _FailingGeom

    scene = load_ifc_neutral_scene(model, ifc_module=_FailingIfcModule)
    uncertainty = scene.source_objects[0].uncertainties[0]

    assert uncertainty.code == "missing_geometry"
    assert uncertainty.details["failure_type"] == "RuntimeError"
    assert uncertainty.details["failure_message"] == "unsupported representation fixture"


def test_adapter_audits_explicit_affordance_without_geometry(tmp_path):
    """An authored affordance marker without geometry remains auditable but unusable."""
    import ifcopenshell

    path = tmp_path / "empty-affordance.ifc"
    model = ifcopenshell.file(schema="IFC4")
    zone = model.create_entity("IfcSpatialZone", Name="Chair clearance")
    zone.GlobalId = ifcopenshell.guid.new()
    zone.PredefinedType = "USERDEFINED"
    zone.ObjectType = "OM_AFFORDANCE_ZONE"
    wall = model.create_entity("IfcWall", Name="Invalid referenced wall")
    wall.GlobalId = ifcopenshell.guid.new()
    model.create_entity(
        "IfcRelReferencedInSpatialStructure",
        RelatingStructure=zone,
        RelatedElements=[wall],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    zone_object = next(
        record for record in scene.source_objects if record.source_id == zone.GlobalId
    )

    assert scene.authored_affordances == ()
    assert zone_object.uncertainties[0].code == "missing_geometry"
    assert "unusable_authored_affordance" in {
        record.code for record in scene.uncertainties
    }
    assert "invalid_affordance_furniture_reference" in {
        record.code for record in scene.uncertainties
    }
    assert "missing_affordance_furniture_reference" in {
        record.code for record in scene.uncertainties
    }


def test_adapter_audits_authored_affordance_without_furniture_reference(tmp_path):
    """A geometric authored affordance without furniture linkage stays uncertain."""
    import ifcopenshell
    from .fixtures.ifc4_description_fixture import write_ifc4_description_fixture

    path = tmp_path / "unlinked-affordance.ifc"
    ids = write_ifc4_description_fixture(path)
    model = ifcopenshell.open(str(path))
    zone = model.by_guid(ids["affordance"])
    for relation in tuple(zone.ReferencesElements):
        model.remove(relation)

    scene = load_ifc_neutral_scene(model)
    affordance = scene.authored_affordances[0]

    assert affordance.source_furniture_refs == ()
    assert "missing_affordance_furniture_reference" in {
        item.code for item in affordance.uncertainties
    }


def test_adapter_does_not_infer_affordance_purpose_from_zone_name(tmp_path):
    """A display name cannot replace an explicitly authored affordance purpose."""
    import ifcopenshell
    from .fixtures.ifc4_description_fixture import write_ifc4_description_fixture

    path = tmp_path / "purpose-less-affordance.ifc"
    ids = write_ifc4_description_fixture(path)
    model = ifcopenshell.open(str(path))
    zone = model.by_guid(ids["affordance"])
    for relation in tuple(zone.IsDefinedBy):
        definition = relation.RelatingPropertyDefinition
        if getattr(definition, "Name", None) == "OM_Affordance":
            model.remove(relation)
    for relation in tuple(zone.ReferencesElements):
        model.remove(relation)
    model.create_entity(
        "IfcRelReferencedInSpatialStructure",
        RelatingStructure=zone,
        RelatedElements=[model.by_guid(ids["wall"])],
    )

    scene = load_ifc_neutral_scene(model)

    assert scene.authored_affordances == ()
    assert "missing_affordance_purpose" in {
        item.code for item in scene.uncertainties
    }
    assert "invalid_affordance_furniture_reference" in {
        item.code for item in scene.uncertainties
    }
    assert "missing_affordance_furniture_reference" in {
        item.code for item in scene.uncertainties
    }


def test_adapter_distinguishes_selected_domain_from_usable_domain_geometry(tmp_path):
    """An explicit geometry-free room is selected but not advertised as usable domain."""
    import ifcopenshell

    path = tmp_path / "empty-domain.ifc"
    model = ifcopenshell.file(schema="IFC4")
    room = model.create_entity("IfcSpace", Name="Room")
    room.GlobalId = ifcopenshell.guid.new()
    model.write(str(path))

    scene = load_ifc_neutral_scene(path, analysis_domain_source_id=room.GlobalId)

    assert scene.analysis_domain is not None
    assert scene.analysis_domain.geometry_refs == ()
    assert scene.context.capability_flags["analysis_domain"] is False


def test_adapter_distinguishes_grid_entity_from_usable_grid_axes(tmp_path):
    """An IFC grid with no valid axes remains authored but unavailable to analysis."""
    import ifcopenshell

    path = tmp_path / "empty-grid.ifc"
    model = ifcopenshell.file(schema="IFC4")
    grid = model.create_entity("IfcGrid", Name="Empty grid")
    grid.GlobalId = ifcopenshell.guid.new()
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert len(scene.authored_grids) == 1
    assert scene.authored_grid_axes == ()
    assert scene.context.capability_flags["authored_grid"] is False
    assert "unusable_authored_grid" in {record.code for record in scene.uncertainties}


def test_adapter_preserves_native_ifc_material_assignment_facts(tmp_path):
    """A serialized IFC4 material assignment remains a factual object reference."""
    import ifcopenshell

    path = tmp_path / "material.ifc"
    model = ifcopenshell.file(schema="IFC4")
    furniture = model.create_entity("IfcFurniture", Name="Chair")
    furniture.GlobalId = ifcopenshell.guid.new()
    material = model.create_entity("IfcMaterial", Name="oak veneer")
    model.create_entity(
        "IfcRelAssociatesMaterial",
        RelatingMaterial=material,
        RelatedObjects=[furniture],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.materials[0].source_id == f"ifc-step:{material.id()}"
    assert scene.materials[0].identity == "oak veneer"
    assert scene.source_objects[0].material_refs == (
        f"ifc-material:ifc-step:{material.id()}",
    )
    assert scene.materials[0].visible_transmittance is None
    assert scene.materials[0].uncertainties[0].code == (
        "missing_material_optical_evidence"
    )


def test_adapter_expands_ifc_material_layer_set_usage_to_constituent_materials(
    tmp_path,
):
    """A material usage association links each constituent material to the object."""
    import ifcopenshell

    path = tmp_path / "layered-material.ifc"
    model = ifcopenshell.file(schema="IFC4")
    wall = model.create_entity("IfcWall", Name="Layered wall")
    wall.GlobalId = ifcopenshell.guid.new()
    gypsum = model.create_entity("IfcMaterial", Name="gypsum")
    insulation = model.create_entity("IfcMaterial", Name="insulation")
    layer_set = model.create_entity(
        "IfcMaterialLayerSet",
        MaterialLayers=[
            model.create_entity(
                "IfcMaterialLayer",
                Material=gypsum,
                LayerThickness=0.02,
                IsVentilated=False,
            ),
            model.create_entity(
                "IfcMaterialLayer",
                Material=insulation,
                LayerThickness=0.1,
                IsVentilated=False,
            ),
        ],
        LayerSetName="wall build-up",
    )
    layer_usage = model.create_entity(
        "IfcMaterialLayerSetUsage",
        ForLayerSet=layer_set,
        LayerSetDirection="AXIS2",
        DirectionSense="POSITIVE",
        OffsetFromReferenceLine=0.0,
    )
    model.create_entity(
        "IfcRelAssociatesMaterial",
        RelatingMaterial=layer_usage,
        RelatedObjects=[wall],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    expected_refs = {
        f"ifc-material:ifc-step:{gypsum.id()}",
        f"ifc-material:ifc-step:{insulation.id()}",
    }
    assert {item.id for item in scene.materials} == expected_refs
    wall_record = next(item for item in scene.source_objects if item.source_id == wall.GlobalId)
    assert set(wall_record.material_refs) == expected_refs


def test_adapter_links_type_inherited_material_to_furniture_occurrence(tmp_path):
    """A type-level material remains discoverable from its furniture occurrence."""
    import ifcopenshell

    path = tmp_path / "type-material.ifc"
    model = ifcopenshell.file(schema="IFC4")
    furniture = model.create_entity("IfcFurniture", Name="Chair")
    furniture.GlobalId = ifcopenshell.guid.new()
    furniture_type = model.create_entity("IfcFurnitureType", Name="Chair type")
    furniture_type.GlobalId = ifcopenshell.guid.new()
    model.create_entity(
        "IfcRelDefinesByType",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[furniture],
        RelatingType=furniture_type,
    )
    material = model.create_entity("IfcMaterial", Name="birch")
    model.create_entity(
        "IfcRelAssociatesMaterial",
        GlobalId=ifcopenshell.guid.new(),
        RelatingMaterial=material,
        RelatedObjects=[furniture_type],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    record = next(item for item in scene.source_objects if item.source_id == furniture.GlobalId)

    assert record.material_refs == (f"ifc-material:ifc-step:{material.id()}",)
    assert scene.materials[0].identity == "birch"


def test_adapter_separates_material_optical_property_from_viewport_style(tmp_path):
    """Measured transmittance and viewport transparency remain separate IFC facts."""
    import ifcopenshell

    path = tmp_path / "optical-material.ifc"
    model = ifcopenshell.file(schema="IFC4")
    furniture = model.create_entity("IfcFurniture", Name="Partition")
    furniture.GlobalId = ifcopenshell.guid.new()
    material = model.create_entity("IfcMaterial", Name="clear panel")
    visible_transmittance = model.create_entity(
        "IfcPropertySingleValue",
        Name="VisibleTransmittance",
        NominalValue=model.create_entity("IfcNormalisedRatioMeasure", 0.82),
    )
    model.create_entity(
        "IfcMaterialProperties",
        Name="Pset_MaterialOptical",
        Properties=[visible_transmittance],
        Material=material,
    )
    colour = model.create_entity("IfcColourRgb", Red=0.8, Green=0.9, Blue=1.0)
    rendering = model.create_entity(
        "IfcSurfaceStyleRendering",
        SurfaceColour=colour,
        Transparency=0.25,
        ReflectanceMethod="NOTDEFINED",
    )
    surface_style = model.create_entity(
        "IfcSurfaceStyle",
        Name="Viewport glass",
        Side="BOTH",
        Styles=[rendering],
    )
    styled_item = model.create_entity("IfcStyledItem", Styles=[surface_style])
    styled_representation = model.create_entity(
        "IfcStyledRepresentation",
        RepresentationIdentifier="Style",
        RepresentationType="Material",
        Items=[styled_item],
    )
    model.create_entity(
        "IfcMaterialDefinitionRepresentation",
        Representations=[styled_representation],
        RepresentedMaterial=material,
    )
    model.create_entity(
        "IfcRelAssociatesMaterial",
        RelatingMaterial=material,
        RelatedObjects=[furniture],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.materials[0].visible_transmittance == pytest.approx(0.82)
    assert scene.materials[0].viewport_transparency == pytest.approx(0.25)
    assert scene.context.capability_flags["optical"] is True


@pytest.mark.parametrize(
    ("ifc_value_type", "invalid_value"),
    (
        ("IfcReal", -0.1),
        ("IfcReal", 1.1),
        ("IfcReal", 0.5),
        ("IfcLabel", "0.5"),
    ),
)
def test_adapter_distinguishes_invalid_material_optical_value_from_missing(
    tmp_path,
    ifc_value_type,
    invalid_value,
):
    """An authored out-of-range optical value is invalid rather than absent."""
    import ifcopenshell

    path = tmp_path / f"invalid-optical-{invalid_value}.ifc"
    model = ifcopenshell.file(schema="IFC4")
    furniture = model.create_entity("IfcFurniture", Name="Partition")
    furniture.GlobalId = ifcopenshell.guid.new()
    material = model.create_entity("IfcMaterial", Name="invalid optical panel")
    prop = model.create_entity(
        "IfcPropertySingleValue",
        Name="VisibleTransmittance",
        NominalValue=model.create_entity(ifc_value_type, invalid_value),
    )
    model.create_entity(
        "IfcMaterialProperties",
        Name="Pset_MaterialOptical",
        Properties=[prop],
        Material=material,
    )
    model.create_entity(
        "IfcRelAssociatesMaterial",
        RelatingMaterial=material,
        RelatedObjects=[furniture],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    record = scene.materials[0]

    assert record.visible_transmittance is None
    uncertainty = next(
        item
        for item in record.uncertainties
        if item.code == "invalid_material_optical_evidence"
    )
    if isinstance(invalid_value, str):
        assert uncertainty.details["raw_value"] == invalid_value
    else:
        assert uncertainty.details["raw_value"] == pytest.approx(invalid_value)
    assert "missing_material_optical_evidence" not in {
        item.code for item in record.uncertainties
    }


def test_adapter_preserves_native_ifc_covering_as_surface_fact(tmp_path):
    """An IFC4 floor covering enters as surface evidence, not physical mass."""
    import ifcopenshell

    path = tmp_path / "covering.ifc"
    model = ifcopenshell.file(schema="IFC4")
    covering = model.create_entity("IfcCovering", Name="Blue carpet")
    covering.GlobalId = ifcopenshell.guid.new()
    covering.PredefinedType = "FLOORING"
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.surfaces[0].source_id == covering.GlobalId
    assert scene.surfaces[0].identity == "IfcCovering:FLOORING"
    assert scene.surfaces[0].geometry_refs == ()
    assert scene.source_objects[0].surface_refs == (f"ifc-surface:{covering.GlobalId}",)


def test_adapter_maps_ifc_covering_host_and_reverse_surface_reference(tmp_path):
    """IfcRelCoversBldgElements links a covering surface to its building host."""
    import ifcopenshell

    path = tmp_path / "covering-host.ifc"
    model = ifcopenshell.file(schema="IFC4")
    slab = model.create_entity("IfcSlab", Name="Floor")
    slab.GlobalId = ifcopenshell.guid.new()
    covering = model.create_entity("IfcCovering", Name="Carpet")
    covering.GlobalId = ifcopenshell.guid.new()
    covering.PredefinedType = "FLOORING"
    model.create_entity(
        "IfcRelCoversBldgElements",
        GlobalId=ifcopenshell.guid.new(),
        RelatingBuildingElement=slab,
        RelatedCoverings=[covering],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    surface = scene.surfaces[0]
    slab_record = next(item for item in scene.source_objects if item.source_id == slab.GlobalId)

    assert surface.host_refs == (f"ifc-object:{slab.GlobalId}",)
    assert slab_record.surface_refs == (f"ifc-surface:{covering.GlobalId}",)


def test_adapter_links_opening_and_surface_transport_geometry(tmp_path):
    """Geometric openings and surface products reuse their extracted transport meshes."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import add_mesh_representation, assign_representation
    from ifcopenshell.api.root import create_entity

    path = tmp_path / "geometric-facts.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    model_context = add_context(model, context_type="Model")
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    wall = create_entity(model, ifc_class="IfcWall", name="Wall")
    opening = create_entity(model, ifc_class="IfcOpeningElement", name="Opening")
    covering = create_entity(model, ifc_class="IfcCovering", name="Carpet")
    covering.PredefinedType = "FLOORING"
    surface = create_entity(model, ifc_class="IfcSurfaceFeature", name="Paint field")
    surface.PredefinedType = "USERDEFINED"
    surface.ObjectType = "OM_COLOR_FIELD"
    model.create_entity(
        "IfcRelVoidsElement",
        RelatingBuildingElement=wall,
        RelatedOpeningElement=opening,
    )
    model.create_entity(
        "IfcRelAssignsToProduct",
        RelatingProduct=wall,
        RelatedObjects=[surface],
    )
    for product, z_value in ((opening, 0.0), (covering, 0.01), (surface, 0.02)):
        # Separate representations prove each fact references its own source geometry.
        representation = add_mesh_representation(
            model,
            context=body_context,
            vertices=[
                [
                    (0.0, 0.0, z_value),
                    (1.0, 0.0, z_value),
                    (0.0, 1.0, z_value),
                ]
            ],
            faces=[[[0, 1, 2]]],
        )
        assign_representation(model, product=product, representation=representation)
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    opening_record = next(item for item in scene.openings if item.source_id == opening.GlobalId)
    surface_by_source = {item.source_id: item for item in scene.surfaces}

    assert opening_record.geometry_refs == (f"ifc-mesh:{opening.GlobalId}",)
    assert opening_record.uncertainties == ()
    assert surface_by_source[covering.GlobalId].geometry_refs == (
        f"ifc-mesh:{covering.GlobalId}",
    )
    assert surface_by_source[surface.GlobalId].geometry_refs == (
        f"ifc-mesh:{surface.GlobalId}",
    )
    assert surface_by_source[surface.GlobalId].host_refs == (
        f"ifc-object:{wall.GlobalId}",
    )
    wall_record = next(item for item in scene.source_objects if item.source_id == wall.GlobalId)
    assert f"ifc-surface:{surface.GlobalId}" in wall_record.surface_refs
    assert surface_by_source[surface.GlobalId].identity == (
        "IfcSurfaceFeature:OM_COLOR_FIELD"
    )


def test_adapter_inherits_type_level_om_surface_facts(tmp_path):
    """A surface occurrence inherits OM_Surface defaults from its IFC type."""
    import ifcopenshell

    path = tmp_path / "type-surface-facts.ifc"
    model = ifcopenshell.file(schema="IFC4")
    surface = model.create_entity("IfcCovering", Name="Raised finish")
    surface.GlobalId = ifcopenshell.guid.new()
    surface.PredefinedType = "FLOORING"
    surface_type = model.create_entity("IfcCoveringType", Name="Finish type")
    surface_type.GlobalId = ifcopenshell.guid.new()
    color = model.create_entity(
        "IfcPropertySingleValue",
        Name="Color",
        NominalValue=model.create_entity("IfcLabel", "#224466"),
    )
    pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Surface",
        HasProperties=[color],
    )
    surface_type.HasPropertySets = [pset]
    model.create_entity(
        "IfcRelDefinesByType",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[surface],
        RelatingType=surface_type,
    )
    model.write(str(path))

    record = load_ifc_neutral_scene(path).surfaces[0]

    assert record.color == "#224466"
    assert record.provenance["property_sources"]["Color"] == {
        "scope": "type",
        "owner_source_id": surface_type.GlobalId,
        "property_set_id": pset.GlobalId,
        "property_class": "IfcPropertySingleValue",
    }


def test_adapter_does_not_fall_back_after_invalid_occurrence_surface_override(
    tmp_path,
):
    """An unusable occurrence value blocks the same inherited surface default."""
    import ifcopenshell

    path = tmp_path / "invalid-occurrence-surface-override.ifc"
    model = ifcopenshell.file(schema="IFC4")
    surface = model.create_entity("IfcCovering", Name="Raised finish")
    surface.GlobalId = ifcopenshell.guid.new()
    surface.PredefinedType = "FLOORING"
    surface_type = model.create_entity("IfcCoveringType", Name="Finish type")
    surface_type.GlobalId = ifcopenshell.guid.new()
    type_color = model.create_entity(
        "IfcPropertySingleValue",
        Name="Color",
        NominalValue=model.create_entity("IfcLabel", "#224466"),
    )
    type_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Surface",
        HasProperties=[type_color],
    )
    surface_type.HasPropertySets = [type_pset]
    model.create_entity(
        "IfcRelDefinesByType",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[surface],
        RelatingType=surface_type,
    )
    invalid_color = model.create_entity(
        "IfcPropertyBoundedValue",
        Name="Color",
        UpperBoundValue=model.create_entity("IfcLabel", "#ffffff"),
        LowerBoundValue=model.create_entity("IfcLabel", "#000000"),
    )
    occurrence_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Surface",
        HasProperties=[invalid_color],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatingPropertyDefinition=occurrence_pset,
        RelatedObjects=[surface],
    )
    model.write(str(path))

    record = load_ifc_neutral_scene(path).surfaces[0]

    assert record.color is None
    unsupported = next(
        item
        for item in record.uncertainties
        if item.code == "unsupported_om_surface_property"
    )
    assert unsupported.details["source_scope"] == "occurrence"
    assert unsupported.details["property_set_id"] == occurrence_pset.GlobalId


def test_adapter_maps_explicit_om_surface_facts_and_audits_unsupported_values(
    tmp_path,
):
    """OM_Surface facts remain factual fields and unsupported forms remain visible."""
    import ifcopenshell

    path = tmp_path / "om-surface.ifc"
    model = ifcopenshell.file(schema="IFC4")
    surface = model.create_entity("IfcSurfaceFeature", Name="Finish field")
    surface.GlobalId = ifcopenshell.guid.new()
    surface.PredefinedType = "USERDEFINED"
    surface.ObjectType = "OM_FINISH_FIELD"
    properties = [
        model.create_entity(
            "IfcPropertySingleValue",
            Name=name,
            NominalValue=model.create_entity("IfcLabel", value),
        )
        for name, value in (
            ("Color", "#335577"),
            ("Finish", "matte"),
            ("Texture", "woven"),
            ("Slope", "1:50"),
        )
    ]
    properties.append(
        model.create_entity(
            "IfcPropertyBoundedValue",
            Name="Elevation",
            UpperBoundValue=model.create_entity("IfcLengthMeasure", 0.03),
            LowerBoundValue=model.create_entity("IfcLengthMeasure", 0.01),
        )
    )
    pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Surface",
        HasProperties=properties,
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        RelatingPropertyDefinition=pset,
        RelatedObjects=[surface],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    record = scene.surfaces[0]

    assert record.color == "#335577"
    assert record.finish == "matte"
    assert record.texture == "woven"
    assert record.slope == "1:50"
    assert record.elevation is None
    unsupported = next(
        item for item in record.uncertainties if item.code == "unsupported_om_surface_property"
    )
    assert unsupported.details["property_name"] == "Elevation"
    assert unsupported.details["property_class"] == "IfcPropertyBoundedValue"


def test_adapter_normalizes_om_surface_elevation_to_analysis_metres(tmp_path):
    """An IFC length-valued surface elevation follows the project unit scale."""
    import ifcopenshell
    from ifcopenshell.api.root import create_entity
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    path = tmp_path / "surface-elevation-mm.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    length_unit = add_si_unit(model, unit_type="LENGTHUNIT", prefix="MILLI")
    assign_unit(model, units=[length_unit])
    surface = create_entity(model, ifc_class="IfcSurfaceFeature", name="Raised finish")
    surface.PredefinedType = "USERDEFINED"
    surface.ObjectType = "OM_FINISH_FIELD"
    elevation = model.create_entity(
        "IfcPropertySingleValue",
        Name="Elevation",
        NominalValue=model.create_entity("IfcLengthMeasure", 30.0),
    )
    pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Surface",
        HasProperties=[elevation],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatingPropertyDefinition=pset,
        RelatedObjects=[surface],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.surfaces[0].elevation == pytest.approx(0.03)
    assert scene.surfaces[0].provenance["elevation_unit"] == "m"
    source_record = next(
        item for item in scene.source_objects if item.source_id == surface.GlobalId
    )
    assert "OM_Surface" not in source_record.factual_properties


def test_adapter_honors_property_level_unit_for_om_surface_elevation(tmp_path):
    """An explicit property unit overrides the project unit for surface elevation."""
    import ifcopenshell
    from ifcopenshell.api.root import create_entity
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    path = tmp_path / "surface-elevation-property-unit.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    metre = add_si_unit(model, unit_type="LENGTHUNIT")
    assign_unit(model, units=[metre])
    centimetre = model.create_entity(
        "IfcSIUnit",
        UnitType="LENGTHUNIT",
        Prefix="CENTI",
        Name="METRE",
    )
    surface = create_entity(model, ifc_class="IfcSurfaceFeature", name="Raised finish")
    surface.PredefinedType = "USERDEFINED"
    surface.ObjectType = "OM_FINISH_FIELD"
    elevation = model.create_entity(
        "IfcPropertySingleValue",
        Name="Elevation",
        NominalValue=model.create_entity("IfcLengthMeasure", 30.0),
        Unit=centimetre,
    )
    pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Surface",
        HasProperties=[elevation],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatingPropertyDefinition=pset,
        RelatedObjects=[surface],
    )
    model.write(str(path))

    record = load_ifc_neutral_scene(path).surfaces[0]

    assert record.elevation == pytest.approx(0.3)
    assert record.provenance["elevation_scale_source"] == "property_unit"
    assert record.provenance["elevation_scale_to_metres"] == pytest.approx(0.01)


def test_adapter_rejects_non_length_property_unit_for_om_surface_elevation(tmp_path):
    """A non-length property unit cannot be treated as a metre conversion."""
    import ifcopenshell
    from ifcopenshell.api.root import create_entity
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    path = tmp_path / "surface-elevation-time-unit.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    metre = add_si_unit(model, unit_type="LENGTHUNIT")
    assign_unit(model, units=[metre])
    surface = create_entity(model, ifc_class="IfcSurfaceFeature", name="Raised finish")
    surface.PredefinedType = "USERDEFINED"
    surface.ObjectType = "OM_FINISH_FIELD"
    time_unit = model.create_entity(
        "IfcSIUnit",
        UnitType="TIMEUNIT",
        Name="SECOND",
    )
    elevation = model.create_entity(
        "IfcPropertySingleValue",
        Name="Elevation",
        NominalValue=model.create_entity("IfcLengthMeasure", 30.0),
        Unit=time_unit,
    )
    pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Surface",
        HasProperties=[elevation],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatingPropertyDefinition=pset,
        RelatedObjects=[surface],
    )
    model.write(str(path))

    record = load_ifc_neutral_scene(path).surfaces[0]

    assert record.elevation is None
    unsupported = next(
        item
        for item in record.uncertainties
        if item.code == "unsupported_om_surface_property"
    )
    assert unsupported.details["property_name"] == "Elevation"


def test_adapter_preserves_explicit_ifc_affordance_zone_facts(tmp_path):
    """An explicitly marked IFC4 spatial zone remains authored affordance evidence."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import add_mesh_representation, assign_representation
    from ifcopenshell.api.root import create_entity

    path = tmp_path / "affordance.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    model_context = add_context(model, context_type="Model")
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    furniture = model.create_entity("IfcFurniture", Name="Chair")
    furniture.GlobalId = ifcopenshell.guid.new()
    wall = model.create_entity("IfcWall", Name="Nearby wall")
    wall.GlobalId = ifcopenshell.guid.new()
    zone = model.create_entity("IfcSpatialZone", Name="Seat clearance")
    zone.GlobalId = ifcopenshell.guid.new()
    zone.PredefinedType = "USERDEFINED"
    zone.ObjectType = "OM_AFFORDANCE_ZONE"
    representation = add_mesh_representation(
        model,
        context=body_context,
        vertices=[
            [
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.2),
            ]
        ],
        faces=[[[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]]],
        unit_scale=1.0,
    )
    assign_representation(model, product=zone, representation=representation)
    model.create_entity(
        "IfcRelReferencedInSpatialStructure",
        RelatingStructure=zone,
        RelatedElements=[furniture, wall],
    )
    purpose_property = model.create_entity(
        "IfcPropertySingleValue",
        Name="Purpose",
        NominalValue=model.create_entity("IfcLabel", "chair_pull_back"),
    )
    purpose_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Affordance",
        HasProperties=[purpose_property],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        RelatingPropertyDefinition=purpose_pset,
        RelatedObjects=[zone],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)

    assert scene.authored_affordances[0].id == f"ifc-affordance:{zone.GlobalId}"
    assert scene.authored_affordances[0].source_id == zone.GlobalId
    assert scene.authored_affordances[0].purpose == "chair_pull_back"
    assert scene.authored_affordances[0].geometry_refs == (
        f"ifc-mesh:{zone.GlobalId}",
    )
    assert scene.authored_affordances[0].vertical_extent == pytest.approx((0.0, 1.2))
    assert scene.authored_affordances[0].source_furniture_refs == (
        f"ifc-object:{furniture.GlobalId}",
    )
    invalid_reference = next(
        item
        for item in scene.authored_affordances[0].uncertainties
        if item.code == "invalid_affordance_furniture_reference"
    )
    assert invalid_reference.source_refs == (wall.GlobalId, zone.GlobalId)
    assert invalid_reference.details["source_class"] == "IfcWall"
    assert scene.context.capability_flags["authored_affordance"] is True


def test_adapter_requires_complete_ifc_affordance_marker(tmp_path):
    """ObjectType alone cannot promote an ordinary spatial zone to affordance input."""
    import ifcopenshell

    path = tmp_path / "incomplete-affordance-marker.ifc"
    model = ifcopenshell.file(schema="IFC4")
    zone = model.create_entity("IfcSpatialZone", Name="Ordinary zone")
    zone.GlobalId = ifcopenshell.guid.new()
    zone.PredefinedType = "NOTDEFINED"
    zone.ObjectType = "OM_AFFORDANCE_ZONE"
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    zone_object = next(item for item in scene.source_objects if item.source_id == zone.GlobalId)

    assert scene.authored_affordances == ()
    assert zone_object.source_role == "spatial_zone"


def test_adapter_maps_explicit_domain_containment_type_and_om_facts(tmp_path):
    """Explicit IFC context and OM factual properties remain auditable source facts."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import add_mesh_representation, assign_representation
    from ifcopenshell.api.root import create_entity

    path = tmp_path / "context.ifc"
    model = ifcopenshell.file(schema="IFC4")
    create_entity(model, ifc_class="IfcProject", name="Project")
    model_context = add_context(model, context_type="Model")
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    storey = create_entity(model, ifc_class="IfcBuildingStorey", name="Level 1")
    room = create_entity(model, ifc_class="IfcSpace", name="Analysis room")
    furniture = create_entity(model, ifc_class="IfcFurniture", name="Desk")
    furniture_type = create_entity(model, ifc_class="IfcFurnitureType", name="Desk type")
    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        RelatingStructure=storey,
        RelatedElements=[furniture],
    )
    model.create_entity(
        "IfcRelAggregates",
        RelatingObject=storey,
        RelatedObjects=[room],
    )
    model.create_entity(
        "IfcRelDefinesByType",
        RelatingType=furniture_type,
        RelatedObjects=[furniture],
    )
    role_property = model.create_entity(
        "IfcPropertySingleValue",
        Name="Role",
        NominalValue=model.create_entity("IfcLabel", "workstation"),
    )
    property_set = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Layout",
        HasProperties=[role_property],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        RelatingPropertyDefinition=property_set,
        RelatedObjects=[furniture],
    )
    room_representation = add_mesh_representation(
        model,
        context=body_context,
        vertices=[[(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (0.0, 4.0, 0.0)]],
        faces=[[[0, 1, 2]]],
    )
    assign_representation(model, product=room, representation=room_representation)
    model.write(str(path))

    scene = load_ifc_neutral_scene(path, analysis_domain_source_id=room.GlobalId)
    furniture_record = next(
        record for record in scene.source_objects if record.source_id == furniture.GlobalId
    )

    assert scene.analysis_domain is not None
    assert scene.analysis_domain.source_id == room.GlobalId
    assert scene.analysis_domain.geometry_refs == (f"ifc-mesh:{room.GlobalId}",)
    assert scene.context.capability_flags["analysis_domain"] is True
    assert furniture_record.container_refs == (f"ifc-object:{storey.GlobalId}",)
    assert furniture_record.level_ref == f"ifc-object:{storey.GlobalId}"
    assert furniture_record.type_ref == f"ifc-type:{furniture_type.GlobalId}"
    assert furniture_record.factual_properties == {
        "OM_Layout": {"Role": "workstation"}
    }


def test_adapter_quarantines_forbidden_om_analysis_facts(tmp_path):
    """OM metadata cannot smuggle inferred results weights or scores into source facts."""
    import ifcopenshell

    path = tmp_path / "forbidden-om-analysis.ifc"
    model = ifcopenshell.file(schema="IFC4")
    furniture = model.create_entity("IfcFurniture", Name="Chair")
    furniture.GlobalId = ifcopenshell.guid.new()
    allowed_role = model.create_entity(
        "IfcPropertySingleValue",
        Name="Role",
        NominalValue=model.create_entity("IfcLabel", "workseat"),
    )
    forbidden_properties = [
        model.create_entity(
            "IfcPropertySingleValue",
            Name=name,
            NominalValue=model.create_entity("IfcReal", 0.9),
        )
        for name in ("boundary_strength", "trend_score", "perceptual_weight")
    ]
    allowed_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Layout",
        HasProperties=[allowed_role],
    )
    forbidden_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Analysis",
        HasProperties=forbidden_properties,
    )
    unknown_metric = model.create_entity(
        "IfcPropertySingleValue",
        Name="overall_metric",
        NominalValue=model.create_entity("IfcReal", 0.9),
    )
    unknown_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="OM_Results",
        HasProperties=[unknown_metric],
    )
    for pset in (allowed_pset, forbidden_pset, unknown_pset):
        model.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            RelatingPropertyDefinition=pset,
            RelatedObjects=[furniture],
        )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    record = scene.source_objects[0]
    serialized = json.dumps(scene.to_dict(), sort_keys=True)

    assert record.factual_properties["OM_Layout"] == {"Role": "workseat"}
    assert "OM_Analysis" not in record.factual_properties
    assert "OM_Results" not in record.factual_properties
    assert '"boundary_strength": 0.9' not in serialized
    assert '"trend_score": 0.9' not in serialized
    assert '"perceptual_weight": 0.9' not in serialized
    rejected = [
        item
        for item in record.uncertainties
        if item.code == "forbidden_om_analysis_fact"
    ]
    assert {item.details["property_name"] for item in rejected} == {
        "boundary_strength",
        "trend_score",
        "perceptual_weight",
    }
    unregistered = next(
        item
        for item in record.uncertainties
        if item.code == "unregistered_om_factual_property"
    )
    assert unregistered.details == {
        "adapter": "ifc4-bonsai-adapter/0.1.0",
        "property_set_name": "OM_Results",
        "property_name": "overall_metric",
    }


def test_adapter_inherits_registered_om_facts_with_occurrence_override(tmp_path):
    """Registered type facts flow to occurrences and occurrence values take precedence."""
    import ifcopenshell

    path = tmp_path / "typed-om-facts.ifc"
    model = ifcopenshell.file(schema="IFC4")
    furniture_type = model.create_entity("IfcFurnitureType", Name="Chair type")
    furniture_type.GlobalId = ifcopenshell.guid.new()
    inherited = model.create_entity("IfcFurniture", Name="Inherited chair")
    inherited.GlobalId = ifcopenshell.guid.new()
    overridden = model.create_entity("IfcFurniture", Name="Overridden chair")
    overridden.GlobalId = ifcopenshell.guid.new()
    model.create_entity(
        "IfcRelDefinesByType",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[inherited, overridden],
        RelatingType=furniture_type,
    )

    def role_pset(value):
        """Create one registered OM_Layout role property set."""
        role = model.create_entity(
            "IfcPropertySingleValue",
            Name="Role",
            NominalValue=model.create_entity("IfcLabel", value),
        )
        return model.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            Name="OM_Layout",
            HasProperties=[role],
        )

    furniture_type.HasPropertySets = [role_pset("type_role")]
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatingPropertyDefinition=role_pset("occurrence_role"),
        RelatedObjects=[overridden],
    )
    model.write(str(path))

    scene = load_ifc_neutral_scene(path)
    facts = {item.source_id: item.factual_properties for item in scene.source_objects}

    assert facts[inherited.GlobalId]["OM_Layout"]["Role"] == "type_role"
    assert facts[overridden.GlobalId]["OM_Layout"]["Role"] == "occurrence_role"


def test_adapter_uses_injected_ifc4_facts_without_mutation_or_analysis():
    """Normalized IFC facts become neutral records with stable source provenance only."""
    source = _FakeIfcFile()
    before = source.snapshot()

    scene = load_ifc_neutral_scene(source)

    assert source.snapshot() == before
    assert scene.context.input_mode == "ifc"
    assert scene.context.source_schema == "IFC4"
    assert scene.source_objects[0].source_id == "furniture-001"
    assert scene.source_objects[0].source_class == "IfcFurniture"
    assert scene.geometries[0].source_representation_id == "furniture-001"
    assert scene.source_objects[0].provenance["method"] == "ifc4_read_only_extraction"
    assert "boundary_strength" not in json.dumps(scene.to_dict())
    assert "inferred_regions" not in json.dumps(scene.to_dict())


def test_adapter_retains_source_object_when_geometry_is_unavailable():
    """A partial IFC extraction records missing geometry without discarding its source."""
    source = _FakeIfcFile()
    source.payload["objects"] = (
        {"global_id": "wall-001", "ifc_class": "IfcWall"},
    )

    scene = load_ifc_neutral_scene(source)

    assert scene.source_objects[0].source_id == "wall-001"
    assert scene.source_objects[0].geometry_refs == ()
    assert scene.source_objects[0].uncertainties[0].code == "missing_geometry"


@pytest.mark.parametrize(
    "triangles",
    (
        ((0, 1),),
        ((0, 1, -1),),
        ((0, 1, 3),),
    ),
)
def test_adapter_rejects_malformed_transport_triangles_at_its_boundary(triangles):
    """Malformed normalized mesh facts fail before reaching later geometry consumers."""
    source = _FakeIfcFile()
    source.payload["objects"][0]["geometry"]["triangles"] = triangles

    with pytest.raises(ValueError, match="triangle"):
        load_ifc_neutral_scene(source)


@pytest.mark.parametrize("triangles", (((0, 1, 0.9),), ((0, 1, True),)))
def test_adapter_rejects_non_integer_triangle_indices_without_coercion(triangles):
    """Transport indices must not be silently truncated or coerced."""
    source = _FakeIfcFile()
    source.payload["objects"][0]["geometry"]["triangles"] = triangles

    with pytest.raises(ValueError, match="triangle"):
        load_ifc_neutral_scene(source)


@pytest.mark.parametrize("geometry", ({}, {"vertices": (), "triangles": ()}))
def test_adapter_marks_empty_transport_geometry_as_missing(geometry):
    """Empty transport extraction remains an explicit unavailable capability."""
    source = _FakeIfcFile()
    source.payload["objects"] = (
        {"global_id": "empty-geometry", "ifc_class": "IfcWall", "geometry": geometry},
    )

    scene = load_ifc_neutral_scene(source)

    assert scene.source_objects[0].geometry_refs == ()
    assert scene.source_objects[0].uncertainties[0].code == "missing_geometry"


@pytest.mark.parametrize("schema", ("IFC2X3", "IFC4X3"))
def test_adapter_rejects_non_ifc4_schemas_without_assuming_cross_schema_relations(schema):
    """IFC4X3-only or legacy relationships never enter the IFC4 adapter path."""
    source = _FakeIfcFile()
    source.schema = schema

    with pytest.raises(ValueError, match="IFC4"):
        load_ifc_neutral_scene(source)
