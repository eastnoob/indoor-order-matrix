# Column Grid Relation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit-axis column-grid neutral records, bay graph evidence, `C_global`, and `C_local_profile` rows with SVG notebook verification.

**Architecture:** Keep SVG as an adapter. `features/scene_loader.py` reads explicit column and axis records into neutral scene fields; a new small `features/column_grid.py` builds systems, branches, bays, and profile evidence; `features/scene_evaluator.py` consumes those records and draws them. No automatic axis inference from `piler`/columns in this implementation.

**Tech Stack:** Python 3.14 via Pixi, existing `Rect`/`Polygon` geometry models, existing pytest and notebook execution pattern.

---

## File Structure

- Create `features/column_grid.py`: neutral column-grid normalization, explicit-axis bay construction, bay graph expansion, `C_global`, and `C_local_profile` evidence helpers.
- Modify `features/scene_loader.py`: split `column` records into `scene["columns"]`, keep explicit axis records in `scene["column_axes"]`, and recognize the SVG `axis` fixture group as explicit column axes.
- Modify `features/scene_evaluator.py`: call `column_grid_evidence(scene)`, add new metric rows, keep old column rows available during migration, update overlay and adapter handoff to use explicit bay/profile evidence.
- Modify `test/test_floorplan_scene_loader.py`: add focused tests for explicit axis parsing, columns without axes, bay graph, `C_global`, `C_local_profile`, and overlay layers.
- Create `test/column_grid_relation_demo.ipynb`: visual verification for baseline, uneven/chaotic, oblique, and no-axis cases.

---

### Task 1: Loader Separates Columns From Explicit Axes

**Files:**
- Modify: `features/scene_loader.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write the failing loader test**

Add this test near the existing SVG loader tests:

```python
def test_svg_loader_separates_pilers_from_explicit_column_axes():
    """Piler records are columns; explicit SVG axis records are column axes."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    assert "columns" in scene
    assert len(scene["columns"]) >= 6
    assert len(scene["column_axes"]) >= 2
    assert all(item["role"] == "column" for item in scene["columns"])
    assert all(item["role"] == "column_axis" for item in scene["column_axes"])
    assert any(axis["id"].startswith("column_axis") for axis in scene["column_axes"])
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_svg_loader_separates_pilers_from_explicit_column_axes -q
```

Expected: FAIL because `scene["columns"]` does not exist or piler records still share `column_axes`.

- [ ] **Step 3: Implement the minimal loader split**

Change the scene initialization in `load_structured_svg_scene()`:

```python
scene = {
    "source": str(source),
    "size": _svg_size(root),
    "objects": [],
    "boundaries": [],
    "entries": [],
    "paths": [],
    "columns": [],
    "column_axes": [],
    "regions": [],
    "uncertainties": [],
}
```

Change role routing in `_walk()`:

```python
elif role == "column":
    scene["columns"].append(record)
elif role in {"column_axis", "column_grid"}:
    record["role"] = "column_axis"
    record["metadata"]["role"] = "column_axis"
    scene["column_axes"].append(record)
```

Extend `_role_from_id()` conservatively:

```python
if "column_axis" in lowered:
    return "column_axis"
if (
    tag in {"line", "path", "polygon"}
    and lowered.startswith("axis")
):
    return "column_axis"
```

Add this important-step comment before the new `axis` fallback:

```python
# SVG fixtures use an "axis" group for authored grid axes; this is explicit
# fixture metadata, not geometric axis inference from columns.
```

- [ ] **Step 4: Run the loader test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_svg_loader_separates_pilers_from_explicit_column_axes -q
```

Expected: PASS.

- [ ] **Step 5: Run nearby loader tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "load_structured_svg_scene or svg_id_fixture"
```

Expected: PASS after updating old assertions that expected piler records inside `column_axes`.

---

### Task 2: Add Neutral Column-Grid Evidence Builder

**Files:**
- Create: `features/column_grid.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing evidence tests**

Add these imports:

```python
from features.affordance.models import Rect
from features.column_grid import column_grid_evidence
```

Add this test:

```python
def test_column_grid_evidence_builds_bays_from_explicit_axes():
    """Explicit axes should create neutral systems, branches, bays, and graph edges."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "regions": [],
        "columns": [],
        "column_axes": [
            {
                "id": "x0",
                "role": "column_axis",
                "rect": Rect(cx=150, cy=0, width=300, height=0),
                "points": [(0, 0), (300, 0)],
                "metadata": {"grid-id": "main", "branch-id": "orthogonal", "axis-list": "x"},
            },
            {
                "id": "x1",
                "role": "column_axis",
                "rect": Rect(cx=150, cy=100, width=300, height=0),
                "points": [(0, 100), (300, 100)],
                "metadata": {"grid-id": "main", "branch-id": "orthogonal", "axis-list": "x"},
            },
            {
                "id": "y0",
                "role": "column_axis",
                "rect": Rect(cx=0, cy=50, width=0, height=100),
                "points": [(0, 0), (0, 100)],
                "metadata": {"grid-id": "main", "branch-id": "orthogonal", "axis-list": "y"},
            },
            {
                "id": "y1",
                "role": "column_axis",
                "rect": Rect(cx=120, cy=50, width=0, height=100),
                "points": [(120, 0), (120, 100)],
                "metadata": {"grid-id": "main", "branch-id": "orthogonal", "axis-list": "y"},
            },
        ],
    }

    evidence = column_grid_evidence(scene)

    assert evidence["systems"][0]["id"] == "main"
    assert evidence["branches"][0]["id"] == "orthogonal"
    assert len(evidence["bays"]) == 1
    assert evidence["bays"][0]["axis_ids"] == ["x0", "x1", "y0", "y1"]
    assert evidence["bays"][0]["adjacent_bay_ids"] == []
