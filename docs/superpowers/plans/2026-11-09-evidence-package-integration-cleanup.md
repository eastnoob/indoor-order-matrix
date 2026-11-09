# Evidence Package Integration Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the evidence-package structure/readback work without disturbing the main worktree, close the three reviewed contract gaps, and produce a verified candidate ready for a later mainline merge.

**Architecture:** The candidate remains based on common ancestor `8524943e` and keeps the dependency-ordered source line `a336524b`, `932f5fd0`, `9f071266` as its rollback/reference history. The existing immutable package/output contracts remain the boundary: stale external channels are audit-only, published dependencies retain compact references, and a complete package graph is validated at an explicit execution boundary. Documentation must describe the actual candidate and must not imply a registry or automatic cross-package fusion.

**Tech Stack:** Python 3.12, Pixi, dataclasses, pytest, Jujutsu (`jj`), Markdown architecture records.

**Spec:** `docs/superpowers/specs/2026-11-09-evidence-package-cross-package-readback-design.md`

## Global Constraints

- Preserve unrelated dirty changes in the main worktree and do not rewrite the existing implementation line.
- Keep `codex/evidence-package-cross-package-readback` as a rollback/reference line until the integrated candidate is independently verified.
- Preserve every existing source and derived channel; stale/unavailable external package dependencies cannot produce a non-null observation, while invalid/ambiguous evidence remains explicit under the consuming package's contract.
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
- [x] Record the candidate working-copy revision and exact post-repair file hashes: `field_core.py` `0DE6F12C538C2C4CAAA14D775D2525809B19079630E8048BC9C50683B3F0419C`; `test_evidence_package_output.py` `CB2C25BB9168D99741CFB7572658B8203D1F35163F09108158B5ED20077A2E0C`; `evidence-package-structure.md` `4CD017F51AE4E66DDF98CAA30E59B46B3668D888853B082EF299D61E812D8`; cross-package spec `695F62DF505AC4AF307388D2A3D77669D464226F42D3D3A0737E43AFBB6668E0`.

### Task 2: Reconcile the design and architecture records

**Files:**
- Modify: `docs/project/evidence/evidence-package-structure.md`
- Modify: `docs/software-architecture.md`
- Modify: `docs/project/group-evidence-design-index.md`
- Modify: `docs/superpowers/plans/2026-10-26-group-attribution-evidence-field-implementation.md`

**Interfaces:**
- Consumes: current `features/field_core.py` contracts and package/freshness records.
- Produces: documentation that distinguishes package, channel, snapshot, readback, and derivation; states that cross-package readback is a contract capability rather than automatic package fusion; and records the candidate's remaining acceptance limits.

- [x] Compare the candidate documentation with the common-ancestor records and resolve only evidence-package semantic drift.
- [x] Keep the plain-language model: a package groups independent channels; channel meanings/inputs/outputs remain distinct, while this implementation identifies the executing algorithm at package-function level; snapshot/freshness belongs to outer package records; readback is explicit; derivation appends a new channel.
- [x] State the stale rule exactly: no usable `channel` reaches computation callbacks, redacted `audit_channel` is explanation/audit only, and stale/unavailable dependencies cannot publish any non-null observation regardless of output status.
- [x] State that graph validation only runs when the caller passes the complete dependency graph; no registry or implicit global graph is introduced in this slice.
- [x] Mark this as a candidate pending verification, not as a completed mainline merge.

### Task 3: Close the reviewed runtime contract gaps with TDD

**Files:**
- Modify: `features/field_core.py`
- Modify: `test/test_evidence_package_output.py`
- Modify: `test/test_evidence_package_freshness.py` only if a direct freshness regression is needed.

**Interfaces:**
- Preserve `EvidencePackage.evaluate(source_envelopes, *, dependencies=())` and existing callback compatibility.
- Preserve `EvidencePackageResolvedDependency` fields and `EvidencePackageOutput.dependencies` as compact declarations.
- Preserve `validate_evidence_package_dependency_graph(graph) -> None`, while making normalization and execution-boundary use explicit.

