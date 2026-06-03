# Affordance Aisle Scene Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evaluation-first affordance and aisle system with a sampled grid backend, structured violations, and a visual notebook demo.

**Architecture:** Keep `OrderAnalyzer` as the public report orchestrator, but move new spatial concepts into focused modules under `features/affordance/`. Use semantic entities and profiles for customization, a `SpatialGridBackend` for MVP computation, and stable report fields that can later support polygon geometry and layout generation.

**Tech Stack:** Python 3.12 via Pixi, pytest, dataclasses, stdlib JSON for notebook generation, existing OCTA rendering helpers for visual context.

---

## File Structure

- Create `features/affordance/__init__.py`: public exports for the new affordance package.
- Create `features/affordance/models.py`: `Rect`, `SpatialEntity`, `Furniture`, `GridFrame`, and `SceneModel`.
- Create `features/affordance/profiles.py`: `AffordanceProfile`, `AisleProfile`, default registry, and profile merge helpers.
- Create `features/affordance/grid_backend.py`: sampled grid cells, occupancy marking, affordance marking, conflict marking, and reachability.
- Create `features/affordance/evaluator.py`: `AffordanceEvaluator`, `AisleEvaluator`, and combined `evaluate_spatial_access()`.
- Modify `features/entities.py`: extend `Table` and add `Chair` as convenience domain objects with affordance/aisle overrides.
- Modify `features/analyzer.py`: add optional `include_affordance=False` and `affordance_options=None` report integration.
- Modify `features/__init__.py` and root `__init__.py`: export `Chair` and selected affordance classes.
- Create `test/test_affordance_aisle.py`: unit and integration tests for the new system.
- Create `test/affordance_aisle_demo.ipynb`: visual demo matching the style of `test/first_test.ipynb`.

This directory is not a git repository. Replace commit steps with explicit checkpoint verification.

---

### Task 1: Spatial Entity Model

**Files:**
- Create: `features/affordance/__init__.py`
- Create: `features/affordance/models.py`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Write failing tests for rectangles and furniture entities**

Add this to `test/test_affordance_aisle.py`:

```python
import pytest

from features.affordance.models import Furniture, Rect, SceneModel


def test_rect_geometry_helpers():
    rect = Rect(cx=100, cy=50, width=40, height=20)

    assert rect.left == pytest.approx(80)
    assert rect.right == pytest.approx(120)
    assert rect.top == pytest.approx(40)
    assert rect.bottom == pytest.approx(60)
    assert rect.area == pytest.approx(800)
    assert rect.intersects(Rect(cx=120, cy=50, width=10, height=10))
    assert not rect.intersects(Rect(cx=200, cy=50, width=10, height=10))


def test_scene_model_indexes_furniture_entities():
    table = Furniture(
        id="table_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=100, cy=100, width=80, height=40),
        parent_id="group_1",
    )
    scene = SceneModel(entities=[table])

    assert scene.get_entity("table_1") is table
    assert scene.entities_by_role("table") == [table]
    assert scene.entities_by_parent("group_1") == [table]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: import failure because `features.affordance.models` does not exist.

- [ ] **Step 3: Implement spatial models**

Create `features/affordance/models.py`:

```python
"""Semantic spatial models for affordance and aisle evaluation."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle in world coordinates."""

    cx: float
    cy: float
    width: float
    height: float

    @property
    def left(self):
        return self.cx - self.width / 2.0

    @property
    def right(self):
        return self.cx + self.width / 2.0

    @property
    def top(self):
        return self.cy - self.height / 2.0

    @property
    def bottom(self):
        return self.cy + self.height / 2.0

    @property
    def area(self):
        return max(0.0, self.width) * max(0.0, self.height)

    def intersects(self, other):
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bottom < other.top
            or self.top > other.bottom
        )

    def expanded(self, left=0.0, right=0.0, top=0.0, bottom=0.0):
        new_left = self.left - left
        new_right = self.right + right
        new_top = self.top - top
        new_bottom = self.bottom + bottom
        return Rect(
            cx=(new_left + new_right) / 2.0,
            cy=(new_top + new_bottom) / 2.0,
            width=max(0.0, new_right - new_left),
            height=max(0.0, new_bottom - new_top),
        )


@dataclass(frozen=True)
class SpatialEntity:
    id: str
    type_id: str
    role: str
    rect: Rect
    parent_id: str = "root"
    orientation: float = 0.0
    metadata: dict = field(default_factory=dict)
    affordance: dict = field(default_factory=dict)
    aisle: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Furniture(SpatialEntity):
    pass


