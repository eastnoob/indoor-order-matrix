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

    processed_path = next((FIXTURES / "raw_processed").glob("processed-*.json"))
    assert storage.load_processed_output(processed_path, raw_output=raw,
                                         processor=_processor()) is not None
    assert _sha256(processed_path) == by_family["processed"]["sha256"]

    free_path = next((FIXTURES / "authenticated_free_space").glob("[0-9a-f]*.json"))
    secret = (free_path.parent / ".free_space_cache_key").read_bytes()
    assert len(secret) == 32
    assert free_space._read_cache(free_path, free_path.stem, secret) is not None
    assert _sha256(free_path) == by_family["authenticated_free_space"]["sha256"]

    blender_path = next((FIXTURES / "blender_wire").glob("[0-9a-f]*.json"))
    loaded = blender._load_cached_result(blender_path, content_key=blender_path.stem,
                                         versions=__import__("features.analysis_requests",
                                                             fromlist=["_backend_versions"])._backend_versions())
    assert loaded is not None
    assert wire.document_digest(loaded) == loaded["digest"]
    assert _sha256(blender_path) == by_family["blender_wire"]["sha256"]
