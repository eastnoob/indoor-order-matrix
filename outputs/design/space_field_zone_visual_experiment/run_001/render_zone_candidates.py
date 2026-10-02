"""Build and render disposable Blender scenes for D6 zone candidates."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "render_input.json"
WALL_PATH = ROOT / "physical_wall_plan_projection.json"
RENDER_WIDTH = 2400
RENDER_HEIGHT = 1200
FRAME = {"xmin": 0.0, "xmax": 25.6, "ymin": -0.01, "ymax": 12.6}
COLORS = {
    "ink": (0.12, 0.16, 0.19),
    "muted": (0.35, 0.40, 0.43),
    "context": (0.71, 0.74, 0.76),
    "furniture": (0.84, 0.82, 0.76),
    "wall": (0.42, 0.46, 0.48),
    "frame": (0.71, 0.28, 0.11),
    "white": (1.0, 1.0, 1.0),
    "region": [
        (0.30, 0.47, 0.66),
        (0.91, 0.49, 0.19),
        (0.33, 0.63, 0.39),
        (0.82, 0.31, 0.29),
        (0.36, 0.66, 0.65),
        (0.65, 0.45, 0.64),
    ],
}


def _read_json(path: Path) -> dict:
    """Load one UTF-8 experiment input file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _material(name: str, color: tuple[float, float, float], alpha: float = 1.0):
    """Create an unlit Blender material with explicit alpha for plan overlays."""
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
        # Blender versions that lack the property still render the emission layer.
        pass
    return material


