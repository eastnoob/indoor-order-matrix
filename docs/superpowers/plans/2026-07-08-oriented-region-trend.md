# Oriented Region Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Infer activity region polygons and trend axes from rotated member furniture so SVG probe layouts no longer collapse to horizontal/vertical bbox trends.

**Architecture:** SVG loading remains an adapter that emits neutral scene geometry. Region polygons and trend metadata are derived in `features/scene_inference.py`. `features/scene_evaluator.py` keeps using existing axis descriptor behavior.

**Tech Stack:** Python stdlib math/statistics, existing `Rect` and `Polygon`, pixi/pytest, nbclient notebook execution.

---

## File Map

- Modify `features/scene_loader.py`: preserve transform orientation, transformed rectangle points, and bbox from points.
- Modify `features/scene_inference.py`: add oriented-envelope helper and member-orientation trend metadata for inferred region candidates.
- Modify `test/test_floorplan_scene_loader.py`: add tests for loader orientation, inferred region points, trend angle, and strength differences.
- Modify `test/svg_id_inference_demo.ipynb`: draw inferred region polygons and expose trend strength.

## Task 1: Loader Rotated Rect Geometry

**Files:**
- Modify: `features/scene_loader.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write the failing test**

Add a test that loads `test/SVG_oblique.svg`, finds `center_sofa_upper`, and asserts:

```python
assert round(obj["orientation"], 4) == 90.0
assert len(obj["points"]) == 5
assert obj["rect"].width > 50
assert obj["rect"].height > 140
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_svg_loader_preserves_rotated_rect_points_and_orientation`

Expected: fail because `orientation` is missing and `points` is empty.

- [ ] **Step 3: Implement minimal loader changes**

In `_shape_record()`, read transform angle from `meta["_transform"]`, write `orientation`, and add `metadata["orientation"]` when absent.

In `_points_for_shape()`, return transformed rectangle corners for `rect`:

```python
if tag == "rect":
    x = float(attrib.get("x", 0) or 0)
    y = float(attrib.get("y", 0) or 0)
    width = float(attrib.get("width", 0) or 0)
    height = float(attrib.get("height", 0) or 0)
    points = [
        _transform_point(x, y, tx, ty, angle),
        _transform_point(x + width, y, tx, ty, angle),
        _transform_point(x + width, y + height, tx, ty, angle),
        _transform_point(x, y + height, tx, ty, angle),
    ]
    return [*points, points[0]]
```

In `_rect_for_shape()`, for `rect`, build bbox from `_points_for_shape()`.

- [ ] **Step 4: Run focused test**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_svg_loader_preserves_rotated_rect_points_and_orientation`

Expected: pass.

## Task 2: Inferred Region Polygon And Trend Metadata

**Files:**
- Modify: `features/scene_inference.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing tests**

Add tests that:

```python
oblique = infer_scene_evidence(load_structured_svg_scene(Path("test/SVG_oblique.svg")))
center = {item["region"]: item for item in oblique["inferred_region_candidates"]}["center_lounge"]
assert len(center["points"]) == 5
assert center["metadata"]["axis-basis"] == "member_orientation_axis_mean"
assert float(center["metadata"]["axis-strength"]) > 0.9
assert 80.0 <= float(center["metadata"]["axis-angle"]) <= 100.0
```

And:

```python
baseline = infer_scene_evidence(load_structured_svg_scene(Path("test/SVG_baseline.svg")))
chaotic = infer_scene_evidence(load_structured_svg_scene(Path("test/SVG_chaoticsvg.svg")))
baseline_north = {item["region"]: item for item in baseline["inferred_region_candidates"]}["north_tables"]
chaotic_north = {item["region"]: item for item in chaotic["inferred_region_candidates"]}["north_tables"]
assert float(baseline_north["metadata"]["axis-strength"]) > float(chaotic_north["metadata"]["axis-strength"])
```

- [ ] **Step 2: Run focused tests to verify they fail**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_inferred_oblique_region_uses_member_orientation_trend test/test_floorplan_scene_loader.py::test_chaotic_probe_has_weaker_north_table_trend_than_baseline`

