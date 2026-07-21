# Column Grid Local Region Shape Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `C_local_profile` use inferred `ActivityRegion.points` before falling back to world-axis `rect`.

**Architecture:** Keep `features/scene_inference.py` as the owner of region shape and trend. Update only the column-grid consumer so seed-bay lookup and bay grammar use a `Rect | Polygon` region shape. Keep notebook visual QA aligned by drawing inferred region polygons from `points`.

**Tech Stack:** Python stdlib, existing `Rect` / `Polygon`, existing `_polygon_rect_overlap_area`, Pixi pytest, nbclient, Playwright screenshot.

---

## File Structure

- Modify `features/column_grid.py`: add shape helpers and use them in `C_local_profile`.
- Modify `test/test_floorplan_scene_loader.py`: add one focused regression test for polygon-first seed bay and bay grammar.
- Modify `test/column_grid_relation_demo.ipynb`: draw inferred region polygons from `points`.
- Refresh `test/output/column_grid_relation_demo.executed.ipynb`, `.visual.html`, and `.visual.png`.

---

### Task 1: Use Region Shape For `C_local_profile`

**Files:**
- Modify: `features/column_grid.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add the failing test**

Add this test near the existing column-grid tests in `test/test_floorplan_scene_loader.py`:

```python
def test_column_grid_local_profile_uses_region_points_before_world_bbox():
    """C_local should seed bays from inferred region shape, not its world bbox."""
    scene = {
        "source": "unit",
        "size": (220.0, 120.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "columns": [],
        "regions": [
            {
                "id": "oblique_region",
                "role": "region",
                "region": "oblique_region",
                "group": "oblique_region",
                "rect": Rect(cx=100.0, cy=50.0, width=120.0, height=40.0),
                "points": [
                    (20.0, 30.0),
                    (90.0, 30.0),
                    (90.0, 70.0),
                    (20.0, 70.0),
                    (20.0, 30.0),
                ],
                "metadata": {"axis-angle": "0"},
            }
        ],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=0, width=200, height=0),
                "points": [(0, 0), (200, 0)],
                "metadata": {"branch-id": "main", "axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=100, width=200, height=0),
                "points": [(0, 100), (200, 100)],
                "metadata": {"branch-id": "main", "axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {"branch-id": "main", "axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=100, cy=50, width=0, height=100),
                "points": [(100, 0), (100, 100)],
                "metadata": {"branch-id": "main", "axis-list": "y"},
            },
            {
                "id": "y2",
                "role": "column_axis",
                "rect": Rect(cx=200, cy=50, width=0, height=100),
                "points": [(200, 0), (200, 100)],
                "metadata": {"branch-id": "main", "axis-list": "y"},
            },
        ],
    }

    grid = column_grid_evidence(scene)
    scale_zero = [
        item for item in grid["local_profiles"] if item["region_id"] == "oblique_region" and item["scale"] == 0
    ]

    assert len(scale_zero) == 1
    profile = scale_zero[0]
    assert len(profile["seed_bay_ids"]) == 1
    assert "__y0__y1" in profile["seed_bay_ids"][0]
    assert all("__y1__y2" not in bay_id for bay_id in profile["seed_bay_ids"])
    first_bay = next(
        item for item in profile["bay_grammar"] if "__y0__y1" in item["bay_id"]
    )
    second_bay = next(
        item for item in profile["bay_grammar"] if "__y1__y2" in item["bay_id"]
    )
    assert first_bay["overlap_area"] == 2800.0
    assert first_bay["region_area"] == 2800.0
    assert second_bay["overlap_area"] == 0.0
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_column_grid_local_profile_uses_region_points_before_world_bbox -q
```

Expected: FAIL because current `C_local_profile` uses `region["rect"]`, so both bays are seeded and bay grammar area is based on the world bbox.

- [ ] **Step 3: Import the existing polygon overlap helper**

In `features/column_grid.py`, add:

```python
from .affordance.grid_backend import _polygon_rect_overlap_area
```

Keep the existing `Polygon` / `Rect` import.

- [ ] **Step 4: Use region shape in local profiles**

In `_local_profiles()`, replace:

```python
region_rect = region["rect"]
region_frame = _region_frame(region)
```

with:

```python
region_shape = _region_shape(region)
region_frame = _region_frame(region)
```

Then replace:

```python
seed_ids = _seed_bay_ids(region_rect, branch_bays)
...
"bay_grammar": _bay_grammar(region_rect, included_bays),
```

with:

```python
seed_ids = _seed_bay_ids(region_shape, branch_bays)
...
"bay_grammar": _bay_grammar(region_shape, included_bays),
```

- [ ] **Step 5: Add minimal shape helpers**

Add these helpers near `_region_frame()`:

```python
def _region_shape(region: dict) -> Rect | Polygon:
    """Return the inferred region polygon when present, otherwise its bbox."""
    points = [
        (float(x), float(y))
        for x, y in region.get("points", [])
    ]
    unique_points = {(round(x, 9), round(y, 9)) for x, y in points}
    if len(unique_points) >= 3:
        # C_local consumes the activity-region geometry selected by inference;
        # the bbox remains only a compatibility fallback.
        return Polygon(points=tuple(points))
    return region["rect"]


