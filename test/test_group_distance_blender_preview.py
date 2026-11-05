"""Check route presentation coordinates and exact result identity without Blender."""

import importlib
import json
import math
from copy import deepcopy

import pytest

from .test_blender_analysis_board import _result, wire


def _renderer():
    """Load the optional native renderer without starting Blender."""
    name = "scripts.design.group_level.render_group_distance_blender"
    assert importlib.util.find_spec(name) is not None, "native route renderer is missing"
    return importlib.import_module(name)


def test_route_coordinates_undo_offset_and_use_plane_before_native_units():
    """A rotated translated plane and centimetre scene must retain world position."""
    plane = {"origin": [10, 20, 1.6], "basis": [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]}
    points = _renderer().native_route_points([[5, 2], [6, 2]], plane, [3, -4], .01, 1.626)
    assert points == pytest.approx([(400, 2200, 162.6), (400, 2300, 162.6)])


@pytest.mark.parametrize("bad", [[float("nan"), 2], [True, 2], [1, 2, 3]])
def test_route_coordinates_reject_invalid_recorded_points(bad):
    """Malformed saved points must fail before creating display geometry."""
    plane = {"origin": [0, 0, 1.6], "basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
    with pytest.raises(ValueError):
        _renderer().native_route_points([bad], plane, [0, 0], 1, 1.626)


def test_route_coordinates_do_not_flatten_tilted_plane():
    """A horizontal board cannot silently depict a route in an unsupported plane."""
    plane = {"origin": [0, 0, 1.6], "basis": [[1, 0, 0], [0, .8, .6], [0, -.6, .8]]}
    with pytest.raises(ValueError, match="horizontal"):
        _renderer().native_route_points([[1, 2]], plane, [0, 0], 1, 1.626)


def _recorded():
    """Provide a literal single-cell route bound to a real validated wire fixture."""
    result = _result()
    document = wire.plain(result.document)
    reference = {"kind": result.kind, "result_id": result.result_id, "digest": result.digest}
    request = document["tables"]["snapshot"]["request"]
    manifest = {"query_context": {"result_ref": reference, "geometry_query": request["geometry_query"]},
                "algorithm_version": "group-distance/1", "schema_version": "group-distance/v1",
                "analysis_plane": dict(request["plane"]), "domain": dict(document["identity"]["domain_identity"]),
                "grid": {"origin": [0, 0], "spacing": 1, "n_rows": 1, "n_cols": 1},
                "origin_offset": [0, 0], "source_identity": dict(document["identity"]["project_source_identity"])}
    observation = {"pair_id": "pair", "centroid_free_space_hybrid": {"status": "computed", "value": 2},
                   "route": {"cell_keys": [[0, 0]], "points": [[.5, .5]],
                             "source_centroid": [-1, .5], "target_centroid": [2, .5],
                             "source_access": {"proxy_point": [0, .5], "cell_center": [.5, .5]},
                             "target_access": {"proxy_point": [1, .5], "cell_center": [.5, .5]}}}
    # This fixture's minimal wire omits optional lattice facts; supply the actual frozen grid in both views.
    document["tables"]["lattice"] = manifest["grid"]
    return manifest, observation, document, reference


def _diagonal_recorded():
    """Use abstract cell coordinates to check topology, without representing a scene."""
    manifest, observation, document, reference = _recorded()
    manifest.update(algorithm_version="group-distance/2", schema_version="group-distance/v2",
                    edge_support_version="eight-neighbor-two-flank-occurrences/1")
    manifest["grid"].update(n_rows=2, n_cols=2)
    document["cells"] = [deepcopy(document["cells"][0]) for _ in range(4)]
    route = observation["route"]
    route.update(cell_keys=[[0, 0], [1, 1]], points=[[.5, .5], [1.5, 1.5]],
                 guard_cell_keys=[[0, 1], [1, 0]], support_cell_keys=[[0, 0], [0, 1], [1, 0], [1, 1]])

    def reference_for(row, column):
        """Form exact publication addresses independently of the renderer helper."""
        return f"free-space:{reference['result_id']}:{reference['digest']}:cell:{row}:{column}"

    route["guard_query_refs"] = [reference_for(0, 1), reference_for(1, 0)]
    route["support_query_refs"] = [reference_for(*key) for key in route["support_cell_keys"]]
    route["source_access"]["query_ref"] = reference_for(0, 0)
    route["target_access"].update(cell_center=[1.5, 1.5], query_ref=reference_for(1, 1))
    route["edges"] = [{"from": [0, 0], "to": [1, 1], "edge_key": [[0, 0], [1, 1]],
                       "occupancy_query_refs": [reference_for(0, 0), reference_for(1, 1)],
                       "guard_cell_keys": [[0, 1], [1, 0]], "guard_query_refs": route["guard_query_refs"],
                       "edge_support_version": manifest["edge_support_version"], "weight": math.sqrt(2)}]
    return manifest, observation, document, reference


def test_v2_diagonal_requires_both_exact_known_empty_flanks():
    """The new native consumer accepts only the recorded no-corner-cut diagonal."""
    manifest, observation, document, reference = _diagonal_recorded()
    assert _renderer().prepare_route(manifest, observation, document, reference)["main"] == [[.5, .5], [1.5, 1.5]]
    document["cells"][1]["value"] = True
    with pytest.raises(ValueError, match="flank"):
        _renderer().prepare_route(manifest, observation, document, reference)


@pytest.mark.parametrize("change", ["guard", "guard_ref", "endpoint_ref", "access_ref", "coverage", "model"])
def test_v2_diagonal_rejects_stale_or_incomplete_support(change):
    """Saved support cannot be retargeted, omitted, or relabeled without rejection."""
    manifest, observation, document, reference = _diagonal_recorded()
    route = observation["route"]
    if change == "guard":
        route["edges"][0]["guard_cell_keys"] = [[0, 1]]
    elif change == "guard_ref":
        route["edges"][0]["guard_query_refs"] = ["stale", "stale"]
    elif change == "endpoint_ref":
        route["edges"][0]["occupancy_query_refs"] = ["stale", "stale"]
    elif change == "access_ref":
        route["source_access"]["query_ref"] = "stale"
    elif change == "coverage":
        route["support_cell_keys"] = [[0, 0], [1, 1]]
    else:
        manifest["edge_support_version"] = "unrestricted-diagonal"
    with pytest.raises(ValueError):
        _renderer().prepare_route(manifest, observation, document, reference)


def test_historical_v1_does_not_silently_accept_diagonals():
    """Reading a historical schema must retain that schema's original neighbor rule."""
    manifest, observation, document, reference = _diagonal_recorded()
    manifest.update(algorithm_version="group-distance/1", schema_version="group-distance/v1")
    with pytest.raises(ValueError, match="neighbor model"):
        _renderer().prepare_route(manifest, observation, document, reference)


def _clearance_recorded():
    """Extend the abstract diagonal with off-path side support in occupied coarse cells."""
    manifest, observation, document, reference = _diagonal_recorded()
    manifest.update(algorithm_version="group-distance/3", schema_version="group-distance/v3",
                    edge_support_version="eight-neighbor-two-flank-occurrences-directional-clearance/1")
    manifest["grid"].update(n_rows=3, n_cols=3)
    document["cells"] = [deepcopy(document["cells"][0]) for _ in range(9)]
    route = observation["route"]
    heading = [1 / math.sqrt(2), 1 / math.sqrt(2)]
    route["state_keys"] = [[[0, 0], heading], [[1, 1], heading]]
    edge = route["edges"][0]
    edge.update({"from": route["state_keys"][0], "to": route["state_keys"][1],
                 "edge_support_version": manifest["edge_support_version"]})
    for kind, key in (("clearance", [0, 2]), ("turn", [2, 0])):
        witness = {"min_left_m": .3, "min_right_m": .4, "min_total_m": .7,
                   "limiting_left_m": .3, "limiting_right_m": .4, "limiting_total_m": .7,
                   "side_sample_cell_keys": [key], "side_sample_statuses": ["established"],
                   "side_sample_query_refs": [f"free-space:{reference['result_id']}:{reference['digest']}:cell:{key[0]}:{key[1]}"]}
        witness["limiting_position_m" if kind == "clearance" else "limiting_angle_fraction"] = 0.
        edge[kind] = witness
        document["cells"][key[0] * 3 + key[1]]["value"] = True
    route["clearance"] = {"min_left_m": .3, "min_right_m": .4, "min_total_m": .7,
                          "edge_witnesses": [edge["clearance"]], "turn_witnesses": [edge["turn"]]}
    route["support_cell_keys"] = sorted([*route["support_cell_keys"], [0, 2], [2, 0]])
    route["support_query_refs"] = [f"free-space:{reference['result_id']}:{reference['digest']}:cell:{row}:{column}"
                                  for row, column in route["support_cell_keys"]]
    return manifest, observation, document, reference


@pytest.mark.parametrize("status", ["established", "conditional"])
def test_clearance_side_support_accepts_authoritative_occupied_coarse_cells(status):
    """Side queries gate confidence while exact geometry already owns the empty ray portion."""
    manifest, observation, document, reference = _clearance_recorded()
    document["cells"][6]["status"] = status
    observation["route"]["edges"][0]["turn"]["side_sample_statuses"] = [status]
    layer = _renderer().prepare_route(manifest, observation, document, reference)
    assert len(layer["main"]) == 2 and len(layer["clearance_bands"]) == 1


@pytest.mark.parametrize("change", ["unknown", "invalid", "not_available", "outside", "ref", "status", "coverage", "cell"])
def test_clearance_side_support_rejects_missing_or_stale_dependencies(change):
    """The native reader cannot omit or retarget an edge or turn side dependency."""
    manifest, observation, document, reference = _clearance_recorded()
    route, witness = observation["route"], observation["route"]["edges"][0]["turn"]
    if change in {"unknown", "invalid", "not_available", "outside"}:
        document["cells"][6]["status"] = change
    elif change == "ref":
        witness["side_sample_query_refs"] = ["stale"]
    elif change == "status":
        witness["side_sample_statuses"] = ["conditional"]
    elif change == "coverage":
        route["support_cell_keys"].remove([2, 0])
    else:
        witness["side_sample_cell_keys"] = [[3, 0]]
    with pytest.raises(ValueError):
        _renderer().prepare_route(manifest, observation, document, reference)


def _group_projection_recorded():
    """Build abstract component records solely to check complete group display binding."""
    from ..features.field_core import fingerprint_evidence_dependency as fingerprint

    groups = [{"group_id": "a", "components": [{"exterior": [[0, 0], [1, 0], [0, 1]], "holes": []},
                                               {"exterior": [[1, 1], [2, 1], [1, 2]], "holes": []}],
               "source_refs": ["member:1", "member:2"], "status": "available", "explanation": ""},
              {"group_id": "b", "components": [{"exterior": [[3, 0], [4, 0], [3, 1]], "holes": []}],
               "source_refs": ["member:3"], "status": "available", "explanation": ""}]
    records = [{**group, "components": sorted(group["components"], key=fingerprint),
                "source_refs": sorted(group["source_refs"], key=fingerprint)} for group in groups]
    geometry = {"analysis_plane": {}, "origin_offset": [0, 0], "domain": {}, "groups": groups}
    manifest = {**{key: geometry[key] for key in ("analysis_plane", "origin_offset", "domain")},
                "group_ids": ["a", "b"], "dependency_fingerprints": {"groups": fingerprint(records)}}
    observation = {"group_ids": ["a", "b"], "lineage": {"group_source_refs": {g["group_id"]: g["source_refs"] for g in groups}},
                   "geometry_audit": {g["group_id"]: {"source_refs": g["source_refs"]} for g in groups}}
    return geometry, manifest, observation


def test_group_highlights_retain_all_members_and_components():
    """A highlighted endpoint is its complete group projection, including disjoint members."""
    geometry, manifest, observation = _group_projection_recorded()
    groups = _renderer().prepare_groups(geometry, manifest, observation)
    assert len(groups[0]["components"]) == 2
    assert groups[0]["source_refs"] == ["member:1", "member:2"]
    geometry["groups"][0]["components"].pop()
    with pytest.raises(ValueError, match="fingerprint"):
        _renderer().prepare_groups(geometry, manifest, observation)


def test_comparison_rejects_another_source_or_pair():
    """Old and new routes must refer to identical physical inputs and endpoint groups."""
    manifest = {key: {} for key in ("source_identity", "analysis_plane", "domain", "grid", "query_context", "dependency_fingerprints")}
    manifest.update(origin_offset=[0, 0], group_ids=["a", "b"])
    observation = {"pair_id": "pair", "group_ids": ["a", "b"], "center_to_center_euclidean": {"value": 3}}
    _renderer().prepare_comparison(manifest, observation, manifest, observation)
    changed = deepcopy(manifest)
    changed["source_identity"] = {"id": "other"}
    with pytest.raises(ValueError, match="same recorded input"):
        _renderer().prepare_comparison(manifest, observation, changed, observation)


def test_recorded_route_keeps_endpoint_offsets_separate():
    """Rendering cannot join centroids into the free-cell polyline."""
    manifest, observation, document, reference = _recorded()
    layer = _renderer().prepare_route(manifest, observation, document, reference)
    assert layer["main"] == [[.5, .5]]
    assert layer["offsets"] == [[[-1, .5], [0, .5], [.5, .5]], [[2, .5], [1, .5], [.5, .5]]]


@pytest.mark.parametrize("change", ["ref", "domain", "point", "occupied"])
def test_wrong_route_dependency_or_cell_is_rejected(change):
    """A route from another ref/domain or over occupied cells cannot be drawn on this field."""
    manifest, observation, document, reference = _recorded()
    if change == "ref":
        manifest["query_context"]["result_ref"] = {**reference, "digest": "b" * 64}
    elif change == "domain":
        manifest["domain"]["id"] = "other"
    elif change == "point":
        observation["route"]["points"][0] = [1.5, .5]
    else:
        document["cells"] = [{**document["cells"][0], "value": True}]
    with pytest.raises(ValueError):
        _renderer().prepare_route(manifest, observation, document, reference)


def test_no_route_status_is_not_replaced_by_a_line():
    """Unreachable pairs remain route-free rather than drawing a centroid shortcut."""
    manifest, observation, document, reference = _recorded()
    observation.update(route=None, centroid_free_space_hybrid={"status": "unreachable", "value": None})
    layer = _renderer().prepare_route(manifest, observation, document, reference)
    assert layer["main"] == layer["offsets"] == []
    assert layer["status"] == "unreachable"


def test_run_loader_rejects_mismatched_pair_locator(tmp_path):
    """A stale pair index must not select an unrelated observation for native display."""
    manifest = {"dependency_fingerprints": {"grid": "recorded"}, "expected_pair_ids": ["pair"]}
    observation = {"pair_id": "pair", "group_ids": ["a", "b"], "dependencies": manifest["dependency_fingerprints"],
                   "route": None}
    for name, value in (("run_manifest.json", manifest), ("observations.json", [observation]),
                        ("pair_index.json", [{"pair_id": "other", "group_ids": ["a", "b"], "observation_index": 0}])):
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="pair index"):
        _renderer().load_run(tmp_path, "pair")


