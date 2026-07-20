# Column Grid Layer Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the column-grid layer hierarchy from the design spec: diagnostic object-to-grid, core region-to-local-grid, core inter-region-to-grid, and summary whole-room-to-grid.

**Architecture:** Reuse the existing neutral scene, inference, and column-grid evidence boundaries. `features/column_grid.py` remains the structural evidence builder; `features/scene_evaluator.py` emits matrix rows and policy metadata; `features/room_analysis_model.py` expands row evidence into concrete model metric records. SVG remains only a proxy input.

**Tech Stack:** Python stdlib, existing `Rect` / `Polygon`, existing `evaluate_scene`, `column_grid_evidence`, `pixi run pytest`, `nbformat` / `nbclient` for notebook verification.

---

## File Structure

- Modify `features/scene_evaluator.py`: add column-grid layer policy metadata, inter-region-to-grid rows, and whole-room-to-grid summary rows.
- Modify `features/room_analysis_model.py`: expand column-grid evidence rows to concrete `Furniture`, `ActivityRegion`, `SpatialNetwork`, and `Room` targets.
- Modify `test/test_floorplan_scene_loader.py`: add focused pytest coverage for each layer.
- Modify `test/column_grid_relation_demo.ipynb`: show inferred regions, seed bays, nearby bay expansion, and inter-region evidence for the SVG fixtures.
- Output refreshed notebook artifacts under `test/output/column_grid_relation_demo.*`.

---

### Task 1: Mark Object-To-Grid Rows As Diagnostic By Default

**Files:**
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add the failing test**

Add this test near the existing column alignment tests in `test/test_floorplan_scene_loader.py`:

```python
def test_object_to_grid_rows_are_diagnostic_by_default():
    """Object-to-grid evidence should be optional diagnostics, not main scoring."""
    scene = {
        "source": "unit",
        "size": (200.0, 200.0),
        "objects": [
            {
                "id": "chair_loose",
                "role": "chair",
                "group": "seating",
                "region": "seating",
                "rect": Rect(cx=30, cy=30, width=20, height=20),
                "metadata": {},
            }
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [],
        "columns": [],
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
        ],
    }

    rows = {
        row["metric"]: row
        for row in evaluate_scene(scene)["rows"]
        if row["view_id"] == "column_alignment"
    }

    assert rows["object_column_axis_phase_alignment"]["scoring_role"] == "diagnostic"
    assert rows["object_column_axis_phase_alignment"]["default_enabled"] is False
    assert rows["object_column_bay_local_position_coverage"]["scoring_role"] == "diagnostic"
    assert rows["object_column_bay_local_position_coverage"]["default_enabled"] is False
    excluded = evaluate_scene(scene)["score_matrix"]["excluded_metrics"]
    assert "column_alignment.object_column_axis_phase_alignment" in excluded
    assert "column_alignment.object_column_bay_local_position_coverage" in excluded
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_object_to_grid_rows_are_diagnostic_by_default -q
```

Expected: FAIL because the object-level rows do not expose `scoring_role` and `default_enabled`.

- [ ] **Step 3: Add minimal policy metadata**

In `features/scene_evaluator.py`, inside `_column_alignment_rows()`, add these fields to the `object_column_axis_phase_alignment` row:

```python
"layer": "object_to_grid",
"scoring_role": "diagnostic",
"default_enabled": False,
"policy": "object_to_grid_diagnostic",
```

Add the same fields to the `object_column_bay_local_position_coverage` row.

Do not change the current score calculation.

- [ ] **Step 4: Exclude diagnostic rows from the main score matrix**

In `features/scene_evaluator.py`, update `_score_matrix_excluded_metric()`:

```python
def _score_matrix_excluded_metric(row: dict) -> bool:
    """Return whether a computed row is evidence-only for aggregate scoring."""
    metric = row["metric"]
    return (
        row["view_id"] in {"boundary_connectivity", "uncertainties"}
        or row.get("scoring_role") in {"diagnostic", "summary"}
        or row.get("default_enabled") is False
        or metric.endswith("_count")
        or metric.endswith("_count_mean")
        or "count" in metric
    )
```

- [ ] **Step 5: Run the test again**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_object_to_grid_rows_are_diagnostic_by_default -q
```

Expected: PASS.

- [ ] **Step 6: Check nearby column-grid tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "object_column or column_grid or score_matrix"
```

Expected: PASS for the selected tests.

- [ ] **Step 7: JJ checkpoint**

Run:

```bash
jj describe -m "feat: mark object grid evidence diagnostic"
jj new
```

