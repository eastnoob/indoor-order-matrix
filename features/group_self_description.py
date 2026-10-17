"""Standalone evidence descriptions for explicitly authored furniture groups."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import combinations
from math import atan2, cos, degrees, hypot, isfinite, sin
from typing import Any

from .affordance.models import Rect
from .analysis_substitute_discovery import resolve_function_substitute
from .geometry_substitutes import mass_patch_from_mesh
from .geometry_views import plan_projection
from .neutral_scene_views import AnalysisSceneInput, analysis_scene_view, furniture_analysis_participation
from .scene_contract import NeutralSceneV2


def describe_group_relations(scene: AnalysisSceneInput) -> dict[str, object]:
    """Return standalone authored-group geometry and deferred relation evidence."""
    if isinstance(scene, NeutralSceneV2):
        objects, groups, frame, provenance, tolerances, uncertainties, view = _neutral_inputs(scene)
    elif isinstance(scene, dict):
        view = analysis_scene_view(scene)
        objects, groups, frame, provenance, tolerances, uncertainties = _legacy_inputs(view)
    else:
        raise TypeError("scene must be a legacy analysis mapping or NeutralSceneV2")
    object_by_id = {str(item["id"]): item for item in objects}
    groups = sorted(groups, key=lambda item: str(item["id"]))
    eligible_ids = {ref for group in groups for ref in group["member_refs"]}
    context_ids = sorted(str(item["id"]) for item in objects if str(item["id"]) not in eligible_ids)
    geometries = [_group_geometry(group, object_by_id, tolerances[0]) for group in groups]
    relations = _group_relations(groups, object_by_id, geometries, tolerances, view)
    result = {
        "schema": "group-self-description-evidence/v1",
        "status": "computed" if groups else "not_evaluated",
        "reason": None if groups else "no_eligible_authored_groups",
        "analysis_frame": frame,
        "eligibility": [
            {
                "eligible_group_id": group["id"],
                "member_object_ids": sorted(group["member_refs"]),
                "membership_provenance": group.get("provenance", {}),
                "excluded_context_object_ids": context_ids,
                "completeness_status": "computed",
            }
            for group in groups
        ],
        "group_geometry": geometries,
        "group_relations": relations,
        "space_observations": _space_observations(scene, view, context_ids),
        "local_neighborhood": _local_neighborhood(relations),
        "candidate_view_status": "deferred",
        "candidate_views": None,
        "capabilities": {
            "planar_geometry": {
                "status": "computed" if objects else "not_available",
                "source": "explicit_analysis_plane",
                "reason": None if objects else "no_planar_objects",
            },
            "3d_clearance": {
                "status": "not_available",
                "source": "planar_first_slice",
                "reason": "three_dimensional_query_deferred",
            },
            "z_compatibility": {
                "status": "not_available",
                "source": "planar_first_slice",
                "reason": "three_dimensional_query_deferred",
            },
        },
        "uncertainties": uncertainties,
        "provenance": provenance,
        "_tolerances": {"geometry": tolerances[0], "topology": tolerances[1]},
    }
    return _json_ready(result)


def _legacy_inputs(scene: Mapping[str, object]):
    """Collect legacy records using only explicit furniture-group markers."""
    settings = scene.get("settings", {})
    settings = settings if isinstance(settings, Mapping) else {}
    objects = [dict(item) for item in scene.get("objects", ()) if isinstance(item, Mapping)]
    groups = {}
    for item in objects:
        marker = item.get("furniture_group")
        metadata = item.get("metadata", {})
        if not marker and isinstance(metadata, Mapping):
            marker = metadata.get("furniture-group")
        if isinstance(marker, str) and marker:
            groups.setdefault(marker, {"id": marker, "member_refs": [], "provenance": {}})
            groups[marker]["member_refs"].append(str(item["id"]))
    plane_name = str(settings.get("analysis_plane", "xy"))
    frame = {
        "name": plane_name,
        "plane": plane_name,
        "basis": [[1.0, 0.0], [0.0, 1.0]],
        "origin": [0.0, 0.0, 0.0],
        "unit": settings.get("analysis_length_unit", settings.get("unit", "unknown")),
    }
    return (
        objects,
        list(groups.values()),
        frame,
        {
            "source_schema": str(scene.get("source", "legacy")),
            "adapter_version": str(scene.get("adapter_version", "legacy")),
            "input_mode": str(scene.get("input_mode", "legacy")),
            "method": "authored_group_planar_evidence",
            "version": "v1",
        },
        (
            _number(settings.get("geometry_tolerance", 1e-9), 1e-9),
            _number(settings.get("topology_tolerance", 1e-9), 1e-9),
        ),
        [dict(item) for item in scene.get("uncertainties", ()) if isinstance(item, Mapping)],
    )


def _neutral_inputs(scene: NeutralSceneV2):
    """Project Neutral Scene geometry while preserving unresolved authored members."""
    plane = scene.context.analysis_plane
    meshes = {mesh.id: mesh for mesh in scene.geometries}
    sources_by_id = {}
    for source in scene.source_objects:
        sources_by_id.setdefault(source.id, []).append(source)
    objects = []
    for source in scene.source_objects:
        participation = furniture_analysis_participation(source)
        components = []
        for geometry_ref in source.geometry_refs:
            mesh = meshes.get(geometry_ref)
            if mesh is None:
                continue
            projection = plan_projection(mass_patch_from_mesh(mesh), plane)
            # Keep the source projection in the authored plane; the generic
            # consumer view shifts coordinates for rendering compatibility.
            components.extend(
                {
                    "exterior": tuple(tuple(float(value) for value in point) for point in component.get("exterior", ())),
                    "holes": tuple(
                        tuple(tuple(float(value) for value in point) for point in hole)
                        for hole in component.get("holes", ())
                    ),
                }
                for component in projection.components
            )
        trend_resolution = (
            {"status": "not_available", "reason": "furniture_analysis_" + participation}
            if participation in ("excluded", "unknown")
            else resolve_function_substitute(scene, source.id, "trend")
        )
        trend_components = []
        if trend_resolution["status"] == "accepted":
            # Trend descriptors may consume only the independently typed
            # Analysis substitute; the source object's Body projection stays
            # available for compatibility evidence and audit.
            substitute_id = trend_resolution["substitute_source_object_id"]
            targets = sources_by_id.get(str(substitute_id), ())
            if len(targets) == 1:
                for geometry_ref in targets[0].geometry_refs:
                    mesh = meshes.get(geometry_ref)
                    if mesh is None:
                        continue
                    projection = plan_projection(mass_patch_from_mesh(mesh), plane)
                    trend_components.extend(
                        {
                            "exterior": tuple(tuple(float(value) for value in point) for point in component.get("exterior", ())),
                            "holes": tuple(
                                tuple(tuple(float(value) for value in point) for point in hole)
                                for hole in component.get("holes", ())
                            ),
                        }
                        for component in projection.components
                    )
        objects.append(
            {
                "id": source.id,
                "geometry_components": components,
                "geometry_refs": list(source.geometry_refs),
                "uncertainties": [record.to_dict() for record in source.uncertainties],
                "type_ref": source.type_ref,
                "factual_properties": dict(source.factual_properties),
                "source_role": source.source_role,
                "_furniture_analysis_participation": participation,
                "provenance": dict(source.provenance),
                "_trend_geometry_components": trend_components,
                "_trend_geometry_refs": (
                    list(sources_by_id[str(trend_resolution["substitute_source_object_id"])][0].geometry_refs)
                    if trend_resolution["status"] == "accepted"
                    and len(sources_by_id.get(str(trend_resolution["substitute_source_object_id"]), ())) == 1
                    else []
                ),
                "_trend_resolution": trend_resolution,
            }
        )
    groups = [
        {"id": group.id, "member_refs": list(group.member_refs), "provenance": dict(group.provenance)}
        for group in scene.authored_groups
        if group.group_role == "furniture_group"
    ]
    view = analysis_scene_view(scene)
    view["_group_analysis_unit"] = scene.context.analysis_length_unit
    return (
        objects,
        groups,
        {
            "name": plane.name,
            "plane": plane.name,
            "basis": [list(axis) for axis in plane.basis],
            "origin": list(plane.origin),
            "unit": scene.context.analysis_length_unit,
        },
        {
            "source_schema": scene.context.source_schema,
            "adapter_version": scene.context.adapter_version,
            "input_mode": scene.context.input_mode,
            "method": "authored_group_planar_evidence",
            "version": "v1",
        },
        (scene.context.geometry_tolerance, scene.context.topology_tolerance),
        [record.to_dict() for record in scene.uncertainties]
        + [uncertainty for item in objects for uncertainty in item["uncertainties"]],
        view,
    )


def _group_geometry(group, object_by_id, tolerance):
    """Compute additive member moments, status propagation, and frame descriptors."""
    valid = []
    excluded = []
    invalid = False
    for member_id in sorted(group["member_refs"]):
        item = object_by_id.get(member_id)
        if item is None:
            excluded.append({"member_id": member_id, "status": "invalid", "reason": "unresolved_member_ref", "source_refs": []})
            invalid = True
            continue
        if item.get("_furniture_analysis_participation") in ("excluded", "unknown"):
            excluded.append({"member_id": member_id, "status": "not_available",
                             "reason": "furniture_analysis_" + item["_furniture_analysis_participation"],
                             "source_refs": list(item["geometry_refs"])})
            continue
        geometry, reason = _member_geometry(item, tolerance)
        if geometry is None:
            # Invalid evidence stays invalid; missing evidence remains
            # unavailable so later selectors cannot treat either as zero area.
            status = "invalid" if reason != "missing_geometry" else "not_available"
            excluded.append({
                "member_id": member_id,
                "status": status,
                "reason": reason,
                "source_refs": list(item.get("geometry_refs", item.get("_source_geometry_refs", ()))),
            })
            invalid = invalid or status == "invalid"
        else:
            valid.append(geometry)
    support = sum(item["area"] for item in valid)
    if invalid:
        geometry_status = "invalid"
    elif valid and excluded:
        geometry_status = "partial"
    elif valid:
        geometry_status = "computed"
    else:
        geometry_status = "not_available"
    representative = _representative(valid, support) if valid and not invalid else None
    diagnostic = (
        {"status": "diagnostic_only", "support_area": support, "member_count": len(valid)}
        if valid and invalid
        else None
    )
    trend_valid, trend_excluded, trend_status = _trend_geometry(
        group, object_by_id, tolerance
    )
    resolutions = [
        object_by_id.get(member_id, {}).get("_trend_resolution")
        for member_id in group["member_refs"]
    ]
    # With no authored binding at all, expose the historical fields as a
    # compatibility fallback; any typed attempt must not mix Body evidence.
    has_resolution = any(isinstance(resolution, Mapping) for resolution in resolutions)
    legacy_compatibility_fallback = not has_resolution or all(
        isinstance(resolution, Mapping)
        and resolution.get("status") == "not_available"
        and resolution.get("reason") == "missing_typed_binding"
        for resolution in resolutions
    )
    has_typed_trend_contract = bool(resolutions) and not legacy_compatibility_fallback
    # Canonical A must use the same typed Analysis members as C and D. Legacy
    # dictionary inputs retain their existing A calculation for compatibility.
    direction = (
        _directions(trend_valid)
        if has_typed_trend_contract and trend_status == "computed"
        else {
            "group_frame": {"angle": None, "coherence": 0.0, "direction_status": "undefined"},
            "group_axis": {"angle": None, "coherence": 0.0, "direction_status": "undefined"},
            "directional_member_support": 0,
        }
        if has_typed_trend_contract
        else _directions(valid)
    )
    trend_representative = (
        _representative(trend_valid, sum(item["area"] for item in trend_valid))
        if trend_valid and trend_status == "computed"
        else None
    )
    trend_bindings = [
        object_by_id[member_id]["_trend_resolution"]
        for member_id in sorted(group["member_refs"])
        if isinstance(object_by_id.get(member_id, {}).get("_trend_resolution"), Mapping)
        and object_by_id[member_id]["_trend_resolution"].get("status") == "accepted"
    ]
    return {
        "target_layer": "furniture_group",
        "target_id": group["id"],
        "geometry_status": geometry_status,
        "support_area": representative["support_area"] if representative else None,
        "center": representative["center"] if representative else None,
        "within_member_covariance": representative["within_member_covariance"] if representative else None,
        "between_member_covariance": representative["between_member_covariance"] if representative else None,
        "covariance": representative["covariance"] if representative else None,
        "excluded_member_reasons": excluded,
        "geometry_completeness": {"usable_members": len(valid), "declared_members": len(group["member_refs"])},
        "member_geometry": valid,
        "diagnostic_geometry": diagnostic,
        **direction,
        "trend_descriptors": _trend_descriptors(
            trend_valid,
            trend_representative,
            trend_status,
            tolerance,
            trend_excluded,
            trend_bindings,
        ),
        "strength": None,
        "strength_status": "deferred",
        "overlap_area": None,
        "union_area_status": "deferred",
        "aggregation_status": "deferred",
    }


def _trend_geometry(group, object_by_id, tolerance):
    """Collect only typed Analysis geometry and propagate its contract state."""
    valid = []
    excluded = []
    statuses = []
    for member_id in sorted(group["member_refs"]):
        item = object_by_id.get(member_id)
        if item is None:
            statuses.append("not_available")
            excluded.append({
                "member_id": member_id,
                "status": "not_available",
                "resolver_status": "not_available",
                "reason": "unresolved_member_ref",
                "provenance": None,
            })
            continue
        resolution = item.get("_trend_resolution")
        if not isinstance(resolution, Mapping) or resolution.get("status") != "accepted":
            # Missing/unresolved evidence is unavailable; a rejected contract
            # is invalid so its cause remains visible to the caller.
            resolver_status = resolution.get("status") if isinstance(resolution, Mapping) else "not_available"
            status = "not_available" if resolver_status == "not_available" else "invalid"
            statuses.append(status)
            excluded.append({
                "member_id": member_id,
                "status": status,
                "resolver_status": resolver_status,
                "reason": (resolution or {}).get("reason", "missing_typed_binding"),
                "source_refs": list(item.get("geometry_refs", ())),
                "provenance": (resolution or {}).get("provenance"),
                "candidate_provenance": (resolution or {}).get("candidate_provenance", []),
            })
            continue
        trend_item = dict(item)
        trend_item["geometry_components"] = item.get("_trend_geometry_components", ())
        geometry, reason = _member_geometry(trend_item, tolerance)
        if geometry is None:
            status = "not_available" if reason == "missing_geometry" else "invalid"
            statuses.append(status)
            excluded.append({
                "member_id": member_id,
                "status": status,
                "resolver_status": "accepted",
                "reason": reason,
                "source_refs": list(item.get("_trend_geometry_refs", ())),
                "provenance": resolution.get("substitute_provenance"),
            })
            continue
        valid.append(geometry)
        statuses.append("computed")

    if not valid:
        status = "not_available" if all(item == "not_available" for item in statuses) else "invalid"
    elif any(item == "invalid" for item in statuses):
        status = "invalid"
    elif any(item == "not_available" for item in statuses):
        status = "partial"
    else:
        status = "computed"
    return valid, excluded, status


def _trend_descriptors(members, representative, status, tolerance, excluded, bindings):
    """Build formal C/A/D descriptors while isolating partial diagnostics."""
    empty = {
        "angle": None,
        "strength": None,
        "direction_status": "undefined" if status == "computed" else status,
    }
    if status != "computed" or representative is None:
        member_directions = _directions(members) if members else None
        diagnostic = {
            "status": "diagnostic_only",
            "usable_member_count": len(members),
            "excluded_members": excluded,
            "member_frame": member_directions["group_frame"] if member_directions else None,
            "member_axis": member_directions["group_axis"] if member_directions else None,
        }
        return {
            "status": status,
            "overall_group_axis": {**empty, "basis": "area_weighted_total_covariance_pca"},
            "member_frame": {**empty, "basis": "member_orientation_consensus"},
            "member_axis": {**empty, "basis": "member_orientation_consensus"},
            "layout_axis": {**empty, "basis": "between_member_centroid_pca"},
            "member_bindings": bindings,
            "diagnostic_evidence": diagnostic,
        }

    overall = _covariance_axis(
        representative["covariance"],
        "area_weighted_total_covariance_pca",
        tolerance,
    )
    layout = _covariance_axis(
        representative["between_member_covariance"],
        "between_member_centroid_pca",
        tolerance,
    )
    member_directions = _directions(members)
    member_frame = dict(member_directions["group_frame"])
    member_axis = dict(member_directions["group_axis"])
    member_frame["basis"] = "member_orientation_consensus"
    member_axis["basis"] = "member_orientation_consensus"
    member_frame["strength"] = member_frame["coherence"]
    member_axis["strength"] = member_axis["coherence"]
    return {
        "status": status,
        "overall_group_axis": {**overall, "center": representative["center"]},
        "member_frame": member_frame,
        "member_axis": member_axis,
        "layout_axis": {**layout, "center": representative["center"]},
        "member_bindings": bindings,
        "diagnostic_evidence": None,
    }


def _covariance_axis(covariance, basis, tolerance):
    """Return a deterministic major-axis angle and eigenvalue anisotropy."""
    try:
        xx, xy, yy = float(covariance[0][0]), float(covariance[0][1]), float(covariance[1][1])
    except (TypeError, ValueError, IndexError):
        return {"angle": None, "strength": None, "direction_status": "undefined", "basis": basis}
    trace = xx + yy
    delta = hypot(xx - yy, 2.0 * xy)
    # The closed-form 2x2 eigensystem keeps C and D deterministic without a
    # numerical dependency or an arbitrary direction for degenerate spread.
    if not isfinite(trace) or not isfinite(delta) or trace <= tolerance:
        return {"angle": None, "strength": None, "direction_status": "undefined", "basis": basis}
    strength = delta / trace
    if delta <= tolerance:
        return {"angle": None, "strength": None, "direction_status": "undefined", "basis": basis}
    angle = degrees(atan2(2.0 * xy, xx - yy) / 2.0) % 180.0
    if abs(angle - 180.0) < 1e-12:
        angle = 0.0
    return {"angle": angle, "strength": strength, "direction_status": "computed", "basis": basis}


def _group_relations(groups, object_by_id, geometries, tolerances, view):
    """Emit auditable member-pair observations without selecting a group edge."""
    geometry_by_group = {item["target_id"]: item for item in geometries}
    relations = []
    for first, second in combinations(groups, 2):
        group_a, group_b = first["id"], second["id"]
        observations = []
        for member_a in sorted(first["member_refs"]):
            for member_b in sorted(second["member_refs"]):
                left = _member_record(geometry_by_group[group_a], member_a)
                right = _member_record(geometry_by_group[group_b], member_b)
                observations.append(_member_pair_observation(left, right, object_by_id, tolerances[0]))
        semantic = _semantic_channel(first, second, object_by_id)
        pair_id = f"{group_a}|{group_b}"
        computed = [item for item in observations if item["status"] == "computed"]
        shared_members = sorted(set(first["member_refs"]) & set(second["member_refs"]))
        if shared_members and len(shared_members) == len(first["member_refs"]) == len(second["member_refs"]):
            status = "diagnostic_only"
        elif computed and any(item["status"] != "computed" for item in observations):
            status = "partial"
        elif computed:
            status = "computed"
        elif any(item["status"] == "invalid" for item in observations):
            status = "invalid"
        else:
            status = "not_available"
        relations.append({
            "target_layer": "furniture_group_pair",
            "target_id": pair_id,
            "group_a": group_a,
            "group_b": group_b,
            "member_pair_observations": observations,
            "member_pair_witnesses": [item["witness"] for item in computed],
            "raw_boundary_gap": None,
            "normalized_boundary_gap": None,
            "contact": None,
            "overlap": None,
            "overlap_area": None,
            "aggregation_status": "deferred",
            "formal_membership_edge": None,
            "positive_support": None,
            "negative_evidence": semantic["negative_evidence"],
            "semantic_conflicts": semantic["conflicts"],
            "semantic_channel_status": semantic["status"],
            "space_channel_status": "not_available",
            "barrier_observation": {"status": "not_available", "source": "planar_group_slice", "reason": "barrier_aggregation_deferred"},
            "3d_clearance": {"status": "not_available", "source": "planar_group_slice"},
            "3d_overlap": {"status": "not_available", "source": "planar_group_slice"},
            "z_compatibility": {"status": "not_available", "source": "planar_group_slice"},
            "shared_member_dependency": {"status": "diagnostic_only" if shared_members else "not_applicable", "member_ids": shared_members},
            "status": status,
            "reason": "shared_member_dependency" if status == "diagnostic_only" else (None if computed else "no_usable_member_pair"),
            "analysis_frame": view.get("_analysis_view", {}).get("analysis_plane", "xy"),
            "unit": view.get("_group_analysis_unit", view.get("settings", {}).get("analysis_length_unit", "unknown") if isinstance(view.get("settings"), Mapping) else "unknown"),
            "tolerance": {"geometry": tolerances[0], "topology": tolerances[1]},
            "source_provenance": {"method": "member_pair_boundary_observation", "tolerance": tolerances[0]},
        })
    return relations


def _member_record(group_geometry, member_id):
    """Find one valid member geometry while keeping excluded states explicit."""
    for item in group_geometry.get("member_geometry", ()):
        if item["member_id"] == member_id:
            return item
    for item in group_geometry.get("excluded_member_reasons", ()):
        if item["member_id"] == member_id:
            return {"member_id": member_id, "status": item["status"], "reason": item["reason"]}
    return {"member_id": member_id, "status": "invalid", "reason": "unresolved_member_ref"}


def _member_pair_observation(left, right, object_by_id, tolerance):
    """Measure one member pair's raw gap, contact, overlap, and witness."""
    witness = {"member_a": left["member_id"], "member_b": right["member_id"], "source_refs": []}
    if left.get("status") and left.get("status") != "computed":
        return {"member_a": left["member_id"], "member_b": right["member_id"], "status": left["status"], "reason": left.get("reason"), "raw_boundary_gap": None, "normalized_boundary_gap": None, "contact": None, "overlap": None, "overlap_area": None, "witness": witness}
    if right.get("status") and right.get("status") != "computed":
        return {"member_a": left["member_id"], "member_b": right["member_id"], "status": right["status"], "reason": right.get("reason"), "raw_boundary_gap": None, "normalized_boundary_gap": None, "contact": None, "overlap": None, "overlap_area": None, "witness": witness}
    from shapely.geometry import Polygon
    polygons_a = [Polygon(points, holes) for points, holes in zip(left.get("polygons", ()), left.get("polygon_holes", [()] * len(left.get("polygons", ()))))]
    polygons_b = [Polygon(points, holes) for points, holes in zip(right.get("polygons", ()), right.get("polygon_holes", [()] * len(right.get("polygons", ()))))]
    if not polygons_a or not polygons_b:
        return {"member_a": left["member_id"], "member_b": right["member_id"], "status": "not_available", "reason": "missing_geometry", "raw_boundary_gap": None, "normalized_boundary_gap": None, "contact": None, "overlap": None, "overlap_area": None, "witness": witness}
    raw_gap = min(first.boundary.distance(second.boundary) for first in polygons_a for second in polygons_b)
    overlap_area = sum(first.intersection(second).area for first in polygons_a for second in polygons_b)
    overlap = overlap_area > tolerance
    if overlap:
        raw_gap = 0.0
    contact = raw_gap <= tolerance and not overlap
    area_scale = (left["area"] + right["area"]) ** 0.5
    return {
        "member_a": left["member_id"],
        "member_b": right["member_id"],
        "status": "computed",
        "reason": None,
        "raw_boundary_gap": raw_gap,
        "normalized_boundary_gap": raw_gap / area_scale if area_scale else None,
        "normalization": {"method": "sqrt_member_support_area_sum", "denominator": area_scale},
        "contact": contact,
        "overlap": overlap,
        "overlap_area": overlap_area if overlap else 0.0,
        "witness": {**witness, "boundary_method": "minimum_exterior_segment_distance", "source_refs": sorted(set(object_by_id.get(left["member_id"], {}).get("geometry_refs", ()) + object_by_id.get(right["member_id"], {}).get("geometry_refs", ())))},
    }


