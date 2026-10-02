"""Run the D6 Task 3d inferred-group design experiment without production imports."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

EPS = 1e-9


def _bounds(box: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return xmin, xmax, ymin, ymax for an axis-aligned fixture box."""
    cx, cy = box["center"]
    sx, sy = box["size"]
    return cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2


def _z_bounds(box: dict[str, Any]) -> tuple[float, float]:
    """Return z-min and z-max for a fixture cuboid."""
    return tuple(box["z"])  # type: ignore[return-value]


def _area(box: dict[str, Any]) -> float:
    """Return the positive plan area of a fixture rectangle."""
    return box["size"][0] * box["size"][1]


def _rect_gap(first: dict[str, Any], second: dict[str, Any]) -> tuple[float, bool, float]:
    """Return 2D boundary gap, overlap flag, and intersection area."""
    ax0, ax1, ay0, ay1 = _bounds(first)
    bx0, bx1, by0, by1 = _bounds(second)
    dx = max(ax0 - bx1, bx0 - ax1, 0.0)
    dy = max(ay0 - by1, by0 - ay1, 0.0)
    overlap_area = max(0.0, min(ax1, bx1) - max(ax0, bx0)) * max(0.0, min(ay1, by1) - max(ay0, by0))
    return math.hypot(dx, dy), overlap_area > EPS, overlap_area


def _box_clearance(first: dict[str, Any], second: dict[str, Any]) -> tuple[float, bool, float]:
    """Return 3D AABB clearance, volume-overlap flag, and overlap volume."""
    gap_2d, overlap_2d, area = _rect_gap(first, second)
    az0, az1 = _z_bounds(first)
    bz0, bz1 = _z_bounds(second)
    dz = max(az0 - bz1, bz0 - az1, 0.0)
    z_overlap = max(0.0, min(az1, bz1) - max(az0, bz0))
    volume = area * z_overlap
    return math.sqrt(gap_2d * gap_2d + dz * dz), volume > EPS, volume


def _group_geometry(group: dict[str, Any]) -> dict[str, Any]:
    """Summarize status, additive support, and usable member records."""
    usable = [member for member in group["members"] if member["status"] == "computed"]
    excluded = {member["id"]: member.get("reason", member["status"]) for member in group["members"] if member["status"] != "computed"}
    if any(member["status"] == "invalid" for member in group["members"]):
        status = "invalid"
    elif not usable:
        status = "not_available"
    else:
        status = "computed"
    support = sum(_area(member["box"]) for member in usable)
    if support:
        center = [sum(_area(m["box"]) * m["box"]["center"][axis] for m in usable) / support for axis in (0, 1)]
    else:
        center = None
    return {
        "id": group["id"],
        "status": status,
        "completeness": "partial" if usable and excluded and status == "computed" else ("complete" if usable else "not_applicable"),
        "support_area": support if usable else None,
        "center": center,
        "excluded_member_reasons": excluded,
        "members": usable,
    }


