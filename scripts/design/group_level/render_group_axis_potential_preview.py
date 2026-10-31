"""Render linked, read-only views of the retained real-IFC support matrix."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
REPLAY = ROOT / "outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z"
OUTPUT = ROOT / "outputs/design/group_axis_potential_visual_preview"
PINNED_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
INPUTS = ("field_matrix.json", "field_profiles.json", "field_directions.json", "description.json", "source_manifest.json")
HIERARCHY_INPUTS = ("axis_potential_output.json", "family_matrix.json", "family_profiles.json", "family_directions.json", "family_view_manifest.json", "hierarchy.json", "report.json", "source_reuse.json", "view_manifest.json")


def _read(path: Path) -> Any:
    """Read one retained JSON artifact without modifying its bytes."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    """Write strict JSON for traceable presentation data."""
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    """Fingerprint the bytes actually consumed or emitted by this preview."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _color(value: float | None) -> str:
    """Map the fixed support range to a single opaque sequential palette."""
    if value is None:
        return "#dedede"
    # The palette only displays the existing scalar; it adds no threshold or evidence.
    return "#" + "".join(f"{round(a + (b-a)*value):02x}" for a, b in zip((239, 246, 255), (26, 76, 139)))


def _label(value: float | None, digits: int = 3) -> str:
    """Format a known reading and keep missing readings distinct from zero."""
    return "NA" if value is None else f"{value:.{digits}f}"


def _presentation_data(value: Any) -> Any:
    """Keep exact rational integers as text across JavaScript JSON.parse."""
    if isinstance(value, dict):
        return {
            key: [str(part) for part in item] if key.endswith("_exact") else _presentation_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_presentation_data(item) for item in value]
    return value


def load_preview(replay: Path) -> dict[str, Any]:
    """Join the retained scalar records to their real analysis-plane polygons."""
    records = {name: _read(replay / name) for name in INPUTS}
    source = records["source_manifest.json"]
    if source["source"]["sha256"] != PINNED_SHA256 or source["source_after"]["sha256"] != PINNED_SHA256:
        raise ValueError("preview requires the pinned IFC-derived replay")
    if source["analysis_plane"]["name"] != "ifc-world-plan":
        raise ValueError("preview requires the retained IFC analysis plane")
    matrix = records["field_matrix.json"]["fields"]
    group_geometry = {item["target_id"]: item for item in records["description.json"]["group_geometry"]}
    group_ids = sorted(group_geometry)
    fields = sorted(matrix, key=lambda field_id: matrix[field_id]["anchor_group_id"])
    profiles = records["field_profiles.json"]["profiles"]
    directions = records["field_directions.json"]["directions"]
    if len(fields) != 37 or len(group_ids) != 37 or set(fields) != set(profiles) or set(fields) != set(directions):
        raise ValueError("the specified replay must retain all 37 groups and fields")
    for field_id in fields:
        cells = matrix[field_id]["cells"]
        if len(cells) != len(group_ids) or {cell["target_group_id"] for cell in cells} != set(group_ids):
            raise ValueError("a field has missing or duplicate scope cells")
        if any(cell["field_id"] != field_id for cell in cells):
            raise ValueError("cell lineage does not match its field")
    # Use the retained member polygons, never a generated furniture or layout proxy.
    points = [point for group in group_geometry.values() for member in group["member_geometry"] for polygon in member["polygons"] for point in polygon]
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    scale = min(1080 / (xmax-xmin), 590 / (ymax-ymin))

    def project(point: list[float]) -> tuple[float, float]:
        """Preserve the IFC plane aspect ratio while mapping it to screen space."""
        return 60 + (point[0]-xmin)*scale, 660 - (point[1]-ymin)*scale

    groups = []
    for index, group_id in enumerate(group_ids):
        group = group_geometry[group_id]
        paths = []
        for member in group["member_geometry"]:
            for polygon in member["polygons"]:
                coords = [project(point) for point in polygon]
                paths.append("M " + " L ".join(f"{x:.3f} {y:.3f}" for x, y in coords) + " Z")
        groups.append({"id": group_id, "code": f"G{index+1:02}", "paths": paths, "label_point": project(group["center"])})
    field_records = []
    for index, field_id in enumerate(fields):
        item = matrix[field_id]
        by_group = {cell["target_group_id"]: cell for cell in item["cells"]}
        field_records.append({"id": field_id, "code": f"F{index+1:02}", "anchor": item["anchor_group_id"], "angle": item["cells"][0]["anchor_axis_angle"], "cells": [by_group[group_id] for group_id in group_ids], "profile": profiles[field_id], "direction": directions[field_id]})
    by_angle = sorted(range(len(fields)), key=lambda i: (field_records[i]["angle"], field_records[i]["id"]))
    first, last = by_angle[0], by_angle[-1]

    def display_separation(index: int) -> float:
        """Sample an existing reference distinct from the two display extremes."""
        gaps = [abs(field_records[index]["angle"]-field_records[other]["angle"]) for other in (first, last)]
        return min(min(gap, 180-gap) for gap in gaps)

    # This only samples display panels; it never creates, merges, or scores fields.
    contrast = max(by_angle, key=display_separation)
    data = {"groups": groups, "fields": field_records, "representatives": [first, contrast, last], "source": source["source"], "plane": source["analysis_plane"], "analysis_frame": records["description.json"]["analysis_frame"], "world_bounds": [xmin, ymin, xmax, ymax], "source_replay": str(replay.resolve())}
    if (replay / "hierarchy.json").is_file():
        missing = [name for name in HIERARCHY_INPUTS if not (replay / name).is_file()]
        if missing:
            raise ValueError(f"hierarchy replay is missing: {', '.join(missing)}")
        data["hierarchy"] = _load_hierarchy_preview(replay, data)
    return data


