"""Exact-result handoff checks using the actual retained IFC publication and run."""

from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import math
import csv

import pytest

from adapters import blender_analysis_result_wire as wire
from adapters import free_space_distance as bridge
from adapters.free_space_distance import _domain_meshes, distance_input_from_free_space
from features import group_distance as kernel
from features.geometry_views import component_shape
from scripts.design.group_level.run_group_distance_free_space import load_json, retained_read_context
from scripts.design.group_level import run_group_distance_free_space as runner
from scripts.design.group_level.run_group_distance_ifc import read_json, retained_input, validate_result
from scripts.design.group_level import run_group_distance_ifc as ifc_runner

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "order_analyzer_free_space_cache/outputs/blender_analysis/jobs/fe3243c13b3f45daac8744efc46f3962"
RECEIPT = ROOT.parent / "order_analyzer_free_space_cache/outputs/design/free_space_prerequisite/verification/native-free-codec-restored-publication.json"
RUN = ROOT / "outputs/design/group_distance_ifc/run_v3_finite_band_result"


def test_result_identity_distinguishes_historical_and_eight_neighbor_semantics():
    """Readers accept both explicit models and reject an unsupported mixed identity."""
    historical = {"algorithm_version": "group-distance/1", "schema_version": "group-distance/v1"}
    current = {"algorithm_version": "group-distance/2", "schema_version": "group-distance/v2",
               "edge_support_version": "eight-neighbor-two-flank-occurrences/1"}
    assert ifc_runner.distance_topology(historical) == 4
    assert ifc_runner.distance_topology(current) == 8
    for changed in ({**current, "schema_version": historical["schema_version"]},
                    {**current, "edge_support_version": "unsupported"}):
        with pytest.raises(ValueError, match="distance model identity"):
            ifc_runner.distance_topology(changed)


@pytest.fixture(scope="module")
def actual_publication():
    """Open accepted bytes with expectations from the independent native receipt."""
    if not (SOURCE / "result.json").exists() or not RECEIPT.exists():
        pytest.skip("accepted native free-space publication is not installed")
    native, receipt = load_json(SOURCE / "request.json"), load_json(RECEIPT)
    reference, context = retained_read_context(native, receipt)
    snapshot = wire.open_analysis_result([load_json(SOURCE / "result.json")], result_ref=reference, context=context)
    return native, receipt, snapshot


@pytest.fixture(scope="module")
def actual_bundle():
    """Reuse the actual immutable adapter output rather than manufacturing a layout."""
    if not (RUN / "coverage_report.json").exists():
        pytest.skip("execute the accepted free-space distance run before spatial acceptance")
    return retained_input(RUN / "input_bundle.json")


@pytest.fixture(scope="module")
def stored_distance_free_space(actual_publication, actual_bundle, tmp_path_factory):
    """Store the actual nonempty native document under a complete B address."""
    import hashlib
    from features.cache_paths import CacheAddress
    from features.cache_store import CacheStore
    from features.output_port_cache import OutputPortRef

    native, receipt, snapshot = actual_publication
    _, context = retained_read_context(native, receipt)
    validator = bridge.build_distance_free_space_validator(actual_bundle, native_request=native, context=context)
    store = CacheStore(tmp_path_factory.mktemp("distance-native-free-space"))
    payload = (SOURCE / "result.json").read_bytes()
    address = CacheAddress(kernel.fingerprint_evidence_dependency(actual_bundle.source_identity),
                           "blender-analysis", "combined", "raw", snapshot.ref.digest)
    store.put(address, contract={"result_ref": wire.plain(actual_bundle.free_space_samples["result_ref"])},
              payload=payload, payload_format="json", validator=validator)
    reference = OutputPortRef(address.source_fingerprint, address.package_id, address.output_port,
                              address.identity, address.layer, hashlib.sha256(payload).hexdigest())
    return store, reference, validator


def test_distance_free_space_validator_reopens_actual_samples_without_group_projection(
        actual_publication, actual_bundle, stored_distance_free_space, monkeypatch):
    """Owner validation consumes exact actual samples without recalculating member geometry."""
    store, reference, validator = stored_distance_free_space
    def forbidden(*args, **kwargs):
        """Detect unnecessary member projection or occupancy execution during a read."""
        pytest.fail("native validation recalculated independent geometry")
    monkeypatch.setattr(bridge, "_group_projections", forbidden)
    assert store.get(reference.address, validator=validator) is not None


