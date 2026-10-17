# B3 conditional field handoff and physical occupancy plan

Date: 2026-10-09. Status: **package A OWNER ACCEPTED; B1 facts accepted with explicit transport/material limits; bounded captured-source identification views and historical 2D hull summaries accepted; generated ordinary closed 3D convex meshes OWNER ACCEPTED; historical 3D proxy comparison and selected-domain boundary package run_20261009T083535Z_c914e2 OWNER ACCEPTED; generic boundary rule OWNER ACCEPTED; raw door qualification unresolved only as historical source evidence; three counter/plant proxies active for physical occupancy only in run_20261009T091601Z_242b33 (OWNER ACCEPTED); furniture/group/trend/orientation/affordance analysis excluded; B2 not promoted; B3 OPEN**.

**CURRENT planning pointer (2026-10-09):** The [physical occupancy policy plan](physical-occupancy-policy-plan.md) records the implemented and verified two-dimensional occupancy/substitute main chain plus the B3 shared enrollment implementation currently under verification. The new package uses explicit world-XY `z=1.6 m` sections over the same physical representatives; arbitrary planes/bands, live promotion, complete occupancy and complete clearance remain open. This B3 history and its accepted packages remain unchanged.

**CURRENT implementation evidence:** `outputs/design/b3_shared_occupancy_enrollment/run_20261009T141817Z_8e23c2/execution.json` reports `exit_0`; its comparison audit has 9,648 field-equivalent samples and zero deltas for all four recorded areas. This is **IMPLEMENTED / VERIFICATION IN PROGRESS**, not OWNER ACCEPTED. The failed mappingproxy run `run_20261009T141637Z_243803` remains historical evidence.

This continuation has two sequential packages: **A, formal reusable conditional tri-state discrete-field delivery**, then **B, targeted source qualification toward complete physical occupancy at world z=1.6 m**. A delivers the accepted evidence to an ordinary Python consumer. It does not close B3 or establish complete occupancy. B starts after A is implemented and reviewed; it may end with documented source-semantic blockers rather than a complete-occupancy claim.

Historical planning authorization covered bounded reconnaissance and these three documents only: this plan, the [exploratory plan](b3-space-field-exploratory-plan.md), and the [deliverable design](b3-space-field-deliverable-design.md). The owner subsequently accepted A as the bounded reusable conditional discrete delivery and explicitly authorized B1: verify frozen native IFC length/SHA first, inspect the 13 exact STEP/GlobalId/Body/item bindings, add focused tests, run one targeted collector and repair actual failures only. Original-index topology, Closed, mapped lineage, placements, units, native/capture comparison and source-semantic blockers are in scope. Stop after evidence for consequential owner ruling; B2 is not authorized. No full import/tessellation, old audit repetition, geometry repair, new section/solid engine, source/live/Blender mutation, field regeneration, dependency/Git/agent/chat actions. Accepted comparison evidence needs no further visual approval.

## Current owner scope and 3D mesh proxy delivery

The owner excludes counter/shelves **#1992252**, Assembly A **#2032485 / #2053009 / #2082638**, and Assembly B **#3269286 / #3237875 / #3236022** from furniture-level analysis while requiring their physical volume in occupancy and downstream free space. Three accepted convex substitutes represent those seven originals once for the bounded B3 field and new shared enrollment package. This is human source-scope provenance, not exact original material or a completeness claim. Preserve all original facts, meshes, accepted A/source/field packages, statuses and localized unknown in their historical source artifacts. Historical packages still contain these sources; their masks and counts were not regenerated. A, B1 facts and the five identification PNGs remain accepted; B2 is not promoted and B3 remains OPEN.

The user explicitly means **three-dimensional 凸包 (convex hulls) as normal mesh objects**. The earlier 2D-only footprint delivery misread the intended dimensionality. Its accepted display package `outputs/design/b3_deferred_display_hulls/run_20261008T224700Z_138106/` is retained as history. The new authorized outcome is three separate closed 3D convex meshes from all full-height world-XYZ vertices of each complete group. It is not an XY hull extruded to a prism. User-selected convex approximation intentionally fills all internal gaps/concavities; this authorization supersedes the earlier no-hull restriction for these three proxies only and does not identify original exact physical material.

Delivered one minimal [3D mesh renderer/exporter](../../scripts/design/space_field/render_b3_deferred_convex_meshes.py) using the existing frozen-input/fingerprint/plotting patterns and exact group definitions. Installed SciPy 1.17.1 `spatial.ConvexHull` supplies triangulated facets without QJ, random perturbation, repair or new dependencies. Facet winding is aligned with Qhull outward normals, then compacted to ordinary OBJ vertex/triangle arrays. The final unique package `outputs/design/b3_deferred_convex_meshes/run_20261008T225203Z_aa8aaa/` contains three OBJ files, a readable original-plus-translucent-facets 3D preview, small provenance/mesh metadata, manifest and execution record. See the [identification and 3D proxy evidence note](evidence/b3-unresolved-source-identification-views.md) for exact files and checks. Exit 0; tetrahedron-with-interior-point self-check, frozen-input/exact-membership assertions and all three closed/outward/nonzero-volume checks passed. The final image was inspected; the owner reviewed the script, final preview, execution and mesh metadata and accepts the three generated ordinary closed 3D convex meshes, their XYZ derivation, outward/incidence/positive-volume evidence, compact OBJ export and source associations.

