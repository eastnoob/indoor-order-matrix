# Clean-Room Unified Layout Descriptor Contract

- **Status:** Draft for owner review
- **Date:** 2026-09-27
- **Stage:** D6 design specification; no production implementation authorized by this document
- **Inputs:** D3–D5 evidence ledger and synthesis, Phase 0 decisions, architecture memory, existing repository inspection

## Design decision

Design a new source-independent contract for the first quantitative layout-description slice, then evaluate current code as migration candidates. The current implementation is reference material, not the specification baseline. A component can move into the new implementation only after it satisfies this contract and independent tests; otherwise it is wrapped, rewritten, or discarded.

The first slice is deliberately narrow:

```text
IFC4 adapter ─┐
              ├─> canonical scene facts ─> normalized plan geometry
SVG oracle ───┘                              ├─> relative-order
                                             └─> authored-group local trend
```

This design describes computable layout evidence. It does not claim psychological or perceptual validity.

## Problem

The repository already contains multiple adapters, a NeutralSceneV2 record family, geometry substitutes, trend evidence, and evaluator rows. Those artifacts are useful observations, but their historical boundaries and names must not silently become the scientific contract. D6 therefore needs a clean definition of what is factual input, what is normalized geometry, what is derived evidence, what is a descriptor result, and what is unavailable.

## Goals

- Use one descriptor algorithm for normalized IFC and SVG inputs.
- Preserve source identity, coordinate transforms, units, geometry settings, authored group membership, and missing-state reasons.
- Keep factual source objects separate from derived geometry and descriptor values.
- Make the first two descriptors independently testable and exportable.
- Provide an explicit migration ledger for useful current behavior.
- Permit later descriptors without making them part of this first contract.

## Non-goals

- Psychological validation, human labels, experiment design, power analysis, or Bayesian calibration.
- Furniture affordance generation, clearance interpretation as human usability, route/path inference, boundary channels, visual complexity, or perception weighting.
- Repairing the rich acceptance IFC.
- Live Bonsai UI/import verification.
- Reproducing every current evaluator row.
- Treating SVG element IDs, legacy dictionary keys, or current class names as normative.

## Clean-room architecture

The contract has five layers. Names below are design names; they are not promises to preserve existing Python classes.

### 1. Source facts

Adapters emit factual records with no descriptor scores:

- `object_id`: stable project identifier plus source identifier/provenance;
- `semantic_type`: source type such as `IfcFurniture`, with `unknown` retained when absent;
- `world_transform`: fully expanded source placement in the selected coordinate system;
- `geometry_refs`: source representations and representation contexts;
- `authored_group_refs`: explicit group membership only;
- `source_unit` and source-file metadata;
- source-level uncertainty records.

IFC facts come from IFC4 semantics. SVG is a benchmark adapter that produces equivalent factual records; SVG naming and drawing order are not semantic authority.

### 2. Canonical analysis frame

A frame record defines:

- stable frame identifier;
- origin and orthonormal basis;
- source and analysis units;
- positive finite geometry and topology tolerances;
- plane used for the first slice;
- axis declaration and orientation convention;
- transform provenance.

No descriptor may silently choose a world axis, unit, or tolerance. If the source does not author a frame, the adapter must use the documented default or return an explicit unavailable state.

### 3. Normalized plan geometry

The canonical geometry record is a source-independent plan projection derived from source geometry:

- object reference;
- ordered vertices/triangles or an equivalent auditable footprint;
- source representation and geometry settings;
- transform and unit conversion provenance;
- geometric status: `computed`, `undefined`, `invalid`, or `not_available`;
- uncertainty and failure reason.

The contract does not require convex hulls, bounding boxes, or PCA. They are algorithms that may be selected for a descriptor and must retain their own method and limitation metadata. Empty, degenerate, non-finite, or non-projectable geometry is never silently converted to zero.

### 4. Authored relations

An authored group record contains:

- group identifier and source reference;
- ordered or canonicalized member object references;
- source object type/role when present;
- provenance and membership warnings.

Group membership is a source fact. It does not imply adjacency, activity, usability, visual grouping, or perceptual unity. Inferred groups are outside this slice.

### 5. Descriptor results

Every descriptor result contains:

