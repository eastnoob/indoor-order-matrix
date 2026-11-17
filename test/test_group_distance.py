"""Nonspatial contract checks; real geometry and route acceptance use pinned IFC/S4."""

from dataclasses import FrozenInstanceError, replace
from itertools import permutations
import json
from pathlib import Path

import networkx as nx
import pytest

from features import group_distance as kernel
from features.field_core import FieldQuery
from features.group_distance import (
    GridDescriptor, GroupDistanceInput, GroupProjection, _analysis_plane_binding_error, _arithmetic,
    _recover_source, _target_route, calculate_group_pair_distances,
    group_distance_input_fingerprints, serialize_group_distance_result,
)


def _missing_bundle():
    """Provide identities with explicitly missing geometry, without inventing a layout."""
    return GroupDistanceInput(
        source_identity={"id": "contract-only-source"}, analysis_plane=None, domain=None,
        grid=GridDescriptor("contract-grid", "contract-frame", (0, 0), 1, 1, 1),
        groups=tuple(GroupProjection(identity, None, ("source:" + identity,), "not_available") for identity in ("c", "a", "b")),
        physical_occupancy=None, unresolved_source_ids=(), unresolved_supports={},
        query=FieldQuery("contract-domain", "contract-frame"),
        query_context={"domain_id": "contract-domain", "frame": "contract-frame", "plane": None, "height_band": None, "demand": None},
        origin_offset=(0, 0), dependency_fingerprints={},
    )


def _abstract_graph(edges, states):
    """Construct only a symbolic weighted graph, with no spatial geometry or furniture."""
    graph = nx.Graph()
    for first, second in edges:
        graph.add_edge(first, second, weight=0.25)
    samples = {node: {"status": states.get(node, "established"), "center": None} for node in graph}
    source = min(graph)
    access = {source: {"offset": 0.125, "access_key": ("abstract-group", source)}}
    return graph, samples, access


def test_frozen_records_detach_nested_inputs():
    """Caller edits cannot rewrite an already issued query or result identity."""
    refs = [{"source_id": "a"}]
    group = GroupProjection("a", None, refs, "not_available")
    refs[0]["source_id"] = "changed"
    assert group.source_refs[0]["source_id"] == "a"
    with pytest.raises(TypeError):
        group.source_refs[0]["source_id"] = "changed"
    with pytest.raises(FrozenInstanceError):
        group.group_id = "changed"


def test_route_indexes_include_diagonals_but_access_indexes_keep_shared_edges():
    """Index-only adjacency distinguishes routing from footprint edge interfaces."""
    grid = GridDescriptor("index-contract", "index-frame", (0, 0), 1, 3, 3)
    assert kernel._neighbors((1, 1), grid) == ((0, 1), (1, 0), (1, 2), (2, 1))
    assert kernel._route_neighbors((1, 1), grid) == (
        (0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2))
    assert kernel._route_neighbors((0, 0), grid) == ((0, 1), (1, 0), (1, 1))


def test_missing_input_preserves_complete_pair_scope_and_null_values():
    """An unavailable input still emits each unordered pair exactly once."""
    result = calculate_group_pair_distances(_missing_bundle())
    payload = serialize_group_distance_result(result)
    assert payload["group_ids"] == ["a", "b", "c"]
    assert [row["group_ids"] for row in payload["pair_index"]] == [["a", "b"], ["a", "c"], ["b", "c"]]
    assert len({row["pair_id"] for row in payload["pair_index"]}) == 3
    for observation in payload["observations"]:
        for channel in ("center_to_center_euclidean", "centroid_free_space_hybrid"):
            assert observation[channel]["status"] == "not_available"
            assert observation[channel]["value"] is None
        assert observation["route"] is None
    json.dumps(payload, allow_nan=False)


def test_input_fingerprints_and_pair_identity_ignore_record_order():
    """Canonical record order remains stable while changed source content invalidates identity."""
    first = _missing_bundle()
    second = replace(first, groups=tuple(reversed(first.groups)))
    assert group_distance_input_fingerprints(first) == group_distance_input_fingerprints(second)
    first_ids = calculate_group_pair_distances(first).manifest["expected_pair_ids"]
    assert first_ids == calculate_group_pair_distances(second).manifest["expected_pair_ids"]
    changed = replace(first, source_identity={"id": "different-source"})
    assert group_distance_input_fingerprints(first)["source"] != group_distance_input_fingerprints(changed)["source"]
    assert first_ids != calculate_group_pair_distances(changed).manifest["expected_pair_ids"]
    shifted = replace(first, origin_offset=(3, 4))
    assert group_distance_input_fingerprints(first)["query"] != group_distance_input_fingerprints(shifted)["query"]
    malformed_offset = replace(first, origin_offset=(0,))
    assert calculate_group_pair_distances(malformed_offset).diagnostics["global_status"] == "invalid"


