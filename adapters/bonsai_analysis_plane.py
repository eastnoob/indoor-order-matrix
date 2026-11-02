"""Native drawing-camera observations and bounded creation for analysis planes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import importlib
import math
from typing import Any

if "." in (__package__ or ""):
    from ..features.field_core import _freeze
    from ..features.scene_contract import AnalysisPlane
else:
    from features.field_core import _freeze
    from features.scene_contract import AnalysisPlane


BINDING_VERSION = "bonsai-camera-binding/2"
FRAME_TOLERANCE = 1e-6  # Blender matrices use single-precision components.


def _validated_frame(matrix: Any, *, allow_scale: bool) -> tuple[tuple[float, ...], tuple[tuple[float, ...], ...]]:
    """Read matrix columns as frame axes and reject non-finite, singular, or sheared poses."""
    values = tuple(tuple(float(matrix[row][col]) for col in range(4)) for row in range(4))
    if not all(math.isfinite(value) for row in values for value in row):
        raise ValueError("camera matrix must be finite")
    if any(abs(values[3][col] - float(col == 3)) > FRAME_TOLERANCE for col in range(4)):
        raise ValueError("camera matrix must be affine")
    axes = tuple(tuple(values[row][col] for row in range(3)) for col in range(3))
    lengths = tuple(math.hypot(*axis) for axis in axes)
    if any(length <= 0 for length in lengths):
        raise ValueError("camera matrix must be non-singular")
    if not allow_scale and any(abs(length - 1) > FRAME_TOLERANCE for length in lengths):
        raise ValueError("Bonsai resolved camera matrix must have unit axes")
    basis = tuple(tuple(value / lengths[index] for value in axis) for index, axis in enumerate(axes))
    if any(abs(sum(a * b for a, b in zip(basis[first], basis[second]))) > FRAME_TOLERANCE
           for first in range(3) for second in range(first + 1, 3)):
        raise ValueError("camera matrix must not contain shear")
    return tuple(values[row][3] for row in range(3)), basis


def _determinant(basis: tuple[tuple[float, ...], ...]) -> float:
    """Return frame handedness without depending on Blender's matrix type."""
    x, y, z = basis
    return sum(z[index] * (x[(index + 1) % 3] * y[(index + 2) % 3]
                          - x[(index + 2) % 3] * y[(index + 1) % 3]) for index in range(3))


@dataclass(frozen=True)
class CameraBinding:
    """An immutable camera reference and observation, with metre origin and unit basis axes."""

    camera_id: str
    role: str
    origin: tuple[float, float, float]
    basis: tuple[tuple[float, float, float], ...]
    display: Mapping[str, Any]
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Validate authorship and deeply freeze facts copied from the source camera."""
        if not isinstance(self.camera_id, str) or not self.camera_id.strip():
            raise ValueError("camera_id must be a non-empty string")
        if self.role not in {"display", "geometry_author"}:
            raise ValueError("camera role must be display or geometry_author")
        if not isinstance(self.display, Mapping) or not isinstance(self.provenance, Mapping):
            raise ValueError("camera display and provenance must be mappings")
        # The analyzer contract owns orthonormal validation; a camera cannot inject a left-handed frame.
        frame = AnalysisPlane(name="camera-observation", origin=self.origin, basis=self.basis)
        if _determinant(frame.basis) <= 0:
            raise ValueError("resolved camera basis must be right-handed")
        object.__setattr__(self, "origin", frame.origin)
        object.__setattr__(self, "basis", frame.basis)
        object.__setattr__(self, "display", _freeze(self.display))
        object.__setattr__(self, "provenance", _freeze(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the observation without exposing mutable nested source data."""
        def json_value(value: Any) -> Any:
            """Unfreeze nested JSON facts for a caller-owned serialized copy."""
            if isinstance(value, Mapping):
                return {key: json_value(item) for key, item in value.items()}
            if isinstance(value, tuple):
                return [json_value(item) for item in value]
            return value
        return {"camera_id": self.camera_id, "role": self.role, "origin": list(self.origin),
                "basis": json_value(self.basis), "display": json_value(self.display),
                "provenance": json_value(self.provenance)}


