from __future__ import annotations

from itertools import combinations
from math import atan2, cos, degrees, radians, sin, sqrt
from statistics import mean

from .affordance.models import Rect


def infer_scene_evidence(scene: dict) -> dict:
    """Infer analysis evidence from a neutral scene, independent of SVG loading."""
    zones = affordance_zones(scene)
    extents = furniture_affordance_extents(scene)
    groups = furniture_groups(scene, extents)
    candidates = inferred_region_candidates(scene)
    regions = inferred_regions(scene, candidates)
    gap_paths = inferred_region_gap_paths(candidates)
    networks = spatial_networks(groups, gap_paths)
    boundaries = boundary_semantics(scene)
    return {
        "affordance_zones": zones,
        "furniture_affordance_extents": extents,
        "furniture_groups": groups,
        "inferred_region_candidates": candidates,
        "inferred_regions": regions,
        "inferred_region_gap_paths": gap_paths,
        "spatial_networks": networks,
        "boundary_semantics": boundaries,
        "inferred_region_gap_path_graph": build_inferred_region_gap_path_graph(
            candidates,
            gap_paths,
            scene=scene,
        ),
    }


def affordance_zones(scene: dict) -> list[dict]:
    """Collect all furniture affordance zones in a neutral scene."""
    return [
        zone
        for obj in scene.get("objects", [])
        for zone in record_affordance_zones(obj)
    ]


def furniture_affordance_extents(scene: dict) -> list[dict]:
    """Infer one maximum affordance extent for each furniture object."""
    return sorted(
        [
            _furniture_affordance_extent_record(obj)
            for obj in scene.get("objects", [])
            if _participates_in_region_inference(obj)
        ],
        key=lambda item: item["id"],
    )


def furniture_groups(scene: dict, extents: list[dict] | None = None) -> list[dict]:
    """Build canonical furniture groups from semantic keys and affordance extents."""
    extents = extents if extents is not None else furniture_affordance_extents(scene)
    objects_by_id = {obj["id"]: obj for obj in scene.get("objects", [])}
    extents_by_group: dict[str, list[dict]] = {}
    for extent in extents:
        source_object = objects_by_id.get(extent["object_id"], extent)
        group_key = _furniture_group_key(source_object)
        if not group_key:
            continue
        extents_by_group.setdefault(group_key, []).append(extent)
    groups = []
    for group_key, group_extents in sorted(extents_by_group.items()):
        sorted_extents = sorted(group_extents, key=lambda item: item["id"])
        activity_region_id = _analysis_region_key(sorted_extents[0]) or group_key
        # The group extent is the union envelope; overlaps are relation evidence,
        # not a replacement for the group's full maximum affordance extent.
        group_rect = _bounds(sorted_extents)
        members = [
            objects_by_id[extent["object_id"]]
            for extent in sorted_extents
            if extent["object_id"] in objects_by_id
        ]
        frame = _furniture_group_frame(members, sorted_extents)
        groups.append(
            {
                "id": f"furniture_group_{group_key}",
                "activity_region_id": activity_region_id,
                "region": activity_region_id,
                "member_ids": sorted(extent["object_id"] for extent in sorted_extents),
                "furniture_affordance_extent_ids": [
                    extent["id"] for extent in sorted_extents
                ],
                "rect": group_rect,
                "bbox": _rect_bbox(group_rect),
                "overlap_evidence": _extent_overlap_evidence(sorted_extents),
                "metadata": {
                    "level": "furniture_group",
                    "source": "semantic_region_grouped_furniture_affordance_extents",
                    "geometry_basis": "union_envelope_of_member_furniture_affordance_extents",
                    **_group_frame_metadata(frame),
                },
            }
        )
    return groups


def spatial_networks(furniture_groups: list[dict], gap_paths: list[dict]) -> list[dict]:
    """Build shared-schema spatial networks for internal and inter-region scopes."""
    networks = [
        {
            "id": f"spatial_network_region_internal_{group['activity_region_id']}",
            "scope": "region_internal",
            "nodes": [
                {
                    "id": extent_id,
                    "kind": "furniture_affordance_extent",
                }
                for extent_id in group["furniture_affordance_extent_ids"]
            ],
            "edges": _furniture_group_internal_edges(group),
            "components": [[extent_id] for extent_id in group["furniture_affordance_extent_ids"]],
            "metadata": {
                "method": "furniture_group_member_extent_network_skeleton",
                "furniture_group_id": group["id"],
            },
        }
        for group in furniture_groups
    ]
    region_node_ids = sorted(
        {
            region_id
            for path in gap_paths
            for region_id in (path["region_a"], path["region_b"])
        }
    )
    adjacency = {region_id: set() for region_id in region_node_ids}
    for path in gap_paths:
        adjacency.setdefault(path["region_a"], set()).add(path["region_b"])
        adjacency.setdefault(path["region_b"], set()).add(path["region_a"])
    networks.append(
        {
            "id": "spatial_network_inter_region_gap_paths",
            "scope": "inter_region",
            "nodes": [
                {
                    "id": region_id,
                    "kind": "activity_region_candidate",
                }
                for region_id in region_node_ids
            ],
            "edges": [
                {
                    "id": path["id"],
                    "a": path["region_a"],
                    "b": path["region_b"],
                    "kind": "gap_path",
                    "thickness": round(path["thickness"], 4),
                }
                for path in sorted(gap_paths, key=lambda item: item["id"])
            ],
            "components": _components({region_id: {} for region_id in region_node_ids}, adjacency)
            if region_node_ids
            else [],
            "metadata": {
                "method": "shared_spatial_network_schema_from_furniture_groups_and_gap_paths",
            },
        }
    )
    return networks


def boundary_semantics(scene: dict) -> list[dict]:
    """Normalize boundary-like records into walk/see/grouping semantic profiles."""
    openings_by_boundary: dict[str, list[str]] = {}
    for entry in scene.get("entries", []):
        host = entry.get("metadata", {}).get("host-boundary")
        if host:
            openings_by_boundary.setdefault(host, []).append(entry["id"])
    semantics = []
    for boundary in sorted(scene.get("boundaries", []), key=lambda item: item["id"]):
        weights = boundary.get("weights", {})
        metadata = boundary.get("metadata", {})
        thickness = _float_metadata(metadata, "thickness")
        grouping_strength = round(float(weights.get("grouping_strength", 0.0)), 4)
        semantics.append(
            {
                "id": boundary["id"],
                "kind": metadata.get("boundary-kind", boundary.get("role", "boundary")),
                "walk_passable": float(weights.get("walk_block", 0.0)) < 0.5,
                "see_passable": float(weights.get("see_block", 0.0)) < 0.5,
                "thickness": round(thickness, 4),
                "grouping_strength": grouping_strength,
                "opening_ids": sorted(openings_by_boundary.get(boundary["id"], [])),
                "surface_identity": thickness == 0.0 and grouping_strength > 0.0,
                "metadata": {
                    "source": "authored_boundary_weights_and_metadata",
                },
            }
        )
    return semantics


def inferred_region_candidates(scene: dict) -> list[dict]:
    """Infer candidate activity regions from objects, affordances, and boundary cues."""
    return _spacing_margin_expanded_candidates(
        _raw_inferred_region_candidates(scene),
        scene.get("size", (0.0, 0.0)),
        scene,
    )


def inferred_regions(scene: dict, candidates: list[dict]) -> list[dict]:
    """Return inferred candidates that are not already explicit scene regions."""
    existing_region_keys = {
        region.get("region") for region in scene.get("regions", [])
    }
    return [
        candidate
        for candidate in candidates
        if candidate.get("region") not in existing_region_keys
    ]