- [x] Add a failing regression proving stale/unavailable derived output cannot retain a numeric observation, including when output status is `partial`.
- [x] Run the focused test and record the expected failure before changing production code.
- [x] Implement the smallest boundary fix while retaining audit metadata for explanation.
- [x] Run stale regression and existing output tests.
- [x] Retain the existing regression proving published outputs do not retain nested `source_output` objects in memory; normalization remains in the output boundary.
- [x] Retain the existing regression proving execution-boundary graph validation normalizes whitespace and rejects indirect cycles before the callback; the standalone helper remains covered.
- [x] Retain tests for duplicate external channel declarations and normalized direct self-dependencies.
- [x] Run the focused red-green suite after the repair.

### Task 4: Independent verification and scope audit

**Files:**
- No additional production files unless Task 4 finds a substantive defect.
- Evidence note: `docs/project/evidence/evidence-package-integration-cleanup-2026-11-09.md`.

**Interfaces:**
- Consumes: frozen candidate and complete package-output test surface.
- Produces: reproducible verification evidence with cwd, commands, exit codes, test counts, candidate revision, and fixture limitations.

- [x] Freeze the candidate with `jj status`, `jj diff --stat`, and hashes for `features/field_core.py` and focused tests.
- [x] Run `$env:PYTHONPATH='.'; pixi run pytest test/test_evidence_package_output.py test/test_field_core.py test/test_evidence_package_freshness.py -q` (**53 passed**).
- [x] Run `pixi run python -m compileall -q features test` (exit 0).
- [x] Run relevant free-space and potential tests; 11 potential field/preview failures are missing retained IFC replay files, and 9 free-space inspection tests skip because retained fixtures are unavailable.
- [x] Confirm the main worktree retains its pre-existing dirty state and inspect the candidate diff for accidental files.
- [x] Write the evidence note with actual results and remaining limits; do not claim a mainline merge.

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
- Task 3 implementation completed in `features/field_core.py` and `test/test_evidence_package_output.py`; focused core tests report `53 passed` and compileall exits 0. The related evidence-package/freshness/group-distance command reports `86 passed`.
- Scoped code review passed with no Critical/Important findings. Its only minor finding, unavailable typed-source redaction coverage, is now covered by a regression assertion; stale/unavailable audit metadata semantics are explicit in the spec.
- Independent verification found the candidate's focused distance/free-space/potential limits documented in `docs/project/evidence/evidence-package-integration-cleanup-2026-11-09.md`: missing retained IFC replay files, existing relative-import collection errors, and a pre-existing NetworkX `3.7` versus required `3.6.1` mismatch.
- Ruling: keep the candidate isolated and do not move the mainline bookmark in this turn; the verified core contract is reviewable, but fixture/version limits remain explicit and the owner has not authorized the irreversible mainline merge.
- After merge, the old feature bookmark can technically receive more commits; preferred practice is to close it at the merge and start a fresh `codex/...` development line from the updated mainline.
- Candidate checkpoint is tracked by `codex/evidence-package-integration-cleanup`, as a separate child of the original `9f071266` checkpoint. The original `codex/evidence-package-cross-package-readback` bookmark is restored to `9f071266`; no mainline bookmark was moved.
- 2026-11-10 Superpowers review found that the structure diagram conflated runtime `EvidencePackageOutput` fields with outer package contract/status/manifest; channel-specific algorithm/snapshot identities are logical design requirements but not typed runtime fields; the resolver's freshness is caller-supplied; graph-cycle validation is optional; persisted JSON has no generic typed decoder; and the output boundary allowed `partial` observations from stale dependencies. The structure/spec/architecture/index/memory and parent checklist now state those exact limits. A new unavailable-source `partial` regression failed before the production edit with `DID NOT RAISE`, then passed with the stale observation guard; evidence-package output, freshness and distance-package tests report 86 passed; compileall exits 0. Potential tests report 21 passed, 11 failures from missing retained IFC replay files, and 9 skips. Indirect cycle checking remains caller-enforced, not automatic. Mainline merge, a concrete package consumer, and deciding/implementing channel-specific algorithm/snapshot identity remain future checklist work.
- The same review found the cross-package spec overstated consumer output status: it required `not_available` where the shared core only gates `effective_status` and forbids a non-null observation. The spec now distinguishes typed-reader errors, stale/unavailable observation gating, and optional graph-cycle rejection; consumer status semantics remain package-owned. A second read-only review found no remaining blocking mismatch; it requested one clarification that partial/ambiguous status preservation is the consuming package's responsibility, which is now explicit. No runtime behavior changed in this correction.
