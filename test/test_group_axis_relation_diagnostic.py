"""Focused checks for the read-only group-axis relation diagnostic."""

from __future__ import annotations

import pytest

from scripts.design.group_level.run_group_axis_relation_ifc import (
    _relation_records,
    axis_angle_gap,
)


def test_undirected_axis_gap_treats_zero_and_180_as_equal():
    """An undirected axis repeats every 180 degrees and caps at 90 degrees."""
    assert axis_angle_gap(0.0, 180.0) == pytest.approx(0.0)
    assert axis_angle_gap(15.0, 195.0) == pytest.approx(0.0)
    assert axis_angle_gap(0.0, 90.0) == pytest.approx(90.0)


def test_pair_channels_are_symmetric_and_not_collapsed():
    """Relation readings stay separate while their endpoint order is irrelevant."""
    observations = {
        "a": {"angle": 0.0, "clarity": 0.8, "axis_status": "computed", "direction_status": "computed"},
        "b": {"angle": 180.0, "clarity": 0.4, "axis_status": "computed", "direction_status": "computed"},
    }
    record = _relation_records(observations)[0]
    channels = record["channels"]
    assert channels["axis_angle_gap"]["value"] == pytest.approx(0.0)
    assert channels["direction_similarity"]["value"] == pytest.approx(1.0)
    assert channels["clarity_similarity"]["value"] == pytest.approx(0.6)
    assert channels["clarity_support"]["value"] == pytest.approx(0.4)
    assert "combined_relation" not in record


def test_unavailable_axis_does_not_erase_valid_clarity_relation():
    """Axis state gates direction readings independently from clarity values."""
    observations = {
        "a": {"angle": 30.0, "clarity": 0.25, "axis_status": "computed", "direction_status": "undefined"},
        "b": {"angle": 50.0, "clarity": 0.75, "axis_status": "computed", "direction_status": "computed"},
    }
    channels = _relation_records(observations)[0]["channels"]
    assert channels["axis_angle_gap"]["status"] == "not_available"
    assert channels["direction_similarity"]["value"] is None
    assert channels["clarity_similarity"]["value"] == pytest.approx(0.5)
    assert channels["clarity_support"]["value"] == pytest.approx(0.25)
