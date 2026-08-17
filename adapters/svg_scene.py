"""Parse planar SVG source facts into Neutral Scene v2."""

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path
import re
from typing import Iterable, Mapping, MutableMapping
import unicodedata
import xml.etree.ElementTree as ET

if "." in (__package__ or ""):
    from ..features.scene_contract import (
        NEUTRAL_SCENE_V2,
        AnalysisContext,
        AnalysisDomain,
        AnalysisPlane,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MeshGeometry3D,
        NeutralSceneV2,
        SourceObject,
        SourceOpening,
        UncertaintyRecord,
    )
else:
    from features.scene_contract import (
        NEUTRAL_SCENE_V2,
        AnalysisContext,
        AnalysisDomain,
        AnalysisPlane,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MeshGeometry3D,
        NeutralSceneV2,
        SourceObject,
        SourceOpening,
        UncertaintyRecord,
    )


SVG_ADAPTER_VERSION = "svg-scene-adapter/0.4.0"
DEFAULT_GEOMETRY_TOLERANCE = 1e-6
DEFAULT_TOPOLOGY_TOLERANCE = 1e-6

_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
_CSS_WIDE_KEYWORDS = {"inherit", "initial", "revert", "revert-layer", "unset"}
_SIMPLE_FILL_KEYWORDS = {
    "black",
    "blue",
    "currentcolor",
    "gray",
    "green",
    "grey",
    "none",
    "red",
    "transparent",
    "white",
    "yellow",
}

_UNIT_IN_METRES = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
    "in": 0.0254,
    "ft": 0.3048,
}
_FORBIDDEN_METADATA_KEYS = {
    "weights",
    "walk-block",
    "walk_block",
    "see-block",
    "see_block",
    "grouping-strength",
    "grouping_strength",
    "boundary-strength",
    "boundary_strength",
}
_IDENTITY_AFFINE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_SUPPORTED_GEOMETRY_TAGS = {
    "circle",
    "ellipse",
    "line",
    "path",
    "polygon",
    "polyline",
    "rect",
    "use",
}
_FILLABLE_GEOMETRY_TAGS = {"circle", "ellipse", "path", "polygon", "rect"}
_RESOURCE_CONTAINER_TAGS = {
    "clipPath",
    "defs",
    "filter",
    "linearGradient",
    "marker",
    "mask",
    "pattern",
    "radialGradient",
    "symbol",
}
_NON_SOURCE_TAGS = {"defs", "g", "style", "svg", *_RESOURCE_CONTAINER_TAGS}
_PATH_CURVE_SAMPLES = 16
_CURVE_OUTLINE_SEGMENTS = 64


def load_svg_neutral_scene(
    path: str | Path,
    *,
    source_length_unit: str,
    analysis_length_unit: str = "m",
    geometry_tolerance: float = DEFAULT_GEOMETRY_TOLERANCE,
    topology_tolerance: float = DEFAULT_TOPOLOGY_TOLERANCE,
) -> NeutralSceneV2:
    """Load explicit SVG facts into a planar-only Neutral Scene v2 record.

    Physical units are mandatory because SVG viewBox coordinates do not carry
    reliable real-world units. Coordinates are normalized into the requested
    analysis unit while the original y-down convention remains in provenance.
    """
    source = Path(path)
    (width, height), records, document_ids = _parse_svg_source(source)

    # Constructing the context is the contract's authoritative unit and
    # tolerance validation boundary; no viewBox-derived unit guess is allowed.
    context = _analysis_context(
        source_length_unit=source_length_unit,
        analysis_length_unit=analysis_length_unit,
        geometry_tolerance=geometry_tolerance,
        topology_tolerance=topology_tolerance,
        viewbox_size=(width, height),
        coordinate_scale=None,
    )
    scale = _UNIT_IN_METRES[context.source_length_unit] / _UNIT_IN_METRES[
        context.analysis_length_unit
    ]
    context = _analysis_context(
        source_length_unit=source_length_unit,
        analysis_length_unit=analysis_length_unit,
        geometry_tolerance=geometry_tolerance,
        topology_tolerance=topology_tolerance,
        viewbox_size=(width, height),
        coordinate_scale=scale,
    )

    _assign_neutral_ids(records, reserved_ids=set(document_ids))
    _validate_explicit_source_ids(records)
    geometries: list[MeshGeometry3D] = []
    geometry_refs: dict[int, str] = {}
    geometry_warnings: dict[int, tuple[UncertaintyRecord, ...]] = {}
    for bucket, record in records:
        geometry, warnings = _mesh_from_record(
            record,
            scale=scale,
            analysis_length_unit=context.analysis_length_unit,
            source_bucket=bucket,
        )
        geometry_warnings[id(record)] = warnings
        if geometry is not None:
            geometries.append(geometry)
            geometry_refs[id(record)] = geometry.id

    authored_groups, object_group_refs = _authored_groups(record for _, record in records)
    source_ids = {_neutral_id(record) for _, record in records}
    openings, opening_uncertainties = _source_openings(
        (record for _, record in records),
        geometry_refs=geometry_refs,
        valid_object_refs=source_ids,
    )
    opening_refs_by_host: dict[str, list[str]] = defaultdict(list)
    for opening in openings:
        for host_ref in opening.host_refs:
            opening_refs_by_host[host_ref].append(opening.id)

    source_objects = tuple(
        _source_object(
            record,
            source_bucket=bucket,
            geometry_ref=geometry_refs.get(id(record)),
            group_refs=object_group_refs.get(_neutral_id(record), ()),
            opening_refs=tuple(opening_refs_by_host.get(_neutral_id(record), ())),
            geometry_warnings=geometry_warnings.get(id(record), ()),
        )
        for bucket, record in records
    )
    axes, grids = _authored_grids(
        (record for _, record in records), scale=scale
    )
    affordances, affordance_uncertainties = _authored_affordances(
        (record for _, record in records),
        geometry_refs=geometry_refs,
        scale=scale,
        valid_object_refs=source_ids,
    )
    analysis_domain = _analysis_domain(
        (record for _, record in records),
        geometry_refs=geometry_refs,
    )

    _validate_adapter_references(
        source_objects=source_objects,
        geometries=tuple(geometries),
        authored_groups=authored_groups,
        authored_grids=grids,
        authored_grid_axes=axes,
        authored_affordances=affordances,
        openings=openings,
        analysis_domain=analysis_domain,
    )

    return NeutralSceneV2(
        context=context,
        analysis_domain=analysis_domain,
        source_objects=source_objects,
        geometries=tuple(geometries),
        authored_groups=authored_groups,
        authored_grids=grids,
        authored_grid_axes=axes,
        authored_affordances=affordances,
        openings=openings,
        uncertainties=(*affordance_uncertainties, *opening_uncertainties),
    )


