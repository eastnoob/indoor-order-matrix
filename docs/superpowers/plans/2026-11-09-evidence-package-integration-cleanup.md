# Evidence Package Integration Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the evidence-package structure/readback work without disturbing the main worktree, close the three reviewed contract gaps, and produce a verified candidate ready for a later mainline merge.

**Architecture:** The candidate remains based on common ancestor `8524943e` and keeps the dependency-ordered source line `a336524b`, `932f5fd0`, `9f071266` as its rollback/reference history. The existing immutable package/output contracts remain the boundary: stale external channels are audit-only, published dependencies retain compact references, and a complete package graph is validated at an explicit execution boundary. Documentation must describe the actual candidate and must not imply a registry or automatic cross-package fusion.

**Tech Stack:** Python 3.12, Pixi, dataclasses, pytest, Jujutsu (`jj`), Markdown architecture records.

**Spec:** `docs/superpowers/specs/2026-11-09-evidence-package-cross-package-readback-design.md`

## Global Constraints

- Preserve unrelated dirty changes in the main worktree and do not rewrite the existing implementation line.
- Keep `codex/evidence-package-cross-package-readback` as a rollback/reference line until the integrated candidate is independently verified.
- Preserve every existing source and derived channel; stale, unavailable, invalid, and ambiguous external evidence cannot become a computed numeric result.
- Do not add a registry, scheduler, universal fusion formula, or package-specific algorithm.
- Use English docstrings/comments for modified project-owned code and keep comments limited to non-obvious boundary rules.
- No visual is required: identity, freshness, serialization, dependency validation, and documentation are answered by tests and byte-level inspection.

---

### Task 1: Freeze the integration boundary

**Files:**
- Modify: `docs/superpowers/plans/2026-11-09-evidence-package-integration-cleanup.md`
- Inspect only: `docs/indoor_layout_evaluation_matrix_architecture_memory.md`, `docs/software-architecture.md`

