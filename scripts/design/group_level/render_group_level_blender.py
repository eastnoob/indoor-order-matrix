"""Render a design-only Blender diagnostic for group trend and adjacency.

The preview shows source geometry, the selected undirected member consensus,
and normalized boundary-gap edges. It is a computational inspection artifact,
not a perceptual or usability validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def material(name: str, color: tuple[float, float, float]):
    """Create one opaque material for a diagnostic role."""
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    return mat


def add_text(body: str, location: tuple[float, float], size: float, mat, name: str):
    """Add a top-down label while retaining the fixture panel context."""
    data = bpy.data.curves.new(name, type="FONT")
    data.body = body
    data.align_x = "CENTER"
    data.size = size
    data.extrude = 0.004
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = (location[0], location[1], 0.25)
    obj.data.materials.append(mat)
    return obj


def add_segment(start: tuple[float, float], end: tuple[float, float], radius: float, mat, name: str):
    """Draw a plan segment between two points."""
    start_vec, end_vec = Vector((*start, 0.12)), Vector((*end, 0.12))
    delta = end_vec - start_vec
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=delta.length,
                                        location=(start_vec + end_vec) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    obj.data.materials.append(mat)
    return obj


def add_rectangle(center: list[float], size: list[float], angle: float, mat, name: str):
    """Draw one canonical member footprint as a thin cuboid."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center[0], center[1], 0.16))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (size[0], size[1], 0.10)
    obj.rotation_euler[2] = angle
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def panel_origin(index: int) -> tuple[float, float]:
    """Return stable positions for the three diagnostic panels."""
    return [(-5.0, 2.2), (0.0, 2.2), (4.9, 2.2)][index]


def render_scene(fixture: dict, output_dir: Path) -> dict:
    """Build, render, and save the deterministic group-level diagnostic."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = material("source_geometry", (0.16, 0.46, 0.92))
    trend = material("selected_trend", (0.15, 0.82, 0.38))
    neighbor = material("neighbor_edge", (0.98, 0.62, 0.10))
    knn = material("knn_edge", (0.92, 0.20, 0.20))
    title = material("label", (0.92, 0.92, 0.92))
    ground_mat = material("ground", (0.035, 0.045, 0.06))

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    bpy.context.object.data.materials.append(ground_mat)

    for index, case in enumerate(fixture["trend_cases"][:3]):
        ox, oy = panel_origin(index)
        add_text(case["id"], (ox, oy + 2.0), 0.28, title, f"trend_title_{case['id']}")
        for member in case["members"]:
            rectangle = member.get("rectangle")
            if rectangle is None:
                continue
            center = [rectangle["center"][0] * 0.55 + ox, rectangle["center"][1] * 0.55 + oy]
            size = [rectangle["size"][0] * 0.55, rectangle["size"][1] * 0.55]
            add_rectangle(center, size, rectangle["angle"], source, f"{case['id']}_{member['id']}")
        expected = case["expected"].get("angle")
        if expected is not None:
            add_segment((ox, oy), (ox + 1.0 * math_cos(expected), oy + 1.0 * math_sin(expected)), 0.035, trend,
                        f"trend_axis_{case['id']}")
        else:
            add_text("axis undefined", (ox, oy - 1.3), 0.18, trend, f"trend_undefined_{case['id']}")

    neighbor_case = fixture["neighbor_cases"][0]
    ox, oy = (0.0, -3.0)
    add_text("local_components | orange=normalized gap, red=kNN", (ox, oy + 2.0), 0.25, title, "neighbor_title")
    positions = {}
    for group in neighbor_case["groups"]:
        member = group["members"][0]["rectangle"]
        center = (ox + member["center"][0] * 0.45 - 2.4, oy + member["center"][1] * 0.45)
        positions[group["id"]] = center
        add_rectangle(list(center), [size * 0.45 for size in member["size"]], member["angle"], source, f"neighbor_{group['id']}")
        add_text(group["id"], (center[0], center[1] + 0.42), 0.18, title, f"neighbor_label_{group['id']}")
    for edge in ("A--B", "A--F", "D--E"):
        first, second = edge.split("--")
        add_segment(positions[first], positions[second], 0.035, neighbor, f"gap_{edge}")
    for edge in ("A--F", "B--F", "C--F", "D--E"):
        first, second = edge.split("--")
        add_segment(positions[first], positions[second], 0.018, knn, f"knn_{edge}")

    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.0, 10.0))
    bpy.context.object.data.energy = 1000
    bpy.context.object.data.size = 12.0
    bpy.ops.object.camera_add(location=(0.0, 0.0, 16.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 14.0
    bpy.context.scene.camera = camera
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("group_level_world")
    scene.world.color = (0.01, 0.015, 0.025)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = (output_dir / "group_level_diagnostic.png").resolve()
    scene.render.filepath = str(image_path)
    blend_path = (output_dir / "group_level_diagnostic.blend").resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.render.render(write_still=True)
    metadata = {
        "schema": "group-level-blender-diagnostic/v1",
        "fixture_sha256": hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest(),
        "scene": str(blend_path).replace("\\", "/"),
        "render": str(image_path).replace("\\", "/"),
        "camera": "orthographic top-down",
        "panels": ["directional", "isotropic", "symmetric", "local_components"],
        "limitation": "Headless render inspection is computational evidence; no interactive Blender viewport or human perceptual validation was performed.",
    }
    (output_dir / "blender_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def math_cos(value: float) -> float:
    """Return cosine without importing the fixture's implementation details."""
    import math
    return math.cos(value)


def math_sin(value: float) -> float:
    """Return sine without importing the fixture's implementation details."""
    import math
    return math.sin(value)


def main() -> None:
    """Parse Blender arguments and render the reproducible diagnostic."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    print(json.dumps(render_scene(fixture, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
