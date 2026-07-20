# Column Grid Layer Hierarchy Design

## Status

This is a design spec for column-grid relation layers in the indoor layout
evaluation matrix. It is not an implementation plan.

The design keeps SVG as a BIM proxy. SVG may provide explicit column axes,
physical column records, object records, and test fixtures, but the matrix
logic consumes neutral scene and inference records.

## Problem

Column-grid relation should not be treated as one flat score. A movable chair
being off-grid is not the same kind of evidence as an activity region ignoring
nearby structural bays, and neither is the same as the inter-region path system
cutting against the grid.

The matrix needs explicit layers so each relation can be enabled, audited, and
weighted independently.

## Design Principles

- Explicit column axes define the first implementation of the column grid.
- Physical columns are source evidence, not axis generators.
- Column bays are generated from adjacent authored axes.
- Furniture-derived regions remain inference evidence, not SVG annotations.
- Object-level column-grid metrics are optional diagnostics by default.
- Region and inter-region metrics are the primary perceptual candidates.
- Whole-room column-grid relation is a summary, not a separate mystery trend.
- Nearby grid context is graph distance across column bays, not metric radius.

## Neutral Layers

### `column_axis`

An authored structural reference line. In BIM terms this corresponds to an
explicit grid axis such as `IfcGridAxis`. In SVG tests this may be an `axis`
path or line.

Required evidence:

- `id`
- geometry
- `system_id`
- `branch_id`
- axis-list or derived axis-list
- direction angle or local frame

### `column_bay`

A structural span cell generated from adjacent column axes. In plain terms,
this is the small rectangle or quadrilateral enclosed by two neighboring axes
in one direction and two neighboring axes in the other direction.

Required evidence:

- `id`
- polygon or rect
- adjacent bay ids
- `system_id`
- `branch_id`
- source axis ids

### `activity_region`

A furniture-group region inferred from object affordance extents. This is the
main unit for region-to-grid evaluation.

Required evidence:

- `id`
- geometry
- member object or furniture-group ids
- trend frame
- frame strength or clarity

### `spatial_network`

A shared graph schema already used by `region_internal` and `inter_region`
evidence. Column-grid relation should use the `inter_region` scope when
evaluating region-to-region and path-to-grid organization.

## Metric Layers

### 1. `object_to_grid`

Purpose:

Object-level diagnostics for how individual source records relate to the
authored grid.

Default scoring role:

Disabled in the main score. It can be enabled for diagnostic mode or for object
classes that behave like fixed architectural elements.

Inputs:

- neutral objects
- physical/fixed-object classification from role or metadata
- column axes
- column bays

Evidence:

- nearest column axis
- distance to nearest axis
- containing or nearest bay
- local coordinates inside bay
- optional cross-bay footprint flag

Current reusable implementation:

- `object_column_axis_phase_alignment`
- `object_column_bay_local_position_coverage`

Required adjustment:

Add a matrix option or policy field that marks this layer as diagnostic-only by
default, while allowing fixed furniture, equipment, partitions, and boundary
objects to opt into scoring.

### 2. `region_to_local_grid`

Purpose:

Core evidence for whether an activity region relates to the nearby structural
bay context.

Default scoring role:

Primary candidate for the main score.

Inputs:

- inferred or authored activity regions
- region trend frame
- column bays
- bay adjacency graph

Nearby-grid definition:

The nearby grid is a bay graph profile:

- `scale=0`: bays overlapped by the region; if none overlap, the nearest bay
- `scale=1`: `scale=0` plus directly adjacent bays
- `scale=2`: one more adjacency expansion
- `scale=all`: all bays in the same branch

This is intentionally not an Euclidean radius. Graph distance across bays works
with uneven spans and keeps the definition tied to structural organization.

Evidence:

- seed bay ids
- included bay ids per scale
- region frame to branch/bay frame agreement
- region overlap with included bays
- region centroid or support inside bay-local coordinates

Current reusable implementation:

- `C_local_profile` in `features/column_grid.py`
- column-bay overlay and seed-bay overlay in `scene_metric_overlay_svg`

Required adjustment:

Ensure automatically inferred regions feed this layer consistently and make the
scale profile visible in the notebook. The implementation should keep
`scale=0`, `scale=1`, and `scale=all` first; `scale=2` can be added only when
the evaluator needs an intermediate profile.

### 3. `inter_region_to_grid`

Purpose:

Core evidence for whether relationships between activity regions are organized
by the structural grid.

Default scoring role:

Primary candidate for the main score.

Inputs:

- `inter_region` spatial network
- inferred gap paths
- activity-region centers and frames
- column bays and branches

Evidence:

- region-center edge direction versus branch/grid frame
- gap-path direction versus branch/grid frame
- whether inter-region connections travel through adjacent or coherent bay
  sequences
- whether major paths follow bay corridors instead of cutting arbitrarily
  across the grid

Current reusable implementation:

- `spatial_networks` from `features/scene_inference.py`
- inferred gap paths
- column bays and bay adjacency graph

Required adjustment:

Add a small evaluator row that joins inter-region network edges with the
column-bay graph. This should not create a new pathfinding system yet; the
first version only audits direction agreement and bay-sequence continuity for
existing inter-region evidence.

### 4. `whole_room_to_grid`

Purpose:

A reporting summary over region and inter-region column-grid evidence.

Default scoring role:

Summary only. It should not introduce an independent score unless later
perception experiments justify one.

Inputs:

- `region_to_local_grid`
- `inter_region_to_grid`
- optional enabled `object_to_grid` diagnostics

Evidence:

- distribution of local profile scores
- dominant branch ids
- count of conflicting regions or paths
- aggregate agreement by system and branch

Current reusable implementation:

- Existing `whole_space_force` rows are only a rough proxy.

Required adjustment:

Reframe current whole-space output as legacy/proxy evidence or replace it with
a summary built from the lower layers.

## Scoring Policy

The model should separate evidence generation from scoring policy.

Default policy:

- `object_to_grid`: diagnostic-only
- `region_to_local_grid`: enabled
- `inter_region_to_grid`: enabled
- `whole_room_to_grid`: summary-only

Optional policies:

- `object_to_grid_fixed_only`: score fixed objects and architectural elements
- `object_to_grid_all`: score all objects for debugging or special studies
- `column_grid_ablation`: expose all layers separately without aggregate score

Policy should be represented as evaluator configuration or row metadata, not as
SVG-specific flags.

## Target Layers

When exported through `room_analysis_model`, metrics should attach to explicit
targets:

- `object_to_grid`: `target_layer="Furniture"`, `target_id=<object_id>`
- `region_to_local_grid`: `target_layer="ActivityRegion"`,
  `target_id=<region_id>`
- `inter_region_to_grid`: `target_layer="SpatialNetwork"`,
  `target_id=<network_or_edge_id>`
- `whole_room_to_grid`: `target_layer="Room"`, `target_id="room"`

This follows the model rule that scoring rows target model layers rather than
SVG drawings.

Current row-level fallback in `features/room_analysis_model.py` is too coarse
for these layers. The implementation should expand per-object, per-region, and
per-network evidence items into metric records instead of relying only on one
row-level `target_id`.

## Data Flow

```text
SVG or BIM adapter
  -> neutral objects, columns, column axes
  -> column_grid_evidence builds axes, bays, branches, systems
  -> scene_inference builds activity regions, gap paths, spatial networks
  -> evaluator creates object, region, inter-region, and summary rows
  -> room_analysis_model exports rows with target_layer and target_id
```

## Edge Cases

- No authored column axes: column-grid layers are `not_available`.
- Physical columns without axes: keep columns as source evidence but do not
  fabricate axes or bays.
- Region outside all bays: use nearest bay as `scale=0` seed and report that
  fallback in evidence.
- Multiple grid branches: evaluate each relevant branch separately; do not
  average oblique branches into a false global axis.
- Irregular bay sizes: use bay graph distance and bay-local coordinates, not
  uniform spacing assumptions.
- Movable loose furniture: keep object-level relation diagnostic unless policy
  explicitly enables it.

## Minimal Implementation Direction

Use the current code as the base:

- keep `features/column_grid.py` as the column-grid evidence builder;
- keep explicit-axis parsing in `features/scene_loader.py`;
- reuse inferred regions and spatial networks from `features/scene_inference.py`;
- add only evaluator rows and tests needed to expose the four-layer contract;
- keep notebook visualization focused on `scale=0`, `scale=1`, and `scale=all`.

## Acceptance Checks

- A plain Python scene dict with explicit axes can generate column bays without
  SVG parsing.
- Physical columns alone do not generate bays.
- `C_local_profile` reports seed and included bay ids for inferred regions.
- Object-to-grid rows can be present while marked diagnostic-only by default.
- Inter-region rows target spatial-network evidence, not raw SVG elements.
- The notebook shows column axes, generated bays, seed bays, and nearby bay
  expansion for the three SVG fixtures.

## Self-Review

- No SVG-only metric semantics are introduced.
- No BIM plugin assumptions are required.
- No metric radius defines nearby grid context.
- Object-level evidence is configurable rather than permanently low-weighted.
- Whole-room relation is a summary over lower layers, not a separate hidden
  trend definition.
