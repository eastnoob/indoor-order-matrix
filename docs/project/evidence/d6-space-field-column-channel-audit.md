# D6 column occupancy and channel audit v2

Date: 2026-10-03<br>
Status: bounded design diagnostic; no production selector selected<br>
Source: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`

## Audit result

`repair_v1/empty_space_candidates.json` does account for physical occupancy. Its `after` result uses valid projected wall geometry, eligible Level 1 `IfcColumn` geometry, and declared `furniture_group` geometry. The implementation unions these geometries before subtracting them from the provisional frame, so overlap is deducted once. The real inventory has one observed storey, 16 columns, and all 16 pass the recorded floor, world-XY, height, and geometry checks. The fixtures exercise non-target-level and missing/invalid states because those states do not occur in the confirmed real inventory.

The existing evidence includes free area, connected component count, a global `local_width_proxy_m`, relative bottleneck samples, and before/after deltas. For the real IFC, the staged values are:

| Stage | Free area | Components | Local-width p50 |
|---|---:|---:|---:|
| furniture only | 355.884414 m² | 1 | 3.424438 m |
| wall aware | 332.277691 m² | 3 | 1.040614 m |
| wall plus eligible columns | 326.517691 m² | 5 | 1.003333 m |

The global field is distinct from pairwise furniture separation. Existing hard cuts have geometric boundary-gap evidence, but this design does not implement a pairwise channel/free-space profile. The updated result therefore records `column_effect_on_pairwise_channel: not_available`. The global local-width proxy remains a relative occupancy-boundary diagnostic and is not called corridor width, route width, or true bottleneck width. Without a qualified `AnalysisDomain`, axis/path selector, or accepted channel rule, route width, walkability, and true traversal capacity remain `not_computable`.

## Restricted hard-partition semantics

The new JSON does not treat the earlier `columns_change_hard_partition: false` as proof that columns can never affect a future selector. It records:

- `hard_partition_change_status: "not_computable"`;
- `hard_partition_under_current_furniture_only_recipe: "unchanged"`;
- `column_effect_on_empty_space: "computed"`;
- `column_effect_on_pairwise_channel: "not_available"`.

B and C still reuse A's furniture partition. The wall/column selector remains deferred, and the furniture relation graph stays separate from the obstacle/boundary evidence graph.

## Fixtures

The eight fixtures cover two groups without columns; an internal column; a column near a gap while leaving an opening; a wall-edge column; a column row with open gaps; a column overlapping furniture; a different-level column; and missing/invalid geometry. Each record contains nodes, obstacle-union sources, stage free area, component count, local-width and relative bottleneck evidence, eligibility, provenance, membership status, and pairwise channel status. Every fixture keeps furniture membership unchanged, selects no virtual separation, and reports pairwise channel evidence as `not_available`.

The fixture interpretations are bounded: an interior column can reduce local clearance without disconnecting the field; a wall-edge column adds boundary context without creating an interior region; a column row remains an arrangement clue while its openings stay open; overlap is removed once by union; and excluded level or missing geometry remains excluded with provenance.

## Scope and validation

The audit reuses repair_v1 projections and the confirmed source hash; it does not rerun the full IFC geometry adapter. It writes only the new design-probe directory and its evidence records. Production code, adapter, API, formal tests, dependencies, source IFC, and the user's Blender file were not modified. Existing D6 visual artifacts remain available; no new Blender render was needed for this numeric audit.

Default run, temporary-directory deterministic rerun, JSON/schema checks, numeric/status assertions, manifest hashes, and bounded Git scope audit passed.

STOP FOR COLUMN OCCUPANCY AND CHANNEL AUDIT REVIEW
