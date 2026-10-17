# Blender Workflow Contract (Proposed)

**Status: APPROVED / IMPLEMENTATION IN PROGRESS.** The user approved Spec004 on October 15, 2026. The unified Analysis workbench design covers independent complete B4 Domain tools and new free-space through one UI/service boundary. Proposed Python signatures define the implementation seam; they are not available APIs. JSON records are strict, versioned, and data-only. Minimum fields and owning modules for all new records, including GeoJSON/UnknownSupportEvidence, are defined in [data-model.md](../data-model.md).

## Module boundaries

### `adapters/blender_analysis_capture.py`

```python
def begin_analysis_capture(*, bpy_context, scene_token: str, batch_size: int = 5) -> CaptureJob:
    """Start validated main-thread Blender capture; no worker-thread bpy access."""

def capture_next_batch(job: CaptureJob, *, max_seconds: float = 0.050) -> CaptureProgress:
    """Capture bounded evaluated objects, always release each temporary mesh."""

def cancel_capture(job: CaptureJob, *, reason: str) -> CaptureJob:
    """Stop between objects/batches and retain captured failure audit."""

def finalize_capture(job: CaptureJob) -> CanonicalCaptureInput:
    """Return only when inventory and source identity checks are complete."""
```

`CaptureProgress` contains job token, stage, processed/total, elapsed, errors and completion flag. A single non-preemptible `evaluated_get(...).to_mesh()` may exceed the callback budget; report actual per-object and callback duration. Capture all IFC-linked physical objects needed by the canonical input; unsupported/unlinked objects follow an explicit inclusion record rather than silently vanish. Preserve transforms, frame, modifiers, evaluated mesh digest, IFC identity, BIM id, material facts used, and failures.

### `adapters/bonsai_live.py`

```python
def load_bonsai_capture(
    capture: CanonicalCaptureInput, *, plane: AnalysisPlane,
    support_binding: SupportBinding | None = None,
    legacy_bindings: Sequence[LegacySourceBinding] = (),
) -> BonsaiLiveScene:
    """Validate current IFC identities and build one canonical NeutralSceneV2."""

def structural_b4_view(
    scene: NeutralSceneV2, *, context: StructuralContext, source_token: str,
) -> NeutralSceneV2:
    """Select only verified B4 structural source ids while reusing exact geometry refs."""
```

`BonsaiLiveScene` contains `scene`, `structural_scene`, `identity_map`, `domain_support_audit`, `capture_fingerprint`, and diagnostics. Identity map is explicit records: `legacy_object_id`, `legacy_step_id`, `global_id`, `project_global_id`, `canonical_object_id`, `geometry_refs`, `geometry_digest`, `capture_identity`. Every identity relation must resolve uniquely and match. Do not change `adapters/blender_geometry.py` or `load_blender_neutral_scene` semantics.

The reducer wiring is explicit: `source_revision` is the stable structural-source-facts digest (project/source identities, structural geometry and relevant structural transforms/facts), while `frame_id` is the canonical structural frame key (selected world-XY basis/origin, datum/cut and B4 constants). Neither field includes full occupancy plane revision, exact-query Z, display name, camera, selection or volatile capture token. Verify this at the actual reducer call; wrapper-only comparison of structural tokens is insufficient.

### `features/_analysis_domain_handoff.py`

`domain_handoff(...)` keeps every current return key and adds:

```python
"domain_geometries": tuple[MeshGeometry3D, ...]
```

For an authored domain, return the exact referenced, already validated objects. For an inferred active domain, return the exact `mesh` produced in that call's `_qualified`; append that same object to the child scene and return it. No outline-to-mesh rebuild. For no active domain, return `()`. Existing `analysis_domain`, `scope_polygon`, reducer events and status remain backward-compatible.

### `adapters/blender_analysis_session.py`

```python
def evaluate_domain_request(
    scene: NeutralSceneV2, *, context: StructuralContext, prior: Mapping[str, object] | None,
    action: Mapping[str, object] | None,
) -> DomainSessionResult:
    """Run the existing B4 diagnostics and reducer for the current canonical structural view."""

def execute_live_analysis(
    scene: NeutralSceneV2, *, request: AnalysisRequest,
    domain_geometries: Sequence[MeshGeometry3D],
    support_binding: SupportBinding | None = None,
) -> AnalysisRun:
    """Execute the existing AnalysisRequest with its confirmed exact geometry handoff."""

def serialize_analysis_result(
    run: AnalysisRun, *, job_id: str, plane_uuid: str, plane_revision: int,
    domain_request_id: str, domain_session_revision: int,
) -> dict[str, object]:
    """Build deterministic compact, reconstructable data-only result JSON."""

def reconstruct_field_sample(
    document: Mapping[str, object], *, row: int, column: int,
) -> FieldSample[bool]:
    """Rebuild one exact full public sample from shared records plus cell deltas."""

def validate_analysis_result(
    document: Mapping[str, object], *, expected_job_id: str,
    expected_plane_uuid: str, expected_plane_revision: int,
    expected_semantic_key: str,
) -> ValidatedAnalysisResult:
    """Check schema, digest, tokens and compact references before publication."""

def write_result_atomic(document: Mapping[str, object], *, path: Path) -> Path:
    """Write a unique partial sidecar and atomically replace the final result path."""
```