def _semantic_channel(first, second, object_by_id):
    """Preserve factual type disagreement and explicit mutual exclusion only."""
    types = {"a": [], "b": []}
    exclusions = []
    for group, label in ((first, "a"), (second, "b")):
        for member_id in group["member_refs"]:
            item = object_by_id.get(member_id, {})
            facts = item.get("factual_properties", {})
            if not isinstance(facts, Mapping):
                facts = {}
            type_value = item.get("type_ref") or facts.get("type") or facts.get("Type") or facts.get("OM_TypeKey")
            if type_value:
                value = str(type_value)
                if value not in types[label]:
                    types[label].append(value)
            declared = facts.get("mutual_exclusion")
            if isinstance(declared, str):
                declared = [declared]
            if isinstance(declared, (list, tuple, set)):
                exclusions.extend({"kind": "mutual_exclusion", "source": member_id, "value": str(value)} for value in declared)
    negative = {}
    if types["a"] and types["b"] and set(types["a"]).isdisjoint(types["b"]):
        negative["type_mismatch"] = {"status": "soft_negative", "types": types}
    return {"status": "computed" if any(types.values()) or exclusions else "not_available", "negative_evidence": negative, "conflicts": exclusions}


def _local_neighborhood(relations):
    """Expose symmetric relation views without ranking or selecting neighbors."""
    records = []
    for relation in relations:
        for group_id, neighbor_id in ((relation["group_a"], relation["group_b"]), (relation["group_b"], relation["group_a"])):
            records.append({
                "group_id": group_id,
                "neighbor_group_id": neighbor_id,
                "relation_id": relation["target_id"],
                "positive_support_vector": None,
                "negative_evidence_vector": relation["negative_evidence"],
                "semantic_conflicts": relation["semantic_conflicts"],
                "space_conflicts": [],
                "missingness": [item["reason"] for item in relation["member_pair_observations"] if item.get("reason")],
                "status": relation["status"],
                "candidate_competition_refs": [],
                "formal_membership_edge": None,
            })
    return records


