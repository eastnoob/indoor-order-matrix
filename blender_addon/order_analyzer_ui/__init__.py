"""Installable Blender 5.2 Analysis workbench entry point."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
from types import SimpleNamespace
import sys
import math
import json
from datetime import datetime, timezone
import uuid

bl_info = {
    "name": "Order Analyzer Analysis",
    "author": "order_analyzer",
    "version": (0, 4, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Analysis",
    "category": "3D View",
}

_REGISTERED = False
_REGISTERED_CLASSES: tuple[type, ...] = ()
_TIMER = None
_HANDLERS: list[tuple[object, object]] = []
_RUNTIME_MODULE = None


def _bpy():
    """Load Blender only when registration is explicitly requested."""
    import bpy
    return bpy


def _configured_repo_root(context=None):
    """Resolve the project root automatically, with an optional advanced override."""
    bpy = _bpy()
    context = context or bpy.context
    # Blender registers this package under its installable addon key, while tests may inject the package key.
    addon_key = __name__.rsplit(".", 1)[-1]
    addon = context.preferences.addons.get(addon_key)
    if addon is None:
        addon = context.preferences.addons.get(__package__)
    raw = getattr(getattr(addon, "preferences", None), "repo_root", "")
    candidates = []
    if str(raw).strip():
        candidates.append(Path(str(raw)).expanduser())
    marker = Path(__file__).with_name("repo_root.txt")
    if marker.is_file():
        try:
            candidates.append(Path(marker.read_text(encoding="utf-8").strip()))
        except OSError:
            pass
    # A saved blend normally lives beside the project checkout. Walk only its
    # ancestors so startup stays cheap and never scans a whole drive.
    blend_path = str(getattr(getattr(bpy, "data", None), "filepath", "") or "")
    if blend_path:
        candidates.extend(Path(blend_path).resolve().parents)
    candidates.extend(Path(__file__).resolve().parents)
    candidates.append(Path.cwd())
    seen = set()
    for candidate in candidates:
        try:
            root = candidate.resolve()
        except OSError:
            continue
        if root in seen:
            continue
        seen.add(root)
        if (root / "pixi.toml").is_file():
            return root
    if str(raw).strip():
        raise ValueError("configured Analysis repository root is invalid")
    raise ValueError("Analysis project root could not be found automatically")


def _runtime(context=None):
    """Import the lightweight runtime after the configured repository is available."""
    global _RUNTIME_MODULE
    root = _configured_repo_root(context)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if _RUNTIME_MODULE is None:
        from . import runtime
        _RUNTIME_MODULE = runtime
    return _RUNTIME_MODULE


def _action_runtime(context=None):
    """Load runtime state only when an operator needs the configured project root."""
    runtime = _runtime(context)
    runtime.STATE.observation_hooks_active = True
    return runtime


def _domain_action(kind: str, version_id: str | None = None, *, source_id: str | None = None,
                   storey_ref: str | None = None, support_source_id: str | None = None) -> dict[str, object]:
    """Build one reducer action without creating a second B4 state."""
    action = {"kind": kind}
    if version_id is not None:
        action["candidate_version_id"] = version_id
    if source_id is not None:
        action["domain_source_id"] = source_id
    if storey_ref is not None:
        action["storey_ref"] = storey_ref
    if support_source_id is not None:
        action["support_source_id"] = support_source_id
    return action


def _entity_storey_ref(entity) -> str | None:
    """Read the explicit IfcBuildingStorey relation from one native IFC entity."""
    storeys = []
    for relation in tuple(getattr(entity, "ContainedInStructure", ()) or ()) + tuple(getattr(entity, "Decomposes", ()) or ()):
        container = getattr(relation, "RelatingStructure", None) or getattr(relation, "RelatingObject", None)
        if container is None or not callable(getattr(container, "is_a", None)) or container.is_a() != "IfcBuildingStorey":
            continue
        guid = getattr(container, "GlobalId", None)
        if isinstance(guid, str) and guid.strip():
            storeys.append("ifc-object:" + guid)
    return storeys[0] if len(storeys) == 1 else None


def _selected_wall_refs(scene) -> tuple[str, ...]:
    """Decode the persisted selected-wall scope as one canonical immutable tuple."""
    raw = str(getattr(scene, "om_analysis_selected_wall_refs_json", "") or "").strip()
    if not raw:
        return ()
    try:
        values = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Selected wall scope is not valid JSON") from exc
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise ValueError("Selected wall scope must be a JSON list of IFC object references")
    refs = tuple(sorted(values))
    if (len(refs) != len(set(refs))
            or any(not ref.startswith("ifc-object:") or not ref.removeprefix("ifc-object:").strip()
                   for ref in refs)):
        raise ValueError("Selected wall scope contains invalid or duplicate IFC object references")
    return refs


def _set_selected_wall_refs(scene, refs=()) -> tuple[str, ...]:
    """Persist selected-wall identities in deterministic JSON for reopen and refresh."""
    canonical = tuple(sorted(str(item) for item in refs))
    if (len(canonical) != len(set(canonical))
            or any(not ref.startswith("ifc-object:") or not ref.removeprefix("ifc-object:").strip()
                   for ref in canonical)):
        raise ValueError("Selected wall scope contains invalid or duplicate IFC object references")
    scene.om_analysis_selected_wall_refs_json = json.dumps(list(canonical), separators=(",", ":")) if canonical else ""
    return canonical


def _selected_native_wall_refs(context) -> tuple[str, ...]:
    """Resolve current Blender selection to unique IfcWall identities in the chosen storey."""
    scene = context.scene
    storey_ref = str(getattr(scene, "om_analysis_storey_ref", "") or "").strip()
    if getattr(scene, "om_analysis_datum_mode", "storey") == "slab":
        storey_ref = _space_datum(scene)["storey_ref"]
    if not storey_ref:
        raise ValueError("Select a building storey before analyzing selected walls")
    objects = tuple(getattr(context, "selected_objects", ()) or ())
    if not objects:
        raise ValueError("Select one or more IfcWall objects")
    try:
        import bonsai.tool as tool
    except ImportError as exc:
        raise ValueError("Bonsai IFC selection is unavailable") from exc
    refs = []
    for obj in objects:
        entity = tool.Ifc.get_entity(obj)
        is_wall = callable(getattr(entity, "is_a", None)) and bool(entity.is_a("IfcWall"))
        guid = getattr(entity, "GlobalId", None) if is_wall else None
        if not isinstance(guid, str) or not guid.strip():
            raise ValueError("Every selected object must resolve uniquely to an IfcWall")
        entity_storey = _entity_storey_ref(entity)
        if entity_storey is not None and entity_storey != storey_ref:
            raise ValueError("Selected IfcWall does not match the explicit storey")
        refs.append("ifc-object:" + guid)
    if len(refs) != len(set(refs)):
        raise ValueError("Selected objects resolve to duplicate IfcWall identities")
    return tuple(sorted(refs))


def _selected_authored_binding(context) -> dict[str, str]:
    """Return exact identity facts for the explicitly selected native IfcSpace."""
    scene = getattr(context, "scene", None)
    support_source_id = str(getattr(scene, "om_analysis_support_source_id", "") or "")
    active_object = getattr(context, "active_object", None)
    if active_object is None:
        return {"support_source_id": support_source_id} if support_source_id else {}
    try:
        import bonsai.tool as bonsai_tool
        entity = bonsai_tool.Ifc.get_entity(active_object)
    except Exception:
        entity = None
    is_space = callable(getattr(entity, "is_a", None)) and entity.is_a() == "IfcSpace"
    source_id = getattr(entity, "GlobalId", None) if is_space else None
    if not isinstance(source_id, str) or not source_id.strip():
        return {"support_source_id": support_source_id} if support_source_id else {}
    storey_ref = _entity_storey_ref(entity) or ""
    payload = {"domain_source_id": source_id, "storey_ref": storey_ref}
    if support_source_id:
        payload["support_source_id"] = support_source_id
    return payload


def _native_space_candidates(context) -> tuple[dict[str, object], ...]:
    """List native Space metadata without validating topology or projecting meshes."""
    try:
        import bonsai.tool as tool
        model = tool.Ifc.get()
        if model is None:
            return ()
        rows = []
        for entity in model.by_type("IfcSpace"):
            guid = getattr(entity, "GlobalId", None)
            if not isinstance(guid, str) or not guid.strip():
                continue
            obj = tool.Ifc.get_object(entity)
            mesh = getattr(obj, "data", None) if getattr(obj, "type", None) == "MESH" else None
            mesh_present = mesh is not None and len(getattr(mesh, "vertices", ())) > 0
            represented = getattr(entity, "Representation", None) is not None
            hidden = bool(getattr(obj, "hide_viewport", False))
            storey = _entity_storey_ref(entity)
            status = ("missing_storey" if not storey else "missing_geometry" if not (represented and mesh_present)
                      else "hidden" if hidden else "available")
            rows.append({"domain_source_id": guid, "name": str(getattr(entity, "Name", None) or guid),
                         "storey_ref": storey, "hide_viewport": hidden,
                         "has_representation": represented, "mesh_present": mesh_present,
                         "metadata_status": status, "geometry_validation": "pending"})
        return tuple(rows)
    except (ImportError, AttributeError, RuntimeError, ReferenceError):
        return ()


def _space_identity_from_guid(context, source_id: str, *, storey_ref: str) -> dict[str, str]:
    """Check explicit native identity and cheap geometry presence, leaving topology to capture."""
    if not isinstance(source_id, str) or not source_id.strip() or not isinstance(storey_ref, str) or not storey_ref.strip():
        raise ValueError("Use selected IfcSpace requires an explicit source and storey")
    try:
        import bonsai.tool as tool
        model = tool.Ifc.get()
        entity = model.by_guid(source_id) if model is not None else None
    except (ImportError, AttributeError, RuntimeError) as exc:
        raise ValueError("IfcSpace source not found in the current IFC") from exc
    if entity is None or getattr(entity, "GlobalId", None) != source_id:
        raise ValueError("IfcSpace source not found in the current IFC")
    if not callable(getattr(entity, "is_a", None)) or entity.is_a() != "IfcSpace":
        raise ValueError("Selected source is not an IfcSpace")
    if _entity_storey_ref(entity) != storey_ref:
        raise ValueError("Selected IfcSpace does not match the explicit storey")
    obj = tool.Ifc.get_object(entity)
    projects = model.by_type("IfcProject")
    if len(projects) != 1 or not getattr(projects[0], "GlobalId", None):
        raise ValueError("Selected IfcSpace requires one active native project")
    linked = tool.Ifc.get_entity(obj) if obj is not None else None
    if linked is None or linked.id() != entity.id() or linked.GlobalId != source_id:
        raise ValueError("Selected IfcSpace native object/entity link is inconsistent")
    import bpy
    objects = [item for item in bpy.data.objects
               if (item_entity := tool.Ifc.get_entity(item)) is not None and item_entity.id() == entity.id()]
    if len(objects) != 1 or objects[0] is not obj:
        raise ValueError("Selected IfcSpace requires one unique native object link")
    mesh = getattr(obj, "data", None) if getattr(obj, "type", None) == "MESH" else None
    if getattr(entity, "Representation", None) is None or mesh is None or not len(getattr(mesh, "vertices", ())):
        raise ValueError("Selected IfcSpace has no native geometry; use Bonsai to provide its representation")
    return {"domain_source_id": source_id, "storey_ref": storey_ref}


def _space_adopt_payload(context, *, source_id: str, storey_ref: str) -> dict[str, object]:
    """Build a fresh authored-domain request without active or retained identity fallback."""
    identity = _space_identity_from_guid(context, source_id, storey_ref=storey_ref)
    scene = context.scene
    payload = {"kind": "domain_session", "context": _space_context_payload(scene, storey_ref=storey_ref),
               "prior": None, "action": None, **identity}
    # Support consent belongs to its floor, so an explicit cross-floor choice cannot inherit it.
    if getattr(scene, "om_analysis_storey_ref", "") == storey_ref:
        support = getattr(scene, "om_analysis_support_source_id", "")
        if support:
            payload["support_source_id"] = support
    return payload


def _space_context_payload(scene, *, storey_ref):
    """Use the reviewed camera frame for an existing Space without requiring B4 or extrusion inputs."""
    from adapters.bonsai_live import StructuralContext
    return StructuralContext.from_plane(_analysis_plane(scene), storey_ref=storey_ref).to_dict()


def _clear_space_selection(scene, *, clear_storey=False):
    """Forget transient source choices without removing persisted Regions or results."""
    scene.om_analysis_space_source_id = ""
    scene.om_analysis_support_source_id = ""
    scene.om_analysis_selected_version_id = ""
    _set_selected_wall_refs(scene)
    if clear_storey:
        scene.om_analysis_storey_ref = ""


def _storey_input_update(scene, context):
    """Clear floor-bound choices and consent when a storey property changes."""
    _clear_space_selection(scene)
    try:
        _runtime(context).invalidate_domain_session("analysis storey changed")
    except ValueError:
        pass


def _clear_missing_space_selection(context, runtime=None) -> bool:
    """Clear a selected Space only when the live IFC explicitly reports it missing."""
    scene = getattr(context, "scene", None)
    source_id = str(getattr(scene, "om_analysis_space_source_id", "") or "")
    if not source_id:
        return False
    try:
        tool = sys.modules.get("bonsai.tool")
        if tool is None:
            import bonsai.tool as tool
        model = tool.Ifc.get()
        if model is None:
            return False
        entity = model.by_guid(source_id)
    except Exception:
        return False
    if entity is not None and getattr(entity, "GlobalId", None) == source_id:
        return False
    _clear_space_selection(scene, clear_storey=True)
    invalidate = getattr(runtime, "invalidate_domain_session", None)
    if callable(invalidate):
        invalidate("selected IfcSpace was removed")
    return True


def _retained_authored_binding(domain, scene) -> dict[str, str]:
    """Extract exact authored/support identities from a retained Domain session."""
    if not isinstance(domain, Mapping):
        return {}
    authored = domain.get("authored_domain")
    payload = {}
    if isinstance(authored, Mapping) and authored.get("source_id"):
        payload["domain_source_id"] = str(authored["source_id"])
        provenance = authored.get("provenance")
        if isinstance(provenance, Mapping) and provenance.get("level_ref"):
            payload["storey_ref"] = str(provenance["level_ref"])
    support = domain.get("support_binding")
    if isinstance(support, Mapping) and support.get("source_object_id"):
        payload["support_source_id"] = str(support["source_object_id"])
    if "storey_ref" not in payload:
        storey_ref = str(getattr(scene, "om_analysis_storey_ref", "") or "")
        if storey_ref:
            payload["storey_ref"] = storey_ref
    if "support_source_id" not in payload:
        support_source_id = str(getattr(scene, "om_analysis_support_source_id", "") or "")
        if support_source_id:
            payload["support_source_id"] = support_source_id
    return payload


def _apply_region_identity(scene, record: Mapping[str, object]) -> None:
    """Keep visible storey/support selectors aligned with the chosen persisted row."""
    scene.om_analysis_storey_ref = str(record.get("storey_ref") or "")
    scene.om_analysis_support_source_id = str(record.get("support_source_id") or "")
    _set_selected_wall_refs(scene, record.get("selected_wall_refs") or ())


def _scene_token(context) -> str:
    """Return a persisted per-scene identity used to bind one region Text."""
    scene = context.scene
    key = "om_analysis_scene_token"
    getter = getattr(scene, "get", None)
    token = getter(key) if callable(getter) else getattr(scene, key, None)
    if isinstance(token, str) and token.strip():
        return token
    token = str(uuid.uuid4())
    try:
        scene[key] = token
    except (TypeError, AttributeError, KeyError):
        # Blender scenes support custom properties; this fallback keeps pure
        # test doubles usable without reintroducing pointer-based persistence.
        try:
            setattr(scene, key, token)
        except Exception:
            pass
    return token


def _restore_region_overlay(runtime, bpy_module) -> None:
    """Restore persisted region lines into the GPU cache without changing analysis state."""
    from . import region_overlay
    # Blender exposes a restricted context while an addon is being enabled from
    # startup; defer restoration until a real scene context is available.
    try:
        context = getattr(bpy_module, "context", None)
        scene = getattr(context, "scene", None)
    except (AttributeError, RuntimeError):
        return
    if scene is None:
        return
    manifest = runtime.find_region_manifest(
        scene_token=_scene_token(SimpleNamespace(scene=scene)), bpy_module=bpy_module)
    manifest = manifest or {}
    region_overlay.set_records(
        manifest.get("records", ()), selected_id=manifest.get("active_region_id"))


def _candidate_rings(candidate):
    """Extract a polygon shell and holes from the service candidate payload."""
    outline = candidate.get("outline")
    if not outline:
        raise ValueError("candidate has no closed outline")
    if isinstance(outline, Mapping):
        coordinates = outline.get("coordinates", ())
        if outline.get("type") == "Polygon":
            return coordinates[0], coordinates[1:]
        if outline.get("type") == "MultiPolygon" and coordinates:
            return coordinates[0][0], coordinates[0][1:]
    if isinstance(outline, (tuple, list)):
        return outline[0], outline[1:]
    raise ValueError("candidate outline is not polygon geometry")


def _native_scope_candidates(context):
    """Return cheap native Storey and same-storey IfcSlab choices for the UI."""
    try:
        import bonsai.tool as tool
        model = tool.Ifc.get()
    except Exception:
        return (), ()
    if model is None or not callable(getattr(model, "by_type", None)):
        return (), ()
    storeys = []
    for entity in tuple(model.by_type("IfcBuildingStorey") or ()):
        guid = getattr(entity, "GlobalId", None)
        if not isinstance(guid, str) or not guid.strip():
            continue
        name = getattr(entity, "LongName", None) or getattr(entity, "Name", None) or guid
        storeys.append(("ifc-object:" + guid, str(name), entity))
    selected = str(getattr(getattr(context, "scene", None), "om_analysis_storey_ref", "") or "")
    supports = [("", "No support", None)]
    selected_matches = [row for row in storeys if row[0] == selected]
    if len(selected_matches) != 1:
        return tuple((ref, label) for ref, label, _ in storeys), tuple((ref, label) for ref, label, _ in supports)
    for slab in tuple(model.by_type("IfcSlab") or ()):
        guid = getattr(slab, "GlobalId", None)
        if not isinstance(guid, str) or not guid.strip():
            continue
        if _entity_storey_ref(slab) != selected:
            continue
        name = getattr(slab, "Name", None) or getattr(slab, "LongName", None) or guid
        supports.append((guid, str(name), slab))
    return tuple((ref, label) for ref, label, _ in storeys), tuple((ref, label) for ref, label, _ in supports)


def _draw_storey_selector(layout, scene, storeys=None):
    """Render named native storey choices through the existing validated selector operator."""
    if storeys is None:
        storeys, _supports = _native_scope_candidates(SimpleNamespace(scene=scene))
    if storeys:
        layout.label(text="Storey")
        for ref, label in storeys:
            row = layout.row(align=True)
            row.label(text=label)
            op = row.operator(
                "om_analysis.select_storey",
                text="Selected" if ref == getattr(scene, "om_analysis_storey_ref", "") else "Use")
            op.value = ref
    else:
        layout.label(text="Storey: no native building storeys found", icon="ERROR")
    selected = str(getattr(scene, "om_analysis_storey_ref", "") or "")
    selected_label = next((label for ref, label in storeys if ref == selected), None)
    if selected_label:
        layout.label(text=f"Selected storey: {selected_label}")
    return tuple(storeys)


def _domain_xy_bounds(domain, domain_geometries=()):
    """Return min/max plane-local XY coordinates from confirmed domain evidence."""
    points = []
    outline = domain.get("outline") if isinstance(domain, Mapping) else None
    if isinstance(outline, Mapping):
        outline = outline.get("coordinates")
    def collect(value):
        if isinstance(value, (tuple, list)):
            if len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
                points.append((float(value[0]), float(value[1])))
            else:
                for item in value:
                    collect(item)
    collect(outline)
    for geometry in domain_geometries or ():
        vertices = geometry.get("vertices", ()) if isinstance(geometry, Mapping) else getattr(geometry, "vertices", ())
        collect(vertices)
    if not points:
        return None
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def _grid_coverage(scene, domain, domain_geometries=(), *, plane=None):
    """Cover world-domain bounds in the chosen horizontal plane's sampling coordinates."""
    spacing = float(scene.om_analysis_grid_spacing)
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError("grid spacing must be positive")
    bounds = _domain_xy_bounds(domain, domain_geometries)
    if bounds is None:
        raise ValueError("confirmed domain geometry bounds are unavailable; refresh and confirm the domain again")
    min_x, min_y, max_x, max_y = bounds
    if plane is not None:
        # Sampling lives in the native camera frame; world XY bounds alone miss translated/rotated planes.
        corners = [(world_x - plane.origin[0], world_y - plane.origin[1], -plane.origin[2])
                   for world_x in (min_x, max_x) for world_y in (min_y, max_y)]
        local = [tuple(sum(value * axis for value, axis in zip(corner, basis)) for basis in plane.basis[:2])
                 for corner in corners]
        min_x, max_x = min(point[0] for point in local), max(point[0] for point in local)
        min_y, max_y = min(point[1] for point in local), max(point[1] for point in local)
    ix0, iy0 = math.floor(min_x / spacing), math.floor(min_y / spacing)
    ix1, iy1 = math.ceil(max_x / spacing), math.ceil(max_y / spacing)
    return (ix0 * spacing, iy0 * spacing), max(1, iy1 - iy0), max(1, ix1 - ix0)


