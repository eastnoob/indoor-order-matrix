# Group Attribution Strength Design Experiment Protocol

- Date: 2026-10-25
- Status: design-only protocol executed on 2026-10-26; no production scoring rule selected; see [protocol results](evidence/grouping-strength-design-protocol-results.md)
- Scope: close the input, attribution-field, and group-profile questions before real-scene review or implementation

## Purpose

This protocol tests whether a candidate representation can express evidence-based, non-probabilistic attribution of eligible authored furniture groups to overlapping organization candidates, and whether a group-level profile makes strong cores, weak members, and missing evidence visible.

Keep four outputs distinct:

1. Candidate proposal: which organization hypotheses a declared recipe proposes.
2. Attribution field `E(g, k, s)`: channel-level evidence for authored group `g` in candidate `k` at scale/query `s`.
3. Attribution readout `M_k(g, s)`: a non-probabilistic scalar only where the evidence-to-scalar mapping is justified; otherwise retain channel-specific records and status.
4. Group profile: a summary of the candidate's member readouts and evidence coverage.

The proposal extent is not membership truth. The frozen eligible scope defines the field domain; a group outside a proposal extent but inside that scope still receives an attribution record. Scope-external entities are not assigned zero. Group-to-grid, group-to-wall, and group-to-group fit are downstream consumers and are outside this experiment.

## Boundaries

- Reuse Stage A/D6 fixtures and diagnostics first. Add only cases that do not already test the invariant below.
- Treat the proposed input rules in `grouping-goal-alignment.md` as the baseline under test, not as a production contract already accepted by implementation.
- Do not resume synthetic-label fitting, select a probability model, choose production evidence weights, add a production API, or connect a UI.
- Do not edit historical Stage A/D6 artifacts to make them appear to cover this target.
- Use the existing evidence/status vocabulary. Missing, conflicting, invalid, conditional, and incomplete evidence must retain its reason and dependency; none is converted to numeric zero.

## Frozen test scope and input contract

Each case declares the eligible authored-group inventory, source/object identities, candidate proposal extent, recipe, scale/query, evidence-family availability, and search-completeness state before attribution is evaluated. Candidate and field results must be replayable from those frozen inputs.

Test the following proposed eligibility and identity behavior across `AuthoredGroup`, `analysis_scene_view`, and `group_self_description`:

- A source-traceable explicit furniture-group marker qualifies a node. Do not infer eligibility solely because every referenced object happens to be furniture.
- An explicitly marked empty group creates no node but remains visible in the input audit with an empty-group reason.
- Repeated references to the same exact object identity count once in membership and evidence; retain the duplicate-reference diagnostic.
- Dangling references remain in source/audit records. Affected evidence is marked unavailable, partial, or invalid according to the actual failure; it is never silently dropped or treated as negative evidence.
- A physical object shared by two eligible authored groups remains a member of both. Preserve the shared-source dependency and count its physical observation once when aggregating evidence.
- An unmarked generic group whose members are all furniture is excluded from the eligible inventory and reported as such.

If the three current consumers disagree, record the smallest reproducing case and the disagreement. The experiment does not silently repair production code or choose a compatibility rule.

## Diagnostic matrix

| ID | Case family | Required invariant / observation | Decision informed |
|---|---|---|---|
| I1 | Explicit marker vs. generic all-furniture group | Eligibility follows the declared source marker; the inventory and exclusion reason are auditable. | Is there one consistent authored-node qualification rule? |
| I2 | Empty and duplicate references | Empty nodes do not enter the field; duplicate object identities do not multiply evidence. Raw input anomalies remain visible. | Which input facts affect node identity versus evidence quality? |
| I3 | Dangling references | The authored fact remains; only affected evidence is unavailable/partial/invalid with a reason. | Which failures invalidate a node, a channel, or only a readout? |
| I4 | Shared physical object across nodes | Both authored memberships remain; shared geometry/source evidence is dependency-deduplicated. | How should shared membership affect coverage and aggregation? |
| C1 | Driver and modifier perturbations | Replay the same fixture with the driver removed/changed and with each modifier added/removed. Record candidate changes separately from attribution changes. | One driver plus modifiers, joint closure, or parallel recipes? |
| C2 | Explicit mutual exclusion | A resolved declaration with exact valid endpoints vetoes joint participation in that candidate, even if geometry is absent. It does not zero unrelated candidates or all evidence for either endpoint. | What endpoint identity and scope are required for a hard veto? |
| C3 | Invalid or unresolved exclusion endpoint | A dangling, ambiguous, or out-of-scope endpoint cannot silently act as a hard veto; preserve the declaration and its status. | Which endpoint failures remain unresolved diagnostics? |
| S1 | Unknown / conditional evidence | Keep the raw status and reason distinct from a numeric value. A conditional source does not become established evidence merely through aggregation. | Which statuses permit a scalar readout, and under what explanation? |
| S2 | Incomplete candidate search | Mark search completeness separately from evidence status. Do not call a candidate recipe-maximal or the result exhaustive when the search was truncated. | What closure claims are allowed for each recipe? |
| F1 | Full field vs. proposal extent | For each frozen candidate and scale/query, emit one field record for every eligible in-scope authored group, including groups outside that proposal's extent. Report extent-external evidence as boundary tension, not forced zero membership. | Can proposal and attribution domains remain separate? |
| F2 | Scope-external entity | Do not create a zero-valued field cell for an entity outside the frozen eligible scope; report it as out of scope/uncovered with provenance. | How is scope change distinguished from weak attribution? |
| D1 | Proposal/attribution dependence | Compare same-source attribution, attribution after removing proposal evidence, and independent/held-out attribution where available. Keep candidate discovery exposure explicit in every result. | Does proposal reuse inflate its own attribution readout? |
| P1 | Strong core plus weak bridge | Use the existing RGB/weak-bridge construction. Show member-level readouts and at least mean, median, and weakest-member summaries; a single mean must not hide the weak bridge. | Which compact profile distinguishes a coherent core from a weak attachment? |
| P2 | Missing pair/channel evidence | Preserve observed values and separately report expected/observed coverage by evidence family and source dependency. Missing comparisons do not become zero. | Is coverage adequate for interpreting the profile? |
| P3 | Singleton and low-coverage candidate | Report member readout and coverage status without inventing within-group pair evidence or treating the absence of comparisons as perfect support. | What does a profile mean when its candidate has too few members/evidence? |
| P4 | Candidate-wide comparison | Compare original groups, a nested/overlapping merge, and a broad candidate under the same declared evidence. Retain member distribution and statuses; do not normalize memberships to sum to one across candidates. | Does the profile express strong cores, weak merges, and overlap? |

