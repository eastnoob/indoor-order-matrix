"""Route-first directional-clearance repair over an existing group-distance result.

The ordinary eight-neighbor result is used as a fast candidate.  Directional
clearance is then checked only on that route and a small local set of alternate
routes.  This module deliberately keeps the full constrained kernel separate:
an accepted route is exact for that route, while a search-budget miss is
reported as unresolved rather than as a proof of global unreachability.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
import heapq
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import networkx as nx
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from . import group_distance as kernel


METHOD_VERSION = "route-first-lazy-exact/1"
SCHEMA_VERSION = "route-repair/1"
GLOBAL_METHOD_VERSION = "global-directional-lazy-exact/1"


def _tuple_cell(value: Any) -> tuple[int, int]:
    """Normalize a serialized lattice cell to the tuple used by the kernel."""
    return int(value[0]), int(value[1])


def _clearance_context(bundle: Any, policy: Mapping[str, float]) -> dict:
    """Build one shared exact geometry context for all route checks."""
    thresholds = kernel._clearance_thresholds(policy)
    domain = kernel._shape(bundle.domain["components"])
    blockers = unary_union(
        [kernel._shape(record["geometry_components"])
         for record in bundle.physical_occupancy if record.get("geometry_components")]
    )
    return {
        "bundle": bundle,
        "domain": domain,
        "blockers": blockers,
        "index": kernel._build_clearance_index(blockers, domain),
        "thresholds": thresholds,
        "edge_cache": {},
        "turn_cache": {},
        "exact_edge_cache": {},
        "exact_turn_cache": {},
        "rejected_edges": set(),
        "checks": {"edges": 0, "turns": 0},
    }


def _path_headings(path: tuple[tuple[int, int], ...], grid: Any) -> tuple[tuple[float, float], ...]:
    """Return the positive-length heading for every path edge."""
    return tuple(kernel._heading(kernel._center(first, grid), kernel._center(second, grid))
                 for first, second in pairwise(path))


def _access_heading(access: Mapping[str, Any] | None, grid: Any, *, target: bool = False):
    """Read or derive the direction of the segment between a footprint and free cell."""
    if not access:
        return None
    key = "target_heading" if target else "heading"
    if access.get(key):
        return tuple(access[key])
    footprint, free = access.get("footprint_cell"), access.get("free_cell")
    if footprint is None or free is None:
        return None
    first, second = (free, footprint) if target else (footprint, free)
    return kernel._heading(kernel._center(tuple(first), grid), kernel._center(tuple(second), grid))


def check_path(path: tuple[tuple[int, int], ...], context: dict,
               source_access: Mapping[str, Any] | None = None,
               target_access: Mapping[str, Any] | None = None) -> dict:
    """Check lattice edges, internal turns and turns at both furniture interfaces."""
    grid = context["bundle"].grid
    blockers, domain = context["blockers"], context["domain"]
    thresholds, index = context["thresholds"], context["index"]
    edges, turns = [], []
    screened_edges, screened_turns = 0, 0
    def check_turn(cell: tuple[int, int], incoming: tuple[float, float], outgoing: tuple[float, float],
                   failure: dict) -> dict | None:
        """Use the screen first, then exact geometry for ambiguous interface turns."""
        key = ("turn", cell, incoming, outgoing)
        if key not in context["turn_cache"]:
            context["checks"]["turns"] += 1
            screen = kernel._turn_clearance(
                kernel._center(cell, grid), incoming, outgoing, blockers, domain, thresholds,
                max_distance=max(thresholds), index=index, screen_only=True)
            context["turn_cache"][key] = ("screen", screen) if screen == {} else (
                "exact", kernel._turn_clearance(kernel._center(cell, grid), incoming, outgoing,
                                                 blockers, domain, thresholds, index=index))
        kind, witness = context["turn_cache"][key]
        if witness is None:
            return {"passed": False, "failure": failure, "edge_witnesses": tuple(edges),
                    "turn_witnesses": tuple(turns)}
        if kind == "screen":
            nonlocal screened_turns
            screened_turns += 1
        else:
            turns.append(witness)
        return None

    if len(path) > 1:
        headings = _path_headings(path, grid)
        for first, second, heading in zip(path, path[1:], headings):
            key = first, second
            if key not in context["edge_cache"]:
                context["checks"]["edges"] += 1
                screen = kernel._edge_clearance(
                    first, second, grid, blockers, domain, thresholds,
                    max_distance=max(thresholds), index=index, screen_only=True)
                context["edge_cache"][key] = ("screen", screen) if screen == {} else (
                    "exact", kernel._edge_clearance(first, second, grid, blockers, domain, thresholds, index=index))
            kind, witness = context["edge_cache"][key]
            if witness is None:
                context["rejected_edges"].add(key)
                return {"passed": False, "failure": {"kind": "edge", "from": first, "to": second},
                        "edge_witnesses": tuple(edges), "turn_witnesses": tuple(turns)}
            if kind == "screen":
                screened_edges += 1
            else:
                edges.append(witness)
        for index_in_path, (first, middle, last) in enumerate(zip(path, path[1:], path[2:])):
            turn_key = first, middle, last
            if turn_key not in context["turn_cache"]:
                context["checks"]["turns"] += 1
                screen = kernel._turn_clearance(
                    kernel._center(middle, grid), headings[index_in_path], headings[index_in_path + 1],
                    blockers, domain, thresholds, max_distance=max(thresholds), index=index, screen_only=True)
                context["turn_cache"][turn_key] = ("screen", screen) if screen == {} else (
                    "exact", kernel._turn_clearance(kernel._center(middle, grid), headings[index_in_path],
                                                     headings[index_in_path + 1], blockers, domain, thresholds,
                                                     index=index))
            kind, witness = context["turn_cache"][turn_key]
            if witness is None:
                return {"passed": False, "failure": {"kind": "turn", "from": first,
                                                         "at": middle, "to": last},
                        "edge_witnesses": tuple(edges), "turn_witnesses": tuple(turns)}
            if kind == "screen":
                screened_turns += 1
            else:
                turns.append(witness)
        source_heading = _access_heading(source_access, grid)
        if source_heading:
            heading = source_heading
            failure = {"kind": "turn", "from": tuple(source_access["footprint_cell"]),
                       "at": path[0], "to": path[1], "endpoint": "source"}
            failed = check_turn(path[0], heading, headings[0], failure)
            if failed:
                return failed
        target_heading = _access_heading(target_access, grid, target=True)
        if target_heading:
            heading = target_heading
            failure = {"kind": "turn", "from": path[-2], "at": path[-1],
                       "to": tuple(target_access["footprint_cell"]), "endpoint": "target"}
            failed = check_turn(path[-1], headings[-1], heading, failure)
            if failed:
                return failed
    elif len(path) == 1 and source_access and target_access:
        source_heading = _access_heading(source_access, grid)
        target_heading = _access_heading(target_access, grid, target=True)
        if source_heading and target_heading:
            failure = {"kind": "turn", "from": tuple(source_access["footprint_cell"]),
                       "at": path[0], "to": tuple(target_access["footprint_cell"]), "endpoint": "both"}
            failed = check_turn(path[0], source_heading, target_heading, failure)
            if failed:
                return failed
    witnesses = tuple(edges) + tuple(turns)
    if witnesses:
        minimum = {
            name: min(record[f"min_{name}_m"] for record in witnesses)
            for name in ("left", "right", "total")
        }
    else:
        minimum = {"left": None, "right": None, "total": None}
    return {"passed": True, "failure": None, "edge_witnesses": tuple(edges),
            "turn_witnesses": tuple(turns), "minimum_m": minimum,
            "screened_edges": screened_edges, "screened_turns": screened_turns}


def _exact_path(path: tuple[tuple[int, int], ...], context: dict,
                source_access: Mapping[str, Any] | None = None,
                target_access: Mapping[str, Any] | None = None) -> dict:
    """Recheck a selected route and its interface turns with uncapped witnesses."""
    grid = context["bundle"].grid
    blockers, domain = context["blockers"], context["domain"]
    thresholds, index = context["thresholds"], context["index"]
    edges, turns = [], []
    headings = _path_headings(path, grid)
    for first, second in pairwise(path):
        key = ("exact", first, second)
        if key not in context["exact_edge_cache"]:
            context["checks"]["exact_edges"] = context["checks"].get("exact_edges", 0) + 1
            context["exact_edge_cache"][key] = kernel._edge_clearance(
                first, second, grid, blockers, domain, thresholds, index=index)
        witness = context["exact_edge_cache"][key]
        if witness is None:
            return {"passed": False, "failure": {"kind": "edge", "from": first, "to": second},
                    "edge_witnesses": tuple(edges), "turn_witnesses": tuple(turns)}
        edges.append(witness)
    for index_in_path, (first, middle, last) in enumerate(zip(path, path[1:], path[2:])):
        key = ("exact", first, middle, last)
        if key not in context["exact_turn_cache"]:
            context["checks"]["exact_turns"] = context["checks"].get("exact_turns", 0) + 1
            context["exact_turn_cache"][key] = kernel._turn_clearance(
                kernel._center(middle, grid), headings[index_in_path], headings[index_in_path + 1],
                blockers, domain, thresholds, index=index)
        witness = context["exact_turn_cache"][key]
        if witness is None:
            return {"passed": False, "failure": {"kind": "turn", "from": first,
                                                     "at": middle, "to": last},
                    "edge_witnesses": tuple(edges), "turn_witnesses": tuple(turns)}
        turns.append(witness)
    endpoint_turns = []
    source_heading = _access_heading(source_access, grid)
    target_heading = _access_heading(target_access, grid, target=True)
    if len(path) > 1 and source_heading:
        endpoint_turns.append((path[0], source_heading, headings[0],
                               {"kind": "turn", "from": tuple(source_access["footprint_cell"]),
                                "at": path[0], "to": path[1], "endpoint": "source"}))
    if len(path) > 1 and target_heading:
        endpoint_turns.append((path[-1], headings[-1], target_heading,
                               {"kind": "turn", "from": path[-2], "at": path[-1],
                                "to": tuple(target_access["footprint_cell"]), "endpoint": "target"}))
    elif len(path) == 1 and source_access and target_access:
        source_heading = _access_heading(source_access, grid)
        target_heading = _access_heading(target_access, grid, target=True)
        if source_heading and target_heading:
            endpoint_turns.append((path[0], source_heading, target_heading,
                                   {"kind": "turn", "from": tuple(source_access["footprint_cell"]),
                                    "at": path[0], "to": tuple(target_access["footprint_cell"]),
                                    "endpoint": "both"}))
    for cell, incoming, outgoing, failure in endpoint_turns:
        key = ("exact-endpoint", cell, incoming, outgoing)
        if key not in context["exact_turn_cache"]:
            context["checks"]["exact_turns"] = context["checks"].get("exact_turns", 0) + 1
            context["exact_turn_cache"][key] = kernel._turn_clearance(
                kernel._center(cell, grid), incoming, outgoing, blockers, domain, thresholds, index=index)
        witness = context["exact_turn_cache"][key]
        if witness is None:
            return {"passed": False, "failure": failure, "edge_witnesses": tuple(edges),
                    "turn_witnesses": tuple(turns)}
        turns.append(witness)
    records = tuple(edges) + tuple(turns)
    return {"passed": True, "failure": None, "edge_witnesses": tuple(edges),
            "turn_witnesses": tuple(turns),
            "minimum_m": {name: min((record[f"min_{name}_m"] for record in records), default=None)
                          for name in ("left", "right", "total")}}


def _transition_ok(first: tuple[int, int], second: tuple[int, int], incoming: tuple[float, float] | None,
                   context: dict) -> bool:
    """Use cheap conservative screens and exact checks only for ambiguous transitions."""
    grid = context["bundle"].grid
    blockers, domain = context["blockers"], context["domain"]
    thresholds, index = context["thresholds"], context["index"]
    edge_key = first, second
    if edge_key not in context["edge_cache"]:
        context["checks"]["edges"] += 1
        screen = kernel._edge_clearance(first, second, grid, blockers, domain, thresholds,
                                        max_distance=max(thresholds), index=index, screen_only=True)
        context["edge_cache"][edge_key] = ("screen", screen) if screen == {} else (
            "exact", kernel._edge_clearance(first, second, grid, blockers, domain, thresholds, index=index))
    if context["edge_cache"][edge_key][1] is None:
        return False
    if incoming is None:
        return True
    outgoing = kernel._heading(kernel._center(first, grid), kernel._center(second, grid))
    turn_key = first, incoming, outgoing
    if turn_key not in context["turn_cache"]:
        context["checks"]["turns"] += 1
        screen = kernel._turn_clearance(kernel._center(first, grid), incoming, outgoing, blockers, domain,
                                        thresholds, max_distance=max(thresholds), index=index, screen_only=True)
        context["turn_cache"][turn_key] = ("screen", screen) if screen == {} else (
            "exact", kernel._turn_clearance(kernel._center(first, grid), incoming, outgoing,
                                             blockers, domain, thresholds, index=index))
    return context["turn_cache"][turn_key][1] is not None


def _transition_screen_ok(first: tuple[int, int], second: tuple[int, int],
                          incoming: tuple[float, float] | None, context: dict) -> bool:
    """Use the bounded screen as the global-search feasibility gate.

    The selected route is replayed with uncapped exact witnesses afterwards;
    doing exact geometry on every ambiguous search transition makes the global
    search repeat the expensive kernel for nearly every edge and turn.
    """
    grid = context["bundle"].grid
    blockers, domain = context["blockers"], context["domain"]
    thresholds, index = context["thresholds"], context["index"]
    edge_key = ("screen", first, second)
    if edge_key not in context["edge_cache"]:
        context["checks"]["edges"] += 1
        context["edge_cache"][edge_key] = kernel._edge_clearance(
            first, second, grid, blockers, domain, thresholds,
            max_distance=max(thresholds), index=index, screen_only=True)
    if context["edge_cache"][edge_key] is None:
        return False
    if incoming is None:
        return True
    outgoing = kernel._heading(kernel._center(first, grid), kernel._center(second, grid))
    turn_key = ("screen", first, incoming, outgoing)
    if turn_key not in context["turn_cache"]:
        context["checks"]["turns"] += 1
        context["turn_cache"][turn_key] = kernel._turn_clearance(
            kernel._center(first, grid), incoming, outgoing, blockers, domain, thresholds,
            max_distance=max(thresholds), index=index, screen_only=True)
    return context["turn_cache"][turn_key] is not None


def _route_distance(route: Mapping[str, Any], path: tuple[tuple[int, int], ...], grid: Any) -> float:
    """Recompose a candidate route distance using the retained endpoint offsets."""
    edge_sum = math.fsum(math.dist(kernel._center(first, grid), kernel._center(second, grid))
                         for first, second in pairwise(path))
    return float(route["source_access"]["offset"] + edge_sum + route["target_access"]["offset"])


def _corridor_graph(graph: nx.Graph, path: tuple[tuple[int, int], ...], grid: Any,
                    margin_cells: int) -> nx.Graph:
    """Restrict alternate search to a narrow corridor around the baseline route."""
    points = [kernel._center(cell, grid) for cell in path]
    line = LineString(points) if len(points) > 1 else Point(points[0])
    margin = margin_cells * grid.spacing
    nodes = [node for node in graph if line.distance(Point(kernel._center(node, grid))) <= margin]
    nodes.extend(path)
    return graph.subgraph(set(nodes)).copy()


def _alternate_paths(graph: nx.Graph, route: Mapping[str, Any], grid: Any,
                     margin_cells: int, budget: int, blocked_edges: set[tuple] | None = None,
                     blocked_turns: set[tuple] | None = None):
    """Yield bounded local alternatives with the same access endpoints."""
    baseline = tuple(_tuple_cell(cell) for cell in route["cell_keys"])
    if not baseline or baseline[0] not in graph or baseline[-1] not in graph:
        return
    corridor = _corridor_graph(graph, baseline, grid, margin_cells)
    blocked_edges = blocked_edges or set()
    blocked_turns = blocked_turns or set()
    corridor.remove_edges_from((first, second) for first, second in blocked_edges
                               if corridor.has_edge(first, second))
    source, target = "__route_source__", "__route_target__"
    corridor.add_node(source)
    corridor.add_node(target)
    corridor.add_edge(source, baseline[0], weight=float(route["source_access"]["offset"]))
    corridor.add_edge(baseline[-1], target, weight=float(route["target_access"]["offset"]))
    seen = 0
    try:
        paths = nx.shortest_simple_paths(corridor, source, target, weight="weight")
        for candidate in paths:
            cells = tuple(node for node in candidate if node not in {source, target})
            if cells == baseline:
                continue
            if any((first, second) in blocked_edges for first, second in pairwise(cells)):
                continue
            if any((first, middle, last) in blocked_turns for first, middle, last in zip(cells, cells[1:], cells[2:])):
                continue
            yield cells
            seen += 1
            if seen >= budget:
                return
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return


def _access_route_candidates(graph: nx.Graph, source_accesses: tuple[dict, ...],
                             target_accesses: tuple[dict, ...], budget: int,
                             blocked_edges: set[tuple] | None = None,
                             blocked_turns: set[tuple] | None = None,
                             blocked_access_keys: set[tuple] | None = None) -> tuple[dict, ...]:
    """Return bounded shortest routes across alternate furniture interfaces.

    A small number of source access cells is expanded with one Dijkstra run
    each, then target interfaces are ranked by the resulting total distance.
    This changes only the endpoint access; the route graph and exact clearance
    kernel remain the existing implementation.
    """
    if budget <= 0 or not source_accesses or not target_accesses:
        return ()
    blocked_edges = {(tuple(first), tuple(second)) for first, second in (blocked_edges or set())}
    blocked_turns = blocked_turns or set()
    blocked_access_keys = set(blocked_access_keys or set())
    directed = graph if graph.is_directed() else graph.to_directed()
    lattice_nodes = set(directed)
    source_limit = max(4, min(len(source_accesses), int(math.sqrt(max(1, budget) * 8))))
    target_limit = max(8, min(len(target_accesses), budget * 2))
    def group_accesses(accesses: tuple[dict, ...], limit: int) -> tuple[tuple[tuple[int, int], tuple[dict, ...]], ...]:
        """Keep alternate interface states while bounding distinct free cells."""
        by_cell: dict[tuple[int, int], list[dict]] = {}
        for access in accesses:
            if tuple(access["access_key"]) in blocked_access_keys:
                continue
            by_cell.setdefault(tuple(access["free_cell"]), []).append(access)
        ranked = sorted(by_cell.items(), key=lambda item: min(
            (float(access["offset"]), access["access_key"]) for access in item[1]))
        return tuple((cell, tuple(sorted(items, key=lambda access: (float(access["offset"]), access["access_key"]))))
                     for cell, items in ranked[:limit])

    source_groups = group_accesses(source_accesses, source_limit)
    target_groups = group_accesses(target_accesses, target_limit)
    if not source_groups or not target_groups:
        return ()
    graph_view = nx.subgraph_view(directed, filter_edge=lambda first, second: (first, second) not in blocked_edges)
    candidates = []
    for start, sources in source_groups:
        try:
            distances, paths = nx.single_source_dijkstra(graph_view, start, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        for end, targets in target_groups:
            if end not in distances:
                continue
            cells = tuple(paths[end])
            if any((first, middle, last) in blocked_turns
                   for first, middle, last in zip(cells, cells[1:], cells[2:])):
                continue
            for source in sources:
                for target in targets:
                    value = float(distances[end]) + float(source["offset"]) + float(target["offset"])
                    candidates.append((value, source["access_key"], target["access_key"],
                                      {"value": value, "cell_keys": cells,
                                       "source_access": source, "target_access": target}))
    selected = []
    seen = set()
    for _, _, _, route in sorted(candidates, key=lambda item: item[:3]):
        key = (route["source_access"]["access_key"], route["target_access"]["access_key"], route["cell_keys"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(route)
        if len(selected) >= budget:
            break
    return tuple(selected)


def _unconstrained_bundle(bundle: Any) -> Any:
    """Remove an accidental policy binding before using the ordinary graph."""
    if bundle.clearance_policy is None:
        return bundle
    context = dict(bundle.query_context)
    context.pop("clearance_policy", None)
    cleared = replace(bundle, clearance_policy=None, query_context=context, dependency_fingerprints={})
    return replace(cleared, dependency_fingerprints=kernel.group_distance_input_fingerprints(cleared))


def repair_result(bundle: Any, baseline: Mapping[str, Any], policy: Mapping[str, float], *,
                  candidate_budget: int = 4, corridor_margin_cells: int = 3,
                  pair_limit: int | None = None,
                  access_candidate_budget: int = 8) -> dict:
    """Repair ordinary routes with bounded local exact directional-clearance checks."""
    if candidate_budget < 0 or corridor_margin_cells < 0 or access_candidate_budget < 0:
        raise ValueError("candidate budgets and corridor_margin_cells must be nonnegative")
    ordinary = _unconstrained_bundle(bundle)
    context = _clearance_context(ordinary, policy)
    domain = context["domain"]
    observed = None
    access_graph = None
    samples = frontier = None
    if candidate_budget or access_candidate_budget:
        samples, observed, _, frontier = kernel._graphs(ordinary, domain)
        access_graph = observed.to_directed()
    access_cache: dict[str, tuple[dict, ...]] = {}

    def group_access(group_id: str) -> tuple[dict, ...]:
        """Materialize one group's alternate interfaces only when needed."""
        if group_id not in access_cache and samples is not None and frontier is not None:
            access_cache[group_id] = _access_candidates_for_group(ordinary, group_id, domain, samples, frontier)
        return access_cache.get(group_id, ())
    observations = []
    counts = {"exact_route_verified": 0, "unresolved_budget": 0, "proxy_unreachable": 0}
    source_observations = baseline["observations"] if pair_limit is None else baseline["observations"][:pair_limit]
    for original in source_observations:
        row = dict(original)
        route = original.get("route")
        repair = {
            "method": METHOD_VERSION,
            "quality": "proxy_unreachable",
            "baseline_distance_m": None,
            "candidate_distance_m": None,
            "lower_bound_m": None,
            "gap_m": None,
            "candidate_index": None,
            "failed_checks": [],
        }
        if route and route.get("cell_keys"):
            baseline_path = tuple(_tuple_cell(cell) for cell in route["cell_keys"])
            repair["baseline_distance_m"] = float(route["value"])
            repair["lower_bound_m"] = float(route["value"])
            checked = check_path(baseline_path, context, route.get("source_access"), route.get("target_access"))
            if checked["passed"]:
                exact = _exact_path(baseline_path, context, route.get("source_access"), route.get("target_access"))
                if exact["passed"]:
                    repair.update(quality="exact_route_verified", candidate_distance_m=float(route["value"]),
                                  gap_m=0.0, candidate_index=0,
                                  exact_witness={"edge_witnesses": exact["edge_witnesses"],
                                                 "cell_keys": baseline_path,
                                                 "turn_witnesses": exact["turn_witnesses"],
                                                 "minimum_m": exact["minimum_m"],
                                                 "source_access": route.get("source_access"),
                                                 "target_access": route.get("target_access")})
                else:
                    repair["failed_checks"].append(exact["failure"])
            else:
                repair["failed_checks"].append(checked["failure"])
                if candidate_budget:
                    graph = observed
                    blocked_edges, blocked_turns = set(), set()
                    for candidate_index, candidate in enumerate(
                            _alternate_paths(graph, route, ordinary.grid, corridor_margin_cells, candidate_budget,
                                             blocked_edges, blocked_turns), start=1):
                        candidate_check = check_path(candidate, context, route.get("source_access"), route.get("target_access"))
                        if candidate_check["passed"]:
                            exact = _exact_path(candidate, context, route.get("source_access"), route.get("target_access"))
                            if exact["passed"]:
                                distance = _route_distance(route, candidate, ordinary.grid)
                                repair.update(quality="exact_route_verified", candidate_distance_m=distance,
                                              gap_m=distance - float(route["value"]), candidate_index=candidate_index,
                                              exact_witness={"cell_keys": candidate,
                                                             "edge_witnesses": exact["edge_witnesses"],
                                                             "turn_witnesses": exact["turn_witnesses"],
                                                             "minimum_m": exact["minimum_m"],
                                                             "source_access": route.get("source_access"),
                                                             "target_access": route.get("target_access")})
                                break
                            repair["failed_checks"].append(exact["failure"])
                            continue
                        failure = candidate_check["failure"]
                        repair["failed_checks"].append(failure)
                        if failure["kind"] == "edge":
                            blocked_edges.add((tuple(failure["from"]), tuple(failure["to"])))
                        else:
                            blocked_turns.add((tuple(failure["from"]), tuple(failure["at"]), tuple(failure["to"])))
                if (repair["quality"] not in {"exact_route_verified", "screen_verified"}
                        and access_candidate_budget and observed is not None):
                    source_id, target_id = tuple(original["group_ids"])
                    access_blocked_edges: set[tuple] = set()
                    access_blocked_keys: set[tuple] = set()
                    access_seen_routes: set[tuple] = set()
                    for candidate_index in range(1, access_candidate_budget + 1):
                        alternate_routes = _access_route_candidates(
                            access_graph, group_access(source_id), group_access(target_id), 1,
                            context["rejected_edges"] | access_blocked_edges,
                            blocked_access_keys=access_blocked_keys)
                        candidate = next((item for item in alternate_routes
                                          if (item["source_access"]["access_key"],
                                              item["target_access"]["access_key"],
                                              tuple(item["cell_keys"])) not in access_seen_routes), None)
                        if candidate is None:
                            break
                        access_seen_routes.add((candidate["source_access"]["access_key"],
                                                candidate["target_access"]["access_key"],
                                                tuple(candidate["cell_keys"])))
                        same_baseline_interfaces = (
                            candidate["source_access"].get("access_key") == route.get("source_access", {}).get("access_key")
                            and candidate["target_access"].get("access_key") == route.get("target_access", {}).get("access_key")
                        )
                        if tuple(candidate["cell_keys"]) == baseline_path and same_baseline_interfaces:
                            access_blocked_edges.update(pairwise(baseline_path))
                            continue
                        candidate_check = check_path(tuple(candidate["cell_keys"]), context,
                                                     candidate["source_access"], candidate["target_access"])
                        if candidate_check["passed"]:
                            exact = _exact_path(tuple(candidate["cell_keys"]), context,
                                                candidate["source_access"], candidate["target_access"])
                            if exact["passed"]:
                                repair.update(quality="exact_route_verified", candidate_distance_m=float(candidate["value"]),
                                              gap_m=float(candidate["value"]) - float(route["value"]),
                                              candidate_index=candidate_index,
                                              exact_witness={"cell_keys": tuple(candidate["cell_keys"]),
                                                             "edge_witnesses": exact["edge_witnesses"],
                                                             "turn_witnesses": exact["turn_witnesses"],
                                                             "minimum_m": exact["minimum_m"],
                                                             "source_access": candidate["source_access"],
                                                             "target_access": candidate["target_access"]})
                                break
                            repair["failed_checks"].append(exact["failure"])
                            failure = exact["failure"]
                            if failure["kind"] == "edge":
                                access_blocked_edges.add((tuple(failure["from"]), tuple(failure["to"])))
                            elif failure.get("endpoint") == "source":
                                access_blocked_keys.add(tuple(candidate["source_access"]["access_key"]))
                            elif failure.get("endpoint") == "target":
                                access_blocked_keys.add(tuple(candidate["target_access"]["access_key"]))
                            else:
                                access_blocked_edges.add((tuple(failure["at"]), tuple(failure["to"])))
                            continue
                        failure = candidate_check["failure"]
                        repair["failed_checks"].append(failure)
                        if failure["kind"] == "edge":
                            access_blocked_edges.add((tuple(failure["from"]), tuple(failure["to"])))
                        elif failure.get("endpoint") == "source":
                            access_blocked_keys.add(tuple(candidate["source_access"]["access_key"]))
                        elif failure.get("endpoint") == "target":
                            access_blocked_keys.add(tuple(candidate["target_access"]["access_key"]))
                        else:
                            access_blocked_edges.add((tuple(failure["at"]), tuple(failure["to"])))
        if repair["quality"] not in {"exact_route_verified", "screen_verified"}:
            repair["quality"] = "unresolved_budget" if route and route.get("cell_keys") else "proxy_unreachable"
        counts.setdefault(repair["quality"], 0)
        counts[repair["quality"]] += 1
        row["directional_repair"] = repair
        observations.append(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "method": METHOD_VERSION,
        "policy": dict(policy),
        "candidate_budget": candidate_budget,
        "access_candidate_budget": access_candidate_budget,
        "corridor_margin_cells": corridor_margin_cells,
        "result_ref": baseline.get("manifest", {}).get("free_space_result", {}).get("result_ref"),
        "group_count": len(ordinary.groups),
        "pair_count": len(observations),
        "pair_limit": pair_limit,
        "quality_counts": counts,
        "geometry_checks": context["checks"],
        "cache_sizes": {"edges": len(context["edge_cache"]), "turns": len(context["turn_cache"])},
        "observations": observations,
    }