```

Add this test:

```python
def test_column_grid_evidence_does_not_infer_axes_from_columns():
    """Columns alone are evidence, not enough to silently create a grid."""
    scene = {
        "source": "unit",
        "size": (300.0, 300.0),
        "objects": [],
        "regions": [],
        "columns": [
            {"id": "piler_1", "role": "column", "rect": Rect(cx=0, cy=0, width=10, height=10), "metadata": {}},
            {"id": "piler_2", "role": "column", "rect": Rect(cx=100, cy=0, width=10, height=10), "metadata": {}},
        ],
        "column_axes": [],
    }

    evidence = column_grid_evidence(scene)

    assert evidence["systems"] == []
    assert evidence["bays"] == []
    assert evidence["status"] == "not_available"
    assert evidence["reason"] == "missing_explicit_column_axes"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid_evidence"
```

Expected: FAIL because `features.column_grid` does not exist.

- [ ] **Step 3: Create minimal evidence builder**

Create `features/column_grid.py`:

```python
from __future__ import annotations

from itertools import pairwise
from math import atan2, cos, degrees, radians, sin
from statistics import mean

from .affordance.models import Polygon, Rect


def column_grid_evidence(scene: dict) -> dict:
    """Build neutral column-grid evidence from explicit authored axes."""
    axes = [_axis_record(axis) for axis in scene.get("column_axes", [])]
    if not axes:
        return {
            "status": "not_available",
            "reason": "missing_explicit_column_axes",
            "columns": list(scene.get("columns", [])),
            "axes": [],
            "systems": [],
            "branches": [],
            "bays": [],
            "local_profiles": [],
            "global_relations": [],
        }
    branches = _branches(axes)
    bays = [bay for branch in branches for bay in _branch_bays(branch)]
    _attach_bay_adjacency(bays)
    systems = _systems(branches)
    return {
        "status": "computed",
        "reason": "explicit_column_axes",
        "columns": list(scene.get("columns", [])),
        "axes": axes,
        "systems": systems,
        "branches": branches,
        "bays": bays,
        "local_profiles": [],
        "global_relations": [],
    }


def _axis_record(axis: dict) -> dict:
    """Normalize one explicit axis record without inferring it from columns."""
    metadata = axis.get("metadata", {})
    return {
        "id": axis["id"],
        "source_id": axis["id"],
        "system_id": metadata.get("grid-id") or metadata.get("system-id") or "default_grid",
        "branch_id": metadata.get("branch-id") or "default_branch",
        "axis_list": metadata.get("axis-list") or _axis_list_from_angle(_axis_angle(axis)),
        "angle": round(_axis_angle(axis), 4),
        "rect": axis["rect"],
        "points": axis.get("points") or _rect_line_points(axis["rect"]),
        "metadata": metadata,
    }


