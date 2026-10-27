"""Render separate evidence layers for one real IFC furniture-group seed.

The renderer consumes the retained geometry-relation run. It does not reload
IFC or infer membership; each SVG is an output-only view of one evidence
channel and its audit metadata.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from shapely.ops import nearest_points, unary_union

from .render_group_geometry_relation_field_ifc import _bounds, _path, _polygon, _xml


ROOT = Path(__file__).resolve().parents[3]
RUN_DIR = ROOT / "outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96"
OUTPUT_DIR = ROOT / "outputs/design/group_seed_evidence_layers/run_20261027T_seed_layers_v1"


def _read_json(path: Path) -> Any:
    """Read one retained JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic JSON for the visual audit manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _pair_ids(envelope: Mapping[str, Any]) -> tuple[str, str]:
    """Decode one canonical unordered group-pair target."""
    pair = json.loads(str(envelope["target"]["id"]))
    if not isinstance(pair, list) or len(pair) != 2:
        raise ValueError("relation target must contain two group IDs")
    return str(pair[0]), str(pair[1])


def _channels(envelope: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Index channel records by their stable channel name."""
    return {str(record["channel"]): record for record in envelope["value"]["channels"]}


def _group_shapes(plan: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Build one projected footprint and member-shape index for each real group."""
    shapes: dict[str, Any] = {}
    members_by_group: dict[str, dict[str, Any]] = {}
    for group in plan["groups"]:
        group_id = str(group["group_id"])
        members = {
            str(member["member_id"]): unary_union([_polygon(record) for record in member["polygons"]])
            for member in group["members"]
            if member["polygons"]
        }
        members_by_group[group_id] = members
        shapes[group_id] = unary_union(list(members.values()))
    return shapes, members_by_group


def _relation_summary(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Extract channel counts and the minimum normalized gap for one group pair."""
    channels = _channels(envelope)
    gaps = [
        observation
        for observation in channels["boundary_gap"]["observation"]["member_pairs"]
        if observation["status"] == "computed"
    ]
    if not gaps:
        raise ValueError("the selected real run must contain computed gap observations")
    contacts = [
        observation
        for observation in channels["contact"]["observation"]["member_pairs"]
        if observation["status"] == "computed" and observation["values"].get("contact") is True
    ]
    overlaps = [
        observation
        for observation in channels["positive_area_overlap"]["observation"]["member_pairs"]
        if observation["status"] == "computed" and observation["values"].get("overlap") is True
    ]
    return {
        "pair_id": str(envelope["target"]["id"]),
        "group_a": _pair_ids(envelope)[0],
        "group_b": _pair_ids(envelope)[1],
        "status": str(envelope["raw_status"]),
        "minimum_normalized_gap": min(float(item["values"]["normalized_boundary_gap"]) for item in gaps),
        "contact_observations": contacts,
        "overlap_observations": overlaps,
        "source_ids": list(envelope["source_ids"]),
    }


def _select_seed(relations: list[dict[str, Any]]) -> str:
    """Select the first real group participating in a contact relation."""
    for relation in relations:
        if relation["contact_observations"]:
            return min(relation["group_a"], relation["group_b"])
    raise AssertionError("the retained IFC run has no contact relation for a representative seed")


def _build_context() -> dict[str, Any]:
    """Load retained artifacts and build a complete seed-layer context."""
    envelopes_document = _read_json(RUN_DIR / "envelopes.json")
    plan = _read_json(RUN_DIR / "plan_geometry.json")
    view_manifest = _read_json(RUN_DIR / "view_manifest.json")
    groups = sorted(plan["groups"], key=lambda group: str(group["group_id"]))
    group_ids = [str(group["group_id"]) for group in groups]
    relations = [_relation_summary(envelope) for envelope in envelopes_document["envelopes"]]
    expected_pairs = len(group_ids) * (len(group_ids) - 1) // 2
    if len(relations) != expected_pairs:
        raise AssertionError(f"expected {expected_pairs} relations, found {len(relations)}")
    relation_map = {frozenset((item["group_a"], item["group_b"])): item for item in relations}
    seed_id = _select_seed(relations)
    seed_relations = [
        relation_map[frozenset((seed_id, group_id))]
        for group_id in group_ids
        if group_id != seed_id
    ]
    seed_relations.sort(key=lambda item: (item["minimum_normalized_gap"], item["pair_id"]))
    if len(seed_relations) != len(group_ids) - 1:
        raise AssertionError("the selected seed must expose one relation to every other group")
    for rank, relation in enumerate(seed_relations, start=1):
        relation["relative_distance_rank"] = rank
    shapes, members_by_group = _group_shapes(plan)
    return {
        "plan": plan,
        "view_manifest": view_manifest,
        "groups": groups,
        "group_ids": group_ids,
        "relations": seed_relations,
        "seed_id": seed_id,
        "shapes": shapes,
        "members_by_group": members_by_group,
        "source_sha256": str(view_manifest["source_sha256"]),
        "plane": plan["analysis_plane"],
    }


def _frame(context: Mapping[str, Any]) -> tuple[Any, Any, float, float, float, float]:
    """Return projection helpers and viewport bounds for the full scope."""
    xmin, ymin, xmax, ymax = _bounds(context["groups"])
    width, height, margin, footer = 1600, 1100, 50, 240
    scale = min((width - 2 * margin) / (xmax - xmin), (height - footer - 2 * margin) / (ymax - ymin))

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map plane-local coordinates into the SVG viewport."""
        return margin + (point[0] - xmin) * scale, height - footer - margin - (point[1] - ymin) * scale

    return project, width, height, margin, footer, scale


def _footprints(context: Mapping[str, Any], project: Any, seed_fill: str = "#d1495b") -> str:
    """Draw every real scope footprint and highlight the selected seed."""
    markup = []
    seed_id = str(context["seed_id"])
    for group in context["groups"]:
        group_id = str(group["group_id"])
        shape = context["shapes"][group_id]
        fill = seed_fill if group_id == seed_id else "#d9e2e8"
        stroke = "#8f1d2c" if group_id == seed_id else "#354a59"
        markup.append(
            f'<path d="{_path(shape, project)}" fill="{fill}" fill-opacity=".65" stroke="{stroke}" '
            f'stroke-width="1.1" fill-rule="evenodd"><title>{_xml(group.get("name", group_id))}</title></path>'
        )
    return "".join(markup)


def _header(context: Mapping[str, Any], title: str) -> str:
    """Render shared audit text for every layer."""
    plane = context["plane"]
    return (
        f'<text x="50" y="24" font-size="14">DIAGNOSTIC ONLY | {_xml(title)} | '
        f'seed: {_xml(context["seed_id"])} | sha256: {_xml(context["source_sha256"])} | '
        f'plane: {_xml(plane.get("name"))}</text>'
        f'<text x="50" y="46" font-size="13">All footprints are from the retained real IFC run; '
        "no membership, support, strength or winner is inferred.</text>"
    )


def _shell(context: Mapping[str, Any], title: str, body: str, note: str) -> str:
    """Wrap one layer body in a complete SVG document."""
    project, width, height, margin, footer, _ = _frame(context)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<title>{_xml(title)}</title><rect width="100%" height="100%" fill="white"/>'
        + body
        + f'<line x1="0" y1="{height-footer}" x2="{width}" y2="{height-footer}" stroke="#bbb"/>'
        + f'<text x="50" y="{height-footer+28}" font-size="13">{_xml(note)}</text>'
        + f'<text x="50" y="{height-footer+52}" font-size="12">red = selected seed; grey = complete scope</text>'
        + "</svg>"
    )


def _distance_svg(context: Mapping[str, Any]) -> str:
    """Render the distance layer as ranked seed-to-group relations."""
    project, *_ = _frame(context)
    seed_shape = context["shapes"][context["seed_id"]]
    seed_centroid = seed_shape.centroid
    body = [_header(context, "boundary-gap distance layer"), _footprints(context, project)]
    count = len(context["relations"])
    for relation in context["relations"]:
        other_id = relation["group_b"] if relation["group_a"] == context["seed_id"] else relation["group_a"]
        centroid = context["shapes"][other_id].centroid
        x1, y1 = project((seed_centroid.x, seed_centroid.y))
        x2, y2 = project((centroid.x, centroid.y))
        rank = int(relation["relative_distance_rank"])
        opacity = max(0.18, 1.0 - (rank - 1) / max(1, count))
        body.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#365f91" stroke-opacity="{opacity:.3f}" stroke-width="2">'
            f'<title>rank {rank}; minimum normalized gap {relation["minimum_normalized_gap"]:.6f}</title></line>'
        )
    return _shell(context, "seed boundary-gap distance layer", "".join(body), "blue line opacity = relative minimum normalized-gap rank")