def test_distance_free_space_validation_memo_is_local_to_exact_bytes_and_intent(
        actual_publication, actual_bundle, stored_distance_free_space, monkeypatch):
    """Repeated B validation reuses a success only for this callback's identical bytes."""
    from features.cache_store import CacheValidationContext
    store, reference, validator = stored_distance_free_space
    entry = store.get(reference.address, validator=validator)
    payload = entry.payload_paths[0].read_bytes()
    context = CacheValidationContext(reference.address, None, None, entry.receipt["contract"])
    def forbidden(*args, **kwargs):
        """An identical validated payload needs no second full wire/sample traversal."""
        pytest.fail("reopened an already validated identical native payload")
    with monkeypatch.context() as patch:
        patch.setattr(wire, "open_analysis_result", forbidden)
        validator(payload, context)
    changed = wire.load_json(payload.decode("utf-8"))
    changed["digest"] = "0" * 64
    with pytest.raises(ValueError):
        validator(wire.canonical_json(changed).encode("utf-8"), context)
    native, receipt, _ = actual_publication
    _, independent = retained_read_context(native, receipt)
    incompatible = bridge.build_distance_free_space_validator(actual_bundle, native_request=native,
        context=replace(independent, require_current=True, allow_historical=False))
    with pytest.raises(ValueError, match="current read"):
        incompatible(payload, context)


@pytest.mark.parametrize("fault", ["query", "lattice", "sample", "ref", "currentness"])
def test_distance_free_space_validator_rejects_independent_context_drift(
        actual_publication, actual_bundle, stored_distance_free_space, fault):
    """A valid saved document cannot authorize different current sample intent."""
    native, receipt, _ = actual_publication
    store, reference, _ = stored_distance_free_space
    _, context = retained_read_context(native, receipt)
    bundle = actual_bundle
    if fault == "query":
        bundle = replace(bundle, query=replace(bundle.query, revision="different-current-query"))
    elif fault == "lattice":
        bundle = replace(bundle, grid=replace(bundle.grid, spacing=bundle.grid.spacing * 2))
    elif fault == "sample":
        samples = dict(bundle.free_space_samples)
        cells = list(samples["cells"])
        index = next(index for index, item in enumerate(cells) if type(item["value"]) is bool)
        cells[index] = {**cells[index], "value": not cells[index]["value"]}
        bundle = replace(bundle, free_space_samples={**samples, "cells": cells})
    elif fault == "ref":
        samples = dict(bundle.free_space_samples)
        bundle = replace(bundle, free_space_samples={**samples, "result_ref": {**samples["result_ref"], "digest": "0" * 64}})
    else:
        context = replace(context, require_current=True, allow_historical=False)
    validator = bridge.build_distance_free_space_validator(bundle, native_request=native, context=context)
    with pytest.raises(ValueError):
        store.get(reference.address, validator=validator)


def test_exact_adapter_refuses_another_request_capture_or_domain(actual_publication):
    """Reject swapped native inputs before they can contribute group geometry."""
    native, _, snapshot = actual_publication
    changed = {**native, "request": {**native["request"], "request_id": "different-request"}}
    with pytest.raises(ValueError, match="native request"):
        distance_input_from_free_space(snapshot, changed)
    changed = {**native, "job_binding": {**native["job_binding"], "job_id": "different-publication"}}
    with pytest.raises(ValueError, match="native request"):
        distance_input_from_free_space(snapshot, changed)
    capture = {**native["canonical_capture"], "identity": {**native["canonical_capture"]["identity"],
        "project_global_id": "different-native-project"}}
    with pytest.raises(ValueError, match="native capture"):
        distance_input_from_free_space(snapshot, {**native, "canonical_capture": capture})
    meshes = deepcopy(native["domain_geometries"])
    meshes[0]["vertices"][0][0] += 0.1
    with pytest.raises(ValueError, match="domain mesh bytes"):
        _domain_meshes(native["canonical_capture"], native["request"],
            snapshot.payload["tables"]["snapshot"]["provenance"], meshes)


def test_receipt_expectations_are_external_and_reject_wrong_native_binding(actual_publication):
    """An altered publication receipt cannot authorize the saved producer request."""
    native, receipt, snapshot = actual_publication
    reference, context = retained_read_context(native, receipt)
    assert reference == snapshot.ref and context.allow_historical is True
    assert context.require_current is False and context.current_observation is None
    changed = {**receipt, "binding": {**receipt["binding"], "job_id": "another-job"}}
    with pytest.raises(ValueError, match="publication receipt"):
        retained_read_context(native, changed)