def _parse_svg_source(
    path: Path,
) -> tuple[
    tuple[float, float],
    list[tuple[str, dict[str, object]]],
    tuple[str, ...],
]:
    """Parse every supported visible SVG source element in document order."""
    root = ET.parse(path).getroot()
    document_ids, validated_source_ids = _document_ids(root)
    stylesheet_rules, unresolved_stylesheet = _local_stylesheet_rules(
        root,
        external_stylesheet=_has_external_stylesheet(path),
    )
    records: list[tuple[str, dict[str, object]]] = []
    _walk_svg_source(
        root,
        inherited_metadata={},
        inherited_presentation={"fill": "black", "fill-rule": "nonzero"},
        inherited_presentation_unresolved=False,
        parent_affine=_IDENTITY_AFFINE,
        stylesheet_rules=stylesheet_rules,
        unresolved_stylesheet=unresolved_stylesheet,
        validated_source_ids=validated_source_ids,
        records=records,
        inside_resource=False,
        inside_foreign_content=False,
        nested_viewport=False,
        svg_depth=0,
    )
    return _svg_size(root), records, document_ids


def _document_ids(
    root: ET.Element,
) -> tuple[tuple[str, ...], dict[ET.Element, str]]:
    """Collect and validate every explicit SVG id, including resource elements."""
    ids: list[str] = []
    validated_by_element: dict[ET.Element, str] = {}
    first_positions: dict[str, int] = {}
    for position, element in enumerate(root.iter(), start=1):
        if "id" not in element.attrib:
            continue
        source_id = element.attrib["id"]
        if not source_id:
            raise ValueError(f"empty explicit SVG id at document element {position}")
        if (
            any(character.isspace() for character in source_id)
            or unicodedata.normalize("NFC", source_id) != source_id
        ):
            raise ValueError(
                f"invalid explicit SVG id at document element {position}: "
                "ids must be nonempty, whitespace-free, and NFC-normalized"
            )
        if source_id in first_positions:
            raise ValueError(
                f"duplicate explicit SVG source id {source_id!r} "
                f"at document elements {first_positions[source_id]} and {position}"
            )
        first_positions[source_id] = position
        ids.append(source_id)
        validated_by_element[element] = source_id
    return tuple(ids), validated_by_element


def _has_external_stylesheet(path: Path) -> bool:
    """Detect an external XML stylesheet marker without fetching its dependency."""
    return re.search(br"<\?xml-stylesheet\b", path.read_bytes(), re.IGNORECASE) is not None


def _local_stylesheet_rules(
    root: ET.Element,
    *,
    external_stylesheet: bool,
) -> tuple[tuple[dict[str, object], ...], bool]:
    """Parse deterministic tag, class, and id rules that affect SVG fill facts."""
    rules: list[dict[str, object]] = []
    unresolved = external_stylesheet
    order = 0
    for element in root.iter():
        namespace, tag = _tag_identity(element.tag)
        if namespace == _SVG_NAMESPACE and tag == "link":
            rel = element.attrib.get("rel", "").lower().split()
            if "stylesheet" in rel:
                unresolved = True
            continue
        if namespace != _SVG_NAMESPACE or tag != "style":
            continue
        raw = re.sub(r"/\*.*?\*/", "", element.text or "", flags=re.DOTALL)
        if re.search(r"@import\b", raw, re.IGNORECASE):
            unresolved = True
        matches = list(re.finditer(r"([^{}]+)\{([^{}]*)\}", raw))
        remainder = re.sub(r"[^{}]+\{[^{}]*\}", "", raw).strip()
        if remainder and re.search(r"(?:fill|fill-rule)\s*:", raw, re.IGNORECASE):
            unresolved = True
        for match in matches:
            declarations = _inline_style(match.group(2))
            fill_facts = {
                name: value.strip().lower()
                for name, value in declarations.items()
                if name in {"fill", "fill-rule"}
            }
            if not fill_facts:
                continue
            if any(
                not _css_property_value_is_resolved(name, value)
                for name, value in fill_facts.items()
            ):
                unresolved = True
                continue
            for selector in match.group(1).split(","):
                parsed = _simple_selector(selector.strip())
                if parsed is None:
                    unresolved = True
                    continue
                selector_kind, selector_value, specificity = parsed
                rules.append(
                    {
                        "kind": selector_kind,
                        "value": selector_value,
                        "specificity": specificity,
                        "order": order,
                        "declarations": fill_facts,
                    }
                )
                order += 1
    return tuple(rules), unresolved


def _css_property_value_is_resolved(name: str, value: str) -> bool:
    """Return whether a fill property value is safe for local topology decisions."""
    normalized = value.strip().lower()
    if (
        not normalized
        or normalized in _CSS_WIDE_KEYWORDS
        or "!important" in normalized
        or re.search(r"[a-z_-][\w-]*\s*\(", normalized)
    ):
        return False
    if name == "fill-rule":
        return normalized in {"evenodd", "nonzero"}
    return normalized in _SIMPLE_FILL_KEYWORDS or re.fullmatch(
        r"#[0-9a-f]{3}(?:[0-9a-f]{1}|[0-9a-f]{3}|[0-9a-f]{5})?",
        normalized,
    ) is not None


def _simple_selector(selector: str) -> tuple[str, str, int] | None:
    """Parse one local CSS selector without implementing browser selector logic."""
    if re.fullmatch(r"#[A-Za-z_][\w.-]*", selector):
        return "id", selector[1:], 100
    if re.fullmatch(r"\.[A-Za-z_][\w-]*", selector):
        return "class", selector[1:], 10
    if re.fullmatch(r"[A-Za-z_][\w-]*", selector):
        return "tag", selector, 1
    return None


def _walk_svg_source(
    element: ET.Element,
    *,
    inherited_metadata: Mapping[str, object],
    inherited_presentation: Mapping[str, str],
    inherited_presentation_unresolved: bool,
    parent_affine: tuple[float, float, float, float, float, float],
    stylesheet_rules: tuple[dict[str, object], ...],
    unresolved_stylesheet: bool,
    validated_source_ids: Mapping[ET.Element, str],
    records: list[tuple[str, dict[str, object]]],
    inside_resource: bool,
    inside_foreign_content: bool,
    nested_viewport: bool,
    svg_depth: int,
) -> None:
    """Collect source elements while carrying authored metadata and transforms."""
    namespace, tag = _tag_identity(element.tag)
    metadata = dict(inherited_metadata)
    metadata.update(
        {
            key[5:]: value
            for key, value in element.attrib.items()
            if key.startswith("data-")
        }
    )
    presentation, presentation_unresolved = _presentation_facts(
        inherited_presentation,
        element.attrib,
        inherited_unresolved=inherited_presentation_unresolved,
        tag=tag,
        stylesheet_rules=stylesheet_rules,
    )
    affine = _compose_svg_affine(parent_affine, element.attrib.get("transform"))
    in_resource = inside_resource or tag in _RESOURCE_CONTAINER_TAGS
    in_foreign_content = (
        inside_foreign_content
        or namespace != _SVG_NAMESPACE
        or tag == "foreignObject"
    )
    in_nested_viewport = nested_viewport or (
        namespace == _SVG_NAMESPACE and tag == "svg" and svg_depth > 0
    )
    child_svg_depth = (
        svg_depth + 1
        if namespace == _SVG_NAMESPACE and tag == "svg"
        else svg_depth
    )

    # Resource descendants participate in global id integrity but are not
    # ordinary scene geometry until an explicitly supported instance resolves them.
    if (
        not in_resource
        and not in_foreign_content
        and _is_source_element(namespace, tag, metadata)
    ):
        if in_nested_viewport:
            geometry, geometry_error = None, "unsupported_nested_svg_viewport"
        else:
            geometry, geometry_error = _geometry_for_element(
                tag,
                element.attrib,
                affine,
                presentation,
            )
            if (
                (unresolved_stylesheet or presentation_unresolved)
                and tag in _FILLABLE_GEOMETRY_TAGS
                and geometry is not None
            ):
                # Unknown selectors may change fill topology, so retaining only
                # the outline is safer than manufacturing a filled surface.
                geometry["polygonal"] = False
                _append_geometry_uncertainty(
                    geometry,
                    "unresolved_css_presentation",
                )
        records.append(
            (
                "source_elements",
                {
                    "tag": tag,
                    "_source_id": validated_source_ids.get(element),
                    "_source_namespace": namespace,
                    "_authored_metadata": metadata,
                    "_adapter_geometry": geometry,
                    "_adapter_geometry_error": geometry_error,
                    "adapter_refs": _adapter_refs(metadata),
                },
            )
        )

    for child in element:
        _walk_svg_source(
            child,
            inherited_metadata=metadata,
            inherited_presentation=presentation,
            inherited_presentation_unresolved=presentation_unresolved,
            parent_affine=affine,
            stylesheet_rules=stylesheet_rules,
            unresolved_stylesheet=unresolved_stylesheet,
            validated_source_ids=validated_source_ids,
            records=records,
            inside_resource=in_resource,
            inside_foreign_content=in_foreign_content,
            nested_viewport=in_nested_viewport,
            svg_depth=child_svg_depth,
        )


