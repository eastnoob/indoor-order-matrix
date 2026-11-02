"""Focused tests for the configured addon handoff and Start payload boundary."""

from types import SimpleNamespace
from types import MappingProxyType
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import blender_addon.order_analyzer_ui as addon
from blender_addon.order_analyzer_ui import _configured_repo_root, _request_binding_payload


def _camera_ui_fixture(monkeypatch, *, elevation=2.5):
    """Provide an independently observed native camera at the addon boundary."""
    from adapters import bonsai_analysis_plane as cameras
    from blender_addon.order_analyzer_ui import runtime
    observation = cameras.CameraBinding(camera_id="ifc:camera-A", role="geometry_author",
        origin=(4.0, 6.0, elevation), basis=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        display={"name": "Drawing A"}, provenance={"project_global_id": "project-A",
        "source_ifc_global_id": "camera-A", "geometry_author_qualified": True})
    current = {"observation": observation}
    camera = SimpleNamespace(type="CAMERA")
    scene = SimpleNamespace(om_analysis_plane_binding_json="", om_analysis_plane_reviewed=False,
        om_analysis_plane_uuid="", om_analysis_plane_revision=1, om_analysis_plane_origin_z=0.0,
        om_analysis_query_kind="whole_height_projection", om_analysis_storey_ref="",
        om_analysis_selected_version_id="old-selection", om_analysis_grid_spacing=0.25)
    context = SimpleNamespace(scene=scene, active_object=camera)
    monkeypatch.setattr(cameras, "read_camera_binding", lambda obj, **kwargs: current["observation"])
    monkeypatch.setattr(cameras, "resolve_camera_binding", lambda **kwargs: current["observation"])
    monkeypatch.setattr(cameras, "create_native_drawing", lambda **kwargs: camera)
    monkeypatch.setattr(runtime, "STATE", runtime.RuntimeState(current_result=object(),
        documents=[{"history": True}], domain_session={"confirmation_binding": {"action_id": "old"}}))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    return context, current, runtime


@pytest.mark.parametrize("action", ["adopt", "new"])
def test_native_camera_actions_adopt_exact_pose_and_revoke_consent(monkeypatch, action):
    """Both explicit entrances preserve history and keep native camera Z separate from B4."""
    context, current, runtime = _camera_ui_fixture(monkeypatch)
    history = runtime.STATE.current_result
    addon._set_camera_plane(context, action)
    plane = addon._analysis_plane(context.scene)
    assert plane.origin == (4, 6, 2.5) and plane.revision == 1
    assert context.scene.om_analysis_plane_reviewed is True
    assert runtime.STATE.domain_session is None
    assert runtime.STATE.current_result is history and runtime.STATE.documents == [{"history": True}]
    assert context.scene.om_analysis_selected_version_id == ""
    assert current["observation"].origin == plane.origin


def test_native_camera_refresh_detects_motion_and_keeps_identity(monkeypatch):
    """Movement requires an explicit refresh and never changes query or silently restores consent."""
    from dataclasses import replace
    context, current, runtime = _camera_ui_fixture(monkeypatch)
    addon._set_camera_plane(context, "adopt")
    first = addon._analysis_plane(context.scene)
    current["observation"] = replace(current["observation"], origin=(4, 6, 3.5))
    with pytest.raises(ValueError, match="refresh"):
        addon._analysis_plane(context.scene)
    addon._set_camera_plane(context, "refresh")
    updated = addon._analysis_plane(context.scene)
    assert updated.identity == first.identity and updated.revision == 2
    assert updated.origin[2] == 3.5 and context.scene.om_analysis_query_kind == "whole_height_projection"
    assert runtime.STATE.domain_session is None


def test_native_camera_reopen_and_project_replacement_require_recheck(monkeypatch):
    """Persisted observations cannot authorize a new session or a different project."""
    from dataclasses import replace
    context, current, _runtime = _camera_ui_fixture(monkeypatch)
    addon._set_camera_plane(context, "adopt")
    context.scene.om_analysis_plane_reviewed = False
    with pytest.raises(ValueError, match="review|refresh"):
        addon._analysis_plane(context.scene)
    addon._set_camera_plane(context, "refresh")
    current["observation"] = replace(current["observation"], provenance={
        **current["observation"].provenance, "project_global_id": "other-project"})
    with pytest.raises(ValueError, match="project"):
        addon._set_camera_plane(context, "refresh")


def test_readopting_same_camera_preserves_revision_history(monkeypatch):
    """The adopt entrance must not reset a previously observed camera revision."""
    from dataclasses import replace
    context, current, _runtime = _camera_ui_fixture(monkeypatch)
    addon._set_camera_plane(context, "adopt")
    first = addon._analysis_plane(context.scene)
    current["observation"] = replace(current["observation"], origin=(4, 6, 3.5))
    addon._set_camera_plane(context, "adopt")
    updated = addon._analysis_plane(context.scene)
    assert updated.identity == first.identity and updated.revision == first.revision + 1
    addon._set_camera_plane(context, "adopt")
    assert addon._analysis_plane(context.scene).revision == updated.revision


def test_free_space_panel_displays_exact_plane_space_and_authored_targets(monkeypatch):
    """Users see captured group membership and query without inferring groups from labels."""
    context, _current, runtime = _camera_ui_fixture(monkeypatch)
    addon._set_camera_plane(context, "adopt")
    context.scene.om_analysis_space_source_id = "space-A"
    runtime.STATE.current_result = SimpleNamespace(document={"binding": {"authored_groups": [
        {"id": "ifc-group:G", "member_refs": ["ifc-object:A", "ifc-object:B"]}]}})
    labels, properties = [], []
    layout = SimpleNamespace(label=lambda **kw: labels.append(kw["text"]),
        prop=lambda _scene, name, **kw: properties.append(name), operator=lambda *a, **kw: None)
    layout.row = lambda **kw: layout
    addon._draw_free_space(layout, context.scene, runtime)
    assert "Space: space-A" in labels
    assert "Group ifc-group:G: ifc-object:A, ifc-object:B" in labels
    assert any("revision 1" in text and "2.5 m" in text for text in labels)
    assert "om_analysis_query_kind" in properties


def test_plane_never_falls_back_to_manual_world_z():
    """Legacy manual Z fields cannot impersonate a reviewed native drawing."""
    scene = SimpleNamespace(om_analysis_plane_origin_z=3.0, om_analysis_plane_uuid="manual")
    with pytest.raises(ValueError, match="camera|drawing"):
        addon._analysis_plane(scene)


def test_make_analysis_request_ground_band_uses_plane_local_bounds(monkeypatch):
    """The ground-to-plane option maps world ground into local plane Z."""
    from features.scene_contract import AnalysisDomain
    context, _current, _runtime = _camera_ui_fixture(monkeypatch)
    addon._set_camera_plane(context, "adopt")
    scene = context.scene
    scene.om_analysis_query_kind = "ground_to_analysis_plane_band"
    domain = AnalysisDomain.from_dict({"id": "domain", "geometry_refs": (), "source_id": None,
                                      "selection_method": "test", "provenance": {}, "uncertainties": ()})
    monkeypatch.setattr(addon, "_grid_coverage", lambda *_args, **_kwargs: ((0.0, 0.0), 1, 1))
    request = addon._make_analysis_request(scene, domain)
    assert request.geometry_query.kind == "finite_height_band"
    assert request.geometry_query.height_band == (-2.5, 0.0)


def test_camera_grid_coverage_uses_translated_rotated_plane_coordinates(monkeypatch):
    """A valid native camera frame must cover the world domain in plane-local sampling coordinates."""
    from dataclasses import replace
    from features.scene_contract import AnalysisDomain
    context, current, _runtime = _camera_ui_fixture(monkeypatch)
    current["observation"] = replace(current["observation"], basis=((0, 1, 0), (-1, 0, 0), (0, 0, 1)))
    addon._set_camera_plane(context, "adopt")
    domain = AnalysisDomain.from_dict({"id": "domain", "geometry_refs": (), "source_id": None,
                                      "selection_method": "test", "provenance": {}, "uncertainties": ()})
    meshes = ({"vertices": ((4.0, 6.0, 0.0), (6.0, 9.0, 0.0))},)
    request = addon._make_analysis_request(context.scene, domain, meshes)
    assert request.sampling.origin == (0.0, -2.0)
    assert request.sampling.n_rows == 8 and request.sampling.n_cols == 12


def test_five_panels_are_siblings_and_same_category():
    """The Analyzer workbench exposes five native sibling panels."""
    class Panel:
        """Fake Blender panel base."""

    fake_bpy = SimpleNamespace(types=SimpleNamespace(Panel=Panel))
    classes = addon._panel_classes(fake_bpy)
    assert [cls.__name__ for cls in classes] == [
        "OM_ANALYSIS_PT_plane", "OM_ANALYSIS_PT_region", "OM_ANALYSIS_PT_free_space",
        "OM_ANALYSIS_PT_b4", "OM_ANALYSIS_PT_results"]
    assert all(cls.bl_space_type == "VIEW_3D" for cls in classes)
    assert all(cls.bl_region_type == "UI" for cls in classes)
    assert all(cls.bl_category == "Analyzer" for cls in classes)
    assert all(getattr(cls, "bl_parent_id", "") == "" for cls in classes)
    assert all("DEFAULT_CLOSED" in cls.bl_options for cls in classes)


def test_register_unregister_keeps_one_runtime_and_reverses_panel_lifecycle(monkeypatch):
    """Registration installs all panels and unregister removes them cleanly."""
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
        data=SimpleNamespace(texts=[]),
        props=SimpleNamespace(BoolProperty=lambda **kw: kw.get("default"), FloatProperty=lambda **kw: kw.get("default"),
                              IntProperty=lambda **kw: kw.get("default"), StringProperty=lambda **kw: kw.get("default", ""),
                              EnumProperty=lambda **kw: kw.get("default")),
        utils=SimpleNamespace(register_class=lambda cls: registered.append(cls), unregister_class=lambda cls: registered.remove(cls)),
        app=SimpleNamespace(timers=SimpleNamespace(register=lambda *a, **kw: None, is_registered=lambda _t: True,
                                                    unregister=lambda _t: None),
                            handlers=SimpleNamespace(load_post=[], undo_post=[], depsgraph_update_post=[])),
    )
    runtime = SimpleNamespace(STATE=SimpleNamespace(observation_hooks_active=False),
                              invalidate_runtime=lambda *a, **kw: None, reap_owned_job=lambda: None)
    monkeypatch.setattr(addon, "_bpy", lambda: fake_bpy)
    monkeypatch.setattr(addon, "_runtime", lambda context=None: runtime)
    monkeypatch.setattr(addon, "_restore_region_overlay", lambda *a, **kw: None)
    addon._REGISTERED = False
    addon._REGISTERED_CLASSES = ()
    addon.register()
    assert [cls.__name__ for cls in registered if cls.__name__.startswith("OM_ANALYSIS_PT_")] == [
        "OM_ANALYSIS_PT_plane", "OM_ANALYSIS_PT_region", "OM_ANALYSIS_PT_free_space", "OM_ANALYSIS_PT_b4", "OM_ANALYSIS_PT_results"]
    addon.unregister()
    assert not [cls for cls in registered if cls.__name__.startswith("OM_ANALYSIS_PT_")]


