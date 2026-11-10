# Evidence Package Integration Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the existing evidence-package rollout through saved-output parsing, faithful cross-package consumption, retained IFC replay and synchronized docs, without disturbing the main worktree or merging/pushing the candidate.

**Architecture:** The candidate keeps common ancestor `8524943e` and dependency-ordered reference line `a336524b`, `932f5fd0`, `9f071266`. Existing immutable types own fixed-v1 parsing, computation identity and serialized content integrity; an explicit complete graph checks declaration consistency before execution. A distinct readback package faithfully republishes selected existing channels using pinned files and freshly compared contracts. Channel traceability reuses provenance/function/version, lineage and cache fingerprints; no formula, registry or automatic fusion is added.

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

- [x] Core candidate bookmark `codex/evidence-package-integration-cleanup` records change `vlktzmkurykvryupqwprprvwqwsrnqzp`, commit `51b8c6e789d4bece0a7c4ae65fea5210e77b8ed0`; this checkpoint covers the shared core subset, not the full rollout below.
- [x] Keep the mainline bookmark separate until the owner authorizes the merge; no merge or push is authorized for this rollout.
- [x] Leave the candidate isolated while the full saved-snapshot and existing-package acceptance work proceeds.
- [x] Record the continuation rule: a merged feature branch can technically receive more commits, but the preferred workflow is to close it at merge and create a new `codex/...` branch from updated mainline.

### Task 6: Fixed-schema saved snapshot readback and traceability

**Files:** `features/field_core.py`, `test/test_evidence_package_output.py`,
`scripts/design/group_level/run_group_axis_potential_ifc_replay.py`.

**Interfaces:** Add `deserialize_field_result_envelope(payload)` and
`deserialize_evidence_package_output(payload)` for the two existing v1 schemas.
The existing replay `_load_envelope()` delegates to the shared parser. Reuse
existing dataclass validation and accept JSON values only; do not load class
names or arbitrary Python objects. Preserve channel observations, status,
support, source IDs, provenance and both reference types.

- [x] Add failing tests for JSON roundtrip, saved-value/status tampering,
  unsupported schema/fields, old publications without dependencies or content
  fingerprints, and multiple targets using the same external channel name.
- [x] Serialize `payload_fingerprint` as SHA-256 of canonical complete output
  excluding that field. Validate it when present. It measures content integrity;
  `output_identity` measures computation identity; neither proves currentness.
- [x] Restore historical no-dependency identity by omitting the dependency key
  from the identity payload when empty. Preserve historical published IDs; the
  unshipped intermediate core candidate is not a new publication format.
- [x] Parse the fixed schemas and reject changed identity/unknown contract
  fields instead of silently losing saved evidence. Legacy files without the
  added fingerprint remain readable; execution must pin their artifact bytes
  and compare current contracts rather than trust a saved freshness receipt.
- [x] Fix dependency uniqueness to use `(target_identity, channel)`.
- [x] When a dependency graph is explicitly supplied, require closed node
  coverage and consistency with current/available upstream declarations before
  running the callback. Keep the no-graph legacy API compatible and document
  that this path has no complete-graph guarantee.
- [x] Run focused readback/output/freshness/core tests and record red/green.

### Task 7: Existing package consumption and retained IFC replay

**Files:** Existing free-space, group-distance, potential producers and their
callers/tests as required by concrete consumption; one output-only replay entry
under `scripts/design/group_level/` if no existing entry owns this operation.

- [x] Read back the actual saved free-space, distance and potential packages;
  read geometry/trend envelopes with the same fixed envelope parser. Treat
  geometry/trend as source adapters, preserving their public/audit boundary.
- [x] Demonstrate another package consuming existing published channels with
  explicit dependencies, current contract comparison, exact scope/plane binding,
  and a complete dependency graph checked before execution. Use existing
  computations or faithful existing-channel readback, never a new fusion score.
  Actually consume two different target identities of the same `path_distance`
  channel using full package/output/target/channel addresses; test mismatch
  refusal and freshness gating rather than merely documenting capability.
- [x] Bind the saved output to independently supplied current source envelopes
  via `current_source_envelopes` before numeric readback. Compare the signature
  of `target`, `query`, `channel_set`, `cache_identity`, `raw_status`, `value`,
  `support`, `source_ids`, including readings/channel records. Outer audit
  provenance such as `source_freshness` and visualization is excluded.
  Missing current source context is unavailable;
  input/query/plane mismatch is rejected. Prove that a contract from snapshot B
  cannot enable output A even with equal package IDs, and that audit-only
  historical/current provenance labels do not alter actual input binding.
