# B3 real-source capture qualification — 2026-10-08

**Disposition: partial, for owner review before worker B.** Full evaluated real Body geometry and the unchanged historically accepted S3 polygon are persisted. Geometry parity is qualified; the current live acceptance binding and complete solid occupancy are not. No field, PNG, or `.blend` has been generated, and B3 remains open.

## Capture and provenance

Package: [`outputs/design/b3_real_source_field/run_001/`](../../../outputs/design/b3_real_source_field/run_001/). Entry points are `capture_manifest.json`, `qualification.json`, and `artifact_index.json`. Geometry is stored per IFC STEP in `meshes/`; GlobalId, class, psets, containment, declared/loaded representation, quality flags, and geometry byte hashes remain in the capture manifest. `structural_parity.json`, `s3_scope.json`, `scope_inventory.json`, and `height_probes.json` hold the qualification evidence.

The live capture used only `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` (5.2.0 LTS) and the existing read-only structural capture seam. It extracted 354 evaluated **Body** meshes: 1,802,274 vertices and 3,543,857 triangles, in 164,849,278 bytes of mesh JSON. Absolute world coordinates are metres; the evaluated world transform was applied once, with no second IFC scaling. IFC source units remain millimetres, with normalization 0.001 m/source unit. These records can support later disposable rendering and independent height queries without rereading native IFC geometry.

