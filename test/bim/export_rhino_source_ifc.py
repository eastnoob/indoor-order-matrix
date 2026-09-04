"""Export a normalized Rhino source JSON payload into a traceable IFC4 file."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from convert_rhino_fixture_to_ifc import (
    _assign_layout_properties,
    _assign_mesh,
    _create_root,
    _localize_mesh,
    _stable_guid,
)


def _load_source(path: Path) -> dict[str, Any]:
    """Load and validate the normalized Rhino source payload."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    objects = payload.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("The Rhino source payload has no logical furniture objects")
    for record in objects:
        if not record.get("id") or not record.get("vertices") or not record.get("faces"):
            raise ValueError(f"Incomplete logical furniture record: {record.get('id')}")
    return payload


def _occurrence_name(
    record: dict[str, Any], kind: str, ordinal: int
) -> str:
    """Return a readable occurrence name while preserving source identity separately."""
    explicit_name = str(
        record.get("display_name")
        or record.get("logical_name")
        or record.get("name")
        or record.get("source_preview_name")
        or ""
    ).strip()
    if explicit_name:
        return explicit_name
    # Keep generated source IDs out of the human-facing IFC name.
    label = re.sub(r"[^A-Za-z0-9]+", "_", kind.strip()).strip("_") or "Furniture"
    return f"{label.title()}_{ordinal:02d}"


def _type_name(record: dict[str, Any], kind: str) -> str:
    """Return a readable type name without exposing generated naming syntax."""
    explicit_name = str(record.get("type_family_name") or "").strip()
    generated_name = f"{kind.strip().lower()}_type"
    if explicit_name and explicit_name.lower() != generated_name:
        return explicit_name
    label = re.sub(r"[^A-Za-z0-9]+", "_", kind.strip()).strip("_") or "Furniture"
    return f"{label.title()}Type"


def write_ifc(source_path: Path, target_path: Path) -> dict[str, object]:
    """Write one IFC4 file from normalized logical furniture records."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import edit_object_placement
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    payload = _load_source(source_path)
    source_objects = payload["objects"]
    model = ifcopenshell.file(schema="IFC4")
    # Keep the exported file in metric IFC4 so Rhino millimetre coordinates
    # remain traceable through the placement conversion below.
    project = _create_root(model, "IfcProject", "Rhino baseRoom furniture export")
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

    site = _create_root(model, "IfcSite", "baseRoom site")
    building = _create_root(model, "IfcBuilding", "baseRoom building")
    storey = _create_root(model, "IfcBuildingStorey", "Level 1")
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=_stable_guid("baseRoom:project-site"),
        RelatingObject=project,
        RelatedObjects=[site],
    )
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=_stable_guid("baseRoom:site-building"),
        RelatingObject=site,
        RelatedObjects=[building],
    )
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=_stable_guid("baseRoom:building-storey"),
        RelatingObject=building,
        RelatedObjects=[storey],
    )

    entities: dict[str, Any] = {}
    type_members: dict[str, list[Any]] = defaultdict(list)
    group_members: dict[str, list[Any]] = defaultdict(list)
    type_entities: dict[str, Any] = {}
    kind_ordinals: dict[str, int] = defaultdict(int)

    for record in source_objects:
        logical_id = str(record["id"])
        kind = str(record.get("kind", "furniture"))
        kind_ordinals[kind] += 1
        occurrence_name = _occurrence_name(record, kind, kind_ordinals[kind])
        entity = _create_root(model, "IfcFurniture", occurrence_name)
        entity.Tag = logical_id
        entity.ObjectType = kind
        # Store each logical product as one IFC object; source mesh parts are
        # merged before export so chair legs or proxy branches cannot become
        # accidental furniture entities.
        local_vertices, faces, origin = _localize_mesh(record)
        _assign_mesh(model, body_context, entity, local_vertices, faces)
        placement = [
            [1.0, 0.0, 0.0, origin[0]],
            [0.0, 1.0, 0.0, origin[1]],
            [0.0, 0.0, 1.0, origin[2]],
            [0.0, 0.0, 0.0, 1.0],
        ]
        edit_object_placement(model, product=entity, matrix=placement, is_si=True)
        _assign_layout_properties(
            model,
            entity,
            {
                "SourceDocument": payload.get("source_name", "Rhino source"),
                "SourcePath": payload.get("source_path", ""),
                "SourcePreviewName": record.get("source_preview_name", ""),
                "SourceRepresentation": record.get("source_representation", ""),
                "SourceModel": record.get("source_model", ""),
                "SourceDefinition": record.get("source_definition", ""),
                "SourceObjectCount": len(record.get("source_ids", [])),
                "DisplayName": occurrence_name,
                "FunctionalRole": kind,
                "TypeFamilyId": str(record.get("type_family_id") or kind),
                "CanonicalObject": "true",
                "GeometryBranch": "GEOMETRY",
            },
        )
        # Use the normalized type family as the type key; broad semantic kind
        # remains the backward-compatible fallback for legacy source records.
        type_family_id = str(record.get("type_family_id") or kind)
        type_family_name = _type_name(record, kind)
        type_entity = type_entities.get(type_family_id)
        if type_entity is None:
            type_entity = _create_root(model, "IfcFurnitureType", type_family_name)
            type_entity.Name = type_family_name
            type_entities[type_family_id] = type_entity
        type_members[type_family_id].append(entity)
        group_members[str(record.get("source_model", "unassigned"))].append(entity)
        entities[logical_id] = entity

    for type_family_id, type_entity in type_entities.items():
        model.create_entity(
            "IfcRelDefinesByType",
            GlobalId=_stable_guid(f"baseRoom:type:{type_family_id}"),
            RelatingType=type_entity,
            RelatedObjects=type_members[type_family_id],
        )

    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=_stable_guid("baseRoom:storey-contains-furniture"),
        RelatingStructure=storey,
        RelatedElements=list(entities.values()),
    )

    # Preserve source-model membership as IFC groups without treating GROUP
    # and VARIABLE preview representations as separate physical products.
    for source_model, members in sorted(group_members.items()):
        group = _create_root(model, "IfcGroup", f"source_{source_model}")
        model.create_entity(
            "IfcRelAssignsToGroup",
            GlobalId=_stable_guid(f"baseRoom:group:{source_model}"),
            RelatingGroup=group,
            RelatedObjects=members,
        )
        _assign_layout_properties(
            model,
            group,
            {
                "SourceModel": source_model,
                "SourceRepresentationPolicy": "GROUP preferred; VARIABLE not duplicated",
                "MemberCount": len(members),
                "SemanticStatus": "source-normalized",
            },
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(target_path))
    return {
        "status": "passed",
        "target": str(target_path),
        "schema": model.schema,
        "furniture_count": len(model.by_type("IfcFurniture")),
        "furniture_type_count": len(model.by_type("IfcFurnitureType")),
        "group_count": len(model.by_type("IfcGroup")),
        "mesh_representation_count": len(model.by_type("IfcTriangulatedFaceSet")),
        "source_path": payload.get("source_path"),
        "source_object_count": len(source_objects),
        "excluded_source_facts": payload.get("excluded_source_facts", {}),
        "import_status": "not_run",
    }


def main() -> None:
    """Parse source and target paths, then print a machine-readable export report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    report = write_ifc(args.source, args.target)
    report_path = args.target.with_suffix(".export.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
