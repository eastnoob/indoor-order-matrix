
# AnalysisContext Ancestor Integration Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

Goal: Make the scene-level AnalysisContext the single-plane ancestor for every evidence-package call while preserving explicit package-plane replacement, multi-plane admission checks, unused-plane behavior, cache boundaries, and existing single-plane compatibility.

Architecture: Keep AnalysisPlane as an immutable value object, AnalysisContext as the existing scene-level immutable record with exactly one required analysis_plane, and PackageAnalysisContext as a per-call frozen tuple of one or more planes. Extend the existing resolver and EvidencePackage boundary so a scene context supplies its default plane, while an explicit package context replaces it without merging. Keep UI/native persistence outside this phase.

Tech Stack: Python 3.12 under Pixi; pytest; Jujutsu (jj) for workspace/checkpoints; existing dataclass and cache contracts.

Spec: docs/superpowers/specs/2026-11-18-analysis-context-ancestor-design.md

## Global Constraints

- AnalysisContext owns exactly one explicitly supplied default AnalysisPlane.
- Every EvidencePackage.evaluate() and process_output() admission resolves a non-empty PackageAnalysisContext before producer, processor, storage, or cache work.
- A package-level explicit plane set replaces the ancestor default; it is never automatically appended.
- Multiple planes require both package capability and explicit call permission.
- A package may receive a context and ignore it without projection, grid, model extraction, or unrelated cache invalidation.
- Actual plane-dependent algorithms own their plane identity/revision dependencies.
- Existing source-query plane inference remains only as a narrow migration compatibility path; the new scene-context path is canonical.
- No Ancestor base class, global mutable registry, UI panel work, .blend lifecycle work, or new dependency.
- Preserve all unrelated dirty work already present in the default jj workspace.
- Every changed function keeps an English docstring; important inference and cache decisions receive concise why-comments.

## jj execution and rollback design

The default workspace contains unrelated dirty work. The verified starting root is `d6ab0f9a9aca3746ed3125aa2b43f0078b1a5472`; an older draft referred to `f457f56f`, which is not the recovery baseline for this delivery. Do not reset, abandon, overwrite, merge, or push the default workspace.

1. Capture the default workspace state with jj --version, jj --ignore-working-copy status, jj --ignore-working-copy log -r '@' -n 8, and jj diff --stat.
2. Create a dedicated workspace named analysis-context-ancestor-20261118 from the current owner revision, then apply the captured working-copy diff into that workspace so this implementation is isolated while the original dirty workspace remains recoverable.
3. Use local jj checkpoints named context-root, package-contract, caller-migration, dependency-and-tests, and documentation-and-verification.
4. Each checkpoint records a narrow, reviewable change with jj describe and jj new; no remote push is performed.
5. Recovery selects a named checkpoint or its preceding immutable revision. The original default workspace is never rewritten.

---

### Task 0: Preflight and design gate

Files:
- Create: docs/superpowers/plans/2026-11-18-analysis-context-ancestor-implementation.md
- Inspect: the design spec, software architecture, architecture memory, scene_contract.py, package_analysis_context.py, field_core.py, and direct package callers.

Interfaces:
- Establish the resolver and boundary signatures used by Tasks 1–3.
- Produce a design-review record before code changes.

- [x] Write this plan and record jj preflight.
- [x] Self-review the plan against every design-note requirement.
- [x] Run an independent Grill-Me review of the design and plan. Challenge default inheritance, explicit replacement, multi-plane admission, compatibility inference, cache behavior, and dirty-work rollback; record findings and rulings.
- [x] Create the isolated jj workspace and verify its starting diff.

Expected gate evidence: plan, Grill-Me review/rulings, workspace name, and intended file list.

### Task 1: Ancestor-aware package context resolver

Files:
- Modify: features/package_analysis_context.py
- Test: test/test_package_analysis_context.py

