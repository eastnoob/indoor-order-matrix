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

ALGORITHM_VERSION = "group-distance/2"
SCHEMA_VERSION = "group-distance/v2"
EDGE_SUPPORT_VERSION = "eight-neighbor-two-flank-occurrences/1"
CLEARANCE_ALGORITHM_VERSION = "group-distance/3"
CLEARANCE_SCHEMA_VERSION = "group-distance/v3"
CLEARANCE_EDGE_SUPPORT_VERSION = "eight-neighbor-two-flank-occurrences-directional-clearance/1"
CLEARANCE_POLICY_VERSION = "directional-clearance/1"
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
    free_space_samples: Any = None
    clearance_policy: Any = None


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
    # Legacy constructor bundles retain their saved fingerprint. Exact-result
    # consumers additionally bind every immutable sample and its publication ref.
    if bundle.free_space_samples is not None:
        occupancy["free_space_samples"] = bundle.free_space_samples
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
    if bundle.clearance_policy is not None:
        query["clearance_policy"] = bundle.clearance_policy
    return {name: fingerprint_evidence_dependency(value) for name, value in {
        "source": bundle.source_identity, "analysis_plane": bundle.analysis_plane,
        "domain": bundle.domain, "occupancy": occupancy, "groups": groups,
        "query": query, "grid": bundle.grid,
    }.items()}


def _clearance_thresholds(policy: Any) -> tuple[float, float, float] | None:
    """Read the opt-in directional thresholds while leaving legacy input untouched."""
    if policy is None:
        return None
    if not isinstance(policy, Mapping):
        raise ValueError("clearance_policy must be a mapping or None")
    values = tuple(policy.get(name) for name in ("min_left_m", "min_right_m", "min_total_m"))
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("clearance_policy thresholds must be finite nonnegative numbers")
    return tuple(float(value) for value in values)


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
    if bundle.free_space_samples is not None:
        sample_error = _saved_samples_error(bundle)
        if sample_error:
            return "not_available", sample_error, domain
    elif any(value is not None for value in (query.plane, query.height_band, query.demand)):
        return "not_available", "only an explicit whole-height planar occupancy query is supported", domain
    if (grid.domain_fingerprint != fingerprints["domain"] or grid.occupancy_fingerprint != fingerprints["occupancy"]
            or not isinstance(bundle.dependency_fingerprints, Mapping)
            or any(bundle.dependency_fingerprints.get(name) != digest for name, digest in fingerprints.items())):
        return "not_available", "dependency fingerprints are missing or do not match input content", domain
    if not isinstance(bundle.query_context, Mapping) or bundle.query_context.get("domain_id") != query.domain_id or bundle.query_context.get("frame") != query.frame:
        return "not_available", "field constructor query context does not match the actual query", domain
    return None, "", domain


