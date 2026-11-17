"""Independent structural B4 service and exact request-scoped geometry handoff."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import isfinite
from dataclasses import fields
from pathlib import Path
import argparse
from contextlib import nullcontext
from hashlib import sha256
from time import perf_counter

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from . import blender_analysis_result_wire as wire
from .blender_analysis_result_wire import (ResultRef, ResultMetadata, ResultReadContext,
    ReadOnlyResultSnapshot, ValidatedAnalysisResult, list_analysis_results, open_analysis_result,
    validate_analysis_result, write_result_atomic)

from .blender_analysis_capture import digest, freeze, plain
from .bonsai_live import (authored_space_domain, structural_b4_view, validate_support_binding,
                          source_capture_fingerprint, numeric_source_facts,
                          validate_legacy_applicability, geometry_digest)
try:
    from ..features.cache_paths import CacheAddress, SidecarLocator, SourceBinding
    from ..features.cache_store import CacheStore
    from ..features.evidence_package_storage import load_bound_store_entry, adopt_legacy_store_payload
except ImportError:
    from features.cache_paths import CacheAddress, SidecarLocator, SourceBinding
    from features.cache_store import CacheStore
    from features.evidence_package_storage import load_bound_store_entry, adopt_legacy_store_payload

if "." in (__package__ or ""):
    from ..features import analysis_requests as requests
    from ..features._analysis_domain_handoff import domain_handoff, structural_source_facts, _project_authored
    from ..features.affordance.models import Polygon as AffordancePolygon, Rect as AffordanceRect
    from ..features.analysis_requests import WORLD_XY_BASIS
    from ..features.geometry_views import _project_to_plane
    from ..features.scene_contract import AnalysisDomain, AnalysisPlane, MeshGeometry3D
    from ..features.neutral_scene_views import _analysis_scene_view_with_semantic_enclosure
else:
    from features import analysis_requests as requests
    from features._analysis_domain_handoff import domain_handoff, structural_source_facts, _project_authored
    from features.affordance.models import Polygon as AffordancePolygon, Rect as AffordanceRect
    from features.analysis_requests import WORLD_XY_BASIS
    from features.geometry_views import _project_to_plane
    from features.scene_contract import AnalysisDomain, AnalysisPlane, MeshGeometry3D
    from features.neutral_scene_views import _analysis_scene_view_with_semantic_enclosure


def _transport(value):
    """Serialize the closed Domain transport set without arbitrary object fallback."""
    if isinstance(value, AffordanceRect):
        fields = {"cx": value.cx, "cy": value.cy, "width": value.width, "height": value.height}
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) or not isfinite(item)
               for item in fields.values()):
            raise ValueError("Rect coordinates and dimensions must be finite numbers")
        return fields
    if isinstance(value, AffordancePolygon):
        points = []
        for point in value.points:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError("Polygon points must be coordinate pairs")
            if any(isinstance(item, bool) or not isinstance(item, (int, float)) or not isfinite(item)
                   for item in point):
                raise ValueError("Polygon point coordinates must be finite numbers")
            points.append([float(point[0]), float(point[1])])
        return {"points": points}
    if isinstance(value, (AnalysisDomain, MeshGeometry3D)):
        return _transport(value.to_dict())
    if isinstance(value, Mapping):
        return {key: _transport(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_transport(item) for item in value]
    if value is None or type(value) in (bool, str, int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("Domain transport contains a non-finite float")
        return value
    raise ValueError("unsupported Domain transport value: " + type(value).__name__)


@dataclass(frozen=True)
class DomainSessionResult(Mapping):
    """Immutable B4 facts with exact in-memory domain mesh objects retained."""

    payload: Mapping

    def __post_init__(self):
        """Detach nested service facts while retaining immutable scene records."""
        object.__setattr__(self, "payload", freeze(self.payload))

    def __getitem__(self, key):
        """Expose the existing B4 mapping contract to callers."""
        return self.payload[key]

    def __iter__(self):
        """Iterate the preserved authoritative payload fields."""
        return iter(self.payload)

    def __len__(self):
        """Report the number of payload fields."""
        return len(self.payload)

    def to_dict(self):
        """Return a strict data-only defensive copy with exact geometry records."""
        return _transport(self.payload)


def tolerance_m2(value):
    """Convert a finite nonnegative UI square-millimetre tolerance exactly once."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise ValueError("residual tolerance must be a finite nonnegative number of mm²")
    return float(value) / 1_000_000


def _source_xy_bounds(scene, source, plane):
    """Return complete plane-local XY bounds, or None when exclusion is not provable."""
    geometries = {}
    for geometry in scene.geometries:
        geometries.setdefault(geometry.id, []).append(geometry)
    if not source.geometry_refs:
        return None
    points = []
    for ref in source.geometry_refs:
        matches = geometries.get(ref, ())
        if len(matches) != 1 or matches[0].units != "m" or not matches[0].vertices:
            return None
        try:
            points.extend(_project_to_plane(vertex, plane)[:2] for vertex in matches[0].vertices)
        except (TypeError, ValueError):
            return None
    if not points or not all(isfinite(value) for point in points for value in point):
        return None
    return (min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points))


def _geometry_xy_bounds(scene, geometry_refs, plane):
    """Return complete plane-local bounds for opening geometry, retaining unknowns."""
    class GeometryOwner:
        """Expose only geometry refs to the shared conservative bounds reader."""

        def __init__(self, refs):
            """Freeze opening geometry refs for one bounds query."""
            self.geometry_refs = tuple(refs)

    return _source_xy_bounds(scene, GeometryOwner(geometry_refs), plane)


def _bounds_overlap(bounds, target_bounds):
    """Conservatively reject only bounds proven disjoint in plane-local XY."""
    if bounds is None or target_bounds is None:
        return True
    return not (bounds[2] < target_bounds[0] or target_bounds[2] < bounds[0]
                or bounds[3] < target_bounds[1] or target_bounds[3] < bounds[1])


def _scene_subset(scene, sources, openings):
    """Retain complete source and opening meshes for one B4-only child."""
    refs = {ref for source in sources for ref in source.geometry_refs}
    refs.update(ref for opening in openings for ref in opening.geometry_refs)
    if scene.analysis_domain is not None:
        refs.update(scene.analysis_domain.geometry_refs)
    return replace(scene, source_objects=tuple(sorted(sources, key=lambda source: source.id)),
                   openings=tuple(sorted(openings, key=lambda opening: opening.id)),
                   geometries=tuple(sorted((mesh for mesh in scene.geometries if mesh.id in refs),
                                           key=lambda mesh: mesh.id)))


def _opening_relation_refs(opening):
    """Return canonical hosts and fillings without inferring missing relations."""
    return set(opening.host_refs).union(opening.provenance.get("filling_source_refs", ()))


def _selected_perimeter_child(scene, selected_wall_refs, plane):
    """Build a seed child from selected walls and conservatively relevant non-wall evidence."""
    selected = []
    for ref in selected_wall_refs:
        matches = [source for source in scene.source_objects if source.id == ref]
        if len(matches) != 1:
            raise ValueError(f"selected wall source is unavailable or ambiguous: {ref}")
        source = matches[0]
        if source.source_role != "wall":
            raise ValueError(f"selected wall source is not an IfcWall: {ref}")
        selected.append(source)
    selected_bounds = [_source_xy_bounds(scene, source, plane) for source in selected]
    if any(bounds is None for bounds in selected_bounds):
        raise ValueError("selected wall source has missing or ambiguous geometry bounds")
    envelope = (min(bounds[0] for bounds in selected_bounds), min(bounds[1] for bounds in selected_bounds),
                max(bounds[2] for bounds in selected_bounds), max(bounds[3] for bounds in selected_bounds))
    selected_ids = set(selected_wall_refs)
    openings = []
    for opening in scene.openings:
        related = bool(selected_ids.intersection(_opening_relation_refs(opening)))
        bounds = _geometry_xy_bounds(scene, opening.geometry_refs, plane)
        if related or _bounds_overlap(bounds, envelope):
            openings.append(opening)
    related_ids = {ref for opening in openings for ref in _opening_relation_refs(opening)}
    sources = list(selected)
    for source in scene.source_objects:
        if source.id in selected_ids or source.source_role == "wall":
            continue
        bounds = _source_xy_bounds(scene, source, plane)
        if source.id in related_ids or _bounds_overlap(bounds, envelope):
            sources.append(source)
    return _scene_subset(scene, sources, openings)


