"""Render the frozen D6 Body and Analysis sample in a disposable Blender file."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _args() -> argparse.Namespace:
    """Parse arguments after Blender's ``--`` separator."""
    import sys

    tokens = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(tokens)


def _load(input_dir: Path) -> tuple[dict, dict, dict]:
    """Load only serialized smoke data; Blender never recomputes evidence."""
    sample = json.loads((input_dir / "sample_scene.json").read_text(encoding="utf-8"))
    description = json.loads((input_dir / "description.json").read_text(encoding="utf-8"))
    inventory = json.loads((input_dir / "inventory.json").read_text(encoding="utf-8"))
    return sample, description, inventory


def _material(name: str, color: tuple[float, float, float], alpha: float = 1.0):
    """Create a tagged material for this disposable output scene."""
    import bpy

    material = bpy.data.materials.get("D6Smoke_" + name) or bpy.data.materials.new("D6Smoke_" + name)
    material.diffuse_color = (*color, alpha)
    material.use_nodes = False
    material["d6_smoke_material"] = True
    material["d6_role"] = name
    return material


def _collection(name: str):
    """Create one independently hideable output collection."""
    import bpy

    collection = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if collection.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(collection)
    return collection


def _mesh(collection, name: str, vertices: list, faces: list, material, role: str, source_id: str):
    """Create one source-linked mesh object and preserve its identity tags."""
    import bpy

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["d6_smoke"] = True
    obj["d6_role"] = role
    obj["source_id"] = source_id
    return obj


