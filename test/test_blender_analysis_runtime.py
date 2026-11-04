"""Concrete asynchronous lifecycle and lightweight import boundary tests."""

from types import SimpleNamespace
from pathlib import Path
import importlib
import json
import os
import subprocess
import sys
import typing

import pytest


def _runtime():
    """Import the addon runtime without requiring native Blender."""
    return importlib.import_module("blender_addon.order_analyzer_ui.runtime")


@pytest.fixture
def runtime():
    """Keep the one process-global slot isolated between tests."""
    module = _runtime()
    module.invalidate_runtime("test reset", new_session=True)
    module.STATE.documents.clear()
    module.STATE.current_result = None
    module.STATE.domain_session = None
    yield module
    module.invalidate_runtime("test cleanup", new_session=True)


def test_native_scale_observation_detects_unit_round_trip(runtime):
    """Scale observation reports both unit changes and restoration without stale state."""
    bpy = SimpleNamespace(context=SimpleNamespace(scene=SimpleNamespace(
        unit_settings=SimpleNamespace(scale_length=1.0))))
    assert runtime.observe_native_scale(bpy_module=bpy) is False
    bpy.context.scene.unit_settings.scale_length = .001
    assert runtime.observe_native_scale(bpy_module=bpy) is True
    bpy.context.scene.unit_settings.scale_length = 1.0
    assert runtime.observe_native_scale(bpy_module=bpy) is True


def test_aba_during_capture_never_publishes_current(runtime):
    """Observed edit and reversal invalidate a frozen job permanently."""
    runtime.STATE.freshness = "current"
    runtime.invalidate_runtime("source changed")
    first = runtime.STATE.observation_epoch
    runtime.invalidate_runtime("source restored")
    assert runtime.STATE.observation_epoch > first
    assert runtime.STATE.freshness in {"stale", "unverified"}
    with pytest.raises(ValueError):
        runtime.prepare_publication({"freshness": "current"})


@pytest.mark.parametrize("reason", ["load", "undo", "file switch", "unregister"])
def test_file_undo_unregister_invalidate_job(runtime, reason):
    """Lifecycle events detach result currentness and invalidate the old session."""
    before = runtime.STATE.runtime_session
    old = object()
    runtime.STATE.current_result = old
    runtime.invalidate_runtime(reason, new_session=True)
    assert runtime.STATE.runtime_session != before
    assert runtime.STATE.current_result is old
    assert runtime.STATE.freshness in {"stale", "unverified"}


def test_furniture_change_stales_occupancy_not_domain_consent(runtime):
    """Resource invalidation must not erase independent structural reducer consent."""
    domain = {"confirmation_binding": {"candidate": "confirmed"}}
    runtime.STATE.domain_session = domain
    runtime.STATE.freshness = "current"
    runtime.invalidate_runtime("furniture changed")
    assert runtime.STATE.domain_session is domain
    assert runtime.STATE.freshness == "stale"


def test_display_change_keeps_semantic_key(runtime):
    """Known presentation changes do not mutate request identity or epoch."""
    epoch = runtime.STATE.observation_epoch
    runtime.invalidate_runtime("display_only")
    assert runtime.STATE.observation_epoch == epoch


def test_cache_request_and_publication_resources_remain_observed(runtime, monkeypatch, tmp_path):
    """Cache/request implementation drift remains a native runtime freshness failure."""
    required = {"adapters/blender_analysis_session.py", "adapters/blender_analysis_result_wire.py",
        "features/analysis_requests.py", "blender_addon/order_analyzer_ui/runtime.py",
        "blender_addon/order_analyzer_ui/__init__.py"}
    assert required <= set(runtime.RESOURCE_PATHS)
    for relative in required:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("original implementation", encoding="utf-8")
    monkeypatch.setattr(runtime, "RESOURCE_PATHS", tuple(required))
    before = runtime._file_stats(tmp_path)
    monkeypatch.setattr(runtime, "_scene_file_token", lambda _context: "scene")
    from types import SimpleNamespace
    job = SimpleNamespace(root=tmp_path, epoch=runtime.STATE.observation_epoch,
        runtime_session=runtime.STATE.runtime_session, context=object(), scene_file_token="scene",
        observation_before={"file_stats": before, "native_guard": {}})
    runtime.STATE.job = job
    monkeypatch.setattr(runtime, "_native_guard", lambda _job: {})
    runtime._check_job(job)
    (tmp_path / "blender_addon/order_analyzer_ui/runtime.py").write_text("changed implementation bytes", encoding="utf-8")
    with pytest.raises(ValueError, match="implementation/config resources changed"):
        runtime._check_job(job)
    runtime.STATE.job = None


def test_native_observation_tracks_grid_axis_without_global_id(runtime, monkeypatch, tmp_path):
    """Non-root IFC objects stay observable without inventing a product GlobalId."""
    axis = SimpleNamespace(id=lambda: 42)
    obj = SimpleNamespace(matrix_world=[[1.0]], parent=None, data=None,
                          modifiers=(), material_slots=())
    model = SimpleNamespace(schema="IFC4", by_type=lambda kind: ())
    store = SimpleNamespace(last_transaction="transaction")
    monkeypatch.setitem(sys.modules, "bonsai.bim.ifc", SimpleNamespace(IfcStore=store))
    monkeypatch.setattr(runtime, "_native_guard", lambda job: {})
    monkeypatch.setattr(runtime, "_file_stats", lambda root: {})
    monkeypatch.setattr(runtime, "RESOURCE_PATHS", ())
    job = SimpleNamespace(root=tmp_path, context=SimpleNamespace(scene=SimpleNamespace(objects=[obj])),
                          capture_job=SimpleNamespace(model=model, tool=SimpleNamespace(
                              Ifc=SimpleNamespace(get_entity=lambda value: axis))))

    def observe():
        """Consume the bounded observer and return its final digest."""
        steps = runtime._native_observation_steps(job)
        while True:
            try:
                next(steps)
            except StopIteration as done:
                return done.value["native_digest"]

    first = observe()
    assert observe() == first
    obj.matrix_world = [[2.0]]
    assert observe() != first
    axis.id = lambda: 43
    assert observe() != first


