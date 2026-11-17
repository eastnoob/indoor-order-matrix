"""Focused synthetic checks for directional constrained route geometry."""

from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import networkx as nx
import pytest
from types import SimpleNamespace

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


def test_unreachable_pair_identifies_its_clearance_model():
    """A valid blocked handoff retains a null distance and explains its routing model."""
    from dataclasses import replace
    from features.field_core import FieldQuery

    component = {"exterior": [(0, 0), (3, 0), (3, 1), (0, 1), (0, 0)], "holes": []}
    bundle = kernel.GroupDistanceInput(
        source_identity={"id": "blocked-fixture"}, analysis_plane={"frame": "plane", "units": "m"},
        domain={"id": "domain", "frame": "plane", "components": [component]},
        grid=GridDescriptor("blocked", "plane", (0, 0), 1, 1, 3),
        groups=tuple(kernel.GroupProjection(identity, [component], (identity,)) for identity in ("a", "b")),
        physical_occupancy=({"id": "barrier", "geometry_components": [component], "represented_source_ids": ["barrier"],
                             "representation_status": "original", "representation_provenance": {"representation_identifier": "Analysis"}},),
        unresolved_source_ids=(), unresolved_supports={},
        query=FieldQuery("domain", "plane"), query_context={"domain_id": "domain", "frame": "plane"},
        origin_offset=(0, 0), dependency_fingerprints={},
        clearance_policy={"min_left_m": .225, "min_right_m": .225, "min_total_m": .55})
    fingerprints = kernel.group_distance_input_fingerprints(bundle)
    bundle = replace(bundle, grid=replace(bundle.grid, domain_fingerprint=fingerprints["domain"],
                                          occupancy_fingerprint=fingerprints["occupancy"]),
                     query_context={**bundle.query_context, "analysis_plane_fingerprint": fingerprints["analysis_plane"]})
    bundle = replace(bundle, dependency_fingerprints=kernel.group_distance_input_fingerprints(bundle))
    result = kernel.calculate_group_pair_distances(bundle)
    reading = result.observations[0].centroid_free_space_hybrid
    assert reading["status"] == "unreachable" and reading["value"] is None, reading["reason"]
    assert "directional-clearance model" in reading["reason"]


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
    assert kernel._turn_clearance((1, 0.5), (1.0, 0.0), (0.0, 1.0), blocker, DOMAIN,
                                  (0.225, 0.225, 0.55), max_distance=0.55,
                                  index=kernel._build_clearance_index(blocker, DOMAIN), screen_only=True) is None


def test_sub_ulp_silhouette_keeps_its_own_vertex_clearance_event():
    """A positive-area narrow wedge cannot disappear when its angular span rounds to zero."""
    import math
    import numpy as np

    angle = math.radians(110.)
    direction = np.array((math.cos(angle), math.sin(angle)))
    normal = np.array((-direction[1], direction[0]))
    blocker = Polygon((.2 * direction, .23 * direction + 1e-17 * normal, .23 * direction - 1e-17 * normal))
    assert blocker.area > 0
    heading = angle - math.pi / 2 - .3
    incoming = math.cos(heading), math.sin(heading)
    outgoing = math.cos(heading + .6), math.sin(heading + .6)
    assert kernel._turn_clearance((0., 0.), incoming, outgoing, blocker, box(-5, -5, 5, 5),
                                  (.225, .225, .55)) is None