def test_malformed_occupancy_metadata_preserves_invalid_pair_scope():
    """Malformed record metadata invalidates hybrid queries without losing pair observations."""
    baseline = calculate_group_pair_distances(_missing_bundle())
    malformed = replace(_missing_bundle(), physical_occupancy=(1,))
    result = calculate_group_pair_distances(malformed)
    assert result.manifest["expected_pair_ids"] == baseline.manifest["expected_pair_ids"]
    assert len(result.observations) == 3
    for observation, original in zip(result.observations, baseline.observations, strict=True):
        assert observation.centroid_free_space_hybrid["status"] == "invalid"
        assert observation.centroid_free_space_hybrid["value"] is None
        assert observation.center_to_center_euclidean == original.center_to_center_euclidean
        assert observation.route is None
    assert "physical_occupancy" in result.diagnostics["global_explanation"]
    json.dumps(serialize_group_distance_result(result), allow_nan=False)


def test_retained_camera_plane_requires_explicit_query_context_binding():
    """Real S4 plane metadata binds by fingerprint; canonical planes need no invented frame field."""
    manifest_path = Path(__file__).resolve().parents[1] / "outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/s4_confirmed_manifest.json"
    if not manifest_path.exists():
        pytest.skip("retained historical S4 plane metadata is not installed")
    plane = json.loads(manifest_path.read_text(encoding="utf-8"))["analysis_plane"]
    bundle = replace(_missing_bundle(), analysis_plane=plane)
    original = group_distance_input_fingerprints(bundle)
    assert "fingerprint binding" in _analysis_plane_binding_error(bundle, original)
    bound = replace(bundle, query_context={**bundle.query_context, "analysis_plane_fingerprint": original["analysis_plane"]})
    fingerprints = group_distance_input_fingerprints(bound)
    assert fingerprints["query"] != original["query"]
    assert _analysis_plane_binding_error(bound, fingerprints) is None
    mismatch = replace(bound, query_context={**bound.query_context, "analysis_plane_fingerprint": "different-plane"})
    assert "fingerprint binding" in _analysis_plane_binding_error(mismatch, group_distance_input_fingerprints(mismatch))
    explicit_wrong_frame = replace(bound, analysis_plane={**plane, "frame": "different-frame"})
    wrong_fingerprints = group_distance_input_fingerprints(explicit_wrong_frame)
    explicit_wrong_frame = replace(explicit_wrong_frame, query_context={**bound.query_context, "analysis_plane_fingerprint": wrong_fingerprints["analysis_plane"]})
    assert "frame" in _analysis_plane_binding_error(explicit_wrong_frame, group_distance_input_fingerprints(explicit_wrong_frame))


def test_duplicate_group_identity_rejected_without_silent_pair_loss():
    """Duplicate node identities are malformed input rather than a smaller pair scope."""
    bundle = _missing_bundle()
    with pytest.raises(ValueError, match="unique"):
        calculate_group_pair_distances(replace(bundle, groups=(bundle.groups[0], bundle.groups[0])))


@pytest.mark.parametrize("mode,states,expected_middle", [
    (False, {}, (0, 1)),
    (False, {(0, 1): "conditional"}, (1, 0)),
    (True, {(0, 1): "unknown"}, (1, 0)),
])
def test_exact_tight_recovery_is_insertion_order_independent(mode, states, expected_middle):
    """Every edge permutation obeys count, source access and complete-path ordering."""
    start, left, right, end = (0, 0), (0, 1), (1, 0), (1, 1)
    edges = ((start, left), (left, end), (start, right), (right, end))
    for order in permutations(edges):
        graph, samples, accesses = _abstract_graph(order, states)
        distances, best, unknown = _recover_source(graph, accesses, samples, mode)
        assert best[end][-1] == (start, expected_middle, end)
        assert best[end][0:2] == (0, 0)
        assert distances[end] == 0.625
        assert "virtual-source" not in graph
        assert unknown[end] is bool(mode and states)


def test_source_access_precedes_complete_path_for_exact_backend_ties():
    """Virtual-source offsets retain the stable AccessKey when scalar costs tie."""
    a, b, target = (0, 0), (0, 1), (0, 2)
    graph, samples, _ = _abstract_graph(((a, target), (b, target)), {})
    accesses = {a: {"offset": 0.125, "access_key": ("z", a)}, b: {"offset": 0.125, "access_key": ("a", b)}}
    _, best, _ = _recover_source(graph, accesses, samples, False)
    assert best[target][2] == accesses[b]["access_key"]
    assert best[target][-1] == (b, target)


