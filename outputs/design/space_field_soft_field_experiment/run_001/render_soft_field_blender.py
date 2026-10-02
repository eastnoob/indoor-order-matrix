"""Render disposable Blender plan views for the D6 soft-field experiment."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 2400, 1200
FRAME = (-1.28, -0.63, 26.88, 13.23)
COLORS = {
    "ink": (0.10, 0.14, 0.17),
    "muted": (0.35, 0.39, 0.42),
    "context": (0.68, 0.72, 0.74),
    "wall": (0.42, 0.46, 0.48),
    "furniture": (0.86, 0.83, 0.74),
    "frame": (0.76, 0.31, 0.12),
    "white": (1.0, 1.0, 1.0),
    "cyan": (0.10, 0.63, 0.72),
    "blue": (0.12, 0.36, 0.78),
    "orange": (0.92, 0.40, 0.10),
    "region": [(0.30, 0.47, 0.66), (0.91, 0.49, 0.19), (0.33, 0.63, 0.39), (0.82, 0.31, 0.29)],
}


def _read_json(path: Path) -> dict:
    """Read one experiment input JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _material(name: str, color: tuple[float, float, float], alpha: float = 1.0):
    """Create an unlit emission material with explicit transparency."""
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, alpha)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = alpha
    material.node_tree.links.new(transparent.outputs[0], mix.inputs[1])
    material.node_tree.links.new(emission.outputs[0], mix.inputs[2])
    material.node_tree.links.new(mix.outputs[0], output.inputs["Surface"])
    try:
        material.surface_render_method = "DITHERED"
    except (AttributeError, TypeError):
        pass
    return material


