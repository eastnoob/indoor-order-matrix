"""Acceptance tests for the provider-neutral VisualARQ source payload."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.rhino_visualarq_source import normalize_visualarq_source


FIXTURE = Path(__file__).parent / "fixtures" / "visualarq_source_fixture.json"


def test_fixture_contains_mixed_visualarq_semantics() -> None:
    """Keep authored furniture/building labels and unknown evidence distinct."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = normalize_visualarq_source(payload["objects"], payload)
    labels = {
        item["source_semantics"]["ifc_entity"] for item in report["objects"]
    }
    assert {"IfcWall", "IfcFurnishingElement", "unknown"} <= labels
    assert report["visualarq_guides"] == [{"id": "guide-a", "name": "A"}]


def test_acceptance_is_read_only_and_does_not_export() -> None:
    """Prove that source adaptation alone does not run later BIM phases."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = normalize_visualarq_source(payload["objects"], payload)
    assert report["exported_ifc"] is False
    assert report["imported_bonsai"] is False
    assert len(report["objects"]) == len(payload["objects"])


def test_decorative_exclusion_is_a_flag_not_object_removal() -> None:
    """Retain excluded decorations so downstream policy can audit the choice."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = normalize_visualarq_source(payload["objects"], payload)
    plant = next(item for item in report["objects"] if item["id"] == "plant-01")
    assert plant["analysis_participation"] == "exclude"