def _qualified_work_area(seed_b2, selected_wall_refs):
    """Require usable selected walls and actual closed scopes without unresolved apertures."""
    rows = {row["source_ref"]: row for row in seed_b2["sources"]}
    if any(ref not in rows or not rows[ref]["enclosure_support_eligible"] for ref in selected_wall_refs):
        raise ValueError("selected wall source is not usable at the B4 query")
    scopes = [scope for scope in seed_b2["scope_proposals"]
              if not scope["local_unresolved_aperture_refs"]]
    polygons = [shape(scope["geometry"]["geojson"]) for scope in scopes]
    if not polygons:
        raise ValueError("selected walls do not define a qualified enclosed scope")
    work_area = unary_union(polygons)
    if work_area.is_empty or not work_area.is_valid:
        raise ValueError("selected wall work area is invalid")
    return work_area


def _local_structural_child(scene, work_area, plane, selected_wall_refs):
    """Keep full structural sources whose cheap bounds may affect the selected work area."""
    target_bounds = work_area.bounds
    selected_ids = set(selected_wall_refs)
    sources = [source for source in scene.source_objects
               if source.id in selected_ids
               or _bounds_overlap(_source_xy_bounds(scene, source, plane), target_bounds)]
    source_ids = {source.id for source in sources}
    openings = [opening for opening in scene.openings
                if source_ids.intersection(_opening_relation_refs(opening))
                or _bounds_overlap(_geometry_xy_bounds(scene, opening.geometry_refs, plane), target_bounds)]
    related_ids = {ref for opening in openings for ref in _opening_relation_refs(opening)}
    sources = [source for source in scene.source_objects
               if source.id in source_ids or source.id in related_ids]
    return _scene_subset(scene, sources, openings)


def _covered_b2(b2, work_area):
    """Retain complete candidate polygons covered by the work area without clipping."""
    scopes = [scope for scope in b2["scope_proposals"]
              if work_area.covers(shape(scope["geometry"]["geojson"]))]
    scope_ids = {scope["id"] for scope in scopes}
    contours = [contour for contour in b2["enclosure_contours"] if contour.get("scope_ref") in scope_ids]
    contour_ids = {contour["id"] for contour in contours}
    apertures = [{**item,
                  "affected_scope_ids": [ref for ref in item["affected_scope_ids"] if ref in scope_ids],
                  "affected_contour_ids": [ref for ref in item["affected_contour_ids"] if ref in contour_ids]}
                 for item in b2["apertures"]]
    treatments = [{**item,
                   "affected_scope_ids": [ref for ref in item["affected_scope_ids"] if ref in scope_ids],
                   "affected_contour_ids": [ref for ref in item["affected_contour_ids"] if ref in contour_ids]}
                  for item in b2["treatments"]]
    if not scopes:
        raise ValueError("selected wall scope produced no complete covered interior")
    return {**b2, "scope_proposals": scopes, "enclosure_contours": contours,
            "apertures": apertures, "treatments": treatments}


def _selected_wall_b4(scene, context, request):
    """Run the existing B4 twice while sectioning only conservatively local geometry."""
    seed = _selected_perimeter_child(scene, context.selected_wall_refs, context.analysis_plane)
    started = perf_counter()
    seed_b2 = _analysis_scene_view_with_semantic_enclosure(
        seed, request=request)["_analysis_view"]["b2_boundary_diagnostics"]["semantic_enclosure"]
    seed_seconds = perf_counter() - started
    work_area = _qualified_work_area(seed_b2, context.selected_wall_refs)
    local = _local_structural_child(scene, work_area, context.analysis_plane, context.selected_wall_refs)
    started = perf_counter()
    local_b2 = _analysis_scene_view_with_semantic_enclosure(
        local, request=request)["_analysis_view"]["b2_boundary_diagnostics"]["semantic_enclosure"]
    local_seconds = perf_counter() - started
    return local, _covered_b2(local_b2, work_area), {
        "selected_wall_refs": context.selected_wall_refs,
        "work_area": mapping(work_area),
        "base_source_count": len(scene.source_objects),
        "base_geometry_count": len(scene.geometries),
        "seed_source_count": len(seed.source_objects),
        "seed_geometry_count": len(seed.geometries),
        "local_source_count": len(local.source_objects),
        "local_geometry_count": len(local.geometries),
        "seed_b4_seconds": seed_seconds,
        "local_b4_seconds": local_seconds,
    }


def _authored_space_revision(scene, context, domain, storey_ref):
    """Bind Space consent to its exact source, mesh and explicit storey scope."""
    structural = structural_b4_view(scene, context=context, storey_ref=storey_ref)
    domain_meshes = [mesh.to_dict() for ref in domain.geometry_refs
                     for mesh in scene.geometries if mesh.id == ref]
    return digest({"structural": structural_source_facts(structural),
                   "domain_meshes": domain_meshes,
                   "authored_space_domain": domain.to_dict(), "storey_ref": storey_ref})


def _authored_space_request_child(scene, domain):
    """Mark proven other-storey, vertically disjoint sources out of one request child.

    The complete captured scene remains the identity and validation authority. This
    child-only annotation lets the existing occupancy resolver emit its normal
    ``scoped_out`` inventory rows while retaining ambiguous, crossing, uncontained,
    and missing-geometry sources conservatively.
    """
    if (domain is None or domain.selection_method != "explicit_bonsai_ifcspace"
            or not domain.source_id):
        return scene
    storey_ref = domain.provenance.get("level_ref")
    if not isinstance(storey_ref, str) or not storey_ref:
        return scene
    domain_sources = [source for source in scene.source_objects if source.source_id == domain.source_id]
    if len(domain_sources) != 1 or len(domain.geometry_refs) != 1:
        return scene
    domain_meshes = [mesh for mesh in scene.geometries if mesh.id in domain.geometry_refs]
    if len(domain_meshes) != 1 or not domain_meshes[0].vertices:
        return scene
    try:
        domain_z = [float(vertex[2]) for vertex in domain_meshes[0].vertices
                    if len(vertex) >= 3 and all(isfinite(float(item)) for item in vertex[:3])]
    except (TypeError, ValueError):
        return scene
    if not domain_z:
        return scene
    domain_min, domain_max = min(domain_z), max(domain_z)
    try:
        from ..features.neutral_scene_views import _is_original_physical_source
    except ImportError:
        from features.neutral_scene_views import _is_original_physical_source
    scoped = {}
    for source in scene.source_objects:
        if source.source_id == domain.source_id or not _is_original_physical_source(source):
            continue
        # A level mismatch alone is insufficient: uncontained and contradictory
        # spatial facts stay in the child so the resolver can report them.
        if (source.level_ref is None or source.level_ref == storey_ref
                or not source.container_refs
                or tuple(dict.fromkeys(source.container_refs)) != (source.level_ref,)):
            continue
        meshes = [mesh for ref in source.geometry_refs for mesh in scene.geometries if mesh.id == ref]
        if not source.geometry_refs or len(meshes) != len(source.geometry_refs):
            continue
        try:
            z_values = [float(vertex[2]) for mesh in meshes for vertex in mesh.vertices
                        if len(vertex) >= 3 and all(isfinite(float(item)) for item in vertex[:3])]
        except (TypeError, ValueError):
            continue
        if len(z_values) != sum(len(mesh.vertices) for mesh in meshes):
            continue
        source_min, source_max = min(z_values), max(z_values)
        if source_max < domain_min or source_min > domain_max:
            scoped[source.id] = "authored_space_other_storey_z_disjoint"
    if not scoped:
        return scene
    marked = tuple(replace(source, factual_properties={
        **source.factual_properties,
        "analysis_scope_exclusion": {"reason": scoped[source.id], "domain_source_id": domain.source_id,
                                      "storey_ref": storey_ref},
    }) if source.id in scoped else source for source in scene.source_objects)
    return replace(scene, source_objects=marked)


def _support_candidates(scene, *, storey_ref):
    """Expose only exact same-storey floor facts for explicit user selection."""
    return tuple({"source_id": source.source_id, "source_object_id": source.id,
                  "source_class": source.source_class, "storey_ref": source.level_ref,
                  "geometry_refs": tuple(source.geometry_refs),
                  "geometry_digest": geometry_digest(scene, source)}
                 for source in scene.source_objects
                 if source.source_role in {"slab", "floor"} and source.source_id
                 and source.level_ref == storey_ref and source.geometry_refs)


