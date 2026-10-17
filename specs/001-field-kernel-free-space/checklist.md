# 001 Field Kernel + Free-Space Planning Checklist

> Living planning record. This checklist drives the Speckit plan; it is not an implementation promise.
> Scope starts with the abstract field kernel and the first free-space read-only slice. B3 remains OPEN.

## Working rules

- Read `docs/indoor_layout_evaluation_matrix_architecture_memory.md` and `docs/software-architecture.md` before every design or code change.
- Keep physical occupancy, free-space qualification, relation evidence, and influence/decay as separate channels.
- Do not treat `self_description_competition_fixtures.json` as production geometry or psychological ground truth.
- Do not promote the frozen B3 package into the live evaluator during this planning slice.
- Preserve `unknown`, `outside`, `invalid`, and `not_available`; never coerce them to numeric zero or known free.
- Use the repository Pixi environment and the specified portable Blender only if a later visual check needs Blender.

## Status legend

`[ ]` planned · `[~]` active · `[x]` completed · `[!]` blocked or needs an owner decision · `[D]` design-only evidence

## Phase 0 — Baseline and scope gate

- [x] Read the architecture memory, software architecture map, B3 handoff documents, and field brainstorm.
- [x] Check Speckit extension hooks; `.specify/extensions.yml` has no executable hooks.
- [x] Inspect current branch and mixed/untracked work; do not reset or stage unrelated changes.
- [x] Receive the two read-only delegated audits: fixture reuse and B3/field integration boundary.
- [x] Run the existing D6 probe twice and record fixture/runner hashes, environment, output paths, and the `probe_only_not_production` label; both outputs are byte-identical and report 8/8 passes.
- [!] Constitution gate: `.specify/memory/constitution.md` is still a template placeholder. Draft project-specific principles or explicitly keep planning status as pending review; do not claim ratification.

**Checkpoint report:** baseline facts, current risks, and the exact no-promotion boundary.

## Phase 1 — Feature spec and acceptance boundary

- [x] Replace the feature-spec template with a narrow draft for `001-field-kernel-free-space`.
- [x] Define the first deliverable as field-core semantics plus a read-only B3 adapter/visualization seam.
- [x] Keep `evaluate_scene`, `room_analysis_model`, the existing B3 loader shape, and the live free-space evaluator unchanged in this slice.
- [x] Define explicit non-goals: complete occupancy geometry, clearance certification, arbitrary height bands, opening-state inference, Bayesian calibration, and production inferred-group selection.
- [x] Define acceptance scenarios for scalar/batch lookup, status preservation, provenance, deterministic replay, and channel isolation.

**Owner decision gate:** approve the first slice boundary before production implementation.

## Phase 2 — Research and design decisions

- [x] Consolidate the delegated field-abstraction research into `research.md`.
- [x] Resolve the minimum `Field` core: domain, frame, query context, units, value schema, representation, provenance, scalar lookup, and batch lookup.
- [x] Record the owner-proposed status gates for `invalid`, `unknown`, `outside`, `conditional`, and `not_available`; see `owner-decision.md`.
- [x] Select `Field` as the single public concept name while leaving the exact Python protocol shape for implementation planning; do not create parallel bases.
- [x] Record why relation fields share the core but do not require spatial interpolation.
- [x] Keep decay as an explicit operator/parameterized influence feature; occupancy and physical distance do not decay.

**Checkpoint report:** chosen contract, rejected alternatives, and unresolved questions.

## Phase 3 — Data model and contracts

- [x] Create `data-model.md` for `FieldQuery`, `FieldSample`, domain/frame metadata, status, provenance, and channel bundles.
- [x] Specify the read-only B3 adapter contract without changing `load_discrete_space_field`.
- [x] Specify a separate field visualization manifest that labels layer, coordinate, status, source ids, units, and algorithm version.
- [x] Specify the free-space bundle as an explicit consumer of physical occupancy; no substitute/fallback policy duplication.
- [x] Keep `MembershipField`/group evidence as a later relation-field instance, not a subclass hierarchy for the first implementation.

**Contract gate:** no caller or public export changes until the contract documents are internally consistent.

## Phase 4 — Fixture-driven validation plan

