# Spec004 Review 与证据 Checklist

**APPROVED / IMPLEMENTATION IN PROGRESS — 2026-10-15。** 用户已批准并授权执行；所有 implementation/unit/native/live/reopen 验证仍未运行。PENDING 是真实状态，不能作为 PASS。native acceptance 仍 pending，B3 仍为 OPEN。

## 本轮实际完成

- [x] 先读 architecture memory，再读 software-architecture；核对实际 paths 与 Git reference；当前 request/plane/live-capture 为 CURRENT TREE ABSENT，B4/domain handoff 存在。
- [x] 读 speckit-plan 和 Superpowers writing-plans；grill-me 文件实际仅 `Run a /grilling session`，记录 owner adversarial Q/A，未声称 automated skill PASS。
- [x] inspect `.specify/extensions.yml`：`hooks: {}`；before/after 无 executable hook。
- [x] inspect constitution：未 ratified template，非 PASS。
- [x] process-only `SPECIFY_FEATURE=004-blender-analysis-workflow`、absolute feature directory、`SPECIFY_FEATURE_NO_PERSIST=1` setup-plan 成功；工具 process exit0；返回 feature spec/plan/directory 与 identifier；没有 VCS branch write。
- [x] 写实际 spec/plan/research/data-model/contract/quickstart/tasks/checklist。
- [x] 用户于 2026-10-15 批准计划并授权实施；owner 后续实现验收和独立 review 仍需实际证据。

## 计划自查（writer）

- [x] FR01–FR22 都有 task/test/native acceptance mapping（见下表）。
- [x] planned APIs 与 currently existing APIs 分开；新模块现在不存在。
- [x] `_occupancy` 三返回、generic Blender identity、六态 FieldStatus、shared resolver/registry/MassPatch 兼容边界明确。
- [x] owner seam corrections: canonical IFC map、actual domain mesh、support/proxy no fallback、localized unknown、ABA/freshness、compact exact reconstruction、frozen overlay、save/reopen 写入所有依赖文档。
- [x] Read-only static scan: all eight Spec004 Markdown files exist with approval/in-progress markers and headings; local Markdown links resolve; old pytest invocation, smoke path placeholders and fictitious snapshot/checkpoint syntax removed. No production validation inferred.

## FR → task → focused test / acceptance

新名字是计划新增测试；Existing 为 checkpoint/source 参考名称，T0 必须在隔离 baseline 逐项验证存在和 import closure，不能当作当前磁盘已可运行。

| FR | Task | Unit/contract 检查 | Native/live evidence |
|---|---|---|---|
| FR01 stable one-panel addon | T4,T5 | new runtime `test_one_analysis_panel_and_one_b4_state` | install/enable + visible N→Analysis |
| FR02 owned UUID/frame/unsupported modes | T4 | new `test_duplicate_uuid_needs_explicit_reassignment`; Existing bonsai plane validation tests | plane edit/scale/tilt rejection |
| FR03 B4 explicit consent/events | T1,T3,T4 | new session `test_select_does_not_confirm`; handoff session audit | actual Refresh/Select/human Confirm |
| FR04 canonical one-capture identities | T1 | new canonical `test_canonical_identity_map_requires_project_guid_step_and_geometry` | capture/source map |
| FR05 exact domain mesh | T1,T3 | new session `test_handoff_returns_exact_qualified_mesh_without_retriangulation` | geometry refs/digest/holes |
| FR06 modes/.25/plane Z | T1,T3,T5 | Existing request `test_exact_section_uses_absolute_world_z_with_translated_xy_and_origin_z` | both .25 modes, B4 cut1.5 distinct |
| FR07 structural/full fingerprint | T1,T3 | new runtime `test_furniture_change_stales_occupancy_not_domain_consent` | source/confirmation report |
| FR08 exact floor support/member | T1,T5 | new canonical `test_unbound_floor_remains_occupancy`; Existing request `test_only_exact_confirmed_boundary_membership_excludes_doors` | support warning/binding/membership |
| FR09 exact-once/proxy/physical sources | T1,T5 | new `test_required_proxy_refusal_never_restores_raw_owner`; Existing request `test_failed_required_proxy_never_falls_back_to_original_mass` | plants/counter/furniture inventory |
| FR10 local unknown safety | T2 | new `test_unknown_support_localizes_only_trusted_intersections`, touch/global/outside/coverage cases | percell vs run support evidence |
| FR11 main-thread async/cancel | T1,T3,T5 | capture/runtime fake process tests | real callback/mesh times and UI response |
| FR12 ABA/session/frozen result | T3,T4,T5 | new runtime `test_aba_during_capture_never_publishes_current`; new overlay old-pose test | live edit/revert/undo/file-switch |
| FR13 configured Pixi/hidden process | T3 | new `test_payload_cannot_select_executable`; fake Popen | process argv/window audit |
| FR14 compact exact recoverable | T3 | new `test_compact_round_trip_preserves_every_field_sample`, dedupe/atomic cases | size/digest/full-cell compare |
| FR15 mesh clipping/index | T4 | new `test_fragments_clip_exact_domain_and_holes`, `test_multiple_faces_keep_one_cell_index` | holes/multiple fragments attrs |
| FR16 text inspect/area honesty | T4,T5 | inspect reconstructed sample equality | visible status/support/counts |
| FR17 embedded save/reopen | T3,T4,T5 | new `test_restore_embedded_without_sidecar`, `test_save_copy_exception_preserves_live_truth_and_cleans_owned_partial`, schema/digest rejection, no-load-process | real Save Copy/injected native exception + separate process |
| FR18 imports/dependency boundary | T1,T3,T4,T6 | Existing `test_native_core_imports_avoid_legacy_heavy_modules` | Pixi/approved binary audit |
| FR19 true acceptance | T5 | persistent native smoke real operators | .25 two modes, offline recovery/IFC unchanged |
| FR20 review/docs/jj | T0,T6 | independent review and architecture diff | owner evidence, sole scoped version writer |
| FR21 existing service/operation boundaries | T0,T1,T3,T6 | B4 independence; existing AnalysisRequest/Field/resolver regressions | shared capture/identity/domain/read boundary; no new job/result registry |
| FR22 immutable read-only consumer | T3,T4,T5 | exact-ref/missing/ambiguity/version/source/domain/plane/mode/revision isolation; no effects; unknown/conditional/provenance; nested immutability | live/embedded same reader with no sidecar; historical-as-current rejection |