def _create_space_prerequisite_error(context):
    """Validate cheap native Bonsai prerequisites before invoking its operator."""
    try:
        import bonsai.tool as tool
    except Exception:
        return None
    root = getattr(tool, "Root", None)
    model = getattr(tool, "Model", None)
    sync_error = _sync_bonsai_default_container(context, tool=tool)
    if sync_error:
        return sync_error
    default_container = (root.get_default_container() if callable(getattr(root, "get_default_container", None)) else None)
    if default_container is None:
        return "Set a Bonsai default container/storey before creating an IfcSpace"
    props = model.get_model_props() if callable(getattr(model, "get_model_props", None)) else None
    try:
        rl3 = float(getattr(props, "rl3")) if props is not None else float("nan")
    except (TypeError, ValueError):
        rl3 = float("nan")
    if not math.isfinite(rl3):
        return "Set the Bonsai relative level (RL) before creating an IfcSpace"
    scene = getattr(context, "scene", None)
    selected_storey = str(getattr(scene, "om_analysis_storey_ref", "") or "")
    container_guid = getattr(default_container, "GlobalId", None)
    if selected_storey and container_guid and selected_storey != "ifc-object:" + str(container_guid):
        return "Selected storey does not match Bonsai's default container"
    active = getattr(context, "active_object", None)
    if active is not None:
        entity = None
        try:
            entity = tool.Ifc.get_entity(active)
        except Exception:
            pass
        if entity is None or not callable(getattr(entity, "is_a", None)) or entity.is_a() != "IfcSpace":
            return "Deselect the active non-space object or place the cursor before creating an IfcSpace"
    return None


