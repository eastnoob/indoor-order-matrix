# Room Analysis Model Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a static `RoomAnalysisModel` that organizes existing scene, region, network, reference, metric, and summary outputs without changing current scoring algorithms.

**Architecture:** Add one adapter-style builder that consumes the neutral scene plus existing `evaluate_scene()` matrix payload. The model is model-facing, but this first pass adapts existing rows to avoid rewriting working algorithms.

**Tech Stack:** Python dict records, existing `features.scene_evaluator`, existing `features.scene_inference`, Pixi pytest, Jupyter notebook demo.

---

## Files

- Create: `features/room_analysis_model.py`
- Modify: `features/scene_evaluator.py`
- Modify: `features/__init__.py`
- Modify: `test/test_floorplan_scene_loader.py`
- Create: `docs/room_analysis_model_interface.md`
- Create: `docs/room_analysis_model_development_standard.md`
- Create: `test/room_analysis_model_demo.ipynb`
- Create on execution: `test/output/room_analysis_model_demo.executed.ipynb`

## Execution Status

2026-07-20 closure:

- Focused RoomAnalysisModel pytest checks passed: `6 passed`.
- Notebook execution succeeded with `nbclient`:
  `test/output/room_analysis_model_demo.executed.ipynb`.
- Full pytest is green after the follow-up fixture/loader reconciliation:
  `284 passed`.
- The follow-up fixed SVG furniture-group container parsing, plain vertical rect
  orientation, and multi-group inferred-region trend input, so this feature can
  be treated as merge-ready once the current jj change is integrated.

## Task 1: Add RoomAnalysisModel Builder

- [x] **Step 1: Write failing model tests**

Add tests to `test/test_floorplan_scene_loader.py`:

```python
def test_evaluate_scene_exports_room_analysis_model_layers():
    scene = load_structured_svg_scene(Path("test/SVG_potionNoRotation.svg"))
    matrix = evaluate_scene(scene)
    model = matrix["room_analysis_model"]

    assert model["contract"] == {"id": "room_analysis_model", "version": 1}
    assert model["base_layer"]["room"]["id"] == "room"
    assert model["object_layer"]["furniture_groups"]
    assert model["region_layer"]["activity_regions"]
    assert "spatial_networks" in model["network_layer"]
    assert "column_grid" in model["reference_layer"]
    assert model["metric_layer"]["metrics"]
    assert model["summary_layer"]["summaries"]


def test_room_analysis_model_maps_position_to_static_scope_not_subject():
    scene = load_structured_svg_scene(Path("test/SVG_potionNoRotation.svg"))
    model = evaluate_scene(scene)["room_analysis_model"]

    position_metrics = [
        item
        for item in model["metric_layer"]["metrics"]
        if item["metric"] == "P_position_fit"
    ]

    assert position_metrics
    assert {item["target_layer"] for item in position_metrics} <= {
        "ActivityRegion",
        "RoomScope",
    }
    assert all("subject_id" not in item for item in position_metrics)


@pytest.mark.parametrize(
    "fixture",
    [
        "test/SVG_baseline.svg",
        "test/SVG_oblique.svg",
        "test/SVG_chaoticsvg.svg",
        "test/SVG_potionNoRotation.svg",
    ],
)
def test_room_analysis_model_builds_for_svg_fixtures(fixture):
    scene = load_structured_svg_scene(Path(fixture))
    model = evaluate_scene(scene)["room_analysis_model"]

    assert set(model) == {
        "contract",
        "source",
        "base_layer",
        "object_layer",
        "region_layer",
        "network_layer",
        "reference_layer",
        "metric_layer",
        "summary_layer",
    }
```

- [x] **Step 2: Run failing tests**

Run:

```bash
pixi run pytest -q test/test_floorplan_scene_loader.py::test_evaluate_scene_exports_room_analysis_model_layers test/test_floorplan_scene_loader.py::test_room_analysis_model_maps_position_to_static_scope_not_subject test/test_floorplan_scene_loader.py::test_room_analysis_model_builds_for_svg_fixtures
```

Expected: fail because `room_analysis_model` does not exist.

- [x] **Step 3: Implement the builder**

Create `features/room_analysis_model.py` with:

```python
from __future__ import annotations

from collections import defaultdict
from statistics import mean


CONTRACT = {"id": "room_analysis_model", "version": 1}


def build_room_analysis_model(scene: dict, matrix: dict) -> dict:
    """Build the static room analysis model from neutral scene and matrix data."""
    metrics = _metric_records(matrix)
    return {
        "contract": dict(CONTRACT),
        "source": matrix.get("source") or scene.get("source"),
        "base_layer": _base_layer(scene),
        "object_layer": _object_layer(scene, matrix),
        "region_layer": _region_layer(scene, matrix),
        "network_layer": _network_layer(matrix),
        "reference_layer": _reference_layer(scene, matrix),
        "metric_layer": {"metrics": metrics},
        "summary_layer": {"summaries": _summary_records(metrics, matrix)},
    }
```

Add small private helpers in the same file:

```python
def _metric_records(matrix: dict) -> list[dict]:
    """Convert existing matrix rows into model-attached metric records."""
    records = []
    for row in matrix.get("rows", []):
        if row.get("metric") in {"P_position_fit", "P_position_confidence"}:
            records.extend(_position_metric_records(row))
            continue
        records.append(_row_metric_record(row))
    return records
```

