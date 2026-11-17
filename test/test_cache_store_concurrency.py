"""Exercise process-shared cache locking and catalog recovery."""

from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path
import importlib
from types import ModuleType
import time

import pytest

from features.cache_paths import CacheAddress
from features.cache_store import CacheLockTimeoutError, CacheStore

from .test_cache_store import validate_demo


def _worker_publish(root, identity, ready, counter, results):
    """Wait for the peer, then perform a real lookup-to-publish sequence."""
    store = CacheStore(Path(root))
    address = CacheAddress("scene-a", "demo", "combined", "raw", identity)
    ready.wait(20)
    with store.identity_lock(address):
        entry = store.get(address, validator=validate_demo)
        if entry is None:
            with counter.get_lock():
                counter.value += 1
            time.sleep(0.08)
            store.put(
                address, contract={}, payload=b'{"value":1}',
                payload_format="json", validator=validate_demo,
            )
            results.put("computed")
        else:
            results.put("hit")


def _join_processes(processes):
    """Join workers with a bounded wait and fail on a worker error."""
    for process in processes:
        process.join(30)
        assert not process.is_alive(), "cache worker did not finish"
        assert process.exitcode == 0


def test_same_identity_is_computed_once_across_processes(tmp_path):
    """The public identity lock covers lookup, computation and publication."""
    context = get_context("spawn")
    ready = context.Event()
    counter = context.Value("i", 0)
    results = context.Queue()
    processes = [context.Process(target=_worker_publish,
                                 args=(str(tmp_path), "same", ready, counter, results))
                 for _ in range(2)]
    for process in processes:
        process.start()
    ready.set()
    _join_processes(processes)
    observed = sorted(results.get(timeout=5) for _ in processes)
    assert observed == ["computed", "hit"]
    assert counter.value == 1
    address = CacheAddress("scene-a", "demo", "combined", "raw", "same")
    assert CacheStore(tmp_path).get(address, validator=validate_demo) is not None


def test_different_identities_remain_independent_across_processes(tmp_path):
    """Independent identities can calculate concurrently and both remain listable."""
    context = get_context("spawn")
    ready = context.Event()
    counter = context.Value("i", 0)
    results = context.Queue()
    processes = [context.Process(target=_worker_publish,
                                 args=(str(tmp_path), identity, ready, counter, results))
                 for identity in ("one", "two")]
    for process in processes:
        process.start()
    ready.set()
    _join_processes(processes)
    assert sorted(results.get(timeout=5) for _ in processes) == ["computed", "computed"]
    assert counter.value == 2
    entries = CacheStore(tmp_path).list(package_id="demo")
    assert {entry.address.identity for entry in entries} == {"one", "two"}


def test_corrupt_index_is_rebuilt_from_receipts(tmp_path):
    """The disposable index cannot hide a complete receipt-derived entry."""
    store = CacheStore(tmp_path)
    address = CacheAddress("scene-a", "demo", "combined", "raw", "one")
    store.put(address, contract={}, payload=b'{"value":1}',
              payload_format="json", validator=validate_demo)
    (tmp_path / "index.json").write_text("[]", encoding="utf-8")
    rebuilt = store.rebuild_index()
    assert rebuilt["entries"][0]["address"] == {
        "source_fingerprint": "scene-a", "package_id": "demo",
        "output_port": "combined", "layer": "raw", "identity": "one",
    }
    assert store.get(address, validator=validate_demo) is not None


def _worker_real_runner(producer, root, ready, counter, results, version=1):
    """Run one real package entry in a fresh process and count its producer call."""
    if producer == "distance":
        from features import group_distance_evidence_package as owner
        from .test_group_distance import _missing_bundle
        bundle = _missing_bundle()
        if version != 1:
            bundle = replace(bundle, clearance_policy={
                "min_left_m": .2, "min_right_m": .2, "min_total_m": .5})
        arguments = (bundle,)
        real = owner.evaluate_group_distance_package

        def wrapped(*args, **kwargs):
            """Count the actual distance package calculation before executing it."""
            with counter.get_lock():
                counter.value += 1
            time.sleep(0.08)
            return real(*args, **kwargs)

        owner.evaluate_group_distance_package = wrapped
        run = owner.run_group_distance_package
        model = Path(root) / "layout.ifc"
        options = {}
    elif producer == "free_space":
        workspace = ModuleType("concurrency_workspace")
        workspace.__path__ = [str(Path(__file__).resolve().parents[1])]
        import sys
        sys.modules.setdefault("concurrency_workspace", workspace)
        fixtures = importlib.import_module("concurrency_workspace.test.test_analysis_requests")
        owner = importlib.import_module("concurrency_workspace.adapters.free_space_evidence_package")
        _scene, _object, _request = fixtures._scene, fixtures._object, fixtures._request
        scene = _scene(_object("chair"))
        request = _request(scene)
        request = replace(request, sampling=replace(request.sampling, spacing=float(version)))
        arguments = (scene, request)
        options = {}
        real = owner.requests.execute_analysis_request

        def wrapped(*args, **kwargs):
            """Count the actual free-space request before executing it."""
            with counter.get_lock():
                counter.value += 1
            time.sleep(0.08)
            return real(*args, **kwargs)

        owner.requests.execute_analysis_request = wrapped
        run = owner.run_free_space_package
        model = Path(root) / "layout.ifc"
    else:
        workspace = ModuleType("concurrency_workspace")
        workspace.__path__ = [str(Path(__file__).resolve().parents[1])]
        import sys
        sys.modules.setdefault("concurrency_workspace", workspace)
        owner = importlib.import_module("concurrency_workspace.adapters.blender_analysis_session")
        payload_factory = importlib.import_module("concurrency_workspace.test.test_blender_analysis_session")
        _cache_payload = payload_factory._cache_payload
        payload = _cache_payload()
        payload["request"]["sampling"]["spacing"] = float(version)
        options = {}
        real = owner.requests.execute_analysis_request

        def wrapped(*args, **kwargs):
            """Count the actual Blender analysis request before executing it."""
            with counter.get_lock():
                counter.value += 1
            time.sleep(0.08)
            return real(*args, **kwargs)

        owner.requests.execute_analysis_request = wrapped
        run = owner._execute_workflow_payload
        arguments = (payload,)
        model = Path(root) / "layout.blend"
    ready.wait(20)
    try:
        result = run(*arguments, model_path=model, **options)
        reuse = result.get("cache_reuse")
        if reuse is None and isinstance(result.get("content_cache"), dict):
            reuse = result["content_cache"].get("cache_reuse")
        results.put(("ok", reuse))
    except Exception as exc:  # pragma: no cover - parent reports the child error
        results.put(("error", f"{type(exc).__name__}: {exc}"))
        raise