def _member_geometry(item, tolerance):
    """Parse simple polygon components or an explicitly approved rectangle fallback."""
    if item.get("_furniture_analysis_participation") in ("excluded", "unknown"):
        return None, "furniture_analysis_" + item["_furniture_analysis_participation"]
    components = item.get("geometry_components", ())
    if components:
        parts = []
        for component in components:
            if not isinstance(component, Mapping):
                return None, "invalid_polygon"
            part = _polygon_moments(
                component.get("exterior", ()),
                tolerance,
                component.get("holes", ()),
            )
            if part is None:
                return None, _polygon_reason(component.get("exterior", ()))
            parts.append(part)
        return _combine_parts(parts, item), None
    if item.get("geometry_basis") == "rect_fallback" and isinstance(item.get("rect"), Rect):
        rect = item["rect"]
        points = ((rect.left, rect.top), (rect.right, rect.top), (rect.right, rect.bottom), (rect.left, rect.bottom))
        return _combine_parts([_polygon_moments(points, tolerance)], item, basis="rect_fallback"), None
    return None, "missing_geometry"


def _polygon_reason(points):
    """Classify malformed polygon evidence without changing invalidity into missingness."""
    try:
        values = [float(value) for point in points for value in point]
    except (TypeError, ValueError, IndexError):
        return "invalid_polygon"
    return "non_finite_coordinates" if any(not isfinite(value) for value in values) else "invalid_polygon"


