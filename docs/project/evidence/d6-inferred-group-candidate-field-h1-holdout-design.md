# D6 H1 holdout computational truth contract

状态：`design_only_stop_for_design_review`。本记录只物化 holdout contract、seed replica 记录和 evaluation-side computational truth；不运行 holdout recovery scoring。

## Scope and boundary

H1 的实验单位是完整的 fixture-family replica。development 使用 seeds `101, 202`；holdout 固定使用 `303, 404`。禁止按 member 或 pair 拆分。candidate probe 只能接收 [holdout fixture manifest](../../../scripts/design/group_level/inferred_group_candidate_field_h1_holdout_fixtures.json)，不得读取 [computational truth manifest](../../../scripts/design/group_level/inferred_group_candidate_field_h1_computational_truth.json)。truth 只在未来 evaluation side 比较 emitted candidates 时读取。

truth 是预注册生成器产生的 evaluation-side computational structure：candidate member sets、hard mutual-exclusion veto pairs、singleton/unassigned diagnostics 和状态传播目标。它不是人工标签、心理真值、真实场景准确率，也不会写回 authored membership、public API 或 production selector。

## Materialized contract

- Eight families each have two development and two holdout seed records.
- Seed material is `d6-h1/holdout-fixture/v1|{family}|{split}|{seed}`; each record stores its SHA-256 digest.
- `relative_gap_rank`、`local_persistence_window`、`space_profile_rank` and the four aggregation diagnostics remain comparison factors only. H1 does not choose scale, aggregation, threshold, or selector.
- Truth member sets are family-level computational targets and are copied to each deterministic seed replica without treating members or pairs as independent samples.
- Hard vetoes are categorical precedence constraints with source references; ordinary type/geometry disagreement remains soft evidence.
- `computed`、`partial`、`invalid`、`not_available` are separate status targets. Missing or invalid geometry is never imputed.

## Family target index

| Family | Truth candidate member sets | Hard veto pairs | Singleton/unassigned diagnostic | Status targets |
|---|---|---|---|---|
| gap-jump | `[['G1', 'G2', 'G3'], ['G4', 'G5']]` | `[]` | `[]` | computed `['G1', 'G2', 'G3', 'G4', 'G5']`; partial `[]`; invalid `[]`; not_available `[]` |
| minority-mixed | `[['M1', 'M2', 'M3']]` | `[]` | `['M4']` | computed `['M1', 'M2', 'M3', 'M4']`; partial `[]`; invalid `[]`; not_available `[]` |
| geometry-conflict | `[['CUBE', 'TALL'], ['TALL', 'ROUNDISH']]` | `[]` | `[]` | computed `['CUBE', 'TALL', 'ROUNDISH']`; partial `[]`; invalid `[]`; not_available `[]` |
| space-conflict | `[['S1', 'S3']]` | `[{'pair': ['S1', 'S2'], 'source_ref': 'S1.member.factual_properties.mutual_exclusion', 'target_ref': 'S2'}]` | `['S2']` | computed `['S1', 'S2', 'S3']`; partial `[]`; invalid `[]`; not_available `[]` |
| bridge-chain | `[['A', 'B'], ['B', 'C']]` | `[]` | `['D']` | computed `['A', 'B', 'C', 'D']`; partial `[]`; invalid `[]`; not_available `[]` |
| overlapping-candidates | `[['O1', 'O2'], ['O2', 'O3']]` | `[]` | `[]` | computed `['O1', 'O2', 'O3']`; partial `[]`; invalid `[]`; not_available `[]` |
| missing-invalid | `[]` | `[]` | `['VALID', 'PARTIAL', 'INVALID', 'MISSING_GEOMETRY']` | computed `['VALID']`; partial `['PARTIAL']`; invalid `['INVALID']`; not_available `['MISSING_GEOMETRY']` |
| context-perturbation | `[['P1', 'P2']]` | `[]` | `[]` | computed `['P1', 'P2']`; partial `[]`; invalid `[]`; not_available `[]` |

## Invariance contract

For every split, translation, common rotation with frame update, positive unit scaling, and ID/traversal reorder must preserve the canonical relation signature, canonical candidate member identity, hard-veto membership, categorical evidence statuses, and deterministic ordering. ID renaming requires source-reference remapping before comparison. The context-perturbation check preserves authored node eligibility but may change context and space-role references. Missing-invalid keeps unavailable geometry unavailable, invalid geometry invalid, and partial reasons intact.

## Not run and owner decisions still open

- Holdout recovery scoring: `not_run`; no precision/recall/Jaccard result is claimed.
- No numerical acceptance threshold, recipe winner, scale recipe, aggregation recipe, singleton consumption policy, or production selector is frozen.
- Owner must decide whether any future evaluation consumes singleton diagnostics as a report-only state or as an ambiguity set.
- Owner must approve the evaluation metric bundle and any threshold in a new design review; this H1 contract does not select one.
- Owner must separately specify Bayesian prior/likelihood/spatial dependence/calibration and ML representation/algorithm/hyperparameters/validation target before B1/M1 work.
- Owner must decide how future space-role evidence is reported while remaining separate from furniture membership.

**STOP FOR DESIGN REVIEW**