def _curve(collection, name: str, points: list, material, role: str, source_id: str, bevel: float = 0.012):
    """Create one display-only polyline overlay with source identity."""
    import bpy

    curve = bpy.data.curves.new(name + "_curve", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel
    spline = curve.splines.new("POLY")
    spline.points.add(max(0, len(points) - 1))
    for target, point in zip(spline.points, points):
        target.co = (float(point[0]), float(point[1]), float(point[2]) if len(point) > 2 else 0.05, 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["d6_smoke"] = True
    obj["d6_role"] = role
    obj["source_id"] = source_id
    return obj


def _label(collection, text: str, location: tuple[float, float, float], material, role: str, source_id: str, size: float = 0.12):
    """Add a readable top-view identity label without encoding a score."""
    import bpy

    curve = bpy.data.curves.new("LabelCurve", "FONT")
    curve.body = text
    curve.align_x = "CENTER"
    curve.size = size
    obj = bpy.data.objects.new("D6Label_" + source_id.replace(":", "_"), curve)
    obj.location = location
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["d6_smoke"] = True
    obj["d6_role"] = role
    obj["source_id"] = source_id
    return obj


def _all_points(sample: dict, description: dict) -> list[tuple[float, float, float]]:
    """Collect actual Body and Analysis coordinates for deterministic framing."""
    points = []
    for item in sample.get("body_meshes", ()):
        points.extend(tuple(point) for point in item["mesh"]["vertices"])
    for mesh in sample.get("scene", {}).get("geometries", ()):
        points.extend(tuple(point) for point in mesh.get("vertices", ()))
    for group in description.get("group_geometry", ()):
        for member in group.get("member_geometry", ()):
            points.extend((float(point[0]), float(point[1]), 0.0) for point in member.get("points", ()))
    return points


def _camera(points: list[tuple[float, float, float]]) -> dict[str, object]:
    """Frame all display geometry and labels in the rendered image."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector

    bpy.context.view_layer.update()
    # Text and overlays extend beyond source geometry, so include their actual Blender bounds.
    for obj in bpy.data.objects:
        if obj.get("d6_smoke"):
            points.extend(tuple(obj.matrix_world @ Vector(corner)) for corner in obj.bound_box)
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0
    aspect = bpy.context.scene.render.resolution_x / bpy.context.scene.render.resolution_y
    span = max(max_x - min_x, (max_y - min_y) * aspect, 1.0)
    camera_data = bpy.data.cameras.new("D6SmokeCamera")
    camera = bpy.data.objects.new("D6SmokeCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (cx, cy, 60.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera_data.type = "ORTHO"
    # Blender's ortho scale spans image width; convert vertical extent using aspect.
    camera_data.ortho_scale = span * 1.30
    bpy.context.scene.camera = camera
    bpy.context.view_layer.update()
    projected = [world_to_camera_view(bpy.context.scene, camera, Vector(point)) for point in points]
    bounds = {axis: [min(point[index] for point in projected), max(point[index] for point in projected)] for axis, index in (("x", 0), ("y", 1))}
    if any(low < 0.04 or high > 0.96 for low, high in bounds.values()):
        raise RuntimeError(f"smoke geometry or labels clipped by camera: {bounds}")
    return {"normalized_image_bounds": bounds, "ortho_scale": camera_data.ortho_scale}


def _configure_scene():
    """Configure a stable workbench render with a neutral world background."""
    import bpy

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.world.color = (0.035, 0.035, 0.035)


def _clear_startup_objects() -> None:
    """Remove factory-startup objects so artifact counts cover only this smoke scene."""
    import bpy

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.unlink(collection)
        bpy.data.collections.remove(collection)


def _build(sample: dict, description: dict, inventory: dict) -> dict[str, object]:
    """Build separate Body, Analysis, overlay, and label collections."""
    import bpy

    body_collection = _collection("D6_Source_Body")
    analysis_collection = _collection("D6_Analysis_Terminal")
    overlay_collection = _collection("D6_Analysis_Overlays")
    source_label_collection = _collection("D6_Source_Labels")
    analysis_label_collection = _collection("D6_Analysis_Labels")
    body_material = _material("Body", (0.42, 0.45, 0.50))
    analysis_material = _material("Analysis", (0.20, 0.58, 0.92), 0.75)
    footprint_material = _material("Footprint", (0.15, 0.85, 0.55))
    center_material = _material("Center", (0.95, 0.85, 0.20))
    frame_material = _material("Frame", (1.0, 0.55, 0.08))
    axis_material = _material("Axis", (0.92, 0.18, 0.18))
    label_material = _material("Labels", (0.98, 0.98, 0.98))
    source_meshes = sample.get("body_meshes", ())
    analysis_meshes = {item["id"]: item for item in sample.get("scene", {}).get("geometries", ())}
    body_vertices = {item["source_id"]: item["mesh"]["vertices"] for item in source_meshes}
    for item in source_meshes:
        mesh = item["mesh"]
        _mesh(body_collection, "Body_" + item["source_id"], mesh["vertices"], mesh["triangle_indices"], body_material, "Body", item["source_id"])
    for mesh_id, mesh in analysis_meshes.items():
        owner = mesh_id.removeprefix("ifc-mesh:").removesuffix(":analysis")
        _mesh(analysis_collection, "Analysis_" + owner, mesh["vertices"], mesh["triangle_indices"], analysis_material, "Analysis", owner)
    for group_index, group in enumerate(inventory.get("selected_groups", ()), start=1):
        member_ids = group.get("member_source_ids", ())
        member_points = [point for member in member_ids for point in body_vertices.get(member, ())]
        if not member_points:
            continue
        group_x = (min(point[0] for point in member_points) + max(point[0] for point in member_points)) / 2.0
        group_top = max(point[1] for point in member_points)
        for member_index, member in enumerate(member_ids, start=1):
            vertices = body_vertices.get(member, ())
            if not vertices:
                continue
            x = (min(point[0] for point in vertices) + max(point[0] for point in vertices)) / 2.0
            y = (min(point[1] for point in vertices) + max(point[1] for point in vertices)) / 2.0
            # Short display keys separate nearby furniture; metadata retains each complete IFC ID.
            for collection, role in ((source_label_collection, "source_member_label"), (analysis_label_collection, "analysis_member_label")):
                _label(collection, f"{group_index}{chr(96 + member_index)}", (x, y, 2.0), label_material, role, member, 0.11)
        _label(source_label_collection, f"G{group_index}", (group_x, group_top + 0.35, 2.0), label_material, "source_group_label", group["id"], 0.15)
        _label(analysis_label_collection, f"G{group_index}", (group_x, group_top + 0.52, 2.0), label_material, "analysis_group_label", group["id"], 0.15)
        record = next(item for item in description.get("group_geometry", ()) if item["target_id"] == group["id"])
        completeness = record["geometry_completeness"]
        status = f"{record['geometry_status'].upper()} {completeness['usable_members']}/{completeness['declared_members']} HOLES"
        _label(analysis_label_collection, status, (group_x, group_top + 0.28, 2.0), label_material, "analysis_status_label", group["id"], 0.09)
    for record in description.get("group_geometry", ()):
        group_id = record["target_id"]
        valid = record.get("member_geometry", ())
        centers = [item["center"] for item in valid if item.get("center")]
        anchor = (sum(point[0] for point in centers) / len(centers), sum(point[1] for point in centers) / len(centers)) if centers else None
        for member in valid:
            points = [(float(point[0]), float(point[1]), 1.2) for point in member.get("points", ())]
            if len(points) >= 2:
                _curve(overlay_collection, "Footprint_" + member["member_id"], points + [points[0]], footprint_material, "analysis_footprint", member["member_id"], 0.018)
            if member.get("center"):
                _curve(overlay_collection, "Center_" + member["member_id"], [(member["center"][0] - 0.06, member["center"][1], 1.3), (member["center"][0] + 0.06, member["center"][1], 1.3)], center_material, "analysis_center", member["member_id"], 0.012)
                _curve(overlay_collection, "CenterY_" + member["member_id"], [(member["center"][0], member["center"][1] - 0.06, 1.3), (member["center"][0], member["center"][1] + 0.06, 1.3)], center_material, "analysis_center", member["member_id"], 0.012)
        if anchor:
            for key, material, role in (("group_frame", frame_material, "analysis_group_frame"), ("group_axis", axis_material, "analysis_group_axis")):
                direction = record.get(key, {})
                angle = direction.get("angle")
                coherence = direction.get("coherence")
                if angle is None or coherence is None:
                    continue
                length = 0.50 if key == "group_frame" else 0.32
                radians = math.radians(float(angle))
                height = 1.4 if key == "group_frame" else 1.45
                start = (anchor[0] - length * math.cos(radians), anchor[1] - length * math.sin(radians), height)
                end = (anchor[0] + length * math.cos(radians), anchor[1] + length * math.sin(radians), height)
                glyph = _curve(overlay_collection, group_id + "_" + key, [start, end], material, role, group_id, 0.022)
                glyph["diagnostic_scope"] = "partial_usable_members_only"
    for collection in (body_collection, analysis_collection, overlay_collection, source_label_collection, analysis_label_collection):
        collection["d6_smoke_collection"] = True
    return {"collections": [body_collection.name, analysis_collection.name, overlay_collection.name, source_label_collection.name, analysis_label_collection.name], "body_objects": len(source_meshes), "analysis_objects": len(analysis_meshes)}


def _set_visibility(names: set[str]) -> None:
    """Show only named output collections for one render."""
    import bpy

    for collection in bpy.data.collections:
        if collection.get("d6_smoke_collection"):
            collection.hide_render = collection.name not in names


def main() -> None:
    """Build, render, save, and report the disposable smoke artifact."""
    import bpy

    args = _args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sample, description, inventory = _load(input_dir)
    points = _all_points(sample, description)
    if not points:
        raise RuntimeError("serialized smoke sample has no geometry for framing")
    _clear_startup_objects()
    _configure_scene()
    build = _build(sample, description, inventory)
    framing = _camera(points)
    scene = bpy.context.scene
    _set_visibility({"D6_Source_Body", "D6_Source_Labels"})
    scene.render.filepath = str(output_dir / "source_sample.png")
    bpy.ops.render.render(write_still=True)
    _set_visibility({"D6_Analysis_Terminal", "D6_Analysis_Overlays", "D6_Analysis_Labels"})
    scene.render.filepath = str(output_dir / "analysis_sample.png")
    bpy.ops.render.render(write_still=True)
    scene["d6_smoke_source_ifc"] = sample.get("sample_source")
    scene["d6_smoke_selected_groups"] = json.dumps(sample.get("selected_groups", ()), sort_keys=True)
    scene["d6_smoke_note"] = "Body and Analysis are separate output collections; labels and frame glyphs are display-only."
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "three_group_smoke.blend"))
    print(json.dumps({"status": "pass", "build": build, "framing": framing, "source_png": str(output_dir / "source_sample.png"), "analysis_png": str(output_dir / "analysis_sample.png"), "blend": str(output_dir / "three_group_smoke.blend")}, sort_keys=True))


if __name__ == "__main__":
    main()
