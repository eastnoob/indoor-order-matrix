# Position Grammar Proxy Design

## Status

This is the formal design for the internal position-order proxy. It supersedes
the working note where the two conflict.

## Goal

Add one neutral evidence proxy for internal furniture-group position order:

```text
PositionGrammarProxy
```

It asks whether furniture-group positions can be explained by a simple internal
position rule. It is paired with the existing frame/trend evidence:

```text
F_frame_coherence  -> direction/frame order
P_position_fit     -> position-grammar order
```

`PositionGrammarProxy` is not a final perceptual model and does not assign final
experimental weights.

## Non-Goals

The proxy must not:

- infer table-chair, sofa-table, or other furniture membership from raw roles;
- keep `activity_group` and `FurnitureGroup` as parallel runtime systems;
- evaluate S-shaped walls, curved boundaries, exhibition walls, rugs, columns,
  or room-edge following;
- replace column-grid relation evidence;
- expose many top-level OCTA-like position variables before experiments justify
  them.

Boundary-following belongs to `B_boundary_relation`. Column and bay relation
belongs to `C_column_grid`.

## Canonical Hierarchy

The runtime hierarchy after migration is:

```text
Object
-> FurnitureAffordanceExtent
-> FurnitureGroup
-> ActivityRegion
```

`FurnitureGroup` is the smallest semantic unit for position grammar. It is an
authored or imported group such as a table-chair set, a sofa-table set, a row of
chairs, or a one-member degenerate group when no richer grouping exists.

`ActivityRegion` is a larger analysis unit composed from one or more
`FurnitureGroup` records.

## Migration Contract

Current code has `activity_group` records. They must be migrated into canonical
`FurnitureGroup` records, not duplicated.

Required rules:

- `scene/inference` runtime exposes one canonical `furniture_groups` collection.
- Existing consumers of `activity_groups` are updated to consume
  `furniture_groups`.
- Existing `activity_group` naming is removed from runtime APIs, matrix rows,
  notebooks, tests, and adapter payload primary fields.
- Legacy SVG/BIM fields may be accepted only at loader/adapter boundaries and
  normalized immediately into `FurnitureGroup` records.
- Any backward-compatible export alias must point to the same canonical records,
  not a separately computed group system.

## FurnitureGroup Record

A canonical `FurnitureGroup` record should contain:

```text
id
activity_region_id
member_ids
furniture_affordance_extent_ids
rect / bbox
overlap_evidence
group-axis-angle
group-secondary-axis-angle
group-axis-strength
group-axis-basis
group-axis-clarity
group-axis-member-alignment
```

These properties mostly exist on current group records and should be preserved
during the migration.

The loader should preserve explicit `data-furniture-group`,
`furniture_group_id`, or an equivalent BIM group identifier when present. If no
explicit group is present, a single object may become a one-member
`FurnitureGroup`.

## PositionGrammarProxy Output

The proxy creates auditable evidence records, not a separate semantic group
system.

Each evidence record should contain:

```text
id
subject_id
subject_kind                  # furniture_group or activity_region
position-frame-angle
position-frame-basis
position-grammar-type         # authored, line, grid, pair
position-fit
position-confidence
position-residual-mean
position-residual-max
position-member-count
position-slot-count
position-system-id
slots
assignments
residuals
```

Only two matrix-level variables are public:

```text
P_position_fit
P_position_confidence
```

All grammar-specific details remain nested evidence.

## Input Geometry

The proxy uses `FurnitureAffordanceExtent` centers and extents, not raw object
footprints by default. This keeps the calculation aligned with the existing
layout hierarchy where usable furniture space is different from physical
footprint.

For a `FurnitureGroup`, the proxy may evaluate member extents inside the group.
For an `ActivityRegion`, the proxy evaluates the positions of child
`FurnitureGroup` records inside that region.

## Local Frame

All position grammar runs in local `u/v` coordinates, never global x/y.

Frame source priority:

1. authored position frame on the `FurnitureGroup` or `ActivityRegion`;
2. existing `group-axis-*` frame on `FurnitureGroup`;
3. inferred region frame;
4. not available when no reliable frame exists.

