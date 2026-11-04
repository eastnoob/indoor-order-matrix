"""Display one recorded group route on an existing board in a disposable blend copy."""

from __future__ import annotations

import math
import argparse
from hashlib import file_digest
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
    model = manifest.get("algorithm_version"), manifest.get("schema_version")
    if model not in {("group-distance/1", "group-distance/v1"), ("group-distance/2", "group-distance/v2"),
                     ("group-distance/3", "group-distance/v3")}:
        raise ValueError("unsupported distance algorithm/schema identity")
    eight_neighbor = model[0] == "group-distance/2"
    support_version = "eight-neighbor-two-flank-occurrences/1"
    if model[0] == "group-distance/3":
        support_version = "eight-neighbor-two-flank-occurrences-directional-clearance/1"
    if model[0] in {"group-distance/2", "group-distance/3"} and manifest.get("edge_support_version") != support_version:
        raise ValueError("unsupported eight-neighbor edge support identity")
    eight_neighbor = model[0] in {"group-distance/2", "group-distance/3"}
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
    path_keys = []
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
        if previous is not None:
            dr, dc = abs(row - previous[0]), abs(column - previous[1])
            if (max(dr, dc) != 1 if eight_neighbor else dr + dc != 1):
                raise ValueError("route cells do not follow the declared neighbor model")
        previous = key
        path_keys.append(tuple(key))
    if eight_neighbor:
        # A displayed diagonal is valid only with the producer's two independently saved empty flanks.
        def query_ref(key):
            """Address the exact publication cell, rather than another route's local reference."""
            return f"free-space:{reference['result_id']}:{reference['digest']}:cell:{key[0]}:{key[1]}"

        edges = route["edges"]
        if len(edges) != len(path_keys) - 1:
            raise ValueError("route edge coverage differs from its path cells")
        state_keys = route.get("state_keys", path_keys)
        guard_keys = set()
        for edge_index, (edge, first, second) in enumerate(zip(edges, path_keys, path_keys[1:])):
            endpoints = sorted((first, second))
            guards = sorted(((first[0], second[1]), (second[0], first[1]))) if (
                first[0] != second[0] and first[1] != second[1]) else []
            expected_from = first
            edge_from = tuple(edge["from"])
            edge_to = tuple(edge["to"])
            if model[0] == "group-distance/3":
                expected_from = tuple(state_keys[edge_index])
                expected_to = tuple(state_keys[edge_index + 1])
            else:
                expected_from, expected_to = first, second
            if (edge_from != expected_from or edge_to != expected_to
                    or [tuple(key) for key in edge["edge_key"]] != endpoints
                    or edge["occupancy_query_refs"] != [query_ref(key) for key in endpoints]
                    or [tuple(key) for key in edge["guard_cell_keys"]] != guards
                    or edge["guard_query_refs"] != [query_ref(key) for key in guards]
                    or edge["edge_support_version"] != support_version):
                raise ValueError("eight-neighbor edge support differs from its exact cell references")
            for key in guards:
                cell = document["cells"][key[0] * lattice["n_cols"] + key[1]]
                if cell["value"] is not False or cell["status"] not in {"established", "conditional"}:
                    raise ValueError("diagonal flank is not an authoritative known-empty cell")
            guard_keys.update(guards)
        guards, support = sorted(guard_keys), sorted(set(path_keys) | guard_keys)
        if ([tuple(key) for key in route["guard_cell_keys"]] != guards
                or route["guard_query_refs"] != [query_ref(key) for key in guards]
                or [tuple(key) for key in route["support_cell_keys"]] != support
                or route["support_query_refs"] != [query_ref(key) for key in support]):
            raise ValueError("route support coverage differs from its selected edges")
    offsets = []
    for side, endpoint in (("source", route["points"][0]), ("target", route["points"][-1])):
        access = route[side + "_access"]
        if _vector(access["cell_center"], 2) != _vector(endpoint, 2):
            raise ValueError("endpoint access does not meet its recorded route")
        if eight_neighbor and access["query_ref"] != query_ref(path_keys[0 if side == "source" else -1]):
            raise ValueError("endpoint access references another free-space publication cell")
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


