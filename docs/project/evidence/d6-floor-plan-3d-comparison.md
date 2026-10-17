# D6 floor-plan versus 3D comparison

Started: 2026-10-07; synthesis: 2026-10-08 (Europe/Berlin). Status: executed bounded experiment; design review pending. The pre-result plan is preserved in `integration/run_002/published_plan.md` with its machine matrix.
Coordinator owns this report and `outputs/design/d6_floor_plan_3d_comparison/integration/` only. No production changes, commits, dependency installation, full pytest, or full native IFC geometry conversion are authorized by this experiment. Root chat owns final acceptance.

## Comparison contract published before geometry results

Input A is the read-only disk IFC4 `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, expected 408617800 bytes / SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`. Worker A verifies identity and inventories authored representations without full tessellation.

Input B is the frozen evaluated structural snapshot `outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json`, expected SHA-256 `c5659dcd99d8c4f20b97efd2cc37352d6305436e20e698ccbcf8c89abfe67867`. Worker B verifies identity, finite world coordinates, metres and once-applied matrix_world provenance, and 11 walls / 16 columns / 6 doors. Do not multiply the snapshot by the disk IFC's mm-to-m factor. Adapter IFC IDs remain nullable; use the saved external association table. Disk-to-snapshot geometry parity is unverified.

The single reported storey has no authored Elevation or placement in prior evidence. A must check whether another trustworthy datum exists. Until evidenced, the real experiment uses world XY at z=0 as an explicitly assumed diagnostic datum. `section_at_1p5m` then means world z=1.5 m conditional on that assumption, never an authored floor-plan fact. Synthetic datum is authored z=0.

| Method ID | Operation and setting | Matched question / independent expectation | Interpretation |
|---|---|---|---|
| `authored_plan_if_qualified` | Actual PLAN_VIEW / FootPrint / 2D representation; preserve context, placement, unit and item provenance | Is relevant structural geometry represented, with scope and height semantics sufficient for this task? Compare contours at identical Z only when authored height is demonstrated | May be not_available or unsupported. PLAN_VIEW alone proves neither completeness nor a 1.5 m cut; furniture Analysis is not a room plan |
| `section_at_1p5m` | Exact mesh-plane section at datum + 1.5 m | Occupied contours at that Z; closed analytic solids compared with algebraic box cross-sections | Missing low or overhead mass is expected; open/unreliable mesh contours remain partial diagnostics |
| `finite_band_projection` | Positive-overlap projection of band [datum+0.0, datum+2.0] m; experiment-only setting | Does any occupied volume intersect this specified band at each XY? Analytic box XY support conditional on positive band overlap | Distinct estimand from the section. Retain existing helper fallback/uncertainty; do not claim exact arbitrary-solid volume projection from unqualified surface fallback |
| `full_height_xy` | Existing plan_projection without height band | Union of physical XY supports across all Z | Diagnostic reference; overhead and low objects can block its footprint even when absent at 1.5 m |
| `genuine_3d_reference` | Existing vertical triangle intersections plus design-only bounded surface crossings using the existing triangle-ray parameter routine; forward-ray helper retained for a contrast self-check | Occupied vertical intervals, segment/surface crossings at stated heights, and local overhead lower surface. Algebraic box/slab intersection supplies independent analytic oracle | Genuine 3D queries, not a 3D render or stack of 2D samples. A segment wholly inside a solid or coplanar with a face is outside the verified crossing semantics. No automatic full-room volumetric enclosure, walkability or routing claim |

All physical wall and column mass remains in occupancy. A boundary column may supply enclosure evidence only when geometric contact/closure is actually evaluated. Known synthetic opening-host semantics are kept apart from real missing opening relations; no real IfcDoor is silently converted to a void or sealing polygon. No inferred candidate becomes an active AnalysisDomain. The real scene's floor, ceiling and domain closure are unqualified; free-space, routes, route width and UI integration remain unavailable.

## Bounded scene matrix and error budget

Worker B implements at most four analytic scenes plus the one real snapshot, reusing existing 3D fixtures where suitable. No test-framework project is needed. Each analytic scene is one experimental unit; its methods, probes and timing repeats are repeated observations, not independent samples.