## 执行证据 ledger（当前均 PENDING）

各任务完成时新增一行完整记录：`date | task | actual command | exit | stdout/stderr/report absolute paths | conclusion | reviewer`。路径由运行时唯一 run dir 产生，执行后填写，不预造文件。

| Task | Status | Evidence needed |
|---|---|---|
| T0 baseline/user design gate | IN PROGRESS; user gate APPROVED 2026-10-15 | Version specialist conducting isolated `23d24a3` full approved dependency/import closure verification + hashes + caller report + baseline exit/log; baseline evidence pending |
| T1 capture/canonical/domain | PENDING | new red/green + existing regressions + verified source map/mesh identity |
| T2 local unknown | PENDING | touch/line/point/outside/malformed/global/proxy coverage tests |
| T3 compact/lifecycle | PENDING | exact whole FieldSample roundtrip, shared table size, atomic failure, ABA/cancel |
| T4 addon/overlay/restore | PENDING | single panel, fake-user Text, clipped mesh/index, no live-parent, embedded restore |
| T5 native/live/reopen | PENDING | exact commands/exits, .25 two queries, user consent, response/times, Save Copy/separate reopen, IFC unchanged |
| T6 independent review/docs/jj | PENDING | independent findings/resolution, architecture synchronization, scoped path-only jj by specialist |

## Owner seam review（实施前后都应回答）

- [ ] Unified workbench has independently collapsible Domain/Free-space sections and independently usable complete B4 controls/diagnostics per plan mapping. T1 `test_domain_session_preserves_existing_b4_payload` / `test_domain_workflow_independent_of_free_space_request`, T4 `test_unified_domain_section_preserves_b4_controls_and_diagnostics` and T5 Domain-only operator evidence cover FR01/03. Significant aperture residuals, current/attempt, tolerance and counts remain; reducer-only replace/conflict is not prior UI parity.
- [ ] T3 read-only list/exact-ref open/sample tests cover versions/identities/freshness/immutability/no-effects, current unknown/conditional and full provenance. Unconfirmed domain None is diagnostic-only; confirmed/current-domain demand rejects None. T5 verifies same live/embedded reader without sidecar. No auto-latest, mesh truth, extra registry or claimed real downstream analysis.
- [ ] canonical id `ifc-object:{GlobalId}`；legacy map 验证 STEP/GUID/project/source/geometry/coverage，拒绝 blind rewrite；generic Blender source_id=None 保留。
- [ ] 一次 full capture，B4 structural view 同 source/geometry refs；structural/full tokens 分离。
- [ ] inferred source_id None；actual `_qualified` mesh 直接 `domain_geometries`；无重建或 preview 真值。
- [ ] B4 cut1.5 与 exact plane-origin Z 分离，analysis Z 本身不自动撤销合法 XY consent。
- [ ] floor support 显式唯一/current；未绑定警告不删除 slab、不阻 raw calculation；无硬编码/类全排除。
- [ ] 所有 physical furniture/plant/counter 保留；required failed proxy unresolved 不 raw fallback；旧三 hull/七 owners scope verified。
- [ ] local unknown 仅可信 exact owner/query/geometry 完整 coverage；bad/missing support global；occupied wins；touch conservative。
- [ ] job/session/plane/request/source/config/digest all match 才 current；ABA/file/undo/load/unregister invalidation；uncertain→unverified。
- [ ] overlay frozen snapshot world frame/no live parent；display lift separate；holes/index stable；color 非真值。
- [ ] full FieldSample exact reconstruct，same-key different-value 不丢；unique atomic final 错误保留旧值。
- [ ] main-thread bpy、无重 draw/handler、hidden no-shell Pixi、one process slot、no payload executable。
- [ ] embedded fake-user strict JSON、sidecar-free reopen、future schema拒绝、no autoexec/autostart。
- [ ] 显式新 Save Copy copy=True、独立授权 portable process reopen、原 blend/IFC 不变证据。
- [ ] fixture/native API availability/live acceptance 分清；B3 OPEN、clearance/routing/3D 未交付。