def _wall_status(first: list[float], second: list[float], walls: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify a fixture wall as pass, opening, or blocked using center-line crossing."""
    x1, y1 = first
    x2, y2 = second
    for wall in walls:
        wx = wall["x"]
        if min(x1, x2) - EPS <= wx <= max(x1, x2) + EPS:
            ratio = 0.0 if abs(x2 - x1) <= EPS else (wx - x1) / (x2 - x1)
            y = y1 + ratio * (y2 - y1)
            if wall["y_range"][0] - EPS <= y <= wall["y_range"][1] + EPS:
                return {"status": "opening" if wall["opening"] else "blocked", "wall_id": wall["id"]}
    return {"status": "clear", "wall_id": None}


def _relation(first: dict[str, Any], second: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    """Compute independent 2D, 3D, Z, barrier, and dependency channels."""
    shared = sorted({m["id"] for m in first["members"]} & {m["id"] for m in second["members"]})
    if first["status"] == "invalid" or second["status"] == "invalid":
        return {"edge": False, "formal_membership_edge": False, "status": "diagnostic_invalid", "reason": "invalid_group", "shared_members": shared}
    if not first["members"] or not second["members"]:
        return {"edge": False, "formal_membership_edge": False, "status": "not_available", "reason": "no_usable_physical_support", "shared_members": shared}
    pairs = list(itertools.product(first["members"], second["members"]))
    pair_values = []
    for left, right in pairs:
        gap, overlap, overlap_area = _rect_gap(left["box"], right["box"])
        clearance, overlap_3d, overlap_volume = _box_clearance(left["box"], right["box"])
        lz0, lz1 = _z_bounds(left["box"])
        rz0, rz1 = _z_bounds(right["box"])
        pair_values.append({
            "members": [left["id"], right["id"]],
            "gap_2d": gap,
            "overlap_2d": overlap,
            "overlap_area": overlap_area,
            "clearance_3d": clearance,
            "overlap_3d": overlap_3d,
            "z_compatible": not (lz1 <= rz0 + EPS or rz1 <= lz0 + EPS),
        })
    closest_2d = min(pair_values, key=lambda value: value["gap_2d"])
    closest_3d = min(pair_values, key=lambda value: value["clearance_3d"])
    support_sum = first["support_area"] + second["support_area"]
    normalized = closest_2d["gap_2d"] / math.sqrt(support_sum) if support_sum > EPS else None
    barrier = _wall_status(first["center"], second["center"], fixture.get("walls", []))
    thresholds = fixture.get("thresholds", {})
    z_compatible = any(value["z_compatible"] for value in pair_values)
    edge = (
        first["status"] == "computed" and second["status"] == "computed"
        and normalized is not None and normalized <= thresholds.get("normalized_gap", math.inf) + EPS
        and closest_3d["clearance_3d"] <= thresholds.get("clearance_3d", math.inf) + EPS
        and z_compatible and barrier["status"] != "blocked" and not shared
    )
    return {
        "edge": edge,
        "status": "partial" if first["completeness"] == "partial" or second["completeness"] == "partial" else "computed",
        "raw_gap_2d": closest_2d["gap_2d"],
        "normalized_gap_2d": normalized,
        "overlap_2d": closest_2d["overlap_2d"],
        "overlap_area_2d": max(value["overlap_area"] for value in pair_values),
        "clearance_3d": closest_3d["clearance_3d"],
        "overlap_3d": any(value["overlap_3d"] for value in pair_values),
        "z_compatible": z_compatible,
        "z_channel_status": "computed",
        "barrier": barrier,
        "shared_members": shared,
        "shared_member_dependency": bool(shared),
        "formal_membership_edge": edge and not shared and first["status"] == second["status"] == "computed" and first["completeness"] == second["completeness"] == "complete",
        "reason": "shared_member_dependency" if shared else ("barrier_blocked" if barrier["status"] == "blocked" else None),
    }


def _edges(groups: list[dict[str, Any]], fixture: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Return formal relation edges and all pair records."""
    reps = [_group_geometry(group) for group in groups]
    relations = {}
    edge_list = []
    for left, right in itertools.combinations(reps, 2):
        key = "--".join(sorted((left["id"], right["id"])))
        relation = _relation(left, right, fixture)
        relations[key] = relation
        if relation["formal_membership_edge"]:
            edge_list.append(key)
    return sorted(edge_list), relations


def _connected_components(ids: list[str], edges: list[str]) -> list[list[str]]:
    """Return deterministic connected components for an undirected edge list."""
    adjacency = {item: set() for item in ids}
    for edge in edges:
        left, right = edge.split("--")
        adjacency[left].add(right)
        adjacency[right].add(left)
    components = []
    unseen = set(ids)
    while unseen:
        start = min(unseen)
        stack = [start]
        unseen.remove(start)
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(adjacency[node], reverse=True):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda component: component[0])