| Scene | Required source solids / semantics | Independent expected contrast |
|---|---|---|
| `walls_columns` | Vertical walls z=[0,3]; interior and boundary columns with explicit contacts; authored diagnostic extent | At 1.5 m all masses remain; interior column occupancy never disappears. Boundary support and polygon validity are separate from enclosure |
| `opening_lintel` | Host wall assembled around an explicitly authored opening z=[0,2.1], with lintel above; open scenario | Opening centre has no mass at 1.5 m; local vertical ray returns lintel interval; upper segment can hit while lower segment clears. Full-height projection can fill the opening |
| `low_partition` | Partition z=[0,1.0] and a bounded probe at z=0.5 / 1.5 | Exact 1.5 m section omits partition; band [0,2] and full-height include it; true 3D low/high segments differ |
| `overhead_bridge` | Slab/beam z=[2.4,2.8] over a known XY probe | Section and [0,2] band omit it; full-height includes it; vertical ray records 2.4 m lower surface, high segment hits, low segment clears |
| `real_structural_snapshot` | All 33 saved structural meshes, own topology flags and external IFC mapping | Supported object-local section/projection/3D observations only; no invented watertight room or opening subtraction |

Analysis plane: origin=(0,0,datum), orthonormal world XY basis; no view-origin offset is used in measurements. Record any render-only translation separately. Lengths m, areas m². Geometry comparison budget: 1e-6 m linear / height agreement on analytic scenes and 1e-6 m² symmetric-difference area; reject failures rather than widening tolerance after observing results. Existing positive-band-overlap tolerance 1e-9 m is separately recorded. Avoid ambiguous coplanar probe positions; use interior probes with >1e-6 m boundary margin. Real mesh quantization/topology/section closure observations are reported rather than repaired or promoted. Area, topology and volumetric estimands are never averaged into one accuracy score.

## Timing and deliverables

Inspect callers and reuse `features/geometry_views.py`, `features/geometry_substitutes.py`, `features/mass_patch_collection.py`, `adapters/blender_geometry.py` and existing design runners before adding design-only helpers. Exact section helper, if required, belongs only to B's runner. Record actual imported paths, versions, hashes and helper uncertainties.

Save commands, stdout/stderr, actual exit/timeout, result JSON, annotated PNG/SVG, source/method provenance and byte/SHA-256 manifests in fresh owned run directories. Images show geometry, cut plane/band and masks/contours with readable legends. View actual PNG pixels. A owns authored-input inventory/qualification; B owns fixtures, geometry and timing; coordinator owns matrix and synthesis. Never overwrite a prior run or a peer's artifacts.

After A completes and concurrent heavy work stops, B runs final timing serially: one untimed warm-up followed by five rounds, alternating forward/reverse method order. Preserve every sample and median/min/max, no significance claims. Separate snapshot disk-read/JSON decode, adapter/patch extraction, geometric query, inference (not executed if absent), render and serialization. Record probe count/workload for 3D; its different answer cannot support a like-for-like speedup ratio. Native whole-file timeout is historical ingest evidence only, not a denominator against cached slicing. Any earlier concurrent timings remain exploratory.

## Existing evidence and skill use

Read AGENTS.md, architecture memory, current IFC-neutral input contract, B2 real-input report and independent review, and native timeout repair report. Current observed branch is `codex/d6-analysis-domain-layout-handoff`, HEAD `ab55da50dfb278b639e2327008ad23a50e86973d`; existing dirty/untracked work is preserved. Prior accepted LIMITED B2 evidence verifies snapshot-to-adapter provenance and refusal, not native parity, domain qualification or a full 3D algorithm.

Actually read experimental-design and verification-before-completion SKILL.md files. Applied repeated-observation / estimand / timing-confound controls and fresh evidence gates. No skill scripts or extra dependencies are needed. Skill attribution: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065), DOI 10.48550/arXiv.2609.00065. Bibliographic record checked on 2026-10-07; current revision dated 2026-09-02. This credits the procedural skill, not a geometry-validation oracle.

## Results / decision proposal

Worker A's executed metadata inventory (`native_plan/run_001/inventory.json`, worker exit 0; outer 15.745 s, parse 13.111 s) accounts for 33/33 structural STEP/GlobalId/class identities. All 449 authored shape representations are 3D Tessellation: Body=354, Analysis=95. There are zero PLAN_VIEW / FootPrint / 2D candidates across the disk source; all 33 structural objects have zero plan candidates. `authored_plan_if_qualified` is **not_available for this IFC**, so the experiment derives geometry from the separately identified snapshot. This finding does not say that IFC4 cannot encode a plan.