def read_camera_binding(camera: Any, *, role: str = "display", source_id: str | None = None) -> CameraBinding:
    """Read native Bonsai camera geometry and identity without changing camera or IFC facts."""
    if role not in {"display", "geometry_author"}:
        raise ValueError("camera role must be display or geometry_author")
    if getattr(camera, "type", None) != "CAMERA":
        raise ValueError("binding requires a Blender CAMERA object")
    if source_id is not None and (not isinstance(source_id, str) or not source_id.strip()):
        raise ValueError("source_id must be a non-empty string")
    # Imports occur at the Blender boundary, so ordinary Python core callers need no Bonsai runtime.
    tool = importlib.import_module("bonsai.tool")
    bonsai = importlib.import_module("bonsai")
    bpy = importlib.import_module("bpy")
    unit_scale = float(bpy.context.scene.unit_settings.scale_length)
    if not math.isfinite(unit_scale) or unit_scale <= 0:
        raise ValueError("Blender unit scale must be finite and positive")
    raw_origin, raw_basis = _validated_frame(camera.matrix_world, allow_scale=True)
    matrix = tool.Drawing.get_camera_matrix(camera)
    origin, native_basis = _validated_frame(matrix, allow_scale=False)
    # A scene's authored length conversion applies to translation, never to unit frame axes.
    origin = tuple(value * unit_scale for value in origin)
    if _determinant(native_basis) <= 0:
        raise ValueError("Bonsai resolved camera basis must be right-handed")
    # Orthonormalize float32 roundoff before handing axes to the stricter analyzer contract.
    x = native_basis[0]
    dot = sum(a * b for a, b in zip(x, native_basis[1]))
    y = tuple(value - dot * axis for value, axis in zip(native_basis[1], x))
    length = math.hypot(*y)
    y = tuple(value / length for value in y)
    z = tuple(x[(index + 1) % 3] * y[(index + 2) % 3]
              - x[(index + 2) % 3] * y[(index + 1) % 3] for index in range(3))
    entity = tool.Ifc.get_entity(camera)
    global_id = getattr(entity, "GlobalId", None)
    project_id = None
    if role == "geometry_author":
        model = tool.Ifc.get()
        projects = model.by_type("IfcProject") if model is not None else ()
        if len(projects) != 1 or not getattr(projects[0], "GlobalId", None):
            raise ValueError("geometry author requires one native IFC project")
        project_id = projects[0].GlobalId
        if (entity is None or not entity.is_a("IfcAnnotation") or entity.ObjectType != "DRAWING"
                or not global_id):
            raise ValueError("geometry author requires a native drawing annotation")
        try:
            native = model.by_guid(global_id)
        except (RuntimeError, ValueError) as error:
            raise ValueError("native camera GUID is absent from the active project") from error
        if native.id() != entity.id() or tool.Ifc.get_object(native) is not camera:
            raise ValueError("native drawing entity/object relationship is inconsistent")
        # A copied Blender IFC link must not compete with the authoritative native object.
        linked = [obj for obj in bpy.data.objects if
                  (linked_entity := tool.Ifc.get_entity(obj)) is not None and linked_entity.id() == entity.id()]
        if len(linked) != 1 or linked[0] is not camera:
            raise ValueError("native drawing must have exactly one linked Blender object")
        if camera.data.type != "ORTHO":
            raise ValueError("geometry author requires an orthographic drawing camera")
        if source_id is not None and source_id != f"ifc:{global_id}":
            raise ValueError("source_id cannot override native drawing identity")
    camera_id = source_id or (f"ifc:{global_id}" if global_id else
                             f"blender:{getattr(getattr(camera, 'library', None), 'filepath', '')}:{camera.name_full}")
    target_view = (tool.Drawing.get_drawing_target_view(entity)
                   if entity is not None and entity.is_a("IfcAnnotation") else None)
    return CameraBinding(
        camera_id=camera_id, role=role, origin=origin, basis=(x, y, z),
        display={"name": camera.name_full, "camera_type": camera.data.type,
                 "ortho_scale": float(camera.data.ortho_scale), "clip_start": float(camera.data.clip_start),
                 "clip_end": float(camera.data.clip_end), "color": tuple(camera.color), "target_view": target_view},
        provenance={"adapter_version": BINDING_VERSION,
                    "bonsai_version": getattr(bonsai, "bbim_semver", {}).get("version", "unreported"),
                    "blender_version": bpy.app.version_string,
                    "native_reader": "bonsai.tool.Drawing.get_camera_matrix",
                    "project_global_id": project_id,
                    "source_step_id": entity.id() if project_id else None,
                    "geometry_author_qualified": role == "geometry_author",
                    "source_ifc_global_id": global_id, "raw_reflected": _determinant(raw_basis) < 0,
                    "raw_origin": raw_origin, "blender_unit_scale_to_m": unit_scale,
                    "units": "m", "drawing_offset_applied": False,
                    "native_pose_comparison_tolerance": {"origin_m": FRAME_TOLERANCE, "unit_axes": FRAME_TOLERANCE},
                    "geometry_precision_note": "float32 native axes orthonormalized; no clipping offset"},
    )


