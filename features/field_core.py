"""Immutable core contracts for exact, auditable field lookups."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
import hashlib
import json
from math import isfinite
from types import MappingProxyType
from typing import Any, Callable, Generic, TypeVar


Target = TypeVar("Target")
Value = TypeVar("Value")


class FieldStatus(str, Enum):
    """The six unordered outcome states shared by field samples."""

    ESTABLISHED = "established"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"
    OUTSIDE = "outside"
    INVALID = "invalid"
    NOT_AVAILABLE = "not_available"


class FieldResultStatus(str, Enum):
    """Raw computation states retained by a field result envelope."""

    COMPUTED = "computed"
    PARTIAL = "partial"
    NOT_EVALUATED = "not_evaluated"
    NOT_AVAILABLE = "not_available"
    INVALID = "invalid"
    OUTSIDE = "outside"
    AMBIGUOUS = "ambiguous"


def _freeze(value: Any) -> Any:
    """Return a JSON-safe immutable representation of a nested value."""
    if type(value) is _MetadataOverlay:
        return value.mapping
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if is_dataclass(value):
        params = getattr(value, "__dataclass_params__", None)
        if params is None or not params.frozen:
            raise TypeError(f"mutable dataclass {type(value).__name__} is not JSON-safe")
        frozen_fields = {}
        for field in fields(value):
            nested = getattr(value, field.name)
            frozen = _freeze(nested)
            if frozen is not nested:
                if not field.init:
                    raise TypeError(
                        f"frozen dataclass {type(value).__name__} has an unsafe non-init field"
                    )
                frozen_fields[field.name] = frozen
        if not frozen_fields:
            return value
        try:
            # Rebuild the same dataclass type so contract records retain their API.
            return replace(value, **frozen_fields)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"frozen dataclass {type(value).__name__} cannot be safely frozen"
            ) from exc
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("JSON-safe values cannot contain non-finite floats")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("mapping keys must be strings")
        # Deep freezing preserves audit data without exposing mutable containers.
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    raise TypeError(f"value of type {type(value).__name__} is not JSON-safe")


@dataclass(frozen=True, slots=True, init=False)
class _MetadataOverlay:
    """Reuse privately validated audit values while freezing only local metadata."""

    mapping: Mapping[str, Any]

    def __init__(self, base: Mapping[str, Any] | _MetadataOverlay,
                 local: Mapping[str, Any] | _MetadataOverlay | None = None) -> None:
        """Detach caller mappings; only this private exact type may reuse frozen data."""
        # An exact private overlay already contains deeply frozen values. Reuse
        # its immutable mapping directly so shared request audit records retain
        # identity across per-sample overlays instead of being copied per cell.
        shared = base.mapping if type(base) is _MetadataOverlay else _freeze(base)
        changes = (local.mapping if type(local) is _MetadataOverlay else
                   _freeze({} if local is None else local))
        if not isinstance(shared, Mapping) or not isinstance(changes, Mapping):
            raise TypeError("metadata must be a mapping")
        # Sharing the immutable base avoids copying large per-cell audit payloads.
        object.__setattr__(self, "mapping", MappingProxyType({**shared, **changes}))


def _json_value(value: Any) -> Any:
    """Convert frozen JSON-safe values into deterministic JSON structures."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, EvidencePackageDependency):
        return {
            "package_id": value.package_id,
            "output_identity": value.output_identity,
            "package_freshness": value.package_freshness,
            "channels": _json_value(value.channels),
        }
    if is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    """Serialize a JSON-safe value with stable key and separator ordering."""
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class FieldQuery:
    """Immutable request context retained by every field sample."""

    domain_id: str | None = None
    frame: str | None = None
    plane: Any = None
    height_band: Any = None
    demand: Any = None
    tolerance: float = 0.0
    revision: str = ""

    def __post_init__(self) -> None:
        """Validate scalar query fields and deep-freeze optional context."""
        if self.domain_id is not None and not isinstance(self.domain_id, str):
            raise TypeError("domain_id must be a string or None")
        if self.frame is not None and not isinstance(self.frame, str):
            raise TypeError("frame must be a string or None")
        if not isinstance(self.revision, str):
            raise TypeError("revision must be a string")
        if isinstance(self.tolerance, bool) or not isinstance(self.tolerance, (int, float)):
            raise TypeError("tolerance must be a real number")
        if not isfinite(float(self.tolerance)) or self.tolerance < 0:
            raise ValueError("tolerance must be finite and non-negative")
        object.__setattr__(self, "tolerance", float(self.tolerance))
        for name in ("plane", "height_band", "demand"):
            object.__setattr__(self, name, _freeze(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class FieldSample(Generic[Value]):
    """Immutable value/status result with query, support, and provenance."""

    value: Value | None
    status: FieldStatus
    query: FieldQuery
    support: Any = None
    source_ids: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = MappingProxyType({})
    explanation: str = ""

    def __post_init__(self) -> None:
        """Enforce status-gated values and freeze all audit payloads."""
        try:
            status = self.status if isinstance(self.status, FieldStatus) else FieldStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise ValueError("status must be a valid FieldStatus") from exc
        if not isinstance(self.query, FieldQuery):
            raise TypeError("query must be a FieldQuery")
        if status in {
            FieldStatus.INVALID,
            FieldStatus.NOT_AVAILABLE,
            FieldStatus.OUTSIDE,
            FieldStatus.UNKNOWN,
        } and self.value is not None:
            raise ValueError(f"{status.value} samples cannot carry a value")
        if status in {FieldStatus.CONDITIONAL, FieldStatus.ESTABLISHED} and self.value is None:
            raise ValueError(f"{status.value} samples require a value")
        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")
        if status is FieldStatus.CONDITIONAL and not self.explanation.strip():
            raise ValueError("conditional samples require a scope explanation")
        source_ids = tuple(self.source_ids)
        if any(not isinstance(source_id, str) for source_id in source_ids):
            raise TypeError("source_ids must contain strings")
        provenance = (self.provenance.mapping if type(self.provenance) is _MetadataOverlay
                      else _freeze(self.provenance))
        if not isinstance(provenance, Mapping):
            raise TypeError("provenance must be a mapping")
        if "algorithm_version" not in provenance or "schema_version" not in provenance:
            raise ValueError("provenance requires algorithm_version and schema_version")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "value", _freeze(self.value))
        object.__setattr__(self, "support", _freeze(self.support))
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True, slots=True)
class EvidenceChannelRecord:
    """Immutable, status-bearing observation for one admitted evidence channel."""

    channel: str
    required: bool
    polarity: str
    observation: Any = None
    support: Any = None
    units: str | None = None
    status: FieldResultStatus = FieldResultStatus.COMPUTED
    source_ids: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = MappingProxyType({})
    explanation: str = ""

    def __post_init__(self) -> None:
        """Validate and deeply freeze channel evidence and audit metadata."""
        if not isinstance(self.channel, str) or not self.channel.strip():
            raise ValueError("channel must be a non-empty string")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean")
        if self.polarity not in {"positive", "negative", "conflict", "descriptive"}:
            raise ValueError("polarity must be positive, negative, conflict, or descriptive")
        if self.units is not None and not isinstance(self.units, str):
            raise TypeError("units must be a string or None")
        try:
            status = self.status if isinstance(self.status, FieldResultStatus) else FieldResultStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise ValueError("status must be a valid FieldResultStatus") from exc
        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")
        source_ids = tuple(self.source_ids)
        if any(not isinstance(source_id, str) for source_id in source_ids):
            raise TypeError("source_ids must contain strings")
        provenance = _freeze(self.provenance)
        if not isinstance(provenance, Mapping):
            raise TypeError("provenance must be a mapping")
        if "algorithm_version" not in provenance and provenance.get("inherits_top_level") is not True:
            raise ValueError("channel provenance requires algorithm_version/schema_version or inherits_top_level")
        if "algorithm_version" in provenance and "schema_version" not in provenance:
            raise ValueError("channel provenance requires algorithm_version and schema_version")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "observation", _freeze(self.observation))
        object.__setattr__(self, "support", _freeze(self.support))
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True, slots=True)
class FieldResultEnvelope:
    """Canonical immutable result and audit boundary for field computations."""

    target: Mapping[str, str]
    query: FieldQuery
    raw_status: FieldResultStatus
    channel_set: tuple[str, ...]
    value: Any = None
    support: Any = None
    field_projection: Mapping[str, Any] | None = None
    source_ids: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = MappingProxyType({})
    cache_identity: Mapping[str, str] = MappingProxyType({})
    visualization_ref: Mapping[str, Any] | None = None
    explanation: str = ""
    schema: str = "field-result-envelope/v1"

    def __post_init__(self) -> None:
        """Normalize channel records and enforce envelope freshness invariants."""
        if not isinstance(self.target, Mapping):
            raise TypeError("target must be a mapping")
        if self.schema != "field-result-envelope/v1":
            raise ValueError("schema must be field-result-envelope/v1")
        target = _freeze(self.target)
        if any(not isinstance(target.get(key), str) or not target[key].strip() for key in ("kind", "id", "identity")):
            raise ValueError("target requires non-empty kind, id, and identity")
        if not isinstance(self.query, FieldQuery):
            raise TypeError("query must be a FieldQuery")
        try:
            raw_status = self.raw_status if isinstance(self.raw_status, FieldResultStatus) else FieldResultStatus(self.raw_status)
        except (TypeError, ValueError) as exc:
            raise ValueError("raw_status must be a valid FieldResultStatus") from exc
        channels = tuple(self.channel_set)
        if any(not isinstance(channel, str) or not channel.strip() for channel in channels):
            raise ValueError("channel_set entries must be non-empty strings")
        if len(set(channels)) != len(channels):
            raise ValueError("channel_set cannot contain duplicates")
        channels = tuple(sorted(channels))
        records = ()
        if channels and self.value is None:
            raise ValueError("non-empty channel_set requires channel records")
        if self.value is not None:
            if not isinstance(self.value, Mapping) or "channels" not in self.value:
                raise TypeError("value must be a mapping containing channels")
            records = tuple(self.value["channels"])
            if any(not isinstance(record, EvidenceChannelRecord) for record in records):
                raise TypeError("value.channels must contain EvidenceChannelRecord values")
            keys = [(record.channel, record.polarity) for record in records]
            if len(set(keys)) != len(keys):
                raise ValueError("channel records cannot duplicate channel/polarity keys")
            names = [record.channel for record in records]
            if any(record.channel not in channels for record in records):
                raise ValueError("channel record is outside channel_set")
            if set(names) != set(channels):
                raise ValueError("value.channels must represent every admitted channel")
            records = tuple(sorted(records, key=lambda record: (record.channel, record.polarity)))
        if raw_status is FieldResultStatus.COMPUTED and (not channels or self.value is None):
            raise ValueError("computed results require channel evidence")
        if raw_status is not FieldResultStatus.COMPUTED and not isinstance(self.explanation, str):
            raise TypeError("non-computed results require a string explanation")
        if raw_status is not FieldResultStatus.COMPUTED and not self.explanation.strip():
            raise ValueError("non-computed results require an explanation")
        provenance = _freeze(self.provenance)
        if not isinstance(provenance, Mapping) or "algorithm_version" not in provenance or "schema_version" not in provenance:
            raise ValueError("provenance requires algorithm_version and schema_version")
        cache_identity = _freeze(self.cache_identity)
        if not isinstance(cache_identity, Mapping):
            raise TypeError("cache_identity must be a mapping")
        required_identity = {"input_fingerprint", "source_fingerprint", "query_fingerprint", "channel_fingerprint", "recipe_fingerprint", "algorithm_version", "schema_version", "identity"}
        if required_identity - set(cache_identity) or any(not isinstance(cache_identity[key], str) or not cache_identity[key] for key in required_identity):
            raise ValueError("cache_identity is incomplete")
        source_ids = tuple(self.source_ids)
        if any(not isinstance(source_id, str) for source_id in source_ids):
            raise TypeError("source_ids must contain strings")
        projection = None if self.field_projection is None else _freeze(self.field_projection)
        if projection is not None:
            if projection.get("status") not in {status.value for status in FieldStatus}:
                raise ValueError("field_projection.status must be a valid FieldStatus")
            if not isinstance(projection.get("mapping_reason"), str) or not projection["mapping_reason"].strip():
                raise ValueError("field_projection requires a mapping_reason")
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "raw_status", raw_status)
        object.__setattr__(self, "channel_set", channels)
        object.__setattr__(self, "value", None if self.value is None else MappingProxyType({"channels": records}))
        object.__setattr__(self, "support", _freeze(self.support))
        object.__setattr__(self, "field_projection", projection)
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "cache_identity", cache_identity)
        object.__setattr__(self, "visualization_ref", None if self.visualization_ref is None else _freeze(self.visualization_ref))


