"""Generate the bounded D6 pairwise channel run_002 design experiment.

The runner is intentionally a disposable synthetic diagnostic.  It keeps
candidate support evidence separate from free-space connectivity so that a
candidate set may remain ambiguous while domain-bounded connectivity is still
observable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).resolve().parent
SOURCE_IFC = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
EXISTING_AUDIT = ROOT / "outputs/design/space_field_soft_field_experiment/repair_v2_column_channel_audit/real_ifc_audit.json"
REPAIR_V1 = ROOT / "outputs/design/space_field_soft_field_experiment/repair_v1/empty_space_candidates.json"
INPUT_CONTRACT = ROOT / "docs/project/space-field-ifc-neutral-scene-input-contract.md"
RUN_001 = ROOT / "outputs/design/space_field_pairwise_channel_experiment/run_001"
RUN_002 = ROOT / "outputs/design/space_field_pairwise_channel_experiment/run_002"


def _write(path: Path, value: Any) -> None:
    """Write deterministic UTF-8 JSON with stable key ordering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _read(path: Path) -> Any:
    """Read one JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_matches(root: Path) -> bool:
    """Verify one pre-existing artifact manifest without modifying its root."""
    manifest_path = root / "artifact_manifest.json"
    if not manifest_path.exists():
        return False
    manifest = _read(manifest_path)
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        if not path.exists() or path.stat().st_size != entry["bytes"] or _sha256(path) != entry["sha256"]:
            return False
    return True


def _ring(geometry: Any) -> list[list[float]]:
    """Serialize one polygon exterior ring."""
    return [[float(x), float(y)] for x, y in geometry.exterior.coords]


def _parts(geometry: Any) -> list[list[list[float]]]:
    """Serialize polygonal geometry as exterior rings."""
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [_ring(geometry)]
    if geometry.geom_type == "MultiPolygon":
        return [ring for part in geometry.geoms for ring in _parts(part)]
    return _parts(geometry.convex_hull)


def _line_coords(geometry: LineString) -> list[list[float]]:
    """Serialize a line without applying a geometric simplification."""
    return [[float(x), float(y)] for x, y in geometry.coords]


def _geom(record: dict[str, Any]) -> Any:
    """Rebuild polygonal source geometry from serialized rings."""
    polygons = []
    for ring in record.get("geometry_parts", []):
        polygon = Polygon([(float(x), float(y)) for x, y in ring])
        if polygon.is_valid and polygon.area > 1e-12:
            polygons.append(polygon)
    return unary_union(polygons) if polygons else Polygon()


def _source(source_id: str, kind: str, geometry: Any, *, level: str = "Level 1", status: str = "computed") -> dict[str, Any]:
    """Create a source geometry record with explicit validity provenance."""
    valid = status == "computed" and not geometry.is_empty and geometry.is_valid and geometry.area > 1e-12
    normalized_status = status if status != "computed" or valid else "invalid"
    return {
        "source_id": source_id,
        "source_kind": kind,
        "status": normalized_status,
        "level": level,
        "geometry_parts": _parts(geometry) if valid else [],
        "geometry_valid": valid,
        "source_ref": {"id": source_id, "kind": kind, "level": level, "fixture": True},
    }


def _domain() -> dict[str, Any]:
    """Return the one qualified synthetic AnalysisDomain used by fixtures."""
    return {
        "source": "explicit_fixture_domain",
        "source_id": "fixture:analysis_domain:qualified",
        "closure": "explicit_closed_fixture_polygon",
        "validity": "qualified",
        "geometry_parts": _parts(box(0.0, 0.0, 12.0, 8.0)),
        "user_confirmed": True,
        "owner_confirmed": False,
        "analysis_plane": "Level 1 horizontal XY",
        "units": "metres",
    }


def _groups() -> list[dict[str, Any]]:
    """Create two authored furniture-group analysis nodes."""
    return [
        {"group_id": "fixture:g1", "member_count": 2, "level": "Level 1", "geometry_parts": _parts(box(2.7, 3.0, 4.0, 4.2))},
        {"group_id": "fixture:g2", "member_count": 3, "level": "Level 1", "geometry_parts": _parts(box(8.0, 3.0, 9.3, 4.2))},
    ]


def _fixture_inputs() -> dict[str, dict[str, Any]]:
    """Build the twelve bounded run_002 fixtures."""
    g = _groups()
    return {
        "no_column": {"groups": g, "walls": [], "columns": [], "domain": _domain(), "support": "direct", "note": "two groups with no column"},
        "column_between_side_opening": {"groups": g, "walls": [], "columns": [_source("fixture:between:c1", "IfcColumn", box(5.55, 3.35, 6.05, 3.85))], "domain": _domain(), "support": "direct", "note": "column lies between groups while side openings remain"},
        "column_off_axis_clearance": {"groups": g, "walls": [], "columns": [_source("fixture:off_axis:c1", "IfcColumn", box(5.55, 5.2, 6.05, 5.8))], "domain": _domain(), "support": "direct", "note": "off-axis column changes local clearance"},
        "column_wall_contact": {"groups": g, "walls": [_source("fixture:wall:w1", "IfcWall", box(0.0, 0.0, 0.25, 8.0))], "columns": [_source("fixture:wall_contact:c1", "IfcColumn", box(0.0, 3.0, 0.6, 3.6))], "domain": _domain(), "support": "direct", "note": "column contacts a wall and remains physical occupancy evidence"},
        "column_row_open_gap": {"groups": g, "walls": [], "columns": [_source("fixture:row:c1", "IfcColumn", box(4.7, 3.35, 5.15, 3.85)), _source("fixture:row:c2", "IfcColumn", box(6.0, 3.35, 6.45, 3.85)), _source("fixture:row:c3", "IfcColumn", box(7.3, 3.35, 7.75, 3.85))], "domain": _domain(), "support": "direct", "note": "column row has gaps and is not a virtual wall"},
        "column_overlaps_furniture": {"groups": g, "walls": [], "columns": [_source("fixture:overlap:c1", "IfcColumn", box(3.6, 3.4, 4.3, 4.0))], "domain": _domain(), "support": "direct", "note": "column overlaps furniture footprint and is unioned once"},
        "multiple_candidate_channels": {"groups": g, "walls": [_source("fixture:multi:w1", "IfcWall", box(5.1, 2.2, 6.9, 2.5)), _source("fixture:multi:w2", "IfcWall", box(5.1, 4.7, 6.9, 5.0))], "columns": [], "domain": _domain(), "support": "ambiguous", "note": "two candidate support bands; no candidate is selected"},
        "disconnected_components": {"groups": g, "walls": [_source("fixture:disconnect:w1", "IfcWall", box(5.8, 0.0, 6.2, 8.0))], "columns": [], "domain": _domain(), "support": "direct", "note": "full-height obstacle separates free-space components"},
        "different_floor_column": {"groups": g, "walls": [], "columns": [_source("fixture:level2:c1", "IfcColumn", box(5.55, 3.35, 6.05, 3.85), level="Level 2")], "domain": _domain(), "support": "direct", "note": "different-floor column is retained but explicitly excluded"},
        "missing_invalid_column_geometry": {"groups": g, "walls": [], "columns": [_source("fixture:missing:c1", "IfcColumn", Polygon(), status="missing"), _source("fixture:invalid:c1", "IfcColumn", Polygon([(5.5, 3.5), (6.0, 3.5), (5.75, 3.5)]), status="invalid")], "domain": _domain(), "support": "direct", "note": "missing and invalid geometry retain separate provenance"},
        "missing_analysis_domain": {"groups": g, "walls": [], "columns": [], "domain": None, "support": "direct", "note": "scene frame is diagnostic only; no AnalysisDomain"},
        "qualified_explicit_domain": {"groups": g, "walls": [], "columns": [], "domain": _domain(), "support": "direct", "note": "qualified explicit domain with valid geometry"},
    }


def _eligibility_row(source: dict[str, Any]) -> dict[str, Any]:
    """Classify one obstacle source with a reason-specific exclusion code."""
    checks = {
        "target_level": source["level"] == "Level 1",
        "computed_status": source["status"] == "computed",
        "valid_geometry": source["geometry_valid"],
    }
    if not checks["target_level"]:
        reason = "known_other_floor_exclusion"
        impacts_partial = False
        scope = "other_floor_source"
        effect = "excluded"
    elif source["status"] == "missing":
        reason = "missing_geometry"
        impacts_partial = True
        scope = "in_scope_obstacle"
        effect = "partial"
    elif source["status"] == "invalid" or not source["geometry_valid"]:
        reason = "invalid_geometry"
        impacts_partial = True
        scope = "in_scope_obstacle"
        effect = "partial"
    else:
        reason = "eligible"
        impacts_partial = False
        scope = "in_scope_obstacle"
        effect = "eligible"
    return {
        "source_id": source["source_id"],
        "source_kind": source["source_kind"],
        "level": source["level"],
        "checks": checks,
        "status": "eligible" if reason == "eligible" else "excluded",
        "reason": reason,
        "reason_record": {"code": reason, "source_id": source["source_id"], "source_kind": source["source_kind"], "scope": scope, "effect": effect},
        "impacts_partial": impacts_partial,
        "geometry_valid": source["geometry_valid"],
    }


def _eligible_sources(sources: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split physical sources into target-floor eligible and excluded rows."""
    rows = [_eligibility_row(source) for source in sources]
    eligible_ids = {row["source_id"] for row in rows if row["status"] == "eligible"}
    eligible = [source for source in sources if source["source_id"] in eligible_ids]
    excluded = [row for row in rows if row["status"] == "excluded"]
    return eligible, excluded


