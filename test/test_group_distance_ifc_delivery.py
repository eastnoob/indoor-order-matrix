"""Focused boundary and retained real-IFC delivery checks; no synthetic layouts."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import sys

import pytest

from features.group_distance import group_distance_input_fingerprints
from scripts.design.group_level.run_group_distance_ifc import (
    bind_clearance_policy, confirmed_domain, confirmed_s4, read_json, rebind_retained_input, retained_input,
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


def test_clearance_policy_rebinds_retained_query_identity():
    """An opt-in constraint changes identity while the no-policy handoff stays intact."""
    from .test_group_distance import _missing_bundle

    bundle = _missing_bundle()
    bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
    baseline = bind_clearance_policy(bundle, None)
    constrained = bind_clearance_policy(bundle, {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55})
    assert baseline is bundle
    assert constrained.clearance_policy == {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55}
    assert constrained.query_context["clearance_policy"] == constrained.clearance_policy
    assert dict(constrained.dependency_fingerprints) == group_distance_input_fingerprints(constrained)
    assert constrained.dependency_fingerprints["query"] != bundle.dependency_fingerprints["query"]


def test_constrained_endpoint_only_route_passes_complete_result_validation():
    """A shared access cell needs endpoint arithmetic but has no corridor to certify."""
    from types import SimpleNamespace
    import networkx as nx

    from features import group_distance as kernel
    from features.field_core import _json_value

    grid = kernel.GridDescriptor("endpoint-only", "plane", (0, 0), 1, 1, 3)
    sample = {"cell_key": (0, 1), "status": "established", "value": False, "center": (1.5, .5), "query_ref": "middle"}
    samples = {(0, 1): sample}
    source = {"free_cell": (0, 1), "footprint_cell": (0, 0), "heading": (1., 0.),
              "access_key": ("a",), "offset": 1., "proxy_point": (1., .5), "cell_center": (1.5, .5)}
    target = {"free_cell": (0, 1), "footprint_cell": (0, 2), "target_heading": (1., 0.),
              "access_key": ("b",), "offset": 1., "proxy_point": (2., .5), "cell_center": (1.5, .5)}
    sources = kernel._state_accesses({"a": source})
    targets = kernel._state_accesses({"b": target}, target=True)
    graph = nx.DiGraph()
    distances, best, unknown = kernel._recover_source(graph, sources, samples, False)
    route = kernel._target_route(graph, targets, sources, distances, best, unknown, samples, False)
    assert route["edges"] == () and route["clearance"] is None
    domain = {"components": [{"exterior": [(0, 0), (3, 0), (3, 1), (0, 1), (0, 0)], "holes": []}]}
    bundle = SimpleNamespace(groups=("a", "b"), domain=domain, grid=grid)
    observation = {"pair_id": "pair", "group_ids": ["a", "b"], "route": route,
                   "center_to_center_euclidean": {"value": 2.},
                   "centroid_free_space_hybrid": {"value": 2., "status": "computed", "tie_uncertainty": False},
                   "geometry_audit": {"a": {"centroid": (.5, .5)}, "b": {"centroid": (2.5, .5)}},
                   "lineage": {"optimistic_lower_bound": None, "observed_query_refs": ("middle",)}}
    result = _json_value({"manifest": {"algorithm_version": kernel.CLEARANCE_ALGORITHM_VERSION,
                         "schema_version": kernel.CLEARANCE_SCHEMA_VERSION,
                         "edge_support_version": kernel.CLEARANCE_EDGE_SUPPORT_VERSION,
                         "expected_pair_ids": ["pair"], "cell_samples": [sample],
                         "clearance_policy": {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55}},
                         "observations": [observation],
                         "pair_index": [{"pair_id": "pair", "group_ids": ["a", "b"], "observation_index": 0}]})
    report = validate_result(result, bundle)
    assert report["selected_paths_checked"] == 1 and report["selected_edges_checked"] == 0
    result["observations"][0]["route"]["clearance"] = {}
    with pytest.raises(ValueError, match="endpoint-only"):
        validate_result(result, bundle)


@pytest.mark.parametrize("policy", [
    {"min_left_m": .225, "min_right_m": .225},
    {"min_left_m": -.001, "min_right_m": .225, "min_total_m": .55},
    {"min_left_m": True, "min_right_m": .225, "min_total_m": .55},
])
def test_clearance_policy_rejects_incomplete_or_invalid_thresholds(policy):
    """Reject malformed directional thresholds before any distance calculation."""
    from .test_group_distance import _missing_bundle

    with pytest.raises(ValueError, match="clearance_policy"):
        bind_clearance_policy(_missing_bundle(), policy)


def test_exact_result_cli_passes_complete_policy_and_rejects_partial_policy(monkeypatch):
    """CLI constraints must reach the exact-result runner as one complete policy."""
    from scripts.design.group_level import run_group_distance_free_space as runner

    policies = []

    def record_run(*_args, clearance_policy=None):
        """Record parser handoff without opening files or calculating spatial routes."""
        policies.append(clearance_policy)
        return {}

    monkeypatch.setattr(runner, "run", record_run)
    arguments = ["run_group_distance_free_space", "--free-space-result", "result.json",
                 "--native-request", "request.json", "--publication-receipt", "receipt.json",
                 "--allow-historical", "--output-dir", "unused"]
    monkeypatch.setattr(sys, "argv", arguments)
    runner.main()
    monkeypatch.setattr(sys, "argv", arguments + ["--min-left-m", ".225", "--min-right-m", ".225", "--min-total-m", ".55"])
    runner.main()
    assert policies == [None, {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55}]
    monkeypatch.setattr(sys, "argv", arguments + ["--min-left-m", ".225"])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2 and len(policies) == 2


def test_clearance_comparison_allows_only_the_policy_binding_difference(tmp_path):
    """Comparison tolerates policy identity changes but rejects changed source metadata."""
    from features.field_core import _json_value
    from features.group_distance import calculate_group_pair_distances, serialize_group_distance_result
    from scripts.design.group_level import run_group_distance_free_space as runner
    from .test_group_distance import _missing_bundle

    # Missing-input records exercise identity guards without inventing geometry or distance readings.
    bundle = _missing_bundle()
    fingerprints = group_distance_input_fingerprints(bundle)
    bundle = replace(bundle, grid=replace(bundle.grid, domain_fingerprint=fingerprints["domain"],
                                         occupancy_fingerprint=fingerprints["occupancy"]))
    bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
    constrained = bind_clearance_policy(bundle, {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55})
    previous, current = (serialize_group_distance_result(calculate_group_pair_distances(item))
                         for item in (bundle, constrained))
    reference = {"kind": "free_space_run", "result_id": "contract-only", "digest": "contract-only"}
    for payload in (previous, current):
        payload["manifest"]["free_space_result"] = {"result_ref": reference}
    baseline, output = tmp_path / "baseline", tmp_path / "constrained"
    (baseline / "preview").mkdir(parents=True)
    output.mkdir()
    write_json(baseline / "input_bundle.json", _json_value(bundle))
    write_json(output / "input_bundle.json", _json_value(constrained))
    for directory in (baseline, output):
        write_json(directory / "scene_geometry.json", {})
    write_json(baseline / "run_manifest.json", previous["manifest"])
    write_json(baseline / "observations.json", previous["observations"])
    preview = baseline / "preview/index.html"
    preview.write_text('<script type="application/json" id="data">' + json.dumps({"observations": previous["observations"]}) + "</script>", encoding="utf-8")
    write_json(baseline / "coverage_report.json", {"output_hashes": {
        "observations.json": runner.file_hash(baseline / "observations.json")}})
    write_json(baseline / "preview/coverage_report.json", {"output_hashes": {"index.html": runner.file_hash(preview)}})
    summary = runner.write_comparison(baseline, current, output)
    assert summary["input_bundle_and_scene_geometry_byte_identical"] is False
    assert summary["geometry_lattice_samples_unchanged"] is True
    assert summary["baseline_model"] == "group-distance/2" and summary["current_model"] == "group-distance/3"
    no_policy = tmp_path / "no_policy"
    no_policy.mkdir()
    write_json(no_policy / "input_bundle.json", _json_value(bundle))
    write_json(no_policy / "scene_geometry.json", {})
    historical = runner.write_comparison(baseline, previous, no_policy)
    assert historical["input_bundle_and_scene_geometry_byte_identical"] is True
    assert "mean_improvement_m" in historical and "max_absolute_improvement" in historical
    changed = replace(constrained, source_identity={"id": "changed-source"})
    changed = replace(changed, dependency_fingerprints=group_distance_input_fingerprints(changed))
    write_json(output / "input_bundle.json", _json_value(changed))
    with pytest.raises(ValueError, match="beyond the clearance policy binding"):
        runner.write_comparison(baseline, current, output)


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