`execute_live_analysis` may build the temporary scene via the existing private domain/request composition, but must use `domain_geometries` without rerunning domain inference or triangulation. It may use only the existing shared resolver, registry, MassPatch, `execute_analysis_request`, and section helper. CLI accepts one request JSON path and one result JSON path; it does not accept a command/interpreter path from payload. Runtime derives interpreter from validated addon preference root and `.pixi/envs/default/python.exe`.

`evaluate_domain_request` receives the actual canonical structural scene and `StructuralContext` (datum 0 m, cut 1.5 m, selected XY basis), never the occupancy-height plane masquerading behind a different token. Start validates the current full-capture observation token and recaptures once if stale/unverifiable; both structural/full inputs then derive from that capture. Stable digest fields/exclusions follow the data model, with volatile observation tokens kept separate. A validated support binding resolves one `source_object_id` to canonical `source.source_id` (GlobalId) only in the request-scoped child domain used by `_scope_exclusions`; shared inferred B4 source_id remains None. Unbound/rejected support removes nothing.

B4 remains an independent service/reducer workflow. DomainSessionResult preserves or references the original authoritative service payload: candidates/id/version/area/holes/labels/reasons, current/attempt/conflict diagnostics, aperture/significant residual diagnostics, ignored tiny residual count, source/geometry counts, source identity, scenario/tolerance, provenance and handoff state. UI renders these facts without recomputing them. A domain snapshot can be inspected before confirmation; neither reading it nor selecting a candidate creates consent. No requirement routes B4 lifecycle through free-space AnalysisRequest. Existing operation strings/descriptors and the substitute-selection registry keep their current roles; no general operation/job/result registry is introduced.

`serialize_analysis_result` uses shared tables (`snapshot`, `request`, `lattice`, `source_audit`, string/value dictionaries) and per-cell deltas. Deduplication is by canonical JSON value, not key-name alone. Reconstruction must preserve the entire `FieldSample` exactly. Digest covers canonical serialized payload except the digest field and excludes display-only color/name/lift.

Unknown supports cross the subprocess seam in an explicit source-id→GeoJSON/None mapping plus verification evidence. Only exact selected source geometry/query/helper algorithm/coverage match and success permit local support. An empty support is locally empty only when that same trusted helper emits a qualified empty fact; malformed, missing, failed-target, or incomplete multi-owner support remains global unknown. The exact world-Z section comes from `request.plane.origin[2]`; B4 cut 1.5 m is never substituted.

Evidence explicitly distinguishes `valid_nonempty`, `validated_empty`, and `missing_or_malformed`. Complete selected-owner coverage is required even for empty or multi-owner support; failure remains global. No empty JSON object is accepted as a qualified-empty fact.

### Read-only result access in `adapters/blender_analysis_session.py`

The following proposed pure API consumes validated data documents, never bpy objects or paths that trigger capture. Its catalogue/wire validation portion must remain stdlib-only; if the session module's existing heavy imports cannot be isolated, extract only that minimal read portion into a lightweight sibling module. Field reconstruction stays bpy-free in Pixi using existing FieldSample, without a new framework.

```python
def list_analysis_results(
    documents: Sequence[Mapping[str, object]], *, kind: str | None = None,
) -> tuple[ResultMetadata, ...]:
    """Project metadata from the existing manifest documents without selecting latest."""

def open_analysis_result(
    documents: Sequence[Mapping[str, object]], *, result_ref: ResultRef,
    context: ResultReadContext,
) -> ReadOnlyResultSnapshot:
    """Open one exact immutable result, rejecting missing, ambiguous or incompatible evidence."""

def read_analysis_sample(
    snapshot: ReadOnlyResultSnapshot, *, row: int, column: int,
) -> FieldSample[bool]:
    """Reconstruct the existing complete sample from an opened free-space snapshot."""
```

