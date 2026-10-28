"""Render full-scope axis relations from retained IFC-derived observations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree

from features.group_axis_potential_field import (
    axis_angle_gap,
    build_axis_relation_records,
)

from scripts.design.group_level.render_group_geometry_relation_field_ifc import (
    _bounds,
    _path,
    _plan_geometry,
    _polygon,
    _xml,
)

ROOT = Path(__file__).resolve().parents[3]
AXIS_RUN = ROOT / "outputs/design/group_axis_potential_ifc/run_20261029T010230Z"
TREND_RUN = ROOT / "outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z"
OUTPUT_ROOT = ROOT / "outputs/design/group_axis_relation_diagnostic"
EXPECTED_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
GROUP_COLORS = ("#4d7c70", "#b98c55", "#6d879c", "#9a7182", "#858e5b")


def _read_json(path: Path) -> Any:
    """Read one retained UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic diagnostic JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _axis_observations(document: Mapping[str, Any], expected_sha256: str) -> dict[str, dict[str, Any]]:
    """Extract whole-group axis and endpoint lineage from package source envelopes."""
    if document.get("schema") != "evidence-package-output/v1":
        raise ValueError("unexpected axis-potential output schema")
    observations = {}
    for envelope in document.get("source_envelopes", ()):
        target_id = str(envelope.get("target", {}).get("id", ""))
        cache_identity = envelope.get("cache_identity", {})
        if not target_id or cache_identity.get("input_fingerprint") != expected_sha256:
            raise ValueError(f"axis envelope lacks the pinned IFC lineage: {target_id!r}")
        matches = [
            item for item in envelope.get("value", {}).get("channels", ())
            if item.get("channel") == "overall_group_axis"
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one overall_group_axis for {target_id}")
        channel = matches[0]
        descriptor = channel.get("observation", {}).get("descriptor", {})
        if target_id in observations:
            raise ValueError(f"duplicate source axis target {target_id}")
        observations[target_id] = {
            "group_id": target_id,
            "angle": descriptor.get("angle"),
            "clarity": descriptor.get("strength"),
            "axis_status": channel.get("status", envelope.get("raw_status")),
            "direction_status": descriptor.get("direction_status"),
            "source_ids": list(channel.get("source_ids", envelope.get("source_ids", ()))),
            "source_cache_identity": cache_identity,
            "source_channel": "overall_group_axis",
        }
    if not observations:
        raise ValueError("axis output contains no source envelopes")
    return observations


def _relation_records(observations: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build every unordered relation while keeping channel states separate."""
    return build_axis_relation_records(observations)


def _matrices(group_ids: list[str], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build symmetric full-scope matrices with null diagonal."""
    index = {group_id: position for position, group_id in enumerate(group_ids)}
    channels = ("direction_similarity", "clarity_support")
    matrices = {channel: [[None for _ in group_ids] for _ in group_ids] for channel in channels}
    status = {channel: [["self" if row == col else "missing" for col in range(len(group_ids))] for row in range(len(group_ids))] for channel in channels}
    pair_map = {}
    for record in records:
        row, column = index[record["group_a"]], index[record["group_b"]]
        pair_map[record["pair_id"]] = {"row": row, "column": column, "group_indices": [row, column]}
        for channel in channels:
            reading = record["channels"][channel]
            matrices[channel][row][column] = matrices[channel][column][row] = reading["value"]
            status[channel][row][column] = status[channel][column][row] = reading["status"]
    return {
        "schema": "group-axis-relation-matrices/v1",
        "group_ids": group_ids,
        "index_labels": [f"{i + 1:03d}" for i in range(len(group_ids))],
        "diagonal": "not_applicable",
        "values": matrices,
        "status": status,
        "pair_map": pair_map,
    }


def _matrix_svg(group_ids: list[str], matrix: Mapping[str, Any], channel: str, source_sha256: str, plane_name: str) -> str:
    """Render one labeled symmetric matrix with exact cell values in titles."""
    count, cell = len(group_ids), 20
    margin_left, margin_top, margin_bottom = 78, 100, 55
    width, height = margin_left + count * cell + 24, margin_top + count * cell + margin_bottom
    values, statuses = matrix["values"][channel], matrix["status"][channel]
    markup = []
    for row in range(count):
        label = f"{row + 1:03d}"
        x_label = margin_left + row * cell + cell / 2
        markup.append(f'<text x="{x_label:.1f}" y="{margin_top - 8}" font-size="8" text-anchor="start" transform="rotate(-55 {x_label:.1f} {margin_top - 8})">{label}</text>')
        markup.append(f'<text x="{margin_left - 8}" y="{margin_top + row * cell + 14}" font-size="8" text-anchor="end">{label}</text>')
        for column in range(count):
            value, state = values[row][column], statuses[row][column]
            if state == "self":
                fill, reading = "#d9dee2", "not applicable: self-comparison"
            elif value is None:
                fill, reading = "#f1f1f1", f"{state}: unavailable"
            else:
                strength = max(0.0, min(1.0, float(value)))
                rgb = tuple(round(a + (b - a) * strength) for a, b in zip((245, 248, 245), (44, 118, 92)))
                fill, reading = "#" + "".join(f"{part:02x}" for part in rgb), f"{channel}={float(value):.8f}"
            title = f"row {row + 1:03d} {group_ids[row]}; column {column + 1:03d} {group_ids[column]}; {reading}"
            markup.append(f'<rect x="{margin_left + column * cell}" y="{margin_top + row * cell}" width="{cell}" height="{cell}" fill="{fill}" stroke="white" stroke-width=".45"><title>{_xml(title)}</title></rect>')
    title = "Direction similarity cos squared of undirected angle gap" if channel == "direction_similarity" else "Common clarity support minimum endpoint clarity"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><title>{_xml(title)}</title>'
        f'<rect width="100%" height="100%" fill="white"/><text x="{margin_left}" y="23" font-size="15">{_xml(title)}</text>'
        f'<text x="{margin_left}" y="43" font-size="10">Full-scope relations only | 0° and 180° are equivalent | no pairing or combined score</text>'
        f'<text x="{margin_left}" y="60" font-size="9">Source SHA-256: {_xml(source_sha256)} | plane: {_xml(plane_name)}</text>'
        + "".join(markup)
        + f'<text x="{margin_left}" y="{height - 12}" font-size="9">Hover a cell for exact value and endpoint IDs. Color encodes this channel only.</text></svg>'
    )


def _plane_svg(groups: list[Mapping[str, Any]], source_sha256: str, plane: Mapping[str, Any], group_indexes: Mapping[str, int]) -> str:
    """Render real IFC-derived group footprints with neutral identity colors."""
    xmin, ymin, xmax, ymax = _bounds(groups)
    width, height, margin = 1500, 1050, 48
    scale = min((width - 2 * margin) / (xmax - xmin), (height - 2 * margin) / (ymax - ymin))

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map analysis-plane coordinates into the SVG viewport."""
        return margin + (point[0] - xmin) * scale, height - margin - (point[1] - ymin) * scale

    markup = []
    for group in groups:
        group_id = str(group["group_id"])
        color = GROUP_COLORS[group_indexes[group_id] % len(GROUP_COLORS)]
        for member in group["members"]:
            for polygon in member["polygons"]:
                markup.append(f'<path d="{_path(_polygon(polygon), project)}" fill="{color}" fill-opacity=".48" stroke="{color}" stroke-width=".7" fill-rule="evenodd"><title>{_xml(group_id)}</title></path>')
        center = group.get("center")
        if center:
            x, y = project((float(center[0]), float(center[1])))
            markup.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="10" text-anchor="middle" fill="#111">{group_indexes[group_id] + 1:03d}</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><title>Neutral IFC furniture-group plan</title>'
        f'<rect width="100%" height="100%" fill="white"/>{"".join(markup)}'
        f'<text x="{margin}" y="22" font-size="12">GROUP COLORS ARE IDENTIFIERS ONLY | no axis, relation edge, or aggregate direction drawn</text>'
        f'<text x="{margin}" y="42" font-size="11">Source SHA-256: {_xml(source_sha256)} | plane: {_xml(plane.get("name"))} | units: {_xml(plane.get("unit"))}</text></svg>'
    )


def run(axis_run: Path = AXIS_RUN, trend_run: Path = TREND_RUN, output_root: Path = OUTPUT_ROOT) -> Path:
    """Create pair records, matrices, and neutral plan from saved IFC artifacts."""
    source_manifest = _read_json(trend_run / "source_manifest.json")
    source = source_manifest["source"]
    if source.get("sha256") != EXPECTED_SHA256 or source_manifest.get("source_after", {}).get("sha256") != EXPECTED_SHA256:
        raise ValueError("trend run does not match the pinned IFC source fingerprint")
    plane = source_manifest["analysis_plane"]
    if plane.get("name") != "ifc-world-plan" or source_manifest.get("analysis_unit") != "m":
        raise ValueError("unexpected retained analysis plane")
    plane = {**plane, "unit": source_manifest["analysis_unit"]}
    axis_document = _read_json(axis_run / "axis_potential_output.json")
    observations = _axis_observations(axis_document, EXPECTED_SHA256)
    description = _read_json(trend_run / "description.json")
    geometry_groups = _plan_geometry(description, {})["groups"]
    geometry_by_id = {group["group_id"]: group for group in geometry_groups}
    if set(observations) != set(geometry_by_id):
        raise ValueError("axis observations and plane geometry do not cover the same authored groups")
    if len(observations) != 37:
        raise ValueError(f"expected the retained 37-group IFC scope, found {len(observations)}")
    records = _relation_records(observations)
    expected_pairs = len(observations) * (len(observations) - 1) // 2
    if len(records) != expected_pairs:
        raise AssertionError("full unordered group-pair coverage failed")
    group_ids = sorted(observations)
    matrix = _matrices(group_ids, records)
    output = Path(output_root) / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    (output / "matrices").mkdir()
    _write_json(output / "relations.json", {"schema": "group-axis-relation-records/v1", "diagnostic_only": True, "source_sha256": EXPECTED_SHA256, "analysis_plane": plane, "groups": observations, "relations": records})
    _write_json(output / "matrices.json", matrix)
    group_index = {group_id: index for index, group_id in enumerate(group_ids)}
    groups_indexed = []
    for group_id in group_ids:
        geometry = dict(geometry_by_id[group_id])
        source_group = next(item for item in description["group_geometry"] if item["target_id"] == group_id)
        geometry["center"] = source_group.get("center")
        groups_indexed.append(geometry)
    plane_path = output / "group_plan.svg"
    plane_path.write_text(_plane_svg(groups_indexed, EXPECTED_SHA256, plane, group_index), encoding="utf-8")
    for channel in ("direction_similarity", "clarity_support"):
        path = output / "matrices" / f"{channel}.svg"
        path.write_text(_matrix_svg(group_ids, matrix, channel, EXPECTED_SHA256, str(plane["name"])), encoding="utf-8")
    manifest = {
        "schema": "group-axis-relation-diagnostic-manifest/v1",
        "diagnostic_only": True,
        "source": source,
        "analysis_plane": plane,
        "retained_axis_run": str(axis_run.resolve()),
        "retained_geometry_run": str(trend_run.resolve()),
        "ifc_extraction_rerun": False,
        "synthetic_input": False,
        "scope": {"group_count": len(group_ids), "unordered_pair_count": len(records)},
        "group_index": [{"index": index, "label": f"{index + 1:03d}", "group_id": group_id} for index, group_id in enumerate(group_ids)],
        "pair_index": [{"pair_id": record["pair_id"], **matrix["pair_map"][record["pair_id"]], "group_a": record["group_a"], "group_b": record["group_b"]} for record in records],
        "artifacts": {"relations": "relations.json", "matrices": "matrices.json", "direction_similarity_matrix": "matrices/direction_similarity.svg", "clarity_support_matrix": "matrices/clarity_support.svg", "group_plan": "group_plan.svg"},
        "interpretation": "Each unordered pair is a relation address, not a pairing or grouping decision. Matrix diagonals are not applicable; channel readings remain separate and no combined relation score is emitted.",
    }
    _write_json(output / "manifest.json", manifest)
    report = {
        "schema": "group-axis-relation-diagnostic-report/v1",
        "status": "pass",
        "source_sha256": EXPECTED_SHA256,
        "analysis_plane": plane,
        "group_count": len(group_ids),
        "unordered_pair_count": len(records),
        "channel_status_counts": {channel: {status: sum(record["channels"][channel]["status"] == status for record in records) for status in ("computed", "not_available")} for channel in ("axis_angle_gap", "direction_similarity", "clarity_similarity", "clarity_support")},
        "matrix_symmetry_verified": all(matrix["values"][channel][i][j] == matrix["values"][channel][j][i] for channel in ("direction_similarity", "clarity_support") for i in range(len(group_ids)) for j in range(len(group_ids))),
        "pair_scope_only": True,
        "combined_relation_emitted": False,
        "ifc_extraction_rerun": False,
        "artifacts": manifest["artifacts"],
    }
    _write_json(output / "report.json", report)
    for relative in [*manifest["artifacts"].values(), "manifest.json", "report.json"]:
        path = output / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"diagnostic artifact missing or empty: {relative}")
        if path.suffix == ".svg":
            ElementTree.parse(path)
    if not report["matrix_symmetry_verified"]:
        raise AssertionError("relation matrices are not symmetric")
    return output


def main() -> None:
    """Replay retained artifacts and print the diagnostic output directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--axis-run", type=Path, default=AXIS_RUN)
    parser.add_argument("--trend-run", type=Path, default=TREND_RUN)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    output = run(args.axis_run.resolve(), args.trend_run.resolve(), args.output_root.resolve())
    print(json.dumps({"status": "pass", "output": str(output.resolve())}, sort_keys=True))


if __name__ == "__main__":
    main()
