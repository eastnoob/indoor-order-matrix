"""Pure-Python seam checks; these stubs are not native Bonsai runtime evidence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import subprocess
import sys
from types import SimpleNamespace

import pytest

from ..adapters.bonsai_analysis_plane import CameraBinding, plane_from_camera, read_camera_binding, refresh_camera_plane


def _matrix(*, scale=(1, 1, 1), origin=(2, 3, 1.6)):
    """Build a diagonal camera matrix without using Blender or mathutils."""
    return [[scale[0], 0, 0, origin[0]], [0, scale[1], 0, origin[1]],
            [0, 0, scale[2], origin[2]], [0, 0, 0, 1]]


def _camera(matrix=None):
    """Return a clearly synthetic camera for dependency-seam tests."""
    return SimpleNamespace(type="CAMERA", name_full="FixtureCamera", library=None,
                           matrix_world=matrix or _matrix(), color=(0.2, 0.3, 0.4, 1.0),
                           data=SimpleNamespace(type="ORTHO", ortho_scale=8.0, clip_start=0.1, clip_end=100.0))


def _runtime(monkeypatch, *, resolved=None, entity=None):
    """Inject stubs at the lazy import seam and retain calls for verification."""
    calls = []
    entity = entity or SimpleNamespace(GlobalId="native-ifc-id", ObjectType="DRAWING",
        id=lambda: 42, is_a=lambda name: name == "IfcAnnotation")
    if not hasattr(entity, "id"):
        entity.id = lambda: 42
        entity.ObjectType = "DRAWING"
    objects = []
    project = SimpleNamespace(GlobalId="project-A")
    model = SimpleNamespace(by_type=lambda name: [project] if name == "IfcProject" else [entity],
                            by_guid=lambda guid: entity)
    def matrix(camera):
        """Expose a resolved matrix while recording the selected native seam."""
        calls.append(("get_camera_matrix", camera))
        return resolved if resolved is not None else _matrix()
    def get_entity(camera):
        """Return the synthetic IFC link without editing camera metadata."""
        calls.append(("get_entity", camera))
        if camera not in objects:
            objects.append(camera)
        return entity
    def target_view(drawing):
        """Label only the stub drawing target view."""
        return "REFLECTED_PLAN_VIEW"
    tool = SimpleNamespace(Drawing=SimpleNamespace(get_camera_matrix=matrix,
                           get_drawing_target_view=target_view),
                           Ifc=SimpleNamespace(get_entity=get_entity, get=lambda: model,
                                               get_object=lambda item: objects[0] if objects else None))
    monkeypatch.setitem(sys.modules, "bonsai", SimpleNamespace(bbim_semver={"version": "stub-only"}))
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    monkeypatch.setitem(sys.modules, "bpy", SimpleNamespace(data=SimpleNamespace(objects=objects),
                        app=SimpleNamespace(version_string="stub-only"),
                        context=SimpleNamespace(scene=SimpleNamespace(unit_settings=SimpleNamespace(scale_length=1)))))
    return calls


def test_adapter_import_does_not_load_blender_or_bonsai():
    """Pure core imports remain usable without native Blender modules."""
    result = subprocess.run([sys.executable, "-c",
                             "import sys; import adapters.bonsai_analysis_plane; "
                             "assert 'bpy' not in sys.modules; assert 'bonsai' not in sys.modules"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_capture_uses_native_seam_and_retains_exact_origin(monkeypatch):
    """Clip offsets stay display-only and source camera facts remain unchanged."""
    calls = _runtime(monkeypatch)
    camera = _camera()
    before = repr(camera)
    binding = read_camera_binding(camera, role="geometry_author")
    assert [name for name, _ in calls][:2] == ["get_camera_matrix", "get_entity"]
    assert repr(camera) == before
    assert binding.origin == (2, 3, 1.6)
    assert binding.basis == ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert binding.display["clip_start"] == 0.1
    assert binding.provenance["drawing_offset_applied"] is False
    assert binding.provenance["bonsai_version"] == "stub-only"
    with pytest.raises(FrozenInstanceError):
        binding.role = "display"
    with pytest.raises(TypeError):
        binding.display["color"] = "red"
    copied = binding.to_dict()
    copied["display"]["color"][0] = 100
    assert binding.display["color"][0] == 0.2


def test_reflection_uses_resolved_native_frame(monkeypatch):
    """Raw mirrored axes never replace Bonsai's resolved right-handed frame."""
    def is_annotation(name):
        """Identify the stub as a drawing annotation."""
        return name == "IfcAnnotation"
    entity = SimpleNamespace(GlobalId="native-ifc-id", is_a=is_annotation)
    _runtime(monkeypatch, resolved=_matrix(scale=(-1, -1, 1)), entity=entity)
    binding = read_camera_binding(_camera(_matrix(scale=(1, -1, 1))))
    assert binding.camera_id == "ifc:native-ifc-id"
    assert binding.basis == ((-1, 0, 0), (0, -1, 0), (0, 0, 1))
    assert binding.provenance["raw_reflected"] is True
    assert binding.display["target_view"] == "REFLECTED_PLAN_VIEW"