def _bpy_with_root(root):
    """Build the smallest fake Blender preference surface used by root resolution."""
    preferences = SimpleNamespace(addons={addon.__package__: SimpleNamespace(
        preferences=SimpleNamespace(repo_root=str(root)))})
    return SimpleNamespace(context=SimpleNamespace(preferences=preferences))


def test_configured_repo_root_uses_addon_preference(monkeypatch, tmp_path):
    """Installed package location is ignored in favor of the explicit preference."""
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    monkeypatch.setattr(addon, "_bpy", lambda: _bpy_with_root(tmp_path))
    assert _configured_repo_root() == tmp_path.resolve()


def test_configured_repo_root_uses_registered_addon_key(monkeypatch, tmp_path):
    """Installed Blender registration uses order_analyzer_ui as the preference key."""
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    preferences = SimpleNamespace(addons={"order_analyzer_ui": SimpleNamespace(
        preferences=SimpleNamespace(repo_root=str(tmp_path)))})
    fake_bpy = SimpleNamespace(context=SimpleNamespace(preferences=preferences))
    monkeypatch.setattr(addon, "_bpy", lambda: fake_bpy)
    assert _configured_repo_root() == tmp_path.resolve()


def test_configured_repo_root_rejects_missing_preference(monkeypatch):
    """An unavailable project remains an actionable root-resolution error."""
    monkeypatch.chdir("C:/Windows")
    monkeypatch.setattr(addon, "__file__", "C:/Windows/order_analyzer_ui/__init__.py")
    fake = SimpleNamespace(context=SimpleNamespace(preferences=SimpleNamespace(addons={})))
    monkeypatch.setattr(addon, "_bpy", lambda: fake)
    with pytest.raises(ValueError, match="could not be found"):
        _configured_repo_root()


def test_action_runtime_requires_root_then_loads_configured_runtime(monkeypatch, tmp_path):
    """Project runtime loading stays deferred until a project root is available."""
    monkeypatch.chdir("C:/Windows")
    monkeypatch.setattr(addon, "__file__", "C:/Windows/order_analyzer_ui/__init__.py")
    fake = SimpleNamespace(context=SimpleNamespace(preferences=SimpleNamespace(addons={})))
    monkeypatch.setattr(addon, "_bpy", lambda: fake)
    with pytest.raises(ValueError, match="could not be found"):
        addon._action_runtime()
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    monkeypatch.setattr(addon, "_bpy", lambda: _bpy_with_root(tmp_path))
    runtime = addon._action_runtime()
    assert runtime.STATE.observation_hooks_active is True


def test_addon_uses_one_runtime_module_identity(monkeypatch, tmp_path):
    """Operator, timer and direct package access share the committed runtime state."""
    import importlib
    import blender_addon.order_analyzer_ui as addon

    root = tmp_path
    (root / "pixi.toml").write_text("", encoding="utf-8")
    runtime = importlib.import_module("blender_addon.order_analyzer_ui.runtime")
    addon._RUNTIME_MODULE = None
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: root)
    assert addon._runtime() is addon._runtime()
    assert addon._runtime().STATE is runtime.STATE


def test_start_binding_payload_preserves_existing_session_records():
    """Start forwards existing binding records without creating or rewriting them."""
    support = {"source_object_id": "ifc-object:floor"}
    legacy = ({"legacy_object_id": "legacy-floor"},)
    assert _request_binding_payload({"support_binding": support, "legacy_bindings": legacy}) == {
        "support_binding": support, "legacy_bindings": legacy}
    assert _request_binding_payload({}) == {"support_binding": None, "legacy_bindings": ()}


def test_panel_shows_terminal_failure_before_domain_controls(monkeypatch):
    """A capture failure is visible even when no Domain session was produced."""
    runtime = SimpleNamespace(STATE=SimpleNamespace(job=None, last_job=SimpleNamespace(error="capture failed")))
    monkeypatch.setattr(addon, "_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_draw_domain", lambda *args: None)
    monkeypatch.setattr(addon, "_draw_free_space", lambda *args: None)
    panel = addon._panel_classes(SimpleNamespace(types=SimpleNamespace(Panel=object)))[-1]()
    labels = []
    panel.layout = SimpleNamespace(label=lambda **kwargs: labels.append(kwargs))
    panel.draw(SimpleNamespace(scene=object()))
    assert labels == [{"text": "capture failed", "icon": "ERROR"}]


def test_analyze_spaces_operator_preserves_scope_and_entrypoint(monkeypatch, tmp_path):
    """The formal Space entrypoint submits the shared Domain job with scope facts."""
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    class Operator:
        """Fake Blender operator base."""
    captured = {}
    events = []
    runtime = SimpleNamespace(
        STATE=SimpleNamespace(domain_session={"cached": True}),
        _flush_native_view_layer=lambda: events.append("flush"),
        invalidate_domain_session=lambda reason: events.append(reason),
        start_job=lambda **kwargs: captured.update(kwargs),
    )
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                                context=SimpleNamespace(preferences=SimpleNamespace(addons={})))
    monkeypatch.setattr(addon, "_bpy", lambda: fake_bpy)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_action_runtime", lambda context=None: runtime)
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene: {"scope": "frozen"})
    monkeypatch.setattr(addon, "_selected_storey_datum_z_m", lambda _ref: 0.0)
    cls = next(item for item in addon._operator_classes(fake_bpy)
               if item.bl_idname == "om_analysis.analyze_spaces")
    op = cls()
    scene = SimpleNamespace(om_analysis_storey_ref="ifc-object:storey", om_analysis_support_source_id="slab")
    assert op.execute(SimpleNamespace(scene=scene)) == {"FINISHED"}
    assert events == ["flush", "whole-storey analysis requested"]
    payload = captured["payload"]
    assert payload["kind"] == "domain_session"
    assert payload["entrypoint"] == "analyze_spaces"
    assert payload["storey_ref"] == "ifc-object:storey"
    assert payload["support_source_id"] == "slab"
    assert payload["prior"] is None
    assert scene.om_analysis_selected_wall_refs_json == ""


def test_slab_datum_sets_b4_base_and_cut_without_requiring_storey_selection(monkeypatch):
    """Slab-only scope derives one native storey while camera Z and cut offset remain separate."""
    monkeypatch.setattr(addon, "_space_datum", lambda scene: {"storey_ref": "ifc-object:S", "datum_z_m": .2})
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: Path.cwd())
    scene = SimpleNamespace(om_analysis_datum_mode="slab", om_analysis_storey_ref="",
        om_analysis_plane_uuid="P", om_b4_tolerance_mm2=4., om_analysis_b4_cut_offset=1.2)
    context = addon._structural_context_payload(scene)
    assert context["storey_ref"] == "ifc-object:S"
    assert context["datum_z_m"] == .2 and context["cut_z_m"] == pytest.approx(1.4)
    assert context["b4_parameters"]["tolerance_mm2"] == 4.
    assert context["selected_wall_refs"] == [] or context["selected_wall_refs"] == ()


def test_manual_height_ui_does_not_require_authored_quantity(monkeypatch):
    """The selected manual value and unit reach the one native height resolver."""
    import types
    from .test_bonsai_space_authoring import native_model

    model, _storey, ref = native_model()
    monkeypatch.setitem(sys.modules, "bonsai.tool", types.SimpleNamespace(Ifc=SimpleNamespace(get=lambda: model)))
    monkeypatch.setitem(sys.modules, "bonsai", types.SimpleNamespace(tool=sys.modules["bonsai.tool"]))
    scene = SimpleNamespace(om_analysis_height_mode="manual", om_analysis_manual_height=3200., om_analysis_height_unit="mm")
    result = addon._space_height(scene, ref)
    assert result["height_m"] == 3.2 and result["unit_source"] == "manual"


def test_analyze_spaces_refuses_missing_storey_datum_before_starting_job(monkeypatch):
    """The Analyze entry reports the authored datum prerequisite before launching work."""
    class Operator:
        """Fake Blender operator base."""

    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session=None))
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator))
    monkeypatch.setattr(addon, "_action_runtime", lambda context=None: runtime)
    monkeypatch.setattr(addon, "_selected_storey_datum_z_m",
                        lambda _ref: (_ for _ in ()).throw(ValueError(
                            "Selected storey has no placement or elevation. Set its Elevation in Bonsai > Object Attributes, then retry Analyze spaces")))
    cls = next(item for item in addon._operator_classes(fake_bpy)
               if item.bl_idname == "om_analysis.analyze_spaces")
    op = cls()
    reports = []
    op.report = lambda *args: reports.append(args)
    scene = SimpleNamespace(om_analysis_storey_ref="ifc-object:storey", om_analysis_support_source_id="")
    assert op.execute(SimpleNamespace(scene=scene)) == {"CANCELLED"}
    assert "Set its Elevation in Bonsai > Object Attributes" in reports[0][1]


def _native_storey_ui_fixture(monkeypatch, prefix=None):
    """Supply an actual IFC storey and project units at the UI's native seam."""
    import types
    from .test_bonsai_space_authoring import native_model

    model, storey, ref = native_model(prefix)
    tool = types.ModuleType("bonsai.tool")
    tool.Ifc = SimpleNamespace(get=lambda: model)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: Path.cwd())
    return model, storey, ref


def test_selected_storey_builds_explicit_elevated_b4_context_without_moving_projection(monkeypatch):
    """Native placement sets B4 datum/cut while the camera keeps its independent elevation."""
    import numpy as np
    import ifcopenshell.api.geometry

    model, storey, ref = _native_storey_ui_fixture(monkeypatch, "MILLI")
    matrix = np.eye(4)
    matrix[2, 3] = 21.
    ifcopenshell.api.geometry.edit_object_placement(model, product=storey, matrix=matrix)
    camera_context, _current, _runtime = _camera_ui_fixture(monkeypatch, elevation=99.)
    addon._set_camera_plane(camera_context, "adopt")
    scene = camera_context.scene
    scene.om_analysis_storey_ref = ref
    scene.om_b4_tolerance_mm2 = 1.
    context = addon._structural_context_payload(scene)
    assert context["storey_ref"] == ref and context["datum_z_m"] == 21.
    assert context["cut_z_m"] == 22.5 and addon._analysis_plane(scene).origin[2] == 99.


def test_selected_storey_without_height_facts_refuses_with_bonsai_guidance(monkeypatch):
    """An absent placement/elevation remains unavailable rather than becoming zero."""
    _model, storey, ref = _native_storey_ui_fixture(monkeypatch)
    storey.ObjectPlacement = None
    storey.Elevation = None
    with pytest.raises(ValueError, match="placement or elevation"):
        addon._selected_storey_datum_z_m(ref)


@pytest.mark.parametrize("prefix,elevation,expected", [("MILLI", 21000., 21.), (None, 0., 0.)])
def test_selected_storey_elevation_is_converted_from_project_units(monkeypatch, prefix, elevation, expected):
    """Explicit zero and native millimetres follow the same shared conversion path."""
    _model, storey, ref = _native_storey_ui_fixture(monkeypatch, prefix)
    storey.ObjectPlacement = None
    storey.Elevation = elevation
    assert addon._selected_storey_datum_z_m(ref) == expected