@dataclass(frozen=True)
class GridFrame:
    id: str
    kind: str = "furniture_grid"
    parent_id: str = "root"
    metadata: dict = field(default_factory=dict)


class SceneModel:
    """Minimal scene container for evaluation-first spatial analysis."""

    def __init__(self, entities=None, grids=None):
        self.entities = list(entities or [])
        self.grids = list(grids or [])
        self._entity_by_id = {entity.id: entity for entity in self.entities}

    def get_entity(self, entity_id):
        return self._entity_by_id[entity_id]

    def entities_by_role(self, role):
        return [entity for entity in self.entities if entity.role == role]

    def entities_by_parent(self, parent_id):
        return [entity for entity in self.entities if entity.parent_id == parent_id]
```

Create `features/affordance/__init__.py`:

```python
"""Affordance and aisle evaluation package."""

from .models import Furniture, GridFrame, Rect, SceneModel, SpatialEntity

__all__ = ["Furniture", "GridFrame", "Rect", "SceneModel", "SpatialEntity"]
```

- [ ] **Step 4: Run task tests**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: 2 passed.

- [ ] **Step 5: Checkpoint**

Run:

```bash
pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q
```

Expected: existing MVP tests still pass plus the new spatial model tests.

---

### Task 2: Profiles and Customization

**Files:**
- Create: `features/affordance/profiles.py`
- Modify: `features/affordance/__init__.py`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add failing profile tests**

Append to `test/test_affordance_aisle.py`:

```python
from features.affordance.profiles import (
    AffordanceProfile,
    AisleProfile,
    resolve_affordance_profile,
    resolve_aisle_profile,
)


def test_affordance_profile_supports_edge_specific_depth_override():
    profile = resolve_affordance_profile(
        "table.default",
        {
            "usable_edges": ["right", "bottom"],
            "edge_depth": {"right": 900, "bottom": 600},
            "coverage_threshold": 0.8,
        },
    )

    assert profile.usable_edges == ("right", "bottom")
    assert profile.depth_for("right") == pytest.approx(900)
    assert profile.depth_for("bottom") == pytest.approx(600)
    assert profile.depth_for("left") == pytest.approx(0)
    assert profile.coverage_threshold == pytest.approx(0.8)


def test_aisle_profile_allows_instance_override():
    profile = resolve_aisle_profile("table.default", {"min_width": 1200})

    assert profile.min_width == pytest.approx(1200)
    assert profile.reachability_required is True
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: import failure for `features.affordance.profiles`.

- [ ] **Step 3: Implement profile dataclasses and merge helpers**

Create `features/affordance/profiles.py`:

```python
"""Customizable affordance and aisle profiles."""

from dataclasses import dataclass, replace

EDGE_KEYS = ("top", "right", "bottom", "left")


@dataclass(frozen=True)
class AffordanceProfile:
    usable_edges: tuple[str, ...] = EDGE_KEYS
    edge_depth: dict | float = 600.0
    min_clearance: float = 450.0
    min_aisle_width: float = 900.0
    merge_policy: str = "deactivate_touching_edges"
    coverage_threshold: float = 0.75

    def depth_for(self, edge):
        if edge not in self.usable_edges:
            return 0.0
        if isinstance(self.edge_depth, dict):
            return float(self.edge_depth.get(edge, 0.0))
        return float(self.edge_depth)


@dataclass(frozen=True)
class AisleProfile:
    min_width: float = 900.0
    reachability_required: bool = True
    bottleneck_soft_ratio: float = 0.8


DEFAULT_AFFORDANCE_PROFILES = {
    "furniture.default": AffordanceProfile(),
    "table.default": AffordanceProfile(),
    "chair.default": AffordanceProfile(
        usable_edges=("front",),
        edge_depth={"front": 450.0},
        min_clearance=300.0,
        min_aisle_width=600.0,
    ),
}

DEFAULT_AISLE_PROFILES = {
    "furniture.default": AisleProfile(),
    "table.default": AisleProfile(),
    "chair.default": AisleProfile(min_width=600.0),
}


def _coerce_edges(value):
    if value is None:
        return None
    return tuple(str(edge) for edge in value)


def resolve_affordance_profile(type_id, override=None):
    base = DEFAULT_AFFORDANCE_PROFILES.get(
        type_id, DEFAULT_AFFORDANCE_PROFILES["furniture.default"]
    )
    override = dict(override or {})
    if "usable_edges" in override:
        override["usable_edges"] = _coerce_edges(override["usable_edges"])
    return replace(base, **override)


def resolve_aisle_profile(type_id, override=None):
    base = DEFAULT_AISLE_PROFILES.get(
        type_id, DEFAULT_AISLE_PROFILES["furniture.default"]
    )
    return replace(base, **dict(override or {}))
```