Expected: fail because inferred candidates have no points or axis metadata.

- [ ] **Step 3: Implement minimal inference helpers**

Add helpers in `features/scene_inference.py`:

- `_record_points(record)` returns `record["points"]` or rect corners.
- `_axis_orientation_stats(records)` computes axis mean and strength from member orientations, weighted by `max(width, height) / max(min(width, height), 1e-9)` minus 1.
- `_oriented_envelope(points, angle, scene_size)` projects points into the axis frame, builds a local bbox, transforms corners back, and returns `(rect, closed_points)`.
- `_attach_region_axis_metadata(candidate, members, scene_size)` returns a copy with `points`, bbox `rect`, and axis metadata.

Use these helpers inside `_raw_inferred_region_candidates()` after building the initial member/boundary points. Keep existing spacing expansion, but update it to preserve and expand polygon points through the same oriented envelope when possible.

- [ ] **Step 4: Run focused tests**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_inferred_oblique_region_uses_member_orientation_trend test/test_floorplan_scene_loader.py::test_chaotic_probe_has_weaker_north_table_trend_than_baseline`

Expected: pass.

## Task 3: Notebook Visual Evidence

**Files:**
- Modify: `test/svg_id_inference_demo.ipynb`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing test assertion**

Extend `test_svg_id_inference_notebook_presents_three_auto_inference_fixtures()` to assert source contains:

```python
assert "region-polygon" in source
assert "axis-strength" in source
```

- [ ] **Step 2: Run notebook source test**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_svg_id_inference_notebook_presents_three_auto_inference_fixtures`

Expected: fail until notebook overlay renders polygon and strength.

- [ ] **Step 3: Update notebook overlay**

In `_inference_overlay_html()`:

- draw `region["points"]` as `<polygon data-layer="region-polygon">` when present.
- keep rect fallback for regions without points.
- write `data-axis-strength` on `region-trend`.
- set trend line opacity to `0.35 + 0.55 * strength`.

- [ ] **Step 4: Execute notebook**

Run:

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/svg_id_inference_demo.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, p)"
```

Expected: exit 0.

- [ ] **Step 5: Run notebook source test**

Run: `pixi run pytest -q test/test_floorplan_scene_loader.py::test_svg_id_inference_notebook_presents_three_auto_inference_fixtures`

Expected: pass.

## Task 4: Full Verification And Visual QA

**Files:**
- Generated ignored files under `test/output/svg_id_fixture_overlays/`

- [ ] **Step 1: Run full tests**

Run: `pixi run pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Generate visual QA HTML from executed notebook**

Run a Python snippet that extracts `text/html` output from `test/svg_id_inference_demo.ipynb` to `test/output/svg_id_fixture_overlays/svg_id_inference_trend_qa.html`.

- [ ] **Step 3: Browser screenshot**

Use Edge/Playwright to render the QA HTML and save `test/output/svg_id_fixture_overlays/svg_id_inference_trend_qa.png`.

Expected DOM counts:

```json
{
  "trend": 15,
  "candidate": 15,
  "polygon": 15
}
```

- [ ] **Step 4: Inspect screenshot**

Confirm oblique and chaotic probes visibly differ from baseline: oblique region polygons and orange trend axes should not all collapse to horizontal/vertical bbox lines.

## Task 5: JJ Save Point

**Files:**
- All modified tracked files

- [ ] **Step 1: Confirm working copy**

Run: `jj status`

Expected: only spec, plan, source, notebook, and tests are tracked. `test/output/` remains ignored.

- [ ] **Step 2: Describe current change**

Run: `jj describe -m "feat: infer oriented region trends"`

- [ ] **Step 3: Open next empty change**

Run: `jj new`

Expected: new empty working copy on top of the described change.

## Self Review

The plan covers the spec requirements: loader neutral geometry, inference region polygon/trend metadata, notebook visual evidence, full test and visual QA, and jj save point. No new dependencies are introduced. Existing axis-aligned gap path logic remains unchanged by design.
