"""Persistent historical result boards; numerical authority stays in external JSON."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from . import overlay, palettes

wire = overlay.wire
DESCRIPTOR_PROPERTY = "om_analysis_board"
DISPLAY_ROLES = frozenset({"board", "board_source", "board_display", "board_mesh", "board_material", "board_nodes"})
DEFAULT_STYLE = dict(palette="cividis", reverse=False, opacity=.5, range_mode="auto",
                     range_min=0., range_max=1., display_elevation_m=.02)
SOURCE_LIFT_M = .02


def _native(bpy_module):
    """Import Blender only at the native presentation boundary."""
    if bpy_module is None:
        import bpy as bpy_module
    return bpy_module


def _tag(datablock, role, board_id=None):
    """Mark only resources explicitly created for this presentation boundary."""
    datablock["om_analysis_owner"] = "order_analyzer"
    datablock["om_analysis_role"] = role
    if board_id is not None:
        datablock["om_analysis_board_id"] = board_id


def owned_display_datablock(datablock):
    """Recognize only explicitly owned board presentation datablocks."""
    get = getattr(datablock, "get", None)
    return callable(get) and get("om_analysis_owner") == "order_analyzer" and get("om_analysis_role") in DISPLAY_ROLES


def scene_boards(*, bpy_module=None):
    """Return this scene's owned board Empties."""
    bpy_module = _native(bpy_module)
    return tuple(obj for obj in bpy_module.context.scene.objects
                 if owned_display_datablock(obj) and obj.get("om_analysis_role") == "board"
                 and getattr(obj, "type", None) == "EMPTY")


