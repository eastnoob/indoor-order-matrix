# Group distance IFC v1 execution evidence

Date: 2026-11-03. The original S4 package below is preserved historical wrong-selection evidence, superseded by the user's red outline selecting the right furniture hall and left connecting passage. The corrected S3 delivery is recorded at the end. Useful real-route validation and user visual acceptance remain open.

## Source and confirmed coordinate handoff

- IFC: `D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`.
- Bytes: `408618044`; SHA-256 before and after: `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`.
- Confirmed S4 inputs: `outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z/s4_confirmed_manifest.json` and `s4_confirm_result.json`; the failed `domain_result.json` is never loaded.
- The canonical capture is a wrapper: the loader consumes its `capture` member. Wrapper source/plane, active confirmation, request/candidate/domain, mesh provenance and structural source revision are cross-checked.
- The confirmed domain mesh is attached to the capture's Neutral Scene before exactly one `analysis_scene_view`. Projected domain and complete group rings receive its common offset; physical occupancy already carries that offset. No second projection or native triangulation occurs.
- Camera origin: `(0, 0, 4.599999904632568)` m, identity basis. Common view offset: `(-0.30000001192092896, -0.30000001192092896)` m. S4 area: `56.04000065088272` m². View bounds: `(0,0)..(4.699999988079071,12.000000178813934)` m.
- `359` capture/source records, `353` physical occupancy records, `0` unresolved occupancy owners, `37` available whole-group projections. Missing declared members/projections would prevent a computed whole-group centroid.
- Explicit diagnostic spacing `0.1` m gives `121 × 47 = 5687` cells; rows advance plane Y and columns plane X. It is not body-width calibration.

## Actual result and limits

The result retains all `37` groups and all `666` unordered pairs. All `666` Euclidean readings are computed. All `666` hybrid readings are `outside` with null values and null routes: every actual group union has zero positive-area intersection with S4. The smallest group X bound is about `10.45` m in the common view, beyond S4's `4.7` m right bound.

All `5651` in-domain field samples are established occupied. Their sole covering source is `ifc-object:2mbfCNlr9T48ZweNBN3dyn`, mesh `ifc-mesh:2mbfCNlr9T48ZweNBN3dyn`. A bounded lookup of that exact retained canonical record confirms `IfcSlab`. The other `36` samples are outside. Occupancy and domain were preserved; there is no inferred slab exclusion or domain expansion.

Both observed and optimistic graphs have `0` nodes, `0` edges and `0` source runs. Selected route/node/edge checks therefore execute `0` spatial cases. `computed`, `partial`, `unknown`, `unreachable`, `invalid`, `not_available`, conditional-route behavior, access-marker rendering and tie behavior remain spatially unobserved. No synthetic geometry or preset distances were introduced to manufacture those branches. This run cannot establish useful real-route correctness, route performance at 37 active sources, continuous shortest paths, or user visual acceptance.

## Final artifacts and reconciliation

Final package: `outputs/design/group_distance_ifc/run_v1/`.

- `observations.json`, `pair_index.json`, `run_manifest.json`, `coverage_report.json`.
- `input_bundle.json`, `scene_geometry.json`, `adapter_audit.json`, `spatial_scope_audit.json`.
- `preview/index.html`: all `666` selectable pair/status locators, full unordered row list, symmetric Euclidean/hybrid matrices, explicit null/not-applicable diagonal and group-ID mapping.
- `preview/distance_rows.csv`, `pair_views.json`, `source_plan.svg`, `representative_01.png`, `representative_02.png`, `coverage_report.json`.
- `viewer_execution_check.json`: final viewer JavaScript executed for all `666` actual pair selections using a minimal DOM host. This checks syntax and recorded-data selection, not browser layout.

