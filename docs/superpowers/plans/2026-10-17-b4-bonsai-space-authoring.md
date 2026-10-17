# B4 to Bonsai Space Authoring Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Extend the existing Blender Analyzer workbench so a user can prepare B4 enclosure candidates, preview and select one candidate, and explicitly create one native Bonsai/IFC IfcSpace with auditable provenance.

**Architecture:** Reuse the existing B4/domain handoff as the only enclosure source, the existing timer-driven runtime as the only background-job mechanism, and the existing GPU overlay as the preview surface. Add one feature-local candidate-cache/index module and one Bonsai polygon-to-IfcSpace adapter. Preparation and hover remain read-only; IFC mutation occurs only in the explicit create operation.

**Tech Stack:** Python 3.12 project runtime, Blender 5.2 portable, Bonsai 0.8.5, IfcOpenShell IFC4, Pixi, bpy.app.timers, existing region_overlay.py GPU drawing, pytest, and Jujutsu (jj), with Git fallback only if jj cannot perform the required operation.

**Spec:** docs/superpowers/specs/2026-10-17-b4-bonsai-space-authoring-design.md

## Global Constraints

- B4 remains the authoritative enclosure algorithm. Do not add a second polygonizer or call cursor-based Bonsai boundary discovery after a B4 candidate is selected.
- Bonsai owns native IfcSpace creation and Body representation assignment. The adapter may call set_space_representation_from_polygon or its tested equivalent only after validation.
- Preparation, candidate lookup, hover preview, and list selection are read-only. They must not mutate IFC or create temporary Blender objects.
- Candidate caches are invalid when plane, storey, source observation, structural identity, configuration, or positive height facts change.
- Unsupported holes or multi-part geometry must be rejected explicitly because the Bonsai 0.8.5 extrusion seam serializes only the exterior ring.
- Zero, negative, missing, or ambiguous height blocks writing before IFC mutation.
- A failed Bonsai write must never be reported as completed; partial entity creation must be surfaced with a diagnostic and an undo or cleanup path.
- New or modified project-owned functions require English-first docstrings and comments explaining non-obvious inference, geometry, identity, or adapter handoffs.
- Preserve unrelated dirty work. Stage and checkpoint only explicit feature files.
- Use the portable Blender at D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe for live checks.

---

### Task 1: Define the feature-local candidate cache and spatial index

Files:
- Create D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\features\space_authoring.py
- Test D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\test\test_space_authoring_cache.py

Interfaces:
- Consumes validated B4 candidate mappings from domain_handoff or structural_b4_view, plus plane, storey, configuration, observation, and height identities.
- Produces SpaceAuthoringCandidate, SpaceAuthoringCache, build_candidate_cache(candidates, *, plane_identity, storey_identity, source_identity, configuration_identity, height_facts), query_candidate(cache, point_xy), cache_freshness(cache, current_identity), and candidate_digest(candidate).

- [ ] Write focused tests for an interior hit, outside miss, identity freshness, malformed outline, duplicate binding, and unsupported holes.
- [ ] Run pixi run pytest test/test_space_authoring_cache.py -q and confirm the new interfaces fail before implementation.
- [ ] Implement immutable-friendly records preserving outline, holes, area, source references, column decisions, height facts, candidate digest, and the full identity tuple.
- [ ] Implement bbox filtering followed by point-in-polygon lookup. Reject non-finite coordinates, empty outlines, unsupported holes or multipolygons, and duplicate candidate bindings while building the cache.
- [ ] Run the focused tests and add boundary-point and stale-source assertions.
- [ ] Inspect jj status --ignore-working-copy and create a focused jj checkpoint named feat: add B4 space authoring candidate cache. Do not include unrelated files.

---

### Task 2: Integrate preparation with the existing runtime and truthful progress

Files:
- Modify D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\runtime.py
- Modify D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\__init__.py
- Test D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\test\test_space_authoring_runtime.py

Interfaces:
- Consumes the Task 1 cache API, existing RuntimeJob, RuntimeState, start_job, poll_job, cancel_job, invalidate_runtime, and the existing B4/domain capture seam.
- Produces start_space_authoring_preparation(context, *, plane_id, storey_id, configuration), space_authoring_status(), cancel_space_authoring_preparation(), retained STATE.space_authoring_cache and STATE.space_authoring_attempt, and stages capture, collect_b4, qualify, column_policy, validate_height, and index_publish.

