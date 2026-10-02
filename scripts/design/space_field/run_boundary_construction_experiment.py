"""Run the bounded D6 AnalysisDomain boundary-construction experiment.

The probe keeps four boundary constructions separate from the physical wall
field. It uses one controlled rectangular fixture, adds topology failure cases,
and inventories the real IFC without invoking the production geometry adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DATE = "2026-10-02"
ROOT = Path(__file__).resolve().parents[3]
LIVE_IFC = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
CURRENT_BLENDER_STATUS = {
    "status": "current_blender_not_observed",
    "reason": "cua_getState_returned_no_blender_app",
    "observation_mode": "read_only_ui_inventory",
}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _json(value: object) -> object:
    """Convert tuples and nested mappings into deterministic JSON values."""
    if isinstance(value, Mapping):
        return {str(key): _json(nested) for key, nested in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    return value


def _write_json(path: Path, value: object) -> None:
    """Write one stable, human-readable JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture() -> dict[str, object]:
    """Return the controlled wall fixture and bounded topology variants."""
    controlled_walls = [
        {"id": "wall-n", "a": [0.0, 0.0], "b": [8.0, 0.0], "thickness": 0.20, "level": "L1"},
        {"id": "wall-e", "a": [8.0, 0.0], "b": [8.0, 6.0], "thickness": 0.20, "level": "L1"},
        {"id": "wall-s", "a": [8.0, 6.0], "b": [0.0, 6.0], "thickness": 0.20, "level": "L1"},
        {"id": "wall-w", "a": [0.0, 6.0], "b": [0.0, 0.0], "thickness": 0.20, "level": "L1"},
    ]
    return {
        "controlled_rectangular_room": {
            "walls": controlled_walls,
            "authored_curve": [[0.30, 0.30], [7.70, 0.30], [7.70, 5.70], [0.30, 5.70], [0.30, 0.30]],
            "openings": [{"id": "opening-door", "host_refs": ["wall-s"], "scenario": "closed_by_assumption"}],
            "objects": [],
        },
        "automatic_closed_wall_shell": {
            "walls": [
                {"id": "wall-a", "a": [0.0, 0.0], "b": [5.0, 0.0], "thickness": 0.18, "level": "L1"},
                {"id": "wall-b", "a": [5.0, 0.0], "b": [5.0, 4.0], "thickness": 0.18, "level": "L1"},
                {"id": "wall-c", "a": [5.0, 4.0], "b": [0.0, 4.0], "thickness": 0.18, "level": "L1"},
                {"id": "wall-d", "a": [0.0, 4.0], "b": [0.0, 0.0], "thickness": 0.18, "level": "L1"},
            ],
            "openings": [{"id": "opening-a", "host_refs": ["wall-b"], "scenario": "closed_by_assumption"}],
        },
        "multi_shell_conflict": {
            "walls": [
                {"id": "shell1-a", "a": [0.0, 0.0], "b": [4.0, 0.0], "thickness": 0.20, "level": "L1"},
                {"id": "shell1-b", "a": [4.0, 0.0], "b": [4.0, 3.0], "thickness": 0.20, "level": "L1"},
                {"id": "shell1-c", "a": [4.0, 3.0], "b": [0.0, 3.0], "thickness": 0.20, "level": "L1"},
                {"id": "shell1-d", "a": [0.0, 3.0], "b": [0.0, 0.0], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-a", "a": [2.0, 1.0], "b": [6.0, 1.0], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-b", "a": [6.0, 1.0], "b": [6.0, 4.0], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-c", "a": [6.0, 4.0], "b": [2.0, 4.0], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-d", "a": [2.0, 4.0], "b": [2.0, 1.0], "thickness": 0.20, "level": "L1"},
            ],
            "openings": [],
        },
        "open_boundary": {
            "walls": [
                {"id": "open-a", "a": [0.0, 0.0], "b": [5.0, 0.0], "thickness": 0.20, "level": "L1"},
                {"id": "open-b", "a": [5.0, 0.0], "b": [5.0, 4.0], "thickness": 0.20, "level": "L1"},
                {"id": "open-c", "a": [5.0, 4.0], "b": [0.0, 4.0], "thickness": 0.20, "level": "L1"},
            ],
            "openings": [],
        },
        "cross_floor": {
            "walls": [
                {"id": "cross-a", "a": [0.0, 0.0], "b": [5.0, 0.0], "thickness": 0.20, "level": "L1"},
                {"id": "cross-b", "a": [5.0, 0.0], "b": [5.0, 4.0], "thickness": 0.20, "level": "L2"},
                {"id": "cross-c", "a": [5.0, 4.0], "b": [0.0, 4.0], "thickness": 0.20, "level": "L2"},
                {"id": "cross-d", "a": [0.0, 4.0], "b": [0.0, 0.0], "thickness": 0.20, "level": "L1"},
            ],
            "openings": [],
        },
    }


