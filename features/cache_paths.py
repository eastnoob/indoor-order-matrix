"""Portable cache addresses, verified containment and immutable source bindings."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Literal

from .evidence_package_parameters import _freeze
from .evidence_package_storage import write_receipt


_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_RESERVED = {"CON", "PRN", "AUX", "NUL"}
_RESERVED.update(f"COM{number}" for number in range(1, 10))
_RESERVED.update(f"LPT{number}" for number in range(1, 10))


class CachePathError(ValueError):
    """Reject an unsafe cache address or filesystem boundary."""


def validate_cache_component(value: str) -> str:
    """Require one portable filename component without Windows aliases or streams."""
    if type(value) is not str:
        raise TypeError("cache address components must be strings")
    if (
        not _COMPONENT.fullmatch(value)
        or value.endswith(".")
        or value.split(".", 1)[0].upper() in _RESERVED
    ):
        raise CachePathError(f"unsafe cache address component: {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class CacheAddress:
    """Separate durable source identity from package and calculation identities."""

    source_fingerprint: str
    package_id: str
    output_port: str
    layer: Literal["raw", "processed"]
    identity: str

    def __post_init__(self):
        """Validate every component before any address can be joined to a root."""
        for value in (
            self.source_fingerprint, self.package_id, self.output_port,
            self.layer, self.identity,
        ):
            validate_cache_component(value)
        if self.layer not in {"raw", "processed"}:
            raise CachePathError("cache layer must be raw or processed")


@dataclass(frozen=True, slots=True)
class SourceBinding:
    """Retain verified source facts independently of the model's current locator."""

    source_fingerprint: str
    canonical_source_identity: str
    content_fingerprint: str
    external_dependencies: Mapping[str, str]
    current_locator: str

    def __post_init__(self):
        """Detach external fingerprints and validate immutable source identity fields."""
        validate_cache_component(self.source_fingerprint)
        for value in (
            self.canonical_source_identity, self.content_fingerprint,
            self.current_locator,
        ):
            if type(value) is not str or not value:
                raise TypeError("source identity, content and locator must be nonempty strings")
        if not isinstance(self.external_dependencies, Mapping):
            raise TypeError("external_dependencies must be a mapping")
        if any(
            type(key) is not str or not key
            or type(value) is not str or not value
            for key, value in self.external_dependencies.items()
        ):
            raise TypeError("external dependency names and fingerprints must be nonempty strings")
        object.__setattr__(
            self, "external_dependencies", _freeze(self.external_dependencies),
        )


def resolve_sidecar_path(model_path: Path) -> Path:
    """Locate a model-stem sidecar without using its path as result identity."""
    model_path = Path(model_path)
    if model_path.is_dir() or model_path.suffix.lower() not in {".ifc", ".blend"}:
        raise ValueError("a saved IFC or Blender model path is required")
    return model_path.with_suffix(".order_analyzer")


@dataclass(frozen=True, slots=True)
class SidecarLocator:
    """Resolve a model-local cache directory without changing cache identity."""

    model_path: Path | None
    explicit_directory: Path | None = None
    temporary_root: Path | None = None

    def resolve(self) -> Path:
        """Return an explicit, saved-model, or caller-owned temporary location."""
        if self.explicit_directory is not None:
            return Path(self.explicit_directory)
        if self.model_path is not None:
            model = Path(self.model_path)
            if model.is_dir():
                raise ValueError("a model directory cannot be a cache source; provide explicit_directory")
            return resolve_sidecar_path(model)
        if self.temporary_root is None:
            raise ValueError("an unsaved model requires temporary_root or explicit_directory")
        return Path(self.temporary_root)

    def source_root(self, source_fingerprint: str) -> Path:
        """Return the source namespace below the resolved sidecar."""
        validate_cache_component(source_fingerprint)
        return self.resolve() / "sources" / source_fingerprint


def sidecar_layout(root: Path) -> dict[str, Path]:
    """Describe stable sidecar locations without creating any directories."""
    root = Path(root)
    return {
        "root": root,
        "sources": root / "sources",
        "index": root / "index.json",
        "manifest": root / "manifest.json",
        "locks": root / "locks",
        "quarantine": root / "quarantine",
    }


def _unlinked_stat(path: Path):
    """Inspect one path without following symlinks, junctions or reparse points."""
    try:
        information = path.lstat()
    except FileNotFoundError:
        return None
    if (
        stat.S_ISLNK(information.st_mode)
        or getattr(information, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    ):
        raise CachePathError(f"cache paths cannot traverse links or reparse points: {path}")
    return information


def _comparison_path(path: Path) -> str:
    """Normalize Windows extended-path spelling before comparing resolved boundaries."""
    value = os.path.normcase(os.path.normpath(os.fspath(path)))
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def contained_cache_path(root: Path, path: Path) -> Path:
    """Verify lexical and resolved containment without traversing directory links."""
    root = Path(os.path.abspath(root))
    path = Path(os.path.abspath(path))
    if not path.is_relative_to(root):
        raise CachePathError("cache path is outside its configured root")
    # Inspect ancestors before resolving: resolving first would follow a junction.
    for candidate in reversed((path, *path.parents)):
        information = _unlinked_stat(candidate)
        if (
            information is not None
            and (candidate != path or candidate == root)
            and not stat.S_ISDIR(information.st_mode)
        ):
            raise CachePathError(f"cache directory ancestor is not a directory: {candidate}")
    resolved_path = path.resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    path_text = _comparison_path(resolved_path)
    root_text = _comparison_path(resolved_root)
    try:
        contained = os.path.commonpath((path_text, root_text)) == root_text
    except ValueError:
        contained = False
    if not contained:
        raise CachePathError(
            f"resolved cache path is outside its configured root: "
            f"root={root!s} path={path!s} resolved_root={resolved_root!s} "
            f"resolved_path={resolved_path!s}"
        )
    return path


def ensure_cache_directory(root: Path, directory: Path) -> Path:
    """Check containment before creating parents and again after their creation."""
    directory = contained_cache_path(root, directory)
    directory.mkdir(parents=True, exist_ok=True)
    directory = contained_cache_path(root, directory)
    information = directory.lstat()
    if not stat.S_ISDIR(information.st_mode):
        raise CachePathError("cache directory is not a directory")
    return directory


def create_run_directory(*, model_path=None, temporary_root=None, root=None, prefix="run") -> Path:
    """Allocate a unique run beside the model or below an explicitly chosen export parent."""
    validate_cache_component(prefix)
    boundary = (Path(root) if root is not None else SidecarLocator(
        model_path=model_path, temporary_root=temporary_root).resolve())
    parent = boundary if root is not None else boundary / "runs"
    parent = ensure_cache_directory(boundary, parent)
    return contained_cache_path(boundary, Path(tempfile.mkdtemp(prefix=prefix + "_", dir=parent)))


@contextmanager
def run_journal(directory: Path):
    """Mark one publication active until it completes or fails without hiding its error."""
    directory = ensure_cache_directory(directory, directory)
    path = contained_cache_path(directory, directory / "run.json")
    write_receipt(path, {"schema": "cache-run/v1", "state": "running"})
    try:
        yield
    except BaseException as error:
        try:
            write_receipt(path, {"schema": "cache-run/v1", "state": "failed"})
        except OSError as journal_error:
            error.add_note(f"Failed to record run state: {journal_error}")
        raise
    else:
        write_receipt(path, {"schema": "cache-run/v1", "state": "complete"})
