# Member Frame Trend Ground Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make region trend direction and strength come from member furniture frame consensus when directional member evidence exists.

**Architecture:** Keep `features/scene_inference.py` as the inference layer. Change `_activity_group_frame()` so member-frame consensus is the primary trend source while PCA remains geometry diagnostics/fallback. Tests live in `test/test_floorplan_scene_loader.py`.

**Tech Stack:** Python, pytest, pixi, nbclient, html2image/Edge.

---

### Task 1: Tests

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] Add a focused synthetic test proving a single directional table can produce high `axis-strength`.
- [ ] Add an SVG fixture regression proving `SVG_chaoticsvg.svg` `east_work` follows its member frame rather than the bbox/PCA frame.
- [ ] Run the new focused tests and verify they fail before production code changes.

### Task 2: Implementation

**Files:**
- Modify: `features/scene_inference.py`

- [ ] Update `_activity_group_frame()` so `_member_frame_consensus()` supplies trend angle and strength whenever it has positive directional support.
- [ ] Keep PCA stats for geometric fallback and clarity diagnostics.
- [ ] Add metadata fields for support and geometry angle if needed by tests/audits.
- [ ] Run focused tests and then full `pixi run pytest -q`.

### Task 3: Visual QA

**Files:**
- Modify: `test/output/svg_id_inference_demo.executed.ipynb`
- Modify: `test/output/svg_id_inference_demo.visual.html`
- Modify: `test/output/svg_id_inference_demo.visual.png`

- [ ] Execute `test/svg_id_inference_demo.ipynb` into `test/output/svg_id_inference_demo.executed.ipynb`.
- [ ] Extract HTML output to `test/output/svg_id_inference_demo.visual.html`.
- [ ] Render `test/output/svg_id_inference_demo.visual.png`.
- [ ] Inspect the PNG, especially `SVG_chaoticsvg.svg` `east_work` and `north_tables`.
