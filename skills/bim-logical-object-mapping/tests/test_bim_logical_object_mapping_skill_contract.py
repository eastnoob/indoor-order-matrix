"""Contract tests for the logical-object mapping skill document."""

from __future__ import annotations

from pathlib import Path


SKILL = Path(__file__).parents[1] / "SKILL.md"


def test_skill_declares_generic_type_instance_boundary() -> None:
    """Require the skill to separate product, type family, and occurrence."""
    assert SKILL.is_file()
    content = SKILL.read_text(encoding="utf-8")
    required = (
        "logical_object",
        "type_family",
        "occurrence",
        "IfcFurnitureType",
        "IfcRelDefinesByType",
        "IfcRepresentationMap",
        "confidence",
        "ambiguous",
    )
    missing = [term for term in required if term not in content]
    assert not missing, f"missing skill contract terms: {missing}"


def test_skill_is_not_hard_coded_to_the_acceptance_fixture() -> None:
    """Prevent the reusable skill from encoding the current Rhino group IDs."""
    content = SKILL.read_text(encoding="utf-8")
    assert "Group698" not in content
    assert "Group700" not in content
    assert "Group702" not in content
