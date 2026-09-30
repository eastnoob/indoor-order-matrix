"""Read-only discovery of already-authored analysis geometry substitutes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .substitute_contract import load_substitute_registry, resolve_substitute_contract
from .scene_contract import NeutralSceneV2


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

    registry = load_substitute_registry()
    candidates: list[tuple[Mapping[str, Any], object, dict[str, object]]] = []
    rejections: list[dict[str, object]] = []
    for index, raw in enumerate(raw_bindings):
        if not isinstance(raw, Mapping):
            rejections.append({"index": index, "reason": "invalid_binding"})
            continue
        contract = resolve_substitute_contract(
            {**raw, "source_object_id": source.id}, str(consumer), registry
        )
        if contract["status"] != "accepted":
            rejections.append({"index": index, "reason": contract["reason_code"]})
            continue
        substitute_id = str(raw.get("substitute_id") or "")
        if not substitute_id:
            rejections.append({"index": index, "reason": "missing_substitute_id"})
            continue
        targets = [item for item in scene.source_objects if item.id == substitute_id]
        if not targets:
            rejections.append({"index": index, "reason": "unresolved_substitute_id", "substitute_id": substitute_id})
            continue
        if len(targets) != 1:
            rejections.append({"index": index, "reason": "ambiguous_substitute_id", "substitute_id": substitute_id})
            continue
        target = targets[0]
        if target.id == source.id:
            rejections.append({"index": index, "reason": "substitute_must_be_independent", "substitute_id": substitute_id})
            continue
        if target.source_role != "analysis_substitute":
            rejections.append({"index": index, "reason": "wrong_source_role", "substitute_id": substitute_id})
            continue
        expected_representation = contract["accepted_representation_identifier"]
        if target.provenance.get("representation_identifier") != expected_representation:
            rejections.append({"index": index, "reason": "wrong_representation_identifier", "substitute_id": substitute_id})
            continue
        if not target.geometry_refs:
            rejections.append({"index": index, "reason": "missing_geometry", "substitute_id": substitute_id})
            continue
        geometry_ids = {geometry.id for geometry in scene.geometries}
        if any(ref not in geometry_ids for ref in target.geometry_refs):
            rejections.append({"index": index, "reason": "missing_geometry", "substitute_id": substitute_id})
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
        reason = rejections[0]["reason"] if rejections else "no_valid_typed_binding"
        status = "not_available" if reason in {
            "missing_geometry",
            "no_valid_typed_binding",
            "unresolved_substitute_id",
        } else "ambiguous" if reason == "ambiguous_substitute_id" else "rejected"
        return _resolution(status, str(reason), source_object_id=source.id, rejections=rejections)

    binding, target, contract = candidates[0]
    return {
        "status": "accepted",
        "selected_substitute_id": str(binding["substitute_id"]),
        "source_object_id": source.id,
        "substitute_source_object_id": target.id,
        "reason": "typed_analysis_binding",
        "provenance": dict(binding["provenance"]),
        "binding": dict(binding),
        "rejections": rejections,
    }


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


__all__ = ["discover_analysis_substitutes", "resolve_function_substitute"]
