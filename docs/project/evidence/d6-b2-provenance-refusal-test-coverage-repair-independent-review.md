# D6 B2 Provenance/Refusal Test-Coverage Repair Independent Review

- Review date: **2026-10-07**
- Branch: `codex/d6-analysis-domain-layout-handoff`
- Review mode: read-only supplementary review of the prior REVISE findings
- Decision: **ACCEPT**

## Scope

This review evaluates only whether the new test coverage closes the two findings in `d6-b2-provenance-refusal-implementation-independent-review.md`. The original review was read and left unchanged. Also read the plan's “Independent review coverage repair” section and the new shell-identity and downstream-refusal assertions in `test/test_neutral_scene_analysis_regression.py`.

No implementation or test files were changed. No Blender, IFC adapter, real IFC geometry, or full pytest run was performed.

## Finding 1: Fail-closed shell identity coverage — Closed

The parameterized cases explicitly cover:

| Case | Expected private blocker |
|---|---|
| Duplicate domain `source_id` | `analysis_domain_source_id_ambiguous` |
| Unmatched domain `source_id` | `analysis_domain_source_id_unmatched` |
| Matching source role `wall`, `boundary`, or `column` | `analysis_domain_source_role_ineligible` |
| Explicit domain with empty `geometry_refs` | `analysis_domain_geometry_unavailable` |
| Matching source object with no projected record | `analysis_domain_source_record_unavailable` |

The shared test body asserts for every case that `shell_record_ids` is empty, identity is blocked, and the expected blocker is reported. It also asserts that `retained_wall` and `retained_column` remain in both `physical_occupancy` and `walk_blockers`; when the shell itself has geometry, it asserts that shell remains in occupancy as well (`test/test_neutral_scene_analysis_regression.py:485-592`).

The fixtures use unique Neutral Scene record IDs while deliberately repeating a source ID only in the duplicate case. For source objects with no geometry refs, the helper supplies the contract-required `missing_geometry` uncertainty; domain geometry refs may be empty, which validly represents an unavailable explicit domain (`test/test_neutral_scene_analysis_regression.py:247-318`; `features/scene_contract.py:483-503`, `549-578`). No dangling or invented contract field is used. The unavailable-domain case exercises the `domain_available=False` refusal branch. There is no separate fixture with non-empty but unprojectable geometry refs; that does not leave the tested unavailable-domain branch uncovered.

## Finding 2: Private downstream refusal assertions — Closed

The tolerance-invariance test now directly asserts `candidate_polygon_validity.status == "not_available"`, `source_components.status == "not_available"`, and downstream `subtraction == "refused"`, `free_space == "not_evaluated"`, and `route == "not_evaluated"` (`test/test_neutral_scene_analysis_regression.py:697-719`). These assertions cover each field named in the prior finding.

## Verification

| Command | Exit | Result |
|---|---:|---|
| `pixi run pytest test/test_neutral_scene_analysis_regression.py -q -k "blocked_domain_shell_identity or b2_diagnostics_are_invariant_to_context_tolerance_values"` | 0 | **8 passed, 40 deselected** in 0.12s |
| `git diff --check` | 0 | Passed; no output |

## Decision

**ACCEPT** — both findings from the original REVISE report are closed by direct assertions. This decision accepts the test-coverage repair only; it does not reopen or repeat the broader implementation review.