def test_selected_storey_nonfinite_native_height_refuses_b4_context(monkeypatch):
    """Invalid native elevation cannot become a usable B4 datum."""
    _model, storey, ref = _native_storey_ui_fixture(monkeypatch)
    storey.ObjectPlacement = None
    with pytest.raises(RuntimeError, match="finite"):
        storey.Elevation = float("nan")
    with pytest.raises(ValueError, match="placement or elevation"):
        addon._selected_storey_datum_z_m(ref)


def test_space_job_status_displays_stage_and_error():
    """The Space panel exposes lifecycle/stage and terminal error from the shared job."""
    labels = []
    layout = SimpleNamespace(label=lambda **kwargs: labels.append(kwargs), operator=lambda *args, **kwargs: None)
    job = SimpleNamespace(lifecycle="running", stage="process", error="worker failed", metrics={})
    addon._draw_space_job_status(layout, SimpleNamespace(STATE=SimpleNamespace(job=job, last_job=None)))
    assert labels[0]["text"] == "Analyzing; please wait · process"
    assert labels[1] == {"text": "worker failed", "icon": "ERROR"}


def test_draw_regions_uses_persisted_scene_token(monkeypatch):
    """Region history lookup follows the persisted scene identity across pointer changes."""
    class Scene:
        """Expose a persisted custom-property token and a misleading RNA pointer."""
        om_analysis_regions_expanded = True
        om_analysis_active_region_id = ""

        def get(self, key, default=None):
            """Read the persisted scene token."""
            return {"om_analysis_scene_token": "scene-token"}.get(key, default)

        def as_pointer(self):
            """Expose a pointer that must not be used for persistence."""
            return 987654

    scene = Scene()
    calls = []
    runtime = SimpleNamespace(find_region_manifest=lambda **kwargs: calls.append(kwargs) or {"records": ()})
    layout = SimpleNamespace(prop=lambda *args, **kwargs: None,
                             label=lambda *args, **kwargs: None,
                             operator=lambda *args, **kwargs: SimpleNamespace(),
                             row=lambda **kwargs: SimpleNamespace(operator=lambda *args, **kwargs: SimpleNamespace(),
                                                                  label=lambda *args, **kwargs: None))
    addon._draw_regions(layout, scene, runtime, SimpleNamespace(scene=scene))
    assert calls == [{"scene_token": "scene-token"}]


def test_register_persists_load_handler_and_restores_open_file_regions(monkeypatch):
    """Registration wraps load handlers persistently and rebuilds the open-file GPU cache."""
    class Operator:
        """Fake Blender operator base."""

    class Panel:
        """Fake Blender panel base."""

    class Scene:
        """Fake Blender scene type."""

    registered = []
    persistent_calls = []
    timer_calls = []

    def persistent(handler):
        """Mark a handler as persistent while preserving its callable behavior."""
        def wrapped(*args, **kwargs):
            return handler(*args, **kwargs)
        wrapped.original = handler
        persistent_calls.append(handler)
        return wrapped

    scene = SimpleNamespace(get=lambda key, default=None: {
        "om_analysis_scene_token": "scene-token"}.get(key, default))
    fake_bpy = SimpleNamespace(
        types=SimpleNamespace(Operator=Operator, Panel=Panel, Scene=Scene, AddonPreferences=Operator),
        context=SimpleNamespace(scene=scene, preferences=SimpleNamespace(addons={})),
        data=SimpleNamespace(texts=[]),
        props=SimpleNamespace(BoolProperty=lambda **kwargs: kwargs.get("default"),
                              FloatProperty=lambda **kwargs: kwargs.get("default"),
                              IntProperty=lambda **kwargs: kwargs.get("default"),
                              StringProperty=lambda **kwargs: "object",
                              EnumProperty=lambda **kwargs: kwargs.get("default")),
        utils=SimpleNamespace(register_class=lambda cls: registered.append(cls),
                               unregister_class=lambda cls: registered.remove(cls)),
        app=SimpleNamespace(timers=SimpleNamespace(register=lambda *args, **kwargs: timer_calls.append((args, kwargs)),
                                                   is_registered=lambda timer: True,
                                                   unregister=lambda timer: None),
                            handlers=SimpleNamespace(load_post=[], undo_post=[], depsgraph_update_post=[],
                                                      persistent=persistent)),
    )
    def invalidate_domain_session(_reason):
        """Drop the retained session when the native file changes."""
        runtime.STATE.domain_session = None

    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session={"retained": True}),
                              find_region_manifest=lambda **kwargs: {"records": ({"region_id": "r1"},),
                                                                     "active_region_id": "r1"},
                              invalidate_domain_session=invalidate_domain_session,
                              invalidate_runtime=lambda *args, **kwargs: None,
                              reap_owned_job=lambda: None)
    restored = []
    from blender_addon.order_analyzer_ui import region_overlay
    monkeypatch.setattr(addon, "_bpy", lambda: fake_bpy)
    monkeypatch.setattr(addon, "_runtime", lambda context=None: runtime)
    monkeypatch.setattr(addon, "_REGISTERED", False)
    monkeypatch.setattr(addon, "_REGISTERED_CLASSES", ())
    monkeypatch.setattr(region_overlay, "set_records",
                        lambda records, selected_id=None: restored.append((tuple(records), selected_id)))

    addon.register()
    assert len(persistent_calls) == 3
    assert timer_calls and timer_calls[0][1]["persistent"] is True
    assert fake_bpy.app.handlers.load_post[0].original is persistent_calls[0]
    assert fake_bpy.app.handlers.undo_post[0].original is persistent_calls[1]
    assert fake_bpy.app.handlers.depsgraph_update_post[0].original is persistent_calls[2]
    assert restored == [(({"region_id": "r1"},), "r1")]
    assert runtime.STATE.domain_session == {"retained": True}
    fake_bpy.app.handlers.load_post[0]()
    assert runtime.STATE.domain_session is None
    addon.unregister()
    assert fake_bpy.app.handlers.load_post == []
    assert fake_bpy.app.handlers.undo_post == []
    assert fake_bpy.app.handlers.depsgraph_update_post == []


def test_register_skips_overlay_restore_without_scene_context(monkeypatch):
    """Addon enablement from Blender's restricted context defers scene-bound restore."""
    class Runtime:
        """Expose state and lifecycle hooks needed by registration teardown."""
        STATE = SimpleNamespace(domain_session={"retained": True})

        def find_region_manifest(self, **_kwargs):
            """Fail if registration incorrectly queries a missing scene."""
            raise AssertionError("scene-bound restore ran without a scene")

        def invalidate_runtime(self, *_args, **_kwargs):
            """Accept teardown invalidation."""

        def reap_owned_job(self):
            """Accept teardown reaping."""

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
        data=SimpleNamespace(texts=[]),
        props=SimpleNamespace(BoolProperty=lambda **kwargs: kwargs.get("default"),
                              FloatProperty=lambda **kwargs: kwargs.get("default"),
                              IntProperty=lambda **kwargs: kwargs.get("default"),
                              StringProperty=lambda **kwargs: "object",
                              EnumProperty=lambda **kwargs: kwargs.get("default")),
        utils=SimpleNamespace(register_class=lambda cls: registered.append(cls),
                               unregister_class=lambda cls: registered.remove(cls)),
        app=SimpleNamespace(timers=SimpleNamespace(register=lambda *args, **kwargs: None,
                                                   is_registered=lambda timer: True,
                                                   unregister=lambda timer: None),
                            handlers=SimpleNamespace(load_post=[], undo_post=[], depsgraph_update_post=[])),
    )
    runtime = Runtime()
    monkeypatch.setattr(addon, "_bpy", lambda: fake_bpy)
    monkeypatch.setattr(addon, "_runtime", lambda context=None: runtime)
    monkeypatch.setattr(addon, "_REGISTERED", False)
    monkeypatch.setattr(addon, "_REGISTERED_CLASSES", ())
    addon.register()
    assert runtime.STATE.domain_session == {"retained": True}
    addon.unregister()
    assert registered == []


