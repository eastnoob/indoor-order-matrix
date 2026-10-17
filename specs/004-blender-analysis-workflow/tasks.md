# Blender Analysis Workflow Implementation Plan — Tasks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付 [spec.md](spec.md) 的统一 Analysis workbench：独立完整 B4 Domain 工具、新增 free-space、native cells、持久恢复与只读消费合约。

**Architecture:** [plan.md](plan.md) 固定的 canonical capture → B4 exact geometry → AnalysisRequest → compact result → frozen native overlay。

**Tech Stack:** 锁定 Pixi Python3.12.13、指定 portable Blender5.2、已有 Bonsai/IfcOpenShell/Shapely、pytest、stdlib。

**Spec:** [spec.md](spec.md)，精确接口 [contracts/blender-workflow.md](contracts/blender-workflow.md)。

## Global Constraints

**APPROVED / IMPLEMENTATION IN PROGRESS**；用户于 2026-10-15 批准并授权执行。T0 baseline 正在进行，后续任务 pending；实现与验收不因此通过。delegated execution 已选，无需再问方法。所有任务受 plan.md Global Constraints 约束。Only version specialist performs VCS writes or manages workspaces; prefer jj/jj workspace and jj git push, with Git fallback allowed when jj is unavailable or incapable, recording the reason per project memory。每次 red/green、native command 都把实际 exit code、output path、结论填入 checklist；未运行一律 PENDING。以下新 test 名称是拟新增验收点，不冒充已存在；标记 Existing 的名字来自现存源码或 Git23d24a3 reference，T0 必须逐项核验存在/import closure。

Owner ruling (2026-10-15): this task uses a jj workspace in place of Git-worktree skill instructions. Only the version specialist manages it; preserve the workspace and undelivered artifacts until accepted/integrated, with no automatic deletion. Durable task progress is [progress.md](../../.superpowers/sdd/004-blender-analysis-workflow/progress.md).

### Task T0: Baseline、caller audit 与 owner design gate

**Files:** Read `AGENTS.md`, architecture memory, software-architecture, Spec004 全文；read `features/{analysis_requests,free_space_field,_analysis_domain_handoff}.py` 和 `scripts/design/{live_domain,space_field}` 实际调用；write `specs/004-blender-analysis-workflow/checklist.md`。本任务不编辑生产代码。

**Interfaces:** Consumes current files/contracts；produces exact baseline/caller report 和用户 design decision。setup-plan returned feature identifier 不是新 VCS branch。

- [ ] **B4 parity inventory:** Audit actual `blender_panel.py` / `run_live_domain.py` against plan capability mapping: Refresh, finite nonnegative tolerance mm² / closed-aperture assumptions, source/geometry counts, id/version/area/holes/reasons, outline/hole curves/labels, Select without consent, explicit Confirm, refusal/error/current/attempt/stale and ignored-tiny/significant-aperture residual diagnostics. Preserve original service payload; do not label reducer-only replace/conflict actions existing UI parity. Confirm B4 can operate independently of a free-space run.

- [ ] **Prerequisite: CURRENT TREE ABSENT.** 当前 `features/analysis_requests.py`、`adapters/bonsai_analysis_plane.py` 和 `scripts/design/space_field/{capture_b3_live_scene,run_b3_live_analysis_request}.py` 缺失；`features/_analysis_domain_handoff.py` 与两份 live_domain B4 modules 存在。Version specialist 必须先在隔离 clean workspace（优先 jj workspace，按项目记忆允许 Git fallback）恢复/核验 Git checkpoint `23d24a3` 的完整 approved dependency/import closure，保留 dirty history；不能只拷几个入口文件。优先用 `jj --ignore-working-copy file show -r 23d24a3 <path>` 阅读缺失 Spec003 文档，不复制第二套文档。下列 hash/caller/baseline tests 只在该 prerequisite 完成后运行；本轮未恢复生产代码或运行测试。

