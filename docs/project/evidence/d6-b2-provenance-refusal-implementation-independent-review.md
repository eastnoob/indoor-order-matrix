# D6 B2 Provenance/Refusal Implementation Independent Review

- Review date: **2026-10-07**
- Branch: `codex/d6-analysis-domain-layout-handoff`
- Review mode: read-only implementation review
- Final decision: **REVISE**

## Scope

Reviewed `AGENTS.md`, the indoor-layout architecture memory, the owner decision/design boundary, the v2 implementation plan and its independent plan review, the changed implementation and regression tests, and the relevant Neutral Scene contract, SVG/Blender/IFC adapters, group-description serializer, and analysis-view callers.

The tracked diff is limited to the five authorized implementation/test files: `features/neutral_scene_views.py`, `test/test_neutral_scene_analysis_regression.py`, `test/test_svg_scene_adapter.py`, `test/test_blender_geometry_adapter.py`, and `test/test_group_self_description.py`. Existing untracked evidence, plan, and log artifacts were treated as checkout baseline. This review created only this report; it did not edit, stage, or commit implementation or tests.

## Findings

### Medium — Fail-closed shell identity branches lack focused regression coverage

The implementation resolves a shell only when the explicit domain has projected points, a non-empty exact `source_id`, exactly one matching source object, an eligible role, and a corresponding projected record. Missing, unavailable, unmatched, duplicate, ineligible, and unavailable-record cases return no shell IDs and a private blocker (`features/neutral_scene_views.py:675-737`). The physical-occupancy and walking-blocker filters then exclude only those resolved record IDs (`features/neutral_scene_views.py:131-145`, `563-600`). This is safe by inspection.

The tests exercise successful identity with shared geometry and a missing domain source ID (`test/test_neutral_scene_analysis_regression.py:293-408`), but do not exercise duplicate or unmatched IDs, ineligible wall/boundary/column identity, or unavailable/unprojectable domain geometry. These are central safety conditions for preventing a false shell match from suppressing physical occupancy or walking blockers. Add focused cases that assert each condition keeps the record eligible and exposes its blocker before treating this contract as regression-locked.

### Low — Fixed downstream refusal fields are not directly asserted

The diagnostic sets candidate polygon validity and source components to `not_available`, subtraction to `refused`, and free-space and route to `not_evaluated` (`features/neutral_scene_views.py:876-904`). The tests assert refused candidate promotion and public space-measurement unavailability (`test/test_neutral_scene_analysis_regression.py:353-408`; `test/test_group_self_description.py:235-250`), but do not assert these corresponding private B2 fields. A small contract assertion would prevent accidental future promotion of these private statuses.

No implementation defect violating the approved boundary was observed. The decision is **REVISE** because the fail-closed identity cases above are important enough to lock with focused tests; this is a coverage finding, not a claim that the current branches remove occupancy incorrectly.

## Contract assessment

1. **Domain shell identity and safe refusal — Pass by code; partial test coverage.** Exact, unique, non-empty `AnalysisDomain.source_id` matching controls shell IDs. Geometry overlap is not used. Missing, duplicate, unmatched, ineligible, and unprojectable cases produce no exclusions and a private reason. Only missing and established identities are currently covered by the new regression fixtures; see the medium finding.

2. **Shared geometry and compatibility — Pass.** Physical occupancy and walking blockers filter by resolved record ID, so a shell and wall/column can share geometry refs without that overlap removing the wall or column (`features/neutral_scene_views.py:131-150`, `563-600`). The legacy `interface_facts` geometry-ref filter remains separate (`features/neutral_scene_views.py:112-129`), and the shared-geometry regression asserts wall and column retention (`test/test_neutral_scene_analysis_regression.py:293-350`). The legacy `physical_blockers` bucket remains boundary-only (`features/neutral_scene_views.py:169-173`).

