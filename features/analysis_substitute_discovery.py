"""Read-only discovery of already-authored analysis geometry substitutes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .substitute_contract import load_substitute_registry, resolve_substitute_contract
from .scene_contract import NeutralSceneV2
from .geometry_substitutes import mass_patch_from_mesh
from .geometry_views import plan_projection


def _candidate_source_id(record: Mapping[str, Any]) -> str | None:
    """Read the stable source binding from a candidate record."""
    value = record.get("source_global_id") or record.get("source_id")
    return str(value) if value is not None and str(value) else None


def _candidate_id(record: Mapping[str, Any]) -> str | None:
    """Read the candidate identity without fabricating one."""
    value = record.get("substitute_id") or record.get("id")
    return str(value) if value is not None and str(value) else None


def _is_substitute(record: Mapping[str, Any]) -> bool:
    """Identify explicit substitute evidence without relying on object names."""
    role = str(record.get("analysis_role") or record.get("role") or "").lower()
    kind = str(record.get("substitute_kind") or "").lower()
    return (
        role in {"analysis_substitute", "analysis_geometry_substitute"}
        or kind == "masspatch"
    )


def discover_analysis_substitutes(
    source_records: Sequence[Mapping[str, Any]],
) -> dict[str, object]:
    """Discover explicit substitutes without generating or mutating any record."""
    accepted: list[dict[str, object]] = []
    by_source: dict[str, list[dict[str, object]]] = {}
    source_ids: list[str] = []

    # First collect authoritative source IDs; candidate records are not sources.
    for record in source_records:
        if not isinstance(record, Mapping) or _is_substitute(record):
            continue
        source_id = str(record.get("source_global_id") or record.get("id") or "")
        if source_id:
            source_ids.append(source_id)

    for record in source_records:
        if not isinstance(record, Mapping) or not _is_substitute(record):
            continue
        source_id = _candidate_source_id(record)
        substitute_id = _candidate_id(record)
        if source_id is None or substitute_id is None:
            continue
        binding = {
            "source_global_id": source_id,
            "substitute_id": substitute_id,
            "substitute_kind": str(record.get("substitute_kind") or "MassPatch"),
            "analysis_role": str(
                record.get("analysis_role") or "analysis_geometry_substitute"
            ),
            "visibility_policy": str(
                record.get("visibility_policy") or "analysis_only"
            ),
            "provenance": record.get("provenance")
            or {"method": "explicit_record_binding"},
            "confidence": str(record.get("confidence") or "high"),
        }
        by_source.setdefault(source_id, []).append(binding)

    ambiguous_candidates = sorted(
        source_id
        for source_id, candidates in by_source.items()
        if len(candidates) != 1
    )
    for source_id, candidates in sorted(by_source.items()):
        if len(candidates) == 1:
            accepted.append(candidates[0])

    missing_sources = sorted(set(source_ids) - set(by_source))
    if ambiguous_candidates:
        status = "ambiguous"
    elif missing_sources:
        status = "not_found"
    else:
        status = "passed"
    return {
        "status": status,
        "substitutes": accepted,
        "source_bindings": [
            {
                "source_global_id": item["source_global_id"],
                "substitute_id": item["substitute_id"],
            }
            for item in accepted
        ],
        "missing_sources": missing_sources,
        "ambiguous_candidates": ambiguous_candidates,
        "confidence": {
            item["source_global_id"]: item["confidence"] for item in accepted
        },
        "provenance": {
            item["source_global_id"]: item["provenance"] for item in accepted
        },
    }


def resolve_function_substitute(
    scene: NeutralSceneV2,
    source_object_id: str,
    consumer: str,
) -> dict[str, object]:
    """Keep the trend caller's result vocabulary over the shared resolver."""
    result = resolve_source_representation(scene, source_object_id, consumer)
    if result["status"] == "unresolved":
        result = {**result, "status": result.get("resolver_status", "rejected")}
    return result


