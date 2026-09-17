"""Contract tests for the independent VisualARQ source adapter skill."""

from pathlib import Path


SKILL_PATH = Path(__file__).parents[1] / "SKILL.md"


def test_skill_has_triggering_frontmatter_and_phase_boundaries() -> None:
    """Require discoverability and explicit read-only phase boundaries."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "name: visualarq-source-adapter" in text
    assert "Use when" in text.splitlines()[2]
    assert "read-only" in text
    assert "does not export IFC" in text
    assert "does not import Bonsai" in text


def test_skill_defines_the_neutral_contract_and_safety_rules() -> None:
    """Require the fields and anti-guessing rules future agents need."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    for phrase in (
        "normalize_visualarq_source",
        "source_properties",
        "source_semantics.ifc_entity",
        "review_records",
        "analysis_participation",
        "visualarq_guides",
        "never establish an IFC class",
        "bim-logical-object-mapping",
        "currently advertised by `list_slots`",
        "10500",
    ):
        assert phrase in text