def test_display_and_positive_scale_changes_preserve_geometry(monkeypatch):
    """Display metadata and removed camera scale cannot become geometric authorship."""
    _runtime(monkeypatch)
    camera = _camera()
    first = read_camera_binding(camera)
    camera.data.ortho_scale = 90
    camera.data.clip_start = 0.4
    camera.color = (1, 0, 0, 1)
    camera.matrix_world = _matrix(scale=(2, 3, 4))
    second = read_camera_binding(camera)
    assert first.role == second.role == "display"
    assert first.origin == second.origin and first.basis == second.basis
    assert first.display != second.display


@pytest.mark.parametrize("change", ["shear", "singular", "nonfinite", "nonaffine"])
def test_bad_raw_camera_matrix_is_rejected(monkeypatch, change):
    """Malformed source matrices cannot be normalized into apparently valid facts."""
    calls = _runtime(monkeypatch)
    matrix = _matrix()
    if change == "shear":
        matrix[0][1] = 0.1
    elif change == "singular":
        matrix[1][1] = 0
    elif change == "nonfinite":
        matrix[0][3] = float("nan")
    else:
        matrix[3][0] = 0.1
    with pytest.raises(ValueError):
        read_camera_binding(_camera(matrix))
    assert calls == []


def test_left_handed_resolved_matrix_is_rejected(monkeypatch):
    """The adapter rejects a broken native resolver rather than silently flipping axes."""
    _runtime(monkeypatch, resolved=_matrix(scale=(1, -1, 1)))
    with pytest.raises(ValueError, match="right-handed"):
        read_camera_binding(_camera())


def test_roundoff_is_orthonormalized_without_clip_offset(monkeypatch):
    """Tiny native float32 axis drift is repaired only within validated frame precision."""
    matrix = _matrix()
    matrix[0][1] = 1e-8
    _runtime(monkeypatch, resolved=matrix)
    binding = read_camera_binding(_camera())
    assert binding.origin == (2, 3, 1.6)
    assert binding.basis == ((1, 0, 0), (0, 1, 0), (0, 0, 1))


@pytest.mark.parametrize("role", [None, "camera", "author", ""])
def test_ambiguous_role_fails_before_runtime_import(role):
    """Only explicit display and geometry-author modes are legal."""
    with pytest.raises(ValueError, match="role"):
        read_camera_binding(_camera(), role=role)


def test_non_camera_and_blank_identity_are_rejected():
    """A display mesh or a blank caller ID cannot impersonate a camera binding."""
    with pytest.raises(ValueError, match="CAMERA"):
        read_camera_binding(SimpleNamespace(type="MESH"))
    with pytest.raises(ValueError, match="source_id"):
        read_camera_binding(_camera(), source_id=" ")


def test_camera_binding_rejects_left_handed_direct_construction():
    """Direct dataclass callers observe the same frame contract as capture."""
    with pytest.raises(ValueError, match="right-handed"):
        CameraBinding(camera_id="fixture", role="display", origin=(0, 0, 0),
                      basis=((1, 0, 0), (0, -1, 0), (0, 0, 1)), display={}, provenance={})


def test_display_binding_cannot_author_or_refresh_plane(monkeypatch):
    """Composition does not turn a display camera into a geometry author."""
    _runtime(monkeypatch)
    camera = _camera()
    binding = read_camera_binding(camera)
    with pytest.raises(ValueError, match="geometry_author"):
        plane_from_camera(binding, name="analysis")
    plane = plane_from_camera(read_camera_binding(camera, role="geometry_author"), name="analysis")
    display = replace(binding, origin=(9, 8, 7))
    with pytest.raises(ValueError, match="geometry_author"):
        refresh_camera_plane(plane, display)


