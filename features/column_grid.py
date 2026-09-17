from __future__ import annotations

from itertools import pairwise
from math import atan2, cos, degrees, hypot, radians, sin, sqrt
from statistics import mean

from .affordance.grid_backend import shape_overlap_area
from .affordance.models import Polygon, Rect
from .neutral_scene_views import AnalysisSceneInput, analysis_scene_view


def column_grid_evidence(scene: AnalysisSceneInput) -> dict:
    """Build neutral column-grid evidence from explicit authored axes."""
    scene = analysis_scene_view(scene)
    axes = [_axis_record(axis) for axis in scene.get("column_axes", [])]
    if not axes:
        return {
            "status": "not_available",
            "reason": "missing_explicit_column_axes",
            "columns": list(scene.get("columns", [])),
            "axes": [],
            "systems": [],
            "branches": [],
            "bays": [],
            "local_profiles": [],
            "global_relations": [],
            "field_profiles": [],
        }

    branches = _branches(axes)
    bays = [bay for branch in branches for bay in _branch_bays(branch)]
    _attach_bay_adjacency(bays)
    systems = _systems(branches)
    regions = list(scene.get("regions", []))

    return {
        "status": "computed",
        "reason": "explicit_column_axes",
        "columns": list(scene.get("columns", [])),
        "axes": axes,
        "systems": systems,
        "branches": branches,
        "bays": bays,
        "local_profiles": _local_profiles(regions, branches, bays),
        "global_relations": _global_relations(regions, systems, branches),
        "field_profiles": _field_profiles(regions, branches, bays),
    }


def column_grid_field_evidence(scene: dict) -> list[dict]:
    """Return only the continuous field profiles derived from explicit axes."""
    return column_grid_evidence(scene).get("field_profiles", [])


def _axis_record(axis: dict) -> dict:
    """Normalize one explicit axis record without inferring it from columns."""
    metadata = dict(axis.get("metadata", {}))
    points = axis.get("points") or _rect_line_points(axis["rect"])
    angle = _axis_angle(axis, points)
    # Grid and branch IDs come only from explicit axis metadata; physical
    # columns remain payload evidence and never synthesize axes here.
    return {
        "id": axis["id"],
        "source_id": axis["id"],
        "system_id": metadata.get("system-id")
        or metadata.get("grid-id")
        or "default_grid",
        "branch_id": metadata.get("branch-id") or "default_branch",
        "axis_list": metadata.get("axis-list") or _axis_list_from_angle(angle),
        "angle": round(angle, 4),
        "rect": axis["rect"],
        "points": points,
        "metadata": metadata,
    }


def _branches(axes: list[dict]) -> list[dict]:
    """Group explicit axes into authored branch records."""
    branches = []
    keys = sorted({(axis["system_id"], axis["branch_id"]) for axis in axes})
    for system_id, branch_id in keys:
        branch_axes = [
            axis
            for axis in axes
            if axis["system_id"] == system_id and axis["branch_id"] == branch_id
        ]
        branches.append(
            {
                "id": branch_id,
                "system_id": system_id,
                "axis_ids": [axis["id"] for axis in branch_axes],
                "axes": branch_axes,
                "trend_frame": _frame_from_angles(
                    [axis["angle"] for axis in branch_axes]
                ),
            }
        )
    return branches


def _systems(branches: list[dict]) -> list[dict]:
    """Group branches into authored column systems."""
    systems = []
    for system_id in sorted({branch["system_id"] for branch in branches}):
        system_branches = [
            branch for branch in branches if branch["system_id"] == system_id
        ]
        systems.append(
            {
                "id": system_id,
                "branch_ids": [branch["id"] for branch in system_branches],
                "global_trend_frame": _frame_from_angles(
                    [branch["trend_frame"]["angle"] for branch in system_branches]
                ),
                "source": "explicit_column_axes",
            }
        )
    return systems