def test_diagonal_edge_recheck_retains_the_original_silhouette_origin():
    """Scalar distance reconstruction must not move a selected ray past its vertex."""
    from scripts.design.group_level.render_group_distance_blender import clearance_bands

    grid = GridDescriptor("diagonal-silhouette", "plane", (-1.25, -1.25), .5, 6, 6)
    domain = Polygon(((-3., -3.), (4., -2.), (3., 4.), (-2., 3.)))
    blockers = unary_union([
        Polygon(((-.8894686104662918, -.15909118010858883), (-1.1692619501306558, .11478479558491436),
                 (-1.3791968783211526, -.37314693127191867))),
        Polygon(((2.1626201750059013, 2.6417258555069925), (2.1891281685224078, 1.9907062362822447),
                 (2.6832100635353533, 1.9286998685903662))),
    ])
    witness = kernel._edge_clearance((2, 2), (3, 1), grid, blockers, domain, (.01, .01, .02))
    assert witness["min_left_m"] == pytest.approx(.7414437383950441)
    assert witness["min_total_m"] == pytest.approx(5.55501124430444)
    band, = clearance_bands({"points": [(0., 0.), (-.5, .5)], "clearance": {"edge_witnesses": [witness]}})
    geometry = Polygon(band["points"])
    assert geometry.difference(domain).area < 1e-12
    assert geometry.intersection(blockers).area < 1e-12


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
    sample = {(0, 0): {"status": "established", "value": False, "center": (0.5, 0.5), "query_ref": "q"}}
    access = {(0, 0): {"free_cell": (0, 0), "heading": (1.0, 0.0), "offset": 0.1,
                       "access_key": ("source",)}}
    distances, best, unknown = kernel._recover_source(graph, kernel._state_accesses(access), sample, False)
    assert list(distances) == ["virtual-source", ((0, 0), (1.0, 0.0))]
    assert best[((0, 0), (1.0, 0.0))][-1] == (((0, 0), (1.0, 0.0)),)
    assert unknown[((0, 0), (1.0, 0.0))] is False


def test_source_access_heading_can_turn_when_both_axis_neighbors_are_occupied():
    """A real shared-edge access may start a turn absent from all viable edge headings."""
    from features.field_core import FieldQuery

    def component(shape):
        """Keep the fixture on the same polygon handoff as ordinary group geometry."""
        return {"exterior": tuple(shape.exterior.coords), "holes": []}

    grid, domain = GridDescriptor("access-turn", "plane", (0, 0), 1., 5, 5), box(0, 0, 5, 5)
    source = box(2.1, 1.1, 2.9, 1.9)
    physical = tuple({"id": name, "geometry_components": [component(shape)],
                      "represented_source_ids": [name], "representation_status": "original",
                      "representation_provenance": {"representation_identifier": "Analysis"}}
                     for name, shape in (("source", source), ("ahead", box(2.4, 3.4, 2.6, 3.6))))
    bundle = SimpleNamespace(grid=grid, query=FieldQuery("d", "plane"),
                             domain={"id": "d", "frame": "plane", "components": [component(domain)]},
                             physical_occupancy=physical, unresolved_source_ids=(), unresolved_supports={},
                             query_context={"domain_id": "d", "frame": "plane"}, origin_offset=(0, 0),
                             free_space_samples=None,
                             clearance_policy={"min_left_m": .225, "min_right_m": .225, "min_total_m": .55})
    samples, graph, _, frontier = kernel._graphs(bundle, domain)
    group = kernel.GroupProjection("source", [component(source)], ("source",))
    accesses = kernel._accesses(group, kernel._group_geometry(group), domain, grid, samples, frontier, True)
    first, second = ((2, 2), (0., 1.)), ((2, 3), (1., 0.))
    source_access = next(access for access in accesses["selected"].values()
                         if (access["free_cell"], access["heading"]) == first)
    assert graph.has_edge(first, second)
    seeds = kernel._state_accesses({source_access["access_key"]: source_access})
    distances, best, _ = kernel._recover_source(graph, seeds, samples, False)
    assert distances[second] == source_access["offset"] + 1.
    assert best[second][-1] == (first, second)
    assert graph[first][second]["weight"] == 1.


@pytest.mark.parametrize("optimistic", [False, True])
@pytest.mark.parametrize("status,value", [("established", False), ("conditional", False),
                                          ("unknown", None), ("outside", None), ("invalid", None),
                                          ("not_available", None), ("established", True)])
def test_endpoint_only_source_seed_preserves_center_sample_eligibility(status, value, optimistic):
    """An access-only heading must obey the same status/value gate as route centers."""
    cell, state = (0, 0), ((0, 0), (1., 0.))
    samples = {cell: dict(status=status, value=value, center=(.5, .5), query_ref="access")}
    graph = nx.DiGraph()
    distances, best, _ = kernel._recover_source(graph, {state: dict(offset=0., access_key="source")},
                                               samples, optimistic)
    expected = (status in {"established", "conditional"} and value is False) or optimistic and status == "unknown"
    assert (state in distances) is expected
    assert (state in best) is expected