def inferred_region_gap_paths(inferred_regions: list[dict]) -> list[dict]:
    """Infer axis-aligned gap bands between region bounding boxes."""
    gap_paths = []
    for region_a, region_b in combinations(inferred_regions, 2):
        rect_a = region_a["rect"]
        rect_b = region_b["rect"]
        top = max(rect_a.top, rect_b.top)
        bottom = min(rect_a.bottom, rect_b.bottom)
        if bottom > top:
            left_region, right_region = sorted(
                (region_a, region_b),
                key=lambda region: region["rect"].cx,
            )
            left = left_region["rect"].right
            right = right_region["rect"].left
            if right > left:
                gap_rect = Rect(
                    cx=(left + right) / 2,
                    cy=(top + bottom) / 2,
                    width=right - left,
                    height=bottom - top,
                )
                if not _gap_path_blocked_by_intermediate_region(
                    gap_rect,
                    (left_region, right_region),
                    inferred_regions,
                ):
                    gap_paths.append(
                        _inferred_region_gap_path(
                            left_region,
                            right_region,
                            gap_rect,
                            "vertical",
                        )
                    )
        left = max(rect_a.left, rect_b.left)
        right = min(rect_a.right, rect_b.right)
        if right > left:
            top_region, bottom_region = sorted(
                (region_a, region_b),
                key=lambda region: region["rect"].cy,
            )
            top_edge = top_region["rect"].bottom
            bottom_edge = bottom_region["rect"].top
            if bottom_edge > top_edge:
                gap_rect = Rect(
                    cx=(left + right) / 2,
                    cy=(top_edge + bottom_edge) / 2,
                    width=right - left,
                    height=bottom_edge - top_edge,
                )
                if not _gap_path_blocked_by_intermediate_region(
                    gap_rect,
                    (top_region, bottom_region),
                    inferred_regions,
                ):
                    gap_paths.append(
                        _inferred_region_gap_path(
                            top_region,
                            bottom_region,
                            gap_rect,
                            "horizontal",
                        )
                    )
    return sorted(gap_paths, key=lambda item: item["id"])


def build_inferred_region_gap_path_graph(
    inferred_regions: list[dict],
    gap_paths: list[dict],
    sampled_walkable_space: dict | None = None,
    gap_path_occupancy: list[dict] | None = None,
    gap_path_free_space_overlap: list[dict] | None = None,
    gap_path_cad_free_space_overlap: list[dict] | None = None,
    *,
    scene: dict | None = None,
) -> dict:
    """Build graph evidence that connects inferred regions through usable gap bands."""
    occupancy_by_gap_path = {
        item["gap_path_id"]: item
        for item in gap_path_occupancy or []
    }
    free_space_overlap_by_gap_path = {
        item["gap_path_id"]: item
        for item in gap_path_free_space_overlap or []
    }
    cad_free_space_overlap_by_gap_path = {
        item["gap_path_id"]: item
        for item in gap_path_cad_free_space_overlap or []
    }
    has_cad_free_space_overlap = bool(cad_free_space_overlap_by_gap_path)
    nodes = [
        {
            "id": region["id"],
            "region": region["region"],
        }
        for region in sorted(inferred_regions, key=lambda region: region["id"])
    ]
    edges = []
    for path in gap_paths:
        occupancy = occupancy_by_gap_path.get(path["id"], {})
        free_space_overlap = free_space_overlap_by_gap_path.get(path["id"], {})
        cad_free_space_overlap = cad_free_space_overlap_by_gap_path.get(path["id"], {})
        occupancy_ratio = occupancy.get("occupancy_ratio", 0.0)
        edge = {
            "id": path["id"],
            "a": path["region_a"],
            "b": path["region_b"],
            "orientation": path["orientation"],
            "thickness": round(path["thickness"], 4),
            "overlap_span": round(path["overlap_span"], 4),
            "clear_status": gap_path_clear_status(occupancy_ratio),
            "occupancy_ratio": occupancy_ratio,
            "free_space_overlap_ratio": free_space_overlap.get(
                "free_space_overlap_ratio",
                0.0,
            ),
        }
        if has_cad_free_space_overlap:
            # CAD overlap is stronger support evidence, but it stays additive here.
            edge["cad_free_space_overlap_ratio"] = cad_free_space_overlap.get(
                "cad_free_space_overlap_ratio",
                0.0,
            )
        edges.append(edge)
    adjacency = {node["id"]: set() for node in nodes}
    for edge in edges:
        adjacency.setdefault(edge["a"], set()).add(edge["b"])
        adjacency.setdefault(edge["b"], set()).add(edge["a"])
    node_map = {node["id"]: node for node in nodes}
    components = _components(node_map, adjacency) if node_map else []
    # A gap band is usable only when it is clear and supported by free space
    walkable_proxy_edges = [
        edge["id"]
        for edge in edges
        if edge["clear_status"] == "clear_proxy"
        and edge["free_space_overlap_ratio"] > 0
    ]
    walkable_proxy_edge_widths = [
        {
            "id": edge["id"],
            "thickness": edge["thickness"],
            "overlap_span": edge["overlap_span"],
        }
        for edge in edges
        if edge["id"] in walkable_proxy_edges
    ]
    # Manual path width is a demand parameter, not an inferred SVG feature
    required_path_width = _required_path_width(scene or {})
    minimum_width = (
        required_path_width
        if required_path_width is not None
        else round(sampled_walkable_space["resolution"] / 2, 4)
        if sampled_walkable_space
        else None
    )
    minimum_width_basis = (
        "manual_required_path_width"
        if required_path_width is not None
        else "half_sampled_grid_resolution"
        if minimum_width is not None
        else None
    )
    minimum_width_evidence = (
        ["scene.settings.required_path_width"]
        if required_path_width is not None
        else sampled_walkable_space.get("resolution_evidence", [])
        if sampled_walkable_space
        else []
    )
    width_evidence = [
        {
            "id": item["id"],
            "thickness": item["thickness"],
            "minimum_width": minimum_width,
            "passes": item["thickness"] >= minimum_width,
        }
        for item in walkable_proxy_edge_widths
        if minimum_width is not None
    ]
    width_pass_edges = [item["id"] for item in width_evidence if item["passes"]]
    width_fail_edges = [item["id"] for item in width_evidence if not item["passes"]]
    walkable_proxy_adjacency = {node["id"]: set() for node in nodes}
    for edge in edges:
        if edge["id"] not in walkable_proxy_edges:
            continue
        walkable_proxy_adjacency.setdefault(edge["a"], set()).add(edge["b"])
        walkable_proxy_adjacency.setdefault(edge["b"], set()).add(edge["a"])
    walkable_proxy_components = (
        _components(node_map, walkable_proxy_adjacency) if node_map else []
    )
    graph = {
        "method": "inferred_gap_path_region_adjacency_graph_proxy",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "clear_edge_count": sum(
            1 for edge in edges if edge["clear_status"] == "clear_proxy"
        ),
        "occupied_edge_count": sum(
            1 for edge in edges if edge["clear_status"] == "occupied_proxy"
        ),
        "free_space_supported_edge_count": sum(
            1 for edge in edges if edge["free_space_overlap_ratio"] > 0
        ),
        "walkable_proxy_edge_count": len(walkable_proxy_edges),
        "walkable_proxy_min_thickness": min(
            (item["thickness"] for item in walkable_proxy_edge_widths),
            default=None,
        ),
        "walkable_proxy_mean_thickness": round(
            mean(item["thickness"] for item in walkable_proxy_edge_widths),
            4,
        )
        if walkable_proxy_edge_widths
        else None,
        "component_count": len(components),
        "walkable_proxy_component_count": len(walkable_proxy_components),
        "components": components,
        "walkable_proxy_components": walkable_proxy_components,
        "nodes": nodes,
        "edges": edges,
        "walkable_proxy_edges": walkable_proxy_edges,
        "walkable_proxy_edge_widths": walkable_proxy_edge_widths,
        "minimum_width": minimum_width,
        "minimum_width_basis": minimum_width_basis,
        "minimum_width_evidence": minimum_width_evidence,
        "width_pass_edge_count": len(width_pass_edges),
        "width_fail_edge_count": len(width_fail_edges),
        "width_pass_edges": width_pass_edges,
        "width_fail_edges": width_fail_edges,
        "width_evidence": width_evidence,
    }
    if has_cad_free_space_overlap:
        cad_free_space_supported_edges = [
            edge["id"]
            for edge in edges
            if edge.get("cad_free_space_overlap_ratio", 0.0) > 0
        ]
        graph.update(
            {
                "cad_free_space_supported_edge_count": (
                    len(cad_free_space_supported_edges)
                ),
                "cad_free_space_supported_edges": cad_free_space_supported_edges,
            }
        )
    return graph


