"""Main-thread capture and one owned Pixi child; no geometry engine imports.

T4 registers native handlers/timers and builds staged Text/mesh artifacts. Its
handlers call invalidate_runtime; its timer calls poll_job. Persistent documents
never contain RuntimeJob or automatically start a child on restore.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
from threading import current_thread, main_thread
from time import monotonic, perf_counter
import uuid

from adapters import blender_analysis_capture as capture
from adapters import blender_analysis_result_wire as wire

BUDGET_SECONDS = .050
LOG_LIMIT = 1024 * 1024
CANCEL_GRACE_SECONDS = 2.0
RESOURCE_PATHS = ("pixi.toml", "pixi.lock", "adapters/blender_analysis_session.py",
    "blender_addon/order_analyzer_ui/runtime.py", "blender_addon/order_analyzer_ui/__init__.py",
    "adapters/bonsai_analysis_plane.py", "adapters/bonsai_space_authoring.py", "adapters/ifc_bonsai.py",
    "adapters/blender_analysis_result_wire.py", "adapters/blender_analysis_capture.py", "adapters/bonsai_live.py",
    "features/analysis_requests.py", "features/field_core.py", "features/free_space_field.py",
    "features/_analysis_domain_handoff.py", "features/scene_contract.py", "features/section_views.py",
    "features/geometry_substitutes.py", "features/geometry_views.py", "features/neutral_scene_views.py",
    "features/analysis_substitute_discovery.py", "features/substitute_contract.py",
    "scripts/design/group_level/trend_substitute_registry.json")


@dataclass
class RuntimeJob:
    """One temporary native/process owner; it is never serialized or resumed."""

    job_id: str
    root: Path
    context: object
    payload: dict
    directory: Path
    epoch: int
    runtime_session: str
    scene_file_token: str
    lifecycle: str = "capturing"
    stage: str = "capture"
    capture_job: object = None
    captured: capture.CanonicalCaptureInput | dict | None = None
    process: object = None
    logs: list = field(default_factory=list)
    iterator: object = None
    observation_start: dict | None = None
    observation_before: dict | None = None
    observation_after: dict | None = None
    binding: dict = field(default_factory=dict)
    candidate: object = None
    started: float = field(default_factory=monotonic)
    cancel_started: float | None = None
    error: str | None = None
    launch_argv: tuple[str, ...] = ()
    launch_cwd: str | None = None
    launch_error: str | None = None
    terminal_diagnostics: dict | None = None
    auto_publish: bool = False
    metrics: dict = field(default_factory=lambda: {"callbacks": 0, "max_callback_seconds": 0.,
        "overruns": 0, "json_bytes": 0, "max_object_seconds": 0., "atomic_seconds": {},
        "stage_seconds": {}, "stage_max_callback_seconds": {}})


@dataclass
class RuntimeState:
    """Shared in-memory session, one job slot and retained immutable documents."""

    runtime_session: str = field(default_factory=lambda: uuid.uuid4().hex)
    observation_epoch: int = 0
    job: RuntimeJob | None = None
    last_job: RuntimeJob | None = None
    lifecycle: str = "idle"
    freshness: str = "unverified"
    current_result: object = None
    domain_session: object = None
    domain_context: object = None
    documents: list = field(default_factory=list)
    observation_hooks_active: bool = False
    current_observation: object = None
    overlay_object: object = None
    inspection: object = None


STATE = RuntimeState()


def reassign_duplicate_plane_uuid(*, plane_uuid: str, new_uuid: str,
                                  existing_plane_uuids=()) -> dict[str, object]:
    """Require an explicit new plane identity and preserve the old result as historical."""
    if not isinstance(plane_uuid, str) or not plane_uuid.strip():
        raise ValueError("existing plane UUID is required")
    if not isinstance(new_uuid, str) or not new_uuid.strip() or new_uuid == plane_uuid:
        raise ValueError("new plane UUID must be distinct")
    existing = tuple(existing_plane_uuids)
    if plane_uuid not in existing:
        raise ValueError("duplicate plane UUID was not observed")
    if new_uuid in existing:
        raise ValueError("new plane UUID already exists")
    STATE.observation_epoch += 1
    STATE.freshness = "historical" if STATE.current_result is not None else "unverified"
    return {"action": "reassign_duplicate_plane", "old_plane_uuid": plane_uuid,
            "new_plane_uuid": new_uuid, "revision": 1}


def embed_result_text(result, *, bpy_module=None, text_name: str | None = None):
    """Write one strict validated result into a fake-user Blender Text block."""
    _main_thread()
    if not isinstance(result, wire.ValidatedAnalysisResult):
        raise TypeError("result must be a ValidatedAnalysisResult")
    bpy = bpy_module or importlib.import_module("bpy")
    name = text_name or f"OM Analysis Result {result.document['result_id']}"
    text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    text.clear()
    text.write(wire.canonical_json(result.document))
    text.use_fake_user = True
    text["om_analysis_owner"] = "order_analyzer"
    text["om_analysis_role"] = "overlay"
    text["om_analysis_result_id"] = result.document["result_id"]
    return text


def embed_region_manifest(manifest_text: str, *, scene_token: str, bpy_module=None,
                          text_name: str | None = None):
    """Persist one validated display-only region manifest for one native scene."""
    from . import regions

    restored = regions.decode_manifest(manifest_text)
    bpy = bpy_module or importlib.import_module("bpy")
    name = text_name or f"OM Analysis Regions {scene_token}"
    text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    text.clear()
    text.write(regions.encode_manifest(restored["records"], active_region_id=restored.get("active_region_id"),
                                       storey_ref=restored.get("storey_ref")))
    text.use_fake_user = True
    text["om_analysis_owner"] = "order_analyzer"
    text["om_analysis_role"] = "region_list"
    text["om_analysis_scene_token"] = str(scene_token)
    return text


def restore_region_manifest(text_body: str):
    """Restore region records as historical display data without runtime consent."""
    from . import regions
    return regions.decode_manifest(text_body)


def find_region_manifest(*, scene_token: str, bpy_module=None):
    """Find the region Text bound to one scene, ignoring other scenes in the file."""
    bpy = bpy_module or importlib.import_module("bpy")
    for text in bpy.data.texts:
        if (getattr(text, "get", lambda *_: None)("om_analysis_owner") == "order_analyzer"
                and getattr(text, "get", lambda *_: None)("om_analysis_role") == "region_list"
                and getattr(text, "get", lambda *_: None)("om_analysis_scene_token") == str(scene_token)):
            return restore_region_manifest(text.as_string())
    return None


def restore_embedded_text(text_body: str):
    """Validate embedded JSON through the same wire reader as sidecar documents."""
    from .overlay import restore_embedded_result
    return restore_embedded_result(text_body)


def save_copy(*, target: Path, live_path: Path | None = None, bpy_module=None, artifact_log: list | None = None):
    """Save a new native copy and retain live truth when native saving fails."""
    _main_thread()
    bpy = bpy_module or importlib.import_module("bpy")
    scene = getattr(getattr(bpy, "context", None), "scene", None)
    if scene is not None and callable(getattr(scene, "get", None)) and scene.get("om_analysis_authoring_recovery_error"):
        raise ValueError("Save Copy blocked after native authoring recovery failed")
    target = Path(target).resolve()
    if live_path is not None and target == Path(live_path).resolve():
        raise ValueError("Save Copy target must differ from the live file")
    if target.exists():
        raise FileExistsError(str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.name}.{uuid.uuid4().hex}.partial")
    partial.write_bytes(b"")
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    partial.unlink(missing_ok=True)
    if artifact_log is not None:
        artifact_log.append(str(target))
    return target


def reap_owned_job(*, timeout: float = CANCEL_GRACE_SECONDS + 0.25) -> None:
    """Drive cooperative cancellation and child reaping before addon teardown."""
    _main_thread()
    if STATE.job is None:
        return
    cancel_job()
    deadline = monotonic() + timeout
    while STATE.job is not None and monotonic() < deadline:
        poll_job()
    if STATE.job is not None:
        poll_job()


def _main_thread():
    """Reject native/process work from any background thread before state access."""
    if current_thread() is not main_thread():
        raise RuntimeError("analysis runtime requires Blender main thread")


def _paths(repo_root):
    """Resolve only fixed trusted repository/Pixi paths, never payload commands."""
    root = Path(repo_root).resolve()
    for relative in RESOURCE_PATHS + (".pixi/envs/default/python.exe",):
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("invalid repository/Pixi path: " + relative)
    return root, root / ".pixi/envs/default/python.exe"


def _scene_file_token(context):
    """Bind the actual current native file/scene without using display names as semantics."""
    bpy = importlib.import_module("bpy")
    if context.scene is not bpy.context.scene:
        raise ValueError("capture requires current native scene")
    pointer = context.scene.as_pointer() if hasattr(context.scene, "as_pointer") else id(context.scene)
    return wire.canonical_json([bpy.data.filepath, pointer])


def _file_stats(root):
    """Observe fixed implementation/config resources cheaply between hashing batches."""
    result = {}
    for relative in RESOURCE_PATHS:
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("resource escaped configured root")
        stat = path.stat()
        result[relative] = [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    return result


def _native_guard(job):
    """Read cheap current file/frame/IFC transaction facts again at final commit."""
    scene = job.context.scene
    store = importlib.import_module("bonsai.bim.ifc").IfcStore
    transaction = getattr(store, "last_transaction", None)
    return {"scene_file_token": _scene_file_token(job.context), "frame": scene.frame_current,
        "subframe": scene.frame_subframe, "unit_scale": scene.unit_settings.scale_length,
        "mode": job.context.mode, "ifc_transaction": str(transaction) if transaction is not None else None,
        "ifc_path": str(getattr(store, "path", "")), "model_identity": id(store.get_file())}


def _native_observation_steps(job):
    """Batch native factual reads and fixed file hashing without a watcher framework."""
    scene, model = job.context.scene, job.capture_job.model
    store = importlib.import_module("bonsai.bim.ifc").IfcStore
    transaction = getattr(store, "last_transaction", None)
    guard = _native_guard(job)
    facts = [{**guard, "schema": model.schema}]
    products = []
    for entity in model.by_type("IfcProduct"):
        products.append([entity.id(), entity.GlobalId, entity.is_a()])
        yield None
    facts.append(sorted(products))
    for obj in tuple(scene.objects):
        tags = {key: obj.get(key) for key in ("om_analysis_preview", "OM_B4_Diagnostic", "om_analysis_owner", "om_analysis_role")} if callable(getattr(obj, "get", None)) else {}
        if capture.is_owned_display(tags):
            continue
        entity = job.capture_job.tool.Ifc.get_entity(obj)
        if entity is None:
            continue
        matrix = getattr(obj, "matrix_world", ())
        # Non-root bindings such as IfcGridAxis have STEP identity but no GlobalId.
        facts.append({"guid": getattr(entity, "GlobalId", None), "step": entity.id(),
            "matrix": [[float(value) for value in row] for row in matrix], "parent": getattr(getattr(obj, "parent", None), "name_full", None),
            "data": getattr(getattr(obj, "data", None), "name_full", None),
            "modifiers": [{"name": modifier.name, "type": modifier.type,
                "show_viewport": modifier.show_viewport, "show_render": modifier.show_render} for modifier in obj.modifiers],
            "materials": [getattr(slot.material, "name_full", None) for slot in obj.material_slots]})
        yield None
    stats = _file_stats(job.root)
    resources = {}
    for relative in RESOURCE_PATHS:
        digest = sha256()
        with (job.root / relative).open("rb") as stream:
            while chunk := stream.read(65536):
                digest.update(chunk)
                yield None
        resources[relative] = digest.hexdigest()
    if stats != _file_stats(job.root):
        raise ValueError("configuration changed while verifying")
    # Normal native event hooks + IFC transaction observation delimit the observable freshness claim.
    return {"native_digest": sha256(wire.canonical_json(facts).encode()).hexdigest(), "resources": resources,
            "file_stats": stats, "verified": STATE.observation_hooks_active and transaction is not None,
            "native_guard": guard, "epoch": STATE.observation_epoch}


def _check_job(job):
    """A reverted edit, session change or resource mutation cannot revive frozen work."""
    if (STATE.job is not job or job.epoch != STATE.observation_epoch or job.runtime_session != STATE.runtime_session
            or _scene_file_token(job.context) != job.scene_file_token):
        raise ValueError("job observation/session invalidated")
    if job.observation_before is not None and _file_stats(job.root) != job.observation_before["file_stats"]:
        raise ValueError("implementation/config resources changed")
    if job.observation_before is not None and _native_guard(job) != job.observation_before["native_guard"]:
        raise ValueError("native file/frame/IFC transaction changed")


def start_job(*, repo_root: Path, bpy_context: object, payload: Mapping[str, object],
              auto_publish: bool = False) -> str:
    """Freeze one concrete workflow and begin main-thread capture without spawning yet."""
    _main_thread()
    if STATE.job is not None:
        raise ValueError("one analysis job is already active")
    if not isinstance(payload, Mapping) or payload.get("kind") not in wire.KINDS:
        raise ValueError("invalid workflow payload")
    allowed = {"kind", "job_binding"} | ({"context", "prior", "action", "entrypoint", "domain_source_id", "storey_ref",
        "support_source_id"} if payload["kind"] == "domain_session"
        else {"request", "domain_geometries", "support_binding", "legacy_bindings"})
    if set(payload) - allowed:
        raise ValueError("payload cannot choose capture, executable, command or module")
    payload = wire.plain(payload)
    if payload["kind"] == "free_space_run":
        domain = STATE.domain_session
        if (not isinstance(domain, Mapping) or not domain.get("confirmation_binding")
                or domain.get("analysis_domain") is None or STATE.domain_context is None
                or domain.get("current", {}).get("status") != "active"
                or payload.get("request", {}).get("domain") != wire.plain(domain["analysis_domain"])
                or payload.get("domain_geometries") != wire.plain(domain["domain_geometries"])):
            raise ValueError("free-space Start requires the retained exact confirmed domain")
        frozen_domain = {"domain_request_id": domain["domain_request_identity"],
            "domain_session_revision": domain["session_revision"],
            "confirmation_binding": wire.plain(domain["confirmation_binding"]),
            "structural_context": wire.plain(STATE.domain_context)}
        # Retain authored IFC identity facts in the child binding so the
        # executor validates the exact Space/storey/support selection again.
        authored = domain.get("authored_domain")
        if isinstance(authored, Mapping) and authored.get("source_id"):
            frozen_domain["domain_source_id"] = authored["source_id"]
            if domain.get("space_binding") is not None:
                frozen_domain["space_binding"] = wire.plain(domain["space_binding"])
            provenance = authored.get("provenance")
            if isinstance(provenance, Mapping) and provenance.get("level_ref"):
                frozen_domain["storey_ref"] = provenance["level_ref"]
        support = domain.get("support_binding")
        if isinstance(support, Mapping) and support.get("source_object_id"):
            frozen_domain["support_source_id"] = support["source_object_id"]
        supplied = payload.get("job_binding", {})
        if any(key in supplied and supplied[key] != value for key, value in frozen_domain.items()):
            raise ValueError("payload domain binding differs from retained session")
        payload["job_binding"] = {**supplied, **frozen_domain}
    root, _ = _paths(repo_root)
    token = _scene_file_token(bpy_context)
    job_id = uuid.uuid4().hex
    directory = root / "outputs" / "blender_analysis" / "jobs" / job_id
    directory = directory.resolve()
    if not directory.is_relative_to(root):
        raise ValueError("owned job directory escaped root")
    directory.mkdir(parents=True, exist_ok=False)
    job = RuntimeJob(job_id, root, bpy_context, wire.plain(payload), directory,
                     STATE.observation_epoch, STATE.runtime_session, token,
                     auto_publish=auto_publish)
    job.binding = {**wire.plain(payload.get("job_binding", {})), "job_id": job_id,
        "runtime_session": job.runtime_session, "scene_file_token": token, "observation_epoch": job.epoch,
        "created_at": datetime.now(timezone.utc).isoformat(), "root": str(root)}
    try:
        started = perf_counter()
        job.capture_job = capture.begin_analysis_capture(bpy_context=bpy_context, scene_token=job.runtime_session)
        job.metrics["atomic_seconds"]["begin_capture"] = perf_counter() - started
    except Exception:
        # Directory is newly owned but may contain useful native failure evidence; never recurse-delete it.
        STATE.freshness = "unverified"
        raise
    job.stage, job.iterator = "observe_start", _native_observation_steps(job)
    STATE.job, STATE.lifecycle = job, job.lifecycle
    STATE.current_observation = None
    return job_id


def _write_request_steps(job):
    """Stream finite JSON chunks before launching the fixed Pixi module."""
    observation = job.observation_before
    job.captured = yield from _canonical_capture_for_request_steps(job.captured)
    job.stage = "request_digest"
    yield None
    capture_digest = yield from _document_digest_steps(job.captured)
    job.binding.update(config_observation=observation["resources"], native_observation=observation["native_digest"],
        capture_digest=capture_digest)
    job.payload.update(job_binding=job.binding, canonical_capture=job.captured)
    job.stage = "write"
    yield None
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)
    with (job.directory / "request.json").open("w", encoding="utf-8", newline="\n") as stream:
        for chunk in encoder.iterencode(job.payload):
            stream.write(chunk)
            job.metrics["json_bytes"] += len(chunk.encode("utf-8"))
            yield None
        stream.flush()


def _canonical_capture_for_request(captured):
    """Keep the synchronous normalization API on the same validated transport path."""
    steps = _canonical_capture_for_request_steps(captured)
    while True:
        try:
            next(steps)
        except StopIteration as done:
            return done.value


def _canonical_capture_for_request_steps(captured):
    """Share canonical normalization with native recapture before strict wire validation."""
    data = yield from capture.normalized_capture_steps(captured)
    yield from _validate_wire_steps(data)
    return data


def _validate_wire_steps(value, progress=None):
    """Validate transport data with wire.plain's strict JSON rules without copying."""
    if progress is None:
        progress = [0]
    progress[0] += 1
    if progress[0] % 256 == 0:
        yield None
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            yield from _validate_wire_steps(item, progress)
            if isinstance(item, float):
                value[key] = float(item)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _validate_wire_steps(item, progress)
            if isinstance(item, float):
                value[index] = float(item)
        return
    if value is None or type(value) in (bool, str, int):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    raise ValueError("document contains non-finite or non-data value: " + type(value).__name__)


