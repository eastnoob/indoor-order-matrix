# D6 Boundary-Inference Height View Implementation Plan

> **For agentic workers:** Execute task by task with the existing coordinator and geometry worker B. `superpowers:executing-plans` is the reference for checked execution; human scope overrides its new-worktree, extra-reviewer, formal-test and commit workflow. No new chats or approval pause.

**Goal:** Execute fresh, diagnostic planar enclosure-candidate inference from explicitly eligible structural section geometry, preserving wall/column mass and unresolved semantics.

**Architecture:** Reuse the frozen world-metre snapshot through the existing adapter and tested design-only exact section. A minimal boundary-only runner computes candidates from the current eligible section geometry; historical JSON candidates and toy centreline output are references, not new inference. Enclosure contours, physical occupancy, candidate scope and qualification remain separate outputs.

**Tech Stack:** Pixi Python 3.12; installed Shapely/Trimesh; existing geometry transport and section helpers. No installations.

**Spec:** Human-authorized 2026-10-08 narrower boundary-only brief; `docs/project/space-field-ifc-neutral-scene-input-contract.md`, B2 implementation-design owner decision, architecture memory, and `docs/project/evidence/d6-floor-plan-3d-comparison.md`. Previous comparison accepted only as LIMITED DESIGN EVIDENCE.

## Global constraints and fixed experiment inputs

- No production/adapters/API/formal-test/source IFC/user Blender changes; no branch/index/stage/commit operations. No full pytest/native tessellation/plan re-inventory.
- Explicit plane is world XY; datum world z=0 is an experiment assumption, cut height above datum=1.5 m. Units m/m². Reuse 1e-6 m and 1e-6 m² analytic comparison budgets; exact shared-edge construction, no snapping/buffer/hull/epsilon widening to close gaps. Original source topology flags stay unchanged.
- Frozen input: `outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json`, 4318044 bytes, SHA256 `c5659dcd99d8c4f20b97efd2cc37352d6305436e20e698ccbcf8c89abfe67867`; 11 walls/16 columns/6 doors, 56561 vertices/112886 triangles. External IFC identities; adapter IDs/classes remain nullable. Disk IFC/snapshot geometry parity remains unverified.
- Disk IFC expected identity remains `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240` / 408617800 bytes. Reuse the previous metadata inventory; it has no authored plan, no qualified floor datum, and no opening-host relations. Do not convert geometry again.
- Walls and columns are eligible structural support candidates; eligibility is not observed support. Ordinary standalone beams, furniture and unknown/nonstructural objects are excluded from boundary support, with their source/occupancy records retained. A wall's integrated lintel remains wall geometry; cut semantics determine whether it contributes.
- Door default-closed is a user-requested scenario assumption, never observed state. Only independently qualified host/location/extent/closure geometry permits a separately tagged diagnostic seal. Door class/name/bbox never supplies that qualification; unresolved real doors remain unresolved.
- No candidate winner, auto-promotion, active AnalysisDomain, new public enum, free-space/walkability/route/furniture/headroom or whole-room 3D claims. General multi-mode abstraction and production tolerance policy stay deferred.

## Ownership and actual reusable path

Coordinator creates this plan, `docs/project/evidence/d6-boundary-inference-height-view.md`, and `outputs/design/d6_boundary_inference_height_view/integration/`; appends one factual progress entry at completion. B creates only `scripts/design/space_field/run_boundary_height_view.py` and `outputs/design/d6_boundary_inference_height_view/geometry/`. Earlier reports/runners/runs/manifests are read-only.

| Reuse / call site | Actual role in this phase |
|---|---|
| `run_floor_plan_3d_comparison.normalize(snapshot)` | Existing adapter → MassPatch; identical world vertices, external source mapping, independently measured topology beside unchanged flags |
| `run_floor_plan_3d_comparison.section(row,height)` / `indexed_section_segments(mesh,height)` | Exact source-edge contours; qualified faces and raw/coplanar/unclosed diagnostics. No band substitution |
| `features.geometry_views.component_shape`, `geometry_substitutes.mass_patch_from_mesh` | Existing transport/polygon construction; no new source classification or transform |
| `run_boundary_construction_experiment._candidate_record` and `_controlled_candidates` | Reuse semantic separation only: scope enclosure versus physical wall field. These functions operate ordered toy centreline/offset inputs and do not infer from current mesh sections; do not import their accepted flags or selected authored toy candidate |
| `outputs/design/live_ifc_boundary_candidate_comparison/run_experiment.py` | Reference for source relation diagnostics only; consumes retained JSON candidates, not fresh inference |
| New B `infer_candidates(section_records, source_rows, scenario_evidence)` (design-only interface) | The actual fresh inference step: exact eligible-section union, bounded holes/enclosure contours, exact source contact/contribution evidence and provisional scope relationship; installed Shapely operations only |

## Task 1: Freeze input/eligibility and executable inference