def _text(value, name):
    """Require explicit stable identity and path strings in saved descriptors."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " must be a nonempty string")
    return value


def _datum_binding(datum, project, domain):
    """Validate a complete explicit ground receipt and retain all of its evidence."""
    required = {"project_global_id", "storey_ref", "storey_id", "mode", "slab_ref", "slab_id",
                "datum_z_m", "geometry_digest", "observation_digest"}
    if not isinstance(datum, Mapping) or not required <= datum.keys() or datum.get("mode") != "slab":
        raise ValueError("board requires an explicit selected slab datum receipt")
    datum = wire.plain(datum)
    if datum["project_global_id"] != _text(project, "project identity"):
        raise ValueError("datum project differs from result project identity")
    if not isinstance(domain, Mapping) or not domain:
        raise ValueError("board requires an explicit domain identity")
    palettes.finite_number(datum["datum_z_m"], "datum height")
    for kind in ("slab", "storey"):
        ref, step_id = datum[kind + "_ref"], datum[kind + "_id"]
        if (not isinstance(ref, str) or not ref.startswith("ifc-object:") or not ref[11:].strip()
                or type(step_id) is not int or step_id <= 0):
            raise ValueError("datum requires exact slab and storey identity")
    for name in ("geometry_digest", "observation_digest"):
        token = datum[name]
        if not isinstance(token, str) or len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
            raise ValueError("datum requires SHA256 evidence")
    # Native receipt hashing uses ASCII-escaped JSON; preserve that recipe without importing capture.
    receipt_json = json.dumps({key: value for key, value in datum.items() if key != "observation_digest"},
                             sort_keys=True, separators=(",", ":"), allow_nan=False)
    if sha256(receipt_json.encode()).hexdigest() != datum["observation_digest"]:
        raise ValueError("datum observation digest mismatch")
    return dict(project_global_id=project, domain_identity=wire.plain(domain),
                slab_ref=datum["slab_ref"], storey_ref=datum["storey_ref"], datum=datum)


def _binding(result):
    """Derive stable project/domain/ground binding independently from display metadata."""
    document = result.document
    if document["kind"] != "free_space_run":
        raise ValueError("boards require a free-space result")
    request = document["tables"]["snapshot"]["request"]
    identity = document["identity"]
    return _datum_binding(request.get("height_band_datum"),
                          identity.get("project_source_identity", {}).get("project_global_id"),
                          identity.get("domain_identity"))


def board_record(board):
    """Return the validated saved descriptor for UI and selection."""
    if not owned_display_datablock(board) or board.get("om_analysis_role") != "board":
        raise ValueError("object is not an owned analysis board")
    try:
        record = wire.load_json(board[DESCRIPTOR_PROPERTY])
        required = {"version", "board_id", "binding", "results", "active_result_id", "style", "status", "message"}
        if (not isinstance(record, dict) or set(record) != required or type(record["version"]) is not int
                or record["version"] != 1):
            raise ValueError("invalid board descriptor version or fields")
        _text(record["board_id"], "board identity")
        if record["board_id"] != board.get("om_analysis_board_id"):
            raise ValueError("board identity differs from ownership tag")
        binding = record["binding"]
        if (set(binding) != {"project_global_id", "domain_identity", "slab_ref", "storey_ref", "datum"}
                or _datum_binding(binding["datum"], binding["project_global_id"], binding["domain_identity"]) != binding):
            raise ValueError("invalid board binding")
        if set(record["style"]) != set(DEFAULT_STYLE):
            raise ValueError("invalid board style fields")
        palettes.validate_style(record["style"])
        if record["status"] not in {"historical", "unavailable"} or not isinstance(record["message"], str):
            raise ValueError("invalid historical display status")
        if not isinstance(record["results"], list) or not record["results"]:
            raise ValueError("board requires explicit external result entries")
        ids = []
        for entry in record["results"]:
            if set(entry) != {"ref", "path", "expected_identity", "backend_versions"}:
                raise ValueError("invalid external result entry")
            ref = wire.ResultRef(**entry["ref"])
            if ref.kind != "free_space_run":
                raise ValueError("board entry must be free-space")
            _text(entry["path"], "result path")
            if not Path(entry["path"]).is_absolute():
                raise ValueError("saved result path must be absolute")
            if (not isinstance(entry["expected_identity"], dict) or not entry["expected_identity"]
                    or not isinstance(entry["backend_versions"], dict) or not entry["backend_versions"]):
                raise ValueError("external result requires independent identity and backend expectations")
            ids.append(ref.result_id)
        if len(set(ids)) != len(ids) or record["active_result_id"] not in ids:
            raise ValueError("invalid or ambiguous active result identity")
        return record
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("invalid board descriptor") from error


def _save(board, record):
    """Persist one finite JSON descriptor without any runtime-current evidence."""
    board[DESCRIPTOR_PROPERTY] = wire.canonical_json(record)


def _entry(result, result_path):
    """Freeze expectations from the validated publication, never from a later file read."""
    document = result.document
    return dict(ref=dict(kind=document["kind"], result_id=document["result_id"], digest=document["digest"]),
                path=str(Path(result_path).resolve()), expected_identity=wire.plain(document["identity"]),
                backend_versions=wire.plain(document["backend_versions"]))


def _open_entry(entry, binding):
    """Open an exact external ref historically against independently saved expectations."""
    document = wire.load_json(Path(entry["path"]).read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("external analysis result must be a JSON object")
    snapshot = wire.open_analysis_result([document], result_ref=wire.ResultRef(**entry["ref"]),
        context=wire.ResultReadContext(expected=entry["expected_identity"], backend_versions=entry["backend_versions"],
                                       allow_historical=True))
    result = wire.ValidatedAnalysisResult(snapshot.payload)
    if _binding(result) != binding:
        raise ValueError("result project/domain/datum binding differs from board")
    return result


def _display(board, bpy_module):
    """Find the one explicitly owned display child, rejecting ambiguous native state."""
    children = [obj for obj in bpy_module.context.scene.objects if owned_display_datablock(obj)
                and obj.get("om_analysis_role") == "board_display" and obj.parent is board]
    if len(children) > 1:
        raise ValueError("board has ambiguous display children")
    return children[0] if children else None


def _source(result, bpy_module):
    """Reuse only exact-ref geometry built for the active native unit scale."""
    scale = overlay.native_unit_scale(bpy_module)
    ref_json = wire.canonical_json(dict(kind=result.kind, result_id=result.result_id, digest=result.digest))
    for obj in bpy_module.context.scene.objects:
        if (owned_display_datablock(obj) and obj.get("om_analysis_role") == "board_source"
                and obj.get("om_analysis_result_ref") == ref_json and obj.get("om_analysis_native_scale") == scale):
            obj.hide_viewport = obj.hide_render = True
            return obj
    plane = result.document["tables"]["snapshot"]["request"]["plane"]
    origin = plane.get("origin")
    if not isinstance(origin, (list, tuple)) or len(origin) != 3:
        raise ValueError("board requires explicit analysis plane origin")
    plane_z = palettes.finite_number(origin[2], "analysis plane height")
    # A vertical translation preserves world XY and only applies to this supported horizontal board.
    if any(abs(vertex[2] - plane_z) > 1e-6 for fragment in result.display_fragments for vertex in fragment["vertices"]):
        raise ValueError("board requires horizontal result fragments at the analysis plane")
    source = overlay.build_native_mesh(result, bpy_module=bpy_module, name="OM Analysis Result", display_lift_m=SOURCE_LIFT_M)
    _tag(source, "board_source")
    _tag(source.data, "board_mesh")
    source["om_analysis_result_ref"] = ref_json
    source["om_analysis_native_scale"] = scale
    source["om_analysis_plane_z_m"] = plane_z
    source["om_analysis_display_lift_m"] = SOURCE_LIFT_M
    source.hide_viewport = source.hide_render = True
    # Slot indices encode categories once; style updates only change object-bound materials.
    face_index = 0
    categories = [name for name, label in palettes.LEGEND]
    for fragment in result.display_fragments:
        cell = result.cells[fragment["cell_index"]]
        category = ("occupied" if cell["value"] else "empty") if cell["status"] == "established" else cell["status"]
        for face in fragment["faces"]:
            source.data.polygons[face_index].material_index = categories.index(category)
            face_index += 1
    return source


def _material(board_id, category, rgba, bpy_module):
    """Build an owned real shader material supporting global alpha in EEVEE."""
    material = bpy_module.data.materials.new("OM Board " + category)
    _tag(material, "board_material", board_id)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    shader = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    output = next((node for node in nodes if node.type == "OUTPUT_MATERIAL"), None)
    if shader is None:
        shader = nodes.new("ShaderNodeBsdfPrincipled")
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    _tag(material.node_tree, "board_nodes", board_id)
    _color_material(material, rgba)
    return material


def _color_material(material, rgba):
    """Update actual shader sockets as well as the solid-mode viewport swatch."""
    # Matplotlib samples are sRGB; Blender shader and viewport colors are scene-linear.
    rgba = (*tuple(channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4
                   for channel in rgba[:3]), rgba[3])
    shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Alpha"].default_value = rgba[3]
    shader.inputs["Roughness"].default_value = .8
    material.diffuse_color = rgba
    if hasattr(material, "surface_render_method"):
        rna = getattr(material, "bl_rna", None)
        choices = {item.identifier for item in rna.properties["surface_render_method"].enum_items} if rna else {"DITHERED"}
        material.surface_render_method = "DITHERED" if "DITHERED" in choices else "BLENDED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "BLEND"


def _style_display(display, board_id, style, binding, bpy_module):
    """Apply object-bound categorical materials and a datum-relative metre lift."""
    source_scale = display.data.get("om_analysis_native_scale")
    scale = overlay.native_unit_scale(bpy_module)
    if source_scale != scale:
        raise ValueError("display geometry scene scale differs; select or restore its external result")
    # Geometry is shared; each board's OBJECT material overrides keep styles independent.
    for index, (category, label) in enumerate(palettes.LEGEND):
        rgba = palettes.cell_color(category == "occupied", "established" if index < 2 else category,
                                   palette=style["palette"], reverse=style["reverse"], opacity=style["opacity"])
        slot = display.material_slots[index] if index < len(display.material_slots) else None
        material = slot.material if slot is not None else None
        if (not owned_display_datablock(material) or material.get("om_analysis_board_id") != board_id
                or slot is None or slot.link != "OBJECT"):
            material = _material(board_id, category, rgba, bpy_module)
        else:
            _color_material(material, rgba)
        if index >= len(display.data.materials):
            display.data.materials.append(material)
        slot = display.material_slots[index]
        slot.link = "OBJECT"
        slot.material = material
    plane_z = display.data["om_analysis_plane_z_m"]
    source_lift = display.data["om_analysis_display_lift_m"]
    display.location = (0., 0., (binding["datum"]["datum_z_m"] + style["display_elevation_m"] - plane_z - source_lift) / scale)


def _present(board, record, result, bpy_module):
    """Reuse one display child over a hidden exact-ref source without moving the plane."""
    source = _source(result, bpy_module)
    for key in ("om_analysis_native_scale", "om_analysis_plane_z_m", "om_analysis_display_lift_m"):
        source.data[key] = source[key]
    display = _display(board, bpy_module)
    created = display is None
    if display is None:
        display = bpy_module.data.objects.new("OM Analysis Board Display", source.data)
        _tag(display, "board_display", record["board_id"])
        display.parent = board
    previous_data, previous_location = display.data, tuple(display.location)
    previous_slots = [(slot.link, slot.material) for slot in display.material_slots]
    try:
        display.data = source.data
        _style_display(display, record["board_id"], record["style"], record["binding"], bpy_module)
    except Exception:
        # A native style failure must not replace the previous valid result presentation.
        display.data, display.location = previous_data, previous_location
        for slot, (link, material) in zip(display.material_slots, previous_slots):
            slot.link, slot.material = link, material
        raise
    if created:
        bpy_module.context.scene.collection.objects.link(display)
    display["om_analysis_result_id"] = result.result_id
    display.hide_viewport = display.hide_render = False
    return source


def attach_result(result, *, result_path, bpy_module=None):
    """Create/reuse a bound board and hidden source, returning the board Empty."""
    if not isinstance(result, wire.ValidatedAnalysisResult):
        raise TypeError("result must be a ValidatedAnalysisResult")
    wire.validate_document(result.document)
    binding = _binding(result)
    bpy_module = _native(bpy_module)
    overlay.native_unit_scale(bpy_module)
    entry = _entry(result, result_path)
    _open_entry(entry, binding)
    matches = [board for board in scene_boards(bpy_module=bpy_module) if board_record(board)["binding"] == binding]
    if len(matches) > 1:
        raise ValueError("ambiguous boards for this binding")
    if matches:
        board = matches[0]
        record = board_record(board)
        previous = next((item for item in record["results"] if item["ref"]["result_id"] == result.result_id), None)
        if previous is not None and previous["ref"] != entry["ref"]:
            raise ValueError("registered result identity has different content")
        if previous is None:
            record["results"].append(entry)
        else:
            previous["path"] = entry["path"]
    else:
        board = bpy_module.data.objects.new("OM Analysis Board", None)
        board_id = str(uuid4())
        _tag(board, "board", board_id)
        record = dict(version=1, board_id=board_id, binding=binding, results=[entry],
                      active_result_id=result.result_id, style=dict(DEFAULT_STYLE), status="historical", message="")
    _present(board, record, result, bpy_module)
    record.update(active_result_id=result.result_id, status="historical", message="Historical display; currentness requires a live verified observation.")
    _save(board, record)
    if not matches:
        bpy_module.context.scene.collection.objects.link(board)
    return board


def select_result(board, result_id, *, bpy_module=None):
    """Strictly open a registered external result and show it historically."""
    record = board_record(board)
    entry = next((item for item in record["results"] if item["ref"]["result_id"] == result_id), None)
    if entry is None:
        raise ValueError("result is not explicitly registered on this board")
    result = _open_entry(entry, record["binding"])
    _present(board, record, result, _native(bpy_module))
    record.update(active_result_id=result_id, status="historical", message="Historical display; currentness requires a live verified observation.")
    _save(board, record)
    return result


def update_style(board, *, palette=None, reverse=None, opacity=None,
                 range_mode=None, range_min=None, range_max=None,
                 display_elevation_m=None, bpy_module=None):
    """Validate, persist and apply display settings without numerical mutation.

    display_elevation_m is a nonnegative lift ABOVE the selected slab top.
    """
    record = board_record(board)
    changes = dict(palette=palette, reverse=reverse, opacity=opacity, range_mode=range_mode,
                   range_min=range_min, range_max=range_max, display_elevation_m=display_elevation_m)
    record["style"].update({key: value for key, value in changes.items() if value is not None})
    palettes.validate_style(record["style"])
    bpy_module = _native(bpy_module)
    display = _display(board, bpy_module)
    if display is not None and record["status"] != "unavailable":
        _style_display(display, record["board_id"], record["style"], record["binding"], bpy_module)
    _save(board, record)
    return record["style"]


def restore_boards(*, bpy_module=None):
    """Restore this scene's boards historically; report missing refs on the board."""
    bpy_module = _native(bpy_module)
    boards = scene_boards(bpy_module=bpy_module)
    for board in boards:
        try:
            record = board_record(board)
            select_result(board, record["active_result_id"], bpy_module=bpy_module)
        except (OSError, ValueError, TypeError) as error:
            display = _display(board, bpy_module)
            if display is not None:
                display.hide_viewport = display.hide_render = True
            # A malformed descriptor cannot safely supply binding/results, so leave its bytes intact.
            try:
                record = board_record(board)
            except ValueError:
                continue
            record.update(status="unavailable", message=str(error))
            _save(board, record)
    return boards
