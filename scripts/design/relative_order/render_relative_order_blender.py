"""Build a design-only Blender diagnostic for relative-order variables.

The scene shows anchors, explicit axis direction, a partial-tie region, and a
rotated/transformed frame.  It is a computational preview of the probe inputs,
not a perceptual validity experiment.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def material(name, color):
    """Create a simple opaque material for diagnostic overlays."""
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    return mat


def add_text(body, location, size, mat, name):
    """Add readable top-down text while retaining the panel provenance label."""
    data = bpy.data.curves.new(name, type="FONT")
    data.body = body
    data.align_x = "CENTER"
    data.size = size
    data.extrude = 0.005
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = (*location, 0.16)
    obj.data.materials.append(mat)
    return obj


def add_cylinder_between(start, end, radius, mat, name):
    """Draw an axis segment between two plan points."""
    start_vec, end_vec = Vector((*start, 0.10)), Vector((*end, 0.10))
    delta = end_vec - start_vec
    midpoint = (start_vec + end_vec) / 2
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=delta.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    obj.data.materials.append(mat)
    return obj


def add_arrow(start, direction, length, mat, name):
    """Draw an axis with a cone showing its positive direction."""
    end = (start[0] + direction[0] * length, start[1] + direction[1] * length)
    add_cylinder_between(start, end, 0.025, mat, f"{name}_shaft")
    end_vec = Vector((*end, 0.10))
    direction_vec = Vector((direction[0], direction[1], 0.0))
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.10, radius2=0.0, depth=0.28, location=end_vec)
    cone = bpy.context.object
    cone.name = f"{name}_direction"
    cone.rotation_mode = "QUATERNION"
    cone.rotation_quaternion = direction_vec.to_track_quat("Z", "Y")
    cone.data.materials.append(mat)


def add_anchor(label, point, mat, panel_name):
    """Draw one anchor marker and its stable object label."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.11, location=(*point, 0.24))
    sphere = bpy.context.object
    sphere.name = f"{panel_name}_anchor_{label}"
    sphere.data.materials.append(mat)
    add_text(label, (point[0], point[1] + 0.22), 0.22, mat, f"{panel_name}_label_{label}")


def add_tie_ring(center, radius, mat, name):
    """Mark the region in which pair positions are tied by tolerance."""
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=0.025, major_segments=48, location=(*center, 0.18))
    ring = bpy.context.object
    ring.name = name
    ring.data.materials.append(mat)


def add_panel(panel_origin, title, positions, axis, axis_color, tie_center=None, tie_radius=0.0, panel_name="panel"):
    """Create a labelled panel with local anchors and an explicit analysis axis."""
    ox, oy = panel_origin
    points = [(ox + x, oy + y) for x, y in positions]
    for label, point in zip(("A", "B", "C"), points):
        add_anchor(label, point, anchor_material, panel_name)
    frame_origin = (ox - 1.0, oy - 0.75)
    bpy.ops.mesh.primitive_cube_add(size=0.13, location=(*frame_origin, 0.18))
    origin_marker = bpy.context.object
    origin_marker.name = f"{panel_name}_frame_origin"
    origin_marker.data.materials.append(title_material)
    add_text("O", (frame_origin[0] - 0.16, frame_origin[1] - 0.16), 0.15, title_material, f"{panel_name}_origin_label")
    add_arrow(frame_origin, axis, 2.7, axis_color, f"{panel_name}_axis")
    add_text(title, (ox, oy + 1.18), 0.25, title_material, f"{panel_name}_title")
    add_text("+ direction", (ox + axis[0] * 1.30, oy - 0.93 + axis[1] * 1.30), 0.16, axis_color, f"{panel_name}_direction_label")
    if tie_center is not None:
        add_tie_ring((ox + tie_center[0], oy + tie_center[1]), tie_radius, tie_material, f"{panel_name}_tie_region")
        add_text("tie ≤ tol", (ox + tie_center[0], oy + tie_center[1] - 0.42), 0.16, tie_material, f"{panel_name}_tie_label")
    return points


def main():
    """Create and render the reproducible relative-order diagnostic scene."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    global anchor_material, axis_material, reverse_material, tie_material, title_material
    anchor_material = material("anchor_blue", (0.12, 0.45, 0.95))
    axis_material = material("positive_axis_green", (0.16, 0.85, 0.35))
    reverse_material = material("reversed_axis_red", (0.95, 0.18, 0.18))
    tie_material = material("tie_orange", (1.0, 0.55, 0.05))
    title_material = material("title_white", (0.92, 0.92, 0.92))
    ground_material = material("ground", (0.035, 0.045, 0.06))

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "diagnostic_ground"
    ground.data.materials.append(ground_material)
    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.0, 10.0))
    light = bpy.context.object
    light.name = "diagnostic_fill"
    light.data.energy = 1200
    light.data.shape = "DISK"
    light.data.size = 12.0

    add_panel((-3.7, 2.0), "aligned | A=1, B=1", [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)], (1.0, 0.0), axis_material, panel_name="aligned")
    add_panel((3.5, 2.0), "rotated geometry + translated frame | A=1, B=1", [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)], (0.0, 1.0), axis_material, panel_name="rotated")
    add_panel((0.0, -2.1), "partial tie + axis reversal", [(0.0, 0.0), (0.05, 0.0), (1.0, 0.0)], (1.0, 0.0), axis_material, tie_center=(0.025, 0.0), tie_radius=0.30, panel_name="ties")
    add_arrow((-1.0, -2.85), (-1.0, 0.0), 2.7, reverse_material, "reversed_axis")
    add_text("reversed axis", (-2.15, -2.85), 0.18, reverse_material, "reversed_axis_label")
    add_text("blue = anchor   green/red = declared direction   orange ring = tied region", (0.0, -3.35), 0.18, title_material, "legend")

    bpy.ops.object.camera_add(location=(0.0, 0.0, 16.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 13.0
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera.rotation_euler[0] = 0.0
    camera.rotation_euler[1] = 0.0
    camera.rotation_euler[2] = 0.0
    # A top-down camera looks along -Z; the explicit origin keeps screen axes auditable.
    camera.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.scene.camera = camera
    camera.data.lens = 50

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str((args.output_dir / "relative_order_diagnostic.png").resolve())
    scene.world = bpy.data.worlds.new("relative_order_world")
    scene.world.color = (0.01, 0.015, 0.025)
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"

    blend_path = (args.output_dir / "relative_order_diagnostic.blend").resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.render.render(write_still=True)
    metadata = {
        "schema": "relative-order-blender-diagnostic/v1",
        "fixture": str(args.fixture.resolve()).replace("\\", "/"),
        "script": str(Path(__file__).resolve()).replace("\\", "/"),
        "scene": str(blend_path).replace("\\", "/"),
        "render": str(Path(scene.render.filepath).resolve()).replace("\\", "/"),
        "settings": {
            "engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "camera": "orthographic top-down",
            "panels": ["aligned", "rotated geometry + translated frame", "partial tie", "axis reversal"],
        },
        "limitation": "Headless render was inspected as an image; interactive Blender viewport/UI inspection was not performed.",
    }
    (args.output_dir / "blender_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