def record_affordance_zones(record: dict) -> list[dict]:
    """Convert one object record into side-specific affordance rectangles."""
    zones = []
    for side, depth in _affordance_margins(record).items():
        if depth <= 0:
            continue
        zones.append(
            {
                "id": f"affordance_zone_{record['id']}_{side}",
                "object_id": record["id"],
                "region": _analysis_region_key(record),
                "side": side,
                "depth": round(depth, 4),
                "source": _affordance_margin_source(record, side),
                "rect": _affordance_zone_rect(record["rect"], side, depth),
                "footprint_rect": record["rect"],
            }
        )
    return zones


def gap_path_clear_status(occupancy_ratio: float) -> str:
    """Classify a gap path as clear or occupied from proxy occupancy evidence."""
    return "occupied_proxy" if occupancy_ratio > 0 else "clear_proxy"


def _raw_inferred_region_candidates(scene: dict) -> list[dict]:
    """Create unexpanded region candidates from semantic furniture group keys."""
    groups_by_region: dict[str, list[dict]] = {}
    for group in furniture_groups(scene):
        # Activity regions can contain several furniture groups; keeping only
        # one group makes region trend look falsely strong and single-sourced.
        groups_by_region.setdefault(group["region"], []).append(group)
    # Group objects by neutral region keys, falling back to BIM furniture-group
    # keys when a base map has not already assigned final activity regions.
    region_keys = sorted(
        {
            _analysis_region_key(obj)
            for obj in scene.get("objects", [])
            if _analysis_region_key(obj) and _participates_in_region_inference(obj)
        }
    )
    candidates = []
    for region_key in region_keys:
        members = [
            obj
            for obj in scene.get("objects", [])
            if _analysis_region_key(obj) == region_key
            and _participates_in_region_inference(obj)
        ]
        if not members:
            continue
        extents = [_furniture_affordance_extent_record(obj) for obj in members]
        # Activity regions are composed from per-furniture maximum affordance extents
        rects = [
            extent["rect"]
            for extent in extents
        ]
        boundary_cues = [
            boundary
            for boundary in scene.get("boundaries", [])
            if _analysis_region_key(boundary) == region_key
            and boundary.get("weights", {}).get("grouping_strength", 0.0) > 0.0
        ]
        rects.extend(boundary["rect"] for boundary in boundary_cues)
        region_rect = _bounds([{"rect": rect} for rect in rects])
        member_ids = sorted(obj["id"] for obj in members)
        child_extent_ids = sorted(extent["id"] for extent in extents)
        affordance_zone_ids = [
            zone_id
            for extent in extents
            for zone_id in extent["affordance_zone_ids"]
        ]
        boundary_cue_ids = sorted(boundary["id"] for boundary in boundary_cues)
        candidate = _inferred_region_record(
            region_key,
            region_rect,
            member_ids,
            child_extent_ids,
            affordance_zone_ids,
            boundary_cue_ids,
        )
        candidates.append(
            _attach_region_axis_metadata(
                candidate,
                members,
                rects,
                groups_by_region.get(region_key, []),
                scene.get("size", (0.0, 0.0)),
            )
        )
    return candidates


def _inferred_region_record(
    region_key: str,
    region_rect: Rect,
    member_ids: list[str],
    child_extent_ids: list[str],
    affordance_zone_ids: list[str],
    boundary_cue_ids: list[str],
) -> dict:
    """Create the neutral record used for an inferred activity region."""
    return {
        "id": f"inferred_region_{region_key}",
        "role": "region",
        "group": region_key,
        "region": region_key,
        "rect": region_rect,
        "points": [],
        "weights": {
            "walk_block": 0.0,
            "see_block": 0.0,
            "grouping_strength": 0.0,
        },
        "metadata": {
            "inferred": "true",
            "level": "activity_region_candidate",
            "source": "affordance_zone_boundary_cue_expanded_group_bounds",
            "geometry_basis": "object_footprints_plus_affordance_zone_rects",
            "member_ids": ",".join(member_ids),
            "child_extent_ids": ",".join(child_extent_ids),
            "affordance_zone_ids": ",".join(sorted(affordance_zone_ids)),
            "boundary_cue_ids": ",".join(boundary_cue_ids),
        },
        "adapter_refs": {},
    }


def _candidate_member_rects(scene: dict, candidate: dict) -> list[Rect]:
    """Look up footprint rectangles for the objects named by a candidate."""
    member_ids = {
        item
        for item in candidate["metadata"].get("member_ids", "").split(",")
        if item
    }
    return [
        obj["rect"]
        for obj in scene.get("objects", [])
        if obj["id"] in member_ids
    ]


def _member_spacing_margin(rects: list[Rect]) -> float:
    """Estimate a small expansion margin from nearest positive member spacing."""
    if len(rects) < 4:
        return float("inf")
    gaps = []
    for a, b in combinations(rects, 2):
        if min(a.bottom, b.bottom) > max(a.top, b.top):
            gaps.append(max(a.left, b.left) - min(a.right, b.right))
        if min(a.right, b.right) > max(a.left, b.left):
            gaps.append(max(a.top, b.top) - min(a.bottom, b.bottom))
    positive_gaps = [gap for gap in gaps if gap > 0]
    if not positive_gaps:
        return float("inf")
    return min(positive_gaps) * 0.25


