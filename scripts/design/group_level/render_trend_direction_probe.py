"""Render serialized D6 trend estimands as output-only Blender overlays."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def material(name: str, color: tuple[float, float, float]) -> object:
    """Create an opaque display material for one evidence channel."""
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    return mat


def label(text: str, location: tuple[float, float], size: float, mat: object, name: str) -> None:
    """Add a compact top-down label with a fixed display position."""
    data = bpy.data.curves.new(name, type="FONT")
    data.body = text
    data.align_x = "CENTER"
    data.size = size
    data.extrude = 0.002
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = (location[0], location[1], 0.35)
    obj.data.materials.append(mat)


def segment(start: tuple[float, float], end: tuple[float, float], radius: float, mat: object, name: str) -> None:
    """Draw one serialized direction or center marker."""
    a, b = Vector((*start, 0.22)), Vector((*end, 0.22))
    delta = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=delta.length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    obj.data.materials.append(mat)


def footprint(points: list[list[float]], origin: tuple[float, float], scale: float, mat: object, name: str) -> None:
    """Draw a footprint from serialized polygon vertices only."""
    vertices = [(origin[0] + point[0] * scale, origin[1] + point[1] * scale, 0.12) for point in points]
    if len(vertices) < 3:
        return
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [list(range(len(vertices)))])
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)


def display_transform(case: dict[str, object], origin: tuple[float, float], panel_width: float = 7.2) -> tuple[tuple[float, float], float]:
    """Choose a display-only translation and scale; no metric is recomputed."""
    points = [point for item in case.get("footprints", []) for polygon in item["polygons"] for point in polygon]
    if not points:
        return origin, 1.0
    cx = sum(point[0] for point in points) / len(points)
    cy = sum(point[1] for point in points) / len(points)
    span = max(max(point[0] for point in points) - min(point[0] for point in points), max(point[1] for point in points) - min(point[1] for point in points), 1e-9)
    return origin, 3.3 / span


def render_panel(case: dict[str, object], origin: tuple[float, float], mats: dict[str, object], panel_name: str) -> None:
    """Render one case with separate consensus, total, between, and legacy glyphs."""
    origin, scale = display_transform(case, origin)
    points = [point for item in case.get("footprints", []) for polygon in item["polygons"] for point in polygon]
    estimands = case.get("estimands") or (case.get("usable_subset") or {}).get("estimands") or {}
    total_record = estimands.get("area_weighted_total_covariance_pca", {})
    group_center = total_record.get("center") or estimands.get("between_member_centroid_pca", {}).get("center")
    if group_center is None:
        group_center = [sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points)] if points else [0.0, 0.0]
    cx, cy = group_center
    center = origin
    for item in case.get("footprints", []):
        for index, polygon in enumerate(item["polygons"]):
            footprint(polygon, (origin[0] - cx * scale, origin[1] - cy * scale), scale, mats["member"], f"{panel_name}_{item['member_id']}_{index}")
    label(str(case["id"]), (origin[0], origin[1] + 2.1), 0.18, mats["text"], f"title_{panel_name}")
    label(str(case["status"]), (origin[0], origin[1] - 2.0), 0.13, mats["status_invalid"] if case["status"] != "computed" else mats["text"], f"status_{panel_name}")
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.07, location=(center[0], center[1], 0.3))
    bpy.context.object.data.materials.append(mats["center"])
    directions = [("member", estimands.get("member_orientation_consensus", {}).get("frame_angle_deg")), ("total", estimands.get("area_weighted_total_covariance_pca", {}).get("angle_deg")), ("between", estimands.get("between_member_centroid_pca", {}).get("angle_deg")), ("legacy", estimands.get("legacy_projected_point_cloud_pca", {}).get("angle_deg"))]
    for key, angle in directions:
        if angle is None:
            continue
        radians = math.radians(float(angle))
        length = 1.25 if key != "legacy" else 1.05
        start = (center[0] - length * math.cos(radians), center[1] - length * math.sin(radians))
        end = (center[0] + length * math.cos(radians), center[1] + length * math.sin(radians))
        segment(start, end, 0.025 if key != "legacy" else 0.015, mats[key], f"{panel_name}_{key}")
    lines = []
    for key, short in (("member", "A"), ("total", "C"), ("between", "D"), ("legacy", "B")):
        value = estimands.get({"member": "member_orientation_consensus", "total": "area_weighted_total_covariance_pca", "between": "between_member_centroid_pca", "legacy": "legacy_projected_point_cloud_pca"}[key], {})
        angle = value.get("frame_angle_deg", value.get("angle_deg"))
        lines.append(f"{short}:{'undef' if angle is None else round(float(angle), 1)}")
    label(" ".join(lines), (origin[0], origin[1] - 1.68), 0.11, mats["text"], f"metrics_{panel_name}")


def render(data: dict[str, object], output_dir: Path) -> None:
    """Create two orthographic images from serialized synthetic and IFC values."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {"member": material("member_orientation_consensus", (0.18, 0.82, 0.38)), "center": material("center", (0.98, 0.90, 0.18)), "total": material("total_covariance_pca", (0.98, 0.46, 0.15)), "between": material("between_centroid_pca", (0.75, 0.28, 0.82)), "legacy": material("legacy_point_cloud_pca", (0.25, 0.72, 0.92)), "text": material("text", (0.92, 0.92, 0.92)), "status_invalid": material("status_invalid", (0.98, 0.30, 0.24))}
    # A flat ground plane only separates panels; no source geometry is inferred here.
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    bpy.context.object.data.materials.append(material("ground", (0.025, 0.035, 0.05)))
    output_dir.mkdir(parents=True, exist_ok=True)
    synthetic = data["synthetic_cases"]
    for index, case in enumerate(synthetic):
        render_panel(case, (-10.5 + (index % 4) * 7.0, 5.2 - (index // 4) * 5.7), mats, f"synthetic_{index}")
    label("green=A member orientation | orange=C total | purple=D between | cyan=B legacy", (0.0, -9.0), 0.16, mats["text"], "legend_synthetic")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 2000, 1400, 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("trend_direction_world")
    scene.world.color = (0.01, 0.015, 0.025)
    scene.camera = None
    bpy.ops.object.camera_add(location=(0.0, -1.0, 24.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 26.0
    scene.camera = camera
    synthetic_path = (output_dir / "synthetic_trend_direction.png").resolve()
    scene.render.filepath = str(synthetic_path)
    bpy.ops.render.render(write_still=True)
    # Keep the real IFC sample in a separate image and collection coordinate frame.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {"member": material("member_orientation_consensus", (0.18, 0.82, 0.38)), "center": material("center", (0.98, 0.90, 0.18)), "total": material("total_covariance_pca", (0.98, 0.46, 0.15)), "between": material("between_centroid_pca", (0.75, 0.28, 0.82)), "legacy": material("legacy_point_cloud_pca", (0.25, 0.72, 0.92)), "text": material("text", (0.92, 0.92, 0.92)), "status_invalid": material("status_invalid", (0.98, 0.30, 0.24))}
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    bpy.context.object.data.materials.append(material("ground_real", (0.025, 0.035, 0.05)))
    for index, case in enumerate(data["ifc_cases"]):
        render_panel(case, (-6.2 + index * 6.2, 0.0), mats, f"ifc_{index}")
    label("IFC Analysis footprints | green=A | orange=C | purple=D | cyan=B", (0.0, 2.5), 0.18, mats["text"], "legend_ifc")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1800, 900, 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("trend_direction_ifc_world")
    scene.world.color = (0.01, 0.015, 0.025)
    bpy.ops.object.camera_add(location=(0.0, 0.0, 22.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 20.0
    scene.camera = camera
    real_path = (output_dir / "ifc_trend_direction.png").resolve()
    scene.render.filepath = str(real_path)
    blend_path = (output_dir / "trend_direction_probe.blend").resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.render.render(write_still=True)
    (output_dir / "blender_render_metadata.json").write_text(json.dumps({"schema": "d6-trend-direction-render/v1", "source": "trend_direction_results.json", "synthetic_render": str(synthetic_path).replace("\\", "/"), "ifc_render": str(real_path).replace("\\", "/"), "blend": str(blend_path).replace("\\", "/"), "recomputed_metrics": False, "display_only_transform": True}, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Load saved numeric evidence and render it in portable Blender."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    render(json.loads(args.input.read_text(encoding="utf-8")), args.output_dir)


if __name__ == "__main__":
    main()
