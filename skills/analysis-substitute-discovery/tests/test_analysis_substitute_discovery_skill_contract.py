from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]


def test_discovery_skill_declares_read_only_missing_and_no_generation_rules() -> None:
    """Keep the skill contract explicit about its non-generating boundary."""
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "already-authored",
        "does not create",
        "not_found",
        "read-only",
        "source_global_id",
        "masspatch",
    ):
        assert phrase in text


def test_reference_declares_binding_fields_and_separation() -> None:
    """Ensure the reusable contract documents the fields consumers need."""
    text = (
        SKILL_ROOT / "references" / "substitute-contract.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "source_global_id",
        "substitute_id",
        "substitute_kind",
        "analysis_role",
        "visibility_policy",
        "provenance",
        "confidence",
        "IFC serialization",
    ):
        assert phrase in text
