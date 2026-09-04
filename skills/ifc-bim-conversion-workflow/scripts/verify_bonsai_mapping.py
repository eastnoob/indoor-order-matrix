"""Read-only, adapter-driven verification of Bonsai IFC object mappings."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


REQUIRED_ENTITY_TYPES = (
    "IfcProject",
    "IfcFurniture",
    "IfcFurnitureType",
    "IfcGroup",
)


def _base_report(*, path: str | None = None, tool_version: object = None) -> dict[str, object]:
    """Return the stable JSON-safe report shape used for every result."""
    return {
        "status": "not_available",
        "reason": None,
        "path": path,
        "tool_version": _json_safe_value(tool_version),
        "ifc_store_file": False,
        "schema": None,
        "entity_counts": {name: None for name in REQUIRED_ENTITY_TYPES},
        "mapped_objects": [],
        "unmapped_objects": [],
    }


def _json_safe_value(value: object) -> object:
    """Keep optional report metadata representable by the standard JSON encoder."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


def _property_value(obj: Any, name: str, default: object = None) -> object:
    """Read a property from either an object or a mapping without mutating it."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _definition_id(obj: Any) -> object:
    """Read Bonsai's IFC definition ID from the conventional property group."""
    properties = _property_value(obj, "BIMObjectProperties")
    if properties is None:
        properties = _property_value(obj, "bim_object_properties")
    return _property_value(properties, "ifc_definition_id", 0)


def _object_mapping(obj: Any) -> dict[str, object]:
    """Convert one relevant Blender object into JSON-safe mapping evidence."""
    name = _property_value(obj, "name", "<unnamed>")
    definition_id = _definition_id(obj)
    # Preserve the observed value so invalid identity evidence remains actionable.
    if not isinstance(definition_id, (bool, int, float, str, type(None))):
        definition_id = repr(definition_id)
    if definition_id is None:
        definition_id = 0
    return {"name": str(name), "ifc_definition_id": definition_id}


def _objects(adapter: Any) -> Iterable[Any]:
    """Return relevant scene objects through the adapter's read-only iterator."""
    return adapter.iter_relevant_objects()


class SnapshotAdapter:
    """Expose a JSON adapter snapshot through the verifier's read-only contract."""

    def __init__(self, snapshot: dict[str, Any]) -> None:
        """Store the caller-provided snapshot without changing it."""
        self.snapshot = snapshot

    def get_ifc_store_file(self) -> object:
        """Return the snapshot's active IfcStore presence marker."""
        return self.snapshot.get("ifc_store_file")

    def get_tool_version(self) -> object:
        """Return the optional Bonsai/Blender version recorded in the snapshot."""
        return self.snapshot.get("tool_version")

    def get_schema(self, ifc_file: object) -> object:
        """Return the snapshot's IFC schema."""
        return self.snapshot.get("schema")

    def count_entities(self, ifc_file: object, entity_type: str) -> object:
        """Return one recorded IFC entity count."""
        return self.snapshot.get("entity_counts", {}).get(entity_type)

    def iter_relevant_objects(self) -> list[dict[str, object]]:
        """Return recorded mapping evidence as immutable-shaped dictionaries."""
        return [
            {
                "name": item.get("name", "<unnamed>"),
                "BIMObjectProperties": {
                    "ifc_definition_id": item.get("ifc_definition_id", 0)
                },
            }
            for item in self.snapshot.get("mapped_objects", [])
            if isinstance(item, dict)
        ]