def _branches(axes: list[dict]) -> list[dict]:
    """Group explicit axes into independent authored branch records."""
    keys = sorted({(axis["system_id"], axis["branch_id"]) for axis in axes})
    branches = []
    for system_id, branch_id in keys:
        branch_axes = [axis for axis in axes if axis["system_id"] == system_id and axis["branch_id"] == branch_id]
        branches.append({
            "id": branch_id,
            "system_id": system_id,
            "axis_ids": [axis["id"] for axis in branch_axes],
            "axes": branch_axes,
            "trend_frame": _frame_from_angles([axis["angle"] for axis in branch_axes]),
        })
    return branches


def _systems(branches: list[dict]) -> list[dict]:
    """Group branches into authored column systems."""
    system_ids = sorted({branch["system_id"] for branch in branches})
    return [
        {
            "id": system_id,
            "branch_ids": [branch["id"] for branch in branches if branch["system_id"] == system_id],
            "global_trend_frame": _frame_from_angles([
                branch["trend_frame"]["angle"]
                for branch in branches
                if branch["system_id"] == system_id
            ]),
            "source": "explicit_column_axes",
        }
        for system_id in system_ids
    ]


def _branch_bays(branch: dict) -> list[dict]:
    """Create rectangular/quad bays from adjacent explicit axes in two axis lists."""
    axes_by_list: dict[str, list[dict]] = {}
    for axis in branch["axes"]:
        axes_by_list.setdefault(axis["axis_list"], []).append(axis)
    if len(axes_by_list) < 2:
        return []
    lists = sorted(axes_by_list)[:2]
    first_axes = sorted(axes_by_list[lists[0]], key=_axis_sort_key)
    second_axes = sorted(axes_by_list[lists[1]], key=_axis_sort_key)
    bays = []
    for a0, a1 in pairwise(first_axes):
        for b0, b1 in pairwise(second_axes):
            polygon = _bay_polygon(a0, a1, b0, b1)
            if polygon is None:
                continue
            bay_id = f"bay_{branch['id']}__{a0['id']}__{a1['id']}__{b0['id']}__{b1['id']}"
            bays.append({
                "id": bay_id,
                "system_id": branch["system_id"],
                "branch_id": branch["id"],
                "axis_ids": [a0["id"], a1["id"], b0["id"], b1["id"]],
                "polygon": polygon,
                "rect": polygon.bounds,
                "angle": branch["trend_frame"]["angle"],
                "adjacent_bay_ids": [],
            })
    return bays


def _attach_bay_adjacency(bays: list[dict]) -> None:
    """Connect bays that share at least two axis ids inside one branch."""
    for bay in bays:
        neighbors = [
            other["id"]
            for other in bays
            if other["id"] != bay["id"]
            and other["branch_id"] == bay["branch_id"]
            and len(set(bay["axis_ids"]) & set(other["axis_ids"])) >= 2
        ]
        bay["adjacent_bay_ids"] = sorted(neighbors)
```

Continue the same file with geometry helpers:

```python
def _axis_angle(axis: dict) -> float:
    """Return authored angle or derive an explicit axis angle from its geometry."""
    raw = axis.get("metadata", {}).get("axis-angle")
    if raw is not None:
        try:
            return float(raw) % 180.0
        except ValueError:
            pass
    points = axis.get("points") or []
    if len(points) >= 2:
        x1, y1 = points[0]
        x2, y2 = points[-1]
        return degrees(atan2(y2 - y1, x2 - x1)) % 180.0
    return 0.0 if axis["rect"].width >= axis["rect"].height else 90.0


def _axis_list_from_angle(angle: float) -> str:
    """Assign a stable list key when SVG omits IFC-like U/V metadata."""
    return "x" if abs(cos(radians(angle * 2))) >= 0.5 else "y"


def _axis_sort_key(axis: dict) -> tuple[float, float, str]:
    """Sort parallel axes by their perpendicular center coordinate."""
    return (axis["rect"].cy, axis["rect"].cx, axis["id"])