def _polygon_moments(points, tolerance, holes=()):
    """Compute hole-aware area, centroid, and uniform-polygon covariance."""
    try:
        points = tuple((float(point[0]), float(point[1])) for point in points)
    except (TypeError, ValueError, IndexError):
        return None
    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]
    if len(points) < 3 or any(not isfinite(value) for point in points for value in point):
        return None
    normalized_holes = []
    for hole in holes or ():
        try:
            ring = tuple((float(point[0]), float(point[1])) for point in hole)
        except (TypeError, ValueError, IndexError):
            return None
        if len(ring) >= 2 and ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(ring) < 3 or any(not isfinite(value) for point in ring for value in point):
            return None
        ring_area = sum(
            ring[index][0] * ring[(index + 1) % len(ring)][1]
            - ring[(index + 1) % len(ring)][0] * ring[index][1]
            for index in range(len(ring))
        ) / 2.0
        # Coplanar tessellation seams can polygonize as zero-area rings. Drop
        # only degenerate rings before Shapely sees them; nonzero bad rings stay invalid.
        try:
            from shapely.geometry import Polygon
            ring_polygon = Polygon(ring)
        except (TypeError, ValueError):
            return None
        if abs(ring_area) <= tolerance:
            distinct = []
            for point in ring:
                if point not in distinct:
                    distinct.append(point)
            if len(distinct) <= 2:
                continue
            anchor, direction = distinct[0], None
            for point in distinct[1:]:
                if point != anchor:
                    direction = (point[0] - anchor[0], point[1] - anchor[1])
                    break
            collinear = direction is not None and all(
                direction[0] * (point[1] - anchor[1])
                - direction[1] * (point[0] - anchor[0]) == 0.0
                for point in distinct[1:]
            )
            if not collinear and not ring_polygon.is_valid:
                return None
            continue
        if not ring_polygon.is_valid:
            return None
        normalized_holes.append(ring)
    # Reject self-intersecting rings before deriving moments; shoelace area can
    # be non-zero for an invalid polygon and would otherwise create false facts.
    try:
        from shapely.geometry import Polygon

        polygon = Polygon(points, normalized_holes)
    except (TypeError, ValueError):
        return None
    if not polygon.is_valid or not polygon.exterior.is_simple:
        return None
    crosses = [
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    ]
    signed_area = sum(crosses) / 2.0
    # Signed shoelace integrals preserve clockwise and counter-clockwise rings
    # while the final area remains positive and orientation invariant.
    if abs(signed_area) <= tolerance:
        return None
    cx = sum((points[i][0] + points[(i + 1) % len(points)][0]) * crosses[i] for i in range(len(points))) / (6.0 * signed_area)
    cy = sum((points[i][1] + points[(i + 1) % len(points)][1]) * crosses[i] for i in range(len(points))) / (6.0 * signed_area)
    xx = sum((points[i][0] ** 2 + points[i][0] * points[(i + 1) % len(points)][0] + points[(i + 1) % len(points)][0] ** 2) * crosses[i] for i in range(len(points))) / (12.0 * signed_area)
    yy = sum((points[i][1] ** 2 + points[i][1] * points[(i + 1) % len(points)][1] + points[(i + 1) % len(points)][1] ** 2) * crosses[i] for i in range(len(points))) / (12.0 * signed_area)
    xy = sum(
        (
            points[i][0] * points[(i + 1) % len(points)][1]
            + 2 * points[i][0] * points[i][1]
            + 2 * points[(i + 1) % len(points)][0] * points[(i + 1) % len(points)][1]
            + points[(i + 1) % len(points)][0] * points[i][1]
        ) * crosses[i]
        for i in range(len(points))
    ) / (24.0 * signed_area)
    outer_area = abs(signed_area)
    raw = ((outer_area * xx, outer_area * xy), (outer_area * xy, outer_area * yy))
    first = (outer_area * cx, outer_area * cy)
    area = outer_area
    # Subtract void integrals before centering; ring winding must not add mass.
    for hole in normalized_holes:
        hole_moments = _polygon_moments(hole, tolerance)
        if hole_moments is None:
            return None
        if hole_moments["area"] >= area - tolerance:
            return None
        hole_area = hole_moments["area"]
        hole_center = hole_moments["center"]
        hole_covariance = hole_moments["covariance"]
        hole_raw = (
            (hole_covariance[0][0] + hole_center[0] ** 2,
             hole_covariance[0][1] + hole_center[0] * hole_center[1]),
            (hole_covariance[1][0] + hole_center[0] * hole_center[1],
             hole_covariance[1][1] + hole_center[1] ** 2),
        )
        area -= hole_area
        first = (first[0] - hole_area * hole_center[0], first[1] - hole_area * hole_center[1])
        raw = ((raw[0][0] - hole_area * hole_raw[0][0], raw[0][1] - hole_area * hole_raw[0][1]),
               (raw[1][0] - hole_area * hole_raw[1][0], raw[1][1] - hole_area * hole_raw[1][1]))
    if area <= tolerance:
        return None
    center = (first[0] / area, first[1] / area)
    return {
        "area": area,
        "center": center,
        "covariance": ((raw[0][0] / area - center[0] ** 2, raw[0][1] / area - center[0] * center[1]),
                       (raw[1][0] / area - center[0] * center[1], raw[1][1] / area - center[1] ** 2)),
        "points": points,
        "holes": tuple(tuple(hole) for hole in normalized_holes),
    }