These are **provisional ordinary 3D mesh substitutes** for later dedicated analysis enrollment, analogous to furniture. Their current overall-analysis exclusion remains. No new registry, framework or production contract is created. No existing caller, test, fixture, config, export, production geometry or live state needs edits for this standalone package. Confirmed door #6231 counts as closed S3 boundary for current interior occupancy and uncertainty; its unresolved raw qualification remains historical. B2 is not promoted; complete scoped physical occupancy/clearance remains unavailable. The checks certify the generated convex meshes, not original-source volume or world completeness.

## Package A implementation and verification

Implemented [`features/discrete_space_field.py`](../../features/discrete_space_field.py) and [`test/test_discrete_space_field.py`](../../test/test_discrete_space_field.py). `load_discrete_space_field(package_dir, *, spacing_m, origin_offset_m)` returns `field`, `variant`, `source_sections` and `artifact_manifest` dictionaries. Both fixed sibling payloads are SHA-256/length checked before decoding; field/source schemas, provenance, settled height, lattice coordinates/indices/counts and tri-state/missingness invariants are validated. All serialized variants are checked; only the explicitly chosen variant is returned. Errors propagate as file errors or `ValueError`, never computed-empty results. Original records, coordinates, statuses/errors and refs remain intact.

Coordinate validation allows eight times the sum of ULPs of the domain minimum, offset, index-step product and expected coordinate, accounting for the few multiplication/addition operations of the original sampler. It is a serialization arithmetic check only; no domain membership, occupancy, geometry precision, repair or numerical field operation is computed. External source/code refs are checked for fingerprint structure and retained; their files, original meshes, IFC, PNGs and Blender output are not opened or revalidated. Manifest consistency does not authenticate acceptance.

Verification on 2026-10-09:

- `pixi run pytest test/test_discrete_space_field.py -q`: **50 passed in 2.12 s**. The first invocation stopped at collection because the new test used a top-level import; it was corrected to the repository's existing package-relative test import and only this file was rerun. The final run includes a fresh ordinary Python subprocess import/consumer check.
- One read-only real consumer, `pixi run python -` using the example below: **exit 0**, selected 0.25 m / [0, 0], **3,888 samples / 3,323 in domain**, **3,015 conditional empty / 308 unknown / 565 outside / zero occupied samples**, **358 source records**. Both consumed hashes matched the recorded values below. All selected complete-clearance values remain null; six original source refs are retained; `scripts.design` was absent from loaded modules.
- Original artifact status remains `design_only_partial_qualified_subset_owner_review_required`; its owner acceptance is retained in the manifest. A does not relabel the immutable package. No live handoff, exports, room model/UI, existing tests/runners, dependencies or accepted artifacts were edited.

The implemented A scope is the two Python files and these three B3 documents. No separate CLI, object model or evidence output run was added. **Package A is OWNER ACCEPTED under the fixed datum0 / eye1.6 / world-XY conditional contract. Completed discrete delivery is distinct from complete physical occupancy. B1 facts and identification views are accepted within their stated limits; B2 is deferred; door investigation is paused and B3 remains OPEN.**

## Fixed evidence and boundaries

The primary datum remains human-confirmed storey-bound 0.0 m plus eye offset 1.6 m: **world z=1.6 m**. Storey #13 has no authored elevation/placement; the explicit confirmation is provenance, not an inferred replacement. Historical S3 is 206.5209234821732 m² with two holes. Its frame metadata contains the original cut 1.5 m; that horizontal scope reference must remain separate from the eye query. Current live domain binding and S3 vertical extent remain unverified.

Immutable inputs are:

- Accepted field package: `outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/`, especially `field_samples.json`, `source_sections.json` and `artifact_manifest.json`.
- Accepted connectivity package: `outputs/design/b3_eye_plane_connectivity/run_20261008T214917Z_5c7dab/`. Its accepted comparison uses serialized S3-clipped targets and a floating-point open-interior reference.
- Frozen capture: `outputs/design/b3_real_source_field/run_001/`, including `artifact_index.json` (366 entries), `capture_manifest.json`, `scope_inventory.json`, `s3_scope.json`, `qualification.json`, `structural_parity.json` and 354 Body mesh files.

Field SHA-256 is `abaf69ef376323680a181265ba048027280cae6ba7634ae6dde152152d2f3fc7` (7,026,520 bytes); source sections SHA-256 is `57181d1dcf9b57b9386c2be036cfbdedddb641ab5242c9fdf1d01e5d7c7a56e7` (11,397,078 bytes). These are recorded manifest values, not newly recomputed in this planning step. Preserve accepted artifacts, historical failed/interrupted runs, original errors, ambiguity guards and raw/clipped distinctions.

The accepted source result has 34 qualified closed sections, 111 valid empty below, 195 valid empty above, 13 unresolved open/nonmanifold sources, one excluded slab and four semantic nonmass exclusions. Fifteen below-plane degenerate chair meshes retain invalid geometry status separately from proven plane absence. Qualified raw area is 22.392615629752758 m²; S3-clipped qualified area is 0.014987329164664116 m²; clipped unknown support is 19.069186870135574 m². All four lattices miss the tiny positive subset.

