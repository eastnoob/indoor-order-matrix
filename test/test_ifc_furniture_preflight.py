"""Unit tests for the read-only IFC furniture preflight measurements."""

from types import SimpleNamespace

import pytest

from .bim.check_ifc_furniture_analysis import (
    _bbox,
    _bbox_overlap_ratio,
    _normalized_center_distance,
)


def _mesh(offset: float = 0.0) -> SimpleNamespace:
    """Build the smallest mesh-like object needed by the descriptive checks."""
    return SimpleNamespace(
        id="fixture",
        vertices=(
            (offset, 0.0, 0.0),
            (offset + 1.0, 0.0, 0.0),
            (offset, 1.0, 0.0),
            (offset, 0.0, 1.0),
        ),
        triangle_indices=((0, 1, 2), (0, 1, 3)),
        is_manifold=False,
        is_closed=False,
    )


def test_preflight_reports_coincident_body_and_analysis_bounds() -> None:
    """Coincident representations produce full overlap and zero separation."""
    body = _bbox(_mesh())
    analysis = _bbox(_mesh())

    assert _bbox_overlap_ratio(body, analysis) == pytest.approx(1.0)
    assert _normalized_center_distance(body, analysis) == pytest.approx(0.0)


def test_preflight_reports_translation_without_inventing_a_score() -> None:
    """A translated substitute remains a measurable geometry discrepancy."""
    body = _bbox(_mesh())
    analysis = _bbox(_mesh(0.25))

    assert 0.0 < _bbox_overlap_ratio(body, analysis) < 1.0
    assert _normalized_center_distance(body, analysis) > 0.0
