"""Analyzer-derived, weight-free boundary evidence over neutral substitutes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Iterable, Mapping
from typing import TypeAlias

from .geometry_substitutes import MassPatch, SurfacePatch
from .geometry_views import PlanProjection, plan_projection, vertical_intervals_at


Substitute: TypeAlias = MassPatch | SurfacePatch


def _json_value(value: object) -> object:
    """Convert nested immutable or mapping values to JSON-compatible values."""
    if isinstance(value, Mapping):
        return {str(key): _json_value(nested) for key, nested in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def _centroid(projection: PlanProjection) -> tuple[float, float] | None:
    """Return the centroid of the first projected component's vertices."""
    if not projection.components:
        return None
    points = projection.components[0]["exterior"]
    if not points:
        return None
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _representative_points(projection: PlanProjection) -> tuple[tuple[float, float], ...]:
    """Return one interior plan point for every disconnected component."""
    from shapely.geometry import Polygon

    points = []
    for component in projection.components:
        exterior = component["exterior"]
        holes = component["holes"]
        if not exterior:
            continue
        polygon = Polygon(exterior, holes)
        if polygon.is_valid and not polygon.is_empty:
            representative = polygon.representative_point()
            points.append((float(representative.x), float(representative.y)))
        else:
            # Invalid source topology remains auditable; a boundary vertex is
            # still preferable to silently dropping this component's heights.
            points.append((float(exterior[0][0]), float(exterior[0][1])))
    return tuple(points)


def _projection_from_references(
    surface: SurfacePatch,
    mass_by_reference: Mapping[str, MassPatch],
) -> PlanProjection | None:
    """Resolve surface location from referenced geometry without assigning mass."""
    components = []
    for reference in surface.geometry_refs:
        patch = mass_by_reference.get(reference)
        if patch is None:
            continue
        components.extend(plan_projection(patch).components)
    if not components:
        return None
    coordinates = tuple(components[0]["exterior"])
    return PlanProjection(
        source_patch_id=surface.id,
        coordinates=coordinates,
        components=tuple(components),
    )


def _nearest_boundary_point(
    projection: PlanProjection,
    point: tuple[float, float],
) -> tuple[float, float] | None:
    """Return the nearest point on any projected exterior or hole boundary."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import nearest_points, unary_union

    boundaries = []
    for component in projection.components:
        polygon = Polygon(component["exterior"], component["holes"])
        if polygon.is_valid and not polygon.is_empty:
            boundaries.append(polygon.boundary)
    if not boundaries:
        return None
    nearest = nearest_points(Point(point), unary_union(boundaries))[1]
    return (float(nearest.x), float(nearest.y))


def _default_body_profile() -> dict[str, object]:
    """Return an explicit generic body query for default factual evidence."""
    return {"id": "default-body", "height_band": (0.0, 1.8), "radius": 0.3}


def _default_visual_band() -> dict[str, object]:
    """Return an explicit generic eye-height query for default factual evidence."""
    return {"id": "default-eye", "height_band": (1.5, 1.8)}


@dataclass(frozen=True)
class BoundaryEvidence:
    """An analyzer-derived interface with separate factual evidence channels."""

    id: str
    source_refs: tuple[str, ...]
    method: str
    projection: PlanProjection | None
    representative_point: tuple[float, float] | None
    representative_points: tuple[tuple[float, float], ...]
    provenance: Mapping[str, object]
    physical_continuity: Mapping[str, object]
    walking_permeability: tuple[Mapping[str, object], ...]
    visual_permeability: tuple[Mapping[str, object], ...]
    gestalt_continuity: Mapping[str, object]
    tolerances: Mapping[str, float]
    uncertainties: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialize evidence without collapsing channels into a weight."""
        return {
            "id": self.id,
            "source_refs": self.source_refs,
            "method": self.method,
            "projection": self.projection.to_dict() if self.projection else None,
            "representative_point": self.representative_point,
            "representative_points": self.representative_points,
            "provenance": _json_value(self.provenance),
            "physical_continuity": _json_value(self.physical_continuity),
            "walking_permeability": _json_value(self.walking_permeability),
            "visual_permeability": _json_value(self.visual_permeability),
            "gestalt_continuity": _json_value(self.gestalt_continuity),
            "tolerances": _json_value(self.tolerances),
            "uncertainties": self.uncertainties,
        }

    def relate_subject(
        self,
        subject: Mapping[str, object],
        *,
        max_distance: float | None = None,
    ) -> dict[str, object]:
        """Describe a subject-interface relation without producing an influence score."""
        subject_point = subject.get("centroid")
        if (
            not isinstance(subject_point, (tuple, list))
            or len(subject_point) != 2
            or self.projection is None
        ):
            return {"status": "unknown", "reason": "missing_plan_centroid"}
        normalized_subject_point = (
            float(subject_point[0]),
            float(subject_point[1]),
        )
        nearest = _nearest_boundary_point(self.projection, normalized_subject_point)
        if nearest is None:
            return {"status": "unknown", "reason": "missing_boundary_geometry"}
        distance = math.hypot(
            normalized_subject_point[0] - nearest[0],
            normalized_subject_point[1] - nearest[1],
        )
        relation: dict[str, object] = {
            "subject_id": subject.get("id"),
            "boundary_id": self.id,
            "distance": distance,
            "status": "evaluated",
            "nearest_side": (
                nearest[0] - normalized_subject_point[0],
                nearest[1] - normalized_subject_point[1],
            ),
            "frame_agreement": "not_evaluated",
        }
        if max_distance is not None:
            if not math.isfinite(max_distance) or max_distance < 0.0:
                raise ValueError("max_distance must be finite and non-negative")
            if distance > max_distance:
                # Range controls work performed; it is not a zero-valued relation.
                relation["status"] = "not_evaluated"
                relation.pop("nearest_side")
                relation.pop("frame_agreement")
        return relation