def test_start_accepts_immutable_active_domain_and_rejects_plain_invalid_object(monkeypatch):
    """Start trusts immutable mapping sessions while refusing non-mapping state."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(
        types=SimpleNamespace(Operator=Operator),
        props=SimpleNamespace(StringProperty=lambda **kwargs: ""),
    )
    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session=None), start_job=lambda **kwargs: None)
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: Path.cwd())
    monkeypatch.setattr(addon, "_make_analysis_request",
                        lambda scene, domain, domain_geometries=(): SimpleNamespace(to_dict=lambda: {"domain": domain}))
    monkeypatch.setattr(addon, "_stored_camera_plane", lambda scene: ({"camera_guid": "fixture"}, None))
    start_class = next(cls for cls in addon._operator_classes(fake_bpy)
                       if getattr(cls, "bl_idname", "") == "om_analysis.start")
    calls = []
    runtime.start_job = lambda **kwargs: calls.append(kwargs)
    context = SimpleNamespace(scene=SimpleNamespace())
    runtime.STATE.domain_session = MappingProxyType({
        "current": MappingProxyType({"status": "active"}),
        "analysis_domain": {"id": "domain"}, "domain_geometries": (),
    })
    operator = start_class()
    operator.report = lambda *_args: None
    assert operator.execute(context) == {"FINISHED"}
    assert calls
    runtime.STATE.domain_session = object()
    assert operator.execute(context) == {"CANCELLED"}


def test_selected_wall_start_requires_current_structural_context(monkeypatch, tmp_path):
    """Start accepts unchanged selected consent and refuses tolerance, scope, or storey drift."""
    from .test_analysis_requests import _plane
    from ..adapters.bonsai_live import StructuralContext

    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    refs = ("ifc-object:wall-a", "ifc-object:wall-b")
    retained = StructuralContext.from_plane(
        _plane(), storey_ref="ifc-object:S7", selected_wall_refs=refs,
        b4_parameters={"tolerance_mm2": 10.0, "contact_distance_m": 1e-6,
                       "aperture_area_budget_m2": 1e-6})
    domain = MappingProxyType({
        "current": MappingProxyType({"status": "active"}),
        "analysis_domain": {"id": "domain"}, "domain_geometries": (),
    })
    calls = []
    runtime = SimpleNamespace(
        STATE=SimpleNamespace(domain_session=domain, domain_context=retained.to_dict()),
        start_job=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_make_analysis_request",
                        lambda scene, value, domain_geometries=(): SimpleNamespace(to_dict=lambda: {"domain": value}))
    monkeypatch.setattr(addon, "_stored_camera_plane", lambda scene: ({"camera_guid": "fixture"}, None))
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene: StructuralContext.from_plane(
        _plane(), storey_ref=scene.storey_ref, selected_wall_refs=scene.selected_wall_refs,
        b4_parameters={"tolerance_mm2": scene.tolerance_mm2, "contact_distance_m": 1e-6,
                       "aperture_area_budget_m2": 1e-6}).to_dict())
    operator = next(cls for cls in addon._operator_classes(fake_bpy)
                    if cls.bl_idname == "om_analysis.start")()
    errors = []
    operator.report = lambda _kind, message: errors.append(message)
    scene = SimpleNamespace(storey_ref="ifc-object:S7", selected_wall_refs=refs, tolerance_mm2=10.0)
    assert operator.execute(SimpleNamespace(scene=scene)) == {"FINISHED"}
    assert len(calls) == 1
    for attribute, value in (("tolerance_mm2", 25.0),
                             ("selected_wall_refs", ("ifc-object:wall-a", "ifc-object:wall-c")),
                             ("storey_ref", "ifc-object:S8")):
        setattr(scene, attribute, value)
        assert operator.execute(SimpleNamespace(scene=scene)) == {"CANCELLED"}
        assert "refresh and confirm" in errors[-1].lower()
        setattr(scene, "tolerance_mm2", 10.0)
        setattr(scene, "selected_wall_refs", refs)
        setattr(scene, "storey_ref", "ifc-object:S7")
    assert len(calls) == 1


def test_inspect_reads_current_free_space_cell_and_refuses_stale_result(monkeypatch):
    """Inspect delegates to the authoritative helper and rejects unavailable truth."""
    class Operator:
        """Fake Blender operator base."""
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    import blender_addon.order_analyzer_ui.overlay as overlay
    result = SimpleNamespace(document={"kind": "free_space_run"})
    runtime = SimpleNamespace(STATE=SimpleNamespace(current_result=result, freshness="current", inspection=None))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(overlay, "inspect_cell", lambda value, row, column: {"row": row, "column": column})
    inspect_class = next(cls for cls in addon._operator_classes(fake_bpy)
                         if getattr(cls, "bl_idname", "") == "om_analysis.inspect")
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_inspect_row=2, om_analysis_inspect_column=3,
                                                    om_analysis_inspection=""))
    operator = inspect_class()
    messages = []
    operator.report = lambda _levels, message: messages.append(message)
    runtime.STATE.overlay_object = object()
    if hasattr(runtime, "invalidate_runtime"):
        runtime.invalidate_runtime("display_only")
    assert operator.execute(context) == {"FINISHED"}
    assert runtime.STATE.inspection == {"row": 2, "column": 3}
    runtime.STATE.freshness = "stale"
    assert operator.execute(context) == {"CANCELLED"}
    assert "unavailable" in messages[-1]


def test_overlay_update_classification_uses_stable_native_markers(monkeypatch):
    """Distinct RNA-like wrappers with matching names and tags remain display-only."""
    class Wrapper:
        """Expose Blender-like name and custom-property access."""
        def __init__(self, name, values=None):
            self.name = name
            self._values = values or {}
        def get(self, key, default=None):
            """Read a custom marker."""
            return self._values.get(key, default)
    mesh = Wrapper("OM Analysis OverlayMesh")
    overlay_object = Wrapper("OM Analysis Overlay", {
        "om_analysis_owner": "order_analyzer", "om_analysis_role": "overlay",
        "om_analysis_result_id": "result-1"})
    overlay_object.data = mesh
    result = SimpleNamespace(document={"kind": "free_space_run", "result_id": "result-1"})
    runtime = SimpleNamespace(STATE=SimpleNamespace(overlay_object=overlay_object, current_result=result))
    depsgraph = SimpleNamespace(updates=(SimpleNamespace(id=Wrapper("OM Analysis Overlay", overlay_object._values)),
                                         SimpleNamespace(id=Wrapper("OM Analysis OverlayMesh")),
                                         SimpleNamespace(id=Wrapper("scene",),),))
    depsgraph.updates[-1].id.bl_rna = SimpleNamespace(identifier="Scene")
    assert addon._overlay_updates_only(runtime, depsgraph)
    depsgraph.updates = (SimpleNamespace(id=depsgraph.updates[-1].id),)
    assert not addon._overlay_updates_only(runtime, depsgraph)
    depsgraph.updates = (SimpleNamespace(id=Wrapper("source-object")),)
    assert not addon._overlay_updates_only(runtime, depsgraph)


def test_analysis_input_callback_invalidates_but_scene_metadata_does_not(monkeypatch):
    """Request controls stale currentness explicitly while metadata stays presentation-only."""
    calls = []
    runtime = SimpleNamespace(invalidate_domain_session=lambda reason: calls.append(reason))
    monkeypatch.setattr(addon, "_runtime", lambda context=None: runtime)
    addon._analysis_input_update(object(), object())
    assert calls == ["analysis input changed"]
    class RNA:
        """Expose Blender RNA type identity."""
        def __init__(self, identifier):
            self.identifier = identifier
    scene = SimpleNamespace(bl_rna=RNA("Scene"))
    collection = SimpleNamespace(bl_rna=RNA("Collection"))
    window_manager = SimpleNamespace(bl_rna=RNA("WindowManager"))
    screen = SimpleNamespace(bl_rna=RNA("Screen"))
    object_data = SimpleNamespace(bl_rna=RNA("Object"))
    mesh_data = SimpleNamespace(bl_rna=RNA("Mesh"))
    assert addon._depsgraph_updates_are_neutral(SimpleNamespace(
        updates=(SimpleNamespace(id=scene), SimpleNamespace(id=collection),
                 SimpleNamespace(id=window_manager), SimpleNamespace(id=screen))))
    assert not addon._depsgraph_updates_are_neutral(SimpleNamespace(
        updates=(SimpleNamespace(id=window_manager), SimpleNamespace(id=screen),
                 SimpleNamespace(id=object_data))))
    assert not addon._depsgraph_updates_are_neutral(SimpleNamespace(
        updates=(SimpleNamespace(id=mesh_data),)))


def test_missing_selected_space_clears_stale_selection(monkeypatch):
    """An explicit IFC deletion clears only the stale Space-bound UI state."""
    model = SimpleNamespace(by_guid=lambda _guid: None)
    monkeypatch.setitem(sys.modules, "bonsai.tool", SimpleNamespace(Ifc=SimpleNamespace(get=lambda: model)))
    scene = SimpleNamespace(om_analysis_space_source_id="space-guid", om_analysis_storey_ref="storey",
                            om_analysis_support_source_id="floor", om_analysis_selected_version_id="version")
    calls = []
    assert addon._clear_missing_space_selection(SimpleNamespace(scene=scene), SimpleNamespace(
        invalidate_domain_session=lambda reason: calls.append(reason)))
    assert scene.om_analysis_space_source_id == ""
    assert scene.om_analysis_storey_ref == ""
    assert scene.om_analysis_support_source_id == ""
    assert scene.om_analysis_selected_version_id == ""
    assert calls == ["selected IfcSpace was removed"]


def test_existing_selected_space_preserves_selection(monkeypatch):
    """A still-present native Space keeps its selection and consent state."""
    entity = SimpleNamespace(GlobalId="space-guid")
    model = SimpleNamespace(by_guid=lambda _guid: entity)
    monkeypatch.setitem(sys.modules, "bonsai.tool", SimpleNamespace(Ifc=SimpleNamespace(get=lambda: model)))
    scene = SimpleNamespace(om_analysis_space_source_id="space-guid", om_analysis_storey_ref="storey",
                            om_analysis_support_source_id="floor", om_analysis_selected_version_id="version")
    assert not addon._clear_missing_space_selection(SimpleNamespace(scene=scene), SimpleNamespace())
    assert scene.om_analysis_space_source_id == "space-guid"
    assert scene.om_analysis_storey_ref == "storey"


def test_unavailable_ifc_preserves_selection(monkeypatch):
    """Unavailable or failing IFC access is non-authoritative and preserves state."""
    monkeypatch.setitem(sys.modules, "bonsai.tool", SimpleNamespace(Ifc=SimpleNamespace(
        get=lambda: (_ for _ in ()).throw(RuntimeError("not loaded")))))
    scene = SimpleNamespace(om_analysis_space_source_id="space-guid", om_analysis_storey_ref="storey",
                            om_analysis_support_source_id="floor", om_analysis_selected_version_id="version")
    assert not addon._clear_missing_space_selection(SimpleNamespace(scene=scene), SimpleNamespace())
    assert scene.om_analysis_space_source_id == "space-guid"
    assert scene.om_analysis_storey_ref == "storey"


def test_region_manifest_neutrality_requires_a_text_datablock():
    """Ownership tags on a geometry datablock cannot suppress source invalidation."""
    class RNA:
        """Expose one Blender datablock identifier."""
        def __init__(self, identifier):
            self.identifier = identifier
    class Tagged:
        """Expose addon-like tags for both text and geometry cases."""
        def __init__(self, identifier):
            self.bl_rna = RNA(identifier)
        def get(self, key, default=None):
            """Read one test ownership tag."""
            return {"om_analysis_owner": "order_analyzer", "om_analysis_role": "region_list"}.get(key, default)
    assert addon._depsgraph_updates_are_neutral(SimpleNamespace(
        updates=(SimpleNamespace(id=Tagged("Text")),)))
    assert not addon._depsgraph_updates_are_neutral(SimpleNamespace(
        updates=(SimpleNamespace(id=Tagged("Object")),)))


def test_overlay_update_classification_survives_invalid_old_rna_handle():
    """A removed old overlay handle cannot make a tagged overlay update stale."""
    class InvalidOverlay:
        """Simulate a Blender Object wrapper invalidated by removal."""
        @property
        def name(self):
            """Raise the native invalid-handle error on access."""
            raise ReferenceError("StructRNA of type Object has been removed")
        @property
        def data(self):
            """Raise the native invalid-handle error on access."""
            raise ReferenceError("StructRNA of type Object has been removed")
    class Marker:
        """Expose stable update-ID markers after object removal."""
        name = "OM Analysis Overlay"
        def get(self, key, default=None):
            """Return addon ownership markers."""
            return {"om_analysis_owner": "order_analyzer", "om_analysis_role": "overlay",
                    "om_analysis_result_id": "result-1"}.get(key, default)
    runtime = SimpleNamespace(STATE=SimpleNamespace(overlay_object=InvalidOverlay(),
                                                     current_result=SimpleNamespace(
                                                         document={"result_id": "result-1"})))
    depsgraph = SimpleNamespace(updates=(SimpleNamespace(id=Marker()),))
    assert addon._overlay_updates_only(runtime, depsgraph)
    depsgraph.updates = (SimpleNamespace(id=SimpleNamespace(name="source-object")),)
    assert not addon._overlay_updates_only(runtime, depsgraph)


def test_select_writes_ui_state_without_submitting_a_job(monkeypatch):
    """Candidate row selection is UI-only and leaves the retained session untouched."""
    class Operator:
        """Fake Blender operator base."""
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    calls = []
    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session={}),
                              start_job=lambda **kwargs: calls.append(kwargs),
                              invalidate_runtime=lambda reason: calls.append({"invalidated": reason}))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: Path.cwd())
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene: {"frame": "b4"})
    monkeypatch.setattr(addon, "_domain_action", lambda kind, version_id=None: {"kind": kind, "candidate_version_id": version_id})
    select_class = next(cls for cls in addon._operator_classes(fake_bpy)
                        if getattr(cls, "bl_idname", "") == "om_analysis.b4_select")
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_selected_version_id=""))
    operator = select_class()
    operator.version_id = "candidate-1"
    operator.report = lambda *_args: None
    assert operator.execute(context) == {"FINISHED"}
    assert context.scene.om_analysis_selected_version_id == "candidate-1"
    assert calls == []


def test_select_and_confirm_keep_candidate_within_analyzed_storey(monkeypatch, tmp_path):
    """A stale S7 row is refused in S8 and accepted with exact S7 job scope."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    candidate = {"version_id": "candidate-1", "identity": "identity-1",
                 "storey_ref": "ifc-object:S7"}
    result = {"candidates": (candidate,), "session_revision": 1,
              "provenance": {"source_revision": "source", "frame_id": "frame", "request_id": "request"}}
    calls = []
    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session=result),
                              start_job=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene: {"storey_ref": scene.om_analysis_storey_ref})
    classes = addon._operator_classes(fake_bpy)
    scene = SimpleNamespace(om_analysis_selected_version_id="candidate-1",
                            om_analysis_storey_ref="ifc-object:S8",
                            om_analysis_support_source_id="")
    context = SimpleNamespace(scene=scene)
    errors = []

    select = next(cls for cls in classes if cls.bl_idname == "om_analysis.b4_select")()
    select.version_id = "candidate-1"
    select.storey_ref = "ifc-object:S7"
    select.report = lambda _kind, message: errors.append(message)
    assert select.execute(context) == {"CANCELLED"}

    confirm = next(cls for cls in classes if cls.bl_idname == "om_analysis.b4_confirm")()
    confirm.report = lambda _kind, message: errors.append(message)
    assert confirm.execute(context) == {"CANCELLED"}
    assert calls == []
    assert all("storey" in message.lower() for message in errors)

    scene.om_analysis_storey_ref = "ifc-object:S7"
    assert select.execute(context) == {"FINISHED"}
    assert confirm.execute(context) == {"FINISHED"}
    assert calls[0]["payload"]["storey_ref"] == "ifc-object:S7"
    assert calls[0]["payload"]["context"]["storey_ref"] == "ifc-object:S7"


