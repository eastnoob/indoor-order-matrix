"""GPU-only region outlines with no Blender marker objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


_RECORDS: tuple[Mapping[str, object], ...] = ()
_PREVIEW: Mapping[str, object] | None = None
_CANDIDATE_PREVIEWS: tuple[Mapping[str, object], ...] = ()
_SELECTED_ID: str | None = None
_HANDLERS: list[object] = []


def _record_rings(record: Mapping[str, object]) -> tuple[tuple, tuple]:
    """Read plain or GeoJSON polygon rings without replacing geometry by a hull."""
    outline = record.get("outline", ())
    holes = record.get("holes", ())
    if isinstance(outline, Mapping):
        coordinates = outline.get("coordinates", ())
        if outline.get("type") == "Polygon":
            return (tuple(coordinates[0]),), tuple(tuple(ring) for ring in coordinates[1:])
        if outline.get("type") == "MultiPolygon" and coordinates:
            polygon = coordinates[0]
            return (tuple(polygon[0]),), tuple(tuple(ring) for ring in polygon[1:])
    return tuple(outline), tuple(holes) if isinstance(holes, (tuple, list)) else ()


def build_line_data(records: Iterable[Mapping[str, object]], *, selected_id: str | None = None,
                    preview: Mapping[str, object] | None = None,
                    candidate_previews: Iterable[Mapping[str, object]] = (),
                    lift: float = 0.02) -> dict[str, object]:
    """Flatten plane-local polygon rings into lifted world-space GPU segments."""
    vertices, indices, styles = [], [], []
    candidate_items = tuple(candidate_previews)
    all_records = list(records) + ([preview] if preview is not None else []) + list(candidate_items)
    for record in all_records:
        selected = record.get("region_id") == selected_id
        preview_item = record is preview or record in candidate_items
        origin = tuple(record.get("plane_origin", (0.0, 0.0, 0.0)))
        basis = tuple(tuple(axis) for axis in record.get(
            "plane_basis", ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))))
        if len(origin) != 3 or len(basis) != 3 or any(len(axis) != 3 for axis in basis):
            raise ValueError("region record contains invalid plane facts")
        x_axis, y_axis, normal = basis
        outline, holes = _record_rings(record)
        for ring in outline + holes:
            start = len(vertices)
            vertices.extend(tuple(
                float(origin[index]) + float(point[0]) * float(x_axis[index])
                + float(point[1]) * float(y_axis[index]) + float(lift) * float(normal[index])
                for index in range(3)) for point in ring)
            for index in range(len(ring) - 1):
                indices.append((start + index, start + index + 1))
                styles.append({"selected": selected, "preview": preview_item})
    return {"vertices": tuple(vertices), "indices": tuple(indices), "styles": tuple(styles)}


def set_records(records: Iterable[Mapping[str, object]], *, selected_id: str | None = None,
                preview: Mapping[str, object] | None = None,
                candidate_previews: Iterable[Mapping[str, object]] = ()) -> None:
    """Replace the rebuildable GPU cache without changing authoritative records."""
    global _RECORDS, _SELECTED_ID, _PREVIEW, _CANDIDATE_PREVIEWS
    _RECORDS = tuple(records)
    _SELECTED_ID = selected_id
    _PREVIEW = preview
    _CANDIDATE_PREVIEWS = tuple(candidate_previews)


def set_candidate_previews(candidates: Iterable[Mapping[str, object]]) -> None:
    """Replace transient eye-enabled candidate outlines without creating Blender data."""
    global _CANDIDATE_PREVIEWS
    _CANDIDATE_PREVIEWS = tuple(candidates)


def _draw(context=None):
    """Draw cached region segments in the current 3D view."""
    import gpu
    import bpy
    from gpu_extras.batch import batch_for_shader

    # Blender can keep a draw handler alive after the originating window closes;
    # resolve the active context at draw time instead of retaining stale UI state.
    context = getattr(bpy, "context", None) or context
    if context is None or getattr(context, "region", None) is None:
        return
    data = build_line_data(_RECORDS, selected_id=_SELECTED_ID, preview=_PREVIEW,
                           candidate_previews=_CANDIDATE_PREVIEWS)
    if not data["vertices"]:
        return
    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    shader.bind()
    shader.uniform_float("viewportSize", (context.region.width, context.region.height))
    shader.uniform_float("lineWidth", 2.0)
    groups = {(False, False): [], (True, False): [], (False, True): [], (True, True): []}
    for edge, style in zip(data["indices"], data["styles"]):
        groups[(bool(style["selected"]), bool(style["preview"]))].append(edge)
    for (selected, preview), edges in groups.items():
        if not edges:
            continue
        shader.uniform_float("color", (0.2, 0.8, 1.0, 0.85) if selected else (0.3, 0.9, 0.4, 0.65) if preview else (0.2, 0.65, 1.0, 0.55))
        batch_for_shader(shader, "LINES", {"pos": data["vertices"]}, indices=edges).draw(shader)


def tag_redraw(context) -> None:
    """Request a viewport repaint without touching scene semantics."""
    screen = getattr(getattr(context, "window", None), "screen", None)
    for area in getattr(screen, "areas", ()):
        if getattr(area, "type", None) == "VIEW_3D" and callable(getattr(area, "tag_redraw", None)):
            area.tag_redraw()


def install(context) -> None:
    """Install one POST_VIEW handler, replacing any previous handler."""
    if _HANDLERS:
        return
    uninstall()
    space_data = getattr(context, "space_data", None)
    space_view = space_data if callable(getattr(space_data, "draw_handler_add", None)) else None
    if space_view is None:
        import bpy
        space_view = bpy.types.SpaceView3D
    _HANDLERS.append(space_view.draw_handler_add(_draw, (), "WINDOW", "POST_VIEW"))


def uninstall() -> None:
    """Remove all owned handlers and leave no native data behind."""
    if not _HANDLERS:
        return
    import bpy
    for handler in tuple(_HANDLERS):
        try:
            bpy.types.SpaceView3D.draw_handler_remove(handler, "WINDOW")
        except (AttributeError, ValueError):
            pass
    _HANDLERS.clear()

