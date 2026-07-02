# Structured SVG Evaluation Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the automatic structured-SVG-to-evaluation-matrix loop for `test/floorplan_order_fixture.svg`.

**Architecture:** Use a small stdlib SVG loader to convert fixture metadata into a neutral scene, then evaluate that scene into stable metric rows. The notebook becomes a thin display layer that calls `load_structured_svg_scene()`, `evaluate_scene()`, and `scene_metric_overlay_svg()`.

**Tech Stack:** Python stdlib `xml.etree.ElementTree`, existing `features.affordance.models.Rect`, existing `OrderAnalyzer` for OCTA-compatible north-table order, `nbformat` / `nbclient` for notebook execution.

---

## Scope

This plan implements the current spec section 26. It does not implement arbitrary image recognition, Rhino UI, or exact SVG path boolean geometry.

## File Structure

- Modify: `test/floorplan_order_fixture.svg`
  - Add `data-role`, `data-group`, `data-region`, and optional `data-order-view` metadata to existing SVG elements.
- Create: `features/scene_loader.py`
  - Parse structured SVG into simple records.
  - Support only fixture-needed shapes: `rect`, `circle`, `path` as boundary/opening metadata, and `g` inheritance.
- Create: `features/scene_evaluator.py`
  - Compute metric rows from the parsed scene.
  - Generate a compact overlay SVG.
- Modify: `features/__init__.py`
  - Export `load_structured_svg_scene`, `evaluate_scene`, and `scene_metric_overlay_svg`.
- Create: `test/test_floorplan_scene_loader.py`
  - Verify loader and evaluator behavior.
- Modify: `test/floorplan_order_matrix_demo.ipynb`
  - Replace manual object declarations with automatic loader/evaluator calls.
- Modify: `docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md`
  - Mark automatic SVG path implemented only after tests and notebook pass.
- Modify: `docs/indoor_layout_evaluation_matrix_task_status.md`
  - Record implementation evidence and remaining gaps honestly.

No commits are required inside this plan because the worktree already has unrelated dirty files. Keep changes scoped and report touched files.

---

### Task 1: Make The Fixture SVG Machine-Readable

**Files:**
- Modify: `test/floorplan_order_fixture.svg`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add failing metadata test**

Create `test/test_floorplan_scene_loader.py` with:

```python
from pathlib import Path
import xml.etree.ElementTree as ET


FIXTURE = Path("test/floorplan_order_fixture.svg")


def _fixture_elements():
    root = ET.parse(FIXTURE).getroot()
    return list(root.iter())


def test_floorplan_fixture_has_structured_metadata():
    elements = _fixture_elements()
    roles = {element.attrib.get("data-role") for element in elements}
    groups = {element.attrib.get("data-group") for element in elements}
    regions = {element.attrib.get("data-region") for element in elements}

    assert "table" in roles
    assert "sofa" in roles
    assert "armchair" in roles
    assert "boundary" in roles
    assert "opening" in roles
    assert "north_tables" in groups
    assert "west_lounge" in groups
    assert "center_lounge" in groups
    assert "east_armchairs" in groups
    assert "north_tables" in regions
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_floorplan_fixture_has_structured_metadata -q
```

Expected: FAIL because the current SVG lacks `data-*` metadata.

- [ ] **Step 3: Add SVG metadata**

Patch `test/floorplan_order_fixture.svg` with the minimum metadata:

```xml
<path id="room_boundary" data-role="boundary" data-boundary-kind="room" class="room" ... />
<path id="left_entry" data-role="opening" data-edge="left" class="door" ... />
<g id="north_tables" data-group="north_tables" data-region="north_tables" data-order-view="north_tables_order">
  <g id="north_table_group_r1_c1" data-group="north_tables" data-region="north_tables">
    <rect id="north_table_r1_c1" data-role="table" data-group="north_tables" data-region="north_tables" class="table" ... />
  </g>
</g>
<g id="west_lounge" data-group="west_lounge" data-region="west_lounge">
  <rect id="west_sofa_1" data-role="sofa" data-group="west_lounge" data-region="west_lounge" class="sofa" ... />
</g>
```

Apply the same pattern to all visible fixture objects needed by the notebook:

- six north tables;
- west sofas and coffee table;
- center sofas and coffee tables;
- east armchairs and coffee table;
- east work table / podium and chair;
- room boundary, internal partition, and door/opening hints;
- candidate region rectangles.

