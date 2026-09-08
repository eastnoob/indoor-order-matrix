# Budgeted MassPatch Proxy Design

**Date:** 2026-09-11

## Goal

Make MassPatch generation return compact, auditable analysis proxies for high-face-count BIM/Rhino/IFC-style meshes without falling back to copied display geometry by default.

## Design

1. This is a backend rule, not a Rhino rule. Every adapter still feeds `MeshGeometry3D`; the generator decides from topology, size, and budgets only.
2. `MassPatch` remains the only mass substitute. Do not add convex-hull, ring, tube, Rhino, or furniture-specific substitute classes.
3. Exact source geometry is an audit baseline and final emergency fallback, not the preferred analysis output for detailed CAD meshes.
4. Component sampling is budgeted. The pitch may become finer than the parent pitch, but never so fine that one thin decorative detail forces a dense voxel solve for an entire component.
5. Open or parent-uncertain logical objects may select conservative cuboid envelopes with explicit uncertainty. They must not claim closed-solid height or occlusion truth.
6. Closed, manifold sources still keep hard evidence checks for plan recall, plan overreach, vertical interval endpoints, and occlusion disagreement. A candidate that fills a confirmed source opening must be rejected.
7. Over-budget simplification must finish deterministically and report uncertainty instead of hanging or silently returning copied mesh triangles.

## Acceptance Criteria

- A closed rectangular frame remains a few rectangular bars and keeps the center empty.
- A simple chair with separate legs keeps its floor-level gap.
- An open-top box can select a conservative envelope and reports `open_envelope_uncertain`.
- A parent-open logical object with closed child components can return compact cuboid/envelope patches instead of exact source mesh copies.
- High-face-count live Rhino extraction can be prepared for Rhino visualization without unbounded solving.
- All modified project-owned functions have English-first docstrings and intent comments for non-obvious geometry decisions.

## Grill Me Self-Check

- **Is this a hidden convex-hull pass?** No. AABB/OBB can bound sampling or simple components, but confirmed holes remain evidence that blocks filled proxies.
- **Does uncertainty become a fake score?** No. It is provenance and evidence quality, not a perceptual weight.
- **Can it lose useful thin details?** It may simplify visual detail, by design. It must preserve layout-relevant occupancy, height intervals, and confirmed open space.
- **Is Rhino special-cased?** No. Rhino only exposed the high-face-count open-parent case; the rule lives in the backend.