3. **Opening provenance and refusal — Pass.** Diagnostics originate from each `SourceOpening`; scene uncertainties join only when `opening.id` occurs in `source_refs`, and opening-local uncertainties remain attached (`features/neutral_scene_views.py:740-749`). The implemented precedence is conflict → unsupported → invalid/malformed → partial → not_available → diagnostic_only (`features/neutral_scene_views.py:752-793`). Omitted-host refs are read from the matching unresolved-host uncertainty; nullable source IDs are preserved; every diagnostic opening sets subtraction false (`features/neutral_scene_views.py:760-829`). `_opening_records` still emits a renderable entry only when actual projected opening points exist (`features/neutral_scene_views.py:1204-1235`). Tests cover each state, exact scene-uncertainty association, omitted-host provenance, nullable IDs, and false subtraction (`test/test_neutral_scene_analysis_regression.py:428-511`; `test/test_svg_scene_adapter.py:858-890`).

4. **Occupancy, support, and deferred geometry — Pass by code.** Physical occupancy includes source records with mass geometry after exact shell exclusion. Wall, boundary, and column support observations are separate, source-referenced diagnostics with `conditional_support=False` and no computed closure (`features/neutral_scene_views.py:833-874`). Polygon validity and source components remain unavailable, and downstream subtraction/free-space/route remain refused or unevaluated (`features/neutral_scene_views.py:876-904`). Direct tests for those final private status values are absent; see the low finding.

5. **Private boundary and compatibility — Pass.** B2 diagnostics are placed only under `_analysis_view` (`features/neutral_scene_views.py:185-202`). The group-description serializer omits underscore-prefixed view data (`features/group_self_description.py:923-931`), and the new regression checks the public JSON boundary plus unavailable public space measurements (`test/test_group_self_description.py:235-250`). Top-level uncertainties still serialize `scene.uncertainties` directly, and legacy buckets are retained (`features/neutral_scene_views.py:162-183`).

6. **Tolerance isolation — Pass.** B2 helper signatures and bodies do not read geometry or topology tolerances. The regression changes both context values and compares only the B2 diagnostic payload (`test/test_neutral_scene_analysis_regression.py:514-531`), which is the appropriate invariance scope because unrelated channel evidence may use geometry tolerance.

7. **Adapter-specific behavior and test scope — Pass with limits.** SVG continues to omit the missing host while retaining a scene-level uncertainty that the diagnostic joins by exact opening reference (`adapters/svg_scene.py:1557-1608`; `test/test_svg_scene_adapter.py:858-890`). Blender still rejects a dangling opening host through adapter validation (`adapters/blender_geometry.py:279-320`; `test/test_blender_geometry_adapter.py:247-262`). The named IFC test builds a temporary synthetic IFC4 file and checks native opening/host facts (`test/test_ifc_bonsai_adapter.py:810-836`); it does not validate real IFC geometry or the B2 diagnostic projection.

8. **Changed-file scope — Pass.** `git diff --name-only` reported only the five authorized files listed above. Pre-existing untracked artifacts were not included in the review diff or modified.

## Verification

| Command | Exit | Result |
|---|---:|---|
| `pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q` | 0 | **105 passed** in 4.93s |
| `pixi run pytest test/test_blender_geometry_adapter.py test/test_group_self_description.py test/test_ifc_bonsai_adapter.py::test_adapter_preserves_native_ifc_opening_and_host_facts -q` | 0 | **56 passed** in 0.26s |
| `git diff --check` | 0 | Passed; no output |

## Limitations

No full pytest suite, Blender process, or real IFC geometry was run. The isolated IFC test above uses a temporary synthetic IFC4 fixture. The implementation plan records that a broader command was interrupted and that it is unknown whether it had reached a real-IFC test; this review did not rerun that command and makes no real-IFC validation claim. The review did not run the entire IFC adapter test module.

## Decision

**REVISE** — the bounded implementation is consistent with the approved provenance/refusal design by inspection and all requested focused checks pass. Add focused regression cases for duplicate, unmatched, ineligible, and unavailable/unprojectable domain-shell identity before accepting the fail-closed identity contract.