| Spacing m | XY origin offset m | Samples | In domain | Occupied | Conditional empty | Unknown | Outside |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | [0, 0] | 960 | 815 | 0 | 744 | 71 | 145 |
| 0.5 | [0.125, 0.125] | 960 | 817 | 0 | 745 | 72 | 143 |
| 0.25 | [0, 0] | 3888 | 3323 | 0 | 3015 | 308 | 565 |
| 0.25 | [0.0625, 0.0625] | 3840 | 3276 | 0 | 2978 | 298 | 564 |

Accepted geometric/4/8 component counts are 1/1/1, 1/1/1, 1/2/1 and 1/2/1. At 0.25 m the 4-neighbor splits are 3014+1 and 2975+3 within one geometric component. Counts do not establish agreement or routes. The raw-path source-boundary residual for `live-step-3556226` remains recorded; package A does not reconstruct that reference.

## A — delivered reusable interface and approved scope

### Existing boundary and proposed reach

`features/scene_evaluator.py::validate_adapter_payload_json` validates a different exported adapter contract. `features/substitute_contract.py::load_substitute_registry` validates a different registry. Neither is a field loader; reuse their UTF-8 JSON/dictionary/error conventions, not their schemas. The design runners contain generation and experimental dependencies and are not a production consumer boundary.

Implemented one module-level consumer function in **`features/discrete_space_field.py`**:

```python
load_discrete_space_field(package_dir, *, spacing_m, origin_offset_m) -> dict
```

`package_dir` is the caller-supplied accepted package directory. Both lattice parameters are required; exact matching must select one serialized variant. Unknown or duplicate choices raise `ValueError`, with no nearest resolution, interpolation or implicit default. The initial supported format is the existing v1 field/source/manifest schemas. This is a serialized artifact consumer, not a field generator or query engine.

Return plain dictionaries: `field` (existing field metadata/channels/provenance with `variants` removed), `variant` (the selected existing lattice dictionary, including all indexed samples), `source_sections` (existing source-section dictionary), and `artifact_manifest` (existing manifest dictionary). Retain the original artifact status and owner-ruling text; loading does not confer acceptance. No new class or normalization of source records is required.

| Path/surface | Implemented A reach |
| --- | --- |
| `features/discrete_space_field.py` | New UTF-8 loader, manifest integrity and contract validation, explicit lattice selection, dictionary return. Every function has an English docstring; important validation steps explain why. |
| `test/test_discrete_space_field.py` | Small synthetic serialized package fixtures plus focused invalid/semantic/import-boundary checks. Fixtures are built in the test; do not copy multi-megabyte capture files. |
| This plan and the two linked B3 documents | Record implementation result, exact consumer example and qualification limits after A. |
| Ordinary Python caller | Direct module import, illustrated below; no existing production caller is switched. |
| `features/__init__.py`, root exports, adapters, live handoff, room model, UI, existing runners/tests/fixtures, Pixi config | No edits needed for the direct module import. No dependency additions. |

There is no existing field caller to migrate. The real smallest consumer is a Python script/notebook importing `features.discrete_space_field` from the repository root (or `order_analyzer.features.discrete_space_field` when the parent package is on its import path). The sample consumer and focused test are the only initial callers. Do not introduce another standalone CLI/example file.

### Validation and dictionary contract

Read the three fixed sibling files: `artifact_manifest.json`, `field_samples.json` and `source_sections.json`. Match exactly one manifest entry for each consumed payload; check byte length and SHA-256 before decoding the payload. Bind entries and the field's `source_sections` reference to these sibling files and this package, rather than following arbitrary paths from JSON. Existing references are repository-relative: preserve their original strings. No absolute machine root, current-working-directory inference or path rewriting should be needed to consume this copied package.

The sibling manifest provides an integrity consistency check, not independent authentication. A's recorded acceptance identifies the reviewed package/hash pair. A loader must not mark another self-consistent manifest as owner accepted. Validate only consumed artifacts; the Blender file, PNGs, code references and original IFC/meshes are provenance, not required runtime dependencies for A. Preserve their recorded hashes and mark no unvisited reference as newly verified.

At the trust boundary, require the supported schemas, required dictionary/list fields, units in metres, declared frame and scope/source revision identities, floor datum, eye offset and matching field/section/sample world height. Reject missing or malformed metadata. Reject nonfinite numbers and nonstandard JSON NaN/Infinity, malformed samples, noninteger/bool lattice indices, duplicate `(cell_i, cell_j)` identities, duplicate variants, count mismatches and inconsistent state/masks. Ensure coordinates follow the declared spacing and offset without resampling; preserve original coordinates and indices. The offset is relative to the accepted domain-bounds lattice construction, **not an absolute XY origin**: for 0.5 m/[0,0], sample (0,0) is approximately (5.400000095367432, 0.550000011920929). Validate this convention using serialized domain bounds/coordinates and floating-point roundoff only; do not create a geometric precision or occupancy tolerance.

