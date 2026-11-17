"""Immutable model-side publication below package-owned validation and calculation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import ctypes
from dataclasses import asdict, dataclass, field, replace
import errno
from contextlib import contextmanager
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import stat
import sys
import tempfile
import threading
import time
from typing import Any, Literal

from .cache_paths import (
    CacheAddress,
    CachePathError,
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


class CacheLockTimeoutError(TimeoutError):
    """Report a bounded failure to acquire a cache lock."""


class CacheAuthenticationError(CacheValidationError, CacheUnsupportedError):
    """Report an entry whose authentication material is unavailable or invalid."""


class CacheStatus(str, Enum):
    """Lifecycle states reported by the model-side store."""

    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"
    ORPHANED = "orphaned"
    QUARANTINED = "quarantined"
    MIGRATION_FAILED = "migration_failed"
    UNAVAILABLE = "unavailable"
    HISTORICAL = "historical"
    MIGRATED_REUSE = "migrated_reuse"


@dataclass(frozen=True, slots=True)
class MigrationReport:
    """Describe a validated copy without changing source entries or identities."""

    source: Path
    destination: Path
    copied: tuple[CacheAddress, ...]
    reused: tuple[CacheAddress, ...]
    failed: tuple[tuple[str, str], ...]
    quarantined: tuple[str, ...]
    index_rebuilt: bool
    auth_material_copied: bool
    old_directory_retained: bool


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
    status: CacheStatus | str
    reuse_origin: Literal["local", "migrated", "legacy_adopted"]

    def __post_init__(self):
        """Deeply detach public receipt data and the collection of payload paths."""
        if not isinstance(self.address, CacheAddress):
            raise TypeError("entry address must be a CacheAddress")
        if not isinstance(self.receipt, Mapping):
            raise TypeError("entry receipt must be a mapping")
        if self.status not in set(CacheStatus) and self.status not in {
            item.value for item in CacheStatus
        }:
            raise ValueError("unknown cache lifecycle status")
        if self.reuse_origin not in {"local", "migrated", "legacy_adopted"}:
            raise ValueError("unknown cache reuse origin")
        object.__setattr__(self, "receipt", _freeze(self.receipt))
        object.__setattr__(self, "payload_paths", tuple(self.payload_paths))
        object.__setattr__(self, "status", CacheStatus(self.status))


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
    if not isinstance(value, Mapping) or set(value) != _ADDRESS_FIELDS:
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


_LOCAL_LOCKS: dict[tuple[str, str], "_LocalLock"] = {}
_LOCAL_LOCKS_GUARD = threading.Lock()


class _LocalLock:
    """Share one reentrant thread lock among CacheStore instances in a process."""

    def __init__(self):
        """Initialize reentrant ownership tracking for one process-local lock."""
        self.lock = threading.RLock()
        self.depth = 0


def _local_lock(key: tuple[str, str]) -> _LocalLock:
    """Return the process-wide lock state for one resolved root and lock name."""
    with _LOCAL_LOCKS_GUARD:
        return _LOCAL_LOCKS.setdefault(key, _LocalLock())


def _try_os_lock(stream) -> bool:
    """Attempt one nonblocking exclusive lock on an open lock-file stream."""
    if os.name == "nt":
        import msvcrt
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock_os(stream) -> None:
    """Release one operating-system lock held by this process."""
    if os.name == "nt":
        import msvcrt
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return
    import fcntl
    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class CacheStore:
    """Publish exact immutable bytes while callers retain all package semantics."""

    def __init__(self, root: Path):
        """Pin an explicit root without creating directories or choosing a fallback."""
        self.root = Path(os.path.abspath(root))
        contained_cache_path(self.root, self.root)

    @property
    def _lock_root_key(self) -> str:
        """Return the normalized root key shared by all store instances."""
        return os.path.normcase(str(self.root))

    def _lock_file(self, name: str) -> Path:
        """Resolve one harmless lock file beneath the sidecar lock directory."""
        validate_cache_component(name)
        directory = ensure_cache_directory(self.root, self.root / "locks")
        return contained_cache_path(self.root, directory / f"{name}.lock")

    @contextmanager
    def _file_lock(self, name: str, *, timeout: float = 30.0):
        """Acquire a reentrant process lock and an OS lock with a bounded timeout."""
        if type(timeout) not in {int, float} or timeout < 0 or not math.isfinite(timeout):
            raise TypeError("timeout must be a finite nonnegative number")
        key = (self._lock_root_key, name)
        state = _local_lock(key)
        started = time.monotonic()
        remaining = lambda: max(0.0, float(timeout) - (time.monotonic() - started))
        acquired = state.lock.acquire(timeout=remaining())
        if not acquired:
            raise CacheLockTimeoutError(f"timed out acquiring cache lock: {name}")
        stream = None
        outer = state.depth == 0
        try:
            if outer:
                path = self._lock_file(name)
                stream = path.open("a+b")
                if stream.seek(0, os.SEEK_END) == 0:
                    stream.write(b"\0")
                    stream.flush()
                    os.fsync(stream.fileno())
                stream.seek(0)
                while not _try_os_lock(stream):
                    if remaining() <= 0:
                        raise CacheLockTimeoutError(f"timed out acquiring cache lock: {name}")
                    time.sleep(min(0.01, remaining()))
            state.depth += 1
            yield
        finally:
            if state.depth:
                state.depth -= 1
            if outer and stream is not None:
                _unlock_os(stream)
                stream.close()
            state.lock.release()

    @contextmanager
    def identity_lock(self, address: CacheAddress, *, timeout: float = 30.0):
        """Serialize one complete lookup, calculation and publication identity."""
        if not isinstance(address, CacheAddress):
            raise TypeError("address must be a CacheAddress")
        digest = hashlib.sha256(_json_bytes(asdict(address))).hexdigest()
        with self._file_lock(f"identity-{digest}", timeout=timeout):
            yield

    @contextmanager
    def _catalog_lock(self, *, timeout: float = 30.0):
        """Serialize short catalog, index and authentication metadata updates."""
        with self._file_lock("catalog", timeout=timeout):
            yield

    def _entry_directory(self, address: CacheAddress) -> Path:
        """Join only a validated full address beneath the verified sidecar root."""
        if not isinstance(address, CacheAddress):
            raise TypeError("address must be a CacheAddress")
        return contained_cache_path(
            self.root,
            self.root / "sources" / address.source_fingerprint / "outputs"
            / address.package_id / address.output_port / address.layer / address.identity,
        )

    def _auth_path(self, key_id: str) -> Path:
        """Resolve one authentication secret path after validating its key ID."""
        validate_cache_component(key_id)
        if len(key_id) != 64 or any(char not in "0123456789abcdef" for char in key_id):
            raise CacheValidationError("authentication key ID must be a lowercase SHA-256 digest")
        return contained_cache_path(
            self.root, self.root / "auth" / key_id / ".free_space_cache_key",
        )

    def _read_auth_key(self, key_id: str) -> bytes:
        """Read and verify an entry-owned authentication secret without logging it."""
        path = self._auth_path(key_id)
        try:
            information = path.lstat()
        except FileNotFoundError as exc:
            raise CacheAuthenticationError(
                f"Task 2 authentication key is unavailable: {key_id}"
            ) from exc
        if not stat.S_ISREG(information.st_mode):
            raise CacheAuthenticationError("authentication key is not a regular file")
        secret = path.read_bytes()
        if hashlib.sha256(secret).hexdigest() != key_id:
            raise CacheAuthenticationError("authentication key digest does not match its ID")
        return secret

    def register_auth_key(self, secret: bytes) -> str:
        """Create an authentication key once and return its stable SHA-256 ID."""
        if type(secret) is not bytes or not secret:
            raise TypeError("secret must be nonempty bytes")
        key_id = hashlib.sha256(secret).hexdigest()
        with self._catalog_lock():
            directory = ensure_cache_directory(self.root, self.root / "auth" / key_id)
            path = self._auth_path(key_id)
            try:
                existing = path.lstat()
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if not stat.S_ISREG(existing.st_mode) or path.read_bytes() != secret:
                    raise CacheConflictError("authentication key ID is already bound to different bytes")
                return key_id
            descriptor, temporary = tempfile.mkstemp(
                prefix=".key.", suffix=".staging", dir=directory,
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(secret)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary_path = contained_cache_path(self.root, Path(temporary))
                try:
                    os.link(temporary_path, path, follow_symlinks=False)
                except FileExistsError:
                    if path.read_bytes() != secret:
                        raise CacheConflictError("authentication key ID is already bound to different bytes")
                finally:
                    temporary_path.unlink(missing_ok=True)
            except Exception:
                Path(temporary).unlink(missing_ok=True)
                raise
        return key_id

    def get_or_create_auth_key(self) -> bytes:
        """Return the sidecar's existing free-space key or create one atomically.

        Package adapters need a stable HMAC domain, but they should not reach into
        the store's catalog lock or authentication directory layout.  Prefer an
        already published keyed secret, retain a legacy root secret during
        adoption, and create a new keyed secret only when the sidecar is empty.
        """
        with self._catalog_lock():
            # Keep the destination's chosen domain stable when migration adds another key.
            default_path = self.root / ".default_auth_key.json"
            try:
                default = _read_json(self.root, default_path)
                key_id = default.get("key_id") if type(default) is dict else None
                if type(key_id) is str:
                    validate_cache_component(key_id)
                    return self._read_auth_key(key_id)
            except (OSError, CacheValidationError, CacheAuthenticationError):
                pass

            legacy = self.root / ".free_space_cache_key"
            try:
                information = legacy.lstat()
                secret = legacy.read_bytes()
            except OSError:
                secret = None
                information = None
            if information is not None and stat.S_ISREG(information.st_mode) and secret:
                key_id = self.register_auth_key(secret)
                write_receipt(default_path, {"key_id": key_id})
                return secret

            auth_root = self.root / "auth"
            if auth_root.is_dir():
                for directory in self._child_directories(auth_root):
                    candidate = directory / ".free_space_cache_key"
                    try:
                        information = candidate.lstat()
                        secret = candidate.read_bytes()
                    except OSError:
                        continue
                    if (
                        stat.S_ISREG(information.st_mode)
                        and secret
                        and hashlib.sha256(secret).hexdigest() == directory.name
                    ):
                        write_receipt(default_path, {"key_id": directory.name})
                        return secret

            secret = secrets.token_bytes(32)
            key_id = self.register_auth_key(secret)
            write_receipt(default_path, {"key_id": key_id})
            return secret

    def _validation_context(self, address: CacheAddress, receipt) -> CacheValidationContext:
        """Resolve the immutable receipt's own authentication domain for owner validation."""
        key_id = receipt["auth_key_id"]
        if key_id is None:
            return CacheValidationContext(address, None, None, receipt["contract"])
        return CacheValidationContext(
            address, key_id, self._read_auth_key(key_id), receipt["contract"],
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
        auth_key_id = receipt["auth_key_id"]
        if auth_key_id is not None:
            if type(auth_key_id) is not str:
                raise CacheValidationError("cache auth_key_id must be a string or null")
            self._auth_path(auth_key_id)
        payload = _read_file(self.root, directory / "payload.json")
        if (
            len(payload) != metadata["size"]
            or hashlib.sha256(payload).hexdigest() != metadata["sha256"]
        ):
            raise CacheValidationError("cache payload size or checksum does not match")
        if auth_key_id is not None:
            self._read_auth_key(auth_key_id)
        return receipt, payload

    def _reuse_origin(self, address: CacheAddress) -> str:
        """Read persisted lookup provenance while keeping receipts immutable."""
        path = self._provenance_path(address)
        try:
            document = _read_json(self.root, path)
        except (FileNotFoundError, CacheValidationError):
            return "local"
        if type(document) is dict and document.get("reuse_origin") in {
            "migrated", "legacy_adopted", "local",
        }:
            return document["reuse_origin"]
        return "local"

    def _entry(
        self, address, receipt, directory, *, status: CacheStatus | str = CacheStatus.COMPLETE,
        reuse_origin: str | None = None,
    ) -> CacheEntry:
        """Expose frozen publication metadata after its bytes have been checked."""
        return CacheEntry(
            address, receipt, directory / "receipt.json",
            (directory / "payload.json",), status,
            self._reuse_origin(address) if reuse_origin is None else reuse_origin,
        )

    def _provenance_path(self, address: CacheAddress) -> Path:
        """Resolve per-entry migration provenance outside immutable receipt bytes."""
        digest = hashlib.sha256(_json_bytes(asdict(address))).hexdigest()
        return contained_cache_path(self.root, self.root / "provenance" / f"{digest}.json")

    def _write_provenance(self, address: CacheAddress, reuse_origin: str) -> None:
        """Atomically record lookup provenance for a copied or adopted entry."""
        if reuse_origin not in {"local", "migrated", "legacy_adopted"}:
            raise ValueError("unknown cache reuse origin")
        directory = ensure_cache_directory(self.root, self.root / "provenance")
        write_receipt(self._provenance_path(address), {
            "schema": "cache-provenance/v1",
            "address": asdict(address),
            "reuse_origin": reuse_origin,
        })

    def record_reuse_origin(self, address: CacheAddress, reuse_origin: str) -> None:
        """Record adapter-visible reuse provenance through the public store API."""
        if not isinstance(address, CacheAddress):
            raise TypeError("address must be a CacheAddress")
        with self.identity_lock(address):
            self._write_provenance(address, reuse_origin)

    def _lookup_path(self, address: CacheAddress) -> Path:
        """Keep reviewed legacy lookup facts outside immutable payloads and the index."""
        digest = _fingerprint(asdict(address))
        return contained_cache_path(self.root, self.root / "lookups" / f"{digest}.json")

    def get_lookup_binding(self, request_address: CacheAddress) -> Mapping[str, Any] | None:
        """Read intact lookup facts; only the package can authorize numerical reuse."""
        path = self._lookup_path(request_address)
        if not path.exists():
            return None
        document = _read_json(self.root, path)
        fields = {"schema", "request_address", "legacy_address", "attestation", "fingerprint"}
        if (not isinstance(document, dict) or set(document) != fields
                or document["schema"] != "lookup-binding/v1"
                or _decode_address(document["request_address"]) != request_address
                or not isinstance(document["attestation"], dict)
                or document["fingerprint"] != _fingerprint({
                    key: value for key, value in document.items() if key != "fingerprint"})):
            raise CacheValidationError("invalid legacy lookup binding")
        _decode_address(document["legacy_address"])
        return _freeze(document)

    def record_lookup_binding(self, request_address: CacheAddress, legacy_address: CacheAddress,
                              *, attestation: Mapping[str, Any]) -> Mapping[str, Any]:
        """Publish one immutable, package-reviewed current-to-original lookup binding."""
        if not isinstance(attestation, Mapping):
            raise TypeError("lookup attestation must be a mapping")
        document = {"schema": "lookup-binding/v1", "request_address": asdict(request_address),
                    "legacy_address": asdict(legacy_address), "attestation": _json_value(attestation)}
        document["fingerprint"] = _fingerprint(document)
        with self.identity_lock(request_address):
            previous = self.get_lookup_binding(request_address)
            if previous is not None:
                if _json_bytes(previous) != _json_bytes(document):
                    raise CacheConflictError("current request has a different legacy lookup binding")
                return previous
            if self._read_storage(legacy_address) is None:
                raise CacheValidationError("lookup target must be a complete stored entry")
            path = self._lookup_path(request_address)
            ensure_cache_directory(self.root, path.parent)
            write_receipt(path, document)
        return _freeze(document)

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
            validator(saved_payload, self._validation_context(address, saved_receipt))
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
        """Serialize one complete publication while holding its identity lock."""
        # Preserve the no-side-effects-on-rejected-input contract for a cold cache.
        if not self.root.exists():
            if not isinstance(contract, Mapping) or type(payload) is not bytes:
                raise TypeError("invalid cache publication arguments")
            normalized_contract = _json_value(_freeze(contract))
            key = None if auth_key_id is None else self._read_auth_key(auth_key_id)
            validator(
                payload,
                CacheValidationContext(address, auth_key_id, key, normalized_contract),
            )
        with self.identity_lock(address):
            result = self._put_unlocked(
                address, contract=contract, payload=payload,
                payload_format=payload_format, upstream_refs=upstream_refs,
                validator=validator, auth_key_id=auth_key_id,
            )
            with self._catalog_lock():
                self._write_manifest()
            return result

    def _put_unlocked(
        self, address: CacheAddress, *, contract: Mapping[str, Any],
        payload: bytes, payload_format: str,
        upstream_refs: tuple[CacheAddress, ...] = (),
        validator: CacheValidator, auth_key_id: str | None = None,
    ) -> CacheEntry:
        """Validate, fsync and publish immutable bytes without resolving parameters."""
        final = self._entry_directory(address)
        if auth_key_id is not None:
            if type(auth_key_id) is not str:
                raise TypeError("auth_key_id must be a string or None")
            auth_key_id = self._auth_path(auth_key_id).parent.name
            auth_key = self._read_auth_key(auth_key_id)
        else:
            auth_key = None
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
        validator(payload, CacheValidationContext(address, auth_key_id, auth_key, contract))
        receipt = {
            "schema": "cache-receipt/v1",
            "address": asdict(address),
            "contract": contract,
            "payload": {
                "path": "payload.json", "format": payload_format,
                "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            },
            "upstream_refs": [asdict(reference) for reference in upstream_refs],
            "auth_key_id": auth_key_id,
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
        validator(payload, self._validation_context(address, receipt))
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
        """Publish source facts or update only their current locator atomically."""
        with self._catalog_lock():
            result = self._put_source_binding_unlocked(binding)
            self._write_manifest()
            return result

    def _put_source_binding_unlocked(self, binding: SourceBinding) -> SourceBinding:
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

    def _child_directories(self, directory: Path) -> tuple[Path, ...]:
        """List direct child directories without following links or reparse points."""
        directory = contained_cache_path(self.root, directory)
        try:
            information = directory.lstat()
        except FileNotFoundError:
            return ()
        if not stat.S_ISDIR(information.st_mode):
            raise CacheValidationError(f"cache scan target is not a directory: {directory}")
        result = []
        for child in directory.iterdir():
            child = contained_cache_path(self.root, child)
            child_info = child.lstat()
            if stat.S_ISLNK(child_info.st_mode) or getattr(
                child_info, "st_file_attributes", 0
            ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise CachePathError(f"cache scan cannot follow linked path: {child}")
            if stat.S_ISDIR(child_info.st_mode):
                result.append(child)
        return tuple(result)

    def _scan_addresses(self) -> tuple[tuple[CacheAddress, Path], ...]:
        """Discover addressed entry directories without trusting the advisory index."""
        sources = self.root / "sources"
        if not sources.exists():
            return ()
        result = []
        for source in self._child_directories(sources):
            validate_cache_component(source.name)
            outputs = source / "outputs"
            for package in self._child_directories(outputs):
                validate_cache_component(package.name)
                for output_port in self._child_directories(package):
                    validate_cache_component(output_port.name)
                    for layer in self._child_directories(output_port):
                        validate_cache_component(layer.name)
                        if layer.name not in {"raw", "processed"}:
                            continue
                        for identity in self._child_directories(layer):
                            if identity.name.startswith("."):
                                continue
                            validate_cache_component(identity.name)
                            result.append((CacheAddress(
                                source.name, package.name, output_port.name,
                                layer.name, identity.name,
                            ), identity))
        return tuple(sorted(result, key=lambda item: str(item[0])))

    def _quarantine_directory(
        self, address: CacheAddress, directory: Path, reason: str | None = None,
    ) -> Path | None:
        """Move one malformed addressed directory out of the hit namespace."""
        directory = contained_cache_path(self.root, directory)
        try:
            info = directory.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise CachePathError("only a regular cache entry directory can be quarantined")
        quarantine_root = ensure_cache_directory(self.root, self.root / "quarantine")
        suffix = hashlib.sha256(
            f"{time.time_ns()}:{address.identity}".encode(),
        ).hexdigest()[:16]
        destination = contained_cache_path(
            self.root, quarantine_root / f"{address.source_fingerprint}-{address.package_id}-"
            f"{address.output_port}-{address.layer}-{address.identity}-{suffix}",
        )
        os.rename(directory, destination)
        if reason:
            write_receipt(destination / "reason.json", {
                "schema": "cache-quarantine/v1",
                "address": asdict(address),
                "reason": str(reason),
            })
        return destination

    def quarantine(self, address: CacheAddress, *, reason: str = "manual quarantine") -> Path | None:
        """Move an exact entry to quarantine while preserving its bytes for diagnosis."""
        if not isinstance(address, CacheAddress):
            raise TypeError("address must be a CacheAddress")
        with self.identity_lock(address):
            result = self._quarantine_directory(address, self._entry_directory(address), reason)
        if result is not None:
            self.rebuild_index()
        return result

    def _entry_status(self, receipt) -> CacheStatus:
        """Derive lifecycle availability from immutable storage and upstream presence."""
        return (
            CacheStatus.COMPLETE
            if self._dependencies_available(receipt["upstream_refs"], set())
            else CacheStatus.ORPHANED
        )

    def _scan_entries(self, *, quarantine_invalid: bool = True) -> tuple[CacheEntry, ...]:
        """Read all valid entries and quarantine malformed addressed directories."""
        entries = []
        for address, directory in self._scan_addresses():
            try:
                stored = self._read_storage(address, directory=directory)
            except CacheAuthenticationError:
                try:
                    receipt = _read_json(self.root, directory / "receipt.json")
                    if _decode_address(receipt.get("address")) != address:
                        raise CacheValidationError("entry address mismatch")
                    entries.append(self._entry(
                        address, receipt, directory, status=CacheStatus.UNAVAILABLE,
                    ))
                except (CacheValidationError, TypeError, AttributeError):
                    if quarantine_invalid:
                        self._quarantine_directory(address, directory, "unreadable authenticated entry")
                continue
            except (CacheValidationError, CacheUnsupportedError):
                if quarantine_invalid:
                    self._quarantine_directory(address, directory, "invalid cache entry")
                continue
            if stored is None:
                continue
            receipt, _payload = stored
            entries.append(self._entry(address, receipt, directory, status=self._entry_status(receipt)))
        return tuple(sorted(entries, key=lambda entry: str(entry.address)))

    def list(
        self, *, source_fingerprint: str | None = None,
        package_id: str | None = None, output_port: str | None = None,
    ) -> tuple[CacheEntry, ...]:
        """List storage-valid entries while deriving dependency lifecycle status."""
        for component in (source_fingerprint, package_id, output_port):
            if component is not None:
                validate_cache_component(component)
        entries = self._scan_entries()
        return tuple(entry for entry in entries if (
            (source_fingerprint is None or entry.address.source_fingerprint == source_fingerprint)
            and (package_id is None or entry.address.package_id == package_id)
            and (output_port is None or entry.address.output_port == output_port)
        ))

    def delete_exact(self, address: CacheAddress) -> bool:
        """Delete one exact addressed version and preserve every neighboring version."""
        if not isinstance(address, CacheAddress):
            raise TypeError("address must be a CacheAddress")
        deleted = False
        with self.identity_lock(address):
            directory = self._entry_directory(address)
            try:
                information = directory.lstat()
            except FileNotFoundError:
                information = None
            if information is not None:
                if not stat.S_ISDIR(information.st_mode) or stat.S_ISLNK(information.st_mode):
                    raise CachePathError("cache entry is not a regular directory")
                shutil.rmtree(directory)
                deleted = True
                self._provenance_path(address).unlink(missing_ok=True)
        if deleted:
            self.rebuild_index()
        return deleted

    def _write_index(self, entries: tuple[CacheEntry, ...]) -> Mapping[str, Any]:
        """Replace the disposable catalog from receipt-derived entry facts."""
        document = {
            "schema": "cache-index/v1",
            "entries": [
                {
                    "address": asdict(entry.address),
                    "status": entry.status.value,
                    "reuse_origin": entry.reuse_origin,
                    "upstream_refs": _json_value(entry.receipt["upstream_refs"]),
                }
                for entry in entries
            ],
        }
        ensure_cache_directory(self.root, self.root)
        write_receipt(self.root / "index.json", document)
        return document

    def _manifest(self) -> dict:
        """Read durable storage metadata without using it to authorize a hit."""
        path = contained_cache_path(self.root, self.root / "manifest.json")
        if not path.exists():
            return {"schema": "cache-manifest/v1", "cache_format_version": "cache-receipt/v1",
                    "producer_versions": {"cache_store": "1", "python": sys.version.split()[0]},
                    "sources": {}, "migrations": []}
        document = _read_json(self.root, path)
        if (not isinstance(document, dict) or document.get("schema") != "cache-manifest/v1"
                or document.get("cache_format_version") != "cache-receipt/v1"
                or not isinstance(document.get("producer_versions"), dict)
                or not isinstance(document.get("sources"), dict)
                or not isinstance(document.get("migrations"), list)):
            raise CacheValidationError("unsupported cache manifest")
        return document

    def _write_manifest(self, *, migrations=()) -> None:
        """Record source facts and migration history while holding the catalog lock."""
        document = self._manifest()
        sources = self.root / "sources"
        document["sources"] = {
            directory.name: _binding_document(binding)
            for directory in self._child_directories(sources)
            if (binding := self.get_source_binding(directory.name)) is not None
        }
        for migration in migrations:
            if migration not in document["migrations"]:
                document["migrations"].append(migration)
        write_receipt(self.root / "manifest.json", document)

    def rebuild_index(self) -> Mapping[str, Any]:
        """Rebuild index.json from authoritative receipts and dependency snapshots."""
        with self._catalog_lock():
            entries = self._scan_entries()
            return self._write_index(entries)

    @staticmethod
    def _address_label(address: CacheAddress) -> str:
        """Format an address as a stable report key without exposing filesystem syntax."""
        return json.dumps(asdict(address), sort_keys=True, separators=(",", ":"))

    def _copy_auth_material_from(self, source: "CacheStore") -> bool:
        """Copy source authentication domains without replacing destination secrets."""
        auth_root = source.root / "auth"
        if not auth_root.exists():
            return True
        for directory in source._child_directories(auth_root):
            key_id = directory.name
            validate_cache_component(key_id)
            source_path = source._auth_path(key_id)
            secret = source._read_auth_key(key_id)
            self.register_auth_key(secret)
            if self._read_auth_key(key_id) != secret:
                raise CacheConflictError(f"authentication domain conflict: {key_id}")
        return True

    def _copy_source_bindings_from(self, source: "CacheStore") -> None:
        """Copy immutable source facts and retain their original locator bytes."""
        sources = source.root / "sources"
        if not sources.exists():
            return
        for source_dir in source._child_directories(sources):
            path = source_dir / "source.json"
            if not path.exists():
                continue
            binding = source.get_source_binding(source_dir.name)
            if binding is None:
                continue
            existing = self.get_source_binding(source_dir.name)
            if existing is not None and _binding_facts(existing) != _binding_facts(binding):
                raise CacheConflictError(
                    f"source binding conflict: {source_dir.name}",
                )
            if existing is None:
                self.put_source_binding(binding)

    def _copy_one_entry(
        self, source: "CacheStore", address: CacheAddress, validator: CacheValidator,
    ) -> str:
        """Copy one validated immutable entry after releasing the source lock."""
        with source.identity_lock(address):
            source_directory = source._entry_directory(address)
            stored = source._read_storage(address, directory=source_directory)
            if stored is None:
                raise CacheValidationError("source entry disappeared during migration")
            receipt, payload = stored
            validator(payload, source._validation_context(address, receipt))
            receipt_bytes = (source_directory / "receipt.json").read_bytes()
            payload_bytes = (source_directory / "payload.json").read_bytes()

        with self.identity_lock(address):
            destination = self._entry_directory(address)
            existing = None
            try:
                existing = self._read_storage(address, directory=destination)
            except CacheValidationError as exc:
                raise CacheConflictError("destination addressed artifact is invalid") from exc
            if existing is not None:
                existing_receipt, existing_payload = existing
                if (
                    _json_bytes(existing_receipt) == _json_bytes(receipt)
                    and existing_payload == payload
                ):
                    self._write_provenance(address, "migrated")
                    return "reused"
                raise CacheConflictError("destination identity has different immutable bytes")

            parent = ensure_cache_directory(self.root, destination.parent)
            stage = contained_cache_path(self.root, Path(tempfile.mkdtemp(
                prefix=f".{address.identity}.migration-", dir=parent,
            )))
            try:
                stage_payload = contained_cache_path(self.root, stage / "payload.json")
                stage_receipt = contained_cache_path(self.root, stage / "receipt.json")
                stage_payload.write_bytes(payload_bytes)
                with stage_payload.open("r+b") as stream:
                    os.fsync(stream.fileno())
                stage_receipt.write_bytes(receipt_bytes)
                with stage_receipt.open("r+b") as stream:
                    os.fsync(stream.fileno())
                verified = self._read_storage(address, directory=stage)
                if verified is None:
                    raise CacheValidationError("staged migration disappeared")
                validator(payload, self._validation_context(address, receipt))
                _rename_no_replace(stage, destination)
                stage = None
            finally:
                if stage is not None:
                    shutil.rmtree(stage, ignore_errors=True)
            self._write_provenance(address, "migrated")
            return "copied"

    def _copy_lookup_bindings_from(self, source: "CacheStore") -> None:
        """Retain reviewed aliases only after their immutable targets have copied."""
        directory = source.root / "lookups"
        if not directory.exists():
            return
        contained_cache_path(source.root, directory)
        for path in directory.iterdir():
            document = _read_json(source.root, path)
            request = _decode_address(document.get("request_address"))
            checked = source.get_lookup_binding(request)
            legacy = _decode_address(checked["legacy_address"])
            self.record_lookup_binding(request, legacy, attestation=checked["attestation"])

    def _copy_auxiliary_tree(self, source: "CacheStore", directory: Path,
                             destination: Path, *, settings=False) -> None:
        """Copy closed evidence byte-for-byte; scratch is never reusable data."""
        for current, directories, filenames in os.walk(directory, followlinks=False):
            current = contained_cache_path(source.root, Path(current))
            directories[:] = [name for name in directories if name != "scratch"]
            for name in directories:
                contained_cache_path(source.root, current / name)
            for name in filenames:
                path = contained_cache_path(source.root, current / name)
                payload = _read_file(source.root, path)
                target = contained_cache_path(self.root, destination / path.relative_to(directory))
                if target.exists() and _read_file(self.root, target) != payload:
                    if not settings:
                        raise CacheConflictError(f"closed run artifact conflict: {target}")
                    # A named imported profile preserves a destination's own settings.
                    profile = "imported-" + hashlib.sha256(str(source.root).encode()).hexdigest()[:16]
                    target = destination / profile / path.relative_to(directory)
                    target = contained_cache_path(self.root, target)
                ensure_cache_directory(self.root, target.parent)
                if target.exists():
                    if _read_file(self.root, target) != payload:
                        raise CacheConflictError(f"imported artifact conflict: {target}")
                else:
                    with target.open("xb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())

    def _copy_closed_runs_from(self, source: "CacheStore") -> list[tuple[str, str]]:
        """Preserve settings and terminal run evidence without moving active jobs."""
        failures = []
        settings = source.root / "settings"
        if settings.exists():
            try:
                with self._catalog_lock():
                    self._copy_auxiliary_tree(source, settings, self.root / "settings", settings=True)
            except (OSError, ValueError) as exc:
                failures.append(("settings", str(exc)))
        roots = [source.root / "runs"]
        sources = source.root / "sources"
        if sources.exists():
            roots.extend(path / "runs" for path in source._child_directories(sources))
        for runs in roots:
            if not runs.exists():
                continue
            for run in source._child_directories(runs):
                label = str(run.relative_to(source.root))
                try:
                    journal = _read_json(source.root, run / "run.json")
                    if (journal.get("schema") != "cache-run/v1"
                            or journal.get("state") not in {"complete", "failed", "interrupted"}):
                        raise CacheValidationError("run is active or lacks a terminal journal")
                    # The consumer still validates every checkpoint's exact input/policy binding.
                    with self._file_lock("run-" + _fingerprint(label)):
                        self._copy_auxiliary_tree(source, run, self.root / run.relative_to(source.root))
                except (OSError, ValueError) as exc:
                    failures.append((label, str(exc)))
        return failures

    def migrate_to(
        self, destination: Path, *, validators: Mapping[str, CacheValidator],
    ) -> MigrationReport:
        """Copy validated entries, source bindings and authentication domains to a new root."""
        destination = Path(os.path.abspath(destination))
        if destination == self.root:
            raise ValueError("migration destination must differ from the source root")
        if destination.is_relative_to(self.root) or self.root.is_relative_to(destination):
            raise ValueError("migration roots cannot contain one another")
        if not isinstance(validators, Mapping):
            raise TypeError("validators must be a mapping")
        target = CacheStore(destination)
        copied: list[CacheAddress] = []
        reused: list[CacheAddress] = []
        failed: list[tuple[str, str]] = []
        quarantined: list[str] = []
        auth_material_copied = False
        try:
            target._copy_auth_material_from(self)
            auth_material_copied = True
            target._copy_source_bindings_from(self)
        except (CacheValidationError, CacheConflictError, OSError) as exc:
            failed.append(("catalog", str(exc)))

        for address, directory in self._scan_addresses():
            validator = validators.get(f"{address.package_id}:{address.layer}")
            if validator is None:
                validator = validators.get(address.package_id)
            label = self._address_label(address)
            if validator is None:
                failed.append((label, "no validator supplied"))
                continue
            try:
                outcome = target._copy_one_entry(self, address, validator)
                (copied if outcome == "copied" else reused).append(address)
            except CacheAuthenticationError as exc:
                failed.append((label, str(exc)))
            except (CacheValidationError, CacheConflictError, CacheUnsupportedError, OSError) as exc:
                if isinstance(exc, CacheValidationError) and not isinstance(
                    exc, (CacheConflictError, CacheUnsupportedError),
                ):
                    try:
                        quarantined_path = self.quarantine(address, reason=str(exc))
                    except (CachePathError, OSError):
                        quarantined_path = None
                    if quarantined_path is not None:
                        quarantined.append(str(quarantined_path))
                failed.append((label, str(exc)))
            except (ValueError, TypeError) as exc:
                # Owner rejection is entry-local; preserve its bytes and continue independent entries.
                failed.append((label, str(exc)))

        try:
            target._copy_lookup_bindings_from(self)
        except (CacheValidationError, CacheConflictError, OSError, TypeError) as exc:
            failed.append(("lookups", str(exc)))
        failed.extend(target._copy_closed_runs_from(self))

        try:
            target.rebuild_index()
            index_rebuilt = True
        except (CacheValidationError, OSError) as exc:
            failed.append(("index", str(exc)))
            index_rebuilt = False
        report = MigrationReport(
            source=self.root, destination=destination,
            copied=tuple(copied), reused=tuple(reused), failed=tuple(failed),
            quarantined=tuple(quarantined), index_rebuilt=index_rebuilt,
            auth_material_copied=auth_material_copied,
            old_directory_retained=self.root.exists(),
        )
        try:
            with self._catalog_lock():
                inherited = self._manifest()["migrations"]
            event = {"source": str(self.root), "destination": str(destination),
                     "copied": [asdict(address) for address in copied],
                     "reused": [asdict(address) for address in reused],
                     "failed": [list(failure) for failure in failed],
                     "status": "partial" if failed else "complete"}
            with target._catalog_lock():
                target._write_manifest(migrations=(*inherited, event))
        except (OSError, ValueError, TypeError) as exc:
            report = replace(report, failed=(*report.failed, ("manifest", str(exc))))
        return report
