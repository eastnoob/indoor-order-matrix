# Group distance module implementation plan

Date: 2026-11-03  
Status: **Kernel and IFC delivery implemented; complete outside/Euclidean run recorded; useful real-route validation and user visual acceptance open**

## Goal and boundary

Implement the frozen group distance module against one scene-view handoff. Keep the two raw readings separate: centroid-to-centroid Euclidean distance and centroid/free-space hybrid distance. Preserve pair-local state, route lineage, source identity and the complete unordered scope. Do not add a field package, distance-to-support transform, scheduler, cache service, or generic export layer.

The pinned IFC is `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` with SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`. The confirmed S4 handoff is the manifest/result pair under `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/`; never consume its failed `domain_result.json` as confirmed domain input. The implementation must resolve scene geometry once and keep coordinate translation in that handoff path, with no second projection.

## Concrete API handoff

Implemented in `features/group_distance.py` with documented immutable records:

- `GridDescriptor(grid_id, frame, origin, spacing, n_rows, n_cols, row_axis, column_axis, cell_rule, domain_fingerprint, occupancy_fingerprint)`.
- `GroupProjection(group_id, components, source_refs, status, explanation)` where components use the existing exterior/holes polygon record shape.
- `GroupDistanceInput(source_identity, analysis_plane, domain, grid, groups, physical_occupancy, unresolved_source_ids, unresolved_supports, query, query_context, origin_offset, dependency_fingerprints)`.
- `GroupPairDistanceObservation(pair_id, group_ids, center_to_center_euclidean, centroid_free_space_hybrid, geometry_audit, route, lineage, dependencies)`.
- `GroupDistanceResult(observations, pair_index, manifest, diagnostics)`.

`query` is the existing `FieldQuery` record, keeping every null/non-null field in its fingerprint. The frozen constructor handoff also includes `query_context`, field algorithm/schema versions, normalized occupancy source IDs, unresolved IDs/support hashes, and row/column convention. Nested records must be defensively frozen or copied to immutable tuples so later caller mutation cannot change the input identity.

The same-view `query_context` must include `analysis_plane_fingerprint` equal to
`fingerprint_evidence_dependency` of the actual `AnalysisPlane` contents. Require
`query_context.frame == query.frame == grid.frame`, with the same domain frame.
Missing or mismatched binding returns `not_available`. Canonical plane metadata
need not invent `frame`/`frame_id` fields; when present they must match. Never infer
or default the query/grid frame from a canonical plane. The runtime runner supplies
this same required binding used by the kernel.

`origin_offset` is required, must contain two finite real coordinates (excluding
bool), and participates in the query/handoff identity. A changed offset changes the
fingerprint; malformed input yields `invalid`. Malformed occupancy metadata now also
preserves all expected pair observations with `invalid` hybrid state instead of
escaping during fingerprint construction. Euclidean observations retain their
independent valid-centroid semantics.

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

Implemented `scripts/design/group_level/run_group_distance_ifc.py`. Its verified handoff and delivery responsibilities are:

- verify the pinned IFC path, byte count and SHA-256 before scene parsing;
- load and cross-check `s4_confirmed_manifest.json` with `s4_confirm_result.json`, including active domain, camera plane, request/candidate/domain identities and source revision;
- require explicit `--spacing-m` for the first run. The retained feasibility probe used `0.1 m` and produced a `121 × 47` covering grid; the value is not a production default. If a scene setting is used later, write its value and provenance into `GridDescriptor`;
- parse one scene-view for groups, physical occupancy and confirmed domain, then construct the immutable input bundle;
- write `observations.json`, `pair_index.json`, `run_manifest.json`, `coverage_report.json`, and a route locator for every pair, including no-route states.

Implemented `scripts/design/group_level/render_group_distance_preview.py` as output-only. It reads the package and same-source camera-plane geometry, then writes a complete pair matrix/list and indexed route views. It must not recompute distance or infer missing routes.

## Checklist and stopping gates

- [x] `.18.0` Frozen spec, `.17` readiness and owner acceptance complete (2026-11-03); bounded probe/evidence linked below.
- [x] `.18.1` Implement immutable inputs/fingerprints and kernel logic in `features/group_distance.py`. The implementation includes same-input `FreeSpaceField` construction, source-batched NetworkX search, deterministic route recovery, pair observations and serialization. Latest implementer result: `13 passed in 0.30s` for guarded `pixi run pytest test/test_group_distance.py -q` on 2026-11-03. The checks cover input detachment, identity/order behavior, missing-input pair coverage, abstract-graph tie/count/lineage behavior, binary64 diagnostics, explicit retained-camera-plane fingerprint/frame binding, origin-offset identity/validation and malformed-occupancy invalid-pair preservation; these standalone checks do not establish spatial route validity. Kernel review is closed at `.18.3`; the real run is separately limited as recorded below.
- [x] `.18.2` Same-view S4/domain/grid/occupancy adapter and coordinate handoff implemented and exercised in `outputs/design/group_distance_ifc/run_v1/`. The explicit plane fingerprint, common view offset and retained input validation are recorded in the [IFC evidence](../../project/evidence/group-distance-ifc-v1.md).
- [x] `.18.3` Independent kernel/interface review closed by the owner after the exact input-binding/occupancy fixes; the focused kernel result is `13 passed in 0.30s`. Runner/renderer delivery checks separately report `4 passed in 5.48s`; the fresh combined owner check reports `17 passed in 5.30s` (exit 0). This acceptance covers the implemented contract and observed data, not unobserved real routes.
- [x] `.18.4` Generated all 37-group / 666-pair observations, index and manifest. All 666 Euclidean readings are computed; all 666 hybrid observations are `outside`, with null route/value. No expected pair is missing or duplicated.
- [x] `.18.5` Actual resources recorded: 5687 samples; both graphs have 0 nodes/edges/source searches. Final first kernel: `47.2163139 s`, Python tracemalloc peak `23,744,479 B`. Final same-bundle two-kernel process: `101.6013874 s`, Windows peak working set `205,701,120 B` / peak commit `195,854,336 B`. Earlier full capture/adapter plus two kernel calls: `751.2994114 s`, peak working set `2,825,302,016 B` / peak commit `2,877,648,896 B`. These are separate scopes, not a 37-active-source route benchmark.
- [x] `.18.6` Pinned IFC hash/bytes match before and after; same-bundle normalized result SHA-256 is `db188cdd9f555041b92ef36a732d6ac70e67c9049a1059dce3bdac25ea093249` on both kernel evaluations. Source/plane/grid/query bindings and the retained-input upgrade are recorded in the evidence.
- [x] `.18.7` Published full-scope plan, complete matrices/rows and all 666 readable pair/status view locators in `run_v1/preview/index.html`. Both representative PNGs show S4 left of the furniture. No hybrid route is present; route/access-marker rendering is spatially unobserved.
- [ ] `.18.8` **Partially verified:** actual expected/observation/index/visual sets reconcile at 666 each, with zero missing/duplicate IDs; scoped review verified all 14 recorded hashes and all 666 readable locators. Selected path/node/edge checks execute 0 cases. Useful real-route nodes/edges/lineage/arithmetic validation therefore remains open and cannot be passed by this outside-only run.
- [x] `.18.9` Actual state coverage recorded: 666 hybrid `outside`, 666 Euclidean `computed`, 5651 established occupied samples and 36 outside samples; 0 free/unknown. Other hybrid/status/access/tie/conditional route branches remain spatially unobserved.
- [ ] `.18.10` User visual review remains pending. The full-scope IFC/S4 preview is reviewable; owner inspection of PNGs is not user visual acceptance. Master `.18` stays open for useful real-route validation and user acceptance.

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
pixi run pytest test/test_group_distance.py -q
pixi run pytest test/test_group_distance_ifc_delivery.py -q
pixi run python scripts/design/group_level/run_group_distance_ifc.py --source-ifc ../order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --s4-dir outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z --spacing-m 0.1 --output-dir outputs/design/group_distance_ifc/run_v1
pixi run python scripts/design/group_level/render_group_distance_preview.py --run-dir outputs/design/group_distance_ifc/run_v1 --output-dir outputs/design/group_distance_ifc/run_v1/preview
```