def test_domain_action_carries_optional_space_storey_and_support_identity():
    """Authored Space and explicit support choices travel through the existing reducer action."""
    assert addon._domain_action("select", "candidate", source_id="space-guid",
                                storey_ref="ifc-object:storey", support_source_id="floor-guid") == {
        "kind": "select", "candidate_version_id": "candidate", "domain_source_id": "space-guid",
        "storey_ref": "ifc-object:storey", "support_source_id": "floor-guid"}


def test_create_space_operator_is_explicit_and_invalidates_capture(monkeypatch):
    """Create Space delegates to Bonsai and makes the next capture authoritative."""
    class Operator:
        """Fake Blender operator base."""
    calls = []
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""),
                               ops=SimpleNamespace(om_analysis=SimpleNamespace(
                                   create_space_from_candidate=lambda: calls.append("exact_candidate") or {"FINISHED"})))
    runtime = SimpleNamespace(invalidate_runtime=lambda reason: calls.append(reason))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    cls = next(cls for cls in addon._operator_classes(fake_bpy)
               if getattr(cls, "bl_idname", "") == "om_analysis.create_space")
    result = cls().execute(SimpleNamespace())
    assert result == {"FINISHED"}
    assert calls == ["exact_candidate"]


def test_selected_authored_binding_reads_native_space_and_storey(monkeypatch):
    """Refresh adopts only an explicitly selected native IfcSpace and its relation."""
    import types
    storey = SimpleNamespace(GlobalId="storey-guid", is_a=lambda: "IfcBuildingStorey")
    relation = SimpleNamespace(RelatingStructure=storey)
    space = SimpleNamespace(GlobalId="space-guid", is_a=lambda: "IfcSpace", ContainedInStructure=(relation,))
    tool = types.ModuleType("bonsai.tool")
    tool.Ifc = SimpleNamespace(get_entity=lambda _obj: space)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_support_source_id="floor-guid"), active_object=object())
    assert addon._selected_authored_binding(context) == {
        "domain_source_id": "space-guid", "storey_ref": "ifc-object:storey-guid",
        "support_source_id": "floor-guid"}


def test_native_space_candidates_are_cheap_and_keep_hidden_metadata(monkeypatch):
    """Space listing exposes identity metadata without claiming topology validity."""
    import types
    storey = SimpleNamespace(GlobalId="storey-guid", is_a=lambda: "IfcBuildingStorey")
    relation = SimpleNamespace(RelatingStructure=storey)
    mesh = SimpleNamespace(vertices=(1, 2, 3))
    obj = SimpleNamespace(type="MESH", data=mesh, hide_viewport=True)
    space = SimpleNamespace(GlobalId="space-guid", Name="Room A", LongName=None,
                            Representation=object(), ContainedInStructure=(relation,))
    model = SimpleNamespace(by_type=lambda kind: (space,) if kind == "IfcSpace" else ())
    tool = types.ModuleType("bonsai.tool")
    tool.Ifc = SimpleNamespace(get=lambda: model, get_object=lambda entity: obj)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)

    rows = addon._native_space_candidates(SimpleNamespace(scene=SimpleNamespace()))

    assert rows == ({
        "domain_source_id": "space-guid",
        "name": "Room A",
        "storey_ref": "ifc-object:storey-guid",
        "hide_viewport": True,
        "has_representation": True,
        "mesh_present": True,
        "metadata_status": "hidden",
        "geometry_validation": "pending",
    },)


def _native_space_model(monkeypatch, *, kind="IfcSpace", representation=True, mesh=True):
    """Install native metadata with geometry that must never be iterated."""
    import types
    storey = SimpleNamespace(GlobalId="storey-guid", is_a=lambda: "IfcBuildingStorey")
    entity = SimpleNamespace(GlobalId="space-guid", Name="Room A", is_a=lambda: kind, id=lambda: 41,
                             Representation=object() if representation else None,
                             Decomposes=(SimpleNamespace(RelatingObject=storey),))
    obj = SimpleNamespace(type="MESH", data=SimpleNamespace(vertices=(object(),)) if mesh else None,
                          hide_viewport=True)
    entities = {entity.GlobalId: entity}
    model = SimpleNamespace(by_guid=lambda guid: entities.get(guid),
                            by_type=lambda name: (SimpleNamespace(GlobalId="project-guid"),) if name == "IfcProject"
                            else tuple(entities.values()) if name == "IfcSpace" else ())
    tool = types.ModuleType("bonsai.tool")
    tool.Ifc = SimpleNamespace(get=lambda: model, get_object=lambda source: obj, get_entity=lambda item: entity)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    monkeypatch.setitem(sys.modules, "bpy", SimpleNamespace(data=SimpleNamespace(objects=[obj])))
    return entities


@pytest.mark.parametrize("failure", ["project", "reverse_link", "duplicate_link", "conflicting_storey"])
def test_native_space_adoption_rejects_inconsistent_identity_links(monkeypatch, failure):
    """Both UI entries must qualify project, source, object and a unique native storey."""
    entities = _native_space_model(monkeypatch)
    tool = sys.modules["bonsai.tool"]
    if failure == "project":
        tool.Ifc.get().by_type = lambda name: ()
    elif failure == "reverse_link":
        tool.Ifc.get_entity = lambda obj: None
    elif failure == "duplicate_link":
        sys.modules["bpy"].data.objects.append(SimpleNamespace(type="MESH"))
    else:
        entities["space-guid"].Decomposes += (SimpleNamespace(RelatingObject=SimpleNamespace(
            GlobalId="other-storey", is_a=lambda: "IfcBuildingStorey")),)
    with pytest.raises(ValueError, match="project|native|storey"):
        addon._space_identity_from_guid(SimpleNamespace(), "space-guid", storey_ref="ifc-object:storey-guid")


@pytest.mark.parametrize("kind,representation,mesh,source,storey,error", [
    ("IfcWall", True, True, "space-guid", "ifc-object:storey-guid", "IfcSpace"),
    ("IfcSpace", True, True, "space-guid", "ifc-object:other", "storey"),
    ("IfcSpace", False, True, "space-guid", "ifc-object:storey-guid", "geometry"),
    ("IfcSpace", True, False, "space-guid", "ifc-object:storey-guid", "geometry"),
    ("IfcSpace", True, True, "removed", "ifc-object:storey-guid", "not found"),
])
def test_space_identity_rejects_invalid_native_metadata(monkeypatch, kind, representation, mesh, source, storey, error):
    """Explicit source metadata rejects wrong type, floor and missing geometry."""
    _native_space_model(monkeypatch, kind=kind, representation=representation, mesh=mesh)
    with pytest.raises(ValueError, match=error):
        addon._space_identity_from_guid(SimpleNamespace(), source, storey_ref=storey)


def test_space_adopt_payload_uses_only_explicit_hidden_identity(monkeypatch):
    """A hidden Space is selectable without a visibility change or retained fallback."""
    _native_space_model(monkeypatch)
    monkeypatch.setattr(addon, "_space_context_payload", lambda scene, **kwargs: {"frame": "authored"})
    scene = SimpleNamespace(om_analysis_storey_ref="ifc-object:wrong",
                            om_analysis_support_source_id="wrong-floor")
    payload = addon._space_adopt_payload(SimpleNamespace(scene=scene), source_id="space-guid",
                                         storey_ref="ifc-object:storey-guid")
    assert payload == {"kind": "domain_session", "context": {"frame": "authored"}, "prior": None,
                       "action": None, "domain_source_id": "space-guid",
                       "storey_ref": "ifc-object:storey-guid"}


def test_storey_change_clears_space_support_version_and_consent(monkeypatch):
    """Changing floor through RNA must not retain an adopted Space or consent."""
    scene = SimpleNamespace(om_analysis_space_source_id="space-guid", om_analysis_storey_ref="other",
                            om_analysis_support_source_id="floor", om_analysis_selected_version_id="version")
    invalidated = []
    monkeypatch.setattr(addon, "_runtime", lambda context: SimpleNamespace(
        invalidate_domain_session=lambda reason: invalidated.append(reason)))
    addon._storey_input_update(scene, SimpleNamespace(scene=scene))
    assert scene.om_analysis_space_source_id == ""
    assert scene.om_analysis_storey_ref == "other"
    assert scene.om_analysis_support_source_id == ""
    assert scene.om_analysis_selected_version_id == ""
    assert invalidated == ["analysis storey changed"]


def test_selected_wall_json_is_canonical_and_strict():
    """Scene persistence uses deterministic canonical IFC refs and refuses malformed state."""
    scene = SimpleNamespace(om_analysis_selected_wall_refs_json="")
    assert addon._set_selected_wall_refs(scene, ("ifc-object:b", "ifc-object:a")) == (
        "ifc-object:a", "ifc-object:b")
    assert scene.om_analysis_selected_wall_refs_json == '["ifc-object:a","ifc-object:b"]'
    assert addon._selected_wall_refs(scene) == ("ifc-object:a", "ifc-object:b")
    scene.om_analysis_selected_wall_refs_json = '["ifc-object:a","ifc-object:a"]'
    with pytest.raises(ValueError, match="duplicate"):
        addon._selected_wall_refs(scene)


