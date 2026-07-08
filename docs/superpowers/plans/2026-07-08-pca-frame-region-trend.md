# PCA Frame Region Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compute inferred region trend axes from affordance point-cloud PCA instead of raw member furniture orientation means.

**Architecture:** Keep SVG/BIM loading neutral. Replace the trend helper in `features/scene_inference.py` so inferred region candidates carry PCA frame metadata. Reuse the existing notebook overlay path and add only source/tests needed to expose the new evidence.

**Tech Stack:** Python stdlib math, existing `Rect`, pixi/pytest, nbclient notebook execution.

---

## File Map

- Modify `features/scene_inference.py`: replace `_axis_orientation_stats()` usage with PCA frame stats over affordance/member points.
- Modify `test/test_floorplan_scene_loader.py`: add focused tests for frame-equivalent horizontal/vertical groups and update existing basis expectations.
- Modify `test/svg_id_inference_demo.ipynb`: expose PCA basis/extents in overlay titles/data attributes if absent.
- Generated ignored QA output remains under `test/output/svg_id_fixture_overlays/`.

## Task 1: Add PCA Frame Tests

- [ ] Add a synthetic scene test with two inferred regions: one horizontal repeated table group and one vertical repeated table group. Assert both use `axis-basis == "affordance_point_pca_frame"` and both have `axis-strength > 0.8`.
- [ ] Update oblique SVG trend tests so they expect `axis-basis == "affordance_point_pca_frame"` and non-empty `axis-primary-extent` / `axis-secondary-extent`.
- [ ] Run the focused tests and verify they fail because current code still writes `member_orientation_axis_mean`.

## Task 2: Implement Minimal PCA Frame Helper

- [ ] Replace `_axis_orientation_stats()` with `_pca_frame_stats(points)` or route `_attach_region_axis_metadata()` through that helper.
- [ ] Compute centroid, covariance, closed-form 2D primary eigenvector angle, variance clarity, and projected extents using only stdlib math.
- [ ] Keep fallback behavior: fewer than two points or near-zero total variance returns angle `0`, strength `0`, extents `0`.
- [ ] Use the PCA angle in `_oriented_envelope()` and write PCA metadata keys.
- [ ] Run focused tests and verify they pass.

## Task 3: Notebook Evidence

- [ ] Update `_inference_overlay_html()` in `test/svg_id_inference_demo.ipynb` only if it does not show basis/extents.
- [ ] Execute the notebook with nbclient.
- [ ] Run the notebook source test.

## Task 4: Verification

- [ ] Run `pixi run pytest -q`.
- [ ] Extract notebook HTML to `test/output/svg_id_fixture_overlays/svg_id_inference_trend_qa.html`.
- [ ] Render a screenshot to `test/output/svg_id_fixture_overlays/svg_id_inference_trend_qa.png`.
- [ ] Inspect DOM counts for `region-trend`, `region-polygon`, and `axis-strength`.

## Task 5: JJ Save

- [ ] Run `jj status`.
- [ ] Describe the change with `jj describe -m "feat: infer PCA frame region trends"`.
- [ ] Run `jj new`.

## Self Review

The plan is intentionally narrow. It fixes the current trend algorithm at the inference boundary and defers multi-group region frame averaging until the hierarchy model can represent multiple furniture groups inside one region.