def _access_candidates(bundle: Any, domain: Any, samples: Mapping, frontier: nx.Graph) -> dict:
    """Build all source and target access states instead of retaining one baseline access."""
    result = {}
    for group in bundle.groups:
        geometry = kernel._group_geometry(group)
        if geometry["status"] != "computed":
            continue
        access = kernel._accesses(group, geometry, domain, bundle.grid, samples, frontier, constrained=True)
        result[group.group_id] = tuple(access["selected"].values())
    return result


def _access_candidates_for_group(bundle: Any, group_id: str, domain: Any,
                                 samples: Mapping, frontier: nx.Graph) -> tuple[dict, ...]:
    """Build access states for one group to keep global searches memory bounded."""
    group = next((item for item in bundle.groups if item.group_id == group_id), None)
    if group is None:
        return ()
    geometry = kernel._group_geometry(group)
    if geometry["status"] != "computed":
        return ()
    access = kernel._accesses(group, geometry, domain, bundle.grid, samples, frontier, constrained=True)
    return tuple(access["selected"].values())


def _state_graph_neighbors(graph: nx.Graph, cell: tuple[int, int]) -> tuple:
    """Read ordinary observed route neighbors in stable order."""
    return tuple(sorted(graph.neighbors(cell))) if cell in graph else ()


