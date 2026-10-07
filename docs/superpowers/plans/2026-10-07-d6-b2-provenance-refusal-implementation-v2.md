# D6 B2 Provenance/Refusal Plumbing Implementation Plan v2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Do not execute this plan until the owner separately authorizes implementation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private, source-grounded B2 diagnostic projection that preserves opening, domain, occupancy, and uncertainty provenance while refusing inferred promotion and opening subtraction.

**Architecture:** Keep `NeutralSceneV2` and its existing records as source of truth. Add one private diagnostic projection in `features/neutral_scene_views.py`, derive omitted SVG host provenance from existing scene-level `UncertaintyRecord` entries, and change domain-shell exclusion to use exact source identity only. The explicit authored `AnalysisDomain` remains an available formal input; inferred candidate promotion stays refused/ambiguous.

**Tech Stack:** Python 3.12 under Pixi, existing frozen Neutral Scene dataclasses, existing analysis view, and focused pytest files.

**Spec:** `docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-owner-decision.md`; detailed approved boundary in `docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-review.md` and its independent review.

## Global Constraints

- Do not add a public status enum or public serialization contract.
- Do not add a selector, ranking, score, Bayesian/ML inference, production tolerance, or near-contact policy.
- Do not add a free-space/topology backend, resolution, origin, clearance, bottleneck, route width, or walkability policy.
- Do not add UI authority, real-IFC policy, or merge behavior.
- Do not infer loop closure, candidate polygon validity, source connectivity, contact, or boundary support.
- Keep `subtraction_performed` false for every opening observation.
- Preserve physical column occupancy separately from conditional boundary-support diagnostics.
- Keep an existing explicit authored `AnalysisDomain` available as a formal source; only inferred/diagnostic candidate promotion is refused or ambiguous.
- Preserve existing SVG omission plus scene-level uncertainty and existing Blender dangling-reference rejection; do not change either adapter behavior.
- Do not read `geometry_tolerance` or `topology_tolerance` in any new B2 helper.
- Candidate polygon validity and source-component observations are both `not_available` unconditionally in this implementation; the current named interfaces expose no source field for either observation.
- New or modified project-owned functions need English docstrings and comments on non-obvious computation.
- Modify only files listed below. Do not modify dependencies, IFC/Blender inputs, or unrelated dirty/untracked files.

---

## Exact file map

- Modify `features/neutral_scene_views.py`: build the private `b2_boundary_diagnostics` under `_analysis_view`; pass the whole `NeutralSceneV2` to the opening projection; derive exact domain-shell identity; apply ID-based exclusions in `_neutral_scene_view`, `_channel_blocker_records`, and `physical_mass_records`.
- Modify `test/test_neutral_scene_analysis_regression.py`: cover diagnostic state precedence, exact shell identity, no-identity blocker behavior, explicit domain availability, and B2-only tolerance invariance.
- Modify `test/test_svg_scene_adapter.py`: exercise existing SVG host omission and scene uncertainty, then verify that the view joins the omitted refs into opening diagnostics.
- Modify `test/test_blender_geometry_adapter.py`: retain a regression asserting dangling explicit opening refs still fail `_validate_scene_references` through the loader.
- Read only `features/scene_contract.py`, `adapters/svg_scene.py`, `adapters/blender_geometry.py`, and `adapters/ifc_bonsai.py`; no adapter or contract changes are planned.

## Diagnostic contract and current interfaces

`analysis_scene_view(scene: AnalysisSceneInput) -> LegacyAnalysisScene` dispatches Neutral Scene inputs to `_neutral_scene_view(scene)`. That function currently projects `scene.source_objects` through `_source_record`, projects source openings through `_opening_records(scene, geometry_points)`, exposes `scene.uncertainties` at top-level `uncertainties`, and builds private `_analysis_view`. It currently excludes records from physical occupancy and walking blockers by intersection with `scene.analysis_domain.geometry_refs`.

Use these private functions/signatures in the implementation:

