# D6 B2 Provenance/Refusal Implementation Plan Independent Review

- Review date: 2026-10-07
- Plan reviewed: docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation.md
- Review mode: read-only independent plan review
- Production implementation: not approved / not run
- Final decision: REVISE PLAN

## Scope and source materials

The review read:

- AGENTS.md
- docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation.md
- docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-owner-decision.md
- docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-review.md
- docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-independent-review.md
- docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-repair-v2-independent-review.md
- features/neutral_scene_views.py
- features/group_self_description.py
- features/scene_contract.py
- adapters/ifc_bonsai.py
- adapters/svg_scene.py
- adapters/blender_geometry.py
- test/test_neutral_scene_analysis_regression.py
- test/test_group_self_description.py
- test/test_ifc_bonsai_adapter.py
- test/test_svg_scene_adapter.py
- test/test_blender_geometry_adapter.py

## Commands and exit codes

All commands ran from D:\PROJECTS\understandOtherPackage\order_analyzer.

| Check | Exit code | Result |
|---|---:|---|
| Read AGENTS.md, the plan, and the four required B2 evidence records | 0 | Passed |
| rg production touch-point/function inventory | 0 | All named paths and functions exist |
| rg --files test test-layout check | 0 | All five named test files exist |
| PowerShell path-existence check for all plan touch points | 0 | Passed |
| Static function-name checks for analysis_scene_view, _neutral_scene_view, _channel_blocker_records, _opening_records, _native_opening_records, _source_openings, _validate_scene_references, _space_observations, and _json_ready | 0 | Passed |
| rg placeholder scan (TBD, TODO, FIXME, unassigned) | 0 | No implementation placeholder found; the plan self-review claim is accurate |
| git diff --check | 0 | Passed |
| git status --short --branch | 0 | No tracked production diff; pre-existing untracked evidence/log files preserved |

No pytest, implementation command, adapter execution, IFC execution, Blender execution, worktree creation, staging, commit, or merge was performed. This obeys the read-only review request.

## Findings

### High severity — required revisions

1. **Partial opening evidence is missing from the proposed state machine.**

   The approved B2 design explicitly requires a distinguishable partial observation when some host or geometry evidence is present but qualification is incomplete. The plan's _opening_local_diagnostic_state only specifies not_available, unsupported, conflict, invalid, and diagnostic_only. Its empty-reference rules also collapse cases that may be partial. The implementation plan must define precedence and a concrete partial case, preserve all available refs, and keep subtraction_performed=False.

2. **The stated SVG provenance test cannot be satisfied by the stated helper interface.**

   adapters/svg_scene.py::_source_openings filters unresolved host refs out of SourceOpening.host_refs and emits unresolved_opening_host_ref in the scene-level NeutralSceneV2.uncertainties; the SourceOpening.uncertainties tuple remains empty for that condition. The proposed _b2_opening_diagnostic(opening, shifted_geometry) receives neither the scene-level uncertainty collection nor the omitted host refs. Therefore the Task 3 requirement to report missing/incomplete host evidence with retained provenance is not internally executable as written. Revise the plan to pass or associate scene-level uncertainty facts, including omitted refs, or explicitly change the adapter record shape while preserving the existing SVG behavior and source lineage.

3. **Unconditional domain promotion refusal conflicts with the approved explicit-domain path.**

   Task 1 requires domain_scope.promotion to be refused for every view, while the owner decision states that an explicitly authored AnalysisDomain remains a valid formal input and that B2 must not replace it with automatic inference. The plan must distinguish “existing explicit domain is available/used” from “candidate promotion is refused/not authorized.” A diagnostic field may report refusal for inferred candidate promotion, but it must not falsely label an already explicit domain as refused.

### Medium severity — clarify before implementation

4. **Domain-shell identity is not fully specified against the current record model.**

   NeutralSceneV2.analysis_domain is a separate record, while _neutral_scene_view builds its records from SourceObject values and _source_record maps source roles at the view edge. The plan allows exact identity, geometry refs, and role, but does not state the required source-record shape for an explicit shell or the exact behavior when no source record can be proven to be the shell. The blocker path is mentioned, but no focused test or implementation stop criterion is defined. Add one concrete fixture and an explicit refusal/blocker assertion. The helper must continue to retain wall/column records sharing the domain geometry ref.

