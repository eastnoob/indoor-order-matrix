# Clean-Room Layout Descriptor Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to execute this plan task-by-task. The plan is intentionally incremental: stop at every checkpoint and wait for review before starting the next checkpoint.

**Goal:** Implement the first clean-room canonical contract for IFC/SVG layout descriptors, then add one adapter and one descriptor at a time while retaining only current behavior that passes the new contract.

**Architecture:** New canonical records and algorithms are the normative layer. IFC and SVG adapters translate into those records; they do not compute adapter-specific metrics. Existing NeutralSceneV2, evaluator payloads, helpers, fixtures, and tests are migration candidates or reference evidence only. Delivery proceeds through hard-stopped checkpoints so a failed contract or descriptor does not trigger a big-bang rewrite.

**Tech Stack:** Python 3.12 under Pixi, standard-library dataclasses/JSON, existing `numpy`, `shapely`, and `ifcopenshell` only when a task requires them, pytest, IFC4 fixtures, and SVG fixtures. Design probes may use only `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`; realization tasks do not require Blender unless a separately approved verification step adds it.

**Spec:** `docs/superpowers/specs/2026-09-27-clean-room-layout-descriptor-contract-design.md`

## Global Constraints

- The current implementation is reference material, not the contract baseline.
- Do not add a compatibility alias merely to preserve an old name.
- Do not add dependencies; use the Pixi-locked environment.
- Do not modify the vendored OCTA toolbox.
- Do not repair the rich IFC or run Bonsai import in Checkpoints 0–4.
- Do not claim psychological or perceptual validity.
- Every new or modified project-owned function has an English-first docstring; important geometry, provenance, status, and adapter handoff steps have English-first intent comments.
- `undefined`, `invalid`, `not_available`, and `not_evaluated` remain distinct from numeric zero.
- Every checkpoint ends with targeted tests or a documented reason it cannot yet be tested.
- The executor may run several tasks in one session, but must stop at each `STOP FOR REVIEW` marker and report the commit, tests, changed files, and open decisions before continuing.

## Design/realization rule

Each metric, estimator, adapter, or coordinate convention has two phases:

1. **Design:** exploratory scripts, synthetic fixtures, hand calculations, and
   Blender diagnostics are allowed; production modules and production tests are
   not. If plausible alternatives differ materially, a reproducible comparison
   experiment is mandatory.
2. **Realization:** after the owner approves the design table, implement the
   exact approved semantics with production code and tests. Any implementation
   ambiguity reopens design instead of being resolved silently in code.

Blender design probes must use only
`D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`, retain their
script/fixture/settings/output provenance, and be described as computational
diagnostics rather than perceptual validation.

Design-only scripts are still project-owned code: give them English-first
docstrings/comments, deterministic command-line entry points where practical,
and enough metadata to replay the exact probe. They must remain outside
production import paths until separately approved.

## Review Focus

- Legacy leakage: new canonical modules must not import evaluator score dictionaries or use SVG element names as semantics; test: import and fixture tests run without the legacy evaluator.
- Contract strictness: malformed IDs, non-finite numbers, invalid units, invalid frames, and unknown statuses fail at construction or deserialization; test: negative cases in `test/test_canonical_layout_contract.py`.
- Geometry provenance: every projected geometry records frame, unit, source representation, and method; test: round-trip and missing-geometry cases.
- Adapter equivalence: equivalent IFC and SVG fixtures produce the same canonical facts before descriptor computation; test: canonical comparison fixture.
- Incremental scope: no task imports or modifies the next checkpoint's implementation; test: checkpoint-specific test selection and diff review.

---

### Task 0: Freeze the migration ledger and checkpoint protocol

**Files:**
- Create: `docs/project/d6-migration-ledger.md`
- Modify: none
- Test: document self-check only

**Interfaces:**
- Consumes: the D6 design spec and current repository inventory.
- Produces: a ledger that later tasks update; it is not a production API.

- [ ] **Step 1: Create the ledger skeleton**

  Add one row per current candidate family: placement/unit conversion, geometry extraction, MassPatch construction, authored group extraction, trend estimation, evaluator rows, SVG parsing, IFC adapter, preview, and tests. Columns must be `candidate`, `current_location`, `classification`, `contract_reason`, `tests`, `replacement_or_stop`, and `status`.

- [ ] **Step 2: Mark only current knowledge**

  Use `unknown` where the clean-room contract has not tested behavior. Do not mark a component `migrate` merely because current tests pass.

