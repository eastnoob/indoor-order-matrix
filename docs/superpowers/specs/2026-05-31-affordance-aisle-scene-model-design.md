# Affordance, Aisle, and Scene Model Design

## Goal

Build the next stage of `order_analyzer` as an evaluation-first affordance and aisle system. The MVP should score whether furniture keeps enough usable space and circulation space, while preserving a clean path toward later repair/generation and polygon-based geometry.

## Current Context

The current codebase already has:

- `OrderAnalyzer` as the main report and scoring entry point.
- `features/schema.py` for v1 cell normalization.
- `features/layout.py` for grid geometry, fixed layout size, and per-cell bounding boxes.
- `features/entities.py` with a simple `Table` domain object.
- `test/test_order_analyzer_mvp.py` for pytest coverage.
- `test/first_test.ipynb` as the user-facing visual demo pattern.

The new work should not collapse all spatial concepts into `OrderAnalyzer`.

## Two Directions

There are two long-term directions:

1. Evaluation and scoring.
2. Generation, repair, and layout planning.

The first implementation phase is evaluation-first. It must still use data structures that a future generator can reuse.

The intended progression is:

1. Evaluate: compute affordance and aisle scores plus structured violations.
2. Diagnose: turn violations into repair hints.
3. Repair: move or adjust existing furniture.
4. Generate: create layouts from constraints.

## Grid Concepts

The system has three different grid concepts, and they must stay separate.

- `GridFrame`: semantic design grid, such as column grid or furniture group grid.
- Furniture grid: also a semantic `GridFrame`, used for table/chair groups.
- `SpatialGridBackend`: computational sampling grid for area, conflict, and reachability estimates.

The sampling grid is not the design grid. It is only the MVP backend for geometry evaluation.

## Proposed Architecture

Use a modular monolith with small domain classes. Avoid service-style over-fragmentation.

Core concepts:

- `SceneModel`: owns nodes, parent-child relationships, coordinate transforms, and object lookup.
- `GridFrame`: a semantic grid node for column grids, furniture grids, and future nested grids.
- `SpatialEntity`: base entity with id, role, type_id, parent_id, position, size, orientation, and metadata.
- `Furniture`: general furniture entity. `Table` and future `Chair` are convenience constructors, not separate deep hierarchies.
- `Boundary`: reserved entity type for room boundaries, carpets, shelves, and later entrance logic.
- `AffordanceProfile`: customizable rules for usable edges, edge depth, clearance, coverage threshold, and merge behavior.
- `AisleProfile`: customizable rules for minimum aisle width, reachability, and bottleneck severity.
- `SpatialGridBackend`: sampled occupancy/affordance/free/conflict/reachability backend for MVP.
- `PolygonBackend`: long-term backend for exact geometry, rotation, round tables, irregular boundaries, and SVG/CAD workflows.
- `AffordanceEvaluator`: computes per-object required/effective affordance coverage and violations.
- `AisleEvaluator`: computes free-space reachability and aisle bottlenecks from the grid backend.

## Customization Model

The API should be simple by default but allow high customization.

Profile resolution order:

1. Global defaults.
2. `type_id` default profile.
3. Instance-level profile override.
4. Per-call evaluation options.

Example minimal use:

```python
Table(size=(1200, 800))
```

Example customized use:

```python
Table(
    size=(1200, 800),
    affordance={
        "usable_edges": ["right", "bottom"],
        "edge_depth": {"right": 900, "bottom": 600},
        "min_clearance": 450,
        "min_aisle_width": 1000,
        "coverage_threshold": 0.8,
    },
)
```

## MVP Geometry

The MVP uses `SpatialGridBackend`.

Workflow:

1. Flatten entities into world coordinates.
2. Mark furniture body cells as occupied.
3. Generate edge affordance bands from each object's profile.
4. Deactivate touching/merged edges when profile policy says so.
5. Mark affordance cells with owner ids.
6. Mark conflicts where required affordance is occupied or blocked.
7. Compute per-object coverage as effective cells / required cells.
8. Compute free-space reachability and bottlenecks for aisle scoring.

## Report Contract

`OrderAnalyzer.report()` should gain optional v2 fields without changing existing v1 meanings.

Expected shape:

```python
{
    "affordance": {
        "enabled": True,
        "backend": "grid",
        "score": 0.86,
        "objects": {
            "table_1": {
                "coverage": 0.86,
                "required_area": 120,
                "effective_area": 104,
                "blocked_edges": ["left"],
            }
        },
        "violations": []
    },
    "aisle": {
        "enabled": True,
        "score": 0.78,
        "reachable_objects": ["table_1"],
        "unreachable_objects": [],
        "bottlenecks": []
    }
}
```

Violations must be structured so future generation/repair can consume them:

```python
{
    "type": "affordance_coverage_low",
    "severity": "soft",
    "object_ids": ["table_1"],
    "location": {"row": 12, "col": 8},
    "required": 0.75,
    "actual": 0.62,
    "suggestion_hint": "increase_clearance",
}
```

## Notebook Requirement

Every key feature in this stage needs tests and a visual notebook demo. The notebook should follow the spirit of `test/first_test.ipynb`:

- Import local `order_analyzer`.
- Build a small, readable furniture scene.
- Render or display the original layout.
- Show affordance/aisle report fields.
- Visualize debug output, such as occupied, affordance, conflict, and reachable cells.
- Include at least one good case and one bad case.

The planned notebook is:

`test/affordance_aisle_demo.ipynb`

## Non-Goals for MVP

The MVP does not implement:

- Full layout generation.
- Automatic repair.
- Polygon geometry backend.
- Exact rotated furniture area.
- Exact circular/irregular affordance areas.
- Boundary entrance detection.
- Recursive multi-level scoring.