def test_selected_native_wall_refs_accept_unknown_containment_and_reject_wrong_storey(monkeypatch):
    """Native selection requires walls while unknown containment stays conservative."""
    class Entity:
        """Minimal IFC entity with optional explicit storey relation."""
        def __init__(self, guid, storey=None):
            """Store one wall identity and optional explicit storey relation."""
            self.GlobalId = guid
            self.ContainedInStructure = (() if storey is None else (
                SimpleNamespace(RelatingStructure=SimpleNamespace(
                    is_a=lambda: "IfcBuildingStorey", GlobalId=storey)),))
            self.Decomposes = ()
        def is_a(self, expected=None):
            """Expose IFC class predicate and name forms."""
            return "IfcWall" if expected is None else expected == "IfcWall"
    entities = {"unknown": Entity("wall-a"), "same": Entity("wall-b", "S7"),
                "wrong": Entity("wall-c", "S8")}
    tool = SimpleNamespace(Ifc=SimpleNamespace(get_entity=lambda obj: entities[obj]))
    monkeypatch.setitem(sys.modules, "bonsai", SimpleNamespace(tool=tool))
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    scene = SimpleNamespace(om_analysis_storey_ref="ifc-object:S7")
    assert addon._selected_native_wall_refs(SimpleNamespace(
        scene=scene, selected_objects=("same", "unknown"))) == (
            "ifc-object:wall-a", "ifc-object:wall-b")
    with pytest.raises(ValueError, match="storey"):
        addon._selected_native_wall_refs(SimpleNamespace(scene=scene, selected_objects=("wrong",)))


def test_analyze_selected_walls_freezes_native_scope_before_capture(monkeypatch, tmp_path):
    """Selected-wall launch persists refs, flushes Scene writes, and starts a fresh scoped job."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    events, calls = [], []
    runtime = SimpleNamespace(
        STATE=SimpleNamespace(domain_session={"old": True}),
        _flush_native_view_layer=lambda: events.append("flush"),
        invalidate_domain_session=lambda reason: events.append(reason),
        start_job=lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(addon, "_selected_native_wall_refs",
                        lambda context: ("ifc-object:wall-a", "ifc-object:wall-b"))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene: {
        "selected_wall_refs": addon._selected_wall_refs(scene)})
    scene = SimpleNamespace(
        om_analysis_storey_ref="ifc-object:S7", om_analysis_space_source_id="space",
        om_analysis_support_source_id="floor", om_analysis_selected_version_id="candidate",
        om_analysis_selected_wall_refs_json="")
    context = SimpleNamespace(scene=scene, selected_objects=(object(),))
    operator = next(cls for cls in addon._operator_classes(fake_bpy)
                    if cls.bl_idname == "om_analysis.analyze_selected_walls")()
    operator.report = lambda *_args: None
    assert operator.execute(context) == {"FINISHED"}
    assert events == ["flush", "selected-wall analysis requested"]
    assert scene.om_analysis_selected_wall_refs_json == '["ifc-object:wall-a","ifc-object:wall-b"]'
    assert scene.om_analysis_space_source_id == ""
    assert scene.om_analysis_support_source_id == "floor"
    assert calls[0]["payload"]["prior"] is None
    assert calls[0]["payload"]["support_source_id"] == "floor"
    assert calls[0]["payload"]["context"]["selected_wall_refs"] == (
        "ifc-object:wall-a", "ifc-object:wall-b")


def test_selected_wall_confirm_rebuilds_current_context_with_frozen_refs(monkeypatch, tmp_path):
    """Confirmation keeps analyzed refs while reading current tolerance and storey inputs."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    refs = ("ifc-object:wall-a", "ifc-object:wall-b")
    candidate = {"version_id": "candidate", "identity": "identity", "storey_ref": "ifc-object:S7",
                 "selected_wall_refs": refs}
    result = {"candidates": (candidate,), "session_revision": 1,
              "provenance": {"source_revision": "source", "frame_id": "frame", "request_id": "request"}}
    calls = []
    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session=result),
                              start_job=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene, *, selected_wall_refs=(): {
        "tolerance_mm2": scene.om_b4_tolerance_mm2, "selected_wall_refs": tuple(selected_wall_refs)})
    scene = SimpleNamespace(
        om_analysis_selected_version_id="candidate", om_analysis_storey_ref="ifc-object:S7",
        om_analysis_support_source_id="", om_analysis_selected_wall_refs_json='["ifc-object:other"]',
        om_b4_tolerance_mm2=25.0)
    operator = next(cls for cls in addon._operator_classes(fake_bpy)
                    if cls.bl_idname == "om_analysis.b4_confirm")()
    operator.report = lambda *_args: None
    assert operator.execute(SimpleNamespace(scene=scene)) == {"FINISHED"}
    assert calls[0]["payload"]["context"] == {"tolerance_mm2": 25.0, "selected_wall_refs": refs}


def test_use_selected_ifcspace_requires_explicit_identity_and_no_fallback(monkeypatch, tmp_path):
    """The Space entry starts a fresh explicit request and never reuses retained state."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(
        types=SimpleNamespace(Operator=Operator),
        props=SimpleNamespace(StringProperty=lambda **_kwargs: ""),
    )
    calls = []
    events = []
    observed_epochs = []
    state = SimpleNamespace(domain_session={"current": {"status": "active"}}, observation_epoch=41)
    scene = SimpleNamespace(om_analysis_space_source_id="old-space",
                            om_analysis_storey_ref="old-storey",
                            om_analysis_support_source_id="old-floor",
                            om_analysis_selected_version_id="old-version")

    def flush_native_view_layer():
        """Settle the four pending Scene writes before the job freezes its epoch."""
        assert (scene.om_analysis_space_source_id, scene.om_analysis_storey_ref,
                scene.om_analysis_support_source_id, scene.om_analysis_selected_version_id) == (
                    "space-guid", "ifc-object:storey-guid", "", "")
        state.observation_epoch += 1
        events.append("flush")

    def start_job(**kwargs):
        """Record the epoch observed at the operator-to-runtime handoff."""
        observed_epochs.append((state.observation_epoch, state.observation_epoch))
        events.append("start")
        calls.append(kwargs)

    runtime = SimpleNamespace(
        STATE=state,
        start_job=start_job,
        invalidate_domain_session=lambda reason: (events.append("invalidate"), calls.append({"invalidated": reason})),
        _flush_native_view_layer=flush_native_view_layer,
    )
    monkeypatch.setattr(addon, "_action_runtime", lambda _context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda _context=None: tmp_path)
    monkeypatch.setattr(addon, "_space_context_payload", lambda _scene, **kwargs: {"frame": "authored"})
    monkeypatch.setattr(addon, "_space_identity_from_guid", lambda _ctx, guid, *, storey_ref: {
        "domain_source_id": guid, "storey_ref": storey_ref})
    classes = addon._operator_classes(fake_bpy)
    cls = next(cls for cls in classes if getattr(cls, "bl_idname", "") == "om_analysis.use_selected_ifcspace")
    operator = cls()
    operator.source_id = "space-guid"
    operator.storey_ref = "ifc-object:storey-guid"
    operator.report = lambda *_args: None
    assert operator.execute(SimpleNamespace(scene=scene)) == {"FINISHED"}
    assert scene.om_analysis_space_source_id == "space-guid"
    assert scene.om_analysis_storey_ref == "ifc-object:storey-guid"
    assert scene.om_analysis_support_source_id == ""
    assert scene.om_analysis_selected_version_id == ""
    assert events == ["flush", "invalidate", "start"]
    assert observed_epochs == [(42, 42)]
    assert calls == [
        {"invalidated": "analysis Space selection changed"},
        {"repo_root": tmp_path, "bpy_context": SimpleNamespace(scene=scene),
         "auto_publish": True,
         "payload": {"kind": "domain_session", "context": {"frame": "authored"},
                     "prior": None, "action": None,
                     "domain_source_id": "space-guid", "storey_ref": "ifc-object:storey-guid"}},
    ]


def test_use_selected_ifcspace_rejects_missing_storey(monkeypatch):
    """An explicit Space request cannot fall back to the active or retained storey."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(
        types=SimpleNamespace(Operator=Operator),
        props=SimpleNamespace(StringProperty=lambda **_kwargs: ""),
    )
    cls = next(cls for cls in addon._operator_classes(fake_bpy)
               if getattr(cls, "bl_idname", "") == "om_analysis.use_selected_ifcspace")
    operator = cls()
    operator.source_id = "space-guid"
    operator.storey_ref = ""
    errors = []
    operator.report = lambda _kind, message: errors.append(message)
    assert operator.execute(SimpleNamespace(scene=SimpleNamespace(om_analysis_storey_ref="fallback"))) == {"CANCELLED"}
    assert errors == ["Use selected IfcSpace requires an explicit source and storey"]