- `descriptor_id`;
- `scope` and input object/group references;
- `value` or a structured value;
- `status`: `computed`, `undefined`, `invalid`, `not_available`, or `not_evaluated`;
- output unit, if applicable;
- algorithm identifier and version;
- parameters, including axis and tolerance;
- source and geometry provenance;
- warnings and limitations.

Result records are analysis outputs. They are not written back into factual IFC by default.

## First descriptor contracts

### `relative-order`

Purpose: describe a relative arrangement along an explicitly declared analysis axis. The name is an engineering descriptor and must not be presented as a human order judgment.

Required inputs:

- at least two usable object anchors or intervals;
- normalized plan geometry or an explicitly documented anchor fallback;
- analysis frame, axis, unit, and tolerance;
- stable object identities and source provenance.

The result must make its comparison basis explicit: anchor definition, sequence construction, tie handling, tolerance, and whether the reported value is a sequence/inversion summary or a spacing-deviation summary. The exact formula is a descriptor decision, not an adapter-specific choice.

Required failure behavior:

- fewer than two usable inputs: `undefined`;
- unavailable or non-projectable geometry: `not_available` or `invalid` with reason;
- ties within tolerance: retain tie metadata and do not invent an order;
- non-finite values: `invalid`.

### `authored_group_local_trend`

Purpose: describe local geometric direction evidence within one explicitly authored group. It is not a visual-continuity, activity, or perceptual score.

Required inputs:

- one authored group with member references;
- usable normalized plan geometry for directional members;
- analysis frame and tolerance;
- explicit member eligibility and degeneracy rules.

The result must expose member support, primary/secondary frame or equivalent directional representation, strength/concentration, geometric basis, and excluded-member reasons. Directional evidence must come from normalized geometry, not stale transform history. Circular, square, isotropic, missing, or insufficient geometry may produce `undefined` directional strength while remaining valid object facts.

The exact estimator (for example area-weighted 2D PCA or a member-frame consensus) must be selected and tested in D8–D10. The contract requires that the choice be versioned and auditable; it does not assume the existing trend implementation is correct.

## Descriptor implementation design gate

An algorithm decision record is not sufficient authorization to write code. After
the owner approves a descriptor decision, the next artifact must be a separate
implementation design table for that descriptor. The table is reviewed before
production code begins.

Each implementation design table must specify:

- the exact function boundary and input/output fields;
- pseudocode or a stepwise calculation order;
- status and reason behavior for every failure class;
- tie, tolerance, missing-data, and degeneracy handling;
- provenance and parameter requirements;
- mathematical invariants and hand-computable examples;
- a focused test matrix and explicit non-goals.

The implementation design stage is documentation-only. It may clarify an
already-approved algorithm, but it may not silently change the scientific
decision. If the table exposes an unresolved choice, implementation stops and
the owner decision record is reopened.

## Incremental delivery and hard stops

This design must be delivered as a sequence of independently reviewable slices. It is not a big-bang rewrite and no later slice may be started because an earlier slice is inconvenient.

### Checkpoint 0 — Contract decisions only

Resolve the open axis, tolerance, formula, membership, and record-location decisions. Produce the canonical record definitions, status vocabulary, provenance minimum, and a migration ledger skeleton. This checkpoint changes documentation only.

### Checkpoint 1 — In-memory canonical records

Implement and test the smallest canonical records with hand-built Python fixtures. Do not connect IFC, SVG, Bonsai, or legacy adapters yet. Stop if the record/status/serialization tests cannot be made unambiguous.

### Checkpoint 2 — One adapter at a time

Add the IFC adapter and its contract tests first, then add the SVG oracle adapter. Each adapter must independently produce canonical facts and normalized geometry before any descriptor algorithm is added. Cross-adapter comparison is a separate test task.

### Checkpoint 3 — One descriptor at a time

Implement `relative-order` with hand-computable fixtures and explicit failure states. Only after it passes should `authored_group_local_trend` be implemented. A failed descriptor checkpoint stops the slice; it does not trigger a rewrite of unrelated layers.

### Checkpoint 4 — Selective migration and comparison

