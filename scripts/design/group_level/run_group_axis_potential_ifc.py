"""Run the axis-only furniture-group potential on the pinned IFC source."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from features.field_core import (
    FieldQuery,
    build_evidence_package_contract,
    evaluate_evidence_package_freshness,
    fingerprint_evidence_dependency,
    serialize_evidence_package_output,
)
from features.group_axis_potential_field import (
    FIELD_OUTPUT_SCHEMA,
    FIELD_RECIPE_ID,
    OUTPUT_FUNCTION_VERSION,
    build_group_axis_potential_package,
)
from features.group_self_description import describe_group_relations

from .run_group_trend_alignment_field_ifc import (
    DEFAULT_IFC,
    _build_scene,
    _fingerprint,
    _plain,
    _points,
    _write,
    _artifacts_readable,
)
from features.group_trend_alignment_field import build_group_trend_alignment_envelopes


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "group-axis-potential-ifc/v1"
PACKAGE_ID = "group-axis-potential"
PACKAGE_PRODUCER = "features.group_axis_potential_field.build_group_axis_potential_package"


def _field_metadata(result: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build deterministic matrix, non-self profile, and soft-direction artifacts."""
    cells: dict[str, list[dict[str, Any]]] = {}
    profiles: dict[str, dict[str, Any]] = {}
    directions: dict[str, dict[str, Any]] = {}
    for output in result.outputs:
        observation = _plain(output.observation)
        if output.target["kind"] == "furniture_group_axis_field_cell":
            cells.setdefault(observation["field_id"], []).append(observation)
        elif output.channel == "non_self_profile":
            profiles[observation["field_id"]] = observation
        elif output.channel == "soft_view_direction":
            directions[observation["field_id"]] = observation
    matrix = {
        "schema": "group-axis-potential-field-matrix/v1",
        "fields": {
            field_id: {
                "anchor_group_id": items[0]["anchor_group_id"] if items else None,
                "cells": sorted(items, key=lambda item: item["target_group_id"]),
            }
            for field_id, items in sorted(cells.items())
        },
    }
    return (
        matrix,
        {"schema": "group-axis-potential-non-self-profiles/v1", "profiles": profiles},
        {"schema": "group-axis-potential-soft-view-directions/v1", "directions": directions},
    )


def _package_contract(
    description: dict[str, Any],
    envelopes: tuple[Any, ...],
    query: FieldQuery,
    plane: dict[str, Any],
    source_sha256: str,
    artifact_paths: tuple[str, ...],
    result: Any,
) -> dict[str, Any]:
    """Declare source-axis dependencies and all replayable package artifacts."""
    target_ids = tuple(sorted(str(envelope.target["id"]) for envelope in envelopes))
    channels = tuple(sorted({output.channel for output in result.outputs}))
    dependencies = {
        "scene": fingerprint_evidence_dependency(description.get("group_geometry", ())),
        "model": fingerprint_evidence_dependency({"target_kind": "furniture_group", "scope": target_ids}),
        "source": source_sha256,
        "plane": fingerprint_evidence_dependency(plane),
        "query": fingerprint_evidence_dependency(_plain(query)),
        "recipe": fingerprint_evidence_dependency({"recipe": FIELD_RECIPE_ID, "field_schema": FIELD_OUTPUT_SCHEMA}),
        "channels": fingerprint_evidence_dependency(channels),
    }
    return build_evidence_package_contract(
        package_id=PACKAGE_ID,
        package_schema=FIELD_OUTPUT_SCHEMA,
        producer=PACKAGE_PRODUCER,
        target_ids=target_ids,
        dependencies=dependencies,
        algorithm_version=OUTPUT_FUNCTION_VERSION,
        schema_version=FIELD_OUTPUT_SCHEMA,
        artifacts={
            "source_manifest": "source_manifest.json",
            "description": "description.json",
            "envelopes": "envelopes.json",
            "axis_potential_output": "axis_potential_output.json",
            "report": "report.json",
            "view_manifest": "view_manifest.json",
            "field_view_manifest": "field_view_manifest.json",
            "field_matrix": "field_matrix.json",
            "field_profiles": "field_profiles.json",
            "field_directions": "field_directions.json",
            "visualizations": list(artifact_paths),
        },
    )