def _sync_bonsai_default_container(context, *, tool=None):
    """Align Bonsai's native Space container with the Analyzer's selected storey."""
    try:
        tool = tool or __import__("bonsai.tool", fromlist=["tool"])
    except Exception:
        return None
    storey_ref = str(getattr(getattr(context, "scene", None), "om_analysis_storey_ref", "") or "")
    if not storey_ref:
        return None
    guid = storey_ref.removeprefix("ifc-object:")
    if not guid:
        return "Selected storey has no IFC GlobalId"
    ifc = getattr(tool, "Ifc", None)
    if not callable(getattr(ifc, "get", None)):
        return None
    model = ifc.get()
    if model is None or not callable(getattr(model, "by_guid", None)):
        return None
    try:
        entity = model.by_guid(guid)
    except Exception:
        entity = None
    if entity is None or not callable(getattr(entity, "is_a", None)) or entity.is_a() != "IfcBuildingStorey":
        return "Selected storey is not a loaded IfcBuildingStorey"
    spatial = getattr(tool, "Spatial", None)
    setter = getattr(spatial, "set_default_container", None)
    if not callable(setter):
        return "Bonsai Spatial.set_default_container is unavailable"
    try:
        setter(entity)
    except Exception as exc:
        return f"Could not set Bonsai default container: {exc}"
    return None




def _space_datum(scene):
    """Resolve exactly the user's selected base without granting support-occupancy permission."""
    import bonsai.tool as tool
    from adapters.bonsai_space_authoring import resolve_slab_datum, resolve_storey_datum

    if getattr(scene, "om_analysis_datum_mode", "storey") == "slab":
        return resolve_slab_datum(tool.Ifc.get(), getattr(scene, "om_analysis_datum_slab_ref", ""))
    return resolve_storey_datum(tool.Ifc.get(), getattr(scene, "om_analysis_storey_ref", ""))


def _space_height(scene, storey_ref):
    """Resolve the chosen authored or manual height without combining the two sources."""
    import bonsai.tool as tool
    from adapters.bonsai_space_authoring import resolve_height

    return resolve_height(tool.Ifc.get(), storey_ref, mode=scene.om_analysis_height_mode,
        manual_value=scene.om_analysis_manual_height, manual_unit=scene.om_analysis_height_unit)


def _authoring_form(scene):
    """Retain explicit form choices so changes cannot reuse a previously analyzed candidate."""
    defaults = {"datum_mode": "storey", "datum_slab_ref": "", "storey_ref": "",
                "height_mode": "authored", "manual_height": 0., "height_unit": "m",
                "b4_cut_offset": 1.5, "query_kind": "whole_height_projection"}
    return {key: getattr(scene, "om_analysis_" + key, value) for key, value in defaults.items()}


def _domain_storey_ref(scene):
    """Use the slab's derived storey only for B4; authored Space adoption stays independent."""
    if (not getattr(scene, "om_analysis_space_source_id", "")
            and getattr(scene, "om_analysis_datum_mode", "storey") == "slab"):
        return _space_datum(scene)["storey_ref"]
    return str(getattr(scene, "om_analysis_storey_ref", "") or "")


