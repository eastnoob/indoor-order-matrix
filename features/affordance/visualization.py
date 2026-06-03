from __future__ import annotations

from html import escape
from math import ceil
from typing import Any

from .continuous_conflict import geometry_intersection_polygon
from .models import Polygon, Rect
from .models import SceneModel


def _matrix_from_report(report: dict[str, Any], section: str, key: str) -> list[list[int]]:
    """Read a debug matrix from report; missing layers render as empty overlays."""
    return report.get(section, {}).get("debug", {}).get(key, [])


def _fmt(value: float) -> str:
    """Keep SVG data attributes stable while avoiding noisy float tails."""
    return f"{float(value):.1f}"


def _points_attr(points: tuple[tuple[float, float], ...]) -> str:
    """Serialize polygon points for SVG while keeping numeric output stable."""
    return " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in points)


def _cell_rect(
    *,
    row: int,
    col: int,
    resolution: float,
    width: float,
    height: float,
) -> tuple[float, float, float, float]:
    """Map sampled grid index to scene-space rect, clamped at canvas boundary."""
    x = col * resolution
    y = row * resolution
    return x, y, min(resolution, width - x), min(resolution, height - y)


def _draw_sample_layer(
    *,
    parts: list[str],
    matrix: list[list[int]],
    layer: str,
    resolution: float,
    width: float,
    height: float,
    fill: str,
    opacity: float,
) -> None:
    """Draw nonzero sampled cells; these are debug explanations, not geometry."""
    for row, values in enumerate(matrix):
        for col, value in enumerate(values):
            if not value:
                continue
            x, y, w, h = _cell_rect(
                row=row,
                col=col,
                resolution=resolution,
                width=width,
                height=height,
            )
            parts.append(
                f'<rect data-layer="{layer}" data-count="{int(value)}" '
                f'x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(w)}" height="{_fmt(h)}" '
                f'fill="{fill}" opacity="{opacity}"/>'
            )


def _draw_marker_layer(
    *,
    parts: list[str],
    matrix: list[list[int]],
    layer: str,
    resolution: float,
    width: float,
    height: float,
    fill: str,
    opacity: float,
) -> None:
    """Draw conflict as small centered markers so base affordance color remains visible."""
    for row, values in enumerate(matrix):
        for col, value in enumerate(values):
            if not value:
                continue
            x, y, w, h = _cell_rect(
                row=row,
                col=col,
                resolution=resolution,
                width=width,
                height=height,
            )
            marker_w = w * 0.46
            marker_h = h * 0.46
            marker_x = x + (w - marker_w) / 2
            marker_y = y + (h - marker_h) / 2
            parts.append(
                f'<rect data-layer="{layer}" data-count="{int(value)}" '
                f'x="{_fmt(marker_x)}" y="{_fmt(marker_y)}" '
                f'width="{_fmt(marker_w)}" height="{_fmt(marker_h)}" '
                f'fill="{fill}" opacity="{opacity}" stroke="#881337" stroke-width="0.8"/>'
            )


def _draw_entry_layer(
    *,
    parts: list[str],
    matrix: list[list[int]],
    resolution: float,
    width: float,
    height: float,
) -> None:
    """Draw BFS entry cells as boundary arrows; these starts are not road geometry."""
    for row, values in enumerate(matrix):
        for col, value in enumerate(values):
            if not value:
                continue
            x, y, w, h = _cell_rect(
                row=row,
                col=col,
                resolution=resolution,
                width=width,
                height=height,
            )
            mid_y = y + h / 2
            parts.append(
                f'<path data-layer="entry" data-entry="left-boundary" '
                f'd="M {_fmt(x - 15)} {_fmt(mid_y)} L {_fmt(x - 3)} {_fmt(mid_y)} '
                f'M {_fmt(x - 8)} {_fmt(mid_y - 5)} L {_fmt(x - 3)} {_fmt(mid_y)} '
                f'L {_fmt(x - 8)} {_fmt(mid_y + 5)}" '
                f'fill="none" stroke="#0f172a" stroke-width="1.6" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
            )


