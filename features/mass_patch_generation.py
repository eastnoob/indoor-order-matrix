"""Conservative source-independent generation of MassPatch candidates."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .geometry_substitutes import MassPatch, mass_patch_from_mesh
from .geometry_views import occlusion_intersections, vertical_intervals_at
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
        if self.sample_spacing is not None:
            object.__setattr__(
                self,
                "sample_spacing",
                _finite_positive(self.sample_spacing, "sample_spacing"),
            )
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
    plan_recall: float | None
    plan_overreach: float | None
    vertical_endpoint_error: float | None
    gap_preservation_error: float | None
    occlusion_disagreement: float | None
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
    uncertainties: tuple[str, ...] = ()

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
            "uncertainties": self.uncertainties,
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


def _non_degenerate_triangles(mesh: MeshGeometry3D) -> tuple[tuple[int, int, int], ...]:
    """Return source faces that contribute measurable geometric area."""
    triangles = []
    for triangle in mesh.triangle_indices:
        first, second, third = triangle
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
            triangles.append(triangle)
    return tuple(triangles)


def _validate_source_mesh(mesh: MeshGeometry3D) -> None:
    """Reject source geometry that cannot support any spatial query."""
    if not isinstance(mesh, MeshGeometry3D):
        raise TypeError("mesh must be a MeshGeometry3D")
    if not mesh.triangle_indices:
        raise ValueError("mesh must contain at least one triangle")
    if not _has_non_degenerate_triangle(mesh):
        raise ValueError("mesh must contain at least one non-degenerate triangle")


def _component_meshes(mesh: MeshGeometry3D) -> tuple[MeshGeometry3D, ...]:
    """Split one source mesh into deterministic factual connectivity components."""
    import numpy as np
    import trimesh

    source = trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices, dtype=float),
        # Degenerate faces cannot contribute occupancy but can break the
        # library's face-adjacency graph, so remove them before splitting.
        faces=np.asarray(_non_degenerate_triangles(mesh), dtype=int),
        process=False,
    )
    components = list(source.split(only_watertight=False))
    # Geometry-based ordering makes the result independent of hash order or
    # incidental face traversal order in the source adapter.
    components.sort(
        key=lambda component: (
            tuple(float(value) for value in component.bounds[0]),
            tuple(float(value) for value in component.bounds[1]),
            len(component.vertices),
            len(component.faces),
        )
    )
    records = []
    for index, component in enumerate(components):
        records.append(
            MeshGeometry3D(
                id=f"{mesh.id}:component:{index}",
                vertices=tuple(
                    tuple(float(value) for value in vertex)
                    for vertex in component.vertices
                ),
                triangle_indices=tuple(
                    tuple(int(value) for value in triangle)
                    for triangle in component.faces
                ),
                normals=(),
                is_manifold=mesh.is_manifold,
                is_closed=mesh.is_closed,
                local_to_world_provenance=mesh.local_to_world_provenance,
                source_representation_id=mesh.source_representation_id,
                tessellation_settings=mesh.tessellation_settings,
                units=mesh.units,
            )
        )
    return tuple(records)


def _exact_component_report() -> MassPatchCandidateReport:
    """Build the zero-error report for the mandatory exact baseline."""
    return MassPatchCandidateReport(
        candidate_method="exact_component",
        accepted=True,
        plan_recall=1.0,
        plan_overreach=0.0,
        vertical_endpoint_error=0.0,
        gap_preservation_error=0.0,
        occlusion_disagreement=0.0,
    )


def _annotate_generated_patch(
    patch: MassPatch,
    *,
    source_mesh_id: str,
    component_index: int,
    candidate_method: str,
) -> MassPatch:
    """Attach generation provenance without changing candidate geometry."""
    return MassPatch(
        id=patch.id,
        source_geometry_id=patch.source_geometry_id,
        vertices=patch.vertices,
        triangle_indices=patch.triangle_indices,
        is_manifold=patch.is_manifold,
        is_closed=patch.is_closed,
        provenance={
            **dict(patch.provenance),
            "source_mesh_id": source_mesh_id,
            "source_component_index": component_index,
            "candidate_method": candidate_method,
        },
    )


def _validation_config_dict(
    config: MassPatchGenerationConfig,
) -> dict[str, object]:
    """Serialize the effective geometry tolerances used for one decision."""
    return {
        "linear_tolerance": config.linear_tolerance,
        "sample_spacing": config.sample_spacing,
        "minimum_plan_recall": config.minimum_plan_recall,
        "maximum_plan_overreach": config.maximum_plan_overreach,
        "maximum_vertical_endpoint_error": config.maximum_vertical_endpoint_error,
        "maximum_occlusion_disagreement": config.maximum_occlusion_disagreement,
    }


def _attach_validation_provenance(
    patch: MassPatch,
    config: MassPatchGenerationConfig,
    report: MassPatchCandidateReport,
) -> MassPatch:
    """Record the exact validation inputs and result on the selected patch."""
    return MassPatch(
        id=patch.id,
        source_geometry_id=patch.source_geometry_id,
        vertices=patch.vertices,
        triangle_indices=patch.triangle_indices,
        is_manifold=patch.is_manifold,
        is_closed=patch.is_closed,
        provenance={
            **dict(patch.provenance),
            "validation_config": _validation_config_dict(config),
            "validation_result": report.to_dict(),
        },
    )


def _oriented_box_candidate(component: MeshGeometry3D) -> MassPatch | None:
    """Build an OBB candidate for one non-degenerate mesh component."""
    import numpy as np
    import trimesh

    source = trimesh.Trimesh(
        vertices=np.asarray(component.vertices, dtype=float),
        faces=np.asarray(component.triangle_indices, dtype=int),
        process=False,
    )
    if source.is_empty or any(float(extent) <= 0.0 for extent in source.extents):
        return None
    oriented = source.bounding_box_oriented
    return MassPatch(
        id=f"{component.id}:candidate:oriented-bounding-box",
        source_geometry_id=component.id,
        vertices=tuple(
            tuple(float(value) for value in vertex)
            for vertex in oriented.vertices
        ),
        triangle_indices=tuple(
            tuple(int(value) for value in triangle)
            for triangle in oriented.faces
        ),
        is_manifold=True,
        is_closed=True,
        provenance={
            "method": "oriented_bounding_box",
            "source_geometry_id": component.id,
            "units": component.units,
        },
    )


def _unvalidated_candidate_report(method: str) -> MassPatchCandidateReport:
    """Describe a candidate that has not reached source comparison yet."""
    return MassPatchCandidateReport(
        candidate_method=method,
        accepted=False,
        plan_recall=None,
        plan_overreach=None,
        vertical_endpoint_error=None,
        gap_preservation_error=None,
        occlusion_disagreement=None,
        rejection_reason="awaiting_validation",
    )


def _plan_sample_points(
    source: MassPatch,
    candidate: MassPatch,
    config: MassPatchGenerationConfig,
) -> tuple[tuple[float, float], ...]:
    """Build bounded deterministic plan samples for source comparison."""
    points = [
        (float(vertex[0]), float(vertex[1]))
        for patch in (source, candidate)
        for vertex in patch.vertices
    ]
    minimum_x = min(point[0] for point in points)
    maximum_x = max(point[0] for point in points)
    minimum_y = min(point[1] for point in points)
    maximum_y = max(point[1] for point in points)
    span = max(maximum_x - minimum_x, maximum_y - minimum_y)
    spacing = config.sample_spacing or max(4.0 * config.linear_tolerance, span / 32.0)
    grid_points = []
    x = minimum_x + spacing / 2.0
    while x < maximum_x:
        y = minimum_y + spacing / 2.0
        while y < maximum_y:
            grid_points.append((x, y))
            y += spacing
        x += spacing
    # Vertices are added explicitly so narrow edges are not represented only
    # by a coarse grid cell.
    points.extend(grid_points)
    return tuple(sorted(set(points)))


def _occupied_intervals(
    patch: MassPatch,
    point: tuple[float, float],
) -> tuple[tuple[float, float], ...]:
    """Return occupied height intervals for one plan sample."""
    return vertical_intervals_at(patch, point).intervals


def _vertical_endpoint_error(
    source_intervals: tuple[tuple[float, float], ...],
    candidate_intervals: tuple[tuple[float, float], ...],
    *,
    fallback_span: float,
) -> float:
    """Measure the largest height mismatch at one plan sample."""
    if not source_intervals and not candidate_intervals:
        return 0.0
    if len(source_intervals) != len(candidate_intervals):
        return fallback_span
    if not source_intervals:
        return fallback_span
    return max(
        max(
            abs(source_interval[0] - candidate_interval[0]),
            abs(source_interval[1] - candidate_interval[1]),
        )
        for source_interval, candidate_interval in zip(
            source_intervals,
            candidate_intervals,
        )
    )


def _occlusion_samples(
    source: MassPatch,
    candidate: MassPatch,
    config: MassPatchGenerationConfig,
) -> tuple[dict[str, object], ...]:
    """Build bounded horizontal ray queries for occlusion comparison."""
    vertices = source.vertices + candidate.vertices
    minimum_x = min(vertex[0] for vertex in vertices)
    maximum_x = max(vertex[0] for vertex in vertices)
    minimum_y = min(vertex[1] for vertex in vertices)
    maximum_y = max(vertex[1] for vertex in vertices)
    minimum_z = min(vertex[2] for vertex in vertices)
    maximum_z = max(vertex[2] for vertex in vertices)
    margin = max(config.linear_tolerance * 4.0, 1e-6)
    def interior_triplet(lower: float, upper: float) -> tuple[float, float, float]:
        """Return boundary-safe low, middle, and high sample coordinates."""
        inset = min((upper - lower) / 4.0, margin)
        return (
            lower + inset,
            (lower + upper) / 2.0,
            upper - inset,
        )

    # Interior samples avoid tangent hits at a component's exact boundary;
    # tangent classification is not stable enough for comparing two meshes.
    y_values = interior_triplet(minimum_y, maximum_y)
    z_values = interior_triplet(minimum_z, maximum_z)
    queries = []
    for y in y_values:
        for z in z_values:
            queries.append(
                {
                    "origin": (minimum_x - margin, y, z),
                    "direction": (1.0, 0.0, 0.0),
                    "height_band": (
                        z - config.linear_tolerance,
                        z + config.linear_tolerance,
                    ),
                }
            )
    for x in interior_triplet(minimum_x, maximum_x):
        for z in z_values:
            queries.append(
                {
                    "origin": (x, minimum_y - margin, z),
                    "direction": (0.0, 1.0, 0.0),
                    "height_band": (
                        z - config.linear_tolerance,
                        z + config.linear_tolerance,
                    ),
                }
            )
    return tuple(queries)


def validate_mass_patch_candidate(
    source: MeshGeometry3D | MassPatch,
    candidate: MassPatch,
    config: MassPatchGenerationConfig,
) -> MassPatchCandidateReport:
    """Compare one candidate against source geometry using hard tolerances."""
    source_patch = (
        mass_patch_from_mesh(source)
        if isinstance(source, MeshGeometry3D)
        else source
    )
    if source_patch.is_closed is not True or source_patch.is_manifold is not True:
        return MassPatchCandidateReport(
            candidate_method=str(
                candidate.provenance.get("method", "candidate")
            ),
            accepted=False,
            plan_recall=None,
            plan_overreach=None,
            vertical_endpoint_error=None,
            gap_preservation_error=None,
            occlusion_disagreement=None,
            rejection_reason="source_topology_uncertain",
        )
    samples = _plan_sample_points(source_patch, candidate, config)
    source_states = tuple(
        _occupied_intervals(source_patch, point) for point in samples
    )
    candidate_states = tuple(
        _occupied_intervals(candidate, point) for point in samples
    )
    source_occupied = sum(bool(intervals) for intervals in source_states)
    candidate_occupied = sum(bool(intervals) for intervals in candidate_states)
    matching_occupied = sum(
        bool(source_intervals) and bool(candidate_intervals)
        for source_intervals, candidate_intervals in zip(
            source_states,
            candidate_states,
        )
    )
    false_occupied = sum(
        not source_intervals and bool(candidate_intervals)
        for source_intervals, candidate_intervals in zip(
            source_states,
            candidate_states,
        )
    )
    plan_recall = (
        matching_occupied / source_occupied
        if source_occupied
        else 1.0
    )
    plan_overreach = (
        false_occupied / candidate_occupied
        if candidate_occupied
        else 0.0
    )
    source_heights = [vertex[2] for vertex in source_patch.vertices]
    candidate_heights = [vertex[2] for vertex in candidate.vertices]
    fallback_span = max(
        max(source_heights) - min(source_heights),
        max(candidate_heights) - min(candidate_heights),
    )
    height_error = max(
        _vertical_endpoint_error(
            source_intervals,
            candidate_intervals,
            fallback_span=fallback_span,
        )
        for source_intervals, candidate_intervals in zip(
            source_states,
            candidate_states,
        )
    )
    occlusion_queries = _occlusion_samples(source_patch, candidate, config)
    disagreements = sum(
        bool(occlusion_intersections(source_patch, query))
        != bool(occlusion_intersections(candidate, query))
        for query in occlusion_queries
    )
    occlusion_disagreement = disagreements / len(occlusion_queries)
    gap_error = plan_overreach
    reason = None
    if plan_recall < config.minimum_plan_recall:
        reason = "plan_recall"
    elif plan_overreach > config.maximum_plan_overreach:
        reason = "plan_overreach"
    elif height_error > config.maximum_vertical_endpoint_error:
        reason = "vertical_endpoint_error"
    elif occlusion_disagreement > config.maximum_occlusion_disagreement:
        reason = "occlusion_disagreement"
    method = str(candidate.provenance.get("method", "candidate"))
    return MassPatchCandidateReport(
        candidate_method=method,
        accepted=reason is None,
        plan_recall=plan_recall,
        plan_overreach=plan_overreach,
        vertical_endpoint_error=height_error,
        gap_preservation_error=gap_error,
        occlusion_disagreement=occlusion_disagreement,
        rejection_reason=reason,
    )


def _patch_complexity(patch: MassPatch) -> tuple[int, int]:
    """Return a deterministic geometric complexity key for one patch."""
    return (len(patch.triangle_indices), len(patch.vertices))


def generate_mass_patches(
    mesh: MeshGeometry3D,
    config: MassPatchGenerationConfig | None = None,
) -> MassPatchGenerationResult:
    """Generate exact connected-component baselines for one source mesh."""
    _validate_source_mesh(mesh)
    config = config or MassPatchGenerationConfig()
    patches = []
    component_reports = []
    for component_index, component in enumerate(_component_meshes(mesh)):
        # The exact source component is the mandatory baseline before any
        # simplification candidate is allowed to replace it.
        exact_patch = _annotate_generated_patch(
            mass_patch_from_mesh(component),
            source_mesh_id=mesh.id,
            component_index=component_index,
            candidate_method="exact_component",
        )
        exact_report = _exact_component_report()
        candidate_methods = ["exact_component"]
        candidate_reports = [exact_report]
        selected_patch = exact_patch
        selected_method = "exact_component"
        rejections = {}
        obb = _oriented_box_candidate(component)
        if obb is not None:
            obb = _annotate_generated_patch(
                obb,
                source_mesh_id=mesh.id,
                component_index=component_index,
                candidate_method="oriented_bounding_box",
            )
            candidate_methods.append("oriented_bounding_box")
            obb_report = validate_mass_patch_candidate(component, obb, config)
            candidate_reports.append(obb_report)
            if obb_report.accepted and _patch_complexity(obb) < _patch_complexity(
                exact_patch
            ):
                selected_patch = obb
                selected_method = "oriented_bounding_box"
            elif not obb_report.accepted:
                rejections["oriented_bounding_box"] = (
                    obb_report.rejection_reason or "rejected"
                )
        patches.append(selected_patch)
        selected_report = next(
            report
            for report in candidate_reports
            if report.candidate_method == selected_method
        )
        selected_patch = _attach_validation_provenance(
            selected_patch,
            config,
            selected_report,
        )
        patches[-1] = selected_patch
        component_reports.append(
            MassPatchComponentReport(
                component_index=component_index,
                candidate_methods=tuple(candidate_methods),
                selected_candidate=selected_method,
                candidate_reports=tuple(candidate_reports),
                rejections=rejections,
                gap_preservation_error=selected_report.gap_preservation_error or 0.0,
                uncertainties=(
                    ("source_topology_uncertain",)
                    if component.is_closed is not True
                    or component.is_manifold is not True
                    else ()
                ),
            )
        )
    return MassPatchGenerationResult(
        source_mesh_id=mesh.id,
        patches=tuple(patches),
        component_reports=tuple(component_reports),
    )


__all__ = [
    "MassPatchCandidateReport",
    "MassPatchComponentReport",
    "MassPatchGenerationConfig",
    "MassPatchGenerationResult",
    "generate_mass_patches",
]
