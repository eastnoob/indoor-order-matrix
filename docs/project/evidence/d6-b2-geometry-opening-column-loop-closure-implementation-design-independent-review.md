# D6 B2 Geometry, Opening, and Column Loop-Closure Implementation Design Independent Review

- Review date: **2026-10-07**
- Design record reviewed: `d6-b2-geometry-opening-column-loop-closure-implementation-design-review.md`
- Evidence basis: repair-v2 commit `82d08fe` and independent evidence decision `ACCEPT LIMITED DESIGN EVIDENCE`
- Owner decision baseline: `9b50bb1`
- Real IFC: **not verified / not run**
- Blender: **not run**
- Production implementation: **not approved**
- Final decision: **ACCEPT FOR OWNER DESIGN APPROVAL**

## Review boundary

This is an independent, read-only review of the bounded implementation design. It does not approve the design on behalf of the owner and does not authorize production code, adapter changes, NeutralSceneV2 changes, public API changes, tests, dependencies, IFC/Blender work, a selector, a tolerance, a space backend, or a merge.

The review checked the design against the owner decision, the repair-v2 evidence, the existing production touch points, and a fresh read-only probe reproduction. Synthetic evidence remains synthetic design evidence; it was not promoted to real IFC or Blender validation.

## Checks and findings

### 1. Accepted invariants are preserved — PASS

The design keeps physical occupancy separate from conditional boundary support. It preserves column occupancy even when support is refused, keeps exact-contact support diagnostic-only, retains conflicting contact observations, refuses conflicting opening subtraction, and keeps candidate polygon validity separate from source-component connectivity. The domain-promotion gate remains refusal-first when evidence is incomplete, conflicting, ambiguous, or unsupported.

### 2. Candidate segment semantics are preserved — PASS

`candidate_segment_ids` is explicitly described as diagnostic candidate provenance, while `conditional_support_in_this_fixture` is kept separate from production boundary acceptance. The design does not turn the exact-endpoint helper into a geometry tolerance or a public policy.

### 3. Deferred policy boundaries remain deferred — PASS

The design explicitly excludes automatic selectors, ranking, Bayesian/ML models, resolution, route width, space roles, free-space backends, production tolerance, and hidden singleton/replay/UI selection. It keeps explicit authored `AnalysisDomain` handling separate from inferred candidates and refuses singular promotion while candidate authority is unresolved.

### 4. Opening and uncertainty propagation — PASS WITH OWNER NOTE

The opening table covers missing, invalid, partial, conflict, unsupported, and diagnostic-only observations, preserves source references, and refuses subtraction. The labels are explicitly local diagnostic vocabulary rather than a frozen public enum. The owner’s downstream `empty` distinction is deferred with B3 and is not produced by this B2 design; any later downstream contract must retain it if that projection supports it.

### 5. Production touch-point inventory — PASS WITH TWO NON-BLOCKING CONDITIONS

All listed files and named functions exist in the checkout and their stated responsibilities match the current code at the level required for a bounded design. The following conditions must remain explicit when implementation is later authorized:

1. `features/neutral_scene_views.py` currently excludes `scene.analysis_domain.geometry_refs` from `physical_occupancy` and walking blockers. A future implementation must keep a scope/enclosure shell separate from wall/column physical field geometry and must not let this existing support-geometry exclusion erase wall occupancy.
2. `adapters/svg_scene.py` records unresolved authored host references as adapter uncertainty while `adapters/blender_geometry.py` rejects dangling references at validation. The implementation must preserve this distinction in provenance/refusal output and must not silently turn either path into a qualified opening.

These are implementation guard conditions, not blockers to owner design approval, because the reviewed design already keeps domain/source facts separate and defers B4 integration policy.

### 6. Tolerance and existing geometry helpers — PASS WITH OWNER NOTE

The current context contains `geometry_tolerance` and `topology_tolerance`, and existing boundary evidence consumes the context geometry tolerance for height-band calculations. The reviewed design correctly states that the B2 exact-endpoint helper is diagnostic only and that production tolerance remains deferred. Any implementation branch must keep those existing fields out of B2 loop-closure support decisions until the separate tolerance policy gate is approved.

### 7. Data flow, legacy compatibility, and error boundaries — PASS

The adapter/source-fact/NeutralScene/diagnostic-projection/promotion-gate ordering is coherent. Source records remain immutable; derived diagnostics retain lineage; legacy views remain compatibility projections; unresolved references are refused or carried with provenance rather than repaired by invented geometry. The design does not assign furniture substitute discovery any role in boundary support.

### 8. Validation plan and evidence class — PASS

The proposed focused commands are executable and scoped to the existing B2 runners. A fresh temporary-directory run of the repair-v2 probe completed with exit code `0`, reproduced 11 fixtures, and matched the committed result/provenance/SVG hashes. The manifest’s six declared non-self artifacts all matched byte counts and SHA-256 values; JSON and SVG/XML parsing passed. No full pytest, real IFC geometry run, or Blender run was performed.

### 9. Deferred decisions and owner gate — PASS

The design retains the required deferred decisions: public serialization, conflict/undo authority, multiple-candidate selection, multi-floor/units/work-plane policy, production tolerance, opening responsibility, free-space/topology backend, resolution, route width, space role, real IFC/UI integration, production API/tests, and merge. It correctly places independent review before owner implementation authorization.

## Verification commands

The following read-only commands were executed during this review:

1. `Get-Content -Raw AGENTS.md` and the referenced design/evidence records — exit **0**.
2. `git show --stat --oneline 9b50bb1`, `git show --stat --oneline f7f71a3`, and `git show --stat --oneline 02d6eda` — exit **0**.
3. `rg` scans for every production touch-point function and referenced helper — exit **0**.
4. Fresh temporary reproduction: `pixi run python outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py --output-dir <fresh-temp-dir>` — exit **0**; 11 fixtures reproduced.
5. Read-only JSON/SVG/XML parsing and manifest byte/SHA-256 verification — exit **0**; six declared artifacts verified.
6. `git diff --check` — exit **0**.
7. `git status --short --branch` — exit **0**; no tracked production diff was present.

## Scope and limitations

- The design record and this review record are untracked evidence files in the shared worktree; no files were staged or committed by this review.
- Existing unrelated untracked D6 evidence and logs were preserved.
- The review did not run production tests, real IFC geometry, Blender, or any implementation branch.
- The owner still must decide whether to approve the design and later authorize a bounded production branch.

## Decision

**ACCEPT FOR OWNER DESIGN APPROVAL**.

The design is sufficiently bounded and faithful to the accepted B2 evidence for the owner to decide. The two touch-point conditions and the tolerance guard must be carried into any later implementation plan; they do not authorize implementation by themselves.

This is not owner approval and not production implementation approval.

STOP FOR D6 B2 IMPLEMENTATION DESIGN INDEPENDENT REVIEW
