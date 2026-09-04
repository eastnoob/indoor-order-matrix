# Validated MassPatch Cuboid Collection Design

**Date:** 2026-09-08

## Goal

Generate a small, auditable collection of analysis cuboids for one complete
logical object while preserving the source object's plan occupancy, height
intervals, important gaps, and basic visibility behavior.

## Problem

The current generator splits a mesh by factual connectivity and tests at most
one oriented bounding box per component. This is conservative, but it does
not implement the intended substitute: a chair or table should be represented
by a small collection of long cuboids rather than by hundreds of detailed CAD
fragments or one unsafe enclosing box.

The current collection also has no single place that defines how overlapping
patches are queried. A seat and back cuboid may overlap physically, but the
overlap must not be double-counted.

## Design Principles

1. `MassPatch` remains the only physical geometry substitute type.
2. A logical object may own a tuple of `MassPatch` records.
3. The generator works on the complete logical-object mesh, including
   disconnected factual parts such as chair legs.
4. Cuboids are upright: their local X/Y axes may rotate in plan, but analysis Z
   remains the vertical axis.
5. Geometry tolerances are hard acceptance constraints, not perceptual weights.
6. A candidate collection is selected by feasibility first, then minimum patch
   count, then geometric error and triangle complexity.
7. If no simplified collection passes, the exact source geometry remains the
   result.
8. Convex hulls are derived 2D descriptors only. They are not physical
   substitutes and must not replace collection occupancy queries.

## Collection Semantics

For patches `P = {p1, ..., pn}` representing one object:

- plan geometry is `union(project_xy(pi))`;
- occupied height at `(x, y)` is the union of all `vertical_intervals(pi, x, y)`;
- a visibility ray is blocked if at least one `pi` blocks it;
- path overlap uses the union of all patch projections;
- overlap diagnostics report pairwise and total union overlap separately.

The implementation may avoid constructing one permanent 3D Boolean mesh. The
collection query layer can use a 2D Shapely union, interval merging, and
short-circuit ray queries. This keeps the analysis representation small and
avoids making fragile CAD Boolean operations part of every query.

## Candidate Generation

### 1. Normalize the complete logical object

The input remains `MeshGeometry3D`. Its connected components are used as
occupancy seeds and topology facts, but they are not automatically emitted as
the final patch collection. This prevents a multi-part chair from becoming one
patch per CAD fragment.

The analysis frame uses the source analysis plane's horizontal basis when
available. Otherwise, it uses world Z as vertical and a deterministic
horizontal PCA yaw for the object. Z is never tilted by ordinary horizontal
PCA.

### 2. Build an adaptive occupied representation

Voxelize or sample the closed source mesh in the upright object frame. The
pitch is explicit in the generation configuration or derived from the source
linear tolerance. The representation must retain occupied and empty cells in
three dimensions so that seat/back/leg gaps survive candidate fitting.

Open or non-manifold source geometry is not silently filled. It either uses a
surface-aware conservative representation or selects the exact fallback.

### 3. Extract maximal upright cuboids

Repeatedly search the occupied representation for a large rectangular block
whose footprint and height span are internally occupied. Candidate ranking is:

1. maximum newly covered occupied volume;
2. minimum false occupancy introduced near the candidate boundary;
3. longer contiguous spans;
4. deterministic coordinate order.

The candidate is removed from the remaining occupied representation only after
it is accepted by local source comparison. Component-separated gaps are never
bridged merely because their outer bounds overlap.

### 4. Refine the collection

After the initial greedy cover:

- merge adjacent or slightly overlapping cuboids when the union still passes
  all source comparisons;
- split a cuboid along the largest residual empty slab or height mismatch when
  the collection fails validation;
- repeat until the collection is feasible or a deterministic search limit is
  reached.

This is an auditable approximate minimum-cover algorithm. It does not claim a
mathematical global minimum for arbitrary 3D geometry.

## Collection-Level Validation

Add a validator that compares the source mesh with a tuple of candidate
`MassPatch` records. It reuses the existing hard tolerances:

- plan recall;
- plan overreach;
- vertical endpoint error;
- gap preservation;
- occlusion disagreement.

The source and candidate states are computed from collection union semantics:

- occupied plan state is boolean OR;
- height intervals are sorted and merged;
- occlusion is boolean OR;
- area overlap is union area.

Candidate selection is lexicographic:

1. reject any collection that violates a hard tolerance;
2. minimize number of cuboids;
3. minimize plan/height/occlusion error;
4. minimize triangles and vertices;
5. preserve deterministic ordering.

## Public Output

Keep the existing `MassPatchGenerationResult.patches` tuple. A successful
result contains the selected cuboid collection; an uncertain result contains
the exact source components. Add collection-level report fields without
changing the existing `MassPatch` record:

- selected collection method;
- patch count;
- overlap pair count and union-overlap ratio;
- voxel/sample frame and pitch;
- collection validation report;
- fallback reason and uncertainty records.

## Resource Strategy

Use cheap broad-phase checks before detailed geometry:

- per-patch AABB rejection;
- cached plan union per object and analysis plane;
- interval merge only for patches whose plan bounds contain the query point;
- short-circuit ray blocking after the first hit.

The source mesh is read once for generation. Detailed polygon or ray work is
performed only for candidate validation and requested analysis queries.

## Exclusions

- no new convex-hull substitute type;
- no furniture-kind templates;
- no semantic naming inference;
- no perceptual weights;
- no Rhino UI changes;
- no IFC persistence by default;
- no mandatory CoACD or V-HACD dependency;
- no promise of an exact globally minimal cuboid cover.

## Acceptance Criteria

- A simple box becomes one cuboid patch.
- A chair-like object becomes a small collection rather than one enclosing box
  that fills seat/leg gaps.
- Intersecting seat/back boxes are counted once in plan, height, area, and
  visibility queries.
- Hollow and sloped geometry does not silently become a filled or incorrectly
  elevated cuboid collection.
- Disconnected chair parts can be represented by several cuboids under one
  logical source object.
- Exact fallback remains available when approximation is unsafe.
- Existing SVG, BIM, boundary, path, and OCTA tests remain green.
- Live Rhino validation proves source geometry is not modified.
