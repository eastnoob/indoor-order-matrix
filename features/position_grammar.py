from __future__ import annotations

from itertools import combinations
from math import atan2, cos, degrees, hypot, radians, sin
from statistics import mean, pstdev


def group_assembly_grammar_evidence(
    furniture_groups: list[dict],
    extents: list[dict],
) -> dict:
    """Build debug position evidence for extents inside each furniture group."""
    extents_by_id = {extent["id"]: extent for extent in extents}
    items = []
    for group in furniture_groups:
        members = [
            extents_by_id[extent_id]
            for extent_id in group.get("furniture_affordance_extent_ids", [])
            if extent_id in extents_by_id
        ]
        evidence = _group_position_evidence(group, members)
        if evidence is not None:
            items.append(evidence)
    return {
        "method": "local_frame_group_assembly_grammar_debug",
        "items": items,
    }


def region_position_grammar_evidence(
    furniture_groups: list[dict],
    *,
    allow_two_point_inferred_frame: bool = False,
) -> dict:
    """Build public position grammar evidence for furniture groups in scopes."""
    scopes = _position_scopes(furniture_groups)
    items = []
    items_by_scope_id = {}
    for scope in scopes:
        evidence = _scope_position_evidence(
            scope,
            allow_two_point_inferred_frame=allow_two_point_inferred_frame,
        )
        if evidence is not None:
            items.append(evidence)
            items_by_scope_id[scope["id"]] = evidence
    return {
        "method": "region_level_furniture_group_position_grammar",
        "scopes": [
            {
                "id": scope["id"],
                "kind": scope["kind"],
                "member_group_ids": list(scope["member_group_ids"]),
                "position-frame-angle": (
                    items_by_scope_id.get(scope["id"], {}).get("position-frame-angle")
                ),
                "position-frame-basis": (
                    items_by_scope_id.get(scope["id"], {}).get(
                        "position-frame-basis",
                        scope["position-frame-basis"],
                    )
                ),
            }
            for scope in scopes
        ],
        "items": items,
    }


def _position_scopes(furniture_groups: list[dict]) -> list[dict]:
    """Create analysis scopes that contain two or more furniture groups."""
    groups = [group for group in furniture_groups if _is_position_group(group)]
    by_region: dict[str, list[dict]] = {}
    for group in groups:
        region = group.get("activity_region_id") or group.get("region") or "room"
        by_region.setdefault(str(region), []).append(group)
    region_scopes = [
        _scope_record(f"position_scope_region_{region}", "activity_region", members)
        for region, members in sorted(by_region.items())
        if len(members) >= 2
    ]
    if region_scopes:
        return region_scopes
    if len(groups) >= 2:
        return [_scope_record("position_scope_room", "room_scope", groups)]
    return []


def _is_position_group(group: dict) -> bool:
    """Return whether a group should participate in public position scoring."""
    region = str(group.get("activity_region_id") or group.get("region") or "")
    metadata = group.get("metadata", {})
    if region.lower() == "global":
        return False
    if metadata.get("analysis-position") == "false":
        return False
    return True


def _scope_record(scope_id: str, kind: str, groups: list[dict]) -> dict:
    """Return one position scope with a shared local frame."""
    sorted_groups = sorted(groups, key=lambda item: item["id"])
    rect = _bounds(sorted_groups)
    metadata = _scope_metadata(sorted_groups)
    return {
        "id": scope_id,
        "kind": kind,
        "member_group_ids": [group["id"] for group in sorted_groups],
        "groups": sorted_groups,
        "rect": rect,
        "metadata": metadata,
        "position-frame-angle": None,
        "position-frame-basis": "position_frame_selected_by_grammar",
    }


def _bounds(records: list[dict]):
    """Return the axis-aligned union rect for records with Rect geometry."""
    left = min(record["rect"].left for record in records)
    right = max(record["rect"].right for record in records)
    top = min(record["rect"].top for record in records)
    bottom = max(record["rect"].bottom for record in records)
    rect_type = type(records[0]["rect"])
    return rect_type(
        cx=(left + right) / 2,
        cy=(top + bottom) / 2,
        width=right - left,
        height=bottom - top,
    )


