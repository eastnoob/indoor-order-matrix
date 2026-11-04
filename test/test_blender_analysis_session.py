"""B4 reducer identity and exact mesh handoff contracts."""

from dataclasses import replace

import pytest

from ..adapters.bonsai_live import load_bonsai_capture, StructuralContext
from ..adapters.blender_analysis_session import evaluate_domain_request
from ..features._analysis_domain_handoff import domain_handoff
from .test_analysis_requests import _plane, _scene
from .test_bonsai_live import capture


def _compact_run(*, mode="whole_height_projection", revision=1, domain_id="room", project="project-A", domain_source=None):
    """Run real fixture geometry with independently selectable consumer identities."""
    from .test_analysis_requests import _request, _missing, _proxy_scene
    from ..features.analysis_requests import execute_analysis_request, GeometryQuery
    scene = _proxy_scene()
    scene = replace(scene, context=replace(scene.context, analysis_plane=_plane(revision=revision),
        world_coordinate_system={"project_global_id": project, "ifc_source_identity": project + ".ifc"}),
        analysis_domain=replace(scene.analysis_domain, id=domain_id, source_id=domain_source),
        source_objects=scene.source_objects + (_missing("unresolved-C")[0],))
    query = GeometryQuery(mode, world_z_m=0 if mode == "exact_world_xy_section" else None)
    return execute_analysis_request(scene, _request(scene, geometry_query=query))


def _compact_document(**changes):
    """Serialize a real run without inventing FieldSample.to_dict."""
    from ..adapters import blender_analysis_session as service
    run = _compact_run(**changes)
    document = service.serialize_analysis_result(run, job_id="job-A", plane_uuid=run.snapshot.request.plane.identity,
        plane_revision=run.snapshot.request.plane.revision, domain_request_id="domain-request-A", domain_session_revision=2)
    return run, document


def _cache_payload():
    """Build a real data-only free-space envelope with exact test-domain geometry."""
    from .test_analysis_requests import _request
    scene = _scene()
    return {"kind": "free_space_run", "job_binding": {"job_id": "cache-first",
        "domain_request_id": "domain-first", "domain_session_revision": 1},
        "canonical_capture": capture("wall").to_dict(), "request": _request(scene).to_dict(),
        "domain_geometries": [scene.geometries[0].to_dict()], "support_binding": None, "legacy_bindings": []}


def test_disk_cache_hit_skips_all_generators_and_republishes_current_revision(tmp_path, monkeypatch):
    """A fresh call restores disk content before projection and refreshes current identity."""
    from ..adapters import blender_analysis_session as service
    from ..features import analysis_requests, geometry_views, free_space_field
    payload = _cache_payload()
    counters = {}
    targets = ((service, "_project_authored"), (geometry_views, "plan_projection"),
        (analysis_requests, "execute_analysis_request"), (free_space_field, "FreeSpaceField"),
        (service, "build_display_fragments"))
    def counted(name, function):
        """Record actual first-miss generation rather than simulating a hit flag."""
        def wrapper(*args, **kwargs):
            """Delegate unchanged arguments and count this actual generator call."""
            counters[name] = counters.get(name, 0) + 1
            return function(*args, **kwargs)
        return wrapper
    for module, name in targets:
        monkeypatch.setattr(module, name, counted(name, getattr(module, name)))
    first = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert all(counters.get(name, 0) > 0 for _, name in targets)
    cache_path, = tmp_path.glob("*.json")
    original_bytes = cache_path.read_bytes()
    def forbidden(*_args, **_kwargs):
        """A cache hit must never activate, project, calculate or rebuild display geometry."""
        pytest.fail("cache hit reached a generator")
    for module, name in targets:
        monkeypatch.setattr(module, name, forbidden)
    payload["job_binding"].update(job_id="cache-current", domain_request_id="domain-current", domain_session_revision=7)
    payload["request"]["request_id"] = "request-current"
    payload["request"]["plane"].update(revision=9, name="renamed display plane")
    current = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert current["content_cache"]["hit"] is True and first["content_cache"]["hit"] is False
    assert cache_path.read_bytes() == original_bytes
    first_ref = service.list_analysis_results([first])[0].ref
    current_ref = service.list_analysis_results([current])[0].ref
    assert current_ref != first_ref
    assert current["content_cache"]["origin_result_ref"] == {"kind": first_ref.kind,
        "result_id": first_ref.result_id, "digest": first_ref.digest}
    assert current["plane_revision"] == 9 and current["identity"]["domain_request_id"] == "domain-current"
    assert current["identity"]["domain_session_revision"] == 7
    assert current["tables"]["snapshot"]["request"] == payload["request"]
    assert current["semantic_key"] != first["semantic_key"]
    for row in range(4):
        for column in range(4):
            old = service.reconstruct_field_sample(first, row=row, column=column)
            new = service.reconstruct_field_sample(current, row=row, column=column)
            assert (new.value, new.status, new.source_ids, new.explanation) == (
                old.value, old.status, old.source_ids, old.explanation)
            assert new.query.plane["revision"] == 9 and new.query.frame.endswith(":9")
            assert new.query.revision == current["semantic_key"]
            assert new.support["plane"] == new.query.plane and new.support["frame"] == new.query.frame
            assert new.provenance["query_revision"] == current["semantic_key"]
            assert new.provenance["projected_domain_participation"] == old.provenance["projected_domain_participation"]
    observation = {"digest": current["digest"], "binding": current["binding"], "verified": True}
    assert service.open_analysis_result([current], result_ref=current_ref,
        context=_read_context(current, require_current=True, current_observation=observation)).freshness == "current"
    with pytest.raises(ValueError, match="independently verified"):
        service.open_analysis_result([first], result_ref=first_ref,
            context=_read_context(first, require_current=True, current_observation=observation))


def test_disk_cache_restored_plane_pose_hits_after_an_intermediate_miss(tmp_path):
    """A geometric undo can reuse original content despite a higher audit revision."""
    from ..adapters import blender_analysis_session as service
    payload = _cache_payload()
    first = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    payload["request"]["plane"].update(origin=[0, 0, 1], revision=2)
    payload["job_binding"]["job_id"] = "changed-pose"
    moved = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert moved["content_cache"]["hit"] is False
    payload["request"]["plane"].update(origin=[0, 0, 0], revision=3)
    payload["job_binding"]["job_id"] = "restored-pose"
    restored = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert restored["content_cache"]["hit"] is True
    assert restored["content_cache"]["content_key"] == first["content_cache"]["content_key"]
    assert len(list(tmp_path.glob("*.json"))) == 2