def _document_digest_steps(document):
    """Hash already-validated transport using exactly the wire's canonical encoding."""
    digest = sha256()
    payload = {key: value for key, value in document.items() if key != "digest"}
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                               separators=(",", ":"), sort_keys=True)
    for chunk in encoder.iterencode(payload):
        digest.update(chunk.encode("utf-8"))
        yield None
    return digest.hexdigest()


def _launch(job):
    """Spawn only the validated fixed interpreter/module with owned, consumed logs."""
    root, python = _paths(job.root)
    argv = (str(python), "-m", "adapters.blender_analysis_session",
            str(job.directory / "request.json"), str(job.directory / "result.json"))
    job.launch_argv, job.launch_cwd = argv, str(root)
    environment = _child_environment(root, os.environ)
    logs = [(job.directory / name).open("wb") for name in ("stdout.log", "stderr.log")]
    job.logs = logs
    try:
        job.process = subprocess.Popen(list(argv), cwd=str(root), env=environment, shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), stdout=logs[0], stderr=logs[1])
    except Exception as exc:
        job.launch_error = f"{type(exc).__name__}: {exc}"
        for log in logs:
            log.close()
        _write_terminal_diagnostics(job, returncode=None)
        raise
    job.lifecycle, job.stage = "running", "process"