def _support_binding_from_source(scene, *, source_id, storey_ref, confirmation_id):
    """Mint one request-local binding from an explicitly selected current floor."""
    matches = [source for source in scene.source_objects if source.source_id == source_id]
    if len(matches) != 1:
        raise ValueError("support source identity is missing or ambiguous")
    source = matches[0]
    if source.source_role not in {"slab", "floor"} or source.level_ref != storey_ref:
        raise ValueError("support source must be a same-storey floor or slab")
    if not source.geometry_refs:
        raise ValueError("support source geometry is unavailable")
    project = scene.context.world_coordinate_system.get("project_global_id")
    if not isinstance(confirmation_id, str) or not confirmation_id:
        raise ValueError("support selection requires the confirmation action identity")
    if "." in (__package__ or ""):
        from .bonsai_live import SupportBinding
    else:
        from adapters.bonsai_live import SupportBinding
    return SupportBinding(source.id, project, source.source_class, source.geometry_refs,
                          geometry_digest(scene, source), source_capture_fingerprint(scene), confirmation_id)


def evaluate_domain_request(scene, *, context, prior, action, domain_source_id=None,
                            storey_ref=None, support_source_id=None, space_binding=None):
    """Run existing structural diagnostics/reducer without a free-space request."""
    if storey_ref is not None and context.storey_ref is not None and storey_ref != context.storey_ref:
        raise ValueError("selected storey conflicts with the frozen structural context")
    storey_ref = storey_ref or context.storey_ref
    authored_domain = None
    full_scene = scene
    if context.selected_wall_refs and (domain_source_id is not None or scene.analysis_domain is not None):
        raise ValueError("selected wall scope cannot be combined with an authored IfcSpace")
    if domain_source_id is not None:
        authored_domain = authored_space_domain(scene, domain_source_id, storey_ref=storey_ref)
        # Keep the domain mesh in the existing B4 reducer view, while source
        # identity remains in the full request child for occupancy exclusion.
        scene = replace(scene, analysis_domain=authored_domain)
    from .bonsai_live import authored_space_composition
    space_binding = (authored_space_composition(full_scene, domain_source_id, storey_ref=storey_ref, previous=space_binding)
                     if authored_domain is not None else None)
    scene = structural_b4_view(scene, context=context, storey_ref=storey_ref)
    base_scene = scene
    parameters = context.b4_parameters
    tolerance = parameters.get("tolerance_mm2", 1.)
    frame = {"analysis_plane": context.analysis_plane, "units": "m",
             "datum_m": context.datum_z_m, "cut_height_m": context.cut_z_m - context.datum_z_m}
    identity = dict(scene.context.world_coordinate_system)
    request = frame | {"contact_distance_m": parameters.get("contact_distance_m", 1e-6),
        "aperture_area_budget_m2": parameters.get("aperture_area_budget_m2", 1e-6),
        "aperture_residual_tolerance_m2": tolerance_m2(tolerance),
        "source_ifc_path": identity.get("ifc_source_identity", identity.get("ifc_path")),
        "source_project_global_id": identity.get("project_global_id"),
        "default_closed_authority": "B4 user-authorized closed door/window scenario; state not observed",
        "exclude_override_authority": "B4 task-only structural/window/door enclosure; source exclusion retained"}
    selected_wall_scope = None
    if authored_domain is not None:
        # Native Space geometry is authoritative; unrelated inferred rooms cannot veto its adoption.
        b2 = None
    elif context.selected_wall_refs:
        scene, b2, selected_wall_scope = _selected_wall_b4(base_scene, context, request)
    else:
        b2 = _analysis_scene_view_with_semantic_enclosure(
            scene, request=request)["_analysis_view"]["b2_boundary_diagnostics"]["semantic_enclosure"]
    previous = prior or {}
    source_revision = (_authored_space_revision(base_scene, context, authored_domain, storey_ref)
                       if authored_domain is not None else digest(structural_source_facts(base_scene)))
    # `domain_handoff` already catalogs `scene.analysis_domain`; passing it again
    # would create a duplicate candidate version.
    candidates = ()
    result = domain_handoff(scene, candidates=candidates, session_state=plain(previous.get("session_state")),
        action=action, expected_session_revision=previous.get("session_revision"),
        expected_source_revision=(previous.get("provenance") or {}).get("source_revision"),
        frame_request=frame, b2=b2, b2_request=request if b2 is not None else None,
        source_revision=source_revision, frame_id=context.structural_frame_key)
    candidate_payloads = []
    for item in result["candidates"]:
        polygon = shape(item["outline"]) if item["outline"] else None
        candidate_payloads.append(item | {"area_m2": polygon.area if polygon is not None else None,
            "holes": len(polygon.interiors) if polygon is not None else None,
            "label_xy": list(polygon.representative_point().coords[0]) if polygon is not None else None,
            **({"selected_wall_refs": context.selected_wall_refs} if context.selected_wall_refs else {}),
            **({"storey_ref": storey_ref} if storey_ref is not None else {}),
            **({"source_id": domain_source_id, "domain_kind": "authored_ifcspace"}
               if authored_domain is not None else {})})
    binding = result["session_state"]["current_binding"] if result["current"]["status"] == "active" else None
    support_binding = None
    if (authored_domain is not None and result["attempt"]["status"] == "accepted"
            and isinstance(action, Mapping) and action.get("kind") == "confirm"
            and support_source_id is not None):
        support_binding = _support_binding_from_source(
            full_scene, source_id=support_source_id, storey_ref=storey_ref,
            confirmation_id=action.get("action_id"))
    return DomainSessionResult(result | {"candidates": candidate_payloads, "events": result["session_state"]["events"],
        "domain_request_identity": result["provenance"]["request_id"], "confirmation_binding": binding,
        "status": result["current"]["status"], "handoff_executed": bool(result["domain_geometries"]),
        "b4_diagnostics": b2, "apertures": [aperture | {"area_m2": aperture["geometry"]["area_m2"]}
                                            for aperture in (b2 or {}).get("apertures", ())],
        "ignored_tiny_residual_count": sum(not aperture["significant_residual"] for aperture in (b2 or {}).get("apertures", ())),
        "source_count": len(scene.source_objects), "geometry_count": len(scene.geometries),
        "source_identity": identity, "scenario": ("native IfcSpace; B4 not requested" if authored_domain is not None else
                                                   "default closed doors/windows; observed leaf states unknown"),
        "tolerance_mm2": tolerance,
        "authored_domain": (authored_domain.to_dict() if authored_domain is not None else None),
        "space_binding": space_binding,
        "support_candidates": _support_candidates(full_scene, storey_ref=storey_ref) if authored_domain is not None else (),
        "support_binding": support_binding.__dict__ if support_binding is not None else None,
        "support_status": ("selected" if support_binding is not None else "unbound") if authored_domain is not None else "not_applicable",
        **({"selected_wall_scope": selected_wall_scope} if selected_wall_scope is not None else {})})


def _activate_legacy_proxies(scene, request):
    """Activate checked pending representations only for an exact applicable request."""
    if request.domain is None or request.plane.basis != WORLD_XY_BASIS:
        return scene
    sources = {source.id: source for source in scene.source_objects}
    if len(sources) != len(scene.source_objects):
        return scene
    world_plane = AnalysisPlane(name="Legacy scope world XY", origin=(0, 0, 0), basis=WORLD_XY_BASIS)
    world_scene = replace(scene, context=replace(scene.context, analysis_plane=world_plane))
    try:
        actual_scope = _project_authored(world_scene, request.domain)
    except ValueError:
        return scene
    activated = {}
    for proxy in scene.source_objects:
        pending = proxy.factual_properties.get("pending_legacy_occupancy")
        if not isinstance(pending, Mapping):
            continue
        try:
            scope = pending["scope"]
            footprint, query = validate_legacy_applicability(scope)
            owners = tuple(pending["covered_owner_ids"])
            refs = tuple(pending["geometry_refs"])
            meshes = [mesh for ref in refs for mesh in scene.geometries if mesh.id == ref]
            if (scope["applicability"]["operation"] != request.operation or query != request.geometry_query
                    or not footprint.equals(actual_scope) or not owners or len(set(owners)) != len(owners)
                    or set(pending["owner_geometry"]) != set(owners)
                    or pending["capture_identity"] != scene.context.world_coordinate_system
                    or len(refs) != 1 or len(meshes) != 1
                    or digest([meshes[0].to_dict()]) != pending["proxy_geometry_digest"]
                    or set(owners) & activated.keys()):
                continue
            for owner_id in owners:
                owner, expected = sources[owner_id], pending["owner_geometry"][owner_id]
                original = replace(owner, geometry_refs=tuple(expected["geometry_refs"]))
                if (owner.geometry_refs or owner.source_id != expected["source_id"]
                        or owner.source_class != expected["source_class"]
                        or owner.provenance["step_id"] != expected["step_id"]
                        or geometry_digest(scene, original) != expected["geometry_digest"]):
                    raise ValueError("pending_legacy_owner_changed")
        except (KeyError, TypeError, ValueError):
            continue
        # The shared resolver receives its existing declarations only in this child.
        activated[proxy.id] = replace(proxy, geometry_refs=refs, uncertainties=(),
            factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": owners},
                                "furniture_analysis_participation": "excluded"})
        for owner_id in owners:
            owner = sources[owner_id]
            binding = {"consumer": "physical_occupancy", "source_object_id": owner_id,
                "substitute_id": proxy.id, "substitute_kind": "MassPatch", "analysis_role": "physical_occupancy_substitute",
                "representation_identifier": "GeneratedProxy",
                "provenance": {"representation_identifier": "GeneratedProxy", "scope": plain(scope)}}
            activated[owner_id] = replace(owner, geometry_refs=tuple(pending["owner_geometry"][owner_id]["geometry_refs"]),
                factual_properties={**owner.factual_properties,
                "OM_FunctionSubstitutes": [binding], "furniture_analysis_participation": "excluded"},
                uncertainties=tuple(item for item in owner.uncertainties if item.operation != "legacy_scope_pending"))
    return replace(scene, source_objects=tuple(activated.get(source.id, source) for source in scene.source_objects))


