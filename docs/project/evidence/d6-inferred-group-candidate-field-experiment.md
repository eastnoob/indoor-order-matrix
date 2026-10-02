# D6 inferred-group candidate-field experiment

状态：design-only checkpoint；停止在 implementation-design review 之前。

本实验复用 `features/group_self_description.py` 的 `describe_group_relations()`
输出作为 D0 共同证据输入。实验脚本和 fixture 位于
[`run_inferred_group_candidate_field_probe.py`](../../scripts/design/group_level/run_inferred_group_candidate_field_probe.py)
和
[`inferred_group_candidate_field_fixtures.json`](../../scripts/design/group_level/inferred_group_candidate_field_fixtures.json)。
外部 computational truth 位于
[`inferred_group_candidate_field_truth.json`](../../scripts/design/group_level/inferred_group_candidate_field_truth.json)；
probe 没有 truth 参数，也没有读取该文件。

## Verified repository facts

- Authored furniture groups are collected only from the explicit `furniture_group` marker by the reused evidence function.
- The current evidence function keeps geometry, semantic conflicts, missingness, space observations, provenance, and status separate; its candidate view remains `deferred`.
- The architecture memory keeps context as spatial/reference evidence and requires an explicit analysis domain for negative-space computation.
- Existing D6 evidence records already leave candidate aggregation, Bayesian priors, ML training targets, and production selectors unfrozen.

## Design assumptions

- The experimental unit is a complete synthetic layout fixture. Members and pair observations inside one fixture are not independent replicates.
- Relative scale is an experimental factor. The manifest pre-registers `relative_gap_rank`, `local_persistence_window`, and `space_profile_rank`, including parameters, formulas, and provenance.
- Aggregation is reported in parallel as `all_pairs`, `max_span`, `min_gap`, and `complete_link_diagnostic`; none is selected as a formal rule.
- `co_membership_evidence` is deterministic support, never a probability. Every candidate has `formal_membership_edge=false`.
- Ordinary type disagreement is soft negative evidence. Explicit `factual_properties["mutual_exclusion"]` is a candidate-level veto with source references.

## Observed probe outputs

- Eight fixture families ran: gap-jump, minority-mixed, geometry-conflict, space-conflict, bridge-chain, overlapping-candidates, missing-invalid, and context-perturbation.
- Each fixture produced 11 declared scale views and 44 parallel aggregation views. Four invariance variants ran: translation, rotation with frame, unit scale, and ID/traversal reorder.
- D0 remained evidence-only with `candidate_view_status=deferred`. D1 retained complete positive/negative vectors, space role references, missingness, conflicts, supporting observations, recipe parameters, and provenance.
- Overlapping, ambiguous, weak, and unassigned candidate statuses are present in the evidence. Bridge-chain and overlapping-candidates preserve shared-node alternatives; isolated nodes remain `unassigned`.
- The explicit S1/S2 mutual exclusion remains `unassigned` with the veto source reference even when geometry is close. No veto is converted to a numeric penalty.
- The missing-invalid fixture preserves `partial`, `invalid`, and `not_available` group geometry statuses. No missing or invalid geometry is filled with zero or a fabricated center.
- Empty-space role candidates are carried separately (`corridor_candidate`, `activity_space_candidate`, `separator_space`, `connector_space`). The missing-domain fixture reports `not_available`.
- Translation, rotation+frame, positive unit scale, and ID/traversal reorder all preserved the canonical relation signature. Context perturbation changed context references while authored node eligibility stayed unchanged.

## Mechanism status

| Mechanism | Result | Reason |
|---|---|---|
| D0 | `computed` | Reused `describe_group_relations()` plus deterministic local relation vectors |
| D1 | `computed` | All pre-registered relative-scale and aggregation recipes ran side by side |
| B1 | `not_run` | No owner-approved estimand, prior, likelihood, spatial dependence, identifiability plan, or calibration plan |
| M1 | `not_run` | No pre-registered feature representation, algorithm, hyperparameters, seed, or validation target; no dependency installation |

## Verification

The probe assertions passed:

1. D0 candidate view remains deferred.
2. D1 emits parallel recipes without a formal edge.
3. Hard veto wins and retains source references.
4. Partial, invalid, and missing states remain categorical.
5. Declared invariance transforms preserve the canonical relation signature.
6. Context perturbation preserves authored node eligibility.

Executed checks:

```text
pixi run python -m py_compile scripts/design/group_level/run_inferred_group_candidate_field_probe.py
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_probe.py --fixtures scripts/design/group_level/inferred_group_candidate_field_fixtures.json --output docs/project/evidence/d6-inferred-group-candidate-field-experiment.json
git diff --check
```

Fixture manifest SHA-256: `b4aaeb588fe6ebbbc3033f1bd93b48d1696a7be931c12aaa79488cc89ab4dc2a`.

## Interpretation

The deterministic probe demonstrates an auditable comparison surface: relative
scale changes the candidate view, aggregation recipes can disagree, and the
schema can retain overlap, ambiguity, weak support, unassignment, hard vetoes,
and channel missingness at the same time. This is a computational design result,
not a selector result, a probability, a human label, or a psychological claim.

## Unresolved decisions

- Freeze the candidate estimand: edge, membership, or space role.
- Choose a persistence definition and decide whether any scale recipe may enter production.
- Decide how space-field roles are consumed downstream while keeping them separate from group membership.
- Decide whether a future selector may emit singleton candidates, overlapping candidates, or only an ambiguity set.
- Declare a Bayesian prior/likelihood/spatial dependence model before any posterior prototype.
- Declare an ML representation, algorithm, seed, hyperparameters, and independent validation target before any ML diagnostic.
- Define a synthetic holdout and acceptance criteria shared by any future mechanisms.

## External evidence limits

[`d6-bayesian-synthesis.md`](d6-bayesian-synthesis.md) supports Bayesian grouping,
spatial dependence, synthetic calibration, and posterior predictive checks as
methodological possibilities. It does not validate a furniture grouping model,
choose a prior, establish psychological validity, or justify a production
selector. The external truth manifest is a computational generation record only.

**STOP FOR DESIGN REVIEW**

## Membership-level follow-up design

The owner-approved next estimand and fixture-family/seed holdout contract are recorded in [d6-inferred-group-candidate-field-membership-holdout-design.md](d6-inferred-group-candidate-field-membership-holdout-design.md). The machine-readable probe result now carries `membership_estimand` and `synthetic_holdout` metadata. Holdout scoring is `not_run` because generated seed replicas and owner-approved truth targets are not materialized; no recipe winner or numerical threshold is selected.

**STOP FOR DESIGN REVIEW**
