# Floorplan Order Matrix Notebook Test Plan

## Purpose

Create and maintain a notebook-level validation path for the indoor layout evaluation matrix using the current schematic floor plan:

- fixture SVG: `test/floorplan_order_fixture.svg`
- executable notebook: `test/floorplan_order_matrix_demo.ipynb`

The notebook is not an automatic image-recognition demo. It is a controlled 2D technical fixture: object meaning comes from structured SVG `data-*` metadata, then the notebook calls the loader/evaluator path directly. Manual object declarations are now debug fallback only.

Current status:

- `test/floorplan_order_matrix_demo.ipynb` exists.
- It has been executed and saved with outputs.
- It calls `load_structured_svg_scene()`, `evaluate_scene()`, and `scene_metric_overlay_svg()`.
- Verification found 7 cells, 2 SVG outputs, and 2 HTML table outputs before the evaluator-family expansion; rerun the notebook after evaluator changes before reporting fresh cell/output counts.

## Fixture Interpretation

The SVG contains:

- room boundary and door hints;
- north repeated table-chair groups;
- north small table;
- west lower lounge: two sofas and one coffee table;
- center lower lounge: two sofa groups;
- east lower area: small armchairs and one coffee table;
- east middle work/podium-like table;
- internal boundary/partition hints;
- candidate region outlines;
- soft circulation polygon for later path testing.

## Notebook Cells

### 1. Display Fixture

Input:

- `test/floorplan_order_fixture.svg`

Output:

- rendered SVG.

Purpose:

- confirm the test scene before any metric is computed.

```python
from IPython.display import SVG, display
display(SVG(filename="test/floorplan_order_fixture.svg"))
```

### 2. Load Structured Scene

Input:

- `test/floorplan_order_fixture.svg` with `data-role`, `data-group`, and `data-region` metadata.

Output:

- `scene["objects"]`, `scene["boundaries"]`, `scene["regions"]`, `scene["entries"]`, `scene["paths"]`.

Required first objects:

- six north table-chair groups;
- `north_small_table`;
- `west_lounge` sofas/table;
- `center_lounge` two sofa groups;
- `east_armchairs`;
- `east_work`;
- room boundary;
- bottom and right entries;
- internal partition boundary.

Implementation note:

- Use `features.load_structured_svg_scene()` as the main path.
- Do not manually type the main fixture object table in the notebook.
- Do not add a new geometry library.

### 3. Build Metric Views

Output:

```python
views = [
    {"id": "north_tables_order", "mode": "octa_grid"},
    {"id": "west_lounge_geometry", "mode": "group_geometry"},
    {"id": "center_lounge_geometry", "mode": "group_geometry"},
    {"id": "east_armchair_geometry", "mode": "group_geometry"},
    {"id": "boundary_summary", "mode": "boundary"},
    {"id": "circulation_placeholder", "mode": "path_graph"},
]
```

Rules:

- OCTA view only applies where elements are comparable: first target is the north repeated table-chair array.
- Sofa/armchair areas use geometry/group metrics, not a forced OCTA grid.
- Path view starts as a placeholder with manually drawn negative-space geometry.

### 4. Compute First Metric Matrix

Output columns:

```text
view_id
metric_family
score
raw_value
method
confidence
evidence
uncertainty
```

First metric rows:

- `north_tables_order.shape_order`
- `north_tables_order.orientation_order`
- `north_tables_order.position_phase`
- `west_lounge_geometry.enclosure`
- `west_lounge_geometry.centering`
- `center_lounge_geometry.parallelism`
- `east_armchair_geometry.group_compactness`
- `boundary_summary.walk_block_balance`
- `boundary_summary.visibility_block_balance`
- `circulation_placeholder.entry_to_region_reachability`

Do not overfit these names. The notebook should make weak metrics visible so they can be changed.

### 5. Visualize Evidence

SVG overlay layers:

- object ids;
- group outlines;
- candidate region outlines;
- local axes;
- path placeholder;
- metric labels.

Purpose:

- the metric table must be traceable back to visible geometry.

### 6. Uncertainty Log

Notebook must print a small table:

```text
issue
affected_metric
current_handling
needs_paper_search
needs_perception_test
```

Initial uncertainty rows:

