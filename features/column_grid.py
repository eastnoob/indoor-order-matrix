from __future__ import annotations

from itertools import pairwise
from math import atan2, cos, degrees, radians, sin
from statistics import mean

from .affordance.grid_backend import shape_overlap_area
from .affordance.models import Polygon, Rect


def column_grid_evidence(scene: dict) -> dict:
    """Build neutral column-grid evidence from explicit authored axes."""
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
    }


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
    # Quadrupled angles collapse 0/90-degree orthogonal grid directions into a
    # single frame while preserving oblique branch trends.
    x = mean(cos(radians(angle * 4.0)) for angle in angles)
    y = mean(sin(radians(angle * 4.0)) for angle in angles)
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
