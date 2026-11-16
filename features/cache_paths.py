"""Portable cache addresses, verified containment and immutable source bindings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
from typing import Literal

from .evidence_package_parameters import _freeze


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
    if not path.resolve(strict=False).is_relative_to(root.resolve(strict=False)):
        raise CachePathError("resolved cache path is outside its configured root")
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
