"""Independent semantic distance publication and verified-adoption contracts."""

from dataclasses import replace

import pytest

from features.cache_paths import CacheAddress
from features.cache_store import CacheStore
from features.evidence_package_storage import legacy_candidate_contract, serialize_raw_output_bytes
from features import group_distance_evidence_package as owner
from features.group_distance_evidence_package import build_group_distance_parameter_snapshot, run_group_distance_package
from features import group_distance_output_ports as ports
from .test_group_distance import _missing_bundle


def _bundle(total=1.0):
    """Vary policy with explicitly unavailable geometry rather than inventing a scene."""
    return replace(_missing_bundle(), clearance_policy={
        "min_left_m": 0.225, "min_right_m": 0.225, "min_total_m": total,
    })


def _parameters(bundle):
    """Resolve current intent independently through the existing package owner."""
    return build_group_distance_parameter_snapshot(bundle)


def _forbidden(*args, **kwargs):
    """Fail when an exact cache hit unexpectedly executes a producer."""
    pytest.fail("an independently cached producer ran again")


def test_policy_one_two_one_reuses_euclidean_and_restores_path(tmp_path, monkeypatch):
    """Only path versions depend on clearance policy and restoring values restores reuse."""
    store = CacheStore(tmp_path)
    first_bundle, second_bundle = _bundle(), _bundle(2.0)
    first = ports.run_group_distance_ports(first_bundle, store=store, parameters=_parameters(first_bundle))
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    second = ports.run_group_distance_ports(second_bundle, store=store, parameters=_parameters(second_bundle))
    assert second["euclidean_distance"].cache_hit is True
    assert second["path_distance"].cache_hit is False
    assert first["euclidean_distance"].publication.ref == second["euclidean_distance"].publication.ref
    assert first["path_distance"].publication.ref.identity != second["path_distance"].publication.ref.identity
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    restored = ports.run_group_distance_ports(first_bundle, store=store, parameters=_parameters(first_bundle))
    assert all(result.cache_hit for result in restored.values())
    assert restored["path_distance"].publication.ref == first["path_distance"].publication.ref


def test_runner_adopts_combined_entry_before_any_semantic_producer(tmp_path, monkeypatch):
    """Reopen an original B receipt before projecting either standalone view."""
    bundle = _bundle()
    run_group_distance_package(bundle, cache_directory=tmp_path, temporary_cache_root=tmp_path)
    store = CacheStore(tmp_path)
    entry = next(item for item in store.list() if item.address.output_port == "combined")
    original = entry.payload_paths[0].read_bytes()
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    result = ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle), legacy_entry=entry)
    assert all(item.cache_hit and item.cache_reuse == "legacy_adopted" for item in result.values())
    assert all(item.publication.parameter_snapshot == _parameters(bundle) for item in result.values())
    assert entry.payload_paths[0].read_bytes() == original
    assert len(store.list()) == 3


def test_owner_bundle_disagreement_rejected_before_publication(tmp_path):
    """Current intent cannot silently differ from the bundle supplied to the producer."""
    with pytest.raises(ValueError, match="parameters"):
        ports.run_group_distance_ports(_bundle(), store=CacheStore(tmp_path), parameters=_parameters(_bundle(2.0)))


def test_euclidean_source_locator_is_not_a_calculation_input():
    """Recognized factual project identity excludes absolute locator and capture session."""
    first = replace(_bundle(), source_identity={"project_global_id": "project", "frame": "world", "ifc_source_identity": "P:/a.ifc", "capture_digest": "a"})
    second = replace(first, source_identity={**first.source_identity, "ifc_source_identity": "Q:/b.ifc", "capture_digest": "b"})
    a = ports.evaluate_euclidean_port(first, parameters=_parameters(first))
    b = ports.evaluate_euclidean_port(second, parameters=_parameters(second))
    assert a.ref == b.ref


@pytest.mark.parametrize("changed", ["parameters", "source"])
def test_combined_projection_rejects_wrong_current_context(tmp_path, monkeypatch, changed):
    """A valid old receipt cannot authenticate a different current source or intent."""
    bundle = _bundle()
    run_group_distance_package(bundle, cache_directory=tmp_path, temporary_cache_root=tmp_path)
    store = CacheStore(tmp_path)
    entry = next(iter(store.list()))
    original = entry.payload_paths[0].read_bytes()
    current = (_bundle(2.0) if changed == "parameters" else
               replace(bundle, source_identity={"id": "different-source"}))
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    with pytest.raises(ValueError):
        ports.run_group_distance_ports(current, store=store, parameters=_parameters(current), legacy_entry=entry)
    assert all(item.address.output_port == "combined" for item in store.list())
    assert entry.payload_paths[0].read_bytes() == original


def test_combined_without_original_snapshot_stays_historical(tmp_path, monkeypatch):
    """A valid pre-A B receipt is retained without borrowing today's owner defaults."""
    bundle = _bundle()
    current, _ = owner._run_contract(bundle, None)
    historical = legacy_candidate_contract(current)
    address = CacheAddress(owner._distance_source_fingerprint(historical), owner.PACKAGE_ID,
                           "combined", "raw", historical["package_identity"])
    payload = serialize_raw_output_bytes(cache_key=address.identity, contract=historical,
                                         raw_output=owner.evaluate_group_distance_package(bundle))
    store = CacheStore(tmp_path)
    entry = store.put(address, contract=historical, payload=payload,
                      payload_format="evidence-package-cache/v1",
                      validator=owner._distance_raw_validator(owner.build_group_distance_evidence_package(), historical))
    assert "parameter_snapshot" not in historical
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    with pytest.raises(ValueError):
        ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle), legacy_entry=entry)
    assert store.list() == (entry,)
    assert entry.payload_paths[0].read_bytes() == payload