- [ ] **Step 3: Check the ledger**

  Verify no production files changed and no row claims psychological validity. Commit as `docs: add clean-room migration ledger`.

Continue to Task 1 in the same execution session unless the ledger exposes a scope or contract conflict.

---

### Task 1: Implement canonical records and strict serialization (Checkpoint 1)

**Files:**
- Create: `features/canonical_layout_contract.py`
- Test: `test/test_canonical_layout_contract.py`

**Interfaces:**
- Produces the only normative record types for later tasks:
  - `ResultStatus`
  - `AnalysisFrame`
  - `AxisSpec`
  - `SourceObjectFact`
  - `SourceGeometry3D`
  - `PlanGeometry`
  - `AuthoredGroupFact`
  - `CanonicalScene`
  - `DescriptorResult`
  - `validate_canonical_scene(scene: CanonicalScene) -> None`
  - Each record exposes `to_dict() -> dict[str, JsonValue]` and a strict `from_dict(data: object) -> RecordType`.

  `AxisSpec` contains a frame reference, a named axis, a unit vector in that frame, and an explicit direction convention; it must not be inferred from an SVG element name or an adapter-local default.

- [ ] **Step 1: Write failing construction and round-trip tests**

  Add tests for valid hand-built records, JSON round-trip, stable ordering of object/group references, and descriptor results with each allowed status.

- [ ] **Step 2: Write failing rejection tests**

  Cover empty IDs, non-finite floats, invalid units, non-orthonormal frames, non-positive tolerances, unknown statuses, inconsistent status/value combinations, and unexpected JSON fields.

- [ ] **Step 3: Implement the minimum immutable records**

  Use frozen dataclasses and standard-library validation. Keep source facts, geometry, authored relations, and descriptor results as separate records. Do not import `features.scene_contract` or any adapter.

- [ ] **Step 4: Run the focused contract tests**

  Run: `pixi run pytest test/test_canonical_layout_contract.py -q`
  Expected: all focused tests pass.

- [ ] **Step 5: Commit**

  Commit as `feat: add clean-room canonical layout contract`.

**STOP FOR REVIEW:** the records and status vocabulary must be reviewed before geometry or adapters are added.

---

### Task 2: Add normalized frame and plan-geometry operations (Checkpoint 1 continuation)

**Files:**
- Create: `features/canonical_layout_geometry.py`
- Test: `test/test_canonical_layout_geometry.py`
- Modify: `features/canonical_layout_contract.py` only if a missing field is proven by a failing test

**Interfaces:**
- `normalize_analysis_frame(frame: AnalysisFrame) -> AnalysisFrame`
- `transform_points(points: Sequence[Vector3], matrix: Matrix4) -> tuple[Vector3, ...]`
- `project_plan_geometry(source: SourceGeometry3D, frame: AnalysisFrame) -> PlanGeometry`
- `plan_anchor(geometry: PlanGeometry) -> tuple[float, float] | None`

- [ ] **Step 1: Write tests for frame and transform behavior**

  Test identity, translation, rotation, unit conversion, and rejection of non-finite or non-orthonormal inputs.

- [ ] **Step 2: Write tests for projection status**

  Test usable triangles, empty geometry, insufficient vertices, degenerate triangles, non-finite coordinates, and unsupported source geometry. Assert explicit status and reason, never numeric zero substitution.

- [ ] **Step 3: Implement the minimum geometry operations**

  Keep projection independent of IFC, SVG, and legacy helpers. Record frame ID, unit conversion, source representation, and method in provenance.

- [ ] **Step 4: Run focused tests and existing contract tests**

  Run: `pixi run pytest test/test_canonical_layout_contract.py test/test_canonical_layout_geometry.py -q`
  Expected: all pass.

- [ ] **Step 5: Commit**

  Commit as `feat: add canonical plan geometry operations`.

**STOP FOR REVIEW:** Checkpoint 1 is complete only if canonical records and normalized geometry work with hand-built fixtures and no adapter import.

---

### Task 3: Record initial relative-order candidate designs (Checkpoint 3 design baseline)

**Files:**
- Create: `docs/project/d6-relative-order-decision.md`
- Test: hand-computable examples embedded in the decision document

**Interfaces:**
- Produces the algorithm contract later consumed by `compute_relative_order(...)`.

- [ ] **Step 1: Compare candidate definitions**

  Compare inversion-rate/order-consistency and spacing-deviation summaries using the same small point fixtures. Record required anchors, axis declaration, tie handling, normalization, and interpretation limits.

