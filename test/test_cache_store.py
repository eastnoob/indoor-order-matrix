"""Exercise immutable publication independently of package parameter resolution."""

from dataclasses import asdict, replace
import errno
import hashlib
import json
import os

import pytest

import features.cache_store as cache_module
import features.evidence_package_storage as receipt_storage
from features.cache_paths import CacheAddress, SourceBinding
from features.cache_store import (
    CacheConflictError,
    CacheStore,
    CacheUnsupportedError,
    CacheValidationContext,
    CacheValidationError,
)
from features.evidence_package_parameters import (
    ParameterSchema,
    ParameterSpec,
    _fingerprint,
    _json_value,
)
from features.evidence_package_storage import write_receipt


def demo_address(identity="one", *, package="demo", layer="raw"):
    """Create a full address without mixing source and request identities."""
    return CacheAddress("scene-a", package, "combined", layer, identity)


def validate_demo(payload: bytes, context: CacheValidationContext) -> None:
    """Validate package bytes independently of their storage wrapper."""
    if json.loads(payload) != {"value": 1}:
        raise ValueError("invalid demo payload")


def validate_json(payload, context):
    """Accept arbitrary JSON for tests that isolate storage identity checks."""
    json.loads(payload)


def publish_demo(store, address=None, *, contract=None, validator=validate_demo):
    """Publish the shared demo payload through the real storage entry point."""
    return store.put(
        demo_address() if address is None else address,
        contract={} if contract is None else contract,
        payload=b'{"value":1}', payload_format="json", validator=validator,
    )


def rewrite_receipt(entry, field_path, value, *, rehash=True):
    """Change one stored field while optionally retaining a valid wrapper hash."""
    receipt = json.loads(entry.receipt_path.read_bytes())
    parts = field_path.split(".")
    current = receipt
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value
    if rehash:
        receipt["receipt_fingerprint"] = _fingerprint({
            key: item for key, item in receipt.items()
            if key != "receipt_fingerprint"
        })
    write_receipt(entry.receipt_path, receipt)


def test_publication_round_trip_and_namespaces(tmp_path):
    """Package, layer and source namespaces remain independent of local identity."""
    store = CacheStore(tmp_path)
    first = publish_demo(store)
    other = publish_demo(store, demo_address(package="another"))
    processed = publish_demo(store, demo_address(layer="processed"))
    another_source = publish_demo(
        store, replace(demo_address(), source_fingerprint="scene-b"),
    )
    assert len({
        first.receipt_path, other.receipt_path,
        processed.receipt_path, another_source.receipt_path,
    }) == 4
    loaded = CacheStore(tmp_path).get(demo_address(), validator=validate_demo)
    assert loaded.address == first.address
    assert loaded.status == "complete"
    assert loaded.reuse_origin == "local"
    assert loaded.payload_paths[0].read_bytes() == b'{"value":1}'


def test_missing_get_does_not_create_root(tmp_path):
    """A miss performs no publication or parent-directory creation."""
    root = tmp_path / "missing"
    assert CacheStore(root).get(demo_address(), validator=validate_demo) is None
    assert not root.exists()


def test_identical_publication_reuses_exact_bytes(tmp_path):
    """An identical request verifies and reuses its complete immutable directory."""
    store = CacheStore(tmp_path)
    first = publish_demo(store)
    receipt_bytes = first.receipt_path.read_bytes()
    payload_bytes = first.payload_paths[0].read_bytes()
    second = publish_demo(store)
    assert second.receipt_path == first.receipt_path
    assert second.receipt_path.read_bytes() == receipt_bytes
    assert second.payload_paths[0].read_bytes() == payload_bytes


@pytest.mark.parametrize(
    ("payload", "contract"),
    [
        (b'{"value": 1}', {}),
        (b'{"value":2}', {}),
        (b'{"value":1}', {"different": True}),
        (b'{"value":1}', {"number": True}),
    ],
)
def test_same_identity_conflicts_preserve_existing_bytes(tmp_path, payload, contract):
    """Different bytes or contracts cannot replace a complete addressed entry."""
    store = CacheStore(tmp_path)
    first = publish_demo(store, contract={"number": 1}, validator=validate_json)
    before = (first.receipt_path.read_bytes(), first.payload_paths[0].read_bytes())
    with pytest.raises(CacheConflictError):
        store.put(
            demo_address(), contract=contract, payload=payload,
            payload_format="json", validator=validate_json,
        )
    assert (first.receipt_path.read_bytes(), first.payload_paths[0].read_bytes()) == before


