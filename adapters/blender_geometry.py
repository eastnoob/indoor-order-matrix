"""Read explicitly selected Blender mesh snapshots into Neutral Scene v2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

if "." in (__package__ or ""):
    from ..features.scene_contract import (
        AnalysisContext,
        AnalysisDomain,
        AnalysisPlane,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MaterialFact,
        MeshGeometry3D,
        NEUTRAL_SCENE_V2,
        NeutralSceneV2,
        SourceObject,
        SourceOpening,
        SurfaceFact,
        UncertaintyRecord,
    )
else:
    from features.scene_contract import (
        AnalysisContext,
        AnalysisDomain,
        AnalysisPlane,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MaterialFact,
        MeshGeometry3D,
        NEUTRAL_SCENE_V2,
        NeutralSceneV2,
        SourceObject,
        SourceOpening,
        SurfaceFact,
        UncertaintyRecord,
    )


BLENDER_ADAPTER_VERSION = "blender-geometry-adapter/0.1.0"
_IDENTITY_4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def _object_records(source: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    """Validate and return the ordered evaluated Blender object snapshots."""
    raw_objects = source.get("objects", ())
    if not isinstance(raw_objects, (list, tuple)):
        raise ValueError("Blender source objects must be an ordered sequence")
    records: list[Mapping[str, object]] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(raw_objects):
        if not isinstance(record, Mapping):
            raise ValueError(f"Blender object {index} must be a mapping")
        object_id = record.get("id")
        if not isinstance(object_id, str) or not object_id.strip():
            raise ValueError(f"Blender object {index} needs a non-empty id")
        if object_id in seen_ids:
            raise ValueError(f"duplicate Blender object id: {object_id}")
        seen_ids.add(object_id)
        records.append(record)
    return tuple(records)


def _selected_record_ids(
    records: Sequence[Mapping[str, object]],
    selected_ids: Sequence[str] | None,
) -> set[str]:
    """Resolve the explicit selection allowlist without consulting visibility or names."""
    if selected_ids is not None:
        return {str(object_id) for object_id in selected_ids}
    selected: set[str] = set()
    for record in records:
        if record.get("selected") is True:
            selected.add(str(record["id"]))
    return selected


def _missing_geometry_uncertainty(object_id: str) -> UncertaintyRecord:
    """Describe why a selected Blender object cannot enter geometry analysis."""
    return UncertaintyRecord(
        code="missing_geometry",
        message="Selected Blender object has no evaluated mesh geometry.",
        source_refs=(f"blender-object:{object_id}",),
        operation="blender_geometry_extraction",
        severity="warning",
        details={
            "adapter": BLENDER_ADAPTER_VERSION,
            "object_id": object_id,
            "bbox_fallback": False,
        },
    )


def _mesh_from_snapshot(
    object_id: str,
    record: Mapping[str, object],
) -> MeshGeometry3D | None:
    """Convert one evaluated Blender mesh snapshot without deriving a bbox."""
    vertices = record.get("vertices")
    triangles = record.get("triangles", record.get("triangle_indices"))
    if vertices is None or triangles is None:
        return None
    normals = record.get("normals", ())
    units = record.get("units", "m")
    return MeshGeometry3D(
        id=f"blender-mesh:{object_id}",
        vertices=vertices,
        triangle_indices=triangles,
        normals=normals,
        is_manifold=record.get("is_manifold"),
        is_closed=record.get("is_closed"),
        local_to_world_provenance={
            "method": "blender_evaluated_mesh",
            "coordinate_space": "world",
            "source_object_id": object_id,
            "transform_applied": bool(record.get("transform_applied", False)),
        },
        source_representation_id=record.get("representation_id"),
        tessellation_settings=record.get("tessellation_settings", {}),
        units=units,
    )


def _source_object_from_snapshot(
    object_id: str,
    record: Mapping[str, object],
    mesh: MeshGeometry3D | None,
    roles: Mapping[str, str],
    *,
    selection_method: str,
    linked_ifc_source_id: str | None = None,
) -> SourceObject:
    """Create a Blender source record while keeping IFC identity absent."""
    uncertainties = () if mesh is not None else (_missing_geometry_uncertainty(object_id),)
    provenance: dict[str, object] = {
        "adapter": BLENDER_ADAPTER_VERSION,
        "method": "explicit_blender_geometry_snapshot",
        "object_id": object_id,
        "object_name": record.get("name") if isinstance(record.get("name"), str) else None,
        "selection_method": selection_method,
        "ifc_identity": None,
    }
    if linked_ifc_source_id is not None:
        provenance["linked_ifc_source_id"] = linked_ifc_source_id
        provenance["link_method"] = "explicit_mapping"
    return SourceObject(
        id=f"blender-object:{object_id}",
        source_id=None,
        source_role=roles.get(object_id),
        source_class=None,
        world_transform=record.get("world_transform", _IDENTITY_4),
        geometry_refs=(mesh.id,) if mesh is not None else (),
        group_refs=tuple(record.get("group_refs", ())),
        material_refs=tuple(record.get("material_refs", ())),
        surface_refs=tuple(record.get("surface_refs", ())),
        authored_local_frame=record.get("authored_local_frame"),
        factual_properties=record.get("factual_properties", {}),
        provenance=provenance,
        uncertainties=uncertainties,
    )


def _context_from_base(
    base: NeutralSceneV2,
    input_mode: str,
    helper_count: int,
    analysis_domain: AnalysisDomain | None = None,
) -> Any:
    """Clone an IFC context with explicit Blender mode provenance."""
    flags = dict(base.context.capability_flags)
    flags["blender_geometry"] = helper_count > 0
    flags["hybrid_links"] = input_mode == "hybrid" and helper_count > 0
    if analysis_domain is not None:
        flags["analysis_domain"] = bool(analysis_domain.geometry_refs)
    return replace(
        base.context,
        adapter_version=BLENDER_ADAPTER_VERSION,
        capability_flags=flags,
        input_mode=input_mode,
    )


def _build_blender_context(
    source: Mapping[str, object],
    input_mode: str,
    geometries: Sequence[MeshGeometry3D],
    analysis_domain: AnalysisDomain | None = None,
) -> Any:
    """Build a source-independent context for ordinary Blender geometry."""
    source_unit = source.get("source_length_unit", "m")
    if not isinstance(source_unit, str):
        raise ValueError("Blender source_length_unit must be a string")
    return AnalysisContext(
        contract_version=NEUTRAL_SCENE_V2,
        source_schema="BLENDER",
        adapter_version=BLENDER_ADAPTER_VERSION,
        source_length_unit=source_unit,
        analysis_length_unit="m",
        world_coordinate_system={
            "method": "blender_evaluated_mesh",
            "coordinate_space": "world",
        },
        level_references=(),
        analysis_plane=AnalysisPlane(
            name="Blender world XY analysis plane",
            origin=(0.0, 0.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        geometry_tolerance=float(source.get("geometry_tolerance", 1e-6)),
        topology_tolerance=float(source.get("topology_tolerance", 1e-6)),
        walking_body_profiles=(),
        visual_height_bands=(),
        capability_flags={
            "blender_geometry": bool(geometries),
            "height": bool(geometries),
            "analysis_domain": bool(
                analysis_domain is not None and analysis_domain.geometry_refs
            ),
        },
        input_mode=input_mode,
    )


def _explicit_blender_records(
    records: Sequence[Mapping[str, object]],
    object_ids: set[str],
    roles: Mapping[str, str],
    *,
    selection_method: str,
    hybrid_links: Mapping[str, str] | None = None,
) -> tuple[tuple[SourceObject, ...], tuple[MeshGeometry3D, ...]]:
    """Build source records for an explicit selection or hybrid link allowlist."""
    source_objects: list[SourceObject] = []
    geometries: list[MeshGeometry3D] = []
    for record in records:
        object_id = str(record["id"])
        if object_id not in object_ids:
            continue
        mesh = _mesh_from_snapshot(object_id, record)
        if mesh is not None:
            geometries.append(mesh)
        linked_id = hybrid_links.get(object_id) if hybrid_links is not None else None
        source_objects.append(
            _source_object_from_snapshot(
                object_id,
                record,
                mesh,
                roles,
                selection_method=selection_method,
                linked_ifc_source_id=linked_id,
            )
        )
    return tuple(source_objects), tuple(geometries)


def _require_reference_subset(
    references: Sequence[str],
    allowed: set[str],
    label: str,
) -> None:
    """Reject explicit cross-record references that do not exist in a scene."""
    dangling = sorted(set(references) - allowed)
    if dangling:
        raise ValueError(f"dangling {label} references: {dangling}")


def _validate_scene_references(scene: NeutralSceneV2) -> None:
    """Validate every adapter-created cross-record reference before handoff."""
    # A cross-layer duplicate makes otherwise valid references ambiguous, so
    # reject it before any downstream analyzer receives the scene.
    all_records = (
        scene.source_objects
        + scene.geometries
        + scene.materials
        + scene.surfaces
        + scene.authored_groups
        + scene.authored_grids
        + scene.authored_grid_axes
        + scene.authored_affordances
        + scene.openings
        + ((scene.analysis_domain,) if scene.analysis_domain is not None else ())
    )
    seen_ids: set[str] = set()
    for record in all_records:
        if record.id in seen_ids:
            raise ValueError(f"duplicate record id: {record.id}")
        seen_ids.add(record.id)
    object_ids = {record.id for record in scene.source_objects}
    geometry_ids = {record.id for record in scene.geometries}
    material_ids = {record.id for record in scene.materials}
    surface_ids = {record.id for record in scene.surfaces}
    group_ids = {record.id for record in scene.authored_groups}
    axis_ids = {record.id for record in scene.authored_grid_axes}
    opening_ids = {record.id for record in scene.openings}
    for record in scene.source_objects:
        _require_reference_subset(record.geometry_refs, geometry_ids, "source geometry")
        _require_reference_subset(record.group_refs, group_ids, "source group")
        _require_reference_subset(record.material_refs, material_ids, "source material")
        _require_reference_subset(record.surface_refs, surface_ids, "source surface")
        _require_reference_subset(record.opening_refs, opening_ids, "source opening")
        _require_reference_subset(record.container_refs, object_ids, "source container")
    for record in scene.authored_groups:
        _require_reference_subset(record.member_refs, object_ids, "group member")
    for record in scene.authored_grids:
        _require_reference_subset(record.axis_refs, axis_ids, "grid axis")
    for record in scene.surfaces:
        _require_reference_subset(record.geometry_refs, geometry_ids, "surface geometry")
        _require_reference_subset(record.host_refs, object_ids, "surface host")
    for record in scene.authored_affordances:
        _require_reference_subset(record.geometry_refs, geometry_ids, "affordance geometry")
        _require_reference_subset(
            record.source_furniture_refs,
            object_ids,
            "affordance furniture",
        )
    for record in scene.openings:
        _require_reference_subset(record.geometry_refs, geometry_ids, "opening geometry")
        _require_reference_subset(record.host_refs, object_ids, "opening host")
    if scene.analysis_domain is not None:
        _require_reference_subset(
            scene.analysis_domain.geometry_refs,
            geometry_ids,
            "analysis domain geometry",
        )


def load_blender_neutral_scene(
    source: Mapping[str, object],
    *,
    mode: str = "blender_geometry",
    selected_ids: Sequence[str] | None = None,
    roles: Mapping[str, str] | None = None,
    ifc_scene: NeutralSceneV2 | None = None,
    hybrid_links: Mapping[str, str] | None = None,
    analysis_domain: AnalysisDomain | None = None,
    authored_groups: Sequence[AuthoredGroup] = (),
    authored_grids: Sequence[AuthoredGrid] = (),
    authored_grid_axes: Sequence[AuthoredGridAxis] = (),
    materials: Sequence[MaterialFact] = (),
    surfaces: Sequence[SurfaceFact] = (),
    authored_affordances: Sequence[AuthoredAffordanceZone] = (),
    openings: Sequence[SourceOpening] = (),
) -> NeutralSceneV2:
    """Load explicit Blender geometry in ``blender_geometry`` or ``hybrid`` mode."""
    if mode not in {"ifc", "blender_geometry", "hybrid"}:
        raise ValueError("Blender adapter mode must be one of ifc, blender_geometry, hybrid")
    if mode == "ifc":
        if ifc_scene is None:
            raise ValueError("ifc mode requires an explicit ifc_scene")
        # IFC mode deliberately ignores the Blender payload and returns the
        # durable IFC facts unchanged, regardless of viewport selection state.
        return ifc_scene
    if not isinstance(source, Mapping):
        raise ValueError("Blender source must be a mapping")
    records = _object_records(source)
    explicit_roles = dict(roles or {})
    if mode == "blender_geometry":
        object_ids = _selected_record_ids(records, selected_ids)
        available_ids = {str(record["id"]) for record in records}
        unknown_selection = sorted(object_ids - available_ids)
        if unknown_selection:
            raise ValueError(
                f"unknown selected Blender object ids: {unknown_selection}"
            )
        selection_method = "explicit_selection"
    else:
        if ifc_scene is None:
            raise ValueError("hybrid mode requires an explicit ifc_scene")
        links = dict(hybrid_links or {})
        object_ids = set(links)
        selection_method = "explicit_ifc_link"
        known_blender_ids = {str(record["id"]) for record in records}
        unknown_helpers = sorted(object_ids - known_blender_ids)
        if unknown_helpers:
            raise ValueError(f"unknown Blender helper ids: {unknown_helpers}")
        known_ifc_ids = {
            item.source_id or item.id for item in ifc_scene.source_objects
        }
        unknown_links = sorted(set(links.values()) - known_ifc_ids)
        if unknown_links:
            raise ValueError(f"hybrid links reference unknown IFC ids: {unknown_links}")
    unknown_roles = sorted(set(explicit_roles) - object_ids)
    if unknown_roles:
        raise ValueError(f"unknown Blender role ids: {unknown_roles}")
    source_objects, geometries = _explicit_blender_records(
        records,
        object_ids,
        explicit_roles,
        selection_method=selection_method,
        hybrid_links=dict(hybrid_links or {}) if mode == "hybrid" else None,
    )
    if mode == "hybrid":
        assert ifc_scene is not None
        selected_domain = analysis_domain or ifc_scene.analysis_domain
        context = _context_from_base(
            ifc_scene,
            mode,
            len(source_objects),
            selected_domain,
        )
        result = replace(
            ifc_scene,
            context=context,
            source_objects=ifc_scene.source_objects + source_objects,
            geometries=ifc_scene.geometries + geometries,
            authored_groups=ifc_scene.authored_groups + tuple(authored_groups),
            authored_grids=ifc_scene.authored_grids + tuple(authored_grids),
            authored_grid_axes=ifc_scene.authored_grid_axes + tuple(authored_grid_axes),
            materials=ifc_scene.materials + tuple(materials),
            surfaces=ifc_scene.surfaces + tuple(surfaces),
            authored_affordances=ifc_scene.authored_affordances
            + tuple(authored_affordances),
            openings=ifc_scene.openings + tuple(openings),
            analysis_domain=analysis_domain or ifc_scene.analysis_domain,
        )
        _validate_scene_references(result)
        return result
    context = _build_blender_context(source, mode, geometries, analysis_domain)
    result = NeutralSceneV2(
        context=context,
        analysis_domain=analysis_domain,
        source_objects=source_objects,
        geometries=geometries,
        authored_groups=tuple(authored_groups),
        authored_grids=tuple(authored_grids),
        authored_grid_axes=tuple(authored_grid_axes),
        materials=tuple(materials),
        surfaces=tuple(surfaces),
        authored_affordances=tuple(authored_affordances),
        openings=tuple(openings),
    )
    _validate_scene_references(result)
    return result


__all__ = ["BLENDER_ADAPTER_VERSION", "load_blender_neutral_scene"]