def _global_relations(
    regions: list[dict],
    systems: list[dict],
    branches: list[dict],
) -> list[dict]:
    """Compare each region frame with authored system and branch frames."""
    relations = []
    for region in regions:
        frame = _region_frame(region)
        for system in systems:
            target_frame = system["global_trend_frame"]
            relations.append(
                {
                    "metric": "C_global",
                    "region_id": region["id"],
                    "target_kind": "system",
                    "target_id": system["id"],
                    "region_angle": frame["angle"],
                    "target_angle": target_frame["angle"],
                    "target_strength": target_frame["strength"],
                    "agreement": _axis_score(
                        frame["angle"], target_frame["angle"]
                    ),
                    "source": "explicit_column_axes",
                }
            )
        for branch in branches:
            target_frame = branch["trend_frame"]
            relations.append(
                {
                    "metric": "C_global",
                    "region_id": region["id"],
                    "target_kind": "branch",
                    "target_id": branch["id"],
                    "system_id": branch["system_id"],
                    "branch_id": branch["id"],
                    "region_angle": frame["angle"],
                    "target_angle": target_frame["angle"],
                    "target_strength": target_frame["strength"],
                    "agreement": _axis_score(
                        frame["angle"], target_frame["angle"]
                    ),
                    "source": "explicit_column_axes",
                }
            )
    return relations


def _local_profiles(
    regions: list[dict],
    branches: list[dict],
    bays: list[dict],
) -> list[dict]:
    """Build scale-local bay evidence for each region and authored branch."""
    profiles = []
    bays_by_branch = {
        (branch["system_id"], branch["id"]): [
            bay
            for bay in bays
            if bay["system_id"] == branch["system_id"]
            and bay["branch_id"] == branch["id"]
        ]
        for branch in branches
    }
    bay_by_id = {bay["id"]: bay for bay in bays}
    for region in regions:
        region_shape = _region_shape(region)
        region_frame = _region_frame(region)
        for branch in branches:
            branch_bays = bays_by_branch[(branch["system_id"], branch["id"])]
            if not branch_bays:
                # Local profiles require authored bay polygons for seed overlap
                # and fallback. Empty profiles would imply invented bay context.
                continue
            seed_ids = _seed_bay_ids(region_shape, branch_bays)
            for scale in [0, 1, "all"]:
                included_ids = _expand_bays(seed_ids, branch_bays, bay_by_id, scale)
                included_bays = [bay_by_id[bay_id] for bay_id in included_ids]
                profiles.append(
                    {
                        "metric": "C_local_profile",
                        "region_id": region["id"],
                        "system_id": branch["system_id"],
                        "branch_id": branch["id"],
                        "scale": scale,
                        "region_angle": region_frame["angle"],
                        "branch_angle": branch["trend_frame"]["angle"],
                        "frame_agreement": _axis_score(
                            region_frame["angle"], branch["trend_frame"]["angle"]
                        ),
                        "seed_bay_ids": seed_ids,
                        "included_bay_ids": included_ids,
                        "bay_grammar": _bay_grammar(region_shape, included_bays),
                        "source": "explicit_column_axes",
                    }
                )
    return profiles


def _field_profiles(
    regions: list[dict],
    branches: list[dict],
    bays: list[dict],
) -> list[dict]:
    """Aggregate deterministic probe evidence into one continuous profile per region."""
    bays_by_branch = {
        (branch["system_id"], branch["id"]): [
            bay
            for bay in bays
            if bay["system_id"] == branch["system_id"]
            and bay["branch_id"] == branch["id"]
        ]
        for branch in branches
    }
    profiles = []
    for region in regions:
        shape = _region_shape(region)
        probes = [
            _field_probe(point, branches, bays_by_branch)
            for point in _region_probe_points(shape, _region_frame(region)["angle"])
        ]
        branch_evidence = [
            evidence
            for probe in probes
            for evidence in probe["branch_evidence"]
            if evidence["weight"] > 0.0
        ]
        if not branch_evidence:
            continue
        angle, clarity = _field_frame(branch_evidence)
        support = mean(probe["support"] for probe in probes)
        # Support measures nearby structural mass, while clarity records whether
        # that local mass agrees on one axial frame. Neither grows by raw count.
        profiles.append(
            {
                "metric": "column_grid_field_profile",
                "region_id": region["id"],
                "angle": angle,
                "secondary_angle": round((angle + 90.0) % 180.0, 4),
                "support": round(support, 4),
                "clarity": clarity,
                "strength": round(support * clarity, 4),
                "probes": probes,
                "source": "explicit_column_axes_probe_field",
            }
        )
    return profiles


