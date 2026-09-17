"""Resolve factual metadata authored on Rhino Block Definitions and instances."""

from __future__ import annotations

from collections.abc import Mapping


def effective_block_user_text(
    definition_user_text: Mapping[str, str] | None,
    instance_user_text: Mapping[str, str] | None,
) -> dict[str, str]:
    """Merge a reusable Definition default with occurrence-level overrides."""
    # Rhino Definitions describe reusable class defaults, while each placed
    # instance can intentionally override a property for one occurrence.
    effective = dict(definition_user_text or {})
    effective.update(instance_user_text or {})
    return effective


def is_furniture_group(user_text: Mapping[str, str]) -> bool:
    """Return whether metadata explicitly marks one Block as a group container."""
    # Exact matching prevents display names and approximate values from
    # silently creating an authored semantic relationship.
    return user_text.get("OM.Role") == "furniture_group"


def is_project_furniture_definition(definition_name: str) -> bool:
    """Recognize the project's established chair/table Block naming marker."""
    # This is a compatibility path for existing authored furniture Blocks. It
    # does not classify arbitrary geometry, labels, layers, or spatial groups.
    normalized = definition_name.upper()
    return normalized.startswith(("CHAIR_", "TABLE_"))


__all__ = [
    "effective_block_user_text",
    "is_furniture_group",
    "is_project_furniture_definition",
]
