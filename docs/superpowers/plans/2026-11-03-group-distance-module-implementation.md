# Group distance module implementation plan

Date: 2026-11-03  
Status: **Implementation retained; prior S4 selection superseded; intended hall + left passage confirmed; corrected unreachable run and preview retained; useful routes and user review open**

## Goal and boundary

Implement the frozen group distance module against one scene-view handoff. Keep the two raw readings separate: centroid-to-centroid Euclidean distance and centroid/free-space hybrid distance. Preserve pair-local state, route lineage, source identity and the complete unordered scope. Do not add a field package, distance-to-support transform, scheduler, cache service, or generic export layer.

The pinned IFC is `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` with SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`. The historical, now-superseded S4 handoff is the manifest/result pair under `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/`; never consume its failed `domain_result.json` as confirmed domain input. The implementation must resolve scene geometry once and keep coordinate translation in that handoff path, with no second projection.

## Current user-selected domain correction — 2026-11-03

The user explicitly corrected the earlier S4 selection using a red outline: the
intended analysis domain is the **right furniture hall plus its left connecting
passage**. The prior narrow S4 room and `run_v1` outside-only result are historical
execution evidence for the wrong selected domain, not the user's intended domain
or accepted result. The prior P3 confirmation execution remains recorded; its
selection is superseded. Independent worker/reviewer audits identify existing source-wall candidate S3 as
the matching hall plus passage. Original-request candidate identity is
`ec4599e3308aea74bc6766185d1fbee6f3b8b127fb0ff1fb6c950e9edb06ebc0`,
original-request version `inferred:S3:eabc9c10f7dd41da9d136f1dd6672dc459e1e8df84907f56f4c22f6e1fbdf3e4`.
Its area is `207.24092382549588 m²`; all 37 group projections have positive-area
intersection. The original request was refused with `unresolved_local_aperture`:
A22 on the diagonal wall retains a measured residual of `3.4968646007715876 mm²`.
The owner selected the existing per-request `aperture_residual_tolerance_m2=1e-5`
(10 mm²) policy, documented in the [residual-tolerance evidence](../../project/evidence/d6-inner-space-residual-tolerance.md).
Preparation was provisional with unchanged `207.24092382549588 m²`, zero-hole
geometry. A22 remains `above_area_budget=true`, `significant_residual=false`, and
`scenario_closed=false`; the separate `aperture_area_budget_m2=1e-6` (1 mm²)
opening-qualification budget is unchanged. This uses existing request policy,
with no global/default/schema change, geometry repair, or closure override.
Changing that policy changes request identity; the original version above is
identification history. The fresh confirmation is accepted and active at session
revision 1. The manifest/result agree exactly on domain and confirmation binding:

- Request: `7ef6f9024a63aead017fb1cda20db92c9e2ed261ddc73b899e3c7a9ed67a31c3`.
- Candidate: `908856c940ec7e0ffa25cb9157b7a8712b8d070edc7eabe3eb92ac4b8cbbf0f6`.
- Version: `inferred:S3:9e209ac62b6e4748246e2276b67b9756d62fb0f5a0c7cad368ada4f95f3cabaf`.
- Domain: `selected:86410d576017fa2d62e2cc1e1a5159143e9082e74e09186c36d9e8497e17f87a`.

Evidence: `outputs/design/group_distance_ifc/domain_correction_inspection/confirmed_domain_manifest.json`
and `confirmed_domain_result.json`. The recorded `user-red-outline-s3-20261103`
action executes the user's explicit hall/passage selection; the prior A22 refusal
is retained in the manifest. The result has no session conflict or invalidation.

S3's inferred floor support is not qualified for occupancy exclusion; whole-height occupancy may still prevent routes.
Do not guess a candidate ID, substitute a furniture bbox, or reuse the superseded
S4 identity as current. Identification evidence is `outputs/design/group_distance_ifc/domain_correction_inspection/candidate_report.json` and `s3_candidate_intent_comparison.png`; use the fresh confirmed bindings above for the corrected run.

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
- [x] `.18.7` Published corrected S3 preview at `run_v2_corrected_domain/preview/index.html`, with complete matrices and 666 readable pair/status locators. Independent artifact review verified 12 runner/preview hashes, the locator bijection, SVG viewer, S3 header and both PNGs. No hybrid route is present; this records presentation and artifact integrity, not user visual acceptance.
- [ ] `.18.8` **Partially verified:** corrected expected/observation/index/visual sets reconcile at 666 each with zero missing/duplicate IDs, and artifact hashes/locators were independently reviewed. Selected path/node/edge checks execute 0 cases because the corrected graph has zero nodes and edges. Useful real-route connectivity, access, lineage and route-arithmetic validation therefore remains open; the all-unreachable result does not pass this item.
- [x] `.18.9` Corrected S3 state coverage recorded: 666 hybrid `unreachable`, 666 Euclidean `computed`, 21,064 established occupied samples and 3,378 outside samples; 0 free/unknown, graph nodes/edges/searches or routes. Other hybrid status/access/tie/conditional route branches remain spatially unobserved. The slab is retained under unchanged whole-height occupancy.
- [ ] `.18.10` User visual review remains pending for the corrected full-scope S3 preview. Independent artifact/PNG review is not user acceptance. Master `.18` stays open for useful real-route validation and user acceptance.

**Delegated prerequisite for `.18.8` — 2026-11-03:** At the user's request, chat **自由空间生成与缓存对接** (`01a1a257-c569-7161-b8b7-b583372d4c6f`) owns free-space generation/cache investigation and direct user discussion, with completion handoff to distance owner `01a17389-9f50-7700-a8d7-c2e0ad7b3d09`. Its isolated jj workspace is `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache`, change `vvnuuksk`, parent `9c0b024b`; the six-file path-band draft is excluded and the owner's files are untouched.

Investigation found the existing answer to support handling: the historical whole-height inspection preserves the upstream `excluded_support_slab` declaration; the general live seam validates a specific `SupportBinding` and changes only request-local interior occupancy. Missing or stale binding retains the slab. Current inferred-wall-domain `evaluate_domain_request` returns `support_status=not_applicable`, while authored IfcSpace exposes the support binding. The historical excluded slab has the current slab GUID but another IFC hash/domain, so it is not a current validated declaration. Existing full free-space serialization, atomic result writing and exact ResultRef/sample reading can be reused; cache-key selection and distance consumption remain unconnected, and plane revision still affects the request semantic key. No new query policy or height band was selected.

Verification on the pre-draft baseline used the existing Pixi environment with the main checkout's embedded OCTA source on `PYTHONPATH`: `test_unbound_floor_remains_occupancy`, `test_live_execution_uses_exact_mesh_and_request_scoped_support`, `test_analysis_domain_support_mass_is_not_a_walking_blocker_when_overlapping_body_band`, `test_unidentified_analysis_domain_keeps_shared_wall_and_column_occupancy`, `test_key_excludes_request_ids_and_display_but_tracks_semantics`, and `test_live_and_embedded_results_use_same_reader_without_sidecar` — **6 passed in 3.58s**. The first collection lacked the untracked embedded OCTA tree; supplying its existing path resolved collection without installing dependencies or changing source. No new scene, IFC extraction, free-space map or route was generated. `.18.8`, `.18.10`, `.18.C4` and parent `.18` remain open; no completion handoff has been sent.

**User free-space clarification and implementation audit — 2026-11-03:** The
user specified floor-surface-to-analysis-plane height projection, with projected
domain intersection including boundary-touching objects. The exact plane cut
remains a separate interface. The recovered UI already has
`ground_to_analysis_plane_band`; `_make_analysis_request` maps it to local-Z
`finite_height_band`, and the request executor uses existing clipped projection
geometry. This entry hard-codes world Z=0 instead of consuming the separately
available selected-slab upper-surface datum. Exact domain cell clipping exists;
a unified inclusive object-scope handoff does not. Keep object participation
separate from positive-area occupancy. Current corrected S3 retained input is
explicitly whole-height with no band; the earlier support-exclusion investigation
does not prescribe the fix or satisfy the clarified rule. No algorithm changes
were made in this audit.

Eight existing test selections (11 parametrized cases) passed in **5.55s** under
the same Pixi environment and OCTA path setup above: ground-band UI conversion,
request local-Z occupancy, rotated-plane band projection, local high-part
projection, slab/storey upper-surface resolution, unsupported slab surface
rejection, partial-domain/hole clipping, and independent absolute-world-Z section.
These checks verify existing capabilities, not a fresh S3 result. Cache completion,
useful routes and user visual acceptance remain open.

### User correction continuation within .18

The `.18.2–.18.6` S4 adapter/run details above remain historical. Corrected S3
preview/state recording is captured by `.18.7`, `.18.9` and `.18.C1–.18.C4`.
Parent `.18`, useful-route validation `.18.8`, and user visual acceptance
`.18.10` remain open.

- [x] `.18.C1` Identified existing candidate S3 as the right furniture hall + left passage in independent worker/reviewer audits. Area `207.24092382549588 m²`, all 37 groups intersect; original candidate identity/version and retained A22 diagnostics are recorded above. Evidence: `outputs/design/group_distance_ifc/domain_correction_inspection/candidate_report.json` and `s3_candidate_intent_comparison.png`. This checks identification only, not confirmation or acceptance.
- [x] `.18.C2` **Corrected S3 confirmation frozen (2026-11-03):** `confirmed_domain_manifest.json` and `confirmed_domain_result.json` under `domain_correction_inspection/` agree on the accepted/active session revision 1, exact domain, current binding and candidate version recorded above. The explicit `user-red-outline-s3-20261103` action represents the user-selected hall/passage. Area is unchanged at `207.24092382549588 m²`, holes 0; original A22 refusal and superseded S4 history remain retained. The existing explicit 10 mm² residual request policy retains A22 diagnostics and the separate 1 mm² opening budget. No geometry repair, slab exclusion, or height-policy change is authorized.
- [x] `.18.C3` **Corrected cached run retained (2026-11-03):** `outputs/design/group_distance_ifc/run_v2_corrected_domain/` contains the actual run manifest, coverage report and spatial-scope audit. The independently audited rebind supplies 37 groups and 343 occupancy records after 10 exact boundary-member exclusions through the existing resolver; the pre-rebind 353-record count is retained as history only, and the slab remains preserved. The 121 × 202 grid at 0.1 m has all 37 centroids inside; source/hash bindings agree, and common-translation polygon symmetric difference is at most `2.57e-16 m²`. All 666 Euclidean values are computed; all 666 hybrid observations are `unreachable`, with null values/routes. Expected/observation/index/visual locator sets reconcile at 666 with no missing/duplicate IDs. Combined kernel/delivery checks passed 19 tests in 14.68s before a metadata-only occupancy-count correction; post-correction focused delivery checks passed 6 tests in 17.71s. The correction changed current count/hash metadata only, not metrics or kernel output. This completes corrected execution and actual-state recording, not useful-route validation.
- [ ] `.18.C4` **Preview delivered; user review pending:** `run_v2_corrected_domain/preview/index.html` contains all 666 pair locators and two representative PNGs of the corrected green S3 hall/passage and furniture. The final independent artifact review verified 12 runner/preview hashes, the 666-pair locator bijection, SVG viewer, S3 header and PNGs. The preview records no S4 label and does not recompute distance. No hybrid route is present. Obtain user review before closing this item or `.18.10`; `.18.8` useful-route validation remains open.

### Corrected S3 run and retained limits

The current intended-domain output is `outputs/design/group_distance_ifc/run_v2_corrected_domain/`;
`run_v1/` remains superseded-S4 history. Evidence is `run_manifest.json`,
`coverage_report.json`, `spatial_scope_audit.json` and the [IFC delivery record](../../project/evidence/group-distance-ifc-v1.md).
The common view offset is `[-5.150000095367432, -0.30000001192092896]`;
the unchanged S3 area is `207.24092382549588 m²` and view bounds are
`(0, 0)..(20.149999141693115, 12.000000178813934)`. Domain/grid/query/occupancy
fingerprints are fresh for this binding, rather than copied from S4.

Of 24,442 samples, 21,064 are established occupied and 3,378 outside; none are
free or unknown. Every occupied sample includes retained IfcSlab
`ifc-object:2mbfCNlr9T48ZweNBN3dyn` among its source refs. Both graphs have
zero nodes, edges and source runs. This run demonstrates `unreachable` under the
existing whole-height occupancy policy; it does not establish spatial routes,
access selection, ties or conditional/unknown paths. Inferred floor support does
not authorize slab exclusion, and no height-policy change was made.

One corrected kernel call took `334.9034131 s` with tracemalloc peak
`48,687,026 B`. The retained-input process took `352.656185 s`, with Windows
peak working set `336,601,088 B` and peak commit `329,084,928 B`. These are
cached-rebind/one-kernel measurements, not full IFC parse cost or an active-route
benchmark. No corrected same-bundle replay was performed; normalized result
SHA-256 is `db9cae4be1b8d7628a5a64ffe92ed9ee5efe963a4bfeff53ae3d379780891b93`.
Source bytes/hash remain unchanged before/after. Parent `.18`, useful-route
validation `.18.8`, user visual acceptance `.18.10` and `.18.C4` remain open.

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
failed or unobserved items accurately. Text readiness and the corrected S3
666-pair execution, peak resources, source/hash reconciliation and full-scope
preview are recorded. All hybrid pairs are unreachable under unchanged whole-height
occupancy, so useful real-route validation and user visual review remain open
acceptance gates. Finish the implementation only when real generated artifacts are
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

## Historical superseded-S4 run and remaining acceptance

The historical wrong-selection package is `outputs/design/group_distance_ifc/run_v1/`; its preview is
`preview/index.html`, with `source_plan.svg` and two representative PNGs. All 37
actual group unions are outside confirmed S4: the smallest group X bound is about
10.45 m in the common translated view, beyond S4's 4.7 m right bound. All 666
Euclidean readings are computed, while all 666 hybrid results are `outside` for that superseded selection; none of these results establish the corrected hall/passage outcome.

The 121 × 47 grid at explicit 0.1 m spacing has 5651 established occupied cells
and 36 outside cells. The sole source covering every occupied cell is IfcSlab
`ifc-object:2mbfCNlr9T48ZweNBN3dyn`; there are no free/unknown cells, graph
nodes/edges/source searches or selected routes. This records the consequence of
the confirmed input selection and whole-height occupancy semantics, not a failed
Dijkstra run. This historical S4 run does not establish useful-route correctness,
active 37-source route performance, access/tie/unknown/conditional route behavior,
continuous shortest paths or user visual acceptance. The corrected S3 run also
has no routes because unchanged whole-height occupancy leaves no free graph cells;
it does not validate route behavior. The user has now corrected the selected wall domain; use the matching real wall
candidate and explicit confirmation, not an arbitrary geometric expansion. Occupancy
policy changes such as slab exclusion still require a separate design decision.

Complete artifact reconciliation and output-only full-scope visualization are
recorded in [IFC execution evidence](../../project/evidence/group-distance-ifc-v1.md).
`.18.8` and `.18.10` remain open. The corrected S3 preview is available at
`outputs/design/group_distance_ifc/run_v2_corrected_domain/preview/index.html`;
user visual acceptance requires the user's review and cannot be inferred from the
independent artifact review.