def _region_probe_points(shape: Rect | Polygon, angle: float) -> list[tuple[float, float]]:
    """Return stable region probes without creating a dense scene raster."""
    bounds = _shape_bounds(shape)
    if not isinstance(shape, Polygon):
        return [(bounds.cx, bounds.cy)]

    points = list(dict.fromkeys(shape.points))
    if len(points) < 3:
        return [(bounds.cx, bounds.cy)]
    center = _polygon_centroid(points, bounds)
    direction = (cos(radians(angle)), sin(radians(angle)))
    projections = [
        ((x - center[0]) * direction[0] + (y - center[1]) * direction[1])
        for x, y in points
    ]
    probes = [
        center,
        (center[0] + min(projections) * direction[0], center[1] + min(projections) * direction[1]),
        (center[0] + max(projections) * direction[0], center[1] + max(projections) * direction[1]),
    ]
    edges = list(pairwise([*points, points[0]]))
    # Long edges retain shape-sensitive probes without letting every small hull
    # corner become a separate field sample.
    for (x1, y1), (x2, y2) in sorted(
        edges,
        key=lambda edge: hypot(edge[1][0] - edge[0][0], edge[1][1] - edge[0][1]),
        reverse=True,
    )[:2]:
        probes.append(((x1 + x2) / 2.0, (y1 + y2) / 2.0))
    return list(dict.fromkeys((round(x, 9), round(y, 9)) for x, y in probes))


def _polygon_centroid(points: list[tuple[float, float]], bounds: Rect) -> tuple[float, float]:
    """Return the area centroid of a polygon, with bounds-center fallback."""
    area_factor = 0.0
    x_total = 0.0
    y_total = 0.0
    for (x1, y1), (x2, y2) in pairwise([*points, points[0]]):
        cross = x1 * y2 - x2 * y1
        area_factor += cross
        x_total += (x1 + x2) * cross
        y_total += (y1 + y2) * cross
    if abs(area_factor) <= 1e-9:
        return (bounds.cx, bounds.cy)
    return (x_total / (3.0 * area_factor), y_total / (3.0 * area_factor))


def _field_probe(
    point: tuple[float, float],
    branches: list[dict],
    bays_by_branch: dict[tuple[str, str], list[dict]],
) -> dict:
    """Evaluate authored branch evidence at one deterministic region probe."""
    evidence = []
    for branch in branches:
        branch_bays = bays_by_branch[(branch["system_id"], branch["id"])]
        if not branch_bays:
            continue
        nearest = min(branch_bays, key=lambda bay: _point_bay_distance(point, bay))
        distance = _point_bay_distance(point, nearest)
        scale = max(sqrt(max(nearest["polygon"].area, 1e-9)), 1e-9)
        # Local bay scale normalizes uneven spans, avoiding a fixed world radius.
        weight = 1.0 / (1.0 + distance / scale)
        evidence.append(
            {
                "system_id": branch["system_id"],
                "branch_id": branch["id"],
                "bay_id": nearest["id"],
                "angle": branch["trend_frame"]["angle"],
                "distance": round(distance, 4),
                "local_scale": round(scale, 4),
                "weight": round(weight, 4),
            }
        )
    # The maximum is normalized local structural support. It avoids treating a
    # duplicated or densely subdivided grid as stronger merely by item count.
    support = max((item["weight"] for item in evidence), default=0.0)
    return {
        "point": (round(point[0], 4), round(point[1], 4)),
        "support": round(support, 4),
        "branch_evidence": evidence,
    }


def _point_bay_distance(point: tuple[float, float], bay: dict) -> float:
    """Return Euclidean distance from a probe to one authored bay polygon."""
    polygon = bay["polygon"]
    if polygon.contains_point(*point):
        return 0.0
    edges = pairwise([*polygon.points, polygon.points[0]])
    return min(_point_segment_distance(point, start, end) for start, end in edges)


def _point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    """Return Euclidean point-to-segment distance for polygon bay proximity."""
    px, py = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-12:
        return hypot(px - x1, py - y1)
    ratio = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_squared))
    return hypot(px - (x1 + ratio * dx), py - (y1 + ratio * dy))


