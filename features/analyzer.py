"""
Order analyzer wrapper around the OCTA toolbox.

Input:
    actual_matrix  : 2D list of dicts, e.g.
                     [
                       [{"shape": "rect", "attr": "zone_A"}, {"shape": "circle", "attr": "zone_B"}],
                       [{"shape": "rect", "attr": "zone_A"}, {"shape": "rect",   "attr": "zone_A"}],
                     ]
    ideal_matrix   : same structure, defines the expected (fully ordered) pattern.
                     If None, only shape-agnostic metrics are available.
    spacing        : (row_spacing, col_spacing) in your unit. Default (100, 100).
    features       : which features to include in order calculation.
                     Subset of ["shapes", "custom_attr"].
                     Default ["shapes"].

Output:
    calculate_order() -> float in [0.0, 1.0]
                         1.0 = perfectly matches ideal
                         0.0 = every cell deviates from ideal
"""

import sys
import os
import math

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "OCTA_toolbox-master")
)

from octa.patterns import GridPattern
from octa.shapes import Rectangle, Ellipse
from octa.measurements import Order

from .affordance.evaluator import evaluate_spatial_access
from .affordance.geometry import build_affordance_bands
from .affordance.models import (
    ClearanceBand,
    Furniture,
    Rect,
    RoadBand,
    SceneModel,
)
from .schema import (
    CELL_DEFAULTS,
    CELL_REQUIRED_KEYS,
    FEATURE_TO_OCTA,
    ROLE_FROM_SHAPE,
    SCHEMA_VERSION,
    normalize_features,
    normalize_matrix,
    to_distinction_features,
    validate_matrix_shape,
)
from .math_utils import (
    angle_diff_deg,
    centroid,
    clip01,
    dominant_axis_score,
    flat,
    mean,
    spacing_to_xy,
    variance,
)
from .layout import (
    _build_grid,
    _parse_size,
    _resolve_cell_boundingbox,
    _resolve_grid_geometry,
)


def _offset_tuple(cell):
    """Read per-cell position offset from offset/x_offset/y_offset fields."""
    ox = 0.0
    oy = 0.0

    raw = cell.get("offset")
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        try:
            ox = float(raw[0])
            oy = float(raw[1])
        except (TypeError, ValueError):
            ox, oy = 0.0, 0.0

    try:
        ox = float(cell.get("x_offset", ox))
    except (TypeError, ValueError):
        pass

    try:
        oy = float(cell.get("y_offset", oy))
    except (TypeError, ValueError):
        pass

    return (ox, oy)


def _extract_layout_input(value):
    """Accept either a legacy matrix or a layout dict with road intents."""
    if isinstance(value, dict) and "matrix" in value:
        return value["matrix"], [dict(road) for road in value.get("roads", [])]
    return value, []


def _has_explicit_offset(cell):
    return (
        "offset" in cell
        or "x_offset" in cell
        or "y_offset" in cell
    )


SHAPE_MAP = {
    "rect": Rectangle,
    "rectangle": Rectangle,
    "square": Rectangle,
    "circle": Ellipse,
    "ellipse": Ellipse,
    "round": Ellipse,
}


