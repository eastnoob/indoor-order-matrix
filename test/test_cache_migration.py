"""Exercise byte-preserving sidecar migration and authentication domains."""

from dataclasses import replace
import hashlib
import hmac
import importlib
import json
from multiprocessing import get_context
from pathlib import Path
import shutil
import sys
import traceback
from types import ModuleType

import pytest

from test.test_evidence_package_output import _package_context

from features.cache_paths import CacheAddress, SourceBinding
from features.cache_store import CacheStore

from .test_cache_store import validate_demo


FIXTURES = Path(__file__).resolve().parent / "fixtures/cache_migration/pre_parameter_sidecar"


def _address(identity="one"):
    """Create one stable migration address."""
    return CacheAddress("scene-a", "demo", "combined", "raw", identity)


def test_migration_preserves_payload_and_retains_source(tmp_path):
    """Migration copies verified bytes and leaves a rollback source in place."""
    source_root, destination_root = tmp_path / "old", tmp_path / "new"
    source = CacheStore(source_root)
    address = _address()
    source.put_source_binding(SourceBinding(
        "scene-a", "canonical-a", "content-a", {}, "old/layout.ifc",
    ))
    prior = source.put(address, contract={"recipe": "v1"}, payload=b'{"value":1}',
                       payload_format="json", validator=validate_demo)
    prior_receipt = prior.receipt_path.read_bytes()
    prior_payload = prior.payload_paths[0].read_bytes()
    report = source.migrate_to(destination_root, validators={"demo:raw": validate_demo})
    copied = CacheStore(destination_root).get(address, validator=validate_demo)
    assert report.copied == (address,)
    assert report.failed == ()
    assert report.old_directory_retained is True
    assert copied is not None and copied.reuse_origin == "migrated"
    assert copied.receipt_path.read_bytes() == prior_receipt
    assert copied.payload_paths[0].read_bytes() == prior_payload
    assert CacheStore(destination_root).get_source_binding("scene-a").current_locator == "old/layout.ifc"
    assert prior.receipt_path.exists() and prior.payload_paths[0].exists()
    manifest = json.loads((destination_root / "manifest.json").read_bytes())
    assert manifest["cache_format_version"] == "cache-receipt/v1"
    assert manifest["producer_versions"]["cache_store"] == "1"
    assert manifest["sources"]["scene-a"]["content_fingerprint"] == "content-a"
    assert manifest["migrations"][-1]["source"] == str(source_root)
    assert manifest["migrations"][-1]["status"] == "complete"


def test_repeat_migration_reuses_exact_destination_bytes(tmp_path):
    """A second migration does not replace an identical complete destination."""
    source = CacheStore(tmp_path / "old")
    address = _address()
    source.put(address, contract={}, payload=b'{"value":1}',
               payload_format="json", validator=validate_demo)
    destination = tmp_path / "new"
    first = source.migrate_to(destination, validators={"demo:raw": validate_demo})
    before = (CacheStore(destination).get(address, validator=validate_demo).receipt_path.read_bytes(),
              CacheStore(destination).get(address, validator=validate_demo).payload_paths[0].read_bytes())
    second = source.migrate_to(destination, validators={"demo:raw": validate_demo})
    assert first.copied == (address,)
    assert second.reused == (address,)
    loaded = CacheStore(destination).get(address, validator=validate_demo)
    assert (loaded.receipt_path.read_bytes(), loaded.payload_paths[0].read_bytes()) == before


def test_authentication_key_is_copied_with_entry_and_verified_after_restart(tmp_path):
    """Migrated authenticated bytes select their original key domain."""
    secret = b"migration-secret"

    def validate_authenticated(payload, context):
        """Require the owner-visible authentication secret and payload bytes."""
        if context.auth_key != secret or payload != b"authenticated":
            raise ValueError("authenticated payload rejected")

    source = CacheStore(tmp_path / "old")
    key_id = source.register_auth_key(secret)
    address = _address("auth")
    source.put(address, contract={}, payload=b"authenticated", payload_format="bytes",
               validator=validate_authenticated, auth_key_id=key_id)
    destination = tmp_path / "new"
    report = source.migrate_to(destination, validators={"demo:raw": validate_authenticated})
    assert report.auth_material_copied is True
    loaded = CacheStore(destination).get(address, validator=validate_authenticated)
    assert loaded is not None and loaded.reuse_origin == "migrated"
    assert (destination / "auth" / key_id / ".free_space_cache_key").read_bytes() == secret