Interfaces:
- Consumes AnalysisContext.analysis_plane, PackageAnalysisContext, and existing source-query compatibility inference.
- Produces:
  resolve_package_analysis_context(source_envelopes=(), *, analysis_context: AnalysisContext | PackageAnalysisContext | None = None, package_planes: Iterable[AnalysisPlane] | None = None, supports_multiple_planes: bool = False, allow_multiple_planes: bool = False) -> PackageAnalysisContext
- The result is frozen and contains at least one validated plane.

- [x] Add failing tests for scene-default inheritance, explicit single-plane replacement, and explicit multi-plane replacement; implemented and green in the focused resolver suite.
- [x] Add failing tests for duplicate/non-plane/empty package sets, conflicting resolver arguments, and preservation of the unique source-query migration path; implemented and green in the focused resolver suite.
- [x] Implement the smallest resolver change: a scene AnalysisContext contributes only its analysis_plane when package_planes is absent; explicit package_planes or PackageAnalysisContext replaces it; existing boolean checks remain; no numerical work is performed.
- [x] Run focused resolver tests; 39 passed and 1 namespace smoke test was deselected in the isolated workspace.
- [x] Self-review and Task 1 Grill-Me completed; no blocking findings.
- [x] Create jj checkpoint context-root (`c3065a40`).

### Task 2: EvidencePackage boundary contract

Files:
- Modify: features/field_core.py
- Modify: features/output_port_cache.py only if boundary forwarding requires it
- Test: test/test_package_analysis_context.py, test/test_evidence_package_output.py, test/test_evidence_package_processing.py

Interfaces:
- EvidencePackage.evaluate and process_output accept AnalysisContext | PackageAnalysisContext, optional package_planes, and allow_multiple_planes.
- EvidencePackageInput.analysis_context remains the resolved PackageAnalysisContext delivered to context-aware callbacks.

- [x] Add failing tests that scene context reaches callbacks, explicit package planes replace it, and invalid admission occurs before producer/processor/storage work.
- [x] Add package_planes keyword-only parameters and resolve once at the top of both methods.
- [x] Keep plain output_function(envelopes) behavior unchanged for algorithms that intentionally ignore context.
- [x] Run focused boundary tests; 256 passed and 1 namespace smoke test was deselected.
- [x] Self-review and Task 2 Grill-Me completed; no blocking findings.
- [x] Create jj checkpoint package-contract (`59871409`).

### Task 3: Migrate production package and port entrypoints

Files:
- Modify: adapters/free_space_evidence_package.py
- Modify: features/group_axis_potential_field.py
- Modify: features/group_axis_output_ports.py
- Modify: features/group_distance_evidence_package.py
- Modify: features/group_distance_output_ports.py
- Modify: features/output_port_cache.py
- Modify any additional direct evidence-package evaluate/process_output caller found by rg.
- Test the corresponding package and runner suites.

Interfaces:
- Every production evidence-package runner resolves a scene AnalysisContext or explicit PackageAnalysisContext before invoking the package; no direct production call bypasses the resolver.

- [x] Enumerate direct calls with rg and classify field-level calls versus package calls; the audit is retained in the Task 3 review and verification record.
- [x] Add focused runner coverage through the context propagation and lifecycle tests.
- [x] Forward package_planes where a caller exposes package-level selection; resolve once per runner and pass the frozen snapshot to nested calls.
- [x] Run available targeted suites; group-distance/lifecycle 125 passed, group-axis 137 passed with 8 missing-retained-artifact failures, and the nested-worktree free-space suite could not collect due relative imports.
- [x] Self-review and Task 3 Grill-Me completed; no migration findings.
- [x] Create jj checkpoint caller-migration (`79fd3865`).

### Task 4: Plane-use and cache dependency verification

Files:
- Modify features/output_port_cache.py only if a real missing dependency is demonstrated.
- Test: test/test_package_analysis_context.py, test/test_output_port_cache.py, and relevant lifecycle tests.

Interfaces:
- Context admission is selection-only; ignored planes preserve output/cache identity; plane-using callbacks declare their own plane dependencies.