For the weak-bridge fixture, the previously replayed arithmetic is a diagnostic reference only: four core members read `0.5125` each and the bridge reads `0.15`; the resulting profile has mean `0.44`, median `0.5125`, and minimum `0.15`. Recompute from the frozen fixture rather than copying these values into a production rule. The missing-evidence case must lower reported coverage without lowering observed values by implicit zero-fill.

## Required result record

For every case, record:

- fixture and source identities, frozen scope, candidate recipe/extent, and scale/query;
- the complete eligible `candidate × authored group × scale/query` field domain, including explicit status/reason for cells with no scalar;
- channel observations, support/counterevidence polarity, status, source references, and shared-source dependencies;
- proposal evidence and attribution evidence, including overlap and any ablation/holdout boundary;
- candidate closure/search completeness, veto resolution, uncovered nodes, and extent-external boundary-tension records;
- member-level attribution readouts when justified, plus group mean, median, weakest-member readout, valid-member count, and per-family expected/observed coverage;
- a decision label for each question: `resolved`, `provisionally supported`, or `unresolved`, with the evidence and remaining ambiguity.

Mean, median, and minimum are comparison readouts for the experiment, not selected production operators. If evidence families lack a justified shared scale, report their profiles separately and leave a single combined `M` unresolved. Never substitute zero for a missing member readout when computing a profile; report the denominator and valid-member coverage.

## Gate to finish this experiment

The design-diagnostic gate is complete when:

1. Every matrix family is represented by a deterministic fixture or an explicitly documented reason it cannot yet be tested.
2. The three input consumers agree on the proposed qualification/identity rules, or the precise unresolved contract difference is recorded for owner decision.
3. Each frozen candidate has a complete field record over all eligible in-scope authored groups; every absent value has a status and reason.
4. Veto, unknown/conditional evidence, incomplete search, shared-source dependence, and proposal leakage satisfy the invariants above or remain explicitly unresolved rather than being coerced into a passing score.
5. The profile comparisons distinguish the constructed strong-core, weak-bridge, and missing-coverage cases without claiming real-world calibration.
6. Repeated replay yields the same logical result; any non-determinism or failed case is retained in the report.
7. The report states which design decisions are supported and which remain open. If the fixtures cannot discriminate options, retain the alternatives; do not force a winner.

Passing this gate permits preparation for an independent real-scene blind interpretability review. It does not validate a real-world scale, select a production recipe, or authorize implementation. If no suitable independent scene is available, leave that review open. Measure search cost against Stage A's 37-node baseline only after recipe semantics are stable, and report bounded searches as incomplete.

## Execution outputs and handoff

Execution should reuse current D6/Stage A artifacts, add only missing design fixtures, and produce a concise replayable evidence report with the case inventory, observed results, failures, hashes, and unresolved decisions. Keep runners and fixtures design-only under `scripts/design/group_level/`; keep the report and compact machine-readable result under `docs/project/evidence/`. Run only the focused checks for the changed design fixtures and consumers; do not present that result as full-suite or real-scene acceptance.

After this protocol is executed, revise or replace the successor design spec before production work. The original Stage A–D successor spec remains useful for candidate identity, overlap, provenance, and field structure, but its probabilistic membership-strength gate does not define this non-probabilistic target. Write an implementation plan only after the revised strength contract is reviewed and accepted.

Execution artifacts:

- [Field-slice report and result](evidence/group-attribution-field-slice.md), [JSON](evidence/group-attribution-field-slice.json), and [runner](../../scripts/design/group_level/run_group_attribution_field_slice.py).
- [Follow-up protocol result](evidence/grouping-strength-design-protocol-results.md), [JSON](evidence/group-attribution-protocol-followup.json), and [fixture/runner](../../scripts/design/group_level/group_attribution_protocol_followup_fixture.json).

## References

- [Current goal alignment and stage status](grouping-goal-alignment.md)
- [Original Stage A–D successor design](D:/PROJECTS/understandOtherPackage/order_analyzer_group_inference_stage_b/docs/superpowers/specs/2026-10-22-group-clustering-evidence-field-design.md)
- [Original Stage A plan](D:/PROJECTS/understandOtherPackage/order_analyzer_group_inference_stage_b/docs/superpowers/plans/2026-10-22-group-clustering-stage-a.md)
