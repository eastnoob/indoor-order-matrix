"""Focused persistence and resolution tests for native plane settings."""

import json
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blender_addon.order_analyzer_ui.plane_settings import NativePlaneSettings


def _record(guid="camera-A", *, project="project-A", revision=1, z=2.5):
    """Build one validated native drawing observation using the existing wire shape."""
    return {
        "version": 1,
        "project_global_id": project,
        "camera_guid": guid,
        "plane_uuid": "bonsai-camera:ifc:" + guid,
        "plane_revision": revision,
        "origin": [4.0, 6.0, z],
        "basis": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "observation_digest": "a" * 64,
    }


def test_legacy_binding_migrates_lazily_and_roundtrips_strictly():
    """A legacy binding becomes one catalog record while new JSON remains strict."""
    record = _record()
    legacy = json.dumps(record)
    settings = NativePlaneSettings.from_json("", legacy_binding=legacy)
    assert settings.default_plane_id == record["plane_uuid"]
    encoded = json.dumps(settings.to_dict(), sort_keys=True)
    restored = NativePlaneSettings.from_json(encoded)
    assert restored.to_dict() == settings.to_dict()


def test_settings_detach_nested_callers_and_resolution_uses_catalog():
    """Caller mutations cannot alter frozen observations, defaults, or package overrides."""
    first, second = _record(), _record("camera-B", z=3.5)
    source = {first["plane_uuid"]: first, second["plane_uuid"]: second}
    settings = NativePlaneSettings(source, first["plane_uuid"])
    source[first["plane_uuid"]]["origin"][2] = 99.0
    assert settings.resolve()["origin"][2] == 2.5
    selected = settings.with_observation(second).with_package_override("free-space", second["plane_uuid"])
    assert selected.resolve("free-space")["camera_guid"] == "camera-B"
    inherited = selected.with_package_override("free-space", None)
    assert inherited.resolve("free-space")["camera_guid"] == "camera-A"


def test_invalid_defaults_overrides_projects_and_schema_fail_closed():
    """Dangling selections, mixed projects, and malformed JSON cannot fall back to legacy data."""
    first = _record()
    with pytest.raises(ValueError, match="default"):
        NativePlaneSettings({first["plane_uuid"]: first}, "missing")
    with pytest.raises(ValueError, match="override"):
        NativePlaneSettings({first["plane_uuid"]: first}, first["plane_uuid"], {"free-space": "missing"})
    second = _record("camera-B", project="project-B")
    with pytest.raises(ValueError, match="projects"):
        NativePlaneSettings({first["plane_uuid"]: first, second["plane_uuid"]: second}, first["plane_uuid"])
    malformed = json.dumps({"version": 99, "records": {}, "default_plane_id": None, "package_overrides": {}})
    with pytest.raises(ValueError, match="version"):
        NativePlaneSettings.from_json(malformed, legacy_binding=json.dumps(first))
    with pytest.raises(ValueError, match="package id"):
        NativePlaneSettings({first["plane_uuid"]: first}, first["plane_uuid"]).with_package_override("", None)


def test_identity_and_record_mutation_are_rejected():
    """Native identities remain tied to their persisted IFC drawing GUID."""
    record = _record()
    bad = deepcopy(record)
    bad["plane_uuid"] = "arbitrary-uuid"
    with pytest.raises(ValueError, match="identity"):
        NativePlaneSettings({bad["plane_uuid"]: bad}, bad["plane_uuid"])