Require source identifiers to resolve to source records; retain STEP/GlobalId, category, participation, status/error, geometry refs/hashes, source qualification and boundary evidence. Keep algorithm/code revision hashes, source integrity audit, units/frame, storey/datum/height and historical scope binding accessible. Checking structural consistency of these facts does not requalify geometry.

The sample contract is the accepted contract:

| Channel | Delivery meaning |
| --- | --- |
| `cell_i`, `cell_j`, `x_m`, `y_m`, `world_z_m` | Original indexed point location; no cells or interpolated values certified. |
| `domain_mask` | Independent in-domain/outside distinction. Outside has null occupancy and `unknown_mask=False`; it is not conditional empty. |
| `occupancy_value` | Exact Python `True`/`False`/`None`, never numeric 1/0 coercion. True is qualified interior evidence; false is empty only under declared qualification; null in domain is unknown. |
| `qualified_occupied_subset_mask` | Positive qualified evidence overrides overlapping unresolved support/boundary ambiguity. Preserve those independent masks and IDs even when occupancy is true. |
| `unresolved_source_support_mask`, `unresolved_source_ids`, `section_boundary_ambiguity_mask`, `unknown_mask` | Independent missingness/ambiguity evidence. No false value when these imply unresolved occupancy without overriding positive evidence. Missing uncertainty support must not become empty. |
| `known_free_under_qualification`, `status` | Preserve conditional status; no promotion to physical free space. Outside remains distinct; positive/unknown samples are not known free. |
| `distance_to_domain_boundary_m` | Independent unsigned distance to historical S3 exterior or hole boundaries; outside null. |
| `distance_to_raw_qualified_occupied_subset_m` | Unsigned distance to incomplete raw qualified mass, including outside-domain mass; outside/empty-target null. It is not complete clearance. |
| `complete_physical_clearance_m` | Null throughout A. Non-null would be an incompatible promotion requiring a separate qualified contract. |

Use explicit exceptions for unavailable/missing files and malformed/incompatible input. Never catch an error and return an empty sample list, zero occupancy, empty blockers or computed-empty status. Keep recorded unsupported/invalid/ambiguous/source errors even when a point is conditionally empty elsewhere.

`features/neutral_scene_views.py::_analysis_scene_view_with_domain_handoff` calls the private `features/_analysis_domain_handoff.py::domain_handoff`. That live contract binds source revision, scene digest, frame, request/candidate identity and confirmation lifecycle. **Its downstream `formal_field` remains `not_available`.** An offline historical accepted field is not a live confirmation. Do not change that handoff, attach the offline field to a current scene, or change exported `room_analysis_model` shape.

Connectivity stays in its accepted separate diagnostic package. A does not load/build graphs, infer routes, reconstruct cells, reclip geometry or require a PNG/Blender view. No production spacing is selected by implementing this loader.

### Smallest ordinary consumer example

This implemented API was exercised by the real consumer above. Run from the repository root with Pixi Python:

```python
from pathlib import Path
from features.discrete_space_field import load_discrete_space_field

package = Path("outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3")
delivery = load_discrete_space_field(
    package, spacing_m=0.25, origin_offset_m=(0.0, 0.0)
)
samples = delivery["variant"]["samples"]
point_values = [
    (s["cell_i"], s["cell_j"], s["x_m"], s["y_m"],
     s["occupancy_value"], s["domain_mask"], s["unknown_mask"])
    for s in samples
]
provenance = delivery["field"]["sources"]
source_records = delivery["source_sections"]["records"]
```

The consumer obtains all 3,888 original points for this choice, with 3,323 in domain, 3,015 conditional empty, 308 unknown and 565 outside. Neither the consumer nor the loader imports `scripts.design`. The original source IFC and meshes need not be present to read verified serialized evidence.

### Approved implementation order and A acceptance (completed checks above)

1. Add the function and only necessary private validation helpers. Keep serialized dictionaries intact and documented. Validate the package and variant without geometry recomputation.
2. Add focused tests: true/false/null/outside; positive overriding unknown while preserving IDs/masks; boundary ambiguity; explicit/missing/unknown/duplicate lattice choice; missing files, schema/hash/count/index/nonfinite/state errors; preserved provenance and both distances; null complete clearance. Include positive and overlapping-unknown samples in synthetic fixtures because the accepted four grids contain no true samples. Rehash a deliberately malformed fixture so semantic validation is exercised independently of hash failure.
3. Verify direct ordinary import and consumer execution without loading `scripts.design`. Run `pixi run pytest test/test_discrete_space_field.py -q`, then the one read-only consumer against the accepted package. Report selected sample counts and hash verification without regenerating field/connectivity/source geometry or running Blender. No broad suite is required unless an actual affected import/caller failure appears.
4. Hand back the implemented API, focused checks and ordinary consumer result. A is complete only when these work and the conditional limits survive. **B3 remains OPEN.** Proceed to B only on the approved sequential route.

## B — targeted qualification after A

### Source identity and current evidence