def _frame_from_angles(angles: list[float]) -> dict:
    """Average orthogonal frames so 0 and 90 degrees remain equivalent axes."""
    if not angles:
        return {"angle": 0.0, "strength": 0.0}
    x = mean(cos(radians(angle * 4.0)) for angle in angles)
    y = mean(sin(radians(angle * 4.0)) for angle in angles)
    angle = (degrees(atan2(y, x)) / 4.0) % 90.0
    strength = (x * x + y * y) ** 0.5
    return {"angle": round(angle, 4), "strength": round(strength, 4)}


def _rect_line_points(rect: Rect) -> list[tuple[float, float]]:
    """Represent bbox-only axes as a two-point centerline."""
    if rect.width >= rect.height:
        return [(rect.left, rect.cy), (rect.right, rect.cy)]
    return [(rect.cx, rect.top), (rect.cx, rect.bottom)]


def _bay_polygon(a0: dict, a1: dict, b0: dict, b1: dict) -> Polygon | None:
    """Build one bay polygon from two axes in each direction."""
    points = [
        _line_intersection(a0, b0),
        _line_intersection(a0, b1),
        _line_intersection(a1, b1),
        _line_intersection(a1, b0),
    ]
    if any(point is None for point in points):
        return None
    closed = [point for point in points if point is not None]
    return Polygon(points=tuple([*closed, closed[0]]))


def _line_intersection(first: dict, second: dict) -> tuple[float, float] | None:
    """Return the intersection of two explicit axis centerlines."""
    (x1, y1), (x2, y2) = first["points"][0], first["points"][-1]
    (x3, y3), (x4, y4) = second["points"][0], second["points"][-1]
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) <= 1e-9:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den
    return (px, py)
```

- [ ] **Step 4: Run evidence tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid_evidence"
```

Expected: PASS.

---

### Task 3: Compute `C_global` And `C_local_profile`

