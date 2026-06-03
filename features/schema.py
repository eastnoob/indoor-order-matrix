"""Schema and feature mapping helpers for OrderAnalyzer."""

from collections.abc import Mapping

FEATURE_TO_OCTA = {
    "shapes": "shapes",
    "custom_attr": "classlabels",
    "orientations": "orientations",
}

LOCAL_ONLY_FEATURES = {"positions"}

ROLE_FROM_SHAPE = {
    "rect": "table",
    "rectangle": "table",
    "square": "table",
    "circle": "chair",
    "ellipse": "chair",
    "round": "chair",
}

SCHEMA_VERSION = "v1"
CELL_REQUIRED_KEYS = ("shape",)
CELL_DEFAULTS = {
    "shape": "rect",
    "attr": "",
    "orientation": 0.0,
    "role": "",
    "group": "global",
    "id": "",
    "type_id": "",
    "align": "center",
    "affordance": {},
    "aisle": {},
}


def _coerce_cell_like(cell):
    """Coerce dict-like or domain object input to a plain dict cell。"""
    if isinstance(cell, Mapping):
        return dict(cell)
    if hasattr(cell, "to_cell") and callable(cell.to_cell):
        converted = cell.to_cell()
        if not isinstance(converted, Mapping):
            raise ValueError("cell.to_cell() 必须返回 dict-like 对象。")
        return dict(converted)
    raise ValueError("cell 必须是 dict，或实现 to_cell() 的对象。")


def validate_matrix_shape(matrix, matrix_name):
    """Validate 2D rectangular matrix structure and basic element types。"""
    if not isinstance(matrix, list) or not matrix:
        raise ValueError(f"{matrix_name} 必须是非空二维 list。")
    if not all(isinstance(row, list) and row for row in matrix):
        raise ValueError(f"{matrix_name} 的每一行都必须是非空 list。")

    n_cols = len(matrix[0])
    for r, row in enumerate(matrix):
        if len(row) != n_cols:
            raise ValueError(f"{matrix_name} 必须是规则矩阵: 第 {r} 行列数不一致。")
        for c, cell in enumerate(row):
            try:
                _coerce_cell_like(cell)
            except ValueError as exc:
                raise ValueError(f"{matrix_name}[{r}][{c}] 非法: {exc}") from exc


def normalize_cell(cell):
    """Normalize one cell to frozen schema with defaults and safe value casting。"""
    cell = _coerce_cell_like(cell)
    normalized = dict(CELL_DEFAULTS)
    normalized.update(cell)

    shape = str(normalized.get("shape", "")).lower().strip()
    if not shape:
        shape = CELL_DEFAULTS["shape"]
    normalized["shape"] = shape

    normalized["attr"] = str(normalized.get("attr", ""))

    try:
        normalized["orientation"] = float(normalized.get("orientation", 0.0))
    except (TypeError, ValueError):
        normalized["orientation"] = 0.0

    normalized["role"] = str(normalized.get("role", "")).lower().strip()
    normalized["group"] = str(normalized.get("group", CELL_DEFAULTS["group"]))
    if not normalized["group"]:
        normalized["group"] = CELL_DEFAULTS["group"]

    # Spatial v2 fields are preserved but kept optional, so existing v1 inputs
    # remain valid while affordance/aisle evaluators can read explicit IDs.
    normalized["id"] = str(normalized.get("id", ""))
    normalized["type_id"] = str(normalized.get("type_id", ""))
    normalized["align"] = str(normalized.get("align", "center")).lower().strip()
    if not normalized["align"]:
        normalized["align"] = "center"
    if not isinstance(normalized.get("affordance"), dict):
        normalized["affordance"] = {}
    if not isinstance(normalized.get("aisle"), dict):
        normalized["aisle"] = {}

    return normalized


def normalize_matrix(matrix):
    """Normalize full matrix to frozen schema while preserving matrix geometry。"""
    return [[normalize_cell(cell) for cell in row] for row in matrix]


def normalize_features(features):
    """Normalize and filter user-selected features to supported keys。"""
    if features is None:
        features = ("shapes",)
    normalized = []
    for feature in features:
        if (
            feature in FEATURE_TO_OCTA or feature in LOCAL_ONLY_FEATURES
        ) and feature not in normalized:
            normalized.append(feature)
    return normalized


def to_distinction_features(features):
    """Translate public feature names to OCTA distinction feature names。"""
    normalized = normalize_features(features)
    return [FEATURE_TO_OCTA[f] for f in normalized if f in FEATURE_TO_OCTA]
