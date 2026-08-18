"""Generate the deterministic three-dimensional Gate 8 acceptance fixture."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
import uuid


_GUID_NAMESPACE = uuid.UUID("483adb3c-d1cd-4cf9-ada4-d294f72e42d7")


@dataclass(frozen=True)
class Box:
    """One oriented closed box in world coordinates."""

    center: tuple[float, float, float]
    size: tuple[float, float, float]
    angle: float = 0.0


@dataclass(frozen=True)
class ObjectSpec:
    """One stable acceptance object and its factual geometry role."""

    id: str
    ifc_class: str
    role: str
    boxes: tuple[Box, ...]


def _scene_objects() -> tuple[ObjectSpec, ...]:
    """Return the complete deterministic physical and surface object set."""
    return (
        ObjectSpec("room", "IfcSpace", "analysis_domain", (Box((6.0, 4.5, -0.01), (12.0, 9.0, 0.02)),)),
        ObjectSpec("floor", "IfcSlab", "slab", ()),
        ObjectSpec("wall_north", "IfcWall", "wall", (Box((6.0, 8.9, 1.5), (12.0, 0.2, 3.0)),)),
        ObjectSpec("wall_west", "IfcWall", "wall", (Box((0.1, 4.5, 1.5), (0.2, 9.0, 3.0)),)),
        ObjectSpec("aligned_table_a", "IfcFurniture", "furniture", (Box((2.0, 2.0, 0.375), (1.6, 0.8, 0.75)),)),
        ObjectSpec("aligned_chair", "IfcFurniture", "furniture", (Box((3.4, 2.0, 0.45), (0.6, 0.6, 0.9)),)),
        ObjectSpec("oblique_table_a", "IfcFurniture", "furniture", (Box((7.8, 2.1, 0.375), (1.6, 0.8, 0.75), 30.0),)),
        ObjectSpec("oblique_chair", "IfcFurniture", "furniture", (Box((9.0, 2.8, 0.45), (0.6, 0.6, 0.9), 30.0),)),
        ObjectSpec("mixed_table_a", "IfcFurniture", "furniture", (Box((3.0, 6.4, 0.375), (1.6, 0.8, 0.75)),)),
        ObjectSpec("mixed_table_b", "IfcFurniture", "furniture", (Box((4.6, 6.5, 0.375), (1.6, 0.8, 0.75), 45.0),)),
        ObjectSpec(
            "sofa",
            "IfcFurniture",
            "furniture",
            (
                Box((8.0, 6.3, 0.425), (2.4, 0.8, 0.45)),
                Box((8.0, 6.82, 0.6), (2.4, 0.16, 1.2)),
                Box((6.9, 6.4, 0.55), (0.2, 1.0, 0.7)),
                Box((9.1, 6.4, 0.55), (0.2, 1.0, 0.7)),
            ),
        ),
        ObjectSpec("low_cabinet", "IfcFurniture", "furniture", (Box((10.7, 5.8, 0.45), (1.2, 0.5, 0.9)),)),
        ObjectSpec("glass_partition", "IfcWall", "wall", (Box((6.0, 4.5, 1.2), (0.12, 3.0, 2.4)),)),
        ObjectSpec("carpet", "IfcCovering", "surface", (Box((2.8, 2.2, 0.01), (4.5, 3.2, 0.02)),)),
        ObjectSpec("chair_affordance_aligned", "IfcSpatialZone", "affordance_zone", (Box((3.4, 1.25, 0.6), (0.8, 0.9, 1.2)),)),
        ObjectSpec("chair_affordance_oblique", "IfcSpatialZone", "affordance_zone", (Box((9.35, 2.2, 0.6), (0.8, 0.9, 1.2), 30.0),)),
    )


def _stable_guid(name: str) -> str:
    """Return a reproducible compressed IFC GlobalId for one logical id."""
    import ifcopenshell

    return ifcopenshell.guid.compress(uuid.uuid5(_GUID_NAMESPACE, name).hex)


def _box_mesh(box: Box) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    """Create a closed triangulated box while preserving its stable world transform."""
    cx, cy, cz = box.center
    sx, sy, sz = box.size
    theta = radians(box.angle)
    vertices = []
    for z_sign in (-1.0, 1.0):
        for y_sign in (-1.0, 1.0):
            for x_sign in (-1.0, 1.0):
                local_x = x_sign * sx / 2.0
                local_y = y_sign * sy / 2.0
                vertices.append(
                    (
                        cx + local_x * cos(theta) - local_y * sin(theta),
                        cy + local_x * sin(theta) + local_y * cos(theta),
                        cz + z_sign * sz / 2.0,
                    )
                )
    faces = [
        [0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5],
        [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6],
        [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3],
    ]
    return vertices, faces


def _compound_mesh(boxes: tuple[Box, ...]) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    """Combine disconnected closed boxes into one deterministic product mesh."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    for box in boxes:
        box_vertices, box_faces = _box_mesh(box)
        offset = len(vertices)
        vertices.extend(box_vertices)
        faces.extend([[index + offset for index in face] for face in box_faces])
    return vertices, faces