def _load_hierarchy_preview(replay: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Validate and join family outputs to the same retained groups and source axes."""
    hierarchy = _read(replay / "hierarchy.json")
    family_matrix = _read(replay / "family_matrix.json")["families"]
    profiles = _read(replay / "family_profiles.json")["profiles"]
    directions = _read(replay / "family_directions.json")["directions"]
    family_manifest = _read(replay / "family_view_manifest.json")
    view_manifest = _read(replay / "view_manifest.json")
    source_manifest = _read(replay / "source_manifest.json")
    report = _read(replay / "report.json")
    if report["project_global_id"] != source_manifest["project_global_id"] or report["source"]["sha256"] != data["source"]["sha256"]:
        raise ValueError("hierarchy replay and preview source identity do not match")
    if family_matrix.keys() != profiles.keys() or family_matrix.keys() != directions.keys():
        raise ValueError("family matrices, profiles, and directions must have the same family IDs")
    if family_manifest.get("analysis_plane") != data["plane"] or view_manifest.get("analysis_plane") != data["plane"]:
        raise ValueError("hierarchy views do not use the retained preview analysis plane")
    definitions = {item["family_id"]: item for item in hierarchy["families"]}
    indexed = {item["family_id"]: item for item in family_manifest["families"]}
    group_ids = [group["id"] for group in data["groups"]]
    field_by_id = {field["id"]: field for field in data["fields"]}
    if set(definitions) != set(family_matrix) or set(indexed) != set(family_matrix):
        raise ValueError("family definitions and indexes must retain every family matrix")
    if family_matrix and set(_read(replay / "family_matrix.json")["groups"]) != set(group_ids):
        raise ValueError("family matrix scope differs from the retained geometry")
    families = []
    for index, family_id in enumerate(sorted(family_matrix)):
        matrix = family_matrix[family_id]
        cells = matrix["cells"]
        by_group = {cell["group_id"]: cell for cell in cells}
        if len(cells) != len(group_ids) or set(by_group) != set(group_ids):
            raise ValueError(f"family {family_id} has missing or duplicate scope cells")
        definition = definitions[family_id]
        view = indexed[family_id]
        if view["family_index"] != index or len(definition["leaf_field_ids"]) != len(matrix["leaf_field_ids"]):
            raise ValueError(f"family {family_id} has a mismatched stable index or leaf list")
        if any(leaf_id not in field_by_id for leaf_id in definition["leaf_field_ids"]):
            raise ValueError(f"family {family_id} references an unknown source-axis field")
        residuals = [edge for edge in hierarchy["residuals"] if family_id in (edge["child_family_id"], edge["parent_family_id"])]
        families.append({
            "id": family_id,
            "code": f"H{index + 1:03d}",
            "index": index,
            "view_id": view["view_id"],
            "anchor_group_ids": matrix["anchor_group_ids"],
            "leaf_field_ids": matrix["leaf_field_ids"],
            "birth": matrix["birth"],
            "death": matrix["death"],
            "birth_exact": matrix["birth_exact"],
            "death_exact": matrix["death_exact"],
            "scale_persistence": matrix["scale_persistence"],
            "direction_classes": definition["direction_classes"],
            "parent_ids": definition["parent_ids"],
            "cells": [by_group[group_id] for group_id in group_ids],
            "profile": profiles[family_id],
            "direction": directions[family_id],
            "residuals": residuals,
            "view_ref": view["view_ref"],
        })
    return {"families": families, "scope": hierarchy["scope"], "target_index": view_manifest["target_index"]}


def _family_representatives(data: dict[str, Any]) -> dict[str, int]:
    """Sample one persistent small family and two overlapping maximal top families."""
    families = data["hierarchy"]["families"]
    ordered = sorted(range(len(families)), key=lambda index: (len(families[index]["anchor_group_ids"]), -families[index]["scale_persistence"], families[index]["id"]))
    small = next((index for index in ordered if len(families[index]["anchor_group_ids"]) > 1), None)
    tops = sorted((index for index in ordered if not families[index]["parent_ids"]), key=lambda index: (-len(families[index]["anchor_group_ids"]), families[index]["id"]))
    candidates = [(index, set(families[index]["anchor_group_ids"])) for index in tops]
    # This samples actual anchor sets for display; it never creates a family or membership.
    overlap = next(
        ((left, right)
         for position, (left, left_anchors) in enumerate(candidates)
         for right, right_anchors in candidates[position + 1:]
         if left_anchors & right_anchors and left_anchors - right_anchors and right_anchors - left_anchors),
        None,
    )
    samples = {"small": small} if small is not None else {}
    if overlap is not None:
        samples.update({"overlap_top_a": overlap[0], "overlap_top_b": overlap[1]})
    return samples


def plan_svg(data: dict[str, Any], field_index: int, *, family: bool = False) -> str:
    """Show one complete scope with support fill, group codes and anchor outline."""
    field = data["hierarchy"]["families"][field_index] if family else data["fields"][field_index]
    anchors = set(field["anchor_group_ids"]) if family else {field["anchor"]}
    width = 1560 if family else 1200
    title = f'{field["code"]} | Family support | ifc-world-plan / m' if family else f'{field["code"]} | Reference {data["groups"][field_index]["code"]} | {field["angle"]:.3f}° | ifc-world-plan / m'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 760" role="img" font-family="Arial, sans-serif" aria-label="{field["code"]} real IFC furniture support plan"><rect width="{width}" height="760" fill="white"/>', f'<text x="30" y="32" font-size="21">{title}</text>']
    if family:
        anchor_codes = ", ".join(group["code"] for group in data["groups"] if group["id"] in anchors)
        parts.append(f'<text x="30" y="51" font-size="12">{html.escape(field["id"])}</text><text x="30" y="69" font-size="12">Anchors: {anchor_codes} | lifespan [{field["birth"]:.6f}, {field["death"]:.6f}) degrees</text><text x="1210" y="80" font-size="14">Group | Support 0-1 | Status</text>')
    for group, cell in zip(data["groups"], field["cells"]):
        value = cell["value"] if family else cell["axis_field_support"]
        anchor = group["id"] in anchors
        title = html.escape(f'{group["code"]} | {group["id"]} | support={value} | {cell["status"]} | anchor={anchor}') if family else html.escape(f'{group["code"]} | {group["id"]} | support={value} | {cell["status"]} | self={cell["self_reference"]}')
        parts.append(f'<g data-group="{html.escape(group["id"])}" data-support="{value}" data-self="{str(anchor).lower()}"><title>{title}</title>')
        for path in group["paths"]:
            parts.append(f'<path d="{path}" fill="{_color(value)}" stroke="{"#b34900" if anchor else "#526879"}" stroke-width="{3 if anchor else .65}"/>')
        x, y = group["label_point"]
        parts.append(f'<text x="{x:.2f}" y="{y-8:.2f}" text-anchor="middle" font-size="12" font-weight="700" fill="#172f46" stroke="white" stroke-width="3" paint-order="stroke">{"* " if anchor else ""}{group["code"]}</text>')
        parts.append("</g>")
    if family:
        for row, (group, cell) in enumerate(zip(data["groups"], field["cells"])):
            parts.append(f'<text x="1210" y="{100 + row * 16}" font-size="12">{"* " if group["id"] in anchors else ""}{group["code"]} | {_label(cell["value"], 6)} | {html.escape(cell["status"])}</text>')
    for index in range(101):
        parts.append(f'<rect x="{40+index*2}" y="706" width="2.1" height="12" fill="{_color(index/100)}"/>')
    parts.append('<text x="40" y="742" font-size="14">0.000</text><text x="205" y="742" font-size="14">1.000</text><text x="275" y="720" font-size="15">Fill = support; asterisk (*) / orange outline = reference anchor. All 37 groups retained.</text><text x="275" y="744" font-size="14">Exact readings: linked HTML table. Furniture projections only; no inferred field boundary.</text></svg>')
    return "".join(parts)


def matrix_svg(data: dict[str, Any]) -> str:
    """Export every matrix reading with fixed-scale color and self markers."""
    size, left, top = 31, 115, 145
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1370" role="img"><title>All 37 groups by 37 source-axis fields: support matrix</title><rect width="100%" height="100%" fill="white"/><g font-family="Arial, sans-serif" fill="#172f46"><text x="20" y="30" font-size="21">Furniture group to reference field: complete support matrix</text><text x="20" y="57" font-size="14">Read a row: one group supports multiple fields. Read a column: all groups under one reference.</text><text x="20" y="81" font-size="14">Columns: field F / anchor G / actual axis angle. Fixed 0-1 scale. Values rounded to 2 decimals; asterisk (*) = self.</text>']
    for col, field in enumerate(data["fields"]):
        x = left+col*size+15
        parts.append(f'<text x="{x}" y="110" text-anchor="middle" font-size="10">{field["code"]}</text><text x="{x}" y="125" text-anchor="middle" font-size="9">{data["groups"][col]["code"]}</text><text x="{x}" y="138" text-anchor="middle" font-size="8">{field["angle"]:.1f}°</text>')
    for row, group in enumerate(data["groups"]):
        y = top+row*size
        parts.append(f'<text x="100" y="{y+20}" text-anchor="end" font-size="13">{group["code"]}</text>')
        for col, field in enumerate(data["fields"]):
            cell = field["cells"][row]
            value = cell["axis_field_support"]
            x = left+col*size
            fg = "white" if value is not None and value > .55 else "#172f46"
            parts.append(f'<g data-group="{html.escape(group["id"])}" data-field="{html.escape(field["id"])}" data-value="{value}"><rect x="{x}" y="{y}" width="30" height="30" fill="{_color(value)}"/><text x="{x+15}" y="{y+19}" text-anchor="middle" font-size="10" fill="{fg}">{_label(value, 2)}{"*" if cell["self_reference"] else ""}</text></g>')
    for index in range(101):
        parts.append(f'<rect x="{115+index*2}" y="1308" width="2.1" height="12" fill="{_color(index/100)}"/>')
    parts.append('<text x="80" y="1320" font-size="13">0.0</text><text x="325" y="1320" font-size="13">1.0</text><text x="375" y="1320" font-size="13">Color displays support only; not probability. No row normalization.</text><text x="20" y="1350" font-size="13">G/F codes map to original IFC group / field IDs in manifest.json. Exact values: linked HTML / source JSON.</text></g></svg>')
    return "".join(parts)


def family_matrix_svg(data: dict[str, Any]) -> str:
    """Export every family-by-group value, keeping incomplete values visibly unknown."""
    families = data["hierarchy"]["families"]
    groups = data["groups"]
    left, top, cell_width, cell_height = 315, 142, 27, 17
    width, height = left + len(groups) * cell_width + 20, top + len(families) * cell_height + 70
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img"><title>Complete family support matrix</title><rect width="100%" height="100%" fill="white"/><g font-family="Arial, sans-serif" fill="#172f46"><text x="20" y="30" font-size="21">All generated direction families by furniture group</text><text x="20" y="55" font-size="13">One row per family; one column per retained group. Gray NA means no complete family value.</text><text x="20" y="78" font-size="13">Support uses the existing 0-1 scale. Lifespan is [birth, death); no spatial boundary is implied.</text>']
    for column, group in enumerate(groups):
        x = left + column * cell_width + cell_width / 2
        parts.append(f'<text x="{x}" y="{top - 8}" text-anchor="middle" font-size="8">{html.escape(group["code"])}</text>')
    for row, family in enumerate(families):
        y = top + row * cell_height
        parts.append(f'<text x="{left - 8}" y="{y + 12}" text-anchor="end" font-size="8">{family["code"]} | {family["birth"]:.2f}-{family["death"]:.2f}</text>')
        for column, (group, cell) in enumerate(zip(groups, family["cells"])):
            x = left + column * cell_width
            value, status = cell["value"], cell["status"]
            bounds = f'{cell["lower"]},{cell["upper"]}'
            title = html.escape(f'{family["id"]} | {group["id"]} | value={value} | status={status} | bounds={bounds}')
            parts.append(f'<g data-family-cell="" data-family="{html.escape(family["id"], quote=True)}" data-group="{html.escape(group["id"], quote=True)}" data-value="{value}" data-status="{status}" data-bounds="{bounds}"><title>{title}</title><rect x="{x}" y="{y}" width="{cell_width - 1}" height="{cell_height - 1}" fill="{_color(value)}"/><text x="{x + (cell_width - 1) / 2}" y="{y + 11}" text-anchor="middle" font-size="7">{_label(value, 2)}</text></g>')
    parts.append('</g></svg>')
    return "".join(parts)


PAGE = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>从家具组到参考场 · IFC 支持读数</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#183047;font:15px/1.6 "Segoe UI","Microsoft YaHei",sans-serif}main{max-width:1600px;margin:auto;padding:26px}h1{font-size:28px;margin:0}h2{font-size:20px;margin:0 0 8px}p{margin:7px 0}.intro{max-width:1100px}.badge{display:inline-block;background:#e5edf5;border-radius:5px;padding:2px 8px;font-size:13px}.card{background:white;border:1px solid #d8e1ea;border-radius:12px;padding:20px;margin:20px 0}.grid{display:grid;grid-template-columns:1.35fr 1fr;gap:20px}.scroll{overflow:auto;max-height:670px}table{border-collapse:separate;border-spacing:1px;font-variant-numeric:tabular-nums}th{background:#edf2f7;position:sticky;top:0;z-index:2}th:first-child{left:0;z-index:3}th button{white-space:nowrap}.matrix td{padding:0}.matrix button{width:38px;height:29px;padding:0;border:0;border-radius:0;font-size:11px}.matrix th button{width:38px;font-size:10px;line-height:1.3}.matrix tbody th{position:sticky;left:0;z-index:1}.matrix button.selected{outline:2px solid #e67a12;outline-offset:-2px}.matrix tr.row th{background:#ffe5c4}.matrix th.active{background:#ffe5c4}button,select{cursor:pointer;border:1px solid #b9c9d7;background:white;border-radius:5px;padding:4px 8px;color:#183047}button:focus-visible,select:focus-visible{outline:3px solid #e67a12;outline-offset:2px}select{max-width:100%;font-size:15px}.legend{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.gradient{width:220px;height:14px;background:linear-gradient(to right,#eff6ff,#1a4c8b)}.small{font-size:13px;color:#526879}.plan svg{width:100%;height:auto}.detail td,.detail th{padding:4px 8px;white-space:nowrap}.detail .picked{background:#fff0db}.bar{height:9px;background:#e9eff5;width:180px}.bar i{display:block;height:100%;background:#326aa6}.id{overflow-wrap:anywhere;font:12px/1.4 Consolas,monospace}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.metric{background:#f2f6fa;padding:8px;border-radius:5px}.metric strong{display:block;font-size:20px}.samples{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.samples svg{width:100%;height:auto}.samples button{width:100%;text-align:left}.trace{max-height:240px;overflow:auto}a{color:#1c5890}@media(max-width:950px){.grid,.samples{grid-template-columns:1fr}main{padding:12px}.card{padding:12px}}
</style><main>
<span class="badge">真实 IFC replay · 只读显示 · 37 组 / 37 个参考视图</span><h1>同一组家具，可以同时支持多个参考场</h1>
<div class="intro"><p><b>这里的“场”是一列参考视图：</b>用一个真实家具组的整体轴作为参考，再看所有家具组对这个方向的支持。参考组叫 <b>anchor</b>，用 ★ 和橙色外框标记。</p><p>支持读数 S(g,k) 范围 0–1，越大表示该组的轴越支持该参考方向。<b>不是概率或已确定归属；一行不归一，不选赢家。</b>颜色只显示已有数值，未生成空间边界。</p></div>
<section class="card"><h2>① 全场矩阵：先看重叠，再看位置</h2><p>行 = 家具组 G；列 = 参考场 F（标题同时显示其 anchor G 和实际角度）。点任意格，下面联动显示该场平面和该组跨场读数。</p><div class="legend"><span>支持 0</span><span class="gradient"></span><span>1</span><span>★ 自身参考</span><span>NA 未知，灰色；已知零仍为 0</span></div><p class="small">数字显示到两位；点格后可读原始精度。顺序固定为原始 group ID 顺序；所有 1,369 格都保留。可横向、纵向滚动。</p><div class="scroll"><table class="matrix" id="matrix" aria-label="家具组对全部参考场的支持矩阵"></table></div></section>
<div class="grid"><section class="card"><h2>② 这个场在哪里、谁是参考</h2><label>参考场 <select id="field"></select></label><p id="field-title"></p><div class="plan" id="plan"></div><div class="legend"><span>0</span><span class="gradient"></span><span>1</span><span>★ 橙框 = anchor；填色统一表示支持</span></div><p class="small">只显示同源家具组投影，非房间边界或连续空间力场。点击家具组可查看它跨多个场的读数。</p><div class="metrics" id="metrics"></div><details><summary>原始 field ID / 只读方向描述</summary><div class="id" id="field-id"></div><p id="direction" class="small"></p></details><h3>该场中每个家具组的支持</h3><div class="scroll" style="max-height:330px"><table class="detail" id="column"></table></div></section>
<section class="card"><h2>③ 横看同一组：它同时支持哪些场</h2><label>家具组 <select id="group"></select></label><p id="group-title"></p><p class="small">每条都是同一组对一个不同参考的读数；没有阈值、不做互斥分配。条长使用同一个 0–1 尺度。</p><div class="scroll" style="max-height:570px"><table class="detail" id="row"></table></div><h3>当前格的原始读数</h3><pre class="id trace" id="cell"></pre></section></div>
<section class="card"><h2>④ 三个代表参考，始终使用同一平面与色标</h2><p>从现有 anchor 中展示最小角、最大角，以及与这两者最分离的一个已有参考；不代表三个组织簇或真实场数量。完整 37 场见矩阵与下拉菜单。</p><div class="samples" id="samples"></div></section>
<section class="card"><h2>来源与阅读方法</h2><p>推荐组合：<b>矩阵热图 + 联动平面 + 单行跨场条形明细</b>。矩阵展示重叠，平面定位实体，明细保留精确数值。</p><p>单场图 + 图例/数值适合解释一个参考；完整矩阵最适合比较全部支持；小 multiples 适合少量空间对照，但单独使用会漏掉其余列。三者在本页使用同一原始数据。</p><p>数据文件：<a href="__MATRIX_URI__">field_matrix.json</a> · <a href="__PROFILES_URI__">field_profiles.json</a> · <a href="__DIRECTIONS_URI__">field_directions.json</a> · <a href="manifest.json">预览 manifest</a> · <a href="matrix.svg">完整矩阵 SVG</a></p><p class="small">数值来自冻结 replay；non-self 均值排除 ★ 自身，soft direction 包含自身，是只读描述，不会修改参考角度。平行列按各自真实 anchor 保留，不代表重复投票。该页面不决定 membership 或 merge。</p><div class="id" id="source"></div></section>
__HIERARCHY_SECTION__</main><script id="preview-data" type="application/json">__DATA__</script><script>
const D=JSON.parse(document.getElementById('preview-data').textContent);let fi=0,gi=0;
/** Display an existing value without turning null into a zero. */
function fmt(v,n=3){return v===null||v===undefined?'NA':Number(v).toFixed(n)}
/** Match the SVG palette on the unchanged 0..1 support scale. */
function color(v){return v===null?'#dedede':'rgb('+[239,246,255].map((a,i)=>Math.round(a+([26,76,139][i]-a)*v)).join(',')+')'}
/** Escape source identities before inserting them into markup. */
function esc(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
/** Select one original field and group; this changes presentation only. */
function choose(f,g){fi=f;gi=g;render()}
/** Render the full retained matrix in a fixed identity order. */
function matrix(){let out='<thead><tr><th>组 ↓ / 场 →</th>';D.fields.forEach((f,j)=>out+=`<th class="${j===fi?'active':''}"><button onclick="choose(${j},gi)" aria-label="${f.code}，参考${D.groups[j].code}，${fmt(f.angle)}度">${f.code}<br>${D.groups[j].code}<br>${fmt(f.angle,1)}°</button></th>`);out+='</tr></thead><tbody>';D.groups.forEach((g,i)=>{out+=`<tr class="${i===gi?'row':''}"><th><button onclick="choose(fi,${i})">${g.code}</button></th>`;D.fields.forEach((f,j)=>{const c=f.cells[i],v=c.axis_field_support;out+=`<td><button class="${i===gi||j===fi?'selected':''}" style="background:${color(v)};color:${v!==null&&v>.55?'white':'#183047'}" onclick="choose(${j},${i})" aria-label="${g.code} 对 ${f.code} 支持 ${v} ${c.self_reference?'自身参考':''}" title="${esc(g.id)} → ${esc(f.id)} | ${v}">${fmt(v,2)}${c.self_reference?'★':''}</button></td>`});out+='</tr>'});document.getElementById('matrix').innerHTML=out+'</tbody>'}
/** Build the selected field from the retained real IFC member polygons. */
function plan(index,interactive=true){const f=D.fields[index];let out='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 710" role="img" aria-label="真实IFC家具组平面"><rect width="1200" height="710" fill="white"/>';D.groups.forEach((g,i)=>{const c=f.cells[i],anchor=g.id===f.anchor;out+=`<g ${interactive?`onclick="choose(fi,${i})" tabindex="0" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();choose(fi,${i})}" role="button"`:''} aria-label="${g.code} 支持 ${c.axis_field_support} ${anchor?'参考anchor':''}" style="cursor:pointer"><title>${esc(g.id)} | ${c.axis_field_support}</title>`;g.paths.forEach(p=>out+=`<path d="${p}" fill="${color(c.axis_field_support)}" stroke="${anchor?'#b34900':i===gi?'#141d27':'#526879'}" stroke-width="${anchor?4:i===gi?2:.65}"/>`);out+=`<text x="${g.label_point[0]}" y="${g.label_point[1]-8}" text-anchor="middle" font-size="15" font-weight="700" fill="#183047" stroke="white" stroke-width="4" paint-order="stroke">${anchor?'★ ':''}${g.code}</text></g>`});return out+'</svg>'}
/** Update the linked views using stored cells, profiles and direction records. */
function render(){const f=D.fields[fi],g=D.groups[gi],p=f.profile,q=f.direction,c=f.cells[gi];matrix();document.getElementById('field').value=fi;document.getElementById('group').value=gi;document.getElementById('field-title').textContent=`${f.code} 的参考是 ★ ${D.groups[fi].code}；实际轴角 ${fmt(f.angle)}°。本列的所有家具组都可支持这个方向。`;document.getElementById('plan').innerHTML=plan(fi);document.getElementById('field-id').textContent=f.id;document.getElementById('metrics').innerHTML=`<div class="metric">其余 ${p.expected_count} 组平均支持（排除自身）<strong>${fmt(p.value)}</strong>${p.valid_count}/${p.expected_count} 个有效；coverage ${fmt(p.coverage)}</div><div class="metric">当前格 ${g.code} → ${f.code}<strong>${fmt(c.axis_field_support,6)}</strong>${c.self_reference?'★ 自身参考，排除于 non-self 均值':'非自身参考'}；${c.status}</div>`;document.getElementById('direction').textContent=`含参考自身 ${q.expected_count} 组的只读软方向：${fmt(q.direction)}°；一致性 ${fmt(q.direction_coherence)}；有效 ${q.valid_count}/${q.expected_count}；self权重占比 ${fmt(q.self_weight_fraction)}；状态 ${q.direction_status}。它不是上方参考方向。`;document.getElementById('group-title').textContent=`${g.code} | ${g.id} | 自身轴 ${fmt(c.group_axis_angle)}°；清晰度 ${fmt(c.group_clarity)}。`;
document.getElementById('column').innerHTML='<tr><th>组</th><th>支持 S(g,k)</th><th>身份 / 状态</th></tr>'+D.groups.map((a,i)=>{const v=f.cells[i];return `<tr class="${i===gi?'picked':''}"><td><button onclick="choose(fi,${i})">${a.code}</button></td><td>${fmt(v.axis_field_support,6)}</td><td>${v.self_reference?'★ anchor / ':''}${esc(v.status)}</td></tr>`}).join('');document.getElementById('row').innerHTML='<tr><th>参考场 / anchor</th><th>支持 0 → 1</th><th>读数</th></tr>'+D.fields.map((a,j)=>{const v=a.cells[gi].axis_field_support;return `<tr class="${j===fi?'picked':''}"><td><button onclick="choose(${j},gi)">${a.code} / ${D.groups[j].code}${a.cells[gi].self_reference?' ★':''}</button><br><small>${fmt(a.angle)}°</small></td><td><div class="bar"><i style="width:${v===null?0:100*v}%"></i></div></td><td>${fmt(v,6)}</td></tr>`}).join('');document.getElementById('cell').textContent=JSON.stringify(c,null,2)}
D.fields.forEach((f,j)=>document.getElementById('field').add(new Option(`${f.code} · anchor ${D.groups[j].code} · ${fmt(f.angle)}°`,j)));D.groups.forEach((g,i)=>document.getElementById('group').add(new Option(`${g.code} · ${g.id}`,i)));document.getElementById('field').onchange=e=>choose(Number(e.target.value),gi);document.getElementById('group').onchange=e=>choose(fi,Number(e.target.value));document.getElementById('samples').innerHTML=D.representatives.map((j,n)=>`<div><button onclick="choose(${j},gi)"><b>${['角度最小','方向对照','角度最大'][n]}：${D.fields[j].code} / ${D.groups[j].code}</b><br>${fmt(D.fields[j].angle)}° · 点击查看完整平面</button>${plan(j,false)}</div>`).join('');document.getElementById('source').textContent=`IFC: ${D.source.path}\nSHA-256: ${D.source.sha256}\nreplay: ${D.source_replay}\nplane: ${JSON.stringify(D.plane)}`;render();
</script></html>'''


HIERARCHY_SECTION = r"""<section class="card" id="hierarchy"><h2>⑤ Direction families: complete indexed views</h2><p>Each family is a contiguous source-axis direction window with its own [birth, death) lifespan. Select any family to show all retained groups on the same IFC analysis plane; geometry is shared, and the family support vector is read from the package output.</p><label>Family <select id="family-select"></select></label><p id="family-title"></p><div class="plan" id="family-plan"></div><div class="metrics" id="family-metrics"></div><details><summary>Source axes, exact lifespan and family profile</summary><div id="family-axes" class="small"></div></details><details><summary>Parent residuals</summary><div class="scroll" id="family-residuals"></div></details><p class="small">Gray NA cells remain unknown. Family rows describe max support over their actual leaf axes; no hard spatial boundary, membership, winner, real-world cluster validity, or live UI behavior is asserted.</p><p><a href="family_matrix.svg">Complete family-by-group matrix</a></p></section>"""


HIERARCHY_SCRIPT = r"""
/** Select an indexed family and preserve the selected scope group in its link. */
function chooseFamily(index,group=gi){hi=index;if(Number.isInteger(group))gi=group;const f=D.hierarchy.families[hi];history.replaceState(null,'',`#family=${encodeURIComponent(f.id)}&group=${encodeURIComponent(D.groups[gi].id)}`);renderHierarchy()}
/** Draw the chosen family vector over the existing plane-local member polygons. */
function familyPlan(f){const cells=new Map(f.cells.map(c=>[c.group_id,c]));const anchors=new Set(f.anchor_group_ids);let out='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 710" role="img" aria-label="Direction family on retained IFC plan"><rect width="1200" height="710" fill="white"/>';D.groups.forEach((g,i)=>{const c=cells.get(g.id),anchor=anchors.has(g.id),value=c.value;out+=`<g data-group="${esc(g.id)}" data-support="${value}" data-status="${esc(c.status)}" tabindex="0" role="button" aria-label="${g.code} ${fmt(value)} ${esc(c.status)}" onclick="chooseFamily(hi,${i})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();chooseFamily(hi,${i})}"><title>${esc(g.id)} | value=${value} | status=${esc(c.status)} | lower=${c.lower} upper=${c.upper}</title>`;g.paths.forEach(p=>out+=`<path d="${p}" fill="${color(value)}" stroke="${anchor?'#b34900':i===gi?'#172f46':'#526879'}" stroke-width="${anchor?4:i===gi?2:.65}"/>`);out+=`<text x="${g.label_point[0]}" y="${g.label_point[1]-8}" text-anchor="middle" font-size="14" font-weight="700" fill="#183047" stroke="white" stroke-width="4" paint-order="stroke">${anchor?'★ ':''}${g.code}</text></g>`});return out+'</svg>'}
/** Show exact events, included source axes, profiles, direction, and residuals. */
function renderHierarchy(){const f=D.hierarchy.families[hi];document.getElementById('family-select').value=hi;document.getElementById('family-title').textContent=`${f.code} | ${f.anchor_group_ids.length} anchor(s) | birth ${fmt(f.birth,6)}°; death ${fmt(f.death,6)}°; interval [birth, death).` ;document.getElementById('family-plan').innerHTML=familyPlan(f);const p=f.profile.domains.full_scope,n=f.profile.domains.non_anchor,q=f.direction;document.getElementById('family-metrics').innerHTML=`<div class="metric">Full-scope support<strong>${fmt(p.known_mean,6)}</strong>${p.known_count}/${p.expected_count} known; coverage ${fmt(p.coverage)}; n_eff ${fmt(p.n_eff)}</div><div class="metric">Non-anchor profile<strong>${fmt(n.known_mean,6)}</strong>${n.known_count}/${n.expected_count} known; coverage ${fmt(n.coverage)}; support mass ${fmt(n.support_mass)}</div><div class="metric">Read-only family direction<strong>${fmt(q.direction,6)}°</strong>${esc(q.direction_status)}; Q=(${fmt(q.Q[0],6)}, ${fmt(q.Q[1],6)}); coherence ${fmt(q.coherence)}</div><div class="metric">Window persistence<strong>${fmt(f.scale_persistence,6)}</strong>${f.leaf_field_ids.length} leaf fields; exact events ${f.birth_exact[0]}/${f.birth_exact[1]} → ${f.death_exact[0]}/${f.death_exact[1]}</div>`;const axes=f.direction_classes.map(c=>{const refs=c.leaf_field_ids.map(id=>{const leaf=D.fields.find(x=>x.id===id);return `${leaf.code} ${D.groups.find(g=>g.id===leaf.anchor).code} ${fmt(leaf.angle,6)}°`}).join('; ');return `<li>class ${c.class_index} θ=${fmt(c.theta,6)}° exact=${c.theta_exact[0]}/${c.theta_exact[1]}: ${esc(refs)}</li>`}).join('');document.getElementById('family-axes').innerHTML=`<p>Family ID: <span class="id">${esc(f.id)}</span></p><p>Anchor groups: ${esc(f.anchor_group_ids.join(', '))}</p><p>Included source axes:</p><ul>${axes}</ul>`;document.getElementById('family-residuals').innerHTML=f.residuals.length?'<table class="detail"><tr><th>Child → parent</th><th>Coverage</th><th>Known / expected</th><th>Scope rows</th></tr>'+f.residuals.map(e=>`<tr><td><span class="id">${esc(e.child_family_id)} → ${esc(e.parent_family_id)}</span></td><td>${fmt(e.coverage)}</td><td>${e.known_count}/${e.expected_count}</td><td>${e.rows.map(r=>`${esc(r.group_id)}: ${fmt(r.value,6)} [${fmt(r.lower,6)}, ${fmt(r.upper,6)}] ${esc(r.status)}`).join('<br>')}</td></tr>`).join('')+'</table>':'<p>No residual edges for this family.</p>'}
/** Resolve stable manifest fragments so every leaf and family has an address. */
function routeIndexedView(){const route=new URLSearchParams(location.hash.slice(1));if(route.has('family')){const index=D.hierarchy.families.findIndex(f=>f.id===route.get('family'));if(index>=0){const group=route.get('group'),giNext=group?D.groups.findIndex(g=>g.id===group):gi;chooseFamily(index,giNext>=0?giNext:gi);return}}if(route.has('leaf')){const index=D.fields.findIndex(f=>f.id===route.get('leaf'));if(index>=0){const group=route.get('group'),groupIndex=group?D.groups.findIndex(g=>g.id===group):gi;choose(index,groupIndex>=0?groupIndex:gi)}}}
let hi=0;D.hierarchy.families.forEach(f=>document.getElementById('family-select').add(new Option(`${f.code} · ${f.anchor_group_ids.length} anchors · ${fmt(f.birth,3)}–${fmt(f.death,3)}°`,f.index)));document.getElementById('family-select').onchange=e=>chooseFamily(Number(e.target.value));window.addEventListener('hashchange',routeIndexedView);renderHierarchy();routeIndexedView();
"""


def run(replay: Path, output: Path) -> Path:
    """Write a self-contained preview and source-addressed presentation manifest."""
    before = {name: _sha(replay / name) for name in INPUTS}
    data = load_preview(replay)
    hierarchy_mode = "hierarchy" in data
    hierarchy_before = {name: _sha(replay / name) for name in HIERARCHY_INPUTS} if hierarchy_mode else {}
    run_dir = output / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    payload = json.dumps(_presentation_data(data), ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    page = PAGE.replace("__DATA__", payload).replace("__HIERARCHY_SECTION__", HIERARCHY_SECTION if hierarchy_mode else "")
    if hierarchy_mode:
        page = page.replace("</script></html>", HIERARCHY_SCRIPT + "</script></html>")
    for name, token in (("field_matrix.json", "__MATRIX_URI__"), ("field_profiles.json", "__PROFILES_URI__"), ("field_directions.json", "__DIRECTIONS_URI__")):
        page = page.replace(token, (replay / name).resolve().as_uri())
    (run_dir / "index.html").write_text(page, encoding="utf-8")
    (run_dir / "matrix.svg").write_text(matrix_svg(data), encoding="utf-8")
    if hierarchy_mode:
        (run_dir / "family_matrix.svg").write_text(family_matrix_svg(data), encoding="utf-8")
    samples = []
    for position, field_index in enumerate(data["representatives"]):
        name = f"representative_{position+1}.svg"
        (run_dir / name).write_text(plan_svg(data, field_index), encoding="utf-8")
        samples.append({"path": name, "field_id": data["fields"][field_index]["id"], "selection": ("minimum source axis angle", "existing reference maximally separated from both extremes (axial angle)", "maximum source axis angle")[position]})
    family_samples = []
    if hierarchy_mode:
        for selection, family_index in _family_representatives(data).items():
            family = data["hierarchy"]["families"][family_index]
            name = f"family_representative_{selection}.svg"
            (run_dir / name).write_text(plan_svg(data, family_index, family=True), encoding="utf-8")
            family_samples.append({"path": name, "png": str(Path(name).with_suffix(".png")), "family_id": family["id"], "anchor_group_ids": family["anchor_group_ids"], "selection": selection})
    for path in run_dir.glob("*.svg"):
        ET.parse(path)
    # Installed reportlab/svglib provide inspectable rasters without a browser.
    from reportlab.graphics import renderPM
    from svglib.svglib import svg2rlg

    for path in run_dir.glob("*.svg"):
        if path.name == "family_matrix.svg":
            continue
        renderPM.drawToFile(svg2rlg(str(path)), str(path.with_suffix(".png")), fmt="PNG")
    if before != {name: _sha(replay / name) for name in INPUTS}:
        raise RuntimeError("a retained source changed during preview rendering")
    if hierarchy_mode and hierarchy_before != {name: _sha(replay / name) for name in HIERARCHY_INPUTS}:
        raise RuntimeError("a retained hierarchy source changed during preview rendering")
    manifest = {"schema": "group-axis-potential-read-only-preview/v1", "source": data["source"], "analysis_plane": data["plane"], "analysis_frame": data["analysis_frame"], "source_replay": str(replay.resolve()), "inputs": [{"path": str((replay / name).resolve()), "sha256": digest} for name, digest in before.items()], "group_map": [{"code": group["code"], "group_id": group["id"]} for group in data["groups"]], "field_map": [{"code": field["code"], "field_id": field["id"], "anchor_group_id": field["anchor"], "angle": field["angle"]} for field in data["fields"]], "cell_count": sum(len(field["cells"]) for field in data["fields"]), "representatives": samples, "presentation_only": True, "support_recomputed": False, "ifc_extraction_rerun": False, "synthetic_input": False, "palette": {"range": [0, 1], "meaning": "existing axis_field_support only; not new evidence", "unknown": "gray / NA", "anchor": "orange outline and star; support fill unchanged"}, "artifacts": [{"path": str(path.resolve()), "sha256": _sha(path)} for path in sorted(run_dir.iterdir()) if path.is_file()]}
    if hierarchy_mode:
        manifest["palette"]["meaning"] = "existing axis_field_support / family support only; not new evidence"
        manifest.update({
            "hierarchy": True,
            "family_representatives": family_samples,
            "family_count": len(data["hierarchy"]["families"]),
            "family_cell_count": sum(len(family["cells"]) for family in data["hierarchy"]["families"]),
            "leaf_map": [{"code": field["code"], "field_id": field["id"], "href": f"index.html#leaf={field['id']}"} for field in data["fields"]],
            "family_map": [{"code": family["code"], "family_id": family["id"], "family_index": family["index"], "view_id": family["view_id"], "href": family["view_ref"]} for family in data["hierarchy"]["families"]],
            "target_index": [{**item, "href": item["view_ref"]} for item in data["hierarchy"]["target_index"]],
            "hierarchy_inputs": [{"path": str((replay / name).resolve()), "sha256": digest} for name, digest in hierarchy_before.items()],
        })
    family_note = f"已提供全部 {len(data['hierarchy']['families'])} 个 FieldFamily 的索引平面与 `family_matrix.svg`；它们是可重叠方向族，不是硬分组或空间势边界。另有 {len(family_samples)} 张 `family_representative_*.svg` / PNG 快照，展示可用代表：最小非单例中 persistence 最大的族，以及按 anchor 数排序的首对相交且互不包含的 maximal top families；不存在的代表会跳过。每张保留全部 37 组、anchor 标签与支持读数，复用同一真实平面和固定 0–1 色标。" if hierarchy_mode else "没有硬分组、空间势边界、FieldFamily 或 merge。"
    (run_dir / "README.md").write_text(f"""# 真实 IFC source-axis 支持预览

打开 `index.html`。矩阵保留全部 37×37 读数；点击格后，联动真实 IFC 平面、完整列明细和同一组的跨场条形明细。F/G 短码仅用于显示，原始身份见 manifest。

| 表达 | 能解释什么 | 限制 |
| --- | --- | --- |
| 单场平面 + 图例 + 数值表 | 谁是参考、组在哪里、每组支持多少 | 单独看无法比较其余场 |
| 完整矩阵热图 | 一行可同时支持多列，完整重叠一目了然 | 需要平面补充位置 |
| 三个代表场小图 | 相同平面上的空间对照 | 展示采样不代表只有三个场 |

推荐矩阵 + 联动平面，单行条形明细帮助读懂重叠。色彩只显示现有值，固定 0–1，不归一、不阈值、不 winner。橙色外框/★ 只标 anchor，不替换支持填色。三个代表场从现有 anchor 中选最小角、最大角和对这两个方向最分离的一个已有参考，完整 37 场仍保留。

non-self 均值排除 self，soft direction 包含 self，后者只读且不更新参考。读数不是概率或已确定的归属。{family_note}此处只复用 retained description 中的真实家具组投影，不展示未提供的房间边界。未知与已知零分别显示；本次真实数据只有 computed 状态，未把未出现状态伪造成 IFC 结果。

输入路径、SHA-256、analysis plane、完整 group/field 映射和输出地址见 `manifest.json`。`matrix.svg` 和三个 representative SVG 可独立查看；HTML 无外部脚本依赖。页面数值只是格式化显示，点格可查看保留原始精度的 JSON。
""", encoding="utf-8")
    manifest["artifacts"].append({"path": str((run_dir / "README.md").resolve()), "sha256": _sha(run_dir / "README.md")})
    _write_json(run_dir / "manifest.json", manifest)
    return run_dir


def main() -> None:
    """Render the specified replay into a new output-only directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, default=REPLAY)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps({"status": "pass", "output": str(run(args.replay.resolve(), args.output_root.resolve()))}))


if __name__ == "__main__":
    main()
