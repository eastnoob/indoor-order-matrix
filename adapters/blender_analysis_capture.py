"""Main-thread read-only evaluated capture; no native imports at module import."""

from __future__ import annotations

from collections.abc import Mapping
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from functools import lru_cache
import importlib
import json
import math
from pathlib import Path
from time import perf_counter
from threading import current_thread, main_thread
from types import MappingProxyType
import uuid


CAPTURE_VERSION = "blender-analysis-capture/1"
BINARY = Path(r"D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe")


def plain(value):
    """Copy frozen JSON facts into caller-owned transport values."""
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def normalized_capture_steps(captured):
    """Copy and normalize capture facts cooperatively before request encoding."""
    if isinstance(captured, CanonicalCaptureInput):
        captured = {name: getattr(captured, name) for name in
                    ("identity", "records", "diagnostics", "observation", "capture_id", "capture_complete")}
    data = yield from plain_steps(captured)
    for record in data.get("records", ()):
        mesh = record.get("mesh")
        quality = mesh.get("quality") if isinstance(mesh, Mapping) else None
        histogram = quality.get("edge_face_counts") if isinstance(quality, Mapping) else None
        if isinstance(histogram, Mapping):
            bins = []
            for face_count, edge_count in histogram.items():
                if type(face_count) is not int or face_count < 0:
                    raise ValueError("edge_face_counts keys must be nonnegative integers")
                if type(edge_count) is not int or edge_count < 0:
                    raise ValueError("edge_face_counts values must be nonnegative integers")
                bins.append((face_count, edge_count))
                yield None
            quality["edge_face_counts"] = [
                {"face_count": face_count, "edge_count": edge_count}
                for face_count, edge_count in sorted(bins)]
        elif isinstance(histogram, (list, tuple)):
            bins = []
            seen = set()
            for item in histogram:
                if not isinstance(item, Mapping) or set(item) != {"face_count", "edge_count"}:
                    raise ValueError("edge_face_counts records must contain face_count and edge_count")
                face_count, edge_count = item["face_count"], item["edge_count"]
                if type(face_count) is not int or face_count < 0:
                    raise ValueError("edge_face_counts face_count must be a nonnegative integer")
                if type(edge_count) is not int or edge_count < 0:
                    raise ValueError("edge_face_counts edge_count must be a nonnegative integer")
                if face_count in seen:
                    raise ValueError("edge_face_counts contains duplicate face_count")
                seen.add(face_count)
                bins.append((face_count, edge_count))
                yield None
            quality["edge_face_counts"] = [
                {"face_count": face_count, "edge_count": edge_count}
                for face_count, edge_count in sorted(bins)]
        elif histogram is not None:
            raise ValueError("edge_face_counts must be a mapping or record list")
        yield None
    return data