```python
def _domain_shell_identity(
    scene: NeutralSceneV2,
    records: list[dict],
) -> tuple[set[str], dict[str, object]]: ...

def _opening_local_diagnostic_state(
    opening: SourceOpening,
    scene_uncertainties: tuple[UncertaintyRecord, ...],
) -> tuple[str, str, list[str]]: ...

def _b2_opening_diagnostic(
    opening: SourceOpening,
    scene_uncertainties: tuple[UncertaintyRecord, ...],
) -> dict[str, object]: ...

def _b2_boundary_diagnostics(
    scene: NeutralSceneV2,
    records: list[dict],
    domain_shell_record_ids: set[str],
) -> dict[str, object]: ...
```

`AnalysisDomain` has `id`, `geometry_refs`, optional `source_id`, `selection_method`, `provenance`, and `uncertainties`. `SourceObject` has `id`, optional `source_id`, `source_role`, `geometry_refs`, and `uncertainties`. `SourceOpening` has `id`, optional `source_id`, `host_refs`, `geometry_refs`, `opening_kind`, `provenance`, and `uncertainties`. `UncertaintyRecord` has `code`, `source_refs`, and JSON-safe `details`. SVG `_source_openings(records, *, geometry_refs, valid_object_refs)` keeps only valid host refs and stores omitted refs in a scene uncertainty with code `unresolved_opening_host_ref`, `source_refs=(opening_id,)`, and `details["omitted_refs"]`. Blender `_validate_scene_references(scene)` rejects dangling opening refs. IFC `_native_opening_records(source, geometry_by_source_id)` supplies opening host/geometry facts and a `missing_geometry` uncertainty when geometry is absent.

The private diagnostic dictionary has the following keys. Values are local diagnostic strings, not a shared/public enum:

```python
{
    "schema": "d6-b2-neutral-scene-diagnostics/v2",
    "evidence_class": "source_fact_and_refusal_plumbing",
    "domain_scope": {
        "availability": "available" | "not_available",
        "source": "explicit_authored" | "none",
        "id": str | None,
        "geometry_refs": list[str],
        "shell_record_ids": list[str],
        "shell_identity": "established" | "blocked" | "not_applicable",
        "blocker": str | None,
    },
    "candidate_promotion": {
        "status": "refused" | "ambiguous",
        "reason": "inferred_candidate_promotion_not_authorized",
    },
    "physical_occupancy": [
        {"source_id": str, "source_role": str, "geometry_refs": list[str], "included": True}
    ],
    "boundary_support": [
        {"source_id": str, "candidate_segment_ids": list[str],
         "conditional_support": False, "local_diagnostic_state": "diagnostic_only",
         "reason": "b2_loop_closure_policy_deferred", "source_refs": list[str]}
    ],
    "candidate_polygon_validity": {
        "status": "not_available", "reason": "no_current_source_observation", "source_refs": []
    },
    "source_components": {
        "status": "not_available", "reason": "no_current_source_observation", "source_segment_ids": []
    },
    "openings": [
        {"id": str, "source_id": str | None, "host_refs": list[str],
         "omitted_host_refs": list[str], "geometry_refs": list[str],
         "opening_kind": str, "provenance": dict, "uncertainties": list[dict],
         "local_diagnostic_state": str, "reason": str,
         "source_refs": list[str], "subtraction_performed": False}
    ],
    "downstream": {
        "subtraction": "refused", "free_space": "not_evaluated", "route": "not_evaluated"
    },
}
```

Opening state precedence, evaluated from source opening uncertainties plus matching scene uncertainties:

1. Any matching uncertainty code containing `conflict` → `conflict`.
2. Else any matching code containing `unsupported` → `unsupported`.
3. Else any matching code containing `invalid` or `malformed` → `invalid`.
4. Else if `unresolved_opening_host_ref` omitted refs exist, or exactly one of host refs/geometry refs is empty → `partial`. Keep every available host, geometry, omitted host ref, and uncertainty source ref.
5. Else if both host refs and geometry refs are empty, or any matching code is `missing_geometry` → `not_available`.
6. Else → `diagnostic_only`; both refs exist, but no qualification policy is approved.