Expected: the completed change is described, and a new empty change is ready for the next task.

---

### Task 2: Expand Column-Grid Metric Targets In RoomAnalysisModel

**Files:**
- Modify: `features/room_analysis_model.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add the failing model target test**

Add this test near `test_room_analysis_model_maps_position_to_static_scope_not_subject`:

```python
def test_room_analysis_model_expands_column_grid_targets():
    """Column-grid metrics should target concrete model objects, not coarse rows."""
    scene = {
        "source": "unit",
        "size": (200.0, 200.0),
        "objects": [
            {
                "id": "chair_loose",
                "role": "chair",
                "group": "seating",
                "region": "seating",
                "rect": Rect(cx=30, cy=30, width=20, height=20),
                "metadata": {},
            }
        ],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "regions": [
            {
                "id": "region_seating",
                "role": "region",
                "region": "seating",
                "group": "seating",
                "rect": Rect(cx=40, cy=40, width=40, height=40),
                "metadata": {"axis-angle": "0"},
            }
        ],
        "columns": [],
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
        ],
    }

    metrics = evaluate_scene(scene)["room_analysis_model"]["metric_layer"]["metrics"]
    object_metrics = [
        item
        for item in metrics
        if item["metric"] == "object_column_bay_local_position_coverage"
    ]
    region_metrics = [
        item for item in metrics if item["metric"] == "column_grid_C_local_profile"
    ]

    assert object_metrics
    assert {item["target_layer"] for item in object_metrics} == {"Furniture"}
    assert {item["target_id"] for item in object_metrics} == {"chair_loose"}
    assert region_metrics
    assert {item["target_layer"] for item in region_metrics} == {"ActivityRegion"}
    assert {item["target_id"] for item in region_metrics} == {"region_seating"}
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_room_analysis_model_expands_column_grid_targets -q
```

Expected: FAIL because column-grid rows still map through coarse fallback targets.

- [ ] **Step 3: Route column-grid rows to expansion helpers**

In `features/room_analysis_model.py`, update `_metric_records()`:

```python
        if row.get("view_id") == "column_alignment":
            expanded = _column_grid_metric_records(row)
            if expanded:
                records.extend(expanded)
                continue
```

Place this after the position row branch and before `_row_metric_record(row)`.

- [ ] **Step 4: Add `_column_grid_metric_records()`**

Add this helper below `_position_metric_records()`:

```python
def _column_grid_metric_records(row: dict) -> list[dict]:
    """Expand column-grid rows into concrete model-targeted metric records."""
    metric = row.get("metric")
    if metric == "object_column_axis_phase_alignment":
        return [
            _evidence_metric_record(
                row,
                target_layer="Furniture",
                target_id=item["object_id"],
                value=item.get("score"),
                evidence=item,
            )
            for item in row.get("object_axis_phase_evidence", [])
        ]
    if metric == "object_column_bay_local_position_coverage":
        return [
            _evidence_metric_record(
                row,
                target_layer="Furniture",
                target_id=item["object_id"],
                value=item.get("score"),
                evidence=item,
            )
            for item in row.get("object_bay_local_position_evidence", [])
        ]
    if metric == "column_grid_C_local_profile":
        return [
            _evidence_metric_record(
                row,
                target_layer="ActivityRegion",
                target_id=item["region_id"],
                value=item.get("frame_agreement"),
                evidence=item,
            )
            for item in row.get("column_grid_evidence", {}).get("local_profiles", [])
        ]
    if metric == "column_grid_C_global":
        return [
            _evidence_metric_record(
                row,
                target_layer="ActivityRegion",
                target_id=item["region_id"],
                value=item.get("agreement"),
                evidence=item,
            )
            for item in row.get("column_grid_evidence", {}).get("global_relations", [])
        ]
    if metric == "column_grid_inter_region_alignment":
        return [
            _evidence_metric_record(
                row,
                target_layer="SpatialNetwork",
                target_id=item["target_id"],
                value=item.get("score"),
                evidence=item,
            )
            for item in row.get("inter_region_column_grid_evidence", [])
        ]
    return []
```

- [ ] **Step 5: Add `_evidence_metric_record()`**

Add this helper below `_column_grid_metric_records()`:

```python
def _evidence_metric_record(
    row: dict,
    *,
    target_layer: str,
    target_id: str,
    value,
    evidence: dict,
) -> dict:
    """Build one metric record from a row-level evidence item."""
    return {
        "metric": row.get("metric"),
        "family": row.get("view_id"),
        "target_layer": target_layer,
        "target_id": target_id,
        "value": value,
        "status": row.get("status", "computed"),
        "geometry": None,
        "anchor": None,
        "reference": row.get("column_grid_evidence") or row.get("column_axis_evidence"),
        "confidence": row.get("confidence"),
        "method": row.get("method"),
        "evidence": evidence,
        "uncertainty": row.get("uncertainty"),
    }