def _shape_bounds(shape: Rect | Polygon) -> Rect:
    """Return axis-aligned bounds for nearest-bay fallback and center checks."""
    return shape.bounds if isinstance(shape, Polygon) else shape


def _shape_area(shape: Rect | Polygon) -> float:
    """Return the area of a region shape regardless of geometry type."""
    return shape.area


def _shape_bay_overlap_area(shape: Rect | Polygon, bay: dict) -> float:
    """Return region-shape overlap area with one generated column bay."""
    if isinstance(shape, Polygon):
        return _polygon_rect_overlap_area(shape, bay["rect"])
    return _rect_overlap_area(shape, bay["rect"])
```

- [ ] **Step 6: Update seed and grammar helpers**

Change signatures and bodies:

```python
def _seed_bay_ids(region_shape: Rect | Polygon, branch_bays: list[dict]) -> list[str]:
    """Choose overlapping seed bays, or the nearest bay when none overlap."""
    overlaps = [
        (bay["id"], _shape_bay_overlap_area(region_shape, bay))
        for bay in branch_bays
    ]
    seed_ids = sorted(bay_id for bay_id, area in overlaps if area > 0.0)
    if seed_ids:
        return seed_ids
    bounds = _shape_bounds(region_shape)
    nearest = min(
        branch_bays,
        key=lambda bay: (_rect_gap(bounds, bay["rect"]), bay["id"]),
    )
    return [nearest["id"]]
```

```python
def _bay_grammar(region_shape: Rect | Polygon, bays: list[dict]) -> list[dict]:
    """Describe how the region shape sits inside included local bays."""
    grammar = []
    region_area = max(_shape_area(region_shape), 1e-9)
    for bay in bays:
        overlap = _shape_bay_overlap_area(region_shape, bay)
        grammar.append(
            {
                "bay_id": bay["id"],
                "overlap_area": round(overlap, 4),
                "region_area": round(region_area, 4),
                "overlap_ratio": round(overlap / region_area, 4),
                "region_center_in_bay": _local_in_bay(region_shape, bay),
            }
        )
    return grammar
```

```python
def _local_in_bay(region_shape: Rect | Polygon, bay: dict) -> bool:
    """Return whether the region shape center falls inside one bay."""
    bounds = _shape_bounds(region_shape)
    polygon = bay.get("polygon")
    if polygon:
        return polygon.contains_point(bounds.cx, bounds.cy)
    return bay["rect"].intersects(Rect(bounds.cx, bounds.cy, 0.0, 0.0))
```

- [ ] **Step 7: Run the focused test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_column_grid_local_profile_uses_region_points_before_world_bbox -q
```

Expected: PASS.

- [ ] **Step 8: Run nearby column-grid tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid or room_analysis_model"
```

Expected: PASS for selected tests.

- [ ] **Step 9: JJ checkpoint**

Run:

```bash
jj describe -m "fix: use region shape for column grid local profile"
jj new
```

Expected: completed implementation change is described and a new empty change is ready.

---

### Task 2: Refresh Column Grid Visual QA

**Files:**
- Modify: `test/column_grid_relation_demo.ipynb`
- Output: `test/output/column_grid_relation_demo.executed.ipynb`
- Output: `test/output/column_grid_relation_demo.visual.html`
- Output: `test/output/column_grid_relation_demo.visual.png`

- [ ] **Step 1: Update the demo overlay to draw region polygons**

In the notebook helper `column_grid_demo_overlay_svg()`, add a small polygon renderer:

```python
def polygon_svg(points, *, y_offset=margin_top, **attrs):
    """Render a closed polygon with escaped SVG attributes."""
    attr_text = " ".join(f'{name}="{escape(str(value))}"' for name, value in attrs.items())
    point_text = " ".join(f"{x:.1f},{y + y_offset:.1f}" for x, y in points)
    return f'<polygon points="{point_text}" {attr_text}/>'
