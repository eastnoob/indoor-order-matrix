"""Verify true pre-parameter-cache receipts through their original readers."""

import hashlib
import json
from pathlib import Path

from adapters import blender_analysis_session as blender
from adapters import free_space_evidence_package as free_space
from adapters import blender_analysis_result_wire as wire
from features import evidence_package_storage as storage
from features import group_axis_potential_field as potential
from .test_evidence_package_lifecycle import _processor


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "test/fixtures/cache_migration/pre_parameter_sidecar"


def _sha256(path):
    """Return the exact digest used by the retained-byte manifest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pre_parameter_receipts_reopen_with_original_readers():
    """All retained families remain readable without recalculation or secret disclosure."""
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    by_family = {item["family"]: item for item in manifest["families"]}

    raw_path = ROOT / by_family["raw"]["relative_path"]
    raw_receipt = json.loads(raw_path.read_text(encoding="utf-8"))
    raw = storage.load_raw_output(raw_path, cache_key=raw_receipt["cache_key"],
                                  contract=raw_receipt["contract"],
                                  package=potential.build_group_axis_potential_package())
    assert raw is not None
    assert _sha256(raw_path) == by_family["raw"]["sha256"]

    processed_path = ROOT / by_family["processed"]["relative_path"]
    assert storage.load_processed_output(processed_path, raw_output=raw,
                                         processor=_processor()) is not None
    assert _sha256(processed_path) == by_family["processed"]["sha256"]

    free_path = ROOT / by_family["authenticated_free_space"]["relative_path"]
    secret = (free_path.parent / ".free_space_cache_key").read_bytes()
    assert len(secret) == 32
    assert free_space._read_cache(free_path, free_path.stem, secret) is not None
    assert _sha256(free_path) == by_family["authenticated_free_space"]["sha256"]

    blender_path = ROOT / by_family["blender_wire"]["relative_path"]
    saved_versions = by_family["blender_wire"]["versions"]["backend_versions"]
    loaded = blender._load_cached_result(blender_path, content_key=blender_path.stem,
                                         versions=saved_versions)
    assert loaded is not None
    assert wire.document_digest(loaded) == loaded["digest"]
    assert _sha256(blender_path) == by_family["blender_wire"]["sha256"]
    current_versions = __import__(
        "features.analysis_requests", fromlist=["_backend_versions"])._backend_versions()
    # Historical readability does not authorize current backend compatibility.
    # B must review the retained wire implementation mismatch before current reuse.
    if json.dumps(current_versions, sort_keys=True) != json.dumps(saved_versions, sort_keys=True):
        assert blender._load_cached_result(
            blender_path, content_key=blender_path.stem,
            versions=current_versions,
        ) is None


def test_retained_authenticated_pre_a_explicit_path_reconstructs_and_refuses_foreign_bytes(
    tmp_path, monkeypatch,
):
    """The unchanged authenticated baseline supplies historical values without execution."""
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    family = next(item for item in manifest["families"]
                  if item["family"] == "authenticated_free_space")
    path = ROOT / family["relative_path"]
    original = path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == family["sha256"]
    receipt = wire.load_json(original.decode("utf-8"))
    secret = (path.parent / ".free_space_cache_key").read_bytes()
    snapshot = free_space.package.build_free_space_parameter_snapshot(
        receipt["document"]["tables"]["snapshot"]["request"])

    def forbidden(*args, **kwargs):
        """Fail if historical receipt reconstruction attempts geometry execution."""
        raise AssertionError("explicit historical lookup executed geometry")

    monkeypatch.setattr(free_space.requests, "execute_analysis_request", forbidden)
    lookup = free_space._read_cache_entry(
        path, family["key"], secret, expected_parameter_snapshot=snapshot,
        legacy_adopter=free_space._reconstruct_legacy_free_space_contract,
    )
    assert lookup is not None
    assert lookup.reuse_origin["mode"] == "adopted_legacy"
    assert lookup.reuse_origin["verification_mode"] == "owner_reconstructed_parameters"
    assert lookup.reuse_origin["origin_cache_key"] == receipt["cache_key"]
    assert lookup.reuse_origin["origin_payload_fingerprint"] == receipt["document_digest"]
    assert wire.canonical_json(lookup.reuse_origin["origin_contract"]) == wire.canonical_json(
        receipt["contract"])
    assert lookup.parameter_status["exact_match"] is False
    assert lookup.parameter_status["recompute_required"] is False
    assert wire.canonical_json(lookup.document) == wire.canonical_json(receipt["document"])
    assert json.dumps(
        wire.plain(lookup.cached_contract)["parameter_snapshot"]["calculated_parameters"],
        sort_keys=True, separators=(",", ":"),
    ) == json.dumps(
        snapshot.to_json()["calculated_parameters"],
        sort_keys=True, separators=(",", ":"),
    )
    foreign_secret = bytes([secret[0] ^ 1]) + secret[1:]
    assert free_space._read_cache_entry(
        path, family["key"], foreign_secret, expected_parameter_snapshot=snapshot,
        legacy_adopter=free_space._reconstruct_legacy_free_space_contract,
    ) is None
    assert free_space._read_cache_entry(
        path, "foreign-key", secret, expected_parameter_snapshot=snapshot,
        legacy_adopter=free_space._reconstruct_legacy_free_space_contract,
    ) is None
    damaged = wire.load_json(original.decode("utf-8"))
    cell = next(cell for cell in damaged["document"]["cells"]
                if type(cell["value"]) is bool)
    cell["value"] = not cell["value"]
    damaged["document"]["digest"] = wire.document_digest(damaged["document"])
    damaged["document_digest"] = damaged["document"]["digest"]
    # Even a newly authenticated document must still match the saved contract.
    damaged["auth_tag"] = free_space._receipt_tag(damaged, secret)
    damaged_path = tmp_path / "explicit-altered-document.json"
    damaged_path.write_text(wire.canonical_json(damaged), encoding="utf-8")
    damaged_bytes = damaged_path.read_bytes()
    assert free_space._read_cache_entry(
        damaged_path, family["key"], secret, expected_parameter_snapshot=snapshot,
        legacy_adopter=free_space._reconstruct_legacy_free_space_contract,
    ) is None
    assert damaged_path.read_bytes() == damaged_bytes

    contract_changes = [
        ("algorithm_version", "unknown-free-space-algorithm/1"),
        ("schema_version", "unknown-free-space-schema/1"),
        ("package_id", "foreign-free-space"),
        ("package_schema", "unknown-free-space-package/1"),
        ("producer", "foreign.free_space_evidence_package"),
        ("target_ids", [receipt["contract"]["target_ids"][0] + ":foreign"]),
        ("artifacts", {"visualization_manifest": {"foreign": True}}),
    ]
    contract_changes.extend(
        ("dependencies", [
            {**item, "fingerprint": "0" * 64} if item["name"] == dependency["name"] else item
            for item in receipt["contract"]["dependencies"]
        ])
        for dependency in receipt["contract"]["dependencies"]
    )
    for index, (name, value) in enumerate(contract_changes):
        altered = wire.load_json(original.decode("utf-8"))
        altered["contract"][name] = value
        # Rebuild self-identities so refusal proves independent document binding.
        altered["contract"] = storage.legacy_candidate_contract(altered["contract"])
        altered["auth_tag"] = free_space._receipt_tag(altered, secret)
        altered_path = tmp_path / f"altered-contract-{index}.json"
        altered_path.write_text(wire.canonical_json(altered), encoding="utf-8")
        altered_bytes = altered_path.read_bytes()
        assert free_space._read_cache(altered_path, family["key"], secret) is None
        assert free_space._read_cache_entry(
            altered_path, family["key"], secret, expected_parameter_snapshot=snapshot,
            legacy_adopter=free_space._reconstruct_legacy_free_space_contract,
        ) is None
        assert altered_path.read_bytes() == altered_bytes

    for section, name, value in (
        ("identity", "project_source_identity", {"name": "foreign"}),
        ("identity", "request_source_fingerprint", "0" * 64),
        ("request", "geometry_tolerance", 0.002),
        ("request", "geometry_query", {
            "kind": "unknown-query", "height_band": None, "world_z_m": None,
        }),
    ):
        altered = wire.load_json(original.decode("utf-8"))
        target = (altered["document"]["tables"]["snapshot"]["request"]
                  if section == "request" else altered["document"]["identity"])
        target[name] = value
        altered["document"]["digest"] = wire.document_digest(altered["document"])
        altered["document_digest"] = altered["document"]["digest"]
        altered["auth_tag"] = free_space._receipt_tag(altered, secret)
        altered_path = tmp_path / f"altered-document-{name}.json"
        altered_path.write_text(wire.canonical_json(altered), encoding="utf-8")
        assert free_space._read_cache(altered_path, family["key"], secret) is None
        assert free_space._read_cache_entry(
            altered_path, family["key"], secret, expected_parameter_snapshot=snapshot,
            legacy_adopter=free_space._reconstruct_legacy_free_space_contract,
        ) is None

    for name in ("height_band_datum", "geometry_tolerance", "topology_tolerance", "demand"):
        incomplete = wire.load_json(original.decode("utf-8"))
        del incomplete["document"]["tables"]["snapshot"]["request"][name]
        incomplete["document"]["digest"] = wire.document_digest(incomplete["document"])
        incomplete["document_digest"] = incomplete["document"]["digest"]
        # Even a matching current projection cannot attest an omitted historical value.
        incomplete["contract"] = storage.legacy_candidate_contract(
            free_space.package.build_free_space_package_contract(incomplete["document"]))
        incomplete["auth_tag"] = free_space._receipt_tag(incomplete, secret)
        incomplete_path = tmp_path / f"incomplete-request-{name}.json"
        incomplete_path.write_text(wire.canonical_json(incomplete), encoding="utf-8")
        assert free_space._reconstruct_legacy_free_space_contract(
            incomplete, lookup.cached_contract) is None
        assert free_space._read_cache(incomplete_path, family["key"], secret) is None
        assert free_space._read_cache_entry(
            incomplete_path, family["key"], secret, expected_parameter_snapshot=snapshot,
            legacy_adopter=free_space._reconstruct_legacy_free_space_contract,
        ) is None
    assert path.read_bytes() == original