def _prepare_live_analysis(scene, *, request, domain_geometries, support_binding=None):
    """Validate frozen inputs and compose scope without projection or field generation."""
    if request.height_band_datum is not None:
        from .bonsai_space_authoring import validate_captured_slab_datum
        # Native form observation precedes frozen capture; refuse a raced floor before calculation.
        validate_captured_slab_datum(scene, request.height_band_datum)
    meshes = tuple(domain_geometries)
    domain = request.domain
    refs = tuple(mesh.id for mesh in meshes)
    if domain is None:
        if meshes:
            raise ValueError("domain geometry requires an explicit domain")
    elif not refs or len(set(refs)) != len(refs) or set(refs) != set(domain.geometry_refs):
        raise ValueError("exact qualified domain geometry refs required")
    for mesh in meshes:
        existing = [item for item in scene.geometries if item.id == mesh.id]
        if len(existing) > 1 or any(item != mesh for item in existing):
            raise ValueError("domain geometry conflicts with captured source")
    audit = validate_support_binding(scene, support_binding,
                                     capture_fingerprint=source_capture_fingerprint(scene))
    # Support consent changes only request-local occupancy scope. The authored
    # Space identity remains the domain source; a validated floor is an exact
    # boundary member, never a broad slab-class exemption.
    if domain is not None and audit["status"] == "validated" and domain.source_id is None:
        domain = replace(domain, source_id=audit["source_id"])
    elif domain is not None and audit["status"] == "validated":
        members = list(domain.provenance.get("boundary_member_source_ids", ()))
        if audit["source_id"] not in members:
            members.append(audit["source_id"])
        domain = replace(domain, provenance={**domain.provenance,
            "boundary_member_source_ids": tuple(members),
            "support_binding_audit": dict(audit)})
    child = replace(scene, context=replace(scene.context, analysis_plane=request.plane), analysis_domain=domain,
                    geometries=tuple(mesh for mesh in scene.geometries if mesh.id not in refs) + meshes)
    child = _authored_space_request_child(child, domain)
    scoped_request = replace(request, domain=domain)
    return child, scoped_request


def execute_live_analysis(scene, *, request, domain_geometries, support_binding=None):
    """Compose only the confirmed exact meshes and use the existing request executor."""
    child, scoped_request = _prepare_live_analysis(scene, request=request,
        domain_geometries=domain_geometries, support_binding=support_binding)
    child = _activate_legacy_proxies(child, scoped_request)
    return requests.execute_analysis_request(child, scoped_request)


CONTENT_CACHE_VERSION = 1
CONTENT_CACHE_DIRECTORY = Path(__file__).resolve().parents[1] / "outputs/blender_analysis/content_cache/v1"
CONTENT_IMPLEMENTATIONS = ("adapters/blender_analysis_session.py", "adapters/blender_analysis_result_wire.py",
    "adapters/blender_analysis_capture.py", "adapters/bonsai_live.py", "adapters/ifc_bonsai.py",
    "adapters/bonsai_space_authoring.py", "adapters/bonsai_analysis_plane.py",
    "blender_addon/order_analyzer_ui/runtime.py", "blender_addon/order_analyzer_ui/__init__.py",
    "pixi.toml", "pixi.lock")


def _content_cache_key(scene, request, binding, support_binding, *, versions=None,
                       implementation_hashes=None, numeric_projection=True):
    """Hash complete preactivation facts separately from current publication tokens."""
    # The old executor fingerprint omits pending legacy and containment/scope facts.
    # Use the full capture recipe before activation can hide any of those inputs.
    projected = numeric_source_facts(scene) if numeric_projection else None
    support_facts = None if support_binding is None else dict(support_binding.__dict__)
    domain_facts = None if request.domain is None else request.domain.to_dict()
    confirmation = binding.get("confirmation_binding") or {}
    confirmation_facts = {key: value for key, value in confirmation.items() if key != "request_id"}
    if numeric_projection:
        # Current support consent is validated before this key is reachable.
        # Its audit token may change after reconfirmation without changing the
        # exact selected floor, mesh or request-local boundary membership.
        if support_facts is not None:
            for key in ("capture_fingerprint", "confirmation_id"):
                support_facts.pop(key, None)
        if domain_facts is not None:
            audit = domain_facts.get("provenance", {}).get("support_binding_audit")
            if isinstance(audit, Mapping):
                domain_facts["provenance"]["support_binding_audit"] = {
                    key: value for key, value in audit.items() if key != "confirmation_id"}
        if confirmation:
            # The exact domain facts carry the selected topology.  These full
            # capture/reducer receipt hashes are checked before lookup, then
            # retain their role as consent audit rather than numerical inputs.
            confirmation_facts = {"selected": True,
                "acknowledged_conflicts": confirmation.get("acknowledged_conflicts", ())}
    facts = {"identity": (scene.context.to_dict() if projected is None else projected["context"]),
        "sources": ([source.to_dict() for source in scene.source_objects]
                    if projected is None else projected["sources"]),
        "geometries": ([mesh.to_dict() for mesh in scene.geometries]
                       if projected is None else projected["geometries"]),
        "openings": ([opening.to_dict() for opening in scene.openings]
                     if projected is None else projected["openings"]),
        "authored_groups": [group.to_dict() for group in scene.authored_groups],
        "domain": domain_facts,
        "support_binding": support_facts,
        "confirmation_selection": confirmation_facts,
        "domain_source_id": binding.get("domain_source_id"), "storey_ref": binding.get("storey_ref")}
    del facts["identity"]["analysis_plane"]
    source_rows = facts["sources"]
    pending = [source["factual_properties"]["pending_legacy_occupancy"] for source in source_rows
               if isinstance(source.get("factual_properties", {}).get("pending_legacy_occupancy"), Mapping)]
    if pending:
        # These exact digest/equality receipts affect activation even when nested keys look presentational.
        facts["legacy_validation_digest"] = digest({"pending": pending,
            "identity": facts["identity"]["world_coordinate_system"], "meshes": facts["geometries"]})
    versions = requests._backend_versions() if versions is None else versions
    root = Path(__file__).resolve().parents[1]
    implementations = ({path: sha256((root / path).read_bytes()).hexdigest()
                        for path in CONTENT_IMPLEMENTATIONS}
                       if implementation_hashes is None else implementation_hashes)
    backend = {"schema": wire.SCHEMA_VERSION, "algorithm": wire.ALGORITHM_VERSION,
        "cache": CONTENT_CACHE_VERSION,
        "implementations": implementations}
    normalized = replace(request, plane=replace(request.plane, revision=1))
    fingerprint = digest(requests._semantic_json({"facts": facts, "backend": backend}))
    return requests._request_key(fingerprint, normalized, versions), versions


def _legacy_content_cache_key(scene, request, binding, support_binding):
    """Rebuild the reviewed historical key from independently supplied current facts."""
    profile = requests._legacy_cache_compatibility_profile()
    if profile is None or requests.legacy_backend_compatibility(profile["original_backend_versions"]) is None:
        return None
    try:
        implementations = {path: profile["original_content_implementations"][path]
                           for path in CONTENT_IMPLEMENTATIONS}
    except (KeyError, TypeError):
        return None
    return _content_cache_key(scene, request, binding, support_binding,
        versions=profile["original_backend_versions"], implementation_hashes=implementations,
        numeric_projection=False)