def _require_workflow_camera(binding: CameraBinding, query_kind: str) -> None:
    """Reject unsupported camera capabilities before creating or refreshing a plane."""
    if (not isinstance(binding, CameraBinding) or binding.role != "geometry_author"
            or binding.provenance.get("geometry_author_qualified") is not True):
        raise ValueError("plane requires a verified native geometry_author CameraBinding")
    if any(abs(actual - expected) > FRAME_TOLERANCE
           for actual, expected in zip(binding.basis[2], (0, 0, 1))):
        raise ValueError("analysis workflow requires a horizontal upward camera frame")
    if query_kind == "exact_world_xy_section" and binding.basis != ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        raise ValueError("exact world-XY section requires the canonical world-XY basis")


def plane_from_camera(binding: CameraBinding, *, name: str,
                      query_kind: str = "whole_height_projection") -> AnalysisPlane:
    """Explicitly author a new analyzer plane from one immutable camera observation."""
    _require_workflow_camera(binding, query_kind)
    return AnalysisPlane(name=name, origin=binding.origin, basis=binding.basis,
                         identity=f"bonsai-camera:{binding.camera_id}", revision=1)


def refresh_camera_plane(plane: AnalysisPlane, binding: CameraBinding, *,
                         query_kind: str = "whole_height_projection",
                         project_global_id: str | None = None) -> AnalysisPlane:
    """Refresh an explicitly adopted native author without crossing project identity."""
    if not isinstance(plane, AnalysisPlane) or not isinstance(binding, CameraBinding):
        raise TypeError("refresh requires an AnalysisPlane and CameraBinding")
    _require_workflow_camera(binding, query_kind)
    if project_global_id is not None and binding.provenance["project_global_id"] != project_global_id:
        raise ValueError("native camera project changed")
    if plane.identity != f"bonsai-camera:{binding.camera_id}":
        raise ValueError("plane geometry author differs from the camera binding")
    before = (*plane.origin, *(value for axis in plane.basis for value in axis))
    after = (*binding.origin, *(value for axis in binding.basis for value in axis))
    # Native float32 normalization may drift under positive scale; sub-micrometre drift is not a new pose.
    if all(math.isclose(a, b, rel_tol=0, abs_tol=FRAME_TOLERANCE) for a, b in zip(before, after)):
        return plane
    return replace(plane, origin=binding.origin, basis=binding.basis, revision=plane.revision + 1)


