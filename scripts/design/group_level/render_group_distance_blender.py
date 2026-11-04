"""Display one recorded group route on an existing board in a disposable blend copy."""

from __future__ import annotations

import math
import argparse
from hashlib import sha256
import json
from collections.abc import Mapping
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _vector(value, size):
    """Reject malformed or nonfinite saved coordinates before native handoff."""
    if (not isinstance(value, (list, tuple)) or len(value) != size
            or any(type(item) not in (int, float) or not math.isfinite(item) for item in value)):
        raise ValueError("coordinates must contain finite real numbers")
    return tuple(float(item) for item in value)


def native_route_points(points, plane, origin_offset, native_scale, display_z_m):
    """Undo the view offset, restore world SI through the plane, then convert units."""
    origin = _vector(plane["origin"], 3)
    basis = tuple(_vector(axis, 3) for axis in plane["basis"])
    if len(basis) != 3 or any(abs(axis[2]) > 1e-8 for axis in basis[:2]) or abs(abs(basis[2][2]) - 1) > 1e-8:
        raise ValueError("route display requires a horizontal analysis plane")
    if any(abs(sum(a * b for a, b in zip(basis[i], basis[j])) - (i == j)) > 1e-8
           for i in range(3) for j in range(3)):
        raise ValueError("analysis plane basis must be orthonormal")
    offset = _vector(origin_offset, 2)
    scale, z = _vector([native_scale, display_z_m], 2)
    if scale <= 0:
        raise ValueError("native unit scale must be positive")
    converted = []
    for point in points:
        x, y = _vector(point, 2)
        # Distance-view coordinates include this translation; Blender and SVG do not share Y inversion.
        x, y = x - offset[0], y - offset[1]
        converted.append(tuple((origin[i] + x * basis[0][i] + y * basis[1][i]) / scale
                               for i in range(2)) + (z / scale,))
    return converted


def prepare_route(manifest, observation, document, requested_ref):
    """Bind recorded route cells to the exact authoritative free-space publication."""
    from adapters import blender_analysis_result_wire as wire

    reference = {key: document[key] for key in ("kind", "result_id", "digest")}
    if reference != requested_ref or manifest["query_context"].get("result_ref") != reference:
        raise ValueError("distance run requires the exact requested free-space ResultRef")
    request = document["tables"]["snapshot"]["request"]
    domain = wire.plain(document["identity"]["domain_identity"])
    if any(wire.plain(manifest["domain"].get(key)) != value for key, value in domain.items()):
        raise ValueError("distance domain differs from the free-space result")
    plane = wire.plain(request["plane"])
    if any(wire.plain(manifest["analysis_plane"].get(key)) != value for key, value in plane.items()):
        raise ValueError("distance plane differs from the free-space result")
    source = wire.plain(document["identity"]["project_source_identity"])
    if any(wire.plain(manifest["source_identity"].get(key)) != value for key, value in source.items()):
        raise ValueError("distance source differs from the free-space result")
    lattice = wire.plain(document["tables"]["lattice"])
    if (any(wire.plain(manifest["grid"].get(key)) != value for key, value in lattice.items())
            or wire.plain(manifest["query_context"].get("geometry_query")) != wire.plain(request["geometry_query"])):
        raise ValueError("distance lattice or geometry query differs from the free-space result")
    channel, route = observation["centroid_free_space_hybrid"], observation["route"]
    layer = dict(pair_id=observation["pair_id"], status=channel["status"], main=[], offsets=[])
    if route is None:
        if channel["value"] is not None or channel["status"] in {"computed", "partial"}:
            raise ValueError("computed distance lacks its recorded route")
        return layer
    if channel["status"] not in {"computed", "partial"} or not isinstance(route, Mapping):
        raise ValueError("route does not have a computed or partial status")
    if not route["points"] or len(route["points"]) != len(route["cell_keys"]):
        raise ValueError("route point and cell coverage differ")
    previous = None
    for key, point in zip(route["cell_keys"], route["points"]):
        if (not isinstance(key, (list, tuple)) or len(key) != 2 or any(type(i) is not int for i in key)
                or not 0 <= key[0] < lattice["n_rows"] or not 0 <= key[1] < lattice["n_cols"]):
            raise ValueError("route references an invalid cell")
        row, column = key
        cell = document["cells"][row * lattice["n_cols"] + column]
        center = tuple(lattice["origin"][axis] + (index + .5) * lattice["spacing"]
                       for axis, index in enumerate((column, row)))
        if (cell["value"] is not False or cell["status"] not in {"established", "conditional"}
                or any(abs(a - b) > 1e-8 for a, b in zip(_vector(point, 2), center))):
            raise ValueError("route point differs from its known-empty saved cell")
        if previous is not None and abs(row - previous[0]) + abs(column - previous[1]) != 1:
            raise ValueError("route cells are not four-neighbor adjacent")
        previous = key
    offsets = []
    for side, endpoint in (("source", route["points"][0]), ("target", route["points"][-1])):
        access = route[side + "_access"]
        if _vector(access["cell_center"], 2) != _vector(endpoint, 2):
            raise ValueError("endpoint access does not meet its recorded route")
        offsets.append([list(_vector(route[side + "_centroid"], 2)),
                        list(_vector(access["proxy_point"], 2)), list(_vector(endpoint, 2))])
    layer.update(main=wire.plain(route["points"]), offsets=offsets)
    return layer


