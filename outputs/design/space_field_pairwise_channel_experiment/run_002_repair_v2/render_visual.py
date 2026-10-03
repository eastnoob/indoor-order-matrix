"""Render the run_002 disposable Blender diagnostic scene."""

from __future__ import annotations

import argparse
import json
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


def _serialized_bounds(parts: list[list[list[float]]]) -> tuple[float, float, float, float]:
    """Return bounds for serialized polygon rings."""
    points = [point for ring in parts for point in ring]
    if not points:
        return 0.0, 0.0, 12.0, 8.0
    xs, ys = [float(point[0]) for point in points], [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _projector(domain_parts: list[list[list[float]]], offset: float):
    """Map serialized metre coordinates into one display panel."""
    minx, miny, maxx, maxy = _serialized_bounds(domain_parts)
    sx, sy = 10.0 / (maxx - minx), 6.6 / (maxy - miny)
    def project(point: list[float]) -> tuple[float, float]:
        return offset + 1.0 + (float(point[0]) - minx) * sx, 1.0 + (float(point[1]) - miny) * sy
    return project


def _annotated_line(name: str, coords: list[list[float]], project, z: float, material: bpy.types.Material, *, candidate_id: str, fixture_id: str) -> None:
    """Draw one serialized candidate line and retain its source coordinates in Blender."""
    start, end = project(coords[0]), project(coords[-1])
    _line(name, start, end, z, material, 0.08)
    obj = bpy.data.objects[name]
    obj["source_fixture"] = fixture_id
    obj["candidate_id"] = candidate_id
    obj["serialized_coordinates_xy_m"] = json.dumps(coords, separators=(",", ":"))


def _draw_serialized_polygon(name: str, parts: list[list[list[float]]], project, z: float, material: bpy.types.Material, *, fixture_id: str, source_id: str) -> None:
    """Draw an axis-aligned serialized polygon as a display cube."""
    if not parts:
        return
    minx, miny, maxx, maxy = _serialized_bounds(parts)
    p1, p2 = project([minx, miny]), project([maxx, maxy])
    _cube(name, ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0, z), (abs(p2[0] - p1[0]), abs(p2[1] - p1[1]), 0.28), material)
    obj = bpy.data.objects[name]
    obj["source_fixture"] = fixture_id
    obj["source_id"] = source_id
    obj["serialized_geometry_parts"] = json.dumps(parts, separators=(",", ":"))


