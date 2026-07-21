# Column Grid Local Region Shape Design

## Status

This is a narrow supplement to the column-grid relation specs. It fixes the
geometry handoff between inferred activity regions and `C_local_profile`.

## Problem

`ActivityRegion` inference already produces two different geometry records:

- `points`: the inferred region shape in its selected local frame, usually an
  oriented rectangle or regularized hull.
- `rect`: the world-axis-aligned bounding box kept as a stable fallback for
  older path, occupancy, and adapter code.

`C_local_profile` currently uses `region["rect"]` for seed-bay overlap and
bay grammar. That makes oblique or irregular inferred regions behave like
large horizontal/vertical bounding boxes when relating to column bays.

## Design Rule

`C_local_profile` must consume the previous region-inference layer instead of
re-inferring region geometry.

For each region:

1. Use `region["points"]` as the primary region shape when it has at least
   three usable points.
2. Fall back to `region["rect"]` only when no polygon shape is available.
3. Continue reading region trend from `metadata["axis-angle"]`.
4. Keep `C_global` unchanged because it already compares region frame with
   column-grid frame.
5. Keep `inter_region` gap-path geometry unchanged in this pass because it is
   a separate path-model issue.

## Required Behavior

### Seed Bay Lookup

`_seed_bay_ids()` should overlap the region shape with each bay. If the region
shape is a polygon, overlap should use polygon-vs-bay area. If no bay overlaps,
nearest-bay fallback may still use the region shape bounds.

### Bay Grammar

`_bay_grammar()` should report:

- overlap area between the region shape and each included bay;
- region area from the polygon when present;
- center-in-bay based on the shape bounds center for now.

The current `region_center_in_bay` field remains a simple local-context proxy;
it is not a full polygon-in-bay classification.

### Visual QA

The column-grid demo overlay should draw inferred regions from `points` first
and draw `rect` only as a fallback. Furniture geometry, inferred region shape,
region trend, and column grid remain the only visual layers.

## Non-Goals

- Do not change region trend inference.
- Do not change `C_global`.
- Do not rewrite `inter_region` gap paths to polygon routing.
- Do not add Shapely or another geometry dependency.
- Do not change SVG parsing semantics.

## Acceptance Checks

- A synthetic oblique `ActivityRegion` whose `rect` overlaps two bays but whose
  `points` polygon overlaps one bay should seed only the polygon-overlapped bay.
- The same synthetic region should report bay grammar overlap area from the
  polygon, not the world bbox.
- The notebook visual overlay should show oblique inferred regions as polygons,
  not horizontal/vertical world bboxes.
- Existing column-grid tests should still pass.

## Grill-Me Self-Check

- If the region layer already owns shape and trend, should the column-grid layer
  compute a new local bbox? No. It should consume the region's `points` and
  `axis-angle`.
- Is this only a visualization bug? No. Visualization used `rect`, but
  `C_local_profile` also used `rect` for seed-bay and grammar geometry.
- Should gap paths change now? No. Gap paths are explicitly documented as a
  bbox-axis proxy and need a separate path geometry spec.
- Is a new dependency justified? No. Existing `Polygon`, `Rect`, and
  `_polygon_rect_overlap_area` cover the needed polygon-vs-rect cases.

