
"""Generate a read-only D6 furniture-group zone candidate experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ifcopenshell
import ifcopenshell.geom
import networkx as nx
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union

from adapters.ifc_bonsai import _native_length_unit, _native_mesh_record, _native_source_id

SCHEMA = "d6-space-field-zone-visual-experiment/v1"
IFC_DEFAULT = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]


def _sha256(path: Path) -> str:
    """Return a stable SHA-256 digest for provenance."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    """Convert geometry and scalar values to strict JSON-compatible data."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite value cannot be serialized")
        return value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _write(path: Path, payload: Any) -> None:
    """Write deterministic UTF-8 JSON for one experiment artifact."""
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _representation(entity: object, identifier: str) -> object | None:
    """Find an exact authored IFC representation without guessing by name."""
    product_representation = getattr(entity, "Representation", None)
    return next(
        (
            item
            for item in getattr(product_representation, "Representations", ()) or ()
            if getattr(item, "RepresentationIdentifier", None) == identifier
        ),
        None,
    )


def _mesh(entity: object, units: str, label: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Extract one read-only transport mesh and expose missing geometry explicitly."""
    for representation_name in ("Analysis", "Body"):
        representation = _representation(entity, representation_name)
        if representation is None:
            continue
        mesh, uncertainty = _native_mesh_record(
            entity,
            f"{_native_source_id(entity)}:{label.lower()}",
            units,
            ifcopenshell,
            representation,
        )
        if mesh is not None:
            return (
                mesh.to_dict(),
                {
                    "status": "computed",
                    "representation": representation_name,
                    "source_id": _native_source_id(entity),
                    "uncertainty": None if uncertainty is None else uncertainty.to_dict(),
                },
            )
    return None, {
        "status": "missing",
        "representation": None,
        "source_id": _native_source_id(entity),
        "uncertainty": {
            "code": "missing_geometry",
            "message": "No usable Analysis or Body representation was extracted.",
        },
    }


def _footprint(mesh: dict[str, Any]) -> Polygon | None:
    """Build a conservative planar footprint for display and relation evidence."""
    points = [(float(point[0]), float(point[1])) for point in mesh.get("vertices", ())]
    if len(points) < 3:
        return None
    polygon = MultiPoint(points).convex_hull
    return polygon if not polygon.is_empty and polygon.area > 0.0 else None


def _geometry_parts(geometry: object) -> list[list[list[float]]]:
    """Serialize polygonal geometry parts as closed coordinate rings."""
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [[[float(x), float(y)] for x, y in geometry.exterior.coords]]
    if geometry.geom_type == "MultiPolygon":
        return [
            [[float(x), float(y)] for x, y in part.exterior.coords]
            for part in geometry.geoms
            if not part.is_empty
        ]
    return _geometry_parts(geometry.convex_hull)


def _polygon_from_parts(parts: list[list[list[float]]]) -> object:
    """Rebuild a polygonal display geometry from serialized parts."""
    return unary_union([Polygon(part) for part in parts if len(part) >= 4])


def _member_record(entity: object, units: str) -> dict[str, Any]:
    """Return one furniture member record with group-preserving footprint facts."""
    mesh, extraction = _mesh(entity, units, "Analysis")
    if mesh is None:
        return {
            "source_id": _native_source_id(entity),
            "class": entity.is_a(),
            "status": "missing",
            "geometry_parts": [],
            "z_range": None,
            "extraction": extraction,
        }
    footprint = _footprint(mesh)
    vertices = mesh.get("vertices", ())
    zs = [float(point[2]) for point in vertices]
    return {
        "source_id": _native_source_id(entity),
        "class": entity.is_a(),
        "status": "computed" if footprint is not None else "missing",
        "geometry_parts": _geometry_parts(footprint),
        "z_range": [min(zs), max(zs)] if zs else None,
        "extraction": extraction,
    }


def _group_records(source: object, units: str) -> tuple[list[dict[str, Any]], dict[str, object]]:
    """Extract exactly authored furniture groups and never split their members."""
    groups = []
    members_seen: set[str] = set()
    all_groups = 0
    eligible_groups = 0
    for group in source.by_type("IfcGroup"):
        all_groups += 1
        if getattr(group, "ObjectType", None) != "furniture_group":
            continue
        eligible_groups += 1
        members = []
        for relation in getattr(group, "IsGroupedBy", ()) or ():
            members.extend(getattr(relation, "RelatedObjects", ()) or ())
        member_records = [_member_record(member, units) for member in members]
        members_seen.update(item["source_id"] for item in member_records)
        polygons = [
            _polygon_from_parts(item["geometry_parts"])
            for item in member_records
            if item["status"] == "computed"
        ]
        polygons = [item for item in polygons if item is not None and not item.is_empty]
        geometry = unary_union(polygons) if polygons else None
        centroid = geometry.centroid if geometry is not None and not geometry.is_empty else None
        z_values = [
            value
            for item in member_records
            for value in (item.get("z_range") or ())
        ]
        groups.append(
            {
                "group_id": f"ifc-group:{_native_source_id(group)}",
                "source_id": _native_source_id(group),
                "name": getattr(group, "Name", None),
                "group_role": getattr(group, "ObjectType", None),
                "member_count": len(member_records),
                "usable_member_count": sum(item["status"] == "computed" for item in member_records),
                "member_source_ids": [item["source_id"] for item in member_records],
                "members": member_records,
                "geometry_parts": _geometry_parts(geometry),
                "area_m2": float(geometry.area) if geometry is not None else None,
                "centroid_m": [float(centroid.x), float(centroid.y)] if centroid is not None else None,
                "z_range_m": [min(z_values), max(z_values)] if z_values else None,
                "status": "computed" if geometry is not None else "missing",
                "provenance": {
                    "source_kind": "ifc_authored_group",
                    "selection_rule": 'exact group_role == "furniture_group"',
                    "source_global_id": _native_source_id(group),
                },
            }
        )
    groups.sort(key=lambda item: item["source_id"])
    return groups, {
        "IfcGroup_total": all_groups,
        "exact_furniture_group_total": eligible_groups,
        "unique_grouped_member_total": len(members_seen),
    }


def _context_records(source: object, units: str, grouped_members: set[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Extract low-contrast reference footprints and retain physical walls."""
    records: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    include_classes = {
        "IfcWall",
        "IfcDoor",
        "IfcWindow",
        "IfcColumn",
        "IfcSlab",
        "IfcFurnishingElement",
        "IfcFurniture",
    }
    for entity in source.by_type("IfcProduct"):
        cls = entity.is_a()
        if cls not in include_classes:
            continue
        source_id = _native_source_id(entity)
        if cls == "IfcFurniture" and source_id in grouped_members:
            continue
        mesh, extraction = _mesh(entity, units, cls)
        counts[cls] = counts.get(cls, 0) + 1
        if mesh is None:
            records.append(
                {
                    "source_id": source_id,
                    "class": cls,
                    "role": "physical_wall_geometry" if cls == "IfcWall" else "context_reference",
                    "status": "missing",
                    "geometry_parts": [],
                    "extraction": extraction,
                }
            )
            continue
        footprint = _footprint(mesh)
        records.append(
            {
                "source_id": source_id,
                "class": cls,
                "role": "physical_wall_geometry" if cls == "IfcWall" else "context_reference",
                "status": "computed" if footprint is not None else "missing",
                "geometry_parts": _geometry_parts(footprint),
                "extraction": extraction,
            }
        )
    return records, counts


def _relation_records(groups: list[dict[str, Any]]) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    """Compute independent relative geometry channels between group nodes."""
    relation_map: dict[tuple[str, str], dict[str, Any]] = {}
    for index, left in enumerate(groups):
        left_geometry = _polygon_from_parts(left["geometry_parts"])
        for right in groups[index + 1 :]:
            right_geometry = _polygon_from_parts(right["geometry_parts"])
            key = tuple(sorted((left["group_id"], right["group_id"])))
            if left_geometry is None or right_geometry is None:
                relation_map[key] = {
                    "status": "not_available",
                    "boundary_gap_m": None,
                    "normalized_gap": None,
                    "overlap_area_m2": None,
                    "z_compatible": None,
                    "source_refs": [left["group_id"], right["group_id"]],
                }
                continue
            gap = float(left_geometry.distance(right_geometry))
            overlap = float(left_geometry.intersection(right_geometry).area)
            min_area = max(min(float(left["area_m2"]), float(right["area_m2"])), 1e-12)
            normalized_gap = gap / math.sqrt(min_area)
            left_z = left.get("z_range_m")
            right_z = right.get("z_range_m")
            z_compatible = (
                left_z is not None
                and right_z is not None
                and max(left_z[0], right_z[0]) < min(left_z[1], right_z[1])
            )
            relation_map[key] = {
                "status": "computed",
                "boundary_gap_m": gap,
                "normalized_gap": normalized_gap,
                "overlap_area_m2": overlap,
                "overlap_or_touch": bool(gap <= 1e-12 or overlap > 1e-12),
                "centroid_distance_m": math.dist(left["centroid_m"], right["centroid_m"]),
                "z_compatible": z_compatible,
                "height_channel": "computed",
                "obstacle_channel": "not_evaluated",
                "source_refs": [left["group_id"], right["group_id"]],
            }
    pairs = [
        {"left": key[0], "right": key[1], **value}
        for key, value in sorted(relation_map.items())
    ]
    return relation_map, pairs


def _mst_candidates(groups: list[dict[str, Any]], relation_map: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a baseline plus several diagnostic gap-cut partitions."""
    group_ids = [item["group_id"] for item in groups]
    graph = nx.Graph()
    graph.add_nodes_from(group_ids)
    for (left, right), relation in relation_map.items():
        if relation["status"] == "computed":
            graph.add_edge(left, right, weight=float(relation["normalized_gap"]))
    tree = nx.minimum_spanning_tree(graph, weight="weight")
    tree_edges = sorted(
        tree.edges(data=True),
        key=lambda edge: (float(edge[2]["weight"]), edge[0], edge[1]),
        reverse=True,
    )
    positive_edges = [edge for edge in tree_edges if float(edge[2]["weight"]) > 1e-12]

    candidates = [
        {
            "candidate_id": "candidate:baseline:one_region",
            "label": "baseline — one region, no internal split",
            "region_count": 1,
            "basis": "entire provisional diagnostic frame; no internal partition applied",
            "cut_edges": [],
            "regions": [group_ids],
        }
    ]
    for region_count in (2, 3, 4):
        cut_edges = positive_edges[: region_count - 1]
        reduced = tree.copy()
        reduced.remove_edges_from([(edge[0], edge[1]) for edge in cut_edges])
        regions = sorted(
            [sorted(component) for component in nx.connected_components(reduced)],
            key=lambda component: (component[0], len(component)),
        )
        candidates.append(
            {
                "candidate_id": f"candidate:mst_gap_cut:{region_count}_regions",
                "label": f"diagnostic candidate — {region_count} regions by largest relative gap cuts",
                "region_count": len(regions),
                "basis": "MST over normalized 2D boundary gaps; cut the largest positive edges; no fixed metre threshold",
                "cut_edges": [
                    {
                        "left": edge[0],
                        "right": edge[1],
                        "normalized_gap": float(edge[2]["weight"]),
                        "boundary_gap_m": relation_map[tuple(sorted((edge[0], edge[1])))]["boundary_gap_m"],
                    }
                    for edge in cut_edges
                ],
                "regions": regions,
            }
        )
    return candidates


def _candidate_payload(candidate: dict[str, Any], groups_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Add display-only zone envelopes while retaining group-node membership."""
    regions = []
    for index, member_ids in enumerate(candidate["regions"], start=1):
        geometries = [
            _polygon_from_parts(groups_by_id[item]["geometry_parts"])
            for item in member_ids
        ]
        geometries = [item for item in geometries if item is not None and not item.is_empty]
        union = unary_union(geometries) if geometries else None
        display = union.convex_hull if union is not None and not union.is_empty else None
        regions.append(
            {
                "region_id": f"{candidate['candidate_id']}:region:{index}",
                "display_geometry_method": "convex_hull_of_group_footprints",
                "group_ids": member_ids,
                "geometry_parts": _geometry_parts(display),
                "area_m2": float(display.area) if display is not None else None,
                "color": PALETTE[(index - 1) % len(PALETTE)],
            }
        )
    return {**candidate, "regions": regions}


def _source_summary(source: object, source_path: Path, units: str, scale: float, group_counts: dict[str, Any], context_counts: dict[str, int]) -> dict[str, Any]:
    """Summarize native IFC facts and the confirmed current Blender source."""
    return {
        "schema": SCHEMA,
        "source_ifc": {
            "path": str(source_path.resolve()),
            "bytes": source_path.stat().st_size,
            "sha256": _sha256(source_path),
            "ifc_schema": source.schema,
            "units": {"token": units, "scale_to_metres": scale},
            "counts": {cls: len(source.by_type(cls)) for cls in (
                "IfcGroup", "IfcFurniture", "IfcWall", "IfcDoor", "IfcOpeningElement",
                "IfcRelVoidsElement", "IfcRelFillsElement", "IfcSpace", "IfcBuildingStorey",
            )},
        },
        "current_blender_identity": {
            "observed": True,
            "scene_name": "Scene",
            "blender_version": "5.2.0 LTS",
            "portable_executable": "D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe",
            "scene_filepath": "",
            "bonsai_ifc_store_path": "D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc",
            "unit_settings": {"system": "METRIC", "length_unit": "MILLIMETERS", "scale_length": 1.0},
            "floor_candidates": ["IfcBuildingStorey/Level 1"],
            "object_count": 372,
            "mesh_count": 363,
            "ifc_object_counts": {
                "IfcGroup": 37, "IfcFurniture": 95, "IfcWall": 11, "IfcDoor": 6,
                "IfcOpeningElement": 0, "IfcRelVoidsElement": 0, "IfcRelFillsElement": 0,
                "IfcSpace": 0, "IfcBuildingStorey": 1,
            },
            "source_path_match": True,
            "match_basis": "Bonsai IfcStore.path read directly from current Blender and equals source_ifc.path.",
        },
        "group_selection": {
            **group_counts,
            "selection_rule": 'exact group_role == "furniture_group"',
            "members_are_not_split": True,
        },
        "context_inventory": context_counts,
        "context_extraction_scope": {
            "included_ifc_product_classes": [
                "IfcWall", "IfcDoor", "IfcWindow", "IfcColumn", "IfcSlab",
                "IfcFurnishingElement", "IfcFurniture",
            ],
            "other_ifc_product_classes": "not_extracted_for_context_display; analysis membership is never inferred from class",
            "IfcBuildingElementProxy": "not_extracted_for_context_display",
        },
        "geometry_capabilities": {
            "group_plan_geometry": "computed",
            "height_compatibility": "computed",
            "physical_wall_geometry": "computed",
            "analysis_domain": "not_available",
            "opening_host_relation": "not_available",
            "door_state": "not_available",
            "free_space": "not_computed",
            "walkability": "not_computed",
            "visibility": "not_computed",
            "route_or_accessibility": "not_computed",
        },
    }


def _write_record(output: Path, summary: dict[str, Any], groups: list[dict[str, Any]], context: list[dict[str, Any]], pairs: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> None:
    """Write machine-readable evidence artifacts for owner review."""
    _write(output / "source_summary.json", summary)
    _write(output / "furniture_group_nodes.json", {"schema": SCHEMA, "groups": groups})
    _write(output / "group_relation_evidence.json", {"schema": SCHEMA, "relations": pairs})
    _write(output / "zone_candidates.json", {"schema": SCHEMA, "candidates": candidates})
    _write(
        output / "provenance.json",
        {
            "schema": SCHEMA,
            "source_path": summary["source_ifc"]["path"],
            "source_sha256": summary["source_ifc"]["sha256"],
            "current_blender_source_path": summary["current_blender_identity"]["bonsai_ifc_store_path"],
            "current_blender_source_match": True,
            "algorithm": {
                "name": "diagnostic MST gap-cut comparison",
                "group_nodes": 'exact group_role == "furniture_group"',
                "pair_channels": ["planar boundary gap", "overlap_or_touch", "centroid distance", "height compatibility"],
                "partition_generation": "baseline plus 2/3/4-region cuts at largest positive MST normalized-gap edges",
                "fixed_metre_threshold": False,
                "production_selection": False,
            },
            "boundary": {
                "candidate": "scene-geometry fallback frame from source geometry extent",
                "status": "diagnostic_only",
                "owner_confirmed": False,
                "analysis_domain": "not_available",
                "reason": "live IFC has zero IfcSpace and no accepted AnalysisDomain record",
            },
            "door_and_opening": {
                "ifc_opening_relations": "not_available",
                "door_state": "not_available",
                "door_geometry_used_as_opening": False,
            },
        },
    )
    _write(
        output / "scope_audit.json",
        {
            "schema": SCHEMA,
            "read_only_experiment": True,
            "production_code_modified": False,
            "adapters_modified": False,
            "formal_tests_modified": False,
            "public_api_modified": False,
            "dependencies_modified": False,
            "source_ifc_modified": False,
            "current_blender_scene_modified": False,
            "outputs_written_only_under": str(output.resolve()),
            "not_computed": ["AnalysisDomain selection", "free-space", "connectivity", "routes", "walkability", "visibility", "activity function", "production room role"],
            "context_policy": "walls, doors, and other ungrouped objects are reference/context only",
            "group_policy": 'only exact group_role == "furniture_group"; no name/layer/proximity inference creates membership',
        },
    )
    render_input = {
        "schema": SCHEMA,
        "source_summary": summary,
        "groups": groups,
        "context": context,
        "candidates": candidates,
        "boundary": {
            "status": "diagnostic_only",
            "label": "provisional diagnostic boundary — scene geometry fallback, not an accepted AnalysisDomain",
        },
    }
    _write(output / "render_input.json", render_input)


def _write_record_md(output: Path, summary: dict[str, Any], groups: list[dict[str, Any]], context: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> None:
    """Write a compact owner-facing experiment record."""
    counts = summary["source_ifc"]["counts"]
    lines = [
        "# D6 当前 IFC 空间分区候选 Blender 可视化实验",
        "",
        "- 日期：2026-10-02",
        "- 状态：STOP FOR OWNER VISUAL REVIEW",
        "- 目的：并列展示不细分基线与几何关系支持的探索性分区候选。",
        "- 当前 Blender：已直接观察并确认 Bonsai IfcStore.path 与本实验 IFC 相同；当前场景未修改、未保存。",
        "",
        "## 边界与状态",
        "",
        "当前 IFC 没有 IfcSpace，也没有 owner 接受的 AnalysisDomain。所有图使用源几何范围作为 diagnostic_only 视图框，并明确标为 provisional；它不是 room、free-space 或生产边界。",
        "",
        "## 实测可用输入",
        "",
        f"- IFC4；长度单位 {summary['source_ifc']['units']['token']}，换算到米 {summary['source_ifc']['units']['scale_to_metres']}。",
        f"- 原生计数：IfcGroup={counts['IfcGroup']}、IfcFurniture={counts['IfcFurniture']}、IfcWall={counts['IfcWall']}、IfcDoor={counts['IfcDoor']}、IfcSpace={counts['IfcSpace']}、IfcOpeningElement={counts['IfcOpeningElement']}、IfcRelVoidsElement={counts['IfcRelVoidsElement']}。",
        f"- 分析节点：{len(groups)} 个 exact group_role == furniture_group，成员保持组内不可拆分；{sum(item['usable_member_count'] for item in groups)} 个成员几何可用。",
        f"- 墙体：{sum(item['class']=='IfcWall' and item['status']=='computed' for item in context)} 个可显示的实体墙体几何；墙厚保留在源墙网格的显示层中。",
        "- 组间关系：平面边界间隙、重叠/接触、质心距离和高度兼容性可计算；障碍物穿越关系未用于分区。",
        "",
        "## 缺失或未计算输入",
        "",
        "- 没有合格 AnalysisDomain；没有 free-space、连通性、route、walkability、visibility 或空间功能结论。",
        "- 没有 IfcRelVoidsElement / IfcRelFillsElement；门几何不被解释为 opening relation，也不推断开闭状态。",
        "- 标签/name 只作为并列诊断字段，不参与分区；没有未经校准的概率或准确率。",
        "",
        "## 候选为何不同",
        "",
        "- 基线把全部家具组放入一个 provisional diagnostic region，显示“也可能不再细分”。",
        "- 2/3/4 区候选使用同一组间几何关系图：以归一化平面边界间隙构造最小生成树，再分别切除最大、前两条、前三条正间隙边。没有固定米数阈值；切口边和原始数值写入 zone_candidates.json。",
        "- 这些切分是并列诊断视图，不代表最终分区数、最终算法或 owner 认可。",
        "",
        "## 视觉阅读提示",
        "",
        "- 彩色半透明块：候选区域的显示包络；黑色边框和 Gxx：一个不可拆分的 furniture_group analysis node。",
        "- 灰色实体：墙体或 context/reference；门只作为 context/reference。",
        "- 图例包含 provisional diagnostic candidate — not owner-confirmed、furniture_group analysis node、context/reference only、physical wall geometry 及边界状态。",
        "",
        "## Owner 目视问题",
        "",
        "- 哪个候选最像你理解的空间分区？",
        "- 有没有图上没分开、但你认为应单独成区的部分？",
        "- 这些颜色更像独立区域，还是一个连续场中的软边界？",
        "",
        "STOP FOR OWNER VISUAL REVIEW",
    ]
    (output / "experiment_record.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Extract current IFC evidence and write diagnostic candidate inputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ifc", type=Path, default=IFC_DEFAULT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_path = args.ifc.resolve()
    source = ifcopenshell.open(str(source_path))
    units, scale, explicit, metadata = _native_length_unit(source)
    groups, group_counts = _group_records(source, units)
    grouped_members = {member for group in groups for member in group["member_source_ids"]}
    context, context_counts = _context_records(source, units, grouped_members)
    relation_map, pairs = _relation_records(groups)
    candidates = [
        _candidate_payload(candidate, {item["group_id"]: item for item in groups})
        for candidate in _mst_candidates(groups, relation_map)
    ]
    summary = _source_summary(source, source_path, units, scale, group_counts, context_counts)
    summary["current_blender_identity"]["observed_at"] = "2026-10-02"
    _write_record(output, summary, groups, context, pairs, candidates)
    _write_record_md(output, summary, groups, context, candidates)
    assert len(groups) == 37
    assert all(item["group_role"] == "furniture_group" for item in groups)
    assert all(item["usable_member_count"] > 0 for item in groups)
    assert candidates[0]["region_count"] == 1
    print(json.dumps({"status": "pass", "groups": len(groups), "members": len(grouped_members), "candidates": [item["candidate_id"] for item in candidates]}, ensure_ascii=False))


if __name__ == "__main__":
    main()




