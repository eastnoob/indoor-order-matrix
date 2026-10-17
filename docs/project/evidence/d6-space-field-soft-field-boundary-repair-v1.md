# D6 soft-field boundary repair v1

Date: 2026-10-02<br>
Status: diagnostic evidence only; stop at `STOP FOR SOFT-FIELD OWNER VISUAL REVIEW`<br>
Backup checkpoint: git commit `de1c53b` (`chore: checkpoint D6 evidence before boundary repair`)

## Purpose

This repair reruns the D6 soft-field / empty-space evidence design on the unchanged real IFC:

`outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`

The prior `run_001` artifacts are preserved. The prior empty-space complement subtracted only authored `furniture_group` geometry. Walls and columns were rendered as context but were not consumed by the occupancy calculation. `repair_v1` adds valid physical wall and column geometry to an independent empty-space diagnostic while retaining the existing furniture-group support field.

## Input and scope

- Exact `ObjectType == "furniture_group"` groups remain the only analysis nodes: 37 groups and 95 grouped furniture members.
- Group members are never split and authored membership is never rewritten.
- Walls remain physical geometry and external enclosure evidence. Doors are context/reference only; no opening or state is assumed.
- All 16 `IfcColumn` products are directly contained by the single observed `IfcBuildingStorey/Level 1`.
- Columns enter calculation only after floor, world-XY projection, finite valid geometry, and derived full-level height-band checks. The observed column z range is 0–4.5 m; the diagnostic band derived from group/column geometry is approximately -0.020855–4.5 m.
- The provisional frame is a view frame from extracted wall and furniture extents. It is not a room boundary or accepted AnalysisDomain.

## Boundary repair

One column footprint and source reference are reused for three diagnostic uses:

1. candidate source for external enclosure evidence;
2. internal solid obstacle and empty-space boundary;
3. local direction, arrangement, and spatial-separation reference.

Wall adjacency is recorded as one evidence field only. It is not a selection gate. The 16 eligible columns therefore produce 16 boundary candidates even though only 14 intersect the projected wall union. The three roles remain separate: wall-based external enclosure evidence, column-based internal obstacle boundary, and unselected column-line separation clue.

Column alignment and proximity never fills a gap, closes a corridor, or changes connectivity. The synthetic isolated-column, wall-edge-column, and three-column-row cases all reduce occupied area while retaining one connected diagnostic complement; `virtual_separation_hypothesis` remains `not_selected`.

## Real IFC before/after

The preserved baseline is the original `run_001` furniture-only complement in the same provisional frame. The repair subtracts the union of valid physical wall triangles, all eligible column footprints, and declared furniture-group footprints.

| Evidence | Before `run_001` | After `repair_v1` |
|---|---:|---:|
| Occupancy sources | furniture groups | walls + columns + furniture groups |
| Bounded free area | 355.8844 m² | 326.5177 m² |
| Complement components | 1 | 5 |
| Local width proxy p50 | 3.4244 m | 1.0033 m |

The component increase is a physical-obstacle diagnostic. It is not a route, walkability, visibility, room, or free-space truth result.

## Soft-field and hard-candidate reading

The continuous furniture-group support field retains all 37 nodes and relative gradients. Exact zero normalized-gap contact components expose a compact four-group band at the upper-left of the plan (`G06`, `G11`, `G20`, `G27` in the rendered stable source-id order). This is the clearest local support for a local sub-field: it is a repeated contact relationship rather than a single isolated hard cut.

The lower-left and lower-right clusters do not acquire an independent boundary from the repaired evidence. Their touching pairs resemble the repeated layout pattern elsewhere, and the column-line profile remains a reference-only alignment signal. No virtual wall is selected. This supports reading those clusters as layout variation pending owner interpretation, rather than as automatically separate zones.

The hard candidates remain discrete views of the same relative evidence:

- 1 region is the uncut baseline; its mean node support is 0.5000.
- 2 regions adds one low-support ranked gap (`0.1464`, relative rank `0.0857`); mean node support is 0.4865.
- 3 regions adds a second low-support ranked gap (`0.1468`, relative rank `0.0827`); mean node support is 0.4785.
- 4 regions adds a third low-support ranked gap (`0.1547`, relative rank `0.0752`); mean node support is 0.4588.

These values support visual comparison of hard cuts against a continuous field. They do not freeze region count, threshold, algorithm, production resolution, or selector.

## Empty-space diagnostic

`empty_space_field` remains independent of furniture membership. It records free area, component continuity, adjacent wall/column/furniture source references, local width proxy, relative bottleneck samples, and boundary provenance. Context identity does not exclude wall or column physical geometry from occupancy, and no context product becomes a furniture-group node.

## Artifacts and checks

The complete repair bundle is in `outputs/design/space_field_soft_field_experiment/repair_v1/`:

- JSON field, candidate, occupancy, before/after, provenance, scope, schema, validation, and manifest records;
- `hard_1_regions.png` through `hard_4_regions.png`, `soft_field_diagnostic.png`, `empty_space_diagnostic.png`, `before_furniture_only.png`, `before_after_comparison.png`, and `boundary_evidence.png`;
- disposable `d6_soft_field_boundary_repair_v1_disposable.blend` with nine orthographic scenes.

Validation passed for source hash, JSON contract, PNG dimensions and non-empty crop, temporary-directory reproduction, and disposable blend readback. The current Blender identity was previously observed with the real IFC path and Level 1 inventory; this repair did not open, save, or modify the user’s current Blender file. The portable Blender background process was used only for disposable rendering.

No production code, adapter, formal test, dependency, source IFC, API, or user Blender file was modified. No Bayesian/ML model, production resolution, route width, fixed metre threshold, or selector was chosen.

STOP FOR SOFT-FIELD OWNER VISUAL REVIEW