Storey #13, GlobalId `2udSq8mkbQwxg0XrW$uM_r`, name Level 1, has null Elevation, no placement and no representation. Model world-coordinate-system identity establishes coordinate axes, not an authored floor datum. The real 1.5 m section remains conditional on world-z=0 as an experiment-only datum. No default height/backend/threshold/policy or production mode is approved.

### What the executed methods answer

Final geometry evidence is `geometry/run_006/`, worker exit 0, timed_out=false, outer 27.767 s. All four analytic scenes passed independent dimension-based XY area/symmetric-difference, component/hole, triangle vertical-interval, bounded-crossing/slab-algebra and mesh-volume checks. The source dimension/oracle records precede queries. These are deterministic examples, not a statistically representative scene sample.

| Analytic scene | Exact 1.5 m section area | [0,2] m band area | Full-height XY area | Genuine 3D result / practical difference |
|---|---:|---:|---:|---|
| Walls + boundary/interior columns | 5.0 m² | 5.0 m² | 5.0 m² | Two occupied components / one hole; interior column remains physical mass. Boundary column physically closes the south-wall gap in this explicit synthetic geometry; no active domain is created |
| Known opening below lintel | 0.9 m² | 0.9 m² | 1.2 m² | At opening centre, interval [2.1,3.0] m; z=1.5 segment has no crossings, z=2.5 segment crosses lintel at t=0.5/0.65. Full-height XY fills the opening's footprint |
| Low partition [0,1] m | 0 m² | 0.5 m² | 0.5 m² | Low z=0.5 segment crosses; z=1.5 clears. A single eye-height section omits the low obstacle |
| Overhead bridge [2.4,2.8] m | 0 m² | 0 m² | 2.0 m² | Local interval [2.4,2.8] m records the lower surface; z=1.5 clears, z=2.6 crosses. Lower-surface height is conditional on synthetic datum, not verified human headroom |

The forward-ray-versus-bounded-segment self-check also passed: a bridge beyond the endpoint hits the infinite ray but gives no segment crossings. The coplanar cut self-check explicitly refuses area; it does not shift the plane or substitute a band. Physical wall/column occupancy, polygon validity, component connectivity and enclosure remain separate facts. Fixture box dimensions provide an independent oracle; same-scene methods and timing repeats remain repeated observations.

### Real structural result and qualification

The final comparison retains all 33 objects and exact saved external STEP/GlobalId associations. Adapter source_id/source_class remain null; world-metre vertices are byte-for-value unchanged through the adapter, with no second matrix or 0.001 scale. Independently measured triangle topology plus Trimesh watertight/winding checks qualify 32 meshes for the limited solid-interval/section interpretation; door `live-step-6231` is non-watertight and remains contour-only. Source is_closed/is_manifold flags remain None. Accordingly, raw vertical helper output still carries `open_or_nonmanifold_geometry`; the separate measured qualification is visible alongside it and does not rewrite transport facts.

| Real method | Reported occupied XY area | Components / holes | Coverage / interpretation |
|---|---:|---:|---|
| `section_at_1p5m` | 22.377628 m² | 8 / 3 | Partial mask from qualified faces of 32 objects; unqualified door retains raw contours (four cut edges) |
| `finite_band_projection` | 28.890460 m² | 3 / 7 | Surface projection across all 33 meshes under original flags and explicit [0,2] m band; helper uncertainty/fallback semantics retained |
| `full_height_xy` | 29.560582 m² | 3 / 6 | All-height surface projection across all 33 meshes; diagnostic reference |
| `genuine_3d_reference` | No planar area estimand | Not a planar connectivity test | 33 declared XY probes and three bounded horizontal segments against source triangles in the comparison; final timing deliberately uses three XY probes plus the same three segments |

These are mass areas, never room or free-space areas. Section-versus-projection totals differ both in estimand and qualification scope; do not interpret their difference as geometry error. B's saved-result-only matched-32-object reaggregation (`geometry/delivery_002/matched_32_object_diagnostic.json`) reports section=22.3776283483, band=28.7483598181 and full-height=29.5195820626 m²; it removes the asymmetric object scope but keeps the different estimands. The three real horizontal segments at z=0.5,1.5,2.6 cross the same six objects at their declared location: this real sample does not itself demonstrate a height-dependent segment contrast. That contrast is demonstrated by the analytic low partition and overhead/lintel scenes. A supported real example is wall `live-step-141159` at XY=(6.5335819721,10.5250000954), whose triangle-derived occupied interval is [0,4.5] m with the original uncertainty and separate measured qualification. None of these probes verifies whole-room 3D enclosure.

