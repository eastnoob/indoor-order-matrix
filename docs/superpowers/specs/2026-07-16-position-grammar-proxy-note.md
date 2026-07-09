# Position Grammar Proxy Note

## Status

This is a working design note for discussion, not an implementation spec.

## Purpose

`PositionGrammarProxy` is a neutral evidence layer for internal furniture-group
position order. It is paired with the existing frame/trend evidence but does not
replace it.

The proxy asks:

> Can the positions of authored furniture groups, or their imported member
> extents, be explained by a simple internal position rule?

It does not evaluate furniture response to external walls, curved boundaries,
rugs, partitions, column grids, or room edges. Those belong to boundary or
structural relation variables such as `B_boundary_relation` or `C_column_grid`.

## Relation To OCTA

The idea borrows OCTA's regularity/deviation logic, especially repeated
position regularity, but extends it with indoor-layout semantics.

OCTA contribution:

- repeated elements;
- position regularity;
- deviation from an expected pattern.

Indoor-layout extension:

- furniture-group affordance extents as the analyzed geometry;
- local frame coordinates instead of global x/y;
- authored furniture-group membership as the base analysis unit;
- pair, mirror, and repeated group relations.

## Current Code Mapping

The current implementation has an `activity_group` carrier that overlaps with
the intended furniture-group layer. The final implementation must not keep two
parallel group systems.

- `features.scene_loader` writes neutral `group` and `region` keys from
  `data-group`, `data-region`, or conservative SVG group-id fallback.
- `features.scene_inference.furniture_affordance_extents()` creates one maximum
  affordance envelope per participating furniture object.
- `features.scene_inference.activity_groups()` currently groups those extents
  by the semantic analysis region key. This is the implementation surface that
  must be renamed and semantically migrated, not duplicated.
- Each current group record already carries `member_ids`,
  `furniture_affordance_extent_ids`, a union `rect`, overlap evidence, and
  `group-axis-*` frame metadata.
- `features.scene_inference.spatial_networks()` already creates
  `region_internal` networks over the member affordance extents.

Therefore `PositionGrammarProxy` should not infer raw furniture membership from
object roles. Its target input is the canonical `FurnitureGroup` layer. The
implementation should migrate the existing `activity_group` code path to this
new semantic name and contract, then update existing consumers to read the new
records. It should not run old `activity_group` and new `FurnitureGroup`
systems side by side.

The intended hierarchy is:

```text
Object
-> FurnitureAffordanceExtent
-> FurnitureGroup
-> ActivityRegion
```

`FurnitureGroup` is the smallest semantic unit for position grammar. A single
object can be represented as a degenerate one-member `FurnitureGroup` only when
the input does not provide a richer group. `ActivityRegion` is a larger analysis
unit formed from one or more `FurnitureGroup` records.

The loader/BIM adapter should preserve explicit `furniture_group_id` or an
equivalent semantic group identifier. `PositionGrammarProxy` can evaluate
positions among furniture groups inside an activity region, or member extents
inside an explicitly authored furniture group, but it must not create the group
membership itself.

## Migration Rule

There must be one runtime group system after implementation:

```text
canonical: furniture_groups
removed/replaced: activity_groups as a runtime concept
```

Legacy SVG/BIM fields may be accepted only at the adapter boundary and must be
normalized immediately into `FurnitureGroup` records. Matrix rows, adapter
payloads, notebooks, tests, and internal networks should all consume the
canonical `FurnitureGroup` naming and semantics. Backward-compatible aliases may
exist in exported payloads only if they point to the same canonical records, not
to a separately computed group system.

## Minimal Outputs

`P_position_fit`

- Main evidence value.
- High when object positions are well explained by a simple internal position
  grammar.

`P_position_confidence`

- Evidence reliability, not an aesthetic score.
- High when the grammar has clear semantic or geometric support.
- Low or `not_available` when furniture count, roles, or geometry do not support
  a stable interpretation.

## Candidate Internal Grammars

Line grammar:

- Objects follow one local axis.
- Adjacent projected gaps are regular.

Grid grammar:

- Objects form rows and columns in a local two-axis frame.
- Rows and columns are not global x/y; they are coordinates inside the selected
  furniture-group or region frame.
- Fit depends on row/column assignment stability, spacing regularity, and
  residual distance to inferred slots.

Pair grammar:

- Two or more related objects form pair, mirror, or repeated relations.
- Fit depends on symmetry, matched offsets, and compatible orientation/frame.

Authored group grammar:

- The base unit is an authored or imported furniture group, not an automatically
  inferred object relation.
- Table-chair sets, lounge sets, and similar compositions should arrive as
  grouped records from SVG/BIM/user input.
- If a group carries internal anchor/member metadata, the proxy may use it as
  evidence, but it must not invent group membership from object roles.
- Current `activity_group` records should be replaced by canonical
  `FurnitureGroup` records during the migration.

## Scope Boundary

Curved-wall following, S-shaped wall seating, exhibition-wall furniture, and
other boundary-following cases are not part of this proxy. They should be
modeled later as boundary-relation evidence because the reference curve is an
external authored object, not an internal furniture-generated position grammar.

## Implementation Milestones

The milestones are delivery checkpoints, not scope reduction. The final
delivery of this proxy should cover the complete internal grammar set above:
line, grid, authored-group, and pair evidence, with one compact public output
layer.

Milestone 1: local-frame grid/line fit

- Reuse the canonical `FurnitureGroup` `group-axis-*` frame as the local `u/v`
  coordinate system, falling back to the inferred region frame only when group
  frame evidence is unavailable.
- Project furniture affordance extent centers into `u/v`.
- Split sorted `u` and `v` coordinates into candidate columns and rows using
  coordinate gaps, not global x/y.
- Build inferred slots from row and column centers.
- Match furniture centers to nearest slots and compute normalized residuals.
- Output provisional `P_position_fit`, `P_position_confidence`, and auditable
  row/column/slot evidence.

Milestone 2: multi-system and authored group relation fit

- Allow one region to contain more than one position system when a single
  grid/line explains the group poorly.
- Add authored group grammar for user/BIM-provided furniture-group records.
- Add pair grammar for mirror, symmetric, or matched-offset group relations.
- Select the simplest grammar or grammar combination that explains the
  furniture positions with low residual and sufficient confidence.

Final delivery

- Replace existing `activity_group` runtime usage with canonical
  `FurnitureGroup` naming and semantics across code, tests, notebooks, and
  adapter payloads.
- Expose `P_position_fit` as the main internal position variable.
- Expose `P_position_confidence` as reliability evidence, not a design score.
- Preserve detailed grammar evidence for inspection, notebook visualization,
  and later perceptual-model fitting.
- Do not infer table-chair or sofa-table group membership from raw object roles;
  grouping is input data or an upstream parsing responsibility.
- Keep boundary-following and column-grid relation evidence outside this proxy.