def _child_environment(root, inherited):
    """Build the Windows conda loader environment from the validated repository root."""
    environment = dict(inherited)
    env_root = (Path(root) / ".pixi" / "envs" / "default").resolve()
    runtime_paths = (env_root, env_root / "Library" / "mingw-w64" / "bin",
                     env_root / "Library" / "usr" / "bin", env_root / "Library" / "bin",
                     env_root / "Scripts", env_root / "bin")
    entries = [str(path) for path in runtime_paths]
    entries.extend(str(inherited.get("PATH", "")).split(os.pathsep))
    unique, identities = [], set()
    for entry in entries:
        if not entry:
            continue
        identity = _windows_path_identity(entry)
        if identity in identities:
            continue
        identities.add(identity)
        unique.append(entry)
    environment["PATH"] = os.pathsep.join(unique)
    environment["CONDA_PREFIX"] = str(env_root)
    existing_pythonpath = inherited.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, (str(root), existing_pythonpath)))
    return environment


def _windows_path_identity(value):
    """Compare PATH entries case-insensitively without resolving or rewriting them."""
    text = str(value).replace("/", "\\")
    while len(text) > 3 and text.endswith("\\"):
        text = text[:-1]
    return text.casefold()


def _write_terminal_diagnostics(job, *, returncode):
    """Persist complete child launch/terminal evidence in the owned job directory."""
    def read_log(name):
        """Read one bounded child log without hiding a missing artifact."""
        path = job.directory / name
        try:
            return path.read_bytes()[-LOG_LIMIT:].decode("utf-8", "replace")
        except FileNotFoundError:
            return "<missing>"

    diagnostics = {"argv": list(job.launch_argv), "cwd": job.launch_cwd,
        "returncode": returncode, "launch_error": job.launch_error,
        "stdout": read_log("stdout.log"), "stderr": read_log("stderr.log"),
        "metrics": wire.plain(job.metrics)}
    job.terminal_diagnostics = diagnostics
    (job.directory / "terminal_diagnostics.json").write_text(
        wire.canonical_json(diagnostics), encoding="utf-8", newline="\n")
    return diagnostics


