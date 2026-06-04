# Affordance Profile Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing `type_id -> AffordanceProfile` defaults a small public registry so users can rely on `type_id` instead of repeating `affordance={...}` in every `TableTemplate`.

**Architecture:** Reuse `features/affordance/profiles.py`. It already has `DEFAULT_AFFORDANCE_PROFILES`, `AffordanceProfile`, and `resolve_affordance_profile(...)`; add minimal public registration helpers and tests. Instance-level `affordance` dict remains the override path.

**Tech Stack:** Python dataclasses, existing `pytest`, existing `pixi`, existing notebooks.

---

## File Structure

- Modify: `features/affordance/profiles.py`
  - Add public `register_affordance_profile(...)` and `register_aisle_profile(...)` helpers.
- Modify: `features/affordance/__init__.py`
  - Export the two registration helpers.
- Modify: `test/test_affordance_aisle.py`
  - Add focused registry tests.
- Modify: `test/simple_3x3_table_affordance_demo.ipynb`
  - Use `type_id` defaults where possible; keep instance override only where demo needs a visible special case.
- Modify: `plan/plan/plan_v1.md`
  - Mark `引入属性驱动可供性档案（affordance profile registry）` complete after implementation.

No new profile class. No YAML/JSON config. No plugin-style registry.

---

### Task 1: Pin Current Resolver Behavior

**Files:**
- Modify: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add tests for default type_id profile resolution**

Add near `test_affordance_profile_supports_edge_specific_depth_override`:

```python
def test_affordance_profile_resolves_type_id_defaults():
    table_profile = resolve_affordance_profile("table.default")
    unknown_profile = resolve_affordance_profile("unknown.type")

    assert isinstance(table_profile, AffordanceProfile)
    assert table_profile.depth_for("right") == pytest.approx(60.0)
    assert unknown_profile.depth_for("right") == pytest.approx(0.0)
```

- [ ] **Step 2: Add test that instance override wins over registry default**

```python
def test_affordance_profile_instance_override_wins_over_registry_default():
    profile = resolve_affordance_profile(
        "table.default",
        {"usable_edges": ("right",), "edge_depth": {"right": 20}},
    )

    assert profile.usable_edges == ("right",)
    assert profile.depth_for("right") == pytest.approx(20.0)
    assert profile.depth_for("left") == pytest.approx(0.0)
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
pixi run pytest test/test_affordance_aisle.py::test_affordance_profile_resolves_type_id_defaults test/test_affordance_aisle.py::test_affordance_profile_instance_override_wins_over_registry_default -q
```

Expected: `2 passed`

If these fail, fix only `resolve_affordance_profile(...)`.

---

### Task 2: Add Minimal Public Registration Helpers

**Files:**
- Modify: `features/affordance/profiles.py`
- Modify: `features/affordance/__init__.py`
- Modify: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add failing tests for public registration**

Add:

```python
def test_register_affordance_profile_adds_type_default():
    register_affordance_profile(
        "table.training",
        usable_edges=("right",),
        edge_depth={"right": 24},
        coverage_threshold=0.75,
    )

    profile = resolve_affordance_profile("table.training")

    assert profile.usable_edges == ("right",)
    assert profile.depth_for("right") == pytest.approx(24.0)
    assert profile.coverage_threshold == pytest.approx(0.75)
```

Add:

```python
def test_register_aisle_profile_adds_type_default():
    register_aisle_profile("table.training", min_width=72, reachability_required=False)

    profile = resolve_aisle_profile("table.training")

    assert profile.min_width == pytest.approx(72.0)
    assert profile.reachability_required is False
```

Update imports at the top of `test/test_affordance_aisle.py`:

```python
from features.affordance import (
    ...,
    register_affordance_profile,
    register_aisle_profile,
    resolve_aisle_profile,
)
```

- [ ] **Step 2: Run tests and verify they fail before implementation**

Run:

```powershell
pixi run pytest test/test_affordance_aisle.py::test_register_affordance_profile_adds_type_default test/test_affordance_aisle.py::test_register_aisle_profile_adds_type_default -q
```

Expected before implementation: `ImportError` or `NameError`.

- [ ] **Step 3: Implement smallest helpers**

In `features/affordance/profiles.py`, add:

```python
def register_affordance_profile(type_id: str, **kwargs: Any) -> AffordanceProfile:
    key = str(type_id).strip()
    if not key:
        raise ValueError("type_id must be non-empty")
    profile = AffordanceProfile(**kwargs)
    DEFAULT_AFFORDANCE_PROFILES[key] = profile
    return profile


def register_aisle_profile(type_id: str, **kwargs: Any) -> AisleProfile:
    key = str(type_id).strip()
    if not key:
        raise ValueError("type_id must be non-empty")
    profile = AisleProfile(**kwargs)
    DEFAULT_AISLE_PROFILES[key] = profile
    return profile
```

Add this comment above the helpers:

```python
# ponytail: process-local registry; add scoped registries only if tests need isolation beyond type_id names.
```

- [ ] **Step 4: Export helpers**

In `features/affordance/__init__.py`, import and add to `__all__`:

```python
register_affordance_profile,
register_aisle_profile,
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
pixi run pytest test/test_affordance_aisle.py::test_register_affordance_profile_adds_type_default test/test_affordance_aisle.py::test_register_aisle_profile_adds_type_default -q
```

Expected: `2 passed`

---

### Task 3: Prove Analyzer Uses Registered Defaults

**Files:**
- Modify: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add analyzer integration test**

Add:

```python
def test_table_template_type_id_uses_registered_affordance_profile_in_report():
    register_affordance_profile(
        "table.training.report",
        usable_edges=("right",),
        edge_depth={"right": 30},
        coverage_threshold=1.0,
    )
    template = TableTemplate(size=(40, 20), type_id="table.training.report")
    grid = TableGrid(1, 1, fill=template)

    report = OrderAnalyzer(
        actual_matrix=grid.to_matrix(),
        ideal_matrix=grid.to_matrix(),
        layout_size=(100, 100),
        fit_to_layout=True,
    ).report(
        features=("positions",),
        include_affordance=True,
        affordance_options={"width": 100, "height": 100, "resolution": 10},
    )

    table = report["affordance"]["objects"]["t11"]
    assert table["coverage_backend"] == "continuous"
    assert table["required_area"] == pytest.approx(600.0)
```

Reason: one table is `40 x 20`; right affordance depth is `30`, so area is `30 * 20 = 600`.

- [ ] **Step 2: Run integration test**

Run:

```powershell
pixi run pytest test/test_affordance_aisle.py::test_table_template_type_id_uses_registered_affordance_profile_in_report -q
```

Expected: `1 passed`

If it fails, inspect `features/analyzer.py` and `features/affordance/geometry.py`; do not add profile logic to `TableTemplate`.

---

### Task 4: Update Notebook to Demonstrate Registry Use

**Files:**
- Modify: `test/simple_3x3_table_affordance_demo.ipynb`

- [ ] **Step 1: Import registration helper**

Change import cell from:

```python
from order_analyzer.features.affordance import resolution_comparison_svg, scene_grid_overlay_svg
```

to:

```python
from order_analyzer.features.affordance import (
    register_affordance_profile,
    resolution_comparison_svg,
    scene_grid_overlay_svg,
)
```

- [ ] **Step 2: Register demo table profile once**

Before `standard_table = TableTemplate(...)`, add:

```python
register_affordance_profile(
    "table.demo",
    usable_edges=("right",),
    edge_depth={"right": 18},
)
```

- [ ] **Step 3: Remove repeated affordance dict from standard table**

Change:

```python
standard_table = TableTemplate(
    size=(64, 44),
    type_id="table.default",
    affordance={"usable_edges": ("right",), "edge_depth": {"right": 18}},
    aisle={"min_width": 80},
)
```

to:

```python
standard_table = TableTemplate(
    size=(64, 44),
    type_id="table.demo",
    aisle={"min_width": 80},
)
```

- [ ] **Step 4: Execute notebook**

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

Expected: `executed test\simple_3x3_table_affordance_demo.ipynb`

Windows pyzmq warning is acceptable.

---

### Task 5: Update Plan Record and Run Regression

**Files:**
- Modify: `plan/plan/plan_v1.md`

- [ ] **Step 1: Mark TODO complete**

Change:

```markdown
- [ ] 引入属性驱动可供性档案（affordance profile registry）
```

to:

```markdown
- [x] 引入属性驱动可供性档案（affordance profile registry）
```

- [ ] **Step 2: Add work record**

Append:

```markdown
### 2026-07-02（Affordance profile registry 完成）

- 完成内容
  - 将现有 `type_id -> AffordanceProfile/AisleProfile` 默认映射固定为公开 registry API。
  - 新增 `register_affordance_profile(...)` 与 `register_aisle_profile(...)`。
  - 保持实例级 `affordance` / `aisle` override 优先级不变。
  - notebook 改为注册 `table.demo` profile，`TableTemplate` 只写 `type_id`。
- 验证
  - 运行 `pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q`
  - 用 `nbformat/nbclient` 执行 `test/simple_3x3_table_affordance_demo.ipynb`
- 当前状态
  - 用户可通过 `type_id` 复用默认可供性规则；复杂外部配置暂不引入。
```

- [ ] **Step 3: Run full regression**

Run:

```powershell
pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Check dirty files**

Run:

```powershell
git status --short --branch
```

Do not stage or commit `test/affordance_aisle_demo.ipynb` unless explicitly requested.

---

## Self-Review Notes

- Existing resolver already covers much of the goal; this plan only makes the registry public and tested.
- No config files, no class hierarchy, no registry object.
- Global process-local mutation is acceptable for tests that use unique `type_id` names.
- Instance overrides continue to be the user-facing escape hatch.
