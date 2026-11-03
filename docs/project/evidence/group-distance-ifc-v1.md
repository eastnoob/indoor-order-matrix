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
