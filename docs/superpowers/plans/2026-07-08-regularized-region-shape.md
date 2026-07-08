# Regularized Region Shape Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make inferred region polygons choose between clean oriented rectangles and regularized convex hulls while keeping trend axes based on furniture-group organization.

**Architecture:** Keep the change inside `features/scene_inference.py`. The loader still emits neutral geometry; inference computes candidate polygons, shape metadata, and organization trend metadata. The notebook only visualizes the new metadata.

**Tech Stack:** Python stdlib geometry helpers, existing `Rect`, pytest, nbclient notebook execution.

---

### Task 1: Add Region Shape Tests

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing tests**

Add tests that build synthetic scenes through `evaluate_scene()` and assert:

```python
assert region["metadata"]["region-shape-basis"] == "oriented_rectangle"
assert irregular["metadata"]["region-shape-basis"] == "regularized_convex_hull"
assert irregular["metadata"]["axis-basis"] == "activity_group_frame_mean"
assert "shape-axis-angle" in irregular["metadata"]
assert "frame-delta" in irregular["metadata"]
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "regularized_region_shape or shape_frame"
```

Expected: fail because metadata and hull selection do not exist yet.

### Task 2: Implement Shape Selection

**Files:**
- Modify: `features/scene_inference.py`

- [ ] **Step 1: Add minimal geometry helpers**

Add helpers for convex hull, hull simplification, edge alignment, frame delta, and final shape metadata. Every function gets a docstring. Important geometry steps get English comments.

- [ ] **Step 2: Replace candidate polygon selection**

Update `_attach_region_axis_metadata()` so it still computes organization frame from groups, but chooses final `points` through the new shape selector.

- [ ] **Step 3: Run focused tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "regularized_region_shape or shape_frame"
```

Expected: pass.

### Task 3: Update Visual Notebook

**Files:**
- Modify: `test/svg_id_inference_demo.ipynb`

- [ ] **Step 1: Add shape-basis label/title output**

Include `region-shape-basis`, `shape-axis-angle`, and `frame-delta` in the region polygon title or nearby overlay label.

- [ ] **Step 2: Run notebook**

Run:

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/svg_id_inference_demo.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, p)"
```

Expected: notebook executes and regenerated HTML output includes the new metadata.

### Task 4: Verify And Save

**Files:**
- All touched files above

- [ ] **Step 1: Run full tests**

Run:

```bash
pixi run pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Visual QA**

Generate/open the SVG inference QA HTML and verify region polygons, shape-basis labels, and organization trend axes are present.

- [ ] **Step 3: Save with jj**

Run:

```bash
jj status
jj diff
jj split
jj describe -m "feat: regularize inferred region shapes"
```