The observation/index/expected/visual pair sets are a bijection with `666` unique IDs, no missing/duplicate IDs, and readable indexed locators. Metric values are finite when present. Renderer input hashes are checked; it does not calculate distances or infer routes. It draws fixed centroids/gray Euclidean lines, recorded red routes, separate purple dashed endpoint offsets, access-cell squares, shared edges and proxy markers when those records exist. Both PNGs were inspected and show S4 left of all furniture with the correct outside status and absent hybrid route.

Normalized same-bundle result SHA-256: `db188cdd9f555041b92ef36a732d6ac70e67c9049a1059dce3bdac25ea093249`, identical on the equivalent replay. Runtime/allocation diagnostics are excluded from that normalized hash.

| Artifact | SHA-256 |
| --- | --- |
| observations.json | `ac03dd15b4c227811f6385391c2cd5dde47baec2ab1743f7ba02deb9fa76694b` |
| pair_index.json | `ce8f243275a0428e8ce4607af67df30b0b9f68b8354fa11bc25088feabdda181` |
| run_manifest.json | `a09e0796e4e72a04c7a1c1532fb8aab777b60bd1210414b0c245726e895f5186` |
| input_bundle.json | `e23ce49c8e36579500d8ad36887b6406c93ff9dc741b43b4ebe50be8afd57d3c` |
| scene_geometry.json | `a00f9482146224a0d738d9296565ec967c00f2d23bbcc24313a1e77eb2d87305` |
| preview/index.html | `bd68b15e1071841341609ee762354ea58b7aecfbae74c3d7694254e780548132` |
| preview/representative_01.png | `ce0d401fa3895c3de6d7a148aecc477aad5b45616a13e6e28d6eb2fc38e2c13b` |
| preview/representative_02.png | `760073699160d4c509e4db307ecfa550f4a206a5f1132c7b9f2e8924b6bbe97a` |

## Final independent review scope

Decision: **APPROVE the bounded Euclidean/outside delivery**, not full `.18` acceptance. The review verified that retained dependency/source/plane/frame/domain/offset claims are validated before the missing plane binding is finalized, and that access/proxy overlays are implemented. All `666` locators and all `14` artifact hashes were verified. With `0` selected routes, runtime path/access/tie spatial validity remains unobserved; useful real-route validation and user visual acceptance stay open.

The owner separately ran guarded `pixi run pytest test/test_group_distance.py test/test_group_distance_ifc_delivery.py -q`: **17 passed in 5.30s**, exit `0`. This fresh combined check was supplied to the documentation worker and was not rerun by it. Owner inspection of `preview/representative_01.png` confirmed S4 left of all furniture; it is not user visual acceptance.

## Runtime and memory scope

The full capture/adapter process plus two implementation-era kernel calls took `751.2994114` seconds, with actual Windows process peak working set `2825302016` bytes and peak commit `2877648896` bytes. These process counters include native allocations and the full one-time capture/projection cost.

The definitive final-kernel process reused the retained same-source planar bundle: `101.6013874` seconds through two kernel calls, peak working set `205701120` bytes, peak commit `195854336` bytes. Its first kernel call took `47.2163139` seconds with `23744479` bytes tracemalloc peak. Tracemalloc covers kernel Python allocations, not complete native/process memory. The two process scopes are retained separately in `run_manifest.json` / `adapter_audit.json`; the final process is not presented as a fresh full-capture cost.

Before the retained bundle's missing implementation-era `analysis_plane_fingerprint` was added, every saved dependency fingerprint and grid domain/occupancy claim was checked. The runner then checked the canonical plane against the confirmed manifest, all frame/domain/query/revision bindings, source/capture hashes, origin offset and translated S4 geometry. Only that explicitly identified missing binding was finalized; geometry was not reprojected or changed.

## Commands and focused checks

All commands run in `D:/PROJECTS/understandOtherPackage/order_analyzer_group_distance`, with `PYTHONNOUSERSITE=1`, `PYTHONPATH=.` and the Pixi locked interpreter.

The full parse/project CLI was run into retained `run_v1_attempt02`:

```powershell
pixi run python scripts/design/group_level/run_group_distance_ifc.py --source-ifc D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --s4-dir outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z --spacing-m 0.1 --output-dir outputs/design/group_distance_ifc/run_v1_attempt02
```

The definitive run used `run(..., parsed_input=Path('outputs/design/group_distance_ifc/run_v1_attempt02/input_bundle.json'))` with the same source/S4/spacing and fresh `run_v1` directory, then performed the equivalent immutable-bundle replay. This avoids repeating the large capture parse/projection solely for a kernel binding completion. The normal CLI requires all four flags and a fresh output directory.

```powershell
pixi run python scripts/design/group_level/render_group_distance_preview.py --run-dir outputs/design/group_distance_ifc/run_v1 --output-dir outputs/design/group_distance_ifc/run_v1/preview
pixi run pytest test/test_group_distance_ifc_delivery.py -q
node outputs/design/group_distance_ifc/verify_viewer.cjs
```

Focused result: `4 passed in 5.48s`. Checks cover confirmed source binding, actual complete pair/path reconciliation, all renderer locators and refusal of changed retained source metadata before binding finalization. The renderer publishes into `RUN_DIR/preview` because the runner's pair index already declares those exact locators. Python compile checks and final JavaScript execution pass.

Preserved attempts: `run_v1_attempt01/failure.json` (wrapper passed directly to capture constructor); `run_v1_attempt02/` (full one-pass adapter and earlier imported kernel); `run_v1_attempt03_retained_binding/failure.json` (frozen tuple vs JSON list comparison); `run_v1_attempt04_before_retained_validation/` (final kernel results before strengthening retained-claim validation). The final `run_v1` was generated after that validation fix. No attempts, input IFC bytes or prior outputs were overwritten.

No native Blender launch, dependency addition, package-formula change, domain selection change, occupancy-policy change, version mutation, commit, push or merge was performed by this delivery worker.

## Corrected S3 wall-domain confirmation — 2026-11-03

The user explicitly selected the right furniture hall and left connecting passage. Retained real-wall candidate S3 exactly matches that intent: area `207.24092382549588` m², zero holes, all 37 group centroids inside. Its exact outline comes from the retained native wall geometry, never from image tracing or furniture bounds. The old S4 package and original IFC remain preserved.

At the former 1 mm² residual tolerance, S3 was refused for A22: `3.4968646007715876` mm² on watertight, manifold, section-qualified wall `ifc-object:3R_rUQk_TQmBN0VHbYhNx6`. It has no authored opening reference, no treatment and only one jamb side. Independent review measured a `5.092860406` m × `1.473987750` µm residual; native endpoint X `25.209487915039062` has binary32 next-step spacing `1.907348633` µm, so the maximum measured width is approximately `0.772794` ULP. This supports the existing mesh-sliver policy; it does not prove a unique numeric cause.

The owner authorized this corrected request alone to use the existing `tolerance_mm2=10` parameter, matching `DEFAULT_APERTURE_RESIDUAL_TOLERANCE_M2=1e-5` and the established residual-tolerance evidence. The existing path is `StructuralContext.b4_parameters` → `evaluate_domain_request` → `tolerance_m2` → `aperture_residual_tolerance_m2`. Physical `aperture_area_budget_m2=1e-6` and contact distance `1e-6` m stay unchanged. No global default, shared API, wall mesh, opening geometry or occupancy semantics changed. A22's exact geometry remains in diagnostics: `above_area_budget=true`, `significant_residual=false`, `scenario_closed=false`.

Fresh existing-service prepare and confirm artifacts are retained in `outputs/design/group_distance_ifc/domain_correction_inspection/`: `s3_prepare_request.json`, `s3_prepare_result.json`, `s3_confirm_request.json`, `confirmed_domain_result.json`, `confirmed_domain_manifest.json`. The reducer reports `accepted` / `active` with handoff executed; no status override was used.