def _scope_metadata(groups: list[dict]) -> dict:
    """Return authored position metadata shared by every group in a scope."""
    angles = []
    for group in groups:
        raw = group.get("metadata", {}).get("position-frame-angle")
        if raw is None:
            return {}
        angle = _parse_axial_angle(raw)
        if angle is None:
            return {}
        angles.append(angle)
    # Authored frames are scope metadata only when every group says the same
    # axial frame. A single authored member must not steer the public scope.
    rounded = {round(angle, 4) for angle in angles}
    if len(rounded) == 1:
        return {"position-frame-angle": rounded.pop()}
    return {}


def _parse_axial_angle(raw) -> float | None:
    """Return a normalized axial angle or None when metadata is not numeric."""
    try:
        return float(raw) % 180.0
    except (TypeError, ValueError):
        return None


def _scope_position_evidence(
    scope: dict,
    *,
    allow_two_point_inferred_frame: bool,
) -> dict | None:
    """Return selected grammar evidence for furniture groups inside one scope."""
    groups = scope["groups"]
    if len(groups) < 2:
        return None
    base_coords = [
        {
            "id": group["id"],
            "x": group["rect"].cx,
            "y": group["rect"].cy,
            "scale": max(group["rect"].width, group["rect"].height, 1e-9),
        }
        for group in groups
    ]
    candidates = [
        candidate
        for frame_index, frame in enumerate(
            _frame_candidates(
                scope,
                base_coords,
                allow_two_point_inferred_frame=allow_two_point_inferred_frame,
            )
        )
        for coords in [_project_coords(base_coords, scope, frame)]
        for candidate in _grammar_candidates(scope, coords, frame, frame_index)
    ]
    if not candidates:
        return None
    # Public position order is selected from position-only frames. Rotation and
    # region trend evidence are intentionally absent from this competition.
    selected = sorted(
        candidates,
        key=lambda item: (
            -item["position-fit"],
            0 if item["position-frame-basis"] == "authored_position_frame" else 1,
            item["complexity"],
            item["frame-priority"],
        ),
    )[0]
    selected["subject_kind"] = scope["kind"]
    selected["subject_id"] = scope["id"]
    selected["position-system-id"] = (
        f"{scope['id']}__{selected['position-grammar-type']}"
    )
    selected["scope-member-group-ids"] = list(scope["member_group_ids"])
    return selected


def _frame_candidates(
    scope: dict,
    coords: list[dict],
    *,
    allow_two_point_inferred_frame: bool = False,
) -> list[dict]:
    """Return position-only frame candidates for one scope."""
    raw = scope.get("metadata", {}).get("position-frame-angle")
    candidates = []
    angle = _parse_axial_angle(raw)
    if angle is not None:
        candidates.append((angle, "authored_position_frame"))
    self_inferred_allowed = len(coords) >= 3 or allow_two_point_inferred_frame
    if self_inferred_allowed:
        # Two points cannot disprove their own connecting line, so this branch
        # stays opt-in for two-point demo comparisons and default-on for 3+ points.
        for first, second in combinations(coords, 2):
            dx = second["x"] - first["x"]
            dy = second["y"] - first["y"]
            if hypot(dx, dy) > 1e-9:
                candidates.append((degrees(atan2(dy, dx)), "position_pair_direction"))
        pca = _pca_position_angle(coords)
        if pca is not None:
            candidates.append((pca, "position_pca_frame"))
    candidates.extend([(0.0, "global_position_fallback"), (90.0, "global_position_fallback")])

    frames = []
    seen = set()
    for angle, basis in candidates:
        axial = angle % 180.0
        key = round(axial, 4)
        if key in seen:
            continue
        seen.add(key)
        frames.append({"angle": axial, "basis": basis, "priority": len(frames)})
    return frames


def _pca_position_angle(coords: list[dict]) -> float | None:
    """Return the principal axis of furniture-group centers, if meaningful."""
    if len(coords) < 2:
        return None
    cx = mean(item["x"] for item in coords)
    cy = mean(item["y"] for item in coords)
    xx = mean((item["x"] - cx) ** 2 for item in coords)
    yy = mean((item["y"] - cy) ** 2 for item in coords)
    xy = mean((item["x"] - cx) * (item["y"] - cy) for item in coords)
    if xx <= 1e-9 and yy <= 1e-9:
        return None
    return (0.5 * degrees(atan2(2.0 * xy, xx - yy))) % 180.0