def _combine_parts(parts, item, *, basis=None):
    """Aggregate simple components additively without polygon union."""
    if any(part is None for part in parts):
        return None
    area = sum(part["area"] for part in parts)
    center = (
        sum(part["area"] * part["center"][0] for part in parts) / area,
        sum(part["area"] * part["center"][1] for part in parts) / area,
    )
    covariance = _weighted_covariance(parts, area, center)
    return {
        "member_id": str(item["id"]),
        "area": area,
        "center": center,
        "covariance": covariance,
        "points": tuple(point for part in parts for point in part["points"]),
        "polygons": tuple(part["points"] for part in parts),
        "polygon_holes": tuple(part.get("holes", ()) for part in parts),
        "geometry_basis": basis or item.get("geometry_basis", "polygon"),
        "directional_weight": None,
    }


def _representative(members, support):
    """Apply support-area weighting to within and between member covariance."""
    center = (
        sum(item["area"] * item["center"][0] for item in members) / support,
        sum(item["area"] * item["center"][1] for item in members) / support,
    )
    within = _within_covariance(members, support)
    # Within-member moments exclude centroid separation; that is recorded only
    # by the separate between-member covariance term below.
    between = [[0.0, 0.0], [0.0, 0.0]]
    for item in members:
        dx = item["center"][0] - center[0]
        dy = item["center"][1] - center[1]
        weight = item["area"] / support
        between[0][0] += weight * dx * dx
        between[0][1] += weight * dx * dy
        between[1][0] += weight * dx * dy
        between[1][1] += weight * dy * dy
    return {
        "support_area": support,
        "center": center,
        "within_member_covariance": within,
        "between_member_covariance": between,
        "covariance": [[within[i][j] + between[i][j] for j in range(2)] for i in range(2)],
    }


