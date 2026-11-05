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
import math
from pathlib import Path
from typing import Any, Mapping

import networkx as nx
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from . import group_distance as kernel


METHOD_VERSION = "route-first-lazy-exact/1"
SCHEMA_VERSION = "route-repair/1"


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
        "checks": {"edges": 0, "turns": 0},
    }


def _path_headings(path: tuple[tuple[int, int], ...], grid: Any) -> tuple[tuple[float, float], ...]:
    """Return the positive-length heading for every path edge."""
    return tuple(kernel._heading(kernel._center(first, grid), kernel._center(second, grid))
                 for first, second in pairwise(path))


def check_path(path: tuple[tuple[int, int], ...], context: dict) -> dict:
    """Check one lattice path and return exact witnesses or its first failure."""
    grid = context["bundle"].grid
    blockers, domain = context["blockers"], context["domain"]
    thresholds, index = context["thresholds"], context["index"]
    edges, turns = [], []
    screened_edges, screened_turns = 0, 0
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
                  pair_limit: int | None = None) -> dict:
    """Repair ordinary routes with bounded local exact directional-clearance checks."""
    if candidate_budget < 0 or corridor_margin_cells < 0:
        raise ValueError("candidate_budget and corridor_margin_cells must be nonnegative")
    ordinary = _unconstrained_bundle(bundle)
    context = _clearance_context(ordinary, policy)
    domain = context["domain"]
    observed = None
    if candidate_budget:
        _, observed, _, _ = kernel._graphs(ordinary, domain)
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
            checked = check_path(baseline_path, context)
            if checked["passed"]:
                quality = "screen_verified" if checked["screened_edges"] or checked["screened_turns"] else "exact_route_verified"
                repair.update(quality=quality, candidate_distance_m=float(route["value"]),
                              gap_m=0.0, candidate_index=0,
                              exact_witness={"edge_witnesses": checked["edge_witnesses"],
                                             "cell_keys": baseline_path,
                                             "turn_witnesses": checked["turn_witnesses"],
                                             "minimum_m": checked["minimum_m"]})
            else:
                repair["failed_checks"].append(checked["failure"])
                if candidate_budget:
                    graph = observed
                    blocked_edges, blocked_turns = set(), set()
                    for candidate_index, candidate in enumerate(
                            _alternate_paths(graph, route, ordinary.grid, corridor_margin_cells, candidate_budget,
                                             blocked_edges, blocked_turns), start=1):
                        candidate_check = check_path(candidate, context)
                        if candidate_check["passed"]:
                            distance = _route_distance(route, candidate, ordinary.grid)
                            quality = "screen_verified" if candidate_check["screened_edges"] or candidate_check["screened_turns"] else "exact_route_verified"
                            repair.update(quality=quality, candidate_distance_m=distance,
                                          gap_m=distance - float(route["value"]), candidate_index=candidate_index,
                                          exact_witness={"cell_keys": candidate,
                                                         "edge_witnesses": candidate_check["edge_witnesses"],
                                                         "turn_witnesses": candidate_check["turn_witnesses"],
                                                         "minimum_m": candidate_check["minimum_m"]})
                            break
                        failure = candidate_check["failure"]
                        repair["failed_checks"].append(failure)
                        if failure["kind"] == "edge":
                            blocked_edges.add((tuple(failure["from"]), tuple(failure["to"])))
                        else:
                            blocked_turns.add((tuple(failure["from"]), tuple(failure["at"]), tuple(failure["to"])))
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


def write_repair_result(result: Mapping[str, Any], output: Path) -> None:
    """Write one deterministic JSON package for downstream preview tooling."""
    import json

    output.mkdir(parents=True, exist_ok=False)
    (output / "repair_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