@pytest.mark.parametrize("legacy_destination", [False, True])
def test_migration_keeps_destination_default_authentication_domain(tmp_path, legacy_destination):
    """Imported credentials cannot replace a modern or legacy destination default."""
    source = CacheStore(tmp_path / "old")
    source.register_auth_key(b"imported-secret")
    destination = tmp_path / "new"
    if legacy_destination:
        destination.mkdir()
        (destination / ".free_space_cache_key").write_bytes(b"legacy-destination-secret")
        original = b"legacy-destination-secret"
    else:
        original = CacheStore(destination).get_or_create_auth_key()
    source.migrate_to(destination, validators={})
    assert CacheStore(destination).get_or_create_auth_key() == original
    assert CacheStore(destination).get_or_create_auth_key() == original


def test_corrupt_source_entry_is_reported_without_erasing_other_entries(tmp_path):
    """One damaged entry cannot prevent an independent valid entry from migrating."""
    source = CacheStore(tmp_path / "old")
    good = source.put(_address("good"), contract={}, payload=b'{"value":1}',
                      payload_format="json", validator=validate_demo)
    bad = source.put(_address("bad"), contract={}, payload=b'{"value":1}',
                     payload_format="json", validator=validate_demo)
    bad.payload_paths[0].write_bytes(b"broken")
    destination = tmp_path / "new"
    report = source.migrate_to(destination, validators={"demo:raw": validate_demo})
    assert good.address in report.copied
    assert any('bad' in label for label, _ in report.failed)
    assert CacheStore(destination).get(good.address, validator=validate_demo) is not None
    assert good.receipt_path.exists()
    assert report.old_directory_retained is True


@pytest.mark.parametrize("rejection", [ValueError, TypeError])
def test_owner_rejection_preserves_source_and_migrates_independent_entries(tmp_path, rejection):
    """An owner-rejected recipe cannot abort unrelated valid cache migration."""
    source = CacheStore(tmp_path / "old")
    entries = [source.put(_address(identity), contract={}, payload=b'{"value":1}',
                          payload_format="json", validator=validate_demo)
               for identity in ("a-rejected", "z-valid")]
    original = {path: path.read_bytes() for entry in entries
                for path in (entry.receipt_path, *entry.payload_paths)}

    def validate_current(payload, context):
        """Reject a historical recipe while admitting the independent current entry."""
        validate_demo(payload, context)
        if context.address.identity == "a-rejected":
            raise rejection("recipe is unavailable")

    destination = tmp_path / "new"
    report = source.migrate_to(destination, validators={"demo:raw": validate_current})
    assert report.copied == (entries[1].address,)
    assert len(report.failed) == 1 and "a-rejected" in report.failed[0][0]
    assert report.quarantined == ()
    assert CacheStore(destination).get(entries[1].address, validator=validate_current) is not None
    assert CacheStore(destination).get(entries[0].address, validator=validate_demo) is None
    assert all(path.read_bytes() == payload for path, payload in original.items())


def test_exact_delete_is_source_scoped_and_preserves_signed_orphan_bytes(tmp_path):
    """Deleting one source version cannot delete its namesake or rewrite dependents."""
    store = CacheStore(tmp_path)
    upstream = _address("shared")
    independent = replace(upstream, source_fingerprint="scene-b")
    downstream = replace(_address("derived"), layer="processed")
    for address in (upstream, independent):
        store.put(address, contract={}, payload=b'{"value":1}', payload_format="json",
                  validator=validate_demo)
    secret = b"signed-downstream"
    body = b'{"derived":1}'
    payload = hmac.digest(secret, body, "sha256") + b"\n" + body

    def validate_signed(saved, context):
        """Authenticate the exact opaque downstream payload through its own key domain."""
        tag, saved_body = saved.rsplit(b"\n", 1)
        if context.auth_key != secret or not hmac.compare_digest(
                tag, hmac.digest(context.auth_key, saved_body, "sha256")):
            raise ValueError("invalid downstream authentication")

    entry = store.put(downstream, contract={}, payload=payload, payload_format="bytes",
                      upstream_refs=(upstream,), validator=validate_signed,
                      auth_key_id=store.register_auth_key(secret))
    original = (entry.receipt_path.read_bytes(), entry.payload_paths[0].read_bytes())
    assert store.delete_exact(upstream) is True
    assert store.delete_exact(upstream) is False
    assert store.get(independent, validator=validate_demo) is not None
    assert store.get(downstream, validator=validate_signed) is None
    assert {entry.address: entry.status for entry in store.list()}[downstream] == "orphaned"
    assert (entry.receipt_path.read_bytes(), entry.payload_paths[0].read_bytes()) == original


