"""Contract checks for the standalone IFC export skill."""

from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1] / "skills" / "ifc-export"


def test_ifc_export_skill_routes_to_project_exporter_without_copying_it() -> None:
    """Require the skill to call the existing exporter with explicit modes."""
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "test/bim/export_rhino_source_ifc.py" in text
    assert "representation" in text
    assert "sidecar" in text
    assert "Body" in text
    assert "Analysis" in text
    assert "does not generate" in text
    assert "--substitute-mode representation" in text
    assert "--substitute-mode sidecar" in text
    assert not (SKILL_ROOT / "scripts" / "export_rhino_source_ifc.py").exists()