Every state has `subtraction_performed=False`. Merge only the uncertainty records associated by `opening.id in record.source_refs`; do not infer an association from order or names. A partial opening does not become qualified even if one host and one geometry ref remain.

For domain shell identity, an explicit domain is available when `scene.analysis_domain` exists and its referenced geometry projects to points (the same condition as `_analysis_view.domain_available`). Identity is established only by a unique `SourceObject` with non-empty `source_id == scene.analysis_domain.source_id` and a non-wall/non-boundary/non-column `source_role`; use that source record's `id`. If `source_id` is absent, unmatched, duplicated, or the exact match is wall/boundary/column, set `shell_identity="blocked"`, include a concrete blocker reason, and return no shell IDs. Never use `geometry_refs`, proximity, coordinates, or tolerance to establish identity. On blocked identity, exclude no source record; preserve wall/column occupancy and expose the blocker in the diagnostic. This is a local diagnostic blocker, not a public error or altered AnalysisDomain.

Explicit domain availability/use and inferred candidate promotion are separate: report `domain_scope.source="explicit_authored"` and its availability when applicable. `candidate_promotion` describes only inferred/diagnostic candidates and remains refused (or ambiguous when current view evidence contains multiple inferred region candidates; if candidate count is not supplied to this projection, use refused) without changing `scene.analysis_domain`.

---

### Task 1: Add private opening and B2 provenance diagnostics

**Files:**
- Modify: `features/neutral_scene_views.py`, `_neutral_scene_view`, `_opening_records`, and private helpers adjacent to `_domain_points`.
- Test: `test/test_neutral_scene_analysis_regression.py`.
- Test: `test/test_svg_scene_adapter.py`.

**Interfaces:**
- Consumes: `NeutralSceneV2.openings`, `NeutralSceneV2.uncertainties`, `SourceOpening`, projected `records`, and existing geometry refs.
- Produces: `_analysis_view["b2_boundary_diagnostics"]`; no `scene_contract.py` edits and no adapter behavior changes.

- [ ] **Step 1: Add focused failing tests for opening precedence and the SVG join.**

In `test/test_neutral_scene_analysis_regression.py`, construct `SourceOpening` fixtures with `host_refs` and `geometry_refs` combinations and `UncertaintyRecord` codes. Assert conflict > unsupported > invalid > partial > not_available > diagnostic_only in overlapping cases; assert omitted SVG refs are carried from `scene.uncertainties`, `source_refs` includes the uncertainty reference, and all records retain `subtraction_performed is False`. In `test/test_svg_scene_adapter.py`, adapt a small SVG with an opening referencing one valid object and one missing host; assert the adapter still omits the missing host from `SourceOpening.host_refs`, leaves its opening uncertainty tuple unchanged, and emits `unresolved_opening_host_ref` with `details["omitted_refs"]`; call `analysis_scene_view(scene)` and assert the B2 record reports `partial` with that omitted ref.

Run: `pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q`
Expected before implementation: new diagnostic assertions fail because the B2 projection is absent.

- [ ] **Step 2: Implement the opening diagnostics with existing records only.**

Add the signatures and state order defined above. Match scene uncertainties only through `record.source_refs` containing `opening.id`; serialize matching uncertainty records with `to_dict()`. Include `SourceOpening` uncertainty records and all available source refs. Update `_opening_records(scene, geometry_points)` only to pass the whole scene into `_b2_opening_diagnostic`; preserve its current renderable `entries` behavior and do not manufacture a projected opening entry when geometry is absent.

- [ ] **Step 3: Add the B2 payload at the existing view handoff.**

In `_neutral_scene_view`, after `records` exist, build `b2_boundary_diagnostics` from `scene`, `records`, and exact shell IDs, then store it only inside `_analysis_view`. Preserve the existing top-level `uncertainties`, legacy buckets, and `_json_ready` privacy boundary.

- [ ] **Step 4: Run the focused opening tests.**

