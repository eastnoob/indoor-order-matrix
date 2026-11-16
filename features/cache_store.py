"""Immutable model-side publication below package-owned validation and calculation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import ctypes
from dataclasses import asdict, dataclass, field
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, Literal

from .cache_paths import (
    CacheAddress,
    SourceBinding,
    contained_cache_path,
    ensure_cache_directory,
    validate_cache_component,
)
from .evidence_package_parameters import _fingerprint, _freeze, _json_value
from .evidence_package_storage import write_receipt


_ADDRESS_FIELDS = {
    "source_fingerprint", "package_id", "output_port", "layer", "identity",
}
_RECEIPT_FIELDS = {
    "schema", "address", "contract", "payload", "upstream_refs",
    "auth_key_id", "status", "receipt_fingerprint",
}
_BINDING_FIELDS = {
    "schema", "source_fingerprint", "canonical_source_identity",
    "content_fingerprint", "external_dependencies", "current_locator",
}


class CacheValidationError(ValueError):
    """Reject incomplete, malformed or integrity-invalid stored data."""


class CacheConflictError(ValueError):
    """Preserve an existing addressed artifact that differs from a publication."""


class CacheUnsupportedError(NotImplementedError):
    """Refuse a storage capability that this implementation cannot safely provide."""


@dataclass(frozen=True, slots=True)
class CacheValidationContext:
    """Pass immutable wrapper facts and a private authentication domain to an owner."""

    address: CacheAddress
    auth_key_id: str | None
    auth_key: bytes | None = field(repr=False)
    contract: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Detach the wrapper contract without resolving package parameters."""
        if not isinstance(self.address, CacheAddress):
            raise TypeError("validation address must be a CacheAddress")
        if self.auth_key_id is not None and type(self.auth_key_id) is not str:
            raise TypeError("auth_key_id must be a string or None")
        if self.auth_key is not None and type(self.auth_key) is not bytes:
            raise TypeError("auth_key must be bytes or None")
        if not isinstance(self.contract, Mapping):
            raise TypeError("validation contract must be a mapping")
        object.__setattr__(self, "contract", _freeze(self.contract))


CacheValidator = Callable[[bytes, CacheValidationContext], None]


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """Expose a complete publication without exposing mutable receipt containers."""

    address: CacheAddress
    receipt: Mapping[str, Any]
    receipt_path: Path
    payload_paths: tuple[Path, ...]
    status: str
    reuse_origin: Literal["local", "migrated", "legacy_adopted"]

    def __post_init__(self):
        """Deeply detach public receipt data and the collection of payload paths."""
        if not isinstance(self.address, CacheAddress):
            raise TypeError("entry address must be a CacheAddress")
        if not isinstance(self.receipt, Mapping):
            raise TypeError("entry receipt must be a mapping")
        if self.status != "complete":
            raise ValueError("a CacheEntry must be complete")
        if self.reuse_origin not in {"local", "migrated", "legacy_adopted"}:
            raise ValueError("unknown cache reuse origin")
        object.__setattr__(self, "receipt", _freeze(self.receipt))
        object.__setattr__(self, "payload_paths", tuple(self.payload_paths))