**Files:**
- Modify: `features/column_grid.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing metric-evidence test**

Add this test:

```python
def test_column_grid_evidence_reports_global_and_local_profiles_for_regions():
    """Furniture regions should relate to explicit global and local column-grid evidence."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    evidence = infer_scene_evidence(scene)
    scene = dict(scene)
    scene["regions"] = evidence["inferred_regions"]

    grid = column_grid_evidence(scene)

    assert grid["global_relations"]
    assert grid["local_profiles"]
    assert all(item["metric"] == "C_global" for item in grid["global_relations"])
    assert all(item["metric"] == "C_local_profile" for item in grid["local_profiles"])
    assert any(item["scale"] == 0 for item in grid["local_profiles"])
    assert any(item["scale"] == "all" for item in grid["local_profiles"])
    assert all("seed_bay_ids" in item for item in grid["local_profiles"])
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_column_grid_evidence_reports_global_and_local_profiles_for_regions -q
```

Expected: FAIL because `global_relations` and `local_profiles` are empty.

- [ ] **Step 3: Add profile generation**

In `column_grid_evidence()`, after bay adjacency:

```python
global_relations = _global_relations(scene.get("regions", []), systems, branches)
local_profiles = _local_profiles(scene.get("regions", []), branches, bays)
```

Return those instead of empty lists:

```python
"local_profiles": local_profiles,
"global_relations": global_relations,
```

Add helpers:

```python
def _global_relations(regions: list[dict], systems: list[dict], branches: list[dict]) -> list[dict]:
    """Compare each region frame to whole-system and branch trend frames."""
    relations = []
    for region in sorted(regions, key=lambda item: item["id"]):
        region_frame = _region_frame(region)
        for system in systems:
            relations.append({
                "metric": "C_global",
                "region_id": region["id"],
                "target_kind": "column_system",
                "target_id": system["id"],
                "agreement": round(_axis_score(region_frame["angle"], system["global_trend_frame"]["angle"]), 4),
                "region_angle": region_frame["angle"],
                "target_angle": system["global_trend_frame"]["angle"],
                "target_strength": system["global_trend_frame"]["strength"],
                "source": "explicit_column_axes",
            })
        for branch in branches:
            relations.append({
                "metric": "C_global",
                "region_id": region["id"],
                "target_kind": "column_branch",
                "target_id": branch["id"],
                "agreement": round(_axis_score(region_frame["angle"], branch["trend_frame"]["angle"]), 4),
                "region_angle": region_frame["angle"],
                "target_angle": branch["trend_frame"]["angle"],
                "target_strength": branch["trend_frame"]["strength"],
                "source": "explicit_column_axes",
            })
    return relations


def _local_profiles(regions: list[dict], branches: list[dict], bays: list[dict]) -> list[dict]:
    """Build bay-graph scale evidence without choosing a perceptual scope."""
    profiles = []
    bays_by_branch = {
        branch["id"]: [bay for bay in bays if bay["branch_id"] == branch["id"]]
        for branch in branches
    }
    for region in sorted(regions, key=lambda item: item["id"]):
        region_frame = _region_frame(region)
        for branch in branches:
            branch_bays = bays_by_branch.get(branch["id"], [])
            seed_ids = _seed_bay_ids(region, branch_bays)
            if not seed_ids:
                continue
            for scale in [0, 1, "all"]:
                included = _expand_bays(seed_ids, branch_bays, scale)
                profiles.append({
                    "metric": "C_local_profile",
                    "region_id": region["id"],
                    "branch_id": branch["id"],
                    "scale": scale,
                    "seed_bay_ids": seed_ids,
                    "included_bay_ids": included,
                    "frame_agreement": round(_axis_score(region_frame["angle"], branch["trend_frame"]["angle"]), 4),
                    "bay_grammar": _bay_grammar(region, branch_bays, included),
                    "source": "explicit_column_axes",
                })
    return profiles
```

Add helper body:

```python
def _region_frame(region: dict) -> dict:
    """Read the already-inferred region frame from neutral metadata."""
    metadata = region.get("metadata", {})
    raw = metadata.get("axis-angle")
    if raw is not None:
        try:
            return {"angle": float(raw) % 180.0, "basis": metadata.get("axis-basis", "metadata_axis")}
        except ValueError:
            pass
    rect = region["rect"]
    return {"angle": 0.0 if rect.width >= rect.height else 90.0, "basis": "bbox_long_axis"}


def _axis_score(a: float, b: float) -> float:
    """Score undirected orthogonal-frame agreement."""
    return abs(cos(radians((a - b) * 2.0)))


def _seed_bay_ids(region: dict, bays: list[dict]) -> list[str]:
    """Pick intersected bays, falling back to nearest bay support."""
    if not bays:
        return []
    overlaps = [
        (bay["id"], _rect_overlap_area(region["rect"], bay["rect"]))
        for bay in bays
    ]
    intersected = sorted(bay_id for bay_id, area in overlaps if area > 1e-9)
    if intersected:
        return intersected
    nearest = min(bays, key=lambda bay: (_rect_gap(region["rect"], bay["rect"]), bay["id"]))
    return [nearest["id"]]


def _expand_bays(seed_ids: list[str], bays: list[dict], scale: int | str) -> list[str]:
    """Expand seed bays by graph distance; `all` returns the complete branch."""
    bay_by_id = {bay["id"]: bay for bay in bays}
    if scale == "all":
        return sorted(bay_by_id)
    seen = set(seed_ids)
    frontier = set(seed_ids)
    for _ in range(int(scale)):
        frontier = {
            neighbor
            for bay_id in frontier
            for neighbor in bay_by_id.get(bay_id, {}).get("adjacent_bay_ids", [])
            if neighbor not in seen
        }
        seen.update(frontier)
    return sorted(seen)


def _bay_grammar(region: dict, bays: list[dict], included_ids: list[str]) -> dict:
    """Report region center in seed bay coordinates as inspectable evidence."""
    selected = [bay for bay in bays if bay["id"] in set(included_ids)]
    if not selected:
        return {"status": "not_available"}
    local_items = []
    for bay in selected:
        local = _local_in_bay(region["rect"].cx, region["rect"].cy, bay)
        if local is not None:
            local_items.append({"bay_id": bay["id"], "local_u": round(local[0], 4), "local_v": round(local[1], 4)})
    return {"status": "computed" if local_items else "not_available", "items": local_items}
```

Add simple geometry helpers:

```python
def _rect_overlap_area(a: Rect, b: Rect) -> float:
    """Return overlap area for axis-aligned envelopes."""
    width = max(0.0, min(a.right, b.right) - max(a.left, b.left))
    height = max(0.0, min(a.bottom, b.bottom) - max(a.top, b.top))
    return width * height


def _rect_gap(a: Rect, b: Rect) -> float:
    """Return Euclidean gap between axis-aligned envelopes."""
    dx = max(0.0, b.left - a.right, a.left - b.right)
    dy = max(0.0, b.top - a.bottom, a.top - b.bottom)
    return (dx * dx + dy * dy) ** 0.5


def _local_in_bay(x: float, y: float, bay: dict) -> tuple[float, float] | None:
    """Map a point into the affine coordinates of a bay polygon."""
    points = list(bay["polygon"].points)
    p0, p1, _, p3 = points[0], points[1], points[2], points[3]
    ux, uy = p1[0] - p0[0], p1[1] - p0[1]
    vx, vy = p3[0] - p0[0], p3[1] - p0[1]
    det = ux * vy - uy * vx
    if abs(det) <= 1e-9:
        return None
    px, py = x - p0[0], y - p0[1]
    return ((px * vy - py * vx) / det, (ux * py - uy * px) / det)
```

- [ ] **Step 4: Run metric-evidence test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_column_grid_evidence_reports_global_and_local_profiles_for_regions -q
```

Expected: PASS.

---

### Task 4: Wire Evidence Into Evaluator Rows And Adapter Handoff

**Files:**
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing evaluator test**

Add this import:

```python
from features.scene_evaluator import evaluate_scene, scene_metric_overlay_svg
```

Add this test:

```python
def test_evaluator_emits_column_grid_relation_rows():
    """Matrix rows should expose explicit-axis C_global and C_local_profile evidence."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}

    assert rows["column_grid_C_global"]["status"] == "computed"
    assert rows["column_grid_C_local_profile"]["status"] == "computed"
    assert rows["column_grid_C_global"]["column_grid_evidence"]["global_relations"]
    assert rows["column_grid_C_local_profile"]["column_grid_evidence"]["local_profiles"]
    assert matrix["adapter_payload"]["column_grid_handoff"]["C_global"]["evidence_count"] > 0
    assert matrix["adapter_payload"]["column_grid_handoff"]["C_local_profile"]["evidence_count"] > 0
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_evaluator_emits_column_grid_relation_rows -q
```

Expected: FAIL because rows are missing.

- [ ] **Step 3: Import and call `column_grid_evidence`**

At the top of `features/scene_evaluator.py`:

```python
from .column_grid import column_grid_evidence
```

In `evaluate_scene()`, after `analysis_scene` is built:

```python
column_grid = column_grid_evidence(analysis_scene)
```

After existing `_column_alignment_rows(analysis_scene)`:

```python
rows.extend(_column_grid_relation_rows(column_grid))
```

Add `column_grid` to the returned matrix:

```python
"column_grid": column_grid,
```

- [ ] **Step 4: Add row helper**

Add near `_column_alignment_rows()`:

```python
def _column_grid_relation_rows(column_grid: dict) -> list[dict]:
    """Expose explicit-axis column-grid relation evidence as matrix rows."""
    if column_grid.get("status") != "computed":
        return [
            _not_available(
                "column_alignment",
                "column_grid_C_global",
                column_grid.get("reason", "missing column-grid support"),
            ),
            _not_available(
                "column_alignment",
                "column_grid_C_local_profile",
                column_grid.get("reason", "missing column-grid support"),
            ),
        ]
    global_relations = column_grid.get("global_relations", [])
    local_profiles = column_grid.get("local_profiles", [])
    rows = []
    rows.append({
        "view_id": "column_alignment",
        "metric": "column_grid_C_global",
        "score": round(mean(item["agreement"] for item in global_relations), 4) if global_relations else None,
        "status": "computed" if global_relations else "not_available",
        "method": "furniture_region_frame_to_explicit_column_system_or_branch_frame",
        "evidence": [item["region_id"] for item in global_relations],
        "column_grid_evidence": {"global_relations": global_relations},
        "uncertainty": "global structural trend evidence only; no final perceptual weight is assigned",
    })
    rows.append({
        "view_id": "column_alignment",
        "metric": "column_grid_C_local_profile",
        "score": round(mean(item["frame_agreement"] for item in local_profiles), 4) if local_profiles else None,
        "status": "computed" if local_profiles else "not_available",
        "method": "furniture_region_to_explicit_column_bay_graph_profile",
        "evidence": [item["region_id"] for item in local_profiles],
        "column_grid_evidence": {"local_profiles": local_profiles},
        "uncertainty": "reports bay-graph profile evidence; S_scope remains an experimental parameter",
    })
    return rows
