# D6 semantic enclosure window repair evidence

Date: 2026-10-08 (Europe/Berlin). Status: bounded source capture, real semantic execution and reproduction complete; root acceptance pending.

The prior material-section experiment omitted windows from its 33-source input and equated bounded holes of occupied sectional mass with enclosure. Its zero-contour result is accurate for that method, but cannot establish that the real building is unclosed. The human corrected the immediate target to semantic enclosure / provisional AnalysisDomain boundary candidates, under an explicit **doors and windows default-closed scenario**. Historical reports and runs remain unchanged.

## Pre-result rule and ownership

Published plan: `docs/superpowers/plans/2026-10-08-d6-semantic-enclosure-window-repair.md`; frozen pre-result bytes: `outputs/design/d6_semantic_enclosure_window_repair/integration/run_001/published_plan.md`, SHA256 `c82e03d2c0fd81c2958cdef24111f4db853f667b3cb355ccb453e55d82bc80c5`. Compact baseline protects 18 relevant records and the exact prior progress prefix, without a whole-project crawl. Observed branch/HEAD: `codex/d6-analysis-domain-layout-handoff` / `ab55da50dfb278b639e2327008ad23a50e86973d`; preserve existing dirty work and index.

Minimal flow is source window/door/wall facts → task-specific enclosure eligibility → authored or evidenced inferred host/span association → explicit default-closed scenario carrier → provisional enclosure contours and compound scope, with physical occupancy independently retained. Non-watertight glazing or a leaf missing the 1.5 m material cut does not automatically disqualify meaningful planar opening/span geometry. Missing authored relations alone do not blanket-refuse known windows. Class/name/bbox alone do not invent an extent/host. Qualified unique inferred associations remain labelled inferred; unknown/ambiguous spans receive no seal. True unfilled openings stay open.

Carrier geometry and observed occupancy are separate. Full-height projection cannot silently close every void beneath a lintel. No buffer/hull/snapping/tolerance widening/generic gap repair, free-space, route, headroom, whole-room 3D inference, active domain or winner. World XY/world-z0 datum and 1.5 m localization cut remain experiment assumptions; source carriers need not contain material at that cut. Production contact/datum/scope authority remains deferred.

C owns this report, the plan, integration artifacts and one dated progress append. A owns `inputs/`; B owns `geometry/` under the new output root. No production/features/adapters/API/formal tests/dependency/source IFC/user Blender writes, stage/commit/branch changes, full native conversion, full suite or timing comparison are authorized. Existing chats perform scoped collaboration; checks are not independent review.

Root clarified its direct B assignment also authorizes the one design runner `scripts/design/space_field/run_semantic_boundary_view.py`; it stays at that canonical path. The current plan appends this ownership clarification, while the frozen pre-result contract remains unchanged. No semantic or production authority changes.

## Early source facts

A's read-only live inspection reports 11 walls, 16 columns, 6 doors and **5 separate IfcWindow meshes**, with 0 IfcOpeningElement/IfcRelVoidsElement/IfcRelFillsElement. Window STEP IDs: #43654, #49645, #55636, #61627, #67618. OverallWidth/OverallHeight are null and filling relationships absent. These are factual source observations; rough object locations/sizes are localization diagnostics, not qualified host/span evidence.

A captured one coherent 38-object cohort using the same live evaluated depsgraph and world-metre normalization. C chose it before real inference in `integration/run_001/cohort_decision.json`: `inputs/run_001/live_snapshot.json`, 5,692,042 bytes, SHA256 `96f40383297fdebb12ed7a26ef9dac38188ed05fcfa7def43c202fceaeb3daad`, 71,561 vertices / 142,716 triangles. All 38 are fresh together; no geometry merging. C independently compared all 33 prior mesh records' vertices, triangles, world_transform, units and transform_applied fields: identical. That isolates coverage differences to the five newly included windows and additional source metadata; it does not demonstrate disk IFC tessellation parity. A records read-only capture provenance and unchanged Blender state separately.

All five windows carry authored OM_Layout `FunctionalRole=window`, `CanonicalObject=true`, `GeometryBranch=GEOMETRY`, `AnalysisParticipation=exclude`. These fields remain unchanged. `integration/run_001/window_eligibility_ruling.json` records the explicit human door/window enclosure-scenario instruction taking precedence only for this diagnostic carrier path, with generic authored participation still excluded. Eligibility does not imply span/host qualification and is not a production participation override.