def _create_root(model, ifc_class: str, name: str):
    """Create one rooted IFC entity with stable identity."""
    from ifcopenshell.api.root import create_entity

    entity = create_entity(model, ifc_class=ifc_class, name=name)
    entity.GlobalId = _stable_guid(name)
    return entity


def _assign_mesh(model, context, product, boxes: tuple[Box, ...]) -> None:
    """Attach deterministic world-coordinate mesh geometry to one IFC product."""
    if not boxes:
        return
    from ifcopenshell.api.geometry import add_mesh_representation, assign_representation

    vertices, faces = _compound_mesh(boxes)
    # One shared triangulation function feeds IFC and Blender snapshots, which
    # makes the cross-adapter comparison test about adapters rather than fixtures.
    representation = add_mesh_representation(
        model,
        context=context,
        vertices=[vertices],
        faces=[faces],
    )
    assign_representation(model, product=product, representation=representation)


def _assign_property_set(model, entity, name: str, values: dict[str, str]) -> None:
    """Assign a small explicit OM_ property set to one IFC entity."""
    properties = [
        model.create_entity(
            "IfcPropertySingleValue",
            Name=key,
            NominalValue=model.create_entity("IfcLabel", value),
        )
        for key, value in values.items()
    ]
    property_set = model.create_entity(
        "IfcPropertySet",
        GlobalId=_stable_guid(f"{entity.GlobalId}:{name}"),
        Name=name,
        HasProperties=properties,
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=_stable_guid(f"rel:{entity.GlobalId}:{name}"),
        RelatingPropertyDefinition=property_set,
        RelatedObjects=[entity],
    )


def _grid_axis(model, tag: str, start: tuple[float, float], end: tuple[float, float]):
    """Create one explicit IFC grid axis from stable world coordinates."""
    curve = model.create_entity(
        "IfcPolyline",
        Points=[
            model.create_entity("IfcCartesianPoint", Coordinates=start),
            model.create_entity("IfcCartesianPoint", Coordinates=end),
        ],
    )
    return model.create_entity("IfcGridAxis", AxisTag=tag, AxisCurve=curve, SameSense=True)


