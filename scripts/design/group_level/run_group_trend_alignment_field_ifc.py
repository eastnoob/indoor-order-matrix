"""Run the approved trend-alignment package on the pinned IFC only."""

from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.ifc_bonsai import (  # noqa: E402
    _native_length_unit,
    _native_mesh_record,
    _native_source_id,
    _native_world_transform,
    _native_group_records,
    _scene_from_records,
)
from features.field_core import FieldQuery  # noqa: E402
from features.group_self_description import describe_group_relations  # noqa: E402
from features.group_trend_alignment_field import build_group_trend_alignment_envelopes  # noqa: E402
from features.scene_contract import AuthoredGroup, SourceObject  # noqa: E402


DEFAULT_IFC = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
SCHEMA = "group-trend-alignment-ifc-diagnostic/v2"
PACKAGE_SCHEMA = "group-trend-alignment-envelopes/v2"
CHANNELS = ("overall_group_axis", "layout_axis")
SUPPRESSED_CHANNELS = ("member_frame", "member_axis")


def _plain(value: Any) -> Any:
    """Convert frozen contracts and nested records to strict JSON values."""
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


def _write(path: Path, value: Any) -> None:
    """Write deterministic JSON without mutating the IFC source."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_plain(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _fingerprint(path: Path) -> dict[str, object]:
    """Capture the pinned IFC identity before and after extraction."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path.resolve()), "byte_length": path.stat().st_size, "sha256": digest.hexdigest()}


def _representation(entity: object, identifier: str) -> object | None:
    """Select one exact authored IFC representation without a fallback."""
    product_representation = getattr(entity, "Representation", None)
    return next(
        (item for item in getattr(product_representation, "Representations", ()) or ()
         if getattr(item, "RepresentationIdentifier", None) == identifier),
        None,
    )


def _build_scene(source_path: Path) -> tuple[object, dict[str, object], tuple[AuthoredGroup, ...]]:
    """Extract only the 37 authored furniture groups and their 95 IFC members."""
    import ifcopenshell
    import ifcopenshell.geom  # noqa: F401
    import ifcopenshell.util.shape  # noqa: F401

    source = ifcopenshell.open(str(source_path))
    module = importlib.import_module("ifcopenshell")
    units, scale, _, _ = _native_length_unit(source)
    authored = tuple(group for group in _native_group_records(source) if group.group_role == "furniture_group")
    member_ids = sorted({ref.removeprefix("ifc-object:") for group in authored for ref in group.member_refs})
    products = {_native_source_id(entity): entity for entity in source.by_type("IfcProduct")}
    geometries = []
    source_objects = []
    for member_id in member_ids:
        entity = products.get(member_id)
        if entity is None:
            continue
        body = _representation(entity, "Body")
        analysis = _representation(entity, "Analysis")
        body_mesh, body_uncertainty = (None, None) if body is None else _native_mesh_record(entity, f"{member_id}:body", units, module, body)
        analysis_mesh, analysis_uncertainty = (None, None) if analysis is None else _native_mesh_record(entity, f"{member_id}:analysis", units, module, analysis)
        if body_mesh is not None:
            geometries.append(body_mesh)
        if analysis_mesh is not None:
            geometries.append(analysis_mesh)
        transform, placement_uncertainty = _native_world_transform(entity, float(scale), member_id)
        group_refs = tuple(group.id for group in authored if f"ifc-object:{member_id}" in group.member_refs)
        properties: dict[str, object] = {"analysis_authoritative": analysis_mesh is not None}
        if analysis_mesh is not None:
            properties["OM_FunctionSubstitutes"] = [{
                "substitute_id": f"ifc-object:{member_id}:analysis",
                "source_object_id": f"ifc-object:{member_id}",
                "consumer": "trend",
                "substitute_kind": "MassPatch",
                "analysis_role": "analysis_geometry_substitute",
                "representation_identifier": "Analysis",
                "provenance": {
                    "source_global_id": member_id,
                    "extraction_method": "ifc4_analysis_representation",
                    "world_transform_applied": True,
                    "representation_identifier": "Analysis",
                    "geometry_refs": [analysis_mesh.id],
                },
            }]
        uncertainties = tuple(item for item in (body_uncertainty, placement_uncertainty) if item is not None)
        source_objects.append(SourceObject(
            id=f"ifc-object:{member_id}",
            source_id=member_id,
            source_role="furniture",
            source_class=entity.is_a(),
            world_transform=transform,
            geometry_refs=(body_mesh.id,) if body_mesh is not None else (),
            group_refs=group_refs,
            factual_properties=properties,
            provenance={"method": "group_trend_alignment_ifc_extraction", "body_representation": "Body", "analysis_representation": "Analysis"},
            uncertainties=uncertainties,
        ))
        if analysis_mesh is not None:
            source_objects.append(SourceObject(
                id=f"ifc-object:{member_id}:analysis",
                source_id=f"{member_id}:analysis",
                source_role="analysis_substitute",
                source_class=entity.is_a(),
                geometry_refs=(analysis_mesh.id,),
                factual_properties={"OM_AnalysisRepresentation": {"OM_SourceGlobalId": member_id, "OM_SubstituteKind": "MassPatch", "OM_AnalysisRole": "analysis_geometry_substitute", "OM_VisibilityPolicy": "analysis_only"}},
                provenance={"method": "group_trend_alignment_ifc_extraction", "representation_identifier": "Analysis", "mesh_coordinate_space": "world", "mesh_transform_applied": True},
                uncertainties=(analysis_uncertainty,) if analysis_uncertainty is not None else (),
            ))
    scene = _scene_from_records(units, source_objects, geometries, authored_groups=authored, analysis_units="m")
    project = next(iter(source.by_type("IfcProject")), None)
    metadata = {
        "source": _fingerprint(source_path),
        "ifc_schema": source.schema,
        "project_global_id": getattr(project, "GlobalId", None),
        "source_unit": units,
        "analysis_unit": "m",
        "authored_furniture_group_count": len(authored),
        "member_count": len(member_ids),
        "selection": "all exact IfcGroup.ObjectType=furniture_group groups and their direct members",
    }
    return scene, metadata, authored


