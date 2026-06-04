# Entry Door Slot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `TableGrid.entry(edge=..., index=..., width=...)` a tested semantic-grid door slot for BFS reachability.

**Architecture:** Reuse existing `Entry`, `EntryBand`, `TableGrid.entry(...)`, `OrderAnalyzer._build_entry_bands()`, and `AisleEvaluator._entry_cells_for_band()`. The door is continuous `EntryBand` geometry; sampled entry cells are only BFS starts/debug output.

**Tech Stack:** Python dataclasses, existing `pytest`, existing `pixi`, existing notebook `test/simple_3x3_table_affordance_demo.ipynb`.

---

## File Structure

- Modify: `test/test_affordance_aisle.py`
  - Add tests that pin semantic door slot behavior.
- Modify if tests expose a gap: `features/analyzer.py`
  - Keep entry intent to `EntryBand` conversion in `_build_entry_bands()`.
- Modify if tests expose a gap: `features/affordance/evaluator.py`
  - Keep filtering occupied door cells in `_entry_cells_for_band()`.
- Modify: `test/simple_3x3_table_affordance_demo.ipynb`
  - Use `grid.entry(edge="left", index=1, width=80, id="main_door")`.
- Modify: `plan/plan/plan_v1.md`
  - Mark the door slot MVP complete after implementation.

No new `Door` class. No internal road-node entry. No room polygon doors.

---

### Task 1: Pin Entry Door Slot Semantics

**Files:**
- Modify: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add a test for `Entry.index` intent preservation**

Add this near `test_entry_intent_and_table_grid_layout_preserve_matrix_compatibility`:

```python
def test_entry_intent_preserves_semantic_door_slot_index():
    entry = Entry(id="main_door", edge="left", index=1, width=80, offset=10)
    intent = entry.to_intent()

    assert intent == {
        "id": "main_door",
        "edge": "left",
        "offset": 10.0,
        "index": 1,
        "width": 80.0,
    }

    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.entry(edge="left", index=1, width=80, offset=10, id="main_door")

    assert grid.to_layout()["entries"] == [intent]
```

- [ ] **Step 2: Run the focused test**

Run:

```powershell
pixi run pytest test/test_affordance_aisle.py::test_entry_intent_preserves_semantic_door_slot_index -q
```

Expected:

```text
1 passed
```

If it fails, fix only `Entry.to_intent()` or `TableGrid.entry(...)`; do not add a new class.

---

### Task 2: Pin EntryBand Geometry for Boundary Door Slots

**Files:**
- Modify: `test/test_affordance_aisle.py`
- Modify if needed: `features/analyzer.py`

- [ ] **Step 1: Add a left-edge indexed door geometry test**

Add this near `test_order_analyzer_layout_input_builds_entry_band_and_report_entries`:

```python
def test_order_analyzer_builds_indexed_left_entry_door_band():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.entry(edge="left", index=1, width=80, id="main_door")

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    band = scene.entry_bands[0]

    assert band.id == "main_door"
    assert band.edge == "left"
    assert band.rect.left == pytest.approx(0)
    assert band.rect.right == pytest.approx(1)
    assert band.rect.top == pytest.approx(110)
    assert band.rect.bottom == pytest.approx(190)
    assert band.metadata["index"] == 1
    assert band.metadata["span"] == pytest.approx((110, 190))
```

- [ ] **Step 2: Add a top-edge indexed door geometry test**

Add:

```python
def test_order_analyzer_builds_indexed_top_entry_door_band():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.entry(edge="top", index=2, width=60, id="top_door")

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    scene = analyzer._build_scene_model()
    band = scene.entry_bands[0]

    assert band.id == "top_door"
    assert band.edge == "top"
    assert band.rect.left == pytest.approx(220)
    assert band.rect.right == pytest.approx(280)
    assert band.rect.top == pytest.approx(0)
    assert band.rect.bottom == pytest.approx(1)
```

- [ ] **Step 3: Run the focused geometry tests**

Run:

```powershell
pixi run pytest test/test_affordance_aisle.py::test_order_analyzer_builds_indexed_left_entry_door_band test/test_affordance_aisle.py::test_order_analyzer_builds_indexed_top_entry_door_band -q
```

Expected:

```text
2 passed
```

- [ ] **Step 4: Minimal implementation if needed**

If the tests fail, update only `OrderAnalyzer._build_entry_bands()` in `features/analyzer.py` so `index` means semantic slot center:

```python
grid_index = int(intent["index"])
span_width = float(intent.get("width", cell_length))
center = (grid_index + 0.5) * cell_length + float(intent.get("offset", 0.0))
start = center - span_width / 2
end = center + span_width / 2
```

Keep the existing clamp:

```python
start = max(0.0, min(axis_length, start))
end = max(0.0, min(axis_length, end))
```

---

### Task 3: Pin BFS Start Cells and Fallback Behavior

**Files:**
- Modify: `test/test_affordance_aisle.py`
- Modify if needed: `features/affordance/evaluator.py`

- [ ] **Step 1: Add a test that indexed doors seed only the selected boundary span**

Add:

```python
def test_indexed_entry_door_marks_only_selected_boundary_start_cells():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))
    grid.entry(edge="left", index=1, width=80, id="main_door")

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    report = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 20},
    )

    entry_rows = [
        row_index
        for row_index, row in enumerate(report["aisle"]["debug"]["entries"])
        if row[0]
    ]

    assert report["aisle"]["entries"] == [
        {"id": "main_door", "edge": "left", "entry_cells": 4, "source": "explicit"}
    ]
    assert entry_rows == [5, 6, 7, 8]
```

- [ ] **Step 2: Add a fallback test**

Add:

```python
def test_missing_entry_keeps_left_boundary_fallback():
    grid = TableGrid(3, 3, fill=TableTemplate(size=(40, 20)))

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    report = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 20},
    )

    assert report["aisle"]["entries"] == [
        {"id": "left-boundary", "edge": "left", "entry_cells": 15, "source": "default"}
    ]
```

- [ ] **Step 3: Add an occupied-door-cell test**

Add:

```python
def test_entry_door_cells_occupied_by_furniture_are_not_bfs_starts():
    template = TableTemplate(size=(100, 100))
    grid = TableGrid(3, 3, fill=template)
    grid.entry(edge="left", index=1, width=80, id="blocked_door")

    analyzer = OrderAnalyzer(
        actual_matrix=grid.to_layout(),
        ideal_matrix=grid.to_layout(),
        layout_size=(300, 300),
        fit_to_layout=True,
    )
    report = analyzer.report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 300, "resolution": 20},
    )

    assert report["aisle"]["entries"][0]["id"] == "blocked_door"
    assert report["aisle"]["entries"][0]["entry_cells"] == 0
    assert sum(sum(row) for row in report["aisle"]["debug"]["entries"]) == 0
```

- [ ] **Step 4: Run the focused BFS tests**

Run:

```powershell
pixi run pytest test/test_affordance_aisle.py::test_indexed_entry_door_marks_only_selected_boundary_start_cells test/test_affordance_aisle.py::test_missing_entry_keeps_left_boundary_fallback test/test_affordance_aisle.py::test_entry_door_cells_occupied_by_furniture_are_not_bfs_starts -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Minimal implementation if needed**

If occupied door cells are not filtered, update only `_entry_cells_for_band()` in `features/affordance/evaluator.py` to keep this existing rule:

```python
if grid.free(row, col):
    cells.append((row, col))
```

Do not add collision scoring for doors.

---

### Task 4: Update Notebook Demo

**Files:**
- Modify: `test/simple_3x3_table_affordance_demo.ipynb`

- [ ] **Step 1: Update the entry declaration cell**

Change:

```python
grid.entry(edge="left", width=120, id="main_entry")
```

to:

```python
grid.entry(edge="left", index=1, width=80, id="main_door")
```

- [ ] **Step 2: Keep the report output**

Ensure this line remains in the notebook:

```python
print("aisle.entries:", report["aisle"].get("entries"))
```

- [ ] **Step 3: Execute and save the notebook**

Run:

```powershell
@'
import nbformat
from nbclient import NotebookClient
from pathlib import Path

path = Path("test/simple_3x3_table_affordance_demo.ipynb")
nb = nbformat.read(path, as_version=4)
NotebookClient(nb, timeout=180, kernel_name="python3").execute()
nbformat.write(nb, path)
print(f"executed {path}")
'@ | pixi run python -
```

Expected:

```text
executed test\simple_3x3_table_affordance_demo.ipynb
```

Windows may print the existing pyzmq event-loop warning; that warning is acceptable.

---

### Task 5: Update Plan Record and Run Regression

**Files:**
- Modify: `plan/plan/plan_v1.md`

- [ ] **Step 1: Add a completed TODO**

In section `6.3 待开始`, add:

```markdown
- [x] 将 Entry 扩展为 semantic grid 边界洞口：支持 edge + index + width 的门洞入口
```

- [ ] **Step 2: Add a work record**

At the end of section `9. 当前工作记录`, add:

```markdown
### 2026-07-02（Entry boundary door slot MVP 完成）

- 完成内容
  - `TableGrid.entry(edge=..., index=..., width=...)` 固定为 semantic grid 边界洞口 API。
  - `OrderAnalyzer` 将 indexed entry intent 转成连续 `EntryBand`。
  - `AisleEvaluator` 只把未被家具占用的 entry sampled cells 作为 BFS 起点。
  - 未声明 entry 时继续使用左边界 fallback。
  - notebook 改为显示 `main_door` 洞口入口。
- 验证
  - 运行 `pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q`
  - 用 `nbformat/nbclient` 执行 `test/simple_3x3_table_affordance_demo.ipynb`
- 当前状态
  - Entry 仍是 reachability 起点，不参与 furniture / affordance / road / clearance 冲突评分。
```

- [ ] **Step 3: Run full regression**

Run:

```powershell
pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 4: Check dirty files before final report**

Run:

```powershell
git status --short --branch
```

Expected:

```text
feature files changed for Entry door slot
existing unrelated dirty notebook may still be present
```

Do not stage or commit `test/affordance_aisle_demo.ipynb` unless the user explicitly asks.

---

## Self-Review Notes

- Spec coverage: covers current `Entry` door slot API, optional fallback, occupied-cell filtering, report output, and notebook visibility.
- No new class: `Door` is intentionally skipped; `Entry` is enough.
- No internal node scope: internal road-node entries and room polygon doors are excluded from this plan.
- Current code may already pass several tests; keep implementation diff minimal and let tests decide.
