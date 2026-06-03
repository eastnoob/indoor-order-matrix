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
