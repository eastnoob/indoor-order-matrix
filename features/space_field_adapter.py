"""Read-only typed views over validated B3 discrete-field deliveries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .field_core import Field, FieldQuery, FieldSample, FieldStatus


class _FrozenList(list):
    """List-compatible immutable container preserving loader equality."""

    def _blocked(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("adapter metadata is immutable")

    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = reverse = sort = _blocked


class _FrozenDict(dict):
    """Dict-compatible immutable container preserving loader equality."""

    def _blocked(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("adapter metadata is immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked


def _freeze_delivery(value: Any) -> Any:
    """Deep-freeze copied delivery data while retaining JSON container equality."""
    if isinstance(value, Mapping):
        return _FrozenDict({key: _freeze_delivery(item) for key, item in value.items()})
    if isinstance(value, list):
        return _FrozenList(_freeze_delivery(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_delivery(item) for item in value)
    return value


class B3AdapterView(Field[int, bool]):
    """Expose one validated B3 lattice as an exact, conditional Field."""

    def __init__(self, delivery: Mapping[str, Any]) -> None:
        """Freeze loader output and retain the package's audit metadata."""
        if not isinstance(delivery, Mapping):
            raise TypeError("delivery must be a mapping")
        required = ("field", "variant", "source_sections", "artifact_manifest")
        if any(key not in delivery for key in required):
            raise ValueError("delivery is missing a required B3 payload")
        field = _freeze_delivery(delivery["field"])
        variant = _freeze_delivery(delivery["variant"])
        source_sections = _freeze_delivery(delivery["source_sections"])
        artifact_manifest = _freeze_delivery(delivery["artifact_manifest"])
        if not isinstance(field, Mapping) or not isinstance(variant, Mapping):
            raise TypeError("B3 field and variant must be mappings")
        raw_provenance = {
            "algorithm_version": str(field["algorithm"]["identity"]),
            "schema_version": str(field["schema"]),
            "schema": str(field["schema"]),
            "raw_status": str(field.get("status", "")),
            "units": str(field.get("units", "")),
            "primary_plane_world_z_m": field.get("primary_plane_world_z_m"),
        }
        super().__init__(
            domain=field.get("domain_geometry"),
            frame=field.get("frame"),
            value_schema="conditional_occupancy",
            representation="discrete_lattice",
            provenance=raw_provenance,
        )
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "variant", variant)
        object.__setattr__(self, "source_sections", source_sections)
        object.__setattr__(self, "artifact_manifest", artifact_manifest)
        object.__setattr__(self, "units", field.get("units"))
        object.__setattr__(self, "primary_plane_world_z_m", field.get("primary_plane_world_z_m"))
        object.__setattr__(self, "complete_occupancy_geometry", field.get("complete_occupancy_geometry"))
        object.__setattr__(self, "complete_physical_clearance_m", None)

    @classmethod
    def from_loaded(cls, delivery: Mapping[str, Any]) -> "B3AdapterView":
        """Build a typed view from the unchanged loader return value."""
        return cls(delivery)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent mutation of adapter payload and declared metadata."""
        if hasattr(self, name):
            raise AttributeError(f"{name} is immutable")
        super().__setattr__(name, value)

    def evaluate(self, target: int, query: FieldQuery) -> FieldSample[bool]:
        """Return one exact lattice sample with B3 status preserved in provenance."""
        if not isinstance(target, int) or isinstance(target, bool):
            return FieldSample(
                value=None,
                status=FieldStatus.INVALID,
                query=query,
                provenance=self._sample_provenance("invalid"),
                explanation="sample index must be an integer",
            )
        samples = self.variant.get("samples")
        if not isinstance(samples, (tuple, list)) or target < 0 or target >= len(samples):
            return FieldSample(
                value=None,
                status=FieldStatus.OUTSIDE,
                query=query,
                provenance=self._sample_provenance("outside_domain"),
                explanation="sample index is outside the selected lattice",
            )
        raw = samples[target]
        raw_status = raw["status"]
        status, value = {
            "established_occupied": (FieldStatus.CONDITIONAL, True),
            "established_empty_under_qualification": (FieldStatus.CONDITIONAL, False),
            "unknown": (FieldStatus.UNKNOWN, None),
            "outside_domain": (FieldStatus.OUTSIDE, None),
        }.get(raw_status, (FieldStatus.INVALID, None))
        explanation = (
            "conditional B3 section observation at the declared primary plane"
            if status is FieldStatus.CONDITIONAL
            else f"B3 sample status is {raw_status}"
        )
        return FieldSample(
            value=value,
            status=status,
            query=query,
            support={
                "raw_sample": raw,
                "units": self.units,
                "frame": self.frame,
            },
            source_ids=tuple(raw.get("unresolved_source_ids", ())),
            provenance=self._sample_provenance(raw_status),
            explanation=explanation,
        )

    def _sample_provenance(self, raw_status: str) -> dict[str, Any]:
        """Return versioned provenance while retaining the raw B3 status."""
        return {
            "algorithm_version": self.provenance["algorithm_version"],
            "schema_version": self.provenance["schema_version"],
            "raw_status": raw_status,
            "units": self.units,
            "plane": self.field["frame"]["plane"],
        }