Source: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, project GlobalId `2uGd6yom9GZe5$z7LfbGW0`, 408,617,800 bytes, SHA256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`. Capture-manifest SHA256: `776ebd32fe8ae4595c01dc8bf664fb6da456a0d791a4cafd160bda3afa2cafb7`.

Before/after original object names/types, selection, active object, camera, filepath, mode, and dirty state match. There were 372 scene objects: 363 meshes and nine empties. Four products are semantic nonmass (site/building/storey/grid); the separate non-product audit contains nine grid-axis meshes and five project/type empties, all IFC linked. No geometry was welded, repaired, or replaced, and no source IFC or scene writes occurred. Native IFC tessellation parity was not checked.

All 95 furniture products declare both Body and Analysis; the other 259 extracted products declare Body. Only the loaded Body was extracted. This is a **design-only factual Body mass branch**: canonical Analysis-substitute discovery and Body exclusion policy are unchanged. Authored participation remains a separate fact (95 furniture `include`; structural/context/support products `exclude`). Excluded physical Body geometry is retained for review, while the slab is explicitly support excluded from occupancy. No affordance volume, trend substitute, or helper axis is promoted into an obstacle.

## Historical S3 parity and binding

Against `outputs/design/d6_b4_live_blender/run_001/live_request.json` and `live_result.json`, all 38 structural records have exactly matching vertices, triangle indices, world transforms, units, applied-transform flags, representation/tessellation metadata, roles, factual properties, and IFC GlobalIds. **26 Blender display names and object ordering differ.** Snapshot identity also records changed dirty state and scope ordering/names. Restoring only historical object names and order in a diagnostic copy reproduces the historical Neutral Scene digest exactly; no actual source or binding was normalized.

- Historical source revision: `e4f19cad8c7d0b6ca8e85fe5efcabbcf25ab8a619c54d938573ef9b8b0c64722`.
- Captured structural revision: `15050986d6b7aa02e666a0a9de45d129d2a7cf9892d7eba06b9ebff403174b24`.
- Historical frame: `04c8a31502b3ccf1cab94cd5b143cbe79da743c4b280d8c9f6d48ea442167ec8` (world XY, datum 0 m, B4 cut 1.5 m).
- Historical request: `80153b2a3de0c8da18eab569c02b6ea47ed69e7aa5c1593c666be3f98aa9a44f`.
- Candidate identity: `dbd6d9d9e2968aa4e28202d2b829fe45cc8f45bfef2e9b26143f533bb1f8e88b`.
- Accepted version: `inferred:S3:61132013996064b3239a7e6cdfbd86abd07dec33404340c122ae03888bc3032b`.

`s3_scope.json` copies the accepted candidate, exterior, two holes, confirmation action, binding, and provenance unchanged. Recomputed polygon area agrees with the saved **206.5209234821732 m²**. The frame digest also reproduces exactly. This permits a bounded **historical-snapshot planar experiment with verified geometry parity**. It does not qualify a current live S3 acceptance: panel state was not observed, revisions differ, and no rebind/reconfirmation/inference was performed. S3's 3D extent remains unknown.

The floor datum carries the human confirmation of 2026-10-08: **0 m, floor top surface**, analysis world z=0, Level 1 / storey #13 (`2udSq8mkbQwxg0XrW$uM_r`), slab #4884, containment #3556490. IFC `Elevation=None` and `ObjectPlacement=None` remain explicit. Slab bounds z≈[-0.300000012, 0] m are audit evidence, not a datum fallback. The provisional eye offset 1.6 m gives world z=1.6 m and band [1.55, 1.65] m. Independent lower diagnostic band [0.45, 0.55] m is a named experiment, not a production height policy.

## Scope and query limits

Global mesh quality: **190** meet the captured closed/manifold/consistent-edge-winding/no-degenerate-triangle criteria; **164** do not. Totals are 58,026 boundary edges, 58,735 nonmanifold edges, 1,002 nonmanifold vertices, three inconsistent-winding edges, and zero degenerate triangles. Passing these criteria does not establish absence of self-intersections or nested-solid ambiguity.

Actual projected triangle interiors determine positive-area S3 membership; collapsed face edges preserve boundary contact. Bboxes only reject disjoint candidates. This existential full-height XY test preserves holes and is not an eye/lower occupancy slice or a union-area measurement. No snapping or tolerance-based removal was applied.

| IFC class | Extracted | Eligible globally | Positive S3 area | Boundary contact | Outside |
|---|---:|---:|---:|---:|---:|
| Column | 16 | 16 | 0 | 12 | 4 |
| Slab (support) | 1 | 1 | 1 | 0 | 0 |
| Door | 6 | 5 | 6 | 0 | 0 |
| Window | 5 | 0 | 0 | 0 | 5 |
| Wall | 11 | 11 | 1 | 7 | 3 |
| Furniture | 95 | 37 | 95 | 0 | 0 |
| BuildingElementProxy | 193 | 109 | 193 | 0 | 0 |
| FurnishingElement | 27 | 11 | 27 | 0 | 0 |
| Total | 354 | 190 | 323 | 19 | 12 |

The positive-area wall includes a small real numerical overlap: witness triangle clipped area 5.077557396482302e-7 m². Keep this evidence for scope/boundary review. Boundary-contact and outside bodies remain persisted because later raw-clearance queries may need them.

**159 unsupported bodies have positive full-height S3 area**, including 58 furniture. Of those, ten overlap the observed eye-height range and 72 the lower-height range. These are conservative candidate flags formed from actual full-height XY membership plus observed z range, not actual band occupancy or proof of free space. Per-object missingness remains explicit; unsupported solid-query areas are null, not zero.

Fifteen bounded real probes (eight eligible, seven unsupported) preserve source hashes, witness XY, vertical interval results/uncertainties, and separate height queries. Existing `mass_patch_from_mesh`, `vertical_intervals_at`, and `plan_projection` were reused. Eligible band projections preserve disconnected components, holes, raw/clipped area, and helper uncertainties; every result is labeled **diagnostic surface projection, not exact solid-band occupancy or exact plane section**. Surface clipping can miss enclosed volume; cross-section reconstruction or full-footprint fallback may occur. A missing helper uncertainty is not certification of exactness.

Examples: furniture #191333 has observed z=[0.0006972163, 0.7127441764] m, no positive eye-band overlap, and lower projected area 0.002809174382 m². Eligible furnishing #3556226 has observed z=[0, 4.5] m and positive clipped eye/lower projected area ≈0.004263132136 m². Door #20409 has full-height S3 overlap but zero clipped projected area at both bands. Open door #6231 retains `open_or_nonmanifold_geometry` and unsupported band areas even though its local interval helper returned crossings. Probes do not establish a complete field, exact slice, visibility, perception, or walkability.

## Verification and owner handoff

Live capture command (through Blender MCP): `runpy.run_path(r'D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\b3_real_source_field\run_001\capture_live.py', run_name='__main__')`.

Host qualification: `pixi run python outputs/design/b3_real_source_field/run_001/qualify_capture.py`. Its assertions reject NaN/Infinity/duplicate JSON keys, check scope holes/contact, verify input bytes/hashes, validate finite meshes/index topology through the existing adapter contract, reproduce historical revision/frame, and check every mass's full indexed geometry and structural parity. A first diagnostic assertion exposed changed ordering; the final successful run records that difference and includes a tall eligible eye-band probe.

Final audit: `pixi run python outputs/design/b3_real_source_field/run_001/verify_artifacts.py`. It checks referenced hashes, all 354 mesh hashes, the immutable capture manifest, positive real eye/lower probe evidence, new-function docstrings/syntax, and manual whitespace checks for the output scripts and this untracked note. Bounded `git diff --check` passes. All **75 pre-existing dirty/untracked file hashes are unchanged**. `artifact_index.json` records each package file and this note; its own hash is printed separately by the verifier to avoid a circular hash dependency.

Owner review can use this package to decide historical-snapshot scope use versus live rebinding, Body/context participation, treatment of open meshes and small scope overlaps, and the projection/missingness policy before worker B. The capture is sufficient as auditable geometry input for disposable rendering; it is insufficient for a complete known-free/occupied field without those decisions or further geometry qualification.

Skipped: worker B, field generation/rendering, native IFC adapter, full pytest, source edits, API/dependency changes, staging/commit/push, and messages to other chats. Risks: revision binding incompatibility, unsupported meshes, approximate height projections, unknown S3 vertical extent, and no native IFC geometry parity.
