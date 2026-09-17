# Terminal Geometry Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make furniture and furniture-group trend, coherence, and column-grid alignment depend on final analysis geometry rather than historical or authored rotation records.

**Architecture:** The adapter supplies final world-space Analysis MassPatch geometry. `features.furniture_frame` derives terminal member frames. `features.scene_inference` derives group terminal trend and member coherence. Column-grid consumers read only the derived group trend. Historical orientation remains audit-only.

**Tech Stack:** Python 3.12 via Pixi, pytest, `MeshGeometry3D`, Neutral Scene, IFC/Bonsai adapter.

**Spec:** `docs/superpowers/specs/2026-09-24-terminal-geometry-trend-design.md`

## Global Constraints

- Use Pixi; do not add pip/venv dependencies.
- Do not change IFC schema semantics, add matrix results, or add UI/visualization.
- `Analysis` MassPatch is analytical geometry; `Body` is audit-only.
- Historical/authored orientation is provenance-only.
- Modified project code needs English-first docstrings and intent comments.
- Do not revert unrelated dirty-worktree changes.
- Use `jj` for checkpoints when the repository is jj-managed; the listed commit messages are checkpoint descriptions, not permission to rewrite unrelated history.

## Review Focus

- Oblique final geometry with no rotation metadata remains oblique.
- Stale orientation cannot override final geometry.
- Mixed members lower coherence without hiding group trend.
- IFC/Bonsai final Analysis geometry reaches Neutral Scene.
- Oblique groups are not fully aligned to an orthogonal grid.

---

### Task 1: Terminal single-furniture frame contract

**Files:** `features/furniture_frame.py`, `test/test_furniture_frame.py`

- [ ] Write failing tests for an oblique MassPatch with no metadata, the same geometry with stale orientation metadata, and a square/circular proxy with weak strength.
- [ ] Run `pixi run pytest test/test_furniture_frame.py -q`; verify the new precedence test fails for the intended reason.
- [ ] Keep the existing area-weighted PCA, but make its contract explicitly final-geometry-only. Preserve compatibility keys and add terminal-geometry names only where needed.
- [ ] Add English-first comments explaining why MassPatch geometry, not rotation history, is authoritative.
- [ ] Run the focused test again and commit `fix: define terminal geometry furniture frames`.

### Task 2: Terminal furniture-group trend and coherence

**Files:** `features/scene_inference.py`, `features/neutral_scene_views.py`, `test/test_floorplan_scene_loader.py`, `test/test_neutral_scene_analysis_regression.py`

- [ ] Write failing tests with two or three final 30-degree MassPatches and no orientation facts; assert an approximately 30-degree group trend.
- [ ] Add a stale-0-degree metadata case; assert the group result is unchanged.
- [ ] Add a mixed-member case; assert group geometry trend remains descriptive while member terminal coherence/clarity falls.
- [ ] Run `pixi run pytest test/test_floorplan_scene_loader.py -q -k "furniture_group or trend or frame"` and `pixi run pytest test/test_neutral_scene_analysis_regression.py -q -k "furniture_group or frame"`; verify the current failure.
- [ ] Refactor `_furniture_group_frame` so reported group trend comes from final world-space member geometry, affordance extents, and centers. Use member terminal frames only as coherence evidence. Do not read `authored_orientation` or legacy `orientation` for angle or strength.
- [ ] Normalize each member contribution so tessellation density is not a hidden perceptual weight. Keep low clarity for symmetric or contradictory geometry.
- [ ] Name/annotate metadata as `group_terminal_trend`, `member_terminal_trend_coherence`, and provenance-only legacy fields, preserving compatibility output where required.
- [ ] Run focused tests and commit `fix: infer furniture group trends from terminal geometry`.

### Task 3: IFC/Bonsai final Analysis geometry handoff

**Files:** `adapters/ifc_bonsai.py`, `adapters/blender_geometry.py` only if required, `test/test_ifc_bonsai_adapter.py`

- [ ] Write a failing injected IFC test whose Analysis geometry is already oblique while placement and orientation facts are zero; assert extracted vertices remain oblique and Analysis is selected.
- [ ] Run `pixi run pytest test/test_ifc_bonsai_adapter.py -q -k "analysis or transform or geometry"` and verify the failure.
- [ ] Correct only the handoff if necessary. Preserve final coordinates; expose uncertainty when unavailable; never substitute historical rotation.
- [ ] Run `pixi run pytest test/test_ifc_bonsai_adapter.py test/test_furniture_frame.py -q` and commit `test: preserve final analysis geometry for trend inference`.

### Task 4: Column-grid consumer

**Files:** `features/column_grid.py`, `features/scene_evaluator.py` only if required, `test/test_column_grid_trend_regression.py`

- [ ] Write failing tests for a 30-degree group against a 0/90-degree grid: alignment must be less than 1 and deviation non-zero. Keep 0/90 equivalence passing.
- [ ] Run `pixi run pytest test/test_column_grid_trend_regression.py -q` and verify the failure.
- [ ] Keep `_axis_score`'s undirected orthogonal-frame rule. Change its input to terminal group trend; never pass historical orientation, authored orientation, or a block axis. Keep strength/clarity as separate objective evidence.
- [ ] Run focused column-grid and furniture-group tests and commit `fix: compare column grid with terminal group trends`.

### Task 5: Documentation and verification

**Files:** `docs/indoor_layout_evaluation_matrix_architecture_memory.md`, relevant model/skill docs only where stale, and affected tests.

- [ ] Document terminal Analysis geometry as the direction source; document historical/authored orientation as audit-only; preserve single-furniture, group, coherence, and region distinctions.
- [ ] Run `rg -n "authored_orientation|authored orientation|record[.]orientation|group-axis-geometry-angle" features adapters test docs skills` and classify every remaining use.
- [ ] Run the focused suite, then `pixi run pytest -q`, `python -m compileall features adapters test`, and `git diff --check`.
- [ ] Confirm no matrix output, UI, visualization, IFC semantic change, or perceptual weight was added; confirm docstrings/comments; commit `docs: make terminal geometry the trend source of truth`.
