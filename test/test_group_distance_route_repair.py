"""Focused checks for route-first directional-clearance repair."""

from types import SimpleNamespace

from features import group_distance as kernel
from features.group_distance import GridDescriptor
import networkx as nx
import pytest

from features.group_distance_repair import _access_route_candidates, _clearance_context, check_path


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


def test_route_repair_checks_source_interface_turn(monkeypatch):
    """A clear lattice edge still fails when the source access turn is too tight."""
    context = _clearance_context(_bundle(), {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5})
    path = ((1, 1), (1, 2))
    heading = kernel._heading(kernel._center(path[0], context["bundle"].grid),
                              kernel._center(path[1], context["bundle"].grid))
    monkeypatch.setattr(kernel, "_edge_clearance", lambda *args, screen_only=False, **kwargs:
                        {} if screen_only else {"min_left_m": .3, "min_right_m": .3, "min_total_m": .6})

    def reject_source_turn(point, incoming, outgoing, *args, **kwargs):
        """Reject only the furniture-to-route heading transition at the first cell."""
        return None if point == kernel._center(path[0], context["bundle"].grid) and incoming == (1.0, 0.0) else {
            "min_left_m": .3, "min_right_m": .3, "min_total_m": .6
        }

    monkeypatch.setattr(kernel, "_turn_clearance", reject_source_turn)
    source = {"heading": (1.0, 0.0), "footprint_cell": (0, 1)}
    result = check_path(path, context, source_access=source)

    assert result["passed"] is False
    assert result["failure"]["kind"] == "turn"
    assert result["failure"]["endpoint"] == "source"


def test_access_route_candidates_change_endpoint_access():
    """Alternate furniture interfaces produce a bounded shortest route."""
    graph = nx.Graph()
    graph.add_edge((0, 0), (1, 0), weight=1.0)
    graph.add_edge((1, 0), (2, 0), weight=1.0)
    source = ({"access_key": ("s", 0), "free_cell": (0, 0), "offset": 0.1},)
    target = ({"access_key": ("t", 0), "free_cell": (2, 0), "offset": 0.2},)
    routes = _access_route_candidates(graph, source, target, 1)
    assert len(routes) == 1
    assert routes[0]["cell_keys"] == ((0, 0), (1, 0), (2, 0))
    assert routes[0]["value"] == pytest.approx(2.3)


def test_access_route_candidates_keep_same_cell_interface_variants():
    """Interfaces sharing a free cell remain distinct route candidates."""
    graph = nx.Graph()
    graph.add_edge((0, 0), (1, 0), weight=1.0)
    source = (
        {"access_key": ("s", 0), "free_cell": (0, 0), "offset": 0.1, "heading": (1.0, 0.0)},
        {"access_key": ("s", 1), "free_cell": (0, 0), "offset": 0.2, "heading": (0.0, 1.0)},
    )
    target = ({"access_key": ("t", 0), "free_cell": (1, 0), "offset": 0.2},)
    routes = _access_route_candidates(graph, source, target, 2)
    assert [route["source_access"]["access_key"] for route in routes] == [("s", 0), ("s", 1)]


def test_access_route_candidates_skip_blocked_interface_variant():
    """A failed endpoint interface can be excluded without blocking its cell path."""
    graph = nx.Graph()
    graph.add_edge((0, 0), (1, 0), weight=1.0)
    source = (
        {"access_key": ("s", 0), "free_cell": (0, 0), "offset": 0.1},
        {"access_key": ("s", 1), "free_cell": (0, 0), "offset": 0.2},
    )
    target = ({"access_key": ("t", 0), "free_cell": (1, 0), "offset": 0.2},)
    routes = _access_route_candidates(graph, source, target, 1, blocked_access_keys={("s", 0)})
    assert len(routes) == 1
    assert routes[0]["source_access"]["access_key"] == ("s", 1)