- [ ] **Step 4: Run metadata test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_floorplan_fixture_has_structured_metadata -q
```

Expected: PASS.

---

### Task 2: Implement Structured SVG Loader

**Files:**
- Create: `features/scene_loader.py`
- Modify: `features/__init__.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add failing loader tests**

Append to `test/test_floorplan_scene_loader.py`:

```python
from features.scene_loader import load_structured_svg_scene


def test_load_structured_svg_scene_returns_expected_scene_records():
    scene = load_structured_svg_scene(FIXTURE)

    assert scene["source"] == str(FIXTURE)
    assert scene["size"] == (1000.0, 1000.0)
    assert len(scene["objects"]) >= 20
    assert len(scene["boundaries"]) >= 2
    assert len(scene["entries"]) >= 2
    assert len(scene["regions"]) >= 4

    object_ids = {obj["id"] for obj in scene["objects"]}
    assert "north_table_r1_c1" in object_ids
    assert "west_sofa_1" in object_ids
    assert "east_armchair_left" in object_ids

    north_tables = [obj for obj in scene["objects"] if obj["group"] == "north_tables" and obj["role"] == "table"]
    assert len(north_tables) == 6
    assert all(obj["rect"].width > 0 and obj["rect"].height > 0 for obj in north_tables)


def test_loader_exports_public_api():
    import features

    assert hasattr(features, "load_structured_svg_scene")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'features.scene_loader'`.

- [ ] **Step 3: Create minimal loader**

Create `features/scene_loader.py`:

```python
from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .affordance.models import Rect


SVG_NS = "{http://www.w3.org/2000/svg}"


def load_structured_svg_scene(path: str | Path) -> dict:
    """Load a structured SVG fixture into neutral scene records.

    The loader trusts explicit SVG metadata. It is not image recognition.
    """
    source = Path(path)
    root = ET.parse(source).getroot()
    width, height = _svg_size(root)
    scene = {
        "source": str(source),
        "size": (width, height),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "regions": [],
        "uncertainties": [],
    }
    _walk(root, inherited={}, scene=scene)
    return scene


def _svg_size(root: ET.Element) -> tuple[float, float]:
    view_box = root.attrib.get("viewBox", "")
    parts = [float(part) for part in view_box.replace(",", " ").split() if part]
    if len(parts) == 4:
        return parts[2], parts[3]
    return float(root.attrib.get("width", 0) or 0), float(root.attrib.get("height", 0) or 0)


def _walk(element: ET.Element, *, inherited: dict, scene: dict) -> None:
    meta = _merge_metadata(inherited, element.attrib)
    tag = _tag_name(element.tag)
    if tag == "g":
        transform = _combine_transform(inherited.get("_transform"), element.attrib.get("transform"))
        meta["_transform"] = transform
        for child in element:
            _walk(child, inherited=meta, scene=scene)
        return

    record = _shape_record(tag, element.attrib, meta)
    if record is None:
        return
    role = record.get("role")
    if role == "boundary":
        scene["boundaries"].append(record)
    elif role == "opening":
        scene["entries"].append(record)
    elif role == "region":
        scene["regions"].append(record)
    elif role:
        scene["objects"].append(record)


def _merge_metadata(inherited: dict, attrib: dict) -> dict:
    meta = dict(inherited)
    for key, value in attrib.items():
        if key.startswith("data-") or key == "id":
            meta[key] = value
    return meta


def _shape_record(tag: str, attrib: dict, meta: dict) -> dict | None:
    role = meta.get("data-role")
    if not role:
        return None
    rect = _rect_for_shape(tag, attrib, meta.get("_transform"))
    record = {
        "id": meta.get("id") or attrib.get("id") or role,
        "role": role,
        "group": meta.get("data-group", "global"),
        "region": meta.get("data-region", meta.get("data-group", "global")),
        "order_view": meta.get("data-order-view"),
        "rect": rect,
        "tag": tag,
        "metadata": {key[5:]: value for key, value in meta.items() if key.startswith("data-")},
    }
    return record


def _rect_for_shape(tag: str, attrib: dict, transform: tuple[float, float, float] | None) -> Rect:
    tx, ty, angle = transform or (0.0, 0.0, 0.0)
    if tag == "rect":
        x = float(attrib.get("x", 0) or 0)
        y = float(attrib.get("y", 0) or 0)
        w = float(attrib.get("width", 0) or 0)
        h = float(attrib.get("height", 0) or 0)
        cx, cy = _transform_point(x + w / 2, y + h / 2, tx, ty, angle)
        return Rect(cx=cx, cy=cy, width=w, height=h)
    if tag in {"circle", "ellipse"}:
        cx = float(attrib.get("cx", 0) or 0)
        cy = float(attrib.get("cy", 0) or 0)
        if tag == "circle":
            r = float(attrib.get("r", 0) or 0)
            w = h = 2 * r
        else:
            w = 2 * float(attrib.get("rx", 0) or 0)
            h = 2 * float(attrib.get("ry", 0) or 0)
        cx, cy = _transform_point(cx, cy, tx, ty, angle)
        return Rect(cx=cx, cy=cy, width=w, height=h)
    return Rect(cx=tx, cy=ty, width=0.0, height=0.0)


def _combine_transform(parent: tuple[float, float, float] | None, raw: str | None) -> tuple[float, float, float]:
    tx, ty, angle = parent or (0.0, 0.0, 0.0)
    if not raw:
        return tx, ty, angle
    translate = re.search(r"translate\(([-0-9.]+)(?:[ ,]+([-0-9.]+))?\)", raw)
    if translate:
        tx += float(translate.group(1))
        ty += float(translate.group(2) or 0)
    rotate = re.search(r"rotate\(([-0-9.]+)\)", raw)
    if rotate:
        angle += float(rotate.group(1))
    return tx, ty, angle


def _transform_point(x: float, y: float, tx: float, ty: float, angle: float) -> tuple[float, float]:
    if abs(angle) < 1e-9:
        return x + tx, y + ty
    from math import cos, radians, sin

    theta = radians(angle)
    return x * cos(theta) - y * sin(theta) + tx, x * sin(theta) + y * cos(theta) + ty


def _tag_name(tag: str) -> str:
    return tag[len(SVG_NS):] if tag.startswith(SVG_NS) else tag
```