- [ ] **Step 2: Record candidate choices and provisional policy**

  Do not treat a formula as final because it matches an existing evaluator row. If evidence cannot distinguish the candidates, mark the decision owner question and carry it into Task 3a.

- [ ] **Step 3: Record invariants and failure cases**

  Include translation invariance under a moved analysis frame, explicit rotation behavior, duplicate/tied positions, fewer than two objects, and missing geometry.

- [ ] **Step 4: Commit**

  Commit as `docs: decide relative-order contract`.

**STOP FOR DESIGN REVIEW:** no relative-order production code may be written until the candidate comparison experiment and design table are approved.

---

### Task 3a: Compare relative-order candidate designs (Checkpoint 3 design phase)

**Files:**
- Create: `docs/project/d6-relative-order-design-experiment.md`
- Create: exploratory scripts/fixtures in a clearly marked design-only location
- Required attempt for spatial variables: Blender scene, render, or viewport capture with replay metadata; record an explicit limitation if the UI cannot be inspected reliably
- Modify: none of the production `features/`, `adapters/`, or `test/` modules

**Interfaces:**
- Produces a reproducible comparison of order-consistency and spacing-consistency candidates for design review.

- [ ] **Step 1: Define the comparison before running it**

  Record the factors, hand-built and synthetic fixtures, expected invariants, tie cases, transform cases, output measures, decision rule, seed, and limitations. Do not use human-perception language as an outcome measure.

- [ ] **Step 2: Run the smallest sufficient probes**

  Compare the candidates on aligned, reversed, uneven, tied, translated, rotated, and degenerate layouts. Use the portable Blender probe for the spatial variables and keep a scriptable numerical oracle for every result. Show the resulting scene or capture to the owner before closing the design phase; if inspection is unavailable, record that limitation and do not claim visual verification.

- [ ] **Step 3: Record observations and evidence classes**

  Separate external evidence, repository facts, computational observations, engineering interpretation, and unresolved owner decisions. Preserve raw inputs and generated outputs.

- [ ] **Step 4: Commit design evidence**

  Commit as `docs: compare relative-order design candidates`.

**STOP FOR DESIGN REVIEW:** do not finalize the implementation design table or write descriptor production code until the probe results have been reviewed.

---

### Task 3b: Write and review the relative-order implementation design (Checkpoint 3 design gate)

**Files:**
- Create: `docs/project/d6-relative-order-implementation-design.md`
- Modify: `docs/project/d6-relative-order-decision.md` only to record the explicit owner approval
- Test: document self-check and hand-computable examples; no production test code

**Interfaces:**
- Produces the implementation-level contract consumed by Task 4.

- [ ] **Step 1: Record the approved owner decision after Task 3a review**

  Update the decision record with the selected `relative-order/v1` order-consistency formula, partial-tie policy, explicit-axis policy, anchor definition, and transform semantics. Do not introduce a new formula unless Task 3a exposed a counterexample that reopens the decision.

- [ ] **Step 2: Create the implementation design table**

  Document the exact function boundary, calculation order, status/reason matrix, tie metadata, provenance fields, invariants, hand-computable examples, focused test matrix, and non-goals. Distinguish the declared object sequence from any stable identifier used only for metadata.

- [ ] **Step 3: Self-review the design table**

  Check that it is implementable without importing IFC, SVG, legacy evaluator, or trend code; that every unresolved choice is surfaced; and that it does not claim psychological validity.

- [ ] **Step 4: Commit**

  Commit as `docs: design relative-order implementation`.

**STOP FOR OWNER REVIEW:** no relative-order production code may be written until the implementation design table is approved.

---

### Task 4: Implement relative-order and its tests (Checkpoint 3, first descriptor)

**Files:**
- Create: `features/canonical_layout_descriptors.py`
- Test: `test/test_canonical_layout_descriptors.py`

**Interfaces:**
- `compute_relative_order(scene: CanonicalScene, *, object_ids: Sequence[str], axis: AxisSpec, tolerance: float, algorithm_id: str) -> DescriptorResult`

- [ ] **Step 1: Write failing hand-computable tests**

  Cover aligned order, reversed order, equal/tied positions, translation, explicit rotated axis, missing geometry, insufficient objects, and non-finite input. Assert value, status, parameters, and provenance.

- [ ] **Step 2: Implement only the approved formula**

  Use canonical scene records and canonical geometry only. Do not import current evaluator functions or SVG adapters.