def _terminal_error(diagnostics):
    """Format terminal evidence without collapsing an empty-log child failure."""
    # Timing details stay in the artifact so they cannot crowd out the UI failure.
    return "Pixi child failed: " + wire.canonical_json(
        {key: value for key, value in diagnostics.items() if key != "metrics"})


def _read_result_steps(job):
    """Read result bytes in bounded chunks; report indivisible parse/validation honestly."""
    chunks = []
    with (job.directory / "result.json").open("rb") as stream:
        while chunk := stream.read(65536):
            chunks.append(chunk)
            yield None
    raw = b"".join(chunks)
    job.metrics["result_bytes"] = len(raw)
    started = perf_counter()
    document = wire.load_json(raw.decode("utf-8"))
    wire.validate_document(document)
    job.metrics["atomic_seconds"]["parse_validate"] = perf_counter() - started
    return wire.ValidatedAnalysisResult(document)


def _finish(job, lifecycle, error=None):
    """Release only this owned slot after its child exits, retaining previous truth."""
    job.lifecycle, job.error = lifecycle, str(error)[:1200] if error is not None else None
    if job.iterator is not None:
        job.iterator.close()
        job.iterator = None
    for log in job.logs:
        log.close()
    job.metrics["elapsed_seconds"] = monotonic() - job.started
    STATE.lifecycle, STATE.last_job = lifecycle, job
    STATE.job = None
    if lifecycle != "complete":
        STATE.freshness = "stale" if STATE.current_result is not None else "unverified"
        STATE.current_observation = None
    return job


