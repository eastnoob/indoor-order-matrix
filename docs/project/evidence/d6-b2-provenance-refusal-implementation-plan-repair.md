# D6 B2 Provenance/Refusal Implementation Plan Repair Record

- Repair date: **2026-10-07**
- Original plan: `docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation.md` (preserved unchanged)
- Repaired plan: `docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation-v2.md`
- Basis: `docs/project/evidence/d6-b2-provenance-refusal-implementation-plan-independent-review.md` (decision: **REVISE PLAN**)
- Scope: documentation-only plan repair; no production implementation authorized or executed

## Append-only repair record

This record adds the v2 disposition without editing or replacing the original plan or the independent review.

1. **Partial opening state and precedence.** V2 defines a distinguishable `partial` state, preserves available host/geometry refs, carries omitted host refs, and specifies conflict → unsupported → invalid → partial → not_available → diagnostic_only precedence. All states keep `subtraction_performed=False`.
2. **SVG uncertainty and omitted host provenance.** V2 uses the actual `NeutralSceneV2.uncertainties` collection. It associates an uncertainty only when `opening.id` occurs in `UncertaintyRecord.source_refs`, reads omitted IDs from `details["omitted_refs"]`, and keeps the current `_source_openings` behavior intact. The view helper receives the scene uncertainty collection; no adapter record shape is changed.
3. **Explicit domain vs inferred promotion.** V2 reports explicit domain availability/source in `domain_scope`. The separate `candidate_promotion` field refuses or marks ambiguous only inferred/diagnostic candidates. It does not call an existing authored `AnalysisDomain` refused and does not mutate it.
4. **Domain-shell identity and blocker.** V2 establishes shell identity only through a unique exact match between non-empty `AnalysisDomain.source_id` and `SourceObject.source_id`, with an explicit non-wall/non-boundary/non-column source role. A concrete shared-geometry fixture proves the matched shell is excluded while wall and column records remain. Missing, duplicate, unmatched, or ineligible identity produces a diagnostic blocker, an empty exclusion set, and no geometric/proximity/tolerance fallback.
5. **Polygon/connectivity observations.** V2 states that this implementation always emits `candidate_polygon_validity.status="not_available"` and `source_components.status="not_available"`: current `NeutralSceneV2`, `_source_record`, `_neutral_scene_view`, and adapter interfaces expose no named factual observation for either.
6. **Tolerance regression.** V2 compares only `_analysis_view["b2_boundary_diagnostics"]` for scenes with different `geometry_tolerance` and `topology_tolerance`. It does not compare the whole view or tolerance-sensitive channel evidence.

## Verification boundary and commands

Read-only inspection and static plan validation only. Commands executed from `D:\PROJECTS\understandOtherPackage\order_analyzer`:

- `Get-Content AGENTS.md` — exit **0**.
- Read the original plan, independent plan review, owner decision, design review, and design independent review — exit **0**.
- `rg` inventory of actual classes, functions, adapters, and named test files — exit **0**.
- Read current definitions and relevant existing fixtures in `features/neutral_scene_views.py`, `features/scene_contract.py`, `adapters/svg_scene.py`, `adapters/blender_geometry.py`, `adapters/ifc_bonsai.py`, and focused tests — exit **0**.
- PowerShell static v2-plan placeholder/required-text/test-path checks — exit **0**.
- `git diff --check` — exit **0** for tracked changes.
- PowerShell line scan for trailing spaces in both new Markdown files — exit **0**.

No implementation plan step was executed. No production code, adapter, test, dependency, IFC, Blender, or other evidence file was changed. No pytest, real IFC, Blender, worktree creation, staging, commit, or merge was performed.

## Limitations

- The checkout had numerous pre-existing untracked evidence/log files before this repair; they were left untouched.
- The proposed exact source-identity shell rule is deliberately a blocker when current records cannot prove identity. The implementation must stop on that blocker rather than invent a role, geometry, proximity, or tolerance heuristic.
- IFC opening projection remains subject to the existing available fixture coverage; the plan explicitly allows a static-only IFC interface check when invoking an adapter fixture would require prohibited real IFC execution.

STOP FOR D6 B2 PROVENANCE/REFUSAL IMPLEMENTATION PLAN V2 REPAIR



