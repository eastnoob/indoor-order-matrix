"""Small typed JSON receipt storage shared by package-owned execution entries."""

import json
import os
from pathlib import Path
import tempfile

from .field_core import (
    deserialize_evidence_package_output, deserialize_evidence_processed_output,
    fingerprint_evidence_dependency, serialize_evidence_package_output,
    serialize_evidence_processed_output,
)


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


def load_raw_output(path, *, cache_key, contract, package):
    """Treat malformed, foreign-content or obsolete-producer receipts as cache misses."""
    try:
        receipt = json.loads(Path(path).read_text(encoding="utf-8"))
        if (set(receipt) != {"schema", "cache_key", "contract", "raw_output", "receipt_fingerprint"}
                or receipt["schema"] != "evidence-package-cache/v1" or receipt["cache_key"] != cache_key
                or receipt["contract"] != contract
                or receipt["receipt_fingerprint"] != fingerprint_evidence_dependency({
                    key: value for key, value in receipt.items() if key != "receipt_fingerprint"})):
            return None
        output = deserialize_evidence_package_output(receipt["raw_output"])
        if (output.package_id != package.package_id or output.output_function != package.output_function_id
                or output.output_function_version != package.output_function_version):
            return None
        return output
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return None


def processed_cache_key(raw_output, processor):
    """Derive the recipe identity without executing its callback."""
    raw = serialize_evidence_package_output(raw_output)
    return fingerprint_evidence_dependency({
        "package_id": raw_output.package_id, "raw_output_identity": raw["output_identity"],
        "raw_payload_fingerprint": raw["payload_fingerprint"],
        "processor_id": processor.function_id, "processor_version": processor.version,
        "parameters": processor.parameters,
    })


def load_processed_output(path, *, raw_output, processor):
    """Read only successful processed bytes matching independently current raw and recipe."""
    try:
        output = deserialize_evidence_processed_output(
            json.loads(Path(path).read_text(encoding="utf-8")), raw_output=raw_output)
        if output.error_code is not None or output.processing_identity != processed_cache_key(raw_output, processor):
            return None
        return output
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return None


def save_processed_output(path, output):
    """Persist configured successful transforms; processing errors are never cache hits."""
    if output.error_code is None:
        write_receipt(path, serialize_evidence_processed_output(output))