def build(output: Path) -> None:
    """Build PNG and Blend from serialized repair_v2 evidence files."""
    candidate_evidence = json.loads((output / "candidate_evidence.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((output / "pairwise_diagnostic.json").read_text(encoding="utf-8"))
    fixture_manifest = json.loads((output / "fixture_manifest.json").read_text(encoding="utf-8"))
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    materials = {
        "domain": _material("domain_outline", (0.2, 0.7, 1.0, 1.0)),
        "frame": _material("display_frame", (0.55, 0.58, 0.62, 1.0)),
        "group": _material("furniture_group", (0.1, 0.45, 0.95, 1.0)),
        "wall": _material("physical_wall", (0.85, 0.15, 0.65, 1.0)),
        "column": _material("physical_column", (0.45, 0.15, 0.75, 1.0)),
        "support": _material("candidate_support_one", (0.1, 0.8, 0.3, 1.0)),
        "candidate_two": _material("candidate_support_two", (0.95, 0.45, 0.05, 1.0)),
        "text": _material("annotation", (0.02, 0.02, 0.02, 1.0)),
    }
    panels = [("qualified_explicit_domain", "qualified domain / single candidate"), ("multiple_candidate_channels", "multiple candidates / no winner"), ("disconnected_components", "computed_disconnected")]
    colors = [materials["support"], materials["candidate_two"], materials["column"], materials["wall"]]
    for index, (fixture_id, title) in enumerate(panels):
        offset = float(index * 14.0)
        fixture = fixture_manifest["fixture_inputs"][fixture_id]
        domain_parts = fixture["domain"].get("geometry_parts", []) if fixture.get("domain") else []
        project = _projector(domain_parts, offset)
        # The display frame is deliberately separate from the serialized AnalysisDomain boundary.
        _line(f"display_frame_{fixture_id}_bottom", (offset + 0.3, 0.4), (offset + 11.7, 0.4), 0.0, materials["frame"], 0.05)
        _line(f"display_frame_{fixture_id}_top", (offset + 0.3, 8.2), (offset + 11.7, 8.2), 0.0, materials["frame"], 0.05)
        _line(f"display_frame_{fixture_id}_left", (offset + 0.3, 0.4), (offset + 0.3, 8.2), 0.0, materials["frame"], 0.05)
        _line(f"display_frame_{fixture_id}_right", (offset + 11.7, 0.4), (offset + 11.7, 8.2), 0.0, materials["frame"], 0.05)
        for ring_index, ring in enumerate(domain_parts):
            for point_index in range(len(ring) - 1):
                _line(f"domain_{fixture_id}_{ring_index}_{point_index}", project(ring[point_index]), project(ring[point_index + 1]), 0.05, materials["domain"], 0.07)
        for group in fixture["groups"]:
            _draw_serialized_polygon(f"{fixture_id}_{group['group_id']}", group["geometry_parts"], project, 0.16, materials["group"], fixture_id=fixture_id, source_id=group["group_id"])
        for wall in fixture["walls"]:
            _draw_serialized_polygon(f"{fixture_id}_{wall['source_id']}", wall.get("geometry_parts", []), project, 0.22, materials["wall"], fixture_id=fixture_id, source_id=wall["source_id"])
        for column in fixture["columns"]:
            _draw_serialized_polygon(f"{fixture_id}_{column['source_id']}", column.get("geometry_parts", []), project, 0.22, materials["column"], fixture_id=fixture_id, source_id=column["source_id"])
        for candidate_index, candidate in enumerate(candidate_evidence["fixtures"][fixture_id]["candidate_set"]["candidates"]):
            material = colors[candidate_index % len(colors)]
            _annotated_line(f"candidate_{fixture_id}_{candidate['candidate_id'].replace(':', '_')}", candidate["geometry"]["coordinates_xy_m"], project, 0.42, material, candidate_id=candidate["candidate_id"], fixture_id=fixture_id)
            coords = candidate["geometry"]["coordinates_xy_m"]
            midpoint = [(coords[0][0] + coords[-1][0]) / 2.0, (coords[0][1] + coords[-1][1]) / 2.0]
            label_position = project(midpoint)
            _text(f"label_{fixture_id}_{candidate['candidate_id'].replace(':', '_')}", candidate["candidate_id"], (label_position[0], label_position[1] + 0.35 + 0.25 * candidate_index, 0.0), 0.22, material)
        if fixture_id == "multiple_candidate_channels":
            _text("selection_none_label", "selection: none", (offset + 6.0, 0.78, 0.0), 0.24, materials["text"])
        _text(f"title_{fixture_id}", title, (offset + 6.0, 9.0, 0.0), 0.32, materials["text"])
        _text(f"profile_{fixture_id}", f"profile: {diagnostics['fixtures'][fixture_id]['estimands']['pairwise_free_space_profile']['status']}", (offset + 6.0, 0.0, 0.0), 0.19, materials["text"])
        _text(f"connectivity_{fixture_id}", f"connectivity: {diagnostics['fixtures'][fixture_id]['estimands']['pairwise_connectivity_evidence']['status']}", (offset + 6.0, -0.34, 0.0), 0.17, materials["text"])
    _text("semantic_warning", "synthetic fixture diagnostic", (20.0, 11.25, 0.0), 0.34, materials["text"])
    _text("semantic_warning_ifc", "not real IFC partition/channel inference", (20.0, 10.78, 0.0), 0.27, materials["text"])
    _text("semantic_warning_route", "not route width", (20.0, 10.34, 0.0), 0.27, materials["text"])
    _text("semantic_warning_walk", "not walkability", (20.0, 9.90, 0.0), 0.27, materials["text"])
    bpy.ops.object.camera_add(location=(20.0, 4.7, 35.0))
    camera = bpy.context.object
    camera.name = "DisposableCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 44.0
    bpy.context.scene.camera = camera
    bpy.context.scene.world.color = (0.96, 0.96, 0.96)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1800, 760, 100
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