```

- [ ] **Step 5: Extend adapter handoff minimally**

In `_adapter_column_grid_handoff()`, read new rows:

```python
c_global_row = column_rows.get("column_grid_C_global", {})
c_local_row = column_rows.get("column_grid_C_local_profile", {})
```

Add to the returned dict:

```python
"C_global": {
    "method": c_global_row.get("method"),
    "score": c_global_row.get("score"),
    "evidence_count": len(c_global_row.get("column_grid_evidence", {}).get("global_relations", [])),
    "items": c_global_row.get("column_grid_evidence", {}).get("global_relations", []),
},
"C_local_profile": {
    "method": c_local_row.get("method"),
    "score": c_local_row.get("score"),
    "evidence_count": len(c_local_row.get("column_grid_evidence", {}).get("local_profiles", [])),
    "items": c_local_row.get("column_grid_evidence", {}).get("local_profiles", []),
},
```

- [ ] **Step 6: Run evaluator test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_evaluator_emits_column_grid_relation_rows -q
```

Expected: PASS.

---

### Task 5: Draw Column Grid Evidence In Overlay

**Files:**
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing overlay test**

Add this test:

```python
def test_overlay_draws_column_grid_relation_layers():
    """The visual overlay should expose axes, bays, seed bays, and C evidence."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="column-axis"' in svg
    assert 'data-layer="column-bay"' in svg
    assert 'data-layer="column-seed-bay"' in svg
    assert 'data-layer="column-global-frame"' in svg
    assert 'data-layer="column-local-profile"' in svg
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_overlay_draws_column_grid_relation_layers -q
```

