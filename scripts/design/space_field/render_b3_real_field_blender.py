"""Render frozen Body geometry in an independent disposable Blender process."""

import json
import sys
from pathlib import Path

import bpy


def collection(name):
    """Keep frozen sources and each derived query in separate tagged collections."""
    result = bpy.data.collections.new(name)
    result["b3_preview"] = True
    bpy.context.scene.collection.children.link(result)
    return result


def curve_object(name, rings, color, target, z=5.0, width=.025):
    """Show serialized ring paths without changing the actual derived geometry."""
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = width
    data.bevel_resolution = 0
    for ring in rings:
        if len(ring) < 2:
            continue
        spline = data.splines.new("POLY")
        spline.points.add(len(ring) - 1)
        for point, coordinate in zip(spline.points, ring):
            point.co = (coordinate[0], coordinate[1], z, 1)
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    obj.color = (*color, 1)
    obj["b3_preview"] = True
    obj["geometry_role"] = "derived_overlay_ring_display_not_occupancy_buffer"
    obj["display_stroke_radius_m"] = width
    return obj


def rings(geometry):
    """Preserve all exterior and hole paths from the frozen GeoJSON geometry."""
    kind = geometry["type"]
    if kind == "Polygon":
        return geometry["coordinates"]
    if kind == "MultiPolygon":
        return [ring for polygon in geometry["coordinates"] for ring in polygon]
    if kind == "GeometryCollection":
        return [ring for child in geometry["geometries"] for ring in rings(child)]
    return []


def label(text, xy, target, size=.25, color=(.06, .08, .13)):
    """Add readable world-metre labels with the same XY orientation as the plan."""
    data = bpy.data.curves.new(text, "FONT")
    data.body = text
    data.size = size
    obj = bpy.data.objects.new(text, data)
    obj.location = (*xy, 6.0)
    obj.color = (*color, 1)
    obj["b3_preview"] = True
    obj["geometry_role"] = "inspection_label"
    target.objects.link(obj)
    return obj


def main():
    """Load only immutable JSON, save a new blend, and actually render three plans."""
    out = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    root = Path(__file__).resolve().parents[3]
    capture_root = root / "outputs/design/b3_real_source_field/run_001"
    preview = json.loads((out / "preview_input.json").read_text(encoding="utf-8"))
    # Factory-startup clears only this fresh process, never the original live scene.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene["b3_status"] = "partial_diagnostic_historical_snapshot_only"
    scene["world_units"] = "m; frozen_transform_applied_once; no_IFC_rescaling"
    scene["exact_section"] = "unsupported"
    sources = collection("B3_Frozen_Actual_Body")
    support = collection("B3_Support_Slab_Not_Occupancy")
    domain_collection = collection("B3_Historical_S3_Domain_Two_Holes")
    labels = collection("B3_Inspection_Labels")
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
        obj.color = (.66, .7, .77, 1)
        obj["b3_preview"] = True
        obj["geometry_role"] = "source_support_not_occupancy" if target == support else "frozen_actual_Body_design_only"
        obj["source_id"] = row["id"]
        obj["source_global_id"] = row["global_id"]
        obj["source_sha256"] = row["geometry"]["sha256"]
        obj["authored_participation"] = row.get("participation") or "not_available"
        obj["solid_query_eligible"] = row["solid_query_eligible"]
        obj["complete_physical_occupancy_status"] = "unsupported"
        counts["objects"] += 1
        counts["vertices"] += len(record["vertices"])
        counts["triangles"] += len(record["triangles"])
    support.hide_render = True
    support.hide_viewport = True
    curve_object("Historical S3 / exact exterior and two holes", rings(preview["domain"]), (.0, .55, .58), domain_collection, width=.04)
    query_collections = {}
    for name, query in preview["queries"].items():
        target = collection(f"B3_Derived_{name}_Partial")
        query_collections[name] = target
        curve_object("Approximate eligible band projection", rings(query["clipped_projection_geometry"]), (.7, .04, .56), target, z=5.15)
        curve_object("Unassessed candidate vertex hull supports / not occupancy", rings(query["clipped_uncertainty_support_geometry"]), (.9, .46, .0), target, z=5.25, width=.02)
    camera_data = bpy.data.cameras.new("B3_Independent_Top_Camera")
    camera = bpy.data.objects.new("B3_Independent_Top_Camera", camera_data)
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
    scene.world = bpy.data.worlds.new("B3_White_World")
    scene.world.color = (.95, .96, .98)
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    label("B3 / frozen actual Body + historical S3 / partial diagnostic", (.2, 14.05), labels, size=.4)
    query_label = label("Source geometry only", (.2, 13.35), labels, size=.32)
    label("Human Level 1 datum 0 m / floor top. Complete occupancy + exact section unsupported.", (.2, -1.2), labels, size=.29)
    label("Teal: S3 + two holes | Magenta: approximate band projection | Orange: unassessed support", (.2, -1.8), labels, size=.28)
    label("Complement is NOT known free. Stroke width is display only. World XY / metres / equal aspect.", (.2, -2.35), labels, size=.27)
    for x in range(0, 26, 5):
        label(str(x), (x, -.55), labels, size=.23)
    label("X (m)", (26, -.55), labels, size=.25)
    for y in range(0, 13, 2):
        label(str(y), (-.65, y), labels, size=.23)
    label("Y (m)", (-.7, 12.9), labels, size=.25)
    renders = []
    for name in ["source_domain", "provisional_eye", "independent_lower_diagnostic"]:
        for key, target in query_collections.items():
            target.hide_render = key != name
            target.hide_viewport = key != name
        query_label.data.body = {"source_domain": "SOURCE ONLY / actual Body geometry; slab support hidden",
                                 "provisional_eye": "EYE / band 1.55–1.65 m / reference 1.60 m / projection + uncertainty",
                                 "independent_lower_diagnostic": "LOWER / independent band 0.45–0.55 m / projection + uncertainty"}[name]
        scene.render.filepath = str(out / f"blender_{name}.png")
        bpy.ops.render.render(write_still=True)
        renders.append(scene.render.filepath)
    for key, target in query_collections.items():
        target.hide_render = key != "provisional_eye"
        target.hide_viewport = key != "provisional_eye"
    query_label.data.body = "EYE / band 1.55–1.65 m / reference 1.60 m / projection + uncertainty"
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "b3_real_partial_disposable.blend"), compress=True)
    report = {"blender_version": bpy.app.version_string, "source_counts": counts,
              "renders": renders, "blend": str(out / "b3_real_partial_disposable.blend"),
              "source_geometry_transform": "frozen_world_metres; identity_object_transform; no_second_scale",
              "original_live_scene": "not_loaded_or_modified", "default_visible_query": "provisional_eye",
              "inspection": "actual_image_content_not_yet_viewed"}
    with (out / "blender_runtime.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, allow_nan=False, indent=2)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
