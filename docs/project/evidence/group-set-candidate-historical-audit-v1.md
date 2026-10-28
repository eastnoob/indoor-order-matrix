# Group set-candidate historical audit v1

- Date: 2026-10-28
- Status: design direction confirmed; no production selector chosen

## Conclusion

The early design separates two layers:

1. compute pairwise group relations as raw evidence;
2. use the complete relation graph to propose a candidate containing multiple
   authored furniture groups.

An edge is not authored membership, and a two-node edge must not be presented
as the grouping answer. Candidate records are independent inferred views that
may overlap, remain incomplete, or be ambiguous, and should retain member
group IDs, support/exclusion evidence, algorithm, parameters, and status.

## Historical implementations and limits

- `connected-components` is a chaining baseline and diagnostic only.
- `complete-link` / maximum within-candidate gap are possible set-level
  comparison methods, but their thresholds and final semantics are not frozen.
- `features/position_grammar.py::region_position_grammar_evidence` already
  evaluates multi-group scopes and emits grammar evidence, but it is evidence,
  not a furniture-group candidate selector, and depends on authored region
  labels.
- `scene_inference.inferred_region_candidates` produces activity-region
  candidates from object/affordance/boundary cues; it is a different layer and
  cannot substitute for furniture-group candidates.
- `features/analyzer.py::_score_inter` is an old continuous orientation/phase
  heuristic, not a candidate generator and not a production attribution rule.

## Consequence for the current work

The seed + nearest-neighbour/contact one-step runner remains retained as an
off-target structural diagnostic. It must not be used to select a recipe or to
claim pairwise grouping. The next diagnostic should use a set-level candidate
contract and treat the existing pairwise geometry envelopes as input evidence.