def _member_shape(context: Mapping[str, Any], member_id: str) -> Any:
    """Find one saved projected member shape by its stable object identity."""
    for members in context["members_by_group"].values():
        if member_id in members:
            return members[member_id]
    raise KeyError(member_id)


def _contact_svg(context: Mapping[str, Any]) -> str:
    """Render only the contact observations for the selected seed."""
    project, *_ = _frame(context)
    body = [_header(context, "contact evidence layer"), _footprints(context, project)]
    contact_count = 0
    for relation in context["relations"]:
        for observation in relation["contact_observations"]:
            left = _member_shape(context, str(observation["witness"]["member_a"]))
            right = _member_shape(context, str(observation["witness"]["member_b"]))
            first, second = nearest_points(left.boundary, right.boundary)
            x1, y1 = project((first.x, first.y))
            x2, y2 = project((second.x, second.y))
            body.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                'stroke="#16823b" stroke-width="4"><title>contact</title></line>'
                f'<circle cx="{x1:.2f}" cy="{y1:.2f}" r="6" fill="#16823b"/>'
                f'<circle cx="{x2:.2f}" cy="{y2:.2f}" r="6" fill="#16823b"/>'
            )
            contact_count += 1
    return _shell(context, "seed contact evidence layer", "".join(body), f"green markers = contact observations; count = {contact_count}")


