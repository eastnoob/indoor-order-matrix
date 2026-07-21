# Column Grid Continuous Field Design

## Status

This is a design spec for a continuous column-frame field layer in the indoor
layout evaluation matrix. It is not an implementation plan.

SVG remains a neutral BIM proxy/base map. The field layer consumes neutral
scene records, explicit column axes, generated bays, and inferred region
geometry. It does not infer axes from columns, and it does not rewrite the SVG
fixture into the matrix definition.

## Problem

The current column-grid contract is discrete:

- `C_global` compares a region frame with authored system and branch frames.
- `C_local_profile` compares a region with nearby authored bays.
- `column_grid_inter_region_alignment` compares gap-path travel with the grid.

That is good for regular rectilinear systems, but it is not enough for uneven
spans, partial bay coverage, oblique layouts, or regions whose structural
context is better described as a continuous influence than as one exact bay
match.

The matrix therefore needs a field layer that answers:

- what local column structure influences this region;
- in what axial direction that influence points;
- how strong that influence is;
- how much of the strength comes from support versus directional clarity.

## Goals

- Keep explicit axes, branches, and bays as the structural scaffold.
- Add a continuous field layer that reuses that scaffold instead of replacing
  it.
- Make the field robust to uneven bay sizes and oblique grids.
- Keep the field independent from SVG rendering and from any new axis inference.
- Preserve existing `C_global`, `C_local_profile`, and inter-region rows.
- Make strength auditable, not a hidden scalar.

## Non-Goals

- Do not infer column axes from physical columns.
- Do not replace bay-based local profiles.
- Do not add a dense raster or navmesh field in the first version.
- Do not make the field depend on SVG element names or overlay conventions.
- Do not add a new geometry dependency.

## Recommended Approach

Use a hybrid field:

1. Keep bays and branches as the discrete structural backbone.
2. Define a continuous field over query points in the scene plane.
3. Sample that field at deterministic region probes.
4. Aggregate those samples into one region-level field record.

This is the smallest design that stays continuous without becoming a full
physics-like simulation.

## Considered Approaches

### A. Bay-only

Use only bay overlap and branch adjacency.

Tradeoff: simple, but it fails when bays are uneven, oblique, or partly missing.

### B. Full dense field

Build a rasterized influence map over the whole room.

Tradeoff: expressive, but expensive, hard to test, and unnecessary for the
current matrix.

### C. Hybrid field

Use bays and axes as the structural basis, then compute a continuous influence
field only at deterministic probe points.

Tradeoff: one small helper layer, strong enough for irregular cases, and easy to
audit.

Recommended: C.

## Field Definition

The field is a function over a query point `q`:

```text
field(q) -> {
  angle,
  secondary_angle,
  support,
  clarity,
  strength,
  evidence
}
```

The field reports a two-axis frame:

- `angle` is the dominant axial orientation.
- `secondary_angle` is the orthogonal companion.
- `support` is how much local structural evidence is present.
- `clarity` is how unimodal that evidence is.
- `strength = support * clarity`.

The field is axial, so 0 and 90 degree evidence belong to the same frame.
That means the frame averaging must use doubled or quadrupled angle vectors,
not a naive linear mean.

## Strength Rule

Strength should not grow just because there are more items. It should grow when
nearby evidence is both:

1. present in enough local structural mass;
2. directionally consistent.

Use this rule:

```text
support(q) = normalized local evidence mass
clarity(q) = vector length of the axial evidence consensus
strength(q) = support(q) * clarity(q)
```

Evidence mass should combine:

- structural proximity in bay-graph space;
- geometric proximity in scene space;
- authored branch/system support;
- bay overlap when available.

This lets a messy region keep a real direction while still showing weaker
strength than a clean one.

## Neighborhood Rule

The field should not use one fixed world-space radius.

Instead:

- use the seeded bay neighborhood from the region shape;
- expand by bay graph distance within the same branch or system;
- convert Euclidean distances using a local scale derived from the nearby bay
  or axis spacing;
- fall back to the nearest authored bay or nearest authored axis only when no
  bay overlap exists.

This keeps the field adaptive to uneven spans and avoids a hard global cutoff.

## Probe Rule

The field should be sampled at deterministic probes rather than a dense grid.

For each region, use:

- the region centroid;
- the major-axis endpoints when a polygon exists;
- the midpoints of the longest stable edges when a polygon exists;
- the bbox center only as a fallback.

The region-level result is the weighted aggregation of those probes.

## Data Flow

```text
explicit column axes
  -> column_grid_evidence builds branches, bays, and bay adjacency
  -> region geometry from inference provides deterministic probes
  -> continuous field evaluates local evidence at each probe
  -> region field summary stores angle, secondary angle, support, clarity,
     and strength
  -> evaluator exposes the row and notebook overlay
```

## Proposed Outputs

Add one region-level evidence record family:

- `column_grid_field_profile`

Suggested row shape:

- `target_layer = "ActivityRegion"`
- `target_id = <region_id>`
- `score = field_strength`
- `field_angle`
- `field_secondary_angle`
- `field_support`
- `field_clarity`
- `field_strength`
- `field_evidence`

This row is additive. It does not replace:

- `column_grid_C_global`
- `column_grid_C_local_profile`
- `column_grid_inter_region_alignment`

## Integration Points

### `features/column_grid.py`

Add a continuous-field helper that:

- consumes region geometry, branches, bays, and adjacency;
- computes probe-level field evidence;
- aggregates the result into a region field record.

### `features/scene_evaluator.py`

Expose the new field row beside the existing column-grid rows.

### Notebook overlay

Draw the field direction as a line whose length reflects `strength`.
Do not snap the field to an orthogonal display-only simplification.

## Acceptance Checks

- A clean oblique region should produce an oblique field angle, not a forced
  horizontal or vertical one.
- A mixed region should keep the dominant angle but show lower strength.
- A region with uneven bay coverage should still get a stable field when the
  local structure is coherent.
- A region with no authored axes should return `not_available`, not a guessed
  field.
- Existing bay-based column-grid tests should continue to pass.

## Test Plan

Add focused tests for:

- one regular orthogonal scene;
- one oblique scene;
- one uneven / mixed scene;
- one no-axis scene.

The tests should assert both angle and strength behavior, not just presence.

## Grill-Me Self-Check

- Is this just `C_local_profile` with a different name? No. `C_local_profile`
  stays discrete and bay-based; the field is continuous and probe-based.
- Is this a full raster field? No. That would be heavier than the problem
  needs.
- Does strength come from item count? No. It comes from normalized local
  support and directional clarity.
- Can the field work without SVG parsing? Yes. It only needs neutral scene
  records and explicit column evidence.
- Will oblique layouts survive? Yes, because the field uses axial frame
  consensus rather than orthogonal snapping.

## Brainstorming Self-Check

- The design stays inside the current architecture boundary: SVG is input, not
  the matrix.
- The design reuses existing column-grid evidence instead of inventing a second
  grid system.
- The design is strong enough for irregular cases without requiring a full
  navmesh or field simulation.
- The design keeps the implementation bounded to one new helper path and one
  new matrix row family.