def _load_cached_result(path, *, content_key, versions, accepted_content_keys=None):
    """Treat absent, damaged or incompatible cache bytes as a safe computation miss."""
    try:
        document = wire.validate_document(wire.load_json(path.read_text(encoding="utf-8")))
        receipt = document["cache_entry"]
        accepted_keys = {content_key} if accepted_content_keys is None else set(accepted_content_keys)
        accepted_keys.add(content_key)
        if (type(receipt["version"]) is not int or receipt["version"] != CONTENT_CACHE_VERSION
                or receipt["content_key"] not in accepted_keys
                or document["kind"] != "free_space_run" or document["backend_versions"] != versions):
            return None
        ResultRef(**receipt["origin_result_ref"])
        original_ref = {"kind": document["kind"], "result_id": document["result_id"],
            "digest": wire.document_digest({key: value for key, value in document.items() if key != "cache_entry"})}
        if receipt["origin_result_ref"] != original_ref:
            return None
        snapshot = document["tables"]["snapshot"]
        original_request = _request_from_wire(snapshot["request"])
        if requests._request_key(snapshot["source_fingerprint"], original_request, versions) != snapshot["semantic_key"]:
            return None
        return document
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        return None


def _portable_capture_binding(capture_input, *, model_path, root):
    """Build a source binding from captured facts while excluding display locators."""
    from .blender_analysis_capture import capture_source_fingerprint
    identity = dict(capture_input.identity)
    content = capture_source_fingerprint(identity, capture_input.records,
                                         capture_input.diagnostics, capture_input.observation)
    project = identity.get("project_global_id", "unknown-project")
    canonical = identity.get("canonical_source_identity", f"blender:{project}:{content}")
    locator = str(Path(model_path).resolve()) if model_path is not None else str(Path(root).resolve())
    return SourceBinding(content, canonical, content, identity.get("external_dependencies", {}), locator)


def _numeric_capture_binding(capture_input, *, model_path, root):
    """Bind the numerical source projection independently of full capture authentication."""
    from .blender_analysis_capture import capture_source_fingerprint, numeric_capture_source_fingerprint
    content = numeric_capture_source_fingerprint(capture_input.identity, capture_input.records,
        capture_input.diagnostics, capture_input.observation)
    project = capture_input.identity.get("project_global_id", "unknown-project")
    canonical = f"blender:{project}:{content}"
    declared = capture_input.identity.get("canonical_source_identity")
    full = capture_source_fingerprint(capture_input.identity, capture_input.records,
        capture_input.diagnostics, capture_input.observation)
    if declared is not None and declared != f"blender:{project}:{full}":
        canonical = declared
    locator = str(Path(model_path).resolve()) if model_path is not None else str(Path(root).resolve())
    return SourceBinding(content, canonical, content,
                         capture_input.identity.get("external_dependencies", {}), locator)


def _resolve_content_store(capture_input, *, cache_directory, model_path, temporary_cache_root):
    """Resolve a model-side CacheStore only for locator-aware worker calls."""
    if model_path is None and temporary_cache_root is None:
        return None
    root = SidecarLocator(
        model_path=None if model_path is None else Path(model_path),
        explicit_directory=None if cache_directory is None else Path(cache_directory),
        temporary_root=None if temporary_cache_root is None else Path(temporary_cache_root),
    ).resolve()
    store = CacheStore(root)
    full_binding = _portable_capture_binding(capture_input, model_path=model_path, root=root)
    store.put_source_binding(full_binding)
    binding = _numeric_capture_binding(capture_input, model_path=model_path, root=root)
    if binding.source_fingerprint != full_binding.source_fingerprint:
        store.put_source_binding(binding)
    else:
        binding = full_binding
    return store, binding


def _validate_cached_result_bytes(payload, *, content_key, versions, accepted_content_keys=None):
    """Validate a wire cache payload without requiring a temporary path."""
    try:
        document = wire.validate_document(wire.load_json(payload.decode("utf-8")))
        receipt = document["cache_entry"]
        accepted_keys = {content_key} if accepted_content_keys is None else set(accepted_content_keys)
        accepted_keys.add(content_key)
        if (type(receipt["version"]) is not int or receipt["version"] != CONTENT_CACHE_VERSION
                or receipt["content_key"] not in accepted_keys
                or document["kind"] != "free_space_run" or document["backend_versions"] != versions):
            raise ValueError("content cache receipt is stale")
        ResultRef(**receipt["origin_result_ref"])
        original_ref = {"kind": document["kind"], "result_id": document["result_id"],
            "digest": wire.document_digest({key: value for key, value in document.items() if key != "cache_entry"})}
        if receipt["origin_result_ref"] != original_ref:
            raise ValueError("content cache origin reference is invalid")
        snapshot = document["tables"]["snapshot"]
        original_request = _request_from_wire(snapshot["request"])
        if requests._request_key(snapshot["source_fingerprint"], original_request, versions) != snapshot["semantic_key"]:
            raise ValueError("content cache semantic key is invalid")
        return document
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("invalid Blender content cache payload") from exc


def _refresh_shared_metadata(actual, before, after):
    """Refresh only declared shared fields while retaining cell overrides and deletions."""
    if not isinstance(actual, Mapping):
        return actual
    result = dict(actual)
    for key, value in before.items():
        if key in result and (result[key] is value or result[key] == value):
            result[key] = after[key]
    return result


class _CachedSamples:
    """Expose validated cached samples to the ordinary lossless result serializer."""

    def __init__(self, document, snapshot, query):
        """Keep original calculation evidence separate from current publication fields."""
        # Own the cache document once; a MappingProxy supplied by a caller alone
        # does not prove that its nested values or backing dictionary are frozen.
        self.document, self.snapshot, self.query = wire.freeze(document), snapshot, query
        original = self.document["tables"]["snapshot"]
        self.metadata_entries, self.queries = {}, {}
        self.empty_metadata = requests._MetadataOverlay({})
        self.base_provenance = {key: wire.resolve_value(self.document, ref)
                               for key, ref in self.document["tables"]["sample_provenance"].items()}
        self.before_query = requests._request_query(_request_from_wire(original["request"]), original["semantic_key"])
        self.before_provenance = {**original["provenance"], "frame": self.before_query.frame,
            "query_revision": self.before_query.revision,
            "input_query_context": {"domain_id": self.before_query.domain_id, "frame": self.before_query.frame}}
        self.after_provenance = {**snapshot.provenance, "frame": query.frame,
            "query_revision": query.revision,
            "input_query_context": {"domain_id": query.domain_id, "frame": query.frame}}
        self.before_query_values = wire.freeze({item.name: getattr(self.before_query, item.name)
                                               for item in fields(self.before_query)})
        self.after_query_values = {item.name: getattr(query, item.name) for item in fields(query)}

    def _metadata(self, value):
        """Freeze each owned metadata value once and compose trusted core overlays."""
        if not isinstance(value, Mapping):
            return value
        result = self.empty_metadata
        for key, item in value.items():
            token = (key, id(item))
            if token not in self.metadata_entries:
                # Retain the source identity alongside its frozen overlay so IDs
                # cannot be recycled while another cell still uses the cache.
                self.metadata_entries[token] = (item, requests._MetadataOverlay({key: item}))
            result = requests._MetadataOverlay(result, self.metadata_entries[token][1])
        return result

    def evaluate(self, target, query):
        """Rebind shared identity only; preserve all actual per-cell calculation deltas."""
        sample = wire._decode_cell_view(self.document, row=target[0], column=target[1],
                                        base_provenance=self.base_provenance)
        query_token = id(sample["query"])
        if query_token not in self.queries:
            updated = _refresh_shared_metadata(sample["query"], self.before_query_values, self.after_query_values)
            self.queries[query_token] = requests.FieldQuery(**updated)
        sample["query"] = self.queries[query_token]
        old_support = sample["support"]
        sample["support"] = _refresh_shared_metadata(old_support,
            {"frame": self.before_query.frame, "plane": self.before_query.plane},
            {"frame": self.query.frame, "plane": self.query.plane})
        # Support may be a shared link or an independent cell-specific observation.
        provenance_support = sample["provenance"].get("support")
        sample["provenance"] = _refresh_shared_metadata(sample["provenance"],
            self.before_provenance, self.after_provenance)
        sample["support"] = self._metadata(sample["support"])
        if provenance_support == old_support and "support" in sample["provenance"]:
            sample["provenance"]["support"] = sample["support"]
        sample["provenance"] = self._metadata(sample["provenance"])
        return requests.FieldSample(**sample)


