"""Build a bounded D6 soft-field and empty-space diagnostic bundle.

This experiment consumes the already verified, read-only furniture-group and
wall projections from the real IFC experiment. It produces relative evidence
for review; it does not select a production domain, topology backend, or
threshold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import unary_union


SCHEMA = "d6-space-field-soft-field-experiment/v1"
ROOT = Path(__file__).resolve().parents[4]
SOURCE_RUN = ROOT / "outputs/design/space_field_zone_visual_experiment/run_001"
SOURCE_IFC = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"


def _sha256(path: Path) -> str:
    """Return a streaming SHA-256 digest for one source or artifact file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    """Read a UTF-8 JSON artifact without changing its source bytes."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    """Write deterministic UTF-8 JSON for an auditable experiment artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _percentile(values: list[float], fraction: float) -> float:
    """Return a deterministic linear percentile for non-empty numeric values."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * max(0.0, min(1.0, fraction))
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return float(ordered[lower])
    weight = index - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def _rank_percentiles(values: dict[str, float], *, reverse: bool = False) -> dict[str, float]:
    """Map values to stable zero-to-one rank percentiles for relative comparison."""
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]), reverse=reverse)
    if len(ordered) <= 1:
        return {key: 0.5 for key, _ in ordered}
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        percentile = ((index + end - 1) / 2) / (len(ordered) - 1)
        for key, _ in ordered[index:end]:
            ranks[key] = percentile
        index = end
    return ranks


def _polygon(parts: list[list[list[float]]]) -> object:
    """Rebuild a valid union from serialized polygon rings."""
    polygons = []
    for ring in parts:
        if len(ring) < 4:
            continue
        candidate = Polygon([(float(point[0]), float(point[1])) for point in ring])
        if not candidate.is_empty and candidate.is_valid and candidate.area > 1e-12:
            polygons.append(candidate)
    return unary_union(polygons) if polygons else Polygon()


def _frame(groups: list[dict[str, Any]], walls: dict[str, Any]) -> tuple[object, dict[str, Any]]:
    """Build a provisional view frame from source geometry extents only."""
    points: list[tuple[float, float]] = []
    for group in groups:
        for ring in group.get("geometry_parts", []):
            points.extend((float(point[0]), float(point[1])) for point in ring)
    for wall in walls.get("walls", []):
        for ring in wall.get("outlines_xy_m", []):
            points.extend((float(point[0]), float(point[1])) for point in ring)
    if len(points) < 3:
        raise RuntimeError("No geometry is available for the provisional diagnostic frame.")
    bounds = MultiPoint(points).bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    margin_fraction = 0.05
    frame = box(
        bounds[0] - width * margin_fraction,
        bounds[1] - height * margin_fraction,
        bounds[2] + width * margin_fraction,
        bounds[3] + height * margin_fraction,
    )
    return frame, {
        "basis": "bounding extent of extracted furniture_group footprints plus physical wall projections",
        "margin_fraction": margin_fraction,
        "status": "diagnostic_only",
        "owner_confirmed": False,
        "analysis_domain": "not_available",
        "is_room_boundary": False,
        "source_extent_is_not_true_boundary": True,
    }


def _grid(frame: object, columns: int, rows: int, origin_shift: tuple[float, float] = (0.0, 0.0)) -> dict[str, Any]:
    """Return a deterministic display grid and its origin/spacing metadata."""
    xmin, ymin, xmax, ymax = map(float, frame.bounds)
    dx = (xmax - xmin) / columns
    dy = (ymax - ymin) / rows
    return {
        "columns": columns,
        "rows": rows,
        "origin_m": [xmin + dx * origin_shift[0], ymin + dy * origin_shift[1]],
        "origin_shift_fraction_of_cell": list(origin_shift),
        "cell_size_m": [dx, dy],
        "frame_bounds_m": [xmin, ymin, xmax, ymax],
        "purpose": "display_and_relative_profile_only; sampled topology is not free-space truth",
    }


def _centers(grid: dict[str, Any]) -> list[tuple[float, float]]:
    """Enumerate grid cell centers using the recorded display origin."""
    xmin, ymin, _, _ = grid["frame_bounds_m"]
    dx, dy = grid["cell_size_m"]
    ox, oy = grid["origin_m"]
    return [
        (ox + (column + 0.5) * dx, oy + (row + 0.5) * dy)
        for row in range(grid["rows"])
        for column in range(grid["columns"])
        if xmin <= ox + (column + 0.5) * dx <= grid["frame_bounds_m"][2]
        and ymin <= oy + (row + 0.5) * dy <= grid["frame_bounds_m"][3]
    ]


def _node_geometry(groups: list[dict[str, Any]]) -> dict[str, object]:
    """Rebuild one exact, unsplit geometry per authored group."""
    return {group["group_id"]: _polygon(group["geometry_parts"]) for group in groups}


def _relations(groups: list[dict[str, Any]], relation_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute node compactness and continuous pair support from relative gaps."""
    usable = [record for record in relation_records if record.get("status") == "computed"]
    by_id = {group["group_id"]: group for group in groups}
    gaps: dict[str, list[float]] = {group["group_id"]: [] for group in groups}
    for record in usable:
        gaps[record["left"]].append(float(record["normalized_gap"]))
        gaps[record["right"]].append(float(record["normalized_gap"]))
    nearest = {key: min(values) for key, values in gaps.items() if values}
    compactness = _rank_percentiles(nearest, reverse=False)
    # Data-derived bandwidth preserves relative evidence without a metre cutoff.
    positive_nearest = [value for value in nearest.values() if value > 1e-12]
    # Touching group envelopes are retained as strong support; positive gaps
    # provide the relative bandwidth so zero gaps do not collapse the field.
    scale = max(_percentile(positive_nearest, 0.5) if positive_nearest else 1.0, 1e-9)
    pairs = []
    for record in usable:
        relative_gap = float(record["normalized_gap"])
        support = math.exp(-relative_gap / scale)
        pairs.append({
            "left": record["left"],
            "right": record["right"],
            "normalized_gap": relative_gap,
            "support_score": support,
            "relative_rank": None,
            "z_compatible": record.get("z_compatible"),
        })
    pair_ranks = _rank_percentiles({f"{p['left']}|{p['right']}": p["normalized_gap"] for p in pairs})
    for pair in pairs:
        pair["relative_rank"] = pair_ranks[f"{pair['left']}|{pair['right']}"]
    nearest_records = []
    for group_id, value in nearest.items():
        nearest_records.append({
            "group_id": group_id,
            "centroid_m": by_id[group_id]["centroid_m"],
            "nearest_normalized_gap": value,
            "compactness_rank": compactness[group_id],
            "support_score": 1.0 - compactness[group_id],
        })
    return {
        "node_compactness": sorted(nearest_records, key=lambda item: item["group_id"]),
        "pair_support": sorted(pairs, key=lambda item: (item["left"], item["right"])),
        "bandwidth": {
            "definition": "median positive nearest-neighbour normalized boundary gap",
            "value_relative": scale,
            "fixed_metre_threshold": False,
        },
        "computed_pair_count": len(usable),
        "all_pair_count": len(relation_records),
    }


