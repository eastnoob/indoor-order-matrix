# Group candidate recipe diagnostic v1

- Date: 2026-10-28
- Status: geometry-only diagnostic; no recipe selected
- Source: pinned IFC-derived seed and geometry artifacts

## Purpose

This run compares two deliberately small one-step proposal rules using the
same 37 real furniture groups and 666 real group-pair observations already
produced from the pinned IFC. It checks whether the candidate record can keep a
proposal extent, complete scope exposure, source references, and a plane-local
visualization without turning a proposal into membership or strength.

## Parallel recipes

1. `nearest-neighbour-one-step`: include every group tied at the seed's
   minimum normalized boundary gap.
2. `contact-only-one-step`: include every group whose seed relation has one or
   more computed contact observations.

Both recipes use `closure_status=not_evaluated`. They are parallel diagnostic
views only; neither is a production recipe and no winner is chosen.

## Real IFC coverage

| Recipe | Seed views | Proposal extent sizes |
| --- | ---: | --- |
| nearest-neighbour-one-step | 37 | 34 seeds with 2 groups; 3 seeds with 3 groups |
| contact-only-one-step | 37 | 8 seeds with the seed only; 26 seeds with 2 groups; 3 seeds with 3 groups |

Every view retains all 37 scope groups. Each scope member keeps normalized
boundary-gap observations, contact count, positive-area-overlap count, status,
source references, dependency references, and whether it is in the proposed
extent or scope-only. The output explicitly contains no participation,
membership, support, potential, strength, or winner value.

## Visualization and validation

The run writes 74 plane-local SVG views and a manifest mapping every view to its
recipe, seed, proposal extent, and source fingerprint. Red marks the seed,
yellow marks the proposed extent, and grey marks the remaining scope. All 74
SVG files parse as XML. The source fingerprint and `ifc-world-plan` match the
retained IFC-derived artifacts.

Artifacts:

- `outputs/design/group_candidate_recipe_diagnostic/run_20261028T_parallel_v1/candidate_recipe_diagnostic.json`
- `outputs/design/group_candidate_recipe_diagnostic/run_20261028T_parallel_v1/manifest.json`
- `outputs/design/group_candidate_recipe_diagnostic/run_20261028T_parallel_v1/views/`

Verification:

```text
pixi run pytest test/test_group_candidate_recipe_diagnostic.py -q
2 passed

pixi run python -m scripts.design.group_level.run_group_candidate_recipe_diagnostic
candidate recipe diagnostic: .../run_20261028T_parallel_v1

37 seeds × 2 recipes = 74 views; 74/74 SVG XML parses successfully.
```

This result only makes the two proposal shapes inspectable. It does not show
that either rule is perceptually or operationally correct, and it does not
unblock scalar readouts or strength `M`.

## Visual audit

Two representative views were rasterized from the same SVGs for inspection:

- nearest-neighbour seed `0003` highlights the red seed plus one yellow nearest
  proposal group;
- contact-only seed `0003` highlights only the red seed because that seed has no
  computed contact relation.

The red/yellow/grey distinction is readable, the complete scope remains
visible, and the contact-only seed-only case is represented without inventing a
neighbor. This is a visualization audit only; it does not favor either recipe.
