# D6 Candidate-Set Lifecycle — Final Owner Decision

- Date: 2026-10-05
- Basis: lifecycle experiment, render repair v1, and independent review
- Evidence class: limited design evidence

## Decision

**APPROVE the lifecycle design principles for continued design work.**

**DEFER production implementation, automatic selection, and public API changes.**

The repaired visualization is accepted as limited diagnostic evidence. The
excluded SHA-256 checks are a tooling limitation and are not treated as a
semantic or rendering failure; no hash verification is claimed.

## Approved principles

1. Automatic boundary candidates are retained as a candidate set. No automatic
   winner is selected merely because one candidate is a singleton or appears
   geometrically plausible.
2. Candidate-set facts and candidate-level lifecycle facts remain separate.
   Cardinality and assignment belong to the set; user actions, replacement
   history, evidence quality, and candidate validity belong to candidate records
   or explicit relations.
3. `unassigned` means that no candidate has been explicitly assigned or
   promoted to the analysis domain. It does not delete or hide retained
   candidates.
4. `ambiguous` is a set-level diagnostic description for multiple plausible
   candidates without a selection. It is not a ranking and does not create a
   production winner.
5. `singleton` is a cardinality fact only. A one-candidate set remains
   provisional until explicit owner or user confirmation exists.
6. Explicit authored or user-defined domain input takes precedence for domain
   use. Automatic candidates remain retained provenance; disagreement remains
   visible as conflict and is not silently resolved.
7. Confirmation, rejection, and replacement are explicit actions with actor,
   time, stable IDs, reasons, and provenance. Rejection preserves the rejected
   evidence; replacement preserves prior versions and links them to the active
   replacement.
8. Evidence states such as `not_available`, `partial`, `invalid`,
   `unsupported`, and `diagnostic_only` are orthogonal to lifecycle actions and
   must not be converted into a candidate winner.
9. A conflict has no automatic resolution. Downstream domain promotion remains
   unavailable until the conflict is explicitly resolved.

## Deferred items

- Exact production enum names and serialization schema.
- Whether set-level descriptors are stored as fields, relations, or derived
  views.
- Candidate selector or scoring rule.
- Formal `AnalysisDomain` promotion policy.
- Free-space, connectivity, route, walkability, Bayesian/ML, threshold,
  resolution, geometry-backend, and public-API decisions.

## Next gate

Proceed to a separate **lifecycle status-contract and implementation-design
review** using the approved principles above. That review must remain design
only and must not implement a production selector. Production implementation
can begin only after the status contract, authored-domain precedence, conflict
handling, and selector policy receive a separate explicit approval.

## Scope record

No production code, adapter, NeutralSceneV2, public API, test, dependency,
source IFC, or user Blender file was modified by this decision.
