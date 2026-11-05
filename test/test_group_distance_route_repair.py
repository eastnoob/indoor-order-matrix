"""Focused checks for route-first directional-clearance repair."""

from types import SimpleNamespace

from features.group_distance import GridDescriptor
from features.group_distance_repair import _clearance_context, check_path


def _polygon(x0, y0, x1, y1):
    """Return the canonical polygon component used by the geometry handoff."""
    return {"exterior": ((x0, y0), (x1, y0), (x1, y1), (x0, y1))}


def _bundle(blocker=None):
    """Build a small in-memory bundle for route-checking tests."""
    occupancy = () if blocker is None else ({"geometry_components": (blocker,)},)
    return SimpleNamespace(
        grid=GridDescriptor("test-grid", "test-frame", (0.0, 0.0), 1.0, 4, 4),
        domain={"components": (_polygon(0.0, 0.0, 4.0, 4.0),)},
        physical_occupancy=occupancy,
    )


def test_route_repair_accepts_clear_route():
    """A route with enough room on both sides receives exact witnesses."""
    context = _clearance_context(_bundle(), {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5})
    result = check_path(((1, 1), (1, 2)), context)
    assert result["passed"] is True
    assert result["edge_witnesses"] or result["screened_edges"]


def test_route_repair_rejects_blocked_edge():
    """A physical blocker crossing the candidate edge is reported for repair."""
    blocker = _polygon(1.45, 1.0, 1.55, 2.0)
    context = _clearance_context(_bundle(blocker), {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5})
    result = check_path(((1, 1), (1, 2)), context)
    assert result["passed"] is False
    assert result["failure"]["kind"] == "edge"