def test_closed_runs_settings_and_bound_route_checkpoints_migrate(tmp_path, monkeypatch):
    """Migration retains terminal evidence and resumes exact policy checkpoints after undo."""
    from features import group_distance_repair as repair
    from .test_group_distance_route_repair import _checkpoint_fixture

    source_root, destination = tmp_path / "old", tmp_path / "new"
    checkpoints = source_root / "runs/closed/checkpoints"
    bundle, baseline, first_policy = _checkpoint_fixture()
    second_policy = {**first_policy, "min_total_m": .8}
    for policy in (first_policy, second_policy):
        result = repair.global_repair_result(bundle, baseline, policy, checkpoint_dir=checkpoints)
        assert result["quality_counts"]["exact_route_verified"] == 1
    (checkpoints.parent / "run.json").write_text(
        json.dumps({"schema": "cache-run/v1", "state": "complete"}), encoding="utf-8")
    (checkpoints.parent / "stdout.log").write_bytes(b"completed route search")
    scratch = checkpoints.parent / "scratch"
    scratch.mkdir()
    (scratch / "partial").write_bytes(b"not reusable")
    active = source_root / "runs/active"
    active.mkdir()
    (active / "run.json").write_text(
        json.dumps({"schema": "cache-run/v1", "state": "running"}), encoding="utf-8")
    for root, value in ((source_root, b"source settings"), (destination, b"destination settings")):
        (root / "settings").mkdir(parents=True)
        (root / "settings/default.json").write_bytes(value)
    original = {path.relative_to(source_root): path.read_bytes()
                for path in source_root.rglob("*") if path.is_file()}
    report = CacheStore(source_root).migrate_to(destination, validators={})
    assert len(report.failed) == 1 and report.failed[0][0] == str(Path("runs") / "active")
    assert (destination / "settings/default.json").read_bytes() == b"destination settings"
    assert [path.read_bytes() for path in (destination / "settings").glob("imported-*/default.json")] == [b"source settings"]
    assert not (destination / "runs/active").exists()
    assert not (destination / "runs/closed/scratch").exists()
    assert (destination / "runs/closed/stdout.log").read_bytes() == b"completed route search"
    assert all((source_root / relative).read_bytes() == value for relative, value in original.items())

    def forbid_search(*args, **kwargs):
        """Prove the migrated checkpoint suppresses the actual current route search."""
        raise AssertionError("checkpoint search sentinel")

    monkeypatch.setattr(repair, "_global_source_search", forbid_search)
    for policy in (first_policy, second_policy, first_policy):
        result = repair.global_repair_result(bundle, baseline, policy,
                                            checkpoint_dir=destination / "runs/closed/checkpoints")
        assert result["quality_counts"]["exact_route_verified"] == 1
    with pytest.raises(AssertionError, match="checkpoint search sentinel"):
        repair.global_repair_result(bundle, baseline, first_policy,
                                   checkpoint_dir=tmp_path / "empty-checkpoints")
    assert {path.name: path.read_bytes() for path in checkpoints.glob("*.json")} == {
        path.name: path.read_bytes() for path in (destination / "runs/closed/checkpoints").glob("*.json")}


def _migration_modules():
    """Load independently constructed scene fixtures under one stable package namespace."""
    workspace = ModuleType("migration_workspace")
    workspace.__path__ = [str(Path(__file__).resolve().parents[1])]
    sys.modules.setdefault("migration_workspace", workspace)
    return (
        importlib.import_module("migration_workspace.adapters.free_space_evidence_package"),
        importlib.import_module("migration_workspace.adapters.blender_analysis_session"),
        importlib.import_module("migration_workspace.test.test_analysis_requests"),
        importlib.import_module("migration_workspace.test.test_blender_analysis_session"),
    )


def _forbid_migration_calculation(*args, **kwargs):
    """Expose a cache miss at the actual producer or numerical executor boundary."""
    raise AssertionError("migration calculation sentinel")