Modify `features/affordance/__init__.py`:

```python
"""Affordance and aisle evaluation package."""

from .models import Furniture, GridFrame, Rect, SceneModel, SpatialEntity
from .profiles import (
    AffordanceProfile,
    AisleProfile,
    resolve_affordance_profile,
    resolve_aisle_profile,
)

__all__ = [
    "AffordanceProfile",
    "AisleProfile",
    "Furniture",
    "GridFrame",
    "Rect",
    "SceneModel",
    "SpatialEntity",
    "resolve_affordance_profile",
    "resolve_aisle_profile",
]
```

- [ ] **Step 4: Run profile tests**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: all current affordance tests pass.

---

### Task 3: Spatial Grid Backend

**Files:**
- Create: `features/affordance/grid_backend.py`
- Modify: `features/affordance/__init__.py`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add failing grid backend tests**

Append to `test/test_affordance_aisle.py`:

```python
from features.affordance.grid_backend import SpatialGridBackend


def test_spatial_grid_marks_occupied_and_affordance_owner_tags():
    grid = SpatialGridBackend(width=300, height=200, resolution=50)
    rect = Rect(cx=100, cy=100, width=100, height=50)

    grid.mark_occupied("table_1", rect)
    grid.mark_affordance("table_1", rect.expanded(left=50, right=50))

    occupied = grid.cells_with("occupied_by", "table_1")
    affordance = grid.cells_with("affordance_for", "table_1")

    assert occupied
    assert affordance
    assert len(affordance) > len(occupied)


def test_spatial_grid_detects_conflicted_affordance_cells():
    grid = SpatialGridBackend(width=300, height=200, resolution=50)
    table = Rect(cx=100, cy=100, width=100, height=50)
    blocker = Rect(cx=175, cy=100, width=50, height=50)

    grid.mark_affordance("table_1", table.expanded(right=100))
    grid.mark_occupied("blocker_1", blocker)
    grid.mark_conflicts()

    conflicted = grid.cells_with("conflict_for", "table_1")
    assert conflicted
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: import failure for `SpatialGridBackend`.

- [ ] **Step 3: Implement grid backend**

Create `features/affordance/grid_backend.py`:

```python
"""Sampled spatial grid backend for MVP affordance and aisle evaluation."""

from collections import deque