The commands above show the implemented fresh-output CLI; the existing `run_v1` must not be overwritten. The final delivery reused the authenticated retained `run_v1_attempt02/input_bundle.json` through the runner API and repeated the same immutable input after the input-binding correction; [execution evidence](../../project/evidence/group-distance-ifc-v1.md) retains the exact attempt lineage. The renderer must publish to `RUN_DIR/preview`, matching the recorded pair locators. Actual checks and remaining limits are tracked at `.18.2` and `.18.4–.18.10`. `--source-ifc` uses the actual pinned source in the main workspace;
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
failed or unobserved items accurately. Text readiness is complete. The actual outside-only 666-pair execution, peak resources
and artifact reconciliation are recorded; useful real-route validation and user visual
review remain open acceptance gates. Finish the implementation only when real generated artifacts are
reviewable; user visual acceptance must never be inferred from test success.

## Evidence and current implementation record

Kernel implementation: `features/group_distance.py`; focused tests: `test/test_group_distance.py`. The implementer supplied the guarded result below; this documentation update reused that evidence without rerunning the tests:

```powershell
$env:PYTHONNOUSERSITE='1'
$env:PYTHONPATH='.'
pixi run pytest test/test_group_distance.py -q
# 13 passed in 0.30s (latest focused kernel result)
```