def _ring(walls: Sequence[Mapping[str, object]]) -> list[tuple[float, float]]:
    """Return a centerline ring from ordered wall segments."""
    return [tuple(float(value) for value in wall["a"]) for wall in walls] + [
        tuple(float(value) for value in walls[0]["a"])
    ]


def _signed_area(points: Sequence[Sequence[float]]) -> float:
    """Return the signed area of a closed planar ring."""
    return 0.5 * sum(
        float(points[index][0]) * float(points[index + 1][1])
        - float(points[index + 1][0]) * float(points[index][1])
        for index in range(len(points) - 1)
    )


def _line_intersection(
    point_a: tuple[float, float],
    direction_a: tuple[float, float],
    point_b: tuple[float, float],
    direction_b: tuple[float, float],
) -> tuple[float, float]:
    """Intersect two non-parallel 2D lines used by offset faces."""
    determinant = direction_a[0] * direction_b[1] - direction_a[1] * direction_b[0]
    if abs(determinant) < 1e-12:
        raise ValueError("parallel wall edges cannot define an offset corner")
    delta = (point_b[0] - point_a[0], point_b[1] - point_a[1])
    scale = (delta[0] * direction_b[1] - delta[1] * direction_b[0]) / determinant
    return (point_a[0] + scale * direction_a[0], point_a[1] + scale * direction_a[1])


def _offset_ring(walls: Sequence[Mapping[str, object]], inward: bool) -> list[tuple[float, float]]:
    """Offset an ordered closed wall centerline by half the local wall thickness."""
    centerline = _ring(walls)[:-1]
    orientation = 1.0 if _signed_area(centerline + [centerline[0]]) > 0.0 else -1.0
    result: list[tuple[float, float]] = []
    for index, point in enumerate(centerline):
        previous = centerline[index - 1]
        following = centerline[(index + 1) % len(centerline)]
        previous_direction = (point[0] - previous[0], point[1] - previous[1])
        next_direction = (following[0] - point[0], following[1] - point[1])
        previous_length = math.hypot(*previous_direction)
        next_length = math.hypot(*next_direction)
        thickness = float(walls[index]["thickness"])
        distance = thickness / 2.0
        sign = orientation if inward else -orientation
        previous_normal = (
            sign * (-previous_direction[1] / previous_length),
            sign * (previous_direction[0] / previous_length),
        )
        next_normal = (
            sign * (-next_direction[1] / next_length),
            sign * (next_direction[0] / next_length),
        )
        previous_point = (point[0] + previous_normal[0] * distance, point[1] + previous_normal[1] * distance)
        next_point = (point[0] + next_normal[0] * distance, point[1] + next_normal[1] * distance)
        result.append(_line_intersection(previous_point, previous_direction, next_point, next_direction))
    return result + [result[0]]


def _wall_field_polygon(wall: Mapping[str, object]) -> list[tuple[float, float]]:
    """Return the independent rectangular physical field for one wall segment."""
    start = tuple(float(value) for value in wall["a"])
    end = tuple(float(value) for value in wall["b"])
    direction = (end[0] - start[0], end[1] - start[1])
    length = math.hypot(*direction)
    half = float(wall["thickness"]) / 2.0
    normal = (-direction[1] / length * half, direction[0] / length * half)
    return [
        (start[0] + normal[0], start[1] + normal[1]),
        (end[0] + normal[0], end[1] + normal[1]),
        (end[0] - normal[0], end[1] - normal[1]),
        (start[0] - normal[0], start[1] - normal[1]),
        (start[0] + normal[0], start[1] + normal[1]),
    ]


