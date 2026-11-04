"""Frozen planar grid requests composing the existing geometry and Field contracts.

This executor is a planar profile. Generic 3D and relation Fields need neither
this request profile nor an AnalysisPlane. Geometry backends load on execution so
native adapters can import the records without OCTA or the calculation runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
from types import MappingProxyType

from .field_core import Field, FieldQuery, FieldSample, FieldStatus, _MetadataOverlay
from .scene_contract import (
    AnalysisDomain, AnalysisPlane, NeutralSceneV2, _Record, _json_object,
    _number, _text,
)
from .substitute_contract import load_substitute_registry


REQUEST_VERSION = "planar-analysis-request/2"
WORLD_XY_BASIS = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
DEFAULT_SOURCE_RULES = MappingProxyType({
    "registry": "shared_operation_registry",
    "coverage": "declared_exact_source_set",
    "boundary_membership": "explicit_exact_identity_only",
})
_CAPABILITIES = MappingProxyType({
    "whole_height_projection": True,
    "exact_world_xy_section": True,
    "finite_height_band": True,
    "tilted_section": False,
    "volume_3d": False,
})
_DISPLAY_KEYS = frozenset({"display", "display_name", "color", "colour", "legend", "camera_scale"})


def _default_rules() -> Mapping[str, object]:
    """Supply shared immutable defaults without an unhashable dataclass default."""
    return DEFAULT_SOURCE_RULES


@dataclass(frozen=True)
class GeometryQuery(_Record):
    """An explicit whole-height projection, local-Z band, or zero-thickness cut."""

    kind: str = "whole_height_projection"
    world_z_m: float | None = None
    height_band: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        """Reject malformed or contradictory query parameters before execution."""
        if not isinstance(self.kind, str) or self.kind not in _CAPABILITIES:
            raise ValueError("kind must be a recognized geometry query")
        if self.kind in {"exact_world_xy_section", "tilted_section"}:
            object.__setattr__(self, "world_z_m", _number(self.world_z_m, "world_z_m"))
        elif self.world_z_m is not None:
            raise ValueError("world_z_m applies only to a section query")
        if self.kind == "finite_height_band":
            if not isinstance(self.height_band, (tuple, list)) or len(self.height_band) != 2:
                raise ValueError("height_band must contain two ordered finite bounds")
            bounds = tuple(_number(value, "height_band") for value in self.height_band)
            if bounds[0] >= bounds[1]:
                raise ValueError("height_band must have positive thickness")
            object.__setattr__(self, "height_band", bounds)
        elif self.height_band is not None:
            raise ValueError("height_band applies only to a finite_height_band query")


@dataclass(frozen=True)
class GridSampling(_Record):
    """Finite exact-cell lattice in plane-local metres, columns X and rows Y."""

    origin: tuple[float, float]
    spacing: float
    n_rows: int
    n_cols: int

    def __post_init__(self) -> None:
        """Validate the lattice once, including finite final bounds."""
        if not isinstance(self.origin, (tuple, list)) or len(self.origin) != 2:
            raise ValueError("origin must contain two finite coordinates")
        origin = tuple(_number(value, "origin") for value in self.origin)
        spacing = _number(self.spacing, "spacing", positive=True)
        for name in ("n_rows", "n_cols"):
            count = getattr(self, name)
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ValueError(f"{name} must be a positive integer")
        try:
            for axis, count in enumerate((self.n_cols, self.n_rows)):
                _number(origin[axis] + count * spacing, "lattice bounds")
        except OverflowError:
            raise ValueError("lattice bounds must remain finite") from None
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "spacing", spacing)


@dataclass(frozen=True)
class AnalysisRequest(_Record):
    """Current planar grid execution profile, independent of camera/display state."""

    request_id: str
    plane: AnalysisPlane
    domain: AnalysisDomain | None
    sampling: GridSampling
    operation: str = "free_space"
    geometry_query: GeometryQuery = GeometryQuery()
    source_rules: Mapping[str, object] = field(default_factory=_default_rules)
    demand: Mapping[str, object] | None = None
    geometry_tolerance: float = 0.001
    topology_tolerance: float = 0.001
    height_band_datum: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        """Validate the profile and detach all nested caller-owned parameters."""
        _text(self.request_id, "request_id")
        _text(self.operation, "operation")
        if not isinstance(self.plane, AnalysisPlane):
            raise TypeError("plane must be an AnalysisPlane for this planar profile")
        if self.domain is not None and not isinstance(self.domain, AnalysisDomain):
            raise TypeError("domain must be an AnalysisDomain or None")
        if not isinstance(self.sampling, GridSampling):
            raise TypeError("sampling must be GridSampling for this planar profile")
        if not isinstance(self.geometry_query, GeometryQuery):
            raise TypeError("geometry_query must be GeometryQuery")
        if self.height_band_datum is not None:
            datum = _json_object(self.height_band_datum, "height_band_datum")
            if self.geometry_query.kind != "finite_height_band" or datum.get("mode") != "slab":
                raise ValueError("height_band_datum requires a finite band and selected slab datum")
            # Use AnalysisPlane's frame precision: native XY rotations can round unit Z below one.
            if (any(abs(actual - expected) > 1e-9
                    for actual, expected in zip(self.plane.basis[2], (0.0, 0.0, 1.0)))
                    or any(abs(axis[2]) > 1e-9 for axis in self.plane.basis[:2])):
                raise ValueError("slab height band requires a horizontal upward analysis plane")
            # Captured geometry is already world metres; only the height origin changes.
            lower = _number(datum.get("datum_z_m"), "datum_z_m") - self.plane.origin[2]
            if lower >= 0 or self.geometry_query.height_band != (lower, 0.0):
                raise ValueError("slab datum must be below the plane and match the height band")
            object.__setattr__(self, "height_band_datum", datum)
        object.__setattr__(self, "source_rules", _json_object(self.source_rules, "source_rules"))
        if self.demand is not None:
            object.__setattr__(self, "demand", _json_object(self.demand, "demand"))
        for name in ("geometry_tolerance", "topology_tolerance"):
            object.__setattr__(self, name, _number(getattr(self, name), name, positive=True))


@dataclass(frozen=True)
class AnalysisSnapshot(_Record):
    """Detached immutable evidence binding a request to facts and backend versions."""

    semantic_key: str
    source_fingerprint: str
    request: AnalysisRequest
    backend_versions: Mapping[str, object]
    provenance: Mapping[str, object]

    def __post_init__(self) -> None:
        """Keep audit payloads immutable and enforce the snapshot's typed request."""
        _text(self.semantic_key, "semantic_key")
        _text(self.source_fingerprint, "source_fingerprint")
        if not isinstance(self.request, AnalysisRequest):
            raise TypeError("request must be an AnalysisRequest")
        for name in ("backend_versions", "provenance"):
            object.__setattr__(self, name, _json_object(getattr(self, name), name))