def test_exact_adapter_never_executes_analysis(actual_publication, actual_bundle, monkeypatch):
    """A successful consumer reads saved cells without entering the analysis executor."""
    from features import analysis_requests
    native, _, snapshot = actual_publication
    def forbidden(*_args, **_kwargs):
        """Fail on an unintended regeneration while consuming the exact publication."""
        pytest.fail("exact-result adapter invoked execute_analysis_request")
    monkeypatch.setattr(analysis_requests, "execute_analysis_request", forbidden)
    # Reuse the already verified real group projections to isolate this seam;
    # the actual runner separately performs native-capture group projection.
    def retained_groups(*_args):
        """Supply the unchanged real group projections from the completed run."""
        return actual_bundle.groups
    monkeypatch.setattr(bridge, "_group_projections", retained_groups)
    recreated = distance_input_from_free_space(snapshot, native)
    assert recreated.dependency_fingerprints == actual_bundle.dependency_fingerprints


def test_saved_lattice_samples_and_query_are_exact(actual_publication, actual_bundle):
    """The distance handoff preserves every saved bool/status and sample locator."""
    _, _, snapshot = actual_publication
    saved = actual_bundle.free_space_samples
    assert kernel._saved_samples_error(actual_bundle) is None
    assert wire.plain(saved["result_ref"]) == {
        "kind": snapshot.ref.kind, "result_id": snapshot.ref.result_id, "digest": snapshot.ref.digest}
    assert wire.plain(saved["lattice"]) == wire.plain(snapshot.payload["tables"]["lattice"])
    assert actual_bundle.query.height_band == (-1.600000023841858, 0)
    assert actual_bundle.origin_offset == (0, 0)
    counts = Counter()
    for cell, sample in zip(saved["cells"], wire.iter_analysis_samples(snapshot), strict=True):
        for stored, original in (("status", "status"), ("value", "value"), ("explanation", "explanation")):
            assert wire.plain(cell[stored]) == wire.plain(sample[original])
        assert wire.plain(saved["source_ids"][cell["source_refs"]["index"]]) == wire.plain(sample["source_ids"])
        if cell["support"] is None:
            assert sample["support"] is None
        else:
            support = cell["support"]
            expanded = {key: value for key, value in saved["support_context"].items()
                        if key not in support["removed_context_keys"]}
            expanded.update({key: value for key, value in support.items()
                             if key not in {"context_ref", "removed_context_keys", "exact_sample_ref"}})
            assert wire.plain(expanded) == wire.plain(sample["support"])
            assert support["exact_sample_ref"] == cell["query_ref"]
        assert snapshot.ref.digest in cell["query_ref"]
        assert cell["query_ref"] == cell["provenance_ref"]
        counts["free" if cell["value"] is False else "occupied" if cell["value"] is True else cell["status"]] += 1
    assert counts == {"free": 14047, "occupied": 7023, "outside": 3372}
    assert len(actual_bundle.groups) == 37 and len(actual_bundle.physical_occupancy) == 343


def test_saved_graph_bypasses_generation_and_keeps_exact_bindings(actual_bundle, monkeypatch):
    """The actual graph can only read saved cells; its source lattice is immutable."""
    def forbidden(*_args, **_kwargs):
        """Fail if the exact-result route attempts a second occupancy calculation."""
        pytest.fail("exact-result handoff invoked FreeSpaceField")
    monkeypatch.setattr(kernel, "FreeSpaceField", forbidden)
    samples, observed, optimistic, frontier = kernel._graphs(actual_bundle, component_shape(actual_bundle.domain["components"]))
    assert len(samples) == 24442 and len(observed) > 0 and observed.number_of_edges() > 0
    assert set(observed) == set(optimistic) == set(frontier)
    for cell in observed:
        assert samples[cell]["value"] is False and samples[cell]["status"] == "established"
    diagonal_count, blocked_corners = 0, 0
    for a, b, edge in observed.edges(data=True):
        assert edge["weight"] == math.dist(samples[a]["center"], samples[b]["center"])
        diagonal = a[0] != b[0] and a[1] != b[1]
        guards = tuple(sorted(((a[0], b[1]), (b[0], a[1])))) if diagonal else ()
        assert edge["guard_cell_keys"] == guards
        assert edge["guard_query_refs"] == tuple(samples[cell]["query_ref"] for cell in guards)
        assert all(cell in observed for cell in guards)
        diagonal_count += diagonal
    for a in observed:
        for b in kernel._route_neighbors(a, actual_bundle.grid):
            if b in observed and a[0] != b[0] and a[1] != b[1]:
                guards = ((a[0], b[1]), (b[0], a[1]))
                if any(cell not in observed for cell in guards):
                    assert not observed.has_edge(a, b)
                    blocked_corners += 1
    assert diagonal_count > 0 and blocked_corners > 0
    saved = actual_bundle.free_space_samples
    changed = {**saved, "query": {**saved["query"], "height_band": None}}
    assert "binding differs" in kernel._saved_samples_error(replace(actual_bundle, free_space_samples=changed))
    changed = {**saved, "cells": saved["cells"][:-1]}
    assert "coverage is incomplete" in kernel._saved_samples_error(replace(actual_bundle, free_space_samples=changed))


