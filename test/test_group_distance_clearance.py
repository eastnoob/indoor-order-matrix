"""Focused synthetic checks for directional constrained route geometry."""

from shapely.geometry import box
from shapely.ops import unary_union

from features import group_distance as kernel
from features.group_distance import GridDescriptor


GRID = GridDescriptor("clearance", "plane", (0, 0), 1, 1, 2)
DOMAIN = box(0, 0, 2, 1)


def _rectangles(*bounds):
    """Return physical occupancy geometry from compact rectangle bounds."""
    return unary_union([box(*bound) for bound in bounds])


def test_asymmetric_thresholds_accept_exact_sum_and_reject_left_shortfall():
    """Both side thresholds and the same-position total are enforced inclusively."""
    accepted = _rectangles((0, 0, 2, 0.175), (0, 0.725, 2, 1))
    assert kernel._edge_clearance((0, 0), (0, 1), GRID, accepted, DOMAIN, (0.225, 0.225, 0.55))
    rejected = _rectangles((0, 0, 2, 0.15), (0, 0.70, 2, 1))
    assert kernel._edge_clearance((0, 0), (0, 1), GRID, rejected, DOMAIN, (0.225, 0.225, 0.55)) is None


def test_same_position_total_bottleneck_is_not_minima_from_different_points():
    """The total threshold is checked on each cross-section, rather than mixed minima."""
    blockers = _rectangles((0, 0, 2, 0.20), (0, 0.75, 2, 1))
    left, right, total = kernel._clearance_at((0.5, 0.5), (1.0, 0.0), blockers, DOMAIN)
    assert (left, right, total) == (0.25, 0.3, 0.55)


def test_obstacle_between_endpoints_blocks_segment():
    """A positive-length route edge cannot pass through physical mass."""
    blockers = _rectangles((0.95, 0.4, 1.05, 0.6))
    assert kernel._edge_clearance((0, 0), (0, 1), GRID, blockers, DOMAIN, (0.1, 0.1, 0.2)) is None


def test_domain_boundary_limits_directional_clearance():
    """The exact domain boundary is a clearance witness when no object is present."""
    left, right, total = kernel._clearance_at((1.0, 0.5), (1.0, 0.0), _rectangles(), DOMAIN)
    assert left == right == 0.5
    assert total == 1.0


def test_turn_has_positive_clearance_witness_and_rejects_narrow_corner():
    """Heading changes are checked at the vertex and do not create a zero-cost edge."""
    wide = _rectangles((0, 0, 2, 0.1), (0, 0.9, 2, 1))
    witness = kernel._turn_clearance((1, 0.5), (1.0, 0.0), (0.0, 1.0), wide, DOMAIN, (0.225, 0.225, 0.55))
    assert witness is not None
    narrow = _rectangles((0, 0, 2, 0.4), (0, 0.7, 2, 1))
    assert kernel._turn_clearance((1, 0.5), (1.0, 0.0), (0.0, 1.0), narrow, DOMAIN, (0.225, 0.225, 0.55)) is None


def test_turn_checks_normal_vertex_events_between_endpoint_and_midpoint_samples():
    """A blocker hit by a rotating normal between coarse turn samples is rejected."""
    import math

    angle = math.radians(110.0)
    x, y = 1.0 + 0.2 * math.cos(angle), 0.5 + 0.2 * math.sin(angle)
    blocker = _rectangles((x - 0.003, y - 0.003, x + 0.003, y + 0.003))
    assert kernel._turn_clearance((1, 0.5), (1.0, 0.0), (0.0, 1.0), blocker, DOMAIN,
                                  (0.225, 0.225, 0.55)) is None


def test_segment_positions_include_multipolygon_holes():
    """Polygon rings and holes participate in interior event splitting."""
    blockers = _rectangles((0.4, 0.2, 0.6, 0.4), (1.4, 0.6, 1.6, 0.8))
    positions = kernel._segment_positions(kernel.LineString(((0.5, 0.5), (1.5, 0.5))), blockers, DOMAIN)
    assert any(abs(value - expected) < 1e-12 for value in positions for expected in (0.1, 0.9))


def test_directional_state_accesses_keep_same_cell_candidates_distinct():
    """Source and target orientation remain part of access identity."""
    first = {"free_cell": (0, 1), "heading": (1.0, 0.0), "target_heading": (-1.0, 0.0), "offset": 1.0,
             "access_key": ("g", (0, 0), (0, 1))}
    second = {"free_cell": (0, 1), "heading": (0.0, 1.0), "target_heading": (0.0, -1.0), "offset": 1.0,
              "access_key": ("g", (1, 1), (0, 1))}
    states = kernel._state_accesses({first["access_key"]: first})
    states.update(kernel._state_accesses({second["access_key"]: second}))
    assert len(states) == 2


def test_constrained_recovery_keeps_same_cell_heading_seed_without_edges():
    """A zero-cell route remains a valid endpoint-offset-only constrained route."""
    import networkx as nx

    graph = nx.DiGraph()
    sample = {(0, 0): {"status": "established", "center": (0.5, 0.5), "query_ref": "q"}}
    access = {(0, 0): {"free_cell": (0, 0), "heading": (1.0, 0.0), "offset": 0.1,
                       "access_key": ("source",)}}
    distances, best, unknown = kernel._recover_source(graph, kernel._state_accesses(access), sample, False)
    assert list(distances) == ["virtual-source", ((0, 0), (1.0, 0.0))]
    assert best[((0, 0), (1.0, 0.0))][-1] == (((0, 0), (1.0, 0.0)),)
    assert unknown[((0, 0), (1.0, 0.0))] is False
