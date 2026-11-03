"""Focused boundary and retained real-IFC delivery checks; no synthetic layouts."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from features.group_distance import group_distance_input_fingerprints
from scripts.design.group_level.run_group_distance_ifc import (
    confirmed_domain, confirmed_s4, read_json, rebind_retained_input, retained_input,
    validate_retained_binding, validate_result, write_json,
)
from scripts.design.group_level.render_group_distance_preview import base_svg, html_document

ROOT = Path(__file__).resolve().parents[1]
S4 = ROOT / "outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z"
RUN = ROOT / "outputs/design/group_distance_ifc/run_v1"
CORRECTED = ROOT / "outputs/design/group_distance_ifc/domain_correction_inspection"


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


def test_corrected_real_domain_requires_matching_candidate_scope_and_mesh(tmp_path):
    """Reject a swapped real scope even if active confirmation metadata is unchanged."""
    if not (CORRECTED / "confirmed_domain_manifest.json").exists():
        pytest.skip("corrected real-domain confirmation is not installed")
    manifest = read_json(CORRECTED / "confirmed_domain_manifest.json")
    result = read_json(CORRECTED / "confirmed_domain_result.json")
    confirmed_domain(CORRECTED, manifest["source"], expected_candidate="S3")
    result["scope_polygon"] = read_json(S4 / "s4_confirm_result.json")["scope_polygon"]
    write_json(tmp_path / "confirmed_domain_manifest.json", manifest)
    write_json(tmp_path / "confirmed_domain_result.json", result)
    with pytest.raises(ValueError, match="exact scope"):
        confirmed_domain(tmp_path, manifest["source"])


def test_corrected_real_cache_rebase_authenticates_old_claims_and_preserves_occupancy():
    """Translate actual cached group/occupancy rings only after authenticating the old handoff."""
    if not (CORRECTED / "confirmed_domain_manifest.json").exists():
        pytest.skip("corrected real-domain confirmation is not installed")
    bundle = retained_input(RUN / "input_bundle.json")
    audit = read_json(RUN / "adapter_audit.json")
    source = read_json(CORRECTED / "confirmed_domain_manifest.json")["source"]
    bad = replace(bundle, query_context={**dict(bundle.query_context), "analysis_plane_fingerprint": "wrong-plane"})
    with pytest.raises(ValueError, match="pinned source/domain/spacing"):
        validate_retained_binding(bad, audit, S4, source, .1)
    rebound, corrected_audit = rebind_retained_input(bundle, audit, old_directory=S4,
        new_directory=CORRECTED, source=source, spacing=.1)
    assert len(rebound.groups) == 37 and len(rebound.physical_occupancy) == 343
    assert corrected_audit["physical_occupancy_records"] == 343
    assert corrected_audit["cache_rebind"]["old_physical_occupancy_records"] == 353
    assert rebound.domain["selected_candidate_id"] == "S3"
    assert corrected_audit["cache_rebind"]["retained_nonboundary_inventory_unchanged"]
    assert dict(rebound.dependency_fingerprints) == group_distance_input_fingerprints(rebound)
    delta = corrected_audit["cache_rebind"]["delta_translation_m"]
    scope = corrected_audit["cache_rebind"]["boundary_scope_reconciliation"]
    assert set(scope["old_members"]).issubset(scope["new_members"])
    assert len(scope["newly_scoped_out_source_ids"]) == 10
    expected = [record for record in bundle.physical_occupancy
                if not set(record["represented_source_ids"]).intersection(scope["new_members"])]
    assert len(expected) == len(rebound.physical_occupancy)
    assert any("ifc-object:2mbfCNlr9T48ZweNBN3dyn" in record["represented_source_ids"] for record in rebound.physical_occupancy)
    for before, after in zip(expected, rebound.physical_occupancy, strict=True):
        assert before["represented_source_ids"] == after["represented_source_ids"]
        for old_component, new_component in zip(before["geometry_components"], after["geometry_components"], strict=True):
            assert new_component["exterior"][0] == pytest.approx([old_component["exterior"][0][i] + delta[i] for i in range(2)])