- when a gap becomes a path;
- when two furniture clusters become one region;
- how strong rug/material boundary cues should be;
- whether sofa order should be judged by enclosure, symmetry, facing, or all three;
- how to align irregular regions with irregular column grids.

## Acceptance Criteria

- The notebook displays `test/floorplan_order_fixture.svg`.
- The notebook loads all major fixture areas through `load_structured_svg_scene()`.
- The notebook outputs a metric matrix table.
- The notebook separates OCTA-compatible order from geometry/group metrics.
- The notebook includes an uncertainty table.
- The notebook does not require automatic PNG/image recognition.
- The notebook does not treat sampled grid cells as the source of truth.

## Explicit Non-Goals

- No automatic image recognition.
- No BIM import.
- No complete path skeletonization.
- No full new evaluator framework before the first notebook validates the metric rows.
- No claim that sofa, podium, and table array order are comparable under one global grid.

## Next Implementation Slice

1. Create `test/floorplan_order_matrix_demo.ipynb`.
2. Display the fixture SVG.
3. Manually declare fixture objects using existing geometry primitives.
4. Build the metric matrix as a small list of dictionaries.
5. Render one overlay SVG with object/group/region ids.
6. Save executed notebook output.

## Executable Notebook Skeleton

The first notebook should be implementable with only standard Python plus existing project imports.

### Minimal Imports

```python
import math
from statistics import mean, pstdev
from IPython.display import SVG, display

from features.affordance.models import Rect, Polygon
```

### Debug-Only Fixture Object Declaration

The notebook no longer uses this as the main path. Keep direct dictionaries only as a debug fallback if the structured SVG loader fails.

```python
debug_fixture_records = [
    {"id": "north_table_r1_c1", "type": "table", "group": "north_tables", "rect": Rect(185, 215, 150, 56), "orientation": 0},
    {"id": "north_table_r1_c2", "type": "table", "group": "north_tables", "rect": Rect(500, 215, 150, 56), "orientation": 0},
    {"id": "north_table_r1_c3", "type": "table", "group": "north_tables", "rect": Rect(815, 215, 150, 56), "orientation": 0},
    {"id": "north_table_r2_c1", "type": "table", "group": "north_tables", "rect": Rect(185, 465, 150, 56), "orientation": 0},
    {"id": "north_table_r2_c2", "type": "table", "group": "north_tables", "rect": Rect(500, 465, 150, 56), "orientation": 0},
    {"id": "north_table_r2_c3", "type": "table", "group": "north_tables", "rect": Rect(815, 465, 150, 56), "orientation": 0},
    {"id": "west_sofa_1", "type": "sofa", "group": "west_lounge", "rect": Rect(79, 722.5, 48, 145), "orientation": 90},
    {"id": "west_sofa_2", "type": "sofa", "group": "west_lounge", "rect": Rect(170, 867.5, 170, 45), "orientation": 0},
    {"id": "west_coffee_table", "type": "coffee_table", "group": "west_lounge", "rect": Rect(177.5, 775, 55, 80), "orientation": 90},
    {"id": "center_sofa_1", "type": "sofa", "group": "center_lounge_upper", "rect": Rect(577.5, 747.5, 145, 55), "orientation": 0},
    {"id": "center_table_1", "type": "coffee_table", "group": "center_lounge_upper", "rect": Rect(585, 679, 80, 38), "orientation": 0},
    {"id": "center_sofa_2", "type": "sofa", "group": "center_lounge_lower", "rect": Rect(577.5, 872.5, 155, 55), "orientation": 0},
    {"id": "center_table_2", "type": "coffee_table", "group": "center_lounge_lower", "rect": Rect(585, 809, 80, 38), "orientation": 0},
    {"id": "east_armchair_left", "type": "armchair", "group": "east_armchairs", "rect": Rect(712.5, 877.5, 55, 55), "orientation": 0},
    {"id": "east_coffee_table", "type": "coffee_table", "group": "east_armchairs", "rect": Rect(795, 875, 64, 64), "orientation": 0},
    {"id": "east_armchair_right", "type": "armchair", "group": "east_armchairs", "rect": Rect(902.5, 877.5, 55, 55), "orientation": 0},
    {"id": "east_work_table", "type": "work_table", "group": "east_work", "rect": Rect(862.5, 711, 145, 62), "orientation": 0},
    {"id": "north_small_table", "type": "table", "group": "north_wall", "rect": Rect(447.5, 82.5, 45, 55), "orientation": 0},
]
```

