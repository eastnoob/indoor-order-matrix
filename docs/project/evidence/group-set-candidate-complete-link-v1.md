# Group set candidate complete-link comparison v1

- Date: 2026-10-28
- Status: geometry-only limitation found; no selector approved
- Source: the pinned IFC-derived 666 group-pair observations

## Comparison

The set-level diagnostic now compares two graph interpretations and two
set-level readings:

- connected components: groups are chained when the selected graph contains a
  path between them;
- complete-link: every pair inside the proposed set must be an edge in the
  selected graph.

The complete-link views use maximal cliques. Isolated groups are retained as
singleton diagnostic views so that the source scope remains visible; this does
not assign them membership or strength.

## Result on the real IFC

| Rule | Candidate views | Set sizes |
| --- | ---: | --- |
| nearest-neighbour connected components | 14 | 8×2, 3×3, 3×4 |
| contact connected components | 21 | 8×1, 11×2, 1×3, 1×4 |
| nearest-neighbour complete-link | 23 | 23×2 |
| contact complete-link | 24 | 16×2, 8×1 |

This exposes the current geometry-only limitation:

- connected components can create multi-group sets, but a chain can merge
  groups even when the end groups have no direct relation;
- complete-link prevents that chain, but with the current observations it
  produces only pairs (plus isolated singletons), so it does not express the
  intended multi-group organization well.

No candidate is selected. All views remain diagnostic, with full scope,
relation/source references, `closure_status=not_evaluated`, and no authored
membership, participation, potential, strength, or winner.

## Verification

The updated runner writes 82 plane-local SVG views in
`outputs/design/group_set_candidate_diagnostic/run_20261028T_set_level_v2/`.
All 82 SVG files parse as XML. Focused tests report `2 passed`.

The result does not justify adding a distance threshold or choosing a graph
rule. It indicates that the next evidence discussion should add a second
evidence family, such as arrangement-pattern or cross-group trend similarity,
before attempting a production candidate selector.
