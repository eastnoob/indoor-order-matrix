# Research: Field Kernel and Free-Space Read-Only Slice

Status: draft planning evidence. This file does not claim that a production
field API or a calibrated grouping model exists.

## Decision 1 — Use one small global `Field` core with capabilities

**Decision:** Define one semantic field contract around domain, frame, query
context, value schema, representation, status, provenance, exact lookup, and
batch lookup. Add optional capabilities for spatial sampling, topology, or
bulk evaluation rather than creating a deep feature inheritance tree.

**Rationale:** The same audit requirements apply to 2D occupancy, 3D samples,
distance values, demand checks, and object-to-candidate-group evidence. Relation
fields need the core metadata and exact lookup but do not need spatial
interpolation. A small core keeps the first implementation reversible.

**Alternatives considered:** Separate `FreeSpaceField` and
`InferredGroupField` base hierarchies were rejected because they duplicate
status/provenance/query semantics and make later cross-channel composition
harder. A single numeric score was rejected because it hides occupancy,
distance, demand, and influence semantics.

## Decision 2 — Keep physical channels separate

**Decision:** A bundle may share domain/frame/query context, but occupancy,
boundary distance, occupancy clearance, human-demand qualification, and
influence/decay remain distinct channels.

**Rationale:** Occupancy is categorical and does not decay. Distance retains
physical units. Demand is a comparison against an explicit requirement.
Influence is the only channel where a declared decay/kernel operator is
appropriate. Combining them would make a result impossible to explain or
audit.

**Alternatives considered:** A single “free-space strength” field was rejected
because a high score could not reveal whether it came from distance, missing
occupancy, a threshold, or an influence kernel.

## Decision 3 — Preserve exact lookup and batch lookup as separate operations

**Decision:** The minimum contract has `evaluate(point, query)` and
`evaluate_many(points, query)`. `sample`/interpolation is optional.

**Rationale:** The current B3 artifact is a discrete serialized field. Exact
lookup can preserve its states without inventing values between samples. Batch
lookup supports performance without requiring a dense 3D allocation. Relation
fields can use the same audit envelope without pretending that object ids are
spatial coordinates.

## Decision 4 — Treat B3 as a read-only compatibility boundary

**Decision:** Keep `features/discrete_space_field.py` unchanged. Add a later
adapter that maps its validated dictionary to field samples while preserving
schema, variant, hashes, source sections, status counts, and open limitations.

**Rationale:** The loader already has focused tests and is the stable package
boundary. Changing its return shape or importing production features into the
loader would break the current B3 evidence chain and create a cycle.

**Alternatives considered:** Feeding the B3 dictionary directly into
`evaluate_scene` was rejected because domain alignment, coordinate offsets,
unknown coverage, inventory completeness, and sampled-versus-polygon semantics
are unresolved.

## Decision 5 — Use the eight fixtures as design probes, not truth

**Decision:** Reuse `scripts/design/group_level/self_description_competition_fixtures.json`
for status/provenance/channel-isolation and deterministic replay. Keep all
probe formulas labeled `probe_only_not_production`.

**Rationale:** The fixtures cover minority labels, disconnected gaps,
geometry conflict, barriers, semantic veto, context, missing channels, and
invalid geometry. They do not define a complete analysis domain, full 3D
occupancy, or psychological ground truth.

**Delegated evidence:** `fixture_plan_audit` mapped all eight fixtures to the
field core, free-space, and membership checks. `field_integration_audit`
confirmed the B3 adapter boundary and listed current tests/callers at risk.

## Decision 6 — Defer aggregation and probability calibration

**Decision:** Store evidence contributions with support, quality, polarity,
status, source references, and explanation. Defer the production aggregation
rule and any Bayesian calibration until candidate generation, dependence,
holdout validation, and performance thresholds are specified.

**Rationale:** The user needs unequal and overlapping membership strength, but
that does not require calling the value a probability. PSL-like weighted rules,
belief functions, Choquet-style aggregation, and Bayesian calibration remain
research options; none is selected as production truth by this plan.

## Existing references used

- `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- `docs/software-architecture.md`
- `docs/project/space-field-base-contract-brainstorm.md`
- `docs/project/b3-space-field-handoff-and-occupancy-plan.md`
- `docs/project/b3-shared-occupancy-enrollment-plan.md`
- `features/discrete_space_field.py`
- `scripts/design/group_level/self_description_competition_fixtures.json`
- `scripts/design/group_level/run_self_description_competition_probe.py`
- Existing B3 and discrete-field tests listed in the delegated audit.

## Owner-proposed resolutions for the first planning checkpoint

- Use `Field` as the single public concept; keep capability composition shallow
  and avoid competing functional base classes.
- Treat statuses as staged gates rather than a hidden total score. A missing
  domain is `not_available`; only a valid target outside an available domain is
  `outside`; incomplete but usable evidence is `unknown`; limited-scope output
  is `conditional`.

The detailed wording is recorded in [owner-decision.md](owner-decision.md).

## Open questions that remain explicit

1. The selected module-level export policy for `Field` after US1 tests pass.
2. The selected analysis-domain geometry and opening/door semantics for a future
   free-space evaluator.
3. Numeric performance target and memory budget for batch queries.
4. Which evidence aggregation rule, if any, is validated for inferred groups.
5. Whether and when a field layer may be promoted into `evaluate_scene`.