class SpatialGridBackend:
    def __init__(self, width, height, resolution=50):
        if resolution <= 0:
            raise ValueError("resolution must be greater than 0")
        self.width = float(width)
        self.height = float(height)
        self.resolution = float(resolution)
        self.n_cols = max(1, int((self.width + self.resolution - 1) // self.resolution))
        self.n_rows = max(1, int((self.height + self.resolution - 1) // self.resolution))
        self.cells = [
            [
                {
                    "occupied_by": set(),
                    "affordance_for": set(),
                    "conflict_for": set(),
                    "reachable": False,
                }
                for _ in range(self.n_cols)
            ]
            for _ in range(self.n_rows)
        ]

    def cell_center(self, row, col):
        return (
            (col + 0.5) * self.resolution,
            (row + 0.5) * self.resolution,
        )

    def iter_indices_in_rect(self, rect):
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                x, y = self.cell_center(row, col)
                if rect.left <= x <= rect.right and rect.top <= y <= rect.bottom:
                    yield row, col

    def mark_occupied(self, object_id, rect):
        for row, col in self.iter_indices_in_rect(rect):
            self.cells[row][col]["occupied_by"].add(object_id)

    def mark_affordance(self, object_id, rect):
        for row, col in self.iter_indices_in_rect(rect):
            self.cells[row][col]["affordance_for"].add(object_id)

    def mark_conflicts(self):
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                cell = self.cells[row][col]
                if cell["occupied_by"] and cell["affordance_for"]:
                    cell["conflict_for"].update(cell["affordance_for"])

    def cells_with(self, key, value):
        found = []
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                if value in self.cells[row][col][key]:
                    found.append((row, col))
        return found

    def free(self, row, col):
        return not self.cells[row][col]["occupied_by"]

    def compute_reachability(self, starts):
        queue = deque()
        for row, col in starts:
            if 0 <= row < self.n_rows and 0 <= col < self.n_cols and self.free(row, col):
                self.cells[row][col]["reachable"] = True
                queue.append((row, col))

        while queue:
            row, col = queue.popleft()
            for nr, nc in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if not (0 <= nr < self.n_rows and 0 <= nc < self.n_cols):
                    continue
                cell = self.cells[nr][nc]
                if cell["reachable"] or not self.free(nr, nc):
                    continue
                cell["reachable"] = True
                queue.append((nr, nc))

    def debug_matrix(self, key):
        matrix = []
        for row in range(self.n_rows):
            values = []
            for col in range(self.n_cols):
                value = self.cells[row][col][key]
                if isinstance(value, set):
                    values.append(len(value))
                else:
                    values.append(1 if value else 0)
            matrix.append(values)
        return matrix
```

Modify `features/affordance/__init__.py` to export `SpatialGridBackend`:

```python
from .grid_backend import SpatialGridBackend
```

Add `"SpatialGridBackend"` to `__all__`.

- [ ] **Step 4: Run grid tests**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: grid backend tests pass.

---

### Task 4: Affordance Evaluator

**Files:**
- Create: `features/affordance/evaluator.py`
- Modify: `features/affordance/__init__.py`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add failing affordance evaluator tests**

Append to `test/test_affordance_aisle.py`:

```python
from features.affordance.evaluator import AffordanceEvaluator


def test_affordance_evaluator_reports_low_coverage_when_blocked():
    table = Furniture(
        id="table_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=100, cy=100, width=100, height=50),
        affordance={"usable_edges": ["right"], "edge_depth": {"right": 100}},
    )
    blocker = Furniture(
        id="blocker_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=175, cy=100, width=50, height=50),
    )
    scene = SceneModel([table, blocker])

    result = AffordanceEvaluator(width=300, height=200, resolution=25).evaluate(scene)

    assert result["enabled"] is True
    assert result["backend"] == "grid"
    assert result["objects"]["table_1"]["coverage"] < 1.0
    assert result["violations"]
    assert result["violations"][0]["suggestion_hint"] == "increase_clearance"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: import failure for `AffordanceEvaluator`.

- [ ] **Step 3: Implement affordance evaluator**

Create `features/affordance/evaluator.py`:

```python
"""Affordance and aisle evaluators using the sampled grid backend."""

from .grid_backend import SpatialGridBackend
from .profiles import resolve_affordance_profile, resolve_aisle_profile


EDGE_EXPANSION = {
    "top": lambda d: {"top": d},
    "right": lambda d: {"right": d},
    "bottom": lambda d: {"bottom": d},
    "left": lambda d: {"left": d},
}


def _edge_band(rect, edge, depth):
    if edge == "top":
        return rect.expanded(top=depth)
    if edge == "right":
        return rect.expanded(right=depth)
    if edge == "bottom":
        return rect.expanded(bottom=depth)
    if edge == "left":
        return rect.expanded(left=depth)
    return rect


class AffordanceEvaluator:
    def __init__(self, width, height, resolution=50):
        self.width = width
        self.height = height
        self.resolution = resolution

    def evaluate(self, scene):
        grid = SpatialGridBackend(self.width, self.height, self.resolution)

        for entity in scene.entities:
            grid.mark_occupied(entity.id, entity.rect)

        object_reports = {}
        for entity in scene.entities:
            profile = resolve_affordance_profile(entity.type_id, entity.affordance)
            required_cells = set()
            for edge in profile.usable_edges:
                depth = profile.depth_for(edge)
                if depth <= 0:
                    continue
                band = _edge_band(entity.rect, edge, depth)
                grid.mark_affordance(entity.id, band)
                required_cells.update(grid.cells_with("affordance_for", entity.id))

            object_reports[entity.id] = {
                "coverage_threshold": profile.coverage_threshold,
                "required_cells": required_cells,
            }

        grid.mark_conflicts()

        violations = []
        scores = []
        for entity in scene.entities:
            required_cells = object_reports[entity.id]["required_cells"]
            conflict_cells = set(grid.cells_with("conflict_for", entity.id))
            effective_cells = required_cells - conflict_cells
            coverage = 1.0 if not required_cells else len(effective_cells) / len(required_cells)
            threshold = object_reports[entity.id]["coverage_threshold"]

            object_reports[entity.id] = {
                "coverage": round(coverage, 4),
                "required_area": len(required_cells) * (self.resolution ** 2),
                "effective_area": len(effective_cells) * (self.resolution ** 2),
                "blocked_edges": [],
            }
            scores.append(coverage)

            if coverage < threshold:
                location = None
                if conflict_cells:
                    row, col = sorted(conflict_cells)[0]
                    location = {"row": row, "col": col}
                violations.append(
                    {
                        "type": "affordance_coverage_low",
                        "severity": "soft",
                        "object_ids": [entity.id],
                        "location": location,
                        "required": threshold,
                        "actual": round(coverage, 4),
                        "suggestion_hint": "increase_clearance",
                    }
                )

        score = 1.0 if not scores else sum(scores) / len(scores)
        return {
            "enabled": True,
            "backend": "grid",
            "score": round(score, 4),
            "objects": object_reports,
            "violations": violations,
            "debug": {
                "occupied": grid.debug_matrix("occupied_by"),
                "affordance": grid.debug_matrix("affordance_for"),
                "conflict": grid.debug_matrix("conflict_for"),
            },
        }
```

Modify `features/affordance/__init__.py` to export `AffordanceEvaluator`.

- [ ] **Step 4: Run affordance evaluator tests**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: affordance evaluator tests pass.

---

### Task 5: Aisle Evaluator

**Files:**
- Modify: `features/affordance/evaluator.py`
- Modify: `features/affordance/__init__.py`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add failing aisle evaluator test**

Append to `test/test_affordance_aisle.py`:

```python
from features.affordance.evaluator import AisleEvaluator


def test_aisle_evaluator_marks_unreachable_object_when_blocked_by_wall():
    wall = Furniture(
        id="wall_1",
        type_id="furniture.default",
        role="obstacle",
        rect=Rect(cx=150, cy=100, width=50, height=200),
    )
    table = Furniture(
        id="table_1",
        type_id="table.default",
        role="table",
        rect=Rect(cx=250, cy=100, width=40, height=40),
    )
    scene = SceneModel([wall, table])

    result = AisleEvaluator(width=300, height=200, resolution=50).evaluate(scene)

    assert result["enabled"] is True
    assert "table_1" in result["unreachable_objects"]
    assert result["score"] < 1.0
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: import failure or missing class for `AisleEvaluator`.

- [ ] **Step 3: Implement aisle evaluator**

Append to `features/affordance/evaluator.py`:

```python
class AisleEvaluator:
    def __init__(self, width, height, resolution=50, entries=None):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.entries = entries

    def _default_entries(self, grid):
        return [(row, 0) for row in range(grid.n_rows)]

    def _entity_reachable(self, grid, entity):
        for row, col in grid.iter_indices_in_rect(entity.rect.expanded(left=self.resolution, right=self.resolution, top=self.resolution, bottom=self.resolution)):
            if grid.cells[row][col]["reachable"]:
                return True
        return False

    def evaluate(self, scene):
        grid = SpatialGridBackend(self.width, self.height, self.resolution)
        for entity in scene.entities:
            grid.mark_occupied(entity.id, entity.rect)

        entries = self.entries or self._default_entries(grid)
        grid.compute_reachability(entries)

        reachable = []
        unreachable = []
        for entity in scene.entities:
            if entity.role == "obstacle":
                continue
            aisle_profile = resolve_aisle_profile(entity.type_id, entity.aisle)
            if not aisle_profile.reachability_required:
                continue
            if self._entity_reachable(grid, entity):
                reachable.append(entity.id)
            else:
                unreachable.append(entity.id)

        total = len(reachable) + len(unreachable)
        score = 1.0 if total == 0 else len(reachable) / total
        bottlenecks = []
        for entity_id in unreachable:
            bottlenecks.append(
                {
                    "type": "unreachable_object",
                    "severity": "hard",
                    "object_ids": [entity_id],
                    "suggestion_hint": "open_aisle_path",
                }
            )

        return {
            "enabled": True,
            "score": round(score, 4),
            "reachable_objects": reachable,
            "unreachable_objects": unreachable,
            "bottlenecks": bottlenecks,
            "debug": {"reachable": grid.debug_matrix("reachable")},
        }
```

Modify `features/affordance/__init__.py` to export `AisleEvaluator`.

- [ ] **Step 4: Run aisle tests**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: aisle evaluator tests pass.

---

### Task 6: Table and Chair Convenience Entities

**Files:**
- Modify: `features/entities.py`
- Modify: `features/__init__.py`
- Modify: `__init__.py`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add failing entity tests**

Append to `test/test_affordance_aisle.py`:

```python
from features.entities import Chair, Table


def test_table_and_chair_cells_include_profile_overrides():
    table = Table(
        id="table_1",
        size=(1200, 800),
        affordance={"usable_edges": ["right"]},
        aisle={"min_width": 1000},
    )
    chair = Chair(id="chair_1", size=(400, 400), orientation=180)

    table_cell = table.to_cell()
    chair_cell = chair.to_cell()

    assert table_cell["id"] == "table_1"
    assert table_cell["type_id"] == "table.default"
    assert table_cell["affordance"]["usable_edges"] == ["right"]
    assert table_cell["aisle"]["min_width"] == 1000
    assert chair_cell["role"] == "chair"
    assert chair_cell["type_id"] == "chair.default"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: `Chair` import failure and `Table` missing fields.

- [ ] **Step 3: Extend entity convenience classes**

Modify `features/entities.py`:

```python
"""Domain entities for semantic grid input."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Table:
    """Table domain object that can be converted into analyzer cell schema."""

    shape: str = "rect"
    size: tuple[float, float] | float | None = None
    attr: str = ""
    orientation: float = 0.0
    group: str = "global"
    id: str = ""
    type_id: str = "table.default"
    affordance: dict = field(default_factory=dict)
    aisle: dict = field(default_factory=dict)

    def to_cell(self):
        shape = str(self.shape).lower().strip() or "rect"
        cell = {
            "shape": shape,
            "size": self.size,
            "role": "table",
            "type_id": str(self.type_id),
            "attr": str(self.attr),
            "orientation": float(self.orientation),
            "group": str(self.group),
            "affordance": dict(self.affordance),
            "aisle": dict(self.aisle),
        }
        if self.id:
            cell["id"] = str(self.id)
        return cell


@dataclass(frozen=True)
class Chair:
    """Chair domain object that can be converted into analyzer cell schema."""

    shape: str = "circle"
    size: tuple[float, float] | float | None = None
    attr: str = ""
    orientation: float = 0.0
    group: str = "global"
    id: str = ""
    type_id: str = "chair.default"
    affordance: dict = field(default_factory=dict)
    aisle: dict = field(default_factory=dict)

    def to_cell(self):
        shape = str(self.shape).lower().strip() or "circle"
        cell = {
            "shape": shape,
            "size": self.size,
            "role": "chair",
            "type_id": str(self.type_id),
            "attr": str(self.attr),
            "orientation": float(self.orientation),
            "group": str(self.group),
            "affordance": dict(self.affordance),
            "aisle": dict(self.aisle),
        }
        if self.id:
            cell["id"] = str(self.id)
        return cell
```

Modify `features/__init__.py` and root `__init__.py` to export `Chair`:

```python
from .entities import Chair, Table

__all__ = ["OrderAnalyzer", "Table", "Chair"]
```

- [ ] **Step 4: Run entity tests and regression tests**

Run:

```bash
pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q
```

Expected: all tests pass.

---

### Task 7: Report Integration

**Files:**
- Modify: `features/schema.py`
- Modify: `features/analyzer.py`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add failing report integration test**

Append to `test/test_affordance_aisle.py`:

```python
def test_order_analyzer_report_includes_affordance_and_aisle_when_enabled():
    grid = [
        [
            Table(id="table_1", size=(80, 40), affordance={"usable_edges": ["right"], "edge_depth": {"right": 80}}),
            Table(id="blocker_1", size=(40, 40)),
        ]
    ]

    report = OrderAnalyzer(
        actual_matrix=grid,
        ideal_matrix=grid,
        layout_size=(300, 150),
        fit_to_layout=True,
    ).report(
        features=("shapes",),
        include_affordance=True,
        affordance_options={"width": 300, "height": 150, "resolution": 25},
    )

    assert "affordance" in report
    assert "aisle" in report
    assert report["affordance"]["enabled"] is True
    assert "table_1" in report["affordance"]["objects"]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py::test_order_analyzer_report_includes_affordance_and_aisle_when_enabled -q
```

Expected: `report()` does not accept `include_affordance`.

- [ ] **Step 3: Preserve schema custom fields**

Modify `features/schema.py` inside `CELL_DEFAULTS`:

```python
CELL_DEFAULTS = {
    "shape": "rect",
    "attr": "",
    "orientation": 0.0,
    "role": "",
    "group": "global",
    "id": "",
    "type_id": "",
    "affordance": {},
    "aisle": {},
}
```

Inside `normalize_cell`, after group normalization:

```python
    normalized["id"] = str(normalized.get("id", ""))
    normalized["type_id"] = str(normalized.get("type_id", ""))
    if not isinstance(normalized.get("affordance"), dict):
        normalized["affordance"] = {}
    if not isinstance(normalized.get("aisle"), dict):
        normalized["aisle"] = {}
```

- [ ] **Step 4: Add analyzer scene conversion and report integration**

Modify `features/analyzer.py` imports:

```python
from .affordance.evaluator import AffordanceEvaluator, AisleEvaluator
from .affordance.models import Furniture, Rect, SceneModel
```

Add method to `OrderAnalyzer`:

```python
    def _build_scene_model(self):
        entities = []
        default_size = _parse_size(self.cell_size) or (
            min(self.spacing[1], 100.0) * 0.5,
            min(self.spacing[0], 100.0) * 0.5,
        )
        for r, row in enumerate(self.actual_matrix):
            for c, cell in enumerate(row):
                cx, cy = spacing_to_xy(r, c, self.spacing)
                size = _resolve_cell_boundingbox(cell, default_size) or default_size
                shape = str(cell.get("shape", "")).lower()
                role = str(cell.get("role", "")).lower().strip() or ROLE_FROM_SHAPE.get(shape, "unknown")
                type_id = str(cell.get("type_id", "")).strip() or f"{role}.default"
                entity_id = str(cell.get("id", "")).strip() or f"r{r}_c{c}"
                entities.append(
                    Furniture(
                        id=entity_id,
                        type_id=type_id,
                        role=role,
                        rect=Rect(cx=cx, cy=cy, width=size[0], height=size[1]),
                        parent_id=str(cell.get("group", "global")),
                        orientation=float(cell.get("orientation", 0.0)),
                        metadata={"row": r, "col": c},
                        affordance=dict(cell.get("affordance", {})),
                        aisle=dict(cell.get("aisle", {})),
                    )
                )
        return SceneModel(entities=entities)
```

Change `report` signature:

```python
    def report(self, features=("shapes",), include_affordance=False, affordance_options=None):
```

Before final `return`, compute optional output:

```python
        affordance_report = None
        aisle_report = None
        if include_affordance:
            options = dict(affordance_options or {})
            width = options.get("width")
            height = options.get("height")
            if width is None or height is None:
                if self.stim_size is not None:
                    width, height = self.stim_size
                else:
                    width = max(1.0, self.n_cols * self.spacing[1])
                    height = max(1.0, self.n_rows * self.spacing[0])
            resolution = options.get("resolution", 50)
            scene = self._build_scene_model()
            affordance_report = AffordanceEvaluator(width, height, resolution).evaluate(scene)
            aisle_report = AisleEvaluator(width, height, resolution).evaluate(scene)
```

Store the existing return dict in `result`, then add:

```python
        if include_affordance:
            result["affordance"] = affordance_report
            result["aisle"] = aisle_report
        return result
```

- [ ] **Step 5: Run integration tests**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py -q
```

Expected: all affordance tests pass.

- [ ] **Step 6: Run full local regression**

Run:

```bash
pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q
```

Expected: all tests pass.

---

### Task 8: Visual Notebook Demo

**Files:**
- Create: `test/affordance_aisle_demo.ipynb`
- Test: `test/test_affordance_aisle.py`

- [ ] **Step 1: Add notebook existence test**

Append to `test/test_affordance_aisle.py`:

```python
import json
from pathlib import Path


def test_affordance_aisle_demo_notebook_exists_and_mentions_key_outputs():
    notebook_path = Path("test/affordance_aisle_demo.ipynb")
    assert notebook_path.exists()

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook.get("cells", [])
    )

    assert "include_affordance=True" in source
    assert "affordance" in source
    assert "aisle" in source
    assert "conflict" in source
    assert "reachable" in source
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py::test_affordance_aisle_demo_notebook_exists_and_mentions_key_outputs -q
```

Expected: notebook file does not exist.

- [ ] **Step 3: Create notebook with visual demo cells**

Create `test/affordance_aisle_demo.ipynb` as a valid nbformat 4 JSON notebook with these code cells:

```python
import sys, os

def find_order_analyzer_parent(start=None):
    current = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(current, "features")) and os.path.isdir(os.path.join(current, "OCTA_toolbox-master")):
            return os.path.abspath(os.path.join(current, os.pardir))
        if os.path.isdir(os.path.join(current, "order_analyzer")) and os.path.isdir(os.path.join(current, "order_analyzer", "features")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent

project_parent = find_order_analyzer_parent()
if project_parent not in sys.path:
    sys.path.insert(0, project_parent)

from order_analyzer import OrderAnalyzer, Table
try:
    from order_analyzer import Chair
except ImportError:
    Chair = None
```

```python
from IPython.display import display, Markdown

good = [
    [
        Table(id="table_1", size=(80, 40), affordance={"usable_edges": ["right"], "edge_depth": {"right": 50}}),
        {"shape": "rect", "role": "empty", "id": "open_1", "size": (10, 10)},
        Table(id="table_2", size=(80, 40), affordance={"usable_edges": ["left"], "edge_depth": {"left": 50}}),
    ]
]

bad = [
    [
        Table(id="table_1", size=(80, 40), affordance={"usable_edges": ["right"], "edge_depth": {"right": 80}}),
        Table(id="blocker_1", size=(80, 40)),
        Table(id="table_2", size=(80, 40), affordance={"usable_edges": ["left"], "edge_depth": {"left": 80}}),
    ]
]
```

```python
display(Markdown("### Good case"))
good_report = OrderAnalyzer(
    actual_matrix=good,
    ideal_matrix=good,
    layout_size=(360, 160),
    fit_to_layout=True,
).report(
    features=("shapes",),
    include_affordance=True,
    affordance_options={"width": 360, "height": 160, "resolution": 20},
)
good_report["affordance"], good_report["aisle"]
```

```python
display(Markdown("### Bad case"))
bad_report = OrderAnalyzer(
    actual_matrix=bad,
    ideal_matrix=bad,
    layout_size=(360, 160),
    fit_to_layout=True,
).report(
    features=("shapes",),
    include_affordance=True,
    affordance_options={"width": 360, "height": 160, "resolution": 20},
)
bad_report["affordance"], bad_report["aisle"]
```

```python
import matplotlib.pyplot as plt

def show_debug_matrix(report, key, title):
    matrix = report["affordance"]["debug"].get(key) or report["aisle"]["debug"].get(key)
    plt.figure(figsize=(6, 2.4))
    plt.imshow(matrix, cmap="viridis")
    plt.title(title)
    plt.colorbar()
    plt.show()

show_debug_matrix(bad_report, "occupied", "Occupied cells")
show_debug_matrix(bad_report, "affordance", "Affordance cells")
show_debug_matrix(bad_report, "conflict", "Conflict cells")
show_debug_matrix(bad_report, "reachable", "Reachable aisle cells")
```

Use stdlib JSON or a notebook editor; the saved file must be a valid `.ipynb`.

- [ ] **Step 4: Run notebook existence test**

Run:

```bash
pixi run pytest test/test_affordance_aisle.py::test_affordance_aisle_demo_notebook_exists_and_mentions_key_outputs -q
```

Expected: pass.

- [ ] **Step 5: Execute notebook smoke check**

Run:

```bash
pixi run python -c "import json; nb=json.load(open('test/affordance_aisle_demo.ipynb', encoding='utf-8')); src=''.join(''.join(c.get('source', [])) for c in nb['cells']); print(len(nb['cells']), 'include_affordance=True' in src, 'show_debug_matrix' in src)"
```

Expected output:

```text
5 True True
```

---

### Task 9: Plan Completion Verification

**Files:**
- Modify only if tests reveal a defect in the files introduced above.

- [ ] **Step 1: Run all project tests**

Run:

```bash
pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run an import smoke check**

Run:

```bash
pixi run python -c "from order_analyzer import OrderAnalyzer, Table, Chair; from order_analyzer.features.affordance import AffordanceEvaluator, AisleEvaluator, SpatialGridBackend; print('ok')"
```

Expected output:

```text
ok
```

- [ ] **Step 3: Verify existing behavior remains compatible**

Run:

```bash
pixi run python -c "from order_analyzer import OrderAnalyzer; grid=[[{'shape':'rect'}]]; print(OrderAnalyzer(grid, grid).report(features=('shapes',))['order'])"
```

Expected output:

```text
1.0
```

- [ ] **Step 4: Verify optional v2 fields are opt-in**

Run:

```bash
pixi run python -c "from order_analyzer import OrderAnalyzer; grid=[[{'shape':'rect'}]]; report=OrderAnalyzer(grid, grid).report(features=('shapes',)); print('affordance' in report, 'aisle' in report)"
```

Expected output:

```text
False False
```

---

## Self-Review

Spec coverage:

- Evaluation-first affordance and aisle scoring: Tasks 3, 4, 5, and 7.
- Scene/entity abstraction: Task 1.
- High customization with simple defaults: Task 2 and Task 6.
- Sampling grid MVP and polygon long-term separation: Task 3 implements grid backend; design keeps polygon out of MVP.
- Structured violations for future generation: Task 4 and Task 5.
- Visual notebook demo requirement: Task 8.
- Existing API compatibility: Task 7 and Task 9.

No red-flag planning terms are intentionally left in the task steps. The plan uses concrete file paths, commands, expected failures, and expected passing states.