def cancel_job() -> None:
    """Cancel cooperatively; retain the slot until the owned child has been reaped."""
    _main_thread()
    job = STATE.job
    if job is None or job.lifecycle == "cancelling":
        return
    STATE.observation_epoch += 1
    STATE.current_observation = None
    job.lifecycle, STATE.lifecycle = "cancelling", "cancelling"
    job.cancel_started = monotonic()
    if job.capture_job is not None:
        capture.cancel_capture(job.capture_job, reason="runtime cancellation")
    if job.iterator is not None:
        job.iterator.close()
        job.iterator = None
    if job.process is not None and job.process.poll() is None:
        job.process.terminate()


def invalidate_runtime(reason: str, *, new_session: bool = False) -> None:
    """Record sticky observed changes without geometry work or revoking B4 consent."""
    _main_thread()
    if reason == "display_only" and not new_session:
        return
    STATE.observation_epoch += 1
    STATE.current_observation = None
    STATE.freshness = "stale" if STATE.current_result is not None or STATE.freshness == "current" else "unverified"
    if new_session:
        STATE.runtime_session = uuid.uuid4().hex
        STATE.observation_hooks_active = False
    if STATE.job is not None:
        STATE.job.error = str(reason)[:1200]
        cancel_job()
        if STATE.job is not None and (STATE.job.process is None or STATE.job.process.poll() is not None):
            _finish(STATE.job, "interrupted", reason)