- [ ] Write tests for staged lifecycle, cancellation, previous-cache preservation after failure, stale invalidation, and indeterminate progress when a denominator is unknown.
- [ ] Run pixi run pytest test/test_space_authoring_runtime.py -q and confirm failure before implementation.
- [ ] Add staged preparation as a thin extension of the existing timer runtime. Reuse the 50 ms callback budget and cancellation behavior. Capture identities before B4 work, call B4/domain once, apply the Bonsai-compatible column policy, validate geometry and height, build the index, and publish only a complete cache.
- [ ] Preserve the previous valid cache as historical on cancellation or failure. Do not add a second job registry or subprocess for hover.
- [ ] Serialize stage, elapsed time, candidate count, progress mode, and diagnostic. Show percentage only for a trustworthy denominator; otherwise show indeterminate progress.
- [ ] Run pixi run pytest test/test_space_authoring_runtime.py test/test_blender_analysis_runtime.py test/test_blender_analysis_ui.py -q.
- [ ] Create a focused jj checkpoint named feat: run space authoring preparation through runtime.

---

### Task 3: Add GPU-only preview and explicit candidate selection

Files:
- Modify D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\region_overlay.py
- Create D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\space_authoring_overlay.py
- Modify D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\__init__.py
- Test D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\test\test_space_authoring_overlay.py

Interfaces:
- Consumes SpaceAuthoringCache, query_candidate, analysis-plane ray coordinates, and the existing POST_VIEW handler registration.
- Produces set_space_authoring_preview(candidate_id or None), lock_space_authoring_candidate(candidate_id), clear_space_authoring_selection(), and a modal/list selection path that returns a candidate ID without writing IFC.

- [ ] Write tests for cached hover lookup, list fallback, lock and unlock, and the guarantee that preview creates no Blender object or IFC mutation.
- [ ] Run pixi run pytest test/test_space_authoring_overlay.py -q and confirm failure before implementation.
- [ ] Extend the existing GPU-only overlay path with a thin yellow outline and diagonal hatch for the cached candidate only. Convert the pointer ray into analysis-plane coordinates and never re-read IFC geometry or invoke B4 or Bonsai during pointer movement.
- [ ] Implement Esc or right-click clearing, left-click locking, and list selection. Only a locked candidate is eligible for writing.
- [ ] Run pixi run pytest test/test_space_authoring_overlay.py test/test_blender_analysis_overlay.py test/test_blender_analysis_ui.py -q.
- [ ] Create a focused jj checkpoint named feat: preview and lock B4 space candidates.

---

### Task 4: Implement the validated B4 polygon to Bonsai/IFC adapter

Files:
- Create D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\adapters\bonsai_space_authoring.py
- Modify D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\__init__.py
- Test D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\test\test_bonsai_space_authoring.py

Interfaces:
- Consumes a locked SpaceAuthoringCandidate, fresh cache identity, positive height facts, active IFC/Bonsai context, and selected storey/container.
- Produces validate_space_write(candidate, *, cache_identity, current_identity, height_facts), create_ifc_space_from_candidate(context, candidate, *, height_m, storey, name), and a stable candidate-to-IfcSpace binding containing candidate_id, GlobalId, storey_id, plane_uuid, and source digest.

- [ ] Write tests for invalid height, stale identity, missing storey, duplicate binding, malformed geometry, unsupported holes, and successful adapter invocation with a positive extrusion.
- [ ] Run pixi run pytest test/test_bonsai_space_authoring.py -q and confirm failure before implementation.
- [ ] Implement preflight validation before any IFC mutation. Generate a stable name from storey/context and candidate ID; do not rely on Bonsai's default Space0.
- [ ] Implement the native write transaction using Bonsai's IFC operator or transaction convention. Create the Blender object and IfcSpace through Bonsai, then pass the validated B4 polygon and positive height to set_space_representation_from_polygon or the tested supported seam, refresh the IFC object, and record the binding.
- [ ] If a post-creation step fails, return a partial-write diagnostic and invoke the supported undo or cleanup path; never claim completed.
- [ ] Run pixi run pytest test/test_bonsai_space_authoring.py test/test_bonsai_live.py test/test_bonsai_analysis_plane.py -q.
- [ ] Create a focused jj checkpoint named feat: write validated B4 candidates as native IFC spaces.

---

### Task 5: Add the independent Space Authoring panel and persistence

Files:
- Modify D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\__init__.py
- Modify D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\blender_addon\order_analyzer_ui\regions.py only if existing persistence helpers are the established owner
- Test D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\test\test_space_authoring_ui.py