def _field_frame(evidence: list[dict]) -> tuple[float, float]:
    """Return the weighted orthogonal frame and its directional clarity."""
    weight_total = sum(item["weight"] for item in evidence)
    x = sum(item["weight"] * cos(radians(item["angle"] * 4.0)) for item in evidence)
    y = sum(item["weight"] * sin(radians(item["angle"] * 4.0)) for item in evidence)
    angle = (degrees(atan2(y, x)) / 4.0) % 90.0
    # 0 and 90 describe the same orthogonal frame. Floating-point signed zero
    # can otherwise surface that equivalent frame as a misleading 90 degrees.
    if abs(angle - 90.0) <= 1e-9:
        angle = 0.0
    clarity = hypot(x, y) / max(weight_total, 1e-9)
    return (round(angle, 4), round(clarity, 4))


def _region_frame(region: dict) -> dict:
    """Return an authored region frame, falling back to its bbox long axis."""
    raw = region.get("metadata", {}).get("axis-angle")
    if raw is not None:
        try:
            return {"angle": round(float(raw) % 180.0, 4), "basis": "metadata"}
        except ValueError:
            pass
    rect = region["rect"]
    angle = 0.0 if rect.width >= rect.height else 90.0
    return {"angle": angle, "basis": "bbox_long_axis"}


def _region_shape(region: dict) -> Rect | Polygon:
    """Return the inferred region polygon when present, otherwise its bbox."""
    points = []
    for point in region.get("points", []):
        try:
            x, y = point
            points.append((float(x), float(y)))
        except (TypeError, ValueError):
            continue
    unique_points = {(round(x, 9), round(y, 9)) for x, y in points}
    if len(unique_points) >= 3:
        # C_local consumes activity-region geometry from inference; the world
        # bbox remains a compatibility fallback for older region records.
        return Polygon(points=tuple(points))
    return region["rect"]


def _shape_bounds(shape: Rect | Polygon) -> Rect:
    """Return axis-aligned bounds for fallback distance and center checks."""
    return shape.bounds if isinstance(shape, Polygon) else shape


def _shape_bay_overlap_area(shape: Rect | Polygon, bay: dict) -> float:
    """Return region-shape overlap area with one generated column bay."""
    bay_shape = bay.get("polygon") or bay["rect"]
    # Region inference and bay generation already own the geometry shapes; the
    # column-grid layer only chooses which authored shapes participate.
    return shape_overlap_area(shape, bay_shape)


def _axis_score(first: float, second: float) -> float:
    """Score undirected orthogonal-frame agreement from 0 to 1."""
    diff = abs((first - second) % 180.0)
    diff = min(diff, 180.0 - diff)
    # Orthogonal grid frames treat an axis and its perpendicular as equivalent.
    frame_diff = min(diff, abs(90.0 - diff))
    return round(max(0.0, 1.0 - frame_diff / 45.0), 4)


def _seed_bay_ids(region_shape: Rect | Polygon, branch_bays: list[dict]) -> list[str]:
    """Choose overlapping seed bays, or the nearest bay when none overlap."""
    overlaps = [
        (bay["id"], _shape_bay_overlap_area(region_shape, bay))
        for bay in branch_bays
    ]
    seed_ids = sorted(bay_id for bay_id, area in overlaps if area > 0.0)
    if seed_ids:
        return seed_ids
    bounds = _shape_bounds(region_shape)
    # A no-overlap region still gets local context from the nearest explicit bay.
    nearest = min(
        branch_bays,
        key=lambda bay: (_rect_gap(bounds, bay["rect"]), bay["id"]),
    )
    return [nearest["id"]]


def _expand_bays(
    seed_bay_ids: list[str],
    branch_bays: list[dict],
    bay_by_id: dict[str, dict],
    scale: int | str,
) -> list[str]:
    """Expand seed bays by graph distance within one authored branch."""
    branch_ids = {bay["id"] for bay in branch_bays}
    if scale == "all":
        return sorted(branch_ids)
    included = set(seed_bay_ids)
    frontier = set(seed_bay_ids)
    for _ in range(int(scale)):
        next_frontier = {
            neighbor_id
            for bay_id in frontier
            for neighbor_id in bay_by_id[bay_id]["adjacent_bay_ids"]
            if neighbor_id in branch_ids and neighbor_id not in included
        }
        included.update(next_frontier)
        frontier = next_frontier
    return sorted(included)