def _support_cells(groups: list[dict[str, Any]], relations: dict[str, Any], frame: object, grid: dict[str, Any]) -> list[dict[str, Any]]:
    """Sample a smooth display-only support field at cell centers."""
    centroids = [(g["group_id"], Point(g["centroid_m"])) for g in groups]
    scale = relations["bandwidth"]["value_relative"]
    # Convert relative group gap bandwidth to a display distance using the median centroid spacing.
    centroid_distances = []
    for index, (_, left) in enumerate(centroids):
        centroid_distances.extend(left.distance(right) for _, right in centroids[index + 1 :])
    spatial_scale = max(_percentile(centroid_distances, 0.15) * max(scale, 0.25), 1e-6)
    cells = []
    for x, y in _centers(grid):
        values = [math.exp(-((Point((x, y)).distance(point) / spatial_scale) ** 2)) for _, point in centroids]
        raw = sum(values)
        cells.append({"x_m": x, "y_m": y, "support_raw": raw})
    maximum = max((cell["support_raw"] for cell in cells), default=1.0)
    for cell in cells:
        cell["support_score"] = cell["support_raw"] / maximum if maximum else 0.0
    return cells


def _empty_space(groups: list[dict[str, Any]], frame: object, grid: dict[str, Any]) -> dict[str, Any]:
    """Describe a bounded empty-space candidate without calling it a room or route."""
    geometries = _node_geometry(groups)
    furniture_union = unary_union([geometry for geometry in geometries.values() if not geometry.is_empty])
    candidate = frame.difference(furniture_union)
    components = list(candidate.geoms) if candidate.geom_type == "MultiPolygon" else [candidate]
    components = [component for component in components if not component.is_empty and component.area > 1e-12]
    samples = []
    for x, y in _centers(grid):
        point = Point(x, y)
        if not frame.covers(point) or furniture_union.covers(point):
            continue
        clearance = point.distance(furniture_union.boundary) if not furniture_union.is_empty else 0.0
        samples.append({"x_m": x, "y_m": y, "clearance_proxy_m": float(clearance)})
    clearance_values = [item["clearance_proxy_m"] for item in samples if item["clearance_proxy_m"] > 0.0]
    median_clearance = max(_percentile(clearance_values, 0.5), 1e-9)
    for sample in samples:
        sample["relative_clearance"] = sample["clearance_proxy_m"] / median_clearance
    width_values = [2.0 * value for value in clearance_values]
    adjacent = [group_id for group_id, geometry in geometries.items() if not geometry.is_empty and candidate.boundary.intersects(geometry)]
    return {
        "candidate_id": "empty_space_candidate:provisional_frame_complement",
        "diagnostic_attribute": "empty_space_field",
        "status": "diagnostic_only",
        "owner_confirmed": False,
        "geometry_parts": [
            [[float(x), float(y)] for x, y in component.exterior.coords]
            for component in components
        ],
        "free_area_m2": float(candidate.area),
        "continuity": {
            "component_count": len(components),
            "component_area_m2": [float(component.area) for component in components],
            "interpretation": "bounded diagnostic complement; sampled topology is not a true free-space result",
        },
        "adjacent_furniture_group_ids": sorted(adjacent),
        "local_width_proxy_m": {
            "definition": "two times point-to-furniture-boundary clearance at display-grid samples",
            "p10": _percentile(width_values, 0.10),
            "p50": _percentile(width_values, 0.50),
            "p90": _percentile(width_values, 0.90),
            "min": min(width_values) if width_values else None,
            "max": max(width_values) if width_values else None,
            "unit": "m",
            "semantic_limit": "relative local width evidence; not route width or walkability",
        },
        "bottleneck_evidence": {
            "definition": "lowest relative-clearance display samples",
            "relative_rank_only": True,
            "sample_count": len(samples),
            "lowest_samples": sorted(samples, key=lambda item: item["relative_clearance"])[:12],
        },
        "boundary_source": {
            "frame": "provisional diagnostic view frame",
            "frame_basis": "walls plus furniture extents with relative margin",
            "furniture_boundary": "exact authored group footprint union",
            "walls": "context/reference and physical geometry retained; not silently promoted to AnalysisDomain",
        },
        "samples": samples,
    }