The frozen capture refers to `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, 408,617,800 bytes, SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`. B1 verified both length and digest before native parsing. IFC4 source-to-metre scale is 0.001; captured meshes are already world metres with transforms applied and were not scaled again. The [B1 native facts evidence](evidence/b3-native-source-qualification.md) binds all 13 exact product/GlobalId/Body/item/placement refs and preserves independent capture hashes. Capture `native_IFC_geometry_parity` remains `not_checked`; neither historical structural parity nor B1's bounded positional comparison certifies native physical equivalence.

Every row below retains `status=unresolved_open_or_nonmanifold`, `solid_query_eligible=False`, zero recorded degenerate triangles, zero coplanar/contact triangles and the error: **“Closed solid prerequisite fails; closed planar contours alone do not qualify open mass.”** This guard precedes section-residual and connected-shell qualification. Accordingly, closed-looking section faces or zero residuals do not clear the source. B1 confirms one direct `IfcPolygonalFaceSet` per **Body / Tessellation**, `Closed=None`, `PnIndex=None`, all original faces triangular and no mapped items or occurrence/type material associations. Every native original-index component has boundary edges. These facts do not establish physical gaps or solid meaning.

IDs are `live-step-<STEP>`. Capture mesh refs are `outputs/design/b3_real_source_field/run_001/meshes/<STEP>.json`; corresponding bytes/SHA-256/GlobalId are in the accepted source records and frozen inventory. The table supplies original object/Body representation lookups and recorded diagnostics, not new computations. `B/N/V` means boundary edges / nonmanifold edges / nonmanifold vertices. Five windows are outside the historical S3 by the recorded disjoint bounding-box broad phase; eight rows have positive-area projected-triangle overlap. Their unknown support is localization, not occupied mass.

| STEP | Name / IFC class | Body rep STEP | S3 | B/N/V | Strict crossings / faces | Residual length m | Branch |
| ---: | --- | ---: | --- | --- | --- | --- | --- |
| 6231 | Door / IfcDoor | 15562 | overlap | 8/39/26 | 52 / 6 | cuts 1.7100005149841309 | T + S |
| 43654 | Window / IfcWindow | 49623 | outside | 12/12/0 | 76 / 8 | cuts 3.7176313400268555 | T + S; outside |
| 49645 | Window / IfcWindow | 55614 | outside | 12/12/0 | 76 / 8 | cuts 3.717630386352539 | T + S; outside |
| 55636 | Window / IfcWindow | 61605 | outside | 12/12/0 | 76 / 8 | cuts 3.717632293701172 | T + S; outside |
| 61627 | Window / IfcWindow | 67596 | outside | 12/12/0 | 76 / 8 | cuts 3.7176313400268555 | T + S; outside |
| 67618 | Window / IfcWindow | 73587 | outside | 12/12/0 | 76 / 8 | cuts 3.717630386352539 | T + S; outside |
| 1992252 | OTHER_BarCounterAndShelves / IfcBuildingElementProxy | 1996033 | overlap | 0/46/40 | 40 / 2 | all zero | T + M |
| 2032485 | CET_dull_yellow / IfcFurnishingElement | 2051205 | overlap | 995/995/0 | 0 / 0 | all zero | T + M + U if unsupported |
| 2053009 | CET_dark_green / IfcFurnishingElement | 2082616 | overlap | 5332/5332/0 | 220 / 0 | dangles 1.1114691434056558 | T + S + M |
| 2082638 | CET_yellow / IfcFurnishingElement | 2084469 | overlap | 60/60/0 | 24 / 2 | all zero | T + M |
| 3236022 | CET_yellow / IfcFurnishingElement | 3237853 | overlap | 60/60/0 | 24 / 2 | all zero | T + M |
| 3237875 | CET_dark_green / IfcFurnishingElement | 3267482 | overlap | 5332/5332/0 | 220 / 0 | dangles 1.1114659034100096 | T + S + M |
| 3269286 | CET_dull_yellow / IfcFurnishingElement | 3288006 | overlap | 995/995/0 | 0 / 0 | all zero | T + M + U if unsupported |

The paired furnishing rows share diagnostic patterns; B1 independently verified both members' actual identities and original-index topology. Do not assume identical geometry from names, counts or colours. All rows retain independent mesh hashes. The dull-yellow pair's captured z range [0.5389143824577332, 1.7290375232696533] spans the query, but has no strict triangle crossings or guarded contacts. B1 finds every original-index component wholly below or above the plane: native surface absence is recorded, but intended material absence remains unqualified. It is **not** a whole-object entirely-above/below solid proof.

### B1 completed facts and stop

The [focused evidence note](evidence/b3-native-source-qualification.md) records all 13 exact bindings, topology/component counts, native/capture comparisons, preserved section failures and source-semantic limits. Final focused tests: **21 passed in 0.31 s**. Final collector `run_20261008T222211Z_3c1393`: **exit 0, 13 records, no source/item failures**. The first attempt's string/integer Body-binding failure is preserved; only that actual failure was repaired before the successful rerun. No further collector or old audit was run.

Capture has fewer coordinates and different index connectivity; all triangle counts match, while every world-metre float32 triangle multiset is unequal. Separate local-vertex/placement rounding may explain the positional result. **Neither inequality proves material geometry loss nor disconnected original indices prove physical gaps.** Native original-index topology does not provide a closed-solid qualification route. Complete physical occupancy/clearance remains unavailable. The owner accepts B1 as native facts with the explicit transport/material limits in the final note and accepts the bounded captured-source identification views for source interpretation. **B2 remains unimplemented and deferred; current scope and the display-only hull delivery are recorded in the current-owner-scope section above.**

