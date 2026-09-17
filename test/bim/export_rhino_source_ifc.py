"""Export a normalized Rhino source JSON payload into a traceable IFC4 file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# The exporter is a documented standalone script, so add the repository root
# before importing shared adapters when Python starts from test/bim.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from convert_rhino_fixture_to_ifc import (
    _assign_layout_properties,
    _assign_mesh,
    _create_root,
    _localize_mesh,
    _stable_guid,
)
from adapters.rhino_visualarq_grid import normalize_visualarq_guides


# Only IFC product occurrences belong in the generic source-object loop. Grid
# axes and other non-products remain owned by their dedicated IFC structures.
SUPPORTED_PRODUCT_CLASSES = frozenset(
    {
        "IfcFurniture",
        "IfcFurnishingElement",
        "IfcEquipmentElement",
        "IfcElectricalElement",
        "IfcWall",
        "IfcDoor",
        "IfcWindow",
        "IfcColumn",
        "IfcBeam",
        "IfcSlab",
        "IfcRoof",
        "IfcStair",
        "IfcRailing",
        "IfcOpeningElement",
        "IfcBuildingElementProxy",
    }
)
FURNITURE_CLASSES = frozenset({"IfcFurniture", "IfcFurnishingElement"})
# These source labels are seen in VisualARQ, but they are not IFC4 entity
# declarations in the locked IfcOpenShell schema. They remain source facts and
# use the proxy fallback rather than creating an illegal IFC4 class.
IFC4_EXPORT_PRODUCT_CLASSES = SUPPORTED_PRODUCT_CLASSES - {
    "IfcEquipmentElement",
    "IfcElectricalElement",
}


def _load_source(path: Path) -> dict[str, Any]:
    """Load and validate source records that are ready for IFC serialization."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    objects = payload.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("The Rhino source payload has no exportable objects")
    for record in objects:
        if not record.get("id"):
            raise ValueError(f"Source record has no id: {record}")
    return payload


def _select_ifc_product_class(record: dict[str, Any]) -> tuple[str, str]:
    """Return an authored product class or the untyped proxy fallback."""
    semantics = record.get("source_semantics")
    authored = semantics.get("ifc_entity") if isinstance(semantics, dict) else None
    authored = authored or record.get("ifc_entity")
    if not authored or str(authored).lower() == "unknown":
        # The source adapter uses ``unknown`` as an explicit absence marker;
        # it must not be reported as a conflicting authored semantic label.
        authored = None
    if authored in IFC4_EXPORT_PRODUCT_CLASSES:
        return str(authored), "authored"
    if authored:
        return "IfcBuildingElementProxy", "review"
    # Legacy normalized furniture payloads predate source-semantic records.
    # Keep that explicit contract working without weakening the new adapter:
    # a new source record always carries source_semantics, even when unknown.
    if "source_semantics" not in record and str(record.get("kind", "")).lower() in {
        "chair",
        "table",
        "furniture",
    }:
        return "IfcFurniture", "authored"
    return "IfcBuildingElementProxy", "untyped"


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
        _validate_substitute_record(record)
    return records


def _validate_substitute_record(record: object) -> None:
    """Validate one explicit or embedded analysis substitute record."""
    if not isinstance(record, dict):
        raise ValueError("Each substitute record must be an object")
    required = ("source_global_id", "substitute_id", "vertices", "triangle_indices")
    if any(not record.get(field) for field in required):
        raise ValueError(f"Incomplete substitute record: {record.get('substitute_id')}")


def _embedded_substitutes(source_objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract authored nested proxy branches from their owning source objects."""
    embedded: list[dict[str, Any]] = []
    for source in source_objects:
        raw = source.get("analysis_substitutes")
        if raw is None and source.get("analysis_substitute") is not None:
            raw = source["analysis_substitute"]
        if raw is None:
            continue
        records = [raw] if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            raise ValueError(
                f"analysis_substitutes must be a list for source {source.get('id')}"
            )
        for substitute in records:
            if not isinstance(substitute, dict):
                raise ValueError("Each embedded substitute record must be an object")
            normalized = dict(substitute)
            normalized["source_global_id"] = str(source["id"])
            _validate_substitute_record(normalized)
            embedded.append(normalized)
    return embedded


def _authored_furniture_groups(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated explicit furniture-group source records only."""
    records = payload.get("furniture_groups", [])
    if records is None:
        return []
    if not isinstance(records, list):
        raise ValueError("furniture_groups must be a list when supplied")
    validated: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict) or not record.get("id"):
            raise ValueError("Each furniture group requires a stable id")
        member_ids = record.get("member_ids")
        if not isinstance(member_ids, list):
            raise ValueError(
                f"Furniture group {record['id']} must provide member_ids as a list"
            )
        validated.append(record)
    return validated