def test_explicit_refresh_retains_identity_and_updates_only_changed_pose(monkeypatch):
    """A stable author produces revisioned immutable snapshots and no random refresh revisions."""
    _runtime(monkeypatch)
    binding = read_camera_binding(_camera(), role="geometry_author")
    plane = plane_from_camera(binding, name="analysis")
    assert plane.identity == "bonsai-camera:ifc:native-ifc-id" and plane.revision == 1
    assert refresh_camera_plane(plane, binding) is plane
    changed_display = replace(binding, display={"color": "red", "ortho_scale": 100})
    assert refresh_camera_plane(plane, changed_display) is plane
    drift = replace(binding, origin=(2 + 1e-8, 3, 1.6))
    assert refresh_camera_plane(plane, drift) is plane
    changed_pose = replace(binding, origin=(2, 3, 2.0))
    updated = refresh_camera_plane(plane, changed_pose)
    assert updated.identity == plane.identity and updated.revision == 2
    assert updated.origin == (2, 3, 2.0) and plane.origin == (2, 3, 1.6)
    with pytest.raises(ValueError, match="author differs"):
        refresh_camera_plane(plane, replace(binding, camera_id="different-camera"))


def test_blender_length_units_are_converted_only_on_translation(monkeypatch):
    """Millimetre-authored camera positions become metre-valued analyzer frames."""
    _runtime(monkeypatch)
    sys.modules["bpy"].context.scene.unit_settings.scale_length = 0.001
    binding = read_camera_binding(_camera())
    assert binding.origin == (0.002, 0.003, 0.0016)
    assert binding.basis == ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert binding.provenance["blender_unit_scale_to_m"] == 0.001


@pytest.mark.parametrize("change", ["missing_project", "duplicate_project", "not_drawing", "unlinked",
                                    "wrong_guid", "wrong_object", "duplicate_object", "override", "perspective"])
def test_geometry_author_requires_unique_native_project_drawing_and_object(monkeypatch, change):
    """Names and caller IDs cannot stand in for the current native IFC relationship."""
    _runtime(monkeypatch)
    tool = sys.modules["bonsai.tool"]
    camera = _camera()
    read_camera_binding(camera)
    model = tool.Ifc.get()
    entity = model.by_guid("native-ifc-id")
    if change == "missing_project":
        model.by_type = lambda name: []
    elif change == "duplicate_project":
        model.by_type = lambda name: [SimpleNamespace(GlobalId="project-A"), SimpleNamespace(GlobalId="other")]
    elif change == "not_drawing":
        entity.ObjectType = "LABEL"
    elif change == "unlinked":
        tool.Ifc.get_entity = lambda obj: None
    elif change == "wrong_guid":
        model.by_guid = lambda guid: SimpleNamespace(id=lambda: 99)
    elif change == "wrong_object":
        tool.Ifc.get_object = lambda item: _camera()
    elif change == "duplicate_object":
        duplicate = _camera(_matrix(origin=(9, 8, 7)))
        sys.modules["bpy"].data.objects.append(duplicate)
    elif change == "perspective":
        camera.data.type = "PERSP"
    with pytest.raises(ValueError, match="native|drawing|project|source_id|orthographic"):
        read_camera_binding(camera, role="geometry_author", source_id="fake" if change == "override" else None)


def test_geometry_author_records_project_identity_without_a_display_name_key(monkeypatch):
    """Rename changes display only; the independent source project remains auditable."""
    _runtime(monkeypatch)
    camera = _camera()
    binding = read_camera_binding(camera, role="geometry_author")
    assert binding.provenance["project_global_id"] == "project-A"
    assert binding.provenance["source_step_id"] == 42
    camera.name_full = "Renamed"
    second = read_camera_binding(camera, role="geometry_author")
    assert binding.camera_id == second.camera_id
    assert binding.origin == second.origin and binding.basis == second.basis


def test_full_workflow_rejects_tilt_and_exact_section_rejects_rotated_basis(monkeypatch):
    """Capability checks keep camera pose, B4 cut, Space base and height separate."""
    _runtime(monkeypatch)
    binding = read_camera_binding(_camera(), role="geometry_author")
    tilted = replace(binding, basis=((1, 0, 0), (0, 0, 1), (0, -1, 0)))
    with pytest.raises(ValueError, match="horizontal"):
        plane_from_camera(tilted, name="tilted")
    rotated = replace(binding, basis=((0, 1, 0), (-1, 0, 0), (0, 0, 1)))
    assert plane_from_camera(rotated, name="rotated").basis == rotated.basis
    with pytest.raises(ValueError, match="canonical"):
        plane_from_camera(rotated, name="section", query_kind="exact_world_xy_section")
    assert plane_from_camera(binding, name="whole").origin[2] == 1.6


