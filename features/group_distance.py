"""Descriptive group distances over one explicit, immutable scene-view handoff."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from itertools import combinations, pairwise
import math
import platform
import time
import tracemalloc
from typing import Any

import networkx as nx
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .field_core import FieldQuery, FieldStatus, _freeze, _json_value, fingerprint_evidence_dependency
from .free_space_field import FreeSpaceField

ALGORITHM_VERSION = "group-distance/1"
SCHEMA_VERSION = "group-distance/v1"
ARITHMETIC_VERSION = "networkx-binary64-left-add/1"
_ROOT = "virtual-source"


class _FrozenRecord:
    """Detach nested JSON inputs while preserving concrete immutable records."""

    def __post_init__(self) -> None:
        """Freeze each field so caller mutation cannot change a running query."""
        for member in fields(self):
            object.__setattr__(self, member.name, _freeze(getattr(self, member.name)))


@dataclass(frozen=True)
class GridDescriptor(_FrozenRecord):
    """Square cells in plane coordinates; rows advance Y and columns advance X."""

    grid_id: str
    frame: str
    origin: tuple[float, float]
    spacing: float
    n_rows: int
    n_cols: int
    row_axis: str = "+plane_y"
    column_axis: str = "+plane_x"
    cell_rule: str = "axis_aligned_square"
    domain_fingerprint: str = ""
    occupancy_fingerprint: str = ""


@dataclass(frozen=True)
class GroupProjection(_FrozenRecord):
    """One whole-group projection, retaining its explicit availability and sources."""

    group_id: str
    components: Any
    source_refs: Any
    status: str = "available"
    explanation: str = ""


@dataclass(frozen=True)
class GroupDistanceInput(_FrozenRecord):
    """Same-view geometry, occupancy, lattice and identity for one calculation."""

    source_identity: Any
    analysis_plane: Any
    domain: Any
    grid: GridDescriptor
    groups: tuple[GroupProjection, ...]
    physical_occupancy: Any
    unresolved_source_ids: tuple[str, ...]
    unresolved_supports: Any
    query: FieldQuery
    query_context: Any
    origin_offset: tuple[float, float]
    dependency_fingerprints: Any


@dataclass(frozen=True)
class GroupPairDistanceObservation(_FrozenRecord):
    """Independent raw readings and selected route for one unordered group pair."""

    pair_id: str
    group_ids: tuple[str, str]
    center_to_center_euclidean: Any
    centroid_free_space_hybrid: Any
    geometry_audit: Any
    route: Any
    lineage: Any
    dependencies: Any


@dataclass(frozen=True)
class GroupDistanceResult(_FrozenRecord):
    """Complete pair scope, reusable manifest, and measured execution diagnostics."""

    observations: tuple[GroupPairDistanceObservation, ...]
    pair_index: Any
    manifest: Any
    diagnostics: Any


def serialize_group_distance_result(result: GroupDistanceResult) -> dict[str, Any]:
    """Convert the typed immutable result to standard JSON-ready containers."""
    return {"group_ids": _json_value(result.manifest["group_ids"]), **_json_value(result)}


def _ordered(values: Any) -> tuple:
    """Canonicalize record order without changing record content or geometry."""
    return tuple(sorted(values or (), key=fingerprint_evidence_dependency))


def group_distance_input_fingerprints(bundle: GroupDistanceInput) -> dict[str, str]:
    """Hash explicit dependency contents; usable while assembling the handoff."""
    if not isinstance(bundle.origin_offset, (tuple, list)) or len(bundle.origin_offset) != 2 or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in bundle.origin_offset
    ):
        raise ValueError("origin_offset must contain two finite real coordinates")
    if bundle.physical_occupancy is not None and (
        not isinstance(bundle.physical_occupancy, (tuple, list))
        or any(not isinstance(record, Mapping) for record in bundle.physical_occupancy)
    ):
        raise ValueError("physical_occupancy must be a sequence of record mappings or None")
    occupancy = {
        "physical_occupancy": None if bundle.physical_occupancy is None else _ordered(bundle.physical_occupancy),
        "unresolved_source_ids": sorted(bundle.unresolved_source_ids),
        "unresolved_supports": bundle.unresolved_supports,
    }
    groups = tuple({"group_id": group.group_id, "components": _ordered(group.components),
                    "source_refs": _ordered(group.source_refs), "status": group.status,
                    "explanation": group.explanation} for group in sorted(bundle.groups, key=lambda item: item.group_id))
    query = {member.name: getattr(bundle.query, member.name) for member in fields(bundle.query)}
    query.update(query_context=bundle.query_context, origin_offset=bundle.origin_offset,
                 algorithm_version=(bundle.query_context or {}).get("algorithm_version", "free-space-field/2"),
                 schema_version=(bundle.query_context or {}).get("schema_version", "free-space-field/1"),
                 unresolved_source_ids=sorted(bundle.unresolved_source_ids),
                 unresolved_supports=bundle.unresolved_supports,
                 occupancy_source_ids=sorted({owner for record in bundle.physical_occupancy or () for owner in record.get("represented_source_ids", ())}))
    query["index_convention"] = (bundle.grid.row_axis, bundle.grid.column_axis, bundle.grid.cell_rule)
    return {name: fingerprint_evidence_dependency(value) for name, value in {
        "source": bundle.source_identity, "analysis_plane": bundle.analysis_plane,
        "domain": bundle.domain, "occupancy": occupancy, "groups": groups,
        "query": query, "grid": bundle.grid,
    }.items()}


def _pair_id(group_ids: tuple[str, str], source_identity: Any) -> str:
    """Derive a stable address without relying on separators in source identities."""
    return "group-pair:" + fingerprint_evidence_dependency({"source": source_identity, "group_ids": group_ids})[:24]


def _shape(components: Any):
    """Reject malformed components instead of silently dropping invalid polygons."""
    if not isinstance(components, (tuple, list)) or not components:
        raise ValueError("projection components must contain positive-area polygons")
    polygons = []
    for component in _ordered(components):
        if not isinstance(component, Mapping):
            raise ValueError("polygon component must be a mapping")
        rings = (component.get("exterior", ()), *component.get("holes", ()))
        for ring in rings:
            if len(ring) < 3 or any(len(point) != 2 or any(
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in point) for point in ring):
                raise ValueError("polygon rings require finite two-dimensional coordinates")
        polygon = Polygon(rings[0], rings[1:])
        if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
            raise ValueError("polygon component is invalid or has no area")
        polygons.append(polygon)
    geometry = unary_union(polygons)
    if geometry.is_empty or not geometry.is_valid or not math.isfinite(geometry.area):
        raise ValueError("union geometry is invalid")
    return geometry


def _group_geometry(group: GroupProjection) -> dict:
    """Keep one union centroid, including when it falls outside the group union."""
    if group.status in {"not_available", "missing"} or group.components is None:
        return {"status": "not_available", "explanation": group.explanation or "group projection is missing"}
    if group.status not in {"available", "computed", "established"}:
        return {"status": "invalid", "explanation": group.explanation or "group projection is invalid"}
    try:
        geometry = _shape(group.components)
        centroid = geometry.centroid
        if not all(math.isfinite(value) for value in centroid.coords[0]):
            raise ValueError("group centroid is not finite")
    except (TypeError, ValueError, IndexError) as exc:
        return {"status": "invalid", "explanation": str(exc)}
    audit = {"union_area": float(geometry.area),
             "component_count": len(geometry.geoms) if geometry.geom_type == "MultiPolygon" else 1,
             "centroid_inside_union": geometry.covers(centroid),
             "centroid_source_ref": "group-union:" + fingerprint_evidence_dependency(_ordered(group.components)),
             "centroid": tuple(centroid.coords[0]), "source_refs": group.source_refs}
    return {"status": "computed", "shape": geometry, "audit": audit}


def _analysis_plane_binding_error(bundle: GroupDistanceInput, fingerprints: Mapping) -> str | None:
    """Bind a canonical camera plane to the constructor context without inventing its frame."""
    if (not isinstance(bundle.query_context, Mapping)
            or bundle.query_context.get("analysis_plane_fingerprint") != fingerprints["analysis_plane"]):
        return "analysis plane fingerprint binding is missing or does not match the handoff"
    plane = _json_value(bundle.analysis_plane)
    if (not isinstance(plane, Mapping) or plane.get("units", "m") != "m"
            or any(plane[name] != bundle.grid.frame for name in ("frame_id", "frame") if name in plane)):
        return "analysis plane frame or linear-unit handoff does not match"
    return None


def _validate_handoff(bundle: GroupDistanceInput, fingerprints: Mapping) -> tuple[str | None, str, Any]:
    """Check identities and exact grid coverage before permitting route claims."""
    grid, query = bundle.grid, bundle.query
    if nx.__version__ != "3.6.1":
        return "not_available", "the numerical contract requires NetworkX 3.6.1", None
    if bundle.domain is None:
        return "not_available", "analysis domain handoff is missing", None
    try:
        domain = _shape(bundle.domain.get("components"))
        if bundle.domain.get("status") == "invalid":
            raise ValueError("domain is explicitly invalid")
        if (isinstance(grid.spacing, bool) or grid.spacing <= 0 or not math.isfinite(grid.spacing)
                or len(grid.origin) != 2 or not all(math.isfinite(value) for value in grid.origin)
                or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (grid.n_rows, grid.n_cols))):
            raise ValueError("grid geometry is malformed")
        extent = box(*grid.origin, grid.origin[0] + grid.n_cols * grid.spacing,
                     grid.origin[1] + grid.n_rows * grid.spacing)
        if not all(math.isfinite(value) for value in extent.bounds):
            raise ValueError("grid bounds are not finite")
        FieldQuery(query.domain_id, query.frame, query.plane, query.height_band, query.demand, query.tolerance, query.revision)
    except (TypeError, ValueError, AttributeError, IndexError) as exc:
        return "invalid", str(exc), None
    if not bundle.source_identity or not bundle.analysis_plane or bundle.physical_occupancy is None:
        return "not_available", "source, plane or physical occupancy handoff is missing", domain
    if not extent.covers(domain):
        return "not_available", "grid rectangle does not cover the complete analysis domain", domain
    plane_error = _analysis_plane_binding_error(bundle, fingerprints)
    if plane_error:
        return "not_available", plane_error, domain
    if (grid.row_axis, grid.column_axis, grid.cell_rule) != ("+plane_y", "+plane_x", "axis_aligned_square"):
        return "not_available", "grid index convention does not match the declared plane", domain
    if (not grid.grid_id or not grid.frame or query.frame != grid.frame
            or bundle.domain.get("frame") != grid.frame or bundle.domain.get("id") != query.domain_id):
        return "not_available", "plane, domain, frame or linear-unit handoff does not match", domain
    if any(value is not None for value in (query.plane, query.height_band, query.demand)):
        return "not_available", "only an explicit whole-height planar occupancy query is supported", domain
    if (grid.domain_fingerprint != fingerprints["domain"] or grid.occupancy_fingerprint != fingerprints["occupancy"]
            or not isinstance(bundle.dependency_fingerprints, Mapping)
            or any(bundle.dependency_fingerprints.get(name) != digest for name, digest in fingerprints.items())):
        return "not_available", "dependency fingerprints are missing or do not match input content", domain
    if not isinstance(bundle.query_context, Mapping) or bundle.query_context.get("domain_id") != query.domain_id or bundle.query_context.get("frame") != query.frame:
        return "not_available", "field constructor query context does not match the actual query", domain
    return None, "", domain


def _neighbors(cell: tuple[int, int], grid: GridDescriptor) -> tuple:
    """Return existing four-neighbor cells in canonical index order."""
    row, col = cell
    return tuple(sorted((r, c) for r, c in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
                        if 0 <= r < grid.n_rows and 0 <= c < grid.n_cols))


def _center(cell: tuple[int, int], grid: GridDescriptor) -> tuple[float, float]:
    """Read a cell center from the explicit lattice, without resampling geometry."""
    return grid.origin[0] + (cell[1] + 0.5) * grid.spacing, grid.origin[1] + (cell[0] + 0.5) * grid.spacing


def _cell_polygon(cell: tuple[int, int], grid: GridDescriptor):
    """Build the cell used by the same FreeSpaceField query."""
    row, col = cell
    return box(grid.origin[0] + col * grid.spacing, grid.origin[1] + row * grid.spacing,
               grid.origin[0] + (col + 1) * grid.spacing, grid.origin[1] + (row + 1) * grid.spacing)


def _graphs(bundle: GroupDistanceInput, domain: Any) -> tuple:
    """Query cells once, then build observed, optimistic and failure-frontier graphs."""
    grid, query = bundle.grid, bundle.query
    field = FreeSpaceField(domain=bundle.domain, origin=grid.origin, spacing=grid.spacing,
                           n_rows=grid.n_rows, n_cols=grid.n_cols, physical_occupancy=sorted(bundle.physical_occupancy, key=lambda item: item["id"]),
                           unresolved_source_ids=bundle.unresolved_source_ids, unresolved_supports=bundle.unresolved_supports,
                           query_context=bundle.query_context, frame=grid.frame, origin_offset=bundle.origin_offset,
                           algorithm_version=bundle.query_context.get("algorithm_version", "free-space-field/2"),
                           schema_version=bundle.query_context.get("schema_version", "free-space-field/1"))
    request = FieldQuery(query.domain_id, query.frame, query.plane, query.height_band, query.demand, query.tolerance, query.revision)
    samples, observed, optimistic, frontier = {}, nx.Graph(), nx.Graph(), nx.Graph()
    for row in range(grid.n_rows):
        for col in range(grid.n_cols):
            cell = row, col
            sample = field.evaluate(cell, request)
            samples[cell] = {"cell_key": cell, "query_ref": f"{grid.grid_id}:cell:{row}:{col}",
                             "status": sample.status.value, "value": sample.value, "source_refs": sample.source_ids,
                             "support": sample.support, "explanation": sample.explanation, "center": _center(cell, grid)}
            if not domain.covers(Point(_center(cell, grid))):
                continue
            if sample.value is False and sample.status in {FieldStatus.ESTABLISHED, FieldStatus.CONDITIONAL}:
                observed.add_node(cell)
                optimistic.add_node(cell)
                frontier.add_node(cell)
            elif sample.status == FieldStatus.UNKNOWN:
                optimistic.add_node(cell)
                frontier.add_node(cell)
            elif sample.status in {FieldStatus.INVALID, FieldStatus.NOT_AVAILABLE}:
                # Failed queries remain failures; this graph identifies their relevant frontier only.
                frontier.add_node(cell)
    for cell in sorted(frontier):
        for neighbor in _neighbors(cell, grid):
            if neighbor <= cell or neighbor not in frontier:
                continue
            segment = LineString((_center(cell, grid), _center(neighbor, grid)))
            if not domain.covers(segment):
                continue
            weight = math.dist(_center(cell, grid), _center(neighbor, grid))
            data = {"weight": weight, "edge_key": (cell, neighbor), "domain_covered": True,
                    "domain_fingerprint": grid.domain_fingerprint, "grid_id": grid.grid_id,
                    "occupancy_query_refs": (samples[cell]["query_ref"], samples[neighbor]["query_ref"])}
            frontier.add_edge(cell, neighbor, **data)
            if cell in optimistic and neighbor in optimistic:
                optimistic.add_edge(cell, neighbor, **data)
            if cell in observed and neighbor in observed:
                observed.add_edge(cell, neighbor, **data)
    return samples, observed, optimistic, frontier


def _accesses(group: GroupProjection, geometry: dict, domain: Any, grid: GridDescriptor, samples: dict, frontier: nx.Graph) -> dict:
    """Keep every footprint/interface candidate and audit duplicate free-cell reduction."""
    clipped = geometry["shape"].intersection(domain)
    if clipped.area <= 0:
        return {"outside": True, "footprint_cells": (), "selected": {}, "candidates": (), "discarded": (), "query_cells": ()}
    footprint = tuple(cell for cell in sorted(samples) if _cell_polygon(cell, grid).intersection(clipped).area > 0)
    candidates, query_cells = [], set(footprint)
    centroid = geometry["audit"]["centroid"]
    for cell in footprint:
        for neighbor in _neighbors(cell, grid):
            query_cells.add(neighbor)
            if neighbor not in frontier:
                continue
            shared = _cell_polygon(cell, grid).intersection(_cell_polygon(neighbor, grid))
            endpoints = tuple(sorted(tuple(point) for point in shared.coords))
            midpoint = tuple(shared.interpolate(0.5, normalized=True).coords[0])
            free_center = _center(neighbor, grid)
            candidates.append({"access_key": (group.group_id, cell, neighbor, endpoints), "group_id": group.group_id, "footprint_cell": cell,
                               "free_cell": neighbor, "shared_edge": endpoints, "proxy_point": midpoint,
                               "cell_center": free_center, "offset": math.dist(centroid, midpoint) + math.dist(midpoint, free_center),
                               "query_ref": samples[neighbor]["query_ref"], "status": samples[neighbor]["status"]})
    selected, discarded = {}, []
    for candidate in sorted(candidates, key=lambda item: (item["offset"], item["access_key"])):
        cell = candidate["free_cell"]
        if cell in selected:
            discarded.append(candidate)
        else:
            selected[cell] = candidate
    return {"outside": False, "footprint_cells": footprint, "selected": selected,
            "candidates": tuple(sorted(candidates, key=lambda item: item["access_key"])), "discarded": tuple(discarded),
            "query_cells": tuple(sorted(query_cells))}


def _recover_source(graph: nx.Graph, accesses: Mapping, samples: Mapping, optimistic: bool) -> tuple:
    """Recover deterministic representatives from exact NetworkX predecessor labels."""
    seeds = {cell: access for cell, access in accesses.items() if cell in graph}
    if not seeds:
        return {}, {}, {}
    graph.add_node(_ROOT)
    for cell in sorted(seeds):
        graph.add_edge(_ROOT, cell, weight=seeds[cell]["offset"])
    try:
        predecessors, distances = nx.dijkstra_predecessor_and_distance(graph, _ROOT, weight="weight")
        best, any_unknown = {}, {}
        for cell in sorted((node for node in distances if node != _ROOT), key=lambda node: (distances[node], node)):
            if not math.isfinite(distances[cell]):
                raise ArithmeticError("non-finite backend distance label")
            for neighbor, edge in graph[cell].items():
                if neighbor != _ROOT and not distances[cell] + edge["weight"] > distances[cell]:
                    raise ArithmeticError("physical edge does not strictly increase a binary64 label")
            choices, unknown_alternatives = [], []
            for parent in predecessors[cell]:
                if distances[parent] + graph[parent][cell]["weight"] != distances[cell]:
                    continue
                if parent == _ROOT:
                    previous = (0, 0, seeds[cell]["access_key"], ())
                    unknown_alternatives.append(False)
                else:
                    if distances[parent] >= distances[cell] or parent not in best:
                        raise ArithmeticError("tight physical predecessor is not an increasing DAG")
                    previous = best[parent]
                    unknown_alternatives.append(any_unknown[parent])
                unknown, conditional, source, path = previous
                choices.append((unknown + (samples[cell]["status"] == "unknown"),
                                conditional + (samples[cell]["status"] == "conditional"), source, path + (cell,)))
            if not choices:
                raise ArithmeticError("backend label has no exactly replayable predecessor")
            best[cell] = min(choices, key=lambda label: label if optimistic else label[1:])
            any_unknown[cell] = samples[cell]["status"] == "unknown" or any(unknown_alternatives)
        return distances, best, any_unknown
    finally:
        graph.remove_node(_ROOT)


def _arithmetic(source_offset: float, weights: tuple, target_offset: float, label: float) -> dict:
    """Verify exact backend replay and bound the explicit regrouping residual."""
    replay, route_sum = source_offset, 0.0
    for weight in weights:
        replay += weight
        route_sum += weight
    replay += target_offset
    recomposed = (source_offset + route_sum) + target_offset
    residual = label - recomposed
    k_eps = (len(weights) + 3) * 2.0 ** -52
    if k_eps >= 1:
        raise ArithmeticError("binary64 rounding bound is undefined")
    bound = 2 * k_eps / (1 - k_eps) * math.fsum((abs(source_offset), *(abs(weight) for weight in weights), abs(target_offset)))
    if not all(math.isfinite(value) for value in (label, replay, recomposed, residual, bound)) or replay != label or abs(residual) > bound:
        raise ArithmeticError("backend route replay or binary64 residual contract failed")
    return {"source_offset": source_offset, "route_edge_sum": route_sum, "target_offset": target_offset,
            "backend_hybrid_label": label, "canonical_recomposed_sum": recomposed,
            "residual": residual, "residual_ulp": residual / math.ulp(label), "rounding_bound": bound,
            "backend_replay": replay, "arithmetic_version": ARITHMETIC_VERSION}


def _target_route(graph: nx.Graph, target_accesses: Mapping, source_accesses: Mapping,
                  distances: Mapping, best: Mapping, any_unknown: Mapping, samples: Mapping,
                  optimistic: bool) -> dict | None:
    """Select one target candidate using the complete frozen binary64 ordering."""
    candidates = []
    for cell, target in sorted(target_accesses.items()):
        if cell in best:
            unknown, conditional, source_key, path = best[cell]
            label = distances[cell] + target["offset"]
            key = ((label, unknown, conditional, source_key, path, target["access_key"]) if optimistic else
                   (label, conditional, source_key, path, target["access_key"]))
            candidates.append((key, cell, target))
    if not candidates:
        return None
    key, cell, target = min(candidates, key=lambda item: item[0])
    unknown, conditional, source_key, path = best[cell]
    source = source_accesses[path[0]]
    edges = tuple({**graph[a][b], "from": a, "to": b} for a, b in pairwise(path))
    arithmetic = _arithmetic(source["offset"], tuple(edge["weight"] for edge in edges), target["offset"], key[0])
    return {"value": key[0], "cell_keys": path, "points": tuple(samples[node]["center"] for node in path),
            "edges": edges, "source_access": source, "target_access": target,
            "conditional_cell_count": conditional, "unknown_cell_count": unknown,
            "cells": tuple(samples[node] for node in path), "arithmetic": arithmetic,
            "unknown_cells": tuple(node for node in path if samples[node]["status"] == "unknown"),
            "has_unknown_tie": any(any_unknown[end] for candidate, end, _ in candidates if candidate[0] == key[0])}


def _failure_cells(first: dict, second: dict, component_failures: Mapping, samples: Mapping) -> tuple:
    """Limit failed queries to endpoint queries and their connected search frontier."""
    relevant = set(first["query_cells"]) | set(second["query_cells"])
    for access in (first, second):
        for cell in access["selected"]:
            relevant.update(component_failures.get(cell, ()))
    return tuple(samples[cell] for cell in sorted(relevant) if samples[cell]["status"] in {"invalid", "not_available"})


def calculate_group_pair_distances(input_bundle: GroupDistanceInput) -> GroupDistanceResult:
    """Calculate every unordered pair, batching each graph by source group."""
    if not isinstance(input_bundle, GroupDistanceInput):
        raise TypeError("input_bundle must be a GroupDistanceInput")
    bundle = input_bundle
    if not all(isinstance(group, GroupProjection) and isinstance(group.group_id, str) and group.group_id for group in bundle.groups):
        raise ValueError("groups require nonempty identities and GroupProjection records")
    groups = tuple(sorted(bundle.groups, key=lambda group: group.group_id))
    if len({group.group_id for group in groups}) != len(groups):
        raise ValueError("group identities must be unique")
    started, owns_trace = time.perf_counter(), not tracemalloc.is_tracing()
    if owns_trace:
        tracemalloc.start()
    try:
        return _calculate(bundle, groups, started)
    finally:
        if owns_trace:
            tracemalloc.stop()


def _calculate(bundle: GroupDistanceInput, groups: tuple, started: float) -> GroupDistanceResult:
    """Keep one source search state alive at a time and assemble typed pair output."""
    try:
        fingerprints = group_distance_input_fingerprints(bundle)
    except (TypeError, ValueError) as exc:
        # Malformed metadata must still reach complete pair output and independent centroid evaluation.
        fingerprints, global_status, global_explanation, domain = {}, "invalid", str(exc), None
    else:
        global_status, global_explanation, domain = _validate_handoff(bundle, fingerprints)
    geometry = {group.group_id: _group_geometry(group) for group in groups}
    pairs = tuple(combinations((group.group_id for group in groups), 2))
    samples, access, routes, graph_stats, search_failures = {}, {}, {}, {}, {}
    graphs, component_failures = None, {}
    if global_status is None:
        try:
            samples, observed, optimistic, frontier = _graphs(bundle, domain)
            graphs = (observed, optimistic, frontier)
            if samples and all(sample["status"] == "invalid" for sample in samples.values()):
                global_status, global_explanation = "invalid", "the frozen occupancy field rejects every query"
            # Component failure membership is shared across pairs; it never turns failures into route nodes.
            for component in nx.connected_components(frontier):
                failed = tuple(sorted(cell for cell in component if samples[cell]["status"] in {"invalid", "not_available"}))
                for cell in component:
                    component_failures[cell] = failed
            for group in groups:
                if geometry[group.group_id]["status"] == "computed":
                    access[group.group_id] = _accesses(group, geometry[group.group_id], domain, bundle.grid, samples, frontier)
            for mode, graph in (("observed", observed), ("optimistic", optimistic)):
                runs = 0
                for index, source in enumerate(groups[:-1]):
                    if source.group_id not in access or access[source.group_id]["outside"]:
                        continue
                    try:
                        if any(cell in graph for cell in access[source.group_id]["selected"]):
                            runs += 1
                        distances, best, unknown = _recover_source(graph, access[source.group_id]["selected"], samples, mode == "optimistic")
                        for target in groups[index + 1:]:
                            if target.group_id in access and not access[target.group_id]["outside"]:
                                routes.setdefault((source.group_id, target.group_id), {})[mode] = _target_route(
                                    graph, access[target.group_id]["selected"], access[source.group_id]["selected"],
                                    distances, best, unknown, samples, mode == "optimistic")
                        del distances, best, unknown
                    except ArithmeticError as exc:
                        search_failures[(source.group_id, mode)] = str(exc)
                graph_stats[mode] = {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(), "source_runs": runs}
        except (TypeError, ValueError, KeyError) as exc:
            global_status, global_explanation = "invalid", str(exc)
    observations, pair_index = [], []
    for ids in pairs:
        first, second = (geometry[identity] for identity in ids)
        audits = {identity: geometry[identity].get("audit", {"status": geometry[identity]["status"], "explanation": geometry[identity].get("explanation", "")}) for identity in ids}
        endpoint_statuses = {first["status"], second["status"]}
        endpoint_status = "invalid" if "invalid" in endpoint_statuses else "not_available" if "not_available" in endpoint_statuses else None
        euclidean = {"status": endpoint_status or "computed", "value": None, "units": "m"}
        if endpoint_status is None:
            euclidean.update(value=math.dist(first["audit"]["centroid"], second["audit"]["centroid"]),
                             centroid_source_refs=tuple(audits[identity]["centroid_source_ref"] for identity in ids))
        selected, lower, failures, explanation = None, None, (), global_explanation
        status = "invalid" if "invalid" in {global_status, endpoint_status} else global_status or endpoint_status
        if status is None:
            a, b = (access[identity] for identity in ids)
            failures = _failure_cells(a, b, component_failures, samples)
            failure_statuses = {sample["status"] for sample in failures}
            numerical = [reason for (source, mode), reason in search_failures.items() if source == ids[0]]
            if "invalid" in failure_statuses or numerical:
                status, explanation = "invalid", "; ".join(numerical) or "invalid occupancy query in pair dependency frontier"
            elif "not_available" in failure_statuses:
                status, explanation = "not_available", "unavailable occupancy query in pair dependency frontier"
            elif a["outside"] or b["outside"]:
                status, explanation = "outside", "group footprint has no positive-area domain intersection"
            else:
                selected = routes.get(ids, {}).get("observed")
                lower = routes.get(ids, {}).get("optimistic")
                if selected is not None:
                    tau = max(math.ulp(selected["value"]), math.ulp(lower["value"]) if lower else 0, math.ulp(bundle.grid.spacing))
                    status = "partial" if selected["conditional_cell_count"] or lower and selected["value"] - lower["value"] > tau else "computed"
                else:
                    status = "unknown" if lower is not None else "unreachable"
        hybrid = {"status": status, "value": selected["value"] if selected else None, "units": "m", "reason": explanation,
                  "optimistic_lower_bound": lower["value"] if lower else None, "discrete_approximation": True,
                  "conditional_cell_count": selected["conditional_cell_count"] if selected else None,
                  "unknown_cell_count": lower["unknown_cell_count"] if lower else None,
                  "arithmetic": selected["arithmetic"] if selected else None,
                  "tie_uncertainty": bool(selected and lower and lower["has_unknown_tie"] and abs(selected["value"] - lower["value"]) <= max(math.ulp(selected["value"]), math.ulp(lower["value"]), math.ulp(bundle.grid.spacing)))}
        if selected:
            hybrid.update(source_centroid_to_access_offset=selected["arithmetic"]["source_offset"],
                          free_space_route_distance=selected["arithmetic"]["route_edge_sum"], target_access_to_centroid_offset=selected["arithmetic"]["target_offset"])
            selected = {**selected, "source_centroid": audits[ids[0]]["centroid"], "target_centroid": audits[ids[1]]["centroid"]}
        pair_id = _pair_id(ids, bundle.source_identity)
        lineage = {"group_source_refs": {group.group_id: group.source_refs for group in groups if group.group_id in ids},
                   "failed_queries": failures,
                   "observed_query_refs": tuple(cell["query_ref"] for cell in selected["cells"]) if selected else (),
                   "optimistic_lower_bound": lower,
                   "access_audit": {identity: {name: access[identity][name] for name in ("footprint_cells", "candidates", "discarded")} for identity in ids if identity in access}}
        observations.append(GroupPairDistanceObservation(pair_id, ids, euclidean, hybrid, audits, selected, lineage, fingerprints))
        pair_index.append({"pair_id": pair_id, "group_ids": ids, "observation_index": len(observations) - 1})
    _, peak = tracemalloc.get_traced_memory()
    manifest = {"algorithm_version": ALGORITHM_VERSION, "schema_version": SCHEMA_VERSION,
                "arithmetic_version": ARITHMETIC_VERSION, "source_identity": bundle.source_identity,
                "analysis_plane": bundle.analysis_plane, "domain": bundle.domain, "grid": bundle.grid,
                "query": bundle.query, "query_context": bundle.query_context, "origin_offset": bundle.origin_offset, "units": "m", "group_ids": tuple(group.group_id for group in groups),
                "expected_pair_ids": tuple(item["pair_id"] for item in pair_index), "expected_pair_count": len(pairs),
                "dependency_fingerprints": fingerprints, "cell_samples": tuple(samples[cell] for cell in sorted(samples)),
                "python_version": platform.python_version(), "networkx_version": nx.__version__}
    diagnostics = {"global_status": global_status, "global_explanation": global_explanation,
                   "graphs": graph_stats, "source_batched": True, "second_dijkstra": False,
                   "runtime_s": time.perf_counter() - started, "tracemalloc_peak_bytes": peak,
                   "numerical_contract_failures": tuple({"source_group_id": key[0], "mode": key[1], "explanation": reason} for key, reason in sorted(search_failures.items())),
                   "observed_statuses": tuple(sorted({item.centroid_free_space_hybrid["status"] for item in observations}))}
    return GroupDistanceResult(tuple(observations), pair_index, manifest, diagnostics)
