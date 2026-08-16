"""Translate structured planar SVG fixture facts into Neutral Scene v2."""

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path
import re
from typing import Iterable, Mapping, MutableMapping

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
    from ..features.scene_loader import load_structured_svg_scene
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
    from features.scene_loader import load_structured_svg_scene


SVG_ADAPTER_VERSION = "svg-scene-adapter/0.1.0"
DEFAULT_GEOMETRY_TOLERANCE = 1e-6
DEFAULT_TOPOLOGY_TOLERANCE = 1e-6

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
    legacy_scene = load_structured_svg_scene(source, include_source_order=True)
    width, height = legacy_scene["size"]

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

    records = list(legacy_scene["_source_records"])
    _assign_neutral_ids(records)
    _validate_explicit_source_ids(records)
    geometries: list[MeshGeometry3D] = []
    geometry_refs: dict[int, str] = {}
    geometry_warnings: dict[int, tuple[UncertaintyRecord, ...]] = {}
    for bucket, record in records:
        geometry, warnings = _mesh_from_record(
            record,
            scale=scale,
            analysis_length_unit=context.analysis_length_unit,
            legacy_bucket=bucket,
        )
        geometry_warnings[id(record)] = warnings
        if geometry is not None:
            geometries.append(geometry)
            geometry_refs[id(record)] = geometry.id

    authored_groups, object_group_refs = _authored_groups(record for _, record in records)
    openings = _source_openings(
        (record for _, record in records),
        geometry_refs=geometry_refs,
    )
    opening_refs_by_host: dict[str, list[str]] = defaultdict(list)
    for opening in openings:
        for host_ref in opening.host_refs:
            opening_refs_by_host[host_ref].append(opening.id)

    source_objects = tuple(
        _source_object(
            record,
            legacy_bucket=bucket,
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
    )
    analysis_domain = _analysis_domain(
        (record for _, record in records),
        geometry_refs=geometry_refs,
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
        uncertainties=affordance_uncertainties,
    )


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
    legacy_bucket: str,
) -> tuple[MeshGeometry3D | None, tuple[UncertaintyRecord, ...]]:
    """Create a z=0 mesh from adapter handoff geometry without bbox invention."""
    source_ref = _neutral_id(record)
    descriptor = record.get("_adapter_geometry")
    if not isinstance(descriptor, Mapping):
        reason = str(record.get("_adapter_geometry_error") or "unsupported")
        return None, (
            _record_uncertainty(
                "missing_geometry",
                "The SVG element has no supported authored geometry.",
                source_ref,
                {"reason": reason},
            ),
            _record_uncertainty(
                "unsupported_svg_geometry",
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
    warnings: tuple[UncertaintyRecord, ...] = ()
    triangles: tuple[tuple[int, int, int], ...] = ()
    if bool(descriptor.get("polygonal")) and len(planar_vertices) >= 3:
        planar_vertices, triangles, triangulation_error = _triangulate_polygon(
            planar_vertices
        )
        if triangulation_error:
            warnings = (
                _record_uncertainty(
                    "polygon_triangulation_unavailable",
                    "The authored polygon vertices were preserved without fabricated faces.",
                    source_ref,
                    {"reason": triangulation_error},
                ),
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
            "method": "structured_svg_loader_world_points",
            "svg_y_direction": "down",
            "legacy_bucket": legacy_bucket,
            "world_affine": descriptor.get("world_affine"),
        },
        source_representation_id=source_id,
        tessellation_settings={
            "geometry_source": str(descriptor.get("geometry_source") or "unknown"),
            "curve_segments": 64
            if descriptor.get("geometry_source") in {"analytic_circle", "analytic_ellipse"}
            else None,
            "triangulation": "shapely_constrained_filter" if triangles else "none",
        },
        units=analysis_length_unit,
    ), warnings


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
    legacy_bucket: str,
    geometry_ref: str | None,
    group_refs: tuple[str, ...],
    opening_refs: tuple[str, ...],
    geometry_warnings: tuple[UncertaintyRecord, ...],
) -> SourceObject:
    """Translate one loader record without adding analysis semantics."""
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
                {"compatibility_role": record.get("role")},
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
        material_refs=_metadata_refs(metadata, "material-ref", "material-refs"),
        surface_refs=_metadata_refs(metadata, "surface-ref", "surface-refs"),
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
            "legacy_bucket": legacy_bucket,
            "source_order": "global_svg_traversal",
            "source_metadata": metadata,
            "adapter_refs": dict(record.get("adapter_refs") or {}),
            "authored_hint": authored_role in {"region", "path"},
            "compatibility_role": record.get("role"),
            "compatibility_group": record.get("group"),
            "compatibility_furniture_group": record.get("furniture_group"),
            "compatibility_semantics_authored": False,
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
) -> None:
    """Assign deterministic neutral ids without colliding with authored SVG ids."""
    materialized = list(records)
    explicit_ids = {
        source_id
        for _, record in materialized
        if (source_id := _source_id(record)) is not None
    }
    assigned_ids = set(explicit_ids)
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
) -> tuple[tuple[AuthoredAffordanceZone, ...], tuple[UncertaintyRecord, ...]]:
    """Preserve only affordances with explicit role, purpose, owners, and extent."""
    zones: list[AuthoredAffordanceZone] = []
    uncertainties: list[UncertaintyRecord] = []
    for record in records:
        metadata = _authored_metadata(record)
        if metadata.get("role") not in {"affordance", "affordance_zone"}:
            continue
        purpose = _optional_text(metadata.get("purpose"))
        owners = _metadata_refs(
            metadata, "source-furniture-refs", "source-furniture-ref"
        )
        geometry_ref = geometry_refs.get(id(record))
        if not purpose or not owners or not geometry_ref:
            source_id = _neutral_id(record)
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
        source_id = _neutral_id(record)
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
) -> tuple[SourceOpening, ...]:
    """Translate explicitly parsed SVG openings and their authored host refs."""
    openings: list[SourceOpening] = []
    for record in records:
        metadata = _authored_metadata(record)
        if metadata.get("role") != "opening":
            continue
        neutral_id = _neutral_id(record)
        geometry_ref = geometry_refs.get(id(record))
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
                host_refs=_metadata_refs(metadata, "host-refs", "host-ref"),
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
    return tuple(openings)


def _analysis_domain(
    records: Iterable[Mapping[str, object]],
    *,
    geometry_refs: Mapping[int, str],
) -> AnalysisDomain | None:
    """Return only an explicitly role-marked SVG analysis domain."""
    for record in records:
        metadata = _authored_metadata(record)
        if metadata.get("role") not in {"analysis_domain", "analysis-domain"}:
            continue
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
    return None


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