def _maximal_cliques(ids: list[str], edges: list[str]) -> list[list[str]]:
    """Return maximal cliques, the complete-link candidates for this finite fixture."""
    adjacency = {item: set() for item in ids}
    for edge in edges:
        left, right = edge.split("--")
        adjacency[left].add(right)
        adjacency[right].add(left)
    cliques = []
    for size in range(2, len(ids) + 1):
        for candidate in itertools.combinations(ids, size):
            if all(right in adjacency[left] for left, right in itertools.combinations(candidate, 2)):
                cliques.append(list(candidate))
    return [candidate for candidate in cliques if not any(set(candidate) < set(other) for other in cliques)]


def _max_span_candidates(ids: list[str], relations: dict[str, dict[str, Any]], threshold: float) -> list[list[str]]:
    """Return maximal groups whose every pair stays within a raw-gap span ceiling."""
    candidates = []
    for size in range(2, len(ids) + 1):
        for candidate in itertools.combinations(ids, size):
            pair_keys = ["--".join(sorted(pair)) for pair in itertools.combinations(candidate, 2)]
            if all(relations[key].get("raw_gap_2d", math.inf) <= threshold + EPS for key in pair_keys):
                candidates.append(list(candidate))
    return [candidate for candidate in candidates if not any(set(candidate) < set(other) for other in candidates)]


def _partition_options(ids: list[str], cliques: list[list[str]]) -> list[dict[str, Any]]:
    """Enumerate small hard partitions and retain tied maximum-coverage choices."""
    options = []
    for assignment in itertools.product(range(len(cliques) + 1), repeat=len(ids)):
        blocks = []
        valid = True
        for index, clique in enumerate(cliques):
            members = [ids[position] for position, value in enumerate(assignment) if value == index]
            if members and not set(members).issubset(clique):
                valid = False
            if members:
                blocks.append(sorted(members))
        if not valid:
            continue
        unassigned = sorted(ids[position] for position, value in enumerate(assignment) if value == len(cliques))
        if not blocks:
            continue
        coverage = sum(len(block) for block in blocks)
        options.append({"blocks": sorted(blocks), "unassigned": unassigned, "coverage": coverage})
    unique = {(tuple(tuple(block) for block in item["blocks"]), tuple(item["unassigned"])): item for item in options}
    best = max(item["coverage"] for item in unique.values())
    return sorted((item for item in unique.values() if item["coverage"] == best), key=lambda item: (item["blocks"], item["unassigned"]))


def _representative_overlap(group: dict[str, Any]) -> dict[str, Any]:
    """Return additive area, pairwise overlap, and exact rectangle union for one group."""
    members = [member for member in group["members"] if member["status"] == "computed"]
    additive = sum(_area(member["box"]) for member in members)
    pairwise = sum(_rect_gap(left["box"], right["box"])[2] for left, right in itertools.combinations(members, 2))
    xs = sorted({coord for member in members for coord in _bounds(member["box"])[0:2]})
    union = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        if x1 <= x0 + EPS:
            continue
        intervals = sorted((_bounds(member["box"])[2], _bounds(member["box"])[3]) for member in members if _bounds(member["box"])[0] < x1 - EPS and _bounds(member["box"])[1] > x0 + EPS)
        covered = 0.0
        if intervals:
            low, high = intervals[0]
            for next_low, next_high in intervals[1:]:
                if next_low <= high + EPS:
                    high = max(high, next_high)
                else:
                    covered += high - low
                    low, high = next_low, next_high
            covered += high - low
        union += (x1 - x0) * covered
    return {"additive_support_area": additive, "pairwise_overlap_area": pairwise, "union_area": union, "union_area_status": "diagnostic_only"}