- [ ] **Step 4: Export loader**

Modify `features/__init__.py`:

```python
from .scene_loader import load_structured_svg_scene

__all__ = [
    "OrderAnalyzer",
    "Table",
    "Chair",
    "Entry",
    "Road",
    "TableTemplate",
    "TableGrid",
    "load_structured_svg_scene",
]
```

- [ ] **Step 5: Run loader tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q
```

Expected: PASS after fixture metadata and loader are aligned.

---

### Task 3: Implement Evaluation Matrix And Overlay

**Files:**
- Create: `features/scene_evaluator.py`
- Modify: `features/__init__.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add failing evaluator tests**

Append to `test/test_floorplan_scene_loader.py`:

```python
from features.scene_evaluator import evaluate_scene, scene_metric_overlay_svg


def test_evaluate_scene_returns_stable_metric_rows():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)
    row_ids = {row["view_id"] for row in matrix["rows"]}

    assert "north_tables_order" in row_ids
    assert "west_lounge_geometry" in row_ids
    assert "center_lounge_geometry" in row_ids
    assert "east_armchair_geometry" in row_ids
    assert "boundary_connectivity" in row_ids
    assert "uncertainties" in row_ids

    north = [row for row in matrix["rows"] if row["view_id"] == "north_tables_order"]
    assert any(row["method"].startswith("octa") for row in north)

    non_octa = [row for row in matrix["rows"] if row["view_id"] in {"west_lounge_geometry", "center_lounge_geometry", "east_armchair_geometry"}]
    assert non_octa
    assert all(not row["method"].startswith("octa") for row in non_octa)


def test_scene_metric_overlay_svg_contains_source_ids_and_metric_layers():
    scene = load_structured_svg_scene(FIXTURE)
    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert "<svg" in svg
    assert "north_table_r1_c1" in svg
    assert "west_lounge" in svg
    assert "data-layer=\"metric-evidence\"" in svg
```

- [ ] **Step 2: Run evaluator tests to verify they fail**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_evaluate_scene_returns_stable_metric_rows -q
```

Expected: FAIL with missing `features.scene_evaluator`.

- [ ] **Step 3: Create minimal evaluator**

Create `features/scene_evaluator.py`:

```python
from __future__ import annotations

import math
from statistics import mean, pstdev

