# Group attribution readout comparison preflight v1

- Date: 2026-10-28
- Status: completed as an unresolved gate; no numeric comparison authorized
- Scope: stage 2 readout-use audit on the pinned IFC
- Source: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`

## Purpose

Before choosing a non-probability strength readout, check whether the current
evidence can be used in three distinct ways:

1. use the currently admitted evidence to propose an organization view and read
   its relation;
2. propose the view first, then temporarily remove the proposing evidence and
   read the relation from what remains;
3. read the relation from a genuinely independent or held-out source.

These are comparison arrangements, not new field types, group types, or
algorithms. The comparison is meant to detect whether one evidence source is
being used to propose a relation and then to confirm itself.

## Evidence available in the current IFC run

| Evidence | What it currently contains | Can propose a candidate? | Can read attribution? | Independent/held-out? |
| --- | --- | --- | --- | --- |
| Geometry relation package | Pairwise `boundary_gap`, `contact`, and `positive_area_overlap` observations for 666 group pairs; member-pair facts are `audit_only`; group aggregation is `deferred`. | Not yet: no approved proposal recipe or closure rule. | No: no participation mapping, attribution field, or readout is implemented. | No: it is the only current inter-group relation source. |
| Trend alignment package v2 | One envelope per furniture group with `overall_group_axis` and `layout_axis`; member-level channels are suppressed audit data. | Not yet: it does not propose candidates or compare groups. | No: it describes each group and does not provide group-to-group similarity or attribution. | No: it is derived from the same IFC furniture geometry and is not a held-out label. |
| AuthoredGroup declarations | Source-bound input facts identifying 37 furniture groups and 95 members. | They define the input scope only. | They are not an attribution answer or validation label. | No: treating them as ground truth would violate the project boundary. |
| Seed relation profiles | A view of each authored group against the complete scope, with distance ordering only. | Candidate proposal is explicitly `not_evaluated`. | Participation and strength are explicitly `null`. | No: it is a re-expression of the geometry package. |

## Result

The current source and packages do **not** provide the three ingredients needed
for a numeric comparison:

- no approved candidate proposal recipe or search closure;
- no approved mapping from an observation to participation or attribution;
- no independent or held-out attribution evidence in the pinned IFC.

The trend package is a possible future evidence family, but it is not currently
independent and it does not yet expose cross-group similarity. The authored
group declarations cannot be used as a truth label because the project treats
them as source facts rather than ground-truth grouping.

Therefore this gate is recorded as **unresolved by evidence availability**. No
candidate, membership, participation, potential, strength, winner, or scalar
`M` is produced. The existing geometry and trend packages remain descriptive
envelopes only.

## Spatial traceability

No new comparison plot is generated because no valid comparison readout exists
to plot. The underlying observations remain traceable on the same pinned-IFC
plane through:

- geometry relation package: `outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/`;
- trend alignment package v2: `outputs/design/group_trend_alignment_field_ifc/run_20261027T232920Z/`;
- seed relation profiles: `outputs/design/group_seed_candidate_experiment/run_20261027T_seed_profile_v1/`.

All three use the diagnostic `ifc-world-plan` and retain the source fingerprint
`1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`.

## Consequence for the plan

The stage 2 comparison item remains unchecked as a **numeric comparison**. Its
required preflight is complete, with the prescribed unresolved conclusion:
there is no defensible readout mapping or independent evidence yet, so scalar
`M` decisions stop here. The next work is not to invent a strength formula; it
is to discuss whether to approve a candidate proposal/readout rule or add a
new evidence package, one package at a time, using the existing envelope
contract.