def invalidate_domain_session(reason: str = "analysis domain changed") -> None:
    """Drop retained Domain consent when a persisted region selection changes."""
    _main_thread()
    STATE.domain_session = None
    STATE.domain_context = None
    invalidate_runtime(reason)


def _advance(job):
    """Consume one timer budget from a concrete capture/write/read/verify stage."""
    deadline = perf_counter() + BUDGET_SECONDS
    stage = job.stage
    while perf_counter() < deadline:
        try:
            next(job.iterator)
            if job.stage != stage:
                return False, None
        except StopIteration as finished:
            job.iterator = None
            return True, finished.value
    return False, None


def poll_job() -> RuntimeJob | None:
    """Advance one bounded main-thread callback; never block waiting for a child."""
    _main_thread()
    job = STATE.job
    if job is None:
        return None
    started = perf_counter()
    stage = job.stage
    try:
        if job.lifecycle == "cancelling":
            if job.process is not None and job.process.poll() is None:
                if monotonic() - job.cancel_started >= CANCEL_GRACE_SECONDS:
                    job.process.kill()
                return job
            return _finish(job, "interrupted", job.error or "cancelled")
        _check_job(job)
        if job.stage == "observe_start":
            complete, value = _advance(job)
            if complete:
                job.observation_start = value
                job.stage = "capture"
        elif job.stage == "capture":
            progress = capture.capture_next_batch(job.capture_job, max_seconds=BUDGET_SECONDS)
            job.metrics["max_object_seconds"] = max(job.metrics["max_object_seconds"], progress.max_object_seconds)
            if progress.callback_seconds > BUDGET_SECONDS:
                job.capture_job.batch_size = max(1, job.capture_job.batch_size // 2)
            if progress.complete:
                job.stage, job.iterator = "finalize", capture.finalize_capture_steps(job.capture_job)
        elif job.stage == "finalize":
            complete, value = _advance(job)
            if complete:
                job.captured = value
                # The pre-capture observation remains the immutable baseline.
                job.stage, job.iterator = "observe_after_capture", _native_observation_steps(job)
        elif job.stage == "observe_after_capture":
            complete, value = _advance(job)
            if complete:
                if value != job.observation_start:
                    raise ValueError("native source changed between capture start and finalize")
                job.observation_before = job.observation_start
                job.stage, job.iterator = "request_normalize", _write_request_steps(job)
        elif job.stage in {"request_normalize", "request_digest", "write"}:
            if _advance(job)[0]:
                _check_job(job)
                _launch(job)
        elif job.stage == "process":
            if any((job.directory / name).stat().st_size > LOG_LIMIT for name in ("stdout.log", "stderr.log")):
                job.error = "child exceeded owned log budget"
                cancel_job()
            elif job.process.poll() is not None:
                for log in job.logs:
                    log.close()
                job.logs = []
                diagnostics = _write_terminal_diagnostics(job, returncode=job.process.returncode)
                if job.process.returncode:
                    return _finish(job, "failed", _terminal_error(diagnostics))
                job.stage, job.iterator = "read", _read_result_steps(job)
        elif job.stage == "read":
            complete, value = _advance(job)
            if complete:
                job.candidate = value
                job.stage, job.iterator = "observe_after", _native_observation_steps(job)
        elif job.stage == "observe_after":
            complete, value = _advance(job)
            if complete:
                job.observation_after = value
                if value != job.observation_start:
                    raise ValueError("source/config changed during analysis")
                job.candidate = prepare_publication(job.candidate)
                if job.auto_publish:
                    job.stage = "awaiting_publication"
                    commit_publication(job.candidate, native_artifacts={})
                else:
                    job.stage = "awaiting_publication"
        return job
    except Exception as exc:
        if job.process is not None and job.process.poll() is None:
            job.error = str(exc)[:1200]
            cancel_job()
            return job
        return _finish(job, "failed", exc)
    finally:
        elapsed = perf_counter() - started
        job.metrics["callbacks"] += 1
        job.metrics["max_callback_seconds"] = max(job.metrics["max_callback_seconds"], elapsed)
        job.metrics["overruns"] += elapsed > BUDGET_SECONDS
        totals = job.metrics["stage_seconds"]
        maxima = job.metrics["stage_max_callback_seconds"]
        totals[stage] = totals.get(stage, 0.) + elapsed
        maxima[stage] = max(maxima.get(stage, 0.), elapsed)


def prepare_publication(document: Mapping[str, object]) -> wire.ValidatedAnalysisResult:
    """Authenticate candidate content and independently compare this runtime's frozen job."""
    _main_thread()
    started = perf_counter()
    if isinstance(document, wire.ValidatedAnalysisResult):
        candidate = document
    else:
        wire.validate_document(document)
        candidate = wire.ValidatedAnalysisResult(document)
    job = STATE.job
    if job is None:
        raise ValueError("no active owned job can publish")
    _check_job(job)
    binding = candidate.document["binding"]
    if any(wire.plain(binding.get(key)) != value for key, value in job.binding.items()):
        raise ValueError("result binding differs from frozen native job")
    if candidate.document["job_id"] != job.job_id or job.observation_before is None or job.observation_after != job.observation_before:
        raise ValueError("result lacks matching pre/post native observations")
    if not all(binding.get(key) for key in ("canonical_structural_fingerprint", "canonical_full_fingerprint", "project_source_identity")):
        raise ValueError("result lacks verified canonical capture facts")
    job.metrics["atomic_seconds"]["prepare_publication"] = perf_counter() - started
    return candidate


def _replace_native_overlay(candidate: wire.ValidatedAnalysisResult, *, bpy_module=None):
    """Replace the one display-only mesh for a free-space result, excluding Domain documents."""
    if candidate.document["kind"] != "free_space_run":
        return None
    from . import overlay
    bpy_module = bpy_module or importlib.import_module("bpy")
    scene = getattr(getattr(bpy_module, "context", None), "scene", None)
    # A saved display survives reload, while the process-local cached handle does not.
    previous = [obj for obj in scene.objects
                if obj.get("om_analysis_owner") == "order_analyzer" and obj.get("om_analysis_role") == "overlay"] if scene else []
    if scene is None and STATE.overlay_object is not None:
        previous.append(STATE.overlay_object)
    if any(len(getattr(obj, "users_scene", ())) > 1 for obj in previous):
        raise ValueError("Analyzer overlay is shared with another scene; unlink it before replacing")
    replacement = overlay.build_native_mesh(candidate, bpy_module=bpy_module)
    for old in previous:
        old_mesh = getattr(old, "data", None)
        objects = getattr(getattr(bpy_module, "data", None), "objects", None)
        meshes = getattr(getattr(bpy_module, "data", None), "meshes", None)
        if objects is not None and hasattr(objects, "remove"):
            objects.remove(old, do_unlink=True)
        if (meshes is not None and old_mesh is not None and hasattr(meshes, "remove")
                and getattr(old_mesh, "users", 0) == 0):
            meshes.remove(old_mesh)
    return replacement


def _flush_native_view_layer(*, bpy_module=None):
    """Flush queued Blender view-layer updates before publishing currentness."""
    bpy_module = bpy_module or importlib.import_module("bpy")
    context = getattr(bpy_module, "context", None)
    view_layer = getattr(context, "view_layer", None)
    update = getattr(view_layer, "update", None)
    if not callable(update):
        raise RuntimeError("Blender view-layer update is unavailable")
    update()


def commit_publication(candidate: wire.ValidatedAnalysisResult, *, native_artifacts: Mapping[str, object]) -> None:
    """Commit only the staged exact candidate after native construction and final guards."""
    _main_thread()
    started = perf_counter()
    job = STATE.job
    if job is None or job.stage != "awaiting_publication" or candidate is not job.candidate:
        raise ValueError("candidate is not this job's staged publication")
    if not isinstance(candidate, wire.ValidatedAnalysisResult):
        raise TypeError("candidate must be a prepared validated result")
    _check_job(job)
    binding = candidate.document["binding"]
    if any(wire.plain(binding.get(key)) != value for key, value in job.binding.items()):
        raise ValueError("result binding differs from frozen native job")
    if (candidate.document["job_id"] != job.job_id or job.observation_before is None
            or job.observation_after != job.observation_before):
        raise ValueError("result lacks matching pre/post native observations")
    if not all(binding.get(key) for key in ("canonical_structural_fingerprint", "canonical_full_fingerprint", "project_source_identity")):
        raise ValueError("result lacks verified canonical capture facts")
    verified = job.observation_after["verified"] and all(binding.get(key) is not None for key in (
        "created_at", "runtime_session", "scene_file_token", "observation_epoch", "backend_versions"))
    if candidate.document["kind"] == "free_space_run":
        verified = verified and bool(binding.get("confirmation_binding"))
    overlay_object = _replace_native_overlay(candidate)
    if candidate.document["kind"] == "free_space_run":
        _flush_native_view_layer()
    STATE.documents.append(candidate.document)
    STATE.freshness = "current" if verified else "unverified"
    if verified or STATE.current_result is None:
        STATE.current_result = candidate
    if candidate.document["kind"] == "free_space_run":
        STATE.overlay_object = overlay_object
        STATE.inspection = None
    if candidate.document["kind"] == "domain_session":
        STATE.domain_session = candidate.document["payload"]
        STATE.domain_context = candidate.document["binding"]["structural_context"]
    STATE.current_observation = wire.freeze({"digest": candidate.digest, "binding": binding, "verified": True}) if verified else None
    # Native handles remain runtime-only; Text/mesh serialization is exclusively T4's responsibility.
    job.metrics["native_artifacts"] = dict(native_artifacts)
    job.metrics["atomic_seconds"]["commit_publication"] = perf_counter() - started
    _finish(job, "complete")

