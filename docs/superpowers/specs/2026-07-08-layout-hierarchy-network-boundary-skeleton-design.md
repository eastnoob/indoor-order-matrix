# Layout Hierarchy Network Boundary Skeleton Design

## Goal

Add first-class evidence skeletons for activity groups, shared spatial networks, and semantic boundaries without changing the SVG/BIM separation.

## Scope

This pass builds the minimal matrix-facing skeleton. It does not add a BIM plugin, polygon boolean operations, navmesh routing, or calibrated perception metrics.

## Architecture

The neutral scene remains the only input object. SVG is still only one adapter that can create a neutral scene.

`features/scene_inference.py` owns the new derived evidence:

- `activity_groups`: one record per user-authored region/group key, composed from member furniture affordance extents.
- `spatial_networks`: one shared graph schema used for both `region_internal` and `inter_region` networks.
- `boundary_semantics`: one record per boundary/entry/path-like record describing walkability, visibility, thickness, grouping, and openings.

`features/scene_evaluator.py` only exposes these evidence records in the matrix result and adapter payload evidence geometry. It does not define region, path, or boundary semantics itself.

## Data Semantics

User-authored attributes are primary. Object `region`/`group`, boundary metadata, weights, openings, and path settings are trusted when present.

Geometry fallback is secondary. Bounding boxes and inferred affordance extents create computational stand-ins when the matrix needs geometry, but these stand-ins do not override semantic labels.

Furniture group affordance extent is a union envelope, not a Boolean intersection. Overlap/intersection is recorded as relation evidence because it can indicate common-use, conflict, or tight coupling, but it is not the complete group extent.

## Evidence Records

Activity group records include:

- `id`
- `region`
- `member_ids`
- `furniture_affordance_extent_ids`
- `rect`
- `metadata.level = activity_group`
- `metadata.geometry_basis = union_envelope_of_member_furniture_affordance_extents`
- optional overlap evidence between member affordance extents

Spatial network records share one schema:

- `id`
- `scope`, either `region_internal` or `inter_region`
- `nodes`
- `edges`
- `components`
- `metadata.method`

Boundary semantic records include:

- `id`
- `kind`
- `walk_passable`
- `see_passable`
- `thickness`
- `grouping_strength`
- `opening_ids`
- `surface_identity`
- `metadata.source`

## Testing

Use plain Python scene dictionaries with `Rect` records so behavior proves the matrix is independent of SVG parsing.

Minimum tests:

- activity group extent uses union of member furniture affordance extents and records overlap evidence separately.
- `region_internal` and `inter_region` networks use the same schema with different scopes.
- boundary semantics classify rug, low cabinet, and glass-like boundaries from metadata and weights.
- evaluator exposes the new evidence at top level and in `adapter_payload.evidence_geometry`.

## Self Review

No placeholders remain. Scope is one implementation pass. The plan deliberately avoids polygon booleans and BIM-specific adapters because the current requirement is a skeleton that preserves the layer boundary.
