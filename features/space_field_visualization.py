"""Build deterministic, standalone manifests for Field samples."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .field_core import FieldSample, FieldStatus


def _json_value(value: Any) -> Any:
    """Convert immutable field metadata into JSON-friendly containers."""
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def build_field_layer_manifest(
    *, layer_id: str, channel: str, samples: Iterable[FieldSample[Any]]
) -> dict[str, Any]:
    """Return an explicit deterministic visualization manifest for samples."""
    if not isinstance(layer_id, str) or not layer_id.strip():
        raise ValueError("layer_id must be a non-empty string")
    if not isinstance(channel, str) or not channel.strip():
        raise ValueError("channel must be a non-empty string")
    if isinstance(samples, (str, bytes)) or samples is None:
        raise TypeError("samples must be a non-empty FieldSample iterable")
    records = []
    for sample in samples:
        if not isinstance(sample, FieldSample):
            raise TypeError("samples must contain FieldSample values")
        status = sample.status
        provenance = _json_value(sample.provenance)
        query = sample.query
        records.append(
            {
                "status": status.value,
                "visual_state": _visual_state(status),
                "value": _json_value(sample.value),
                "source_ids": list(sample.source_ids),
                "support": _json_value(sample.support),
                "domain_id": query.domain_id,
                "frame": query.frame,
                "plane": _json_value(query.plane),
                "height_band": _json_value(query.height_band),
                "demand": _json_value(query.demand),
                "tolerance": provenance.get("tolerance", query.tolerance),
                "revision": query.revision,
                "units": provenance.get("units"),
                "algorithm_version": provenance["algorithm_version"],
                "schema_version": provenance["schema_version"],
                "provenance": provenance,
                "explanation": sample.explanation,
            }
        )
    if not records:
        raise ValueError("samples must not be empty")
    return {
        "schema": "field-layer-manifest/v1",
        "layer_id": layer_id,
        "semantic_channel": channel,
        "samples": records,
    }


def _visual_state(status: FieldStatus) -> str:
    """Map every status to a distinct display state without implying free space."""
    return {
        FieldStatus.CONDITIONAL: "conditional",
        FieldStatus.UNKNOWN: "unknown",
        FieldStatus.INVALID: "invalid",
        FieldStatus.OUTSIDE: "outside",
        FieldStatus.ESTABLISHED: "established",
        FieldStatus.NOT_AVAILABLE: "not_available",
    }[status]