- [ ] **Step 1: Capture baseline hashes and caller paths.**

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath features/analysis_requests.py,features/free_space_field.py,features/_analysis_domain_handoff.py,scripts/design/space_field/capture_b3_live_scene.py,scripts/design/space_field/run_b3_live_analysis_request.py,scripts/design/live_domain/run_live_domain.py,scripts/design/live_domain/blender_panel.py,pixi.lock | ConvertTo-Json
rg -n 'domain_handoff\(|_qualified\(|load_blender_neutral_scene\(|live-step-|blender-object:|_sample_records|FreeSpaceField\(' features adapters scripts test
```

- [ ] **Step 2: Run current focused baseline.**

```powershell
pixi run python -m pytest test/test_analysis_requests.py test/test_free_space_field.py test/test_b3_live_scene_capture.py test/test_b3_live_analysis_request.py test/test_b3_occupancy_only_handoff.py test/test_bonsai_analysis_plane.py -q
```

Expected: baseline green, or exact failure classified before implementation. Do not fix unrelated historical dirty files.

Audit the actual B4 reducer caller's `source_revision` and `frame_id`: the current handoff hashes complete `scene.to_dict()` and `frame`, so a wrapper structural token alone does not fix identity drift. Record this T0 caller evidence; T1 must bind `source_revision` to the stable structural-source-facts digest and `frame_id` to `structural_frame_key`, or supply an equivalent canonical structural scene/frame projection whose hashes exclude every occupancy-only and volatile field. Verify the values reaching the reducer, not just adapter comparison results.

- [x] **Step 3: Record user design review and architecture seam ownership.** User approved spec.md and plan.md on 2026-10-15; the other artifacts support that review without separate per-file signatures. Keep architecture/memory planned seams and later actual implementation states synchronized.

**Stop:** T0 baseline remains unexplained; scope requires IFC writes, another Blender, new dependencies, a second algorithm, or historical S3 auto-selection. No production test was run by the planning writer; approval is already recorded above and does not waive the baseline gate.

### Task T1: Canonical capture、B4 service 与实际 domain mesh

**Files:** Create `adapters/blender_analysis_capture.py`, `adapters/bonsai_live.py`, `adapters/blender_analysis_session.py`, `test/test_blender_analysis_capture.py`, `test/test_bonsai_live.py`, `test/test_blender_analysis_session.py`。Modify `features/_analysis_domain_handoff.py`；必要兼容 wrappers only in `scripts/design/space_field/{capture_b3_live_scene,run_b3_live_analysis_request}.py` 和 `scripts/design/live_domain/{run_live_domain,blender_panel}.py`。Read `adapters/ifc_bonsai.py` 身份惯例；不改 generic Blender loader。

**Interfaces:**

```python
begin_analysis_capture(*, bpy_context, scene_token: str, batch_size: int = 5) -> CaptureJob
capture_next_batch(job: CaptureJob, *, max_seconds: float = .050) -> CaptureProgress
cancel_capture(job: CaptureJob, *, reason: str) -> CaptureJob
finalize_capture(job: CaptureJob) -> CanonicalCaptureInput
load_bonsai_capture(capture: CanonicalCaptureInput, *, plane: AnalysisPlane,
                   support_binding: SupportBinding | None = None,
                   legacy_bindings: Sequence[LegacySourceBinding] = ()) -> BonsaiLiveScene
structural_b4_view(scene: NeutralSceneV2, *, context: StructuralContext, source_token: str) -> NeutralSceneV2
evaluate_domain_request(scene: NeutralSceneV2, *, context: StructuralContext,
                        prior: Mapping[str, object] | None,
                        action: Mapping[str, object] | None) -> DomainSessionResult
execute_live_analysis(scene: NeutralSceneV2, *, request: AnalysisRequest,
                      domain_geometries: Sequence[MeshGeometry3D],
                      support_binding: SupportBinding | None = None) -> AnalysisRun