def test_run_loader_retains_requested_no_route_pair(tmp_path):
    """Selecting an unavailable pair cannot fall back to another pair that has a route."""
    manifest = {"dependency_fingerprints": {"grid": "recorded"}, "expected_pair_ids": ["pair"]}
    observation = {"pair_id": "pair", "group_ids": ["a", "b"], "dependencies": manifest["dependency_fingerprints"],
                   "route": None}
    for name, value in (("run_manifest.json", manifest), ("observations.json", [observation]),
                        ("pair_index.json", [{"pair_id": "pair", "group_ids": ["a", "b"], "observation_index": 0}])):
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    assert _renderer().load_run(tmp_path, "pair")[1] == observation


@pytest.mark.parametrize("width,height", [(20.15, 12), (12, 20.15)])
def test_native_landscape_camera_contains_complete_board(width, height):
    """Horizontal camera scale must fit both board extents with a visible margin."""
    aspect = 1280 / 1050
    span = _renderer().plan_ortho_scale(width, height, aspect)
    assert span >= width * 1.13
    assert span / aspect >= height * 1.13 - 1e-10


def _section_route():
    """Provide abstract numeric witnesses solely to test display coordinate conversion."""
    return {"points": [[0, 0], [2, 0]], "state_keys": [[[0, 0], [0, 1]], [[0, 1], [1, 0]]],
            "clearance": {"min_left_m": .1, "min_right_m": .2, "min_total_m": .7,
                          "edge_witnesses": [{"min_left_m": .1, "min_right_m": .2,
                                               "limiting_position_m": .5, "limiting_left_m": .3,
                                               "limiting_right_m": .4, "limiting_total_m": .7}],
                          "turn_witnesses": []}}


