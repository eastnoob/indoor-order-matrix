"""Run read-only IFC furniture and MassPatch preflight checks.

This checkpoint intentionally stops before affordance, region, path, or scoring
inference. It verifies only the factual IFC handoff and the pairing of one
furniture occurrence with its own Analysis representation.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

try:
    from ...adapters.ifc_bonsai import load_ifc_neutral_scene
except ImportError:
    # Keep direct script execution usable from the repository root without
    # duplicating the IFC adapter or changing its import contract.
    import sys

    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from adapters.ifc_bonsai import load_ifc_neutral_scene


def _mesh_for_object(scene: object, source_object: object) -> object | None:
    """Resolve the first referenced mesh for one neutral source object."""
    geometry_by_id = {mesh.id: mesh for mesh in scene.geometries}
    for geometry_id in source_object.geometry_refs:
        mesh = geometry_by_id.get(geometry_id)
        if mesh is not None:
            return mesh
    return None


def _bbox(mesh: object) -> dict[str, Any]:
    """Return world-space bounds and scale facts for one neutral mesh."""
    if not mesh.vertices:
        raise ValueError(f"mesh {mesh.id} has no vertices")
    minimum = tuple(min(vertex[index] for vertex in mesh.vertices) for index in range(3))
    maximum = tuple(max(vertex[index] for vertex in mesh.vertices) for index in range(3))
    dimensions = tuple(maximum[index] - minimum[index] for index in range(3))
    center = tuple((minimum[index] + maximum[index]) / 2.0 for index in range(3))
    diagonal = math.sqrt(sum(value * value for value in dimensions))
    return {
        "min": minimum,
        "max": maximum,
        "dimensions": dimensions,
        "center": center,
        "diagonal": diagonal,
        "vertex_count": len(mesh.vertices),
        "triangle_count": len(mesh.triangle_indices),
        "is_manifold": mesh.is_manifold,
        "is_closed": mesh.is_closed,
    }


def _bbox_overlap_ratio(first: dict[str, Any], second: dict[str, Any]) -> float:
    """Measure axis-aligned overlap relative to the smaller bounding box.

    This is a descriptive geometry check, not a pass/fail perceptual score.
    Zero-thickness axes are treated as coincident only when both boxes share
    that zero extent, which avoids inventing volume for planar evidence.
    """
    overlap = []
    denominator = []
    for axis in range(3):
        first_extent = float(first["dimensions"][axis])
        second_extent = float(second["dimensions"][axis])
        low = max(float(first["min"][axis]), float(second["min"][axis]))
        high = min(float(first["max"][axis]), float(second["max"][axis]))
        shared = max(0.0, high - low)
        if min(first_extent, second_extent) == 0.0:
            overlap.append(1.0 if first_extent == second_extent == 0.0 else 0.0)
            denominator.append(1.0)
        else:
            overlap.append(shared)
            denominator.append(min(first_extent, second_extent))
    return math.prod(overlap) / math.prod(denominator)


def _normalized_center_distance(first: dict[str, Any], second: dict[str, Any]) -> float:
    """Return center separation normalized by the larger object diagonal."""
    delta = tuple(
        float(first["center"][axis]) - float(second["center"][axis])
        for axis in range(3)
    )
    distance = math.sqrt(sum(value * value for value in delta))
    scale = max(float(first["diagonal"]), float(second["diagonal"]), 1e-12)
    return distance / scale


def _source_role_counts(scene: object) -> dict[str, int]:
    """Count source records by their neutral semantic role."""
    counts: dict[str, int] = {}
    for source_object in scene.source_objects:
        role = source_object.source_role or "unknown"
        counts[role] = counts.get(role, 0) + 1
    return dict(sorted(counts.items()))


def build_preflight_report(source_path: Path, sample_size: int = 6) -> dict[str, Any]:
    """Load an IFC file and report factual furniture/Analysis handoff checks."""
    scene = load_ifc_neutral_scene(source_path)
    source_objects = tuple(scene.source_objects)
    furniture = tuple(
        item
        for item in source_objects
        if item.source_class == "IfcFurniture"
        and item.source_role == "furniture"
        and not item.source_id.endswith(":analysis")
    )
    analysis = {
        item.source_id.removesuffix(":analysis"): item
        for item in source_objects
        if item.source_role == "analysis_substitute"
        and item.source_id.endswith(":analysis")
    }
    geometry_count = len(scene.geometries)
    samples: list[dict[str, Any]] = []
    sampled_type_refs: set[str] = set()
    missing_analysis: list[str] = []
    missing_body_geometry: list[str] = []
    missing_analysis_geometry: list[str] = []

    for item in furniture:
        base_id = item.source_id
        analysis_item = analysis.get(base_id)
        if analysis_item is None:
            missing_analysis.append(base_id)
            continue
        body_mesh = _mesh_for_object(scene, item)
        analysis_mesh = _mesh_for_object(scene, analysis_item)
        if body_mesh is None:
            missing_body_geometry.append(base_id)
        if analysis_mesh is None:
            missing_analysis_geometry.append(base_id)
        sample_key = item.type_ref or "untyped-family"
        # Prefer one representative per authored type family so the preflight
        # visibly covers both tables and chairs rather than only file ordering.
        should_sample = (
            body_mesh is not None
            and analysis_mesh is not None
            and (
                sample_key not in sampled_type_refs
                or len(samples) < min(sample_size, len(sampled_type_refs) + 1)
            )
        )
        if len(samples) < sample_size and should_sample:
            body_box = _bbox(body_mesh)
            analysis_box = _bbox(analysis_mesh)
            sampled_type_refs.add(sample_key)
            samples.append(
                {
                    "source_id": base_id,
                    "type_ref": item.type_ref,
                    "body": body_box,
                    "analysis": analysis_box,
                    "bbox_overlap_ratio": _bbox_overlap_ratio(body_box, analysis_box),
                    "normalized_center_distance": _normalized_center_distance(
                        body_box, analysis_box
                    ),
                }
            )

    report = {
        "contract": {
            "name": "ifc_furniture_analysis_preflight",
            "version": 1,
            "scope": ["ifc_read", "furniture_selection", "analysis_pairing", "geometry_facts"],
            "deferred": ["affordance", "regions", "paths", "groups", "scores"],
        },
        "source": {"path": str(source_path), "schema": scene.context.source_schema},
        "scene": {
            "source_object_count": len(source_objects),
            "geometry_count": geometry_count,
            "source_role_counts": _source_role_counts(scene),
            "authored_affordance_count": len(scene.authored_affordances),
            "analysis_domain_available": scene.analysis_domain is not None,
        },
        "furniture": {
            "formal_count": len(furniture),
            "with_analysis_representation": len(furniture) - len(missing_analysis),
            "missing_analysis": missing_analysis,
            "missing_body_geometry": missing_body_geometry,
            "missing_analysis_geometry": missing_analysis_geometry,
            "sample_pair_checks": samples,
        },
        "status": "passed"
        if not missing_analysis and not missing_body_geometry and not missing_analysis_geometry
        else "failed",
    }
    return report


def main() -> None:
    """Parse paths and write the read-only IFC preflight report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample-size", type=int, default=6)
    args = parser.parse_args()
    report = build_preflight_report(args.source, sample_size=args.sample_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "status": report["status"]}))


if __name__ == "__main__":
    main()