@dataclass(frozen=True, slots=True)
class EvidenceChannelReference:
    """Identify one input channel within an immutable field result."""

    result_identity: str
    target_identity: str
    channel: str

    def __post_init__(self) -> None:
        """Reject incomplete references so package outputs remain traceable."""
        for name in ("result_identity", "target_identity", "channel"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    @classmethod
    def from_envelope(cls, envelope: FieldResultEnvelope, channel: str) -> EvidenceChannelReference:
        """Create a stable reference to an admitted channel on an envelope."""
        if not isinstance(envelope, FieldResultEnvelope):
            raise TypeError("envelope must be a FieldResultEnvelope")
        if channel not in envelope.channel_set:
            raise ValueError("channel must be admitted by the envelope")
        return cls(
            result_identity=envelope.cache_identity["identity"],
            target_identity=envelope.target["identity"],
            channel=channel,
        )


@dataclass(frozen=True, slots=True)
class EvidencePackageChannelReference:
    """Identify one channel published by an already evaluated evidence package."""

    package_id: str
    output_identity: str
    target_identity: str
    channel: str

    def __post_init__(self) -> None:
        """Reject incomplete external references before they enter lineage data."""
        for name in ("package_id", "output_identity", "target_identity", "channel"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        object.__setattr__(self, "package_id", self.package_id.strip())
        object.__setattr__(self, "output_identity", self.output_identity.strip())
        object.__setattr__(self, "target_identity", self.target_identity.strip())
        object.__setattr__(self, "channel", self.channel.strip())


@dataclass(frozen=True, slots=True)
class EvidencePackageDependency:
    """Declare the published channels consumed from one upstream package output."""

    package_id: str
    output_identity: str
    channels: tuple[EvidencePackageChannelReference, ...]
    source_output: EvidencePackageOutput | None = None
    package_freshness: str = "unavailable"

    def __post_init__(self) -> None:
        """Require every declared channel to belong to this package output exactly once."""
        for name in ("package_id", "output_identity"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        channels = tuple(self.channels)
        if not channels or any(not isinstance(item, EvidencePackageChannelReference) for item in channels):
            raise ValueError("channels must contain EvidencePackageChannelReference values")
        if any(item.package_id != self.package_id for item in channels):
            raise ValueError("dependency channels must use the same package_id")
        if any(item.output_identity != self.output_identity for item in channels):
            raise ValueError("dependency channels must use the same output_identity")
        if len({item.channel for item in channels}) != len(channels):
            raise ValueError("dependency channels must be unique")
        if self.package_freshness not in {"fresh", "stale", "unavailable"}:
            raise ValueError("package_freshness must be fresh, stale, or unavailable")
        if self.source_output is not None:
            if not isinstance(self.source_output, EvidencePackageOutput):
                raise TypeError("source_output must be an EvidencePackageOutput or None")
            if self.source_output.package_id != self.package_id or self.source_output.output_identity != self.output_identity:
                raise ValueError("source_output identity must match dependency package and output")
        object.__setattr__(self, "package_id", self.package_id.strip())
        object.__setattr__(self, "output_identity", self.output_identity.strip())
        object.__setattr__(self, "channels", tuple(sorted(channels, key=lambda item: (item.target_identity, item.channel))))


@dataclass(frozen=True, slots=True)
class EvidencePackageResolvedDependency:
    """Separate a freshness-gated channel from its audit-only source record."""

    ref: EvidencePackageChannelReference
    channel: EvidenceOutputChannel | None
    audit_channel: EvidenceOutputChannel | None
    package_freshness: str
    channel_status: FieldResultStatus | None
    effective_status: FieldResultStatus
    explanation: str = ""

    def __post_init__(self) -> None:
        """Enforce the freshness gate and preserve the published channel status."""
        if not isinstance(self.ref, EvidencePackageChannelReference):
            raise TypeError("ref must be an EvidencePackageChannelReference")
        if self.channel is not None and not isinstance(self.channel, EvidenceOutputChannel):
            raise TypeError("channel must be an EvidenceOutputChannel or None")
        if self.audit_channel is not None and not isinstance(self.audit_channel, EvidenceOutputChannel):
            raise TypeError("audit_channel must be an EvidenceOutputChannel or None")
        if self.package_freshness not in {"fresh", "stale", "unavailable"}:
            raise ValueError("package_freshness must be fresh, stale, or unavailable")
        channel_status = self.channel_status
        if channel_status is not None:
            channel_status = channel_status if isinstance(channel_status, FieldResultStatus) else FieldResultStatus(channel_status)
        effective_status = self.effective_status
        if not isinstance(effective_status, FieldResultStatus):
            effective_status = FieldResultStatus(effective_status)
        if self.audit_channel is None and channel_status is not None:
            raise ValueError("channel_status requires an audit channel")
        if self.audit_channel is not None and channel_status is not self.audit_channel.status:
            raise ValueError("channel_status must preserve the source channel status")
        if self.package_freshness == "fresh" and self.channel is not self.audit_channel:
            raise ValueError("fresh dependencies must expose their resolved channel")
        if self.package_freshness != "fresh" and self.channel is not None:
            raise ValueError("stale or unavailable dependencies cannot expose a usable channel")
        expected = (
            channel_status
            if self.package_freshness == "fresh" and self.channel is not None
            else FieldResultStatus.NOT_AVAILABLE
        )
        if effective_status is not expected:
            raise ValueError("effective_status must respect package freshness")
        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")
        object.__setattr__(self, "channel_status", channel_status)
        object.__setattr__(self, "effective_status", effective_status)


@dataclass(frozen=True, slots=True)
class EvidencePackageInput:
    """Provide source envelopes and freshness-qualified upstream channels to a package."""

    source_envelopes: tuple[FieldResultEnvelope, ...]
    resolved_dependencies: tuple[EvidencePackageResolvedDependency, ...] = ()

    def __post_init__(self) -> None:
        """Keep package callback context immutable and contract-typed."""
        sources = tuple(self.source_envelopes)
        resolved = tuple(self.resolved_dependencies)
        if any(not isinstance(item, FieldResultEnvelope) for item in sources):
            raise TypeError("source_envelopes must contain FieldResultEnvelope values")
        if any(not isinstance(item, EvidencePackageResolvedDependency) for item in resolved):
            raise TypeError("resolved_dependencies must contain EvidencePackageResolvedDependency values")
        object.__setattr__(self, "source_envelopes", sources)
        object.__setattr__(self, "resolved_dependencies", resolved)


@dataclass(frozen=True, slots=True)
class EvidenceOutputScale:
    """Describe an output's meaning and any claimed normalization scale."""

    meaning: str
    scale_id: str | None = None
    units: str | None = None
    normalization_method: str | None = None
    value_range: tuple[float, float] | None = None
    endpoint_meanings: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate declared output scale metadata without choosing a scale."""
        if not isinstance(self.meaning, str) or not self.meaning.strip():
            raise ValueError("meaning must be a non-empty string")
        for name in ("scale_id", "units", "normalization_method"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be a non-empty string or None")
        if self.value_range is not None:
            if len(self.value_range) != 2:
                raise ValueError("value_range must contain exactly two bounds")
            lower, upper = self.value_range
            if (
                isinstance(lower, bool)
                or isinstance(upper, bool)
                or not isinstance(lower, (int, float))
                or not isinstance(upper, (int, float))
                or not isfinite(float(lower))
                or not isfinite(float(upper))
                or lower >= upper
            ):
                raise ValueError("value_range must contain finite increasing bounds")
            object.__setattr__(self, "value_range", (float(lower), float(upper)))
            if self.endpoint_meanings is None:
                raise ValueError("bounded scales require endpoint_meanings")
        if self.endpoint_meanings is not None:
            endpoints = tuple(self.endpoint_meanings)
            if len(endpoints) != 2 or any(not isinstance(item, str) or not item.strip() for item in endpoints):
                raise ValueError("endpoint_meanings must contain two non-empty strings")
            if self.value_range is None:
                raise ValueError("endpoint_meanings require value_range")
            object.__setattr__(self, "endpoint_meanings", endpoints)


@dataclass(frozen=True, slots=True)
class EvidenceOutputChannel:
    """Store one package-derived output without replacing its source evidence."""

    target: Mapping[str, str]
    channel: str
    observation: Any
    status: FieldResultStatus
    scale: EvidenceOutputScale
    derived_from: tuple[EvidenceChannelReference | EvidencePackageChannelReference, ...]
    source_ids: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = MappingProxyType({})
    explanation: str = ""

    def __post_init__(self) -> None:
        """Freeze output data and require explicit input-channel lineage."""
        target = _freeze(self.target)
        if not isinstance(target, Mapping) or any(
            not isinstance(target.get(key), str) or not target[key].strip()
            for key in ("kind", "id", "identity")
        ):
            raise ValueError("target requires non-empty kind, id, and identity")
        if not isinstance(self.channel, str) or not self.channel.strip():
            raise ValueError("channel must be a non-empty string")
        try:
            status = self.status if isinstance(self.status, FieldResultStatus) else FieldResultStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise ValueError("status must be a valid FieldResultStatus") from exc
        if not isinstance(self.scale, EvidenceOutputScale):
            raise TypeError("scale must be an EvidenceOutputScale")
        lineage = tuple(self.derived_from)
        if not lineage or any(not isinstance(item, (EvidenceChannelReference, EvidencePackageChannelReference)) for item in lineage):
            raise ValueError("derived_from must contain at least one valid channel reference")
        if len(set(lineage)) != len(lineage):
            raise ValueError("derived_from cannot contain duplicate references")
        source_ids = tuple(self.source_ids)
        if any(not isinstance(source_id, str) for source_id in source_ids):
            raise TypeError("source_ids must contain strings")
        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")
        if status is not FieldResultStatus.COMPUTED and not self.explanation.strip():
            raise ValueError("non-computed outputs require an explanation")
        provenance = _freeze(self.provenance)
        if not isinstance(provenance, Mapping):
            raise TypeError("provenance must be a mapping")
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "channel", self.channel.strip())
        object.__setattr__(self, "observation", _freeze(self.observation))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "derived_from", tuple(sorted(
            lineage,
            key=lambda ref: (
                getattr(ref, "result_identity", getattr(ref, "output_identity", "")),
                ref.target_identity,
                ref.channel,
            ),
        )))
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True, slots=True)
class EvidencePackageOutput:
    """Pair immutable source envelopes with additive package-owned outputs."""

    package_id: str
    output_function: str
    output_function_version: str
    source_envelopes: tuple[FieldResultEnvelope, ...]
    outputs: tuple[EvidenceOutputChannel, ...]
    dependencies: tuple[EvidencePackageDependency, ...] = ()
    schema: str = "evidence-package-output/v1"

    def __post_init__(self) -> None:
        """Validate output lineage while retaining every input envelope unchanged."""
        for name in ("package_id", "output_function", "output_function_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.schema != "evidence-package-output/v1":
            raise ValueError("schema must be evidence-package-output/v1")
        envelopes = tuple(self.source_envelopes)
        if not envelopes or any(not isinstance(item, FieldResultEnvelope) for item in envelopes):
            raise ValueError("source_envelopes must contain FieldResultEnvelope values")
        identities = [item.cache_identity["identity"] for item in envelopes]
        if len(set(identities)) != len(identities):
            raise ValueError("source_envelopes cannot contain duplicate result identities")
        envelopes = tuple(sorted(envelopes, key=lambda item: item.cache_identity["identity"]))
        outputs = tuple(self.outputs)
        if not outputs or any(not isinstance(item, EvidenceOutputChannel) for item in outputs):
            raise ValueError("outputs must contain EvidenceOutputChannel values")
        output_keys = [(item.target["identity"], item.channel) for item in outputs]
        if len(set(output_keys)) != len(output_keys):
            raise ValueError("outputs cannot duplicate target/channel pairs")

        dependencies = tuple(self.dependencies)
        if any(not isinstance(item, EvidencePackageDependency) for item in dependencies):
            raise TypeError("dependencies must contain EvidencePackageDependency values")
        declared_external_refs = {
            reference
            for dependency in dependencies
            for reference in dependency.channels
        }
        if any(dependency.package_id == self.package_id for dependency in dependencies):
            raise ValueError("evidence package output cannot depend on itself")
        available_refs = {
            (item.cache_identity["identity"], item.target["identity"], channel)
            for item in envelopes
            for channel in item.channel_set
        }
        for output in outputs:
            for ref in output.derived_from:
                if isinstance(ref, EvidencePackageChannelReference):
                    if ref not in declared_external_refs:
                        raise ValueError("external output lineage must be declared in dependencies")
                else:
                    key = (ref.result_identity, ref.target_identity, ref.channel)
                    if key not in available_refs:
                        raise ValueError("output lineage must reference a channel in source_envelopes")
            if any(
                output.target["identity"] == envelope.target["identity"]
                and output.channel in envelope.channel_set
                for envelope in envelopes
            ):
                raise ValueError("package outputs must not replace source evidence channels")

        outputs = tuple(sorted(outputs, key=lambda item: (item.target["identity"], item.channel)))
        object.__setattr__(self, "package_id", self.package_id.strip())
        object.__setattr__(self, "output_function", self.output_function.strip())
        object.__setattr__(self, "output_function_version", self.output_function_version.strip())
        object.__setattr__(self, "source_envelopes", envelopes)
        object.__setattr__(self, "outputs", outputs)
        # Published outputs retain compact references, not the upstream object graph.
        dependencies = tuple(
            replace(item, source_output=None) if item.source_output is not None else item
            for item in dependencies
        )
        object.__setattr__(self, "dependencies", tuple(sorted(
            dependencies, key=lambda item: (item.package_id, item.output_identity)
        )))

    @property
    def output_identity(self) -> str:
        """Return a stable cache key for these inputs and output declarations."""
        # The source identity and output declaration versioning invalidate derived results together.
        payload = {
            "schema": self.schema,
            "source_result_identities": tuple(
                envelope.cache_identity["identity"] for envelope in self.source_envelopes
            ),
            "package_id": self.package_id,
            "output_function": self.output_function,
            "output_function_version": self.output_function_version,
            "dependencies": tuple(
                {
                    "package_id": dependency.package_id,
                    "output_identity": dependency.output_identity,
                    "package_freshness": dependency.package_freshness,
                    "channels": dependency.channels,
                }
                for dependency in self.dependencies
            ),
            "outputs": tuple(
                {
                    "target": output.target,
                    "channel": output.channel,
                    "derived_from": output.derived_from,
                    "scale": output.scale,
                }
                for output in self.outputs
            ),
        }
        return hashlib.sha256(_canonical_json(payload).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidencePackage:
    """Define the required callable output step for one evidence package."""

    package_id: str
    output_function_id: str
    output_function_version: str
    output_function: Callable[[tuple[FieldResultEnvelope, ...]], Iterable[EvidenceOutputChannel]] | None
    context_output_function: Callable[[EvidencePackageInput], Iterable[EvidenceOutputChannel]] | None = None

    def __post_init__(self) -> None:
        """Validate stable function metadata before a package can run."""
        for name in ("package_id", "output_function_id", "output_function_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.output_function is None and self.context_output_function is None:
            raise TypeError("output_function or context_output_function must be callable")
        if self.output_function is not None and not callable(self.output_function):
            raise TypeError("output_function must be callable")
        if self.context_output_function is not None and not callable(self.context_output_function):
            raise TypeError("context_output_function must be callable")

    def evaluate(
        self,
        source_envelopes: Iterable[FieldResultEnvelope],
        *,
        dependencies: Iterable[EvidencePackageDependency] = (),
    ) -> EvidencePackageOutput:
        """Run the package function and validate its complete additive output."""
        envelopes = tuple(source_envelopes)
        if not envelopes or any(not isinstance(item, FieldResultEnvelope) for item in envelopes):
            raise TypeError("source_envelopes must contain FieldResultEnvelope values")

        dependencies = tuple(dependencies)
        if any(not isinstance(item, EvidencePackageDependency) for item in dependencies):
            raise TypeError("dependencies must contain EvidencePackageDependency values")
        if any(item.package_freshness == "fresh" and item.source_output is None for item in dependencies):
            raise ValueError("fresh dependencies require a typed source_output during evaluation")
        context = EvidencePackageInput(envelopes, _resolve_package_dependencies(dependencies))
        if self.context_output_function is not None:
            produced = self.context_output_function(context)
        else:
            produced = self.output_function(envelopes)
        if isinstance(produced, (str, bytes, Mapping)) or not isinstance(produced, Iterable):
            raise TypeError("output_function must return an iterable of EvidenceOutputChannel values")
        outputs = tuple(produced)

        # EvidencePackageOutput enforces lineage, status explanations, scale metadata,
        # duplicate prevention, and source-channel preservation in one shared boundary.
        return EvidencePackageOutput(
            package_id=self.package_id,
            output_function=self.output_function_id,
            output_function_version=self.output_function_version,
            source_envelopes=envelopes,
            outputs=outputs,
            dependencies=dependencies,
        )


def serialize_evidence_package_output(result: EvidencePackageOutput) -> dict[str, Any]:
    """Serialize package outputs together with their complete source envelopes."""
    if not isinstance(result, EvidencePackageOutput):
        raise TypeError("result must be an EvidencePackageOutput")
    serialized = _json_value(result)
    serialized["dependencies"] = [
        {
            "package_id": dependency.package_id,
            "output_identity": dependency.output_identity,
            "package_freshness": dependency.package_freshness,
            "channels": _json_value(dependency.channels),
        }
        for dependency in result.dependencies
    ]
    serialized["output_identity"] = result.output_identity
    return serialized


def _resolve_package_dependencies(
    dependencies: tuple[EvidencePackageDependency, ...],
) -> tuple[EvidencePackageResolvedDependency, ...]:
    """Resolve declared references while withholding stale observations as usable values."""
    resolved = []
    for dependency in dependencies:
        for reference in dependency.channels:
            if dependency.source_output is not None:
                resolved.append(resolve_evidence_package_channel(
                    dependency.source_output,
                    reference,
                    package_freshness=dependency.package_freshness,
                ))
                continue
            resolved.append(EvidencePackageResolvedDependency(
                ref=reference,
                channel=None,
                audit_channel=None,
                package_freshness=dependency.package_freshness,
                channel_status=None,
                effective_status=FieldResultStatus.NOT_AVAILABLE,
                explanation="upstream package output is unavailable",
            ))
    return tuple(resolved)


def read_evidence_package_channel(
    output: EvidencePackageOutput,
    reference: EvidencePackageChannelReference,
) -> EvidenceOutputChannel:
    """Read a published channel from its matching typed package output."""
    if not isinstance(output, EvidencePackageOutput):
        raise TypeError("output must be an EvidencePackageOutput")
    if not isinstance(reference, EvidencePackageChannelReference):
        raise TypeError("reference must be an EvidencePackageChannelReference")
    if output.package_id != reference.package_id:
        raise ValueError("reference package_id does not match output")
    if output.output_identity != reference.output_identity:
        raise ValueError("reference output_identity does not match output")
    for channel in output.outputs:
        if (
            channel.target["identity"] == reference.target_identity
            and channel.channel == reference.channel
        ):
            return channel
    raise ValueError("referenced target/channel is not published by output")


def resolve_evidence_package_channel(
    output: EvidencePackageOutput,
    reference: EvidencePackageChannelReference,
    *,
    package_freshness: str,
) -> EvidencePackageResolvedDependency:
    """Resolve a published channel while freshness-gating its usable observation."""
    if package_freshness not in {"fresh", "stale", "unavailable"}:
        raise ValueError("package_freshness must be fresh, stale, or unavailable")
    channel = read_evidence_package_channel(output, reference)
    usable = package_freshness == "fresh"
    return EvidencePackageResolvedDependency(
        ref=reference,
        channel=channel if usable else None,
        audit_channel=channel,
        package_freshness=package_freshness,
        channel_status=channel.status,
        effective_status=channel.status if usable else FieldResultStatus.NOT_AVAILABLE,
        explanation=("" if usable else
            "upstream package is stale" if package_freshness == "stale" else
            "upstream package output is unavailable"),
    )


def validate_evidence_package_dependency_graph(
    graph: Mapping[str, Iterable[str]],
) -> None:
    """Reject self-dependencies and longer cycles in a package dependency graph."""
    if not isinstance(graph, Mapping):
        raise TypeError("graph must be a mapping")
    normalized: dict[str, tuple[str, ...]] = {}
    for package_id, dependencies in graph.items():
        if not isinstance(package_id, str) or not package_id.strip():
            raise ValueError("graph package ids must be non-empty strings")
        if isinstance(dependencies, (str, bytes)) or not isinstance(dependencies, Iterable):
            raise TypeError("each dependency list must be iterable")
        entries = tuple(dependencies)
        if any(not isinstance(item, str) or not item.strip() for item in entries):
            raise ValueError("dependency package ids must be non-empty strings")
        normalized[package_id] = entries

    visiting: list[str] = []
    visited: set[str] = set()

    def visit(package_id: str) -> None:
        """Visit reachable dependencies and report the concrete cycle path."""
        if package_id in visiting:
            start = visiting.index(package_id)
            cycle = visiting[start:] + [package_id]
            raise ValueError("evidence package dependency cycle: " + " -> ".join(cycle))
        if package_id in visited:
            return
        visiting.append(package_id)
        for dependency in normalized.get(package_id, ()):
            visit(dependency)
        visiting.pop()
        visited.add(package_id)

    for package_id in normalized:
        visit(package_id)


def build_field_result_cache_identity(*, target: Mapping[str, Any], query: FieldQuery, channel_declarations: Iterable[Any], input_fingerprint: str, source_fingerprint: str, recipe_fingerprint: str, algorithm_version: str, schema_version: str) -> dict[str, str]:
    """Build deterministic fingerprints for the complete field input boundary."""
    for name, value in (("input_fingerprint", input_fingerprint), ("source_fingerprint", source_fingerprint), ("recipe_fingerprint", recipe_fingerprint), ("algorithm_version", algorithm_version), ("schema_version", schema_version)):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")
    canonical_target = _freeze(target)
    if not isinstance(query, FieldQuery):
        raise TypeError("query must be a FieldQuery")
    declarations = tuple(sorted((_freeze(declaration) for declaration in channel_declarations), key=_canonical_json))
    query_payload = {field: getattr(query, field) for field in ("domain_id", "frame", "plane", "height_band", "demand", "tolerance", "revision")}
    query_fingerprint = hashlib.sha256(_canonical_json(query_payload).encode()).hexdigest()
    channel_fingerprint = hashlib.sha256(_canonical_json(declarations).encode()).hexdigest()
    payload = {"target": canonical_target, "query": query_payload, "channel_declarations": declarations, "input_fingerprint": input_fingerprint, "source_fingerprint": source_fingerprint, "recipe_fingerprint": recipe_fingerprint, "algorithm_version": algorithm_version, "schema_version": schema_version}
    identity = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
    return {"input_fingerprint": input_fingerprint, "source_fingerprint": source_fingerprint, "query_fingerprint": query_fingerprint, "channel_fingerprint": channel_fingerprint, "recipe_fingerprint": recipe_fingerprint, "algorithm_version": algorithm_version, "schema_version": schema_version, "identity": identity}


_EVIDENCE_PACKAGE_CONTRACT_SCHEMA = "field-evidence-package-contract/v1"
_EVIDENCE_PACKAGE_STATUS_SCHEMA = "field-evidence-package-status/v1"
_EVIDENCE_PACKAGE_DEPENDENCIES = (
    "scene",
    "model",
    "source",
    "plane",
    "query",
    "recipe",
    "channels",
)
_EVIDENCE_PACKAGE_REASON_CODES = {
    "scene": "scene_changed",
    "model": "model_changed",
    "source": "source_changed",
    "plane": "plane_changed",
    "query": "query_changed",
    "recipe": "recipe_changed",
    "channels": "channel_set_changed",
}


def fingerprint_evidence_dependency(value: Any) -> str:
    """Return a content-derived SHA-256 for one package dependency value."""
    return hashlib.sha256(_canonical_json(_freeze(value)).encode()).hexdigest()


def _package_target_ids(value: Any) -> tuple[str, ...]:
    """Normalize a package target sequence and reject duplicate identifiers."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise TypeError("target_ids must be an iterable of strings")
    target_ids = tuple(value)
    if any(not isinstance(target, str) for target in target_ids):
        raise TypeError("target_ids must contain strings")
    target_ids = tuple(sorted(target_ids))
    if any(not target.strip() for target in target_ids):
        raise ValueError("target_ids must contain non-empty strings")
    if len(set(target_ids)) != len(target_ids):
        raise ValueError("target_ids cannot contain duplicates")
    return target_ids


def _package_dependencies(value: Any) -> tuple[dict[str, str], ...]:
    """Normalize named package dependencies into deterministic records."""
    if isinstance(value, Mapping):
        records = ({"name": name, "fingerprint": fingerprint} for name, fingerprint in value.items())
    else:
        records = value
    if isinstance(records, (str, bytes)) or not isinstance(records, Iterable):
        raise TypeError("dependencies must be a mapping or iterable of mappings")
    normalized = []
    for record in records:
        if not isinstance(record, Mapping):
            raise TypeError("dependency records must be mappings")
        name = record.get("name")
        fingerprint = record.get("fingerprint")
        if name not in _EVIDENCE_PACKAGE_DEPENDENCIES:
            raise ValueError(f"unsupported evidence package dependency: {name!r}")
        if not isinstance(fingerprint, str) or not fingerprint:
            raise ValueError(f"dependency {name!r} requires a non-empty fingerprint")
        normalized.append({"name": name, "fingerprint": fingerprint})
    normalized.sort(key=lambda item: item["name"])
    names = [item["name"] for item in normalized]
    missing = set(_EVIDENCE_PACKAGE_DEPENDENCIES) - set(names)
    if missing:
        raise ValueError(f"dependencies missing required names: {sorted(missing)}")
    if len(set(names)) != len(names):
        raise ValueError("dependencies cannot contain duplicate names")
    return tuple(normalized)


def _package_identity_payload(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Return the identity-bearing subset of a package contract."""
    return {
        "package_id": contract["package_id"],
        "package_schema": contract["package_schema"],
        "producer": contract["producer"],
        "target_ids": tuple(contract["target_ids"]),
        "dependencies": tuple(contract["dependencies"]),
        "algorithm_version": contract["algorithm_version"],
        "schema_version": contract["schema_version"],
        "invalidation_scope": contract["invalidation_scope"],
    }


def build_evidence_package_contract(
    *,
    package_id: str,
    package_schema: str,
    producer: str,
    target_ids: Iterable[str],
    dependencies: Mapping[str, str] | Iterable[Mapping[str, str]],
    algorithm_version: str,
    schema_version: str,
    artifacts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic package contract without reading or recomputing evidence."""
    for name, value in (
        ("package_id", package_id),
        ("package_schema", package_schema),
        ("producer", producer),
        ("algorithm_version", algorithm_version),
        ("schema_version", schema_version),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    normalized = {
        "schema": _EVIDENCE_PACKAGE_CONTRACT_SCHEMA,
        "package_id": package_id,
        "package_schema": package_schema,
        "producer": producer,
        "target_ids": list(_package_target_ids(target_ids)),
        "dependencies": list(_package_dependencies(dependencies)),
        "algorithm_version": algorithm_version,
        "schema_version": schema_version,
        "invalidation_scope": "whole_package",
        "artifacts": {},
    }
    artifact_mapping = {} if artifacts is None else artifacts
    if not isinstance(artifact_mapping, Mapping):
        raise TypeError("artifacts must be a JSON mapping")
    frozen_artifacts = _freeze(artifact_mapping)
    normalized["artifacts"] = _json_value(frozen_artifacts)
    identity_payload = _package_identity_payload(normalized)
    normalized["package_identity"] = hashlib.sha256(
        _canonical_json(identity_payload).encode()
    ).hexdigest()
    return normalized


def _validate_evidence_package_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a stored package contract for status comparison."""
    if not isinstance(contract, Mapping):
        raise TypeError("package contract must be a mapping")
    if contract.get("schema") != _EVIDENCE_PACKAGE_CONTRACT_SCHEMA:
        raise ValueError("unsupported evidence package contract schema")
    normalized = build_evidence_package_contract(
        package_id=contract.get("package_id"),
        package_schema=contract.get("package_schema"),
        producer=contract.get("producer"),
        target_ids=contract.get("target_ids", ()),
        dependencies=contract.get("dependencies", ()),
        algorithm_version=contract.get("algorithm_version"),
        schema_version=contract.get("schema_version"),
        artifacts=contract.get("artifacts", {}),
    )
    if contract.get("invalidation_scope") != "whole_package":
        raise ValueError("evidence package invalidation_scope must be whole_package")
    if contract.get("package_identity") != normalized["package_identity"]:
        raise ValueError("package_identity does not match contract contents")
    return normalized


def _best_effort_package_targets(contract: Any) -> tuple[str, ...]:
    """Read target ids for unavailable-status reporting without trusting the contract."""
    if not isinstance(contract, Mapping):
        return ()
    try:
        return _package_target_ids(contract.get("target_ids", ()))
    except (TypeError, ValueError):
        return ()


def evaluate_evidence_package_freshness(
    *,
    cached_contract: Mapping[str, Any] | None,
    current_contract: Mapping[str, Any] | None,
    artifacts_available: bool = True,
) -> dict[str, Any]:
    """Compare package identities and return a UI-facing, read-only status payload."""
    cached_targets = _best_effort_package_targets(cached_contract)
    current_targets = _best_effort_package_targets(current_contract)
    affected_targets = tuple(sorted(set(cached_targets) | set(current_targets)))
    reasons: list[dict[str, Any]] = []
    cached = current = None
    try:
        if cached_contract is not None:
            cached = _validate_evidence_package_contract(cached_contract)
        if current_contract is not None:
            current = _validate_evidence_package_contract(current_contract)
    except (TypeError, ValueError):
        package_id = (
            str(current_contract.get("package_id"))
            if isinstance(current_contract, Mapping) and current_contract.get("package_id")
            else str(cached_contract.get("package_id"))
            if isinstance(cached_contract, Mapping) and cached_contract.get("package_id")
            else ""
        )
        reasons.append({"code": "package_invalid", "dependency": None, "cached": None, "current": None})
        return {
            "schema": _EVIDENCE_PACKAGE_STATUS_SCHEMA,
            "package_id": package_id,
            "cached_package_identity": None,
            "current_package_identity": None,
            "freshness": "unavailable",
            "recompute_required": True,
            "reasons": reasons,
            "affected_targets": list(affected_targets),
            "invalidation_scope": "whole_package",
            "algorithm": {
                "status": "unknown",
                "cached_version": None,
                "current_version": None,
                "recompute_required": True,
            },
        }

    package_id = (
        current["package_id"]
        if current is not None
        else cached["package_id"]
        if cached is not None
        else ""
    )
    if cached is None:
        reasons.append({"code": "package_missing", "dependency": None, "cached": None, "current": current["package_identity"] if current else None})
    if current is None and cached is not None:
        reasons.append({"code": "package_invalid", "dependency": None, "cached": cached["package_identity"] if cached else None, "current": None})

    algorithm_status = "unknown"
    algorithm_recompute = True
    cached_algorithm = cached["algorithm_version"] if cached else None
    current_algorithm = current["algorithm_version"] if current else None
    if cached is not None and current is not None:
        if cached_algorithm == current_algorithm:
            algorithm_status = "same"
            algorithm_recompute = False
        else:
            algorithm_status = "changed"
            reasons.append({"code": "algorithm_version_changed", "dependency": "algorithm", "cached": cached_algorithm, "current": current_algorithm})

    if cached is not None and current is not None:
        cached_dependencies = {item["name"]: item["fingerprint"] for item in cached["dependencies"]}
        current_dependencies = {item["name"]: item["fingerprint"] for item in current["dependencies"]}
        for name in _EVIDENCE_PACKAGE_DEPENDENCIES:
            if cached_dependencies.get(name) != current_dependencies.get(name):
                reasons.append({
                    "code": _EVIDENCE_PACKAGE_REASON_CODES[name],
                    "dependency": name,
                    "cached": cached_dependencies.get(name),
                    "current": current_dependencies.get(name),
                })
        if cached["target_ids"] != current["target_ids"]:
            reasons.append({
                "code": "model_changed",
                "dependency": "target_ids",
                "cached": fingerprint_evidence_dependency(cached["target_ids"]),
                "current": fingerprint_evidence_dependency(current["target_ids"]),
            })
        if cached["package_id"] != current["package_id"] or cached["producer"] != current["producer"]:
            reasons.append({
                "code": "model_changed",
                "dependency": "package_definition",
                "cached": cached["package_id"] + "::" + cached["producer"],
                "current": current["package_id"] + "::" + current["producer"],
            })
        if cached["package_schema"] != current["package_schema"] or cached["schema_version"] != current["schema_version"]:
            reasons.append({
                "code": "schema_changed",
                "dependency": "schema",
                "cached": cached["package_schema"] + "::" + cached["schema_version"],
                "current": current["package_schema"] + "::" + current["schema_version"],
            })

    if not artifacts_available:
        reasons.append({"code": "package_invalid", "dependency": "artifacts", "cached": None, "current": None})

    freshness = (
        "unavailable"
        if not artifacts_available or cached is None or current is None
        else "fresh"
        if not reasons
        else "stale"
    )
    return {
        "schema": _EVIDENCE_PACKAGE_STATUS_SCHEMA,
        "package_id": package_id,
        "cached_package_identity": cached["package_identity"] if cached else None,
        "current_package_identity": current["package_identity"] if current else None,
        "freshness": freshness,
        "recompute_required": bool(reasons),
        "reasons": reasons,
        "affected_targets": list(affected_targets if reasons else ()),
        "invalidation_scope": "whole_package",
        "algorithm": {
            "status": algorithm_status,
            "cached_version": cached_algorithm,
            "current_version": current_algorithm,
            "recompute_required": algorithm_recompute if algorithm_status != "same" else False,
        },
    }


def project_field_sample(result: FieldResultEnvelope) -> FieldSample[Any] | None:
    """Project only semantically complete envelopes into the legacy sample contract."""
    if not isinstance(result, FieldResultEnvelope) or result.field_projection is None or result.value is None:
        return None
    if result.raw_status is not FieldResultStatus.COMPUTED:
        return None
    projection = result.field_projection
    try:
        status = FieldStatus(projection["status"])
        provenance = dict(result.provenance)
        provenance.update({"raw_status": result.raw_status.value, "mapping_reason": projection["mapping_reason"]})
        return FieldSample(value=result.value, status=status, query=result.query, support=result.support, source_ids=result.source_ids, provenance=provenance, explanation=projection["mapping_reason"])
    except (TypeError, ValueError):
        return None


class Field(Generic[Target, Value], ABC):
    """Generic exact-lookup field contract for spatial or relation targets."""

    def __init__(
        self,
        *,
        domain: Any = None,
        frame: Any = None,
        value_schema: Any = None,
        representation: Any = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> None:
        """Store immutable field declaration metadata."""
        self.domain = _freeze(domain)
        self.frame = _freeze(frame)
        self.value_schema = _freeze(value_schema)
        self.representation = _freeze(representation)
        # Let __setattr__ distinguish trusted private overlays from ordinary
        # mappings, freezing the latter while preserving validated shared data.
        self.provenance = provenance or {}

    def __setattr__(self, name: str, value: Any) -> None:
        """Keep declared metadata immutable after its first assignment."""
        if name in {"domain", "frame", "value_schema", "representation", "provenance"} and hasattr(
            self, name
        ):
            raise AttributeError(f"{name} is immutable")
        if name in {"domain", "frame", "value_schema", "representation", "provenance"}:
            value = value.mapping if type(value) is _MetadataOverlay else _freeze(value)
        object.__setattr__(self, name, value)

    @abstractmethod
    def evaluate(self, target: Target, query: FieldQuery) -> FieldSample[Value]:
        """Evaluate one exact target under the supplied immutable query."""
        raise NotImplementedError

    def evaluate_many(
        self, targets: Iterable[Target], query: FieldQuery
    ) -> tuple[FieldSample[Value], ...]:
        """Evaluate targets in input order, preserving duplicates and cardinality."""
        # Exact repeated lookup is the least surprising default for relation fields.
        return tuple(self.evaluate(target, query) for target in targets)