def _weighted_covariance(items, total, center):
    """Aggregate area-weighted central covariance terms."""
    if center is None:
        center = (
            sum(item["area"] * item["center"][0] for item in items) / total,
            sum(item["area"] * item["center"][1] for item in items) / total,
        )
    result = [[0.0, 0.0], [0.0, 0.0]]
    for item in items:
        dx = item["center"][0] - center[0]
        dy = item["center"][1] - center[1]
        weight = item["area"] / total
        result[0][0] += weight * (item["covariance"][0][0] + dx * dx)
        result[0][1] += weight * (item["covariance"][0][1] + dx * dy)
        result[1][0] += weight * (item["covariance"][1][0] + dx * dy)
        result[1][1] += weight * (item["covariance"][1][1] + dy * dy)
    return result


def _within_covariance(items, total):
    """Aggregate central member covariances without adding between-member spread."""
    return [
        [sum(item["area"] * item["covariance"][i][j] for item in items) / total for j in range(2)]
        for i in range(2)
    ]


def _directions(members):
    """Compute independent four-angle frame and two-angle axis resultants."""
    records = []
    for item in members:
        xx, xy, yy = item["covariance"][0][0], item["covariance"][0][1], item["covariance"][1][1]
        trace = xx + yy
        delta = hypot(xx - yy, 2.0 * xy)
        if trace <= 0.0:
            continue
        anisotropy = (2.0 * delta / trace) / 2.0
        if anisotropy <= 0.0:
            continue
        angle = atan2(2.0 * xy, xx - yy) / 2.0
        weight = item["area"] * anisotropy
        item["directional_weight"] = weight
        records.append((weight, angle))
    if not records:
        undefined = {"angle": None, "coherence": 0.0, "direction_status": "undefined"}
        return {"group_frame": dict(undefined), "group_axis": dict(undefined), "directional_member_support": 0}
    total = sum(weight for weight, _ in records)
    frame_x = sum(weight * cos(4.0 * angle) for weight, angle in records)
    frame_y = sum(weight * sin(4.0 * angle) for weight, angle in records)
    axis_x = sum(weight * cos(2.0 * angle) for weight, angle in records)
    axis_y = sum(weight * sin(2.0 * angle) for weight, angle in records)
    frame_angle = degrees(atan2(frame_y, frame_x) / 4.0) % 90.0
    axis_angle = degrees(atan2(axis_y, axis_x) / 2.0) % 180.0
    if abs(frame_angle - 90.0) < 1e-12:
        frame_angle = 0.0
    if abs(axis_angle - 180.0) < 1e-12:
        axis_angle = 0.0
    return {
        "group_frame": {"angle": frame_angle, "coherence": hypot(frame_x, frame_y) / total, "direction_status": "computed"},
        "group_axis": {"angle": axis_angle, "coherence": hypot(axis_x, axis_y) / total, "direction_status": "computed"},
        "directional_member_support": len(records),
    }