def freeze(value):
    """Detach and freeze JSON facts without importing the geometry runtime."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


def _json_key(key):
    """Validate one key using the same JSON-compatible key domain as json.dumps."""
    json.dumps({key: None}, sort_keys=True, allow_nan=False)


def _freeze_generator(value, progress):
    """Validate and detach each node, including nodes inside a single large mesh."""
    progress[0] += 1
    if progress[0] % 256 == 0:
        yield None
    if isinstance(value, Mapping):
        # The old sorted JSON validation rejects mutually unsortable key types.
        sorted(value)
        result = {}
        for key, item in value.items():
            _json_key(key)
            result[key] = yield from _freeze_generator(item, progress)
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            result.append((yield from _freeze_generator(item, progress)))
        return tuple(result)
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        # Preserve json.dumps' integer conversion limit without formatting every index.
        if value.bit_length() > 1024:
            json.dumps(value, allow_nan=False)
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("capture contains non-finite or non-data value: " + type(value).__name__)


def freeze_steps(value):
    """Freeze validated capture data with a main-thread check at every resume."""
    steps = _freeze_generator(value, [0])
    while True:
        _main_thread()
        try:
            next(steps)
        except StopIteration as done:
            return done.value
        yield None


def _plain_generator(value, progress):
    """Copy detached JSON values into mutable transport containers cooperatively."""
    progress[0] += 1
    if progress[0] % 256 == 0:
        yield None
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            result[key] = yield from _plain_generator(item, progress)
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            result.append((yield from _plain_generator(item, progress)))
        return result
    return value


def plain_steps(value):
    """Yield while copying frozen capture data into mutable transport values."""
    return (yield from _plain_generator(value, [0]))


def digest(value):
    """Hash stable strict JSON facts without relying on object identity."""
    return sha256(json.dumps(plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def is_owned_display(tags):
    """Recognize explicit analyzer ownership, never names or an IFC annotation category."""
    return (tags.get("om_analysis_preview") is True or tags.get("OM_B4_Diagnostic") is True
            or tags.get("om_analysis_owner") == "order_analyzer"
            and tags.get("om_analysis_role") in {
                "plane", "overlay", "display_camera", "board", "board_source", "board_display",
                "board_mesh", "board_material", "board_nodes",
            })


@lru_cache(maxsize=None)
def ifc_ancestry(schema, class_name):
    """Read verified IFC ancestry from the installed schema, never caller-supplied roles."""
    import ifcopenshell.ifcopenshell_wrapper as wrapper
    try:
        declaration = wrapper.schema_by_name(schema).declaration_by_name(class_name)
        ancestry = []
        while declaration is not None:
            ancestry.append(declaration.name())
            declaration = declaration.supertype()
    except (RuntimeError, AttributeError, TypeError) as exc:
        raise ValueError("IFC class must resolve in the declared schema") from exc
    return tuple(ancestry)


@dataclass(frozen=True)
class CanonicalCaptureInput:
    """Immutable complete IFC inventory, evaluated geometry and separate observation."""

    identity: Mapping
    records: tuple
    diagnostics: tuple
    observation: Mapping
    capture_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    capture_complete: bool = True

    def __post_init__(self):
        """Freeze independent transport data and reject non-JSON facts."""
        for name in ("identity", "records", "diagnostics", "observation"):
            value = getattr(self, name)
            digest(value)
            object.__setattr__(self, name, freeze(value))

    @classmethod
    def _from_frozen(cls, *, identity, records, diagnostics, observation, capture_id,
                     capture_complete=True):
        """Construct from fields already validated and detached cooperatively."""
        result = object.__new__(cls)
        object.__setattr__(result, "identity", identity)
        object.__setattr__(result, "records", records)
        object.__setattr__(result, "diagnostics", diagnostics)
        object.__setattr__(result, "observation", observation)
        object.__setattr__(result, "capture_id", capture_id)
        object.__setattr__(result, "capture_complete", capture_complete)
        return result

    def to_dict(self):
        """Return a serializable copy without exposing captured facts to mutation."""
        return {name: plain(getattr(self, name)) for name in
                ("identity", "records", "diagnostics", "observation", "capture_id", "capture_complete")}

    @property
    def session_token(self):
        """Expose the originating runtime scene session separately from stable facts."""
        return self.observation.get("scene_token")

    @property
    def ifc_identity(self):
        """Expose the stable linked IFC source identity."""
        return self.identity["ifc_source_identity"]

    @property
    def project_global_id(self):
        """Expose the verified unique IFC project GUID."""
        return self.identity["project_global_id"]

    @property
    def schema(self):
        """Expose the source IFC schema."""
        return self.identity["schema"]

    @property
    def units_scale(self):
        """Expose the actual Blender length conversion used for evaluated coordinates."""
        return self.observation.get("blender_world_to_m")

    @property
    def frame(self):
        """Expose the frozen Blender frame and subframe."""
        return (self.observation.get("frame"), self.observation.get("subframe"))

    @property
    def source_inventory(self):
        """Retain every IFC product, including missing evaluated geometry."""
        return self.records

    @property
    def geometry_records(self):
        """Expose the actual extracted mesh facts without duplicating them."""
        return tuple(row["mesh"] for row in self.records if row.get("mesh") is not None)

    @property
    def unresolved_records(self):
        """Expose explicit missing or invalid geometry facts."""
        return tuple(row for row in self.records if row.get("status") not in {"extracted", "display_only"})

    @property
    def observation_token(self):
        """Bind volatile runtime observations separately from stable source digests."""
        return digest(self.observation)


@dataclass
class CaptureJob:
    """Temporary native capture state, owned by the Blender main thread."""

    context: object
    tool: object
    model: object
    entities: tuple
    links: dict
    identity: dict
    observation: dict
    batch_size: int
    graph: object
    records: list = field(default_factory=list)
    diagnostics: list = field(default_factory=list)
    index: int = 0
    stage: str = "capturing"
    job_token: str = field(default_factory=lambda: uuid.uuid4().hex)
    elapsed_seconds: float = 0.
    callback_seconds: float = 0.
    max_object_seconds: float = 0.
    started_monotonic: float = field(default_factory=perf_counter)

    @property
    def capture_id(self):
        """Expose the capture identity used by canonical transport."""
        return self.job_token

    @property
    def session_token(self):
        """Expose the scene-session binding for runtime freshness guards."""
        return self.observation["scene_token"]

    @property
    def inventory(self):
        """Expose the complete native source inventory owned by the main thread."""
        return self.entities

    @property
    def next_index(self):
        """Expose the next unprocessed source position."""
        return self.index

    @property
    def sources(self):
        """Expose accumulated factual source records."""
        return self.records

    @property
    def geometries(self):
        """Expose extracted geometry without duplicating native or transport data."""
        return tuple(row["mesh"] for row in self.records if row.get("mesh") is not None)

    @property
    def unresolved(self):
        """Expose failed or unavailable source geometry facts."""
        return tuple(row for row in self.records if row["status"] not in {"extracted", "display_only"})

    @property
    def cancelled(self):
        """Expose cooperative cancellation independently of completion."""
        return self.stage == "cancelled"

    @property
    def errors(self):
        """Expose accumulated extraction errors for progress and audit."""
        return tuple(row["error"] for row in self.records if "error" in row)


@dataclass(frozen=True)
class CaptureProgress:
    """Bounded progress with measured indivisible native call duration."""

    job_token: str
    stage: str
    processed: int
    total: int
    elapsed_seconds: float
    callback_seconds: float
    max_object_seconds: float
    errors: tuple
    complete: bool

    @property
    def cancelled(self):
        """Distinguish cancellation from a completed full capture."""
        return self.stage == "cancelled"

    @property
    def capture_id(self):
        """Expose the same capture identity at each lifecycle boundary."""
        return self.job_token


def _main_thread():
    """Reject worker-native access before importing or touching Blender."""
    if current_thread() is not main_thread():
        raise RuntimeError("Blender capture requires the main thread")


def _check_observation(job):
    """Refuse mixed-frame/unit captures instead of publishing inconsistent geometry."""
    scene = job.context.scene
    if (job.context.mode != "OBJECT" or scene.frame_current != job.observation["frame"]
            or scene.frame_subframe != job.observation["subframe"]
            or scene.unit_settings.scale_length != job.observation["blender_world_to_m"]):
        job.stage = "invalidated"
        raise ValueError("capture frame, units or mode changed")


def topology_quality(mesh):
    """Inspect native indexed topology without welding or repairing source geometry."""
    _main_thread()
    import bmesh

    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        edge_faces = Counter(len(edge.link_faces) for edge in bm.edges)
        nonmanifold_edges = sum(not edge.is_manifold for edge in bm.edges)
        nonmanifold_vertices = sum(not vertex.is_manifold for vertex in bm.verts)
        winding = sum(edge.is_manifold and not edge.is_contiguous for edge in bm.edges)
        degenerate = sum(triangle.area <= 0 for triangle in mesh.loop_triangles)
        closed = bool(bm.edges) and all(count == 2 for count in edge_faces)
        manifold = nonmanifold_edges == 0 and nonmanifold_vertices == 0
        return {"method": "fresh_evaluated_bmesh_indexed_topology_no_welding",
                "edge_face_counts": dict(edge_faces), "nonmanifold_edges": nonmanifold_edges,
                "nonmanifold_vertices": nonmanifold_vertices, "inconsistent_winding_edges": winding,
                "degenerate_triangles": degenerate, "is_closed": closed, "is_manifold": manifold,
                "solid_query_eligible": False if not (closed and manifold and winding == 0 and degenerate == 0) else None,
                "solid_validity": "unknown; self-intersection and native IFC geometry parity not checked"}
    finally:
        bm.free()


def extract_evaluated_mesh(obj, depsgraph, scale, *, quality_reader=None):
    """Transform evaluated vertices once, triangulate natively and always release."""
    _main_thread()
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("positive finite Blender metre scale required")
    evaluated = obj.evaluated_get(depsgraph)
    try:
        mesh_started = perf_counter()
        mesh = evaluated.to_mesh()
        to_mesh_seconds = perf_counter() - mesh_started
        if mesh is None:
            raise ValueError("evaluated object returned no mesh")
        mesh.calc_loop_triangles()
        matrix = evaluated.matrix_world.copy()
        determinant = matrix.to_3x3().determinant()
        if not math.isfinite(determinant) or determinant == 0:
            raise ValueError("singular or nonfinite evaluated world transform")
        vertices = [[float(value) * scale for value in matrix @ vertex.co] for vertex in mesh.vertices]
        # Retain native face ordering/winding for exact historical geometry parity.
        triangles = [list(triangle.vertices) for triangle in mesh.loop_triangles]
        if not vertices or not triangles or not all(math.isfinite(c) for point in vertices for c in point):
            raise ValueError("empty or nonfinite evaluated geometry")
        if any(len(set(triangle)) != 3 or any(i < 0 or i >= len(vertices) for i in triangle) for triangle in triangles):
            raise ValueError("invalid evaluated triangle indices")
        try:
            quality = (quality_reader or topology_quality)(mesh)
        except Exception as exc:
            quality = {"is_closed": None, "is_manifold": None, "solid_query_eligible": None,
                       "error": f"{type(exc).__name__}: {exc}"[:300]}
        return {"vertices": vertices, "triangles": triangles, "units": "m", "transform_applied": True,
                "to_mesh_seconds": to_mesh_seconds,
                "world_transform": [list(row) for row in matrix], "quality": quality,
                "is_closed": quality["is_closed"], "is_manifold": quality["is_manifold"],
                "blender_world_to_m": scale,
                "tessellation_settings": {"method": "evaluated_mesh_loop_triangles", "evaluated_polygons": len(mesh.polygons)}}
    finally:
        evaluated.to_mesh_clear()


def begin_analysis_capture(*, bpy_context, scene_token, batch_size=5):
    """Inventory current IFC products through authoritative Bonsai bindings."""
    _main_thread()
    bpy = importlib.import_module("bpy")
    tool = importlib.import_module("bonsai.tool")
    store = importlib.import_module("bonsai.bim.ifc").IfcStore
    if Path(bpy.app.binary_path).resolve() != BINARY.resolve():
        raise ValueError("only the configured portable Blender is supported")
    if not isinstance(scene_token, str) or not scene_token or type(batch_size) is not int or batch_size < 1:
        raise ValueError("scene_token and positive batch_size required")
    model = store.get_file()
    if model is None:
        raise ValueError("Bonsai has no linked IFC model")
    projects = model.by_type("IfcProject")
    if len(projects) != 1:
        raise ValueError("one unique IFC project required")
    scale = bpy_context.scene.unit_settings.scale_length
    if bpy_context.mode != "OBJECT" or not math.isfinite(scale) or scale <= 0:
        raise ValueError("OBJECT mode and positive finite scene scale required")
    links, diagnostics = {}, []
    for obj in bpy_context.scene.objects:
        try:
            entity = tool.Ifc.get_entity(obj)
        except Exception as exc:
            diagnostics.append({"object": obj.name, "reason": "unresolved_bonsai_binding", "error": str(exc)[:200]})
            continue
        if entity is None:
            diagnostics.append({"object": obj.name, "reason": "unlinked_object_not_ifc"})
            continue
        links.setdefault(entity.id(), []).append(obj)
    entities = tuple(sorted(model.by_type("IfcProduct"), key=lambda entity: (getattr(entity, "GlobalId", ""), entity.id())))
    ids = [entity.GlobalId for entity in entities]
    if len(set(ids)) != len(ids) or any(not value for value in ids):
        raise ValueError("ambiguous IFC GlobalId identity")
    from .ifc_bonsai import _native_group_records
    identity = {"project_global_id": projects[0].GlobalId, "ifc_source_identity": str(Path(store.path).resolve()) if store.path else "unsaved:" + projects[0].GlobalId,
                "schema": model.schema, "capture_version": CAPTURE_VERSION,
                "authored_groups": [group.to_dict() for group in _native_group_records(model)]}
    observation = {"scene_token": scene_token, "blend_path": bpy.data.filepath, "scene": bpy_context.scene.name,
                   "frame": bpy_context.scene.frame_current, "subframe": bpy_context.scene.frame_subframe,
                   "blender_world_to_m": scale}
    return CaptureJob(bpy_context, tool, model, entities, links, identity, observation, batch_size,
                      bpy_context.evaluated_depsgraph_get(), diagnostics=diagnostics)


def capture_next_batch(job, *, max_seconds=.050):
    """Read bounded batches; report native overruns rather than claiming preemption."""
    _main_thread()
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("max_seconds must be positive and finite")
    started = perf_counter()
    if job.stage == "capturing":
        _check_observation(job)
    count = 0
    while job.stage == "capturing" and job.index < len(job.entities) and count < job.batch_size:
        entity = job.entities[job.index]
        item_started = perf_counter()
        row = {"id": "ifc-object:" + entity.GlobalId, "global_id": entity.GlobalId, "step_id": entity.id(),
               "project_global_id": job.identity["project_global_id"], "ifc_class": entity.is_a(),
               "binding_verified": True, "mesh": None, "status": "missing_geometry"}
        try:
            if job.model.by_guid(entity.GlobalId).id() != entity.id():
                raise ValueError("IFC identity changed during capture")
            from ifcopenshell.util.element import get_psets
            row["properties"] = get_psets(entity, psets_only=True)
            # Capture authored spatial containment as source facts so a later
            # domain choice can enforce exact storey scope without guessing
            # from object names or geometry overlap.
            containers = []
            storey_refs = []
            for relation in getattr(entity, "ContainedInStructure", ()) or ():
                container = getattr(relation, "RelatingStructure", None)
                if container is None:
                    continue
                ref = "ifc-object:" + container.GlobalId
                containers.append(ref)
                if container.is_a() == "IfcBuildingStorey":
                    storey_refs.append(ref)
            for relation in getattr(entity, "Decomposes", ()) or ():
                container = getattr(relation, "RelatingObject", None)
                if container is None or not callable(getattr(container, "is_a", None)):
                    continue
                ref = "ifc-object:" + container.GlobalId
                if ref not in containers:
                    containers.append(ref)
                if container.is_a() == "IfcBuildingStorey":
                    storey_refs.append(ref)
            row["container_refs"] = containers
            # Do not turn contradictory native containment into a last-wins storey choice.
            row["level_ref"] = storey_refs[0] if len(storey_refs) == 1 else None
            row["spatial_facts"] = {
                "name": getattr(entity, "Name", None),
                "long_name": getattr(entity, "LongName", None),
            }
            if "IfcOpeningElement" in ifc_ancestry(job.model.schema, entity.is_a()):
                row["opening_facts"] = {
                    "host_source_ids": [relation.RelatingBuildingElement.GlobalId
                                        for relation in getattr(entity, "VoidsElements", ())],
                    "filling_source_ids": [relation.RelatedBuildingElement.GlobalId
                                           for relation in getattr(entity, "HasFillings", ())]}
            matches = job.links.get(entity.id(), ())
            if len(matches) > 1:
                raise ValueError("duplicate Blender binding for IFC source")
            if matches:
                obj = matches[0]
                current = job.tool.Ifc.get_entity(obj)
                if current is None or current.GlobalId != entity.GlobalId or current.id() != entity.id():
                    raise ValueError("Bonsai identity changed during capture")
                if job.tool.Ifc.get_object(entity) is not obj:
                    raise ValueError("Bonsai native reverse object link changed during capture")
                row["object_provenance"] = {"name": obj.name, "data": obj.data.name if obj.data else None,
                    "parent": obj.parent.name if obj.parent else None,
                    "frame": job.observation["frame"], "subframe": job.observation["subframe"],
                    "modifiers": [{"name": m.name, "type": m.type, "show_viewport": m.show_viewport,
                                   "show_render": m.show_render} for m in obj.modifiers],
                    "materials": [slot.material.name if slot.material else None for slot in obj.material_slots]}
                tags = {key: obj.get(key) for key in ("om_analysis_preview", "OM_B4_Diagnostic",
                        "om_analysis_owner", "om_analysis_role")} if callable(getattr(obj, "get", None)) else {}
                if is_owned_display(tags):
                    row.update(status="display_only", display_ownership=tags)
                elif obj.type == "CAMERA":
                    from .bonsai_analysis_plane import read_camera_binding
                    row["native_camera"] = read_camera_binding(obj, role="geometry_author").to_dict()
                    row["status"] = "native_drawing_camera"
                elif obj.type == "MESH":
                    row["mesh"] = extract_evaluated_mesh(obj, job.graph, job.observation["blender_world_to_m"])
                    row["status"] = "extracted"
        except Exception as exc:
            row.update(status="invalid_extraction", error=f"{type(exc).__name__}: {exc}"[:300])
        job.records.append(row)
        job.index += 1
        count += 1
        job.max_object_seconds = max(job.max_object_seconds, perf_counter() - item_started)
        if perf_counter() - started >= max_seconds:
            break
    job.callback_seconds = perf_counter() - started
    job.elapsed_seconds = perf_counter() - job.started_monotonic
    if job.index == len(job.entities) and job.stage == "capturing":
        _check_observation(job)
        job.stage = "complete"
    return CaptureProgress(job.job_token, job.stage, job.index, len(job.entities), job.elapsed_seconds,
                           job.callback_seconds, job.max_object_seconds,
                           tuple(row["error"] for row in job.records if "error" in row), job.stage == "complete")


def cancel_capture(job, *, reason):
    """Cancel between batches without publishing an incomplete source inventory."""
    _main_thread()
    job.stage = "cancelled"
    job.diagnostics.append({"reason": str(reason)[:300]})
    return job


def _check_final_capture(job, records):
    """Check complete capture and current native identities against the supplied facts."""
    _main_thread()
    if job.stage != "complete":
        raise ValueError("capture inventory is incomplete")
    _check_observation(job)
    from .ifc_bonsai import _native_group_records
    if [group.to_dict() for group in _native_group_records(job.model)] != plain(job.identity.get("authored_groups", [])):
        job.stage = "invalidated"
        raise ValueError("authored group membership changed during capture")
    current = {(entity.id(), entity.GlobalId) for entity in job.model.by_type("IfcProduct")}
    if current != {(row["step_id"], row["global_id"]) for row in records}:
        job.stage = "invalidated"
        raise ValueError("capture source inventory changed")
    expected_guids = {row["step_id"]: row["global_id"] for row in records}
    for step, objects in job.links.items():
        if step not in expected_guids:
            continue
        for obj in objects:
            entity = job.tool.Ifc.get_entity(obj)
            expected = expected_guids[step]
            if (entity is None or entity.id() != step or entity.GlobalId != expected
                    or job.tool.Ifc.get_object(entity) is not obj):
                job.stage = "invalidated"
                raise ValueError("Bonsai binding changed during capture")


def finalize_capture(job):
    """Freeze a completed inventory; cancelled/partial captures cannot publish."""
    _check_final_capture(job, job.records)
    return CanonicalCaptureInput(job.identity, tuple(job.records), tuple(job.diagnostics),
                                 job.observation, capture_id=job.capture_id)


def finalize_capture_steps(job):
    """Validate and freeze cooperatively, then recheck native identities before returning."""
    _check_final_capture(job, job.records)
    frozen = {}
    for name in ("identity", "records", "diagnostics", "observation"):
        frozen[name] = yield from freeze_steps(getattr(job, name))
    # Timer yields permit edits; verify against the detached facts, not mutable source rows.
    _check_final_capture(job, frozen["records"])
    return CanonicalCaptureInput._from_frozen(
        identity=frozen["identity"], records=frozen["records"],
        diagnostics=frozen["diagnostics"], observation=frozen["observation"],
        capture_id=job.capture_id)