@pytest.mark.parametrize("unresolved,expected", [((), "computed"), (("unresolved",), "unknown")])
def test_public_endpoint_only_route_cannot_promote_unknown_access_to_computed(unresolved, expected):
    """A shared unknown access produces only an optimistic endpoint-offset reading."""
    from dataclasses import replace
    from features.field_core import FieldQuery

    def component(shape):
        """Serialize the actual endpoint and domain polygons for the public input."""
        return {"exterior": tuple(shape.exterior.coords), "holes": []}

    shapes = (box(.1, .1, .9, .9), box(2.1, .1, 2.9, .9))
    physical = tuple({"id": name, "geometry_components": [component(shape)],
                      "represented_source_ids": [name], "representation_status": "original",
                      "representation_provenance": {"representation_identifier": "Analysis"}}
                     for name, shape in zip(("a", "b"), shapes))
    bundle = kernel.GroupDistanceInput(
        source_identity={"id": "endpoint-status"}, analysis_plane={"frame": "plane", "units": "m"},
        domain={"id": "d", "frame": "plane", "components": [component(box(0, 0, 3, 1))]},
        grid=GridDescriptor("endpoint-status", "plane", (0, 0), 1., 1, 3),
        groups=tuple(kernel.GroupProjection(name, [component(shape)], (name,))
                     for name, shape in zip(("a", "b"), shapes)), physical_occupancy=physical,
        unresolved_source_ids=unresolved, unresolved_supports={}, query=FieldQuery("d", "plane"),
        query_context={"domain_id": "d", "frame": "plane"}, origin_offset=(0, 0), dependency_fingerprints={},
        clearance_policy={"min_left_m": .225, "min_right_m": .225, "min_total_m": .55})
    fingerprints = kernel.group_distance_input_fingerprints(bundle)
    bundle = replace(bundle, grid=replace(bundle.grid, domain_fingerprint=fingerprints["domain"],
                                          occupancy_fingerprint=fingerprints["occupancy"]),
                     query_context={**bundle.query_context, "analysis_plane_fingerprint": fingerprints["analysis_plane"]})
    bundle = replace(bundle, dependency_fingerprints=kernel.group_distance_input_fingerprints(bundle))
    result = kernel.calculate_group_pair_distances(bundle)
    observation = result.observations[0]
    assert observation.centroid_free_space_hybrid["status"] == expected
    route = observation.route if not unresolved else observation.lineage["optimistic_lower_bound"]
    assert route["value"] == 2. and route["edges"] == () and route["clearance"] is None
    assert result.diagnostics["graphs"]["observed"]["source_runs"] == (0 if unresolved else 1)
    assert result.diagnostics["graphs"]["optimistic"]["source_runs"] == 1


def test_constrained_geometry_is_cached_across_observed_and_optimistic_graphs(monkeypatch):
    """Both graphs share screens and selected witnesses; later calculations own new caches."""
    base = nx.Graph()
    base.add_edge((0, 0), (0, 1), weight=1.0, guard_cell_keys=())
    bundle = SimpleNamespace(clearance_policy={"min_left_m": 0.225, "min_right_m": 0.225, "min_total_m": 0.55},
                             physical_occupancy=(), grid=GRID)
    calls = {"edge": 0, "turn": 0}
    original_edge, original_turn = kernel._edge_clearance, kernel._turn_clearance

    def counted_edge(*args, **kwargs):
        """Count real edge computations without replacing geometry behavior."""
        calls["edge"] += 1
        return original_edge(*args, **kwargs)

    def counted_turn(*args, **kwargs):
        """Count real turn computations without replacing geometry behavior."""
        calls["turn"] += 1
        return original_turn(*args, **kwargs)

    monkeypatch.setattr(kernel, "_edge_clearance", counted_edge)
    monkeypatch.setattr(kernel, "_turn_clearance", counted_turn)
    domain = box(-10, -10, 10, 10)
    observed, optimistic, _ = kernel._constrained_graphs(bundle, domain, {}, (base, base.copy(), base.copy()))
    assert calls == {"edge": 2, "turn": 8}
    first, second = ((0, 0), (1.0, 0.0)), ((0, 1), (1.0, 0.0))
    assert "min_total_m" not in observed[first][second]["clearance"]
    exact = kernel._materialize_clearance(observed, first, second)
    assert (exact["clearance"]["min_left_m"], exact["clearance"]["min_right_m"], exact["clearance"]["min_total_m"]) == (9.5, 10.5, 20.0)
    assert calls == {"edge": 3, "turn": 9}
    assert kernel._materialize_clearance(optimistic, first, second) == exact
    assert calls == {"edge": 3, "turn": 9}
    kernel._constrained_graphs(bundle, domain, {}, (base, base.copy(), base.copy()))
    assert calls == {"edge": 5, "turn": 17}