- [x] Cover fresh, stale, unavailable and partial states; unused optional
  dependencies must not suppress independent pure-axis outputs.
- [x] Reuse retained artifacts from the four named workspaces. Pin file hashes,
  source identity, query and plane. The camera-plane free-space/distance chain
  must not be conflated with world-plane potential/trend/geometry.
- [x] Run affected Pixi tests and the real saved-artifact replay, retaining a
  compact report with actual paths/hashes/counts and reused visualization refs.
  Preserve the initial potential source-order `AssertionError` and corrected
  replay: use original `envelopes.json` SHA
  `de0434b947e562b0ed9f486fe134da118e5d25b81199582dc9374903336534c0`
  order to reproduce all 4,112 outputs; roundtrip separately preserves all
  outputs/37 sources. Do not change formulas/versions for an audit-list order.

### Task 8: Synchronize the rollout record and checkpoint

**Files:** Existing structure note, cross-package spec, output/minimal standards,
architecture/memory, evidence index, parent checklist and this plan/evidence note.

- [x] Map each channel's algorithm/recipe, actual input lineage, computation
  identity and payload fingerprint to existing fields; add no parallel class tree.
- [x] Replace superseded typed-only/future-consumer claims with exact implemented
  behavior. Keep historical failures as history and record their resolution.
- [x] Review the changed implementation against the scope and run necessary
  checks, reusing unchanged evidence instead of repeating broad reviews.
- [x] Create a task-owned local JJ checkpoint, advance the candidate bookmark,
  and report exact IDs and remaining limits to the owner. Preserve `master`,
  the original reference bookmark, unrelated dirty work and bookmark conflicts.

## Rollout rulings — 2026-11-10

- Fixed-schema parsing is required by the authorized saved-snapshot use case;
  it is not an arbitrary-object serialization framework.
- A content fingerprint complements existing computation identities because
  output identity deliberately excludes observation/status bytes.
- Historical receipts do not establish current freshness. Retained replay may
  establish freshness only against its explicitly pinned retained scope.
- Worker edits are serialized at shared interfaces; root alone writes JJ
  history. Read-only reconnaissance runs in parallel. No mainline merge/push.
- The full payload fingerprint is serialized metadata, not a new typed output
  field. It binds values/status/provenance and retained recipe/input content;
  computation-identity equality alone is not value-integrity evidence.
- Complete shared readback and per-package replay do not implement
  distance-to-potential business integration. The retained plane/query mismatch
  must remain explicit; inventing a fusion formula is outside this rollout.
- A current contract must bind to the saved output's actual source snapshot;
  package-ID equality alone is insufficient. Independently current source
  identities/readings gate numeric use; audit freshness labels are not inputs.

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
- Historical pre-rollout review on 2026-11-10 found that the structure diagram conflated runtime `EvidencePackageOutput` fields with outer package contract/status/manifest; channel-specific algorithm/snapshot identities are logical design requirements but not typed runtime fields; the resolver's freshness is caller-supplied; graph-cycle validation is optional; persisted JSON has no generic typed decoder; and the output boundary allowed `partial` observations from stale dependencies. The structure/spec/architecture/index/memory and parent checklist now state those exact limits. A new unavailable-source `partial` regression failed before the production edit with `DID NOT RAISE`, then passed with the stale observation guard; evidence-package output, freshness and distance-package tests report 86 passed; compileall exits 0. Potential tests report 21 passed, 11 failures from missing retained IFC replay files, and 9 skips. Indirect cycle checking remains caller-enforced, not automatic. Mainline merge, a concrete package consumer, and deciding/implementing channel-specific algorithm/snapshot identity remain future checklist work.
- The same review found the cross-package spec overstated consumer output status: it required `not_available` where the shared core only gates `effective_status` and forbids a non-null observation. The spec now distinguishes typed-reader errors, stale/unavailable observation gating, and optional graph-cycle rejection; consumer status semantics remain package-owned. A second read-only review found no remaining blocking mismatch; it requested one clarification that partial/ambiguous status preservation is the consuming package's responsibility, which is now explicit. No runtime behavior changed in this correction.
- 2026-11-10 rollout continuation supersedes the earlier typed-only decoder and channel-identity follow-up limits: fixed-v1 readers, serialized content fingerprints, faithful readback and independent source-context binding are implemented. The retained report is error-free, the scoped P1 review is approved, and the affected candidate checks pass. The local JJ checkpoint is created on this candidate; old missing-fixture and dependency-version failures remain dated history. No new plan, mainline merge or push.