def _points(group: Mapping[str, Any]) -> list[tuple[float, float]]:
    """Collect projected exterior points for one group drawing."""
    return [
        (float(point[0]), float(point[1]))
        for member in group.get("member_geometry", ())
        for polygon in member.get("polygons", ())
        for point in polygon
    ]


def _svg(group: Mapping[str, Any], descriptor: Mapping[str, Any], channel: str, source: Mapping[str, Any], plane: Mapping[str, Any]) -> str:
    """Render one channel over real IFC-derived projected furniture polygons."""
    points = _points(group)
    if not points:
        xmin, ymin, xmax, ymax = 0.0, 0.0, 1.0, 1.0
    else:
        xmin, ymin = min(point[0] for point in points), min(point[1] for point in points)
        xmax, ymax = max(point[0] for point in points), max(point[1] for point in points)
        xmax, ymax = max(xmax, xmin + 1.0), max(ymax, ymin + 1.0)
    width, height, margin, footer = 1200, 850, 50, 180
    scale = min((width - 2 * margin) / (xmax - xmin), (height - footer - 2 * margin) / (ymax - ymin))
    def project(point: tuple[float, float]) -> tuple[float, float]:
        return margin + (point[0] - xmin) * scale, height - footer - margin - (point[1] - ymin) * scale
    markup = []
    for index, member in enumerate(group.get("member_geometry", ())):
        fill = "#2a9d8f" if index % 2 == 0 else "#e9a23b"
        for polygon in member.get("polygons", ()):
            if not polygon:
                continue
            coords = [project((float(point[0]), float(point[1]))) for point in polygon]
            path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in coords) + " Z"
            markup.append(f'<path d="{path}" fill="{fill}" fill-opacity=".35" stroke="{fill}" stroke-width="1.5"><title>{member.get("member_id")}</title></path>')
    angle = descriptor.get("angle")
    center = descriptor.get("center")
    if center is None and points:
        center = [sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points)]
    direction = "undefined"
    if angle is not None and center is not None:
        length = max(xmax - xmin, ymax - ymin) * 0.35
        radians = math.radians(float(angle))
        first = project((float(center[0]) - length * math.cos(radians), float(center[1]) - length * math.sin(radians)))
        second = project((float(center[0]) + length * math.cos(radians), float(center[1]) + length * math.sin(radians)))
        markup.append(f'<line x1="{first[0]:.2f}" y1="{first[1]:.2f}" x2="{second[0]:.2f}" y2="{second[1]:.2f}" stroke="#c1121f" stroke-width="4"><title>{channel} angle {angle}</title></line>')
        direction = f"angle={float(angle):.4f}°"
    else:
        direction = str(descriptor.get("direction_status", "undefined"))
    details = [
        f"group: {group.get('target_id')}",
        f"channel: {channel}",
        f"status: {descriptor.get('direction_status', group.get('trend_status'))}",
        f"basis: {descriptor.get('basis')}",
        f"direction: {direction}",
        f"source sha256: {source.get('sha256')}",
        f"plane: {plane.get('name')} | units: m",
        "Diagnostic only: descriptive geometry; no potential, membership, strength, candidate, or winner.",
    ]
    text = "".join(f'<text x="{margin}" y="{height-footer+24+i*20}" font-size="13">{item}</text>' for i, item in enumerate(details))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><title>{group.get("target_id")} {channel}</title><rect width="100%" height="100%" fill="white"/>{"".join(markup)}<line x1="0" y1="{height-footer}" x2="{width}" y2="{height-footer}" stroke="#bbb"/>{text}</svg>'


