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


def _load_substitutes(path: Path | None) -> list[dict[str, Any]]:
    """Load explicit MassPatch records without generating or inferring geometry."""
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("substitutes", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("Substitute payload must be a list or contain a substitutes list")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each substitute record must be an object")
        required = ("source_global_id", "substitute_id", "vertices", "triangle_indices")
        if any(not record.get(field) for field in required):
            raise ValueError(f"Incomplete substitute record: {record.get('substitute_id')}")
    return records


def _assign_analysis_properties(
    model: Any,
    entity: Any,
    binding: dict[str, Any],
    *,
    property_set_name: str = "OM_AnalysisProxy",
) -> None:
    """Store explicit source-to-analysis binding facts on the owning product."""
    values = {
        "OM_SourceGlobalId": binding["source_global_id"],
        "OM_SubstituteKind": binding.get("substitute_kind", "MassPatch"),
        "OM_AnalysisRole": binding.get(
            "analysis_role", "analysis_geometry_substitute"
        ),
        "OM_VisibilityPolicy": binding.get("visibility_policy", "analysis_only"),
    }
    if property_set_name == "OM_AnalysisProxy":
        values["OM_ProxyKind"] = values.pop("OM_SubstituteKind")
        values["OM_Authoritative"] = "false"
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
        GlobalId=_stable_guid(f"{entity.GlobalId}:{property_set_name}"),
        Name=property_set_name,
        HasProperties=properties,
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=_stable_guid(f"{entity.GlobalId}:{property_set_name}:relation"),
        RelatingPropertyDefinition=property_set,
        RelatedObjects=[entity],
    )


def write_ifc(
    source_path: Path,
    target_path: Path,
    *,
    substitute_path: Path | None = None,
    substitute_mode: str = "representation",
) -> dict[str, object]:
    """Write IFC4 furniture with optional same-product or sidecar analysis geometry."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import edit_object_placement
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    if substitute_mode not in {"representation", "sidecar"}:
        raise ValueError("substitute_mode must be 'representation' or 'sidecar'")

    payload = _load_source(source_path)
    source_objects = payload["objects"]
    substitutes = _load_substitutes(substitute_path)
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
    analysis_context = add_context(
        model,
        context_type="Model",
        context_identifier="Analysis",
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

    proxy_entities: list[Any] = []
    analysis_representation_count = 0
    analysis_representation_bindings: list[dict[str, str]] = []
    for binding in substitutes:
        source_global_id = str(binding["source_global_id"])
        if source_global_id not in entities:
            raise ValueError(
                f"Substitute source_global_id is not a source furniture object: "
                f"{source_global_id}"
            )
        vertices = [[float(value) / 1000.0 for value in vertex] for vertex in binding["vertices"]]
        faces = [[int(index) for index in face] for face in binding["triangle_indices"]]
        if substitute_mode == "representation":
            source_entity = entities[source_global_id]
            source_record = next(
                record for record in source_objects if str(record["id"]) == source_global_id
            )
            _, _, source_origin = _localize_mesh(source_record)
            # Substitute vertices are authored in world millimetres; convert them
            # into the source product's local metre frame before attaching them.
            local_vertices = [
                [
                    float(vertex[axis]) / 1000.0 - float(source_origin[axis])
                    for axis in range(3)
                ]
                for vertex in binding["vertices"]
            ]
            _assign_mesh(model, analysis_context, source_entity, local_vertices, faces)
            _assign_analysis_properties(
                model,
                source_entity,
                binding,
                property_set_name="OM_AnalysisRepresentation",
            )
            analysis_representation_count += 1
            analysis_representation_bindings.append(
                {
                    "source_global_id": source_global_id,
                    "substitute_id": str(binding["substitute_id"]),
                }
            )
            continue
        proxy = _create_root(
            model,
            "IfcBuildingElementProxy",
            f"analysis_{binding['substitute_id']}",
        )
        proxy.ObjectType = "ANALYSIS_GEOMETRY_SUBSTITUTE"
        proxy.Tag = str(binding["substitute_id"])
        _assign_mesh(model, body_context, proxy, vertices, faces)
        # A represented IfcProduct must have a placement, even when its mesh
        # vertices are already expressed in the storey's world coordinates.
        edit_object_placement(
            model,
            product=proxy,
            matrix=[
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            is_si=True,
        )
        _assign_analysis_properties(model, proxy, binding)
        proxy_entities.append(proxy)

    if proxy_entities:
        model.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=_stable_guid("baseRoom:storey-contains-analysis-proxies"),
            RelatingStructure=storey,
            RelatedElements=proxy_entities,
        )
        proxy_group = _create_root(model, "IfcGroup", "analysis_substitutes")
        model.create_entity(
            "IfcRelAssignsToGroup",
            GlobalId=_stable_guid("baseRoom:analysis-substitutes"),
            RelatingGroup=proxy_group,
            RelatedObjects=proxy_entities,
        )
        _assign_layout_properties(
            model,
            proxy_group,
            {
                "SemanticStatus": "analysis-only",
                "MemberCount": len(proxy_entities),
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
        "proxy_object_count": len(proxy_entities),
        "substitute_mode": substitute_mode,
        "analysis_representation_count": analysis_representation_count,
        "analysis_representation_bindings": analysis_representation_bindings,
        "proxy_bindings": [
            {
                "source_global_id": binding["source_global_id"],
                "substitute_id": binding["substitute_id"],
            }
            for binding in substitutes
            if substitute_mode == "sidecar"
        ],
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
    parser.add_argument("--substitutes", type=Path, default=None)
    parser.add_argument(
        "--substitute-mode",
        choices=("representation", "sidecar"),
        default="representation",
    )
    args = parser.parse_args()
    report = write_ifc(
        args.source,
        args.target,
        substitute_path=args.substitutes,
        substitute_mode=args.substitute_mode,
    )
    report_path = args.target.with_suffix(".export.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