- [x] Add a context-aware package test that ignores the snapshot: P0/P1 output and cache identity stay equal and no projection/model/grid helper is called.
- [x] Add a context-aware package test that uses the snapshot: declared plane identity/revision makes P0/P1 identities distinct.
- [x] Run relevant cache/lifecycle tests; 194 passed with the known nested-worktree namespace smoke failure, plus 2 focused cache tests passed.
- [x] Self-review and Task 4 Grill-Me completed; no generic cache change was needed.
- [x] Create jj checkpoint dependency-and-tests (`56c120e4`).

### Task 5: Architecture synchronization and final verification

Files:
- Modify docs/software-architecture.md
- Modify docs/indoor_layout_evaluation_matrix_architecture_memory.md only where the package-context selection entry is stale.
- Modify this plan with exact evidence.
- Create docs/project/evidence/analysis-context-ancestor-verification-2026-11-18.md

- [x] Update prose and diagrams to state one scene default, per-call snapshot, explicit replacement, and deferred UI/native lifecycle. Evidence: `docs/software-architecture.md` and the architecture memory entry, updated 2026-11-18.
- [x] Run static call audit: `rg -n "\.evaluate\(|\.process_output\(" features adapters blender_addon --glob "*.py"`. Fresh result: 21 matches; package-relevant calls forward `analysis_context`/the resolved snapshot, while field/affordance evaluators are unrelated non-package APIs. Classification is recorded in the verification record; script callers were also reviewed and migrated.
- [x] Attempt the full test suite and report its actual outcome. The nested-workspace `pixi run pytest test/ -q` stopped with 48 collection errors. A package-shaped jj acceptance checkout at `94838661`, with OCTA available, subsequently reached 317 passed and one missing historical B3 fixture setup error using `test/ -q --maxfail=1`. Whole-repository success remains unverified; this checked item records execution, not a passing gate.
- [x] Run final independent Superpowers review and final Grill-Me review; repair findings. Grill-Me returned PASS and Superpowers returned SPEC PASS / QUALITY PASS. Stale pending ledger text was repaired; the later evidence follow-up and its reproduction correction are recorded below.
- [x] Record commands, checkpoint IDs, and limits. Historical subsets and failures remain historical. Final package-shaped selected runs cover 830 distinct passes and two explicit native-publication skips, with no failures/errors across 832 distinct nodes; the formerly failing namespace smoke test is included and passes. Eleven retained artifacts were copied with matching hashes, without recomputation. See the verification record and machine-readable acceptance summary for exact reports, source identity, and skip reasons. No UI/.blend lifecycle or full physical-model acceptance is claimed.
- [x] Create jj checkpoint documentation-and-verification; do not push or merge. The final local checkpoint is created after this ledger update and is recorded in the verification evidence and final response.

## Completion gate

Complete only when inheritance, replacement, multi-plane permission, invalid-input ordering, ignored-plane identity, plane-using dependency, caller coverage, architecture synchronization, and jj rollback checkpoints are all evidenced by fresh tests or explicit review records. UI and .blend lifecycle work remain deferred.

Core-feature completion is distinct from whole-repository or integration acceptance. This delivery satisfies the former in an isolated jj workspace; the missing historical B3 fixture and two explicit native-publication skips limit broader acceptance. The default-root interrupted run (exit `1073807364`, no final report, two unidentified failure markers) is inconclusive and is not candidate or passing-baseline evidence.

## Final acceptance-evidence follow-up

