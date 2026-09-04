"""Conservative source-independent generation of MassPatch candidates."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .geometry_substitutes import MassPatch, mass_patch_from_mesh
from .scene_contract import MeshGeometry3D


def _finite_positive(value: float, name: str) -> float:
    """Validate one finite positive geometry setting."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be finite and positive")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


@dataclass(frozen=True)
class MassPatchGenerationConfig:
    """Geometry tolerances used to accept or reject substitute candidates."""

    linear_tolerance: float = 1e-6
    sample_spacing: float | None = None
    minimum_plan_recall: float = 0.98
    maximum_plan_overreach: float = 0.02
    maximum_vertical_endpoint_error: float | None = None
    maximum_occlusion_disagreement: float = 0.02

    def __post_init__(self) -> None:
        """Validate geometry tolerances without introducing perceptual weights."""
        linear_tolerance = _finite_positive(self.linear_tolerance, "linear_tolerance")
        object.__setattr__(self, "linear_tolerance", linear_tolerance)
        spacing = (
            4.0 * linear_tolerance
            if self.sample_spacing is None
            else _finite_positive(self.sample_spacing, "sample_spacing")
        )
        object.__setattr__(self, "sample_spacing", spacing)
        for name in (
            "minimum_plan_recall",
            "maximum_plan_overreach",
            "maximum_occlusion_disagreement",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
            object.__setattr__(self, name, value)
        endpoint_error = (
            2.0 * linear_tolerance
            if self.maximum_vertical_endpoint_error is None
            else _finite_positive(
                self.maximum_vertical_endpoint_error,
                "maximum_vertical_endpoint_error",
            )
        )
        object.__setattr__(self, "maximum_vertical_endpoint_error", endpoint_error)


@dataclass(frozen=True)
class MassPatchCandidateReport:
    """Measured geometry evidence for one candidate substitute."""

    candidate_method: str
    accepted: bool
    plan_recall: float
    plan_overreach: float
    vertical_endpoint_error: float
    gap_preservation_error: float
    occlusion_disagreement: float
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible candidate report."""
        return {
            "candidate_method": self.candidate_method,
            "accepted": self.accepted,
            "plan_recall": self.plan_recall,
            "plan_overreach": self.plan_overreach,
            "vertical_endpoint_error": self.vertical_endpoint_error,
            "gap_preservation_error": self.gap_preservation_error,
            "occlusion_disagreement": self.occlusion_disagreement,
            "rejection_reason": self.rejection_reason,
        }


@dataclass(frozen=True)
class MassPatchComponentReport:
    """Candidate decisions and evidence for one source mesh component."""

    component_index: int
    candidate_methods: tuple[str, ...]
    selected_candidate: str
    candidate_reports: tuple[MassPatchCandidateReport, ...]
    rejections: Mapping[str, str]
    gap_preservation_error: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible component report."""
        return {
            "component_index": self.component_index,
            "candidate_methods": self.candidate_methods,
            "selected_candidate": self.selected_candidate,
            "candidate_reports": tuple(
                report.to_dict() for report in self.candidate_reports
            ),
            "rejections": dict(self.rejections),
            "gap_preservation_error": self.gap_preservation_error,
        }


@dataclass(frozen=True)
class MassPatchGenerationResult:
    """Generated substitutes and auditable source-comparison reports."""

    source_mesh_id: str
    patches: tuple[MassPatch, ...]
    component_reports: tuple[MassPatchComponentReport, ...]
    method_version: str = "mass-patch-generation-v1"

    def to_dict(self) -> dict[str, object]:
        """Return the complete generation result as JSON-compatible data."""
        return {
            "source_mesh_id": self.source_mesh_id,
            "patches": tuple(patch.to_dict() for patch in self.patches),
            "component_reports": tuple(
                report.to_dict() for report in self.component_reports
            ),
            "method_version": self.method_version,
        }


def _has_non_degenerate_triangle(mesh: MeshGeometry3D) -> bool:
    """Return whether at least one source triangle has measurable area."""
    for first, second, third in mesh.triangle_indices:
        a = mesh.vertices[first]
        b = mesh.vertices[second]
        c = mesh.vertices[third]
        ab = tuple(b[index] - a[index] for index in range(3))
        ac = tuple(c[index] - a[index] for index in range(3))
        cross = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        if sum(component * component for component in cross) > 0.0:
            return True
    return False


def _validate_source_mesh(mesh: MeshGeometry3D) -> None:
    """Reject source geometry that cannot support any spatial query."""
    if not isinstance(mesh, MeshGeometry3D):
        raise TypeError("mesh must be a MeshGeometry3D")
    if not mesh.triangle_indices:
        raise ValueError("mesh must contain at least one triangle")
    if not _has_non_degenerate_triangle(mesh):
        raise ValueError("mesh must contain at least one non-degenerate triangle")


def generate_mass_patches(
    mesh: MeshGeometry3D,
    config: MassPatchGenerationConfig | None = None,
) -> MassPatchGenerationResult:
    """Generate the exact validated baseline for one source mesh."""
    _validate_source_mesh(mesh)
    config = config or MassPatchGenerationConfig()
    # The exact source copy is the mandatory baseline before any simplification
    # candidate is allowed to replace it.
    patch = mass_patch_from_mesh(mesh)
    exact_report = MassPatchCandidateReport(
        candidate_method="exact_component",
        accepted=True,
        plan_recall=1.0,
        plan_overreach=0.0,
        vertical_endpoint_error=0.0,
        gap_preservation_error=0.0,
        occlusion_disagreement=0.0,
    )
    component_report = MassPatchComponentReport(
        component_index=0,
        candidate_methods=("exact_component",),
        selected_candidate="exact_component",
        candidate_reports=(exact_report,),
        rejections={},
        gap_preservation_error=0.0,
    )
    del config
    return MassPatchGenerationResult(
        source_mesh_id=mesh.id,
        patches=(patch,),
        component_reports=(component_report,),
    )


__all__ = [
    "MassPatchCandidateReport",
    "MassPatchComponentReport",
    "MassPatchGenerationConfig",
    "MassPatchGenerationResult",
    "generate_mass_patches",
]