ResultRef is `(kind, result_id, digest)` for `domain_session` or `free_space_run`. Metadata and ResultReadContext have the minimum fields in [data-model.md](../data-model.md): supported schema/algorithm/backend versions, project/source identity and fingerprints, domain, plane/revision/frame, request identity, and applicable operation/query/semantic key. Domain uses its structural request/frame; it does not invent an occupancy query. Unconfirmed/refused DomainSessionResult with no valid active domain has `analysis_domain=None`, `confirmation_binding=None`, and metadata `domain_identity=None`; candidate/request identities still exist. An unsuccessful new attempt does not erase a reducer-retained valid current domain. Context expected-domain defaults to None for exact diagnostic open, with explicit `require_confirmed_domain=False`; confirmed/current-domain consumers set that requirement and reject None. Candidate identity never substitutes valid AnalysisDomain or consent. The catalogue derives from existing embedded manifest/document references; it is not another authoritative mutable index.

The same list/open calls receive live memory documents or documents restored from fake-user Text. Validate canonical digest, references and expected identities before exposing a frozen snapshot. Missing ref, duplicate/conflicting matching entries, version incompatibility, source/domain/plane/revision/mode/query mismatch and out-of-lattice sample lookup fail explicitly. Historical read requires `allow_historical`; `require_current` requires matching verified fresh observation evidence and rejects stale/historical/unverified, even when a stored flag says current. These calls cannot capture, compute, spawn processes, mutate sessions/consent/source/results or read truth from overlay geometry. Nested result data are immutable or defensively copied.

`read_analysis_sample` rejects domain snapshots and delegates to the same `reconstruct_field_sample` used by inspection, preserving value/status/query/support/source_ids/provenance/explanation exactly. True means occupied; False means known-empty only with established/conditional evidence for that query; unknown/outside/invalid/not_available have None. Preserve conditional restrictions and unknown; freshness is independent of FieldStatus. A current run need not have complete occupancy support and is no clearance/routing certificate. No real downstream analysis consumer is claimed; the planned headless consumer tests exercise this boundary.

### `features/free_space_field.py`

Add keyword-only optional input (backward-compatible default):

```python
unresolved_supports: Mapping[str, object] | None = None
```

Validated GeoJSON polygons/lines/points supply local unknown masks. `None` per source means unresolved global support. Existing `unresolved_source_ids` remains valid and any listed source without a validated support stays global. Validate IDs are unique strings and support geometry finite/valid before field construction. Do not buffer or apply tolerance. `features/analysis_requests.py:_occupancy` returns its existing three values; `execute_analysis_request` binds trusted local support separately into the field and immutable audit. Keep `AnalysisRun.support_status` a run-level summary, unchanged.

The section helper's raw support is world XY/metres. Apply the existing occupied/domain/grid affine frame mathematics exactly once to accepted unknown support before FreeSpaceField receives it, preserving GeoJSON dimensionality: polygon/multipolygon rings, line/multiline coordinates, point/multipoint coordinates, and qualified empty geometry remain representable. `_components(geometry, request.plane.origin[:2])` is a reference for that mathematics only; its polygon-only extraction must not discard line/point touch evidence. Keep raw support and unit/frame/transform audit, preserve validated-empty as empty, reject unsupported bases conservatively. Never intersect worldXY support directly with local cells or translate twice. Core accepts plain mappings and must not import adapter-owned classes.

## Addon runtime contract

Package root: `blender_addon/order_analyzer_ui`. `bl_info` declares compatible minimum Blender 5.2. One `VIEW_3D` sidebar panel with `bl_category="Analysis"`, containing independently collapsible/expandable Domain and Free-space sections; no experiment panel registration. Preference is repository root only, never executable command text. Register/unregister the existing property/operator/panel set deterministically; unregister kills only addon-owned process, removes timer/handlers and invalidates in-memory job tokens.

Domain section preserves B4 Refresh, finite nonnegative residual tolerance in mm² (convert once by /1e6), world XY/datum0/cut1.5 and closed doors/windows assumptions, source/geometry counts, candidate selection without confirmation, candidate id/version/area/hole count/reason, outline/hole diagnostic curves and measured labels, current/last-attempt/refusal/error/stale diagnostics, ignored tiny and significant aperture residuals, and explicit Confirm. Use one reducer/session state shared with compatibility om_b4 wrappers. No free-space execution is needed for these functions. Existing reducer replace/conflict support is not claimed as existing UI functionality; service conflict status remains visible when present. Free-space section adds plane/query/grid/Start/progress/cancel/sample inspection/result access/Save Copy, using the same capture/identity/confirmed-domain boundary.

Runtime lifecycle enum: `idle | capturing | running | cancelling | complete | failed | interrupted`. Freshness: `current | stale | unverified | historical`; these are not FieldStatus values. Blender handlers/timers only enqueue stale observations or update state, never perform expensive mesh projection. Every `bpy` read/write, mesh construction, Text write, and process polling occurs on Blender main thread. One process-global job slot prevents resource contention; per-plane persisted results do not form a queue.