- Candidate version: `inferred:S3:9e209ac62b6e4748246e2276b67b9756d62fb0f5a0c7cad368ada4f95f3cabaf`.
- Candidate identity: `908856c940ec7e0ffa25cb9157b7a8712b8d070edc7eabe3eb92ac4b8cbbf0f6`.
- Source revision: `c4760b58f44c4e5ae5504180f2f9a1082fab608d2ac418b2cde07edbfc63c007`.
- Frame: `e19642c74e9ff5dae44caea019dc8ec8dc366074bba05f8128f094a01be0aba8`.
- Request: `7ef6f9024a63aead017fb1cda20db92c9e2ed261ddc73b899e3c7a9ed67a31c3`.

The runner authenticates every old saved dependency fingerprint and the source/camera/frame/query/domain/offset/capture/confirmation claims before rebinding. It checks the selected candidate identity, exact outline and small confirmed support mesh projection. Groups and retained occupancy receive only the common translation delta `(-4.850000083446503,0)` m, yielding new origin offset `(-5.150000095367432,-0.30000001192092896)` m. No IFC parse or full furniture projection is repeated.

Domain membership is reconciled separately through existing `_resolve_boundary_member_ids`: the one old S4 boundary member is a proven subset of S3's eleven members. Exactly ten sole-owner records newly scoped out by S3 are removed; no formerly scoped member needs restoration. Mixed/missing ownership or an old boundary no longer in the new set would refuse this cache path. All 343 remaining occupancy records preserve their ownership/representation facts, including the slab. Exact source IDs and resolver diagnostics are retained in `rebase_preflight.json` and the new adapter audit. This is the existing selected-domain boundary policy, not an arbitrary physical exclusion.

`slab_source_audit.json` records retained native `IfcSlab` `ifc-object:2mbfCNlr9T48ZweNBN3dyn`: 663 vertices, 1322 triangles, world Z `[-0.30000001192092896,0]` m. Whole-height planar occupancy still covers the corrected domain; the geometric difference is only `7.888609052210118e-31` m² numeric roundoff. Camera origin Z remains `4.599999904632568` m, B4 datum `0` m and cut height `1.5` m. No support binding or height-policy extension was introduced.

Focused corrected-delivery checks: `pixi run pytest test/test_group_distance_ifc_delivery.py -q` → **6 passed in 20.83s**. They include rejecting a substituted real scope, forged old plane claim, exact scope-derived 343-record membership, unchanged slab inclusion and translated real geometry. Independent reviewer approved the bounded corrected handoff; useful-route and user visual acceptance remain open.

## Corrected S3 result and preview

Final package: `outputs/design/group_distance_ifc/run_v2_corrected_domain/`. All **666 Euclidean distances are computed**. All **666 hybrid results are `unreachable` with null values and null routes**. The corrected domain contains every actual group centroid. At 0.1 m spacing, the `121 × 202 = 24442` samples comprise `21064` established occupied samples and `3378` outside samples; every occupied sample includes slab source `ifc-object:2mbfCNlr9T48ZweNBN3dyn`. Both graphs have zero nodes, edges and source runs. This corrects the domain intent but does not establish useful route/access/tie behavior.

The one corrected kernel call took `334.9034131` s and `48687026` B tracemalloc peak. The cache-validating runner took `352.656185` s, with process peak working set `336601088` B and peak commit `329084928` B. The explicit corrected-run replay was skipped as authorized; prior unchanged-kernel determinism evidence remains historical and is not claimed as a corrected-bundle replay.

`preview/index.html` contains all 666 selectable pair views, complete rows, symmetric matrices and null/not-applicable diagonal; its actual candidate label is S3. Both representative PNGs were inspected: the green outline is the right furniture hall plus left passage, furniture remains visible, fixed-centroid Euclidean lines are gray, and no route is invented. User visual acceptance remains pending. The unchanged viewer JavaScript was also executed against all 666 corrected selections under the minimal DOM host (`viewer_execution_check.json`); this is not native browser-layout acceptance.