def _write_ifc(path: Path, specs: tuple[ObjectSpec, ...]) -> dict[str, str]:
    """Write the complete IFC4 acceptance artifact and return logical source ids."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    model = ifcopenshell.file(schema="IFC4")
    project = _create_root(model, "IfcProject", "acceptance_project")
    assign_unit(model, units=[add_si_unit(model, unit_type="LENGTHUNIT")])
    model_context = add_context(model, context_type="Model")
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    site = _create_root(model, "IfcSite", "acceptance_site")
    building = _create_root(model, "IfcBuilding", "acceptance_building")
    storey = _create_root(model, "IfcBuildingStorey", "acceptance_storey")
    model.create_entity("IfcRelAggregates", GlobalId=_stable_guid("rel_project_site"), RelatingObject=project, RelatedObjects=[site])
    model.create_entity("IfcRelAggregates", GlobalId=_stable_guid("rel_site_building"), RelatingObject=site, RelatedObjects=[building])
    model.create_entity("IfcRelAggregates", GlobalId=_stable_guid("rel_building_storey"), RelatingObject=building, RelatedObjects=[storey])

    entities = {}
    for spec in specs:
        entity = _create_root(model, spec.ifc_class, spec.id)
        if spec.ifc_class == "IfcCovering":
            entity.PredefinedType = "FLOORING"
        if spec.ifc_class == "IfcSpatialZone":
            entity.PredefinedType = "USERDEFINED"
            entity.ObjectType = "OM_AFFORDANCE_ZONE"
        _assign_mesh(model, body_context, entity, spec.boxes)
        entities[spec.id] = entity

    room = entities["room"]
    model.create_entity("IfcRelAggregates", GlobalId=_stable_guid("rel_storey_room"), RelatingObject=storey, RelatedObjects=[room])
    contained = [entity for logical_id, entity in entities.items() if logical_id != "room" and entity.is_a("IfcElement")]
    model.create_entity("IfcRelContainedInSpatialStructure", GlobalId=_stable_guid("rel_storey_elements"), RelatingStructure=storey, RelatedElements=contained)

    groups = {
        "table_group_aligned": ("aligned_table_a", "aligned_chair"),
        "table_group_oblique": ("oblique_table_a", "oblique_chair"),
        "table_group_mixed": ("mixed_table_a", "mixed_table_b"),
    }
    for group_id, member_ids in groups.items():
        group = _create_root(model, "IfcGroup", group_id)
        entities[group_id] = group
        model.create_entity(
            "IfcRelAssignsToGroup",
            GlobalId=_stable_guid(f"rel:{group_id}"),
            RelatingGroup=group,
            RelatedObjects=[entities[item] for item in member_ids],
        )

    grid = _create_root(model, "IfcGrid", "grid_main")
    grid.UAxes = [
        _grid_axis(model, "A", (0.0, 0.0), (12.0, 0.0)),
        _grid_axis(model, "B", (0.0, 4.5), (12.0, 4.5)),
    ]
    grid.VAxes = [
        _grid_axis(model, "1", (0.0, 0.0), (0.0, 9.0)),
        _grid_axis(model, "2", (6.0, 0.0), (6.0, 9.0)),
    ]
    entities["grid_main"] = grid

    affordance_owners = {
        "chair_affordance_aligned": "aligned_chair",
        "chair_affordance_oblique": "oblique_chair",
    }
    for zone_id, owner_id in affordance_owners.items():
        zone = entities[zone_id]
        _assign_property_set(model, zone, "OM_Affordance", {"Purpose": "chair_pull_back"})
        model.create_entity(
            "IfcRelReferencedInSpatialStructure",
            GlobalId=_stable_guid(f"rel:{zone_id}:owner"),
            RelatingStructure=zone,
            RelatedElements=[entities[owner_id]],
        )

    _assign_property_set(model, entities["carpet"], "OM_Surface", {"Color": "#557a68", "Finish": "textile"})
    material = model.create_entity("IfcMaterial", Name="acceptance_glass")
    optical = model.create_entity(
        "IfcPropertySingleValue",
        Name="VisibleTransmittance",
        NominalValue=model.create_entity("IfcNormalisedRatioMeasure", 0.82),
    )
    model.create_entity("IfcMaterialProperties", Name="Pset_MaterialOptical", Properties=[optical], Material=material)
    model.create_entity(
        "IfcRelAssociatesMaterial",
        GlobalId=_stable_guid("rel_glass_material"),
        RelatingMaterial=material,
        RelatedObjects=[entities["glass_partition"]],
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(path))
    return {logical_id: entity.GlobalId for logical_id, entity in entities.items()}


def _blender_snapshot(specs: tuple[ObjectSpec, ...]) -> dict[str, object]:
    """Build the explicit Blender geometry payload from the shared source specification."""
    group_members = {
        "table_group_aligned": ("aligned_table_a", "aligned_chair"),
        "table_group_oblique": ("oblique_table_a", "oblique_chair"),
        "table_group_mixed": ("mixed_table_a", "mixed_table_b"),
    }
    group_by_member = {
        member_id: group_id
        for group_id, member_ids in group_members.items()
        for member_id in member_ids
    }
    objects = []
    for spec in specs:
        if not spec.boxes:
            continue
        vertices, faces = _compound_mesh(spec.boxes)
        group_id = group_by_member.get(spec.id)
        material_refs = ("blender-material:glass",) if spec.id == "glass_partition" else ()
        surface_refs = ("blender-surface:carpet",) if spec.id == "carpet" else ()
        factual_properties = {}
        if group_id is not None:
            factual_properties = {"group": group_id, "region": group_id}
        orientation = {
            "aligned_table_a": 0.0,
            "aligned_chair": 0.0,
            "oblique_table_a": 30.0,
            "oblique_chair": 30.0,
            "mixed_table_a": 0.0,
            "mixed_table_b": 45.0,
        }.get(spec.id)
        objects.append(
            {
                "id": spec.id,
                "name": spec.id,
                "selected": True,
                "vertices": vertices,
                "triangle_indices": faces,
                "is_manifold": True,
                "is_closed": True,
                "group_refs": ((f"blender-group:{group_id}",) if group_id else ()),
                "material_refs": material_refs,
                "surface_refs": surface_refs,
                "authored_local_frame": (
                    {"orientation_degrees": orientation}
                    if orientation is not None
                    else None
                ),
                "factual_properties": factual_properties,
                "world_transform": (
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                ),
            }
        )
    # These records are passed as typed authored facts to the Blender adapter;
    # their references intentionally target the adapter's stable object/mesh ids.
    authored_groups = [
        {
            "id": f"blender-group:{group_id}",
            "source_id": group_id,
            "member_refs": [f"blender-object:{member_id}" for member_id in member_ids],
            "group_role": "furniture_group",
            "provenance": {"method": "generated_explicit_blender_group"},
        }
        for group_id, member_ids in group_members.items()
    ]
    authored_grid_axes = [
        {
            "id": "blender-grid-axis:A",
            "source_id": "grid_main:A",
            "curve_points": [[0.0, 0.0, 0.0], [12.0, 0.0, 0.0]],
            "branch_identifier": "main",
            "list_identifier": "U",
            "same_sense": True,
            "provenance": {"method": "generated_explicit_blender_grid"},
        },
        {
            "id": "blender-grid-axis:B",
            "source_id": "grid_main:B",
            "curve_points": [[0.0, 4.5, 0.0], [12.0, 4.5, 0.0]],
            "branch_identifier": "main",
            "list_identifier": "U",
            "same_sense": True,
            "provenance": {"method": "generated_explicit_blender_grid"},
        },
        {
            "id": "blender-grid-axis:1",
            "source_id": "grid_main:1",
            "curve_points": [[0.0, 0.0, 0.0], [0.0, 9.0, 0.0]],
            "branch_identifier": "main",
            "list_identifier": "V",
            "same_sense": True,
            "provenance": {"method": "generated_explicit_blender_grid"},
        },
        {
            "id": "blender-grid-axis:2",
            "source_id": "grid_main:2",
            "curve_points": [[6.0, 0.0, 0.0], [6.0, 9.0, 0.0]],
            "branch_identifier": "main",
            "list_identifier": "V",
            "same_sense": True,
            "provenance": {"method": "generated_explicit_blender_grid"},
        },
    ]
    return {
        "source_length_unit": "m",
        "geometry_tolerance": 1e-6,
        "topology_tolerance": 1e-6,
        "objects": objects,
        "authored_groups": authored_groups,
        "authored_grids": [{
            "id": "blender-grid:grid_main",
            "source_id": "grid_main",
            "axis_refs": [axis["id"] for axis in authored_grid_axes],
            "provenance": {"method": "generated_explicit_blender_grid"},
        }],
        "authored_grid_axes": authored_grid_axes,
        "materials": [{
            "id": "blender-material:glass",
            "source_id": "glass_partition:material",
            "identity": "acceptance_glass",
            "visible_transmittance": 0.82,
            "viewport_transparency": None,
            "provenance": {"method": "generated_explicit_blender_material"},
        }],
        "surfaces": [{
            "id": "blender-surface:carpet",
            "source_id": "carpet",
            "host_refs": ["blender-object:room"],
            "identity": "IfcCovering:FLOORING",
            "color": "#557a68",
            "finish": "textile",
            "texture": None,
            "elevation": 0.01,
            "slope": None,
            "geometry_refs": ["blender-mesh:carpet"],
            "provenance": {"method": "generated_explicit_blender_surface"},
        }],
        "authored_affordances": [
            {
                "id": f"blender-affordance:{zone_id}",
                "source_id": zone_id,
                "geometry_refs": [f"blender-mesh:{zone_id}"],
                "vertical_extent": [0.0, 1.2],
                "purpose": "chair_pull_back",
                "task_facts": {"Purpose": "chair_pull_back"},
                "source_furniture_refs": [
                    f"blender-object:{owner_id}"
                    for owner_id in (
                        "aligned_chair" if zone_id == "chair_affordance_aligned" else "oblique_chair",
                    )
                ],
                "provenance": {"method": "generated_explicit_blender_affordance"},
            }
            for zone_id in ("chair_affordance_aligned", "chair_affordance_oblique")
        ],
    }


def generate_acceptance_scene(output_dir: Path) -> dict[str, object]:
    """Generate IFC and explicit Blender inputs safely in one output directory."""
    output_dir = Path(output_dir)
    specs = _scene_objects()
    ifc_path = output_dir / "bim_acceptance.ifc"
    source_ids = _write_ifc(ifc_path, specs)
    return {
        "ifc": ifc_path,
        "source_ids": source_ids,
        "blender_snapshot": _blender_snapshot(specs),
        "roles": {spec.id: spec.role for spec in specs if spec.boxes},
    }


if __name__ == "__main__":
    generate_acceptance_scene(Path(__file__).parents[1] / "output")