- [ ] **Step 3: Run focused tests**

  Run: `pixi run pytest test/test_canonical_layout_descriptors.py -q`
  Expected: all relative-order tests pass.

- [ ] **Step 4: Commit**

  Commit as `feat: add canonical relative-order descriptor`.

**STOP FOR REVIEW:** do not start group-trend work until relative-order passes independent review.

---

### Task 5a: Compare authored-group trend candidate designs (Checkpoint 3 design phase)

**Files:**
- Create: `docs/project/d6-group-trend-design-experiment.md`
- Create: design-only scripts/fixtures and optional Blender diagnostics
- Modify: none of the production `features/`, `adapters/`, or `test/` modules

**Interfaces:**
- Produces a reproducible comparison of candidate trend estimators and membership policies.

- [ ] **Step 1: Compare candidate estimators**

  Compare area-weighted plan-geometry PCA and member-frame consensus on directional, square, circular, isotropic, opposing, and mixed-member fixtures.

- [ ] **Step 2: Compare membership and degeneracy policies**

  Probe multiple-group membership, missing geometry, insufficient members, and degenerate direction support. Record the decision rule and limitations.

- [ ] **Step 3: Record computational observations**

  Preserve scripts, fixtures, numerical outputs, and any Blender diagnostic scene. Separate computational behavior from perceptual claims.

- [ ] **Step 4: Commit and stop**

  Commit as `docs: compare authored-group trend designs`.

**STOP FOR DESIGN REVIEW:** do not write the trend implementation design table or production code.

---

### Task 5b: Write and review the authored-group trend implementation design

**Files:**
- Create: `docs/project/d6-group-trend-implementation-design.md`
- Modify: `docs/project/d6-group-trend-design-experiment.md` only to record owner-approved decisions
- Test: document self-check and hand-computable examples; no production test code

**Interfaces:**
- Produces the implementation-level contract for `compute_authored_group_local_trend(...)`.

- [ ] **Step 1: Define estimator, eligibility, degeneracy, strength, and membership semantics**
- [ ] **Step 2: Record status/reason and provenance matrices**
- [ ] **Step 3: Record focused test matrix and explicit non-goals**
- [ ] **Step 4: Commit as `docs: design authored-group trend implementation`**

**STOP FOR OWNER REVIEW:** no trend production code may be written until the design table is approved.

---

### Task 5c: Implement authored-group local trend (Checkpoint 3 realization)

**Files:**
- Modify: `features/canonical_layout_descriptors.py`
- Modify: `test/test_canonical_layout_descriptors.py`

**Interfaces:**
- `compute_authored_group_local_trend(scene: CanonicalScene, *, group_id: str, estimator_id: str, tolerance: float) -> DescriptorResult`

- [ ] **Step 1: Write tests from the approved design table**
- [ ] **Step 2: Implement only the approved estimator and policies**
- [ ] **Step 3: Run `pixi run pytest test/test_canonical_layout_descriptors.py -q`**
- [ ] **Step 4: Commit as `feat: add canonical authored-group trend descriptor`**

**STOP FOR REVIEW:** do not migrate current trend code until the clean-room descriptor passes.

---

### Task 6a: Design the IFC adapter mapping (Checkpoint 2 design phase)

**Files:**
- Create: `docs/project/d6-ifc-adapter-design.md`
- Create: design-only extraction probes or fixture manifests as needed
- Modify: none of the production adapter or test modules

**Interfaces:**
- Produces the IFC-to-canonical mapping table and missing/invalid behavior contract.

- [ ] **Step 1: Map IFC facts, placement, units, representations, and explicit groups**
- [ ] **Step 2: Compare representation/placement alternatives with the small IFC fixture**
- [ ] **Step 3: Record failure states, provenance, rich-IFC exclusion, and any Blender/Bonsai diagnostic observations**
- [ ] **Step 4: Commit as `docs: design canonical IFC adapter`**

**STOP FOR DESIGN REVIEW:** no IFC adapter production code may be written until the mapping design is approved.

---

### Task 6b: Add the IFC adapter bridge (Checkpoint 2 realization)

**Files:**
- Create: `adapters/canonical_layout_ifc.py`
- Test: `test/test_canonical_layout_ifc.py`
- Reference only: `adapters/ifc_bonsai.py`

**Interfaces:**
- `load_ifc_canonical(path: Path, *, frame: AnalysisFrame | None = None) -> CanonicalScene`