def _is_source_element(
    namespace: str | None,
    tag: str,
    metadata: Mapping[str, object],
) -> bool:
    """Return whether an SVG element should become one Neutral Scene source object."""
    if namespace != _SVG_NAMESPACE:
        return False
    if tag in _SUPPORTED_GEOMETRY_TAGS:
        return True
    return tag not in _NON_SOURCE_TAGS and bool(_optional_text(metadata.get("role")))


def _svg_size(root: ET.Element) -> tuple[float, float]:
    """Return SVG viewBox dimensions without interpreting them as physical units."""
    raw = root.attrib.get("viewBox", "")
    try:
        values = [float(part) for part in re.split(r"[\s,]+", raw.strip()) if part]
    except ValueError:
        values = []
    if len(values) == 4 and all(math.isfinite(value) for value in values):
        return values[2], values[3]
    return _svg_dimension(root.attrib.get("width")), _svg_dimension(
        root.attrib.get("height")
    )


def _svg_dimension(raw: str | None) -> float:
    """Parse one finite SVG dimension while tolerating a presentation unit suffix."""
    if raw is None:
        return 0.0
    match = re.fullmatch(
        r"\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)(?:[A-Za-z%]+)?\s*",
        raw,
    )
    if not match:
        return 0.0
    value = float(match.group(1))
    return value if math.isfinite(value) else 0.0


def _presentation_facts(
    inherited: Mapping[str, str],
    attributes: Mapping[str, str],
    *,
    inherited_unresolved: bool,
    tag: str,
    stylesheet_rules: tuple[dict[str, object], ...],
) -> tuple[dict[str, str], bool]:
    """Resolve inherited, presentation, stylesheet, and inline fill facts."""
    result = dict(inherited)
    unresolved = inherited_unresolved
    priorities = {name: (-1, -1) for name in ("fill", "fill-rule")}
    for name in ("fill", "fill-rule"):
        if name in attributes:
            value = attributes[name].strip().lower()
            if _css_property_value_is_resolved(name, value):
                result[name] = value
                priorities[name] = (0, -1)
            else:
                unresolved = True
    for rule in stylesheet_rules:
        if not _selector_matches(rule, tag, attributes):
            continue
        priority = (int(rule["specificity"]), int(rule["order"]))
        declarations = rule["declarations"]
        if not isinstance(declarations, Mapping):
            continue
        for name, value in declarations.items():
            if priority >= priorities[str(name)]:
                normalized_name = str(name)
                normalized_value = str(value)
                if _css_property_value_is_resolved(normalized_name, normalized_value):
                    result[normalized_name] = normalized_value
                    priorities[normalized_name] = priority
                else:
                    unresolved = True
    style = _inline_style(attributes.get("style"))
    for name in ("fill", "fill-rule"):
        if name in style:
            value = style[name].strip().lower()
            if _css_property_value_is_resolved(name, value):
                result[name] = value
            else:
                unresolved = True
    return result, unresolved


def _selector_matches(
    rule: Mapping[str, object],
    tag: str,
    attributes: Mapping[str, str],
) -> bool:
    """Match one supported simple selector against an SVG element."""
    kind = rule.get("kind")
    value = str(rule.get("value") or "")
    if kind == "tag":
        return tag == value
    if kind == "id":
        return attributes.get("id") == value
    if kind == "class":
        return value in attributes.get("class", "").split()
    return False


def _inline_style(raw: str | None) -> dict[str, str]:
    """Parse the small inline CSS declaration subset needed for SVG fill facts."""
    result: dict[str, str] = {}
    for declaration in (raw or "").split(";"):
        name, separator, value = declaration.partition(":")
        if separator and name.strip() and value.strip():
            result[name.strip().lower()] = value.strip()
    return result


def _geometry_for_element(
    tag: str,
    attributes: Mapping[str, str],
    transform: tuple[float, float, float, float, float, float],
    presentation: Mapping[str, str],
) -> tuple[dict[str, object] | None, str | None]:
    """Extract authored planar geometry without substituting a bounding box."""
    fill = presentation.get("fill", "black")
    fill_rule = presentation.get("fill-rule", "nonzero")
    filled = fill != "none"
    if tag == "rect":
        x = _finite_svg_number(attributes.get("x"), default=0.0)
        y = _finite_svg_number(attributes.get("y"), default=0.0)
        width = _finite_svg_number(attributes.get("width"), default=0.0)
        height = _finite_svg_number(attributes.get("height"), default=0.0)
        if None in {x, y, width, height} or width <= 0.0 or height <= 0.0:
            return None, "invalid_rect_dimensions"
        points = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
        return _geometry_descriptor(
            "authored_rect", points, transform, polygonal=filled, fill=fill, fill_rule=fill_rule
        ), None
    if tag in {"circle", "ellipse"}:
        return _curve_geometry(tag, attributes, transform, fill, fill_rule)
    if tag in {"polygon", "polyline"}:
        points = _points_attribute(attributes.get("points"))
        minimum = 3 if tag == "polygon" else 2
        if points is None or len(points) < minimum:
            error = (
                "invalid_polygon_points"
                if tag == "polygon"
                else "invalid_polyline_points"
            )
            return None, error
        return _geometry_descriptor(
            f"authored_{tag}",
            points,
            transform,
            polygonal=tag == "polygon" and filled,
            fill=fill,
            fill_rule=fill_rule,
        ), None
    if tag == "line":
        values = tuple(
            _finite_svg_number(attributes.get(name), default=0.0)
            for name in ("x1", "y1", "x2", "y2")
        )
        if any(value is None for value in values):
            return None, "invalid_line_coordinates"
        x1, y1, x2, y2 = values
        return _geometry_descriptor(
            "authored_line",
            ((x1, y1), (x2, y2)),
            transform,
            polygonal=False,
            fill="none",
            fill_rule=fill_rule,
        ), None
    if tag == "path":
        return _path_geometry(attributes.get("d", ""), transform, fill, fill_rule)
    if tag == "use":
        return None, "unresolved_use_reference"
    return None, f"unsupported_svg_tag:{tag or 'unknown'}"