Run: `pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q`
Expected: PASS; SVG adapter data remains unchanged while B2 diagnostic retains its omitted-host uncertainty.

---

### Task 2: Resolve explicit shell identity and preserve occupancy

**Files:**
- Modify: `features/neutral_scene_views.py`, `_neutral_scene_view`, `_channel_blocker_records`, and new `_domain_shell_identity` / `_b2_boundary_diagnostics`.
- Test: `test/test_neutral_scene_analysis_regression.py`.

**Interfaces:**
- Consumes: `AnalysisDomain.source_id`, `SourceObject.source_id`, projected record IDs and roles, existing channel evidence.
- Produces: ID-based shell exclusion when exact identity is proven; a diagnostic blocker and no exclusions when it is not.

- [ ] **Step 1: Add an exact-identity fixture and an unprovable-identity fixture.**

The proven fixture has one `AnalysisDomain(id="domain-room", source_id="source-room", geometry_refs=("mesh-shared",))`, one shell `SourceObject(id="room-shell", source_id="source-room", source_role="slab", geometry_refs=("mesh-shared",))`, plus `SourceObject(id="wall-shared", source_id="source-wall", source_role="wall", geometry_refs=("mesh-shared",))` and `SourceObject(id="column-shared", source_id="source-column", source_role="column", geometry_refs=("mesh-shared",))`. Assert only `room-shell` appears in `domain_scope.shell_record_ids`; it is excluded from physical occupancy and walking blockers while the wall and column remain eligible/included. A second fixture sets domain `source_id=None` with the same geometry refs and asserts `shell_identity="blocked"`, a non-empty blocker, no shell IDs, and that geometry overlap removes neither wall nor column. Assert the explicit `AnalysisDomain` remains `domain_scope.source="explicit_authored"` and is not labeled as candidate promotion.

- [ ] **Step 2: Implement exact identity and record-ID exclusion.**

Add `_domain_shell_identity(scene, records)` as specified above. Extend `_channel_blocker_records` with `excluded_record_ids: set[str] | None = None`; skip those IDs before its existing `excluded_geometry_refs` check. In `_neutral_scene_view`, use proven IDs for `physical_mass_records` and `walk_blockers`; remove geometry-ref overlap as the B2 exclusion rule. Keep the legacy `physical_blockers` bucket unchanged. When identity is blocked, use an empty exclusion set and surface the blocker; do not raise, guess, or suppress occupancy.

- [ ] **Step 3: Populate physical occupancy and independent boundary support.**

Build diagnostic occupancy only from records already included in `physical_mass_records`, preserving source ID, normalized source role, and `_source_geometry_refs`. For wall/column records, add diagnostic boundary-support observations with `candidate_segment_ids` copied only from current source IDs, `conditional_support=False`, state `diagnostic_only`, and reason `b2_loop_closure_policy_deferred`. Do not calculate contact or closure. Set polygon and source-component records to `not_available` with reason `no_current_source_observation`; the current interfaces expose no factual record to preserve.

- [ ] **Step 4: Add the B2-only tolerance invariance assertion.**

Make two copies of one Neutral Scene using different `AnalysisContext.geometry_tolerance` and `topology_tolerance` values. Call `analysis_scene_view` on each and compare only:

```python
view_a["_analysis_view"]["b2_boundary_diagnostics"] == view_b["_analysis_view"]["b2_boundary_diagnostics"]
```

Do not compare the whole view or channel evidence; channel height-band behavior may legitimately consume `geometry_tolerance`. Confirm the new B2 helper signatures have no tolerance parameters and their bodies do not read either context tolerance.

- [ ] **Step 5: Run the focused neutral-view regression file.**

Run: `pixi run pytest test/test_neutral_scene_analysis_regression.py -q`
Expected: PASS; exact identity excludes only the explicit shell, unproven identity emits a blocker, and wall/column occupancy survives geometry-ref overlap.

---

### Task 3: Lock adapter boundaries and compatibility