- [ ] **Step 1: Write adapter contract tests**

  Use the valid small IFC fixture first. Assert IFC4 source metadata, stable GlobalIds, placement expansion, selected representation provenance, explicit IfcGroup membership, units, and source-level missing geometry.

- [ ] **Step 2: Implement the smallest IFC extraction**

  Extract only furniture/recognized product facts, explicit groups, placement, selected geometry, and source provenance needed by the two descriptors. Do not repair invalid IFC, infer affordance, or call Bonsai.

- [ ] **Step 3: Add invalid/missing behavior tests**

  Test missing geometry, unsupported representation, invalid placement, and non-IFC input. Preserve explicit statuses and reasons.

- [ ] **Step 4: Run adapter plus canonical tests**

  Run: `pixi run pytest test/test_canonical_layout_contract.py test/test_canonical_layout_geometry.py test/test_canonical_layout_ifc.py -q`
  Expected: all pass.

- [ ] **Step 5: Update migration ledger and commit**

  Classify old IFC helpers as `migrate`, `wrap`, `rewrite`, `discard`, or `reference_only` based on these tests. Commit as `feat: add canonical IFC layout adapter`.

**STOP FOR REVIEW:** rich acceptance IFC repair remains a separate task and is not silently included here.

---

### Task 7a: Design the SVG oracle mapping (Checkpoint 2 design phase)

**Files:**
- Create: `docs/project/d6-svg-adapter-design.md`
- Create: design-only fixture manifests or parser probes as needed
- Modify: none of the production adapter or test modules

**Interfaces:**
- Produces the SVG-to-canonical mapping table and equivalence comparison plan.

- [ ] **Step 1: Define fixture semantics without treating SVG IDs or draw order as meaning**
- [ ] **Step 2: Define unsupported-element, transform, unit, and missing-geometry behavior**
- [ ] **Step 3: Define the IFC/SVG equivalence comparison before implementation**
- [ ] **Step 4: Commit as `docs: design canonical SVG oracle`**

**STOP FOR DESIGN REVIEW:** no SVG adapter production code may be written until the mapping design is approved.

---

### Task 7b: Add the SVG oracle adapter (Checkpoint 2 realization)

**Files:**
- Create: `adapters/canonical_layout_svg.py`
- Test: `test/test_canonical_layout_svg.py`
- Reference only: `adapters/svg_scene.py`

**Interfaces:**
- `load_svg_canonical(path: Path, *, frame: AnalysisFrame | None = None) -> CanonicalScene`

- [ ] **Step 1: Write oracle adapter tests**

  Use a small fixture with known rectangles/ellipses and `test/SVG_baseline.svg`. Assert that unsupported SVG elements become explicit unavailable records rather than silently becoming semantic furniture.

- [ ] **Step 2: Implement the translation boundary**

  Reuse an existing parser only behind a translation function whose output is canonical. Record the reuse in the migration ledger; do not expose SVG IDs or legacy evaluator fields to descriptor algorithms.

- [ ] **Step 3: Add cross-adapter equivalence tests**

  Build equivalent IFC and SVG fixtures and compare canonical object identities, normalized anchors/geometry within tolerance, group membership, and source-independent descriptor inputs.

- [ ] **Step 4: Run adapter and descriptor tests**

  Run: `pixi run pytest test/test_canonical_layout_ifc.py test/test_canonical_layout_svg.py test/test_canonical_layout_descriptors.py -q`
  Expected: all pass.

- [ ] **Step 5: Commit and stop**

  Commit as `feat: add canonical SVG oracle adapter`.

**STOP FOR REVIEW:** Checkpoint 2 is complete only when both adapters produce equivalent canonical inputs for the comparison fixture.

---

### Task 8a: Design selective migration decisions (Checkpoint 4 design phase)

**Files:**
- Modify: `docs/project/d6-migration-ledger.md`
- Create: `docs/project/d6-migration-design.md`
- Test: comparison plan and fixture inventory only; no migration code

**Interfaces:**
- Produces a reviewable migrate/wrap/rewrite/discard/reference-only decision for each proposed component.

- [ ] **Step 1: Compare current behavior with the approved canonical contracts**
- [ ] **Step 2: Record evidence, contract violations, replacement path, and rollback boundary**
- [ ] **Step 3: Choose only the smallest candidate for the first realization**
- [ ] **Step 4: Commit as `docs: design selective migration decisions`**

**STOP FOR OWNER REVIEW:** no legacy helper may be moved or wrapped until the migration design is approved.

---

### Task 8b: Selectively migrate or discard current behavior (Checkpoint 4 realization)

