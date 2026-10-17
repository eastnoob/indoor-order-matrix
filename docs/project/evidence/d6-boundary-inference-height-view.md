# D6 boundary-only height-view execution evidence

Date: 2026-10-08 (Europe/Berlin). Status: bounded execution complete; root acceptance pending.

The immediate question is which eligible structural geometry encloses provisional planar AnalysisDomain boundary candidates on an explicit cut plane. This phase keeps enclosure-contour evidence, source occupancy and proposed scope separate. It does not compute free-space, walkability, furniture grouping/trends, headroom or full volumetric room inference.

## Frozen contract and scope

Plan: `docs/superpowers/plans/2026-10-08-d6-boundary-inference-height-view.md`; frozen pre-result copy and compact baseline: `outputs/design/d6_boundary_inference_height_view/integration/run_001/`. Prior comparison is accepted only as LIMITED DESIGN EVIDENCE and remains unchanged.

Current observed branch/HEAD: `codex/d6-analysis-domain-layout-handoff` / `ab55da50dfb278b639e2327008ad23a50e86973d`. Existing progress modification and untracked work are retained. Coordinator owns this report, the new plan and integration artifacts; B owns the new design-only runner and geometry artifacts. No production/adapters/public API/formal tests/dependencies/source IFC/user Blender/branch/index/commits are authorized.

Frozen 33-object snapshot is `outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json`, 4318044 bytes / SHA256 `c5659dcd99d8c4f20b97efd2cc37352d6305436e20e698ccbcf8c89abfe67867`. Evaluated world geometry is in metres, matrix_world already applied once; 11 walls/16 columns/6 doors, 56561 vertices/112886 triangles. External STEP/GlobalId identities remain separate from nullable adapter source IDs. Disk IFC shape parity remains unverified; this phase reuses the previous metadata inventory rather than repeating inventory/tessellation.

Explicit experiment cut: world XY, world-z=0 datum assumption, relative height=1.5 m. Floor datum is unqualified; this is not a production default. Analytic comparison budgets stay 1e-6 m / 1e-6 m²; no hull/buffer/snapping/welding/tolerance widening manufactures closure. Exact section omissions and incomplete/coplanar contour evidence remain visible; no band substitution.

## Exact flow and reuse

`run_boundary_height_view.py` → prior `normalize(snapshot)` → existing Blender adapter/MassPatch transport → prior `section(row,height)` / `indexed_section_segments(mesh,height)` → eligible wall/column section selection → fresh design-only inference → source contact/contribution, enclosure-contour and compound-scope diagnostics.

The prior section computes each shared indexed source edge crossing once; it preserves source coordinates and raw Trimesh reference diagnostics. Original topology flags remain None; independently measured connectivity/watertight/winding observations are separately recorded, with their self-intersection limitation. Door #6231 is non-watertight in accepted comparison evidence; it must remain unresolved/contour-only here.

`run_boundary_construction_experiment._controlled_candidates` constructs ordered toy centreline/offset curves. The old enclosed-room runner is topology-only toy geometry. `outputs/design/live_ifc_boundary_candidate_comparison/run_experiment.py` reads retained candidate JSON. None computes candidates from the current mesh section. This phase therefore adds only minimal installed-Shapely union/interior-ring glue and reuses the old semantic separation of scope versus wall field, without importing toy selected/accepted flags or saved candidates.

Eligibility and support are separate: wall/column roles are eligible, actual usable sections and measured contribution determine support for each contour. An isolated interior column remains occupancy-only; its exterior cannot become a room/domain and its mass is not carved out of candidate scope. Standalone beams/furniture/unknown objects are excluded only from this boundary-support path, with source/occupancy preserved. Integrated lintels stay within source wall geometry, governed by the cut.

One compound scope proposal may represent the actual exterior of a wall-bearing connected sectional-mass component, with bounded holes filled. Bounded interior rings are separately numbered enclosure-contour candidates. Several rings within one component share the one scope proposal; per-room wall allocation/local extents remain unresolved. This retains the relevant physical wall mass without silently choosing empty interior only or a scene bbox. No candidate is selected/promoted; no active AnalysisDomain is created.

Default-closed doors are an explicit user-requested scenario, not observed IFC state. Only qualified host/location/extent/closure geometry allows a separately tagged diagnostic seal. Missing real opening-host relationships cannot be filled from door class/name/bbox. Closed observed wall geometry does not resolve missing opening/door semantics. Local evidence limitations are attributed where geometry actually supports association; global unknowns remain global.

