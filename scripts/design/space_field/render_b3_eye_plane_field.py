"""Render primary-plane evidence over frozen Body meshes in a disposable Blender."""

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from render_b3_real_field_blender import collection, curve_object, label, rings


def main():
    """Reuse output-only drawing helpers without the earlier band metadata or live scene."""
    out = Path(sys.argv[sys.argv.index("--") + 1])
    root = Path(__file__).resolve().parents[3]
    preview = json.loads((out / "preview_input.json").read_text(encoding="utf-8"))
    capture_root = (root / preview["capture"]["path"]).parent
    field = json.loads((out / "field_samples.json").read_text(encoding="utf-8"))
    section_rows = json.loads((out / "source_sections.json").read_text(encoding="utf-8"))["records"]
    statuses = {row["id"]: row["status"] for row in section_rows}
    scene = bpy.context.scene
    scene["primary_plane_world_z_m"] = 1.6
    scene["plane_rule"] = "IFC storey #13 human datum 0 + eye offset 1.6 m"
    scene["complete_occupancy"] = "partial; see qualified sections and unresolved source support"
    scene["source_geometry"] = "frozen_actual_Body_world_metres_no_rescaling; canonical Analysis unchanged"
    sources = collection("B3_Eye_Frozen_Actual_Body")
    support = collection("B3_Eye_Slab_Support_Not_Occupancy")
    overlays = collection("B3_PRIMARY_Eye_Qualified_And_Unknown")
    labels = collection("B3_Eye_Inspection_Labels")
    counts = {"objects": 0, "vertices": 0, "triangles": 0}
    for row in preview["source_meshes"]:
        if row["geometry"] is None:
            continue
        record = json.loads((capture_root / row["geometry"]["path"]).read_text(encoding="utf-8"))
        assert record["units"] == "m" and record["transform_applied"] is True
        data = bpy.data.meshes.new(f"frozen:{row['id']}")
        data.from_pydata(record["vertices"], [], record["triangles"])
        data.update()
        obj = bpy.data.objects.new(f"Body:{row['id']}:{row['ifc_class']}", data)
        target = support if row["ifc_class"] == "IfcSlab" else sources
        target.objects.link(obj)
        obj.color = (.66, .70, .77, 1)
        obj["b3_preview"] = True
        obj["source_id"] = row["id"]
        obj["source_sha256"] = row["geometry"]["sha256"]
        obj["geometry_role"] = "frozen_actual_Body_audit" if target == sources else "support_excluded"
        obj["primary_plane_section_status"] = statuses[row["id"]]
        counts["objects"] += 1
        counts["vertices"] += len(record["vertices"])
        counts["triangles"] += len(record["triangles"])
    support.hide_render = True
    support.hide_viewport = True
    # Raised strokes make overlays legible above source meshes; their display elevation is not the query plane.
    curve_object("Historical S3 exterior + two holes", rings(preview["domain"]), (0, .55, .58), overlays, z=5.05, width=.035)
    curve_object("PRIMARY qualified occupied subset / exact-height query", rings(preview["occupied"]), (.7, .04, .56), overlays, z=5.15, width=.025)
    curve_object("Unresolved source supports / NOT occupancy", rings(preview["unknown"]), (.9, .46, 0), overlays, z=5.25, width=.02)
    camera_data = bpy.data.cameras.new("B3_Eye_Independent_Top_Camera")
    camera = bpy.data.objects.new("B3_Eye_Independent_Top_Camera", camera_data)
    labels.objects.link(camera)
    camera.location = (12.8, 6.3, 60)
    camera.rotation_euler = (0, 0, 0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 30.5
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.background_type = "WORLD"
    scene.world = bpy.data.worlds.new("B3_Eye_White_World")
    scene.world.color = (.95, .96, .98)
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    label("B3 PRIMARY / fixed world z = 1.6 m / qualified geometric subset", (.2, 14.05), labels, size=.38)
    label("Frozen actual Body + historical S3 / incomplete sources / independent disposable scene", (.2, 13.35), labels, size=.29)
    label("Teal: S3 + two holes | Magenta: occupied evidence | Orange: unresolved support, NOT mass", (.2, -1.2), labels, size=.27)
    label("IFC storey #13 human datum 0 + eye offset 1.6 m. No alternative height or band substitution.", (.2, -1.8), labels, size=.27)
    label("World XY / metres / equal aspect. Raised overlay strokes are display only; full clearance unknown.", (.2, -2.35), labels, size=.26)
    for x in range(0, 26, 5):
        label(str(x), (x, -.55), labels, size=.23)
    label("X (m)", (26, -.55), labels, size=.25)
    for y in range(0, 13, 2):
        label(str(y), (-.65, y), labels, size=.23)
    label("Y (m)", (-.7, 12.9), labels, size=.25)
    scene.render.filepath = str(out / "blender_primary_eye_plane.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "b3_primary_eye_disposable.blend"), compress=True)
    report = {"blender_version": bpy.app.version_string, "source_counts": counts,
              "render": scene.render.filepath, "blend": str(out / "b3_primary_eye_disposable.blend"),
              "primary_plane_world_z_m": field["primary_plane_world_z_m"],
              "original_live_scene": "not_loaded_or_modified", "source_geometry_transform": "frozen_world_metres_identity_no_second_scale",
              "overlay_elevation": "raised_display_only_query_remains_z1.6", "inspection": "pending_actual_image_view"}
    with (out / "blender_runtime.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, allow_nan=False, indent=2)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
