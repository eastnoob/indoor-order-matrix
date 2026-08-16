from __future__ import annotations

from math import cos, pi, radians, sin, tan
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .affordance.models import Rect


SVG_NS = "{http://www.w3.org/2000/svg}"
_IDENTITY_AFFINE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def load_structured_svg_scene(
    path: str | Path,
    *,
    include_source_order: bool = False,
) -> dict:
    """Load a metadata-bearing SVG fixture into neutral scene records.

    This is not image recognition: geometry meaning comes from explicit
    `data-*` attributes so the same path can later map to Rhino/BIM metadata.
    """
    source = Path(path)
    root = ET.parse(source).getroot()
    scene = {
        "source": str(source),
        "size": _svg_size(root),
        "objects": [],
        "boundaries": [],
        "entries": [],
        "paths": [],
        "columns": [],
        "column_axes": [],
        "regions": [],
        "uncertainties": [],
    }
    if include_source_order:
        # Neutral Scene adapters need cross-bucket source order and authoredness,
        # while the default legacy dictionary must remain byte-for-byte shaped.
        scene["_source_records"] = []
        scene["_next_neutral_id"] = 1
    # SVG fixtures can be partially annotated while they evolve toward BIM-like
    # metadata, so id fallback stays available only for elements missing a role.
    _walk(root, inherited={"_allow_id_fallback": True}, scene=scene)
    return scene


def _svg_size(root: ET.Element) -> tuple[float, float]:
    """Return the SVG viewBox size, falling back to explicit dimensions."""
    view_box = root.attrib.get("viewBox", "")
    parts = [float(part) for part in view_box.replace(",", " ").split() if part]
    if len(parts) == 4:
        return parts[2], parts[3]
    return (
        float(root.attrib.get("width", 0) or 0),
        float(root.attrib.get("height", 0) or 0),
    )


def _walk(element: ET.Element, *, inherited: dict, scene: dict) -> None:
    """Walk SVG elements and route neutral records into scene buckets."""
    meta = _merge_metadata(inherited, element.attrib)
    tag = _tag_name(element.tag)
    transform = _combine_transform(inherited.get("_transform"), element.attrib.get("transform"))
    meta["_transform"] = transform
    if "_source_records" in scene:
        # The adapter handoff keeps a complete affine chain beside the legacy
        # translation/angle approximation, so compatibility values do not move.
        meta["_adapter_affine"] = _compose_svg_affine(
            inherited.get("_adapter_affine"), element.attrib.get("transform")
        )

    if tag == "g" or list(element):
        for child in element:
            _walk(child, inherited=meta, scene=scene)
        if tag == "g" or tag in {"svg", "defs", "style"}:
            return

    record = _shape_record(tag, element.attrib, meta)
    if record is None:
        return
    role = record["role"]
    if role == "boundary":
        bucket = "boundaries"
    elif role == "opening":
        bucket = "entries"
    elif role == "region":
        bucket = "regions"
    elif role == "path":
        bucket = "paths"
    elif role == "column":
        bucket = "columns"
    elif role in {"column_axis", "column_grid"}:
        # Adapter handoff expects authored grid-axis records to use one role.
        record["role"] = "column_axis"
        record["metadata"]["role"] = "column_axis"
        bucket = "column_axes"
    else:
        bucket = "objects"
    scene[bucket].append(record)
    if "_source_records" in scene:
        # Raw data-* keys distinguish authored facts from compatibility defaults
        # without asking the adapter to traverse XML a second time.
        record["_authored_metadata_keys"] = tuple(
            key[5:] for key in meta if key.startswith("data-")
        )
        record["_authored_metadata"] = {
            key[5:]: value for key, value in meta.items() if key.startswith("data-")
        }
        source_id = element.attrib.get("id")
        neutral_index = scene["_next_neutral_id"]
        scene["_next_neutral_id"] += 1
        record["_source_id"] = source_id
        record["_neutral_id"] = source_id or f"svg-element-{neutral_index:06d}"
        geometry, geometry_error = _adapter_geometry_for_shape(
            tag,
            element.attrib,
            meta["_adapter_affine"],
        )
        record["_adapter_geometry"] = geometry
        record["_adapter_geometry_error"] = geometry_error
        scene["_source_records"].append((bucket, record))


