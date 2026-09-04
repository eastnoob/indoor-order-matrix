"""Read-only, JSON-safe inspection of an IFC file."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _entity_ref(entity: Any) -> dict[str, object]:
    """Return the stable, JSON-safe identity fields for an IFC entity."""
    return {
        "id": entity.id(),
        "type": entity.is_a(),
        "global_id": getattr(entity, "GlobalId", None),
        "name": getattr(entity, "Name", None),
    }


def _version(ifcopenshell: Any) -> str | None:
    """Return the installed IfcOpenShell version when exposed by the module."""
    value = getattr(ifcopenshell, "version", None)
    return value if isinstance(value, str) else None


def _header_filename(model: Any) -> str | None:
    """Read the source filename recorded in the IFC STEP header."""
    try:
        value = model.header.file_name.name
    except (AttributeError, IndexError):
        return None
    return value if isinstance(value, str) else None


def _has_step_envelope(path: Path) -> bool:
    """Check the required STEP header and closing marker before opening the parser."""
    with path.open("rb") as stream:
        content = stream.read()
    # Reject obviously incomplete STEP input before IfcOpenShell can construct a broken model.
    return content.startswith(b"ISO-10303-21;") and content.rstrip().endswith(
        b"END-ISO-10303-21;"
    )


def _units(model: Any) -> list[dict[str, object]]:
    """Summarize unit assignments without changing the model."""
    result: list[dict[str, object]] = []
    for assignment in model.by_type("IfcUnitAssignment"):
        for unit in assignment.Units or []:
            result.append(
                {
                    "type": unit.is_a(),
                    "unit_type": getattr(unit, "UnitType", None),
                    "name": getattr(unit, "Name", None),
                    "prefix": getattr(unit, "Prefix", None),
                }
            )
    return result


def _representations(model: Any) -> dict[str, object]:
    """Summarize product representation identifiers and representation types."""
    counts: Counter[str] = Counter()
    products: list[dict[str, object]] = []
    for product in model.by_type("IfcProduct"):
        representations = getattr(product, "Representation", None)
        if not representations:
            continue
        items = []
        for representation in representations.Representations or []:
            identifier = getattr(representation, "RepresentationIdentifier", None)
            representation_type = getattr(representation, "RepresentationType", None)
            counts[f"{identifier}:{representation_type}"] += 1
            items.append(
                {
                    "identifier": identifier,
                    "type": representation_type,
                    "item_count": len(representation.Items or []),
                }
            )
        products.append({"product": _entity_ref(product), "representations": items})
    return {"count": sum(counts.values()), "by_identifier_and_type": dict(counts), "products": products}


def _relations(model: Any) -> dict[str, list[dict[str, object]]]:
    """Summarize type, spatial, and group relations for import-gating evidence."""
    type_relations = []
    for relation in model.by_type("IfcRelDefinesByType"):
        type_relations.append(
            {
                "type": _entity_ref(relation.RelatingType),
                "objects": [_entity_ref(item) for item in relation.RelatedObjects or []],
            }
        )

    spatial_containment = []
    for relation in model.by_type("IfcRelContainedInSpatialStructure"):
        spatial_containment.append(
            {
                "structure": _entity_ref(relation.RelatingStructure),
                "elements": [_entity_ref(item) for item in relation.RelatedElements or []],
            }
        )

    group_membership = []
    for relation in model.by_type("IfcRelAssignsToGroup"):
        group_membership.append(
            {
                "group": _entity_ref(relation.RelatingGroup),
                "members": [_entity_ref(item) for item in relation.RelatedObjects or []],
            }
        )

    # These relation summaries expose semantic links that geometry alone cannot prove.
    return {
        "type_relations": type_relations,
        "spatial_containment": spatial_containment,
        "group_membership": group_membership,
    }


def _duplicate_global_ids(model: Any) -> list[dict[str, object]]:
    """Find repeated GlobalIds across rooted IFC entities."""
    entities_by_guid: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for entity in model:
        global_id = getattr(entity, "GlobalId", None)
        if global_id:
            entities_by_guid[global_id].append(_entity_ref(entity))
    # Duplicate IDs are import-gating evidence, so report every conflicting entity together.
    return [
        {"global_id": global_id, "entities": entities}
        for global_id, entities in entities_by_guid.items()
        if len(entities) > 1
    ]


def inspect_ifc(path: Path) -> dict[str, object]:
    """Inspect an IFC path without writing, importing, or otherwise mutating it."""
    path = Path(path)
    report: dict[str, object] = {
        "status": "not_available",
        "path": str(path),
        "reason": "IFC file does not exist",
        "schema": None,
        "validator_version": None,
        "entity_counts": {},
        "global_id_duplicates": [],
        "type_relations": [],
        "spatial_containment": [],
        "group_membership": [],
        "representations": {},
        "units": [],
        "source_header_filename": None,
    }
    if not path.is_file():
        return report

    try:
        import ifcopenshell
    except ImportError:
        report["reason"] = "ifcopenshell is not installed"
        return report

    try:
        if not _has_step_envelope(path):
            report.update(
                {
                    "status": "failed",
                    "reason": "Unable to open IFC file: missing ISO-10303-21 header or END-ISO-10303-21 marker",
                    "validator_version": _version(ifcopenshell),
                }
            )
            return report
    except OSError as exc:
        report.update(
            {
                "status": "failed",
                "reason": f"Unable to read IFC file: {exc}",
                "validator_version": _version(ifcopenshell),
            }
        )
        return report

    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:
        report.update(
            {
                "status": "failed",
                "reason": f"Unable to open IFC file: {exc}",
                "validator_version": _version(ifcopenshell),
            }
        )
        return report

    try:
        counts = Counter(entity.is_a() for entity in model)
        report.update(
            {
                "status": "passed",
                "reason": None,
                "schema": model.schema,
                "validator_version": _version(ifcopenshell),
                "entity_counts": dict(counts),
                "global_id_duplicates": _duplicate_global_ids(model),
                "representations": _representations(model),
                "units": _units(model),
                "source_header_filename": _header_filename(model),
                **_relations(model),
            }
        )
    except Exception as exc:
        report.update(
            {
                "status": "failed",
                "reason": f"Unable to inspect opened IFC file: {exc}",
                "validator_version": _version(ifcopenshell),
            }
        )
    return report


def main() -> None:
    """Parse CLI arguments and print the inspection report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to an IFC file")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()
    report = inspect_ifc(args.path)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: {report['path']}")


if __name__ == "__main__":
    main()