def _apply_matrix(stim, matrix, n_rows, n_cols, cell_size=None, size_scale=1.0):
    """Project matrix attributes into OCTA patterns (shape/classlabel/orientation)."""
    flat_cells = flat(matrix)

    shapes = [
        SHAPE_MAP.get(cell.get("shape", "").lower(), Rectangle) for cell in flat_cells
    ]
    attrs = [str(cell.get("attr", "")) for cell in flat_cells]
    orientations = [cell.get("orientation", 0) for cell in flat_cells]

    stim.shapes = GridPattern.RepeatAcrossElements(shapes, n_rows=n_rows, n_cols=n_cols)
    stim.classlabels = GridPattern.RepeatAcrossElements(
        attrs, n_rows=n_rows, n_cols=n_cols
    )
    stim.orientations = GridPattern.RepeatAcrossElements(
        orientations, n_rows=n_rows, n_cols=n_cols
    )
    explicit_sizes = [_resolve_cell_boundingbox(cell, None) for cell in flat_cells]
    has_explicit_size = any(size is not None for size in explicit_sizes)

    if cell_size is not None or has_explicit_size:
        default_size = _parse_size(cell_size) or (10.0, 10.0)
        sizes = []
        for cell, explicit_size in zip(flat_cells, explicit_sizes):
            size = explicit_size
            if size is None:
                size = _resolve_cell_boundingbox(cell, default_size)
            resolved = size or default_size
            sizes.append((resolved[0] * size_scale, resolved[1] * size_scale))
        stim.boundingboxes = GridPattern.RepeatAcrossElements(
            sizes, n_rows=n_rows, n_cols=n_cols
        )
    return stim