def collect_bonsai_mapping(
    adapter: Any, required_entity_counts: dict[str, int] | None = None
) -> dict[str, object]:
    """Collect active IFC and object mapping evidence from a read-only adapter.

    The adapter must expose ``get_ifc_store_file``, ``get_schema``,
    ``count_entities``, and ``iter_relevant_objects``. It may wrap a live
    Blender/Bonsai namespace or a test fake; this function never imports,
    deletes, clears, saves, or invokes an operator. Optional entity requirements
    are minimum counts for a known fixture or workflow; generic verification
    does not assume particular IFC classes beyond an active schema.
    """
    report = _base_report()
    required_entity_counts = required_entity_counts or {}
    invalid_requirements = [
        entity_type
        for entity_type, count in required_entity_counts.items()
        if not isinstance(entity_type, str)
        or not entity_type
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
    ]
    if invalid_requirements:
        report["status"] = "failed"
        report["reason"] = "required entity counts must map non-empty names to non-negative integers"
        return report
    get_tool_version = getattr(adapter, "get_tool_version", None)
    if callable(get_tool_version):
        try:
            report["tool_version"] = _json_safe_value(get_tool_version())
        except Exception:
            # Optional metadata must not change the verification status or block a report.
            report["tool_version"] = None
    required_methods = (
        "get_ifc_store_file",
        "get_schema",
        "count_entities",
        "iter_relevant_objects",
    )
    # Keep the adapter read-only: this verifier may inspect a live Blender scene but never mutate it.
    missing = [name for name in required_methods if not callable(getattr(adapter, name, None))]
    if missing:
        report["reason"] = "adapter lacks read-only capability: " + ", ".join(missing)
        return report

    try:
        ifc_file = adapter.get_ifc_store_file()
    except Exception as exc:
        report["status"] = "failed"
        report["reason"] = f"could not read active IfcStore file: {exc}"
        return report

    if ifc_file is None or ifc_file is False:
        report["status"] = "failed"
        report["reason"] = "Bonsai has no active IfcStore file; load an IFC file before verifying mappings"
        return report

    report["ifc_store_file"] = True
    try:
        schema = adapter.get_schema(ifc_file)
        if not isinstance(schema, str) or not schema.strip():
            report["status"] = "failed"
            report["reason"] = "adapter returned no IFC schema for the active IfcStore file"
            return report
        report["schema"] = schema
        entity_types = tuple(dict.fromkeys((*REQUIRED_ENTITY_TYPES, *required_entity_counts)))
        counts = {
            entity_type: adapter.count_entities(ifc_file, entity_type)
            for entity_type in entity_types
        }
    except Exception as exc:
        report["status"] = "failed"
        report["reason"] = f"adapter cannot provide IFC schema/counts: {exc}"
        return report

    # Normalize only values the generic verifier can trust; fixture-specific counts belong in adapters/tests.
    invalid_counts = [
        entity_type
        for entity_type, count in counts.items()
        if not isinstance(count, int) or isinstance(count, bool) or count < 0
    ]
    if invalid_counts:
        report["status"] = "failed"
        report["reason"] = "adapter returned invalid non-negative integer IFC counts: " + ", ".join(invalid_counts)
        return report

    report["entity_counts"] = counts
    unmet_requirements = [
        entity_type
        for entity_type, minimum in required_entity_counts.items()
        if counts[entity_type] < minimum
    ]
    if unmet_requirements:
        report["status"] = "failed"
        report["reason"] = "required IFC entity counts are below configured minimums: " + ", ".join(
            unmet_requirements
        )
        return report

    try:
        evidence = [_object_mapping(obj) for obj in _objects(adapter)]
    except Exception as exc:
        report["status"] = "failed"
        report["reason"] = f"adapter cannot inspect relevant Blender objects: {exc}"
        return report

    if not evidence:
        report["status"] = "failed"
        report["reason"] = "active IfcStore file has no relevant Blender object mapping evidence"
        return report

    # Names help operators diagnose a scene, but only Bonsai definition IDs establish IFC identity.
    unmapped = [
        item
        for item in evidence
        if not isinstance(item["ifc_definition_id"], int)
        or isinstance(item["ifc_definition_id"], bool)
        or item["ifc_definition_id"] <= 0
    ]
    report["mapped_objects"] = [item for item in evidence if item not in unmapped]
    report["unmapped_objects"] = unmapped
    if unmapped:
        report["status"] = "failed"
        report["reason"] = (
            "relevant Blender objects must have positive integer "
            "BIMObjectProperties.ifc_definition_id values; object names alone are insufficient"
        )
        return report

    report["status"] = "passed"
    report["reason"] = None
    return report


def _snapshot_report(path: Path) -> dict[str, object]:
    """Load and verify a JSON adapter snapshot without importing Blender or MCP."""
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = _base_report(path=str(path))
        report["reason"] = f"could not read JSON adapter snapshot: {exc}"
        return report
    if not isinstance(snapshot, dict):
        report = _base_report(path=str(path))
        report["reason"] = "JSON adapter snapshot must be an object"
        return report
    report = collect_bonsai_mapping(SnapshotAdapter(snapshot))
    report["path"] = str(path)
    return report


def main() -> None:
    """Print a read-only Bonsai mapping report from a snapshot or unavailable state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="JSON report-shaped adapter snapshot")
    args = parser.parse_args()
    if args.snapshot is None:
        report = _base_report()
        report["reason"] = (
            "a Bonsai adapter or Blender namespace is required for live mapping verification; "
            "provide --snapshot PATH for an offline read-only report"
        )
    else:
        report = _snapshot_report(args.snapshot)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
