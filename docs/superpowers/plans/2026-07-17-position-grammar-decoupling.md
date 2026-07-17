# Position Grammar Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the public rotation-driven position grammar with a position-only grammar that can be disabled independently.

**Architecture:** Keep the algorithm in `features/position_grammar.py`; keep `features/scene_evaluator.py` as a thin caller that emits rows and overlay evidence. The public `P_position_fit` path must not read furniture rotation, region trend, or column-grid evidence.

**Tech Stack:** Python, pytest, Pixi, notebook visual QA.

---

### Task 1: Red Tests For Decoupling And Disable Switch

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add failing tests**

Add tests that assert:

```python
def test_region_position_grammar_ignores_group_rotation_for_grid_positions():
    """Position score should stay high when only furniture-group rotations vary."""
```

Use `SVG_chaoticsvg.svg` north-table evidence. Expected after implementation:
`position-grammar-type == "grid"` and `position-fit == 1.0`.

```python
def test_position_grammar_can_be_disabled_without_touching_other_rows():
    """Position grammar switch should only disable public position rows."""
```

Call `evaluate_scene(scene, position_grammar_enabled=False)`. Expected:
`P_position_fit` and `P_position_confidence` have `status == "disabled"`;
`region_position_grammar["status"] == "disabled"`;
non-position metrics such as `region_centroid_trend_alignment` still match the enabled run.

```python
def test_region_position_grammar_selects_line_for_non_grid_layout():
    """A straight non-grid layout should not be forced into grid evidence."""
```

Build synthetic furniture groups in Python with three centers on a line and assert selected grammar is `line`.

- [ ] **Step 2: Verify tests fail**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "position_grammar_ignores_group_rotation or can_be_disabled or selects_line_for_non_grid"
```

Expected: failures from current rotation-driven frame and missing switch argument.

### Task 2: Position-Only Grammar Selection

**Files:**
- Modify: `features/position_grammar.py`

- [ ] **Step 1: Replace scope frame selection**

Remove public use of `group-axis-angle`. Add helpers:

```python
def _frame_candidates(scope: dict, coords: list[dict]) -> list[dict]:
    """Return position-only frame candidates for one scope."""
```

Candidate sources:

- authored `position-frame-angle`, if present in scope/group metadata;
- pairwise center directions from `coords`;
- PCA angle from centers;
- `0` and `90`.

- [ ] **Step 2: Score every grammar in every frame**

Change `_scope_position_evidence()` so it projects coords per candidate frame and tests:

```python
_grid_candidate(...)
_line_candidate(...)
_pair_candidate(...)
_cluster_candidate(...)
_unstructured_candidate(...)
```

Select by `(-position-fit, authored frame preference, complexity, frame_priority)`
so a shared authored position frame wins equal-fit ties without overriding worse
fit evidence.

- [ ] **Step 3: Add `cluster` and `unstructured` candidates**

`cluster` uses the centroid slot and can win for compact non-grid groups.
`unstructured` always exists with low-confidence fallback evidence.

- [ ] **Step 4: Verify focused tests pass**

Run the command from Task 1 and fix only this module until green.

### Task 3: Evaluator Switch And Disabled Rows

**Files:**
- Modify: `features/scene_evaluator.py`

- [ ] **Step 1: Add public switch**

Change:

```python
def evaluate_scene(scene: dict) -> dict:
```

to:

```python
def evaluate_scene(scene: dict, *, position_grammar_enabled: bool = True) -> dict:
```

When disabled, use a stable payload:

```python
{"method": "region_level_furniture_group_position_grammar", "status": "disabled", "scopes": [], "items": []}
```

- [ ] **Step 2: Emit disabled rows**

Update `_position_grammar_rows()` so disabled payloads return disabled
`P_position_fit` and `P_position_confidence` rows with no evidence.

- [ ] **Step 3: Keep overlay stable**

Focused overlay should naturally draw no yellow position slots when `items` is empty.

- [ ] **Step 4: Verify tests pass**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "position_grammar_ignores_group_rotation or can_be_disabled or selects_line_for_non_grid or position_grammar"
```

### Task 4: Regression And Visual Verification

**Files:**
- Modify generated outputs under `test/output/position_grammar_proxy_demo.*`

- [ ] **Step 1: Run focused and MVP tests**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "furniture_group or position_grammar or potionNoRotation or position_no_rotation"
pixi run pytest test/test_order_analyzer_mvp.py -q
```

- [ ] **Step 2: Re-execute notebook**

Run:

```powershell
@'
import nbformat
from nbclient import NotebookClient
from pathlib import Path
source = Path("test/position_grammar_proxy_demo.ipynb")
out = Path("test/output/position_grammar_proxy_demo.executed.ipynb")
nb = nbformat.read(source, as_version=4)
NotebookClient(nb, timeout=300, kernel_name="python3").execute()
out.parent.mkdir(parents=True, exist_ok=True)
nbformat.write(nb, out)
print(out)
'@ | pixi run python -
```

- [ ] **Step 3: Export HTML and PNG**

Reuse the existing simple HTML extraction and Playwright screenshot commands for
`test/output/position_grammar_proxy_demo.visual.html` and `.visual.png`.

- [ ] **Step 4: Visual self-check**

Confirm `SVG_chaoticsvg.svg` north table grid no longer shows long
rotation-driven residuals and still shows basemap, group proxy boxes, and group-level slots.

## Self-Review

- Spec coverage: decoupling, no two public systems, disable switch, non-grid grammar, notebook QA are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: public switch is `position_grammar_enabled`; payload key remains `region_position_grammar`.
