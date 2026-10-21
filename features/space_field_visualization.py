"""Build deterministic, standalone manifests for Field samples."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from .field_core import (
    EvidenceChannelRecord,
    FieldResultEnvelope,
    FieldSample,
    FieldStatus,
    project_field_sample,
)


def _json_value(value: Any) -> Any:
    """Convert immutable field metadata into JSON-friendly containers."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
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


def build_field_result_layer_manifest(
    *, layer_id: str, channel: str, results: Iterable[FieldResultEnvelope]
) -> dict[str, Any]:
    """Project immutable result envelopes into the existing layer manifest."""
    if not isinstance(layer_id, str) or not layer_id.strip():
        raise ValueError("layer_id must be a non-empty string")
    if not isinstance(channel, str) or not channel.strip():
        raise ValueError("channel must be a non-empty string")
    if isinstance(results, (str, bytes)) or results is None:
        raise TypeError("results must be a non-empty FieldResultEnvelope iterable")

    records = []
    for result in results:
        if not isinstance(result, FieldResultEnvelope):
            raise TypeError("results must contain FieldResultEnvelope values")
        sample = project_field_sample(result)
        if sample is None:
            query = result.query
            status = "unknown"
            visual_state = "unknown"
            value = None
            support = result.support
            source_ids = result.source_ids
            provenance = result.provenance
            explanation = (
                result.field_projection["mapping_reason"]
                if result.field_projection is not None
                else result.explanation
            )
        else:
            query = sample.query
            status = sample.status.value
            visual_state = _visual_state(sample.status)
            value = sample.value
            support = sample.support
            source_ids = sample.source_ids
            provenance = sample.provenance
            explanation = sample.explanation
        records.append(
            {
                "status": status,
                "visual_state": visual_state,
                "value": _json_value(value),
                "source_ids": list(source_ids),
                "support": _json_value(support),
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
                "provenance": _json_value(provenance),
                "explanation": explanation,
                "raw_status": result.raw_status.value,
                "channel_set": list(result.channel_set),
                "channel_records": [
                    _json_value(_channel_record(record))
                    for record in _envelope_channels(result)
                ],
            }
        )
    if not records:
        raise ValueError("results must not be empty")
    return {
        "schema": "field-layer-manifest/v1",
        "layer_id": layer_id,
        "semantic_channel": channel,
        "samples": records,
    }


def _envelope_channels(result: FieldResultEnvelope) -> tuple[EvidenceChannelRecord, ...]:
    """Return serialized channel-bearing evidence, including unavailable channels."""
    if result.value is None:
        return ()
    return tuple(result.value["channels"])


def _channel_record(record: EvidenceChannelRecord) -> dict[str, Any]:
    """Convert one immutable evidence record to the manifest's JSON shape."""
    return {
        "channel": record.channel,
        "required": record.required,
        "polarity": record.polarity,
        "observation": record.observation,
        "support": record.support,
        "units": record.units,
        "status": record.status.value,
        "source_ids": list(record.source_ids),
        "provenance": record.provenance,
        "explanation": record.explanation,
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
