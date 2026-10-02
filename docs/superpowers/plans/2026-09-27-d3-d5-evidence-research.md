# D3-D5 Evidence Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to execute this plan task-by-task. This plan is research-first; do not modify production code unless a task explicitly permits it.

**Goal:** Build an auditable evidence ledger that distinguishes IFC/BIM facts, geometry-algorithm correctness, software evidence, and psychological perception evidence before D6 input-contract decisions.

**Architecture:** D3-D5 is a read-only research slice whose durable output is a small set of evidence records and a synthesis decision memo. IFC schema and software documentation establish data/interop facts; mathematical and algorithmic sources establish descriptor definitions; perception studies are reported separately and cannot be used to claim psychological validity for this project.

**Tech Stack:** Markdown evidence ledger, project-local research skills, primary papers/standards/official documentation, existing `docs/` architecture notes, and the existing Pixi environment for any reproducibility checks.

**Spec:** `docs/project/phase-0-user-decisions.md`; `docs/indoor_layout_evaluation_matrix_architecture_memory.md`; `.specify/assessments/bim-furniture-layout/intake.md`; `docs/project/raw_requirements/source-01-b044dcf0.txt`; `docs/project/raw_requirements/source-02-17de9dce.txt`.

## Global Constraints

- The project computes quantitative layout descriptors for later experiments; it does not claim psychological perceptual validity.
- IFC4 -> NeutralScene is the proposed production path; SVG remains an algorithm benchmark.
- Do not treat an abstract, search snippet, repository README, or generated fixture as proof of a scientific claim.
- Every evidence item must record source, exact location, access status, claim supported, and limitations.
- Keep authored facts, inferred analysis objects, algorithmic derivation, and human-perception evidence as separate channels.
- Do not install packages, change the IFC fixture, edit production code, or run Bonsai import during D3-D5.
- If a key primary source cannot be obtained, mark it `inaccessible` and ask the project owner for the original; do not fill the gap from memory.
- Do not introduce a Bayesian or perception-calibration layer in this research slice.

## Review Focus

- Terminology drift between “order”, “regularity”, “complexity”, “symmetry”, and “visual continuity”; test: each proposed term has a source-backed operational definition or is marked unresolved.
- IFC semantics versus project-specific analysis semantics; test: every IFC claim points to schema/official documentation and every inferred concept is labeled as such.
- Algorithm correctness versus empirical validity; test: every descriptor is assigned to exactly one evidence class and cannot inherit support from another class.
- Geometry edge cases such as rotation, scale, missing meshes, occlusion, and degenerate polygons; test: the synthesis memo lists whether each candidate descriptor is invariant, sensitive, or undefined.
- Software claims about Bonsai/Blender/IfcOpenShell; test: only verified versioned documentation or a reproducible local observation is accepted.

---

### Task 1: Create the D3-D5 research ledger and search protocol

**Files:**
- Create: `docs/project/evidence/d3-d5-evidence-ledger.md`
- Create: `docs/project/evidence/d3-d5-search-log.md`

**Interfaces:**
- Consumes: Phase 0 decision record and architecture memory.
- Produces: A stable record format used by Tasks 2-5; no production-code interface.

- [ ] **Step 1: Define the evidence record fields**

  Use one record per claim with these fields: `ID`, `date`, `question`, `claim`, `evidence_class`, `source`, `version/year`, `locator`, `access_status`, `short_excerpt_or_paraphrase`, `supports`, `does_not_support`, `confidence`, and `follow_up`.

  Allowed `evidence_class` values: `IFC_SCHEMA`, `BIM_INTEROP`, `GEOMETRY_ALGORITHM`, `SOFTWARE`, `PERCEPTION_EMPIRICAL`, `ENGINEERING_INFERENCE`.

  Allowed `access_status` values: `full_text_verified`, `official_doc_verified`, `abstract_only`, `inaccessible`, `conflicting`.

- [ ] **Step 2: Record the search protocol**

  In `d3-d5-search-log.md`, record database/site, exact query, date, inclusion rule, exclusion rule, and result status. Search logs must make failed searches visible.

- [ ] **Step 3: Check ledger structure**

  Verify that every record has all required fields and that no record uses a free-form evidence class. Do not add a dependency solely for this check.

---

### Task 2: D3 terminology and descriptor definitions

**Files:**
- Modify: `docs/project/evidence/d3-d5-evidence-ledger.md`
- Modify: `docs/project/evidence/d3-d5-search-log.md`

**Interfaces:**
- Consumes: Task 1 record format.
- Produces: Evidence records for terminology and candidate descriptor definitions, plus unresolved terminology questions for D6.

- [ ] **Step 1: Search primary terminology sources**

  Search for operational definitions of spatial/layout order, regularity, symmetry, repetition, clustering, visual complexity, and continuity. Prefer original research papers, standards, or authoritative reference works. Record exact queries and exclusions.

- [ ] **Step 2: Separate descriptive and perceptual claims**

  For every source, record whether it defines a geometric/descriptive variable, reports a human judgment, or merely uses an informal term. A perceptual result must not be copied into the descriptor definition without an explicit qualification.

- [ ] **Step 3: Build a candidate-term table**

  For each candidate term, record operational formula or construction if available, required inputs, known invariances/sensitivities, and whether the source supports computation, perception, both, or neither.

- [ ] **Step 4: Verify D3 output**

  Pass condition: no candidate term is recommended for D6 unless it has either a verified operational source or an explicit `ENGINEERING_INFERENCE` label and an unresolved-evidence note.

---

