"""Render saved trend parity evidence without recomputing any metric."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def mat(name: str, color: tuple[float, float, float]) -> object:
    """Create one material for a named evidence channel."""
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    return material


def text(value: str, location: tuple[float, float], size: float, material: object, name: str) -> None:
    """Place a compact top-down label so meaning survives grayscale viewing."""
    data = bpy.data.curves.new(name, type="FONT")
    data.body = value[:120]
    data.align_x = "CENTER"
    data.size = size
    data.extrude = 0.001
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = (location[0], location[1], 0.45)
    obj.data.materials.append(material)


def line(start: tuple[float, float], end: tuple[float, float], radius: float, material: object, name: str) -> None:
    """Draw one vector with a channel-specific width and object name."""
    a, b = Vector((*start, 0.25)), Vector((*end, 0.25))
    delta = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=delta.length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    obj.data.materials.append(material)


def polygon(points: list[list[float]], origin: tuple[float, float], scale: float, material: object, name: str) -> None:
    """Draw one serialized Analysis footprint polygon."""
    vertices = [(origin[0] + point[0] * scale, origin[1] + point[1] * scale, 0.12) for point in points]
    if len(vertices) < 3:
        return
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [list(range(len(vertices)))])
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)


def render_case(case: dict[str, object], origin: tuple[float, float], materials: dict[str, object], name: str, contract_label: str) -> None:
    """Render one saved parity case using only serialized coordinates and angles."""
    footprints = case.get("footprints", [])
    raw = case.get("comparison", {}).get("raw_angles_deg", {})
    all_points = [point for item in footprints for ring in item.get("polygons", []) for point in ring]
    if not all_points:
        text(f"{case['group_id']} {case['status']}", origin, 0.12, materials["text"], f"title_{name}")
        return
    cx = sum(point[0] for point in all_points) / len(all_points)
    cy = sum(point[1] for point in all_points) / len(all_points)
    span = max(max(point[0] for point in all_points) - min(point[0] for point in all_points), max(point[1] for point in all_points) - min(point[1] for point in all_points), 1e-9)
    scale = 3.0 / span
    shifted = (origin[0] - cx * scale, origin[1] - cy * scale)
    for item in footprints:
        for index, ring in enumerate(item.get("polygons", [])):
            polygon(ring, shifted, scale, materials["footprint"], f"{name}_{item.get('member_id')}_{index}")
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.07, location=(origin[0], origin[1], 0.3))
    bpy.context.object.data.materials.append(materials["center"])
    text(f"{case['group_id']} | {case['status']}", (origin[0], origin[1] + 2.1), 0.12, materials["text"], f"title_{name}")
    text(f"contract: {contract_label}", (origin[0], origin[1] - 1.75), 0.075, materials["text"], f"contract_{name}")
    text("A solid frame | C thick axis | D thin axis | B dashed label", (origin[0], origin[1] - 1.98), 0.07, materials["text"], f"legend_{name}")
    channels = [("A", "A_frame", "a", 1.15, 0.034), ("C", "C", "c", 1.35, 0.046), ("D", "D", "d", 1.0, 0.026), ("B", "B", "b", 0.9, 0.018)]
    for label, key, material_key, length, radius in channels:
        angle = raw.get(key)
        if angle is None:
            continue
        theta = math.radians(float(angle))
        start = (origin[0] - length * math.cos(theta), origin[1] - length * math.sin(theta))
        end = (origin[0] + length * math.cos(theta), origin[1] + length * math.sin(theta))
        line(start, end, radius, materials[material_key], f"{name}_{label}_{float(angle):.3f}")
        text(f"{label}={float(angle):.3f}°", (origin[0] + (label == "B") * 0.35, origin[1] - 1.48 - channels.index((label, key, material_key, length, radius)) * 0.12), 0.07, materials[material_key], f"angle_{name}_{label}")


def _hash(path: Path) -> str:
    """Return a SHA-256 hash for one rendered artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render(data: dict[str, object], registry: dict[str, object], output_dir: Path) -> None:
    """Render synthetic and real panels from saved parity JSON and registry metadata."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials = {"footprint": mat("Analysis footprint", (0.35, 0.38, 0.48)), "center": mat("area weighted center", (0.98, 0.88, 0.12)), "a": mat("A member orientation", (0.18, 0.82, 0.38)), "c": mat("C total covariance", (0.98, 0.46, 0.15)), "d": mat("D centroid placement", (0.75, 0.28, 0.82)), "b": mat("B legacy diagnostic", (0.25, 0.72, 0.92)), "text": mat("labels", (0.92, 0.92, 0.92))}
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 0))
    bpy.context.object.data.materials.append(mat("ground", (0.02, 0.03, 0.05)))
    output_dir.mkdir(parents=True, exist_ok=True)
    contract_label = registry["contracts"]["trend_analysis"]["display"]["label"]
    for index, case in enumerate(data["synthetic_parity"]):
        render_case(case, (-10.5 + (index % 4) * 7.0, 6.2 - (index // 4) * 4.8), materials, f"synthetic_{index}", contract_label)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 2200, 1600, 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("trend_parity_world")
    scene.world.color = (0.01, 0.015, 0.025)
    bpy.ops.object.camera_add(location=(0.0, 0.0, 24.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 25.0
    scene.camera = camera
    synthetic_path = (output_dir / "synthetic_trend_substitute_contract_parity.png").resolve()
    scene.render.filepath = str(synthetic_path)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials = {"footprint": mat("Analysis footprint", (0.35, 0.38, 0.48)), "center": mat("area weighted center", (0.98, 0.88, 0.12)), "a": mat("A member orientation", (0.18, 0.82, 0.38)), "c": mat("C total covariance", (0.98, 0.46, 0.15)), "d": mat("D centroid placement", (0.75, 0.28, 0.82)), "b": mat("B legacy diagnostic", (0.25, 0.72, 0.92)), "text": mat("labels", (0.92, 0.92, 0.92))}
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    bpy.context.object.data.materials.append(mat("ground real", (0.02, 0.03, 0.05)))
    for index, case in enumerate(data["ifc_parity"]):
        render_case(case, (-6.2 + index * 6.2, 0.0), materials, f"ifc_{index}", contract_label)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 2000, 900, 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("trend_parity_ifc_world")
    scene.world.color = (0.01, 0.015, 0.025)
    bpy.ops.object.camera_add(location=(0.0, 0.0, 22.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 20.0
    scene.camera = camera
    real_path = (output_dir / "real_ifc_trend_substitute_contract_parity.png").resolve()
    scene.render.filepath = str(real_path)
    bpy.ops.render.render(write_still=True)
    blend_path = (output_dir / "trend_substitute_contract_parity.blend").resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    manifest = {"schema": "d6-trend-substitute-contract-parity-visual-manifest/v1", "source_parity_json": str((output_dir / "trend_substitute_contract_parity.json").resolve()).replace("\\", "/"), "registry_schema": registry.get("schema"), "display_spec": registry["contracts"]["trend_analysis"]["display"], "recomputed_metrics": False, "winner": None, "artifacts": [{"path": str(synthetic_path).replace("\\", "/"), "sha256": _hash(synthetic_path)}, {"path": str(real_path).replace("\\", "/"), "sha256": _hash(real_path)}, {"path": str(blend_path).replace("\\", "/"), "sha256": _hash(blend_path)}], "manual_inspection": {"synthetic": "rendered_pending_visual_inspection", "real_ifc": "rendered_pending_visual_inspection"}}
    (output_dir / "d6-trend-substitute-contract-parity-visual-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "artifact_manifest.json").write_text(json.dumps({"schema": "d6-trend-substitute-contract-parity-artifacts/v1", "artifacts": manifest["artifacts"], "source_sha256": data.get("source_result")}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    """Load saved parity evidence and invoke the output-only renderer."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    render(json.loads(args.input.read_text(encoding="utf-8")), json.loads(args.registry.read_text(encoding="utf-8")), args.output_dir)


if __name__ == "__main__":
    main()