```

- [ ] **Step 6: Run the model target test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_room_analysis_model_expands_column_grid_targets -q
```

Expected: PASS.

- [ ] **Step 7: Run model tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "room_analysis_model or column_grid"
```

Expected: PASS for the selected tests.

- [ ] **Step 8: JJ checkpoint**

Run:

```bash
jj describe -m "feat: expand column grid model targets"
jj new
```

Expected: the completed change is described, and a new empty change is ready for the next task.

---

### Task 3: Add Inter-Region-To-Grid Evidence Row

**Files:**
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add the failing inter-region test**

Add this test near the column-grid relation tests:

```python
def test_inter_region_to_grid_uses_spatial_network_edges():
    """Inter-region grid evidence should target network edges, not raw SVG paths."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)
    rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "column_alignment"
    }

    row = rows["column_grid_inter_region_alignment"]

    assert row["layer"] == "inter_region_to_grid"
    assert row["status"] == "computed"
    assert row["inter_region_column_grid_evidence"]
    assert all(
        item["target_layer"] == "SpatialNetwork"
        for item in row["inter_region_column_grid_evidence"]
    )
    metrics = matrix["room_analysis_model"]["metric_layer"]["metrics"]
    model_items = [
        item for item in metrics if item["metric"] == "column_grid_inter_region_alignment"
    ]
    assert model_items
    assert {item["target_layer"] for item in model_items} == {"SpatialNetwork"}
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_inter_region_to_grid_uses_spatial_network_edges -q
```

Expected: FAIL because `column_grid_inter_region_alignment` does not exist.

- [ ] **Step 3: Pass spatial networks and gap paths into the row builder**

In `features/scene_evaluator.py`, change:

```python
rows.extend(_column_grid_relation_rows(column_grid))
```

to:

```python
rows.extend(
    _column_grid_relation_rows(
        column_grid,
        spatial_networks,
        inferred_region_gap_paths,
    )
)
```

Change the function signature:

```python
def _column_grid_relation_rows(
    column_grid: dict,
    spatial_networks: list[dict] | None = None,
    gap_paths: list[dict] | None = None,
) -> list[dict]:
    """Return explicit column-grid relation rows for evaluator consumers."""
```

- [ ] **Step 4: Add the row call**

At the end of `_column_grid_relation_rows()`, before `return rows`, append:

```python
    rows.append(
        _inter_region_column_grid_row(
            column_grid,
            spatial_networks or [],
            gap_paths or [],
        )
    )
```

- [ ] **Step 5: Add `_inter_region_column_grid_row()`**

Add this helper near `_column_grid_relation_rows()`:

```python
def _inter_region_column_grid_row(
    column_grid: dict,
    spatial_networks: list[dict],
    gap_paths: list[dict],
) -> dict:
    """Compare inter-region gap directions with the column-grid frame."""
    if column_grid.get("status") != "computed":
        return _not_available(
            "column_alignment",
            "column_grid_inter_region_alignment",
            column_grid.get("reason", "missing column-grid support"),
        )
    frames = [
        branch["trend_frame"]["angle"]
        for branch in column_grid.get("branches", [])
        if branch.get("trend_frame")
    ]
    gap_path_by_id = {path["id"]: path for path in gap_paths}
    inter_networks = [
        network
        for network in spatial_networks
        if network.get("scope") == "inter_region"
    ]
    evidence = []
    for network in inter_networks:
        for edge in network.get("edges", []):
            path = gap_path_by_id.get(edge.get("id"))
            angle = _gap_path_grid_angle(path) if path else None
            if angle is None or not frames:
                continue
            score = max(_axis_pair_score(angle, frame) for frame in frames)
            evidence.append(
                {
                    "target_layer": "SpatialNetwork",
                    "target_id": edge.get("id") or network["id"],
                    "network_id": network["id"],
                    "edge_id": edge.get("id"),
                    "edge_angle": round(angle % 180.0, 4),
                    "gap_path_orientation": path.get("orientation"),
                    "score": round(score, 4),
                    "source": "inter_region_gap_path",
                }
            )
    if not evidence:
        return _not_available(
            "column_alignment",
            "column_grid_inter_region_alignment",
            "no inter-region network edge direction evidence",
        )
    return {
        "view_id": "column_alignment",
        "metric": "column_grid_inter_region_alignment",
        "layer": "inter_region_to_grid",
        "score": round(mean(item["score"] for item in evidence), 4),
        "status": "computed",
        "method": "inter_region_gap_path_orientation_to_column_grid_frame",
        "evidence": [item["target_id"] for item in evidence],
        "inter_region_column_grid_evidence": evidence,
        "uncertainty": "uses existing inferred gap-path orientation; not a new pathfinding or corridor extraction system",
    }
```

Add this small helper below `_inter_region_column_grid_row()`:

```python
def _gap_path_grid_angle(path: dict | None) -> float | None:
    """Return the travel direction represented by an inferred gap band."""
    if not path:
        return None
    orientation = path.get("orientation")
    if orientation == "vertical":
        return 90.0
    if orientation == "horizontal":
        return 0.0
    return None
```

Reuse `_axis_pair_score()` for agreement scoring. Do not add another angle-scoring helper.

- [ ] **Step 6: Run the inter-region test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_inter_region_to_grid_uses_spatial_network_edges -q
```

Expected: PASS.

- [ ] **Step 7: Run column-grid tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid or spatial_network"
```

Expected: PASS for the selected tests.

- [ ] **Step 8: JJ checkpoint**

Run:

```bash
jj describe -m "feat: add inter-region column grid evidence"
jj new
```

Expected: the completed change is described, and a new empty change is ready for the next task.

---

### Task 4: Replace Whole-Room Grid Meaning With A Summary Row

**Files:**
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add the failing summary test**

Add this test near the inter-region test:

```python
def test_whole_room_to_grid_is_summary_only():
    """Whole-room grid relation should summarize lower layers instead of inventing a trend."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)
    rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "column_alignment"
    }

    summary = rows["column_grid_whole_room_summary"]

    assert summary["layer"] == "whole_room_to_grid"
    assert summary["scoring_role"] == "summary"
    assert summary["target_layer"] == "Room"
    assert summary["target_id"] == "room"
    assert "column_grid_C_local_profile" in summary["source_metrics"]
    assert "column_grid_inter_region_alignment" in summary["source_metrics"]
    assert (
        "column_alignment.column_grid_whole_room_summary"
        in matrix["score_matrix"]["excluded_metrics"]
    )
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_whole_room_to_grid_is_summary_only -q
```

Expected: FAIL because `column_grid_whole_room_summary` does not exist.

- [ ] **Step 3: Add the summary append**

At the end of `_column_grid_relation_rows()`, after the inter-region row is appended, add:

```python
    rows.append(_column_grid_whole_room_summary_row(rows))