def _authoring_runtime(monkeypatch, tmp_path, *, unit_scale=1.0):
    """Use real IFC transactions with synthetic Blender resources at the native authoring seam."""
    import ifcopenshell
    import ifcopenshell.api
    from ..adapters import bonsai_analysis_plane as adapter

    class Resource:
        """Supply identity-hashable Blender-like datablocks and properties."""

        def __init__(self, **values):
            """Retain only fields used by the adapter's bounded native recovery."""
            self.__dict__.update(values)

        def select_set(self, selected):
            """Record explicit native selection restoration."""
            self.selected = selected

    class Resources(list):
        """Expose Blender's exact resource removal signature."""

        def remove(self, resource, do_unlink=False):
            """Remove by identity, without name-based cleanup."""
            super().remove(resource)

    class DrawingRows(list):
        """Provide the native drawing-list recovery interface."""

        def add(self):
            """Allocate one drawing row for retained state restoration."""
            row = Resource()
            self.append(row)
            return row

    class Scene(dict):
        """Keep native custom properties separate from scene RNA-like fields."""

    model = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject")
    model.history_size = 64
    data = Resource(**{kind: Resources() for kind in
                      ("objects", "cameras", "meshes", "curves", "collections", "materials")})
    scene = Scene()
    scene.unit_settings = Resource(scale_length=unit_scale)
    scene.camera = None
    scene.cursor = Resource(matrix=_matrix(origin=(0, 0, 0)))
    scene.collection = Resource(children=[])
    view_objects = Resources()
    view_objects.active = None
    view_layer = Resource(objects=view_objects, active_layer_collection=None, update=lambda: None)
    context = Resource(scene=scene, mode="OBJECT", view_layer=view_layer, selected_objects=[])
    bpy = Resource(data=data, context=context, app=Resource(version_string="synthetic"))
    bim_props = Resource(last_transaction="", is_dirty=False)
    spatial_props = Resource(default_container=0)
    drawing_props = Resource(target_view="SECTION_VIEW", location_hint="0", active_drawing_id=0,
                             active_drawing_index=0, current_drawing_index=0, drawings=DrawingRows())
    state = Resource(calls=[], failure=None, storey_hint=None)

    class Store:
        """Mirror the installed wrapper's finalized-error semantics using real IFC undo."""
        current_transaction = ""
        modal_in_progress = False
        history = []
        future = [{"key": "retained-redo", "operations": []}]
        last_transaction = ""
        id_map = {}
        guid_map = {}
        edited_objs = set()

        @staticmethod
        def begin_transaction(operator):
            """Give each owned operation an observable unique history key."""
            operator.transaction_key = f"native-{len(Store.history)}"
            Store.current_transaction = operator.transaction_key

        @staticmethod
        def execute_ifc_operator(operator, native_context):
            """Always finalize the event, including injected native exceptions."""
            Store.begin_transaction(operator)
            key = operator.transaction_key
            bim_props.is_dirty = True
            model.begin_transaction()
            try:
                return operator._execute(native_context)
            finally:
                model.end_transaction()
                Store.history.append({"key": key, "operations": [{"rollback": lambda data: model.undo(), "data": None}]})
                Store.future = []
                Store.last_transaction = bim_props.last_transaction = key
                Store.current_transaction = ""

    def get_entity(obj):
        """Resolve only the currently linked native entity, as Bonsai does."""
        identifier = getattr(getattr(obj, "bim", None), "ifc_definition_id", 0)
        return model.by_id(identifier) if identifier else None

    def native_run(operation, **kwargs):
        """Retain actual property-set persistence and inject failure after marker mutation."""
        result = ifcopenshell.api.run(operation, model, **kwargs)
        if operation == "pset.edit_pset" and state.failure == "marker":
            raise RuntimeError("injected marker failure")
        return result

    class Surveyor:
        """Mirror Bonsai's assumption that Blender translation already uses SI metres."""

        @classmethod
        def get_absolute_matrix(cls, camera):
            """Read the pose without silently adding the scene scale missing from the installed API."""
            import numpy as np
            return np.array(camera.matrix_world, dtype=float)

    class Drawing:
        """Implement the installed creation, assignment and placement method contracts."""
        drawing_selected_states = {}

        @classmethod
        def get_document_props(cls):
            """Expose native operation settings retained in the recovery snapshot."""
            return drawing_props

        @classmethod
        def get_default_drawing_resource_path(cls, kind):
            """Use an existing disposable directory so no real resources are touched."""
            return str(tmp_path / "styles.json")

        @classmethod
        def get_camera_matrix(cls, camera):
            """Return the unchanged normalized synthetic camera pose."""
            return camera.matrix_world

        @classmethod
        def get_drawing_target_view(cls, entity):
            """Label the authored native drawing without depending on its display name."""
            return "PLAN_VIEW"

        @classmethod
        def create_camera(cls, *arguments, **keywords):
            """Allocate a camera with an intentionally different native default elevation."""
            camera_data = Resource(type="ORTHO", ortho_scale=8., clip_start=.1, clip_end=100.)
            camera = Resource(type="CAMERA", name_full="Synthetic camera", library=None,
                matrix_world=_matrix(origin=(11., 12., 4.2)), color=(1, 1, 1, 1), data=camera_data,
                users_collection=[], bim=Resource(ifc_definition_id=0, location_checksum="before",
                    rotation_checksum="before", blender_offset_type="NONE"))
            data.objects.append(camera)
            data.cameras.append(camera_data)
            view_objects.append(camera)
            state.calls.append("create")
            return camera

        @classmethod
        def run_root_assign_class(cls, *, obj, **kwargs):
            """Record initial placement after the adapter's camera-creation hook runs."""
            state.calls.append(("assign_z", obj.matrix_world[2][3]))
            entity = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcAnnotation",
                                        predefined_type="DRAWING")
            obj.bim.ifc_definition_id = entity.id()
            Store.id_map[entity.id()] = obj
            Store.guid_map[entity.GlobalId] = obj
            cls.sync_object_placement(obj)
            if state.failure == "creation":
                raise RuntimeError("injected creation failure")
            return entity

        @classmethod
        def sync_object_placement(cls, camera):
            """Write genuine IFC placement and mutate the same Bonsai pose checksum fields."""
            entity = get_entity(camera)
            matrix = Surveyor.get_absolute_matrix(camera)
            ifcopenshell.api.run("geometry.edit_object_placement", model, product=entity, matrix=matrix)
            camera.bim.location_checksum = repr(tuple(matrix[:3, 3]))
            state.calls.append("sync")
            if state.failure == "update":
                raise RuntimeError("injected update failure")
            return entity

    tool = Resource(Drawing=Drawing, Surveyor=Surveyor, Ifc=Resource(get=lambda: model, get_entity=get_entity,
        get_object=lambda entity: Store.id_map.get(entity.id()), run=native_run, resolve_uri=lambda uri: uri),
        Blender=Resource(get_bim_props=lambda: bim_props, get_object_bim_props=lambda obj: obj.bim),
        Spatial=Resource(get_spatial_props=lambda: spatial_props))
    brick = Resource(history=[], future=[], current_changesets=0, graph=None)

    def add_drawing():
        """Reproduce native create-before-assign ordering in one finalized transaction."""
        def execute(_context):
            """Create and assign exactly one native camera using the installed hook contracts."""
            state.storey_hint = drawing_props.location_hint
            camera = Drawing.create_camera()
            Drawing.run_root_assign_class(obj=camera)
            return {"FINISHED"}
        return Store.execute_ifc_operator(Resource(_execute=execute), context)

    monkeypatch.setitem(sys.modules, "bpy", bpy)
    monkeypatch.setitem(sys.modules, "bonsai", Resource(bbim_semver={"version": "synthetic"}))
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    monkeypatch.setitem(sys.modules, "bonsai.bim.ifc", Resource(IfcStore=Store))
    monkeypatch.setitem(sys.modules, "bonsai.tool.brick", Resource(BrickStore=brick))
    monkeypatch.setattr(adapter, "_invoke_add_drawing", add_drawing)
    return Resource(adapter=adapter, model=model, project=project, bpy=bpy, tool=tool, store=Store,
                    brick=brick, state=state, Resource=Resource)