def _component_count(walls: Sequence[Mapping[str, object]]) -> tuple[int, dict[tuple[float, float], int]]:
    """Count endpoint-connected wall components and endpoint degrees."""
    endpoint_to_walls: dict[tuple[float, float], list[str]] = defaultdict(list)
    for wall in walls:
        for endpoint in (wall["a"], wall["b"]):
            endpoint_to_walls[tuple(float(value) for value in endpoint)].append(str(wall["id"]))
    adjacency: dict[str, set[str]] = defaultdict(set)
    for ids in endpoint_to_walls.values():
        for left in ids:
            for right in ids:
                if left != right:
                    adjacency[left].add(right)
    remaining = {str(wall["id"]) for wall in walls}
    components = 0
    while remaining:
        components += 1
        root = remaining.pop()
        queue = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
    return components, {point: len(ids) for point, ids in endpoint_to_walls.items()}


def _topology_status(walls: Sequence[Mapping[str, object]]) -> tuple[str, str, int, dict[str, int]]:
    """Classify closure and level consistency without a production tolerance."""
    components, degrees = _component_count(walls)
    levels = sorted({str(wall.get("level")) for wall in walls})
    degree_histogram = {
        str(degree): sum(1 for value in degrees.values() if value == degree)
        for degree in sorted(set(degrees.values()))
    }
    if len(levels) > 1:
        return "invalid", "cross_floor_or_analysis_plane_conflict", components, degree_histogram
    if not walls:
        return "not_available", "missing_wall_geometry", components, degree_histogram
    closed = all(value == 2 for value in degrees.values())
    if components == 1 and closed:
        return "computed", "one_connected_closed_shell", components, degree_histogram
    if components > 1 and closed:
        return "ambiguous", "multiple_closed_shells", components, degree_histogram
    return "partial", "open_or_disconnected_boundary", components, degree_histogram


def _area(points: Sequence[Sequence[float]]) -> float:
    """Return absolute polygon area for a closed ring."""
    return abs(_signed_area(points))


def _perimeter(points: Sequence[Sequence[float]]) -> float:
    """Return the perimeter of a closed ring."""
    return sum(
        math.hypot(float(points[index + 1][0]) - float(points[index][0]), float(points[index + 1][1]) - float(points[index][1]))
        for index in range(len(points) - 1)
    )


def _candidate_record(
    case_id: str,
    candidate_kind: str,
    fixture: Mapping[str, object],
    geometry: Sequence[Sequence[float]] | None,
    *,
    status: str,
    reason: str,
    source_kind: str,
    user_confirmed: bool,
    accepted: bool,
    diagnostic_only: bool,
    relation: str,
) -> dict[str, object]:
    """Create one auditable boundary candidate record."""
    candidate_id = f"candidate:{case_id}:{candidate_kind}"
    wall_refs = [str(wall["id"]) for wall in fixture.get("walls", ())]
    opening_refs = [str(opening["id"]) for opening in fixture.get("openings", ())]
    geometry_ref = f"geometry:{candidate_id}"
    return {
        "candidate_id": candidate_id,
        "candidate_refs": [candidate_id],
        "source_refs": wall_refs + [f"fixture:{case_id}"],
        "geometry_refs": [geometry_ref] if geometry else [],
        "candidate_kind": candidate_kind,
        "source_kind": source_kind,
        "priority": "user-authored" if source_kind == "user_authored" else "automatic candidate" if source_kind == "automatic_candidate" else "diagnostic-only",
        "scope_enclosure_geometry": {
            "geometry_ref": geometry_ref if geometry else None,
            "points": list(geometry) if geometry else [],
            "is_closed": bool(geometry and list(geometry[0]) == list(geometry[-1])),
            "area_m2": round(_area(geometry), 6) if geometry else None,
            "perimeter_m": round(_perimeter(geometry), 6) if geometry else None,
        },
        "physical_wall_field_geometry": {
            "wall_refs": wall_refs,
            "geometry_refs": [f"physical-field:{wall_ref}" for wall_ref in wall_refs],
            "thickness_m": sorted({float(wall["thickness"]) for wall in fixture.get("walls", ())}),
            "preserved_separately": True,
        },
        "wall_thickness": sorted({float(wall["thickness"]) for wall in fixture.get("walls", ())}),
        "opening_host_evidence": list(fixture.get("openings", ())),
        "analysis_plane": "fixture-world-plan-z=0" if candidate_kind != "not_available" else "unknown",
        "units": "m",
        "closure_scenario": "authored_closed_curve" if candidate_kind == "authored_closed_curve" else "closed_by_wall_topology_assumption",
        "status": status,
        "status_reason": reason,
        "provenance": {
            "method": "controlled_offset_geometry_probe" if candidate_kind in {"inner_wall_face", "outer_wall_face"} else "source_centerline_geometry" if candidate_kind == "wall_centerline" else "explicit_user_curve" if candidate_kind == "authored_closed_curve" else "diagnostic_topology_record",
            "source_case": case_id,
            "production_backend_selected": False,
            "fixed_threshold_used": False,
        },
        "wall_field_relation": relation,
        "user_confirmed": user_confirmed,
        "accepted": accepted,
        "diagnostic_only": diagnostic_only,
        "evidence_status": "available" if geometry else "not_available",
    }


