# Group Frame Region Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Infer region trend from furniture-group PCA frames and draw both primary and secondary region axes.

**Architecture:** `features/scene_inference.py` computes activity-group frames and region trend means. The evaluator continues to consume metadata. The SVG inference notebook visualizes the two-axis region frame.

**Tech Stack:** Python stdlib math/statistics, existing `Rect`, pixi/pytest, nbclient, Chrome visual QA.

---

## File Map

- Modify `features/scene_inference.py`: add group frame helpers, region frame mean helper, and route inferred region metadata through activity-group frames.
- Modify `features/scene_evaluator.py` only if existing consumers need metadata naming support.
- Modify `test/test_floorplan_scene_loader.py`: add TDD coverage for group metadata and region frame mean.
- Modify `test/svg_id_inference_demo.ipynb`: draw primary and secondary axes.
- Add spec/plan docs under `docs/superpowers/`.

## Task 1: Tests

- [ ] Add a test that `infer_scene_evidence()` exposes activity groups with `metadata["group-axis-basis"] == "affordance_group_pca_frame"`.
- [ ] Add a direct helper-level test or scene-level test proving region trend metadata uses `axis-basis == "activity_group_frame_mean"`.
- [ ] Add a test for the notebook source requiring `region-trend-primary` and `region-trend-secondary`.
- [ ] Run focused tests and confirm they fail before implementation.

## Task 2: Group Frames

- [ ] Reuse the existing `_pca_frame_stats()` helper for activity-group point clouds.
- [ ] Add `_activity_group_frame()` to compute group frame metadata from member records and affordance extents.
- [ ] Store group frame metadata on activity groups without changing their bbox contract.

## Task 3: Region Frame Mean

- [ ] Add `_region_frame_mean(group_frames)` using four-angle circular mean.
- [ ] Update inferred region candidate metadata so `axis-basis` becomes `activity_group_frame_mean`.
- [ ] Preserve existing candidate `rect` for downstream bbox metrics.
- [ ] Preserve oriented `points` for visual QA, using the region frame angle.

## Task 4: Notebook Dual-Axis Overlay

- [ ] Draw the primary axis as `data-layer="region-trend-primary"`.
- [ ] Draw the secondary axis as `data-layer="region-trend-secondary"`.
- [ ] Keep `data-axis-strength`, extent, and member-alignment metadata on both lines.

## Task 5: Verification

- [ ] Run `pixi run pytest -q`.
- [ ] Execute `test/svg_id_inference_demo.ipynb` with nbclient.
- [ ] Generate `test/output/svg_id_fixture_overlays/svg_id_inference_trend_qa.html`.
- [ ] Use Chrome to visually inspect or screenshot the QA HTML.

## Task 6: JJ Save

- [ ] Confirm `test/SVG_abnormal.svg` remains untouched by this change.
- [ ] Run `jj describe -m "feat: infer region trends from group frames"`.
- [ ] Run `jj new`.

## Self Review

This plan intentionally avoids new dependencies and automatic sub-group discovery. It creates the correct group-frame to region-trend seam first, then leaves richer group discovery for a later task.