@pytest.mark.parametrize("unit_scale", [1., .001, 2.])
def test_managed_plane_ensure_is_idempotent_and_native_placement_uses_world_metres(monkeypatch, tmp_path, unit_scale):
    """One marked native identity survives repeat ensure, movement and explicit plane refresh."""
    from ifcopenshell.util.placement import get_local_placement
    runtime = _authoring_runtime(monkeypatch, tmp_path, unit_scale=unit_scale)
    adapter = runtime.adapter
    camera = adapter.ensure_native_analysis_plane(elevation_m=1.6)
    binding = adapter.read_camera_binding(camera, role="geometry_author")
    plane = adapter.plane_from_camera(binding, name="test")
    entity = runtime.tool.Ifc.get_entity(camera)
    assert camera.matrix_world[2][3] == pytest.approx(1.6 / unit_scale)
    assert runtime.state.calls[1] == ("assign_z", 1.6 / unit_scale)
    assert get_local_placement(entity.ObjectPlacement)[2, 3] == pytest.approx(1.6)
    assert adapter.ensure_native_analysis_plane(elevation_m=1.6) is camera
    assert len(runtime.store.history) == 1 and runtime.state.calls.count("create") == 1
    assert adapter.ensure_native_analysis_plane(elevation_m=2.3,
        project_global_id=runtime.project.GlobalId, camera_guid=entity.GlobalId) is camera
    assert get_local_placement(entity.ObjectPlacement)[2, 3] == pytest.approx(2.3)
    updated = adapter.refresh_camera_plane(plane, adapter.read_camera_binding(camera, role="geometry_author"))
    assert updated.identity == plane.identity and updated.revision == 2
    assert updated.origin[:2] == plane.origin[:2] and updated.origin[2] == pytest.approx(2.3)
    assert adapter.refresh_camera_plane(updated, adapter.read_camera_binding(camera, role="geometry_author")) is updated
    assert runtime.state.calls.count("sync") == 2 and len(runtime.store.history) == 2


