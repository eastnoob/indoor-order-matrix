"""Small typed JSON receipt storage shared by package-owned execution entries."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import tempfile

from .field_core import (
    _freeze,
    _validate_evidence_package_contract,
    _processed_identity_payload,
    deserialize_evidence_package_output, deserialize_evidence_processed_output,
    fingerprint_evidence_dependency, serialize_evidence_package_output,
    serialize_evidence_processed_output,
    build_evidence_package_contract,
    evaluate_evidence_package_freshness,
)
from .evidence_package_parameters import ParameterSnapshot, compare_parameter_snapshots


@dataclass(frozen=True, slots=True)
class RawCacheLookup:
    """Return a validated raw result together with immutable reuse evidence."""

    raw_output: object
    cached_contract: Mapping[str, object]
    parameter_status: Mapping[str, object] | None
    reuse_origin: Mapping[str, object]

    def __post_init__(self):
        """Detach and freeze receipt audit containers before exposing them."""
        object.__setattr__(self, "cached_contract", _freeze(self.cached_contract))
        object.__setattr__(self, "reuse_origin", _freeze(self.reuse_origin))
        if self.parameter_status is not None:
            object.__setattr__(self, "parameter_status", _freeze(self.parameter_status))


@dataclass(frozen=True, slots=True)
class ProcessedCacheLookup:
    """Return a validated processed result with immutable status and origin."""

    processed_output: object
    parameter_status: Mapping[str, object] | None
    reuse_origin: Mapping[str, object]

    def __post_init__(self):
        """Retain immutable saved processing status and origin metadata."""
        object.__setattr__(self, "reuse_origin", _freeze(self.reuse_origin))
        if self.parameter_status is not None:
            object.__setattr__(self, "parameter_status", _freeze(self.parameter_status))


def compare_receipt_parameters(cached_contract, current_contract):
    """Compare owner snapshots without discarding other contract freshness failures."""
    status = evaluate_evidence_package_freshness(
        cached_contract=cached_contract, current_contract=current_contract,
    )
    parameter_status = status.get("parameter_status")
    result = parameter_status if parameter_status is not None else {
        "reuse": "legacy",
        "exact_match": True,
        "recompute_required": False,
        "calculated_parameters": None,
        "requested_parameters": None,
        "warnings": [],
    }
    # Parameter reconstruction can repair missing parameter provenance only.
    # Producer, version, dependency and document bindings remain admission gates.
    if any(reason.get("dependency") != "parameters" for reason in status["reasons"]):
        return {**result, "reuse": "recompute_required",
                "exact_match": False, "recompute_required": True}
    return result


def _contract_arguments(contract):
    """Extract the stable contract fields accepted by the shared builder."""
    return {
        name: contract[name] for name in (
            "package_id", "package_schema", "producer", "target_ids",
            "dependencies", "algorithm_version", "schema_version",
        )
    }


def legacy_candidate_contract(current_contract):
    """Build the exact pre-typed contract identity used by legacy receipts."""
    if not isinstance(current_contract, Mapping):
        raise TypeError("current_contract must be a mapping")
    return build_evidence_package_contract(
        **_contract_arguments(current_contract),
        artifacts=current_contract.get("artifacts", {}),
    )


def legacy_processed_cache_key(raw_output, processor, *, parameters=None) -> str:
    """Bind a legacy recipe to its explicit full parameters without a typed projection."""
    raw = serialize_evidence_package_output(raw_output)
    return fingerprint_evidence_dependency(_processed_identity_payload(
        raw_output.package_id, raw["output_identity"], raw["payload_fingerprint"],
        processor.function_id, processor.version,
        processor.parameters if parameters is None else parameters, None,
    ))


def reconstruct_legacy_processed_snapshot(saved_output, processor):
    """Capture complete saved recipe values without borrowing current defaults."""
    schema = processor.parameter_schema
    if (schema is None or saved_output.processor_id != processor.function_id
            or saved_output.processor_version != processor.version
            or set(saved_output.parameters) != {item.name for item in schema.specs}):
        return None
    try:
        return schema.capture_calculated(
            saved_output.parameters,
            sources={name: "legacy-receipt" for name in saved_output.parameters},
        )
    except (TypeError, ValueError):
        return None


def _typed_contract_from_snapshot(contract, snapshot):
    """Rebuild a historical contract after an owner independently attests values."""
    return build_evidence_package_contract(
        **_contract_arguments(contract), artifacts=contract.get("artifacts", {}),
        parameter_snapshot=snapshot,
    )


def _load_receipt(path):
    """Read one strict JSON receipt without mutating or normalizing its bytes."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_receipt(path, receipt):
    """Publish complete JSON atomically, retaining prior bytes on replacement failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, partial = tempfile.mkstemp(prefix=path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(receipt, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        Path(partial).unlink(missing_ok=True)


def save_raw_output(path, *, cache_key, contract, raw_output):
    """Save typed output with its complete input and current producer contract binding."""
    receipt = {"schema": "evidence-package-cache/v1", "cache_key": cache_key,
               "contract": contract, "raw_output": serialize_evidence_package_output(raw_output)}
    receipt["receipt_fingerprint"] = fingerprint_evidence_dependency(receipt)
    write_receipt(path, receipt)


def load_raw_entry(path, *, cache_key, contract, package, legacy_adopter=None):
    """Return a validated raw result together with historical parameter evidence."""
    try:
        receipt = _load_receipt(path)
        if (type(receipt) is not dict
                or set(receipt) != {"schema", "cache_key", "contract", "raw_output", "receipt_fingerprint"}
                or receipt["schema"] != "evidence-package-cache/v1"
                or receipt["cache_key"] != cache_key
                or receipt["receipt_fingerprint"] != fingerprint_evidence_dependency({
                    key: value for key, value in receipt.items() if key != "receipt_fingerprint"})):
            return None
        cached_contract = _validate_evidence_package_contract(receipt["contract"])
        if cached_contract["package_identity"] != cache_key:
            return None
        output = deserialize_evidence_package_output(receipt["raw_output"])
        if (output.package_id != package.package_id or output.output_function != package.output_function_id
                or output.output_function_version != package.output_function_version):
            return None
        # A legacy filename remains eligible only when all non-parameter identity inputs agree.
        current_identity = contract["package_identity"]
        legacy_identity = legacy_candidate_contract(contract)["package_identity"]
        if cached_contract["package_identity"] not in {current_identity, legacy_identity}:
            return None
        parameter_status = compare_receipt_parameters(cached_contract, contract)
        historical_contract = cached_contract
        origin = {
            "mode": "cache_hit",
            "origin_cache_key": receipt["cache_key"],
            "origin_contract": cached_contract,
            "origin_payload_fingerprint": receipt["raw_output"]["payload_fingerprint"],
        }
        if parameter_status["recompute_required"]:
            if legacy_adopter is None:
                return None
            adopted = legacy_adopter(receipt, contract)
            if adopted is None:
                return None
            adopted = _validate_evidence_package_contract(adopted)
            verified_status = compare_receipt_parameters(adopted, contract)
            if verified_status["recompute_required"]:
                return None
            historical_contract = adopted
            parameter_status = {**verified_status, "exact_match": False}
            origin = {**origin, "mode": "adopted_legacy",
                      "verification_mode": "owner_reconstructed_parameters"}
        return RawCacheLookup(output, historical_contract, parameter_status, origin)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        return None


def load_raw_output(path, *, cache_key, contract, package):
    """Preserve the existing bare-output API for legacy callers."""
    entry = load_raw_entry(path, cache_key=cache_key, contract=contract, package=package)
    return None if entry is None else entry.raw_output


def processed_cache_key(raw_output, processor):
    """Derive the recipe identity without executing its callback."""
    raw = serialize_evidence_package_output(raw_output)
    return fingerprint_evidence_dependency(_processed_identity_payload(
        raw_output.package_id, raw["output_identity"], raw["payload_fingerprint"],
        processor.function_id, processor.version, processor.parameters,
        processor.parameter_snapshot))


def _read_processed_entry(path, *, raw_output, processor):
    """Read one processed receipt and preserve its exact serialized identity."""
    payload = _load_receipt(path)
    output = deserialize_evidence_processed_output(payload, raw_output=raw_output)
    if output.error_code is not None:
        return None
    if output.processor_id != processor.function_id or output.processor_version != processor.version:
        return None
    if output.processing_identity != processed_cache_key(raw_output, processor):
        return None
    if output.parameter_snapshot is not None and processor.parameter_snapshot is not None:
        status = compare_parameter_snapshots(output.parameter_snapshot, processor.parameter_snapshot)
    elif output.parameter_snapshot is None and processor.parameter_snapshot is None:
        status = None
    else:
        status = {"reuse": "missing", "exact_match": False,
                  "recompute_required": True, "calculated_parameters": None,
                  "requested_parameters": None, "warnings": []}
    if status is not None and status["recompute_required"]:
        return None
    origin = {
        "mode": "cache_hit",
        "origin_processing_identity": output.processing_identity,
        "origin_payload_fingerprint": payload.get("payload_fingerprint"),
    }
    return ProcessedCacheLookup(output, status, origin)


def load_processed_entry(path, *, raw_output, processor, legacy_path=None,
                         legacy_processed_adopter=None):
    """Retain saved calculated parameters and adoption origin on processed reuse."""
    try:
        entry = _read_processed_entry(path, raw_output=raw_output, processor=processor)
        if entry is not None:
            return entry
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        entry = None
    if legacy_path is None or legacy_processed_adopter is None:
        return None
    try:
        payload = _load_receipt(legacy_path)
        saved = deserialize_evidence_processed_output(payload, raw_output=raw_output)
        if (saved.error_code is not None or saved.parameter_snapshot is not None
                or saved.processor_id != processor.function_id
                or saved.processor_version != processor.version):
            return None
        # Authenticate the historical full-parameter recipe independently of
        # today's requested warning values before constructing typed provenance.
        if legacy_processed_cache_key(
                raw_output, processor, parameters=saved.parameters) != saved.processing_identity:
            return None
        adopted_snapshot = legacy_processed_adopter(saved, processor)
        if adopted_snapshot is None:
            return None
        adopted = replace(saved, parameter_snapshot=adopted_snapshot)
        if processor.parameter_snapshot is None:
            return None
        status = compare_parameter_snapshots(adopted_snapshot, processor.parameter_snapshot)
        if status["recompute_required"]:
            return None
        origin = {
            "mode": "adopted_legacy",
            "verification_mode": "owner_reconstructed_parameters",
            "origin_processing_identity": saved.processing_identity,
            "origin_payload_fingerprint": payload.get("payload_fingerprint"),
        }
        return ProcessedCacheLookup(adopted, {**status, "exact_match": False}, origin)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        return None


def load_processed_output(path, *, raw_output, processor):
    """Preserve the existing bare-output API for legacy callers."""
    entry = load_processed_entry(path, raw_output=raw_output, processor=processor)
    return None if entry is None else entry.processed_output


def save_processed_output(path, output):
    """Persist configured successful transforms; processing errors are never cache hits."""
    if output.error_code is None:
        write_receipt(path, serialize_evidence_processed_output(output))