def _project_coords(base_coords: list[dict], scope: dict, frame: dict) -> list[dict]:
    """Project scene centers into one candidate position frame."""
    return [
        {
            **item,
            "u": u,
            "v": v,
        }
        for item in base_coords
        for u, v in [
            _project(
                item["x"],
                item["y"],
                scope["rect"].cx,
                scope["rect"].cy,
                frame["angle"],
            )
        ]
    ]


def _grammar_candidates(
    scope: dict,
    coords: list[dict],
    frame: dict,
    frame_index: int,
) -> list[dict]:
    """Return scored position grammar candidates for one frame."""
    candidates = [
        item
        for item in (
            _line_candidate(scope, coords, frame),
            _pair_candidate(scope, coords, frame),
            _grid_candidate(scope, coords, frame),
            _cluster_candidate(scope, coords, frame),
            _unstructured_candidate(scope, coords, frame),
        )
        if item is not None
    ]
    for item in candidates:
        item["frame-priority"] = frame_index
    return candidates


def _group_position_evidence(group: dict, members: list[dict]) -> dict | None:
    """Return the simplest available position grammar evidence for one group."""
    if len(members) < 2:
        return None
    frame = _group_frame(group)
    if frame is None:
        return None
    coords = [
        {
            "id": member["id"],
            "x": member["rect"].cx,
            "y": member["rect"].cy,
            "u": u,
            "v": v,
            "scale": max(member["rect"].width, member["rect"].height, 1e-9),
        }
        for member in members
        for u, v in [
            _project(
                member["rect"].cx,
                member["rect"].cy,
                group["rect"].cx,
                group["rect"].cy,
                frame["angle"],
            )
        ]
    ]
    authored = _authored_candidate(group, coords, frame)
    if authored is not None:
        return authored
    pair = _pair_candidate(group, coords, frame)
    if len(coords) == 2 and pair is not None:
        return pair
    candidates = [
        item
        for item in (
            _line_candidate(group, coords, frame),
            pair,
            _grid_candidate(group, coords, frame),
        )
        if item is not None
    ]
    if not candidates:
        return None
    # Fit is primary, but lower complexity wins ties so a row does not become a
    # grid merely because a line can be described as a degenerate grid.
    return sorted(candidates, key=lambda item: (-item["position-fit"], item["complexity"]))[0]


def _group_frame(group: dict) -> dict | None:
    """Read the local frame from canonical group metadata."""
    raw = group.get("metadata", {}).get("group-axis-angle")
    if raw is None:
        return None
    try:
        return {
            "angle": float(raw) % 180.0,
            "basis": group.get("metadata", {}).get("group-axis-basis", "group-axis"),
        }
    except (TypeError, ValueError):
        return None


def _project(x: float, y: float, cx: float, cy: float, angle: float) -> tuple[float, float]:
    """Project scene coordinates into a local u/v frame."""
    theta = radians(angle)
    ux, uy = cos(theta), sin(theta)
    vx, vy = -uy, ux
    dx, dy = x - cx, y - cy
    return dx * ux + dy * uy, dx * vx + dy * vy


def _unproject(u: float, v: float, cx: float, cy: float, angle: float) -> tuple[float, float]:
    """Map local u/v coordinates back to scene coordinates."""
    theta = radians(angle)
    ux, uy = cos(theta), sin(theta)
    vx, vy = -uy, ux
    return cx + u * ux + v * vx, cy + u * uy + v * vy


def _authored_candidate(group: dict, coords: list[dict], frame: dict) -> dict | None:
    """Score authored local slots when complete member-slot metadata exists."""
    raw = group.get("metadata", {}).get("position-slots")
    if not raw:
        return None
    slots = {}
    for chunk in raw.split(";"):
        if not chunk.strip() or ":" not in chunk:
            return None
        member_id, pair = chunk.split(":", 1)
        values = pair.split(",")
        if len(values) != 2:
            return None
        try:
            slots[member_id.strip()] = (float(values[0]), float(values[1]))
        except ValueError:
            return None
    if {item["id"] for item in coords} - set(slots):
        return None
    scale = _stable_scale([], coords, group)
    residuals = [
        _residual_record(item, slots[item["id"]][0], slots[item["id"]][1], group, frame, scale)
        for item in coords
    ]
    return _evidence(group, frame, "authored", residuals, len(coords), len(slots), complexity=0)