def test_direct_creation_default_and_storey_hint_remain_compatible(monkeypatch, tmp_path):
    """Ordinary direct creation retains native elevation and does not acquire managed ownership."""
    import ifcopenshell.api
    from ifcopenshell.util.element import get_pset
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    storey = ifcopenshell.api.run("root.create_entity", runtime.model, ifc_class="IfcBuildingStorey")
    runtime.store.id_map[storey.id()] = runtime.Resource()
    camera = runtime.adapter.create_native_drawing(storey_ref=f"ifc-object:{storey.GlobalId}")
    assert camera.matrix_world[2][3] == 4.2
    assert runtime.state.storey_hint == str(storey.id())
    assert get_pset(runtime.tool.Ifc.get_entity(camera), runtime.adapter.MANAGED_PLANE_PSET) is None


def test_explicit_direct_creation_uses_world_metres_without_managed_ownership(monkeypatch, tmp_path):
    """Callers may request SI elevation without opting into the managed singleton lifecycle."""
    from ifcopenshell.util.element import get_pset
    from ifcopenshell.util.placement import get_local_placement
    runtime = _authoring_runtime(monkeypatch, tmp_path, unit_scale=.001)
    camera = runtime.adapter.create_native_drawing(elevation_m=1.6)
    entity = runtime.tool.Ifc.get_entity(camera)
    assert camera.matrix_world[2][3] == 1600.
    assert get_local_placement(entity.ObjectPlacement)[2, 3] == pytest.approx(1.6)
    assert get_pset(entity, runtime.adapter.MANAGED_PLANE_PSET) is None


def test_managed_marker_resolves_after_ifc_only_serialization_without_scene_binding(monkeypatch, tmp_path):
    """Actual IFC bytes retain ownership, while camera relinking remains a synthetic runtime seam."""
    import ifcopenshell
    from ifcopenshell.util.element import get_pset
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    camera = runtime.adapter.ensure_native_analysis_plane(elevation_m=1.6)
    guid = runtime.tool.Ifc.get_entity(camera).GlobalId
    reopened = ifcopenshell.file.from_string(runtime.model.to_string())
    assert get_pset(reopened.by_guid(guid), runtime.adapter.MANAGED_PLANE_PSET)["ProjectGlobalId"] == runtime.project.GlobalId
    runtime.model = reopened
    runtime.tool.Ifc.get = lambda: reopened
    runtime.tool.Ifc.get_entity = lambda obj: reopened.by_guid(guid)
    runtime.tool.Ifc.get_object = lambda entity: camera
    assert not runtime.bpy.context.scene
    assert runtime.adapter.ensure_native_analysis_plane(elevation_m=1.6) is camera


@pytest.mark.parametrize("change", ["duplicate_plane", "duplicate_link", "wrong_project", "explicit_other",
                                    "marker_project", "nonfinite_pose", "tilted_pose"])
