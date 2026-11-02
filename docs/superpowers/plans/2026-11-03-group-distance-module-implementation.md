# Group distance module implementation plan

Date: 2026-11-03  
Status: **Ready for implementation; design frozen; no production code started**

## Goal and boundary

Implement the frozen group distance module against one scene-view handoff. Keep the two raw readings separate: centroid-to-centroid Euclidean distance and centroid/free-space hybrid distance. Preserve pair-local state, route lineage, source identity and the complete unordered scope. Do not add a field package, distance-to-support transform, scheduler, cache service, or generic export layer.

The pinned IFC is `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` with SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`. The confirmed S4 handoff is the manifest/result pair under `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/`; never consume its failed `domain_result.json` as confirmed domain input. The implementation must resolve scene geometry once and keep coordinate translation in that handoff path, with no second projection.

## Concrete API handoff

Add `features/group_distance.py` with documented immutable records:

- `GridDescriptor(grid_id, frame, origin, spacing, n_rows, n_cols, row_axis, column_axis, cell_rule, domain_fingerprint, occupancy_fingerprint)`.
- `GroupProjection(group_id, components, source_refs, status, explanation)` where components use the existing exterior/holes polygon record shape.
- `GroupDistanceInput(source_identity, analysis_plane, domain, grid, groups, physical_occupancy, unresolved_source_ids, unresolved_supports, query, query_context, origin_offset, dependency_fingerprints)`.
- `GroupPairDistanceObservation(pair_id, group_ids, center_to_center_euclidean, centroid_free_space_hybrid, geometry_audit, route, lineage, dependencies)`.
- `GroupDistanceResult(observations, pair_index, manifest, diagnostics)`.

`query` is the existing `FieldQuery` record, keeping every null/non-null field in its fingerprint. The frozen constructor handoff also includes `query_context`, field algorithm/schema versions, normalized occupancy source IDs, unresolved IDs/support hashes, and row/column convention. Nested records must be defensively frozen or copied to immutable tuples so later caller mutation cannot change the input identity.

Main entry point: `calculate_group_pair_distances(input_bundle) -> GroupDistanceResult`. Use `serialize_group_distance_result(result) -> dict` for the runner; do not export it from `features/__init__.py` unless an existing import convention requires it.

The kernel constructs `FreeSpaceField` from the same explicit domain/grid/occupancy/query handoff. The runner supplies constructor data rather than a separately constructed field, eliminating a second metadata API. It must never read private field attributes, silently resample, reuse the B3 inspection grid, or accept a separately built field whose identity is unverified.

## Algorithm steps

1. Validate source, plane/frame/units, S4 confirmation binding, domain geometry, grid coverage, query fingerprint and occupancy fingerprints. Return `not_available` or `invalid` according to the frozen precedence; do not turn missing input into occupied/free.
2. Build each qualifying group union and fixed centroid. Record area, component count, centroid-inside flag and source references. Generate stable `CellKey`, `AccessKey`, and `EdgeKey` values.
3. Query observed and optimistic cell states from the same `FreeSpaceField` handoff. Generate all 4-neighbor access candidates using positive-area footprint intersection and shared-edge midpoint offsets. Keep duplicate access candidates for audit, then reduce the same free cell to the smallest offset with stable `AccessKey` tie selection.
4. For each graph mode, process one source group at a time. Run NetworkX 3.6.1 weighted Dijkstra with a virtual source edge carrying the selected source access offset. Release source labels/predecessors after all targets are consumed. Record source-run count, node/edge counts, runtime and peak memory.
5. Recover the route from the exact tight predecessor DAG. NetworkX scalar labels are numerical authority. Apply the frozen conditional/unknown count, access-key, and full-cell-path ordering. Keep source offset, route edge sum, target offset, backend label, recomposed sum and residual/ULP diagnostic. A non-finite or materially inconsistent diagnostic is a contract failure; residual never changes route selection or status.
6. Emit one observation for every `combinations(sorted(group_ids), 2)` pair. Preserve `outside`, `not_available`, `invalid`, `unknown`, `unreachable`, `partial` and `computed` states; never omit a no-route pair or substitute Euclidean distance for hybrid.

## Runner and renderer

Add `scripts/design/group_level/run_group_distance_ifc.py`. It must:

- verify the pinned IFC path, byte count and SHA-256 before scene parsing;
- load and cross-check `s4_confirmed_manifest.json` with `s4_confirm_result.json`, including active domain, camera plane, request/candidate/domain identities and source revision;
- require explicit `--spacing-m` for the first run. The retained feasibility probe used `0.1 m` and produced a `121 × 47` covering grid; the value is not a production default. If a scene setting is used later, write its value and provenance into `GridDescriptor`;
- parse one scene-view for groups, physical occupancy and confirmed domain, then construct the immutable input bundle;
- write `observations.json`, `pair_index.json`, `run_manifest.json`, `coverage_report.json`, and a route locator for every pair, including no-route states.

Add `scripts/design/group_level/render_group_distance_preview.py` as output-only. It reads the package and same-source camera-plane geometry, then writes a complete pair matrix/list and indexed route views. It must not recompute distance or infer missing routes.

## Checklist and stopping gates

- [x] `.18.0` Frozen spec, `.17` readiness and owner acceptance complete (2026-11-03); bounded probe/evidence linked below.
- [ ] `.18.1` Implement immutable input records and validation in `features/group_distance.py`.
- [ ] Implement same-view S4/domain/grid/occupancy adapter and coordinate handoff.
- [ ] Implement deterministic NetworkX source-batched search and route recovery.
- [ ] Implement complete 666-pair observations, index bijection and package manifest.
- [ ] Record actual node/edge counts, source runs, runtime and peak memory.
- [ ] Run the pinned IFC with explicit spacing and verify source hash before/after.
- [ ] Render same-plane matrix and route views for all pair locators.
- [ ] Reconcile observations, locators, manifest and hashes.
- [ ] Record states actually observed; leave absent branches explicitly unobserved.
- [ ] Request user visual review only after real IFC artifacts exist.

## Observation and artifact schema

JSON schema version: `group-distance/v1`. One top-level result has `group_ids`, sorted
`observations`, `pair_index`, `manifest`, and `diagnostics`. Pair identity is a stable
hash of the source scene namespace and the sorted two immutable group IDs, never a
row number. Every pair has:

- `pair_id`, `group_ids=[source_id,target_id]`;
- `center_to_center_euclidean={status,value,units,centroid_source_refs}`;
- `centroid_free_space_hybrid={status,value,units,reason,optimistic_lower_bound,tie_uncertainty,conditional_cell_count,unknown_cell_count,arithmetic}`;
- `geometry_audit` keyed by group ID with union area, component count, centroid coordinates/relation and source refs;
- `route` with source/target access records (`group_id,footprint_cell,free_cell,shared_edge,proxy_point,cell_center,offset`), ordered cells/edges, source/route/target components, selected state/source refs and separate optimistic witness when present;
- `lineage` and `dependencies` referencing actual group geometry, input manifest, field queries, exact-domain coverage and selected cell/edge/occupancy records. `arithmetic` uses the exact names and numerical checks in frozen spec §4.4.

Absent values/routes are JSON `null`, never zero or an invented polyline. The route
locator remains present for every no-route state and resolves to a status view.
Shared run metadata may be referenced rather than duplicated per pair. Do not add
`FieldResultEnvelope` or modify the existing package evaluate signature.

Artifacts in one output directory: `run_manifest.json`, `observations.json`,
`pair_index.json`, `distance_rows.csv` (or a complete matrix), `coverage_report.json`,
and same-plane source geometry. The renderer adds `index.html` and indexed SVG
route views. The manifest/index map each `pair_id` to one observation and one route
view locator (a shared view plus fragment is allowed). Reconciliation checks exact
pair-set equality, duplicate absence, readable locators, source/input/output hashes,
finite metric values when present and component arithmetic. All 37 input group IDs
and all 666 pairs remain even though many groups may lie outside the small S4 domain.
Use an explicit `null/not_applicable` matrix diagonal.

## Runnable commands and checks

Run all commands from `D:/PROJECTS/understandOtherPackage/order_analyzer_group_distance`:

```powershell
$env:PYTHONNOUSERSITE='1'
$env:PYTHONPATH='.'
pixi run python docs/project/evidence/distance-readiness-probe-2026-11-03.py
pixi run pytest test/test_group_distance.py test/test_free_space_field.py test/test_analysis_requests.py -q
pixi run python scripts/design/group_level/run_group_distance_ifc.py --source-ifc ../order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --s4-dir outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z --spacing-m 0.1 --output-dir outputs/design/group_distance_ifc/run_v1
pixi run python scripts/design/group_level/render_group_distance_preview.py --run-dir outputs/design/group_distance_ifc/run_v1 --output-dir outputs/design/group_distance_preview/run_v1
```

The script flags above are the runner interface to implement, not commands that
already exist. `--source-ifc` uses the actual pinned source in the main workspace;
the runner must hash it and record the resolved path. The 0.1 m grid is an explicit
diagnostic resolution: about 5,687 cells over S4, roughly 6.25 times the cell count
of the existing 0.25 m inspection setting. It is not a body-width calibration.

Focused tests should retain the bounded nonspatial graph insertion-order/count/
lineage checks and immutable query/identity checks. Runtime spatial assertions must
use this real IFC/run, without simulated geometry, furniture, layouts, IFC or preset
distance fixtures. Assert every selected path node/query, 4-neighbor step, exact
coverage edge and lineage binding; compare repeated same-input normalized content
for identity determinism, and verify changed metadata invalidates fingerprints.
Record unobserved geometric/status branches instead of manufacturing coverage.
Run the relevant existing regression checks once; broaden only after a concrete
failure or later shared-boundary edit.

Keep this entire checklist current while executing: mark a task in progress in its
line, attach the actual code/artifact/check evidence before checking it, and retain
failed or unobserved items accurately. Text readiness is complete; actual 666-pair
execution, peak resources, artifact reconciliation and user visual review are later
acceptance gates. Finish the implementation only when real generated artifacts are
reviewable; user visual acceptance must never be inferred from test success.

## Evidence already accepted

- `docs/project/evidence/distance-readiness-2026-11-03.md`
- `docs/project/evidence/distance-readiness-probe-2026-11-03.py`
- `docs/project/evidence/distance-backend-contract-probe-2026-11-02.md`
- `docs/project/evidence/distance-spec-grill-review-2026-11-02.md`
- confirmed S4 manifest/result under `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/`

## Known limits

No production distance code, IFC occupancy grid, full-pair run, route visualization, or user visual acceptance exists yet. The readiness probe is nonspatial and cannot establish runtime reachability, unknown/conditional coverage, performance at 37 groups, or geometric correctness of the future route renderer.