def _bay_grammar(region_shape: Rect | Polygon, bays: list[dict]) -> list[dict]:
    """Summarize how a region shape sits inside included authored bays."""
    grammar = []
    region_area = max(region_shape.area, 1e-9)
    for bay in bays:
        overlap = _shape_bay_overlap_area(region_shape, bay)
        # The score is local containment evidence only, not a perceptual weight.
        grammar.append(
            {
                "bay_id": bay["id"],
                "overlap_area": round(overlap, 4),
                "region_area": round(region_area, 4),
                "overlap_score": round(overlap / region_area, 4),
                "region_center_in_bay": _local_in_bay(region_shape, bay),
            }
        )
    return grammar


def _local_in_bay(region_shape: Rect | Polygon, bay: dict) -> bool:
    """Return whether the region shape bounds center lies inside one bay."""
    bounds = _shape_bounds(region_shape)
    polygon = bay.get("polygon")
    # Keep the legacy field as a bounds-center proxy so adapter payloads stay
    # stable; full polygon-in-bay classification is a separate metric decision.
    if isinstance(polygon, Polygon):
        return polygon.contains_point(bounds.cx, bounds.cy)
    return bay["rect"].intersects(Rect(bounds.cx, bounds.cy, 0.0, 0.0))


def _rect_gap(first: Rect, second: Rect) -> float:
    """Return the shortest axis-aligned gap between two rectangles."""
    dx = max(second.left - first.right, first.left - second.right, 0.0)
    dy = max(second.top - first.bottom, first.top - second.bottom, 0.0)
    return (dx * dx + dy * dy) ** 0.5


def _branch_bays(branch: dict) -> list[dict]:
    """Create bay polygons from adjacent axes in two explicit axis lists."""
    axes_by_list: dict[str, list[dict]] = {}
    for axis in branch["axes"]:
        axes_by_list.setdefault(axis["axis_list"], []).append(axis)
    if len(axes_by_list) < 2:
        return []

    lists = sorted(axes_by_list)[:2]
    first_axes = sorted(axes_by_list[lists[0]], key=_axis_sort_key)
    second_axes = sorted(axes_by_list[lists[1]], key=_axis_sort_key)
    bays = []
    for a0, a1 in pairwise(first_axes):
        for b0, b1 in pairwise(second_axes):
            polygon = _bay_polygon(a0, a1, b0, b1)
            if polygon is None:
                continue
            # Bay IDs feed local profile lookup, so include the authored system
            # to keep same-named branches and axes from colliding globally.
            bay_id = (
                f"bay_{branch['system_id']}__{branch['id']}__"
                f"{a0['id']}__{a1['id']}__{b0['id']}__{b1['id']}"
            )
            bays.append(
                {
                    "id": bay_id,
                    "system_id": branch["system_id"],
                    "branch_id": branch["id"],
                    "axis_ids": [a0["id"], a1["id"], b0["id"], b1["id"]],
                    "axis_list_axis_ids": {
                        a0["axis_list"]: [a0["id"], a1["id"]],
                        b0["axis_list"]: [b0["id"], b1["id"]],
                    },
                    "polygon": polygon,
                    "rect": polygon.bounds,
                    "angle": branch["trend_frame"]["angle"],
                    "adjacent_bay_ids": [],
                }
            )
    return bays


def _attach_bay_adjacency(bays: list[dict]) -> None:
    """Connect bays that share one complete boundary axis pair."""
    for bay in bays:
        neighbors = [
            other["id"]
            for other in bays
            if other["id"] != bay["id"]
            and other["system_id"] == bay["system_id"]
            and other["branch_id"] == bay["branch_id"]
            and _share_boundary_axis_pair(bay, other)
        ]
        bay["adjacent_bay_ids"] = sorted(neighbors)


def _share_boundary_axis_pair(first: dict, second: dict) -> bool:
    """Return whether two bays share one full edge without skipped bays."""
    first_pairs = first["axis_list_axis_ids"]
    second_pairs = second["axis_list_axis_ids"]
    for axis_list, axis_ids in first_pairs.items():
        other_ids = second_pairs.get(axis_list, [])
        if len(set(axis_ids) & set(other_ids)) != 1:
            continue
        # The other axis list must describe the same strip; otherwise diagonal
        # corner touches and skipped strip bays would look like adjacency.
        remaining_lists = [key for key in first_pairs if key != axis_list]
        if any(
            set(first_pairs[key]) == set(second_pairs.get(key, []))
            for key in remaining_lists
        ):
            return True
    return False


