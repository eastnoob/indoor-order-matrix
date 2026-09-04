"""Normalize source components into logical products and BIM type families."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import re
from typing import Any, Mapping


def _text(value: Any) -> str:
    """Return a trimmed string for optional source facts."""
    return str(value).strip() if value is not None else ""


def _number(value: Any) -> float | None:
    """Return a finite numeric value or None for unusable source data."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _canonical(value: Any) -> str:
    """Serialize JSON-compatible evidence into a stable comparison key."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _group_id(record: Mapping[str, Any]) -> str:
    """Read a stable group identifier from a source group record."""
    return _text(record.get("id") or record.get("group_id") or record.get("name"))


def _component_group_ids(record: Mapping[str, Any]) -> list[str]:
    """Read all authored group memberships from one source component."""
    values = record.get("group_ids")
    if values is None:
        values = record.get("groups")
    if values is None:
        values = [record.get("source_group_id", record.get("source_group"))]
    if not isinstance(values, (list, tuple)):
        values = [values]
    return [_text(value) for value in values if _text(value)]


def _component_ids(record: Mapping[str, Any]) -> list[str]:
    """Return source IDs represented by one component record."""
    value = record.get("source_ids")
    if isinstance(value, (list, tuple)) and value:
        return [_text(item) for item in value if _text(item)]
    identifier = _text(record.get("id") or record.get("object_id"))
    return [identifier] if identifier else []


def _bbox_size(record: Mapping[str, Any]) -> list[float] | None:
    """Read a component bounding-box size in a rotation-tolerant form."""
    value = record.get("bbox_size")
    if value is None and isinstance(record.get("bbox"), Mapping):
        value = record["bbox"].get("size")
        if isinstance(value, Mapping):
            value = [value.get("x"), value.get("y"), value.get("z")]
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    numbers = [_number(item) for item in value]
    return sorted(round(item, 6) for item in numbers) if all(item is not None for item in numbers) else None


def _component_signature(record: Mapping[str, Any], tolerance: float) -> dict[str, Any]:
    """Build a placement-independent, type-relevant component signature."""
    geometry_signature = _text(
        record.get("geometry_signature")
        or record.get("shape_signature")
        or record.get("geometry_hash")
    )
    if not geometry_signature:
        dimensions = _bbox_size(record)
        scale = tolerance if tolerance > 0 else 1e-6
        geometry_signature = _canonical(
            {
                "geometry_type": _text(record.get("geometry_type") or record.get("type")),
                "dimensions": (
                    [round(value / scale) * scale for value in dimensions]
                    if dimensions is not None
                    else None
                ),
                "vertex_count": record.get("vertex_count"),
                "face_count": record.get("face_count"),
            }
        )
    role = _text(
        record.get("part_role")
        or record.get("component_role")
        or record.get("role")
        or record.get("kind")
    ).lower()
    return {
        "role": role,
        "geometry_signature": geometry_signature,
        "material_signature": _text(record.get("type_material_signature")),
    }


def _placement_center(
    components: list[Mapping[str, Any]],
) -> list[float] | None:
    """Return an occurrence center without using it for type matching."""
    points: list[list[float]] = []
    for component in components:
        value = component.get("center")
        if isinstance(value, (list, tuple)) and len(value) == 3:
            numbers = [_number(item) for item in value]
            if all(item is not None for item in numbers):
                points.append([float(item) for item in numbers])
    if not points:
        return None
    return [round(sum(point[index] for point in points) / len(points), 6) for index in range(3)]


def _merge_geometry(
    components: list[Mapping[str, Any]],
) -> tuple[list[Any], list[list[int]]] | None:
    """Merge optional component meshes while preserving source topology."""
    vertices: list[Any] = []
    faces: list[list[int]] = []
    for component in components:
        component_vertices = component.get("vertices")
        component_faces = component.get("faces")
        if not isinstance(component_vertices, list) or not isinstance(component_faces, list):
            return None
        offset = len(vertices)
        vertices.extend(component_vertices)
        for face in component_faces:
            if not isinstance(face, list):
                return None
            faces.append([int(index) + offset for index in face])
    return (vertices, faces) if vertices and faces else None


def _candidate_kind(
    group: Mapping[str, Any], components: list[Mapping[str, Any]]
) -> tuple[str, list[str]]:
    """Resolve a tentative semantic kind from explicit evidence only."""
    explicit = _text(
        group.get("kind")
        or group.get("category")
        or group.get("semantic_role")
        or group.get("object_type")
    ).lower()
    if explicit:
        return explicit, ["explicit_group_semantic"]
    values = [
        _text(
            component.get("kind")
            or component.get("category")
            or component.get("semantic_role")
            or component.get("object_type")
        ).lower()
        for component in components
    ]
    counts = Counter(value for value in values if value)
    if counts:
        return counts.most_common(1)[0][0], ["component_semantic_consensus"]
    return "untyped", ["no_semantic_kind"]


def _source_groups(
    payload: Mapping[str, Any], components: list[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Build a group membership index from explicit groups or component facts."""
    groups: dict[str, dict[str, Any]] = {}
    for raw_group in payload.get("groups", []) or []:
        if not isinstance(raw_group, Mapping):
            continue
        identifier = _group_id(raw_group)
        if identifier:
            groups[identifier] = dict(raw_group)
    for component in components:
        for identifier in _component_group_ids(component):
            group = groups.setdefault(identifier, {"id": identifier})
            members = group.setdefault("member_ids", [])
            for source_id in _component_ids(component):
                if source_id not in members:
                    members.append(source_id)
    return groups


