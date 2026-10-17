# D6 Real IFC Boundary Candidate Comparison — Owner Decision

- Date: 2026-10-04
- Evidence reviewed: `d6-space-field-real-ifc-boundary-candidate-comparison.md`
- Independent review verdict: `ACCEPT LIMITED`
- Scope: design evidence only; no production implementation approval

## Decision

### 1. Real-IFC comparison evidence — APPROVE LIMITED

Accept the eight retained candidates as auditable, real-IFC-derived diagnostic
evidence. This acceptance does not make any candidate a room, an
`AnalysisDomain`, or a production selector input.

### 2. Candidate retention — APPROVE

Retain all eight candidate IDs and their provenance:

- 3 wall-only candidates;
- 3 wall-plus-column candidates;
- 2 column-assisted candidates.

The candidate set keeps an explicit no-selection state. No candidate is silently
removed, merged, ranked, or promoted.

### 3. Large candidates C04 and C08 — APPROVE AS DIAGNOSTIC ONLY

Keep C04 (`~251.52 m²`) and C08 (`~207.24 m²`) because they are useful evidence
of broad enclosure interpretations. Label them as broad diagnostic candidates,
not rooms. Their area must not be used as an automatic acceptance signal.

### 4. Wall and column semantics — APPROVE

- Every eligible column remains physical occupancy.
- A column may receive a boundary-support role only when explicit geometric
  contact participates in a closed diagnostic wall loop.
- Boundary support never removes the column from occupancy.
- A column must not be converted into a virtual wall by inference alone.
- Support references and occupancy-context references remain separate.

### 5. Source topology and component reporting — APPROVE WITH CLARIFICATION

Keep candidate polygon validity separate from source-union topology. The next
design artifact must use scoped names such as `candidate_component_count` and
`source_union_component_count`; the existing broad `multiple_components` field
remains diagnostic evidence and is not renamed in place.

### 6. Formal status and lifecycle — DEFER

Do not freeze the proposed `ambiguous`, `singleton`, `unassigned`, or
`user_confirmed` enum/lifecycle contract yet. Keep the current
`provisional_diagnostic_only` status and the explicit no-selection state. A
future design experiment may compare these concepts, but it must not change the
public API or production schema.

### 7. Authored-domain precedence — APPROVE AS DESIGN PRINCIPLE

When a qualified user-authored or explicit IFC analysis domain exists, it has
precedence over automatically derived candidates. Automatic candidates remain
available as provenance and comparison evidence. This principle is not a
production selector implementation and still requires lifecycle and conflict
rules before implementation.

### 8. Production and model gates — DEFER

Continue to defer:

- formal `AnalysisDomain` promotion;
- production candidate selector;
- free-space or connectivity computation;
- route, walkability, or space-role inference;
- production resolution, thresholds, or geometry backend;
- Bayesian or ML production modeling;
- public API and production integration.

## Next allowed step

Approve one further design-only experiment for **candidate-set lifecycle and
precedence**. It should use the retained real-IFC candidates plus a separate
synthetic control and compare:

1. automatic provisional candidate set;
2. multiple plausible candidates with no selection;
3. a singleton candidate that remains provisional;
4. explicit user confirmation;
5. explicit/authored domain precedence;
6. rejection or replacement while preserving provenance.

The experiment must define scoped component evidence and preserve
`not_available`, `partial`, `invalid`, `unsupported`, and `diagnostic_only`
without silently converting them into a new production enum.

## Final gate

This decision authorizes the next bounded design experiment only. It does not
authorize production implementation or any free-space computation.

**STOP FOR OWNER DECISION — REAL IFC BOUNDARY CANDIDATE COMPARISON**