def _migration_processor(value, *, forbidden=False):
    """Build two current numerical recipes independently of saved receipt metadata."""
    from features import field_core as core
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec
    from .test_evidence_package_lifecycle import _processor

    base = _processor()

    def transform(raw, parameters):
        """Scale the existing tiny real processor output by its declared effective value."""
        return tuple(replace(item, observation=item.observation * parameters["value"])
                     for item in base.function(raw, parameters))

    schema = ParameterSchema("group-axis-potential", "migration-test/1",
                             (ParameterSpec("value", int, 1, minimum=1, maximum=2),))
    return core.EvidenceOutputProcessor(
        "migration-values", "1", _forbid_migration_calculation if forbidden else transform,
        {"value": value}, parameter_schema=schema,
    )


def _migration_request(family, root, value, modules, *, forbidden=False, original=False):
    """Invoke the ordinary owner runner using fresh fixture inputs and current recipes."""
    free_space, blender, fixtures, blender_fixtures = modules
    if family in {"raw", "processed"}:
        from features import group_axis_potential_field as potential
        from .test_evidence_package_lifecycle import _potential_sources, _processor
        processor = (_processor(function=_forbid_migration_calculation if forbidden else None)
                     if original and family == "processed" else
                     None if original else _migration_processor(value, forbidden=forbidden))
        return potential.run_group_axis_potential_package(
            _potential_sources(), temporary_cache_root=root, output_processor=processor,
         analysis_context=_package_context())
    if family == "auth_free_space":
        scene = fixtures._scene(fixtures._object("chair"))
        request = fixtures._request(scene)
        request = replace(request, sampling=replace(request.sampling, spacing=float(value)))
        return free_space.run_free_space_package(scene, request, temporary_cache_root=root)
    payload = blender_fixtures._cache_payload()
    payload["request"]["sampling"]["spacing"] = float(value)
    return blender._execute_workflow_payload(payload, temporary_cache_root=root)


def _migration_validators(family, modules):
    """Use owner decoders and independently supplied current contracts while copying bytes."""
    from features import evidence_package_storage as storage
    from features import group_axis_potential_field as potential
    from features.evidence_package_parameters import ParameterSnapshot
    from .test_evidence_package_lifecycle import _potential_sources, _processor

    free_space, blender, fixtures, _ = modules
    sources = _potential_sources()
    contract = potential.build_group_axis_potential_package_contract(sources)
    snapshot = ParameterSnapshot.from_json(contract["parameter_snapshot"])
    producer = potential.build_group_axis_potential_package()

    def reconstruct(receipt, wanted):
        """Attest the owner defaults only after the saved contract passes the normal reader."""
        return storage._typed_contract_from_snapshot(receipt["contract"], snapshot)

    def validate_raw(payload, context):
        """Reject foreign raw publications instead of trusting their storage checksum alone."""
        lookup = storage.load_raw_bytes(
            payload, cache_key=context.address.identity, contract=contract,
            package=producer, legacy_adopter=reconstruct,
        )
        if lookup is None or tuple(lookup.raw_output.source_envelopes) != sources:
            raise ValueError("migration raw source binding rejected")

    def validate_processed(payload, context):
        """Bind every copied processor version to the retained raw identity and explicit recipe."""
        saved = json.loads(payload)
        raw = __import__("features.field_core", fromlist=["deserialize_evidence_package_output"])
        raw_output = raw.deserialize_evidence_package_output(json.loads(
            (FIXTURES / "raw_processed/12a42760a9d8c2a9e021ba17505ba11fa4d816f2ef92c20339cd0d0b1260a283.json")
            .read_bytes())["raw_output"])
        processor = (_processor() if saved["processor_id"] == "lifecycle-test" else
                     _migration_processor(saved["parameters"]["value"]))
        if storage.load_processed_bytes(
                payload, raw_output=raw_output, processor=processor,
                legacy_processed_adopter=storage.reconstruct_legacy_processed_snapshot) is None:
            raise ValueError("migration processed recipe rejected")

    def validate_authenticated(payload, context):
        """Check HMAC, independent geometry/request keys and reviewed numerical compatibility."""
        receipt = free_space.wire.load_json(payload.decode("utf-8"))
        document = receipt["document"]
        scene = fixtures._scene(fixtures._object("chair"))
        value = document["tables"]["snapshot"]["request"]["sampling"]["spacing"]
        if value not in {1.0, 2.0}:
            raise ValueError("migration request value rejected")
        request = fixtures._request(scene)
        request = replace(request, sampling=replace(request.sampling, spacing=value))
        binding = free_space._free_space_source_binding(scene, model_path=None, root=Path("."))
        world = {**scene.context.world_coordinate_system, "ifc_source_identity": binding.canonical_source_identity}
        portable = replace(scene, context=replace(scene.context, world_coordinate_system=world))
        keys = {free_space.free_space_cache_key(scene, request),
                free_space.free_space_cache_key(portable, request),
                free_space._legacy_free_space_cache_key(scene, request)}
        if context.address.identity not in keys:
            raise ValueError("migration factual key rejected")
        versions = document["backend_versions"]
        if (versions != free_space.requests._backend_versions()
                and free_space.requests.legacy_backend_compatibility(versions) is None):
            raise ValueError("migration numerical backend rejected")
        if free_space._read_cache_entry_bytes(
                payload, context.address.identity, context.auth_key,
                expected_parameter_snapshot=free_space.package.build_free_space_parameter_snapshot(request.to_dict()),
                legacy_adopter=free_space._reconstruct_legacy_free_space_contract) is None:
            raise ValueError("migration authenticated document rejected")

    def validate_blender(payload, context):
        """Retain exact wire origin references and the reviewed implementation profile."""
        document = blender.wire.load_json(payload.decode("utf-8"))
        versions = document["backend_versions"]
        if (versions != blender.requests._backend_versions()
                and blender.requests.legacy_backend_compatibility(versions) is None):
            raise ValueError("migration Blender backend rejected")
        blender._validate_cached_result_bytes(payload, content_key=context.address.identity, versions=versions)

    if family in {"raw", "processed"}:
        return {"group-axis-potential:raw": validate_raw,
                "group-axis-potential:processed": validate_processed}
    return {"free-space:raw": validate_authenticated} if family == "auth_free_space" else {
        "blender-analysis:raw": validate_blender,
    }


