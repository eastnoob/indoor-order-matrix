"""Exact-cell physical occupancy field over pre-resolved plan geometry."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite
from typing import Any

from shapely.geometry import Polygon, box

from .field_core import Field, FieldQuery, FieldSample, FieldStatus, _freeze
from .geometry_views import component_shape


def _finite(value: Any) -> bool:
    """Accept finite real coordinates while excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def _vector(value: Any, size: int) -> bool:
    """Validate a fixed-length numeric query vector without coercion."""
    return isinstance(value, (list, tuple)) and len(value) == size and all(_finite(item) for item in value)


def _query_malformed(query: FieldQuery) -> bool:
    """Validate optional geometry requests before refusing unsupported semantics."""
    plane = query.plane
    if plane is not None:
        if not isinstance(plane, Mapping):
            return True
        if "axis" in plane:
            valid = plane.get("axis") in ("x", "y", "z") and _finite(plane.get("value"))
        else:
            valid = (_vector(plane.get("origin"), 3) and _vector(plane.get("normal"), 3)
                     and any(plane["normal"]))
        if not valid or ("units" in plane and (not isinstance(plane["units"], str) or not plane["units"].strip())):
            return True
    if query.height_band is not None and (
        not _vector(query.height_band, 2) or query.height_band[0] > query.height_band[1]
    ):
        return True
    return query.demand is not None and (not isinstance(query.demand, Mapping) or not query.demand)


def _points(value: Any) -> tuple[tuple[float, float], ...] | None:
    """Validate one finite polygon ring without repairing its topology."""
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    result = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        if not all(_finite(item) for item in point):
            return None
        result.append((float(point[0]), float(point[1])))
    return tuple(result)


def _components(value: Any) -> tuple[dict[str, object], ...] | None:
    """Validate polygon components before delegating union construction."""
    if not isinstance(value, (list, tuple)):
        return None
    result = []
    for component in value:
        if not isinstance(component, Mapping):
            return None
        exterior = _points(component.get("exterior"))
        holes = component.get("holes", ())
        if exterior is None or not isinstance(holes, (list, tuple)):
            return None
        normalized_holes = []
        for hole in holes:
            ring = _points(hole)
            if ring is None:
                return None
            normalized_holes.append(ring)
        polygon = Polygon(exterior, normalized_holes)
        if polygon.is_empty or not polygon.is_valid or not _finite(polygon.area) or polygon.area <= 0.0:
            return None
        result.append({"exterior": exterior, "holes": tuple(normalized_holes)})
    return tuple(result)