def _spacing_margin_expanded_candidates(
    candidates: list[dict],
    scene_size: tuple[float, float],
    scene: dict,
) -> list[dict]:
    """Expand inferred region candidates using local spacing between groups."""
    if len(candidates) < 2:
        return candidates
    explicit_by_region = {
        region["region"]: region
        for region in scene.get("regions", [])
        if region.get("metadata", {}).get("analysis-region") != "false"
    }
    expanded = []
    for candidate in candidates:
        # Expand candidates just enough to represent repeated-group spacing
        boundary_cue_ids = [
            cue_id
            for cue_id in candidate["metadata"].get("boundary_cue_ids", "").split(",")
            if cue_id
        ]
        if boundary_cue_ids:
            expanded.append(candidate)
            continue
        rect = candidate["rect"]
        member_rects = _candidate_member_rects(scene, candidate)
        margin = round(
            min(
                max(rect.width, rect.height) * 0.25,
                _member_spacing_margin(member_rects),
            ),
            4,
        )
        side_margins = {
            "left": margin,
            "right": margin,
            "top": margin,
            "bottom": margin,
        }
        for other in candidates:
            if other is candidate:
                continue
            other_rect = other["rect"]
            if min(rect.bottom, other_rect.bottom) > max(rect.top, other_rect.top):
                if other_rect.left >= rect.right:
                    side_margins["right"] = min(
                        side_margins["right"],
                        max(0.0, (other_rect.left - rect.right) * 0.25),
                    )
                elif rect.left >= other_rect.right:
                    side_margins["left"] = min(
                        side_margins["left"],
                        max(0.0, (rect.left - other_rect.right) * 0.25),
                    )
            if min(rect.right, other_rect.right) > max(rect.left, other_rect.left):
                if other_rect.top >= rect.bottom:
                    side_margins["bottom"] = min(
                        side_margins["bottom"],
                        max(0.0, (other_rect.top - rect.bottom) * 0.25),
                    )
                elif rect.top >= other_rect.bottom:
                    side_margins["top"] = min(
                        side_margins["top"],
                        max(0.0, (rect.top - other_rect.bottom) * 0.25),
                    )
        if not all(value > 0 and value != float("inf") for value in side_margins.values()):
            expanded.append(candidate)
            continue
        candidate_rect = _clamp_rect_to_scene_size(
            Rect(
                cx=(rect.left - side_margins["left"] + rect.right + side_margins["right"]) / 2,
                cy=(rect.top - side_margins["top"] + rect.bottom + side_margins["bottom"]) / 2,
                width=rect.width + side_margins["left"] + side_margins["right"],
                height=rect.height + side_margins["top"] + side_margins["bottom"],
            ),
            scene_size,
        )
        explicit = explicit_by_region.get(candidate["region"])
        if explicit and _rect_iou(candidate_rect, explicit["rect"]) < _rect_iou(
            candidate["rect"],
            explicit["rect"],
        ):
            expanded.append(candidate)
            continue
        widened = dict(candidate)
        metadata = dict(candidate["metadata"])
        metadata["source"] = "affordance_zone_boundary_cue_expanded_group_bounds"
        metadata["spacing_margin"] = str(margin)
        metadata["spacing_side_margins"] = ",".join(
            f"{side}:{value}"
            for side, value in {
                "left": round(rect.left - candidate_rect.left, 4),
                "right": round(candidate_rect.right - rect.right, 4),
                "top": round(rect.top - candidate_rect.top, 4),
                "bottom": round(candidate_rect.bottom - rect.bottom, 4),
            }.items()
        )
        widened["metadata"] = metadata
        widened["rect"] = candidate_rect
        if candidate.get("points"):
            widened["points"] = _expand_points_bbox(candidate["points"], candidate_rect)
        expanded.append(widened)
    return expanded


def _attach_region_axis_metadata(
    candidate: dict,
    members: list[dict],
    rects: list[Rect],
    groups: list[dict],
    scene_size: tuple[float, float],
) -> dict:
    """Add organization-frame trend evidence and a selected region polygon."""
    # Region shape must include affordance extents while retaining true member
    # points when the adapter provides rotated footprint geometry.
    points = [
        point
        for rect in rects
        for point in _rect_points(rect)
    ]
    points.extend(
        point
        for member in members
        for point in _record_points(member)
    )
    fallback_frame = _furniture_group_frame(
        members,
        [{"rect": rect} for rect in rects],
    )
    frame = _region_frame_mean(groups, fallback_frame)
    frame, explainability_metadata = _frame_with_explainability_correction(
        frame,
        points,
        members,
    )
    shape = _region_shape(points, frame["angle"], scene_size)
    enriched = dict(candidate)
    metadata = dict(candidate["metadata"])
    metadata.update(
        {
            "axis-angle": str(round(frame["angle"], 4)),
            "axis-strength": str(round(frame["strength"], 4)),
            "axis-basis": "furniture_group_frame_mean",
            "secondary-axis-angle": str(round((frame["angle"] + 90.0) % 180.0, 4)),
            "axis-primary-extent": str(round(frame["primary_extent"], 4)),
            "axis-secondary-extent": str(round(frame["secondary_extent"], 4)),
            "axis-clarity": str(round(frame["clarity"], 4)),
            "axis-shape-clarity": str(round(frame["clarity"], 4)),
            "axis-trend-strength": str(round(frame["strength"], 4)),
            "axis-member-alignment": str(round(frame["member_alignment"], 4)),
            "axis-member-count": str(len(members)),
            "axis-group-count": str(len(groups)),
            "axis-group-ids": ",".join(group["id"] for group in groups),
            **explainability_metadata,
            **_region_shape_metadata(shape, frame),
        }
    )
    enriched["metadata"] = metadata
    # Keep the existing axis-aligned candidate bbox stable for downstream path,
    # occupancy, and adapter metrics; the oriented frame lives in points/metadata.
    enriched["rect"] = candidate["rect"]
    enriched["points"] = shape["points"]
    return enriched


def _pca_frame_stats(points: list[tuple[float, float]]) -> dict:
    """Compute a deterministic two-axis frame from affordance geometry points."""
    if len(points) < 2:
        return _empty_frame_stats()
    cx = mean(x for x, _y in points)
    cy = mean(y for _x, y in points)
    centered = [(x - cx, y - cy) for x, y in points]
    # The covariance matrix captures how the whole furniture-group extent spreads,
    # independent of individual object orientation labels.
    cov_xx = mean(x * x for x, _y in centered)
    cov_yy = mean(y * y for _x, y in centered)
    cov_xy = mean(x * y for x, y in centered)
    total = cov_xx + cov_yy
    if total <= 1e-9:
        return _empty_frame_stats()
    delta = sqrt((cov_xx - cov_yy) ** 2 + 4.0 * cov_xy * cov_xy)
    primary_variance = (total + delta) / 2.0
    secondary_variance = (total - delta) / 2.0
    # Closed-form 2D PCA angle for the major eigenvector.
    angle = (degrees(0.5 * atan2(2.0 * cov_xy, cov_xx - cov_yy))) % 180.0
    primary_extent, secondary_extent = _frame_extents(points, angle)
    clarity = max(0.0, min(1.0, (primary_variance - secondary_variance) / total))
    return {
        "angle": angle,
        "strength": clarity,
        "clarity": clarity,
        "primary_extent": primary_extent,
        "secondary_extent": secondary_extent,
    }


def _furniture_group_frame(members: list[dict], extents: list[dict]) -> dict:
    """Compute one furniture-group frame from affordance extent geometry."""
    points = [
        point
        for extent in extents
        for point in _rect_points(extent["rect"])
    ]
    points.extend(
        point
        for member in members
        for point in _record_points(member)
    )
    stats = _pca_frame_stats(points)
    member_frame = _member_frame_consensus(members)
    member_alignment = member_frame["strength"]
    if member_frame["weight"] > 0.0:
        # Trend ground truth is member frame consensus; PCA remains geometry
        # evidence for shape diagnostics and fallback when no member frame exists.
        angle = member_frame["angle"]
        strength = member_frame["strength"]
        basis = "member_frame_consensus"
    else:
        angle = stats["angle"]
        strength = stats["clarity"]
        basis = "affordance_group_pca_frame"
    return {
        "angle": angle,
        "strength": strength,
        "clarity": stats["clarity"],
        "member_alignment": member_alignment,
        "support": member_frame["weight"],
        "geometry_angle": stats["angle"],
        "primary_extent": stats["primary_extent"],
        "secondary_extent": stats["secondary_extent"],
        "basis": basis,
    }


