"""Run single-furniture frame analysis against an IFC4 source file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

try:
    from ...adapters.ifc_bonsai import load_ifc_neutral_scene
    from ...features.furniture_frame import infer_furniture_frame
except ImportError:
    # Keep the acceptance runner usable as a direct repository-root command.
    import sys

    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from adapters.ifc_bonsai import load_ifc_neutral_scene
    from features.furniture_frame import infer_furniture_frame


def _mesh_by_id(scene: object) -> dict[str, object]:
    """Index neutral meshes so frame analysis never re-reads IFC geometry."""
    return {mesh.id: mesh for mesh in scene.geometries}


def _mesh_for_source(meshes: dict[str, object], source_object: object) -> object | None:
    """Resolve the first mesh referenced by one neutral source object."""
    return next(
        (meshes[geometry_id] for geometry_id in source_object.geometry_refs if geometry_id in meshes),
        None,
    )


def _angle_delta(first: float, second: float) -> float:
    """Return the smallest unsigned difference between two undirected axes."""
    delta = abs((first - second) % 180.0)
    return min(delta, 180.0 - delta)


def build_frame_report(source_path: Path) -> dict[str, Any]:
    """Load IFC facts and calculate one independent two-axis frame per furniture."""
    scene = load_ifc_neutral_scene(source_path)
    meshes = _mesh_by_id(scene)
    records = {
        item.source_id: item
        for item in scene.source_objects
        if item.source_class == "IfcFurniture"
        and item.source_role == "furniture"
        and not item.source_id.endswith(":analysis")
    }
    analysis_records = {
        item.source_id.removesuffix(":analysis"): item
        for item in scene.source_objects
        if item.source_role == "analysis_substitute"
        and item.source_id.endswith(":analysis")
    }

    furniture_results: list[dict[str, Any]] = []
    missing_analysis: list[str] = []
    missing_geometry: list[str] = []
    for source_id, record in sorted(records.items()):
        analysis_record = analysis_records.get(source_id)
        if analysis_record is None:
            missing_analysis.append(source_id)
            continue
        analysis_mesh = _mesh_for_source(meshes, analysis_record)
        body_mesh = _mesh_for_source(meshes, record)
        if analysis_mesh is None or body_mesh is None:
            missing_geometry.append(source_id)
            continue
        analysis_frame = infer_furniture_frame(analysis_mesh)
        body_frame = infer_furniture_frame(body_mesh)
        furniture_results.append(
            {
                "source_id": source_id,
                "type_ref": record.type_ref,
                "analysis_frame": analysis_frame,
                "body_cross_check": {
                    "primary_angle_degrees": body_frame["primary_angle_degrees"],
                    "orientation_strength": body_frame["orientation_strength"],
                    "angle_delta_degrees": _angle_delta(
                        analysis_frame["primary_angle_degrees"],
                        body_frame["primary_angle_degrees"],
                    ),
                },
            }
        )

    strengths = [
        item["analysis_frame"]["orientation_strength"]
        for item in furniture_results
    ]
    report = {
        "contract": {
            "name": "ifc_single_furniture_frame_analysis",
            "version": 1,
            "input_geometry": "Analysis MassPatch",
            "secondary_cross_check": "Body",
            "deferred": ["affordance", "regions", "paths", "groups", "scores"],
        },
        "source": {"path": str(source_path), "schema": scene.context.source_schema},
        "scene": {
            "formal_furniture_count": len(records),
            "frame_result_count": len(furniture_results),
            "analysis_domain_available": scene.analysis_domain is not None,
            "authored_affordance_count": len(scene.authored_affordances),
        },
        "summary": {
            "orientation_strength_min": min(strengths) if strengths else None,
            "orientation_strength_max": max(strengths) if strengths else None,
            "orientation_strength_mean": mean(strengths) if strengths else None,
            "orientation_strength_median": median(strengths) if strengths else None,
            "analysis_missing_count": len(missing_analysis),
            "geometry_missing_count": len(missing_geometry),
        },
        "missing_analysis": missing_analysis,
        "missing_geometry": missing_geometry,
        "furniture": furniture_results,
        "status": "passed"
        if len(furniture_results) == len(records)
        else "failed",
    }
    return report


def main() -> None:
    """Parse paths, run frame analysis, and write a stable JSON report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_frame_report(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "status": report["status"]}))


if __name__ == "__main__":
    main()
