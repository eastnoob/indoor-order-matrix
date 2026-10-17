---
description: "Implementation tasks for offline FreeSpaceField inspection"
---

# Tasks: Free-Space Field Inspection

**Input**: Design documents from `/specs/002-free-space-field-inspection/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/inspection-manifest.md`, and read-only
`delegated/locked-input-seam-review.md`

**Tests**: Focused tests are required by the feature acceptance criteria; live
Blender/IFC tests are explicitly out of scope.

## Phase 1: Setup

- [X] T001 Create the runner entry point at `scripts/design/space_field/run_free_space_field_inspection.py` without importing a side-effectful runner
- [X] T002 [P] Create focused test scaffold at `test/test_free_space_field_inspection.py`
- [X] T003 [P] Add the inspection schema and status legend constants in `specs/002-free-space-field-inspection/contracts/inspection-manifest.md`

## Phase 2: Foundational

- [X] T004 Implement authenticated package and mesh reference loading in `scripts/design/space_field/run_free_space_field_inspection.py` using `artifact_manifest.json` byte counts and SHA-256 values
- [X] T005 Implement runner-local whole-height transport facts from `transport_audit.json`, bindings, and capture records with explicit `world_xy`, metre units, `[0.0, 0.0]` offset, exact domain geometry including two holes, and no historical section records in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T006 Preserve the exact five unresolved ids before shared-view promotion by emitting canonical `missing_geometry` uncertainty, retaining capture references/arrays only as audit provenance, and omitting qualified `geometry_refs` for those sources in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T007 Route the qualified handoff through `analysis_scene_view(neutral_scene)` and refuse direct-preview resolver logic in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T008 [P] Add foundational refusal and source-coverage tests for hash mismatch, missing domain, exact boundary membership, non-furniture physical sources, and duplicate proxy owners in `test/test_free_space_field_inspection.py`

## Phase 3: User Story 1 - Locked geometry and field side-by-side (Priority: P1)

**Goal**: Produce an offline HTML/SVG artifact with aligned source and field
layers.

**Independent Test**: Open the generated HTML from disk and compare domain,
holes, physical sources, proxies, unresolved supports, and lattice extents.

- [X] T009 [US1] Build the explicit whole-height `FreeSpaceField` from normalized domain and occupancy records in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T010 [US1] Evaluate the declared `0.25 m` lattice and call `build_field_layer_manifest` in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T011 [US1] Render inline SVG source and field layers with aligned frame, datum, offset, holes, furniture, physical-context sources, proxies, and uncertainty in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T012 [US1] Write a self-contained HTML shell with no external assets and an explicit demonstration-resolution/semantic-limits panel in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T013 [P] [US1] Add artifact-opening, deterministic-order, and source/field alignment tests in `test/test_free_space_field_inspection.py`

## Phase 4: User Story 2 - Cell evidence and status audit (Priority: P1)

**Goal**: Preserve exact cell semantics and make all six statuses visibly
distinct.

**Independent Test**: Recover each displayed cell and compare value, status,
source ids, query metadata, support, explanation, and provenance with the
current `FreeSpaceField.evaluate` result.

- [X] T014 [US2] Preserve all six `FieldStatus` states and non-empty explanations in the inspection payload in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T015 [US2] Add shared provenance-table serialization with deterministic per-cell references and exact manifest-record recovery in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T016 [US2] Add a cell-detail view that distinguishes `conditional`, `unknown`, `outside`, `invalid`, `not_available`, and established states in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T017 [P] [US2] Add scalar/manifest equivalence, global-unknown propagation, proxy conditional status, and provenance-recovery tests in `test/test_free_space_field_inspection.py`

## Phase 5: User Story 3 - Deterministic offline evidence package (Priority: P2)

**Goal**: Make the inspection artifact reproducible, measurable, and honest
about its historical inputs and limits.

**Independent Test**: Re-run against unchanged locked inputs and compare
normalized fingerprints, current whole-height cell records, and output schema.

- [X] T018 [US3] Record projection, field-evaluation, serialization, JSON-size, and HTML-size measurements in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T019 [US3] Record that the historical 9,648/zero-mismatch result is eye-plane evidence only and is not the new whole-height acceptance sample in `scripts/design/space_field/run_free_space_field_inspection.py`
- [X] T020 [US3] Add deterministic hash-preservation, timing/size, and whole-height-versus-section separation tests in `test/test_free_space_field_inspection.py`
- [X] T021 [US3] Add a refusal report for any required input, provenance, boundary, or unresolved-handoff inconsistency in `scripts/design/space_field/run_free_space_field_inspection.py`

## Phase 6: Polish and Cross-Cutting Concerns

- [X] T022 [P] Update `docs/software-architecture.md` with the implemented output-only inspection layer and explicit non-promotion boundary
- [X] T023 [P] Update `docs/indoor_layout_evaluation_matrix_architecture_memory.md` with the same implemented output-layer boundary
- [X] T024 Run the offline `specs/002-free-space-field-inspection/quickstart.md` command and record actual timings/output sizes for `run_20261010T160739Z_23dd5d`; manual browser load/cell-click verification remains uncompleted because `file://` is rejected by the in-app browser
- [X] T025 Stop and return a concrete owner blocker if canonical `missing_geometry` uncertainty cannot preserve the five unresolved ids without changing `features/*` — not triggered; the runner-local handoff preserves all five ids without changing `features/*`

## Dependencies and Execution Order

- Phase 1 precedes all other phases.
- Phase 2 blocks every user story because the field must not be built from
  unauthenticated or section-only inputs.
- US1 and US2 share the Phase 2 normalized handoff; US2 depends on the field
  created in US1.
- US3 depends on US1 and US2 so measurements cover the actual artifact.
- Phase 6 follows the completed stories; T025 is a stop condition, not an
  invitation to expand the Field API.

## Parallel Opportunities

- T002, T003, and T008 can proceed in parallel after the directory exists.
- T013 and T017 can proceed in parallel once their corresponding output seams
  are present.
- T022 and T023 can proceed in parallel because they touch separate architecture
  documents.

## MVP Scope

MVP is Phase 1 + Phase 2 + US1: a self-contained side-by-side offline artifact
with authenticated whole-height inputs. US2 is required before owner acceptance;
US3 supplies reproducibility and measured size evidence.
