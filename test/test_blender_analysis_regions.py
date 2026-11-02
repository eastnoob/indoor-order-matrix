"""Focused contracts for persisted region records and GPU-only outlines."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ..blender_addon.order_analyzer_ui import regions, region_overlay
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_addon.order_analyzer_ui import runtime
from blender_addon.order_analyzer_ui import _scene_token


def test_region_manifest_round_trip_is_strict_and_historical_on_restore():
    """A saved region list retains identity facts without reviving consent."""
    record = regions.build_region_record(
        region_id="region-1", name="Room 1", storey_ref="ifc-object:storey-1",
        plane_uuid="plane-1", plane_revision=2, source_id="space-1",
        geometry_refs=("ifc-mesh:space-1",),
        outline=(((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0), (0.0, 0.0)),),
        status="confirmed", confirmation={"action_id": "confirm-1"},
    )
    encoded = regions.encode_manifest([record], active_region_id="region-1", storey_ref="ifc-object:storey-1")
    restored = regions.decode_manifest(encoded)
    assert restored["active_region_id"] == "region-1"
    assert restored["records"][0]["status"] == "historical"
    assert restored["records"][0]["source_id"] == "space-1"
    with pytest.raises(ValueError, match="digest"):
        regions.decode_manifest(encoded.replace('"region-1"', '"tampered"', 1))


def test_region_upsert_deduplicates_same_source_and_outline():
    """Repeated confirmation selects one stable record instead of duplicating it."""
    base = regions.build_region_record(
        region_id="region-1", name="Room", storey_ref=None, plane_uuid="plane", plane_revision=1,
        source_id="space", geometry_refs=(), outline=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),),
    )
    updated, selected = regions.upsert_record((base,), {**base, "region_id": "new-id"})
    assert selected == "region-1"
    assert len(updated) == 1


@pytest.mark.parametrize("origin", ["adopted", "created_from_b4"])
def test_region_compositions_restore_as_recheck_with_provenance_only(origin):
    """Save/reopen retains observed native identities without persisting live consent."""
    plane_binding = {"version": 1, "project_global_id": "project-A", "camera_guid": "camera-A",
        "plane_uuid": "plane", "plane_revision": 1, "origin": [0, 0, 0],
        "basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "observation_digest": "a" * 64}
    space_binding = {"version": 1, "project_global_id": "project-A", "space_guid": "space-A",
        "source_id": "ifc-object:space-A", "storey_ref": "ifc-object:storey-A",
        "geometry_digest": "b" * 64, "origin": origin,
        "provenance": {"method": "native_capture", "authoring": {"candidate_digest": "c" * 64}}}
    record = regions.build_region_record(region_id="r", name="Room", storey_ref="ifc-object:storey-A",
        plane_uuid="plane", plane_revision=1, source_id="space-A", geometry_refs=("ifc-mesh:space-A",),
        outline=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),),
        plane_binding=plane_binding, space_binding=space_binding, confirmation={"action_id": "confirm"})
    restored = regions.decode_manifest(regions.encode_manifest((record,)))["records"][0]
    assert restored["plane_binding"] == plane_binding and restored["space_binding"] == space_binding
    assert restored["status"] == "recheck" and restored["confirmation"] == {}
    assert restored["review"] == "requires_recheck"
    assert record["status"] == "confirmed"


def test_region_selected_wall_scope_round_trips_and_distinguishes_equal_geometry():
    """Persisted inferred regions retain scope identity and never merge across wall sets."""
    common = dict(
        name="Room", storey_ref="ifc-object:storey", plane_uuid="plane", plane_revision=1,
        source_id=None, geometry_refs=(), outline=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),),
    )
    first = regions.build_region_record(
        region_id="region-1", selected_wall_refs=("ifc-object:wall-b", "ifc-object:wall-a"), **common)
    second = regions.build_region_record(
        region_id="region-2", selected_wall_refs=("ifc-object:wall-c", "ifc-object:wall-a"), **common)
    restored = regions.decode_manifest(regions.encode_manifest((first, second)))
    assert restored["records"][0]["selected_wall_refs"] == (
        "ifc-object:wall-a", "ifc-object:wall-b")
    updated, selected = regions.upsert_record((first,), second)
    assert selected == "region-2"
    assert len(updated) == 2


def test_region_overlay_builds_lines_without_native_objects():
    """GPU cache conversion emits closed line segments and never needs Blender data."""
    record = regions.build_region_record(
        region_id="region-1", name="Room", storey_ref=None, plane_uuid="plane", plane_revision=1,
        source_id="space", geometry_refs=(), outline=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),),
    )
    lines = region_overlay.build_line_data((record,), selected_id="region-1")
    assert len(lines["vertices"]) == 5
    assert len(lines["indices"]) == 4
    assert lines["styles"][0]["selected"] is True


def test_region_overlay_transforms_plane_local_rings_to_elevated_world_space():
    """Persisted plane origin and basis keep an upper-floor outline at its authored height."""
    record = regions.build_region_record(
        region_id="region-upper", name="Upper room", storey_ref="ifc-object:storey-2",
        plane_uuid="plane-upper", plane_revision=1, source_id="space-upper", geometry_refs=(),
        outline=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),),
        plane_origin=(0.0, 0.0, 3.0),
    )
    lines = region_overlay.build_line_data((record,))
    assert lines["vertices"][0] == (0.0, 0.0, pytest.approx(3.02))
    assert lines["vertices"][1] == (1.0, 0.0, pytest.approx(3.02))


def test_region_overlay_handler_uses_only_space_view_draw_api(monkeypatch):
    """Installing and removing the outline handler never touches bpy.data objects."""
    class SpaceView3D:
        """Fake Blender view type exposing only draw-handler methods."""
        handlers = []
        @classmethod
        def draw_handler_add(cls, callback, args, region, phase):
            cls.handlers.append((callback, args, region, phase))
            return cls.handlers[-1]
        @classmethod
        def draw_handler_remove(cls, handler, region):
            cls.handlers.remove(handler)
    monkeypatch.setitem(sys.modules, "bpy", SimpleNamespace(types=SimpleNamespace(SpaceView3D=SpaceView3D)))
    context = SimpleNamespace(space_data=SpaceView3D)
    region_overlay.install(context)
    assert SpaceView3D.handlers and SpaceView3D.handlers[0][3] == "POST_VIEW"
    assert SpaceView3D.handlers[0][1] == ()
    region_overlay.uninstall()
    assert not SpaceView3D.handlers


def test_region_manifest_rejects_unknown_schema_and_consent_fields():
    """A malformed or consent-bearing manifest cannot become runtime authority."""
    with pytest.raises(ValueError, match="schema"):
        regions.decode_manifest(json.dumps({"schema_version": 999}))
    record = regions.build_region_record(
        region_id="region-1", name="Room", storey_ref=None, plane_uuid="plane", plane_revision=1,
        source_id="space", geometry_refs=(), outline=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),),
    )
    manifest = regions.decode_manifest(regions.encode_manifest((record,)))
    assert "domain_session" not in manifest
    assert "confirmation_binding" not in manifest


def test_runtime_region_text_uses_scene_binding_and_restores_history():
    """Region Text is tagged to one scene and restores display history only."""
    class Text:
        """Small fake Blender Text datablock."""
        def __init__(self, name):
            self.name, self.body, self.props, self.use_fake_user = name, "", {}, False
        def clear(self):
            self.body = ""
        def write(self, value):
            self.body += value
        def as_string(self):
            return self.body
        def __setitem__(self, key, value):
            self.props[key] = value
        def get(self, key, default=None):
            return self.props.get(key, default)
    class Texts(dict):
        """Map-like fake Text collection."""
        def new(self, name):
            value = Text(name)
            self[name] = value
            return value
    fake = SimpleNamespace(data=SimpleNamespace(texts=Texts()))
    record = regions.build_region_record(
        region_id="region-1", name="Room", storey_ref=None, plane_uuid="plane", plane_revision=1,
        source_id="space", geometry_refs=(), outline=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),),
    )
    encoded = regions.encode_manifest((record,))
    text = runtime.embed_region_manifest(encoded, scene_token="scene-a", bpy_module=fake)
    assert text.get("om_analysis_role") == "region_list"
    assert text.get("om_analysis_scene_token") == "scene-a"
    restored = runtime.restore_region_manifest(text.as_string())
    assert restored["records"][0]["status"] == "historical"


def test_scene_token_survives_pointer_change_and_isolates_same_named_scenes():
    """Persisted scene UUIDs survive reopen-like pointer changes and avoid name collisions."""
    class Scene:
        """Minimal scene custom-property mapping with a mutable native pointer."""
        def __init__(self, name):
            self.name, self.pointer, self.props = name, 1, {}
        def as_pointer(self):
            """Return the current process-local pointer."""
            return self.pointer
        def get(self, key, default=None):
            """Read one persisted custom property."""
            return self.props.get(key, default)
        def __setitem__(self, key, value):
            self.props[key] = value
    first = Scene("Scene")
    second = Scene("Scene")
    first_context = SimpleNamespace(scene=first)
    second_context = SimpleNamespace(scene=second)
    first_token = _scene_token(first_context)
    first.pointer = 99
    assert _scene_token(first_context) == first_token
    assert _scene_token(second_context) != first_token

