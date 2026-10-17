# B3 B1 native source qualification

Date: 2026-10-09 (local). **B1 facts accepted with the transport/material limits in this note; A OWNER ACCEPTED; identification views and display-only hull summaries accepted; B2 deferred; door investigation paused; B3 OPEN.** The fixed datum0 / eye1.6 / world-XY contract and historical S3 remain the analysis inputs. Eventual completeness is bounded to the frozen qualified imported inventory and declared domain, not exhaustive world completeness.

B1 found **no native original-index closed component in any of the 13 sources**. All native items have open boundary indices, `Closed=None`, and no occurrence/type material association. Native indexing therefore does not establish the capture's missing solid prerequisite. Face counts agree with capture; coordinate counts and topology differ, and the stated float32 positional comparison is unequal for every source. **Disconnected original indices do not prove physical gaps; multiset inequality does not prove material geometry loss.** Separate local-vertex/placement rounding may explain the positional comparison. B1 does not isolate a transport defect or establish physical volume.

## Execution and provenance

Implemented only the [collector](../../../scripts/design/space_field/run_b3_native_source_qualification.py), [focused tests](../../../test/test_b3_native_source_qualification.py), this note and the three linked B3 status documents. No production caller, fixture, export or config change is required.

- The IFC was length/SHA verified before native parsing: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, **408617800 bytes**, SHA-256 **`018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`**. The collector repeats this gate before opening IFC4 and confirms source-to-metre scale **0.001**.
- Accepted `source_sections.json`: 11397078 bytes, SHA-256 `57181d1dcf9b57b9386c2be036cfbdedddb641ab5242c9fdf1d01e5d7c7a56e7`. Frozen `scope_inventory.json`: 540239 bytes, SHA-256 `3ad1fadec5d1cc84bf88f7180fa9edf5a597ccce072ba8d5d779f234a628eb48`. Both were verified before decoding; each of the 13 mesh payloads was independently checked against the shared accepted/inventory ref.
- `pixi run pytest test/test_b3_native_source_qualification.py -q`: initially **21 passed in 0.48 s**. The first collector attempt, [run_20261008T222125Z_c088fd](../../../outputs/design/b3_native_source_qualification/run_20261008T222125Z_c088fd/execution.json), preserved 13 Body-binding failures, exit 1. The new fixture had incorrectly modeled the capture's string `representation_id` as an integer. Only that actual boundary mismatch and fixture were corrected; the explicit canonical string comparison still rejects another Body ID.
- Affected focused verification after repair: **21 passed in 0.31 s**. The repair rerun, [run_20261008T222211Z_3c1393](../../../outputs/design/b3_native_source_qualification/run_20261008T222211Z_3c1393/execution.json), completed **exit 0, 13 records, zero source/item failures**. No further collector run or optional tests followed.
- [Native source facts](../../../outputs/design/b3_native_source_qualification/run_20261008T222211Z_3c1393/native_source_facts.json): **76679526 bytes**, SHA-256 **`a712f2eb470a89728d34561b53e01e249d0a58e4e3945aef8e6cb75c543b2772`**. The large file retains every original face STEP ID, component membership and bounds; coordinate/ring arrays are identified by digests and exact frozen item refs. [Artifact manifest](../../../outputs/design/b3_native_source_qualification/run_20261008T222211Z_3c1393/artifact_manifest.json) also fingerprints the code and test file used.

The owner identified a possible O(components × edges) rescan in component incidence summaries. The running process had about 200 CPU seconds at observation; no installed stack sampler was found, so that observation alone did not isolate its slow path. A stop request was sent, but the tool returned the already completed successful run, exit 0. It is **completed, not interrupted**. No performance patch or further rerun was made. The completed data confirms that high component counts exercise the rescan; a future authorized rerun could group counts once by component root. This performance limit does not change the recorded topology.

## Exact native bindings