def prepare_groups(geometry, manifest, observation):
    """Authenticate every endpoint projection component before highlighting whole groups."""
    from features.field_core import fingerprint_evidence_dependency as fingerprint

    if any(geometry[key] != manifest[key] for key in ("analysis_plane", "origin_offset", "domain")):
        raise ValueError("group display geometry differs from the recorded distance view")
    groups = geometry["groups"]
    ids = [group["group_id"] for group in groups]
    if len(set(ids)) != len(ids) or sorted(ids) != sorted(manifest["group_ids"]):
        raise ValueError("group display geometry does not cover the recorded group scope")
    # Match the producer's whole-group fingerprint, including every component and member reference.
    records = [{**group, "components": sorted(group["components"] or (), key=fingerprint),
                "source_refs": sorted(group["source_refs"], key=fingerprint)}
               for group in sorted(groups, key=lambda group: group["group_id"])]
    if fingerprint(records) != manifest["dependency_fingerprints"]["groups"]:
        raise ValueError("group display projection fingerprint differs from the distance run")
    selected = []
    for identity in observation["group_ids"]:
        group = groups[ids.index(identity)]
        if group["status"] != "available" or not group["components"]:
            raise ValueError("endpoint group has no complete saved projection to highlight")
        refs = group["source_refs"]
        if (not refs or any(not isinstance(ref, str) or not ref for ref in refs)
                or refs != observation["lineage"]["group_source_refs"][identity]
                or sorted(refs) != sorted(observation["geometry_audit"][identity]["source_refs"])):
            raise ValueError("endpoint group members differ from the recorded observation")
        for component in group["components"]:
            for ring in (component["exterior"], *component.get("holes", ())):
                if len(ring) < 3:
                    raise ValueError("endpoint group projection ring is incomplete")
                for point in ring:
                    _vector(point, 2)
        selected.append(group)
    return selected


def prepare_comparison(manifest, observation, baseline_manifest, baseline_observation):
    """Require the same physical input and pair before overlaying historical algorithms."""
    keys = ("source_identity", "analysis_plane", "domain", "grid", "origin_offset", "query_context",
            "dependency_fingerprints", "group_ids")
    if (any(manifest[key] != baseline_manifest[key] for key in keys)
            or observation["pair_id"] != baseline_observation["pair_id"]
            or observation["group_ids"] != baseline_observation["group_ids"]
            or observation["center_to_center_euclidean"] != baseline_observation["center_to_center_euclidean"]):
        raise ValueError("comparison must use the same recorded input and group pair")


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


def _group_label(name, text, point, scale, parent, material, metadata, bpy):
    """Place an owned plan label beside the complete saved endpoint projection."""
    data = bpy.data.curves.new(name, "FONT")
    data.body, data.size, data.align_x = text, .27 / scale, "CENTER"
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent, obj.location = parent, point
    data.materials.append(material)
    for block, role in ((obj, "overlay"), (data, "board_mesh")):
        block["om_analysis_owner"], block["om_analysis_role"] = "order_analyzer", role
    obj["om_analysis_preview"] = True
    for key, value in metadata.items():
        obj[key] = value
    return obj


def _file_hash(path):
    """Hash actual input and output bytes for the static preview receipt."""
    with Path(path).open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def plan_ortho_scale(width, height, aspect):
    """Fit both board extents when Blender's orthographic scale controls image width."""
    return max(width, height * aspect) * 1.13


