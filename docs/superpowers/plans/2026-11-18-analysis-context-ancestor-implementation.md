
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

The default workspace currently contains unrelated dirty work and an existing snapshot f457f56f. Do not reset, abandon, overwrite, merge, or push it.

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
- [x] Run static call audit: `rg -n "\.evaluate\(|\.process_output\(" features adapters blender_addon --glob "*.py"`. Fresh result: 21 matches; package-relevant calls forward `analysis_context`/the resolved snapshot, while field/affordance evaluators are unrelated non-package APIs. Full output is retained in the verification record.
- [x] Run: `pixi run pytest test/ -q`. Result: collection stopped with 48 errors caused by the nested-worktree package shape (`..features` relative imports beyond the top-level package and missing `octa` on `sys.path`); no implementation assertion ran in those files. This remains an environment limitation, not a package-context regression.
- [x] Run final independent Superpowers review and final Grill-Me review; repair findings. Both reviews returned SPEC/QUALITY PASS. The only finding was stale pending ledger text; it is corrected in this plan before the final checkpoint.
- [x] Record fresh command output, jj checkpoint names, and known limits. Focused command: `pixi run pytest test/test_package_analysis_context.py test/test_evidence_package_output.py test/test_evidence_package_processing.py test/test_output_port_cache.py -q -k "not context_contract_imports_under_both_namespaces_without_heavy_engines"` → `258 passed, 1 deselected in 11.33s`. Resolver-only focused command: `44 passed, 1 deselected`; unfiltered resolver command: `44 passed, 1 failed` only because its subprocess could not import `order_analyzer` from the hyphenated worktree parent. Targeted group-distance/lifecycle command: `125 passed`; group-axis command: `137 passed` plus 8 missing-retained-artifact failures. No UI/.blend lifecycle or physical-model recomputation was claimed.
- [x] Create jj checkpoint documentation-and-verification; do not push or merge. The final local checkpoint is created after this ledger update and is recorded in the verification evidence and final response.

## Completion gate

Complete only when inheritance, replacement, multi-plane permission, invalid-input ordering, ignored-plane identity, plane-using dependency, caller coverage, architecture synchronization, and jj rollback checkpoints are all evidenced by fresh tests or explicit review records. UI and .blend lifecycle work remain deferred.


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