Addon registration/imports remain stdlib+bpy/lightweight records only: no eager Shapely/heavy core import. Pixi computes domain-clipped display fragments and triangulation. Capture, JSON handoff/validation, mesh assembly, Text append/write and polling all use bounded main-thread batches (target 50 ms); measure each callback and indivisible operation, record JSON byte count/mesh vertex-face counts and total elapsed. On overrun report actual duration and split the next batch; do not claim preemption of native mesh/Text/JSON atomic calls. Build in addon-owned temporary records and publish only after complete validation; cancellation/error retains the previous result.

`Popen([str(validated_pixi_python), str(session_cli), request_path, result_path], cwd=str(validated_root), shell=False, creationflags=CREATE_NO_WINDOW, stdout=owned_stdout_log, stderr=owned_stderr_log)` is the proposed Windows invocation. Owned log files are bounded/rotated by the addon; do not use unconsumed `PIPE` handles for long jobs. Poll with registered timers. Cancel sets lifecycle first, signals only child process, waits via polls, then kills that owned child only after a bounded grace period. Request JSON cannot name an executable or cause arbitrary module import. Process output is bounded in panel diagnostics.

Before publishing overlay, require result match `job_id`, scene/file session token, plane UUID/revision, domain-session/confirmation binding, structural/full fingerprints, request semantic key, registry/helper/backend versions and digest. If observations cannot verify tokens (including changes during capture/process or undo/load/file switch), do not mark current. Preserve prior overlay/result on error and mark it stale/unverified. Display edits are excluded from semantic key.

Overlay is built from exact domain-clipped cell geometry, including holes. One polygon may produce multiple face fragments with same stable cell index. Store compact face attributes for `cell_index`, `row`, `column`, `value`, and `status_code`; inspect resolves the authoritative embedded result by index. Do not parent results to live plane/camera. Use frozen world frame; separate display lift is presentation only. Blender mesh colors/attributes are not authoritative data.

Persistence embeds deterministic versioned compact result in `bpy.data.texts` with fake user and tags plane/overlay. Sidecar publishing is atomic and unique, after JSON validation; sidecar failure leaves previous embedded result and overlay intact. Load handler validates/migrates only supported schema and reconstructs display mesh from embedded result when needed; it never starts analysis. Save Copy uses documented Save Copy semantics (`copy=True`) and an explicit new path; default suggested target is unique by run id and does not silently overwrite. Ordinary save of current `.blend` remains Blender's normal user action. IFC is never written.

Save Copy failure retains the live Text/overlay/result and removes only addon-owned partial files; record the saved artifact only after native save success. Reopen remains historical/unverified. Before Start, verify current IFC/project/GUID mappings, stable fingerprints and domain/support bindings from a fresh valid capture. CameraBinding only follows display and cannot contribute geometry, keys or occupancy.

## Tests and acceptance contracts

- Pure pytest tests test canonicalization, strict schema/digest, exact sample round-trip, identity/proxy rejection, callback cancellation, stale token rejection, hole-clipped fragments and support geometry.
- Headless read-only consumer tests list both kinds, exact-open by ResultRef, reconstruct all sample fields, isolate different domain/plane/mode/revision/source identities, reject missing/ambiguous/incompatible/stale-as-current, prove no capture/compute/mutation, and compare live versus restored embedded documents after sidecar removal. Current snapshots containing unknown/conditional retain their exact statuses and provenance. B4 service/UI parity includes all Domain capabilities above and significant aperture diagnostics, with an independently usable Domain workflow.
- Native smoke script is planned at `test/bim/run_blender_analysis_workflow_smoke.py`; it launches only configured portable binary with `--python-exit-code 1`, enables the installed addon and invokes real operators in a disposable IFC-derived scene. Background mode remains alive through the same native runtime timer/main-thread bounded pump until the real asynchronous job completes and a successful machine report exists and validates; timeout/failure raises a nonzero exit. Visible UI/timer responsiveness is separately tested. It must not bypass UI service or fake human confirmation; fixture-only explicit test actors are labelled as such.
- Live acceptance tests both `whole_height_projection` and `exact_world_xy_section` at 0.25 m, reuses/produces current manually confirmed domain, inspects unresolved sources, verifies old result retention on injected cancel/failure, uses Save Copy to a new file, opens copy in a separate authorized portable process, compares compact cell identity/value/status/source records byte-equivalently, confirms no IFC mutation, and records actual elapsed stages. If valid live domain consent is absent, stop and report the specific required user action; do not auto-confirm.
