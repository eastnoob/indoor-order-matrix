"""Read back and validate the disposable candidate blend without saving it."""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Assert candidate scene contents and write a compact readback record."""
    scenes = sorted(bpy.data.scenes, key=lambda scene: scene.name)
    if len(scenes) != 4:
        raise RuntimeError(f"Expected four candidate scenes, found {len(scenes)}.")
    scene_records = []
    for scene in scenes:
        objects = list(scene.objects)
        labels = [item for item in objects if item.name.startswith("NodeLabel_G")]
        walls = [item for item in objects if item.name.startswith("PhysicalWall_")]
        fills = [item for item in objects if item.name.startswith("RegionFill_")]
        if len(labels) != 37:
            raise RuntimeError(f"{scene.name}: expected 37 group labels, found {len(labels)}.")
        if len(walls) != 11:
            raise RuntimeError(f"{scene.name}: expected 11 wall meshes, found {len(walls)}.")
        if not fills:
            raise RuntimeError(f"{scene.name}: candidate region geometry is missing.")
        if scene.camera is None or scene.camera.data.type != "ORTHO":
            raise RuntimeError(f"{scene.name}: top-down orthographic camera is missing.")
        scene_records.append({
            "scene": scene.name,
            "object_count": len(objects),
            "analysis_node_labels": len(labels),
            "physical_wall_meshes": len(walls),
            "region_fill_meshes": len(fills),
            "camera_type": scene.camera.data.type,
            "render_resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "render_path": scene.render.filepath,
        })
    target = ROOT / "blend_readback.json"
    target.write_text(
        json.dumps({
            "status": "pass",
            "blend_filepath": bpy.data.filepath,
            "blender_version": bpy.app.version_string,
            "scene_count": len(scenes),
            "scenes": scene_records,
            "source_scene_opened_or_saved": False,
        }, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "pass", "scenes": len(scenes), "path": str(target)}))


if __name__ == "__main__":
    main()