`integration/run_001/association_ruling.json` freezes B's bounded qualifier before real results: actual wall face projection minus exact occupied cut localizes residual apertures only, including within-component voids. It never enters enclosure wholesale. Actual known window/door surface/outline must evidence the same local aperture and two distinct cut-level jamb sides. Save jamb geometries/contact measurements and all alternatives; multiple qualifying hosts/apertures remain ambiguous. Authored mapping may identify a host but does not waive meaningful span. Only the uniquely qualified local aperture becomes a separate inferred scenario carrier. Unknown or true unfilled apertures remain unsealed. The fixed comparison budgets do not widen coordinates or repair closure.

## Actual reuse and semantic defect

The prior `run_boundary_height_view.infer_candidates` unions qualified wall/column material sections and uses `component.interiors` as contour evidence. `qualify_scenarios` additionally requires authored opening extent and a qualified material section. Reusing that gate would repeat the semantic window defect.

The bounded repair reuses `run_floor_plan_3d_comparison.normalize`, exact `section`/`indexed_section_segments`, box fixtures and geometry serialization, plus the prior `polygon_parts`/`contact_graph` diagnostics. `features.geometry_views.plan_projection` can project actual triangles without requiring closed volume when height-band is absent; vertical surfaces may collapse to lines, so empty polygon output alone is not proof of missing span. `component_shape` transports usable polygons. Existing authored opening/surface record helpers do not infer qualified hosts/apertures. The evaluator's nearest-entry-boundary fallback selects one host by entry centre and lacks aperture/ambiguity checks; it is not association authority here. B therefore adds only the bounded task-local association/carrier operation and names its actual call site in delivery.

## Executed source and aperture evidence

A's `inputs/run_001/source_metadata.json` verifies source identity, schema, units and all 38 STEP/GlobalId/class links without full native geometry conversion. `capture_mcp_result.json` records one read-only live evaluated capture: portable Blender 5.2.0, world scale 1, unsaved scene, dirty=false before/after, unchanged selection/active object/mode/frame/camera/counts/units. A's `mesh_equivalence_old33.json` and C's cohort check establish saved mesh equality, not disk/live shape parity.

`inputs/run_001/component_apertures.json` retains exact face indices of connected 3D wall mesh components. Five substantial bounded facade apertures occur **within individual components**: two on wall #142850 and three on #143931, approximately 10.04408 m² each, z=1..3.5 m. Their corresponding typed window surfaces provide usable spans despite all five being non-watertight, 11-component meshes. Three other raw facade rings are numerical slivers near 1e-31 m², retained separately under the existing 1e-6 m² comparison budget. Facade-projection overlaps alone are not unique mappings: opposite north/south facades can coincide, and A retains depth ranges without choosing hosts.

A's annotated source preview and `apertures_002/aperture_inventory_annotated.json` keep source geometry, columns, all window/door locations, substantial facade apertures and numerical residuals separate. Its diagonal-wall axis-face projection is partial. This source-only inventory does not choose enclosure semantics or author host relations.

## Same-cohort material versus semantic result

Final geometry is `geometry/run_002/`. On the **same fresh 38-source input**, the material-only path yields 0 enclosure contours / 0 scope proposals. The corrected semantic path yields **5 bounded enclosure contours / 1 compound provisional scope**, using 11 qualified inferred scenario carriers: all 5 windows and all 6 doors. Actual window handling is exercised; no absence-of-window or no-room claim is used to explain the old result.

| Observation | Material-only interpretation | Corrected semantic interpretation |
|---|---|---|
| Retained physical sources | 38 | Same 38, source sections unchanged |
| Structural material input | 27 qualified wall/column sections; 22.122628529470543 m² | Physical input unchanged; carrier union separately adds only qualified local scenario apertures |
| Eligible polygon components | 9 occupied components | 3 carrier components, including two isolated column components |
| Bounded contours / scope proposals | 0 / 0 | 5 / 1, diagnostic only |
| Window/door scenarios | No qualified carriers | 5 window + 6 door carriers, all inferred, observed state=null |
| Qualified physical cut union across all sources | 22.37762834827209 m² | Identical; non-watertight window/door contours remain separately retained |
| AnalysisDomain / selected candidate / free-space | none / none / not computed | Same refusal to promote or compute downstream products |