def test_overlay_only_depsgraph_update_does_not_stale_current_result(runtime):
    """Display mesh updates preserve a freshly committed free-space current result."""
    runtime.STATE.current_result = SimpleNamespace(document={"kind": "free_space_run"})
    runtime.STATE.freshness = "current"
    runtime.STATE.overlay_object = object()
    runtime.invalidate_runtime("display_only")
    assert runtime.STATE.freshness == "current"


def test_load_never_resumes_process(runtime, monkeypatch):
    """Loading and restored-document reads cannot spawn computation."""
    def forbidden(*args, **kwargs):
        """Turn accidental load-time process startup into a hard test failure."""
        raise AssertionError("load spawned process")
    monkeypatch.setattr(runtime.subprocess, "Popen", forbidden)
    runtime.invalidate_runtime("load", new_session=True)
    assert runtime.poll_job() is None


def test_addon_wire_and_capture_import_without_heavy_dependencies(tmp_path):
    """A fresh interpreter must not hide heavy imports behind existing sys.modules."""
    root = Path(__file__).resolve().parents[1]
    code = '''
import sys, importlib.abc
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'shapely','numpy','trimesh','pandas','octa','ifcopenshell','bpy'}:
            raise AssertionError('heavy import: ' + fullname)
sys.meta_path.insert(0, Block())
import adapters.blender_analysis_result_wire
import adapters.blender_analysis_capture
import blender_addon.order_analyzer_ui.runtime
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_runtime_rejects_command_payload_and_invalid_root_before_spawn(runtime, tmp_path):
    """Trust boundary validates fixed paths and rejects executable selection."""
    for payload in ({"kind": "free_space_run", "executable": "bad"}, {"kind": "free_space_run"}):
        with pytest.raises(ValueError):
            runtime.start_job(repo_root=tmp_path, bpy_context=None, payload=payload)
    assert runtime.STATE.job is None


def test_start_job_preserves_authored_domain_identity_in_free_space_binding(runtime, monkeypatch, tmp_path):
    """Free-space Start freezes retained IfcSpace, storey, and support identities for the child."""
    root = tmp_path
    (root / "outputs").mkdir()
    monkeypatch.setattr(runtime, "_paths", lambda value: (root, root / "python.exe"))
    monkeypatch.setattr(runtime, "_scene_file_token", lambda _context: "scene-token")
    monkeypatch.setattr(runtime.capture, "begin_analysis_capture",
                        lambda **_kwargs: SimpleNamespace(stage="capturing", diagnostics=[]))
    def observation_steps(_job):
        """Provide a closeable no-op observation generator for the start boundary."""
        if False:
            yield None
    monkeypatch.setattr(runtime, "_native_observation_steps", observation_steps)
    runtime.STATE.observation_hooks_active = True
    runtime.STATE.domain_context = {"structural": "context"}
    runtime.STATE.domain_session = {
        "domain_request_identity": "request-1", "session_revision": 4,
        "confirmation_binding": {"source_revision": "source-1"},
        "analysis_domain": {"id": "space-domain"}, "domain_geometries": (),
        "current": {"status": "active"},
        "authored_domain": {"source_id": "space-guid", "provenance": {"level_ref": "ifc-object:storey-guid"}},
        "support_binding": {"source_object_id": "floor-guid"},
    }
    payload = {"kind": "free_space_run", "request": {"domain": {"id": "space-domain"}},
               "domain_geometries": ()}
    runtime.start_job(repo_root=root, bpy_context=SimpleNamespace(scene=object()), payload=payload)
    assert runtime.STATE.job.payload["job_binding"]["domain_source_id"] == "space-guid"
    assert runtime.STATE.job.payload["job_binding"]["storey_ref"] == "ifc-object:storey-guid"
    assert runtime.STATE.job.payload["job_binding"]["support_source_id"] == "floor-guid"


def test_region_manifest_update_keeps_pending_recheck_job_observable(runtime, monkeypatch):
    """The Text write made by Recheck cannot trip its just-created job guard."""
    import blender_addon.order_analyzer_ui as addon

    class RNA:
        """Expose Blender's datablock type identifier."""
        identifier = "Text"

    class RegionText:
        """Expose exactly the owned manifest tags written by the runtime."""
        bl_rna = RNA()
        def get(self, key, default=None):
            """Read one addon ownership tag."""
            return {"om_analysis_owner": "order_analyzer", "om_analysis_role": "region_list"}.get(key, default)

    job = SimpleNamespace(epoch=17, runtime_session="recheck-session", scene_file_token="scene-token",
                          context=SimpleNamespace(), observation_before=None, lifecycle="capturing")
    runtime.STATE.observation_epoch = 17
    runtime.STATE.runtime_session = "recheck-session"
    runtime.STATE.job = job
    monkeypatch.setattr(runtime, "_scene_file_token", lambda _context: "scene-token")
    update = SimpleNamespace(updates=(SimpleNamespace(id=RegionText()),))
    try:
        # This is the decision made by the registered depsgraph callback before
        # `poll_job()` calls `_check_job()` for its observe-start lifecycle.
        if not addon._depsgraph_updates_are_neutral(update):
            runtime.invalidate_runtime("scene changed")
        runtime._check_job(job)
        assert runtime.STATE.job is job
        assert runtime.STATE.observation_epoch == 17
    finally:
        runtime.STATE.job = None


def test_native_capture_topology_histogram_round_trips_at_request_boundary(runtime):
    """Normalize native integer histogram bins without weakening strict JSON keys."""
    raw_capture = {
        "records": [{"mesh": {"quality": {"edge_face_counts": {1: 4, 2: 7}}}}],
        "identity": {"project_global_id": "project"},
        "diagnostics": [],
        "observation": {"scene_token": "scene"},
        "capture_id": "capture",
        "capture_complete": True,
    }
    from ..adapters import blender_analysis_result_wire as wire

    with pytest.raises(ValueError, match="object keys must be strings"):
        wire.document_digest(raw_capture)

    normalized = runtime._canonical_capture_for_request(raw_capture)
    encoded = wire.canonical_json(normalized)
    restored = wire.load_json(encoded)
    assert restored["records"][0]["mesh"]["quality"]["edge_face_counts"] == [
        {"face_count": 1, "edge_count": 4}, {"face_count": 2, "edge_count": 7}]


@pytest.mark.parametrize("histogram", [
    {True: 4}, {-1: 4}, {"1": 4}, {1: True}, {1: -1},
    [{"face_count": True, "edge_count": 4}],
    [{"face_count": 1, "edge_count": -1}],
    [{"face_count": 1, "edge_count": 4, "extra": 0}],
    [{"face_count": 1, "edge_count": 4}, {"face_count": 1, "edge_count": 8}],
    [{"face_count": 1, "edge_count": 4}, {"face_count": "2", "edge_count": 8}],
])
def test_native_capture_topology_histogram_rejects_malformed_bins(runtime, histogram):
    """Malformed or ambiguous histogram bins fail with the strict boundary error."""
    with pytest.raises(ValueError):
        runtime._canonical_capture_for_request({
            "records": [{"mesh": {"quality": {"edge_face_counts": histogram}}}]})


def test_native_capture_topology_histogram_sorts_explicit_records(runtime):
    """Already-recordized bins remain canonical and deterministically ordered."""
    normalized = runtime._canonical_capture_for_request({
        "records": [{"mesh": {"quality": {"edge_face_counts": [
            {"face_count": 2, "edge_count": 7}, {"face_count": 1, "edge_count": 4}]}}}]})
    assert normalized["records"][0]["mesh"]["quality"]["edge_face_counts"] == [
        {"face_count": 1, "edge_count": 4}, {"face_count": 2, "edge_count": 7}]


def test_background_thread_cannot_touch_runtime(runtime):
    """Even native-free calls refuse the wrong thread before accessing job state."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError):
            pool.submit(runtime.poll_job).result()


def test_failed_publication_retains_previous_result(runtime):
    """Malformed or incomplete staging cannot destroy previously displayed truth."""
    old = object()
    runtime.STATE.current_result = old
    with pytest.raises(ValueError):
        runtime.prepare_publication({"kind": "free_space_run", "freshness": "current"})
    assert runtime.STATE.current_result is old


def _native_job(runtime, monkeypatch, tmp_path, *, running=False, auto_publish=False):
    """Use real capture and wire/CLI execution with explicit synthetic native/process edges."""
    from .test_blender_analysis_capture import runtime as native_fixture
    from .test_b3_live_scene_capture import unknown_quality
    from ..adapters import blender_analysis_session as service
    from ..adapters.bonsai_live import StructuralContext
    from .test_analysis_requests import _plane
    import shutil
    context, entities, evaluated = native_fixture(monkeypatch)
    bpy = sys.modules["bpy"]
    bpy.context = context
    sys.modules["bonsai.bim.ifc"].IfcStore.last_transaction = "txn-one"
    monkeypatch.setattr(runtime.capture, "topology_quality", unknown_quality)
    root = tmp_path / "root"
    source_root = Path(__file__).resolve().parents[1]
    for relative in runtime.RESOURCE_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, path)
    python = root / ".pixi/envs/default/python.exe"
    python.parent.mkdir(parents=True)
    shutil.copyfile(sys.executable, python)
    children = []
    class Child:
        """Simulate only the OS child boundary; the real service generates result bytes."""
        def __init__(self, args, **kwargs):
            """Execute the real data payload and retain owned-process lifecycle facts."""
            assert args[1:3] == ["-m", "adapters.blender_analysis_session"]
            assert kwargs["shell"] is False and kwargs["cwd"] == str(root)
            self.args, self.kwargs = args, kwargs
            self.returncode = None if running else 0
            self.terminated = self.killed = False
            payload = runtime.wire.load_json(Path(args[-2]).read_text(encoding="utf-8"))
            document = service._execute_workflow_payload(payload)
            runtime.wire.write_result_atomic(document, path=Path(args[-1]))
            children.append(self)
        def poll(self):
            """Return an OS-like nonblocking exit observation."""
            return self.returncode
        def terminate(self):
            """Record graceful termination without implicitly releasing the slot."""
            self.terminated = True
        def kill(self):
            """Model the OS child finally exiting after escalation."""
            self.killed, self.returncode = True, -9
    monkeypatch.setattr(runtime.subprocess, "Popen", Child)
    runtime.STATE.observation_hooks_active = True
    payload = {"kind": "domain_session", "context": StructuralContext.from_plane(_plane()).to_dict(),
               "prior": None, "action": None}
    runtime.start_job(repo_root=root, bpy_context=context, payload=payload, auto_publish=auto_publish)
    return root, context, children


def _pump_until(runtime, stage):
    """Bound fake-native tests by callback count without sleeping on real timers."""
    for _ in range(1000):
        job = runtime.poll_job()
        if runtime.STATE.job is None or job.stage == stage:
            return job
    raise AssertionError("runtime pump did not reach " + stage)


def test_native_capture_process_and_staged_commit(runtime, monkeypatch, tmp_path):
    """Real capture/service bytes reach one staged commit with independently observed freshness."""
    root, context, children = _native_job(runtime, monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        runtime.start_job(repo_root=root, bpy_context=context, payload={"kind": "domain_session"})
    job = _pump_until(runtime, "awaiting_publication")
    assert job.error is None and job.candidate is not None
    assert runtime.STATE.current_result is None
    runtime.commit_publication(job.candidate, native_artifacts={})
    assert runtime.STATE.job is None and runtime.STATE.lifecycle == "complete"
    assert runtime.STATE.freshness == "current"
    assert runtime.STATE.current_result is job.candidate
    assert len(children) == 1 and len(runtime.STATE.documents) == 1
    assert job.metrics["json_bytes"] > 0 and job.metrics["max_object_seconds"] >= 0
    diagnostics = runtime.wire.load_json((job.directory / "terminal_diagnostics.json").read_text(encoding="utf-8"))
    for stage in ("finalize", "request_normalize", "request_digest", "write"):
        assert diagnostics["metrics"]["stage_seconds"][stage] > 0
        assert diagnostics["metrics"]["stage_max_callback_seconds"][stage] > 0


def test_completed_child_auto_publication_is_once_and_terminal(runtime, monkeypatch, tmp_path):
    """A completed child commits once, clears the slot, and makes later polls inert."""
    _, context, children = _native_job(runtime, monkeypatch, tmp_path, auto_publish=True)
    calls = 0
    while runtime.STATE.job is not None and calls < 1000:
        runtime.poll_job()
        calls += 1
    assert runtime.STATE.job is None
    assert runtime.STATE.lifecycle == "complete"
    assert runtime.STATE.current_result is not None
    assert len(runtime.STATE.documents) == 1


def test_direct_publication_prepares_and_validates_once(runtime, monkeypatch, tmp_path):
    """The staged path carries one validated immutable candidate into manual commit."""
    root, _, children = _native_job(runtime, monkeypatch, tmp_path)
    job = _pump_until(runtime, "process")
    counts = {"validate": 0, "prepare": 0}
    original_validate, original_prepare = runtime.wire.validate_document, runtime.prepare_publication

    def validate(document):
        """Count runtime wire validation without changing its behavior."""
        counts["validate"] += 1
        return original_validate(document)

    def prepare(document):
        """Count preparation while retaining the existing guard."""
        counts["prepare"] += 1
        return original_prepare(document)

    monkeypatch.setattr(runtime.wire, "validate_document", validate)
    monkeypatch.setattr(runtime, "prepare_publication", prepare)
    children[0].returncode = 0
    staged = _pump_until(runtime, "awaiting_publication")
    assert staged.candidate is job.candidate
    assert counts == {"validate": 1, "prepare": 1}
    runtime.commit_publication(staged.candidate, native_artifacts={})
    assert runtime.STATE.job is None
    assert runtime.poll_job() is None
    assert counts == {"validate": 1, "prepare": 1}


def test_native_overlay_replacement_is_free_space_only_and_idempotent(runtime, monkeypatch):
    """Free-space publication replaces one display mesh while Domain stays mesh-free."""
    from .test_blender_analysis_overlay import _document
    from ..adapters import blender_analysis_result_wire as wire
    import blender_addon.order_analyzer_ui.overlay as overlay
    calls, removed = [], []
    class Objects:
        """Track native object removal for the replacement boundary."""
        def remove(self, value, **kwargs):
            removed.append((value, kwargs))
            value.removed = True
    class Meshes:
        """Track native mesh removal for the replacement boundary."""
        def remove(self, value):
            removed.append(value)
    bpy = SimpleNamespace(data=SimpleNamespace(objects=Objects(), meshes=Meshes()))
    monkeypatch.setattr(overlay, "build_native_mesh", lambda result, bpy_module: calls.append(result) or SimpleNamespace(data="mesh"))
    free = wire.ValidatedAnalysisResult(_document())
    domain = SimpleNamespace(document={"kind": "domain_session"})
    assert runtime._replace_native_overlay(domain, bpy_module=bpy) is None
    class OldObject:
        """Invalidate object data after removal like Blender StructRNA handles."""
        def __init__(self):
            self.removed = False
            self._mesh = "old-mesh"
        @property
        def data(self):
            """Expose mesh before removal and reject access after object removal."""
            if self.removed:
                raise RuntimeError("StructRNA of type Object has been removed")
            return self._mesh
    runtime.STATE.overlay_object = OldObject()
    first = runtime._replace_native_overlay(free, bpy_module=bpy)
    runtime.STATE.overlay_object = first
    second = runtime._replace_native_overlay(free, bpy_module=bpy)
    assert first is not None and second is not None and len(calls) == 2
    assert len(removed) == 4


@pytest.mark.parametrize("shared_scene", [False, True])
def test_reopened_overlay_replacement_preserves_other_scene_objects(runtime, monkeypatch, shared_scene):
    """Saved overlays are replaced without a cached handle or deleting another scene's display."""
    from .test_blender_analysis_overlay import _document
    from ..adapters import blender_analysis_result_wire as wire
    import blender_addon.order_analyzer_ui.overlay as overlay

    class Object(dict):
        """Represent Blender's persistent ownership tags and native mesh reference."""
        def __init__(self, owner, role, scenes):
            """Keep object identity distinct from equal custom-property mappings."""
            super().__init__(om_analysis_owner=owner, om_analysis_role=role)
            self.data = SimpleNamespace(users=1)
            self.users_scene = scenes

    class Objects(list):
        """Release the removed object's mesh and current-scene links."""
        def remove(self, value, *, do_unlink):
            """Model Blender removal without touching objects in other scenes."""
            assert do_unlink
            self[:] = [item for item in self if item is not value]
            scene.objects[:] = [item for item in scene.objects if item is not value]
            value.data.users -= 1

    scene, other_scene = SimpleNamespace(objects=[]), SimpleNamespace()
    saved = Object("order_analyzer", "overlay", (scene, other_scene) if shared_scene else (scene,))
    unrelated = Object("another_addon", "overlay", (scene,))
    other = Object("order_analyzer", "overlay", (other_scene,))
    objects = Objects([saved, unrelated, other])
    scene.objects[:] = [saved, unrelated]
    meshes = [saved.data, unrelated.data, other.data]
    bpy = SimpleNamespace(context=SimpleNamespace(scene=scene), data=SimpleNamespace(objects=objects, meshes=meshes))

    def build_mesh(result, *, bpy_module):
        """Simulate only the native creation boundary unavailable in Pixi Python."""
        replacement = Object("order_analyzer", "overlay", (scene,))
        objects.append(replacement)
        scene.objects.append(replacement)
        meshes.append(replacement.data)
        return replacement

    monkeypatch.setattr(overlay, "build_native_mesh", build_mesh)
    runtime.STATE.overlay_object = None
    candidate = wire.ValidatedAnalysisResult(_document())
    if shared_scene:
        with pytest.raises(ValueError, match="shared with another scene"):
            runtime._replace_native_overlay(candidate, bpy_module=bpy)
        assert len(objects) == 3 and len(scene.objects) == 2
    else:
        replacement = runtime._replace_native_overlay(candidate, bpy_module=bpy)
        assert len(scene.objects) == 2
        assert any(item is replacement for item in scene.objects)
        assert all(item is not saved for item in objects)
        assert all(mesh is not saved.data for mesh in meshes)
    assert any(item is unrelated for item in objects)
    assert any(item is other for item in objects)


def test_view_layer_flush_runs_before_currentness_and_later_object_updates_stale(runtime):
    """Queued native updates are flushed before currentness; later source edits still stale."""
    events = []
    class ViewLayer:
        """Simulate Blender's queued depsgraph flush boundary."""
        def update(self):
            """Record the flush without changing the committed result."""
            events.append("flush")
            runtime.invalidate_runtime("scene changed")
    bpy = SimpleNamespace(context=SimpleNamespace(view_layer=ViewLayer()))
    runtime._flush_native_view_layer(bpy_module=bpy)
    runtime.STATE.current_result = SimpleNamespace(document={"kind": "free_space_run"})
    runtime.STATE.freshness = "current"
    assert events == ["flush"] and runtime.STATE.freshness == "current"
    runtime.invalidate_runtime("scene changed")
    assert runtime.STATE.freshness == "stale"


def test_auto_publication_prepares_and_commits_once(runtime, monkeypatch, tmp_path):
    """The native auto path commits the same prepared candidate exactly once."""
    root, _, children = _native_job(runtime, monkeypatch, tmp_path, auto_publish=True)
    job = _pump_until(runtime, "process")
    counts = {"validate": 0, "prepare": 0, "commit": 0}
    original_validate, original_prepare = runtime.wire.validate_document, runtime.prepare_publication
    original_commit = runtime.commit_publication

    def validate(document):
        """Count one result validation."""
        counts["validate"] += 1
        return original_validate(document)

    def prepare(document):
        """Count one publication preparation."""
        counts["prepare"] += 1
        return original_prepare(document)

    def commit(candidate, *, native_artifacts):
        """Count one terminal publication commit."""
        counts["commit"] += 1
        return original_commit(candidate, native_artifacts=native_artifacts)

    monkeypatch.setattr(runtime.wire, "validate_document", validate)
    monkeypatch.setattr(runtime, "prepare_publication", prepare)
    monkeypatch.setattr(runtime, "commit_publication", commit)
    children[0].returncode = 0
    while runtime.STATE.job is not None:
        runtime.poll_job()
    assert counts == {"validate": 1, "prepare": 1, "commit": 1}
    for _ in range(5):
        assert runtime.poll_job() is None
    assert len(runtime.STATE.documents) == 1


def test_operator_style_auto_commit_updates_addon_runtime_state(runtime, monkeypatch, tmp_path):
    """The addon-facing runtime identity observes the committed Domain session."""
    import blender_addon.order_analyzer_ui as addon

    root, _, children = _native_job(runtime, monkeypatch, tmp_path, auto_publish=True)
    addon._RUNTIME_MODULE = runtime
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: root)
    while runtime.STATE.job is not None:
        runtime.poll_job()
    addon_runtime = addon._runtime()
    assert addon_runtime is runtime
    assert addon_runtime.STATE.domain_session is not None
    assert "candidates" in addon_runtime.STATE.domain_session
    assert children[0].returncode == 0


def test_child_launch_uses_validated_root_for_job_and_module_resolution(runtime, monkeypatch, tmp_path):
    """Installed-module location cannot redirect job output or child imports."""
    monkeypatch.setattr(runtime, "__file__", str(tmp_path / "installed" / "runtime.py"))
    root, context, children = _native_job(runtime, monkeypatch, tmp_path, running=True)
    job = _pump_until(runtime, "process")
    child = children[0]
    assert job.root == root.resolve()
    assert job.directory.is_relative_to(root / "outputs" / "blender_analysis" / "jobs")
    assert child.kwargs["cwd"] == str(root)
    assert child.kwargs["env"]["PYTHONPATH"].split(os.pathsep)[0] == str(root)
    assert Path(child.args[0]).resolve().is_relative_to(root)
    assert Path(child.args[-2]).is_relative_to(job.directory)
    assert Path(child.args[-1]).is_relative_to(job.directory)
    children[0].returncode = -9
    runtime.cancel_job()
    runtime.poll_job()


def test_child_environment_loads_fixed_pixi_python_from_stripped_environment(runtime):
    """A real fixed-environment subprocess loads native packages without ambient Pixi state."""
    root = Path(__file__).resolve().parents[1]
    env_root = root / ".pixi" / "envs" / "default"
    inherited = {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
                 "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
                 "PATH": "system-path-sentinel"}
    environment = runtime._child_environment(root, inherited)
    result = subprocess.run([str(env_root / "python.exe"), "-c", "import shapely; print('loaded')"],
                            cwd=root, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "loaded"
    assert environment["CONDA_PREFIX"] == str(env_root.resolve())
    assert "system-path-sentinel" in environment["PATH"]


def test_child_environment_deduplicates_windows_path_identity(runtime):
    """Validated prefixes remain first while repeated inherited entries collapse by identity."""
    root = Path(__file__).resolve().parents[1]
    env_root = root / ".pixi" / "envs" / "default"
    inherited_entries = [
        str(env_root).upper() + "\\",
        str(env_root / "Library" / "bin").replace("\\", "/"),
        "C:\\Windows",
        "c:/windows/",
        "",
        "D:\\unrelated",
    ]
    environment = runtime._child_environment(root, {"PATH": os.pathsep.join(inherited_entries)})
    entries = environment["PATH"].split(os.pathsep)
    identities = [runtime._windows_path_identity(entry) for entry in entries]
    assert len(identities) == len(set(identities))
    assert entries[:2] == [str(env_root.resolve()), str((env_root / "Library" / "mingw-w64" / "bin").resolve())]
    assert identities.count(runtime._windows_path_identity("C:\\Windows")) == 1
    assert entries[-1] == "D:\\unrelated"


def test_nonzero_child_persists_complete_terminal_diagnostics(runtime, monkeypatch, tmp_path):
    """A failed child retains return code, launch context and both terminal streams."""
    root, context, children = _native_job(runtime, monkeypatch, tmp_path, running=True)
    job = _pump_until(runtime, "process")
    (job.directory / "stdout.log").write_text("child out", encoding="utf-8")
    (job.directory / "stderr.log").write_text("child err", encoding="utf-8")
    children[0].returncode = 7
    finished = runtime.poll_job()
    assert finished is job and runtime.STATE.job is None
    diagnostics = runtime.wire.load_json((job.directory / "terminal_diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["returncode"] == 7
    assert diagnostics["stdout"] == "child out"
    assert diagnostics["stderr"] == "child err"
    assert str(root) == diagnostics["cwd"]
    assert '"returncode":7' in job.error
    assert diagnostics["metrics"]["stage_seconds"]["request_digest"] > 0
    assert '"metrics":' not in job.error


def test_child_launch_exception_persists_launch_diagnostics(runtime, monkeypatch, tmp_path):
    """A Popen failure retains the configured launch context and exception text."""
    root, context, _ = _native_job(runtime, monkeypatch, tmp_path, running=True)
    job = _pump_until(runtime, "write")

    def fail(*args, **kwargs):
        """Model an OS launch rejection after request creation."""
        raise OSError("launch denied")

    monkeypatch.setattr(runtime.subprocess, "Popen", fail)
    finished = runtime.poll_job()
    assert finished is job and runtime.STATE.job is None
    diagnostics = runtime.wire.load_json((job.directory / "terminal_diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["launch_error"] == "OSError: launch denied"
    assert diagnostics["returncode"] is None
    assert diagnostics["cwd"] == str(root)
    assert "launch denied" in job.error


def test_cancel_keeps_owned_slot_until_child_exit(runtime, monkeypatch, tmp_path):
    """Cancel cannot free the process slot early or replace old truth."""
    root, context, children = _native_job(runtime, monkeypatch, tmp_path, running=True)
    old = object()
    runtime.STATE.current_result = old
    job = _pump_until(runtime, "process")
    runtime.cancel_job()
    runtime.poll_job()
    assert children[0].terminated and runtime.STATE.job is job
    job.cancel_started -= runtime.CANCEL_GRACE_SECONDS + 1
    runtime.poll_job()
    runtime.poll_job()
    assert children[0].killed and runtime.STATE.job is None
    assert runtime.STATE.current_result is old and runtime.STATE.lifecycle == "interrupted"


@pytest.mark.parametrize("edit", ["aba", "config", "transaction", "load"])
def test_running_job_rejects_changed_native_or_config_binding(runtime, monkeypatch, tmp_path, edit):
    """Content-equal ABA, fixed file changes and native transaction edits cannot publish old work."""
    root, context, children = _native_job(runtime, monkeypatch, tmp_path, running=True)
    old = object()
    runtime.STATE.current_result = old
    job = _pump_until(runtime, "process")
    if edit == "aba":
        runtime.invalidate_runtime("parent changed")
        runtime.invalidate_runtime("parent restored")
    elif edit == "load":
        runtime.invalidate_runtime("load", new_session=True)
    elif edit == "config":
        (root / "pixi.toml").write_text("changed", encoding="utf-8")
    else:
        sys.modules["bonsai.bim.ifc"].IfcStore.last_transaction = "txn-two"
    children[0].returncode = 0
    _pump_until(runtime, "awaiting_publication")
    assert runtime.STATE.job is None and runtime.STATE.current_result is old
    assert runtime.STATE.freshness in {"stale", "unverified"}


@pytest.mark.parametrize("edit", ["event", "transaction", "config"])
def test_publication_edit_after_staging_preserves_old_truth(runtime, monkeypatch, tmp_path, edit):
    """A native construction yield cannot bypass the final sticky token guard."""
    root, _, _ = _native_job(runtime, monkeypatch, tmp_path)
    old = object()
    runtime.STATE.current_result = old
    job = _pump_until(runtime, "awaiting_publication")
    if edit == "event":
        runtime.invalidate_runtime("plane changed")
    elif edit == "transaction":
        sys.modules["bonsai.bim.ifc"].IfcStore.last_transaction = "after-native-build"
    else:
        (root / "pixi.toml").write_text("changed after staging", encoding="utf-8")
    with pytest.raises(ValueError):
        runtime.commit_publication(job.candidate, native_artifacts={})
    runtime.poll_job()
    assert runtime.STATE.current_result is old


def test_free_space_start_requires_retained_confirmed_domain(runtime, monkeypatch, tmp_path):
    """A payload's invented confirmation cannot replace the shared retained B4 session."""
    from .test_analysis_requests import _request, _scene
    root, context, _ = _native_job(runtime, monkeypatch, tmp_path)
    job = _pump_until(runtime, "awaiting_publication")
    runtime.commit_publication(job.candidate, native_artifacts={})
    scene = _scene()
    with pytest.raises(ValueError):
        runtime.start_job(repo_root=root, bpy_context=context, payload={"kind": "free_space_run",
            "request": _request(scene).to_dict(), "domain_geometries": [scene.geometries[0].to_dict()],
            "job_binding": {"confirmation_binding": {"invented": True}}})
    assert runtime.STATE.job is None


def test_save_copy_refuses_live_or_existing_target_and_records_only_success(runtime, tmp_path):
    """Save Copy validates a new path and records the artifact only after native success."""
    class WM:
        def save_as_mainfile(self, *, filepath, copy):
            """Create the requested copy for the success branch."""
            assert copy is True
            Path(filepath).write_bytes(b"blend")

    bpy = SimpleNamespace(ops=SimpleNamespace(wm=WM()))
    live = tmp_path / "live.blend"
    live.write_bytes(b"live")
    with pytest.raises(ValueError):
        runtime.save_copy(target=live, live_path=live, bpy_module=bpy)
    target = tmp_path / "copy.blend"
    artifacts = []
    runtime.save_copy(target=target, live_path=live, bpy_module=bpy, artifact_log=artifacts)
    assert target.read_bytes() == b"blend" and artifacts == [str(target)]
    with pytest.raises(FileExistsError):
        runtime.save_copy(target=target, live_path=live, bpy_module=bpy, artifact_log=artifacts)


def test_save_copy_failure_cleans_only_owned_partial(runtime, tmp_path):
    """Native failure leaves the live file and unrelated files untouched."""
    class WM:
        def save_as_mainfile(self, *, filepath, copy):
            """Fail after the runtime has created its owned partial marker."""
            raise RuntimeError("native save failed")

    bpy = SimpleNamespace(ops=SimpleNamespace(wm=WM()))
    live = tmp_path / "live.blend"
    unrelated = tmp_path / "unrelated.txt"
    live.write_bytes(b"live")
    unrelated.write_bytes(b"keep")
    with pytest.raises(RuntimeError):
        runtime.save_copy(target=tmp_path / "failed.blend", live_path=live, bpy_module=bpy)
    assert live.read_bytes() == b"live" and unrelated.read_bytes() == b"keep"
    assert not list(tmp_path.glob("*.partial")) and not list(tmp_path.glob(".*.partial"))


def test_addon_register_unregister_reuses_exact_class_objects(monkeypatch):
    """Registration is identity-stable and repeated registration creates one panel set."""
    import blender_addon.order_analyzer_ui as addon

    class Operator:
        """Fake Blender operator base."""
    class Panel:
        """Fake Blender panel base."""
    class Scene:
        """Fake Blender scene type."""
    registered = []
    fake_bpy = SimpleNamespace(
            types=SimpleNamespace(Operator=Operator, Panel=Panel, Scene=Scene, AddonPreferences=Operator),
        context=SimpleNamespace(preferences=SimpleNamespace(addons={})),
        props=SimpleNamespace(BoolProperty=lambda **kwargs: kwargs.get("default"),
                              FloatProperty=lambda **kwargs: kwargs.get("default"),
                              IntProperty=lambda **kwargs: kwargs.get("default"),
                              StringProperty=lambda **kwargs: "object",
                              EnumProperty=lambda **kwargs: kwargs.get("default"),),
        utils=SimpleNamespace(register_class=lambda cls: (typing.get_type_hints(cls), registered.append(cls))[1],
                              unregister_class=lambda cls: registered.remove(cls)),
        app=SimpleNamespace(timers=SimpleNamespace(register=lambda *args, **kwargs: None,
                                                   is_registered=lambda timer: True,
                                                   unregister=lambda timer: None),
                            handlers=SimpleNamespace(load_post=[], undo_post=[], depsgraph_update_post=[])),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setattr(addon, "_configured_repo_root",
                        lambda context=None: (_ for _ in ()).throw(ValueError("project root could not be found automatically")))
    addon._REGISTERED = False
    addon._REGISTERED_CLASSES = ()
    addon.register()
    first = tuple(registered)
    addon.register()
    assert tuple(registered) == first
    refresh = next(cls for cls in registered if getattr(cls, "bl_idname", "") == "om_analysis.b4_refresh")()
    messages = []
    refresh.report = lambda _levels, message: messages.append(message)
    assert refresh.execute(fake_bpy.context) == {"CANCELLED"}
    assert "project root" in messages[-1].lower()
    addon.unregister()
    assert registered == []
    assert addon._REGISTERED_CLASSES == ()


def test_exact_section_request_uses_absolute_plane_origin_z(monkeypatch):
    """The exact section query takes world Z from the analyzer-owned plane once."""
    from blender_addon.order_analyzer_ui import _make_analysis_request, _set_camera_plane
    from .test_analysis_requests import _request, _scene
    from .test_blender_analysis_ui import _camera_ui_fixture
    context, _current, _runtime = _camera_ui_fixture(monkeypatch, elevation=4.2)
    _set_camera_plane(context, "adopt")
    scene = context.scene
    scene.om_analysis_query_kind = "exact_world_xy_section"
    domain = _request(_scene()).domain.to_dict()
    request = _make_analysis_request(scene, domain,
                                     ({"vertices": ((0.0, 0.0, 0.0), (1.0, 1.0, 0.0))},))
    assert request.geometry_query.kind == "exact_world_xy_section"
    assert request.geometry_query.world_z_m == 4.2


def test_save_copy_is_blocked_after_unverified_native_recovery(runtime, tmp_path):
    """An authoring recovery error prevents creating any automatic save artifact."""
    calls = []
    bpy = SimpleNamespace(context=SimpleNamespace(scene={"om_analysis_authoring_recovery_error": "test failure"}),
        ops=SimpleNamespace(wm=SimpleNamespace(save_as_mainfile=lambda **kwargs: calls.append(kwargs))))
    with pytest.raises(ValueError, match="recovery failed"):
        runtime.save_copy(target=tmp_path / "blocked.blend", bpy_module=bpy)
    assert not calls and not list(tmp_path.iterdir())


def test_duplicate_uuid_requires_explicit_reassignment_and_preserves_history(runtime):
    """Duplicate plane identity cannot silently reuse a result or UUID."""
    runtime.STATE.current_result = object()
    action = runtime.reassign_duplicate_plane_uuid(plane_uuid="plane", new_uuid="plane-copy",
                                                   existing_plane_uuids=("plane", "other"))
    assert action == {"action": "reassign_duplicate_plane", "old_plane_uuid": "plane",
                      "new_plane_uuid": "plane-copy", "revision": 1}
    assert runtime.STATE.freshness == "historical"
    with pytest.raises(ValueError):
        runtime.reassign_duplicate_plane_uuid(plane_uuid="plane", new_uuid="other",
                                               existing_plane_uuids=("plane", "other"))


def test_capture_gap_change_cannot_become_observation_baseline(runtime, monkeypatch, tmp_path):
    """A native/IFC edit after finalize is compared with the pre-capture token."""
    root, context, _ = _native_job(runtime, monkeypatch, tmp_path)
    original_finalize_steps = runtime.capture.finalize_capture_steps
    def finalize_then_edit(job):
        """Inject the reviewed capture-to-observation race at the exact boundary."""
        result = yield from original_finalize_steps(job)
        sys.modules["bonsai.bim.ifc"].IfcStore.last_transaction = "txn-after-capture"
        return result
    monkeypatch.setattr(runtime.capture, "finalize_capture_steps", finalize_then_edit)
    old = object()
    runtime.STATE.current_result = old
    for _ in range(1000):
        if runtime.STATE.job is None:
            break
        runtime.poll_job()
    else:
        raise AssertionError("capture-gap job did not terminate")
    assert runtime.STATE.job is None
    assert runtime.STATE.current_result is old
    assert runtime.STATE.freshness in {"stale", "unverified"}


def test_cooperative_transport_preserves_exact_bytes_and_digest(runtime, tmp_path):
    """Large-array transport must yield and match the existing canonical JSON byte contract."""
    from .test_blender_analysis_capture import _consume_steps

    raw = {"identity": {"name": "\u00e9"}, "records": [{"mesh": {
        "vertices": [[float(i), -0.0, 1e-100] for i in range(8000)],
        "quality": {"edge_face_counts": {2: 7, 1: 4}}}}],
        "diagnostics": [], "observation": {}, "capture_id": "capture", "capture_complete": True}
    expected = runtime.capture.plain(raw)
    expected["records"][0]["mesh"]["quality"]["edge_face_counts"] = [
        {"face_count": 1, "edge_count": 4}, {"face_count": 2, "edge_count": 7}]
    expected = runtime.wire.plain(expected)
    result, yields = _consume_steps(runtime._canonical_capture_for_request_steps(raw))
    assert yields > 10
    assert result == expected
    result["records"][0]["mesh"]["vertices"][0][0] = 99
    assert raw["records"][0]["mesh"]["vertices"][0][0] == 0
    job = runtime.RuntimeJob("job", tmp_path, None, {"kind": "domain_session"}, tmp_path,
                             0, "session", "file")
    job.captured = raw
    job.observation_before = {"resources": {}, "native_digest": "native"}
    _, yields = _consume_steps(runtime._write_request_steps(job))
    assert yields > 10
    assert job.binding["capture_digest"] == runtime.wire.document_digest(expected)
    expected_payload = {"kind": "domain_session", "job_binding": job.binding, "canonical_capture": expected}
    assert (tmp_path / "request.json").read_bytes() == runtime.wire.canonical_json(expected_payload).encode("utf-8")
    expected["digest"] = "ignored"
    hashed, _ = _consume_steps(runtime._document_digest_steps(expected))
    assert hashed == runtime.wire.document_digest(expected)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object(), {1: "bad key"}])
def test_cooperative_transport_validates_deep_array_leaves(runtime, value):
    """Chunking cannot skip invalid values near the end of a large mesh."""
    from .test_blender_analysis_capture import _consume_steps

    raw = {"records": [{"mesh": {"vertices": [[0., 0., 0.] for _ in range(3000)] + [value]}}]}
    with pytest.raises(ValueError):
        _consume_steps(runtime._canonical_capture_for_request_steps(raw))


@pytest.mark.parametrize("stage", ["finalize", "request_normalize", "request_digest", "write"])
@pytest.mark.parametrize("change", ["cancel", "aba"])
def test_cooperative_stages_cancel_without_child_or_publication(runtime, monkeypatch, tmp_path, stage, change):
    """Cancellation or an edit/revert during partial work must permanently stop the job."""
    _, _, children = _native_job(runtime, monkeypatch, tmp_path)
    job = _pump_until(runtime, "capture")
    mesh_result = runtime.capture.extract_evaluated_mesh

    def large_mesh(*args, **kwargs):
        """Keep native extraction real while enlarging only its detached test data."""
        mesh = mesh_result(*args, **kwargs)
        mesh["vertices"] = [[float(i), 0., 0.] for i in range(8000)]
        return mesh

    monkeypatch.setattr(runtime.capture, "extract_evaluated_mesh", large_mesh)
    monkeypatch.setattr(runtime, "BUDGET_SECONDS", .0005)
    job = _pump_until(runtime, stage)
    assert job.stage == stage and job.error is None
    runtime.poll_job()
    assert job.stage == stage
    old = object()
    runtime.STATE.current_result = old
    if change == "cancel":
        runtime.cancel_job()
        runtime.poll_job()
    else:
        runtime.invalidate_runtime("source changed")
        runtime.invalidate_runtime("source restored")
    assert runtime.STATE.job is None
    assert not children
    assert runtime.STATE.current_result is old
    assert runtime.STATE.freshness != "current"
    assert job.lifecycle == "interrupted" and job.iterator is None
    assert job.metrics["stage_seconds"][stage] >= job.metrics["stage_max_callback_seconds"][stage] > 0
    if stage == "write":
        # The writer's context manager must release even a partially written request.
        with (job.directory / "request.json").open("ab") as stream:
            stream.write(b"\n")