```

- [ ] **Step 4: Add `_column_grid_whole_room_summary_row()`**

Add this helper near `_inter_region_column_grid_row()`:

```python
def _column_grid_whole_room_summary_row(rows: list[dict]) -> dict:
    """Summarize enabled region and inter-region column-grid evidence."""
    source_metrics = {
        row["metric"]: row
        for row in rows
        if row.get("metric")
        in {"column_grid_C_local_profile", "column_grid_inter_region_alignment"}
    }
    scores = [
        row["score"]
        for row in source_metrics.values()
        if row.get("status") == "computed" and isinstance(row.get("score"), (int, float))
    ]
    if not scores:
        return _not_available(
            "column_alignment",
            "column_grid_whole_room_summary",
            "no enabled region or inter-region column-grid evidence",
        )
    return {
        "view_id": "column_alignment",
        "metric": "column_grid_whole_room_summary",
        "layer": "whole_room_to_grid",
        "scoring_role": "summary",
        "target_layer": "Room",
        "target_id": "room",
        "score": round(mean(scores), 4),
        "status": "computed",
        "method": "summary_mean_of_region_and_inter_region_column_grid_rows",
        "source_metrics": sorted(source_metrics),
        "evidence": sorted(source_metrics),
        "uncertainty": "summary over lower column-grid layers; does not introduce an independent whole-room trend",
    }
```

- [ ] **Step 5: Run the summary test**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py::test_whole_room_to_grid_is_summary_only -q
```

Expected: PASS.

- [ ] **Step 6: Add room-analysis expansion for the summary row**

In `features/room_analysis_model.py`, add this branch to `_column_grid_metric_records()`:

```python
    if metric == "column_grid_whole_room_summary":
        return [
            _evidence_metric_record(
                row,
                target_layer="Room",
                target_id="room",
                value=row.get("score"),
                evidence={
                    "source_metrics": row.get("source_metrics", []),
                    "scoring_role": row.get("scoring_role"),
                },
            )
        ]
```

- [ ] **Step 7: Run model and column-grid tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "room_analysis_model or column_grid"
```

Expected: PASS for the selected tests.

- [ ] **Step 8: JJ checkpoint**

Run:

```bash
jj describe -m "feat: summarize column grid hierarchy"
jj new
```

Expected: the completed change is described, and a new empty change is ready for the next task.

---

### Task 5: Refresh Notebook Visual QA

**Files:**
- Modify: `test/column_grid_relation_demo.ipynb`
- Output: `test/output/column_grid_relation_demo.executed.ipynb`
- Output: `test/output/column_grid_relation_demo.visual.html`
- Output: `test/output/column_grid_relation_demo.visual.png`

- [ ] **Step 1: Update the notebook text**

In `test/column_grid_relation_demo.ipynb`, make the first markdown cell say:

```markdown
# Column Grid Relation Demo

Visual check for explicit axes, generated bays, region seed bays, nearby bay
profiles, inter-region grid evidence, and the no-axis diagnostic case. SVG
files remain proxy inputs; the matrix consumes neutral scene records.
```

- [ ] **Step 2: Update the fixture loop printout**

In the fixture loop cell, print the new hierarchy row statuses:

```python
for path in fixtures:
    scene = load_structured_svg_scene(path)
    matrix = evaluate_scene(scene)
    column_grid = matrix["column_grid"]
    column_rows = {
        row["metric"]: row
        for row in matrix["rows"]
        if row["view_id"] == "column_alignment"
    }
    print(
        path.name,
        "columns=", len(scene.get("columns", [])),
        "axes=", len(scene.get("column_axes", [])),
        "bays=", len(column_grid.get("bays", [])),
        "C_local=", column_rows.get("column_grid_C_local_profile", {}).get("status"),
        "inter_region=", column_rows.get("column_grid_inter_region_alignment", {}).get("status"),
        "whole_room=", column_rows.get("column_grid_whole_room_summary", {}).get("status"),
    )
    display(SVG(data=scene_metric_overlay_svg(scene, matrix)))
```

- [ ] **Step 3: Execute the notebook**

Run:

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/column_grid_relation_demo.ipynb'; out='test/output/column_grid_relation_demo.executed.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, out)"
```

Expected: command exits 0 and writes `test/output/column_grid_relation_demo.executed.ipynb`.

- [ ] **Step 4: Regenerate visual HTML**

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
Path("test/output/column_grid_relation_demo.visual.html").write_text(
    "\n".join(parts),
    encoding="utf-8",
)
'@ | pixi run python -
```

Expected: command exits 0 and writes `test/output/column_grid_relation_demo.visual.html`.

- [ ] **Step 5: Capture the visual PNG**

Run:

```bash
npx playwright screenshot --full-page "file:///D:/PROJECTS/understandOtherPackage/order_analyzer/test/output/column_grid_relation_demo.visual.html" test/output/column_grid_relation_demo.visual.png
```

Expected: command exits 0 and writes `test/output/column_grid_relation_demo.visual.png`.

- [ ] **Step 6: Inspect the PNG**

Open `test/output/column_grid_relation_demo.visual.png`.

Expected visual result:

- physical columns are visible separately from grid axes;
- generated column bays are visible;
- seed bays are visible for region local profiles;
- no-axis case shows columns but no fabricated axes or bays;
- printouts include `C_local`, `inter_region`, and `whole_room` statuses.

- [ ] **Step 7: Final focused verification**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid or room_analysis_model or spatial_network"
```

Expected: PASS for the selected tests.

- [ ] **Step 8: JJ checkpoint**

Run:

```bash
jj describe -m "feat: implement column grid layer hierarchy"
```

Expected: the working copy description updates.

---

## Plan Self-Review

- Spec coverage: object diagnostics, region local profile, inter-region relation, whole-room summary, nearby bay graph, SVG boundary, and room-analysis model targets are each covered by at least one task.
- Scope: this plan does not infer axes from columns and does not create a new pathfinding system.
- Target layers: implementation uses existing `Furniture`, `ActivityRegion`, `SpatialNetwork`, and `Room` model layer names.
- YAGNI: `scale=2` is left out of the first notebook path unless evaluator evidence needs it.
- Verification: every functional task starts with a failing pytest and ends with focused pytest commands; notebook visual QA is isolated in the final task.
