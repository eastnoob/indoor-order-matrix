---
description: "Dependency-ordered implementation tasks for the Field kernel and free-space read-only slice"
---

# Tasks: Field Kernel and Free-Space Read-Only Slice

**Input**: Design documents from `specs/001-field-kernel-free-space/`

**Scope**: US1 Field core, US2 read-only B3 adapter/manifest, and US3 deterministic diagnostic replay are implemented. Remaining work excludes live evaluator promotion, complete occupancy/clearance/connectivity certification, Bayesian calibration, SVG/HTML rendering, and changes to the existing B3 loader.

**Constitution gate**: `.specify/memory/constitution.md` is still the generated placeholder. This plan remains pending owner review or explicit waiver; no task may claim constitution compliance or modify the constitution in this slice.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Freeze scope and establish reproducible implementation inputs without changing production code.

- [ ] T001 Inspect `AGENTS.md`, `docs/indoor_layout_evaluation_matrix_architecture_memory.md`, `docs/software-architecture.md`, `specs/001-field-kernel-free-space/plan.md`, and `specs/001-field-kernel-free-space/git-scope.md`; record the implementation boundary in the work log without editing those files
- [ ] T002 Verify `.specify/memory/constitution.md` remains an unratified placeholder and block implementation checkpoints until the owner reviews it or explicitly waives the gate
- [ ] T003 [P] Re-run the baseline probe from `specs/001-field-kernel-free-space/quickstart.md` twice and compare normalized outputs against `specs/001-field-kernel-free-space/s0-probe-evidence.json` and `specs/001-field-kernel-free-space/s0-probe-evidence-2.json`; keep `formula_scope: probe_only_not_production`
- [ ] T004 [P] Audit `git status --short`, `git diff --name-only`, and `git diff --cached --name-only` before implementation and confirm that only explicitly approved paths can enter a future checkpoint

**Checkpoint**: Baseline evidence is reproducible, the constitution gate is visibly pending, and no production or Git-index change is made by this planning slice.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared test and compatibility constraints before story implementation.

- [ ] T005 Define the implementation file/test ownership map in `specs/001-field-kernel-free-space/tasks-summary.md`, covering `features/field_core.py`, `features/space_field_adapter.py`, `features/space_field_visualization.py`, `test/test_field_core.py`, `test/test_space_field_adapter.py`, `test/test_space_field_visualization.py`, and fixture-validation artifacts
- [ ] T006 [P] Add a focused test helper fixture for explicit domains, 2D/3D frames, section queries, and all six statuses in `test/test_field_core.py` without importing `scripts.design` from production features
- [ ] T007 [P] Add a frozen accepted-package fixture loader seam in `test/test_space_field_adapter.py` using the existing `features.discrete_space_field.load_discrete_space_field` return value; do not alter `features/discrete_space_field.py`
- [ ] T008 Verify the existing checkpoint rule in `specs/001-field-kernel-free-space/git-scope.md`: stage explicit paths only, inspect staged scope, and stop if the constitution gate is unresolved

**Checkpoint**: Shared fixtures and path ownership are ready; no story may change `evaluate_scene`, `room_analysis_model`, the existing B3 loader, or default evaluator overlays.

## Phase 3: User Story 1 - Read and audit a field sample (Priority: P1) - MVP

**Goal**: Provide one small Field contract with exact and batch lookup, explicit status gates, and auditable provenance.

**Independent Test**: `pixi run pytest test/test_field_core.py -q` proves scalar/batch canonical equivalence and preserves `invalid`, `not_available`, `outside`, `unknown`, `conditional`, and `established` without converting missing evidence to zero/free.

### Tests for User Story 1

- [x] T009 [P] [US1] Write contract tests for `FieldQuery` and `FieldSample` validation, required provenance fields, and status semantics in `test/test_field_core.py`
- [x] T010 [P] [US1] Write exact-versus-batch canonical equivalence tests, including relation-native targets that do not support interpolation, in `test/test_field_core.py`
- [x] T011 [P] [US1] Write negative tests for missing domain/channel, outside-domain targets, malformed queries, and unknown evidence in `test/test_field_core.py`

### Implementation for User Story 1

- [x] T012 [US1] Implement immutable `FieldQuery`, `FieldSample`, and `Field` contract records/protocol in `features/field_core.py` with `domain`, `frame`, `query_context`, `value_schema`, `representation`, and `provenance`
- [x] T013 [US1] Implement `Field.evaluate(target, query)` and `Field.evaluate_many(targets, query)` in `features/field_core.py`, preserving exact lookup semantics and canonical batch ordering without dense 3D allocation
- [x] T014 [US1] Implement status/provenance validation in `features/field_core.py` so `not_available` requires absent domain/channel, `outside` requires a valid available domain, `unknown` preserves insufficient evidence, and `conditional` remains scope-limited
- [x] T015 [US1] Add focused docstrings and why-comments for status gates, canonicalization, and provenance handoff in `features/field_core.py`, then run `pixi run pytest test/test_field_core.py -q`
- [x] T016 [US1] Create the first future implementation checkpoint for explicit paths `features/field_core.py` and `test/test_field_core.py`; do not stage or commit while T002 is unresolved

