"""Tests for the final BIM description verification artifact."""

from __future__ import annotations

import json
from pathlib import Path

from ..test.bim.final_verification import build_verification_record


def test_final_verification_record_checks_preview_structure() -> None:
    """Require the final record to report all spatial evidence layers."""
    record = build_verification_record(Path("test/output"))

    assert record["preview"]["source_geometry_count"] > 0
    assert record["preview"]["triangle_count"] > 0
    assert record["preview"]["inferred_region_count"] > 0
    assert record["preview"]["linked_gap_path_count"] == record["preview"]["gap_path_count"]
    assert record["preview"]["grid_axis_count"] > 0
    assert record["preview"]["boundary_geometry_reference_count"] == record["preview"]["boundary_channel_count"]
    assert record["runtime"]["portable_blender_process"] == "passed_generated_acceptance_scene"


def test_final_verification_json_is_valid_if_present() -> None:
    """Validate the generated ignored artifact when a prior run exists."""
    target = Path("test/output/bim_acceptance_verification.json")
    if target.exists():
        parsed = json.loads(target.read_text(encoding="utf-8"))
        assert parsed["contract"]["id"] == "bim_acceptance_verification"
