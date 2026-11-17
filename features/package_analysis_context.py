"""Frozen plane selections for package calls, independent of numerical inputs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .scene_contract import AnalysisPlane


@dataclass(frozen=True, slots=True)
class PackageAnalysisContext:
    """Carry at least one selected plane without projecting or extracting data."""

    planes: tuple[AnalysisPlane, ...]

    def __post_init__(self) -> None:
        """Detach the selection and reject empty, invalid or duplicate identities."""
        planes = tuple(self.planes)
        if not planes or any(not isinstance(plane, AnalysisPlane) for plane in planes):
            raise ValueError("planes must contain at least one AnalysisPlane")
        if len({plane.identity for plane in planes}) != len(planes):
            raise ValueError("planes cannot contain duplicate identities")
        object.__setattr__(self, "planes", planes)

    @property
    def primary_plane(self) -> AnalysisPlane:
        """Return the first explicitly ordered plane in this call."""
        return self.planes[0]


@dataclass(frozen=True, slots=True)
class AnalysisPlaneCatalog:
    """Resolve a scene default or one package override from frozen plane facts."""

    planes: tuple[AnalysisPlane, ...]
    default_plane_identity: str

    def __post_init__(self) -> None:
        """Require an unambiguous catalog with an existing explicit default."""
        context = PackageAnalysisContext(self.planes)
        object.__setattr__(self, "planes", context.planes)
        if not isinstance(self.default_plane_identity, str) or not self.default_plane_identity.strip():
            raise ValueError("default_plane_identity must be a nonempty string")
        if self.default_plane_identity not in {plane.identity for plane in self.planes}:
            raise ValueError("default plane is absent from the catalog")

    def resolve(self, *, package_plane_identity: str | None = None) -> PackageAnalysisContext:
        """Freeze one inherited or explicitly selected plane and reject dangling overrides."""
        selected = self.default_plane_identity if package_plane_identity is None else package_plane_identity
        if not isinstance(selected, str) or not selected.strip():
            raise ValueError("package_plane_identity must be a nonempty string or None")
        for plane in self.planes:
            if plane.identity == selected:
                return PackageAnalysisContext((plane,))
        raise ValueError("selected plane is absent from the catalog")


def _query_plane(value: object) -> AnalysisPlane:
    """Read only complete typed plane facts, including the existing query extensions."""
    if isinstance(value, AnalysisPlane):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("query plane must contain complete AnalysisPlane facts")
    plane_fields = {"name", "origin", "basis", "identity", "revision"}
    if not plane_fields <= set(value):
        raise ValueError("query plane must contain complete AnalysisPlane facts")
    if not isinstance(value["identity"], str) or not value["identity"].strip():
        raise ValueError("query plane must contain an explicit identity")
    if set(value) - plane_fields - {"normal", "units"}:
        raise ValueError("query plane contains unsupported fields")
    plane = AnalysisPlane.from_dict({key: item for key, item in value.items() if key in plane_fields})
    if "normal" in value:
        normal = value["normal"]
        if (not isinstance(normal, (list, tuple))
                or any(isinstance(component, bool) or not isinstance(component, (int, float))
                       for component in normal)
                or tuple(normal) != plane.basis[2]):
            raise ValueError("query plane normal differs from its basis")
    if "units" in value and value["units"] != "m":
        raise ValueError("query plane requires metre units")
    return plane


def resolve_package_analysis_context(
    source_envelopes: Iterable[object] = (), *,
    analysis_context: PackageAnalysisContext | None = None,
    supports_multiple_planes: bool = False,
    allow_multiple_planes: bool = False,
) -> PackageAnalysisContext:
    """Require call context, deriving only a unique complete historical query plane."""
    if type(supports_multiple_planes) is not bool or type(allow_multiple_planes) is not bool:
        raise TypeError("multiple-plane capability and permission must be boolean")
    if analysis_context is None:
        unique = {}
        for source in source_envelopes:
            value = getattr(getattr(source, "query", None), "plane", None)
            if value is None:
                continue
            plane = _query_plane(value)
            # Names are display metadata; identity, revision and pose retain the actual frame.
            key = (plane.identity, plane.revision, plane.origin, plane.basis)
            unique.setdefault(key, plane)
        if len(unique) != 1:
            raise ValueError("analysis_context is required unless source queries identify one complete plane")
        analysis_context = PackageAnalysisContext(tuple(unique.values()))
    elif not isinstance(analysis_context, PackageAnalysisContext):
        raise TypeError("analysis_context must be a PackageAnalysisContext")
    if len(analysis_context.planes) > 1 and not (supports_multiple_planes and allow_multiple_planes):
        raise ValueError("multiple planes require package capability and explicit call permission")
    # Selection is not a claim of numerical use; package-specific input guards own that dependency.
    return analysis_context


__all__ = [
    "AnalysisPlaneCatalog",
    "PackageAnalysisContext",
    "resolve_package_analysis_context",
]