def test_same_contract_different_payload_bytes_conflicts(tmp_path):
    """Equivalent JSON values still conflict when their exact payload bytes differ."""
    store = CacheStore(tmp_path)
    first = publish_demo(store)
    before = first.payload_paths[0].read_bytes()
    with pytest.raises(CacheConflictError):
        store.put(
            demo_address(), contract={}, payload=b'{"value": 1}',
            payload_format="json", validator=validate_demo,
        )
    assert first.payload_paths[0].read_bytes() == before


def test_receipt_and_validation_contract_are_deeply_immutable(tmp_path):
    """Nested caller edits cannot alter stored receipts or callback context."""
    contract = {"nested": {"items": [{"value": 1}]}}
    contexts = []

    def validate(payload, context):
        """Retain a context and verify that its nested contract cannot be edited."""
        validate_demo(payload, context)
        contexts.append(context)
        with pytest.raises(TypeError):
            context.contract["nested"]["items"][0]["value"] = 2

    entry = publish_demo(CacheStore(tmp_path), contract=contract, validator=validate)
    contract["nested"]["items"][0]["value"] = 99
    assert entry.receipt["contract"]["nested"]["items"][0]["value"] == 1
    assert contexts[0].contract["nested"]["items"][0]["value"] == 1
    with pytest.raises(TypeError):
        entry.receipt["contract"]["nested"]["items"][0]["value"] = 2


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        ("schema", "cache-receipt/v2"),
        ("status", "pending"),
        ("extra", True),
        ("address", asdict(demo_address("another"))),
        ("contract", []),
        ("payload.path", "../outside"),
        ("payload.format", ""),
        ("payload.size", True),
        ("payload.size", -1),
        ("payload.size", 999),
        ("payload.sha256", "0" * 64),
        ("payload.extra", True),
        ("upstream_refs", {}),
        ("upstream_refs", [{}]),
    ],
)
def test_strict_receipt_validation_precedes_callback(tmp_path, field_path, value):
    """Malformed or mismatched wrappers never reach package-owned validation."""
    store = CacheStore(tmp_path)
    entry = publish_demo(store)
    rewrite_receipt(entry, field_path, value)
    calls = []

    def unexpected_callback(payload, context):
        """Record an incorrect dispatch before failing the test."""
        calls.append(context)
        raise AssertionError("invalid wrapper reached package validator")

    with pytest.raises(CacheValidationError):
        store.get(demo_address(), validator=unexpected_callback)
    assert calls == []


def test_receipt_fingerprint_is_checked(tmp_path):
    """A wrapper change cannot borrow the previous wrapper fingerprint."""
    store = CacheStore(tmp_path)
    entry = publish_demo(store)
    rewrite_receipt(entry, "contract", {"changed": True}, rehash=False)
    with pytest.raises(CacheValidationError):
        store.get(demo_address(), validator=validate_demo)


@pytest.mark.parametrize(
    "contents",
    [
        b'{"schema":"first","schema":"second"}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":1e999}',
        b"\xff",
    ],
)
def test_receipt_requires_strict_finite_json(tmp_path, contents):
    """Duplicate keys, nonfinite numbers and invalid encoding fail closed."""
    store = CacheStore(tmp_path)
    entry = publish_demo(store)
    entry.receipt_path.write_bytes(contents)
    with pytest.raises(CacheValidationError):
        store.get(demo_address(), validator=validate_demo)


def test_payload_integrity_is_checked(tmp_path):
    """Payload corruption is rejected before its package callback runs."""
    store = CacheStore(tmp_path)
    entry = publish_demo(store)
    entry.payload_paths[0].write_bytes(b'{"value":2}')
    with pytest.raises(CacheValidationError):
        store.get(demo_address(), validator=validate_json)


def test_existing_incomplete_directory_is_not_a_miss_or_overwritten(tmp_path):
    """An incomplete addressed directory is preserved as a conflicting artifact."""
    store = CacheStore(tmp_path)
    entry = publish_demo(store)
    entry.receipt_path.unlink()
    with pytest.raises(CacheValidationError):
        store.get(demo_address(), validator=validate_demo)
    with pytest.raises(CacheConflictError):
        publish_demo(store)
    assert entry.payload_paths[0].read_bytes() == b'{"value":1}'
    assert not entry.receipt_path.exists()


def test_package_validation_failure_prevents_publication(tmp_path):
    """Rejected package bytes cannot create a complete or staged cache entry."""
    root = tmp_path / "cache"
    store = CacheStore(root)
    with pytest.raises(ValueError, match="invalid demo"):
        store.put(
            demo_address(), contract={}, payload=b'{"value":2}',
            payload_format="json", validator=validate_demo,
        )
    assert not root.exists()