**Files:**
- Read only: `adapters/svg_scene.py::_source_openings`, `adapters/ifc_bonsai.py::_native_opening_records`, and `adapters/blender_geometry.py::_validate_scene_references`.
- Test: `test/test_svg_scene_adapter.py`.
- Test: `test/test_blender_geometry_adapter.py`.
- Test: `test/test_ifc_bonsai_adapter.py` only if the existing opening fixture can be used to assert missing geometry uncertainty in a NeutralScene projection without changing adapter code.
- Read only: `features/group_self_description.py::_space_observations` and `_json_ready`.

**Interfaces:**
- Consumes: existing adapter outputs and current private `_analysis_view` boundary.
- Produces: evidence that adapter differences and public compatibility remain as-is.

- [ ] **Step 1: Verify IFC facts using the existing named interface.**

Inspect `_native_opening_records(source, geometry_by_source_id)` and its opening tests. Assert the current `SourceOpening` retains `host_refs`, `geometry_refs`, `opening_kind`, `provenance`, and `missing_geometry` uncertainty. Do not edit `adapters/ifc_bonsai.py`; if no existing test fixture can reach the projection without real IFC execution, leave IFC as a static interface check and state that limit.

- [ ] **Step 2: Preserve Blender dangling-reference rejection.**

Use the existing in-memory fixture pattern in `test/test_blender_geometry_adapter.py` to pass an opening with a dangling `host_refs` or `geometry_refs` into `load_blender_neutral_scene`; assert its existing `_validate_scene_references` path raises `ValueError` matching `dangling`. Do not transform a validation exception into a B2 uncertain opening.

- [ ] **Step 3: Verify the private/public compatibility boundary.**

Read `features/group_self_description.py::_space_observations` and `_json_ready`. If existing tests do not already assert private `_analysis_view` exclusion and deferred `free_space`, `connectivity`, and `bottleneck_profile`, add one focused assertion in `test/test_group_self_description.py`; otherwise add no test or production change. Do not propagate the private diagnostic or a local state label into public output.

- [ ] **Step 4: Run only the focused adapter and compatibility tests.**

Run:

```powershell
pixi run pytest test/test_svg_scene_adapter.py test/test_blender_geometry_adapter.py test/test_ifc_bonsai_adapter.py test/test_group_self_description.py -q
```

Expected: PASS. Existing SVG omission/uncertainty and Blender dangling-reference rejection remain distinct; IFC is static-only if its tests require external IFC execution.

---

## Non-goals

This plan adds only private B2 provenance/refusal plumbing. It does not add an adapter field, Neutral Scene contract field, public serialization, unified status enum, candidate selector, inferred domain, automatic promotion, geometry tolerance, contact or loop-closure policy, polygon/connectivity computation, free-space/topology backend, resolution, origin, clearance, bottleneck, route width, walkability, UI authority, real-IFC policy, Bayesian/ML inference, or merge. It does not alter explicit authored domain facts. Every opening diagnostic reports `subtraction_performed=False`.

## Commands for the implementation session

Run only after implementation is authorized:

```powershell
pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q
pixi run pytest test/test_blender_geometry_adapter.py test/test_ifc_bonsai_adapter.py test/test_group_self_description.py -q
git diff --check
```

Do not run full pytest, real IFC geometry, Blender, or implementation/design evidence runners under this plan.

## Self-review

- [x] Review findings 1–3: precedence includes partial; SVG uncertainty is joined by exact `source_refs`; explicit domain availability is distinct from candidate promotion.
- [x] Review finding 4: shell identity uses exact source IDs, includes a concrete shared-geometry fixture, and blocks with no geometry/proximity fallback.
- [x] Review finding 5: polygon and connectivity are unconditionally `not_available`; no current interface supplies observations.
- [x] Review finding 6: tolerance invariance compares only the B2 payload.
- [x] All owner constraints are copied into Global Constraints and Non-goals; no production step was executed while writing this plan.
- [x] Function/type names correspond to current definitions in `features/neutral_scene_views.py`, `features/scene_contract.py`, and the named adapters.
- [x] Planned test files exist; no implementation placeholders or new dependencies are specified.

