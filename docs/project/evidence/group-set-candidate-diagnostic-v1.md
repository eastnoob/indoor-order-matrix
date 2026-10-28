# Group set candidate diagnostic v1

- Date: 2026-10-28
- Status: set-level structural diagnostic; no production selector chosen
- Source: pinned IFC-derived seed profile and projected group geometry

## What this tests

The diagnostic converts the existing group-pair observations into multi-group
candidate views. A candidate is a proposed set of authored furniture-group
identities; it is not authored membership and it is not a final partition.
Pairwise gap/contact observations remain evidence references inside the proposal.

Two parameter-free graph constructions are kept in parallel:

1. `nearest-neighbour-components`: connect each group to all groups tied at its
   minimum normalized boundary gap, then report undirected connected components.
2. `contact-components`: connect groups with one or more computed contact
   observations, then report undirected connected components.

The connected-component step is deliberately a chaining baseline. It is useful
for exposing set shapes, but it is not approved as the final candidate rule.
No participation, authored membership, potential, strength, or winner is
generated. Closure remains `not_evaluated`.

## Real IFC result

| Diagnostic graph | Candidate sets | Set sizes |
| --- | ---: | --- |
| nearest-neighbour-components | 14 | 8×2 groups, 3×3 groups, 3×4 groups |
| contact-components | 21 | 8×1 groups, 11×2 groups, 1×3 group, 1×4 group |

Each recipe covers all 37 real furniture groups exactly once in its component
views. The source contains 666 group pairs. Every candidate records its full
37-group scope, proposal extent, graph rule, relation IDs, source IDs and
`closure_status=not_evaluated`.

## Visualization and validation

The runner writes one plane-local SVG per candidate set: 14 nearest-neighbour
views and 21 contact views, for 35 total. Yellow marks the proposed multi-group
set and grey shows the remaining complete scope. The source fingerprint and
`ifc-world-plan` match the retained IFC-derived artifacts; all 35 SVG files
parse as XML.

Artifacts:

- `outputs/design/group_set_candidate_diagnostic/run_20261028T_set_level_v1/candidate_sets.json`
- `outputs/design/group_set_candidate_diagnostic/run_20261028T_set_level_v1/manifest.json`
- `outputs/design/group_set_candidate_diagnostic/run_20261028T_set_level_v1/views/`

Verification:

```text
pixi run pytest test/test_group_set_candidate_diagnostic.py -q
2 passed

pixi run python -m scripts.design.group_level.run_group_set_candidate_diagnostic
set candidate diagnostic: .../run_20261028T_set_level_v1

14 + 21 = 35 candidate views; 35/35 SVG XML parses successfully.
```

Representative multi-group views were rasterized for visual inspection. They
show that the output is now a set-level organization view rather than a red
seed plus one neighbor. This confirms the representation direction only; it
does not establish that either graph construction is perceptually or
operationally correct.