def _axis_angle(axis: dict, points: list[tuple[float, float]]) -> float:
    """Return authored angle or derive an explicit axis angle from geometry."""
    raw = axis.get("metadata", {}).get("axis-angle")
    if raw is not None:
        try:
            return float(raw) % 180.0
        except ValueError:
            pass
    if len(points) >= 2:
        x1, y1 = points[0]
        x2, y2 = points[-1]
        return degrees(atan2(y2 - y1, x2 - x1)) % 180.0
    rect = axis["rect"]
    return 0.0 if rect.width >= rect.height else 90.0


def _axis_list_from_angle(angle: float) -> str:
    """Assign a stable list key when metadata omits U/V-style axis lists."""
    normalized = angle % 180.0
    return "x" if min(normalized, 180.0 - normalized) <= abs(normalized - 90.0) else "y"


def _axis_sort_key(axis: dict) -> tuple[float, float, str]:
    """Sort parallel axes by their perpendicular center coordinate."""
    angle = radians(axis["angle"] + 90.0)
    nx = cos(angle)
    ny = sin(angle)
    if nx < -1e-9 or (abs(nx) <= 1e-9 and ny < 0.0):
        nx = -nx
        ny = -ny
    # Projection on the axis normal orders parallel axes by offset, so vertical
    # axes sort by x even when their authored bbox centers have different y.
    cx, cy = _axis_center(axis)
    return (cx * nx + cy * ny, axis["angle"], axis["id"])


def _axis_center(axis: dict) -> tuple[float, float]:
    """Return the center of explicit axis points, falling back to the rect center."""
    points = axis.get("points") or []
    if len(points) >= 2:
        x1, y1 = points[0]
        x2, y2 = points[-1]
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
    rect = axis["rect"]
    return (rect.cx, rect.cy)


def _frame_from_angles(angles: list[float]) -> dict:
    """Average orthogonal trend frames so perpendicular axes share a frame."""
    if not angles:
        return {"angle": 0.0, "strength": 0.0}
    # Axis directions are undirected, so 180 degrees must be the same input as
    # 0 degrees before the four-angle average; otherwise signed zero can turn
    # a horizontal IFC branch into a false 90-degree trend.
    normalized_angles = [float(angle) % 180.0 for angle in angles]
    normalized_angles = [
        0.0 if abs(angle) <= 1e-9 or abs(angle - 180.0) <= 1e-9 else angle
        for angle in normalized_angles
    ]
    # Quadrupled angles collapse 0/90-degree orthogonal grid directions into a
    # single frame while preserving oblique branch trends.
    x = mean(cos(radians(angle * 4.0)) for angle in normalized_angles)
    y = mean(sin(radians(angle * 4.0)) for angle in normalized_angles)
    angle = (degrees(atan2(y, x)) / 4.0) % 90.0
    return {"angle": round(angle, 4), "strength": round((x * x + y * y) ** 0.5, 4)}


def _rect_line_points(rect: Rect) -> list[tuple[float, float]]:
    """Represent bbox-only axes as a two-point centerline."""
    if rect.width >= rect.height:
        return [(rect.left, rect.cy), (rect.right, rect.cy)]
    return [(rect.cx, rect.top), (rect.cx, rect.bottom)]


def _bay_polygon(a0: dict, a1: dict, b0: dict, b1: dict) -> Polygon | None:
    """Build one bay polygon from two axes in each direction."""
    # Bay corners are neutral geometry evidence: intersections of authored
    # centerlines, not inferred structural supports.
    points = [
        _line_intersection(a0, b0),
        _line_intersection(a0, b1),
        _line_intersection(a1, b1),
        _line_intersection(a1, b0),
    ]
    if any(point is None for point in points):
        return None
    corners = [point for point in points if point is not None]
    return Polygon(points=tuple([*corners, corners[0]]))


def _line_intersection(first: dict, second: dict) -> tuple[float, float] | None:
    """Return the intersection of two explicit axis centerlines."""
    (x1, y1), (x2, y2) = first["points"][0], first["points"][-1]
    (x3, y3), (x4, y4) = second["points"][0], second["points"][-1]
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) <= 1e-9:
        return None
    px = (
        (x1 * y2 - y1 * x2) * (x3 - x4)
        - (x1 - x2) * (x3 * y4 - y3 * x4)
    ) / den
    py = (
        (x1 * y2 - y1 * x2) * (y3 - y4)
        - (y1 - y2) * (x3 * y4 - y3 * x4)
    ) / den
    return (px, py)
