# Oriented Region Trend Design

## Goal

Make inferred activity regions and their trend evidence distinguish aligned, chaotic, and oblique furniture layouts without breaking the SVG/BIM separation.

## Current Failure

The current SVG ID-only probes load rotated furniture as records whose centers move, but whose rectangle geometry stays axis-aligned and whose `points` are empty. The inference layer then builds region candidates with an axis-aligned bounding-box union and stores `points=[]`. The evaluator already knows how to use `metadata["axis-angle"]` or region polygon PCA, but the inferred region records do not provide either, so trend overlays fall back to `bbox_long_axis`.

This is why three visually different layouts produce mostly horizontal or vertical region boxes and trend lines.

## Layer Decisions

`features/scene_loader.py` remains an adapter. It should convert SVG transforms into neutral scene geometry:

- object `orientation`
- transformed shape `points` for rectangles and polygons
- an axis-aligned `rect` only as the bbox of those neutral points

`features/scene_inference.py` owns derived region geometry and trend evidence. It should infer region candidate polygons from neutral object geometry and write axis evidence into candidate metadata.

`features/scene_evaluator.py` should keep consuming record geometry and metadata. It should not learn SVG-specific rules. The existing `_record_axis_descriptor()` path is acceptable once inferred regions provide `axis-angle` or polygon points.

## Region Geometry Algorithm

For each semantic region/group:

1. Collect member furniture records and their affordance extents.
2. Prefer point geometry from each member record. If a record has no points, use its `rect` corners.
3. Estimate a region frame angle from member orientations. Use axis-orientation statistics where `0` and `180` are equivalent.
4. Project all member geometry points into that local frame.
5. Build the minimum axis-aligned envelope in the local frame.
6. Expand that local envelope by the existing spacing-margin logic, converted back into the region frame.
7. Transform the local envelope corners back to scene coordinates and store them as `points`.
8. Store `rect` as the bbox of those points so existing axis-aligned path and occupancy code still works.

This is an oriented-envelope proxy, not polygon boolean union. That is intentional for this pass.

## Trend Algorithm

Each inferred region candidate gets trend metadata from member furniture:

- `axis-angle`: axis-circular mean of directional evidence.
- `axis-strength`: resultant length in `[0, 1]`, where high means members share a common axis and low means chaotic directions.
- `axis-basis`: `member_orientation_axis_mean`.
- `secondary-axis-angle`: primary + 90 degrees.
- `axis-member-count`: count of objects used as direction evidence.

Weights are simple: elongated rectangles contribute by aspect ratio, near-square or circular records contribute weakly or not at all. This keeps round coffee tables from dominating a group trend.

## Explicit Authoring Priority

If a future BIM/SVG input provides explicit region `points` or `axis-angle`, those authored values should remain primary. This pass only improves inferred region candidates created from object groups.

## Visual QA

The `test/svg_id_inference_demo.ipynb` notebook should show:

- red activity group boxes
- blue inferred region candidate polygons or polygon-derived bbox fill
- purple inferred gap paths
- orange trend axes
- trend strength in the rendered title or data attributes

The three probe SVGs should visually differ:

- baseline: strong horizontal/vertical local trends matching regular furniture.
- chaotic: lower trend strength than baseline for affected regions.
- oblique: non-cardinal trend axes where furniture is rotated or arranged obliquely.

## Acceptance Tests

Automated tests should prove:

- SVG loader exports orientation and transformed points for rotated rects.
- oblique SVG inferred regions contain non-empty points and axis metadata.
- oblique center lounge trend is not merely the horizontal bbox axis.
- chaotic probe has lower north-table trend strength than baseline.
- notebook source renders `region-trend` with strength evidence.

## Non-Goals

This pass does not implement polygon boolean union, medial-axis routing, navmesh paths, BIM plugins, or calibrated affordance simulation. Existing axis-aligned gap path logic can continue to use candidate bboxes until path inference is upgraded separately.