`changed_request_invalidation_check.json` demonstrates that the existing reducer invalidates the fresh active confirmation when the prior 1 mm² request identity is substituted; it exposes no domain. This bounded check uses retained factual source records and original exact B4 diagnostics without source projection.

| Corrected artifact | SHA-256 |
| --- | --- |
| observations.json | `5462cacf32e7fc6d39a57f2026111bd80ea5f48dc0787a41ae50bbb7fd221066` |
| pair_index.json | `ce8f243275a0428e8ce4607af67df30b0b9f68b8354fa11bc25088feabdda181` |
| run_manifest.json | `56f2076539907716d42b0c17414cd806d273eb2f04fffbdaf20a7861a9c5e3f1` |
| input_bundle.json | `76d772c8080ea8f3b43b5da5325faadcc453d2e4b877b0f93141e0ed6dcf279f` |
| scene_geometry.json | `dcfa158aa8563e086b063f0ab38d99b125ba2a2197ab25264467b2fd78b3fa9d` |
| adapter_audit.json | `5c2b845c8b1175bc6cb4650ee5418dac5ce2f841abd92ed6db77a3ee044bb42b` |

Corrected normalized result SHA-256: `db9cae4be1b8d7628a5a64ffe92ed9ee5efe963a4bfeff53ae3d379780891b93`. Source IFC bytes and SHA-256 match before and after. Generic `--domain-dir` retains legacy `--s4-dir` compatibility; `--parsed-input`, `--previous-domain-dir` and `--skip-replay` make the authenticated corrected cache run explicit.

Combined kernel/delivery checks passed **19 tests in 14.68s**. The final independent artifact review verified hashes, 666 locator bijection, S3 labels and the real hall/passage PNG. A metadata-only correction then made the current adapter count explicitly 343 and retained the old count 353 in `cache_rebind`; prior metadata bytes are preserved in `domain_correction_inspection/metadata_count_correction/`. No metric or kernel output changed, and coverage hashes were updated.

## Exact free-space result continuation — 2026-11-04

Workline: jj workspace `free-space-distance-bridge`, absolute path
`D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge`,
base `bb46ac5d` (accepted-board ancestor `975f472f`), change `mlkkrmsp`,
read-only inspected working revision `f3ecafc5`. Root remains the sole version
writer; the implementer does not commit, push, merge or edit the conflicted
distance workspace.

The exact accepted source is `free_space_run:fe3243c13b3f45daac8744efc46f3962`,
digest `a22de58adc39c241ccb514afd52f2c1b7bbf4819f7ffb93d6a125aac92f4c120`,
from the sibling `order_analyzer_free_space_cache` workspace. Consumer expectations
come from its producing `request.json` and external
`outputs/design/free_space_prerequisite/verification/native-free-codec-restored-publication.json`.
The retained read is explicitly historical and makes no live-currentness claim.
The authenticated domain mesh matches producer source revision
`4d9273b2231462a9e0429bd349199754f4ff3b3589f61fada0da940863133e1b`.
The adapter projects only the same-capture authored group and domain geometry,
uses zero XY offset, and never regenerates occupancy. Board geometry/materials
are not calculation inputs.

The first implementation attempt was cancelled before a completed kernel result:
`outputs/design/group_distance_ifc/run_v3_attempt01_expanded_metadata/` preserves
its input, audit and interruption record. Flat source IDs occupied
`178,583,285 B` of compact JSON and flat support `18,698,660 B`; pretty
`input_bundle.json` was `302,980,274 B`. There are only 205 unique source lists,
while a known-empty cell references all 343 source IDs. The final adapter keeps
those lists once in `free_space_result.source_ids`, with integer references from
each cell. It stores common support context once, local cell support geometry
inline, and the exact ResultRef/row/column locator for complete original support
and provenance. The whole-height constructor route and its fingerprints remain
unchanged. The final real run is retained under
`outputs/design/group_distance_ifc/run_v3_finite_band_result/`.