**Files:**
- Modify: `docs/project/d6-migration-ledger.md`
- Create: `test/test_canonical_layout_migration.py`

**Interfaces:**
- Consumes canonical adapter/descriptor APIs from Tasks 1–7.
- Produces no new public contract; comparison tests and migration decisions only.

- [ ] **Step 1: Add comparison fixtures**

  Run the clean-room descriptors and current implementation on equivalent fixture inputs. Record values, statuses, provenance differences, and intentional omissions.

- [ ] **Step 2: Classify one component at a time**

  Mark current placement conversion, MassPatch generation, group extraction, and trend helpers `migrate`, `wrap`, `rewrite`, `discard`, or `reference_only`. Each classification must cite a test or a specific contract violation.

- [ ] **Step 3: Migrate only passing components**

  Move or wrap the smallest useful component. Do not port the whole evaluator, region/path system, score matrix, or preview layer.

- [ ] **Step 4: Run migration comparison tests**

  Run: `pixi run pytest test/test_canonical_layout_migration.py -q`
  Expected: every preserved behavior has a passing equivalence or an explicit accepted difference.

- [ ] **Step 5: Commit**

  Commit as `docs: record clean-room migration decisions` or a smaller code commit when a component is actually migrated.

**STOP FOR REVIEW:** the owner decides whether another component is worth migrating.

---

### Task 9: Checkpoint 5 acceptance and handoff

**Files:**
- Modify: `docs/project/d6-migration-ledger.md`
- Create: `docs/project/d6-acceptance-report.md`

**Interfaces:**
- Consumes all prior checkpoint artifacts and test outputs.
- Produces a reviewable D6 acceptance report; no new algorithm.

- [ ] **Step 1: Run targeted clean-room tests**

  Run the full canonical contract, geometry, adapter, descriptor, and migration test files. Record the exact command and result.

- [ ] **Step 2: Run the relevant existing regression tests**

  Run the smallest existing test set that exercises reused helpers. Do not reinterpret unchanged legacy failures as clean-room failures; record them separately.

- [ ] **Step 3: Audit comments and provenance**

  Review every changed project-owned function for English-first docstrings, intent comments, and complete provenance/status handling.

- [ ] **Step 4: Write the acceptance report**

  Include passed checkpoints, failed or skipped checks, migrated/discarded components, known limitations, and the exact next decision for D8–D10. State again that computational acceptance is not psychological validation.

- [ ] **Step 5: Commit and request review**

  Commit as `docs: record clean-room contract acceptance`.

**STOP FOR OWNER REVIEW:** do not begin broad metric work, IFC repair, or Bonsai UI validation from this plan without a new approved plan.

## Execution order and hard gates

```text
Task 0
  -> Tasks 1-2 (Checkpoint 1)
  -> STOP/review
  -> Task 3 (initial candidate design)
  -> STOP/design review
  -> Task 3a (relative-order design experiment)
  -> STOP/design review
  -> Task 3b (relative-order implementation design)
  -> STOP/owner review
  -> Task 6a (IFC adapter design)
  -> STOP/design review
  -> Task 6b (IFC adapter realization)
  -> STOP/review
  -> Task 7a (SVG adapter design)
  -> STOP/design review
  -> Task 7b (SVG adapter realization + equivalence)
  -> STOP/review
  -> Task 4 (relative-order realization)
  -> STOP/review
  -> Task 5a (trend design experiment)
  -> STOP/design review
  -> Task 5b (trend implementation design)
  -> STOP/owner review
  -> Task 5c (trend realization)
  -> STOP/review
  -> Task 8a (migration design)
  -> STOP/owner review
  -> Task 8b (selective migration realization)
  -> STOP/review
  -> Task 9 (acceptance)
```

The first execution request may run **Tasks 0–2 as Checkpoint 1**: create the ledger, implement the in-memory canonical records, and implement normalized frame/plan geometry. It must stop after Task 2 for review. Later requests may advance one checkpoint at a time only after the previous checkpoint passes. No executor should implement later tasks in anticipation of approval.

## Handoff checklist

The executor must return after each stop:

- commit hash;
- changed files;
- exact test commands and results;
- migration classifications changed;
- design scripts, preview artifacts, and design-table paths when the task is in the design phase;
- unresolved decisions;
- explicit phase status: design-only, owner-approved design, or realization;
- whether the next checkpoint is safe to start.

No task is complete because code exists; it is complete only when its focused tests and provenance/status review pass.