def test_use_selected_ifcspace_native_sync_failure_cannot_start(monkeypatch, tmp_path):
    """A failed native synchronization boundary must cancel before invalidation or start."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(
        types=SimpleNamespace(Operator=Operator),
        props=SimpleNamespace(StringProperty=lambda **_kwargs: ""),
    )
    calls = []
    runtime = SimpleNamespace(
        _flush_native_view_layer=lambda: (_ for _ in ()).throw(RuntimeError("native update unavailable")),
        invalidate_domain_session=lambda reason: calls.append(("invalidate", reason)),
        start_job=lambda **kwargs: calls.append(("start", kwargs)),
    )
    monkeypatch.setattr(addon, "_action_runtime", lambda _context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda _context=None: tmp_path)
    monkeypatch.setattr(addon, "_space_context_payload", lambda _scene, **kwargs: {"frame": "authored"})
    monkeypatch.setattr(addon, "_space_identity_from_guid", lambda _ctx, guid, *, storey_ref: {
        "domain_source_id": guid, "storey_ref": storey_ref})
    cls = next(cls for cls in addon._operator_classes(fake_bpy)
               if getattr(cls, "bl_idname", "") == "om_analysis.use_selected_ifcspace")
    operator = cls()
    operator.source_id = "space-guid"
    operator.storey_ref = "ifc-object:storey-guid"
    errors = []
    operator.report = lambda _kind, message: errors.append(message)
    scene = SimpleNamespace(om_analysis_space_source_id="old-space",
                            om_analysis_storey_ref="old-storey",
                            om_analysis_support_source_id="old-floor",
                            om_analysis_selected_version_id="old-version")

    assert operator.execute(SimpleNamespace(scene=scene)) == {"CANCELLED"}
    assert calls == []
    assert "native update unavailable" in errors[-1]


def test_refresh_for_selected_native_space_keeps_structural_b4_route(monkeypatch, tmp_path):
    """Refresh keeps B4 structural even when an authored Space is selected."""
    class Operator:
        """Fake Blender operator base."""
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    calls = []
    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session=None),
                              start_job=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene: {"frame": "b4"})
    monkeypatch.setattr(addon, "_selected_authored_binding",
                        lambda context: (_ for _ in ()).throw(AssertionError("B4 must not inspect authored selection")))
    monkeypatch.setattr(addon, "_retained_authored_binding",
                        lambda *args: (_ for _ in ()).throw(AssertionError("B4 must not inspect retained authored state")))
    cls = next(cls for cls in addon._operator_classes(fake_bpy)
               if getattr(cls, "bl_idname", "") == "om_analysis.b4_refresh")
    operator = cls()
    operator.report = lambda *_args: None
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_storey_ref="ifc-object:S7"))
    assert operator.execute(context) == {"FINISHED"}
    assert calls[0]["payload"] == {
        "kind": "domain_session", "context": {"frame": "b4"}, "prior": None, "action": None,
    }


def test_refresh_with_retained_authored_session_keeps_structural_b4_route(monkeypatch, tmp_path):
    """Refresh does not derive authored identity from a retained Domain session."""
    class Operator:
        """Fake Blender operator base."""
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    calls = []
    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session={"authored_domain": {"source_id": "space-guid"}}),
                              start_job=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene: {"frame": "b4"})
    monkeypatch.setattr(addon, "_retained_authored_binding",
                        lambda *args: (_ for _ in ()).throw(AssertionError("B4 must not inspect retained authored state")))
    cls = next(cls for cls in addon._operator_classes(fake_bpy)
               if getattr(cls, "bl_idname", "") == "om_analysis.b4_refresh")
    operator = cls()
    operator.report = lambda *_args: None
    assert operator.execute(SimpleNamespace(scene=SimpleNamespace())) == {"FINISHED"}
    assert calls[0]["payload"] == {
        "kind": "domain_session", "context": {"frame": "b4"},
        "prior": runtime.STATE.domain_session, "action": None}


def test_recheck_submits_persisted_authored_identity(monkeypatch, tmp_path):
    """Recheck launches a new Domain request from saved identity facts."""
    class Operator:
        """Fake Blender operator base."""
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    record = {"region_id": "space-guid", "name": "Room", "storey_ref": "ifc-object:storey-guid",
              "plane_uuid": "plane", "plane_revision": 1,
              "source_id": "space-guid", "geometry_refs": (),
              "outline": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]], "holes": [],
              "status": "historical", "confirmation": {}, "support_source_id": "floor-guid"}
    manifest = {"records": (record,), "active_region_id": "space-guid", "storey_ref": record["storey_ref"]}
    calls = []
    runtime = SimpleNamespace(STATE=SimpleNamespace(domain_session=None),
                              find_region_manifest=lambda **kwargs: manifest,
                              embed_region_manifest=lambda *args, **kwargs: None,
                              invalidate_domain_session=lambda reason: calls.append({"invalidated": reason}),
                              start_job=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_space_context_payload", lambda scene, **kw: {"frame": "native-space", **kw})
    cls = next(cls for cls in addon._operator_classes(fake_bpy)
               if getattr(cls, "bl_idname", "") == "om_analysis.region_recheck")
    operator = cls()
    operator.region_id = "space-guid"
    operator.report = lambda *_args: None
    updates = []
    context = SimpleNamespace(scene=SimpleNamespace(),
                              view_layer=SimpleNamespace(update=lambda: updates.append("flushed")))
    assert operator.execute(context) == {"FINISHED"}
    assert updates == ["flushed"]
    assert calls[0] == {"invalidated": "analysis region requires recheck"}
    payload = calls[1]["payload"]
    assert payload["domain_source_id"] == "space-guid"
    assert payload["storey_ref"] == "ifc-object:storey-guid"
    assert payload["support_source_id"] == "floor-guid"
    assert payload["context"] == {"frame": "native-space", "storey_ref": "ifc-object:storey-guid"}


def test_save_copy_panel_invocation_opens_native_file_selector(tmp_path):
    """Panel invocation lets the user choose a fresh blend path before executing Save Copy."""
    class Operator:
        """Expose the operator methods without native Blender registration."""
    bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                          props=SimpleNamespace(StringProperty=lambda **kwargs: ""),
                          data=SimpleNamespace(filepath=str(tmp_path / "source.blend")))
    operator = next(cls for cls in addon._operator_classes(bpy)
                    if cls.bl_idname == "om_analysis.save_copy")()
    operator.filepath = ""
    selected = []
    context = SimpleNamespace(window_manager=SimpleNamespace(fileselect_add=selected.append))
    assert operator.invoke(context, None) == {"RUNNING_MODAL"}
    assert selected == [operator]
    assert Path(operator.filepath) == tmp_path / "source-analysis-copy.blend"


def test_recheck_submits_persisted_selected_wall_scope(monkeypatch, tmp_path):
    """An inferred Region rechecks through B4 with its frozen wall set and no authored Space identity."""
    class Operator:
        """Fake Blender operator base."""
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    refs = ("ifc-object:wall-a", "ifc-object:wall-b")
    record = {"region_id": "inferred", "name": "Room", "storey_ref": "ifc-object:S7",
              "plane_uuid": "plane", "plane_revision": 1, "source_id": None, "geometry_refs": (),
              "outline": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]], "holes": [],
              "status": "historical", "confirmation": {}, "selected_wall_refs": refs}
    manifest = {"records": (record,), "active_region_id": "inferred", "storey_ref": "ifc-object:S7"}
    calls = []
    runtime = SimpleNamespace(
        STATE=SimpleNamespace(domain_session=None), find_region_manifest=lambda **kwargs: manifest,
        embed_region_manifest=lambda *args, **kwargs: None,
        invalidate_domain_session=lambda reason: calls.append({"invalidated": reason}),
        start_job=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    monkeypatch.setattr(addon, "_configured_repo_root", lambda context=None: tmp_path)
    monkeypatch.setattr(addon, "_structural_context_payload", lambda scene, *, selected_wall_refs=(): {
        "selected_wall_refs": tuple(selected_wall_refs)})
    operator = next(cls for cls in addon._operator_classes(fake_bpy)
                    if cls.bl_idname == "om_analysis.region_recheck")()
    operator.region_id = "inferred"
    operator.report = lambda *_args: None
    scene = SimpleNamespace(om_analysis_selected_wall_refs_json="")
    context = SimpleNamespace(scene=scene, view_layer=SimpleNamespace(update=lambda: None))
    assert operator.execute(context) == {"FINISHED"}
    payload = calls[1]["payload"]
    assert payload["context"]["selected_wall_refs"] == refs
    assert payload["storey_ref"] == "ifc-object:S7"
    assert "domain_source_id" not in payload


def test_region_select_aligns_visible_storey_and_support_to_saved_row(monkeypatch):
    """Selecting history updates selectors before any later explicit confirmation."""
    class Operator:
        """Fake Blender operator base."""
    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    record = {"region_id": "space-guid", "storey_ref": "ifc-object:storey-guid",
              "support_source_id": "floor-guid"}
    invalidations = []
    runtime = SimpleNamespace(find_region_manifest=lambda **kwargs: {"records": (record,)},
                              invalidate_domain_session=lambda reason: invalidations.append(reason))
    monkeypatch.setattr(addon, "_action_runtime", lambda context: runtime)
    cls = next(cls for cls in addon._operator_classes(fake_bpy)
               if getattr(cls, "bl_idname", "") == "om_analysis.region_select")
    operator = cls()
    operator.region_id = "space-guid"
    operator.report = lambda *_args: None
    scene = SimpleNamespace(om_analysis_active_region_id="", om_analysis_storey_ref="other",
                            om_analysis_support_source_id="other-floor")
    assert operator.execute(SimpleNamespace(scene=scene)) == {"FINISHED"}
    assert scene.om_analysis_storey_ref == "ifc-object:storey-guid"
    assert scene.om_analysis_support_source_id == "floor-guid"
    assert invalidations == ["analysis region selection changed"]


def test_grid_coverage_uses_floor_ceil_for_negative_confirmed_extent():
    """Confirmed geometry determines a covering lattice instead of the 1x1 default."""
    scene = SimpleNamespace(om_analysis_grid_spacing=0.25, om_analysis_grid_rows=1, om_analysis_grid_columns=1)
    origin, rows, columns = addon._grid_coverage(
        scene, {}, ({"vertices": ((-0.2, -0.1, 0.0), (1.1, 0.6, 0.0))},))
    assert origin == (-0.25, -0.25)
    assert (rows, columns) == (4, 6)


def test_native_scope_candidates_are_named_and_offer_explicit_no_support(monkeypatch):
    """Native selector choices expose names while retaining canonical IDs."""
    import types
    storey = SimpleNamespace(GlobalId="storey", Name="Level 1", LongName=None,
                             is_a=lambda: "IfcBuildingStorey")
    relation = SimpleNamespace(RelatingStructure=storey)
    slab = SimpleNamespace(GlobalId="slab", Name="Ground", ContainedInStructure=(relation,), Decomposes=())
    model = SimpleNamespace(by_type=lambda kind: (storey,) if kind == "IfcBuildingStorey" else (slab,))
    tool = types.ModuleType("bonsai.tool")
    tool.Ifc = SimpleNamespace(get=lambda: model)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_storey_ref="ifc-object:storey"))
    assert addon._native_scope_candidates(context) == (
        (("ifc-object:storey", "Level 1"),), (("", "No support"), ("slab", "Ground")))


@pytest.mark.parametrize(("storeys", "selected", "expected_button", "expected_label"), [
    ((("ifc-object:s1", "Level 1"),), "", "Use", None),
    ((("ifc-object:s1", "Level 1"),), "ifc-object:s1", "Selected", "Selected storey: Level 1"),
    ((), "", None, "Storey: no native building storeys found"),
])
def test_b4_storey_selector_shows_missing_selected_and_no_native_states(
        monkeypatch, storeys, selected, expected_button, expected_label):
    """B4 exposes the native named storey choice needed by selected-wall analysis."""
    calls = []

    class Layout:
        """Record the small B4 selector surface."""

        def label(self, **kwargs):
            """Record visible text."""
            calls.append(("label", kwargs, None))

        def prop(self, *args, **kwargs):
            """Accept the unchanged tolerance property."""

        def row(self, **kwargs):
            """Reuse this recorder for aligned rows."""
            return self

        def operator(self, name, **kwargs):
            """Record operator and later property assignment."""
            operation = SimpleNamespace()
            calls.append((name, kwargs, operation))
            return operation

    monkeypatch.setattr(addon, "_native_scope_candidates", lambda context: (storeys, ()))
    scene = SimpleNamespace(om_analysis_storey_ref=selected, om_b4_tolerance_mm2=10.0,
                            om_analysis_selected_wall_refs_json="")
    runtime = SimpleNamespace(STATE=SimpleNamespace(
        job=None, last_job=None, freshness="unverified", domain_session=None))

    addon._draw_domain(Layout(), scene, runtime)

    storey_calls = [item for item in calls if item[0] == "om_analysis.select_storey"]
    if expected_button is None:
        assert storey_calls == []
    else:
        assert storey_calls[0][1]["text"] == expected_button
        assert storey_calls[0][2].value == "ifc-object:s1"
    labels = [item[1]["text"] for item in calls if item[0] == "label"]
    if expected_label is None:
        assert not any(text.startswith("Selected storey:") for text in labels)
    else:
        assert expected_label in labels


def test_space_authoring_reuses_shared_storey_selector(monkeypatch):
    """Space Candidates and B4 render the same storey selector implementation."""
    observed = []
    storeys = (("ifc-object:s1", "Level 1"),)
    monkeypatch.setattr(addon, "_native_scope_candidates",
                        lambda context: (storeys, (("", "No support"),)))
    monkeypatch.setattr(addon, "_draw_storey_selector",
                        lambda layout, scene, choices=None: observed.append((scene, choices)))
    layout = SimpleNamespace(
        label=lambda **kwargs: None, row=lambda **kwargs: layout,
        operator=lambda *args, **kwargs: SimpleNamespace(), separator=lambda: None,
        prop=lambda *args, **kwargs: None)
    scene = SimpleNamespace(om_analysis_storey_ref="", om_analysis_support_source_id="",
                            om_analysis_selected_version_id="")
    runtime = SimpleNamespace(STATE=SimpleNamespace(
        job=None, last_job=None, freshness="unverified", domain_session=None))

    addon._draw_space_authoring(layout, scene, runtime)

    assert observed == [(scene, storeys)]


def test_select_storey_operator_keeps_existing_validation_and_invalidation(monkeypatch):
    """The shared drawer still routes through the existing validated storey operator."""
    class Operator:
        """Fake Blender operator base."""

    fake_bpy = SimpleNamespace(types=SimpleNamespace(Operator=Operator),
                               props=SimpleNamespace(StringProperty=lambda **kwargs: ""))
    invalidated = []
    monkeypatch.setattr(addon, "_sync_bonsai_default_container", lambda context, tool: None)
    monkeypatch.setattr(addon, "_action_runtime", lambda context: SimpleNamespace(
        invalidate_domain_session=lambda reason: invalidated.append(reason)))
    tool = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "bonsai", SimpleNamespace(tool=tool))
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    scene = SimpleNamespace(om_analysis_storey_ref="", om_analysis_support_source_id="floor")
    context = SimpleNamespace(scene=scene)
    operator = next(cls for cls in addon._operator_classes(fake_bpy)
                    if cls.bl_idname == "om_analysis.select_storey")()
    operator.value = "ifc-object:s1"
    operator.report = lambda *_args: None

    assert operator.execute(context) == {"FINISHED"}
    assert scene.om_analysis_storey_ref == "ifc-object:s1"
    assert scene.om_analysis_support_source_id == ""
    assert invalidated == ["analysis storey changed"]


@pytest.mark.parametrize("storey_ref, storey_rows", [
    ("", ()),
    ("ifc-object:missing", ("one",)),
    ("ifc-object:duplicate", ("duplicate", "duplicate")),
])
def test_native_scope_candidates_hide_slabs_without_one_unique_selected_storey(
        monkeypatch, storey_ref, storey_rows):
    """Empty, unknown, and duplicate storey scope cannot expose ambiguous slabs."""
    import types
    storeys = tuple(SimpleNamespace(GlobalId=guid, Name=guid, LongName=None,
                                   is_a=lambda: "IfcBuildingStorey") for guid in storey_rows)
    slab = SimpleNamespace(GlobalId="slab", Name="Ground", ContainedInStructure=(), Decomposes=())
    model = SimpleNamespace(by_type=lambda kind: storeys if kind == "IfcBuildingStorey" else (slab,))
    tool = types.ModuleType("bonsai.tool")
    tool.Ifc = SimpleNamespace(get=lambda: model)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_storey_ref=storey_ref))
    _, supports = addon._native_scope_candidates(context)
    assert supports == (("", "No support"),)


def test_create_space_prerequisites_refuse_mismatched_native_scope(monkeypatch):
    """CreateSpace stops before Bonsai mutation when the selected storey disagrees."""
    import types
    storey = SimpleNamespace(GlobalId="native-storey")
    tool = types.ModuleType("bonsai.tool")
    tool.Root = SimpleNamespace(get_default_container=lambda: storey)
    tool.Model = SimpleNamespace(get_model_props=lambda: SimpleNamespace(rl3=0))
    tool.Ifc = SimpleNamespace(get_entity=lambda _obj: None)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_storey_ref="ifc-object:other"), active_object=None)
    assert "does not match" in addon._create_space_prerequisite_error(context)


def test_create_space_accepts_zero_relative_level_with_native_root(monkeypatch):
    """RL zero is a valid native value when Root supplies the default container."""
    import types
    storey = SimpleNamespace(GlobalId="native-storey")
    tool = types.ModuleType("bonsai.tool")
    tool.Root = SimpleNamespace(get_default_container=lambda: storey)
    tool.Model = SimpleNamespace(get_model_props=lambda: SimpleNamespace(rl3=0))
    tool.Ifc = SimpleNamespace(get_entity=lambda _obj: None)
    bonsai = types.ModuleType("bonsai")
    bonsai.tool = tool
    monkeypatch.setitem(sys.modules, "bonsai", bonsai)
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_storey_ref="ifc-object:native-storey"), active_object=None)
    assert addon._create_space_prerequisite_error(context) is None


def test_grid_coverage_requires_confirmed_geometry():
    """Missing authoritative bounds fail instead of fabricating a 1x1 grid."""
    scene = SimpleNamespace(om_analysis_grid_spacing=0.25, om_analysis_grid_rows=1, om_analysis_grid_columns=1)
    with pytest.raises(ValueError, match="bounds are unavailable"):
        addon._grid_coverage(scene, {}, ())


def test_selected_storey_syncs_bonsai_default_container():
    """Space authoring follows the Analyzer storey before Bonsai writes IFC."""
    storey = SimpleNamespace(GlobalId="storey-guid", is_a=lambda: "IfcBuildingStorey")
    calls = []
    model = SimpleNamespace(by_guid=lambda guid: storey if guid == "storey-guid" else None)
    tool = SimpleNamespace(Ifc=SimpleNamespace(get=lambda: model),
                           Spatial=SimpleNamespace(set_default_container=lambda entity: calls.append(entity)))
    context = SimpleNamespace(scene=SimpleNamespace(om_analysis_storey_ref="ifc-object:storey-guid"))
    assert addon._sync_bonsai_default_container(context, tool=tool) is None
    assert calls == [storey]


def test_empty_depsgraph_update_is_neutral():
    """An empty Blender depsgraph callback must not cancel a running analysis."""
    assert addon._depsgraph_updates_are_neutral(SimpleNamespace(updates=())) is True


def test_space_job_status_draws_native_progress_bar():
    """Running Space analysis exposes the stage progress control in Blender UI."""
    calls = []
    layout = SimpleNamespace(
        label=lambda **kwargs: calls.append(("label", kwargs)),
        progress=lambda **kwargs: calls.append(("progress", kwargs)),
        operator=lambda name, **kwargs: calls.append(("operator", name)),
    )
    runtime = SimpleNamespace(STATE=SimpleNamespace(
        job=SimpleNamespace(stage="capture", lifecycle="capturing", metrics={}, error=None),
        last_job=None, freshness="unverified", domain_session=None,
    ))
    addon._draw_space_job_status(layout, runtime)
    assert any(kind == "progress" and item["factor"] == pytest.approx(0.20)
               for kind, item in calls)
    assert ("operator", "om_analysis.cancel") in calls

def test_b4_panel_shows_progress_and_boxed_candidates():
    """B4 keeps progress and candidate controls beside its own launch button."""
    calls = []

    class Layout:
        """Record native layout operations without Blender."""

        def label(self, **kwargs):
            """Record labels."""
            calls.append(('label', kwargs))

        def prop(self, *args, **kwargs):
            """Accept scene controls."""

        def operator(self, name, **kwargs):
            """Record operator identities and accept their properties."""
            calls.append(('operator', name))
            return SimpleNamespace()

        def row(self, **kwargs):
            """Reuse the recorder for one row."""
            return self

        def box(self):
            """Record the visible candidate container."""
            calls.append(('box', None))
            return self

        def progress(self, **kwargs):
            """Record the native progress bar."""
            calls.append(('progress', kwargs))

    runtime = SimpleNamespace(STATE=SimpleNamespace(
        job=SimpleNamespace(stage='capture', lifecycle='capturing', metrics={}, error=None),
        last_job=None, freshness='unverified', domain_session={
            'candidates': [{'version_id': 'room-1', 'name': 'Room 1', 'area_m2': 12.5, 'holes': 0}],
            'current': {'status': 'not_available'}, 'attempt': {},
        }))
    addon._draw_domain(Layout(), SimpleNamespace(
        om_analysis_selected_version_id='', om_analysis_storey_ref='ifc-object:S2'), runtime)
    assert any(kind == 'progress' for kind, _ in calls)
    assert ('box', None) in calls
    assert ('operator', 'om_analysis.b4_select') in calls
    assert ('operator', 'om_analysis.candidate_eye') in calls
    assert any(kind == 'label' and '12.5' in item['text'] for kind, item in calls)
    assert any(kind == 'label' and item['text'] == 'World XY; cut 1.5 m above selected storey'
               for kind, item in calls)


@pytest.mark.parametrize("drawer", [addon._draw_space_authoring, addon._draw_domain])
@pytest.mark.parametrize("domain_kind", ["authored_ifcspace", "inferred"])
@pytest.mark.parametrize("selected_id", ["room-1", "", "missing"])
def test_candidate_panels_expose_explicit_domain_confirmation(monkeypatch, drawer, domain_kind, selected_id):
    """Both panels provide real consent without offering to recreate native Spaces."""
    calls = []
    layout = SimpleNamespace(
        label=lambda **kwargs: None, prop=lambda *args, **kwargs: None,
        operator=lambda name, **kwargs: calls.append(name) or SimpleNamespace(),
        row=lambda **kwargs: layout, box=lambda: layout, separator=lambda: None)
    monkeypatch.setattr(addon, "_native_scope_candidates", lambda context: ((), ()))
    candidate = {"version_id": "room-1", "domain_kind": domain_kind, "area_m2": 12.25}
    runtime = SimpleNamespace(STATE=SimpleNamespace(
        job=None, last_job=None, freshness="current", domain_session={
            "candidates": [candidate], "current": {"status": "not_available"}, "attempt": {}}))
    scene = SimpleNamespace(om_analysis_storey_ref="", om_analysis_selected_version_id=selected_id)

    drawer(layout, scene, runtime)

    assert ("om_analysis.b4_confirm" in calls) == (selected_id == "room-1")
    expected_create = drawer == addon._draw_space_authoring and domain_kind != "authored_ifcspace" and selected_id == "room-1"
    assert ("om_analysis.create_space_from_candidate" in calls) == expected_create


def test_b4_panel_shows_failure_without_cached_result():
    """An early failure is visible where the user clicked, before any cache exists."""
    labels = []
    layout = SimpleNamespace(label=lambda **kw: labels.append(kw['text']),
                             prop=lambda *a, **kw: None, operator=lambda *a, **kw: None)
    runtime = SimpleNamespace(STATE=SimpleNamespace(job=None, domain_session=None, freshness='unverified',
        last_job=SimpleNamespace(stage='observe_start', lifecycle='failed', error='capture refused', metrics={})))
    addon._draw_domain(layout, SimpleNamespace(), runtime)
    assert 'capture refused' in labels


def test_region_panel_keeps_eye_preview_after_restoring_saved_regions(monkeypatch):
    """Drawing saved Region history must not erase candidate eye highlights."""
    from blender_addon.order_analyzer_ui import region_overlay
    preview = {"version_id": "visible-candidate"}
    monkeypatch.setattr(region_overlay, "_CANDIDATE_PREVIEWS", ())
    monkeypatch.setattr(region_overlay, "install", lambda context: None)
    monkeypatch.setattr(addon, "_draw_space_authoring",
                        lambda *args: region_overlay.set_candidate_previews((preview,)))
    monkeypatch.setattr(addon, "_scene_token", lambda context: "scene")
    layout = SimpleNamespace(prop=lambda *a, **kw: None, label=lambda **kw: None,
                             operator=lambda *a, **kw: None)
    runtime = SimpleNamespace(find_region_manifest=lambda **kw: {"records": ()})
    scene = SimpleNamespace()
    addon._draw_regions(layout, scene, runtime, SimpleNamespace(scene=scene))
    assert region_overlay._CANDIDATE_PREVIEWS == (preview,)