def _merge_metadata(inherited: dict, attrib: dict) -> dict:
    """Merge inherited SVG data attributes while tracking semantic parent ids."""
    meta = dict(inherited)
    previous_id = inherited.get("id")
    for key, value in attrib.items():
        if key.startswith("data-") or key == "id":
            meta[key] = value
    if attrib.get("id"):
        if _semantic_group_id(previous_id):
            meta["_semantic_parent_id"] = previous_id
        else:
            meta["_semantic_parent_id"] = inherited.get("_semantic_parent_id")
    return meta


def _shape_record(tag: str, attrib: dict, meta: dict) -> dict | None:
    """Convert one SVG element into a neutral scene record when it has a role."""
    role = meta.get("data-role")
    if not role and meta.get("_allow_id_fallback"):
        role = _role_from_id(attrib.get("id") or meta.get("id"), tag)
    if not role:
        return None
    _tx, _ty, orientation = meta.get("_transform") or (0.0, 0.0, 0.0)
    group = meta.get("data-group") or _group_from_id(meta.get("_semantic_parent_id"))
    region = meta.get("data-region", group)
    metadata = {
        key[5:]: value for key, value in meta.items() if key.startswith("data-")
    }
    if "role" not in metadata:
        metadata["role"] = role
    if "group" not in metadata:
        metadata["group"] = group
    if "region" not in metadata:
        metadata["region"] = region
    if "orientation" not in metadata:
        metadata["orientation"] = str(round(orientation % 360.0, 4))
    furniture_group = (
        meta.get("data-furniture-group")
        or meta.get("data-furniture-group-id")
        or metadata.get("furniture-group")
        or metadata.get("furniture-group-id")
        or group
    )
    if "furniture-group" not in metadata:
        metadata["furniture-group"] = furniture_group
    rect = _rect_for_shape(tag, attrib, meta.get("_transform"))
    points = _points_for_shape(tag, attrib, meta.get("_transform"))
    if abs(orientation) < 1e-9 and points:
        # Path-authored furniture often has no transform matrix, so recover its
        # usable frame from the longest polygon edge instead of treating it as
        # globally horizontal.
        orientation = _points_orientation(points)
        metadata["orientation"] = str(round(orientation % 360.0, 4))
    elif abs(orientation) < 1e-9 and tag == "rect":
        # Some exported SVGs encode object orientation as a plain vertical rect
        # inside an id-bearing group, with no transform matrix or polygon path.
        orientation = _rect_aspect_orientation(attrib)
        metadata["orientation"] = str(round(orientation % 360.0, 4))
        if orientation:
            points = _plain_rect_points(attrib)
    if role in {"column_axis", "column_grid"}:
        # Column axes are authored grid centerlines. Filled/dashed SVG paths may
        # carry many outline points, so collapse line-like bboxes before metrics.
        points = _compact_axis_points(points, rect)
    return {
        "id": attrib.get("id") or meta.get("id") or role,
        "role": role,
        "group": group,
        "region": region,
        "furniture_group": furniture_group,
        "orientation": orientation % 360.0,
        "order_view": meta.get("data-order-view"),
        "rect": rect,
        "points": points,
        "weights": _weights(meta),
        "tag": tag,
        "metadata": metadata,
        "adapter_refs": _adapter_refs(metadata),
    }


def _compact_axis_points(
    points: list[tuple[float, float]],
    rect: Rect,
) -> list[tuple[float, float]]:
    """Return centerline points for line-like authored axes."""
    if len(points) < 3:
        return points
    if rect.height > rect.width * 5:
        return [(rect.cx, rect.top), (rect.cx, rect.bottom)]
    if rect.width > rect.height * 5:
        return [(rect.left, rect.cy), (rect.right, rect.cy)]
    return _dedupe_consecutive_points(points)