## Handoff boundary

This document is a repaired implementation plan, not authorization to execute it. Obtain a separate owner implementation authorization after this plan receives review. If exact shell identity cannot be implemented from the named current fields, stop implementation and report the blocker; do not add a guessed identity rule.

STOP FOR D6 B2 PROVENANCE/REFUSAL IMPLEMENTATION PLAN V2

## Implementation disposition — 2026-10-07

Owner directed the bounded implementation to proceed while retaining the independent review findings. This section records implementation-time treatment without rewriting the review or earlier plan decisions.

1. **Walking-blocker regression:** `test_analysis_domain_support_mass_is_not_a_walking_blocker_when_overlapping_body_band` explicitly describes its slab as the selected AnalysisDomain support. The fixture will carry a matching, non-empty `AnalysisDomain.source_id` and `SourceObject.source_id`; additional shared-geometry coverage will ensure wall and column records remain included unless their own exact identity proves them to be the shell. A source-ID-less domain will assert blocked identity and retained occupancy. Geometry overlap will not establish identity.
2. **Authoritative file scope:** production/test edits are limited to `features/neutral_scene_views.py`, `test/test_neutral_scene_analysis_regression.py`, `test/test_svg_scene_adapter.py`, and `test/test_blender_geometry_adapter.py`. This plan is append-only. `test/test_ifc_bonsai_adapter.py` is read-only. `test/test_group_self_description.py` may be edited only for the private/public boundary assertion; current tests do not assert that `_analysis_view` diagnostics remain absent from the public group-description output, so one focused assertion is authorized if that remains true at implementation time.
3. **Optional source IDs:** private diagnostic `source_id` values remain nullable and preserve `None`; projected record IDs will not be substituted as source identities. Tests will exercise nullable IDs.
4. **Blender regression wording:** add a dangling-opening-reference regression through the existing Blender loader and assert its current rejection. Do not imply this opening-specific test already exists.

Implementation authorization is provided by the owner instruction accompanying this execution task. The implementation remains limited to the approved private provenance/refusal plumbing and its focused verification.

## Implementation execution record — 2026-10-07

The authorized bounded implementation is complete and is stopped for independent implementation review.

### TDD evidence

- The corrected regression module imports `pytest`; the earlier collection-time `NameError` is not treated as a valid RED result.
- Re-ran the same focused assertions after confirming the import:
  `pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py test/test_group_self_description.py -q -k "analysis_domain_support_mass or unidentified_analysis_domain or b2 or dangling_explicit_references"`
- Valid pre-implementation result: **12 failed, 132 deselected**. Failures reached assertions and identified absent B2 diagnostics plus geometry-reference overlap incorrectly removing shared wall/column records.
- After implementation, the same selection returned **12 passed, 132 deselected**.

### Implemented behavior

- Added private `_analysis_view.b2_boundary_diagnostics` for explicit domain scope, nullable physical source IDs, wall/column boundary-support observations, opening provenance/state, and downstream refusal. No public status enum or serializer changed.
- Domain shell exclusion from `physical_occupancy` and `walk_blockers` now requires one exact non-empty `AnalysisDomain.source_id` match to an eligible projected source record. Missing, unmatched, duplicate, unavailable, or ineligible identity produces a local blocker and no occupancy exclusion. Shared geometry references alone do not identify the shell.
- Preserved the existing `interface_facts` support-geometry filter as a separate legacy interface-candidacy behavior. This change does not alter that behavior.
- Opening uncertainty is joined only when `opening.id` occurs in scene-level `source_refs`; local opening uncertainty is retained. Precedence is conflict → unsupported → invalid/malformed → partial → not_available → diagnostic_only. Omitted host refs and uncertainty provenance are kept; subtraction always remains false, and missing-geometry openings do not gain renderable entries.
- Added the dangling Blender opening-host rejection regression and a private/public output-boundary regression. Updated the shared synthetic floor-slab fixture with an exact source identity so its intended explicit-domain support is testable without geometry-overlap inference.

### Verification