Implementer focused checks, cwd above, locked Pixi interpreter:

```powershell
$env:PYTHONPATH='.;D:\PROJECTS\understandOtherPackage\order_analyzer\OCTA_toolbox-master'
$env:PYTHONNOUSERSITE='1'
pixi run pytest test/test_group_distance.py test/test_blender_analysis_session.py test/test_free_space_distance.py -q
# 154 passed, 5 skipped in 35.54s; exit 0
```

One skip is the absent optional historical S4 plane artifact; four depend on the
not-yet-complete real distance run. The first focused attempt exposed that missing
historical fixture; the existing test now follows the same missing-artifact policy
as retained delivery tests. These skips are not positive route evidence.

Initial frozen implementation candidate (physical bytes; final acceptance follows below):

| File | SHA-256 |
| --- | --- |
| `features/group_distance.py` | `2df84a88cd7769418048bb4631b3d2f7c8a0d05a841887621cf2df1f604e0bd0` |
| `adapters/blender_analysis_result_wire.py` | `53712abcfeb6f77a5c1bb0e4317b05d063fbebdb30aa8395f4f52ffa5af06197` |
| `adapters/free_space_distance.py` | `3b1d22b03e04a78b4caaa85ca84c69693f8c57a5f16ffd63d133cce6451ad065` |
| `scripts/design/group_level/run_group_distance_free_space.py` | `1f2fc6f1afd9509e09e4fb75833ac3ada22a6f62d7c8b6e15cc7a0d634b8a95f` |
| `scripts/design/group_level/run_group_distance_ifc.py` | `3d886fdb8b19dcd9fbe40cbf4e1e227b9e5d4684a994be9df2ed9ad585f10005` |
| `test/test_group_distance.py` | `8ad4581b8a0933480617ddb745e94dbfcca63233ae15d6da7af9c2d206a7cbc4` |
| `test/test_blender_analysis_session.py` | `2c7dcc56d2b953cfcbbf0ae695abf595264e29adca8d0d6151466aaa003f58da` |
| `test/test_free_space_distance.py` | `2585d447bf9849198a4e4a1a8546550fb13b5cae911c73162ba724866056d82a` |

Visual decision: reuse the accepted S3/plane/board alignment; require a route
overlay from the new actual distance output to inspect source-to-result placement.
Independent visual rendering is a separate owned file pair. User visual acceptance
`.18.10`/`.18.C4` remains open, regardless of automated or agent review.

### Stable v3 run and current preview

The final historical exact-result runner exited **0**. It preserved all 24,442
saved cells: 14,047 established `False`, 7,023 established `True`, 3,372 outside
`None`. It retained all 343 physical records and the complete 37-group scope.
The exact-domain center rule admits 13,800 graph nodes from the known-empty cells;
both graphs contain 26,301 edges and execute 36 source-batched searches. All
**666 Euclidean and 666 hybrid distances are computed**, with 666 recorded routes.
The runner validates 48,734 selected nodes and 48,068 selected edges, exact cell
lineage, four-neighbor/domain coverage, endpoint offsets, finite metrics and
binary64 arithmetic. No numerical-contract failure or tie uncertainty was observed.
Unknown/conditional/unreachable route branches are not claimed from this scene.

Immutable-bundle replay is equal, normalized SHA-256
`2a09ed17756b9472f31373df686d7c0abec3455901de58bdcc7139f0000a11b7` on both
executions. The original producing request, exact published result and external
receipt byte hashes match before and after. These are retained historical inputs,
not a current native IFC observation:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| producing `request.json` | 165881200 | `926db96864622024356df1aea715bce22b934af824ebcef44ef0aba0e7de3a90` |
| published `result.json` | 23560328 | `9bd16d2c007313dbdcafd101c4f1061c3d8ab892d7c1f261de2cb84f718d660a` |
| external native receipt | 54795 | `28eab9c49d9e65fba0add929c5422083f7f50753db31c89d63925cca371f33c2` |