from .analyzer import OrderAnalyzer


def evaluate_scene(scene: dict) -> dict:
    """Evaluate a parsed layout scene into stable metric rows."""
    objects = scene["objects"]
    rows = []
    rows.extend(_north_table_rows(objects))
    rows.extend(_group_geometry_rows(objects))
    rows.append(_boundary_row(scene))
    rows.append(_uncertainty_row(scene))
    return {"source": scene["source"], "rows": rows}


def scene_metric_overlay_svg(scene: dict, matrix: dict) -> str:
    """Draw parsed objects and group boxes as notebook evidence."""
    labels = []
    boxes = []
    for obj in scene["objects"]:
        rect = obj["rect"]
        labels.append(
            f'<text x="{rect.cx:.1f}" y="{rect.cy:.1f}" font-size="12" text-anchor="middle" fill="#111">{obj["id"]}</text>'
        )
    for group in sorted({obj["group"] for obj in scene["objects"]}):
        members = [obj for obj in scene["objects"] if obj["group"] == group]
        if not members:
            continue
        left = min(obj["rect"].left for obj in members)
        right = max(obj["rect"].right for obj in members)
        top = min(obj["rect"].top for obj in members)
        bottom = max(obj["rect"].bottom for obj in members)
        boxes.append(
            f'<rect data-layer="metric-evidence" data-group="{group}" x="{left:.1f}" y="{top:.1f}" width="{right-left:.1f}" height="{bottom-top:.1f}" fill="none" stroke="#d62728" stroke-width="2" stroke-dasharray="8 6" />'
        )
        boxes.append(f'<text x="{left:.1f}" y="{top-6:.1f}" font-size="16" fill="#d62728">{group}</text>')
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">' + "".join(boxes + labels) + "</svg>"


def _north_table_rows(objects: list[dict]) -> list[dict]:
    tables = [obj for obj in objects if obj["group"] == "north_tables" and obj["role"] == "table"]
    if not tables:
        return []
    ordered = sorted(tables, key=lambda obj: (obj["rect"].cy, obj["rect"].cx))
    matrix = []
    for row_index in range(0, len(ordered), 3):
        row = []
        for obj in ordered[row_index:row_index + 3]:
            row.append({"shape": "rect", "attr": "table", "orientation": 0, "id": obj["id"]})
        if row:
            matrix.append(row)
    order = OrderAnalyzer(matrix, matrix).report(features=("shapes", "custom_attr"))["order"] if matrix else 1.0
    centers = [(obj["rect"].cx, obj["rect"].cy) for obj in ordered]
    return [
        {
            "view_id": "north_tables_order",
            "metric": "octa_table_pattern",
            "score": round(order, 4),
            "method": "octa_shapes_custom_attr",
            "evidence": [obj["id"] for obj in ordered],
            "uncertainty": "valid only for comparable repeated table objects",
        },
        {
            "view_id": "north_tables_order",
            "metric": "x_phase_regular",
            "score": round(_position_phase_score(centers[:3], axis="x"), 4),
            "method": "gap_cv_score",
            "evidence": [obj["id"] for obj in ordered[:3]],
            "uncertainty": "checks first repeated table row spacing",
        },
    ]


def _group_geometry_rows(objects: list[dict]) -> list[dict]:
    rows = []
    groups = {
        "west_lounge_geometry": "west_lounge",
        "center_lounge_geometry": "center_lounge",
        "east_armchair_geometry": "east_armchairs",
    }
    for view_id, group in groups.items():
        members = [obj for obj in objects if obj["group"] == group]
        if not members:
            continue
        rows.append(
            {
                "view_id": view_id,
                "metric": "compactness",
                "score": round(_group_compactness(members), 4),
                "method": "occupied_area_over_bbox_area",
                "evidence": [obj["id"] for obj in members],
                "uncertainty": "compactness is descriptive, not automatically good",
            }
        )
    return rows


def _boundary_row(scene: dict) -> dict:
    return {
        "view_id": "boundary_connectivity",
        "metric": "opening_count",
        "score": len(scene["entries"]),
        "method": "structured_svg_opening_count",
        "evidence": [entry["id"] for entry in scene["entries"]],
        "uncertainty": "opening geometry is metadata-level in this slice",
    }


