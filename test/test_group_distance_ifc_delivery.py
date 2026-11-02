"""Focused boundary and retained real-IFC delivery checks; no synthetic layouts."""

from copy import deepcopy
from pathlib import Path

import pytest

from features.group_distance import group_distance_input_fingerprints
from scripts.design.group_level.run_group_distance_ifc import (
    confirmed_s4, read_json, retained_input, validate_result, write_json,
)
from scripts.design.group_level.render_group_distance_preview import base_svg, html_document

ROOT = Path(__file__).resolve().parents[1]
S4 = ROOT / "outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z"
RUN = ROOT / "outputs/design/group_distance_ifc/run_v1"


def test_confirmed_s4_requires_active_source_bound_handoff():
    """Reject changed confirmation/source metadata while reusing real retained facts."""
    if not S4.exists():
        pytest.skip("retained confirmed S4 input is not installed")
    manifest = read_json(S4 / "s4_confirmed_manifest.json")
    confirmed_s4(S4, manifest["source"])
    changed = deepcopy(manifest["source"])
    changed["sha256"] = "different-source"
    with pytest.raises(ValueError, match="another IFC source"):
        confirmed_s4(S4, changed)


def test_real_ifc_complete_pair_paths_and_fingerprints():
    """Validate the actual 37-group package and its selected spatial paths."""
    if not (RUN / "run_manifest.json").exists():
        pytest.skip("run the pinned real IFC before spatial acceptance")
    bundle = retained_input(RUN / "input_bundle.json")
    assert dict(bundle.dependency_fingerprints) == group_distance_input_fingerprints(bundle)
    manifest, observations, index = (read_json(RUN / name) for name in ("run_manifest.json", "observations.json", "pair_index.json"))
    report = validate_result({"manifest": manifest, "observations": observations, "pair_index": index}, bundle)
    assert report["expected_pair_count"] == report["observation_count"] == report["index_count"] == 666
    assert manifest["same_bundle_replay"]["equal"]


def test_real_ifc_renderer_has_every_pair_locator():
    """Every real pair remains selectable without a distance calculation in rendering."""
    if not (RUN / "run_manifest.json").exists():
        pytest.skip("run the pinned real IFC before renderer acceptance")
    manifest, observations, geometry = (read_json(RUN / name) for name in ("run_manifest.json", "observations.json", "scene_geometry.json"))
    aliases = {identity: f"G{number:02d}" for number, identity in enumerate(manifest["group_ids"], 1)}
    html = html_document(manifest, observations, geometry, aliases, base_svg(geometry, manifest, aliases))
    for identity in manifest["expected_pair_ids"]:
        assert f'value="{identity}"' in html
        assert f'href="#{identity}"' in html
    assert "null/not_applicable" in html
    assert "endpoint offsets" in html


def test_retained_ifc_input_rejects_changed_saved_dependency(tmp_path):
    """Reject changed real-input metadata before any implementation binding upgrade."""
    path = RUN / "input_bundle.json"
    if not path.exists():
        pytest.skip("run the pinned real IFC before retained-input checks")
    data = read_json(path)
    data["source_identity"]["sha256"] = "changed-source-metadata"
    candidate = tmp_path / "input_bundle.json"
    write_json(candidate, data)
    with pytest.raises(ValueError, match="saved dependency fingerprints"):
        retained_input(candidate)