def _line_candidate(group: dict, coords: list[dict], frame: dict) -> dict:
    """Score one-axis spacing plus cross-axis residual."""
    ordered = sorted(coords, key=lambda item: item["u"])
    gaps = [b["u"] - a["u"] for a, b in zip(ordered, ordered[1:])]
    gap_scale = _stable_scale(gaps, coords, group)
    v_center = mean(item["v"] for item in coords)
    residuals = [
        _residual_record(item, item["u"], v_center, group, frame, gap_scale)
        for item in coords
    ]
    # A line grammar needs both even spacing along u and low residual across v.
    residual_fit = _fit(mean(item["normalized"] for item in residuals))
    fit = min(_cv_score(gaps), residual_fit)
    return _evidence(group, frame, "line", residuals, len(coords), len(coords), complexity=1, fit=fit)


def _pair_candidate(group: dict, coords: list[dict], frame: dict) -> dict | None:
    """Score two-member matched offsets around the local origin."""
    if len(coords) != 2:
        return None
    ordered = sorted(coords, key=lambda item: item["u"])
    first, second = ordered
    v_center = mean([first["v"], second["v"]])
    half_span = abs(second["u"] - first["u"]) / 2.0
    scale = _stable_scale([abs(second["u"] - first["u"])], coords, group)
    residuals = [
        _residual_record(first, -half_span, v_center, group, frame, scale),
        _residual_record(second, half_span, v_center, group, frame, scale),
    ]
    return _evidence(group, frame, "pair", residuals, len(coords), 2, complexity=2)


def _grid_candidate(group: dict, coords: list[dict], frame: dict) -> dict | None:
    """Score a row/column grammar in the local u/v frame."""
    if len(coords) < 4:
        return None
    scale = _stable_scale([], coords, group)
    columns = _axis_slots([item["u"] for item in coords], scale)
    rows = _axis_slots([item["v"] for item in coords], scale)
    slot_count = len(columns) * len(rows)
    if len(columns) < 2 or len(rows) < 2 or slot_count > len(coords) * 1.25:
        return None
    residuals = []
    for item in coords:
        # Greedy nearest row/column slot is enough for this proxy because slots
        # are diagnostic evidence, not a final assignment solver.
        slot_u = min(columns, key=lambda value: abs(value - item["u"]))
        slot_v = min(rows, key=lambda value: abs(value - item["v"]))
        residuals.append(_residual_record(item, slot_u, slot_v, group, frame, scale))
    return _evidence(group, frame, "grid", residuals, len(coords), slot_count, complexity=3)


def _cluster_candidate(group: dict, coords: list[dict], frame: dict) -> dict | None:
    """Score compact members around one centroid slot."""
    if len(coords) < 3:
        return None
    slot_u = mean(item["u"] for item in coords)
    slot_v = mean(item["v"] for item in coords)
    scale = _stable_scale(_nearest_neighbor_distances(coords), coords, group)
    residuals = [
        _residual_record(item, slot_u, slot_v, group, frame, scale)
        for item in coords
    ]
    return _evidence(group, frame, "cluster", residuals, len(coords), 1, complexity=4)


def _unstructured_candidate(group: dict, coords: list[dict], frame: dict) -> dict:
    """Return the always-available low-confidence fallback evidence."""
    slot_u = mean(item["u"] for item in coords)
    slot_v = mean(item["v"] for item in coords)
    scale = _stable_scale(_nearest_neighbor_distances(coords), coords, group)
    residuals = [
        _residual_record(item, slot_u, slot_v, group, frame, scale)
        for item in coords
    ]
    evidence = _evidence(
        group,
        frame,
        "unstructured",
        residuals,
        len(coords),
        1,
        complexity=5,
        fit=min(0.25, _fit(mean(item["normalized"] for item in residuals))),
    )
    evidence["position-confidence"] = min(evidence["position-confidence"], 0.25)
    return evidence


def _nearest_neighbor_distances(coords: list[dict]) -> list[float]:
    """Return each point's nearest center distance for local scale estimation."""
    distances = []
    for item in coords:
        others = [
            hypot(item["u"] - other["u"], item["v"] - other["v"])
            for other in coords
            if other is not item
        ]
        if others:
            distances.append(min(others))
    return distances


