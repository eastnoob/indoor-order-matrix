# Layout Hierarchy Network Boundary Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add minimal, tested evidence skeletons for activity groups, shared spatial networks, and semantic boundaries.

**Architecture:** Keep SVG loading, inference, and matrix evaluation separate. Add derived evidence in `features/scene_inference.py`; wire it through `features/scene_evaluator.py`; verify with plain dict scenes.

**Tech Stack:** Python 3.14 via Pixi, pytest, existing `Rect` helpers.

---

### Task 1: Activity Groups

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`
- Modify: `features/scene_inference.py`
- Modify: `features/scene_evaluator.py`

- [ ] **Step 1: Write the failing test**

Add a test that builds two chair/table records in one region, evaluates the scene, and asserts `matrix["activity_groups"][0]` has a union bbox and overlap evidence.

- [ ] **Step 2: Run test to verify it fails**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_evaluate_scene_exposes_activity_groups_from_furniture_affordance_extents`

Expected: FAIL because `activity_groups` is missing.

- [ ] **Step 3: Write minimal implementation**

Add `activity_groups(scene, furniture_affordance_extents)` to `scene_inference.py`, expose it from `infer_scene_evidence()`, and return it from `evaluate_scene()`.

- [ ] **Step 4: Run test to verify it passes**

Run the same focused test and expect PASS.

### Task 2: Shared Spatial Networks

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`
- Modify: `features/scene_inference.py`
- Modify: `features/scene_evaluator.py`

- [ ] **Step 1: Write the failing test**

Add a test asserting `region_internal` and `inter_region` network records share keys `id`, `scope`, `nodes`, `edges`, `components`, `metadata`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_evaluate_scene_exposes_shared_spatial_network_schema`

Expected: FAIL because `spatial_networks` is missing.

- [ ] **Step 3: Write minimal implementation**

Add `spatial_networks(activity_groups, gap_paths)` to `scene_inference.py` using existing component helper.

- [ ] **Step 4: Run test to verify it passes**

Run the focused test and expect PASS.

### Task 3: Boundary Semantics

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`
- Modify: `features/scene_inference.py`
- Modify: `features/scene_evaluator.py`

- [ ] **Step 1: Write the failing test**

Add a test with rug, low cabinet, and glass boundaries. Assert walk/see passability, thickness, grouping, and surface identity.

- [ ] **Step 2: Run test to verify it fails**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_evaluate_scene_exposes_boundary_semantic_profiles`

Expected: FAIL because `boundary_semantics` is missing.

- [ ] **Step 3: Write minimal implementation**

Add `boundary_semantics(scene)` to `scene_inference.py`, expose it from `infer_scene_evidence()`, and pass through evaluator/payload geometry.

- [ ] **Step 4: Run test to verify it passes**

Run the focused test and expect PASS.

### Task 4: Docs And Full Verification

**Files:**
- Modify: `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- Modify: `docs/indoor_layout_evaluation_matrix_task_status.md`

- [ ] **Step 1: Update docs**

Record the new skeletons and keep BIM/Rhino plugin deferred.

- [ ] **Step 2: Run full suite**

Run: `pixi run pytest -q`

Expected: all tests pass.

## Self Review

The plan maps every spec requirement to one testable task. No task requires a new dependency, new adapter, or large refactor.
