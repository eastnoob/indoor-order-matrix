# Region Frame Extent Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure region trend axis lengths use the same final frame angle that the overlay draws.

**Architecture:** Keep the existing inference pipeline. Add one regression test, then recompute frame extents at the final angle in the shared region metadata path.

**Tech Stack:** Python, pytest, pixi, Jupyter notebook execution.

---

### Task 1: Regression And Fix

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`
- Modify: `features/scene_inference.py`
- Modify: `test/svg_id_inference_demo.ipynb`

- [ ] Add a regression test that loads `test/SVG_chaoticsvg.svg`, reads the inferred `north_tables` final `axis-angle`, recomputes extents from the candidate polygon points, and asserts they match `axis-primary-extent` and `axis-secondary-extent`.
- [ ] Run the new test and verify it fails before production changes.
- [ ] Recompute frame extents in `_frame_with_explainability_correction()` after the final angle is known.
- [ ] Run the focused test and then the full pytest suite.
- [ ] Re-execute `test/svg_id_inference_demo.ipynb` into `test/output/svg_id_inference_demo.executed.ipynb`, regenerate the visual HTML/PNG, and inspect the output.
