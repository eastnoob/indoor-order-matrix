"""Authenticate saved free-space inputs or compute them with bounded content-cache reuse."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import hmac
from pathlib import Path
import os
import secrets
import tempfile

from . import blender_analysis_result_wire as wire
from .blender_analysis_session import serialize_analysis_result, _content_cache_key, _cached_run

if "." in (__package__ or ""):
    from ..features import analysis_requests as requests
    from ..features import free_space_evidence_package as package
    from ..features.field_core import (fingerprint_evidence_dependency, evaluate_evidence_package_freshness,
        serialize_evidence_processed_output, deserialize_evidence_processed_output, _freeze,
        _validate_evidence_package_contract)
    from ..features.evidence_package_parameters import compare_parameter_snapshots
    from ..features.evidence_package_storage import (
        ProcessedCacheLookup, legacy_processed_cache_key, processed_cache_key,
        reconstruct_legacy_processed_snapshot, compare_receipt_parameters,
        legacy_candidate_contract,
    )
else:
    from features import analysis_requests as requests
    from features import free_space_evidence_package as package
    from features.field_core import (fingerprint_evidence_dependency, evaluate_evidence_package_freshness,
        serialize_evidence_processed_output, deserialize_evidence_processed_output, _freeze,
        _validate_evidence_package_contract)
    from features.evidence_package_parameters import compare_parameter_snapshots
    from features.evidence_package_storage import (
        ProcessedCacheLookup, legacy_processed_cache_key, processed_cache_key,
        reconstruct_legacy_processed_snapshot, compare_receipt_parameters,
        legacy_candidate_contract,
    )


@dataclass(frozen=True, slots=True)
class AuthenticatedFreeSpaceLookup:
    """Return authenticated free-space bytes with immutable receipt provenance."""

    document: Mapping
    cached_contract: Mapping
    parameter_status: Mapping | None
    reuse_origin: Mapping

    def __post_init__(self):
        """Freeze the historical wire document and all receipt audit metadata."""
        object.__setattr__(self, "document", wire.freeze(self.document))
        object.__setattr__(self, "cached_contract", _freeze(self.cached_contract))
        object.__setattr__(self, "reuse_origin", _freeze(self.reuse_origin))
        if self.parameter_status is not None:
            object.__setattr__(self, "parameter_status", _freeze(self.parameter_status))

CACHE_SCHEMA = "free-space-evidence-cache/v1"


def _publication_cache_key(scene, request):
    """Preserve the original deterministic native publication identity independently of storage."""
    request_data = request.to_dict()
    del request_data["request_id"]
    return fingerprint_evidence_dependency({
        "scene": scene.to_dict(), "request": request_data,
        "executor_key": requests.semantic_cache_key(scene, request),
        "package": {"id": package.PACKAGE_ID, "schema": package.PACKAGE_SCHEMA,
                    "algorithm_version": package.ALGORITHM_VERSION,
                    "function": package.OUTPUT_FUNCTION_ID, "function_version": package.OUTPUT_FUNCTION_VERSION},
        "wire": {"schema": wire.SCHEMA_VERSION, "algorithm": wire.ALGORITHM_VERSION},
    })


def free_space_cache_key(scene, request):
    """Bind complete factual inputs and calculation versions without transient request ids."""
    if not isinstance(scene, requests.NeutralSceneV2) or not isinstance(request, requests.AnalysisRequest):
        raise TypeError("free-space computation requires NeutralSceneV2 and AnalysisRequest")
    # Plane name and revision describe publication state; geometry reuse binds
    # the stable plane identity and pose while normalizing those audit fields.
    calculation_plane = replace(request.plane, name="__calculation_plane__", revision=1)
    normalized_request = replace(request, plane=calculation_plane)
    normalized_scene = replace(scene, context=replace(scene.context,
        analysis_plane=calculation_plane))
    request_data = normalized_request.to_dict()
    del request_data["request_id"]
    # The legacy key also binds registry bytes and numerical backends, but omits
    # scope/uncertainty facts. Complete scene data closes that cache boundary.
    return fingerprint_evidence_dependency({
        "scene": normalized_scene.to_dict(), "request": request_data,
        "executor_key": _content_cache_key(normalized_scene, normalized_request, {}, None)[0],
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


def _read_cache_entry(path, cache_key, secret, *, expected_parameter_snapshot=None,
                      legacy_adopter=None):
    """Authenticate and independently bind the saved contract to its document before reuse."""
    try:
        receipt = wire.load_json(path.read_text(encoding="utf-8"))
        if not hmac.compare_digest(receipt.get("auth_tag", ""), _receipt_tag(receipt, secret)):
            return None
        if (receipt["schema"] != CACHE_SCHEMA or receipt["cache_key"] != cache_key
                or set(receipt) != {"schema", "cache_key", "publication_key", "document_digest",
                                   "document", "contract", "auth_tag"}):
            return None
        document = wire.validate_document(receipt["document"])
        if receipt.get("document_digest") != wire.document_digest(document):
            return None
        if document["result_id"] != "free-space:" + receipt.get("publication_key", cache_key):
            return None
        cached_contract = _validate_evidence_package_contract(receipt["contract"])
        request = document["tables"]["snapshot"]["request"]
        document_snapshot = package.build_free_space_parameter_snapshot(request)
        document_contract = package.build_free_space_package_contract(
            document, parameter_snapshot=document_snapshot)
        # A signed contract must still describe these signed document bytes.
        # Missing typed provenance does not excuse any nonparameter mismatch.
        saved_document_contract = (
            document_contract if "parameter_snapshot" in cached_contract
            else legacy_candidate_contract(document_contract))
        legacy_document_contract = (
            None if "parameter_snapshot" in cached_contract
            else package.build_legacy_free_space_package_contract(document))
        if evaluate_evidence_package_freshness(
                cached_contract=cached_contract,
                current_contract=saved_document_contract)["recompute_required"]:
            # Only the complete independently derived original contract can
            # bridge the pre-A identity projection; typed receipts stay strict.
            if (legacy_document_contract is None
                    or wire.canonical_json(receipt["contract"])
                    != wire.canonical_json(legacy_document_contract)):
                return None
        historical_contract = cached_contract
        origin = {
            "mode": "cache_hit",
            "origin_cache_key": receipt["cache_key"],
            "origin_contract": cached_contract,
            "origin_payload_fingerprint": receipt["document_digest"],
        }
        # Bare historical reads retain their API after document/contract binding;
        # the runner additionally requires independently current owner parameters.
        if expected_parameter_snapshot is None and legacy_adopter is None:
            return AuthenticatedFreeSpaceLookup(document, historical_contract, None, origin)
        snapshot = expected_parameter_snapshot or document_snapshot
        current = package.build_free_space_package_contract(document, parameter_snapshot=snapshot)
        status = compare_receipt_parameters(cached_contract, current)
        if status["recompute_required"]:
            if legacy_adopter is None:
                return None
            adopted = legacy_adopter(receipt, current)
            if adopted is None:
                return None
            historical_contract = _validate_evidence_package_contract(adopted)
            verified = compare_receipt_parameters(historical_contract, current)
            if verified["recompute_required"]:
                return None
            status = {**verified, "exact_match": False}
            origin = {**origin, "mode": "adopted_legacy",
                      "verification_mode": "owner_reconstructed_parameters"}
        return AuthenticatedFreeSpaceLookup(document, historical_contract, status, origin)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        return None


def _read_cache(path, cache_key, secret):
    """Preserve the existing authenticated bare-document API."""
    entry = _read_cache_entry(path, cache_key, secret)
    return None if entry is None else wire.plain(entry.document)


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


def _read_processed_cache_entry(path, *, raw_output, processor, secret,
                                legacy_path=None, legacy_processed_adopter=None):
    """Authenticate processed receipts before shared parameter-aware reuse."""
    def read_one(candidate):
        """Authenticate one envelope and require its declared identity to match the payload."""
        receipt = wire.load_json(Path(candidate).read_text(encoding="utf-8"))
        expected = processed_cache_key(raw_output, processor)
        if (set(receipt) != {"schema", "processing_identity", "processed_output", "auth_tag"}
                or receipt["schema"] != "free-space-processed-cache/v1"
                or not hmac.compare_digest(receipt["auth_tag"], _receipt_tag(receipt, secret))):
            return None
        output = deserialize_evidence_processed_output(receipt["processed_output"], raw_output=raw_output)
        if output.error_code is not None or output.processor_id != processor.function_id \
                or output.processor_version != processor.version:
            return None
        if (receipt["processing_identity"] != output.processing_identity
                or output.processing_identity != expected):
            return None
        if output.parameter_snapshot is not None and processor.parameter_snapshot is not None:
            status = compare_parameter_snapshots(output.parameter_snapshot, processor.parameter_snapshot)
        elif output.parameter_snapshot is None and processor.parameter_snapshot is None:
            status = None
        else:
            return None
        if status is not None and status["recompute_required"]:
            return None
        return ProcessedCacheLookup(output, status, {
            "mode": "cache_hit",
            "origin_processing_identity": output.processing_identity,
            "origin_payload_fingerprint": receipt["processed_output"].get("payload_fingerprint"),
        })

    try:
        entry = read_one(path)
        if entry is not None:
            return entry
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        pass
    if legacy_path is None or legacy_processed_adopter is None:
        return None
    try:
        receipt = wire.load_json(Path(legacy_path).read_text(encoding="utf-8"))
        if (set(receipt) != {"schema", "processing_identity", "processed_output", "auth_tag"}
                or receipt["schema"] != "free-space-processed-cache/v1"
                or not hmac.compare_digest(receipt["auth_tag"], _receipt_tag(receipt, secret))):
            return None
        saved = deserialize_evidence_processed_output(receipt["processed_output"], raw_output=raw_output)
        if (saved.error_code is not None or saved.parameter_snapshot is not None
                or saved.processor_id != processor.function_id
                or saved.processor_version != processor.version
                or receipt["processing_identity"] != saved.processing_identity):
            return None
        # Verify the saved full recipe first; current warning values can have
        # another legacy key while sharing the same authorized computation.
        if saved.processing_identity != legacy_processed_cache_key(
                raw_output, processor, parameters=saved.parameters):
            return None
        snapshot = legacy_processed_adopter(saved, processor)
        if snapshot is None or processor.parameter_snapshot is None:
            return None
        from dataclasses import replace as _replace
        adopted = _replace(saved, parameter_snapshot=snapshot)
        status = compare_parameter_snapshots(snapshot, processor.parameter_snapshot)
        if status["recompute_required"]:
            return None
        return ProcessedCacheLookup(adopted, {**status, "exact_match": False}, {
            "mode": "adopted_legacy",
            "verification_mode": "owner_reconstructed_parameters",
            "origin_processing_identity": saved.processing_identity,
            "origin_payload_fingerprint": receipt["processed_output"].get("payload_fingerprint"),
        })
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        return None


def _read_processed_cache(path, *, raw_output, processor, secret):
    """Preserve the existing authenticated bare-output API."""
    entry = _read_processed_cache_entry(path, raw_output=raw_output, processor=processor, secret=secret)
    return None if entry is None else entry.processed_output


def _write_processed_cache(path, output, secret):
    """Use the same HMAC and atomic replacement boundary as authenticated raw free space."""
    if output.error_code is None:
        receipt = {"schema": "free-space-processed-cache/v1", "processing_identity": output.processing_identity,
                   "processed_output": serialize_evidence_processed_output(output)}
        receipt["auth_tag"] = _receipt_tag(receipt, secret)
        _write_cache(path, receipt)


def evaluate_free_space_package(scene, request, *, cache_directory=None):
    """Compute or reuse occupancy for supplied immutable facts, then project the one package channel."""
    return run_free_space_package(scene, request, cache_directory=cache_directory)["raw_output"]


def _reconstruct_legacy_free_space_contract(receipt, current_contract):
    """Attest explicit historical parameters after independently verifying their contract."""
    try:
        old = _validate_evidence_package_contract(receipt["contract"])
        if "parameter_snapshot" in old:
            return None
        legacy_document_contract = package.build_legacy_free_space_package_contract(
            receipt["document"])
        request = receipt["document"]["tables"]["snapshot"]["request"]
        snapshot = package.build_free_space_parameter_snapshot(request)
        reconstructed = package.build_free_space_package_contract(
            receipt["document"], dependency_fingerprints=None,
            parameter_snapshot=snapshot,
        )
        # Authentication proves origin; independently derived dependencies and
        # versions prove that the historical contract actually binds this source.
        if evaluate_evidence_package_freshness(
                cached_contract=old,
                current_contract=legacy_candidate_contract(reconstructed))["recompute_required"]:
            if (wire.canonical_json(receipt["contract"])
                    != wire.canonical_json(legacy_document_contract)):
                return None
        if compare_receipt_parameters(reconstructed, current_contract)["recompute_required"]:
            return None
        return reconstructed
    except (KeyError, TypeError, ValueError):
        return None


def run_free_space_package(scene, request, *, cache_directory=None, output_processor=None):
    """Own authenticated occupancy reuse, current publication and optional processed access."""
    cache_key = free_space_cache_key(scene, request)
    directory = None if cache_directory is None else Path(cache_directory)
    path = None if directory is None else directory / (cache_key + ".json")
    secret = None if directory is None else _cache_secret(directory)
    requested_snapshot = package.build_free_space_parameter_snapshot(request.to_dict())
    lookup = None if path is None else _read_cache_entry(
        path, cache_key, secret,
        expected_parameter_snapshot=requested_snapshot,
        legacy_adopter=_reconstruct_legacy_free_space_contract,
    )
    document = None if lookup is None else wire.plain(lookup.document)
    hit = lookup is not None
    publication_key = _publication_cache_key(scene, request) if document is None else document["result_id"].removeprefix("free-space:")
    publication_id = "free-space:" + publication_key
    stable_request = replace(request, request_id=publication_id)
    if document is None:
        # A deterministic synthetic publication id keeps random request/job ids
        # out of the materialized result and replay identity.
        run = requests.execute_analysis_request(scene, stable_request)
        document = serialize_analysis_result(run, job_id=publication_id,
            plane_uuid=request.plane.identity, plane_revision=request.plane.revision,
            domain_request_id="free-space-domain:" + publication_key, domain_session_revision=0)
        if path is not None:
            receipt = {"schema": CACHE_SCHEMA, "cache_key": cache_key, "publication_key": publication_key,
                "document_digest": wire.document_digest(document), "document": document,
                "contract": package.build_free_space_package_contract(
                    document, parameter_snapshot=requested_snapshot,
                )}
            receipt["auth_tag"] = _receipt_tag(receipt, secret)
            _write_cache(path, receipt)
    elif document["tables"]["snapshot"]["request"] != wire.plain(stable_request.to_dict()):
        # The authenticated original stays cached. Rebind publication-only plane
        # counters through the existing strict-query adapter without new geometry.
        origin = {"kind": document["kind"], "result_id": document["result_id"], "digest": document["digest"]}
        run = _cached_run(document, stable_request, requests._backend_versions())
        document = serialize_analysis_result(run, job_id=publication_id,
            plane_uuid=request.plane.identity, plane_revision=request.plane.revision,
            domain_request_id="free-space-domain:" + publication_key, domain_session_revision=0)
        document["content_cache"] = {"content_key": cache_key, "hit": True, "origin_result_ref": origin}
        document["tables"]["snapshot"]["provenance"]["calculation_origin_result_ref"] = origin
        document["digest"] = wire.document_digest(document)
        wire.validate_document(document)
    source = package.build_free_space_source_envelope(document, source_freshness="supplied_scene")
    producer = package.build_free_space_evidence_package(output_processor=output_processor)
    raw = producer.evaluate((source,))
    contract = package.build_free_space_package_contract(
        document, parameter_snapshot=requested_snapshot,
    )
    cache_status = evaluate_evidence_package_freshness(
        cached_contract=None if lookup is None else lookup.cached_contract,
        current_contract=contract,
    )
    if lookup is not None:
        cache_status["parameter_status"] = dict(lookup.parameter_status)
        cache_status["reuse_origin"] = dict(lookup.reuse_origin)
    processed_path = (None if path is None or output_processor is None else
                      path.parent / ("processed-" + processed_cache_key(raw, output_processor) + ".json"))
    processed_legacy_path = None
    if processed_path is not None and output_processor is not None:
        old_key = legacy_processed_cache_key(raw, output_processor)
        if old_key != processed_cache_key(raw, output_processor):
            processed_legacy_path = processed_path.parent / ("processed-" + old_key + ".json")
    processed_lookup = None if processed_path is None else _read_processed_cache_entry(
        processed_path, raw_output=raw, processor=output_processor, secret=secret,
        legacy_path=processed_legacy_path,
        legacy_processed_adopter=reconstruct_legacy_processed_snapshot,
    )
    processed = None if processed_lookup is None else processed_lookup.processed_output
    if processed_lookup is None:
        processed = producer.process_output(raw, package_freshness="fresh")
        if processed_path is not None:
            _write_processed_cache(processed_path, processed, secret)
    if processed_lookup is not None:
        cache_status["processed_parameter_status"] = (
            None if processed_lookup.parameter_status is None else dict(processed_lookup.parameter_status))
        cache_status["processed_reuse_origin"] = dict(processed_lookup.reuse_origin)
    return {"raw_output": raw, "processed_output": processed, "contract": contract,
            "status": evaluate_evidence_package_freshness(cached_contract=contract, current_contract=contract),
            "cache_key": cache_key, "cache_hit": hit, "cache_status": cache_status}