- [x] Recheck the three JUnit reports: 197 passed; 385 passed; 248 passed and two skipped. Verify 832 distinct testcase identities, no overlap, failures, or errors.
- [x] Match all 13 changed Python files byte-for-byte between candidate and package-shaped acceptance; recheck all 11 retained fixture source/destination hashes and lengths.
- [x] Retain report digests, skip reasons, code/fixture hashes and normalized root preservation evidence in `docs/project/evidence/analysis-context-ancestor-acceptance-summary-2026-11-18.json`.
- [x] Record linear checkpoint IDs and a non-destructive `jj workspace add -r <checkpoint>` recovery example. Preserve existing checkpoints and the default workspace.
- [x] Narrow preservation claims to recorded evidence: 58 dirty paths/content after CRLF-to-LF normalization, 1,201 snapshot paths, and the normalized complete patch. Original raw-byte/ignored/untracked inventory preservation is not proven.
- [x] Complete focused independent Grill-Me and Superpowers documentation/evidence review. Grill-Me PASS; Superpowers SPEC PASS / QUALITY PASS after adding the core run's `--import-mode=importlib` flag and distinguishing common OCTA reproduction setup from historical invocation. The source/checkpoint CRLF-to-LF distinction is explicit; no source changed.
- [x] Create documentation-only checkpoint `acceptance-evidence: record package-shaped verification and rollback limits`, then leave an empty child. The successful creation and final revision are verified externally after this ledger update; do not merge, push, or delete either workspace.

Ruling: use jj workspace isolation and keep the accepted candidate rather than the Superpowers Git-worktree/cleanup commands — repository jj-first and preservation rules take precedence. No integration action is authorized, and whole-suite green status is not available. The finishing skill's green-suite/integration gate is therefore not claimed as passed. The remaining operation is an evidence-only checkpoint, not integration.

Ruling: final documentation changes do not alter executable bytes — reuse the three completed candidate-code test reports, independently reparse their XML, and verify all changed source hashes rather than repeating expensive identical numerical runs. If source bytes change, this ruling no longer applies.


## Grill-Me corrections before implementation

The following rulings are binding for all tasks:

