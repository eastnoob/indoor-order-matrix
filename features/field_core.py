"""Immutable core contracts for exact, auditable field lookups."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
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


def _freeze(value: Any) -> Any:
    """Return a JSON-safe immutable representation of a nested value."""
    if value is None or isinstance(value, (str, bool, int)):
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
