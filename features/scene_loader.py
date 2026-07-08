from __future__ import annotations

from math import cos, radians, sin
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .affordance.models import Rect


SVG_NS = "{http://www.w3.org/2000/svg}"


def load_structured_svg_scene(path: str | Path) -> dict:
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
        "column_axes": [],
        "regions": [],
        "uncertainties": [],
    }
    _walk(root, inherited={"_allow_id_fallback": not _has_data_roles(root)}, scene=scene)
    return scene


def _has_data_roles(root: ET.Element) -> bool:
    """Return whether an SVG already carries explicit role metadata."""
    return any("data-role" in element.attrib for element in root.iter())


def _svg_size(root: ET.Element) -> tuple[float, float]:
    view_box = root.attrib.get("viewBox", "")
    parts = [float(part) for part in view_box.replace(",", " ").split() if part]
    if len(parts) == 4:
        return parts[2], parts[3]
    return (
        float(root.attrib.get("width", 0) or 0),
        float(root.attrib.get("height", 0) or 0),
    )


def _walk(element: ET.Element, *, inherited: dict, scene: dict) -> None:
    meta = _merge_metadata(inherited, element.attrib)
    tag = _tag_name(element.tag)
    transform = _combine_transform(inherited.get("_transform"), element.attrib.get("transform"))
    meta["_transform"] = transform

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
        scene["boundaries"].append(record)
    elif role == "opening":
        scene["entries"].append(record)
    elif role == "region":
        scene["regions"].append(record)
    elif role == "path":
        scene["paths"].append(record)
    elif role in {"column", "column_axis", "column_grid"}:
        scene["column_axes"].append(record)
    else:
        scene["objects"].append(record)


def _merge_metadata(inherited: dict, attrib: dict) -> dict:
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
    role = meta.get("data-role")
    if not role and meta.get("_allow_id_fallback"):
        role = _role_from_id(attrib.get("id") or meta.get("id"), tag)
    if not role:
        return None
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
    return {
        "id": attrib.get("id") or meta.get("id") or role,
        "role": role,
        "group": group,
        "region": region,
        "order_view": meta.get("data-order-view"),
        "rect": _rect_for_shape(tag, attrib, meta.get("_transform")),
        "points": _points_for_shape(tag, attrib, meta.get("_transform")),
        "weights": _weights(meta),
        "tag": tag,
        "metadata": metadata,
        "adapter_refs": _adapter_refs(metadata),
    }


def _role_from_id(record_id: str | None, tag: str) -> str | None:
    """Infer a conservative role from an id-only SVG fixture element."""
    if not record_id:
        return None
    lowered = record_id.lower()
    if lowered.startswith("region_"):
        return None
    if "entry" in lowered:
        return "opening"
    if "column_axis" in lowered:
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
    tx, ty, angle = transform or (0.0, 0.0, 0.0)
    if tag == "use":
        x = _svg_number(attrib.get("x"))
        y = _svg_number(attrib.get("y"))
        width = _svg_number(attrib.get("width"))
        height = _svg_number(attrib.get("height"))
        cx, cy = _transform_point(x + width / 2, y + height / 2, tx, ty, angle)
        return Rect(cx=cx, cy=cy, width=width, height=height)
    if tag == "rect":
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


def _points_for_path(
    raw: str,
    transform: tuple[float, float, float] | None,
) -> list[tuple[float, float]]:
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
            if lower == "m" and start is None:
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
        elif lower == "z":
            if start is not None:
                x, y = start
                points.append(_transform_point(x, y, tx, ty, angle))
            command = ""
        else:
            break
    return points


def _combine_transform(
    parent: tuple[float, float, float] | None,
    raw: str | None,
) -> tuple[float, float, float]:
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
    if abs(angle) < 1e-9:
        return x + tx, y + ty
    theta = radians(angle)
    return x * cos(theta) - y * sin(theta) + tx, x * sin(theta) + y * cos(theta) + ty


def _tag_name(tag: str) -> str:
    return tag[len(SVG_NS):] if tag.startswith(SVG_NS) else tag