1. Resolver precedence matrix:
   - \`analysis_context=AnalysisContext\`, no \`package_planes\`: resolve exactly the scene's one \`analysis_plane\`.
   - \`analysis_context=AnalysisContext\`, explicit non-empty \`package_planes\`: resolve exactly that explicit set; never append the scene plane.
   - \`analysis_context=PackageAnalysisContext\`, no \`package_planes\`: use that frozen set.
   - \`analysis_context=PackageAnalysisContext\` plus \`package_planes\`: reject the conflicting two sources before producer, processor, storage, or cache work.
   - \`analysis_context=None\`, explicit non-empty \`package_planes\`: use that explicit set.
   - \`analysis_context=None\`, \`package_planes=None\`: allow only the existing unique complete source-query inference migration path.
   - Explicit empty, duplicate, non-\`AnalysisPlane\`, malformed, or unauthorized multi-plane sets fail before package work.

2. Runner propagation is part of the contract, not an optional follow-up. The package-level \`package_planes\` input must be accepted and forwarded through \`EvidencePackage.evaluate()\`, \`EvidencePackage.process_output()\`, \`run_port_processor()\`, free-space evaluate/run entrypoints, group-axis evaluate/run/output entrypoints, and group-distance evaluate/run/output entrypoints. The free-space request plane is an explicit package override when a scene context is also present.

3. Cache identity ruling:
   - A package that ignores \`PackageAnalysisContext\` keeps the same raw and processed bytes and identities for P0 versus P1.
   - A package that uses a plane must include plane identity and revision in its own output, contract, parameter snapshot, or explicit dependency before cache lookup; the generic cache layer must not guess usage.
   - Task 4 must exercise both cases through warm and cold paths.

4. Explicit context is a trusted selection boundary, but does not silently merge source query planes. Existing source/query compatibility checks remain package-owned for plane-dependent packages. The migration inference path still rejects missing, malformed, conflicting, or revision-mismatched source query planes when no explicit context is supplied.

5. jj preservation evidence:
   - Before workspace creation, save complete \`jj diff\` output, tracked/untracked/ignored file lists, and hashes for the existing dirty paths.
   - After workspace creation and dirty patch application, compare the complete patch and hashes and confirm the default workspace is unchanged.
   - Record base revision, workspace revision, checkpoint revisions, and restoration commands in the verification evidence.


Task 0 review evidence: docs/project/evidence/analysis-context-ancestor-plan-grill-review-2026-11-18.md
jj preflight patch SHA-256: A6D515CD4984DDD29343BAF2E26BBB37F5E327EA3D4F749DC03B71B1700DFC5D

## Owner-requested bounded cache-profile repair — 2026-11-18

This addendum follows independent mainline review of delivered candidate
`bdf2d5f12ec1cd18ce1dc42023b47c4ebdf26200`. It preserves all earlier failures,
the original 830-pass/two-skip acceptance scope, and the unmerged delivery status.
Owner alone controls jj history writes and integration. Repair work changes
physical candidate files in the existing implementation workspace; no checkpoint,
snapshot, bookmark, merge, push, or workspace operation was performed.

Scope: the legacy profile, focused request tests, the structure guide's
"Required analysis-plane call context" section, and this plan/verification
record. An unchanged native helper also needed its already-pinned LF bytes
restored; its content version was not reapproved.

- [x] Reproduce with actual `_backend_versions()` under Pixi: Shapely 2.1.2,
  Trimesh 5.1.0, NumPy 2.4.3; original-to-candidate compatibility returned `None`.
  Five changed content files and backend `field_core` had stale pins. A sixth
  content mismatch was only the unchanged `plane_settings.py` CRLF checkout.
- [x] Verify root `plane_settings.py` equals the d6 blob and pinned LF SHA256
  `e92c4e1560b7354d7887c3cf044f68c29b94568c22c8eee8a0ab235778a44d3b`, then restore
  those exact bytes in the implementation workspace without changing its pin.
- [x] Audit all consumers: the central profile validator, Blender historical-key
  reconstruction, and free-space adoption/readback. No parallel compatibility
  authority, fixture change, dependency, export, or numerical algorithm is needed.
- [x] Review the five changed wrappers/resolver against d6: they add ancestor/
  selection admission and forwarding; original numerical kernels, contracts,
  identities, serializers and processing formulas remain unchanged. This is
  compatibility for original artifacts, not a claim of unchanged admission APIs.
- [x] Add five regression nodes using real files and real `_backend_versions()`.
  Before profile repair: two expected failures and three passes. After repair:
  five passes. Unknown backend/numerical versions and one independently changed
  content-only file still miss.
- [x] Update only five reviewed `current_content_implementations` values plus
  `current_backend_versions.implementations.field_core`. Preserve both original
  maps, all numeric/executor versions, schema/profile IDs, mapping membership,
  and the complete strict validation implementation.
- [x] Run 417 focused regression nodes through Pixi, including both requested
  historical `auth_free_space` and `blender_wire` P/Q/R restart families with
  forbidden producers, byte/ref retention and index rebuild checks: 417 passed,
  zero failures/errors/skips. The new package-shaped test copy is separate from
  the frozen original acceptance checkout; 215 Python source/test files and the
  repaired profile match the candidate byte-for-byte.
- [x] Correct only the requested structure-guide section: `AnalysisContext`
  ancestor owns one required default; explicit planes replace it; per-call
  `PackageAnalysisContext` is frozen; native settings/catalog are adapter helpers;
  retain dual multi-plane permission and package-owned true dependencies.
- [x] Independent bounded Grill-Me review PASS; Superpowers SPEC PASS / QUALITY
  PASS. Both verified the exact profile delta, real file hashes, strict validator
  preservation, tests and corrected structure section. Neither substitutes for
  the root-executed 417-test gate.
- [x] Append exact commands, report hashes, reviewed implementation hashes and
  limits to the existing verification record; leave the repair unsnapshotted for
  owner verification/integration. Candidate remains on `a8c2f3fe` above `bdf2d5f1`;
  default root remains `d6ab0f9a` under read-only inspection.

No broader cache migration is authorized by this repair: the bridge remains the
profile's original-to-reviewed-candidate scope. Arbitrary intermediate d6 caches
or other numerical dependency versions do not gain no-recompute acceptance.
Owner must verify every physical source SHA after final checkout/integration,
because exact compatibility intentionally remains sensitive to line endings.

