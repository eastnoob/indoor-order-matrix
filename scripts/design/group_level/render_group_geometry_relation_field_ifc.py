"""Write an IFC group-relation audit from one already computed description."""

from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping
import uuid


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "outputs/design/group_geometry_relation_field_ifc"


def fingerprint(path: Path) -> dict[str, Any]:
    """Stream one IFC file and return its path, size, and SHA-256."""
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "path": str(source.resolve()),
        "byte_length": source.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _plain(value: Any) -> Any:
    """Convert immutable field records into strict JSON-compatible values."""
    if is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite values cannot be serialized")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _write_json(path: Path, value: Any) -> None:
    """Write one deterministic strict-JSON artifact."""
    path.write_text(
        json.dumps(_plain(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _xml(value: Any) -> str:
    """Escape text for SVG XML."""
    return (
        str(value).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def _plane_record(plane: Any) -> dict[str, Any]:
    """Serialize the supplied analysis plane without assuming world-XY."""
    data = _plain(plane)
    if not isinstance(data, Mapping):
        raise TypeError("plane must be an AnalysisPlane or mapping")
    return dict(data)


def _fingerprint_record(value: Any) -> dict[str, Any]:
    """Validate one caller-provided IFC fingerprint record."""
    data = _plain(value)
    if not isinstance(data, Mapping):
        raise TypeError("fingerprint must be a mapping")
    required = {"path", "byte_length", "sha256"}
    if not required.issubset(data):
        raise ValueError(f"fingerprint requires {sorted(required)}")
    return dict(data)


def _group_names(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Map canonical group IDs to source-authored names from the manifest."""
    return {
        f"ifc-group:{group['global_id']}": str(group.get("name") or group["global_id"])
        for group in manifest.get("groups", ())
    }


def _plan_geometry(description: Mapping[str, Any], names: Mapping[str, str]) -> dict[str, Any]:
    """Extract the computed member polygons needed to redraw all pair views."""
    groups = []
    for group in description.get("group_geometry", ()):
        group_id = str(group["target_id"])
        members = []
        for member in group.get("member_geometry", ()):
            polygons = []
            holes_by_polygon = member.get("polygon_holes", ())
            for index, exterior in enumerate(member.get("polygons", ())):
                holes = holes_by_polygon[index] if index < len(holes_by_polygon) else ()
                polygons.append(
                    {
                        "exterior": [[float(x), float(y)] for x, y in exterior],
                        "holes": [
                            [[float(x), float(y)] for x, y in hole]
                            for hole in holes
                        ],
                    }
                )
            members.append(
                {
                    "member_id": str(member["member_id"]),
                    "area": member.get("area"),
                    "polygons": polygons,
                }
            )
        groups.append(
            {
                "group_id": group_id,
                "name": names.get(group_id, group_id),
                "geometry_status": group.get("geometry_status"),
                "members": members,
            }
        )
    return {"schema": "group-relation-plan-geometry/v1", "groups": groups}


def _polygon(record: Mapping[str, Any]) -> Any:
    """Build one Shapely polygon from a saved projected component."""
    from shapely.geometry import Polygon

    return Polygon(record["exterior"], record.get("holes", ()))


def _bounds(groups: list[Mapping[str, Any]]) -> tuple[float, float, float, float]:
    """Return non-degenerate bounds for projected groups."""
    points = [
        point
        for group in groups
        for member in group["members"]
        for polygon in member["polygons"]
        for point in polygon["exterior"]
    ]
    if not points:
        return 0.0, 0.0, 1.0, 1.0
    xmin, ymin = min(p[0] for p in points), min(p[1] for p in points)
    xmax, ymax = max(p[0] for p in points), max(p[1] for p in points)
    return xmin, ymin, xmax if xmax > xmin else xmin + 1.0, ymax if ymax > ymin else ymin + 1.0


def _path(shape: Any, project: Any) -> str:
    """Convert polygonal Shapely geometry, including holes, into an SVG path."""
    if shape.geom_type == "Polygon":
        polygons = [shape]
    elif hasattr(shape, "geoms"):
        polygons = [
            polygon
            for child in shape.geoms
            for polygon in _polygonal_parts(child)
        ]
    else:
        polygons = []
    commands = []
    for polygon in polygons:
        if polygon.geom_type != "Polygon":
            continue
        for ring in [polygon.exterior, *polygon.interiors]:
            coordinates = [project((float(x), float(y))) for x, y in ring.coords]
            if coordinates:
                commands.append(
                    "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in coordinates) + " Z"
                )
    return " ".join(commands)


def _polygonal_parts(shape: Any) -> list[Any]:
    """Recursively retain polygon members from mixed Shapely geometry."""
    if shape.geom_type == "Polygon":
        return [shape]
    if hasattr(shape, "geoms"):
        return [polygon for child in shape.geoms for polygon in _polygonal_parts(child)]
    return []


def _pair_svg(
    pair: Mapping[str, Any],
    groups_by_id: Mapping[str, Mapping[str, Any]],
    source_hash: str,
    plane: Mapping[str, Any],
) -> str:
    """Render real footprints, nearest boundaries, contacts, and overlaps."""
    from shapely.ops import nearest_points, unary_union

    group_a = groups_by_id[pair["group_a"]]
    group_b = groups_by_id[pair["group_b"]]
    selected = [group_a, group_b]
    xmin, ymin, xmax, ymax = _bounds(selected)
    width, height, margin, footer = 1200, 860, 50, 190
    scale = min(
        (width - 2 * margin) / (xmax - xmin),
        (height - footer - 2 * margin) / (ymax - ymin),
    )

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map plane-local coordinates into the pair SVG viewport."""
        return (
            margin + (point[0] - xmin) * scale,
            height - footer - margin - (point[1] - ymin) * scale,
        )

    members = {
        member["member_id"]: unary_union([_polygon(record) for record in member["polygons"]])
        for group in selected
        for member in group["members"]
        if member["polygons"]
    }
    fills = {pair["group_a"]: "#2a9d8f", pair["group_b"]: "#e9a23b"}
    geometry_markup = []
    for group in selected:
        for member in group["members"]:
            shape = members.get(member["member_id"])
            if shape is None:
                continue
            geometry_markup.append(
                f'<path d="{_path(shape, project)}" fill="{fills[group["group_id"]]}" '
                f'fill-opacity=".42" stroke="{fills[group["group_id"]]}" stroke-width="1.5" '
                f'fill-rule="evenodd"><title>{_xml(group["name"])} / {_xml(member["member_id"])}</title></path>'
            )

    relation_markup = []
    for observation in pair["member_pair_observations"]:
        if observation.get("status") != "computed":
            continue
        left = members.get(str(observation["member_a"]))
        right = members.get(str(observation["member_b"]))
        if left is None or right is None:
            continue
        overlap_reading = observation.get("overlap") is True
        overlap = left.intersection(right) if overlap_reading else None
        if overlap is not None and not overlap.is_empty and overlap.area > 0:
            relation_markup.append(
                f'<path d="{_path(overlap, project)}" fill="#d1495b" fill-opacity=".75" '
                'stroke="#8f1d2c" stroke-width="1" fill-rule="evenodd">'
                '<title>positive-area overlap</title></path>'
            )
        contact = observation.get("contact") is True
        if not overlap_reading:
            first, second = nearest_points(left.boundary, right.boundary)
            x1, y1 = project((first.x, first.y))
            x2, y2 = project((second.x, second.y))
            color = "#16823b" if contact else "#365f91"
            relation_markup.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{color}" stroke-width="2"><title>boundary gap: '
                f'{_xml(observation.get("raw_boundary_gap"))}</title></line>'
            )
        if contact and not overlap_reading:
            relation_markup.append(
                f'<circle cx="{x1:.2f}" cy="{y1:.2f}" r="4" fill="#16823b">'
                '<title>contact</title></circle>'
            )

    details = [
        f"pair: {pair['pair_id']}",
        f"groups: {pair['group_a_name']} | {pair['group_b_name']}",
        f"source sha256: {source_hash}",
        f"plane: {plane.get('name')} | units: {pair.get('unit')}",
        f"status: {pair.get('status')} | member pairs: {len(pair['member_pair_observations'])}",
    ]
    unavailable = [
        f"{item.get('member_a')} / {item.get('member_b')}: {item.get('status')} ({item.get('reason')})"
        for item in pair["member_pair_observations"]
        if item.get("status") != "computed"
    ]
    details.append(
        "unavailable member pairs: " + "; ".join(unavailable)
        if unavailable
        else "unavailable member pairs: not covered by this IFC pair"
    )
    detail_markup = "".join(
        f'<text x="{margin}" y="{height-footer+24+index*20}" font-size="13">{_xml(text)}</text>'
        for index, text in enumerate(details)
    )
    legend_y = height - 22
    legend = (
        f'<rect x="50" y="{legend_y-12}" width="14" height="14" fill="#2a9d8f"/>'
        f'<text x="70" y="{legend_y}" font-size="12">group A</text>'
        f'<rect x="155" y="{legend_y-12}" width="14" height="14" fill="#e9a23b"/>'
        f'<text x="175" y="{legend_y}" font-size="12">group B</text>'
        f'<rect x="260" y="{legend_y-12}" width="14" height="14" fill="#d1495b"/>'
        f'<text x="280" y="{legend_y}" font-size="12">overlap</text>'
        f'<line x1="365" y1="{legend_y-5}" x2="385" y2="{legend_y-5}" stroke="#365f91" '
        f'stroke-width="2"/><text x="391" y="{legend_y}" font-size="12">nearest boundaries</text>'
        f'<circle cx="570" cy="{legend_y-5}" r="4" fill="#16823b"/>'
        f'<text x="580" y="{legend_y}" font-size="12">contact</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<title>{_xml(pair["pair_id"])}</title><rect width="100%" height="100%" fill="white"/>'
        + "".join(geometry_markup) + "".join(relation_markup)
        + f'<line x1="0" y1="{height-footer}" x2="{width}" y2="{height-footer}" stroke="#bbb"/>'
        + detail_markup
        + f'<text x="50" y="{height-50}" font-size="12">Diagnostic only: geometry observations; no membership, support or strength.</text>'
        + legend + "</svg>"
    )


def _overview_svg(
    groups: list[Mapping[str, Any]],
    plane: Mapping[str, Any],
    source_hash: str,
    source_metadata: Mapping[str, Any],
) -> str:
    """Render all saved IFC-derived group footprints in one local plane."""
    xmin, ymin, xmax, ymax = _bounds(groups)
    width, height, margin = 1500, 1050, 45
    scale = min((width - 2 * margin) / (xmax - xmin), (height - 2 * margin) / (ymax - ymin))

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map plane-local coordinates into the overview viewport."""
        return margin + (point[0] - xmin) * scale, height - margin - (point[1] - ymin) * scale

    markup = []
    for group in groups:
        for member in group["members"]:
            for record in member["polygons"]:
                markup.append(
                    f'<path d="{_path(_polygon(record), project)}" fill="#d9e2e8" '
                    f'stroke="#354a59" fill-opacity=".7" stroke-width=".8" fill-rule="evenodd">'
                    f'<title>{_xml(group["name"])} / {_xml(group["group_id"])}</title></path>'
                )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        '<title>IFC group geometry relation overview</title><rect width="100%" height="100%" fill="white"/>'
        + "".join(markup)
        + f'<text x="{margin}" y="20" font-size="12">DIAGNOSTIC ONLY | source: {_xml(source_metadata.get("workspace_relative_path"))} '
        f'| schema: {_xml(source_metadata.get("ifc_schema"))} | sha256: {_xml(source_hash)}</text>'
        + f'<text x="{margin}" y="38" font-size="12">plane: {_xml(plane.get("name"))} '
        f'| origin: {_xml(plane.get("origin"))} | basis: {_xml(plane.get("basis"))} '
        f'| unit: {_xml(source_metadata.get("unit"))} | project: {_xml(source_metadata.get("project_ids"))}</text></svg>'
    )


def _shared_dependency_present(value: Any) -> bool:
    """Recognize only explicit shared-member dependency evidence."""
    return bool(
        isinstance(value, Mapping)
        and value.get("status") == "diagnostic_only"
        and value.get("member_ids")
    )


def write_report(
    description: Mapping[str, Any],
    envelopes: tuple[Any, ...] | list[Any],
    manifest: Mapping[str, Any],
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    plane: Any,
    output_root: Path = OUTPUT,
) -> Path:
    """Write audit artifacts from one real description/envelope computation."""
    before_record = _fingerprint_record(before)
    after_record = _fingerprint_record(after)
    expected = manifest.get("source", {})
    if before_record["sha256"] != expected.get("sha256_before"):
        raise ValueError("before fingerprint does not match the pinned source manifest")
    if after_record["sha256"] != expected.get("sha256_after"):
        raise ValueError("after fingerprint does not match the pinned source manifest")
    if before_record["sha256"] != after_record["sha256"]:
        raise ValueError("source fingerprint changed during IFC processing")
    if before_record["byte_length"] != expected.get("byte_length"):
        raise ValueError("source byte length does not match the pinned source manifest")
    if before_record["byte_length"] != after_record["byte_length"]:
        raise ValueError("source byte length changed during IFC processing")

    plane_data = _plane_record(plane)
    names = _group_names(manifest)
    plan_geometry = _plan_geometry(description, names)
    groups_by_id = {group["group_id"]: group for group in plan_geometry["groups"]}
    relations = {
        json.dumps(
            sorted((str(item["group_a"]), str(item["group_b"]))),
            ensure_ascii=False,
            separators=(",", ":"),
        ): item
        for item in description.get("group_relations", ())
    }
    source_hash = str(before_record["sha256"])
    timestamp = datetime.now(timezone.utc)
    output = Path(output_root) / (
        "run_" + timestamp.strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6]
    )
    output.mkdir(parents=True, exist_ok=False)
    pair_directory = output / "pairs"
    pair_directory.mkdir()

    # Persist the expensive computation before generating any derived views.
    _write_json(
        output / "plan_geometry.json",
        {**plan_geometry, "analysis_plane": plane_data, "source_sha256": source_hash},
    )
    _write_json(
        output / "envelopes.json",
        {"schema": "group-geometry-relation-envelopes/v1", "envelopes": envelopes},
    )

    pair_records = []
    raw_status_counts: Counter[str] = Counter()
    member_status_counts: Counter[str] = Counter()
    relation_type_counts: Counter[str] = Counter()
    shared_count = 0
    for index, envelope in enumerate(envelopes):
        pair_id = str(envelope.target["id"])
        relation = relations.get(pair_id)
        if relation is None:
            raise ValueError(f"description lacks relation for envelope {pair_id}")
        member_observations = list(relation.get("member_pair_observations", ()))
        statuses = Counter(str(item.get("status")) for item in member_observations)
        member_status_counts.update(statuses)
        raw_status_counts[str(_plain(envelope.raw_status))] += 1
        if any(item.get("overlap") is True for item in member_observations):
            relation_type_counts["positive_area_overlap"] += 1
        if any(item.get("contact") is True for item in member_observations):
            relation_type_counts["contact"] += 1
        if any(item.get("raw_boundary_gap") not in (None, 0) for item in member_observations):
            relation_type_counts["positive_boundary_gap"] += 1
        shared = relation.get("shared_member_dependency")
        shared_count += int(_shared_dependency_present(shared))
        pair = {
            "index": index,
            "pair_id": pair_id,
            "group_a": str(relation["group_a"]),
            "group_b": str(relation["group_b"]),
            "group_a_name": names.get(str(relation["group_a"]), str(relation["group_a"])),
            "group_b_name": names.get(str(relation["group_b"]), str(relation["group_b"])),
            "status": relation.get("status"),
            "unit": relation.get("unit"),
            "member_pair_observations": member_observations,
            "member_pair_status_counts": dict(sorted(statuses.items())),
            "shared_member_dependency": shared,
            "source_ids": list(envelope.source_ids),
            "provenance": _plain(envelope.provenance),
            "cache_identity": _plain(envelope.cache_identity),
            "envelope": _plain(envelope),
            "svg": f"pairs/{index:04d}.svg",
            "json": f"pairs/{index:04d}.json",
        }
        pair_records.append(pair)
        _write_json(pair_directory / f"{index:04d}.json", pair)
        (pair_directory / f"{index:04d}.svg").write_text(
            _pair_svg(pair, groups_by_id, source_hash, plane_data),
            encoding="utf-8",
        )

    source_metadata = {
        **expected,
        "unit": description.get("analysis_frame", {}).get("unit"),
        "project_ids": expected.get("ifc_project_global_ids"),
    }
    (output / "overview.svg").write_text(
        _overview_svg(plan_geometry["groups"], plane_data, source_hash, source_metadata),
        encoding="utf-8",
    )
    coverage = (
        "not covered by this pinned IFC"
        if not member_status_counts.get("invalid") and not member_status_counts.get("not_available")
        else "present in indexed pair records"
    )
    report = {
        "schema": "group-geometry-relation-field-ifc-report/v1",
        "created_utc": timestamp.isoformat(),
        "source": {
            "manifest": _plain(manifest.get("source", {})),
            "length_unit": _plain(manifest.get("length_unit")),
            "before": before_record,
            "after": after_record,
        },
        "diagnostic_only": True,
        "analysis_plane": plane_data,
        "units": sorted({str(pair["unit"]) for pair in pair_records}),
        "audit": {
            "group_pair_count": len(pair_records),
            "pair_status_counts": dict(sorted(raw_status_counts.items())),
            "relation_type_counts": dict(sorted(relation_type_counts.items())),
            "member_pair_status_counts": dict(sorted(member_status_counts.items())),
            "missing_invalid_coverage": coverage,
            "shared_member_dependency_pair_count": shared_count,
            "pairs_with_source_ids": sum(bool(pair["source_ids"]) for pair in pair_records),
            "pair_ids_in_envelope_order": [pair["pair_id"] for pair in pair_records],
        },
        "legend": {
            "group_a": "teal footprint",
            "group_b": "amber footprint",
            "nearest_boundary": "blue line",
            "contact": "green point and line",
            "positive_area_overlap": "red area",
        },
        "artifacts": {
            "overview": "overview.svg",
            "plan_geometry": "plan_geometry.json",
            "envelopes": "envelopes.json",
            "pair_manifest": "view_manifest.json",
        },
    }
    _write_json(output / "report.json", report)
    _write_json(
        output / "view_manifest.json",
        {
            "schema": "group-geometry-relation-view-manifest/v1",
            "source": {**_plain(expected), "length_unit": _plain(manifest.get("length_unit"))},
            "source_sha256": source_hash,
            "analysis_plane": plane_data,
            "units": report["units"],
            "diagnostic_only": True,
            "overview": "overview.svg",
            "pairs": [
                {
                    "index": pair["index"],
                    "pair_id": pair["pair_id"],
                    "status": pair["status"],
                    "unit": pair["unit"],
                    "svg": pair["svg"],
                    "json": pair["json"],
                }
                for pair in pair_records
            ],
        },
    )
    return output


__all__ = ["OUTPUT", "fingerprint", "write_report"]