def _controlled_candidates(fixture: Mapping[str, object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Build all four constructions and their independent source geometry."""
    walls = list(fixture["walls"])
    status, reason, components, degree_histogram = _topology_status(walls)
    centerline = _ring(walls)
    geometry_by_kind = {
        "inner_wall_face": _offset_ring(walls, inward=True),
        "outer_wall_face": _offset_ring(walls, inward=False),
        "wall_centerline": centerline,
        "authored_closed_curve": [tuple(point) for point in fixture["authored_curve"]],
    }
    relations = {
        "inner_wall_face": "touches_inner_edge_of_physical_wall_field",
        "outer_wall_face": "touches_outer_edge_of_physical_wall_field",
        "wall_centerline": "passes_through_physical_wall_field",
        "authored_closed_curve": "inside_inner_face_without_wall_field_overlap",
    }
    records = []
    for kind, geometry in geometry_by_kind.items():
        is_authored = kind == "authored_closed_curve"
        records.append(
            _candidate_record(
                "controlled_rectangular_room",
                kind,
                fixture,
                geometry,
                status=status,
                reason=reason,
                source_kind="user_authored" if is_authored else "automatic_candidate",
                user_confirmed=is_authored,
                accepted=is_authored,
                diagnostic_only=False,
                relation=relations[kind],
            )
        )
    source_geometry = {
        "scope_enclosure_geometry": {
            "source_kind": "ordered_wall_centerline_segments",
            "wall_segments": [
                {"id": wall["id"], "a": wall["a"], "b": wall["b"], "level": wall["level"]}
                for wall in walls
            ],
        },
        "physical_wall_field_geometry": [
            {
                "id": f"physical-field:{wall['id']}",
                "wall_ref": wall["id"],
                "polygon": _wall_field_polygon(wall),
                "thickness_m": float(wall["thickness"]),
                "level": wall["level"],
            }
            for wall in walls
        ],
        "opening_host_evidence": list(fixture.get("openings", ())),
        "candidate_geometry": {
            kind: {
                "geometry_ref": f"geometry:candidate:controlled_rectangular_room:{kind}",
                "points": points,
            }
            for kind, points in geometry_by_kind.items()
        },
    }
    comparison = {
        "case_id": "controlled_rectangular_room",
        "analysis_plane": "fixture-world-plan-z=0",
        "units": "m",
        "wall_thickness_m": sorted({float(wall["thickness"]) for wall in walls}),
        "topology": {
            "status": status,
            "reason": reason,
            "component_count": components,
            "endpoint_degree_histogram": degree_histogram,
        },
        "candidates": [
            {
                "candidate_kind": record["candidate_kind"],
                "status": record["status"],
                "area_m2": record["scope_enclosure_geometry"]["area_m2"],
                "perimeter_m": record["scope_enclosure_geometry"]["perimeter_m"],
                "wall_field_relation": record["wall_field_relation"],
                "user_confirmed": record["user_confirmed"],
                "accepted": record["accepted"],
            }
            for record in records
        ],
        "selection_experiment": {
            "priority_order": ["user-authored", "explicit IFC", "automatic candidate", "diagnostic-only", "not_available"],
            "selected_candidate_id": "candidate:controlled_rectangular_room:authored_closed_curve",
            "automatic_candidates_retained_as_provenance": True,
            "production_boundary_backend_selected": False,
        },
    }
    return records, {"source_geometry": source_geometry, "comparison": comparison}


def _propagation_case(case_id: str, fixture: Mapping[str, object]) -> dict[str, object]:
    """Propagate topology states to the three automatic constructions."""
    status, reason, components, degree_histogram = _topology_status(list(fixture.get("walls", ())))
    records = []
    for kind in ("inner_wall_face", "outer_wall_face", "wall_centerline"):
        geometry = None
        if status == "computed":
            geometry = _offset_ring(fixture["walls"], inward=kind == "inner_wall_face") if kind != "wall_centerline" else _ring(fixture["walls"])
        records.append(
            _candidate_record(
                case_id,
                kind,
                fixture,
                geometry,
                status=status if geometry else status,
                reason=reason,
                source_kind="automatic_candidate" if geometry else "diagnostic_only",
                user_confirmed=False,
                accepted=False,
                diagnostic_only=geometry is None,
                relation="not_verified_for_noncomputed_topology" if geometry is None else "derived_from_physical_wall_field",
            )
        )
    records.append(
        _candidate_record(
            case_id,
            "authored_closed_curve",
            fixture,
            None,
            status="not_available",
            reason="no_authored_curve_in_case",
            source_kind="diagnostic_only",
            user_confirmed=False,
            accepted=False,
            diagnostic_only=True,
            relation="not_available",
        )
    )
    return {
        "case_id": case_id,
        "fixture_kind": "synthetic_topology_variant",
        "analysis_plane": "fixture-world-plan-z=0" if status != "invalid" else "not_verified",
        "units": "m",
        "source_geometry": {
            "scope_enclosure_geometry": [
                {"id": wall["id"], "a": wall["a"], "b": wall["b"], "level": wall["level"]}
                for wall in fixture.get("walls", ())
            ],
            "physical_wall_field_geometry": [
                {"id": f"physical-field:{wall['id']}", "wall_ref": wall["id"], "polygon": _wall_field_polygon(wall), "thickness_m": wall["thickness"]}
                for wall in fixture.get("walls", ())
            ],
            "opening_host_evidence": list(fixture.get("openings", ())),
            "candidate_geometry": {},
        },
        "topology": {"status": status, "reason": reason, "component_count": components, "endpoint_degree_histogram": degree_histogram},
        "candidate_records": records,
        "selection": {
            "selected_candidate_id": None,
            "domain_status": "not_available" if status != "computed" else "provisional_candidates_available",
            "automatic_candidate_is_provisional": status == "computed",
            "user_confirmation_required": status == "computed",
            "candidate_selection_policy": "not_frozen",
        },
    }


def _ifc_shadow_inventory() -> dict[str, object]:
    """Inspect the real IFC source without extracting geometry."""
    if not LIVE_IFC.exists():
        return {
            "status": "not_available",
            "source_path": str(LIVE_IFC.relative_to(ROOT)).replace("\\", "/"),
            "reason": "live_ifc_file_missing",
            "geometry_adapter": "not_verified",
        }
    import ifcopenshell

    model = ifcopenshell.open(str(LIVE_IFC))
    entity_types = [
        "IfcProject", "IfcBuilding", "IfcBuildingStorey", "IfcWall", "IfcSlab", "IfcDoor",
        "IfcFurniture", "IfcGroup", "IfcSpace", "IfcOpeningElement", "IfcRelVoidsElement", "IfcRelFillsElement",
    ]
    units = []
    for assignment in model.by_type("IfcUnitAssignment"):
        for unit in assignment.Units or ():
            units.append({
                "entity": unit.is_a(),
                "unit_type": getattr(unit, "UnitType", None),
                "name": getattr(unit, "Name", None),
                "prefix": getattr(unit, "Prefix", None),
            })
    products = model.by_type("IfcProduct")
    return {
        "status": "native_inventory_only",
        "source_path": str(LIVE_IFC.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": _sha256(LIVE_IFC),
        "schema": model.schema,
        "counts": {entity_type: len(model.by_type(entity_type)) for entity_type in entity_types},
        "units": units,
        "placement_evidence": {
            "ifc_product_count": len(products),
            "products_with_object_placement": sum(getattr(product, "ObjectPlacement", None) is not None for product in products),
            "products_with_representation": sum(getattr(product, "Representation", None) is not None for product in products),
        },
        "analysis_plane": "not_verified",
        "wall_shell_topology": "not_verified",
        "candidate_generation": {
            kind: {"status": "not_verified", "reason": "native_inventory_only_without_wall_mesh_topology"}
            for kind in ("inner_wall_face", "outer_wall_face", "wall_centerline", "authored_closed_curve")
        },
        "door_state": "not_inferred_from_ifc_inventory",
        "source_and_visualization_role": "read_only_fallback_when_current_blender_not_observed",
    }


def _svg_poly(points: Sequence[Sequence[float]], x0: float, y0: float, scale: float, color: str, width: float, *, fill: str = "none", opacity: float = 1.0, dash: str = "") -> str:
    """Render one plan-view SVG polyline or polygon."""
    tokens = " ".join(f"{x0 + float(point[0]) * scale:.1f},{y0 - float(point[1]) * scale:.1f}" for point in points)
    dash_attr = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<polyline points='{tokens}' fill='{fill}' fill-opacity='{opacity}' stroke='{color}' stroke-width='{width}'{dash_attr}/>"


def _write_svg(path: Path, controlled: Mapping[str, object], shadow: Mapping[str, object]) -> None:
    """Write a static diagnostic figure with redundant color and line encodings."""
    width, height = 1280, 820
    layers = [
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' role='img' aria-label='D6 boundary construction diagnostic'>",
        "<rect width='100%' height='100%' fill='white'/>",
        "<text x='40' y='34' font-family='Arial' font-size='18' font-weight='bold'>Boundary construction — source fact and candidate diagnostic</text>",
    ]
    panel_x, panel_y, scale = 60, 300, 36.0
    layers.append("<rect x='40' y='55' width='520' height='220' fill='#fafafa' stroke='#d4d4d4'/>")
    layers.append("<text x='55' y='78' font-family='Arial' font-size='15' font-weight='bold'>controlled fixture: one closed shell</text>")
    for wall in controlled["source_geometry"]["physical_wall_field_geometry"]:
        layers.append(_svg_poly(wall["polygon"], panel_x, panel_y, scale, "#404040", 7, fill="#9ca3af", opacity=0.35))
    colors = {
        "inner_wall_face": ("#2563eb", "4", ""),
        "outer_wall_face": ("#dc2626", "4", "8 4"),
        "wall_centerline": ("#111827", "2", "2 4"),
        "authored_closed_curve": ("#16a34a", "4", ""),
    }
    for candidate in controlled["comparison"]["candidates"]:
        kind = candidate["candidate_kind"]
        points = controlled["source_geometry"]["candidate_geometry"][kind]["points"]
        color, line_width, dash = colors[kind]
        layers.append(_svg_poly(points, panel_x, panel_y, scale, color, float(line_width), dash=dash))
    layers.extend([
        "<text x='55' y='292' font-family='Arial' font-size='12' fill='#111827'>physical wall field retained; no free-space/route/walkability claim</text>",
        "<text x='610' y='78' font-family='Arial' font-size='15' font-weight='bold'>real IFC shadow inspection</text>",
        f"<text x='610' y='104' font-family='Arial' font-size='13'>schema: {shadow.get('schema', 'not_available')} | geometry: {shadow.get('wall_shell_topology', 'not_verified')}</text>",
        "<text x='610' y='128' font-family='Arial' font-size='13'>inner/outer/centerline: not_verified</text>",
        "<text x='610' y='152' font-family='Arial' font-size='13'>authored closed curve: not_available</text>",
        "<text x='610' y='176' font-family='Arial' font-size='13'>current Blender: current_blender_not_observed</text>",
        "<text x='610' y='200' font-family='Arial' font-size='13'>source: native IFC inventory only; door state not inferred</text>",
    ])
    legend = [
        ("#404040", "physical wall field", ""),
        ("#2563eb", "inner wall face", ""),
        ("#dc2626", "outer wall face", "8 4"),
        ("#111827", "wall centerline", "2 4"),
        ("#16a34a", "authored closed curve", ""),
    ]
    layers.append("<text x='55' y='355' font-family='Arial' font-size='15' font-weight='bold'>legend</text>")
    for index, (color, label, dash) in enumerate(legend):
        y = 385 + index * 28
        dash_attr = f" stroke-dasharray='{dash}'" if dash else ""
        layers.append(f"<line x1='60' y1='{y}' x2='102' y2='{y}' stroke='{color}' stroke-width='6'{dash_attr}/><text x='115' y='{y + 5}' font-family='Arial' font-size='13'>{label}</text>")
    layers.extend([
        "<text x='400' y='385' font-family='Arial' font-size='13' fill='#c2410c'>automatic/derived candidate</text>",
        "<text x='400' y='413' font-family='Arial' font-size='13' fill='#c2410c'>candidate not accepted</text>",
        "<text x='400' y='441' font-family='Arial' font-size='13' fill='#15803d'>user-confirmed</text>",
        "<text x='400' y='469' font-family='Arial' font-size='13' fill='#b91c1c'>not_verified / not_available</text>",
        "<text x='55' y='620' font-family='Arial' font-size='15' font-weight='bold'>geometry comparison (m²)</text>",
    ])
    y = 650
    for candidate in controlled["comparison"]["candidates"]:
        layers.append(
            f"<text x='55' y='{y}' font-family='Arial' font-size='13'>{candidate['candidate_kind']}: area={candidate['area_m2']:.3f}; relation={candidate['wall_field_relation']}; accepted={candidate['accepted']}</text>"
        )
        y += 24
    layers.append("</svg>")
    path.write_text("".join(layers), encoding="utf-8")


def _artifact_manifest(output: Path) -> dict[str, object]:
    """Build a manifest for all primary artifacts while excluding reproductions."""
    paths = [
        path for path in output.rglob("*")
        if path.is_file() and path.name not in {"artifact_manifest.json", "verification_report.json"} and not any(part.startswith("tmp_reproduction_") for part in path.relative_to(output).parts)
    ]
    return {
        "schema": "d6-boundary-construction-artifact-manifest-v1",
        "artifacts": [
            {"path": str(path.relative_to(output)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(paths)
        ],
    }


def _run(output: Path) -> dict[str, object]:
    """Run the controlled comparison, topology propagation, and IFC shadow inventory."""
    output.mkdir(parents=True, exist_ok=True)
    fixture = _fixture()
    controlled_records, controlled_payload = _controlled_candidates(fixture["controlled_rectangular_room"])
    cases = {
        "controlled_rectangular_room": {
            "candidate_records": controlled_records,
            "source_geometry": controlled_payload["source_geometry"],
            "comparison": controlled_payload["comparison"],
            "selection": controlled_payload["comparison"]["selection_experiment"],
        }
    }
    for case_id in ("automatic_closed_wall_shell", "multi_shell_conflict", "open_boundary", "cross_floor"):
        cases[case_id] = _propagation_case(case_id, fixture[case_id])

    # These assertions are the smallest runnable check for the non-trivial probe.
    assert {record["candidate_kind"] for record in controlled_records} == {
        "inner_wall_face", "outer_wall_face", "wall_centerline", "authored_closed_curve"
    }
    assert controlled_records[0]["physical_wall_field_geometry"]["preserved_separately"] is True
    assert cases["multi_shell_conflict"]["selection"]["selected_candidate_id"] is None
    assert cases["open_boundary"]["selection"]["domain_status"] == "not_available"
    assert cases["cross_floor"]["topology"]["status"] == "invalid"

    shadow = _ifc_shadow_inventory()
    _write_json(output / "boundary_comparison.json", {
        "schema": "d6-boundary-construction-comparison-v1",
        "date": DATE,
        "priority_order": ["user-authored", "explicit IFC", "automatic candidate", "diagnostic-only", "not_available"],
        "controlled_fixture": controlled_payload["comparison"],
        "cases": cases,
        "global_constraints": {
            "scope_enclosure_and_physical_wall_field_separate": True,
            "wall_thickness_retained": True,
            "free_space_connectivity_path_not_computed": True,
            "production_boundary_backend_not_selected": True,
            "current_blender_status": CURRENT_BLENDER_STATUS["status"],
        },
        "real_ifc_shadow": shadow,
        "next_gate": "owner boundary construction review before any free-space design",
    })
    _write_json(output / "fixture_manifest.json", {
        "schema": "d6-boundary-construction-fixture-manifest-v1",
        "controlled_fixture": {
            "case_id": "controlled_rectangular_room",
            "units": "m",
            "analysis_plane": "fixture-world-plan-z=0",
            "wall_thickness_m": [0.20],
            "candidate_kinds": ["inner_wall_face", "outer_wall_face", "wall_centerline", "authored_closed_curve"],
            "opening_scenario": "closed_by_assumption",
        },
        "propagation_variants": ["automatic_closed_wall_shell", "multi_shell_conflict", "open_boundary", "cross_floor"],
        "source_fixture": "test/fixtures/ifc4_description_fixture.py",
    })
    _write_json(output / "source_geometry.json", {
        "controlled_rectangular_room": controlled_payload["source_geometry"],
        "propagation_cases": {case_id: cases[case_id]["source_geometry"] for case_id in cases if case_id != "controlled_rectangular_room"},
        "separation_rule": "scope_enclosure_geometry, physical_wall_field_geometry, candidate_geometry, and opening_host_evidence remain separate",
    })
    _write_json(output / "real_ifc_shadow_inspection.json", shadow)
    _write_json(output / "provenance.json", {
        "read_only_sources": [
            "AGENTS.md",
            "docs/indoor_layout_evaluation_matrix_architecture_memory.md",
            "docs/project/space-field-ifc-neutral-scene-input-contract.md",
            "docs/project/evidence/d6-space-field-input-contract-owner-decision.md",
            "docs/project/evidence/d6-space-field-enclosed-room-domain-candidate-experiment.md",
            "features/scene_contract.py",
            "features/neutral_scene_views.py",
            "adapters/ifc_bonsai.py",
            "adapters/blender_geometry.py",
            "adapters/blender_preview.py",
            "test/fixtures/ifc4_description_fixture.py",
            str(LIVE_IFC.relative_to(ROOT)).replace("\\", "/"),
        ],
        "observed": ["controlled wall dimensions", "physical wall field polygons", "opening host evidence", "real IFC native inventory", "current Blender UI inventory"],
        "derived": ["inner/outer offset faces", "centerline and authored curve comparison", "topology status propagation", "static diagnostic visualization"],
        "assumptions": ["door/window closure is a scenario assumption", "offset geometry uses the recorded wall thickness, not a psychological threshold", "automatic candidates remain unaccepted until user confirmation", "current Blender was not observable through the available UI inventory"],
        "current_blender": CURRENT_BLENDER_STATUS,
    })
    _write_svg(output / "boundary_construction_diagnostic.svg", controlled_payload, shadow)
    _write_json(output / "command_log.json", {
        "runner": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
        "argv": sys.argv,
        "exit_code": 0,
        "scope": "bounded read-only boundary construction experiment",
        "blender_render": "pending_disposable_preview_command",
    })
    _write_json(output / "artifact_manifest.json", _artifact_manifest(output))
    return {"case_count": len(cases), "candidate_count": len(controlled_records), "output": str(output), "real_ifc_shadow_status": shadow.get("status")}


def main() -> int:
    """Parse the output path and run the bounded experiment."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = _run(args.output.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
