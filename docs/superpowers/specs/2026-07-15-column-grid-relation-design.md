# Column Grid Relation Design

## Status

This spec defines the neutral column-grid model used by the layout evaluation
matrix. It is a design spec, not an implementation plan. SVG may be used to
test the model, but SVG is only a BIM proxy and must not define the metric
logic.

## Design Self-Check

The direction is valid if the column grid is treated as an independent
structural reference system, not as another furniture-derived region. The
current working note is conceptually sound, but it mixes the broader
`F/R/B/C` candidate model with the specific `C` column-grid design. This spec
separates the `C` design so the next implementation can stay small.

Four constraints are mandatory:

- No fixed metric distance or hand-authored "surrounding radius" decides local
  column-grid influence.
- Column axes are explicit input for the first implementation. IFC `IfcGridAxis`
  or SVG `axis` metadata maps to `ColumnAxis`.
- Irregular and oblique grid branches remain separate records instead of being
  averaged into one false grid.
- The evaluator reports evidence profiles; perceptual experiments decide which
  local scale matters.

## Scope

Build a neutral representation that can express:

- the whole structural grid trend;
- local bay-based structural context around a furniture region;
- region-to-grid evidence needed for `C_global` and `C_local_profile`.

Do not implement the deferred boundary variable `B` here. Do not make SVG
geometry part of the matrix definition.

## Neutral Object Layers

The minimum useful hierarchy is:

```text
Column
  -> ColumnAxis
    -> ColumnBay
      -> ColumnBranch
        -> ColumnSystem

FurnitureGroupRegion relates to ColumnBay, ColumnBranch, and ColumnSystem.
```

### Column

A physical structural column or authored column marker.

Minimum attributes:

- `id`
- center or footprint geometry
- optional size/thickness
- `system_id`
- optional `branch_id`

Relations:

- belongs to one `ColumnSystem`;
- may reference nearby `ColumnAxis` records, but must not create them in the
  first implementation.

### ColumnAxis

A structural reference line or curve through related columns.

Minimum attributes:

- `id`
- axis geometry
- direction or sampled local frame
- `system_id`
- `branch_id`
- optional authored axis label/order

Relations:

- belongs to one `ColumnBranch`;
- adjacent axes form `ColumnBay` records.

### ColumnBay

A local structural span cell. In plain terms, it is the structural unit between
adjacent column axes, not a furniture area and not a perceptual range.

Minimum attributes:

- `id`
- polygon or affine quadrilateral
- local `u/v` frame
- adjacent bay ids
- `system_id`
- `branch_id`

Relations:

- forms the bay adjacency graph;
- can contain, overlap, or neighbor a `FurnitureGroupRegion`.

### ColumnBranch

A continuous local grid family, such as an orthogonal main zone or an oblique
wing.

Minimum attributes:

- `id`
- `system_id`
- member axis ids
- member bay ids
- branch trend frame
- bay adjacency graph

Relations:

- belongs to one `ColumnSystem`;
- supplies branch-level evidence for both global and local column-grid relation.

### ColumnSystem

The authored structural grid system for the scene or floor zone.

Minimum attributes:

- `id`
- branch ids
- global trend frame
- source and confidence metadata

Relations:

- supplies the whole-structure reference for `C_global`;
- contains one or more branches for `C_local_profile`.

### FurnitureGroupRegion

The evaluated furniture-region unit. It is built from furniture-group
affordance proxies, not raw SVG shapes.

Minimum attributes:

- `id`
- region geometry
- member furniture-group ids
- region frame or trend frame
- frame clarity

Relations:

- seeds intersected or nearest `ColumnBay` records;
- compares its frame and bay-local organization against column-grid context.

## Variables

### `C_global`

Meaning:

Whether the furniture region follows the overall structural trend.

Computed from:

- `FurnitureGroupRegion.frame`
- relevant `ColumnSystem.global_trend_frame`
- relevant `ColumnBranch.trend_frame` when a system has multiple branches

Expected output:

- agreement value per relevant system or branch
- source ids used
- `not_available` when no usable column system exists

### `C_local_profile[r]`

Meaning:

Whether the furniture region forms local order with the structural context
around it.

The index `r` is bay-graph scale, not a metric radius:

- `0`: intersected or nearest seed bay set;
- `1`: seed bays plus adjacent bays;
- `2+`: wider bay-graph expansions;
- `all`: the complete branch profile point.

`all` is not `C_global`. It is only the branch-wide endpoint of the local
profile.

Each scale keeps two evidence parts:

- `frame_agreement`: region frame compared with included bay or branch frames;
- `bay_grammar`: furniture-group centers and extents expressed in included bay
  local coordinates.

Expected output:

- profile rows by branch and graph scale;
- seed bay ids and included bay ids;
- frame evidence;
- bay-local coordinate evidence;
- `not_available` when no usable bay context exists.

### `S_scope`

Meaning:

An experimental perceptual range parameter that decides which part of
`C_local_profile` best predicts human judgement.

Computed from:

- perception data outside the geometry engine.

It must not be hard-coded as a geometry threshold in the evaluator.

## Data Flow

```text
BIM or SVG proxy input
  -> neutral Column / Axis / Bay / Branch / System records
  -> neutral FurnitureGroupRegion records
  -> seed bay lookup by overlap or nearest support
  -> bay graph scale expansion
  -> C_global and C_local_profile evidence rows
  -> later perceptual model chooses weighting through S_scope
```

## SVG Test Adapter Rule

SVG may provide test metadata for:

- column markers;
- explicit `axis` records that map to `ColumnAxis` / IFC `IfcGridAxis`;
- axis labels;
- branch/system ids;
- bay polygons when authored;
- furniture-group and affordance proxy records.

SVG must not:

- define the meaning of `C_global`;
- choose `S_scope`;
- turn visual drawing order into analytical hierarchy;
- infer `ColumnAxis` from `piler` objects in the first implementation;
- infer affordance regions unless explicitly running a test helper.

## Error And Edge Cases

- No column grid: report `not_available`, not low order.
- One branch: compute one system/global relation and one local profile.
- Multiple branches: keep one profile per branch; do not average branches.
- Region outside all bays: use nearest bay support as seed and expose that
  provenance.
- Uneven bay sizes: use bay-local coordinates instead of uniform spacing.
- Oblique branch: keep its own branch frame and bay graph.
- Columns without explicit axes: keep the columns as evidence, but report
  missing axis support instead of silently inventing a grid.

## Test Expectations

The first implementation should prove four cases:

- uniform orthogonal grid;
- uneven bay spacing;
- oblique branch beside orthogonal branch;
- region with no usable column-grid support.

Visual notebook verification should show:

- columns;
- axes;
- bay polygons;
- branch ids;
- seed bay set per region;
- `C_global` direction evidence;
- `C_local_profile` scale evidence.

## Non-Goals

- No final perceived-order score.
- No fixed surrounding distance.
- No boundary-object model.
- No full BIM plugin.
- No SVG-only metric behavior.
- No automatic `ColumnAxis` inference from columns in the first implementation.

## Long-Term Goal

When explicit axes are missing, geometry may later infer candidate
`ColumnAxis` records from columns. That inference must remain a fallback with
`source = "inferred_from_columns"` and confidence metadata. It must never
override authored IFC `IfcGridAxis` or SVG `axis` records.