def test_capped_index_screen_rejects_near_obstacle_and_exact_rechecks_far_obstacle():
    """Capped screening rejects near mass while far mass cannot corrupt exact witnesses."""
    grid = GridDescriptor("screen", "plane", (0, -10), 1, 1, 2)
    domain = box(0, -10, 2, 10)
    blockers = _rectangles((0, 0, 2, 1))
    index = kernel._build_clearance_index(blockers, domain)
    thresholds = (0.225, 0.225, 0.55)
    assert kernel._edge_clearance((0, 0), (0, 1), grid, blockers, domain, thresholds,
                                  max_distance=0.55, index=index, screen_only=True) == {}
    exact = kernel._edge_clearance((0, 0), (0, 1), grid, blockers, domain, thresholds, index=index)
    assert exact["min_left_m"] == 9.5
    assert exact["min_right_m"] == 0.5

    near = _rectangles((0, -9.3, 2, -9.0))
    near_index = kernel._build_clearance_index(near, domain)
    assert kernel._edge_clearance((0, 0), (0, 1), grid, near, domain, thresholds,
                                  max_distance=0.55, index=near_index, screen_only=True) is None


def test_continuous_turn_total_keeps_internal_stationary_minimum():
    """An interior total minimum is retained with or without irrelevant far event vertices."""
    domain = Polygon([(-3, -2), (4, -2), (3, 4), (-2, 3)])
    far = Polygon([(-5, 100), (-4, 103), (-7, 102)])
    for blockers in (Polygon(), far):
        witness = kernel._turn_clearance((0, 0), (1, 0), (0, 1), blockers, domain, (0, 0, 0))
        assert witness["min_total_m"] == pytest.approx(5.358446854507672, rel=0, abs=1e-12)


def test_continuous_turn_total_rejects_threshold_above_internal_minimum():
    """Endpoint and midpoint checks cannot accept a total threshold above its true minimum."""
    domain = Polygon([(-3, -2), (4, -2), (3, 4), (-2, 3)])
    far = Polygon([(-5, 100), (-4, 103), (-7, 102)])
    for blockers in (Polygon(), far):
        assert kernel._turn_clearance((0, 0), (1, 0), (0, 1), blockers, domain, (0, 0, 5.3585)) is None
        assert kernel._turn_clearance((0, 0), (1, 0), (0, 1), blockers, domain, (0, 0, 5.3585),
                                      max_distance=5.3585, index=kernel._build_clearance_index(blockers, domain),
                                      screen_only=True) is None


def test_constrained_geometry_caches_failed_edges(monkeypatch):
    """A rejected directional edge is not retried for the second support graph."""
    base = nx.Graph()
    base.add_edge((0, 0), (0, 1), weight=1.0, guard_cell_keys=())
    bundle = SimpleNamespace(clearance_policy={"min_left_m": 1.0, "min_right_m": 1.0, "min_total_m": 2.0},
                             physical_occupancy=(), grid=GRID)
    calls = []
    original = kernel._edge_clearance

    def counted(*args, **kwargs):
        """Observe real rejection calls without replacing the geometry check."""
        calls.append(args[:2])
        return original(*args, **kwargs)

    monkeypatch.setattr(kernel, "_edge_clearance", counted)
    observed, optimistic, _ = kernel._constrained_graphs(bundle, DOMAIN, {}, (base, base.copy(), base.copy()))
    assert observed.number_of_edges() == optimistic.number_of_edges() == 0
    assert calls == [((0, 0), (0, 1)), ((0, 1), (0, 0))]


