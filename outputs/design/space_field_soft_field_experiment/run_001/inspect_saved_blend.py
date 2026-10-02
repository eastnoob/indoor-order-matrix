"""Read back the disposable soft-field blend without saving it."""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Verify six scenes, orthographic cameras, and required display layers."""
    scenes = sorted(bpy.data.scenes, key=lambda scene: scene.name)
    if len(scenes) != 6:
        raise RuntimeError(f"Expected six disposable scenes, found {len(scenes)}.")
    records = []
    required = ["ProvisionalDiagnosticFrame", "Title", "PanelTitle"]
    for scene in scenes:
        if scene.camera is None or scene.camera.data.type != "ORTHO":
            raise RuntimeError(f"{scene.name}: missing top-down orthographic camera.")
        names = {obj.name for obj in scene.objects}
        missing = [prefix for prefix in required if not any(name.startswith(prefix) for name in names)]
        if missing:
            raise RuntimeError(f"{scene.name}: missing display objects {missing}.")
        if not scene.render.filepath.lower().endswith(".png"):
            raise RuntimeError(f"{scene.name}: render path is not PNG.")
        records.append({
            "scene": scene.name,
            "object_count": len(scene.objects),
            "camera_type": scene.camera.data.type,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "render_path": scene.render.filepath,
            "has_frame": any(name.startswith("ProvisionalDiagnosticFrame") for name in names),
        })
    target = ROOT / "blend_readback.json"
    target.write_text(json.dumps({
        "schema": "d6-space-field-soft-field-blend-readback/v1",
        "status": "pass",
        "blend_filepath": bpy.data.filepath,
        "blender_version": bpy.app.version_string,
        "scene_count": len(scenes),
        "scenes": records,
        "source_user_scene_opened_or_saved": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "scene_count": len(scenes), "path": str(target)}))


if __name__ == "__main__":
    main()