def _structural_context_payload(scene, *, selected_wall_refs=None):
    """Build the fixed B4 structural frame from the user-visible plane settings."""
    root = _configured_repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from adapters.bonsai_live import StructuralContext
    from features.scene_contract import AnalysisPlane
    storey_ref = str(getattr(scene, "om_analysis_storey_ref", "") or "")
    wall_refs = _selected_wall_refs(scene) if selected_wall_refs is None else tuple(selected_wall_refs)
    if getattr(scene, "om_analysis_datum_mode", "storey") == "slab":
        datum = _space_datum(scene)
        storey_ref, datum_z_m = datum["storey_ref"], datum["datum_z_m"]
    else:
        datum_z_m = _selected_storey_datum_z_m(storey_ref) if storey_ref else 0.0
    cut_offset = float(getattr(scene, "om_analysis_b4_cut_offset", 1.5))
    if not math.isfinite(cut_offset):
        raise ValueError("B4 cut offset must be finite")
    plane = AnalysisPlane(name="Analysis plane", identity=scene.om_analysis_plane_uuid or "world_xy",
                          revision=int(getattr(scene, "om_analysis_plane_revision", 1)),
                          origin=(0.0, 0.0, 0.0), basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    return StructuralContext.from_plane(plane, storey_ref=storey_ref or None,
        datum_z_m=datum_z_m, cut_z_m=datum_z_m + cut_offset, b4_parameters={
        "tolerance_mm2": float(scene.om_b4_tolerance_mm2),
        "contact_distance_m": 1e-6, "aperture_area_budget_m2": 1e-6},
        selected_wall_refs=wall_refs).to_dict()


def _require_current_selected_wall_context(scene, retained_context) -> None:
    """Refuse Start when current structural settings differ from retained selected-wall consent."""
    if not isinstance(retained_context, Mapping) or not retained_context.get("selected_wall_refs"):
        return
    root = _configured_repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from adapters.bonsai_live import StructuralContext
    retained = StructuralContext(**dict(retained_context))
    current = StructuralContext(**_structural_context_payload(scene))
    if current.structural_frame_key != retained.structural_frame_key:
        raise ValueError("Selected-wall settings changed; refresh and confirm the Domain again before Start")


def _selected_storey_datum_z_m(storey_ref):
    """Use the shared native datum resolver, including transformed horizontal placement checks."""
    import bonsai.tool as tool
    from adapters.bonsai_space_authoring import resolve_storey_datum

    return resolve_storey_datum(tool.Ifc.get(), storey_ref)["datum_z_m"]


def _stored_camera_plane(scene):
    """Read the thin persisted observation without treating it as current native truth."""
    from adapters.blender_analysis_result_wire import validate_compositions
    from features.scene_contract import AnalysisPlane
    encoded = getattr(scene, "om_analysis_plane_binding_json", "")
    if not encoded:
        raise ValueError("create or adopt a native drawing camera first")
    record = json.loads(encoded)
    if not isinstance(record, Mapping):
        raise ValueError("stored drawing camera observation is invalid")
    validate_compositions({"plane_binding": record}, {
        "project_source_identity": {"project_global_id": record.get("project_global_id")},
        "plane_uuid": record.get("plane_uuid"), "plane_revision": record.get("plane_revision")})
    plane = AnalysisPlane(name="Analysis plane", identity=record["plane_uuid"],
        revision=record["plane_revision"], origin=record["origin"], basis=record["basis"])
    return record, plane


def _analysis_plane(scene):
    """Require reviewed native identity and pose before constructing an analysis request."""
    from adapters.bonsai_analysis_plane import camera_composition, refresh_camera_plane, resolve_camera_binding
    record, plane = _stored_camera_plane(scene)
    if not getattr(scene, "om_analysis_plane_reviewed", False):
        raise ValueError("refresh the native drawing camera to review this session")
    binding = resolve_camera_binding(project_global_id=record["project_global_id"], camera_guid=record["camera_guid"])
    updated = refresh_camera_plane(plane, binding, query_kind=scene.om_analysis_query_kind,
                                   project_global_id=record["project_global_id"])
    if updated is not plane or camera_composition(binding, plane) != record:
        raise ValueError("native drawing changed; refresh the plane and confirm the Domain again")
    return plane


def _set_camera_plane(context, action):
    """Handle explicit native creation, adoption or refresh while preserving result history."""
    from adapters.bonsai_analysis_plane import (camera_composition, create_native_drawing, plane_from_camera,
                                              read_camera_binding, refresh_camera_plane, resolve_camera_binding)
    scene = context.scene
    runtime = _action_runtime(context)
    if runtime.STATE.job is not None:
        raise ValueError("finish or cancel the analysis before changing its camera")
    if action == "refresh":
        record, plane = _stored_camera_plane(scene)
        binding = resolve_camera_binding(project_global_id=record["project_global_id"], camera_guid=record["camera_guid"])
        plane = refresh_camera_plane(plane, binding, query_kind=scene.om_analysis_query_kind,
                                     project_global_id=record["project_global_id"])
    elif action in {"adopt", "new"}:
        camera = (create_native_drawing(storey_ref=getattr(scene, "om_analysis_storey_ref", "") or None)
                  if action == "new" else context.active_object)
        binding = read_camera_binding(camera, role="geometry_author")
        previous = _stored_camera_plane(scene) if getattr(scene, "om_analysis_plane_binding_json", "") else None
        if (previous and previous[0]["camera_guid"] == binding.provenance["source_ifc_global_id"]
                and previous[0]["project_global_id"] == binding.provenance["project_global_id"]):
            plane = refresh_camera_plane(previous[1], binding, query_kind=scene.om_analysis_query_kind,
                                         project_global_id=previous[0]["project_global_id"])
        else:
            plane = plane_from_camera(binding, name="Analysis plane", query_kind=scene.om_analysis_query_kind)
    else:
        raise ValueError("unsupported camera action")
    scene.om_analysis_plane_binding_json = json.dumps(camera_composition(binding, plane), sort_keys=True)
    scene.om_analysis_plane_uuid = plane.identity
    scene.om_analysis_plane_revision = plane.revision
    scene.om_analysis_plane_origin_z = plane.origin[2]
    scene.om_analysis_plane_reviewed = True
    scene.om_analysis_selected_version_id = ""
    runtime.invalidate_domain_session("native drawing camera explicitly " + action)


def _make_analysis_request(scene, domain, domain_geometries=()):
    """Build the existing request using plane origin Z and confirmed XY coverage."""
    from features.analysis_requests import AnalysisRequest, GeometryQuery, GridSampling
    from features.scene_contract import AnalysisDomain
    plane = _analysis_plane(scene)
    kind = scene.om_analysis_query_kind
    if kind == "ground_to_analysis_plane_band":
        # GeometryQuery height bands use analysis-plane local Z, so world ground
        # is below the horizontal plane by exactly the plane elevation.
        if plane.origin[2] <= 0.0:
            raise ValueError("ground-to-analysis-plane band requires a positive analysis plane elevation")
        query = GeometryQuery(kind="finite_height_band", height_band=(-plane.origin[2], 0.0))
    else:
        query = GeometryQuery(kind=kind, world_z_m=plane.origin[2] if kind == "exact_world_xy_section" else None)
    origin, n_rows, n_cols = _grid_coverage(scene, domain, domain_geometries, plane=plane)
    return AnalysisRequest(request_id=str(uuid.uuid4()), plane=plane, domain=AnalysisDomain.from_dict(domain),
                           sampling=GridSampling(origin=origin, spacing=float(scene.om_analysis_grid_spacing),
                                                  n_rows=n_rows, n_cols=n_cols),
                           geometry_query=query, operation="free_space")


def _request_binding_payload(domain):
    """Pass through only binding records already produced by the retained session."""
    return {"support_binding": domain.get("support_binding"),
            "legacy_bindings": domain.get("legacy_bindings", ())}


def _overlay_updates_only(runtime, depsgraph):
    """Recognize only depsgraph updates for the current tagged overlay object or mesh."""
    try:
        overlay_object = runtime.STATE.overlay_object
    except ReferenceError:
        overlay_object = None
    result = runtime.STATE.current_result
    updates = tuple(getattr(depsgraph, "updates", ()))
    if overlay_object is None or result is None or not updates:
        return False
    document = getattr(result, "document", {})
    result_id = document.get("result_id") if isinstance(document, Mapping) else None
    try:
        object_name = getattr(overlay_object, "name", None)
        mesh = getattr(overlay_object, "data", None)
        mesh_name = getattr(mesh, "name", None)
    except ReferenceError:
        object_name = mesh_name = None
    overlay_seen = False
    for update in updates:
        item = getattr(update, "id", None)
        try:
            name = getattr(item, "name", None)
            get = getattr(item, "get", None)
            owned = callable(get) and get("om_analysis_owner") == "order_analyzer" \
                and get("om_analysis_role") == "overlay" \
                and get("om_analysis_result_id") == result_id
        except ReferenceError:
            return False
        if owned or name in {object_name, mesh_name}:
            overlay_seen = True
        elif name != mesh_name:
            identifier = getattr(getattr(item, "bl_rna", None), "identifier", type(item).__name__)
            if identifier not in {"Scene", "Collection"}:
                return False
        else:
            overlay_seen = True
    return overlay_seen


def _analysis_input_update(_scene, context):
    """Invalidate current analysis when a request or Domain input changes."""
    try:
        _runtime(context).invalidate_domain_session("analysis input changed")
    except ValueError:
        pass


def _depsgraph_updates_are_neutral(depsgraph):
    """Return true only for non-semantic UI/runtime datablock updates."""
    updates = tuple(getattr(depsgraph, "updates", ()))
    if not updates:
        # Blender can emit an empty depsgraph callback while evaluating a timer
        # or viewport redraw; it carries no source mutation to invalidate.
        return True
    neutral_identifiers = {"WindowManager", "Screen", "Workspace", "Scene", "Collection", "ViewLayer"}
    for update in updates:
        item = getattr(update, "id", None)
        identifier = getattr(getattr(item, "bl_rna", None), "identifier", None)
        # Region manifests are addon-owned display history. Blender reports the
        # Text write after the operator returns; treating it as source geometry
        # would invalidate the recheck job that wrote the same manifest.
        owned_region_manifest = (identifier == "Text" and callable(getattr(item, "get", None))
                                 and item.get("om_analysis_owner") == "order_analyzer"
                                 and item.get("om_analysis_role") == "region_list")
        if identifier not in neutral_identifiers and not owned_region_manifest:
            return False
    return True


def _draw_candidate_list(layout, scene, runtime, result, context=None):
    """Share cached candidate controls and GPU previews across both launch panels."""
    from . import candidate_preview, region_overlay
    container = layout.box()
    container.label(text="Candidate regions")
    visible_candidates = []
    for candidate in result.get("candidates", ()):
        if getattr(scene, "om_analysis_storey_ref", "") and candidate.get("storey_ref") not in {None, scene.om_analysis_storey_ref}:
            continue
        visible_candidates.append(candidate)
        row = container.row(align=True)
        selected = candidate_preview.candidate_id(candidate) == getattr(scene, "om_analysis_selected_version_id", "")
        name = candidate.get("name") or candidate.get("id", "candidate")
        op = row.operator("om_analysis.b4_select", text=str(name), icon="RADIOBUT_ON" if selected else "RADIOBUT_OFF")
        op.version_id = candidate.get("version_id", "")
        op.domain_source_id = candidate.get("source_id", "") or ""
        op.storey_ref = candidate.get("storey_ref", "") or ""
        op.support_source_id = getattr(scene, "om_analysis_support_source_id", "")
        eye = row.operator("om_analysis.candidate_eye", text="", icon="HIDE_OFF" if candidate_preview.candidate_id(candidate) in candidate_preview.eye_ids() else "HIDE_ON")
        eye.version_id = candidate_preview.candidate_id(candidate)
        area = candidate.get("area_m2")
        area_text = f"{area:.2f}" if isinstance(area, (int, float)) else str(area)
        row.label(text=f"{area_text} m²")
        if candidate.get("domain_kind") == "authored_ifcspace":
            row.label(text="IfcSpace", icon="HOME")
        if candidate.get("reason"):
            container.label(text=str(candidate["reason"]), icon="ERROR")
    region_overlay.set_candidate_previews(candidate_preview.eye_enabled(visible_candidates, candidate_preview.eye_ids()))
    if context is not None:
        region_overlay.install(context)
        region_overlay.tag_redraw(context)
    freshness = getattr(runtime.STATE, "freshness", None)
    current_status = result.get("current", {}).get("status")
    if freshness in {"stale", "recheck"} or current_status in {"stale", "recheck"}:
        layout.label(text="Candidate cache stale; re-analyze", icon="ERROR")
    if any(candidate_preview.candidate_id(item) == getattr(scene, "om_analysis_selected_version_id", "")
           for item in visible_candidates):
        layout.operator("om_analysis.b4_confirm", text="Confirm analysis domain", icon="CHECKMARK")
    if not visible_candidates:
        if not str(getattr(scene, "om_analysis_storey_ref", "") or "").strip():
            # Scope is required before an empty result can be interpreted.
            container.label(text="Select a storey/support scope before analyzing", icon="INFO")
        elif current_status in {"failed", "error"}:
            container.label(text="Analysis failed; fix the error above and analyze again", icon="ERROR")
        else:
            container.label(text="Analysis completed with no candidate regions", icon="INFO")
    return visible_candidates


def _draw_space_authoring(layout, scene, runtime, context=None):
    """Render the complete user driven Space candidate workflow in one panel."""
    state = getattr(runtime, "STATE", None)
    if state is None:
        layout.label(text="Space analysis runtime is unavailable", icon="ERROR")
        return
    layout.label(text="Space base")
    layout.prop(scene, "om_analysis_datum_mode", text="Base source")
    storeys, supports = _native_scope_candidates(SimpleNamespace(scene=scene))
    if getattr(scene, "om_analysis_datum_mode", "storey") == "slab":
        layout.prop(scene, "om_analysis_datum_slab_ref", text="Slab reference")
        layout.operator("om_analysis.select_datum_slab", text="Use viewport selected slab")
    else:
        _draw_storey_selector(layout, scene, storeys)
    layout.prop(scene, "om_analysis_b4_cut_offset", text="B4 cut above base (m)")
    layout.prop(scene, "om_analysis_height_mode", text="Extrusion height source")
    if getattr(scene, "om_analysis_height_mode", "authored") == "manual":
        layout.prop(scene, "om_analysis_manual_height", text="Height")
        layout.prop(scene, "om_analysis_height_unit", text="Input unit")
    try:
        datum = _space_datum(scene)
        layout.label(text=f"Base: {datum['datum_z_m']:.6g} m; storey {datum['storey_ref']}")
        height = _space_height(scene, datum["storey_ref"])
        layout.label(text=f"Height: {height['height_m']:.6g} m ({height['unit_source']})")
    except (ValueError, ImportError, AttributeError) as error:
        layout.label(text=str(error)[:180], icon="INFO")
    separator = getattr(layout, "separator", None)
    if callable(separator):
        separator()
    layout.label(text="Analyze — generate B4 candidate regions")
    layout.operator("om_analysis.analyze_spaces", text="Analyze spaces", icon="PLAY")
    layout.operator("om_analysis.analyze_selected_walls", text="Analyze selected walls")
    layout.prop(scene, "om_b4_tolerance_mm2", text="Aperture tolerance (mm²)")
    layout.label(text="Doors/windows assumed closed; leaf states remain unknown")
    _draw_space_job_status(layout, runtime)
    result = state.domain_session
    if result is None:
        layout.label(text="No cached candidates. Choose a floor, then analyze.", icon="INFO")
        return
    layout.label(text=f"{len(result.get('candidates', ())) } interiors; {result.get('source_count', 0)} source meshes; {result.get('geometry_count', 0)} geometries")
    visible_candidates = _draw_candidate_list(layout, scene, runtime, result, context)
    if visible_candidates:
        separator = getattr(layout, "separator", None)
        if callable(separator):
            separator()
        layout.label(text="Candidate selection")
        selected_id = getattr(scene, "om_analysis_selected_version_id", "")
        selected = next((item for item in visible_candidates
                         if item.get("version_id") == selected_id), None)
        if selected is not None and selected.get("domain_kind") != "authored_ifcspace":
            layout.label(text="Space authoring — explicit confirmation required", icon="INFO")
            layout.operator("om_analysis.create_space_from_candidate", text="Confirm and generate Space", icon="HOME")
        elif selected is not None:
            layout.label(text="Native Space selected; confirm its analysis domain", icon="INFO")
        else:
            layout.label(text="Select one candidate to enable Space creation", icon="INFO")
    if result.get("support_status") == "unbound":
        layout.label(text="Unbound floor remains physical occupancy", icon="INFO")
    elif result.get("support_status") == "selected":
        layout.label(text="Supporting floor explicitly selected", icon="CHECKMARK")
    current, attempt = result.get("current", {}), result.get("attempt", {})
    layout.label(text="Regions / results")
    layout.label(text=f"Current: {current.get('status', 'unknown')}")
    layout.label(text=f"Last attempt: {attempt.get('status', 'none')} {attempt.get('reason') or ''}")
    layout.label(text=f"Ignored tiny residuals: {result.get('ignored_tiny_residual_count', 0)}")
    significant = sum(bool(item.get("significant_residual")) for item in result.get("apertures", ()))
    layout.label(text=f"Significant aperture residuals: {significant}")


def _draw_domain(layout, scene, runtime, context=None):
    """Render independent B4 diagnostics with local progress and cached candidates."""
    layout.label(text="Analyze — B4 candidate regions")
    _draw_storey_selector(layout, scene)
    if str(getattr(scene, "om_analysis_storey_ref", "") or "").strip():
        layout.label(text="World XY; cut 1.5 m above selected storey")
    else:
        layout.label(text="World XY; datum 0 m; cut 1.5 m")
    layout.label(text="Doors/windows assumed closed")
    layout.prop(scene, "om_b4_tolerance_mm2", text="Residual tolerance (mm²)")
    row_method = getattr(layout, "row", None)
    row = row_method(align=True) if callable(row_method) else layout
    row.operator("om_analysis.b4_refresh", text="Run B4 diagnostic", icon="FILE_REFRESH")
    row.operator("om_analysis.analyze_selected_walls", text="Analyze selected walls", icon="RESTRICT_SELECT_OFF")
    selected_refs = _selected_wall_refs(scene)
    if selected_refs:
        layout.label(text=f"Selected-wall scope: {len(selected_refs)} walls", icon="CHECKMARK")
    _draw_space_job_status(layout, runtime)
    result = runtime.STATE.domain_session
    if result is None:
        layout.label(text="No B4 diagnostic cached", icon="INFO")
        return
    _draw_candidate_list(layout, scene, runtime, result, context)
    current, attempt = result.get("current", {}), result.get("attempt", {})
    layout.label(text=f"Current: {current.get('status', 'unknown')}")
    layout.label(text=f"Last attempt: {attempt.get('status', 'none')} {attempt.get('reason') or ''}")
    layout.label(text=f"Ignored tiny residuals: {result.get('ignored_tiny_residual_count', 0)}")
    significant = sum(bool(item.get("significant_residual")) for item in result.get("apertures", ()))
    layout.label(text=f"Significant aperture residuals: {significant}")


def _draw_plane(layout, scene, runtime):
    """Render projection-plane setup and explicit authored IfcSpace selection."""
    layout.operator("om_analysis.setup_plane", text="New drawing camera", icon="OUTLINER_OB_CAMERA")
    layout.operator("om_analysis.adopt_camera", text="Use selected drawing camera")
    layout.operator("om_analysis.refresh_camera", text="Refresh camera plane")
    try:
        record, plane = _stored_camera_plane(scene)
        layout.label(text=f"Drawing: {record['camera_guid']}")
        layout.label(text=f"World Z: {plane.origin[2]:.4f} m · Revision {plane.revision}")
        _analysis_plane(scene)
    except (ValueError, KeyError, TypeError) as error:
        layout.label(text=str(error), icon="INFO")
    layout.prop(scene, "om_analysis_space_source_id", text="Selected IfcSpace GUID")
    layout.prop(scene, "om_analysis_storey_ref", text="Selected storey GUID")
    layout.operator("om_analysis.use_selected_ifcspace", text="Use viewport selected IfcSpace")
    space_candidates = _native_space_candidates(SimpleNamespace(scene=scene))
    if space_candidates:
        layout.label(text="IfcSpace source")
        for candidate in space_candidates:
            row = layout.row(align=True)
            row.label(text=str(candidate.get("name") or candidate.get("domain_source_id")))
            op = row.operator("om_analysis.use_selected_ifcspace", text="Use selected IfcSpace")
            op.source_id = candidate.get("domain_source_id", "")
            op.storey_ref = candidate.get("storey_ref", "") or ""
            if candidate.get("storey_ref"):
                row.label(text=f"Storey: {candidate['storey_ref']}")
    else:
        layout.label(text="IfcSpace source: no valid native spaces found", icon="INFO")


def _draw_free_space(layout, scene, runtime):
    """Render free-space controls and lifecycle without exposing implementation details."""
    try:
        plane = _analysis_plane(scene)
        layout.label(text=f"Plane: {plane.name}; revision {plane.revision}; Z {plane.origin[2]:g} m")
    except ValueError as exc:
        layout.label(text=str(exc), icon="ERROR")
    layout.label(text="Space: " + (str(getattr(scene, "om_analysis_space_source_id", "")) or "No native Space selected"))
    result = getattr(runtime.STATE, "current_result", None)
    groups = result.document.get("binding", {}).get("authored_groups", ()) if result is not None else ()
    if not groups:
        layout.label(text="Authored group targets: none")
    for group in groups:
        layout.label(text=f"Group {group['id']}: {', '.join(group['member_refs'])}")
    layout.label(text="All physical obstacles remain in occupancy")
    layout.prop(scene, "om_analysis_query_kind", text="Query")
    layout.prop(scene, "om_analysis_grid_spacing", text="Grid spacing")
    domain = runtime.STATE.domain_session
    if isinstance(domain, Mapping) and domain.get("current", {}).get("status") == "active":
        candidate = next((item for item in domain.get("candidates", ())
                          if item.get("version_id") == getattr(scene, "om_analysis_selected_version_id", "")), None)
        if candidate is not None:
            try:
                coverage = _grid_coverage(scene, candidate, domain.get("domain_geometries", ()), plane=_analysis_plane(scene))
            except ValueError as exc:
                layout.label(text=str(exc), icon="ERROR")
            else:
                layout.label(text=f"Confirmed coverage: origin {coverage[0]}; {coverage[2]} x {coverage[1]} cells")
        else:
            layout.label(text="Confirm a domain to derive grid coverage", icon="INFO")
    else:
        layout.label(text="Rows and columns are derived from the confirmed domain", icon="INFO")
    layout.prop(scene, "om_analysis_inspect_row", text="Inspect row")
    layout.prop(scene, "om_analysis_inspect_column", text="Inspect column")
    row = layout.row(align=True)
    row.operator("om_analysis.start", icon="PLAY")
    row.operator("om_analysis.cancel", icon="CANCEL")
    layout.label(text=f"Stage: {runtime.STATE.lifecycle}; freshness: {runtime.STATE.freshness}")


def _draw_results(layout, scene, runtime):
    """Render terminal diagnostics and read-only result actions."""
    if getattr(runtime.STATE, "current_result", None) is not None:
        layout.operator("om_analysis.inspect", icon="VIEWZOOM")
        if runtime.STATE.inspection is not None:
            layout.label(text=str(runtime.STATE.inspection))
        layout.operator("om_analysis.save_copy", icon="FILE_TICK")


def _draw_regions(layout, scene, runtime, context=None):
    """Render the single Space authoring flow followed by saved Region history."""
    if not hasattr(layout, "prop"):
        return
    try:
        from . import regions
        token = _scene_token(context if context is not None else SimpleNamespace(scene=scene))
        manifest = runtime.find_region_manifest(scene_token=token)
    except Exception:
        manifest = None
    records = (manifest or {}).get("records", ()) if isinstance(manifest, Mapping) else ()
    if context is not None:
        from . import region_overlay
        region_overlay.set_records(records, selected_id=getattr(scene, "om_analysis_active_region_id", None))
        if records:
            region_overlay.install(context)
    # Restore history before authoring rebuilds the independent eye-preview cache.
    _draw_space_authoring(layout, scene, runtime, context)
    separator = getattr(layout, "separator", None)
    if callable(separator):
        separator()
    layout.label(text="Saved analysis Regions")
    layout.label(text=f"Saved regions: {len(records)}")
    for record in records:
        row = layout.row(align=True)
        select = row.operator("om_analysis.region_select", text=str(record.get("name", record.get("region_id", "region"))))
        select.region_id = record.get("region_id", "")
        recheck = row.operator("om_analysis.region_recheck", text="Recheck")
        recheck.region_id = record.get("region_id", "")
        remove = row.operator("om_analysis.region_remove", text="Remove")
        remove.region_id = record.get("region_id", "")
        row.label(text=str(record.get("status", "historical")))
    layout.operator("om_analysis.region_capture", icon="CHECKMARK")


def _draw_space_job_status(layout, runtime):
    """Show the shared Space-analysis job truthfully while it is running or terminal."""
    state = getattr(runtime, "STATE", None)
    if state is None:
        return
    job = getattr(state, "job", None) or getattr(state, "last_job", None)
    if job is None:
        if getattr(state, "freshness", None) in {"stale", "recheck"}:
            layout.label(text="Model changed; refresh the analysis", icon="ERROR")
        else:
            layout.label(text="No space analysis has been run")
        return
    stage = getattr(job, "stage", "unknown")
    lifecycle = getattr(job, "lifecycle", "unknown")
    error = getattr(job, "error", None)
    progress = getattr(job, "metrics", {}).get("progress") if hasattr(job, "metrics") else None
    suffix = f" ({progress:.0%})" if isinstance(progress, (int, float)) else ""
    if lifecycle in {"capturing", "running", "cancelling"}:
        text = f"Analyzing; please wait · {stage}{suffix}"
        progress_factor = {"observe_start": 0.05, "capture": 0.20, "finalize": 0.35,
                           "observe_after_capture": 0.45, "request_normalize": 0.55,
                           "request_digest": 0.62, "write": 0.68, "process": 0.80,
                           "read": 0.90, "observe_after": 0.96}.get(stage, 0.1)
        progress_draw = getattr(layout, "progress", None)
        if callable(progress_draw):
            progress_draw(text=text, factor=progress_factor, type="BAR")
        layout.operator("om_analysis.cancel", text="Cancel analysis", icon="CANCEL")
    elif lifecycle == "complete" and getattr(state, "domain_session", None) is not None:
        text = "Analysis complete; candidates cached"
    else:
        text = f"Space analysis: {lifecycle} · {stage}{suffix}"
    layout.label(text=text, icon="ERROR" if error else "INFO")
    if error:
        layout.label(text=str(error)[:240], icon="ERROR")


def _panel_classes(bpy):
    """Create the five sibling Analyzer panels lazily so imports stay Blender-free."""
    class _AnalyzerPanel(bpy.types.Panel):
        """Provide shared native panel metadata for the Analyzer workbench."""
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "Analyzer"
        bl_options = {"DEFAULT_CLOSED"}

        def _runtime_or_error(self, context):
            """Resolve the one shared runtime and report configuration errors."""
            try:
                return _runtime(context)
            except ValueError as exc:
                self.layout.label(text=str(exc), icon="ERROR")
                return None

    class OM_ANALYSIS_PT_plane(_AnalyzerPanel):
        """Show projection-plane and authored IfcSpace controls."""
        bl_idname = "OM_ANALYSIS_PT_plane"
        bl_label = "Analysis Plane"

        def draw(self, context):
            """Draw plane and explicit Space source controls."""
            runtime = self._runtime_or_error(context)
            if runtime is not None:
                _draw_plane(self.layout, context.scene, runtime)

    class OM_ANALYSIS_PT_region(_AnalyzerPanel):
        """Show persisted analysis Region records and actions."""
        bl_idname = "OM_ANALYSIS_PT_region"
        bl_label = "Space Candidates / Regions"

        def draw(self, context):
            """Draw Region selection, recheck, removal, and capture actions."""
            runtime = self._runtime_or_error(context)
            if runtime is not None:
                _draw_regions(self.layout, context.scene, runtime, context)

    class OM_ANALYSIS_PT_free_space(_AnalyzerPanel):
        """Show free-space execution controls."""
        bl_idname = "OM_ANALYSIS_PT_free_space"
        bl_label = "Free Space"

        def draw(self, context):
            """Draw free-space request and lifecycle controls."""
            runtime = self._runtime_or_error(context)
            if runtime is not None:
                _draw_free_space(self.layout, context.scene, runtime)

    class OM_ANALYSIS_PT_b4(_AnalyzerPanel):
        """Show the independent legacy B4 diagnostic service."""
        bl_idname = "OM_ANALYSIS_PT_b4"
        bl_label = "B4 Structural Diagnostic"

        def draw(self, context):
            """Draw B4 refresh, selection, confirmation, and diagnostics."""
            runtime = self._runtime_or_error(context)
            if runtime is not None:
                _draw_domain(self.layout, context.scene, runtime, context)

    class OM_ANALYSIS_PT_results(_AnalyzerPanel):
        """Show terminal runtime status and read-only result actions."""
        bl_idname = "OM_ANALYSIS_PT_results"
        bl_label = "Analysis Results"

        def draw(self, context):
            """Draw result diagnostics before read-only inspection actions."""
            runtime = self._runtime_or_error(context)
            if runtime is None:
                return
            last_job = runtime.STATE.last_job
            if runtime.STATE.job is None and last_job is not None and last_job.error:
                self.layout.label(text=last_job.error, icon="ERROR")
            _draw_results(self.layout, context.scene, runtime)

    return (OM_ANALYSIS_PT_plane, OM_ANALYSIS_PT_region, OM_ANALYSIS_PT_free_space,
            OM_ANALYSIS_PT_b4, OM_ANALYSIS_PT_results)


def _operator_classes(bpy):
    """Create small native operators that delegate all analysis to runtime/session."""
    class Refresh(bpy.types.Operator):
        """Submit a B4 diagnostic refresh through the shared runtime."""
        bl_idname = "om_analysis.b4_refresh"
        bl_label = "Refresh"

        def execute(self, context):
            """Start an independent Domain job using the retained reducer prior."""
            try:
                runtime = _action_runtime(context)
                runtime.start_job(repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                                  payload={"kind": "domain_session", "context": _structural_context_payload(context.scene),
                                           "prior": runtime.STATE.domain_session, "action": None})
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class AnalyzeSpaces(bpy.types.Operator):
        """Run the formal Space candidate analysis through the existing B4/domain service."""
        bl_idname = "om_analysis.analyze_spaces"
        bl_label = "Analyze spaces"

        def execute(self, context):
            """Start a scoped candidate job without creating IFC or replacing the B4 entry."""
            try:
                runtime = _action_runtime(context)
                scene = context.scene
                if (getattr(scene, "om_analysis_datum_mode", "storey") != "slab"
                        and not str(getattr(scene, "om_analysis_storey_ref", "") or "").strip()):
                    self.report({"WARNING"}, "Select a building storey before analyzing spaces")
                    return {"CANCELLED"}
                if getattr(scene, "om_analysis_datum_mode", "storey") != "slab":
                    _selected_storey_datum_z_m(scene.om_analysis_storey_ref)
                _set_selected_wall_refs(scene)
                scene.om_analysis_space_source_id = ""
                scene.om_analysis_selected_version_id = ""
                runtime._flush_native_view_layer()
                runtime.invalidate_domain_session("whole-storey analysis requested")
                structural = _structural_context_payload(scene)
                runtime.start_job(
                    repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                    payload={"kind": "domain_session", "entrypoint": "analyze_spaces",
                             "job_binding": {"authoring_parameters": _authoring_form(scene)},
                             "context": structural,
                             "prior": None, "action": None,
                             "storey_ref": structural.get("storey_ref") or getattr(scene, "om_analysis_storey_ref", "") or None,
                             "support_source_id": getattr(scene, "om_analysis_support_source_id", "") or None})
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class AnalyzeSelectedWalls(bpy.types.Operator):
        """Freeze selected native IfcWall identities and run local B4 inference."""
        bl_idname = "om_analysis.analyze_selected_walls"
        bl_label = "Analyze selected walls"

        def execute(self, context):
            """Persist one canonical selected-wall scope before capture begins."""
            try:
                refs = _selected_native_wall_refs(context)
                scene = context.scene
                _set_selected_wall_refs(scene, refs)
                scene.om_analysis_space_source_id = ""
                scene.om_analysis_selected_version_id = ""
                runtime = _action_runtime(context)
                runtime._flush_native_view_layer()
                runtime.invalidate_domain_session("selected-wall analysis requested")
                structural = _structural_context_payload(scene)
                runtime.start_job(
                    repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                    payload={"kind": "domain_session", "entrypoint": "analyze_selected_walls",
                             "job_binding": {"authoring_parameters": _authoring_form(scene)},
                             "context": structural, "prior": None, "action": None,
                             "storey_ref": structural.get("storey_ref") or getattr(scene, "om_analysis_storey_ref", "") or None,
                             "support_source_id": getattr(scene, "om_analysis_support_source_id", "") or None})
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class Select(bpy.types.Operator):
        """Select one B4 candidate without granting domain consent."""
        bl_idname = "om_analysis.b4_select"
        bl_label = "Select"
        version_id: bpy.props.StringProperty()
        domain_source_id: bpy.props.StringProperty(options={"SKIP_SAVE"})
        storey_ref: bpy.props.StringProperty(options={"SKIP_SAVE"})
        support_source_id: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Update the shared selected id without submitting a job or confirming it."""
            try:
                selected_storey = _domain_storey_ref(context.scene)
            except ValueError as error:
                self.report({"ERROR"}, str(error)[:240])
                return {"CANCELLED"}
            candidate_storey = str(getattr(self, "storey_ref", "") or "")
            if candidate_storey and candidate_storey != selected_storey:
                self.report({"ERROR"}, "Candidate storey does not match the selected storey")
                return {"CANCELLED"}
            context.scene.om_analysis_selected_version_id = self.version_id
            return {"FINISHED"}

    class CandidateEye(bpy.types.Operator):
        """Toggle one transient candidate GPU preview without changing selection."""
        bl_idname = "om_analysis.candidate_eye"
        bl_label = "Toggle candidate preview"
        version_id: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Rebuild only the GPU candidate cache and request a redraw."""
            from . import candidate_preview, region_overlay
            domain = _runtime(context).STATE.domain_session or {}
            candidate = next((item for item in domain.get("candidates", ())
                              if candidate_preview.candidate_id(item) == self.version_id), None)
            if candidate is not None:
                candidate_preview.toggle_eye(candidate)
                region_overlay.set_candidate_previews(candidate_preview.eye_enabled(
                    domain.get("candidates", ()), candidate_preview.eye_ids()))
                region_overlay.install(context)
                region_overlay.tag_redraw(context)
            return {"FINISHED"}

    class Confirm(bpy.types.Operator):
        """Submit explicit B4 confirmation through the shared session."""
        bl_idname = "om_analysis.b4_confirm"
        bl_label = "Confirm"

        def execute(self, context):
            """Leave confirmation authority with the existing reducer service."""
            try:
                runtime = _action_runtime(context)
                selected_storey = _domain_storey_ref(context.scene)
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            result = runtime.STATE.domain_session
            selected = getattr(context.scene, "om_analysis_selected_version_id", "")
            candidate = next((item for item in (result or {}).get("candidates", ())
                              if item.get("version_id") == selected), None)
            if candidate is None:
                self.report({"ERROR"}, "Select a current interior first")
                return {"CANCELLED"}
            if candidate.get("storey_ref") and candidate["storey_ref"] != selected_storey:
                self.report({"ERROR"}, "Candidate storey does not match the selected storey")
                return {"CANCELLED"}
            provenance = result["provenance"]
            action = {"kind": "confirm", "candidate_version_id": selected,
                      "action_id": str(uuid.uuid4()), "actor": "Blender user",
                      "time": datetime.now(timezone.utc).isoformat(), "reason": "explicit UI confirmation",
                      "expected_session_revision": result["session_revision"],
                      "expected_source_revision": provenance["source_revision"],
                      "expected_plane_identity": provenance["frame_id"],
                      "expected_request_identity": provenance["request_id"],
                      "expected_candidate_identity": candidate["identity"],
                      "acknowledged_conflict_ids": []}
            if candidate.get("source_id"):
                action["domain_source_id"] = candidate["source_id"]
                action["storey_ref"] = candidate.get("storey_ref") or getattr(context.scene, "om_analysis_storey_ref", "")
            support_source_id = getattr(context.scene, "om_analysis_support_source_id", "")
            if support_source_id:
                action["support_source_id"] = support_source_id
            identity = {key: value for key, value in {
                "domain_source_id": candidate.get("source_id"),
                "storey_ref": candidate.get("storey_ref") or getattr(context.scene, "om_analysis_storey_ref", ""),
                "support_source_id": support_source_id,
            }.items() if value}
            try:
                runtime = _action_runtime(context)
                frozen_refs = tuple(candidate.get("selected_wall_refs") or
                                    (result.get("selected_wall_scope") or {}).get("selected_wall_refs") or ())
                structural_context = (_space_context_payload(context.scene, storey_ref=candidate["storey_ref"])
                                      if candidate.get("domain_kind") == "authored_ifcspace" else
                                      _structural_context_payload(context.scene, selected_wall_refs=frozen_refs)
                                      if frozen_refs else _structural_context_payload(context.scene))
                runtime.start_job(repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                                  payload={"kind": "domain_session", "context": structural_context,
                                           "prior": result, "action": action,
                                           "job_binding": ({"space_binding": result["space_binding"]}
                                                           if result.get("space_binding") else {}), **identity})
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class UseSelectedIfcSpace(bpy.types.Operator):
        """Adopt one explicitly selected native IfcSpace as the Domain source."""
        bl_idname = "om_analysis.use_selected_ifcspace"
        bl_label = "Use selected IfcSpace"
        source_id: bpy.props.StringProperty(options={"SKIP_SAVE"})
        storey_ref: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Start a fresh Domain request bound only to the supplied Space and storey."""
            try:
                source_id, storey_ref = self.source_id, self.storey_ref
                if not source_id:
                    selected = _selected_authored_binding(context)
                    source_id, storey_ref = selected.get("domain_source_id", ""), selected.get("storey_ref", "")
                identity = _space_identity_from_guid(context, source_id, storey_ref=storey_ref)
                scene = context.scene
                context_payload = _space_context_payload(scene, storey_ref=storey_ref)
                scene.om_analysis_storey_ref = storey_ref
                scene.om_analysis_space_source_id = source_id
                scene.om_analysis_support_source_id = ""
                scene.om_analysis_selected_version_id = ""
                _set_selected_wall_refs(scene)
                runtime = _action_runtime(context)
                # Settle these native Scene writes before freezing the first job epoch.
                runtime._flush_native_view_layer()
                runtime.invalidate_domain_session("analysis Space selection changed")
                runtime.start_job(repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                                  payload={"kind": "domain_session", "context": context_payload,
                                           "prior": None, "action": None, **identity})
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class CreateSpace(bpy.types.Operator):
        """Keep the former entrypoint on the same exact-candidate authoring contract."""
        bl_idname = "om_analysis.create_space"
        bl_label = "Create IfcSpace from candidate"

        def execute(self, context):
            """Delegate to the explicit reviewed-candidate operation, including its refusal paths."""
            return bpy.ops.om_analysis.create_space_from_candidate()

    class CreateSpaceFromCandidate(bpy.types.Operator):
        """Create one exact reviewed polygon and offer its native identity for domain adoption."""
        bl_idname = "om_analysis.create_space_from_candidate"
        bl_label = "Confirm and generate Space"
        bl_options = {"REGISTER", "UNDO"}

        def execute(self, context):
            """Freeze current inputs, use the narrow native writer, then recapture through US2."""
            created = None
            try:
                from adapters.bonsai_space_authoring import freeze_candidate, create_native_space
                runtime = _action_runtime(context)
                scene = context.scene
                if runtime.STATE.job is not None or runtime.STATE.freshness != "current":
                    raise ValueError("Finish or refresh the analysis before creating a Space")
                _analysis_plane(scene)
                result = runtime.STATE.current_result
                if result is None or result.document.get("kind") != "domain_session":
                    raise ValueError("Select a candidate from the current B4 analysis")
                if result.document["binding"].get("authoring_parameters") != _authoring_form(scene):
                    raise ValueError("Space inputs changed; analyze again before creating a Space")
                current_context = _structural_context_payload(scene)
                from adapters.blender_analysis_capture import plain
                if plain(current_context) != plain(runtime.STATE.domain_context):
                    raise ValueError("B4 settings changed; analyze again before creating a Space")
                datum = _space_datum(scene)
                height = _space_height(scene, datum["storey_ref"])
                sketch = freeze_candidate(result.document, scene.om_analysis_selected_version_id,
                    datum=datum, height=height, plane_binding=_stored_camera_plane(scene)[0],
                    query_key=scene.om_analysis_query_kind)
                runtime._flush_native_view_layer()
                created = create_native_space(sketch)
                _set_selected_wall_refs(scene)
                scene.om_analysis_storey_ref = datum["storey_ref"]
                scene.om_analysis_space_source_id = created["guid"]
                scene.om_analysis_selected_version_id = ""
                runtime.invalidate_domain_session("native Space created; explicit domain confirmation required")
                runtime._flush_native_view_layer()
                runtime.start_job(repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                    payload={"kind": "domain_session", "context": _space_context_payload(scene, storey_ref=datum["storey_ref"]),
                             "domain_source_id": created["guid"], "storey_ref": datum["storey_ref"],
                             "job_binding": {"space_binding": created["space_binding"]}, "prior": None, "action": None})
                return {"FINISHED"}
            except Exception as error:
                if created is not None:
                    self.report({"WARNING"}, "Native Space created; select it and use IfcSpace to recheck: " + str(error)[:160])
                    return {"FINISHED"}
                self.report({"ERROR"}, str(error)[:240])
                return {"CANCELLED"}

    class SelectDatumSlab(bpy.types.Operator):
        """Choose the viewport slab only as a Space base, without excluding any occupancy."""
        bl_idname = "om_analysis.select_datum_slab"
        bl_label = "Use selected slab base"

        def execute(self, context):
            """Validate exact native identity and unique horizontal upper surface before selection."""
            try:
                import bonsai.tool as tool
                from adapters.bonsai_space_authoring import resolve_slab_datum
                entity = tool.Ifc.get_entity(context.active_object) if context.active_object else None
                if entity is None or not entity.is_a("IfcSlab"):
                    raise ValueError("Select one native IfcSlab")
                ref = "ifc-object:" + entity.GlobalId
                resolve_slab_datum(tool.Ifc.get(), ref)
                context.scene.om_analysis_datum_slab_ref = ref
                context.scene.om_analysis_datum_mode = "slab"
            except Exception as error:
                self.report({"ERROR"}, str(error)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class SelectStorey(bpy.types.Operator):
        """Set the canonical storey identity from a native UI choice."""
        bl_idname = "om_analysis.select_storey"
        bl_label = "Use storey"
        value: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Persist only the canonical IfcBuildingStorey identity."""
            context.scene.om_analysis_storey_ref = self.value
            context.scene.om_analysis_support_source_id = ""
            try:
                import bonsai.tool as tool
                error = _sync_bonsai_default_container(context, tool=tool)
                if error:
                    self.report({"ERROR"}, error)
                    return {"CANCELLED"}
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            try:
                _action_runtime(context).invalidate_domain_session("analysis storey changed")
            except Exception:
                pass
            return {"FINISHED"}

    class SelectSupport(bpy.types.Operator):
        """Set or clear the canonical same-storey floor support identity."""
        bl_idname = "om_analysis.select_support"
        bl_label = "Use supporting floor"
        value: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Persist the native slab GlobalId, with an explicit no-support choice."""
            context.scene.om_analysis_support_source_id = self.value
            try:
                _action_runtime(context).invalidate_domain_session("analysis support changed")
            except Exception:
                pass
            return {"FINISHED"}

    class SetupPlane(bpy.types.Operator):
        """Create and adopt a real native drawing camera through Bonsai."""
        bl_idname = "om_analysis.setup_plane"
        bl_label = "New drawing camera"
        bl_options = {"REGISTER", "UNDO"}

        def execute(self, context):
            """Publish the exact native camera only after authoring validation succeeds."""
            try:
                _set_camera_plane(context, "new")
            except Exception as error:
                self.report({"ERROR"}, str(error)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class AdoptCamera(bpy.types.Operator):
        """Explicitly adopt the selected native drawing without changing IFC facts."""
        bl_idname = "om_analysis.adopt_camera"
        bl_label = "Use selected drawing camera"

        def execute(self, context):
            """Use the selected object only after native drawing qualification."""
            try:
                _set_camera_plane(context, "adopt")
            except Exception as error:
                self.report({"ERROR"}, str(error)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class RefreshCamera(bpy.types.Operator):
        """Re-read an adopted camera and explicitly invalidate dependent consent."""
        bl_idname = "om_analysis.refresh_camera"
        bl_label = "Refresh camera plane"

        def execute(self, context):
            """Resolve the original project/GUID rather than the current selection."""
            try:
                _set_camera_plane(context, "refresh")
            except Exception as error:
                self.report({"ERROR"}, str(error)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class CaptureRegion(bpy.types.Operator):
        """Persist the explicitly confirmed current Domain candidate as a region row."""
        bl_idname = "om_analysis.region_capture"
        bl_label = "Save current region"

        def execute(self, context):
            """Write one region record and refresh only the GPU cache."""
            try:
                runtime = _action_runtime(context)
                result = runtime.STATE.domain_session
                if not isinstance(result, Mapping) or result.get("current", {}).get("status") != "active":
                    raise ValueError("confirm a current Domain before saving a region")
                selected = getattr(context.scene, "om_analysis_selected_version_id", "")
                candidate = next((item for item in result.get("candidates", ()) if item.get("version_id") == selected), None)
                if candidate is None:
                    raise ValueError("select a current Space or Domain candidate first")
                shell, holes = _candidate_rings(candidate)
                from . import regions, region_overlay
                plane = _analysis_plane(context.scene)
                record = regions.build_region_record(
                    region_id=str(candidate.get("source_id") or candidate.get("version_id") or uuid.uuid4().hex),
                    name=str(candidate.get("name") or candidate.get("long_name") or candidate.get("id") or "Region"),
                    storey_ref=candidate.get("storey_ref") or getattr(context.scene, "om_analysis_storey_ref", "") or None,
                    plane_uuid=getattr(context.scene, "om_analysis_plane_uuid", "") or "world_xy",
                    plane_revision=int(getattr(context.scene, "om_analysis_plane_revision", 1)),
                    source_id=candidate.get("source_id"), geometry_refs=candidate.get("geometry_refs", ()),
                    outline=(shell,), holes=holes, status="confirmed",
                    confirmation={"action_id": (result.get("confirmation_binding") or {}).get("action_id")},
                    source_revision=(result.get("provenance") or {}).get("source_revision"),
                    support_source_id=getattr(context.scene, "om_analysis_support_source_id", "") or None,
                    selected_wall_refs=candidate.get("selected_wall_refs") or
                                       (result.get("selected_wall_scope") or {}).get("selected_wall_refs") or (),
                    plane_origin=plane.origin, plane_basis=plane.basis,
                    plane_binding=_stored_camera_plane(context.scene)[0], space_binding=result.get("space_binding"))
                token = _scene_token(context)
                manifest = runtime.find_region_manifest(scene_token=token, bpy_module=bpy) or {"records": ()}
                records, region_id = regions.upsert_record(manifest.get("records", ()), record)
                encoded = regions.encode_manifest(records, active_region_id=region_id,
                                                  storey_ref=getattr(context.scene, "om_analysis_storey_ref", "") or None)
                runtime.embed_region_manifest(encoded, scene_token=token, bpy_module=bpy)
                context.scene.om_analysis_active_region_id = region_id
                region_overlay.set_records(records, selected_id=region_id)
                region_overlay.tag_redraw(context)
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class RegionSelect(bpy.types.Operator):
        """Select one persisted region for display and later recheck."""
        bl_idname = "om_analysis.region_select"
        bl_label = "Select region"
        region_id: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Select only display state; it does not restore Domain consent."""
            context.scene.om_analysis_active_region_id = self.region_id
            try:
                runtime = _action_runtime(context)
                manifest = runtime.find_region_manifest(scene_token=_scene_token(context), bpy_module=bpy)
                record = next((item for item in (manifest or {}).get("records", ())
                               if item.get("region_id") == self.region_id), None)
                if record is not None:
                    _apply_region_identity(context.scene, record)
                runtime.invalidate_domain_session("analysis region selection changed")
            except Exception:
                pass
            try:
                from . import region_overlay
                region_overlay.tag_redraw(context)
            except Exception:
                pass
            return {"FINISHED"}

    class RegionRecheck(bpy.types.Operator):
        """Re-submit one persisted region for explicit live re-confirmation."""
        bl_idname = "om_analysis.region_recheck"
        bl_label = "Recheck region"
        region_id: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Mark history stale and launch a fresh Domain request by exact identity."""
            try:
                runtime = _action_runtime(context)
                from . import regions, region_overlay
                token = _scene_token(context)
                manifest = runtime.find_region_manifest(scene_token=token, bpy_module=bpy)
                if manifest is None:
                    raise ValueError("saved region list is unavailable")
                record = next((item for item in manifest["records"] if item.get("region_id") == self.region_id), None)
                if record is None:
                    raise ValueError("saved region is unavailable")
                storey_ref = record.get("storey_ref")
                selected_refs = tuple(record.get("selected_wall_refs") or ())
                source_id = record.get("source_id")
                if not storey_ref or (not source_id and not selected_refs):
                    raise ValueError("saved region lacks authored Space or selected-wall identity")
                _apply_region_identity(context.scene, record)
                _set_selected_wall_refs(context.scene, selected_refs)
                records = []
                for item in manifest["records"]:
                    item = dict(item)
                    if item.get("region_id") == self.region_id:
                        item["status"] = "recheck"
                    records.append(item)
                encoded = regions.encode_manifest(records, active_region_id=self.region_id,
                                                  storey_ref=manifest.get("storey_ref"))
                runtime.embed_region_manifest(encoded, scene_token=token, bpy_module=bpy)
                region_overlay.set_records(records, selected_id=self.region_id)
                # Blender may defer the Text datablock's depsgraph update until
                # the next capture boundary. Flush this display-only write while
                # no job owns an observation epoch, so Recheck snapshots a
                # stable epoch and source edits remain guarded normally.
                view_layer = getattr(context, "view_layer", None)
                update_view_layer = getattr(view_layer, "update", None)
                if callable(update_view_layer):
                    update_view_layer()
                # A recheck must never inherit a prior confirmation; the
                # persisted row supplies identity, while the new request must
                # return to an unconfirmed candidate state.
                runtime.invalidate_domain_session("analysis region requires recheck")
                identity = {"storey_ref": storey_ref}
                if source_id:
                    identity["domain_source_id"] = source_id
                if source_id and record.get("support_source_id"):
                    identity["support_source_id"] = record["support_source_id"]
                structural_context = (_space_context_payload(context.scene, storey_ref=storey_ref) if source_id else
                                      _structural_context_payload(context.scene, selected_wall_refs=selected_refs)
                                      if selected_refs else _structural_context_payload(context.scene))
                runtime.start_job(repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                                  payload={"kind": "domain_session", "context": structural_context,
                                           "job_binding": ({"space_binding": record["space_binding"]}
                                                           if record.get("space_binding") else {}),
                                           "prior": None, "action": None, **identity})
                region_overlay.tag_redraw(context)
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class RegionRemove(bpy.types.Operator):
        """Remove one persisted region and its rebuildable outline."""
        bl_idname = "om_analysis.region_remove"
        bl_label = "Remove region"
        region_id: bpy.props.StringProperty(options={"SKIP_SAVE"})

        def execute(self, context):
            """Delete only the selected region record; no IFC object is touched."""
            try:
                runtime = _action_runtime(context)
                from . import regions, region_overlay
                token = _scene_token(context)
                manifest = runtime.find_region_manifest(scene_token=token, bpy_module=bpy)
                if manifest is None:
                    raise ValueError("saved region list is unavailable")
                records = regions.remove_record(manifest["records"], self.region_id)
                active = None if manifest.get("active_region_id") == self.region_id else manifest.get("active_region_id")
                encoded = regions.encode_manifest(records, active_region_id=active, storey_ref=manifest.get("storey_ref"))
                runtime.embed_region_manifest(encoded, scene_token=token, bpy_module=bpy)
                region_overlay.set_records(records, selected_id=active)
                runtime.invalidate_domain_session("analysis region removed")
                region_overlay.tag_redraw(context)
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class Start(bpy.types.Operator):
        """Start the retained confirmed-domain free-space job."""
        bl_idname = "om_analysis.start"
        bl_label = "Start"

        def execute(self, context):
            """Use the fixed runtime slot and reject fabricated payload authority."""
            try:
                runtime = _action_runtime(context)
                domain = runtime.STATE.domain_session
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            if not isinstance(domain, Mapping) or domain.get("current", {}).get("status") != "active":
                self.report({"WARNING"}, "Select and confirm a Domain first")
                return {"CANCELLED"}
            try:
                _require_current_selected_wall_context(
                    context.scene, getattr(runtime.STATE, "domain_context", None))
                request = _make_analysis_request(context.scene, domain["analysis_domain"],
                                                 domain.get("domain_geometries", ()))
                bindings = _request_binding_payload(domain)
                runtime.start_job(repo_root=_configured_repo_root(context), bpy_context=context, auto_publish=True,
                                  payload={"kind": "free_space_run", "request": request.to_dict(),
                                           "domain_geometries": domain["domain_geometries"],
                                           "job_binding": {"plane_binding": _stored_camera_plane(context.scene)[0]},
                                           **bindings})
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class ReassignPlane(bpy.types.Operator):
        """Explicitly assign a new UUID when a duplicated plane is detected."""
        bl_idname = "om_analysis.reassign_plane"
        bl_label = "Reassign plane UUID"
        new_uuid: bpy.props.StringProperty()

        def execute(self, context):
            """Preserve old results as historical before changing the plane identity."""
            try:
                runtime = _action_runtime(context)
                runtime.reassign_duplicate_plane_uuid(
                    plane_uuid=context.scene.om_analysis_plane_uuid,
                    new_uuid=self.new_uuid,
                    existing_plane_uuids=tuple(filter(None, str(getattr(context.scene, "om_analysis_plane_uuids", "")).split(","))),
                )
                context.scene.om_analysis_plane_uuid = self.new_uuid
                context.scene.om_analysis_plane_revision = 1
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class Cancel(bpy.types.Operator):
        """Cancel only the addon-owned runtime job."""
        bl_idname = "om_analysis.cancel"
        bl_label = "Cancel"

        def execute(self, context):
            """Cooperatively cancel and let the timer reap the child."""
            try:
                _action_runtime(context).cancel_job()
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class Inspect(bpy.types.Operator):
        """Open the current result's authoritative sample path."""
        bl_idname = "om_analysis.inspect"
        bl_label = "Inspect"

        def execute(self, context):
            """Read one authoritative cell and expose its diagnostic without mutating the result."""
            try:
                runtime = _action_runtime(context)
                result = runtime.STATE.current_result
                if (runtime.STATE.freshness != "current" or result is None
                        or result.document.get("kind") != "free_space_run"):
                    raise ValueError("current free-space result is unavailable")
                from . import overlay
                row = int(context.scene.om_analysis_inspect_row)
                column = int(context.scene.om_analysis_inspect_column)
                diagnostic = overlay.inspect_cell(result, row=row, column=column)
                runtime.STATE.inspection = diagnostic
                context.scene.om_analysis_inspection = str(diagnostic)
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    class SaveCopy(bpy.types.Operator):
        """Save a validated result into a new native blend copy."""
        bl_idname = "om_analysis.save_copy"
        bl_label = "Save Copy"
        filepath: bpy.props.StringProperty(subtype="FILE_PATH")

        def invoke(self, context, event):
            """Choose a new native copy path through Blender's file browser."""
            if not self.filepath:
                source = Path(bpy.data.filepath)
                self.filepath = str(source.with_name(f"{source.stem}-analysis-copy.blend")) if source.name else "analysis-copy.blend"
            context.window_manager.fileselect_add(self)
            return {"RUNNING_MODAL"}

        def execute(self, context):
            """Require an explicit path in the full operator implementation."""
            if not self.filepath:
                self.report({"WARNING"}, "Choose a new Save Copy path")
                return {"CANCELLED"}
            try:
                runtime = _action_runtime(context)
                runtime.save_copy(target=Path(self.filepath), live_path=Path(bpy.data.filepath), bpy_module=bpy)
            except Exception as exc:
                self.report({"ERROR"}, str(exc)[:240])
                return {"CANCELLED"}
            return {"FINISHED"}

    return (Refresh, AnalyzeSpaces, AnalyzeSelectedWalls, Select, CandidateEye, Confirm, UseSelectedIfcSpace, CreateSpace, CreateSpaceFromCandidate, SelectDatumSlab, SelectStorey, SelectSupport, SetupPlane, AdoptCamera, RefreshCamera, CaptureRegion, RegionSelect,
            RegionRecheck, RegionRemove, Start, ReassignPlane, Cancel, Inspect, SaveCopy)


def _preferences_class(bpy):
    """Create the addon preference class holding the explicit repository root."""
    # Blender resolves deferred property annotations against module globals during registration.
    globals()["bpy"] = bpy
    class Preferences(bpy.types.AddonPreferences):
        """Store the explicit repository root used by the addon runtime."""
        bl_idname = __package__
        repo_root: bpy.props.StringProperty(name="Repository root", subtype="DIR_PATH", default="")

        def draw(self, context):
            """Expose an optional advanced override; normal use auto-detects the project."""
            self.layout.label(text="Project root is detected automatically when possible")
            self.layout.prop(self, "repo_root")
    return Preferences


def register() -> None:
    """Register Analyzer sibling panels, operators, timer, and observation handlers."""
    global _REGISTERED, _REGISTERED_CLASSES, _TIMER, _HANDLERS
    if _REGISTERED:
        return
    bpy = _bpy()
    preference_class = _preferences_class(bpy)
    bpy.utils.register_class(preference_class)
    classes = _operator_classes(bpy) + _panel_classes(bpy)
    for cls in classes:
        bpy.utils.register_class(cls)
    _REGISTERED_CLASSES = (preference_class,) + classes
    bpy.types.Scene.om_analysis_domain_expanded = bpy.props.BoolProperty(default=True)
    bpy.types.Scene.om_analysis_regions_expanded = bpy.props.BoolProperty(default=True)
    bpy.types.Scene.om_analysis_free_space_expanded = bpy.props.BoolProperty(default=True)
    bpy.types.Scene.om_b4_tolerance_mm2 = bpy.props.FloatProperty(default=10.0, min=0.0, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_plane_uuid = bpy.props.StringProperty(default="", update=_analysis_input_update)
    bpy.types.Scene.om_analysis_plane_binding_json = bpy.props.StringProperty(default="")
    bpy.types.Scene.om_analysis_plane_reviewed = bpy.props.BoolProperty(default=False, options={"SKIP_SAVE"})
    bpy.types.Scene.om_analysis_query_kind = bpy.props.EnumProperty(items=[
        ("whole_height_projection", "Whole height", ""),
        ("exact_world_xy_section", "Exact world XY section", ""),
        ("ground_to_analysis_plane_band", "Ground to analysis plane", "Finite band from world ground to the analysis plane")],
        default="whole_height_projection", update=_analysis_input_update)
    bpy.types.Scene.om_analysis_plane_origin_z = bpy.props.FloatProperty(default=0.0, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_plane_revision = bpy.props.IntProperty(default=1, min=1, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_plane_uuids = bpy.props.StringProperty(default="")
    bpy.types.Scene.om_analysis_grid_spacing = bpy.props.FloatProperty(default=0.25, min=0.0, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_grid_rows = bpy.props.IntProperty(default=1, min=1, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_grid_columns = bpy.props.IntProperty(default=1, min=1, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_selected_version_id = bpy.props.StringProperty(default="")
    bpy.types.Scene.om_analysis_selected_wall_refs_json = bpy.props.StringProperty(default="")
    bpy.types.Scene.om_analysis_space_source_id = bpy.props.StringProperty(default="")
    bpy.types.Scene.om_analysis_storey_ref = bpy.props.StringProperty(default="", update=_storey_input_update)
    bpy.types.Scene.om_analysis_support_source_id = bpy.props.StringProperty(default="", update=_analysis_input_update)
    bpy.types.Scene.om_analysis_datum_mode = bpy.props.EnumProperty(items=[("storey", "Storey base", ""),
        ("slab", "Selected slab upper surface", "")], default="storey", update=_analysis_input_update)
    bpy.types.Scene.om_analysis_datum_slab_ref = bpy.props.StringProperty(default="", update=_analysis_input_update)
    bpy.types.Scene.om_analysis_b4_cut_offset = bpy.props.FloatProperty(default=1.5, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_height_mode = bpy.props.EnumProperty(items=[("authored", "Authored GrossHeight", ""),
        ("manual", "Manual height", "")], default="authored", update=_analysis_input_update)
    bpy.types.Scene.om_analysis_manual_height = bpy.props.FloatProperty(default=0.0, update=_analysis_input_update)
    bpy.types.Scene.om_analysis_height_unit = bpy.props.EnumProperty(items=[("m", "Metres", ""), ("mm", "Millimetres", "")],
        default="m", update=_analysis_input_update)
    bpy.types.Scene.om_analysis_active_region_id = bpy.props.StringProperty(default="")
    bpy.types.Scene.om_analysis_inspect_row = bpy.props.IntProperty(default=0, min=0)
    bpy.types.Scene.om_analysis_inspect_column = bpy.props.IntProperty(default=0, min=0)
    bpy.types.Scene.om_analysis_inspection = bpy.props.StringProperty(default="")
    def timer():
        """Pump one bounded runtime callback."""
        try:
            _runtime().poll_job()
            screen = getattr(getattr(bpy, "context", None), "screen", None)
            for area in getattr(screen, "areas", ()):
                if callable(getattr(area, "tag_redraw", None)):
                    area.tag_redraw()
        except ValueError:
            # Preferences may be configured after addon registration.
            pass
        return 0.05
    _TIMER = timer
    bpy.app.timers.register(timer, first_interval=0.05, persistent=True)
    def invalidate_load(*_):
        """Invalidate runtime state when a configured file is loaded."""
        try:
            runtime = _runtime()
            # A file load starts a fresh native session; retained Domain consent
            # belongs to the prior file and must not survive this lifecycle edge.
            invalidate_domain = getattr(runtime, "invalidate_domain_session", None)
            if callable(invalidate_domain):
                invalidate_domain("load")
            runtime.invalidate_runtime("load", new_session=True)
            bpy.context.scene.om_analysis_plane_reviewed = False
            _clear_space_selection(bpy.context.scene, clear_storey=True)
            _restore_region_overlay(runtime, bpy)
        except ValueError:
            pass

    def invalidate_undo(*_):
        """Invalidate runtime state when a configured file is undone."""
        try:
            runtime = _runtime()
            bpy.context.scene.om_analysis_plane_reviewed = False
            runtime.invalidate_domain_session("undo")
            runtime.invalidate_runtime("undo", new_session=True)
        except ValueError:
            pass

    def invalidate_scene(*_):
        """Invalidate runtime state after a native scene change."""
        try:
            runtime = _runtime()
            # Capture/evaluated-mesh reads can themselves enqueue depsgraph
            # updates. The owned job's native before/after guards remain the
            # authoritative mutation check, so do not cancel from this hook.
            if runtime.STATE.job is not None:
                return
            depsgraph = _[1] if len(_) > 1 else None
            if _overlay_updates_only(runtime, depsgraph):
                runtime.invalidate_runtime("display_only")
                return
            if _depsgraph_updates_are_neutral(depsgraph):
                return
            _clear_missing_space_selection(bpy.context, runtime)
            if getattr(bpy.context.scene, "om_analysis_plane_reviewed", False):
                try:
                    _analysis_plane(bpy.context.scene)
                except (ValueError, RuntimeError, TypeError):
                    bpy.context.scene.om_analysis_plane_reviewed = False
                    runtime.invalidate_domain_session("native drawing changed")
            runtime.invalidate_runtime("scene changed")
        except ValueError:
            pass

    persistent = getattr(bpy.app.handlers, "persistent", None)
    def _persistent(handler):
        """Keep lifecycle callbacks registered when Blender opens another file."""
        return persistent(handler) if callable(persistent) else handler

    for collection, handler in ((bpy.app.handlers.load_post, _persistent(invalidate_load)),
                                (bpy.app.handlers.undo_post, _persistent(invalidate_undo)),
                                (bpy.app.handlers.depsgraph_update_post, _persistent(invalidate_scene))):
        collection.append(handler)
        _HANDLERS.append((collection, handler))
    try:
        _restore_region_overlay(_runtime(), bpy)
    except ValueError:
        # Preferences may be configured after addon registration.
        pass
    _REGISTERED = True


def unregister() -> None:
    """Cancel and reap owned work before removing addon-owned handlers and classes."""
    global _REGISTERED, _REGISTERED_CLASSES, _TIMER, _HANDLERS
    if not _REGISTERED:
        return
    bpy = _bpy()
    try:
        from . import region_overlay
        region_overlay.uninstall()
    except Exception:
        pass
    try:
        runtime = _runtime()
    except ValueError:
        runtime = None
    if runtime is not None:
        runtime.invalidate_runtime("unregister", new_session=True)
        runtime.reap_owned_job()
    for collection, handler in _HANDLERS:
        if handler in collection:
            collection.remove(handler)
    _HANDLERS.clear()
    if _TIMER is not None and bpy.app.timers.is_registered(_TIMER):
        bpy.app.timers.unregister(_TIMER)
    for name in ("om_analysis_domain_expanded", "om_analysis_regions_expanded", "om_analysis_free_space_expanded", "om_b4_tolerance_mm2",
                 "om_analysis_plane_uuid", "om_analysis_query_kind", "om_analysis_grid_spacing",
                 "om_analysis_plane_origin_z", "om_analysis_plane_revision", "om_analysis_plane_uuids",
                 "om_analysis_plane_binding_json", "om_analysis_plane_reviewed",
                 "om_analysis_grid_rows", "om_analysis_grid_columns",
                 "om_analysis_selected_version_id", "om_analysis_selected_wall_refs_json", "om_analysis_space_source_id", "om_analysis_storey_ref", "om_analysis_support_source_id",
                 "om_analysis_datum_mode", "om_analysis_datum_slab_ref", "om_analysis_b4_cut_offset",
                 "om_analysis_height_mode", "om_analysis_manual_height", "om_analysis_height_unit",
                 "om_analysis_active_region_id", "om_analysis_inspect_row",
                 "om_analysis_inspect_column", "om_analysis_inspection"):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(_REGISTERED_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        finally:
            pass
    _REGISTERED_CLASSES = ()
    if runtime is not None:
        runtime.STATE.observation_hooks_active = False
    _TIMER = None
    _REGISTERED = False