Global translation and global rotation should not lower internal position order
when local relations remain stable.

## Grammar Candidates

Authored grammar:

- Used when input provides explicit slots or group-internal position metadata.
- Fit is member-to-authored-slot residual.
- Confidence is high when all required members and slots are present.

Line grammar:

- Used when members are explained by one local axis.
- Project member centers onto the dominant local axis.
- Sort projected coordinates and score adjacent gap regularity plus cross-axis
  residual.

Grid grammar:

- Used when members form row/column structure in local `u/v`.
- Cluster projected `u` coordinates into candidate columns and projected `v`
  coordinates into candidate rows.
- Build slots from row/column centers.
- Match members to nearest slots and score normalized residuals.

Pair grammar:

- Used when two or more groups form mirror, matched-offset, or repeated pair
  relations.
- Compare local-coordinate offsets around the group or region center.
- Score matched offset residuals and optional frame compatibility.

## Fit Calculation

Every grammar produces normalized residuals. The shared fit shape is:

```text
P_position_fit = 1 / (1 + mean_normalized_residual)
```

Residual normalization should use the most local stable scale available:

1. authored slot spacing;
2. inferred row/column spacing;
3. mean member extent size;
4. group or region frame extent.

When no stable scale exists, the evidence is `not_available` rather than a low
score.

## Confidence Calculation

`P_position_confidence` is reliability evidence, not a design score.

It should increase with:

- explicit authored grouping or slots;
- enough members for the chosen grammar;
- stable local frame evidence;
- low assignment ambiguity;
- residuals that are not dominated by one unexplained outlier.

It should decrease or become `not_available` when:

- the group has too few members for the chosen grammar;
- one region mixes multiple systems that are not separated;
- slots greatly outnumber or undercount members;
- the local frame is weak or missing.

## Grammar Selection

The proxy should choose the simplest adequate explanation.

Complexity order:

```text
authored <= line <= pair <= grid <= multi-system
```

Authored evidence wins when complete because it comes from the input contract.
Otherwise, if two grammars have similar fit, choose the lower-complexity grammar
and keep the rejected candidates as evidence.

The selected grammar defines the public `P_position_fit`. Rejected candidates
are inspectable but not separate matrix variables.

## Matrix Rows

Add rows under an internal-order view:

```text
view_id: internal_order
metric: P_position_fit
metric: P_position_confidence
```

Rows should include:

```text
method
status
score
evidence
position_grammar_evidence
uncertainty
```

The rows must not expose `line_fit`, `grid_fit`, `pair_fit`, or similar as
parallel public metrics until experiments justify them.

## SVG Test Platform

SVG remains a test adapter and visualization substrate only.

SVG fixtures may provide:

- `data-furniture-group`;
- `data-region` or equivalent activity-region labels;
- object geometry and affordance attributes;
- intentionally shifted members for residual tests.

The proxy must consume neutral records after loading. The same records should be
replaceable by BIM input later.

## Verification Plan

Tests should cover:

- canonical `FurnitureGroup` records replace runtime `activity_group` records;
- loader preserves explicit furniture group IDs from SVG proxy input;
- no duplicate old/new group systems are emitted;
- line grammar scores regular one-axis group positions higher than shifted
  positions;
- grid grammar works in a rotated local frame, not global x/y;
- pair grammar identifies matched local offsets;
- `P_position_fit` changes when a member is shifted while frame coherence stays
  high;
- boundary-following examples remain out of scope or `not_available`;
- notebook overlay shows slots, assignments, residual vectors, selected grammar,
  fit, and confidence.

## Acceptance Criteria

Implementation is complete only when:

- runtime group terminology is canonicalized to `FurnitureGroup`;
- all previous `activity_group` consumers use the canonical records;
- focused pytest coverage passes;
- the SVG notebook visually demonstrates regular, shifted, rotated, and
  multi-system cases;
- no matrix row or adapter payload contains separately computed old and new group
  systems;
- `P_position_fit` and `P_position_confidence` are available as the only public
  position-order variables.