def camera_composition(binding: CameraBinding, plane: AnalysisPlane) -> dict:
    """Persist only the native identity and observed pose in the existing binding mapping."""
    from .blender_analysis_result_wire import canonical_json, plain
    from hashlib import sha256

    _require_workflow_camera(binding, "whole_height_projection")
    if refresh_camera_plane(plane, binding) is not plane:
        raise ValueError("plane differs from the native camera observation")
    observation = {"project_global_id": binding.provenance["project_global_id"],
                   "camera_guid": binding.provenance["source_ifc_global_id"],
                   "origin": plain(plane.origin), "basis": plain(plane.basis)}
    return {"version": 1, **observation, "plane_uuid": plane.identity, "plane_revision": plane.revision,
            "observation_digest": sha256(canonical_json(observation).encode()).hexdigest()}


def resolve_camera_binding(*, project_global_id: str, camera_guid: str) -> CameraBinding:
    """Resolve persisted identities against the current native project before reading pose."""
    tool = importlib.import_module("bonsai.tool")
    model = tool.Ifc.get()
    projects = model.by_type("IfcProject") if model is not None else ()
    if len(projects) != 1 or projects[0].GlobalId != project_global_id:
        raise ValueError("native camera project changed; explicitly adopt a drawing again")
    try:
        entity = model.by_guid(camera_guid)
    except (RuntimeError, ValueError) as error:
        raise ValueError("native drawing was deleted or replaced") from error
    return read_camera_binding(tool.Ifc.get_object(entity), role="geometry_author")


def _drawing_snapshot(bpy, tool, store, brick) -> dict:
    """Retain only the native drawing operation's recovery boundary and existing resource identities."""
    from pathlib import Path

    scene = bpy.context.scene
    props = tool.Drawing.get_document_props()
    model = tool.Ifc.get()
    resource = Path(tool.Ifc.resolve_uri(tool.Drawing.get_default_drawing_resource_path("ShadingStyles")))
    missing_directories = []
    parent = resource.parent
    while not parent.exists():
        missing_directories.append(parent)
        parent = parent.parent
    return {
        "model": model, "entities": tuple(sorted(str(entity) for entity in model)),
        "history": list(store.history), "future": list(store.future),
        "ifc_history": list(model.history), "ifc_future": list(model.future),
        "last": store.last_transaction, "bim_last": tool.Blender.get_bim_props().last_transaction,
        "dirty": tool.Blender.get_bim_props().is_dirty,
        "id_map": dict(store.id_map), "guid_map": dict(store.guid_map), "edited": set(store.edited_objs),
        "brick": (list(brick.history), list(brick.future), brick.current_changesets),
        "resources": {kind: set(getattr(bpy.data, kind)) for kind in
                      ("objects", "cameras", "meshes", "curves", "collections", "materials")},
        "links": {obj: tuple(obj.users_collection) for obj in bpy.data.objects},
        "object_facts": {obj: (obj.data, tuple(tuple(row) for row in obj.matrix_world),
                              tool.Blender.get_object_bim_props(obj).ifc_definition_id) for obj in bpy.data.objects},
        "children": {group: tuple(group.children) for group in (scene.collection, *bpy.data.collections)},
        "selected": tuple(bpy.context.selected_objects), "active": bpy.context.view_layer.objects.active,
        "camera": scene.camera, "cursor": scene.cursor.matrix.copy(),
        "layer": bpy.context.view_layer.active_layer_collection,
        "container": tool.Spatial.get_spatial_props().default_container,
        "drawing_fields": {name: getattr(props, name) for name in
                           ("target_view", "location_hint", "active_drawing_id", "active_drawing_index", "current_drawing_index")},
        "drawings": [{name: getattr(item, name) for name in
                      ("name", "target_view", "is_selected", "is_drawing", "is_expanded", "ifc_definition_id")}
                     for item in props.drawings],
        "drawing_selected": dict(tool.Drawing.drawing_selected_states),
        "shading_resource": resource, "shading_existed": resource.exists(), "missing_directories": missing_directories,
    }


