"""Normalize Rhino/VisualARQ source facts without making BIM decisions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any


# This registry is intentionally narrower than the IFC schema: it validates
# authored labels relevant to this project without pretending to infer all IFC.
SUPPORTED_IFC_ENTITIES = frozenset(
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
        "IfcGrid",
        "IfcGridAxis",
        "IfcBuildingElementProxy",
    }
)

_PARTICIPATION_VALUES = frozenset({"include", "exclude", "unknown"})


def _copy_value(value: object) -> object:
    """Return a detached JSON-friendly copy of a provider value."""
    try:
        return deepcopy(value)
    except Exception:
        # Provider objects can contain handles that are not deepcopyable. Keep
        # the source record usable and make the loss visible in review output.
        return str(value)


def _text(value: object, default: str = "") -> str:
    """Normalize an optional provider field into a trimmed string."""
    if value is None:
        return default
    return str(value).strip()


def _list_of_text(value: object) -> list[str]:
    """Copy an optional sequence of relationship identifiers as strings."""
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        return [_text(value)] if _text(value) else []
    return [_text(item) for item in value if _text(item)]


def _property_map(record: Mapping[str, object]) -> dict[str, object]:
    """Collect authored property maps while preserving their original names."""
    properties: dict[str, object] = {}
    for key in ("user_text", "usertext", "properties", "attributes"):
        value = record.get(key)
        if isinstance(value, Mapping):
            properties.update({str(name): _copy_value(item) for name, item in value.items()})
    return properties


def _semantic_evidence(
    record: Mapping[str, object],
    properties: Mapping[str, object],
    object_id: str,
) -> tuple[dict[str, str], list[dict[str, object]]]:
    """Validate authored IFC labels and report conflicts without guessing."""
    reviews: list[dict[str, object]] = []
    plain = _text(record.get("IfcEntity") or properties.get("IfcEntity"))
    prefixed = _text(record.get("OM.IfcEntity") or properties.get("OM.IfcEntity"))
    candidates = [("IfcEntity", plain), ("OM.IfcEntity", prefixed)]
    present = [(source, value) for source, value in candidates if value]

    if not present:
        reviews.append(
            {
                "object_id": object_id,
                "reason": "missing_ifc_entity",
                "message": "No authored IFC entity label was provided.",
            }
        )
        return {
            "ifc_entity": "unknown",
            "ifc_entity_source": "none",
            "confidence": "unknown",
        }, reviews

    if len({value for _, value in present}) > 1:
        reviews.append(
            {
                "object_id": object_id,
                "reason": "conflicting_ifc_entity",
                "values": {source: value for source, value in present},
            }
        )
        return {
            "ifc_entity": "unknown",
            "ifc_entity_source": "conflict",
            "confidence": "unknown",
        }, reviews

    source, value = present[0]
    if value not in SUPPORTED_IFC_ENTITIES:
        reviews.append(
            {
                "object_id": object_id,
                "reason": "unsupported_ifc_entity",
                "value": value,
                "source": source,
            }
        )
        return {
            "ifc_entity": "unknown",
            "ifc_entity_source": source,
            "confidence": "unknown",
        }, reviews

    return {
        "ifc_entity": value,
        "ifc_entity_source": source,
        "confidence": "authored",
    }, reviews


def _normalize_geometry(record: Mapping[str, object]) -> dict[str, object]:
    """Describe available geometry without converting it into semantic meaning."""
    vertices = record.get("vertices")
    faces = record.get("faces")
    summary = record.get("geometry_summary")
    available = bool(vertices) or bool(faces) or isinstance(summary, Mapping)
    result: dict[str, object] = {
        "available": available,
        "summary": _copy_value(summary) if isinstance(summary, Mapping) else {},
    }
    if isinstance(vertices, (list, tuple)):
        result["vertex_count"] = len(vertices)
    if isinstance(faces, (list, tuple)):
        result["face_count"] = len(faces)
    return result


def _normalize_relationships(record: Mapping[str, object]) -> dict[str, object]:
    """Preserve block, instance, parent, and group facts for later mapping."""
    return {
        "block_definition": _text(
            record.get("block_definition") or record.get("instance_definition")
        ),
        "instance_path": _list_of_text(record.get("instance_path")),
        "parent_ids": _list_of_text(record.get("parent_ids") or record.get("parents")),
        "group_ids": _list_of_text(record.get("group_ids") or record.get("groups")),
    }


def _normalize_object(
    record: Mapping[str, object], index: int, provider_name: str
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Normalize one source object and return its local review records."""
    reviews: list[dict[str, object]] = []
    object_id = _text(record.get("id") or record.get("guid") or record.get("object_id"))
    if not object_id:
        object_id = f"unidentified-{index:04d}"
        reviews.append(
            {
                "object_id": object_id,
                "reason": "missing_object_id",
                "message": "Provider record has no stable source identifier.",
            }
        )

    properties = _property_map(record)
    semantics, semantic_reviews = _semantic_evidence(record, properties, object_id)
    reviews.extend(semantic_reviews)
    participation = _text(record.get("analysis_participation"), "unknown").lower()
    if participation not in _PARTICIPATION_VALUES:
        reviews.append(
            {
                "object_id": object_id,
                "reason": "invalid_analysis_participation",
                "value": participation,
            }
        )
        participation = "unknown"

    source_name = _text(record.get("name") or record.get("source_name"))
    source_kind = _text(record.get("geometry_type") or record.get("object_type"), "unknown")
    item: dict[str, object] = {
        "id": object_id,
        "source_name": source_name,
        "display_name": source_name,
        "layer": _text(record.get("layer")),
        "source_kind": source_kind.lower(),
        "geometry": _normalize_geometry(record),
        "source_semantics": semantics,
        "relationships": _normalize_relationships(record),
        "analysis_participation": participation,
        "source_properties": properties,
        "provenance": {
            "provider": provider_name,
            "raw_id": object_id,
            "source_index": index,
        },
    }
    return item, reviews


def normalize_visualarq_source(
    records: Iterable[Mapping[str, object]],
    source_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return a neutral, auditable source payload from VisualARQ/Rhino facts."""
    if isinstance(records, (str, bytes, Mapping)):
        raise ValueError("records must be an iterable of object records")

    metadata = dict(source_metadata or {})
    provider_name = _text(metadata.get("provider"), "rhino_visualarq")
    objects: list[dict[str, object]] = []
    reviews: list[dict[str, object]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"records[{index}] must be a mapping")
        item, item_reviews = _normalize_object(record, index, provider_name)
        objects.append(item)
        reviews.extend(item_reviews)

    # Keep guide data separate: the dedicated grid adapter owns its semantics.
    guides = metadata.get("visualarq_guides")
    return {
        "schema_version": "visualarq-source-1",
        "source_application": _text(metadata.get("source_application"), "Rhino"),
        "source_name": _text(metadata.get("source_name")),
        "source_path": _text(metadata.get("source_path")),
        "objects": objects,
        "visualarq_guides": _copy_value(guides) if isinstance(guides, list) else [],
        "review_records": reviews,
        "exported_ifc": False,
        "imported_bonsai": False,
    }
