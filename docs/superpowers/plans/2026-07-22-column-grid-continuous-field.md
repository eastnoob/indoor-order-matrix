# Column Grid Continuous Field Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a continuous, probe-based column-grid field layer that reports region-level angle, secondary angle, support, clarity, and strength without replacing bay-based column-grid evidence.

**Architecture:** Keep SVG as a neutral BIM proxy. Reuse the existing explicit-axis -> branches -> bays scaffold, then derive one additive `column_grid_field_profile` row from region probes and nearby column evidence. The field lives in `features/column_grid.py`, is exposed by `features/scene_evaluator.py`, and is expanded into `ActivityRegion` metric records by `features/room_analysis_model.py`.

**Tech Stack:** Python 3.14, pytest, existing geometry helpers in `features/affordance/models.py`, notebook execution with nbformat/nbclient, existing visual QA pipeline.

---

### Task 1: Implement the field evidence and metric plumbing

**Files:**
- Modify: `features/column_grid.py`
- Modify: `features/scene_evaluator.py`
- Modify: `features/room_analysis_model.py`
- Modify: `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write the failing tests**

Add focused regressions that fail before the field exists:

```python
def test_column_grid_field_profile_reports_angle_strength_and_region_targets():
    scene = {
        "source": "unit",
        "size": (400.0, 300.0),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "columns": [],
        "regions": [
            {
                "id": "region_oblique",
                "role": "region",
                "region": "oblique",
                "group": "oblique",
                "rect": Rect(cx=180, cy=150, width=120, height=80),
                "points": [(120, 120), (240, 140), (220, 200), (100, 180), (120, 120)],
                "metadata": {"axis-angle": "12.0"},
            }
        ],
        "column_axes": [
            {"id": "x0", "role": "column_axis", "rect": Rect(cx=0, cy=0, width=300, height=0), "points": [(0, 0), (300, 0)], "metadata": {"branch-id": "main", "axis-list": "x"}},
            {"id": "x1", "role": "column_axis", "rect": Rect(cx=0, cy=120, width=300, height=0), "points": [(0, 120), (300, 120)], "metadata": {"branch-id": "main", "axis-list": "x"}},
            {"id": "y0", "role": "column_axis", "rect": Rect(cx=0, cy=0, width=0, height=200), "points": [(0, 0), (0, 200)], "metadata": {"branch-id": "main", "axis-list": "y"}},
            {"id": "y1", "role": "column_axis", "rect": Rect(cx=180, cy=0, width=0, height=200), "points": [(180, 0), (180, 200)], "metadata": {"branch-id": "main", "axis-list": "y"}},
        ],
    }

    matrix = evaluate_scene(scene)
    row = next(item for item in matrix["rows"] if item["metric"] == "column_grid_field_profile")
    assert row["status"] == "computed"
    assert row["score"] == row["field_strength"]
    assert 0.0 <= row["field_strength"] <= 1.0
    assert row["field_evidence"]

    model_metrics = matrix["room_analysis_model"]["metric_layer"]["metrics"]
    field_metrics = [item for item in model_metrics if item["metric"] == "column_grid_field_profile"]
    assert field_metrics
    assert {item["target_layer"] for item in field_metrics} == {"ActivityRegion"}
    assert {item["target_id"] for item in field_metrics} == {"region_oblique"}
```

Add one second regression proving mixed evidence lowers strength without forcing a right angle:

```python
def test_column_grid_field_strength_drops_for_mixed_local_evidence():
    matrix = evaluate_scene(load_structured_svg_scene(Path("test/SVG_chaoticsvg.svg")))
    row = next(item for item in matrix["rows"] if item["metric"] == "column_grid_field_profile")
    assert row["status"] == "computed"
    assert 0.0 <= row["field_strength"] <= 1.0
    assert row["field_strength"] < 1.0
    assert row["field_angle"] != 0.0 or row["field_secondary_angle"] != 90.0
```

Add a third regression proving the field stays unavailable when there is no authored column grid:

```python
def test_column_grid_field_profile_is_not_available_without_axes():
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    scene["column_axes"] = []
    matrix = evaluate_scene(scene)
    row = next(item for item in matrix["rows"] if item["metric"] == "column_grid_field_profile")
    assert row["status"] == "not_available"
    assert row["score"] is None
    assert row.get("column_grid_field_evidence") == []
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid_field_profile or room_analysis_model_expands_column_grid_field_profile_targets"
```

Expected: FAIL because `column_grid_field_profile` does not exist yet and the model does not expand it.

- [ ] **Step 3: Implement the field helper and row**

Add one additive helper in `features/column_grid.py`:

```python
def column_grid_field_evidence(scene: dict) -> list[dict]:
    """Build region-level continuous field evidence from existing column-grid support."""