@pytest.mark.parametrize("damage", ["missing", "json", "digest", "version", "content", "backend"])
def test_disk_cache_invalid_entry_recomputes(tmp_path, damage):
    """A content path alone never authenticates damaged or incompatible cached data."""
    from ..adapters import blender_analysis_session as service
    payload = _cache_payload()
    service._execute_workflow_payload(payload, cache_directory=tmp_path)
    path, = tmp_path.glob("*.json")
    if damage == "missing":
        path.unlink()
    elif damage == "json":
        path.write_text('{"ambiguous":1,"ambiguous":2}', encoding="utf-8")
    else:
        data = service.wire.load_json(path.read_text(encoding="utf-8"))
        if damage == "digest":
            data["digest"] = "0" * 64
        elif damage == "version":
            data["cache_entry"]["version"] = 999
        elif damage == "content":
            data["cache_entry"]["content_key"] = "another-content"
        else:
            data["backend_versions"]["packages"]["numpy"] = "old-version"
        if damage != "digest":
            data["digest"] = service.wire.document_digest(data)
        path.write_text(service.wire.canonical_json(data), encoding="utf-8")
    payload["job_binding"]["job_id"] = "recomputed"
    result = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert result["content_cache"]["hit"] is False
    service.wire.validate_document(service.wire.load_json(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("change", ["source", "source_mesh", "domain_mesh", "domain_hole", "members",
    "plane", "basis", "band", "grid", "rules", "tolerance", "containment", "legacy", "scope",
    "confirmation", "support", "schema", "algorithm", "backend", "implementation", "cache_version"])
def test_disk_cache_content_changes_miss(tmp_path, monkeypatch, change):
    """Physical, scope, selection, request and implementation inputs all invalidate reuse."""
    from ..adapters import blender_analysis_session as service
    from ..features import analysis_requests
    payload = _cache_payload()
    first = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    row = payload["canonical_capture"]["records"][0]
    if change == "source":
        row["ifc_class"] = "IfcFurniture"
    elif change == "source_mesh":
        row["mesh"]["vertices"][0][0] += .01
    elif change == "domain_mesh":
        payload["domain_geometries"][0]["vertices"][0][0] += .01
    elif change == "domain_hole":
        scene = _scene(holes=(((1, 1), (2, 1), (2, 2), (1, 2)),))
        payload["request"]["domain"] = scene.analysis_domain.to_dict()
        payload["domain_geometries"] = [scene.geometries[0].to_dict()]
    elif change == "members":
        payload["request"]["domain"]["provenance"]["boundary_member_source_ids"] = ["ifc-object:g1"]
    elif change == "plane":
        payload["request"]["plane"]["origin"][2] = .1
    elif change == "basis":
        payload["request"]["plane"]["basis"] = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
    elif change == "band":
        payload["request"]["geometry_query"] = {"kind": "finite_height_band", "height_band": [0, 1], "world_z_m": None}
    elif change == "grid":
        payload["request"]["sampling"]["spacing"] = .5
    elif change == "rules":
        payload["request"]["source_rules"]["custom"] = True
    elif change == "tolerance":
        payload["request"]["topology_tolerance"] *= 2
    elif change == "containment":
        row.update(level_ref="storey-other", container_refs=["storey-other"])
    elif change == "legacy":
        row["properties"]["pending_legacy_occupancy"] = {"scope": {"operation": "changed"}}
    elif change == "scope":
        row["properties"]["analysis_scope_exclusion"] = {"reason": "changed", "domain_source_id": "other"}
    elif change == "confirmation":
        from ..adapters.blender_analysis_capture import CanonicalCaptureInput
        live = load_bonsai_capture(CanonicalCaptureInput(**payload["canonical_capture"]), plane=_plane())
        context = StructuralContext.from_plane(_plane())
        payload["job_binding"]["confirmation_binding"] = {"candidate_identity": "another-selection",
            "source_revision": service.digest(service.structural_source_facts(service.structural_b4_view(live.scene, context=context))),
            "frame_id": context.structural_frame_key}
    elif change == "support":
        from ..adapters.bonsai_live import SupportBinding
        from dataclasses import fields
        payload["support_binding"] = {item.name: "stale" for item in fields(SupportBinding)}
        payload["support_binding"]["geometry_refs"] = ["stale-geometry"]
    elif change == "schema":
        monkeypatch.setattr(service.wire, "SCHEMA_VERSION", "analysis-result/cache-test")
    elif change == "algorithm":
        monkeypatch.setattr(service.wire, "ALGORITHM_VERSION", "result-algorithm/cache-test")
    elif change == "cache_version":
        monkeypatch.setattr(service, "CONTENT_CACHE_VERSION", 2)
    elif change == "implementation":
        original_read = service.Path.read_bytes
        def changed_implementation(path):
            """Simulate different wire implementation bytes without editing shared source."""
            data = original_read(path)
            return data + b"\n# changed wire implementation\n" if path.name == "blender_analysis_result_wire.py" else data
        monkeypatch.setattr(service.Path, "read_bytes", changed_implementation)
    else:
        versions = analysis_requests._backend_versions()
        versions["packages"]["numpy"] = "changed"
        monkeypatch.setattr(analysis_requests, "_backend_versions", lambda: versions)
    payload["job_binding"]["job_id"] = "changed-content"
    result = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert result["content_cache"]["hit"] is False
    assert result["content_cache"]["content_key"] != first["content_cache"]["content_key"]
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_disk_cache_display_and_publication_metadata_reuse(tmp_path):
    """Declared display facts and observation tokens do not force recalculation."""
    from ..adapters import blender_analysis_session as service
    payload = _cache_payload()
    first = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    payload["canonical_capture"]["records"][0]["properties"].update(display_name="new label", color="red")
    payload["canonical_capture"]["observation"]["scene_token"] = "new-observation"
    payload["job_binding"].update(job_id="new-job", created_at="now", runtime_session="fresh-session")
    payload["request"]["request_id"] = "new-request"
    result = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert result["content_cache"]["hit"] is True
    assert result["binding"]["canonical_full_fingerprint"] != first["binding"]["canonical_full_fingerprint"]
    assert result["binding"]["capture_digest"] != first["binding"]["capture_digest"]
    assert result["binding"]["created_at"] == "now"


def test_fixed_cli_uses_persistent_cache_in_a_fresh_process(tmp_path):
    """Separate interpreter jobs use the fixed module's stable cache, outside job paths."""
    import subprocess
    import sys
    from pathlib import Path
    from ..adapters import blender_analysis_session as service
    payload = _cache_payload()
    from hashlib import sha256
    payload["request"]["domain"]["id"] = "cache-cli-" + sha256(str(tmp_path).encode()).hexdigest()
    request_path, first_path, current_path = (tmp_path / name for name in ("request.json", "first.json", "current.json"))
    request_path.write_text(service.wire.canonical_json(payload), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    first_child = subprocess.run([sys.executable, "-m", "adapters.blender_analysis_session", str(request_path), str(first_path)],
                                cwd=root, capture_output=True, text=True)
    assert first_child.returncode == 0, first_child.stderr
    first = service.wire.load_json(first_path.read_text(encoding="utf-8"))
    cache_path = service.CONTENT_CACHE_DIRECTORY / (first["content_cache"]["content_key"] + ".json")
    try:
        assert cache_path.is_file() and cache_path.parent != first_path.parent
        payload["job_binding"]["job_id"] = "fresh-process-hit"
        payload["request"]["plane"]["revision"] = 5
        request_path.write_text(service.wire.canonical_json(payload), encoding="utf-8")
        code = '''
import sys
from adapters import blender_analysis_session as session
from features import analysis_requests, geometry_views, free_space_field
def forbidden(*args, **kwargs):
    """Fail if a fresh-process cache hit attempts geometry or field generation."""
    raise AssertionError("cached CLI repeated generation")
session._project_authored = session.build_display_fragments = forbidden
analysis_requests.execute_analysis_request = geometry_views.plan_projection = forbidden
free_space_field.FreeSpaceField = forbidden
session.main(sys.argv[1:])
'''
        child = subprocess.run([sys.executable, "-c", code, str(request_path), str(current_path)],
                               cwd=root, capture_output=True, text=True)
        assert child.returncode == 0, child.stderr
        result = service.wire.load_json(current_path.read_text(encoding="utf-8"))
        assert result["content_cache"]["hit"] is True and result["plane_revision"] == 5
        assert result["content_cache"]["origin_result_ref"]["digest"] == first["digest"]
    finally:
        cache_path.unlink(missing_ok=True)


def test_disk_cache_preserves_all_states_and_distinct_cell_deltas(tmp_path, monkeypatch):
    """Fresh publication cannot flatten custom cell queries, support or provenance differences."""
    from ..adapters import blender_analysis_session as service
    from ..features import analysis_requests
    from ..features.field_core import FieldSample
    execute = analysis_requests.execute_analysis_request
    def distinct_run(scene, request):
        """Use the actual executor snapshot with intentionally distinct complete samples."""
        run = execute(scene, request)
        class Samples:
            """Supply independent sample deltas which sharing must preserve exactly."""
            def evaluate(self, target, query):
                """Vary states, metadata and deletions across the same immutable lattice."""
                row, column = target
                index = row * 4 + column
                status, value = (("established", True), ("conditional", False), ("unknown", None),
                    ("outside", None), ("invalid", None), ("not_available", None))[index % 6]
                actual_query = replace(query, demand={"cell": [row, column]},
                                       revision="cell-query" if column == 1 else query.revision)
                support = None if index == 5 else {"frame": query.frame, "plane": query.plane,
                                                  "nested": [row, column, None]}
                provenance = {**run.snapshot.provenance, "source_fingerprint": "cell-source-" + str(index),
                    "query_revision": actual_query.revision, "support": support,
                    "cell_delta": {"query_revision": query.revision, "nested": [row, column]}}
                provenance.pop("support_status", None)
                return FieldSample(value, status, actual_query, support=support, source_ids=("owner", str(index)),
                                   provenance=provenance, explanation="cell explanation " + str(index))
        return replace(run, field=Samples())
    monkeypatch.setattr(analysis_requests, "execute_analysis_request", distinct_run)
    payload = _cache_payload()
    first = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    def forbidden(*_args, **_kwargs):
        """Force this comparison through disk reconstruction, never generation."""
        pytest.fail("distinct cached samples were regenerated")
    monkeypatch.setattr(analysis_requests, "execute_analysis_request", forbidden)
    payload["job_binding"]["job_id"] = "distinct-hit"
    payload["request"]["plane"]["revision"] = 8
    result = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert result["content_cache"]["hit"] is True
    statuses = set()
    for row in range(4):
        for column in range(4):
            before = service.wire.decode_cell(first, row=row, column=column)
            after = service.wire.decode_cell(result, row=row, column=column)
            statuses.add(after["status"])
            for key in ("value", "status", "source_ids", "explanation"):
                assert after[key] == before[key]
            assert after["query"]["demand"] == before["query"]["demand"]
            assert after["query"]["plane"]["revision"] == 8
            assert after["query"]["revision"] == ("cell-query" if column == 1 else result["semantic_key"])
            assert after["provenance"]["query_revision"] == after["query"]["revision"]
            assert after["provenance"]["source_fingerprint"] == before["provenance"]["source_fingerprint"]
            assert after["provenance"]["cell_delta"] == before["provenance"]["cell_delta"]
            assert "support_status" not in after["provenance"]
            if before["support"] is None:
                assert after["support"] is None and after["provenance"]["support"] is None
            else:
                assert after["support"]["nested"] == before["support"]["nested"]
                assert after["support"]["frame"].endswith(":8") and after["support"]["plane"]["revision"] == 8
                assert after["provenance"]["support"] == after["support"]
    assert statuses == set(service.wire.STATUSES)


@pytest.mark.parametrize("failure", ["capture", "frozen_binding", "confirmation"])
def test_disk_cache_lookup_follows_canonical_and_consent_validation(tmp_path, monkeypatch, failure):
    """Warm content never bypasses invalid capture, frozen binding or stale domain consent."""
    from ..adapters import blender_analysis_session as service
    payload = _cache_payload()
    first = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    def forbidden(*_args, **_kwargs):
        """Refuse any lookup attempted before mandatory current-input validation."""
        pytest.fail("invalid current input reached cache lookup")
    monkeypatch.setattr(service, "_load_cached_result", forbidden)
    if failure == "capture":
        payload["canonical_capture"]["capture_complete"] = False
    elif failure == "frozen_binding":
        payload["job_binding"]["canonical_full_fingerprint"] = first["binding"]["canonical_full_fingerprint"] + "changed"
    else:
        payload["job_binding"]["confirmation_binding"] = {"source_revision": "stale", "frame_id": "wrong"}
    with pytest.raises(ValueError):
        service._execute_workflow_payload(payload, cache_directory=tmp_path)


@pytest.mark.parametrize("failure", ["generation", "cache_write", "public_write"])
def test_cache_and_cli_failures_preserve_previous_valid_files(tmp_path, monkeypatch, failure):
    """Generation and either atomic publication failure preserve prior complete truth."""
    from ..adapters import blender_analysis_session as service
    from ..features import analysis_requests
    cache_directory = tmp_path / "cache"
    monkeypatch.setattr(service, "CONTENT_CACHE_DIRECTORY", cache_directory)
    payload = _cache_payload()
    request_path, public_path = tmp_path / "request.json", tmp_path / "result.json"
    request_path.write_text(service.wire.canonical_json(payload), encoding="utf-8")
    service.main([str(request_path), str(public_path)])
    cache_path, = cache_directory.glob("*.json")
    cache_before, public_before = cache_path.read_bytes(), public_path.read_bytes()
    payload["job_binding"]["job_id"] = "failed-job"
    if failure == "generation":
        payload["request"]["sampling"]["spacing"] = .5
        def fail_generation(*_args, **_kwargs):
            """Inject a real miss failure before any validated candidate is published."""
            raise RuntimeError("generation failed")
        monkeypatch.setattr(analysis_requests, "execute_analysis_request", fail_generation)
    else:
        original_replace = service.wire.os.replace
        if failure == "cache_write":
            monkeypatch.setattr(service, "_load_cached_result", lambda *_args, **_kwargs: None)
        def fail_replace(source, destination):
            """Fail only the selected final atomic replacement, preserving its prior file."""
            if destination == (cache_path if failure == "cache_write" else public_path):
                raise OSError("atomic replacement failed")
            return original_replace(source, destination)
        monkeypatch.setattr(service.wire.os, "replace", fail_replace)
    request_path.write_text(service.wire.canonical_json(payload), encoding="utf-8")
    with pytest.raises((RuntimeError, OSError), match="failed"):
        service.main([str(request_path), str(public_path)])
    assert cache_path.read_bytes() == cache_before and public_path.read_bytes() == public_before
    assert not list(cache_directory.glob("*.partial")) and not list(tmp_path.glob("*.partial"))


def _slab_cache_payload():
    """Translate the real native slab receipt fixture into the canonical workflow wire."""
    from .test_bonsai_space_authoring import captured_slab_scene
    from .test_analysis_requests import _request
    from ..features.analysis_requests import GeometryQuery
    scene, datum = captured_slab_scene()
    records = []
    for source in scene.source_objects:
        mesh = next((mesh for mesh in scene.geometries if mesh.id in source.geometry_refs), None)
        records.append({"id": source.id, "global_id": source.source_id,
            "step_id": source.provenance["step_id"], "project_global_id": datum["project_global_id"],
            "ifc_class": source.source_class, "level_ref": source.level_ref,
            "container_refs": list(source.container_refs), "properties": {}, "binding_verified": True,
            "status": "extracted" if mesh is not None else "failed", "mesh": None if mesh is None else mesh.to_dict()})
    request = _request(scene, plane=_plane(origin=(4, 6, 2)), height_band_datum=datum,
                       geometry_query=GeometryQuery("finite_height_band", height_band=(-1.8, 0)))
    payload = _cache_payload()
    payload.update(request=request.to_dict(), domain_geometries=[scene.geometries[0].to_dict()],
        canonical_capture={"identity": {"project_global_id": datum["project_global_id"],
            "ifc_source_identity": "slab-cache-source", "schema": "IFC4"}, "records": records,
            "diagnostics": [], "observation": {}, "capture_complete": True})
    return payload


def test_disk_cache_datum_roundtrip_and_changed_receipt_miss(tmp_path):
    """A full validated selected-slab receipt survives a hit and its change invalidates content."""
    from ..adapters import blender_analysis_session as service
    payload = _slab_cache_payload()
    first = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    payload["job_binding"]["job_id"] = "slab-hit"
    hit = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert hit["content_cache"]["hit"] is True
    assert hit["tables"]["snapshot"]["request"]["height_band_datum"] == payload["request"]["height_band_datum"]
    assert hit["tables"]["snapshot"]["provenance"]["height_band_datum"] == first["tables"]["snapshot"]["provenance"]["height_band_datum"]
    datum = payload["request"]["height_band_datum"]
    datum["audit"] = {"selection": "re-observed exact source"}
    datum["observation_digest"] = service.digest({key: value for key, value in datum.items() if key != "observation_digest"})
    changed = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert changed["content_cache"]["hit"] is False


@pytest.mark.parametrize("change", ["receipt", "geometry", "containment"])
def test_disk_cache_revalidates_slab_before_lookup(tmp_path, monkeypatch, change):
    """A warm cache cannot hide raced geometry or a forged selected-slab receipt."""
    from ..adapters import blender_analysis_session as service
    payload = _slab_cache_payload()
    service._execute_workflow_payload(payload, cache_directory=tmp_path)
    if change == "receipt":
        payload["request"]["height_band_datum"]["geometry_digest"] = "forged"
    elif change == "geometry":
        for vertex in payload["canonical_capture"]["records"][0]["mesh"]["vertices"]:
            vertex[0] += .1
    else:
        payload["canonical_capture"]["records"][0]["container_refs"] = ["another-storey"]
    def forbidden(*_args, **_kwargs):
        """Fail if stale native slab validation is deferred until after cache lookup."""
        pytest.fail("stale selected slab reached lookup")
    monkeypatch.setattr(service, "_load_cached_result", forbidden)
    with pytest.raises(ValueError):
        service._execute_workflow_payload(payload, cache_directory=tmp_path)


def test_disk_cache_legacy_proxy_preserves_coverage_and_invalidates_applicability(tmp_path, monkeypatch):
    """A reused activated result preserves owners while changed pending applicability stays unknown."""
    from ..adapters import blender_analysis_session as service
    from .test_bonsai_live import legacy_bindings
    raw = capture("furniture", "furniture")
    live = load_bonsai_capture(raw, plane=_plane())
    payload = _cache_payload()
    payload.update(canonical_capture=raw.to_dict(),
                   legacy_bindings=[service.wire.plain(binding.__dict__) for binding in legacy_bindings(tmp_path, live)])
    cache_directory = tmp_path / "cache"
    first = service._execute_workflow_payload(payload, cache_directory=cache_directory)
    sample = service.reconstruct_field_sample(first, row=1, column=1)
    assert sample.value is True and sample.status.value == "conditional"
    assert sample.source_ids == ("ifc-object:g1", "ifc-object:g2")
    original_activation = service._activate_legacy_proxies
    def forbidden(*_args, **_kwargs):
        """Actual legacy activation, including its unconditional domain projection, must be skipped."""
        pytest.fail("legacy hit activated again")
    monkeypatch.setattr(service, "_activate_legacy_proxies", forbidden)
    payload["job_binding"]["job_id"] = "legacy-hit"
    hit = service._execute_workflow_payload(payload, cache_directory=cache_directory)
    assert hit["content_cache"]["hit"] is True
    assert service.reconstruct_field_sample(hit, row=1, column=1) == sample
    monkeypatch.setattr(service, "_activate_legacy_proxies", original_activation)
    for binding in payload["legacy_bindings"]:
        binding["scope"]["applicability"]["operation"] = "physical_occupancy"
    changed = service._execute_workflow_payload(payload, cache_directory=cache_directory)
    assert changed["content_cache"]["hit"] is False
    assert service.reconstruct_field_sample(changed, row=1, column=1).value is None
    assert set(changed["tables"]["snapshot"]["provenance"]["unknown_source_ids"]) == {"ifc-object:g1", "ifc-object:g2"}


def test_disk_cache_support_selection_is_validated_and_never_class_wide(tmp_path):
    """Only a current exact floor binding changes occupancy, including across disk hits."""
    from ..adapters import blender_analysis_session as service
    from ..adapters.bonsai_live import SupportBinding, geometry_digest
    payload = _cache_payload()
    raw = capture("slab")
    payload["canonical_capture"] = raw.to_dict()
    unbound = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert service.reconstruct_field_sample(unbound, row=0, column=0).value is True
    live = load_bonsai_capture(raw, plane=_plane())
    slab = live.scene.source_objects[0]
    binding = SupportBinding(slab.id, "project", "IfcSlab", slab.geometry_refs,
        geometry_digest(live.scene, slab), live.capture_fingerprint, "exact-floor-consent")
    payload["support_binding"] = service.wire.plain(binding.__dict__)
    payload["job_binding"]["job_id"] = "supported-miss"
    supported = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert supported["content_cache"]["hit"] is False
    assert service.reconstruct_field_sample(supported, row=0, column=0).value is False
    payload["job_binding"]["job_id"] = "supported-hit"
    hit = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert hit["content_cache"]["hit"] is True
    assert service.reconstruct_field_sample(hit, row=0, column=0).value is False
    payload["support_binding"]["geometry_digest"] = "stale-floor"
    refused = service._execute_workflow_payload(payload, cache_directory=tmp_path)
    assert refused["content_cache"]["hit"] is False
    assert service.reconstruct_field_sample(refused, row=0, column=0).value is True


@pytest.mark.parametrize("top,plane_z", [(.2, 2.0), (-3.0, -1.2)])
def test_native_slab_band_contact_mass_and_full_receipt_round_trip(top, plane_z):
    """The live seam keeps slab contact empty, partial mass occupied and the full receipt readable."""
    from ..adapters import blender_analysis_session as service
    from ..adapters.blender_analysis_capture import digest
    from ..features.analysis_requests import GeometryQuery, GridSampling
    from .test_analysis_requests import _object, _request
    from .test_bonsai_space_authoring import captured_slab_scene
    scene, datum = captured_slab_scene(top=top)
    datum["audit"] = {"note": "楼板", "observed": ["selected native slab"]}
    datum["observation_digest"] = digest({key: value for key, value in datum.items() if key != "observation_digest"})
    partial, mesh = _object("partial-slab", (6, 6, top - .1, 7, 7, top + .3), role="slab")
    above, high_mesh = _object("above", (7, 6, plane_z, 8, 7, plane_z + .3))
    scene = replace(scene, source_objects=scene.source_objects + (partial, above),
                    geometries=scene.geometries + (mesh, high_mesh))
    request = _request(scene, plane=_plane(origin=(4, 6, plane_z),
        basis=((0, 1, 0), (-1, 0, 0), (0, 0, 1))),
        sampling=GridSampling((0, -4), 1, 4, 4),
        geometry_query=GeometryQuery("finite_height_band", height_band=(top - plane_z, 0)),
        height_band_datum=datum)
    run = service.execute_live_analysis(scene, request=request, domain_geometries=(scene.geometries[0],))
    assert run.field.evaluate((3, 0), run.query).value is False
    assert run.field.evaluate((1, 0), run.query).value is True
    assert run.field.evaluate((0, 0), run.query).value is False
    assert run.snapshot.provenance["height_band_datum"] == request.height_band_datum
    document = service.serialize_analysis_result(run, job_id="slab-band", plane_uuid=request.plane.identity,
        plane_revision=request.plane.revision, domain_request_id="domain", domain_session_revision=1)
    restored = service.wire.load_json(service.wire.canonical_json(document))
    decoded = service._request_from_wire(restored["tables"]["snapshot"]["request"])
    assert decoded.to_dict() == request.to_dict()
    snapshot = service.open_analysis_result([restored], result_ref=service.list_analysis_results([restored])[0].ref,
        context=_read_context(restored))
    assert service.wire.plain(snapshot.payload["tables"]["snapshot"]["request"]["height_band_datum"]) == datum
    assert service.read_analysis_sample(snapshot, row=1, column=0).value is True


def test_live_slab_band_refuses_geometry_race_before_executor(monkeypatch):
    """An unchanged slab top cannot authorize moved captured geometry or execute any occupancy."""
    from ..adapters import blender_analysis_session as service
    from ..features import analysis_requests
    from ..features.analysis_requests import GeometryQuery
    from .test_analysis_requests import _request
    from .test_bonsai_space_authoring import captured_slab_scene
    scene, datum = captured_slab_scene()
    request = _request(scene, plane=_plane(origin=(4, 6, 2)), height_band_datum=datum,
        geometry_query=GeometryQuery("finite_height_band", height_band=(-1.8, 0)))
    geometry = scene.geometries[1]
    moved = replace(geometry, vertices=tuple((x + .1, y, z) for x, y, z in geometry.vertices))
    scene = replace(scene, geometries=(scene.geometries[0], moved))
    def unexpected(*_args):
        """Fail if stale observation reaches the expensive occupancy executor."""
        pytest.fail("stale datum reached occupancy execution")
    monkeypatch.setattr(analysis_requests, "execute_analysis_request", unexpected)
    with pytest.raises(ValueError, match="geometry changed"):
        service.execute_live_analysis(scene, request=request, domain_geometries=(scene.geometries[0],))


def _read_context(document, **changes):
    """Supply explicit frozen expected metadata for a historical diagnostic read."""
    from ..adapters import blender_analysis_session as service
    return service.ResultReadContext(**{"expected": service.list_analysis_results([document])[0].identity,
        "backend_versions": document["backend_versions"], "allow_historical": True, **changes})


def _composition_bindings(document):
    """Provide data-only observations for the two existing composition seams."""
    plane = document["tables"]["snapshot"]["request"]["plane"]
    return {"plane_binding": {"version": 1, "project_global_id": "project-A", "camera_guid": "camera-A",
                "plane_uuid": plane["identity"], "plane_revision": plane["revision"],
                "origin": plane["origin"], "basis": plane["basis"], "observation_digest": "a" * 64},
            "space_binding": {"version": 1, "project_global_id": "project-A", "space_guid": "space-A",
                "source_id": "ifc-object:space-A", "storey_ref": "ifc-object:storey-A",
                "geometry_digest": "b" * 64, "origin": "adopted", "provenance": {}}}


def test_optional_compositions_preserve_legacy_and_round_trip_history():
    """Old documents stay readable and observations alone never revive confirmation."""
    from ..adapters import blender_analysis_session as service
    from ..adapters import blender_analysis_result_wire as wire
    run, legacy = _compact_document(domain_source="space-A")
    assert legacy["binding"] == {}
    binding = _composition_bindings(legacy)
    document = service.serialize_analysis_result(run, job_id="job-A", plane_uuid="plane:plan",
        plane_revision=1, domain_request_id="domain-request-A", domain_session_revision=2, binding=binding)
    restored = wire.load_json(wire.canonical_json(document))
    metadata = service.list_analysis_results([restored])[0]
    snapshot = service.open_analysis_result([restored], result_ref=metadata.ref, context=_read_context(restored))
    assert wire.plain(snapshot.payload["binding"]) == binding
    assert snapshot.freshness == "historical"
    with pytest.raises(ValueError, match="independently verified"):
        service.open_analysis_result([restored], result_ref=metadata.ref,
            context=_read_context(restored, require_current=True))


@pytest.mark.parametrize("change", ["project", "source", "plane", "revision", "query", "domain"])
def test_composition_change_revokes_current_read_but_preserves_history(change):
    """Every dependent input must match fresh evidence, including the native source."""
    from ..adapters import blender_analysis_session as service
    from ..adapters import blender_analysis_result_wire as wire
    run, legacy = _compact_document(domain_source="space-A")
    document = service.serialize_analysis_result(run, job_id="job-A", plane_uuid="plane:plan",
        plane_revision=1, domain_request_id="domain-request-A", domain_session_revision=2,
        binding=_composition_bindings(legacy))
    metadata = service.list_analysis_results([document])[0]
    observed = wire.plain(document["binding"])
    if change == "project":
        observed["plane_binding"]["project_global_id"] = "another-project"
    elif change == "source":
        observed["space_binding"]["geometry_digest"] = "c" * 64
    elif change == "plane":
        observed["plane_binding"]["origin"][2] += 1
    elif change == "revision":
        observed["plane_binding"]["plane_revision"] += 1
    else:
        observed[change + "_key"] = "changed"
    with pytest.raises(ValueError, match="independently verified"):
        service.open_analysis_result([document], result_ref=metadata.ref, context=_read_context(document,
            require_current=True, current_observation={"digest": document["digest"], "binding": observed, "verified": True}))
    assert service.open_analysis_result([document], result_ref=metadata.ref,
        context=_read_context(document)).freshness == "historical"


@pytest.mark.parametrize("change", ["project", "revision", "source", "version", "pointer"])
def test_rehashed_invalid_composition_is_rejected(change):
    """Rehashing cannot make cross-project, mismatched or executable observations valid."""
    from ..adapters import blender_analysis_result_wire as wire
    _, document = _compact_document(domain_source="space-A")
    document["binding"] = _composition_bindings(document)
    if change == "project":
        document["binding"]["space_binding"]["project_global_id"] = "other"
    elif change == "revision":
        document["binding"]["plane_binding"]["plane_revision"] = 2
    elif change == "source":
        document["binding"]["space_binding"]["source_id"] = "ifc-object:other"
    elif change == "version":
        document["binding"]["plane_binding"]["version"] = 99
    else:
        document["binding"]["plane_binding"]["object_pointer"] = 123
    document["digest"] = wire.document_digest(document)
    with pytest.raises(ValueError, match="composition"):
        wire.validate_document(document)


def test_compact_round_trip_preserves_every_field_sample():
    """Compression must reconstruct all public fields, not just value/status."""
    from dataclasses import fields
    from ..adapters import blender_analysis_session as service
    run, document = _compact_document()
    for row in range(4):
        for column in range(4):
            original = run.field.evaluate((row, column), run.query)
            actual = service.reconstruct_field_sample(document, row=row, column=column)
            assert actual == original
            for field in fields(original):
                assert getattr(actual, field.name) == getattr(original, field.name)
    assert document["tables"]["snapshot"] == run.snapshot.to_dict()


def test_dedupe_preserves_same_key_different_cell_values():
    """Same-key changes, removed keys, query and support deltas cannot disappear."""
    from ..adapters import blender_analysis_session as service
    from ..features.field_core import FieldSample, FieldStatus
    run = _compact_run()
    class Samples:
        """Return deliberately distinct complete public samples on the real run query."""
        def evaluate(self, target, query):
            """Vary every auditable component independently of shared key presence."""
            row, column = target
            provenance = dict(run.snapshot.provenance)
            provenance["source_fingerprint"] = f"local-{row}-{column}"
            provenance.pop("support_status", None)
            return FieldSample(False, FieldStatus.CONDITIONAL,
                replace(query, demand={"width": column + 1}, revision=f"q-{row}-{column}"),
                support={"nested": [row, column, None]}, source_ids=("owner", str(column)),
                provenance=provenance, explanation="qualified cell limitation")
    modified = replace(run, field=Samples())
    document = service.serialize_analysis_result(modified, job_id="distinct", plane_uuid="plane:plan",
        plane_revision=1, domain_request_id="d", domain_session_revision=1)
    for row in range(4):
        for column in range(4):
            assert service.reconstruct_field_sample(document, row=row, column=column) == modified.field.evaluate((row, column), run.query)


def _shared_metadata_run(cell_count):
    """Supply complete synthetic cells over a real request with one frozen large audit."""
    from ..features.field_core import FieldSample, _MetadataOverlay
    run = _compact_run()
    request = replace(run.snapshot.request, sampling=replace(run.snapshot.request.sampling,
                                                           n_rows=1, n_cols=cell_count))
    snapshot = replace(run.snapshot, request=request, provenance={**run.snapshot.provenance,
        "selected_records": {"visit_marker": "shared-scale-audit",
                             "vertices": [[float(index), 0.0, 0.0] for index in range(128)]}})
    shared = _MetadataOverlay(snapshot.provenance)
    class Samples:
        """Share only actual core-frozen metadata while retaining distinct cell history."""
        def evaluate(self, target, query):
            """Vary every sample field, including deletion and independent support evidence."""
            index = target[1]
            status, value = (("established", True), ("conditional", False), ("unknown", None),
                ("outside", None), ("invalid", None), ("not_available", None))[index % 6]
            support = {"frame": query.frame, "plane": query.plane, "cell": [0, index, None]}
            local = {"same_key": index, "support": {"independent": True} if index == 1 else support}
            if index == 0:
                local["first_only"] = None
            return FieldSample(value, status, replace(query, demand={"cell": index}, tolerance=index / 100),
                support=support, source_ids=("owner", str(index)), provenance=_MetadataOverlay(shared, local),
                explanation="cell scope " + str(index))
    return replace(run, field=Samples(), snapshot=snapshot)


def test_shared_metadata_work_is_bounded_for_generation_cache_and_validation(monkeypatch):
    """Shared audit traversal and Field freezing stay constant as cell count increases."""
    from collections import Counter
    from collections.abc import Mapping
    from ..adapters import blender_analysis_session as service
    from ..features import field_core
    runs = [_shared_metadata_run(count) for count in (6, 24)]
    visits, phase = {}, ""
    def observed(module, name):
        """Count real recursive visits without replacing conversion or validation behavior."""
        original = getattr(module, name)
        def counted(value):
            """Mark only the large shared audit's root, independent of its leaf count."""
            if isinstance(value, Mapping) and value.get("visit_marker") == "shared-scale-audit":
                visits[phase][name] += 1
            return original(value)
        monkeypatch.setattr(module, name, counted)
    for module, name in ((service.wire, "plain"), (service.wire, "freeze"), (field_core, "_freeze")):
        observed(module, name)
    results = []
    for run in runs:
        counts = {}
        for phase in ("generate", "validate", "cache"):
            visits[phase] = Counter()
            if phase == "generate":
                document = service.serialize_analysis_result(run, job_id="scale", plane_uuid="plane:plan",
                    plane_revision=1, domain_request_id="domain", domain_session_revision=1)
            elif phase == "validate":
                service.validate_analysis_result(document, expected_job_id="scale", expected_plane_uuid="plane:plan",
                    expected_plane_revision=1, expected_semantic_key=document["semantic_key"])
            else:
                request = replace(run.snapshot.request, plane=replace(run.snapshot.request.plane, revision=7))
                cached = service._cached_run(document, request, document["backend_versions"])
                first = cached.field.evaluate((0, 0), cached.query)
                last = cached.field.evaluate((0, request.sampling.n_cols - 1), cached.query)
                assert first.provenance["selected_records"] is last.provenance["selected_records"]
                current = service.serialize_analysis_result(cached, job_id="scale-hit", plane_uuid="plane:plan",
                    plane_revision=7, domain_request_id="current-domain", domain_session_revision=2)
            counts[phase] = dict(visits[phase])
        results.append(counts)
        for column in range(run.snapshot.request.sampling.n_cols):
            sample = run.field.evaluate((0, column), run.query)
            assert service.reconstruct_field_sample(document, row=0, column=column) == sample
            before = service.wire.decode_cell(document, row=0, column=column)
            after = service.wire.decode_cell(current, row=0, column=column)
            for key in ("value", "status", "source_ids", "explanation"):
                assert after[key] == before[key]
            assert after["query"]["demand"] == before["query"]["demand"]
            assert after["query"]["plane"]["revision"] == 7
            assert after["provenance"]["selected_records"] == before["provenance"]["selected_records"]
            assert after["provenance"]["same_key"] == column
            assert ("first_only" in after["provenance"]) == (column == 0)
            assert (after["provenance"]["support"] == after["support"]) == (column != 1)
        # Public decodes must own their returned containers despite private shared views.
        exposed = service.wire.decode_cell(document, row=0, column=0)
        exposed["provenance"]["selected_records"]["vertices"][0][0] = -99
        exposed["support"]["cell"].append("external")
        assert service.wire.decode_cell(document, row=0, column=0) != exposed
    assert results[0] == results[1], results
    assert all(sum(counts.values()) > 0 for counts in results[0].values())


@pytest.mark.parametrize("shallow_proxy", [False, True])
def test_duck_samples_snapshot_mutable_history_before_next_evaluation(shallow_proxy):
    """Neither a duck sample nor its shallow proxy proves deeply frozen ownership."""
    from dataclasses import fields
    from types import MappingProxyType, SimpleNamespace
    from ..adapters import blender_analysis_session as service
    from ..features.field_core import FieldStatus
    run, expected = _compact_run(), []
    class Samples:
        """Reuse caller-owned containers that change between sample evaluations."""
        def __init__(self):
            """Keep one external backing mapping behind optional shallow proxies."""
            self.audit = {"algorithm_version": service.wire.REQUEST_VERSION,
                          "schema_version": service.wire.REQUEST_VERSION, "history": [], "first_only": None}
            self.support = {"history": []}
        def evaluate(self, target, query):
            """Change same-key values, deletions and nested aliases before returning each cell."""
            index = target[0] * 4 + target[1]
            self.audit["history"].append(index)
            self.audit["same_key"] = index
            self.support["history"].append(index)
            self.audit["support"] = self.support if index != 1 else {"independent": True}
            if index:
                self.audit.pop("first_only", None)
            sample = SimpleNamespace(value=True, status=FieldStatus.ESTABLISHED, query=query,
                support=self.support, source_ids=["duck", str(index)],
                provenance=MappingProxyType(self.audit) if shallow_proxy else self.audit, explanation="duck history")
            expected.append({"value": sample.value, "status": sample.status.value,
                "query": {item.name: service.wire.plain(getattr(query, item.name)) for item in fields(query)},
                "support": service.wire.plain(sample.support), "source_ids": service.wire.plain(sample.source_ids),
                "provenance": service.wire.plain(sample.provenance), "explanation": sample.explanation})
            return sample
    samples = Samples()
    document = service.serialize_analysis_result(replace(run, field=samples), job_id="duck", plane_uuid="plane:plan",
        plane_revision=1, domain_request_id="domain", domain_session_revision=1)
    samples.audit["history"].append("later")
    samples.support["history"].append("later")
    assert [service.wire.decode_cell(document, row=row, column=column)
            for row in range(4) for column in range(4)] == expected


def test_atomic_write_failure_retains_old_result(tmp_path, monkeypatch):
    """An atomic replacement failure retains old bytes and removes only its partial."""
    from ..adapters import blender_analysis_session as service
    from ..adapters import blender_analysis_result_wire as wire
    path = tmp_path / "result.json"
    path.write_bytes(b"previous truth")
    unrelated = tmp_path / "unrelated.partial"
    unrelated.write_bytes(b"keep")
    def fail(*args):
        """Inject filesystem failure at the irreversible publish boundary."""
        raise OSError("injected replace failure")
    monkeypatch.setattr(wire.os, "replace", fail)
    with pytest.raises(OSError):
        service.write_result_atomic(_compact_document()[1], path=path)
    assert path.read_bytes() == b"previous truth"
    assert unrelated.read_bytes() == b"keep"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["result.json", "unrelated.partial"]


def test_payload_cannot_select_executable():
    """Unknown command/interpreter/module choices refuse before capture or execution."""
    from ..adapters import blender_analysis_session as service
    for key in ("executable", "command", "module", "interpreter"):
        with pytest.raises(ValueError):
            service._execute_workflow_payload({"kind": "free_space_run", key: "untrusted"})


def test_result_catalogue_lists_domain_and_free_space_metadata():
    """Catalogue exposes both kinds without inventing an occupancy query for B4."""
    from ..adapters import blender_analysis_session as service
    _, free = _compact_document()
    domain = service._serialize_domain_result(evaluate_domain_request(enclosed_scene(),
        context=StructuralContext.from_plane(_plane()), prior=None, action=None), result_id="domain-job", binding={})
    metadata = service.list_analysis_results([domain, free])
    assert {item.ref.kind for item in metadata} == {"domain_session", "free_space_run"}
    assert metadata[0].identity["domain_identity"] is None
    assert "query_key" not in metadata[0].identity
    assert len(service.list_analysis_results([domain, free], kind="free_space_run")) == 1


def test_exact_result_ref_rejects_missing_ambiguous_or_mismatched_identity():
    """An exact immutable ref never silently selects another result."""
    from ..adapters import blender_analysis_session as service
    _, document = _compact_document()
    ref = service.list_analysis_results([document])[0].ref
    for documents, requested in (([], ref), ([document, document], ref),
                                 ([document], replace(ref, digest="0" * 64))):
        with pytest.raises(ValueError):
            service.open_analysis_result(documents, result_ref=requested, context=_read_context(document))


@pytest.mark.parametrize("changed", [{"domain_id": "room-B"}, {"revision": 3},
    {"mode": "exact_world_xy_section"}, {"project": "project-B"}])
def test_consumer_isolates_domain_plane_mode_revision_and_source(changed):
    """A different real request identity cannot satisfy a consumer's expected context."""
    from ..adapters import blender_analysis_session as service
    _, original = _compact_document()
    _, other = _compact_document(**changed)
    with pytest.raises(ValueError):
        service.open_analysis_result([other], result_ref=service.list_analysis_results([other])[0].ref,
                                     context=_read_context(original))
    mismatch = dict(_read_context(original).expected) | {"plane_uuid": "other-plane"}
    with pytest.raises(ValueError):
        service.open_analysis_result([original], result_ref=service.list_analysis_results([original])[0].ref,
                                     context=_read_context(original, expected=mismatch))


def test_consumer_rejects_incompatible_versions_and_stale_as_current():
    """A recomputed digest or saved current flag cannot authorize incompatible/current reads."""
    from ..adapters import blender_analysis_session as service
    from ..adapters import blender_analysis_result_wire as wire
    _, document = _compact_document()
    for key in ("schema_version", "algorithm_version"):
        bad = document | {key: "future/99"}
        bad["digest"] = wire.document_digest(bad)
        with pytest.raises(ValueError):
            service.list_analysis_results([bad])
    ref = service.list_analysis_results([document])[0].ref
    for changes in ({"allow_historical": False}, {"require_current": True},
                    {"backend_versions": {"executor": "other"}}):
        with pytest.raises(ValueError):
            service.open_analysis_result([document], result_ref=ref, context=_read_context(document, **changes))


def test_consumer_preserves_unknown_conditional_and_full_provenance():
    """Freshness does not upgrade unknown or remove conditional restrictions."""
    from ..adapters import blender_analysis_session as service
    from .test_analysis_requests import _proxy_scene, _request, _missing
    from ..features.analysis_requests import execute_analysis_request
    from ..features.field_core import FieldStatus
    scene = _proxy_scene()
    for scene in (scene, replace(scene, source_objects=scene.source_objects + (_missing("missing")[0],))):
        run = execute_analysis_request(scene, _request(scene))
        document = service.serialize_analysis_result(run, job_id="sample", plane_uuid="plane:plan",
            plane_revision=1, domain_request_id="d", domain_session_revision=1)
        from ..adapters import blender_analysis_result_wire as wire
        document["binding"] = {"job_id": "sample", "runtime_session": "trusted-reader-test-observation"}
        document["digest"] = wire.document_digest(document)
        observation = {"digest": document["digest"], "binding": document["binding"], "verified": True}
        snapshot = service.open_analysis_result([document], result_ref=service.list_analysis_results([document])[0].ref,
            context=_read_context(document, require_current=True, current_observation=observation))
        assert snapshot.freshness == "current"
        actual = service.read_analysis_sample(snapshot, row=0, column=0)
        assert actual == run.field.evaluate((0, 0), run.query)
        assert actual.status in {FieldStatus.UNKNOWN, FieldStatus.CONDITIONAL}
        if actual.status is FieldStatus.UNKNOWN:
            assert actual.value is None
        else:
            assert actual.explanation and actual.value is False


def test_readonly_snapshot_cannot_mutate_authority():
    """Neither nested snapshot edits nor later caller edits rewrite the opened truth."""
    from ..adapters import blender_analysis_session as service
    _, document = _compact_document()
    snapshot = service.open_analysis_result([document], result_ref=service.list_analysis_results([document])[0].ref,
                                           context=_read_context(document))
    with pytest.raises(TypeError):
        snapshot.payload["tables"]["snapshot"]["provenance"]["altered"] = True
    with pytest.raises((TypeError, AttributeError)):
        snapshot.payload["cells"][0]["row"] = 99
    original = service.read_analysis_sample(snapshot, row=0, column=0)
    document["cells"][0]["value"] = True
    assert service.read_analysis_sample(snapshot, row=0, column=0) == original
    for row, column in ((-1, 0), (4, 0), (True, 0)):
        with pytest.raises(ValueError):
            service.read_analysis_sample(snapshot, row=row, column=column)


def test_consumer_never_captures_computes_or_spawns(monkeypatch):
    """Reading a document has no route back to analysis or native process authority."""
    import subprocess
    from ..adapters import blender_analysis_session as service, blender_analysis_capture as native
    from ..features import analysis_requests
    _, document = _compact_document()
    def forbidden(*args, **kwargs):
        """Fail on any attempted side effect during read-only consumption."""
        raise AssertionError("reader attempted capture/compute/spawn")
    monkeypatch.setattr(native, "begin_analysis_capture", forbidden)
    monkeypatch.setattr(analysis_requests, "execute_analysis_request", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    ref = service.list_analysis_results([document])[0].ref
    snapshot = service.open_analysis_result([document], result_ref=ref, context=_read_context(document))
    assert service.read_analysis_sample(snapshot, row=0, column=0).value is None


def test_live_and_embedded_results_use_same_reader_without_sidecar(tmp_path):
    """Text JSON alone reconstructs the same immutable samples after sidecar removal."""
    import json
    from ..adapters import blender_analysis_session as service
    _, document = _compact_document()
    sidecar = service.write_result_atomic(document, path=tmp_path / "result.json")
    text_body = sidecar.read_text(encoding="utf-8")
    sidecar.unlink()
    restored = json.loads(text_body)
    ref = service.list_analysis_results([document])[0].ref
    snapshots = [service.open_analysis_result([data], result_ref=ref, context=_read_context(document))
                 for data in (document, restored)]
    assert snapshots[0] == snapshots[1]
    assert service.read_analysis_sample(snapshots[0], row=1, column=1) == service.read_analysis_sample(snapshots[1], row=1, column=1)


def test_unconfirmed_domain_is_diagnostic_only_not_confirmed_consumption():
    """An unconfirmed candidate is readable but cannot stand in for domain consent."""
    from ..adapters import blender_analysis_session as service
    domain = service._serialize_domain_result(evaluate_domain_request(enclosed_scene(),
        context=StructuralContext.from_plane(_plane()), prior=None, action=None), result_id="diagnostic", binding={})
    ref = service.list_analysis_results([domain])[0].ref
    snapshot = service.open_analysis_result([domain], result_ref=ref, context=_read_context(domain))
    assert snapshot.metadata.identity["domain_identity"] is None
    with pytest.raises(ValueError):
        service.open_analysis_result([domain], result_ref=ref, context=_read_context(domain, require_confirmed_domain=True))
    with pytest.raises(ValueError):
        service.read_analysis_sample(snapshot, row=0, column=0)


@pytest.mark.parametrize("status,value", [("established", True), ("conditional", False),
    ("unknown", None), ("outside", None), ("invalid", None), ("not_available", None)])
def test_compact_preserves_all_six_states_and_complete_query(status, value):
    """Every Field state and nested public audit must survive the same codec."""
    from ..adapters import blender_analysis_session as service
    from ..features.field_core import FieldSample
    run = _compact_run()
    sample = FieldSample(value, status, replace(run.query, height_band=(1, 2), demand={"width": [1, 2]}, tolerance=.25),
        support={"point": [2, 3], "qualified_empty": {"type": "GeometryCollection", "geometries": []}},
        source_ids=("A", "B"), provenance=run.snapshot.provenance, explanation="scoped evidence")
    class Samples:
        """Keep this single explicit immutable sample for all legal cells."""
        def evaluate(self, target, query):
            """Return the complete sample independently of serialization."""
            return sample
    document = service.serialize_analysis_result(replace(run, field=Samples()), job_id="six", plane_uuid="plane:plan",
        plane_revision=1, domain_request_id="d", domain_session_revision=1)
    actual = service.reconstruct_field_sample(document, row=0, column=0)
    assert actual == sample
    assert actual.query.demand == {"width": (1, 2)}


@pytest.mark.parametrize("mutation", ["ref", "cell", "sample_schema", "binding", "fragments",
                                     "pairlist_linked", "pairlist_unlinked"])
def test_rehashed_malformed_result_is_rejected(mutation):
    """A valid SHA alone cannot make invalid references, versions or geometry consumable."""
    from ..adapters import blender_analysis_session as service
    from ..adapters import blender_analysis_result_wire as wire
    _, document = _compact_document()
    if mutation == "ref":
        document["cells"][0]["query_ref"] = True
    elif mutation == "cell":
        document["cells"][0]["column"] = 1
    elif mutation == "sample_schema":
        document["cells"][0]["provenance_delta"]["changes"]["schema_version"] = len(document["tables"]["values"])
        document["tables"]["values"].append("future/9")
    elif mutation == "binding":
        document["binding"]["domain_request_id"] = "another-domain-request"
    elif mutation in {"pairlist_linked", "pairlist_unlinked"}:
        reference = len(document["tables"]["values"])
        document["tables"]["values"].append([["algorithm_version", wire.REQUEST_VERSION],
                                             ["schema_version", wire.REQUEST_VERSION]])
        document["cells"][0].update(provenance_delta={"ref": reference},
                                    provenance_support=mutation == "pairlist_linked")
    else:
        document["display_fragments"] = [{"cell_index": 0, "vertices": [[0, 0, 0]], "faces": [[0, 1, 2]]}]
    document["digest"] = wire.document_digest(document)
    with pytest.raises(ValueError):
        service.validate_analysis_result(document, expected_job_id="job-A", expected_plane_uuid="plane:plan",
            expected_plane_revision=1, expected_semantic_key=document["semantic_key"])


def test_wire_json_rejects_duplicate_keys_and_nonfinite():
    """Embedded parsing must reject ambiguous JSON and nonfinite constants."""
    from ..adapters import blender_analysis_result_wire as wire
    for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
        with pytest.raises(ValueError):
            wire.load_json(raw)


@pytest.mark.parametrize("provenance_support", [False, True])
def test_validator_checks_stored_data_without_changing_return_ownership(provenance_support):
    """Mapping hooks cannot hide wrong versions; successful reads retain caller ownership."""
    from ..adapters import blender_analysis_result_wire as wire
    _, document = _compact_document()
    assert wire.validate_document(document) is document
    frozen = wire.freeze(document)
    assert wire.validate_document(frozen) is frozen
    class VersionHook(dict):
        """Store invalid data while presenting compatible versions through a custom getter."""
        def get(self, key, default=None):
            """Spoof only the validation read that previously retained mapping hooks."""
            return wire.REQUEST_VERSION if key in {"algorithm_version", "schema_version"} else super().get(key, default)
    reference = len(document["tables"]["values"])
    document["tables"]["values"].append(VersionHook(algorithm_version="wrong", schema_version="wrong"))
    document["cells"][0].update(provenance_delta={"ref": reference}, provenance_support=provenance_support)
    document["digest"] = wire.document_digest(document)
    with pytest.raises(ValueError, match="provenance"):
        wire.validate_document(document)


def test_validator_checks_stored_query_identity_without_mapping_hooks():
    """A custom query getter cannot disguise a non-string stored domain identity."""
    from ..adapters import blender_analysis_result_wire as wire
    _, document = _compact_document()
    class QueryHook(dict):
        """Keep invalid stored identity while returning a valid string through indexing."""
        def __getitem__(self, key):
            """Mask the identity only when validation reads the caller's custom object."""
            return "masked-domain" if key == "domain_id" else super().__getitem__(key)
    query = QueryHook(wire.resolve_value(document, document["cells"][0]["query_ref"]))
    query["domain_id"] = 17
    document["cells"][0]["query_ref"] = len(document["tables"]["values"])
    document["tables"]["values"].append(query)
    document["digest"] = wire.document_digest(document)
    with pytest.raises(ValueError, match="query"):
        wire.validate_document(document)


def test_fixed_module_cli_round_trip_and_data_binding(tmp_path):
    """The actual fixed module CLI reads two paths and produces the shared validated format."""
    import json
    import subprocess
    import sys
    from pathlib import Path
    from ..adapters import blender_analysis_session as service
    from ..adapters import blender_analysis_result_wire as wire
    context = StructuralContext.from_plane(_plane())
    request_path, result_path = tmp_path / "request.json", tmp_path / "result.json"
    payload = {"kind": "domain_session", "job_binding": {"job_id": "cli-domain", "created_at": "frozen-time"},
        "canonical_capture": capture("wall").to_dict(), "context": context.to_dict(), "prior": None, "action": None}
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    child = subprocess.run([sys.executable, "-m", "adapters.blender_analysis_session", str(request_path), str(result_path)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert child.returncode == 0, child.stderr
    document = wire.load_json(result_path.read_text(encoding="utf-8"))
    metadata = service.list_analysis_results([document])[0]
    assert document["result_id"] == "cli-domain"
    assert document["binding"]["created_at"] == "frozen-time"
    assert document["binding"]["canonical_full_fingerprint"]
    assert document["binding"]["authored_groups"] == []
    assert metadata.ref.kind == "domain_session" and "query_key" not in metadata.identity
    # A new free-space envelope reuses exact typed domain geometry, never B4 triangulation.
    from .test_analysis_requests import _request
    scene = _scene()
    payload = {"kind": "free_space_run", "job_binding": {"job_id": "cli-free", "domain_request_id": "d", "domain_session_revision": 1},
        "canonical_capture": capture("wall").to_dict(), "request": _request(scene).to_dict(),
        "domain_geometries": [scene.geometries[0].to_dict()], "support_binding": None, "legacy_bindings": []}
    document = service._execute_workflow_payload(payload)
    assert document["binding"]["canonical_full_fingerprint"] != document["tables"]["snapshot"]["source_fingerprint"]
    assert service.reconstruct_field_sample(document, row=3, column=3).value is False


def test_top_level_cli_authored_space_domain_import_context(tmp_path):
    """The fixed top-level module CLI resolves authored Space helpers without package-relative imports."""
    import json
    import subprocess
    import sys
    from pathlib import Path
    from ..adapters import blender_analysis_result_wire as wire

    data = capture("space").to_dict()
    data["records"][0].update(ifc_class="IfcSpace", role="space",
                               level_ref="ifc-object:storey-1",
                               container_refs=["ifc-object:storey-1"])
    context = StructuralContext.from_plane(_plane())
    request_path, result_path = tmp_path / "request.json", tmp_path / "result.json"
    payload = {"kind": "domain_session",
        "job_binding": {"job_id": "cli-authored", "created_at": "frozen-time"},
        "canonical_capture": data, "context": context.to_dict(), "prior": None,
        "action": None, "domain_source_id": "g1", "storey_ref": "ifc-object:storey-1"}
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    child = subprocess.run([sys.executable, "-m", "adapters.blender_analysis_session",
                            str(request_path), str(result_path)],
                           cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert child.returncode == 0, child.stderr
    document = wire.load_json(result_path.read_text(encoding="utf-8"))
    assert document["payload"]["candidates"][0]["domain_kind"] == "authored_ifcspace"
    assert document["payload"]["candidates"][0]["source_id"] == "g1"


def test_wire_rejects_source_identity_conflict_with_snapshot():
    """Metadata cannot claim a different source after recomputing a valid digest."""
    from ..adapters import blender_analysis_result_wire as wire
    _, document = _compact_document()
    document["identity"]["request_source_fingerprint"] = "different-source"
    document["identity"]["project_source_identity"] = {"project_global_id": "different-project", "ifc_source_identity": "different.ifc"}
    document["digest"] = wire.document_digest(document)
    with pytest.raises(ValueError, match="source identity"):
        wire.list_analysis_results([document])


def test_domain_wire_rejects_boolean_plane_revision():
    """Domain diagnostics use strict non-boolean revision identity."""
    from ..adapters import blender_analysis_result_wire as wire
    from ..adapters import blender_analysis_session as service
    result = service._serialize_domain_result(evaluate_domain_request(enclosed_scene(),
        context=StructuralContext.from_plane(_plane()), prior=None, action=None), result_id="domain-bool",
        binding={"plane_uuid": "structural:fixture", "plane_revision": 1})
    result["identity"]["plane_revision"] = True
    result["binding"]["plane_revision"] = True
    result["digest"] = wire.document_digest(result)
    with pytest.raises(ValueError, match="plane revision"):
        wire.list_analysis_results([result])


def test_handoff_returns_exact_qualified_mesh_without_retriangulation():
    """Authored geometry reaches the consumer as the original object."""
    scene = _scene()
    frame = {"analysis_plane": scene.context.analysis_plane, "units": "m", "datum_m": 0., "cut_height_m": 1.5}
    args = dict(candidates=(), expected_session_revision=None, expected_source_revision=None, frame_request=frame)
    first = domain_handoff(scene, session_state=None, action=None, **args)
    item = first["candidates"][0]
    action = {"kind": "confirm", "action_id": "confirm", "actor": "user", "time": "now", "reason": "explicit", "candidate_version_id": item["version_id"], "expected_candidate_identity": item["identity"], "expected_session_revision": first["session_revision"], "expected_source_revision": first["provenance"]["source_revision"], "expected_plane_identity": first["provenance"]["frame_id"], "expected_request_identity": first["provenance"]["request_id"], "acknowledged_conflict_ids": []}
    args.update(expected_session_revision=first["session_revision"], expected_source_revision=first["provenance"]["source_revision"])
    result = domain_handoff(scene, session_state=first["session_state"], action=action, **args)
    assert result["domain_geometries"][0] is scene.geometries[0]
    assert first["domain_geometries"] == ()


def test_reducer_bindings_use_stable_structural_source_and_frame():
    """Actual reducer provenance ignores full occupancy plane state."""
    live = load_bonsai_capture(capture("wall", "furniture"), plane=_plane())
    context = StructuralContext.from_plane(_plane())
    first = evaluate_domain_request(live.scene, context=context, prior=None, action=None)
    changed = replace(live.scene, context=replace(live.scene.context, analysis_plane=_plane(origin=(0, 0, 99), revision=8)))
    second = evaluate_domain_request(changed, context=context, prior=first, action=None)
    assert first["provenance"] == second["provenance"]
    assert first["source_count"] == 1
    assert first["analysis_domain"] is None
    assert first["domain_geometries"] == ()


def test_authored_ifcspace_domain_session_uses_exact_source_and_storey(monkeypatch):
    """Existing domain session confirms a verified IfcSpace with stable scope facts."""
    from ..adapters.blender_analysis_capture import CanonicalCaptureInput
    data = capture("space", "wall", "furniture").to_dict()
    data["records"][0].update(ifc_class="IfcSpace", role="space",
                               level_ref="ifc-object:storey-1",
                               container_refs=["ifc-object:storey-1"])
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    context = StructuralContext.from_plane(_plane())
    from ..adapters import blender_analysis_session as service
    def reject_b4(*args, **kwargs):
        """A verified native Space must remain usable when B4 preparation is unavailable."""
        raise AssertionError("native Space adoption invoked B4")
    monkeypatch.setattr(service, "_analysis_scene_view_with_semantic_enclosure", reject_b4)
    initial = evaluate_domain_request(live.scene, context=context, prior=None, action=None,
                                      domain_source_id="g1", storey_ref="ifc-object:storey-1")
    assert initial["candidates"][0]["domain_kind"] == "authored_ifcspace"
    assert len(initial["candidates"]) == 1 and initial["b4_diagnostics"] is None
    active = evaluate_domain_request(live.scene, context=context, prior=initial,
                                     action=confirmation(initial), domain_source_id="g1",
                                     storey_ref="ifc-object:storey-1")
    assert active["current"]["status"] == "active"
    assert active["analysis_domain"].source_id == "g1"
    assert active["support_status"] == "unbound"


def test_authored_workflow_carries_observed_space_before_and_after_confirmation():
    """Adoption observes geometry without granting consent and preserves it through the same reducer."""
    from ..adapters import blender_analysis_session as service
    from ..adapters.blender_analysis_capture import CanonicalCaptureInput
    data = capture("space").to_dict()
    data["records"][0].update(ifc_class="IfcSpace", level_ref="ifc-object:storey-1",
                               container_refs=["ifc-object:storey-1"])
    payload = {"kind": "domain_session", "canonical_capture": data,
        "job_binding": {"job_id": "adopt-job"}, "context": StructuralContext.from_plane(_plane()).to_dict(),
        "domain_source_id": "g1", "storey_ref": "ifc-object:storey-1", "prior": None, "action": None}
    first = service._execute_workflow_payload(payload)
    binding = first["binding"]["space_binding"]
    assert binding["origin"] == "adopted" and binding["source_id"] == "ifc-object:g1"
    assert first["payload"]["confirmation_binding"] is None
    payload.update(prior=first["payload"], action=confirmation(first["payload"]))
    active = service._execute_workflow_payload(payload)
    assert active["binding"]["space_binding"] == binding
    assert active["payload"]["confirmation_binding"]
    payload["job_binding"]["space_binding"] = {**binding, "geometry_digest": "0" * 64}
    with pytest.raises(ValueError, match="Space|space.*changed"):
        service._execute_workflow_payload(payload)


def test_domain_workflow_independent_of_free_space_request(monkeypatch):
    """B4 invocation never calls the occupancy executor."""
    from ..features import analysis_requests
    def fail(*args, **kwargs):
        """Fail if the structural service starts free-space computation."""
        raise AssertionError("occupancy executor called")
    monkeypatch.setattr(analysis_requests, "execute_analysis_request", fail)
    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    result = evaluate_domain_request(scene, context=context, prior=None, action=None)
    selected = evaluate_domain_request(scene, context=context, prior=result,
        action={"kind": "select", "candidate_version_id": result["candidates"][0]["version_id"]})
    active = evaluate_domain_request(scene, context=context, prior=selected, action=confirmation(selected))
    assert active["current"]["status"] == "active"
    assert {"apertures", "current", "attempt", "candidates", "source_count", "geometry_count", "scenario", "tolerance_mm2"} <= result.keys()


def enclosed_scene():
    """Make a hand-checked four-wall enclosure with a 3.5 by 3.5 interior."""
    from .test_analysis_requests import _object
    walls = [_object(str(i), bounds, role="wall") for i, bounds in enumerate((
        (0, 0, 0, 4, .25, 3), (0, 3.75, 0, 4, 4, 3),
        (0, .25, 0, .25, 3.75, 3), (3.75, .25, 0, 4, 3.75, 3)))]
    return replace(_scene(*walls), analysis_domain=None)


def selected_wall_scene(*, remote=True, column=False, plane=None):
    """Build a selected perimeter with one unselected divider and optional remote room."""
    from .test_analysis_requests import _object

    definitions = [
        ("south", (0, 0, 0, 4, .25, 3)),
        ("north", (0, 3.75, 0, 4, 4, 3)),
        ("west", (0, .25, 0, .25, 3.75, 3)),
        ("east", (3.75, .25, 0, 4, 3.75, 3)),
        ("divider", (1.875, .25, 0, 2.125, 3.75, 3)),
    ]
    if remote:
        definitions.extend([
            ("remote-south", (10, 0, 0, 14, .25, 3)),
            ("remote-north", (10, 3.75, 0, 14, 4, 3)),
            ("remote-west", (10, .25, 0, 10.25, 3.75, 3)),
            ("remote-east", (13.75, .25, 0, 14, 3.75, 3)),
        ])
    if column:
        definitions.append(("column", (.75, 1.5, 0, 1.0, 1.75, 3)))
    objects = [
        _object(f"ifc-object:{name}", bounds, role="column" if name == "column" else "wall",
                source_id=name, source_class="IfcColumn" if name == "column" else "IfcWall")
        for name, bounds in definitions
    ]
    scene = replace(_scene(*objects), analysis_domain=None)
    return replace(scene, context=replace(scene.context, analysis_plane=plane)) if plane is not None else scene


def selected_wall_refs():
    """Return the canonical perimeter identities used by selected-wall regressions."""
    return tuple(sorted(f"ifc-object:{name}" for name in ("south", "north", "west", "east")))


def test_selected_wall_scope_keeps_divider_and_excludes_remote_room():
    """Selected perimeter walls limit B4 while an unselected divider still creates two rooms."""
    scene = selected_wall_scene()
    context = StructuralContext.from_plane(scene.context.analysis_plane, storey_ref="ifc-object:S1",
                                           selected_wall_refs=selected_wall_refs())

    result = evaluate_domain_request(scene, context=context, prior=None, action=None)

    assert sorted(candidate["area_m2"] for candidate in result["candidates"]) == pytest.approx([5.6875, 5.6875])
    assert result["source_count"] == result["geometry_count"] == 5
    assert result["selected_wall_scope"]["selected_wall_refs"] == selected_wall_refs()
    assert result["selected_wall_scope"]["base_source_count"] == 9
    assert result["selected_wall_scope"]["local_source_count"] == 5
    from ..adapters.blender_analysis_capture import digest
    from ..adapters.bonsai_live import structural_b4_view
    from ..features._analysis_domain_handoff import structural_source_facts
    base = structural_b4_view(scene, context=context, storey_ref=context.storey_ref)
    assert result["provenance"]["source_revision"] == digest(structural_source_facts(base))


def test_selected_wall_scope_uses_analysis_plane_local_bounds():
    """Cheap filtering uses the same translated and rotated plane-local XY coordinates as B4."""
    plane = _plane(origin=(100, 200, 0), basis=((0, 1, 0), (-1, 0, 0), (0, 0, 1)))
    original = selected_wall_scene(plane=plane)
    transformed = []
    for source, mesh in zip(original.source_objects, original.geometries[1:]):
        vertices = tuple((100 - y, 200 + x, z) for x, y, z in mesh.vertices)
        transformed.append((source, replace(mesh, vertices=vertices)))
    scene = replace(original, source_objects=tuple(source for source, _ in transformed),
                    geometries=(original.geometries[0],) + tuple(mesh for _, mesh in transformed))
    context = StructuralContext.from_plane(plane, storey_ref="ifc-object:S1",
                                           selected_wall_refs=reversed(selected_wall_refs()))

    result = evaluate_domain_request(scene, context=context, prior=None, action=None)

    assert tuple(result["selected_wall_scope"]["selected_wall_refs"]) == selected_wall_refs()
    assert sorted(candidate["area_m2"] for candidate in result["candidates"]) == pytest.approx([5.6875, 5.6875])


def test_selected_wall_scope_refuses_open_missing_or_nonwall_sources():
    """Malformed selected scope never falls back to a whole-storey candidate run."""
    scene = selected_wall_scene(remote=False)
    cases = [
        selected_wall_refs()[:-1],
        (*selected_wall_refs()[:-1], "ifc-object:missing"),
        (*selected_wall_refs()[:-1], "ifc-object:column"),
    ]
    column_scene = selected_wall_scene(remote=False, column=True)
    for refs, current in zip(cases, (scene, scene, column_scene)):
        with pytest.raises(ValueError, match="selected wall|enclosed scope"):
            evaluate_domain_request(current, context=StructuralContext.from_plane(
                current.context.analysis_plane, storey_ref="ifc-object:S1",
                selected_wall_refs=refs), prior=None, action=None)


def test_selected_wall_scope_keeps_detached_column_as_occupancy_without_hole():
    """A detached in-area column survives local inference without becoming a room hole."""
    scene = selected_wall_scene(remote=False, column=True)
    context = StructuralContext.from_plane(scene.context.analysis_plane, storey_ref="ifc-object:S1",
                                           selected_wall_refs=selected_wall_refs())

    result = evaluate_domain_request(scene, context=context, prior=None, action=None)

    assert sum(candidate["holes"] for candidate in result["candidates"]) == 0
    assert any("ifc-object:column" in scope["occupancy_source_refs"]
               for scope in result["b4_diagnostics"]["scope_proposals"])


def test_selected_wall_scope_change_and_tolerance_change_invalidate_consent():
    """Frozen wall identity and current structural parameters both participate in consent freshness."""
    scene = selected_wall_scene(remote=False)
    context = StructuralContext.from_plane(
        scene.context.analysis_plane, storey_ref="ifc-object:S1",
        selected_wall_refs=selected_wall_refs())
    first = evaluate_domain_request(scene, context=context, prior=None, action=None)
    active = evaluate_domain_request(scene, context=context, prior=first, action=confirmation(first))
    changed_scope = replace(context, selected_wall_refs=selected_wall_refs() + ("ifc-object:divider",))
    scope_stale = evaluate_domain_request(scene, context=changed_scope, prior=active, action=None)
    changed_tolerance = replace(context, b4_parameters={**context.b4_parameters, "tolerance_mm2": 0})
    tolerance_stale = evaluate_domain_request(scene, context=changed_tolerance, prior=active, action=None)
    assert active["current"]["status"] == "active"
    assert scope_stale["current"]["status"] == "not_available"
    assert tolerance_stale["current"]["status"] == "not_available"


def test_selected_wall_scope_refuses_missing_mesh_wrong_storey_and_existing_domain():
    """Selected mode refuses incomplete source proof, explicit other-storey walls, and authored domains."""
    scene = selected_wall_scene(remote=False)
    context = StructuralContext.from_plane(
        scene.context.analysis_plane, storey_ref="ifc-object:S1",
        selected_wall_refs=selected_wall_refs())
    missing_ref = next(source.geometry_refs[0] for source in scene.source_objects
                       if source.id == selected_wall_refs()[0])
    missing = replace(scene, geometries=tuple(mesh for mesh in scene.geometries if mesh.id != missing_ref))
    with pytest.raises(ValueError, match="selected wall"):
        evaluate_domain_request(missing, context=context, prior=None, action=None)
    other_storey = replace(scene, source_objects=tuple(
        replace(source, level_ref="ifc-object:S2", container_refs=("ifc-object:S2",))
        if source.id in selected_wall_refs() else source for source in scene.source_objects))
    with pytest.raises(ValueError, match="selected wall"):
        evaluate_domain_request(other_storey, context=context, prior=None, action=None)
    with pytest.raises(ValueError, match="authored IfcSpace"):
        evaluate_domain_request(replace(scene, analysis_domain=_scene().analysis_domain),
                                context=context, prior=None, action=None)


def test_selected_wall_local_pass_keeps_opening_relation_sources_beyond_bounds():
    """A retained opening carries its related filling source even when source bounds are contradictory."""
    from shapely.geometry import box
    from ..adapters import blender_analysis_session as service
    from ..features.scene_contract import SourceOpening
    from .test_analysis_requests import _object

    scene = selected_wall_scene(remote=False)
    filling, filling_mesh = _object(
        "ifc-object:door", (20, 20, 0, 21, 21, 2), role="door",
        source_id="door", source_class="IfcDoor")
    _, opening_mesh = _object("opening-evidence", (1, 1, 0, 1.2, 1.2, 2), role="opening")
    opening = SourceOpening(
        id="ifc-opening:opening", source_id="opening", host_refs=(selected_wall_refs()[0],),
        geometry_refs=(opening_mesh.id,), opening_kind="door",
        provenance={"filling_source_refs": (filling.id,)})
    scene = replace(scene, source_objects=scene.source_objects + (filling,),
                    geometries=scene.geometries + (filling_mesh, opening_mesh), openings=(opening,))
    child = service._local_structural_child(
        scene, box(.25, .25, 3.75, 3.75), scene.context.analysis_plane, selected_wall_refs())
    assert filling.id in {source.id for source in child.source_objects}
    assert opening.id in {item.id for item in child.openings}


def test_selected_wall_candidate_filter_never_clips_crossing_polygon():
    """Coverage filtering drops a crossing candidate whole instead of clipping it to the work area."""
    from shapely.geometry import box, mapping
    from ..adapters import blender_analysis_session as service

    inside = {"id": "inside", "geometry": {"geojson": mapping(box(0, 0, 1, 1))},
              "local_unresolved_aperture_refs": []}
    crossing = {"id": "crossing", "geometry": {"geojson": mapping(box(.5, .5, 2, 2))},
                "local_unresolved_aperture_refs": []}
    filtered = service._covered_b2({"scope_proposals": [inside, crossing],
                                    "enclosure_contours": [], "apertures": [], "treatments": []},
                                   box(0, 0, 1, 1))
    assert [item["id"] for item in filtered["scope_proposals"]] == ["inside"]


def confirmation(result, *, action_id="confirm"):
    """Target the exact observed reducer candidate without implicit consent."""
    item = result["candidates"][0]
    return {"kind": "confirm", "action_id": action_id, "actor": "user", "time": "now", "reason": "explicit",
            "candidate_version_id": item["version_id"], "expected_candidate_identity": item["identity"],
            "expected_session_revision": result["session_revision"],
            "expected_source_revision": result["provenance"]["source_revision"],
            "expected_plane_identity": result["provenance"]["frame_id"],
            "expected_request_identity": result["provenance"]["request_id"], "acknowledged_conflict_ids": []}


def test_select_does_not_confirm():
    """Select cannot fabricate a domain or erase the separate current/attempt states."""
    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    initial = evaluate_domain_request(scene, context=context, prior=None, action=None)
    selected = evaluate_domain_request(scene, context=context, prior=initial,
        action={"kind": "select", "candidate_version_id": initial["candidates"][0]["version_id"]})
    assert selected["attempt"]["status"] == "selected"
    assert selected["current"]["status"] == "not_available"
    assert selected["analysis_domain"] is None and selected["confirmation_binding"] is None
    assert selected["domain_geometries"] == ()


def test_inferred_handoff_reuses_one_qualified_mesh(monkeypatch):
    """Confirmation qualification and consumption share one tessellation and mesh object."""
    from ..features import _analysis_domain_handoff as reducer
    from ..features import neutral_scene_views
    meshes, children = [], []
    original_mesh, original_view = reducer._inferred_mesh, neutral_scene_views.analysis_scene_view
    def mesh(*args, **kwargs):
        """Observe actual generated meshes while retaining real qualification."""
        result = original_mesh(*args, **kwargs)
        meshes.append(result)
        return result
    def view(scene, **kwargs):
        """Observe the exact child consumed by the existing occupancy view."""
        children.append(scene)
        return original_view(scene, **kwargs)
    monkeypatch.setattr(reducer, "_inferred_mesh", mesh)
    monkeypatch.setattr(neutral_scene_views, "analysis_scene_view", view)
    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    first = evaluate_domain_request(scene, context=context, prior=None, action=None)
    active = evaluate_domain_request(scene, context=context, prior=first, action=confirmation(first))
    assert active["current"]["status"] == "active"
    assert active["analysis_domain"].source_id is None
    assert len(meshes) == 1
    assert active["domain_geometries"][0] is meshes[0]
    assert any(mesh is meshes[0] for mesh in children[-1].geometries)
    assert active.to_dict()["domain_geometries"][0] == meshes[0].to_dict()


def test_domain_session_preserves_existing_b4_payload():
    """Full authoritative diagnostics survive service enrichment and JSON transport."""
    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    result = evaluate_domain_request(scene, context=context, prior=None, action=None)
    assert result["source_count"] == result["geometry_count"] == 4
    assert result["candidates"][0]["area_m2"] == pytest.approx(12.25)
    assert result["candidates"][0]["holes"] == 0
    assert all(.25 < coordinate < 3.75 for coordinate in result["candidates"][0]["label_xy"])
    assert result["tolerance_mm2"] == 1
    assert result["b4_diagnostics"]["request"]["aperture_residual_tolerance_m2"] == 1e-6
    assert result["apertures"] == result["b4_diagnostics"]["apertures"]
    assert result["ignored_tiny_residual_count"] == 0
    assert result["handoff_executed"] is False
    assert result["scenario"] == "default closed doors/windows; observed leaf states unknown"
    assert {"source_identity", "provenance", "attempt", "current", "downstream", "events", "status"} <= result.keys()
    import json
    json.dumps(result.to_dict(), allow_nan=False)


def test_confirmed_domain_affordance_geometry_round_trips_as_plain_records():
    """Confirmed Domain preview Rect records survive strict wire serialization and restore."""
    import json
    from ..adapters import blender_analysis_session as service
    from ..adapters import blender_analysis_result_wire as wire

    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    initial = evaluate_domain_request(scene, context=context, prior=None, action=None)
    active = evaluate_domain_request(scene, context=context, prior=initial, action=confirmation(initial))
    document = service._serialize_domain_result(active, result_id="domain-rect", binding={})
    encoded = wire.canonical_json(document)
    restored = wire.load_json(encoded)
    wire.validate_document(restored)
    rect = restored["payload"]["preview"]["physical_occupancy"][0]["rect"]
    source_rect = active.to_dict()["preview"]["physical_occupancy"][0]["rect"]
    assert rect == source_rect
    assert "Rect" not in encoded
    assert json.loads(encoded)["payload"]["preview"]["physical_occupancy"][0]["rect"] == rect


def test_domain_transport_rejects_unknown_to_dict_object():
    """Domain transport does not invoke arbitrary object serializers."""
    from ..adapters import blender_analysis_session as service

    class Unknown:
        """Object that must remain outside the closed transport contract."""
        def to_dict(self):
            """Expose a tempting but unsupported conversion hook."""
            return {"unexpected": True}

    with pytest.raises(ValueError, match="unsupported Domain transport value"):
        service._transport(Unknown())


def test_domain_transport_rejects_nonfinite_rect():
    """Rect transport rejects NaN coordinates before JSON encoding."""
    from ..adapters import blender_analysis_session as service
    from ..features.affordance.models import Rect

    with pytest.raises(ValueError, match="Rect coordinates"):
        service._transport(Rect(float("nan"), 0, 1, 1))


def test_domain_transport_rejects_nonfinite_polygon():
    """Polygon transport rejects infinite point coordinates before JSON encoding."""
    from ..adapters import blender_analysis_session as service
    from ..features.affordance.models import Polygon

    with pytest.raises(ValueError, match="Polygon point coordinates"):
        service._transport(Polygon(((0, 0), (float("inf"), 1), (1, 1))))


def test_unified_domain_parity_preserves_all_b4_controls_and_diagnostics():
    """The unified Domain section can render every approved B4 service fact."""
    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    result = evaluate_domain_request(scene, context=context, prior=None, action=None).to_dict()
    assert {"source_count", "geometry_count", "tolerance_mm2", "scenario", "candidates",
            "current", "attempt", "apertures", "ignored_tiny_residual_count", "b4_diagnostics",
            "provenance", "events", "status"} <= result.keys()
    candidate = result["candidates"][0]
    assert {"id", "version_id", "area_m2", "holes", "label_xy", "reason", "outline"} <= candidate.keys()
    assert result["b4_diagnostics"]["request"]["analysis_plane"]
    assert result["scenario"] == "default closed doors/windows; observed leaf states unknown"


def test_tolerance_drift_cannot_restore_aba_confirmation():
    """Observing different tolerance permanently invalidates earlier consent."""
    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    first = evaluate_domain_request(scene, context=context, prior=None, action=None)
    active = evaluate_domain_request(scene, context=context, prior=first, action=confirmation(first))
    changed = replace(context, b4_parameters={**context.b4_parameters, "tolerance_mm2": 0})
    invalidated = evaluate_domain_request(scene, context=changed, prior=active, action=None)
    restored = evaluate_domain_request(scene, context=context, prior=invalidated, action=None)
    assert active["current"]["status"] == "active"
    assert invalidated["current"]["status"] == restored["current"]["status"] == "not_available"


@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf"), True])
def test_tolerance_rejects_invalid_values(invalid):
    """Reject malformed tolerance before structural computation or reducer mutation."""
    with pytest.raises(ValueError):
        context = StructuralContext.from_plane(_plane(), b4_parameters={"tolerance_mm2": invalid})
        evaluate_domain_request(enclosed_scene(), context=context, prior=None, action=None)



def test_reducer_receives_structural_facts_and_actual_frame(monkeypatch):
    """Furniture, recapture and occupancy pose cannot invalidate structural consent."""
    from ..adapters import blender_analysis_session as service
    from ..features._analysis_domain_handoff import structural_source_facts
    from ..adapters.blender_analysis_capture import digest
    from .test_analysis_requests import _object
    calls = []
    original = service.domain_handoff
    def observe(scene, **kwargs):
        """Inspect the real reducer binding and continue real execution."""
        calls.append((scene, kwargs))
        return original(scene, **kwargs)
    monkeypatch.setattr(service, "domain_handoff", observe)
    scene, context = enclosed_scene(), StructuralContext.from_plane(_plane())
    first = service.evaluate_domain_request(scene, context=context, prior=None, action=None)
    active = service.evaluate_domain_request(scene, context=context, prior=first, action=confirmation(first))
    furniture, mesh = _object("chair", (.5, .5, 0, 1, 1, 1))
    changed = replace(scene, source_objects=tuple(reversed(scene.source_objects)) + (furniture,),
                      geometries=tuple(reversed(scene.geometries)) + (mesh,),
                      context=replace(scene.context, analysis_plane=_plane(origin=(0, 0, 99), revision=9, name="renamed")))
    same = service.evaluate_domain_request(changed, context=context, prior=active, action=None)
    assert same["current"]["status"] == "active"
    assert calls[0][1]["source_revision"] == calls[-1][1]["source_revision"]
    assert calls[-1][1]["source_revision"] == digest(structural_source_facts(calls[-1][0]))
    assert calls[-1][1]["frame_id"] == context.structural_frame_key
    assert calls[-1][0].context.analysis_plane.origin == (0, 0, 0)
    assert calls[-1][1]["b2_request"]["cut_height_m"] == 1.5
    structural = replace(scene, geometries=tuple(replace(mesh, vertices=tuple(
        (x + .125, y, z) for x, y, z in mesh.vertices)) if mesh.id == "mesh:0" else mesh
        for mesh in scene.geometries))
    drift = service.evaluate_domain_request(structural, context=context, prior=same, action=None)
    assert calls[-1][1]["source_revision"] != calls[0][1]["source_revision"]
    assert drift["current"]["status"] == "not_available"
    frame = replace(context, xy_origin_m=(1, 0))
    service.evaluate_domain_request(scene, context=frame, prior=active, action=None)
    assert calls[-1][1]["frame_id"] != calls[0][1]["frame_id"]
    assert calls[-1][0].context.analysis_plane.origin == (1, 0, 0)


def test_live_execution_uses_exact_mesh_and_request_scoped_support(monkeypatch):
    """Unbound floors occupy; explicit validated support excludes only that one source."""
    from ..adapters.blender_analysis_session import execute_live_analysis
    from ..adapters.bonsai_live import SupportBinding, geometry_digest
    from ..features import analysis_requests
    from .test_analysis_requests import _request
    from ..features.scene_contract import AnalysisDomain
    live = load_bonsai_capture(capture("slab"), plane=_plane())
    qualified = _scene().geometries[0]
    domain = AnalysisDomain("confirmed", geometry_refs=(qualified.id,), source_id=None, selection_method="confirmed")
    request = _request(replace(live.scene, analysis_domain=domain))
    seen = []
    original = analysis_requests.execute_analysis_request
    def observe(scene, request):
        """Inspect handoff identity while executing the real field."""
        seen.append(scene)
        return original(scene, request)
    monkeypatch.setattr(analysis_requests, "execute_analysis_request", observe)
    raw = execute_live_analysis(live.scene, request=request, domain_geometries=(qualified,))
    assert raw.field.evaluate((0, 0), raw.query).value is True
    source = live.scene.source_objects[0]
    binding = SupportBinding(source.id, "project", "IfcSlab", source.geometry_refs,
        geometry_digest(live.scene, source), live.capture_fingerprint, "user-consent")
    supported = execute_live_analysis(live.scene, request=request, domain_geometries=(qualified,), support_binding=binding)
    assert supported.field.evaluate((0, 0), supported.query).value is False
    assert seen[-1].analysis_domain.source_id == "g1"
    assert next(mesh for mesh in seen[-1].geometries if mesh.id == qualified.id) is qualified
    assert request.domain.source_id is None and live.scene.analysis_domain is None
    stale = replace(binding, geometry_digest="stale")
    refused = execute_live_analysis(live.scene, request=request, domain_geometries=(qualified,), support_binding=stale)
    assert refused.field.evaluate((0, 0), refused.query).value is True
    with pytest.raises(ValueError, match="refs"):
        execute_live_analysis(live.scene, request=request, domain_geometries=())


def test_authored_space_confirmation_reaches_workflow_child_with_exact_support():
    """The serialized authored session drives the real child while preserving a low chair."""
    from ..adapters import blender_analysis_session as service
    from ..adapters.blender_analysis_capture import CanonicalCaptureInput
    from .test_analysis_requests import _object, _request

    data = capture("space", "slab", "furniture").to_dict()
    data["records"][0].update(ifc_class="IfcSpace", role="space",
                               level_ref="ifc-object:storey-1",
                               container_refs=["ifc-object:storey-1"])
    data["records"][1].update(ifc_class="IfcSlab", role="slab",
                               level_ref="ifc-object:storey-1",
                               container_refs=["ifc-object:storey-1"])
    data["records"][2].update(ifc_class="IfcFurniture", role="furniture",
                               level_ref="ifc-object:storey-1",
                               container_refs=["ifc-object:storey-1"])
    _, low_chair = _object("chair", (0, 0, 0, 1, 1, .5), role="furniture")
    data["records"][2]["mesh"] = low_chair.to_dict()
    plane = _plane(origin=(0, 0, 2), revision=4)
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=plane)
    context = StructuralContext.from_plane(plane)
    initial = evaluate_domain_request(live.scene, context=context, prior=None, action=None,
                                      domain_source_id="g1", storey_ref="ifc-object:storey-1")
    active = evaluate_domain_request(
        live.scene, context=context, prior=initial, action=confirmation(initial),
        domain_source_id="g1", storey_ref="ifc-object:storey-1", support_source_id="g2")
    assert active["current"]["status"] == "active"
    assert active["analysis_domain"].source_id == "g1"
    assert active["support_binding"]["source_object_id"] == "ifc-object:g2"

    domain_document = service._serialize_domain_result(active, result_id="domain-job",
        binding={"plane_uuid": plane.identity, "plane_revision": plane.revision})
    domain_binding = {
        **domain_document["binding"], "domain_request_id": active["domain_request_identity"],
        "domain_session_revision": active["session_revision"],
        "confirmation_binding": active["confirmation_binding"],
        "structural_context": context.to_dict(), "domain_source_id": "g1",
        "storey_ref": "ifc-object:storey-1",
    }
    domain_scene = replace(live.scene, analysis_domain=active["analysis_domain"])
    request = _request(domain_scene)
    space_ref = live.scene.source_objects[0].geometry_refs[0]
    space_mesh = next(mesh for mesh in live.scene.geometries if mesh.id == space_ref)
    payload = {
        "kind": "free_space_run", "job_binding": {"job_id": "free-job", **domain_binding},
        "canonical_capture": data, "request": request.to_dict(),
        "domain_geometries": [space_mesh.to_dict()],
        "support_binding": active["support_binding"], "legacy_bindings": [],
    }
    document = service._execute_workflow_payload(payload)
    sample = service.reconstruct_field_sample(document, row=0, column=0)
    assert sample.value is True
    assert "ifc-object:g3" in sample.source_ids
    assert "ifc-object:g2" not in sample.source_ids

    for invalid_storey in (None, "ifc-object:storey-2"):
        with pytest.raises(ValueError, match="storey"):
            evaluate_domain_request(live.scene, context=context, prior=None, action=None,
                                    domain_source_id="g1", storey_ref=invalid_storey)


@pytest.mark.parametrize(
    "case,level_ref,container_refs,bounds,missing,expected_status,expected_reason",
    [
        ("other_storey_disjoint", "ifc-object:storey-B", ("ifc-object:storey-B",),
         (0, 0, 2, 1, 1, 2.5), False, "established", "authored_space_other_storey_z_disjoint"),
        ("other_storey_crossing", "ifc-object:storey-B", ("ifc-object:storey-B",),
         (0, 0, .5, 1, 1, 1.5), False, "established", "qualified_original_geometry"),
        ("same_storey_low", "ifc-object:storey-A", ("ifc-object:storey-A",),
         (0, 0, 0, 1, 1, .5), False, "established", "qualified_original_geometry"),
        ("uncontained_disjoint", "ifc-object:storey-B", (),
         (0, 0, 2, 1, 1, 2.5), False, "established", "qualified_original_geometry"),
        ("other_storey_missing", "ifc-object:storey-B", ("ifc-object:storey-B",),
         None, True, "unknown", "missing_geometry"),
    ],
)
def test_authored_space_child_scope_keeps_ambiguous_physical_facts(
    case, level_ref, container_refs, bounds, missing, expected_status, expected_reason,
):
    """Only proven disjoint other-storey mass is scoped out in the request child."""
    from ..adapters.blender_analysis_capture import CanonicalCaptureInput
    from ..adapters.bonsai_live import authored_space_domain
    from ..adapters.blender_analysis_session import execute_live_analysis
    from .test_analysis_requests import _object, _request

    data = capture("space", "furniture").to_dict()
    data["records"][0].update(ifc_class="IfcSpace", role="space",
                               level_ref="ifc-object:storey-A",
                               container_refs=["ifc-object:storey-A"])
    data["records"][1].update(ifc_class="IfcFurniture", role="furniture",
                               level_ref=level_ref, container_refs=list(container_refs))
    _, space_mesh = _object("space", (0, 0, 0, 1, 1, 1), role="space")
    data["records"][0]["mesh"] = space_mesh.to_dict()
    if missing:
        data["records"][1]["mesh"] = None
    else:
        _, furniture_mesh = _object("furniture", bounds, role="furniture")
        data["records"][1]["mesh"] = furniture_mesh.to_dict()
    plane = _plane()
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=plane)
    original_scene = live.scene.to_dict()
    original_fingerprint = live.full_fingerprint
    domain = authored_space_domain(live.scene, "g1", storey_ref="ifc-object:storey-A")
    child_scene = replace(live.scene, analysis_domain=domain)
    request = _request(child_scene)
    exact_domain_mesh = next(mesh for mesh in live.scene.geometries if mesh.id == domain.geometry_refs[0])
    run = execute_live_analysis(live.scene, request=request, domain_geometries=(exact_domain_mesh,))
    assert live.scene.to_dict() == original_scene
    assert live.full_fingerprint == original_fingerprint
    sample = run.field.evaluate((0, 0), run.query)
    inventory = sample.provenance["physical_source_inventory"]
    furniture = next(item for item in inventory if item["source_object_id"] == "ifc-object:g2")
    assert sample.status.value == expected_status, case
    assert furniture["reason"] == expected_reason, case
    if case == "other_storey_disjoint":
        assert sample.value is False
        assert furniture["status"] == "scoped_out"
    else:
        if expected_status == "unknown":
            assert sample.value is None
        else:
            assert sample.value is True
        assert furniture["status"] == ("unknown" if missing else "original")


def test_legacy_b4_wrapper_delegates_to_independent_service():
    """Both canonical CLI transport and the old panel consume the complete B4 payload."""
    from ..scripts.design.live_domain.run_live_domain import evaluate
    data = capture("wall").to_dict()
    result = evaluate({"canonical_capture": data, "tolerance_mm2": 10})
    assert result["source_count"] == 1 and result["tolerance_mm2"] == 10
    assert result["b4_diagnostics"]["request"]["aperture_residual_tolerance_m2"] == 1e-5
    assert result["analysis_domain"] is None and result["domain_geometries"] == []
    assert result["source_identity"]["project_global_id"] == "project"


def test_b4_apertures_holes_and_conflicts_are_preserved():
    """The complete diagnostics retain significant residuals, holes and reducer conflicts."""
    from .test_neutral_scene_analysis_regression import _enclosure_scene
    scene = _enclosure_scene()
    context = StructuralContext.from_plane(scene.context.analysis_plane)
    first = evaluate_domain_request(scene, context=context, prior=None, action=None)
    assert len(first["apertures"]) == 1
    aperture = first["apertures"][0]
    assert aperture["geometry"]["area_m2"] == pytest.approx(.25)
    assert aperture["significant_residual"] is True
    assert {"host_ref", "affected_scope_ids", "scenario_closed"} <= aperture.keys()
    assert sum(item["holes"] for item in first["candidates"]) == 0
    assert first["b4_diagnostics"]["treatments"][0]["source_ref"] == "window"
    active = evaluate_domain_request(scene, context=context, prior=first, action=confirmation(first))
    changed = {**confirmation(first), "reason": "different-payload-same-id"}
    conflict = evaluate_domain_request(scene, context=context, prior=active, action=changed)
    assert conflict["attempt"]["reason"] == "conflicting_action_id"
    assert conflict["current"]["status"] == "conflict"
    assert conflict["session_state"]["conflict"] is True
    assert conflict["analysis_domain"] is None and conflict["domain_geometries"] == ()
    assert conflict.to_dict()["apertures"][0]["geometry"]["area_m2"] == pytest.approx(.25)
    ignored_context = replace(context, b4_parameters={**context.b4_parameters, "tolerance_mm2": 250001})
    ignored = evaluate_domain_request(scene, context=ignored_context, prior=None, action=None)
    assert ignored["ignored_tiny_residual_count"] == 1
    assert ignored["apertures"][0]["significant_residual"] is False


def test_structural_b4_view_filters_proven_other_storeys_conservatively():
    """Selected storey filtering excludes proven mismatches but keeps unknown facts."""
    from ..adapters.bonsai_live import structural_b4_view
    from .test_analysis_requests import _scene
    from .test_neutral_scene_analysis_regression import _enclosure_scene
    scene = _enclosure_scene()
    first, second = scene.source_objects[:2]
    scene = replace(scene, source_objects=(replace(first, level_ref="ifc-object:A", container_refs=("ifc-object:A",)),
                                           replace(second, level_ref="ifc-object:B", container_refs=("ifc-object:B",))))
    filtered = structural_b4_view(scene, context=StructuralContext.from_plane(scene.context.analysis_plane), storey_ref="ifc-object:A")
    assert all(source.level_ref != "ifc-object:B" for source in filtered.source_objects)


def test_elevated_selected_storey_survives_b4_confirmation_and_free_space_stale_check():
    """S7 datum, scope, consent, and child binding stay identical across both workflows."""
    from ..adapters import blender_analysis_session as service
    from ..adapters.blender_analysis_capture import CanonicalCaptureInput
    from .test_analysis_requests import _object, _request

    data = capture(*(["wall"] * 8)).to_dict()
    bounds = (
        (0, 0, 0, 4, .25, 3), (0, 3.75, 0, 4, 4, 3),
        (0, .25, 0, .25, 3.75, 3), (3.75, .25, 0, 4, 3.75, 3),
        (0, 0, 20, 4, .25, 23), (0, 3.75, 20, 4, 4, 23),
        (0, .25, 20, .25, 3.75, 23), (3.75, .25, 20, 4, 3.75, 23),
    )
    for index, (record, box) in enumerate(zip(data["records"], bounds)):
        storey = "S1" if index < 4 else "S7"
        _, mesh = _object(str(index), box, role="wall")
        record.update(mesh=mesh.to_dict(), level_ref=f"ifc-object:{storey}",
                      container_refs=[f"ifc-object:{storey}"])
    projection_plane = _plane(origin=(0, 0, 99), revision=4)
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=projection_plane)
    context = StructuralContext.from_plane(
        projection_plane, storey_ref="ifc-object:S7", datum_z_m=20.0, cut_z_m=21.5)

    initial = evaluate_domain_request(live.scene, context=context, prior=None, action=None)
    assert len(initial["candidates"]) == 1
    assert initial["candidates"][0]["storey_ref"] == "ifc-object:S7"
    assert initial["source_count"] == 4
    assert context.datum_z_m == 20.0
    assert context.analysis_plane.origin[2] == 0.0
    assert projection_plane.origin[2] == 99
    active = evaluate_domain_request(
        live.scene, context=context, prior=initial, action=confirmation(initial))
    assert active["current"]["status"] == "active"

    domain_scene = replace(live.scene, analysis_domain=active["analysis_domain"])
    payload = {
        "kind": "free_space_run",
        "job_binding": {
            "job_id": "s7-free", "domain_request_id": active["domain_request_identity"],
            "domain_session_revision": active["session_revision"],
            "confirmation_binding": active["confirmation_binding"],
            "structural_context": context.to_dict(),
        },
        "canonical_capture": data,
        "request": _request(domain_scene).to_dict(),
        "domain_geometries": [mesh.to_dict() for mesh in active["domain_geometries"]],
        "support_binding": None,
        "legacy_bindings": [],
    }
    document = service._execute_workflow_payload(payload)
    assert document["binding"]["structural_context"]["storey_ref"] == "ifc-object:S7"

    stale = service.wire.plain(payload)
    stale["job_binding"]["job_id"] = "s1-free"
    stale["job_binding"]["structural_context"].update(
        storey_ref="ifc-object:S1", datum_z_m=0.0, cut_z_m=1.5)
    with pytest.raises(ValueError, match="stale"):
        service._execute_workflow_payload(stale)


def test_selected_wall_confirmation_reaches_free_space_and_scope_mismatch_is_stale():
    """Serialized free-space consumes the exact selected scope and retains in-area column occupancy."""
    from ..adapters import blender_analysis_session as service
    from ..adapters.blender_analysis_capture import CanonicalCaptureInput
    from .test_analysis_requests import _object, _request

    roles = ["wall"] * 5 + ["furniture"]
    data = capture(*roles).to_dict()
    bounds = (
        (0, 0, 0, 4, .25, 3), (0, 3.75, 0, 4, 4, 3),
        (0, .25, 0, .25, 3.75, 3), (3.75, .25, 0, 4, 3.75, 3),
        (1.875, .25, 0, 2.125, 3.75, 3), (.75, 1.5, 0, 1.0, 1.75, 3),
    )
    for index, (record, box) in enumerate(zip(data["records"], bounds)):
        role = "column" if index == 5 else "wall"
        _, mesh = _object(str(index), box, role=role)
        record.update(mesh=mesh.to_dict(), role=role,
                      ifc_class="IfcColumn" if role == "column" else "IfcWall",
                      level_ref="ifc-object:S1", container_refs=["ifc-object:S1"])
    live = load_bonsai_capture(CanonicalCaptureInput(**data), plane=_plane())
    refs = tuple(sorted(f"ifc-object:g{index}" for index in range(1, 5)))
    context = StructuralContext.from_plane(
        _plane(), storey_ref="ifc-object:S1", selected_wall_refs=refs)
    initial = evaluate_domain_request(live.scene, context=context, prior=None, action=None)
    candidate = next(item for item in initial["candidates"] if item["label_xy"][0] < 2.0)
    action = confirmation(initial)
    action.update(candidate_version_id=candidate["version_id"],
                  expected_candidate_identity=candidate["identity"])
    active = evaluate_domain_request(live.scene, context=context, prior=initial, action=action)
    assert active["current"]["status"] == "active"

    domain_scene = replace(live.scene, analysis_domain=active["analysis_domain"])
    payload = {
        "kind": "free_space_run",
        "job_binding": {
            "job_id": "selected-free", "domain_request_id": active["domain_request_identity"],
            "domain_session_revision": active["session_revision"],
            "confirmation_binding": active["confirmation_binding"],
            "structural_context": context.to_dict(),
        },
        "canonical_capture": data,
        "request": _request(domain_scene).to_dict(),
        "domain_geometries": [mesh.to_dict() for mesh in active["domain_geometries"]],
        "support_binding": None,
        "legacy_bindings": [],
    }
    document = service._execute_workflow_payload(payload)
    assert tuple(document["binding"]["structural_context"]["selected_wall_refs"]) == refs
    samples = [service.reconstruct_field_sample(document, row=row, column=column)
               for row in range(4) for column in range(4)]
    assert any("ifc-object:g6" in sample.source_ids and sample.value is True
               and sample.explanation == "occupied by pre-resolved physical geometry"
               for sample in samples)

    stale = service.wire.plain(payload)
    stale["job_binding"]["job_id"] = "selected-stale"
    stale["job_binding"]["structural_context"]["selected_wall_refs"].append("ifc-object:g5")
    with pytest.raises(ValueError, match="stale"):
        service._execute_workflow_payload(stale)


def test_b4_legacy_aperture_area_accessor_is_preserved():
    """Existing B4 callers can still read the measured top-level aperture area."""
    from .test_neutral_scene_analysis_regression import _enclosure_scene
    scene = _enclosure_scene()
    result = evaluate_domain_request(scene, context=StructuralContext.from_plane(scene.context.analysis_plane), prior=None, action=None)
    assert result["apertures"][0]["area_m2"] == pytest.approx(.25)
    assert result["b4_diagnostics"]["apertures"][0]["geometry"]["area_m2"] == pytest.approx(.25)
    assert result.to_dict()["apertures"][0]["area_m2"] == pytest.approx(.25)

