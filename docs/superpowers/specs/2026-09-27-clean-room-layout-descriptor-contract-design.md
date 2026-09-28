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
SVG oracle ───┘                              ├─> furniture-group geometry/trend
                                             ├─> neighboring-group relations
                                             └─> scene self-description candidates
```

This design describes computable layout evidence. It does not claim psychological or perceptual validity.

## Owner clarification: machine-only scene self-description

The project itself has no human participants, human labels, human dependent
variables, or human-calibrated parameters. It produces quantitative
descriptions of a furniture layout for consumption by a separate downstream
experiment. That downstream use is outside this project's computation and
acceptance criteria; the archived raw requirements remain unchanged.

The Bayesian idea is therefore not a future perception-calibration layer. It is
an in-project candidate family for letting the scene infer latent structure
from its own geometry. Deterministic descriptors and Bayesian scene
self-description must compete on the same canonical inputs before either is
selected for a combined production path. Fusion is allowed only when the
candidates estimate the same declared quantity and their uncertainty and
provenance can be retained; otherwise their outputs remain separate evidence
channels. No human observation may be used as a prior, likelihood, training
target, or calibration target.

## Owner correction: group-level scene description is the product target

The minimum analysis unit is a furniture group. A group receives a geometric
representative and a trend-derived direction or orientation evidence. Groups
then form explicit, computable neighboring relations. The project does not
assume an externally supplied object order and does not use external order as
the product estimand.

The previous `relative-order` experiment remains useful as a deterministic
formula oracle: it tests pairwise ordering arithmetic on labeled synthetic
points. It is not the core furniture-layout descriptor and must not require a
human-provided sequence in the production path.

If a trend estimator returns an undirected axis, the result must retain axis
symmetry or report both directions. It must not invent a positive direction
without a declared scene fact or a separate inference rule.

## Problem

The repository already contains multiple adapters, a NeutralSceneV2 record family, geometry substitutes, trend evidence, and evaluator rows. Those artifacts are useful observations, but their historical boundaries and names must not silently become the scientific contract. D6 therefore needs a clean definition of what is factual input, what is normalized geometry, what is derived evidence, what is a descriptor result, and what is unavailable.

## Goals

- Use one descriptor algorithm for normalized IFC and SVG inputs.
- Preserve source identity, coordinate transforms, units, geometry settings, authored group membership, and missing-state reasons.
- Keep factual source objects separate from derived geometry and descriptor values.
- Make initial group-level descriptors independently testable and exportable.
- Make furniture-group geometry, trend evidence, and neighboring-group
  relations the primary scene-description units.
- Provide an explicit migration ledger for useful current behavior.
- Compare deterministic descriptors with Bayesian scene-self-description
  candidates using synthetic computational truth, then retain separate outputs
  or fuse them only under an explicit model-combination decision.
- Permit later descriptors without making them part of this first contract.

## Non-goals

- Psychological validation, human labels, human-study design, power analysis,
  or calibration against human judgments. Bayesian scene-self-description
  design is in scope; human-calibrated Bayesian modeling is not.
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

Group membership is a source fact when supplied by IFC or another adapter. It
does not imply adjacency, activity, usability, visual grouping, or perceptual
unity. Inferred groups are a separate candidate result and must not overwrite
authored membership.

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

## Initial group-level descriptor contracts

### `relative-order` benchmark oracle

Purpose: provide a deterministic arithmetic oracle for labeled synthetic
sequences. It is not the primary furniture-group scene descriptor.

Required inputs:

- at least two usable object anchors derived from normalized plan geometry;
- a declared comparison sequence only for benchmark fixtures, with documented
  provenance; production group self-description must not require this input;
- normalized plan geometry or an explicitly documented anchor fallback;
- analysis frame, axis, unit, and tolerance;
- stable object identities and source provenance.

The result must make its comparison basis explicit: anchor definition, sequence construction, tie handling, tolerance, and whether the reported value is a sequence/inversion summary or a spacing-deviation summary. The exact formula is a descriptor decision, not an adapter-specific choice.

Required failure behavior:

- fewer than two usable inputs: `undefined`;
- unavailable or non-projectable geometry: `not_available` or `invalid` with reason;
- ties within tolerance: retain tie metadata and do not invent an order;
- non-finite values: `invalid`.

If the benchmark sequence is absent or its provenance is unknown, the oracle is
`not_evaluated`. A computed value must never be presented as an intrinsic order
of an unlabeled scene.

### `authored_group_local_trend`

Purpose: describe local geometric direction evidence within one explicitly authored group. It is not a visual-continuity, activity, or perceptual score.

Required inputs:

- one authored group with member references;
- usable normalized plan geometry for directional members;
- analysis frame and tolerance;
- explicit member eligibility and degeneracy rules.

The result must expose member support, primary/secondary frame or equivalent directional representation, strength/concentration, geometric basis, and excluded-member reasons. Directional evidence must come from normalized geometry, not stale transform history. Circular, square, isotropic, missing, or insufficient geometry may produce `undefined` directional strength while remaining valid object facts.

The exact estimator (for example area-weighted 2D PCA or a member-frame consensus) must be selected and tested in the group-level design gate. The contract requires that the choice be versioned and auditable; it does not assume the existing trend implementation is correct.

### `neighboring_group_relations` candidate

Purpose: describe pairwise and local relations between furniture groups using
only canonical group geometry and trend evidence. Candidate relations may
include distance, boundary gap, relative orientation, overlap, alignment, and
local consistency. The neighbor rule, directionality, scale, multiple-neighbor
policy, and aggregation method require a design experiment. This candidate
must not use authored membership as a hidden adjacency rule and must not
collapse all pairwise relations into one score before the estimand is defined.

## Bayesian scene-self-description track

This track treats the scene as the source of its own latent description. A
candidate model may infer an axis, an order, a group structure, a trend, or a
joint latent arrangement from canonical geometry and source provenance. It
must report the posterior, model assumptions, priors, likelihood, identifiable
quantities, and failure/low-information states. A posterior is uncertainty
about a computational scene description; it is not a perceptual probability.

The design comparison must use synthetic scenes with known generating
parameters and perturbations for translation, rotation, scale, tessellation,
missing geometry, and contradictory members. It must evaluate recovery of the
declared latent quantity, invariance, robustness, posterior calibration against
the synthetic truth, identifiability, and reproducibility. No human labels or
human ratings are admissible evaluation targets.

The deterministic group-trend and neighboring-relation descriptors are the
transparent baselines. A Bayesian model may infer a latent axis, group
structure, or relation field from the same canonical group geometry. It must
emit an explicitly different latent-result record when its estimand differs;
it may not silently turn a benchmark reference order into production input.

Candidate competition and fusion are separate decisions. If models estimate
different quantities, keep both outputs. If they estimate the same quantity,
compare them before considering posterior model averaging or another fusion
rule. Fusion must preserve model identity, weights or posterior probabilities,
uncertainty, and the synthetic benchmark used to choose it.

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

## Design and realization phases

Every major metric or adapter has two separate phases. They must not be merged
because a candidate appears easy to implement.

### Design phase

The design phase may create exploratory scripts, synthetic fixtures, hand
calculations, geometry probes, Blender scenes, renders, and comparison tables.
These artifacts are evidence for a design decision, not production APIs.

When two or more plausible definitions, estimators, coordinate conventions, or
variable constructions could produce different results, an explicit comparison
experiment is required before the design table is approved. The experiment must
state its inputs, varied factors, expected invariants, observed outputs,
decision rule, random seed when applicable, and limitations. A hand example may
be one arm of the comparison, but it does not replace a reproducible probe when
the alternatives have materially different behavior.

This comparison includes anchor construction whenever source geometry may have
different vertex sampling densities. Arithmetic vertex means, area-weighted
centroids, and other candidates must either be compared on tessellation-varied
fixtures or explicitly excluded with a documented reason. It also includes
tolerance sensitivity near the tie boundary and the provenance of any external
comparison sequence.

Blender may be used in this phase to make geometry, axes, anchors, ties,
degeneracy, and transform effects visible. Blender previews are diagnostic
evidence about the computational variables. They are not evidence of human
perceptual validity. A preview must retain its generating script, input fixture,
settings, output path, and provenance so it can be replayed.

Design outputs that support a decision must be durable: either track the output
in Git or copy a compact manifest/result into a tracked project evidence path.
An ignored local image or blend file alone is not sufficient evidence for a
later session. If a binary preview is intentionally not tracked, the manifest
must include the exact replay command and a checksum or equivalent identity.

The design phase ends only when the owner has a reviewable design table that
separates verified external evidence, repository and runtime facts,
computational observations from exploratory probes, engineering choices,
unresolved owner decisions, and claims that require a later human experiment.
When a visual probe is used, the owner must be shown the result or a reproducible
capture and may approve, reject, or request a different variable construction
before the design table is finalized.

### Realization phase

The realization phase implements the approved design table with production code,
contract tests, regression tests, and adapters. It must not change the metric's
meaning, formula, axis policy, tie policy, or status semantics. If realization
reveals an ambiguity or a counterexample to the approved design, it stops and
reopens the design phase; it must not silently repair the specification in code.

Exploratory scripts may be promoted only after they pass the same contract and
provenance review as any other migrated behavior. A script that only supports a
design decision remains reference evidence.

## Incremental delivery and hard stops

This design must be delivered as a sequence of independently reviewable slices. It is not a big-bang rewrite and no later slice may be started because an earlier slice is inconvenient.

### Checkpoint 0 — Contract decisions only

Resolve the open axis, tolerance, formula, membership, and record-location decisions. Produce the canonical record definitions, status vocabulary, provenance minimum, and a migration ledger skeleton. This checkpoint changes documentation only.

### Checkpoint 1 — In-memory canonical records

Implement and test the smallest canonical records with hand-built Python fixtures. Do not connect IFC, SVG, Bonsai, or legacy adapters yet. Stop if the record/status/serialization tests cannot be made unambiguous.

### Checkpoint 2 — One adapter at a time

Add the IFC adapter and its contract tests first, then add the SVG oracle adapter. Each adapter must independently produce canonical facts and normalized geometry before any descriptor algorithm is added. Cross-adapter comparison is a separate test task.

### Checkpoint 3 — Design, then realize one descriptor at a time

For each descriptor, first compare plausible definitions with reproducible
fixtures or exploratory scripts, including Blender diagnostics when geometry
variables need visual inspection. Then produce the implementation design table
and obtain owner review. Only after that approval may the descriptor be
implemented with hand-computable fixtures and explicit failure states. A failed
design or realization checkpoint stops the slice; it does not trigger a rewrite
of unrelated layers.

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
4. Descriptor tests for group trend and neighboring-group relations with
   hand-computable fixtures. Keep `relative-order` tests in the benchmark
   oracle path.
5. Migration comparison tests showing which current outputs are preserved, changed, or intentionally discarded.
6. Full existing test-suite execution only after targeted contract tests pass.
7. Reproducible design-probe scripts and, where used, Blender preview artifacts with input/output provenance.
8. Independent review of the diff, migration ledger, design tables, probe outputs, test output, and claims before moving to D8–D10.

A passing test demonstrates computational behavior under the contract. It does not demonstrate psychological validity.

## Acceptance criteria for D6 design

- One canonical layer diagram and data flow are documented.
- The two descriptor contracts have explicit inputs, outputs, statuses, provenance, and failure behavior.
- IFC and SVG have equivalent adapter obligations.
- Current implementation is classified as migration candidates rather than assumed foundation.
- The clean-room boundary excludes affordance, perception, Bonsai UI, and broad future metrics.
- The project has no human-in-the-loop computation; downstream human studies
  are external consumers of the descriptors, not training or acceptance data.
- Deterministic and Bayesian scene-self-description candidates have an explicit
  competition/fusion design gate before a combined production path.
- The workplan can name exact files and tests without inventing unresolved semantics.
- Delivery is divided into the hard-stopped checkpoints above; no big-bang rewrite is planned.
- Every metric and adapter has a documented design phase before its realization phase.
- When candidate designs differ materially, a reproducible comparison experiment is recorded before owner approval.
- Blender previews, when used, are diagnostic computational evidence and are not presented as perceptual validation.
- No production code is changed during a metric, estimator, adapter, or migration design stage; previously approved realization checkpoints remain valid.

## Open decisions carried into the workplan

1. Define the furniture-group representative, trend estimator, and
   neighboring-relation policy through a reproducible design experiment.
2. Define the Bayesian scene-self-description estimand(s), priors, likelihood,
   synthetic truth, and competition criteria against deterministic baselines.
3. Decide whether any candidates estimate the same quantity and, if so, whether
   fusion is justified or separate outputs are retained.
4. Decide how multiple authored-group memberships and inferred groups are
   represented in group-level aggregation.
5. Decide whether the relative-order oracle remains benchmark-only or receives
   a separate future product interpretation.
6. Decide whether rich IFC repair gates the first implementation fixture or
   runs as a parallel acceptance task.
7. Define the canonical record location and serialization format after
   reviewing existing project conventions.

## Evidence boundary

D3–D5 evidence supports IFC semantics, geometry algorithm limitations, and separation from perception claims. It does not yet select a Bayesian self-description model, prior, likelihood, or fusion rule. It also does not prove that any descriptor predicts human judgments. Any later perceptual validation is a separate external use and must not be added to this contract as an implicit acceptance criterion.
