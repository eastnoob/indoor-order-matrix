"""Build a read-only Blender preview from Neutral Scene facts and matrix evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from html import escape
from math import cos, radians, sin
from pathlib import Path
from typing import Any


def _value(record: object, name: str, default: object = None) -> object:
    """Read one field from either a contract record or a plain mapping."""
    if isinstance(record, Mapping):
        return record.get(name, default)
    return getattr(record, name, default)


def _jsonable(value: object) -> object:
    """Convert contract records and geometry helpers into JSON-safe values."""
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return value


def _rect_points(record: object) -> list[list[float]]:
    """Extract a planar polygon from an inferred region or gap-path record."""
    points = _value(record, "points")
    if points:
        return [[float(point[0]), float(point[1]), 0.02] for point in points]
    rect = _value(record, "rect")
    if rect is None:
        bounds = _value(record, "bounds")
        if not bounds or len(bounds) != 4:
            return []
        left, bottom, right, top = (float(value) for value in bounds)
        return [
            [left, bottom, 0.02],
            [right, bottom, 0.02],
            [right, top, 0.02],
            [left, top, 0.02],
            [left, bottom, 0.02],
        ]
    cx = float(_value(rect, "cx", 0.0))
    cy = float(_value(rect, "cy", 0.0))
    width = float(_value(rect, "width", 0.0))
    height = float(_value(rect, "height", 0.0))
    return [
        [cx - width / 2, cy - height / 2, 0.02],
        [cx + width / 2, cy - height / 2, 0.02],
        [cx + width / 2, cy + height / 2, 0.02],
        [cx - width / 2, cy + height / 2, 0.02],
        [cx - width / 2, cy - height / 2, 0.02],
    ]


def _trend_axes(region: object) -> list[dict[str, object]]:
    """Expose both region trend axes without inventing a perceptual score."""
    metadata = _value(region, "metadata", {}) or {}
    trend = _value(region, "trend", {}) or {}
    primary = float(metadata.get("axis-angle", trend.get("primary_angle", 0.0)))
    secondary = float(metadata.get("secondary-axis-angle", trend.get("secondary_angle", primary + 90.0)))
    primary_strength = float(metadata.get("axis-strength", metadata.get("axis-trend-strength", trend.get("primary_strength", 0.0))))
    # A region trend is an orthogonal frame, so its clarity belongs to both
    # frame axes unless the analysis explicitly reports separate strengths.
    secondary_strength = float(metadata.get("secondary-axis-strength", trend.get("secondary_strength", primary_strength)))
    return [
        {"angle": primary, "strength": primary_strength, "axis": "primary"},
        {"angle": secondary, "strength": secondary_strength, "axis": "secondary"},
    ]


def build_preview_manifest(scene: object, matrix: Mapping[str, object]) -> dict[str, object]:
    """Build a deterministic preview manifest while preserving source inputs."""
    source_objects = _value(scene, "source_objects", ()) or ()
    geometries = {
        str(_value(geometry, "id")): geometry
        for geometry in (_value(scene, "geometries", ()) or ())
    }
    source_geometry = []
    # Copy only referenced source meshes so the preview cannot silently include
    # unselected Blender objects or adapter-private geometry.
    for source in source_objects:
        source_id = str(_value(source, "id", _value(source, "source_id", "")))
        for geometry_id in _value(source, "geometry_refs", ()) or ():
            geometry = geometries.get(str(geometry_id))
            if geometry is None:
                continue
            source_geometry.append(
                {
                    "source_id": source_id,
                    "source_role": str(
                        _value(source, "source_role", _value(source, "role", "unknown"))
                        or "unknown"
                    ),
                    "source_class": str(_value(source, "source_class", "") or ""),
                    "geometry_id": str(geometry_id),
                    "vertices": _jsonable(_value(geometry, "vertices", ())),
                    "faces": _jsonable(
                        _value(
                            geometry,
                            "triangle_indices",
                            _value(geometry, "faces", ()),
                        )
                    ),
                }
            )
    regions = []
    # Derived geometry remains a separate output layer; it never replaces the
    # source mesh records used to explain the analysis.
    for region in matrix.get("inferred_regions", ()) or ():
        regions.append(
            {
                "id": str(_value(region, "id", "")),
                "points": _rect_points(region),
                "trend_axes": _trend_axes(region),
            }
        )
    paths = []
    for path in matrix.get("gap_paths", matrix.get("inferred_region_gap_paths", ())) or ():
        region_ids = list(_value(path, "region_ids", ()) or ())
        if not region_ids:
            region_ids = [
                str(value)
                for value in (_value(path, "region_a"), _value(path, "region_b"))
                if value
            ]
        paths.append(
            {
                "id": str(_value(path, "id", "")),
                "points": _rect_points(path),
                "region_ids": region_ids,
                "thickness": float(_value(path, "thickness", 0.0) or 0.0),
            }
        )
    grid_axes = [
        {
            "id": str(_value(axis, "id", "")),
            "curve_points": _jsonable(_value(axis, "curve_points", ())),
        }
        for axis in (_value(scene, "authored_grid_axes", ()) or ())
    ]
    channels = matrix.get("boundary_channels", matrix.get("boundary_semantics", ())) or ()
    boundary_channels = []
    # Keep factual channel observations and geometry references intact so the
    # viewport marker and notebook table remain traceable to source evidence.
    for channel in channels:
        boundary_channels.append(
            {
                "id": str(_value(channel, "id", "")),
                "source_id": str(_value(channel, "source_id", _value(channel, "id", ""))),
                "geometry_refs": list(
                    _value(channel, "source_geometry_refs", _value(channel, "geometry_refs", ())) or ()
                ),
                "walking": _value(channel, "walking", _value(channel, "walking_permeability_status", "unknown")),
                "visual": _value(channel, "visual", _value(channel, "visual_permeability_status", "unknown")),
                "visible_transmittance": _jsonable(_value(channel, "visible_transmittance")),
                "uncertainties": _jsonable(_value(channel, "uncertainties", ())),
                "provenance": _jsonable(_value(channel, "provenance", {})),
            }
        )
    return {
        "version": 1,
        "collection": "OM_AnalysisPreview",
        "source_geometry": source_geometry,
        "regions": regions,
        "paths": paths,
        "grid_axes": grid_axes,
        "boundary_channels": boundary_channels,
    }


def write_preview_script(scene: object, matrix: Mapping[str, object], target: str | Path) -> Path:
    """Write a self-contained Blender script that creates only preview objects."""
    manifest = build_preview_manifest(scene, matrix)
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=True)
    # The generated script consumes one frozen manifest. Blender object state
    # is an output target only and cannot feed back into description evidence.
    script = f'''"""Generated output-only analysis preview."""
import json
import bpy
from math import cos, radians, sin

MANIFEST = json.loads({payload!r})

def _material(role, color):
    """Create or reuse a tagged preview material without touching source materials."""
    material = next((item for item in bpy.data.materials if item.get("om_analysis_preview") and item.get("om_role") == role), None)
    material = material or bpy.data.materials.new("OM_AnalysisPreview_" + role)
    material["om_analysis_preview"] = True
    material["om_role"] = role
    material.diffuse_color = (*color, 1.0)
    return material

def _source_material(role):
    """Choose restrained preview colors from factual source roles."""
    colors = {{"floor": (0.75, 0.75, 0.75), "space": (0.82, 0.82, 0.82), "wall": (0.28, 0.28, 0.28), "furniture": (0.48, 0.48, 0.48), "surface": (0.65, 0.55, 0.25)}}
    return _material("Source_" + role, colors.get(role, (0.42, 0.42, 0.42)))

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
    region_material = _material("InferredRegion", (0.1, 0.7, 0.2))
    trend_material = _material("TrendAxes", (1.0, 0.35, 0.05))
    grid_material = _material("AuthoredGrid", (0.05, 0.7, 0.9))
    path_material = _material("GapPaths", (0.85, 0.1, 0.75))
    boundary_material = _material("BoundaryChannels", (0.9, 0.1, 0.1))
    for item in MANIFEST["source_geometry"]:
        _mesh(collection, "OM_Source_" + item["geometry_id"], item["vertices"], item["faces"], _source_material(item["source_role"]))
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
    geometry_by_id = {{item["geometry_id"]: item for item in MANIFEST["source_geometry"]}}
    for channel in MANIFEST["boundary_channels"]:
        vertices = [vertex for ref in channel["geometry_refs"] for vertex in geometry_by_id.get(ref, {{"vertices": []}})["vertices"]]
        if vertices:
            cx = sum(vertex[0] for vertex in vertices) / len(vertices)
            cy = sum(vertex[1] for vertex in vertices) / len(vertices)
            z = max(vertex[2] for vertex in vertices) + 0.12
            _curve(collection, "OM_Boundary_" + channel["id"] + "_a", [[cx - 0.15, cy - 0.15, z], [cx + 0.15, cy + 0.15, z]], boundary_material, 0.045)
            _curve(collection, "OM_Boundary_" + channel["id"] + "_b", [[cx - 0.15, cy + 0.15, z], [cx + 0.15, cy - 0.15, z]], boundary_material, 0.045)
    return {{"collection": collection.name, "counts": {{"source": len(MANIFEST["source_geometry"]), "regions": len(MANIFEST["regions"]), "paths": len(MANIFEST["paths"])}}}}

RESULT = build_preview()
print(json.dumps(RESULT, sort_keys=True))
'''
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(script, encoding="utf-8")
    return output


def _spatial_svg(manifest: Mapping[str, object]) -> str:
    """Render one plan-view SVG from the exact serialized preview manifest."""
    all_points: list[Sequence[float]] = []
    for geometry in manifest.get("source_geometry", ()):
        all_points.extend(geometry.get("vertices", ()))
    for key, field in (("regions", "points"), ("paths", "points"), ("grid_axes", "curve_points")):
        for item in manifest.get(key, ()):
            all_points.extend(item.get(field, ()))
    if not all_points:
        return "<svg viewBox='0 0 800 500'></svg>"
    min_x = min(float(point[0]) for point in all_points)
    max_x = max(float(point[0]) for point in all_points)
    min_y = min(float(point[1]) for point in all_points)
    max_y = max(float(point[1]) for point in all_points)
    scale = min(740.0 / max(1e-9, max_x - min_x), 440.0 / max(1e-9, max_y - min_y))

    def screen(point: Sequence[float]) -> tuple[float, float]:
        """Map world XY into a stable top-view SVG coordinate."""
        return (30.0 + (float(point[0]) - min_x) * scale, 470.0 - (float(point[1]) - min_y) * scale)

    def points_text(points: Sequence[Sequence[float]]) -> str:
        """Serialize world points into an SVG point-list token."""
        return " ".join(f"{x:.2f},{y:.2f}" for x, y in (screen(point) for point in points))

    layers = ["<svg viewBox='0 0 800 500' role='img' aria-label='BIM spatial evidence'>"]
    # Layer ordering keeps the original mesh visible below translucent paths,
    # region outlines, trend frames, grid axes, and boundary markers.
    for geometry in manifest.get("source_geometry", ()):
        vertices = geometry.get("vertices", ())
        role = str(geometry.get("source_role", "unknown"))
        source_style = {
            "floor": ("#d4d4d4", "0.10"),
            "space": ("#e5e7eb", "0.06"),
            "wall": ("#525252", "0.38"),
            "furniture": ("#a3a3a3", "0.48"),
            "surface": ("#eab308", "0.20"),
        }.get(role, ("#a3a3a3", "0.30"))
        for face in geometry.get("faces", ()):
            polygon = [vertices[index] for index in face]
            layers.append(f"<polygon data-layer='source-geometry' data-role='{escape(role)}' points='{points_text(polygon)}' fill='{source_style[0]}' fill-opacity='{source_style[1]}' stroke='#666' stroke-width='0.55'/>")
    for path in manifest.get("paths", ()):
        layers.append(f"<polygon data-layer='gap-path' points='{points_text(path.get('points', ())) }' fill='#d946ef' fill-opacity='0.18' stroke='#a21caf' stroke-width='1.2'/>")
    for region in manifest.get("regions", ()):
        points = region.get("points", ())
        layers.append(f"<polyline data-layer='region' points='{points_text(points)}' fill='none' stroke='#16a34a' stroke-width='2.2'/>")
        if points:
            center_points = points[:-1] if len(points) > 1 and points[0] == points[-1] else points
            cx = sum(float(point[0]) for point in center_points) / len(center_points)
            cy = sum(float(point[1]) for point in center_points) / len(center_points)
            for axis in region.get("trend_axes", ()):
                length = 0.7 * max(0.15, float(axis.get("strength", 0.0)))
                angle = radians(float(axis.get("angle", 0.0)))
                start = screen((cx - cos(angle) * length, cy - sin(angle) * length))
                end = screen((cx + cos(angle) * length, cy + sin(angle) * length))
                layers.append(f"<line data-layer='trend-axis' x1='{start[0]:.2f}' y1='{start[1]:.2f}' x2='{end[0]:.2f}' y2='{end[1]:.2f}' stroke='#f97316' stroke-width='3'/>")
    for axis in manifest.get("grid_axes", ()):
        layers.append(f"<polyline data-layer='grid-axis' points='{points_text(axis.get('curve_points', ())) }' fill='none' stroke='#06b6d4' stroke-width='1.5' stroke-dasharray='6 4'/>")
    geometry_by_id = {item.get("geometry_id"): item for item in manifest.get("source_geometry", ())}
    for channel in manifest.get("boundary_channels", ()):
        vertices = [vertex for ref in channel.get("geometry_refs", ()) for vertex in geometry_by_id.get(ref, {}).get("vertices", ())]
        if vertices:
            center = screen((sum(float(vertex[0]) for vertex in vertices) / len(vertices), sum(float(vertex[1]) for vertex in vertices) / len(vertices)))
            layers.append(f"<circle data-layer='boundary-channel' data-id='{escape(str(channel.get('id', '')))}' cx='{center[0]:.2f}' cy='{center[1]:.2f}' r='5' fill='#dc2626'/>")
    layers.append("</svg>")
    return "".join(layers)


def write_preview_html(manifest: Mapping[str, object], target: str | Path) -> Path:
    """Write a compact inspectable HTML table directly from serialized evidence."""
    rows = []
    for region in manifest.get("regions", ()):
        axes = region.get("trend_axes", ())
        rows.append(
            "<tr><td>{}</td><td>{:.2f}</td><td>{:.3f}</td><td>{:.2f}</td><td>{:.3f}</td></tr>".format(
                region.get("id", ""),
                float(axes[0].get("angle", 0.0)),
                float(axes[0].get("strength", 0.0)),
                float(axes[1].get("angle", 0.0)),
                float(axes[1].get("strength", 0.0)),
            )
        )
    html = """<!doctype html><meta charset='utf-8'><title>BIM description preview</title>
