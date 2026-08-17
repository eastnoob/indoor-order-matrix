"""Source-independent functional substitutes for geometry analysis."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from types import MappingProxyType
from typing import Iterable

from .scene_contract import AuthoredAffordanceZone, MeshGeometry3D, SurfaceFact


def _json_tuple(values: Iterable[object]) -> tuple[object, ...]:
    """Freeze an iterable so substitute records remain deterministic."""
    return tuple(values)


def _json_value(value: object) -> object:
    """Convert frozen mappings and nested tuples into JSON-compatible values."""
    if isinstance(value, Mapping):
        return {str(key): _json_value(nested) for key, nested in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def _freeze_value(value: object) -> object:
    """Freeze nested factual mappings so substitute records remain stable."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(nested) for key, nested in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_value(item) for item in value)
    return value


@dataclass(frozen=True)
class MassPatch:
    """A physical connected geometry component used for spatial queries."""

    id: str
    source_geometry_id: str
    vertices: tuple[tuple[float, float, float], ...]
    triangle_indices: tuple[tuple[int, int, int], ...]
    is_manifold: bool | None
    is_closed: bool | None
    provenance: Mapping[str, object]

    def __post_init__(self) -> None:
        """Freeze provenance after the factual mesh copy is constructed."""
        object.__setattr__(self, "provenance", _freeze_value(self.provenance))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable description record."""
        return {
            "id": self.id,
            "source_geometry_id": self.source_geometry_id,
            "vertices": self.vertices,
            "triangle_indices": self.triangle_indices,
            "is_manifold": self.is_manifold,
            "is_closed": self.is_closed,
            "provenance": _json_value(self.provenance),
        }


@dataclass(frozen=True)
class SurfacePatch:
    """A coherent surface region kept separate from physical mass."""

    id: str
    source_surface_id: str
    geometry_refs: tuple[str, ...]
    color: object
    elevation: object
    provenance: Mapping[str, object]
    mass_geometry_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze source provenance without changing surface observations."""
        object.__setattr__(self, "provenance", _freeze_value(self.provenance))
        object.__setattr__(self, "color", _freeze_value(self.color))
        object.__setattr__(self, "elevation", _freeze_value(self.elevation))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable surface description."""
        return {
            "id": self.id,
            "source_surface_id": self.source_surface_id,
            "geometry_refs": self.geometry_refs,
            "mass_geometry_refs": self.mass_geometry_refs,
            "color": _json_value(self.color),
            "elevation": _json_value(self.elevation),
            "provenance": _json_value(self.provenance),
        }


@dataclass(frozen=True)
class AffordanceZone:
    """An explicitly authored functional volume for a source object."""

    id: str
    source_zone_id: str
    geometry_refs: tuple[str, ...]
    vertical_extent: tuple[float, float]
    purpose: str
    source_furniture_refs: tuple[str, ...]
    provenance: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        """Freeze authored provenance while retaining the explicit zone facts."""
        object.__setattr__(self, "provenance", _freeze_value(self.provenance or {}))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable affordance description."""
        return {
            "id": self.id,
            "source_zone_id": self.source_zone_id,
            "geometry_refs": self.geometry_refs,
            "vertical_extent": self.vertical_extent,
            "purpose": self.purpose,
            "source_furniture_refs": self.source_furniture_refs,
            "provenance": _json_value(self.provenance or {}),
        }


def mass_patch_from_mesh(mesh: MeshGeometry3D) -> MassPatch:
    """Create one transport substitute without inspecting source semantics."""
    # The substitute copies factual mesh data; no object class or source name is
    # consulted, so the same operation works for furniture, walls, or terrain.
    return MassPatch(
        id=f"mass-patch:{mesh.id}",
        source_geometry_id=mesh.id,
        vertices=tuple(mesh.vertices),
        triangle_indices=tuple(mesh.triangle_indices),
        is_manifold=mesh.is_manifold,
        is_closed=mesh.is_closed,
        provenance={
            "method": "mesh_geometry_transport",
            "source_representation_id": mesh.source_representation_id,
            "units": mesh.units,
        },
    )


def surface_patch_from_fact(fact: SurfaceFact) -> SurfacePatch:
    """Create a surface substitute without turning appearance into physical mass."""
    return SurfacePatch(
        id=f"surface-patch:{fact.id}",
        source_surface_id=fact.id,
        geometry_refs=tuple(fact.geometry_refs),
        color=fact.color,
        elevation=fact.elevation,
        provenance={"method": "surface_fact_transport", "source_id": fact.source_id},
    )


def affordance_zone_from_record(zone: AuthoredAffordanceZone) -> AffordanceZone:
    """Convert an authored contract zone into an analysis substitute."""
    return AffordanceZone(
        id=f"affordance-zone:{zone.id}",
        source_zone_id=zone.id,
        geometry_refs=tuple(zone.geometry_refs),
        vertical_extent=tuple(zone.vertical_extent),
        purpose=zone.purpose,
        source_furniture_refs=tuple(zone.source_furniture_refs),
        provenance={"method": "authored_affordance_transport", **dict(zone.provenance)},
    )
