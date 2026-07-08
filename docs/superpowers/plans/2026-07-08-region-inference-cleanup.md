# Region Inference Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exclude decorative objects from automatic region solving, make regular hulls collapse to rectangles, and separate trend visual length from trend strength.

**Architecture:** Keep production changes in `features/scene_inference.py`. Keep visual-only changes in `test/svg_id_inference_demo.ipynb`. Tests live in `test/test_floorplan_scene_loader.py`.

**Tech Stack:** Python stdlib, existing `Rect`, pytest, nbclient notebook execution.

---

### Task 1: Decorative Object Filtering

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`
- Modify: `features/scene_inference.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting a `plant` in the same region is excluded from inferred-region member ids and does not expand the rect, while `metadata["region-shape-anchor"] = "true"` opts it back in.

- [ ] **Step 2: Run focused tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "decorative_object or region_shape_anchor"
```

Expected: fail because filtering does not exist.

- [ ] **Step 3: Implement helper**

Add `_participates_in_region_inference(record)` and use it in `activity_groups()` and `_raw_inferred_region_candidates()`.

### Task 2: Hull Shape Rule

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`
- Modify: `features/scene_inference.py`

- [ ] **Step 1: Write failing test**

Assert `SVG_baseline.svg` `center_lounge` has `region-shape-basis == "oriented_rectangle"` even when the simplified hull has eight vertices.

- [ ] **Step 2: Implement minimal rule**

Change near-collinear tolerance from `8°` to `15°`, and keep an eight-vertex hull rectangular when `aligned_edge_ratio >= 0.75`.

### Task 3: Trend Visual Semantics

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`
- Modify: `test/svg_id_inference_demo.ipynb`
- Modify: `features/scene_inference.py`

- [ ] **Step 1: Write failing tests**

Assert metadata includes `axis-shape-clarity`, `axis-trend-strength`, and notebook source includes `axis-visual-length-basis` without `extent * max(0.15, strength)`.

- [ ] **Step 2: Implement metadata and notebook update**

Add semantic aliases in inference metadata and make notebook axis length use `extent * 0.65` with opacity still based on strength.

### Task 4: Verification

- [ ] **Step 1: Run focused tests**

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "decorative_object or region_shape_anchor or center_lounge or svg_id_inference_notebook"
```

- [ ] **Step 2: Run full tests**

```bash
pixi run pytest -q
```

- [ ] **Step 3: Execute notebook**

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/svg_id_inference_demo.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, p)"
```

- [ ] **Step 4: Visual QA**

Extract the notebook HTML, open it in a browser, and verify region polygons and trend axes render with shape-basis and visual-length metadata.
