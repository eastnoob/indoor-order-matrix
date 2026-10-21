# Group Attribution Strength Design Diagnostic

- Date: 2026-10-25
- Status: diagnostic complete; design gate **not passed**
- Scope: input identity, candidate/attribution boundary, statuses, and group-profile coverage; design-only

## Finding

The earlier Stage A/D6 work is reusable evidence for candidate proposal generation, overlap, veto precedence, provenance, invariance, and categorical geometry status. It does **not** test the requested per-authored-group attribution field or group profile. No production strength rule or probability interpretation is supported by this diagnostic.

The immediate blocker is the input unit contract: the three current consumer paths disagree on eligibility and identity. A minimal runtime reproduction used a generic all-furniture group, two explicit furniture groups sharing `left_table`, and one empty explicit furniture group. `analysis_scene_view` assigned `left_table` to the generic group and `right_table` to the first explicit group; `describe_group_relations` excluded the generic group, kept both explicit memberships, and emitted the empty explicit group. This matches the source behavior in [`neutral_scene_views.py`](../../../features/neutral_scene_views.py#L1050) and [`group_self_description.py`](../../../features/group_self_description.py#L196).

There is also a contract-level mismatch. `AuthoredGroup` accepts repeated and unresolved member references; the separate canonical layout contract rejects duplicate references and dangling group members. The group self-description path preserves dangling members as invalid evidence, while `analysis_scene_view` reduces member-to-group identity to one first-seen group. The legacy dictionary path cannot represent an authored empty group or an explicit dangling membership. See [`scene_contract.py`](../../../features/scene_contract.py#L727), [`canonical_layout_contract.py`](../../../features/canonical_layout_contract.py#L110), and [`group_self_description.py`](../../../features/group_self_description.py#L78).

## Reproducibility and checks

- Replayed `run_inferred_group_candidate_field_probe.py` twice under Pixi against the existing eight-family fixture. Both runs produced byte-identical JSON (SHA-256 `d0096c9236a183bf5147c6a3db2a72fdf7f9eb2f8317ced7e7d4a39f648ddbc3`). The current fixture SHA-256 is `6199c764aaf28c999b10194deaed33b92314c4f448c3b091af9234b342d5944a`.
- The replay passed its ten existing design assertions: candidate view remains deferred, aggregation recipes remain parallel, veto/source references are retained, partial/invalid/not-available stay categorical, invariance and context checks pass, and the status/provenance regressions pass.
- Focused current-tree tests passed: `206 passed` across `test_group_self_description.py`, `test_scene_contract.py`, and `test_neutral_scene_analysis_regression.py`.
- The older D6 markdown record stores fixture SHA-256 `b4aaeb588fe6ebbbc3033f1bd93b48d1696a7be931c12aaa79488cc89ab4dc2a`, which differs from the current replay input. Treat the replay above as reproducible for the current fixture bytes; the older record's exact input lineage remains unresolved. Historical D6 artifacts were left untouched.
- The sibling Stage A report supports candidate-proposal diagnostics (13 proposal cases, 35 breakpoint views, 61 relations, 45 eligible nodes, plus a bounded 37-node cost case). It is historical evidence only: that sibling checkout is dirty and its Stage A runner was not rerun here. It does not establish attribution strength.

Commands run:

```text
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_probe.py --fixtures scripts/design/group_level/inferred_group_candidate_field_fixtures.json --output %TEMP%/group-attribution-d6-replay.json
pixi run pytest -q test/test_group_self_description.py test/test_scene_contract.py test/test_neutral_scene_analysis_regression.py
```

## Diagnostic matrix

| ID | Result | Evidence and remaining gap |
|---|---|---|
| I1 explicit marker vs generic group | **Unresolved** | Runtime reproduction confirms `analysis_scene_view` promotes a generic all-furniture group, while `describe_group_relations` only includes exact `furniture_group` roles. There is no common eligibility inventory/audit result. |
| I2 empty and duplicate references | **Unresolved** | The view produces no empty node or empty-group audit; group self-description includes an empty explicit group. `AuthoredGroup` accepts duplicate refs and group geometry iterates raw refs, so duplicate evidence can be counted repeatedly. The canonical layout contract rejects duplicates; no common duplicate diagnostic exists. |
| I3 dangling references | **Unresolved** | Group self-description retains unresolved refs as invalid members; the analysis view's membership mapping does not expose a corresponding unresolved-member audit; canonical validation rejects dangling references. |
| I4 shared physical member | **Unresolved** | Group self-description retains both explicit memberships and reports a shared-member dependency. The analysis view uses `setdefault`, so it silently keeps the first group. Dependency-aware single-count aggregation is not implemented. |
| C1 driver/modifier perturbations | **Unresolved** | D6 and Stage A compare proposal recipes/cases, but no replay removes or changes one driver and independently toggles each modifier while separating proposal changes from attribution changes. |
| C2 resolved mutual exclusion | **Provisionally supported** | Stage A and D6 preserve an exact valid-endpoint veto when geometry is unavailable and retain its source reference. They test candidate-level veto behavior, not the full attribution-field invariant for unrelated candidates and endpoint evidence. |
| C3 invalid exclusion endpoints | **Unresolved** | No fixture covers dangling, ambiguous, or out-of-scope veto endpoints and their non-veto status propagation. |
| S1 unknown/conditional attribution | **Unresolved** | D6 preserves partial, invalid, and unavailable geometry states. No membership-attribution fixture checks `unknown` or `conditional`, their explanations, or scalar-readout eligibility. Field status behavior elsewhere in the application is only an analogy. |
| S2 incomplete search | **Unresolved** | Stage A documents bounded search and a 37-node cost case. No candidate result exposes search completeness separately from evidence status, so bounded results cannot be audited through the target contract. |
| F1 complete field vs proposal extent | **Unresolved** | Existing artifacts emit candidate member sets and relation evidence, not a record for every frozen eligible group for every candidate and scale/query. No `candidate × authored group × scale/query` field exists. |
| F2 scope-external entity | **Unresolved** | Candidate-scope exclusion is represented in Stage A, but there is no field record marking an external entity out-of-scope/uncovered without assigning zero. |
| D1 proposal/attribution dependence | **Unresolved** | Stage A's same-data, node-holdout, source-block, and external-ideal pattern checks are useful proposal-leakage analogues. They do not compare same-source attribution with proposal-evidence ablation and independent/held-out attribution. |
| P1 strong core / weak bridge | **Unresolved** | Candidate bridge-chain fixtures test topology, not member attribution readouts. The protocol's `0.5125 × 4` plus `0.15` arithmetic recomputes to mean `0.44`, median `0.5125`, and minimum `0.15`, but no frozen source fixture for that RGB/weak-bridge vector was found in the current D6/Stage A artifacts. |
| P2 missing pair/channel coverage | **Unresolved** | Existing status fixtures preserve missing/invalid states, but no attribution profile reports expected/observed pair or channel denominators or shared-source coverage. |
| P3 singleton/low coverage | **Unresolved** | Singleton candidates exist as proposal diagnostics; there is no singleton member readout or low-coverage profile semantics. |
| P4 original/merged/broad candidates | **Unresolved** | Overlap and nesting are represented in candidate proposals. No member-level profile compares original, nested/overlapping merge, and broad candidates under the same attribution evidence. |

## Gate and next design work

The design gate remains open. No matrix family is fully resolved; only candidate-level exclusion precedence is provisionally supported. The minimum next work is a revised design spec that resolves the input unit/identity rules, then specifies the field domain and the profile's coverage denominator. A design-only attribution fixture/runner must follow those decisions. Keep the numerical aggregation choices open until such a fixture can compare them without zero-filling missing members or reusing proposal evidence as independent support.

The Stage A–D probability-strength contract remains outside this target. A later spec should preserve its reusable proposal/provenance/status work while replacing its probability gate with the non-probabilistic attribution contract. Real-scene blind review and search-cost benchmarking remain later gates.

## Evidence references

- Current goal boundary: [`grouping-goal-alignment.md`](../grouping-goal-alignment.md)
- Executed protocol: [`grouping-strength-design-experiment-protocol.md`](../grouping-strength-design-experiment-protocol.md)
- D6 replay runner and fixture: [`run_inferred_group_candidate_field_probe.py`](../../../scripts/design/group_level/run_inferred_group_candidate_field_probe.py), [`inferred_group_candidate_field_fixtures.json`](../../../scripts/design/group_level/inferred_group_candidate_field_fixtures.json)
- Historical current-tree D6 report: [`d6-inferred-group-candidate-field-experiment.md`](d6-inferred-group-candidate-field-experiment.md)
- Historical Stage A report and decision in dirty sibling checkout: [`candidate report`](../../../../order_analyzer_group_inference_stage_b/docs/project/evidence/group-clustering-stage-a-candidate-report.md), [`decision`](../../../../order_analyzer_group_inference_stage_b/docs/project/evidence/group-clustering-stage-a-decision.md)