def _group_frame_metadata(frame: dict) -> dict:
    """Return string metadata for a canonical furniture-group trend frame."""
    return {
        "group-axis-angle": str(round(frame["angle"], 4)),
        "group-secondary-axis-angle": str(round((frame["angle"] + 90.0) % 180.0, 4)),
        "group-axis-strength": str(round(frame["strength"], 4)),
        "group-axis-basis": frame["basis"],
        "group-axis-primary-extent": str(round(frame["primary_extent"], 4)),
        "group-axis-secondary-extent": str(round(frame["secondary_extent"], 4)),
        "group-axis-clarity": str(round(frame["clarity"], 4)),
        "group-axis-member-alignment": str(round(frame["member_alignment"], 4)),
        "group-axis-support": str(round(frame["support"], 4)),
        "group-axis-geometry-angle": str(round(frame["geometry_angle"], 4)),
    }


def _region_frame_mean(groups: list[dict], fallback_frame: dict) -> dict:
    """Average activity-group frames into a region trend frame."""
    frames = [_frame_from_group(group) for group in groups]
    if not frames:
        return dict(fallback_frame)
    weighted_x = 0.0
    weighted_y = 0.0
    total_weight = 0.0
    for frame in frames:
        weight = frame["strength"] if frame["strength"] > 0.0 else 1.0
        theta = radians(frame["angle"] * 4.0)
        weighted_x += weight * cos(theta)
        weighted_y += weight * sin(theta)
        total_weight += weight
    if total_weight <= 0.0:
        return dict(fallback_frame)
    angle = _orthogonal_frame_angle(degrees(atan2(weighted_y, weighted_x)) / 4.0)
    strength = min(1.0, sqrt(weighted_x * weighted_x + weighted_y * weighted_y) / total_weight)
    return {
        "angle": _orthogonal_frame_angle(angle),
        "strength": strength * mean(frame["strength"] for frame in frames),
        "clarity": mean(frame["clarity"] for frame in frames),
        "member_alignment": mean(frame["member_alignment"] for frame in frames),
        "primary_extent": mean(frame["primary_extent"] for frame in frames),
        "secondary_extent": mean(frame["secondary_extent"] for frame in frames),
    }


def _frame_with_explainability_correction(
    frame: dict,
    points: list[tuple[float, float]],
    members: list[dict],
) -> tuple[dict, dict]:
    """Return a region frame corrected only when orthogonal evidence dominates."""
    evidence = _frame_explainability_record(points, members, frame["angle"])
    corrected = dict(frame)
    if evidence["snap_candidate"]:
        corrected["angle"] = evidence["orthogonal_angle"]
        corrected["member_alignment"] = evidence["orthogonal_alignment"]
    # The final angle may be normalized or corrected after PCA, so extents must
    # be recomputed in the same frame that downstream overlays draw.
    corrected["primary_extent"], corrected["secondary_extent"] = _frame_extents(
        points,
        corrected["angle"],
    )
    return corrected, _frame_explainability_metadata(evidence)


def _frame_from_group(group: dict) -> dict:
    """Parse activity-group frame metadata back into numeric frame evidence."""
    metadata = group.get("metadata", {})
    return {
        "angle": float(metadata.get("group-axis-angle", 0.0) or 0.0),
        "strength": float(metadata.get("group-axis-strength", 0.0) or 0.0),
        "clarity": float(metadata.get("group-axis-clarity", 0.0) or 0.0),
        "member_alignment": float(
            metadata.get("group-axis-member-alignment", 0.0) or 0.0
        ),
        "primary_extent": float(metadata.get("group-axis-primary-extent", 0.0) or 0.0),
        "secondary_extent": float(
            metadata.get("group-axis-secondary-extent", 0.0) or 0.0
        ),
    }


def _empty_frame_stats() -> dict:
    """Return zero-strength frame metadata for degenerate point clouds."""
    return {
        "angle": 0.0,
        "strength": 0.0,
        "clarity": 0.0,
        "primary_extent": 0.0,
        "secondary_extent": 0.0,
    }


def _frame_extents(points: list[tuple[float, float]], angle: float) -> tuple[float, float]:
    """Return point-cloud ranges along the PCA primary and secondary axes."""
    theta = radians(angle)
    c = cos(theta)
    s = sin(theta)
    # Projection ranges are kept separate from normalized clarity so visual
    # overlays can show both real geometry scale and confidence.
    primary = [x * c + y * s for x, y in points]
    secondary = [-x * s + y * c for x, y in points]
    return max(primary) - min(primary), max(secondary) - min(secondary)


def _frame_explainability_record(
    points: list[tuple[float, float]],
    members: list[dict],
    angle: float,
) -> dict:
    """Compare the current frame with its nearest orthogonal interpretation."""
    orthogonal_angle = _nearest_orthogonal_angle(angle)
    pca_area = _frame_area(points, angle)
    orthogonal_area = _frame_area(points, orthogonal_angle)
    pca_alignment = _member_alignment_for_angle(members, angle)
    orthogonal_alignment = _member_alignment_for_angle(members, orthogonal_angle)
    area_loss = orthogonal_area / pca_area if pca_area > 1e-9 else 0.0
    alignment_loss = (
        orthogonal_alignment / pca_alignment
        if pca_alignment > 1e-9
        else 0.0
    )
    snap_candidate = _orthogonal_frame_explains_better(
        pca_area,
        orthogonal_area,
        pca_alignment,
        orthogonal_alignment,
    )
    return {
        "angle": angle,
        "orthogonal_angle": orthogonal_angle,
        "pca_area": pca_area,
        "orthogonal_area": orthogonal_area,
        "area_ratio": area_loss,
        "pca_alignment": pca_alignment,
        "orthogonal_alignment": orthogonal_alignment,
        "alignment_ratio": alignment_loss,
        "snap_candidate": snap_candidate,
    }


def _orthogonal_frame_explains_better(
    pca_area: float,
    orthogonal_area: float,
    pca_alignment: float,
    orthogonal_alignment: float,
) -> bool:
    """Return true when an orthogonal frame Pareto-dominates the current frame."""
    # Numerical tolerance only absorbs floating-point noise; the rule itself is
    # not angle-threshold based. Orthogonal correction is allowed only when it
    # keeps the envelope no larger and explains member frames at least as well.
    epsilon = 1e-9
    has_member_support = orthogonal_alignment > epsilon
    area_not_worse = orthogonal_area <= pca_area + epsilon
    alignment_not_worse = orthogonal_alignment + epsilon >= pca_alignment
    strictly_better = (
        orthogonal_area + epsilon < pca_area
        or orthogonal_alignment > pca_alignment + epsilon
    )
    return (
        has_member_support
        and area_not_worse
        and alignment_not_worse
        and strictly_better
    )


def _frame_explainability_metadata(evidence: dict) -> dict:
    """Return string metadata for frame explainability evidence."""
    return {
        "frame-explainability-basis": "pca_vs_nearest_orthogonal_frame",
        "frame-pca-area": str(round(evidence["pca_area"], 4)),
        "frame-orthogonal-area": str(round(evidence["orthogonal_area"], 4)),
        "frame-orthogonal-area-ratio": str(round(evidence["area_ratio"], 4)),
        "frame-pca-member-alignment": str(round(evidence["pca_alignment"], 4)),
        "frame-orthogonal-member-alignment": str(
            round(evidence["orthogonal_alignment"], 4)
        ),
        "frame-member-alignment-ratio": str(round(evidence["alignment_ratio"], 4)),
        "frame-nearest-orthogonal-angle": str(round(evidence["orthogonal_angle"], 4)),
        "frame-snap-candidate": "true" if evidence["snap_candidate"] else "false",
        "axis-explainability-correction": (
            "nearest_orthogonal_frame" if evidence["snap_candidate"] else "none"
        ),
        "axis-original-angle": str(round(evidence["angle"], 4)),
    }