Interfaces:
- Consumes preparation status, cache candidates, preview and lock state, create_ifc_space_from_candidate, and existing panel registration/preferences.
- Produces one independently collapsible OM_ANALYSIS_PT_space_authoring panel with Prepare Candidates, truthful stage/progress/elapsed/diagnostic, Cancel, candidate count/list, hover and lock status, positive height summary, Create IfcSpace, and stale/failure/partial-write messages.

- [ ] Write tests for panel registration, control enablement, stale blocking, and reopen persistence.
- [ ] Run pixi run pytest test/test_space_authoring_ui.py -q and confirm failure before implementation.
- [ ] Register the sixth independent panel beside Plane/Space, Region, Free-space, B4, and Results. Keep B4 responsible for diagnostics and inspection.
- [ ] Persist only analyzer-owned cache identity, candidate summaries, selected and locked IDs, result bindings, and overlay metadata. Never persist active runtime jobs or temporary preview geometry.
- [ ] Run pixi run pytest test/test_space_authoring_ui.py test/test_blender_analysis_ui.py test/test_blender_analysis_regions.py -q.
- [ ] Create a focused jj checkpoint named feat: expose Space Authoring panel.

---

### Task 6: Run portable Blender acceptance and iterate to user acceptance

Files:
- Modify only implementation files from Tasks 1 to 5 for focused acceptance defects.
- Create D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\test\test_space_authoring_acceptance.py
- Create D:\PROJECTS\understandOtherPackage\order_analyzer_spec004_delivery\docs\evidence\b4-space-authoring-live-acceptance.md

Interfaces:
- Consumes all preceding Space Authoring interfaces and the real IFC/Blender context.
- Produces reproducible live acceptance evidence and the user-visible Blender workflow.

- [ ] Run pixi run pytest test/test_space_authoring_cache.py test/test_space_authoring_runtime.py test/test_space_authoring_overlay.py test/test_bonsai_space_authoring.py test/test_space_authoring_ui.py -q.
- [ ] Launch only D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe if Blender is not already running, using the existing MCP/UI connection when available.
- [ ] Validate preparation progress, cancellation, successful candidate count, quick hover and list selection, lock, one native IfcSpace creation, Bonsai and IFC visibility, stale invalidation after plane/model/height change, invalid-height diagnostics, and duplicate prevention on the real IFC.
- [ ] Fix only acceptance defects that violate the spec and rerun the smallest affected checks. Do not add speculative modes, automatic whole-model creation, arbitrary tilted planes, or a new background framework.
- [ ] Obtain the user's live satisfaction report and repeat the focused iteration until accepted. Record each material iteration in the evidence file.
- [ ] Update docs/software-architecture.md and the relevant project-memory record after acceptance; verify the diagram agrees with the code.
- [ ] Inspect jj diff --stat and explicit scope, then create a final jj checkpoint named feat: add B4 Bonsai Space Authoring workflow. Do not push or merge without separate authorization.

---

## Plan Self-Review

### Spec coverage

- B4 reuse and no second polygonizer: Tasks 1, 2, and 4.
- Candidate cache, identity, index, and stale invalidation: Tasks 1 and 2.
- Truthful progress, cancellation, and failure preservation: Task 2.
- GPU-only preview, hover/list selection, and lock state: Task 3.
- Positive height, holes or multipolygon rejection, stable naming, transaction, and partial-write handling: Task 4.
- Independent panel and persistence: Task 5.
- Live Blender acceptance and user satisfaction loop: Task 6.
- Architecture synchronization and jj-first checkpointing: Task 6.

### Placeholder scan

No TBD, TODO, implement later, or vague edge-case instructions are used. Every code task names concrete files, interfaces, focused tests, and commands.

### Type consistency

- Task 1 produces SpaceAuthoringCandidate, SpaceAuthoringCache, build_candidate_cache, query_candidate, cache_freshness, and candidate_digest.
- Task 2 consumes the cache builder and produces runtime preparation and status functions.
- Task 3 consumes the cache and query API and produces preview and lock functions.
- Task 4 consumes the locked candidate and produces validation and write functions.
- Task 5 consumes runtime and write APIs and exposes the panel controls.
- Task 6 consumes all preceding interfaces and verifies the live workflow.

The plan intentionally does not add a general job registry, a new field hierarchy, a new IFC schema, automatic whole-model space creation, Revit-specific logic, or arbitrary 3D or tilted-plane inference.