def _sensitivity(groups: list[dict[str, Any]], relations: dict[str, Any], frame: object) -> dict[str, Any]:
    """Record resolution and origin sensitivity for display-only sampling."""
    variants = []
    for columns, rows, shift in ((72, 54, (0.0, 0.0)), (54, 40, (0.0, 0.0)), (72, 54, (0.25, 0.25))):
        grid = _grid(frame, columns, rows, shift)
        field = _support_cells(groups, relations, frame, grid)
        empty = _empty_space(groups, frame, grid)
        variants.append({
            "grid": grid,
            "support_cell_count": len(field),
            "empty_sample_count": len(empty["samples"]),
            "empty_component_count": empty["continuity"]["component_count"],
            "empty_area_m2": empty["free_area_m2"],
            "local_width_p50_m": empty["local_width_proxy_m"]["p50"],
        })
    return {
        "variants": variants,
        "interpretation": "display sensitivity only; no sampled topology is promoted to truth or production resolution",
        "production_resolution_selected": False,
        "origin_sensitivity_recorded": True,
    }


def _hard_alignment(candidates: list[dict[str, Any]], groups: list[dict[str, Any]], relations: dict[str, Any]) -> list[dict[str, Any]]:
    """Relate existing 1/2/3/4-region cuts to continuous node and edge evidence."""
    compactness = {item["group_id"]: item for item in relations["node_compactness"]}
    pair_support = {
        tuple(sorted((item["left"], item["right"]))): item
        for item in relations["pair_support"]
    }
    output = []
    for candidate in candidates:
        region_records = []
        for region in candidate["regions"]:
            ids = region["group_ids"]
            scores = [compactness[group_id]["support_score"] for group_id in ids]
            region_records.append({
                "region_id": region["region_id"],
                "group_ids": ids,
                "group_count": len(ids),
                "mean_node_support": sum(scores) / len(scores) if scores else None,
                "min_node_support": min(scores) if scores else None,
                "max_node_support": max(scores) if scores else None,
            })
        cuts = []
        for edge in candidate["cut_edges"]:
            pair = pair_support.get(tuple(sorted((edge["left"], edge["right"]))))
            cuts.append({
                **edge,
                "continuous_pair_support": None if pair is None else pair["support_score"],
                "continuous_pair_rank": None if pair is None else pair["relative_rank"],
                "interpretation": "relative separation edge; no fixed metre cutoff",
            })
        output.append({
            "candidate_id": candidate["candidate_id"],
            "region_count": candidate["region_count"],
            "cuts": cuts,
            "regions": region_records,
            "relation_to_soft_field": "hard candidate is a discrete view of ranked relative gaps; soft field retains gradients between nodes",
        })
    return output


