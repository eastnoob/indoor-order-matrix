"""Capture the frozen B3 identities from live evaluated Blender geometry in batches.

Load into a dedicated module with exec(compile(...)); call begin_capture(), then
capture_next_batch(). Native imports and scene access occur only on those calls.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import uuid


ROOT = Path(r"D:\PROJECTS\understandOtherPackage\order_analyzer")
BINARY = Path(r"D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe")
SOURCE = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
FROZEN = ROOT / "outputs/design/b3_real_source_field/run_001/scope_inventory.json"
OWNER_DISK_EVIDENCE = {
    "origin": "owner disk verification supplied 2026-10-14; not live geometry evidence",
    "bytes": 408617800,
    "sha256": "018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240",
    "mtime_utc": "2026-09-23T13:19:05.204894Z",
}
_CAPTURE = None


def utc():
    """Return an unambiguous UTC timestamp for run and batch evidence."""
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    """Hash strict canonical JSON for compact observed-state comparisons."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def file_ref(path, relative_to):
    """Hash a small input or one output without retaining its bytes in memory."""
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": path.relative_to(relative_to).as_posix(),
            "bytes": path.stat().st_size, "sha256": checksum}


def write_json(path, value, *, checkpoint=False):
    """Write strict JSON; replace only this fresh run's checkpoint files."""
    target = path.with_suffix(".json.tmp") if checkpoint else path
    with target.open("w" if checkpoint else "x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False, separators=(",", ":"))
        stream.write("\n")
    if checkpoint:
        target.replace(path)


def match_inventory(expected, live):
    """Join identities by both keys, retaining ambiguity, mismatch and missingness."""
    by_step, by_guid = defaultdict(list), defaultdict(list)
    for item in live:
        if not item["in_scene"]:
            continue
        if item.get("step_id"):
            by_step[item["step_id"]].append(item)
        if item.get("global_id"):
            by_guid[item["global_id"]].append(item)
    records = []
    for source in expected:
        row = {key: source[key] for key in ("id", "step_id", "global_id")}
        step_hits, guid_hits = by_step[row["step_id"]], by_guid[row["global_id"]]
        row.update(geometry=None, is_closed=None, is_manifold=None, solid_query_eligible=None)
        if len(step_hits) > 1 or len(guid_hits) > 1:
            row["status"] = "duplicate_identity"
        elif not step_hits and not guid_hits:
            row["status"] = "missing_identity"
        elif (not step_hits or not guid_hits or step_hits[0] is not guid_hits[0]
              or step_hits[0].get("identity_error")):
            row["status"] = "identity_mismatch"
        else:
            row.update(status="pending", blender_name=step_hits[0]["blender_name"])
        row["identity_candidates"] = sorted({item["blender_name"] for item in step_hits + guid_hits})
        records.append(row)
    enrolled = {(row["step_id"], row["global_id"]) for row in expected}
    diagnostics = {
        "duplicates": {
            "step_id": {str(key): [item["blender_name"] for item in hits]
                        for key, hits in by_step.items() if len(hits) > 1},
            "global_id": {key: [item["blender_name"] for item in hits]
                          for key, hits in by_guid.items() if len(hits) > 1}},
        "extras": [item for item in live if
                   (item.get("step_id"), item.get("global_id")) not in enrolled or not item["in_scene"]],
        "missing_identities": [row["id"] for row in records if row["status"] == "missing_identity"],
    }
    return records, diagnostics


def declared_representations(entity):
    """Read declared IFC representations without choosing a consumer policy."""
    representation = getattr(entity, "Representation", None)
    return [{"step_id": rep.id(), "identifier": rep.RepresentationIdentifier,
             "type": rep.RepresentationType} for rep in representation.Representations] if representation else []


def loaded_representation(obj, model, tool):
    """Read the actual source datablock's Bonsai representation link."""
    if obj.type != "MESH":
        return None
    step = tool.Geometry.get_mesh_props(obj.data).ifc_definition_id
    rep = model.by_id(step) if step else None
    return {"step_id": step or None, "identifier": getattr(rep, "RepresentationIdentifier", None),
            "type": getattr(rep, "RepresentationType", None)}


def live_inventory(bpy, model, tool):
    """Observe every live object, including extras, bad links and other scenes."""
    scene_names = {obj.name for obj in bpy.context.scene.objects}
    inventory = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        row = {"blender_name": obj.name, "type": obj.type, "in_scene": obj.name in scene_names,
               "step_id": None, "global_id": None, "ifc_class": None}
        try:
            step = tool.Blender.get_object_bim_props(obj).ifc_definition_id
            row["step_id"] = step or None
            entity = model.by_id(step) if step else None
            if entity:
                row.update(global_id=getattr(entity, "GlobalId", None), ifc_class=entity.is_a(),
                           name=getattr(entity, "Name", None),
                           declared_representations=declared_representations(entity))
                if entity.id() != step:
                    row["identity_error"] = "linked STEP differs from resolved entity"
            row["loaded_representation"] = loaded_representation(obj, model, tool)
        except Exception as exc:
            row["identity_error"] = f"{type(exc).__name__}: {exc}"
        inventory.append(row)
    return inventory


def scene_state(bpy, store, model, tool):
    """Observe cheap invariants without hashing meshes or serializing the IFC."""
    scene, active = bpy.context.scene, bpy.context.view_layer.objects.active
    objects = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        data = obj.data
        objects.append({"name": obj.name, "pointer": obj.as_pointer(), "type": obj.type,
                        "step": tool.Blender.get_object_bim_props(obj).ifc_definition_id,
                        "matrix": [list(row) for row in obj.matrix_world],
                        "data": data.as_pointer() if data else None,
                        "data_name": data.name if data else None,
                        "loaded_representation_step": tool.Geometry.get_mesh_props(data).ifc_definition_id
                        if obj.type == "MESH" else None,
                        "counts": {key: len(getattr(data, key, ())) for key in
                                   ("vertices", "edges", "polygons")},
                        "modifiers": [(m.name, m.type, m.show_viewport, m.show_render) for m in obj.modifiers]})
    stat = SOURCE.stat()
    return {"objects": objects, "objects_sha256": digest(objects),
            "scene_objects": sorted(obj.name for obj in scene.objects), "scene": scene.name,
            "frame": scene.frame_current, "subframe": scene.frame_subframe,
            "units": {"system": scene.unit_settings.system, "scale_length": scene.unit_settings.scale_length},
            "selection": sorted(obj.name for obj in bpy.context.selected_objects),
            "active": active.name if active else None, "mode": bpy.context.mode,
            "camera": scene.camera.name if scene.camera else None,
            "blend_path": bpy.data.filepath, "dirty": bpy.data.is_dirty,
            "ifc_path": str(Path(store.path).resolve()), "ifc_model_identity": id(model),
            "ifc_schema": model.schema, "ifc_last_transaction": store.last_transaction,
            "ifc_history_count": len(store.history), "ifc_future_count": len(store.future),
            "source_ifc_bytes": stat.st_size, "source_ifc_mtime_ns": stat.st_mtime_ns}


def topology_quality(mesh):
    """Measure fresh indexed topology, leaving solid validity unqualified."""
    from adapters.blender_analysis_capture import topology_quality as capture_quality
    return capture_quality(mesh)


def extract_mesh(obj, depsgraph, metres_per_blender_unit, row):
    """Read evaluated world geometry and always free the temporary mesh."""
    from adapters.blender_analysis_capture import extract_evaluated_mesh
    snapshot = extract_evaluated_mesh(obj, depsgraph, metres_per_blender_unit, quality_reader=topology_quality)
    return snapshot | {"id": row["id"], "step_id": row["step_id"], "global_id": row["global_id"],
        "name": obj.name, "representation_id": str(row["loaded_representation"]["step_id"])
        if row["loaded_representation"]["step_id"] else None,
        "declared_representations": row["declared_representations"],
        "loaded_representation": row["loaded_representation"], "factual_properties": row["properties"]}


def capture_source(session, row, depsgraph):
    """Persist one matched source while retaining all extraction failures."""
    started = time.perf_counter()
    try:
        model, tool = session["model"], session["tool"]
        entity = model.by_id(row["step_id"])
        if entity.GlobalId != row["global_id"]:
            raise ValueError("source IFC identity changed during capture")
        obj = session["bpy"].data.objects[row["blender_name"]]
        if tool.Blender.get_object_bim_props(obj).ifc_definition_id != row["step_id"]:
            raise ValueError("source object IFC link changed during capture")
        from ifcopenshell.util.element import get_psets

        properties = get_psets(entity, psets_only=True)
        layout = properties.get("OM_Layout", {})
        row.update(ifc_class=entity.is_a(), name=entity.Name, properties=properties,
                   function=layout.get("FunctionalRole"), participation=layout.get("AnalysisParticipation"),
                   declared_representations=declared_representations(entity),
                   loaded_representation=loaded_representation(obj, model, tool),
                   containment=[{"relation_step": rel.id(), "relation_global_id": rel.GlobalId,
                                 "storey_step": rel.RelatingStructure.id(),
                                 "storey_global_id": rel.RelatingStructure.GlobalId}
                                for rel in getattr(entity, "ContainedInStructure", ())],
                   modifiers=[{"name": modifier.name, "type": modifier.type} for modifier in obj.modifiers])
        if obj.type != "MESH":
            row["status"] = "missing_linked_mesh" if row["declared_representations"] else "semantic_nonmass"
            return
        snapshot = extract_mesh(obj, depsgraph, session["metres_per_blender_unit"], row)
        path = session["out"] / "meshes" / f"{row['step_id']}.json"
        write_json(path, snapshot)
        row.update(status="extracted", geometry=file_ref(path, session["out"]),
                   vertices=len(snapshot["vertices"]), triangles=len(snapshot["triangles"]),
                   bounds_world_m=[[min(vertex[axis] for vertex in snapshot["vertices"]) for axis in range(3)],
                                   [max(vertex[axis] for vertex in snapshot["vertices"]) for axis in range(3)]],
                   quality=snapshot["quality"], is_closed=snapshot["is_closed"], is_manifold=snapshot["is_manifold"],
                   solid_query_eligible=snapshot["quality"]["solid_query_eligible"], captured_utc=utc())
    except Exception as exc:
        row.update(status="invalid_extraction", geometry=None, error=f"{type(exc).__name__}: {exc}")
    finally:
        row["elapsed_seconds"] = time.perf_counter() - started


def checkpoint(session):
    """Persist audit-only metadata after each batch, never the mesh arrays."""
    manifest = session["manifest"]
    manifest.update(inventory=session["records"], statuses=dict(Counter(row["status"] for row in session["records"])),
                    elapsed_seconds=time.perf_counter() - session["started_clock"])
    write_json(session["out"] / "scope_inventory.json", {
        "schema": "b3-live-scope-inventory/v1", "status": manifest["status"],
        "records": session["records"], "frozen_identity_source": manifest["frozen_identity_source"],
        "scope": manifest["historical_scope"], **session["diagnostics"],
        "policy": "358 exact frozen identities; live geometry only; extras not enrolled; unknown never known-free",
    }, checkpoint=True)
    write_json(session["out"] / "capture_manifest.json", manifest, checkpoint=True)


def progress(session):
    """Return a small MCP-safe progress record without full inventories or arrays."""
    remaining = sum(row["status"] == "pending" for row in session["records"])
    return {"directory": str(session["out"]), "status": session["manifest"]["status"],
            "done": session["manifest"]["status"] != "in_progress", "processed": len(session["records"]) - remaining,
            "remaining": remaining, "statuses": session["manifest"]["statuses"],
            "elapsed_seconds": session["manifest"]["elapsed_seconds"]}


def begin_capture():
    """Validate the authorized live session and create a unique capture directory."""
    global _CAPTURE
    if _CAPTURE is not None and _CAPTURE["manifest"]["status"] == "in_progress":
        raise RuntimeError("capture already active; continue capture_next_batch()")
    import bpy
    import bonsai.tool as tool
    from bonsai.bim.ifc import IfcStore
    from ifcopenshell.util.unit import calculate_unit_scale

    if Path(bpy.app.binary_path).resolve() != BINARY.resolve():
        raise ValueError("only the authorized portable Blender may capture")
    if Path(IfcStore.path).resolve() != SOURCE.resolve():
        raise ValueError("live IFC path differs from the authorized source")
    model = IfcStore.get_file()
    if model is None or model.schema != "IFC4":
        raise ValueError("the authorized live IFC4 model is required")
    if bpy.context.mode != "OBJECT":
        raise ValueError("capture requires OBJECT mode; script will not change mode")
    scale = bpy.context.scene.unit_settings.scale_length
    if bpy.context.scene.unit_settings.system != "METRIC" or not math.isfinite(scale) or scale <= 0:
        raise ValueError("positive explicit METRIC Blender scene units are required")
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    expected = frozen["records"]
    if (len(expected) != 358 or len({row["step_id"] for row in expected}) != 358
            or len({row["global_id"] for row in expected}) != 358
            or len({row["id"] for row in expected}) != 358
            or any(not isinstance(row["step_id"], int) or row["step_id"] <= 0
                   or not isinstance(row["global_id"], str) or not row["global_id"] for row in expected)):
        raise ValueError("frozen enrollment must contain 358 unique STEP/GlobalId/source identities")
    started_clock, started_utc = time.perf_counter(), utc()
    before = scene_state(bpy, IfcStore, model, tool)
    live = live_inventory(bpy, model, tool)
    records, diagnostics = match_inventory(expected, live)
    out = ROOT / "outputs/design/analysis_request_live" / (
        "live_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_") + uuid.uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    (out / "meshes").mkdir()
    disk_mtime = datetime.fromtimestamp(SOURCE.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
    disk_matches = before["source_ifc_bytes"] == OWNER_DISK_EVIDENCE["bytes"] and disk_mtime == OWNER_DISK_EVIDENCE["mtime_utc"]
    manifest = {"schema": "b3-live-evaluated-capture/v1", "status": "in_progress",
                "started_utc": started_utc, "ended_utc": None, "binary": bpy.app.binary_path,
                "blender_version": bpy.app.version_string, "source_path": str(SOURCE),
                "source_schema": model.schema, "project_global_ids": [entity.GlobalId for entity in model.by_type("IfcProject")],
                "source_ifc_bytes": before["source_ifc_bytes"],
                "source_ifc_sha256": OWNER_DISK_EVIDENCE["sha256"] if disk_matches else None,
                "source_disk_evidence": OWNER_DISK_EVIDENCE | {"observed_size_mtime_match": disk_matches},
                "source_to_m": calculate_unit_scale(model), "world_units": "m", "blender_world_to_m": scale,
                "source_units": [{"unit_type": unit.UnitType, "name": getattr(unit, "Name", None),
                                  "prefix": getattr(unit, "Prefix", None)}
                                 for project in model.by_type("IfcProject") for unit in project.UnitsInContext.Units
                                 if getattr(unit, "UnitType", None) == "LENGTHUNIT"],
                "world_transform_policy": "evaluated_matrix_world_once_then_scene_units; no_second_IFC_scale",
                "frozen_identity_source": file_ref(FROZEN, ROOT),
                "historical_scope": {"reference": frozen["scope"], "origin": "frozen B3 run_001",
                                     "confirmation_date": "2026-10-08", "current_reconfirmation": False,
                                     "geometry_parity": "not_checked", "vertical_extent": "unknown"},
                "live_inventory": live, "live_counts": dict(Counter(item["type"] for item in live if item["in_scene"])),
                **diagnostics, "state_before": before, "state_after": None,
                "scene_preserved": None, "batches": [], "capture_errors": [],
                "invariant_limit": "names/links/transforms/data counts only; same-count coordinate edits and untracked IFC edits not detected",
                "native_IFC_geometry_parity": "not_checked", "solid_validity": "not_qualified",
                "purpose": "fresh live source capture only; historical S3; B3 OPEN"}
    _CAPTURE = {"bpy": bpy, "tool": tool, "store": IfcStore, "model": model,
                "metres_per_blender_unit": scale, "out": out, "manifest": manifest,
                "records": records, "diagnostics": diagnostics, "started_clock": started_clock}
    checkpoint(_CAPTURE)
    return progress(_CAPTURE)


def capture_next_batch(max_objects=5):
    """Capture at most this many pending identities and automatically finalize."""
    if not isinstance(max_objects, int) or isinstance(max_objects, bool) or max_objects < 1:
        raise ValueError("max_objects must be a positive integer")
    if _CAPTURE is None:
        raise RuntimeError("call begin_capture() first")
    session, manifest = _CAPTURE, _CAPTURE["manifest"]
    if manifest["status"] != "in_progress":
        return progress(session)
    started, batch_utc = time.perf_counter(), utc()
    batch_ids, scene_changed = [], False
    try:
        current_model = session["store"].get_file()
        before = scene_state(session["bpy"], session["store"], current_model, session["tool"])
        if before != manifest["state_before"]:
            manifest["state_after"], scene_changed = before, True
            raise RuntimeError("scene invariants changed before batch")
        depsgraph = session["bpy"].context.evaluated_depsgraph_get()
        for row in [item for item in session["records"] if item["status"] == "pending"][:max_objects]:
            batch_ids.append(row["id"])
            capture_source(session, row, depsgraph)
        after = scene_state(session["bpy"], session["store"], session["store"].get_file(), session["tool"])
        manifest.update(state_after=after, scene_preserved=after == manifest["state_before"])
        if not manifest["scene_preserved"]:
            scene_changed = True
            raise RuntimeError("scene invariants changed during batch")
        if not any(row["status"] == "pending" for row in session["records"]):
            failures = any(row["status"] not in {"extracted", "semantic_nonmass"} or row.get("quality", {}).get("error")
                           for row in session["records"])
            manifest.update(status="complete_with_failures" if failures else "complete", ended_utc=utc())
    except Exception as exc:
        manifest.update(status="aborted_scene_changed" if scene_changed else "aborted_capture_failed",
                        ended_utc=utc(), scene_preserved=False if scene_changed else None)
        manifest["capture_errors"].append(f"{type(exc).__name__}: {exc}")
        # Pending identities remain visible in an aborted run, never silently omitted.
    manifest["batches"].append({"started_utc": batch_utc, "ended_utc": utc(), "ids": batch_ids,
                                "elapsed_seconds": time.perf_counter() - started})
    checkpoint(session)
    return progress(session)

