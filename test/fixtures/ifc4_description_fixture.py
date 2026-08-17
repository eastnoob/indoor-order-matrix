"""Deterministic IFC4 factual fixture used by the BIM description pipeline."""

from __future__ import annotations

from pathlib import Path
import uuid


_GUID_NAMESPACE = uuid.UUID("ddb53d57-6b7d-42bc-8d4c-77c068d72876")


def _stable_guid(name: str) -> str:
    """Create a reproducible compressed IFC GlobalId from a fixture key."""
    import ifcopenshell

    value = uuid.uuid5(_GUID_NAMESPACE, name)
    return ifcopenshell.guid.compress(value.hex)


def _create_root(model, ifc_class: str, name: str, key: str):
    """Create one rooted IFC entity with a deterministic fixture GlobalId."""
    from ifcopenshell.api.root import create_entity

    entity = create_entity(model, ifc_class=ifc_class, name=name)
    entity.GlobalId = _stable_guid(key)
    return entity


def _assign_triangle_mesh(model, context, product, vertices) -> None:
    """Assign a deterministic triangle transport representation to a product."""
    from ifcopenshell.api.geometry import add_mesh_representation, assign_representation

    representation = add_mesh_representation(
        model,
        context=context,
        vertices=[vertices],
        faces=[[[0, 1, 2]]],
    )
    assign_representation(model, product=product, representation=representation)


def _grid_axis(model, tag: str, start: tuple[float, float], end: tuple[float, float]):
    """Create one explicit two-dimensional IFC grid-axis polyline."""
    curve = model.create_entity(
        "IfcPolyline",
        Points=[
            model.create_entity("IfcCartesianPoint", Coordinates=start),
            model.create_entity("IfcCartesianPoint", Coordinates=end),
        ],
    )
    return model.create_entity(
        "IfcGridAxis",
        AxisTag=tag,
        AxisCurve=curve,
        SameSense=True,
    )