def _resolve_typed_binding(scene, source_object_id, descriptor, registry, query=None):
    """Resolve one typed function binding without selecting by name or order.

    The binding lives on the owning source object while geometry lives on an
    independent analysis substitute object.  Every rejection keeps its reason
    so callers can distinguish missing, invalid, and ambiguous evidence.
    """
    sources = [item for item in scene.source_objects if item.id == str(source_object_id)]
    if not sources:
        return _resolution("not_available", "source_object_not_found", source_object_id=source_object_id)
    if len(sources) != 1:
        return _resolution("ambiguous", "duplicate_source_object_id", source_object_id=source_object_id)

    source = sources[0]
    raw_bindings = source.factual_properties.get("OM_FunctionSubstitutes")
    if raw_bindings is None:
        return _resolution("not_available", "missing_typed_binding", source_object_id=source.id)
    if not isinstance(raw_bindings, (list, tuple)):
        return _resolution("rejected", "invalid_binding_collection", source_object_id=source.id)

    consumer = descriptor["consumer"]
    candidates: list[tuple[Mapping[str, Any], object, dict[str, object]]] = []
    rejections: list[dict[str, object]] = []
    for index, raw in enumerate(raw_bindings):
        if not isinstance(raw, Mapping):
            rejections.append({"index": index, "reason": "invalid_binding"})
            continue
        if raw.get("consumer") != consumer:
            continue
        declared_owner = raw.get("source_object_id")
        if declared_owner is not None and declared_owner != source.id:
            rejections.append({"index": index, "reason": "source_owner_mismatch"})
            continue
        contract = resolve_substitute_contract(
            ({**raw, "source_object_id": source.id}
             if "source_object_id" not in raw and descriptor["coverage"] == "single_source" else raw),
            str(consumer), registry
        )
        if contract["status"] != "accepted":
            rejections.append({
                "index": index,
                "reason": contract["reason_code"],
                "provenance": dict(raw.get("provenance", {})) if isinstance(raw.get("provenance"), Mapping) else None,
            })
            continue
        if raw.get("substitute_kind") != descriptor["substitute_kind"]:
            rejections.append({"index": index, "reason": "wrong_substitute_kind"})
            continue
        if raw.get("analysis_role") != descriptor["input"]:
            rejections.append({"index": index, "reason": "wrong_analysis_role"})
            continue
        substitute_id = str(raw.get("substitute_id") or "")
        if not substitute_id:
            rejections.append({"index": index, "reason": "missing_substitute_id"})
            continue
        targets = [item for item in scene.source_objects if item.id == substitute_id]
        if not targets:
            rejections.append({
                "index": index,
                "reason": "unresolved_substitute_id",
                "substitute_id": substitute_id,
                "provenance": dict(raw.get("provenance", {})),
            })
            continue
        if len(targets) != 1:
            rejections.append({
                "index": index,
                "reason": "ambiguous_substitute_id",
                "substitute_id": substitute_id,
                "provenance": dict(raw.get("provenance", {})),
            })
            continue
        target = targets[0]
        if target.id == source.id:
            rejections.append({"index": index, "reason": "substitute_must_be_independent", "substitute_id": substitute_id, "provenance": dict(target.provenance)})
            continue
        if target.source_role != "analysis_substitute":
            rejections.append({"index": index, "reason": "wrong_source_role", "substitute_id": substitute_id, "provenance": dict(target.provenance)})
            continue
        expected_representation = contract["accepted_representation_identifier"]
        if target.provenance.get("representation_identifier") != expected_representation:
            rejections.append({"index": index, "reason": "wrong_representation_identifier", "substitute_id": substitute_id, "provenance": dict(target.provenance)})
            continue
        geometry_reason = _geometry_rejection(scene, target, descriptor["geometry_query"], query)
        if geometry_reason:
            rejections.append({"index": index, "reason": geometry_reason, "substitute_id": substitute_id, "provenance": dict(target.provenance)})
            continue
        candidates.append((raw, target, contract))

    if len(candidates) > 1:
        return _resolution(
            "ambiguous",
            "multiple_valid_substitutes",
            source_object_id=source.id,
            rejections=rejections,
            candidates=[str(target.id) for _, target, _ in candidates],
        )
    if not candidates:
        reason = rejections[0]["reason"] if rejections else (
            "wrong_consumer" if raw_bindings else "no_valid_typed_binding"
        )
        status = "not_available" if reason in {
            "missing_geometry",
            "no_valid_typed_binding",
            "unresolved_substitute_id",
        } else "ambiguous" if reason == "ambiguous_substitute_id" else "rejected"
        provenance = [item.get("provenance") for item in rejections if item.get("provenance")]
        return _resolution(
            status,
            str(reason),
            source_object_id=source.id,
            rejections=rejections,
            provenance=provenance[0] if len(provenance) == 1 else None,
            candidate_provenance=provenance,
        )

    binding, target, contract = candidates[0]
    return {
        "status": "accepted",
        "selected_substitute_id": str(binding["substitute_id"]),
        "source_object_id": source.id,
        "substitute_source_object_id": target.id,
        "reason": "typed_analysis_binding",
        "provenance": dict(binding["provenance"]),
        "substitute_provenance": dict(target.provenance),
        "binding": dict(binding),
        "rejections": rejections,
    }