Each product has one declared **Body / Tessellation** representation containing one direct **IfcPolygonalFaceSet**. All faces are original triangles, `PnIndex=None`, inner-ring count zero and mapped lineage empty. Each recorded local placement has a single chain entry, default world-aligned directions and no parent placement. Native product matrices remain in source units; only transformed native coordinates are scaled to metres. Captured vertices already declare metres and `transform_applied=True` and are not scaled again.

| Product STEP | GlobalId | Body STEP | Item STEP | Coordinate-list STEP | Placement STEP |
| ---: | --- | ---: | ---: | ---: | ---: |
| 6231 | `3y7JkDRLzPT9x47Baq5air` | 15562 | 15561 | 6232 | 15568 |
| 43654 | `2$pZmZTQPRNQWDdiOmzSo_` | 49623 | 49622 | 43655 | 49629 |
| 49645 | `1cameBqC9H4gRgew6pelrZ` | 55614 | 55613 | 49646 | 55620 |
| 55636 | `3Ubr6f0zfLAAxYyBdvFyju` | 61605 | 61604 | 55637 | 61611 |
| 61627 | `1yil0vYiLSlP7C2s8YPjLM` | 67596 | 67595 | 61628 | 67602 |
| 67618 | `05qK_LP$PLHfyzuz5MHWHc` | 73587 | 73586 | 67619 | 73593 |
| 1992252 | `1wZJY19NTU$Bn2CE1vayIo` | 1996033 | 1996032 | 1992253 | 1996039 |
| 2032485 | `3tVuwteKLUAxI0S_ptGNQT` | 2051205 | 2051204 | 2032486 | 2051211 |
| 2053009 | `1frmBqaGbPA9BIJetQWrfy` | 2082616 | 2082615 | 2053010 | 2082622 |
| 2082638 | `31IHP3QHrVcfPwKvRNo$wX` | 2084469 | 2084468 | 2082639 | 2084475 |
| 3236022 | `1ABvcEoPPOdulOu6GfO5ru` | 3237853 | 3237852 | 3236023 | 3237859 |
| 3237875 | `0ZKIA_vCHHJB1xk3DDhXGh` | 3267482 | 3267481 | 3237876 | 3267488 |
| 3269286 | `2s6tcXT5rR49krD_XhXIfN` | 3288006 | 3288005 | 3269287 | 3288012 |

## Original topology and capture comparison

`Vn/Vc` is native/capture coordinate count; `F` is both native and capture triangle count. `Bn/Bc` is boundary-edge count. `Cn` is native edge-connected face-component count. `L/A/X` counts components entirely below / entirely above / neither side of z=1.6. No tolerance, coordinate joining or surface repair is used. `Unmatched` counts triangles on **each** side of the world-metre float32 position-multiset comparison; every comparison is unequal.

| STEP | Vn / Vc | F | Bn / Bc | Cn | L / A / X | Unmatched |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6231 | 5828 / 4662 | 9328 | 2216 / 8 | 60 | 34 / 6 / 20 | 5649 |
| 43654 | 4282 / 3000 | 5966 | 2488 / 12 | 63 | 28 / 8 / 27 | 4773 |
| 49645 | 4282 / 3000 | 5966 | 2488 / 12 | 63 | 28 / 8 / 27 | 4836 |
| 55636 | 4282 / 3000 | 5966 | 2488 / 12 | 63 | 28 / 8 / 27 | 4679 |
| 61627 | 4282 / 3000 | 5966 | 2488 / 12 | 63 | 28 / 8 / 27 | 4901 |
| 67618 | 4282 / 3000 | 5966 | 2488 / 12 | 63 | 28 / 8 / 27 | 4990 |
| 1992252 | 3507 / 1889 | 3778 | 2962 / 0 | 137 | 43 / 86 / 8 | 2294 |
| 2032485 | 56049 / 10055 | 18717 | 56049 / 995 | 18666 | 18092 / 574 / 0 | 17892 |
| 2053009 | 88772 / 17667 | 29604 | 88772 / 5332 | 29584 | 27075 / 2289 / 220 | 27754 |
| 2082638 | 5484 / 948 | 1828 | 5484 / 60 | 1828 | 1748 / 56 / 24 | 1689 |
| 3236022 | 5484 / 948 | 1828 | 5484 / 60 | 1828 | 1748 / 56 / 24 | 1801 |
| 3237875 | 88772 / 17667 | 29604 | 88772 / 5332 | 29584 | 27075 / 2289 / 220 | 28664 |
| 3269286 | 56049 / 10055 | 18717 | 56049 / 995 | 18666 | 18092 / 574 / 0 | 18099 |

