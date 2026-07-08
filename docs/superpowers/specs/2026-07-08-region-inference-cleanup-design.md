# Region Inference Cleanup Design

## Goal

Fix three small issues in automatic region inference:

- decorative objects should not anchor inferred regions by default
- regular eight-point hulls should still be allowed to collapse to rectangles
- trend visualization should not make clear furniture orientation look weak by shortening axes with strength

## Scope

This pass only changes the inference layer and SVG diagnostic notebook. It does not change SVG loading, BIM adapters, path routing, or matrix scoring rows.

## Decorative Objects

Objects with roles such as `plant`, `decor`, and `decoration` remain in the neutral scene. They are excluded from automatic activity-group and inferred-region construction unless explicitly opted in with:

```text
region-shape-anchor = true
```

This prevents decorative objects from expanding region hulls, trend frames, and activity-group extents.

## Hull Simplification

The hull used for shape selection is still a regularized convex hull. This pass changes two conservative rules:

- near-collinear cleanup uses `15°` tolerance instead of `8°`
- an eight-vertex hull whose edges mostly align with the organization frame still uses an oriented rectangle

This keeps visually regular regions from becoming convex hulls just because of small corner offsets.

## Trend Semantics

The organization trend remains based on furniture-group frames. Metadata separates:

- `axis-member-alignment`: member frame agreement
- `axis-shape-clarity`: PCA/geometric axis clarity
- `axis-trend-strength`: combined trend evidence

Existing `axis-strength` is kept as an alias for compatibility. The notebook visual length uses geometric extent with a stable floor and records `axis-visual-length-basis`, so low strength changes opacity rather than making axes almost disappear.

## Tests

- Plant records do not expand inferred region candidates by default.
- `region-shape-anchor=true` makes a plant participate.
- Baseline `center_lounge` uses `oriented_rectangle` after regularized eight-point handling.
- Notebook source uses `axis-visual-length-basis` and no longer multiplies axis length directly by `strength`.