def _global_source_search(graph: nx.Graph, source_accesses: tuple[dict, ...], target_accesses: Mapping[str, tuple[dict, ...]],
                          context: dict, *, blocked_exact_edges: set[tuple] | None = None,
                          blocked_exact_turns: set[tuple] | None = None) -> dict[str, dict | None]:
    """Run multi-target Dijkstra while excluding exact failures already observed."""
    grid = context["bundle"].grid
    blocked_exact_edges = blocked_exact_edges or set()
    blocked_exact_turns = blocked_exact_turns or set()
    heap, distances, predecessors, seed_access = [], {}, {}, {}
    # A target access is valid when the route reaches its free cell.  The
    # access geometry does not prescribe one incoming lattice heading; the
    # final edge and any preceding turn are checked by the directional kernel.
    # Indexing targets by ``(cell, heading)`` would therefore make every
    # target unreachable because access records do not carry a target heading.
    targets_by_cell = {}
    minimum_offsets = {}
    for group_id, accesses in target_accesses.items():
        if accesses:
            minimum_offsets[group_id] = min(float(access["offset"]) for access in accesses)
        for access in accesses:
            cell = tuple(access["free_cell"])
            targets_by_cell.setdefault(cell, []).append((group_id, access))
    for access in source_accesses:
        cell = tuple(access["free_cell"])
        heading = tuple(access.get("heading", ()))
        state = (cell, heading)
        label = float(access["offset"])
        if label < distances.get(state, float("inf")):
            distances[state] = label
            predecessors[state] = None
            seed_access[state] = access
            heapq.heappush(heap, (label, repr(state), state))
    best = {}
    while heap:
        distance, _, state = heapq.heappop(heap)
        if distance != distances.get(state):
            continue
        cell, incoming = state
        for group_id, access in targets_by_cell.get(cell, ()):
            target_heading = _access_heading(access, grid, target=True)
            if incoming and target_heading and (cell, incoming, target_heading) in blocked_exact_turns:
                continue
            value = distance + float(access["offset"])
            prior = best.get(group_id)
            candidate = (value, access["access_key"], state, access)
            if prior is None or candidate[:2] < prior[:2]:
                best[group_id] = candidate
        # A target's endpoint offset varies, so reaching every target alone is
        # not a valid stopping rule.  Stop only when the smallest remaining
        # lattice distance plus that target's cheapest endpoint offset cannot
        # beat its current complete route distance.
        if len(best) == len(target_accesses) and heap:
            next_distance = heap[0][0]
            if all(best[target_id][0] <= next_distance + minimum_offsets[target_id]
                   for target_id in target_accesses):
                break
        for neighbor in _state_graph_neighbors(graph, cell):
            outgoing = kernel._heading(kernel._center(cell, grid), kernel._center(neighbor, grid))
            if (cell, neighbor) in blocked_exact_edges:
                continue
            if incoming and (cell, incoming, outgoing) in blocked_exact_turns:
                continue
            if not _transition_screen_ok(cell, neighbor, incoming or None, context):
                continue
            next_state = (neighbor, outgoing)
            edge_weight = float(graph[cell][neighbor]["weight"])
            label = distance + edge_weight
            if label < distances.get(next_state, float("inf")):
                distances[next_state] = label
                predecessors[next_state] = state
                heapq.heappush(heap, (label, repr(next_state), next_state))
    routes = {}
    for group_id, candidate in best.items():
        value, _, state, target = candidate
        path_states = []
        cursor = state
        while cursor is not None:
            path_states.append(cursor)
            cursor = predecessors.get(cursor)
        path_states.reverse()
        cells = tuple(item[0] for item in path_states)
        source_state = path_states[0]
        source = seed_access[source_state]
        routes[group_id] = {"value": value, "cell_keys": cells,
                            "source_access": source, "target_access": target,
                            "state_keys": tuple(path_states)}
    return routes