## Executed results and decision recommendation

The explicit world-z=1.5 m exact wall/column section produces **zero bounded enclosure contours and zero compound scope proposals**. All 33 physical source records remain. Recommend retaining this as LIMITED BOUNDARY-ONLY DESIGN EVIDENCE, with no candidate promotion or production integration. The result is specific to the frozen structural subset, exact contact policy and assumed cut datum; it does not certify that the building has no rooms.

Final diagnostic result: `outputs/design/d6_boundary_inference_height_view/geometry/run_002/`. `run_001` is preserved as the first successful result before adding source-contact counts and clearer no-contour figure diagnostics. The correction changed presentation/evidence, not the zero-contour result; no gap repair or additional geometry mode was introduced.

| Observation | Actual result | Interpretation |
|---|---:|---|
| Physical source records | 33 | 11 walls, 16 columns, 6 doors retained |
| Usable eligible sections | 27 | All 11 walls and 16 columns are qualified at this cut |
| Door sections | 5 qualified; 1 contour-only | Door `live-step-6231` remains unqualified/non-watertight; doors do not supply structural support |
| Eligible sectional union | 22.122628529470543 m²; valid | Physical occupancy geometry; no domain inference from its exterior alone |
| Occupied polygon components | 9 | Seven wall-bearing components without bounded rings, two isolated column components |
| Source-contact graph | 3 groups; 30 contacts | Exact positive-area or positive-length contacts; source identity can span disconnected sectional pieces, so this is not geometric component count |
| Bounded holes / enclosure contours / compound scopes | 0 / 0 / 0 | No wall-bearing bounded enclosure at the requested exact cut |
| Columns contributing to an enclosure contour | 0 | All 16 retain occupancy; this does not declare them generally nonstructural |
| Assumed-closed real door seals | 0 applied; 6 refused | All refuse with `host_relation_unresolved`; observed state stays null |
| Selected candidate / active AnalysisDomain | none / none | No room/free-space/route result |

`boundary_result.json` retains nine actual occupied component geometries, STEP/GlobalId source refs, explicit no-scope reasons, contact graph and measured separations. `candidate_table.json` contains empty scope/contour arrays. No extent is substituted when enclosure is unavailable. Seven wall-bearing no-scope records retain their wall mass; two column-only records have reason `no_wall_bearing_bounded_ring`.

The figure shows four shortest distinct component-pair separations: G1=1.000000 m, G2=2.050000 m, G3=3.542644 m, G4=4.017631 m. JSON preserves the full per-component nearest-separation observations, including reciprocal pairs. These distances demonstrate disconnection only; they do not establish authored opening locations or authorize sealing. The coordinator viewed the actual saved PNG pixels: labels/legend, separate occupancy and inference panels, unresolved door contours, no-contour table, and explicit datum/parity limits are visible.

![Real boundary-only height-view diagnostics](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/d6_boundary_inference_height_view/geometry/run_002/real_boundary_height_view.png)

## Runnable analytic controls

The runner writes `control_oracles_before_queries.json` before evaluating controls. It reuses the prior fixture dimensions and exact section helper; expected areas come from declared rectangle dimensions, not another call to the inference under test. The installed Shapely union is the only new geometric glue.

| Control | Saved passing evidence |
|---|---|
| Known wall gap completed by boundary column | One contour, one scope; contour area 19.25 m²; scope area 24 m², no scope holes |
| Remove boundary column | Zero enclosure contours; original contour probe lies in the unbounded complement after removal |
| Interior / isolated column | Interior column has no contour support and remains occupancy; isolated column produces no scope |
| Add excluded furniture | Scope/contour payloads identical; physical source count increases by one |
| Qualified synthetic default-closed seal | One contour; explicit authored extent and positive-length contact to each declared wall host |
| Open scenario / missing host / missing closure geometry | Each produces zero contours; refused seal reasons retained |

The closed synthetic case leaves physical source records and input masses unchanged; the hypothetical seal is separately tagged scenario geometry. Its 24 m² compound scope contains the 4.75 m² supporting mass plus the 19.25 m² bounded interior, including the interior column's physical occupancy in the field. The scope is never defined as empty interior minus columns. Exact contour contact and leave-one-column-out observations are recorded separately; the removal result evaluates the original interior probe, rather than treating changed contour coordinates/count alone as proof of necessary closure. This bounded control does not establish general production opening qualification or multiple-room wall allocation.

