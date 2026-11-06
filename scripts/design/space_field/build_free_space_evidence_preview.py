"""Render authenticated free-space evidence in a separate portable Blender process."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters import blender_analysis_result_wire as wire

BLENDER = Path("D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")
COLORS = {
    "established_free": (0.39, 0.76, 0.57),
    "established_occupied": (0.19, 0.25, 0.33),
    "conditional_free": (0.91, 0.72, 0.31),
    "conditional_occupied": (0.63, 0.40, 0.62),
    "unknown": (0.91, 0.52, 0.19),
    "outside": (0.85, 0.87, 0.90),
    "invalid": (0.80, 0.20, 0.23),
    "not_available": (0.56, 0.50, 0.64),
}
STATUS = {"established": "computed", "conditional": "partial", "unknown": "partial",
          "outside": "outside", "invalid": "invalid", "not_available": "not_available"}


def category(cell):
    """Keep conditional and unavailable states visibly separate from established free."""
    status, occupied = cell["status"], cell["value"]
    if (status not in STATUS or (occupied is not None and type(occupied) is not bool)
            or (status in {"established", "conditional"}) != (type(occupied) is bool)):
        raise ValueError("invalid occupancy value/status in preview")
    return status + ("_occupied" if occupied else "_free") if type(occupied) is bool else status


def prepare_preview(package, manifest):
    """Bind every depicted fragment and package target to the retained raw cell."""
    if (package.get("schema") != "evidence-package-output/v1"
            or manifest.get("output_identity") != package.get("output_identity")
            or manifest.get("channel") != "free_space"
            or len(package.get("source_envelopes", ())) != 1):
        raise ValueError("preview package/manifest identity or channel mismatch")
    document = package["source_envelopes"][0]["value"]["channels"][0]["observation"]["document"]
    wire.validate_document(document)
    reference = {key: document[key] for key in ("kind", "result_id", "digest")}
    if manifest.get("source_result_ref") != reference:
        raise ValueError("preview requires the manifest's exact retained ResultRef")
    if "live scene not observed" not in manifest.get("freshness_scope", ""):
        raise ValueError("retained preview must declare its historical observation scope")
    cells, fragments = document["cells"], document["display_fragments"]
    fragments_by_cell = defaultdict(list)
    for index, fragment in enumerate(fragments):
        fragments_by_cell[fragment["cell_index"]].append(index)
    targets = manifest["targets"]
    by_id = {item["target_id"]: item for item in targets}
    if len(by_id) != len(targets) or len(targets) != len(cells) or len(package["outputs"]) != len(cells):
        raise ValueError("preview must retain every unique package cell target")
    seen = set()
    for output in package["outputs"]:
        target = by_id[output["target"]["identity"]]
        locator, observation = output["observation"]["cell_locator"], output["observation"]
        index = locator["cell_index"]
        if type(index) is not int or not 0 <= index < len(cells) or index in seen:
            raise ValueError("invalid or repeated package cell locator")
        seen.add(index)
        cell = cells[index]
        value = not cell["value"] if type(cell["value"]) is bool else None
        if (output["channel"] != "free_space" or output["status"] != STATUS[cell["status"]]
                or locator["result_ref"] != reference
                or any(locator[key] != cell[key] or target[key] != cell[key] for key in ("row", "column"))
                or target["cell_index"] != index
                or target["fragment_indices"] != fragments_by_cell[index]
                or observation["raw_status"] != cell["status"]
                or observation["physical_occupancy"] is not cell["value"]
                or observation["value"] is not value):
            raise ValueError("preview target, observation or fragment differs from raw evidence")
    counts = Counter(category(cell) for cell in cells)
    depicted = Counter(category(cells[index]) for index in fragments_by_cell if fragments_by_cell[index])
    return document, dict(counts), dict(depicted)


def file_hash(path):
    """Fingerprint exact artifacts without loading their bytes into the receipt."""
    with path.open("rb") as source:
        import hashlib
        return hashlib.file_digest(source, "sha256").hexdigest()


def enum_id(owner, property_name, token):
    """Resolve native enum identifiers through RNA rather than localized node names."""
    return next(item.identifier for item in owner.bl_rna.properties[property_name].enum_items
                if token.lower() in item.identifier.lower())


def linear(value):
    """Convert display sRGB to the linear shader values Blender expects."""
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def material(bpy, name, color):
    """Use emission so lighting cannot change the categorical evidence colors."""
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    nodes = result.node_tree.nodes
    nodes.clear()
    emission, output = nodes.new("ShaderNodeEmission"), nodes.new("ShaderNodeOutputMaterial")
    emission.inputs[0].default_value = (*map(linear, color), 1)
    result.node_tree.links.new(emission.outputs[0], output.inputs[0])
    result.diffuse_color = (*color, 1)
    return result


def main():
    """Build a saved categorical plan without changing the user's live Blender scene."""
    import bpy
    from mathutils import Matrix, Vector

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if not bpy.app.background or Path(bpy.app.binary_path).resolve() != BLENDER.resolve():
        raise RuntimeError("Use only the specified portable Blender in background mode")
    source_hashes = {str(path.resolve()): file_hash(path) for path in (args.package_output, args.manifest)}
    package = wire.load_json(args.package_output.read_text(encoding="utf-8"))
    manifest = wire.load_json(args.manifest.read_text(encoding="utf-8"))
    document, counts, depicted = prepare_preview(package, manifest)
    args.out.mkdir(parents=True, exist_ok=True)
    png, blend = args.out / "free_space_evidence.png", args.out / "free_space_evidence.blend"
    if png.exists() or blend.exists():
        raise FileExistsError("Use an output directory without an existing native preview")
    # This reset affects only the dedicated background process, never the live user scene.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = enum_id(scene.unit_settings, "system", "METRIC")
    scene.unit_settings.scale_length = 1
    scene["output_identity"] = package["output_identity"]
    scene["source_result_ref"] = json.dumps(manifest["source_result_ref"], sort_keys=True)
    scene["freshness_scope"] = manifest["freshness_scope"]
    scene["geometry_role"] = "retained clipped display fragments; categorical free-space evidence"
    plane = document["tables"]["snapshot"]["request"]["plane"]
    origin, axes = Vector(plane["origin"]), [Vector(axis) for axis in plane["basis"]]
    rotation = Matrix(axes).transposed().to_quaternion()

    def point(x, y, lift=0):
        """Place display labels in the declared plane while preserving world-SI meshes."""
        return origin + x * axes[0] + y * axes[1] + lift * axes[2]

    def label(text, x, y, size=.25, color=(.10, .15, .22)):
        """Keep titles and legends in the same coordinate frame as the analysis."""
        data = bpy.data.curves.new(text, "FONT")
        data.body, data.size = text, size
        obj = bpy.data.objects.new(text, data)
        scene.collection.objects.link(obj)
        obj.location, obj.rotation_mode, obj.rotation_quaternion = point(x, y, .04), "QUATERNION", rotation
        data.materials.append(material(bpy, text, color))
        obj["geometry_role"] = "display_label"
        return obj

    geometry = {}
    for fragment in document["display_fragments"]:
        index = fragment["cell_index"]
        vertices, faces, indices = geometry.setdefault(category(document["cells"][index]), ([], [], []))
        offset = len(vertices)
        vertices.extend(fragment["vertices"])
        faces.extend(tuple(value + offset for value in face) for face in fragment["faces"])
        indices.extend([index] * len(fragment["faces"]))
    bindings = []
    for name, (vertices, faces, indices) in sorted(geometry.items()):
        mesh = bpy.data.meshes.new("FreeSpace:" + name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.attributes.new("cell_index", "INT", "FACE").data.foreach_set("value", indices)
        obj = bpy.data.objects.new("FreeSpace:" + name, mesh)
        scene.collection.objects.link(obj)
        obj["geometry_role"] = "exact_retained_display_fragments_world_SI"
        obj["raw_category"] = name
        obj["output_identity"] = package["output_identity"]
        mesh.materials.append(material(bpy, name, COLORS[name]))
        bindings.append({"category": name, "object": obj.name, "cell_attribute": "cell_index",
                         "target_count": len(set(indices)), "triangle_count": len(faces)})
    lattice = document["tables"]["lattice"]
    x0, y0 = lattice["origin"]
    x1 = x0 + lattice["n_cols"] * lattice["spacing"]
    y1 = y0 + lattice["n_rows"] * lattice["spacing"]
    label("FREE SPACE / EVIDENCE PACKAGE", x0, y1 + 2.4, .50)
    label("One evidence channel: free_space | retained IFC result | units: m", x0, y1 + 1.65, .28)
    label("Known free", x0, y1 + .9, .32, COLORS["established_free"])
    label(f"{counts.get('established_free', 0):,}", x0 + 2.6, y1 + .9, .32)
    label("Occupied", x0 + 6.8, y1 + .9, .32, COLORS["established_occupied"])
    label(f"{counts.get('established_occupied', 0):,}", x0 + 9.3, y1 + .9, .32)
    label("Outside / no fill", x0 + 13.4, y1 + .9, .32, (.44, .47, .52))
    label(f"{counts.get('outside', 0):,}", x0 + 17.4, y1 + .9, .32)
    label(f"{len(document['cells']):,} samples | {sum(depicted.values()):,} clipped cell fragments | spacing {lattice['spacing']:.2f} m", x0, y0 - .7, .27)
    query = document["tables"]["snapshot"]["request"]["geometry_query"]
    label(f"Query: {query['kind']} | analysis plane z = {plane['origin'][2]:.2f} m", x0, y0 - 1.15, .25)
    label("Historical result; live scene not observed. Blank exterior and holes are outside, not free.", x0, y0 - 1.6, .25)
    label(f"Result: {document['result_id']} | package: {package['output_identity'][:20]}", x0, y0 - 2.05, .23)
    camera_data = bpy.data.cameras.new("FreeSpace:PlanCamera")
    camera = bpy.data.objects.new("FreeSpace:PlanCamera", camera_data)
    scene.collection.objects.link(camera)
    camera_data.type = enum_id(camera_data, "type", "ORTHO")
    camera.rotation_mode, camera.rotation_quaternion = "QUATERNION", rotation
    camera.location = point((x0 + x1) / 2, (y0 + y1) / 2 + .25, 50)
    camera_data.ortho_scale = max(x1 - x0 + 1.6, (y1 - y0 + 6.0) * 4 / 3)
    scene.camera = camera
    # RNA exposes the installed real-time engine; emission needs no source-scene lights.
    scene.render.engine = enum_id(scene.render, "engine", "EEVEE")
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = enum_id(scene.render.image_settings, "file_format", "PNG")
    # Blender 5.2 exposes view transforms dynamically rather than through RNA enum items.
    try:
        scene.view_settings.view_transform = "Standard"
    except (TypeError, ValueError):
        pass
    scene.world = bpy.data.worlds.new("FreeSpace:WhiteWorld")
    scene.world.use_nodes = True
    background = next(node for node in scene.world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (*map(linear, (.98, .985, .99)), 1)
    scene.render.filepath = str(png.resolve())
    if bpy.ops.render.render(write_still=True) != {"FINISHED"}:
        raise RuntimeError("native preview render did not finish")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()), compress=True)
    if any(file_hash(Path(path)) != digest for path, digest in source_hashes.items()):
        raise ValueError("package or manifest changed while building native preview")
    receipt = {"schema": "free-space-evidence-native-preview/v1", "output_identity": package["output_identity"],
               "source_result_ref": manifest["source_result_ref"], "freshness_scope": manifest["freshness_scope"],
               "source_file_hashes": source_hashes, "total_targets": len(document["cells"]),
               "depicted_targets": sum(depicted.values()), "category_counts": counts,
               "depicted_category_counts": depicted, "mesh_bindings": bindings,
               "geometry_source": "unchanged world-SI vertices and faces from retained display_fragments",
               "blender_executable": str(BLENDER), "blender_version": bpy.app.version_string,
               "artifact_hashes": {str(path.resolve()): file_hash(path) for path in (png, blend)}}
    receipt_path = args.out / "native_preview_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