def test_cross_section_uses_same_position_values_instead_of_independent_minima():
    """The displayed span cannot combine smaller side minima from other positions."""
    section = _renderer().clearance_cross_section(_section_route())
    assert section["center"] == [.5, 0]
    assert section["left"] == [.5, .3] and section["right"] == [.5, -.4]
    assert section["total_m"] == .7 and section["kind"] == "edge"


def test_clearance_band_uses_independent_guaranteed_sides_without_relabeling_the_total():
    """A display rectangle retains side guarantees rather than inventing a total bottleneck."""
    route = _section_route()
    route["clearance"]["edge_witnesses"][0].update(min_left_m=.1, min_right_m=.2)
    band, = _renderer().clearance_bands(route)
    assert band == {"segment_index": 0, "points": [[0, .1], [2, .1], [2, -.2], [0, -.2]],
                    "left_m": .1, "right_m": .2}
    assert _renderer().clearance_bands(None) == []
    assert _renderer().clearance_bands({"points": [[0, 0]], "clearance": None}) == []
    route["clearance"]["edge_witnesses"][0]["min_left_m"] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        _renderer().clearance_bands(route)


def test_cross_section_selects_narrower_saved_turn_with_its_rotated_heading():
    """A narrower turn must be located at its vertex and saved heading fraction."""
    route = _section_route()
    route["clearance"]["turn_witnesses"] = [{"limiting_angle_fraction": .5, "limiting_left_m": .25,
                                             "limiting_right_m": .35, "limiting_total_m": .6}]
    section = _renderer().clearance_cross_section(route)
    assert section["kind"] == "turn" and section["center"] == [0, 0]
    assert section["left"] == pytest.approx([-.25 / math.sqrt(2), .25 / math.sqrt(2)])
    assert section["right"] == pytest.approx([.35 / math.sqrt(2), -.35 / math.sqrt(2)])


