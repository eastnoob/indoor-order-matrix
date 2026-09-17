from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.column_grid import _axis_score, _frame_from_angles


def test_column_grid_normalizes_reversed_horizontal_axis_to_zero_trend() -> None:
    """A reversed IFC axis remains the same undirected horizontal trend."""
    frame = _frame_from_angles([180.0, 180.0, 180.0])

    assert frame == {"angle": 0.0, "strength": 1.0}


def test_column_grid_keeps_vertical_branch_trend() -> None:
    """A vertical branch remains distinct from the horizontal branch."""
    frame = _frame_from_angles([90.0, 90.0, 90.0])

    assert frame == {"angle": 90.0, "strength": 1.0}


def test_oblique_terminal_group_is_not_fully_aligned_to_orthogonal_grid() -> None:
    """A 30-degree terminal trend receives a non-zero orthogonal deviation."""
    assert _axis_score(30.0, 0.0) < 1.0
    assert _axis_score(30.0, 0.0) > 0.0