Important comments:

- row adaptation is temporary compatibility glue;
- SVG-specific fields must not be interpreted here;
- target ids are static model ids, not experiment subjects.

- [x] **Step 4: Wire evaluator and package export**

In `features/scene_evaluator.py`, import and call:

```python
from .room_analysis_model import build_room_analysis_model
```

Build the return dict first, then add:

```python
matrix["room_analysis_model"] = build_room_analysis_model(
    _adapter_scene(scene, inferred_regions=inferred_regions),
    matrix,
)
return matrix
```

In `features/__init__.py`, export `build_room_analysis_model`.

- [x] **Step 5: Run focused tests**

Run:

```bash
pixi run pytest -q test/test_floorplan_scene_loader.py::test_evaluate_scene_exports_room_analysis_model_layers test/test_floorplan_scene_loader.py::test_room_analysis_model_maps_position_to_static_scope_not_subject test/test_floorplan_scene_loader.py::test_room_analysis_model_builds_for_svg_fixtures
```

Expected: pass.

## Task 2: Add Minimal Interface And Development Docs

- [x] **Step 1: Add interface document**

Create `docs/room_analysis_model_interface.md` with:

```markdown
# RoomAnalysisModel Interface

`RoomAnalysisModel` is a static room-layer model returned by
`evaluate_scene(scene)["room_analysis_model"]`.

Top-level keys:

- `base_layer`: room bounds and boundary records.
- `object_layer`: objects, affordance extents, furniture groups, entries, columns.
- `region_layer`: activity regions and room-scope fallback records.
- `network_layer`: spatial networks, gap-path graph, negative-space graph.
- `reference_layer`: boundary semantics, column grid, axes, room references.
- `metric_layer`: metric records attached to static model objects.
- `summary_layer`: room-level summaries derived from metric records.

Metric record minimum:

```text
metric, family, target_layer, target_id, value, status, geometry, anchor,
reference, confidence, method, evidence, uncertainty
```

Rule: `target_id` is a static model object id. It is not an experiment
`subject_id`.
```

- [x] **Step 2: Add development standard**

Create `docs/room_analysis_model_development_standard.md` with:

```markdown
# RoomAnalysisModel Development Standard

When adding a new layout abstraction or metric:

1. Add or reuse a neutral scene/model object first.
2. Attach metrics to `target_layer` and `target_id`.
3. Keep SVG parsing inside the adapter layer.
4. Keep scoring algorithms outside the model builder.
5. Add one focused pytest proving the new output lands in the correct layer.

Do not add experiment fields, BIM-plugin assumptions, or SVG-only semantics to
the model.
```

- [x] **Step 3: Run doc smoke check**

Run:

```bash
rg -n "subject_id|SVG-only|target_layer|RoomAnalysisModel" docs/room_analysis_model_interface.md docs/room_analysis_model_development_standard.md
```

Expected: interface excludes experiment `subject_id`; standard forbids SVG-only semantics.

## Task 3: Add Notebook Demo

- [x] **Step 1: Create notebook**

Create `test/room_analysis_model_demo.ipynb` with cells that:

- load the four `SVG_*.svg` fixtures;
- call `evaluate_scene(scene)`;
- display `scene_metric_overlay_svg(scene, matrix)` for one baseline visual check;
- show layer counts;
- show metric counts by `target_layer`;
- show room summaries.

- [x] **Step 2: Execute notebook**

Run:

```bash
pixi run python -c "from pathlib import Path; import nbformat; from nbclient import NotebookClient; src=Path('test/room_analysis_model_demo.ipynb'); out=Path('test/output/room_analysis_model_demo.executed.ipynb'); out.parent.mkdir(parents=True, exist_ok=True); nb=nbformat.read(src, as_version=4); NotebookClient(nb, timeout=600, kernel_name='python3').execute(); nbformat.write(nb, out); print(out)"
```

Expected: executed notebook is created under `test/output/`.

## Task 4: Final Verification

- [x] **Step 1: Run focused tests**

Run:

```bash
pixi run pytest -q test/test_floorplan_scene_loader.py::test_evaluate_scene_exports_room_analysis_model_layers test/test_floorplan_scene_loader.py::test_room_analysis_model_maps_position_to_static_scope_not_subject test/test_floorplan_scene_loader.py::test_room_analysis_model_builds_for_svg_fixtures
```

Expected: pass.

- [x] **Step 2: Run full pytest**

Run:

```bash
pixi run pytest -q
```

Expected: pass.

Actual closure result: failed with 14 legacy fixture/expectation failures. Do
not merge this change until that separate suite drift is reconciled or the team
accepts a non-green baseline.

Follow-up closure result: the suite drift was reconciled in the next jj change.
Full pytest now reports `284 passed`.

- [x] **Step 3: Check jj status**

Run:

```bash
jj status
```

Expected: changes are limited to the planned feature files and docs.

## Self Review

- Spec coverage: the plan creates the static model, maps current layers, adds summaries, and leaves column-grid/boundary/BIM algorithms untouched.
- Placeholder scan: no implementation placeholder remains.
- Type consistency: public builder is `build_room_analysis_model(scene, matrix)` and evaluator exports `room_analysis_model`.
- Scope control: development standard and interface docs are short; no new scoring theory is added.