def _recover_drawing(before: dict, transaction_key: str | None, bpy, tool, store, brick) -> None:
    """Discard an open owned transaction or reverse exactly its finalized native event."""
    model = before["model"]
    if tool.Ifc.get() is not model:
        raise RuntimeError("active IFC changed during drawing creation")
    events = store.history[len(before["history"]):]
    if store.history[:len(before["history"])] != before["history"]:
        raise RuntimeError("native history boundary changed")
    if events and (len(events) != 1 or not transaction_key or events[0]["key"] != transaction_key):
        raise RuntimeError("drawing recovery does not own the new history events")
    if model.transaction is not None:
        if not transaction_key or store.current_transaction != transaction_key:
            raise RuntimeError("drawing recovery does not own the open transaction")
        model.discard_transaction()
        # An open event contains link operations but no finalized IFC undo callback.
        for event in reversed(events):
            for operation in reversed(event["operations"]):
                operation["rollback"](operation["data"])
    elif events:
        for operation in reversed(events[0]["operations"]):
            operation["rollback"](operation["data"])
    if brick.graph is not None and transaction_key:
        for _ in range(brick.current_changesets):
            brick.graph.undo()
    if tuple(sorted(str(entity) for entity in model)) != before["entities"]:
        raise RuntimeError("native IFC entities or relationships were not restored")

    # Remove exact newly allocated datablocks; existing names are never deletion keys.
    for kind, previous in before["resources"].items():
        collection = getattr(bpy.data, kind)
        if not previous.issubset(set(collection)):
            raise RuntimeError("drawing creation removed an existing " + kind + " resource")
        for resource in set(collection) - previous:
            collection.remove(resource, do_unlink=True)
    for obj, groups in before["links"].items():
        for group in tuple(obj.users_collection):
            if group not in groups:
                group.objects.unlink(obj)
        for group in groups:
            if obj not in tuple(group.objects):
                group.objects.link(obj)
    for group, children in before["children"].items():
        for child in tuple(group.children):
            if child not in children:
                group.children.unlink(child)
        for child in children:
            if child not in tuple(group.children):
                group.children.link(child)
    for name, value in (("history", before["history"]), ("future", before["future"]),
                        ("id_map", before["id_map"]), ("guid_map", before["guid_map"]),
                        ("edited_objs", before["edited"]), ("last_transaction", before["last"]),
                        ("current_transaction", "")):
        setattr(store, name, value)
    model.history = before["ifc_history"]
    model.future = before["ifc_future"]
    brick.history, brick.future, brick.current_changesets = before["brick"]
    tool.Blender.get_bim_props().last_transaction = before["bim_last"]
    tool.Blender.get_bim_props().is_dirty = before["dirty"]
    scene = bpy.context.scene
    scene.camera = before["camera"]
    scene.cursor.matrix = before["cursor"]
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in before["selected"])
    bpy.context.view_layer.objects.active = before["active"]
    bpy.context.view_layer.active_layer_collection = before["layer"]
    tool.Spatial.get_spatial_props().default_container = before["container"]
    props = tool.Drawing.get_document_props()
    props.drawings.clear()
    for record in before["drawings"]:
        item = props.drawings.add()
        for name, value in record.items():
            setattr(item, name, value)
    tool.Drawing.drawing_selected_states = before["drawing_selected"]
    for name, value in before["drawing_fields"].items():
        setattr(props, name, value)
    if not before["shading_existed"]:
        before["shading_resource"].unlink(missing_ok=True)
        for directory in before["missing_directories"]:
            if directory.exists():
                directory.rmdir()
    after = _drawing_snapshot(bpy, tool, store, brick)
    if any(after[key] != value for key, value in before.items()):
        raise RuntimeError("native drawing recovery could not verify all retained state")


