"""Normalize role-bearing Rhino nested Blocks for the existing BIM mapper."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


_ROOT = Path(__file__).resolve().parents[1]
_NORMALIZER = (
    _ROOT
    / "skills"
    / "bim-logical-object-mapping"
    / "scripts"
    / "normalize_logical_objects.py"
)


def _text(value: object) -> str:
    """Return a trimmed string for an optional authored value."""
    return str(value).strip() if value is not None else ""


def _attributes(record: Mapping[str, Any]) -> dict[str, Any]:
    """Merge supported Rhino attribute carriers without mutating input."""
    result: dict[str, Any] = {}
    for key in ("attributes", "user_text"):
        value = record.get(key)
        if isinstance(value, Mapping):
            result.update(value)
    return result


def _property(record: Mapping[str, Any], name: str) -> str:
    """Read one registered OM property from a Rhino record."""
    return _text(_attributes(record).get(name))


@lru_cache(maxsize=1)
def _normalizer_module() -> ModuleType:
    """Load the existing skill normalizer without copying its algorithm."""
    spec = importlib.util.spec_from_file_location(
        "order_analyzer_bim_logical_object_normalizer", _NORMALIZER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load BIM logical-object normalizer: {_NORMALIZER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _children(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested Block children from supported source field names."""
    value = record.get("children")
    if value is None:
        value = record.get("members")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _components(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return leaf geometry records directly authored under one Block."""
    value = record.get("components")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _walk_representations(
    root_id: str,
    record: Mapping[str, Any],
    path: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect display components, representation facts, and review issues."""
    display_components: list[dict[str, Any]] = []
    representations: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []

    for index, child in enumerate(_children(record), start=1):
        child_id = _text(child.get("id")) or f"child-{index}"
        definition = _text(child.get("definition") or child.get("name")) or child_id
        child_path = (*path, definition)
        role = _property(child, "OM.RepresentationRole")
        nested = _children(child)
        components = _components(child)

        if not role and (components or not nested):
            review.append(
                {
                    "root_id": root_id,
                    "block_path": list(child_path),
                    "candidate_id": child_id,
                    "reason": "unresolved_representation_role",
                    "required_action": "supervisor_assign_representation_role",
                }
            )
        elif role:
            source_id = _property(child, "OM.SourceInstanceId") or root_id
            substitute_kind = _property(child, "OM.SubstituteKind")
            representations.append(
                {
                    "id": child_id,
                    "root_id": root_id,
                    "block_path": list(child_path),
                    "representation_role": role,
                    "substitute_kind": substitute_kind or None,
                    "visibility_policy": (
                        _property(child, "OM.VisibilityPolicy")
                        or ("analysis_only" if role == "analysis_substitute" else "visible")
                    ),
                    "source_instance_id": source_id,
                    "confidence": "high",
                    "evidence": ["explicit_om_representation_role"],
                }
            )
            if role == "analysis_substitute" and source_id != root_id:
                review.append(
                    {
                        "root_id": root_id,
                        "block_path": list(child_path),
                        "candidate_id": child_id,
                        "reason": "conflicting_source_instance_binding",
                        "required_action": "supervisor_confirm_source_binding",
                    }
                )

            # Only visible product geometry defines the reusable furniture type.
            # Analysis substitutes remain attached evidence, never extra products.
            if role == "display_geometry":
                for component_index, component in enumerate(components, start=1):
                    normalized = dict(component)
                    source_component_id = _text(component.get("id")) or f"component-{component_index}"
                    normalized["id"] = "::".join((*child_path, source_component_id))
                    normalized["source_block_path"] = list(child_path)
                    display_components.append(normalized)

        nested_display, nested_representations, nested_review = _walk_representations(
            root_id, child, child_path
        )
        display_components.extend(nested_display)
        representations.extend(nested_representations)
        review.extend(nested_review)

    return display_components, representations, review


def normalize_rhino_blocks(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map nested Rhino Blocks into the existing logical-object report."""
    raw_instances = payload.get("instances")
    if raw_instances is None:
        raw_instances = payload.get("objects", [])
    instances = (
        [item for item in raw_instances if isinstance(item, Mapping)]
        if isinstance(raw_instances, Sequence) and not isinstance(raw_instances, (str, bytes))
        else []
    )
    groups: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    representations: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []

    for index, instance in enumerate(instances, start=1):
        root_id = (
            _property(instance, "OM.InstanceId")
            or _text(instance.get("id"))
            or f"rhino-product-{index}"
        )
        definition = _text(instance.get("definition") or instance.get("name")) or root_id
        if _property(instance, "OM.Role") != "logical_product":
            manual_review.append(
                {
                    "root_id": root_id,
                    "block_path": [definition],
                    "reason": "unconfirmed_logical_product_root",
                    "required_action": "supervisor_confirm_product_root",
                }
            )
            continue

        display, child_representations, child_review = _walk_representations(
            root_id, instance, (definition,)
        )
        components.extend(display)
        representations.extend(child_representations)
        manual_review.extend(child_review)
        if not display:
            manual_review.append(
                {
                    "root_id": root_id,
                    "block_path": [definition],
                    "reason": "missing_display_geometry",
                    "required_action": "supervisor_identify_display_geometry",
                }
            )

        groups.append(
            {
                "id": root_id,
                "name": definition,
                "kind": (
                    "furniture"
                    if _property(instance, "OM.IfcEntity") == "IfcFurniture"
                    else _property(instance, "OM.IfcEntity") or "untyped"
                ),
                "functional_complete": True,
                "member_ids": [item["id"] for item in display],
                "type_attributes": {"OM.TypeKey": _property(instance, "OM.TypeKey")},
                "source_block_path": [definition],
            }
        )

    normalizer = _normalizer_module()
    report = normalizer.normalize_source(
        {
            "source_name": _text(payload.get("source_name")) or "rhino-blocks",
            "groups": groups,
            "components": components,
        }
    )
    report["representations"] = representations
    report["manual_review"] = manual_review
    if manual_review:
        report["status"] = "blocked"
    return report


__all__ = ["normalize_rhino_blocks"]
