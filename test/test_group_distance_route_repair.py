"""Focused checks for route-first directional-clearance repair."""

from dataclasses import replace
import json
from types import SimpleNamespace

from features import group_distance as kernel
from features.group_distance import GridDescriptor
import networkx as nx
import pytest

from features.group_distance_repair import (
    _access_route_candidates, _checkpoint_fingerprint, _checkpoint_matches,
    _clearance_context, check_path, global_repair_result)


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


def test_global_source_cli_uses_owner_clearance_defaults_and_overrides():
    """The external entry resolves package defaults without copying constants."""
    from scripts.design.group_level.run_group_distance_global_source import (
        build_parser, resolve_clearance_cli_parameters)
    from features.group_distance_evidence_package import GROUP_DISTANCE_CLEARANCE_SCHEMA

    base = ["--input-bundle", "input.json", "--baseline-run-dir", "baseline",
            "--output-dir", "result", "--source-index", "0"]
    default = resolve_clearance_cli_parameters(build_parser().parse_args(base))
    assert default.parameter_fingerprint == GROUP_DISTANCE_CLEARANCE_SCHEMA.resolve().parameter_fingerprint
    changed = resolve_clearance_cli_parameters(build_parser().parse_args(
        base + ["--min-left-m", "0.3", "--min-total-m", "0.8"]))
    assert changed.effective_parameters["min_left_m"] == 0.3
    assert changed.effective_parameters["min_total_m"] == 0.8
    assert changed.parameter_sources["min_left_m"] == "cli"
    with pytest.raises((TypeError, ValueError)):
        resolve_clearance_cli_parameters(build_parser().parse_args(
            base + ["--min-left-m", "nan"]))


def test_checkpoint_fingerprint_changes_with_policy_input_and_method(monkeypatch):
    """Checkpoint identity binds real computation inputs independently of its path."""
    from features import group_distance_repair as repair
    from .test_group_distance import _missing_bundle

    bundle = _missing_bundle()
    baseline = {"observations": [{"group_ids": ["a", "b"]}]}
    policy = {"min_left_m": 0.225, "min_right_m": 0.225, "min_total_m": 0.55}
    first = repair._checkpoint_fingerprint(bundle, baseline, policy)
    assert repair._checkpoint_fingerprint(bundle, baseline, dict(policy)) == first
    changed_policy = {**policy, "min_total_m": 0.8}
    assert repair._checkpoint_fingerprint(bundle, baseline, changed_policy) != first
    changed_input = replace(bundle, source_identity={"id": "other-source"})
    assert repair._checkpoint_fingerprint(changed_input, baseline, policy) != first
    changed_pairs = {"observations": [{"group_ids": ["a", "c"]}]}
    assert repair._checkpoint_fingerprint(bundle, changed_pairs, policy) != first
    monkeypatch.setattr(repair, "GLOBAL_METHOD_VERSION", "changed-method")
    assert repair._checkpoint_fingerprint(bundle, baseline, policy) != first


def test_unbound_or_foreign_checkpoint_never_marks_source_complete():
    """A retained old JSON file cannot silently skip the current source search."""
    from features import group_distance_repair as repair

    unbound = {"source_index": 0, "source_id": "a", "results": []}
    assert not repair._checkpoint_matches(
        unbound, fingerprint="current", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))
    policy = {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5}
    context = repair._clearance_context(_bundle(), policy)
    cells = ((1, 1), (1, 2))
    route = {"value": 1.0, "cell_keys": cells,
             "state_keys": ((cells[0], None), (cells[1], (1.0, 0.0))),
             "source_access": {"free_cell": cells[0], "offset": 0.0},
             "target_access": {"free_cell": cells[1], "offset": 0.0}}
    exact = repair._exact_path(cells, context)
    assert exact["passed"]
    bound = {**unbound, "schema": "directional-repair-checkpoint/1",
             "checkpoint_fingerprint": "current", "results": [
                 {"key": ["a", "b"], "route": route, "exact": exact}]}
    assert repair._checkpoint_matches(
        bound, fingerprint="current", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        bound, fingerprint="changed-policy", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        {**bound, "results": []}, fingerprint="current", source_index=0,
        source_id="a", wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        {**bound, "results": bound["results"] * 2}, fingerprint="current",
        source_index=0, source_id="a", wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        {**bound, "source_index": True}, fingerprint="current", source_index=0,
        source_id="a", wanted_pairs=(("a", "b"),))