def _aggregate_svg(description: dict[str, Any], angle: float | None, source: dict[str, Any], plane: dict[str, Any]) -> str:
    """Render all real IFC-derived group polygons and one aggregate axis."""
    groups = tuple(description.get("group_geometry", ()))
    points = [point for group in groups for point in _points(group)]
    if not points:
        xmin, ymin, xmax, ymax = 0.0, 0.0, 1.0, 1.0
    else:
        xmin, ymin = min(point[0] for point in points), min(point[1] for point in points)
        xmax, ymax = max(point[0] for point in points), max(point[1] for point in points)
        xmax, ymax = max(xmax, xmin + 1.0), max(ymax, ymin + 1.0)
    width, height, margin, footer = 1400, 1000, 50, 220
    scale = min((width - 2 * margin) / (xmax - xmin), (height - footer - 2 * margin) / (ymax - ymin))

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map a world-plan point into the SVG viewport."""
        return margin + (point[0] - xmin) * scale, height - footer - margin - (point[1] - ymin) * scale

    markup: list[str] = []
    for index, group in enumerate(groups):
        fill = "#2a9d8f" if index % 2 == 0 else "#e9a23b"
        for member in group.get("member_geometry", ()):
            for polygon in member.get("polygons", ()):
                if not polygon:
                    continue
                coords = [project((float(point[0]), float(point[1]))) for point in polygon]
                path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in coords) + " Z"
                markup.append(f'<path d="{path}" fill="{fill}" fill-opacity=".24" stroke="{fill}" stroke-width="1"><title>{group.get("target_id")}</title></path>')
    if points:
        center = (sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points))
    else:
        center = (0.5, 0.5)
    direction = "undefined"
    if angle is not None:
        length = max(xmax - xmin, ymax - ymin) * 0.30
        theta = math.radians(float(angle))
        first = project((center[0] - length * math.cos(theta), center[1] - length * math.sin(theta)))
        second = project((center[0] + length * math.cos(theta), center[1] + length * math.sin(theta)))
        markup.append(f'<line x1="{first[0]:.2f}" y1="{first[1]:.2f}" x2="{second[0]:.2f}" y2="{second[1]:.2f}" stroke="#c1121f" stroke-width="5"><title>aggregate_direction angle {angle}</title></line>')
        direction = f"angle={float(angle):.4f}°"
    details = [
        "axis-only furniture-group potential",
        f"groups: {len(groups)}",
        f"aggregate direction: {direction}",
        f"source sha256: {source.get('sha256')}",
        f"plane: {plane.get('name')} | units: m",
        "axis source: overall_group_axis; layout_axis excluded",
    ]
    text = "".join(f'<text x="{margin}" y="{height-footer+24+i*20}" font-size="13">{item}</text>' for i, item in enumerate(details))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><title>axis-only furniture-group potential</title><rect width="100%" height="100%" fill="white"/>{"".join(markup)}<line x1="0" y1="{height-footer}" x2="{width}" y2="{height-footer}" stroke="#bbb"/>{text}</svg>'


def _field_svg(
    description: dict[str, Any],
    field_id: str,
    cells: tuple[dict[str, Any], ...],
    source: dict[str, Any],
    plane: dict[str, Any],
) -> str:
    """Render one full-scope source-axis field from real IFC group polygons."""
    groups = tuple(description.get("group_geometry", ()))
    points = [point for group in groups for point in _points(group)]
    if not points:
        xmin, ymin, xmax, ymax = 0.0, 0.0, 1.0, 1.0
    else:
        xmin, ymin = min(point[0] for point in points), min(point[1] for point in points)
        xmax, ymax = max(point[0] for point in points), max(point[1] for point in points)
        xmax, ymax = max(xmax, xmin + 1.0), max(ymax, ymin + 1.0)
    width, height, margin, footer = 1400, 1000, 50, 220
    scale = min((width - 2 * margin) / (xmax - xmin), (height - footer - 2 * margin) / (ymax - ymin))

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map a real IFC plan point into the SVG viewport."""
        return margin + (point[0] - xmin) * scale, height - footer - margin - (point[1] - ymin) * scale

    by_group = {cell["target_group_id"]: cell for cell in cells}
    anchor_group_id = cells[0]["anchor_group_id"] if cells else None
    markup: list[str] = []
    for group in groups:
        group_id = group.get("target_id")
        cell = by_group.get(group_id)
        value = cell.get("axis_field_support") if cell else None
        status = cell.get("status", "not_available") if cell else "not_available"
        opacity = 0.12 + 0.78 * float(value) if isinstance(value, (int, float)) else 0.08
        fill = "#3155a6" if group_id != anchor_group_id else "#c1121f"
        stroke_width = 3 if group_id == anchor_group_id else 1
        for member in group.get("member_geometry", ()):
            for polygon in member.get("polygons", ()):
                if not polygon:
                    continue
                coords = [project((float(point[0]), float(point[1]))) for point in polygon]
                path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in coords) + " Z"
                title = f"{group_id} status={status} support={value}"
                markup.append(f'<path d="{path}" fill="{fill}" fill-opacity="{opacity:.3f}" stroke="{fill}" stroke-width="{stroke_width}"><title>{title}</title></path>')
    details = [
        "source-axis furniture-group field",
        f"field: {field_id}",
        f"anchor: {anchor_group_id}",
        f"groups: {len(groups)}",
        f"cell statuses: computed={sum(item['status'] == 'computed' for item in cells)}; unavailable={sum(item['status'] == 'not_available' for item in cells)}",
        f"source sha256: {source.get('sha256')}",
        f"plane: {plane.get('name')} | units: m",
        "color opacity encodes continuous support; red marks the anchor",
    ]
    text = "".join(f'<text x="{margin}" y="{height-footer+24+i*20}" font-size="13">{item}</text>' for i, item in enumerate(details))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><title>source-axis furniture-group field</title><rect width="100%" height="100%" fill="white"/>{"".join(markup)}<line x1="0" y1="{height-footer}" x2="{width}" y2="{height-footer}" stroke="#bbb"/>{text}</svg>'