5. **Pre-existing factual polygon/connectivity observations have no named source in the current interfaces.**

   Task 1 says to preserve a pre-existing exact observation if one exists, but the plan does not identify a field or record from which candidate_polygon_validity or source_components can be read. Either state that this implementation has no such source and always emits not_available, or name the exact existing field and test it. Do not invent a new public record for this task.

6. **The tolerance-invariance test needs a narrower assertion.**

   Existing channel evidence is allowed to read geometry_tolerance for its approved height-band behavior. The test should compare only the new B2 diagnostic payload, not the whole view or channel evidence, and should state that the diagnostic helper receives no tolerance argument.

## Boundary review

- **Owner-approved B2 boundary:** Mostly preserved. The plan remains limited to provenance/refusal plumbing and does not select a production geometry policy, selector, Bayesian/ML method, resolution, free-space backend, route, UI authority, real-IFC policy, public status enum, serialization contract, or merge policy.
- **Source facts and occupancy:** The intent is correct, and Task 2 addresses the current geometry-reference exclusion that can erase wall/column occupancy. It must be implemented by shell record identity as planned, with the explicit-domain ambiguity correction above.
- **Conditional boundary support:** Correctly remains diagnostic-only and false in the proposed local shape; no loop closure, polygon validity, or connectivity is computed.
- **Candidate polygon vs source connectivity:** Correctly kept separate, subject to clarifying where pre-existing factual observations could come from.
- **Opening refusal/provenance:** Refusal and subtraction_performed=False are preserved in the intended shape, but the missing partial state and SVG scene-level provenance path are blockers to faithful implementation.
- **Domain shell vs physical occupancy:** Correctly identified as a required change and grounded in the current code. The explicit-domain promotion labeling is contradictory and must be corrected.
- **SVG vs Blender behavior:** The plan correctly requires SVG unresolved-host omission/uncertainty and Blender dangling-reference rejection to remain different. The SVG test wiring needs the provenance interface correction above.
- **Legacy group compatibility:** The current _json_ready removes private keys and _space_observations keeps free-space, connectivity, and bottleneck statuses unavailable. The proposed compatibility boundary is internally consistent.
- **Minimality:** Production scope is appropriately small. Task 3's conditional adapter edit is acceptable only for missing source uncertainty facts and must not become qualification or subtraction logic.
- **Implementation gate:** The plan correctly stops before implementation review and requires a later independent implementation review. The final stop text is appropriate for the future implementation session.

## Required plan revisions

Before handoff to implementation, revise the plan to:

1. Define partial opening diagnostics and precedence for mixed/missing evidence, with retained refs and refusal.
2. Define how scene-level SVG uncertainty and omitted host refs are associated with the B2 opening diagnostic.
3. Separate explicit-domain availability/use from inferred-candidate promotion refusal.
4. Add a concrete domain-shell fixture and blocker assertion for records that cannot be identified without tolerance or proximity heuristics.
5. State the exact source of any pre-existing polygon/connectivity observation, or state that this task emits not_available unconditionally.
6. Narrow the tolerance regression assertion to the B2 diagnostic payload.

## Scope and limitations

This review assessed plan consistency against the owner decision, the prior independent design review, current production definitions, and current test layout. It did not execute the planned implementation or tests, validate real IFC, run Blender, assess geometry correctness, or approve any production change. The shared worktree contains unrelated pre-existing untracked D6 evidence/log files; none were modified.

## Final decision

**REVISE PLAN**.

The plan is within the intended B2 scope and is close to handoff, but the three high-severity issues above would allow an implementation to lose approved provenance or misstate explicit-domain status. After those revisions and focused fixture/interface clarifications, it can return for implementation handoff. This review does not approve production implementation.

STOP FOR D6 B2 PROVENANCE/REFUSAL IMPLEMENTATION PLAN INDEPENDENT REVIEW