@pytest.mark.parametrize("key,value", [("limiting_position_m", -1), ("limiting_position_m", True),
                                        ("limiting_left_m", float("nan")), ("limiting_total_m", .6)])
def test_cross_section_rejects_malformed_saved_witness(key, value):
    """Display conversion must not repair or replace invalid saved metric values."""
    route = _section_route()
    route["clearance"]["edge_witnesses"][0][key] = value
    with pytest.raises(ValueError):
        _renderer().clearance_cross_section(route)
    assert _renderer().clearance_cross_section(None) is None


def _comparison_run(directory, bundle, result):
    """Publish a nonspatial contract fixture with producer-style file hashes."""
    from features.field_core import _json_value

    directory.mkdir(exist_ok=True)
    result = deepcopy(result)
    manifest = result["manifest"]
    plain = _json_value(bundle)
    for key in ("source_identity", "analysis_plane", "domain", "grid", "query", "query_context",
                "origin_offset", "dependency_fingerprints", "clearance_policy"):
        if key in manifest or key != "clearance_policy" or bundle.clearance_policy is not None:
            manifest[key] = plain[key]
    documents = {"input_bundle.json": plain, "run_manifest.json": manifest,
                 "observations.json": result["observations"], "pair_index.json": result["pair_index"],
                 "scene_geometry.json": {}}
    for name, payload in documents.items():
        (directory / name).write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    (directory / "coverage_report.json").write_text(json.dumps({"output_hashes": {
        name: _renderer()._file_hash(directory / name) for name in documents}}), encoding="utf-8")
    return manifest, result["observations"][0]