def _migration_process(stage, family, source_root, destination_root, results):
    """Import in P and prove ordinary runner reuse in independent Q and R interpreters."""
    try:
        source, destination = Path(source_root), Path(destination_root)
        modules = _migration_modules()
        free_space, blender, _, _ = modules
        from features import group_axis_potential_field as potential
        if stage == "P":
            source.mkdir(parents=True, exist_ok=True)
            manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
            selected = ({"raw", "processed"} if family == "processed" else
                        {"raw"} if family == "raw" else
                        {"authenticated_free_space"} if family == "auth_free_space" else {"blender_wire"})
            for item in manifest["families"]:
                if item["family"] in selected:
                    fixture = Path(__file__).resolve().parents[1] / item["relative_path"]
                    shutil.copyfile(fixture, source / fixture.name)
                    if item["family"] == "authenticated_free_space":
                        shutil.copyfile(fixture.parent / ".free_space_cache_key", source / ".free_space_cache_key")
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbid_migration_calculation)
                patch.setattr(free_space.requests, "execute_analysis_request", _forbid_migration_calculation)
                patch.setattr(blender.requests, "execute_analysis_request", _forbid_migration_calculation)
                imported = _migration_request(family, source, 1, modules, forbidden=True, original=True)
                assert imported.get("cache_hit", imported.get("content_cache", {}).get("hit")) is True
            for value in (1, 2):
                _migration_request(family, source, value, modules)
            destination_store = CacheStore(destination)
            destination_secret = destination_store.get_or_create_auth_key()
            destination_key = destination_store.register_auth_key(destination_secret)
            destination_store.put(
                CacheAddress("destination-source", "demo", "combined", "raw", "original-auth"),
                contract={}, payload=b'{"value":1}', payload_format="json",
                validator=validate_demo, auth_key_id=destination_key,
            )
            report = CacheStore(source).migrate_to(destination, validators=_migration_validators(family, modules))
            assert report.failed == (), report.failed
            assert report.copied
            results.put({"stage": stage, "copied": len(report.copied), "retained": report.old_directory_retained})
            return
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbid_migration_calculation)
            patch.setattr(free_space.requests, "execute_analysis_request", _forbid_migration_calculation)
            patch.setattr(blender.requests, "execute_analysis_request", _forbid_migration_calculation)
            original = _migration_request(family, destination, 1, modules, forbidden=True, original=True)
            observed = []
            for value in (1, 2, 1):
                result = _migration_request(family, destination, value, modules, forbidden=True)
                if family == "blender_wire":
                    assert result["content_cache"]["hit"] is True
                    assert result["content_cache"]["cache_reuse"] == "migrated_reuse"
                else:
                    assert result["cache_hit"] is True
                    assert result["cache_status"]["freshness"] == "fresh"
                    assert result["cache_reuse"] == "migrated_reuse"
                    if family in {"raw", "processed"}:
                        assert result["processed_output"].error_code is None
                        assert result["processed_output"].outputs[0].observation == value * 0.25
                observed.append(value)
            with pytest.raises(AssertionError, match="migration calculation sentinel"):
                _migration_request(family, destination.parent / (stage + "-empty"), 1, modules, forbidden=True)
            if family in {"auth_free_space", "blender_wire"}:
                current = free_space.requests._backend_versions()
                for section, name in (("packages", "numpy"), ("implementations", "analysis_requests")):
                    changed = json.loads(json.dumps(current))
                    changed[section][name] = "unreviewed-numerical-or-implementation-version"

                    def unknown_versions():
                        """Expose a genuine unknown dependency instead of the reviewed current stack."""
                        return changed

                    with pytest.MonkeyPatch.context() as drift:
                        drift.setattr(free_space.requests, "_backend_versions", unknown_versions)
                        with pytest.raises(AssertionError, match="migration calculation sentinel"):
                            _migration_request(family, destination, 1, modules, forbidden=True)
            store = CacheStore(destination)
            entries = store.list()
            payloads = {entry.address.identity: hashlib.sha256(entry.payload_paths[0].read_bytes()).hexdigest()
                        for entry in entries}
            default = store.get_or_create_auth_key()

            def validate_existing(payload, context):
                """Prove that migration retained the destination's original authentication domain."""
                validate_demo(payload, context)
                if context.auth_key != default:
                    raise ValueError("destination auth domain changed")

            assert store.get(
                CacheAddress("destination-source", "demo", "combined", "raw", "original-auth"),
                validator=validate_existing,
            ) is not None
            if family == "auth_free_space":
                assert len(tuple((destination / "auth").iterdir())) == 2
            if stage == "Q":
                (destination / "index.json").write_text("[]", encoding="utf-8")
                store.rebuild_index()
            origin = (original["content_cache"]["origin_result_ref"] if family == "blender_wire" else
                      original["cache_status"]["reuse_origin"])
            if family == "processed":
                origin = {"raw": origin, "processed": original["cache_status"]["processed_reuse_origin"]}
            results.put({"stage": stage, "observed": observed, "payloads": payloads,
                         "origin": free_space.wire.plain(origin)})
    except BaseException:
        results.put({"stage": stage, "error": traceback.format_exc()})
        raise


