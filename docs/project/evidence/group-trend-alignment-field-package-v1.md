# Group trend alignment evidence package v1

## Boundary

This is the second evidence package in the group-attribution field. It wraps
the existing typed `Analysis` trend descriptors for each eligible authored
`furniture_group`. It does not infer membership, select a candidate, calculate
potential, calculate a final strength, choose a winner, or combine channels.

The working contract was approved by the user on 2026-10-27. The four
channels remain parallel:

- `overall_group_axis` — area-weighted total-geometry PCA axis;
- `member_frame` — four-angle member orientation consensus;
- `member_axis` — two-angle member orientation consensus; and
- `layout_axis` — between-member centroid PCA axis.

The existing `strength` and `coherence` values are retained as geometric
concentration/consensus diagnostics. They are not potential-1 strength, a
group potential, a support value, or a calibrated scalar.

## Envelope contract

`features/group_trend_alignment_field.py` emits one `FieldResultEnvelope` per
eligible authored group using `group-trend-alignment-envelopes/v1`. Each
envelope preserves the four channel observations separately, typed member
bindings, source IDs, provenance, descriptor status, excluded-member
diagnostics, geometry status, and cache identity. Undefined direction remains
inside a computed descriptor; it is not silently converted to missing data.

The package uses the shared `FieldQuery`/`FieldResultEnvelope` contract and
the same analysis plane as the scene. It does not add a second field kernel or
a new public API.

## Current IFC diagnostic run

The design-only runner
`scripts/design/group_level/run_group_trend_alignment_field_ifc.py` reads only
the pinned IFC and extracts the 37 exact `IfcGroup.ObjectType ==
"furniture_group"` groups and their 95 direct members. Body and typed
`Analysis` representations are extracted once, then one description and one
package build are performed. The IFC was unchanged during the run.

Run output:

`outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/`

| Item | Result |
| --- | ---: |
| eligible authored groups | 37 |
| trend envelopes | 37 |
| channels per envelope | 4 |
| computed / partial / invalid / unavailable | 37 / 0 / 0 / 0 |
| SVG visualizations | 148 |
| SVG files parsed successfully | 148 |

The source is IFC4, project GlobalId `2uGd6yom9GZe5$z7LfbGW0`, source unit
millimetres, analysis unit metres, and current diagnostic plane
`ifc-world-plan`. Source bytes and SHA-256 are recorded in
`source_manifest.json` and match before and after extraction:

```text
408618044 bytes
1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077
```

`envelopes.json` contains the four separate descriptor channels and all source
bindings. `view_manifest.json` maps every group/channel pair to one real IFC
plane SVG. Each SVG draws the projected furniture polygons and one channel's
direction when defined; undefined directions are labeled rather than replaced
with an invented arrow.

## What remains undecided

The current run proves that the approved structure can carry the existing
trend facts for this IFC. It does not decide channel fusion, potential-1
similarity, group-level averaging, weights, thresholds, candidate closure,
winner selection, nested evidence packages, or a non-probability strength
formula. Those remain later review gates.

This IFC run also does not cover partial, invalid, or unavailable typed
Analysis members; those states remain represented by the package contract but
are not present in this source. The full stage-2 comparison, blind review, and
recipe decision gates remain open.