def global_repair_result(bundle: Any, baseline: Mapping[str, Any], policy: Mapping[str, float], *,
                         pair_limit: int | None = None,
                         checkpoint_dir: Path | None = None) -> dict:
    """Find exact directional routes globally, using one shared graph/context.

    ``checkpoint_dir`` stores one atomic JSON checkpoint after each source
    group.  A later invocation reuses completed source checkpoints, so an
    interrupted full run does not discard the expensive geometry work.
    """
    ordinary = _unconstrained_bundle(bundle)
    context = _clearance_context(ordinary, policy)
    domain = context["domain"]
    samples, observed, _, frontier = kernel._graphs(ordinary, domain)
    accesses: dict[str, tuple[dict, ...]] = {}

    def get_access(group_id: str) -> tuple[dict, ...]:
        """Materialize and cache one group's access states on demand."""
        if group_id not in accesses:
            accesses[group_id] = _access_candidates_for_group(ordinary, group_id, domain, samples, frontier)
        return accesses[group_id]
    groups = tuple(group.group_id for group in ordinary.groups)
    wanted = baseline["observations"] if pair_limit is None else baseline["observations"][:pair_limit]
    wanted_ids = {tuple(row["group_ids"]): row for row in wanted}
    results = {}
    completed_sources: set[int] = set()
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        for checkpoint in sorted(checkpoint_dir.glob("source_*.json")):
            try:
                payload = json.loads(checkpoint.read_text(encoding="utf-8"))
                source_index = int(payload["source_index"])
                for item in payload.get("results", ()):
                    key = tuple(item["key"])
                    results[key] = {"route": item["route"], "exact": item["exact"]}
                completed_sources.add(source_index)
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                # A partial or malformed checkpoint is ignored and recomputed.
                continue
    for index, source_id in enumerate(groups[:-1]):
        if index in completed_sources:
            continue
        target_ids = tuple(target_id for target_id in groups[index + 1:]
                           if (source_id, target_id) in wanted_ids)
        if not target_ids:
            if checkpoint_dir is not None:
                checkpoint = checkpoint_dir / f"source_{index:03d}.json"
                temporary = checkpoint.with_suffix(".json.tmp")
                temporary.write_text(json.dumps({"source_index": index, "source_id": source_id,
                                                 "results": []}, sort_keys=True), encoding="utf-8")
                temporary.replace(checkpoint)
            continue
        source_accesses = get_access(source_id)
        if not source_accesses:
            if checkpoint_dir is not None:
                checkpoint = checkpoint_dir / f"source_{index:03d}.json"
                temporary = checkpoint.with_suffix(".json.tmp")
                temporary.write_text(json.dumps({"source_index": index, "source_id": source_id,
                                                 "results": []}, sort_keys=True), encoding="utf-8")
                temporary.replace(checkpoint)
            continue
        candidate_targets = {
            target_id: get_access(target_id)
            for target_id in target_ids
            if get_access(target_id)
        }
        if not candidate_targets:
            if checkpoint_dir is not None:
                checkpoint = checkpoint_dir / f"source_{index:03d}.json"
                temporary = checkpoint.with_suffix(".json.tmp")
                temporary.write_text(json.dumps({"source_index": index, "source_id": source_id,
                                                 "results": []}, sort_keys=True), encoding="utf-8")
                temporary.replace(checkpoint)
            continue
        routes = _global_source_search(observed, source_accesses,
                                       candidate_targets, context)
        source_results = []
        for target_id, route in routes.items():
            key = (source_id, target_id)
            if key not in wanted_ids:
                continue
            exact = _exact_path(tuple(route["cell_keys"]), context,
                                route.get("source_access"), route.get("target_access"))
            results[key] = {"route": route, "exact": exact}
            source_results.append({"key": list(key), "route": route, "exact": exact})
        if checkpoint_dir is not None:
            checkpoint = checkpoint_dir / f"source_{index:03d}.json"
            temporary = checkpoint.with_suffix(".json.tmp")
            temporary.write_text(json.dumps({"source_index": index, "source_id": source_id,
                                             "results": source_results},
                                            sort_keys=True, ensure_ascii=False), encoding="utf-8")
            temporary.replace(checkpoint)
    observations = []
    counts = {"exact_route_verified": 0, "unresolved_global": 0, "proxy_unreachable": 0}
    for original in wanted:
        key = tuple(original["group_ids"])
        row = dict(original)
        found = results.get(key)
        repair = {"method": GLOBAL_METHOD_VERSION, "quality": "proxy_unreachable",
                  "baseline_distance_m": original.get("route", {}).get("value"),
                  "candidate_distance_m": None, "lower_bound_m": None, "gap_m": None,
                  "candidate_index": None, "failed_checks": []}
        if found is not None:
            route, exact = found["route"], found["exact"]
            repair["lower_bound_m"] = route["value"]
            if exact["passed"]:
                repair.update(quality="exact_route_verified", candidate_distance_m=route["value"],
                              gap_m=None, candidate_index=0,
                              exact_witness={"cell_keys": route["cell_keys"],
                                             "state_keys": route["state_keys"],
                                             "edge_witnesses": exact["edge_witnesses"],
                                             "turn_witnesses": exact["turn_witnesses"],
                                             "minimum_m": exact["minimum_m"],
                                             "source_access": route["source_access"],
                                             "target_access": route["target_access"]})
            else:
                repair.update(quality="unresolved_global", failed_checks=[exact["failure"]])
        else:
            repair["quality"] = "unresolved_global"
        counts[repair["quality"]] += 1
        row["directional_repair"] = repair
        observations.append(row)
    return {"schema_version": "route-repair/2", "method": GLOBAL_METHOD_VERSION,
            "policy": dict(policy), "group_count": len(groups), "pair_count": len(observations),
            "pair_limit": pair_limit, "quality_counts": counts, "geometry_checks": context["checks"],
            "cache_sizes": {"edges": len(context["edge_cache"]), "turns": len(context["turn_cache"]),
                            "exact_edges": len(context["exact_edge_cache"]), "exact_turns": len(context["exact_turn_cache"])},
            "observations": observations}


def write_repair_result(result: Mapping[str, Any], output: Path) -> None:
    """Write one deterministic JSON package for downstream preview tooling."""
    import json

    output.mkdir(parents=True, exist_ok=False)
    (output / "repair_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