def test_combined_projection_rejects_changed_payload_before_publication(tmp_path):
    """Integrity failure in the original bytes cannot become a semantic receipt."""
    bundle = _bundle()
    run_group_distance_package(bundle, cache_directory=tmp_path, temporary_cache_root=tmp_path)
    store = CacheStore(tmp_path)
    entry = next(iter(store.list()))
    entry.payload_paths[0].write_bytes(entry.payload_paths[0].read_bytes() + b" ")
    with pytest.raises(ValueError):
        ports.project_verified_distance_ports(entry, bundle=bundle, parameters=_parameters(bundle), store=store)
    assert not any(item.address.output_port != "combined" for item in store.list())


def test_direct_combined_projector_preserves_original_calculated_sources(tmp_path):
    """Current source labels remain separate from calculated historical snapshot audit."""
    bundle = _bundle()
    sources = {name: "historical-owner-selection" for name in _parameters(bundle).effective_parameters}
    run_group_distance_package(bundle, cache_directory=tmp_path, temporary_cache_root=tmp_path, parameter_sources=sources)
    store = CacheStore(tmp_path)
    entry = next(iter(store.list()))
    selected = ports.project_verified_distance_ports(entry, bundle=bundle, parameters=_parameters(bundle), store=store)
    assert set(selected) == {"euclidean_distance", "path_distance"}
    for publication in selected.values():
        assert set(publication.parameter_snapshot.parameter_sources.values()) == {"historical-owner-selection"}


def test_corrupt_semantic_entry_is_preserved_and_only_its_port_recomputed(tmp_path, monkeypatch):
    """Storage corruption is quarantined before one selected publication is replaced."""
    bundle = _bundle()
    store = CacheStore(tmp_path)
    first = ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle))
    reference = first["euclidean_distance"].publication.ref
    entry = store.get(reference.address, validator=ports.validate_port_payload)
    corrupted = entry.payload_paths[0].read_bytes() + b" "
    entry.payload_paths[0].write_bytes(corrupted)
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    second = ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle))
    assert second["euclidean_distance"].cache_hit is False
    assert second["path_distance"].cache_hit is True
    assert second["euclidean_distance"].publication.ref == reference
    assert [path.read_bytes() for path in (tmp_path / "quarantine").rglob("payload.json")] == [corrupted]


@pytest.mark.parametrize("warm_semantic", [False, True])
def test_invalid_automatic_combined_does_not_block_independent_ports(tmp_path, monkeypatch, warm_semantic):
    """A damaged optional combined candidate neither blocks hits nor cold calculation."""
    bundle = _bundle()
    run_group_distance_package(bundle, cache_directory=tmp_path, temporary_cache_root=tmp_path)
    store = CacheStore(tmp_path)
    combined = next(iter(store.list()))
    if warm_semantic:
        ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle))
        monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
        monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    corrupted = combined.payload_paths[0].read_bytes() + b" "
    combined.payload_paths[0].write_bytes(corrupted)
    results = ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle))
    assert all(result.cache_hit is warm_semantic for result in results.values())
    assert combined.payload_paths[0].read_bytes() == corrupted


def _repair(bundle, policy):
    """Retain an explicitly declared repair policy with unavailable route readings."""
    saved = ports.kernel.serialize_group_distance_result(ports.kernel.calculate_group_pair_distances(bundle))
    saved.update(schema_version="route-repair/2", method="contract-repair/1", policy=policy)
    for row in saved["observations"]:
        row["directional_repair"] = {"quality": "unresolved_unknown", "method": "contract-repair/1"}
    return saved


@pytest.mark.parametrize("repair_policy", [None, {"min_left_m": .225, "min_right_m": .225, "min_total_m": 2.0}])
def test_path_rejects_repair_policy_disagreement_before_publication(tmp_path, monkeypatch, repair_policy):
    """Historical repair policy must agree with independent current path owner intent."""
    bundle = _bundle()
    repair = _repair(bundle, repair_policy)
    store = CacheStore(tmp_path)
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    with pytest.raises(ValueError, match="repair.*policy"):
        ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle), repaired_result=repair)
    assert not store.list()
    assert ports.euclidean_port_contract(bundle, parameters=_parameters(bundle)).output_port == "euclidean_distance"


@pytest.mark.parametrize("constrained", [False, True])
def test_path_accepts_matching_or_unconstrained_repair_policy(constrained):
    """The gate admits declared matching thresholds and the explicit None policy."""
    bundle = _bundle() if constrained else _missing_bundle()
    publication = ports.evaluate_path_port(bundle, parameters=_parameters(bundle),
                                            repaired_result=_repair(bundle, bundle.clearance_policy))
    assert publication.ref.output_port == "path_distance"


def test_partial_saved_repair_is_rejected_before_any_semantic_publication(tmp_path, monkeypatch):
    """C declares the complete bundle pair scope while the combined API retains subsets."""
    bundle = _bundle()
    repair = _repair(bundle, bundle.clearance_policy)
    repair["observations"] = repair["observations"][:1]
    repair["manifest"].update(expected_pair_count=1,
                              expected_pair_ids=[row["pair_id"] for row in repair["observations"]])
    original, _ = owner._run_contract(bundle, repair)
    assert len(original["target_ids"]) == 1
    store = CacheStore(tmp_path)
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    with pytest.raises(ValueError, match="complete.*pair scope"):
        ports.run_group_distance_ports(bundle, store=store, parameters=_parameters(bundle), repaired_result=repair)
    assert not store.list()
