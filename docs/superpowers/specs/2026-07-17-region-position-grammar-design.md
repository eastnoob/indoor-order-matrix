# Region Position Grammar Design

## Status

This spec supersedes the position-layer parts of
`2026-07-16-position-grammar-proxy-design.md`.

The previous implementation made `P_position_fit` describe the positions of
`FurnitureAffordanceExtent` records inside one `FurnitureGroup`. That is useful
debug evidence, but it is the wrong public matrix layer.

This design makes the public position variable describe the positions of
`FurnitureGroup` records inside an analysis scope.

## Goal

Build a robust position-order layer for the evaluation matrix:

```text
P_position_fit
P_position_confidence
```

`P_position_fit` answers:

```text
Do furniture groups fall into a stable position grammar inside their analysis
scope?
```

The public metric must not answer:

```text
Are the individual furniture pieces inside one furniture group arranged well?
```

That second question belongs to a separate, nested assembly-debug layer.

## Required Hierarchy

The runtime hierarchy is:

```text
Object
-> FurnitureAffordanceExtent
-> FurnitureGroup
-> ActivityRegion / RoomScope
```

Definitions:

- `Object`: one parsed SVG/BIM object, such as a chair, table, sofa, plant, or
  column.
- `FurnitureAffordanceExtent`: the simplified operational substitute used for
  furniture geometry. It is derived from the object plus authored affordance
  data in the SVG test adapter, and should come from BIM/neutral input later.
- `FurnitureGroup`: the smallest semantic furniture unit used by matrix
  position analysis, such as a table-chair set, lounge set, work pair, or a
  one-member fallback group.
- `ActivityRegion`: a larger area containing one or more furniture groups.
- `RoomScope`: a whole-scene fallback analysis scope used when authored region
  labels are identical to furniture-group labels and no larger region exists.

`FurnitureGroup` and `ActivityRegion` must not be treated as the same layer.

## Input Semantics

SVG remains only a proxy input and visual test bed.

SVG may provide:

- `data-furniture-group` or `furniture-group`;
- `data-region` or region metadata;
- object geometry;
- authored affordance properties;
- authored slot metadata in later tests.

The matrix consumes neutral records after loading. It must not depend on SVG
syntax directly.

The fixture `test/SVG_potionNoRotation.svg` is part of this design. It is a
position-order test object where object rotation should not be needed to explain
the metric. It must be included in notebook and pytest verification.

## Scope Construction

The algorithm builds `PositionScope` records before scoring.

Each scope contains:

```text
id
kind                         # activity_region or room_scope
member_group_ids
rect / bbox
frame
frame_basis
source
```

Scope construction rules:

1. Prefer authored `ActivityRegion` records when they contain at least two
   `FurnitureGroup` records.
2. When SVG fixtures use the same labels for `region` and `furniture_group`,
   build one `RoomScope` containing all non-global furniture groups.
3. Exclude plants and other non-furniture/non-analysis objects unless they are
   explicitly authored as furniture groups.
4. A scope with fewer than two furniture groups is `not_available`, not a low
   position score.

This avoids pretending that one furniture group can have an inter-group position
grammar.

## FurnitureGroup Proxy

Each `FurnitureGroup` is represented once in public position scoring.

The group proxy contains:

```text
id
center_x
center_y
rect / bbox
frame_angle
frame_strength
frame_basis
member_ids
furniture_affordance_extent_ids
```

The proxy center is the group-level operational position. It should come from
the union of the group's authored operational geometry:

1. authored group position if present;
2. union of member `FurnitureAffordanceExtent` records;
3. object footprint bbox only as loader/test fallback.

The public position layer must never create one slot per chair/table extent when
the subject is a furniture group.

## Frame Semantics

Position is not rotation.

Rotation/trend may define the local coordinate system, but it must not directly
lower `P_position_fit`.

Frame source priority:

1. authored scope frame;
2. frame from the scope's member furniture-group consensus;
3. room/region geometric frame;
4. global x/y fallback only when explicitly marked as weak evidence.

If all objects are shifted out of ideal locations but rotations remain zero,
`P_position_fit` must still change. This is the purpose of
`SVG_potionNoRotation.svg`.

## Grammar Candidates

The public region-level grammar works over furniture-group proxies.

Candidate types:

- `authored`: explicit slots from input metadata;
- `line`: groups form one local row/sequence;
- `grid`: groups form local rows and columns;
- `pair`: two groups form matched local offsets around a scope center;
- `multi_system`: several simple systems inside one scope, used only when a
  single simple grammar clearly under-explains the data.

Selection rule:

```text
authored <= line <= pair <= grid <= multi_system
```

Pick the simplest grammar with adequate fit. Keep rejected candidates as nested
evidence, not public matrix rows.

## Fit