**Checkpoint**: US1 is independently usable as an auditable Field contract and is the MVP; it does not imply free-space, B3 promotion, or evaluator integration.

## Phase 4: User Story 2 - Adapt the frozen B3 package without promotion (Priority: P2)

**Goal**: Expose a read-only B3 adapter and standalone visualization manifest while preserving the loader boundary and conditional/open limitations.

**Independent Test**: `pixi run pytest test/test_space_field_adapter.py test/test_space_field_visualization.py -q` proves package identity, hashes, statuses, source sections, and limitations survive adaptation and visualization.

### Tests for User Story 2

- [x] T017 [P] [US2] Write adapter contract tests for schema, selected variant, artifact manifest, hashes, source sections, counts, analysis plane, units, and null/open completeness fields in `test/test_space_field_adapter.py`
- [x] T018 [P] [US2] Write adapter rejection tests proving the read-only seam does not infer geometry, interpolation, clearance, connectivity, whole-height walkability, or live-source discovery in `test/test_space_field_adapter.py`
- [x] T019 [P] [US2] Write visualization-manifest tests for layer id, semantic channel, coordinates, frame/plane/height band, value/status, source ids, provenance, units, and algorithm/schema versions in `test/test_space_field_visualization.py`
- [x] T020 [P] [US2] Write visual-state tests proving `unknown`, `invalid`, `outside`, and `conditional` are distinct from empty/free in `test/test_space_field_visualization.py`

### Implementation for User Story 2

- [x] T021 [US2] Implement `B3AdapterView` and read-only sample mapping in `features/space_field_adapter.py` over the validated dictionary returned by `features.discrete_space_field.load_discrete_space_field` without changing that loader
- [x] T022 [US2] Preserve B3 package identity, source ids, hashes, status counts, analysis plane, units, provenance, and conditional/open completeness fields in `features/space_field_adapter.py`
- [x] T023 [US2] Implement the standalone field-layer manifest in `features/space_field_visualization.py`; require explicit field/adapter input and leave `scene_metric_overlay_svg(scene, matrix)` unchanged. SVG/HTML rendering remains future work.
- [x] T024 [US2] Add explicit limitation metadata in `features/space_field_adapter.py` and `features/space_field_visualization.py` for B3 `z=1.6 m` conditional observations versus whole-height truth
- [x] T025 [US2] Run the focused adapter and visualization tests, audit English-first docstrings/comments, and record the future checkpoint for explicit paths `features/space_field_adapter.py`, `features/space_field_visualization.py`, `test/test_space_field_adapter.py`, and `test/test_space_field_visualization.py`; no staging or commit performed

**Checkpoint**: US2 is an independently inspectable, read-only seam. `features/discrete_space_field.py`, `features/scene_evaluator.py`, `features/room_analysis_model.py`, and default evaluator visualization remain unchanged.

## Phase 5: User Story 3 - Validate evidence-channel isolation (Priority: P3)

**Goal**: Replay all eight design-only fixtures twice and prove deterministic, channel-local perturbation behavior with honest missing/invalid/open states.

**Independent Test**: A focused replay command produces byte-equivalent canonical observations and all declared S1-S3 assertions pass without promoting probe formulas to production semantics.

### Tests for User Story 3

- [x] T026 [P] [US3] Add deterministic replay assertions for all eight fixtures, canonical observations, statuses, provenance, and output hashes in `test/test_field_fixture_replay.py`
- [x] T027 [P] [US3] Add channel-isolation assertions for geometry, space/barrier, semantic, and context changes in `test/test_field_fixture_replay.py`
- [x] T028 [P] [US3] Add perturbation assertions for identifier/order changes, translation, supported rotation, opening mutation, missing domain, invalid geometry, and section-versus-whole-height limits in `test/test_field_fixture_replay.py`

### Implementation for User Story 3

- [x] T029 [US3] Implement deterministic fixture replay and canonicalization in `scripts/design/group_level/run_field_fixture_replay.py`, consuming `scripts/design/group_level/self_description_competition_fixtures.json` and labeling every formula `probe_only_not_production`
- [x] T030 [US3] Write replay manifests, assertion matrices, perturbation diffs, and artifact hashes under `specs/001-field-kernel-free-space/delegated/` without changing production features, fixtures, or existing probe outputs
- [x] T031 [US3] Compare deferred S3 cases and explicit limitations with `specs/001-field-kernel-free-space/delegated/owner-review.md`; retain the accepted ruling unless a separate owner-approved evidence update is requested
- [x] T032 [US3] Run the focused fixture replay tests twice, compare normalized outputs, and create a future checkpoint for explicit paths `scripts/design/group_level/run_field_fixture_replay.py` and `test/test_field_fixture_replay.py`; no staging or commit performed

