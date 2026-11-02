# Group distance IFC v1 execution evidence

Date: 2026-11-03. Runner/renderer delivery exists; useful real-route validation and user visual acceptance remain open.

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