@pytest.mark.parametrize("producer", ["distance", "free_space", "blender"])
def test_real_runner_first_miss_calculates_once_across_processes(tmp_path, producer):
    """Each locator-aware public runner serializes its first miss across processes."""
    context = get_context("spawn")
    ready = context.Event()
    counter = context.Value("i", 0)
    results = context.Queue()
    processes = [context.Process(target=_worker_real_runner,
                                 args=(producer, str(tmp_path), ready, counter, results))
                 for _ in range(2)]
    for process in processes:
        process.start()
    ready.set()
    _join_processes(processes)
    observed = [results.get(timeout=5) for _ in processes]
    assert all(status == "ok" for status, _ in observed), observed
    assert sorted(value for _, value in observed) == ["computed", "exact_hit"]
    assert counter.value == 1


@pytest.mark.parametrize("producer", ["distance", "free_space", "blender"])
def test_real_runner_different_versions_each_compute_and_remain_in_catalog(tmp_path, producer):
    """Different request versions remain independent at the real runner boundary."""
    context = get_context("spawn")
    ready, counter, results = context.Event(), context.Value("i", 0), context.Queue()
    processes = [context.Process(target=_worker_real_runner,
                                 args=(producer, str(tmp_path), ready, counter, results, version))
                 for version in (1, 2)]
    for process in processes:
        process.start()
    ready.set()
    _join_processes(processes)
    assert [results.get(timeout=5) for _ in processes] == [("ok", "computed")] * 2
    assert counter.value == 2
    store = CacheStore(tmp_path / "layout.order_analyzer")
    entries = store.list()
    assert len(entries) == 2
    assert len({entry.address.identity for entry in entries}) == 2
    assert len({entry.address.source_fingerprint for entry in entries}) == 1
    assert len(store.rebuild_index()["entries"]) == 2


def _worker_hold_lock(root, acquired):
    """Hold the OS lock until the parent simulates an interrupted worker."""
    address = CacheAddress("scene-a", "demo", "combined", "raw", "crashed")
    with CacheStore(Path(root)).identity_lock(address):
        acquired.set()
        time.sleep(30)


def test_crashed_holder_releases_os_lock_and_timeout_is_typed(tmp_path):
    """OS process exit releases ownership without a stale lock-file heuristic."""
    context = get_context("spawn")
    acquired = context.Event()
    holder = context.Process(target=_worker_hold_lock, args=(str(tmp_path), acquired))
    holder.start()
    address = CacheAddress("scene-a", "demo", "combined", "raw", "crashed")
    try:
        assert acquired.wait(15)
        with pytest.raises(CacheLockTimeoutError):
            with CacheStore(tmp_path).identity_lock(address, timeout=.05):
                pytest.fail("live holder lock was bypassed")
    finally:
        holder.terminate()
        holder.join(5)
    assert not holder.is_alive()
    with CacheStore(tmp_path).identity_lock(address, timeout=2):
        CacheStore(tmp_path).put(address, contract={}, payload=b'{"value":1}',
                                 payload_format="json", validator=validate_demo)


def test_identity_lock_is_reentrant_across_store_instances(tmp_path):
    """A runner can call another Store instance while owning the same address lock."""
    address = CacheAddress("scene-a", "demo", "combined", "raw", "nested")
    with CacheStore(tmp_path).identity_lock(address, timeout=.1):
        with CacheStore(tmp_path).identity_lock(address, timeout=.1):
            CacheStore(tmp_path).put(address, contract={}, payload=b'{"value":1}',
                                     payload_format="json", validator=validate_demo)