def resolve_source_representation(
    scene: NeutralSceneV2,
    source_object_id: str,
    operation: str,
    *,
    query: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Select a representative; exact-plane eligibility does not certify its section."""
    registry = load_substitute_registry()
    descriptor = registry.get("operations", {}).get(operation)
    base = {"operation": operation, "original_source_id": str(source_object_id),
            "selected_source": None, "selected_geometry": (), "coverage": ()}
    if not isinstance(descriptor, Mapping):
        return _unresolved(base, "unknown_operation", source_object_id=source_object_id)
    # This small vocabulary describes existing operations, not executable rules.
    policies = {
        "input": {"analysis_geometry_substitute", "physical_occupancy_substitute", "physical_occupancy"},
        "geometry_query": {"plan_projection", "whole_height_planar_mass_patch", "exact_world_plane_section"},
        "fallback": {"unresolved", "original_without_required_binding"},
        "coverage": {"single_source", "declared_exact_source_set"},
        "substitute_kind": {"MassPatch"},
    }
    for key, allowed in policies.items():
        if descriptor.get(key) not in allowed:
            reason = {"input": "unknown_input_requirement", "geometry_query": "unknown_geometry_query",
                      "fallback": "unknown_fallback_policy", "coverage": "unknown_coverage_policy",
                      "substitute_kind": "unknown_substitute_kind"}[key]
            return _unresolved(base, reason, source_object_id=source_object_id)
    if not isinstance(descriptor.get("consumer"), str) or not descriptor["consumer"]:
        return _unresolved(base, "invalid_operation_consumer", source_object_id=source_object_id)
    if descriptor["input"] == "physical_occupancy":
        # Free-space consumes the qualified occupancy input, using its policies.
        upstream = registry.get("operations", {}).get("physical_occupancy")
        if operation == "physical_occupancy" or not isinstance(upstream, Mapping):
            return _unresolved(base, "invalid_operation_input", source_object_id=source_object_id)
        result = resolve_source_representation(scene, source_object_id, "physical_occupancy", query=query)
        return {**result, "operation": operation, "input": "physical_occupancy"}
    base["geometry_query"] = descriptor["geometry_query"]
    if descriptor["geometry_query"] == "exact_world_plane_section":
        from .section_views import section_query_height
        try:
            section_query_height(query)
        except ValueError:
            return _unresolved(base, "invalid_exact_world_plane_query", source_object_id=source_object_id)
        base["query"] = dict(query)
    sources = [item for item in scene.source_objects if item.id == str(source_object_id)]
    if len(sources) != 1:
        return _unresolved(base, "source_object_not_found" if not sources else "duplicate_source_object_id",
                           source_object_id=source_object_id)
    source = sources[0]
    raw_bindings = source.factual_properties.get("OM_FunctionSubstitutes")
    binding_present = (any(isinstance(item, Mapping) and item.get("consumer") == descriptor["consumer"]
                           for item in raw_bindings)
                       if isinstance(raw_bindings, (list, tuple)) else raw_bindings is not None)
    if binding_present and descriptor["geometry_query"] == "exact_world_plane_section":
        # Failed required targets affect their entire declared/bound owner set.
        base["required_coverage"] = _required_coverage(scene, source, descriptor["consumer"])
    if not binding_present and descriptor["fallback"] == "original_without_required_binding":
        reason = _geometry_rejection(scene, source, descriptor["geometry_query"], query)
        if reason:
            return _unresolved(base, reason, source_object_id=source.id)
        return {**_resolution("original", "qualified_original_geometry", source_object_id=source.id), **base,
                "selected_source": source.id, "selected_geometry": tuple(source.geometry_refs),
                "coverage": (source.id,), "rejection_diagnostics": [], "provenance": dict(source.provenance)}
    result = _resolve_typed_binding(scene, source.id, descriptor, registry, query)
    if result["status"] != "accepted":
        return {**result, **base, "status": "unresolved", "resolver_status": result["status"],
                "rejection_diagnostics": result["rejections"] or [{"reason": result["reason"]}]}
    target = next(item for item in scene.source_objects if item.id == result["substitute_source_object_id"])
    coverage = (source.id,)
    if descriptor["coverage"] == "declared_exact_source_set":
        coverage, reason = _exact_coverage(scene, target, descriptor, registry, query)
        if reason:
            return _unresolved({**result, **base}, reason, source_object_id=source.id)
    return {**result, **base, "selected_source": target.id, "selected_geometry": tuple(target.geometry_refs),
            "coverage": coverage, "rejection_diagnostics": result["rejections"]}


def _unresolved(base, reason, *, source_object_id):
    """Retain a refusal reason in both shared and compatibility vocabularies."""
    return {**_resolution("unresolved", reason, source_object_id=source_object_id), **base,
            "status": "unresolved", "reason": reason,
            "selected_source": None, "selected_geometry": (), "coverage": (),
            "resolver_status": "not_available" if reason == "missing_geometry" else "rejected",
            "rejection_diagnostics": [{"reason": reason}]}


def _geometry_rejection(scene, source, geometry_query, query=None):
    """Validate refs and frames; section qualification is a separate geometry step."""
    refs = source.geometry_refs
    if not refs:
        return "missing_geometry"
    if len(refs) != len(set(refs)):
        return "duplicate_geometry_ref"
    for ref in refs:
        matches = [mesh for mesh in scene.geometries if mesh.id == ref]
        if not matches:
            return "missing_geometry"
        if len(matches) != 1:
            return "duplicate_geometry_id"
        mesh = matches[0]
        if mesh.units != scene.context.analysis_length_unit or mesh.units == "custom":
            return "geometry_units_not_normalized"
        if not mesh.local_to_world_provenance or mesh.local_to_world_provenance.get("world_transform_applied") is False:
            return "geometry_frame_unqualified"
        if geometry_query == "exact_world_plane_section":
            if mesh.units != "m":
                return "geometry_units_not_normalized"
            if mesh.local_to_world_provenance.get("world_transform_applied") is not True:
                return "geometry_frame_unqualified"
            # Empty XY projection cannot disqualify a legal above/below-plane result.
            continue
        projection = plan_projection(mass_patch_from_mesh(mesh), scene.context.analysis_plane)
        if not projection.components:
            return "missing_planar_geometry"
    return None


def _required_coverage(scene, source, consumer):
    """Retain all declared and bound owners when required section selection fails."""
    raw = source.factual_properties.get("OM_FunctionSubstitutes", ())
    bindings = raw if isinstance(raw, (list, tuple)) else ()
    target_ids = {item.get("substitute_id") for item in bindings
                  if isinstance(item, Mapping) and item.get("consumer") == consumer
                  and isinstance(item.get("substitute_id"), str)}
    owners = {source.id}
    for item in scene.source_objects:
        if item.id in target_ids:
            facts = item.factual_properties.get("OM_PhysicalOccupancy", {})
            declared = facts.get("represented_source_ids", ()) if isinstance(facts, Mapping) else ()
            if isinstance(declared, (list, tuple)):
                owners.update(value for value in declared if isinstance(value, str))
        raw = item.factual_properties.get("OM_FunctionSubstitutes", ())
        if isinstance(raw, (list, tuple)) and any(
            isinstance(binding, Mapping) and binding.get("consumer") == consumer
            and binding.get("substitute_id") in target_ids for binding in raw
        ):
            owners.add(item.id)
    return tuple(sorted(owners))


def _exact_coverage(scene, target, descriptor, registry, query=None):
    """Require exact target coverage of all same-purpose source-owned bindings."""
    facts = target.factual_properties.get("OM_PhysicalOccupancy")
    declared = facts.get("represented_source_ids") if isinstance(facts, Mapping) else None
    if (not isinstance(declared, (list, tuple)) or not declared
            or any(not isinstance(value, str) or not value.strip() for value in declared)
            or len(declared) != len(set(declared))):
        return (), "invalid_coverage_declaration"
    owners = []
    for source in scene.source_objects:
        raw = source.factual_properties.get("OM_FunctionSubstitutes")
        bindings = [item for item in raw if isinstance(item, Mapping) and item.get("consumer") == descriptor["consumer"]] if isinstance(raw, (list, tuple)) else []
        matching = [item for item in bindings if item.get("substitute_id") == target.id]
        if not matching:
            continue
        if source.source_role == "analysis_substitute" or len(bindings) != 1:
            return (), "overlapping_or_ambiguous_coverage"
        if matching[0].get("source_object_id") != source.id:
            return (), "source_owner_mismatch"
        if sum(item.id == source.id for item in scene.source_objects) != 1:
            return (), "duplicate_source_object_id"
        # Exact coverage cannot borrow legitimacy from a different owner's valid binding.
        qualification = _resolve_typed_binding(scene, source.id, descriptor, registry, query)
        if qualification["status"] != "accepted":
            return (), qualification["reason"]
        owners.append(source.id)
    if set(declared) != set(owners):
        return (), "coverage_source_set_mismatch"
    return tuple(sorted(owners)), None


def _resolution(status: str, reason: str, **fields: object) -> dict[str, object]:
    """Build one stable resolver result for diagnostics and JSON output."""
    return {
        "status": status,
        "selected_substitute_id": None,
        "source_object_id": fields.pop("source_object_id", None),
        "substitute_source_object_id": None,
        "reason": reason,
        "provenance": None,
        "rejections": fields.pop("rejections", []),
        **fields,
    }


__all__ = ["discover_analysis_substitutes", "resolve_function_substitute", "resolve_source_representation"]