Every selected grammar produces assignments:

```text
FurnitureGroup current center -> expected slot
```

Each assignment has:

```text
actual_x, actual_y
slot_x, slot_y
distance
normalized_distance
```

Public fit:

```text
P_position_fit = 1 / (1 + mean_normalized_distance)
```

The normalizing scale is chosen from the selected scope:

1. authored slot spacing;
2. inferred local spacing;
3. mean furniture-group size;
4. scope size fallback.

When no stable scale exists, return `not_available`.

## Confidence

`P_position_confidence` is evidence reliability, not design quality.

It increases with:

- authored group and region semantics;
- enough furniture groups for the chosen grammar;
- stable local frame evidence;
- low assignment ambiguity;
- consistent residuals.

It decreases with:

- one furniture group only;
- mixed systems without enough evidence to split them;
- weak frame;
- missing authored grouping;
- residual dominated by one unexplained outlier.

## Matrix Contract

Public rows:

```text
view_id: internal_order
metric: P_position_fit
metric: P_position_confidence
```

Nested evidence key:

```text
region_position_grammar_evidence
```

The public matrix must not expose these as top-level metrics:

```text
line_fit
grid_fit
pair_fit
group_assembly_fit
extent_position_fit
```

## Assembly Debug Layer

The existing extent-level grammar is retained only as a nested debug layer:

```text
group_assembly_grammar
```

It answers:

```text
Are the member affordance extents inside this furniture group arranged in a
simple way?
```

It may be shown in a debug notebook, but it must not drive the public
`P_position_fit` row.

## Visualization

The default position overlay draws only region-level evidence:

- green outline: one `FurnitureGroup` proxy;
- yellow point: expected slot for that furniture group;
- yellow line: residual from group center to expected slot;
- text/title metadata: scope id, grammar type, fit, confidence, residual.

The number of yellow points in the default overlay must equal the number of
scored furniture groups in the selected scope, not the number of individual
furniture objects or affordance extents.

The debug assembly overlay may draw extent-level slots, but it must use a
different function name and layer names so the two views cannot be confused.

## Implementation Phases

### Phase 1: Spec And Boundary Tests

Add tests that fail under the current implementation:

- `P_position_fit` evidence subject is `ActivityRegion` or `RoomScope`, not
  `FurnitureGroup`.
- A scope with three furniture groups creates three slots.
- No `FurnitureAffordanceExtent` id appears as a public position assignment.
- `SVG_potionNoRotation.svg` participates in position verification.

### Phase 2: Scope Builder

Add a small scope builder that consumes existing neutral records:

```text
furniture_groups
inferred_regions / authored regions
room bounds
```

It emits `PositionScope` records and does not change SVG parsing semantics.

### Phase 3: Region-Level Grammar

Move the public grammar calculation to group proxies inside scopes.

The existing extent-level function is either renamed or wrapped as
`group_assembly_grammar` so the old layer is still inspectable but no longer
public.

### Phase 4: Matrix And Adapter Wiring

Wire public rows to region-level evidence:

```text
P_position_fit
P_position_confidence
```

Adapter payload should include:

```text
region_position_grammar
group_assembly_grammar
```

Only `region_position_grammar` contributes to public position rows.

### Phase 5: Visualization

Replace the default focused overlay with region-level group slots/residuals.

Keep a separate debug overlay for assembly evidence only if it helps inspection.
Do not show both in the same default notebook cell.

### Phase 6: Notebook Verification

Update the position notebook to show:

- `SVG_baseline.svg`;
- `SVG_oblique.svg`;
- `SVG_chaoticsvg.svg`;
- `SVG_potionNoRotation.svg`.

The notebook should report:

```text
scope_count
scored_group_count
P_position_fit
P_position_confidence
grammar_type
mean_residual
```

The visual check must make it obvious that yellow points are furniture-group
slots.

## Acceptance Criteria

The work is complete only when:

- public `P_position_fit` is computed from furniture-group positions inside
  scopes;
- default position overlay shows one yellow slot per scored furniture group;
- extent-level slots no longer appear in the default position overlay;
- `SVG_potionNoRotation.svg` is included in pytest and notebook verification;
- shifted position without rotation changes `P_position_fit`;
- pure rotation/frame changes do not directly count as a position penalty;
- old extent-level evidence is either renamed to `group_assembly_grammar` or
  removed from public output;
- pytest passes for focused position tests and existing MVP tests;
- executed notebook and PNG visual verification are regenerated.

## Open Constraint

Current SVG fixtures often use the same label for `region` and
`furniture_group`. The implementation must therefore build a `RoomScope`
fallback for verification, while preserving the stricter long-term BIM contract:

```text
BIM/SVG input should eventually provide ActivityRegion and FurnitureGroup as
separate semantic layers.
```