- [x] Re-run the existing probe as S0 and save canonical output plus artifact manifest.
- [x] S1: adapt fixture observations into explicit field records; test scalar/batch equivalence, status propagation, source ids, and canonical bytes across two runs. Delegated to independent session `01a122e1-2f9b-7372-b86e-6adfc885183a`; 8/8 passed.
- [x] S2: test channel isolation: barrier evidence does not erase geometry evidence; soft semantic disagreement does not veto; hard mutual exclusion does not alter physical occupancy; context does not invent membership. Delegated to independent session `01a122e1-42ee-7ca3-93f3-75fc755e0ff7`; 8/8 passed.
- [x] S3: test translation/rotation/id-order replay, closed-wall/opening perturbation, missing-domain propagation, and invalid-versus-missing mutation. Delegated to independent session `01a122e1-581a-7e52-b676-fa63439b2752`; 5 executable checks passed and 3 are blocked/design-only due to fixture schema limits.
- [D] `minority_mixed`: soft semantic negative with candidate retained; free-space only baseline.
- [D] `independent_minority`: local gap evidence versus cross-island gap; no label-prevalence shortcut.
- [D] `geometry_conflict`: shape mismatch is negative evidence; never claim clearance.
- [D] `space_barrier`: closed barrier is a separate space channel; opening is a declared perturbation, not current fixture truth.
- [D] `semantic_conflict`: explicit mutual exclusion is a candidate veto; proximity cannot silently override it.
- [D] `context_reference`: context changes applicability/provenance, not eligibility by itself.
- [D] `missing_channels`: missing domain/semantic channels become unavailable or unknown, never negative/zero.
- [D] `invalid_geometry`: invalid is distinct from missing and must not produce known free space.

**Stop condition:** stop design exploration after deterministic replay, status/provenance invariants, and channel isolation pass twice with no unexplained diff.

## Phase 5 — Architecture synchronization and implementation readiness

- [x] Update `docs/software-architecture.md` with the owner-proposed target design while labeling it as planned until code exists.
- [x] Update the architecture memory and brainstorm alignment note with the same planned global `Field`/capability-composition direction; both explicitly remain design records and do not define a production API.
- [x] Re-check callers, tests, fixtures, exports, and B3 compatibility boundaries through the delegated integration audit and Git scope audit before implementation.
- [x] Split implementation into reversible checkpoints: core contract, B3 adapter, standalone visualization, optional explicit bridge, later promotion only by owner decision; recorded in `git-scope.md`.
- [x] Produce a Speckit plan with branch, artifacts, gates, and validation commands.

**Final planning gate:** report what is ready to implement, what remains design-only, and what requires explicit owner approval.

## Phase 6 — US1 Field core implementation

- [x] Freeze the exact Python protocol/dataclass shape for `Field`, `FieldQuery`, and `FieldSample`; API review accepted the generic ABC and deep-immutability corrections.
- [x] Write focused tests first in `test/test_field_core.py`; delegated to independent session `01a12305-8f95-7870-8370-a683796dd217`.
- [x] Implement the minimal core in `features/field_core.py`; delegated to independent session `01a1230a-53d7-7a40-a4ec-a737bb9924ec`.
- [x] Run focused tests: `PYTHONPATH=. pixi run pytest test/test_field_core.py` passes 12 tests; owner Git scope audit completed with no staged files. US1 changes are limited to `features/field_core.py`, `test/test_field_core.py`, and synchronized architecture/contract/checklist documentation; existing mixed historical changes were untouched.

## Phase 7 — US2 B3 adapter and field-layer manifest

- [x] Write red adapter and manifest tests covering package identity, status mapping, read-only metadata, provenance, and visual-state separation.
- [x] Implement `B3AdapterView` in `features/space_field_adapter.py` without changing `load_discrete_space_field` or live evaluator paths.
- [x] Implement `build_field_layer_manifest` in `features/space_field_visualization.py`; SVG/HTML rendering remains future work.
- [x] Run the historical US2 owner verification: focused US1/US2 tests plus the unchanged loader baseline reported **71 passed**; the current US1/US2/US3 owner total is 74; no staged files.
- [x] Audit scope: US2 changes are limited to the adapter/manifest modules and synchronized documentation; `evaluate_scene`, `room_analysis_model`, default overlay, B3 loader, and historical mixed changes were untouched.

## Phase 8 — US3 deterministic fixture replay

