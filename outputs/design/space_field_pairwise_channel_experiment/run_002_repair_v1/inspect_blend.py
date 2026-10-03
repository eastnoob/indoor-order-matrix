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


def main() -> None:
    """Parse Blender arguments and write readback JSON."""
    marker = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[marker + 1 :])
    inspect(args.blend.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
