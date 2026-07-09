# Internal Configuration Order: Working Note

## Status

This is a candidate measurement model for later perceptual experiments. It is
not a final score, and it does not assign hand-authored weights.

## Analysis Unit

The unit is a furniture-group affordance proxy. A single furniture item is a
degenerate group only when no group is available. SVG remains an input adapter;
the same neutral records can later come from BIM.

## Candidate Variables

| Key | Meaning | Excludes |
| --- | --- | --- |
| `F` frame coherence | Whether furniture-group frames form one stable local orthogonal coordinate system. A 90-degree turn is equivalent within that frame. | Spacing, boundary response, and inter-region trend. |
| `R` relational regularity | Whether normalized relations between furniture groups can be explained by a small set of repeated transformations: translation, reflection, rotation, or stable adjacency/facing. | A reward for low object count or low type variety. |
| `B` region-boundary relation | Whether a region relates to an independently authored boundary object. | Any boundary inferred from the same furniture being evaluated. This candidate is deferred. |
| `C` column-grid relation | Whether a region and its furniture groups relate coherently to the independent structural column systems and branches that influence their setting. | A uniform global-grid assumption, a fixed number of bays, or a requirement to align with every column. |

`compactness`, object count, and semantic variety are descriptive controls, not
internal-order variables. Region trend remains a separate, outward-facing
alignment descriptor. OCTA remains evidence only for explicitly comparable
repeated arrays; it is not the generic internal-order model.

## Experimental Form

The experiment, rather than code, determines whether and how the candidates
contribute to perceived order:

```text
perceived_order ~ F + R + C + controls + participant/scene effects
```

The final model may remove or merge candidates after experimental validation.

## Deferred Candidate: Region-Boundary Relation (`B`)

`B` is deliberately deferred. A boundary created from the evaluated furniture
would make the comparison circular. `B` may resume only after the neutral scene
contains an independently authored boundary object, such as a room edge, wall,
partition, rug, or other explicitly semantic spatial delimiter.

## Active Candidate: Local Column-Grid Relation (`C`)

The column system is an independent structural reference, not a permanently
uniform lattice. A region is not defined only by the column bays it occupies:
it can be between bays, beside a grid, or adjacent to a second oblique branch.
`C` must therefore not choose a fixed range, a fixed bay count, or an untested
distance-decay function.

Column systems and their branches must exist before `C` can be trusted. In BIM,
an authored `column_system` or `grid_system` label is primary. Geometry may
propose candidate systems from axis continuity, adjacency, and direction, but a
transition between an orthogonal main grid and an oblique wing must remain
auditable as multiple branches rather than being averaged into one false frame.

`C` is a multiscale relation profile, not one premature score. For every
column-system branch, seed the bay graph at the region's intersected bays or,
when none intersect, its nearest bay or bays. Then report the same relation at
every structural graph radius: seed bay, one adjacent-bay ring, two rings, and
so on through the whole branch. The final radius is only the branch-wide local
profile point, not the separate whole-system `C_global`. No radius is declared
to be the perceptual “surrounding”; later
experiments select or combine profile scales.

At each scale, retain two inspectable evidence parts, not pre-weighted scores:

- local-frame agreement: the region/furniture organization frame versus each
  influential local column-system branch;
- local-bay organization: positions and extents expressed in the included
  bays' local coordinates, preserving irregular bay sizes and oblique axes.

One bay cannot establish repeated grid rhythm, but it can still provide local
placement evidence. Multiple connected bays provide inter-bay evidence. An
oblique wing is a separate branch with its own profile, never an averaged axis.
A region with no usable column-system support is `not_available`, not low order.

The current implementation has useful prototypes for column axes and adjacent
bays, but its nearest-axis, global-median-spacing, and best-single-bay rows are
not yet the non-uniform local-patch model described here.

## Column-Grid Object Hierarchy for `C`

The column-grid relation should use a small neutral hierarchy. BIM labels are
primary when available; SVG geometry is only a test adapter that can populate
the same records.

| Layer | Meaning | Minimum Attributes | Main Relations |
| --- | --- | --- | --- |
| `Column` | A physical structural column or column marker. | `id`, center/footprint geometry, optional size/thickness, `system_id`, optional `branch_id`. | Belongs to one `ColumnSystem`; may support one or more nearby `ColumnAxis` records. |
| `ColumnAxis` | A structural reference line/curve through related columns. | `id`, geometry, direction/frame sample, `system_id`, `branch_id`, optional axis label/order. | Belongs to one branch; combines with adjacent axes to form `ColumnBay` records. |
| `ColumnBay` | A local structural cell or span patch. | `id`, polygon or affine quad, local `u/v` frame, adjacent bay ids, `system_id`, `branch_id`. | Forms the bay adjacency graph; contains or neighbors furniture regions. |
| `ColumnBranch` | A continuous local grid family, such as an orthogonal main hall or oblique wing. | `id`, `system_id`, member axes/bays, branch trend frame, bay graph. | Keeps incompatible grid directions separate and auditable. |
| `ColumnSystem` | The authored structural grid system for a room/floor zone. | `id`, branch ids, global trend frame, confidence/source metadata. | Supplies `C_global`; contains one or more branches for `C_local_profile`. |
| `FurnitureGroupRegion` | The furniture-region analysis unit built from group affordance proxies. | `id`, region geometry, group ids, region frame/trend, frame clarity. | Seeds the nearest/intersected `ColumnBay` records and compares its frame/relations to column context. |

Do not flatten oblique or discontinuous branches into one averaged grid. A
region may relate to multiple branches, but each branch must keep its own
evidence profile.

## `C` Variable Generation

`C` should expose two variable families plus one experimental scope parameter:

| Key | Role | Computed From | Interpretation |
| --- | --- | --- | --- |
| `C_global` | Region-to-whole-structure relation. | `FurnitureGroupRegion.frame` compared with each relevant `ColumnSystem` or branch trend frame. | Whether the region follows the overall structural trend, even when the grid is uneven. |
| `C_local_profile[r]` | Region-to-nearby-structure relation at graph scale `r`. | Seed `ColumnBay` records from region overlap/nearest support, then expand by bay-graph distance `r`. Compare local frames and bay-coordinate organization at each scale. | Whether the region forms local order with its surrounding structural context. |
| `S_scope` | Experimental perceptual range parameter. | Chosen or fitted outside the geometry engine from perception data. | Determines which `C_local_profile` scale or weighted scale combination best predicts human judgement. |

`C_global` is not a substitute for `C_local_profile`. A region can align with
the whole building trend while being locally awkward, or be locally organized
inside an oblique branch while weakly related to the dominant global frame.

`C_local_profile` is indexed by column-bay graph distance, not by a fixed metric
radius. Radius `0` is the intersected or nearest seed bay set; radius `1` adds
adjacent bays; larger radii continue through the branch; `all` is the complete
branch. The code should report the profile and evidence, not decide which
radius is perceptually correct.

Each local scale should keep two evidence parts:

- `frame_agreement`: agreement between the furniture-region frame and the
  included bay/branch frames;
- `bay_grammar`: furniture-group centers/extents expressed in the included
  bays' local coordinates, preserving irregular bay sizes instead of forcing a
  uniform grid.