### Minimal Metric Helpers

```python
def rect_center(obj):
    return (obj["rect"].cx, obj["rect"].cy)

def cv_score(values):
    if len(values) < 2:
        return 1.0
    m = mean(values)
    if abs(m) < 1e-9:
        return 0.0
    return 1 / (1 + pstdev(values) / abs(m))

def position_phase_score(points, axis="x"):
    coords = sorted(p[0] if axis == "x" else p[1] for p in points)
    gaps = [b - a for a, b in zip(coords, coords[1:])]
    return cv_score(gaps)

def orientation_consistency(degrees, axis_symmetric=True):
    multiplier = 2 if axis_symmetric else 1
    vectors = [
        (
            math.cos(math.radians(d * multiplier)),
            math.sin(math.radians(d * multiplier)),
        )
        for d in degrees
    ]
    return math.hypot(mean(x for x, _ in vectors), mean(y for _, y in vectors))

def group_compactness(group_objects):
    left = min(o["rect"].left for o in group_objects)
    right = max(o["rect"].right for o in group_objects)
    top = min(o["rect"].top for o in group_objects)
    bottom = max(o["rect"].bottom for o in group_objects)
    hull_area = max(1e-9, (right - left) * (bottom - top))
    occupied = sum(o["rect"].area for o in group_objects)
    return min(1.0, occupied / hull_area)
```

These helpers are deliberately small. They are not final theory; they are the first reproducible metric rows.

### First Metric Matrix Rows

```python
def by_group(group_id):
    return [o for o in debug_fixture_records if o["group"] == group_id]

north_tables = [o for o in debug_fixture_records if o["id"].startswith("north_table_")]
west_lounge = by_group("west_lounge")
center_upper = by_group("center_lounge_upper")
center_lower = by_group("center_lounge_lower")
east_armchairs = by_group("east_armchairs")

metric_rows = [
    {
        "view_id": "north_tables_order",
        "metric": "x_phase_regular",
        "score": position_phase_score([rect_center(o) for o in north_tables[:3]], axis="x"),
        "method": "gap_cv_score",
        "uncertainty": "valid only for the repeated north table row",
    },
    {
        "view_id": "north_tables_order",
        "metric": "orientation_consistency",
        "score": orientation_consistency([o["orientation"] for o in north_tables]),
        "method": "circular_resultant",
        "uncertainty": "axis-symmetric furniture assumed",
    },
    {
        "view_id": "west_lounge_geometry",
        "metric": "compactness",
        "score": group_compactness(west_lounge),
        "method": "occupied_area_over_bbox_area",
        "uncertainty": "compactness is descriptive, not automatically good",
    },
    {
        "view_id": "center_lounge_geometry",
        "metric": "upper_compactness",
        "score": group_compactness(center_upper),
        "method": "occupied_area_over_bbox_area",
        "uncertainty": "does not yet include facing/enclosure",
    },
    {
        "view_id": "center_lounge_geometry",
        "metric": "lower_compactness",
        "score": group_compactness(center_lower),
        "method": "occupied_area_over_bbox_area",
        "uncertainty": "does not yet include facing/enclosure",
    },
    {
        "view_id": "east_armchair_geometry",
        "metric": "compactness",
        "score": group_compactness(east_armchairs),
        "method": "occupied_area_over_bbox_area",
        "uncertainty": "armchair facing direction not encoded yet",
    },
]
```

### Required Output Table

The notebook should print rows as a `pandas.DataFrame` if pandas is already available. If not, printing a list of dictionaries is acceptable for the first pass.

Required visible columns:

```text
view_id | metric | score | method | uncertainty
```

### Overlay Requirements

The first overlay must label:

- object ids;
- group ids;
- candidate regions;
- local axis for north tables;
- path placeholder.

SVG generation can be direct string formatting. Do not add a plotting dependency for this.

## Next Notebook Work

1. Keep `test/floorplan_order_matrix_demo.ipynb` executable.
2. Keep the notebook on the automatic loader/evaluator path.
3. Add slanted/irregular boundary cells as separate follow-up fixtures.
4. Do not add image recognition until structured geometry metrics are stable.