### Task 3: D4 IFC/BIM semantics and geometry algorithm evidence

**Files:**
- Modify: `docs/project/evidence/d3-d5-evidence-ledger.md`
- Modify: `docs/project/evidence/d3-d5-search-log.md`

**Interfaces:**
- Consumes: Task 1 record format and D3 terminology table.
- Produces: IFC/BIM and geometry-algorithm records that constrain the NeutralScene contract and descriptor tests.

- [ ] **Step 1: Verify IFC4 relationship claims**

  Use authoritative IFC schema/documentation sources to verify placement, representation, grouping, grid, spatial-zone, covering, surface-feature, and furniture semantics relevant to the existing adapters. Record entity/attribute names and version context; do not infer missing relationships from the sample fixture.

- [ ] **Step 2: Verify BIM affordance and region claims**

  Search primary or authoritative sources for whether furniture clearance, activity zones, circulation paths, openings, and boundaries are native facts, derived geometry, or application-specific annotations. Record each as a separate evidence item.

- [ ] **Step 3: Verify geometry algorithms**

  For candidate computations already present or implied by the repository—world-space projection, bounding boxes, convex/concave footprint handling, pairwise distance, orientation/order, graph/path construction, and overlap/clearance—record the mathematical source or mark the item as engineering inference.

- [ ] **Step 4: Record edge-condition evidence**

  For every candidate algorithm, record behavior under rotation, nonuniform scale, missing geometry, degenerate geometry, multiple coordinate systems, and unit conversion. If the source is silent, record the silence rather than inventing a guarantee.

- [ ] **Step 5: Verify D4 output**

  Pass condition: D6 can trace every planned IFC field or geometry operation to either an authoritative source, an existing project contract, or an explicitly labeled engineering choice.

---

### Task 4: D5 software and perception-validity boundary

**Files:**
- Modify: `docs/project/evidence/d3-d5-evidence-ledger.md`
- Modify: `docs/project/evidence/d3-d5-search-log.md`

**Interfaces:**
- Consumes: Tasks 1-3 evidence records.
- Produces: Versioned software evidence and a separate perception-validity boundary memo inside the ledger.

- [ ] **Step 1: Verify software behavior claims**

  Check official/versioned documentation or reproducible local behavior for IfcOpenShell, Bonsai Open IFC Project, Blender 5.2.0 LTS, and any adapter API relied upon. Record the exact version and whether the claim was observed, documented, or unavailable.

- [ ] **Step 2: Search perception studies separately**

  Search for studies that test human judgments of spatial order, regularity, complexity, symmetry, grouping, or visual continuity. Record task, stimuli, population, dependent variable, and whether the study supports only an empirical association or a general validity claim.

- [ ] **Step 3: Mark unavailable originals**

  For paywalled, inaccessible, or abstract-only sources, record the gap and request the original from the project owner if it is needed for a decision. Do not use an abstract as full-text proof.

- [ ] **Step 4: Write the boundary statement**

  Add a short ledger section stating which descriptors are currently justified as computable descriptions, which have empirical perception evidence, and which have no evidence. Explicitly state that perception evidence is not a project acceptance criterion.

- [ ] **Step 5: Verify D5 output**

  Pass condition: no software README or perception paper is cited as proof of IFC schema correctness or algorithm correctness, and no geometry metric is described as psychologically valid solely because it is computable.

---

### Task 5: D3-D5 synthesis and G0.5 handoff

**Files:**
- Create: `docs/project/evidence/d3-d5-synthesis.md`
- Modify: `docs/project/evidence/d3-d5-evidence-ledger.md`

**Interfaces:**
- Consumes: Tasks 1-4 evidence records.
- Produces: A decision-ready memo for D6 and the current control thread.

- [ ] **Step 1: Build the evidence-to-decision matrix**

  For each candidate descriptor or input field, record: purpose, required source facts, computation status in the repository, evidence class, evidence confidence, missing data state, and whether it belongs in the first vertical slice.

- [ ] **Step 2: Identify contradictions and gaps**

  List conflicting definitions, inaccessible primary sources, unverified software behavior, and claims that remain engineering choices. Each gap must have an owner or a decision required from the project owner.

- [ ] **Step 3: Recommend one narrow D8-D10 slice**

  Use the default recommendation—geometry/relative-order plus authored-group local trend—only if the evidence supports it. Otherwise recommend a smaller slice and state why. Do not add perception calibration or D14 work.

- [ ] **Step 4: Run the handoff check**

  Confirm that the synthesis points to stable source locations, contains no fabricated citations or test results, and can be read without the research worker's chat history.

- [ ] **Step 5: Commit the research-only deliverable**

  Commit only the evidence documents with a message such as `docs: add D3-D5 evidence research ledger`. Do not include production code, generated binaries, or unrelated formatting changes.

## Completion Gate

D3-D5 is complete only when:

1. All searches and failed searches are logged.
2. Every claim is assigned to one evidence class with a source and access status.
3. IFC/BIM facts, algorithm evidence, software evidence, and perception evidence remain separate.
4. Unavailable primary sources are explicitly listed for owner follow-up.
5. `d3-d5-synthesis.md` recommends or rejects a single narrow D8-D10 slice and identifies the D6 contract consequences.
6. No production code, IFC fixture, Bonsai scene, or psychological-validity claim was changed.

## Handoff Instructions

The executor should return the commit hash, the two main document paths, the number of verified/full-text versus abstract-only/inaccessible sources, unresolved owner questions, and the recommended D8-D10 slice. The executor must stop at the completion gate and wait for the project owner before D6.
