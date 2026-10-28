# Group attribution candidate and readout draft v1

- Date: 2026-10-28
- Status: draft for owner review; not a production recipe or strength approval
- Scope: smallest rule set that can unblock the next design discussion without
  inventing a scalar intensity

## What this draft is for

The current IFC packages expose observations but do not define how an
organization view is proposed or how an AuthoredGroup receives a relation
readout. This draft fixes the record shape and keeps the unresolved choices
visible. It does not create hard groups, a winner, a probability, a potential,
or a strength formula.

## Fixed record shape

Every organization view records:

```text
P = {
  recipe,
  scope,
  seed_or_seed_set,
  proposal_extent,
  closure_status,
  proposal_evidence
}
```

For every eligible AuthoredGroup in the frozen scope, the corresponding field
record keeps:

```text
E(group, view, query) = {
  proposal_exposure,
  boundary_gap,
  contact,
  positive_area_overlap,
  status,
  reason,
  source_refs,
  dependency_refs
}
```

The three geometry channels remain separate. Missing or invalid observations
retain their states; they are never replaced by zero. `proposal_extent` is an
observation range, not a hard membership boundary. Groups outside it but inside
the frozen scope remain visible as boundary tension or unresolved evidence.

## Current diagnostic view (not the target candidate model)

The existing seed relation profile is the only view that can be produced from
the current IFC without inventing a rule:

- every eligible AuthoredGroup may serve as a seed;
- the view contains the complete frozen group scope;
- relations are shown in raw/normalized distance order, with contact and
  overlap status;
- `proposal_extent = not_evaluated`;
- `closure_status = not_evaluated`;
- no participation, membership, support, potential, strength, or winner is
  produced.

This is a traceable organization view for inspection. It is not yet a
candidate proposal algorithm.

This seed-to-group display must not be read as pairwise grouping. A sample
with one red seed and one highlighted neighbor only visualizes one raw
relation used by a diagnostic recipe; it does not answer whether two groups
belong together. The intended candidate is a multi-group organization view.
Pairwise gap, contact, and overlap observations are inputs to that set-level
proposal and remain separate evidence channels.

## Choices that must be approved before a real proposal recipe

To turn a seed into a proposal extent, one rule is needed. The available
choices are different interpretations of the same geometry observations:

1. nearest-neighbour expansion;
2. contact-only expansion;
3. a declared distance threshold;
4. a declared top-k expansion;
5. a parallel set of these recipes with no single winner.

The choice also needs a closure rule: stop after one expansion, expand until no
new eligible group is admitted, or leave closure incomplete under a budget.
No choice is selected in this draft because each one changes the meaning of a
candidate and may change the later readout comparison.

## Readout boundary

Until a proposal rule and a defensible observation-to-readout mapping are
approved, the readout is the channel vector plus state and provenance. It is
not a scalar participation value and cannot be used to compute `M`.

The trend package is not an independent readout source: it describes each group
from the same IFC and currently has no group-to-group similarity channel. The
AuthoredGroup declarations are input facts, not validation labels.

## Required owner decision

Choose whether to:

- keep seed views diagnostic only and first define a multi-group candidate-set
  proposal rule; or
- add a new evidence package before defining proposal extent.

If defining proposal extent now, choose one of nearest-neighbour,
contact-only, threshold, top-k, or parallel recipes, and state whether closure
is evaluated or remains `not_evaluated` in the first run. Until then, the stage
2 numeric comparison item remains blocked and scalar `M` remains unresolved.