All native edges have one or two incident faces, with **zero edges above two incidences**, zero inconsistent winding edges and zero collapsed-index edges. **Every component has boundary edges**; consistent winding on shared edges does not establish a solid. Native `non_closed_cycle_vertex_links` equals Bn for each row. Its test requires one closed link cycle and therefore counts boundary vertices as failures. It is deliberately different from the accepted capture's `nonmanifold_vertices`, which must not be equated with it. The accepted `nonmanifold_edges` counts every edge whose incidence is not two, including boundary edges; capture #6231 also has 31 four-face edges and #1992252 has 46 four-face edges.

The positional comparison ignores triangle winding and index identity and preserves triangle multiplicity. It does not establish float64 equality, self-intersection freedom, a solid or material equivalence. Capture `evaluated_mesh_loop_triangles` has fewer coordinates and different connectivity; no causal welding/repair history or physical gap is asserted. Bounds are close but not identical: for example #6231 native x-max is 8.8 m versus capture 8.800000190734863 m; #3237875 native x-min is 24.274615234375 m versus capture 24.274614334106445 m. Separate rounding of local vertices and placements before world composition may explain multiset inequality. Bounds inspection confirms the same world-metre region, but it is not a triangle correspondence or material-loss test. No distance tolerance or alternative matching was introduced, and no new native/capture parity certificate is claimed.

Only `OM_Layout` property sets were returned. They supply provenance, role, family and `AnalysisParticipation=exclude`; they do not supply a closed-solid/thickness/void interpretation. No occurrence/type material association was found. Names, colours and family strings do not justify physical material. The design Body-mass experiment remains distinct from canonical Analysis participation.

## Per-source diagnosis and owner ruling

- **Door #6231 / item #15561:** native indices contain 60 open components, including 20 at the plane. Capture has 8 boundary and 31 four-face edges, plus the retained 1.7100005149841309 m cut residual. Native topology does not clear its solid prerequisite. Source closure/material interpretation is the first blocker; numerical section tracing is not yet justified as a repair route.
- **Windows #43654, #49645, #55636, #61627, #67618 / their exact items above:** each has 63 open components and 27 at the plane; capture retains 12 boundary edges and its individual cut residual around 3.71763 m. These five retain their accepted outside-S3 broad-phase classification. No new domain proof was run. They remain unresolved for raw/outside-domain distance targets and do not need an interior mass inference merely to force this B1 cohort to pass.
- **Counter/shelves #1992252 / item #1996032:** native has 137 open components, 8 at the plane; capture has zero boundary edges but 46 four-face edges. Two planar faces and zero section residual do not qualify physical mass. No separate authored solid/material definition was found.
- **Dull-yellow #2032485 and #3269286 / items #2051204 and #3288005:** each has 18666 open indexed components, 18092 wholly below and 574 wholly above the plane, none spanning/touching it. Thus the recorded native triangle surfaces do not meet the plane. This is **surface absence only**: the tessellation does not establish that these are all intended physical parts or that no intended enclosed material crosses 1.6 m. Retain unknown physical occupancy pending that source meaning; do not infer an envelope or fill the gap.
- **Dark-green #2053009 and #3237875 / items #2082615 and #3267481:** each has 29584 open components, 220 at the plane; capture retains 5332 boundary edges and its original dangle residual (1.1114691434056558 / 1.1114659034100096 m). Direct native indexing supplies no closed-shell route. Keep the original failure rather than changing section arithmetic to manufacture closure.
- **Yellow #2082638 and #3236022 / items #2084468 and #3237852:** all 1828 native triangles are separate indexed components, 24 at the plane. Capture's two closed-looking planar faces and zero residual do not overcome 60 boundary edges or absent material semantics.