```

`CaptureJob`, `CaptureProgress`, `CanonicalCaptureInput`, `LegacySourceBinding`, `SupportBinding`, `BonsaiLiveScene`, `DomainSessionResult` are concrete adapter-local records defined by data-model/contract fields, not new core base classes. `domain_handoff(...)` adds `domain_geometries: tuple[MeshGeometry3D,...]`.

- [ ] **Step 1: Add focused failing contract tests.** New `test_bonsai_live.py::test_canonical_identity_map_requires_project_guid_step_and_geometry`, `::test_unbound_floor_remains_occupancy`, `::test_required_proxy_refusal_never_restores_raw_owner`；`test_blender_analysis_session.py::test_select_does_not_confirm`, `::test_handoff_returns_exact_qualified_mesh_without_retriangulation`。Use existing real dataclass scene fixtures from `test/test_analysis_requests.py` as pattern; make the new fixtures local with explicitly declared GlobalId/project/STEP/mesh facts. Small assertions:

```python
assert source.id == 'ifc-object:' + source.source_id
assert structural_scene.geometries[0] is full_scene.geometries[0]
assert result['analysis_domain'].source_id is None
assert result['domain_geometries'][0] is qualified_mesh
assert triangulation_call_count == 1
assert refused_owner_id in unresolved_source_ids
assert refused_owner_id not in selected_raw_source_ids
```

- [ ] **Step 2: Run red tests.** `pixi run python -m pytest test/test_bonsai_live.py test/test_blender_analysis_session.py -q`。Expected new imports/missing seam failure；记录实际 failure，不伪造已通过。
- [ ] **Step 3: Factor capture once.** Move existing evaluated extraction/release/units behavior to adapter；full IFC inventory independent visibility；missing mesh creates unresolved fact；capture frozen frame/modifiers/material/parent/source tokens；temporary meshes `finally: to_mesh_clear()`；main-thread batched work returns measured callback/individual to_mesh time。
- [ ] **Step 4: Canonicalize and validate bindings.** `ifc-object:{GlobalId}` + source_id GlobalId + verified class；legacy rows verify project/source identity、STEP+GUID、mesh refs/digest、declared scope/coverage。Reject ambiguous/stale map；start unconfirmed reducer on changed identity。B4 gets structural subset of same records；full occupancy unchanged。Explicit unique current slab/floor support only；unbound warns but raw occupancy runs。Three old hulls/seven owners imported only after exact scope/geometry validation；no fallback for required proxy refusal。
- [ ] **Step 5: Add actual geometry handoff and service.** Retain exact `_qualified` mesh object in child scene and new `domain_geometries` result；authored returns actual refs；no active gives empty tuple。Service serializes these records directly, never reruns inference/triangulation or derives geometry from preview。Reuse B4 reducer events and rules, structural cut1.5；request exact Z distinct。Old om_b4 wrappers use same service, no second state。

- [ ] **B4 service parity:** Add `test_domain_session_preserves_existing_b4_payload` covering `attempt/current`, candidates/area/holes/labels/reasons, aperture/significant residuals, ignored tiny residual count, source/geometry counts, scenario/tolerance/provenance and returned conflict diagnostics. Add `test_domain_workflow_independent_of_free_space_request` proving Refresh/Select/Confirm uses existing B4 service/reducer without executing occupancy. Convert finite nonnegative mm² tolerance to m² exactly once; changing it reobserves and cannot revive ABA consent.

- [ ] **Reducer identity seam:** Wire actual reducer `source_revision` to the stable structural-source-facts digest and `frame_id` to the canonical structural frame key (selected XY basis/origin, datum/cut and B4 constants). Exclude full occupancy plane revision/Z/name/camera and volatile capture tokens. Add `test_reducer_bindings_use_stable_structural_source_and_frame`: capture reducer arguments across identical recapture, furniture-only edits, occupancy Z/revision/name edits and structural geometry/frame edits; assert only actual structural changes invalidate consent. Do not retain complete-scene/full-plane hashing behind a wrapper token.
- [ ] **Step 6: Run green and compatibility.**

```powershell
pixi run python -m pytest test/test_blender_analysis_capture.py test/test_bonsai_live.py test/test_blender_analysis_session.py test/test_b3_live_scene_capture.py test/test_b3_live_analysis_request.py test/test_b3_occupancy_only_handoff.py test/test_bonsai_analysis_plane.py -q
```

Existing: `test_evaluated_transform_once_then_blender_units_not_ifc_units`, `test_mesh_release_on_every_extraction_failure`, `test_enrollment_requires_unique_step_and_guid_preserves_extras_and_missing`, `test_failed_or_missing_proxy_refuses_occupancy_handoff`。

**Stop:** Generic loader changes source semantics；ambiguous canonical identity；required owner vanishes；raw fallback occurs；historical artifacts overwritten；actual mesh cannot cross handoff。

### Task T2: Localized unknown 的保守共享修复

**Files:** Modify `features/free_space_field.py`, `features/analysis_requests.py`, `test/test_free_space_field.py`, `test/test_analysis_requests.py`。Existing `features/section_views.py:exact_plane_section` 只读复用。

**Interfaces:** additive keyword `FreeSpaceField(..., unresolved_supports: Mapping[str, object] | None = None)`；`_occupancy(scene, request, excluded) -> tuple[list,list,dict]` 保持三返回，audit 增 trusted support；FieldStatus 六态不变；algorithm version advance。

- [ ] **Step 1: Add red tests.** New `test_free_space_field.py::test_unknown_support_localizes_only_trusted_intersections`、`::test_unknown_touch_is_conservative_while_mass_touch_stays_empty`、`::test_missing_or_malformed_support_stays_global_unknown`、`::test_qualified_empty_or_domain_outside_support_affects_no_cell`、`::test_unqualified_empty_stays_global_unknown`；new request `::test_unknown_support_requires_exact_selected_owner_query_and_complete_coverage` and nonzero plane/grid-origin alignment tests described below。

```python
assert occupied_sample.value is True  # known positive wins
assert local_support_cell.status is FieldStatus.UNKNOWN
assert unaffected_cell.value is False
assert touching_point_or_line_cell.status is FieldStatus.UNKNOWN
assert outside_support_cell.value is False
assert malformed_support_other_cell.status is FieldStatus.UNKNOWN
```

- [ ] **Step 2: Run red.** `pixi run python -m pytest test/test_free_space_field.py test/test_analysis_requests.py -q`；capture precise new failures。
- [ ] **Step 3: Implement minimal mask.** Freeze/validate mapping；missing/malformed/source absent/global None remain global unresolved；valid geometry clipped domain；unknown uses any nonempty intersection incl touch/line/point；known occupied wins；no tolerance buffer/precision change。Retain per-source support audit。Only selected owner/query/geometry identity matches and no required coverage failure permit reuse of existing section unknown_support_geometry；failed multiowner proxy global unless complete trusted union。Run support_status independent。

- [ ] **Coordinate seam tests:** Apply the same existing affine coordinate mathematics to all supported GeoJSON dimensions; do not feed line/point evidence through polygon-only `_components`. Add `test_translated_unknown_line_and_point_touch_preserves_dimension` with plane origin (100,200) and nonzero grid origin, checking local touch and wholly outside supports, alongside polygon alignment/qualified-empty/unsupported-basis tests.
- [ ] **Step 4: Run green.** `pixi run python -m pytest test/test_free_space_field.py test/test_analysis_requests.py test/test_physical_occupancy_section.py test/test_b3_occupancy_only_handoff.py -q`。Existing `test_unknown_support_does_not_erase_known_occupied_cells`, `test_line_contact_and_clipped_out_occupancy_do_not_fill_a_cell`, `test_failed_required_proxy_never_falls_back_to_original_mass`, `test_exact_section_uses_absolute_world_z_with_translated_xy_and_origin_z` must remain green。

**Stop:** Support localizes incomplete/refused coverage；occupied loses truth；mass touch becomes occupied；three-return contract changes；legacy absent mapping becomes optimistic。

### Task T3: Compact result、async lifecycle 与持久格式

**Files:** Extend `adapters/blender_analysis_session.py`, `test/test_blender_analysis_session.py`；create `blender_addon/order_analyzer_ui/runtime.py`, `test/test_blender_analysis_runtime.py`。No new core hierarchy/dependencies。

**Interfaces:**

```python
serialize_analysis_result(run: AnalysisRun, *, job_id: str, plane_uuid: str,
    plane_revision: int, domain_request_id: str, domain_session_revision: int) -> dict[str,object]