Fresh owner verification (2026-11-03), reused here without rerunning:

```powershell
$env:PYTHONNOUSERSITE='1'
$env:PYTHONPATH='.'
pixi run pytest test/test_group_distance.py test/test_group_distance_ifc_delivery.py -q
# 17 passed in 5.30s; exit 0
```

The owner also inspected `preview/representative_01.png` and confirmed the displayed
left S4/right furniture separation. This is owner inspection, not user visual
acceptance. Scoped review independently verified all 14 artifact hashes and all
666 locators within the Euclidean/outside slice; no real route was observed.

The latest focused result supersedes the earlier `11 passed in 0.31s` implementation record. The added fixes require the explicit plane-content binding, include and validate origin offset in handoff identity, and preserve invalid-pair observations for malformed occupancy metadata. The runtime runner has been adapted to the same binding field. The owner accepted the exact kernel fixes and review closure. Real IFC delivery evidence is [group-distance-ifc-v1.md](../../project/evidence/group-distance-ifc-v1.md): `4 passed in 5.48s` for guarded `pixi run pytest test/test_group_distance_ifc_delivery.py -q`, plus execution of all 666 actual viewer selections in a Node minimal DOM host. This checks recorded-data selection and JavaScript execution, not browser layout or user visual acceptance. Historical readiness evidence remains accepted:

- `docs/project/evidence/distance-readiness-2026-11-03.md`
- `docs/project/evidence/distance-readiness-probe-2026-11-03.py`
- `docs/project/evidence/distance-backend-contract-probe-2026-11-02.md`
- `docs/project/evidence/distance-spec-grill-review-2026-11-02.md`
- confirmed S4 manifest/result under `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/`

## Actual input limitation and remaining acceptance

The final package is `outputs/design/group_distance_ifc/run_v1/`; its preview is
`preview/index.html`, with `source_plan.svg` and two representative PNGs. All 37
actual group unions are outside confirmed S4: the smallest group X bound is about
10.45 m in the common translated view, beyond S4's 4.7 m right bound. All 666
Euclidean readings are computed, while all 666 hybrid results are `outside`.

The 121 × 47 grid at explicit 0.1 m spacing has 5651 established occupied cells
and 36 outside cells. The sole source covering every occupied cell is IfcSlab
`ifc-object:2mbfCNlr9T48ZweNBN3dyn`; there are no free/unknown cells, graph
nodes/edges/source searches or selected routes. This records the consequence of
the confirmed input selection and whole-height occupancy semantics, not a failed
Dijkstra run. The current run does not establish useful-route correctness, active
37-source route performance, access/tie/unknown/conditional route behavior,
continuous shortest paths or user visual acceptance. No slab exclusion or domain
expansion is permitted without a new design decision.

Complete artifact reconciliation and output-only full-scope visualization are
recorded in [IFC execution evidence](../../project/evidence/group-distance-ifc-v1.md).
`.18.8` and `.18.10` remain open. The owner may show the actual full IFC/S4 preview
for user review, but willingness to review or owner PNG inspection is not acceptance.