The single scope S1 is the actual connected wall-bearing **semantic carrier** component exterior with bounded holes filled after qualified closure. It has area 307.560003676415 m², no holes, all 11 wall sources, and five contour refs. It is not a bbox, convex hull, inner-only domain or five independently allocated room domains. Supporting carrier area is 28.794076358087146 m²; carrier area outside S1=0. C separately measures original wall/column sectional mass outside S1=0. Interior columns remain source occupancy in the field and are not carved out of the scope. Shared-component local wall allocation remains unresolved.

| Contour | Area (m²) | Position and measured source boundary | Qualified door/window contour support |
|---|---:|---|---|
| C1 | 56.0400006509 | Large western enclosure candidate; x=0.300..5.000, y=0.300..12.300; walls #142222/#142689/#142850/#143931 and five contour-contact columns | Door #34356 |
| C2 | 207.2409238255 | Large central/eastern enclosure candidate; x=5.150..25.300, y=0.300..12.300; eight wall sources including diagonal #143733, ten contour-contact columns | All 5 windows and all 6 doors |
| C3 | 4.5104657142 | Narrow northern pocket; x=5.150..6.459, y=8.750..12.300; walls #141159/#141626/#142222/#142850, column #73609 | Door #39005 |
| C4 | 4.8020911651 | Middle northern pocket; x=6.609..7.961, y=8.750..12.300; walls #141159/#141320/#141626/#142850 | Door #25058 |
| C5 | 6.1724459627 | Eastern northern pocket; x=8.111..9.850, y=8.750..12.300; walls #141320/#141481/#141626/#142850 | Door #20409 |

These are bounded carrier contours, not certified rooms or free-space polygons. `semantic_result.json` records exact positive-length contour support separately from carrier presence, contact connectivity, scope validity and semantic completeness. All five windows demonstrate contour support on C2; applied association alone is not treated as support.

C1/C2 are plausible large planar enclosures by their saved extent and multi-source boundaries, with semantic roles unassigned. C3–C5 are three geometrically substantial, narrow pockets in the northern partition cluster, each closed at its southern span by a door scenario carrier. Their boundaries involve several source walls, so they are not cavities inferred solely inside one wall solid. They are also distinct from the tiny diagonal locator residuals A11/A12. Available source facts do not assign room functions or certify that these pockets are separate rooms; all five roles remain unassigned. `integration/run_002/contour_location_table.json` retains full-precision bounds, representative points, actual support refs/classes/contact lengths from the already-saved geometries, without new inference or role thresholds.

S1 includes the measured exterior perimeter, internal supporting partitions/columns, qualified scenario spans, and all five filled contour interiors as one compound analysis-scope proposal. The real diagonal exterior is retained; this is not the rectangular scene extent. Interior column islands remain physical field occupancy inside the scope. Shared wall allocation and per-room extents are unresolved; S1 is neither a room count nor a union of five accepted room domains.

## Real per-source treatment table

`opening_treatment_table.json` saves all actual source identities/properties, projected visible spans, host/aperture alternatives, jamb geometry, measured distances, old material qualification, inferred mappings, scenario carriers and candidate-local dependencies. All mappings below are **geometry-supported inferred**, never authored. Old treatment for each was no enclosure carrier; the new treatment is a qualified default-closed local aperture carrier, with actual leaf/glazing mass unchanged.

| Source | Host wall STEP | Local aperture | Jamb qualification | Contour contribution |
|---|---:|---|---|---|
| Window #43654 | 142850 | A9 | Exact contact on both sides | C2 |
| Window #49645 | 142850 | A8 | One exact side; other within fixed budget | C2 |
| Window #55636 | 143931 | A22 | Exact contact on both sides | C2 |
| Window #61627 | 143931 | A19 | Exact contact on both sides | C2 |
| Window #67618 | 143931 | A16 | One exact side; other within fixed budget | C2 |
| Door #6231 | 143931 | A14 | Exact contact on both sides; mass mesh still unqualified | C2 |
| Door #20409 | 141626 | A3 | Exact contact on both sides | C2, C5 |
| Door #25058 | 141626 | A2 | Exact contact on both sides | C2, C4 |
| Door #29707 | 141997 | A4 | Exact contact on both sides | C2 |
| Door #34356 | 142222 | A5 | One exact side; other within fixed budget | C1, C2 |
| Door #39005 | 141626 | A1 | Exact contact on both sides | C2, C3 |