Expected: FAIL because the new profile layers are missing.

- [ ] **Step 3: Draw evidence from `matrix["column_grid"]`**

In `scene_metric_overlay_svg()`, after existing column axis/bay drawing, add:

```python
column_grid = matrix.get("column_grid", {})
seed_bay_ids = {
    bay_id
    for item in column_grid.get("local_profiles", [])
    if item.get("scale") == 0
    for bay_id in item.get("seed_bay_ids", [])
}
for bay in column_grid.get("bays", []):
    if bay["id"] not in seed_bay_ids:
        continue
    polygon = bay.get("polygon")
    if polygon is None:
        continue
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in polygon.points)
    column_layers.append(
        f'<polygon data-layer="column-seed-bay" data-bay="{escape(bay["id"])}" '
        f'points="{points}" fill="#fbbf24" stroke="#d97706" '
        f'stroke-width="2.4" opacity="0.28"><title>{escape(bay["id"])}</title></polygon>'
    )
for item in column_grid.get("global_relations", []):
    region = next((region for region in analysis_scene.get("regions", []) if region["id"] == item["region_id"]), None)
    if not region:
        continue
    x1, y1, x2, y2 = _axis_line(region["rect"], item["target_angle"])
    column_layers.append(
        f'<line data-layer="column-global-frame" data-region="{escape(item["region_id"])}" '
        f'data-target="{escape(item["target_id"])}" x1="{x1:.1f}" y1="{y1:.1f}" '
        f'x2="{x2:.1f}" y2="{y2:.1f}" stroke="#0f766e" stroke-width="2.2" '
        f'opacity="0.62"><title>C_global {item["agreement"]:.4f}</title></line>'
    )
for item in column_grid.get("local_profiles", []):
    if item.get("scale") != 0:
        continue
    region = next((region for region in analysis_scene.get("regions", []) if region["id"] == item["region_id"]), None)
    if not region:
        continue
    column_layers.append(
        f'<circle data-layer="column-local-profile" data-region="{escape(item["region_id"])}" '
        f'data-branch="{escape(item["branch_id"])}" data-scale="0" '
        f'cx="{region["rect"].cx:.1f}" cy="{region["rect"].cy:.1f}" r="6" '
        f'fill="#0f766e" opacity="0.78"><title>C_local_profile scale 0</title></circle>'
    )
```