def _cached_run(document, request, versions):
    """Rebuild current strict run identity without repeating cached geometry work."""
    original = document["tables"]["snapshot"]
    fingerprint = original["source_fingerprint"]
    key = requests._request_key(fingerprint, request, versions)
    provenance = {**original["provenance"], "semantic_key": key,
        "geometry_query": request.geometry_query.to_dict(), "height_band_datum": request.height_band_datum,
        "backend_versions": versions}
    snapshot = requests.AnalysisSnapshot(key, fingerprint, request, versions, provenance)
    query = requests._request_query(request, key)
    return requests.AnalysisRun(_CachedSamples(document, snapshot, query), query, snapshot,
                               requests.FieldStatus(document["support_status"]), document["explanation"])


def serialize_analysis_result(run, *, job_id, plane_uuid, plane_revision, domain_request_id, domain_session_revision,
                              binding=None):
    """Serialize every public sample using value references and exact mapping deltas."""
    request = run.snapshot.request
    if request.plane.identity != plane_uuid or request.plane.revision != plane_revision:
        raise ValueError("serializer plane does not match frozen request")
    wire._integer(domain_session_revision, "domain session revision")
    wire._text(domain_request_id, "domain request id")
    snapshot = wire.plain(run.snapshot.to_dict())
    values, value_indices = [], {}
    detached, encodings, queries = {}, {}, {}
    def data(value, *, owned=False):
        """Detach duck samples per evaluation; reuse only actual frozen Field data."""
        if not isinstance(value, (Mapping, tuple, list)):
            return wire.plain(value)
        token = id(value)
        if owned and token in detached:
            return detached[token][1]
        if isinstance(value, Mapping):
            if any(not isinstance(key, str) for key in value):
                raise ValueError("JSON object keys must be strings")
            result = {key: data(item, owned=owned) for key, item in value.items()}
        else:
            result = [data(item, owned=owned) for item in value]
        if owned:
            detached[token] = (value, result)
        return result
    def encoding(value):
        """Encode each codec-owned value once while retaining its identity."""
        token = id(value)
        if token not in encodings:
            encodings[token] = (value, wire.canonical_json(value))
        return encodings[token][1]
    shared = {encoding(value): {"snapshot": key} for key, value in snapshot["provenance"].items()}
    def intern(value):
        """Deduplicate equal values, never merely equal metadata key names."""
        encoded = encoding(value)
        if encoded in shared:
            return shared[encoded]
        if encoded not in value_indices:
            value_indices[encoded] = len(values)
            values.append(value)
        return value_indices[encoded]
    def delta(base, actual):
        """Preserve changed values and key deletion under an otherwise shared mapping."""
        if not isinstance(base, Mapping) or not isinstance(actual, Mapping):
            return {"ref": intern(actual)}
        return {"changes": {key: intern(value) for key, value in actual.items()
                            if key not in base or (base[key] is not value and encoding(base[key]) != encoding(value))},
                "removed": sorted(base.keys() - actual.keys())}
    first = run.field.evaluate((0, 0), run.query)
    first_owned = type(first) is requests.FieldSample
    base_support = data(first.support, owned=first_owned)
    base_provenance = dict(data(first.provenance, owned=first_owned))
    # Support commonly occurs in provenance too; preserve that equality as an explicit cell reference.
    if base_provenance.get("support", object()) == base_support:
        base_provenance.pop("support", None)
    cells = []
    for row in range(request.sampling.n_rows):
        for column in range(request.sampling.n_cols):
            sample = first if (row, column) == (0, 0) else run.field.evaluate((row, column), run.query)
            owned = type(sample) is requests.FieldSample
            support = data(sample.support, owned=owned)
            provenance = dict(data(sample.provenance, owned=owned))
            provenance_support = "support" in provenance and provenance["support"] == support
            if provenance_support:
                del provenance["support"]
            query_owned = owned and type(sample.query) is requests.FieldQuery
            query_token = id(sample.query)
            if not query_owned or query_token not in queries:
                query = {item.name: data(getattr(sample.query, item.name), owned=query_owned)
                         for item in fields(sample.query)}
                if query_owned:
                    queries[query_token] = (sample.query, query)
            else:
                query = queries[query_token][1]
            cells.append({"row": row, "column": column, "value": sample.value, "status": sample.status.value,
                "query_ref": intern(query), "support_delta": delta(base_support, support),
                "source_ids_ref": intern(data(sample.source_ids, owned=owned)),
                "provenance_delta": delta(base_provenance, provenance),
                "provenance_support": provenance_support, "explanation_ref": intern(data(sample.explanation))})
    project_source_identity = snapshot["provenance"].get("project_source_identity",
        {"request_source_fingerprint": run.snapshot.source_fingerprint})
    identity = {"project_source_identity": project_source_identity,
        "request_source_fingerprint": run.snapshot.source_fingerprint, "domain_identity": snapshot["request"]["domain"],
        "plane_uuid": plane_uuid, "plane_revision": plane_revision, "frame_key": run.query.frame,
        "request_identity": request.request_id, "domain_request_id": domain_request_id,
        "domain_session_revision": domain_session_revision, "operation": request.operation,
        "query_key": request.geometry_query.to_dict(), "semantic_key": run.snapshot.semantic_key}
    document = {"kind": "free_space_run", "result_id": job_id, "job_id": job_id,
        "schema_version": wire.SCHEMA_VERSION, "algorithm_version": wire.ALGORITHM_VERSION,
        "plane_uuid": plane_uuid, "plane_revision": plane_revision, "semantic_key": run.snapshot.semantic_key,
        "backend_versions": wire.plain(run.snapshot.backend_versions), "identity": identity,
        "binding": wire.plain(binding or {}),
        "tables": {"snapshot": snapshot, "lattice": request.sampling.to_dict(),
            "source_audit": {"snapshot_provenance_keys": sorted(snapshot["provenance"])},
            "sample_support": base_support,
            "sample_provenance": {key: intern(value) for key, value in base_provenance.items()}, "values": values},
        "support_status": run.support_status.value, "explanation": run.explanation,
        "cells": cells, "display_fragments": ()}
    document = wire.plain(document)
    document["digest"] = wire.document_digest(document)
    wire.validate_document(document)
    return document


def build_display_fragments(run, domain_geometries):
    """Clip lattice cells to the exact qualified domain and emit display-only triangles."""
    from shapely import constrained_delaunay_triangles
    from shapely.geometry import Polygon, box
    from shapely.ops import triangulate, unary_union

    request = run.snapshot.request
    plane = request.plane
    if plane is not None and not hasattr(plane, "basis"):
        # Legacy fixtures carried only a world-Z origin; retain identity XY semantics.
        plane = type("_LegacyPlane", (), {"origin": plane.origin,
                                          "basis": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))})()
    triangles = []
    for mesh in domain_geometries:
        for face in mesh.triangle_indices:
            points = [_project_to_plane(mesh.vertices[index], plane) for index in face]
            polygon = Polygon([(point[0], point[1]) for point in points])
            if polygon.is_valid and polygon.area > 0:
                triangles.append(polygon)
    domain = unary_union(triangles)
    fragments = []
    for row in range(request.sampling.n_rows):
        for column in range(request.sampling.n_cols):
            x = request.sampling.origin[0] + column * request.sampling.spacing
            y = request.sampling.origin[1] + row * request.sampling.spacing
            clipped = box(x, y, x + request.sampling.spacing, y + request.sampling.spacing).intersection(domain)
            if clipped.is_empty:
                continue
            pieces = (clipped,) if clipped.geom_type == "Polygon" else tuple(getattr(clipped, "geoms", ()))
            vertices, faces, area = [], [], 0.0
            for piece in pieces:
                if piece.geom_type != "Polygon" or piece.area <= 0:
                    continue
                try:
                    candidate_triangles = constrained_delaunay_triangles(piece).geoms
                except Exception:
                    candidate_triangles = triangulate(piece)
                for triangle in candidate_triangles:
                    if not piece.covers(triangle) and not piece.covers(triangle.representative_point()):
                        continue
                    coords = list(triangle.exterior.coords)[:3]
                    start = len(vertices)
                    origin = plane.origin
                    first, second, _normal = plane.basis
                    vertices.extend([[float(origin[index] + px * first[index] + py * second[index])
                                      for index in range(3)] for px, py in coords])
                    faces.append([start, start + 1, start + 2])
                    area += triangle.area
            if vertices and abs(area - clipped.area) > 1e-8 * max(1.0, clipped.area):
                raise ValueError("display fragment area mismatch")
            if vertices:
                fragments.append({"cell_index": row * request.sampling.n_cols + column,
                                  "vertices": vertices, "faces": faces})
    return tuple(fragments)