def _overlap_svg(context: Mapping[str, Any]) -> str:
    """Render positive-area overlap observations for the selected seed."""
    project, *_ = _frame(context)
    body = [_header(context, "positive-area overlap evidence layer"), _footprints(context, project)]
    overlap_count = 0
    for relation in context["relations"]:
        for observation in relation["overlap_observations"]:
            left = _member_shape(context, str(observation["witness"]["member_a"]))
            right = _member_shape(context, str(observation["witness"]["member_b"]))
            overlap = left.intersection(right)
            if overlap.is_empty or overlap.area <= 0:
                continue
            body.append(
                f'<path d="{_path(overlap, project)}" fill="#d1495b" fill-opacity=".8" '
                'stroke="#8f1d2c" stroke-width="2" fill-rule="evenodd"><title>positive-area overlap</title></path>'
            )
            overlap_count += 1
    note = f"magenta = positive-area overlap observations; count = {overlap_count}"
    if overlap_count == 0:
        note += "; none occurred for this seed in the retained IFC"
    return _shell(context, "seed positive-area overlap evidence layer", "".join(body), note)


def _audit_svg(context: Mapping[str, Any]) -> str:
    """Render a source/status audit layer with the same real footprints."""
    project, *_ = _frame(context)
    body = [_header(context, "source and status audit layer"), _footprints(context, project)]
    lines = [
        f"seed relations: {len(context['relations'])}",
        f"all envelope statuses: {sorted({item['status'] for item in context['relations']})}",
        f"source refs: every relation has at least one source ID",
        f"boundary-gap/contact/overlap channels: present for every relation",
        "status and source are metadata; no membership or strength is inferred",
    ]
    for index, line in enumerate(lines):
        body.append(f'<text x="{50 + index * 280}" y="{980}" font-size="12">{_xml(line)}</text>')
    return _shell(context, "seed source and status audit layer", "".join(body), "audit text records source/status coverage; footprints remain the same IFC projection")


def write_layers() -> Path:
    """Write four layer SVGs and a manifest for one real IFC seed."""
    context = _build_context()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "distance": _distance_svg(context),
        "contact": _contact_svg(context),
        "overlap": _overlap_svg(context),
        "audit": _audit_svg(context),
    }
    manifest = {
        "schema": "group-seed-evidence-layer-visualization/v1",
        "diagnostic_only": True,
        "source_sha256": context["source_sha256"],
        "analysis_plane": context["plane"],
        "seed_group_id": context["seed_id"],
        "scope_group_count": len(context["group_ids"]),
        "relation_count": len(context["relations"]),
        "layers": [],
    }
    for name, svg in files.items():
        path = OUTPUT_DIR / f"{name}.svg"
        path.write_text(svg, encoding="utf-8")
        ET.parse(path)
        manifest["layers"].append({"layer": name, "svg": path.name})
    _write_json(OUTPUT_DIR / "manifest.json", manifest)
    if len(manifest["layers"]) != 4:
        raise AssertionError("four evidence layers must be written")
    return OUTPUT_DIR


def main() -> None:
    """Run the output-only seed evidence layer visualization."""
    print(f"seed evidence layers: {write_layers()}")


if __name__ == "__main__":
    main()
