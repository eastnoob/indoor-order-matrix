import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.analysis_substitute_discovery import discover_analysis_substitutes


def test_discovery_returns_existing_masspatch_without_generation() -> None:
    """Existing explicit bindings are returned as analysis-only records."""
    report = discover_analysis_substitutes(
        [
            {"id": "chair-1", "role": "furniture"},
            {
                "id": "patch-1",
                "role": "analysis_substitute",
                "substitute_kind": "MassPatch",
                "source_global_id": "chair-1",
            },
        ]
    )
    assert report["status"] == "passed"
    assert report["substitutes"][0]["substitute_id"] == "patch-1"


def test_discovery_reports_missing_source_without_generating() -> None:
    """A missing substitute is explicit and never becomes a generated record."""
    report = discover_analysis_substitutes(
        [{"id": "chair-1", "role": "furniture"}]
    )
    assert report["status"] == "not_found"
    assert report["missing_sources"] == ["chair-1"]
    assert report["substitutes"] == []


def test_discovery_reports_conflicting_bindings() -> None:
    """Two candidates for one source remain ambiguous instead of being guessed."""
    report = discover_analysis_substitutes(
        [
            {"id": "chair-1", "role": "furniture"},
            {"id": "patch-a", "role": "analysis_substitute", "source_id": "chair-1"},
            {"id": "patch-b", "role": "analysis_substitute", "source_id": "chair-1"},
        ]
    )
    assert report["status"] == "ambiguous"
    assert report["ambiguous_candidates"] == ["chair-1"]
    assert report["substitutes"] == []
