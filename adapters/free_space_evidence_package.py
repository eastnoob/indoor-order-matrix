"""Authenticate saved free-space inputs or compute them with bounded content-cache reuse."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import hmac
from pathlib import Path
import os
import secrets
import tempfile

from . import blender_analysis_result_wire as wire
from .blender_analysis_session import serialize_analysis_result

if "." in (__package__ or ""):
    from ..features import analysis_requests as requests
    from ..features import free_space_evidence_package as package
    from ..features.field_core import fingerprint_evidence_dependency, evaluate_evidence_package_freshness
else:
    from features import analysis_requests as requests
    from features import free_space_evidence_package as package
    from features.field_core import fingerprint_evidence_dependency, evaluate_evidence_package_freshness

CACHE_SCHEMA = "free-space-evidence-cache/v1"


def free_space_cache_key(scene, request):
    """Bind complete factual inputs and calculation versions without transient request ids."""
    if not isinstance(scene, requests.NeutralSceneV2) or not isinstance(request, requests.AnalysisRequest):
        raise TypeError("free-space computation requires NeutralSceneV2 and AnalysisRequest")
    request_data = request.to_dict()
    del request_data["request_id"]
    # The legacy key also binds registry bytes and numerical backends, but omits
    # scope/uncertainty facts. Complete scene data closes that cache boundary.
    return fingerprint_evidence_dependency({
        "scene": scene.to_dict(), "request": request_data,
        "executor_key": requests.semantic_cache_key(scene, request),
        "package": {"id": package.PACKAGE_ID, "schema": package.PACKAGE_SCHEMA,
                    "algorithm_version": package.ALGORITHM_VERSION,
                    "function": package.OUTPUT_FUNCTION_ID, "function_version": package.OUTPUT_FUNCTION_VERSION},
        "wire": {"schema": wire.SCHEMA_VERSION, "algorithm": wire.ALGORITHM_VERSION},
    })


def evaluate_saved_free_space_package(snapshot):
    """Adapt an already exact-opened authenticated snapshot and retain its freshness state."""
    if not isinstance(snapshot, wire.ReadOnlyResultSnapshot) or snapshot.ref.kind != "free_space_run":
        raise TypeError("an opened free-space ReadOnlyResultSnapshot is required")
    wire.validate_document(snapshot.payload)
    actual = wire.list_analysis_results([snapshot.payload])[0]
    if snapshot.ref != actual.ref or snapshot.metadata != actual:
        raise ValueError("snapshot reference or metadata differs from authenticated document")
    if snapshot.freshness not in {"historical", "current"}:
        raise ValueError("saved snapshot has unsupported freshness state")
    source = package.build_free_space_source_envelope(snapshot.payload, source_freshness=snapshot.freshness)
    return package.build_free_space_evidence_package().evaluate((source,))


def _cache_secret(directory):
    """Create one cache-directory signing secret outside each mutable receipt."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".free_space_cache_key"
    if path.exists():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    descriptor, partial = tempfile.mkstemp(prefix=path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(secret)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.replace(partial, path)
        except FileExistsError:
            return path.read_bytes()
    finally:
        Path(partial).unlink(missing_ok=True)
    return secret


def _receipt_tag(receipt, secret):
    """Authenticate all receipt fields except the tag itself."""
    payload = {key: value for key, value in receipt.items() if key != "auth_tag"}
    return hmac.new(secret, wire.canonical_json(payload).encode("utf-8"), hashlib.sha256).hexdigest()


def _read_cache(path, cache_key, secret):
    """Treat corrupt, foreign or stale receipts as misses before any output is admitted."""
    try:
        receipt = wire.load_json(path.read_text(encoding="utf-8"))
        if not hmac.compare_digest(receipt.get("auth_tag", ""), _receipt_tag(receipt, secret)):
            return None
        if receipt["schema"] != CACHE_SCHEMA or receipt["cache_key"] != cache_key:
            return None
        document = wire.validate_document(receipt["document"])
        # Keep a receipt-level digest separate from the document's self-reported
        # digest so rewriting both fields cannot turn altered bytes into a hit.
        if receipt.get("document_digest") != wire.document_digest(document):
            return None
        if document["result_id"] != "free-space:" + cache_key:
            return None
        current = package.build_free_space_package_contract(document)
        status = evaluate_evidence_package_freshness(cached_contract=receipt["contract"], current_contract=current)
        if status["freshness"] != "fresh" or receipt["contract"] != current:
            return None
        return document
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return None


def _write_cache(path, receipt):
    """Atomically replace the whole document/contract receipt while preserving prior final bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, partial = tempfile.mkstemp(prefix=path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(wire.canonical_json(receipt))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        Path(partial).unlink(missing_ok=True)


def evaluate_free_space_package(scene, request, *, cache_directory=None):
    """Compute or reuse occupancy for supplied immutable facts, then project the one package channel."""
    cache_key = free_space_cache_key(scene, request)
    directory = None if cache_directory is None else Path(cache_directory)
    path = None if directory is None else directory / (cache_key + ".json")
    secret = None if directory is None else _cache_secret(directory)
    document = None if path is None else _read_cache(path, cache_key, secret)
    if document is None:
        # A deterministic synthetic publication id keeps random request/job ids
        # out of the materialized result and replay identity.
        stable_request = replace(request, request_id="free-space:" + cache_key)
        run = requests.execute_analysis_request(scene, stable_request)
        document = serialize_analysis_result(run, job_id="free-space:" + cache_key,
            plane_uuid=request.plane.identity, plane_revision=request.plane.revision,
            domain_request_id="free-space-domain:" + cache_key, domain_session_revision=0)
        if path is not None:
            receipt = {"schema": CACHE_SCHEMA, "cache_key": cache_key,
                "document_digest": wire.document_digest(document), "document": document,
                "contract": package.build_free_space_package_contract(document)}
            receipt["auth_tag"] = _receipt_tag(receipt, secret)
            _write_cache(path, receipt)
    source = package.build_free_space_source_envelope(document, source_freshness="supplied_scene")
    return package.build_free_space_evidence_package().evaluate((source,))