### Evidence-led branches

**T — original topology / index transport.** First verify the native IFC digest against the frozen identity. Inspect these object/representation IDs, underlying items, any mapped-item lineage/transforms, original coordinates/index arrays, declared closed flags and face orientation. Use original index adjacency to locate open boundaries or multiply incident edges and distinguish native topology from evaluated-capture transport. Determine whether native indexing supports a closed solid without coordinate welding. Preserve both representations and their provenance; if a different native extraction qualifies, issue new derived evidence rather than rewriting capture meshes or clearing old flags. Original coordinate equality does not authorize merging indices. Declared IFC `Closed` or a successful tessellation alone is not proof.

**S — section / numerical failure.** For the door/windows with cut residuals and dark-green pair with dangles, retain original face/edge identity, section endpoint-degree evidence and residual geometry. If native topology qualifies, trace only the failing plane edges and contours to separate source openings, overlapping shells, intersection computation and floating-point noding. Existing indexed-edge identity is the first comparison. Any numerical failure leaves the affected section unknown with original error and residuals. No snap, buffer, weld, `make_valid`, precision repair, closure, tolerance deletion, inferred fill or automatic alternative slicing backend. An alternative algorithm proposal requires concrete failing evidence and separate review before expanding this route.

**M — material / shell interpretation.** The proxy with no boundary edges still has nonmanifold edge/vertex counts; two planar faces do not establish material. The yellow pairs also have clean-looking plane faces but open 3D topology. Inspect authored representation/item and type/occurrence facts for separate solids, surfaces, voids, nesting/overlap and part membership. Reuse the accepted connected-shell audit as a bounded diagnostic once topology permits it; it does not certify 3D self-intersection or physical material. Do not infer union, XOR, cavity, thickness or volume from orientation, name, colour or projected outline. Existing `participation=exclude` is the source/Analysis policy: the accepted B3 design Body-mass experiment intentionally evaluates these context objects; that experiment must not silently change the canonical policy.

**U — genuinely unavailable solid semantics.** If the native representation supplies only an open surface/tessellation and neither source topology nor authored facts establishes the physical volume, retain localized unknown and an explicit unsupported reason. Zero crossings in the dull-yellow pair can become plane absence only with evidence that all intended physical parts are represented and none contains plane material; an unrepresented connection/envelope cannot be invented. A request for a qualified authored solid or explicit source interpretation is a legitimate blocker. No material envelope is inferred from XY hulls or a band projection.

### Existing facilities, future reach and sequence

Installed Pixi facilities already include Python 3.12.13, IfcOpenShell 0.8.5, Shapely 2.1.x, NumPy, trimesh 5.x, NetworkX and Matplotlib. No new dependencies are proposed. `adapters/ifc_bonsai.py::load_ifc_neutral_scene` is a read-only facts-to-NeutralSceneV2 adapter; its native extraction separates Body/Analysis and records missing-geometry uncertainty, source representation identity and SI world coordinates. Its full-scene importer need not be invoked to inspect 13 known entities: use the installed IfcOpenShell read-only source/STEP lookup for the targeted evidence, following existing transform/unit/error conventions. Any reuse of private `_native_mesh_record` is limited to a future diagnostic, not a new public adapter API.

`features/geometry_substitutes.py::mass_patch_from_mesh` and `features/geometry_views.py::{plan_projection, component_shape, vertical_intervals_at, vertical_profile}` provide existing transport/geometry diagnostics. Projection can contain approximation/fallback paths; interval/parity logic needs closed/manifold assumptions. They cannot replace qualified exact-plane physical occupancy. The accepted runner's `section_source`, indexed-edge and connected-shell/parity audits are design diagnostics; A does not relocate their geometry machinery into production.

1. **B1, targeted facts:** after A review, add only `scripts/design/space_field/run_b3_native_source_qualification.py` and, if it has nontrivial extraction/validation logic, `test/test_b3_native_source_qualification.py`. Read the exact frozen IFC and 13 refs; verify identity before inspection. Emit a fresh unique run under `outputs/design/b3_native_source_qualification/` with per-source STEP/GlobalId/Body-item refs, native/capture hashes, units/transforms, topology/section reason classification and remaining blockers. This first step gathers evidence; it does not produce a new occupancy field. Add a focused B evidence note and update this plan/linked docs when results exist. No existing production module, fixture, config or export needs to change for B1.
2. **B2, only supported derivation:** where B1 proves a source route, derive new plane-local evidence with existing indexed geometry facilities, retain original capture comparison and all unsupported rows. Gather failure-focused tests for actual new branches; use Pixi focused checks, not an exhaustive solid-validity study. Stop investigation of a row when the evidence identifies an unavoidable semantic gap. Exact code reach for a new algorithm is contingent on B1, and must be stated before that implementation; this plan does not authorize a general solid engine.
3. **B3, qualification review:** reconcile included/excluded/unavailable records against the frozen inventory, document every source outcome and distinction below, then request only consequential source interpretation. If qualified evidence changes, generate a new versioned source/field package after the supported derivation is reviewed. Preserve accepted packages. Re-evaluate affected masks/distances/connectivity with retained unknown; do not overwrite A or relabel the accepted comparison. Complete physical clearance remains null until its target is independently complete.

