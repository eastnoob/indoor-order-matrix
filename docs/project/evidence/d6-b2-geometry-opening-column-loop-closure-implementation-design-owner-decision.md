# D6 B2 Geometry, Opening, and Column Loop-Closure Implementation Design Owner Decision

- Decision date: **2026-10-07**
- Design record: `d6-b2-geometry-opening-column-loop-closure-implementation-design-review.md`
- Independent review: `d6-b2-geometry-opening-column-loop-closure-implementation-design-independent-review.md`
- Evidence basis: B2 repair-v2 commit `82d08fe`
- Decision: **APPROVE IMPLEMENTATION DESIGN WITH CONDITIONS**
- Production implementation: **not started**

## Decision

The bounded B2 implementation design is approved as the planning boundary for a later, separately reviewed implementation task. This approval covers the data-flow and refusal/provenance design only. It does not select a production geometry policy or authorize unrelated space-field, UI, IFC, or Bayesian/ML work.

## Approved design boundary

- Preserve source wall, column, opening, transform, relation, and uncertainty facts in the existing Neutral Scene path.
- Keep physical column occupancy independent from conditional boundary-support evidence.
- Qualify opening host and geometry evidence before any future subtraction decision; unresolved, invalid, partial, conflicting, unsupported, and diagnostic-only observations remain traceable and refuse subtraction.
- Keep candidate polygon validity separate from source-component connectivity.
- Keep diagnostic candidate records separate from formal `AnalysisDomain` promotion.
- Refuse promotion when required evidence is incomplete, conflicting, ambiguous, unsupported, or unauthorized.
- Preserve provenance and downstream refusal/unevaluated outcomes through compatibility views.

## Mandatory implementation conditions

1. In `features/neutral_scene_views.py`, keep an AnalysisDomain scope/enclosure shell separate from wall/column physical-field occupancy. Existing exclusion of `analysis_domain.geometry_refs` must not erase physical wall or column occupancy.
2. Preserve the different dangling-opening behaviors of `adapters/svg_scene.py` and `adapters/blender_geometry.py`; carry each path's provenance/refusal semantics without silently qualifying the opening.
3. Do not use existing `geometry_tolerance` or `topology_tolerance` for B2 loop closure until a separate tolerance decision is approved.
4. Do not convert `candidate_segment_ids`, `conditional_support_in_this_fixture`, or local diagnostic labels into a public status enum or production selector.
5. Keep exact-endpoint topology evidence diagnostic-only until a production geometry algorithm and tolerance policy are separately approved.

## Deferred decisions

The following remain deferred and are outside this approval:

- production geometry tolerance, intersection, and near-contact policy;
- automatic candidate selector, precedence, ranking, score, Bayesian posterior, or ML model;
- public status enum and public serialization format;
- conflict, undo, and replacement authority;
- multi-floor, units, transforms, and work-plane policy beyond prerequisite validation;
- free-space/topology backend, resolution, origin, clearance, bottleneck, route width, and walkability;
- space-role semantics and singleton acceptance;
- real IFC integration policy and UI authority/behavior;
- production API, test expansion, and merge policy.

## Authorization boundary

The next task may prepare a separate, minimal implementation plan and branch limited to the approved B2 provenance/refusal plumbing. Before code changes, that task must name exact files, preserve legacy compatibility, define focused checks, and receive its own implementation review. This record does not authorize implementation of deferred policies or a production space-field backend.

## Verification and scope

This decision is based on the independent review's fresh 11-fixture repair-v2 reproduction, manifest/hash checks, JSON/SVG/XML parsing, and Git scope audit. No real IFC, Blender, full test suite, or production implementation was run for this decision. The decision record itself is an append-only evidence file; no production file was modified.

STOP FOR D6 B2 IMPLEMENTATION DESIGN OWNER DECISION
