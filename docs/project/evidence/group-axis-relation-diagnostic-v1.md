# Group axis relation diagnostic v1

Date: 2026-10-29

This is a read-only diagnostic of the user-confirmed axis relation layer. It
reuses the retained IFC-derived axis envelopes and same-plane group geometry;
it does not re-extract IFC geometry or create simulated furniture.

## Result

- Source: pinned IFC SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`.
- Analysis plane: `ifc-world-plan`, metres.
- Scope: 37 authored furniture groups and 666 unordered group pairs.
- Pair channels: undirected angle gap, `cos²(δ)` direction similarity,
  clarity similarity, and `min(ca, cb)` clarity support.
- All four channels were `computed` for all 666 pairs in this retained IFC.
- Direction-similarity and clarity-support matrices are 37×37, symmetric, and
  have a not-applicable diagonal.
- The neutral plan uses group colors as identifiers only. It draws no axis,
  relation edge, threshold, membership, or aggregate direction.

## Artifacts

The reproducible output is
`outputs/design/group_axis_relation_diagnostic/run_20261029T131057Z/`.

- `relations.json` contains endpoint provenance and all pair channels.
- `matrices.json` contains values, channel states, and pair-to-cell mapping.
- `group_plan.svg` is the neutral IFC-derived plane view.
- `matrices/direction_similarity.svg` and
  `matrices/clarity_support.svg` are inspectable matrix views.
- `manifest.json` maps stable group IDs and pair IDs to artifacts and cells.
- `report.json` records coverage, symmetry, source identity, and the fact that
  no IFC extraction was rerun.

The reviewed pair channels are now active additive outputs of the
`group-axis-potential` package. Package evaluation preserves all source
envelopes and original channels, then appends four independently traceable
pair channels for each unordered group pair. The package still does not create
a combined relation score, use pair readings as extra votes in the global
resultant, or infer grouping/membership.

Verification: `PYTHONPATH=.` with the pinned IFC-derived envelopes produced
37 source envelopes and `666 * 4` pair outputs; the focused package, relation,
and output-contract tests passed (`24 passed`).