def _uncertainty_row(scene: dict) -> dict:
    return {
        "view_id": "uncertainties",
        "metric": "open_items",
        "score": len(scene.get("uncertainties", [])),
        "method": "uncertainty_log",
        "evidence": scene.get("uncertainties", []),
        "uncertainty": "perceptual assumptions remain explicit",
    }


def _position_phase_score(points: list[tuple[float, float]], axis: str = "x") -> float:
    coords = sorted(point[0] if axis == "x" else point[1] for point in points)
    gaps = [b - a for a, b in zip(coords, coords[1:])]
    return _cv_score(gaps)


def _cv_score(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    avg = mean(values)
    if abs(avg) < 1e-9:
        return 0.0
    return 1 / (1 + pstdev(values) / abs(avg))


def _group_compactness(objects: list[dict]) -> float:
    left = min(obj["rect"].left for obj in objects)
    right = max(obj["rect"].right for obj in objects)
    top = min(obj["rect"].top for obj in objects)
    bottom = max(obj["rect"].bottom for obj in objects)
    hull_area = max(1e-9, (right - left) * (bottom - top))
    occupied = sum(obj["rect"].area for obj in objects)
    return min(1.0, occupied / hull_area)
```

- [ ] **Step 4: Export evaluator API**

Modify `features/__init__.py`:

```python
from .scene_evaluator import evaluate_scene, scene_metric_overlay_svg

__all__ = [
    "OrderAnalyzer",
    "Table",
    "Chair",
    "Entry",
    "Road",
    "TableTemplate",
    "TableGrid",
    "load_structured_svg_scene",
    "evaluate_scene",
    "scene_metric_overlay_svg",
]
```

- [ ] **Step 5: Run evaluator tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q
```

Expected: PASS.

---

### Task 4: Convert Notebook To Automatic Entry

**Files:**
- Modify: `test/floorplan_order_matrix_demo.ipynb`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add notebook source test**

Append to `test/test_floorplan_scene_loader.py`:

```python
import nbformat


def test_floorplan_notebook_uses_automatic_scene_loader():
    nb = nbformat.read("test/floorplan_order_matrix_demo.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in nb.cells)

    assert "load_structured_svg_scene" in source
    assert "evaluate_scene" in source
    assert "scene_metric_overlay_svg" in source
    assert "Manual object declarations" not in source
    assert "objects = [" not in source
```

- [ ] **Step 2: Run notebook source test to verify it fails**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_floorplan_notebook_uses_automatic_scene_loader -q
```

Expected: FAIL because the current notebook has manual object declarations.

- [ ] **Step 3: Replace notebook logic**

Rewrite `test/floorplan_order_matrix_demo.ipynb` cells to this minimal flow:

```python
from pathlib import Path
from IPython.display import SVG, display

fixture_path = Path("test/floorplan_order_fixture.svg")
display(SVG(filename=str(fixture_path)))
```

```python
from features import load_structured_svg_scene, evaluate_scene, scene_metric_overlay_svg

scene = load_structured_svg_scene(fixture_path)
matrix = evaluate_scene(scene)

print("objects:", len(scene["objects"]))
print("groups:", sorted({obj["group"] for obj in scene["objects"]}))
print("metric rows:", len(matrix["rows"]))
```

```python
try:
    import pandas as pd
    display(pd.DataFrame(matrix["rows"]))
except Exception:
    matrix["rows"]
```

```python
display(SVG(data=scene_metric_overlay_svg(scene, matrix)))
```

```python
audit = {
    "automatic_loader": True,
    "manual_fixture_object_table": False,
    "required_views": sorted({row["view_id"] for row in matrix["rows"]}),
}
audit
```

- [ ] **Step 4: Run notebook source test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_floorplan_notebook_uses_automatic_scene_loader -q
```

Expected: PASS.

- [ ] **Step 5: Execute notebook and save outputs**

Run:

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/floorplan_order_matrix_demo.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, p)"
```

Expected: command exits 0 and notebook output contains fixture SVG, metric table, and overlay SVG.

---

### Task 5: Update Audit And Status After Verification

**Files:**
- Modify: `docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md`
- Modify: `docs/indoor_layout_evaluation_matrix_task_status.md`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add documentation status test**

Append to `test/test_floorplan_scene_loader.py`:

```python
def test_audit_records_automatic_svg_path_as_implemented_after_work():
    audit = Path("docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md").read_text(encoding="utf-8")
    status = Path("docs/indoor_layout_evaluation_matrix_task_status.md").read_text(encoding="utf-8")

    assert "Automatic structured 2D plan to evaluation matrix" in audit
    assert "Implemented" in audit
    assert "load_structured_svg_scene" in status
    assert "evaluate_scene(scene)" in status