class FreeSpaceField(Field[tuple[int, int], bool]):
    """Evaluate exact (row, column) cells in an explicit plan domain.

    Columns advance X and rows advance Y from ``origin``. Indices must satisfy
    0 <= row < n_rows and 0 <= column < n_cols; geometry is clipped to the domain.
    """

    def __init__(
        self,
        *,
        domain: Mapping[str, object] | None,
        origin: tuple[float, float],
        spacing: float,
        n_rows: int,
        n_cols: int,
        physical_occupancy: Iterable[Mapping[str, object]] | None,
        unresolved_source_ids: Iterable[str],
        query_context: Mapping[str, object],
        frame: str,
        origin_offset: tuple[float, float],
        algorithm_version: str = "free-space-field/1",
        schema_version: str = "free-space-field/1",
    ) -> None:
        """Freeze the explicit handoff and validate all lattice inputs."""
        object.__setattr__(self, "_sealed", False)
        self._input_invalid = False
        if not _vector(origin, 2):
            raise ValueError("origin must contain two finite numbers")
        if not _finite(spacing) or spacing <= 0:
            raise ValueError("spacing must be finite and positive")
        if isinstance(n_rows, bool) or not isinstance(n_rows, int) or n_rows <= 0:
            raise ValueError("n_rows must be a positive integer")
        if isinstance(n_cols, bool) or not isinstance(n_cols, int) or n_cols <= 0:
            raise ValueError("n_cols must be a positive integer")
        try:
            bounds_valid = all(_finite(origin[axis] + count * spacing)
                               for axis, count in enumerate((n_cols, n_rows)))
        except OverflowError:
            bounds_valid = False
        if not bounds_valid:
            raise ValueError("lattice bounds must remain finite")
        if not isinstance(frame, str) or not frame.strip():
            raise ValueError("frame must be a non-empty string")
        if not _vector(origin_offset, 2):
            raise ValueError("origin_offset must contain finite values")
        if not isinstance(query_context, Mapping):
            raise ValueError("query_context must be a mapping")
        if (
            query_context.get("frame") != frame
            or not isinstance(query_context.get("domain_id"), str)
            or not query_context["domain_id"].strip()
            or query_context.get("plane") is not None
            or query_context.get("height_band") is not None
            or query_context.get("demand") is not None
            or query_context.get("geometry_query", "whole_height_planar_mass_patch") != "whole_height_planar_mass_patch"
        ):
            raise ValueError("query_context must declare matching domain_id/frame and whole-height projection")
        if not all(isinstance(value, str) and value.strip() for value in (algorithm_version, schema_version)):
            raise ValueError("algorithm_version and schema_version must be non-empty strings")
        self._origin = (float(origin[0]), float(origin[1]))
        self._spacing = float(spacing)
        self._n_rows = n_rows
        self._n_cols = n_cols
        self._frame = frame
        self.origin_offset = tuple(float(value) for value in origin_offset)
        self.query_context = _freeze(query_context)
        self._domain_id = query_context["domain_id"]
        self._domain_shape = None
        domain_components = None
        if domain is not None:
            if (
                not isinstance(domain, Mapping)
                or domain.get("id") != self._domain_id
                or domain.get("frame") != frame
            ):
                self._input_invalid = True
            else:
                domain_components = _components(domain.get("components"))
                self._domain_shape = component_shape(domain_components or ()) if domain_components is not None else None
                if domain_components is None or self._domain_shape is None or self._domain_shape.is_empty or not self._domain_shape.is_valid:
                    self._input_invalid = True
        self._occupancy_missing = physical_occupancy is None
        if isinstance(physical_occupancy, (Mapping, str, bytes)):
            raise TypeError("physical_occupancy must be an iterable of records or None")
        try:
            records = () if physical_occupancy is None else tuple(physical_occupancy)
        except TypeError as exc:
            raise TypeError("physical_occupancy must be an iterable of records or None") from exc
        if not isinstance(unresolved_source_ids, (list, tuple, set, frozenset)) or any(
            not isinstance(source_id, str) or not source_id.strip() for source_id in unresolved_source_ids
        ):
            raise ValueError("unresolved_source_ids must be an explicit sequence of non-empty strings")
        self.unresolved_source_ids = tuple(sorted(set(unresolved_source_ids)))
        unknown_owners = set(self.unresolved_source_ids)
        self._accepted_present = False
        occupancy_shapes = []
        frozen_records = []
        selected_audit = []
        selected_ids = set()
        represented_owners: set[str] = set()
        for record in records:
            if (not isinstance(record, Mapping) or not isinstance(record.get("id"), str)
                or not record["id"].strip() or record["id"] in selected_ids):
                self._input_invalid = True
                continue
            selected_ids.add(record["id"])
            status = record.get("representation_status")
            if status not in ("original", "accepted"):
                self._input_invalid = True
                continue
            if status == "accepted":
                self._accepted_present = True
            raw_owners = record.get("represented_source_ids")
            if not isinstance(raw_owners, (list, tuple)) or any(
                not isinstance(item, str) or not item.strip() for item in raw_owners
            ):
                self._input_invalid = True
                continue
            owners = tuple(raw_owners)
            if not owners or len(set(owners)) != len(owners):
                self._input_invalid = True
                continue
            if represented_owners.intersection(owners):
                self._input_invalid = True
                continue
            represented_owners.update(owners)
            raw_components = record.get("geometry_components")
            components = () if raw_components is None else _components(raw_components)
            if components is None:
                self._input_invalid = True
                continue
            # Compatibility views also contain Rect and channel objects. Freeze only
            # the consumed geometry and original audit fields, never those extra models.
            record_provenance = record.get("representation_provenance")
            if record_provenance is not None and not isinstance(record_provenance, Mapping):
                self._input_invalid = True
                continue
            audit = {"id": record["id"], "represented_source_ids": owners,
                     "representation_status": status,
                     "representation_provenance": {} if record_provenance is None else record_provenance}
            for key in ("provenance", "representation_diagnostics", "_source_geometry_refs", "_neutral_source_id", "adapter_refs"):
                if key in record:
                    audit[key] = record[key]
            try:
                audit = _freeze(audit)
                frozen_records.append(_freeze({**audit, "geometry_components": components}))
            except (TypeError, ValueError):
                self._input_invalid = True
                continue
            selected_audit.append(audit)
            if not components:
                unknown_owners.update(owners)
                continue
            shape = component_shape(components)
            if shape is None or shape.is_empty or not shape.is_valid:
                self._input_invalid = True
                continue
            occupancy_shapes.append((shape, audit))
        self.physical_occupancy = tuple(frozen_records)
        self._occupancy_shapes = tuple(occupancy_shapes)
        self._unknown_owners = tuple(sorted(unknown_owners))
        self._represented_owners = tuple(sorted(represented_owners))
        provenance = {
            "algorithm_version": algorithm_version,
            "schema_version": schema_version,
            "frame": frame,
            "origin_offset": tuple(float(value) for value in origin_offset),
            "input_query_context": self.query_context,
            "units": "boolean", "geometry_units": "m", "area_units": "m^2",
            "selected_records": tuple(selected_audit),
            "unknown_source_ids": self._unknown_owners,
        }
        super().__init__(
            domain=None if domain is None else {"id": self._domain_id, "frame": frame,
                "components": domain_components or ()},
            frame=frame,
            value_schema="physical_occupancy_bool",
            representation="exact_cell",
            provenance=provenance,
        )
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent mutation of constructor inputs after the field is sealed."""
        if getattr(self, "_sealed", False):
            raise AttributeError(f"{name} is immutable")
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        """Keep deletion from bypassing the frozen declaration and cached evidence."""
        raise AttributeError(f"{name} is immutable")

    def evaluate(
        self, target: tuple[int, int], query: FieldQuery
    ) -> FieldSample[bool]:
        """Evaluate one exact lattice cell under the frozen whole-height query."""
        if not isinstance(query, FieldQuery):
            raise TypeError("query must be a FieldQuery")
        base = {**self.provenance, "query_revision": query.revision, "tolerance": query.tolerance,
                "plane": query.plane, "height_band": query.height_band, "demand": query.demand}
        if self._input_invalid or not isinstance(target, tuple) or len(target) != 2 or any(
            isinstance(value, bool) or not isinstance(value, int) for value in target
        ):
            return self._sample(None, FieldStatus.INVALID, query, base, "malformed field, target, or geometry")
        row, column = target
        if row < 0 or row >= self._n_rows or column < 0 or column >= self._n_cols:
            return self._sample(None, FieldStatus.INVALID, query, base, "target is outside the lattice index range")
        if query.domain_id != self._domain_id or query.frame != self._frame:
            return self._sample(None, FieldStatus.INVALID, query, base, "query domain or frame does not match the frozen input")
        if _query_malformed(query):
            return self._sample(None, FieldStatus.INVALID, query, base, "malformed plane, height-band, or demand query")
        if query.plane is not None or query.height_band is not None or query.demand is not None:
            return self._sample(None, FieldStatus.NOT_AVAILABLE, query, base, "section, height-band, and demand queries are unsupported")
        cell = box(
            self._origin[0] + column * self._spacing,
            self._origin[1] + row * self._spacing,
            self._origin[0] + (column + 1) * self._spacing,
            self._origin[1] + (row + 1) * self._spacing,
        )
        eligible = cell.intersection(self._domain_shape) if self._domain_shape is not None else None
        base["support"] = {
            "target": target,
            "cell_bounds": (
                cell.bounds[0], cell.bounds[1], cell.bounds[2], cell.bounds[3]
            ),
            "domain_intersection_area": float(eligible.area) if eligible is not None else None,
            "lattice": {
                "origin": self._origin,
                "spacing": self._spacing,
                "n_rows": self._n_rows,
                "n_cols": self._n_cols,
            },
            "frame": self._frame,
            "plane": None,
            "height_band": None,
        }
        if self._occupancy_missing or eligible is None:
            return self._sample(None, FieldStatus.NOT_AVAILABLE, query, base, "domain or occupancy channel is unavailable")
        # Query tolerance is a length, not an area threshold: every positive sliver counts.
        if eligible.area <= 0.0:
            return self._sample(None, FieldStatus.OUTSIDE, query, base, "cell has no positive-area domain intersection")
        positive_ids = []
        source_ids = set()
        conditional = self._accepted_present
        for shape, audit in self._occupancy_shapes:
            if eligible.intersection(shape).area > 0.0:
                positive_ids.append(audit["id"])
                source_ids.update(audit["represented_source_ids"])
        base["occupied_record_ids"] = tuple(sorted(positive_ids))
        base["represented_source_ids"] = tuple(sorted(source_ids))
        if positive_ids:
            status = FieldStatus.CONDITIONAL if conditional else FieldStatus.ESTABLISHED
            explanation = "occupied by pre-resolved physical geometry"
            if conditional:
                explanation = "occupied in a field containing accepted substitute geometry; exact physical envelope is not inferred"
            return self._sample(True, status, query, base, explanation, source_ids)
        if self._unknown_owners:
            return self._sample(None, FieldStatus.UNKNOWN, query, base, "unresolved support prevents a known-empty result", self._unknown_owners)
        return self._sample(False, FieldStatus.CONDITIONAL if conditional else FieldStatus.ESTABLISHED, query, base,
                            "empty physical occupancy from accepted substitute geometry; this is not a walkability or clearance claim"
                            if conditional else
                            "empty physical occupancy; this is not a walkability or clearance claim", self._represented_owners)

    def _sample(self, value, status, query, provenance, explanation, source_ids=()):
        """Build one immutable sample with deterministic support and provenance."""
        provenance = dict(provenance)
        provenance.setdefault("support", {"field": "physical_occupancy", "representation": "exact_cell"})
        return FieldSample(
            value=value,
            status=status,
            query=query,
            support=provenance.get("support"),
            source_ids=tuple(sorted(source_ids)),
            provenance=provenance,
            explanation=explanation,
        )
