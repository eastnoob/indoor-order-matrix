# Group Frame Region Trend Design

## Goal

Separate furniture-group frame inference from region trend inference. A region trend should be the weighted mean of furniture-group frames, not a direct PCA over the whole region candidate geometry.

## Layer Decisions

`features/scene_loader.py` remains a neutral SVG/BIM adapter and does not infer trend.

`features/scene_inference.py` owns derived evidence:

- activity-group frame evidence from affordance point-cloud PCA
- inferred-region trend evidence from one or more activity-group frames
- notebook-friendly geometry and metadata

`features/scene_evaluator.py` consumes metadata. It should not recompute group or region trend.

## Algorithms

### Single Furniture

Single furniture provides deterministic geometry only:

- authored or transformed points when available
- fallback rectangle corners
- neutral `orientation` as local furniture frame evidence

No random sampling is used.

### Furniture Group Frame

For each activity group, collect all member furniture maximum affordance extent rectangle corners and member footprint points. Run closed-form 2D PCA on that point cloud:

- `group-axis-angle`: primary eigenvector angle
- `group-secondary-axis-angle`: primary + 90 degrees
- `group-axis-primary-extent`: projected point-cloud range along the primary axis
- `group-axis-secondary-extent`: projected range along the secondary axis
- `group-axis-clarity`: `(lambda1 - lambda2) / (lambda1 + lambda2)`
- `group-axis-member-alignment`: four-angle consistency of member local frames
- `group-axis-strength`: clarity multiplied by member alignment
- `group-axis-basis`: `affordance_group_pca_frame`

### Region Trend

A region can contain one or more furniture groups. Its trend is a weighted four-angle circular mean of group frames:

```text
C = sum(weight * cos(4 * group_angle))
S = sum(weight * sin(4 * group_angle))
region_angle = atan2(S, C) / 4
region_strength = sqrt(C*C + S*S) / sum(weight)
```

The four-angle mean makes `{0, 90}` equivalent to `{90, 0}`. Use group strength as the default weight. If all weights are zero, fall back to equal weights so the angle remains deterministic while strength stays low.

Region metadata:

- `axis-angle`
- `secondary-axis-angle`
- `axis-strength`
- `axis-basis`: `activity_group_frame_mean`
- `axis-group-count`
- `axis-group-ids`
- `axis-primary-extent`
- `axis-secondary-extent`

When one inferred region contains one activity group, region trend equals that group's frame. This is expected and keeps current SVG fixtures working while preserving the correct hierarchy.

## Visual QA

The SVG inference notebook should draw both axes for each region:

- primary trend axis: solid orange line
- secondary trend axis: dashed orange line
- both lines use axis strength and extents from metadata

## Non-Goals

This pass does not implement automatic subdivision of one semantic region into multiple furniture groups. It uses existing activity groups and adds the correct frame aggregation interface. Future grouping can feed multiple group frames into the same region averaging helper.