def run(source_path: Path, output_root: Path, *, group_limit: int | None = None) -> Path:
    """Extract trend envelopes from the pinned IFC and emit additive potential evidence."""
    before = _fingerprint(source_path)
    scene, metadata, authored = _build_scene(source_path, group_limit=group_limit)
    description = describe_group_relations(scene)
    query = FieldQuery(
        frame=scene.context.analysis_plane.name,
        plane=scene.context.analysis_plane,
        tolerance=scene.context.geometry_tolerance,
        revision="group-axis-potential-v1",
    )
    envelopes = build_group_trend_alignment_envelopes(
        scene,
        query=query,
        input_fingerprint=before["sha256"],
        source_fingerprint=before["sha256"],
        recipe_fingerprint="group-axis-potential-axis-only-v1",
        algorithm_version="group-axis-potential-v1",
        schema_version="group-axis-potential-source-envelope/v1",
    )
    result = build_group_axis_potential_package().evaluate(envelopes)
    after = _fingerprint(source_path)
    if before != after:
        raise RuntimeError("pinned IFC changed during axis-potential extraction")
    run_dir = output_root / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    plane = _plain(scene.context.analysis_plane)
    _write(run_dir / "source_manifest.json", {"schema": "group-axis-potential-source-manifest/v1", **metadata, "source_after": after, "analysis_plane": plane})
    _write(run_dir / "description.json", description)
    _write(run_dir / "envelopes.json", {"schema": "group-trend-alignment-envelopes/v2", "query": query, "envelopes": envelopes})
    _write(run_dir / "axis_potential_output.json", serialize_evidence_package_output(result))
    aggregate = next(output for output in result.outputs if output.channel == "aggregate_direction")
    svg_path = run_dir / "aggregate_axis.svg"
    svg_path.write_text(_aggregate_svg(description, aggregate.observation.get("angle"), before, plane), encoding="utf-8")
    _write(run_dir / "view_manifest.json", {"schema": "group-axis-potential-view-manifest/v1", "source": before, "analysis_plane": plane, "artifacts": [str(svg_path.resolve())], "channel": "aggregate_direction"})
    field_views_dir = run_dir / "field_views"
    field_views_dir.mkdir()
    field_cells: dict[str, list[dict[str, Any]]] = {}
    for output in result.outputs:
        if output.target["kind"] != "furniture_group_axis_field_cell":
            continue
        field_cells.setdefault(output.observation["field_id"], []).append(dict(output.observation))
    field_artifacts = []
    for index, (field_id, cells) in enumerate(sorted(field_cells.items())):
        field_path = field_views_dir / f"field_{index:03d}.svg"
        field_path.write_text(_field_svg(description, field_id, tuple(cells), before, plane), encoding="utf-8")
        field_artifacts.append({"field_id": field_id, "path": str(field_path.resolve()), "anchor_group_id": cells[0]["anchor_group_id"]})
    fields_by_id = {item["field_id"]: item for item in field_artifacts}
    for field_id, items in field_cells.items():
        fields_by_id[field_id].update({
            "cell_count": len(items),
            "status_counts": {
                status: sum(item["status"] == status for item in items)
                for status in ("computed", "partial", "not_available", "invalid", "ambiguous")
            },
        })
    field_manifest = {"schema": "group-axis-potential-field-view-manifest/v1", "source": before, "analysis_plane": plane, "fields": [fields_by_id[key] for key in sorted(fields_by_id)]}
    _write(run_dir / "field_view_manifest.json", field_manifest)
    matrix, profiles, directions = _field_metadata(result)
    _write(run_dir / "field_matrix.json", matrix)
    _write(run_dir / "field_profiles.json", profiles)
    _write(run_dir / "field_directions.json", directions)
    report = {
        "schema": SCHEMA,
        "source": before,
        "source_after": after,
        "eligible_authored_groups": len(authored),
        "source_envelopes": len(envelopes),
        "derived_outputs": len(result.outputs),
        "output_channels": [output.channel for output in result.outputs],
        "aggregate_direction_status": _plain(aggregate.status),
        "aggregate_direction": aggregate.observation.get("angle"),
        "coverage": next(output.observation for output in result.outputs if output.channel == "coverage"),
        "visualization": str(svg_path.resolve()),
        "field_view_count": len(field_artifacts),
        "field_view_manifest": str((run_dir / "field_view_manifest.json").resolve()),
        "field_cell_count": len(field_cells) * len(envelopes),
        "field_matrix": "field_matrix.json",
        "field_profiles": "field_profiles.json",
        "field_directions": "field_directions.json",
        "synthetic_input": False,
        "layout_axis_used": False,
        "package_contract": "package_contract.json",
        "package_status": "package_status.json",
    }
    _write(run_dir / "report.json", report)
    visualization_paths = tuple(sorted(
        str(Path(item["path"]).relative_to(run_dir.resolve())) for item in field_artifacts
    ))
    artifact_paths = ("source_manifest.json", "description.json", "envelopes.json", "axis_potential_output.json", "report.json", "view_manifest.json", "field_view_manifest.json", "field_matrix.json", "field_profiles.json", "field_directions.json", *visualization_paths, "aggregate_axis.svg")
    contract = _package_contract(description, envelopes, query, plane, str(before["sha256"]), visualization_paths + ("aggregate_axis.svg",), result)
    _write(run_dir / "package_contract.json", contract)
    package_status = evaluate_evidence_package_freshness(
        cached_contract=contract,
        current_contract=contract,
        artifacts_available=_artifacts_readable(run_dir, (*artifact_paths, "package_contract.json")),
    )
    _write(run_dir / "package_status.json", package_status)
    return run_dir


def main() -> None:
    """Run the pinned-IFC axis-potential extraction and print its artifact path."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ifc", type=Path, default=DEFAULT_IFC)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/design/group_axis_potential_ifc")
    parser.add_argument("--group-limit", type=int, default=None)
    args = parser.parse_args()
    run_dir = run(args.ifc.resolve(), args.output_root.resolve(), group_limit=args.group_limit)
    print(json.dumps({"status": "pass", "run_dir": str(run_dir), "source": _fingerprint(args.ifc.resolve())}, sort_keys=True))


if __name__ == "__main__":
    main()
