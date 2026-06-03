"""Domain entities for semantic grid input."""

from dataclasses import dataclass, field
from copy import deepcopy


@dataclass(frozen=True)
class Road:
    """User-facing circulation intent; geometry is built later by analyzer."""

    id: str = ""
    axis: str = "vertical"
    between: tuple[int, int] = (0, 1)
    width: float = 80.0
    min_clearance: float | None = None
    offset: float = 0.0
    level: str = "primary"
    priority: int = 0
    serves: tuple[str, ...] | None = None

    def to_intent(self):
        """Return a stable dict so TableGrid/OrderAnalyzer can pass road intent."""
        axis = str(self.axis).lower().strip() or "vertical"
        if axis not in {"vertical", "horizontal"}:
            raise ValueError("Road axis must be 'vertical' or 'horizontal'.")
        width = float(self.width)
        if width <= 0:
            raise ValueError("Road width must be positive.")
        clearance = width if self.min_clearance is None else float(self.min_clearance)
        if clearance <= 0:
            raise ValueError("Road min_clearance must be positive.")
        between = tuple(int(value) for value in self.between)
        if len(between) != 2:
            raise ValueError("Road between must contain two integer indexes.")

        intent = {
            "id": str(self.id),
            "axis": axis,
            "between": between,
            "width": width,
            "min_clearance": clearance,
            "offset": float(self.offset),
            "level": str(self.level),
            "priority": int(self.priority),
        }
        if "index" in getattr(self, "metadata", {}):
            intent["index"] = int(self.metadata["index"])
        if self.serves is not None:
            intent["serves"] = tuple(str(item) for item in self.serves)
        return intent


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
    align: str = "center"
    affordance: dict = field(default_factory=dict)
    aisle: dict = field(default_factory=dict)

    def to_cell(self):
        """Convert to OrderAnalyzer-compatible cell dict。"""
        shape = str(self.shape).lower().strip() or "rect"
        cell = {
            "shape": shape,
            "size": self.size,
            "role": "table",
            "type_id": str(self.type_id),
            "attr": str(self.attr),
            "orientation": float(self.orientation),
            "group": str(self.group),
            "align": str(self.align).lower().strip() or "center",
            "affordance": dict(self.affordance),
            "aisle": dict(self.aisle),
        }
        if self.id:
            cell["id"] = str(self.id)
        return cell


@dataclass(frozen=True)
class TableTemplate:
    """Reusable table type; grid placement creates concrete instances."""

    shape: str = "rect"
    size: tuple[float, float] | float | None = None
    attr: str = ""
    orientation: float = 0.0
    group: str = "global"
    type_id: str = "table.default"
    affordance: dict = field(default_factory=dict)
    aisle: dict = field(default_factory=dict)

    def base_cell(self):
        """Return shared default cell fields for one table instance."""
        shape = str(self.shape).lower().strip() or "rect"
        return {
            "shape": shape,
            "size": self.size,
            "role": "table",
            "type_id": str(self.type_id),
            "attr": str(self.attr),
            "orientation": float(self.orientation),
            "group": str(self.group),
            "align": "center",
            # Deepcopy keeps per-instance overrides from mutating template data.
            "affordance": deepcopy(self.affordance),
            "aisle": deepcopy(self.aisle),
        }