def run(source_path: Path, output_root: Path) -> Path:
    """Build all trend envelopes and visualizations from one pinned IFC read."""
    before = _fingerprint(source_path)
    scene, metadata, authored = _build_scene(source_path)
    description = describe_group_relations(scene)
    query = FieldQuery(
        frame=scene.context.analysis_plane.name,
        plane=scene.context.analysis_plane,
        tolerance=scene.context.geometry_tolerance,
        revision="group-trend-alignment-v1",
    )
    envelopes = build_group_trend_alignment_envelopes(
        scene,
        query=query,
        input_fingerprint=before["sha256"],
        source_fingerprint=before["sha256"],
        recipe_fingerprint="group-trend-alignment-working-contract-v1",
        algorithm_version="group-trend-alignment-field-v2",
        schema_version=PACKAGE_SCHEMA,
    )
    after = _fingerprint(source_path)
    if before != after:
        raise RuntimeError("pinned IFC changed during trend extraction")
    run_dir = output_root / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    plane = _plain(scene.context.analysis_plane)
    _write(run_dir / "source_manifest.json", {"schema": "group-trend-alignment-source-manifest/v1", **metadata, "source_after": after, "analysis_plane": plane})
    _write(run_dir / "description.json", description)
    _write(run_dir / "envelopes.json", {"schema": PACKAGE_SCHEMA, "query": query, "envelopes": envelopes})
    by_group = {str(group["target_id"]): group for group in description.get("group_geometry", ())}
    manifest = {
        "schema": "group-trend-alignment-visual-manifest/v2",
        "source": before,
        "analysis_plane": plane,
        "channels": CHANNELS,
        "suppressed_channels": SUPPRESSED_CHANNELS,
        "artifacts": [],
    }
    envelope_by_id = {str(envelope.target["id"]): envelope for envelope in envelopes}
    for group_id, envelope in sorted(envelope_by_id.items()):
        group = by_group[group_id]
        records = {record.channel: record for record in envelope.value["channels"]}
        for channel in CHANNELS:
            descriptor = _plain(records[channel].observation["descriptor"])
            path = run_dir / "visualizations" / f"{group_id.replace(':', '_')}__{channel}.svg"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_svg(group, descriptor, channel, before, plane), encoding="utf-8")
            manifest["artifacts"].append({"group_id": group_id, "channel": channel, "path": str(path.resolve()), "status": _plain(envelope.raw_status), "basis": descriptor.get("basis"), "angle": descriptor.get("angle")})
    _write(run_dir / "view_manifest.json", manifest)
    report = {
        "schema": SCHEMA,
        "source": before,
        "source_after": after,
        "eligible_authored_groups": len(authored),
        "envelopes": len(envelopes),
        "expected_channels": len(CHANNELS),
        "suppressed_channels": list(SUPPRESSED_CHANNELS),
        "visualizations": len(manifest["artifacts"]),
        "status_counts": {status: sum(1 for item in envelopes if _plain(item.raw_status) == status) for status in ("computed", "partial", "invalid", "not_available")},
        "composition": None,
        "potential": None,
        "strength": None,
        "candidate": None,
        "winner": None,
        "read_only": True,
        "synthetic_input": False,
    }
    _write(run_dir / "report.json", report)
    if len(envelopes) != len(authored) or len(manifest["artifacts"]) != len(envelopes) * len(CHANNELS):
        raise AssertionError("trend package coverage does not match authored group/channel coverage")
    return run_dir


def main() -> None:
    """Run the current-IFC diagnostic and print its artifact directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ifc", type=Path, default=DEFAULT_IFC)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/design/group_trend_alignment_field_ifc")
    args = parser.parse_args()
    run_dir = run(args.ifc.resolve(), args.output_root.resolve())
    print(json.dumps({"status": "pass", "run_dir": str(run_dir), "source": _fingerprint(args.ifc.resolve())}, sort_keys=True))


if __name__ == "__main__":
    main()
