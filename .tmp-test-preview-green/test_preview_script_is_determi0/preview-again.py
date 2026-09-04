"""Generated output-only analysis preview."""
import json
import bpy
from math import cos, radians, sin

MANIFEST = json.loads('{"boundary_channels": [{"geometry_refs": ["mesh-1"], "id": "wall-1", "provenance": {}, "source_id": "wall-1", "uncertainties": [], "visible_transmittance": null, "visual": "blocked", "walking": "blocked"}], "collection": "OM_AnalysisPreview", "grid_axes": [{"curve_points": [[0, 0, 0], [4, 0, 0]], "id": "axis-x"}], "paths": [{"id": "path-1", "points": [], "region_ids": ["region-1", "region-2"], "thickness": 0.6}], "regions": [{"id": "region-1", "points": [], "trend_axes": [{"angle": 0.0, "axis": "primary", "strength": 0.8}, {"angle": 90.0, "axis": "secondary", "strength": 0.2}]}], "source_geometry": [{"faces": [[0, 1, 2], [0, 2, 3]], "geometry_id": "mesh-1", "source_id": "table-1", "vertices": [[0, 0, 0], [2, 0, 0], [2, 1, 0], [0, 1, 0]]}], "version": 1}')

def _material(role, color):
    """Create or reuse a tagged preview material without touching source materials."""
    material = next((item for item in bpy.data.materials if item.get("om_analysis_preview") and item.get("om_role") == role), None)
    material = material or bpy.data.materials.new("OM_AnalysisPreview_" + role)
    material["om_analysis_preview"] = True
    material["om_role"] = role
    material.diffuse_color = (*color, 1.0)
    return material

def _collection():
    """Create the dedicated preview collection and never remove source data."""
    name = MANIFEST["collection"]
    collection = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if collection.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(collection)
    return collection

def _clear_preview_objects(collection):
    """Remove only objects previously created by this preview generator."""
    for obj in tuple(collection.objects):
        if obj.get("om_analysis_preview"):
            bpy.data.objects.remove(obj, do_unlink=True)

def _mesh(collection, name, vertices, faces, material):
    """Create one source-geometry copy inside the output-only collection."""
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj["om_analysis_preview"] = True
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def _curve(collection, name, points, material, bevel=0.025):
    """Create a polyline overlay for regions, axes, and paths."""
    curve = bpy.data.curves.new(name + "_curve", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel
    spline = curve.splines.new("POLY")
    spline.points.add(max(0, len(points) - 1))
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1.0)
    obj = bpy.data.objects.new(name, curve)
    obj["om_analysis_preview"] = True
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def build_preview():
    """Materialize manifest evidence while leaving every source object intact."""
    collection = _collection()
    _clear_preview_objects(collection)
    source_material = _material("SourceGeometry", (0.35, 0.35, 0.35))
    region_material = _material("InferredRegion", (0.1, 0.7, 0.2))
    trend_material = _material("TrendAxes", (1.0, 0.35, 0.05))
    grid_material = _material("AuthoredGrid", (0.05, 0.7, 0.9))
    path_material = _material("GapPaths", (0.85, 0.1, 0.75))
    boundary_material = _material("BoundaryChannels", (0.9, 0.1, 0.1))
    for item in MANIFEST["source_geometry"]:
        _mesh(collection, "OM_Source_" + item["geometry_id"], item["vertices"], item["faces"], source_material)
    for region in MANIFEST["regions"]:
        _curve(collection, "OM_Region_" + region["id"], region["points"], region_material, 0.04)
        points = region["points"]
        if len(points) >= 2:
            cx = sum(point[0] for point in points[:-1]) / max(1, len(points) - 1)
            cy = sum(point[1] for point in points[:-1]) / max(1, len(points) - 1)
            for axis in region["trend_axes"]:
                length = 0.7 * max(0.15, float(axis["strength"]))
                angle = radians(float(axis["angle"]))
                _curve(collection, "OM_Trend_" + region["id"] + "_" + axis["axis"], [[cx - cos(angle)*length, cy - sin(angle)*length, 0.08], [cx + cos(angle)*length, cy + sin(angle)*length, 0.08]], trend_material, 0.05)
    for axis in MANIFEST["grid_axes"]:
        _curve(collection, "OM_Grid_" + axis["id"], axis["curve_points"], grid_material, 0.035)
    for path in MANIFEST["paths"]:
        _curve(collection, "OM_Path_" + path["id"], path["points"], path_material, 0.06)
    geometry_by_id = {item["geometry_id"]: item for item in MANIFEST["source_geometry"]}
    for channel in MANIFEST["boundary_channels"]:
        vertices = [vertex for ref in channel["geometry_refs"] for vertex in geometry_by_id.get(ref, {"vertices": []})["vertices"]]
        if vertices:
            cx = sum(vertex[0] for vertex in vertices) / len(vertices)
            cy = sum(vertex[1] for vertex in vertices) / len(vertices)
            z = max(vertex[2] for vertex in vertices) + 0.12
            _curve(collection, "OM_Boundary_" + channel["id"] + "_a", [[cx - 0.15, cy - 0.15, z], [cx + 0.15, cy + 0.15, z]], boundary_material, 0.045)
            _curve(collection, "OM_Boundary_" + channel["id"] + "_b", [[cx - 0.15, cy + 0.15, z], [cx + 0.15, cy - 0.15, z]], boundary_material, 0.045)
    return {"collection": collection.name, "counts": {"source": len(MANIFEST["source_geometry"]), "regions": len(MANIFEST["regions"]), "paths": len(MANIFEST["paths"])}}

RESULT = build_preview()
print(json.dumps(RESULT, sort_keys=True))