**Handback:** retain all original statuses and localized unknown; B2 remains unimplemented and deferred. The **eight overlapping sources** (#6231, #1992252, #2032485, #2053009, #2082638, #3236022, #3237875, #3269286) still lack a qualified physical-volume interpretation. In particular, surface absence for the dull-yellow pair does not establish absence of intended material/connections through eye height. Human interpretation must remain labeled interpretation and cannot create absent geometry or a numerical solid certificate.

The owner reviewed the completed metrics and accepts B1 as native facts with the explicit transport/material limits in this note. Original-index openness alone justifies no B2 occupancy derivation. The owner also reviewed and accepted the [captured-source identification visualization package](b3-unresolved-source-identification-views.md) for interpreting the eight overlapping exceptions. It uses frozen capture only and no native parsing/tessellation rerun or repair. It identifies physical forms using raw captured triangles; it assigns no material semantics or whole-object envelope. The later display-only convex hulls are separate from this accepted native-fact/identification evidence. B1 facts and accepted identification views authorize no B2 derivation. A stronger occupancy claim would still require a ledger over the frozen qualified imported inventory/domain and an independently complete declared distance target.

No full-scene import, tessellation, old geometric audit rerun, repair/weld/snap/fill, new section/solid engine, source/live/Blender mutation, field regeneration, dependencies, Git actions, agents or cross-chat messages were used. No broader tests or new images were needed for this bounded fact handback. A and B1 facts remain accepted; B2 is deferred; door investigation is paused and B3 remains OPEN.

## Current owner scope after identification

The owner temporarily defers counter/shelves #1992252, Assembly A #2032485/#2053009/#2082638 and Assembly B #3269286/#3237875/#3236022 from current overall analysis. The eight-source physical-volume diagnosis above remains an accepted historical fact; this scope ruling does not turn unknown into empty geometry or change original source/canonical records or accepted packages. Door #6231 investigation and B2 are paused for the current display delivery. Five outside windows retain their prior status.

The owner explicitly chooses 凸包 (convex hull), authorizing the earlier furniture display footprint method for three separate complete groups only. The owner accepted the final PNG, execution and serialized method/scope of the [display-only hull package](b3-unresolved-source-identification-views.md). It preserves the original meshes and uses all full-height world-XY vertices per group. Its filled holes/concavities establish no physical material, eye-plane occupancy or orientation participation. That earlier 2D package did not create or enroll mesh substitutes. The latest user ruling explicitly requests real 3D convex meshes as normal objects; the new [3D proxy delivery](b3-unresolved-source-identification-views.md) creates three provisional closed OBJ substitutes for later dedicated analysis enrollment, while current exclusion remains. Generated-proxy closure/volume does not qualify the original native/captured source material. Accepted 2D artifacts remain history and original B1 facts are unchanged. B3 remains OPEN and complete physical occupancy/clearance remains unavailable.

## Accepted 3D geometry; enrollment alone pending

The owner accepts the three generated ordinary closed 3D convex meshes in `outputs/design/b3_deferred_convex_meshes/run_20261008T225203Z_aa8aaa/` after reviewing code, final preview, execution and mesh metadata. Geometry generation is complete. The only pending user decision is whether to continue deferred/excluded status or activate physical occupancy while excluding plant orientation evidence. Until a reply, retain the current seven-source deferral and proxy exclusion; do not regenerate or enroll. Dedicated analysis enrollment remains a separate step. Earlier 2D artifacts remain historical predecessors; original-source material/volume limitations, accepted A and B1 remain unchanged. B3 stays OPEN for scoped physical occupancy.