def test_unknown_tie_witness_survives_known_representative_selection():
    """A known canonical route does not erase an exactly tied unknown alternative."""
    a, b, c, d = (0, 0), (0, 1), (1, 0), (1, 1)
    graph, samples, accesses = _abstract_graph(((a, b), (b, d), (a, c), (c, d)), {b: "unknown"})
    for node, sample in samples.items():
        sample.update(query_ref=str(node), source_refs=())
    distances, best, unknown = _recover_source(graph, accesses, samples, True)
    route = _target_route(graph, {d: {"offset": 0.125, "access_key": ("target", d)}}, accesses,
                          distances, best, unknown, samples, True)
    assert route["unknown_cell_count"] == 0
    assert route["has_unknown_tie"] is True
    assert route["cell_keys"] == (a, c, d)


@pytest.mark.parametrize("state,mode,position", [("conditional", False, 1), ("unknown", True, 0)])
def test_guard_occurrences_rank_compositionally_and_keep_distinct_support(state, mode, position):
    """Symbolic guard support ranks per edge occurrence while evidence remains distinct."""
    a, b, c, target, guard = (0, 0), (0, 1), (1, 0), (1, 1), (2, 0)
    graph, samples, accesses = _abstract_graph(((a, b), (b, target), (a, c), (c, target)), {})
    samples[guard] = {"status": state, "center": None}
    graph[a][b]["guard_cell_keys"] = (guard,)
    graph[b][target]["guard_cell_keys"] = (guard,)
    graph[a][c]["guard_cell_keys"] = (guard,)
    for node, sample in samples.items():
        sample.update(query_ref=str(node), source_refs=())
    distances, best, unknown = _recover_source(graph, accesses, samples, mode)
    assert best[target][position] == 1
    assert best[target][-1] == (a, c, target)
    route = _target_route(graph, {target: {"offset": .125, "access_key": ("target", target)}},
                          accesses, distances, best, unknown, samples, mode)
    assert route[state + "_cell_count"] == 0
    assert route[state + "_support_occurrence_count"] == 1
    assert route["guard_cell_keys"] == (guard,)
    assert route["guard_query_refs"] == (samples[guard]["query_ref"],)
    assert route["support_cell_keys"] == tuple(sorted((a, c, target, guard)))
    assert route["has_unknown_tie"] is (state == "unknown")


def test_unknown_guard_tie_remains_visible_when_known_route_is_selected():
    """A guard-only unknown alternative cannot vanish behind a known representative."""
    a, b, c, end, guard = (0, 0), (0, 1), (1, 0), (1, 1), (2, 0)
    graph, samples, accesses = _abstract_graph(((a, b), (b, end), (a, c), (c, end)), {})
    samples[guard] = {"status": "unknown", "center": None, "query_ref": "guard"}
    graph[a][b]["guard_cell_keys"] = (guard,)
    for node, sample in samples.items():
        sample.update(query_ref=str(node), source_refs=())
    distances, best, unknown = _recover_source(graph, accesses, samples, True)
    route = _target_route(graph, {end: {"offset": .125, "access_key": ("target", end)}},
                          accesses, distances, best, unknown, samples, True)
    assert route["cell_keys"] == (a, c, end)
    assert route["unknown_support_occurrence_count"] == 0
    assert route["has_unknown_tie"] is True


def test_frontier_includes_failed_edge_guard_without_its_cardinal_connection():
    """A symbolic edge dependency survives even when its guard is another component."""
    a, b, guard, unrelated = (0, 0), (1, 1), (0, 1), (9, 9)
    graph = nx.Graph()
    graph.add_edge(a, b, guard_cell_keys=(guard,))
    graph.add_nodes_from((guard, unrelated))
    samples = {a: {"status": "established"}, b: {"status": "established"},
               guard: {"status": "invalid"}, unrelated: {"status": "not_available"}}
    failures = kernel._component_failure_cells(graph, samples)
    assert failures[a] == failures[b] == (guard,)
    assert failures[unrelated] == (unrelated,)


def test_non_increasing_binary64_physical_edge_fails_search():
    """An unrepresentable positive increment is an explicit numerical failure."""
    graph, samples, accesses = _abstract_graph((((0, 0), (0, 1)),), {})
    accesses[(0, 0)]["offset"] = float(2 ** 53)
    with pytest.raises(ArithmeticError, match="strictly increase"):
        _recover_source(graph, accesses, samples, False)
    assert "virtual-source" not in graph


def test_binary64_reassociation_residual_is_reported_without_changing_label():
    """Exact backend replay and regrouped component sums have distinct contracts."""
    source, weights, target = 0.1, (0.2, 0.3), 0.0
    label = source
    for weight in weights:
        label += weight
    label += target
    arithmetic = _arithmetic(source, weights, target, label)
    assert arithmetic["backend_hybrid_label"] == label
    assert arithmetic["backend_replay"] == label
    assert arithmetic["residual"] == label - ((source + sum(weights)) + target)
    assert arithmetic["residual"] != 0.0
    assert abs(arithmetic["residual"]) <= arithmetic["rounding_bound"]
    with pytest.raises(ArithmeticError, match="replay"):
        _arithmetic(source, weights, target, label + 1.0)