The three within-budget spans have measured source-to-jamb distance **9.5367431640625e-7 m** (0.953674 µm), below the original 1e-6 m comparison budget. Their exact-contact failure remains saved. **Distance-based qualification was clarified after observing the literal-contact failures in run_001**, then recorded in `integration/run_001/contact_measurement_clarification.json` before corrected run_002. The final qualification semantics were not all frozen before the first observed run; reuse of the existing numeric budget does not itself approve a production contact policy. There is no budget increase, moved coordinate, buffer or snapping. The carrier remains the exact measured host aperture, supplying thickness independently of thin source glazing. This is bounded diagnostic association evidence with its refinement history disclosed.

B retains 23 projection-minus-cut locator residuals, not 23 authored openings. Eleven are associated and closed by the qualified door/window scenario. Ten are below the comparison area budget; two diagonal-wall residuals A11/A12 remain unsealed, about 3.4968646e-6 / 1.4218075e-6 m², with one jamb each and no qualified source span. They are **not confirmed true unfilled openings**. Saved geometry associates both locally with S1; its semantic completeness remains conditional on those residuals plus global limits. Unknown/ambiguous mappings receive no carrier. The synthetic true-unfilled control demonstrates an affirmative genuine-opening case separately.

![Real semantic enclosure overlay](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/d6_semantic_enclosure_window_repair/geometry/run_002/real_semantic_enclosure.png)

C viewed the actual saved pixels: physical wall/column cut, window/door spans and labels, distinct dashed closures, unresolved diagonal residuals, numbered C1..C5 and S1, source treatment table and assumptions/legend are visible. Physical occupancy is independently shown alongside semantic carrier geometry.

## Controls, executions and reproduction

The minimal runner `scripts/design/space_field/run_semantic_boundary_view.py` uses `source_extent` → `locate_apertures` → `associate_spans` → `semantic_candidate_assembly`. `source_extent` uses actual triangle projection or actual projected triangle edges for zero-area surfaces. `locate_apertures` only enumerates local residuals. `associate_spans` qualifies unique source/host/aperture evidence. Assembly creates explicitly private geometry-only carrier copies, calls the unchanged old ring/scope constructor, strips/renames inherited material claims, and verifies original source-section serialization is unchanged. No production B2 candidate algorithm is called.

Pre-query oracle JSON and saved runner assertions pin three controls: known non-watertight window above the material cut gives 0 material / 1 semantic contour and 24 m² scope; true unfilled opening gives 0 semantic contours; duplicate qualifying hosts remain ambiguous with no carrier. `controls_001` failed before inference on NumPy integer-index coercion in the synthetic fixture. B fixed conversion to plain integers; `controls_002` passes, and all real runs execute the same controls. Failed logs remain intact.

Actual corrected invocation:

```powershell
pixi run python -B scripts/design/space_field/run_semantic_boundary_view.py --snapshot outputs/design/d6_semantic_enclosure_window_repair/inputs/run_001/live_snapshot.json --contract outputs/design/d6_semantic_enclosure_window_repair/integration/run_001/published_plan.md --datum 0 --cut-height 1.5 --output-dir outputs/design/d6_semantic_enclosure_window_repair/geometry/run_002
```

Final worker exits 0, no timeout, 12.806919 s under the predeclared 120 s budget. Earlier real run_001 also exits 0; it used literal jamb contact only (3 windows + 5 doors, 3 contours / 1 smaller scope) and remains preserved as superseded evidence. The corrected run compares spans against the original budget; no coordinates change. Actual argv/exits/elapsed times are evidence, not a timing study.

Fresh-directory reproduction uses identical corrected parameters plus `--reproduce-of outputs/design/d6_semantic_enclosure_window_repair/geometry/run_002` and `--output-dir outputs/design/d6_semantic_enclosure_window_repair/geometry/run_003`. It exits 0 without timeout; **17 deterministic files are byte-identical**, including source sections, physical occupancy, material baseline, host locator/apertures, source treatment table, carriers, semantic result, controls/oracles, provenance, frozen contract/three initial decisions, PNG and runner snapshot. Command/timing metadata and replay checks remain separate. The contact-measurement clarification is independently fingerprinted in B's delivery audit.