def test_managed_plane_rejects_ambiguous_or_unqualified_identity_before_mutation(monkeypatch, tmp_path, change):
    """Persistent ownership never overrides project, native-link or horizontal-pose qualification."""
    import ifcopenshell.api
    from ifcopenshell.util.element import get_pset
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    adapter = runtime.adapter
    camera = adapter.ensure_native_analysis_plane(elevation_m=1.6)
    entity = runtime.tool.Ifc.get_entity(camera)
    arguments = {}
    if change == "duplicate_plane":
        duplicate = ifcopenshell.api.run("root.create_entity", runtime.model, ifc_class="IfcAnnotation", predefined_type="DRAWING")
        pset = ifcopenshell.api.run("pset.add_pset", runtime.model, product=duplicate, name=adapter.MANAGED_PLANE_PSET)
        ifcopenshell.api.run("pset.edit_pset", runtime.model, pset=pset,
            properties={**adapter.MANAGED_PLANE_MARKER, "ProjectGlobalId": runtime.project.GlobalId})
    elif change == "duplicate_link":
        duplicate = runtime.Resource(**camera.__dict__)
        runtime.bpy.data.objects.append(duplicate)
    elif change == "wrong_project":
        arguments["project_global_id"] = "other-project"
    elif change == "explicit_other":
        arguments.update(project_global_id=runtime.project.GlobalId, camera_guid="unrelated")
    elif change == "marker_project":
        pset = runtime.model.by_id(get_pset(entity, adapter.MANAGED_PLANE_PSET)["id"])
        ifcopenshell.api.run("pset.edit_pset", runtime.model, pset=pset, properties={"ProjectGlobalId": "other"})
    elif change == "nonfinite_pose":
        camera.matrix_world = _matrix(origin=(0, 0, float("nan")))
    else:
        camera.matrix_world = ((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 1.6), (0, 0, 0, 1))
    calls, history = list(runtime.state.calls), list(runtime.store.history)
    with pytest.raises(ValueError):
        adapter.ensure_native_analysis_plane(elevation_m=2., **arguments)
    assert runtime.state.calls == calls and runtime.store.history == history


@pytest.mark.parametrize("explicit_identity", [False, True])
@pytest.mark.parametrize("elevation_m", [1.6, 2.3])
def test_managed_reverse_map_cannot_substitute_another_valid_drawing(monkeypatch, tmp_path, explicit_identity, elevation_m):
    """An id-map-only conflict must reject both discovery and explicit GUID reuse before mutation."""
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    adapter = runtime.adapter
    managed = adapter.ensure_native_analysis_plane(elevation_m=1.6)
    entity = runtime.tool.Ifc.get_entity(managed)
    unrelated = adapter.create_native_drawing(elevation_m=1.6)
    unrelated_binding = adapter.read_camera_binding(unrelated, role="geometry_author")
    assert unrelated_binding.camera_id != f"ifc:{entity.GlobalId}"
    # Keep F's reciprocal mapping valid; corrupt only E's reverse lookup as the installed id_map permits.
    runtime.store.id_map[entity.id()] = unrelated
    before = adapter._drawing_snapshot(runtime.bpy, runtime.tool, runtime.store, runtime.brick)
    calls = list(runtime.state.calls)
    arguments = ({"project_global_id": runtime.project.GlobalId, "camera_guid": entity.GlobalId}
                 if explicit_identity else {})
    with pytest.raises(ValueError, match="managed drawing entity/object relationship"):
        adapter.ensure_native_analysis_plane(elevation_m=elevation_m, **arguments)
    assert adapter._drawing_snapshot(runtime.bpy, runtime.tool, runtime.store, runtime.brick) == before
    assert runtime.state.calls == calls


def test_managed_identity_is_rechecked_after_native_placement_and_recovers_conflict(monkeypatch, tmp_path):
    """A post-placement handoff to another independently valid native author cannot report success."""
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    adapter = runtime.adapter
    managed = adapter.ensure_native_analysis_plane(elevation_m=1.6)
    unrelated = adapter.create_native_drawing(elevation_m=1.6)
    unrelated_entity = runtime.tool.Ifc.get_entity(unrelated)
    before = adapter._drawing_snapshot(runtime.bpy, runtime.tool, runtime.store, runtime.brick)
    native_invoke = adapter._invoke_plane_operation

    def relink_after_placement(operator, context):
        """Inject a reciprocal, uniquely linked alternate author after the owned native sync completes."""
        status = native_invoke(operator, context)
        managed.bim.ifc_definition_id = unrelated_entity.id()
        unrelated.bim.ifc_definition_id = 0
        runtime.store.id_map[unrelated_entity.id()] = managed
        assert adapter.read_camera_binding(managed, role="geometry_author").camera_id == f"ifc:{unrelated_entity.GlobalId}"
        return status

    monkeypatch.setattr(adapter, "_invoke_plane_operation", relink_after_placement)
    with pytest.raises(ValueError, match="managed drawing entity/object relationship"):
        adapter.ensure_native_analysis_plane(elevation_m=2.3)
    assert adapter._drawing_snapshot(runtime.bpy, runtime.tool, runtime.store, runtime.brick) == before
    assert not runtime.bpy.context.scene.get("om_analysis_authoring_recovery_error")