The final shared-reference `input_bundle.json` is `46,572,507 B`, reduced from
the observed expanded attempt's `302,980,274 B`. The reported first-kernel runtime
is `131.4923575 s`, with kernel Python tracemalloc peak `369,269,693 B`. Full
runner time is `526.3187724 s`, including request/result decoding, group/domain
projection, both kernel calls, validation and output publication. Its process peak
working set is `3,692,367,872 B`, peak commit `3,718,479,872 B`; process counters
include native allocations and are distinct from kernel tracemalloc.

```powershell
pixi run python -m scripts.design.group_level.run_group_distance_free_space --free-space-result ../order_analyzer_free_space_cache/outputs/blender_analysis/jobs/fe3243c13b3f45daac8744efc46f3962/result.json --native-request ../order_analyzer_free_space_cache/outputs/blender_analysis/jobs/fe3243c13b3f45daac8744efc46f3962/request.json --publication-receipt ../order_analyzer_free_space_cache/outputs/design/free_space_prerequisite/verification/native-free-codec-restored-publication.json --allow-historical --output-dir outputs/design/group_distance_ifc/run_v3_finite_band_result
pixi run python -m scripts.design.group_level.render_group_distance_preview --run-dir outputs/design/group_distance_ifc/run_v3_finite_band_result --output-dir outputs/design/group_distance_ifc/run_v3_finite_band_result/preview
pixi run pytest test/test_free_space_distance.py -q
# 6 passed in 66.02s; exit 0
pixi run pytest test/test_group_distance_preview_payload.py -q
# 1 passed in 3.50s; exit 0
```

The preview command exits 0 with 666 selectable pair/route locators, complete
matrices, `distance_rows.csv` and two representative PNGs. An observed initial
HTML of `216,158,261 B` is preserved as `preview_attempt01_full_audit_payload/`.
Its compact observation payload included `134,065,752 B` of lineage and
`78,057,865 B` of routes, including `45,969,589 B` of cells and `28,481,404 B` of
edges unused by the viewer. The final HTML projects only fields consumed by its
existing JavaScript and is **7,171,746 B**. Complete `observations.json`
(`401,104,240 B`) and every numerical artifact remain unchanged. The actual payload
test proves the exact rendered metrics, audit, route points, access geometry and
arithmetic match the full observations, with no embedded unused lineage/cell/edge
audit arrays. The source label correctly identifies the native capture digest
rather than presenting it as an IFC byte hash.

| Stable v3 artifact | SHA-256 |
| --- | --- |
| `observations.json` | `8676973e7c63e84d21f3163b44731623b73d9119210cb2407d449b69e06062fc` |
| `pair_index.json` | `2b06694da532c22c9ed86a9a044b882845929bda823e56cdd8fd4a3199691ae6` |
| `run_manifest.json` | `8faaaf09e4920da3d9064f24239ad5cbd616111bb73096ab78f0f3d02fd6ef53` |
| `scene_geometry.json` | `ffb039ace9243a6e5695df5290a5942828a96874958abc74dc4f06ee40a28019` |
| `input_bundle.json` | `28e5304317ef52519d4c6d8c37ff17495032ec331f63e8333d7f15df72a1f93d` |
| `adapter_audit.json` | `839e54d91125ba2d04194a6918574c946b225687b4d76c7a24d8a5ff3518afe7` |
| `preview/index.html` | `afe4e146b73ad3fdcf3dbd534f55803275f70c65fb025c028a8a3260533144d9` |
| `preview/distance_rows.csv` | `a391d8c622e2656a6fa3637addb9ab17604eebb04247d4bdb4b6ec753426f0e0` |
| `preview/representative_01.png` | `0d19d1331718575e61dae5e72efbee12a2360d55018c597644c168d21146c364` |
| `preview/representative_02.png` | `aa7944691ee58a1465c02870d7f80d51f4bddacf6aa69dff74167fd9a6cfe24c` |

