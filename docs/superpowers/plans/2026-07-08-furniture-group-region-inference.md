# Furniture Group Region Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current SVG fixtures work from furniture-group semantics without hand-authored activity region records.

**Architecture:** Reuse the existing `features/scene_inference.py` pipeline. Change grouping key selection so activity groups and inferred region candidates use authored furniture groups when region ids are neutral.

**Tech Stack:** Python stdlib, existing `Rect`, existing pytest and notebook verification.

---

### Task 1: Prove Group-Only Inference

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] Write a test that neutralizes object `region` to `global` while keeping `group`, then verifies five inferred region candidates from the SVG fixture.
- [ ] Run the focused test and confirm it fails before implementation.

### Task 2: Use Group Keys When Region Is Neutral

**Files:**
- Modify: `features/scene_inference.py`

- [ ] Add a helper that returns the analysis grouping key: non-neutral `region` first, otherwise non-neutral `group`.
- [ ] Use the helper in affordance zones, affordance extents, activity groups, raw region candidates, and boundary cue matching.
- [ ] Keep authored explicit region suppression behavior unchanged.

### Task 3: Verify

**Files:**
- Modify: `test/svg_id_inference_demo.ipynb` only if notebook outputs need source updates.

- [ ] Run the focused pytest.
- [ ] Run the full pytest suite.
- [ ] Execute the SVG inference notebook and inspect generated outputs for the three official SVG fixtures.
- [ ] Save the `jj` change after verification.