def load_run(directory, pair_id=None):
    """Read a complete saved run and select one indexed observation without inference."""
    from adapters import blender_analysis_result_wire as wire

    directory = Path(directory)
    manifest, observations, index = (wire.load_json((directory / name).read_text(encoding="utf-8"))
        for name in ("run_manifest.json", "observations.json", "pair_index.json"))
    ids = [item["pair_id"] for item in observations]
    if len(set(ids)) != len(ids) or ids != manifest["expected_pair_ids"] or len(index) != len(ids):
        raise ValueError("pair index does not cover the manifest observations")
    for position, (item, observation) in enumerate(zip(index, observations)):
        if (item["pair_id"] != observation["pair_id"] or item["group_ids"] != observation["group_ids"]
                or item["observation_index"] != position):
            raise ValueError("pair index differs from its observation")
        if observation["dependencies"] != manifest["dependency_fingerprints"]:
            raise ValueError("observation dependencies differ from the run manifest")
    if pair_id is None:
        # Representative selection uses saved route length only; it does not search or calculate a route.
        observation = max(observations, key=lambda item: len((item["route"] or {}).get("points", ())))
    else:
        observation = next((item for item in observations if item["pair_id"] == pair_id), None)
        if observation is None:
            raise ValueError("requested pair is absent from the saved run")
    return manifest, observation