def reconstruct_field_sample(document, *, row, column):
    """Reconstruct the existing complete frozen FieldSample in the Pixi runtime."""
    wire.validate_document(document)
    return _sample_from_wire(wire.decode_cell(document, row=row, column=column))


def _sample_from_wire(sample):
    """Use the shared Field constructors rather than duplicating core immutability."""
    if "." in (__package__ or ""):
        from ..features.field_core import FieldQuery, FieldSample
    else:
        from features.field_core import FieldQuery, FieldSample
    return FieldSample(**{**sample, "query": FieldQuery(**sample["query"])})


def read_analysis_sample(snapshot, *, row, column):
    """Read one exact free-space cell from the already validated immutable snapshot."""
    return _sample_from_wire(wire.decode_cell(snapshot.payload, row=row, column=column))


def _serialize_domain_result(result, *, result_id, binding):
    """Wrap the complete B4 service payload without inventing occupancy or consent."""
    payload = wire.plain(result.to_dict())
    binding = dict(binding)
    if payload.get("space_binding") is not None:
        if binding.get("space_binding") is not None and binding["space_binding"] != payload["space_binding"]:
            raise ValueError("native Space observation changed")
        binding["space_binding"] = payload["space_binding"]
    provenance = payload["provenance"]
    backend = {"domain_service_sha256": sha256(Path(__file__).resolve().parents[1].joinpath(
        "features", "_analysis_domain_handoff.py").read_bytes()).hexdigest()}
    plane_uuid = binding.get("plane_uuid") or "structural:" + provenance["frame_id"]
    plane_revision = binding.get("plane_revision", 1)
    identity = {"project_source_identity": payload["source_identity"], "domain_identity": payload["analysis_domain"],
        "request_identity": provenance["request_id"], "domain_request_id": provenance["request_id"],
        "domain_session_revision": payload["session_revision"], "structural_source_fingerprint": provenance["source_revision"],
        "frame_key": provenance["frame_id"], "plane_uuid": plane_uuid,
        "plane_revision": plane_revision}
    document = {"kind": "domain_session", "result_id": result_id, "job_id": result_id,
        "schema_version": wire.SCHEMA_VERSION, "algorithm_version": wire.ALGORITHM_VERSION,
        "backend_versions": backend, "identity": identity, "binding": wire.plain(binding), "payload": payload}
    document["digest"] = wire.document_digest(document)
    wire.validate_document(document)
    return document


def _request_from_wire(data):
    """Decode only the fixed existing request records; payload selects no Python types."""
    if "." in (__package__ or ""):
        from ..features.analysis_requests import AnalysisRequest, GeometryQuery, GridSampling
        from ..features.scene_contract import AnalysisPlane, AnalysisDomain
    else:
        from features.analysis_requests import AnalysisRequest, GeometryQuery, GridSampling
        from features.scene_contract import AnalysisPlane, AnalysisDomain
    if not isinstance(data, Mapping) or set(data) - {item.name for item in fields(AnalysisRequest)}:
        raise ValueError("invalid request fields")
    return AnalysisRequest(**{**data, "plane": AnalysisPlane.from_dict(data["plane"]),
        "domain": AnalysisDomain.from_dict(data["domain"]) if data["domain"] is not None else None,
        "sampling": GridSampling(**data["sampling"]), "geometry_query": GeometryQuery(**data["geometry_query"])})


