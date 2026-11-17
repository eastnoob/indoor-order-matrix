"""Run bounded native Blender acceptance for the persistent analysis board."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy


ROOT = Path(__file__).resolve().parents[3]
RESULT_PATH = ROOT / "outputs" / "blender_analysis" / "jobs" / "fe3243c13b3f45daac8744efc46f3962" / "result.json"
OUT_DIR = ROOT / "outputs" / "design" / "analysis_board" / "native"
BLEND_PATH = OUT_DIR / "analysis_board_s3.blend"
RENDER_PATH = OUT_DIR / "analysis_board_s3.png"

sys.path.insert(0, str(ROOT))

from adapters import blender_analysis_result_wire as wire
from blender_addon.order_analyzer_ui import board


def _clear_scene() -> None:
    """Remove only the disposable native acceptance scene contents."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def _look_at(camera, target):
    """Aim a camera at a world-space target using Blender's track quaternion."""
    from mathutils import Vector
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def _make_context_floor(result):
    """Create a neutral slab datum reference for the visual placement check."""
    points = [vertex for fragment in result.display_fragments for vertex in fragment["vertices"]]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    margin = max(max_x - min_x, max_y - min_y) * .06
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=((min_x + max_x) / 2, (min_y + max_y) / 2, 0.0))
    floor = bpy.context.object
    floor.name = "Acceptance slab datum (context only)"
    floor.scale = ((max_x - min_x + margin) / 2, (max_y - min_y + margin) / 2, 1.0)
    material = bpy.data.materials.new("Acceptance slab")
    material.diffuse_color = (.08, .09, .11, 1.0)
    floor.data.materials.append(material)
    return (min_x, max_x, min_y, max_y)


def _make_camera(bounds):
    """Create an orthographic top view that shows the whole board and slab context."""
    min_x, max_x, min_y, max_y = bounds
    center = ((min_x + max_x) / 2, (min_y + max_y) / 2, 0.0)
    span = max(max_x - min_x, max_y - min_y)
    camera_data = bpy.data.cameras.new("Acceptance camera")
    camera = bpy.data.objects.new("Acceptance camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (center[0], center[1], span * 1.15 + 2.0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = span * 1.12
    _look_at(camera, center)
    bpy.context.scene.camera = camera
    return camera


def _render(bounds):
    """Render one compact placement/palette view from the disposable scene."""
    _make_camera(bounds)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.filepath = str(RENDER_PATH)
    bpy.ops.render.render(write_still=True)


def comparison() -> None:
    """Render the saved board under each palette and two opacity settings."""
    boards = board.scene_boards(bpy_module=bpy)
    assert len(boards) == 1
    board_object = boards[0]
    display = next(obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display")
    # The camera saved with the fixture already frames the complete board.
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 600
    scene.render.resolution_y = 460
    scene.render.resolution_percentage = 100
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    for palette, opacity in (("cividis", .5), ("viridis", .5), ("magma", .5), ("magma", 1.0)):
        board.update_style(board_object, palette=palette, opacity=opacity, reverse=False, bpy_module=bpy)
        path = OUT_DIR / f"board_{palette}_{str(opacity).replace('.', '_')}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
    print(json.dumps({"mode": "comparison", "output_dir": str(OUT_DIR)}))


def prepare() -> None:
    """Attach the actual S3 result, verify native ownership and save a visual fixture."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _clear_scene()
    document = wire.load_json(RESULT_PATH.read_text(encoding="utf-8"))
    result = wire.ValidatedAnalysisResult(document)
    original_digest = result.digest
    board_object = board.attach_result(result, result_path=RESULT_PATH, bpy_module=bpy)
    record = board.board_record(board_object)
    sources = [obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_source"]
    displays = [obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display"]
    assert len(sources) == len(displays) == 1
    source, display = sources[0], displays[0]
    assert source.hide_viewport and source.hide_render
    assert not display.hide_viewport and not display.hide_render
    assert source.data == display.data
    assert record["active_result_id"] == result.result_id
    assert record["binding"]["datum"]["datum_z_m"] == 0.0
    # Source vertices retain the 1.6 m calculation-plane height; the child offset
    # brings the visible copy down to slab top plus its 0.02 m display lift.
    assert round(display.location.z, 6) == -1.6
    board.update_style(board_object, palette="magma", reverse=True, opacity=.5, bpy_module=bpy)
    assert board.board_record(board_object)["style"]["palette"] == "magma"
    assert board.board_record(board_object)["style"]["reverse"] is True
    assert result.digest == original_digest
    bounds = _make_context_floor(result)
    _render(bounds)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(json.dumps({"mode": "prepare", "result_id": result.result_id, "board_id": record["board_id"],
                      "source_hidden": True, "display_visible": True, "shared_mesh": True,
                      "datum_z_m": record["binding"]["datum"]["datum_z_m"], "display_z": display.location.z,
                      "palette": "magma", "reverse": True, "opacity": .5,
                      "blend": str(BLEND_PATH), "render": str(RENDER_PATH)}))


def reopen() -> None:
    """Reopen the saved fixture and restore only the historical board display."""
    restored = board.restore_boards(bpy_module=bpy)
    assert len(restored) == 1
    board_object = restored[0]
    record = board.board_record(board_object)
    displays = [obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display"]
    sources = [obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_source"]
    assert len(displays) == len(sources) == 1
    assert not displays[0].hide_viewport and sources[0].hide_viewport
    assert record["status"] == "historical"
    print(json.dumps({"mode": "reopen", "board_id": record["board_id"],
                      "active_result_id": record["active_result_id"], "status": record["status"],
                      "source_hidden": sources[0].hide_viewport, "display_visible": not displays[0].hide_viewport}))


if __name__ == "__main__":
    if "--reopen" in sys.argv:
        reopen()
    elif "--comparison" in sys.argv:
        comparison()
    else:
        prepare()