def _ifc_grid_axis(model: Any, record: dict[str, Any]) -> Any:
    """Create one native IFC grid axis from normalized Rhino millimetre points."""
    points = [
        model.create_entity(
            "IfcCartesianPoint",
            Coordinates=(float(point[0]), float(point[1])),
        )
        for point in record["curve_points"]
    ]
    curve = model.create_entity("IfcPolyline", Points=points)
    return model.create_entity(
        "IfcGridAxis",
        AxisTag=str(record["tag"]),
        AxisCurve=curve,
        SameSense=bool(record.get("same_sense", True)),
    )


def _create_visualarq_grid(model: Any, payload: dict[str, Any]) -> Any | None:
    """Serialize optional VisualARQ Guide evidence as one native IFC grid."""
    from ifcopenshell.api.geometry import edit_object_placement

    guide_records = payload.get("visualarq_guides") or ()
    if not guide_records:
        return None
    normalized = normalize_visualarq_guides(guide_records)
    grid = _create_root(model, "IfcGrid", str(normalized["name"]))
    grid.UAxes = [_ifc_grid_axis(model, axis) for axis in normalized["u_axes"]]
    grid.VAxes = [_ifc_grid_axis(model, axis) for axis in normalized["v_axes"]]
    if normalized["w_axes"]:
        grid.WAxes = [_ifc_grid_axis(model, axis) for axis in normalized["w_axes"]]
    # IFC requires a placement even though the imported Guide points are
    # already expressed in the storey's coordinate system.
    edit_object_placement(
        model,
        product=grid,
        matrix=[
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        is_si=True,
    )
    return grid


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
    """Write IFC4 products with optional same-product or sidecar analysis geometry."""
    import ifcopenshell
    from ifcopenshell.api.context import add_context
    from ifcopenshell.api.geometry import edit_object_placement
    from ifcopenshell.api.unit import add_si_unit, assign_unit

    if substitute_mode not in {"representation", "sidecar"}:
        raise ValueError("substitute_mode must be 'representation' or 'sidecar'")

    payload = _load_source(source_path)
    source_objects = payload["objects"]
    furniture_groups = _authored_furniture_groups(payload)
    substitutes = _load_substitutes(substitute_path)
    # A Rhino furniture block may carry its MassPatch as a nested proxy branch.
    # Keep the branch attached to its source occurrence while retaining the
    # older explicit sidecar input for providers that cannot embed it.
    substitutes.extend(_embedded_substitutes(source_objects))
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

    # Grid semantics belong to IFC itself. VisualARQ-specific recognition ends
    # before this point, so downstream Bonsai and analysis code see IfcGrid.
    grid = _create_visualarq_grid(model, payload)

    entities: dict[str, Any] = {}
    type_members: dict[str, list[Any]] = defaultdict(list)
    type_entities: dict[str, Any] = {}
    kind_ordinals: dict[str, int] = defaultdict(int)
    entity_counts: dict[str, int] = defaultdict(int)
    untyped_count = 0
    review_count = 0
    geometry_skipped_count = 0
    source_map: list[dict[str, str]] = []
    furniture_group_review: list[dict[str, object]] = []

    for record in source_objects:
        if not record.get("vertices") or not record.get("faces"):
            # Keep non-mesh source facts in the report, but do not fabricate a
            # zero-area IFC product for points, curves, or failed tessellation.
            geometry_skipped_count += 1
            continue
        logical_id = str(record["id"])
        kind = str(record.get("kind", "furniture"))
        kind_ordinals[kind] += 1
        occurrence_name = _occurrence_name(record, kind, kind_ordinals[kind])
        ifc_class, semantic_status = _select_ifc_product_class(record)
        entity = _create_root(model, ifc_class, occurrence_name)
        # Rhino names are presentation labels and are often repeated. Use the
        # stable source id for IFC identity so duplicate names cannot violate
        # IfcRoot.UR1 in a full-scene export.
        entity.GlobalId = _stable_guid(f"source-occurrence:{logical_id}")
        entity.Tag = logical_id
        entity.ObjectType = kind
        entity_counts[ifc_class] += 1
        if semantic_status == "untyped":
            untyped_count += 1
        elif semantic_status == "review":
            review_count += 1
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
                # Keep analysis participation as a factual source property;
                # downstream analyzers can exclude decoration without
                # confusing it with IFC semantic classification.
                "AnalysisParticipation": str(
                    record.get("analysis_participation", "unknown")
                ),
            },
        )
        # Source traceability is report-level data, not IFC analysis semantics.
        # Keeping it outside the model avoids adding a project-specific
        # property set to every product while preserving deterministic lookup.
        source_map.append(
            {
                "source_id": logical_id,
                "ifc_global_id": entity.GlobalId,
                "ifc_entity": ifc_class,
                "semantic_status": semantic_status,
            }
        )
        # Generic proxies and building products must not acquire fabricated
        # furniture type families merely because they share source geometry.
        if ifc_class in FURNITURE_CLASSES:
            type_family_id = str(record.get("type_family_id") or kind)
            type_family_name = _type_name(record, kind)
            type_entity = type_entities.get(type_family_id)
            if type_entity is None:
                type_entity = _create_root(model, "IfcFurnitureType", type_family_name)
                type_entity.Name = type_family_name
                # Type display names may repeat across families (for example,
                # two chair definitions both rendered as ``ChairType``).
                # IFC identity must follow the authored family key, not the
                # human-facing label, otherwise Bonsai/validators see a
                # duplicate IfcRoot.GlobalId.
                type_entity.GlobalId = _stable_guid(f"baseRoom:type:{type_family_id}")
                type_entities[type_family_id] = type_entity
            type_members[type_family_id].append(entity)
        entities[logical_id] = entity

    for type_family_id, type_entity in type_entities.items():
        model.create_entity(
            "IfcRelDefinesByType",
            # The relationship is a separate IfcRoot and must not reuse the
            # type entity's GUID namespace, even when both use one family key.
            GlobalId=_stable_guid(f"baseRoom:type-relation:{type_family_id}"),
            RelatingType=type_entity,
            RelatedObjects=type_members[type_family_id],
        )

    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=_stable_guid("baseRoom:storey-contains-furniture"),
        RelatingStructure=storey,
        RelatedElements=list(entities.values()),
    )
    if grid is not None:
        model.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=_stable_guid("baseRoom:storey-contains-grid"),
            RelatingStructure=storey,
            RelatedElements=[grid],
        )

    furniture_group_count = 0
    seen_group_ids: set[str] = set()
    for group_record in furniture_groups:
        group_id = str(group_record["id"])
        if group_id in seen_group_ids:
            furniture_group_review.append(
                {"group_id": group_id, "reason": "duplicate_group_id"}
            )
            continue
        seen_group_ids.add(group_id)
        members = []
        for member_id in group_record["member_ids"]:
            entity = entities.get(str(member_id))
            if entity is not None and entity.is_a() in FURNITURE_CLASSES:
                members.append(entity)
            else:
                furniture_group_review.append(
                    {
                        "group_id": group_id,
                        "member_id": str(member_id),
                        "reason": "missing_or_non_furniture_member",
                    }
                )
        if not members:
            furniture_group_review.append(
                {"group_id": group_id, "reason": "no_valid_furniture_members"}
            )
            continue
        # The authored outer Rhino Block is a logical container. Its stable
        # occurrence id defines the group identity; it never becomes a product
        # or acquires flattened container geometry in the IFC model.
        group = _create_root(
            model,
            "IfcGroup",
            str(group_record.get("name") or group_record.get("display_name") or "Furniture group"),
        )
        group.GlobalId = _stable_guid(f"furniture-group:{group_id}")
        group.ObjectType = "furniture_group"
        model.create_entity(
            "IfcRelAssignsToGroup",
            GlobalId=_stable_guid(f"furniture-group:{group_id}:members"),
            RelatingGroup=group,
            RelatedObjects=members,
        )
        _assign_layout_properties(
            model,
            group,
            {
                "GroupRole": "furniture_group",
                "MemberCount": len(members),
                "SourceGroupId": group_id,
                "SemanticStatus": "authored",
            },
        )
        furniture_group_count += 1

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
        "entity_counts": dict(sorted(entity_counts.items())),
        "untyped_count": untyped_count,
        "review_count": review_count,
        "geometry_skipped_count": geometry_skipped_count,
        "group_count": len(model.by_type("IfcGroup")),
        "furniture_group_count": furniture_group_count,
        "furniture_group_review": furniture_group_review,
        "source_model_group_count": 0,
        "grid_count": len(model.by_type("IfcGrid")),
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
        "source_map": source_map,
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