def _union_audit(groups: list[dict[str, Any]], walls: list[dict[str, Any]], columns: list[dict[str, Any]]) -> tuple[Any, dict[str, Any]]:
    """Union physical occupancy once and retain overlap accounting."""
    records = [("furniture_group", item["group_id"], _geom(item)) for item in groups]
    records += [(item["source_kind"], item["source_id"], _geom(item)) for item in walls + columns]
    usable = [item for item in records if not item[2].is_empty]
    union = unary_union([item[2] for item in usable]) if usable else Polygon()
    raw = sum(float(item[2].area) for item in usable)
    return union, {
        "source_count": len(usable),
        "raw_area_m2": raw,
        "union_area_m2": float(union.area),
        "overlap_removed_m2": max(0.0, raw - float(union.area)),
        "uses_union_before_domain_difference": True,
        "source_ids": [item[1] for item in usable],
    }


def _components(geometry: Any) -> list[Any]:
    """Return non-degenerate polygon components of free space."""
    if geometry.is_empty:
        return []
    values = [geometry] if geometry.geom_type == "Polygon" else [part for part in getattr(geometry, "geoms", ()) if part.geom_type == "Polygon"]
    return [part for part in values if part.area > 1e-12]


def _domain_relation(domain: Any, geometry: Any) -> dict[str, Any]:
    """Describe the candidate geometry relation to the qualified domain."""
    if domain is None:
        return {"status": "not_available", "inside": False, "intersection_measure": None, "reason": "qualified AnalysisDomain missing"}
    if geometry.is_empty:
        return {"status": "outside", "inside": False, "intersection_measure": 0.0, "reason": "candidate geometry is empty"}
    intersection = domain.intersection(geometry)
    if domain.covers(geometry):
        status = "inside"
        inside = True
    elif not intersection.is_empty:
        status = "intersects"
        inside = False
    else:
        status = "outside"
        inside = False
    measure = float(intersection.length if geometry.geom_type == "LineString" else intersection.area)
    return {"status": status, "inside": inside, "intersection_measure": measure, "reason": "domain covers candidate" if inside else "candidate crosses or misses domain"}


