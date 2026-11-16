"""Exercise model locators, immutable source facts and filesystem containment."""

from dataclasses import FrozenInstanceError, replace
import os
from pathlib import Path
import subprocess

import pytest

from features.cache_paths import (
    CacheAddress,
    CachePathError,
    SourceBinding,
    contained_cache_path,
    resolve_sidecar_path,
)
from features.cache_store import CacheStore


@pytest.fixture
def directory_link():
    """Create directory links, requiring the Windows junction fallback to work."""
    links = []

    def make_link(link, target):
        """Create one directory link without silently skipping its acceptance case."""
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True, capture_output=True, text=True,
            )
        links.append(link)
        return link

    yield make_link
    for link in reversed(links):
        if link.is_symlink():
            link.unlink()
        else:
            os.rmdir(link)


def demo_address():
    """Return a complete address with distinct source and result identities."""
    return CacheAddress("scene-a", "demo", "combined", "raw", "one")


def validate_demo(payload, context):
    """Accept the exact demo bytes used by the path boundary tests."""
    if payload != b'{"value":1}':
        raise ValueError("invalid demo payload")


def test_saved_model_sidecar(tmp_path):
    """IFC and Blender anchors share the model-stem sidecar convention."""
    assert resolve_sidecar_path(tmp_path / "a.ifc") == tmp_path / "a.order_analyzer"
    assert resolve_sidecar_path(tmp_path / "a.blend") == tmp_path / "a.order_analyzer"
    assert resolve_sidecar_path(tmp_path / "a.IFC") == tmp_path / "a.order_analyzer"


def test_sidecar_rejects_directory_and_other_suffixes(tmp_path):
    """Directories and unrelated files cannot become saved model anchors."""
    directory = tmp_path / "directory.ifc"
    directory.mkdir()
    for path in (directory, tmp_path / "a.json", tmp_path / "unsaved"):
        with pytest.raises(ValueError):
            resolve_sidecar_path(path)


@pytest.mark.parametrize(
    "component",
    [
        "", ".", "..", "../escape", "/absolute", "C:\\x",
        "\\\\server\\share", "x:stream", "a/b", "a\\b",
        "CON", "nul.json", "COM1", "LPT9.txt", "trailing.", "trailing ",
        "bad\x00name", None, True,
    ],
)
@pytest.mark.parametrize(
    "field_name",
    ["source_fingerprint", "package_id", "output_port", "identity"],
)
def test_address_rejects_unsafe_components(component, field_name):
    """Every path-bearing identifier receives the same portable validation."""
    with pytest.raises((TypeError, ValueError)):
        replace(demo_address(), **{field_name: component})


@pytest.mark.parametrize("layer", ["", "intermediate", "../raw", None])
def test_address_rejects_unknown_layers(layer):
    """Only the two existing calculation layers have storage addresses."""
    with pytest.raises((TypeError, ValueError)):
        replace(demo_address(), layer=layer)


def test_containment_rejects_outside_before_creating_parents(tmp_path):
    """A rejected lexical escape leaves both the root and outside area untouched."""
    root = tmp_path / "cache"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"keep")
    with pytest.raises(CachePathError):
        contained_cache_path(root, root / ".." / "outside" / "new" / "payload.json")
    assert not root.exists()
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep"


@pytest.mark.parametrize("operation", ["put", "get"])
def test_store_refuses_directory_link_escape(tmp_path, directory_link, operation):
    """Exact entry access rejects linked ancestors without touching outside data."""
    root = tmp_path / "cache"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"keep")
    store = CacheStore(root)
    root.mkdir()
    directory_link(root / "sources", outside)
    with pytest.raises(CachePathError):
        if operation == "put":
            store.put(
                demo_address(), contract={}, payload=b'{"value":1}',
                payload_format="json", validator=validate_demo,
            )
        else:
            store.get(demo_address(), validator=validate_demo)
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep"


def test_store_refuses_linked_root(tmp_path, directory_link):
    """The configured sidecar root itself cannot be a junction or symlink."""
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"keep")
    root = directory_link(tmp_path / "cache", outside)
    with pytest.raises(CachePathError):
        CacheStore(root)
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep"


def test_store_refuses_replaced_entry_directory(tmp_path, directory_link):
    """An entry replaced by a directory link is rejected on subsequent reads."""
    root = tmp_path / "cache"
    store = CacheStore(root)
    entry = store.put(
        demo_address(), contract={}, payload=b'{"value":1}',
        payload_format="json", validator=validate_demo,
    )
    saved = tmp_path / "saved-entry"
    entry.receipt_path.parent.rename(saved)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"keep")
    directory_link(entry.receipt_path.parent, outside)
    with pytest.raises(CachePathError):
        store.get(demo_address(), validator=validate_demo)
    assert (saved / "payload.json").read_bytes() == b'{"value":1}'
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep"


def test_source_binding_detaches_external_facts():
    """Source facts are detached from callers and cannot be reassigned."""
    dependencies = {"linked-model": "content-b"}
    binding = SourceBinding(
        "scene-a", "canonical-a", "content-a", dependencies, "a.ifc",
    )
    dependencies["linked-model"] = "changed"
    assert binding.external_dependencies["linked-model"] == "content-b"
    with pytest.raises(TypeError):
        binding.external_dependencies["linked-model"] = "changed"
    with pytest.raises(FrozenInstanceError):
        binding.current_locator = "b.ifc"


@pytest.mark.parametrize("operation", ["put", "get"])
def test_source_binding_refuses_link_escape(tmp_path, directory_link, operation):
    """Binding publication and lookup enforce the same source namespace boundary."""
    root = tmp_path / "cache"
    store = CacheStore(root)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"keep")
    directory_link(root / "sources" / "scene-a", outside)
    binding = SourceBinding("scene-a", "canonical-a", "content-a", {}, "a.ifc")
    with pytest.raises(CachePathError):
        if operation == "put":
            store.put_source_binding(binding)
        else:
            store.get_source_binding("scene-a")
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep"