@pytest.mark.parametrize("family", ["raw", "processed", "auth_free_space", "blender_wire"])
def test_migrated_legacy_runner_reuse_survives_process_restart(tmp_path, family):
    """Pinned pre-A bytes survive import, two restarts, index rebuilding and parameter undo."""
    original = {path: path.read_bytes() for path in FIXTURES.rglob("*") if path.is_file()}
    manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
    by_family = {item["family"]: item for item in manifest["families"]}
    baseline = by_family["authenticated_free_space" if family == "auth_free_space" else family]
    context = get_context("spawn")
    outcomes = []
    for stage in ("P", "Q", "R"):
        results = context.Queue()
        process = context.Process(target=_migration_process,
                                  args=(stage, family, str(tmp_path / "old"), str(tmp_path / "new"), results))
        process.start()
        process.join(45)
        if process.is_alive():
            process.terminate()
            process.join(5)
            pytest.fail(f"migration process {stage} timed out")
        outcome = results.get(timeout=5)
        assert "error" not in outcome, outcome.get("error")
        assert process.exitcode == 0
        outcomes.append(outcome)
    for outcome in outcomes[1:]:
        assert outcome["payloads"][baseline["key"]] == baseline["sha256"]
        assert outcome["observed"] == [1, 2, 1]
    assert outcomes[1]["payloads"] == outcomes[2]["payloads"]
    assert outcomes[1]["origin"] == outcomes[2]["origin"]
    if family == "processed":
        assert outcomes[1]["origin"]["processed"]["origin_processing_identity"] == baseline["key"]
        assert outcomes[1]["origin"]["raw"]["origin_cache_key"] == by_family["raw"]["key"]
    elif family == "blender_wire":
        assert outcomes[1]["origin"]["result_id"] == baseline["source_bindings"]["result_id"]
    else:
        assert outcomes[1]["origin"]["origin_cache_key"] == baseline["key"]
    assert hashlib.sha256((tmp_path / "old" / Path(baseline["relative_path"]).name).read_bytes()).hexdigest() == baseline["sha256"]
    assert {path: path.read_bytes() for path in original} == original