class OrderAnalyzer:
    def __init__(
        self,
        actual_matrix,
        ideal_matrix=None,
        spacing=(100, 100),
        cell_size=None,
        layout_size=None,
        fit_to_layout=False,
        unit_scale=1.0,
    ):
        """Initialize analyzer with actual/ideal matrices and spatial settings。"""
        actual_matrix, actual_roads = _extract_layout_input(actual_matrix)
        ideal_matrix, ideal_roads = _extract_layout_input(ideal_matrix)
        self.road_intents = actual_roads
        self.ideal_road_intents = ideal_roads

        validate_matrix_shape(actual_matrix, "actual_matrix")
        self.actual_matrix = normalize_matrix(actual_matrix)

        if ideal_matrix is not None:
            validate_matrix_shape(ideal_matrix, "ideal_matrix")
            if len(ideal_matrix) != len(actual_matrix) or len(ideal_matrix[0]) != len(
                actual_matrix[0]
            ):
                raise ValueError("ideal_matrix 与 actual_matrix 的行列尺寸必须一致。")
            self.ideal_matrix = normalize_matrix(ideal_matrix)
        else:
            self.ideal_matrix = None

        self.n_rows = len(actual_matrix)
        self.n_cols = len(actual_matrix[0])
        self.n_cells = self.n_rows * self.n_cols

        self.layout_size = layout_size
        self.fit_to_layout = fit_to_layout
        self.unit_scale = float(unit_scale)

        self.spacing, self.stim_size = _resolve_grid_geometry(
            n_rows=self.n_rows,
            n_cols=self.n_cols,
            spacing=spacing,
            layout_size=self.layout_size,
            fit_to_layout=self.fit_to_layout,
            unit_scale=self.unit_scale,
        )
        self.cell_size = cell_size

        self._stim = None

    def _cell_span(self):
        if self.stim_size is not None and self.fit_to_layout:
            return (
                float(self.stim_size[1]) / self.n_rows,
                float(self.stim_size[0]) / self.n_cols,
            )
        return self.spacing

    def _alignment_offset(self, cell, resolved_size):
        """Translate user-level cell alignment into a center offset."""
        if _has_explicit_offset(cell):
            return _offset_tuple(cell)

        align = str(cell.get("align", "center")).lower().strip()
        if align == "right":
            _, cell_w = self._cell_span()
            return (max(0.0, (cell_w - resolved_size[0]) / 2.0), 0.0)
        return (0.0, 0.0)

    def _schema_info(self):
        """Expose frozen input schema contract for downstream users/tools。"""
        return {
            "version": SCHEMA_VERSION,
            "required": list(CELL_REQUIRED_KEYS),
            "defaults": dict(CELL_DEFAULTS),
        }

    def _semantic_grid(self):
        """Build semantic-layer view (role/group grids + counts) from normalized matrix。"""
        role_grid = []
        group_grid = []
        role_counts = {}
        group_counts = {}

        for row in self.actual_matrix:
            role_row = []
            group_row = []
            for cell in row:
                role = cell["role"] or ROLE_FROM_SHAPE.get(cell["shape"], "unknown")
                group = cell["group"]

                role_row.append(role)
                group_row.append(group)

                role_counts[role] = role_counts.get(role, 0) + 1
                group_counts[group] = group_counts.get(group, 0) + 1

            role_grid.append(role_row)
            group_grid.append(group_row)

        return {
            "role_grid": role_grid,
            "group_grid": group_grid,
            "role_counts": role_counts,
            "group_counts": group_counts,
        }

    def _extract_objects(self):
        """Flatten cells and build semantic objects for relation scoring."""
        objects = []
        for r, row in enumerate(self.actual_matrix):
            for c, cell in enumerate(row):
                shape = str(cell.get("shape", "")).lower()
                role = str(cell.get("role", "")).lower().strip()
                if not role:
                    # role fallback: use shape heuristics when schema omits explicit role
                    role = ROLE_FROM_SHAPE.get(shape, "unknown")

                obj = {
                    "id": f"r{r}_c{c}",
                    "row": r,
                    "col": c,
                    "xy": spacing_to_xy(r, c, self.spacing),
                    "shape": shape,
                    "role": role,
                    "attr": str(cell.get("attr", "")),
                    "orientation": float(cell.get("orientation", 0.0)),
                    "group": str(cell.get("group", "global")),
                }
                objects.append(obj)
        return objects

    def _build_scene_model(self):
        """Convert normalized analyzer cells into affordance spatial entities."""
        entities = []
        default_size = _parse_size(self.cell_size)
        if default_size is None:
            base = float(min(self.spacing)) if min(self.spacing) > 0 else 10.0
            default_size = (base * 0.5, base * 0.5)

        for r, row in enumerate(self.actual_matrix):
            for c, cell in enumerate(row):
                if self.stim_size is not None and self.fit_to_layout:
                    cell_w = float(self.stim_size[0]) / self.n_cols
                    cell_h = float(self.stim_size[1]) / self.n_rows
                    cx = (c + 0.5) * cell_w
                    cy = (r + 0.5) * cell_h
                else:
                    cx, cy = spacing_to_xy(r, c, self.spacing)
                size = _resolve_cell_boundingbox(cell, default_size) or default_size
                offset_x, offset_y = self._alignment_offset(cell, size)
                cx += offset_x
                cy += offset_y
                shape = str(cell.get("shape", "")).lower()
                role = str(cell.get("role", "")).lower().strip()
                if not role:
                    role = ROLE_FROM_SHAPE.get(shape, "unknown")
                type_id = str(cell.get("type_id", "")).strip() or f"{role}.default"
                entity_id = str(cell.get("id", "")).strip() or f"r{r}_c{c}"

                # SceneModel is the bridge to v2 spatial evaluators. It stays
                # opt-in, so legacy scoring/report semantics are unchanged.
                entities.append(
                    Furniture(
                        id=entity_id,
                        type_id=type_id,
                        role=role,
                        rect=Rect(
                            cx=cx,
                            cy=cy,
                            width=size[0],
                            height=size[1],
                        ),
                        parent_id=str(cell.get("group", "global")),
                        orientation=float(cell.get("orientation", 0.0)),
                        metadata={"row": r, "col": c},
                        affordance=dict(cell.get("affordance", {})),
                        aisle=dict(cell.get("aisle", {})),
                    )
                )

        affordance_bands = build_affordance_bands(entities)
        road_bands, clearance_bands = self._build_road_bands()
        return SceneModel(
            entities=entities,
            affordance_bands=affordance_bands,
            road_bands=road_bands,
            clearance_bands=clearance_bands,
        )

    def _affordance_edge_rect(self, rect, edge, depth):
        """Return external edge band; it moves with the owning furniture bbox."""
        if edge == "top":
            return Rect(rect.cx, rect.top - depth / 2, rect.width, depth)
        if edge == "right":
            return Rect(rect.right + depth / 2, rect.cy, depth, rect.height)
        if edge == "bottom":
            return Rect(rect.cx, rect.bottom + depth / 2, rect.width, depth)
        if edge == "left":
            return Rect(rect.left - depth / 2, rect.cy, depth, rect.height)
        return rect

    def _build_road_bands(self):
        """Convert user Road intents into continuous road/clearance rectangles."""
        road_bands = []
        clearance_bands = []
        if not self.road_intents:
            return road_bands, clearance_bands

        width = (
            float(self.stim_size[0])
            if self.stim_size is not None
            else max(1.0, self.n_cols * self.spacing[1])
        )
        height = (
            float(self.stim_size[1])
            if self.stim_size is not None
            else max(1.0, self.n_rows * self.spacing[0])
        )
        cell_w = width / self.n_cols
        cell_h = height / self.n_rows

        for index, intent in enumerate(self.road_intents):
            axis = str(intent.get("axis", "vertical")).lower().strip() or "vertical"
            between = tuple(intent.get("between", (0, 1)))
            axis_index = intent.get("index")
            road_width = float(intent.get("width", 0.0))
            clearance_width = float(intent.get("min_clearance", road_width))
            offset = float(intent.get("offset", 0.0))
            road_id = str(intent.get("id", "")).strip() or f"road{index + 1}"

            # Road geometry follows semantic cell boundaries. For a vertical
            # road between columns (0, 1), the axis is the boundary x=cell_w.
            if axis == "vertical":
                grid_line = int(axis_index) if axis_index is not None else max(between)
                boundary = (grid_line * cell_w) + offset
                road_rect = Rect(
                    cx=boundary,
                    cy=height / 2,
                    width=road_width,
                    height=height,
                )
                clearance_rect = Rect(
                    cx=boundary,
                    cy=height / 2,
                    width=clearance_width,
                    height=height,
                )
            elif axis == "horizontal":
                grid_line = int(axis_index) if axis_index is not None else max(between)
                boundary = (grid_line * cell_h) + offset
                road_rect = Rect(
                    cx=width / 2,
                    cy=boundary,
                    width=width,
                    height=road_width,
                )
                clearance_rect = Rect(
                    cx=width / 2,
                    cy=boundary,
                    width=width,
                    height=clearance_width,
                )
            else:
                # Unknown axis is ignored instead of crashing report(); Road
                # validation prevents this in the public API path.
                continue

            metadata = {
                "axis": axis,
                "between": between,
                "index": axis_index,
                "offset": offset,
                "source": "Road",
            }
            road_bands.append(
                RoadBand(
                    id=road_id,
                    rect=road_rect,
                    axis=axis,
                    level=str(intent.get("level", "primary")),
                    priority=int(intent.get("priority", 0)),
                    metadata=dict(metadata),
                )
            )
            clearance_bands.append(
                ClearanceBand(
                    id=f"{road_id}.clearance",
                    road_id=road_id,
                    rect=clearance_rect,
                    required_width=clearance_width,
                    metadata=dict(metadata),
                )
            )

        return road_bands, clearance_bands

    def _score_relations(self, objects):
        """Score chair-table relations using distance, bearing, orientation and count."""
        chairs = [o for o in objects if o["role"] == "chair"]
        tables = [o for o in objects if o["role"] == "table"]

        if not chairs or not tables:
            # 无法形成 chair-table pair 时, rel 记为 None 并在 total 里自动重归一化
            return {
                "rel": None,
                "subscores": {
                    "distance": None,
                    "bearing": None,
                    "orientation": None,
                    "quantity": None,
                    "assignment": None,
                },
                "counts": {"chairs": len(chairs), "tables": len(tables)},
            }

        row_spacing, col_spacing = self.spacing
        base_step = (
            float(min(row_spacing, col_spacing))
            if min(row_spacing, col_spacing) > 0
            else 1.0
        )

        per_chair_distance = []
        per_chair_bearing = []
        per_chair_orientation = []
        chair_to_table = {}

        for chair in chairs:
            cx, cy = chair["xy"]

            nearest_table = None
            nearest_dist = None
            for table in tables:
                tx, ty = table["xy"]
                d = math.hypot(tx - cx, ty - cy)
                if nearest_dist is None or d < nearest_dist:
                    nearest_dist = d
                    nearest_table = table

            # greedy nearest assignment: MVP 先求稳定可解释, 后续可替换 Hungarian/global matching
            chair_to_table[chair["id"]] = nearest_table["id"]

            target = base_step
            # distance score peaks near one grid step; tolerate under/over spacing symmetrically
            dist_score = 1.0 - min(abs(nearest_dist - target) / max(target, 1e-6), 1.0)
            per_chair_distance.append(clip01(dist_score))

            tx, ty = nearest_table["xy"]
            angle = math.degrees(math.atan2(ty - cy, tx - cx)) % 360.0
            per_chair_bearing.append(dominant_axis_score(angle))

            ori = chair["orientation"] % 360.0
            # facing score: 0 deg diff best, 90 deg diff roughly zero
            facing_diff = angle_diff_deg(ori, angle)
            per_chair_orientation.append(clip01(1.0 - facing_diff / 90.0))

        table_counts = {t["id"]: 0 for t in tables}
        for table_id in chair_to_table.values():
            table_counts[table_id] += 1

        quantity_scores = []
        for count in table_counts.values():
            # soft band for chair count per table: ideal range [2, 8]
            if 2 <= count <= 8:
                quantity_scores.append(1.0)
            elif count < 2:
                quantity_scores.append(clip01(count / 2.0))
            else:
                quantity_scores.append(clip01(1.0 - (count - 8) / 8.0))

        assignment_score = 1.0
        distance_score = mean(per_chair_distance)
        bearing_score = mean(per_chair_bearing)
        orientation_score = mean(per_chair_orientation)
        quantity_score = mean(quantity_scores)

        weights = {
            # default relation weights for MVP; keep deterministic before data-driven calibration
            "distance": 0.35,
            "bearing": 0.20,
            "orientation": 0.25,
            "quantity": 0.10,
            "assignment": 0.10,
        }
        rel_score = (
            weights["distance"] * distance_score
            + weights["bearing"] * bearing_score
            + weights["orientation"] * orientation_score
            + weights["quantity"] * quantity_score
            + weights["assignment"] * assignment_score
        )

        return {
            "rel": clip01(rel_score),
            "subscores": {
                "distance": round(distance_score, 4),
                "bearing": round(bearing_score, 4),
                "orientation": round(orientation_score, 4),
                "quantity": round(quantity_score, 4),
                "assignment": round(assignment_score, 4),
            },
            "counts": {"chairs": len(chairs), "tables": len(tables)},
        }

    def _score_intra(self, objects):
        """Compute intra-group consistency from orientation + role composition."""
        groups = {}
        for obj in objects:
            groups.setdefault(obj["group"], []).append(obj)

        per_group = {}
        for group_id, members in groups.items():
            if not members:
                per_group[group_id] = 1.0
                continue

            angles = [math.radians(m["orientation"] % 360.0) for m in members]
            # circular consistency: resultant length in [0,1], higher means orientations align better
            cos_mean = mean([math.cos(a) for a in angles])
            sin_mean = mean([math.sin(a) for a in angles])
            orientation_consistency = math.hypot(cos_mean, sin_mean)

            roles = [m["role"] for m in members if m["role"] != "unknown"]
            if roles:
                # role consistency: dominant-role ratio, simple but robust for mixed inputs
                dominant_count = max(roles.count(role) for role in set(roles))
                role_consistency = dominant_count / len(roles)
            else:
                role_consistency = 1.0

            per_group[group_id] = clip01(
                (orientation_consistency + role_consistency) / 2.0
            )

        intra = mean(list(per_group.values())) if per_group else 1.0
        return clip01(intra), {k: round(v, 4) for k, v in per_group.items()}

    def _score_inter(self, objects):
        """Compute inter-group alignment from dominant direction and phase spacing."""
        groups = {}
        for obj in objects:
            groups.setdefault(obj["group"], []).append(obj)

        if len(groups) <= 1:
            return 1.0, {"orientation_alignment": 1.0, "phase_alignment": 1.0}

        centroids = {}
        dominant_angles = {}
        for gid, members in groups.items():
            pts = [m["xy"] for m in members]
            centroids[gid] = centroid(pts)

            angles = [math.radians(m["orientation"] % 360.0) for m in members]
            cos_mean = mean([math.cos(a) for a in angles])
            sin_mean = mean([math.sin(a) for a in angles])
            # each group represented by one dominant orientation for inter-group comparison
            dominant_angles[gid] = (
                math.degrees(math.atan2(sin_mean, cos_mean)) + 360.0
            ) % 360.0

        gids = list(groups.keys())
        pair_diffs = []
        for i in range(len(gids)):
            for j in range(i + 1, len(gids)):
                d = angle_diff_deg(dominant_angles[gids[i]], dominant_angles[gids[j]])
                pair_diffs.append(d)

        orientation_alignment = clip01(
            1.0 - (mean(pair_diffs) / 90.0 if pair_diffs else 0.0)
        )

        xs = [centroids[g][0] for g in gids]
        ys = [centroids[g][1] for g in gids]
        axis = "x" if (variance(xs) or 0.0) >= (variance(ys) or 0.0) else "y"

        projected = sorted(xs if axis == "x" else ys)
        if len(projected) < 3:
            phase_alignment = 1.0
        else:
            gaps = [projected[i + 1] - projected[i] for i in range(len(projected) - 1)]
            gap_mean = mean(gaps)
            if gap_mean <= 1e-6:
                phase_alignment = 0.0
            else:
                # phase alignment via inverse CV: uniform spacing => high score
                cv = math.sqrt(variance(gaps)) / gap_mean
                phase_alignment = clip01(1.0 / (1.0 + cv))

        inter = clip01((orientation_alignment + phase_alignment) / 2.0)
        details = {
            "orientation_alignment": round(orientation_alignment, 4),
            "phase_alignment": round(phase_alignment, 4),
        }
        return inter, details

    def calculate_components(self, features=("shapes",), total_weights=None):
        """Return component scores for MVP implementation."""
        base_order = self.calculate_order(features)
        objects = self._extract_objects()

        rel_result = self._score_relations(objects)
        intra_score, intra_groups = self._score_intra(objects)
        inter_score, inter_details = self._score_inter(objects)

        if total_weights is None:
            # component weights for v1; can be replaced by profile-based configs later
            total_weights = {
                "base_order": 0.35,
                "intra": 0.25,
                "inter": 0.25,
                "rel": 0.15,
            }

        parts = {
            "base_order": base_order,
            "intra": intra_score,
            "inter": inter_score,
            "rel": rel_result["rel"],
        }

        valid = {k: v for k, v in parts.items() if v is not None}
        # Some components may be unavailable; renormalize to keep total in comparable scale
        weight_sum = sum(total_weights.get(k, 0.0) for k in valid.keys())
        if weight_sum <= 1e-9:
            total = 0.0
        else:
            total = (
                sum((total_weights.get(k, 0.0) * v) for k, v in valid.items())
                / weight_sum
            )

        return {
            "scores": {
                "base_order": round(base_order, 4),
                "intra": round(intra_score, 4),
                "inter": round(inter_score, 4),
                "rel": (
                    None if rel_result["rel"] is None else round(rel_result["rel"], 4)
                ),
                "total": round(clip01(total), 4),
            },
            "details": {
                "intra_groups": intra_groups,
                "inter": inter_details,
                "relation": rel_result,
            },
            "weights": total_weights,
        }

    def _prepare(self):
        """Build ideal stimulus and inject actual deviations for OCTA deviant counting."""
        if self.ideal_matrix is None:
            raise ValueError(
                "ideal_matrix が必要です: 理想模式未定义，无法计算 order。"
            )

        stim, n_rows, n_cols = _build_grid(
            self.ideal_matrix,
            self.spacing,
            stim_size=self.stim_size,
            center_fit=self.fit_to_layout,
        )
        stim = _apply_matrix(
            stim,
            self.ideal_matrix,
            n_rows,
            n_cols,
            self.cell_size,
            size_scale=self.unit_scale,
        )

        flat_actual = flat(self.actual_matrix)
        flat_ideal = flat(self.ideal_matrix)

        for i, (actual_cell, ideal_cell) in enumerate(zip(flat_actual, flat_ideal)):
            actual_shape = SHAPE_MAP.get(
                actual_cell.get("shape", "").lower(), Rectangle
            )
            ideal_shape = SHAPE_MAP.get(ideal_cell.get("shape", "").lower(), Rectangle)
            if actual_shape != ideal_shape:
                stim.set_element_shape(i, actual_shape)

            actual_attr = str(actual_cell.get("attr", ""))
            ideal_attr = str(ideal_cell.get("attr", ""))
            if actual_attr != ideal_attr:
                stim.set_element_classlabel(i, actual_attr)

            actual_ori = actual_cell.get("orientation", 0)
            ideal_ori = ideal_cell.get("orientation", 0)
            if actual_ori != ideal_ori:
                stim.set_element_orientation(i, actual_ori)

        element_ids = []
        x_offsets = []
        y_offsets = []
        for i, (actual_cell, ideal_cell) in enumerate(zip(flat_actual, flat_ideal)):
            default_size = _parse_size(self.cell_size) or (
                min(self.spacing[1], 100.0) * 0.5,
                min(self.spacing[0], 100.0) * 0.5,
            )
            actual_size = _resolve_cell_boundingbox(actual_cell, default_size) or default_size
            ideal_size = _resolve_cell_boundingbox(ideal_cell, default_size) or default_size
            actual_offset = self._alignment_offset(actual_cell, actual_size)
            ideal_offset = self._alignment_offset(ideal_cell, ideal_size)
            delta_x = actual_offset[0] - ideal_offset[0]
            delta_y = actual_offset[1] - ideal_offset[1]
            if abs(delta_x) > 1e-9 or abs(delta_y) > 1e-9:
                element_ids.append(i)
                x_offsets.append(delta_x)
                y_offsets.append(delta_y)

        if element_ids:
            stim.positions.SetPositionDeviations(
                element_id=element_ids,
                x_offset=x_offsets,
                y_offset=y_offsets,
            )

        self._stim = stim

    def _feature_value(self, cell, feature):
        """Return normalized comparable value for cell-level boolean deviance check。"""
        if feature == "shapes":
            return SHAPE_MAP.get(str(cell.get("shape", "")).lower(), Rectangle)
        if feature == "custom_attr":
            return str(cell.get("attr", ""))
        if feature == "orientations":
            return cell.get("orientation", 0)
        if feature == "positions":
            default_size = _parse_size(self.cell_size) or (
                min(self.spacing[1], 100.0) * 0.5,
                min(self.spacing[0], 100.0) * 0.5,
            )
            size = _resolve_cell_boundingbox(cell, default_size) or default_size
            return self._alignment_offset(cell, size)
        return None

    def _calculate_deviance_breakdown(self, features):
        """Build deviance details: OCTA feature counts + per-cell boolean deviance map."""
        normalized = normalize_features(features)
        distinction = to_distinction_features(normalized)

        if not normalized:
            raise ValueError("features 至少需要包含可识别的维度。")

        # OCTA-first: compute per-feature deviant counts by invoking OCTA once per feature.
        feature_deviants = {}
        for f in normalized:
            if f in FEATURE_TO_OCTA:
                octa_f = FEATURE_TO_OCTA[f]
                count = Order.CalculatePatternDeviants(self._stim, [octa_f])
                feature_deviants[f] = {
                    "count": int(count),
                    "ratio": round(count / self.n_cells, 4),
                }
            elif f == "positions":
                count = Order.CalculatePositionDeviants(self._stim)
                feature_deviants[f] = {
                    "count": int(count),
                    "ratio": round(count / self.n_cells, 4),
                }

        # Minimal local addition: OCTA exposes counts but not per-cell boolean map.
        cell_flags_flat = []
        flat_actual = flat(self.actual_matrix)
        flat_ideal = flat(self.ideal_matrix)
        for actual_cell, ideal_cell in zip(flat_actual, flat_ideal):
            is_deviant = False
            for f in normalized:
                if self._feature_value(actual_cell, f) != self._feature_value(
                    ideal_cell, f
                ):
                    is_deviant = True
                    break
            cell_flags_flat.append(1 if is_deviant else 0)

        deviance_cells = []
        deviance_matrix = []
        for r in range(self.n_rows):
            row_flags = []
            for c in range(self.n_cols):
                idx = r * self.n_cols + c
                flag = cell_flags_flat[idx]
                row_flags.append(flag)
                if flag == 1:
                    deviance_cells.append({"row": r, "col": c})
            deviance_matrix.append(row_flags)

        return {
            "feature_deviants": feature_deviants,
            "deviance_matrix": deviance_matrix,
            "deviance_cells": deviance_cells,
        }

    def calculate_order(self, features=("shapes",)):
        """
        Returns order score in [0.0, 1.0].

        Parameters
        ----------
        features : tuple/list
            Any combination of "shapes" and "custom_attr".
        """
        # Base order keeps original OCTA route for backward compatibility.
        self._prepare()
        self._stim.Render()

        normalized = normalize_features(features)
        distinction = to_distinction_features(normalized)

        if not normalized:
            raise ValueError("features 至少需要包含可识别的维度。")

        if all(f in FEATURE_TO_OCTA for f in normalized):
            deviants = Order.CalculatePatternDeviants(self._stim, distinction)
            return 1.0 - deviants / self.n_cells

        breakdown = self._calculate_deviance_breakdown(normalized)
        deviants = len(breakdown["deviance_cells"])
        return 1.0 - deviants / self.n_cells

    def report(
        self,
        features=("shapes",),
        include_affordance=False,
        affordance_options=None,
    ):
        """返回详细报告 dict。"""
        # `order` is legacy-compatible; `scores/details/weights` are new explainable outputs.
        order = self.calculate_order(features)
        deviants = int(round((1.0 - order) * self.n_cells))
        components = self.calculate_components(features)
        deviance = self._calculate_deviance_breakdown(features)
        semantic = self._semantic_grid()
        result = {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "n_cells": self.n_cells,
            "features": list(features),
            "layout": {
                "spacing": [round(self.spacing[0], 4), round(self.spacing[1], 4)],
                "size": (
                    None
                    if self.stim_size is None
                    else [round(self.stim_size[0], 4), round(self.stim_size[1], 4)]
                ),
                "fit_to_layout": self.fit_to_layout,
                "unit_scale": round(self.unit_scale, 6),
            },
            "schema": self._schema_info(),
            "semantic": semantic,
            "deviants": deviants,
            "order": round(order, 4),
            "deviance_by_feature": deviance["feature_deviants"],
            "deviance_matrix": deviance["deviance_matrix"],
            "deviance_cells": deviance["deviance_cells"],
            "scores": components["scores"],
            "details": components["details"],
            "weights": components["weights"],
        }

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
            spatial_access = evaluate_spatial_access(
                scene,
                width=width,
                height=height,
                resolution=resolution,
            )
            result["affordance"] = spatial_access["affordance"]
            result["aisle"] = spatial_access["aisle"]

        return result
