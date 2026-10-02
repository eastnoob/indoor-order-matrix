"""Render a disposable Blender preview for the boundary-construction probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def _material(name: str, color: tuple[float, float, float, float]):
    """Create one simple Principled material for the disposable preview."""
    import bpy

    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is not None:
        node.inputs["Base Color"].default_value = color
        node.inputs["Roughness"].default_value = 0.72
    return material


def _mesh_object(name: str, points: list[list[float]], material, z: float = 0.0):
    """Create a flat polygon mesh at a controlled preview height."""
    import bpy

    vertices = [(float(point[0]), float(point[1]), z) for point in points[:-1]]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], [list(range(len(vertices)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def _curve_object(name: str, points: list[list[float]], material, z: float, bevel: float = 0.035):
    """Create a colored curve overlay for one candidate ring."""
    import bpy

    curve = bpy.data.curves.new(name + "Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for spline_point, point in zip(spline.points, points):
        spline_point.co = (float(point[0]), float(point[1]), z, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def _text_object(body: str, location: tuple[float, float, float], material, size: float = 0.22):
    """Create compact plan-view text without touching a user scene."""
    import bpy

    curve = bpy.data.curves.new("TextCurve", type="FONT")
    curve.body = body
    curve.align_x = "LEFT"
    curve.size = size
    curve.extrude = 0.002
    obj = bpy.data.objects.new("Label_" + body.replace(" ", "_"), curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler[0] = 0.0
    obj.data.materials.append(material)
    return obj


def _configure_scene(output: Path, manifest: dict) -> None:
    """Build and render the disposable top-view scene from serialized evidence."""
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    wall_material = _material("PhysicalWallField", (0.20, 0.22, 0.25, 1.0))
    inner_material = _material("InnerWallFace", (0.05, 0.32, 0.90, 1.0))
    outer_material = _material("OuterWallFace", (0.86, 0.08, 0.06, 1.0))
    centerline_material = _material("WallCenterline", (0.04, 0.04, 0.05, 1.0))
    authored_material = _material("AuthoredClosedCurve", (0.03, 0.58, 0.16, 1.0))
    text_material = _material("Labels", (0.02, 0.02, 0.02, 1.0))

    source = manifest["cases"]["controlled_rectangular_room"]["source_geometry"]
    for wall in source["physical_wall_field_geometry"]:
        _mesh_object("PhysicalWall_" + wall["wall_ref"], wall["polygon"], wall_material, z=0.02)
    candidate_styles = {
        "inner_wall_face": (inner_material, 0.12),
        "outer_wall_face": (outer_material, 0.16),
        "wall_centerline": (centerline_material, 0.20),
        "authored_closed_curve": (authored_material, 0.24),
    }
    for kind, payload in source["candidate_geometry"].items():
        material, z = candidate_styles[kind]
        _curve_object("Candidate_" + kind, payload["points"], material, z)

    _text_object("physical wall field", (-0.1, -0.72, 0.30), text_material)
    _text_object("inner", (0.15, 6.24, 0.30), inner_material)
    _text_object("outer", (0.15, 5.93, 0.30), outer_material)
    _text_object("centerline", (0.15, 5.62, 0.30), centerline_material)
    _text_object("authored", (0.15, 5.31, 0.30), authored_material)
    _text_object("automatic/derived candidate; candidate not accepted", (0.15, -1.14, 0.30), outer_material, 0.18)
    _text_object("user-confirmed", (0.15, -1.42, 0.30), authored_material, 0.18)
    _text_object("current Blender: current_blender_not_observed", (0.15, -1.70, 0.30), text_material, 0.18)

    bpy.ops.object.camera_add(location=(4.0, 3.0, 14.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 10.8
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera.rotation_euler[0] = 0.0
    camera.rotation_euler[1] = 0.0
    camera.rotation_euler[2] = 0.0
    camera.rotation_euler = (0.0, 0.0, 0.0)
    # A top-down camera looks along -Z; rotation is explicit for reproducibility.
    camera.rotation_euler[0] = 0.0
    camera.rotation_euler[1] = 0.0
    camera.rotation_euler[2] = 0.0
    camera.location = (4.0, 3.0, 14.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera.rotation_euler[0] = 0.0
    camera.rotation_euler[1] = 0.0
    camera.rotation_euler[2] = 0.0
    # Blender's camera default points along -Z, so the identity rotation is top view.
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(4.0, 3.0, 12.0))
    light = bpy.context.object
    light.data.energy = 1200.0
    light.data.shape = "DISK"
    light.data.size = 12.0

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output / "boundary_construction_preview.png")
    if scene.world is None:
        scene.world = bpy.data.worlds.new("BoundaryConstructionWorld")
    scene.world.color = (1.0, 1.0, 1.0)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        background.inputs["Strength"].default_value = 0.8
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "boundary_construction_preview.blend"))
    bpy.ops.render.render(write_still=True)


def _sha256(path: Path) -> str:
    """Return one artifact digest for the disposable manifest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _update_manifest(output: Path) -> None:
    """Refresh the primary artifact manifest after Blender writes its outputs."""
    manifest_path = output / "artifact_manifest.json"
    if not manifest_path.exists():
        return
    paths = [
        path
        for path in output.rglob("*")
        if path.is_file()
        and path.name not in {"artifact_manifest.json", "verification_report.json"}
        and not any(part.startswith("tmp_reproduction_") for part in path.relative_to(output).parts)
    ]
    manifest = {
        "schema": "d6-boundary-construction-artifact-manifest-v1",
        "artifacts": [
            {
                "path": str(path.relative_to(output)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(paths)
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    """Read the probe manifest and create only disposable Blender outputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(os.environ["BOUNDARY_MANIFEST"]) if os.environ.get("BOUNDARY_MANIFEST") else None)
    parser.add_argument("--output", type=Path, default=Path(os.environ["BOUNDARY_OUTPUT"]) if os.environ.get("BOUNDARY_OUTPUT") else None)
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(script_args)
    if args.manifest is None or args.output is None:
        parser.error("provide --manifest/--output or BOUNDARY_MANIFEST/BOUNDARY_OUTPUT")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    _configure_scene(args.output.resolve(), manifest)
    metadata = {
        "status": "rendered_disposable_preview",
        "blend": "boundary_construction_preview.blend",
        "png": "boundary_construction_preview.png",
        "source_manifest": str(args.manifest.resolve()),
        "current_user_blender_modified": False,
    }
    (args.output / "blender_render_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command_log = args.output / "command_log.json"
    if command_log.exists():
        command_payload = json.loads(command_log.read_text(encoding="utf-8"))
        command_payload["blender_render"] = {"argv": sys.argv, "exit_code": 0, "portable_blender": True}
        command_log.write_text(json.dumps(command_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _update_manifest(args.output.resolve())
    print(json.dumps({"blend": str(args.output / "boundary_construction_preview.blend"), "png": str(args.output / "boundary_construction_preview.png")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
