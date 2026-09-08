# Geometry-Faithful MassPatch Design

**Date:** 2026-09-08

## Goal

Make the single `MassPatch` substitute preserve the source geometry that
matters to layout analysis: occupied volume, meaningful empty space, height
intervals, occlusion, and outward-facing triangle normals.

## Problem

The current cuboid collection builder returns one axis-aligned bounding box per
connected source component before it tries occupancy decomposition. That
shortcut turns a connected rectangular ring into a filled box and loses the
opening that is relevant to walking, visibility, and planar spacing. The shared
box factories also use inward winding, so generated proxy meshes display
reversed normals in Rhino.

## Design

1. `MassPatch` remains the only substitute geometry type. Do not add ring,
   hollow, void, convex-hull, or furniture-specific patch classes.
2. For a source whose factual topology is closed and manifold, build an upright
   occupancy grid first, retain both occupied and empty cells, and greedily
   decompose occupied cells into a bounded collection of maximal rectangular
   cuboids. Empty cells are never converted into patches.
3. For open or mixed-topology sources, do not claim closed-solid occupancy.
   Keep the existing componentwise conservative envelope path, with explicit
   uncertainty in the report and provenance. If that path cannot pass plan
   validation, retain exact source components.
   Mixed objects use a component-scale sampling pitch bounded by the parent
   pitch, so small closed parts are not swallowed by a room-scale cell.
4. Validate every simplified closed collection against hard source evidence:
   plan recall, plan overreach, vertical interval endpoints, and occlusion
   disagreement. A candidate that fills a source opening must be rejected.
5. Among accepted cuboid collections, prefer fewer patches and lower geometry
   complexity. An accepted closed-source cuboid collection is the proxy result
   even when its triangle count exceeds the original low-poly source mesh:
   exact source components are a fidelity fallback, not a competing cuboid
   candidate.
6. All shared upright cuboid factories must use outward winding. The signed
   tetrahedral volume of a unit generated cuboid must be positive.
7. Do not add perceptual weights, semantic special cases, new dependencies, or
   Rhino/BIM/UI behavior in this change.

## Output Contract

`generate_mass_patches()` returns:

- `selected_collection_method="cuboid_collection"` for a validated closed
  occupancy decomposition;
- `selected_collection_method="open_envelope_collection"` only for an
  uncertain componentwise envelope that passes plan-envelope validation;
- `selected_collection_method="componentwise"` when no simplification is safe.

Every selected simplified patch retains validation configuration, validation
result, source id, and method provenance. A failed simplification never
replaces the exact source geometry.
Rejected collection candidates remain in `collection_report` with their hard
rejection reason.

## Acceptance Criteria

- A rectangular ring is represented by multiple thin cuboids with its central
  empty area preserved; it is never accepted as one filled AABB.
- A chair with separated legs does not gain a filled floor-level bridge.
- An open mesh can still receive a conservative component envelope, but the
  result is marked `open_envelope_uncertain` and does not claim closed-solid
  height or occlusion truth.
- A mixed-topology source derives topology per component and never lets a
  single aggregate flag silently certify all components.
- Generated cuboids have outward-facing winding and positive signed volume.
- Existing deterministic generation, exact fallback, source immutability, and
  collection-validation tests remain green.

## Grill Me Self-Check

- **Could the ring still become a filled box?** Only if the occupancy
  decomposition or hard overreach validation is bypassed; the production
  closed-source path now does neither.
- **Could the fix break open sources?** No. Open/mixed sources retain the
  uncertainty branch and exact fallback.
- **Is a second substitute type needed?** No. Empty space is evidence in the
  occupancy grid, not a semantic object.
- **Could the normal fix be visual-only?** No. The shared factory geometry is
  changed and a signed-volume regression test proves the mesh orientation.
- **Is the scope too large?** No. It changes only the shared MassPatch
  generation path, its tests, and its design records.