def _finite_svg_number(raw: str | None, *, default: float | None) -> float | None:
    """Parse one complete finite SVG number without accepting malformed prefixes."""
    if raw is None:
        return default
    try:
        value = float(raw.strip())
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _points_attribute(raw: str | None) -> tuple[tuple[float, float], ...] | None:
    """Parse a complete SVG points attribute into ordered finite coordinates."""
    if not raw or re.search(r"[^0-9eE+\-.,\s]", raw):
        return None
    try:
        values = [float(value) for value in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw)]
    except ValueError:
        return None
    if len(values) % 2 or not all(math.isfinite(value) for value in values):
        return None
    return tuple(zip(values[0::2], values[1::2]))


def _curve_geometry(
    tag: str,
    attributes: Mapping[str, str],
    transform: tuple[float, float, float, float, float, float],
    fill: str,
    fill_rule: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Tessellate a valid analytic circle or ellipse outline deterministically."""
    cx = _finite_svg_number(attributes.get("cx"), default=0.0)
    cy = _finite_svg_number(attributes.get("cy"), default=0.0)
    if tag == "circle":
        rx = ry = _finite_svg_number(attributes.get("r"), default=None)
        source = "analytic_circle"
    else:
        rx = _finite_svg_number(attributes.get("rx"), default=None)
        ry = _finite_svg_number(attributes.get("ry"), default=None)
        source = "analytic_ellipse"
    if None in {cx, cy, rx, ry} or rx <= 0.0 or ry <= 0.0:
        return None, "invalid_curve_dimensions"
    points = tuple(
        (
            cx + rx * math.cos(2.0 * math.pi * index / _CURVE_OUTLINE_SEGMENTS),
            cy + ry * math.sin(2.0 * math.pi * index / _CURVE_OUTLINE_SEGMENTS),
        )
        for index in range(_CURVE_OUTLINE_SEGMENTS)
    )
    return _geometry_descriptor(
        source,
        points,
        transform,
        polygonal=fill != "none",
        fill=fill,
        fill_rule=fill_rule,
        extra={"curve_segments": _CURVE_OUTLINE_SEGMENTS},
    ), None


def _geometry_descriptor(
    source: str,
    points: Iterable[tuple[float, float]],
    transform: tuple[float, float, float, float, float, float],
    *,
    polygonal: bool,
    fill: str,
    fill_rule: str,
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Apply the composed transform once and package adapter geometry facts."""
    return {
        "points": tuple(_apply_affine(point, transform) for point in points),
        "polygonal": polygonal,
        "geometry_source": source,
        "world_affine": transform,
        "fill": fill,
        "fill_rule": fill_rule,
        **dict(extra or {}),
    }


def _append_geometry_uncertainty(
    descriptor: MutableMapping[str, object],
    code: str,
) -> None:
    """Append one stable geometry uncertainty code without duplicating it."""
    existing = tuple(descriptor.get("geometry_uncertainties") or ())
    if code not in existing:
        descriptor["geometry_uncertainties"] = (*existing, code)


def _path_geometry(
    raw: str,
    transform: tuple[float, float, float, float, float, float],
    fill: str,
    fill_rule: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Sample SVG path curves while refusing ambiguous filled topology."""
    if not raw.strip():
        return None, "empty_path"
    try:
        from svgpathtools import Line, parse_path

        subpaths = parse_path(raw).continuous_subpaths()
    except (ImportError, ValueError, TypeError, IndexError, AssertionError) as error:
        return None, f"path_parse_failed:{type(error).__name__}"
    if not subpaths:
        return None, "empty_path"

    points: list[tuple[float, float]] = []
    subpath_offsets: list[int] = []
    curved = False
    for subpath in subpaths:
        subpath_offsets.append(len(points))
        for segment_index, segment in enumerate(subpath):
            steps = 1 if isinstance(segment, Line) else _PATH_CURVE_SAMPLES
            curved = curved or steps > 1
            if segment_index == 0:
                start = segment.point(0.0)
                points.append((float(start.real), float(start.imag)))
            for index in range(1, steps + 1):
                point = segment.point(index / steps)
                points.append((float(point.real), float(point.imag)))

    closed = len(subpaths) == 1 and bool(subpaths[0].isclosed())
    polygonal = fill != "none" and closed
    descriptor = _geometry_descriptor(
        "svg_path_curve" if curved else "svg_path_polyline",
        points,
        transform,
        polygonal=polygonal,
        fill=fill,
        fill_rule=fill_rule,
        extra={
            "subpath_count": len(subpaths),
            "subpath_offsets": tuple(subpath_offsets),
            "curve_sampling_strategy": "fixed_samples_per_segment",
            "curve_samples_per_segment": _PATH_CURVE_SAMPLES,
            "curve_sampling_tolerance": None,
            "sampled_vertex_count": len(points),
        },
    )
    if fill != "none" and not closed:
        _append_geometry_uncertainty(
            descriptor,
            "unsupported_path_fill_topology",
        )
    return descriptor, None


def _compose_svg_affine(
    parent: tuple[float, float, float, float, float, float],
    raw: str | None,
) -> tuple[float, float, float, float, float, float]:
    """Compose a complete SVG transform list beneath its parent transform."""
    local = _IDENTITY_AFFINE
    if raw:
        matches = list(re.finditer(r"([A-Za-z]+)\s*\(([^)]*)\)", raw))
        compact = "".join(match.group(0) for match in matches)
        if not matches or re.sub(r"[\s,]+", "", compact) != re.sub(r"[\s,]+", "", raw):
            raise ValueError(f"unsupported SVG transform syntax: {raw!r}")
        for match in matches:
            values = [
                float(value)
                for value in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", match.group(2))
            ]
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"nonfinite SVG transform values: {raw!r}")
            local = _multiply_affine(local, _svg_transform_operation(match.group(1), values))
    return _multiply_affine(parent, local)


def _svg_transform_operation(
    name: str,
    values: list[float],
) -> tuple[float, float, float, float, float, float]:
    """Return one standard SVG affine operation as a six-value matrix."""
    lowered = name.lower()
    if lowered == "matrix" and len(values) == 6:
        return tuple(values)
    if lowered == "translate" and len(values) in {1, 2}:
        return (1.0, 0.0, 0.0, 1.0, values[0], values[1] if len(values) == 2 else 0.0)
    if lowered == "scale" and len(values) in {1, 2}:
        return (values[0], 0.0, 0.0, values[-1], 0.0, 0.0)
    if lowered == "rotate" and len(values) in {1, 3}:
        angle = math.radians(values[0])
        rotation = (math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0.0, 0.0)
        if len(values) == 1:
            return rotation
        cx, cy = values[1:]
        return _multiply_affine(
            _multiply_affine((1.0, 0.0, 0.0, 1.0, cx, cy), rotation),
            (1.0, 0.0, 0.0, 1.0, -cx, -cy),
        )
    if lowered in {"skewx", "skewy"} and len(values) == 1:
        shear = math.tan(math.radians(values[0]))
        if lowered == "skewx":
            return (1.0, 0.0, shear, 1.0, 0.0, 0.0)
        return (1.0, shear, 0.0, 1.0, 0.0, 0.0)
    raise ValueError(f"unsupported SVG transform operation {name!r} with {len(values)} values")


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


def _tag_identity(tag: str) -> tuple[str | None, str]:
    """Return the namespace URI and local name without discarding either fact."""
    if tag.startswith("{") and "}" in tag:
        namespace, local_name = tag[1:].split("}", 1)
        return namespace, local_name
    return None, tag


def _adapter_refs(metadata: Mapping[str, object]) -> dict[str, str]:
    """Collect explicit external-system references from SVG data attributes."""
    aliases = {
        "rhino_guid": ("rhino-guid", "rhino_guid"),
        "ifc_guid": ("ifc-guid", "ifc_guid"),
        "visualarq_id": ("visualarq-id", "visualarq_id"),
        "source_layer": ("source-layer", "source_layer"),
        "source_id": ("source-id", "source_id"),
    }
    return {
        key: str(value)
        for key, names in aliases.items()
        if (value := next((metadata[name] for name in names if metadata.get(name)), None))
    }


def _analysis_context(
    *,
    source_length_unit: str,
    analysis_length_unit: str,
    geometry_tolerance: float,
    topology_tolerance: float,
    viewbox_size: tuple[float, float],
    coordinate_scale: float | None,
) -> AnalysisContext:
    """Build the explicit planar capability and coordinate context."""
    world_coordinates: dict[str, object] = {
        "name": "SVG user space",
        "x_direction": "right",
        "y_direction": "down",
        "z_direction": "analysis-plane normal",
        "viewbox_size": [viewbox_size[0], viewbox_size[1]],
        "viewbox_size_unit": source_length_unit,
    }
    if coordinate_scale is not None:
        world_coordinates["source_to_analysis_scale"] = coordinate_scale
    return AnalysisContext(
        contract_version=NEUTRAL_SCENE_V2,
        source_schema="SVG",
        adapter_version=SVG_ADAPTER_VERSION,
        source_length_unit=source_length_unit,
        analysis_length_unit=analysis_length_unit,
        world_coordinate_system=world_coordinates,
        level_references=(),
        analysis_plane=AnalysisPlane(
            name="SVG XY analysis plane",
            origin=(0.0, 0.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        geometry_tolerance=geometry_tolerance,
        topology_tolerance=topology_tolerance,
        walking_body_profiles=(),
        visual_height_bands=(),
        capability_flags={
            "planar_geometry": True,
            "height_queries": False,
            "volume_queries": False,
            "closed_solid_geometry": False,
            "optical_queries": False,
            "vertical_queries": False,
        },
        input_mode="svg",
    )


def _mesh_from_record(
    record: Mapping[str, object],
    *,
    scale: float,
    analysis_length_unit: str,
    source_bucket: str,
) -> tuple[MeshGeometry3D | None, tuple[UncertaintyRecord, ...]]:
    """Create a z=0 transport mesh from authored SVG geometry facts."""
    source_ref = _neutral_id(record)
    descriptor = record.get("_adapter_geometry")
    if not isinstance(descriptor, Mapping):
        reason = str(record.get("_adapter_geometry_error") or "unsupported")
        error_code = (
            "path_parse_failed"
            if reason.startswith("path_parse_failed:")
            else reason
            if reason
            in {"invalid_curve_dimensions", "unsupported_nested_svg_viewport"}
            else "unsupported_svg_geometry"
        )
        return None, (
            _record_uncertainty(
                "missing_geometry",
                "The SVG element has no supported authored geometry.",
                source_ref,
                {"reason": reason},
            ),
            _record_uncertainty(
                error_code,
                "The SVG geometry could not be represented without fabrication.",
                source_ref,
                {"reason": reason},
            ),
        )

    points = _dedupe_polygon_closure(descriptor.get("points") or ())
    if len(points) < 2:
        return None, (
            _record_uncertainty(
                "missing_geometry",
                "The authored SVG geometry has fewer than two distinct points.",
                source_ref,
            ),
        )
    planar_vertices = tuple(
        (float(x) * scale, float(y) * scale) for x, y in points
    )
    warnings: list[UncertaintyRecord] = []
    geometry_uncertainties = tuple(
        str(code)
        for code in descriptor.get("geometry_uncertainties") or ()
        if _optional_text(code)
    )
    for geometry_uncertainty in geometry_uncertainties:
        warnings.append(
            _record_uncertainty(
                geometry_uncertainty,
                "SVG fill topology was preserved as line geometry due to uncertainty.",
                source_ref,
                {
                    "subpath_count": descriptor.get("subpath_count"),
                    "fill_rule": descriptor.get("fill_rule"),
                },
            )
        )
    triangles: tuple[tuple[int, int, int], ...] = ()
    if bool(descriptor.get("polygonal")) and len(planar_vertices) >= 3:
        planar_vertices, triangles, triangulation_error = _triangulate_polygon(
            planar_vertices
        )
        if triangulation_error:
            warnings.append(
                _record_uncertainty(
                    "polygon_triangulation_unavailable",
                    "The authored polygon vertices were preserved without fabricated faces.",
                    source_ref,
                    {"reason": triangulation_error},
                )
            )
    vertices = tuple((x, y, 0.0) for x, y in planar_vertices)

    # These meshes transport planar evidence only. They are never declared as
    # closed solids, and manifold state remains unknown until a 3D gate exists.
    source_id = _source_id(record)
    return MeshGeometry3D(
        id=f"svg-geometry:{source_ref}",
        vertices=vertices,
        triangle_indices=triangles,
        normals=tuple((0.0, 0.0, 1.0) for _ in triangles),
        is_manifold=None,
        is_closed=False,
        local_to_world_provenance={
            "adapter": SVG_ADAPTER_VERSION,
            "method": "svg_adapter_world_geometry",
            "svg_y_direction": "down",
            "source_namespace": record.get("_source_namespace"),
            "source_bucket": source_bucket,
            "world_affine": descriptor.get("world_affine"),
        },
        source_representation_id=source_id,
        tessellation_settings={
            "geometry_source": str(descriptor.get("geometry_source") or "unknown"),
            "curve_segments": descriptor.get("curve_segments"),
            "fill": descriptor.get("fill"),
            "fill_rule": descriptor.get("fill_rule"),
            "subpath_count": descriptor.get("subpath_count"),
            "subpath_offsets": descriptor.get("subpath_offsets"),
            "curve_sampling_strategy": descriptor.get("curve_sampling_strategy"),
            "curve_samples_per_segment": descriptor.get("curve_samples_per_segment"),
            "curve_sampling_tolerance": descriptor.get("curve_sampling_tolerance"),
            "sampled_vertex_count": descriptor.get("sampled_vertex_count"),
            "triangulation": "shapely_constrained_filter" if triangles else "none",
        },
        units=analysis_length_unit,
    ), tuple(warnings)


def _dedupe_polygon_closure(
    points: Iterable[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Remove repeated adjacent and closing points without reordering vertices."""
    result: list[tuple[float, float]] = []
    for point in points:
        normalized = (float(point[0]), float(point[1]))
        if not result or normalized != result[-1]:
            result.append(normalized)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result


def _triangulate_polygon(
    points: tuple[tuple[float, float], ...],
) -> tuple[
    tuple[tuple[float, float], ...],
    tuple[tuple[int, int, int], ...],
    str | None,
]:
    """Triangulate a simple concave polygon while excluding exterior Delaunay faces."""
    from shapely.geometry import Polygon
    from shapely.ops import triangulate

    polygon = Polygon(points)
    if not polygon.is_valid or polygon.is_empty or polygon.area <= 0.0:
        return points, (), "invalid_or_zero_area_polygon"
    candidates = [
        triangle
        for triangle in triangulate(polygon)
        if polygon.covers(triangle)
    ]
    if not candidates or not math.isclose(
        sum(triangle.area for triangle in candidates),
        polygon.area,
        rel_tol=1e-9,
        abs_tol=1e-12,
    ):
        return points, (), "triangles_do_not_cover_polygon"

    vertices = list(points)
    indices = {point: index for index, point in enumerate(vertices)}
    triangle_indices: list[tuple[int, int, int]] = []
    for triangle in sorted(
        candidates,
        key=lambda item: (item.centroid.x, item.centroid.y, tuple(item.exterior.coords)),
    ):
        triangle_points = tuple(
            (float(x), float(y)) for x, y in list(triangle.exterior.coords)[:-1]
        )
        for point in triangle_points:
            if point not in indices:
                indices[point] = len(vertices)
                vertices.append(point)
        triangle_indices.append(tuple(indices[point] for point in triangle_points))
    return tuple(vertices), tuple(triangle_indices), None


def _source_object(
    record: Mapping[str, object],
    *,
    source_bucket: str,
    geometry_ref: str | None,
    group_refs: tuple[str, ...],
    opening_refs: tuple[str, ...],
    geometry_warnings: tuple[UncertaintyRecord, ...],
) -> SourceObject:
    """Translate one parsed source element without adding analysis semantics."""
    neutral_id = _neutral_id(record)
    source_id = _source_id(record)
    metadata = _authored_metadata(record)
    authored_role = _optional_text(metadata.get("role"))
    role = authored_role or "unknown"
    if authored_role == "region":
        role = "authored_region_hint"
    elif authored_role == "path":
        role = "authored_path_hint"
    uncertainties = list(geometry_warnings)
    if source_id is None:
        uncertainties.append(
            _record_uncertainty(
                "missing_source_id",
                "The SVG element had no explicit source id; a traversal id was assigned.",
                neutral_id,
            )
        )
    if authored_role is None:
        uncertainties.append(
            _record_uncertainty(
                "source_role_unavailable",
                "No explicit data-role metadata was authored for this SVG element.",
                neutral_id,
            )
        )
    material_refs = _metadata_refs(metadata, "material-ref", "material-refs")
    surface_refs = _metadata_refs(metadata, "surface-ref", "surface-refs")
    if material_refs:
        uncertainties.append(
            _record_uncertainty(
                "unresolved_material_ref",
                "SVG material references were omitted because no material records exist.",
                neutral_id,
                {"omitted_refs": material_refs},
            )
        )
    if surface_refs:
        uncertainties.append(
            _record_uncertainty(
                "unresolved_surface_ref",
                "SVG surface references were omitted because no surface records exist.",
                neutral_id,
                {"omitted_refs": surface_refs},
            )
        )
    orientation = _optional_number(metadata.get("orientation"))
    return SourceObject(
        id=neutral_id,
        source_id=source_id,
        source_role=role,
        source_class=f"svg:{record.get('tag') or 'unknown'}",
        geometry_refs=(geometry_ref,) if geometry_ref else (),
        group_refs=group_refs,
        material_refs=(),
        surface_refs=(),
        opening_refs=opening_refs,
        authored_local_frame=(
            {
                "orientation_degrees": orientation,
                "basis_source": "explicit_svg_orientation_metadata",
            }
            if orientation is not None
            else None
        ),
        provenance={
            "adapter": SVG_ADAPTER_VERSION,
            "source_namespace": record.get("_source_namespace"),
            "source_bucket": source_bucket,
            "source_order": "global_svg_traversal",
            "source_metadata": metadata,
            "adapter_refs": dict(record.get("adapter_refs") or {}),
            "authored_hint": authored_role in {"region", "path"},
        },
        uncertainties=tuple(uncertainties),
    )


def _record_uncertainty(
    code: str,
    message: str,
    source_ref: str,
    details: Mapping[str, object] | None = None,
) -> UncertaintyRecord:
    """Build one adapter warning without collapsing unavailable evidence to zero."""
    return UncertaintyRecord(
        code=code,
        message=message,
        source_refs=(source_ref,),
        operation="svg_adapter_geometry_handoff",
        severity="warning",
        details={"adapter": SVG_ADAPTER_VERSION, **(details or {})},
    )


def _sanitized_metadata(value: object) -> dict[str, object]:
    """Copy factual metadata while removing every legacy weight spelling."""
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): nested
        for key, nested in value.items()
        if str(key).lower() not in _FORBIDDEN_METADATA_KEYS
    }