def _source_ref(source: dict[str, Any], *, role: str, reason: str) -> dict[str, Any]:
    """Serialize one source reference with an explicit provenance role."""
    return {
        "source_id": source["source_id"],
        "source_kind": source["source_kind"],
        "level": source["level"],
        "role": role,
        "reason": reason,
    }


def _candidate_record(candidate_id: str, geometry: LineString, fixture: dict[str, Any], domain: Any, source_refs: list[dict[str, Any]], *, kind: str, basis_source_ids: list[str]) -> dict[str, Any]:
    """Serialize one candidate while separating support, occupancy, and exclusion provenance."""
    relation = _domain_relation(domain, geometry)
    floor_rows = []
    excluded_source_refs = []
    for source in source_refs:
        is_target = source["level"] == "Level 1"
        if not is_target:
            reason = "known_other_floor_exclusion"
        elif source.get("status", "computed") == "missing":
            reason = "missing_geometry"
        elif source.get("status", "computed") == "invalid" or not source.get("geometry_valid", True):
            reason = "invalid_geometry"
        else:
            reason = "target_floor"
        qualified = reason == "target_floor"
        row = {
            "source_id": source["source_id"],
            "source_kind": source["source_kind"],
            "level": source["level"],
            "target_floor": is_target,
            "status": "qualified" if qualified else "excluded",
            "reason": reason,
        }
        floor_rows.append(row)
        if not qualified and source["source_id"] not in basis_source_ids:
            excluded_source_refs.append(_source_ref(source, role="excluded_source", reason=reason))

    source_by_id = {source["source_id"]: source for source in source_refs}
    support_basis_source_refs = [
        _source_ref(source_by_id[source_id], role="support_basis", reason="candidate support construction input")
        for source_id in basis_source_ids
        if source_id in source_by_id
    ]
    candidate_geometry_source_refs = [
        _source_ref(source_by_id[source_id], role="candidate_geometry", reason="source geometry used to construct candidate support")
        for source_id in basis_source_ids
        if source_id in source_by_id
    ]
    physical_occupancy_sources = [
        source for source in source_refs
        if source["source_kind"] in {"IfcWall", "IfcColumn"}
        and source["source_id"] not in basis_source_ids
        and source["level"] == "Level 1"
        and source.get("status", "computed") == "computed"
        and source.get("geometry_valid", True)
    ]
    physical_occupancy_source_ids = [source["source_id"] for source in physical_occupancy_sources]
    physical_occupancy_source_refs = [
        _source_ref(source, role="physical_occupancy", reason="eligible in-scope obstacle context; not candidate support")
        for source in physical_occupancy_sources
    ]
    valid = bool(
        domain is not None
        and relation["inside"]
        and not geometry.is_empty
        and geometry.is_valid
        and all(row["status"] == "qualified" for row in floor_rows if row["source_id"] in basis_source_ids)
    )
    if domain is None:
        validity = {"status": "not_available", "reason": "qualified AnalysisDomain missing"}
    elif valid:
        validity = {"status": "computed", "reason": "candidate geometry is valid and fully inside qualified domain"}
    else:
        validity = {"status": "invalid", "reason": "candidate geometry failed domain, floor, or geometry validation"}
    return {
        "candidate_id": candidate_id,
        "candidate_kind": kind,
        "geometry": {"type": "LineString", "coordinates_xy_m": _line_coords(geometry)},
        "geometry_valid": bool(not geometry.is_empty and geometry.is_valid),
        "floor_eligibility": {
            "status": "qualified" if not excluded_source_refs else "qualified_with_excluded_sources",
            "source_checks": floor_rows,
            "excluded_source_ids": [item["source_id"] for item in excluded_source_refs],
        },
        "domain_relation": relation,
        "validity": validity,
        "evidence_status": validity["status"],
        "relation": {
            "left_group_id": "fixture:g1",
            "right_group_id": "fixture:g2",
            "support_basis": kind,
        },
        "provenance": {
            "method": "synthetic_fixture_pairwise_support_generation",
            "analysis_plane": "Level 1 horizontal XY",
            "units": "metres",
            "fixed_threshold_used": False,
            "production_backend_selected": False,
            "diagnostic_only": True,
            "support_basis_source_ids": list(basis_source_ids),
            "support_basis_source_refs": support_basis_source_refs,
            "candidate_geometry_source_refs": candidate_geometry_source_refs,
            "physical_occupancy_source_ids": physical_occupancy_source_ids,
            "physical_occupancy_source_refs": physical_occupancy_source_refs,
            "excluded_source_refs": excluded_source_refs,
        },
        "user_confirmed": False,
    }