def _link_mesh(scene, name: str, vertices: list[tuple[float, float, float]], faces: list[tuple[int, ...]], material, z: float):
    """Link one flat mesh object into the candidate scene."""
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([(x, y, z) for x, y, _ in vertices], [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def _fill_polygon(scene, name: str, ring: list[list[float]], material, z: float):
    """Create a planar polygon fill from one closed XY ring."""
    points = ring[:-1] if ring and ring[0] == ring[-1] else ring
    if len(points) < 3:
        return None
    vertices = [(float(point[0]), float(point[1]), 0.0) for point in points]
    return _link_mesh(scene, name, vertices, [tuple(range(len(vertices)))], material, z)


def _line_segments(scene, name: str, segments: list[list[tuple[float, float]]], material, width: float, z: float = 0.0):
    """Batch short flat line segments into one curve object per render layer."""
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


def _line(scene, name: str, points: list[tuple[float, float]], material, width: float, cyclic: bool = False, z: float = 0.0):
    """Create a flat polyline using a beveled curve for crisp boundaries."""
    if len(points) < 2:
        return None
    closed = [*points, points[0]] if cyclic and points[-1] != points[0] else points
    return _line_segments(scene, name, [closed], material, width, z)


def _dash_ring(scene, name: str, ring: list[list[float]], material, width: float, dash: float = 0.16, gap: float = 0.10, z: float = 0.0):
    """Draw a polygon boundary as separate dashes without changing its geometry."""
    points = ring[:-1] if ring and ring[0] == ring[-1] else ring
    segments = []
    for edge_index, start in enumerate(points):
        end = points[(edge_index + 1) % len(points)]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            continue
        cursor = 0.0
        while cursor < length:
            stop = min(cursor + dash, length)
            segments.append([
                (start[0] + dx * cursor / length, start[1] + dy * cursor / length),
                (start[0] + dx * stop / length, start[1] + dy * stop / length),
            ])
            cursor += dash + gap
    _line_segments(scene, name, segments, material, width, z)


def _text(scene, name: str, body: str, x: float, y: float, size: float, material, *, align: str = "LEFT", z: float = 0.0):
    """Create readable flat text in the common orthographic plan plane."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.space_line = 1.15
    obj = bpy.data.objects.new(name, curve)
    obj.location = (x, y, z)
    scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def _panel_text(scene, name: str, lines: list[str], x: float, y: float, size: float, material, line_height: float | None = None):
    """Lay out explicitly wrapped lines in the fixed right-side evidence panel."""
    spacing = size * 1.48 if line_height is None else line_height
    for index, line in enumerate(lines):
        _text(scene, f"{name}_{index:02d}", line, x, y - index * spacing, size, material)
    return y - len(lines) * spacing


def _new_scene(name: str):
    """Create an empty scene without opening or modifying the user's scene."""
    return bpy.data.scenes.new(name)


def _world_and_camera(scene):
    """Set a consistent white orthographic camera for all candidate renders."""
    world = bpy.data.worlds.new(f"{scene.name}_World")
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    background.inputs["Strength"].default_value = 1.0
    scene.world = world
    data = bpy.data.cameras.new(f"{scene.name}_Camera")
    camera = bpy.data.objects.new(f"{scene.name}_Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (18.0, 7.5, 70.0)
    target = Vector((18.0, 7.5, 0.0))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    data.type = "ORTHO"
    data.ortho_scale = 40.0
    scene.camera = camera
    return camera


def _configure_render(scene, path: Path):
    """Apply identical deterministic PNG render settings for every scene."""
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = RENDER_WIDTH
    scene.render.resolution_y = RENDER_HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(path)
    scene.render.use_file_extension = True
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def _draw_wall(scene, wall: dict, fill_material, edge_material):
    """Render physical IFC wall plan triangles and their exact projected outline."""
    if wall["status"] != "computed":
        return
    vertices = []
    faces = []
    for triangle in wall["triangles_xy_m"]:
        offset = len(vertices)
        vertices.extend((float(p[0]), float(p[1]), 0.0) for p in triangle)
        faces.append((offset, offset + 1, offset + 2))
    _link_mesh(scene, f"PhysicalWall_{wall['source_id']}", vertices, faces, fill_material, 0.035)
    for index, outline in enumerate(wall["outlines_xy_m"]):
        _line(
            scene,
            f"PhysicalWallOutline_{wall['source_id']}_{index:02d}",
            [(float(point[0]), float(point[1])) for point in outline],
            edge_material,
            0.025,
            cyclic=True,
            z=0.078,
        )


def _draw_context(scene, records: list[dict], materials: dict):
    """Show non-analysis products as low-contrast context/reference geometry."""
    for index, item in enumerate(records):
        if item["class"] == "IfcWall" or item["status"] != "computed":
            continue
        for part_index, ring in enumerate(item["geometry_parts"]):
            slab_z = -0.02 if item["class"] == "IfcSlab" else 0.012
            _fill_polygon(scene, f"Context_{index}_{part_index}", ring, materials["context_fill"], slab_z)
            _line(
                scene,
                f"ContextEdge_{index}_{part_index}",
                [(float(p[0]), float(p[1])) for p in ring],
                materials["context_edge"],
                0.012,
                cyclic=True,
                z=0.071,
            )


def _draw_group(scene, group: dict, display_label: str, materials: dict):
    """Draw all member footprints together under one authored group identifier."""
    for member_index, member in enumerate(group["members"]):
        if member["status"] != "computed":
            continue
        for part_index, ring in enumerate(member["geometry_parts"]):
            _fill_polygon(
                scene,
                f"FurnitureMember_{display_label}_{member_index}_{part_index}",
                ring,
                materials["furniture_fill"],
                0.060,
            )
            _line(
                scene,
                f"FurnitureMemberEdge_{display_label}_{member_index}_{part_index}",
                [(float(p[0]), float(p[1])) for p in ring],
                materials["ink"],
                0.018,
                cyclic=True,
                z=0.083,
            )
    for part_index, ring in enumerate(group["geometry_parts"]):
        _dash_ring(scene, f"GroupNode_{display_label}_{part_index}", ring, materials["ink"], 0.026, z=0.108)
    if group.get("centroid_m"):
        x, y = map(float, group["centroid_m"])
        label_width = 0.54
        label_height = 0.34
        _fill_polygon(
            scene,
            f"NodeLabelCard_{display_label}",
            [[x - label_width / 2, y - label_height / 2], [x + label_width / 2, y - label_height / 2], [x + label_width / 2, y + label_height / 2], [x - label_width / 2, y + label_height / 2], [x - label_width / 2, y - label_height / 2]],
            materials["white"],
            0.12,
        )
        _text(scene, f"NodeLabel_{display_label}", display_label, x, y - 0.095, 0.22, materials["ink"], align="CENTER", z=0.13)


def _draw_region(scene, region: dict, region_index: int, materials: dict):
    """Draw one soft candidate envelope and its colored boundary."""
    material = materials["region_fills"][region_index % len(materials["region_fills"])]
    edge = materials["region_edges"][region_index % len(materials["region_edges"])]
    for part_index, ring in enumerate(region["geometry_parts"]):
        _fill_polygon(scene, f"RegionFill_{region_index + 1}_{part_index}", ring, material, 0.026 + region_index * 0.0001)
        _line(
            scene,
            f"RegionEdge_{region_index + 1}_{part_index}",
            [(float(p[0]), float(p[1])) for p in ring],
            edge,
            0.045,
            cyclic=True,
            z=0.09,
        )


def _draw_frame(scene, materials: dict):
    """Show source extent as a dashed diagnostic view frame, never as a domain."""
    ring = [
        [FRAME["xmin"], FRAME["ymin"]],
        [FRAME["xmax"], FRAME["ymin"]],
        [FRAME["xmax"], FRAME["ymax"]],
        [FRAME["xmin"], FRAME["ymax"]],
        [FRAME["xmin"], FRAME["ymin"]],
    ]
    _dash_ring(scene, "DiagnosticSourceExtentFrame", ring, materials["frame"], 0.040, dash=0.22, gap=0.14, z=0.14)


def _legend(scene, candidate: dict, materials: dict, summary: dict, relation_counts: dict, display_labels: dict):
    """Render the required status legend, boundary provenance, and data limits."""
    ink = materials["ink"]
    muted = materials["muted"]
    _text(scene, "FigureTitle", "D6 · CURRENT IFC · LEVEL 1 · PLAN (m)", -1.0, 16.15, 0.48, ink)
    display_label = candidate["label"]
    if candidate["region_count"] == 1:
        display_label = "baseline — all 37 analysis nodes together; no internal split"
    _text(scene, "CandidateTitle", display_label, -1.0, 15.35, 0.39, ink)
    _text(scene, "FrameHeading", "SOURCE GEOMETRY EXTENT · view frame only", -0.25, 13.25, 0.23, materials["frame"])
    _text(scene, "PanelHeading", "READING THIS CANDIDATE", 28.1, 15.2, 0.31, ink)

    y = 14.55
    y = _panel_text(scene, "provisional", [
        "provisional diagnostic candidate —",
        "not owner-confirmed",
    ], 28.1, y, 0.245, materials["frame"], 0.34)
    y -= 0.15
    y = _panel_text(scene, "boundary", [
        "Boundary candidate used:",
        "source-geometry extent fallback",
        "Status: diagnostic_only; no accepted",
        "AnalysisDomain and no IfcSpace.",
        "This dashed frame is not a room edge.",
    ], 28.1, y, 0.225, ink, 0.32)
    y -= 0.22
    _text(scene, "LegendHeader", "MAP LEGEND", 28.1, y, 0.27, ink)
    y -= 0.50
    _line(scene, "LegendRegionSample", [(28.15, y + 0.08), (28.85, y + 0.08)], materials["region_edges"][0], 0.11)
    _panel_text(scene, "legend_region", ["colored soft fill · candidate region envelope"], 29.1, y, 0.215, ink)
    y -= 0.46
    _dash_ring(scene, "LegendGroupSample", [[28.15, y - 0.07], [28.85, y - 0.07], [28.85, y + 0.19], [28.15, y + 0.19], [28.15, y - 0.07]], ink, 0.035, 0.14, 0.08)
    _text(scene, "LegendGroupText", "furniture_group analysis node", 29.1, y, 0.215, ink)
    y -= 0.47
    _fill_polygon(scene, "LegendContextSample", [[28.15, y - 0.04], [28.85, y - 0.04], [28.85, y + 0.18], [28.15, y + 0.18], [28.15, y - 0.04]], materials["context_fill"], 0.04)
    _text(scene, "LegendContextText", "context/reference only", 29.1, y, 0.215, ink)
    y -= 0.46
    _fill_polygon(scene, "LegendWallSample", [[28.15, y - 0.04], [28.85, y - 0.04], [28.85, y + 0.18], [28.15, y + 0.18], [28.15, y - 0.04]], materials["wall_fill"], 0.04)
    _text(scene, "LegendWallText", "physical wall geometry", 29.1, y, 0.215, ink)
    y -= 0.57

    _text(scene, "PartitionHeader", "PARTITION DIAGNOSTIC", 28.1, y, 0.27, ink)
    y -= 0.44
    _panel_text(scene, "method", [
        f"{candidate['region_count']} connected components from the",
        "same group-gap MST comparison.",
        "Cuts remove the largest positive",
        "normalized XY boundary-gap edges;",
        "no fixed metre cutoff is used.",
    ], 28.1, y, 0.215, muted, 0.30)
    y -= 1.78
    for cut_index, edge in enumerate(candidate["cut_edges"], start=1):
        left = display_labels.get(edge["left"], edge["left"][-6:])
        right = display_labels.get(edge["right"], edge["right"][-6:])
        _panel_text(scene, f"cut_{cut_index}", [
            f"Cut {cut_index}: {left} ↔ {right}",
            f"XY gap {edge['boundary_gap_m']:.3f} m · relative {edge['normalized_gap']:.3f}",
        ], 28.1, y, 0.205, ink, 0.28)
        y -= 0.65
    y -= 0.12
    group_count = summary["group_selection"]["exact_furniture_group_total"]
    member_count = summary["group_selection"]["unique_grouped_member_total"]
    _panel_text(scene, "data_summary", [
        f"{group_count} authored group nodes · {member_count} members",
        f"{relation_counts['computed_pairs']} / {relation_counts['all_pairs']} pair gaps computed",
        f"height-compatible pairs: {relation_counts['height_compatible']};",
        f"incompatible: {relation_counts['height_incompatible']}",
        "obstacle-crossing relation: not evaluated",
        "group names: available in JSON; diagnostic only",
        "group orientation: not extracted",
        "names/type labels did not drive the cuts",
    ], 28.1, y, 0.195, muted, 0.275)

    footer_lines = [
        "Gray products are context/reference only; door geometry does not encode an opening relation or open/closed state.",
        "No room, free-space, connectivity, route, walkability, accessibility, activity, or production-space role is inferred.",
        "Zone envelopes are display-only convex hulls of group footprints; separate envelopes may overlap.",
        "A colored region is a group-set envelope, not occupied floor area or a closed spatial partition.",
    ]
    _panel_text(scene, "footer", footer_lines, -1.0, -0.80, 0.205, muted, 0.30)


def _candidate_record(candidate: dict, data: dict, relation_counts: dict, display_labels: dict) -> dict:
    """Create a candidate-specific machine-readable evidence and provenance record."""
    summary = data["source_summary"]
    source = summary["source_ifc"]
    groups_by_id = {group["group_id"]: group for group in data["groups"]}
    context_counts = {}
    for record in data["context"]:
        key = f"{record['class']}:{record['status']}"
        context_counts[key] = context_counts.get(key, 0) + 1
    region_records = []
    for region in candidate["regions"]:
        region_records.append({
            "region_id": region["region_id"],
            "group_ids": region["group_ids"],
            "display_labels": [display_labels[item] for item in region["group_ids"]],
            "group_names_diagnostic_only": [groups_by_id[item].get("name") for item in region["group_ids"]],
            "group_count": len(region["group_ids"]),
            "display_geometry_method": region["display_geometry_method"],
            "display_area_m2": region["area_m2"],
        })
    return {
        "schema": "d6-space-field-zone-candidate-record/v1",
        "candidate_id": candidate["candidate_id"],
        "label": candidate["label"],
        "region_count": candidate["region_count"],
        "status": "provisional_diagnostic_not_owner_confirmed",
        "inputs": {
            "ifc_path": source["path"],
            "ifc_sha256": source["sha256"],
            "ifc_schema": source["ifc_schema"],
            "length_unit": source["units"],
            "floor": summary["current_blender_identity"]["floor_candidates"],
            "current_blender_source_match": summary["current_blender_identity"]["source_path_match"],
            "current_scene_identity": summary["current_blender_identity"],
            "analysis_nodes": {
                "selection_rule": 'exact group_role == "furniture_group"',
                "group_count": len(data["groups"]),
                "member_count": sum(group["member_count"] for group in data["groups"]),
                "all_group_geometry_computed": all(group["status"] == "computed" for group in data["groups"]),
                "group_members_split": False,
                "display_label_map": display_labels,
                "group_names_available_but_not_used": True,
                "orientation": "not_extracted",
            },
            "context_geometry_counts": context_counts,
            "context_extraction_scope": summary.get("context_extraction_scope"),
            "pairwise_relation_evidence": {
                **relation_counts,
                "channels": {
                    "planar_boundary_gap": "computed and used as MST edge weight after area normalization",
                    "overlap_or_touch": "computed for diagnosis; not an independent cut criterion",
                    "centroid_distance": "computed for diagnosis; not a cut criterion",
                    "height_compatibility": "computed for diagnosis; not used as a cut gate",
                    "obstacle_crossing": "not_evaluated",
                },
            },
        },
        "boundary": {
            "candidate_used": "source-geometry extent fallback",
            "status": "diagnostic_only",
            "owner_confirmed": False,
            "analysis_domain": "not_available",
            "ifc_space_count": source["counts"]["IfcSpace"],
            "view_frame_m": FRAME,
            "purpose": "consistent non-semantic view frame; not a physical room boundary and not used to clip or assign group membership",
            "other_boundary_proposals": [
                {"candidate": "inner wall face", "current_ifc_status": "not_verified", "basis": "synthetic boundary construction fixture only"},
                {"candidate": "outer wall face", "current_ifc_status": "not_verified", "basis": "synthetic boundary construction fixture only"},
                {"candidate": "wall centerline", "current_ifc_status": "not_verified", "basis": "synthetic boundary construction fixture only"},
                {"candidate": "authored closed curve", "current_ifc_status": "not_available", "basis": "no current IFC authored domain/curve confirmed"},
            ],
            "boundary_sensitivity": "The furniture graph memberships do not change with the displayed boundary frame because no boundary geometry participates in clustering; a selected boundary could change clipping, visible context, or how the clusters relate to an enclosure, so these figures do not compare boundary interpretations.",
        },
        "partition": {
            "basis": candidate["basis"],
            "method": "diagnostic minimum spanning tree over normalized 2D furniture-group footprint boundary gaps",
            "fixed_metre_threshold": False,
            "requested_cut_edge_count": len(candidate["cut_edges"]),
            "cut_edges": candidate["cut_edges"],
            "regions": region_records,
            "display_geometry_method": "convex hull of member footprint union; visual envelope only",
        },
        "provenance": {
            "source_path": source["path"],
            "source_sha256": source["sha256"],
            "current_blender_source_path": summary["current_blender_identity"]["bonsai_ifc_store_path"],
            "source_identity_match": summary["current_blender_identity"]["source_path_match"],
            "algorithm_schema": data["schema"],
            "generation": "candidate-specific extraction evidence plus Blender 5.2.0 LTS orthographic render",
            "production_selection": False,
        },
        "not_inferred": [
            "room or activity-region identity",
            "physical AnalysisDomain selection",
            "free-space or connectivity",
            "route, walkability, accessibility, or visibility",
            "door opening relation or open/closed state",
            "activity function or production space role",
            "probability or accuracy",
        ],
    }


def _pixel_camera_bounds(scene, objects: list):
    """Measure rendered label bounds in normalized camera coordinates."""
    from bpy_extras.object_utils import world_to_camera_view

    bounds = []
    for obj in objects:
        if obj.type != "FONT":
            continue
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        projected = [world_to_camera_view(scene, scene.camera, corner) for corner in corners]
        bounds.append({
            "object": obj.name,
            "xmin": min(point.x for point in projected),
            "xmax": max(point.x for point in projected),
            "ymin": min(point.y for point in projected),
            "ymax": max(point.y for point in projected),
            "inside_frame_with_1pct_margin": all(
                0.01 <= point.x <= 0.99 and 0.01 <= point.y <= 0.99 for point in projected
            ),
        })
    return bounds


def main() -> None:
    """Render all candidate scenes and preserve them in one disposable blend."""
    data = _read_json(INPUT_PATH)
    walls_data = _read_json(WALL_PATH)
    wall_by_id = {wall["source_id"]: wall for wall in walls_data["walls"]}
    summary = data["source_summary"]
    if walls_data["source_sha256"] != summary["source_ifc"]["sha256"]:
        raise RuntimeError("Wall projection source hash does not match the candidate input.")
    if len(wall_by_id) != summary["source_ifc"]["counts"]["IfcWall"]:
        raise RuntimeError("Physical wall projection count does not match IFC inventory.")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    groups = data["groups"]
    groups_by_id = {group["group_id"]: group for group in groups}
    display_labels = {
        group["group_id"]: f"G{index:02d}"
        for index, group in enumerate(sorted(groups, key=lambda item: item["source_id"]), start=1)
    }
    relations = _read_json(ROOT / "group_relation_evidence.json")["relations"]
    relation_counts = {
        "all_pairs": len(relations),
        "computed_pairs": sum(item["status"] == "computed" for item in relations),
        "overlap_or_touch": sum(bool(item.get("overlap_or_touch")) for item in relations if item["status"] == "computed"),
        "height_compatible": sum(item.get("z_compatible") is True for item in relations if item["status"] == "computed"),
        "height_incompatible": sum(item.get("z_compatible") is False for item in relations if item["status"] == "computed"),
        "height_not_available": sum(item.get("z_compatible") is None for item in relations if item["status"] == "computed"),
    }
    if not bpy.data.scenes:
        base_scene = bpy.data.scenes.new("Scene")
    else:
        base_scene = bpy.data.scenes[0]
    base_scene.name = "Baseline_1_region"
    scenes = []
    png_checks = []
    for candidate_index, candidate in enumerate(data["candidates"]):
        scene = base_scene if candidate_index == 0 else _new_scene(f"Candidate_{candidate['region_count']}_regions")
        scene.name = "Baseline_1_region" if candidate_index == 0 else f"Candidate_{candidate['region_count']}_regions"
        camera = _world_and_camera(scene)
        region_fills = [
            _material(f"RegionFill_{i + 1}", color, 0.20)
            for i, color in enumerate(COLORS["region"])
        ]
        region_edges = [
            _material(f"RegionEdge_{i + 1}", color, 0.94)
            for i, color in enumerate(COLORS["region"])
        ]
        materials = {
            "ink": _material("Ink", COLORS["ink"]),
            "muted": _material("Muted", COLORS["muted"]),
            "white": _material("White", COLORS["white"]),
            "frame": _material("Frame", COLORS["frame"]),
            "wall_fill": _material("WallSolid", COLORS["wall"], 0.94),
            "wall_edge": _material("WallEdge", COLORS["ink"]),
            "context_fill": _material("ContextFill", COLORS["context"], 0.52),
            "context_edge": _material("ContextEdge", COLORS["context"], 0.66),
            "furniture_fill": _material("FurnitureMember", COLORS["furniture"]),
            "region_fills": region_fills,
            "region_edges": region_edges,
        }

        for region_index, region in enumerate(candidate["regions"]):
            _draw_region(scene, region, region_index, materials)
        _draw_context(scene, data["context"], materials)
        for wall in wall_by_id.values():
            _draw_wall(scene, wall, materials["wall_fill"], materials["wall_edge"])
        for group in groups:
            _draw_group(scene, group, display_labels[group["group_id"]], materials)
        _draw_frame(scene, materials)
        _legend(scene, candidate, materials, summary, relation_counts, display_labels)
        _configure_render(scene, ROOT / f"{candidate['candidate_id'].replace(':', '_')}.png")
        bounds = _pixel_camera_bounds(scene, list(scene.objects))
        scenes.append(scene)
        png_checks.append({
            "candidate_id": candidate["candidate_id"],
            "scene_name": scene.name,
            "png": scene.render.filepath,
            "label_count": len(bounds),
            "labels_inside_frame_with_1pct_margin": all(item["inside_frame_with_1pct_margin"] for item in bounds),
            "labels": bounds,
        })

        record = _candidate_record(candidate, data, relation_counts, display_labels)
        record_path = ROOT / "candidate_records" / f"{candidate['candidate_id'].replace(':', '_')}.json"
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    if not all(check["labels_inside_frame_with_1pct_margin"] for check in png_checks):
        outside = [item["object"] for check in png_checks for item in check["labels"] if not item["inside_frame_with_1pct_margin"]]
        raise RuntimeError(f"Text outside safe render frame: {outside}")
    for scene in scenes:
        bpy.ops.render.render(write_still=True, scene=scene.name)
    blend_path = ROOT / "d6_zone_candidates_disposable.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    (ROOT / "blender_render_checks.json").write_text(
        json.dumps({
            "schema": "d6-space-field-blender-render-checks/v1",
            "blender_version": bpy.app.version_string,
            "renderer": scenes[0].render.engine,
            "resolution": [RENDER_WIDTH, RENDER_HEIGHT],
            "camera_view": "top-down orthographic, shared extents for all candidate scenes",
            "labels_checked_before_render": True,
            "scenes": png_checks,
            "blend_path": str(blend_path),
            "source_wall_mesh_projection": walls_data["projection_status"],
        }, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "pass",
        "blender_version": bpy.app.version_string,
        "scene_count": len(scenes),
        "png_count": len(png_checks),
        "blend": str(blend_path),
        "relation_counts": relation_counts,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