def write_ifc4_description_fixture(path: Path) -> dict[str, str]:
    """Write the complete Gate 5 IFC4 fixture and return stable source ids."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    model = ifcopenshell.file(schema="IFC4")
    project = _create_root(model, "IfcProject", "Description project", "project")
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

    site = _create_root(model, "IfcSite", "Site", "site")
    building = _create_root(model, "IfcBuilding", "Building", "building")
    storey = _create_root(model, "IfcBuildingStorey", "Level 1", "storey")
    room = _create_root(model, "IfcSpace", "Analysis room", "room")
    model.create_entity("IfcRelAggregates", RelatingObject=project, RelatedObjects=[site])
    model.create_entity("IfcRelAggregates", RelatingObject=site, RelatedObjects=[building])
    model.create_entity("IfcRelAggregates", RelatingObject=building, RelatedObjects=[storey])
    model.create_entity("IfcRelAggregates", RelatingObject=storey, RelatedObjects=[room])

    wall = _create_root(model, "IfcWall", "North wall", "wall")
    slab = _create_root(model, "IfcSlab", "Floor slab", "slab")
    opening = _create_root(model, "IfcOpeningElement", "Door opening", "opening")
    furniture_a = _create_root(model, "IfcFurniture", "Table A", "furniture-a")
    furniture_b = _create_root(model, "IfcFurniture", "Chair B", "furniture-b")
    covering = _create_root(model, "IfcCovering", "Carpet", "covering")
    covering.PredefinedType = "FLOORING"
    surface_feature = _create_root(
        model,
        "IfcSurfaceFeature",
        "Colour field",
        "surface-feature",
    )
    surface_feature.PredefinedType = "USERDEFINED"
    surface_feature.ObjectType = "OM_COLOR_FIELD"
    affordance = _create_root(
        model,
        "IfcSpatialZone",
        "Chair pull-back zone",
        "affordance",
    )
    affordance.PredefinedType = "USERDEFINED"
    affordance.ObjectType = "OM_AFFORDANCE_ZONE"
    grid = _create_root(model, "IfcGrid", "Main grid", "grid")

    # Simple authored meshes are sufficient because this gate verifies factual
    # extraction and relationships; local-height solids are exercised in Gate 3/8.
    mesh_vertices = {
        room: [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.0, 6.0, 0.0)],
        wall: [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.0, 0.0, 3.0)],
        slab: [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.0, 6.0, 0.0)],
        opening: [(1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (1.0, 0.0, 2.1)],
        furniture_a: [(2.0, 2.0, 0.0), (3.2, 2.0, 0.0), (2.0, 2.8, 0.75)],
        furniture_b: [(3.4, 2.0, 0.0), (4.0, 2.0, 0.0), (3.4, 2.6, 0.9)],
        covering: [(1.0, 1.0, 0.01), (5.0, 1.0, 0.01), (1.0, 4.0, 0.01)],
        surface_feature: [(5.5, 1.0, 0.02), (7.0, 1.0, 0.02), (5.5, 3.0, 0.02)],
        affordance: [(3.4, 1.2, 0.0), (4.2, 1.2, 0.0), (3.4, 2.0, 1.2)],
    }
    for product, vertices in mesh_vertices.items():
        _assign_triangle_mesh(model, body_context, product, vertices)

    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        RelatingStructure=storey,
        RelatedElements=[wall, slab, opening, furniture_a, furniture_b, covering, surface_feature],
    )
    model.create_entity(
        "IfcRelVoidsElement",
        RelatingBuildingElement=wall,
        RelatedOpeningElement=opening,
    )
    model.create_entity(
        "IfcRelAssignsToProduct",
        RelatingProduct=slab,
        RelatedObjects=[surface_feature],
    )

    group = _create_root(model, "IfcGroup", "Table and chair", "group")
    model.create_entity(
        "IfcRelAssignsToGroup",
        RelatingGroup=group,
        RelatedObjects=[furniture_a, furniture_b],
    )
    grid.UAxes = [_grid_axis(model, "A", (0.0, 0.0), (8000.0, 0.0))]
    grid.VAxes = [_grid_axis(model, "1", (0.0, 0.0), (0.0, 6000.0))]
    model.create_entity(
        "IfcRelReferencedInSpatialStructure",
        RelatingStructure=affordance,
        RelatedElements=[furniture_b],
    )
    affordance_purpose = model.create_entity(
        "IfcPropertySingleValue",
        Name="Purpose",
        NominalValue=model.create_entity("IfcLabel", "chair_pull_back"),
    )
    affordance_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=_stable_guid("affordance-pset"),
        Name="OM_Affordance",
        HasProperties=[affordance_purpose],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        RelatingPropertyDefinition=affordance_pset,
        RelatedObjects=[affordance],
    )

    role_property = model.create_entity(
        "IfcPropertySingleValue",
        Name="Role",
        NominalValue=model.create_entity("IfcLabel", "table_group_member"),
    )
    layout_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=_stable_guid("layout-pset"),
        Name="OM_Layout",
        HasProperties=[role_property],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        RelatingPropertyDefinition=layout_pset,
        RelatedObjects=[furniture_a],
    )

    material = model.create_entity("IfcMaterial", Name="Clear partition material")
    optical_property = model.create_entity(
        "IfcPropertySingleValue",
        Name="VisibleTransmittance",
        NominalValue=model.create_entity("IfcNormalisedRatioMeasure", 0.82),
    )
    model.create_entity(
        "IfcMaterialProperties",
        Name="Pset_MaterialOptical",
        Properties=[optical_property],
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
        Name="Viewport transparency",
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
        RelatedObjects=[furniture_a],
    )

    model.write(str(path))
    return {
        "room": room.GlobalId,
        "wall": wall.GlobalId,
        "slab": slab.GlobalId,
        "opening": opening.GlobalId,
        "furniture_a": furniture_a.GlobalId,
        "furniture_b": furniture_b.GlobalId,
        "covering": covering.GlobalId,
        "surface_feature": surface_feature.GlobalId,
        "affordance": affordance.GlobalId,
        "group": group.GlobalId,
        "grid": grid.GlobalId,
    }


__all__ = ["write_ifc4_description_fixture"]
