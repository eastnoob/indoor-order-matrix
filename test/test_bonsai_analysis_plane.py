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