**Interfaces:**
- Base: common ancestor `8524943e`.
- Source commits: `a336524b`, `932f5fd0`, `9f071266` in that order.
- Main worktree: `D:/PROJECTS/understandOtherPackage/order_analyzer`, preserved unchanged.
- Candidate workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/evidence-package-structure-e86`.

- [x] Verify installed `jj` commands and record that the candidate line already has the source commits in dependency order.
- [x] Record the main worktree dirty state and the existing `codex/free-space-evidence-package` bookmark conflict without resolving it.
- [ ] Record the candidate working-copy commit and exact file hashes before code changes.

### Task 2: Reconcile the design and architecture records

**Files:**
- Modify: `docs/project/evidence/evidence-package-structure.md`
- Modify: `docs/software-architecture.md`
- Modify: `docs/project/group-evidence-design-index.md`
- Modify: `docs/superpowers/plans/2026-10-26-group-attribution-evidence-field-implementation.md`

**Interfaces:**
- Consumes: current `features/field_core.py` contracts and package/freshness records.
- Produces: documentation that distinguishes package, channel, snapshot, readback, and derivation; states that cross-package readback is a contract capability rather than automatic package fusion; and records the candidate's remaining acceptance limits.

- [ ] Compare the candidate documentation with the common-ancestor records and resolve only evidence-package semantic drift.
- [ ] Keep the plain-language model: a package groups independent channels; each channel owns its calculation; snapshot/freshness belongs to package materialization; readback is an explicit access operation; derivation appends a new channel.
- [ ] State the stale rule exactly: `channel` is absent to computation callbacks, `audit_channel` is retained only for explanation/audit, and stale/unavailable dependencies cannot publish a `computed` numeric output.
- [ ] State that graph validation requires the caller's complete dependency graph; no registry or implicit global graph is introduced in this slice.
- [ ] Mark this as a candidate pending verification, not as a completed mainline merge.

### Task 3: Close the reviewed runtime contract gaps with TDD

**Files:**
- Modify: `features/field_core.py`
- Modify: `test/test_evidence_package_output.py`
- Modify: `test/test_evidence_package_freshness.py` only if a direct freshness regression is needed.

**Interfaces:**
- Preserve `EvidencePackage.evaluate(source_envelopes, *, dependencies=())` and existing callback compatibility.
- Preserve `EvidencePackageResolvedDependency` fields and `EvidencePackageOutput.dependencies` as compact declarations.
- Preserve `validate_evidence_package_dependency_graph(graph) -> None`, while making normalization and execution-boundary use explicit.

- [ ] Add a failing regression proving a stale callback cannot treat `audit_channel.observation` as a usable current numeric input; either no usable channel is exposed or a computed result is rejected.
- [ ] Run the focused test and record the expected failure before changing production code.
- [ ] Implement the smallest boundary fix while retaining audit metadata for explanation.
- [ ] Run the stale regression and existing output tests.
- [ ] Add a failing regression proving a published output does not retain nested `source_output` objects in memory, then normalize dependencies before storing them.
- [ ] Add a failing regression proving execution-boundary graph validation normalizes whitespace and rejects self/indirect cycles; retain the standalone helper.
- [ ] Retain tests for duplicate external channel declarations and normalized direct self-dependencies.
- [ ] Run the focused red-green suite after each repair.

### Task 4: Independent verification and scope audit

**Files:**
- No additional production files unless Task 4 finds a substantive defect.
- Evidence note: `docs/project/evidence/evidence-package-integration-cleanup-2026-11-09.md`.

**Interfaces:**
- Consumes: frozen candidate and complete package-output test surface.
- Produces: reproducible verification evidence with cwd, commands, exit codes, test counts, candidate revision, and fixture limitations.

- [ ] Freeze the candidate with `jj status`, `jj diff --stat`, and hashes for `features/field_core.py` and focused tests.
- [ ] Run `pixi run pytest test/test_evidence_package_output.py test/test_evidence_package_freshness.py test/test_group_distance_evidence_package.py -q`.
- [ ] Run `pixi run python -m compileall -q features test`.
- [ ] Run relevant free-space and potential tests when fixtures are present; record exact collection limitations if they remain.
- [ ] Confirm the main worktree is untouched and inspect the diff for accidental files.
- [ ] Write the evidence note with actual results and remaining limits; do not claim a mainline merge.

### Task 5: Decide and record integration disposition

**Files:**
- Modify: `docs/superpowers/plans/2026-11-09-evidence-package-integration-cleanup.md`
- Modify: the existing project checklist/ledger only for the actual candidate status.

**Interfaces:**
- Input: verified candidate from Task 4.
- Output: either a verified integration bookmark or an isolated candidate with a recorded blocker.

- [ ] If all required checks pass, move a candidate bookmark to the verified change and record its exact change/commit ID.
- [ ] Keep the mainline bookmark separate until the owner authorizes the merge; merge only this verified line later.
- [ ] If a required check remains blocked, leave the candidate isolated and do not move a mainline bookmark.
- [ ] Record the continuation rule: a merged feature branch can technically receive more commits, but the preferred workflow is to close it at merge and create a new `codex/...` branch from updated mainline.

## Execution Log

- Candidate workspace is the existing source line based on `8524943e`; a separate rebase attempt was abandoned after jj surfaced unrelated global divergent workspace state.
- Main worktree dirty changes and `codex/free-space-evidence-package` bookmark conflict are preserved and out of scope.
- Source implementation line remains available as rollback/reference history until Task 5.
- Task 3 implementation completed in `features/field_core.py` and `test/test_evidence_package_output.py`; focused core tests report `52 passed` and compileall exits 0.
- Scoped code review passed with no Critical/Important findings. Its only minor finding, unavailable typed-source redaction coverage, is now covered by a regression assertion; stale/unavailable audit metadata semantics are explicit in the spec.
- Independent verification found the candidate's focused distance/free-space/potential limits documented in `docs/project/evidence/evidence-package-integration-cleanup-2026-11-09.md`: missing retained IFC replay files, existing relative-import collection errors, and a pre-existing NetworkX `3.7` versus required `3.6.1` mismatch.
- Ruling: keep the candidate isolated and do not move the mainline bookmark in this turn; the verified core contract is reviewable, but fixture/version limits remain explicit and the owner has not authorized the irreversible mainline merge.
- After merge, the old feature bookmark can technically receive more commits; preferred practice is to close it at the merge and start a fresh `codex/...` development line from the updated mainline.
- Candidate checkpoint is tracked by `codex/evidence-package-integration-cleanup`, as a separate child of the original `9f071266` checkpoint. The original `codex/evidence-package-cross-package-readback` bookmark is restored to `9f071266`; no mainline bookmark was moved.