The design must leave these paths open.

## Acceptance Criteria

- Existing tests still pass.
- New pytest coverage validates profiles, entity normalization, grid marking, coverage scoring, aisle reachability, and report integration.
- `test/affordance_aisle_demo.ipynb` runs and visually demonstrates key behavior.
- Existing `calculate_order()` and existing v1 report fields keep their current semantics.
- Polygon backend and generator concepts are documented as reserved interfaces, not implemented.

---

## 2026-07-02 Addendum: Current Framework Snapshot and Entry Door Slot

This addendum records the current implemented framework and the next small extension. It supersedes older MVP notes where they describe `SpatialGridBackend` as the main geometry scoring backend: continuous geometry is now the source of truth for core spatial conflicts and affordance coverage; sampled grids remain for reachability and notebook/debug explanation.

### Task 1: Current Implemented Framework Summary

`order_analyzer` is an extension layer around the original OCTA toolbox. OCTA still provides the base pattern/deviance route; this package adds semantic furniture input, layout geometry, circulation/access evaluation, and notebook-facing explanation layers.

Implemented user-facing capabilities:

- `OrderAnalyzer`: main entry point for order scoring and reports.
- `Table`, `Chair`: domain objects that convert to analyzer cell dictionaries.
- `TableTemplate`: reusable furniture type definition.
- `TableGrid`: semantic grid helper for creating many furniture instances from one template.
- `TableGrid.place(row, col, ...)`: per-instance override for id, align, offset, orientation, attr, group, affordance, and aisle.
- `TableGrid.enable_road_network(...)`: generates a road intent for every semantic grid line.
- `TableGrid.road(axis=..., index=..., ...)`: overrides or disables one road axis.
- `TableGrid.entry(...)`: declares reachability entry intent.
- `TableGrid.to_matrix()`: legacy analyzer-compatible matrix.
- `TableGrid.to_layout()`: matrix plus road and entry intents.

Implemented framework layers:

- Semantic grid: the user-facing `TableGrid` and cell matrix. This is the design grid.
- Layout geometry: `layout_size`, `fit_to_layout`, per-cell positioning, alignment, and offset conversion.
- Scene model: internal continuous scene objects generated by `OrderAnalyzer`.
- Continuous geometry: `Rect`, lightweight convex `Polygon`, furniture footprint polygons, `AffordanceBand`, `RoadBand`, `ClearanceBand`, and `EntryBand`.
- Sampled grid: `SpatialGridBackend`, used for debug matrices and BFS reachability. It is not the furniture/road/affordance body.
- Continuous conflict: `ContinuousConflictEvaluator` decides furniture / affordance / road / clearance overlap before rasterizing explanation cells.
- Continuous affordance coverage: `required_area`, `blocked_area`, `effective_area`, and `coverage` are continuous-area values.
- Blocker dedupe: overlapping blocker polygons are unioned so the same affordance area is not deducted twice.
- Visualization: notebook SVG overlays can show OCTA output, continuous furniture/affordance/road/clearance geometry, sampled debug cells, entry arrows, and continuous conflict shapes.

Current report behavior:

- `order` and `scores` keep the original OCTA-compatible order semantics plus component scores.
- `deviance_matrix` and `deviance_cells` remain 0/1 semantic-grid explanations.
- `affordance.score` averages per-object continuous coverage.
- `aisle.score` combines reachability with continuous road/clearance conflict penalties.
- `debug.*` matrices are sampled explanations and may change with `resolution`.

Current notebook reference:

- `test/simple_3x3_table_affordance_demo.ipynb` is the main visual demo for the current framework.
- The notebook demonstrates a 3x3 table grid, RoadNetwork, explicit entry, rotated furniture, continuous affordance, continuous conflicts, sampled debug overlays, and r=20/r=10 resolution comparison.

### Task 2: Entry Door Slot MVP

Goal: turn the current optional `Entry` intent into a semantic-grid door opening, without adding a separate `Door` class.

User API:

```python
grid.entry(edge="left", index=1, width=80, id="main_door")
```

Rules:

- `edge` is one of `left`, `right`, `top`, `bottom`.
- `index=None` keeps the existing behavior: the whole boundary edge is open.
- For `left` / `right`, `index` selects a row band in the semantic grid.
- For `top` / `bottom`, `index` selects a column band in the semantic grid.
- `width` is the continuous door opening width.
- `offset` shifts the door within the selected semantic edge slot.
- Door openings are optional. If the user declares no entry, the old left-boundary fallback remains.
- Multiple entries are allowed; all valid sampled start cells seed BFS.
- Entry/door geometry does not participate in furniture, affordance, road, or clearance conflict scoring.

Internal flow:

```text
TableGrid.entry(...)
  -> layout dict entries
  -> OrderAnalyzer entry intent normalization
  -> continuous EntryBand on the selected semantic boundary slot
  -> sampled BFS start cells from EntryBand
  -> report["aisle"]["entries"] and debug["entries"]
```

Implementation acceptance:

- `TableGrid.entry(edge="left", index=1, width=80, id="main_door").to_layout()` includes the entry intent.
- `OrderAnalyzer(...).report(include_affordance=True)` reads entry intents and builds `EntryBand`.
- A left-edge entry with `index=1` opens only the second row band in a 3x3 grid.
- Occupied sampled cells under the door are not used as BFS starts.
- No entry declarations still use the default left-boundary fallback.
- `test/simple_3x3_table_affordance_demo.ipynb` displays the door position and prints `aisle.entries`.

Skipped for this MVP:

- Internal road-node entries.
- Room boundary polygon doors.
- A separate `Door` class.
- Door/furniture collision scoring.