@pytest.mark.parametrize("mutation", [None, "source", "plane", "domain", "groups", "origin_offset", "query",
                                        "physical_occupancy", "samples", "query_context", "grid", "scene", "cell_samples", "stale_query"])
def test_clearance_comparison_accepts_only_authenticated_policy_binding(tmp_path, mutation):
    """Even coherently rehashed physical/query changes cannot enter a policy comparison."""
    from dataclasses import replace
    from features.group_distance import calculate_group_pair_distances, group_distance_input_fingerprints, serialize_group_distance_result
    from scripts.design.group_level.run_group_distance_ifc import bind_clearance_policy
    from .test_group_distance import _missing_bundle

    bundle = _missing_bundle()
    bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
    constrained = bind_clearance_policy(bundle, {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55})
    previous, current = (serialize_group_distance_result(calculate_group_pair_distances(item)) for item in (bundle, constrained))
    if mutation == "source":
        constrained = replace(constrained, source_identity={"id": "changed-source"})
    elif mutation == "plane":
        constrained = replace(constrained, analysis_plane={"identity": "changed-plane"})
    elif mutation == "domain":
        constrained = replace(constrained, domain={"id": "changed-domain"})
    elif mutation == "groups":
        constrained = replace(constrained, groups=(replace(constrained.groups[0], explanation="changed"), *constrained.groups[1:]))
    elif mutation == "origin_offset":
        constrained = replace(constrained, origin_offset=(1, 0))
    elif mutation == "query":
        constrained = replace(constrained, query=replace(constrained.query, frame="changed-frame"))
    elif mutation == "physical_occupancy":
        constrained = replace(constrained, physical_occupancy=())
    elif mutation == "samples":
        constrained = replace(constrained, free_space_samples={"cells": []})
    elif mutation == "query_context":
        constrained = replace(constrained, query_context={**dict(constrained.query_context), "capture": "changed"})
    elif mutation == "grid":
        constrained = replace(constrained, grid=replace(constrained.grid, spacing=2))
    constrained = replace(constrained, dependency_fingerprints=group_distance_input_fingerprints(constrained))
    if mutation == "stale_query":
        constrained = replace(constrained, dependency_fingerprints={**dict(constrained.dependency_fingerprints), "query": "stale"})
    baseline_dir, run_dir = tmp_path / "baseline", tmp_path / "current"
    baseline_manifest, baseline = _comparison_run(baseline_dir, bundle, previous)
    manifest, observation = _comparison_run(run_dir, constrained, current)
    if mutation == "cell_samples":
        manifest["cell_samples"] = [{"status": "changed"}]
        (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        coverage = json.loads((run_dir / "coverage_report.json").read_text(encoding="utf-8"))
        coverage["output_hashes"]["run_manifest.json"] = _renderer()._file_hash(run_dir / "run_manifest.json")
        (run_dir / "coverage_report.json").write_text(json.dumps(coverage), encoding="utf-8")
    if mutation == "scene":
        (run_dir / "scene_geometry.json").write_text('{"changed":true}', encoding="utf-8")
        coverage = json.loads((run_dir / "coverage_report.json").read_text(encoding="utf-8"))
        coverage["output_hashes"]["scene_geometry.json"] = _renderer()._file_hash(run_dir / "scene_geometry.json")
        (run_dir / "coverage_report.json").write_text(json.dumps(coverage), encoding="utf-8")
    if mutation is None:
        _renderer().prepare_comparison(manifest, observation, baseline_manifest, baseline, run_dir, baseline_dir)
        with pytest.raises(ValueError, match="authenticated"):
            _renderer().prepare_comparison(manifest, observation, baseline_manifest, baseline)
        (run_dir / "input_bundle.json").write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="producer bytes"):
            _renderer().prepare_comparison(manifest, observation, baseline_manifest, baseline, run_dir, baseline_dir)
    else:
        with pytest.raises(ValueError, match="comparison"):
            _renderer().prepare_comparison(manifest, observation, baseline_manifest, baseline, run_dir, baseline_dir)


def test_model_labels_preserve_the_actual_eight_neighbor_baseline():
    """A policy comparison must not label the previous v2 route as four-neighbor."""
    assert _renderer().distance_model_label({"algorithm_version": "group-distance/2"}) == "8-neighbor, no corner cut"
    assert "clearance" in _renderer().distance_model_label({"algorithm_version": "group-distance/3", "clearance_policy": {"min_total_m": .55}})