def _frame_area(points: list[tuple[float, float]], angle: float) -> float:
    """Return the projection bbox area for points in one frame."""
    primary_extent, secondary_extent = _frame_extents(points, angle)
    return max(0.0, primary_extent) * max(0.0, secondary_extent)


def _nearest_orthogonal_angle(angle: float) -> float:
    """Return the nearest 0/90-equivalent frame angle."""
    normalized = _orthogonal_frame_angle(angle)
    return 0.0 if normalized <= 45.0 else 90.0


def _member_alignment_for_angle(records: list[dict], angle: float) -> float:
    """Return weighted member-frame agreement with a candidate frame angle."""
    weighted = 0.0
    total_weight = 0.0
    for record in records:
        weight = _record_frame_weight(record)
        if weight <= 0.0:
            continue
        delta = _frame_angle_delta(_record_frame_angle(record), angle)
        # Cosine on a two-axis frame maps 0 and 90 degree agreement to 1.
        weighted += weight * max(0.0, cos(radians(delta * 4.0)))
        total_weight += weight
    return weighted / total_weight if total_weight > 0.0 else 0.0


def _member_frame_consensus(records: list[dict]) -> dict:
    """Average member furniture frames into one organization frame."""
    weighted_x = 0.0
    weighted_y = 0.0
    total_weight = 0.0
    for record in records:
        angle = _record_frame_angle(record)
        weight = _record_frame_weight(record)
        if weight <= 0:
            continue
        # Four-angle averaging treats a 90 degree rotation as the same frame,
        # which matches table groups rotated from horizontal to vertical. This
        # measures member-to-member agreement, not obedience to the PCA axis.
        theta = radians(angle * 4.0)
        weighted_x += weight * cos(theta)
        weighted_y += weight * sin(theta)
        total_weight += weight
    if total_weight <= 0:
        return {"angle": 0.0, "strength": 0.0, "weight": 0.0}
    strength = min(1.0, sqrt(weighted_x * weighted_x + weighted_y * weighted_y) / total_weight)
    angle = _orthogonal_frame_angle(degrees(atan2(weighted_y, weighted_x)) / 4.0)
    return {"angle": angle, "strength": strength, "weight": total_weight}


def _orthogonal_frame_angle(angle: float) -> float:
    """Normalize equivalent two-axis frame angles into the half-open 0-90 range."""
    normalized = angle % 90.0
    # Floating point means an exact 90 degree frame can arrive as 89.999999,
    # but this representation is equivalent to zero for a two-axis frame.
    return 0.0 if normalized >= 89.999 else normalized


def _record_frame_angle(record: dict) -> float:
    """Return the local frame angle for one furniture affordance record."""
    return _record_orientation(record) % 180.0


def _record_frame_weight(record: dict) -> float:
    """Weight member-frame evidence by its own geometric clarity."""
    rect = record["rect"]
    short = max(min(rect.width, rect.height), 1e-9)
    aspect = max(rect.width, rect.height) / short
    return max(0.0, aspect - 1.0)


def _record_points(record: dict) -> list[tuple[float, float]]:
    """Return record polygon points with a rect-corner fallback."""
    points = list(record.get("points") or [])
    return points if points else _rect_points(record["rect"])


def _rect_points(rect: Rect) -> list[tuple[float, float]]:
    """Return closed axis-aligned rectangle corner points."""
    return [
        (rect.left, rect.top),
        (rect.right, rect.top),
        (rect.right, rect.bottom),
        (rect.left, rect.bottom),
        (rect.left, rect.top),
    ]


def _region_shape(
    points: list[tuple[float, float]],
    organization_angle: float,
    scene_size: tuple[float, float],
) -> dict:
    """Choose the visual region shape from affordance geometry complexity."""
    _rect, rectangle = _oriented_envelope(points, organization_angle, scene_size)
    hull = _regularized_hull(points, organization_angle)
    hull_vertex_count = max(0, len(hull) - 1)
    aligned_edge_ratio = _axis_aligned_edge_ratio(hull, organization_angle)
    # Keep rectangles as the preferred representation for simple, axis-readable
    # groups; switch to hull only when the simplified boundary has real complexity.
    use_rectangle = hull_vertex_count <= 7 or (
        hull_vertex_count == 8 and aligned_edge_ratio >= 0.75
    )
    polygon = rectangle if use_rectangle else hull
    shape_frame = _pca_frame_stats(_open_polygon_points(polygon))
    return {
        "basis": "oriented_rectangle" if use_rectangle else "regularized_convex_hull",
        "points": polygon,
        "hull_vertex_count": hull_vertex_count,
        "aligned_edge_ratio": aligned_edge_ratio,
        "rectangle_area": _polygon_area(rectangle),
        "hull_area": _polygon_area(hull),
        "shape_frame": shape_frame,
    }


def _region_shape_metadata(shape: dict, organization_frame: dict) -> dict:
    """Return metadata that separates shape frame diagnostics from trend frame."""
    shape_frame = shape["shape_frame"]
    hull_area = shape["hull_area"]
    area_ratio = shape["rectangle_area"] / hull_area if hull_area > 1e-9 else 0.0
    return {
        "region-shape-basis": shape["basis"],
        "region-shape-vertex-count": str(shape["hull_vertex_count"]),
        "region-shape-aligned-edge-ratio": str(round(shape["aligned_edge_ratio"], 4)),
        "region-shape-area-ratio": str(round(area_ratio, 4)),
        "shape-axis-angle": str(round(shape_frame["angle"], 4)),
        "shape-axis-strength": str(round(shape_frame["strength"], 4)),
        "shape-axis-basis": "region_polygon_pca",
        "shape-secondary-axis-angle": str(round((shape_frame["angle"] + 90.0) % 180.0, 4)),
        "shape-axis-primary-extent": str(round(shape_frame["primary_extent"], 4)),
        "shape-axis-secondary-extent": str(round(shape_frame["secondary_extent"], 4)),
        "frame-delta": str(
            round(_frame_angle_delta(organization_frame["angle"], shape_frame["angle"]), 4)
        ),
    }


def _regularized_hull(
    points: list[tuple[float, float]],
    organization_angle: float,
) -> list[tuple[float, float]]:
    """Return a simplified convex hull for affordance-region visualization."""
    hull = _convex_hull(points)
    hull = _drop_short_edges(hull, min_edge_length=8.0)
    hull = _drop_near_collinear_points(hull, angle_tolerance=15.0)
    return _snap_hull_edges_to_frame(hull, organization_angle, angle_tolerance=5.0)


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Compute a closed convex hull using Andrew's monotonic chain."""
    unique = sorted({(round(x, 10), round(y, 10)) for x, y in points})
    if len(unique) <= 1:
        return unique + unique

    def cross(origin, a, b):
        """Return the signed turn area for three points."""
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (
            a[1] - origin[1]
        ) * (b[0] - origin[0])

    lower = []
    for point in unique:
        # Non-left turns are inside or collinear with the current hull boundary.
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 1e-9:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 1e-9:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    return [*hull, hull[0]] if hull else []


def _drop_short_edges(
    polygon: list[tuple[float, float]],
    min_edge_length: float,
) -> list[tuple[float, float]]:
    """Remove tiny hull edges that come from furniture-corner noise."""
    points = _open_polygon_points(polygon)
    if len(points) <= 4:
        return _close_polygon(points)
    kept = []
    for point in points:
        if not kept or _distance(kept[-1], point) >= min_edge_length:
            kept.append(point)
    if len(kept) > 1 and _distance(kept[0], kept[-1]) < min_edge_length:
        kept.pop()
    return _close_polygon(kept if len(kept) >= 3 else points)