A's final `inputs/run_001/validation_002/verification.json` passes source/identity/mesh/capture/preservation checks; its first UTF-8 script read under GBK failed only the audit and remains in `validation_001/`. Corrected explicit UTF-8 audit exits 0; source/capture/geometry bytes do not change. A's final report and artifact manifest are `inputs/run_001/report.md` / `artifact_manifest.json`.

B's executable audit, evidence notes and compact final geometry manifest are under `geometry/delivery_001/`. C's executable `integration/verify.py` reuses earlier digest/JSON helpers, verifies 18 relevant protected byte records and the original progress prefix, chosen 38-source identity/cohort, all 33 prior mesh fields, window authored properties, provisional 5/1 result, original material inside S1, worker manifests and 17 replay bytes. Its actual result is saved in `integration/run_002/verification.json`; final document/runner/ruling/worker-manifest fingerprints are in `integration/run_002/delivery_manifest.json`. Scoped whitespace/docstring checks accompany delivery. These checks reconcile collaborator outputs and do not constitute independent review, production acceptance or a whole-project immutability claim.

Source/frame/datum/parity/participation/scenario limits remain explicit; carrier closure does not certify semantic completeness.

## Next implementation recommendation

If separately authorized, place a bounded private semantic-carrier operation alongside the existing `_b2_boundary_diagnostics` path in `features/neutral_scene_views.py`. Preserve factual source records and occupancy; pass explicit task/scenario authority, source span geometry, association alternatives/provenance and separate carrier geometry. The existing production projected view cannot silently stand in for a qualified enclosure span, and the old material-section seal gate cannot qualify glazing by volumetric watertightness. No general importer, role registry or second room engine is needed.

Focused future checks in the existing neutral-scene analysis regression path should exercise a window surface absent at cut, a non-watertight leaf with meaningful extent, a true unfilled opening, ambiguous/depth-overlapping hosts, exact versus budget-qualified span measurements, authored participation exclusion versus explicit task authority, and multiple contours sharing one scope without occupancy loss. These are recommendations only; no formal tests or production changes occur here.

Production still needs authored floor/datum policy, acceptable inferred association/contact policy, thin-surface span qualification beyond this cohort, local residual classification, shared-wall allocation, participation/scenario authority and domain confirmation. Disk/live geometry parity and observed leaf/window state remain unverified. Recommend LIMITED SEMANTIC ENCLOSURE DESIGN EVIDENCE, with root acceptance pending and no promotion/integration approval.

STOP FOR D6 SEMANTIC ENCLOSURE WINDOW REPAIR REVIEW


## 2026-10-08 Root decision — accepted limited design evidence

Root decision after reading the consolidated report and execution notes: **ACCEPT LIMITED SEMANTIC ENCLOSURE DESIGN EVIDENCE** for the current real 38-source cohort and explicitly default-closed door/window scenario. This accepts the corrected separation of semantic enclosure from physical occupancy and the demonstrated geometry-supported inferred carriers. It is not independent verification, production integration approval, a global 1 micrometre tolerance decision, five certified rooms or active AnalysisDomain promotion.

Literal-contact run_001 remains 8 carriers / 3 contours; later distance-qualified run_002 remains 11 carriers / 5 contours. Distance qualification was clarified after observing the first run, using the recorded experimental 1e-6 m budget; inferred mappings remain distinct from authored relations. Unclassified diagonal residuals A11/A12, assumed floor datum, unverified disk/live geometry parity and shared-wall allocation limitations remain unresolved. Frozen pre-result contract and all execution evidence remain untouched.

The next recommendation is a minimal, separately scoped B2 private integration of factual source records plus semantic carriers, with occupancy preserved. This decision does not authorize that implementation or further comparison experiments. Documentation-only closure updates this phase's progress status and the two affected delivery fingerprints, without rerunning geometry or a new audit campaign.

STOP FOR D6 SEMANTIC ENCLOSURE WINDOW REPAIR REVIEW