def test_route_clearance_summary_includes_a_narrower_turn():
    """The route summary must include turns as well as positive-length edges."""
    first, second = ((0, 0), (1., 0.)), ((0, 1), (1., 0.))
    graph = nx.DiGraph()
    edge = dict(min_left_m=1., min_right_m=1., min_total_m=2., limiting_position_m=.5,
                limiting_left_m=1., limiting_right_m=1., limiting_total_m=2.)
    turn = dict(min_left_m=.4, min_right_m=.5, min_total_m=.9, limiting_angle_fraction=.3,
                limiting_left_m=.4, limiting_right_m=.5, limiting_total_m=.9)
    graph.add_edge(first, second, weight=1., clearance=edge, turn=turn)
    samples = {(0, column): dict(center=(column + .5, .5), status="established", query_ref=str(column))
               for column in (0, 1)}
    source = {first: dict(offset=0., access_key="s")}
    target = {second: dict(offset=0., access_key="t")}
    route = kernel._target_route(graph, target, source, {second: 1.},
                                 {second: (0, 0, "s", (first, second))}, {second: False}, samples, False)
    assert route["clearance"]["min_total_m"] == .9
    assert route["clearance"]["limiting_kind"] == "turn"
    assert route["clearance"]["limiting_angle_fraction"] == .3


def test_boundary_contact_and_tiny_positive_clearance_are_not_skipped():
    """A boundary hit at zero or below the former hit epsilon cannot become infinity."""
    domain = box(0, 0, 2, 2)
    empty = _rectangles()
    grid = GridDescriptor("boundary", "plane", (0, -.5), 1, 1, 2)
    policy = (.225, .225, .55)
    assert kernel._edge_clearance((0, 0), (0, 1), grid, empty, domain, policy) is None
    for y in (0., 1e-10):
        assert kernel._turn_clearance((.5, y), (1, 0), (1, 0), empty, domain, policy) is None
        assert kernel._clearance_at((.5, y), (1, 0), empty, domain)[1] <= 1e-10


def _support_fixture(status="established", *, turn_only=False):
    """Isolate off-path side evidence while keeping every route center known free."""
    grid = GridDescriptor("side-support", "plane", (0, 0), 1., 5, 5)
    first, second = (2, 2), (2, 3)
    base = nx.Graph()
    base.add_edge(first, second, weight=1., guard_cell_keys=())
    if turn_only:
        base.add_edge((1, 2), first, weight=1., guard_cell_keys=())
    samples = {(row, col): dict(status="established", value=False, center=(col + .5, row + .5),
                                query_ref=f"side:{row}:{col}") for row in range(5) for col in range(5)}
    side = (4, 0) if turn_only else (4, 2)
    # An occupied coarse cell can still contain a physically empty normal ray.
    samples[side].update(status=status, value=True)
    bundle = SimpleNamespace(clearance_policy={"min_left_m": .225, "min_right_m": .225, "min_total_m": .55},
                             grid=grid, physical_occupancy=())
    observed, optimistic, frontier = kernel._constrained_graphs(bundle, box(0, 0, 5, 5), samples,
                                                               (base, base.copy(), base.copy()))
    incoming = (0., 1.) if turn_only else (1., 0.)
    return observed, optimistic, frontier, samples, (first, incoming), (second, (1., 0.)), side