## 用户设计审阅 gate

- [x] 用户于 2026-10-15 以 spec.md 与 plan.md 为主要审阅入口批准计划并授权执行，其他 artifacts 提供支撑；无需逐签八份。
- [x] 用户批准后状态切换为 APPROVED / IMPLEMENTATION IN PROGRESS；生产实现与验收仍需独立证据。
- [ ] delegation 已选择，不再追问 execution method。
- [ ] 如现场缺当前合法 ROI，只要求具体 select/confirm 动作；不自动确认历史 S3 或合成用户行为。

## Final documentation seam checks (implementation remains pending)

- [x] Current-tree facts distinguish absent request/plane/live-capture from existing B4/domain handoff; checkpoint `23d24a3` is reference evidence, not current implementation. T0 requires isolated full approved dependency/import closure, preferring a jj workspace with Git fallback per project memory, preserving dirty history; missing Spec003 docs preferably use `jj --ignore-working-copy file show -r 23d24a3 <path>`.
- [x] B4 receives actual structural_scene/context datum0/cut1.5/XY basis; structural/full stable digests exclude volatile/time/runtime/selection/dirty/camera/IFC transaction/mtime, structural also excludes occupancy-only data; Start checks/rebuilds current full capture once.
- [x] Unique SupportBinding resolves canonical source_object_id→source.source_id GlobalId only in request child domain→_scope_exclusions; inferred B4 source_id stays None.
- [x] Unknown support has valid_nonempty/validated_empty/missing-or-malformed distinction; empty proof and complete owner coverage required, failures global. WorldXY support transforms exactly once to plane-local cells via existing occupied transform, retaining raw/frame/unit/transform audit; nonzero plane/grid-origin and unsupported-basis tests planned.
- [x] Lightweight addon imports; Shapely/heavy core and display triangulation in Pixi; main-thread capture/JSON/Text/mesh/poll batching measures elapsed/bytes/counts and handles overruns honestly.
- [x] Save Copy failure preserves live Text/overlay/result and cleans only owned partials; success records artifact. Reopen historical/unverified, fresh Start verifies IFC/project/GUID/mapping/fingerprint/bindings. CameraBinding remains display-only.
- [x] Commands use pixi run python -m pytest and Blender --python-exit-code 1; unique concrete repository output root, bounded real async smoke pump, success report existence/status assertions and report-derived reopen path documented.
- [x] User clarified jj-first version/workspace management, including delegation and remote pushes through `jj git push`; Git/Git worktree fallback is allowed when jj is unavailable or cannot perform the required operation, with a brief concrete reason. AGENTS, project memory, architecture, plan and tasks agree. Installed `jj --ignore-working-copy workspace --help` and `jj --ignore-working-copy file show --help` returned exit 0 on 2026-10-15; these verify command availability, not workspace creation or delivery. Future delivery prefers an isolated clean jj workspace plus hash-validated task delta/approved dependency closure. No blanket/path-snapshot command.
- [x] Closure review documentation fixes specify actual reducer `source_revision`/`frame_id` wiring and T0 caller audit, dimension-preserving affine support conversion with translated line/point tests, and injected native Save Copy failure assertions in tasks/quickstart.
- [x] User scope correction is reflected in all eight docs and both planned architecture sections: unified workbench, complete independent B4 capability mapping, existing service/operation contracts, immutable read-only consumer contract and concrete headless tests; no downstream analysis implementation claimed.
- [ ] Implementation evidence: reducer arguments remain stable across recapture/furniture/occupancy-plane edits; translated line/point touches survive coordinate conversion; injected `save_as_mainfile` failure preserves live Text/overlay/result, removes only owned partials, records no artifact, and subsequent success records one only after native save success.
- [x] User spec/plan review gate approved and implementation authorized on 2026-10-15; no production acceptance inferred.

This documentation pass ran only read-only document/path/link/status scans. No production tests, Blender validation, addon installation, .blend save/reopen or VCS write ran. User approval is complete; T0 baseline is IN PROGRESS under the version specialist, and T1–T6 implementation/acceptance evidence remains PENDING. Durable task progress is [progress.md](../../.superpowers/sdd/004-blender-analysis-workflow/progress.md).