class TableGrid:
    """User-facing helper that places one table template into many cells."""

    _ALLOWED_OVERRIDES = {
        "id",
        "align",
        "offset",
        "x_offset",
        "y_offset",
        "orientation",
        "attr",
        "group",
        "affordance",
        "aisle",
    }

    def __init__(self, rows, cols, fill=None):
        self.rows = int(rows)
        self.cols = int(cols)
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("TableGrid rows/cols 必须为正整数。")
        self.fill = fill if fill is not None else TableTemplate()
        self._placements = {}
        self._roads = []
        self._road_network_defaults = None
        self._road_axis_overrides = {}

    def place(self, row, col, **overrides):
        """Override one table instance at row/col; returns self for chaining."""
        row = int(row)
        col = int(col)
        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            raise IndexError("TableGrid place(row, col) 超出网格范围。")
        unknown = set(overrides) - self._ALLOWED_OVERRIDES
        if unknown:
            raise ValueError(f"Unsupported TableGrid override fields: {sorted(unknown)}")
        self._placements[(row, col)] = dict(overrides)
        return self

    def enable_road_network(self, **kwargs):
        """Enable one road intent on every semantic grid line."""
        defaults = dict(kwargs)
        defaults.setdefault("enabled", True)
        if defaults.get("min_clearance") is None:
            defaults["min_clearance"] = defaults.get("width", 80.0)
        self._road_network_defaults = defaults
        return self

    def road(self, **kwargs):
        """Add or override Road intent; index targets one semantic grid line."""
        if "index" in kwargs:
            axis = str(kwargs.get("axis", "vertical")).lower().strip() or "vertical"
            if axis not in {"vertical", "horizontal"}:
                raise ValueError("Road axis must be 'vertical' or 'horizontal'.")
            index = int(kwargs["index"])
            max_index = self.cols if axis == "vertical" else self.rows
            if index < 0 or index > max_index:
                raise IndexError("Road index 超出 semantic grid line 范围。")
            override = dict(kwargs)
            override["axis"] = axis
            override["index"] = index
            self._road_axis_overrides[(axis, index)] = override
            return self

        self._roads.append(Road(**kwargs).to_intent())
        return self

    def _base_cell(self):
        if hasattr(self.fill, "base_cell") and callable(self.fill.base_cell):
            return self.fill.base_cell()
        if hasattr(self.fill, "to_cell") and callable(self.fill.to_cell):
            return dict(self.fill.to_cell())
        if isinstance(self.fill, dict):
            return dict(self.fill)
        raise ValueError("TableGrid fill 必须是 TableTemplate、Table、dict 或兼容对象。")

    def _cell_for(self, row, col):
        cell = deepcopy(self._base_cell())
        cell.setdefault("role", "table")
        cell.setdefault("align", "center")
        cell["id"] = f"t{row + 1}{col + 1}"

        overrides = deepcopy(self._placements.get((row, col), {}))
        if "align" in overrides:
            overrides["align"] = str(overrides["align"]).lower().strip() or "center"
        cell.update(overrides)
        return cell

    def to_matrix(self):
        """Build an OrderAnalyzer-compatible matrix of concrete table cells."""
        return [
            [self._cell_for(row, col) for col in range(self.cols)]
            for row in range(self.rows)
        ]

    def to_layout(self):
        """Return matrix plus road intents without changing legacy to_matrix()."""
        return {
            "matrix": self.to_matrix(),
            # Copy each intent so callers cannot mutate TableGrid internals.
            "roads": self._expanded_roads(),
        }

    def _expanded_roads(self):
        roads = [dict(road) for road in self._roads]
        if not self._road_network_defaults:
            return roads

        for axis, max_index in (("vertical", self.cols), ("horizontal", self.rows)):
            for index in range(max_index + 1):
                config = dict(self._road_network_defaults)
                config.update(self._road_axis_overrides.get((axis, index), {}))
                if not config.get("enabled", True):
                    continue
                width = float(config.get("width", 80.0))
                min_clearance = config.get("min_clearance")
                if min_clearance is None:
                    min_clearance = width
                road_id = str(config.get("id", "")).strip() or f"road.{axis}.{index}"
                intent = Road(
                    id=road_id,
                    axis=axis,
                    between=(max(0, index - 1), index),
                    width=width,
                    min_clearance=float(min_clearance),
                    offset=float(config.get("offset", 0.0)),
                    level=str(config.get("level", "primary")),
                    priority=int(config.get("priority", 0)),
                    serves=config.get("serves"),
                ).to_intent()
                # index is a semantic grid-line coordinate; between is kept for
                # compatibility with the older single-road API.
                intent["index"] = index
                intent["enabled"] = True
                roads.append(intent)
        return roads


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
        """Convert to OrderAnalyzer-compatible cell dict。"""
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
