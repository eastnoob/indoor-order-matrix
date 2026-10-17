"""Render preview-only whole-height polygons in a new portable Blender process."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from render_b3_real_field_blender import collection, curve_object, label, rings

BLENDER = Path("D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")
COLORS = {"chair": (.025, .20, .58), "table": (.72, .32, .025),
          "proxy": (.43, .13, .66), "physical_context": (.63, .05, .36),
          "conditional_free": (.48, .79, .56), "occupied": (.86, .49, .67), "unknown": (.95, .42, .02)}


def markers(preview, target):
    """Draw small squares at plan point samples without triangulating polygon interiors."""
    for status, points in preview["samples"].items():
        vertices, faces = [], []
        half = preview["sample_marker_side_m"] / 2
        for x, y in points:
            index = len(vertices)
            vertices.extend([(x-half, y-half, 0), (x+half, y-half, 0),
                             (x+half, y+half, 0), (x-half, y+half, 0)])
            faces.append((index, index+1, index+2, index+3))
        mesh = bpy.data.meshes.new(f"Point samples:{status}")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(f"Point samples:{status}:{len(points)}", mesh)
        target.objects.link(obj)
        obj.color = (*COLORS[status], 1)
        obj["geometry_role"] = "point_sample_markers_not_cell_or_polygon_fill"
        obj["marker_side_m"] = preview["sample_marker_side_m"]


def main():
    """Render rings, keep furniture identifiable, and save only new preview files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]).out.resolve()
    root = Path(__file__).resolve().parents[3]
    if out.parent != root / "outputs/design/b3_shared_occupancy_enrollment" or not out.name.startswith("preview_"):
        raise ValueError("Expected a fresh B3 preview directory")
    if not bpy.app.background or Path(bpy.app.binary_path).resolve() != BLENDER.resolve():
        raise RuntimeError("Expected the specified portable Blender in background mode")
    png, blend = out / "b3_whole_height_plan.png", out / "b3_whole_height_disposable.blend"
    if png.exists() or blend.exists():
        raise FileExistsError("Preview outputs already exist")
    preview_path = out / "preview_input.json"
    preview = json.loads(preview_path.read_text(encoding="utf-8"))
    assert preview["query"] == {"frame": "world_xy", "units": "m", "height_band": None}
    assert preview["complete_occupancy"] is None and preview["complete_clearance"] is None
    stats = preview["statistics"]
    # Reset only this factory-started background process; the live scene is never accessed.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["analysis_query"] = "whole-height world XY plan projection, not an exact-height section"
    scene["complete_occupancy_and_clearance"] = "null"
    scene["preview_input_sha256"] = hashlib.sha256(preview_path.read_bytes()).hexdigest()
    labels = collection("B3_Inspection_Labels")
    markers(preview, collection("B3_Conditional_Plan_Point_Samples"))
    curve_object("S3 exterior + two holes", rings(preview["domain"]), (0, .45, .60),
                 collection("B3_S3_Domain_Two_Holes"), z=.2, width=.02)
    curve_object("Selected whole-height occupied union", rings(preview["clipped_occupancy"]),
                 COLORS["physical_context"], collection("B3_Selected_Plan_Occupancy"), z=.4, width=.011)
    groups = {kind: collection(f"B3_Whole_Height_{kind}") for kind in ("chair", "table", "proxy")}
    displayed = Counter()
    for row in preview["projections"]:
        kind = row["kind"]
        if kind not in groups:
            continue
        # Furniture has its own raised outline so the occupied union cannot hide it.
        obj = curve_object(f"{kind}:{row['id']}:{row['name']}", rings(row["geometry"]),
                           COLORS[kind], groups[kind], z=1.2 if kind != "proxy" else .8,
                           width=.009 if kind == "chair" else .012)
        obj["source_id"] = row["id"]
        obj["projection_status"] = row["status"]
        obj["projection_height_band"] = "whole_height"
        obj["numerical_retry_warnings"] = json.dumps(row["numerical_retry_warnings"])
        obj["represented_owner_ids"] = json.dumps(row["represented_source_ids"])
        displayed[kind] += 1
    assert displayed["chair"] + displayed["table"] == stats["furniture_projection_success_count"]
    unknown_target = collection("B3_Unknown_Supports_Not_Occupancy")
    for row in preview["unknown_supports"]:
        curve_object(f"Unknown:{row['id']}:{row['reason']}", rings(row["geometry"]),
                     COLORS["unknown"], unknown_target, z=1.6, width=.014)
    door = preview["boundary_door"]
    obj = curve_object("Door live-step-6231 EXCLUDED", rings(door["reference_support"]), (.03, .04, .06),
                       collection("B3_Boundary_Door_Excluded_Reference"), z=1.8, width=.025)
    obj["geometry_role"] = door["status"]
    label("Door 6231 / excluded from interior mass", (5.7, -.38), labels, size=.23)
    label(preview["title"], (4.2, 14.45), labels, size=.41)
    label(f"Furniture {stats['furniture_count']}: {stats['chair_count']} chairs (blue) + {stats['table_count']} tables (brown) | "
          f"projected {stats['furniture_projection_success_count']} / failed {stats['furniture_projection_failure_count']}",
          (4.2, 13.8), labels, size=.28)
    label(f"Furniture union {stats['furniture_footprint_union_area_m2']:.3f} m2 | conditional free "
          f"{stats['unknown_masked_conditional_free_area_m2']:.3f} m2 | complete occupancy/clearance = null",
          (4.2, 13.2), labels, size=.27)
    label("Green: conditional free points | Pink: occupied points / magenta union | Teal: S3 + two holes", (4.2, -.95), labels, size=.25)
    label("Blue: chairs | Brown: tables | Purple: 3 whole-height proxies representing 7 owners once", (4.2, -1.45), labels, size=.25)
    label(f"Orange: {len(preview['unknown_supports'])} unknown supports; clipped area "
          f"{stats['clipped_unknown_support_area_m2']:.3f} m2 | Black: boundary door EXCLUDED", (4.2, -1.95), labels, size=.24)
    label("Whole height includes overhead projections. Convex proxies fill gaps. This is conditional, not certified clearance.",
          (4.2, -2.45), labels, size=.23)
    label("0.055 m markers at 0.15 m plan points; rings preserve holes/concavities. Raised strokes are display only.",
          (4.2, -2.95), labels, size=.23)
    for x in range(5, 26, 5):
        label(str(x), (x, -.6), labels, size=.18)
    label("X (m)", (26, -.6), labels, size=.18)
    for y in range(2, 13, 2):
        label(str(y), (4.65, y), labels, size=.18)
    label("Y (m)", (4.2, 12.6), labels, size=.18)
    camera_data = bpy.data.cameras.new("B3_Independent_Plan_Camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    labels.objects.link(camera)
    camera.location = (15.1, 6.1, 60)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 29
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.display.shading.background_type = "WORLD"
    scene.world = bpy.data.worlds.new("B3_White_World")
    scene.world.color = (.96, .97, .99)
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.render.filepath = str(png)
    assert bpy.ops.render.render(write_still=True) == {"FINISHED"}
    assert bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True) == {"FINISHED"}
    verification = {"blender_version": bpy.app.version_string, "background": bpy.app.background,
                    "render_operator_status": "FINISHED", "displayed_projection_counts": dict(displayed),
                    "sample_counts": {key: len(value) for key, value in preview["samples"].items()},
                    "domain_holes": len(preview["domain"]["coordinates"]) - 1,
                    "resolution": [2400, 1600], "render": str(png), "blend": str(blend)}
    with (out / "render_verification.json").open("x", encoding="utf-8") as stream:
        json.dump(verification, stream, indent=2)
    print(json.dumps(verification), flush=True)


if __name__ == "__main__":
    main()