The exact-section backend required a demonstrated numerical correction confined to B's design runner: raw Trimesh mesh_plane computes a shared edge from opposite triangles with slightly different endpoints, leaving false dangles. Indexed-edge interpolation computes each source edge crossing once and assembles contours without coordinate snapping, vertex welding, tolerance widening or source repair. Raw Trimesh segments/residuals remain saved separately. Earlier runs expose the failures: small area errors alone hid wrong component/hole counts. After shared fixture endpoints and indexed-edge assembly, analytic topology agrees, and qualified real contours close. The unqualified door remains partial. This is an experiment backend result, not an approved production backend.

### Timing: where work is saved, and what has not been compared

A finished parsing, streaming source checks and heavy hashing before coordinator released B's serial window. Final timing `geometry/timing_001/` exited 0 with no timeout: one warm-up, five serial alternating-order rounds, 77.435 s outer. All five geometry payload SHA-256 values agree. The following times are geometric-query boundaries on the frozen 33-object snapshot, not native IFC ingestion or room inference.

| Method / workload | Median seconds | Min–max seconds |
|---|---:|---:|
| Exact section, indexed-edge assembly plus retained raw Trimesh diagnostics | 0.934 | 0.724–0.993 |
| Existing finite-band projection, all 33 objects | 3.594 | 3.051–5.616 |
| Existing full-height XY projection, all 33 objects | 4.535 | 3.784–7.496 |
| Genuine 3D, three fixed XY probes + three segments, each against all 33 objects | 0.941 | 0.861–1.168 |

Separate per-round phase medians: snapshot byte read 0.001419 s; JSON decode 0.061049 s; adapter/patch/topology extraction 0.794467 s; payload serialization 0.111154 s. Comparison rendering is separately observed at 2.071 s, outside the final timing loop. Inference was not executed, not measured as zero. A's metadata parse 13.111 s is a separate exploratory ingest observation. All raw samples/order/boundaries are retained; one slower round and small n prevent stable performance-generalization claims.

Reusing a previously evaluated snapshot avoids repeating native tessellation, but acquisition/extraction cost was paid earlier and is outside these query timings. Historical whole-file native timeout remains historical failure evidence; it is not an algorithm speedup denominator. This run does not demonstrate that all 2D analysis is faster than 3D: the bounded six-query 3D workload is about the same measured cost as this section and cheaper than whole-scene projection. Those workloads answer different questions, so no speedup ratio or single accuracy ranking is justified. Complete volumetric room analysis has not been timed or verified.

### Decision proposal and short limits ledger

Evidence supports retaining two conceptual capabilities: explicit height-conditioned plan/section views for planar inspection and local 3D queries for vertical occupancy and surface crossings. Authored native IFC plans can be an input option when available and task-qualified; their absence on this IFC leads to deriving views from qualified geometry. It does not require inventing an authored plan or introducing a third analysis mode.

The minimal next slice proposed for review is an explicit, opt-in derived-view request that takes source identity, plane/datum, cut or band parameters and geometry qualification; it returns contours/masks with partial status and provenance, alongside the existing bounded 3D query outputs. Use the demonstrated analytic oracles and exact shared-edge handling to qualify any later production section implementation. No implementation is authorized by this proposal, and no default height, mode, backend, tolerance, threshold or policy is selected.

| Open limit | Effect / next qualification needed |
|---|---|
| Floor datum, floor/ceiling/domain closure unqualified | Keep real heights conditional; no domain promotion, free-space, walkability, route-width or UI claims |
| Disk IFC versus snapshot shape parity unverified; prerequisites local-only | Keep source identities separate; hashes cannot recreate IFC/snapshot content elsewhere |
| One non-watertight door; raw source topology flags absent | Preserve contour-only/partial status; no fabricated opening-host relation, door state or seal |
| Coplanar area, wholly-inside/coplanar segment containment, arbitrary-solid swept-band qualification unverified | Limit results to executed section/surface projection/triangle-crossing semantics |
| Whole-room volumetric enclosure and inference not executed | Local 3D evidence does not accept complete 3D room analysis or a production volumetric mode |
| One real scene, deterministic analytic controls, five timing repeats | No independent-scene sample-size or generalized speed claim; furniture/typed Analysis trends remain outside scope |