- [x] Coordinator records current branch/HEAD/status and small relevant input/module/previous-delivery fingerprints; freezes the published plan before B generates boundary results.
- [x] B traces the helpers above, records actual imports/hash/provenance, and states exactly which reused or new function computes candidates from current section input.
- [x] B implements minimal design glue with explicit datum/cut arguments and fresh output directory. Keep all 33 source/physical occupancy records; boundary input consists only of usable wall/column sections and separately qualified scenario seals. Unsupported sections remain visible.
- [x] Compute exact union of eligible sectional masses; retain occupied polygon components and bounded interior rings as separate observations. A ring is an enclosure-contour candidate, not an inner-only AnalysisDomain. Never infer from an external bbox or reuse old candidate coordinates.
- [x] Associate actual supporting source refs through measured positive-length contour contact / contribution to the particular enclosure; record the exact operation. Interior columns stay occupancy-only when they do not contribute to that contour. Do not turn an isolated column's occupied exterior into a new room, or carve its mass out of the domain scope.
- [x] For each contour keep polygon validity, closure, occupied source components, supporting refs and completeness separately. Show candidate interior and physical supporting wall/column mass separately. A diagnostic scope proposal may explicitly union the contour's filled interior with its measured supporting sectional mass, preserving interior column occupancy; declare that construction and any shared-wall extent ambiguity. If appropriate wall extent cannot be determined, scope extent remains unresolved rather than choosing inner-only or bbox.
- [x] Keep unresolved door/opening metadata as completeness limitations independently of geometric closure. No missing relation is solved by a closed ring; partiality is attributed per source/candidate where evidenced, with global limits separately recorded.

Pre-result ruling: B may represent one **compound scope proposal per wall-bearing connected sectional-mass component**, using that component's actual exterior with its bounded holes filled. This is a measured exterior construction, not a bbox/hull; all supporting wall mass remains included and all interior columns remain physical occupancy. Each bounded interior ring is separate enclosure-contour evidence. If multiple contours share the same component, they share the one compound scope proposal; per-room wall allocation/local extents stay unresolved. Report enclosure-contour count and compound-scope-proposal count separately. No silently duplicated room domains. Column-only components/rings do not qualify as wall-bearing enclosure proposals in this bounded eligibility path.

Column support may be measured by exact contour contact plus a leave-one-column-out topology observation on already computed sections. Record contact-only, changed contour, and actually opened enclosure as distinct observations; a changed ring coordinate or candidate count is not by itself proof that closure depended on that column. No extra 3D query matrix is needed.

## Task 2: Small controls, one real inference and one replay

- [x] Reuse `walls_columns` dimensions to show an interior column remains occupancy, while removing/restoring the column completing a known wall gap changes enclosure candidate evidence. Independent expected contour/scope area and supporting refs are written before execution.
- [x] Reuse the known opening/host case inside a small closed-wall context, only as needed for a qualified synthetic open/default-closed contrast. A separate explicit synthetic seal may close the known gap; removing host qualification must refuse seal and retain open/unresolved result. Do not infer source mass from the scenario seal.
- [x] One exclusion-invariance check adds/removes a non-boundary object and compares boundary result bytes/geometry while demonstrating occupancy changes. This is an eligibility check, not another beam/3D experiment.
- [x] Execute real boundary inference once in a fresh run, then one fresh-directory replay with identical input/parameters. Compare deterministic geometry/candidate/source diagnostics, excluding only command/timing metadata. Do not run a new performance study.
- [x] Render fresh real section geometry, eligible/supporting versus occupancy-only columns where evidenced, unresolved doors/contours, numbered provisional candidates or explicit unclosed boundary diagnostics. Include wall mass/scope relationship and full labels/legend; view actual PNG pixels.

Expected invocation (B may add only necessary explicit scenario/verification options):

```powershell
pixi run python -B scripts/design/space_field/run_boundary_height_view.py --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --datum 0 --cut-height 1.5 --output-dir outputs/design/d6_boundary_inference_height_view/geometry/run_001
pixi run python -B scripts/design/space_field/run_boundary_height_view.py --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --datum 0 --cut-height 1.5 --output-dir outputs/design/d6_boundary_inference_height_view/geometry/run_002
```

## Task 3: Evidence and minimal future integration recommendation

- [x] B saves commands/actual exits, source/parameters, candidate table, source support/occupancy/scope geometry, scenario refusal records, PNG and relevant byte/SHA256 manifest. English-first docstrings/computation comments; minimal runnable control assertions live in the design runner.
- [x] Coordinator reconciles frozen contract against actual JSON, inspect pixels and fresh hashes, scoped Git/whitespace checks and old progress prefix. Preserve existing dirty work; no whole-project fingerprint crawl.
- [x] Report actual closure/candidate observations and which source limitations affect them; include exact future production call-site/test suggestions and deferred policy choices. Proposals do not authorize implementation.
- [x] Append one dated progress entry, send root consolidated delivery, and stop. Root/human retains acceptance; our consistency check is not independent review.

## Review focus and policy limits

Controls must pin: isolated column does not create a domain/hole; boundary-column geometry contributes when it actually closes a gap; unresolved opening refuses seal; non-boundary exclusion leaves boundary inference invariant; closed observed geometry does not imply candidate semantic completeness. Real non-watertight door #6231 affects door/occupancy interpretation but is not automatically a failure of otherwise usable wall/column section diagnostics. No arbitrary near-gap repair is permitted.

Observed baseline: branch `codex/d6-analysis-domain-layout-handoff`, HEAD `ab55da50dfb278b639e2327008ad23a50e86973d`; progress already modified by the completed comparison, its bytes must be preserved as an append prefix; index unchanged. Writing-plans and verification-before-completion SKILL.md read and applied. Generic skill extra-review/commit/worktree/approval flows are overridden by this phase's explicit ownership and human authorization. Existing B executes its assigned tasks, without extra agents.

STOP FOR D6 BOUNDARY-ONLY HEIGHT-VIEW REVIEW

Execution closure: final geometry/run_002, separate-process replay run_003, coordinator integration/run_002. First successful run_001 is preserved; final run adds explicit no-contour/source-connectedness diagnostics. Scope ruling unchanged; no candidate promoted. Root acceptance pending.