- [x] Implement the probe-local replay script in `scripts/design/group_level/run_field_fixture_replay.py` without changing fixtures, the existing probe, or production features.
- [x] Emit deterministic replay evidence with two manifests, canonical observations sorted by fixture/candidate, fixture/probe hashes, status matrix, provenance, and `design_only=true`.
- [x] Record five supported perturbations as passed and three unsupported transitions as blocked, design-only, and `probe_only_not_production`.
- [x] Run `test/test_field_fixture_replay.py`: 3/3 passed; both manifests agree on canonical SHA `a734362f...019a04`.
- [x] Keep the replay strictly diagnostic; no production Field semantics, free-space promotion, evaluator integration, or live B3 promotion.

## Long-term Field framework demonstration — non-blocking

- [ ] Build one end-to-end example that combines the unified Field core, a
  physical occupancy/free-space instance, a relation/evidence instance, any
  explicitly declared influence/decay channel, and 2D plus 3D/section
  visualization.
- [ ] Use the demonstration to explain why each value exists, which channel
  produced it, how status/provenance are carried, and where decay is or is not
  allowed.
- [ ] Treat this as an architecture demonstration and communication artifact,
  not as an acceptance gate for `001-field-kernel-free-space`, US1, B3 adapter
  work, or live evaluator promotion.

## Phase 9 — FreeSpaceField instance design

- [x] Record the concrete instance boundary in `docs/project/free-space-field-instance-design.md`.
- [x] Keep the instance as composition over `Field`; do not add a second base class or duplicate substitute resolution.
- [x] Define explicit-domain, exact-cell, physical-occupancy semantics and the six-state status mapping.
- [x] Make the universal closed-boundary rule explicit: boundary doors define the domain edge and do not become interior occupancy records.
- [x] Keep furniture, plants, counters, and other physical sources in one role-neutral occupancy channel; furniture eligibility remains a separate concern.
- [x] Implement `features/free_space_field.py` and focused tests; precision-repair evidence is recorded and independent review found no blocker.
- [x] Do not connect the instance to `evaluate_scene`, room-model output, B3 live promotion, clearance, connectivity, or decay in this phase.

## Phase 10 — US4 implementation preparation

- [x] Record the pre-implementation Git/status/hash baseline in `delegated/free-space-field-implementation-evidence.md`.
- [x] Add `contracts/free-space-field.md` with fixed whole-height handoff, positive-area clipping, holes, invalid/unavailable, and provenance rules.
- [x] Add US4/T038-T043 to the task plan without claiming constitution approval.
- [x] Add focused red tests in `test/test_free_space_field.py`; owner review corrected section and upstream-record semantics before execution.
- [x] Implement `features/free_space_field.py` after the red test command; precision-repair evidence is recorded separately.
- [x] Run focused green tests, compile both scoped modules, and rerun the existing 74-test owner suite; final precision-repair evidence records 67 new + 74 existing = 141 passed.
- [x] Complete independent review and synchronize architecture as implemented/isolated/validated; B3/live promotion remains open and constitution remains unratified.

**Checkpoint report:** US4 is an implemented isolated exact-cell physical
occupancy field over pre-resolved plan components. Its result is
empty/occupied under a declared query, not a walkability or clearance score.

## Session/report log