def _height_intervals(
    patch: MassPatch,
    points: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    """Read and deterministically combine local intervals for all components."""
    intervals = {
        interval
        for point in points
        for interval in vertical_intervals_at(patch, point).intervals
    }
    return tuple(sorted(intervals))


def _overlaps(
    first: tuple[float, float],
    second: tuple[float, float],
) -> bool:
    """Return whether two closed vertical bands overlap."""
    return first[1] >= second[0] and first[0] <= second[1]


def _walking_channel(
    intervals: tuple[tuple[float, float], ...],
    profiles: tuple[Mapping[str, object], ...],
    *,
    mass_present: bool,
) -> tuple[Mapping[str, object], ...]:
    """Describe body-band collision facts for each explicit body profile."""
    results = []
    for profile in profiles:
        band = tuple(float(value) for value in profile["height_band"])
        collision = any(_overlaps(interval, band) for interval in intervals)
        results.append(
            {
                "profile_id": profile["id"],
                "height_band": band,
                "radius": profile.get("radius"),
                "status": "blocked" if mass_present and collision else "clear",
                "collision_intervals": tuple(interval for interval in intervals if _overlaps(interval, band)),
            }
        )
    return tuple(results)


def _visual_channel(
    intervals: tuple[tuple[float, float], ...],
    bands: tuple[Mapping[str, object], ...],
    *,
    mass_present: bool,
    optical_transmittance: object = None,
) -> tuple[Mapping[str, object], ...]:
    """Describe geometry and optical evidence independently for each eye band."""
    results = []
    for band_record in bands:
        band = tuple(float(value) for value in band_record["height_band"])
        geometry_blocked = mass_present and any(_overlaps(interval, band) for interval in intervals)
        results.append(
            {
                "band_id": band_record["id"],
                "height_band": band,
                "geometry_status": "blocked" if geometry_blocked else "clear",
                "optical_transmittance": optical_transmittance,
                "status": (
                    "unknown"
                    if optical_transmittance is None and not mass_present
                    else "blocked"
                    if geometry_blocked and optical_transmittance in (None, 0.0)
                    else "clear"
                ),
            }
        )
    return tuple(results)


def _evidence_for_patch(
    patch: Substitute,
    *,
    body_profiles: tuple[Mapping[str, object], ...],
    visual_bands: tuple[Mapping[str, object], ...],
    optical_transmittance: object = None,
    surface_projection: PlanProjection | None = None,
) -> BoundaryEvidence:
    """Build one evidence record from a physical or surface substitute."""
    if isinstance(patch, MassPatch):
        projection = plan_projection(patch)
        points = _representative_points(projection)
        point = points[0] if points else None
        intervals = _height_intervals(patch, points)
        physical = {
            "mass_present": True,
            "occupied_height": intervals[0] if len(intervals) == 1 else intervals,
            "component_count": len(projection.components),
            "thickness": max(interval[1] - interval[0] for interval in intervals) if intervals else None,
        }
        gestalt = {
            "alignment": "not_evaluated",
            "good_continuation": "single_patch",
            "surface_identity": None,
        }
        uncertainties = ("multiple_height_intervals",) if len(intervals) > 1 else ()
    else:
        projection = surface_projection
        points = _representative_points(projection) if projection else ()
        point = points[0] if points else None
        intervals = ()
        physical = {
            "mass_present": False,
            "occupied_height": None,
            "component_count": 0,
            "thickness": 0.0,
        }
        gestalt = {
            "alignment": "not_evaluated",
            "good_continuation": "surface_region",
            "surface_identity": patch.source_surface_id,
            "color": patch.color,
            "elevation": patch.elevation,
        }
        uncertainties = ("surface_has_no_mass_geometry",)
    return BoundaryEvidence(
        id=f"boundary-evidence:{patch.id}",
        source_refs=(patch.id,),
        method="mass_patch_contour_or_surface_edge_evidence",
        projection=projection,
        representative_point=point,
        representative_points=points,
        provenance=patch.provenance,
        physical_continuity=physical,
        walking_permeability=_walking_channel(intervals, body_profiles, mass_present=isinstance(patch, MassPatch)),
        visual_permeability=_visual_channel(
            intervals,
            visual_bands,
            mass_present=isinstance(patch, MassPatch),
            optical_transmittance=optical_transmittance,
        ),
        gestalt_continuity=gestalt,
        tolerances={"height": 1e-9, "distance": 1e-9},
        uncertainties=uncertainties,
    )


def _normalized_queries(
    records: Iterable[Mapping[str, object]],
    *,
    default: Mapping[str, object],
    label: str,
) -> tuple[Mapping[str, object], ...]:
    """Validate and normalize named body or visual height-band queries."""
    source_records = tuple(records) or (default,)
    normalized = []
    for record in source_records:
        identifier = record.get("id") if isinstance(record, Mapping) else None
        band = record.get("height_band") if isinstance(record, Mapping) else None
        if not isinstance(identifier, str) or not identifier:
            raise ValueError(f"{label} requires a non-empty id")
        if not isinstance(band, (tuple, list)) or len(band) != 2:
            raise ValueError(f"{label}.height_band must contain two values")
        values = tuple(float(value) for value in band)
        if not all(math.isfinite(value) for value in values) or values[0] > values[1]:
            raise ValueError(f"{label}.height_band must be finite and ordered")
        radius = record.get("radius")
        if radius is not None and (
            not math.isfinite(float(radius)) or float(radius) <= 0.0
        ):
            raise ValueError(f"{label}.radius must be finite and positive")
        normalized_record = dict(record)
        normalized_record["height_band"] = values
        if radius is not None:
            normalized_record["radius"] = float(radius)
        normalized.append(normalized_record)
    return tuple(normalized)


def derive_boundary_evidence(
    patches: Iterable[Substitute],
    *,
    body_profiles: Iterable[Mapping[str, object]] = (),
    visual_bands: Iterable[Mapping[str, object]] = (),
    optical_transmittance_by_source: Mapping[str, object] | None = None,
) -> tuple[BoundaryEvidence, ...]:
    """Derive separate boundary-channel evidence from neutral substitutes."""
    patches = tuple(patches)
    profiles = _normalized_queries(
        body_profiles,
        default=_default_body_profile(),
        label="body_profile",
    )
    bands = _normalized_queries(
        visual_bands,
        default=_default_visual_band(),
        label="visual_band",
    )
    optical = optical_transmittance_by_source or {}
    mass_by_reference = {
        reference: patch
        for patch in patches
        if isinstance(patch, MassPatch)
        for reference in (patch.id, patch.source_geometry_id)
    }
    return tuple(
        _evidence_for_patch(
            patch,
            body_profiles=profiles,
            visual_bands=bands,
            optical_transmittance=optical.get(
                patch.source_geometry_id if isinstance(patch, MassPatch) else patch.source_surface_id
            ),
            surface_projection=(
                _projection_from_references(patch, mass_by_reference)
                if isinstance(patch, SurfacePatch)
                else None
            ),
        )
        for patch in patches
    )
