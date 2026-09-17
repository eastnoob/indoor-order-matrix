"""Tests for authored Rhino Block metadata resolution."""

from pathlib import Path
import sys


ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rhino_block_metadata import (
    effective_block_user_text,
    is_furniture_group,
    is_project_furniture_definition,
)


def test_effective_block_user_text_uses_instance_value_as_override() -> None:
    """Keep a reusable Definition default while allowing occurrence overrides."""
    effective = effective_block_user_text(
        {"OM.Role": "furniture_group", "Other": "definition"},
        {"OM.Role": "logical_product", "Instance": "yes"},
    )

    assert effective == {
        "OM.Role": "logical_product",
        "Other": "definition",
        "Instance": "yes",
    }


def test_only_the_exact_group_marker_activates_furniture_group_behavior() -> None:
    """Prevent names or near-miss labels from creating group semantics."""
    assert is_furniture_group({"OM.Role": "furniture_group"})
    assert not is_furniture_group({"OM.Role": "Furniture_Group"})
    assert not is_furniture_group({"OM.Role": "logical_product"})
    assert not is_furniture_group({})


def test_project_furniture_definition_uses_existing_chair_and_table_markers() -> None:
    """Recognize only the established project furniture Block naming convention."""
    assert is_project_furniture_definition("CHAIR_CozyChair")
    assert is_project_furniture_definition("TABLE_StandardCaffeeTable")
    assert not is_project_furniture_definition("OTHER_BarCounterAndShelves")
