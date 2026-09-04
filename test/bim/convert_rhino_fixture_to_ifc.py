"""Convert the Rhino table-and-chairs fixture into a compact IFC4 test file."""

from __future__ import annotations

import json
from pathlib import Path
import uuid

import numpy as np


_GUID_NAMESPACE = uuid.UUID("d7d445ca-4c2e-4de9-9b14-b9c7ff4dd65a")


def _stable_guid(key: str) -> str:
    """Return a deterministic IFC GlobalId for one logical fixture key."""
    import ifcopenshell

    return ifcopenshell.guid.compress(uuid.uuid5(_GUID_NAMESPACE, key).hex)


def _create_root(model, ifc_class: str, name: str):
    """Create one rooted IFC entity with a stable identity."""
    from ifcopenshell.api.root import create_entity

    entity = create_entity(model, ifc_class=ifc_class, name=name)
    entity.GlobalId = _stable_guid(name)
    return entity


def _assign_mesh(model, context, product, vertices, faces) -> None:
    """Attach one local triangulated mesh representation to an IFC product."""
    from ifcopenshell.api.geometry import add_mesh_representation, assign_representation

    representation = add_mesh_representation(
        model,
        context=context,
        vertices=[vertices],
        faces=[faces],
    )
    assign_representation(model, product=product, representation=representation)


def _assign_layout_properties(model, entity, values: dict[str, str]) -> None:
    """Store source traceability and factual conversion data in OM_Layout."""
    properties = [
        model.create_entity(
            "IfcPropertySingleValue",
            Name=key,
            NominalValue=model.create_entity("IfcLabel", str(value)),
        )
        for key, value in values.items()
    ]
    property_set = model.create_entity(
        "IfcPropertySet",
        GlobalId=_stable_guid(f"{entity.GlobalId}:OM_Layout"),
        Name="OM_Layout",
        HasProperties=properties,
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=_stable_guid(f"{entity.GlobalId}:OM_Layout:relation"),
        RelatingPropertyDefinition=property_set,
        RelatedObjects=[entity],
    )


def _load_source(path: Path) -> list[dict]:
    """Load the Rhino-extracted functional object records."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    objects = payload.get("objects", [])
    if {item.get("kind") for item in objects} != {"table", "chair"}:
        raise ValueError("Expected table and chair source records")
    if sum(item.get("kind") == "table" for item in objects) != 1:
        raise ValueError("Expected exactly one table source record")
    if sum(item.get("kind") == "chair" for item in objects) != 4:
        raise ValueError("Expected exactly four chair source records")
    return objects


def _localize_mesh(record: dict) -> tuple[list[list[float]], list[list[int]], list[float]]:
    """Convert millimetre world vertices into metre local vertices and placement."""
    vertices = np.asarray(record["vertices"], dtype=float) / 1000.0
    if vertices.size == 0:
        raise ValueError(f"Source object has no vertices: {record['id']}")
    origin = vertices.min(axis=0)
    local_vertices = (vertices - origin).tolist()
    faces = [[int(index) for index in face] for face in record["faces"]]
    if not faces:
        raise ValueError(f"Source object has no faces: {record['id']}")
    return local_vertices, faces, origin.tolist()


def write_ifc(source_path: Path, target_path: Path) -> dict[str, object]:
    """Write five canonical IFC furniture objects and one authored dining group."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import edit_object_placement
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    source_objects = _load_source(source_path)
    model = ifcopenshell.file(schema="IFC4")
    project = _create_root(model, "IfcProject", "Rhino BIM conversion test")
    assign_unit(
        model,
        units=[add_si_unit(model, unit_type="LENGTHUNIT", prefix="MILLI")],
    )
    model_context = add_context(model, context_type="Model")
    body_context = add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )

    site = _create_root(model, "IfcSite", "Test site")
    building = _create_root(model, "IfcBuilding", "Test building")
    storey = _create_root(model, "IfcBuildingStorey", "Level 1")
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=_stable_guid("project-site"),
        RelatingObject=project,
        RelatedObjects=[site],
    )
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=_stable_guid("site-building"),
        RelatingObject=site,
        RelatedObjects=[building],
    )
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=_stable_guid("building-storey"),
        RelatingObject=building,
        RelatedObjects=[storey],
    )

    entities = {}
    type_entities = {}
    type_members: dict[str, list[object]] = {}
    for record in source_objects:
        logical_id = record["id"]
        entity = _create_root(model, "IfcFurniture", logical_id)
        entity.Tag = logical_id
        entity.ObjectType = record["kind"]
        local_vertices, faces, origin = _localize_mesh(record)
        _assign_mesh(model, body_context, entity, local_vertices, faces)
        placement = np.identity(4)
        placement[:3, 3] = origin
        edit_object_placement(model, product=entity, matrix=placement, is_si=True)
        _assign_layout_properties(
            model,
            entity,
            {
                "SourceDocument": "4chair1table-test.3dm",
                "SourceGroup": record["source_group"],
                "SourceObjectCount": len(record["source_ids"]),
                "FunctionalRole": record["kind"],
                "CanonicalObject": "true",
            },
        )
        # Create one type per semantic kind; ``dict.setdefault`` would eagerly
        # evaluate its default and create duplicate IFC GlobalIds.
        type_entity = type_entities.get(record["kind"])
        if type_entity is None:
            type_entity = _create_root(
                model,
                "IfcFurnitureType",
                f"{record['kind']}_type",
            )
            type_entities[record["kind"]] = type_entity
        # IFC permits one type-assignment relation per type; collect all
        # occurrences first so the inverse cardinality remains valid.
        type_members.setdefault(record["kind"], []).append(entity)
        entities[logical_id] = entity

    for kind, type_entity in type_entities.items():
        model.create_entity(
            "IfcRelDefinesByType",
            GlobalId=_stable_guid(f"type:{kind}"),
            RelatingType=type_entity,
            RelatedObjects=type_members[kind],
        )

    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=_stable_guid("storey-contains-furniture"),
        RelatingStructure=storey,
        RelatedElements=list(entities.values()),
    )
    dining_group = _create_root(model, "IfcGroup", "dining_set")
    model.create_entity(
        "IfcRelAssignsToGroup",
        GlobalId=_stable_guid("dining-set-members"),
        RelatingGroup=dining_group,
        RelatedObjects=list(entities.values()),
    )
    _assign_layout_properties(
        model,
        dining_group,
        {
            "FunctionalRole": "table_chair_group",
            "MemberCount": len(entities),
            "SourceDocument": "4chair1table-test.3dm",
        },
    )
    model.write(str(target_path))
    return {
        "target": str(target_path),
        "schema": model.schema,
        "furniture_count": len(model.by_type("IfcFurniture")),
        "group_count": len(model.by_type("IfcGroup")),
        "mesh_representation_count": len(model.by_type("IfcTriangulatedFaceSet")),
        "source_object_count": sum(len(item["source_ids"]) for item in source_objects),
    }


def main() -> None:
    """Convert the extracted Rhino fixture and print a machine-readable summary."""
    root = Path(__file__).parents[2]
    source = root / "test" / "output" / "4chair1table-bim-source-meshes.json"
    target = root / "test" / "output" / "4chair1table-bim-test.ifc"
    print(json.dumps(write_ifc(source, target), sort_keys=True))


if __name__ == "__main__":
    main()