The original eight frozen core hashes above still match. Additional frozen caller
files are `scripts/design/group_level/render_group_distance_preview.py`
`83b4696b88855f582d4544f667e56949a8c5e66ed440fb799e803fb168cecccb` and
`test/test_group_distance_preview_payload.py`
`5ad6edb551c2fb13878414a4f19ac72b4ba9abfe38ecd6dece689ae8b8aa64cd`.
The new reader also accepts every saved fingerprint in the real historical
`../order_analyzer_group_distance/outputs/design/group_distance_ifc/run_v2_corrected_domain/input_bundle.json`
with `free_space_samples=None` and `height_band=None`; this direct compatibility
check exits 0 without recalculating a field. The local six historical delivery
tests skip because those historical outputs are not installed in this workspace;
they are not reported as passing renderer evidence.

The implementer inspected the first recorded-route PNG; it shows the expected
free-cell route and separate centroid offsets. Independent specification/quality,
actual artifact/viewer checks and the native recorded-route overlay remain owned
by separate agents. At the implementer freeze, `.18.8`/`.18.8a` awaited independent
acceptance; the final verdict follows below. User visual acceptance
`.18.10`/`.18.C4` remains pending. The older v1/v2 sections are preserved history;
v3 is the current numerical input and preview.

Independent interim evidence supplied by root before final verdict: the verifier
ran the six actual bridge tests, **6 passed in 66.68 s**, exit 0. Its direct reading
of the authoritative free-space cells independently checked all 666 routes,
48,734 selected nodes and 48,068 four-neighbor edges. `math.fsum` distance
reconciliation has maximum residual `3.552713678800501e-15 m`, within every
recorded rounding bound; graph and 36-source-search counts agree. These are actual
independent results, but do not alone close specification/quality acceptance.

The separate native renderer retained `native_route_board_v2/route-board.blend`,
`route-board.png`, `execution_receipt.json` and `preview_report.json` under this
v3 run. Root reports the frozen PNG SHA-256
`9141cd5fdaf525ba1cdb3f51de37db7f5388ba9afd05aec838d03b4c0dd21cb9`, native
renderer script SHA-256
`e1e3329f8caf52ad7e895514aa4f5b249501caee064b25b082c95baa661c73a2`, and native
preview test SHA-256
`69611c55271f548e8b486f6dbd5cd82f17be17484d79634ace66481ad66e8052`.
Final independent HTML/camera/native-artifact checks are pending at this freeze.
No user acceptance or local commit is inferred from producing these artifacts.

### Final independent technical acceptance

Root supplied the verifier's final verdict: **specification PASS; code quality
Approved**. All 12 frozen code/test hashes match the reviewed bytes. The six
actual bridge checks pass independently, and the final renderer/camera affected
suite passes **16 tests**, exit 0. All **666 pair selections × 2 zoom states =
1,332 actual HTML selections** match the recorded numerical output. Native report,
execution receipt and source input hashes also match.

The independent verifier used only the designated portable Blender executable to
read the final retained blend. It found three recorded-route objects and matched
all 207 red-line segment centers to the HTML route, with maximum world-coordinate
error `9.054596823286574e-7 m`. Board Z is approximately `0.02 m` and the route is
raised another `0.008 m`; all board vertices lie inside the retained camera
frustum. This native check exits 0, and the final PNG passes technical visual
review. These checks establish recorded-data alignment, not a new distance
calculation or user acceptance.

Technical checklist items `.18.8` and `.18.8a` are complete for accepted jj change
`mlkkrmsp`. Parent `.18` remains
open only for user visual gates `.18.10`/`.18.C4`, which remain unchecked. Root is
still the sole version writer and reports the accepted local commit identity in
the delivery message; the
implementer has performed no commit, push or merge. Large output artifacts remain
external execution evidence rather than project source changes.