@dataclass(frozen=True)
class AnalysisRun:
    """Existing Field with its frozen query, snapshot and computational support."""

    field: Field[tuple[int, int], bool]
    query: FieldQuery
    snapshot: AnalysisSnapshot
    support_status: FieldStatus
    explanation: str


def query_capabilities() -> Mapping[str, bool]:
    """Describe this planar executor's query kinds, not all generic Field backends."""
    return _CAPABILITIES


def _semantic_json(value: object) -> object:
    """Detach JSON while excluding declared display metadata from calculation identity."""
    if isinstance(value, Mapping):
        return {key: _semantic_json(item) for key, item in value.items() if key not in _DISPLAY_KEYS}
    if isinstance(value, (list, tuple)):
        return [_semantic_json(item) for item in value]
    return value


def _digest(value: object) -> str:
    """Hash canonical finite JSON rather than mutable or process-dependent identities."""
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _backend_versions() -> dict[str, object]:
    """Bind installed numerical versions and actual shared implementation bytes."""
    packages = {}
    for name in ("shapely", "trimesh", "numpy"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "unavailable"
    # Shared helpers lack a uniform version constant. File digests prevent stale
    # reuse after a resolver/geometry repair without importing optional backends.
    modules = ("analysis_requests", "_analysis_domain_handoff", "analysis_substitute_discovery", "scene_contract",
               "neutral_scene_views", "geometry_substitutes", "geometry_views", "field_core",
               "free_space_field", "section_views", "substitute_contract")
    implementations = {name: sha256(Path(__file__).with_name(name + ".py").read_bytes()).hexdigest()
                       for name in modules}
    return {"executor": REQUEST_VERSION, "packages": packages, "implementations": implementations}


def _domain_identity(domain: AnalysisDomain | None) -> object:
    """Retain exact selected topology refs and membership, excluding display/audit labels."""
    if domain is None:
        return None
    return {"id": domain.id, "geometry_refs": list(domain.geometry_refs),
            "source_id": domain.source_id,
            "boundary_member_source_ids": _semantic_json(
                domain.provenance.get("boundary_member_source_ids", ())) }


def _run_identity(scene: NeutralSceneV2, request: AnalysisRequest) -> tuple[str, str, dict]:
    """Fingerprint factual occupancy inputs separately from overridden request context."""
    if not isinstance(scene, NeutralSceneV2) or not isinstance(request, AnalysisRequest):
        raise TypeError("identity requires NeutralSceneV2 and AnalysisRequest")
    context = scene.context
    facts = {
        "contract_version": context.contract_version,
        "source_schema": context.source_schema, "adapter_version": context.adapter_version,
        "source_length_unit": context.source_length_unit,
        "analysis_length_unit": context.analysis_length_unit,
        "world_coordinate_system": _semantic_json(context.world_coordinate_system),
        "geometries": [_semantic_json(mesh.to_dict()) for mesh in scene.geometries],
        "sources": [{"id": source.id, "source_id": source.source_id,
                     "source_role": source.source_role, "source_class": source.source_class,
                     "world_transform": source.to_dict()["world_transform"],
                     "geometry_refs": list(source.geometry_refs),
                     "representation_identifier": source.provenance.get("representation_identifier"),
                     "bindings": _semantic_json(source.factual_properties.get("OM_FunctionSubstitutes")),
                     "coverage": _semantic_json(source.factual_properties.get("OM_PhysicalOccupancy"))}
                    for source in scene.source_objects],
    }
    fingerprint = _digest(facts)
    params = request.to_dict()
    del params["request_id"]
    del params["plane"]["name"]
    params["domain"] = _domain_identity(request.domain)
    registry = load_substitute_registry()
    rules = {"schema": registry["schema"],
             "operations": {key: value for key, value in registry.get("operations", {}).items()
                            if key in {"free_space", "physical_occupancy", "physical_occupancy_section"}},
             "contracts": {key: value for key, value in registry["contracts"].items()
                           if value.get("consumer") == "physical_occupancy"}}
    versions = _backend_versions()
    key = _digest({"source_fingerprint": fingerprint, "request": params,
                   "shared_rules": _semantic_json(rules), "backend_versions": versions})
    return fingerprint, key, versions


def semantic_cache_key(scene: NeutralSceneV2, request: AnalysisRequest) -> str:
    """Return calculation identity without random request IDs or display state."""
    return _run_identity(scene, request)[1]


def is_stale(snapshot: AnalysisSnapshot, scene: NeutralSceneV2, request: AnalysisRequest) -> bool:
    """Compare current semantics without inventing a seventh FieldStatus."""
    if not isinstance(snapshot, AnalysisSnapshot):
        raise TypeError("snapshot must be AnalysisSnapshot")
    return snapshot.semantic_key != semantic_cache_key(scene, request)


def _unsupported_reason(scene: NeutralSceneV2, request: AnalysisRequest) -> str:
    """Refuse unsupported semantics explicitly instead of using an approximation."""
    if request.operation not in {"free_space", "physical_occupancy"}:
        return "operation is unavailable in this planar executor"
    if not _CAPABILITIES[request.geometry_query.kind]:
        return f"{request.geometry_query.kind} is unavailable in this planar executor"
    if request.source_rules != DEFAULT_SOURCE_RULES:
        return "modified source rules are unavailable; only the shared registry policy is supported"
    if request.demand is not None:
        return "demand operators are unavailable in this physical occupancy executor"
    if scene.context.analysis_length_unit != "m":
        return "calculation requires normalized metre geometry"
    if (request.geometry_query.kind == "exact_world_xy_section"
            and request.plane.basis != WORLD_XY_BASIS):
        return "exact world-XY section currently requires the canonical world-XY basis"
    if request.domain is None:
        return "an explicit exact analysis domain is required"
    return ""


def _qualified_domain(scene: NeutralSceneV2, request: AnalysisRequest) -> tuple[dict | None, dict]:
    """Consume only the exact authored domain through the existing confirmation seam."""
    from ._analysis_domain_handoff import domain_handoff

    # Domain qualification must not trigger an unrelated whole-height occupancy
    # observation for a section request. This private projection retains only its
    # actual domain mesh facts; the full source inventory is resolved separately.
    projection = NeutralSceneV2(context=scene.context, analysis_domain=request.domain,
                               geometries=tuple(mesh for mesh in scene.geometries
                                                if mesh.id in request.domain.geometry_refs))
    frame = {"analysis_plane": request.plane, "units": "m", "datum_m": 0.0,
             "cut_height_m": request.geometry_query.world_z_m or 0.0}
    kwargs = {"candidates": (), "frame_request": frame,
              "expected_session_revision": None, "expected_source_revision": None}
    initial = domain_handoff(projection, session_state=None, action=None, **kwargs)
    candidate = initial["candidates"][0]
    if candidate["status"] == "refused":
        return None, {"reason": candidate["reason"], **initial["provenance"]}
    provenance = initial["provenance"]
    action = {"kind": "confirm", "action_id": request.request_id, "actor": "analysis_request",
              "time": "immutable-request-snapshot", "reason": "execute explicitly selected request domain",
              "candidate_version_id": candidate["version_id"],
              "expected_candidate_identity": candidate["identity"],
              "expected_session_revision": initial["session_revision"],
              "expected_source_revision": provenance["source_revision"],
              "expected_plane_identity": provenance["frame_id"],
              "expected_request_identity": provenance["request_id"], "acknowledged_conflict_ids": []}
    kwargs.update(expected_session_revision=initial["session_revision"],
                  expected_source_revision=provenance["source_revision"])
    result = domain_handoff(projection, session_state=initial["session_state"], action=action, **kwargs)
    audit = {**result["provenance"], "current": result["current"], "attempt": result["attempt"],
             "input_scope": "exact_domain_geometry_only"}
    return result["scope_polygon"], audit


def _scope_exclusions(scene: NeutralSceneV2) -> tuple[set[str], dict]:
    """Resolve exact members against raw identities before missing geometry can drop them."""
    from .neutral_scene_views import _boundary_member_identity, _domain_shell_identity

    records = [{"id": source.id} for source in scene.source_objects]
    members, diagnostics = _boundary_member_identity(scene, records, domain_available=True)
    domain = scene.analysis_domain
    matches = [source for source in scene.source_objects if source.source_id == domain.source_id]
    if domain.source_id is not None and (len(matches) != 1 or
            (matches[0].source_role or "").strip().lower() not in {
                "slab", "floor", "space", "spatial_zone", "spatial_container"}):
        # A domain provenance link alone cannot erase a physical furniture source.
        scene = replace(scene, analysis_domain=replace(domain, source_id=None))
    support, support_audit = _domain_shell_identity(scene, records, domain_available=True)
    return members | support, {"boundary_membership": diagnostics,
                               "boundary_member_ids": sorted(members), "domain_support": support_audit}


def _components(geometry, origin=(0.0, 0.0)) -> tuple[dict, ...]:
    """Convert qualified polygon topology to plane-local components without repair."""
    parts = (geometry,) if geometry.geom_type == "Polygon" else getattr(geometry, "geoms", ())
    return tuple({"exterior": tuple((x - origin[0], y - origin[1]) for x, y in part.exterior.coords),
                  "holes": tuple(tuple((x - origin[0], y - origin[1]) for x, y in ring.coords)
                                 for ring in part.interiors)}
                 for part in parts if part.geom_type == "Polygon" and part.area > 0)


def _plane_local_support(geometry, origin):
    """Translate strict world-XY support once while preserving its dimension."""
    from shapely.affinity import translate
    from shapely.geometry import mapping
    from .free_space_field import _support_geometry

    source = _support_geometry(geometry)
    if source is None:
        return None
    return mapping(translate(source, xoff=-origin[0], yoff=-origin[1]))


def _operation_descriptor_is_usable(descriptor: object) -> bool:
    """Check registry shape before query geometry can be constructed."""
    if not isinstance(descriptor, Mapping):
        return False
    return (
        isinstance(descriptor.get("consumer"), str) and bool(descriptor.get("consumer"))
        and descriptor.get("input") in {
            "analysis_geometry_substitute", "physical_occupancy_substitute", "physical_occupancy"
        }
        and descriptor.get("geometry_query") in {
            "plan_projection", "whole_height_planar_mass_patch", "exact_world_plane_section"
        }
        and descriptor.get("fallback") in {"unresolved", "original_without_required_binding"}
        and descriptor.get("coverage") in {"single_source", "declared_exact_source_set"}
        and descriptor.get("substitute_kind") == "MassPatch"
    )


def _occupancy(scene: NeutralSceneV2, request: AnalysisRequest, excluded: set[str],
               domain_geometry) -> tuple[list, list, dict]:
    """Resolve physical owners once and audit their exact plane-local domain relation."""
    from shapely.errors import GEOSException
    from shapely.geometry import shape
    from .analysis_substitute_discovery import resolve_source_representation
    from .geometry_substitutes import mass_patch_from_mesh
    from .geometry_views import component_shape, plan_projection
    from .neutral_scene_views import _is_original_physical_source, _resolved_physical_occupancy
    from .section_views import (QUALIFIED_SECTION_STATUSES, SECTION_ALGORITHM,
                                exact_plane_section, section_record_rejection)

    section_mode = request.geometry_query.kind == "exact_world_xy_section"
    height_band = (request.geometry_query.height_band
                   if request.geometry_query.kind == "finite_height_band" else None)
    query = ({"frame": "world_xy", "units": "m", "world_z_m": request.geometry_query.world_z_m}
             if section_mode else None)
    operation = "physical_occupancy_section" if section_mode else request.operation
    registry = load_substitute_registry()
    operations = registry.get("operations", {}) if isinstance(registry, Mapping) else {}
    operations = operations if isinstance(operations, Mapping) else {}
    descriptor = operations.get(operation)
    effective_descriptor = descriptor
    if isinstance(descriptor, Mapping) and descriptor.get("input") == "physical_occupancy":
        effective_descriptor = operations.get("physical_occupancy")
    descriptor_usable = (_operation_descriptor_is_usable(descriptor)
                         and _operation_descriptor_is_usable(effective_descriptor)
                         and not (isinstance(effective_descriptor, Mapping)
                                  and effective_descriptor.get("input") == "physical_occupancy"))
    effective_consumer = (effective_descriptor.get("consumer")
                          if isinstance(effective_descriptor, Mapping) else None)
    sources = {source.id: source for source in scene.source_objects}
    scoped_out_reasons = {}
    for source in scene.source_objects:
        marker = source.factual_properties.get("analysis_scope_exclusion")
        if isinstance(marker, Mapping) and isinstance(marker.get("reason"), str):
            scoped_out_reasons[source.id] = marker["reason"]
    query_sources = {}
    for source in scene.source_objects if descriptor_usable and isinstance(effective_consumer, str) else ():
        if source.id in excluded or not _is_original_physical_source(source):
            continue
        bindings = source.factual_properties.get("OM_FunctionSubstitutes")
        required = (any(isinstance(item, Mapping) and item.get("consumer") == effective_consumer
                        for item in bindings) if isinstance(bindings, (list, tuple)) else bindings is not None)
        if required:
            # Required bindings select geometry before construction; refusals never revive raw owners.
            resolution = resolve_source_representation(scene, source.id, operation, query=query)
            if resolution["status"] != "accepted" or set(resolution["coverage"]) & excluded:
                continue
            source = sources[resolution["selected_source"]]
        query_sources[source.id] = source
    records, failures = [], []
    for source in query_sources.values():
        meshes = [mesh for ref in source.geometry_refs for mesh in scene.geometries if mesh.id == ref]
        if (not source.geometry_refs or len(set(source.geometry_refs)) != len(source.geometry_refs)
                or len(meshes) != len(source.geometry_refs) or (section_mode and len(meshes) != 1)):
            continue
        try:
            record = {"id": source.id, "_source_geometry_refs": list(source.geometry_refs)}
            if section_mode:
                # Height is absolute world Z; the analysis-plane origin is never added.
                section = exact_plane_section(mass_patch_from_mesh(meshes[0]),
                                              world_z_m=request.geometry_query.world_z_m)
                # Section audit histograms use integer keys; preserve their JSON
                # representation before binding them to the immutable snapshot.
                record.update(section=json.loads(json.dumps(section, allow_nan=False)),
                              section_evidence={"source_object_id": source.id,
                                                "geometry_refs": list(source.geometry_refs),
                                                "query": query, "algorithm": SECTION_ALGORITHM})
            else:
                # The band is expressed in analysis-plane local Z, matching the
                # existing projection contract; omit it for whole-height queries.
                projections = []
                for mesh in meshes:
                    patch = mass_patch_from_mesh(mesh)
                    projection = (plan_projection(patch, request.plane)
                                  if height_band is None else
                                  plan_projection(patch, request.plane, height_band=height_band))
                    projections.append(projection)
                record["geometry_components"] = tuple(
                    component for projection in projections for component in projection.components)
                record["_legal_empty_height_band"] = bool(
                    height_band is not None and projections
                    and all(not projection.components for projection in projections)
                    and all(projection.uncertainty == "no_positive_vertical_overlap_with_height_band"
                            for projection in projections))
            records.append(record)
        except (ValueError, GEOSException) as error:
            failures.append({"source_id": source.id, "reason": str(error)})
    selected, unresolved, inventory = _resolved_physical_occupancy(
        scene, records, excluded, operation=operation, query=query,
        scoped_out_reasons=scoped_out_reasons)
    trusted_supports = {}
    if section_mode:
        records_by_id = {record["id"]: record for record in records}
        for entry in inventory:
            owner = entry["source_object_id"]
            resolution = entry.get("resolution", {})
            target_id = resolution.get("selected_source")
            target = sources.get(target_id)
            record = records_by_id.get(target_id)
            refs = tuple(resolution.get("selected_geometry", ()))
            coverage = tuple(resolution.get("coverage", ()))
            required = tuple(resolution.get("required_coverage", ()))
            if (owner not in unresolved or entry["status"] != "unknown"
                    or resolution.get("status") != "original"
                    or resolution.get("original_source_id") != owner
                    or target_id != owner
                    or resolution.get("query") != query
                    or coverage != (owner,) or required
                    or target is None or record is None or len(refs) != 1
                    or sum(source.id == target_id for source in scene.source_objects) != 1
                    or sum(mesh.id == refs[0] for mesh in scene.geometries) != 1
                    or tuple(target.geometry_refs) != refs
                    or tuple(record.get("_source_geometry_refs", ())) != refs
                    or record.get("section_evidence") != {
                        "source_object_id": target_id, "geometry_refs": list(refs),
                        "query": query, "algorithm": SECTION_ALGORITHM}
                    or entry.get("reason") != section_record_rejection(record, refs, query)):
                continue
            section = record["section"]
            raw_support = section.get("unknown_support_geometry")
            from .free_space_field import _support_geometry
            support = _support_geometry(raw_support)
            if support is None or (support.is_empty and section.get("status") not in QUALIFIED_SECTION_STATUSES):
                continue
            selected_mesh = next((mesh for mesh in scene.geometries if mesh.id == refs[0]), None)
            if selected_mesh is None:
                continue
            # A failed original may use its own hull; a required proxy cannot bound its owner.
            trusted_supports[owner] = {
                "source_object_id": target_id, "selected_owner_ids": (owner,),
                "query_key": _digest(query), "geometry_digest": _digest(selected_mesh.to_dict()),
                "helper_algorithm_version": SECTION_ALGORITHM, "coverage_complete": True,
                "state": "validated_empty" if support.is_empty else "valid_nonempty",
                "geometry": raw_support, "reason": entry["reason"],
            }
    legal_empty, geometry_records, participation = [], [], []
    represented = set()
    for record in selected:
        owners = record["represented_source_ids"]
        represented.update(owners)
        audit = {"selected_source_id": record["id"], "represented_source_ids": owners,
                 "original_sources": [{"source_object_id": owner,
                    "source_id": sources[owner].source_id,
                    "geometry_refs": list(sources[owner].geometry_refs)} for owner in owners],
                 "selected_geometry_refs": record["_source_geometry_refs"],
                 "representation_status": record["representation_status"],
                 "relation": "unevaluated", "intersection_area_m2": None,
                 "participates": False, "field_input": False}
        participation.append(audit)
        if section_mode:
            geometry = shape(record["section"]["occupied_geometry"])
            if geometry.is_empty:
                # Legal empty is qualified evidence, not missing components. Keep
                # it audited outside FreeSpaceField's missing-geometry contract.
                legal_empty.append(record)
                audit["reason"] = "qualified_empty_section"
                continue
            record = {**record, "geometry_components": _components(geometry, request.plane.origin[:2])}
        elif record.get("_legal_empty_height_band"):
            # A valid source wholly outside the requested band is known empty;
            # keep it in the audit trail without handing an empty shape to the field.
            legal_empty.append(record)
            audit["reason"] = "no_positive_vertical_overlap_with_height_band"
            continue
        try:
            footprint = component_shape(record.get("geometry_components", ()))
            if footprint is None:
                audit.update(reason="no_qualified_query_footprint", participates=None)
                unresolved = sorted(set(unresolved) | set(owners))
                continue
            # Contact is inclusive source evidence, but only positive area can
            # occupy a cell. Preserve exact holes and never inflate by tolerance.
            intersection = domain_geometry.intersection(footprint)
            area = float(intersection.area)
            relation = ("disjoint" if intersection.is_empty else
                        "boundary_contact" if area == 0.0 else
                        "inside" if domain_geometry.covers(footprint) else "crossing")
            audit.update(relation=relation, intersection_area_m2=area,
                         participates=relation != "disjoint", field_input=area > 0.0,
                         reason={"disjoint": "disjoint_from_qualified_domain",
                                 "boundary_contact": "boundary_only_domain_contact",
                                 "inside": "positive_area_domain_intersection",
                                 "crossing": "positive_area_domain_intersection"}[relation])
            if area > 0.0:
                geometry_records.append(record)
        except GEOSException as error:
            # A failed relation cannot prove that an owner is outside the domain.
            failures.append({"source_id": record["id"], "reason": str(error)})
            unresolved = sorted(set(unresolved) | set(owners))
            audit.update(reason="domain_intersection_failed", participates=None,
                         geometry_failure_reason=str(error))
    inventory_by_id = {entry["source_object_id"]: entry for entry in inventory}
    failures_by_id = {entry["source_id"]: entry["reason"] for entry in failures}
    selected_ids = {record["id"] for record in selected}
    for source in scene.source_objects:
        if source.id in represented:
            continue
        entry = inventory_by_id.get(source.id)
        if entry is None and source.id in selected_ids:
            # Substitute geometry is already accounted for by its original owners.
            continue
        audit = {**(entry or {"source_object_id": source.id, "source_id": source.source_id,
                             "original_geometry_refs": list(source.geometry_refs)}),
                 "source_role": source.source_role, "relation": "unevaluated",
                 "intersection_area_m2": None, "participates": False, "field_input": False}
        if entry is None:
            audit["reason"] = "nonphysical_source"
        elif entry["status"] == "unknown":
            audit.update(reason="unresolved_query_geometry", participates=None,
                         source_accounting_reason=entry["reason"])
            target_id = entry.get("resolution", {}).get("selected_source") or source.id
            if target_id in failures_by_id:
                audit["geometry_failure_reason"] = failures_by_id[target_id]
        participation.append(audit)
    return geometry_records, unresolved, {"selected_records": selected,
        "legal_empty_sections": legal_empty, "physical_source_inventory": inventory,
        "unknown_source_ids": unresolved, "geometry_failures": failures,
        "trusted_unknown_supports": trusted_supports,
        "projected_domain_participation": participation}


class _RequestField(Field[tuple[int, int], bool]):
    """Frozen query binding around an existing exact-cell occupancy Field."""

    def __init__(self, request, query, delegate, status, explanation, provenance) -> None:
        """Seal the delegate and retain actual section/query evidence on every sample."""
        self._request = request
        self._query = query
        self._delegate = delegate
        self._status = status
        self._explanation = explanation
        self._request_metadata = _MetadataOverlay(provenance)
        self._sample_metadata = (self._request_metadata if delegate is None else
                                 _MetadataOverlay(delegate._sample_metadata, self._request_metadata))
        self._delegate_query = replace(query, plane=None, height_band=None, demand=None)
        super().__init__(domain=None if delegate is None else delegate.domain, frame=query.frame,
                         value_schema="physical_occupancy_bool", representation="exact_cell",
                         provenance=self._request_metadata)
        self._sealed = True

    def __setattr__(self, name, value) -> None:
        """Prevent caller mutation of the snapshot-bound calculation inputs."""
        if getattr(self, "_sealed", False):
            raise AttributeError(f"{name} is immutable")
        super().__setattr__(name, value)

    def __delattr__(self, name) -> None:
        """Prevent deletion from bypassing the frozen input binding."""
        raise AttributeError(f"{name} is immutable")

    def evaluate(self, target: tuple[int, int], query: FieldQuery) -> FieldSample[bool]:
        """Evaluate exact cells only under this run's immutable request query."""
        if not isinstance(query, FieldQuery):
            raise TypeError("query must be FieldQuery")
        lattice = self._request.sampling
        if (query != self._query or not isinstance(target, tuple) or len(target) != 2
                or any(isinstance(item, bool) or not isinstance(item, int) for item in target)
                or not (0 <= target[0] < lattice.n_rows and 0 <= target[1] < lattice.n_cols)):
            return FieldSample(None, FieldStatus.INVALID, query, provenance=self._request_metadata,
                               explanation="target or query does not match this immutable run")
        if self._delegate is None:
            return FieldSample(None, self._status, query, provenance=self._request_metadata,
                               explanation=self._explanation)
        # Geometry has already been qualified for the actual request. The delegate
        # only measures these planar components; it does not infer section semantics.
        sample = self._delegate.evaluate(target, self._delegate_query)
        # Preserve request-over-delegate precedence while freezing only cell-specific changes.
        provenance = {key: value for key, value in sample.provenance.items()
                      if key not in self._delegate.provenance and key not in self.provenance}
        support = {**sample.support, "plane": query.plane, "height_band": query.height_band,
                   "geometry_query": self._request.geometry_query.to_dict()}
        status, explanation = sample.status, sample.explanation
        selected_records = self.provenance.get("selected_records", ())
        if status is FieldStatus.ESTABLISHED and any(
                record["representation_status"] == "accepted" for record in selected_records):
            status = FieldStatus.CONDITIONAL
            explanation = "physical occupancy under accepted substitute query evidence; exact original envelope is not inferred"
        source_ids = sample.source_ids
        if sample.value is False:
            source_ids = tuple(sorted(set(source_ids) | {owner for record in selected_records
                                                       for owner in record["represented_source_ids"]}))
        provenance["support"] = support
        return FieldSample(sample.value, status, query, support=support, source_ids=source_ids,
                           provenance=_MetadataOverlay(self._sample_metadata, provenance), explanation=explanation)


def execute_analysis_request(scene: NeutralSceneV2, request: AnalysisRequest) -> AnalysisRun:
    """Execute one planar request without mutating facts, bindings, IFC or other runs."""
    fingerprint, key, versions = _run_identity(scene, request)
    frame = f"analysis-plane:{request.plane.identity}:{request.plane.revision}"
    query = FieldQuery(domain_id=request.domain.id if request.domain else None, frame=frame,
                       plane={**request.plane.to_dict(), "normal": request.plane.basis[2], "units": "m"},
                       height_band=request.geometry_query.height_band, demand=request.demand,
                       tolerance=request.geometry_tolerance, revision=key)
    reason = _unsupported_reason(scene, request)
    provenance = {"algorithm_version": REQUEST_VERSION, "schema_version": REQUEST_VERSION,
                  "semantic_key": key, "source_fingerprint": fingerprint,
                  "project_source_identity": scene.context.world_coordinate_system,
                  "geometry_query": request.geometry_query.to_dict(), "backend_versions": versions,
                  "height_band_datum": request.height_band_datum,
                  "geometry_tolerance": request.geometry_tolerance,
                  "topology_tolerance": request.topology_tolerance,
                  "section_thickness_m": 0.0 if request.geometry_query.kind == "exact_world_xy_section" else None}
    delegate = None
    status = FieldStatus.NOT_AVAILABLE
    if not reason:
        # A private context satisfies the existing equality guard while leaving the
        # shared factual scene's selected plane/domain untouched for other requests.
        child = replace(scene, context=replace(scene.context, analysis_plane=request.plane,
                        geometry_tolerance=request.geometry_tolerance,
                        topology_tolerance=request.topology_tolerance), analysis_domain=request.domain)
        try:
            domain_geometry, domain_audit = _qualified_domain(child, request)
            provenance["domain_handoff"] = domain_audit
            if domain_geometry is None:
                reason = "exact domain unavailable: " + str(domain_audit.get("reason", "qualification failed"))
            else:
                from shapely.geometry import shape
                from .free_space_field import FreeSpaceField

                excluded, scope_audit = _scope_exclusions(child)
                domain_polygon = shape(domain_geometry)
                records, unresolved, occupancy_audit = _occupancy(child, request, excluded, domain_polygon)
                provenance.update(scope_audit)
                provenance.update(occupancy_audit)
                lattice = request.sampling
                local_supports = {}
                for owner, evidence in occupancy_audit["trusted_unknown_supports"].items():
                    local_geometry = _plane_local_support(evidence["geometry"], request.plane.origin[:2])
                    if local_geometry is not None:
                        local_supports[owner] = {**evidence, "geometry": local_geometry}
                delegate = FreeSpaceField(domain={"id": request.domain.id, "frame": frame,
                                         "components": _components(domain_polygon)},
                    origin=lattice.origin, spacing=lattice.spacing, n_rows=lattice.n_rows, n_cols=lattice.n_cols,
                    physical_occupancy=records, unresolved_source_ids=unresolved,
                    unresolved_supports=local_supports,
                    query_context={"domain_id": request.domain.id, "frame": frame}, frame=frame,
                    origin_offset=(0.0, 0.0))
                accepted = any(record["representation_status"] == "accepted"
                               for record in occupancy_audit["selected_records"])
                status = (FieldStatus.UNKNOWN if unresolved else FieldStatus.CONDITIONAL if accepted
                          else FieldStatus.ESTABLISHED)
                reason = ("unresolved physical owners; known occupied evidence remains queryable" if unresolved else
                          "accepted source substitute evidence; no original-envelope or clearance certificate" if accepted else
                          "qualified physical occupancy; no walkability or clearance certificate")
        except ImportError as error:
            reason = f"calculation backend unavailable: {error}"
    provenance.update(support_status=status.value, explanation=reason)
    snapshot = AnalysisSnapshot(key, fingerprint, request, versions, provenance)
    result_field = _RequestField(request, query, delegate, status, reason, snapshot.provenance)
    return AnalysisRun(result_field, query, snapshot, status, reason)

