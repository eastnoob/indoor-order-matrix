# D6 Real IFC Pairwise Furniture-Group Relationship Experiment

- Date: 2026-10-05
- Scope: bounded, read-only real-IFC relationship diagnostic
- Source: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`
- Evidence class: diagnostic only
- Production integration: none

## Blockers

No extraction blocker remained. A qualified `AnalysisDomain` was unavailable,
so the world-XY projection is diagnostic evidence only. The full IFC adapter and
full pytest suite were intentionally not run. SVG XML and labels were checked;
the PNG was inspected from the rendered file. The local browser policy prevented
opening the SVG as a browser tab, so SVG visual inspection is represented as an
unverified presentation check rather than claimed as passed.

## Important findings

- 37 nodes were retained, all exact authored `IfcGroup` entities with
  `ObjectType == "furniture_group"`.
- Their 95 `IfcFurniture` members remain observations inside the authored node;
  no group was split into member nodes.
- The complete unordered node-pair set contains 666 pairs. Every pair is
  `computed`, `diagnostic_only = true`, `formal_edge = false`, and
  `membership_promotion = false`.
- Planar observations are 650 gaps, 10 contacts, and 6 overlaps. All 666 pairs
  are Z-compatible.
- 65 witness segments intersect eligible wall/column context, 585 do not, and
  16 pairs have no applicable wall/column witness context.
- No pair was excluded and no pair was promoted to formal membership.
- Relative near/far examples are descriptive rankings only; no distance cutoff
  or grouping threshold was selected.

## Minor findings

- The visualization shows representative pair witnesses rather than drawing all
  666 pair lines, while the JSON preserves every pair.
- The PNG uses a disposable top-down Blender Workbench scene at 3600 × 2400.
- The SVG remains a 2000 × 1300 XML artifact and retains the required diagnostic
  boundary labels.

## Real IFC facts versus unavailable/diagnostic evidence

The source evidence provides IFC4 identity, authored group membership, direct
Body tessellation projections, placements, units, and eligible wall/column
footprints. The experiment computes group footprints by unioning member Body
projections in authored world placement and records source/member references.

The result does not establish a qualified analysis domain, room identity,
free-space geometry, route, walkability, connectivity, space role, or a
production grouping rule. Nearest-boundary witnesses are geometric segments,
not paths. Invalid or missing geometry would remain explicit; none occurred in
this selected set.

## Node inventory

The node inventory is in
`outputs/design/live_ifc_pairwise_relationship_experiment/pairwise_real_ifc_observations.json`.
Each node records its stable IFC GlobalId, source STEP id, authored name,
member references, exact object type, geometry provenance, geometry status, and
vertical extent. The verifier confirms every node is an `IfcGroup` with exact
`ObjectType == "furniture_group"`.

## Pairwise relation inventory

Each pair records stable pair ID, both group IDs, source member references,
geometry provenance, world-XY frame and metre units, tolerance provenance,
planar relation, witness geometry, Z compatibility, occupancy context, shared
dependencies, status, and formal-edge flags. Counts are:

| Observation | Count |
|---|---:|
| Gap | 650 |
| Contact | 10 |
| Overlap | 6 |
| Computed status | 666 |
| Z-compatible | 666 |
| Wall/column witness blocked | 65 |
| Wall/column witness not blocked | 585 |
| No applicable occupancy witness | 16 |

## Excluded-pair inventory

`pairwise_excluded_pairs.json` contains zero excluded pairs. The bounded
verifier confirms the count and preserves the exclusion-reason field for any
future excluded record.

## Wall/column influence

Eligible walls and columns are physical occupancy context only. The output keeps
walls and columns separate, records their source IDs, and explicitly marks
columns as not virtual walls. A blocked witness means that an eligible wall or
column intersects that pair's geometric witness segment; it does not mean a
route is blocked and does not create furniture membership.

## Z/frame/tolerance provenance

The analysis plane is IFC world XY, the length unit is metres, and the source
mesh coordinate-weld tolerance is 1e-9 m. Planar contact uses exact topological
predicates with zero contact tolerance. Vertical compatibility uses closed
interval overlap with exact comparison. No repair, gap fill, convex hull, or
silent geometry substitution was applied.

## Why pairwise evidence does not imply group membership

The authored IFC group is the only node-creation authority. A pairwise gap,
contact, overlap, witness, centroid distance, or occupancy observation describes
the relationship between two already-authored nodes. It neither changes their
membership nor creates an edge for an inferred group. All serialized pair
records therefore retain `formal_edge = false` and
`membership_promotion = false`.

## Whether this evidence supports a later inferred-group design experiment

Yes, as bounded input evidence for a later design-only comparison of candidate
relations, provided that experiment retains source provenance, explicit missing
and ambiguous states, the no-selection state, and the same separation between
diagnostic pairwise evidence and authored membership. It does not authorize a
selector, threshold, inferred group, room, or production API.

## Explicit production boundary

No production rule, selector, threshold, formal edge, free-space computation,
walkability result, connectivity result, or membership inference was chosen.

STOP FOR REAL IFC PAIRWISE RELATIONSHIP DESIGN REVIEW