<style>body{{font:14px sans-serif;margin:2rem}}svg{{width:100%;max-height:70vh;border:1px solid #bbb}}table{{border-collapse:collapse}}th,td{{border:1px solid #bbb;padding:.35rem .6rem}}</style>
<h1>BIM description preview</h1><p>Evidence only; no fitted weights or scores.</p>
{}
<table><thead><tr><th>Region</th><th>Primary angle</th><th>Primary strength</th><th>Secondary angle</th><th>Secondary strength</th></tr></thead>
<tbody>{}</tbody></table><p>Source geometry: {} | Paths: {} | Grid axes: {} | Boundary channels: {}</p>""".format(
        _spatial_svg(manifest),
        "".join(rows),
        len(manifest.get("source_geometry", ())),
        len(manifest.get("paths", ())),
        len(manifest.get("grid_axes", ())),
        len(manifest.get("boundary_channels", ())),
    )
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def write_preview_manifest(manifest: Mapping[str, object], target: str | Path) -> Path:
    """Write the preview evidence as deterministic JSON for notebook inspection."""
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Persist the exact records consumed by HTML and Blender so a visual cannot
    # conceal missing evidence behind an in-memory-only transformation.
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return output


__all__ = [
    "build_preview_manifest",
    "write_preview_html",
    "write_preview_manifest",
    "write_preview_script",
]