### Artifacts and reproducible checks

All paths below are repository-relative for command reproduction. Source IFC and snapshot remain prerequisites, not newly archived input files. Images were opened and their actual pixels inspected: A's availability diagram, B's real section/band/full projection, analytic low/overhead masks and 3D cut/query overlay. Legends, axes, height labels and qualification caveats are visible without clipped content. The 3D overlay is illustrative; query JSON/oracles supply the geometric evidence.

- A: `native_plan/run_001/report.md`, `inventory.json`, `result.json`, `delivery_manifest.json`, `final_checks.json`, and `validation_001/native_plan_availability.png`.
- B: `geometry/run_006/comparison.json`, `coverage.json`, `provenance.json`, `manifest.json`, `real_top_comparison.png`, `analytic_masks.png`, `analytic_3d_cut_and_queries.png`; final serial samples in `geometry/timing_001/serial_timings.json`. Same-input separate-process `run_007/` reproduces 12 retained run_006 artifacts byte-for-byte; this is reproducibility, not independent approval. B's final audit/matched-scope evidence is `geometry/delivery_002/`.
- Integration: `integration/comparison_matrix.json`, frozen pre-result plan/matrix and baseline in `integration/run_002/`, and checked result synthesis in `integration/run_003/synthesis.json`. Final `scope_audit.json` and `combined_manifest.json` index the consolidated artifacts and raw bytes; they are coordinator consistency checks, not independent approval.

Executed successful commands, exit 0 unless their retained execution record says otherwise:

```powershell
pixi run python -B scripts/design/space_field/probe_ifc_floor_plan_representations.py --output-dir outputs/design/d6_floor_plan_3d_comparison/native_plan/run_001
pixi run python -B outputs/design/d6_floor_plan_3d_comparison/native_plan/run_001/verify_evidence.py --run-dir outputs/design/d6_floor_plan_3d_comparison/native_plan/run_001 --output-dir outputs/design/d6_floor_plan_3d_comparison/native_plan/run_001/validation_001
pixi run python -B scripts/design/space_field/run_floor_plan_3d_comparison.py --output-dir outputs/design/d6_floor_plan_3d_comparison/geometry/run_006 --native-inventory outputs/design/d6_floor_plan_3d_comparison/native_plan/run_001/inventory.json --datum 0 --cut-height 1.5 --band-low 0 --band-high 2 --budget-seconds 180
pixi run python -B scripts/design/space_field/run_floor_plan_3d_comparison.py --mode timing --output-dir outputs/design/d6_floor_plan_3d_comparison/geometry/timing_001 --native-inventory outputs/design/d6_floor_plan_3d_comparison/native_plan/run_001/inventory.json --datum 0 --cut-height 1.5 --band-low 0 --band-high 2 --rounds 5 --budget-seconds 180
pixi run python -B outputs/design/d6_floor_plan_3d_comparison/integration/synthesize.py --geometry outputs/design/d6_floor_plan_3d_comparison/geometry/run_006 --timing outputs/design/d6_floor_plan_3d_comparison/geometry/timing_001 --output-dir outputs/design/d6_floor_plan_3d_comparison/integration/run_003
```

Fresh-run commands refuse existing run directories: choose a new directory to reproduce. Finalization additionally checks protected raw fingerprints and source inputs, unchanged branch/HEAD/index, append-only progress prefix, exact allowed Git paths, English docstrings, parsed JSON, worker manifest hashes and whitespace; see integration scope audit for actual results. No full pytest/native whole-file geometry conversion, live Blender access, installation, production/test edits, staging or commits are part of this experiment.

Coordinator baseline initially failed before inputs were read because of a wrong parent-directory index (exit 1, preserved in `integration/run_001/`); corrected fresh baseline `integration/run_002/` exited 0 and verified the two input hashes plus 790 protected files. B retains earlier runner failures and exploratory masks; their exit-0 area-only checks are not mistaken for final topology qualification. A retains its transient final-check shell-quoting failure separately. Final acceptance remains with the root chat/human; this report is not an independent review of our collaboration.

STOP FOR D6 FLOOR-PLAN VS 3D DESIGN REVIEW