def _continuous_conflict_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge continuous conflict debug entries from report sections without duplicates."""
    items: list[dict[str, Any]] = []
    seen = set()
    for section in ("aisle", "affordance"):
        for item in report.get(section, {}).get("debug", {}).get("continuous_conflicts", []):
            key = (
                item.get("type"),
                item.get("source_id"),
                item.get("target_id"),
            )
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    return items


def _shape_from_conflict_ref(
    scene: SceneModel,
    *,
    kind: str,
    object_id: str,
) -> Rect | Polygon | None:
    """Resolve report debug IDs back to continuous SceneModel geometry."""
    if kind == "clearance":
        band = scene.clearance_band_by_id.get(object_id)
        return band.rect if band is not None else None
    if kind == "road":
        band = scene.road_band_by_id.get(object_id)
        return band.rect if band is not None else None
    if kind == "affordance":
        band = scene.affordance_band_by_id.get(object_id)
        return (band.polygon or band.rect) if band is not None else None
    if kind == "furniture":
        entity = scene.entity_by_id.get(object_id)
        return (entity.footprint or entity.rect) if entity is not None else None
    return None


def _draw_continuous_conflict_layer(
    *,
    parts: list[str],
    scene: SceneModel,
    report: dict[str, Any],
) -> None:
    """Draw the true continuous overlap area, not sampled-grid conflict markers."""
    for item in _continuous_conflict_items(report):
        source_shape = _shape_from_conflict_ref(
            scene,
            kind=item.get("source_kind", ""),
            object_id=item.get("source_id", ""),
        )
        target_shape = _shape_from_conflict_ref(
            scene,
            kind=item.get("target_kind", ""),
            object_id=item.get("target_id", ""),
        )
        if source_shape is None or target_shape is None:
            continue
        overlap = geometry_intersection_polygon(source_shape, target_shape)
        if overlap is None:
            continue
        parts.append(
            f'<polygon data-layer="continuous-conflict" '
            f'data-conflict-type="{escape(str(item.get("type", "")))}" '
            f'data-source="{escape(str(item.get("source_id", "")))}" '
            f'data-target="{escape(str(item.get("target_id", "")))}" '
            f'points="{_points_attr(overlap.points)}" '
            f'fill="#e11d48" fill-opacity="0.72" '
            f'stroke="#881337" stroke-width="1.2"/>'
        )


def scene_grid_overlay_svg(
    *,
    scene: SceneModel,
    report: dict[str, Any],
    layout_size: tuple[float, float],
    resolution: float,
    title: str = "SVG/OCTA geometry to sampled grid overlay",
) -> str:
    """Render SceneModel bbox and sampled evaluation layers in one SVG coordinate space.

    This helper is intentionally visualization-only: OCTA/SVG stays the visual
    source of truth, SceneModel provides continuous bbox geometry, and debug
    matrices show how SpatialGridBackend sampled that geometry.
    """
    width, height = float(layout_size[0]), float(layout_size[1])
    resolution = float(resolution)
    n_cols = int(ceil(width / resolution))
    n_rows = int(ceil(height / resolution))
    margin_left = 52
    margin_top = 74
    svg_width = width + margin_left + 34
    svg_height = height + margin_top + 72

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(svg_width)}" '
        f'height="{_fmt(svg_height)}" viewBox="0 0 {_fmt(svg_width)} {_fmt(svg_height)}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="18" y="26" font-size="18" font-family="Arial" fill="#111827">{escape(title)}</text>',
        '<text x="18" y="48" font-size="12" font-family="Arial" fill="#374151">'
        'simple reading: green=table body, yellow=affordance, rose markers=conflict; road/clearance are faint reference bands'
        '</text>',
        f'<g transform="translate({_fmt(margin_left)}, {_fmt(margin_top)})">',
    ]

    # Base sampled grid: every cell is drawn so resolution changes are visible.
    for row in range(n_rows):
        for col in range(n_cols):
            x, y, w, h = _cell_rect(
                row=row,
                col=col,
                resolution=resolution,
                width=width,
                height=height,
            )
            parts.append(
                f'<rect data-layer="sample-cell" x="{_fmt(x)}" y="{_fmt(y)}" '
                f'width="{_fmt(w)}" height="{_fmt(h)}" fill="#f8fafc" '
                f'stroke="#e5e7eb" stroke-width="0.4"/>'
            )

    # Reachable is a BFS debug layer. It can change with resolution/occupancy
    # threshold and should not be read as a continuous road surface.
    _draw_sample_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "aisle", "reachable"),
        layer="reachable",
        resolution=resolution,
        width=width,
        height=height,
        fill="#bbf7d0",
        opacity=0.12,
    )
    _draw_entry_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "aisle", "entries"),
        resolution=resolution,
        width=width,
        height=height,
    )
    # Road/clearance/affordance sampled layers explain how continuous bands were
    # rasterized. They are intentionally pale so geometry remains primary.
    _draw_sample_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "aisle", "aisle"),
        layer="aisle",
        resolution=resolution,
        width=width,
        height=height,
        fill="#c4b5fd",
        opacity=0.10,
    )
    _draw_sample_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "aisle", "road"),
        layer="road",
        resolution=resolution,
        width=width,
        height=height,
        fill="#7c3aed",
        opacity=0.10,
    )
    _draw_sample_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "aisle", "clearance"),
        layer="clearance",
        resolution=resolution,
        width=width,
        height=height,
        fill="#fbbf24",
        opacity=0.10,
    )
    _draw_sample_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "affordance", "affordance"),
        layer="affordance",
        resolution=resolution,
        width=width,
        height=height,
        fill="#fde047",
        opacity=0.16,
    )
    _draw_sample_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "affordance", "occupied"),
        layer="occupied",
        resolution=resolution,
        width=width,
        height=height,
        fill="#22c55e",
        opacity=0.12,
    )
    # Conflict layers are drawn last among sampled cells so they stay visible
    # even when the same sampled cell is also occupied or reachable.
    _draw_marker_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "affordance", "conflict"),
        layer="conflict",
        resolution=resolution,
        width=width,
        height=height,
        fill="#e11d48",
        opacity=0.92,
    )
    _draw_marker_layer(
        parts=parts,
        matrix=_matrix_from_report(report, "aisle", "aisle_conflict"),
        layer="aisle_conflict",
        resolution=resolution,
        width=width,
        height=height,
        fill="#e11d48",
        opacity=0.90,
    )
    if not _continuous_conflict_items(report):
        _draw_marker_layer(
            parts=parts,
            matrix=_matrix_from_report(report, "aisle", "clearance_conflict"),
            layer="clearance_conflict",
            resolution=resolution,
            width=width,
            height=height,
            fill="#e11d48",
            opacity=0.88,
        )
    parts.append(
        '<text data-layer="legend" data-kind="affordance_aisle_conflict" x="0" y="-12" font-size="11" '
        'font-family="Arial" fill="#be123c">yellow cells = affordance; rose markers = conflict</text>'
    )

    # Semantic 3x3 grid lines are reference guides, not sampled cells.
    for i in range(4):
        x = width * i / 3
        y = height * i / 3
        parts.append(
            f'<line data-layer="semantic-grid" x1="{_fmt(x)}" y1="0.0" '
            f'x2="{_fmt(x)}" y2="{_fmt(height)}" stroke="#111827" stroke-width="1.5"/>'
        )
        parts.append(
            f'<line data-layer="semantic-grid" x1="0.0" y1="{_fmt(y)}" '
            f'x2="{_fmt(width)}" y2="{_fmt(y)}" stroke="#111827" stroke-width="1.5"/>'
        )

    # Continuous road and clearance bands are drawn before furniture bboxes so
    # the notebook shows geometry first and sampled cells second.
    for band in scene.road_bands:
        rect = band.rect
        parts.append(
            f'<rect data-layer="road-band" data-road="{escape(band.id)}" '
            f'x="{_fmt(rect.left)}" y="{_fmt(rect.top)}" '
            f'width="{_fmt(rect.width)}" height="{_fmt(rect.height)}" '
            f'fill="#7c3aed" opacity="0.05" stroke="#6d28d9" stroke-width="1.2"/>'
        )
    for band in scene.clearance_bands:
        rect = band.rect
        parts.append(
            f'<rect data-layer="clearance-band" data-clearance="{escape(band.id)}" '
            f'x="{_fmt(rect.left)}" y="{_fmt(rect.top)}" '
            f'width="{_fmt(rect.width)}" height="{_fmt(rect.height)}" '
            f'fill="none" stroke="#d97706" stroke-width="1.2" stroke-dasharray="6 4"/>'
        )

    # Continuous affordance bands are furniture-owned geometry, so they are
    # drawn from SceneModel instead of being inferred from sampled grid cells.
    for band in scene.affordance_bands:
        rect = band.rect
        if band.polygon is not None:
            parts.append(
                f'<polygon data-layer="affordance-band" data-affordance="{escape(band.owner_id + ":" + band.edge)}" '
                f'points="{_points_attr(band.polygon.points)}" '
                f'fill="#fde047" fill-opacity="0.70" stroke="#ca8a04" stroke-width="1.4"/>'
            )
        else:
            parts.append(
                f'<rect data-layer="affordance-band" data-affordance="{escape(band.owner_id + ":" + band.edge)}" '
                f'x="{_fmt(rect.left)}" y="{_fmt(rect.top)}" '
                f'width="{_fmt(rect.width)}" height="{_fmt(rect.height)}" '
                f'fill="#fde047" fill-opacity="0.70" stroke="#ca8a04" stroke-width="1.4"/>'
            )

    _draw_continuous_conflict_layer(parts=parts, scene=scene, report=report)

    # SceneModel bbox is the continuous geometry bridge between OCTA and grid.
    for entity in scene.entities:
        rect = entity.rect
        data_bbox = (
            f'{entity.id}:{_fmt(rect.left)},{_fmt(rect.top)},'
            f'{_fmt(rect.right)},{_fmt(rect.bottom)}'
        )
        if entity.footprint is not None:
            parts.append(
                f'<polygon data-layer="bbox" data-bbox="{escape(data_bbox)}" '
                f'points="{_points_attr(entity.footprint.points)}" '
                f'fill="#22c55e" fill-opacity="0.82" stroke="#f97316" stroke-width="2.2"/>'
            )
        else:
            parts.append(
                f'<rect data-layer="bbox" data-bbox="{escape(data_bbox)}" '
                f'x="{_fmt(rect.left)}" y="{_fmt(rect.top)}" '
                f'width="{_fmt(rect.width)}" height="{_fmt(rect.height)}" '
                f'fill="#22c55e" fill-opacity="0.82" stroke="#f97316" stroke-width="2.2"/>'
            )
        label = f"{entity.id} bbox"
        if abs(float(entity.orientation)) > 1e-9:
            label = f"{label} rot={_fmt(entity.orientation)}"
        parts.append(
            f'<text data-layer="bbox-label" x="{_fmt(rect.left)}" y="{_fmt(rect.top - 4)}" '
            f'font-size="11" font-family="Arial" fill="#9a3412">{escape(label)}</text>'
        )

    parts.append("</g>")
    parts.append(
        f'<text x="18" y="{_fmt(svg_height - 22)}" font-size="12" '
        f'font-family="Arial" fill="#111827">resolution={_fmt(resolution)}, '
        f'sample cells={n_rows}x{n_cols}, objects={len(scene.entities)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def resolution_comparison_svg(
    *,
    scene: SceneModel,
    report_a: dict[str, Any],
    report_b: dict[str, Any],
    layout_size: tuple[float, float],
    resolution_a: float,
    resolution_b: float,
) -> str:
    """Place two overlays side by side so bbox stability vs sampling density is visible."""
    left = scene_grid_overlay_svg(
        scene=scene,
        report=report_a,
        layout_size=layout_size,
        resolution=resolution_a,
        title=f"resolution comparison: r={_fmt(resolution_a)}",
    )
    right = scene_grid_overlay_svg(
        scene=scene,
        report=report_b,
        layout_size=layout_size,
        resolution=resolution_b,
        title=f"resolution comparison: r={_fmt(resolution_b)}",
    )
    panel_w = float(layout_size[0]) + 86
    panel_h = float(layout_size[1]) + 146
    # Embed full SVG panels as images via foreignObject-free nested SVG groups.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(panel_w * 2 + 24)}" '
        f'height="{_fmt(panel_h)}" viewBox="0 0 {_fmt(panel_w * 2 + 24)} {_fmt(panel_h)}">'
        f'<g transform="translate(0,0)">{left}</g>'
        f'<g transform="translate({_fmt(panel_w + 24)},0)">{right}</g>'
        "</svg>"
    )