def _space_observations(scene, view, context_ids):
    """Expose existing domain and context references without deriving topology."""
    available = bool(scene.analysis_domain) if isinstance(scene, NeutralSceneV2) else bool(view.get("analysis_domain"))
    domain_status = "computed" if available else "not_available"
    # The domain is an input fact, but these measurements are not computed by
    # this slice. Keep their channel status unavailable until a later space
    # field implementation supplies actual values.
    channel_status = "not_available"
    return {
        "domain_status": domain_status,
        "analysis_domain": scene.analysis_domain.to_dict() if isinstance(scene, NeutralSceneV2) and scene.analysis_domain else view.get("analysis_domain"),
        "free_space": {"status": channel_status, "value": None, "reason": "space_measurement_deferred"},
        "connectivity": {"status": channel_status, "value": None, "reason": "space_measurement_deferred"},
        "bottleneck_profile": {"status": channel_status, "value": None, "reason": "space_measurement_deferred"},
        "context_references": sorted(context_ids),
        "channel_evidence": view.get("channel_evidence", {}),
        "boundary_evidence": view.get("boundaries", []) + view.get("boundary_facts", []),
    }


def _number(value, default):
    """Return a finite non-negative tolerance or a safe default."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if isfinite(parsed) and parsed >= 0 else default


def _json_ready(value):
    """Convert tuple-shaped evidence into JSON-compatible containers."""
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items() if not str(key).startswith("_")}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    if isinstance(value, Rect):
        return {"cx": value.cx, "cy": value.cy, "width": value.width, "height": value.height}
    return value


__all__ = ["describe_group_relations"]
