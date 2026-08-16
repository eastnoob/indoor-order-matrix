"""Translate structured planar SVG fixture facts into Neutral Scene v2."""

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path
import re
from typing import Iterable, Mapping

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
    from ..features.scene_loader import Rect, load_structured_svg_scene
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
    from features.scene_loader import Rect, load_structured_svg_scene


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
_LINE_ROLES = {"opening", "column_axis", "column_grid"}


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
    geometries: list[MeshGeometry3D] = []
    geometry_refs: dict[int, str] = {}
    for bucket, record in records:
        geometry = _mesh_from_record(
            record,
            scale=scale,
            analysis_length_unit=context.analysis_length_unit,
            legacy_bucket=bucket,
        )
        if geometry is not None:
            geometries.append(geometry)
            geometry_refs[id(record)] = geometry.id

    authored_groups, object_group_refs = _authored_groups(legacy_scene["objects"])
    openings = _source_openings(
        legacy_scene["entries"], geometry_refs=geometry_refs
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
            group_refs=object_group_refs.get(record["id"], ()),
            opening_refs=tuple(opening_refs_by_host.get(record["id"], ())),
        )
        for bucket, record in records
    )
    axes, grids = _authored_grids(
        legacy_scene["column_axes"], scale=scale
    )
    affordances, affordance_uncertainties = _authored_affordances(
        legacy_scene["objects"], geometry_refs=geometry_refs, scale=scale
    )
    analysis_domain = _analysis_domain(
        legacy_scene["objects"], geometry_refs=geometry_refs
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
) -> MeshGeometry3D | None:
    """Create a z=0 transport mesh from explicit points or a recorded rect fallback."""
    raw_points = list(record.get("points") or ())
    outline_closed = len(raw_points) >= 3 and raw_points[0] == raw_points[-1]
    points = _dedupe_polygon_closure(raw_points)
    geometry_source = "points"
    if len(points) < 2:
        rect = record.get("rect")
        if not isinstance(rect, Rect):
            return None
        points = _dedupe_polygon_closure(_rect_corners(rect))
        geometry_source = "rect_fallback"
    if len(points) < 2:
        return None

    vertices = tuple((float(x) * scale, float(y) * scale, 0.0) for x, y in points)
    role = str(record.get("role") or "")
    tag = str(record.get("tag") or "")
    polygonal = (
        len(vertices) >= 3
        and role not in _LINE_ROLES
        and (tag in {"polygon", "rect", "circle", "ellipse", "use"} or outline_closed)
    )
    triangles = tuple(
        (0, index, index + 1) for index in range(1, len(vertices) - 1)
    ) if polygonal else ()

    # These meshes transport planar evidence only. They are never declared as
    # closed solids, and manifold state remains unknown until a 3D gate exists.
    source_id = str(record["id"])
    return MeshGeometry3D(
        id=f"svg-geometry:{source_id}",
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
        },
        source_representation_id=source_id,
        tessellation_settings={
            "geometry_source": geometry_source,
            "triangulation": "deterministic_fan" if triangles else "none",
        },
        units=analysis_length_unit,
    )


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


def _rect_corners(rect: Rect) -> list[tuple[float, float]]:
    """Return deterministic bbox corners for point-poor loader records."""
    return [
        (rect.left, rect.top),
        (rect.right, rect.top),
        (rect.right, rect.bottom),
        (rect.left, rect.bottom),
    ]


def _source_object(
    record: Mapping[str, object],
    *,
    legacy_bucket: str,
    geometry_ref: str | None,
    group_refs: tuple[str, ...],
    opening_refs: tuple[str, ...],
) -> SourceObject:
    """Translate one loader record without adding analysis semantics."""
    source_id = str(record["id"])
    metadata = _sanitized_metadata(record.get("metadata"))
    role = str(record.get("role") or "unknown")
    if legacy_bucket == "regions":
        role = "authored_region_hint"
    elif legacy_bucket == "paths":
        role = "authored_path_hint"
    uncertainties = () if geometry_ref else (_missing_geometry(source_id),)
    orientation = float(record.get("orientation") or 0.0)
    return SourceObject(
        id=source_id,
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
            if "orientation" in record.get("_authored_metadata_keys", ())
            else None
        ),
        provenance={
            "adapter": SVG_ADAPTER_VERSION,
            "legacy_bucket": legacy_bucket,
            "source_order": "global_svg_traversal",
            "source_metadata": metadata,
            "adapter_refs": dict(record.get("adapter_refs") or {}),
            "authored_hint": legacy_bucket in {"regions", "paths"},
        },
        uncertainties=uncertainties,
    )


def _missing_geometry(source_id: str) -> UncertaintyRecord:
    """Describe an explicit SVG object whose loader yielded no usable geometry."""
    return UncertaintyRecord(
        code="missing_geometry",
        message="The structured SVG record had no usable points or rectangle.",
        source_refs=(source_id,),
        operation="svg_adapter_geometry_handoff",
        severity="warning",
        details={"adapter": SVG_ADAPTER_VERSION},
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
    """Collect explicit furniture-group memberships in loader source order."""
    members: dict[str, list[str]] = {}
    for record in records:
        authored_keys = set(record.get("_authored_metadata_keys", ()))
        if not authored_keys.intersection({"furniture-group", "furniture-group-id"}):
            continue
        group_id = str(record.get("furniture_group") or "")
        if not group_id or group_id == "global":
            continue
        members.setdefault(group_id, [])
        source_id = str(record["id"])
        if source_id not in members[group_id]:
            members[group_id].append(source_id)
    groups = tuple(
        AuthoredGroup(
            id=group_id,
            source_id=group_id,
            member_refs=tuple(group_members),
            group_role="furniture_group",
            provenance={
                "adapter": SVG_ADAPTER_VERSION,
                "method": "explicit_svg_furniture_group_metadata",
            },
        )
        for group_id, group_members in members.items()
    )
    object_refs: dict[str, tuple[str, ...]] = {
        member: (group.id,)
        for group in groups
        for member in group.member_refs
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
        points = _dedupe_polygon_closure(record.get("points") or ())
        if len(points) < 2:
            continue
        metadata = _sanitized_metadata(record.get("metadata"))
        axis_id = str(record["id"])
        axes.append(
            AuthoredGridAxis(
                id=axis_id,
                source_id=axis_id,
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
        if str(record.get("role") or "") not in {"affordance", "affordance_zone"}:
            continue
        metadata = _sanitized_metadata(record.get("metadata"))
        purpose = _optional_text(metadata.get("purpose"))
        owners = _metadata_refs(
            metadata, "source-furniture-refs", "source-furniture-ref"
        )
        geometry_ref = geometry_refs.get(id(record))
        if not purpose or not owners or not geometry_ref:
            source_id = str(record["id"])
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
        source_id = str(record["id"])
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
        metadata = _sanitized_metadata(record.get("metadata"))
        source_id = str(record["id"])
        geometry_ref = geometry_refs.get(id(record))
        uncertainties = () if geometry_ref else (_missing_geometry(source_id),)
        openings.append(
            SourceOpening(
                id=source_id,
                source_id=source_id,
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
        if str(record.get("role") or "") not in {"analysis_domain", "analysis-domain"}:
            continue
        source_id = str(record["id"])
        geometry_ref = geometry_refs.get(id(record))
        uncertainties = () if geometry_ref else (_missing_geometry(source_id),)
        return AnalysisDomain(
            id=source_id,
            geometry_refs=(geometry_ref,) if geometry_ref else (),
            source_id=source_id,
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
