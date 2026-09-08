"""Read-only discovery of already-authored analysis geometry substitutes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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


__all__ = ["discover_analysis_substitutes"]