def _saved_samples_error(bundle: GroupDistanceInput) -> str | None:
    """Require the exact lattice/query/source binding of a saved bool field."""
    saved, grid = bundle.free_space_samples, bundle.grid
    if not isinstance(saved, Mapping) or saved.get("kind") != "exact_free_space_samples/1":
        return "saved free-space sample handoff is malformed"
    expected_grid = {"origin": grid.origin, "spacing": grid.spacing,
                     "n_rows": grid.n_rows, "n_cols": grid.n_cols}
    if (saved.get("lattice") != expected_grid or saved.get("query") != _freeze(_json_value(bundle.query))
            or saved.get("source_identity") != bundle.source_identity
            or saved.get("analysis_plane") != bundle.analysis_plane
            or saved.get("domain") != bundle.domain
            or bundle.origin_offset != (0, 0)):
        return "saved free-space lattice, query, plane, domain or source binding differs"
    reference = saved.get("result_ref", {})
    if (reference.get("kind") != "free_space_run" or not reference.get("result_id")
            or not isinstance(reference.get("digest"), str) or len(reference["digest"]) != 64
            or saved.get("freshness") not in {"current", "historical"}):
        return "saved free-space publication identity is incomplete"
    cells = saved.get("cells")
    if not isinstance(cells, (tuple, list)) or len(cells) != grid.n_rows * grid.n_cols:
        return "saved free-space sample coverage is incomplete"
    source_ids = saved.get("source_ids")
    if (not isinstance(source_ids, (tuple, list))
            or any(not isinstance(refs, (tuple, list)) or any(not isinstance(ref, str) for ref in refs)
                   for refs in source_ids) or not isinstance(saved.get("support_context"), Mapping)):
        return "saved free-space shared sample metadata is malformed"
    for index, cell in enumerate(cells):
        if not isinstance(cell, Mapping) or cell.get("cell_key") != divmod(index, grid.n_cols):
            return "saved free-space samples are not in exact lattice order"
        status, value = cell.get("status"), cell.get("value")
        source_ref = cell.get("source_refs")
        if (not isinstance(source_ref, Mapping) or set(source_ref) != {"table", "index"}
                or source_ref["table"] != "free_space_result.source_ids"
                or type(source_ref["index"]) is not int or not 0 <= source_ref["index"] < len(source_ids)):
            return "saved free-space source reference does not resolve"
        if (status not in {item.value for item in FieldStatus}
                or (value is not None and type(value) is not bool)
                or (status in {"established", "conditional"}) != (value is not None)
                or not cell.get("query_ref") or "support" not in cell
                or not isinstance(cell.get("explanation"), str)
                or status == "conditional" and not cell["explanation"].strip()):
            return "saved free-space value/status/sample metadata is invalid"
    return None


def _neighbors(cell: tuple[int, int], grid: GridDescriptor) -> tuple:
    """Return existing four-neighbor cells in canonical index order."""
    row, col = cell
    return tuple(sorted((r, c) for r, c in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
                        if 0 <= r < grid.n_rows and 0 <= c < grid.n_cols))