@pytest.mark.parametrize("name", ["run_v3_finite_band_result", "run_v4_eight_neighbor"])
def test_actual_complete_routes_have_positive_access_path_lineage_and_replay(actual_bundle, name):
    """Run all numerical path assertions against the real 37-group result package."""
    run = RUN.parent / name
    if not (run / "coverage_report.json").exists():
        pytest.skip("complete the actual topology run before spatial acceptance")
    manifest, observations, index = (read_json(run / name) for name in (
        "run_manifest.json", "observations.json", "pair_index.json"))
    report = validate_result({"manifest": manifest, "observations": observations, "pair_index": index}, actual_bundle)
    assert report["expected_pair_count"] == report["observation_count"] == report["index_count"] == 666
    assert report["selected_paths_checked"] > 0 and report["selected_nodes_checked"] > 0 and report["selected_edges_checked"] > 0
    assert manifest["same_bundle_replay"]["equal"] is True
    assert manifest["same_bundle_replay"]["normalized_sha256"] == manifest["same_bundle_replay"]["repeated_normalized_sha256"]
    assert manifest["free_space_result"]["freshness"] == "historical"
    assert manifest["free_space_result"]["result_ref"] == manifest["query_context"]["result_ref"]
    assert report["route_neighbor_count"] == (4 if run == RUN else 8)
    if run != RUN:
        assert report["selected_diagonal_edges_checked"] > 0
        assert report["selected_guard_occurrences_checked"] == 2 * report["selected_diagonal_edges_checked"]


def test_retained_distance_input_authenticates_original_bytes_and_reference(actual_bundle):
    """Reuse real v3 input only when its original producer hashes and exact ref match."""
    audit = read_json(RUN / "adapter_audit.json")
    reference = wire.ResultRef(**audit["result_ref"])
    bundle, reused = runner.retained_distance_input(RUN, audit["input_files"], reference)
    assert bundle == actual_bundle
    assert reused["retained_input"]["input_bundle_sha256"] == runner.file_hash(RUN / "input_bundle.json")
    changed = {**audit["input_files"], "native_request": {
        **audit["input_files"]["native_request"], "sha256": "different-producing-bytes"}}
    with pytest.raises(ValueError, match="original producing inputs"):
        runner.retained_distance_input(RUN, changed, reference)
    changed_ref = wire.ResultRef(reference.kind, reference.result_id, "0" * 64)
    with pytest.raises(ValueError, match="exact result reference"):
        runner.retained_distance_input(RUN, audit["input_files"], changed_ref)


def test_actual_topology_comparison_preserves_every_pair_and_raw_geometry():
    """The real v4 delivery compares all accepted v3 identities and unrounded values."""
    current = RUN.parent / "run_v4_eight_neighbor"
    if not (current / "comparison_summary.json").exists():
        pytest.skip("generate the authorized actual v4 comparison first")
    summary = read_json(current / "comparison_summary.json")
    with (current / "comparison_rows.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert summary["pair_count"] == len(rows) == len({row["pair_id"] for row in rows}) == 666
    assert summary["pair_ids_groups_euclidean_centroids_unchanged"] is True
    assert summary["input_bundle_and_scene_geometry_byte_identical"] is True
    assert summary["counts"].get("worsened", 0) == 0
    maximum = max(rows, key=lambda row: (float(row["improvement_m"]), row["pair_id"]))
    assert summary["max_absolute_improvement"]["pair_id"] == maximum["pair_id"]
    assert summary["max_absolute_improvement"]["improvement_m"] == float(maximum["improvement_m"])
    assert set(summary["visual_pair_ids"]) <= {row["pair_id"] for row in rows}
