# Member Frame Trend Ground Truth Design

## Problem

Region trend currently lets point-cloud PCA influence `axis-angle` and
`axis-strength`. That makes rotated furniture groups vulnerable to axis-aligned
bbox and affordance geometry. `SVG_chaoticsvg.svg` `east_work` is the visible
case: the table is strongly rotated, but the trend frame stays almost horizontal.

## Principle

Trend and shape are separate evidence types.

- Trend describes shared member orientation.
- Shape describes geometric envelope, hull, occupancy, and path spacing.

PCA remains useful for shape diagnostics and geometric fallback, but it is not
the trend ground truth when member frames exist.

## Algorithm

1. Single furniture trend frame:
   - read authored orientation / BIM local frame / SVG-derived orientation;
   - weight by directional clarity, currently rectangle aspect minus one;
   - circular furniture such as chairs can have zero trend weight.
2. Activity-group trend frame:
   - use `_member_frame_consensus()` as the primary trend source;
   - use four-angle averaging so 0 and 90 degree rotations are equivalent;
   - set trend strength to the consensus concentration when directional support exists.
3. Activity-group geometric diagnostics:
   - still compute PCA over affordance geometry;
   - expose this as geometry/shape evidence, not as trend ground truth.
4. Region trend frame:
   - average activity-group trend frames as before;
   - keep existing shape polygon, gap path, and region extent logic unchanged.

## Safety

- Do not change inferred region polygons.
- Do not change affordance extents.
- Do not change inferred gap paths.
- Do not add angle thresholds.
- Do not penalize trend strength merely because there are few members.

## Acceptance

- A one-table synthetic group has strong trend strength.
- `SVG_chaoticsvg.svg` `east_work` trend follows the rotated table frame instead
  of the bbox/PCA frame.
- Chaotic `north_tables` remains weaker than aligned `north_tables`.
- Full pytest passes and the SVG inference notebook is re-executed for visual QA.