| Date | Step | Result | Next decision |
|---|---|---|---|
| 2026-10-10 | Delegated audits | Two read-only audits received; no production `Field` class exists | Run S0 baseline and fill feature spec |
| 2026-10-10 | S0 baseline | Probe ran twice; 8/8 assertions passed; output SHA256 matched; scope remains `probe_only_not_production` | Review research/design gates and constitution status |
| 2026-10-10 | Speckit design draft | `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and three contracts generated; no production code changed | Resolve constitution and naming/status gates before implementation |
| 2026-10-10 | Compatibility check | Existing `test/test_discrete_space_field.py`: 50 passed; loader files were not edited by this planning step | Keep loader boundary unchanged |
| 2026-10-10 | Delegated S1–S3 | Three independent read-only sessions dispatched with exclusive evidence paths; no production edits or Git mutations authorized | Collect results, audit artifacts, then update checklist and Git scope |
| 2026-10-10 | S1–S3 evidence | S1 8/8, S2 8/8, S3 5 pass + 3 blocked/design-only; all artifacts are under `delegated/` | Keep fixture limits explicit; proceed to architecture synchronization only after owner gates |
| 2026-10-10 | Git scope audit | No staged files; feature outputs are isolated under `specs/001-field-kernel-free-space/`; existing mixed changes remain untouched | Do not stage or commit until owner approves a checkpoint |
| 2026-10-10 | Owner planning ruling | `Field` selected as the single concept; status semantics documented as staged gates; no production promotion | Sync target architecture map, then prepare implementation-only plan |
| 2026-10-10 | Architecture sync | Initial planned Field kernel diagram and status gates were added to the architecture map/memory; later US1/US2/US3 implementation updates are recorded below | Constitution review remains pending |
| 2026-10-10 | Owner review | S1–S3 accepted for design-only channel/replay validation; blocked fixture limits recorded in `delegated/owner-review.md` | Prepare implementation-only plan after constitution review; no commit yet |
| 2026-10-10 | Speckit tasks dispatch | Independent session `01a122eb-0b2a-7100-a909-30d56ccf8086` assigned to generate dependency-ordered `tasks.md`; no production edits authorized | Collect tasks, audit format, then stop at implementation gate |
| 2026-10-10 | Speckit tasks result | 37 tasks generated and format-validated: US1=8, US2=9, US3=7; MVP is US1; no staged files | Stop before implementation until constitution gate and exact Python protocol shape are reviewed |
| 2026-10-10 | US1 API review dispatch | Independent session `01a12301-9ff7-7051-9987-d102c3e3d819` assigned to review the minimal Field core shape; no production edits authorized | Collect API review before writing tests |
| 2026-10-10 | US1 API review result | Direction accepted with deep immutability, six-state gate, generic target, query retention, and ordered batch corrections; contract docs updated | Write test-first contract |
| 2026-10-10 | US1 test dispatch | Independent session `01a12305-8f95-7870-8370-a683796dd217` assigned to write only `test/test_field_core.py`; production module remains absent | Collect red test result before implementation |
| 2026-10-10 | US1 red test result | Focused test file exists; py_compile passes; pytest is red only because `features.field_core` is not implemented yet | Implement the frozen core without touching other paths |
| 2026-10-10 | US1 implementation dispatch | Independent session `01a1230a-53d7-7a40-a4ec-a737bb9924ec` assigned to write only `features/field_core.py` and run focused tests | Collect implementation result and audit Git scope |
| 2026-10-10 | US1 implementation result | `features/field_core.py` now implements the frozen immutable core; `PYTHONPATH=. pixi run pytest test/test_field_core.py` passes 12/12, including conditional scope/limitation explanation coverage | Continue with the separately scoped US2 adapter/manifest; keep `FreeSpaceFieldBundle` and live promotion open |
| 2026-10-10 | US1 scope checkpoint | Focused tests pass; exact Git scope/owner audit completed with no staged files and no touched historical mixed changes | Keep the checkpoint limited to the audited US1 files |
| 2026-10-10 | US1 owner Git scope audit | No staged files; US1 additions/edits are limited to `features/field_core.py`, `test/test_field_core.py`, and synchronized architecture/contract/checklist documentation; existing mixed historical changes were not touched | US2 and US3 are now separately verified; keep `FreeSpaceFieldBundle` and live promotion open |
| 2026-10-10 | US2 red tests | Adapter and visualization manifest contract tests were red before implementation, covering loader identity, status mapping, immutability, provenance, and visual-state separation | Implement only the two US2 feature modules |
| 2026-10-10 | US2 implementation | `B3AdapterView` and `build_field_layer_manifest` implemented; no SVG/HTML renderer or live bridge added | Run owner command with loader baseline |
| 2026-10-10 | Historical US2 owner verification | Focused US1/US2 checks plus unchanged loader baseline: **71 passed**; no staged files; loader/evaluator/room model/default overlay unchanged | At that checkpoint, constitution gate, `FreeSpaceFieldBundle`, SVG/HTML rendering, US3, and live promotion were open |
| 2026-10-10 | US3 replay implementation | Added probe-local deterministic replay with eight fixtures, canonical ordering, hashes, status matrix, five supported perturbations, and three blocked design-only cases | Run two subprocess replays and compare manifests |
| 2026-10-10 | US3 owner verification | `test/test_field_fixture_replay.py` passed 3/3; two manifests matched canonical SHA `a734362f...019a04`; no production promotion occurred | Keep constitution gate, SVG/HTML rendering, free-space bundle, and live promotion open |
| 2026-10-10 | Demonstration scope clarification | Whole-Field example demonstration is a later non-blocking architecture artifact, separate from this feature's acceptance criteria | Keep current implementation sequence focused on Field core first |
| 2026-10-10 | FreeSpaceField design checkpoint | Concrete exact-cell physical occupancy design recorded; existing resolver, plan components, and Field core are reused; no production code or evaluator bridge added | Review design, then implement the smallest focused field/test slice |
