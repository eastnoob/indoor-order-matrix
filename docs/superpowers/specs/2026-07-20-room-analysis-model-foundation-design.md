# Room Analysis Model Foundation Design

## Status

This spec defines the next architecture foundation for the indoor layout
evaluation matrix.

It replaces the earlier `SpatialEvidence` wording with a static
`RoomAnalysisModel`. The model describes how one room is organized across
multiple analysis layers. It is not an experimental subject table and it must
not include experiment-facing fields such as `subject_id`.

## Goal

Create one stable static model that can hold current and future matrix work:

```text
Room
-> Furniture / FurnitureGroup
-> ActivityRegion
-> SpatialNetwork
-> ReferenceSystem
-> MetricLayer
-> RoomSummary
```

The goal is not to add new scoring theory in this pass. The goal is to make the
existing region, trend, position, path, boundary, and column-grid work readable
as one room-level structure.

## Core Rule

The model is a layered room map.

Each layer owns objects. Metrics attach to those objects. Room summaries read
the metric layer. SVG remains only a BIM proxy adapter that can create neutral
records for these layers.

```text
SVG/BIM proxy input
  -> neutral scene records
  -> inferred analysis objects
  -> RoomAnalysisModel
  -> matrix rows / notebook overlays / adapter payloads
```

## Layers

### Base Layer

The base layer describes the room coordinate frame and room boundary.

Minimum records:

- room bounds;
- room boundary geometry when authored;
- scene units and scale settings when known.

This layer answers where the room is. It does not score order by itself.

### Object Layer

The object layer contains parsed objects and their operational substitutes.

Minimum records:

- `Furniture`;
- `FurnitureAffordanceExtent`;
- `FurnitureGroup`;
- optional non-furniture objects such as plants, columns, entries, and
  boundaries.

`FurnitureGroup` remains the smallest semantic unit for public position
analysis. A chair, table, sofa, or cabinet may still exist as an object, but
public region-level position order is computed from furniture groups.

### Region Layer

The region layer contains `ActivityRegion` records.

An `ActivityRegion` is a semantic analysis unit composed from one or more
furniture groups. It must have spatial support geometry, but its identity is not
the same thing as the geometry.

Current inferred region candidates fit this layer when explicit region records
are missing. Authored region semantics remain primary.

`RoomScope` is the whole-room fallback analysis scope used when the input has
furniture groups but no larger activity-region semantics. It is not a fake
activity region; it is a scoped container so metrics such as position grammar
can still report `not_available` or room-level evidence cleanly.

### Network Layer

The network layer holds spatial graphs.

The same graph schema should support:

- internal networks inside an activity region;
- inter-region path or gap-path networks;
- negative-space components and reachability evidence;
- future visibility or route graphs.

This keeps "region internal route" and "between-region passage" as two scopes
of the same network idea, not two unrelated systems.

### Reference Layer

The reference layer holds independent spatial reference systems.

Current and planned records:

- `ColumnGrid`;
- `ColumnAxis`;
- `ColumnBay`;
- boundary semantics;
- room axes;
- authored material or visual boundaries.

Reference systems are not generated from the furniture being evaluated unless a
fallback is explicitly marked as inferred. For the first column-grid workflow,
explicit axes are the source of truth.

### Metric Layer

The metric layer stores metric records attached to model objects.

Minimum metric record:

```text
metric
family
target_layer
target_id
value
status
geometry
anchor
reference
confidence
method
evidence
uncertainty
```

`target_id` means the static model object id, such as a region id, network id,
or room id. It is not an experiment subject id.

### Summary Layer

The summary layer describes the whole room from lower-layer metric records.

Minimum useful summaries:

- per-family room score profiles;
- area-weighted region metric means;
- worst-region and strongest-region evidence;
- dominant region/frame trends;
- path/network connectivity summaries;
- column-grid and boundary relation summaries when available.

This layer should produce a room profile, not one final calibrated perception
score.

## Compatibility With Current Work

Current abstractions fit without changing their meaning:

| Current concept | RoomAnalysisModel layer |
| --- | --- |
| parsed SVG/BIM objects | Object layer |
| affordance extents | Object layer |
| explicit `data-furniture-group` | Object layer: `FurnitureGroup` |
| inferred regions | Region layer: `ActivityRegion` |
| region trend/frame | Metric layer targeting `ActivityRegion` |
| rotation/frame coherence | Metric layer targeting `ActivityRegion` or `FurnitureGroup` |
| `P_position_fit` | Metric layer targeting `ActivityRegion` or `RoomScope` |
| gap paths | Network layer plus metric layer |
| negative-space graph | Network layer plus metric layer |
| boundary semantics | Reference layer |
| column axes/bays/system | Reference layer |
| score matrix rows | Projection from Metric and Summary layers |
| SVG overlay | Debug view of selected model layers |

The existing rows do not need to be deleted. They need a shared model-facing
export path so future metrics do not keep inventing private payload shapes.

## Existing Code Touchpoints

The first implementation should stay small and reuse existing outputs:

- `features/scene_loader.py` keeps SVG-to-neutral parsing.
- `features/scene_inference.py` keeps derived evidence such as inferred
  regions, gap paths, activity groups, networks, and boundary semantics.
- `features/position_grammar.py` keeps region-level position grammar evidence.
- `features/column_grid.py` keeps explicit column-grid evidence.
- `features/scene_evaluator.py` builds the public matrix rows and should become
  the first place that assembles `RoomAnalysisModel` from existing pieces.

Do not move algorithms during the foundation pass unless a small adapter helper
is enough.

The first pass may adapt existing matrix rows into metric records to avoid
rewriting working algorithms. The long-term direction remains model-first:
matrix rows are a projection from the model, not the source of room semantics.

## Implementation Scope For This Branch

This branch should deliver the foundation only:

1. Add a small `RoomAnalysisModel` builder from the existing evaluated scene and
   matrix payload, with matrix-row adaptation limited to metric records.
2. Add model objects for the layers that already exist in code.
3. Add metric records by adapting existing rows and evidence payloads.
4. Add room summary records from existing computed metric rows.
5. Add tests proving current region, position, path, and column-grid outputs
   can be represented in the model.
6. Add a notebook view that shows the model layers and summary tables.

The branch does not need to complete new column-grid, boundary, BIM, or
Bayesian-analysis features.

## Testing Requirements

Minimum pytest coverage:

- model builder returns all expected top-level layer keys;
- region trend metrics target `ActivityRegion`;
- `P_position_fit` targets `ActivityRegion` or `RoomScope`, not individual
  furniture objects;
- gap-path and negative-space records appear under `SpatialNetwork`;
- boundary semantics and column-grid records appear under `ReferenceSystem`;
- room summary is computed from existing metric records, not from a second
  hidden scoring path;
- the three existing SVG fixtures and `SVG_potionNoRotation.svg` can build a
  model without missing required layer keys.

Minimum visual verification:

- one notebook renders the base SVG plus selected model overlays;
- one table lists layer counts;
- one table lists metric records grouped by target layer;
- one table lists room summaries.

## Non-Goals

- No final perceived-order score.
- No Bayesian model.
- No experiment subject schema.
- No new SVG-only metric behavior.
- No automatic column-axis inference from columns.
- No full BIM plugin.
- No route certification or full navmesh.
- No replacement of working region, trend, position, or path algorithms.

## Self Review

- Placeholder scan: no `TBD` or unresolved placeholder remains.
- Consistency check: the spec uses `RoomAnalysisModel` as a static room map and
  does not mix in experiment subject fields.
- Scope check: this is one foundation branch because it adapts existing outputs
  instead of adding new geometry algorithms.
- Ambiguity check: metrics attach to `target_layer` and `target_id`; `target_id`
  is a static model object id, not an experimental subject id.
- SVG/BIM boundary check: SVG remains an adapter/debug proxy, while the model is
  built from neutral scene and matrix records.