def _axis_slots(values: list[float], scale: float) -> list[float]:
    """Cluster one projected coordinate axis into slot centers."""
    if not values:
        return []
    tolerance = max(scale * 0.2, 1e-9)
    clusters: list[list[float]] = []
    for value in sorted(values):
        if not clusters or abs(value - mean(clusters[-1])) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [mean(cluster) for cluster in clusters]


def _residual_record(
    item: dict,
    slot_u: float,
    slot_v: float,
    group: dict,
    frame: dict,
    scale: float,
) -> dict:
    """Return one member-to-slot residual in local and scene coordinates."""
    slot_x, slot_y = _unproject(
        slot_u,
        slot_v,
        group["rect"].cx,
        group["rect"].cy,
        frame["angle"],
    )
    distance = hypot(item["u"] - slot_u, item["v"] - slot_v)
    normalized = distance / max(scale, 1e-9)
    return {
        "id": item["id"],
        "x": round(item["x"], 4),
        "y": round(item["y"], 4),
        "u": round(item["u"], 4),
        "v": round(item["v"], 4),
        "slot_u": round(slot_u, 4),
        "slot_v": round(slot_v, 4),
        "slot_x": round(slot_x, 4),
        "slot_y": round(slot_y, 4),
        "distance": round(distance, 4),
        "normalized": round(normalized, 4),
    }


def _stable_scale(values: list[float], coords: list[dict], group: dict) -> float:
    """Return the local distance scale used to normalize position residuals."""
    positive = [abs(value) for value in values if abs(value) > 1e-9]
    if positive:
        return mean(positive)
    member_sizes = [item["scale"] for item in coords if item["scale"] > 1e-9]
    if member_sizes:
        return mean(member_sizes)
    rect = group["rect"]
    return max(rect.width, rect.height, 1.0)


def _cv_score(values: list[float]) -> float:
    """Return a unit score for equal spacing along one axis."""
    positive = [abs(value) for value in values if abs(value) > 1e-9]
    if len(positive) < 2:
        return 1.0
    avg = mean(positive)
    if avg <= 1e-9:
        return 0.0
    return 1.0 / (1.0 + pstdev(positive) / avg)


def _fit(mean_residual: float) -> float:
    """Map normalized residual evidence into a compact unit fit score."""
    return 1.0 / (1.0 + max(0.0, mean_residual))


def _confidence(grammar: str, member_count: int, slot_count: int, fit: float) -> float:
    """Return reliability evidence for the selected grammar."""
    target = 4.0 if grammar == "grid" else 3.0
    count_score = min(1.0, member_count / target)
    slot_score = 1.0 / (1.0 + abs(slot_count - member_count) / max(member_count, 1))
    authored_bonus = 0.1 if grammar == "authored" else 0.0
    # Authored slots are stronger reliability evidence than inferred slots
    # because they come from the neutral input contract.
    return round(min(1.0, fit * 0.5 + count_score * 0.3 + slot_score * 0.2 + authored_bonus), 4)


def _evidence(
    group: dict,
    frame: dict,
    grammar: str,
    residuals: list[dict],
    member_count: int,
    slot_count: int,
    *,
    complexity: int,
    fit: float | None = None,
) -> dict:
    """Create one adapter-safe grammar evidence record."""
    mean_residual = mean(item["normalized"] for item in residuals)
    selected_fit = _fit(mean_residual) if fit is None else fit
    return {
        "id": f"position_grammar_{group['id']}",
        "subject_id": group["id"],
        "subject_kind": "furniture_group",
        "position-frame-angle": round(frame["angle"], 4),
        "position-frame-basis": frame["basis"],
        "position-grammar-type": grammar,
        "position-fit": round(selected_fit, 4),
        "position-confidence": _confidence(grammar, member_count, slot_count, selected_fit),
        "position-residual-mean": round(mean_residual, 4),
        "position-residual-max": round(max(item["normalized"] for item in residuals), 4),
        "position-member-count": member_count,
        "position-slot-count": slot_count,
        "position-system-id": f"{group['id']}__{grammar}",
        "slots": [
            {
                "id": f"{group['id']}__slot_{index}",
                "x": residual["slot_x"],
                "y": residual["slot_y"],
                "u": residual["slot_u"],
                "v": residual["slot_v"],
            }
            for index, residual in enumerate(residuals)
        ],
        "assignments": [item["id"] for item in residuals],
        "residuals": residuals,
        "complexity": complexity,
    }