def _drop_near_collinear_points(
    polygon: list[tuple[float, float]],
    angle_tolerance: float,
) -> list[tuple[float, float]]:
    """Remove hull vertices whose adjacent edges form an almost straight line."""
    points = _open_polygon_points(polygon)
    if len(points) <= 4:
        return _close_polygon(points)
    kept = []
    for index, point in enumerate(points):
        prev_point = points[index - 1]
        next_point = points[(index + 1) % len(points)]
        # Collinear cleanup uses raw axis-angle distance; a 90 degree corner is
        # not equivalent to a straight line here.
        turn = _axis_angle_delta(
            _edge_angle(prev_point, point),
            _edge_angle(point, next_point),
        )
        if abs(180.0 - turn) > angle_tolerance:
            kept.append(point)
    return _close_polygon(kept if len(kept) >= 3 else points)


def _snap_hull_edges_to_frame(
    polygon: list[tuple[float, float]],
    organization_angle: float,
    angle_tolerance: float,
) -> list[tuple[float, float]]:
    """Keep hull coordinates stable while recording frame-aligned complexity."""
    # ponytail: no coordinate snapping yet; add it when visual QA shows jagged
    # hulls after the simple vertex cleanup above.
    return polygon


def _axis_aligned_edge_ratio(
    polygon: list[tuple[float, float]],
    organization_angle: float,
) -> float:
    """Return the share of hull edges aligned with the organization frame axes."""
    edges = list(zip(polygon, polygon[1:]))
    if not edges:
        return 0.0
    aligned = 0
    for a, b in edges:
        delta = _frame_angle_delta(_edge_angle(a, b), organization_angle)
        if min(delta, abs(delta - 90.0)) <= 12.0:
            aligned += 1
    return aligned / len(edges)