@pytest.mark.parametrize("status", ["established", "conditional", "unknown", "invalid", "not_available"])
@pytest.mark.parametrize("turn_only", [False, True])
def test_off_path_side_status_gates_edges_and_turns(status, turn_only):
    """Only optimistic routing may cross unknown sides; failed sides retain their frontier."""
    observed, optimistic, frontier, samples, first, second, side = _support_fixture(status, turn_only=turn_only)
    assert observed.has_edge(first, second) is (status in {"established", "conditional"})
    assert optimistic.has_edge(first, second) is (status in {"established", "conditional", "unknown"})
    assert side not in frontier
    failures = kernel._component_failure_cells(frontier, samples)
    assert (side in failures[first[0]]) is (status in {"invalid", "not_available"})
    if status in {"established", "conditional", "unknown"}:
        graph = optimistic if status == "unknown" else observed
        access = {first: dict(offset=0., access_key="source")}
        distances, best, unknown = kernel._recover_source(graph, access, samples, status == "unknown")
        route = kernel._target_route(graph, {second: dict(offset=0., access_key="target")}, access,
                                     distances, best, unknown, samples, status == "unknown")
        assert side in route["support_cell_keys"] == route["clearance"]["support_cell_keys"]
        assert samples[side]["query_ref"] in route["support_query_refs"]
        assert route["conditional_support_cell_count"] == (status == "conditional")
        assert (side in route["unknown_support_cells"]) is (status == "unknown")
        assert route["has_unknown_tie"] is (status == "unknown")


def test_established_sides_are_materialized_beyond_the_screening_radius():
    """The all-established fast path still publishes complete physical side evidence."""
    observed, _, _, samples, first, second, side = _support_fixture()
    assert observed[first][second]["clearance"]["side_sample_cell_keys"] == ()
    witness = kernel._materialize_clearance(observed, first, second)
    record = witness["clearance"]
    assert side in record["side_sample_cell_keys"]
    assert (0, 2) in record["side_sample_cell_keys"]
    assert tuple(samples[cell]["query_ref"] for cell in record["side_sample_cell_keys"]) == record["side_sample_query_refs"]
    assert set(record["side_sample_statuses"]) == {"established"}


def test_side_sweeps_stop_at_the_first_hit_and_exclude_terminal_only_cells():
    """A coarse occupied hit-cell contributes its free portion, while cells behind it do not."""
    grid = GridDescriptor("occluded-side", "plane", (0, 0), 1., 5, 5)
    domain, blocker = box(0, 0, 5, 5), box(1., 2.8, 3., 3.2)
    context = dict(grid=grid, domain=domain, index=kernel._build_clearance_index(blocker, domain))
    cells = kernel._side_sweep_cells(kernel._edge_side_sweep((1, 1), (1, 2), context), grid)
    assert (2, 1) in cells
    assert (3, 1) not in cells and (4, 1) not in cells
    terminal = kernel._side_sweep_cells(kernel.LineString(((1., .5), (1., 3.))), grid)
    assert {(row, col) for row in range(3) for col in (0, 1)} == set(terminal)
    assert all(row != 3 for row, _ in terminal)


def test_diagonal_side_sweep_includes_cells_outside_the_two_flanks():
    """A diagonal cross-section sweep has support far beyond its route and guard cells."""
    grid = GridDescriptor("diagonal-side", "plane", (0, 0), 1., 5, 5)
    domain = box(0, 0, 5, 5)
    context = dict(grid=grid, domain=domain, index=kernel._build_clearance_index(Polygon(), domain))
    cells = kernel._side_sweep_cells(kernel._edge_side_sweep((1, 1), (2, 2), context), grid)
    assert (3, 0) in cells
    assert (4, 4) not in cells


def test_unknown_side_tie_survives_selection_of_an_established_alternative():
    """A side-only unknown alternative participates in additive recovery and tie uncertainty."""
    a, b, c, d, side = (0, 0), (0, 1), (1, 0), (1, 1), (2, 2)
    graph = nx.Graph()
    graph.add_edge(a, b, weight=1., clearance={"side_sample_cell_keys": (side,)})
    graph.add_edge(b, d, weight=1.)
    graph.add_edge(a, c, weight=1.)
    graph.add_edge(c, d, weight=1.)
    samples = {cell: dict(status="unknown" if cell == side else "established") for cell in (a, b, c, d, side)}
    distances, best, unknown = kernel._recover_source(graph, {a: dict(offset=0., access_key="source")}, samples, True)
    assert distances[d] == 2.
    assert best[d][-1] == (a, c, d)
    assert best[d][0] == 0 and unknown[d]
