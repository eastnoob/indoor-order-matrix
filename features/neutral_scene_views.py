"""Derived planar analysis views over source-independent Neutral Scene facts."""

from __future__ import annotations

from collections.abc import Mapping
from math import atan2, cos, degrees, radians, sin
from typing import TypeAlias

from .affordance.models import Rect
from .boundary_evidence import (
    derive_boundary_evidence,
    derive_boundary_evidence_for_collection,
)
from .geometry_substitutes import mass_patch_from_mesh, surface_patch_from_fact
from .geometry_views import plan_projection
from .scene_contract import NeutralSceneV2, SourceObject, SourceOpening, UncertaintyRecord


LegacyAnalysisScene: TypeAlias = dict[str, object]
AnalysisSceneInput: TypeAlias = LegacyAnalysisScene | NeutralSceneV2


def analysis_scene_view(scene: AnalysisSceneInput) -> LegacyAnalysisScene:
    """Return the canonical planar consumer view for either supported scene form."""
    if isinstance(scene, NeutralSceneV2):
        return _neutral_scene_view(scene)
    if isinstance(scene, dict):
        return scene
    raise TypeError("scene must be a legacy analysis mapping or NeutralSceneV2")


def _analysis_scene_view_with_semantic_enclosure(
    scene: NeutralSceneV2, *, request: Mapping[str, object]
) -> LegacyAnalysisScene:
    """Add explicitly authorized enclosure evidence to a private B2 child."""
    # Lazy handoff keeps the ordinary consumer path and its imports unchanged.
    from ._semantic_enclosure import semantic_enclosure_diagnostics, validate_request

    validate_request(scene, request)
    view = analysis_scene_view(scene)
    diagnostics = view["_analysis_view"]["b2_boundary_diagnostics"]
    diagnostics["semantic_enclosure"] = semantic_enclosure_diagnostics(
        scene, request, diagnostics["openings"]
    )
    return view