def test_get_runs_current_package_validator(tmp_path):
    """Storage integrity alone cannot authorize reuse under a rejecting owner."""
    store = CacheStore(tmp_path)
    store.put(
        demo_address(), contract={}, payload=b'{"value":2}',
        payload_format="json", validator=validate_json,
    )
    with pytest.raises(ValueError, match="invalid demo"):
        store.get(demo_address(), validator=validate_demo)


def test_unavailable_upstream_prevents_hit(tmp_path):
    """A complete dependent entry becomes reusable only while its inputs exist."""
    store = CacheStore(tmp_path)
    upstream = demo_address("upstream")
    store.put(
        demo_address(), contract={}, payload=b'{"value":1}',
        payload_format="json", upstream_refs=(upstream,), validator=validate_demo,
    )
    assert store.get(demo_address(), validator=validate_demo) is None
    source = publish_demo(store, upstream)
    assert store.get(demo_address(), validator=validate_demo) is not None
    source.payload_paths[0].unlink()
    assert store.get(demo_address(), validator=validate_demo) is None


def test_directory_publication_failure_leaves_only_staging(tmp_path, monkeypatch):
    """Failed publication preserves old entries and cannot expose staged data."""
    store = CacheStore(tmp_path)
    old = publish_demo(store)
    before = (old.receipt_path.read_bytes(), old.payload_paths[0].read_bytes())
    stages = []

    def fail_publish(source, destination):
        """Inject a failure after both staged files have been verified."""
        stages.append(source)
        assert (source / "payload.json").read_bytes() == b'{"value":1}'
        assert json.loads((source / "receipt.json").read_bytes())["status"] == "complete"
        raise OSError(errno.EIO, "injected publish failure")

    monkeypatch.setattr(cache_module, "_rename_no_replace", fail_publish)
    with pytest.raises(OSError, match="injected publish"):
        publish_demo(store, demo_address("two"))
    assert stages and stages[0].is_dir()
    assert store.get(demo_address("two"), validator=validate_demo) is None
    with pytest.raises(ValueError):
        demo_address(stages[0].name)
    assert (old.receipt_path.read_bytes(), old.payload_paths[0].read_bytes()) == before


