# Separate SVG Input, Inference, and Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SVG/BIM-style inputs a neutral scene source, move affordance/region/path inference into a separate evidence layer, and keep the evaluation matrix as a consumer of scene plus evidence.

**Architecture:** `features/scene_loader.py` remains the SVG-to-neutral-scene adapter. `features/scene_inference.py` becomes the neutral-scene inference layer for affordance zones, inferred regions, inferred region gap paths, and gap-path graph evidence. `features/scene_evaluator.py` consumes that evidence and emits matrix rows, overlays, and adapter payloads.

**Tech Stack:** Python stdlib, existing `Rect` model, existing affordance profiles, existing pytest suite through Pixi.

---

### Task 1: Extract The Inference Layer

**Files:**
- Create: `features/scene_inference.py`
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write boundary tests**

Add tests proving `infer_scene_evidence(scene)` produces affordance zones, candidates, inferred regions, and gap paths without using SVG APIs, and proving `evaluate_scene(scene)` consumes the same evidence without changing existing metric output.

- [ ] **Step 2: Verify tests fail before extraction**

Run: `pixi run pytest test/test_floorplan_scene_loader.py -q -k "scene_inference_layer or manual_required_path_width"`

Expected: FAIL because `features.scene_inference` does not exist.

- [ ] **Step 3: Move inference code**

Move the minimum existing inference functions out of `features/scene_evaluator.py` into `features/scene_inference.py`: affordance zones, inferred region candidates, inferred regions, inferred gap paths, manual required path width, and gap-path graph assembly.

- [ ] **Step 4: Update evaluator wiring**

`evaluate_scene(scene)` calls `infer_scene_evidence(scene)` once and uses returned evidence. No evaluator row function may call `_inferred_region_candidates(scene)` directly.

- [ ] **Step 5: Verify focused tests**

Run: `pixi run pytest test/test_floorplan_scene_loader.py -q -k "scene_inference_layer or manual_required_path_width or gap_path or adapter_payload"`

Expected: PASS.

### Task 2: Record The Architecture Memory

**Files:**
- Create: `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- Modify: `docs/indoor_layout_evaluation_matrix_task_status.md`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write memory test**

Add a test asserting the architecture memory states that SVG is a neutral BIM proxy/base map, not the matrix definition, and that matrix rows consume neutral scene plus inference evidence.

- [ ] **Step 2: Verify test fails**

Run: `pixi run pytest test/test_floorplan_scene_loader.py -q -k "architecture_memory"`

Expected: FAIL because the memory file does not exist.

- [ ] **Step 3: Write memory document**

Create `docs/indoor_layout_evaluation_matrix_architecture_memory.md` with the durable boundary rule and update task status with the same rule.

- [ ] **Step 4: Verify docs tests**

Run: `pixi run pytest test/test_floorplan_scene_loader.py -q -k "architecture_memory or audit_records_automatic_svg_path or method_ledger_records_source_backed_method_decisions"`

Expected: PASS.

### Task 3: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run full suite**

Run: `pixi run pytest -q`

Expected: PASS with no failures.

- [ ] **Step 2: Check working-copy state**

Run: `jj status`

Expected: Changed files are limited to inference split, docs, and existing dirty files.

---

## Completion Standard

- SVG loader only creates neutral scene records.
- Inference layer owns affordance/region/path evidence generation.
- Evaluation matrix consumes neutral scene plus inference evidence.
- Architecture memory explicitly says SVG is a base-map/BIM proxy, not the matrix framework.
- Focused and full tests pass.
