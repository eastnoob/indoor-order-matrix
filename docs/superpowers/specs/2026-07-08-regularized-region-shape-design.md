# Regularized Region Shape Design

## Goal

Improve inferred activity-region geometry so regular furniture groups keep a clean rectangle while irregular groups use a regularized convex hull. Region trend remains the organization frame derived from furniture-group frames. Region shape frame is added only as diagnostic evidence.

## Problem

Current inferred region polygons use an oriented bounding envelope. This is stable for rectangular repeated groups, but it over-wraps sparse or irregular groups because one rectangle swallows empty space between affordance extents. The screenshot issue is this over-wrapping, not SVG line pickup.

## Shape Inputs

The region shape is inferred from the neutral analysis avatars:

- furniture affordance extent rectangles
- authored transformed points only as geometry evidence when present
- boundary cues already included in the candidate rect list

The SVG loader remains only an adapter. It provides neutral records and metadata; matrix inference decides the region shape from those records.

## Shape Algorithm

For each inferred candidate:

1. Collect affordance extent corner points and available transformed member points.
2. Compute a convex hull from those points.
3. Simplify the hull by removing near-collinear vertices and very short edges.
4. Compute edge-direction complexity against the current organization frame.
5. Choose the visual region polygon:
   - use an oriented rectangle when the simplified hull has four or fewer vertices
   - use an oriented rectangle for five to seven vertices when most edges align with the two organization-frame axes
   - use a regularized convex hull for eight or more simplified vertices, or for directionally complex hulls

Area ratio is recorded as diagnostic metadata only. It is not the main decision rule.

## Frame Semantics

Organization frame:

- existing region trend
- computed from activity-group frames with four-angle circular averaging
- displayed as the orange primary and secondary axes

Shape frame:

- computed from the final region polygon using PCA
- recorded as metadata
- not used to overwrite trend

Frame delta:

- absolute frame difference between organization frame and shape frame
- stored for diagnosing when geometry and furniture organization disagree

## Non-Goals

This pass does not implement concave hulls, polygon-aware path routing, BIM plugins, or matrix score rewrites. Gap paths continue to use candidate bboxes in this pass.

## Tests

- Regular four-corner groups keep `region-shape-basis = oriented_rectangle`.
- Irregular groups with many simplified hull vertices use `region-shape-basis = regularized_convex_hull`.
- Shape-frame metadata is present and does not replace `axis-basis = activity_group_frame_mean`.
- The SVG notebook visual overlay exposes the shape basis and still draws organization trend axes.