def _type_family_id(kind: str, signature: Mapping[str, Any]) -> str:
    """Create a stable type-family ID from type-defining evidence."""
    digest = hashlib.sha1(_canonical(signature).encode("utf-8")).hexdigest()[:12]
    return f"type-{kind}-{digest}"


def _meaningful_name(value: Any) -> str:
    """Return an authored name unless it is an obvious generated placeholder."""
    text = _text(value)
    if not text:
        return ""
    if re.fullmatch(
        r"(?:rhino[-_ ]?group[-_ ]?\d+|group\d*|object\d+|unnamed|default|"
        r"[0-9a-f]{8,})",
        text,
        flags=re.IGNORECASE,
    ):
        return ""
    return text


def _semantic_name(kind: str) -> str:
    """Convert a semantic kind into a readable name base."""
    label = re.sub(r"[^A-Za-z0-9]+", "_", kind.strip()).strip("_")
    return label.title() or "Furniture"


def normalize_source(
    payload: Mapping[str, Any], geometry_tolerance: float = 1e-3
) -> dict[str, Any]:
    """Normalize a source scene into logical products, types, and occurrences."""
    raw_components = payload.get("components")
    if raw_components is None:
        raw_components = payload.get("objects", [])
    components = [item for item in raw_components or [] if isinstance(item, Mapping)]
    by_id = {
        source_id: component
        for component in components
        for source_id in _component_ids(component)
    }
    groups = _source_groups(payload, components)
    logical_objects: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    seen_components: set[str] = set()

    for identifier, raw_group in groups.items():
        member_ids = [
            _text(value)
            for value in raw_group.get("member_ids", [])
            if _text(value) in by_id
        ]
        member_components = [by_id[value] for value in member_ids]
        if not member_components:
            ambiguous.append(
                {"group_id": identifier, "reason": "empty_candidate", "confidence": "low"}
            )
            continue
        if raw_group.get("functional_complete") is False:
            ambiguous.append(
                {
                    "group_id": identifier,
                    "source_component_ids": member_ids,
                    "reason": "incomplete_candidate",
                    "confidence": "high",
                }
            )
            continue
        kind, kind_evidence = _candidate_kind(raw_group, member_components)
        signatures = [
            _component_signature(component, geometry_tolerance)
            for component in member_components
        ]
        type_attributes = raw_group.get("type_attributes", {})
        if not isinstance(type_attributes, Mapping):
            type_attributes = {}
        type_signature = {
            "kind": kind,
            "components": sorted(signatures, key=_canonical),
            "type_attributes": dict(type_attributes),
        }
        object_id = identifier
        geometry = _merge_geometry(member_components)
        evidence = [
            "explicit_group_membership",
            "complete_candidate",
            *kind_evidence,
            "placement_excluded_from_type_signature",
        ]
        logical_object = {
            "id": object_id,
            "kind": kind,
            "source_group_ids": [identifier],
            "source_component_ids": member_ids,
            "type_signature": type_signature,
            "geometry_fingerprint": _canonical(type_signature["components"]),
            "placement": {"center": _placement_center(member_components)},
            "confidence": "high" if kind != "untyped" else "medium",
            "evidence": evidence,
            "authored_name": _meaningful_name(
                raw_group.get("display_name") or raw_group.get("name")
            ),
        }
        if geometry is not None:
            logical_object["vertices"], logical_object["faces"] = geometry
        logical_objects.append(logical_object)
        seen_components.update(member_ids)

    # Human-facing names are derived once at the logical-object boundary;
    # source IDs remain separate so naming never changes object identity.
    name_bases = [
        item["authored_name"] or _semantic_name(str(item["kind"]))
        for item in logical_objects
    ]
    base_counts = Counter(name_bases)
    seen_names: Counter[str] = Counter()
    for logical_object, base in zip(logical_objects, name_bases):
        seen_names[base] += 1
        authored = bool(logical_object["authored_name"])
        if authored and base_counts[base] == 1:
            display_name = base
        else:
            display_name = f"{base}_{seen_names[base]:02d}"
        logical_object["display_name"] = display_name
        logical_object["name_evidence"] = (
            "authored_name" if authored else "semantic_kind_inference"
        )

    ungrouped = [
        source_id
        for source_id in by_id
        if source_id not in seen_components
    ]
    for source_id in ungrouped:
        ambiguous.append(
            {
                "source_component_ids": [source_id],
                "reason": "missing_logical_group_boundary",
                "confidence": "low",
            }
        )

    families: dict[str, dict[str, Any]] = {}
    for logical_object in logical_objects:
        family_id = _type_family_id(
            logical_object["kind"], logical_object["type_signature"]
        )
        logical_object["type_family_id"] = family_id
        family = families.setdefault(
            family_id,
            {
                "id": family_id,
                "kind": logical_object["kind"],
                "member_object_ids": [],
                "identity_basis": logical_object["type_signature"],
                "confidence": logical_object["confidence"],
            },
        )
        family["member_object_ids"].append(logical_object["id"])

    occurrences = [
        {
            "id": f"occurrence-{logical_object['id']}",
            "logical_object_id": logical_object["id"],
            "type_family_id": logical_object["type_family_id"],
            "placement": logical_object["placement"],
            "source_group_ids": logical_object["source_group_ids"],
            "confidence": logical_object["confidence"],
        }
        for logical_object in logical_objects
    ]
    for family in families.values():
        fingerprints = {
            next(
                item["geometry_fingerprint"]
                for item in logical_objects
                if item["id"] == object_id
            )
            for object_id in family["member_object_ids"]
        }
        family["geometry_reuse"] = (
            "shared_candidate"
            if len(family["member_object_ids"]) > 1 and len(fingerprints) == 1
            else "not_shared"
        )

    return {
        "status": "passed" if logical_objects and not ambiguous else "blocked",
        "source_name": _text(payload.get("source_name")),
        "logical_objects": logical_objects,
        "type_families": list(families.values()),
        "occurrences": occurrences,
        "ambiguous_candidates": ambiguous,
    }


def main() -> None:
    """Read a source JSON file, normalize it, and write a JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--geometry-tolerance", type=float, default=1e-3)
    args = parser.parse_args()
    payload = json.loads(args.source.read_text(encoding="utf-8"))
    report = normalize_source(payload, geometry_tolerance=args.geometry_tolerance)
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # Keep terminal output reviewable; the complete evidence remains in target.
    print(
        json.dumps(
            {
                "status": report["status"],
                "logical_object_count": len(report["logical_objects"]),
                "type_family_count": len(report["type_families"]),
                "occurrence_count": len(report["occurrences"]),
                "ambiguous_candidate_count": len(report["ambiguous_candidates"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