Evaluate current helpers against the canonical tests and classify them as `migrate`, `wrap`, `rewrite`, `discard`, or `reference_only`. Migrate one helper or narrow behavior at a time, preserving a comparison fixture for changed behavior. Do not port the whole evaluator or all existing metrics.

### Checkpoint 5 — Acceptance review

Run targeted contract/adapter/descriptor tests, then the relevant existing regression tests. Review the diff, migration ledger, provenance, and claims. The project owner decides whether to proceed to broader D8–D10 work; a passing checkpoint does not authorize the next checkpoint automatically.

Every checkpoint must leave the repository in a runnable state or stop with its failure recorded. No checkpoint may require the entire clean-room architecture to be complete before it can be tested.

## Adapter contract

### IFC4 adapter

Must preserve IFC GlobalId, entity type, placement chain, representation/context, units, explicit `IfcRelAssignsToGroup` membership, and extraction failures. It must not infer affordance, activity, or perceptual semantics from `IfcFurniture`, `IfcGroup`, `IfcSpatialZone`, `IfcClearance`, or surface entities.

### SVG oracle adapter

Must emit the same canonical facts and normalized geometry required by the two descriptor contracts. SVG identifiers may identify fixture objects but cannot define descriptor semantics. The oracle is for deterministic algorithm comparison, not production truth.

### Legacy migration bridge

A temporary bridge may translate current NeutralSceneV2 records or evaluator payloads into the canonical contract for comparison. The bridge is compatibility code, not a new source of truth. It must be removable after the clean-room implementation is accepted.

## Migration ledger

Before moving code, classify each existing module or helper as:

- `migrate`: behavior satisfies the new contract and passes independent tests;
- `wrap`: useful behavior is retained behind the new boundary without exposing legacy semantics;
- `rewrite`: useful intent exists but algorithm, status, or provenance violates the new contract;
- `discard`: behavior is outside the first slice, unsupported by evidence, or tied to legacy semantics;
- `reference_only`: fixture/test/visual behavior informs comparison but is not reused as implementation.

The ledger must record the reason, evidence, tests, and replacement path for every selected component. No compatibility alias may be added only to avoid making a clean-room decision.

## Verification strategy

The implementation plan must include:

1. Contract tests for required fields, status propagation, units, frames, provenance, and strict serialization.
2. IFC and SVG adapter tests that produce equivalent canonical inputs for equivalent fixtures.
3. Property-style or parameterized geometry checks for translation, rotation, scale policy, ties, duplicate positions, missing geometry, non-finite values, degeneracy, and multiple group membership.
4. Descriptor tests for `relative-order` and `authored_group_local_trend` with hand-computable fixtures.
5. Migration comparison tests showing which current outputs are preserved, changed, or intentionally discarded.
6. Full existing test-suite execution only after targeted contract tests pass.
7. Independent review of the diff, migration ledger, test output, and claims before moving to D8–D10.

A passing test demonstrates computational behavior under the contract. It does not demonstrate psychological validity.

## Acceptance criteria for D6 design

- One canonical layer diagram and data flow are documented.
- The two descriptor contracts have explicit inputs, outputs, statuses, provenance, and failure behavior.
- IFC and SVG have equivalent adapter obligations.
- Current implementation is classified as migration candidates rather than assumed foundation.
- The clean-room boundary excludes affordance, perception, Bonsai UI, and broad future metrics.
- The workplan can name exact files and tests without inventing unresolved semantics.
- Delivery is divided into the hard-stopped checkpoints above; no big-bang rewrite is planned.
- No production code is changed by the design stage.

## Open decisions carried into the workplan

1. Review the implementation design table for the owner-approved
   `relative-order` formula and explicit-axis policy before coding.
2. Select the `authored_group_local_trend` estimator and degeneracy thresholds.
3. Decide how multiple authored-group memberships are represented in group-level aggregation.
4. Decide whether rich IFC repair gates the first implementation fixture or runs as a parallel acceptance task.
5. Define the canonical record location and serialization format after reviewing existing project conventions.

## Evidence boundary

D3–D5 evidence supports IFC semantics, geometry algorithm limitations, and separation from perception claims. It does not prove that either descriptor predicts human judgments. Any later perceptual validation is a separate experiment and must not be added to this contract as an implicit acceptance criterion.