- Focused RED selection after implementation: **12 passed, 132 deselected**.
- `pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q`: **105 passed**.
- `pixi run pytest test/test_blender_geometry_adapter.py test/test_group_self_description.py test/test_ifc_bonsai_adapter.py::test_adapter_preserves_native_ifc_opening_and_host_facts -q`: **56 passed**. The IFC case constructs a temporary synthetic IFC4 opening fixture.
- A broader second-suite command including the entire `test/test_ifc_bonsai_adapter.py` was stopped before completion after inspection found tests that load real IFC geometry. No success is claimed for that command. The bounded synthetic opening fixture was run separately; real IFC geometry remains unverified in this checkpoint.
- `git diff --check`: passed.
- No full pytest, Blender, user IFC geometry, free-space/topology experiment, or evidence runner was run. The existing IFC adapter was exercised only through the isolated synthetic opening fixture above.

### Scope and handoff

Changed files are limited to `features/neutral_scene_views.py`, the four authorized regression modules (`test/test_neutral_scene_analysis_regression.py`, `test/test_svg_scene_adapter.py`, `test/test_blender_geometry_adapter.py`, and the specifically authorized `test/test_group_self_description.py` public-boundary assertion), and this plan record. `test/test_ifc_bonsai_adapter.py`, adapters, Neutral Scene contract, public API, dependencies, source IFC, and Blender files are unchanged. No files were staged or committed. Independent implementation review remains the next gate.

### Execution-boundary clarification

The broader command listed above for the second suite was interrupted after source inspection found repository tests that may load a real IFC model. Because quiet pytest output did not identify the active case before termination, it is **not verified whether that interrupted run had reached a real-IFC test**. Treat that command as incomplete and do not use it as real-IFC evidence. The separate bounded rerun completed only the Blender tests, group-description tests, and `test_adapter_preserves_native_ifc_opening_and_host_facts`, which writes and reads a temporary synthetic IFC4 fixture.

## Independent review coverage repair — 2026-10-07

The independent implementation review returned **REVISE** solely for missing direct coverage of fail-closed domain-shell identity branches and fixed private downstream refusal fields. No production defect was reported. The implementation branches already existed, so this repair adds regression coverage without a production-code edit.

- Added parameterized cases for duplicate and unmatched source IDs; ineligible `wall`, `boundary`, and `column` roles; an explicitly unavailable domain geometry (`geometry_refs=()`); and a matched source record with no projected geometry.
- Every blocked case asserts an empty `shell_record_ids`, the exact blocker and blocked identity state, and continued wall/column presence in both `physical_occupancy` and `walk_blockers`. Cases with a projected shell also assert that its own physical occupancy remains when identity is refused.
- The missing-projection source fixtures include the NeutralScene-required `missing_geometry` uncertainty. Empty `AnalysisDomain.geometry_refs` is a valid explicit unavailable-domain fact. No dangling reference or fabricated status was used.
- Direct assertions cover `candidate_polygon_validity.status=not_available`, `source_components.status=not_available`, and downstream `subtraction=refused`, `free_space=not_evaluated`, and `route=not_evaluated`.
- The first targeted run exposed invalid test construction for the two no-geometry source records; after adding their required uncertainty facts, the targeted selection passed. This was a fixture-contract correction, not a production-code failure.

Verification after the repair:

```powershell
pixi run pytest test/test_neutral_scene_analysis_regression.py -q -k "blocked_domain_shell_identity or b2_diagnostics_are_invariant_to_context_tolerance_values"
# 8 passed, 40 deselected

pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q
# 112 passed

pixi run pytest test/test_blender_geometry_adapter.py test/test_group_self_description.py test/test_ifc_bonsai_adapter.py::test_adapter_preserves_native_ifc_opening_and_host_facts -q
# 56 passed

git diff --check
# passed
```

The independent review report remains unchanged. No full suite, full IFC adapter module, Blender, or real IFC geometry was run. This append-only update and `test/test_neutral_scene_analysis_regression.py` are the only files changed for this review repair; no files were staged or committed.
