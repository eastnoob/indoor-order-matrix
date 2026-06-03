"""Layout helpers for fixed-canvas grid geometry and per-cell sizing."""

from octa.Stimulus import Grid
from octa.Positions import Positions

DEFAULT_CIRCLE_SHAPES = {"circle", "round"}


def _parse_size(value):
    """Parse scalar/tuple/dict size input to (width, height)."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        side = float(value)
        return (side, side)

    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            w = float(value[0])
            h = float(value[1])
        except (TypeError, ValueError):
            return None
        if w <= 0 or h <= 0:
            return None
        return (w, h)

    if isinstance(value, dict):
        w = value.get("width", value.get("w"))
        h = value.get("height", value.get("h"))
        if w is None or h is None:
            return None
        try:
            w = float(w)
            h = float(h)
        except (TypeError, ValueError):
            return None
        if w <= 0 or h <= 0:
            return None
        return (w, h)

    return None


def _resolve_cell_boundingbox(cell, default_cell_size=None, circle_shapes=None):
    """Resolve per-cell absolute size; circle defaults to a true circle bbox."""
    circle_shapes = circle_shapes or DEFAULT_CIRCLE_SHAPES
    shape = str(cell.get("shape", "")).lower().strip()

    size = _parse_size(cell.get("size"))
    if size is None:
        size = _parse_size(cell.get("bbox"))

    if size is None:
        diameter = cell.get("diameter")
        radius = cell.get("radius")
        if diameter is not None:
            size = _parse_size(diameter)
        elif isinstance(radius, (int, float)) and radius > 0:
            d = float(radius) * 2.0
            size = (d, d)

    if size is None:
        size = _parse_size(default_cell_size)

    if size is None:
        return None

    w, h = size
    if shape in circle_shapes:
        d = min(w, h)
        return (d, d)
    return (w, h)


def _resolve_grid_geometry(
    n_rows,
    n_cols,
    spacing=(100, 100),
    layout_size=None,
    fit_to_layout=False,
    unit_scale=1.0,
):
    """Resolve grid spacing and fixed stimulus size under optional layout constraints."""
    if unit_scale <= 0:
        raise ValueError("unit_scale 必须大于 0。")

    parsed_spacing = _parse_size(spacing) or (100.0, 100.0)
    row_spacing, col_spacing = parsed_spacing

    stim_size = None
    if layout_size is not None:
        parsed_layout = _parse_size(layout_size)
        if parsed_layout is None:
            raise ValueError("layout_size 必须是正数，或二元尺寸。")

        layout_width, layout_height = parsed_layout
        if fit_to_layout:
            col_spacing = layout_width / n_cols if n_cols > 0 else layout_width
            row_spacing = layout_height / n_rows if n_rows > 0 else layout_height
        stim_size = (layout_width * unit_scale, layout_height * unit_scale)

    scaled_row = max(1, int(round(row_spacing * unit_scale)))
    scaled_col = max(1, int(round(col_spacing * unit_scale)))

    return (scaled_row, scaled_col), stim_size


def _build_grid(matrix, spacing=(100, 100), stim_size=None, center_fit=False):
    """Create OCTA Grid scaffold and optionally shift positions to cell centers."""
    n_rows = len(matrix)
    n_cols = len(matrix[0])
    row_spacing, col_spacing = spacing

    grid_kwargs = {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "row_spacing": row_spacing,
        "col_spacing": col_spacing,
    }
    if stim_size is not None:
        grid_kwargs["size"] = stim_size
        grid_kwargs["x_margin"] = 0
        grid_kwargs["y_margin"] = 0

    stim = Grid(**grid_kwargs)

    if stim_size is not None and center_fit:
        cell_w = float(stim_size[0]) / n_cols
        cell_h = float(stim_size[1]) / n_rows
        xs = []
        ys = []
        for r in range(n_rows):
            for c in range(n_cols):
                xs.append((c + 0.5) * cell_w)
                ys.append((r + 0.5) * cell_h)
        stim.positions = Positions.CreateCustomPositions(xs, ys)

    return stim, n_rows, n_cols