```

- [ ] **Step 2: Run doc test to verify it fails**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_audit_records_automatic_svg_path_as_implemented_after_work -q
```

Expected: FAIL until docs are updated.

- [ ] **Step 3: Update audit**

In `docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md`, change these rows after code and notebook pass:

```markdown
| Automatic structured 2D plan to evaluation matrix | `features/scene_loader.py`, `features/scene_evaluator.py`, notebook execution | Implemented | extend beyond structured SVG later |
| Avoid manual object table as the main workflow | notebook source test | Implemented | manual constructors remain debug-only |
```

- [ ] **Step 4: Update status**

Append to `docs/indoor_layout_evaluation_matrix_task_status.md`:

```markdown
2026-07-06, structured SVG automation pass:

- Implemented `load_structured_svg_scene()` for the current structured SVG fixture.
- Implemented `evaluate_scene(scene)` and `scene_metric_overlay_svg()`.
- Updated `test/floorplan_order_matrix_demo.ipynb` to use the automatic loader/evaluator path.
- Verified:
  - `pixi run pytest test/test_floorplan_scene_loader.py -q`
  - `pixi run python -c "...nbformat/nbclient execution..."`
- Remaining deferred work:
  - arbitrary PNG/image recognition;
  - Rhino / VisualARQ plugin adapters;
  - perception-calibrated weights.
```

- [ ] **Step 5: Run doc test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_audit_records_automatic_svg_path_as_implemented_after_work -q
```

Expected: PASS.

---

### Task 6: Final Verification Loop

**Files:**
- All files above.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q
```

Expected: PASS.

- [ ] **Step 2: Run existing regression tests**

Run:

```bash
pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q
```

Expected: PASS. If unrelated dirty work causes failures, record exact failures and do not claim full completion.

- [ ] **Step 3: Execute notebook**

Run:

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/floorplan_order_matrix_demo.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, p)"
```

Expected: PASS.

- [ ] **Step 4: Run completion checks**

Run:

```bash
pixi run python - <<'PY'
import nbformat
from features import load_structured_svg_scene, evaluate_scene

scene = load_structured_svg_scene("test/floorplan_order_fixture.svg")
matrix = evaluate_scene(scene)
row_ids = {row["view_id"] for row in matrix["rows"]}
required = {
    "north_tables_order",
    "west_lounge_geometry",
    "center_lounge_geometry",
    "east_armchair_geometry",
    "boundary_connectivity",
    "uncertainties",
}
assert required <= row_ids, required - row_ids
nb = nbformat.read("test/floorplan_order_matrix_demo.ipynb", as_version=4)
source = "\n".join(cell.source for cell in nb.cells)
assert "load_structured_svg_scene" in source
assert "objects = [" not in source
print("structured SVG evaluation loop OK")
PY
```

Expected output:

```text
structured SVG evaluation loop OK
```

- [ ] **Step 5: Grill-me / paperjury style self-check**

Answer these in the final status:

```text
1. Is OCTA used only for comparable repeated objects? Expected: yes, north tables only.
2. Is the notebook still manually typing the object table? Expected: no.
3. Does sampled grid control the new metric matrix? Expected: no sampled grid in this slice.
4. Are Rhino / VisualARQ adapters implemented? Expected: no, documented as deferred.
5. Are arbitrary images supported? Expected: no, structured SVG only.
```

- [ ] **Step 6: Use verification-before-completion**

Before claiming the goal complete, invoke `superpowers:verification-before-completion`, then mark the goal complete only if all required commands passed and docs reflect the result.

---

## Self-Review

Spec coverage:

- Structured SVG metadata: Task 1.
- Automatic loader: Task 2.
- `evaluate_scene(scene)`: Task 3.
- Notebook automatic path: Task 4.
- Audit/status honesty: Task 5.
- Test-fix loop and completion gate: Task 6.

Known scoped deferrals:

- Arbitrary image recognition remains out of scope.
- Rhino / VisualARQ adapters remain design-only until the neutral scene path is stable.
- Exact SVG path geometry is deferred; path/opening records can carry metadata in this slice.