**Checkpoint**: US3 proves design-only channel isolation and replay invariants; it does not authorize candidate selection, probability calibration, free-space scoring, or evaluator promotion.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the complete planned slice and preserve architecture boundaries.

- [x] T033 [P] Run the focused US1/US2/US3 suite (plus the unchanged loader baseline) and record the owner result in `specs/001-field-kernel-free-space/tasks-summary.md` (**74 passed**; the loader-inclusive command is the reproducibility check)
- [x] T034 [P] Audit changed implementation files for English-first docstrings and intent comments covering status gates, provenance, geometry/section conversion, serialization, and adapter handoff
- [x] T035 Confirm with `rg` that no planned task modifies `features/discrete_space_field.py`, `features/scene_evaluator.py`, `features/room_analysis_model.py`, default evaluator overlays, or any Bayesian/calibration implementation
- [x] T036 Run the quickstart validation from `specs/001-field-kernel-free-space/quickstart.md`, preserve explicit `not_available`/`unknown`/`conditional` outcomes, and stop with the constitution gate still pending
- [x] T037 Prepare a final future checkpoint review using `git status --short`, `git diff --name-only`, and `git diff --cached --name-only`; no commit, push, merge, or Git-index mutation is authorized by this planning workflow

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No implementation dependency; establishes evidence and gates.
- **Foundational (Phase 2)**: Depends on Setup and blocks story implementation.
- **User Story 1 (Phase 3)**: Depends on Foundational; MVP and prerequisite for the typed adapter seam.
- **User Story 2 (Phase 4)**: Depends on US1 for the Field sample contract; it is otherwise isolated from live evaluator code.
- **User Story 3 (Phase 5)**: Depends on US1 for canonical field semantics; it may run in parallel with US2 after US1.
- **Polish (Phase 6)**: Depends on the desired stories and their focused tests.

### User Story Dependencies

- **US1 (P1)**: Foundational only; no other story dependency.
- **US2 (P2)**: Foundational + US1; consumes the Field contract and existing loader output.
- **US3 (P3)**: Foundational + US1; can proceed in parallel with US2 and does not promote results.

### Parallel Opportunities

- T003-T004 can run in parallel after scope inspection.
- T006-T007 can run in parallel during Foundational.
- T009-T011 can run in parallel before US1 implementation.
- T017-T020 can run in parallel before US2 implementation.
- T026-T028 can run in parallel before US3 implementation.
- After US1, US2 and US3 can be staffed in parallel because they touch different implementation/test files.

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational gates.
2. Implement and test US1 only.
3. Stop at the US1 checkpoint for owner review of the constitution gate and exact Python symbol shape.

### Incremental Delivery

1. Add US2 read-only B3 adapter and standalone visualization.
2. Add US3 deterministic fixture replay and channel-isolation validation.
3. Run Polish checks and preserve all explicit limitations.
4. Treat live evaluator promotion, complete clearance, Bayesian calibration, and loader changes as separate future decisions outside this feature.

## Format and Safety Notes

- Every executable task uses `- [ ] Txxx`, with `[P]` only for parallelizable tasks and `[USx]` only inside a user-story phase.
- Every implementation task names an exact file path.
- Future checkpoints stage explicit paths only and remain blocked by the unresolved constitution gate.

## Phase 7: User Story 4 - Exact-cell physical occupancy field (Priority: P2)

**Goal**: Implement one concrete `Field` instance over explicit domain cells
and already-resolved whole-height occupancy records. Keep it outside the
evaluator and source-resolution layers.

- [x] T038 [US4] Record the implementation baseline and scope in `delegated/free-space-field-implementation-evidence.md`.
- [x] T039 [US4] Add red contract tests in `test/test_free_space_field.py` for exact domain clipping/holes, finite lattice validation, invalid versus unavailable, unresolved/accepted/original propagation, fixed query context, immutable provenance, and ordered batches.
- [x] T040 [US4] Implement `features/free_space_field.py` using existing `Field` core and pre-resolved geometry components; precision repair is recorded separately and the implementation does not rescan sources or call the resolver.
- [x] T041 [US4] Record focused tests and compilation for the two scoped modules; final precision-repair evidence is 67 focused and 141 combined, with the compile check recorded separately.
- [x] T042 [US4] Run the existing owner-approved 74-test suite without changing its scope; final precision-repair evidence reports 67 new plus 74 existing = 141 passed.
- [x] T043 [US4] Complete the independent precision review and synchronize architecture as an implemented isolated slice; B3/live promotion remains open and constitution remains unratified.
