from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]


def test_masspatch_skill_points_to_existing_explicit_backend() -> None:
    """Keep generation as an explicit producer without duplicating its algorithm."""
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "existing backend generator",
        "explicitly requested",
        "does not discover",
        "does not export ifc",
        "features/mass_patch_generation.py",
    ):
        assert phrase in text


def test_masspatch_contract_keeps_source_read_only() -> None:
    """Document the source immutability guarantee for generated substitutes."""
    text = (
        SKILL_ROOT / "references" / "masspatch-generation-contract.md"
    ).read_text(encoding="utf-8").lower()
    assert "source-read-only" in text
    assert "ifc export" in text