### What completeness would mean

**Imported capture/inventory completeness:** every intended physical contributor to historical S3 at the plane must be accounted for by qualified occupancy, proven plane absence, justified semantic exclusion or proven outside-domain irrelevance. All 358 records/354 Body meshes, four semantic nonmass exclusions, missing/unloaded records and non-product entries need ledger coverage, not just the 13 failures. Five outside windows need no interior-occupancy resolution if their irrelevance is proved for S3; they remain relevant to any complete raw/outside-domain distance target. Resolving the eight overlapping exceptions is necessary but is not by itself a completeness certificate. Existing qualified sources retain their limited compound-shell/3D-material assurance until supported for the stronger claim.

**Owner-bounded completeness target:** any eventual claim is “complete for the frozen qualified imported inventory and declared domain,” with its included/excluded/unavailable ledger and distance target explicit. Exhaustive whole-model or real-world completeness is outside this continuation. Hidden, unloaded or omitted contributors are not certified absent; document that scope limit rather than adding a world-completeness audit.

Even if occupancy becomes complete for a stated scope, finite point sampling remains a discrete approximation: missing the 0.014987329164664116 m² subset demonstrates why occupancy completeness does not certify empty cells or routes. World height, S3 horizontal purpose and frame stay settled. Complete physical clearance needs a complete declared distance target, independently of complete S3 interior samples.

### Autonomous work and consequential owner question

After approval of the sequential route, ordinary reversible implementation of A and the targeted B1 identity/native-fact collection can proceed without repeated permission. Source enumeration, original-index comparison, failure classification and evidence-preserving diagnostics are routine within that approved scope. No live mutation, source repair or new material semantics are implied.

If native facts leave open surfaces, overlapping parts or omitted content, present the exact source/item records and a concrete local illustration only if it helps interpret them. Then ask the consequential question: **what physical material/solid and inventory scope are these authored source objects intended to represent?** Ask only for the affected sources; do not ask the user to reapprove accepted S3/connectivity images or the eye height. A human interpretation must be recorded as an interpretation; it does not manufacture absent geometry or numerical proof. If sufficient evidence cannot be obtained, B stays partial/unknown and B3 stays OPEN.

## Plan handback boundary

The owner accepted A, accepts B1 facts with the final evidence note's explicit transport/material limits, and accepts the [captured-source identification views](evidence/b3-unresolved-source-identification-views.md) for source interpretation. There is no live `formal_field` promotion or package-A B3 closure. Final run `run_20261008T223459Z_635777` shows historical S3/holes and eight STEP labels in plan, plus equal-metre-scale 3D views of the door, counter/shelves and two three-source assemblies with z=1.6 shown. The saved script completed with exit 0 and frozen-input assertions passed; the owner visually reviewed all five final PNGs and no more rendering or verification is required. The first shade failure and successful pre-label-fix run are preserved. Frozen capture only; no IFC parsing/tessellation rerun, Blender, mesh/source/live edits, repair or field regeneration. The owner excludes the seven counter/plant sources from furniture-level analysis and selected three closed 3D convex mesh proxies, now active only as physical occupancy substitutes in the bounded field. The prior accepted 2D hull package is history, and the new 3D mesh delivery is documented in the identification evidence note; the accepted five identification PNGs rendered original triangles, not hulls. Door-route investigation and B2 remain paused; no physical material policy or occupancy derivation is implemented. B3 remains OPEN.

## Accepted 3D geometry and occupancy-only handoff

The owner accepts the three generated ordinary closed 3D convex meshes in `outputs/design/b3_deferred_convex_meshes/run_20261008T225203Z_aa8aaa/` after reviewing code, final preview, execution and mesh metadata. Geometry generation is complete. The owner has decided: physical occupancy is mandatory regardless of furniture eligibility. The three proxies are active occupancy-only substitutes for seven originals; counter and plants remain excluded from furniture, group, trend, orientation, and affordance analysis. No user choice remains about counting their volume. Earlier 2D artifacts remain historical predecessors; original-source material/volume limitations, accepted A and B1 remain unchanged. B3 stays OPEN for scoped physical occupancy.

## Historical comparison-only 3D proxy eye-plane bridge — OWNER ACCEPTED

The sibling runner `scripts/design/space_field/run_b3_proxy_eye_plane_comparison.py` produced independently A-loader-readable v1 package `outputs/design/b3_proxy_eye_plane_comparison/run_20261009T074009Z_ff323e/` and side-by-side `baseline_vs_proxy_025_zero.png`. All 358 accepted original source records/errors remain intact; three distinct proxy records hold represented source IDs, original and OBJ references, convex approximation and comparison override provenance. The unchanged A loader verified accepted baseline payload hashes; the accepted proxy manifest fingerprints verified metadata and three OBJ files. Only three OBJ sections were newly qualified at world z=1.6 m with `process=False`. All three returned `qualified_closed_section`: raw per-proxy area 15.473208707089555 m² (counter), 0.5023957609352872 m² (A), and 0.5023960567241503 m² (B). Focused tests: 5 passed; runner exit 0; written package loaded through unchanged A loader; preview inspected by owner. The owner reviewed this evidence and **ACCEPTS the bounded comparison-only package**. Acceptance does not enroll the proxies or authorize B2.