def _execute_workflow_payload(payload, *, cache_directory=None, model_path=None,
                                     temporary_cache_root=None):
    """Execute the two fixed workflows from data-only frozen envelopes."""
    from .blender_analysis_capture import CanonicalCaptureInput
    from .bonsai_live import load_bonsai_capture, StructuralContext, SupportBinding, LegacySourceBinding
    if "." in (__package__ or ""):
        from ..features.scene_contract import AnalysisPlane, MeshGeometry3D
    else:
        from features.scene_contract import AnalysisPlane, MeshGeometry3D
    if not isinstance(payload, Mapping) or payload.get("kind") not in wire.KINDS:
        raise ValueError("unsupported workflow kind")
    kind = payload["kind"]
    cache_path, cached = None, None
    allowed = {"kind", "job_binding", "canonical_capture"} | ({"context", "prior", "action", "entrypoint", "domain_source_id", "storey_ref", "support_source_id"} if kind == "domain_session"
        else {"request", "domain_geometries", "support_binding", "legacy_bindings"})
    if set(payload) - allowed or not {"kind", "job_binding", "canonical_capture"} <= set(payload):
        raise ValueError("unexpected or missing workflow fields; commands are not accepted")
    binding = wire.plain(payload["job_binding"])
    job_id = wire._text(binding.get("job_id"), "job_id")
    capture_input = CanonicalCaptureInput(**payload["canonical_capture"])
    if not capture_input.capture_complete:
        raise ValueError("incomplete capture")
    request = None if kind == "domain_session" else _request_from_wire(payload["request"])
    context = StructuralContext(**payload["context"]) if kind == "domain_session" else StructuralContext(**binding["structural_context"]) if "structural_context" in binding else StructuralContext.from_plane(request.plane)
    plane = context.analysis_plane if request is None else request.plane
    live = load_bonsai_capture(capture_input, plane=plane,
        legacy_bindings=tuple(LegacySourceBinding(**row) for row in payload.get("legacy_bindings", ())))
    store_context = _resolve_content_store(
        capture_input, cache_directory=cache_directory, model_path=model_path,
        temporary_cache_root=temporary_cache_root,
    )
    checked = {"project_source_identity": wire.plain(live.scene.context.world_coordinate_system),
        "authored_groups": [group.to_dict() for group in live.scene.authored_groups],
        "canonical_structural_fingerprint": digest({"sources": structural_source_facts(
            structural_b4_view(live.scene, context=context)), "context": context.to_dict()}),
        "canonical_full_fingerprint": live.full_fingerprint, "capture_digest": wire.document_digest(payload["canonical_capture"]),
        "plane_uuid": plane.identity, "plane_revision": plane.revision, "structural_frame_key": context.structural_frame_key}
    for key, value in checked.items():
        if key in binding and binding[key] is not None and binding[key] != value:
            raise ValueError("frozen capture binding changed: " + key)
    binding.update(checked)
    binding["structural_context"] = wire.plain(context.to_dict())
    store = None
    source_binding = None
    if request is None:
        result = evaluate_domain_request(live.scene, context=context, prior=payload.get("prior"), action=payload.get("action"),
            domain_source_id=payload.get("domain_source_id"), storey_ref=payload.get("storey_ref"),
            support_source_id=payload.get("support_source_id"), space_binding=binding.get("space_binding"))
        binding.update(domain_request_id=result["domain_request_identity"], domain_session_revision=result["session_revision"],
                       confirmation_binding=wire.plain(result["confirmation_binding"]))
        if result.get("authored_domain") is not None:
            binding.update(domain_source_id=result["authored_domain"]["source_id"],
                           storey_ref=result["authored_domain"]["provenance"].get("level_ref"))
        document = _serialize_domain_result(result, result_id=job_id, binding=binding)
        binding.update(document["binding"])
        # Domain results do not enter the cache branch, so apply the shared
        # publication binding and identity fields here as well.
        binding["backend_versions"] = document["backend_versions"]
        binding["frame_key"] = document["identity"]["frame_key"]
        document["identity"].update(plane_uuid=plane.identity, plane_revision=plane.revision)
        document["identity"].update({key: binding[key] for key in (
            "project_source_identity", "canonical_structural_fingerprint", "canonical_full_fingerprint")})
        document["binding"] = binding
        document["digest"] = wire.document_digest(document)
        wire.validate_document(document)
        if store_context is not None:
            document["content_cache"] = {"version": CONTENT_CACHE_VERSION,
                "source_fingerprint": store_context[1].source_fingerprint,
                "cache_location": str(store_context[0].root)}
            document["digest"] = wire.document_digest(document)
            wire.validate_document(document)
    else:
        meshes = tuple(MeshGeometry3D.from_dict(row) for row in payload["domain_geometries"])
        support = SupportBinding(**payload["support_binding"]) if payload.get("support_binding") is not None else None
        consent = binding.get("confirmation_binding")
        expected_revision = digest(structural_source_facts(structural_b4_view(live.scene, context=context)))
        if binding.get("domain_source_id") is not None:
            from .bonsai_live import authored_space_domain, authored_space_composition
            selected = authored_space_domain(live.scene, binding["domain_source_id"],
                                             storey_ref=binding.get("storey_ref"))
            expected_revision = _authored_space_revision(live.scene, context, selected,
                                                         binding.get("storey_ref"))
            observation = authored_space_composition(live.scene, binding["domain_source_id"],
                storey_ref=binding.get("storey_ref"), previous=binding.get("space_binding"))
            binding["space_binding"] = observation
        if consent and (consent.get("source_revision") != expected_revision
                        or consent.get("frame_id") != context.structural_frame_key):
            raise ValueError("structural confirmation is stale")
        child, scoped_request = _prepare_live_analysis(live.scene, request=request,
            domain_geometries=meshes, support_binding=support)
        store = None if store_context is None else store_context[0]
        source_binding = None if store_context is None else store_context[1]
        legacy_content_key = None
        legacy_payload = None
        adopted_legacy = False
        lookup_profile = "blender-source-and-backend/1"
        if store is not None:
            # Keep the pre-binding key available for one validated adoption of a
            # flat receipt written before portable source identities were added.
            legacy_content_key = _content_cache_key(
                child, scoped_request, binding, support,
            )[0]
            historical = _legacy_content_cache_key(child, scoped_request, binding, support)
            portable_world = dict(child.context.world_coordinate_system)
            portable_world["ifc_source_identity"] = source_binding.canonical_source_identity
            child = replace(child, context=replace(child.context, world_coordinate_system=portable_world))
            content_key, versions = _content_cache_key(child, scoped_request, binding, support)
            address = CacheAddress(source_binding.source_fingerprint, "blender-analysis", "combined", "raw", content_key)
            accepted = {content_key: versions, legacy_content_key: versions}
            if historical is not None:
                accepted[historical[0]] = historical[1]

            def validate_store_payload(payload, _context):
                """Rebuild eligible keys from current facts before accepting saved wire bytes."""
                saved = wire.load_json(payload.decode("utf-8"))
                key = saved["cache_entry"]["content_key"]
                expected = accepted.get(key)
                if expected is None or saved["backend_versions"] != expected:
                    raise ValueError("Blender cached computation differs from current facts")
                _validate_cached_result_bytes(payload, content_key=key, versions=expected)

            lock = store.identity_lock(address)
        else:
            lock = nullcontext()
            if cache_directory is not None:
                content_key, versions = _content_cache_key(child, scoped_request, binding, support)
                cache_path = Path(cache_directory) / (content_key + ".json")
                cached = _load_cached_result(cache_path, content_key=content_key, versions=versions)
        with lock:
            if store is not None:
                cached_entry = load_bound_store_entry(
                    store, address, validator=validate_store_payload, profile=lookup_profile)
                if cached_entry is not None:
                    cached = wire.validate_document(wire.load_json(
                        cached_entry.payload_paths[0].read_text(encoding="utf-8")))
                else:
                    candidates = [(old_key, old_versions, store.root / (old_key + ".json"))
                                  for old_key, old_versions in accepted.items()]
                    selected_versions = None
                    for old_key, old_versions, legacy_path in candidates:
                        cached = _load_cached_result(legacy_path, content_key=old_key, versions=old_versions)
                        if cached is not None:
                            legacy_content_key = old_key
                            selected_versions = old_versions
                            legacy_payload = legacy_path.read_bytes()
                            adopted_legacy = True
                            break
            # Lookup must precede activation: even an empty legacy set projects its domain.
            run = (_cached_run(cached, scoped_request, versions) if cached is not None else
                   requests.execute_analysis_request(_activate_legacy_proxies(child, scoped_request), scoped_request))
            document = serialize_analysis_result(run, job_id=job_id, plane_uuid=request.plane.identity,
                plane_revision=request.plane.revision, domain_request_id=binding["domain_request_id"],
                domain_session_revision=binding["domain_session_revision"])
            document["display_fragments"] = (cached["display_fragments"] if cached is not None else
                                             build_display_fragments(run, meshes))
            if store is not None:
                document["content_cache"] = {"version": CONTENT_CACHE_VERSION, "content_key": content_key,
                                             "hit": cached is not None,
                                             "source_fingerprint": source_binding.source_fingerprint,
                                             "cache_location": str(store.root),
                                             "cache_reuse": ("legacy_adopted" if adopted_legacy else
                                                              "migrated_reuse" if cached_entry is not None and
                                                              getattr(cached_entry, "reuse_origin", "local") == "migrated"
                                                              else "exact_hit" if cached is not None else "computed")}
                if cached is not None:
                    document["content_cache"]["origin_result_ref"] = cached["cache_entry"]["origin_result_ref"]
            elif cache_path is not None:
                document["content_cache"] = {"version": CONTENT_CACHE_VERSION, "content_key": content_key,
                                             "hit": cached is not None}
                if cached is not None:
                    document["content_cache"]["origin_result_ref"] = cached["cache_entry"]["origin_result_ref"]
            for key, value in {"semantic_key": run.snapshot.semantic_key, "operation": request.operation,
                               "query_key": request.geometry_query.to_dict()}.items():
                if key in binding and binding[key] is not None and binding[key] != value:
                    raise ValueError("request binding mismatch: " + key)
                binding[key] = value
            binding["backend_versions"] = document["backend_versions"]
            binding["frame_key"] = document["identity"]["frame_key"]
            if kind == "free_space_run":
                document["tables"]["snapshot"]["provenance"]["project_source_identity"] = binding["project_source_identity"]
                document["identity"]["project_source_identity"] = binding["project_source_identity"]
            if kind == "domain_session":
                document["identity"].update(plane_uuid=plane.identity, plane_revision=plane.revision)
            document["identity"].update({key: binding[key] for key in ("project_source_identity", "canonical_structural_fingerprint", "canonical_full_fingerprint")})
            document["binding"] = binding
            document["digest"] = wire.document_digest(document)
            wire.validate_document(document)
            if store is not None and (cached is None or legacy_payload is not None):
                # Keep the first public ResultRef as lineage; the store owns its wrapper digest.
                if legacy_payload is None:
                    entry = wire.plain(document)
                    entry["cache_entry"] = {"version": CONTENT_CACHE_VERSION, "content_key": content_key,
                        "origin_result_ref": {"kind": document["kind"], "result_id": document["result_id"],
                                              "digest": document["digest"]}}
                    entry["digest"] = wire.document_digest(entry)
                    payload_bytes = wire.canonical_json(entry).encode("utf-8")
                else:
                    payload_bytes = legacy_payload
                if adopted_legacy:
                    adopt_legacy_store_payload(store, address, original_identity=legacy_content_key,
                        payload=payload_bytes,
                        contract={"content_key": legacy_content_key, "backend_versions":
                                 accepted.get(legacy_content_key, selected_versions)},
                        payload_format="json", validator=validate_store_payload, profile=lookup_profile)
                else:
                    store.put(address, contract={"content_key": content_key, "backend_versions": versions},
                              payload=payload_bytes, payload_format="json", validator=validate_store_payload)
            elif cache_path is not None and cached is None:
                # Keep the first public ResultRef as lineage; the cache has its own validated digest.
                entry = wire.plain(document)
                entry["cache_entry"] = {"version": CONTENT_CACHE_VERSION, "content_key": content_key,
                    "origin_result_ref": {"kind": document["kind"], "result_id": document["result_id"],
                                          "digest": document["digest"]}}
                entry["digest"] = wire.document_digest(entry)
                write_result_atomic(entry, path=cache_path)
    return document


def main(argv=None):
    """Read two fixed paths and atomically publish one data-only workflow result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("--cache-directory", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--temporary-cache-root", type=Path, default=None)
    args = parser.parse_args(argv)
    document = _execute_workflow_payload(wire.load_json(args.request.read_text(encoding="utf-8")),
                                         cache_directory=args.cache_directory,
                                         model_path=args.model_path,
                                         temporary_cache_root=args.temporary_cache_root)
    write_result_atomic(document, path=args.result)
    print(wire.canonical_json({"result_id": document["result_id"], "kind": document["kind"], "digest": document["digest"]}))


if __name__ == "__main__":
    main()