```

Use the existing scaffold:

- seed each region from its inferred `points` when present, otherwise `rect`;
- probe the region at a small deterministic set of points;
- for each probe, score nearby bays and branches by local distance and frame agreement;
- compute:
  - `field_angle` from axial consensus over probe samples;
  - `field_secondary_angle` as `(field_angle + 90.0) % 180.0`;
  - `field_support` from normalized local evidence mass;
  - `field_clarity` from axial vector consensus length;
  - `field_strength = field_support * field_clarity`.
- if the column-grid evidence is missing or the region has no usable support, return a `not_available` row with an empty evidence list rather than inventing a field.

Return one record per region with a shape like:

```python
{
    "region_id": region["id"],
    "field_angle": ...,
    "field_secondary_angle": ...,
    "field_support": ...,
    "field_clarity": ...,
    "field_strength": ...,
    "probe_evidence": [...],
}
```

Then expose one evaluator row:

```python
{
    "view_id": "column_alignment",
    "metric": "column_grid_field_profile",
    "score": field_strength,
    "status": "computed",
    "method": "continuous_column_grid_field_from_region_probes",
    "evidence": [item["region_id"] for item in field_evidence],
    "column_grid_field_evidence": field_evidence,
    "uncertainty": "continuous field probe layer; additive to bay-based local profiles",
}
```

Update `features/room_analysis_model.py` so `column_grid_field_profile` expands to:

```python
_evidence_metric_record(
    row,
    target_layer="ActivityRegion",
    target_id=item["region_id"],
    value=item.get("field_strength"),
    evidence=item,
)
```

Add a short memory note in `docs/indoor_layout_evaluation_matrix_architecture_memory.md` that the field is a continuous additive layer, not a replacement for `C_local_profile`.

- [ ] **Step 4: Run the targeted tests**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid_field_profile or room_analysis_model_expands_column_grid_field_profile_targets or column_grid"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
jj commit -m "feat: add continuous column grid field profile"
```

### Task 2: Refresh notebook visual QA for the new field

**Files:**
- Modify: `features/scene_evaluator.py`
- Modify: `test/column_grid_relation_demo.ipynb`
- Modify: `test/output/column_grid_relation_demo.executed.ipynb`
- Modify: `test/output/column_grid_relation_demo.visual.html`
- Modify: `test/output/column_grid_relation_demo.visual.png`

- [ ] **Step 1: Write the failing visual assertion**

Add a minimal check that the overlay emits a field layer, for example:

```python
def test_overlay_draws_column_grid_field_layer():
    scene = load_structured_svg_scene(Path("test/SVG_oblique.svg"))
    matrix = evaluate_scene(scene)
    svg = scene_metric_overlay_svg(scene, matrix)
    assert 'data-layer="column-grid-field"' in svg
    assert "column_grid_field_profile" in svg
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
pixi run pytest test/test_floorplan_scene_loader.py -q -k "overlay_draws_column_grid_field_layer"
```

Expected: FAIL until the overlay renders the new field line.

- [ ] **Step 3: Render the field overlay**

In `features/scene_evaluator.py`, keep the existing region trend drawing intact and add a second line layer for the field:

```python
for item in column_grid_field.get("column_grid_field_evidence", []):
    # The field line is a visual summary of continuous support, not a new grid.
    x1, y1 = item["center"]
    x2, y2 = item["tip"]
    region_layers.append(
        f'<line data-layer="column-grid-field" data-region="{escape(item["region_id"])}" '
        f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="#ff7f0e" stroke-width="3" opacity="{0.25 + 0.7 * item["field_strength"]:.2f}">'
        f'<title>{escape(item["region_id"])} field={item["field_strength"]:.3f}</title></line>'
    )
```

Keep the length proportional to `field_strength`, not a hard orthogonal snap.

- [ ] **Step 4: Regenerate the notebook outputs**

Run the notebook execution and refresh the visual artifacts:

```bash
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/column_grid_relation_demo.ipynb'; out='test/output/column_grid_relation_demo.executed.ipynb'; nb=nbformat.read(p, as_version=4); NotebookClient(nb, timeout=240, kernel_name='python3').execute(); nbformat.write(nb, out)"
```

Then rebuild the HTML and PNG preview using the existing notebook export flow already used in this repo.

- [ ] **Step 5: Verify the visual result**

Open the refreshed PNG and confirm:

- the field line appears on the same regions as the field row;
- the line length is visibly stronger on coherent regions;
- the field layer does not replace the bay or trend layers.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat: render continuous column field in notebook qa"
```

## Self-Review

### Spec coverage

- Continuous field definition and strength split: Task 1.
- Additive row family and model target mapping: Task 1.
- Overlay rendering and notebook QA: Task 2.
- Preserve existing bay-based behavior: Task 1 tests.

### Placeholder scan

No TBD/TODO placeholders, no abstract "add validation later" steps, and no unnamed helper functions.

### Type consistency

- Row name is `column_grid_field_profile` everywhere.
- Evidence array key is `column_grid_field_evidence`.
- Model target layer is `ActivityRegion`.
- Scalar output is `score = field_strength`.

### Grill-me check

- Is this replacing `C_local_profile`? No, it is additive.
- Is this a full dense field? No, it is probe-based and bounded.
- Does strength come from raw count? No, it comes from support times clarity.
- Is the field allowed to be oblique? Yes, oblique is the point.
