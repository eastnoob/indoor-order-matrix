"""Immutable core contracts for exact, auditable field lookups."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import hashlib
import json
from math import isfinite
from types import MappingProxyType
from typing import Any, Generic, TypeVar


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
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if is_dataclass(value) and getattr(value, "__dataclass_params__", None) is not None:
        # Frozen contract records already recursively freeze their own payloads.
        return value
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


def _json_value(value: Any) -> Any:
    """Convert frozen JSON-safe values into deterministic JSON structures."""
    if isinstance(value, Enum):
        return value.value
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
        provenance = _freeze(self.provenance)
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
        if self.value is not None:
            if not isinstance(self.value, Mapping) or "channels" not in self.value:
                raise TypeError("value must be a mapping containing channels")
            records = tuple(self.value["channels"])
            if any(not isinstance(record, EvidenceChannelRecord) for record in records):
                raise TypeError("value.channels must contain EvidenceChannelRecord values")
            names = [record.channel for record in records]
            if len(set(names)) != len(names):
                raise ValueError("channel records cannot contain duplicate channels")
            if any(record.channel not in channels for record in records):
                raise ValueError("channel record is outside channel_set")
            if set(names) != set(channels):
                raise ValueError("value.channels must represent every admitted channel")
            records = tuple(sorted(records, key=lambda record: record.channel))
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
        self.provenance = _freeze(provenance or {})

    def __setattr__(self, name: str, value: Any) -> None:
        """Keep declared metadata immutable after its first assignment."""
        if name in {"domain", "frame", "value_schema", "representation", "provenance"} and hasattr(
            self, name
        ):
            raise AttributeError(f"{name} is immutable")
        if name in {"domain", "frame", "value_schema", "representation", "provenance"}:
            value = _freeze(value)
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