- [ ] **Step 4: Run overlay test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_overlay_draws_column_grid_relation_layers -q
```

Expected: PASS.

---

### Task 6: Add Visual Notebook

**Files:**
- Create: `test/column_grid_relation_demo.ipynb`
- Output target: `test/output/column_grid_relation_demo.executed.ipynb`

- [ ] **Step 1: Create the notebook**

Create a notebook with these code cells:

```python
from pathlib import Path
from IPython.display import SVG, display

from features.scene_loader import load_structured_svg_scene
from features.scene_evaluator import evaluate_scene, scene_metric_overlay_svg

fixtures = [
    Path("test/SVG_baseline.svg"),
    Path("test/SVG_chaoticsvg.svg"),
    Path("test/SVG_oblique.svg"),
]
```

```python
for path in fixtures:
    scene = load_structured_svg_scene(path)
    matrix = evaluate_scene(scene)
    column_grid = matrix["column_grid"]
    print(
        path.name,
        "columns=", len(scene.get("columns", [])),
        "axes=", len(scene.get("column_axes", [])),
        "bays=", len(column_grid.get("bays", [])),
        "C_global=", len(column_grid.get("global_relations", [])),
        "C_local=", len(column_grid.get("local_profiles", [])),
    )
    display(SVG(data=scene_metric_overlay_svg(scene, matrix)))
```

```python
scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
scene["column_axes"] = []
matrix = evaluate_scene(scene)
print("no-axis status:", matrix["column_grid"]["status"], matrix["column_grid"]["reason"])
display(SVG(data=scene_metric_overlay_svg(scene, matrix)))
```

- [ ] **Step 2: Execute notebook**

Run:

```bash
pixi run jupyter nbconvert --to notebook --execute test/column_grid_relation_demo.ipynb --output-dir test/output --output column_grid_relation_demo.executed.ipynb
```

Expected: command completes and writes `test/output/column_grid_relation_demo.executed.ipynb`.

- [ ] **Step 3: Visually inspect**

Open:

```text
test/output/column_grid_relation_demo.executed.ipynb
```

Expected visual result:

- blue column axes are visible;
- blue bay polygons are visible where explicit axes create cells;
- yellow seed bays appear around inferred furniture regions;
- green `C_global` direction lines and local-profile dots appear;
- the no-axis case prints `not_available missing_explicit_column_axes` and does not fabricate bays.

---

### Task 7: Full Verification And JJ Checkpoint

**Files:**
- All files touched above

- [ ] **Step 1: Run focused tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid or loader_separates or overlay_draws"
```

Expected: PASS.

- [ ] **Step 2: Run existing floorplan tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q
```

Expected: PASS.

- [ ] **Step 3: Run broad project tests**

Run:

```bash
pixi run pytest -q
```

Expected: PASS.

- [ ] **Step 4: Inspect jj diff**

Run:

```bash
jj diff
```

Expected: diff contains only the column-grid implementation, tests, notebook, and the approved spec/plan docs. Existing unrelated working-copy changes must not be reverted.

- [ ] **Step 5: Describe the jj change**

Run:

```bash
jj describe -m "feat: add explicit column-grid relation evidence"
```

Expected: current jj change description is updated.

---

## Self-Review

- Spec coverage: explicit axes, no piler-to-axis inference, neutral records, bay graph scales, `C_global`, `C_local_profile`, SVG-only adapter behavior, no-axis `not_available`, tests, and notebook visual verification are covered.
- Scope control: this plan does not implement final perceived-order scoring, boundary `B`, BIM plugin import, or automatic axis inference.
- Known simplification: the first bay builder uses two axis lists per branch. This covers current SVG fixtures and first IFC-like U/V grids. Curved/triangular `IfcGridAxis` support stays out until real fixtures require it.
