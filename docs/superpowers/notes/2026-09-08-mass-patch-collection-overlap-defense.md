# MassPatch Collection Overlap Note

**Date:** 2026-09-08

## Implementation Task Anchor

The next implementation target is a **low-count upright cuboid collection**
for one complete logical object. The source object is sampled into a bounded
3D occupied-cell representation, candidate cuboids are extracted from that
representation, and a deterministic greedy cover is refined by merge/split
checks. The result is accepted only when collection-level union queries stay
within hard geometric tolerances; otherwise the exact source geometry remains
the substitute.

The important distinction is:

- `MassPatch` is the only physical substitute type;
- several patches may belong to one logical object;
- the collection is queried as a union, not as a sum of independent boxes;
- a convex hull is never used as a physical substitute;
- the goal is few boxes with preserved gaps, not merely fewer triangles.

The first implementation should deliberately avoid furniture-specific rules,
perceptual weights, and a mandatory external decomposition package. The
algorithm must work from geometry and explicit tolerances, and must expose a
deterministic exact fallback when the simplified collection is unsafe.

This is the working decision for the cuboid-collection implementation.

One logical object may be represented by several `MassPatch` records. These
records are one substitute collection, not several independent semantic
objects and not a second convex-hull substitute.

The collection is allowed to contain overlapping cuboids. Overlap is not an
error by itself: a seat box and a back box may share a small physical volume.
The invariant is that spatial facts are evaluated as a union, never as a
simple sum of overlapping members.

## Query Semantics

- **Plan occupancy:** union all projected patch polygons.
- **Area or volume:** measure the union; do not add member areas or volumes.
- **Height:** collect all vertical intervals and merge overlapping or touching
  intervals before comparison.
- **Visibility:** a ray is blocked when any member patch blocks it; duplicate
  hits do not increase the blocking result.
- **Path conflict:** intersect the path with the union of the patches.
- **Complexity:** keep patch count, triangle count, and overlap diagnostics as
  separate geometry facts.

The external boundary of the union removes internal shared faces. This is the
correct interpretation for a chair whose seat and back boxes slightly
interpenetrate: the shared volume is retained once, while the internal
interface is not treated as an additional boundary.

## Current Coverage

The repository already protects several central 2D consumers with Shapely
unions:

- `features/geometry_views.py::component_shape` unions projected components.
- `features/scene_evaluator.py::_record_shapely_geometry` unions component
  polygons and preserves holes.
- `features/scene_evaluator.py::_records_shapely_union` deduplicates records
  before unioning them.
- `features/scene_evaluator.py::_blocker_union_overlap_area` measures blocker
  union overlap rather than summed overlap.

The protection is incomplete for a future multi-box object substitute:

- `derive_boundary_evidence` still emits one evidence row per patch.
- `vertical_intervals_at` accepts one patch at a time and has no collection
  interval merge.
- `_record_rect_overlap_area` can sum overlapping component contributions.
- `MassPatchGenerationResult` stores a tuple of patches but does not yet
  validate or report collection-level overlap.

## Implementation Boundary

The next implementation must add one shared collection-query layer. It should
not add a persistent `ConvexHullPatch`. A convex hull remains a derived 2D
shape/display descriptor only; physical occupancy, height, path, and
visibility queries use the MassPatch collection.