The seven represented original uncertainty contributions are omitted only in this comparison because their proxies qualified. The focused tests also establish failure fallback and qualified plane-absence override. At 0.25 m / [0,0], baseline 3,888 samples were 565 outside, 3,015 conditional empty, 308 unknown, 0 occupied; comparison samples are 565 outside, 3,054 conditional empty, 0 unknown, 269 occupied. Transitions are 269 unknown→occupied and 39 unknown→conditional empty. S3-clipped occupied area changes 0.014987329164664116→16.359239442311818 m²; clipped unknown support changes 19.069186870135574→0.020499982357023327 m². Original door #6231 remains unresolved and its local unknown support remains. All four lattices have zero samples on that retained door support, so zero sampled unknown is a sampling miss, not door resolution or complete occupancy. Five outside windows remain unchanged. Complete occupancy and physical clearance remain null; convex filling establishes no exact original material or orientation. Canonical proxy enrollment remains `deferred_excluded`; B3 stays OPEN.

## Selected-domain boundary membership rule

The shared NeutralScene analysis view now accepts exact component membership in the selected `AnalysisDomain.provenance.boundary_member_source_ids`. A uniquely resolved member is omitted from interior occupancy and blocker selections while raw source, uncertainty and channel observations remain intact. The private inferred-domain handoff carries membership only from the matching qualified B2 semantic contour; `wall_source_refs` and opening host refs alone grant no exclusion. Unmatched, duplicate and ambiguous identities retain occupancy. This change does not requalify any frozen B3 capture or rewrite the accepted comparison-only package.

The selected-domain rule also applies to doors, windows, or similar infill only when exact membership is declared: they count as the closed analysis boundary and contribute neither interior occupancy nor interior uncertainty. The human declaration [`b3-domain-boundary-membership.json`](evidence/b3-domain-boundary-membership.json) binds the accepted S3 scope, source revision, and baseline source-sections hash to door #6231. Its ID is input data, not a class or STEP-number branch in the algorithm. The shared identity resolver requires a unique exact match before the B3 comparison omits a member.

Owner-accepted comparison package `outputs/design/b3_proxy_eye_plane_comparison/run_20261009T083535Z_c914e2/` applies that declaration to retained serialized original sections and the three qualified proxies. The unmodified A loader accepts the package; seven focused B3 tests and 65 NeutralScene regression tests passed. All 358 original source records and errors remain unchanged in content, all four lattice status counts match the accepted prior comparison, and S3 geometry, masks, and boundary distances are unchanged. At 0.25 m / [0,0], outside remains 565, conditional empty 3054, occupied 269, and sampled unknown 0. Clipped occupied area remains 16.359239442311818 m²; active clipped unknown support changes from 0.020499982357023327 to **0 m²**. The earlier accepted run and its local door unknown remain historical facts. Nonmembers retain their uncertainty, the seven proxy overrides remain comparison-only, and canonical proxy enrollment stays `deferred_excluded`. This is not complete physical occupancy or clearance; B2/live promotion is unchanged and B3 remains OPEN.

## Current occupancy-only B3 handoff — OWNER ACCEPTED

The user confirmed the general invariant: counter and plant physical volume contributes to occupancy and downstream free space even when every furniture-level analysis channel excludes those sources. The accepted three 3D convex meshes are active occupancy-only substitutes for seven represented originals in `outputs/design/b3_occupancy_only_handoff/run_20261009T091601Z_242b33/`. The unchanged A loader reads the package; original records, errors, S3 geometry and all four lattice variants remain preserved. The three substitutes are each qualified positive sections and replace their original sources once. Their source records explicitly say `physical_occupancy_participation=active_substitute` and `furniture_analysis_participation=excluded`. The separate exact selected-boundary policy continues to exclude the confirmed door from interior occupancy and uncertainty.

At 0.25 m / [0,0], the handoff has 269 occupied, 3054 conditional empty and 565 outside samples; clipped occupied area is 16.359239442311818 m², clipped unknown support is 0 m², and conditional free area is 190.1616840398615 m². The conditional free area is the domain minus the qualified occupied subset and remaining unknown support; complete occupancy/clearance and inventory coverage are not established. Focused Pixi checks passed 127 tests, followed by a successful final generator exit and real A-loader check. No B2 or live `formal_field` promotion occurred. B3 remains OPEN.

The unaccepted `run_20261009T091259Z_82ca27` attempt exited 1 after writing a provisional manifest twice; its `execution.json` incorrectly records `exit_0` and `failure_note.md` marks the failure. A later `run_20261009T091441Z_77b07c` was a successful intermediate implementation; `run_20261009T091601Z_242b33` is the final single-manifest package submitted for review. The earlier accepted comparison `run_20261009T083535Z_c914e2` and all original source artifacts remain unchanged.
