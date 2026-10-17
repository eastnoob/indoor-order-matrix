"""Run a bounded, diagnostic-only B3 space-field experiment.

The script keeps synthetic 3D source volumes, an explicit floor datum, and
separate lower-body, eye-level, and overhead occupancy queries.  Its JSON is
exploratory evidence rather than a production field contract.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

import shapely
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union


FLOOR_DATUM_Z_M = 0.0
DEFAULT_EYE_HEIGHT_M = 1.6
DEFAULT_EYE_BAND_THICKNESS_M = 0.10


def height_queries(eye_height_m: float = DEFAULT_EYE_HEIGHT_M, eye_band_m: tuple[float, float] | None = None, floor_datum_z_m: float = FLOOR_DATUM_Z_M, eye_band_thickness_m: float = DEFAULT_EYE_BAND_THICKNESS_M) -> tuple[dict[str, Any], ...]:
    """Resolve provisional height offsets from an explicit absolute floor datum."""
    if not _finite((eye_height_m, floor_datum_z_m, eye_band_thickness_m)) or eye_band_thickness_m <= 0:
        raise ValueError("Datum, eye offset and positive total band thickness must be finite")
    if eye_band_m is None:
        eye_band_m = (eye_height_m - eye_band_thickness_m / 2, eye_height_m + eye_band_thickness_m / 2)
    if not _finite(eye_band_m) or len(eye_band_m) != 2 or eye_band_m[0] >= eye_band_m[1]:
        raise ValueError("Eye band offsets must be finite and ordered")
    # Coordinate support stays fixed; only the query heights resolve from datum.
    queries = []
    for identifier, role, offsets, plane_offset in (
        ("lower_height_reference", "lower_height", (0.0, 1.5), None),
        ("eye_level_reference", "eye_reference", eye_band_m, eye_height_m),
        ("overhead_reference", "overhead", (2.0, 3.5), None),
    ):
        queries.append({"id": identifier, "role": role, "band_offset_m": list(offsets), "band_z_m": [floor_datum_z_m + value for value in offsets], "plane_z_m": None if plane_offset is None else floor_datum_z_m + plane_offset, "plane_offset_m": plane_offset, "eye_offset_m": plane_offset if role == "eye_reference" else None, "band_thickness_m": offsets[1] - offsets[0], "status": "provisional_configurable_not_anthropometric_standard", "units": "m"})
    return tuple(queries)


@dataclass(frozen=True)
class Box3D:
    """Describe an extruded synthetic polygon with absolute 3D heights in metres."""

    id: str
    xy: Polygon
    z_min: float
    z_max: float
    role: str = "occupancy"
    group_id: str | None = None

    def overlaps_band(self, band: tuple[float, float]) -> bool:
        """Return whether this volume has positive vertical overlap with a band."""
        return self.z_min < band[1] and self.z_max > band[0]

    def intersects_plane(self, height: float) -> bool:
        """Return whether this volume contains an interior horizontal plane."""
        return self.z_min < height < self.z_max


def fixture_cases() -> dict[str, dict[str, Any]]:
    """Return explicit 3D-ready fixtures for the bounded exploratory slice."""
    domain = box(0.0, 0.0, 10.0, 8.0)
    pockets = domain.difference(unary_union([box(1, 1, 3, 3), box(7, 5, 9, 7)]))
    return {
        "empty": {"domain": domain, "obstacles": [], "groups": []},
        "fully_occupied": {"domain": domain, "obstacles": [Box3D("full", domain, 0, 4)], "groups": []},
        "vertical_obstacle": {"domain": domain, "obstacles": [Box3D("vertical", box(4, 2, 6, 6), 0, 3, group_id="vertical")], "groups": [("vertical", (5.0, 4.0))]},
        "low_blocker": {"domain": domain, "obstacles": [Box3D("low", box(1, 1, 3, 3), 0, 1, group_id="low")], "groups": [("low", (2.0, 2.0))]},
        "high_blocker": {"domain": domain, "obstacles": [Box3D("high", box(7, 1, 9, 3), 2, 4, group_id="high")], "groups": [("high", (8.0, 2.0))]},
        "overhang": {
            "domain": domain,
            # Both volumes retain their shared authored source identity.
            "obstacles": [
                Box3D("overhang-support", box(4.5, 3.5, 5.5, 4.5), 0, 1.2, group_id="overhang"),
                Box3D("overhang-canopy", box(3.5, 2.5, 6.5, 5.5), 2, 4, group_id="overhang"),
            ],
            "groups": [("overhang", (5.0, 4.0))],
        },
        "narrow_gap": {
            "domain": domain,
            "obstacles": [Box3D("left", box(3, 0, 4.7, 8), 0, 3, group_id="left"), Box3D("right", box(5.3, 0, 7, 8), 0, 3, group_id="right")],
            "groups": [("left", (3.85, 4.0)), ("right", (6.15, 4.0))],
        },
        "connecting_passage": {"domain": domain, "obstacles": [Box3D("wall-west", box(0, 3, 4.7, 5), 0, 3), Box3D("wall-east", box(5.3, 3, 10, 5), 0, 3)], "groups": []},
        "exact_closed_passage": {"domain": domain, "obstacles": [Box3D("closed-wall", box(0, 3, 10, 5), 0, 3)], "groups": []},
        "edge_touch": {"domain": domain, "obstacles": [Box3D("a", box(0, 3, 5, 5), 0, 3), Box3D("b", box(5, 3, 10, 5), 0, 3)], "groups": []},
        "point_touch": {"domain": domain, "obstacles": [Box3D("a", box(0, 0, 5, 4), 0, 3), Box3D("b", box(5, 4, 10, 8), 0, 3)], "groups": []},
        "disconnected_pockets": {"domain": domain, "obstacles": [Box3D("surround", pockets, 0, 3)], "groups": []},
        "eye_face_contact": {"domain": domain, "obstacles": [Box3D("top-at-eye", box(1, 1, 3, 3), 0, 1.6), Box3D("bottom-at-eye", box(7, 5, 9, 7), 1.6, 3)], "groups": []},
        "domain_hole_out_of_domain": {"domain": Polygon([(0, 0), (10, 0), (10, 8), (0, 8)], holes=[[(4, 3), (6, 3), (6, 5), (4, 5)]]), "obstacles": [Box3D("outside", box(11, 1, 12, 2), 0, 3), Box3D("inside-hole", box(4, 3, 6, 5), 0, 3)], "groups": []},
        "missing_domain": {"domain": None, "obstacles": [], "groups": []},
        "missing_obstacles": {"domain": domain, "groups": []},
        "missing_groups": {"domain": domain, "obstacles": []},
        "invalid_geometry": {"domain": domain, "obstacles": [Box3D("bowtie", Polygon([(0, 0), (2, 2), (0, 2), (2, 0)]), 0, 3)], "groups": []},
        "nonfinite_height": {"domain": domain, "obstacles": [Box3D("nonfinite", box(1, 1, 2, 2), 0, math.inf)], "groups": []},
        "nonfinite_group": {"domain": domain, "obstacles": [], "groups": [("bad", (math.nan, 1.0))]},
    }


def _finite(values: object) -> bool:
    """Return whether every supplied numeric value is finite."""
    try:
        return all(isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value) for value in values)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _valid_polygon(geometry: object) -> bool:
    """Return whether a polygon can be used as finite planar evidence."""
    return isinstance(geometry, Polygon) and not geometry.is_empty and geometry.is_valid and _finite(value for ring in [geometry.exterior, *geometry.interiors] for coordinate in ring.coords for value in coordinate)


def _validate_case(case: Mapping[str, Any]) -> tuple[str, list[str], list[Box3D] | None, list[tuple[str, tuple[float, float]]] | None]:
    """Validate source inputs before any height qualification is attempted."""
    missing: list[str] = []
    obstacles = case.get("obstacles")
    groups = case.get("groups")
    if obstacles is None:
        missing.append("obstacle_list")
    elif not isinstance(obstacles, list):
        return "invalid", ["obstacle_list"], None, None
    elif any(not isinstance(item, Box3D) or not item.id or not _valid_polygon(item.xy) or not _finite((item.z_min, item.z_max)) or item.z_min >= item.z_max for item in obstacles):
        return "invalid", ["valid_obstacle_geometry_and_heights"], None, None
    if groups is None:
        missing.append("groups")
        normalized_groups = None
    elif not isinstance(groups, list) or any(not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str) or not item[0] or not isinstance(item[1], tuple) or len(item[1]) != 2 or not _finite(item[1]) for item in groups):
        return "invalid", ["valid_groups"], None, None
    else:
        normalized_groups = groups
    if missing:
        status = "partial" if missing == ["groups"] and isinstance(obstacles, list) else "not_available"
        return status, missing, obstacles if isinstance(obstacles, list) else None, normalized_groups
    return "available", [], obstacles, normalized_groups


def _sample_grid(domain: Polygon, spacing: float, origin: tuple[float, float]) -> list[tuple[int, int, float, float]]:
    """Return cell-center samples for a declared spacing and origin offset."""
    xmin, ymin, xmax, ymax = domain.bounds
    samples: list[tuple[int, int, float, float]] = []
    # Negative indices include centers shifted back into the bounding extent.
    for i in range(math.ceil(-origin[0] / spacing - 0.5), math.floor((xmax - xmin - origin[0]) / spacing - 0.5) + 1):
        for j in range(math.ceil(-origin[1] / spacing - 0.5), math.floor((ymax - ymin - origin[1]) / spacing - 0.5) + 1):
            x, y = xmin + origin[0] + (i + 0.5) * spacing, ymin + origin[1] + (j + 0.5) * spacing
            if xmin <= x <= xmax and ymin <= y <= ymax:
                samples.append((i, j, x, y))
    return samples


def _polygon_parts(geometry: Any) -> list[Polygon]:
    """Keep only positive-area polygon interiors, excluding line/point contacts."""
    if isinstance(geometry, Polygon):
        return [geometry] if geometry.area > 0 else []
    return [part for child in getattr(geometry, "geoms", []) for part in _polygon_parts(child)]


def _rings(geometry: Any) -> list[dict[str, Any]]:
    """Serialize every polygon ring without discarding structural holes."""
    # Rings are intermediates for auditing the sampled field, not its final form.
    return [{"exterior_m": list(part.exterior.coords), "interiors_m": [list(ring.coords) for ring in part.interiors]} for part in _polygon_parts(geometry)]


def _sampled_components(channels: list[dict[str, Any]], mask: str, diagonal: bool) -> int:
    """Count free lattice components with explicit four or eight neighbor adjacency."""
    remaining = {(cell["cell_i"], cell["cell_j"]) for cell in channels if cell["domain_mask"] and not cell[mask]}
    offsets = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di or dj) and (diagonal or abs(di) + abs(dj) == 1)]
    count = 0
    # Integer keys prevent floating-point coordinate equality from defining edges.
    while remaining:
        stack = [remaining.pop()]
        count += 1
        while stack:
            i, j = stack.pop()
            for di, dj in offsets:
                neighbor = (i + di, j + dj)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return count


def _clearance_summary(channels: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """Summarize retained computed values without turning empty evidence into zero."""
    values = [cell[key] for cell in channels if cell[key] is not None]
    return {"count": len(values), "min_m": min(values) if values else None, "max_m": max(values) if values else None, "mean_m": sum(values) / len(values) if values else None}


def _observation(domain: Polygon, raw: Any, channels: list[dict[str, Any]], kind: str, spacing: float) -> dict[str, Any]:
    """Compare vector free interiors with complete sampled masks and clearances."""
    clipped = domain.intersection(raw)
    free = domain.difference(raw)
    mask = f"{kind}_occupancy_mask"
    vector = len(_polygon_parts(free))
    four, eight = _sampled_components(channels, mask, False), _sampled_components(channels, mask, True)
    sampled_domain = sum(cell["domain_mask"] for cell in channels) * spacing ** 2
    sampled_occupancy = sum(cell[mask] for cell in channels) * spacing ** 2
    # Reconstructed cells expose balanced classification error hidden by totals.
    cells = [box(cell["x_m"] - spacing / 2, cell["y_m"] - spacing / 2, cell["x_m"] + spacing / 2, cell["y_m"] + spacing / 2) for cell in channels]
    reconstructed = unary_union([geometry for cell, geometry in zip(channels, cells) if cell[mask]]).intersection(domain)
    unrepresented_area = float(domain.difference(unary_union(cells)).area)
    false_occupied = reconstructed.difference(clipped)
    false_free = clipped.difference(reconstructed)
    discrepancy = four != vector or eight != vector
    return {"vector_reference": "Shapely_floating_point_positive_area_polygon_interiors", "raw_occupancy_area_m2": float(raw.area), "outside_domain_occupancy_area_m2": float(raw.difference(domain).area), "clipped_occupancy_area_m2": float(clipped.area), "free_area_m2": float(free.area), "raw_occupancy_polygons": _rings(raw), "clipped_occupancy_polygons": _rings(clipped), "free_polygons": _rings(free), "vector_free_components": vector, "sampled_4_neighbor_free_components": four, "sampled_8_neighbor_free_components": eight, "eight_neighbor_policy": "all_diagonal_adjacency_no_corner_cut_filter_not_a_route_claim", "sampled_domain_area_m2": sampled_domain, "sampled_occupancy_area_m2": sampled_occupancy, "domain_area_error_m2": sampled_domain - domain.area, "occupancy_area_error_m2": sampled_occupancy - clipped.area, "sampled_free_area_error_m2": sampled_domain - sampled_occupancy - free.area, "area_estimate_method": "point_center_count_times_cell_area_non_conservative", "reconstructed_center_labeled_cells": {"role": "diagnostic_only_primary_evidence_remains_point_samples", "clipping": "exact_domain_including_holes", "unrepresented_domain_area_m2": unrepresented_area, "unrepresented_domain_policy": "no_occupied_reconstructed_cell_unrepresented_area_reported_separately", "occupancy_area_m2": float(reconstructed.area), "symmetric_difference_area_m2": float(reconstructed.symmetric_difference(clipped).area), "false_free_area_m2": float(false_free.area), "false_occupied_area_m2": float(false_occupied.area), "polygons": _rings(reconstructed)}, "clearance_to_occupancy_summary": _clearance_summary(channels, f"clearance_to_{kind}_occupancy_m"), "connectivity_discrepancy": discrepancy, "affected_stability_claim": "component_count_stability_unsupported_for_this_variant" if discrepancy else "component_counts_agree_no_stability_threshold_selected", "walkability": "not_computed"}


def _audit_geometry(obstacles: list[Box3D], domain: Polygon | None = None) -> list[dict[str, Any]]:
    """Serialize source geometry so projected occupancy remains auditable."""
    # Source ids and all rings survive clipping and height qualification.
    return [{"id": item.id, "source_identity": item.group_id or item.id, "group_id": item.group_id, "role": item.role, "xy_ring_m": list(item.xy.exterior.coords), "xy_holes_m": [list(r.coords) for r in item.xy.interiors], "z_range_m": [item.z_min, item.z_max], "raw_area_m2": float(item.xy.area), "clipped_area_m2": float(domain.intersection(item.xy).area) if domain is not None else None} for item in obstacles]


def _occupancy(obstacles: list[Box3D], predicate: Any) -> tuple[Any, list[Box3D]]:
    """Build a union for sources qualifying under one declared height query."""
    active = [item for item in obstacles if predicate(item)]
    return (unary_union([item.xy for item in active]) if active else Polygon()), active


def evaluate_case(name: str, case: Mapping[str, Any], *, query: Mapping[str, Any] | None = None, band: tuple[float, float] | None = None, spacing: float = 1.0, origin: tuple[float, float] = (0.0, 0.0), bandwidth: float = 2.0, floor_datum_z_m: float = FLOOR_DATUM_Z_M) -> dict[str, Any]:
    """Evaluate separate occupancy, clearance, and group-support observations."""
    query = dict(height_queries(floor_datum_z_m=floor_datum_z_m)[1] if query is None else query)
    if band is not None:
        query["band_z_m"] = band
    height_band = tuple(query.get("band_z_m", ()))
    plane_z = query.get("plane_z_m")
    if not _finite((*height_band, spacing, *origin, bandwidth, floor_datum_z_m)) or len(height_band) != 2 or len(origin) != 2 or height_band[0] >= height_band[1] or spacing <= 0 or bandwidth <= 0 or (plane_z is not None and not _finite((plane_z,))):
        raise ValueError("Query heights, spacing, origin and bandwidth must be finite and ordered")
    domain = case.get("domain")
    provenance: dict[str, Any] = {
        "case": name, "status": "available", "missingness": [], "units": "m",
        "query": {"id": query.get("id", "custom"), "role": query.get("role", "custom"), "band_z_m": list(height_band), "plane_z_m": plane_z, "eye_offset_m": query.get("eye_offset_m"), "projection": "positive_vertical_overlap_band", "plane_section": "strict_open_interior_horizontal_plane" if plane_z is not None else "not_requested", "plane_convention": "experimental_open_interior_excludes_exact_top_bottom_faces"},
        "spacing_m": spacing, "origin_offset_m": list(origin), "gaussian_bandwidth_m": bandwidth,
        "semantic_status": "diagnostic_only", "source_revision": "synthetic_fixture_v3",
        "visibility": {"status": "not_computed", "reason": "eye_occupancy_is_not_a_visibility_claim"},
        "algorithm": "shapely_point_queries_positive_overlap_and_plane_section_v3",
    }
    provenance["frame"] = {"id": "synthetic_cartesian_xy_z_up", "floor_datum_z_m": floor_datum_z_m, "level_reference": {"source_role": "synthetic_authored_storey_level_fixture", "elevation": floor_datum_z_m, "units": "m", "frame": "synthetic_cartesian_xy_z_up", "qualification_status": "explicit_authored_fixture_value_not_actual_ifc"}, "projection_support_plane": {"id": "world_xy", "z_m": floor_datum_z_m}, "source_heights": "absolute_world_z_not_translated_when_query_datum_changes", "geometric_slab_z_role": "audit_only_not_datum_inference"}
    provenance["query"].update(plane_offset_m=None if plane_z is None else plane_z - floor_datum_z_m, band_offset_m=[height - floor_datum_z_m for height in height_band], band_thickness_m=height_band[1] - height_band[0], status="provisional_configurable_not_anthropometric_standard", units="m")
    provenance.update(clearance_target="raw_qualifying_occupancy_including_out_of_domain_sources", boundary_clearance_target="domain_exterior_and_hole_boundaries", sample_mask_convention="domain_covers_and_closed_xy_occupancy_covers", shapely_version=shapely.__version__)
    if domain is None:
        provenance.update(status="not_available", missingness=["analysis_domain"])
        return {"provenance": provenance, "channels": None, "exact": None, "audit_geometry": None}
    if not _valid_polygon(domain):
        provenance.update(status="invalid", missingness=["valid_analysis_domain"])
        return {"provenance": provenance, "channels": None, "exact": None, "audit_geometry": None}
    xmin, ymin, xmax, ymax = domain.bounds
    provenance.update(lattice_anchor_m=[xmin, ymin], spacing_to_extent_ratio=[spacing / (xmax - xmin), spacing / (ymax - ymin)])
    source_status, missingness, obstacles, groups = _validate_case(case)
    if obstacles is None:
        provenance.update(status=source_status, missingness=missingness)
        return {"provenance": provenance, "channels": None, "exact": None, "audit_geometry": None}
    provenance.update(status=source_status, missingness=missingness, source_volumes=_audit_geometry(obstacles, domain), domain_ring_m=list(domain.exterior.coords), domain_holes_m=[list(r.coords) for r in domain.interiors])
    provenance["groups"] = None if groups is None else [{"id": identifier, "center_m": list(center)} for identifier, center in groups]
    band_occupancy, band_sources = _occupancy(obstacles, lambda item: item.overlaps_band(height_band))
    plane_occupancy, plane_sources = _occupancy(obstacles, lambda item: plane_z is not None and item.intersects_plane(float(plane_z)))
    clipped_band = domain.intersection(band_occupancy)
    clipped_plane = domain.intersection(plane_occupancy)
    # Qualification retains each original volume, even when it clips to no area.
    for source in provenance["source_volumes"]:
        source.update(band_qualified=source["id"] in {item.id for item in band_sources}, plane_qualified=None if plane_z is None else source["id"] in {item.id for item in plane_sources}, qualification_query_id=query.get("id", "custom"))
    samples = _sample_grid(domain, spacing, origin)
    channels = []
    for i, j, x, y in samples:
        point = Point(x, y)
        in_domain = bool(domain.covers(point))
        occupied = bool(in_domain and band_occupancy.covers(point))
        # Empty source evidence is distinct from unavailable source evidence.
        clearance_status = "not_available" if not in_domain else ("known_empty" if band_occupancy.is_empty else "computed")
        clearance = None if band_occupancy.is_empty or not in_domain else (0.0 if occupied else float(point.distance(band_occupancy)))
        plane_occupied = None if plane_z is None else bool(in_domain and plane_occupancy.covers(point))
        plane_clearance_status = "not_requested" if plane_z is None else ("not_available" if not in_domain else ("known_empty" if plane_occupancy.is_empty else "computed"))
        plane_clearance = None if plane_z is None or plane_occupancy.is_empty or not in_domain else (0.0 if plane_occupied else float(point.distance(plane_occupancy)))
        support_status = "not_available" if groups is None else ("known_empty" if not groups else "computed")
        support = None if groups is None else sum(math.exp(-((point.distance(Point(center)) / bandwidth) ** 2)) for _, center in groups)
        channels.append({"cell_i": i, "cell_j": j, "x_m": x, "y_m": y, "domain_mask": in_domain, "band_occupancy_mask": occupied, "plane_occupancy_mask": plane_occupied, "occupancy_mask": occupied, "clearance_to_band_occupancy_m": clearance, "clearance_to_band_occupancy_status": clearance_status, "clearance_to_plane_occupancy_m": plane_clearance, "clearance_to_plane_occupancy_status": plane_clearance_status, "clearance_to_occupancy_m": clearance, "clearance_to_occupancy_status": clearance_status, "clearance_to_domain_boundary_m": float(point.distance(domain.boundary)) if in_domain else None, "clearance_to_domain_boundary_status": "computed" if in_domain else "not_available", "gaussian_group_support_raw": support, "gaussian_group_support_status": support_status})
    # Plane and band share coordinates/domain/bandwidth but retain separate evidence.
    band_observation = _observation(domain, band_occupancy, channels, "band", spacing)
    plane_observation = None if plane_z is None else _observation(domain, plane_occupancy, channels, "plane", spacing)
    exact = {
        **band_observation,
        "domain_area_m2": float(domain.area),
        "positive_overlap_band_occupancy_area_m2": float(clipped_band.area),
        "plane_section_occupancy_area_m2": None if plane_z is None else float(clipped_plane.area),
        "positive_overlap_source_ids": [item.id for item in band_sources],
        "plane_section_source_ids": None if plane_z is None else [item.id for item in plane_sources],
        "sampling_spacing_m": spacing,
        "sampling_origin_offset_m": list(origin),
        "eye_plane_band_mask_disagreement_count": None if plane_z is None else sum(cell["plane_occupancy_mask"] != cell["band_occupancy_mask"] for cell in channels if cell["domain_mask"]),
        "clearance_to_boundary_summary": _clearance_summary(channels, "clearance_to_domain_boundary_m"),
    }
    return {
        "provenance": provenance,
        "channels": channels,
        "observations": {"positive_overlap_band": band_observation, "open_interior_plane": plane_observation},
        "audit_geometry": {"domain_polygons": _rings(domain), "source_occupancy": {"area_m2": float(band_occupancy.area), "source_ids": [item.id for item in band_sources]}, "domain_clipped_occupancy": {"area_m2": float(clipped_band.area), "source_ids": [item.id for item in band_sources]}},
        "exact": exact,
    }


def run_experiment(eye_height_m: float = DEFAULT_EYE_HEIGHT_M, eye_band_m: tuple[float, float] | None = None, floor_datum_z_m: float = FLOOR_DATUM_Z_M, eye_band_thickness_m: float = DEFAULT_EYE_BAND_THICKNESS_M) -> dict[str, Any]:
    """Run every fixture across named queries and sampling sensitivity variants."""
    queries = height_queries(eye_height_m, eye_band_m, floor_datum_z_m, eye_band_thickness_m)
    eye_query = queries[1]
    outputs: dict[str, Any] = {"schema": "b3-space-field-exploratory/v3", "status": "diagnostic_only", "floor_datum_z_m": floor_datum_z_m, "level_reference": {"source_role": "synthetic_authored_storey_level_fixture", "elevation": floor_datum_z_m, "units": "m", "frame": "synthetic_cartesian_xy_z_up", "qualification_status": "explicit_authored_fixture_value_not_actual_ifc", "geometric_slab_z_role": "audit_only_not_datum_inference"}, "coordinate_support_frame": {"id": "synthetic_cartesian_xy_z_up", "projection_support_plane": "world_xy", "floor_datum_z_m": floor_datum_z_m}, "default_analysis_reference": dict(eye_query), "cases": {}}
    for name, case in fixture_cases().items():
        domain = case.get("domain")
        extent = min(domain.bounds[2] - domain.bounds[0], domain.bounds[3] - domain.bounds[1]) if _valid_polygon(domain) else 8.0
        # Scene-relative spacings each receive zero and shifted lattice origins.
        variants = [(extent / divisor, origin) for divisor in (8, 16, 32) for origin in ((0.0, 0.0), (extent / divisor / 4, extent / divisor / 4))]
        outputs["cases"][name] = {"queries": {query["id"]: evaluate_case(name, case, query=query, floor_datum_z_m=floor_datum_z_m) for query in queries}, "sensitivity": [evaluate_case(name, case, query=eye_query, spacing=spacing, origin=origin, floor_datum_z_m=floor_datum_z_m) for spacing, origin in variants]}
    outputs["interpretation"] = {"polygon_role": "intermediate_geometry_and_vector_reference_only", "primary_field": "complete_coordinate_indexed_point_samples", "reconstructed_cells": "diagnostic_non_conservative_comparison_only", "eye_level_reference": "provisional_configurable_occupancy_query_not_coordinate_frame", "visibility": "not_computed", "walkability": "not_computed", "route_or_body_width": "not_computed", "gaussian_support": "diagnostic_physical_distance_evidence_not_probability_or_fusion", "stability_threshold": "not_selected"}
    return outputs


def main() -> int:
    """Write strict JSON evidence to the requested artifact path."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--eye-height", type=float, default=DEFAULT_EYE_HEIGHT_M)
    parser.add_argument("--floor-datum", type=float, default=FLOOR_DATUM_Z_M)
    parser.add_argument("--eye-band", type=float, nargs=2, metavar=("LOW_OFFSET", "HIGH_OFFSET"))
    parser.add_argument("--eye-band-thickness", type=float, default=DEFAULT_EYE_BAND_THICKNESS_M)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run_experiment(args.eye_height, None if args.eye_band is None else tuple(args.eye_band), args.floor_datum, args.eye_band_thickness)
    except ValueError as error:
        parser.error(str(error))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