def _edge_angle(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Return the unsigned axis angle for a polygon edge."""
    return degrees(atan2(b[1] - a[1], b[0] - a[0])) % 180.0


def _frame_angle_delta(a: float, b: float) -> float:
    """Return the smallest difference between two two-axis frame angles."""
    delta = abs((a - b) % 180.0)
    delta = min(delta, 180.0 - delta)
    return min(delta, abs(delta - 90.0))


def _axis_angle_delta(a: float, b: float) -> float:
    """Return the smallest difference between two undirected axis angles."""
    delta = abs((a - b) % 180.0)
    return min(delta, 180.0 - delta)


def _polygon_area(polygon: list[tuple[float, float]]) -> float:
    """Return the absolute shoelace area of a closed or open polygon."""
    points = _close_polygon(_open_polygon_points(polygon))
    if len(points) < 4:
        return 0.0
    area = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _open_polygon_points(
    polygon: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Return polygon points without the repeated closing point."""
    if len(polygon) > 1 and polygon[0] == polygon[-1]:
        return polygon[:-1]
    return list(polygon)


def _close_polygon(
    points: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Return polygon points with a repeated closing point."""
    if not points:
        return []
    return points if points[0] == points[-1] else [*points, points[0]]


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Return Euclidean distance between two points."""
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _oriented_envelope(
    points: list[tuple[float, float]],
    angle: float,
    scene_size: tuple[float, float],
) -> tuple[Rect, list[tuple[float, float]]]:
    """Build an oriented bbox around points in the supplied axis frame."""
    theta = radians(angle)
    c = cos(theta)
    s = sin(theta)
    local = [(x * c + y * s, -x * s + y * c) for x, y in points]
    left = min(x for x, _y in local)
    right = max(x for x, _y in local)
    top = min(y for _x, y in local)
    bottom = max(y for _x, y in local)
    local_corners = [
        (left, top),
        (right, top),
        (right, bottom),
        (left, bottom),
    ]
    polygon_points = [
        (round(x * c - y * s, 10), round(x * s + y * c, 10))
        for x, y in local_corners
    ]
    polygon_points.append(polygon_points[0])
    rect = _bounds([{"rect": _points_rect(polygon_points)}])
    return _clamped_points_rect(polygon_points, scene_size) or rect, polygon_points


def _points_rect(points: list[tuple[float, float]]) -> Rect:
    """Return the axis-aligned bbox for arbitrary points."""
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return Rect(
        cx=(left + right) / 2,
        cy=(top + bottom) / 2,
        width=right - left,
        height=bottom - top,
    )


def _clamped_points_rect(
    points: list[tuple[float, float]],
    scene_size: tuple[float, float],
) -> Rect | None:
    """Return a scene-clamped bbox for points when scene bounds are valid."""
    rect = _points_rect(points)
    clamped = _clamp_rect_to_scene_size(rect, scene_size)
    return clamped if clamped != rect else rect


def _expand_points_bbox(
    points: list[tuple[float, float]],
    target_rect: Rect,
) -> list[tuple[float, float]]:
    """Scale polygon points from their bbox into an expanded target bbox."""
    source = _points_rect(points)
    if source.width <= 1e-9 or source.height <= 1e-9:
        return points
    expanded = []
    for x, y in points:
        rx = (x - source.left) / source.width
        ry = (y - source.top) / source.height
        expanded.append(
            (
                round(target_rect.left + rx * target_rect.width, 10),
                round(target_rect.top + ry * target_rect.height, 10),
            )
        )
    return expanded


def _gap_path_blocked_by_intermediate_region(
    gap_rect: Rect,
    source_regions: tuple[dict, dict],
    regions: list[dict],
) -> bool:
    """Report whether another region intersects the candidate gap band."""
    source_ids = {region["id"] for region in source_regions}
    return any(
        region["id"] not in source_ids and gap_rect.intersects(region["rect"])
        for region in regions
    )


def _inferred_region_gap_path(region_a: dict, region_b: dict, rect: Rect, orientation: str) -> dict:
    """Create a neutral gap-path record between two inferred regions."""
    region_a_key = region_a["region"]
    region_b_key = region_b["region"]
    return {
        "id": f"inferred_gap_path_{region_a_key}__{region_b_key}",
        "region_a": region_a["id"],
        "region_b": region_b["id"],
        "rect": rect,
        "orientation": orientation,
        "thickness": rect.width if orientation == "vertical" else rect.height,
        "overlap_span": rect.height if orientation == "vertical" else rect.width,
        "metadata": {
            "source": "affordance_region_bbox_axis_gap_band_proxy",
            "path_between": "activity_region_candidate",
        },
    }


def _participates_in_region_inference(record: dict) -> bool:
    """Return whether an object should anchor automatic region inference."""
    metadata = record.get("metadata", {})
    anchor = str(metadata.get("region-shape-anchor", "")).strip().lower()
    if anchor in {"1", "true", "yes"}:
        return True
    role = str(record.get("role", metadata.get("role", ""))).strip().lower()
    # Decorative objects remain scene evidence, but they should not enlarge
    # activity regions unless authored as explicit shape anchors.
    return role not in {"plant", "decor", "decoration"}


def _analysis_region_key(record: dict) -> str:
    """Return the semantic key used to group furniture into activity regions."""
    metadata = record.get("metadata", {})
    neutral = {"", "global", "room", "misc", "room_misc", None}
    region = record.get("region") or metadata.get("region")
    if region not in neutral:
        return str(region)
    group = record.get("group") or metadata.get("group")
    # The group fallback is the critical BIM-proxy rule: furniture groups are
    # authored input, while activity regions are inferred analysis entities.
    return "" if group in neutral else str(group)


def _furniture_group_key(record: dict) -> str:
    """Return the authored furniture-group key used for canonical grouping."""
    metadata = record.get("metadata", {})
    neutral = {"", "global", "room", "misc", "room_misc", None}
    key = record.get("furniture_group") or metadata.get("furniture-group")
    # Authored furniture groups are the preferred BIM-style semantic unit; the
    # activity-region key is only the degenerate fallback for older fixtures.
    if key not in neutral:
        return str(key)
    return _analysis_region_key(record)


def _furniture_affordance_extent_record(record: dict) -> dict:
    """Create one maximum extent from a furniture footprint and its own affordances."""
    zones = record_affordance_zones(record)
    rect = _bounds([{"rect": item} for item in [record["rect"], *[zone["rect"] for zone in zones]]])
    return {
        "id": f"furniture_affordance_extent_{record['id']}",
        "object_id": record["id"],
        "region": _analysis_region_key(record),
        "rect": rect,
        "footprint_rect": record["rect"],
        "affordance_zone_ids": sorted(zone["id"] for zone in zones),
        "metadata": {
            "level": "furniture_affordance_extent",
            "source": "object_footprint_plus_affordance_zones",
            "geometry_basis": "object_footprint_plus_own_affordance_zone_rects",
        },
    }


def _required_path_width(scene: dict) -> float | None:
    """Read the manually configured required path width from scene settings."""
    value = scene.get("settings", {}).get("required_path_width")
    if value is None:
        return None
    width = float(value)
    return round(width, 4) if width > 0 else None


def _extent_overlap_evidence(extents: list[dict]) -> list[dict]:
    """Describe pairwise extent overlaps without using them as group extents."""
    return [
        {
            "a": extent_a["id"],
            "b": extent_b["id"],
            "overlap_area": round(_rect_overlap_area(extent_a["rect"], extent_b["rect"]), 4),
        }
        for extent_a, extent_b in combinations(extents, 2)
    ]


def _furniture_group_internal_edges(group: dict) -> list[dict]:
    """Connect member extents that have non-zero relation overlap evidence."""
    return [
        {
            "id": f"internal_relation_{item['a']}__{item['b']}",
            "a": item["a"],
            "b": item["b"],
            "kind": "member_extent_overlap",
            "overlap_area": item["overlap_area"],
        }
        for item in group["overlap_evidence"]
        if item["overlap_area"] > 0
    ]


def _rect_bbox(rect: Rect) -> tuple[float, float, float, float]:
    """Return a stable rounded bbox tuple for evidence records."""
    return (
        round(rect.left, 4),
        round(rect.top, 4),
        round(rect.right, 4),
        round(rect.bottom, 4),
    )


def _affordance_zone_rect(rect: Rect, side: str, depth: float) -> Rect:
    """Build the affordance rectangle extending from one side of a footprint."""
    if side == "left":
        return Rect(cx=rect.left - depth / 2, cy=rect.cy, width=depth, height=rect.height)
    if side == "right":
        return Rect(cx=rect.right + depth / 2, cy=rect.cy, width=depth, height=rect.height)
    if side == "top":
        return Rect(cx=rect.cx, cy=rect.top - depth / 2, width=rect.width, height=depth)
    return Rect(cx=rect.cx, cy=rect.bottom + depth / 2, width=rect.width, height=depth)


def _affordance_margins(record: dict) -> dict[str, float]:
    """Resolve authored affordance depth for each scene side."""
    metadata = record.get("metadata", {})
    margins = {
        "left": _float_metadata(metadata, "affordance-left"),
        "right": _float_metadata(metadata, "affordance-right"),
        "top": _float_metadata(metadata, "affordance-top"),
        "bottom": _float_metadata(metadata, "affordance-bottom"),
    }
    # Explicit front affordance is still authored input; this only maps it from
    # local furniture orientation into scene coordinates.
    front = _float_metadata(metadata, "affordance-front")
    if front > 0:
        side = _profile_edge_side("front", record)
        margins[side] = max(margins[side], front)
    return margins


def _affordance_margin_source(record: dict, side: str) -> str:
    """Name the evidence source used for one side's affordance depth."""
    metadata = record.get("metadata", {})
    if f"affordance-{side}" in metadata:
        return "explicit_affordance_metadata"
    if metadata.get("affordance-front") and _profile_edge_side("front", record) == side:
        return "explicit_affordance_metadata"
    return "none"


def _profile_edge_side(edge: str, record: dict) -> str:
    """Map a profile edge name onto the scene side after object orientation."""
    if edge != "front":
        return edge
    sides = ("bottom", "right", "top", "left")
    index = round(_record_orientation(record) / 90.0) % len(sides)
    return sides[index]


def _record_orientation(record: dict) -> float:
    """Return object orientation in degrees, defaulting invalid values to zero."""
    metadata = record.get("metadata", {})
    try:
        return float(record.get("orientation", metadata.get("orientation", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _record_affordance_type_id(record: dict) -> str:
    """Resolve the profile type id from explicit fields or role defaults."""
    metadata = record.get("metadata", {})
    role = record.get("role")
    role_defaults = {
        "chair": "chair.default",
        "armchair": "armchair.default",
        "podium": "podium.default",
    }
    return (
        record.get("type_id")
        or metadata.get("type_id")
        or metadata.get("type-id")
        or role_defaults.get(role, "")
    )


def _float_metadata(metadata: dict, key: str) -> float:
    """Parse one numeric metadata value with zero as the safe fallback."""
    try:
        return float(metadata.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _rect_iou(a: Rect, b: Rect) -> float:
    """Return intersection-over-union for two rectangles."""
    intersection = _rect_overlap_area(a, b)
    union = a.area + b.area - intersection
    if union <= 1e-9:
        return 0.0
    return intersection / union


def _clamp_rect_to_scene_size(rect: Rect, scene_size: tuple[float, float]) -> Rect:
    """Clamp a rectangle to scene bounds when the scene size is valid."""
    width, height = scene_size
    if width <= 0 or height <= 0:
        return rect
    left = max(0.0, rect.left)
    right = min(width, rect.right)
    top = max(0.0, rect.top)
    bottom = min(height, rect.bottom)
    if right <= left or bottom <= top:
        return rect
    return Rect(
        cx=(left + right) / 2,
        cy=(top + bottom) / 2,
        width=right - left,
        height=bottom - top,
    )


def _bounds(objects: list[dict]):
    """Return the bounding rectangle around object-like records with rect fields."""
    left = min(obj["rect"].left for obj in objects)
    right = max(obj["rect"].right for obj in objects)
    top = min(obj["rect"].top for obj in objects)
    bottom = max(obj["rect"].bottom for obj in objects)
    rect = objects[0]["rect"]
    return type(rect)(
        cx=(left + right) / 2,
        cy=(top + bottom) / 2,
        width=right - left,
        height=bottom - top,
    )


def _rect_overlap_area(a, b) -> float:
    """Return the overlap area shared by two rectangle-like objects."""
    left = max(a.left, b.left)
    right = min(a.right, b.right)
    top = max(a.top, b.top)
    bottom = min(a.bottom, b.bottom)
    if right <= left or bottom <= top:
        return 0.0
    return (right - left) * (bottom - top)


def _components(nodes: dict, adjacency: dict[str, set[str]]) -> list[list[str]]:
    """Return sorted connected components for a simple undirected graph."""
    remaining = set(nodes)
    components = []
    while remaining:
        start = min(remaining)
        stack = [start]
        component = []
        remaining.remove(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(adjacency.get(node, set()), reverse=True):
                if neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                stack.append(neighbor)
        components.append(sorted(component))
    return components