def _invoke_add_drawing():
    """Invoke the installed native operator through its normal transaction wrapper."""
    return importlib.import_module("bpy").ops.bim.add_drawing()


def create_native_drawing(*, storey_ref: str | None = None):
    """Create one native plan drawing and return its exact camera, recovering owned failures."""
    bpy = importlib.import_module("bpy")
    tool = importlib.import_module("bonsai.tool")
    store = importlib.import_module("bonsai.bim.ifc").IfcStore
    brick = importlib.import_module("bonsai.tool.brick").BrickStore
    model = tool.Ifc.get()
    if bpy.context.scene.get("om_analysis_authoring_recovery_error"):
        raise ValueError("native authoring is blocked after failed recovery; reopen a verified saved file")
    if model is None or len(model.by_type("IfcProject")) != 1:
        raise ValueError("native drawing requires exactly one active IFC project")
    if store.current_transaction or store.modal_in_progress or model.transaction is not None:
        raise ValueError("finish the unrelated native transaction before creating a drawing")
    if model.history_size <= 0:
        raise ValueError("native IFC transaction history must be enabled")
    if bpy.context.mode != "OBJECT":
        raise ValueError("native drawing creation requires Object mode")
    hint = 0
    if storey_ref is not None:
        if not storey_ref.startswith("ifc-object:"):
            raise ValueError("native drawing storey reference is invalid")
        storey = model.by_guid(storey_ref.removeprefix("ifc-object:"))
        if not storey.is_a("IfcBuildingStorey") or tool.Ifc.get_object(storey) is None:
            raise ValueError("native drawing requires a linked storey")
        hint = storey.id()
    before = _drawing_snapshot(bpy, tool, store, brick)
    transaction_key = None
    created = []
    create_descriptor = tool.Drawing.__dict__["create_camera"]
    begin_descriptor = store.__dict__["begin_transaction"]
    native_create = tool.Drawing.create_camera
    native_begin = store.begin_transaction

    def capture_camera(_class, *arguments, **keywords):
        """Retain the exact object returned by native creation without guessing its name."""
        camera = native_create(*arguments, **keywords)
        created.append(camera)
        return camera

    def capture_transaction(operator):
        """Record the native top-level key before any nested authoring step runs."""
        nonlocal transaction_key
        if transaction_key is not None:
            raise RuntimeError("drawing attempted a second top-level native transaction")
        native_begin(operator)
        transaction_key = operator.transaction_key

    tool.Drawing.create_camera = classmethod(capture_camera)
    store.begin_transaction = staticmethod(capture_transaction)
    props = tool.Drawing.get_document_props()
    try:
        props.target_view = "PLAN_VIEW"
        props.location_hint = str(hint)
        # AddDrawing otherwise syncs an unrelated active drawing after creating this one.
        props.active_drawing_id = 0
        result = _invoke_add_drawing()
        if result != {"FINISHED"} or len(created) != 1:
            raise ValueError("native drawing was cancelled or did not return exactly one camera")
        if store.current_transaction or model.transaction is not None:
            raise RuntimeError("native drawing left its transaction open")
        plane_from_camera(read_camera_binding(created[0], role="geometry_author"), name="Analysis plane")
        props.active_drawing_id = before["drawing_fields"]["active_drawing_id"]
        return created[0]
    except Exception as error:
        try:
            _recover_drawing(before, transaction_key, bpy, tool, store, brick)
        except Exception as recovery_error:
            bpy.context.scene["om_analysis_authoring_recovery_error"] = str(recovery_error)
            raise RuntimeError("native drawing recovery failed: " + str(recovery_error)) from error
        raise
    finally:
        tool.Drawing.create_camera = create_descriptor
        store.begin_transaction = begin_descriptor

