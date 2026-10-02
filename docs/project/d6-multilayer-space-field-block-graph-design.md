# D6 Future Design: Multi-Layer Space Field, Blocks, and Graphs

**Status:** future design record; not a production contract and not an implementation authorization.

## Motivation

The current architecture already separates furniture groups, activity-region candidates, free-space gap paths, and graph evidence. It does not yet specify a single multi-layer description in which derived empty-space blocks are first-class spatial artifacts alongside furniture-derived regions. This record preserves that direction without changing the current B1 conditional membership estimand.

## Design decision

The analyzer will eventually expose a **heterogeneous spatial organization graph** built from several derived layers. It is not one undifferentiated graph and it does not replace the existing `region_internal` and `inter_region` network scopes.

### Layers

1. **Source/geometry layer**
   - authored furniture-group nodes;
   - physical mass and authored affordance projections;
   - walls, openings, levels, and analysis-domain support.

2. **Field layer**
   - continuous or sampled free-space evidence;
   - clearance/distance, occupancy, connectivity, bottleneck, and boundary-openness observations;
   - sampling representation is an analysis accelerator, not the semantic unit.

3. **Block layer**
   - connected or structurally coherent free-space blocks;
   - furniture-derived activity-region candidates;
   - singleton, overlapping, ambiguous, and unassigned blocks remain representable;
   - a free-space block may receive a provisional role such as corridor-like or activity-space-like, but role labels are evidence summaries, not authored facts.

4. **Graph layer**
   - typed nodes from furniture groups, furniture-region candidates, free-space blocks, and optional entrances/openings;
   - typed edges for adjacency, separation, containment, overlap, boundary crossing, clearance compatibility, visibility, and route connectivity;
   - edge types remain separate and are not collapsed into one scalar strength.

5. **Narrative/description layer**
   - summaries of how furniture blocks, empty-space blocks, boundaries, and paths organize one another;
   - objective evidence only; no psychological interpretation or perceptual weight.

## Space field resolution

Resolution is not a fixed project-wide distance and is not a semantic threshold such as “1.8 m”. The preferred representation is exact or vector geometry plus a multi-resolution sampling accelerator.

For a declared analysis domain, a future experiment will compare at least three scene-relative resolutions. A resolution is acceptable only when the target summaries are stable across the next finer level:

- free-space component identity;
- bottleneck locations and widths;
- gap-path connectivity;
- block area/centroid summaries;
- typed graph adjacency;
- provisional space-role evidence.

The selected operational resolution, if one is ever needed, is the coarsest level that satisfies the predeclared stability criteria. If summaries change materially across levels, the result is `unstable` or `sensitivity_required`, not silently rounded to one answer.

Grid/voxel spacing and body/route width are separate parameters. The former controls numerical resolution; the latter controls a declared clearance query. Neither is a psychological threshold.

## Block semantics

An empty-space block is not a furniture group and does not enter furniture membership. It can nevertheless be a first-class node in the multi-layer graph. Corridor-like and activity-space-like descriptions are competing evidence summaries derived from geometry, connectivity, persistence of width, bottlenecks, boundary openness, and context. A fixed width alone cannot assign the role.

The first implementation target is **role evidence**, not a hard corridor/activity classifier. A block may therefore carry `role_status`, evidence channels, and an uncertainty or ambiguity state.

## Relation to B1

B1 currently conditions on a frozen candidate universe `K` and estimates authored-group membership `P(Z[g,k] | E,K,M)`. Automatic space-block generation changes the candidate universe and is therefore outside the current estimand. It must not be inserted into B1 as an unannounced likelihood edge.

The intended order is:

1. finish B1 design review and decide whether Bayesian inference remains diagnostic-only or merits a richer design;
2. design and test the space-field resolution/stability contract;
3. design block extraction and the heterogeneous graph contract;
4. only then decide whether a joint furniture/space model is necessary.

## Explicit non-goals

- no production automatic-space implementation;
- no fixed absolute corridor threshold;
- no claim that a free-space block is psychologically perceived as a corridor;
- no replacement of authored IFC facts by inferred blocks;
- no collapse of furniture membership, space-role evidence, and route connectivity into one score;
- no production selector or Bayesian prior is frozen by this document.

## Required future experiments

- multi-resolution convergence on exact IFC-derived analysis geometry;
- narrow passage, broad open area, disconnected space, wall/opening, and multi-level fixtures;
- comparison of component extraction, distance field, and gap-path graph outputs;
- stability of heterogeneous graph topology under resolution changes;
- provenance and status propagation for missing/invalid/partial/not_available space evidence;
- independent visualization of furniture nodes, empty-space blocks, paths, and typed edges.
