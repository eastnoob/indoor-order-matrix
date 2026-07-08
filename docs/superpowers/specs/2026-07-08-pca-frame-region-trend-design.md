# PCA Frame Region Trend Design

## Goal

Replace inferred region trend evidence that averages raw member orientations with frame evidence derived from affordance geometry. The immediate target is the SVG probe workflow: inferred region polygons and axes should reflect the furniture group footprint, and trend strength should express whether that group has a clear shared two-axis frame.

## Layer Decision

`features/scene_loader.py` remains a neutral adapter. It may expose object geometry, transformed points, and metadata, but it must not decide spatial order.

`features/scene_inference.py` owns this feature. It already creates affordance extents and inferred region candidates, so it is the smallest correct place to compute furniture-group frames from those extents.

`features/scene_evaluator.py` keeps consuming metadata such as `axis-angle`, `secondary-axis-angle`, and `axis-strength`. It should not know whether the axis came from SVG, PCA, or authored BIM data.

## Semantics

Single furniture does not need PCA. It contributes affordance geometry: rectangle corners, authored polygon points, or a bbox fallback.

A furniture group frame is computed from all affordance geometry points in the candidate group. Use deterministic PCA on those points:

- `axis-angle`: primary PCA axis angle in degrees.
- `secondary-axis-angle`: the orthogonal secondary axis.
- `axis-primary-extent`: point-cloud range projected onto the primary axis.
- `axis-secondary-extent`: point-cloud range projected onto the secondary axis.
- `axis-clarity`: `(primary_variance - secondary_variance) / (primary_variance + secondary_variance)`.
- `axis-strength`: for this pass, the same value as `axis-clarity`.
- `axis-basis`: `affordance_point_pca_frame`.

The axis line length in visual QA may use extent multiplied by strength, but metadata must keep extent and strength separate.

## Region Trend

For the current implementation, each inferred region candidate corresponds to one furniture group, so the region trend is the group frame. Later, when one authored/derived region contains multiple furniture groups, region trend should average group frames using four-angle circular averaging so `0/90` and `90/0` are equivalent.

## Non-Goals

This pass does not implement multi-group region frame averaging, polygon boolean union, medial-axis routing, BIM plugins, or matrix score rewrites. It only replaces the current member-orientation mean with affordance point PCA frame metadata.

## Acceptance Tests

- A synthetic horizontal table group and vertical table group both report high `axis-strength`.
- Their `axis-angle` values may differ, but their frame evidence uses the same `axis-basis`.
- Oblique SVG inferred regions still produce non-cardinal axes where geometry is oblique.
- The notebook overlay exposes frame basis, strength, and extents for visual QA.