@pytest.mark.parametrize("elevation", [float("nan"), float("inf"), -float("inf")])
def test_managed_plane_rejects_nonfinite_elevation_before_creation(monkeypatch, tmp_path, elevation):
    """Invalid caller values do not enter the native transaction boundary."""
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="finite"):
        runtime.adapter.ensure_native_analysis_plane(elevation_m=elevation)
    assert not runtime.store.history and not runtime.bpy.data.objects


@pytest.mark.parametrize("unit_scale", [0., -1., float("nan"), float("inf")])
def test_managed_plane_rejects_invalid_scene_units_before_creation(monkeypatch, tmp_path, unit_scale):
    """A caller's valid metre height cannot compensate for an invalid scene conversion."""
    runtime = _authoring_runtime(monkeypatch, tmp_path, unit_scale=unit_scale)
    with pytest.raises(ValueError, match="scale"):
        runtime.adapter.ensure_native_analysis_plane(elevation_m=1.6)
    assert not runtime.store.history and not runtime.bpy.data.objects


def test_managed_exact_section_rejects_rotated_author_before_elevation_update(monkeypatch, tmp_path):
    """Existing exact-section capability validation runs before any native update."""
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    camera = runtime.adapter.ensure_native_analysis_plane(elevation_m=1.6)
    camera.matrix_world = ((0, -1, 0, 11), (1, 0, 0, 12), (0, 0, 1, 1.6), (0, 0, 0, 1))
    calls, history = list(runtime.state.calls), list(runtime.store.history)
    with pytest.raises(ValueError, match="canonical"):
        runtime.adapter.ensure_native_analysis_plane(elevation_m=2.3, query_kind="exact_world_xy_section")
    assert runtime.state.calls == calls and runtime.store.history == history
    assert camera.matrix_world[2][3] == 1.6


@pytest.mark.parametrize("failure", ["creation", "marker", "update"])
@pytest.mark.parametrize("unit_scale", [1., .001])
def test_managed_plane_owned_failure_restores_ifc_blender_and_history(monkeypatch, tmp_path, failure, unit_scale):
    """Faults after actual native IFC edits restore every retained snapshot field without false success."""
    runtime = _authoring_runtime(monkeypatch, tmp_path, unit_scale=unit_scale)
    adapter = runtime.adapter
    if failure == "update":
        adapter.ensure_native_analysis_plane(elevation_m=1.6)
    before = adapter._drawing_snapshot(runtime.bpy, runtime.tool, runtime.store, runtime.brick)
    runtime.state.failure = failure
    with pytest.raises(RuntimeError, match=f"injected {failure} failure"):
        adapter.ensure_native_analysis_plane(elevation_m=2.3)
    after = adapter._drawing_snapshot(runtime.bpy, runtime.tool, runtime.store, runtime.brick)
    assert after == before
    assert not runtime.bpy.context.scene.get("om_analysis_authoring_recovery_error")
    runtime.state.failure = None
    assert adapter.ensure_native_analysis_plane(elevation_m=2.3) is not None


def test_managed_plane_failed_recovery_blocks_future_authoring(monkeypatch, tmp_path):
    """A native rollback failure remains explicit and blocks subsequent managed operations."""
    runtime = _authoring_runtime(monkeypatch, tmp_path)
    adapter = runtime.adapter
    adapter.ensure_native_analysis_plane(elevation_m=1.6)
    runtime.state.failure = "update"
    def failed_recovery(*args):
        """Inject a verified recovery boundary failure rather than hiding it as success."""
        raise RuntimeError("injected rollback failure")
    monkeypatch.setattr(adapter, "_recover_drawing", failed_recovery)
    with pytest.raises(RuntimeError, match="recovery failed.*rollback failure"):
        adapter.ensure_native_analysis_plane(elevation_m=2.3)
    assert runtime.bpy.context.scene["om_analysis_authoring_recovery_error"] == "injected rollback failure"
    with pytest.raises(ValueError, match="blocked"):
        adapter.ensure_native_analysis_plane(elevation_m=2.3)