reconstruct_field_sample(document: Mapping[str,object], *, row: int, column: int) -> FieldSample[bool]
validate_analysis_result(document: Mapping[str,object], *, expected_job_id: str,
    expected_plane_uuid: str, expected_plane_revision: int,
    expected_semantic_key: str) -> ValidatedAnalysisResult
write_result_atomic(document: Mapping[str,object], *, path: Path) -> Path
list_analysis_results(documents: Sequence[Mapping[str,object]], *,
    kind: str | None = None) -> tuple[ResultMetadata,...]
open_analysis_result(documents: Sequence[Mapping[str,object]], *,
    result_ref: ResultRef, context: ResultReadContext) -> ReadOnlyResultSnapshot
read_analysis_sample(snapshot: ReadOnlyResultSnapshot, *,
    row: int, column: int) -> FieldSample[bool]
```

`ValidatedAnalysisResult` is concrete validated data-model result; `validate_analysis_result` rejects all serialized digest/token/schema mismatches; runtime additionally verifies current session/source/config/domain binding frozen tokens before publication。

- [ ] **Step 1: Add red tests.** New session `::test_compact_round_trip_preserves_every_field_sample`, `::test_dedupe_preserves_same_key_different_cell_values`, `::test_atomic_write_failure_retains_old_result`, `::test_payload_cannot_select_executable`；runtime `::test_aba_during_capture_never_publishes_current`, `::test_file_undo_unregister_invalidate_job`, `::test_furniture_change_stales_occupancy_not_domain_consent`, `::test_display_change_keeps_semantic_key`, `::test_load_never_resumes_process`。

```python
assert reconstructed.value == original.value
assert reconstructed.status == original.status
assert dict(reconstructed.provenance) == dict(original.provenance)
assert reconstructed.support == original.support
assert reconstructed.source_ids == original.source_ids
assert reconstructed.query == original.query
assert reconstructed.explanation == original.explanation
assert result_after_failed_publish is previous_result
assert runtime.freshness in {'stale', 'unverified'}
assert spawned_process_count_after_load == 0
```

Use equality of complete frozen records plus independently compare all public fields; do not rely on an invented `.to_dict()` for FieldSample。

- [ ] **Step 2: Run red.** `pixi run python -m pytest test/test_blender_analysis_session.py test/test_blender_analysis_runtime.py -q`。
- [ ] **Step 3: Serialize shared tables plus exact deltas.** Snapshot/query/lattice/source_audit once；cells row,col,value,status,explanation/source refs,support/provenance deltas；canonical equal-value dedupe；same key changed cell value preserved；strict JSON/digest/schema/algorithm；full sample round-trip。Do not copy old 150MB serializer or drop audit fields。Unique partial→final atomic publish preserves old final on error。

- [ ] **Read-only consumer contract:** Build minimum immutable ResultRef/metadata/context/snapshot records defined in data-model; list both `domain_session` and `free_space_run` from existing manifest/documents, exact-open one ref, and delegate sample reconstruction to existing FieldSample contract. Keep catalogue/wire stdlib-only (minimal sibling extraction only if heavy session imports require it); Field reconstruction is bpy-free in Pixi. Both live documents and restored Text documents use these exact entry points; no new mutable authority, registry/DSL/framework, auto-latest, capture/compute/mutation or future analysis implementation.
- [ ] **Concrete headless consumer tests:** Add `test_result_catalogue_lists_domain_and_free_space_metadata`, `test_exact_result_ref_rejects_missing_ambiguous_or_mismatched_identity`, `test_consumer_isolates_domain_plane_mode_revision_and_source`, `test_consumer_rejects_incompatible_versions_and_stale_as_current`, `test_consumer_preserves_unknown_conditional_and_full_provenance`, `test_readonly_snapshot_cannot_mutate_authority`, `test_consumer_never_captures_computes_or_spawns`, `test_live_and_embedded_results_use_same_reader_without_sidecar`, `test_unconfirmed_domain_is_diagnostic_only_not_confirmed_consumption`. Use distinct real fixture identities and both modes/revisions; assert a current snapshot may retain unknown/conditional, absent/unknown is never free, historical requires explicit allowance, diagnostic domain=None is readable but confirmed/current-domain demand rejects None, and read of domain samples/out-of-lattice indices refuses. Use call sentinels and nested mutation attempts, not a fake downstream analysis. Run with the existing T3 red/green commands and record exits.
- [ ] **Step 4: Implement main-thread capture + one process slot.** Validate configured root/Pixi executable；Popen hidden/no shell；CLI paths only；timer polls/cancel between chunks；budget target50ms, measure large to_mesh blocking call。Runtime states idle/capturing/running/cancelling/complete/failed/interrupted；freshness distinct。Freeze source/request/config/session tokens incl registry/helper/material/parent/modifier/frame, observe ABA edits conservatively, invalidate on load/undo/file switch/unregister。No heavy computation in handlers/draw；no bpy threads；older result retained on failure/cancel/stale。
- [ ] **Step 5: Run green.** `pixi run python -m pytest test/test_blender_analysis_session.py test/test_blender_analysis_runtime.py test/test_analysis_requests.py -q`；inspect output compact bytes versus old repeated metadata and exact full-cell equality, not an arbitrary optimistic size target。

**Stop:** Serialization loses any evidence；keys dedupe cell override；old result destroyed；unverified source marked current；payload executable accepted；load resumes worker；main-thread boundary broken。

### Task T4: Installable single panel、native overlay、inspect/restore

**Files:** Create `blender_addon/order_analyzer_ui/__init__.py`, `blender_addon/order_analyzer_ui/overlay.py`, `test/test_blender_analysis_overlay.py`；modify `runtime.py`, runtime tests；legacy B4 wrapper change by T1 owner only after service interface agreed。

**Interfaces:**

```python
build_overlay_mesh(result: ValidatedAnalysisResult, *, display_lift_m: float = .02) -> OverlayRecord
inspect_cell(result: ValidatedAnalysisResult, *, row: int, column: int) -> Mapping[str,object]
restore_embedded_result(text_body: str) -> ValidatedAnalysisResult
register() -> None
unregister() -> None
```

OverlayRecord is native vertices/faces/face-cell mapping from data-model; no second occupancy algorithm。Main-thread functions native typed objects can be fake tested, then native T5 proves Blender execution。

- [ ] **Step 1: Add red tests.** New overlay `::test_fragments_clip_exact_domain_and_holes`, `::test_multiple_faces_keep_one_cell_index`, `::test_old_overlay_stays_at_snapshot_pose_when_plane_moves`, `::test_restore_embedded_without_sidecar`, `::test_reject_newer_schema_or_malformed_digest`；runtime `::test_duplicate_uuid_needs_explicit_reassignment`, `::test_one_analysis_panel_and_one_b4_state`, `::test_save_copy_refuses_existing_live_path`。

```python
assert sum(fragment_areas) == pytest.approx(domain_clipped_cell.area)
assert all(domain_polygon.covers(face_polygon) for face_polygon in face_polygons)
assert overlay.parent is None
assert saved_snapshot_frame == restored_snapshot_frame
assert restored_full_cell_records == saved_full_cell_records
assert restored_freshness in {'historical', 'unverified'}
```

- [ ] **Step 2: Run red.** `pixi run python -m pytest test/test_blender_analysis_overlay.py test/test_blender_analysis_runtime.py -q`。
- [ ] **Step 3: Implement native display.** Pixi precomputes exact domain/holes clipping and existing constrained triangulation display-only + area checks；Blender consumes precomputed vertices/faces in measured bounded batches to build one/few tagged meshes；face cell_index/row/col/value/status attrs；stable index across fragments；frozen world frame no plane/camera parent。No Shapely/heavy-core import in addon. Separate lift outside query/key。Inspect boolean true=occupied false=empty, six status text, source/query/domain/support/limitations。Counts only, optional actual clipped classified area explicitly labelled, never exact free area count×spacing²。
- [ ] **Step 4: Implement installable registration/UI.** Local addon zip root order_analyzer_ui, bl_info minimum5.2；preferences root only；one N→Analysis panel with independently usable Domain section preserving every B4 capability in plan mapping and Free-space section containing plane/query/grid, Start/Cancel, stages/freshness, hide/show, inspect/result access, support binding, Save Copy。Use one shared session/reducer state, existing B4 service and existing free-space AnalysisRequest; no forced common lifecycle. Add `test_unified_domain_section_preserves_b4_controls_and_diagnostics` with tolerance/assumptions/counts/candidates/outline/hole/labels/current/attempt/refusal/stale/aperture assertions. Default wholeheight/.25, exact plane origin.z authority。Reject unsupported units/tilt/scale and duplicate UUID; explicit duplicate flow new UUID/results historical。
- [ ] **Step 5: Embed/restore persistent result.** Tagged plane+overlay and fake-user strict JSON Text; save regular scene metadata without autoexec。Save Copy unique suggested target, explicit path validated different live/existing target, `bpy.ops.wm.save_as_mainfile(filepath=target, copy=True)`。Restore independent sidecar, historical/unverified, no process startup; malformed/future schema diagnostic and keep previous artifact。

- [ ] **Save Copy failure test:** New runtime `test_save_copy_exception_preserves_live_truth_and_cleans_owned_partial` injects a native `save_as_mainfile` exception after an owned partial target exists. Assert live Text/overlay/result identity and bytes survive, only addon-owned partials are cleaned, unrelated/preexisting files survive, and no saved artifact is recorded. Follow with successful Save Copy and assert the artifact is recorded only after native success; add the same injected native failure to T5 smoke/report evidence.
- [ ] **Step 6: Run green.** `pixi run python -m pytest test/test_blender_analysis_overlay.py test/test_blender_analysis_runtime.py test/test_bonsai_analysis_plane.py -q`。

**Stop:** Color becomes truth；plane edits drag old answers；second B4 state exists；IFC camera creation required；save overwrites live file；imported Text executes；sidecar mandatory to restore。

### Task T5: Real operators、两模式 live 与独立 save/reopen acceptance

**Files:** Create `test/bim/run_blender_analysis_workflow_smoke.py`；disposable generated artifacts only in unique `outputs/design/blender_analysis_workflow/run_<UTC-and-UUID>`（由 smoke/runtime生成，不提交）；update checklist evidence。No alternate occupancy/domain implementation in smoke。

**Interfaces:** smoke CLI `--addon-zip`, `--repo-root`, `--output-dir`, `--phase smoke|reopen`, `--blend-path`；uses actual installed operators/service/serialization, reports JSON timings/cells/identities/digest/IFC unchanged。Defaults unique outputs, rejects overwrite。`--blend-path` required for reopen phase。

- [ ] **Step 1: Package and install only approved portable addon.** Generate zip via stdlib `zipfile` from addon directory, exact path recorded in checklist. Native API availability probe is insufficient; execute real install/enable and assert operator availability. Proposed command after produced archive:

```powershell
& 'D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe' --background --factory-startup --python-exit-code 1 --python test/bim/run_blender_analysis_workflow_smoke.py -- --phase smoke --repo-root 'D:\PROJECTS\understandOtherPackage\order_analyzer'
```

Smoke generates its unique zip/output paths if omitted; defaults are implementation-fixed from repo root, not unspecified user placeholders. Synthetic confirm in disposable fixture uses explicit test actor and is labelled fixture-only, never live human consent。

Output root is `D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\blender_analysis_workflow\run_<UTC-and-UUID>`. The background script uses the real runtime timer/bounded main-thread pump until the actual asynchronous job completes, then asserts a written valid `smoke_report.json` with `status=success` before exit. Timeout/error raises with `--python-exit-code 1`; immediate exit after Start is failure. [quickstart.md](quickstart.md) gives concrete unique-path generation and report assertions.

- [ ] **Step 2: Visible live flow.** Actual N→Analysis create plane → Refresh B4 → Select → human explicit Confirm；no current confirmation: stop and identify required action, never choose historical S3。Show B4 cut1.5 and exact plane Z distinction；support unbound warning/raw calculation or verified explicit support binding。Inspect actual holes/membership/canonical source/proxy audit。
- [ ] **Standalone B4 and consumer acceptance:** Before free-space Start, exercise Domain-only Refresh/tolerance/Select/Confirm and collect visible evidence for all plan mapping capabilities, including significant aperture residual diagnostics and last-attempt/current/refusal/stale states. Report exact B4 service payload parity; no reducer-only action called prior UI parity. After run/save/reopen, call the same headless list/open/sample interface on live and embedded documents with sidecar removed; compare domain diagnostics and all free-space sample evidence. Reject cross-domain/plane/mode/revision and historical-as-current; prove reader never starts a job. This is contract acceptance, not a claimed downstream analysis.
- [ ] **Step 3: Execute both modes .25.** Wholeheight default and exact plane-origin.z1.6 via real Start；report stages/elapsed/longest to_mesh/callback, responsive view navigation, all sources/remaining unknown reasons, proxy exact-once and plants/counter/furniture occupancy。No fake ETA or precision lowering。
- [ ] **Step 4: Lifecycle attacks.** During capture and subprocess: source transform/modifier/factual change/revert ABA, plane edit, undo, file switch, cancel and child failure；old mesh old pose+stale, no wrong current publish, old truth retained, process slot released。Test display-only color/lift/name remains key-stable。
- [ ] **Step 5: Save Copy/reopen.** Real Save Copy to unique new path；record original blend/IFC byte+transaction fingerprints before/after；delete optional sidecar only after embedded truth verified。Launch the same approved binary in a separate authorized process with the actual `saved_copy_path` read from successful smoke report, `--python-exit-code 1`, and `--phase reopen --blend-path $savedCopyPath` (full command/report assertions in quickstart). Save failure retains live Text/overlay/result, cleans only owned partials, and records no saved artifact. Compare every cell value/status/full sample/source/plane/domain identity and overlay face mapping/digest; no process/autoexec and historical/unverified on restore。Before Start revalidate current IFC/project/GUID mapping/fingerprint/domain/support bindings; linked IFC absent shows offline result and recompute dependency。

**Command/exit evidence:** Native tests write a machine report and stdout/stderr paths under unique output root; owner copies exact invoked command and exit into checklist。A visual-panel assertion requires visible UI interaction evidence in addition to background smoke。

**Stop:** Missing live domain confirmation；unresolved source silently discarded；lack UI response incorrectly reported complete；IFC/live blend altered；save/reopen cell mismatch；native failure. Do not relabel fixture success as live acceptance。

### Task T6: Independent review、architecture sync 与 scoped jj

**Files:** Review all assigned implementation/test paths；modify `docs/software-architecture.md`, `docs/indoor_layout_evaluation_matrix_architecture_memory.md` and Spec004 checklist only for actual evidence。Designated version specialist owns VCS writes and workspace lifecycle, preferring jj/jj workspace with Git fallback per project memory; implementation/review workers do not write version history or manage workspaces。

**Interfaces:** consumes T1–T5 green evidence, produces independent review + owner acceptance + scoped local delivery。No push/merge authorization is implied。

- [ ] **Step 1: Independent review.** Reviewer checks complete independent B4 UI/service parity, unified sections/shared boundaries, read-only consumer identities/versions/freshness/immutability/no-side-effect tests, exact mesh object handoff, canonical identities/migration refusal, support binding/proxy no-fallback, physical inventory, unknown safety, freeze/ABA, compact full round-trip, frozen overlay frame, sidecar-free reopen, no IFC write, import/no-dependency boundaries。Findings include actionable file/line/evidence；implementer fixes before recheck。
- [ ] **Step 2: Final focused suite.**

```powershell
pixi run python -m pytest test/test_blender_analysis_capture.py test/test_bonsai_live.py test/test_blender_analysis_session.py test/test_blender_analysis_runtime.py test/test_blender_analysis_overlay.py test/test_analysis_requests.py test/test_free_space_field.py test/test_physical_occupancy_section.py test/test_b3_live_scene_capture.py test/test_b3_live_analysis_request.py test/test_b3_occupancy_only_handoff.py test/test_bonsai_analysis_plane.py -q
```

- [ ] **Step 3: Sync architecture actual state.** Mark addon/new adapter/lifecycle implemented only for accepted artifacts；B3 OPEN, clearance/routing/3D/complete-free-space not delivered；link native/live output evidence and contract。Check root exports unchanged/module-qualified request imports。
- [ ] **Step 4: Scoped version handoff.** Version specialist prefers verified jj 0.45.1 read-only commands `jj --ignore-working-copy status` and `jj --ignore-working-copy diff --summary` to audit existing dirt, with Git fallback per project memory when needed. In an isolated clean workspace, preferably managed through `jj workspace`, apply only the hash-validated task delta plus approved dependency closure; verify exact included paths/hashes before any authorized checkpoint. Read-only fileset audit syntax supported by this version is `jj --ignore-working-copy diff --summary specs/004-blender-analysis-workflow docs/software-architecture.md docs/indoor_layout_evaluation_matrix_architecture_memory.md`. Never invent a path-scoped snapshot command or snapshot the dirty working copy; no push/merge without separate explicit user instruction。
- [ ] **Step 5: Owner gate.** Owner records independent findings resolution, evidence sufficiency and accepted/changes-requested state. No missing validation is silently waived。If incomplete, leave exact pending items and implementation state rather than claiming success。

**Stop:** Review has open correctness findings, architecture drift, missing live/native evidence, unclear jj path isolation or missing explicit push/merge authority。

## Required task seam checks

- T1: B4 service must consume actual structural_scene and StructuralContext datum0/cut1.5/XY basis, never just a structural token over occupancy-plane geometry. Start verifies full capture freshness and recaptures once if needed; derive both views/digests from that capture. Stable structural/full digests include sorted stable project/source/geometry/transform/config/version facts, excluding time/runtime pointers/selection/dirty/visibility/camera/IFC transaction/mtime/capture-job-session UUID; structural digest additionally excludes occupancy-only facts. Add unchanged-recapture/furniture-only/query-Z isolation tests.
- T1/T3: SupportBinding validation resolves the unique source_object_id to canonical source.source_id (GlobalId), only in the request-scoped child domain reaching `_scope_exclusions`; shared inferred B4 source_id stays None. Test bound slab exclusion, unbound/rejected raw slab preservation and no class-wide exclusions.
- T2: Distinguish valid_nonempty/validated_empty/missing_or_malformed; qualified empty needs trusted identity/query/complete-coverage proof. Missing/malformed/failed-target/incomplete or ambiguous multi-owner support is global. Raw unknown support is world XY; apply the same existing affine frame mathematics exactly once before FreeSpaceField intersection, preserving polygons, lines, points and qualified empty instead of routing through polygon-only `_components`. Preserve raw geometry plus units/frame/transform audit. No new geometry algorithm or core→adapter import. Add nonzero plane origin (100,200), nonzero grid origin, translated line/point touch, matching occupied/unknown/outside placement, transformed validated-empty and unsupported-basis conservative refusal tests.
- T3/T4: Blender imports remain stdlib+bpy/lightweight wire records. Shapely/heavy core and clipped display triangulation stay in Pixi. Capture, JSON validation/handoff, Text assembly/write, mesh construction and polling use bounded main-thread batches with 50 ms target, callback/atomic-call elapsed, JSON bytes and mesh counts. On overruns report duration and reduce subsequent batches; do not promise preemption. Test addon imports without heavy dependencies and cancel/error during publish keeps old truth.
- T4/T5: Save Copy failure retains live Text/overlay/result, cleans only owned partials, records artifact only after successful native save. Reopen is historical/unverified; Start revalidates IFC/project/GUID mapping/fingerprint/bindings. Test rejected/recovered stale bindings. CameraBinding stays display-only, absent from geometry/keys/occupancy and unchanged by computation.

## Writer and dependency ownership

T0 precedes code. T1 capture/canonical/service changes sequentially one writer, with wrapper migration owned by same writer. T2 can run after T1 source/support contract frozen, owns only two core files/tests. T3 extends session only after T1 releases it, owns runtime. T4 owns panel/overlay after T3 compact contract frozen. T5 needs integrated T1–T4; T6 reviewer is independent and version specialist sole VCS writer. No two active writers overlap files; downstream uses exact contract signatures above.