def _mesh(scene, name: str, vertices: list[tuple[float, float, float]], faces: list[tuple[int, ...]], material, z: float = 0.0):
    """Link one flat mesh into a disposable scene."""
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([(x, y, z) for x, y, _ in vertices], [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def _poly(scene, name: str, ring: list[list[float]], material, z: float = 0.0):
    """Draw one polygon ring as a planar face."""
    points = ring[:-1] if ring and ring[0] == ring[-1] else ring
    if len(points) < 3:
        return None
    return _mesh(scene, name, [(float(p[0]), float(p[1]), 0.0) for p in points], [tuple(range(len(points)))], material, z)


def _lines(scene, name: str, segments: list[list[tuple[float, float]]], material, width: float, z: float = 0.0):
    """Draw multiple straight or polyline segments as one curve object."""
    if not segments:
        return None
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = width / 2.0
    curve.bevel_resolution = 0
    for points in segments:
        if len(points) < 2:
            continue
        spline = curve.splines.new("POLY")
        spline.points.add(len(points) - 1)
        for control, (x, y) in zip(spline.points, points):
            control.co = (x, y, 0.0, 1.0)
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.location.z = z
    return obj


def _line(scene: bpy.types.Scene, name: str, points: list[tuple[float, float]], material, width: float, cyclic: bool = False, z: float = 0.0):
    """Draw one polyline or cyclic outline."""
    if cyclic and points[-1] != points[0]:
        points = [*points, points[0]]
    return _lines(scene, name, [points], material, width, z)


def _text(scene, name: str, body: str, x: float, y: float, size: float, material, align: str = "LEFT", z: float = 0.0):
    """Create a flat text label in plan coordinates."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.space_line = 1.1
    obj = bpy.data.objects.new(name, curve)
    obj.location = (x, y, z)
    scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def _panel(scene, name: str, lines: list[str], x: float, y: float, size: float, material, spacing: float = 0.32):
    """Lay out short evidence lines in the right-side panel."""
    for index, line in enumerate(lines):
        _text(scene, f"{name}_{index:02d}", line, x, y - index * spacing, size, material)


def _new_scene(name: str):
    """Create an empty scene without touching the user's current Blender file."""
    return bpy.data.scenes.new(name)


def _camera(scene):
    """Attach a shared top-down orthographic camera to one scene."""
    world = bpy.data.worlds.new(f"{scene.name}_World")
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    background.inputs["Strength"].default_value = 1.0
    scene.world = world
    data = bpy.data.cameras.new(f"{scene.name}_Camera")
    camera = bpy.data.objects.new(f"{scene.name}_Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (19.0, 6.3, 70.0)
    camera.rotation_euler = (Vector((19.0, 6.3, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    data.type = "ORTHO"
    data.ortho_scale = 42.0
    scene.camera = camera


def _configure(scene, path: Path):
    """Apply deterministic PNG render settings."""
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.filepath = str(path)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def _draw_frame(scene, mats):
    """Draw the provisional diagnostic frame as a dashed, non-semantic boundary."""
    xmin, ymin, xmax, ymax = FRAME
    segments = []
    for start, end in [((xmin, ymin), (xmax, ymin)), ((xmax, ymin), (xmax, ymax)), ((xmax, ymax), (xmin, ymax)), ((xmin, ymax), (xmin, ymin))]:
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        cursor = 0.0
        while cursor < length:
            stop = min(cursor + 0.28, length)
            segments.append([(start[0] + dx * cursor / length, start[1] + dy * cursor / length), (start[0] + dx * stop / length, start[1] + dy * stop / length)])
            cursor += 0.44
    _lines(scene, "ProvisionalDiagnosticFrame", segments, mats["frame"], 0.04, 0.32)


def _draw_walls_context(scene, data, mats):
    """Render wall solids and low-contrast non-node context products."""
    for index, wall in enumerate(data["walls"]):
        if wall.get("status") != "computed":
            continue
        for triangle_index, triangle in enumerate(wall.get("triangles_xy_m", [])):
            _poly(scene, f"PhysicalWall_{index}_{triangle_index}", triangle, mats["wall_fill"], 0.04)
        for outline_index, ring in enumerate(wall.get("outlines_xy_m", [])):
            _line(scene, f"PhysicalWallEdge_{index}_{outline_index}", [(float(p[0]), float(p[1])) for p in ring], mats["wall_edge"], 0.024, True, 0.08)
    for index, item in enumerate(data["context"]):
        if item.get("class") == "IfcWall" or item.get("status") != "computed":
            continue
        for part_index, ring in enumerate(item.get("geometry_parts", [])):
            _poly(scene, f"Context_{index}_{part_index}", ring, mats["context_fill"], 0.01)
            _line(scene, f"ContextEdge_{index}_{part_index}", [(float(p[0]), float(p[1])) for p in ring], mats["context_edge"], 0.012, True, 0.07)


def _draw_groups(scene, groups: list[dict], labels: dict[str, str], mats):
    """Draw each authored furniture group intact and label its analysis node."""
    for group in groups:
        label = labels[group["group_id"]]
        for member_index, member in enumerate(group.get("members", [])):
            if member.get("status") != "computed":
                continue
            for part_index, ring in enumerate(member.get("geometry_parts", [])):
                _poly(scene, f"Furniture_{label}_{member_index}_{part_index}", ring, mats["furniture"], 0.10)
                _line(scene, f"FurnitureEdge_{label}_{member_index}_{part_index}", [(float(p[0]), float(p[1])) for p in ring], mats["ink"], 0.018, True, 0.13)
        for ring_index, ring in enumerate(group.get("geometry_parts", [])):
            _line(scene, f"GroupNode_{label}_{ring_index}", [(float(p[0]), float(p[1])) for p in ring], mats["ink"], 0.024, True, 0.16)
        x, y = group["centroid_m"]
        _poly(scene, f"LabelCard_{label}", [[x - 0.28, y - 0.16], [x + 0.28, y - 0.16], [x + 0.28, y + 0.16], [x - 0.28, y + 0.16]], mats["white"], 0.18)
        _text(scene, f"NodeLabel_{label}", label, x, y - 0.09, 0.22, mats["ink"], "CENTER", 0.20)


def _heat_materials(prefix: str, alpha: float):
    """Create a compact blue-to-orange material ramp for continuous overlays."""
    return [_material(f"{prefix}_{index:02d}", (0.12 + 0.78 * index / 11.0, 0.35 - 0.20 * index / 11.0, 0.78 - 0.68 * index / 11.0), alpha) for index in range(12)]


def _draw_heatmap(scene, cells: list[dict], grid: dict, mats, key: str, name: str, alpha: float):
    """Draw a sampled gradient whose topology is explicitly display-only."""
    values = [float(cell[key]) for cell in cells]
    low, high = min(values, default=0.0), max(values, default=1.0)
    high = max(high, low + 1e-9)
    dx, dy = grid["cell_size_m"]
    vertices, faces, material_indices = [], [], []
    ramp = _heat_materials(name, alpha)
    for cell in cells:
        x, y = cell["x_m"], cell["y_m"]
        offset = len(vertices)
        vertices.extend([(x - dx / 2, y - dy / 2, 0.0), (x + dx / 2, y - dy / 2, 0.0), (x + dx / 2, y + dy / 2, 0.0), (x - dx / 2, y + dy / 2, 0.0)])
        faces.append((offset, offset + 1, offset + 2, offset + 3))
        material_indices.append(min(11, max(0, int((float(cell[key]) - low) / (high - low) * 11.0))))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    for material in ramp:
        mesh.materials.append(material)
    for polygon, index in zip(mesh.polygons, material_indices):
        polygon.material_index = index
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def _draw_graph_support(scene, groups: list[dict], field: dict, labels: dict[str, str], mats):
    """Draw nearest-neighbour support links and node compactness markers."""
    pair_by_node = {}
    for pair in field["relations"]["pair_support"]:
        for node in (pair["left"], pair["right"]):
            current = pair_by_node.get(node)
            if current is None or pair["normalized_gap"] < current["normalized_gap"]:
                pair_by_node[node] = pair
    edges = []
    seen = set()
    for pair in pair_by_node.values():
        key = tuple(sorted((pair["left"], pair["right"])))
        if key in seen:
            continue
        seen.add(key)
        left = next(group for group in groups if group["group_id"] == key[0])
        right = next(group for group in groups if group["group_id"] == key[1])
        edges.append([(tuple(left["centroid_m"])), tuple(right["centroid_m"])])
    _lines(scene, "NearestNeighbourSupportLinks", edges, mats["support_edge"], 0.035, 0.30)
    by_id = {item["group_id"]: item for item in field["relations"]["node_compactness"]}
    for group in groups:
        item = by_id[group["group_id"]]
        x, y = group["centroid_m"]
        radius = 0.12 + 0.24 * float(item["support_score"])
        _poly(scene, f"SupportMarker_{labels[group['group_id']]}", [[x - radius, y - radius], [x + radius, y - radius], [x + radius, y + radius], [x - radius, y + radius]], mats["support_fill"], 0.28)


def _draw_regions(scene, candidate: dict, mats):
    """Draw a hard 1/2/3/4 region candidate as a transparent envelope overlay."""
    for index, region in enumerate(candidate["regions"]):
        material = mats["region_fill"][index % len(mats["region_fill"])]
        edge = mats["region_edge"][index % len(mats["region_edge"])]
        for part_index, ring in enumerate(region.get("geometry_parts", [])):
            _poly(scene, f"HardRegionFill_{index}_{part_index}", ring, material, 0.025 + index * 0.001)
            _line(scene, f"HardRegionEdge_{index}_{part_index}", [(float(p[0]), float(p[1])) for p in ring], edge, 0.045, True, 0.22)


def _draw_empty(scene, empty: dict, grid: dict, mats):
    """Draw empty-space candidate geometry and relative clearance evidence."""
    for index, ring in enumerate(empty["geometry_parts"]):
        _poly(scene, f"EmptySpaceFill_{index}", ring, mats["empty_fill"], 0.025)
        _line(scene, f"EmptySpaceBoundary_{index}", [(float(p[0]), float(p[1])) for p in ring], mats["empty_edge"], 0.04, True, 0.24)
    _draw_heatmap(scene, empty["samples"], grid, mats, "relative_clearance", "EmptyClearanceField", 0.14)


def _legend(scene, mode: str, data: dict, mats, candidate: dict | None = None):
    """Write required interpretation labels and scope limits into every view."""
    ink, muted, frame = mats["ink"], mats["muted"], mats["frame"]
    _text(scene, "Title", "D6 · CURRENT IFC · LEVEL 1 · PLAN (m)", -0.5, 16.25, 0.46, ink)
    title = "soft-field diagnostic" if mode == "soft" else "empty-space diagnostic evidence" if mode == "empty" else f"hard candidate · {candidate['region_count']} regions"
    _text(scene, "Subtitle", title, -0.5, 15.45, 0.37, ink)
    _text(scene, "FrameTitle", "provisional diagnostic frame · not owner-confirmed", -0.15, 13.60, 0.24, frame)
    _text(scene, "PanelTitle", "READING THIS VIEW", 28.0, 15.35, 0.31, ink)
    if mode == "soft":
        panel = [
            "soft-field diagnostic",
            "continuous support is relative",
            "bandwidth = median positive",
            "nearest-neighbour normalized gap",
            "no fixed metre threshold",
            "gradient is display evidence",
            "nearest-neighbour links shown",
        ]
    elif mode == "empty":
        panel = [
            "empty-space diagnostic evidence",
            "empty_space_field = frame complement",
            "free area and continuity are bounded",
            "clearance is a local width proxy",
            "lowest ranks are bottleneck evidence",
            "not corridor / route / activity area",
            "sampled topology is not truth",
        ]
    else:
        panel = [
            "hard candidate comparison",
            f"{candidate['region_count']} region envelope(s)",
            "same exact furniture_group nodes",
            "MST ranked relative gap cuts",
            "no fixed metre cutoff",
            "discrete view of continuous evidence",
        ]
    _panel(scene, "Panel", panel, 28.0, 14.70, 0.23, frame if mode in {"soft", "empty"} else muted, 0.31)
    y = 11.95
    _text(scene, "ScopeHeading", "SCOPE / STATUS", 28.0, y, 0.27, ink)
    _panel(scene, "Scope", [
        "furniture_group analysis node",
        "37 authored groups · 95 members",
        "members remain indivisible",
        "context/reference only",
        "walls retained as physical geometry",
        "no accepted AnalysisDomain",
        "not owner-confirmed",
        "no route, walkability, visibility",
        "no activity role or accuracy",
    ], 28.0, y - 0.45, 0.205, muted, 0.29)
    _text(scene, "LegendHeading", "MAP LEGEND", 28.0, 8.90, 0.27, ink)
    _line(scene, "LegendFrame", [(28.05, 8.42), (28.75, 8.42)], frame, 0.06)
    _text(scene, "LegendFrameText", "provisional diagnostic frame", 29.05, 8.35, 0.20, ink)
    _line(scene, "LegendNode", [(28.05, 7.85), (28.75, 7.85)], ink, 0.045)
    _text(scene, "LegendNodeText", "furniture_group analysis node", 29.05, 7.78, 0.20, ink)
    _poly(scene, "LegendContext", [[28.05, 7.25], [28.75, 7.25], [28.75, 7.48], [28.05, 7.48]], mats["context_fill"], 0.05)
    _text(scene, "LegendContextText", "context/reference only", 29.05, 7.27, 0.20, ink)
    _poly(scene, "LegendEmpty", [[28.05, 6.68], [28.75, 6.68], [28.75, 6.91], [28.05, 6.91]], mats["empty_fill"], 0.05)
    _text(scene, "LegendEmptyText", "empty_space_field", 29.05, 6.70, 0.20, ink)
    _panel(scene, "Footer", [
        "Gray products are context/reference only.",
        "Dashed frame is not a room edge.",
        "Hard envelopes are display-only group sets.",
        "Empty evidence is diagnostic and bounded.",
    ], -0.5, -0.78, 0.20, muted, 0.29)


def _materials():
    """Create materials shared by each disposable scene."""
    return {
        "ink": _material("Ink", COLORS["ink"]),
        "muted": _material("Muted", COLORS["muted"]),
        "frame": _material("Frame", COLORS["frame"]),
        "white": _material("White", COLORS["white"]),
        "context_fill": _material("ContextFill", COLORS["context"], 0.34),
        "context_edge": _material("ContextEdge", COLORS["context"], 0.54),
        "wall_fill": _material("WallFill", COLORS["wall"], 0.82),
        "wall_edge": _material("WallEdge", COLORS["ink"], 0.84),
        "furniture": _material("Furniture", COLORS["furniture"]),
        "support_fill": _material("SupportFill", COLORS["cyan"], 0.82),
        "support_edge": _material("SupportEdge", COLORS["blue"], 0.56),
        "empty_fill": _material("EmptyFill", COLORS["cyan"], 0.12),
        "empty_edge": _material("EmptyEdge", COLORS["cyan"], 0.85),
        "region_fill": [_material(f"RegionFill_{i}", color, 0.15) for i, color in enumerate(COLORS["region"])],
        "region_edge": [_material(f"RegionEdge_{i}", color, 0.84) for i, color in enumerate(COLORS["region"])],
    }


def _label_map(groups: list[dict]) -> dict[str, str]:
    """Assign stable display labels in the existing source-id order."""
    return {group["group_id"]: f"G{index:02d}" for index, group in enumerate(sorted(groups, key=lambda item: item["source_id"]), 1)}


def main() -> None:
    """Build six top-down evidence scenes and save a disposable blend."""
    data = _read_json(ROOT / "render_input.json")
    field = data["field"]
    empty_payload = data["empty_space"]["empty_space"]
    grid = field["grid"]
    groups = data["groups"]
    labels = _label_map(groups)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    base = bpy.data.scenes[0] if bpy.data.scenes else bpy.data.scenes.new("Hard_1_region")
    base.name = "Hard_1_region"
    scenes = []
    plans = [("hard", candidate, f"hard_{candidate['region_count']}_regions.png") for candidate in data["candidates"]]
    plans.extend([("soft", None, "soft_field_diagnostic.png"), ("empty", None, "empty_space_diagnostic.png")])
    for index, (mode, candidate, filename) in enumerate(plans):
        scene = base if index == 0 else _new_scene(("Hard_%d_regions" % candidate["region_count"]) if mode == "hard" else "SoftField_diagnostic" if mode == "soft" else "EmptySpace_diagnostic")
        _camera(scene)
        mats = _materials()
        if mode == "hard":
            _draw_regions(scene, candidate, mats)
        elif mode == "soft":
            _draw_heatmap(scene, field["support_cells"], grid, mats, "support_score", "ContinuousSupportField", 0.20)
            _draw_graph_support(scene, groups, field, labels, mats)
        else:
            _draw_empty(scene, empty_payload, grid, mats)
        _draw_walls_context(scene, data, mats)
        _draw_groups(scene, groups, labels, mats)
        _draw_frame(scene, mats)
        _legend(scene, mode, data, mats, candidate)
        _configure(scene, ROOT / filename)
        scenes.append(scene)
    for scene in scenes:
        bpy.ops.render.render(write_still=True, scene=scene.name)
    blend_path = ROOT / "d6_soft_field_disposable.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    checks = {
        "schema": "d6-space-field-soft-field-render-checks/v1",
        "blender_version": bpy.app.version_string,
        "renderer": scenes[0].render.engine,
        "resolution": [WIDTH, HEIGHT],
        "camera_view": "top-down orthographic",
        "scene_names": [scene.name for scene in scenes],
        "pngs": [scene.render.filepath for scene in scenes],
        "current_user_scene_opened": False,
        "disposable_blend": str(blend_path),
        "required_labels": ["soft-field diagnostic", "empty-space diagnostic evidence", "provisional diagnostic frame", "not owner-confirmed", "furniture_group analysis node", "context/reference only"],
    }
    (ROOT / "blender_render_checks.json").write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "scene_count": len(scenes), "blend": str(blend_path)}))


if __name__ == "__main__":
    main()