def run(output: Path) -> dict[str, Any]:
    """Generate the JSON evidence bundle for one output directory."""
    output.mkdir(parents=True, exist_ok=True)
    render_input = _read_json(SOURCE_RUN / "render_input.json")
    walls = _read_json(SOURCE_RUN / "physical_wall_plan_projection.json")
    if _sha256(SOURCE_IFC) != render_input["source_summary"]["source_ifc"]["sha256"]:
        raise RuntimeError("Source IFC hash differs from the existing real-IFC inventory.")
    groups = render_input["groups"]
    candidates = render_input["candidates"]
    relations = _relations(groups, _read_json(SOURCE_RUN / "group_relation_evidence.json")["relations"])
    frame, frame_record = _frame(groups, walls)
    display_grid = _grid(frame, 72, 54)
    support_cells = _support_cells(groups, relations, frame, display_grid)
    empty = _empty_space(groups, frame, display_grid)
    sensitivity = _sensitivity(groups, relations, frame)
    hard_alignment = _hard_alignment(candidates, groups, relations)

    field = {
        "schema": "d6-space-field-soft-field/v1",
        "diagnostic_representation": "A",
        "diagnostic_attribute": "furniture_group_support_field",
        "status": "diagnostic_only",
        "owner_confirmed": False,
        "source_ifc": render_input["source_summary"]["source_ifc"],
        "analysis_nodes": {
            "selection_rule": 'exact ObjectType == "furniture_group"',
            "group_count": len(groups),
            "member_count": sum(group["member_count"] for group in groups),
            "members_are_not_split": True,
        },
        "frame": frame_record,
        "relations": relations,
        "grid": display_grid,
        "support_cells": support_cells,
        "resolution_origin_sensitivity": sensitivity,
        "hard_candidate_alignment": hard_alignment,
        "not_inferred": ["room", "activity role", "corridor", "route", "walkability", "visibility", "accuracy", "production selector"],
    }
    empty_payload = {
        "schema": "d6-space-field-empty-space-diagnostic/v1",
        "diagnostic_representation": "B",
        "source_ifc": render_input["source_summary"]["source_ifc"],
        "frame": frame_record,
        "empty_space": empty,
        "grid": display_grid,
        "resolution_origin_sensitivity": sensitivity,
        "hard_candidate_alignment": hard_alignment,
        "not_inferred": ["corridor", "activity area", "route", "walkability", "visibility", "real room boundary", "production free-space truth"],
    }
    _write_json(output / "soft_field_candidates.json", field)
    _write_json(output / "empty_space_candidates.json", empty_payload)
    _write_json(output / "hard_candidate_alignment.json", {"schema": "d6-space-field-hard-candidate-alignment/v1", "candidates": hard_alignment})
    _write_json(output / "render_input.json", {"schema": SCHEMA, "source_run": str(SOURCE_RUN), "source_summary": render_input["source_summary"], "groups": groups, "context": render_input["context"], "candidates": candidates, "walls": walls["walls"], "field": field, "empty_space": empty_payload})
    _write_json(output / "provenance.json", {
        "schema": "d6-space-field-soft-field-provenance/v1",
        "source_ifc": {"path": str(SOURCE_IFC.resolve()), "sha256": _sha256(SOURCE_IFC), "read_only": True},
        "reused_read_only_inputs": [
            str((SOURCE_RUN / "render_input.json").resolve()),
            str((SOURCE_RUN / "physical_wall_plan_projection.json").resolve()),
            str((SOURCE_RUN / "group_relation_evidence.json").resolve()),
            str((ROOT / "scripts/design/space_field/run_space_field_probe.py").resolve()),
            str((ROOT / "scripts/design/group_level/run_inferred_group_candidate_field_probe.py").resolve()),
            str((ROOT / "scripts/design/group_level/inferred_group_candidate_field_truth.json").resolve()),
            str((ROOT / "outputs/design/space_field_zone_visual_experiment/run_001/generate_zone_experiment.py").resolve()),
            str((ROOT / "docs/project/space-field-ifc-neutral-scene-input-contract.md").resolve()),
            str((ROOT / "docs/project/evidence/d6-space-field-boundary-construction-experiment.md").resolve()),
            str((ROOT / "docs/project/evidence/d6-space-field-zone-visual-experiment.md").resolve()),
            str((ROOT / "docs/project/evidence/d6-space-field-zone-owner-visual-review.md").resolve()),
            str((ROOT / "docs/project/evidence/d6-space-field-input-contract-owner-decision.md").resolve()),
        ],
        "current_blender": {
            "observed": bool(render_input["source_summary"]["current_blender_identity"]["observed"]),
            "basis": "existing live Blender input inspection retained in source_summary.json",
            "source_path_match": bool(render_input["source_summary"]["current_blender_identity"]["source_path_match"]),
            "this_experiment_opened_current_blender": False,
            "portable_blender_for_disposable_render": "D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe",
        },
        "observed_facts": ["IFC4", "37 exact furniture_group nodes", "95 grouped furniture members", "11 walls", "6 doors", "0 IfcSpace", "0 opening/void/fills relations"],
        "derived_diagnostics": ["relative node support", "pair support", "provisional frame complement", "sampled clearance profiles", "hard candidate alignment"],
        "assumptions": ["frame is diagnostic only", "furniture groups remain indivisible", "walls remain context/reference and physical geometry", "sampled topology is not free-space truth"],
        "owner_review_gate": "STOP FOR SOFT-FIELD OWNER VISUAL REVIEW",
    })
    _write_json(output / "scope_audit.json", {
        "schema": "d6-space-field-soft-field-scope-audit/v1",
        "allowed": {
            "real_ifc_source": True,
            "exact_furniture_group_nodes_only": True,
            "group_members_split": False,
            "walls_retained_as_context_reference": True,
            "provisional_diagnostic_frame_labeled": True,
            "empty_space_independent_attribute": True,
            "hard_candidates_1_2_3_4_displayed": True,
            "soft_field_and_empty_space_displayed": True,
        },
        "forbidden_or_not_selected": {
            "production_code_modified": False,
            "adapter_modified": False,
            "formal_tests_modified": False,
            "source_ifc_modified": False,
            "user_blender_file_modified": False,
            "analysis_domain_selected": False,
            "fixed_metre_threshold_selected": False,
            "production_resolution_selected": False,
            "route_width_selected": False,
            "bayesian_or_ml_selected": False,
            "walkability_visibility_route_accuracy_emitted": False,
            "authored_membership_rewritten": False,
        },
        "current_blender_observation": render_input["source_summary"]["current_blender_identity"],
    })
    _write_json(output / "json_schema.json", {
        "schema": "d6-space-field-soft-field-json-contract/v1",
        "required_artifacts": ["soft_field_candidates.json", "empty_space_candidates.json", "hard_candidate_alignment.json", "render_input.json", "provenance.json", "scope_audit.json"],
        "required_fields": {"soft_field_candidates.json": ["schema", "source_ifc", "analysis_nodes", "frame", "relations", "grid", "support_cells", "resolution_origin_sensitivity"], "empty_space_candidates.json": ["schema", "source_ifc", "frame", "empty_space", "grid", "resolution_origin_sensitivity"]},
        "schema_status": "experiment-local contract; not a production API",
    })
    return {"status": "pass", "output": str(output), "group_count": len(groups), "empty_component_count": empty["continuity"]["component_count"]}


def main() -> int:
    """Parse output arguments and run the bounded experiment."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