## Execution and preservation

Actual final invocation:

```powershell
pixi run python -B scripts/design/space_field/run_boundary_height_view.py --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --datum 0 --cut-height 1.5 --contract outputs/design/d6_boundary_inference_height_view/integration/run_001/published_plan.md --output-dir outputs/design/d6_boundary_inference_height_view/geometry/run_002
```

Final worker exit=0, no timeout, elapsed 6.829424 s under a predeclared 120 s budget. The earlier run_001 also exited 0. This is a bounded execution record, not a performance study.

Replay invocation adds `--reproduce-of outputs/design/d6_boundary_inference_height_view/geometry/run_002` and uses fresh `--output-dir outputs/design/d6_boundary_inference_height_view/geometry/run_003`, with all other final invocation arguments identical. Replay exits 0 without timeout. Nine files are byte-identical: source sections, boundary result, candidate table, controls, pre-query oracles, provenance, frozen contract, PNG and runner snapshot. Execution/command metadata and the replay checks differ by design.

Coordinator runnable verification: `pixi run python -B outputs/design/d6_boundary_inference_height_view/integration/verify.py --run outputs/design/d6_boundary_inference_height_view/geometry/run_002 --replay outputs/design/d6_boundary_inference_height_view/geometry/run_003 --output-dir outputs/design/d6_boundary_inference_height_view/integration/run_002`. Its saved verification checks both artifact manifests, nine replay bytes, all 33 snapshot source identities, original frozen plan, and 18 relevant preservation fingerprints. The progress ledger is checked as its exact original byte prefix plus this phase's single append. Git branch/HEAD/index and prior tracked changed-file scope are compared with baseline; production/adapters/prior runners/prior comparison manifest remain byte-identical. This is a compact consistency audit, not independent review or a whole-project immutability claim.

Coordinator verification exited 0; scoped new-file and tracked whitespace checks passed. Final delivery fingerprints are in `integration/run_002/delivery_manifest.json`. B's completed worker notes, executable audit and 47-entry geometry manifest are in `geometry/delivery_001/`; its audit exited 0 and separately verified the three run manifests, finite JSON, PNG decoding, current input/helper/contract identities and 129 artifacts in the prior comparison delivery. Both audits are collaborator consistency checks; root/human acceptance remains pending.

Run artifacts include the runner bytes, frozen pre-result contract, source sections, boundary result, candidate table, pre-query oracles, executed controls, PNG, provenance, checks, actual argv/exit/timing and byte/SHA256 manifest. The source IFC itself is not copied: file fingerprints establish identity only, and disk/snapshot shape parity remains unverified.

## Future production call sites (proposal only)

1. Keep the adapter factual. A qualified exact-section operation would need an explicit plane/datum/height plus source geometry/provenance and a documented tolerance/coplanar/incomplete policy; the current tested operation lives only in the design runner.
2. `features/neutral_scene_views.analysis_scene_view` already constructs source view records; `_b2_boundary_diagnostics` currently emits source/occupancy/refusal evidence with `conditional_support=False` and `b2_loop_closure_policy_deferred`. Any later boundary candidate inference should attach separate evidence to that private path, retaining wall/column occupancy and domain-shell identity exclusions. This experiment does not change or claim to execute a production B2 candidate algorithm.
3. Existing `test/test_neutral_scene_analysis_regression.py` is a plausible later focused verification site for candidate-support eligibility, interior-column occupancy, qualified-seal refusal and retained downstream refusal. No formal tests are added in this phase. Geometry controls must also pin shared component/multiple contour scope ambiguity and exact open gaps without repair.

Production still needs explicit policy choices for scope authority/confirmation, local wall allocation in shared components, opening/door qualification, tolerance/near-contact/coplanar geometry, eligibility beyond this allowlist and public serialization. Those dependencies block promotion/integration only; usable source and geometric diagnostics remain available.

Actually read writing-plans, executing-plans and verification-before-completion SKILL.md. Applied bounded task/call-site planning and fresh evidence gates; no worktree/extra agents/review/commit/approval workflow is introduced contrary to the human's scoped instruction. Coordinator checks are consistency checks, not independent review of its own collaboration.

STOP FOR D6 BOUNDARY-ONLY HEIGHT-VIEW REVIEW