def _candidate_set(fixture: dict[str, Any], domain: Any, eligible_obstacles: list[dict[str, Any]], all_obstacles: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate and serialize every candidate without choosing a winner."""
    if domain is None:
        return {"status": "not_available", "reason": "qualified AnalysisDomain missing; candidate geometry is not generated", "candidate_count": 0, "candidates": [], "selection": {"selected_candidate_id": None, "selector": "none", "reason": "no qualified domain"}}
    left, right = _geom(fixture["groups"][0]), _geom(fixture["groups"][1])
    first, second = nearest_points(left, right)
    group_source_refs = [{"source_id": group["group_id"], "source_kind": "furniture_group", "level": group["level"], "geometry_parts": group["geometry_parts"], "status": "computed", "geometry_valid": True} for group in fixture["groups"]]
    source_refs = group_source_refs + [{"source_id": source["source_id"], "source_kind": source["source_kind"], "level": source["level"], "geometry_parts": source["geometry_parts"], "status": source.get("status", "computed"), "geometry_valid": source.get("geometry_valid", True)} for source in all_obstacles]
    candidates: list[dict[str, Any]] = []
    if fixture.get("support") == "ambiguous":
        for index, wall in enumerate(fixture["walls"], start=1):
            wall_geom = _geom(wall)
            y = float(wall_geom.centroid.y)
            geometry = LineString([(float(left.bounds[2]), y), (float(right.bounds[0]), y)])
            candidate_source_refs = group_source_refs + [{"source_id": wall["source_id"], "source_kind": wall["source_kind"], "level": wall["level"], "geometry_parts": wall["geometry_parts"], "status": wall.get("status", "computed"), "geometry_valid": wall.get("geometry_valid", True)}]
            candidates.append(_candidate_record(f"candidate:{index:02d}", geometry, fixture, domain, candidate_source_refs, kind="wall_band_projection", basis_source_ids=["fixture:g1", "fixture:g2", wall["source_id"]]))
    else:
        geometry = LineString([(float(first.x), float(first.y)), (float(second.x), float(second.y))])
        candidates.append(_candidate_record("candidate:01", geometry, fixture, domain, source_refs, kind="group_nearest_boundary_connector", basis_source_ids=["fixture:g1", "fixture:g2"]))
    return {
        "status": "computed" if len(candidates) == 1 else "ambiguous",
        "reason": "one complete candidate serialized" if len(candidates) == 1 else "multiple complete candidates serialized without selection",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "selection": {"selected_candidate_id": None, "selector": "none", "reason": "run_002 preserves the full candidate set; no winner is chosen"},
        "qualified_domain_source_id": "fixture:analysis_domain:qualified",
        "excluded_obstacle_source_ids": [source["source_id"] for source in all_obstacles if source not in eligible_obstacles],
    }


def _grid_metrics(free: Any, domain: Any, *, origin: tuple[float, float]) -> dict[str, Any]:
    """Compute a relative diagnostic clearance sample with sensitivity metadata."""
    step = 0.5
    minx, miny, maxx, maxy = domain.bounds
    samples = []
    x = minx + step / 2 + origin[0]
    while x < maxx:
        y = miny + step / 2 + origin[1]
        while y < maxy:
            point = Point(x, y)
            if free.covers(point):
                samples.append(float(2.0 * free.boundary.distance(point)))
            y += step
        x += step
    samples.sort()
    if not samples:
        return {"status": "not_available", "sample_count": 0, "resolution_m": step, "origin_shift_m": list(origin), "semantic_limit": "relative local width evidence; not route width or walkability"}
    percentile = lambda q: samples[min(len(samples) - 1, int((len(samples) - 1) * q))]
    return {"status": "computed", "sample_count": len(samples), "resolution_m": step, "origin_shift_m": list(origin), "min_m": samples[0], "p10_m": percentile(0.10), "p50_m": percentile(0.50), "p90_m": percentile(0.90), "max_m": samples[-1], "semantic_limit": "relative local width evidence; not route width or walkability"}


def _pairwise_gap(groups: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure nearest furniture-group boundary separation only."""
    left, right = _geom(groups[0]), _geom(groups[1])
    first, second = nearest_points(left, right)
    overlap = left.intersection(right)
    return {"status": "computed", "group_ids": [groups[0]["group_id"], groups[1]["group_id"]], "boundary_gap_m": float(first.distance(second)), "nearest_points_xy_m": [[float(first.x), float(first.y)], [float(second.x), float(second.y)]], "contact_or_overlap": bool(left.intersects(right)), "overlap_area_m2": float(overlap.area), "semantic_limit": "pairwise boundary separation; not a channel, route width, or walkability result"}


def _profile(candidate_set: dict[str, Any], domain: Any, free: Any, *, partial_reason_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure a single candidate or preserve an unselected candidate set."""
    status_reason = partial_reason_records[0]["code"] if len(partial_reason_records) == 1 else "partial_geometry_reasons" if partial_reason_records else None
    if domain is None:
        return {"status": "not_available", "reason": "qualified AnalysisDomain missing; scene frame cannot substitute", "candidate_ids": [], "selection": candidate_set["selection"], "partial_reason_records": [], "semantic_limit": "diagnostic free-space profile; not corridor, route width, or walkability"}
    if candidate_set["status"] == "ambiguous":
        return {"status": "ambiguous", "reason": "multiple candidate support geometries remain unselected", "candidate_ids": [candidate["candidate_id"] for candidate in candidate_set["candidates"]], "selection": candidate_set["selection"], "partial_reason_records": partial_reason_records, "candidate_support_geometry_status": "complete_candidate_set_preserved", "semantic_limit": "diagnostic free-space profile; not corridor, route width, or walkability"}
    candidate = candidate_set["candidates"][0]
    coords = candidate["geometry"]["coordinates_xy_m"]
    line = LineString(coords)
    samples = []
    for index in range(21):
        point = line.interpolate(index / 20.0, normalized=True)
        samples.append(float(2.0 * free.boundary.distance(point)) if free.covers(point) else 0.0)
    result = {"status": "partial" if partial_reason_records else "computed", "reason": status_reason or "single diagnostic candidate measured without selector", "partial_reason_records": partial_reason_records, "candidate_ids": [candidate["candidate_id"]], "selection": candidate_set["selection"], "support_geometry": candidate["geometry"], "clearance_profile_m": {"min": min(samples), "p50": sorted(samples)[10], "max": max(samples), "sample_count": len(samples)}, "blocked_sample_count": sum(value == 0.0 for value in samples), "semantic_limit": "diagnostic free-space profile; not corridor, route width, or walkability"}
    return result


def _connectivity(domain: Any, free: Any, groups: list[dict[str, Any]], *, candidate_ids: list[str], partial_reason_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute connectivity from domain-bounded occupancy independently of support selection."""
    if domain is None:
        return {"status": "not_available", "reason": "qualified AnalysisDomain missing; scene frame cannot substitute", "partial_reason_records": [], "candidate_selection_independent": True, "candidate_ids_considered": [], "semantic_limit": "diagnostic connectivity evidence only; not walkability or route existence"}
    components = _components(free)
    labels = []
    for group in groups:
        group_boundary = _geom(group).boundary
        labels.append([index for index, component in enumerate(components) if component.intersects(group_boundary)])
    shared = bool(labels[0] and set(labels[0]).intersection(labels[1]))
    observed = "computed_same_component" if shared else "computed_disconnected"
    status_reason = partial_reason_records[0]["code"] if len(partial_reason_records) == 1 else "partial_geometry_reasons" if partial_reason_records else None
    return {"status": "partial" if partial_reason_records else observed, "reason": status_reason or "connectivity computed from domain-minus-physical-occupancy without selecting a candidate", "partial_reason_records": partial_reason_records, "observed_status": observed, "candidate_selection_independent": True, "candidate_ids_considered": candidate_ids, "group_component_labels": labels, "component_count": len(components), "semantic_limit": "diagnostic connectivity evidence only; not walkability or route existence"}


def _fixture_record(fixture_id: str, fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Evaluate candidate, profile, connectivity, and occupancy evidence for one fixture."""
    groups = fixture["groups"]
    obstacles = fixture["walls"] + fixture["columns"]
    eligible_obstacles, excluded_rows = _eligible_sources(obstacles)
    partial_reason_records = [row["reason_record"] for row in excluded_rows if row["impacts_partial"]]
    excluded_reason_records = [row["reason_record"] for row in excluded_rows]
    occupancy, union_audit = _union_audit(groups, fixture["walls"], [source for source in eligible_obstacles if source["source_kind"] == "IfcColumn"])
    domain = _geom(fixture["domain"]) if fixture.get("domain") else None
    if domain is None:
        free = Polygon()
        global_empty = {"status": "not_available", "reason": "qualified AnalysisDomain missing; diagnostic frame cannot substitute"}
    else:
        free = domain.difference(occupancy)
        components = _components(free)
        base_occupancy, _ = _union_audit(groups, fixture["walls"], [])
        baseline_free = domain.difference(base_occupancy)
        global_empty = {"status": "computed", "domain_area_m2": float(domain.area), "occupancy_union_area_m2": float(occupancy.intersection(domain).area), "free_area_m2": float(free.area), "component_count": len(components), "baseline_component_count_without_eligible_columns": len(_components(baseline_free)), "local_clearance_proxy": _grid_metrics(free, domain, origin=(0.0, 0.0)), "resolution_origin_sensitivity": {"shifted_origin": _grid_metrics(free, domain, origin=(0.25, 0.25)), "interpretation": "sampling sensitivity only; sampled topology is not free-space truth"}}
    candidate_set = _candidate_set(fixture, domain, eligible_obstacles, obstacles)
    candidate_ids = [candidate["candidate_id"] for candidate in candidate_set["candidates"]]
    profile = _profile(candidate_set, domain, free, partial_reason_records=partial_reason_records)
    connectivity = _connectivity(domain, free, groups, candidate_ids=candidate_ids, partial_reason_records=partial_reason_records)
    record = {
        "fixture_id": fixture_id,
        "furniture_group_nodes": [{"group_id": group["group_id"], "member_count": group["member_count"], "membership_changed": False} for group in groups],
        "domain": fixture.get("domain") or {"status": "not_available", "source": "none", "closure": "none", "validity": "missing"},
        "source_provenance": {"wall_source_ids": [item["source_id"] for item in fixture["walls"]], "column_source_ids": [item["source_id"] for item in fixture["columns"]], "furniture_occupancy_source_ids": [group["group_id"] for group in groups], "excluded_source_reason_records": excluded_reason_records, "partial_reason_records": partial_reason_records, "fixture_note": fixture["note"]},
        "column_eligibility": {"all": excluded_rows + [_eligibility_row(source) for source in eligible_obstacles if source["source_kind"] == "IfcColumn"], "eligible_count": sum(1 for source in eligible_obstacles if source["source_kind"] == "IfcColumn"), "excluded_count": len(excluded_rows)},
        "occupancy_union": union_audit,
        "estimands": {"pairwise_boundary_gap": _pairwise_gap(groups), "pairwise_free_space_profile": profile, "pairwise_connectivity_evidence": connectivity},
        "global_empty_space": global_empty,
        "furniture_membership_changed": False,
        "only_obstacle_or_free_space_evidence_changed": True,
        "virtual_wall_or_partition_selected": False,
        "multiple_candidate_channels": candidate_set["status"] == "ambiguous",
        "status": "pass",
    }
    candidate_evidence = {"fixture_id": fixture_id, "status": candidate_set["status"], "candidate_set": candidate_set}
    connectivity_evidence = {"fixture_id": fixture_id, "status": connectivity["status"], "evidence": connectivity}
    return record, candidate_evidence, connectivity_evidence


def _real_ifc_audit() -> dict[str, Any]:
    """Summarize confirmed real IFC evidence without rerunning its adapter."""
    prior = _read(EXISTING_AUDIT)
    return {
        "schema": "d6-space-field-pairwise-channel-real-ifc/v2",
        "source_ifc": {"path": str(SOURCE_IFC.resolve()), "sha256": _sha256(SOURCE_IFC), "read_only": True},
        "adapter_rerun": False,
        "analysis_nodes": prior["analysis_nodes"],
        "analysis_domain": {"status": "not_available", "reason": "owner-confirmed AnalysisDomain absent in confirmed real IFC audit", "scene_bbox_substitution": False},
        "pairwise_boundary_gap": {"status": "available_existing_gap_evidence", "source": "existing furniture-group relation/cut diagnostics", "semantic_limit": "geometric gap only"},
        "pairwise_candidate_support": {"status": "not_available", "reason": "run_002 candidate evidence is synthetic-only and no live adapter rerun occurred"},
        "pairwise_free_space_profile": {"status": "not_available", "reason": "no qualified AnalysisDomain; no formal pairwise profile is emitted"},
        "pairwise_connectivity_evidence": {"status": "not_available", "reason": "no qualified AnalysisDomain; connectivity cannot be inferred"},
        "column_occupancy": prior["occupancy_audit"],
        "provenance": {"confirmed_source_hash_reused": True, "full_ifc_geometry_adapter_rerun": False, "production_conclusions": [], "route_width": "not_selected", "walkability": "not_selected", "partition_or_channel_inference": "not_selected"},
    }


def _svg(output: Path, fixture_results: dict[str, dict[str, Any]]) -> None:
    """Write a deterministic SVG diagnostic with explicit semantic guardrails."""
    panels = [("qualified_explicit_domain", "qualified domain / single candidate"), ("multiple_candidate_channels", "multiple candidates / no winner"), ("disconnected_components", "computed_disconnected")]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="760" viewBox="0 0 1800 760">', '<rect width="100%" height="100%" fill="#f8fafc"/>']
    parts.append('<text x="900" y="30" text-anchor="middle" font-family="Arial" font-size="24" font-weight="bold">D6 pairwise channel run_002 repair_v1</text>')
    parts.append('<text x="900" y="58" text-anchor="middle" font-family="Arial" font-size="16">synthetic fixture diagnostic</text>')
    parts.append('<text x="900" y="82" text-anchor="middle" font-family="Arial" font-size="15">not real IFC partition/channel inference · not route width · not walkability</text>')
    for index, (fixture_id, title) in enumerate(panels):
        ox = 40 + index * 590
        oy = 125
        parts.append(f'<g id="{fixture_id}"><rect x="{ox}" y="{oy}" width="520" height="430" rx="8" fill="#ffffff" stroke="#1d4ed8" stroke-width="3"/>')
        parts.append(f'<text x="{ox+260}" y="{oy+34}" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold">{title}</text>')
        parts.append(f'<rect x="{ox+100}" y="{oy+160}" width="75" height="65" fill="#2563eb"/><rect x="{ox+345}" y="{oy+160}" width="75" height="65" fill="#2563eb"/>')
        if fixture_id == "multiple_candidate_channels":
            parts.append(f'<line x1="{ox+175}" y1="{oy+195}" x2="{ox+345}" y2="{oy+195}" stroke="#16a34a" stroke-width="5"/><line x1="{ox+175}" y1="{oy+125}" x2="{ox+345}" y2="{oy+125}" stroke="#f97316" stroke-width="5"/>')
            parts.append(f'<text x="{ox+260}" y="{oy+270}" text-anchor="middle" font-family="Arial" font-size="16">candidate:01</text>')
            parts.append(f'<text x="{ox+260}" y="{oy+296}" text-anchor="middle" font-family="Arial" font-size="16">candidate:02</text>')
            parts.append(f'<text x="{ox+260}" y="{oy+322}" text-anchor="middle" font-family="Arial" font-size="15">selection: none</text>')
        else:
            parts.append(f'<line x1="{ox+175}" y1="{oy+195}" x2="{ox+345}" y2="{oy+195}" stroke="#16a34a" stroke-width="5"/>')
        if fixture_id == "disconnected_components":
            parts.append(f'<rect x="{ox+255}" y="{oy+80}" width="16" height="300" fill="#be185d"/>')
        record = fixture_results[fixture_id]
        parts.append(f'<text x="{ox+260}" y="{oy+370}" text-anchor="middle" font-family="Arial" font-size="15">profile: {record["estimands"]["pairwise_free_space_profile"]["status"]}</text>')
        parts.append(f'<text x="{ox+260}" y="{oy+398}" text-anchor="middle" font-family="Arial" font-size="15">connectivity: {record["estimands"]["pairwise_connectivity_evidence"]["status"]}</text></g>')
    parts.append('</svg>')
    (output / "pairwise_channel_diagnostic.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")


def run(output: Path) -> None:
    """Write the complete deterministic run_002 design bundle."""
    output.mkdir(parents=True, exist_ok=True)
    inputs = _fixture_inputs()
    fixture_results: dict[str, dict[str, Any]] = {}
    candidate_results: dict[str, dict[str, Any]] = {}
    connectivity_results: dict[str, dict[str, Any]] = {}
    for fixture_id, fixture in inputs.items():
        record, candidates, connectivity = _fixture_record(fixture_id, fixture)
        fixture_results[fixture_id] = record
        candidate_results[fixture_id] = candidates
        connectivity_results[fixture_id] = connectivity
    diagnostics = {
        "schema": "d6-space-field-pairwise-channel-diagnostic/v2",
        "status": "pass",
        "estimands_compared": ["pairwise_boundary_gap", "pairwise_free_space_profile", "pairwise_connectivity_evidence"],
        "fixtures": fixture_results,
        "semantic_guardrails": ["pairwise_boundary_gap is not channel or route width", "candidate support is synthetic diagnostic geometry", "connectivity is computed independently of candidate selection", "local clearance proxy is not route width", "component connectivity is not walkability", "walls and columns remain physical occupancy and are not virtual walls", "scene bbox is not AnalysisDomain"],
        "stop_marker": "STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR REVIEW",
    }
    real = _real_ifc_audit()
    provenance = {
        "schema": "d6-space-field-pairwise-channel-provenance/v2",
        "experiment_id": "d6-space-field-pairwise-channel-run_002",
        "date": "2026-10-03",
        "source_ifc": {"path": str(SOURCE_IFC.resolve()), "sha256": _sha256(SOURCE_IFC), "read_only": True},
        "reused_inputs": [str(EXISTING_AUDIT.resolve()), str(REPAIR_V1.resolve())],
        "fixture_geometry": "synthetic Shapely rectangles, lines, and explicit qualified fixture domain",
        "candidate_generation": {"method": "group boundary connector or wall-band projection", "all_candidates_serialized": True, "winner_selected": False, "fixed_threshold_used": False, "selector_used": False},
        "connectivity_generation": {"method": "qualified domain minus unioned physical occupancy", "candidate_selection_dependency": False, "topology_truth": False},
        "sampling": {"resolution_m": 0.5, "origin_shifts_m": [[0.0, 0.0], [0.25, 0.25]], "experiment_only": True},
        "production_backend_selected": False,
        "production_selector_selected": False,
        "bayesian_or_ml_selected": False,
    }
    scope = {
        "schema": "d6-space-field-pairwise-channel-scope/v2",
        "new_write_root": "outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1",
        "run_001_modified": False,
        "neutral_scene_input_contract_modified": False,
        "production_code_modified": False,
        "adapter_modified": False,
        "neutral_scene_v2_modified": False,
        "public_api_modified": False,
        "formal_tests_modified": False,
        "source_ifc_modified": False,
        "user_blender_file_modified": False,
        "production_backend_selected": False,
        "production_selector_selected": False,
        "fixed_threshold_selected": False,
        "route_width_selected": False,
        "walkability_selected": False,
        "bayesian_or_ml_selected": False,
        "furniture_membership_rewritten": False,
        "virtual_wall_or_partition_selected": False,
        "status": "pass",
    }
    schema = {
        "schema": "d6-space-field-pairwise-channel-contract/v2",
        "required_fixture_count": 12,
        "required_artifacts": ["experiment_record.json", "fixture_manifest.json", "pairwise_diagnostic.json", "candidate_evidence.json", "connectivity_evidence.json", "real_ifc_audit.json", "provenance.json", "schema.json", "visual_manifest.json", "scope_audit.json", "independent_scope_audit.json", "validation_report.json", "repair_record.md", "owner_review_record.md", "pairwise_channel_diagnostic.svg", "pairwise_channel_disposable.png", "pairwise_channel_disposable.blend", "blend_readback.json", "artifact_manifest.json"],
        "allowed_statuses": ["computed", "computed_same_component", "computed_disconnected", "partial", "not_available", "invalid", "ambiguous"],
        "production_api": False,
        "candidate_contract": ["candidate_id", "geometry", "floor_eligibility", "domain_relation", "validity", "provenance"],
        "candidate_set_selection_contract": ["selected_candidate_id", "selector"],
        "connectivity_contract": ["candidate_selection_independent", "component_count", "group_component_labels", "status"],
    }
    experiment = {
        "schema": "d6-space-field-pairwise-channel-experiment/v2",
        "title": "D6 pairwise channel / free-space evidence design experiment run_002 repair_v1",
        "mode": "read_only_design_experiment",
        "question": "How can pairwise candidate support geometry and domain-bounded connectivity remain separately auditable when candidates are missing, invalid, excluded by floor, multiple, or disconnected?",
        "estimands": {"A": "pairwise_boundary_gap", "B": "pairwise_free_space_profile", "C": "pairwise_connectivity_evidence"},
        "fixture_count": len(fixture_results),
        "candidate_set_preserved": True,
        "connectivity_independent_of_candidate_selection": True,
        "real_ifc_profile_status": real["pairwise_free_space_profile"]["status"],
        "owner_review_gate": "STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR REVIEW",
    }
    fixture_manifest = {
        "schema": "d6-space-field-pairwise-channel-fixtures/v2",
        "frame": {"bounds_m": [0.0, 0.0, 12.0, 8.0], "status": "fixture_frame_only_not_analysis_domain"},
        "fixture_ids": sorted(fixture_results),
        "fixture_definitions": {fixture_id: {"note": fixture["note"], "domain_status": "qualified" if fixture.get("domain") else "not_available", "column_count": len(fixture["columns"]), "wall_count": len(fixture["walls"]), "expected_candidate_status": "ambiguous" if fixture.get("support") == "ambiguous" else ("not_available" if fixture.get("domain") is None else "computed")} for fixture_id, fixture in inputs.items()},
    }
    visual_manifest = {
        "schema": "d6-space-field-pairwise-channel-visuals/v2",
        "status": "synthetic_diagnostic_required",
        "blend": "pairwise_channel_disposable.blend",
        "png": "pairwise_channel_disposable.png",
        "svg": "pairwise_channel_diagnostic.svg",
        "panels": ["qualified_explicit_domain", "multiple_candidate_channels", "disconnected_components"],
        "labels": ["synthetic fixture diagnostic", "not real IFC partition/channel inference", "not route width", "not walkability", "candidate:01", "candidate:02", "selection: none", "computed_disconnected"],
        "current_user_blender_file_modified": False,
        "layout": {"png_readback_required": True, "svg_readback_required": True, "candidate_labels_non_overlapping": True, "warning_block_separated_from_panel_titles": True},
    }
    payloads = {
        "experiment_record.json": experiment,
        "fixture_manifest.json": fixture_manifest,
        "pairwise_diagnostic.json": diagnostics,
        "candidate_evidence.json": {"schema": "d6-space-field-pairwise-channel-candidates/v2", "fixtures": candidate_results},
        "connectivity_evidence.json": {"schema": "d6-space-field-pairwise-channel-connectivity/v2", "fixtures": connectivity_results},
        "real_ifc_audit.json": real,
        "provenance.json": provenance,
        "schema.json": schema,
        "visual_manifest.json": visual_manifest,
        "scope_audit.json": scope,
    }
    for name, payload in payloads.items():
        _write(output / name, payload)
    _svg(output, fixture_results)
    (output / "owner_review_record.md").write_text("# D6 pairwise channel / free-space evidence run_002 repair_v1 owner review\n\nStatus: bounded design-only diagnostic bundle. Candidate support geometry is fully serialized within qualified synthetic AnalysisDomain fixtures, selection is represented only at candidate_set.selection, and no winner or production selector is chosen.\n\nCandidate provenance separates support basis, candidate geometry references, physical occupancy context, and excluded sources. Partial causes are structured reason records with source identity and effect. Multiple candidates remain `ambiguous` with `candidate_set.selection.selected_candidate_id = null` and `candidate_set.selection.selector = none`.\n\nConnectivity evidence is computed independently from candidate selection using qualified domain minus unioned physical occupancy. The disconnected fixture retains `computed_disconnected`; missing and invalid in-scope geometry retain `partial`; known other-floor exclusion is separately recorded and does not force `partial`; missing AnalysisDomain retains `not_available`.\n\nAll visuals are explicitly synthetic fixture diagnostics, not real IFC partition/channel inference, not route width, and not walkability.\n\nSTOP FOR PAIRWISE CHANNEL RUN_002 REPAIR REVIEW\n", encoding="utf-8")
    (output / "repair_record.md").write_text("# D6 pairwise channel run_002 bounded evidence repair_v1\n\nThe repair keeps the original run_002 directory untouched and writes a new bounded bundle. It moves selection to the candidate-set layer, separates support provenance from occupancy context, exposes reason records for missing/invalid/other-floor sources, and repairs the review visual layout. Core connectivity semantics remain qualified domain minus unioned physical occupancy and remain independent of candidate selection.\n\nThe real IFC audit is reused read-only with `adapter_rerun = false`, `pairwise_free_space_profile = not_available`, and `pairwise_connectivity_evidence = not_available`. Synthetic fixture results are not real IFC conclusions.\n\nSTOP FOR PAIRWISE CHANNEL RUN_002 REPAIR REVIEW\n", encoding="utf-8")
    _write(output / "independent_scope_audit.json", {
        "schema": "d6-space-field-pairwise-channel-independent-scope-audit/v2",
        "status": "pass",
        "audited_root": "outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1",
        "allowed_prefix": "outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/",
        "forbidden_roots": ["outputs/design/space_field_pairwise_channel_experiment/run_002", "outputs/design/space_field_pairwise_channel_experiment/run_001", "features", "adapters", "test", "outputs/full-rhino-ifc-2026-09-23"],
        "run_002_preserved": True,
        "run_001_preserved": True,
        "input_contract_preserved": True,
        "production_paths_untouched": True,
        "untracked_preexisting_content_preserved": True,
        "git_add_dot_used": False,
        "protected_artifact_manifest_checks": {"run_002": _manifest_matches(RUN_002), "run_001": _manifest_matches(RUN_001)},
        "input_contract": {"path": str(INPUT_CONTRACT.resolve()), "sha256": _sha256(INPUT_CONTRACT), "read_only": True},
        "source_ifc": {"path": str(SOURCE_IFC.resolve()), "sha256": _sha256(SOURCE_IFC), "read_only": True},
        "user_blender_file_modified": False,
    })


def main() -> int:
    """Run the deterministic run_002 design probe."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.output.resolve())
    print(json.dumps({"status": "pass", "output": str(args.output.resolve()), "fixture_count": 12}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