def render_plan_comparison(run_dir, baseline_run_dir, pair_id, free_space_result, output_path):
    """Plot exact recorded old/new routes and complete groups in a compact comparison."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from matplotlib.colors import ListedColormap
    import numpy as np
    from adapters import blender_analysis_result_wire as wire

    run_dir, baseline_run_dir, output_path = Path(run_dir), Path(baseline_run_dir), Path(output_path)
    manifest, observation = load_run(run_dir, pair_id)
    baseline_manifest, baseline = load_run(baseline_run_dir, pair_id)
    prepare_comparison(manifest, observation, baseline_manifest, baseline)
    geometry = wire.load_json((run_dir / "scene_geometry.json").read_text(encoding="utf-8"))
    groups = prepare_groups(geometry, manifest, observation)
    document = wire.load_json(Path(free_space_result).read_text(encoding="utf-8"))
    wire.validate_document(document)
    reference = manifest["query_context"]["result_ref"]
    layers = [prepare_route(m, o, document, reference) for m, o in ((baseline_manifest, baseline), (manifest, observation))]
    figure, axes = plt.subplots(1, 3, figsize=(19, 7))
    domain_points = [p for component in geometry["domain"]["components"] for p in component["exterior"]]
    pair_points = [point for group in groups for component in group["components"] for point in component["exterior"]]
    pair_points.extend(point for layer in layers for point in layer["main"])
    spacing = manifest["grid"]["spacing"]
    grid = manifest["grid"]
    values = np.full((grid["n_rows"], grid["n_cols"]), np.nan)
    for sample in manifest["cell_samples"]:
        if sample["status"] != "outside":
            row, column = sample["cell_key"]
            values[row, column] = (3 if sample["status"] == "conditional" else
                                   0 if sample["value"] is False else 1 if sample["value"] is True else 2)
    xs = grid["origin"][0] + np.arange(grid["n_cols"] + 1) * spacing
    ys = grid["origin"][1] + np.arange(grid["n_rows"] + 1) * spacing
    for index, axis in enumerate(axes):
        # The background is the same authoritative Boolean sample grid, never a reconstructed corridor.
        axis.pcolormesh(xs, ys, values, cmap=ListedColormap(("#eef7ec", "#cbd1d5", "#f6d584", "#e6daf4")), vmin=0, vmax=3)
        for component in geometry["domain"]["components"]:
            for ring in (component["exterior"], *component.get("holes", ())):
                axis.add_patch(Polygon(ring, facecolor="none", edgecolor="#238543", linewidth=1))
        for side, (group, color) in enumerate(zip(groups, ("#ed7400", "#009dae"))):
            for component in group["components"]:
                for ring in (component["exterior"], *component.get("holes", ())):
                    axis.add_patch(Polygon(ring, facecolor="none", edgecolor=color, linewidth=2))
            centroid = observation["geometry_audit"][group["group_id"]]["centroid"]
            axis.annotate(f"Group {'AB'[side]} ({len(group['source_refs'])} members)", centroid,
                          xytext=(4, 9 if side == 0 else -16), textcoords="offset points", color=color,
                          fontsize=9, bbox=dict(facecolor="white", alpha=.85, edgecolor="none", pad=1))
        for route_index in ((0, 1) if index == 0 else (index - 1,)):
            layer = layers[route_index]
            color = "#526f84" if route_index == 0 else "#e52b24"
            if layer["main"]:
                axis.plot(*zip(*layer["main"]), color=color, linewidth=1.6,
                          label="4-neighbor path" if route_index == 0 else "8-neighbor path")
            for offset_index, offset in enumerate(layer["offsets"]):
                axis.plot(*zip(*offset), color="#8054ba", linestyle="--", linewidth=1.2,
                          label="endpoint offsets" if offset_index == 0 else None)
        points = domain_points if index == 0 else pair_points
        axis.set_xlim(min(p[0] for p in points)-.5, max(p[0] for p in points)+.5)
        axis.set_ylim(min(p[1] for p in points)-.5, max(p[1] for p in points)+.5)
        axis.set_aspect("equal")
        axis.set_xlabel("Analysis-plane X (m)")
        axis.set_ylabel("Analysis-plane Y (m)")
        axis.legend(loc="upper right", fontsize=8)
    old, new = (item["centroid_free_space_hybrid"]["value"] for item in (baseline, observation))
    axes[0].set_title("Same S3 / exact free-space grid")
    for axis, name, item in zip(axes[1:], ("Before: 4-neighbor", "After: 8-neighbor, no corner cut"), (baseline, observation)):
        reading = item["centroid_free_space_hybrid"]
        value = "null" if reading["value"] is None else f"{reading['value']:.5f}"
        route_value = reading.get("free_space_route_distance")
        route_text = "null" if route_value is None else f"{route_value:.5f}"
        axis.set_title(f"{name}\nHybrid {value} m | free-cell path {route_text} m")
    delta = f" | reduction {old-new:.5f} m ({(old-new)/old:.2%})" if old is not None and new is not None and old > 0 else ""
    figure.suptitle(f"STATIC HISTORICAL | {pair_id}{delta}\n"
                   "Orange/cyan: complete endpoint groups. Purple dashed: centroid/proxy/access offsets.", fontsize=11)
    figure.text(.01, .01, f"Exact free-space {reference['result_id']} | SHA256 {reference['digest']}\n"
                + " | ".join(f"Group {'AB'[i]}: {group['group_id']}" for i, group in enumerate(groups)), fontsize=8)
    figure.tight_layout(rect=(0, .07, 1, .91))
    if output_path.exists():
        raise ValueError("comparison PNG output already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=155)
    plt.close(figure)
    return str(output_path.resolve())


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
    run_names = ("run_manifest.json", "observations.json", "pair_index.json", "scene_geometry.json")
    input_paths = [source_board, args.free_space_result.resolve(), Path(__file__).resolve(),
                   *(args.run_dir.resolve() / name for name in run_names)]
    if args.baseline_run_dir:
        input_paths.extend(args.baseline_run_dir.resolve() / name for name in run_names)
    hashes = {str(path): _file_hash(path) for path in input_paths}
    manifest, observation = load_run(args.run_dir, args.pair_id)
    geometry = wire.load_json((args.run_dir / "scene_geometry.json").read_text(encoding="utf-8"))
    groups = prepare_groups(geometry, manifest, observation)
    baseline_manifest = baseline_observation = None
    if args.baseline_run_dir:
        baseline_manifest, baseline_observation = load_run(args.baseline_run_dir, observation["pair_id"])
        prepare_comparison(manifest, observation, baseline_manifest, baseline_observation)
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
    baseline_layer = prepare_route(baseline_manifest, baseline_observation, result.document, reference) if baseline_manifest else None
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
    layers = [
            ("Recorded free-cell route", [layer["main"]] if layer["main"] else [], (1., .05, .04, 1.), .075, False),
            ("Endpoint offset", layer["offsets"], (.62, .04, .9, 1.), .045, True)]
    if baseline_layer:
        layers.insert(0, ("Baseline four-neighbor route", [baseline_layer["main"]] if baseline_layer["main"] else [],
                          (.21, .35, .48, 1.), .12, False))
        layers.insert(1, ("Baseline endpoint offset", baseline_layer["offsets"], (.39, .48, .56, 1.), .055, True))
    group_reports = []
    for index, (group, color) in enumerate(zip(groups, ((1., .36, .015, 1.), (.01, .62, .73, 1.)))):
        name = "Group " + "AB"[index]
        rings = [list(ring) + [ring[0]] for component in group["components"]
                 for ring in (component["exterior"], *component.get("holes", ()))]
        layers.append((name + " complete projection", rings, color, .065, False))
        all_points = [point for component in group["components"] for point in component["exterior"]]
        x = (min(p[0] for p in all_points) + max(p[0] for p in all_points)) / 2
        y = max(p[1] for p in all_points) + .18 if index == 0 else min(p[1] for p in all_points) - .4
        label_material = board._material(record["board_id"], name + " label", color, bpy)
        label_point = native_route_points([[x, y]], plane, manifest["origin_offset"], scale, z + .002)[0]
        _group_label(name + " label", f"{name} ({len(group['source_refs'])} members)", label_point,
                     scale, display, label_material, metadata, bpy)
        group_reports.append(dict(label=name, group_id=group["group_id"], source_refs=group["source_refs"],
                                  member_count=len(group["source_refs"]), component_count=len(group["components"]),
                                  outline_ring_count=len(rings)))
    for name, paths, color, width, dashed in layers:
        material = board._material(record["board_id"], name, color, bpy) if paths else None
        if material:
            shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
            shader.inputs["Emission Color"].default_value = material.diffuse_color
            shader.inputs["Emission Strength"].default_value = .7
        for index, path in enumerate(paths):
            # Separate presentation layers slightly in Z so coincident recorded XY segments cannot flicker.
            lift = .002 if name.startswith("Group") else 0 if name.startswith("Baseline") else .001
            points = native_route_points(path, plane, manifest["origin_offset"], scale, z + lift)
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
    total = observation["centroid_free_space_hybrid"]["value"]
    baseline_total = baseline_observation["centroid_free_space_hybrid"]["value"] if baseline_observation else None
    comparison_text = (f"4-neighbor {baseline_total:.5f} m -> 8-neighbor {total:.5f} m | "
                       if baseline_total is not None and total is not None else "")
    scene.render.stamp_note_text = (f"STATIC HISTORICAL | pair {layer['pair_id']} | {layer['status']} | metres\n"
        f"{comparison_text}Red: recorded route. Blue-gray: baseline. Purple dashed: endpoint offsets.\n"
        f"Orange: whole Group A. Cyan: whole Group B. Labels show all member counts.\n"
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
                  model={key: manifest[key] for key in ("algorithm_version", "schema_version")},
                  endpoint_groups=group_reports,
                  baseline=dict(run_dir=str(args.baseline_run_dir.resolve()),
                                hybrid=baseline_observation["centroid_free_space_hybrid"],
                                main_point_count=len(baseline_layer["main"]),
                                model={key: baseline_manifest[key] for key in ("algorithm_version", "schema_version")}) if baseline_layer else None,
                  offset_point_counts=[len(path) for path in layer["offsets"]],
                  route_object_count=len(native)-sum(group["outline_ring_count"] for group in group_reports),
                  group_outline_object_count=sum(group["outline_ring_count"] for group in group_reports),
                  input_sha256=hashes, output_sha256={str(path.resolve()): _file_hash(path) for path in (blend, png)},
                  analysis_plane=plane, origin_offset=manifest["origin_offset"], native_scale=scale,
                  display_only_lift_above_board_m=.009,
                  display_only_layer_lifts_m={"baseline": .008, "current_route": .009, "group_outlines": .010},
                  blender_version=bpy.app.version_string,
                  source_context="Existing board scene only; no full IFC source geometry imported.",
                  legend={"red": "recorded current-model free-cell path", "blue_gray": "recorded four-neighbor baseline path",
                          "purple_dashed": "centroid/proxy/access offsets; not free-space path",
                          "orange": "complete Group A projection", "cyan": "complete Group B projection"},
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
    parser.add_argument("--baseline-run-dir", type=Path)
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    render(parser.parse_args(args))


if __name__ == "__main__":
    main()