def test_global_checkpoint_guard_controls_actual_source_search(tmp_path, monkeypatch):
    """Only complete, matching receipts skip a source after policy changes."""
    from features import group_distance_repair as repair
    from .test_group_distance import _missing_bundle

    geometry = _bundle()
    original = _missing_bundle()
    bundle = replace(original, grid=geometry.grid, domain=geometry.domain,
                     physical_occupancy=())
    source, target = (group.group_id for group in bundle.groups[:2])
    baseline = {"observations": [{"group_ids": [source, target]}]}
    policy = {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5}
    cells = ((1, 1), (1, 2))
    access = {"free_cell": cells[0], "offset": 0.0}
    calls = []
    monkeypatch.setattr(repair.kernel, "_graphs",
                        lambda *args: ({}, nx.Graph(), nx.Graph(), {}))
    monkeypatch.setattr(repair, "_access_candidates_for_group",
                        lambda *args: (access,))

    def search(graph, source_accesses, target_accesses, context):
        """Return one fully shaped route without invoking a graph search."""
        calls.append(tuple(context["thresholds"]))
        return {target: {"value": 1.0, "cell_keys": cells,
                         "state_keys": ((cells[0], None), (cells[1], (1.0, 0.0))),
                         "source_access": access, "target_access": access}}

    monkeypatch.setattr(repair, "_global_source_search", search)
    old = tmp_path / "source_000.json"
    old.write_text(json.dumps({"source_index": 0, "source_id": source,
                               "results": []}), encoding="utf-8")
    retained = old.read_bytes()
    repair.global_repair_result(bundle, baseline, policy, checkpoint_dir=tmp_path)
    assert len(calls) == 1 and old.read_bytes() == retained
    repair.global_repair_result(bundle, baseline, policy, checkpoint_dir=tmp_path)
    assert len(calls) == 1 and old.read_bytes() == retained
    repair.global_repair_result(bundle, baseline,
                                {**policy, "min_total_m": .8}, checkpoint_dir=tmp_path)
    assert len(calls) == 2 and old.read_bytes() == retained


@pytest.mark.parametrize("damage", [
    "cell", "cell_boolean", "state", "state_cell", "state_heading",
    "source_access", "target_offset", "access_cell", "edge_witnesses",
    "edge_measurement", "turn_witness", "minimum", "minimum_boolean",
    "minimum_missing", "minimum_disagrees", "failure", "failure_cell", "pair",
])
def test_matching_checkpoint_rejects_malformed_assembly_fields(damage):
    """A matching fingerprint cannot turn malformed nested route evidence into completion."""
    from features import group_distance_repair as repair

    cells = ((1, 1), (1, 2))
    context = repair._clearance_context(
        _bundle(), {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5})
    exact = repair._exact_path(cells, context)
    assert exact["passed"] is True and exact["edge_witnesses"]
    route = {
        "value": 1.0, "cell_keys": cells,
        "state_keys": ((cells[0], None), (cells[1], (1.0, 0.0))),
        "source_access": {"free_cell": cells[0], "offset": 0.0},
        "target_access": {"free_cell": cells[1], "offset": 0.0},
    }
    payload = json.loads(json.dumps({
        "schema": repair.CHECKPOINT_SCHEMA,
        "checkpoint_fingerprint": "current",
        "source_index": 0, "source_id": "a",
        "results": [{"key": ["a", "b"], "route": route, "exact": exact}],
    }))
    assert repair._checkpoint_matches(
        payload, fingerprint="current", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))
    item = payload["results"][0]
    route, exact = item["route"], item["exact"]
    if damage == "cell":
        route["cell_keys"] = [None]
    elif damage == "cell_boolean":
        route["cell_keys"][0][0] = True
    elif damage == "state":
        route["state_keys"] = [None]
    elif damage == "state_cell":
        route["state_keys"][0][0] = [0, 0]
    elif damage == "state_heading":
        route["state_keys"][1][1] = [True, 0.0]
    elif damage == "source_access":
        route["source_access"] = {}
    elif damage == "target_offset":
        route["target_access"]["offset"] = True
    elif damage == "access_cell":
        route["target_access"]["free_cell"] = [None, 1]
    elif damage == "edge_witnesses":
        exact["edge_witnesses"] = None
    elif damage == "edge_measurement":
        exact["edge_witnesses"][0]["min_left_m"] = True
    elif damage == "turn_witness":
        exact["turn_witnesses"] = [None]
    elif damage == "minimum":
        exact["minimum_m"] = None
    elif damage == "minimum_boolean":
        exact["minimum_m"]["left"] = True
    elif damage == "minimum_missing":
        exact["minimum_m"] = {"left": None, "right": None, "total": None}
    elif damage == "minimum_disagrees":
        exact["minimum_m"]["left"] += 1.0
    elif damage == "failure":
        item["exact"] = {"passed": False, "failure": {}}
    elif damage == "failure_cell":
        item["exact"] = {
            "passed": False,
            "failure": {"kind": "edge", "from": None, "to": [1, 2]},
        }
    else:
        item["key"] = [["a"], "b"]
    assert not repair._checkpoint_matches(
        payload, fingerprint="current", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))


def test_checkpoint_retention_failure_prevents_original_replacement(tmp_path, monkeypatch):
    """Publication must fail when rejected bytes cannot be retained."""
    from pathlib import Path
    from features import group_distance_repair as repair

    checkpoint = tmp_path / "source_000-current.json"
    original = b'{"source_index":0,"results":[null]}'
    checkpoint.write_bytes(original)
    replace_path = Path.replace
    attempts = []

    def refuse_retention(path, destination):
        """Refuse both retention attempts while allowing any accidental final replacement."""
        if path == checkpoint:
            attempts.append(destination)
            raise OSError("rejected retention refused")
        return replace_path(path, destination)

    monkeypatch.setattr(Path, "replace", refuse_retention)
    with pytest.raises(OSError):
        repair._write_checkpoint(
            tmp_path, 0, "a", "current", (("a", "b"),), [])
    assert attempts
    assert checkpoint.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))