def test_replace_failure_retains_old_bytes(tmp_path, monkeypatch):
    """The existing atomic receipt writer preserves old bytes on replace failure."""
    store = CacheStore(tmp_path)
    old = publish_demo(store)
    before = (old.receipt_path.read_bytes(), old.payload_paths[0].read_bytes())

    def fail_replace(source, destination):
        """Fail receipt replacement without touching either existing final file."""
        raise OSError(errno.EIO, "injected replace failure")

    monkeypatch.setattr(receipt_storage.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace"):
        write_receipt(old.receipt_path, {"replacement": True})
    with pytest.raises(OSError, match="injected replace"):
        publish_demo(store, demo_address("two"))
    assert store.get(demo_address("two"), validator=validate_demo) is None
    assert (old.receipt_path.read_bytes(), old.payload_paths[0].read_bytes()) == before


@pytest.mark.parametrize("difference", ["none", "payload", "contract", "invalid-package"])
def test_racing_winner_is_fully_verified(tmp_path, monkeypatch, difference):
    """Publication reuses only an exact, independently package-validated winner."""
    store = CacheStore(tmp_path)
    real_publish = cache_module._rename_no_replace
    winners = []

    def publish_competitor(source, destination):
        """Publish another complete directory immediately before losing the race."""
        winner = source.parent / ".winner.staging"
        winner.mkdir()
        receipt = json.loads((source / "receipt.json").read_bytes())
        payload = (source / "payload.json").read_bytes()
        if difference in {"payload", "invalid-package"}:
            payload = b'{"value":2}'
        if difference == "contract":
            receipt["contract"] = {"changed": True}
        receipt["payload"]["size"] = len(payload)
        receipt["payload"]["sha256"] = hashlib.sha256(payload).hexdigest()
        receipt["receipt_fingerprint"] = _fingerprint({
            key: value for key, value in receipt.items()
            if key != "receipt_fingerprint"
        })
        (winner / "payload.json").write_bytes(payload)
        write_receipt(winner / "receipt.json", receipt)
        real_publish(winner, destination)
        winners.append((destination, payload))
        raise FileExistsError(errno.EEXIST, "competing publication")

    monkeypatch.setattr(cache_module, "_rename_no_replace", publish_competitor)
    validator = validate_demo if difference == "invalid-package" else validate_json
    if difference == "none":
        entry = publish_demo(store, validator=validator)
        assert entry.payload_paths[0].read_bytes() == b'{"value":1}'
    else:
        with pytest.raises(CacheConflictError):
            publish_demo(store, validator=validator)
    destination, payload = winners[0]
    assert (destination / "payload.json").read_bytes() == payload


def test_native_publication_refuses_existing_directory(tmp_path):
    """The publication primitive refuses even an empty existing destination."""
    source = tmp_path / "stage"
    destination = tmp_path / "final"
    source.mkdir()
    destination.mkdir()
    (source / "payload").write_bytes(b"candidate")
    with pytest.raises(FileExistsError):
        cache_module._rename_no_replace(source, destination)
    assert (source / "payload").read_bytes() == b"candidate"
    assert list(destination.iterdir()) == []


def test_payload_and_receipt_are_fsynced_before_publish(tmp_path, monkeypatch):
    """Both staged files reach their fsync calls before directory publication."""
    real_fsync = os.fsync
    real_publish = cache_module._rename_no_replace
    syncs = []

    def record_fsync(descriptor):
        """Record successful file synchronization without replacing its behavior."""
        real_fsync(descriptor)
        syncs.append(descriptor)

    def verify_before_publish(source, destination):
        """Require both file synchronizations before publishing the directory."""
        assert len(syncs) >= 2
        real_publish(source, destination)

    monkeypatch.setattr(cache_module.os, "fsync", record_fsync)
    monkeypatch.setattr(cache_module, "_rename_no_replace", verify_before_publish)
    publish_demo(CacheStore(tmp_path))


def test_auth_is_explicitly_unsupported_without_losing_context_fields(tmp_path):
    """Task 1 retains the auth API while refusing unauthenticated substitution."""
    store = CacheStore(tmp_path)
    secret = b"private-secret"
    context = CacheValidationContext(demo_address(), "key", secret, {"a": {"b": 1}})
    assert context.auth_key == secret
    assert "private-secret" not in repr(context)
    with pytest.raises(TypeError):
        context.contract["a"]["b"] = 2
    with pytest.raises(CacheUnsupportedError, match="Task 2"):
        store.put(
            demo_address(), contract={}, payload=b'{"value":1}',
            payload_format="json", validator=validate_demo, auth_key_id="a" * 64,
        )
    entry = publish_demo(store)
    rewrite_receipt(entry, "auth_key_id", "a" * 64)
    with pytest.raises(CacheUnsupportedError, match="Task 2"):
        store.get(demo_address(), validator=validate_demo)


def test_storage_never_resolves_parameters(tmp_path, monkeypatch):
    """Storage round-trips an already calculated snapshot without owner execution."""
    schema = ParameterSchema("demo", "v1", (ParameterSpec("threshold", int, 1),))
    snapshot = schema.resolve().to_json()

    def forbidden_resolution(*args, **kwargs):
        """Fail if persistence tries to resolve or reconstruct parameter values."""
        raise AssertionError("storage resolved parameters")

    monkeypatch.setattr(ParameterSchema, "resolve", forbidden_resolution)
    monkeypatch.setattr(ParameterSchema, "capture_calculated", forbidden_resolution)
    store = CacheStore(tmp_path)
    publish_demo(store, contract={"parameters": snapshot})
    loaded = store.get(demo_address(), validator=validate_demo)
    assert _json_value(loaded.receipt["contract"]["parameters"]) == snapshot


def test_source_binding_round_trip_and_locator_update(tmp_path):
    """Only a locator changes when independently verified source facts agree."""
    store = CacheStore(tmp_path)
    original = SourceBinding(
        "scene-a", "canonical-a", "content-a", {"external": "content-b"}, "a.ifc",
    )
    assert store.get_source_binding("scene-a") is None
    assert store.put_source_binding(original) == original
    relocated = replace(original, current_locator="moved/a.ifc")
    assert store.put_source_binding(relocated) == relocated
    assert CacheStore(tmp_path).get_source_binding("scene-a") == relocated
    assert (tmp_path / "sources" / "scene-a" / "source.json").is_file()
    assert not (tmp_path / "index.json").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"canonical_source_identity": "different"},
        {"content_fingerprint": "different"},
        {"external_dependencies": {"external": "different"}},
    ],
)
def test_source_binding_refuses_changed_facts(tmp_path, changes):
    """A locator update cannot silently replace established source facts."""
    store = CacheStore(tmp_path)
    original = SourceBinding(
        "scene-a", "canonical-a", "content-a", {"external": "content-b"}, "a.ifc",
    )
    store.put_source_binding(original)
    path = tmp_path / "sources" / "scene-a" / "source.json"
    before = path.read_bytes()
    with pytest.raises(CacheConflictError):
        store.put_source_binding(replace(original, **changes))
    assert path.read_bytes() == before