def _mesh_line(name, points, width, dashed, parent, material, metadata, bpy):
    """Build display ribbons as owned meshes compatible with existing overlay cleanup."""
    vertices, faces = [], []
    for start, end in zip(points, points[1:]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        # Dashes are presentation subdivisions of a recorded segment, never inferred route edges.
        pieces = [(0., 1.)] if not dashed else [(t / length, min(t + width * 4, length) / length)
            for t in (i * width * 7 for i in range(math.ceil(length / (width * 7))))]
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        for a, b in pieces:
            p = tuple(start[i] + a * (end[i] - start[i]) for i in range(3))
            q = tuple(start[i] + b * (end[i] - start[i]) for i in range(3))
            first = len(vertices)
            vertices.extend(((p[0] + nx, p[1] + ny, p[2]), (p[0] - nx, p[1] - ny, p[2]),
                             (q[0] - nx, q[1] - ny, q[2]), (q[0] + nx, q[1] + ny, q[2])))
            faces.append(tuple(first + i for i in range(4)))
    if len(points) == 1:
        x, y, z = points[0]
        vertices = [(x + a * width, y + b * width, z) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        faces = [(0, 1, 2, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    mesh.materials.append(material)
    for block, role in ((obj, "overlay"), (mesh, "board_mesh")):
        block["om_analysis_owner"], block["om_analysis_role"] = "order_analyzer", role
    obj["om_analysis_preview"] = True
    for key, value in metadata.items():
        obj[key] = value
    return obj


def _file_hash(path):
    """Hash actual input and output bytes for the static preview receipt."""
    return sha256(Path(path).read_bytes()).hexdigest()


def plan_ortho_scale(width, height, aspect):
    """Fit both board extents when Blender's orthographic scale controls image width."""
    return max(width, height * aspect) * 1.13


def render(args):
    """Open the supplied board, validate exact dependencies, and save a disposable preview."""
    import bpy
    from mathutils import Vector
    from blender_addon.order_analyzer_ui import board
    from adapters import blender_analysis_result_wire as wire

    allowed = Path("D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")
    if not bpy.app.background or Path(bpy.app.binary_path).resolve() != allowed.resolve():
        raise ValueError("use the configured portable Blender in background mode")
    source_board = args.board_blend.resolve()
    input_paths = [source_board, args.free_space_result.resolve(), Path(__file__).resolve(),
                   *(args.run_dir.resolve() / name for name in ("run_manifest.json", "observations.json", "pair_index.json"))]
    hashes = {str(path): _file_hash(path) for path in input_paths}
    manifest, observation = load_run(args.run_dir, args.pair_id)
    reference = dict(kind="free_space_run", result_id=args.result_id, digest=args.digest)
    bpy.ops.wm.open_mainfile(filepath=str(source_board))
    candidates = [(obj, board.board_record(obj)) for obj in board.scene_boards(bpy_module=bpy)]
    matches = [(obj, record, entry) for obj, record in candidates for entry in record["results"] if entry["ref"] == reference]
    if len(matches) != 1:
        raise ValueError("the saved board must register exactly one matching ResultRef")
    attached, record, entry = matches[0]
    # Expectations come from the saved board receipt, independently of the newly read external JSON.
    result = board._open_entry({**entry, "path": str(args.free_space_result.resolve())}, record["binding"])
    layer = prepare_route(manifest, observation, result.document, reference)
    board._present(attached, record, result, bpy)
    record.update(active_result_id=reference["result_id"], status="historical",
                  message="Static historical distance preview; route has no live currentness claim.")
    board._save(attached, record)
    display = board._display(attached, bpy)
    scale = board.overlay.native_unit_scale(bpy)
    plane = manifest["analysis_plane"]
    z = plane["origin"][2] + board.SOURCE_LIFT_M + .008
    metadata = {"om_route_pair_id": layer["pair_id"], "om_route_result_ref": wire.canonical_json(reference),
                "om_route_status": "static_historical", "om_route_run_dir": str(args.run_dir.resolve())}
    native = []
    for name, paths, color, width, dashed in (
            ("Recorded free-cell route", [layer["main"]] if layer["main"] else [], (1., .05, .04, 1.), .075, False),
            ("Endpoint offset", layer["offsets"], (.62, .04, .9, 1.), .045, True)):
        material = board._material(record["board_id"], name, color, bpy) if paths else None
        if material:
            shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
            shader.inputs["Emission Color"].default_value = material.diffuse_color
            shader.inputs["Emission Strength"].default_value = .7
        for index, path in enumerate(paths):
            points = native_route_points(path, plane, manifest["origin_offset"], scale, z)
            native.append(_mesh_line(name + str(index), points, width / scale, dashed, display, material, metadata, bpy))
    bpy.context.view_layer.update()
    bounds = [display.matrix_world @ Vector(corner) for corner in display.bound_box]
    xmin, xmax = min(p.x for p in bounds), max(p.x for p in bounds)
    ymin, ymax = min(p.y for p in bounds), max(p.y for p in bounds)
    span = max(xmax - xmin, ymax - ymin)
    camera_data = bpy.data.cameras.new("Static route plan camera")
    camera = bpy.data.objects.new("Static route plan camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = ((xmin + xmax) / 2, (ymin + ymax) / 2, max(p.z for p in bounds) + span * 2)
    camera.rotation_euler = (0., 0., 0.)
    camera_data.type, camera_data.sensor_fit = "ORTHO", "HORIZONTAL"
    camera_data.ortho_scale = plan_ortho_scale(xmax - xmin, ymax - ymin, 1280 / 1050)
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.device = "CPU"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1280, 1050, 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    # Render stamps identify the historical result and route meaning without adding scene geometry.
    for prop in scene.render.bl_rna.properties:
        if prop.identifier.startswith("use_stamp_"):
            setattr(scene.render, prop.identifier, False)
    scene.render.use_stamp = scene.render.use_stamp_note = True
    scene.render.stamp_font_size = 15
    scene.render.stamp_foreground = (.02, .02, .02, 1.)
    scene.render.stamp_background = (.95, .95, .95, .95)
    scene.render.stamp_note_text = (f"STATIC HISTORICAL | pair {layer['pair_id']} | {layer['status']} | metres\n"
        f"Red: recorded free-cell route. Purple dashed: endpoint offsets. Board context only.\n"
        f"Free-space {reference['result_id']} | SHA256 {reference['digest']}")
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Static preview world")
    scene.world.use_nodes = True
    background = next(node for node in scene.world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (.8, .8, .8, 1)
    background.inputs["Strength"].default_value = .8
    scene.view_settings.view_transform = "Standard"
    args.output_dir.mkdir(parents=True, exist_ok=False)
    blend, png = args.output_dir / "route-board.blend", args.output_dir / "route-board.png"
    scene.render.filepath = str(png.resolve())
    scene["om_static_distance_preview"] = wire.canonical_json(metadata)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()), copy=True)
    bpy.ops.render.render(write_still=True)
    if any(_file_hash(path) != digest for path, digest in hashes.items()):
        raise ValueError("an input changed during native rendering")
    report = dict(status="static_historical", result_ref=reference, pair_id=layer["pair_id"],
                  hybrid=observation["centroid_free_space_hybrid"], main_point_count=len(layer["main"]),
                  offset_point_counts=[len(path) for path in layer["offsets"]], route_object_count=len(native),
                  input_sha256=hashes, output_sha256={str(path.resolve()): _file_hash(path) for path in (blend, png)},
                  analysis_plane=plane, origin_offset=manifest["origin_offset"], native_scale=scale,
                  display_only_lift_above_board_m=.008, blender_version=bpy.app.version_string,
                  source_context="Existing board scene only; no full IFC source geometry imported.",
                  legend={"red": "recorded free-cell path", "purple_dashed": "centroid/proxy/access offsets; not free-space path"},
                  limitation="Static historical preview; selecting another result does not make this route current.")
    (args.output_dir / "preview_report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    return report


def main():
    """Require explicit board, exact free-space ref, saved run and fresh output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run-dir", "board-blend", "free-space-result", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--result-id", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--pair-id")
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    render(parser.parse_args(args))


if __name__ == "__main__":
    main()
