"""Render the run_002 disposable Blender diagnostic scene."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy


def _material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    """Create a simple material for synthetic diagnostic geometry."""
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material


def _cube(name: str, location: tuple[float, float, float], size: tuple[float, float, float], material: bpy.types.Material) -> None:
    """Add one thin rectangular diagnostic object."""
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)


def _text(name: str, body: str, location: tuple[float, float, float], size: float, material: bpy.types.Material) -> None:
    """Add an annotation whose body is also available to the readback audit."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.size = size
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.data.materials.append(material)
    bpy.context.collection.objects.link(obj)


def _line(name: str, start: tuple[float, float], end: tuple[float, float], z: float, material: bpy.types.Material, width: float = 0.06) -> None:
    """Add a thin segment between two points."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    _cube(name, ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, z), (length, width, width), material)
    bpy.data.objects[name].rotation_euler[2] = math.atan2(dy, dx)


def _panel(offset: float, title: str, mode: str, materials: dict[str, bpy.types.Material]) -> None:
    """Draw one fixture panel and its explicit semantic labels."""
    _line(f"domain_{mode}_bottom", (offset, 0), (offset + 12, 0), 0.0, materials["domain"], 0.08)
    _line(f"domain_{mode}_top", (offset, 8), (offset + 12, 8), 0.0, materials["domain"], 0.08)
    _line(f"domain_{mode}_left", (offset, 0), (offset, 8), 0.0, materials["domain"], 0.08)
    _line(f"domain_{mode}_right", (offset + 12, 0), (offset + 12, 8), 0.0, materials["domain"], 0.08)
    _cube(f"group_{mode}_left", (offset + 3.35, 3.6, 0.15), (1.3, 1.2, 0.3), materials["group"])
    _cube(f"group_{mode}_right", (offset + 8.65, 3.6, 0.15), (1.3, 1.2, 0.3), materials["group"])
    if mode == "multiple":
        _line("candidate_01_support", (offset + 4.0, 3.6), (offset + 8.0, 3.6), 0.42, materials["support"], 0.08)
        _line("candidate_02_support", (offset + 4.0, 2.55), (offset + 8.0, 2.55), 0.42, materials["candidate_two"], 0.08)
        # Keep the three contract labels on separate baselines so the PNG remains auditable at review scale.
        _text("candidate_01_label", "candidate:01", (offset + 6, 4.55, 0.0), 0.23, materials["text"])
        _text("candidate_02_label", "candidate:02", (offset + 6, 5.05, 0.0), 0.23, materials["text"])
        _text("selection_none_label", "selection: none", (offset + 6, 5.55, 0.0), 0.23, materials["text"])
        _cube("candidate_wall_band_01", (offset + 6, 2.35, 0.15), (1.8, 0.3, 0.28), materials["wall"])
        _cube("candidate_wall_band_02", (offset + 6, 4.85, 0.15), (1.8, 0.3, 0.28), materials["wall"])
    elif mode == "disconnected":
        _cube("physical_wall_occupancy", (offset + 6, 4.0, 0.20), (0.45, 8.0, 0.4), materials["wall"])
        _line("candidate_disconnected_support", (offset + 4.0, 3.6), (offset + 8.0, 3.6), 0.42, materials["support"], 0.08)
    else:
        _line("candidate_qualified_support", (offset + 4.0, 3.6), (offset + 8.0, 3.6), 0.42, materials["support"], 0.08)
    _text(f"title_{mode}", title, (offset + 6, 8.85, 0.0), 0.38, materials["text"])
    _text(f"gap_{mode}", "pairwise boundary gap", (offset + 6, 8.35, 0.0), 0.21, materials["text"])
    _text(f"profile_{mode}", "pairwise free-space diagnostic", (offset + 6, -0.55, 0.0), 0.21, materials["text"])
    _text(f"connectivity_{mode}", "connectivity independent of candidate selection", (offset + 6, -0.95, 0.0), 0.17, materials["text"])


def build(output: Path) -> None:
    """Create, render, and save the disposable run_002 scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    materials = {
        "domain": _material("domain_outline", (0.2, 0.7, 1.0, 1.0)),
        "group": _material("furniture_group", (0.1, 0.45, 0.95, 1.0)),
        "wall": _material("physical_wall", (0.85, 0.15, 0.65, 1.0)),
        "support": _material("candidate_support_one", (0.1, 0.8, 0.3, 1.0)),
        "candidate_two": _material("candidate_support_two", (0.95, 0.45, 0.05, 1.0)),
        "text": _material("annotation", (0.02, 0.02, 0.02, 1.0)),
    }
    _panel(0.0, "qualified explicit domain", "qualified", materials)
    _panel(14.0, "multiple candidates / no winner", "multiple", materials)
    _panel(28.0, "computed_disconnected", "disconnected", materials)
    # Reserve a dedicated warning band above all panels; this prevents semantic limits from colliding with panel titles.
    _text("semantic_warning", "synthetic fixture diagnostic", (20.0, 11.15, 0.0), 0.34, materials["text"])
    _text("semantic_warning_ifc", "not real IFC partition/channel inference", (20.0, 10.70, 0.0), 0.27, materials["text"])
    _text("semantic_warning_route", "not route width", (20.0, 10.25, 0.0), 0.27, materials["text"])
    _text("semantic_warning_walk", "not walkability", (20.0, 9.80, 0.0), 0.27, materials["text"])
    bpy.ops.object.camera_add(location=(20.0, 5.0, 35.0))
    camera = bpy.context.object
    camera.name = "DisposableCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 44.0
    bpy.context.scene.camera = camera
    world = bpy.context.scene.world
    world.color = (0.96, 0.96, 0.96)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str((output / "pairwise_channel_disposable.png").resolve())
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=str((output / "pairwise_channel_disposable.blend").resolve()))
    bpy.ops.render.render(write_still=True)


def main() -> None:
    """Parse Blender arguments and render the disposable scene."""
    marker = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[marker + 1 :])
    build(args.output.resolve())


if __name__ == "__main__":
    main()
