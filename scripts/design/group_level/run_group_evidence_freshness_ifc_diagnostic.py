"""Run a bounded evidence-package freshness diagnostic against the pinned IFC."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from dataclasses import replace
from html import escape
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.field_core import (  # noqa: E402
    build_evidence_package_contract,
    evaluate_evidence_package_freshness,
    fingerprint_evidence_dependency,
)
from scripts.design.group_level.run_group_trend_alignment_field_ifc import (  # noqa: E402
    DEFAULT_IFC,
    _build_scene,
    _fingerprint,
    _plain,
)
from features.group_self_description import describe_group_relations  # noqa: E402
from features.scene_contract import MeshGeometry3D, NeutralSceneV2  # noqa: E402

SCHEMA = "group-evidence-freshness-ifc-diagnostic/v1"
PACKAGE_SCHEMA = "group-evidence-package/v1"
ROTATION_DEGREES = 17.0
EXPECTED_SOURCE_BYTES = 408618044
EXPECTED_SOURCE_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"


def _write(path: Path, value: Any) -> None:
    """Write deterministic JSON while keeping frozen contract values serializable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_plain(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _group_points(group: Mapping[str, Any]) -> list[tuple[float, float]]:
    """Collect all projected polygon vertices from one described furniture group."""
    points: list[tuple[float, float]] = []
    for member in group.get("member_geometry", ()):
        polygons = member.get("polygons") or ()
        if not polygons and member.get("points"):
            polygons = (member["points"],)
        for polygon in polygons:
            points.extend((float(point[0]), float(point[1])) for point in polygon)
    return points


def _rotate_description(
    description: Mapping[str, Any],
    target_id: str,
    angle_degrees: float,
) -> dict[str, Any]:
    """Rotate one existing group's projected polygons in memory around its centroid."""
    rotated = copy.deepcopy(dict(description))
    groups = rotated.get("group_geometry", ())
    selected = next((item for item in groups if item.get("target_id") == target_id), None)
    if selected is None:
        raise ValueError(f"group target not found: {target_id}")
    center_value = selected.get("center")
    points = _group_points(selected)
    if center_value is None:
        if not points:
            raise ValueError(f"selected group has no usable geometry: {target_id}")
        center_value = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
    cx, cy = float(center_value[0]), float(center_value[1])
    radians = math.radians(float(angle_degrees))
    cosine, sine = math.cos(radians), math.sin(radians)

    # Keep the source description intact and transform only the copied visual geometry.
    for member in selected.get("member_geometry", ()):
        polygons = member.get("polygons") or ()
        if polygons:
            transformed = []
            for polygon in polygons:
                transformed.append([
                    [
                        cx + cosine * (float(point[0]) - cx) - sine * (float(point[1]) - cy),
                        cy + sine * (float(point[0]) - cx) + cosine * (float(point[1]) - cy),
                    ]
                    for point in polygon
                ])
            member["polygons"] = transformed
        elif member.get("points"):
            member["points"] = [
                [
                    cx + cosine * (float(point[0]) - cx) - sine * (float(point[1]) - cy),
                    cy + sine * (float(point[0]) - cx) + cosine * (float(point[1]) - cy),
                ]
                for point in member["points"]
            ]
    return rotated


def _rotate_scene_geometry(
    scene: NeutralSceneV2,
    target_id: str,
    center_xy: tuple[float, float],
    angle_degrees: float,
) -> NeutralSceneV2:
    """Rotate a group's actual IFC Body and Analysis meshes in the scene value."""
    group = next((item for item in scene.authored_groups if item.id == target_id), None)
    if group is None:
        raise ValueError(f"authored group not found in scene: {target_id}")
    member_ids = set(group.member_refs)
    # Rotate both Body and Analysis meshes: geometry relation evidence reads
    # authored Body geometry, while trend evidence follows the typed Analysis substitute.
    member_geometry_ids = {
        geometry_ref
        for source in scene.source_objects
        if (source.id in member_ids or any(source.id == f"{member_id}:analysis" for member_id in member_ids))
        for geometry_ref in source.geometry_refs
    }
    if not member_geometry_ids:
        raise ValueError(f"selected group has no rotatable geometry: {target_id}")

    plane = scene.context.analysis_plane
    origin = plane.origin
    first, second, normal = plane.basis
    center_x, center_y = center_xy
    radians = math.radians(float(angle_degrees))
    cosine, sine = math.cos(radians), math.sin(radians)

    def rotate_vector(vector: tuple[float, float, float]) -> tuple[float, float, float]:
        """Rotate a vector around the analysis-plane normal without translating it."""
        x = sum(vector[index] * first[index] for index in range(3))
        y = sum(vector[index] * second[index] for index in range(3))
        z = sum(vector[index] * normal[index] for index in range(3))
        return tuple(
            (cosine * x - sine * y) * first[index]
            + (sine * x + cosine * y) * second[index]
            + z * normal[index]
            for index in range(3)
        )

    transformed: list[MeshGeometry3D] = []
    changed = 0
    for geometry in scene.geometries:
        if geometry.id not in member_geometry_ids:
            transformed.append(geometry)
            continue
        changed += 1
        vertices = []
        for vertex in geometry.vertices:
            relative = tuple(vertex[index] - origin[index] for index in range(3))
            x = sum(relative[index] * first[index] for index in range(3))
            y = sum(relative[index] * second[index] for index in range(3))
            z = sum(relative[index] * normal[index] for index in range(3))
            dx, dy = x - center_x, y - center_y
            rotated_x = center_x + cosine * dx - sine * dy
            rotated_y = center_y + sine * dx + cosine * dy
            vertices.append(tuple(
                origin[index]
                + rotated_x * first[index]
                + rotated_y * second[index]
                + z * normal[index]
                for index in range(3)
            ))
        transformed.append(
            replace(
                geometry,
                vertices=tuple(vertices),
                normals=tuple(rotate_vector(vector) for vector in geometry.normals),
            )
        )
    if changed == 0:
        raise ValueError(f"selected group's Body and Analysis meshes were not present in scene: {target_id}")
    return replace(scene, geometries=tuple(transformed))


def _plan_svg(
    description: Mapping[str, Any],
    *,
    source: Mapping[str, Any],
    plane: Mapping[str, Any],
    state: str,
    selected_target: str,
    rotation_degrees: float,
    footer_note: str = "Diagnostic only: visual freshness evidence; no recomputation or IFC mutation.",
) -> str:
    """Render a compact plan view from real IFC-derived group polygons."""
    groups = tuple(description.get("group_geometry", ()))
    all_points = [point for group in groups for point in _group_points(group)]
    if not all_points:
        raise ValueError("IFC group description has no projected polygon points")
    xmin = min(point[0] for point in all_points)
    ymin = min(point[1] for point in all_points)
    xmax = max(point[0] for point in all_points)
    ymax = max(point[1] for point in all_points)
    width, height, margin, footer = 1400, 950, 36, 100
    scale = min(
        (width - 2 * margin) / max(xmax - xmin, 1.0),
        (height - footer - 2 * margin) / max(ymax - ymin, 1.0),
    )

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map analysis-plane coordinates into the fixed SVG viewport."""
        return (
            margin + (point[0] - xmin) * scale,
            height - footer - margin - (point[1] - ymin) * scale,
        )

    markup: list[str] = []
    for group_index, group in enumerate(groups):
        target_id = str(group.get("target_id"))
        selected = target_id == selected_target
        fill = "#c1121f" if selected else ("#2a9d8f" if group_index % 2 == 0 else "#e9a23b")
        for member in group.get("member_geometry", ()):
            polygons = member.get("polygons") or ()
            if not polygons and member.get("points"):
                polygons = (member["points"],)
            for polygon in polygons:
                if not polygon:
                    continue
                projected = [project((float(point[0]), float(point[1]))) for point in polygon]
                path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in projected) + " Z"
                markup.append(
                    f'<path d="{path}" fill="{fill}" fill-opacity=".34" '
                    f'stroke="{fill}" stroke-width="1.1"><title>{escape(target_id)}</title></path>'
                )

    details = (
        f"state: {state}",
        f"rotated target: {selected_target}",
        f"rotation: {rotation_degrees:.1f} degrees",
        f"source sha256: {source.get('sha256')}",
        f"plane: {plane.get('name')} | units: {plane.get('unit')}",
        footer_note,
    )
    text = "".join(
        f'<text x="{margin}" y="{height - footer + 20 + index * 15}" '
        f'font-size="12">{escape(line)}</text>'
        for index, line in enumerate(details)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<title>{state} IFC furniture-group plan</title><rect width="100%" height="100%" fill="white"/>'
        f'{"".join(markup)}<line x1="0" y1="{height - footer}" x2="{width}" y2="{height - footer}" stroke="#bbb"/>'
        f'{text}</svg>'
    )


def _contract(
    *,
    scene: NeutralSceneV2,
    source_fingerprint: str,
    plane: Mapping[str, Any],
    target_ids: tuple[str, ...],
    selected_target: str,
) -> dict[str, Any]:
    """Build one package contract while changing only content-derived scene/model inputs."""
    scene_fingerprint = fingerprint_evidence_dependency(
        {
            "analysis_plane": scene.context.analysis_plane,
            "geometries": scene.geometries,
        }
    )
    selected_group = next(item for item in scene.authored_groups if item.id == selected_target)
    model_fingerprint = fingerprint_evidence_dependency(
        {
            "target_id": selected_target,
            "member_refs": selected_group.member_refs,
            "analysis_geometry": tuple(
                geometry
                for geometry in scene.geometries
                if any(
                    f"{member_ref}:analysis" in source.id
                    and geometry.id in source.geometry_refs
                    for member_ref in selected_group.member_refs
                    for source in scene.source_objects
                )
            ),
        }
    )
    stable = {
        "source": source_fingerprint,
        "plane": fingerprint_evidence_dependency(plane),
        "query": fingerprint_evidence_dependency({"frame": plane.get("name"), "tolerance": 1e-6}),
        "recipe": fingerprint_evidence_dependency({"renderer": SCHEMA, "rotation_policy": "deterministic_in_memory"}),
        "channels": fingerprint_evidence_dependency(("plan_geometry",)),
    }
    return build_evidence_package_contract(
        package_id="group-evidence-freshness-ifc",
        package_schema=PACKAGE_SCHEMA,
        producer="run_group_evidence_freshness_ifc_diagnostic",
        target_ids=target_ids,
        dependencies={"scene": scene_fingerprint, "model": model_fingerprint, **stable},
        algorithm_version="group-evidence-freshness-v1",
        schema_version=SCHEMA,
        artifacts={"analysis_plane": plane, "source_sha256": source_fingerprint},
    )


def run(source_path: Path, output_root: Path) -> Path:
    """Run the baseline, rotated, and restored freshness checks without editing the IFC."""
    before = _fingerprint(source_path)
    if before["byte_length"] != EXPECTED_SOURCE_BYTES or before["sha256"] != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("IFC source does not match the pinned diagnostic input")
    scene, _metadata, authored = _build_scene(source_path)
    description = describe_group_relations(scene)
    after = _fingerprint(source_path)
    if before != after:
        raise RuntimeError("pinned IFC changed during diagnostic extraction")

    geometry_groups = tuple(
        sorted(
            (group for group in description.get("group_geometry", ()) if _group_points(group)),
            key=lambda item: str(item.get("target_id")),
        )
    )
    if not geometry_groups:
        raise RuntimeError("no authored furniture group has usable projected geometry")
    selected_target = str(geometry_groups[0]["target_id"])
    rotated_description = _rotate_description(description, selected_target, ROTATION_DEGREES)
    selected_center = next(
        (float(group["center"][0]), float(group["center"][1]))
        for group in geometry_groups
        if group["target_id"] == selected_target and group.get("center") is not None
    )
    rotated_scene = _rotate_scene_geometry(
        scene, selected_target, selected_center, ROTATION_DEGREES
    )
    plane = _plain(scene.context.analysis_plane)
    target_ids = tuple(sorted(str(group["target_id"]) for group in description.get("group_geometry", ())))
    baseline_contract = _contract(
        scene=scene,
        source_fingerprint=str(before["sha256"]),
        plane=plane,
        target_ids=target_ids,
        selected_target=selected_target,
    )
    rotated_contract = _contract(
        scene=rotated_scene,
        source_fingerprint=str(before["sha256"]),
        plane=plane,
        target_ids=target_ids,
        selected_target=selected_target,
    )
    baseline_status = evaluate_evidence_package_freshness(
        cached_contract=baseline_contract, current_contract=baseline_contract, artifacts_available=True
    )
    rotated_status = evaluate_evidence_package_freshness(
        cached_contract=baseline_contract, current_contract=rotated_contract, artifacts_available=True
    )
    restored_status = evaluate_evidence_package_freshness(
        cached_contract=baseline_contract,
        current_contract=_contract(
            scene=scene,
            source_fingerprint=str(before["sha256"]),
            plane=plane,
            target_ids=target_ids,
            selected_target=selected_target,
        ),
        artifacts_available=True,
    )
    if baseline_status["freshness"] != "fresh":
        raise AssertionError(f"baseline package was not fresh: {baseline_status}")
    if rotated_status["freshness"] != "stale":
        raise AssertionError(f"rotated package was not stale: {rotated_status}")
    if restored_status["freshness"] != "fresh":
        raise AssertionError(f"restored package was not fresh: {restored_status}")
    reason_codes = {reason["code"] for reason in rotated_status["reasons"]}
    if not reason_codes.intersection({"scene_changed", "model_changed"}):
        raise AssertionError(f"rotated package did not report content change: {rotated_status}")
    if tuple(rotated_status["affected_targets"]) != target_ids:
        raise AssertionError("whole-package invalidation did not include every group target")

    run_dir = output_root / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    baseline_svg = run_dir / "baseline_plan.svg"
    rotated_svg = run_dir / "rotated_plan.svg"
    baseline_svg.write_text(
        _plan_svg(description, source=before, plane=plane, state="baseline", selected_target=selected_target, rotation_degrees=0.0),
        encoding="utf-8",
    )
    rotated_svg.write_text(
        _plan_svg(rotated_description, source=before, plane=plane, state="rotated", selected_target=selected_target, rotation_degrees=ROTATION_DEGREES),
        encoding="utf-8",
    )
    final_source = _fingerprint(source_path)
    if final_source != before:
        raise RuntimeError("pinned IFC changed during freshness artifact generation")
    manifest = {
        "schema": SCHEMA,
        "source": before,
        "source_after": after,
        "source_final": final_source,
        "analysis_plane": plane,
        "authored_group_count": len(authored),
        "target_ids": target_ids,
        "selected_target": selected_target,
        "rotation_degrees": ROTATION_DEGREES,
        "baseline_svg": str(baseline_svg.resolve()),
        "rotated_svg": str(rotated_svg.resolve()),
        "baseline_contract": baseline_contract,
        "rotated_contract": rotated_contract,
        "statuses": {
            "baseline": baseline_status,
            "rotated": rotated_status,
            "restored": restored_status,
        },
        "read_only": True,
        "synthetic_input": False,
    }
    _write(run_dir / "freshness_diagnostic.json", manifest)
    return run_dir


def main() -> None:
    """Run the pinned IFC freshness diagnostic and print its artifact directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ifc", type=Path, default=DEFAULT_IFC)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/design/group_evidence_freshness_ifc")
    args = parser.parse_args()
    run_dir = run(args.ifc.resolve(), args.output_root.resolve())
    print(json.dumps({"status": "pass", "run_dir": str(run_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
