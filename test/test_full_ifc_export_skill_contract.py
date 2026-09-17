"""Contract tests for the full-fidelity IFC export workflow."""

from pathlib import Path


def test_export_skill_documents_full_export_default() -> None:
    """Require the skill to distinguish full export from semantic guessing."""
    text = (Path(__file__).parents[1] / "skills" / "ifc-export" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "full export",
        "IfcBuildingElementProxy",
        "untyped",
        "analysis_participation",
        "does not mean semantic guessing",
        "validation",
        "Bonsai",
        "external export",
        "source_map",
        "analysis_substitutes",
        "same product's `Analysis`",
        "OM.Role = furniture_group",
        "Block Definition",
        "does not infer furniture groups",
    ):
        assert phrase in text
    assert "must not create an `OM_Source` property set" in text


def test_workflow_documents_untyped_full_export_fallback() -> None:
    """Require the orchestrator to preserve unlabeled geometry by default."""
    text = (
        Path(__file__).parents[1]
        / "skills"
        / "ifc-bim-conversion-workflow"
        / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "full export" in text
    assert "IfcBuildingElementProxy" in text
    assert "unknown" in text
    assert "nested analysis branches" in text
    assert "analysis_substitutes" in text
    assert "OM.Role = furniture_group" in text
    assert "IfcRelAssignsToGroup" in text