def _analysis_scene_view_with_domain_handoff(
    scene: NeutralSceneV2, *, candidates=(), session_state=None, action=None,
    expected_session_revision=None, expected_source_revision=None,
    frame_request: Mapping[str, object], b2_request: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Qualify one private session choice without exposing formal field consumers."""
    from ._analysis_domain_handoff import domain_handoff

    b2 = None
    if b2_request is not None:
        # The accepted B2 helper remains the only semantic-carrier authority.
        view = _analysis_scene_view_with_semantic_enclosure(scene, request=b2_request)
        b2 = view["_analysis_view"]["b2_boundary_diagnostics"]["semantic_enclosure"]
    return domain_handoff(
        scene, candidates=candidates, session_state=session_state, action=action,
        expected_session_revision=expected_session_revision,
        expected_source_revision=expected_source_revision,
        frame_request=frame_request, b2=b2, b2_request=b2_request,
    )


def _neutral_scene_view(scene: NeutralSceneV2) -> LegacyAnalysisScene:
    """Project Neutral Scene facts into the existing planar analysis vocabulary."""
    plane = scene.context.analysis_plane
    geometry_components = {
        geometry.id: _projection_components(geometry, plane)
        for geometry in scene.geometries
    }
    geometry_points = {
        geometry_id: tuple(
            point
            for component in components
            for point in component["exterior"]
        )
        for geometry_id, components in geometry_components.items()
    }
    axis_points = {
        axis.id: tuple(_project_point(point, plane) for point in axis.curve_points)
        for axis in scene.authored_grid_axes
    }
    domain_points = _domain_points(scene, geometry_points)
    bounds_points = domain_points or [
        point
        for points in (*geometry_points.values(), *axis_points.values())
        for point in points
    ]
    offset, size = _view_frame(bounds_points)

    # Every source category is shifted by the same analysis-view offset, so
    # object, affordance, opening, and grid relations retain their geometry.
    shifted_geometry = {
        geometry_id: tuple(_shift_point(point, offset) for point in points)
        for geometry_id, points in geometry_points.items()
    }
    shifted_components = {
        geometry_id: tuple(
            _shift_component(component, offset) for component in components
        )
        for geometry_id, components in geometry_components.items()
    }
    shifted_axes = {
        axis_id: tuple(_shift_point(point, offset) for point in points)
        for axis_id, points in axis_points.items()
    }
    group_by_member = _group_membership(scene)
    affordances_by_owner = _affordance_records(scene, shifted_geometry)
    records = [
        _source_record(
            source,
            shifted_geometry,
            shifted_components,
            group_by_member,
            affordances_by_owner,
        )
        for source in scene.source_objects
    ]
    records = [record for record in records if record is not None]
    channel_evidence, channel_capabilities = _neutral_channel_evidence(
        scene,
        records,
    )
    surface_interfaces = _surface_interface_records(
        scene,
        shifted_geometry,
        shifted_components,
    )
    # Attach evidence after planar records exist so every downstream blocker
    # keeps the exact same geometry and stable source id.
    records = [
        record
        | {
            "channel_evidence": channel_evidence.get(record["id"]),
        }
        for record in records
    ]
    records_by_id = {record["id"]: record for record in records}
    shell_record_ids, domain_scope = _domain_shell_identity(
        scene,
        records,
        domain_available=bool(domain_points),
    )
    # Keep the legacy interface-candidacy rule separate from B2 occupancy:
    # support geometry is context for interface selection, not mass exclusion.
    support_geometry_refs = (
        set(scene.analysis_domain.geometry_refs)
        if scene.analysis_domain is not None
        else set()
    )
    interface_facts = [
        record
        for record in records
        if record["id"] in channel_evidence
        and not support_geometry_refs.intersection(
            record.get("_source_geometry_refs", ())
        )
    ] + [
        record
        | {"channel_evidence": channel_evidence.get(record["id"])}
        for record in surface_interfaces
    ]
    # Physical occupancy follows explicit mass geometry, not source-role labels.
    # Exclude a selected support only when exact source identity proves the match.
    physical_mass_records = [
        record
        for record in records
        if _is_physical_mass_record(record)
        and record["id"] not in shell_record_ids
    ]
    walk_blockers = _channel_blocker_records(
        records_by_id,
        channel_evidence,
        channel="walking",
        offset=offset,
        excluded_record_ids=shell_record_ids,
    )
    visibility_blockers = _channel_blocker_records(
        records_by_id,
        channel_evidence,
        channel="visual",
        offset=offset,
    )
    openings = _opening_records(scene, shifted_geometry)
    b2_boundary_diagnostics = _b2_boundary_diagnostics(
        scene,
        records,
        shell_record_ids,
        domain_scope,
    )
    column_axes = _axis_records(scene, shifted_axes)
    settings = _analysis_settings(scene)
    source = f"{scene.context.source_schema}:{scene.context.adapter_version}"
    return {
        "source": source,
        "size": size,
        "settings": settings,
        "objects": _records_for_bucket(records, "objects"),
        "boundaries": _records_for_bucket(records, "boundaries"),
        "boundary_facts": _records_for_bucket(records, "boundary_facts"),
        # Preserve the old boundary-only field for legacy consumers; Neutral
        # occupancy uses the separate role-neutral mass collection below.
        "physical_blockers": _records_for_bucket(records, "boundaries")
        + _records_for_bucket(records, "boundary_facts"),
        "physical_occupancy": physical_mass_records,
        "walk_blockers": walk_blockers,
        "visibility_blockers": visibility_blockers,
        "channel_evidence": channel_evidence,
        "interface_facts": interface_facts,
        "entries": openings or _records_for_bucket(records, "entries"),
        "paths": _records_for_bucket(records, "paths"),
        "columns": _records_for_bucket(records, "columns"),
        "column_axes": column_axes,
        "regions": _records_for_bucket(records, "regions"),
        "uncertainties": [record.to_dict() for record in scene.uncertainties],
        "_neutral_scene": scene,
        "_analysis_view": {
            "method": "neutral_scene_plan_projection",
            "origin_offset": offset,
            "analysis_plane": plane.name,
            "input_mode": scene.context.input_mode,
            "capability_flags": _normalized_capability_flags(
                scene,
                domain_available=bool(domain_points),
                channel_capabilities=channel_capabilities,
            ),
            "domain_available": bool(domain_points),
            "view_bounds_basis": (
                "explicit_analysis_domain"
                if domain_points
                else "scene_geometry_fallback_not_analysis_domain"
            ),
            "b2_boundary_diagnostics": b2_boundary_diagnostics,
        },
    }


def _surface_interface_records(
    scene: NeutralSceneV2,
    geometry_points: Mapping[str, tuple[tuple[float, float], ...]],
    geometry_components: Mapping[str, tuple[dict[str, object], ...]],
) -> list[dict[str, object]]:
    """Build planar interface records from explicit surface facts."""
    records = []
    for surface in scene.surfaces:
        points = [
            point
            for geometry_ref in surface.geometry_refs
            for point in geometry_points.get(geometry_ref, ())
        ]
        hull = _convex_hull(points) if points else []
        frame = _geometry_frame(hull) if hull else None
        records.append(
            {
                "id": f"surface:{surface.id}",
                "role": "surface",
                "interface_kind": "surface",
                "rect": _points_rect(hull) if hull else None,
                "points": hull,
                "geometry_components": [
                    component
                    for geometry_ref in surface.geometry_refs
                    for component in geometry_components.get(geometry_ref, ())
                ],
                "metadata": {
                    "role": "surface",
                    "surface-identity": surface.identity,
                    "color": surface.color,
                    "elevation": surface.elevation,
                    "orientation": (
                        str(round(frame["angle"], 8)) if frame else None
                    ),
                    "geometry-view": "neutral_scene_surface_projection",
                },
                "_source_geometry_refs": list(surface.geometry_refs),
                "_neutral_source_id": surface.source_id,
            }
        )
    return records


def _neutral_channel_evidence(
    scene: NeutralSceneV2,
    records: list[dict],
) -> tuple[dict[str, dict[str, object]], dict[str, bool]]:
    """Derive four independent boundary channels from explicit Neutral facts."""
    geometry_by_id = {geometry.id: geometry for geometry in scene.geometries}
    mass_patch_by_id = {
        geometry_id: mass_patch_from_mesh(geometry)
        for geometry_id, geometry in geometry_by_id.items()
    }
    material_by_id = {material.id: material for material in scene.materials}
    record_by_id = {record["id"]: record for record in records}
    body_profiles = _explicit_height_queries(scene.context.walking_body_profiles)
    visual_bands = _explicit_height_queries(scene.context.visual_height_bands)
    result: dict[str, dict[str, object]] = {}
    for source in scene.source_objects:
        record = record_by_id.get(source.id)
        if record is None:
            continue
        patches = tuple(
            mass_patch_by_id[reference]
            for reference in source.geometry_refs
            if reference in mass_patch_by_id
        )
        optical_evidence = _source_optical_evidence(source, material_by_id)
        transmittance = optical_evidence["visible_transmittance"]
        optical = {
            patch.source_geometry_id: transmittance
            for patch in patches
        }
        patch_evidence = (
            (
                derive_boundary_evidence_for_collection(
                    patches,
                    body_profiles=body_profiles,
                    visual_bands=visual_bands,
                    optical_transmittance=transmittance,
                    use_default_queries=False,
                    analysis_plane=scene.context.analysis_plane,
                    height_tolerance=scene.context.geometry_tolerance,
                ),
            )
            if patches
            else ()
        )
        result[source.id] = _channel_evidence_payload(
            patch_evidence,
            body_profiles,
            visual_bands,
            geometry_refs=list(source.geometry_refs),
            material_refs=list(source.material_refs),
            visible_transmittance=transmittance,
            optical_assignment_status=str(optical_evidence["status"]),
            optical_uncertainty=optical_evidence.get("uncertainty"),
            interface_kind="mass",
            source_role=record.get("role", "unknown"),
        )

    surface_patches = tuple(surface_patch_from_fact(surface) for surface in scene.surfaces)
    if surface_patches:
        # Surface projection needs referenced mass geometry for location only;
        # derive_boundary_evidence keeps the surface non-mass and permeable.
        surface_evidence = derive_boundary_evidence(
            (*mass_patch_by_id.values(), *surface_patches),
            body_profiles=body_profiles,
            visual_bands=visual_bands,
            use_default_queries=False,
            analysis_plane=scene.context.analysis_plane,
            height_tolerance=scene.context.geometry_tolerance,
        )[-len(surface_patches):]
        for surface, patch_evidence in zip(scene.surfaces, surface_evidence):
            result[f"surface:{surface.id}"] = _channel_evidence_payload(
                (patch_evidence,),
                body_profiles,
                visual_bands,
                geometry_refs=list(surface.geometry_refs),
                material_refs=[],
                visible_transmittance=None,
                optical_assignment_status="not_applicable",
                optical_uncertainty=None,
                interface_kind="surface",
                source_role="surface",
            )

    evidence_records = [
        evidence
        for evidence in result.values()
        if evidence["interface_kind"] == "mass"
    ]
    complete_geometry = bool(evidence_records) and all(
        evidence["geometry_status"] == "usable" for evidence in evidence_records
    )
    visual_resolved = bool(evidence_records) and all(
        item["status"] != "unknown"
        for evidence in evidence_records
        for item in evidence["visual"]
    )
    return result, {
        "walking_profile_queries": bool(body_profiles),
        "visual_band_queries": bool(visual_bands),
        "closed_manifold_mass_geometry": complete_geometry,
        "walk_channel": bool(body_profiles) and complete_geometry,
        "visibility_channel": bool(visual_bands) and complete_geometry and visual_resolved,
        "isovist_channel": bool(visual_bands) and complete_geometry and visual_resolved,
    }


def _channel_evidence_payload(
    patch_evidence: tuple[object, ...],
    body_profiles: tuple[Mapping[str, object], ...],
    visual_bands: tuple[Mapping[str, object], ...],
    *,
    geometry_refs: list[str],
    material_refs: list[str],
    visible_transmittance: object,
    optical_assignment_status: str,
    optical_uncertainty: object,
    interface_kind: str,
    source_role: str,
) -> dict[str, object]:
    """Serialize four patch channels without inventing an aggregate strength."""
    geometry_usable = bool(patch_evidence) and all(
        evidence.physical_continuity.get("channel_geometry_status") == "usable"
        for evidence in patch_evidence
        if evidence.physical_continuity.get("mass_present")
    )
    walking = _aggregate_patch_channels(
        patch_evidence,
        body_profiles,
        channel="walking_permeability",
        identifier_key="profile_id",
    )
    visual = _aggregate_patch_channels(
        patch_evidence,
        visual_bands,
        channel="visual_permeability",
        identifier_key="band_id",
    )
    # Physical and Gestalt observations remain patch-granular because reducing
    # them would invent one object-wide continuity or grouping value.
    return {
        "interface_kind": interface_kind,
        "source_role": source_role,
        "geometry_refs": geometry_refs,
        "material_refs": material_refs,
        "visible_transmittance": visible_transmittance,
        "optical_assignment_status": optical_assignment_status,
        "optical_assignment_uncertainty": optical_uncertainty,
        "geometry_status": "usable" if geometry_usable else "unknown",
        "physical_continuity": [
            dict(evidence.physical_continuity) for evidence in patch_evidence
        ],
        "walking": walking,
        "walking_status": _channel_evaluation_status(
            walking,
            queries_present=bool(body_profiles),
        ),
        "visual": visual,
        "visual_status": _channel_evaluation_status(
            visual,
            queries_present=bool(visual_bands),
        ),
        "gestalt_continuity": [
            dict(evidence.gestalt_continuity) for evidence in patch_evidence
        ],
        "uncertainties": sorted(
            {
                uncertainty
                for evidence in patch_evidence
                for uncertainty in evidence.uncertainties
            }
            | ({str(optical_uncertainty)} if optical_uncertainty else set())
        ),
    }


def _channel_evaluation_status(
    observations: list[dict[str, object]],
    *,
    queries_present: bool,
) -> str:
    """Report whether a queried channel is resolved without hiding unknowns."""
    if not queries_present or not observations:
        return "unknown"
    return (
        "unknown"
        if any(observation.get("status") == "unknown" for observation in observations)
        else "evaluated"
    )


def _explicit_height_queries(
    records: tuple[object, ...],
) -> tuple[Mapping[str, object], ...]:
    """Select named height-band queries without promoting width-only settings."""
    return tuple(
        record
        for record in records
        if isinstance(record, Mapping)
        and isinstance(record.get("id"), str)
        and bool(record.get("id"))
        and isinstance(record.get("height_band"), (tuple, list))
        and len(record["height_band"]) == 2
    )


def _source_optical_evidence(
    source: SourceObject,
    material_by_id: Mapping[str, object],
) -> dict[str, object]:
    """Resolve object-wide optics only when all unassigned material refs agree."""
    if not source.material_refs:
        return {
            "status": "unknown",
            "visible_transmittance": None,
            "uncertainty": "missing_visible_transmittance",
        }
    materials = [material_by_id.get(reference) for reference in source.material_refs]
    if any(material is None for material in materials):
        return {
            "status": "unknown",
            "visible_transmittance": None,
            "uncertainty": "missing_material_reference",
        }
    values = [material.visible_transmittance for material in materials]
    if any(value is None for value in values):
        # Viewport transparency is intentionally excluded: only authored
        # visible transmittance can establish optical transmission.
        return {
            "status": "unknown",
            "visible_transmittance": None,
            "uncertainty": "incomplete_visible_transmittance",
        }
    normalized = {float(value) for value in values}
    if len(normalized) != 1:
        # Material-to-face assignment is absent at this contract level, so a
        # min/max reduction would invent one object-wide optical fact.
        return {
            "status": "ambiguous",
            "visible_transmittance": None,
            "uncertainty": "ambiguous_material_optical_assignment",
        }
    return {
        "status": "resolved",
        "visible_transmittance": normalized.pop(),
        "uncertainty": None,
    }


def _aggregate_patch_channels(
    evidence_records: tuple[object, ...],
    queries: tuple[Mapping[str, object], ...],
    *,
    channel: str,
    identifier_key: str,
) -> list[dict[str, object]]:
    """Aggregate per-geometry channel facts without hiding unknown patches."""
    result = []
    for query in queries:
        identifier = query["id"]
        items = [
            item
            for evidence in evidence_records
            for item in getattr(evidence, channel)
            if item[identifier_key] == identifier
        ]
        statuses = [item["status"] for item in items]
        status = "blocked" if "blocked" in statuses else (
            "unknown" if not items or "unknown" in statuses else (
                "transmitting"
                if channel == "visual_permeability" and "transmitting" in statuses
                else "clear"
            )
        )
        aggregate = dict(items[0]) if items else {
            identifier_key: identifier,
            "height_band": tuple(query["height_band"]),
        }
        aggregate["status"] = status
        aggregate["query_projections"] = [
            item["query_projection"]
            for item in items
            if (item.get("query_projection") or {}).get("components")
        ]
        aggregate["blocker_projections"] = [
            item["query_projection"]
            for item in items
            if item["status"] == "blocked"
            and (item.get("query_projection") or {}).get("components")
        ]
        if channel == "walking_permeability":
            aggregate["collision_intervals"] = tuple(
                sorted(
                    {
                        interval
                        for item in items
                        for interval in item.get("collision_intervals", ())
                    }
                )
            )
        else:
            geometry_statuses = [item["geometry_status"] for item in items]
            aggregate["geometry_status"] = (
                "blocked"
                if "blocked" in geometry_statuses
                else "unknown"
                if not items or "unknown" in geometry_statuses
                else "clear"
            )
        result.append(aggregate)
    return result


def _channel_blocker_records(
    records_by_id: Mapping[str, dict],
    channel_evidence: Mapping[str, dict[str, object]],
    *,
    channel: str,
    offset: tuple[float, float],
    excluded_record_ids: set[str] | None = None,
) -> list[dict]:
    """Build task blockers while excluding only proven analysis-domain records."""
    blockers = []
    excluded_record_ids = excluded_record_ids or set()
    for source_id, evidence in channel_evidence.items():
        record = records_by_id.get(source_id)
        if record is None:
            continue
        # Geometry references can be shared by distinct source records, so only
        # an exact source-identity match may remove an analysis-domain shell.
        if record["id"] in excluded_record_ids:
            continue
        projections = [
            projection
            for item in evidence[channel]
            for projection in item.get("blocker_projections", ())
        ]
        components = _unique_shifted_projection_components(projections, offset)
        if not components:
            continue
        points = [
            point
            for component in components
            for point in component["exterior"]
        ]
        blocker = dict(record)
        blocker["geometry_components"] = components
        blocker["points"] = _convex_hull(points)
        blocker["rect"] = _points_rect(points)
        blockers.append(blocker)
    return blockers


def _unique_shifted_projection_components(
    projections: list[Mapping[str, object]],
    offset: tuple[float, float],
) -> list[dict[str, object]]:
    """Shift and deduplicate query components without filling holes or gaps."""
    components = []
    seen = set()
    for projection in projections:
        for component in projection.get("components", ()):
            shifted = _shift_component(component, offset)
            key = (shifted["exterior"], shifted["holes"])
            if key in seen:
                continue
            seen.add(key)
            components.append(shifted)
    return components


def _normalized_capability_flags(
    scene: NeutralSceneV2,
    *,
    domain_available: bool,
    channel_capabilities: Mapping[str, bool],
) -> dict[str, bool]:
    """Expose adapter aliases and canonical analysis capabilities together."""
    flags = dict(scene.context.capability_flags)
    flags.update(channel_capabilities)
    flags["analysis_domain"] = domain_available
    flags["physical_planar_occupancy"] = bool(scene.geometries)
    return flags


def _projection_components(geometry, plane) -> tuple[dict[str, object], ...]:
    """Project one transport mesh while retaining components and holes."""
    projection = plan_projection(mass_patch_from_mesh(geometry), plane)
    return tuple(
        {
            "exterior": tuple(
                (float(x), float(y)) for x, y in component.get("exterior", ())
            ),
            "holes": tuple(
                tuple((float(x), float(y)) for x, y in hole)
                for hole in component.get("holes", ())
            ),
        }
        for component in projection.components
    )


def _project_point(point, plane) -> tuple[float, float]:
    """Project a world point into the authored orthonormal analysis plane."""
    relative = tuple(point[index] - plane.origin[index] for index in range(3))
    return (
        sum(relative[index] * plane.basis[0][index] for index in range(3)),
        sum(relative[index] * plane.basis[1][index] for index in range(3)),
    )


def _domain_points(
    scene: NeutralSceneV2,
    geometry_points: Mapping[str, tuple[tuple[float, float], ...]],
) -> list[tuple[float, float]]:
    """Return explicit domain points when the source selected a measurable domain."""
    if scene.analysis_domain is None:
        return []
    return [
        point
        for geometry_ref in scene.analysis_domain.geometry_refs
        for point in geometry_points.get(geometry_ref, ())
    ]


def _domain_shell_identity(
    scene: NeutralSceneV2,
    records: list[dict],
    *,
    domain_available: bool,
) -> tuple[set[str], dict[str, object]]:
    """Resolve only an exact, unique source identity for an explicit domain shell."""
    domain = scene.analysis_domain
    if domain is None:
        return set(), {
            "availability": "not_available",
            "source": "none",
            "id": None,
            "geometry_refs": [],
            "shell_record_ids": [],
            "shell_identity": "not_applicable",
            "blocker": None,
        }

    scope: dict[str, object] = {
        "availability": "available" if domain_available else "not_available",
        "source": "explicit_authored",
        "id": domain.id,
        "geometry_refs": list(domain.geometry_refs),
        "shell_record_ids": [],
        "shell_identity": "blocked",
        "blocker": None,
    }
    if not domain_available:
        scope["blocker"] = "analysis_domain_geometry_unavailable"
        return set(), scope

    source_id = domain.source_id
    if source_id is None or not source_id.strip():
        scope["blocker"] = "analysis_domain_source_id_missing"
        return set(), scope

    matches = [source for source in scene.source_objects if source.source_id == source_id]
    if not matches:
        scope["blocker"] = "analysis_domain_source_id_unmatched"
        return set(), scope
    if len(matches) != 1:
        scope["blocker"] = "analysis_domain_source_id_ambiguous"
        return set(), scope

    source = matches[0]
    role = (source.source_role or "").strip().lower()
    if not role or role in {"wall", "boundary", "column"}:
        scope["blocker"] = "analysis_domain_source_role_ineligible"
        return set(), scope

    record_ids = {
        str(record["id"])
        for record in records
        if record.get("id") == source.id
    }
    if len(record_ids) != 1:
        scope["blocker"] = "analysis_domain_source_record_unavailable"
        return set(), scope

    scope["shell_record_ids"] = sorted(record_ids)
    scope["shell_identity"] = "established"
    return record_ids, scope


def _opening_uncertainty_records(
    opening: SourceOpening,
    scene_uncertainties: tuple[UncertaintyRecord, ...],
) -> list[UncertaintyRecord]:
    """Join local and scene uncertainty only through the exact opening reference."""
    records = list(opening.uncertainties)
    for uncertainty in scene_uncertainties:
        if opening.id in uncertainty.source_refs and uncertainty not in records:
            records.append(uncertainty)
    return records


def _opening_local_diagnostic_state(
    opening: SourceOpening,
    scene_uncertainties: tuple[UncertaintyRecord, ...],
) -> tuple[str, str, list[str]]:
    """Apply the local opening evidence precedence without qualifying subtraction."""
    uncertainties = _opening_uncertainty_records(opening, scene_uncertainties)
    codes = [record.code.strip().lower() for record in uncertainties]
    omitted_host_refs: list[str] = []
    for uncertainty in uncertainties:
        if (
            uncertainty.code == "unresolved_opening_host_ref"
            and (
                uncertainty in opening.uncertainties
                or opening.id in uncertainty.source_refs
            )
        ):
            raw_omitted = uncertainty.details.get("omitted_refs", ())
            values = (raw_omitted,) if isinstance(raw_omitted, str) else raw_omitted
            if isinstance(values, (list, tuple)):
                omitted_host_refs.extend(
                    value for value in values if isinstance(value, str) and value
                )
    omitted_host_refs = list(dict.fromkeys(omitted_host_refs))

    if any("conflict" in code for code in codes):
        return "conflict", "opening_uncertainty_reports_conflict", omitted_host_refs
    if any("unsupported" in code for code in codes):
        return "unsupported", "opening_uncertainty_reports_unsupported", omitted_host_refs
    if any("invalid" in code or "malformed" in code for code in codes):
        return "invalid", "opening_uncertainty_reports_invalid_or_malformed", omitted_host_refs
    if omitted_host_refs or bool(opening.host_refs) != bool(opening.geometry_refs):
        return "partial", "opening_host_or_geometry_incomplete", omitted_host_refs
    if (
        (not opening.host_refs and not opening.geometry_refs)
        or "missing_geometry" in codes
    ):
        return "not_available", "opening_host_or_geometry_unavailable", omitted_host_refs
    return (
        "diagnostic_only",
        "opening_facts_present_without_qualification_policy",
        omitted_host_refs,
    )


def _b2_opening_diagnostic(
    opening: SourceOpening,
    scene_uncertainties: tuple[UncertaintyRecord, ...],
) -> dict[str, object]:
    """Serialize one opening's source facts and refusal state for private diagnostics."""
    state, reason, omitted_host_refs = _opening_local_diagnostic_state(
        opening,
        scene_uncertainties,
    )
    uncertainties = _opening_uncertainty_records(opening, scene_uncertainties)
    source_refs = [opening.id]
    if opening.source_id:
        source_refs.append(opening.source_id)
    source_refs.extend(opening.host_refs)
    source_refs.extend(omitted_host_refs)
    source_refs.extend(opening.geometry_refs)
    source_refs.extend(
        source_ref
        for uncertainty in uncertainties
        for source_ref in uncertainty.source_refs
    )
    return {
        "id": opening.id,
        "source_id": opening.source_id,
        "host_refs": list(opening.host_refs),
        "omitted_host_refs": omitted_host_refs,
        "geometry_refs": list(opening.geometry_refs),
        "opening_kind": opening.opening_kind,
        "provenance": opening.to_dict()["provenance"],
        "uncertainties": [record.to_dict() for record in uncertainties],
        "local_diagnostic_state": state,
        "reason": reason,
        "source_refs": list(dict.fromkeys(source_refs)),
        "subtraction_performed": False,
    }


def _b2_boundary_diagnostics(
    scene: NeutralSceneV2,
    records: list[dict],
    domain_shell_record_ids: set[str],
    domain_scope: dict[str, object],
) -> dict[str, object]:
    """Build private provenance/refusal diagnostics from existing scene records."""
    physical_occupancy = []
    boundary_support = []
    for record in records:
        if (
            record["id"] in domain_shell_record_ids
            or not _is_physical_mass_record(record)
        ):
            continue
        source_id = record.get("_neutral_source_id")
        source_role = str(record.get("role", "unknown")).strip().lower()
        geometry_refs = list(record.get("_source_geometry_refs", ()))
        physical_occupancy.append(
            {
                "source_id": source_id,
                "source_role": source_role,
                "geometry_refs": geometry_refs,
                "included": True,
            }
        )
        if source_role not in {"wall", "boundary", "column"}:
            continue
        source_refs = [str(record["id"])]
        if source_id:
            source_refs.append(str(source_id))
        source_refs.extend(str(ref) for ref in geometry_refs)
        boundary_support.append(
            {
                "source_id": source_id,
                "candidate_segment_ids": [source_id] if source_id else [],
                "conditional_support": False,
                "local_diagnostic_state": "diagnostic_only",
                "reason": "b2_loop_closure_policy_deferred",
                "source_refs": list(dict.fromkeys(source_refs)),
            }
        )

    return {
        "schema": "d6-b2-neutral-scene-diagnostics/v2",
        "evidence_class": "source_fact_and_refusal_plumbing",
        "domain_scope": domain_scope,
        "candidate_promotion": {
            "status": "refused",
            "reason": "inferred_candidate_promotion_not_authorized",
        },
        "physical_occupancy": physical_occupancy,
        "boundary_support": boundary_support,
        "candidate_polygon_validity": {
            "status": "not_available",
            "reason": "no_current_source_observation",
            "source_refs": [],
        },
        "source_components": {
            "status": "not_available",
            "reason": "no_current_source_observation",
            "source_segment_ids": [],
        },
        "openings": [
            _b2_opening_diagnostic(opening, scene.uncertainties)
            for opening in scene.openings
        ],
        "downstream": {
            "subtraction": "refused",
            "free_space": "not_evaluated",
            "route": "not_evaluated",
        },
    }


def _view_frame(
    points: list[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return a zero-based analysis offset and stable positive view size."""
    if not points:
        return (0.0, 0.0), (0.0, 0.0)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return (-left, -top), (right - left, bottom - top)


def _shift_point(
    point: tuple[float, float],
    offset: tuple[float, float],
) -> tuple[float, float]:
    """Apply the common zero-based analysis-view translation."""
    return (point[0] + offset[0], point[1] + offset[1])


def _shift_component(
    component: Mapping[str, object],
    offset: tuple[float, float],
) -> dict[str, object]:
    """Shift one exact projected component without changing its topology."""
    return {
        "exterior": tuple(
            _shift_point(point, offset) for point in component.get("exterior", ())
        ),
        "holes": tuple(
            tuple(_shift_point(point, offset) for point in hole)
            for hole in component.get("holes", ())
        ),
    }


def _group_membership(scene: NeutralSceneV2) -> dict[str, str]:
    """Resolve explicit furniture-group membership without name inference."""
    memberships: dict[str, str] = {}
    furniture_ids = {
        source.id
        for source in scene.source_objects
        if (source.source_role or "").strip().lower()
        in {"furniture", "table", "chair", "sofa", "cabinet", "shelf", "desk", "stool", "bench"}
    }
    for group in scene.authored_groups:
        # A generic authored group becomes a furniture group only when every
        # referenced member is factual furniture; no source-specific role name
        # is required at this consumer boundary.
        all_members_are_furniture = bool(group.member_refs) and all(
            member_ref in furniture_ids for member_ref in group.member_refs
        )
        if group.group_role != "furniture_group" and not all_members_are_furniture:
            continue
        for member_ref in group.member_refs:
            memberships.setdefault(member_ref, group.id)
    return memberships


def _source_record(
    source: SourceObject,
    geometry_points: Mapping[str, tuple[tuple[float, float], ...]],
    geometry_components: Mapping[str, tuple[dict[str, object], ...]],
    group_by_member: Mapping[str, str],
    affordances_by_owner: Mapping[str, list[dict]],
) -> dict | None:
    """Build one planar compatibility record from neutral object facts and views."""
    role = (source.source_role or "unknown").strip().lower()
    if role in {"affordance", "affordance_zone", "column_axis", "column_grid", "opening"}:
        return None
    points = [
        point
        for geometry_ref in source.geometry_refs
        for point in geometry_points.get(geometry_ref, ())
    ]
    if not points:
        return None
    hull = _convex_hull(points)
    rect = _points_rect(hull)
    facts = _source_facts(source)
    group = _text_fact(facts, "group") or group_by_member.get(source.id) or source.id
    region = _text_fact(facts, "region") or group
    # Terminal projected geometry is authoritative for Neutral Scene analysis;
    # authored local orientation is retained only as audit provenance.
    authored_orientation = _authored_orientation(source)
    frame = _geometry_frame(hull)
    orientation = frame["angle"]
    frame_source = "terminal_projected_analysis_geometry"
    metadata = {
        **facts,
        "role": _text_fact(facts, "role") or role,
        "group": group,
        "region": region,
        "orientation": str(round(orientation, 8)),
        "frame-primary-extent": str(round(frame["primary_extent"], 8)),
        "frame-secondary-extent": str(round(frame["secondary_extent"], 8)),
        "frame-source": frame_source,
        "historical-orientation": (
            str(round(authored_orientation, 8))
            if authored_orientation is not None
            else None
        ),
        "geometry-view": "neutral_scene_plan_projection",
    }
    record = {
        "id": source.id,
        "role": metadata["role"],
        "group": group,
        "region": region,
        "furniture_group": group_by_member.get(source.id),
        "rect": rect,
        "points": hull,
        "geometry_components": [
            component
            for geometry_ref in source.geometry_refs
            for component in geometry_components.get(geometry_ref, ())
        ],
        "metadata": metadata,
        "adapter_refs": dict(source.provenance.get("adapter_refs", {})),
        "_source_geometry_refs": list(source.geometry_refs),
        "_authored_affordance_zones": list(affordances_by_owner.get(source.id, [])),
        "_neutral_source_id": source.source_id,
    }
    bucket = _record_bucket(role)
    if bucket == "boundaries":
        bucket = "boundary_facts"
    record["_analysis_bucket"] = bucket
    return record


def _source_facts(source: SourceObject) -> dict[str, object]:
    """Return explicit factual properties without promoting provenance metadata."""
    forbidden = {
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
    # Provenance, including adapter-preserved source metadata, is audit-only.
    # Analysis truth must enter through factual properties or typed Neutral Scene relations.
    return {
        str(key): value
        for key, value in source.factual_properties.items()
        if str(key).lower() not in forbidden
    }


def _text_fact(facts: Mapping[str, object], name: str) -> str | None:
    """Return one non-empty textual fact without guessing aliases."""
    value = facts.get(name)
    if value is None or not str(value).strip():
        return None
    return str(value)


def _authored_orientation(source: SourceObject) -> float | None:
    """Return an explicit local-frame orientation without inventing zero."""
    frame = source.authored_local_frame
    if frame is None or "orientation_degrees" not in frame:
        return None
    value = frame.get("orientation_degrees")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _geometry_frame(points: list[tuple[float, float]]) -> dict[str, float]:
    """Derive one two-axis furniture frame from projected geometry PCA."""
    if not points:
        return {"angle": 0.0, "primary_extent": 0.0, "secondary_extent": 0.0}
    center_x = sum(point[0] for point in points) / len(points)
    center_y = sum(point[1] for point in points) / len(points)
    xx = sum((point[0] - center_x) ** 2 for point in points) / len(points)
    yy = sum((point[1] - center_y) ** 2 for point in points) / len(points)
    xy = sum(
        (point[0] - center_x) * (point[1] - center_y) for point in points
    ) / len(points)
    angle = degrees(0.5 * atan2(2.0 * xy, xx - yy)) % 180.0
    primary_extent, secondary_extent = _frame_extents(points, angle)
    return {
        "angle": angle,
        "primary_extent": primary_extent,
        "secondary_extent": secondary_extent,
    }


def _frame_extents(
    points: list[tuple[float, float]],
    angle: float,
) -> tuple[float, float]:
    """Measure projected spans along one local frame and its perpendicular axis."""
    theta = radians(angle)
    primary = (cos(theta), sin(theta))
    secondary = (-sin(theta), cos(theta))
    primary_values = [point[0] * primary[0] + point[1] * primary[1] for point in points]
    secondary_values = [
        point[0] * secondary[0] + point[1] * secondary[1] for point in points
    ]
    return (
        max(primary_values) - min(primary_values),
        max(secondary_values) - min(secondary_values),
    )


def _record_bucket(role: str) -> str:
    """Map explicit neutral roles to legacy consumer buckets only at the view edge."""
    if role in {"boundary", "wall"}:
        return "boundaries"
    if role in {"authored_region_hint", "region"}:
        return "regions"
    if role in {"authored_path_hint", "path"}:
        return "paths"
    if role == "column":
        return "columns"
    if role in {
        "furniture",
        "table",
        "chair",
        "sofa",
        "cabinet",
        "shelf",
        "desk",
        "stool",
        "bench",
    }:
        return "objects"
    # Slabs, spaces, surfaces, containers, and unknown source products remain
    # neutral facts; the legacy object bucket is furniture-specific analysis.
    return "ignored"


def _is_physical_mass_record(record: Mapping[str, object]) -> bool:
    """Return whether a Neutral record represents physical mass for occupancy."""
    role = str(record.get("role", "")).strip().lower()
    if not record.get("_source_geometry_refs"):
        return False
    # These records describe navigation or semantic references; their geometry
    # must remain available to their own consumers without becoming solid mass.
    return role not in {
        "path",
        "authored_path_hint",
        "region",
        "authored_region_hint",
        "entry",
        "opening",
        "surface",
        "grid_axis",
        "analysis_domain",
    }


def _records_for_bucket(records: list[dict], bucket: str) -> list[dict]:
    """Select records assigned to one compatibility bucket."""
    return [record for record in records if record.get("_analysis_bucket") == bucket]


def _affordance_records(
    scene: NeutralSceneV2,
    geometry_points: Mapping[str, tuple[tuple[float, float], ...]],
) -> dict[str, list[dict]]:
    """Project explicit authored affordance geometry and attach it to each owner."""
    records: dict[str, list[dict]] = {}
    for zone in scene.authored_affordances:
        points = [
            point
            for geometry_ref in zone.geometry_refs
            for point in geometry_points.get(geometry_ref, ())
        ]
        if not points:
            continue
        rect = _points_rect(_convex_hull(points))
        for owner_ref in zone.source_furniture_refs:
            records.setdefault(owner_ref, []).append(
                {
                    "id": zone.id,
                    "object_id": owner_ref,
                    "region": None,
                    "side": zone.purpose,
                    "purpose": zone.purpose,
                    "depth": round(max(rect.width, rect.height), 4),
                    "source": "authored_neutral_affordance_zone",
                    "rect": rect,
                    "vertical_extent": zone.vertical_extent,
                    "task_facts": dict(zone.task_facts),
                }
            )
    return records


def _opening_records(
    scene: NeutralSceneV2,
    geometry_points: Mapping[str, tuple[tuple[float, float], ...]],
) -> list[dict]:
    """Project explicit source openings without inventing host relationships."""
    records = []
    for opening in scene.openings:
        points = [
            point
            for geometry_ref in opening.geometry_refs
            for point in geometry_points.get(geometry_ref, ())
        ]
        if not points:
            continue
        rect = _points_rect(_convex_hull(points))
        records.append(
            {
                "id": opening.id,
                "role": "opening",
                "group": opening.host_refs[0] if opening.host_refs else "room",
                "region": "room",
                "rect": rect,
                "points": _convex_hull(points),
                "metadata": {
                    "role": "opening",
                    "opening-kind": opening.opening_kind,
                    "host-boundary": opening.host_refs[0] if opening.host_refs else None,
                    "geometry-view": "neutral_scene_plan_projection",
                },
                "adapter_refs": {},
            }
        )
    return records


def _axis_records(
    scene: NeutralSceneV2,
    axis_points: Mapping[str, tuple[tuple[float, float], ...]],
) -> list[dict]:
    """Build explicit column-axis records from authored Neutral Scene axes."""
    grid_by_axis = {
        axis_ref: grid.id
        for grid in scene.authored_grids
        for axis_ref in grid.axis_refs
    }
    records = []
    for axis in scene.authored_grid_axes:
        points = list(axis_points.get(axis.id, ()))
        if len(points) < 2:
            continue
        records.append(
            {
                "id": axis.id,
                "role": "column_axis",
                "group": grid_by_axis.get(axis.id, "default_grid"),
                "region": "room",
                "rect": _points_rect(points),
                "points": points,
                "metadata": {
                    "role": "column_axis",
                    "system-id": grid_by_axis.get(axis.id, "default_grid"),
                    "branch-id": axis.branch_identifier or "default_branch",
                    "axis-list": axis.list_identifier,
                    "geometry-view": "authored_neutral_grid_axis",
                },
                "adapter_refs": {},
            }
        )
    return records


def _analysis_settings(scene: NeutralSceneV2) -> dict[str, float]:
    """Extract explicit analysis demand parameters from walking body profiles."""
    for profile in scene.context.walking_body_profiles:
        if not isinstance(profile, Mapping):
            continue
        value = profile.get("required_path_width")
        try:
            width = float(value)
        except (TypeError, ValueError):
            continue
        if width > 0.0:
            return {"required_path_width": width}
    return {}


def _points_rect(points: list[tuple[float, float]]) -> Rect:
    """Return the axis-aligned bounds used by legacy planar consumers."""
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return Rect(
        cx=(left + right) / 2.0,
        cy=(top + bottom) / 2.0,
        width=right - left,
        height=bottom - top,
    )


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return a deterministic convex outline for projected source components."""
    ordered = sorted(set(points))
    if len(ordered) <= 2:
        return ordered

    def cross(origin, first, second) -> float:
        """Return the signed turn used by the monotone-chain hull."""
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (
            first[1] - origin[1]
        ) * (second[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


__all__ = ["AnalysisSceneInput", "LegacyAnalysisScene", "analysis_scene_view"]