```

Then change inferred-region drawing from unconditional `rect_svg(rect, ...)` to:

```python
points = region.get("points") or []
if len({(round(x, 9), round(y, 9)) for x, y in points}) >= 3:
    layers.append(
        polygon_svg(
            points,
            fill="#10b981",
            stroke="#047857",
            **{"stroke-width": 2.2, "stroke-dasharray": "8 5", "opacity": 0.17},
        )
    )
else:
    layers.append(
        rect_svg(
            rect,
            fill="#10b981",
            stroke="#047857",
            **{"stroke-width": 2.2, "stroke-dasharray": "8 5", "opacity": 0.17},
        )
    )
```

- [ ] **Step 2: Execute the notebook**

Run:

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/column_grid_relation_demo.ipynb'; out='test/output/column_grid_relation_demo.executed.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=180, kernel_name='python3').execute(); nbformat.write(nb, out)"
```

Expected: command exits 0 and writes the executed notebook. The Windows zmq/Tornado warning is acceptable.

- [ ] **Step 3: Regenerate visual HTML**

Run:

```powershell
@'
import html
from pathlib import Path
import nbformat

nb = nbformat.read("test/output/column_grid_relation_demo.executed.ipynb", as_version=4)
parts = [
    '<!doctype html><meta charset="utf-8"><title>Column Grid Relation Demo</title>',
    '<style>body{font-family:Arial,sans-serif;margin:24px;background:#f8fafc;color:#0f172a} .cell{margin:0 0 28px} pre{white-space:pre-wrap;background:#e2e8f0;padding:10px;border-radius:6px} svg{max-width:100%;height:auto;background:white;border:1px solid #cbd5e1;margin-top:8px}</style>',
]
for cell in nb.cells:
    if cell.cell_type == "markdown":
        title = html.escape(cell.source.splitlines()[0].lstrip("# "))
        parts.append(f'<section class="cell"><h2>{title}</h2></section>')
    elif cell.get("outputs"):
        parts.append('<section class="cell">')
        for output in cell.outputs:
            if output.output_type == "stream":
                parts.append(f"<pre>{html.escape(output.text)}</pre>")
            data = output.get("data", {})
            if "image/svg+xml" in data:
                svg = data["image/svg+xml"]
                parts.append(svg if isinstance(svg, str) else "".join(svg))
        parts.append("</section>")
Path("test/output/column_grid_relation_demo.visual.html").write_text("\n".join(parts), encoding="utf-8")
'@ | pixi run python -
```

Expected: command exits 0 and writes `.visual.html`.

- [ ] **Step 4: Capture the visual PNG**

Run:

```bash
npx playwright screenshot --full-page "file:///D:/PROJECTS/understandOtherPackage/order_analyzer/test/output/column_grid_relation_demo.visual.html" test/output/column_grid_relation_demo.visual.png
```

Expected: command exits 0 and writes `.visual.png`.

- [ ] **Step 5: Inspect visual output**

Open `test/output/column_grid_relation_demo.visual.png`.

Expected:

- furniture geometry remains gray;
- inferred regions are green polygons from `points`, not world bboxes;
- region trend axes remain orange;
- column axes, columns, and bays remain blue;
- no-axis case still shows no fabricated axes or bays.

- [ ] **Step 6: JJ checkpoint**

Run:

```bash
jj describe -m "test: refresh column grid local shape visual qa"
```

Expected: current notebook/output change is described.

---

## Plan Self-Review

- Spec coverage: Task 1 covers polygon-first `C_local_profile`; Task 2 covers visual polygon drawing.
- Scope: `C_global` and `inter_region` are intentionally unchanged.
- No placeholders: every code step includes concrete snippets and commands.
- Type consistency: `Rect | Polygon` is used consistently for region shape helpers.
- YAGNI: no Shapely dependency, no polygon path routing, no new model layer.

