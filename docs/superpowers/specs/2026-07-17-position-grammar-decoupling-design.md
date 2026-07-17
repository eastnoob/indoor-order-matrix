# Position Grammar Decoupling Design

## Goal

Replace the current rotation-driven position grammar with a complete
position-only grammar module. The work may be implemented in small steps, but
the accepted delivery is not a partial "v1": it must fully replace the current
public `P_position_fit` path.

## Hard Constraints

- `P_position_fit` must not use furniture rotation, region trend, or column-grid
  alignment as its scoring basis.
- The public position score reads only furniture-group position proxies:
  group center, group proxy rect, optional authored position slots, and optional
  authored position frame.
- Rotation consistency and position-to-rotation alignment are separate metrics.
  They may reuse evidence for comparison, but they must not feed back into
  `P_position_fit`.
- There must not be two public position systems running in parallel. The new
  position-only grammar replaces the current rotation-driven scope frame.
- The feature must be independently disableable. A disabled position grammar
  must mark `P_position_fit` / `P_position_confidence` as disabled without
  affecting region inference, furniture-group inference, rotation, trend,
  paths, boundaries, or column-grid rows.

## Public Interface

Use the smallest switch that works:

```python
evaluate_scene(scene, *, position_grammar_enabled=True)
```

Default `True` preserves current callers. `False` disables only public position
grammar rows and focused position grammar overlay evidence.

Disabled behavior is explicit: keep `P_position_fit` and
`P_position_confidence` rows with `status="disabled"` and no position evidence.
This avoids breaking downstream row consumers while making it clear that the
module was not adopted for that evaluation.

The returned matrix should also keep a top-level `region_position_grammar`
payload with `status="disabled"` and empty `items`, so overlay and adapter
consumers can branch on one stable shape.

## Data Boundaries

`features.position_grammar` owns:

- position frame candidates;
- position grammar candidates;
- residuals, slots, fit, confidence;
- disabled/not-available position grammar payloads.

`features.scene_evaluator` owns:

- calling the position grammar module;
- adding or omitting public matrix rows based on the feature switch;
- drawing focused position evidence from the returned payload.

It must not contain the grammar algorithm.

`features.scene_inference` owns:

- neutral `FurnitureGroup` records and proxy geometry.

It must not know how position grammar is scored.

SVG/BIM adapters own:

- source object geometry;
- authored role/group/region metadata;
- optional authored position frame or authored slots.

They must not compute the matrix score.

## Algorithm

For each activity-region or room position scope:

1. Collect furniture-group centers and proxy rects.
2. Build position-only frame candidates:
   - authored position frame, if present;
   - candidate angles from pairwise center directions;
   - PCA angle from furniture-group centers;
   - global `0/90` fallback;
   - deduplicate axial angles so equivalent candidates are tested once.
3. For each frame, test grammar candidates:
   - `grid`: stable row/column slots with reasonable slot count;
   - `line`: stable one-axis ordering;
   - `pair`: exactly two stable matched members;
   - `cluster`: compact group around one centroid slot when no stronger
     low-complexity grammar explains the points;
   - `unstructured`: fallback evidence when no order is explainable.
4. Select by:
   - lowest normalized residual / highest fit;
   - then lower grammar complexity;
   - then authored frame preference if scores are effectively tied.

The selected evidence still exposes slots and residuals for visualization.

Frame candidates must not read `group-axis-angle`, `group-axis-basis`, region
trend axes, or column-grid relation outputs. Those values are allowed only in
separate rotation/alignment metrics.

All tolerances must be derived from the observed position proxies, such as
median group size, median nearest-neighbor spacing, or scope size. Avoid a
single hand-tuned angle or distance threshold that only fits the current SVG
fixtures.

## Grammar Details

`grid`:

- Cluster projected `u` and `v` coordinates into row/column slot centers.
- Reject when the slot count is implausibly larger than the member count.
- Residuals connect each group center to its nearest row/column slot.

`line`:

- Keep each member's projected `u`.
- Collapse `v` to the line center.
- Score both equal spacing along `u` and residual distance to the line.

`pair`:

- Applies only to two members.
- Slots are symmetric around the scope center in the tested frame.

`cluster`:

- Uses one centroid slot or a compact local centroid model.
- It is not a replacement for `grid` or `line`; it wins only when it explains
  residuals better than `unstructured` and no lower-residual structured grammar
  wins.

`unstructured`:

- Always available.
- Returns low fit and low confidence with diagnostic residuals to the scope
  centroid, so visual output still explains why the position layer did not find
  a useful rule.

## Required Behavior

- Baseline table grid: position fit high, grammar `grid`.
- Oblique but orderly table grid: position fit high, grammar `grid`, frame based
  on position layout, not furniture rotation.
- Chaotic rotations with unchanged grid positions: position fit high and
  rotation order low.
- Position-only perturbation with unchanged rotations: position fit drops and
  rotation order does not explain it away.
- Non-grid arrangements can score through `line`, `pair`, or `cluster` without
  being forced into `grid`.
- Truly unstructured arrangements return low-confidence `unstructured`
  evidence rather than pretending to be a bad grid.

If rotation-order or position-rotation-alignment rows are not yet implemented
when this work starts, this project must at least expose separate evidence
payloads or disabled rows for them. It must not smuggle either concept into
`P_position_fit`.

## Grill-Me Self-Check

- If changing only furniture rotation changes `P_position_fit`, is position
  decoupled? No. That must be a regression test.
- If the algorithm always returns `grid`, is it robust to irregular layouts? No.
  `line`, `pair`, `cluster`, and `unstructured` must compete.
- If the feature switch disables other rows, is the module cleanly isolated? No.
  Only position grammar rows and focused position evidence should change.
- If the evaluator contains frame-search math, is the boundary clean? No. The
  algorithm belongs in `features.position_grammar`.
- If old rotation-driven frame code remains as a public fallback, are there two
  systems? Yes. It must be removed or demoted to non-public debug evidence.

## Acceptance

- New tests prove position fit is stable when only furniture rotation changes.
- New tests prove position fit drops when only furniture-group positions shift.
  These tests should compare samples against their own controls instead of
  relying on one fixed global threshold.
- New tests cover a non-grid layout that selects `line`, `pair`, or `cluster`.
- New tests cover `position_grammar_enabled=False`.
- New tests prove disabled position grammar leaves non-position row counts and
  key non-position scores unchanged.
- Focused notebook visualizes selected grammar slots/residuals for the same SVG
  fixtures and shows no rotation-driven long residuals for grid-preserving
  chaotic rotations.
- Existing MVP tests still pass.
