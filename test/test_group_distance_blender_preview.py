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