def _authored_metadata(record: Mapping[str, object]) -> dict[str, object]:
    """Return only explicit data-* facts captured during the shared XML traversal."""
    return _sanitized_metadata(record.get("_authored_metadata"))


def _neutral_id(record: Mapping[str, object]) -> str:
    """Return the deterministic Neutral Scene identity assigned by the loader handoff."""
    return str(record["_neutral_id"])


def _source_id(record: Mapping[str, object]) -> str | None:
    """Return the original explicit SVG id without compatibility fallbacks."""
    value = record.get("_source_id")
    return str(value) if value is not None and str(value).strip() else None


def _optional_number(value: object) -> float | None:
    """Return one optional finite numeric metadata fact."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _validate_explicit_source_ids(
    records: Iterable[tuple[str, Mapping[str, object]]],
) -> None:
    """Reject duplicate explicit SVG ids before any Neutral Scene references exist."""
    seen: dict[str, int] = {}
    for index, (_, record) in enumerate(records, start=1):
        source_id = _source_id(record)
        if source_id is None:
            continue
        if source_id in seen:
            raise ValueError(
                f"duplicate explicit SVG source id {source_id!r} "
                f"at traversal records {seen[source_id]} and {index}"
            )
        seen[source_id] = index


def _assign_neutral_ids(
    records: Iterable[tuple[str, MutableMapping[str, object]]],
    *,
    reserved_ids: set[str] | None = None,
) -> None:
    """Assign deterministic neutral ids without colliding with authored SVG ids."""
    materialized = list(records)
    explicit_ids = {
        source_id
        for _, record in materialized
        if (source_id := _source_id(record)) is not None
    }
    assigned_ids = {*explicit_ids, *(reserved_ids or set())}
    next_index = 1

    # Reserve all authored ids first so traversal fallbacks cannot shadow a
    # later element that owns the same textual id in the source document.
    for _, record in materialized:
        source_id = _source_id(record)
        if source_id is not None:
            record["_neutral_id"] = source_id
            continue
        while True:
            candidate = f"svg-element-{next_index:06d}"
            next_index += 1
            if candidate not in assigned_ids:
                break
        record["_neutral_id"] = candidate
        assigned_ids.add(candidate)


def _metadata_refs(metadata: Mapping[str, object], *names: str) -> tuple[str, ...]:
    """Read the first present comma/space-separated metadata reference list."""
    for name in names:
        if metadata.get(name):
            return _split_refs(metadata[name])
    return ()


def _split_refs(value: object) -> tuple[str, ...]:
    """Split and stably deduplicate compact SVG metadata references."""
    parts = re.split(r"[,;\s]+", str(value).strip())
    return tuple(dict.fromkeys(part for part in parts if part))


def _authored_groups(
    records: Iterable[Mapping[str, object]],
) -> tuple[tuple[AuthoredGroup, ...], dict[str, tuple[str, ...]]]:
    """Collect only explicit data-group and furniture-group memberships."""
    members: dict[str, list[str]] = {}
    roles: dict[str, str] = {}
    object_memberships: dict[str, list[str]] = {}
    for record in records:
        metadata = _authored_metadata(record)
        furniture_group = _optional_text(
            metadata.get("furniture-group") or metadata.get("furniture-group-id")
        )
        source_group = _optional_text(metadata.get("group"))
        candidates = []
        if furniture_group:
            candidates.append((furniture_group, "furniture_group"))
        if source_group and source_group != furniture_group:
            candidates.append((source_group, "source_group"))
        neutral_id = _neutral_id(record)
        for group_id, role in candidates:
            members.setdefault(group_id, [])
            roles.setdefault(group_id, role)
            if role == "furniture_group":
                roles[group_id] = role
            if neutral_id not in members[group_id]:
                members[group_id].append(neutral_id)
            object_memberships.setdefault(neutral_id, [])
            if group_id not in object_memberships[neutral_id]:
                object_memberships[neutral_id].append(group_id)
    groups = tuple(
        AuthoredGroup(
            id=group_id,
            source_id=group_id,
            member_refs=tuple(group_members),
            group_role=roles[group_id],
            provenance={
                "adapter": SVG_ADAPTER_VERSION,
                "method": "explicit_svg_group_metadata",
            },
        )
        for group_id, group_members in members.items()
    )
    object_refs: dict[str, tuple[str, ...]] = {
        member: tuple(group_ids)
        for member, group_ids in object_memberships.items()
    }
    return groups, object_refs


def _authored_grids(
    records: Iterable[Mapping[str, object]],
    *,
    scale: float,
) -> tuple[tuple[AuthoredGridAxis, ...], tuple[AuthoredGrid, ...]]:
    """Preserve explicit axes and group only axes carrying authored grid metadata."""
    axes: list[AuthoredGridAxis] = []
    grid_axes: dict[str, list[str]] = {}
    for record in records:
        metadata = _authored_metadata(record)
        if metadata.get("role") not in {"column_axis", "column_grid"}:
            continue
        descriptor = record.get("_adapter_geometry")
        if not isinstance(descriptor, Mapping):
            continue
        points = _dedupe_polygon_closure(descriptor.get("points") or ())
        if len(points) < 2:
            continue
        axis_id = _neutral_id(record)
        axes.append(
            AuthoredGridAxis(
                id=axis_id,
                source_id=_source_id(record),
                curve_points=tuple((x * scale, y * scale, 0.0) for x, y in points),
                branch_identifier=_optional_text(metadata.get("branch")),
                list_identifier=_optional_text(metadata.get("list")),
                provenance={
                    "adapter": SVG_ADAPTER_VERSION,
                    "method": "explicit_svg_column_axis",
                    "source_metadata": metadata,
                },
            )
        )
        grid_id = _optional_text(metadata.get("grid") or metadata.get("grid-id"))
        if grid_id:
            grid_axes.setdefault(grid_id, [])
            if axis_id not in grid_axes[grid_id]:
                grid_axes[grid_id].append(axis_id)
    grids = tuple(
        AuthoredGrid(
            id=grid_id,
            source_id=grid_id,
            axis_refs=tuple(axis_refs),
            provenance={
                "adapter": SVG_ADAPTER_VERSION,
                "method": "explicit_svg_grid_metadata",
            },
        )
        for grid_id, axis_refs in grid_axes.items()
    )
    return tuple(axes), grids


def _authored_affordances(
    records: Iterable[Mapping[str, object]],
    *,
    geometry_refs: Mapping[int, str],
    scale: float,
    valid_object_refs: set[str],
) -> tuple[tuple[AuthoredAffordanceZone, ...], tuple[UncertaintyRecord, ...]]:
    """Preserve only affordances with explicit role, purpose, owners, and extent."""
    zones: list[AuthoredAffordanceZone] = []
    uncertainties: list[UncertaintyRecord] = []
    for record in records:
        metadata = _authored_metadata(record)
        if metadata.get("role") not in {"affordance", "affordance_zone"}:
            continue
        purpose = _optional_text(metadata.get("purpose"))
        authored_owners = _metadata_refs(
            metadata, "source-furniture-refs", "source-furniture-ref"
        )
        owners = tuple(ref for ref in authored_owners if ref in valid_object_refs)
        unresolved_owners = tuple(
            ref for ref in authored_owners if ref not in valid_object_refs
        )
        source_id = _neutral_id(record)
        if unresolved_owners:
            uncertainties.append(
                _record_uncertainty(
                    "unresolved_affordance_owner_ref",
                    "Unknown affordance owner references were omitted.",
                    source_id,
                    {"omitted_refs": unresolved_owners},
                )
            )
        geometry_ref = geometry_refs.get(id(record))
        if not purpose or not owners or not geometry_ref:
            uncertainties.append(
                UncertaintyRecord(
                    code="incomplete_authored_affordance",
                    message="Explicit affordance lacks purpose, owner, or geometry.",
                    source_refs=(source_id,),
                    operation="svg_adapter_affordance_handoff",
                    severity="warning",
                    details={"adapter": SVG_ADAPTER_VERSION},
                )
            )
            continue
        try:
            z_min = float(metadata["z-min"]) * scale
            z_max = float(metadata["z-max"]) * scale
            has_vertical_extent = (
                math.isfinite(z_min) and math.isfinite(z_max) and z_max >= z_min
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            z_min = z_max = 0.0
            has_vertical_extent = False
        zone_uncertainties = ()
        if not has_vertical_extent:
            # z=0 describes the authored planar representation, while this
            # uncertainty prevents consumers from treating it as physical height.
            z_min = z_max = 0.0
            zone_uncertainties = (
                UncertaintyRecord(
                    code="vertical_extent_unavailable",
                    message="SVG supplied planar affordance geometry without physical height.",
                    source_refs=(source_id,),
                    operation="svg_adapter_affordance_handoff",
                    severity="warning",
                    details={"representation_plane_z": 0.0},
                ),
            )
        zones.append(
            AuthoredAffordanceZone(
                id=source_id,
                source_id=source_id,
                geometry_refs=(geometry_ref,),
                vertical_extent=(z_min, z_max),
                purpose=purpose,
                task_facts={"source_metadata": metadata},
                source_furniture_refs=owners,
                provenance={
                    "adapter": SVG_ADAPTER_VERSION,
                    "method": "explicit_svg_affordance_metadata",
                },
                uncertainties=zone_uncertainties,
            )
        )
    return tuple(zones), tuple(uncertainties)


def _source_openings(
    records: Iterable[Mapping[str, object]],
    *,
    geometry_refs: Mapping[int, str],
    valid_object_refs: set[str],
) -> tuple[tuple[SourceOpening, ...], tuple[UncertaintyRecord, ...]]:
    """Translate explicitly parsed SVG openings and their authored host refs."""
    openings: list[SourceOpening] = []
    adapter_uncertainties: list[UncertaintyRecord] = []
    for record in records:
        metadata = _authored_metadata(record)
        if metadata.get("role") != "opening":
            continue
        neutral_id = _neutral_id(record)
        geometry_ref = geometry_refs.get(id(record))
        authored_hosts = _metadata_refs(metadata, "host-refs", "host-ref")
        host_refs = tuple(ref for ref in authored_hosts if ref in valid_object_refs)
        unresolved_hosts = tuple(
            ref for ref in authored_hosts if ref not in valid_object_refs
        )
        if unresolved_hosts:
            adapter_uncertainties.append(
                _record_uncertainty(
                    "unresolved_opening_host_ref",
                    "Unknown opening host references were omitted.",
                    neutral_id,
                    {"omitted_refs": unresolved_hosts},
                )
            )
        uncertainties = () if geometry_ref else (
            _record_uncertainty(
                "missing_geometry",
                "The explicit SVG opening has no supported geometry.",
                neutral_id,
            ),
        )
        openings.append(
            SourceOpening(
                id=neutral_id,
                source_id=_source_id(record),
                host_refs=host_refs,
                geometry_refs=(geometry_ref,) if geometry_ref else (),
                opening_kind=_optional_text(metadata.get("opening-kind")) or "opening",
                provenance={
                    "adapter": SVG_ADAPTER_VERSION,
                    "method": "explicit_svg_opening_role",
                    "source_metadata": metadata,
                },
                uncertainties=uncertainties,
            )
        )
    return tuple(openings), tuple(adapter_uncertainties)


def _analysis_domain(
    records: Iterable[Mapping[str, object]],
    *,
    geometry_refs: Mapping[int, str],
) -> AnalysisDomain | None:
    """Return the sole explicit domain and reject ambiguous authored selection."""
    candidates = [
        record
        for record in records
        if _authored_metadata(record).get("role")
        in {"analysis_domain", "analysis-domain"}
    ]
    if len(candidates) > 1:
        candidate_ids = tuple(_neutral_id(record) for record in candidates)
        raise ValueError(
            f"multiple explicit SVG analysis domains are ambiguous: {candidate_ids}"
        )
    if not candidates:
        return None
    record = candidates[0]
    neutral_id = _neutral_id(record)
    geometry_ref = geometry_refs.get(id(record))
    uncertainties = () if geometry_ref else (
        _record_uncertainty(
            "missing_geometry",
            "The explicit SVG analysis domain has no supported geometry.",
            neutral_id,
        ),
    )
    return AnalysisDomain(
        id=neutral_id,
        geometry_refs=(geometry_ref,) if geometry_ref else (),
        source_id=_source_id(record),
        selection_method="explicit_svg_element",
        provenance={
            "adapter": SVG_ADAPTER_VERSION,
            "method": "explicit_svg_analysis_domain_role",
        },
        uncertainties=uncertainties,
    )


def _validate_adapter_references(
    *,
    source_objects: tuple[SourceObject, ...],
    geometries: tuple[MeshGeometry3D, ...],
    authored_groups: tuple[AuthoredGroup, ...],
    authored_grids: tuple[AuthoredGrid, ...],
    authored_grid_axes: tuple[AuthoredGridAxis, ...],
    authored_affordances: tuple[AuthoredAffordanceZone, ...],
    openings: tuple[SourceOpening, ...],
    analysis_domain: AnalysisDomain | None,
) -> None:
    """Reject any dangling reference left by adapter record construction."""
    object_ids = {record.id for record in source_objects}
    geometry_ids = {record.id for record in geometries}
    group_ids = {record.id for record in authored_groups}
    axis_ids = {record.id for record in authored_grid_axes}
    opening_ids = {record.id for record in openings}

    # Gate 2 constructs neither material nor surface records, so corresponding
    # object refs must be empty rather than point at unrepresented source ids.
    for record in source_objects:
        _require_ref_subset(
            record.geometry_refs,
            geometry_ids,
            f"source_object:{record.id}:geometry_refs",
        )
        _require_ref_subset(record.group_refs, group_ids, f"source_object:{record.id}:group_refs")
        _require_ref_subset(
            record.opening_refs,
            opening_ids,
            f"source_object:{record.id}:opening_refs",
        )
        _require_ref_subset(
            record.container_refs,
            object_ids,
            f"source_object:{record.id}:container_refs",
        )
        _require_ref_subset(
            record.material_refs,
            set(),
            f"source_object:{record.id}:material_refs",
        )
        _require_ref_subset(record.surface_refs, set(), f"source_object:{record.id}:surface_refs")
    for record in authored_groups:
        _require_ref_subset(
            record.member_refs,
            object_ids,
            f"authored_group:{record.id}:member_refs",
        )
    for record in authored_grids:
        _require_ref_subset(record.axis_refs, axis_ids, f"authored_grid:{record.id}:axis_refs")
    for record in authored_affordances:
        _require_ref_subset(
            record.geometry_refs,
            geometry_ids,
            f"affordance:{record.id}:geometry_refs",
        )
        _require_ref_subset(
            record.source_furniture_refs,
            object_ids,
            f"affordance:{record.id}:source_furniture_refs",
        )
    for record in openings:
        _require_ref_subset(
            record.geometry_refs,
            geometry_ids,
            f"opening:{record.id}:geometry_refs",
        )
        _require_ref_subset(record.host_refs, object_ids, f"opening:{record.id}:host_refs")
    if analysis_domain is not None:
        _require_ref_subset(
            analysis_domain.geometry_refs,
            geometry_ids,
            f"analysis_domain:{analysis_domain.id}:geometry_refs",
        )


def _require_ref_subset(
    refs: Iterable[str],
    valid_ids: set[str],
    location: str,
) -> None:
    """Raise an internal adapter error when references escape their record set."""
    missing = tuple(ref for ref in refs if ref not in valid_ids)
    if missing:
        raise RuntimeError(f"dangling Neutral Scene references at {location}: {missing}")


def _optional_text(value: object) -> str | None:
    """Normalize optional compact metadata text without inventing a default."""
    if value is None:
        return None
    result = str(value).strip()
    return result or None


__all__ = [
    "DEFAULT_GEOMETRY_TOLERANCE",
    "DEFAULT_TOPOLOGY_TOLERANCE",
    "SVG_ADAPTER_VERSION",
    "load_svg_neutral_scene",
]
