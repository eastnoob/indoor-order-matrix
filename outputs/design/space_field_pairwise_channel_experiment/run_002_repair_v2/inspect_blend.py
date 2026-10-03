"""Read back the disposable run_002 Blender scene and its labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def inspect(blend: Path, output: Path) -> None:
    """Verify object inventory and required semantic labels."""
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    objects = sorted(obj.name for obj in bpy.data.objects)
    text_bodies = sorted(obj.data.body for obj in bpy.data.objects if obj.type == "FONT")
    required = ["synthetic fixture diagnostic", "not real IFC partition/channel inference", "not route width", "not walkability", "candidate:01", "candidate:02", "selection: none", "computed_disconnected"]
    labels = {label: any(label in body for body in text_bodies) for label in required}
    text_positions = {obj.data.body: [float(value) for value in obj.location[:]] for obj in bpy.data.objects if obj.type == "FONT"}
    candidate_y = [text_positions[label][1] for label in ("candidate:01", "candidate:02", "selection: none") if label in text_positions]
    layout_checks = {
        "candidate_labels_separated": len(candidate_y) == 3 and len(set(candidate_y)) == 3 and max(candidate_y) - min(candidate_y) >= 0.8,
        "warning_block_above_panel_titles": text_positions.get("synthetic fixture diagnostic", [0.0, 0.0, 0.0])[1] > text_positions.get("title_multiple", [0.0, 0.0, 0.0])[1],
    }
    result = {"status": "pass" if all(labels.values()) and all(layout_checks.values()) else "fail", "object_count": len(objects), "objects": objects, "text_bodies": text_bodies, "text_positions": text_positions, "required_labels": labels, "layout_checks": layout_checks, "contains_required_labels": all(labels.values())}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "pass":
        raise SystemExit(1)


def inspect(blend: Path, output: Path, evidence_root: Path) -> None:
    """Read back labels and serialized geometry from the saved Blend file."""
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    candidate_evidence = json.loads((evidence_root / "candidate_evidence.json").read_text(encoding="utf-8"))
    fixture_manifest = json.loads((evidence_root / "fixture_manifest.json").read_text(encoding="utf-8"))
    objects = sorted(obj.name for obj in bpy.data.objects)
    text_bodies = sorted(obj.data.body for obj in bpy.data.objects if obj.type == "FONT")
    required = ["synthetic fixture diagnostic", "not real IFC partition/channel inference", "not route width", "not walkability", "candidate:01", "candidate:02", "selection: none", "computed_disconnected"]
    labels = {label: any(label in body for body in text_bodies) for label in required}
    text_positions = {obj.data.body: [float(value) for value in obj.location[:]] for obj in bpy.data.objects if obj.type == "FONT"}
    candidate_y = [text_positions[label][1] for label in ("candidate:01", "candidate:02", "selection: none") if label in text_positions]
    geometry_matches = {}
    # Only the three displayed panels are expected to have Blender geometry.
    for fixture_id in ("qualified_explicit_domain", "multiple_candidate_channels", "disconnected_components"):
        wrapper = candidate_evidence["fixtures"][fixture_id]
        for candidate in wrapper["candidate_set"]["candidates"]:
            name = f"candidate_{fixture_id}_{candidate['candidate_id'].replace(':', '_')}"
            obj = bpy.data.objects.get(name)
            expected = json.dumps(candidate["geometry"]["coordinates_xy_m"], separators=(",", ":"))
            geometry_matches[f"{fixture_id}:{candidate['candidate_id']}"] = bool(obj and obj.get("serialized_coordinates_xy_m") == expected)
    disconnected_fixture = fixture_manifest["fixture_inputs"]["disconnected_components"]
    domain_points = [point for ring in disconnected_fixture["domain"]["geometry_parts"] for point in ring]
    wall_points = [point for ring in disconnected_fixture["walls"][0]["geometry_parts"] for point in ring]
    domain_bounds = (min(point[0] for point in domain_points), min(point[1] for point in domain_points), max(point[0] for point in domain_points), max(point[1] for point in domain_points))
    wall_bounds = (min(point[0] for point in wall_points), min(point[1] for point in wall_points), max(point[0] for point in wall_points), max(point[1] for point in wall_points))
    wall_spans_domain = wall_bounds[1] <= domain_bounds[1] and wall_bounds[3] >= domain_bounds[3]
    layout_checks = {
        "candidate_labels_separated": len(candidate_y) == 3 and len(set(candidate_y)) == 3 and max(candidate_y) - min(candidate_y) >= 0.8,
        "warning_block_above_panel_titles": text_positions.get("synthetic fixture diagnostic", [0.0, 0.0, 0.0])[1] > max(position[1] for body, position in text_positions.items() if body.startswith("qualified domain")),
        "candidate_geometry_matches_serialized": all(geometry_matches.values()),
        "domain_boundary_separate_from_display_frame": any(name.startswith("domain_") for name in objects) and any(name.startswith("display_frame_") for name in objects),
        "disconnected_wall_spans_qualified_domain": wall_spans_domain,
    }
    result = {"status": "pass" if all(labels.values()) and all(layout_checks.values()) else "fail", "object_count": len(objects), "objects": objects, "text_bodies": text_bodies, "text_positions": text_positions, "required_labels": labels, "layout_checks": layout_checks, "candidate_geometry_matches": geometry_matches, "contains_required_labels": all(labels.values())}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "pass":
        raise SystemExit(1)


def main() -> None:
    """Parse Blender arguments and write readback JSON."""
    marker = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args(sys.argv[marker + 1 :])
    inspect(args.blend.resolve(), args.output.resolve(), args.evidence_root.resolve())


if __name__ == "__main__":
    main()