def _equivalent_2d(manifest: dict[str, Any]) -> dict[str, Any]:
    """Compare canonical 2D facts while excluding SVG-only unsupported channels."""
    ifc = manifest["equivalent_sources"]["ifc_primary"]["canonical_facts"]
    svg = manifest["equivalent_sources"]["svg_equivalent_2d"]["canonical_facts"]
    comparable = {key: value for key, value in ifc.items() if key in svg}
    mismatches = {key: {"ifc": value, "svg": svg.get(key)} for key, value in comparable.items() if svg.get(key) != value}
    return {"comparable_fact_keys": sorted(comparable), "mismatches": mismatches, "status": "pass" if not mismatches else "fail", "ifc_only_channels": sorted(set(ifc) - set(svg))}


def _render_svg(path: Path, fixture: dict[str, Any], edges: list[str], components: list[list[str]], cliques: list[list[str]]) -> None:
    """Write a compact two-panel geometry diagnostic for the bridge fixture."""
    positions = {group["id"]: group["members"][0]["box"]["center"] for group in fixture["groups"]}
    colors = {"A": "#1f77b4", "B": "#2ca02c", "C": "#d62728", "D": "#9467bd"}
    def panel(x_offset: float, title: str, links: list[tuple[str, str]]) -> list[str]:
        lines = [f'<text x="{x_offset + 20}" y="24" font-size="14" font-family="sans-serif">{title}</text>']
        for edge_left, edge_right in links:
            x1, y1 = positions[edge_left]
            x2, y2 = positions[edge_right]
            lines.append(f'<line x1="{x_offset + 80 + x1 * 45:.1f}" y1="{130 - y1 * 45:.1f}" x2="{x_offset + 80 + x2 * 45:.1f}" y2="{130 - y2 * 45:.1f}" stroke="#555" stroke-width="3"/>')
        for group_id, (x, y) in positions.items():
            lines.append(f'<circle cx="{x_offset + 80 + x * 45:.1f}" cy="{130 - y * 45:.1f}" r="16" fill="{colors.get(group_id, "#777")}"/>')
            lines.append(f'<text x="{x_offset + 74 + x * 45:.1f}" y="{136 - y * 45:.1f}" fill="white" font-size="12" font-family="sans-serif">{group_id}</text>')
        return lines
    cc_links = [(left, right) for left, right in (edge.split("--") for edge in edges)]
    clique_links = [(left, right) for clique in cliques for left, right in itertools.combinations(clique, 2)]
    content = ['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="180" viewBox="0 0 920 180">', '<rect width="100%" height="100%" fill="white"/>']
    content += panel(0, "connected components baseline", cc_links)
    content += panel(380, "complete-link maximal cliques", clique_links)
    content.append('</svg>')
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _render_barrier_svg(path: Path, fixture: dict[str, Any]) -> None:
    """Write a top-down diagnostic contrasting level stacking and wall opening states."""
    groups = {group["id"]: group["members"][0]["box"] for group in fixture["groups"]}
    rows = [("FLOOR_A / FLOOR_B", "FLOOR_A", "FLOOR_B", "closed wall → blocked"),
            ("FLOOR_A / STACKED", "FLOOR_A", "STACKED", "same XY → Z incompatible"),
            ("WALL_A / WALL_B", "WALL_A", "WALL_B", "opening → pass")]
    content = ['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="240" viewBox="0 0 720 240">', '<rect width="100%" height="100%" fill="white"/>']
    for row, (title, left_id, right_id, label) in enumerate(rows):
        y = 38 + row * 68
        left = groups[left_id]["center"]
        right = groups[right_id]["center"]
        content.append(f'<text x="12" y="{y}" font-size="12" font-family="sans-serif">{title}</text>')
        content.append(f'<line x1="190" y1="{y - 4}" x2="510" y2="{y - 4}" stroke="#555" stroke-width="2"/>')
        if "WALL" in title:
            content.append(f'<line x1="350" y1="{y - 22}" x2="350" y2="{y + 14}" stroke="#2ca02c" stroke-width="5"/>')
            content.append(f'<text x="330" y="{y + 29}" font-size="10" font-family="sans-serif">opening</text>')
        elif "FLOOR_A / FLOOR_B" in title:
            content.append(f'<line x1="350" y1="{y - 22}" x2="350" y2="{y + 14}" stroke="#d62728" stroke-width="5"/>')
            content.append(f'<text x="325" y="{y + 29}" font-size="10" font-family="sans-serif">closed</text>')
        else:
            content.append(f'<line x1="350" y1="{y - 22}" x2="350" y2="{y + 14}" stroke="#888" stroke-width="2" stroke-dasharray="4 4"/>')
        content.append(f'<circle cx="230" cy="{y - 4}" r="12" fill="#1f77b4"/><circle cx="470" cy="{y - 4}" r="12" fill="#ff7f0e"/>')
        content.append(f'<text x="218" y="{y}" fill="white" font-size="9" font-family="sans-serif">A</text><text x="458" y="{y}" fill="white" font-size="9" font-family="sans-serif">B</text>')
        content.append(f'<text x="530" y="{y}" font-size="11" font-family="sans-serif">{label}</text>')
    content.append('</svg>')
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _run(manifest: dict[str, Any], visual_dir: Path | None) -> dict[str, Any]:
    """Run all design experiments and return a reviewable evidence record."""
    fixtures = {fixture["id"]: fixture for fixture in manifest["fixtures"]}
    bridge = fixtures["bridge_chain"]
    bridge_edges, bridge_relations = _edges(bridge["groups"], bridge)
    bridge_ids = [group["id"] for group in bridge["groups"]]
    bridge_components = _connected_components(bridge_ids, bridge_edges)
    bridge_cliques = _maximal_cliques(bridge_ids, bridge_edges)
    bridge_max_span = _max_span_candidates(bridge_ids, bridge_relations, bridge["thresholds"]["max_span"])
    bridge_partitions = _partition_options(bridge_ids, bridge_cliques)
    long_edges, _ = _edges(fixtures["long_row"]["groups"], fixtures["long_row"])
    long_ids = [g["id"] for g in fixtures["long_row"]["groups"]]
    _, long_relations = _edges(fixtures["long_row"]["groups"], fixtures["long_row"])
    unequal_edges, unequal_relations = _edges(fixtures["unequal_size"]["groups"], fixtures["unequal_size"])
    level_edges, level_relations = _edges(fixtures["levels_and_barriers"]["groups"], fixtures["levels_and_barriers"])
    shared_edges, shared_relations = _edges(fixtures["shared_member"]["groups"], fixtures["shared_member"])
    status_edges, status_relations = _edges(fixtures["status_mix"]["groups"], fixtures["status_mix"])
    overlap = _representative_overlap(fixtures["overlap_union"]["groups"][0])
    trend_edges = {}
    for variant in fixtures["trend_independence"]["trend_variants"]:
        trend_edges[variant], _ = _edges(fixtures["trend_independence"]["groups"], fixtures["trend_independence"])
    parity = _equivalent_2d(manifest)
    results = {
        "candidate_comparison": {
            "bridge_chain": {"edges": bridge_edges, "relations": bridge_relations, "connected_components": bridge_components, "complete_link_maximal_cliques": bridge_cliques, "max_span_candidates": bridge_max_span, "hard_partition_options": bridge_partitions, "candidate_output_diagnostic": {"hard_partition_status": "ambiguous", "overlapping_candidates": bridge_cliques, "unassigned": ["D"]}},
            "long_row": {"edges": long_edges, "connected_components": _connected_components(long_ids, long_edges), "complete_link_maximal_cliques": _maximal_cliques(long_ids, long_edges), "max_span_candidates": _max_span_candidates(long_ids, long_relations, fixtures["long_row"]["thresholds"]["max_span"])},
        },
        "channels": {"unequal_size": {"edges": unequal_edges, "relations": unequal_relations}, "levels_and_barriers": {"edges": level_edges, "relations": level_relations}},
        "shared_member": {"edges": shared_edges, "relations": shared_relations},
        "status_mix": {"edges": status_edges, "relations": status_relations, "group_summaries": [_group_geometry(group) for group in fixtures["status_mix"]["groups"]]},
        "representative_geometry": overlap,
        "trend_independence": {"edges_by_variant": trend_edges, "same_edge_set": len({tuple(value) for value in trend_edges.values()}) == 1},
        "ifc_svg_2d_parity": parity,
    }
    assert bridge_components == [["A", "B", "C"], ["D"]]
    assert bridge_cliques == [["A", "B"], ["B", "C"]]
    assert bridge_max_span == [["A", "B"], ["B", "C"]]
    assert len(bridge_partitions) == 2 and all(item["coverage"] == 3 for item in bridge_partitions)
    assert long_edges == ["L1--L2", "L2--L3", "L3--L4"]
    assert unequal_edges == ["BIG--SMALL"]
    assert unequal_relations["BIG--SMALL"]["raw_gap_2d"] > 0.6 and unequal_relations["BIG--SMALL"]["normalized_gap_2d"] < 0.6
    assert level_relations["FLOOR_A--FLOOR_B"]["barrier"]["status"] == "blocked"
    assert level_relations["FLOOR_A--STACKED"]["z_compatible"] is False
    assert shared_edges == [] and shared_relations["G1--G2"]["shared_member_dependency"] is True
    assert status_relations["PARTIAL--VALID"]["status"] == "partial" and status_relations["PARTIAL--VALID"]["formal_membership_edge"] is False
    assert status_relations["INVALID--VALID"]["status"] == "diagnostic_invalid"
    assert status_relations["MISSING--VALID"]["status"] == "not_available"
    assert results["status_mix"]["group_summaries"][2]["status"] == "not_available"
    assert overlap == {"additive_support_area": 8.0, "pairwise_overlap_area": 2.0, "union_area": 6.0, "union_area_status": "diagnostic_only"}
    assert results["trend_independence"]["same_edge_set"]
    assert parity["status"] == "pass" and "z_intervals" in parity["ifc_only_channels"]
    if visual_dir:
        visual_dir.mkdir(parents=True, exist_ok=True)
        _render_svg(visual_dir / "d6-inferred-group-candidates.svg", bridge, bridge_edges, bridge_components, bridge_cliques)
        _render_barrier_svg(visual_dir / "d6-inferred-group-channels.svg", fixtures["levels_and_barriers"])
    return results


def main() -> None:
    """Load fixtures, execute assertions, and write design-only evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--visual-dir", type=Path)
    args = parser.parse_args()
    raw = args.fixtures.read_bytes()
    manifest = json.loads(raw)
    evidence = {
        "schema": "d6-inferred-group-design-experiment/v1",
        "design_only": True,
        "fixture_manifest": str(args.fixtures).replace("\\", "/"),
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "analysis_frame": manifest["analysis_frame"],
        "tolerance": manifest["tolerance"],
        "results": _run(manifest, args.visual_dir),
        "limitations": [
            "Synthetic boxes are computational fixtures, not human labels or real-scene accuracy evidence.",
            "The relation channels are independent observations; no Bayesian prior, posterior, trend, coherence, or strength enters first-round membership.",
            "Complete-link is represented by finite-fixture maximal cliques; no production threshold or selector is frozen.",
            "SVG is compared only on equivalent canonical 2D facts; 3D, Z, clearance, and barrier channels remain IFC-only acceptance facts.",
            "Union area is a diagnostic arithmetic comparison; polygon topology, holes, self-intersections, and multi-overlap semantics remain deferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"schema": evidence["schema"], "fixture_sha256": evidence["fixture_sha256"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