def _json_bytes(value) -> bytes:
    """Serialize finite JSON canonically while distinguishing bool, int and float."""
    return json.dumps(
        _json_value(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _unique_object(pairs):
    """Reject duplicate receipt fields instead of accepting the final occurrence."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise CacheValidationError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    """Reject JSON extensions for nonfinite numerical values."""
    raise CacheValidationError(f"nonfinite JSON constant: {value}")


def _read_file(root: Path, path: Path) -> bytes:
    """Read one contained regular file without accepting a linked filesystem path."""
    path = contained_cache_path(root, path)
    try:
        information = path.lstat()
        if not stat.S_ISREG(information.st_mode):
            raise CacheValidationError(f"cache artifact is not a regular file: {path}")
        payload = path.read_bytes()
    except FileNotFoundError as exc:
        raise CacheValidationError(f"missing cache artifact: {path}") from exc
    contained_cache_path(root, path)
    return payload


def _read_json(root: Path, path: Path):
    """Load strict finite JSON without coercing duplicate or nonfinite values."""
    payload = _read_file(root, path)
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        _json_value(value)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise CacheValidationError(f"invalid finite JSON artifact: {path}") from exc
    return value


def _decode_address(value) -> CacheAddress:
    """Require exactly the five public address fields in stored references."""
    if type(value) is not dict or set(value) != _ADDRESS_FIELDS:
        raise CacheValidationError("stored cache address fields do not match")
    try:
        return CacheAddress(**value)
    except (ValueError, TypeError) as exc:
        raise CacheValidationError("stored cache address is unsafe") from exc


def _rename_no_replace(source: Path, destination: Path) -> None:
    """Atomically rename a directory with a kernel-enforced absent destination."""
    if os.name == "nt":
        # Windows os.rename refuses an existing destination, including an empty one.
        os.rename(source, destination)
        return
    if not sys.platform.startswith("linux"):
        raise CacheUnsupportedError("no safe no-replace directory rename on this platform")
    library = ctypes.CDLL(None, use_errno=True)
    rename = getattr(library, "renameat2", None)
    if rename is None:
        raise CacheUnsupportedError("renameat2 is required for no-replace publication")
    rename.argtypes = (
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint,
    )
    rename.restype = ctypes.c_int
    # RENAME_NOREPLACE also protects empty destinations; ordinary POSIX rename does not.
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1) != 0:
        code = ctypes.get_errno()
        if code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
            raise CacheUnsupportedError("filesystem lacks no-replace directory publication")
        raise OSError(code, os.strerror(code), str(destination))


def _binding_document(binding: SourceBinding):
    """Serialize durable source facts separately from disposable catalog metadata."""
    return {
        "schema": "source-binding/v1",
        "source_fingerprint": binding.source_fingerprint,
        "canonical_source_identity": binding.canonical_source_identity,
        "content_fingerprint": binding.content_fingerprint,
        "external_dependencies": _json_value(binding.external_dependencies),
        "current_locator": binding.current_locator,
    }


def _binding_facts(binding: SourceBinding) -> bytes:
    """Compare verified source facts without treating a locator as source identity."""
    return _json_bytes({
        key: value for key, value in _binding_document(binding).items()
        if key != "current_locator"
    })


def _decode_binding(document, source_fingerprint: str) -> SourceBinding:
    """Validate the complete durable source-binding schema and namespace."""
    if (
        type(document) is not dict
        or set(document) != _BINDING_FIELDS
        or document["schema"] != "source-binding/v1"
        or document["source_fingerprint"] != source_fingerprint
    ):
        raise CacheValidationError("source binding schema or namespace does not match")
    try:
        return SourceBinding(**{
            key: value for key, value in document.items() if key != "schema"
        })
    except (TypeError, ValueError) as exc:
        raise CacheValidationError("invalid source binding facts") from exc


class CacheStore:
    """Publish exact immutable bytes while callers retain all package semantics."""

    def __init__(self, root: Path):
        """Pin an explicit root without creating directories or choosing a fallback."""
        self.root = Path(os.path.abspath(root))
        contained_cache_path(self.root, self.root)

    def _entry_directory(self, address: CacheAddress) -> Path:
        """Join only a validated full address beneath the verified sidecar root."""
        if not isinstance(address, CacheAddress):
            raise TypeError("address must be a CacheAddress")
        return contained_cache_path(
            self.root,
            self.root / "sources" / address.source_fingerprint / "outputs"
            / address.package_id / address.output_port / address.layer / address.identity,
        )

    def _read_storage(self, address: CacheAddress, *, directory=None):
        """Check one exact wrapper and payload without authorizing numerical reuse."""
        directory = self._entry_directory(address) if directory is None else (
            contained_cache_path(self.root, directory)
        )
        try:
            information = directory.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISDIR(information.st_mode):
            raise CacheValidationError("cache entry is not a directory")
        receipt = _read_json(self.root, directory / "receipt.json")
        if (
            type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS
            or receipt["schema"] != "cache-receipt/v1"
            or receipt["status"] != "complete"
        ):
            raise CacheValidationError("cache receipt schema or completion status does not match")
        if _decode_address(receipt["address"]) != address:
            raise CacheValidationError("cache receipt address does not match its directory")
        if type(receipt["contract"]) is not dict:
            raise CacheValidationError("cache contract must be an object")
        metadata = receipt["payload"]
        if (
            type(metadata) is not dict
            or set(metadata) != {"path", "format", "size", "sha256"}
            or metadata["path"] != "payload.json"
            or type(metadata["format"]) is not str or not metadata["format"]
            or type(metadata["size"]) is not int or metadata["size"] < 0
            or type(metadata["sha256"]) is not str
            or len(metadata["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in metadata["sha256"])
        ):
            raise CacheValidationError("invalid cache payload metadata")
        if type(receipt["upstream_refs"]) is not list:
            raise CacheValidationError("upstream_refs must be an array")
        references = tuple(_decode_address(value) for value in receipt["upstream_refs"])
        if len(set(references)) != len(references):
            raise CacheValidationError("duplicate upstream reference")
        expected_fingerprint = _fingerprint({
            key: value for key, value in receipt.items() if key != "receipt_fingerprint"
        })
        if receipt["receipt_fingerprint"] != expected_fingerprint:
            raise CacheValidationError("cache receipt fingerprint does not match")
        if receipt["auth_key_id"] is not None:
            raise CacheUnsupportedError("authenticated cache entries require Task 2")
        payload = _read_file(self.root, directory / "payload.json")
        if (
            len(payload) != metadata["size"]
            or hashlib.sha256(payload).hexdigest() != metadata["sha256"]
        ):
            raise CacheValidationError("cache payload size or checksum does not match")
        return receipt, payload

    def _entry(self, address, receipt, directory) -> CacheEntry:
        """Expose frozen publication metadata after its bytes have been checked."""
        return CacheEntry(
            address, receipt, directory / "receipt.json",
            (directory / "payload.json",), "complete", "local",
        )

    def _verify_publication(self, address, receipt, payload, validator, *, directory=None):
        """Reuse a staged artifact or winner only after exact and owner validation."""
        directory = self._entry_directory(address) if directory is None else (
            contained_cache_path(self.root, directory)
        )
        try:
            stored = self._read_storage(address, directory=directory)
        except CacheValidationError as exc:
            raise CacheConflictError("existing addressed artifact is incomplete or invalid") from exc
        if stored is None:
            return None
        saved_receipt, saved_payload = stored
        try:
            validator(saved_payload, CacheValidationContext(
                address, None, None, saved_receipt["contract"],
            ))
        except (ValueError, TypeError) as exc:
            raise CacheConflictError("existing addressed artifact fails package validation") from exc
        if (
            _json_bytes(saved_receipt) != _json_bytes(receipt)
            or saved_payload != payload
        ):
            raise CacheConflictError("same cache address has different wrapper or payload bytes")
        return self._entry(address, saved_receipt, directory)

    def _dependencies_available(self, references, seen) -> bool:
        """Require intact stored upstreams without acquiring locks or running owners."""
        for reference in references:
            address = _decode_address(reference)
            if address in seen:
                return False
            try:
                stored = self._read_storage(address)
            except CacheValidationError:
                # An incomplete or corrupt dependency cannot support an exact hit.
                return False
            if stored is None or not self._dependencies_available(
                stored[0]["upstream_refs"], seen | {address},
            ):
                return False
        return True

    def put(
        self, address: CacheAddress, *, contract: Mapping[str, Any],
        payload: bytes, payload_format: str,
        upstream_refs: tuple[CacheAddress, ...] = (),
        validator: CacheValidator, auth_key_id: str | None = None,
    ) -> CacheEntry:
        """Validate, fsync and publish immutable bytes without resolving parameters."""
        final = self._entry_directory(address)
        if auth_key_id is not None:
            raise CacheUnsupportedError("authenticated cache publication requires Task 2")
        if not isinstance(contract, Mapping):
            raise TypeError("contract must be a mapping")
        if type(payload) is not bytes:
            raise TypeError("payload must be bytes")
        if type(payload_format) is not str or not payload_format:
            raise TypeError("payload_format must be a nonempty string")
        if type(upstream_refs) is not tuple or any(
            not isinstance(reference, CacheAddress) for reference in upstream_refs
        ):
            raise TypeError("upstream_refs must be a tuple of CacheAddress values")
        if len(set(upstream_refs)) != len(upstream_refs) or address in upstream_refs:
            raise ValueError("upstream_refs must be distinct and cannot reference this entry")
        contract = _json_value(_freeze(contract))
        validator(payload, CacheValidationContext(address, None, None, contract))
        receipt = {
            "schema": "cache-receipt/v1",
            "address": asdict(address),
            "contract": contract,
            "payload": {
                "path": "payload.json", "format": payload_format,
                "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            },
            "upstream_refs": [asdict(reference) for reference in upstream_refs],
            "auth_key_id": None,
            "status": "complete",
        }
        receipt["receipt_fingerprint"] = _fingerprint(receipt)
        existing = self._verify_publication(address, receipt, payload, validator)
        if existing is not None:
            return existing
        parent = ensure_cache_directory(self.root, final.parent)
        stage = contained_cache_path(self.root, Path(tempfile.mkdtemp(
            prefix=f".{address.identity}.staging-", dir=parent,
        )))
        payload_path = contained_cache_path(self.root, stage / "payload.json")
        with payload_path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        contained_cache_path(self.root, payload_path)
        receipt_path = contained_cache_path(self.root, stage / "receipt.json")
        write_receipt(receipt_path, receipt)
        contained_cache_path(self.root, receipt_path)
        self._verify_publication(address, receipt, payload, validator, directory=stage)
        contained_cache_path(self.root, stage)
        contained_cache_path(self.root, final)
        try:
            _rename_no_replace(stage, final)
        except FileExistsError:
            # A concurrent publisher may win; its complete bytes must still agree.
            pass
        result = self._verify_publication(address, receipt, payload, validator)
        if result is None:
            raise CacheValidationError("published cache directory disappeared")
        return result

    def get(self, address: CacheAddress, *, validator: CacheValidator) -> CacheEntry | None:
        """Authorize an exact hit through current owner validation and stored upstreams."""
        directory = self._entry_directory(address)
        stored = self._read_storage(address, directory=directory)
        if stored is None:
            return None
        receipt, payload = stored
        if not self._dependencies_available(receipt["upstream_refs"], {address}):
            return None
        validator(payload, CacheValidationContext(address, None, None, receipt["contract"]))
        return self._entry(address, receipt, directory)

    def get_source_binding(self, source_fingerprint: str) -> SourceBinding | None:
        """Load durable source facts without consulting or rebuilding an index."""
        validate_cache_component(source_fingerprint)
        path = contained_cache_path(
            self.root, self.root / "sources" / source_fingerprint / "source.json",
        )
        try:
            path.lstat()
        except FileNotFoundError:
            return None
        return _decode_binding(_read_json(self.root, path), source_fingerprint)

    def put_source_binding(self, binding: SourceBinding) -> SourceBinding:
        """Accept caller-verified facts once and subsequently update only their locator."""
        if not isinstance(binding, SourceBinding):
            raise TypeError("binding must be a SourceBinding")
        current = self.get_source_binding(binding.source_fingerprint)
        if current is not None:
            if _binding_facts(current) != _binding_facts(binding):
                raise CacheConflictError("source facts changed under an existing source fingerprint")
            if current.current_locator == binding.current_locator:
                return current
        directory = ensure_cache_directory(
            self.root, self.root / "sources" / binding.source_fingerprint,
        )
        path = contained_cache_path(self.root, directory / "source.json")
        descriptor, temporary = tempfile.mkstemp(
            prefix=".source.", suffix=".staging", dir=directory,
        )
        os.close(descriptor)
        temporary = contained_cache_path(self.root, Path(temporary))
        document = _binding_document(binding)
        try:
            write_receipt(temporary, document)
            staged = _decode_binding(
                _read_json(self.root, temporary), binding.source_fingerprint,
            )
            if _json_bytes(_binding_document(staged)) != _json_bytes(document):
                raise CacheValidationError("staged source binding does not match")
            contained_cache_path(self.root, path)
            if current is None:
                try:
                    # A hard-link publication creates once without exposing partial JSON.
                    os.link(temporary, path, follow_symlinks=False)
                except FileExistsError:
                    current = self.get_source_binding(binding.source_fingerprint)
                    if current is None:
                        raise CacheConflictError("competing source binding disappeared")
            if current is not None:
                if _binding_facts(current) != _binding_facts(binding):
                    raise CacheConflictError("competing source binding has different facts")
                contained_cache_path(self.root, path)
                write_receipt(path, document)
            contained_cache_path(self.root, path)
            result = self.get_source_binding(binding.source_fingerprint)
            if result is None or _binding_facts(result) != _binding_facts(binding):
                raise CacheConflictError("published source binding facts do not match")
            return result
        finally:
            contained_cache_path(self.root, temporary).unlink(missing_ok=True)