def _dedupe_consecutive_points(
    points: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Remove duplicate adjacent vertices introduced by explicit path closing."""
    deduped = []
    for point in points:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    return deduped


def _role_from_id(record_id: str | None, tag: str) -> str | None:
    """Infer a conservative role from an id-only SVG fixture element."""
    if not record_id:
        return None
    lowered = record_id.lower()
    if lowered.endswith("_group") or "_group_" in lowered:
        # Furniture-group containers are semantic scopes, not furniture objects.
        # Children without their own ids must not inherit a group id as a role.
        return None
    if lowered.startswith("region_"):
        return None
    if "entry" in lowered:
        return "opening"
    if "column_axis" in lowered:
        return "column_axis"
    # SVG fixtures use an "axis" group for authored grid axes; this is explicit
    # fixture metadata, not geometric axis inference from columns.
    if tag in {"line", "path", "polygon"} and (
        lowered == "axis" or re.fullmatch(r"axis\d+", lowered)
    ):
        return "column_axis"
    if tag == "use" and "room_boundary" in lowered:
        return "boundary"
    if "piler" in lowered or "piller" in lowered or "pller" in lowered:
        return "column"
    if "boundary" in lowered:
        return "boundary"
    for role in ("armchair", "chair", "sofa", "table", "plant"):
        if role in lowered:
            return role
    return None


def _group_from_id(parent_id: str | None) -> str:
    """Use parent SVG group ids as semantic group keys when data-group is absent."""
    if not parent_id:
        return "global"
    return parent_id


def _semantic_group_id(record_id: str | None) -> bool:
    """Return whether an SVG group id names a furniture activity group."""
    if not record_id:
        return False
    lowered = record_id.lower()
    if lowered.endswith("_group") or "_group_" in lowered:
        return False
    return lowered in {
        "north_tables",
        "west_lounge",
        "center_lounge",
        "east_armchairs",
        "east_work",
    }


def _adapter_refs(metadata: dict) -> dict[str, str]:
    """Collect explicit external-system references from SVG metadata aliases."""
    aliases = {
        "rhino_guid": ("rhino-guid", "rhino_guid"),
        "ifc_guid": ("ifc-guid", "ifc_guid"),
        "visualarq_id": ("visualarq-id", "visualarq_id"),
        "source_layer": ("source-layer", "source_layer"),
        "source_id": ("source-id", "source_id"),
    }
    refs = {}
    for key, names in aliases.items():
        value = next((metadata[name] for name in names if metadata.get(name)), None)
        if value:
            refs[key] = value
    return refs


def _weights(meta: dict) -> dict[str, float]:
    """Build legacy compatibility weights from explicit metadata or role defaults."""
    role = meta.get("data-role", "")
    defaults = {
        "boundary": (1.0, 1.0, 1.0),
        "opening": (0.0, 0.0, 0.0),
        "path": (0.0, 0.0, 0.0),
    }.get(role, (0.0, 0.0, 0.0))
    return {
        "walk_block": _weight(meta.get("data-walk-block"), defaults[0]),
        "see_block": _weight(meta.get("data-see-block"), defaults[1]),
        "grouping_strength": _weight(meta.get("data-grouping-strength"), defaults[2]),
    }


def _weight(raw: str | None, default: float) -> float:
    """Clamp one legacy compatibility weight to the inclusive unit interval."""
    if raw is None:
        return default
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return default


def _rect_for_shape(
    tag: str,
    attrib: dict,
    transform: tuple[float, float, float] | None,
) -> Rect:
    """Build the legacy axis-aligned rectangle proxy for one SVG shape."""
    tx, ty, angle = transform or (0.0, 0.0, 0.0)
    if tag == "use":
        x = _svg_number(attrib.get("x"))
        y = _svg_number(attrib.get("y"))
        width = _svg_number(attrib.get("width"))
        height = _svg_number(attrib.get("height"))
        cx, cy = _transform_point(x + width / 2, y + height / 2, tx, ty, angle)
        return Rect(cx=cx, cy=cy, width=width, height=height)
    if tag == "rect":
        points = _points_for_shape(tag, attrib, transform)
        if points:
            return _rect_from_points(points)
        x = float(attrib.get("x", 0) or 0)
        y = float(attrib.get("y", 0) or 0)
        width = float(attrib.get("width", 0) or 0)
        height = float(attrib.get("height", 0) or 0)
        cx, cy = _transform_point(x + width / 2, y + height / 2, tx, ty, angle)
        return Rect(cx=cx, cy=cy, width=width, height=height)
    if tag in {"circle", "ellipse"}:
        cx = float(attrib.get("cx", 0) or 0)
        cy = float(attrib.get("cy", 0) or 0)
        if tag == "circle":
            radius = float(attrib.get("r", 0) or 0)
            width = height = radius * 2
        else:
            width = 2 * float(attrib.get("rx", 0) or 0)
            height = 2 * float(attrib.get("ry", 0) or 0)
        cx, cy = _transform_point(cx, cy, tx, ty, angle)
        return Rect(cx=cx, cy=cy, width=width, height=height)
    if tag == "path":
        # ponytail: bbox-only path parser for fixture evidence; use a real SVG path parser once path geometry drives metrics.
        points = _points_for_shape(tag, attrib, transform)
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            return Rect(
                cx=(min(xs) + max(xs)) / 2,
                cy=(min(ys) + max(ys)) / 2,
                width=max(xs) - min(xs),
                height=max(ys) - min(ys),
            )
    if tag == "polygon":
        points = _points_for_shape(tag, attrib, transform)
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            return Rect(
                cx=(min(xs) + max(xs)) / 2,
                cy=(min(ys) + max(ys)) / 2,
                width=max(xs) - min(xs),
                height=max(ys) - min(ys),
            )
    if tag == "line":
        x1 = float(attrib.get("x1", 0) or 0)
        y1 = float(attrib.get("y1", 0) or 0)
        x2 = float(attrib.get("x2", 0) or 0)
        y2 = float(attrib.get("y2", 0) or 0)
        p1 = _transform_point(x1, y1, tx, ty, angle)
        p2 = _transform_point(x2, y2, tx, ty, angle)
        return Rect(
            cx=(p1[0] + p2[0]) / 2,
            cy=(p1[1] + p2[1]) / 2,
            width=abs(p2[0] - p1[0]),
            height=abs(p2[1] - p1[1]),
        )
    return Rect(cx=tx, cy=ty, width=0.0, height=0.0)


def _points_for_shape(
    tag: str,
    attrib: dict,
    transform: tuple[float, float, float] | None,
) -> list[tuple[float, float]]:
    """Return legacy world points using the compatibility transform model."""
    tx, ty, angle = transform or (0.0, 0.0, 0.0)
    if tag == "path":
        return _points_for_path(attrib.get("d", ""), transform)
    if tag == "use":
        rect = _rect_for_shape(tag, attrib, transform)
        return [
            (rect.left, rect.top),
            (rect.right, rect.top),
            (rect.right, rect.bottom),
            (rect.left, rect.bottom),
            (rect.left, rect.top),
        ]
    if tag == "rect":
        if abs(angle) < 1e-9:
            return []
        x = float(attrib.get("x", 0) or 0)
        y = float(attrib.get("y", 0) or 0)
        width = float(attrib.get("width", 0) or 0)
        height = float(attrib.get("height", 0) or 0)
        # Rect corners preserve rotation for downstream neutral geometry.
        points = [
            _transform_point(x, y, tx, ty, angle),
            _transform_point(x + width, y, tx, ty, angle),
            _transform_point(x + width, y + height, tx, ty, angle),
            _transform_point(x, y + height, tx, ty, angle),
        ]
        return [*points, points[0]]
    if tag == "line":
        x1 = float(attrib.get("x1", 0) or 0)
        y1 = float(attrib.get("y1", 0) or 0)
        x2 = float(attrib.get("x2", 0) or 0)
        y2 = float(attrib.get("y2", 0) or 0)
        return [
            _transform_point(x1, y1, tx, ty, angle),
            _transform_point(x2, y2, tx, ty, angle),
        ]
    raw = attrib.get("points", "")
    if tag != "polygon" or not raw:
        return []
    numbers = [float(value) for value in re.findall(r"[-+]?\d*\.?\d+", raw)]
    return [
        _transform_point(numbers[i], numbers[i + 1], tx, ty, angle)
        for i in range(0, len(numbers) - 1, 2)
    ]


def _rect_from_points(points: list[tuple[float, float]]) -> Rect:
    """Return the axis-aligned bbox around transformed SVG points."""
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return Rect(
        cx=(left + right) / 2,
        cy=(top + bottom) / 2,
        width=right - left,
        height=bottom - top,
    )


def _points_for_path(
    raw: str,
    transform: tuple[float, float, float] | None,
) -> list[tuple[float, float]]:
    """Extract transformed path vertices that are enough for bbox/axis evidence."""
    if not raw:
        return []
    tx, ty, angle = transform or (0.0, 0.0, 0.0)
    tokens = re.findall(r"[MLHVACQSZmlhvacqsz]|[-+]?\d*\.?\d+", raw)
    index = 0
    command = ""
    x = y = 0.0
    start: tuple[float, float] | None = None
    points: list[tuple[float, float]] = []
    while index < len(tokens):
        if re.fullmatch(r"[MLHVACQSZmlhvacqsz]", tokens[index]):
            command = tokens[index]
            index += 1
        if not command:
            break
        lower = command.lower()
        relative = command.islower()
        if lower in {"m", "l"}:
            if index + 1 >= len(tokens):
                break
            nx = float(tokens[index])
            ny = float(tokens[index + 1])
            index += 2
            x, y = (x + nx, y + ny) if relative else (nx, ny)
            if lower == "m":
                # Each moveto starts a new subpath; closepath must return to
                # that local start so repeated dashed path segments accumulate.
                start = (x, y)
            points.append(_transform_point(x, y, tx, ty, angle))
            if lower == "m":
                command = "l" if relative else "L"
        elif lower == "h":
            if index >= len(tokens):
                break
            nx = float(tokens[index])
            index += 1
            x = x + nx if relative else nx
            points.append(_transform_point(x, y, tx, ty, angle))
        elif lower == "v":
            if index >= len(tokens):
                break
            ny = float(tokens[index])
            index += 1
            y = y + ny if relative else ny
            points.append(_transform_point(x, y, tx, ty, angle))
        elif lower == "a":
            if index + 6 >= len(tokens):
                break
            nx = float(tokens[index + 5])
            ny = float(tokens[index + 6])
            index += 7
            x, y = (x + nx, y + ny) if relative else (nx, ny)
            points.append(_transform_point(x, y, tx, ty, angle))
        elif lower == "c":
            if index + 5 >= len(tokens):
                break
            nx = float(tokens[index + 4])
            ny = float(tokens[index + 5])
            index += 6
            # Cubic control points shape the curve, but the endpoint is enough
            # for authored dashed grid axes and downstream bbox/angle evidence.
            x, y = (x + nx, y + ny) if relative else (nx, ny)
            points.append(_transform_point(x, y, tx, ty, angle))
        elif lower == "z":
            if start is not None:
                x, y = start
                points.append(_transform_point(x, y, tx, ty, angle))
            command = ""
        else:
            break
    return _dedupe_consecutive_points(points)


def _points_orientation(points: list[tuple[float, float]]) -> float:
    """Infer a conservative object orientation from the longest point edge."""
    from math import atan2, degrees

    if len(points) < 2:
        return 0.0
    best_length = 0.0
    best_angle = 0.0
    for start, end in zip(points, points[1:]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = dx * dx + dy * dy
        if length > best_length:
            best_length = length
            best_angle = degrees(atan2(dy, dx)) % 180.0
    return best_angle


def _rect_aspect_orientation(attrib: dict) -> float:
    """Infer orientation for untransformed rects whose aspect carries direction."""
    width = float(attrib.get("width", 0) or 0)
    height = float(attrib.get("height", 0) or 0)
    return 90.0 if height > width else 0.0


def _plain_rect_points(attrib: dict) -> list[tuple[float, float]]:
    """Return corners for an untransformed rect that still carries orientation."""
    x = float(attrib.get("x", 0) or 0)
    y = float(attrib.get("y", 0) or 0)
    width = float(attrib.get("width", 0) or 0)
    height = float(attrib.get("height", 0) or 0)
    points = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
    ]
    return [*points, points[0]]


def _adapter_geometry_for_shape(
    tag: str,
    attrib: dict,
    transform: tuple[float, float, float, float, float, float],
) -> tuple[dict | None, str | None]:
    """Build factual world-space geometry for the opt-in Neutral Scene handoff."""
    if tag == "rect":
        x = _svg_number(attrib.get("x"))
        y = _svg_number(attrib.get("y"))
        width = _svg_number(attrib.get("width"))
        height = _svg_number(attrib.get("height"))
        points = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
        return _adapter_geometry("authored_rect", points, transform, polygonal=True), None
    if tag in {"circle", "ellipse"}:
        cx = _svg_number(attrib.get("cx"))
        cy = _svg_number(attrib.get("cy"))
        if tag == "circle":
            rx = ry = _svg_number(attrib.get("r"))
            source = "analytic_circle"
        else:
            rx = _svg_number(attrib.get("rx"))
            ry = _svg_number(attrib.get("ry"))
            source = "analytic_ellipse"
        # A fixed deterministic tessellation preserves the analytic outline
        # without claiming that the SVG supplied a four-corner bbox polygon.
        points = tuple(
            (
                cx + rx * cos(2.0 * pi * index / 64.0),
                cy + ry * sin(2.0 * pi * index / 64.0),
            )
            for index in range(64)
        )
        return _adapter_geometry(source, points, transform, polygonal=True), None
    if tag == "polygon":
        numbers = [
            float(value)
            for value in re.findall(
                r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", attrib.get("points", "")
            )
        ]
        if len(numbers) < 6 or len(numbers) % 2:
            return None, "invalid_polygon_points"
        points = tuple(zip(numbers[0::2], numbers[1::2]))
        return _adapter_geometry("authored_polygon", points, transform, polygonal=True), None
    if tag == "line":
        points = (
            (_svg_number(attrib.get("x1")), _svg_number(attrib.get("y1"))),
            (_svg_number(attrib.get("x2")), _svg_number(attrib.get("y2"))),
        )
        return _adapter_geometry("authored_line", points, transform, polygonal=False), None
    if tag == "path":
        return _adapter_path_geometry(attrib.get("d", ""), transform)
    if tag == "use":
        return None, "unresolved_use_reference"
    return None, f"unsupported_svg_tag:{tag or 'unknown'}"


def _adapter_geometry(
    source: str,
    points: tuple[tuple[float, float], ...],
    transform: tuple[float, float, float, float, float, float],
    *,
    polygonal: bool,
) -> dict:
    """Apply one composed affine transform and package adapter-only geometry."""
    return {
        "points": tuple(_apply_affine(point, transform) for point in points),
        "polygonal": polygonal,
        "geometry_source": source,
        "world_affine": transform,
    }


def _adapter_path_geometry(
    raw: str,
    transform: tuple[float, float, float, float, float, float],
) -> tuple[dict | None, str | None]:
    """Tessellate authored SVG path segments for the adapter-only handoff."""
    if not raw.strip():
        return None, "empty_path"
    try:
        from svgpathtools import Line, parse_path

        parsed = parse_path(raw)
        subpaths = parsed.continuous_subpaths()
    except (ImportError, ValueError, TypeError) as error:
        return None, f"path_parse_failed:{type(error).__name__}"
    if not subpaths:
        return None, "empty_path"

    points: list[tuple[float, float]] = []
    curved = False
    for subpath in subpaths:
        for segment in subpath:
            steps = 1 if isinstance(segment, Line) else 16
            curved = curved or steps > 1
            start = segment.point(0.0)
            start_point = (float(start.real), float(start.imag))
            if not points or start_point != points[-1]:
                points.append(start_point)
            for index in range(1, steps + 1):
                point = segment.point(index / steps)
                points.append((float(point.real), float(point.imag)))
    closed = len(subpaths) == 1 and bool(subpaths[0].isclosed())
    geometry = _adapter_geometry(
        "svg_path_curve" if curved else "svg_path_polyline",
        tuple(points),
        transform,
        polygonal=closed,
    )
    geometry["subpath_count"] = len(subpaths)
    return geometry, None


def _compose_svg_affine(
    parent: tuple[float, float, float, float, float, float] | None,
    raw: str | None,
) -> tuple[float, float, float, float, float, float]:
    """Compose one complete SVG transform list beneath its parent transform."""
    local = _IDENTITY_AFFINE
    if raw:
        matches = list(re.finditer(r"([A-Za-z]+)\s*\(([^)]*)\)", raw))
        compact_matches = "".join(match.group(0) for match in matches)
        if not matches or re.sub(r"[\s,]+", "", compact_matches) != re.sub(
            r"[\s,]+", "", raw
        ):
            raise ValueError(f"unsupported SVG transform syntax: {raw!r}")
        for match in matches:
            values = [
                float(value)
                for value in re.findall(
                    r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", match.group(2)
                )
            ]
            local = _multiply_affine(
                local, _svg_transform_operation(match.group(1), values)
            )
    return _multiply_affine(parent or _IDENTITY_AFFINE, local)


def _svg_transform_operation(
    name: str,
    values: list[float],
) -> tuple[float, float, float, float, float, float]:
    """Return one standard SVG affine operation as a six-value matrix."""
    lowered = name.lower()
    if lowered == "matrix" and len(values) == 6:
        return tuple(values)
    if lowered == "translate" and len(values) in {1, 2}:
        return (
            1.0,
            0.0,
            0.0,
            1.0,
            values[0],
            values[1] if len(values) == 2 else 0.0,
        )
    if lowered == "scale" and len(values) in {1, 2}:
        return (values[0], 0.0, 0.0, values[-1], 0.0, 0.0)
    if lowered == "rotate" and len(values) in {1, 3}:
        angle = radians(values[0])
        rotation = (cos(angle), sin(angle), -sin(angle), cos(angle), 0.0, 0.0)
        if len(values) == 1:
            return rotation
        cx, cy = values[1:]
        return _multiply_affine(
            _multiply_affine(
                (1.0, 0.0, 0.0, 1.0, cx, cy),
                rotation,
            ),
            (1.0, 0.0, 0.0, 1.0, -cx, -cy),
        )
    if lowered in {"skewx", "skewy"} and len(values) == 1:
        shear = tan(radians(values[0]))
        if lowered == "skewx":
            return (1.0, 0.0, shear, 1.0, 0.0, 0.0)
        return (1.0, shear, 0.0, 1.0, 0.0, 0.0)
    raise ValueError(
        f"unsupported SVG transform operation {name!r} with {len(values)} values"
    )


def _multiply_affine(
    left: tuple[float, float, float, float, float, float],
    right: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    """Multiply SVG affine matrices using column-vector coordinate semantics."""
    la, lb, lc, ld, le, lf = left
    ra, rb, rc, rd, re, rf = right
    return (
        la * ra + lc * rb,
        lb * ra + ld * rb,
        la * rc + lc * rd,
        lb * rc + ld * rd,
        la * re + lc * rf + le,
        lb * re + ld * rf + lf,
    )


def _apply_affine(
    point: tuple[float, float],
    transform: tuple[float, float, float, float, float, float],
) -> tuple[float, float]:
    """Apply one composed SVG affine matrix to a source-space point exactly once."""
    a, b, c, d, e, f = transform
    x, y = point
    return a * x + c * y + e, b * x + d * y + f


def _combine_transform(
    parent: tuple[float, float, float] | None,
    raw: str | None,
) -> tuple[float, float, float]:
    """Combine transforms using the legacy translation-and-angle approximation."""
    tx, ty, angle = parent or (0.0, 0.0, 0.0)
    if not raw:
        return tx, ty, angle
    matrix = re.search(
        r"matrix\(([-0-9.]+),([-0-9.]+),([-0-9.]+),([-0-9.]+),([-0-9.]+),([-0-9.]+)\)",
        raw,
    )
    if matrix:
        a, b, _c, _d, e, f = (float(matrix.group(index)) for index in range(1, 7))
        tx += e
        ty += f
        angle += _matrix_angle(a, b)
        return tx, ty, angle
    translate = re.search(r"translate\(([-0-9.]+)(?:[ ,]+([-0-9.]+))?\)", raw)
    if translate:
        tx += float(translate.group(1))
        ty += float(translate.group(2) or 0)
    rotate = re.search(r"rotate\(([-0-9.]+)\)", raw)
    if rotate:
        angle += float(rotate.group(1))
    return tx, ty, angle


def _matrix_angle(a: float, b: float) -> float:
    """Approximate a transform matrix as rotation for bbox proxy loading."""
    from math import atan2, degrees

    return degrees(atan2(b, a))


def _svg_number(raw: str | None) -> float:
    """Parse SVG numeric attributes that may include units such as px."""
    if raw is None:
        return 0.0
    match = re.search(r"[-+]?\d*\.?\d+", raw)
    return float(match.group(0)) if match else 0.0


def _transform_point(
    x: float,
    y: float,
    tx: float,
    ty: float,
    angle: float,
) -> tuple[float, float]:
    """Apply the legacy translation-and-rotation transform to one point."""
    if abs(angle) < 1e-9:
        return x + tx, y + ty
    theta = radians(angle)
    return x * cos(theta) - y * sin(theta) + tx, x * sin(theta) + y * cos(theta) + ty


def _tag_name(tag: str) -> str:
    """Remove the SVG namespace prefix from an ElementTree tag."""
    return tag[len(SVG_NS):] if tag.startswith(SVG_NS) else tag
