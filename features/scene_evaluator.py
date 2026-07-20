from __future__ import annotations

import json
from collections import deque
from heapq import heappop, heappush
from html import escape
from itertools import combinations
from math import atan2, cos, degrees, hypot, radians, sin
from pathlib import Path
from statistics import mean, pstdev

from .affordance.grid_backend import SpatialGridBackend
from .affordance.grid_backend import _polygon_rect_overlap_area
from .affordance.models import Polygon, Rect
from .analyzer import OrderAnalyzer
from .column_grid import column_grid_evidence
from .position_grammar import region_position_grammar_evidence
from .room_analysis_model import build_room_analysis_model
from .scene_inference import build_inferred_region_gap_path_graph
from .scene_inference import gap_path_clear_status
from .scene_inference import infer_scene_evidence
from .scene_inference import inferred_region_candidates as infer_region_candidates

ADAPTER_PAYLOAD_CONTRACT = {
    "id": "neutral_adapter_payload",
    "version": 1,
}
ADAPTER_READY_HANDOFFS = [
    "host_relationships",
    "route_topology_handoff",
    "visual_analysis_handoff",
    "material_calibration_handoff",
    "column_grid_handoff",
]


def evaluate_scene(
    scene: dict,
    *,
    position_grammar_enabled: bool = True,
    allow_two_point_inferred_frame: bool = False,
) -> dict:
    """Evaluate a parsed layout scene into stable, notebook-friendly rows."""
    objects = scene["objects"]
    inference = infer_scene_evidence(scene)
    affordance_zones = inference["affordance_zones"]
    furniture_affordance_extents = inference["furniture_affordance_extents"]
    furniture_groups = inference["furniture_groups"]
    region_position_grammar = (
        region_position_grammar_evidence(
            furniture_groups,
            allow_two_point_inferred_frame=allow_two_point_inferred_frame,
        )
        if position_grammar_enabled
        else _disabled_position_grammar()
    )
    inferred_region_candidates = inference["inferred_region_candidates"]
    inferred_regions = inference["inferred_regions"]
    inferred_region_gap_paths = inference["inferred_region_gap_paths"]
    spatial_networks = inference["spatial_networks"]
    boundary_semantics = inference["boundary_semantics"]
    analysis_scene = _analysis_scene(scene, inferred_regions=inferred_regions)
    # Column-grid evidence is derived after inferred regions are attached, so
    # relation rows can compare explicit axes against both authored and inferred regions.
    column_grid = column_grid_evidence(analysis_scene)
    graph = _path_graph(analysis_scene)
    graphs = _modal_path_graphs(analysis_scene, graph)
    path_geometry = _path_geometry(scene)
    sampled_walkable_space = _sampled_walkable_space(analysis_scene)
    negative_space = _negative_space_descriptor(
        scene,
        regions=analysis_scene.get("regions", []),
    )
    negative_space_graph = _negative_space_graph(analysis_scene, negative_space)
    line_of_sight_graph = _line_of_sight_graph(analysis_scene)
    isovist_radial_proxy = _isovist_radial_proxy(analysis_scene)
    rows = []
    rows.extend(_north_table_rows(objects))
    rows.extend(_group_geometry_rows(objects))
    rows.append(_region_alignment_row(analysis_scene))
    rows.append(_region_centroid_phase_row(analysis_scene))
    rows.append(_region_centroid_trend_row(analysis_scene))
    rows.append(_region_boundary_alignment_row(analysis_scene))
    rows.append(_region_source_boundary_alignment_row(analysis_scene))
    rows.append(_region_source_boundary_weighted_alignment_row(analysis_scene))
    rows.append(_region_source_boundary_proximity_row(analysis_scene))
    rows.append(_affordance_use_zone_row(affordance_zones))
    rows.append(_furniture_affordance_extent_row(furniture_affordance_extents))
    rows.extend(_position_grammar_rows(region_position_grammar))
    rows.append(_inferred_region_candidate_row(inferred_region_candidates))
    rows.append(_inferred_region_row(inferred_regions))
    rows.append(_inferred_region_explicit_iou_row(scene, inferred_region_candidates))
    rows.append(_inferred_region_gap_path_row(inferred_region_gap_paths))
    gap_path_occupancy_row = _inferred_region_gap_path_occupancy_row(
        scene,
        affordance_zones,
        inferred_region_gap_paths,
    )
    rows.append(gap_path_occupancy_row)
    gap_path_free_space_overlap_row = _inferred_region_gap_path_free_space_overlap_row(
        inferred_region_gap_paths,
        negative_space,
    )
    rows.append(gap_path_free_space_overlap_row)
    gap_path_cad_free_space_overlap_row = (
        _inferred_region_gap_path_cad_free_space_overlap_row(
            inferred_region_gap_paths,
            negative_space,
        )
    )
    inferred_region_gap_path_graph = build_inferred_region_gap_path_graph(
        inferred_region_candidates,
        inferred_region_gap_paths,
        sampled_walkable_space,
        gap_path_occupancy_row.get(
            "inferred_region_gap_path_occupancy_evidence",
            [],
        ),
        gap_path_free_space_overlap_row.get(
            "inferred_region_gap_path_free_space_overlap_evidence",
            [],
        ),
        gap_path_cad_free_space_overlap_row.get(
            "inferred_region_gap_path_cad_free_space_overlap_evidence",
            [],
        ),
        scene=scene,
    )
    rows.append(_inferred_region_gap_path_walkable_proxy_row(inferred_region_gap_path_graph))
    rows.append(_inferred_region_gap_path_min_width_row(inferred_region_gap_path_graph))
    rows.append(gap_path_cad_free_space_overlap_row)
    rows.append(_inferred_region_gap_path_explicit_path_iou_row(scene, inferred_region_gap_paths))
    rows.extend(_object_region_membership_rows(analysis_scene))
    rows.extend(_column_alignment_rows(analysis_scene))
    rows.extend(_column_grid_relation_rows(column_grid))
    rows.extend(_whole_space_force_rows(scene))
    rows.extend(
        _path_connectivity_rows(
            analysis_scene,
            graph,
            graphs,
            path_geometry,
            sampled_walkable_space,
            negative_space,
            negative_space_graph,
            line_of_sight_graph,
            isovist_radial_proxy,
        )
    )
    rows.append(_inferred_gap_path_width_free_space_clearance_row(rows, negative_space))
    rows.append(_boundary_connectivity_row(scene))
    rows.extend(_boundary_metrics_rows(scene, graph))
    rows.append(_adapter_reference_row(scene))
    rows.append(_uncertainty_row(scene))
    rows.append(_uncertainty_route_row(rows))
    rows.append(_matrix_completion_audit_row())
    score_matrix = _score_matrix(rows)
    adapter_scene = _adapter_scene(scene, inferred_regions=inferred_regions)
    matrix = {
        "source": scene["source"],
        "rows": rows,
        "score_matrix": score_matrix,
        "affordance_zones": affordance_zones,
        "furniture_affordance_extents": furniture_affordance_extents,
        "furniture_groups": furniture_groups,
        "region_position_grammar": region_position_grammar,
        "inferred_region_candidates": inferred_region_candidates,
        "inferred_regions": inferred_regions,
        "inferred_region_gap_paths": inferred_region_gap_paths,
        "spatial_networks": spatial_networks,
        "boundary_semantics": boundary_semantics,
        "column_grid": column_grid,
        "inferred_region_gap_path_graph": inferred_region_gap_path_graph,
        "adapter_payload": _adapter_payload(
            adapter_scene,
            rows,
            graphs,
            negative_space,
            negative_space_graph,
            line_of_sight_graph,
            isovist_radial_proxy,
            affordance_zones,
            furniture_affordance_extents,
            furniture_groups,
            region_position_grammar,
            inferred_region_candidates,
            inferred_region_gap_paths,
            spatial_networks,
            boundary_semantics,
            inferred_region_gap_path_graph,
            score_matrix,
        ),
        "graph": graph,
        "graphs": graphs,
        "path_geometry": path_geometry,
        "sampled_walkable_space": sampled_walkable_space,
        "negative_space": negative_space,
        "negative_space_graph": negative_space_graph,
        "line_of_sight_graph": line_of_sight_graph,
        "isovist_radial_proxy": isovist_radial_proxy,
    }
    matrix["room_analysis_model"] = build_room_analysis_model(adapter_scene, matrix)
    return matrix


def export_adapter_payload_json(scene: dict, target: str | Path) -> dict:
    """Write the neutral adapter payload as JSON and return it."""
    payload = evaluate_scene(scene)["adapter_payload"]
    Path(target).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return payload


def validate_adapter_payload_json(target: str | Path) -> dict:
    """Summarize whether an exported adapter payload has the handoff keys."""
    payload = json.loads(Path(target).read_text(encoding="utf-8"))
    required = [
        "handoff_contract",
        "scene_records",
        "external_refs",
        "grasshopper_branches",
        "metric_rows",
        "score_matrix",
        "evidence_geometry",
        "adapter_capability_matrix",
        "notebook_audit_manifest",
    ]
    missing = [key for key in required if key not in payload]
    handoff_contract = payload.get("handoff_contract", {})
    scene_records = payload.get("scene_records", [])
    external_refs = payload.get("external_refs", {})
    grasshopper_branches = payload.get("grasshopper_branches", [])
    ready_handoffs = payload.get("adapter_capability_matrix", {}).get(
        "ready_handoffs", []
    )
    notebook_status = payload.get("notebook_audit_manifest", {}).get("status")
    contract_errors = []
    if "handoff_contract" in missing:
        contract_errors.append("handoff_contract is missing")
    elif handoff_contract != ADAPTER_PAYLOAD_CONTRACT:
        contract_errors.append("handoff_contract is not neutral_adapter_payload version 1")
    if not ready_handoffs:
        contract_errors.append("adapter_capability_matrix.ready_handoffs is empty")
    elif handoff_contract == ADAPTER_PAYLOAD_CONTRACT:
        missing_handoffs = [
            handoff for handoff in ADAPTER_READY_HANDOFFS if handoff not in ready_handoffs
        ]
        if missing_handoffs:
            contract_errors.append(
                "adapter_capability_matrix.ready_handoffs missing: "
                + ", ".join(sorted(missing_handoffs))
            )
    if notebook_status != "ordered_clean_overlay":
        contract_errors.append(
            "notebook_audit_manifest.status is not ordered_clean_overlay"
        )
    if "grasshopper_branches" not in missing and isinstance(
        grasshopper_branches,
        list,
    ):
        branch_paths = [
            branch.get("path")
            for branch in grasshopper_branches
            if isinstance(branch, dict)
        ]
        branch_groups = {
            "records": any(
                isinstance(path, str)
                and path.startswith(
                    (
                        "{0;objects;",
                        "{0;boundaries;",
                        "{0;entries;",
                        "{0;paths;",
                        "{0;regions;",
                        "{0;column_grid;",
                    )
                )
                for path in branch_paths
            ),
            "metrics": any(
                isinstance(path, str) and path.startswith("{0;metrics;")
                for path in branch_paths
            ),
            "graphs": any(
                isinstance(path, str) and path.startswith("{0;graphs;")
                for path in branch_paths
            ),
        }
        missing_branch_groups = sorted(
            group for group, present in branch_groups.items() if not present
        )
        if missing_branch_groups:
            contract_errors.append(
                "grasshopper_branches missing branch groups: "
                + ", ".join(missing_branch_groups)
            )
    if isinstance(scene_records, list) and payload.get("record_count", 0) != len(
        scene_records
    ):
        contract_errors.append("record_count does not match scene_records length")
    if isinstance(scene_records, list):
        record_ids = [
            record.get("id") for record in scene_records if isinstance(record, dict)
        ]
        duplicate_ids = sorted(
            {
                record_id
                for record_id in record_ids
                if record_id is not None and record_ids.count(record_id) > 1
            }
        )
        if duplicate_ids:
            contract_errors.append(
                "scene_records duplicate ids: " + ", ".join(duplicate_ids)
            )
        if isinstance(external_refs, dict):
            record_id_set = {record_id for record_id in record_ids if record_id}
            records_by_id = {
                record.get("id"): record
                for record in scene_records
                if isinstance(record, dict) and record.get("id")
            }
            ref_target_ids = []
            stale_reverse_refs = []
            for refs_by_value in external_refs.values():
                if not isinstance(refs_by_value, dict):
                    continue
                for target in refs_by_value.values():
                    if isinstance(target, list):
                        ref_target_ids.extend(target)
                    else:
                        ref_target_ids.append(target)
            missing_ref_targets = sorted(
                {
                    target
                    for target in ref_target_ids
                    if target not in record_id_set
                }
            )
            if missing_ref_targets:
                contract_errors.append(
                    "external_refs target ids missing: "
                    + ", ".join(missing_ref_targets)
                )
            for ref_key, refs_by_value in external_refs.items():
                if not isinstance(refs_by_value, dict):
                    continue
                for ref_value, target in refs_by_value.items():
                    targets = target if isinstance(target, list) else [target]
                    for target_id in targets:
                        if target_id not in records_by_id:
                            continue
                        record = records_by_id.get(target_id, {})
                        adapter_refs = record.get("adapter_refs", {})
                        if (
                            isinstance(adapter_refs, dict)
                            and adapter_refs.get(ref_key) != ref_value
                        ):
                            stale_reverse_refs.append(
                                f"{ref_key}:{ref_value}->{target_id}"
                            )
            if stale_reverse_refs:
                contract_errors.append(
                    "external_refs stale reverse refs: "
                    + ", ".join(sorted(stale_reverse_refs))
                )
            missing_reverse_refs = []
            for record in scene_records:
                if not isinstance(record, dict):
                    continue
                record_id = record.get("id")
                adapter_refs = record.get("adapter_refs", {})
                if not isinstance(adapter_refs, dict):
                    continue
                for ref_key, ref_value in adapter_refs.items():
                    reverse_target = external_refs.get(ref_key, {}).get(ref_value)
                    targets = (
                        reverse_target
                        if isinstance(reverse_target, list)
                        else [reverse_target]
                    )
                    if record_id not in targets:
                        missing_reverse_refs.append(
                            f"{ref_key}:{ref_value}->{record_id}"
                        )
            if missing_reverse_refs:
                contract_errors.append(
                    "external_refs missing reverse refs: "
                    + ", ".join(sorted(missing_reverse_refs))
                )
    result = {
        "valid": not missing and not contract_errors,
        "missing_keys": missing,
        "contract_id": handoff_contract.get("id"),
        "contract_version": handoff_contract.get("version"),
        "record_count": payload.get("record_count", 0),
        "ready_handoff_count": len(ready_handoffs),
        "notebook_status": notebook_status,
    }
    if contract_errors:
        result["contract_errors"] = contract_errors
    return result


def _analysis_scene(scene: dict, *, inferred_regions: list[dict] | None = None) -> dict:
    filtered = dict(scene)
    inferred_regions = list(inferred_regions or [])
    filtered["regions"] = [
        region
        for region in scene.get("regions", []) + inferred_regions
        if region.get("metadata", {}).get("analysis-region") != "false"
    ]
    return filtered


def _adapter_scene(scene: dict, *, inferred_regions: list[dict] | None = None) -> dict:
    exported = dict(scene)
    exported["regions"] = scene.get("regions", []) + list(inferred_regions or [])
    return exported


def _rect_iou(a: Rect, b: Rect) -> float:
    intersection = _rect_overlap_area(a, b)
    union = a.area + b.area - intersection
    if union <= 1e-9:
        return 0.0
    return intersection / union


def scene_metric_overlay_svg(
    scene: dict,
    matrix: dict,
    *,
    include_free_space_paths: bool = False,
) -> str:
    """Draw parsed source ids and evaluated metric evidence."""
    analysis_scene = _analysis_scene(scene)
    labels = []
    boxes = []
    graph_layers = []
    negative_space_layers = []
    column_layers = []
    region_layers = []
    boundary_layers = []
    region_boundary_layers = []
    object_region_layers = []
    missing_region_layers = []
    conflict_layers = []
    visibility_layers = []
    for obj in scene["objects"]:
        rect = obj["rect"]
        labels.append(
            f'<text x="{rect.cx:.1f}" y="{rect.cy:.1f}" font-size="12" '
            f'text-anchor="middle" fill="#111">{obj["id"]}</text>'
        )

    for group in sorted({obj["group"] for obj in scene["objects"]}):
        members = [obj for obj in scene["objects"] if obj["group"] == group]
        if not members:
            continue
        left = min(obj["rect"].left for obj in members)
        right = max(obj["rect"].right for obj in members)
        top = min(obj["rect"].top for obj in members)
        bottom = max(obj["rect"].bottom for obj in members)
        boxes.append(
            f'<rect data-layer="metric-evidence" data-group="{group}" '
            f'x="{left:.1f}" y="{top:.1f}" width="{right-left:.1f}" '
            f'height="{bottom-top:.1f}" fill="none" stroke="#d62728" '
            f'stroke-width="2" stroke-dasharray="8 6" />'
        )
        boxes.append(
            f'<text x="{left:.1f}" y="{top-6:.1f}" font-size="16" '
            f'fill="#d62728">{group}</text>'
        )

    graph = matrix.get("graph", {})
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    for edge in graph.get("edges", []):
        a = nodes.get(edge["a"])
        b = nodes.get(edge["b"])
        if not a or not b:
            continue
        ax, ay = a["point"]
        bx, by = b["point"]
        graph_layers.append(
            f'<line data-layer="path-graph-edge" data-edge="{escape(edge["id"])}" '
            f'data-kind="{escape(edge["kind"])}" x1="{ax:.1f}" y1="{ay:.1f}" '
            f'x2="{bx:.1f}" y2="{by:.1f}" stroke="#6a3d9a" '
            f'stroke-width="3" stroke-dasharray="5 5" opacity="0.65">'
            f'<title>{escape(edge["id"])}</title></line>'
        )
    for node in graph.get("nodes", []):
        x, y = node["point"]
        graph_layers.append(
            f'<circle data-layer="path-graph-node" data-node="{escape(node["id"])}" '
            f'data-kind="{escape(node["kind"])}" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="7" fill="#6a3d9a" opacity="0.78">'
            f'<title>{escape(node["ref_id"])}</title></circle>'
        )

    negative_space_graph = matrix.get("negative_space_graph", {})
    negative_space_nodes = {
        node["id"]: node for node in negative_space_graph.get("nodes", [])
    }
    for node in negative_space_graph.get("nodes", []):
        if node["kind"] != "negative_space_component":
            continue
        bbox = node.get("bbox")
        if not bbox:
            continue
        left, top, right, bottom = bbox
        if right <= left or bottom <= top:
            continue
        cell_count = node.get("cell_count")
        cell_count_attr = (
            f' data-cell-count="{cell_count}"'
            if cell_count is not None
            else ""
        )
        area = node.get("area")
        area_attr = f' data-area="{area:.1f}"' if isinstance(area, (int, float)) else ""
        negative_space_layers.append(
            f'<rect data-layer="negative-space-component" '
            f'data-node="{escape(node["id"])}" '
            f'data-component="{node["component_index"]}"{cell_count_attr}{area_attr} '
            f'data-bbox-left="{left:.1f}" data-bbox-top="{top:.1f}" '
            f'data-bbox-right="{right:.1f}" data-bbox-bottom="{bottom:.1f}" '
            f'x="{left:.1f}" y="{top:.1f}" width="{right-left:.1f}" '
            f'height="{bottom-top:.1f}" fill="#14b8a6" stroke="#0f766e" '
            f'stroke-width="2" opacity="0.16">'
            f'<title>{escape(node["ref_id"])} component bbox</title></rect>'
        )
    for edge in negative_space_graph.get("edges", []):
        a = negative_space_nodes.get(edge["a"])
        b = negative_space_nodes.get(edge["b"])
        if not a or not b:
            continue
        ax, ay = a["point"]
        bx, by = b["point"]
        overlap = edge.get("overlap_area")
        overlap_attr = (
            f' data-overlap-area="{overlap:.1f}"'
            if isinstance(overlap, (int, float))
            else ""
        )
        negative_space_layers.append(
            f'<line data-layer="negative-space-graph-edge" '
            f'data-edge="{escape(edge["id"])}" '
            f'data-kind="{escape(edge["kind"])}"{overlap_attr} '
            f'x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            f'stroke="#0f766e" stroke-width="2.5" stroke-dasharray="7 4" '
            f'opacity="0.62"><title>{escape(edge["id"])}</title></line>'
        )
    for node in negative_space_graph.get("nodes", []):
        x, y = node["point"]
        radius = 8 if node["kind"] == "negative_space_component" else 5
        negative_space_layers.append(
            f'<circle data-layer="negative-space-graph-node" '
            f'data-node="{escape(node["id"])}" '
            f'data-kind="{escape(node["kind"])}" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{radius}" fill="#0f766e" opacity="0.74">'
            f'<title>{escape(node["ref_id"])}</title></circle>'
        )

    free_space_graph = matrix.get("negative_space", {}).get(
        "free_space_polygon_graph",
        {},
    )
    free_space_nodes = {
        node["id"]: node for node in free_space_graph.get("nodes", [])
    }
    if include_free_space_paths:
        for item in free_space_graph.get("entry_region_distance_evidence", []):
            path_cell_ids = item.get("path_cell_ids", [])
            for index, (from_cell_id, to_cell_id) in enumerate(
                zip(path_cell_ids, path_cell_ids[1:])
            ):
                from_node = free_space_nodes.get(from_cell_id)
                to_node = free_space_nodes.get(to_cell_id)
                if not from_node or not to_node:
                    continue
                ax, ay = from_node["point"]
                bx, by = to_node["point"]
                negative_space_layers.append(
                    f'<line data-layer="free-space-graph-entry-region-path" '
                    f'data-entry="{escape(item["entry_id"])}" '
                    f'data-region="{escape(item["region_id"])}" '
                    f'data-component="{item["component_index"]}" '
                    f'data-segment-index="{index}" '
                    f'data-from-cell="{escape(from_cell_id)}" '
                    f'data-to-cell="{escape(to_cell_id)}" '
                    f'x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                    f'stroke="#f59e0b" stroke-width="2.4" opacity="0.7">'
                    f'<title>{escape(item["entry_id"])} to '
                    f'{escape(item["region_id"])}</title></line>'
                )
    for anchor in free_space_graph.get("anchors", {}).get("entries", []):
        for cell_id in anchor.get("cell_ids", []):
            node = free_space_nodes.get(cell_id)
            if not node:
                continue
            x, y = node["point"]
            negative_space_layers.append(
                f'<circle data-layer="free-space-graph-entry-anchor" '
                f'data-entry="{escape(anchor["entry_id"])}" '
                f'data-component="{anchor["component_index"]}" '
                f'data-cell="{escape(cell_id)}" cx="{x:.1f}" cy="{y:.1f}" '
                f'r="4.5" fill="#f97316" opacity="0.82">'
                f'<title>{escape(anchor["entry_id"])} {escape(cell_id)}</title>'
                f'</circle>'
            )
    for anchor in free_space_graph.get("anchors", {}).get("regions", []):
        for cell_id in anchor.get("cell_ids", []):
            node = free_space_nodes.get(cell_id)
            if not node:
                continue
            x, y = node["point"]
            negative_space_layers.append(
                f'<circle data-layer="free-space-graph-region-anchor" '
                f'data-region="{escape(anchor["region_id"])}" '
                f'data-component="{anchor["component_index"]}" '
                f'data-cell="{escape(cell_id)}" cx="{x:.1f}" cy="{y:.1f}" '
                f'r="4.5" fill="#84cc16" opacity="0.82">'
                f'<title>{escape(anchor["region_id"])} {escape(cell_id)}</title>'
                f'</circle>'
            )

    for column in scene.get("columns", []):
        rect = column["rect"]
        # Physical columns are source evidence, separate from authored grid axes.
        column_layers.append(
            f'<rect data-layer="column-physical" data-column="{escape(column["id"])}" '
            f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
            f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
            f'fill="#1d4ed8" stroke="#172554" stroke-width="1.8" '
            f'opacity="0.58"><title>{escape(column["id"])}</title></rect>'
        )

    for column in scene.get("column_axes", []):
        points = column.get("points") or []
        if len(points) >= 2:
            x1, y1 = points[0]
            x2, y2 = points[-1]
        else:
            rect = column["rect"]
            x1, y1 = rect.left, rect.top
            x2, y2 = rect.right, rect.bottom
        column_layers.append(
            f'<line data-layer="column-axis" data-axis="{escape(column["id"])}" '
            f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#2563eb" stroke-width="2.5" opacity="0.72">'
            f'<title>{escape(column["id"])}</title></line>'
        )
    column_grid = matrix.get("column_grid", {})
    column_grid_bays = column_grid.get("bays", [])
    bay_scores = {}
    for row in matrix.get("rows", []):
        if row.get("metric") != "region_column_bay_fit":
            continue
        for item in row.get("region_bay_fit_evidence", []):
            score = item.get("score")
            if isinstance(score, (int, float)):
                bay_scores.setdefault(item["bay_id"], []).append(score)
    # Keep overlay bays aligned with evaluated matrix evidence; fall back only
    # for callers that predate the column_grid matrix payload.
    for bay in (
        column_grid_bays
        if "column_grid" in matrix
        else _column_axis_bays(scene.get("column_axes", []))
    ):
        scores = bay_scores.get(bay["id"], [])
        score_attr = (
            f' data-score-max="{max(scores):.4f}" data-score-count="{len(scores)}"'
            if scores
            else ""
        )
        polygon = bay.get("polygon")
        if polygon is not None:
            points = " ".join(f"{x:.1f},{y:.1f}" for x, y in polygon.points)
            column_layers.append(
                f'<polygon data-layer="column-bay" data-bay="{escape(bay["id"])}"'
                f'{score_attr} points="{points}" fill="#93c5fd" '
                f'stroke="#2563eb" stroke-width="2" opacity="0.22">'
                f'<title>{escape(bay["id"])}</title></polygon>'
            )
        else:
            rect = bay["rect"]
            column_layers.append(
                f'<rect data-layer="column-bay" data-bay="{escape(bay["id"])}"'
                f'{score_attr} x="{rect.left:.1f}" y="{rect.top:.1f}" '
                f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
                f'fill="#93c5fd" stroke="#2563eb" stroke-width="2" '
                f'opacity="0.22"><title>{escape(bay["id"])}</title></rect>'
            )

    column_grid_bays_by_id = {bay["id"]: bay for bay in column_grid_bays}
    regions_by_id = {
        region["id"]: region
        for region in analysis_scene.get("regions", []) + matrix.get("inferred_regions", [])
    }
    for relation in column_grid.get("global_relations", []):
        region = regions_by_id.get(relation.get("region_id"))
        if not region:
            continue
        x1, y1, x2, y2 = _axis_line(region["rect"], relation["target_angle"])
        column_layers.append(
            f'<line data-layer="column-global-frame" '
            f'data-region="{escape(relation["region_id"])}" '
            f'data-target-kind="{escape(relation["target_kind"])}" '
            f'data-target="{escape(relation["target_id"])}" '
            f'data-agreement="{relation["agreement"]:.4f}" '
            f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#7c3aed" stroke-width="2.4" opacity="0.72">'
            f'<title>{escape(relation["region_id"])} to '
            f'{escape(relation["target_id"])}</title></line>'
        )
    for profile in column_grid.get("local_profiles", []):
        if profile.get("scale") != 0 or not profile.get("seed_bay_ids"):
            continue
        region = regions_by_id.get(profile.get("region_id"))
        if not region:
            continue
        # Scale-zero profiles identify the seed bay context; larger scales are
        # omitted here to keep the overlay tied to direct relation evidence.
        for bay_id in profile["seed_bay_ids"]:
            bay = column_grid_bays_by_id.get(bay_id)
            if not bay:
                continue
            polygon = bay.get("polygon")
            if polygon is not None:
                points = " ".join(f"{x:.1f},{y:.1f}" for x, y in polygon.points)
                column_layers.append(
                    f'<polygon data-layer="column-seed-bay" '
                    f'data-region="{escape(profile["region_id"])}" '
                    f'data-bay="{escape(bay_id)}" points="{points}" '
                    f'fill="#facc15" stroke="#ca8a04" stroke-width="2.4" '
                    f'opacity="0.28"><title>{escape(bay_id)}</title></polygon>'
                )
            else:
                rect = bay["rect"]
                column_layers.append(
                    f'<rect data-layer="column-seed-bay" '
                    f'data-region="{escape(profile["region_id"])}" '
                    f'data-bay="{escape(bay_id)}" x="{rect.left:.1f}" '
                    f'y="{rect.top:.1f}" width="{rect.width:.1f}" '
                    f'height="{rect.height:.1f}" fill="#facc15" '
                    f'stroke="#ca8a04" stroke-width="2.4" opacity="0.28">'
                    f'<title>{escape(bay_id)}</title></rect>'
                )
        rect = region["rect"]
        column_layers.append(
            f'<circle data-layer="column-local-profile" '
            f'data-region="{escape(profile["region_id"])}" '
            f'data-system="{escape(profile["system_id"])}" '
            f'data-branch="{escape(profile["branch_id"])}" '
            f'data-scale="0" data-frame-agreement="{profile["frame_agreement"]:.4f}" '
            f'cx="{rect.cx:.1f}" cy="{rect.cy:.1f}" r="6" '
            f'fill="#ca8a04" opacity="0.82">'
            f'<title>{escape(profile["region_id"])}</title></circle>'
        )

    for region in analysis_scene.get("regions", []):
        rect = region["rect"]
        if rect.width <= 0 or rect.height <= 0:
            continue
        axis = _record_axis_descriptor(region)
        x1, y1, x2, y2 = _axis_line(rect, axis["angle"])
        region_layers.append(
            f'<line data-layer="region-axis" data-region="{escape(region["id"])}" '
            f'data-basis="{escape(axis["basis"])}" data-angle="{axis["angle"]:.4f}" '
            f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#f97316" stroke-width="2.5" opacity="0.74">'
            f'<title>{escape(region["id"])} {axis["angle"]:.4f}</title></line>'
        )
    for zone in matrix.get("affordance_zones", []):
        rect = zone["rect"]
        region_layers.append(
            f'<rect data-layer="affordance-use-zone" '
            f'data-affordance-zone="{escape(zone["id"])}" '
            f'data-object="{escape(zone["object_id"])}" '
            f'data-region="{escape(zone["region"])}" '
            f'data-side="{escape(zone["side"])}" '
            f'data-depth="{zone["depth"]:.4f}" '
            f'data-source="{escape(zone["source"])}" '
            f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
            f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
            f'fill="#22c55e" opacity="0.12" stroke="#16a34a" '
            f'stroke-width="1.8" stroke-dasharray="5 4">'
            f'<title>{escape(zone["id"])}</title></rect>'
        )
    for extent in matrix.get("furniture_affordance_extents", []):
        rect = extent["rect"]
        region_layers.append(
            f'<rect data-layer="furniture-affordance-extent" '
            f'data-extent="{escape(extent["id"])}" '
            f'data-object="{escape(extent["object_id"])}" '
            f'data-region="{escape(extent["region"])}" '
            f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
            f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
            f'fill="none" stroke="#059669" stroke-width="2.0" '
            f'stroke-dasharray="2 4" opacity="0.72">'
            f'<title>{escape(extent["id"])}</title></rect>'
        )
    for item in _position_grammar_items(matrix):
        for residual in item.get("residuals", []):
            # Slots and residuals are diagnostic evidence for the selected
            # grammar; in the public matrix they show how far each furniture
            # group sits from its inferred or authored local position.
            region_layers.append(
                f'<circle data-layer="position-grammar-slot" '
                f'data-system="{escape(item["position-system-id"])}" '
                f'data-member="{escape(residual["id"])}" '
                f'cx="{residual["slot_x"]:.1f}" cy="{residual["slot_y"]:.1f}" r="4" '
                f'fill="#f59e0b" opacity="0.75">'
                f'<title>{escape(item["position-grammar-type"])} '
                f'{residual["normalized"]:.4f}</title></circle>'
            )
            region_layers.append(
                f'<line data-layer="position-grammar-residual" '
                f'data-system="{escape(item["position-system-id"])}" '
                f'data-member="{escape(residual["id"])}" '
                f'x1="{residual["x"]:.1f}" y1="{residual["y"]:.1f}" '
                f'x2="{residual["slot_x"]:.1f}" y2="{residual["slot_y"]:.1f}" '
                f'stroke="#f59e0b" stroke-width="2" opacity="0.7" />'
            )
    inferred_region_ids = {
        region["id"] for region in matrix.get("inferred_regions", [])
    }
    for region in matrix.get("inferred_region_candidates", []):
        if region["id"] in inferred_region_ids:
            continue
        rect = region["rect"]
        region_layers.append(
            f'<rect data-layer="inferred-region-candidate" '
            f'data-candidate="{escape(region["id"])}" '
            f'data-region="{escape(region["region"])}" '
            f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
            f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
            f'fill="none" stroke="#a855f7" stroke-width="2.2" '
            f'stroke-dasharray="10 6" opacity="0.82">'
            f'<title>{escape(region["id"])}</title></rect>'
        )
    for region in matrix.get("inferred_regions", []):
        rect = region["rect"]
        region_layers.append(
            f'<rect data-layer="inferred-region" '
            f'data-region="{escape(region["region"])}" '
            f'data-source="{escape(region["metadata"]["source"])}" '
            f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
            f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
            f'fill="#38bdf8" opacity="0.08" stroke="#0284c7" '
            f'stroke-width="2.4" stroke-dasharray="8 5">'
            f'<title>{escape(region["id"])}</title></rect>'
        )
    occupancy_by_gap_path = {
        item["gap_path_id"]: item
        for row in matrix.get("rows", [])
        if row.get("metric") == "inferred_region_gap_path_occupancy_ratio"
        for item in row.get("inferred_region_gap_path_occupancy_evidence", [])
    }
    for path in matrix.get("inferred_region_gap_paths", []):
        rect = path["rect"]
        occupancy = occupancy_by_gap_path.get(path["id"], {})
        occupancy_ratio = occupancy.get("occupancy_ratio", 0.0)
        occupied = bool(occupancy.get("occupiers"))
        clear_status = gap_path_clear_status(occupancy_ratio)
        region_layers.append(
            f'<rect data-layer="inferred-gap-path" '
            f'data-gap-path="{escape(path["id"])}" '
            f'data-region-a="{escape(path["region_a"])}" '
            f'data-region-b="{escape(path["region_b"])}" '
            f'data-orientation="{escape(path["orientation"])}" '
            f'data-thickness="{path["thickness"]:.4f}" '
            f'data-occupied="{str(occupied).lower()}" '
            f'data-occupancy-ratio="{occupancy_ratio:.4f}" '
            f'data-clear-status="{clear_status}" '
            f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
            f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
            f'fill="#a78bfa" opacity="0.14" stroke="#7c3aed" '
            f'stroke-width="2.2">'
            f'<title>{escape(path["id"])}</title></rect>'
        )
    gap_rects_by_id = {
        path["id"]: path["rect"]
        for path in matrix.get("inferred_region_gap_paths", [])
    }
    affordance_zone_rects = {
        zone["id"]: zone["rect"]
        for zone in matrix.get("affordance_zones", [])
    }
    object_rects = {
        obj["id"]: obj["rect"]
        for obj in scene.get("objects", [])
    }
    for row in matrix.get("rows", []):
        if row.get("metric") != "inferred_region_gap_path_occupancy_ratio":
            continue
        for item in row.get("inferred_region_gap_path_occupancy_evidence", []):
            gap_rect = gap_rects_by_id.get(item["gap_path_id"])
            if not gap_rect:
                continue
            for occupier in item.get("occupiers", []):
                occupier_rect = (
                    affordance_zone_rects.get(occupier["id"])
                    if occupier.get("kind") == "affordance_zone"
                    else object_rects.get(occupier["id"])
                )
                if not occupier_rect:
                    continue
                region_layers.append(
                    f'<line data-layer="inferred-gap-path-occupancy" '
                    f'data-gap-path="{escape(item["gap_path_id"])}" '
                    f'data-occupier="{escape(occupier["id"])}" '
                    f'data-kind="{escape(occupier["kind"])}" '
                    f'data-overlap-area="{occupier["overlap_area"]:.4f}" '
                    f'data-occupancy-ratio="{item["occupancy_ratio"]:.4f}" '
                    f'x1="{gap_rect.cx:.1f}" y1="{gap_rect.cy:.1f}" '
                    f'x2="{occupier_rect.cx:.1f}" y2="{occupier_rect.cy:.1f}" '
                    f'stroke="#dc2626" stroke-width="2.2" stroke-dasharray="3 4" '
                    f'opacity="0.68"><title>{escape(item["gap_path_id"])} occupied by '
                    f'{escape(occupier["id"])}</title></line>'
                )

    for boundary in scene.get("boundaries", []):
        rect = boundary["rect"]
        if rect.width <= 0 and rect.height <= 0:
            continue
        axis = _record_axis_descriptor(boundary)
        weights = boundary.get("weights", {})
        x1, y1, x2, y2 = _axis_line(rect, axis["angle"])
        boundary_layers.append(
            f'<line data-layer="boundary-axis" '
            f'data-boundary="{escape(boundary["id"])}" '
            f'data-kind="{escape(boundary.get("metadata", {}).get("boundary-kind", boundary["role"]))}" '
            f'data-basis="{escape(axis["basis"])}" data-angle="{axis["angle"]:.4f}" '
            f'data-walk-block="{weights.get("walk_block", 0.0):.4f}" '
            f'data-see-block="{weights.get("see_block", 0.0):.4f}" '
            f'data-grouping-strength="{weights.get("grouping_strength", 0.0):.4f}" '
            f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#16a34a" stroke-width="2.25" opacity="0.68">'
            f'<title>{escape(boundary["id"])} {axis["angle"]:.4f}</title></line>'
        )

    records_by_id = {
        record["id"]: record
        for key in ("regions", "boundaries")
        for record in scene.get(key, [])
    }
    for row in matrix.get("rows", []):
        if row.get("metric") != "region_source_boundary_proximity":
            continue
        for item in row.get("region_boundary_proximity", []):
            region = records_by_id.get(item["region_id"])
            if not region:
                continue
            region_rect = region["rect"]
            for boundary_score in item.get("boundary_scores", []):
                boundary = records_by_id.get(boundary_score["boundary_id"])
                if not boundary:
                    continue
                boundary_rect = boundary["rect"]
                region_boundary_layers.append(
                    f'<line data-layer="region-boundary-cue" '
                    f'data-region="{escape(region["id"])}" '
                    f'data-boundary="{escape(boundary["id"])}" '
                    f'data-gap="{boundary_score["gap"]:.4f}" '
                    f'data-proximity="{boundary_score["proximity"]:.4f}" '
                    f'x1="{region_rect.cx:.1f}" y1="{region_rect.cy:.1f}" '
                    f'x2="{boundary_rect.cx:.1f}" y2="{boundary_rect.cy:.1f}" '
                    f'stroke="#ea580c" stroke-width="2" stroke-dasharray="4 5" '
                    f'opacity="0.64"><title>{escape(region["id"])} to '
                    f'{escape(boundary["id"])}</title></line>'
                )

    records_by_id.update({obj["id"]: obj for obj in scene.get("objects", [])})
    object_region_keys = {obj["id"]: obj.get("region", "") for obj in scene.get("objects", [])}
    missing_region_ids = set()
    for row in matrix.get("rows", []):
        if row.get("metric") not in {
            "object_region_membership_coverage",
            "object_region_assignment_coverage",
        }:
            continue
        for item in row.get("object_region_membership_evidence", []):
            obj = records_by_id.get(item["object_id"])
            region = records_by_id.get(item["region_id"])
            if not obj or not region:
                continue
            object_rect = obj["rect"]
            region_rect = region["rect"]
            object_region_layers.append(
                f'<line data-layer="object-region-membership" '
                f'data-object="{escape(obj["id"])}" '
                f'data-region="{escape(region["id"])}" '
                f'data-score="{item["score"]:.4f}" '
                f'x1="{object_rect.cx:.1f}" y1="{object_rect.cy:.1f}" '
                f'x2="{region_rect.cx:.1f}" y2="{region_rect.cy:.1f}" '
                f'stroke="#64748b" stroke-width="1.4" stroke-dasharray="2 5" '
                f'opacity="0.42"><title>{escape(obj["id"])} in '
                f'{escape(region["id"])}</title></line>'
            )
        for object_id in row.get("missing_region_evidence", []):
            if object_id in missing_region_ids:
                continue
            missing_region_ids.add(object_id)
            obj = records_by_id.get(object_id)
            if not obj:
                continue
            rect = obj["rect"]
            missing_region_layers.append(
                f'<circle data-layer="object-missing-region" '
                f'data-object="{escape(object_id)}" '
                f'data-region-key="{escape(object_region_keys.get(object_id, ""))}" '
                f'cx="{rect.cx:.1f}" cy="{rect.cy:.1f}" r="9" '
                f'fill="none" stroke="#dc2626" stroke-width="2.5" '
                f'opacity="0.86"><title>{escape(object_id)} missing region'
                f'</title></circle>'
            )

    records = {
        record["id"]: record
        for key in ("objects", "boundaries", "paths")
        for record in scene.get(key, [])
    }
    for path_id, descriptor in matrix.get("path_geometry", {}).items():
        path = records.get(path_id)
        if not path:
            continue
        path_rect = path["rect"]
        overlap_areas = {
            sample["target_id"]: sample["area"]
            for sample in descriptor.get("blocker_overlap_samples", [])
        }
        for sample in descriptor.get("clearance_samples", []):
            if sample["distance"] > 1e-9:
                continue
            blocker = records.get(sample["target_id"])
            if not blocker:
                continue
            blocker_rect = blocker["rect"]
            overlap_area = overlap_areas.get(blocker["id"], 0.0)
            stroke_width = 2 + min(4, overlap_area / 2500)
            conflict_layers.append(
                f'<line data-layer="path-blocker-conflict" '
                f'data-path="{escape(path_id)}" '
                f'data-blocker="{escape(blocker["id"])}" '
                f'data-overlap-area="{overlap_area:.1f}" '
                f'x1="{path_rect.cx:.1f}" y1="{path_rect.cy:.1f}" '
                f'x2="{blocker_rect.cx:.1f}" y2="{blocker_rect.cy:.1f}" '
                f'stroke="#e11d48" stroke-width="{stroke_width:.1f}" stroke-dasharray="3 4" '
                f'opacity="0.62"><title>{escape(path_id)} overlaps '
                f'{escape(blocker["id"])} ({overlap_area:.1f})</title></line>'
            )

    visibility_points = {
        record["id"]: (record["rect"].cx, record["rect"].cy)
        for key in ("entries", "regions")
        for record in analysis_scene.get(key, [])
    }
    for row in matrix.get("rows", []):
        if row.get("metric") == "line_of_sight_entry_region_ratio":
            sight_items = row.get("line_of_sight_evidence", [])
        elif row.get("metric") == "line_of_sight_region_pair_ratio":
            sight_items = row.get("line_of_sight_region_pair_evidence", [])
        else:
            continue
        for item in sight_items:
            from_id = item.get("entry_id", item.get("region_a"))
            to_id = item.get("region_id", item.get("region_b"))
            start = visibility_points.get(from_id)
            end = visibility_points.get(to_id)
            blockers = item.get("blocking_boundary_evidence", [])
            if start and end:
                visible = "true" if item.get("visible") else "false"
                stroke = "#22c55e" if item.get("visible") else "#db2777"
                visibility_layers.append(
                    f'<line data-layer="line-of-sight-centerline" '
                    f'data-metric="{escape(row["metric"])}" '
                    f'data-from="{escape(from_id)}" data-to="{escape(to_id)}" '
                    f'data-visible="{visible}" data-blocker-count="{len(blockers)}" '
                    f'x1="{start[0]:.1f}" y1="{start[1]:.1f}" '
                    f'x2="{end[0]:.1f}" y2="{end[1]:.1f}" '
                    f'stroke="{stroke}" stroke-width="1.8" stroke-dasharray="5 4" '
                    f'opacity="0.5"><title>{escape(from_id)} to '
                    f'{escape(to_id)} {visible}</title></line>'
                )
            for blocker in item.get("blocking_boundary_evidence", []):
                distances = blocker.get("intersection_distances_from_start", [])
                ratios = blocker.get("intersection_distance_ratios", [])
                for index, point in enumerate(blocker.get("intersection_points", [])):
                    distance = distances[index] if index < len(distances) else 0.0
                    ratio = ratios[index] if index < len(ratios) else 0.0
                    x, y = point
                    visibility_layers.append(
                        f'<circle data-layer="line-of-sight-blocker-hit" '
                        f'data-metric="{escape(row["metric"])}" '
                        f'data-boundary="{escape(blocker["boundary_id"])}" '
                        f'data-x="{x:.4f}" data-y="{y:.4f}" '
                        f'data-distance="{distance:.4f}" '
                        f'data-distance-ratio="{ratio:.4f}" '
                        f'cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#db2777" '
                        f'opacity="0.78"><title>{escape(blocker["boundary_id"])} '
                        f'{ratio:.4f}</title></circle>'
                    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" '
        'width="1000" height="1000">'
        + "".join(
            boxes
            + graph_layers
            + negative_space_layers
            + column_layers
            + region_layers
            + boundary_layers
            + region_boundary_layers
            + object_region_layers
            + missing_region_layers
            + conflict_layers
            + visibility_layers
            + labels
        )
        + "</svg>"
    )


def scene_position_grammar_overlay_svg(scene: dict, matrix: dict) -> str:
    """Draw only region-level furniture-group position grammar evidence."""
    layers = []
    for obj in scene.get("objects", []):
        layers.append(_position_basemap_object_svg(obj))
    for group in matrix.get("furniture_groups", []):
        layers.append(_position_grammar_group_svg(group))
    for item in _position_grammar_items(matrix):
        for residual in item.get("residuals", []):
            # The isolated overlay keeps only the public proxy result: expected
            # slot and actual-to-slot residual vector for each furniture group.
            layers.append(
                f'<circle data-layer="position-grammar-slot" '
                f'data-system="{escape(item["position-system-id"])}" '
                f'data-member="{escape(residual["id"])}" '
                f'cx="{residual["slot_x"]:.1f}" cy="{residual["slot_y"]:.1f}" r="4" '
                f'fill="#f59e0b" opacity="0.8">'
                f'<title>{escape(item["position-grammar-type"])} '
                f'{residual["normalized"]:.4f}</title></circle>'
            )
            layers.append(
                f'<line data-layer="position-grammar-residual" '
                f'data-system="{escape(item["position-system-id"])}" '
                f'data-member="{escape(residual["id"])}" '
                f'x1="{residual["x"]:.1f}" y1="{residual["y"]:.1f}" '
                f'x2="{residual["slot_x"]:.1f}" y2="{residual["slot_y"]:.1f}" '
                f'stroke="#f59e0b" stroke-width="2" opacity="0.82" />'
            )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" '
        'width="1000" height="1000">'
        + "".join(layers)
        + "</svg>"
    )


def _position_basemap_object_svg(obj: dict) -> str:
    """Draw one neutral source object as faint context for position evidence."""
    rect = obj["rect"]
    attrs = (
        f'data-layer="position-basemap-object" '
        f'data-object="{escape(obj["id"])}" '
        f'fill="#64748b" fill-opacity="0.10" '
        f'stroke="#64748b" stroke-width="1" stroke-opacity="0.34"'
    )
    points = obj.get("points") or []
    if len(points) >= 3:
        # Preserve authored polygonal footprints when the SVG/BIM proxy provides
        # them; the basemap is context only, not scoring evidence.
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        return (
            f"<polygon {attrs} points=\"{point_text}\">"
            f'<title>{escape(obj["id"])}</title></polygon>'
        )
    if obj.get("tag") in {"circle", "ellipse"}:
        return (
            f"<ellipse {attrs} "
            f'cx="{rect.cx:.1f}" cy="{rect.cy:.1f}" '
            f'rx="{rect.width / 2:.1f}" ry="{rect.height / 2:.1f}">'
            f'<title>{escape(obj["id"])}</title></ellipse>'
        )
    return (
        f"<rect {attrs} "
        f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
        f'width="{rect.width:.1f}" height="{rect.height:.1f}">'
        f'<title>{escape(obj["id"])}</title></rect>'
    )


def _position_grammar_group_svg(group: dict) -> str:
    """Draw one furniture-group proxy outline for focused position evidence."""
    rect = group["rect"]
    return (
        f'<rect data-layer="position-grammar-group" '
        f'data-group="{escape(group["id"])}" '
        f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
        f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
        f'fill="none" stroke="#059669" stroke-width="2.0" '
        f'stroke-dasharray="2 4" opacity="0.72">'
        f'<title>{escape(group["id"])}</title></rect>'
    )


def _axis_line(rect: Rect, angle: float) -> tuple[float, float, float, float]:
    half = max(rect.width, rect.height) * 0.35
    dx = cos(radians(angle)) * half
    dy = sin(radians(angle)) * half
    return rect.cx - dx, rect.cy - dy, rect.cx + dx, rect.cy + dy


def _north_table_rows(objects: list[dict]) -> list[dict]:
    tables = [
        obj
        for obj in objects
        if obj["group"] == "north_tables" and obj["role"] == "table"
    ]
    if not tables:
        return []

    ordered = sorted(tables, key=lambda obj: (obj["rect"].cy, obj["rect"].cx))
    order_matrix = []
    for row_index in range(0, len(ordered), 3):
        row = [
            {
                "shape": "rect",
                "attr": "table",
                "orientation": 0,
                "id": obj["id"],
            }
            for obj in ordered[row_index : row_index + 3]
        ]
        if row:
            order_matrix.append(row)

    # OCTA is valid here because this view is a comparable repeated table array.
    order = OrderAnalyzer(order_matrix, order_matrix).report(
        features=("shapes", "custom_attr")
    )["order"]
    centers = [(obj["rect"].cx, obj["rect"].cy) for obj in ordered]
    return [
        {
            "view_id": "north_tables_order",
            "metric": "octa_table_pattern",
            "score": round(order, 4),
            "status": "computed",
            "method": "octa_shapes_custom_attr",
            "evidence": [obj["id"] for obj in ordered],
            "uncertainty": "valid only for comparable repeated table objects",
        },
        {
            "view_id": "north_tables_order",
            "metric": "x_phase_regular",
            "score": round(_position_phase_score(centers[:3], axis="x"), 4),
            "status": "computed",
            "method": "gap_cv_score",
            "evidence": [obj["id"] for obj in ordered[:3]],
            "uncertainty": "checks first repeated table row spacing",
        },
    ]


def _group_geometry_rows(objects: list[dict]) -> list[dict]:
    rows = []
    groups = {
        "west_lounge_geometry": "west_lounge",
        "center_lounge_geometry": "center_lounge",
        "east_armchair_geometry": "east_armchairs",
    }
    for view_id, group in groups.items():
        members = [obj for obj in objects if obj["group"] == group]
        if not members:
            continue
        rows.append(
            {
                "view_id": view_id,
                "metric": "compactness",
                "score": round(_group_compactness(members), 4),
                "status": "computed",
                "method": "occupied_area_over_bbox_area",
                "evidence": [obj["id"] for obj in members],
                "uncertainty": "compactness is descriptive, not automatically good",
            }
        )
    return rows


def _region_alignment_row(scene: dict) -> dict:
    axis_descriptors = []
    for region in scene["regions"]:
        rect = region["rect"]
        if rect.width <= 0 or rect.height <= 0:
            continue
        axis_descriptors.append(_record_axis_descriptor(region))
    axes = [item["angle"] for item in axis_descriptors]
    if len(axes) < 2:
        return _not_available(
            "region_alignment",
            "region_axis_agreement",
            "needs at least two region records with measurable bounds",
        )
    return {
        "view_id": "region_alignment",
        "metric": "region_axis_agreement",
        "score": round(_axis_consistency(axes), 4),
        "status": "computed",
        "method": "region_local_axis_consistency",
        "evidence": [item["id"] for item in axis_descriptors],
        "axis_evidence": axis_descriptors,
        "uncertainty": "uses authored axis, polygon longest edge, then bbox fallback",
    }


def _region_centroid_phase_row(scene: dict) -> dict:
    axis_descriptors = [
        _record_axis_descriptor(region)
        for region in scene["regions"]
        if region["rect"].width > 0 and region["rect"].height > 0
    ]
    if len(axis_descriptors) < 3:
        return _not_available(
            "region_alignment",
            "region_centroid_phase_alignment",
            "needs at least three measurable regions",
        )
    axis = mean(item["angle"] for item in axis_descriptors)
    projections = []
    for region in sorted(scene["regions"], key=lambda item: item["id"]):
        rect = region["rect"]
        projection = rect.cx * cos(radians(axis)) + rect.cy * sin(radians(axis))
        projections.append(
            {
                "region_id": region["id"],
                "projection": round(projection, 4),
            }
        )
    return {
        "view_id": "region_alignment",
        "metric": "region_centroid_phase_alignment",
        "score": round(_projection_phase_score(projections), 4),
        "status": "computed",
        "method": "region_centroid_projection_gap_cv_score",
        "evidence": [item["region_id"] for item in projections],
        "axis_evidence": axis_descriptors,
        "region_centroid_phase_evidence": projections,
        "uncertainty": "projects region centers onto the mean region axis and scores spacing regularity; proxy, not region-frame overlap or semantic grouping",
    }


def _projection_phase_score(projections: list[dict]) -> float:
    coords = sorted(item["projection"] for item in projections)
    return _cv_score([b - a for a, b in zip(coords, coords[1:])])


def _region_centroid_trend_row(scene: dict) -> dict:
    regions = [
        region
        for region in scene["regions"]
        if region["rect"].width > 0 and region["rect"].height > 0
    ]
    if len(regions) < 3:
        return _not_available(
            "trend",
            "region_centroid_trend_alignment",
            "needs at least three measurable regions",
        )
    points = [(region["rect"].cx, region["rect"].cy, region["id"]) for region in regions]
    cx = mean(point[0] for point in points)
    cy = mean(point[1] for point in points)
    xx = mean((x - cx) ** 2 for x, _, _ in points)
    yy = mean((y - cy) ** 2 for _, y, _ in points)
    xy = mean((x - cx) * (y - cy) for x, y, _ in points)
    axis = (degrees(0.5 * atan2(2 * xy, xx - yy)) + 180) % 180
    if abs(axis - 180) < 1e-9:
        axis = 0.0
    axis_rad = radians(axis)
    ux, uy = cos(axis_rad), sin(axis_rad)
    evidence = []
    projections = []
    for x, y, region_id in sorted(points, key=lambda item: item[2]):
        dx, dy = x - cx, y - cy
        projection = dx * ux + dy * uy
        cross = abs(-uy * dx + ux * dy)
        projections.append(projection)
        evidence.append(
            {
                "region_id": region_id,
                "projection": round(projection, 4),
                "cross_axis_deviation": round(cross, 4),
            }
        )
    span = max(projections) - min(projections)
    mean_deviation = mean(item["cross_axis_deviation"] for item in evidence)
    return {
        "view_id": "trend",
        "metric": "region_centroid_trend_alignment",
        "score": round(1 / (1 + mean_deviation / max(span, 1e-9)), 4),
        "status": "computed",
        "method": "region_centroid_pca_axis_cross_deviation_score",
        "evidence": [item["region_id"] for item in evidence],
        "trend_axis": {
            "angle": round(axis, 4),
            "basis": "region_centroid_pca_axis",
            "region_count": len(regions),
            "span": round(span, 4),
            "mean_cross_axis_deviation": round(mean_deviation, 4),
        },
        "region_centroid_trend_evidence": evidence,
        "uncertainty": "PCA trend over region bbox centers; proxy for dominant layout direction, not semantic procession, circulation intent, or time-series trend",
    }


def _region_boundary_alignment_row(scene: dict) -> dict:
    region_axis_descriptors = [
        _record_axis_descriptor(region)
        for region in scene["regions"]
        if region["rect"].width > 0 and region["rect"].height > 0
    ]
    boundary_axis_descriptors = [
        _record_axis_descriptor(boundary)
        for boundary in scene.get("boundaries", [])
    ]
    if not region_axis_descriptors or not boundary_axis_descriptors:
        return _not_available(
            "region_alignment",
            "region_boundary_axis_agreement",
            "needs measurable regions and boundaries",
        )
    matches = []
    for region in region_axis_descriptors:
        best = max(
            (
                (
                    _axis_pair_score(region["angle"], boundary["angle"]),
                    boundary,
                )
                for boundary in boundary_axis_descriptors
            ),
            key=lambda item: item[0],
        )
        score, boundary = best
        matches.append(
            {
                "region_id": region["id"],
                "region_angle": region["angle"],
                "boundary_id": boundary["id"],
                "boundary_angle": boundary["angle"],
                "score": round(score, 4),
            }
        )
    return {
        "view_id": "region_alignment",
        "metric": "region_boundary_axis_agreement",
        "score": round(mean(item["score"] for item in matches), 4),
        "status": "computed",
        "method": "region_axis_to_boundary_axis_similarity",
        "evidence": [item["id"] for item in region_axis_descriptors]
        + [item["id"] for item in boundary_axis_descriptors],
        "region_axis_evidence": region_axis_descriptors,
        "boundary_axis_evidence": boundary_axis_descriptors,
        "region_boundary_matches": matches,
        "uncertainty": "matches region axes to nearest boundary axis; does not model boundary distance, strength, or containment",
    }


def _region_source_boundary_alignment_row(scene: dict) -> dict:
    boundaries_by_region = {}
    for boundary in scene.get("boundaries", []):
        boundaries_by_region.setdefault(boundary["region"], []).append(
            _record_axis_descriptor(boundary)
        )
    matches = []
    for region in scene["regions"]:
        if region["rect"].width <= 0 or region["rect"].height <= 0:
            continue
        boundary_axes = boundaries_by_region.get(region["region"], [])
        if not boundary_axes:
            continue
        region_axis = _record_axis_descriptor(region)
        score, boundary = max(
            (
                (
                    _axis_pair_score(region_axis["angle"], boundary["angle"]),
                    boundary,
                )
                for boundary in boundary_axes
            ),
            key=lambda item: item[0],
        )
        matches.append(
            {
                "region_id": region["id"],
                "region": region["region"],
                "region_angle": region_axis["angle"],
                "boundary_id": boundary["id"],
                "boundary_angle": boundary["angle"],
                "score": round(score, 4),
            }
        )
    if not matches:
        return _not_available(
            "region_alignment",
            "region_source_boundary_axis_agreement",
            "needs region-scoped boundary metadata",
        )
    return {
        "view_id": "region_alignment",
        "metric": "region_source_boundary_axis_agreement",
        "score": round(mean(item["score"] for item in matches), 4),
        "status": "computed",
        "method": "region_axis_to_same_region_boundary_axis_similarity",
        "evidence": [item["region_id"] for item in matches]
        + [item["boundary_id"] for item in matches],
        "region_boundary_matches": matches,
        "uncertainty": "uses authored data-region boundary scope; regions without scoped boundaries are omitted rather than assigned a false score",
    }


def _region_source_boundary_weighted_alignment_row(scene: dict) -> dict:
    boundaries_by_region = {}
    for boundary in scene.get("boundaries", []):
        boundaries_by_region.setdefault(boundary["region"], []).append(boundary)
    matches = []
    for region in scene["regions"]:
        if region["rect"].width <= 0 or region["rect"].height <= 0:
            continue
        boundaries = boundaries_by_region.get(region["region"], [])
        if not boundaries:
            continue
        region_axis = _record_axis_descriptor(region)
        boundary_scores = []
        for boundary in boundaries:
            boundary_axis = _record_axis_descriptor(boundary)
            length = _boundary_length(boundary)
            grouping_strength = boundary["weights"]["grouping_strength"]
            influence = length * grouping_strength
            boundary_scores.append(
                {
                    "boundary_id": boundary["id"],
                    "boundary_angle": boundary_axis["angle"],
                    "length": round(length, 4),
                    "grouping_strength": round(grouping_strength, 4),
                    "influence": round(influence, 4),
                    "score": round(
                        _axis_pair_score(region_axis["angle"], boundary_axis["angle"]),
                        4,
                    ),
                }
            )
        total = sum(item["influence"] for item in boundary_scores)
        if total <= 1e-9:
            continue
        matches.append(
            {
                "region_id": region["id"],
                "region": region["region"],
                "region_angle": region_axis["angle"],
                "score": round(
                    sum(item["score"] * item["influence"] for item in boundary_scores) / total,
                    4,
                ),
                "total_influence": round(total, 4),
                "boundary_scores": boundary_scores,
            }
        )
    if not matches:
        return _not_available(
            "region_alignment",
            "region_source_boundary_weighted_axis_agreement",
            "needs same-region boundaries with nonzero grouping influence",
        )
    return {
        "view_id": "region_alignment",
        "metric": "region_source_boundary_weighted_axis_agreement",
        "score": round(mean(item["score"] for item in matches), 4),
        "status": "computed",
        "method": "region_axis_to_same_region_boundary_axis_similarity_weighted_by_length_grouping_strength",
        "evidence": [item["region_id"] for item in matches],
        "region_boundary_weighted_matches": matches,
        "uncertainty": "weights same-region boundary axis agreement by parsed length and authored grouping_strength only",
    }


def _region_source_boundary_proximity_row(scene: dict) -> dict:
    boundaries_by_region = {}
    for boundary in scene.get("boundaries", []):
        boundaries_by_region.setdefault(boundary["region"], []).append(boundary)
    matches = []
    for region in scene["regions"]:
        if region["rect"].width <= 0 or region["rect"].height <= 0:
            continue
        boundaries = boundaries_by_region.get(region["region"], [])
        if not boundaries:
            continue
        region_scale = max(region["rect"].width, region["rect"].height)
        boundary_scores = []
        for boundary in boundaries:
            gap = _rect_gap(region["rect"], boundary["rect"])
            proximity = 1 / (1 + gap / max(region_scale, 1e-9))
            length = _boundary_length(boundary)
            influence = length * boundary["weights"]["grouping_strength"]
            boundary_scores.append(
                {
                    "boundary_id": boundary["id"],
                    "length": round(length, 4),
                    "gap": round(gap, 4),
                    "region_scale": round(region_scale, 4),
                    "proximity": round(proximity, 4),
                    "influence": round(influence, 4),
                }
            )
        total = sum(item["influence"] for item in boundary_scores)
        if total <= 1e-9:
            continue
        matches.append(
            {
                "region_id": region["id"],
                "region": region["region"],
                "score": round(
                    sum(item["proximity"] * item["influence"] for item in boundary_scores) / total,
                    4,
                ),
                "total_influence": round(total, 4),
                "boundary_scores": boundary_scores,
            }
        )
    if not matches:
        return _not_available(
            "region_alignment",
            "region_source_boundary_proximity",
            "needs same-region boundaries with nonzero grouping influence",
        )
    return {
        "view_id": "region_alignment",
        "metric": "region_source_boundary_proximity",
        "score": round(mean(item["score"] for item in matches), 4),
        "status": "computed",
        "method": "same_region_boundary_bbox_gap_weighted_by_length_grouping_strength",
        "evidence": [item["region_id"] for item in matches],
        "region_boundary_proximity": matches,
        "uncertainty": "bbox gap proximity proxy; replace with curve/polygon distance and containment in Rhino/BIM",
    }


def _inferred_region_row(inferred_regions: list[dict]) -> dict:
    evidence = _inferred_region_evidence(inferred_regions)
    return {
        "view_id": "region_alignment",
        "metric": "inferred_region_count",
        "score": len(inferred_regions),
        "status": "computed" if inferred_regions else "not_available",
        "method": "affordance_zone_boundary_cue_expanded_group_bounds",
        "evidence": [region["id"] for region in inferred_regions],
        "inferred_region_evidence": evidence,
        "uncertainty": "candidate regions inferred from furniture footprint, affordance extents, and same-region boundary cues; bbox proxy, not alpha-shape or perception-calibrated region discovery",
    }


def _affordance_use_zone_row(zones: list[dict]) -> dict:
    evidence = [
        {
            "id": zone["id"],
            "object_id": zone["object_id"],
            "region": zone["region"],
            "side": zone["side"],
            "depth": zone["depth"],
            "source": zone["source"],
            "zone_bbox": _rect_bbox(zone["rect"]),
            "footprint_bbox": _rect_bbox(zone["footprint_rect"]),
        }
        for zone in zones
    ]
    return {
        "view_id": "region_alignment",
        "metric": "affordance_use_zone_count",
        "score": len(zones),
        "status": "computed" if zones else "not_available",
        "method": "object_footprint_adjacent_affordance_rect_zones",
        "evidence": [zone["id"] for zone in zones],
        "affordance_use_zone_evidence": evidence,
        "uncertainty": "axis-aligned affordance use zones separate furniture footprints from occupied/use space; proxy, not posture simulation or swept human motion",
    }


def _furniture_affordance_extent_row(extents: list[dict]) -> dict:
    evidence = [
        _furniture_affordance_extent_evidence(extent)
        for extent in extents
    ]
    return {
        "view_id": "region_alignment",
        "metric": "furniture_affordance_extent_count",
        "score": len(extents),
        "status": "computed" if extents else "not_available",
        "method": "object_footprint_plus_own_affordance_zone_extent",
        "evidence": [extent["id"] for extent in extents],
        "furniture_affordance_extent_evidence": evidence,
        "uncertainty": "per-object affordance extents are bbox envelopes of footprint plus own use zones; proxy, not swept posture or motion simulation",
    }


def _furniture_affordance_extent_evidence(extent: dict) -> dict:
    """Return adapter-safe affordance extent evidence without Rect objects."""
    return {
        "id": extent["id"],
        "object_id": extent["object_id"],
        "region": extent["region"],
        "bbox": _rect_bbox(extent["rect"]),
        "footprint_bbox": _rect_bbox(extent["footprint_rect"]),
        "affordance_zone_ids": list(extent["affordance_zone_ids"]),
    }


def _furniture_group_evidence(group: dict) -> dict:
    """Return adapter-safe furniture group evidence without Rect objects."""
    return {
        "id": group["id"],
        "activity_region_id": group["activity_region_id"],
        "region": group["region"],
        "member_ids": list(group["member_ids"]),
        "furniture_affordance_extent_ids": list(group["furniture_affordance_extent_ids"]),
        "bbox": _rect_bbox(group["rect"]),
        "overlap_evidence": list(group["overlap_evidence"]),
        "metadata": dict(group["metadata"]),
    }


def _position_grammar_rows(position_grammar: dict) -> list[dict]:
    """Expose compact public position-order variables from grammar evidence."""
    if position_grammar.get("status") == "disabled":
        return [
            _disabled_row("internal_order", "P_position_fit", "position grammar disabled"),
            _disabled_row("internal_order", "P_position_confidence", "position grammar disabled"),
        ]
    items = position_grammar.get("items", [])
    if not items:
        return [
            _not_available(
                "internal_order",
                "P_position_fit",
                "needs at least two canonical furniture groups in a position scope",
            ),
            _not_available(
                "internal_order",
                "P_position_confidence",
                "needs at least two canonical furniture groups in a position scope",
            ),
        ]
    return [
        {
            "view_id": "internal_order",
            "metric": "P_position_fit",
            "score": round(mean(item["position-fit"] for item in items), 4),
            "status": "computed",
            "method": "region_position_grammar_selected_fit_mean",
            "evidence": [item["id"] for item in items],
            "region_position_grammar_evidence": items,
            "uncertainty": "position grammar is internal evidence only; final perceptual weight is deferred to experiments",
        },
        {
            "view_id": "internal_order",
            "metric": "P_position_confidence",
            "score": round(mean(item["position-confidence"] for item in items), 4),
            "status": "computed",
            "method": "region_position_grammar_confidence_mean",
            "evidence": [item["id"] for item in items],
            "region_position_grammar_evidence": items,
            "uncertainty": "confidence describes evidence reliability, not design quality",
        },
    ]


def _disabled_position_grammar() -> dict:
    """Return a stable empty payload when public position grammar is disabled."""
    return {
        "method": "region_level_furniture_group_position_grammar",
        "status": "disabled",
        "scopes": [],
        "items": [],
    }


def _position_grammar_items(matrix: dict) -> list[dict]:
    """Read nested position grammar evidence from public matrix rows."""
    for row in matrix.get("rows", []):
        if row.get("metric") == "P_position_fit":
            return list(row.get("region_position_grammar_evidence", []))
    return []


def _inferred_region_candidate_row(candidates: list[dict]) -> dict:
    evidence = _inferred_region_evidence(candidates)
    return {
        "view_id": "region_alignment",
        "metric": "inferred_region_candidate_count",
        "score": len(candidates),
        "status": "computed" if candidates else "not_available",
        "method": "affordance_zone_boundary_cue_expanded_group_candidate_bounds",
        "evidence": [region["id"] for region in candidates],
        "inferred_region_candidate_evidence": evidence,
        "uncertainty": "candidate regions inferred from furniture footprint, affordance extents, same-region boundary cues, and spacing margins; bbox proxy, not alpha-shape or perception-calibrated region discovery",
    }


def _inferred_region_evidence(regions: list[dict]) -> list[dict]:
    evidence = []
    for region in regions:
        item = {
            "region": region["region"],
            "geometry_basis": region["metadata"].get("geometry_basis"),
            "member_ids": region["metadata"]["member_ids"].split(","),
            "affordance_zone_ids": [
                zone_id
                for zone_id in region["metadata"].get("affordance_zone_ids", "").split(",")
                if zone_id
            ],
            "boundary_cue_ids": [
                cue_id
                for cue_id in region["metadata"].get("boundary_cue_ids", "").split(",")
                if cue_id
            ],
            "bbox": (
                round(region["rect"].left, 4),
                round(region["rect"].top, 4),
                round(region["rect"].right, 4),
                round(region["rect"].bottom, 4),
            ),
        }
        spacing_side_margins = _spacing_side_margins(region)
        if spacing_side_margins:
            item["spacing_side_margins"] = spacing_side_margins
        evidence.append(item)
    return evidence


def _inferred_region_explicit_iou_row(scene: dict, candidates: list[dict]) -> dict:
    explicit_by_region = {
        region["region"]: region
        for region in scene.get("regions", [])
        if region.get("metadata", {}).get("analysis-region") != "false"
    }
    evidence = []
    for candidate in candidates:
        explicit = explicit_by_region.get(candidate["region"])
        if explicit is None:
            continue
        intersection = _region_record_overlap_area(explicit, candidate["rect"])
        candidate_area = candidate["rect"].area
        explicit_area = explicit["rect"].area
        union = explicit_area + candidate_area - intersection
        if union <= 1e-9:
            continue
        missing_explicit_area = max(0.0, explicit_area - intersection)
        overflow_candidate_area = max(0.0, candidate_area - intersection)
        boundary_cue_ids = [
            cue_id
            for cue_id in candidate["metadata"].get("boundary_cue_ids", "").split(",")
            if cue_id
        ]
        evidence.append(
            {
                "region": candidate["region"],
                "explicit_region_id": explicit["id"],
                "candidate_bbox": (
                    round(candidate["rect"].left, 4),
                    round(candidate["rect"].top, 4),
                    round(candidate["rect"].right, 4),
                    round(candidate["rect"].bottom, 4),
                ),
                "explicit_bbox": (
                    round(explicit["rect"].left, 4),
                    round(explicit["rect"].top, 4),
                    round(explicit["rect"].right, 4),
                    round(explicit["rect"].bottom, 4),
                ),
                "candidate_boundary_cue_ids": boundary_cue_ids,
                "candidate_has_boundary_cue": bool(boundary_cue_ids),
                "candidate_area": round(candidate_area, 4),
                "explicit_area": round(explicit_area, 4),
                "intersection_area": round(intersection, 4),
                "union_area": round(union, 4),
                "iou": round(intersection / union, 4),
                "missing_explicit_area": round(missing_explicit_area, 4),
                "overflow_candidate_area": round(overflow_candidate_area, 4),
                "missing_explicit_area_ratio": round(
                    missing_explicit_area / max(explicit_area, 1e-9),
                    4,
                ),
                "overflow_candidate_area_ratio": round(
                    overflow_candidate_area / max(candidate_area, 1e-9),
                    4,
                ),
                "dominant_mismatch": _dominant_region_iou_mismatch(
                    missing_explicit_area,
                    overflow_candidate_area,
                ),
            }
        )
    evidence = sorted(evidence, key=lambda item: (item["iou"], item["region"]))
    return {
        "view_id": "region_alignment",
        "metric": "inferred_region_explicit_iou_mean",
        "score": round(mean(item["iou"] for item in evidence), 4)
        if evidence
        else None,
        "status": "computed" if evidence else "not_available",
        "method": "affordance_expanded_candidate_region_to_explicit_region_iou",
        "evidence": [item["region"] for item in evidence],
        "inferred_region_explicit_iou_evidence": evidence,
        "uncertainty": "compares affordance-expanded candidate bbox with explicit region geometry; bbox IoU proxy, not semantic region validation",
    }


def _dominant_region_iou_mismatch(
    missing_explicit_area: float,
    overflow_candidate_area: float,
) -> str:
    if max(missing_explicit_area, overflow_candidate_area) <= 1e-9:
        return "aligned"
    if missing_explicit_area > overflow_candidate_area:
        return "candidate_underfills_explicit"
    if overflow_candidate_area > missing_explicit_area:
        return "candidate_overflows_explicit"
    return "mixed"


def _inferred_region_gap_path_row(gap_paths: list[dict]) -> dict:
    evidence = [
        {
            "id": path["id"],
            "region_a": path["region_a"],
            "region_b": path["region_b"],
            "orientation": path["orientation"],
            "bbox": (
                round(path["rect"].left, 4),
                round(path["rect"].top, 4),
                round(path["rect"].right, 4),
                round(path["rect"].bottom, 4),
            ),
            "thickness": round(path["thickness"], 4),
            "overlap_span": round(path["overlap_span"], 4),
        }
        for path in gap_paths
    ]
    return {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_count",
        "score": len(gap_paths),
        "status": "computed" if gap_paths else "not_available",
        "method": "affordance_region_bbox_axis_gap_band_proxy",
        "evidence": [path["id"] for path in gap_paths],
        "inferred_region_gap_path_evidence": evidence,
        "uncertainty": "candidate path bands inferred from gaps between affordance-expanded region bboxes; proxy, not navmesh, medial axis, or route certification",
    }


def _inferred_region_gap_path_occupancy_row(
    scene: dict,
    affordance_zones: list[dict],
    gap_paths: list[dict],
) -> dict:
    candidates_by_id = {
        candidate["id"]: candidate
        for candidate in infer_region_candidates(scene)
    }
    evidence = []
    for gap_path in gap_paths:
        source_member_ids = set()
        source_zone_ids = set()
        for region_id in (gap_path["region_a"], gap_path["region_b"]):
            candidate = candidates_by_id.get(region_id, {})
            metadata = candidate.get("metadata", {})
            source_member_ids.update(
                item
                for item in metadata.get("member_ids", "").split(",")
                if item
            )
            source_zone_ids.update(
                item
                for item in metadata.get("affordance_zone_ids", "").split(",")
                if item
            )
        occupiers = []
        for obj in scene.get("objects", []):
            if obj["id"] in source_member_ids:
                continue
            overlap = _rect_overlap_area(gap_path["rect"], obj["rect"])
            if overlap > 0:
                occupiers.append(
                    {
                        "id": obj["id"],
                        "kind": "object_footprint",
                        "overlap_area": round(overlap, 4),
                    }
                )
        for zone in affordance_zones:
            if zone["id"] in source_zone_ids:
                continue
            overlap = _rect_overlap_area(gap_path["rect"], zone["rect"])
            if overlap > 0:
                occupiers.append(
                    {
                        "id": zone["id"],
                        "kind": "affordance_zone",
                        "object_id": zone["object_id"],
                        "overlap_area": round(overlap, 4),
                    }
                )
        occupied_area = sum(item["overlap_area"] for item in occupiers)
        gap_area = gap_path["rect"].area
        evidence.append(
            {
                "gap_path_id": gap_path["id"],
                "gap_bbox": _rect_bbox(gap_path["rect"]),
                "gap_area": round(gap_area, 4),
                "occupied_area": round(occupied_area, 4),
                "occupancy_ratio": round(occupied_area / max(gap_area, 1e-9), 4),
                "occupiers": occupiers,
            }
        )
    return {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_occupancy_ratio",
        "score": round(mean(item["occupancy_ratio"] for item in evidence), 4)
        if evidence
        else None,
        "status": "computed" if evidence else "not_available",
        "method": "inferred_gap_band_overlap_with_object_footprints_and_affordance_zones",
        "evidence": [item["gap_path_id"] for item in evidence],
        "inferred_region_gap_path_occupancy_evidence": evidence,
        "uncertainty": "overlap of inferred gap bands with object footprints and affordance zones; bbox union proxy, not navmesh clearance certification",
    }


def _inferred_region_gap_path_free_space_overlap_row(
    gap_paths: list[dict],
    negative_space: dict,
) -> dict:
    free_cells = [
        {
            "id": f"component_{item['component_index']}_cell_{item['cell_index']}",
            "rect": _rect_from_points(item["points"]),
        }
        for item in negative_space.get("free_space_polygons", [])
    ]
    evidence = []
    for gap_path in gap_paths:
        overlaps = [
            (cell["id"], _rect_overlap_area(gap_path["rect"], cell["rect"]))
            for cell in free_cells
        ]
        overlaps = [(cell_id, area) for cell_id, area in overlaps if area > 1e-9]
        overlap_area = sum(area for _, area in overlaps)
        gap_area = gap_path["rect"].area
        evidence.append(
            {
                "gap_path_id": gap_path["id"],
                "gap_bbox": _rect_bbox(gap_path["rect"]),
                "gap_area": round(gap_area, 4),
                "free_space_overlap_area": round(overlap_area, 4),
                "free_space_overlap_ratio": round(overlap_area / max(gap_area, 1e-9), 4),
                "overlap_cell_ids": [cell_id for cell_id, _ in overlaps],
            }
        )
    return {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_free_space_overlap_ratio",
        "score": round(mean(item["free_space_overlap_ratio"] for item in evidence), 4)
        if evidence
        else None,
        "status": "computed" if evidence else "not_available",
        "method": "inferred_gap_band_overlap_with_rect_cell_free_space_polygons",
        "evidence": [item["gap_path_id"] for item in evidence],
        "inferred_region_gap_path_free_space_overlap_evidence": evidence,
        "uncertainty": "overlap of inferred gap bands with rect-cell free-space polygons; proxy, not navmesh or route certification",
    }


def _inferred_region_gap_path_walkable_proxy_row(gap_path_graph: dict) -> dict:
    edge_count = gap_path_graph.get("edge_count", 0)
    walkable_edges = gap_path_graph.get("walkable_proxy_edges", [])
    return {
        "view_id": "path_connectivity",
        "metric": "inferred_region_gap_path_walkable_proxy_ratio",
        "score": round(len(walkable_edges) / max(1, edge_count), 4)
        if edge_count
        else None,
        "status": "computed" if edge_count else "not_available",
        "method": "clear_and_free_space_supported_inferred_gap_path_edges",
        "evidence": walkable_edges,
        "walkable_proxy_edge_count": len(walkable_edges),
        "walkable_proxy_component_count": gap_path_graph.get(
            "walkable_proxy_component_count",
            0,
        ),
        "walkable_proxy_min_thickness": gap_path_graph.get(
            "walkable_proxy_min_thickness",
        ),
        "walkable_proxy_mean_thickness": gap_path_graph.get(
            "walkable_proxy_mean_thickness",
        ),
        "total_gap_path_edge_count": edge_count,
        "walkable_proxy_edges": walkable_edges,
        "walkable_proxy_components": gap_path_graph.get(
            "walkable_proxy_components",
            [],
        ),
        "walkable_proxy_edge_widths": gap_path_graph.get(
            "walkable_proxy_edge_widths",
            [],
        ),
        "uncertainty": "clear inferred gap bands with positive free-space overlap; proxy, not navmesh route certification or minimum-width guarantee",
    }


def _inferred_region_gap_path_min_width_row(gap_path_graph: dict) -> dict:
    walkable_count = gap_path_graph.get("walkable_proxy_edge_count", 0)
    passing_edges = gap_path_graph.get("width_pass_edges", [])
    method = (
        "walkable_gap_band_thickness_over_manual_required_path_width"
        if gap_path_graph.get("minimum_width_basis") == "manual_required_path_width"
        else "walkable_gap_band_thickness_over_half_sampled_grid_resolution"
    )
    return {
        "view_id": "path_connectivity",
        "metric": "inferred_region_gap_path_min_width_pass_ratio",
        "score": round(len(passing_edges) / max(1, walkable_count), 4)
        if walkable_count
        else None,
        "status": "computed" if walkable_count else "not_available",
        "method": method,
        "evidence": passing_edges,
        "minimum_width": gap_path_graph.get("minimum_width"),
        "minimum_width_basis": gap_path_graph.get("minimum_width_basis"),
        "minimum_width_evidence": gap_path_graph.get("minimum_width_evidence", []),
        "passing_edge_count": len(passing_edges),
        "walkable_proxy_edge_count": walkable_count,
        "width_pass_edges": passing_edges,
        "width_fail_edges": gap_path_graph.get("width_fail_edges", []),
        "width_evidence": gap_path_graph.get("width_evidence", []),
        "uncertainty": "minimum width uses half the sampled grid resolution as a scene-scale proxy; not code-compliant egress width, human-body calibration, or navmesh clearance",
    }


def _inferred_region_gap_path_cad_free_space_overlap_row(
    gap_paths: list[dict],
    negative_space: dict,
) -> dict:
    """Compare inferred gap bands with Shapely room-minus-blocker free space."""
    cad_polygons = negative_space.get("cad_room_minus_blocker_polygons", [])
    cad_shapes = [
        (f"component_{item['component_index']}", _cad_evidence_to_shapely_polygon(item))
        for item in cad_polygons
    ]
    if not gap_paths or not cad_shapes:
        return {
            "view_id": "path_connectivity",
            "metric": "inferred_region_gap_path_cad_free_space_overlap_ratio",
            "score": None,
            "status": "not_available",
            "method": "inferred_gap_band_overlap_with_shapely_room_minus_blocker_polygons",
            "evidence": [],
            "inferred_region_gap_path_cad_free_space_overlap_evidence": [],
            "uncertainty": "overlap of inferred gap bands with Shapely room-minus-blocker polygons; stronger than rect-cell proxy but still not navmesh route certification",
        }
    evidence = []
    for gap_path in gap_paths:
        gap_shape = _shape_to_shapely_polygon(gap_path["rect"])
        # Intersect each gap band with CAD free-space components, not rect-cell proxies.
        overlaps = [
            (component_id, gap_shape.intersection(cad_shape).area)
            for component_id, cad_shape in cad_shapes
        ]
        overlaps = [
            (component_id, area)
            for component_id, area in overlaps
            if area > 1e-9
        ]
        overlap_area = sum(area for _, area in overlaps)
        gap_area = gap_path["rect"].area
        evidence.append(
            {
                "gap_path_id": gap_path["id"],
                "gap_bbox": _rect_bbox(gap_path["rect"]),
                "gap_area": round(gap_area, 4),
                "cad_free_space_overlap_area": round(overlap_area, 4),
                "cad_free_space_overlap_ratio": round(
                    overlap_area / max(gap_area, 1e-9),
                    4,
                ),
                "overlap_component_ids": [
                    component_id for component_id, _ in overlaps
                ],
            }
        )
    return {
        "view_id": "path_connectivity",
        "metric": "inferred_region_gap_path_cad_free_space_overlap_ratio",
        "score": round(mean(item["cad_free_space_overlap_ratio"] for item in evidence), 4)
        if evidence
        else None,
        "status": "computed" if evidence and cad_shapes else "not_available",
        "method": "inferred_gap_band_overlap_with_shapely_room_minus_blocker_polygons",
        "evidence": [item["gap_path_id"] for item in evidence],
        "inferred_region_gap_path_cad_free_space_overlap_evidence": evidence,
        "uncertainty": "overlap of inferred gap bands with Shapely room-minus-blocker polygons; stronger than rect-cell proxy but still not navmesh route certification",
    }


def _inferred_gap_path_width_free_space_clearance_row(
    rows: list[dict],
    negative_space: dict,
) -> dict:
    row_by_metric = {row.get("metric"): row for row in rows}
    free_space_width = row_by_metric.get(
        "free_space_polygon_graph_mean_edge_clearance_width",
        {},
    ).get("score")
    if free_space_width is None:
        free_space_edges = negative_space.get("free_space_polygon_graph", {}).get(
            "edges",
            [],
        )
        free_space_width = (
            round(mean(edge["clearance_width"] for edge in free_space_edges), 4)
            if free_space_edges
            else None
        )
    walkable_row = row_by_metric.get(
        "inferred_region_gap_path_walkable_proxy_ratio",
        {},
    )
    walkable_width = walkable_row.get("walkable_proxy_mean_thickness")
    evidence = {
        "free_space_mean_edge_clearance_width": free_space_width,
        "walkable_proxy_mean_thickness": walkable_width,
        "walkable_proxy_min_thickness": walkable_row.get(
            "walkable_proxy_min_thickness"
        ),
        "walkable_proxy_edge_count": walkable_row.get("walkable_proxy_edge_count", 0),
    }
    computed = free_space_width is not None and walkable_width not in (None, 0)
    return {
        "view_id": "path_connectivity",
        "metric": "inferred_gap_path_width_free_space_clearance_ratio",
        "score": round(free_space_width / walkable_width, 4) if computed else None,
        "status": "computed" if computed else "not_available",
        "method": "free_space_edge_clearance_width_over_inferred_gap_band_width",
        "evidence": evidence,
        "uncertainty": "ratio between rect-cell free-space shared-edge width and inferred gap-band width; proxy consistency check, not route certification",
    }


def _inferred_region_gap_path_explicit_path_iou_row(
    scene: dict,
    gap_paths: list[dict],
) -> dict:
    explicit_paths = scene.get("paths", [])
    evidence = []
    for gap_path in gap_paths:
        if not explicit_paths:
            continue
        best_path = max(
            explicit_paths,
            key=lambda path: _rect_iou(gap_path["rect"], path["rect"]),
        )
        evidence.append(
            {
                "gap_path_id": gap_path["id"],
                "best_path_id": best_path["id"],
                "gap_bbox": (
                    round(gap_path["rect"].left, 4),
                    round(gap_path["rect"].top, 4),
                    round(gap_path["rect"].right, 4),
                    round(gap_path["rect"].bottom, 4),
                ),
                "path_bbox": (
                    round(best_path["rect"].left, 4),
                    round(best_path["rect"].top, 4),
                    round(best_path["rect"].right, 4),
                    round(best_path["rect"].bottom, 4),
                ),
                "iou": round(_rect_iou(gap_path["rect"], best_path["rect"]), 4),
            }
        )
    return {
        "view_id": "region_alignment",
        "metric": "inferred_region_gap_path_explicit_path_iou_mean",
        "score": round(mean(item["iou"] for item in evidence), 4)
        if evidence
        else None,
        "status": "computed" if evidence else "not_available",
        "method": "affordance_gap_band_to_explicit_path_bbox_iou",
        "evidence": [item["gap_path_id"] for item in evidence],
        "inferred_region_gap_path_explicit_path_iou_evidence": evidence,
        "uncertainty": "compares inferred gap bands with authored path bboxes; bbox IoU proxy, not route validation or navmesh alignment",
    }


def _object_region_membership_rows(scene: dict) -> list[dict]:
    regions_by_key = {region["region"]: region for region in scene.get("regions", [])}
    evidence = []
    missing = []
    for obj in scene.get("objects", []):
        region = regions_by_key.get(obj["region"])
        if region is None:
            missing.append(obj["id"])
            continue
        object_area = obj["rect"].area
        if object_area <= 1e-9:
            continue
        overlap = _region_record_overlap_area(region, obj["rect"])
        evidence.append(
            {
                "object_id": obj["id"],
                "region_id": region["id"],
                "overlap_area": round(overlap, 4),
                "object_area": round(object_area, 4),
                "score": round(overlap / object_area, 4),
            }
        )
    assignment_row = {
        "view_id": "region_alignment",
        "metric": "object_region_assignment_coverage",
        "score": round(len(evidence) / max(1, len(scene.get("objects", []))), 4),
        "status": "computed" if scene.get("objects") else "not_available",
        "method": "objects_with_matching_region_records_ratio",
        "evidence": [item["object_id"] for item in evidence],
        "matched_object_count": len(evidence),
        "total_object_count": len(scene.get("objects", [])),
        "missing_region_evidence": missing,
        "uncertainty": "metadata coverage row; reports whether authored object region ids can be checked against region records",
    }
    if not evidence:
        return [
            _not_available(
                "region_alignment",
                "object_region_membership_coverage",
                "needs objects with authored region ids matching measurable region records",
            ),
            assignment_row,
        ]
    return [{
        "view_id": "region_alignment",
        "metric": "object_region_membership_coverage",
        "score": round(mean(item["score"] for item in evidence), 4),
        "status": "computed",
        "method": "object_region_rect_or_polygon_overlap_area_ratio",
        "evidence": [item["object_id"] for item in evidence],
        "object_region_membership_evidence": evidence,
        "missing_region_evidence": missing,
        "uncertainty": "checks authored object-region metadata against region geometry; bbox object footprints and simple polygon-region overlap only",
    }, assignment_row]


def _region_record_overlap_area(region: dict, rect: Rect) -> float:
    """Return object overlap with authored polygons or inferred region bboxes."""
    metadata = region.get("metadata", {})
    if metadata.get("axis-basis") in {
        "affordance_point_pca_frame",
        "furniture_group_frame_mean",
    }:
        # PCA points are diagnostic oriented envelopes. Membership coverage keeps
        # using the stable bbox proxy that downstream inferred-region rows expose.
        return _rect_overlap_area(region["rect"], rect)
    points = region.get("points") or []
    if len(points) >= 3:
        return _polygon_rect_overlap_area(Polygon(tuple(points)), rect)
    return _rect_overlap_area(region["rect"], rect)


def _column_alignment_rows(scene: dict) -> list[dict]:
    columns = scene.get("column_axes", [])
    if not columns:
        return [_not_available(
            "column_alignment",
            "region_column_axis_agreement",
            "fixture has no column-grid metadata",
        )]
    region_axis_descriptors = [
        _record_axis_descriptor(region)
        for region in scene["regions"]
        if region["rect"].width > 0 and region["rect"].height > 0
    ]
    column_axis_descriptors = [_record_axis_descriptor(column) for column in columns]
    region_axes = [item["angle"] for item in region_axis_descriptors]
    column_axes = [item["angle"] for item in column_axis_descriptors]
    scores = [
        max(_axis_pair_score(region_axis, column_axis) for column_axis in column_axes)
        for region_axis in region_axes
    ]
    rows = []
    if scores:
        rows.append(
            {
                "view_id": "column_alignment",
                "metric": "region_column_axis_agreement",
                "score": round(mean(scores), 4),
                "status": "computed",
                "method": "region_bbox_axis_to_column_axis_similarity",
                "evidence": [item["id"] for item in columns],
                "region_axis_evidence": region_axis_descriptors,
                "column_axis_evidence": column_axis_descriptors,
                "uncertainty": "uses region local axes and authored column axes; irregular grids need local axis interpolation",
            }
        )
    else:
        rows.append(
            _not_available(
                "column_alignment",
                "region_column_axis_agreement",
                "needs measurable regions for region-to-column direction scoring",
            )
        )
    phase_evidence = _object_column_axis_phase_evidence(scene.get("objects", []), columns)
    if phase_evidence:
        rows.append(
            {
                "view_id": "column_alignment",
                "metric": "object_column_axis_phase_alignment",
                "score": round(mean(item["score"] for item in phase_evidence), 4),
                "status": "computed",
                "method": "object_center_to_nearest_column_axis_distance_kernel",
                "evidence": [item["object_id"] for item in phase_evidence],
                "column_axis_evidence": column_axis_descriptors,
                "object_axis_phase_evidence": phase_evidence,
                "uncertainty": "object center to nearest authored column axis normalized by median parallel-axis spacing; phase proxy, not bay containment",
            }
        )
    local_position_evidence = _object_column_bay_local_position_evidence(
        scene.get("objects", []),
        columns,
    )
    if local_position_evidence:
        rows.append(
            {
                "view_id": "column_alignment",
                "metric": "object_column_bay_local_position_coverage",
                "score": round(mean(item["score"] for item in local_position_evidence), 4),
                "status": "computed",
                "method": "object_center_affine_position_in_nearest_column_bay",
                "evidence": [item["object_id"] for item in local_position_evidence],
                "column_axis_evidence": column_axis_descriptors,
                "object_bay_local_position_evidence": local_position_evidence,
                "uncertainty": "object center affine coordinates inside nearest authored column bay; local-frame proxy, not full irregular grid interpolation",
            }
        )
    bay_fit_evidence = _region_column_bay_fit_evidence(scene.get("regions", []), columns)
    if bay_fit_evidence:
        rows.append(
            {
                "view_id": "column_alignment",
                "metric": "region_column_bay_fit",
                "score": round(mean(item["score"] for item in bay_fit_evidence), 4),
                "status": "computed",
                "method": "region_bbox_overlap_with_adjacent_column_axis_bay",
                "evidence": [item["region_id"] for item in bay_fit_evidence],
                "column_axis_evidence": column_axis_descriptors,
                "region_bay_fit_evidence": bay_fit_evidence,
                "uncertainty": "axis-aligned adjacent authored column-axis bay overlap proxy; not polygon bay topology or irregular grid interpolation",
            }
        )
    return rows


def _column_grid_relation_rows(column_grid: dict) -> list[dict]:
    """Return explicit column-grid relation rows for evaluator consumers."""
    if column_grid.get("status") != "computed":
        reason = column_grid.get("reason", "missing column-grid support")
        return [
            _not_available("column_alignment", "column_grid_C_global", reason),
            _not_available("column_alignment", "column_grid_C_local_profile", reason),
        ]

    global_relations = column_grid.get("global_relations", [])
    local_profiles = column_grid.get("local_profiles", [])
    rows = []
    if global_relations:
        # Scores are direct means over normalized relation evidence; empty
        # evidence is unavailable because there is nothing to substantiate.
        rows.append(
            {
                "view_id": "column_alignment",
                "metric": "column_grid_C_global",
                "score": round(mean(item["agreement"] for item in global_relations), 4),
                "status": "computed",
                "method": "explicit_column_grid_region_to_system_branch_frame_agreement",
                "evidence": [item["region_id"] for item in global_relations],
                "column_grid_evidence": {"global_relations": global_relations},
                "uncertainty": "explicit column-grid relation evidence; not structural grid validation or BIM-hosted topology",
            }
        )
    else:
        rows.append(
            _not_available(
                "column_alignment",
                "column_grid_C_global",
                "computed column grid has no global relation evidence",
            )
        )
    if local_profiles:
        rows.append(
            {
                "view_id": "column_alignment",
                "metric": "column_grid_C_local_profile",
                "score": round(
                    mean(item["frame_agreement"] for item in local_profiles), 4
                ),
                "status": "computed",
                "method": "explicit_column_grid_region_local_bay_profile_agreement",
                "evidence": [item["region_id"] for item in local_profiles],
                "column_grid_evidence": {"local_profiles": local_profiles},
                "uncertainty": "explicit bay profile evidence; not irregular structural grid interpolation",
            }
        )
    else:
        rows.append(
            _not_available(
                "column_alignment",
                "column_grid_C_local_profile",
                "computed column grid has no local bay profile evidence",
            )
        )
    return rows


def _region_column_bay_fit_evidence(regions: list[dict], columns: list[dict]) -> list[dict]:
    bays = _column_axis_bays(columns)
    if not regions or not bays:
        return []
    evidence = []
    for region in sorted(regions, key=lambda item: item["id"]):
        best = max(
            (
                (
                    _column_bay_region_overlap_area(region["rect"], bay),
                    bay,
                )
                for bay in bays
            ),
            key=lambda item: (item[0], item[1]["id"]),
        )
        overlap_area, bay = best
        region_area = region["rect"].area
        evidence.append(
            {
                "region_id": region["id"],
                "bay_id": bay["id"],
                "overlap_area": round(overlap_area, 4),
                "region_area": round(region_area, 4),
                "score": round(overlap_area / max(region_area, 1e-9), 4),
            }
        )
    return evidence


def _object_column_bay_local_position_evidence(
    objects: list[dict],
    columns: list[dict],
) -> list[dict]:
    bays = _column_axis_bays(columns)
    if not objects or not bays:
        return []
    evidence = []
    for obj in sorted(objects, key=lambda item: item["id"]):
        candidates = []
        for bay in bays:
            local = _bay_local_coordinates(obj["rect"].cx, obj["rect"].cy, bay)
            if local is None:
                continue
            local_u, local_v = local
            outside = (
                max(0.0, -local_u)
                + max(0.0, local_u - 1.0)
                + max(0.0, -local_v)
                + max(0.0, local_v - 1.0)
            )
            candidates.append((outside, bay["id"], local_u, local_v))
        if not candidates:
            continue
        _, bay_id, local_u, local_v = min(candidates)
        inside_bay = (
            -1e-9 <= local_u <= 1.0 + 1e-9
            and -1e-9 <= local_v <= 1.0 + 1e-9
        )
        evidence.append(
            {
                "object_id": obj["id"],
                "bay_id": bay_id,
                "local_u": round(local_u, 4),
                "local_v": round(local_v, 4),
                "inside_bay": inside_bay,
                "score": 1.0 if inside_bay else 0.0,
            }
        )
    return evidence


def _column_axis_bays(columns: list[dict]) -> list[dict]:
    descriptors = [
        {
            "id": column["id"],
            "angle": _record_axis_angle(column),
            "points": column.get("points") or [],
            "rect": column["rect"],
        }
        for column in columns
    ]
    bays = []
    for angle in (0.0, 90.0):
        parallel = [
            item
            for item in descriptors
            if _axis_pair_score(item["angle"], angle) >= 0.999
        ]
        coord = "y" if angle == 0.0 else "x"
        parallel = sorted(
            parallel,
            key=lambda item: item["rect"].cy if coord == "y" else item["rect"].cx,
        )
        for first, second in zip(parallel, parallel[1:]):
            if coord == "x":
                left, right = sorted((first["rect"].cx, second["rect"].cx))
                if right - left <= 1e-9:
                    continue
                top = min(first["rect"].top, second["rect"].top)
                bottom = max(first["rect"].bottom, second["rect"].bottom)
            else:
                top, bottom = sorted((first["rect"].cy, second["rect"].cy))
                if bottom - top <= 1e-9:
                    continue
                left = min(first["rect"].left, second["rect"].left)
                right = max(first["rect"].right, second["rect"].right)
            bays.append(
                {
                    "id": f"{first['id']}__{second['id']}",
                    "rect": Rect(
                        cx=(left + right) / 2,
                        cy=(top + bottom) / 2,
                        width=right - left,
                        height=bottom - top,
                    ),
                }
            )
    angles = sorted({round(item["angle"], 4) for item in descriptors})
    for angle in angles:
        if any(_axis_pair_score(angle, cardinal) >= 0.999 for cardinal in (0.0, 90.0)):
            continue
        parallel = [
            item
            for item in descriptors
            if len(item["points"]) >= 2 and _axis_pair_score(item["angle"], angle) >= 0.999
        ]
        parallel = sorted(parallel, key=lambda item: item["rect"].cy)
        for first, second in zip(parallel, parallel[1:]):
            polygon = Polygon(
                points=(
                    first["points"][0],
                    first["points"][-1],
                    second["points"][-1],
                    second["points"][0],
                )
            )
            bays.append(
                {
                    "id": f"{first['id']}__{second['id']}",
                    "polygon": polygon,
                    "rect": polygon.bounds,
                }
            )
    return bays


def _column_bay_region_overlap_area(region_rect: Rect, bay: dict) -> float:
    polygon = bay.get("polygon")
    if polygon is not None:
        return _polygon_rect_overlap_area(polygon, region_rect)
    return _rect_overlap_area(region_rect, bay["rect"])


def _bay_local_coordinates(x: float, y: float, bay: dict) -> tuple[float, float] | None:
    polygon = bay.get("polygon")
    if polygon is not None:
        first_start, first_end, _, second_start = polygon.points
        origin_x, origin_y = first_start
        ux = first_end[0] - origin_x
        uy = first_end[1] - origin_y
        vx = second_start[0] - origin_x
        vy = second_start[1] - origin_y
        det = ux * vy - uy * vx
        if abs(det) <= 1e-9:
            return None
        px = x - origin_x
        py = y - origin_y
        return (
            (px * vy - py * vx) / det,
            (ux * py - uy * px) / det,
        )
    rect = bay["rect"]
    if rect.width <= 1e-9 or rect.height <= 1e-9:
        return None
    return (
        (x - rect.left) / rect.width,
        (y - rect.top) / rect.height,
    )


def _object_column_axis_phase_evidence(objects: list[dict], columns: list[dict]) -> list[dict]:
    column_descriptors = [
        {
            "id": column["id"],
            "angle": _record_axis_angle(column),
            "points": column.get("points") or [],
            "rect": column["rect"],
        }
        for column in columns
    ]
    if not objects or not column_descriptors:
        return []
    axis_spacing = _column_axis_spacing(column_descriptors)
    evidence = []
    for obj in sorted(objects, key=lambda item: item["id"]):
        distance, column = min(
            (
                (
                    _point_to_column_axis_distance(
                        obj["rect"].cx,
                        obj["rect"].cy,
                        column,
                    ),
                    column,
                )
                for column in column_descriptors
            ),
            key=lambda item: (item[0], item[1]["id"]),
        )
        evidence.append(
            {
                "object_id": obj["id"],
                "nearest_axis_id": column["id"],
                "distance": round(distance, 4),
                "axis_spacing": round(axis_spacing, 4),
                "score": round(1 / (1 + distance / max(axis_spacing, 1e-9)), 4),
            }
        )
    return evidence


def _point_to_column_axis_distance(x: float, y: float, column: dict) -> float:
    points = column["points"]
    if len(points) >= 2:
        distance, _, _, _ = _project_point_to_polyline(x, y, points)
        return distance
    return _rect_gap(Rect(cx=x, cy=y, width=0.0, height=0.0), column["rect"])


def _column_axis_spacing(columns: list[dict]) -> float:
    distances = [
        hypot(first["rect"].cx - second["rect"].cx, first["rect"].cy - second["rect"].cy)
        for first, second in combinations(columns, 2)
        if _axis_pair_score(first["angle"], second["angle"]) >= 0.999
    ]
    if not distances:
        return 1.0
    distances = sorted(distances)
    return distances[len(distances) // 2]


def _whole_space_force_rows(scene: dict) -> list[dict]:
    axis_evidence = []
    for group in sorted({obj["group"] for obj in scene["objects"]}):
        members = [obj for obj in scene["objects"] if obj["group"] == group]
        if not members:
            continue
        rect = _bounds(members)
        axis_evidence.append(
            {
                "id": group,
                "angle": 0.0 if rect.width >= rect.height else 90.0,
                "basis": "group_bbox_long_axis",
                "member_count": len(members),
            }
        )
    group_axes = [item["angle"] for item in axis_evidence]
    if not group_axes:
        return [_not_available(
            "whole_space_force",
            "group_axis_concentration",
            "needs furniture groups",
        )]
    rows = [{
        "view_id": "whole_space_force",
        "metric": "group_axis_concentration",
        "score": round(_axis_consistency(group_axes), 4),
        "status": "computed",
        "method": "group_bbox_axis_histogram",
        "evidence": [item["id"] for item in axis_evidence],
        "axis_evidence": axis_evidence,
        "uncertainty": "multi-scale force is reduced to group bbox axes in this slice",
    }]
    column_axis_evidence = [
        _record_axis_descriptor(column) for column in scene.get("column_axes", [])
    ]
    if column_axis_evidence:
        column_axes = [item["angle"] for item in column_axis_evidence]
        scores = [
            max(_axis_pair_score(group_axis, column_axis) for column_axis in column_axes)
            for group_axis in group_axes
        ]
        rows.append(
            {
                "view_id": "whole_space_force",
                "metric": "group_column_axis_agreement",
                "score": round(mean(scores), 4),
                "status": "computed",
                "method": "group_bbox_axis_to_column_axis_similarity",
                "evidence": [item["id"] for item in axis_evidence]
                + [item["id"] for item in column_axis_evidence],
                "group_axis_evidence": axis_evidence,
                "column_axis_evidence": column_axis_evidence,
                "uncertainty": "compares group bbox force proxy to authored column axes; not a weighted whole-space force model",
            }
        )
    path_axis_evidence = [
        _record_axis_descriptor(path) for path in scene.get("paths", [])
    ]
    if path_axis_evidence:
        path_axes = [item["angle"] for item in path_axis_evidence]
        scores = [
            max(_axis_pair_score(group_axis, path_axis) for path_axis in path_axes)
            for group_axis in group_axes
        ]
        rows.append(
            {
                "view_id": "whole_space_force",
                "metric": "group_path_axis_agreement",
                "score": round(mean(scores), 4),
                "status": "computed",
                "method": "group_bbox_axis_to_path_axis_similarity",
                "evidence": [item["id"] for item in axis_evidence]
                + [item["id"] for item in path_axis_evidence],
                "group_axis_evidence": axis_evidence,
                "path_axis_evidence": path_axis_evidence,
                "uncertainty": "compares group bbox force proxy to authored path polygon axis; not a route field or movement model",
            }
        )
    boundary_axis_evidence = [
        _record_axis_descriptor(boundary) for boundary in scene.get("boundaries", [])
    ]
    if boundary_axis_evidence:
        boundary_axes = [item["angle"] for item in boundary_axis_evidence]
        scores = [
            max(_axis_pair_score(group_axis, boundary_axis) for boundary_axis in boundary_axes)
            for group_axis in group_axes
        ]
        rows.append(
            {
                "view_id": "whole_space_force",
                "metric": "group_boundary_axis_agreement",
                "score": round(mean(scores), 4),
                "status": "computed",
                "method": "group_bbox_axis_to_boundary_axis_similarity",
                "evidence": [item["id"] for item in axis_evidence]
                + [item["id"] for item in boundary_axis_evidence],
                "group_axis_evidence": axis_evidence,
                "boundary_axis_evidence": boundary_axis_evidence,
                "uncertainty": "compares group bbox force proxy to boundary axes; not a weighted boundary force field",
            }
        )
        weighted_boundary_axes = [
            _weighted_boundary_axis_descriptor(boundary)
            for boundary in scene.get("boundaries", [])
        ]
        rows.append(
            {
                "view_id": "whole_space_force",
                "metric": "weighted_boundary_axis_concentration",
                "score": round(_weighted_axis_consistency(weighted_boundary_axes), 4),
                "status": "computed",
                "method": "boundary_axis_weighted_by_walk_see_grouping_strength",
                "evidence": [item["id"] for item in weighted_boundary_axes],
                "boundary_axis_evidence": weighted_boundary_axes,
                "uncertainty": "boundary weight is mean(walk_block, see_block, grouping_strength); not perception-calibrated",
            }
        )
        length_weighted_boundary_axes = [
            _length_weighted_boundary_axis_descriptor(boundary)
            for boundary in scene.get("boundaries", [])
        ]
        rows.append(
            {
                "view_id": "whole_space_force",
                "metric": "length_weighted_boundary_axis_concentration",
                "score": round(_weighted_axis_consistency(length_weighted_boundary_axes), 4),
                "status": "computed",
                "method": "boundary_axis_weighted_by_length_walk_see_grouping_strength",
                "evidence": [item["id"] for item in length_weighted_boundary_axes],
                "boundary_axis_evidence": length_weighted_boundary_axes,
                "uncertainty": "influence is boundary length times authored channel weight; curved length/thickness calibration pending",
            }
        )
        thickness_weighted_boundary_axes = [
            _thickness_weighted_boundary_axis_descriptor(boundary)
            for boundary in scene.get("boundaries", [])
        ]
        rows.append(
            {
                "view_id": "whole_space_force",
                "metric": "thickness_weighted_boundary_axis_concentration",
                "score": round(_weighted_axis_consistency(thickness_weighted_boundary_axes), 4),
                "status": "computed",
                "method": "boundary_axis_weighted_by_length_thickness_walk_see_grouping_strength",
                "evidence": [item["id"] for item in thickness_weighted_boundary_axes],
                "boundary_axis_evidence": thickness_weighted_boundary_axes,
                "uncertainty": "influence is boundary length times thickness times authored channel weight; BIM thickness calibration pending",
            }
        )
    return rows


def _path_graph(scene: dict) -> dict:
    nodes = []
    edges = []
    for kind, records in (
        ("entry", scene.get("entries", [])),
        ("path", scene.get("paths", [])),
        ("region", scene.get("regions", [])),
    ):
        for record in records:
            rect = record["rect"]
            nodes.append(
                {
                    "id": _node_id(kind, record),
                    "kind": kind,
                    "ref_id": record["id"],
                    "point": (round(rect.cx, 4), round(rect.cy, 4)),
                }
            )

    for entry in scene.get("entries", []):
        for path in scene.get("paths", []):
            if _rects_touch(entry["rect"], path["rect"]):
                edges.append(_graph_edge("entry_path_touch", entry, path, "entry", "path"))
    for path in scene.get("paths", []):
        for region in scene.get("regions", []):
            if _rects_touch(path["rect"], region["rect"]):
                edges.append(_graph_edge("path_region_touch", path, region, "path", "region"))
    return {"nodes": nodes, "edges": edges}


def _modal_path_graphs(scene: dict, graph: dict) -> dict:
    costs = _modal_graph_costs(scene)
    graphs = {}
    for mode, cost in costs.items():
        mode_graph = {
            "nodes": graph["nodes"],
            "edges": [
                edge | {
                    "id": f"{edge['id']}_{mode}",
                    "mode": mode,
                    f"{mode}_cost": round(cost, 4),
                }
                for edge in graph["edges"]
            ],
        }
        mode_graph["metrics"] = _graph_metrics(mode_graph)
        graphs[mode] = mode_graph
    return graphs


def _modal_graph_costs(scene: dict) -> dict[str, float]:
    records = scene.get("boundaries", []) + scene.get("entries", [])
    if not records:
        return {"walk": 0.0, "visibility": 0.0}
    return {
        "walk": mean(record["weights"]["walk_block"] for record in records),
        "visibility": mean(record["weights"]["see_block"] for record in records),
    }


def _path_geometry(scene: dict) -> dict:
    blockers = _path_clearance_blockers(scene)
    return {
        path["id"]: _path_geometry_descriptor(path, blockers)
        for path in scene.get("paths", [])
    }


def _sampled_walkable_space(scene: dict, resolution: float | None = None) -> dict:
    width, height = scene["size"]
    resolution_descriptor = _sampled_grid_resolution(scene)
    if resolution is not None:
        resolution_descriptor = {
            "value": resolution,
            "basis": "explicit_override",
            "evidence": [],
        }
    resolution = resolution_descriptor["value"]
    grid = SpatialGridBackend(width=width, height=height, resolution=resolution)
    domain_cells = _sampled_domain_cells(grid, scene)
    blockers = _sampled_blockers(scene, "walk_block")
    blocker_ids = _mark_sampled_blockers(grid, blockers)

    entry_cells = sorted({
        cell
        for entry in scene.get("entries", [])
        for cell in _seed_cells_for_record(grid, entry, domain_cells)
        if cell in domain_cells
    })
    entry_distances = _sampled_bfs_distances(grid, entry_cells, domain_cells)
    for row, col in entry_distances:
        grid.cells[row][col].reachable = True
    visibility_grid = SpatialGridBackend(width=width, height=height, resolution=resolution)
    visibility_blockers = _sampled_blockers(scene, "see_block")
    visibility_blocker_ids = _mark_sampled_blockers(visibility_grid, visibility_blockers)
    visibility_entry_cells = sorted({
        cell
        for entry in scene.get("entries", [])
        for cell in _seed_cells_for_record(visibility_grid, entry, domain_cells)
        if cell in domain_cells
    })
    visibility_distances = _sampled_bfs_distances(
        visibility_grid,
        visibility_entry_cells,
        domain_cells,
    )

    total_cells = grid.n_rows * grid.n_cols
    blocked_cells = sum(
        1
        for row, col in domain_cells
        if not grid.free(row, col)
    )
    reachable_cells = sum(
        1
        for row, col in domain_cells
        if grid.cells[row][col].reachable
    )
    walkable_cells = len(domain_cells) - blocked_cells
    components = _sampled_walkable_components(grid, domain_cells)
    entry_reachable_components = [
        component
        for component in components
        if any(grid.cells[row][col].reachable for row, col in component)
    ]
    path_cells = {
        cell
        for path in scene.get("paths", [])
        for cell in _cells_for_record(grid, path)
        if cell in domain_cells and grid.free(*cell)
    }
    reachable_path_cells = {
        cell for cell in path_cells if grid.cells[cell[0]][cell[1]].reachable
    }
    region_reachability = [
        _record_reachability(
            grid,
            region,
            path_cells,
            domain_cells,
            entry_distances,
            visibility_distances,
        )
        for region in scene.get("regions", [])
    ]
    sampled_region_pair_evidence = _sampled_entry_reachable_region_pair_evidence(
        entry_reachable_components,
        region_reachability,
    )
    sampled_unreachable_region_pair_evidence = _sampled_unreachable_region_pair_evidence(
        region_reachability,
        sampled_region_pair_evidence,
    )
    sampled_visibility_region_pair_evidence = (
        _sampled_visibility_reachable_region_pair_evidence(region_reachability)
    )
    sampled_visibility_unreachable_region_pair_evidence = (
        _sampled_visibility_unreachable_region_pair_evidence(
            region_reachability,
            sampled_visibility_region_pair_evidence,
        )
    )
    sampled_pair_contrast = _sampled_region_pair_channel_contrast(
        sampled_region_pair_evidence,
        sampled_visibility_region_pair_evidence,
    )
    sampled_total_region_pairs = len(list(combinations(region_reachability, 2)))
    entry_region_distances = [
        {
            "region_id": item["region_id"],
            "distance_steps": item["entry_distance_steps"],
            "distance": item["entry_distance"],
        }
        for item in region_reachability
    ]
    visibility_region_distances = [
        {
            "region_id": item["region_id"],
            "distance_steps": item["visibility_distance_steps"],
            "distance": item["visibility_distance"],
        }
        for item in region_reachability
    ]
    region_pair_grid_distances = _sampled_region_pair_grid_distances(
        grid,
        domain_cells,
        region_reachability,
    )
    entry_region_widest_clearance_paths = _sampled_entry_region_widest_clearance_paths(
        grid,
        domain_cells,
        entry_cells,
        blockers,
        region_reachability,
    )
    reachable_region_distances = [
        item["distance"]
        for item in entry_region_distances
        if item["distance"] is not None
    ]
    reachable_region_steps = [
        item["distance_steps"]
        for item in entry_region_distances
        if item["distance_steps"] is not None
    ]
    visible_region_distances = [
        item["distance"]
        for item in visibility_region_distances
        if item["distance"] is not None
    ]
    visible_region_steps = [
        item["distance_steps"]
        for item in visibility_region_distances
        if item["distance_steps"] is not None
    ]
    reachable_region_pair_distances = [
        item["distance"]
        for item in region_pair_grid_distances
        if item["distance"] is not None
    ]
    reachable_region_pair_steps = [
        item["distance_steps"]
        for item in region_pair_grid_distances
        if item["distance_steps"] is not None
    ]
    reachable_region_widest_clearances = [
        item["widest_clearance"]
        for item in entry_region_widest_clearance_paths
        if item["widest_clearance"] is not None
    ]
    entry_region_clearance_per_distance = [
        item["widest_clearance"] / max(item["distance"] or 0.0, resolution)
        for item in entry_region_widest_clearance_paths
        if item["widest_clearance"] is not None
    ]
    clearance = _sampled_clearance_to_walk_blockers(
        grid,
        domain_cells,
        blockers,
        method="sampled_free_cell_center_to_nearest_walk_blocker_gap",
    )
    entry_reachable_clearance = _sampled_clearance_to_walk_blockers(
        grid,
        domain_cells,
        blockers,
        method="sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap",
        candidate_cells=set(entry_distances),
    )
    resolution_sensitivity = (
        _sampled_resolution_sensitivity(scene, resolution)
        if resolution_descriptor["basis"] != "explicit_override"
        else None
    )
    return {
        "resolution": float(resolution),
        "resolution_basis": resolution_descriptor["basis"],
        "resolution_evidence": resolution_descriptor["evidence"],
        "resolution_sensitivity": resolution_sensitivity,
        "total_cells": total_cells,
        "domain_cells": len(domain_cells),
        "outside_domain_cells": total_cells - len(domain_cells),
        "blocked_cells": blocked_cells,
        "walkable_cells": walkable_cells,
        "reachable_cells": reachable_cells,
        "component_count": len(components),
        "component_sizes": [len(component) for component in components],
        "largest_component_cell_ratio": round(
            (len(components[0]) if components else 0) / max(1, walkable_cells),
            4,
        ),
        "entry_reachable_component_ratio": round(
            len(entry_reachable_components) / max(1, len(components)),
            4,
        ),
        "entry_seed_cells": entry_cells,
        "path_cells": sorted(path_cells),
        "reachable_path_cells": sorted(reachable_path_cells),
        "walkable_cell_ratio": round(walkable_cells / max(1, len(domain_cells)), 4),
        "entry_reachable_cell_ratio": round(reachable_cells / max(1, len(domain_cells)), 4),
        "entry_reachable_region_ratio": round(
            sum(1 for item in region_reachability if item["entry_reachable"]) / max(1, len(region_reachability)),
            4,
        ),
        "visibility_reachable_region_ratio": round(
            sum(1 for item in region_reachability if item["visibility_reachable"]) / max(1, len(region_reachability)),
            4,
        ),
        "visibility_only_region_ratio": round(
            sum(
                1
                for item in region_reachability
                if item["visibility_reachable"] and not item["entry_reachable"]
            )
            / max(1, len(region_reachability)),
            4,
        ),
        "walk_only_region_ratio": round(
            sum(
                1
                for item in region_reachability
                if item["entry_reachable"] and not item["visibility_reachable"]
            )
            / max(1, len(region_reachability)),
            4,
        ),
        "walk_visibility_disagreement_region_ratio": round(
            sum(
                1
                for item in region_reachability
                if item["entry_reachable"] != item["visibility_reachable"]
            )
            / max(1, len(region_reachability)),
            4,
        ),
        "visibility_region_grid_distances": visibility_region_distances,
        "mean_visibility_region_grid_steps": round(mean(visible_region_steps), 4)
        if visible_region_steps
        else None,
        "mean_visibility_region_grid_distance": round(mean(visible_region_distances), 4)
        if visible_region_distances
        else None,
        "entry_region_grid_distances": entry_region_distances,
        "mean_entry_region_grid_steps": round(mean(reachable_region_steps), 4)
        if reachable_region_steps
        else None,
        "mean_entry_region_grid_distance": round(mean(reachable_region_distances), 4)
        if reachable_region_distances
        else None,
        "region_pair_grid_distances": region_pair_grid_distances,
        "entry_region_widest_clearance_paths": entry_region_widest_clearance_paths,
        "mean_entry_region_widest_clearance": round(
            mean(reachable_region_widest_clearances),
            4,
        )
        if reachable_region_widest_clearances
        else None,
        "mean_entry_region_clearance_per_distance": round(
            mean(entry_region_clearance_per_distance),
            4,
        )
        if entry_region_clearance_per_distance
        else None,
        "mean_region_pair_grid_steps": round(mean(reachable_region_pair_steps), 4)
        if reachable_region_pair_steps
        else None,
        "mean_region_pair_grid_distance": round(
            mean(reachable_region_pair_distances),
            4,
        )
        if reachable_region_pair_distances
        else None,
        "path_reachable_region_ratio": round(
            sum(1 for item in region_reachability if item["path_reachable"]) / max(1, len(region_reachability)),
            4,
        ),
        "sampled_entry_reachable_region_pair_ratio": round(
            len(sampled_region_pair_evidence) / max(1, sampled_total_region_pairs),
            4,
        ),
        "sampled_entry_reachable_region_pair_evidence": sampled_region_pair_evidence,
        "sampled_unreachable_region_pair_evidence": (
            sampled_unreachable_region_pair_evidence
        ),
        "sampled_visibility_reachable_region_pair_ratio": round(
            len(sampled_visibility_region_pair_evidence)
            / max(1, sampled_total_region_pairs),
            4,
        ),
        "sampled_visibility_reachable_region_pair_evidence": (
            sampled_visibility_region_pair_evidence
        ),
        "sampled_visibility_unreachable_region_pair_evidence": (
            sampled_visibility_unreachable_region_pair_evidence
        ),
        "sampled_visibility_only_region_pair_ratio": round(
            len(sampled_pair_contrast["visibility_only"])
            / max(1, sampled_total_region_pairs),
            4,
        ),
        "sampled_walk_only_region_pair_ratio": round(
            len(sampled_pair_contrast["walk_only"])
            / max(1, sampled_total_region_pairs),
            4,
        ),
        "sampled_walk_visibility_disagreement_region_pair_ratio": round(
            len(sampled_pair_contrast["disagreement"])
            / max(1, sampled_total_region_pairs),
            4,
        ),
        "sampled_visibility_only_region_pair_evidence": (
            sampled_pair_contrast["visibility_only"]
        ),
        "sampled_walk_only_region_pair_evidence": sampled_pair_contrast["walk_only"],
        "sampled_walk_visibility_disagreement_region_pair_evidence": (
            sampled_pair_contrast["disagreement"]
        ),
        "region_reachability": region_reachability,
        "blocker_evidence": blocker_ids,
        "visibility_blocker_evidence": visibility_blocker_ids,
        "sampled_clearance_to_walk_blockers": clearance,
        "entry_reachable_clearance_to_walk_blockers": entry_reachable_clearance,
        "method": "sampled_occupancy_grid_bfs_proxy",
        "uncertainty": "sampled occupancy grid proxy; not CAD boolean negative space or a navigation mesh",
    }


def _sampled_grid_resolution(scene: dict) -> dict:
    candidates = sorted(
        (
            min(record["rect"].width, record["rect"].height),
            record["id"],
        )
        for record in scene.get("objects", [])
        if record["rect"].width > 1e-9 and record["rect"].height > 1e-9
    )
    if not candidates:
        return {"value": 50.0, "basis": "no_measurable_furniture_fallback", "evidence": []}
    value = candidates[len(candidates) // 2][0]
    return {
        "value": value,
        "basis": "median_shortest_furniture_side",
        "evidence": [record_id for side, record_id in candidates if side == value],
    }


def _sampled_resolution_sensitivity(scene: dict, base_resolution: float) -> dict:
    resolutions = sorted({
        max(base_resolution / 2, 1e-9),
        base_resolution,
        base_resolution * 2,
    })
    summaries = [
        _sampled_metric_summary(scene, resolution)
        for resolution in resolutions
    ]
    return {
        "tested_resolutions": [
            float(round(resolution, 4))
            for resolution in resolutions
        ],
        "entry_reachable_cell_ratio_range": _summary_range(
            summaries,
            "entry_reachable_cell_ratio",
        ),
        "entry_reachable_region_ratio_range": _summary_range(
            summaries,
            "entry_reachable_region_ratio",
        ),
        "path_reachable_region_ratio_range": _summary_range(
            summaries,
            "path_reachable_region_ratio",
        ),
    }


def _sampled_metric_summary(scene: dict, resolution: float) -> dict:
    width, height = scene["size"]
    grid = SpatialGridBackend(width=width, height=height, resolution=resolution)
    domain_cells = _sampled_domain_cells(grid, scene)
    _mark_sampled_blockers(grid, _sampled_blockers(scene, "walk_block"))
    entry_cells = sorted({
        cell
        for entry in scene.get("entries", [])
        for cell in _seed_cells_for_record(grid, entry, domain_cells)
        if cell in domain_cells
    })
    entry_distances = _sampled_bfs_distances(grid, entry_cells, domain_cells)
    for row, col in entry_distances:
        grid.cells[row][col].reachable = True
    path_cells = {
        cell
        for path in scene.get("paths", [])
        for cell in _cells_for_record(grid, path)
        if cell in domain_cells and grid.free(*cell)
    }
    region_reachability = [
        _record_reachability(
            grid,
            region,
            path_cells,
            domain_cells,
            entry_distances,
            {},
        )
        for region in scene.get("regions", [])
    ]
    reachable_cells = sum(
        1
        for row, col in domain_cells
        if grid.cells[row][col].reachable
    )
    return {
        "entry_reachable_cell_ratio": round(
            reachable_cells / max(1, len(domain_cells)),
            4,
        ),
        "entry_reachable_region_ratio": round(
            sum(1 for item in region_reachability if item["entry_reachable"])
            / max(1, len(region_reachability)),
            4,
        ),
        "path_reachable_region_ratio": round(
            sum(1 for item in region_reachability if item["path_reachable"])
            / max(1, len(region_reachability)),
            4,
        ),
    }


def _summary_range(summaries: list[dict], key: str) -> float:
    values = [summary[key] for summary in summaries]
    return round(max(values) - min(values), 4)


def _sampled_blockers(scene: dict, weight_key: str) -> list[dict]:
    room_area = scene["size"][0] * scene["size"][1]
    blockers = list(scene.get("objects", []))
    for boundary in scene.get("boundaries", []):
        kind = boundary.get("metadata", {}).get("boundary-kind")
        if kind == "room":
            continue
        if boundary["rect"].area >= room_area * 0.5:
            continue
        if boundary["weights"][weight_key] <= 0:
            continue
        blockers.append(boundary)
    return blockers


def _sampled_clearance_to_walk_blockers(
    grid: SpatialGridBackend,
    domain_cells: set[tuple[int, int]],
    blockers: list[dict],
    *,
    method: str,
    candidate_cells: set[tuple[int, int]] | None = None,
) -> dict:
    blocker_shapes = [
        (blocker["id"], _record_shape(blocker))
        for blocker in blockers
    ]
    samples = []
    cells = domain_cells if candidate_cells is None else domain_cells & candidate_cells
    for row, col in sorted(cells):
        if not grid.free(row, col):
            continue
        point = grid.cell_center(row, col)
        if not blocker_shapes:
            continue
        blocker_id, distance = min(
            (
                (blocker_id, _point_to_shape_gap(point, shape))
                for blocker_id, shape in blocker_shapes
            ),
            key=lambda item: (item[1], item[0]),
        )
        samples.append(
            {
                "cell": (row, col),
                "point": (round(point[0], 4), round(point[1], 4)),
                "blocker_id": blocker_id,
                "distance": round(distance, 4),
            }
        )
    distances = [sample["distance"] for sample in samples]
    min_clearance = min(distances) if distances else None
    return {
        "method": method,
        "min_clearance": min_clearance,
        "mean_clearance": round(mean(distances), 4) if distances else None,
        "sample_count": len(distances),
        "zero_clearance_sample_count": sum(
            1 for distance in distances if distance <= 1e-9
        ),
        "min_clearance_samples": [
            sample for sample in samples if sample["distance"] == min_clearance
        ][:5],
        "blocker_evidence": [blocker_id for blocker_id, _ in blocker_shapes],
    }


def _point_to_shape_gap(point: tuple[float, float], shape: Rect | Polygon) -> float:
    if isinstance(shape, Polygon):
        if shape.contains_point(*point):
            return 0.0
        points = list(shape.points)
        return min(
            _point_segment_distance(point, start, end)
            for start, end in _closed_edges(points)
        )
    return _rect_gap(Rect(cx=point[0], cy=point[1], width=0.0, height=0.0), shape)


def _mark_sampled_blockers(
    grid: SpatialGridBackend,
    blockers: list[dict],
) -> list[str]:
    blocker_ids = []
    for blocker in blockers:
        blocker_ids.append(blocker["id"])
        grid.mark_occupied(blocker["id"], _record_shape(blocker))
    return blocker_ids


def _path_geometry_descriptor(path: dict, blockers: list[dict]) -> dict:
    points = path.get("points") or []
    lengths = [
        ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    ]
    if lengths and points[:1] != points[-1:]:
        x1, y1 = points[-1]
        x2, y2 = points[0]
        lengths.append(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    lengths = [length for length in lengths if length > 1e-9]
    width_samples = [
        round(min(a, b), 4)
        for a, b in zip(lengths, lengths[1:] + lengths[:1])
        if min(a, b) > 1e-9
    ][::2]
    clearance_samples = _path_clearance_samples(path, blockers)
    clearance_values = [sample["distance"] for sample in clearance_samples]
    overlap_count = sum(1 for value in clearance_values if value <= 1e-9)
    path_polygon = _path_polygon(path)
    path_area = path_polygon.area if path_polygon is not None else path["rect"].area
    blocker_overlap_samples = _path_blocker_overlap_samples(
        path,
        path_polygon,
        blockers,
    )
    summed_blocker_overlap_area = sum(sample["area"] for sample in blocker_overlap_samples)
    blocker_overlap_area = _blocker_union_overlap_area(
        blockers,
        path["rect"],
        path_polygon,
    )
    return {
        "width_samples": width_samples,
        "width_continuity": round(_cv_score(width_samples), 4),
        "clearance_samples": clearance_samples,
        "min_clearance_to_blocker": min(clearance_values) if clearance_values else None,
        "mean_clearance_to_blocker": round(mean(clearance_values), 4)
        if clearance_values
        else None,
        "blocker_overlap_count": overlap_count,
        "blocker_overlap_ratio": round(overlap_count / len(clearance_values), 4)
        if clearance_values
        else None,
        "blocker_overlap_samples": blocker_overlap_samples,
        "path_polygon_area": round(path_area, 4),
        "blocker_overlap_area": round(blocker_overlap_area, 4),
        "summed_blocker_overlap_area": round(summed_blocker_overlap_area, 4),
        "blocker_overlap_area_ratio": round(
            min(path_area, blocker_overlap_area) / path_area,
            4,
        )
        if path_area > 1e-9
        else None,
    }


def _path_clearance_blockers(scene: dict) -> list[dict]:
    room_area = scene["size"][0] * scene["size"][1]
    blockers = list(scene.get("objects", []))
    for boundary in scene.get("boundaries", []):
        kind = boundary.get("metadata", {}).get("boundary-kind")
        if kind == "room":
            continue
        if boundary["rect"].area >= room_area * 0.5:
            continue
        if boundary["weights"]["walk_block"] <= 0:
            continue
        blockers.append(boundary)
    return blockers


def _path_clearance_samples(path: dict, blockers: list[dict]) -> list[dict]:
    samples = [
        {
            "target_id": blocker["id"],
            "target_role": blocker["role"],
            "distance": round(_path_record_gap(path, blocker["rect"]), 4),
        }
        for blocker in blockers
        if blocker["id"] != path["id"]
    ]
    return sorted(samples, key=lambda sample: (sample["distance"], sample["target_id"]))


def _path_record_gap(path: dict, rect) -> float:
    points = path.get("points") or []
    if len(points) < 2:
        return _rect_gap(path["rect"], rect)
    return _polygon_rect_gap(points, rect)


def _record_shape(record: dict) -> Rect | Polygon:
    polygon = _path_polygon(record)
    return polygon if polygon is not None else record["rect"]


def _sampled_domain_cells(
    grid: SpatialGridBackend,
    scene: dict,
) -> set[tuple[int, int]]:
    room = _room_boundary(scene)
    if room is None:
        return {
            (row, col)
            for row in range(grid.n_rows)
            for col in range(grid.n_cols)
        }
    cells = set(_cells_for_record(grid, room))
    return cells or {
        (row, col)
        for row in range(grid.n_rows)
        for col in range(grid.n_cols)
    }


def _sampled_walkable_components(
    grid: SpatialGridBackend,
    domain_cells: set[tuple[int, int]],
) -> list[list[tuple[int, int]]]:
    unseen = {cell for cell in domain_cells if grid.free(*cell)}
    components = []
    while unseen:
        start = unseen.pop()
        component = [start]
        queue = deque([start])
        while queue:
            row, col = queue.popleft()
            for next_cell in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if next_cell not in unseen:
                    continue
                unseen.remove(next_cell)
                component.append(next_cell)
                queue.append(next_cell)
        components.append(sorted(component))
    return sorted(components, key=lambda component: (-len(component), component))


def _sampled_entry_reachable_region_pair_evidence(
    entry_reachable_components: list[list[tuple[int, int]]],
    region_reachability: list[dict],
) -> list[dict]:
    regions_by_component = {}
    for index, component in enumerate(entry_reachable_components):
        component_cells = set(component)
        regions_by_component[index] = sorted(
            item["region_id"]
            for item in region_reachability
            if component_cells & set(item["sampled_cells"])
        )
    pair_components = {}
    for component, region_ids in regions_by_component.items():
        for region_a, region_b in combinations(region_ids, 2):
            pair_components.setdefault((region_a, region_b), []).append(component)
    return [
        {
            "components": components,
            "region_a": region_a,
            "region_b": region_b,
        }
        for (region_a, region_b), components in sorted(pair_components.items())
    ]


def _sampled_unreachable_region_pair_evidence(
    region_reachability: list[dict],
    connected_pair_evidence: list[dict],
) -> list[dict]:
    connected_pairs = {
        (item["region_a"], item["region_b"])
        for item in connected_pair_evidence
    }
    return [
        {"region_a": region_a, "region_b": region_b}
        for region_a, region_b in combinations(
            sorted(item["region_id"] for item in region_reachability),
            2,
        )
        if (region_a, region_b) not in connected_pairs
    ]


def _sampled_visibility_reachable_region_pair_evidence(
    region_reachability: list[dict],
) -> list[dict]:
    visible_regions = sorted(
        item["region_id"]
        for item in region_reachability
        if item["visibility_reachable"]
    )
    return [
        {"regions": [region_a, region_b]}
        for region_a, region_b in combinations(visible_regions, 2)
    ]


def _sampled_visibility_unreachable_region_pair_evidence(
    region_reachability: list[dict],
    connected_pair_evidence: list[dict],
) -> list[dict]:
    connected_pairs = {
        tuple(item["regions"])
        for item in connected_pair_evidence
    }
    return [
        {"regions": [region_a, region_b]}
        for region_a, region_b in combinations(
            sorted(item["region_id"] for item in region_reachability),
            2,
        )
        if (region_a, region_b) not in connected_pairs
    ]


def _sampled_region_pair_channel_contrast(
    walk_pair_evidence: list[dict],
    visibility_pair_evidence: list[dict],
) -> dict[str, list[dict]]:
    walk_pairs = {
        (item["region_a"], item["region_b"])
        for item in walk_pair_evidence
    }
    visibility_pairs = {
        tuple(item["regions"])
        for item in visibility_pair_evidence
    }
    visibility_only = sorted(visibility_pairs - walk_pairs)
    walk_only = sorted(walk_pairs - visibility_pairs)
    return {
        "visibility_only": [
            {"region_a": region_a, "region_b": region_b}
            for region_a, region_b in visibility_only
        ],
        "walk_only": [
            {"region_a": region_a, "region_b": region_b}
            for region_a, region_b in walk_only
        ],
        "disagreement": [
            {"region_a": region_a, "region_b": region_b}
            for region_a, region_b in sorted(set(visibility_only) | set(walk_only))
        ],
    }


def _sampled_region_pair_grid_distances(
    grid: SpatialGridBackend,
    domain_cells: set[tuple[int, int]],
    region_reachability: list[dict],
) -> list[dict]:
    results = []
    for left, right in combinations(region_reachability, 2):
        left_cells = left["sampled_cells"]
        right_cells = set(right["sampled_cells"])
        distances = _sampled_bfs_distances(grid, left_cells, domain_cells)
        distance_steps = min(
            (distances[cell] for cell in right_cells if cell in distances),
            default=None,
        )
        results.append(
            {
                "region_a": left["region_id"],
                "region_b": right["region_id"],
                "distance_steps": distance_steps,
                "distance": round(distance_steps * grid.resolution, 4)
                if distance_steps is not None
                else None,
            }
        )
    return results


def _sampled_entry_region_widest_clearance_paths(
    grid: SpatialGridBackend,
    domain_cells: set[tuple[int, int]],
    entry_cells: list[tuple[int, int]],
    blockers: list[dict],
    region_reachability: list[dict],
) -> list[dict]:
    widest, previous = _sampled_widest_clearance_from_starts(
        grid,
        entry_cells,
        domain_cells,
        blockers,
    )
    results = []
    for region in region_reachability:
        region_cells = set(region["sampled_cells"])
        target_cell = min(
            (cell for cell in region_cells if cell in widest),
            key=lambda cell: (-widest[cell], cell),
            default=None,
        )
        clearance = widest[target_cell] if target_cell is not None else None
        result = {
            "region_id": region["region_id"],
            "widest_clearance": round(clearance, 4)
            if clearance is not None
            else None,
            "distance_steps": region["entry_distance_steps"],
            "distance": region["entry_distance"],
        }
        if target_cell is not None:
            path_cells = _sampled_reconstruct_path(previous, target_cell)
            result["path_cells"] = path_cells[:32]
            if len(path_cells) > 32:
                result["path_truncated"] = True
        results.append(result)
    return results


def _sampled_widest_clearance_from_starts(
    grid: SpatialGridBackend,
    starts: list[tuple[int, int]],
    domain_cells: set[tuple[int, int]],
    blockers: list[dict],
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], tuple[int, int] | None]]:
    blocker_shapes = [
        (blocker["id"], _record_shape(blocker))
        for blocker in blockers
    ]
    clearances = {}
    for row, col in sorted(domain_cells):
        if not grid.free(row, col) or not blocker_shapes:
            continue
        point = grid.cell_center(row, col)
        clearances[(row, col)] = min(
            _point_to_shape_gap(point, shape)
            for _, shape in blocker_shapes
        )
    best = {}
    previous = {}
    queue = []
    for cell in sorted(starts):
        if cell not in clearances:
            continue
        best[cell] = clearances[cell]
        previous[cell] = None
        heappush(queue, (-clearances[cell], cell))
    while queue:
        neg_clearance, cell = heappop(queue)
        clearance = -neg_clearance
        if clearance < best.get(cell, -1.0):
            continue
        row, col = cell
        for next_cell in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if next_cell not in clearances:
                continue
            candidate = min(clearance, clearances[next_cell])
            if candidate <= best.get(next_cell, -1.0):
                continue
            best[next_cell] = candidate
            previous[next_cell] = cell
            heappush(queue, (-candidate, next_cell))
    return best, previous


def _sampled_reconstruct_path(
    previous: dict[tuple[int, int], tuple[int, int] | None],
    target_cell: tuple[int, int],
) -> list[tuple[int, int]]:
    path = []
    cell = target_cell
    while cell is not None:
        path.append(cell)
        cell = previous.get(cell)
    return list(reversed(path))


def _sampled_bfs_distances(
    grid: SpatialGridBackend,
    starts: list[tuple[int, int]],
    domain_cells: set[tuple[int, int]],
) -> dict[tuple[int, int], int]:
    distances = {}
    queue = deque()
    for cell in starts:
        if cell not in domain_cells or not grid.free(*cell) or cell in distances:
            continue
        distances[cell] = 0
        queue.append(cell)
    while queue:
        row, col = queue.popleft()
        for next_cell in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if next_cell not in domain_cells or next_cell in distances:
                continue
            if not grid.free(*next_cell):
                continue
            distances[next_cell] = distances[(row, col)] + 1
            queue.append(next_cell)
    return distances


def _room_boundary(scene: dict) -> dict | None:
    return next(
        (
            boundary
            for boundary in scene.get("boundaries", [])
            if boundary.get("metadata", {}).get("boundary-kind") == "room"
        ),
        None,
    )


def _negative_space_descriptor(
    scene: dict,
    *,
    regions: list[dict] | None = None,
) -> dict:
    room = _room_boundary(scene)
    room_polygon = _path_polygon(room) if room is not None else None
    room_rect = room["rect"] if room is not None else Rect(
        cx=scene["size"][0] / 2,
        cy=scene["size"][1] / 2,
        width=scene["size"][0],
        height=scene["size"][1],
    )
    room_area = room_polygon.area if room_polygon is not None else room_rect.area
    if room_area <= 1e-9:
        return {
            "status": "not_available",
            "room_area": 0.0,
            "blocker_overlap_area": 0.0,
            "negative_space_area": None,
            "negative_space_area_ratio_proxy": None,
            "blocker_evidence": [],
            "method": "room_polygon_minus_summed_blocker_bbox_overlap_area_proxy",
            "uncertainty": "needs a measurable room boundary before estimating negative space",
        }

    samples = []
    blockers = _path_clearance_blockers(scene)
    for blocker in blockers:
        area = _record_overlap_area(blocker, room_polygon, room_rect)
        if area <= 1e-9:
            continue
        samples.append(
            {
                "target_id": blocker["id"],
                "target_role": blocker["role"],
                "area": round(area, 4),
            }
        )
    samples = sorted(samples, key=lambda sample: (-sample["area"], sample["target_id"]))
    summed_blocker_overlap_area = sum(sample["area"] for sample in samples)
    polygon_overlap_risk = _polygon_blocker_overlap_risk_evidence(blockers)
    blocker_overlap_area = _blocker_union_overlap_area(
        blockers,
        room_rect,
        room_polygon,
    )
    negative_space_area = max(0.0, room_area - blocker_overlap_area)
    components = _negative_space_rect_components(
        room_rect,
        blockers,
        room_polygon,
    )
    component_areas = [round(sum(cell["area"] for cell in component), 4) for component in components]
    component_rects = _component_rect_evidence(components, component_areas)
    free_space_polygons = _free_space_polygon_evidence(components)
    free_space_polygon_adjacency = _free_space_polygon_adjacency_evidence(components)
    free_space_polygon_graph = _free_space_polygon_graph_evidence(
        scene,
        components,
        free_space_polygon_adjacency,
    )
    room_minus_blocker_polygons = _room_minus_blocker_polygon_evidence(components)
    cad_room_minus_blocker_polygons = _cad_room_minus_blocker_polygon_evidence(
        room_polygon,
        blockers,
    )
    cad_room_minus_blocker_component_touch_evidence = (
        _cad_room_minus_blocker_component_touch_evidence(
            cad_room_minus_blocker_polygons,
            scene.get("entries", []),
            regions if regions is not None else scene.get("regions", []),
        )
    )
    cad_room_minus_blocker_area_total = round(
        sum(item["area"] for item in cad_room_minus_blocker_polygons),
        4,
    )
    cad_room_minus_blocker_component_areas = [
        item["area"] for item in cad_room_minus_blocker_polygons
    ]
    cad_room_minus_blocker_largest_component_area = round(
        max(cad_room_minus_blocker_component_areas, default=0.0),
        4,
    )
    cad_room_minus_blocker_area_residual = round(
        cad_room_minus_blocker_area_total - round(negative_space_area, 4),
        4,
    )
    cad_entry_connected_component_ids = sorted(
        item["component_index"]
        for item in cad_room_minus_blocker_component_touch_evidence
        if item["entry_ids"]
    )
    cad_entry_connected_component_id_set = set(cad_entry_connected_component_ids)
    cad_non_entry_connected_component_ids = sorted(
        item["component_index"]
        for item in cad_room_minus_blocker_polygons
        if item["component_index"] not in cad_entry_connected_component_id_set
    )
    cad_entry_connected_component_area = round(
        sum(
            item["area"]
            for item in cad_room_minus_blocker_polygons
            if item["component_index"] in cad_entry_connected_component_id_set
        ),
        4,
    )
    cad_non_entry_connected_component_area = round(
        max(
            0.0,
            cad_room_minus_blocker_area_total - cad_entry_connected_component_area,
        ),
        4,
    )
    component_area = sum(component_areas)
    component_area_total = round(component_area, 4)
    component_cell_count_total = sum(item["cell_count"] for item in component_rects)
    component_cell_area_sum_total = round(
        sum(
            cell["area"]
            for item in component_rects
            for cell in item["cell_rects"]
        ),
        4,
    )
    negative_space_component_area_residual = round(
        round(negative_space_area, 4) - component_area_total,
        4,
    )
    entry_component_evidence = _entry_component_evidence(
        scene.get("entries", []),
        components,
        component_areas,
    )
    entry_connected_area = sum(
        item["area"] for item in entry_component_evidence if item["entry_ids"]
    )
    non_entry_connected_area = max(0.0, component_area - entry_connected_area)
    return {
        "status": "computed",
        "room_area": round(room_area, 4),
        "blocker_overlap_area": round(blocker_overlap_area, 4),
        "summed_blocker_overlap_area": round(summed_blocker_overlap_area, 4),
        "negative_space_area": round(negative_space_area, 4),
        "negative_space_area_ratio_proxy": round(negative_space_area / room_area, 4),
        "component_count": len(components),
        "component_areas": component_areas,
        "component_area_total": component_area_total,
        "component_cell_count_total": component_cell_count_total,
        "component_cell_area_sum_total": component_cell_area_sum_total,
        "negative_space_component_area_residual": negative_space_component_area_residual,
        "negative_space_component_area_residual_ratio": round(
            abs(negative_space_component_area_residual)
            / max(round(negative_space_area, 4), 1e-9),
            4,
        ),
        "component_rects": component_rects,
        "free_space_polygons": free_space_polygons,
        "free_space_polygon_adjacency": free_space_polygon_adjacency,
        "free_space_polygon_graph": free_space_polygon_graph,
        "room_minus_blocker_polygons": room_minus_blocker_polygons,
        "cad_room_minus_blocker_polygons": cad_room_minus_blocker_polygons,
        "cad_room_minus_blocker_component_touch_evidence": (
            cad_room_minus_blocker_component_touch_evidence
        ),
        "cad_room_minus_blocker_area_total": cad_room_minus_blocker_area_total,
        "cad_room_minus_blocker_component_areas": (
            cad_room_minus_blocker_component_areas
        ),
        "cad_room_minus_blocker_largest_component_area": (
            cad_room_minus_blocker_largest_component_area
        ),
        "cad_room_minus_blocker_largest_component_area_ratio": round(
            cad_room_minus_blocker_largest_component_area
            / max(cad_room_minus_blocker_area_total, 1e-9),
            4,
        ),
        "cad_room_minus_blocker_area_residual": cad_room_minus_blocker_area_residual,
        "cad_room_minus_blocker_area_residual_ratio": round(
            abs(cad_room_minus_blocker_area_residual)
            / max(round(negative_space_area, 4), 1e-9),
            4,
        ),
        "cad_room_minus_blocker_entry_connected_component_ids": (
            cad_entry_connected_component_ids
        ),
        "cad_room_minus_blocker_non_entry_connected_component_ids": (
            cad_non_entry_connected_component_ids
        ),
        "cad_room_minus_blocker_entry_connected_component_area": (
            cad_entry_connected_component_area
        ),
        "cad_room_minus_blocker_non_entry_connected_component_area": (
            cad_non_entry_connected_component_area
        ),
        "cad_room_minus_blocker_entry_connected_area_ratio": round(
            cad_entry_connected_component_area
            / max(cad_room_minus_blocker_area_total, 1e-9),
            4,
        ),
        "cad_room_minus_blocker_entry_connected_component_ratio": round(
            len(cad_entry_connected_component_ids)
            / max(len(cad_room_minus_blocker_polygons), 1),
            4,
        ),
        "largest_component_area_ratio": round(
            (component_areas[0] if component_areas else 0.0) / max(component_area, 1e-9),
            4,
        ),
        "entry_connected_component_count": sum(
            1 for item in entry_component_evidence if item["entry_ids"]
        ),
        "entry_connected_component_area": round(entry_connected_area, 4),
        "entry_connected_area_ratio": round(
            entry_connected_area / max(component_area, 1e-9),
            4,
        ),
        "non_entry_connected_component_area": round(non_entry_connected_area, 4),
        "non_entry_connected_area_ratio": round(
            non_entry_connected_area / max(component_area, 1e-9),
            4,
        ),
        "entry_component_evidence": entry_component_evidence,
        "components": components,
        "polygon_blocker_overlap_risk_evidence": polygon_overlap_risk,
        "component_method": "room_polygon_rect_cell_decomposition_proxy"
        if room_polygon is not None
        else "room_bbox_rect_cell_decomposition_proxy",
        "blocker_overlap_samples": samples,
        "blocker_evidence": [sample["target_id"] for sample in samples],
        "method": "room_polygon_minus_blocker_union_area_proxy",
        "uncertainty": "blocker union area via rect-cell decomposition inside room; still not CAD boolean negative space",
    }


def _blocker_union_overlap_area(
    blockers: list[dict],
    room_rect: Rect,
    room_polygon: Polygon | None,
) -> float:
    xs = {room_rect.left, room_rect.right}
    ys = {room_rect.top, room_rect.bottom}
    shapes = []
    seen_shapes = set()
    for blocker in blockers:
        overlap = _rect_intersection(room_rect, blocker["rect"])
        if overlap is None:
            continue
        xs.update((overlap.left, overlap.right))
        ys.update((overlap.top, overlap.bottom))
        shape = _record_shape(blocker)
        shape_key = _shape_key(shape)
        if shape_key in seen_shapes:
            continue
        seen_shapes.add(shape_key)
        shapes.append(shape)
    area = 0.0
    sorted_xs = sorted(xs)
    sorted_ys = sorted(ys)
    for left, right in zip(sorted_xs, sorted_xs[1:]):
        for top, bottom in zip(sorted_ys, sorted_ys[1:]):
            if right - left <= 1e-9 or bottom - top <= 1e-9:
                continue
            cell = Rect(
                cx=(left + right) / 2,
                cy=(top + bottom) / 2,
                width=right - left,
                height=bottom - top,
            )
            room_area = (
                _polygon_rect_overlap_area(room_polygon, cell)
                if room_polygon is not None
                else _rect_overlap_area(room_rect, cell)
            )
            if room_area <= 1e-9:
                continue
            blocked_area = min(
                room_area,
                sum(_shape_rect_overlap_area(shape, cell) for shape in shapes),
            )
            area += blocked_area
    return area


def _shape_key(shape: Rect | Polygon) -> tuple:
    if isinstance(shape, Polygon):
        return ("polygon", tuple((round(x, 9), round(y, 9)) for x, y in shape.points))
    return (
        "rect",
        round(shape.left, 9),
        round(shape.top, 9),
        round(shape.right, 9),
        round(shape.bottom, 9),
    )


def _polygon_blocker_overlap_risk_evidence(blockers: list[dict]) -> list[dict]:
    polygon_blockers = []
    for blocker in blockers:
        shape = _record_shape(blocker)
        if isinstance(shape, Polygon):
            polygon_blockers.append((blocker, shape))
    evidence = []
    for left_index, (left, left_shape) in enumerate(polygon_blockers):
        for right, right_shape in polygon_blockers[left_index + 1:]:
            if _shape_key(left_shape) == _shape_key(right_shape):
                continue
            if _rect_intersection(left_shape.bounds, right_shape.bounds) is None:
                continue
            if not _polygons_overlap(left_shape, right_shape):
                continue
            evidence.append(
                {
                    "blocker_a": left["id"],
                    "blocker_b": right["id"],
                    "reason": "nonidentical_polygon_blockers_overlap",
                }
            )
    return evidence


def _polygons_overlap(left: Polygon, right: Polygon) -> bool:
    left_points = list(left.points)
    right_points = list(right.points)
    return (
        any(
            _segments_intersect(a, b, c, d)
            for a, b in _closed_edges(left_points)
            for c, d in _closed_edges(right_points)
        )
        or any(_point_in_polygon(point, right_points) for point in left_points)
        or any(_point_in_polygon(point, left_points) for point in right_points)
    )


def _negative_space_rect_components(
    room_rect: Rect,
    blockers: list[dict],
    room_polygon: Polygon | None,
) -> list[list[dict]]:
    xs = {room_rect.left, room_rect.right}
    ys = {room_rect.top, room_rect.bottom}
    blocking_shapes = []
    seen_shapes = set()
    for blocker in blockers:
        overlap = _rect_intersection(room_rect, blocker["rect"])
        if overlap is None:
            continue
        shape = _record_shape(blocker)
        shape_key = _shape_key(shape)
        if shape_key in seen_shapes:
            continue
        seen_shapes.add(shape_key)
        blocking_shapes.append(shape)
        xs.update((overlap.left, overlap.right))
        ys.update((overlap.top, overlap.bottom))
    xs = sorted(xs)
    ys = sorted(ys)
    cells = []
    for left, right in zip(xs, xs[1:]):
        for top, bottom in zip(ys, ys[1:]):
            if right - left <= 1e-9 or bottom - top <= 1e-9:
                continue
            cell = Rect(
                cx=(left + right) / 2,
                cy=(top + bottom) / 2,
                width=right - left,
                height=bottom - top,
            )
            area = (
                _polygon_rect_overlap_area(room_polygon, cell)
                if room_polygon is not None
                else cell.area
            )
            blocker_area = sum(
                _shape_rect_overlap_area(blocker, cell)
                for blocker in blocking_shapes
            )
            free_area = max(0.0, area - blocker_area)
            if free_area <= 1e-9:
                continue
            cells.append({"rect": cell, "area": free_area})

    adjacency = {index: set() for index in range(len(cells))}
    for left_index, left in enumerate(cells):
        for right_index in range(left_index + 1, len(cells)):
            right = cells[right_index]
            if _rects_share_edge(left["rect"], right["rect"]):
                adjacency[left_index].add(right_index)
                adjacency[right_index].add(left_index)

    components = []
    unseen = set(range(len(cells)))
    while unseen:
        start = unseen.pop()
        component = [cells[start]]
        queue = deque([start])
        while queue:
            index = queue.popleft()
            for next_index in adjacency[index] & unseen:
                unseen.remove(next_index)
                component.append(cells[next_index])
                queue.append(next_index)
        components.append(component)
    return sorted(
        components,
        key=lambda component: (
            -sum(cell["area"] for cell in component),
            component[0]["rect"].left,
            component[0]["rect"].top,
        ),
    )


def _entry_component_evidence(
    entries: list[dict],
    components: list[list[dict]],
    component_areas: list[float],
) -> list[dict]:
    evidence = []
    for index, component in enumerate(components):
        entry_ids = sorted(
            entry["id"]
            for entry in entries
            if any(_rects_touch(entry["rect"], cell["rect"]) for cell in component)
        )
        evidence.append(
            {
                "component_index": index,
                "area": component_areas[index],
                "entry_ids": entry_ids,
            }
        )
    return evidence


def _component_rect_evidence(
    components: list[list[dict]],
    component_areas: list[float],
) -> list[dict]:
    evidence = []
    for index, component in enumerate(components):
        left = min(cell["rect"].left for cell in component)
        top = min(cell["rect"].top for cell in component)
        right = max(cell["rect"].right for cell in component)
        bottom = max(cell["rect"].bottom for cell in component)
        evidence.append(
            {
                "component_index": index,
                "bbox": (
                    round(left, 4),
                    round(top, 4),
                    round(right, 4),
                    round(bottom, 4),
                ),
                "cell_count": len(component),
                "area": component_areas[index],
                "cell_rects": [
                    {
                        "bbox": (
                            round(cell["rect"].left, 4),
                            round(cell["rect"].top, 4),
                            round(cell["rect"].right, 4),
                            round(cell["rect"].bottom, 4),
                        ),
                        "area": round(cell["area"], 4),
                    }
                    for cell in sorted(
                        component,
                        key=lambda cell: (cell["rect"].left, cell["rect"].top),
                    )
                ],
            }
        )
    return evidence


def _free_space_polygon_evidence(components: list[list[dict]]) -> list[dict]:
    evidence = []
    for component_index, component in enumerate(components):
        cells = sorted(component, key=lambda cell: (cell["rect"].left, cell["rect"].top))
        for cell_index, cell in enumerate(cells):
            rect = cell["rect"]
            evidence.append(
                {
                    "component_index": component_index,
                    "cell_index": cell_index,
                    "points": (
                        (round(rect.left, 4), round(rect.top, 4)),
                        (round(rect.right, 4), round(rect.top, 4)),
                        (round(rect.right, 4), round(rect.bottom, 4)),
                        (round(rect.left, 4), round(rect.bottom, 4)),
                    ),
                    "area": round(cell["area"], 4),
                }
            )
    return evidence


def _free_space_polygon_adjacency_evidence(components: list[list[dict]]) -> list[dict]:
    evidence = []
    for component_index, component in enumerate(components):
        cells = sorted(component, key=lambda cell: (cell["rect"].left, cell["rect"].top))
        for left_index, left in enumerate(cells):
            for right_index, right in enumerate(cells[left_index + 1:], start=left_index + 1):
                shared = _rect_shared_edge(left["rect"], right["rect"])
                if shared is None:
                    continue
                evidence.append(
                    {
                        "component_index": component_index,
                        "from_cell": left_index,
                        "to_cell": right_index,
                        "shared_edge": shared,
                        "length": round(
                            hypot(
                                shared[1][0] - shared[0][0],
                                shared[1][1] - shared[0][1],
                            ),
                            4,
                        ),
                    }
                )
    return evidence


def _free_space_polygon_graph_evidence(
    scene: dict,
    components: list[list[dict]],
    adjacency: list[dict],
) -> dict:
    nodes = []
    cells_by_key = {}
    for component_index, component in enumerate(components):
        cells = sorted(component, key=lambda cell: (cell["rect"].left, cell["rect"].top))
        for cell_index, cell in enumerate(cells):
            node_id = f"component_{component_index}_cell_{cell_index}"
            cells_by_key[(component_index, cell_index)] = cell
            nodes.append(
                {
                    "id": node_id,
                    "component_index": component_index,
                    "cell_index": cell_index,
                    "point": (
                        round(cell["rect"].cx, 4),
                        round(cell["rect"].cy, 4),
                    ),
                    "area": round(cell["area"], 4),
                }
            )
    edges = []
    for item in adjacency:
        component_index = item["component_index"]
        left_cell = cells_by_key[(component_index, item["from_cell"])]
        right_cell = cells_by_key[(component_index, item["to_cell"])]
        a = f"component_{component_index}_cell_{item['from_cell']}"
        b = f"component_{component_index}_cell_{item['to_cell']}"
        distance = round(
            hypot(
                left_cell["rect"].cx - right_cell["rect"].cx,
                left_cell["rect"].cy - right_cell["rect"].cy,
            ),
            4,
        )
        edges.append(
            {
                "id": f"edge_{a}_{b}",
                "component_index": component_index,
                "a": a,
                "b": b,
                "shared_edge": item["shared_edge"],
                "length": item["length"],
                "clearance_width": item["length"],
                "weight": distance,
                "distance": distance,
            }
        )
    return {
        "method": "room_polygon_rect_cell_shared_edge_graph_proxy",
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "metrics": _free_space_polygon_graph_metrics(nodes, edges),
        "anchors": _free_space_polygon_graph_anchors(scene, components),
        "entry_region_distance_evidence": (
            _free_space_polygon_graph_entry_region_distance_evidence(
                scene,
                components,
            )
        ),
        "entry_region_widest_path_evidence": (
            _free_space_polygon_graph_entry_region_widest_path_evidence(
                scene,
                components,
            )
        ),
        "uncertainty": "shared-edge graph over rect-cell free-space polygons; proxy, not navmesh or medial-axis topology",
    }


def _free_space_polygon_graph_metrics(nodes: list[dict], edges: list[dict]) -> dict:
    node_ids = {node["id"] for node in nodes}
    adjacency = {node_id: set() for node_id in node_ids}
    for edge in edges:
        adjacency.setdefault(edge["a"], set()).add(edge["b"])
        adjacency.setdefault(edge["b"], set()).add(edge["a"])
    components = _components({node_id: {} for node_id in node_ids}, adjacency)
    dead_end_nodes = sorted(
        node_id for node_id in node_ids if len(adjacency.get(node_id, ())) <= 1
    )
    return {
        "component_count": len(components),
        "cycle_rank": max(0, len(edges) - len(nodes) + len(components)),
        "dead_end_node_count": len(dead_end_nodes),
        "dead_end_nodes": dead_end_nodes,
    }


def _free_space_polygon_graph_anchors(scene: dict, components: list[list[dict]]) -> dict:
    entry_anchors = []
    region_anchors = []
    for component_index, component in enumerate(components):
        cells = sorted(component, key=lambda cell: (cell["rect"].left, cell["rect"].top))
        for entry in scene.get("entries", []):
            cell_ids = [
                f"component_{component_index}_cell_{cell_index}"
                for cell_index, cell in enumerate(cells)
                if _rects_touch(entry["rect"], cell["rect"])
            ]
            if cell_ids:
                entry_anchors.append(
                    {
                        "entry_id": entry["id"],
                        "component_index": component_index,
                        "cell_ids": cell_ids,
                    }
                )
        for region in scene.get("regions", []):
            cell_ids = [
                f"component_{component_index}_cell_{cell_index}"
                for cell_index, cell in enumerate(cells)
                if _rect_overlap_area(region["rect"], cell["rect"]) > 1e-9
            ]
            if cell_ids:
                region_anchors.append(
                    {
                        "region_id": region["id"],
                        "component_index": component_index,
                        "cell_ids": cell_ids,
                    }
                )
    return {"entries": entry_anchors, "regions": region_anchors}


def _free_space_polygon_graph_entry_region_distance_evidence(
    scene: dict,
    components: list[list[dict]],
) -> list[dict]:
    evidence = []
    for component_index, component in enumerate(components):
        cells = sorted(component, key=lambda cell: (cell["rect"].left, cell["rect"].top))
        entry_cells_by_id = {
            entry["id"]: sorted(
                index
                for index, cell in enumerate(cells)
                if _rects_touch(entry["rect"], cell["rect"])
            )
            for entry in scene.get("entries", [])
        }
        region_cells_by_id = {
            region["id"]: sorted(
                index
                for index, cell in enumerate(cells)
                if _rect_overlap_area(region["rect"], cell["rect"]) > 1e-9
            )
            for region in scene.get("regions", [])
        }
        for entry in sorted(scene.get("entries", []), key=lambda item: item["id"]):
            entry_cells = entry_cells_by_id[entry["id"]]
            if not entry_cells:
                continue
            distances, previous, start_by_cell = _cell_adjacency_distances(
                cells,
                entry_cells,
            )
            for region in sorted(scene.get("regions", []), key=lambda item: item["id"]):
                region_cells = [
                    index
                    for index in region_cells_by_id[region["id"]]
                    if index in distances
                ]
                if not region_cells:
                    continue
                region_cell = min(
                    region_cells,
                    key=lambda index: (distances[index], index),
                )
                path_cells = _reconstruct_cell_path(previous, region_cell)
                path_edges = _cell_path_edge_evidence(
                    component_index,
                    cells,
                    path_cells,
                )
                evidence.append(
                    {
                        "entry_id": entry["id"],
                        "region_id": region["id"],
                        "component_index": component_index,
                        "entry_cell_id": (
                            f"component_{component_index}_cell_"
                            f"{start_by_cell[region_cell]}"
                        ),
                        "region_cell_id": (
                            f"component_{component_index}_cell_{region_cell}"
                        ),
                        "distance_edges": distances[region_cell],
                        "distance": _cell_path_length(cells, path_cells),
                        "path_cell_ids": [
                            f"component_{component_index}_cell_{cell_index}"
                            for cell_index in path_cells
                        ],
                        "path_edge_ids": [
                            item["edge_id"] for item in path_edges
                        ],
                        "min_clearance_width": (
                            round(
                                min(item["clearance_width"] for item in path_edges),
                                4,
                            )
                            if path_edges
                            else None
                        ),
                    }
                )
    return evidence


def _free_space_polygon_graph_entry_region_widest_path_evidence(
    scene: dict,
    components: list[list[dict]],
) -> list[dict]:
    evidence = []
    for component_index, component in enumerate(components):
        cells = sorted(component, key=lambda cell: (cell["rect"].left, cell["rect"].top))
        entry_cells_by_id = {
            entry["id"]: sorted(
                index
                for index, cell in enumerate(cells)
                if _rects_touch(entry["rect"], cell["rect"])
            )
            for entry in scene.get("entries", [])
        }
        region_cells_by_id = {
            region["id"]: sorted(
                index
                for index, cell in enumerate(cells)
                if _rect_overlap_area(region["rect"], cell["rect"]) > 1e-9
            )
            for region in scene.get("regions", [])
        }
        for entry in sorted(scene.get("entries", []), key=lambda item: item["id"]):
            entry_cells = entry_cells_by_id[entry["id"]]
            if not entry_cells:
                continue
            widths, previous, start_by_cell = _cell_widest_path_widths(
                cells,
                entry_cells,
            )
            for region in sorted(scene.get("regions", []), key=lambda item: item["id"]):
                region_cells = [
                    index
                    for index in region_cells_by_id[region["id"]]
                    if index in widths
                ]
                if not region_cells:
                    continue
                region_cell = min(
                    region_cells,
                    key=lambda index: (-widths[index], index),
                )
                path_cells = _reconstruct_cell_path(previous, region_cell)
                path_edges = _cell_path_edge_evidence(
                    component_index,
                    cells,
                    path_cells,
                )
                evidence.append(
                    {
                        "entry_id": entry["id"],
                        "region_id": region["id"],
                        "component_index": component_index,
                        "entry_cell_id": (
                            f"component_{component_index}_cell_"
                            f"{start_by_cell[region_cell]}"
                        ),
                        "region_cell_id": (
                            f"component_{component_index}_cell_{region_cell}"
                        ),
                        "widest_clearance_width": (
                            round(widths[region_cell], 4)
                            if path_edges
                            else None
                        ),
                        "path_cell_ids": [
                            f"component_{component_index}_cell_{cell_index}"
                            for cell_index in path_cells
                        ],
                        "path_edge_ids": [
                            item["edge_id"] for item in path_edges
                        ],
                    }
                )
    return evidence


def _cell_widest_path_widths(
    cells: list[dict],
    starts: list[int],
) -> tuple[dict[int, float], dict[int, int | None], dict[int, int]]:
    adjacency = {index: [] for index in range(len(cells))}
    for left_index, left in enumerate(cells):
        for right_index, right in enumerate(cells[left_index + 1:], start=left_index + 1):
            shared = _rect_shared_edge(left["rect"], right["rect"])
            if shared is None:
                continue
            width = hypot(
                shared[1][0] - shared[0][0],
                shared[1][1] - shared[0][1],
            )
            adjacency[left_index].append((right_index, width))
            adjacency[right_index].append((left_index, width))
    widths = {}
    previous = {}
    start_by_cell = {}
    queue = []
    for start in starts:
        widths[start] = float("inf")
        previous[start] = None
        start_by_cell[start] = start
        heappush(queue, (-widths[start], start))
    while queue:
        negative_width, index = heappop(queue)
        width = -negative_width
        if width < widths.get(index, -1.0):
            continue
        for next_index, edge_width in sorted(adjacency[index]):
            candidate = min(width, edge_width)
            if candidate <= widths.get(next_index, -1.0):
                continue
            widths[next_index] = candidate
            previous[next_index] = index
            start_by_cell[next_index] = start_by_cell[index]
            heappush(queue, (-candidate, next_index))
    return widths, previous, start_by_cell


def _cell_path_edge_evidence(
    component_index: int,
    cells: list[dict],
    path_cells: list[int],
) -> list[dict]:
    evidence = []
    for left_index, right_index in zip(path_cells, path_cells[1:]):
        shared = _rect_shared_edge(
            cells[left_index]["rect"],
            cells[right_index]["rect"],
        )
        if shared is None:
            continue
        a = f"component_{component_index}_cell_{min(left_index, right_index)}"
        b = f"component_{component_index}_cell_{max(left_index, right_index)}"
        evidence.append(
            {
                "edge_id": f"edge_{a}_{b}",
                "clearance_width": round(
                    hypot(
                        shared[1][0] - shared[0][0],
                        shared[1][1] - shared[0][1],
                    ),
                    4,
                ),
            }
        )
    return evidence


def _room_minus_blocker_polygon_evidence(components: list[list[dict]]) -> list[dict]:
    evidence = []
    for component_index, component in enumerate(components):
        loops = _component_boundary_loops(component)
        if not loops:
            continue
        outer = max(loops, key=lambda loop: abs(_signed_ring_area(loop)))
        holes = tuple(
            loop
            for loop in sorted(loops, key=lambda loop: (abs(_signed_ring_area(loop)), loop))
            if loop != outer
        )
        evidence.append(
            {
                "component_index": component_index,
                "outer_ring": outer,
                "holes": holes,
                "area": round(sum(cell["area"] for cell in component), 4),
                "cell_count": len(component),
            }
        )
    return evidence


def _cad_room_minus_blocker_polygon_evidence(
    room_polygon: Polygon | None,
    blockers: list[dict],
) -> list[dict]:
    if room_polygon is None:
        return []
    from shapely.geometry import MultiPolygon as ShapelyMultiPolygon
    from shapely.geometry import Polygon as ShapelyPolygon
    from shapely.ops import unary_union

    room = ShapelyPolygon(room_polygon.points)
    blocker_polygons = [
        _shape_to_shapely_polygon(_record_shape(blocker))
        for blocker in blockers
    ]
    blocker_polygons = [polygon for polygon in blocker_polygons if not polygon.is_empty]
    free_geometry = room
    if blocker_polygons:
        free_geometry = room.difference(unary_union(blocker_polygons))
    polygons = (
        list(free_geometry.geoms)
        if isinstance(free_geometry, ShapelyMultiPolygon)
        else [free_geometry]
    )
    evidence = []
    for component_index, polygon in enumerate(polygons):
        if polygon.is_empty:
            continue
        evidence.append(
            {
                "component_index": component_index,
                "outer_ring": _shapely_ring_points(
                    polygon.exterior.coords,
                    positive_area=True,
                ),
                "holes": tuple(
                    _shapely_ring_points(ring.coords, positive_area=False)
                    for ring in polygon.interiors
                ),
                "area": round(polygon.area, 4),
                "source": "shapely_difference",
            }
        )
    return evidence


def _shape_to_shapely_polygon(shape: Rect | Polygon):
    from shapely.geometry import Polygon as ShapelyPolygon

    if isinstance(shape, Polygon):
        return ShapelyPolygon(shape.points)
    return ShapelyPolygon(
        (
            (shape.left, shape.top),
            (shape.right, shape.top),
            (shape.right, shape.bottom),
            (shape.left, shape.bottom),
        )
    )


def _cad_room_minus_blocker_component_touch_evidence(
    cad_polygons: list[dict],
    entries: list[dict],
    regions: list[dict],
) -> list[dict]:
    evidence = []
    for item in cad_polygons:
        polygon = _cad_evidence_to_shapely_polygon(item)
        entry_ids = sorted(
            entry["id"]
            for entry in entries
            if polygon.intersects(_shape_to_shapely_polygon(_record_shape(entry)))
        )
        region_overlap_areas = {}
        for region in regions:
            area = polygon.intersection(
                _shape_to_shapely_polygon(_record_shape(region))
            ).area
            if area > 1e-9:
                region_overlap_areas[region["id"]] = round(area, 4)
        evidence.append(
            {
                "component_index": item["component_index"],
                "entry_ids": entry_ids,
                "region_ids": sorted(region_overlap_areas),
                "region_overlap_areas": region_overlap_areas,
            }
        )
    return sorted(evidence, key=lambda item: item["component_index"])


def _cad_evidence_to_shapely_polygon(item: dict):
    from shapely.geometry import Polygon as ShapelyPolygon

    return ShapelyPolygon(item["outer_ring"], item.get("holes", ()))


def _shapely_ring_points(
    coords,
    *,
    positive_area: bool,
) -> tuple[tuple[float, float], ...]:
    points = tuple(_rounded_point((x, y)) for x, y in list(coords)[:-1])
    if not points:
        return points
    if (_signed_ring_area(points) > 0) != positive_area:
        points = (points[0],) + tuple(reversed(points[1:]))
    start_index = min(range(len(points)), key=lambda index: points[index])
    return points[start_index:] + points[:start_index]


def _component_boundary_loops(component: list[dict]) -> list[tuple[tuple[float, float], ...]]:
    edge_counts = {}
    oriented_edges = []
    for cell in component:
        rect = cell["rect"]
        for start, end in (
            ((rect.left, rect.top), (rect.right, rect.top)),
            ((rect.right, rect.top), (rect.right, rect.bottom)),
            ((rect.right, rect.bottom), (rect.left, rect.bottom)),
            ((rect.left, rect.bottom), (rect.left, rect.top)),
        ):
            edge = (_rounded_point(start), _rounded_point(end))
            oriented_edges.append(edge)
            key = tuple(sorted(edge))
            edge_counts[key] = edge_counts.get(key, 0) + 1

    unused = {
        edge
        for edge in oriented_edges
        if edge_counts[tuple(sorted(edge))] == 1
    }
    loops = []
    while unused:
        start, end = min(unused)
        unused.remove((start, end))
        ring = [start]
        current = end
        while current != start:
            ring.append(current)
            next_edges = sorted(edge for edge in unused if edge[0] == current)
            if not next_edges:
                break
            next_edge = next_edges[0]
            unused.remove(next_edge)
            current = next_edge[1]
        if current == start and len(ring) >= 3:
            loops.append(_normalize_boundary_ring(_simplify_collinear_ring(ring)))
    return sorted(loops, key=lambda loop: (min(point[0] for point in loop), min(point[1] for point in loop), loop))


def _rounded_point(point: tuple[float, float]) -> tuple[float, float]:
    return (round(point[0], 4), round(point[1], 4))


def _simplify_collinear_ring(
    ring: list[tuple[float, float]],
) -> tuple[tuple[float, float], ...]:
    simplified = list(ring)
    changed = True
    while changed and len(simplified) > 3:
        changed = False
        next_ring = []
        for index, point in enumerate(simplified):
            previous = simplified[index - 1]
            following = simplified[(index + 1) % len(simplified)]
            if abs(_orientation(previous, point, following)) <= 1e-9:
                changed = True
                continue
            next_ring.append(point)
        simplified = next_ring
    return tuple(simplified)


def _normalize_boundary_ring(
    ring: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    if not ring:
        return ring
    start_index = min(range(len(ring)), key=lambda index: (ring[index][0], ring[index][1]))
    return ring[start_index:] + ring[:start_index]


def _signed_ring_area(ring: tuple[tuple[float, float], ...]) -> float:
    return sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(ring, ring[1:] + ring[:1])
    ) / 2


def _rect_shared_edge(a, b) -> tuple[tuple[float, float], tuple[float, float]] | None:
    if abs(a.right - b.left) <= 1e-9 or abs(b.right - a.left) <= 1e-9:
        x = a.right if abs(a.right - b.left) <= 1e-9 else b.right
        top = max(a.top, b.top)
        bottom = min(a.bottom, b.bottom)
        if bottom - top > 1e-9:
            return ((round(x, 4), round(top, 4)), (round(x, 4), round(bottom, 4)))
    if abs(a.bottom - b.top) <= 1e-9 or abs(b.bottom - a.top) <= 1e-9:
        y = a.bottom if abs(a.bottom - b.top) <= 1e-9 else b.bottom
        left = max(a.left, b.left)
        right = min(a.right, b.right)
        if right - left > 1e-9:
            return ((round(left, 4), round(y, 4)), (round(right, 4), round(y, 4)))
    return None


def _component_centroid(component: list[dict]) -> tuple[float, float]:
    total_area = sum(cell["area"] for cell in component)
    if total_area <= 1e-9:
        return (0.0, 0.0)
    return (
        sum(cell["rect"].cx * cell["area"] for cell in component) / total_area,
        sum(cell["rect"].cy * cell["area"] for cell in component) / total_area,
    )


def _negative_space_graph(scene: dict, negative_space: dict) -> dict:
    components = negative_space.get("components", [])
    component_rects_by_index = {
        item["component_index"]: item
        for item in negative_space.get("component_rects", [])
    }
    component_nodes = []
    for item in negative_space.get("entry_component_evidence", []):
        component_index = item["component_index"]
        rect_evidence = component_rects_by_index.get(component_index, {})
        node = {
            "id": f"node_negative_space_component_{item['component_index']}",
            "kind": "negative_space_component",
            "ref_id": f"component_{item['component_index']}",
            "component_index": component_index,
            "area": item["area"],
            "point": _component_centroid(components[component_index])
            if component_index < len(components)
            else (0.0, 0.0),
        }
        if "bbox" in rect_evidence:
            node["bbox"] = rect_evidence["bbox"]
        if "cell_count" in rect_evidence:
            node["cell_count"] = rect_evidence["cell_count"]
        if "cell_rects" in rect_evidence:
            node["cell_rects"] = rect_evidence["cell_rects"]
        component_nodes.append(node)
    entry_nodes = [
        {
            "id": _node_id("entry", entry),
            "kind": "entry",
            "ref_id": entry["id"],
            "point": (entry["rect"].cx, entry["rect"].cy),
        }
        for entry in scene.get("entries", [])
    ]
    region_nodes = [
        {
            "id": _node_id("region", region),
            "kind": "region",
            "ref_id": region["id"],
            "point": (region["rect"].cx, region["rect"].cy),
        }
        for region in scene.get("regions", [])
    ]
    entry_edges = [
        {
            "id": f"edge_entry_negative_space_component_{entry_id}_component_{item['component_index']}",
            "kind": "entry_negative_space_component_touch",
            "a": _node_id("entry", {"id": entry_id}),
            "b": f"node_negative_space_component_{item['component_index']}",
            "refs": {"entry": entry_id, "component": item["component_index"]},
        }
        for item in negative_space.get("entry_component_evidence", [])
        for entry_id in item["entry_ids"]
    ]
    region_edges = []
    for component_index, component in enumerate(components):
        for region in scene.get("regions", []):
            overlap_area = sum(
                _rect_overlap_area(region["rect"], cell["rect"])
                for cell in component
            )
            if overlap_area <= 1e-9:
                continue
            region_edges.append(
                {
                    "id": f"edge_negative_space_component_region_component_{component_index}_{region['id']}",
                    "kind": "negative_space_component_region_touch",
                    "a": f"node_negative_space_component_{component_index}",
                    "b": _node_id("region", region),
                    "refs": {"component": component_index, "region": region["id"]},
                    "overlap_area": round(overlap_area, 4),
                    "region_area_ratio": round(
                        overlap_area / max(region["rect"].area, 1e-9),
                        4,
                    ),
                }
            )
    nodes = component_nodes + entry_nodes + region_nodes
    edges = entry_edges + region_edges
    metrics = _negative_space_graph_metrics(nodes, edges)
    distance_evidence = _entry_region_free_polygon_distance_evidence(scene, components)
    metrics["entry_region_free_polygon_distance_evidence"] = distance_evidence
    metrics["mean_entry_region_free_polygon_distance"] = (
        round(mean(item["distance_edges"] for item in distance_evidence), 4)
        if distance_evidence
        else None
    )
    metrics["mean_entry_region_free_polygon_path_length"] = (
        round(mean(item["distance"] for item in distance_evidence), 4)
        if distance_evidence
        else None
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "metrics": metrics,
    }


def _entry_region_free_polygon_distance_evidence(
    scene: dict,
    components: list[list[dict]],
) -> list[dict]:
    evidence = []
    for component_index, component in enumerate(components):
        cells = sorted(component, key=lambda cell: (cell["rect"].left, cell["rect"].top))
        entry_cells = sorted(
            {
                index
                for index, cell in enumerate(cells)
                for entry in scene.get("entries", [])
                if _rects_touch(entry["rect"], cell["rect"])
            }
        )
        if not entry_cells:
            continue
        distances, previous, start_by_cell = _cell_adjacency_distances(
            cells,
            entry_cells,
        )
        for region in sorted(scene.get("regions", []), key=lambda item: item["id"]):
            region_cells = [
                index
                for index, cell in enumerate(cells)
                if _rect_overlap_area(region["rect"], cell["rect"]) > 1e-9
                and index in distances
            ]
            if not region_cells:
                continue
            region_cell = min(region_cells, key=lambda index: (distances[index], index))
            entry_cell = start_by_cell[region_cell]
            path_cells = _reconstruct_cell_path(previous, region_cell)
            evidence.append(
                {
                    "region_id": region["id"],
                    "component_index": component_index,
                    "entry_cell": entry_cell,
                    "region_cell": region_cell,
                    "distance_edges": distances[region_cell],
                    "path_cells": path_cells,
                    "distance": _cell_path_length(cells, path_cells),
                }
            )
    return sorted(evidence, key=lambda item: item["region_id"])


def _cell_adjacency_distances(
    cells: list[dict],
    starts: list[int],
) -> tuple[dict[int, int], dict[int, int | None], dict[int, int]]:
    adjacency = {index: set() for index in range(len(cells))}
    for left_index, left in enumerate(cells):
        for right_index, right in enumerate(cells[left_index + 1:], start=left_index + 1):
            if _rects_share_edge(left["rect"], right["rect"]):
                adjacency[left_index].add(right_index)
                adjacency[right_index].add(left_index)
    distances = {}
    previous = {}
    start_by_cell = {}
    queue = deque()
    for start in starts:
        distances[start] = 0
        previous[start] = None
        start_by_cell[start] = start
        queue.append(start)
    while queue:
        index = queue.popleft()
        for next_index in sorted(adjacency[index]):
            if next_index in distances:
                continue
            distances[next_index] = distances[index] + 1
            previous[next_index] = index
            start_by_cell[next_index] = start_by_cell[index]
            queue.append(next_index)
    return distances, previous, start_by_cell


def _reconstruct_cell_path(
    previous: dict[int, int | None],
    target_cell: int,
) -> list[int]:
    path = []
    cell = target_cell
    while cell is not None:
        path.append(cell)
        cell = previous.get(cell)
    return list(reversed(path))


def _cell_path_length(cells: list[dict], path_cells: list[int]) -> float:
    length = 0.0
    for left, right in zip(path_cells, path_cells[1:]):
        left_rect = cells[left]["rect"]
        right_rect = cells[right]["rect"]
        length += hypot(left_rect.cx - right_rect.cx, left_rect.cy - right_rect.cy)
    return round(length, 4)


def _negative_space_graph_metrics(nodes: list[dict], edges: list[dict]) -> dict:
    component_nodes = [
        node for node in nodes if node["kind"] == "negative_space_component"
    ]
    component_ids = sorted(node["component_index"] for node in component_nodes)
    entry_component_edges = [
        edge
        for edge in edges
        if edge["kind"] == "entry_negative_space_component_touch"
    ]
    region_component_edges = [
        edge
        for edge in edges
        if edge["kind"] == "negative_space_component_region_touch"
    ]
    entry_connected_component_ids = sorted(
        {edge["refs"]["component"] for edge in entry_component_edges}
    )
    region_ids = sorted(
        node["ref_id"] for node in nodes if node["kind"] == "region"
    )
    entry_connected_region_ids = sorted(
        {
            edge["refs"]["region"]
            for edge in region_component_edges
            if edge["refs"]["component"] in entry_connected_component_ids
        }
    )
    entry_connected_region_pair_evidence = _entry_connected_region_pair_evidence(
        [
            edge
            for edge in region_component_edges
            if edge["refs"]["component"] in entry_connected_component_ids
        ]
    )
    unconnected_region_pair_evidence = _unconnected_region_pair_evidence(
        [{"id": region_id} for region_id in region_ids],
        entry_connected_region_pair_evidence,
    )
    total_region_pairs = len(list(combinations(region_ids, 2)))
    component_area_by_id = {
        node["component_index"]: node.get("area", 0.0)
        for node in component_nodes
    }
    component_cell_counts = {
        node["component_index"]: len(node.get("cell_rects", []))
        for node in component_nodes
    }
    component_cell_area_sums = {
        node["component_index"]: round(
            sum(cell["area"] for cell in node.get("cell_rects", [])),
            4,
        )
        for node in component_nodes
    }
    component_cell_area_residuals = {
        component_id: round(
            component_area_by_id[component_id]
            - component_cell_area_sums.get(component_id, 0.0),
            4,
        )
        for component_id in component_ids
    }
    component_area = sum(component_area_by_id.values())
    max_component_cell_area_residual = max(
        (abs(value) for value in component_cell_area_residuals.values()),
        default=0.0,
    )
    entry_connected_component_area = sum(
        component_area_by_id[component_id]
        for component_id in entry_connected_component_ids
    )
    non_entry_connected_component_area = max(
        0.0,
        component_area - entry_connected_component_area,
    )
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "component_node_count": len(component_ids),
        "entry_node_count": sum(1 for node in nodes if node["kind"] == "entry"),
        "region_node_count": sum(1 for node in nodes if node["kind"] == "region"),
        "entry_component_edge_count": len(entry_component_edges),
        "region_component_edge_count": len(region_component_edges),
        "entry_connected_component_ids": entry_connected_component_ids,
        "non_entry_connected_component_ids": [
            component_id
            for component_id in component_ids
            if component_id not in entry_connected_component_ids
        ],
        "entry_connected_component_ratio": round(
            len(entry_connected_component_ids) / max(1, len(component_ids)),
            4,
        ),
        "component_area": round(component_area, 4),
        "component_cell_counts": component_cell_counts,
        "component_cell_area_sums": component_cell_area_sums,
        "component_cell_area_residuals": component_cell_area_residuals,
        "max_component_cell_area_residual_ratio": round(
            max_component_cell_area_residual / max(component_area, 1e-9),
            4,
        ),
        "entry_connected_component_area": round(entry_connected_component_area, 4),
        "non_entry_connected_component_area": round(
            non_entry_connected_component_area,
            4,
        ),
        "entry_connected_area_ratio": round(
            entry_connected_component_area / max(component_area, 1e-9),
            4,
        ),
        "non_entry_connected_area_ratio": round(
            non_entry_connected_component_area / max(component_area, 1e-9),
            4,
        ),
        "entry_connected_region_ids": entry_connected_region_ids,
        "non_entry_connected_region_ids": [
            region_id
            for region_id in region_ids
            if region_id not in entry_connected_region_ids
        ],
        "entry_connected_region_ratio": round(
            len(entry_connected_region_ids) / max(1, len(region_ids)),
            4,
        ),
        "entry_connected_region_pair_count": len(
            entry_connected_region_pair_evidence
        ),
        "total_region_pair_count": total_region_pairs,
        "entry_connected_region_pair_ratio": round(
            len(entry_connected_region_pair_evidence)
            / max(1, total_region_pairs),
            4,
        ),
        "entry_connected_region_pair_evidence": entry_connected_region_pair_evidence,
        "unconnected_region_pair_evidence": unconnected_region_pair_evidence,
    }


def _entry_connected_region_pair_evidence(region_edges: list[dict]) -> list[dict]:
    regions_by_component = {}
    for edge in region_edges:
        regions_by_component.setdefault(edge["refs"]["component"], set()).add(
            edge["refs"]["region"]
        )
    evidence = []
    for component, region_ids in sorted(regions_by_component.items()):
        for region_a, region_b in combinations(sorted(region_ids), 2):
            evidence.append(
                {
                    "component": component,
                    "region_a": region_a,
                    "region_b": region_b,
                }
            )
    return evidence


def _unconnected_region_pair_evidence(
    regions: list[dict],
    connected_pair_evidence: list[dict],
) -> list[dict]:
    connected_pairs = {
        (item["region_a"], item["region_b"])
        for item in connected_pair_evidence
    }
    evidence = []
    for region_a, region_b in combinations(sorted(region["id"] for region in regions), 2):
        if (region_a, region_b) not in connected_pairs:
            evidence.append({"region_a": region_a, "region_b": region_b})
    return evidence


def _entry_connected_region_area_coverage_evidence(
    regions: list[dict],
    region_edges: list[dict],
) -> list[dict]:
    edges_by_region = {}
    for edge in region_edges:
        edges_by_region.setdefault(edge["refs"]["region"], []).append(edge)
    evidence = []
    for region in sorted(regions, key=lambda item: item["id"]):
        edges = sorted(
            edges_by_region.get(region["id"], []),
            key=lambda edge: edge["refs"]["component"],
        )
        entry_connected_area = sum(edge["overlap_area"] for edge in edges)
        region_area = region["rect"].area
        evidence.append(
            {
                "region": region["id"],
                "entry_connected_area": round(entry_connected_area, 4),
                "region_area": round(region_area, 4),
                "coverage_ratio": round(
                    entry_connected_area / max(region_area, 1e-9),
                    4,
                ),
                "components": [edge["refs"]["component"] for edge in edges],
                "edge_ids": [edge["id"] for edge in edges],
            }
        )
    return evidence


def _rect_intersection(a, b) -> Rect | None:
    left = max(a.left, b.left)
    right = min(a.right, b.right)
    top = max(a.top, b.top)
    bottom = min(a.bottom, b.bottom)
    if right - left <= 1e-9 or bottom - top <= 1e-9:
        return None
    return Rect(
        cx=(left + right) / 2,
        cy=(top + bottom) / 2,
        width=right - left,
        height=bottom - top,
    )


def _record_overlap_area(
    record: dict,
    clip_polygon: Polygon | None,
    clip_rect: Rect,
) -> float:
    shape = _record_shape(record)
    if isinstance(shape, Polygon):
        if clip_polygon is not None:
            return _polygon_overlap_area_by_rect_decomposition(shape, clip_polygon)
        return _polygon_rect_overlap_area(shape, clip_rect)
    return (
        _polygon_rect_overlap_area(clip_polygon, shape)
        if clip_polygon is not None
        else _rect_overlap_area(clip_rect, shape)
    )


def _shape_rect_overlap_area(shape: Rect | Polygon, rect: Rect) -> float:
    if isinstance(shape, Polygon):
        return _polygon_rect_overlap_area(shape, rect)
    return _rect_overlap_area(shape, rect)


def _polygon_overlap_area_by_rect_decomposition(
    polygon: Polygon,
    clip_polygon: Polygon,
) -> float:
    xs = sorted({point[0] for point in polygon.points + clip_polygon.points})
    ys = sorted({point[1] for point in polygon.points + clip_polygon.points})
    area = 0.0
    for left, right in zip(xs, xs[1:]):
        for top, bottom in zip(ys, ys[1:]):
            if right - left <= 1e-9 or bottom - top <= 1e-9:
                continue
            cell = Rect(
                cx=(left + right) / 2,
                cy=(top + bottom) / 2,
                width=right - left,
                height=bottom - top,
            )
            area += min(
                _polygon_rect_overlap_area(polygon, cell),
                _polygon_rect_overlap_area(clip_polygon, cell),
            )
    return area


def _rects_share_edge(a, b) -> bool:
    vertical_touch = abs(a.right - b.left) <= 1e-9 or abs(b.right - a.left) <= 1e-9
    vertical_overlap = min(a.bottom, b.bottom) - max(a.top, b.top) > 1e-9
    horizontal_touch = abs(a.bottom - b.top) <= 1e-9 or abs(b.bottom - a.top) <= 1e-9
    horizontal_overlap = min(a.right, b.right) - max(a.left, b.left) > 1e-9
    return (vertical_touch and vertical_overlap) or (horizontal_touch and horizontal_overlap)


def _cells_for_record(
    grid: SpatialGridBackend,
    record: dict,
) -> list[tuple[int, int]]:
    shape = _record_shape(record)
    if isinstance(shape, Polygon):
        return list(grid.iter_indices_in_polygon(shape))
    return list(grid.iter_indices_in_rect(shape))


def _seed_cells_for_record(
    grid: SpatialGridBackend,
    record: dict,
    domain_cells: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    cells = _cells_for_record(grid, record)
    if cells:
        return [cell for cell in cells if cell in domain_cells]
    row = min(grid.n_rows - 1, max(0, int(record["rect"].cy // grid.resolution)))
    col = min(grid.n_cols - 1, max(0, int(record["rect"].cx // grid.resolution)))
    candidates = [(row, col)]
    free_candidates = [
        cell for cell in candidates if cell in domain_cells and grid.free(*cell)
    ]
    if free_candidates:
        return free_candidates
    for radius in range(1, max(grid.n_rows, grid.n_cols)):
        ring = []
        for next_row in range(max(0, row - radius), min(grid.n_rows, row + radius + 1)):
            for next_col in range(max(0, col - radius), min(grid.n_cols, col + radius + 1)):
                if abs(next_row - row) != radius and abs(next_col - col) != radius:
                    continue
                ring.append((next_row, next_col))
        free_ring = [
            cell for cell in ring if cell in domain_cells and grid.free(*cell)
        ]
        if free_ring:
            return free_ring
    return []


def _record_reachability(
    grid: SpatialGridBackend,
    record: dict,
    path_cells: set[tuple[int, int]],
    domain_cells: set[tuple[int, int]],
    entry_distances: dict[tuple[int, int], int],
    visibility_distances: dict[tuple[int, int], int],
) -> dict:
    cells = [
        cell
        for cell in _cells_for_record(grid, record)
        if cell in domain_cells and grid.free(*cell)
    ]
    reachable_cells = [
        cell for cell in cells if grid.cells[cell[0]][cell[1]].reachable
    ]
    path_overlap = sorted(set(cells) & path_cells)
    distance_steps = min(
        (entry_distances[cell] for cell in cells if cell in entry_distances),
        default=None,
    )
    visibility_distance_steps = min(
        (
            visibility_distances[cell]
            for cell in cells
            if cell in visibility_distances
        ),
        default=None,
    )
    return {
        "region_id": record["id"],
        "entry_reachable": bool(reachable_cells),
        "entry_distance_steps": distance_steps,
        "entry_distance": round(distance_steps * grid.resolution, 4)
        if distance_steps is not None
        else None,
        "visibility_reachable": visibility_distance_steps is not None,
        "visibility_distance_steps": visibility_distance_steps,
        "visibility_distance": round(visibility_distance_steps * grid.resolution, 4)
        if visibility_distance_steps is not None
        else None,
        "path_contact": bool(path_overlap),
        "path_reachable": bool(reachable_cells and path_overlap),
        "sampled_cells": sorted(cells),
        "reachable_cells": sorted(reachable_cells),
        "path_overlap_cells": path_overlap,
    }


def _path_polygon(path: dict) -> Polygon | None:
    points = path.get("points") or []
    if len(points) < 3:
        return None
    if points[:1] == points[-1:]:
        points = points[:-1]
    if len(points) < 3:
        return None
    return Polygon(points=tuple(points))


def _path_blocker_overlap_samples(
    path: dict,
    path_polygon: Polygon | None,
    blockers: list[dict],
) -> list[dict]:
    samples = []
    for blocker in blockers:
        if blocker["id"] == path["id"]:
            continue
        area = (
            _polygon_rect_overlap_area(path_polygon, blocker["rect"])
            if path_polygon is not None
            else _rect_overlap_area(path["rect"], blocker["rect"])
        )
        if area <= 1e-9:
            continue
        samples.append(
            {
                "target_id": blocker["id"],
                "target_role": blocker["role"],
                "area": round(area, 4),
            }
        )
    return sorted(samples, key=lambda sample: (-sample["area"], sample["target_id"]))


def _length_weighted_channel(boundaries: list[dict], channel: str) -> float:
    total = sum(_boundary_length(boundary) for boundary in boundaries)
    if total <= 1e-9:
        return 0.0
    return sum(
        _boundary_length(boundary) * boundary["weights"][channel]
        for boundary in boundaries
    ) / total


def _boundary_cue_profile(boundary: dict) -> dict:
    length = _boundary_length(boundary)
    weights = boundary["weights"]
    return {
        "id": boundary["id"],
        "kind": boundary.get("metadata", {}).get("boundary-kind"),
        "length": round(length, 4),
        "walk_block": round(weights["walk_block"], 4),
        "see_block": round(weights["see_block"], 4),
        "grouping_strength": round(weights["grouping_strength"], 4),
        "influence": round(length * weights["grouping_strength"], 4),
    }


def _path_region_boundary_cue_evidence(scene: dict, region_edges: list[dict]) -> list[dict]:
    touched_paths_by_region = {}
    for edge in region_edges:
        touched_paths_by_region.setdefault(edge["refs"]["region"], []).append(edge["refs"]["path"])
    proximity_by_region = {
        item["region_id"]: item
        for item in _region_source_boundary_proximity_row(scene).get(
            "region_boundary_proximity",
            [],
        )
    }
    kind_by_boundary_id = {
        boundary["id"]: boundary.get("metadata", {}).get("boundary-kind")
        for boundary in scene.get("boundaries", [])
    }
    evidence = []
    for region in scene.get("regions", []):
        touched_path_ids = sorted(touched_paths_by_region.get(region["id"], []))
        if not touched_path_ids:
            continue
        proximity = proximity_by_region.get(region["id"])
        perimeter = 2 * (region["rect"].width + region["rect"].height)
        influence = proximity["total_influence"] if proximity else None
        boundary_cue_ids = (
            [item["boundary_id"] for item in proximity.get("boundary_scores", [])]
            if proximity
            else []
        )
        same_region_boundaries = [
            boundary
            for boundary in scene.get("boundaries", [])
            if boundary["id"] in boundary_cue_ids
        ]
        grouping_strength = _length_weighted_channel(
            same_region_boundaries,
            "grouping_strength",
        )
        walk_block = _length_weighted_channel(same_region_boundaries, "walk_block")
        see_block = _length_weighted_channel(same_region_boundaries, "see_block")
        evidence.append(
            {
                "region_id": region["id"],
                "region": region["region"],
                "touched_path_ids": touched_path_ids,
                "has_boundary_cue": proximity is not None,
                "boundary_cue_ids": boundary_cue_ids,
                "boundary_cue_kinds": [
                    kind_by_boundary_id.get(boundary_id)
                    for boundary_id in boundary_cue_ids
                ],
                "boundary_cue_profiles": [
                    _boundary_cue_profile(boundary)
                    for boundary in same_region_boundaries
                ],
                "boundary_cue_count": len(boundary_cue_ids),
                "boundary_grouping_strength": round(grouping_strength, 4),
                "boundary_walk_block": round(walk_block, 4),
                "boundary_see_block": round(see_block, 4),
                "boundary_walk_see_gap": round(abs(walk_block - see_block), 4),
                "boundary_proximity": proximity["score"] if proximity else None,
                "boundary_total_influence": influence,
                "boundary_influence_per_region_perimeter": round(
                    influence / perimeter,
                    4,
                )
                if influence is not None and perimeter > 1e-9
                else 0.0,
            }
        )
    return evidence


def _line_of_sight_entry_region_evidence(scene: dict) -> list[dict]:
    blockers = [
        boundary
        for boundary in scene.get("boundaries", [])
        if boundary.get("metadata", {}).get("boundary-kind") != "room"
        and boundary.get("weights", {}).get("see_block", 0.0) > 0
    ]
    evidence = []
    for region in scene.get("regions", []):
        samples = []
        for entry in scene.get("entries", []):
            start = (entry["rect"].cx, entry["rect"].cy)
            end = (region["rect"].cx, region["rect"].cy)
            blocking_evidence = [
                evidence
                for blocker in blockers
                for evidence in [_line_of_sight_blocker_evidence(blocker, start, end)]
                if not _rects_touch(entry["rect"], blocker["rect"])
                and not _record_contains_point(blocker, start)
                and evidence["intersection_points"]
            ]
            samples.append(
                {
                    "entry_id": entry["id"],
                    "region_id": region["id"],
                    "visible": not blocking_evidence,
                    "blocking_boundary_ids": [
                        evidence["boundary_id"] for evidence in blocking_evidence
                    ],
                    "blocking_boundary_evidence": blocking_evidence,
                }
            )
        if not samples:
            continue
        visible_samples = [sample for sample in samples if sample["visible"]]
        evidence.append((visible_samples or samples)[0])
    return evidence


def _line_of_sight_region_pair_evidence(scene: dict) -> list[dict]:
    blockers = [
        boundary
        for boundary in scene.get("boundaries", [])
        if boundary.get("metadata", {}).get("boundary-kind") != "room"
        and boundary.get("weights", {}).get("see_block", 0.0) > 0
    ]
    evidence = []
    for region_a, region_b in combinations(scene.get("regions", []), 2):
        start = (region_a["rect"].cx, region_a["rect"].cy)
        end = (region_b["rect"].cx, region_b["rect"].cy)
        blocking_evidence = [
            evidence
            for blocker in blockers
            for evidence in [_line_of_sight_blocker_evidence(blocker, start, end)]
            if not _record_contains_point(blocker, start)
            and not _record_contains_point(blocker, end)
            and evidence["intersection_points"]
        ]
        evidence.append(
            {
                "region_a": region_a["id"],
                "region_b": region_b["id"],
                "visible": not blocking_evidence,
                "blocking_boundary_ids": [
                    item["boundary_id"] for item in blocking_evidence
                ],
                "blocking_boundary_evidence": blocking_evidence,
            }
        )
    return evidence


def _line_of_sight_blocker_evidence(
    record: dict,
    start: tuple[float, float],
    end: tuple[float, float],
) -> dict:
    intersections = _record_line_intersections(record, start, end)
    distances = [
        round(hypot(point[0] - start[0], point[1] - start[1]), 4)
        for point in intersections
    ]
    segment_length = hypot(end[0] - start[0], end[1] - start[1])
    return {
        "boundary_id": record["id"],
        "intersection_points": intersections,
        "intersection_distances_from_start": distances,
        "intersection_distance_ratios": [
            round(distance / segment_length, 4) if segment_length > 1e-9 else 0.0
            for distance in distances
        ],
    }


def _line_of_sight_graph(scene: dict) -> dict:
    nodes = [
        _line_of_sight_node(kind, record)
        for kind, records in (
            ("entry", scene.get("entries", [])),
            ("region", scene.get("regions", [])),
        )
        for record in records
    ]
    nodes_by_ref = {node["ref_id"]: node for node in nodes}
    edges = []
    for item in _line_of_sight_entry_region_evidence(scene):
        edges.append(
            _line_of_sight_edge(
                "entry_region_centerline_visibility",
                item["entry_id"],
                item["region_id"],
                "entry",
                "region",
                nodes_by_ref,
                item,
            )
        )
    for item in _line_of_sight_region_pair_evidence(scene):
        edges.append(
            _line_of_sight_edge(
                "region_pair_centerline_visibility",
                item["region_a"],
                item["region_b"],
                "region_a",
                "region_b",
                nodes_by_ref,
                item,
            )
        )
    return {
        "nodes": nodes,
        "edges": edges,
        "metrics": _line_of_sight_graph_metrics(nodes, edges),
    }


def _line_of_sight_node(kind: str, record: dict) -> dict:
    rect = record["rect"]
    return {
        "id": f"node_line_of_sight_{kind}_{record['id']}",
        "kind": kind,
        "ref_id": record["id"],
        "point": (round(rect.cx, 4), round(rect.cy, 4)),
    }


def _line_of_sight_edge(
    kind: str,
    from_id: str,
    to_id: str,
    from_ref: str,
    to_ref: str,
    nodes_by_ref: dict,
    item: dict,
) -> dict:
    start = nodes_by_ref[from_id]["point"]
    end = nodes_by_ref[to_id]["point"]
    from_kind = "entry" if from_ref == "entry" else "region"
    to_kind = "region"
    edge_scope = "entry_region" if from_ref == "entry" else "region_pair"
    return {
        "id": f"edge_line_of_sight_{edge_scope}_{from_id}_{to_id}",
        "kind": kind,
        "a": f"node_line_of_sight_{from_kind}_{from_id}",
        "b": f"node_line_of_sight_{to_kind}_{to_id}",
        "refs": {from_ref: from_id, to_ref: to_id},
        "visible": item["visible"],
        "centerline": {
            "start": start,
            "end": end,
            "length": round(hypot(end[0] - start[0], end[1] - start[1]), 4),
        },
        "blocking_boundary_ids": item["blocking_boundary_ids"],
        "blocking_boundary_evidence": item["blocking_boundary_evidence"],
    }


def _line_of_sight_graph_metrics(nodes: list[dict], edges: list[dict]) -> dict:
    visible_edges = [edge for edge in edges if edge["visible"]]
    blocked_edges = [edge for edge in edges if not edge["visible"]]
    blocked_edges_by_boundary = {}
    for edge in blocked_edges:
        for boundary_id in edge.get("blocking_boundary_ids", []):
            blocked_edges_by_boundary.setdefault(boundary_id, []).append(edge["id"])
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "visible_edge_count": len(visible_edges),
        "blocked_edge_count": len(blocked_edges),
        "visible_edge_ratio": round(len(visible_edges) / max(1, len(edges)), 4),
        "blocked_edge_ratio": round(len(blocked_edges) / max(1, len(edges)), 4),
        "visible_edge_ids": [edge["id"] for edge in visible_edges],
        "blocked_edge_ids": [edge["id"] for edge in blocked_edges],
        "blocking_boundary_ids": sorted(
            {
                boundary_id
                for edge in blocked_edges
                for boundary_id in edge.get("blocking_boundary_ids", [])
            }
        ),
        "blocking_boundary_edge_evidence": [
            {
                "boundary_id": boundary_id,
                "blocked_edge_ids": edge_ids,
                "blocked_edge_count": len(edge_ids),
            }
            for boundary_id, edge_ids in sorted(blocked_edges_by_boundary.items())
        ],
        "mean_centerline_length": round(
            mean(edge["centerline"]["length"] for edge in edges),
            4,
        )
        if edges
        else None,
    }


def _isovist_radial_proxy(scene: dict, ray_count: int = 8) -> dict:
    room = _room_boundary(scene)
    viewpoints = [
        (kind, record)
        for kind, records in (
            ("entry", scene.get("entries", [])),
            ("region", scene.get("regions", [])),
        )
        for record in records
    ]
    method = "radial_isovist_see_block_ray_intersection_proxy"
    if room is None or not viewpoints:
        return {
            "status": "not_available",
            "method": method,
            "ray_evidence": [],
            "isovist_area_evidence": [],
            "metrics": {
                "vantage_count": len(viewpoints),
                "ray_count": 0,
                "blocked_ray_count": 0,
                "blocked_ray_ratio": None,
                "mean_hit_distance": None,
                "mean_hit_polygon_area": None,
            },
            "uncertainty": "needs a room boundary and at least one entry or analysis region for radial isovist sampling",
        }

    blockers = [
        boundary
        for boundary in scene.get("boundaries", [])
        if boundary.get("metadata", {}).get("boundary-kind") != "room"
        and boundary.get("weights", {}).get("see_block", 0.0) > 0
    ]
    ray_length = max(hypot(*scene["size"]), hypot(room["rect"].width, room["rect"].height))
    ray_evidence = []
    for kind, record in viewpoints:
        start = _isovist_vantage_point(kind, record, room)
        for ray_index in range(ray_count):
            angle = ray_index * 360 / ray_count
            angle_degrees = int(angle) if float(angle).is_integer() else round(angle, 4)
            end = (
                start[0] + ray_length * cos(radians(angle)),
                start[1] + ray_length * sin(radians(angle)),
            )
            hits = []
            room_zero_hits = []
            for point in _record_line_intersections(room, start, end):
                distance = hypot(point[0] - start[0], point[1] - start[1])
                if distance > 1e-9:
                    hits.append((distance, 1, room, point, False))
                else:
                    room_zero_hits.append(point)
            if not hits and room_zero_hits:
                hits.append((0.0, 1, room, room_zero_hits[0], False))
            for blocker in blockers:
                if _record_contains_point(blocker, start):
                    continue
                for point in _record_line_intersections(blocker, start, end):
                    distance = hypot(point[0] - start[0], point[1] - start[1])
                    if distance > 1e-9:
                        hits.append((distance, 0, blocker, point, True))
            distance, _, hit_record, hit_point, blocked = min(
                hits,
                default=(ray_length, 1, None, end, False),
                key=lambda hit: (hit[0], hit[1]),
            )
            ray_evidence.append(
                {
                    "vantage_id": record["id"],
                    "vantage_kind": kind,
                    "angle_degrees": angle_degrees,
                    "start": start,
                    "hit_point": (round(hit_point[0], 4), round(hit_point[1], 4)),
                    "hit_distance": round(distance, 4),
                    "hit_boundary_id": hit_record["id"] if hit_record else None,
                    "hit_boundary_kind": (
                        hit_record.get("metadata", {}).get("boundary-kind")
                        if hit_record
                        else None
                    ),
                    "blocked_by_see_block": blocked,
                }
            )

    blocked_rays = [ray for ray in ray_evidence if ray["blocked_by_see_block"]]
    isovist_area_evidence = _isovist_area_evidence(ray_evidence)
    return {
        "status": "computed",
        "method": method,
        "ray_evidence": ray_evidence,
        "isovist_area_evidence": isovist_area_evidence,
        "metrics": {
            "vantage_count": len(viewpoints),
            "ray_count": len(ray_evidence),
            "blocked_ray_count": len(blocked_rays),
            "blocked_ray_ratio": round(len(blocked_rays) / max(1, len(ray_evidence)), 4),
            "mean_hit_distance": round(
                mean(ray["hit_distance"] for ray in ray_evidence),
                4,
            ),
            "mean_hit_polygon_area": round(
                mean(item["hit_polygon_area"] for item in isovist_area_evidence),
                4,
            )
            if isovist_area_evidence
            else None,
        },
        "uncertainty": "8-direction room-bounded radial ray proxy; not full isovist polygon, VGA, or calibrated visual exposure",
    }


def _isovist_area_evidence(ray_evidence: list[dict]) -> list[dict]:
    by_vantage = {}
    for ray in ray_evidence:
        by_vantage.setdefault(
            (ray["vantage_kind"], ray["vantage_id"]),
            [],
        ).append(ray)
    evidence = []
    for (vantage_kind, vantage_id), rays in sorted(by_vantage.items()):
        ordered = sorted(rays, key=lambda ray: ray["angle_degrees"])
        hit_polygon = tuple(ray["hit_point"] for ray in ordered)
        if len(hit_polygon) < 3:
            continue
        evidence.append(
            {
                "vantage_id": vantage_id,
                "vantage_kind": vantage_kind,
                "hit_polygon": hit_polygon,
                "hit_polygon_area": round(Polygon(hit_polygon).area, 4),
                "blocked_ray_count": sum(
                    1 for ray in ordered if ray["blocked_by_see_block"]
                ),
                "ray_count": len(ordered),
            }
        )
    return evidence


def _isovist_vantage_point(
    kind: str,
    record: dict,
    room: dict,
) -> tuple[float, float]:
    if kind == "entry" and not _record_contains_point(room, (record["rect"].cx, record["rect"].cy)):
        _, x, y = _entry_boundary_gap(record, room)
        return (round(x, 4), round(y, 4))
    return (round(record["rect"].cx, 4), round(record["rect"].cy, 4))


def _record_line_intersections(
    record: dict,
    start: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    points = record.get("points") or []
    if len(points) >= 2:
        intersections = [
            _line_segment_intersection_point(start, end, a, b)
            for a, b in _closed_edges(points)
            if _segments_intersect(start, end, a, b)
        ]
        return _unique_points(
            point for point in intersections if point is not None
        )
    rect = record["rect"]
    if rect.width <= 1e-9 or rect.height <= 1e-9:
        return []
    corners = [
        (rect.left, rect.top),
        (rect.right, rect.top),
        (rect.right, rect.bottom),
        (rect.left, rect.bottom),
    ]
    intersections = [
        _line_segment_intersection_point(start, end, a, b)
        for a, b in _closed_edges(corners)
        if _segments_intersect(start, end, a, b)
    ]
    if _point_in_rect(start, rect):
        intersections.append(start)
    if _point_in_rect(end, rect):
        intersections.append(end)
    return _unique_points(point for point in intersections if point is not None)


def _record_contains_point(record: dict, point: tuple[float, float]) -> bool:
    points = record.get("points") or []
    if len(points) >= 3:
        return _point_in_polygon(point, points)
    return _point_in_rect(point, record["rect"])


def _path_connectivity_rows(
    scene: dict,
    graph: dict,
    graphs: dict,
    path_geometry: dict,
    sampled_walkable_space: dict,
    negative_space: dict,
    negative_space_graph: dict,
    line_of_sight_graph: dict,
    isovist_radial_proxy: dict,
) -> list[dict]:
    paths = scene.get("paths", [])
    if not paths:
        return [_not_available(
            "path_connectivity",
            "entry_path_placeholder",
            "fixture has no path metadata",
        )]
    path_area = sum(
        path_geometry.get(path["id"], {}).get("path_polygon_area", path["rect"].area)
        for path in paths
    )
    room_area = max(1e-9, scene["size"][0] * scene["size"][1])
    entry_edges = [edge for edge in graph["edges"] if edge["kind"] == "entry_path_touch"]
    region_edges = [edge for edge in graph["edges"] if edge["kind"] == "path_region_touch"]
    touched_entry_ids = {
        edge["refs"]["entry"] for edge in entry_edges
    }
    entry_touch_evidence = _entry_touch_evidence(
        scene.get("entries", []),
        entry_edges,
        scene.get("boundaries", []),
    )
    path_entry_touch_evidence = [
        {
            "id": path["id"],
            "touched_entry_ids": sorted(
                edge["refs"]["entry"]
                for edge in entry_edges
                if edge["refs"]["path"] == path["id"]
            ),
        }
        for path in paths
    ]
    touched_region_ids = {
        edge["refs"]["region"] for edge in region_edges
    }
    entry_ratio = len(touched_entry_ids) / max(1, len(scene["entries"]))
    region_ratio = len(touched_region_ids) / max(1, len(scene["regions"]))
    walk_cost = graphs["walk"]["edges"][0]["walk_cost"] if graphs["walk"]["edges"] else 0.0
    visibility_cost = (
        graphs["visibility"]["edges"][0]["visibility_cost"]
        if graphs["visibility"]["edges"]
        else 0.0
    )
    graph_metrics = graphs["walk"]["metrics"]
    free_space_graph = negative_space.get("free_space_polygon_graph", {})
    cad_touch_evidence = negative_space.get(
        "cad_room_minus_blocker_component_touch_evidence",
        [],
    )
    cad_component_graph = _cad_room_minus_blocker_component_graph(cad_touch_evidence)
    cad_entry_connected_region_ids = sorted(
        {
            region_id
            for item in cad_touch_evidence
            if item["entry_ids"]
            for region_id in item["region_ids"]
        }
    )
    cad_region_ids = sorted(region["id"] for region in scene.get("regions", []))
    cad_entry_connected_region_pair_evidence = [
        {
            "component": item["component_index"],
            "region_a": region_a,
            "region_b": region_b,
        }
        for item in cad_touch_evidence
        if item["entry_ids"]
        for region_a, region_b in combinations(sorted(item["region_ids"]), 2)
    ]
    cad_total_region_pair_count = len(list(combinations(cad_region_ids, 2)))
    entry_region_distance_evidence = free_space_graph.get(
        "entry_region_distance_evidence",
        [],
    )
    entry_region_widest_path_evidence = free_space_graph.get(
        "entry_region_widest_path_evidence",
        [],
    )
    entry_region_widest_clearance_evidence = [
        item
        for item in entry_region_widest_path_evidence
        if item.get("widest_clearance_width") is not None
    ]
    entry_region_min_clearance_evidence = [
        item
        for item in entry_region_distance_evidence
        if item.get("min_clearance_width") is not None
    ]
    width_scores = [
        descriptor["width_continuity"]
        for descriptor in path_geometry.values()
        if descriptor["width_samples"]
    ]
    clearance_values = [
        descriptor["min_clearance_to_blocker"]
        for descriptor in path_geometry.values()
        if descriptor["min_clearance_to_blocker"] is not None
    ]
    clearance_evidence = list(path_geometry)
    for descriptor in path_geometry.values():
        minimum = descriptor["min_clearance_to_blocker"]
        clearance_evidence.extend(
            sample["target_id"]
            for sample in descriptor["clearance_samples"]
            if sample["distance"] == minimum
        )
    overlap_counts = [
        descriptor["blocker_overlap_count"]
        for descriptor in path_geometry.values()
        if descriptor["blocker_overlap_ratio"] is not None
    ]
    overlap_ratios = [
        descriptor["blocker_overlap_ratio"]
        for descriptor in path_geometry.values()
        if descriptor["blocker_overlap_ratio"] is not None
    ]
    overlap_evidence = list(path_geometry)
    for descriptor in path_geometry.values():
        overlap_evidence.extend(
            sample["target_id"]
            for sample in descriptor["clearance_samples"]
            if sample["distance"] <= 1e-9
        )
    overlap_area_ratios = [
        descriptor["blocker_overlap_area_ratio"]
        for descriptor in path_geometry.values()
        if descriptor["blocker_overlap_area_ratio"] is not None
    ]
    overlap_area_evidence = list(path_geometry)
    for descriptor in path_geometry.values():
        overlap_area_evidence.extend(
            sample["target_id"] for sample in descriptor["blocker_overlap_samples"]
        )
    path_region_boundary_cue_evidence = _path_region_boundary_cue_evidence(
        scene,
        region_edges,
    )
    line_of_sight_evidence = _line_of_sight_entry_region_evidence(scene)
    line_of_sight_region_pair_evidence = _line_of_sight_region_pair_evidence(scene)
    negative_space_edges = [
        edge["id"] for edge in negative_space_graph.get("edges", [])
    ]
    entry_connected_component_edges = [
        edge["id"]
        for edge in negative_space_graph.get("edges", [])
        if edge["kind"] == "entry_negative_space_component_touch"
    ]
    entry_connected_components = {
        edge["refs"]["component"]
        for edge in negative_space_graph.get("edges", [])
        if edge["kind"] == "entry_negative_space_component_touch"
    }
    negative_space_graph_metrics = negative_space_graph["metrics"]
    entry_connected_region_edges = [
        edge
        for edge in negative_space_graph.get("edges", [])
        if edge["kind"] == "negative_space_component_region_touch"
        and edge["refs"]["component"] in entry_connected_components
    ]
    entry_connected_region_pair_evidence = negative_space_graph_metrics[
        "entry_connected_region_pair_evidence"
    ]
    unconnected_region_pair_evidence = negative_space_graph_metrics[
        "unconnected_region_pair_evidence"
    ]
    entry_connected_region_area_coverage_evidence = (
        _entry_connected_region_area_coverage_evidence(
            scene.get("regions", []),
            entry_connected_region_edges,
        )
    )
    total_region_pairs = len(list(combinations(scene.get("regions", []), 2)))
    width_continuity = mean(width_scores) if width_scores else 0.0
    candidate_path_score = round(
        (negative_space.get("entry_connected_area_ratio") or 0.0) * width_continuity,
        4,
    )
    boundary_grouping_mean = (
        mean(item["boundary_grouping_strength"] for item in path_region_boundary_cue_evidence)
        if path_region_boundary_cue_evidence
        else 0.0
    )
    split_tendency = region_ratio * width_continuity * (1 - boundary_grouping_mean)
    walk_passability = max(0.0, min(1.0, 1 - walk_cost))
    capacity_factors = {
        "entry_region_reachability": graph_metrics["entry_region_reachability"],
        "path_width_continuity": round(width_continuity, 4),
        "walk_passability": round(walk_passability, 4),
    }
    candidate_path_inputs = {
        "negative_space_entry_connected_area_ratio": negative_space.get(
            "entry_connected_area_ratio"
        ),
        "path_width_continuity": round(width_continuity, 4),
    }
    candidate_path_pair_inputs = {
        "candidate_path_area_ratio_proxy": candidate_path_score,
        "negative_space_entry_connected_region_pair_ratio": (
            negative_space_graph_metrics["entry_connected_region_pair_ratio"]
        ),
        "entry_connected_region_pair_count": negative_space_graph_metrics[
            "entry_connected_region_pair_count"
        ],
        "total_region_pair_count": negative_space_graph_metrics[
            "total_region_pair_count"
        ],
    }
    sampled_area_ratio = sampled_walkable_space.get("walkable_cell_ratio")
    negative_area_ratio = negative_space.get("negative_space_area_ratio_proxy")
    area_ratio_delta = (
        round(abs(sampled_area_ratio - negative_area_ratio), 4)
        if isinstance(sampled_area_ratio, (int, float))
        and isinstance(negative_area_ratio, (int, float))
        else None
    )
    return [
        {
            "view_id": "path_connectivity",
            "metric": "sampled_grid_resolution",
            "score": sampled_walkable_space["resolution"],
            "status": "computed",
            "method": "sampled_grid_cell_size_scene_units",
            "evidence": sampled_walkable_space["resolution_evidence"],
            "uncertainty": "default cell size uses furniture scale when available; not yet multi-scale by human, path, column, or BIM units",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_resolution_sensitivity",
            "score": max(
                sampled_walkable_space["resolution_sensitivity"][
                    "entry_reachable_cell_ratio_range"
                ],
                sampled_walkable_space["resolution_sensitivity"][
                    "entry_reachable_region_ratio_range"
                ],
                sampled_walkable_space["resolution_sensitivity"][
                    "path_reachable_region_ratio_range"
                ],
            )
            if sampled_walkable_space.get("resolution_sensitivity")
            else None,
            "status": "computed"
            if sampled_walkable_space.get("resolution_sensitivity")
            else "not_available",
            "method": "half_base_double_resolution_sampled_metric_range",
            "evidence": sampled_walkable_space.get("resolution_sensitivity"),
            "uncertainty": "range across half/base/double sampled cell sizes for key sampled ratios; proxy for grid sensitivity, not full multi-resolution validation",
        },
        {
            "view_id": "path_connectivity",
            "metric": "entry_path_placeholder",
            "score": round(min(1.0, path_area / room_area), 4),
            "status": "computed",
            "method": "path_polygon_area_ratio_with_entry_count",
            "evidence": [path["id"] for path in paths] + [edge["id"] for edge in entry_edges],
            "uncertainty": "candidate path only; no medial-axis or visibility graph yet",
        },
        {
            "view_id": "path_connectivity",
            "metric": "entry_touch_ratio",
            "score": round(entry_ratio, 4),
            "status": "computed",
            "method": "path_graph_entry_touch_ratio",
            "evidence": [edge["id"] for edge in entry_edges],
            "entry_touch_evidence": entry_touch_evidence,
            "uncertainty": "bbox touch is fixture evidence, not a final circulation graph",
        },
        {
            "view_id": "path_connectivity",
            "metric": "disconnected_entry_ratio",
            "score": round(
                sum(1 for item in entry_touch_evidence if not item["touched_path_ids"])
                / max(1, len(scene["entries"])),
                4,
            ),
            "status": "computed",
            "method": "openings_without_path_touch_over_openings",
            "evidence": [
                item["id"] for item in entry_touch_evidence if not item["touched_path_ids"]
            ],
            "entry_touch_evidence": entry_touch_evidence,
            "uncertainty": "bbox path contact proxy; replace with hosted doorway-to-negative-space graph later",
        },
        {
            "view_id": "path_connectivity",
            "metric": "disconnected_path_ratio",
            "score": round(
                sum(
                    1
                    for item in path_entry_touch_evidence
                    if not item["touched_entry_ids"]
                )
                / max(1, len(paths)),
                4,
            ),
            "status": "computed",
            "method": "paths_without_entry_touch_over_paths",
            "evidence": [
                item["id"]
                for item in path_entry_touch_evidence
                if not item["touched_entry_ids"]
            ],
            "path_entry_touch_evidence": path_entry_touch_evidence,
            "uncertainty": "bbox path-entry contact proxy; replace with negative-space graph routing later",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_region_touch_ratio",
            "score": round(region_ratio, 4),
            "status": "computed",
            "method": "path_graph_region_touch_ratio",
            "evidence": [edge["id"] for edge in region_edges],
            "uncertainty": "region touch is bbox evidence; replace with negative-space graph later",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_region_split_tendency_proxy",
            "score": round(split_tendency, 4),
            "status": "computed",
            "method": "path_region_touch_width_continuity_minus_boundary_grouping_proxy",
            "evidence": [edge["id"] for edge in region_edges]
            + [path_id for path_id in path_geometry],
            "path_likeness_inputs": {
                "path_region_touch_ratio": round(region_ratio, 4),
                "path_width_continuity": round(width_continuity, 4),
                "boundary_grouping_strength": round(boundary_grouping_mean, 4),
            },
            "uncertainty": "continuous proxy: path touch and width continuity increase split tendency while same-region boundary grouping reduces it; not a region split decision",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_cue_ratio",
            "score": round(
                mean(1.0 if item["has_boundary_cue"] else 0.0 for item in path_region_boundary_cue_evidence),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_regions_with_same_region_boundary_proximity",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "combines bbox path-region touch with same-region boundary proximity; proxy for path split versus boundary grouping cue",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_cue_count_mean",
            "score": round(
                mean(item["boundary_cue_count"] for item in path_region_boundary_cue_evidence),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_region_same_region_boundary_cue_count_mean",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "counts same-region boundary cue records for path-touched regions; count is traceability evidence, not cue quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_cue_strength_mean",
            "score": round(
                mean(item["boundary_proximity"] or 0.0 for item in path_region_boundary_cue_evidence),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_region_same_region_boundary_proximity_mean",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "mean same-region boundary proximity for path-touched regions; regions without scoped boundary cue contribute zero",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_grouping_strength_mean",
            "score": round(
                mean(item["boundary_grouping_strength"] for item in path_region_boundary_cue_evidence),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_region_same_region_boundary_length_weighted_grouping_strength_mean",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "uses authored grouping_strength weighted by parsed boundary length for path-touched regions; missing same-region cues contribute zero",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_walk_block_mean",
            "score": round(
                mean(item["boundary_walk_block"] for item in path_region_boundary_cue_evidence),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_region_same_region_boundary_length_weighted_walk_block_mean",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "uses authored walk_block weighted by parsed boundary length for path-touched regions; missing same-region cues contribute zero",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_see_block_mean",
            "score": round(
                mean(item["boundary_see_block"] for item in path_region_boundary_cue_evidence),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_region_same_region_boundary_length_weighted_see_block_mean",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "uses authored see_block weighted by parsed boundary length for path-touched regions; missing same-region cues contribute zero",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_walk_see_gap_mean",
            "score": round(
                mean(item["boundary_walk_see_gap"] for item in path_region_boundary_cue_evidence),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_region_same_region_boundary_length_weighted_walk_see_gap_mean",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "walk-see channel split for same-region boundary cues on path-touched regions; authored weights only, not transparency calibration",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_touched_region_boundary_cue_perimeter_influence_mean",
            "score": round(
                mean(
                    item["boundary_influence_per_region_perimeter"]
                    for item in path_region_boundary_cue_evidence
                ),
                4,
            )
            if path_region_boundary_cue_evidence
            else None,
            "status": "computed" if path_region_boundary_cue_evidence else "not_available",
            "method": "path_touched_region_same_region_boundary_influence_per_region_bbox_perimeter_mean",
            "evidence": [item["region_id"] for item in path_region_boundary_cue_evidence],
            "path_region_boundary_cue_evidence": path_region_boundary_cue_evidence,
            "uncertainty": "same-region boundary influence normalized by region bbox perimeter; missing cues contribute zero and bbox perimeter is only a scale proxy",
        },
        {
            "view_id": "path_connectivity",
            "metric": "entry_to_region_reachability",
            "score": round(entry_ratio * region_ratio, 4),
            "status": "computed",
            "method": "entry_path_region_touch_graph_proxy",
            "evidence": [edge["id"] for edge in entry_edges + region_edges],
            "uncertainty": "minimal graph proxy; replace with shortest paths over negative space",
        },
        {
            "view_id": "path_connectivity",
            "metric": "walk_visibility_cost_gap",
            "score": round(walk_cost - visibility_cost, 4),
            "status": "computed",
            "method": "boundary_weighted_walk_minus_visibility_graph_cost",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]]
            + [edge["id"] for edge in graphs["visibility"]["edges"]],
            "uncertainty": "mode split uses boundary weight averages; no true walk/visibility graph yet",
        },
        {
            "view_id": "path_connectivity",
            "metric": "line_of_sight_entry_region_ratio",
            "score": round(
                mean(1.0 if item["visible"] else 0.0 for item in line_of_sight_evidence),
                4,
            )
            if line_of_sight_evidence
            else None,
            "status": "computed" if line_of_sight_evidence else "not_available",
            "method": "entry_region_centerline_see_block_intersection",
            "evidence": [
                item["region_id"] for item in line_of_sight_evidence if item["visible"]
            ],
            "line_of_sight_evidence": line_of_sight_evidence,
            "uncertainty": "centerline ray proxy using authored see_block boundaries; not isovist or visibility graph analysis",
        },
        {
            "view_id": "path_connectivity",
            "metric": "line_of_sight_region_pair_ratio",
            "score": round(
                mean(
                    1.0 if item["visible"] else 0.0
                    for item in line_of_sight_region_pair_evidence
                ),
                4,
            )
            if line_of_sight_region_pair_evidence
            else None,
            "status": "computed" if line_of_sight_region_pair_evidence else "not_available",
            "method": "region_pair_centerline_see_block_intersection",
            "evidence": [
                f"{item['region_a']}:{item['region_b']}"
                for item in line_of_sight_region_pair_evidence
                if item["visible"]
            ],
            "line_of_sight_region_pair_evidence": line_of_sight_region_pair_evidence,
            "uncertainty": "region-centerline visibility proxy using authored see_block boundaries; not isovist or visibility graph analysis",
        },
        {
            "view_id": "path_connectivity",
            "metric": "line_of_sight_graph_visible_edge_ratio",
            "score": line_of_sight_graph["metrics"]["visible_edge_ratio"],
            "status": "computed",
            "method": "line_of_sight_graph_edge_visibility_ratio",
            "evidence": line_of_sight_graph["metrics"]["visible_edge_ids"],
            "visible_edge_ids": line_of_sight_graph["metrics"]["visible_edge_ids"],
            "uncertainty": "centerline visibility graph proxy; not full VGA, isovist, or visual integration",
        },
        {
            "view_id": "path_connectivity",
            "metric": "line_of_sight_graph_blocked_edge_ratio",
            "score": line_of_sight_graph["metrics"]["blocked_edge_ratio"],
            "status": "computed",
            "method": "line_of_sight_graph_edge_visibility_ratio",
            "evidence": line_of_sight_graph["metrics"]["blocked_edge_ids"],
            "blocked_edge_ids": line_of_sight_graph["metrics"]["blocked_edge_ids"],
            "blocking_boundary_ids": line_of_sight_graph["metrics"]["blocking_boundary_ids"],
            "uncertainty": "centerline visibility graph proxy; blocked edges identify direct-sight obstructions, not visual-exposure fields",
        },
        {
            "view_id": "path_connectivity",
            "metric": "line_of_sight_graph_blocking_boundary_count",
            "score": len(line_of_sight_graph["metrics"]["blocking_boundary_ids"]),
            "status": "computed",
            "method": "line_of_sight_graph_unique_blocking_boundary_count",
            "evidence": line_of_sight_graph["metrics"]["blocking_boundary_ids"],
            "blocking_boundary_ids": line_of_sight_graph["metrics"]["blocking_boundary_ids"],
            "blocked_edge_ids": line_of_sight_graph["metrics"]["blocked_edge_ids"],
            "blocking_boundary_edge_evidence": line_of_sight_graph["metrics"][
                "blocking_boundary_edge_evidence"
            ],
            "uncertainty": "unique authored see_block boundaries intersecting blocked centerline graph edges; not obstacle attribution from full VGA or isovist fields",
        },
        {
            "view_id": "path_connectivity",
            "metric": "isovist_radial_blocked_ray_ratio",
            "score": isovist_radial_proxy["metrics"]["blocked_ray_ratio"],
            "status": isovist_radial_proxy["status"],
            "method": isovist_radial_proxy["method"],
            "evidence": [
                f"{ray['vantage_id']}:{ray['angle_degrees']}"
                for ray in isovist_radial_proxy["ray_evidence"]
                if ray["blocked_by_see_block"]
            ],
            "blocked_ray_count": isovist_radial_proxy["metrics"]["blocked_ray_count"],
            "ray_count": isovist_radial_proxy["metrics"]["ray_count"],
            "isovist_ray_evidence": isovist_radial_proxy["ray_evidence"],
            "uncertainty": isovist_radial_proxy["uncertainty"],
        },
        {
            "view_id": "path_connectivity",
            "metric": "isovist_radial_hit_polygon_area_mean",
            "score": isovist_radial_proxy["metrics"]["mean_hit_polygon_area"],
            "status": isovist_radial_proxy["status"],
            "method": "radial_isovist_hit_point_polygon_area_proxy",
            "evidence": [
                item["vantage_id"]
                for item in isovist_radial_proxy["isovist_area_evidence"]
            ],
            "isovist_area_evidence": isovist_radial_proxy["isovist_area_evidence"],
            "uncertainty": "area of polygon formed by ordered radial ray hit points; proxy, not full isovist polygon, VGA, or visual integration",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_entry_region_reachability",
            "score": graph_metrics["entry_region_reachability"],
            "status": "computed",
            "method": "bbox_touch_graph_bfs_reachability",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]],
            "reached_region_ids": graph_metrics["reached_region_ids"],
            "unreached_region_ids": graph_metrics["unreached_region_ids"],
            "uncertainty": "BFS over bbox-touch proxy graph; not a navigation graph",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_entry_region_capacity_proxy",
            "score": round(
                graph_metrics["entry_region_reachability"]
                * width_continuity
                * walk_passability,
                4,
            ),
            "status": "computed",
            "method": "bbox_touch_reachability_times_path_width_times_walk_passability",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]] + list(path_geometry),
            "capacity_factors": capacity_factors,
            "uncertainty": "capacity proxy combines bbox-touch reachability, authored path width continuity, and average walk passability; not max-flow or route capacity",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_mean_entry_region_hops",
            "score": graph_metrics["entry_region_mean_hops"],
            "status": "computed",
            "method": "bbox_touch_graph_bfs_mean_hops",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]],
            "uncertainty": "hop count over proxy graph; not metric path length",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_mean_entry_region_shortest_distance",
            "score": graph_metrics["entry_region_mean_shortest_distance"],
            "status": "computed",
            "method": "bbox_touch_graph_dijkstra_distance",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]],
            "uncertainty": "Dijkstra over node-center proxy edges; not a true walking path",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_mean_entry_region_detour_ratio",
            "score": graph_metrics["entry_region_mean_detour_ratio"],
            "status": "computed",
            "method": "bbox_touch_graph_shortest_over_direct_distance",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]],
            "uncertainty": "detour ratio is proxy graph length over direct node distance; not final circulation analysis",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_dead_end_ratio",
            "score": graph_metrics["dead_end_ratio"],
            "status": "computed",
            "method": "bbox_touch_graph_degree_ratio",
            "evidence": [node["id"] for node in graphs["walk"]["nodes"]],
            "dead_end_nodes": graph_metrics["dead_end_nodes"],
            "uncertainty": "degree count over proxy graph; path junction extraction pending",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_component_count",
            "score": graph_metrics["component_count"],
            "status": "computed",
            "method": "bbox_touch_graph_connected_components",
            "evidence": graph_metrics["components"],
            "uncertainty": "connected components over proxy graph; route graph component extraction pending",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_loop_count",
            "score": graph_metrics["loop_count"],
            "status": "computed",
            "method": "undirected_cycle_rank_on_bbox_touch_graph",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]],
            "cycle_rank_inputs": graph_metrics["cycle_rank_inputs"],
            "uncertainty": "cycle rank over proxy graph; true loops need negative-space graph",
        },
        {
            "view_id": "path_connectivity",
            "metric": "graph_loop_ratio",
            "score": graph_metrics["loop_ratio"],
            "status": "computed",
            "method": "undirected_cycle_rank_over_edge_count",
            "evidence": [edge["id"] for edge in graphs["walk"]["edges"]],
            "cycle_rank_inputs": graph_metrics["cycle_rank_inputs"],
            "uncertainty": "cycle rank normalized by proxy graph edge count; true loops need negative-space graph",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_width_continuity",
            "score": round(mean(width_scores), 4) if width_scores else None,
            "status": "computed" if width_scores else "not_available",
            "method": "path_polygon_adjacent_edge_width_cv_score",
            "evidence": list(path_geometry),
            "uncertainty": "width is inferred from path polygon edge pairs; replace with medial-axis width field later",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_min_clearance_to_blocker",
            "score": round(mean(clearance_values), 4) if clearance_values else None,
            "status": "computed" if clearance_values else "not_available",
            "method": "path_polygon_to_blocker_bbox_min_gap",
            "evidence": clearance_evidence,
            "uncertainty": "path polygon to blocker bbox clearance proxy with bbox fallback, not a medial-axis or true negative-space clearance field",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_blocker_overlap_ratio",
            "score": round(mean(overlap_ratios), 4) if overlap_ratios else None,
            "status": "computed" if overlap_ratios else "not_available",
            "method": "path_polygon_blocker_bbox_zero_gap_ratio",
            "evidence": overlap_evidence,
            "uncertainty": f"{sum(overlap_counts)} blocker overlaps in authored path proxy; replace with negative-space conflict geometry",
        },
        {
            "view_id": "path_connectivity",
            "metric": "path_blocker_overlap_area_ratio",
            "score": round(mean(overlap_area_ratios), 4)
            if overlap_area_ratios
            else None,
            "status": "computed" if overlap_area_ratios else "not_available",
            "method": "path_polygon_blocker_union_overlap_area",
            "evidence": overlap_area_evidence,
            "uncertainty": "blocker union overlap area proxy; still not negative-space conflict geometry",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_walkable_cell_ratio",
            "score": sampled_walkable_space["walkable_cell_ratio"],
            "status": "computed",
            "method": "sampled_occupancy_grid_bfs_proxy",
            "evidence": sampled_walkable_space["blocker_evidence"],
            "uncertainty": "sampled free-cell ratio over occupancy grid; proxy, not CAD boolean negative space",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_min_clearance_to_walk_blocker",
            "score": sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                "min_clearance"
            ],
            "status": "computed"
            if sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                "min_clearance"
            ]
            is not None
            else "not_available",
            "method": sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                "method"
            ],
            "evidence": sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                "blocker_evidence"
            ],
            "clearance": sampled_walkable_space["sampled_clearance_to_walk_blockers"],
            "uncertainty": "sampled free-cell center clearance to walk blockers; proxy, not medial-axis width field or navmesh clearance",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_zero_clearance_cell_ratio",
            "score": round(
                sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                    "zero_clearance_sample_count"
                ]
                / max(
                    1,
                    sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                        "sample_count"
                    ],
                ),
                4,
            ),
            "status": "computed"
            if sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                "sample_count"
            ]
            else "not_available",
            "method": "sampled_zero_clearance_cells_over_clearance_samples",
            "evidence": sampled_walkable_space["sampled_clearance_to_walk_blockers"][
                "min_clearance_samples"
            ],
            "clearance": sampled_walkable_space["sampled_clearance_to_walk_blockers"],
            "uncertainty": "share of sampled free cells whose center has zero clearance to a walk blocker; flags occupancy-threshold disagreement, not final geometry truth",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_entry_reachable_min_clearance_to_walk_blocker",
            "score": sampled_walkable_space[
                "entry_reachable_clearance_to_walk_blockers"
            ]["min_clearance"],
            "status": "computed"
            if sampled_walkable_space["entry_reachable_clearance_to_walk_blockers"][
                "min_clearance"
            ]
            is not None
            else "not_available",
            "method": sampled_walkable_space[
                "entry_reachable_clearance_to_walk_blockers"
            ]["method"],
            "evidence": sampled_walkable_space[
                "entry_reachable_clearance_to_walk_blockers"
            ]["blocker_evidence"],
            "clearance": sampled_walkable_space[
                "entry_reachable_clearance_to_walk_blockers"
            ],
            "uncertainty": "entry-reachable sampled free-cell center clearance to walk blockers; proxy, not route-width field or navmesh clearance",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_negative_space_area_ratio_delta",
            "score": area_ratio_delta,
            "status": "computed" if area_ratio_delta is not None else "not_available",
            "method": "absolute_sampled_walkable_minus_negative_space_area_ratio",
            "evidence": {
                "sampled_walkable_cell_ratio": sampled_area_ratio,
                "negative_space_area_ratio_proxy": negative_area_ratio,
            },
            "uncertainty": "absolute difference between sampled occupancy and rect-cell negative-space area proxies; flags proxy disagreement, not geometric truth",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_area_ratio_proxy",
            "score": negative_space["negative_space_area_ratio_proxy"],
            "status": negative_space["status"],
            "method": negative_space["method"],
            "evidence": negative_space["blocker_evidence"],
            "negative_space": negative_space,
            "uncertainty": negative_space["uncertainty"],
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_polygon_overlap_risk_count",
            "score": len(negative_space.get("polygon_blocker_overlap_risk_evidence", [])),
            "status": negative_space["status"],
            "method": "nonidentical_polygon_blocker_overlap_detection",
            "evidence": negative_space.get("polygon_blocker_overlap_risk_evidence", []),
            "uncertainty": "overlapping nonidentical polygon blockers exceed the current rect-cell union proxy; use CAD boolean geometry before treating area/topology as final",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_component_count",
            "score": negative_space.get("component_count"),
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": negative_space.get("component_areas", []),
            "component_rects": negative_space.get("component_rects", []),
            "component_area_total": negative_space.get("component_area_total"),
            "component_cell_count_total": negative_space.get(
                "component_cell_count_total"
            ),
            "component_cell_area_sum_total": negative_space.get(
                "component_cell_area_sum_total"
            ),
            "negative_space_component_area_residual": negative_space.get(
                "negative_space_component_area_residual"
            ),
            "negative_space_component_area_residual_ratio": negative_space.get(
                "negative_space_component_area_residual_ratio"
            ),
            "uncertainty": "continuous rect-cell decomposition over room bbox and blocker bboxes; proxy, not CAD boolean topology",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_free_polygon_count",
            "score": len(negative_space.get("free_space_polygons", [])),
            "status": negative_space["status"],
            "method": "room_polygon_rect_cell_free_space_polygons_proxy",
            "evidence": [
                f"component_{item['component_index']}_cell_{item['cell_index']}"
                for item in negative_space.get("free_space_polygons", [])
            ],
            "free_space_polygons": negative_space.get("free_space_polygons", []),
            "uncertainty": "rect-cell free-space polygon evidence for downstream geometry adapters; not CAD boolean room-minus-blocker polygons",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_room_minus_blocker_polygon_count",
            "score": len(negative_space.get("room_minus_blocker_polygons", [])),
            "status": negative_space["status"],
            "method": "rect_cell_room_minus_blocker_boundary_union_proxy",
            "evidence": [
                f"component_{item['component_index']}"
                for item in negative_space.get("room_minus_blocker_polygons", [])
            ],
            "room_minus_blocker_polygons": negative_space.get(
                "room_minus_blocker_polygons",
                [],
            ),
            "uncertainty": "merged boundary loops over rect-cell negative-space components; proxy, not CAD boolean room-minus-blocker topology",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_polygon_count",
            "score": len(negative_space.get("cad_room_minus_blocker_polygons", [])),
            "status": "computed"
            if negative_space.get("cad_room_minus_blocker_polygons")
            else "not_available",
            "method": "shapely_room_polygon_difference_blocker_union",
            "evidence": [
                f"component_{item['component_index']}"
                for item in negative_space.get("cad_room_minus_blocker_polygons", [])
            ],
            "cad_room_minus_blocker_polygons": negative_space.get(
                "cad_room_minus_blocker_polygons",
                [],
            ),
            "uncertainty": "Shapely polygon difference over current authored room/blocker polygons; still not Rhino/VisualARQ hosted topology or navmesh faces",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_area_residual_ratio",
            "score": negative_space.get("cad_room_minus_blocker_area_residual_ratio"),
            "status": "computed"
            if negative_space.get("cad_room_minus_blocker_polygons")
            else "not_available",
            "method": "shapely_room_minus_blocker_area_minus_negative_space_area",
            "evidence": {
                "cad_room_minus_blocker_area_total": negative_space.get(
                    "cad_room_minus_blocker_area_total"
                ),
                "negative_space_area": negative_space.get("negative_space_area"),
                "cad_room_minus_blocker_area_residual": negative_space.get(
                    "cad_room_minus_blocker_area_residual"
                ),
            },
            "uncertainty": "area closure check between Shapely polygon difference and current negative-space area proxy; flags disagreement but is not Rhino/BIM/navmesh validation",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_largest_component_area_ratio",
            "score": negative_space.get(
                "cad_room_minus_blocker_largest_component_area_ratio"
            ),
            "status": "computed"
            if negative_space.get("cad_room_minus_blocker_polygons")
            else "not_available",
            "method": "shapely_largest_component_area_over_total_free_area",
            "evidence": {
                "largest_component_area": negative_space.get(
                    "cad_room_minus_blocker_largest_component_area"
                ),
                "cad_room_minus_blocker_area_total": negative_space.get(
                    "cad_room_minus_blocker_area_total"
                ),
                "component_areas": negative_space.get(
                    "cad_room_minus_blocker_component_areas",
                    [],
                ),
            },
            "uncertainty": "largest Shapely free-space component area share; fragmentation severity only, not route reachability or route quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_entry_connected_region_ratio",
            "score": round(
                len(cad_entry_connected_region_ids) / max(1, len(cad_region_ids)),
                4,
            )
            if cad_region_ids
            else None,
            "status": "computed"
            if cad_touch_evidence and cad_region_ids
            else "not_available",
            "method": "shapely_component_entry_region_touch_proxy",
            "evidence": cad_entry_connected_region_ids,
            "entry_connected_region_ids": cad_entry_connected_region_ids,
            "non_entry_connected_region_ids": [
                region_id
                for region_id in cad_region_ids
                if region_id not in cad_entry_connected_region_ids
            ],
            "cad_room_minus_blocker_component_touch_evidence": cad_touch_evidence,
            "uncertainty": "Shapely component touch/overlap evidence over current authored polygons; not hosted doorway topology, navmesh reachability, or route quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_entry_connected_area_ratio",
            "score": negative_space.get(
                "cad_room_minus_blocker_entry_connected_area_ratio"
            ),
            "status": "computed"
            if negative_space.get("cad_room_minus_blocker_polygons")
            else "not_available",
            "method": "shapely_component_entry_touched_area_ratio_proxy",
            "evidence": {
                "entry_connected_component_ids": negative_space.get(
                    "cad_room_minus_blocker_entry_connected_component_ids",
                    [],
                ),
                "non_entry_connected_component_ids": negative_space.get(
                    "cad_room_minus_blocker_non_entry_connected_component_ids",
                    [],
                ),
                "entry_connected_component_area": negative_space.get(
                    "cad_room_minus_blocker_entry_connected_component_area"
                ),
                "non_entry_connected_component_area": negative_space.get(
                    "cad_room_minus_blocker_non_entry_connected_component_area"
                ),
                "cad_room_minus_blocker_area_total": negative_space.get(
                    "cad_room_minus_blocker_area_total"
                ),
            },
            "uncertainty": "entry-touched Shapely component area share; component-level evidence only, not route reachability or route quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_entry_connected_component_ratio",
            "score": negative_space.get(
                "cad_room_minus_blocker_entry_connected_component_ratio"
            ),
            "status": "computed"
            if negative_space.get("cad_room_minus_blocker_polygons")
            else "not_available",
            "method": "shapely_component_entry_touched_component_count_proxy",
            "evidence": {
                "entry_connected_component_ids": negative_space.get(
                    "cad_room_minus_blocker_entry_connected_component_ids",
                    [],
                ),
                "non_entry_connected_component_ids": negative_space.get(
                    "cad_room_minus_blocker_non_entry_connected_component_ids",
                    [],
                ),
                "component_count": len(
                    negative_space.get("cad_room_minus_blocker_polygons", [])
                ),
            },
            "uncertainty": "entry-touched Shapely component count share; component-level evidence only, not route reachability or route quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_component_graph_edge_count",
            "score": cad_component_graph["edge_count"],
            "status": "computed" if cad_touch_evidence else "not_available",
            "method": "shapely_component_entry_region_touch_graph_proxy",
            "evidence": {
                "node_count": cad_component_graph["node_count"],
                "edge_count": cad_component_graph["edge_count"],
                "component_node_count": sum(
                    1
                    for node in cad_component_graph["nodes"]
                    if node["kind"] == "cad_free_space_component"
                ),
                "entry_node_count": sum(
                    1 for node in cad_component_graph["nodes"] if node["kind"] == "entry"
                ),
                "region_node_count": sum(
                    1 for node in cad_component_graph["nodes"] if node["kind"] == "region"
                ),
            },
            "uncertainty": "graph-shaped Shapely component/entry/region touch evidence for adapter handoff; not navmesh, skeleton, hosted topology, or route graph",
        },
        {
            "view_id": "path_connectivity",
            "metric": "cad_room_minus_blocker_entry_connected_region_pair_ratio",
            "score": round(
                len(cad_entry_connected_region_pair_evidence)
                / max(1, cad_total_region_pair_count),
                4,
            )
            if cad_region_ids
            else None,
            "status": "computed"
            if cad_touch_evidence and cad_region_ids
            else "not_available",
            "method": "shapely_component_entry_connected_region_pair_proxy",
            "evidence": [
                f"{item['region_a']}->{item['region_b']}"
                for item in cad_entry_connected_region_pair_evidence
            ],
            "region_pair_evidence": cad_entry_connected_region_pair_evidence,
            "entry_connected_region_pair_count": len(
                cad_entry_connected_region_pair_evidence
            ),
            "total_region_pair_count": cad_total_region_pair_count,
            "uncertainty": "region pairs sharing an entry-touched Shapely component; component-level evidence only, not route reachability or route quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_free_polygon_adjacency_count",
            "score": len(negative_space.get("free_space_polygon_adjacency", [])),
            "status": negative_space["status"],
            "method": "room_polygon_rect_cell_shared_edge_adjacency_proxy",
            "evidence": [
                f"component_{item['component_index']}_cell_{item['from_cell']}_cell_{item['to_cell']}"
                for item in negative_space.get("free_space_polygon_adjacency", [])
            ],
            "free_space_polygon_adjacency": negative_space.get(
                "free_space_polygon_adjacency",
                [],
            ),
            "uncertainty": "shared-edge graph over rect-cell free-space polygons; proxy, not navmesh, skeleton, or shortest-path route graph",
        },
        {
            "view_id": "path_connectivity",
            "metric": "free_space_polygon_graph_cycle_rank",
            "score": negative_space.get("free_space_polygon_graph", {})
            .get("metrics", {})
            .get("cycle_rank"),
            "status": negative_space["status"],
            "method": "room_polygon_rect_cell_shared_edge_graph_proxy",
            "evidence": {
                "node_count": negative_space.get("free_space_polygon_graph", {}).get(
                    "node_count"
                ),
                "edge_count": negative_space.get("free_space_polygon_graph", {}).get(
                    "edge_count"
                ),
                "component_count": negative_space.get("free_space_polygon_graph", {})
                .get("metrics", {})
                .get("component_count"),
                "dead_end_nodes": negative_space.get("free_space_polygon_graph", {})
                .get("metrics", {})
                .get("dead_end_nodes", []),
            },
            "uncertainty": "cycle rank over rect-cell free-space graph; proxy, not navmesh loop topology or medial-axis routing",
        },
        {
            "view_id": "path_connectivity",
            "metric": "free_space_polygon_graph_mean_entry_region_distance",
            "score": round(
                mean(
                    item["distance"]
                    for item in entry_region_distance_evidence
                ),
                4,
            )
            if entry_region_distance_evidence
            else None,
            "status": "computed"
            if entry_region_distance_evidence
            else "not_available",
            "method": "room_polygon_rect_cell_shared_edge_graph_distance_proxy",
            "evidence": entry_region_distance_evidence,
            "uncertainty": "shortest center-to-center distance over rect-cell free-space graph; proxy, not navmesh, medial-axis, or certified route distance",
        },
        {
            "view_id": "path_connectivity",
            "metric": "free_space_polygon_graph_mean_edge_clearance_width",
            "score": round(
                mean(
                    edge["clearance_width"]
                    for edge in negative_space.get("free_space_polygon_graph", {}).get(
                        "edges",
                        [],
                    )
                ),
                4,
            )
            if negative_space.get("free_space_polygon_graph", {}).get("edges")
            else None,
            "status": "computed"
            if negative_space.get("free_space_polygon_graph", {}).get("edges")
            else "not_available",
            "method": "room_polygon_rect_cell_shared_edge_width_proxy",
            "evidence": [
                {
                    "edge_id": edge["id"],
                    "a": edge["a"],
                    "b": edge["b"],
                    "clearance_width": edge["clearance_width"],
                    "weight": edge["weight"],
                }
                for edge in negative_space.get("free_space_polygon_graph", {}).get(
                    "edges",
                    [],
                )
            ],
            "uncertainty": "shared-edge length over rect-cell free-space graph; proxy, not medial-axis clearance, navmesh portal width, or code-compliant passage width",
        },
        {
            "view_id": "path_connectivity",
            "metric": "free_space_polygon_graph_mean_entry_region_min_clearance_width",
            "score": round(
                mean(
                    item["min_clearance_width"]
                    for item in entry_region_distance_evidence
                    if item.get("min_clearance_width") is not None
                ),
                4,
            )
            if entry_region_min_clearance_evidence
            else None,
            "status": "computed"
            if entry_region_min_clearance_evidence
            else "not_available",
            "method": "room_polygon_rect_cell_shared_edge_path_bottleneck_width_proxy",
            "evidence": entry_region_distance_evidence,
            "uncertainty": "minimum shared-edge width along rect-cell entry-region paths; proxy, not medial-axis clearance, navmesh portal bottleneck, or egress capacity",
        },
        {
            "view_id": "path_connectivity",
            "metric": "free_space_polygon_graph_mean_entry_region_widest_clearance_width",
            "score": round(
                mean(
                    item["widest_clearance_width"]
                    for item in entry_region_widest_clearance_evidence
                ),
                4,
            )
            if entry_region_widest_clearance_evidence
            else None,
            "status": "computed"
            if entry_region_widest_clearance_evidence
            else "not_available",
            "method": "room_polygon_rect_cell_shared_edge_widest_path_width_proxy",
            "evidence": entry_region_widest_path_evidence,
            "uncertainty": "max-min shared-edge width over rect-cell entry-region paths; proxy, not medial-axis clearance, navmesh routing, or egress capacity",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_component_area_residual_ratio",
            "score": negative_space.get(
                "negative_space_component_area_residual_ratio"
            ),
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": {
                "negative_space_area": negative_space.get("negative_space_area"),
                "component_area_total": negative_space.get("component_area_total"),
                "component_cell_area_sum_total": negative_space.get(
                    "component_cell_area_sum_total"
                ),
                "negative_space_component_area_residual": negative_space.get(
                    "negative_space_component_area_residual"
                ),
            },
            "uncertainty": "descriptor-level closure check between negative-space area and rect-cell components; not CAD boolean validation",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_component_cell_area_residual_ratio",
            "score": negative_space_graph_metrics[
                "max_component_cell_area_residual_ratio"
            ],
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": negative_space_graph_metrics[
                "component_cell_area_residuals"
            ],
            "component_cell_counts": negative_space_graph_metrics[
                "component_cell_counts"
            ],
            "component_cell_area_sums": negative_space_graph_metrics[
                "component_cell_area_sums"
            ],
            "uncertainty": "internal rect-cell area closure check for negative-space component evidence; not CAD boolean validation",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_largest_component_area_ratio",
            "score": negative_space.get("largest_component_area_ratio"),
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": negative_space.get("component_areas", []),
            "uncertainty": "largest decomposed free rectangle-component share; proxy, not navmesh or skeleton connectivity",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_entry_connected_component_count",
            "score": negative_space.get("entry_connected_component_count"),
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": negative_space_edges,
            "entry_component_evidence": negative_space.get("entry_component_evidence", []),
            "uncertainty": "entry contact is rect-touch against decomposed negative-space cells; proxy, not hosted doorway topology",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_entry_connected_component_ratio",
            "score": negative_space_graph_metrics["entry_connected_component_ratio"],
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": entry_connected_component_edges,
            "entry_connected_component_ids": negative_space_graph_metrics[
                "entry_connected_component_ids"
            ],
            "non_entry_connected_component_ids": negative_space_graph_metrics[
                "non_entry_connected_component_ids"
            ],
            "uncertainty": "share of decomposed negative-space components touching entries; rect-touch proxy, not navmesh component reachability",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_entry_connected_area_ratio",
            "score": negative_space_graph_metrics["entry_connected_area_ratio"],
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": negative_space_edges,
            "entry_component_evidence": negative_space.get("entry_component_evidence", []),
            "uncertainty": "share of decomposed negative-space area touching entries; proxy for candidate path space, not route certification",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_non_entry_connected_area_ratio",
            "score": negative_space_graph_metrics["non_entry_connected_area_ratio"],
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": negative_space_edges,
            "entry_component_evidence": negative_space.get("entry_component_evidence", []),
            "uncertainty": "share of decomposed negative-space area not touching entries; proxy for leftover non-path space, not a semantic dead-space classifier",
        },
        {
            "view_id": "path_connectivity",
            "metric": "candidate_path_area_ratio_proxy",
            "score": candidate_path_score,
            "status": negative_space["status"],
            "method": "entry_connected_negative_space_area_times_path_width_continuity",
            "evidence": negative_space_edges + list(path_geometry),
            "candidate_path_inputs": candidate_path_inputs,
            "uncertainty": "candidate path proxy combines entry-connected negative-space area with authored path width continuity; not a navmesh, skeleton, or route classifier",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_entry_connected_region_ratio",
            "score": negative_space_graph_metrics["entry_connected_region_ratio"],
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": [edge["id"] for edge in entry_connected_region_edges],
            "entry_connected_region_ids": negative_space_graph_metrics[
                "entry_connected_region_ids"
            ],
            "non_entry_connected_region_ids": negative_space_graph_metrics[
                "non_entry_connected_region_ids"
            ],
            "uncertainty": "regions touched by entry-connected negative-space components; proxy, not shortest-path or route certification",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_mean_entry_region_free_polygon_distance",
            "score": negative_space_graph_metrics[
                "mean_entry_region_free_polygon_distance"
            ],
            "status": "computed"
            if negative_space_graph_metrics[
                "mean_entry_region_free_polygon_distance"
            ]
            is not None
            else "not_available",
            "method": "entry_to_region_rect_cell_adjacency_shortest_path_proxy",
            "evidence": [
                item["region_id"]
                for item in negative_space_graph_metrics[
                    "entry_region_free_polygon_distance_evidence"
                ]
            ],
            "entry_region_free_polygon_distance_evidence": negative_space_graph_metrics[
                "entry_region_free_polygon_distance_evidence"
            ],
            "uncertainty": "shortest edge count over rect-cell free-space adjacency; proxy, not navmesh, medial-axis, or route-quality distance",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_mean_entry_region_free_polygon_path_length",
            "score": negative_space_graph_metrics[
                "mean_entry_region_free_polygon_path_length"
            ],
            "status": "computed"
            if negative_space_graph_metrics[
                "mean_entry_region_free_polygon_path_length"
            ]
            is not None
            else "not_available",
            "method": "entry_to_region_rect_cell_centerline_length_proxy",
            "evidence": [
                item["region_id"]
                for item in negative_space_graph_metrics[
                    "entry_region_free_polygon_distance_evidence"
                ]
            ],
            "entry_region_free_polygon_distance_evidence": negative_space_graph_metrics[
                "entry_region_free_polygon_distance_evidence"
            ],
            "uncertainty": "center-to-center length over rect-cell free-space path_cells; proxy, not navmesh polyline, medial-axis path, or route-quality distance",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_entry_connected_region_pair_ratio",
            "score": negative_space_graph_metrics["entry_connected_region_pair_ratio"],
            "status": negative_space["status"],
            "method": negative_space.get("component_method"),
            "evidence": [
                f"component_{item['component']}:{item['region_a']}:{item['region_b']}"
                for item in entry_connected_region_pair_evidence
            ],
            "region_pair_evidence": entry_connected_region_pair_evidence,
            "entry_connected_region_pair_count": negative_space_graph_metrics[
                "entry_connected_region_pair_count"
            ],
            "total_region_pair_count": negative_space_graph_metrics[
                "total_region_pair_count"
            ],
            "unconnected_region_pair_evidence": unconnected_region_pair_evidence,
            "uncertainty": "region pairs sharing an entry-connected negative-space component; proxy, not route distance or route quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "candidate_path_region_pair_ratio_proxy",
            "score": round(
                candidate_path_score
                * negative_space_graph_metrics["entry_connected_region_pair_count"]
                / max(1, negative_space_graph_metrics["total_region_pair_count"]),
                4,
            ),
            "status": negative_space["status"],
            "method": "candidate_path_area_times_entry_connected_region_pair_ratio",
            "evidence": [
                f"component_{item['component']}:{item['region_a']}:{item['region_b']}"
                for item in entry_connected_region_pair_evidence
            ],
            "region_pair_evidence": entry_connected_region_pair_evidence,
            "candidate_path_pair_inputs": candidate_path_pair_inputs,
            "uncertainty": "candidate path pair proxy combines candidate path area with same-component region-pair evidence; not route quality or shortest-path routing",
        },
        {
            "view_id": "path_connectivity",
            "metric": "negative_space_entry_connected_region_area_coverage_ratio",
            "score": round(
                mean(
                    item["coverage_ratio"]
                    for item in entry_connected_region_area_coverage_evidence
                ),
                4,
            )
            if entry_connected_region_area_coverage_evidence
            else None,
            "status": negative_space["status"]
            if entry_connected_region_area_coverage_evidence
            else "not_available",
            "method": negative_space.get("component_method"),
            "evidence": [
                item["region"]
                for item in entry_connected_region_area_coverage_evidence
            ],
            "region_area_coverage_evidence": entry_connected_region_area_coverage_evidence,
            "uncertainty": "mean share of each region bbox area overlapped by entry-connected negative-space components; continuous proxy, not route quality",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_entry_reachable_cell_ratio",
            "score": sampled_walkable_space["entry_reachable_cell_ratio"],
            "status": "computed",
            "method": "sampled_occupancy_grid_bfs_proxy",
            "evidence": [entry["id"] for entry in scene.get("entries", [])],
            "uncertainty": "four-neighbor BFS over sampled cells; proxy, not a navigation mesh",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_entry_reachable_region_ratio",
            "score": sampled_walkable_space["entry_reachable_region_ratio"],
            "status": "computed",
            "method": "sampled_occupancy_grid_bfs_proxy",
            "evidence": [region["id"] for region in scene.get("regions", [])],
            "uncertainty": "region has any entry-reachable sampled free cell; proxy until negative-space geometry exists",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_visibility_reachable_region_ratio",
            "score": sampled_walkable_space["visibility_reachable_region_ratio"],
            "status": "computed",
            "method": "sampled_visibility_grid_bfs_proxy",
            "evidence": sampled_walkable_space["visibility_blocker_evidence"],
            "uncertainty": "see-block weighted sampled BFS proxy; not isovist, ray casting, or visibility graph analysis",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_visibility_only_region_ratio",
            "score": sampled_walkable_space["visibility_only_region_ratio"],
            "status": "computed",
            "method": "sampled_visibility_only_minus_walk_reachability_proxy",
            "evidence": sampled_walkable_space["region_reachability"],
            "uncertainty": "regions reachable in see-block channel but not walk-block channel; proxy for visible-but-not-walkable separation",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_walk_only_region_ratio",
            "score": sampled_walkable_space["walk_only_region_ratio"],
            "status": "computed",
            "method": "sampled_walk_only_minus_visibility_reachability_proxy",
            "evidence": sampled_walkable_space["region_reachability"],
            "uncertainty": "regions reachable in walk-block channel but not see-block channel; proxy for walkable-but-not-visible separation",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_walk_visibility_disagreement_region_ratio",
            "score": sampled_walkable_space["walk_visibility_disagreement_region_ratio"],
            "status": "computed",
            "method": "sampled_walk_visibility_reachability_xor_proxy",
            "evidence": sampled_walkable_space["region_reachability"],
            "uncertainty": "region-level XOR between sampled walk and see reachability; proxy for boundary-channel split",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_mean_visibility_region_grid_distance",
            "score": sampled_walkable_space["mean_visibility_region_grid_distance"],
            "status": "computed"
            if sampled_walkable_space["mean_visibility_region_grid_distance"] is not None
            else "not_available",
            "method": "sampled_visibility_grid_bfs_distance_proxy",
            "evidence": sampled_walkable_space["visibility_region_grid_distances"],
            "uncertainty": "see-block weighted sampled grid steps; proxy, not visual distance, isovist depth, or VGA integration",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_mean_entry_region_grid_distance",
            "score": sampled_walkable_space["mean_entry_region_grid_distance"],
            "status": "computed"
            if sampled_walkable_space["mean_entry_region_grid_distance"] is not None
            else "not_available",
            "method": "sampled_occupancy_grid_bfs_distance_proxy",
            "evidence": sampled_walkable_space["entry_region_grid_distances"],
            "uncertainty": "four-neighbor sampled grid steps from entries to region cells; proxy, not continuous route length or navmesh distance",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_mean_entry_region_widest_clearance",
            "score": sampled_walkable_space["mean_entry_region_widest_clearance"],
            "status": "computed"
            if sampled_walkable_space["mean_entry_region_widest_clearance"] is not None
            else "not_available",
            "method": "sampled_grid_widest_path_clearance_proxy",
            "evidence": sampled_walkable_space["entry_region_widest_clearance_paths"],
            "uncertainty": "max-min clearance over sampled entry-to-region grid paths; proxy, not medial-axis width field or navmesh routing",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_mean_entry_region_clearance_per_distance",
            "score": sampled_walkable_space[
                "mean_entry_region_clearance_per_distance"
            ],
            "status": "computed"
            if sampled_walkable_space["mean_entry_region_clearance_per_distance"]
            is not None
            else "not_available",
            "method": "sampled_widest_clearance_over_entry_region_distance_proxy",
            "evidence": sampled_walkable_space["entry_region_widest_clearance_paths"],
            "uncertainty": "widest sampled path clearance divided by sampled entry-region distance; proxy for route capacity density, not code-compliant egress capacity",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_mean_region_pair_grid_distance",
            "score": sampled_walkable_space["mean_region_pair_grid_distance"],
            "status": "computed"
            if sampled_walkable_space["mean_region_pair_grid_distance"] is not None
            else "not_available",
            "method": "sampled_region_pair_grid_bfs_distance_proxy",
            "evidence": sampled_walkable_space["region_pair_grid_distances"],
            "uncertainty": "four-neighbor sampled grid steps between region sampled cells; proxy, not continuous route length, navmesh, or space syntax distance",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_region_pair_reachable_ratio",
            "score": round(
                sum(
                    1
                    for item in sampled_walkable_space["region_pair_grid_distances"]
                    if item["distance"] is not None
                )
                / max(1, total_region_pairs),
                4,
            ),
            "status": "computed",
            "method": "sampled_region_pair_grid_bfs_distance_proxy",
            "evidence": sampled_walkable_space["region_pair_grid_distances"],
            "uncertainty": "share of region pairs with finite sampled grid distance; proxy, not route certification",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_component_count",
            "score": sampled_walkable_space["component_count"],
            "status": "computed",
            "method": "sampled_occupancy_grid_component_proxy",
            "evidence": sampled_walkable_space["component_sizes"],
            "uncertainty": "component count over sampled free cells; proxy until continuous negative-space graph exists",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_largest_component_cell_ratio",
            "score": sampled_walkable_space["largest_component_cell_ratio"],
            "status": "computed",
            "method": "sampled_occupancy_grid_component_proxy",
            "evidence": sampled_walkable_space["component_sizes"],
            "uncertainty": "largest sampled component share; proxy for fragmentation, not final circulation analysis",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_path_reachable_region_ratio",
            "score": sampled_walkable_space["path_reachable_region_ratio"],
            "status": "computed",
            "method": "sampled_occupancy_grid_bfs_proxy",
            "evidence": [region["id"] for region in scene.get("regions", [])],
            "uncertainty": "region has reachable cells and sampled path-cell contact; proxy until true path/region negative-space geometry exists",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_entry_reachable_region_pair_ratio",
            "score": sampled_walkable_space[
                "sampled_entry_reachable_region_pair_ratio"
            ],
            "status": "computed",
            "method": "sampled_occupancy_grid_component_pair_proxy",
            "evidence": [
                f"components_{'-'.join(str(component) for component in item['components'])}:{item['region_a']}:{item['region_b']}"
                for item in sampled_walkable_space[
                    "sampled_entry_reachable_region_pair_evidence"
                ]
            ],
            "region_pair_evidence": sampled_walkable_space[
                "sampled_entry_reachable_region_pair_evidence"
            ],
            "entry_reachable_region_pair_count": len(
                sampled_walkable_space[
                    "sampled_entry_reachable_region_pair_evidence"
                ]
            ),
            "total_region_pair_count": total_region_pairs,
            "unreachable_region_pair_evidence": sampled_walkable_space[
                "sampled_unreachable_region_pair_evidence"
            ],
            "uncertainty": "region pairs sharing an entry-reachable sampled walk component; proxy, not continuous route quality or shortest-path routing",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_visibility_reachable_region_pair_ratio",
            "score": sampled_walkable_space[
                "sampled_visibility_reachable_region_pair_ratio"
            ],
            "status": "computed",
            "method": "sampled_visibility_grid_region_pair_proxy",
            "evidence": [
                f"{item['regions'][0]}:{item['regions'][1]}"
                for item in sampled_walkable_space[
                    "sampled_visibility_reachable_region_pair_evidence"
                ]
            ],
            "region_pair_evidence": sampled_walkable_space[
                "sampled_visibility_reachable_region_pair_evidence"
            ],
            "visibility_reachable_region_pair_count": len(
                sampled_walkable_space[
                    "sampled_visibility_reachable_region_pair_evidence"
                ]
            ),
            "total_region_pair_count": total_region_pairs,
            "visibility_unreachable_region_pair_evidence": sampled_walkable_space[
                "sampled_visibility_unreachable_region_pair_evidence"
            ],
            "uncertainty": "region pairs where both regions are reachable in sampled see-block BFS; proxy, not isovist, VGA, route quality, or visual integration",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_visibility_only_region_pair_ratio",
            "score": sampled_walkable_space[
                "sampled_visibility_only_region_pair_ratio"
            ],
            "status": "computed",
            "method": "sampled_visibility_only_minus_walk_region_pair_proxy",
            "evidence": sampled_walkable_space[
                "sampled_visibility_only_region_pair_evidence"
            ],
            "uncertainty": "region pairs visible in sampled see-block BFS but not connected in sampled walk components; proxy for glass/screen separation, not perception certification",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_walk_only_region_pair_ratio",
            "score": sampled_walkable_space["sampled_walk_only_region_pair_ratio"],
            "status": "computed",
            "method": "sampled_walk_only_minus_visibility_region_pair_proxy",
            "evidence": sampled_walkable_space[
                "sampled_walk_only_region_pair_evidence"
            ],
            "uncertainty": "region pairs connected in sampled walk components but not sampled see-block BFS; proxy for visually screened walk links",
        },
        {
            "view_id": "path_connectivity",
            "metric": "sampled_walk_visibility_disagreement_region_pair_ratio",
            "score": sampled_walkable_space[
                "sampled_walk_visibility_disagreement_region_pair_ratio"
            ],
            "status": "computed",
            "method": "sampled_walk_visibility_region_pair_xor_proxy",
            "evidence": sampled_walkable_space[
                "sampled_walk_visibility_disagreement_region_pair_evidence"
            ],
            "uncertainty": "pair-level XOR between sampled walk and visibility connectivity; proxy, not final visibility graph or route analysis",
        },
    ]


def _boundary_metrics_rows(scene: dict, graph: dict) -> list[dict]:
    boundaries = scene["boundaries"]
    entries = scene["entries"]
    boundary_count = len(boundaries)
    opening_count = len(entries)
    score = opening_count / max(1, boundary_count + opening_count)
    rows = [{
        "view_id": "boundary_metrics",
        "metric": "opening_ratio",
        "score": round(score, 4),
        "status": "computed",
        "method": "opening_count_over_boundary_records",
        "evidence": [item["id"] for item in boundaries + entries],
        "uncertainty": "walk/see/grouping weights need explicit boundary metadata",
    }]
    closed_boundaries = [
        {
            "id": boundary["id"],
            "kind": boundary.get("metadata", {}).get("boundary-kind"),
            "walk_block": boundary["weights"]["walk_block"],
            "see_block": boundary["weights"]["see_block"],
        }
        for boundary in boundaries
        if boundary["weights"]["walk_block"] >= 1.0
        and boundary["weights"]["see_block"] >= 1.0
    ]
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "closed_blocking_boundary_ratio",
            "score": round(len(closed_boundaries) / max(1, len(boundaries)), 4),
            "status": "computed",
            "method": "walk_and_see_blocking_boundaries_over_boundaries",
            "evidence": [item["id"] for item in closed_boundaries],
            "closed_boundary_evidence": closed_boundaries,
            "uncertainty": "authored walk/see weights; not wall topology or fire-code closure",
        }
    )
    entry_widths = [_entry_width_descriptor(entry) for entry in entries]
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "entry_width_mean",
            "score": round(mean(item["width"] for item in entry_widths), 4)
            if entry_widths
            else None,
            "status": "computed" if entry_widths else "not_available",
            "method": "opening_width_metadata_or_rect_max_dimension_mean",
            "evidence": [item["id"] for item in entries],
            "entry_widths": entry_widths,
            "uncertainty": "bbox opening-width proxy; replace with authored/BIM opening width or curve length when available",
        }
    )
    room = _room_boundary(scene)
    room_perimeter = 2 * (room["rect"].width + room["rect"].height) if room else 0.0
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "opening_width_room_perimeter_ratio",
            "score": round(sum(item["width"] for item in entry_widths) / room_perimeter, 4)
            if room_perimeter > 1e-9
            else None,
            "status": "computed" if room_perimeter > 1e-9 else "not_available",
            "method": "sum_opening_width_over_room_boundary_bbox_perimeter",
            "evidence": [item["id"] for item in entries] + ([room["id"]] if room else []),
            "room_boundary_id": room["id"] if room else None,
            "uncertainty": "room-boundary bbox perimeter proxy; replace with true boundary curve length for irregular or curved rooms",
        }
    )
    room_length = _polyline_length(room.get("points", [])) if room else 0.0
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "opening_width_room_boundary_length_ratio",
            "score": round(sum(item["width"] for item in entry_widths) / room_length, 4)
            if room_length > 1e-9
            else None,
            "status": "computed" if room_length > 1e-9 else "not_available",
            "method": "sum_opening_width_over_room_boundary_polyline_length",
            "evidence": [item["id"] for item in entries] + ([room["id"]] if room else []),
            "room_boundary_id": room["id"] if room else None,
            "room_boundary_length": round(room_length, 4) if room_length > 1e-9 else None,
            "uncertainty": "polyline length uses parsed SVG path command endpoints; curved walls need curve-aware length",
        }
    )
    thickness_evidence = [
        item for item in (_boundary_thickness_descriptor(boundary) for boundary in boundaries)
        if item is not None
    ]
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "boundary_thickness_mean",
            "score": round(mean(item["thickness"] for item in thickness_evidence), 4)
            if thickness_evidence
            else None,
            "status": "computed" if thickness_evidence else "not_available",
            "method": "authored_boundary_thickness_mean",
            "evidence": [item["id"] for item in thickness_evidence],
            "thickness_evidence": thickness_evidence,
            "uncertainty": "authored thickness metadata; not inferred from SVG stroke width or BIM wall geometry",
        }
    )
    entry_positions = _entry_boundary_positions(entries, room, room_length) if room else []
    ratios = [item["boundary_ratio"] for item in entry_positions]
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "entry_boundary_position_coverage",
            "score": round(max(ratios) - min(ratios), 4) if ratios else None,
            "status": "computed" if ratios else "not_available",
            "method": "entry_center_projection_ratio_on_room_boundary_polyline",
            "evidence": [item["id"] for item in entries] + ([room["id"]] if room else []),
            "room_boundary_id": room["id"] if room else None,
            "entry_positions": entry_positions,
            "uncertainty": "entry center projected to nearest parsed room-boundary segment; curved openings/walls need curve-aware projection",
        }
    )
    entry_boundary_associations = _entry_nearest_boundary_associations(entries, boundaries)
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "entry_nearest_boundary_gap_mean",
            "score": round(mean(item["gap"] for item in entry_boundary_associations), 4)
            if entry_boundary_associations
            else None,
            "status": "computed" if entry_boundary_associations else "not_available",
            "method": "entry_center_to_nearest_boundary_geometry_gap_mean",
            "evidence": [item["id"] for item in entries]
            + [item["id"] for item in boundaries],
            "entry_boundary_associations": entry_boundary_associations,
            "uncertainty": "nearest authored boundary association by entry center; Rhino/BIM should replace this with hosted opening relationships",
        }
    )
    hosted_entry_ids = [
        item["id"]
        for item in entry_boundary_associations
        if item.get("association_method") == "host_boundary_metadata"
    ]
    fallback_entry_ids = [
        item["id"]
        for item in entry_boundary_associations
        if item.get("association_method") == "nearest_boundary_geometry"
    ]
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "hosted_entry_boundary_ratio",
            "score": round(len(hosted_entry_ids) / max(1, len(entries)), 4),
            "status": "computed" if entries else "not_available",
            "method": "entries_with_explicit_host_boundary_over_entries",
            "evidence": hosted_entry_ids,
            "entry_boundary_associations": entry_boundary_associations,
            "uncertainty": "explicit host-boundary metadata is the preferred Rhino/BIM doorway association; missing hosts still fall back to nearest geometry",
        }
    )
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "fallback_entry_boundary_ratio",
            "score": round(len(fallback_entry_ids) / max(1, len(entries)), 4),
            "status": "computed" if entries else "not_available",
            "method": "entries_with_nearest_geometry_boundary_over_entries",
            "evidence": fallback_entry_ids,
            "entry_boundary_associations": entry_boundary_associations,
            "uncertainty": "nearest-geometry opening association is an SVG fallback; Rhino/BIM adapters should prefer hosted opening topology",
        }
    )
    boundary_opening_evidence = _boundary_opening_width_evidence(
        boundaries,
        entry_boundary_associations,
    )
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "boundary_opening_width_ratio_max",
            "score": round(max(item["opening_ratio"] for item in boundary_opening_evidence), 4)
            if boundary_opening_evidence
            else None,
            "status": "computed" if boundary_opening_evidence else "not_available",
            "method": "sum_associated_opening_width_over_boundary_length",
            "evidence": [item["id"] for item in boundary_opening_evidence],
            "boundary_opening_evidence": boundary_opening_evidence,
            "uncertainty": "opening-to-boundary association uses nearest parsed geometry; hosted BIM openings should replace this proxy",
        }
    )
    entry_edges = [edge for edge in graph["edges"] if edge["kind"] == "entry_path_touch"]
    entry_touch_evidence = _entry_touch_evidence(entries, entry_edges, boundaries)
    boundary_path_opening_evidence = _boundary_path_opening_evidence(
        boundaries,
        entry_boundary_associations,
        entry_touch_evidence,
    )
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "boundary_path_connected_opening_ratio_max",
            "score": round(
                max(
                    item["path_connected_opening_ratio"]
                    for item in boundary_path_opening_evidence
                ),
                4,
            )
            if boundary_path_opening_evidence
            else None,
            "status": "computed" if boundary_path_opening_evidence else "not_available",
            "method": "path_connected_openings_over_associated_openings_by_boundary",
            "evidence": [item["id"] for item in boundary_path_opening_evidence],
            "boundary_path_opening_evidence": boundary_path_opening_evidence,
            "uncertainty": "path-connected opening uses bbox path contact; replace with true doorway-to-negative-space graph later",
        }
    )
    weighted_records = boundaries + entries
    weight_metadata_evidence = _weight_metadata_evidence(weighted_records)
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "boundary_weight_metadata_coverage",
            "score": round(
                sum(
                    1
                    for item in weight_metadata_evidence
                    if item["has_complete_weight_metadata"]
                )
                / max(1, len(weight_metadata_evidence)),
                4,
            ),
            "status": "computed" if weight_metadata_evidence else "not_available",
            "method": "records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records",
            "evidence": [
                item["id"]
                for item in weight_metadata_evidence
                if item["has_complete_weight_metadata"]
            ],
            "weight_metadata_evidence": weight_metadata_evidence,
            "missing_weight_metadata_ids": [
                item["id"]
                for item in weight_metadata_evidence
                if not item["has_complete_weight_metadata"]
            ],
            "uncertainty": "explicit weight metadata coverage only; authored weights are not material or perception calibration",
        }
    )
    for key in ("walk_block", "see_block", "grouping_strength"):
        values = [item["weights"][key] for item in weighted_records]
        rows.append(
            {
                "view_id": "boundary_metrics",
                "metric": f"{key}_mean",
                "score": round(mean(values), 4) if values else None,
                "status": "computed" if values else "not_available",
                "method": "structured_svg_boundary_weight_mean",
                "evidence": [item["id"] for item in weighted_records],
                "uncertainty": "weights are authored metadata until material/BIM mapping is added",
            }
        )
    walk_see_gaps = [
        abs(item["weights"]["walk_block"] - item["weights"]["see_block"])
        for item in weighted_records
    ]
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "walk_see_block_gap_mean",
            "score": round(mean(walk_see_gaps), 4) if walk_see_gaps else None,
            "status": "computed" if walk_see_gaps else "not_available",
            "method": "mean_abs_walk_block_minus_see_block",
            "evidence": [item["id"] for item in weighted_records],
            "uncertainty": "authored boundary channel split; not perception-calibrated transparency",
        }
    )
    soft_cues = [
        item["weights"]["grouping_strength"]
        * (1 - item["weights"]["walk_block"])
        * (1 - item["weights"]["see_block"])
        for item in weighted_records
    ]
    rows.append(
        {
            "view_id": "boundary_metrics",
            "metric": "non_blocking_grouping_cue_mean",
            "score": round(mean(soft_cues), 4) if soft_cues else None,
            "status": "computed" if soft_cues else "not_available",
            "method": "mean_grouping_strength_without_walk_or_see_block",
            "evidence": [item["id"] for item in weighted_records],
            "uncertainty": "authored soft-boundary/surface cue weights; not perception-calibrated",
        }
    )
    glass = _first_boundary_kind(boundaries, "glass")
    if glass:
        rows.append(
            {
                "view_id": "boundary_metrics",
                "metric": "glass_walk_see_gap",
                "score": round(glass["weights"]["walk_block"] - glass["weights"]["see_block"], 4),
                "status": "computed",
                "method": "walk_block_minus_see_block_for_glass",
                "evidence": [glass["id"]],
                "uncertainty": "authored glass transparency weight; material/light calibration later",
            }
        )
    rug = _first_boundary_kind(boundaries, "rug")
    if rug:
        rows.append(
            {
                "view_id": "boundary_metrics",
                "metric": "rug_grouping_without_block",
                "score": round(
                    rug["weights"]["grouping_strength"]
                    * (1 - rug["weights"]["walk_block"])
                    * (1 - rug["weights"]["see_block"]),
                    4,
                ),
                "status": "computed",
                "method": "rug_grouping_strength_without_walk_or_see_block",
                "evidence": [rug["id"]],
                "uncertainty": "authored surface-cue weight; perception calibration later",
            }
        )
    return rows


def _weight_metadata_evidence(records: list[dict]) -> list[dict]:
    channel_keys = {
        "walk_block": ("walk-block", "walk_block"),
        "see_block": ("see-block", "see_block"),
        "grouping_strength": ("grouping-strength", "grouping_strength"),
    }
    evidence = []
    for record in records:
        metadata = record.get("metadata", {})
        explicit = sorted(
            channel
            for channel, keys in channel_keys.items()
            if any(key in metadata for key in keys)
        )
        missing = sorted(set(channel_keys) - set(explicit))
        evidence.append(
            {
                "id": record["id"],
                "role": record["role"],
                "kind": metadata.get("boundary-kind"),
                "explicit_channels": explicit,
                "missing_channels": missing,
                "has_complete_weight_metadata": not missing,
            }
        )
    return evidence


def _entry_width_descriptor(entry: dict) -> dict:
    rect = entry["rect"]
    raw_width = (
        entry["metadata"].get("opening-width")
        or entry["metadata"].get("opening_width")
        or entry["metadata"].get("width")
    )
    try:
        width = float(raw_width) if raw_width is not None else max(rect.width, rect.height)
        source = "opening_width_metadata" if raw_width is not None else "opening_bbox_max_dimension"
    except ValueError:
        width = max(rect.width, rect.height)
        source = "opening_bbox_max_dimension"
    return {
        "id": entry["id"],
        "edge": entry["metadata"].get("edge"),
        "width": round(width, 4),
        "center": (round(rect.cx, 4), round(rect.cy, 4)),
        "width_source": source,
    }


def _boundary_thickness_descriptor(boundary: dict) -> dict | None:
    raw = boundary.get("metadata", {}).get("thickness")
    if raw is None:
        return None
    try:
        thickness = float(raw)
    except ValueError:
        return None
    return {
        "id": boundary["id"],
        "kind": boundary.get("metadata", {}).get("boundary-kind"),
        "thickness": round(thickness, 4),
    }


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )


def _entry_boundary_positions(
    entries: list[dict],
    room: dict,
    room_length: float,
) -> list[dict]:
    points = room.get("points", [])
    if room_length <= 1e-9 or len(points) < 2:
        return []
    return [
        _entry_boundary_position(entry, points, room_length)
        for entry in entries
    ]


def _entry_boundary_position(
    entry: dict,
    points: list[tuple[float, float]],
    room_length: float,
) -> dict:
    rect = entry["rect"]
    gap, distance, px, py = _project_point_to_polyline(rect.cx, rect.cy, points)
    return {
        "id": entry["id"],
        "edge": entry["metadata"].get("edge"),
        "boundary_distance": round(distance, 4),
        "boundary_ratio": round(distance / room_length, 4),
        "projected_point": (round(px, 4), round(py, 4)),
        "projection_gap": round(gap, 4),
    }


def _entry_nearest_boundary_associations(
    entries: list[dict],
    boundaries: list[dict],
) -> list[dict]:
    associations = []
    boundaries_by_id = {boundary["id"]: boundary for boundary in boundaries}
    for entry in entries:
        host_id = (
            entry.get("metadata", {}).get("host-boundary")
            or entry.get("metadata", {}).get("host_boundary")
            or entry.get("metadata", {}).get("host")
        )
        method = "nearest_boundary_geometry"
        boundary = boundaries_by_id.get(host_id)
        if boundary is None:
            best = None
            for candidate in boundaries:
                gap, px, py = _entry_boundary_gap(entry, candidate)
                if best is None or gap < best[0]:
                    best = (gap, candidate, px, py)
            if best is None:
                continue
            gap, boundary, px, py = best
        else:
            method = "host_boundary_metadata"
            gap, px, py = _entry_boundary_gap(entry, boundary)
        if boundary is None:
            continue
        descriptor = _entry_width_descriptor(entry)
        associations.append(
            {
                **descriptor,
                "boundary_id": boundary["id"],
                "boundary_kind": boundary.get("metadata", {}).get("boundary-kind"),
                "gap": round(gap, 4),
                "projected_point": (round(px, 4), round(py, 4)),
                "association_method": method,
            }
        )
    return associations


def _boundary_opening_width_evidence(
    boundaries: list[dict],
    entry_boundary_associations: list[dict],
) -> list[dict]:
    by_boundary = {}
    for association in entry_boundary_associations:
        by_boundary.setdefault(association["boundary_id"], []).append(association)
    evidence = []
    for boundary in boundaries:
        length = _boundary_length(boundary)
        openings = by_boundary.get(boundary["id"], [])
        opening_width = sum(item["width"] for item in openings)
        evidence.append(
            {
                "id": boundary["id"],
                "kind": boundary.get("metadata", {}).get("boundary-kind"),
                "length": round(length, 4),
                "opening_width": round(opening_width, 4),
                "opening_ratio": round(opening_width / length, 4)
                if length > 1e-9
                else None,
                "opening_ids": [item["id"] for item in openings],
            }
        )
    return evidence


def _boundary_path_opening_evidence(
    boundaries: list[dict],
    entry_boundary_associations: list[dict],
    entry_touch_evidence: list[dict],
) -> list[dict]:
    associations_by_boundary = {}
    for association in entry_boundary_associations:
        associations_by_boundary.setdefault(association["boundary_id"], []).append(association)
    touched_by_entry = {
        item["id"]: bool(item["touched_path_ids"]) for item in entry_touch_evidence
    }
    evidence = []
    for boundary in boundaries:
        openings = associations_by_boundary.get(boundary["id"], [])
        connected = [
            opening for opening in openings
            if touched_by_entry.get(opening["id"], False)
        ]
        disconnected = [
            opening for opening in openings
            if not touched_by_entry.get(opening["id"], False)
        ]
        evidence.append(
            {
                "id": boundary["id"],
                "kind": boundary.get("metadata", {}).get("boundary-kind"),
                "opening_count": len(openings),
                "path_connected_opening_count": len(connected),
                "path_connected_opening_ratio": round(len(connected) / len(openings), 4)
                if openings
                else 0.0,
                "opening_ids": [opening["id"] for opening in openings],
                "path_connected_opening_ids": [opening["id"] for opening in connected],
                "path_disconnected_opening_ids": [
                    opening["id"] for opening in disconnected
                ],
            }
        )
    return evidence


def _boundary_length(boundary: dict) -> float:
    points = boundary.get("points") or []
    if len(points) >= 2:
        return _polyline_length(points)
    rect = boundary["rect"]
    return max(rect.width, rect.height)


def _entry_boundary_gap(entry: dict, boundary: dict) -> tuple[float, float, float]:
    rect = entry["rect"]
    points = boundary.get("points", [])
    if len(points) >= 2:
        gap, _, px, py = _project_point_to_polyline(rect.cx, rect.cy, points)
        return gap, px, py
    return _project_point_to_rect(rect.cx, rect.cy, boundary["rect"])


def _project_point_to_polyline(
    x: float,
    y: float,
    points: list[tuple[float, float]],
) -> tuple[float, float, float, float]:
    best = None
    before = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        dx = x2 - x1
        dy = y2 - y1
        length = hypot(dx, dy)
        if length <= 1e-9:
            continue
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (length * length)))
        px = x1 + t * dx
        py = y1 + t * dy
        gap = hypot(x - px, y - py)
        candidate = (gap, before + t * length, px, py)
        best = candidate if best is None or candidate < best else best
        before += length
    return best or (0.0, 0.0, x, y)


def _project_point_to_rect(x: float, y: float, rect) -> tuple[float, float, float]:
    px = max(rect.left, min(x, rect.right))
    py = max(rect.top, min(y, rect.bottom))
    return hypot(x - px, y - py), px, py


def _boundary_connectivity_row(scene: dict) -> dict:
    return {
        "view_id": "boundary_connectivity",
        "metric": "opening_count",
        "score": len(scene["entries"]),
        "status": "computed",
        "method": "structured_svg_opening_count",
        "evidence": [entry["id"] for entry in scene["entries"]],
        "uncertainty": "opening geometry is metadata-level in this slice",
    }


def _adapter_reference_row(scene: dict) -> dict:
    records = _adapter_scene_records(scene)
    evidence = [
        {
            "id": record["id"],
            "role": record["role"],
            "adapter_refs": record.get("adapter_refs", {}),
        }
        for record in records
        if record.get("adapter_refs")
    ]
    role_coverage = {}
    for role in sorted({record["role"] for record in records}):
        role_records = [record for record in records if record["role"] == role]
        role_evidence = [record["id"] for record in role_records if record.get("adapter_refs")]
        role_coverage[role] = {
            "record_count": len(role_records),
            "referenced_count": len(role_evidence),
            "coverage": round(len(role_evidence) / max(1, len(role_records)), 4),
            "evidence": role_evidence,
            "missing_ids": [
                record["id"] for record in role_records if not record.get("adapter_refs")
            ],
        }
    return {
        "view_id": "adapter_readiness",
        "metric": "adapter_reference_coverage",
        "score": round(len(evidence) / max(1, len(records)), 4),
        "status": "computed" if records else "not_available",
        "method": "records_with_external_adapter_refs_over_scene_records",
        "evidence": [item["id"] for item in evidence],
        "adapter_reference_evidence": evidence,
        "adapter_reference_role_coverage": role_coverage,
        "record_count": len(records),
        "uncertainty": "adapter refs are traceability metadata only; they do not prove live Rhino/BIM topology",
    }


def _matrix_completion_audit_row() -> dict:
    """Expose the current full-matrix completion gate as machine-readable evidence."""
    required_family_status = [
        {
            "family": "automatic_neutral_scene",
            "status": "implemented",
            "evidence": ["load_structured_svg_scene", "infer_scene_evidence"],
        },
        {
            "family": "metric_matrix_rows",
            "status": "prototype_expanded",
            "evidence": ["evaluate_scene", "score_matrix"],
        },
        {
            "family": "route_topology",
            "status": "prototype_proxy",
            "evidence": [
                "inferred_region_gap_path_graph",
                "free_space_polygon_graph",
                "cad_room_minus_blocker_component_graph",
            ],
        },
        {
            "family": "visual_analysis",
            "status": "prototype_proxy",
            "evidence": ["line_of_sight_graph", "isovist_radial_proxy"],
        },
        {
            "family": "column_grid",
            "status": "prototype_proxy",
            "evidence": [
                "region_column_bay_fit",
                "object_column_bay_local_position_coverage",
            ],
        },
        {
            "family": "material_boundary_calibration",
            "status": "metadata_handoff",
            "evidence": ["material_calibration_handoff"],
        },
        {
            "family": "notebook_evidence",
            "status": "implemented",
            "evidence": ["floorplan_order_matrix_demo.ipynb"],
        },
        {
            "family": "live_bim_rhino_adapter",
            "status": "deferred_by_user_scope",
            "evidence": ["neutral_adapter_payload"],
        },
    ]
    open_statuses = {"prototype_expanded", "prototype_proxy", "metadata_handoff"}
    # Keep the gate explicit so a completion claim cannot rely on broad green tests alone.
    open_core_families = [
        item["family"]
        for item in required_family_status
        if item["status"] in open_statuses
    ]
    return {
        "view_id": "adapter_readiness",
        "metric": "matrix_completion_audit",
        "score": None,
        "status": "computed",
        "method": "completion_gate_from_current_metric_family_status",
        "evidence": open_core_families,
        "completion_ready": not open_core_families,
        "open_core_families": open_core_families,
        "required_metric_family_status": required_family_status,
        "uncertainty": "completion gate only; proxy or metadata handoff families must be implemented or explicitly deferred before a final completion claim",
    }


def _score_matrix(rows: list[dict]) -> dict:
    included = {}
    excluded = []
    for row in rows:
        score = row.get("score")
        if (
            row.get("status") == "computed"
            and isinstance(score, (int, float))
            and 0.0 <= score <= 1.0
            and not _score_matrix_excluded_metric(row)
        ):
            included.setdefault(row["view_id"], []).append(row)
        elif row.get("status") == "computed" and isinstance(score, (int, float)):
            excluded.append(f"{row['view_id']}.{row['metric']}")
    dimension_scores = [
        {
            "view_id": view_id,
            "score": round(mean(row["score"] for row in view_rows), 4),
            "metric_count": len(view_rows),
            "metrics": sorted(row["metric"] for row in view_rows),
        }
        for view_id, view_rows in sorted(included.items())
    ]
    return {
        "method": "computed_unit_interval_metric_mean_by_view_id",
        "overall_score": round(
            mean(item["score"] for item in dimension_scores),
            4,
        )
        if dimension_scores
        else None,
        "dimension_scores": dimension_scores,
        "excluded_metrics": sorted(excluded),
        "uncertainty": "dimension scores average computed 0..1 scalar metrics only; counts, unavailable rows, and domain-specific weights are excluded until calibrated",
    }


def _score_matrix_excluded_metric(row: dict) -> bool:
    metric = row["metric"]
    return (
        row["view_id"] in {"boundary_connectivity", "uncertainties"}
        or metric.endswith("_count")
        or metric.endswith("_count_mean")
        or "count" in metric
    )


def _adapter_payload(
    scene: dict,
    rows: list[dict],
    graphs: dict,
    negative_space: dict,
    negative_space_graph: dict,
    line_of_sight_graph: dict,
    isovist_radial_proxy: dict,
    affordance_zones: list[dict],
    furniture_affordance_extents: list[dict],
    furniture_groups: list[dict],
    region_position_grammar: dict,
    inferred_region_candidates: list[dict],
    inferred_region_gap_paths: list[dict],
    spatial_networks: list[dict],
    boundary_semantics: list[dict],
    inferred_region_gap_path_graph: dict,
    score_matrix: dict,
) -> dict:
    records = _adapter_scene_records(scene)
    scene_records = []
    external_refs = {}
    for record in records:
        rect = record["rect"]
        adapter_refs = dict(record.get("adapter_refs", {}))
        scene_record = {
            "id": record["id"],
            "role": record["role"],
            "group": record.get("group", "global"),
            "region": record.get("region", record.get("group", "global")),
            "bbox": (
                float(rect.left),
                float(rect.top),
                float(rect.right),
                float(rect.bottom),
            ),
            "adapter_refs": adapter_refs,
        }
        metadata = dict(record.get("metadata", {}))
        if metadata:
            scene_record["metadata"] = metadata
        scene_records.append(scene_record)
        for key, value in adapter_refs.items():
            refs_for_key = external_refs.setdefault(key, {})
            current = refs_for_key.get(value)
            if current is None:
                refs_for_key[value] = record["id"]
            elif isinstance(current, list):
                current.append(record["id"])
            else:
                refs_for_key[value] = [current, record["id"]]
    graph_namespaces = _adapter_graph_namespaces(
        graphs,
        line_of_sight_graph,
    )
    metric_rows = [
        {
            "view_id": row["view_id"],
            "metric": row["metric"],
            "score": row.get("score"),
            "status": row.get("status"),
        }
        for row in rows
    ]
    grasshopper_branches = _adapter_grasshopper_branches(
        scene_records,
        metric_rows,
        graph_namespaces,
    )
    evidence_geometry = _adapter_evidence_geometry(
        rows,
        negative_space,
        negative_space_graph,
        affordance_zones,
        furniture_affordance_extents,
        furniture_groups,
        region_position_grammar,
        inferred_region_candidates,
        inferred_region_gap_paths,
        spatial_networks,
        boundary_semantics,
    )
    host_relationships = _adapter_host_relationships(rows)
    route_handoff = _adapter_route_topology_handoff(
        evidence_geometry,
        host_relationships,
        inferred_region_gap_path_graph,
    )
    visual_handoff = _adapter_visual_analysis_handoff(
        line_of_sight_graph,
        isovist_radial_proxy,
    )
    material_handoff = _adapter_material_calibration_handoff(scene, rows)
    column_handoff = _adapter_column_grid_handoff(rows)
    return {
        "source": scene["source"],
        "handoff_contract": dict(ADAPTER_PAYLOAD_CONTRACT),
        "record_count": len(scene_records),
        "external_refs": external_refs,
        "scene_records": scene_records,
        "evidence_geometry": evidence_geometry,
        "graph_namespaces": graph_namespaces,
        "grasshopper_branches": grasshopper_branches,
        "adapter_targets": _adapter_targets(
            scene_records,
            grasshopper_branches,
        ),
        "host_relationships": host_relationships,
        "route_topology_handoff": route_handoff,
        "visual_analysis_handoff": visual_handoff,
        "material_calibration_handoff": material_handoff,
        "column_grid_handoff": column_handoff,
        "adapter_capability_matrix": _adapter_capability_matrix(rows),
        "notebook_audit_manifest": _notebook_audit_manifest(),
        "score_matrix": score_matrix,
        "metric_rows": metric_rows,
        "uncertainty": "neutral handoff payload only; Rhino/Grasshopper/VisualARQ/BIM adapters still need live geometry and host-object mapping",
    }


def _notebook_audit_manifest() -> dict:
    return {
        "method": "notebook_audit_manifest_for_clean_ordered_evidence_overlay",
        "section_order": [
            "1. Source Fixture",
            "2. Evaluation Summary",
            "3. Metric Matrix",
            "4. Clean Evidence Overlay",
            "5. Audit Snapshot",
        ],
        "default_overlay": {
            "function": "scene_metric_overlay_svg(scene, matrix)",
            "include_free_space_paths": False,
            "dense_free_space_paths_layer": "free-space-graph-entry-region-path",
        },
        "optional_dense_layers": ["free-space-graph-entry-region-path"],
        "status": "ordered_clean_overlay",
        "uncertainty": "notebook audit manifest describes current executable notebook display policy only; it is not visual QA for every rendered layer or a final presentation layout",
    }


def _adapter_capability_matrix(rows: list[dict]) -> dict:
    ready_handoffs = list(ADAPTER_READY_HANDOFFS)
    uncertainty_route = next(
        (
            row
            for row in rows
            if row.get("view_id") == "uncertainties"
            and row.get("metric") == "uncertainty_routes"
        ),
        {},
    )
    route_evidence = uncertainty_route.get("route_evidence", {})
    return {
        "method": "adapter_capability_matrix_from_current_payload_handoffs",
        "ready_handoffs": ready_handoffs,
        "capabilities": [
            {
                "name": "host_relationships",
                "status": "proxy_handoff",
                "replacement": "live Rhino/VisualARQ/BIM hosted opening topology",
            },
            {
                "name": "route_topology_handoff",
                "status": "proxy_handoff",
                "replacement": "navmesh, medial-axis, skeleton, or hosted BIM topology",
            },
            {
                "name": "visual_analysis_handoff",
                "status": "proxy_handoff",
                "replacement": "full isovist polygons, VGA, or calibrated visual integration",
            },
            {
                "name": "material_calibration_handoff",
                "status": "metadata_handoff",
                "replacement": "Rhino/BIM materials, lighting, and perception calibration",
            },
            {
                "name": "column_grid_handoff",
                "status": "proxy_handoff",
                "replacement": "Rhino/BIM grid topology or irregular local grid interpolation",
            },
        ],
        "open_uncertainty_routes": {
            key: len(route_evidence.get(key, []))
            for key in (
                "geometry_upgrade",
                "perception_experiment",
                "bim_mapping",
                "method_replacement",
            )
        },
        "uncertainty": "capability matrix is a handoff readiness index only; it does not prove live adapter execution, hosted topology, validated geometry, material calibration, or final route/visibility analysis",
    }


def _adapter_column_grid_handoff(rows: list[dict]) -> dict:
    """Build the compact column-grid payload for downstream BIM adapters."""
    column_rows = {
        row["metric"]: row
        for row in rows
        if row.get("view_id") == "column_alignment"
    }
    axis_row = column_rows.get("region_column_axis_agreement", {})
    axis_evidence = axis_row.get("column_axis_evidence", [])
    phase_row = column_rows.get("object_column_axis_phase_alignment", {})
    bay_row = column_rows.get("region_column_bay_fit", {})
    local_row = column_rows.get("object_column_bay_local_position_coverage", {})
    c_global_row = column_rows.get("column_grid_C_global", {})
    c_local_row = column_rows.get("column_grid_C_local_profile", {})
    c_global_items = c_global_row.get("column_grid_evidence", {}).get(
        "global_relations",
        [],
    )
    c_local_items = c_local_row.get("column_grid_evidence", {}).get(
        "local_profiles",
        [],
    )
    return {
        "method": "adapter_column_grid_handoff_from_existing_column_alignment_rows",
        "axes": {
            "method": axis_row.get("method"),
            "axis_count": len(axis_evidence),
            "axis_ids": [item["id"] for item in axis_evidence],
            "region_axis_agreement": axis_row.get("score"),
            "items": axis_evidence,
        },
        "object_phase": {
            "method": phase_row.get("method"),
            "score": phase_row.get("score"),
            "evidence_count": len(phase_row.get("object_axis_phase_evidence", [])),
        },
        "region_bays": {
            "method": bay_row.get("method"),
            "score": bay_row.get("score"),
            "evidence_count": len(bay_row.get("region_bay_fit_evidence", [])),
            # Handoff consumers need per-region bay ids, not only aggregate counts.
            "items": bay_row.get("region_bay_fit_evidence", []),
        },
        "object_bay_local_positions": {
            "method": local_row.get("method"),
            "score": local_row.get("score"),
            "evidence_count": len(
                local_row.get("object_bay_local_position_evidence", [])
            ),
            # Local coordinates are the current adapter-readable bay placement proxy.
            "items": local_row.get("object_bay_local_position_evidence", []),
        },
        "C_global": {
            "method": c_global_row.get("method"),
            "score": c_global_row.get("score"),
            "evidence_count": len(c_global_items),
            "items": c_global_items,
        },
        "C_local_profile": {
            "method": c_local_row.get("method"),
            "score": c_local_row.get("score"),
            "evidence_count": len(c_local_items),
            "items": c_local_items,
        },
        "uncertainty": "column-grid handoff only; authored axis and bay proxies must be replaced by Rhino/BIM grid topology or irregular local grid interpolation downstream",
    }


def _adapter_material_calibration_handoff(scene: dict, rows: list[dict]) -> dict:
    boundary_rows = {
        row["metric"]: row
        for row in rows
        if row.get("view_id") == "boundary_metrics"
    }
    thickness_by_id = {
        item["id"]: item["thickness"]
        for item in (
            _boundary_thickness_descriptor(boundary)
            for boundary in scene.get("boundaries", [])
        )
        if item is not None
    }
    return {
        "method": "adapter_material_calibration_handoff_from_authored_boundary_weights",
        "weight_metadata": {
            "method": "records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records",
            "coverage": boundary_rows.get(
                "boundary_weight_metadata_coverage",
                {},
            ).get("score"),
            "missing_ids": boundary_rows.get(
                "boundary_weight_metadata_coverage",
                {},
            ).get("missing_weight_metadata_ids", []),
        },
        "channel_means": {
            "walk_block": boundary_rows.get("walk_block_mean", {}).get("score"),
            "see_block": boundary_rows.get("see_block_mean", {}).get("score"),
            "grouping_strength": boundary_rows.get(
                "grouping_strength_mean",
                {},
            ).get("score"),
            "walk_see_block_gap": boundary_rows.get(
                "walk_see_block_gap_mean",
                {},
            ).get("score"),
            "non_blocking_grouping_cue": boundary_rows.get(
                "non_blocking_grouping_cue_mean",
                {},
            ).get("score"),
        },
        "calibration_candidates": [
            {
                "id": boundary["id"],
                "kind": boundary.get("metadata", {}).get("boundary-kind"),
                "walk_block": boundary["weights"]["walk_block"],
                "see_block": boundary["weights"]["see_block"],
                "grouping_strength": boundary["weights"]["grouping_strength"],
                "thickness": thickness_by_id.get(boundary["id"]),
            }
            for boundary in scene.get("boundaries", [])
            if boundary.get("metadata", {}).get("boundary-kind")
            in {"glass", "rug", "material", "visual"}
        ],
        "uncertainty": "material calibration handoff only; authored walk/see/grouping weights and thickness metadata must be replaced or calibrated from Rhino/BIM materials, lighting, and perception data downstream",
    }


def _adapter_visual_analysis_handoff(
    line_of_sight_graph: dict,
    isovist_radial_proxy: dict,
) -> dict:
    """Build the compact visual-analysis payload for downstream BIM adapters."""
    sight_metrics = line_of_sight_graph.get("metrics", {})
    isovist_metrics = isovist_radial_proxy.get("metrics", {})
    return {
        "method": "adapter_visual_analysis_handoff_from_existing_visibility_proxies",
        "visibility_graph": {
            "method": "line_of_sight_graph_edge_visibility_ratio",
            "node_count": len(line_of_sight_graph.get("nodes", [])),
            "edge_count": len(line_of_sight_graph.get("edges", [])),
            "visible_edge_ratio": sight_metrics.get("visible_edge_ratio", 0.0),
            "blocked_edge_ratio": sight_metrics.get("blocked_edge_ratio", 0.0),
            "blocking_boundary_count": len(
                sight_metrics.get("blocking_boundary_ids", [])
            ),
            # Carry graph-shaped evidence so adapters can inspect each sight edge.
            "items": line_of_sight_graph.get("edges", []),
        },
        "isovist_radial_proxy": {
            "method": isovist_radial_proxy.get("method"),
            "status": isovist_radial_proxy.get("status"),
            "vantage_count": isovist_metrics.get("vantage_count", 0),
            "ray_count": isovist_metrics.get("ray_count", 0),
            "blocked_ray_count": isovist_metrics.get("blocked_ray_count", 0),
            "blocked_ray_ratio": isovist_metrics.get("blocked_ray_ratio"),
            "mean_hit_distance": isovist_metrics.get("mean_hit_distance"),
            "mean_hit_polygon_area": isovist_metrics.get("mean_hit_polygon_area"),
            # Keep ray and hit-polygon details available without inventing a new algorithm.
            "ray_items": isovist_radial_proxy.get("ray_evidence", []),
            "area_items": isovist_radial_proxy.get("isovist_area_evidence", []),
        },
        "uncertainty": "visual analysis handoff only; replace centerline visibility and radial ray proxies with full isovist polygons, VGA, or calibrated visual integration downstream",
    }


def _adapter_route_topology_handoff(
    evidence_geometry: dict,
    host_relationships: dict,
    inferred_region_gap_path_graph: dict | None = None,
) -> dict:
    """Build the compact route-topology payload for downstream BIM adapters."""
    cad_graph = evidence_geometry.get("cad_room_minus_blocker_component_graph", {})
    free_graph = evidence_geometry.get("free_space_polygon_graph", {})
    inferred_gap_paths = evidence_geometry.get("inferred_region_gap_paths", {}).get(
        "items",
        [],
    )
    inferred_graph = inferred_region_gap_path_graph or {}
    inferred_graph_handoff = {
        "method": inferred_graph.get(
            "method",
            "inferred_gap_path_region_adjacency_graph_proxy",
        ),
        "node_count": inferred_graph.get(
            "node_count",
            0,
        ),
        "edge_count": inferred_graph.get(
            "edge_count",
            0,
        ),
        "clear_edge_count": inferred_graph.get(
            "clear_edge_count",
            0,
        ),
        "occupied_edge_count": inferred_graph.get(
            "occupied_edge_count",
            0,
        ),
        "free_space_supported_edge_count": inferred_graph.get(
            "free_space_supported_edge_count",
            0,
        ),
        "walkable_proxy_edge_count": inferred_graph.get(
            "walkable_proxy_edge_count",
            0,
        ),
        "walkable_proxy_min_thickness": inferred_graph.get(
            "walkable_proxy_min_thickness",
        ),
        "walkable_proxy_mean_thickness": inferred_graph.get(
            "walkable_proxy_mean_thickness",
        ),
        "component_count": inferred_graph.get(
            "component_count",
            0,
        ),
        "walkable_proxy_component_count": inferred_graph.get(
            "walkable_proxy_component_count",
            0,
        ),
        "walkable_proxy_components": inferred_graph.get(
            "walkable_proxy_components",
            [],
        ),
        "walkable_proxy_edges": inferred_graph.get(
            "walkable_proxy_edges",
            [],
        ),
        "walkable_proxy_edge_widths": inferred_graph.get(
            "walkable_proxy_edge_widths",
            [],
        ),
        "minimum_width": inferred_graph.get("minimum_width"),
        "minimum_width_basis": inferred_graph.get("minimum_width_basis"),
        "minimum_width_evidence": inferred_graph.get(
            "minimum_width_evidence",
            [],
        ),
        "width_pass_edge_count": inferred_graph.get(
            "width_pass_edge_count",
            0,
        ),
        "width_fail_edge_count": inferred_graph.get(
            "width_fail_edge_count",
            0,
        ),
        "width_pass_edges": inferred_graph.get(
            "width_pass_edges",
            [],
        ),
        "width_fail_edges": inferred_graph.get(
            "width_fail_edges",
            [],
        ),
    }
    if "cad_free_space_supported_edge_count" in inferred_graph:
        # Forward CAD support only when Shapely room-minus-blocker evidence exists.
        inferred_graph_handoff.update(
            {
                "cad_free_space_supported_edge_count": inferred_graph.get(
                    "cad_free_space_supported_edge_count",
                    0,
                ),
                "cad_free_space_supported_edges": inferred_graph.get(
                    "cad_free_space_supported_edges",
                    [],
                ),
            }
        )
    return {
        "method": "adapter_route_topology_handoff_from_existing_proxy_graphs",
        "cad_component_graph": {
            "method": cad_graph.get("method"),
            "node_count": cad_graph.get("node_count", 0),
            "edge_count": cad_graph.get("edge_count", 0),
            # Forward existing graph details for adapters without changing route logic.
            "items": {
                "nodes": cad_graph.get("nodes", []),
                "edges": cad_graph.get("edges", []),
            },
        },
        "free_space_polygon_graph": {
            "method": free_graph.get("method"),
            "node_count": free_graph.get("node_count", 0),
            "edge_count": free_graph.get("edge_count", 0),
            # Keep the rect-cell graph inspectable until a navmesh/skeleton replaces it.
            "items": {
                "nodes": free_graph.get("nodes", []),
                "edges": free_graph.get("edges", []),
            },
        },
        "inferred_gap_paths": {
            "method": "affordance_region_bbox_axis_gap_band_proxy",
            "count": len(inferred_gap_paths),
            "clear_count": sum(
                1
                for item in inferred_gap_paths
                if item.get("clear_status") == "clear_proxy"
            ),
            "occupied_count": sum(
                1
                for item in inferred_gap_paths
                if item.get("clear_status") == "occupied_proxy"
            ),
            "items": inferred_gap_paths,
        },
        "inferred_gap_path_graph": inferred_graph_handoff,
        "host_relationships": {
            "method": host_relationships.get("method"),
            "hosted_entry_count": host_relationships.get("hosted_entry_count", 0),
            "fallback_entry_count": host_relationships.get("fallback_entry_count", 0),
        },
        "uncertainty": "route topology handoff only; replace proxy graphs with navmesh, medial-axis, skeleton, or hosted BIM topology in downstream adapters",
    }


def _adapter_host_relationships(rows: list[dict]) -> dict:
    associations = []
    for row in rows:
        if (
            row.get("view_id") == "boundary_metrics"
            and row.get("metric") == "entry_nearest_boundary_gap_mean"
        ):
            associations = list(row.get("entry_boundary_associations", []))
            break
    return {
        "method": "entry_boundary_associations_from_host_metadata_or_nearest_geometry",
        "entry_boundary_hosts": associations,
        "hosted_entry_count": sum(
            1
            for item in associations
            if item.get("association_method") == "host_boundary_metadata"
        ),
        "fallback_entry_count": sum(
            1
            for item in associations
            if item.get("association_method") == "nearest_boundary_geometry"
        ),
        "uncertainty": "neutral host relationship export only; Rhino/VisualARQ/BIM adapters must replace fallback geometry with live hosted topology",
    }


def _adapter_targets(
    scene_records: list[dict],
    grasshopper_branches: list[dict],
) -> dict:
    branches_by_id = {
        branch["id"]: branch["path"]
        for branch in grasshopper_branches
        if branch["kind"].endswith("_record")
    }
    target_by_role = {
        "boundary": ("Boundary", "Curve|Brep", "Wall"),
        "opening": ("Entry", "Curve|Brep", "Door"),
        "path": ("PathNetwork", "Curve|Brep", "Space"),
        "region": ("Region", "ClosedCurve|Brep", "Space|Room"),
        "column_axis": ("ColumnGrid.axes", "Curve", "GridAxis"),
        "column": ("ColumnGrid.columns", "Point|Brep", "Column"),
        "column_grid": ("ColumnGrid", "Curve|Point|Brep", "Grid"),
    }
    target_by_boundary_kind = {
        "glass": ("GlassBoundary", "Curve|Brep|GlassMaterial", "CurtainWall|Window"),
        "rug": ("BoundaryCue", "Curve|Hatch|Surface", "SurfaceFinish|Annotation"),
        "material": ("BoundaryCue", "Curve|Hatch|Surface", "SurfaceFinish|Annotation"),
        "visual": ("VisualBoundaryCue", "Curve|Annotation", "Annotation|ZoneBoundary"),
    }
    return {
        record["id"]: {
            "neutral_target": target[0],
            "rhino_target": target[1],
            "grasshopper_branch": branches_by_id.get(record["id"]),
            "bim_target": target[2],
        }
        for record in scene_records
        for target in [
            target_by_boundary_kind.get(
                record.get("metadata", {}).get("boundary-kind"),
            )
            if record["role"] == "boundary"
            else None
        ]
        for target in [
            target
            or target_by_role.get(
                record["role"],
                ("FurnitureObject", "ClosedCurve|Brep", "Furniture"),
            )
        ]
    }


def _adapter_grasshopper_branches(
    scene_records: list[dict],
    metric_rows: list[dict],
    graph_namespaces: dict,
) -> list[dict]:
    branches = []
    branch_names = {
        "boundary": "boundaries",
        "opening": "entries",
        "path": "paths",
        "region": "regions",
        "column_axis": "column_grid",
    }
    counters = {}
    for record in scene_records:
        branch = branch_names.get(record["role"], "objects")
        index = counters.get(branch, 0)
        counters[branch] = index + 1
        branches.append(
            {
                "path": f"{{0;{branch};{index}}}",
                "kind": "boundary_record"
                if record["role"] == "boundary"
                else "object_record"
                if branch == "objects"
                else f"{record['role']}_record",
                "id": record["id"],
                "role": record["role"],
            }
        )
    branches.extend(
        {
            "path": f"{{0;metrics;{index}}}",
            "kind": "metric_row",
            "id": f"{row['view_id']}.{row['metric']}",
        }
        for index, row in enumerate(metric_rows)
    )
    branches.extend(
        {
            "path": f"{{0;graphs;{name}}}",
            "kind": "graph_namespace",
            "id": name,
        }
        for name in graph_namespaces
    )
    return branches


def _adapter_graph_namespaces(graphs: dict, line_of_sight_graph: dict) -> dict:
    walk_metrics = graphs.get("walk", {}).get("metrics", {})
    sight_metrics = line_of_sight_graph.get("metrics", {})
    return {
        "walk_graph": {
            "method": "boundary_weighted_bbox_touch_graph_proxy",
            "node_count": len(graphs.get("walk", {}).get("nodes", [])),
            "edge_count": len(graphs.get("walk", {}).get("edges", [])),
            "metrics": {
                "entry_region_reachability": walk_metrics.get(
                    "entry_region_reachability",
                    0.0,
                ),
                "component_count": walk_metrics.get("component_count", 0),
                "loop_count": walk_metrics.get("loop_count", 0),
                "loop_ratio": walk_metrics.get("loop_ratio", 0.0),
            },
            "uncertainty": "bbox-touch modal graph for adapter handoff; not navmesh, hosted topology, or route certification",
        },
        "visibility_graph": {
            "method": "line_of_sight_graph_edge_visibility_ratio",
            "node_count": len(line_of_sight_graph.get("nodes", [])),
            "edge_count": len(line_of_sight_graph.get("edges", [])),
            "metrics": {
                "visible_edge_ratio": sight_metrics.get("visible_edge_ratio", 0.0),
                "blocked_edge_ratio": sight_metrics.get("blocked_edge_ratio", 0.0),
                "blocking_boundary_count": len(
                    sight_metrics.get("blocking_boundary_ids", [])
                ),
            },
            "uncertainty": "centerline visibility graph for adapter handoff; not full VGA, isovist field, or calibrated visual integration",
        },
    }


def _rect_bbox(rect: Rect) -> tuple[float, float, float, float]:
    return (
        round(rect.left, 4),
        round(rect.top, 4),
        round(rect.right, 4),
        round(rect.bottom, 4),
    )


def _rect_from_points(points: tuple[tuple[float, float], ...]) -> Rect:
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


def _spacing_side_margins(region: dict) -> dict[str, float]:
    raw = region["metadata"].get("spacing_side_margins", "")
    margins = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        side, value = part.split(":", 1)
        margins[side] = round(float(value), 4)
    return margins


def _adapter_evidence_geometry(
    rows: list[dict],
    negative_space: dict,
    negative_space_graph: dict,
    affordance_zones: list[dict],
    furniture_affordance_extents: list[dict],
    furniture_groups: list[dict],
    region_position_grammar: dict,
    inferred_region_candidates: list[dict],
    inferred_region_gap_paths: list[dict],
    spatial_networks: list[dict],
    boundary_semantics: list[dict],
) -> dict:
    gap_path_occupancy = next(
        (
            row.get("inferred_region_gap_path_occupancy_evidence", [])
            for row in rows
            if row.get("metric") == "inferred_region_gap_path_occupancy_ratio"
        ),
        [],
    )
    occupancy_by_gap_path = {
        item["gap_path_id"]: item
        for item in gap_path_occupancy
    }
    gap_path_free_space_overlap = next(
        (
            row.get("inferred_region_gap_path_free_space_overlap_evidence", [])
            for row in rows
            if row.get("metric")
            == "inferred_region_gap_path_free_space_overlap_ratio"
        ),
        [],
    )
    free_space_overlap_by_gap_path = {
        item["gap_path_id"]: item
        for item in gap_path_free_space_overlap
    }
    gap_path_cad_free_space_overlap = next(
        (
            row.get("inferred_region_gap_path_cad_free_space_overlap_evidence", [])
            for row in rows
            if row.get("metric")
            == "inferred_region_gap_path_cad_free_space_overlap_ratio"
        ),
        [],
    )
    cad_free_space_overlap_by_gap_path = {
        item["gap_path_id"]: item
        for item in gap_path_cad_free_space_overlap
    }
    return {
        "affordance_zones": {
            "count": len(affordance_zones),
            "items": [
                {
                    "id": zone["id"],
                    "object_id": zone["object_id"],
                    "region": zone["region"],
                    "side": zone["side"],
                    "depth": zone["depth"],
                    "source": zone["source"],
                    "zone_bbox": _rect_bbox(zone["rect"]),
                    "footprint_bbox": _rect_bbox(zone["footprint_rect"]),
                }
                for zone in affordance_zones
            ],
        },
        "furniture_affordance_extents": {
            "count": len(furniture_affordance_extents),
            "items": [
                _furniture_affordance_extent_evidence(extent)
                for extent in furniture_affordance_extents
            ],
        },
        "furniture_groups": {
            "count": len(furniture_groups),
            "items": [
                _furniture_group_evidence(group)
                for group in furniture_groups
            ],
        },
        "region_position_grammar": region_position_grammar,
        "inferred_region_candidates": {
            "count": len(inferred_region_candidates),
            "items": [
                {
                    "id": region["id"],
                    "region": region["region"],
                    "bbox": _rect_bbox(region["rect"]),
                    "geometry_basis": region["metadata"].get("geometry_basis"),
                    "member_ids": [
                        member_id
                        for member_id in region["metadata"].get("member_ids", "").split(",")
                        if member_id
                    ],
                    "affordance_zone_ids": [
                        zone_id
                        for zone_id in region["metadata"].get("affordance_zone_ids", "").split(",")
                        if zone_id
                    ],
                    "boundary_cue_ids": [
                        cue_id
                        for cue_id in region["metadata"].get("boundary_cue_ids", "").split(",")
                        if cue_id
                    ],
                    **(
                        {"spacing_side_margins": spacing_side_margins}
                        if (
                            spacing_side_margins := _spacing_side_margins(region)
                        )
                        else {}
                    ),
                }
                for region in inferred_region_candidates
            ],
        },
        "inferred_region_gap_paths": {
            "count": len(inferred_region_gap_paths),
            "items": [
                {
                    "id": path["id"],
                    "region_a": path["region_a"],
                    "region_b": path["region_b"],
                    "orientation": path["orientation"],
                    "bbox": _rect_bbox(path["rect"]),
                    "thickness": round(path["thickness"], 4),
                    "overlap_span": round(path["overlap_span"], 4),
                    **(
                        {
                            "occupied": bool(occupancy.get("occupiers")),
                            "occupancy_ratio": occupancy.get("occupancy_ratio", 0.0),
                            "occupied_area": occupancy.get("occupied_area", 0.0),
                            "clear_status": gap_path_clear_status(
                                occupancy.get("occupancy_ratio", 0.0)
                            ),
                        }
                        if (occupancy := occupancy_by_gap_path.get(path["id"]))
                        else {}
                    ),
                    **(
                        {
                            "free_space_overlap_ratio": free_space_overlap.get(
                                "free_space_overlap_ratio",
                                0.0,
                            ),
                            "free_space_overlap_area": free_space_overlap.get(
                                "free_space_overlap_area",
                                0.0,
                            ),
                        }
                        if (
                            free_space_overlap := free_space_overlap_by_gap_path.get(
                                path["id"]
                            )
                        )
                        else {}
                    ),
                    **(
                        {
                            "cad_free_space_overlap_ratio": cad_overlap.get(
                                "cad_free_space_overlap_ratio",
                                0.0,
                            ),
                            "cad_free_space_overlap_area": cad_overlap.get(
                                "cad_free_space_overlap_area",
                                0.0,
                            ),
                        }
                        if (
                            cad_overlap := cad_free_space_overlap_by_gap_path.get(
                                path["id"]
                            )
                        )
                        else {}
                    ),
                }
                for path in inferred_region_gap_paths
            ],
        },
        "spatial_networks": {
            "count": len(spatial_networks),
            "items": spatial_networks,
        },
        "boundary_semantics": {
            "count": len(boundary_semantics),
            "items": boundary_semantics,
        },
        "inferred_region_gap_path_occupancy": {
            "count": len(gap_path_occupancy),
            "items": gap_path_occupancy,
        },
        "inferred_region_gap_path_free_space_overlap": {
            "count": len(gap_path_free_space_overlap),
            "items": gap_path_free_space_overlap,
        },
        "inferred_region_gap_path_cad_free_space_overlap": {
            "count": len(gap_path_cad_free_space_overlap),
            "items": gap_path_cad_free_space_overlap,
        },
        "free_space_polygons": {
            "method": "room_polygon_rect_cell_free_space_polygons_proxy",
            "count": len(negative_space.get("free_space_polygons", [])),
            "items": [
                {
                    "id": (
                        f"component_{item['component_index']}"
                        f"_cell_{item['cell_index']}"
                    ),
                    **item,
                }
                for item in negative_space.get("free_space_polygons", [])[:3]
            ],
        },
        "room_minus_blocker_polygons": {
            "method": "rect_cell_room_minus_blocker_boundary_union_proxy",
            "count": len(negative_space.get("room_minus_blocker_polygons", [])),
            "items": negative_space.get("room_minus_blocker_polygons", []),
        },
        "cad_room_minus_blocker_polygons": {
            "method": "shapely_room_polygon_difference_blocker_union",
            "count": len(negative_space.get("cad_room_minus_blocker_polygons", [])),
            "items": negative_space.get("cad_room_minus_blocker_polygons", []),
        },
        "cad_room_minus_blocker_component_touch_evidence": {
            "method": "shapely_component_entry_region_touch_proxy",
            "items": negative_space.get(
                "cad_room_minus_blocker_component_touch_evidence",
                [],
            ),
        },
        "cad_room_minus_blocker_entry_connected_area": {
            "method": "shapely_component_entry_touched_area_ratio_proxy",
            "entry_connected_component_ids": negative_space.get(
                "cad_room_minus_blocker_entry_connected_component_ids",
                [],
            ),
            "non_entry_connected_component_ids": negative_space.get(
                "cad_room_minus_blocker_non_entry_connected_component_ids",
                [],
            ),
            "entry_connected_component_area": negative_space.get(
                "cad_room_minus_blocker_entry_connected_component_area"
            ),
            "non_entry_connected_component_area": negative_space.get(
                "cad_room_minus_blocker_non_entry_connected_component_area"
            ),
            "cad_room_minus_blocker_area_total": negative_space.get(
                "cad_room_minus_blocker_area_total"
            ),
            "entry_connected_area_ratio": negative_space.get(
                "cad_room_minus_blocker_entry_connected_area_ratio"
            ),
        },
        "cad_room_minus_blocker_component_graph": _cad_room_minus_blocker_component_graph(
            negative_space.get(
                "cad_room_minus_blocker_component_touch_evidence",
                [],
            )
        ),
        "free_space_polygon_graph": negative_space.get(
            "free_space_polygon_graph",
            {},
        ),
        "negative_space_graph": {
            "method": negative_space.get("component_method"),
            "node_count": len(negative_space_graph.get("nodes", [])),
            "edge_count": len(negative_space_graph.get("edges", [])),
            "nodes": [
                {
                    "id": node["id"],
                    "kind": node["kind"],
                    "ref_id": node["ref_id"],
                    "point": node["point"],
                }
                for node in negative_space_graph.get("nodes", [])
            ],
            "edges": [
                {
                    "id": edge["id"],
                    "kind": edge["kind"],
                    "a": edge["a"],
                    "b": edge["b"],
                }
                for edge in negative_space_graph.get("edges", [])
            ],
        },
        "uncertainty": "proxy evidence geometry for adapter handoff; not CAD boolean topology, navmesh, or live Rhino/BIM geometry",
    }


def _cad_room_minus_blocker_component_graph(touch_evidence: list[dict]) -> dict:
    nodes = []
    edges = []
    node_ids = set()

    def add_node(node: dict) -> None:
        if node["id"] in node_ids:
            return
        node_ids.add(node["id"])
        nodes.append(node)

    for item in touch_evidence:
        component = item["component_index"]
        component_node = f"cad_component_{component}"
        add_node(
            {
                "id": component_node,
                "kind": "cad_free_space_component",
                "ref_id": f"component_{component}",
            }
        )
        for entry_id in item["entry_ids"]:
            entry_node = f"cad_entry_{entry_id}"
            add_node({"id": entry_node, "kind": "entry", "ref_id": entry_id})
            edges.append(
                {
                    "id": f"cad_edge_entry_component_{entry_id}_{component}",
                    "kind": "entry_cad_component_touch",
                    "a": entry_node,
                    "b": component_node,
                    "refs": {"entry": entry_id, "component": component},
                }
            )
        for region_id in item["region_ids"]:
            region_node = f"cad_region_{region_id}"
            add_node({"id": region_node, "kind": "region", "ref_id": region_id})
            edges.append(
                {
                    "id": f"cad_edge_component_region_{component}_{region_id}",
                    "kind": "cad_component_region_overlap",
                    "a": component_node,
                    "b": region_node,
                    "refs": {"component": component, "region": region_id},
                    "overlap_area": item["region_overlap_areas"][region_id],
                }
            )
    return {
        "method": "shapely_component_entry_region_touch_graph_proxy",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def _adapter_scene_records(scene: dict) -> list[dict]:
    """Collect scene records that should remain visible to adapter payloads."""
    return (
        scene.get("objects", [])
        + scene.get("boundaries", [])
        + scene.get("entries", [])
        + scene.get("paths", [])
        + scene.get("regions", [])
        + scene.get("columns", [])
        + scene.get("column_axes", [])
    )


def _uncertainty_row(scene: dict) -> dict:
    uncertainties = list(scene.get("uncertainties", []))
    if not scene.get("paths"):
        uncertainties.append("path network is not derived from negative-space geometry")
    if not scene.get("column_axes"):
        uncertainties.append("column-grid alignment unavailable without column metadata")
    return {
        "view_id": "uncertainties",
        "metric": "open_items",
        "score": len(uncertainties),
        "status": "computed",
        "method": "uncertainty_log",
        "evidence": uncertainties,
        "uncertainty": "perceptual assumptions remain explicit",
    }


def _uncertainty_route_row(rows: list[dict]) -> dict:
    route_keywords = {
        "geometry_upgrade": (
            "curve",
            "polygon",
            "local axis",
            "irregular",
            "curved",
        ),
        "perception_experiment": (
            "perception",
            "perceptual",
            "calibrated",
            "transparency",
        ),
        "bim_mapping": (
            "bim",
            "hosted",
            "wall geometry",
            "material",
        ),
        "method_replacement": (
            "replace",
            "not a",
            "not final",
            "proxy",
            "pending",
        ),
    }
    route_evidence = {}
    for route, keywords in route_keywords.items():
        matches = []
        for row in rows:
            text = row.get("uncertainty")
            if not isinstance(text, str):
                continue
            lowered = text.lower()
            if any(keyword in lowered for keyword in keywords):
                matches.append(row["metric"])
        unique_matches = list(dict.fromkeys(matches))
        if route == "method_replacement":
            # Prefer diagnostic metrics over count-only rows when the route list is capped.
            unique_matches = [
                metric for metric in unique_matches if not metric.endswith("_count")
            ] + [
                metric for metric in unique_matches if metric.endswith("_count")
            ]
        route_evidence[route] = unique_matches[:8]
    active_routes = [
        route for route, evidence in route_evidence.items()
        if evidence
    ]
    return {
        "view_id": "uncertainties",
        "metric": "uncertainty_routes",
        "score": len(active_routes),
        "status": "computed",
        "method": "keyword_route_summary_from_metric_uncertainty_text",
        "evidence": active_routes,
        "route_evidence": {
            route: route_evidence[route]
            for route in active_routes
        },
        "uncertainty": "routes are keyword summaries of declared metric uncertainty text, not a substitute for method validation",
    }


def _not_available(view_id: str, metric: str, reason: str) -> dict:
    return {
        "view_id": view_id,
        "metric": metric,
        "score": None,
        "status": "not_available",
        "method": "not_available",
        "evidence": [],
        "uncertainty": reason,
    }


def _disabled_row(view_id: str, metric: str, reason: str) -> dict:
    """Return a stable disabled metric row for independently switched modules."""
    row = _not_available(view_id, metric, reason)
    row["status"] = "disabled"
    row["region_position_grammar_evidence"] = []
    return row


def _position_phase_score(points: list[tuple[float, float]], axis: str = "x") -> float:
    coords = sorted(point[0] if axis == "x" else point[1] for point in points)
    gaps = [b - a for a, b in zip(coords, coords[1:])]
    return _cv_score(gaps)


def _cv_score(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    avg = mean(values)
    if abs(avg) < 1e-9:
        return 0.0
    return 1 / (1 + pstdev(values) / abs(avg))


def _group_compactness(objects: list[dict]) -> float:
    rect = _bounds(objects)
    hull_area = max(1e-9, rect.area)
    occupied = sum(obj["rect"].area for obj in objects)
    return min(1.0, occupied / hull_area)


def _bounds(objects: list[dict]):
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


def _axis_consistency(angles: list[float]) -> float:
    vectors = [(cos(radians(angle * 2)), sin(radians(angle * 2))) for angle in angles]
    return (mean(x for x, _ in vectors) ** 2 + mean(y for _, y in vectors) ** 2) ** 0.5


def _weighted_axis_consistency(items: list[dict]) -> float:
    total = sum(item.get("influence", item["weight"]) for item in items)
    if total <= 1e-9:
        return 0.0
    x = sum(item.get("influence", item["weight"]) * cos(radians(item["angle"] * 2)) for item in items) / total
    y = sum(item.get("influence", item["weight"]) * sin(radians(item["angle"] * 2)) for item in items) / total
    return (x ** 2 + y ** 2) ** 0.5


def _weighted_boundary_axis_descriptor(boundary: dict) -> dict:
    descriptor = _record_axis_descriptor(boundary)
    weights = boundary["weights"]
    descriptor["weight"] = round(
        mean((weights["walk_block"], weights["see_block"], weights["grouping_strength"])),
        4,
    )
    return descriptor


def _length_weighted_boundary_axis_descriptor(boundary: dict) -> dict:
    descriptor = _weighted_boundary_axis_descriptor(boundary)
    weights = boundary["weights"]
    raw_weight = mean((weights["walk_block"], weights["see_block"], weights["grouping_strength"]))
    points = boundary.get("points") or []
    length = _polyline_length(points) if len(points) >= 2 else max(
        boundary["rect"].width,
        boundary["rect"].height,
    )
    descriptor["length"] = round(length, 4)
    descriptor["influence"] = round(length * raw_weight, 4)
    return descriptor


def _thickness_weighted_boundary_axis_descriptor(boundary: dict) -> dict:
    descriptor = _length_weighted_boundary_axis_descriptor(boundary)
    weights = boundary["weights"]
    raw_weight = mean((weights["walk_block"], weights["see_block"], weights["grouping_strength"]))
    thickness = 0.0
    try:
        thickness = float(boundary.get("metadata", {}).get("thickness", 0.0))
    except ValueError:
        pass
    points = boundary.get("points") or []
    length = _polyline_length(points) if len(points) >= 2 else max(
        boundary["rect"].width,
        boundary["rect"].height,
    )
    descriptor["thickness"] = round(thickness, 4)
    descriptor["influence"] = round(length * raw_weight * thickness, 4)
    return descriptor


def _axis_angle(record: dict) -> float:
    return _record_axis_angle(record)


def _record_axis_angle(record: dict) -> float:
    return _record_axis_descriptor(record)["angle"]


def _record_axis_descriptor(record: dict) -> dict:
    raw = record.get("metadata", {}).get("axis-angle")
    if raw is not None:
        try:
            return {
                "id": record["id"],
                "angle": round(float(raw), 4),
                "basis": "authored_axis_angle",
            }
        except ValueError:
            pass
    points = record.get("points") or []
    if record.get("role") == "region" and len(points) >= 3:
        return {
            "id": record["id"],
            "angle": round(_polygon_pca_axis_angle(points), 4),
            "basis": "polygon_pca_axis",
        }
    if len(points) >= 2:
        return {
            "id": record["id"],
            "angle": round(_longest_edge_angle(points), 4),
            "basis": "polygon_longest_edge",
        }
    rect = record["rect"]
    return {
        "id": record["id"],
        "angle": 0.0 if rect.width >= rect.height else 90.0,
        "basis": "bbox_long_axis",
    }


def _polygon_pca_axis_angle(points: list[tuple[float, float]]) -> float:
    unique = points[:-1] if points[:1] == points[-1:] else points
    cx = mean(point[0] for point in unique)
    cy = mean(point[1] for point in unique)
    xx = mean((point[0] - cx) ** 2 for point in unique)
    yy = mean((point[1] - cy) ** 2 for point in unique)
    xy = mean((point[0] - cx) * (point[1] - cy) for point in unique)
    angle = (degrees(0.5 * atan2(2 * xy, xx - yy)) + 180) % 180
    return 0.0 if abs(angle - 180) < 1e-9 else angle


def _axis_pair_score(a: float, b: float) -> float:
    return abs(cos(radians((a - b) * 2)))


def _entry_touch_evidence(
    entries: list[dict],
    entry_edges: list[dict],
    boundaries: list[dict],
) -> list[dict]:
    touched_paths_by_entry = {
        entry["id"]: [
            edge["refs"]["path"]
            for edge in entry_edges
            if edge["refs"]["entry"] == entry["id"]
        ]
        for entry in entries
    }
    associations = {
        item["id"]: item for item in _entry_nearest_boundary_associations(entries, boundaries)
    }
    return [
        {
            "id": descriptor["id"],
            "edge": descriptor["edge"],
            "width": descriptor["width"],
            "boundary_id": associations[entry["id"]]["boundary_id"],
            "boundary_gap": associations[entry["id"]]["gap"],
            "touched_path_ids": sorted(touched_paths_by_entry[entry["id"]]),
        }
        for entry in entries
        for descriptor in [_entry_width_descriptor(entry)]
        if entry["id"] in associations
    ]


def _rects_touch(a, b) -> bool:
    return not (
        a.right < b.left
        or a.left > b.right
        or a.bottom < b.top
        or a.top > b.bottom
    )


def _rect_gap(a, b) -> float:
    dx = max(b.left - a.right, a.left - b.right, 0.0)
    dy = max(b.top - a.bottom, a.top - b.bottom, 0.0)
    return hypot(dx, dy)


def _rect_overlap_area(a, b) -> float:
    width = min(a.right, b.right) - max(a.left, b.left)
    height = min(a.bottom, b.bottom) - max(a.top, b.top)
    if width <= 0 or height <= 0:
        return 0.0
    return width * height


def _polygon_rect_gap(points: list[tuple[float, float]], rect) -> float:
    rect_points = [
        (rect.left, rect.top),
        (rect.right, rect.top),
        (rect.right, rect.bottom),
        (rect.left, rect.bottom),
    ]
    polygon_edges = _closed_edges(points)
    rect_edges = _closed_edges(rect_points)
    if any(_segments_intersect(a, b, c, d) for a, b in polygon_edges for c, d in rect_edges):
        return 0.0
    if any(_point_in_polygon(point, points) for point in rect_points):
        return 0.0
    if any(_point_in_rect(point, rect) for point in points):
        return 0.0
    return min(
        _point_segment_distance(point, start, end)
        for point in points + rect_points
        for start, end in (rect_edges if point in points else polygon_edges)
    )


def _closed_edges(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    if len(points) < 2:
        return []
    unique = points[:-1] if points[:1] == points[-1:] else points
    return [
        (point, unique[(index + 1) % len(unique)])
        for index, point in enumerate(unique)
    ]


def _point_in_rect(point: tuple[float, float], rect) -> bool:
    x, y = point
    return rect.left <= x <= rect.right and rect.top <= y <= rect.bottom


def _point_in_polygon(
    point: tuple[float, float],
    polygon: list[tuple[float, float]],
) -> bool:
    x, y = point
    inside = False
    for start, end in _closed_edges(polygon):
        x1, y1 = start
        x2, y2 = end
        if _point_on_segment_2d(point, start, end):
            return True
        if (y1 > y) != (y2 > y):
            cross_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < cross_x:
                inside = not inside
    return inside


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return (
        (abs(o1) < 1e-9 and _point_on_segment_2d(c, a, b))
        or (abs(o2) < 1e-9 and _point_on_segment_2d(d, a, b))
        or (abs(o3) < 1e-9 and _point_on_segment_2d(a, c, d))
        or (abs(o4) < 1e-9 and _point_on_segment_2d(b, c, d))
    )


def _line_segment_intersection_point(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> tuple[float, float] | None:
    denominator = (a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0])
    if abs(denominator) <= 1e-9:
        return None
    x_num = (
        (a[0] * b[1] - a[1] * b[0]) * (c[0] - d[0])
        - (a[0] - b[0]) * (c[0] * d[1] - c[1] * d[0])
    )
    y_num = (
        (a[0] * b[1] - a[1] * b[0]) * (c[1] - d[1])
        - (a[1] - b[1]) * (c[0] * d[1] - c[1] * d[0])
    )
    point = (x_num / denominator, y_num / denominator)
    if _point_on_segment_2d(point, a, b) and _point_on_segment_2d(point, c, d):
        return round(point[0], 4), round(point[1], 4)
    return None


def _unique_points(points) -> list[tuple[float, float]]:
    unique = []
    seen = set()
    for point in points:
        if point in seen:
            continue
        seen.add(point)
        unique.append(point)
    return unique


def _orientation(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_on_segment_2d(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    if abs(_orientation(start, end, point)) > 1e-9:
        return False
    return (
        min(start[0], end[0]) - 1e-9 <= point[0] <= max(start[0], end[0]) + 1e-9
        and min(start[1], end[1]) - 1e-9 <= point[1] <= max(start[1], end[1]) + 1e-9
    )


def _point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-9:
        return hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    return hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _node_id(kind: str, record: dict) -> str:
    return f"node_{kind}_{record['id']}"


def _graph_edge(
    kind: str,
    left: dict,
    right: dict,
    left_kind: str,
    right_kind: str,
) -> dict:
    return {
        "id": f"edge_{kind}_{left['id']}_{right['id']}",
        "kind": kind,
        "a": _node_id(left_kind, left),
        "b": _node_id(right_kind, right),
        "refs": {left_kind: left["id"], right_kind: right["id"]},
    }


def _graph_metrics(graph: dict) -> dict:
    nodes = {node["id"]: node for node in graph["nodes"]}
    adjacency = {node_id: set() for node_id in nodes}
    weighted_adjacency = {node_id: [] for node_id in nodes}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["a"], set()).add(edge["b"])
        adjacency.setdefault(edge["b"], set()).add(edge["a"])
        distance = _node_distance(nodes[edge["a"]], nodes[edge["b"]])
        weighted_adjacency.setdefault(edge["a"], []).append((edge["b"], distance))
        weighted_adjacency.setdefault(edge["b"], []).append((edge["a"], distance))

    entry_nodes = [
        node["id"] for node in graph["nodes"] if node["kind"] == "entry"
    ]
    region_nodes = [
        node["id"] for node in graph["nodes"] if node["kind"] == "region"
    ]
    distances = []
    shortest_distances = []
    detours = []
    reached_regions = set()
    for entry_node in entry_nodes:
        entry_distances = _bfs_distances(entry_node, adjacency)
        weighted_distances = _dijkstra_distances(entry_node, weighted_adjacency)
        for region_node in region_nodes:
            distance = entry_distances.get(region_node)
            if distance is not None:
                distances.append(distance)
                reached_regions.add(region_node)
            weighted_distance = weighted_distances.get(region_node)
            direct_distance = _node_distance(nodes[entry_node], nodes[region_node])
            if weighted_distance is not None and direct_distance > 1e-9:
                shortest_distances.append(weighted_distance)
                detours.append(weighted_distance / direct_distance)
    reached_region_ids = sorted(nodes[node_id]["ref_id"] for node_id in reached_regions)
    unreached_region_ids = sorted(
        nodes[node_id]["ref_id"] for node_id in set(region_nodes) - reached_regions
    )
    dead_end_nodes = [
        {
            "id": node_id,
            "kind": nodes[node_id]["kind"],
            "degree": len(adjacency.get(node_id, ())),
        }
        for node_id in nodes
        if len(adjacency.get(node_id, ())) <= 1
    ]
    components = _components(nodes, adjacency)
    component_count = len(components)
    cycle_rank_inputs = {
        "node_count": len(nodes),
        "edge_count": len(graph["edges"]),
        "component_count": component_count,
    }
    loop_count = max(0, len(graph["edges"]) - len(nodes) + component_count)
    return {
        "entry_region_reachability": round(
            len(reached_regions) / max(1, len(region_nodes)), 4
        ),
        "reached_region_ids": reached_region_ids,
        "unreached_region_ids": unreached_region_ids,
        "entry_region_mean_hops": round(mean(distances), 4) if distances else None,
        "entry_region_mean_shortest_distance": round(mean(shortest_distances), 4)
        if shortest_distances
        else None,
        "entry_region_mean_detour_ratio": round(mean(detours), 4) if detours else None,
        "dead_end_ratio": round(len(dead_end_nodes) / max(1, len(nodes)), 4),
        "dead_end_nodes": dead_end_nodes,
        "component_count": component_count,
        "components": components,
        "loop_count": loop_count,
        "loop_ratio": round(loop_count / max(1, len(graph["edges"])), 4),
        "cycle_rank_inputs": cycle_rank_inputs,
    }


def _bfs_distances(start: str, adjacency: dict[str, set[str]]) -> dict[str, int]:
    distances = {start: 0}
    queue = deque([start])
    while queue:
        node_id = queue.popleft()
        for neighbor in adjacency.get(node_id, ()):
            if neighbor in distances:
                continue
            distances[neighbor] = distances[node_id] + 1
            queue.append(neighbor)
    return distances


def _components(nodes: dict, adjacency: dict[str, set[str]]) -> list[list[str]]:
    unseen = set(nodes)
    components = []
    for start in nodes:
        if start not in unseen:
            continue
        component = sorted(_bfs_distances(start, adjacency))
        components.append(component)
        unseen.difference_update(component)
    return components


def _dijkstra_distances(
    start: str,
    adjacency: dict[str, list[tuple[str, float]]],
) -> dict[str, float]:
    distances = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        distance, node_id = heappop(queue)
        if distance > distances[node_id]:
            continue
        for neighbor, weight in adjacency.get(node_id, ()):
            candidate = distance + weight
            if candidate >= distances.get(neighbor, float("inf")):
                continue
            distances[neighbor] = candidate
            heappush(queue, (candidate, neighbor))
    return distances


def _node_distance(a: dict, b: dict) -> float:
    return hypot(a["point"][0] - b["point"][0], a["point"][1] - b["point"][1])


def _first_boundary_kind(boundaries: list[dict], kind: str) -> dict | None:
    return next(
        (
            boundary
            for boundary in boundaries
            if boundary.get("metadata", {}).get("boundary-kind") == kind
        ),
        None,
    )


def _longest_edge_angle(points: list[tuple[float, float]]) -> float:
    best = (0.0, 0.0)
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy
        if length_sq > best[0]:
            best = (length_sq, degrees(atan2(dy, dx)) % 180)
    return best[1]