def _route_neighbors(cell: tuple[int, int], grid: GridDescriptor) -> tuple:
    """Return canonical eight-neighbor route indexes without changing access edges."""
    row, col = cell
    return tuple((r, c) for r in range(max(0, row - 1), min(grid.n_rows, row + 2))
                 for c in range(max(0, col - 1), min(grid.n_cols, col + 2)) if (r, c) != cell)


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
    field = None if bundle.free_space_samples is not None else FreeSpaceField(domain=bundle.domain, origin=grid.origin, spacing=grid.spacing,
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
            if bundle.free_space_samples is not None:
                samples[cell] = {**bundle.free_space_samples["cells"][row * grid.n_cols + col],
                                 "center": _center(cell, grid)}
            else:
                sample = field.evaluate(cell, request)
                samples[cell] = {"cell_key": cell, "query_ref": f"{grid.grid_id}:cell:{row}:{col}",
                                 "status": sample.status.value, "value": sample.value, "source_refs": sample.source_ids,
                                 "support": sample.support, "explanation": sample.explanation, "center": _center(cell, grid)}
            sample = samples[cell]
            if not domain.covers(Point(_center(cell, grid))):
                continue
            if sample["value"] is False and sample["status"] in {"established", "conditional"}:
                observed.add_node(cell)
                optimistic.add_node(cell)
                frontier.add_node(cell)
            elif sample["status"] == "unknown":
                optimistic.add_node(cell)
                frontier.add_node(cell)
            elif sample["status"] in {"invalid", "not_available"}:
                # Failed queries remain failures; this graph identifies their relevant frontier only.
                frontier.add_node(cell)
    for cell in sorted(frontier):
        for neighbor in _route_neighbors(cell, grid):
            if neighbor <= cell or neighbor not in frontier:
                continue
            guards = tuple(sorted(((cell[0], neighbor[1]), (neighbor[0], cell[1])))) if (
                cell[0] != neighbor[0] and cell[1] != neighbor[1]) else ()
            # A diagonal depends on both flanks even though its centerline visits neither.
            if any(guard not in frontier for guard in guards):
                continue
            segment = LineString((_center(cell, grid), _center(neighbor, grid)))
            if not domain.covers(segment):
                continue
            weight = math.dist(_center(cell, grid), _center(neighbor, grid))
            data = {"weight": weight, "edge_key": (cell, neighbor), "domain_covered": True,
                    "domain_fingerprint": grid.domain_fingerprint, "grid_id": grid.grid_id,
                    "occupancy_query_refs": (samples[cell]["query_ref"], samples[neighbor]["query_ref"]),
                    "guard_cell_keys": guards,
                    "guard_query_refs": tuple(samples[guard]["query_ref"] for guard in guards),
                    "edge_support_version": EDGE_SUPPORT_VERSION}
            frontier.add_edge(cell, neighbor, **data)
            if cell in optimistic and neighbor in optimistic and all(guard in optimistic for guard in guards):
                optimistic.add_edge(cell, neighbor, **data)
            if cell in observed and neighbor in observed and all(guard in observed for guard in guards):
                observed.add_edge(cell, neighbor, **data)
    return samples, *_constrained_graphs(bundle, domain, samples, (observed, optimistic, frontier))


def _accesses(group: GroupProjection, geometry: dict, domain: Any, grid: GridDescriptor, samples: dict, frontier: nx.Graph,
              constrained: bool = False) -> dict:
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
            candidate = {"access_key": (group.group_id, cell, neighbor, endpoints), "group_id": group.group_id,
                         "footprint_cell": cell, "free_cell": neighbor, "shared_edge": endpoints,
                         "proxy_point": midpoint, "cell_center": free_center,
                         "offset": math.dist(centroid, midpoint) + math.dist(midpoint, free_center),
                         "query_ref": samples[neighbor]["query_ref"], "status": samples[neighbor]["status"]}
            if constrained:
                candidate.update(heading=_heading(_center(cell, grid), free_center),
                                 target_heading=_heading(free_center, _center(cell, grid)))
            candidates.append(candidate)
    selected, discarded = {}, []
    for candidate in sorted(candidates, key=lambda item: (item["offset"], item["access_key"])):
        cell = candidate["free_cell"]
        if cell in selected and not constrained:
            discarded.append(candidate)
        else:
            if constrained:
                selected[candidate["access_key"]] = candidate
                continue
            selected[cell] = candidate
    return {"outside": False, "footprint_cells": footprint, "selected": selected,
            "candidates": tuple(sorted(candidates, key=lambda item: item["access_key"])), "discarded": tuple(discarded),
            "query_cells": tuple(sorted(query_cells))}


def _heading(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
    """Return a stable unit heading for a positive-length route segment."""
    dx, dy = second[0] - first[0], second[1] - first[1]
    length = math.hypot(dx, dy)
    if length <= 0 or not math.isfinite(length):
        raise ValueError("route heading requires two distinct points")
    return dx / length, dy / length


def _ray_distance(point: tuple[float, float], direction: tuple[float, float], blockers: Any, boundary: Any) -> float:
    """Measure the first positive hit on a normal ray against mass or domain boundary."""
    extent = max(boundary.bounds[2] - boundary.bounds[0], boundary.bounds[3] - boundary.bounds[1], 1.0) * 4.0
    end = (point[0] + direction[0] * extent, point[1] + direction[1] * extent)
    ray = LineString((point, end))
    hits = []
    for geometry in (blockers, boundary.boundary):
        intersection = ray.intersection(geometry)
        if intersection.is_empty:
            continue
        for candidate in getattr(intersection, "geoms", (intersection,)):
            if not hasattr(candidate, "coords"):
                continue
            for coordinate in candidate.coords:
                distance = math.hypot(coordinate[0] - point[0], coordinate[1] - point[1])
                if distance > 1e-9:
                    hits.append(distance)
    return min(hits, default=float("inf"))


def _clearance_at(point: tuple[float, float], tangent: tuple[float, float], blockers: Any, domain: Any) -> tuple[float, float, float]:
    """Return left, right and total cross-section clearance at one route position."""
    left = (-tangent[1], tangent[0])
    right = (tangent[1], -tangent[0])
    left_distance = _ray_distance(point, left, blockers, domain)
    right_distance = _ray_distance(point, right, blockers, domain)
    return left_distance, right_distance, left_distance + right_distance


def _segment_positions(segment: LineString, blockers: Any, domain: Any) -> tuple[float, ...]:
    """Split a segment at projected polygon vertices so narrow interior bands are checked."""
    start = segment.coords[0]
    dx, dy = segment.coords[-1][0] - start[0], segment.coords[-1][1] - start[1]
    length_sq = dx * dx + dy * dy
    positions = {0.0, 1.0, 0.5}
    def rings(geometry):
        """Yield exterior and interior rings for polygon or multipolygon witnesses."""
        for polygon in getattr(geometry, "geoms", (geometry,)):
            if hasattr(polygon, "exterior"):
                yield polygon.exterior
                yield from polygon.interiors
    for geometry in (blockers, domain):
        for ring in rings(geometry):
            for coordinate in ring.coords:
                t = ((coordinate[0] - start[0]) * dx + (coordinate[1] - start[1]) * dy) / length_sq
                if 0.0 < t < 1.0:
                    positions.add(float(t))
    events = sorted(positions)
    positions.update((first + (second - first) / 2 for first, second in zip(events, events[1:])))
    return tuple(sorted(positions))


def _edge_clearance(first: tuple[int, int], second: tuple[int, int], grid: GridDescriptor,
                    blockers: Any, domain: Any, thresholds: tuple[float, float, float]) -> dict | None:
    """Evaluate continuous directional clearance over one positive-length grid edge."""
    start, end = _center(first, grid), _center(second, grid)
    segment = LineString((start, end))
    if segment.crosses(blockers) or segment.within(blockers) or segment.touches(blockers):
        return None
    tangent = _heading(start, end)
    values = []
    for position in _segment_positions(segment, blockers, domain):
        point = tuple(segment.interpolate(position, normalized=True).coords[0])
        left, right, total = _clearance_at(point, tangent, blockers, domain)
        values.append((left, right, total, position * segment.length))
    limiting = min(values, key=lambda value: (value[2], value[0], value[1], value[3]))
    minimum_left = min(value[0] for value in values)
    minimum_right = min(value[1] for value in values)
    minimum_total = min(value[2] for value in values)
    epsilon = 1e-12
    if minimum_left + epsilon < thresholds[0] or minimum_right + epsilon < thresholds[1] or minimum_total + epsilon < thresholds[2]:
        return None
    return {"min_left_m": minimum_left, "min_right_m": minimum_right, "min_total_m": minimum_total,
            "limiting_position_m": limiting[3], "limiting_left_m": limiting[0],
            "limiting_right_m": limiting[1], "limiting_total_m": limiting[2]}


def _turn_clearance(point: tuple[float, float], incoming: tuple[float, float], outgoing: tuple[float, float],
                    blockers: Any, domain: Any, thresholds: tuple[float, float, float]) -> dict | None:
    """Check the cross-section while the heading rotates through a grid vertex."""
    a = math.atan2(incoming[1], incoming[0])
    b = math.atan2(outgoing[1], outgoing[0])
    delta = (b - a + math.pi) % (2 * math.pi) - math.pi
    # Vertex and segment-direction events partition the ray-intersection
    # functions into intervals where endpoint/midpoint checks are sufficient.
    fractions = {0.0, 1.0}
    if abs(delta) > 1e-12:
        def add_angle(angle: float) -> None:
            """Add an angular event when it lies on the chosen shortest arc."""
            raw = angle - a
            while raw - delta > math.pi:
                raw -= 2 * math.pi
            while raw - delta < -math.pi:
                raw += 2 * math.pi
            if delta < 0 and raw > 0:
                raw -= 2 * math.pi
            if delta > 0 and raw < 0:
                raw += 2 * math.pi
            fraction = raw / delta
            if 0.0 < fraction < 1.0:
                fractions.add(float(fraction))

        def rings(geometry):
            """Yield polygon boundary rings for all geometry components."""
            for polygon in getattr(geometry, "geoms", (geometry,)):
                if hasattr(polygon, "exterior"):
                    yield polygon.exterior
                    yield from polygon.interiors

        for geometry in (blockers, domain):
            for ring in rings(geometry):
                coordinates = tuple(ring.coords)
                for vertex in coordinates[:-1]:
                    vertex_angle = math.atan2(vertex[1] - point[1], vertex[0] - point[0])
                    # The clearance rays are the tangent's left/right normals.
                    add_angle(vertex_angle - math.pi / 2)
                    add_angle(vertex_angle + math.pi / 2)
                for first, second in zip(coordinates, coordinates[1:]):
                    angle = math.atan2(second[1] - first[1], second[0] - first[0])
                    add_angle(angle)
                    add_angle(angle + math.pi)
                    add_angle(angle - math.pi / 2)
                    add_angle(angle + math.pi / 2)
    ordered = sorted(fractions)
    fractions.update(first + (second - first) / 2 for first, second in zip(ordered, ordered[1:]))
    samples = tuple(sorted(fractions))
    values = []
    for fraction in samples:
        angle = a + delta * fraction
        left, right, total = _clearance_at(point, (math.cos(angle), math.sin(angle)), blockers, domain)
        values.append((left, right, total, fraction))
    minimum_left, minimum_right, minimum_total = (min(item[index] for item in values) for index in range(3))
    epsilon = 1e-12
    if minimum_left + epsilon < thresholds[0] or minimum_right + epsilon < thresholds[1] or minimum_total + epsilon < thresholds[2]:
        return None
    limiting = min(values, key=lambda item: (item[2], item[0], item[1], item[3]))
    return {"min_left_m": minimum_left, "min_right_m": minimum_right, "min_total_m": minimum_total,
            "limiting_left_m": limiting[0], "limiting_right_m": limiting[1], "limiting_total_m": limiting[2],
            "limiting_angle_fraction": limiting[3]}


def _constrained_graphs(bundle: GroupDistanceInput, domain: Any, samples: Mapping, base_graphs: tuple) -> tuple:
    """Expand the retained graph into heading states when directional policy is enabled."""
    thresholds = _clearance_thresholds(bundle.clearance_policy)
    if thresholds is None:
        return base_graphs
    blockers = unary_union([_shape(record.get("geometry_components")) for record in bundle.physical_occupancy
                            if record.get("geometry_components")])
    observed_base, optimistic_base, frontier = base_graphs
    observed, optimistic = nx.DiGraph(), nx.DiGraph()
    for base in (observed_base, optimistic_base):
        target = observed if base is observed_base else optimistic
        directed = []
        for first, second, data in base.edges(data=True):
            for start, end in ((first, second), (second, first)):
                clearance = _edge_clearance(start, end, bundle.grid, blockers, domain, thresholds)
                if clearance is None:
                    continue
                
                heading = _heading(_center(start, bundle.grid), _center(end, bundle.grid))
                clearance = {**clearance, "physical_witness_refs": tuple(record.get("id") for record in bundle.physical_occupancy if record.get("id")),
                             "domain_witness_ref": bundle.grid.domain_fingerprint or "analysis-domain",
                             "side_sample_cell_keys": tuple(sorted({start, end, *data.get("guard_cell_keys", ())}))}
                directed.append((start, end, heading, {**data, "clearance": clearance, "heading": heading,
                                                       "edge_support_version": CLEARANCE_EDGE_SUPPORT_VERSION,
                                                       "from_cell": start, "to_cell": end}))
        headings_by_cell = {}
        for start, end, heading, data in directed:
            headings_by_cell.setdefault(start, set()).add(heading)
            headings_by_cell.setdefault(end, set()).add(heading)
            target.add_node((start, heading))
        for start, end, heading, data in directed:
            # A source access seeds the outgoing heading; later states pay for every turn.
            for incoming in sorted(headings_by_cell.get(start, ()), key=repr):
                turn = _turn_clearance(_center(start, bundle.grid), incoming, heading, blockers, domain, thresholds)
                if turn is None:
                    continue
                turn = {**turn,
                        "physical_witness_refs": tuple(record.get("id") for record in bundle.physical_occupancy if record.get("id")),
                        "domain_witness_ref": bundle.grid.domain_fingerprint or "analysis-domain"}
                target.add_edge((start, incoming), (end, heading), **{**data, "turn": turn})
    return (observed, optimistic, frontier)


def _state_accesses(accesses: Mapping, target: bool = False) -> dict:
    """Lift cell access records into heading states for constrained searches."""
    result = {}
    for key, access in accesses.items():
        cell = access.get("free_cell", key)
        heading = access.get("target_heading" if target else "heading")
        if heading is not None:
            result[(cell, tuple(heading))] = access
    return result


def _state_cell(node: Any) -> tuple[int, int]:
    """Read the lattice cell from either a legacy cell node or constrained state."""
    return node[0] if isinstance(node, tuple) and len(node) == 2 and isinstance(node[0], tuple) else node


def _recover_source(graph: nx.Graph, accesses: Mapping, samples: Mapping, optimistic: bool) -> tuple:
    """Recover deterministic representatives from exact NetworkX predecessor labels."""
    # A constrained source and target can share one free cell; retain its
    # heading state even when that cell has no positive-length graph edge.
    if graph.is_directed():
        graph.add_nodes_from(cell for cell in accesses if cell not in graph)
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
                    guards = ()
                else:
                    if distances[parent] >= distances[cell] or parent not in best:
                        raise ArithmeticError("tight physical predecessor is not an increasing DAG")
                    previous = best[parent]
                    guards = graph[parent][cell].get("guard_cell_keys", ())
                    unknown_alternatives.append(any_unknown[parent] or any(samples[_state_cell(guard)]["status"] == "unknown" for guard in guards))
                unknown, conditional, source, path = previous
                # Additive occurrences preserve optimal substructure when a flank repeats.
                support = (_state_cell(cell), *guards)
                choices.append((unknown + sum(samples[node]["status"] == "unknown" for node in support),
                                conditional + sum(samples[node]["status"] == "conditional" for node in support), source, path + (cell,)))
            if not choices:
                raise ArithmeticError("backend label has no exactly replayable predecessor")
            best[cell] = min(choices, key=lambda label: label if optimistic else label[1:])
            any_unknown[cell] = samples[_state_cell(cell)]["status"] == "unknown" or any(unknown_alternatives)
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
    guard_occurrences = tuple(guard for edge in edges for guard in edge.get("guard_cell_keys", ()))
    guards = tuple(sorted(set(guard_occurrences)))
    cell_path = tuple(_state_cell(node) for node in path)
    support = tuple(sorted(set(cell_path) | set(guards)))
    arithmetic = _arithmetic(source["offset"], tuple(edge["weight"] for edge in edges), target["offset"], key[0])
    clearance_records = tuple(edge["clearance"] for edge in edges if edge.get("clearance") is not None)
    clearance = None
    if clearance_records:
        limiting = min(clearance_records, key=lambda record: (record["min_total_m"], record["min_left_m"], record["min_right_m"]))
        clearance = {"min_left_m": min(record["min_left_m"] for record in clearance_records),
                     "min_right_m": min(record["min_right_m"] for record in clearance_records),
                     "min_total_m": min(record["min_total_m"] for record in clearance_records),
                     "limiting_segment_index": clearance_records.index(limiting),
                     "limiting_position_m": limiting["limiting_position_m"],
                     "limiting_left_m": limiting["limiting_left_m"],
                     "limiting_right_m": limiting["limiting_right_m"],
                     "limiting_total_m": limiting["limiting_total_m"],
                     "edge_witnesses": clearance_records,
                     "turn_witnesses": tuple(edge["turn"] for edge in edges if edge.get("turn") is not None),
                     "support_cell_keys": tuple(sorted(set(cell_path))),
                     "support_query_refs": tuple(samples[node]["query_ref"] for node in sorted(set(cell_path))),
                     "support_statuses": tuple(samples[node]["status"] for node in sorted(set(cell_path)))}
    route = {"value": key[0], "cell_keys": cell_path, "points": tuple(samples[_state_cell(node)]["center"] for node in path),
            "edges": edges, "source_access": source, "target_access": target,
            "conditional_cell_count": sum(samples[_state_cell(node)]["status"] == "conditional" for node in path),
            "unknown_cell_count": sum(samples[_state_cell(node)]["status"] == "unknown" for node in path),
            "conditional_support_occurrence_count": conditional, "unknown_support_occurrence_count": unknown,
            "conditional_guard_occurrence_count": sum(samples[node]["status"] == "conditional" for node in guard_occurrences),
            "unknown_guard_occurrence_count": sum(samples[node]["status"] == "unknown" for node in guard_occurrences),
            "guard_cell_keys": guards,
            "guard_query_refs": tuple(samples[node]["query_ref"] for node in guards),
            "support_cell_keys": support, "support_query_refs": tuple(samples[node]["query_ref"] for node in support),
            "conditional_support_cell_count": sum(samples[node]["status"] == "conditional" for node in support),
            "unknown_support_cells": tuple(node for node in support if samples[node]["status"] == "unknown"),
            "cells": tuple(samples[_state_cell(node)] for node in path), "arithmetic": arithmetic,
            "unknown_cells": tuple(_state_cell(node) for node in path if samples[_state_cell(node)]["status"] == "unknown"),
            "has_unknown_tie": any(any_unknown[end] for candidate, end, _ in candidates if candidate[0] == key[0]),
            }
    if graph.is_directed():
        route["state_keys"] = path
        route["clearance"] = clearance
    return route


def _failure_cells(first: dict, second: dict, component_failures: Mapping, samples: Mapping) -> tuple:
    """Limit failed queries to endpoint queries and their connected search frontier."""
    relevant = set(first["query_cells"]) | set(second["query_cells"])
    for access in (first, second):
        for key, candidate in access["selected"].items():
            cell = candidate.get("free_cell", key)
            relevant.update(component_failures.get(cell, ()))
    return tuple(samples[cell] for cell in sorted(relevant) if samples[cell]["status"] in {"invalid", "not_available"})


def _component_failure_cells(frontier: nx.Graph, samples: Mapping) -> dict:
    """Include edge guards even when exact geometry disconnects their own node."""
    failures = {}
    for component in nx.connected_components(frontier):
        support = set(component)
        support.update(guard for cell in component for edge in frontier[cell].values() for guard in edge["guard_cell_keys"])
        failed = tuple(sorted(cell for cell in support if samples[cell]["status"] in {"invalid", "not_available"}))
        failures.update((cell, failed) for cell in component)
    return failures


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
            component_failures = _component_failure_cells(frontier, samples)
            for group in groups:
                if geometry[group.group_id]["status"] == "computed":
                    access[group.group_id] = _accesses(group, geometry[group.group_id], domain, bundle.grid, samples, frontier,
                                                        bundle.clearance_policy is not None)
            for mode, graph in (("observed", observed), ("optimistic", optimistic)):
                runs = 0
                constrained = bundle.clearance_policy is not None
                for index, source in enumerate(groups[:-1]):
                    if source.group_id not in access or access[source.group_id]["outside"]:
                        continue
                    try:
                        source_selected = (_state_accesses(access[source.group_id]["selected"]) if constrained
                                           else access[source.group_id]["selected"])
                        if any(cell in graph for cell in source_selected):
                            runs += 1
                        distances, best, unknown = _recover_source(graph, source_selected, samples, mode == "optimistic")
                        for target in groups[index + 1:]:
                            if target.group_id in access and not access[target.group_id]["outside"]:
                                target_selected = (_state_accesses(access[target.group_id]["selected"], target=True)
                                                   if constrained else access[target.group_id]["selected"])
                                routes.setdefault((source.group_id, target.group_id), {})[mode] = _target_route(
                                    graph, target_selected, source_selected,
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
                    status = "partial" if selected["conditional_support_cell_count"] or lower and selected["value"] - lower["value"] > tau else "computed"
                else:
                    status = "unknown" if lower is not None else "unreachable"
        hybrid = {"status": status, "value": selected["value"] if selected else None, "units": "m", "reason": explanation,
                  "optimistic_lower_bound": lower["value"] if lower else None, "discrete_approximation": True,
                  "conditional_cell_count": selected["conditional_cell_count"] if selected else None,
                  "unknown_cell_count": lower["unknown_cell_count"] if lower else None,
                  "conditional_support_occurrence_count": selected["conditional_support_occurrence_count"] if selected else None,
                  "unknown_support_occurrence_count": lower["unknown_support_occurrence_count"] if lower else None,
                  "conditional_support_cell_count": selected["conditional_support_cell_count"] if selected else None,
                  "unknown_support_cell_count": len(lower["unknown_support_cells"]) if lower else None,
                  "arithmetic": selected["arithmetic"] if selected else None,
                  "tie_uncertainty": bool(selected and lower and lower["has_unknown_tie"] and abs(selected["value"] - lower["value"]) <= max(math.ulp(selected["value"]), math.ulp(lower["value"]), math.ulp(bundle.grid.spacing)))}
        if bundle.clearance_policy is not None:
            hybrid["clearance_policy"] = bundle.clearance_policy
            hybrid["clearance"] = selected.get("clearance") if selected else None
        if selected:
            hybrid.update(source_centroid_to_access_offset=selected["arithmetic"]["source_offset"],
                          free_space_route_distance=selected["arithmetic"]["route_edge_sum"], target_access_to_centroid_offset=selected["arithmetic"]["target_offset"])
            selected = {**selected, "source_centroid": audits[ids[0]]["centroid"], "target_centroid": audits[ids[1]]["centroid"]}
        pair_id = _pair_id(ids, bundle.source_identity)
        lineage = {"group_source_refs": {group.group_id: group.source_refs for group in groups if group.group_id in ids},
                   "failed_queries": failures,
                   "observed_query_refs": selected["support_query_refs"] if selected else (),
                   "optimistic_lower_bound": lower,
                   "access_audit": {identity: {name: access[identity][name] for name in ("footprint_cells", "candidates", "discarded")} for identity in ids if identity in access}}
        observations.append(GroupPairDistanceObservation(pair_id, ids, euclidean, hybrid, audits, selected, lineage, fingerprints))
        pair_index.append({"pair_id": pair_id, "group_ids": ids, "observation_index": len(observations) - 1})
    _, peak = tracemalloc.get_traced_memory()
    constrained = bundle.clearance_policy is not None
    manifest = {"algorithm_version": CLEARANCE_ALGORITHM_VERSION if constrained else ALGORITHM_VERSION,
                "schema_version": CLEARANCE_SCHEMA_VERSION if constrained else SCHEMA_VERSION,
                "edge_support_version": CLEARANCE_EDGE_SUPPORT_VERSION if constrained else EDGE_SUPPORT_VERSION,
                "arithmetic_version": ARITHMETIC_VERSION, "source_identity": bundle.source_identity,
                "analysis_plane": bundle.analysis_plane, "domain": bundle.domain, "grid": bundle.grid,
                "query": bundle.query, "query_context": bundle.query_context, "origin_offset": bundle.origin_offset, "units": "m", "group_ids": tuple(group.group_id for group in groups),
                "expected_pair_ids": tuple(item["pair_id"] for item in pair_index), "expected_pair_count": len(pairs),
                "dependency_fingerprints": fingerprints, "cell_samples": tuple(samples[cell] for cell in sorted(samples)),
                "python_version": platform.python_version(), "networkx_version": nx.__version__}
    if constrained:
        manifest["clearance_policy_version"] = CLEARANCE_POLICY_VERSION
        manifest["clearance_policy"] = bundle.clearance_policy
    if bundle.free_space_samples is not None:
        manifest["free_space_result"] = {key: bundle.free_space_samples[key] for key in
            ("result_ref", "freshness", "identity", "backend_versions", "content_cache", "calculation_provenance",
             "source_ids", "support_context")}
    diagnostics = {"global_status": global_status, "global_explanation": global_explanation,
                   "graphs": graph_stats, "source_batched": True, "second_dijkstra": False,
                   "runtime_s": time.perf_counter() - started, "tracemalloc_peak_bytes": peak,
                   "numerical_contract_failures": tuple({"source_group_id": key[0], "mode": key[1], "explanation": reason} for key, reason in sorted(search_failures.items())),
                   "observed_statuses": tuple(sorted({item.centroid_free_space_hybrid["status"] for item in observations}))}
    return GroupDistanceResult(tuple(observations), pair_index, manifest, diagnostics)
