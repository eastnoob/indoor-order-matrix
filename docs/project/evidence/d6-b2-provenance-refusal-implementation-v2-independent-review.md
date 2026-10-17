# D6 B2 Provenance/Refusal Implementation Plan V2 Independent Review

- Review date: **2026-10-07**
- Plan reviewed: `docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation-v2.md`
- Original plan: `docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation.md`
- Review mode: read-only independent plan review
- Production implementation: **not approved / not run**
- Final decision: **REVISE PLAN**

## Scope and source materials

Reviewed:

- `AGENTS.md`
- v2 plan, repair record, original plan, prior independent review
- owner decision, design review, and design independent review
- `features/neutral_scene_views.py`
- `features/scene_contract.py`
- `adapters/svg_scene.py`
- `adapters/blender_geometry.py`
- `adapters/ifc_bonsai.py`
- named neutral-view, SVG, Blender, IFC, and group-description tests

The review performed only file reads, `rg` searches, static path/function inventory, plan-structure checks, plan comparison, `git status`, and `git diff --check`. No implementation, pytest, real IFC, Blender, staging, commit, merge, or worktree operation was performed.

## Commands and exit codes

All commands ran from `D:\\PROJECTS\\understandOtherPackage\\order_analyzer`.

| Check | Exit | Result |
|---|---:|---|
| Required path and function inventory | 0 | All named paths and symbols exist |
| Writing-plans header, task structure, checkbox steps, and stop gate | 0 | Present |
| Placeholder scan for TBD/TODO/FIXME/XXX/unassigned | 0 | No placeholders |
| Owner-scope constraint scan | 0 | Required prohibitions are present |
| `git diff --check` | 0 | Passed |
| `git status --short --branch` | 0 | Branch clean of tracked changes; pre-existing untracked evidence/plans remain |
| Original/v2 comparison | 0 | Original has 350 lines; v2 has 272 lines; they are separate files and differ as expected |
| Static scope/reference scan for shell identity, optional source IDs, and conditional test files | 0 | Findings below confirmed |

The original plan was read only and was not modified during this review. Because both plan files are untracked in the current checkout, repository history cannot independently establish their pre-review baseline hashes.

## Assessment of the six prior blockers

1. **Partial opening evidence: resolved.** V2 defines a concrete precedence order: conflict, unsupported, invalid/malformed, partial, not_available, diagnostic_only. It retains available host refs, geometry refs, omitted SVG host refs, and uncertainty source refs. Every diagnostic opening explicitly keeps `subtraction_performed=False`.

2. **SVG scene-level uncertainty: resolved.** V2 passes the scene uncertainty collection into the opening projection, associates records only when `opening.id` appears in `UncertaintyRecord.source_refs`, reads `details["omitted_refs"]`, and preserves the current SVG omission behavior. The current adapter emits the unresolved-host uncertainty at scene level exactly as the plan describes.

3. **Explicit domain vs inferred promotion: resolved.** V2 reports explicit domain availability/source under `domain_scope` and keeps `candidate_promotion` limited to inferred or diagnostic candidates. It does not mutate or relabel an authored `AnalysisDomain`.

4. **Domain-shell identity: resolved in principle.** V2 requires a unique exact non-empty `AnalysisDomain.source_id == SourceObject.source_id` match with an eligible source role, gives concrete blocked cases, and forbids geometry overlap, proximity, coordinates, and tolerance fallback. The shared-geometry fixture and no-identity fixture are concrete.

5. **Polygon/connectivity provenance: resolved.** V2 explicitly makes both observations `not_available` with `no_current_source_observation`, matching the current interfaces instead of inventing a source.

6. **Tolerance invariance: resolved.** V2 compares only `view["_analysis_view"]["b2_boundary_diagnostics"]` and explicitly forbids reading either context tolerance in the new helper bodies.

## Findings

### High severity — existing focused regression contradicts the planned blocked-identity behavior

V2 requires that when shell identity is blocked, the exclusion set is empty and no record is removed. Its unprovable fixture uses an explicit domain with `source_id=None`. The existing regression `test_analysis_domain_support_mass_is_not_a_walking_blocker_when_overlapping_body_band` also uses `source_id=None` and asserts `view["walk_blockers"] == []`.

Under the v2 rule, that fixture has no provable shell identity, so its overlapping support mass remains eligible for walking blockers. The planned focused command includes this test file, so the implementation cannot satisfy both the v2 rule and the current assertion without an explicit plan change.

Revise Task 2 to state the required test update: either give the legacy support fixture an exact matching source identity, or change its expected blocked-identity behavior. The plan must make clear that the change is intentional and preserves wall/column occupancy.

### Medium severity — exact modification scope conflicts with conditional Task 3 edits

The global constraint says to modify only the files in the exact file map. Task 3 later permits modifying `test/test_ifc_bonsai_adapter.py` and conditionally adding an assertion to `test/test_group_self_description.py`. Those files are not in the exact modify list.

Clarify the authoritative file set. If those conditional tests are allowed, list them in the exact file map; otherwise make the steps read-only and remove the modification instruction.

### Medium severity — diagnostic source-ID shape is incompatible with current optional source IDs

The diagnostic contract declares `physical_occupancy[].source_id: str` and `boundary_support[].source_id: str`. The current `SourceObject.source_id` is `str | None`, and the existing neutral fixtures commonly use `source_id=None). Task 2 says to preserve source ID but does not specify whether the diagnostic should:

- use the projected record `id` as the stable fallback,
- emit nullable `source_id`, or
- omit the field when no source ID exists.

Without that rule, an implementation can produce a payload that violates its own declared shape or silently substitute an identity. Specify the allowed fallback/nullable contract and add one fixture with `source_id=None`.

### Low severity — Blender regression wording is inaccurate

V2 says to “retain” a dangling explicit opening regression, but the named Blender test file currently contains dangling-domain coverage and no dangling-opening test. The step is executable because the loader accepts an `openings` argument, but it should say “add” the opening-reference regression to avoid implying existing coverage.

## Boundary and minimality review

V2 remains within the owner-approved B2 provenance/refusal plumbing. It does not introduce a public status enum or serialization contract, selector/ranking/score/Bayesian/ML logic, production tolerance, free-space backend, resolution, route width, UI authority, real-IFC policy, or merge behavior. It keeps SVG omission and Blender dangling-reference rejection distinct, keeps opening subtraction refused, keeps physical occupancy separate from boundary-support diagnostics, and retains the private `_analysis_view` compatibility boundary.

The writing-plans header, task/checklist structure, named current functions, named test paths, placeholder scan, and stop-before-implementation gate are present. The plan is close to executable, but the high-severity regression mismatch must be repaired before implementation authorization.

## Scope and limitations

This was a static plan review only. No implementation or tests were run, so runtime behavior was not validated. The checkout contains numerous pre-existing untracked D6 evidence and log files; they were not modified. IFC coverage was assessed through the existing named interface and tests only, without real IFC execution. Blender behavior was assessed from the current loader and validation definitions only.

## Final decision

**REVISE PLAN**.

The six prior blockers are resolved, but the current v2 plan still leaves one focused regression internally inconsistent with its required blocked-identity behavior and has two narrower scope/type ambiguities. Correct those items, then obtain a fresh implementation review. This decision does not approve production implementation.

STOP FOR D6 B2 PROVENANCE/REFUSAL IMPLEMENTATION PLAN V2 INDEPENDENT REVIEW

