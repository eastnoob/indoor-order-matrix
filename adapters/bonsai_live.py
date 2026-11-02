"""Translate verified evaluated IFC facts without inventing object identities."""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Mapping
from hashlib import file_digest
from pathlib import Path

from .blender_analysis_capture import CanonicalCaptureInput, digest, freeze, plain, is_owned_display, ifc_ancestry

if "." in (__package__ or ""):
    from ..features.scene_contract import (AnalysisContext, AnalysisPlane, AnalysisDomain, MeshGeometry3D,
        NeutralSceneV2, SourceObject, SourceOpening, AuthoredGroup, UncertaintyRecord, NEUTRAL_SCENE_V2)
    from ..features._analysis_domain_handoff import structural_source_facts, _polygon
    from ..features.analysis_requests import GeometryQuery
else:
    from features.scene_contract import (AnalysisContext, AnalysisPlane, AnalysisDomain, MeshGeometry3D,
        NeutralSceneV2, SourceObject, SourceOpening, AuthoredGroup, UncertaintyRecord, NEUTRAL_SCENE_V2)
    from features._analysis_domain_handoff import structural_source_facts, _polygon
    from features.analysis_requests import GeometryQuery


STRUCTURAL_ROLES = frozenset({"wall", "column", "door", "window"})
CLASS_ROLES = {"IfcWall": "wall", "IfcColumn": "column",
               "IfcDoor": "door", "IfcWindow": "window", "IfcSlab": "slab",
               "IfcFurniture": "furniture", "IfcFurnishingElement": "furniture",
               "IfcSpace": "space", "IfcSpatialZone": "container",
               "IfcSite": "site", "IfcBuilding": "building",
               "IfcBuildingStorey": "storey", "IfcOpeningElement": "opening",
               "IfcAnnotation": "annotation", "IfcGrid": "grid_axis"}


@dataclass(frozen=True)
class StructuralContext:
    """Independent B4 XY frame and absolute structural section parameters."""

    plane_uuid: str
    xy_origin_m: tuple
    xy_basis: tuple
    datum_z_m: float = 0.
    cut_z_m: float = 1.5
    storey_ref: str | None = None
    selected_wall_refs: tuple[str, ...] = ()
    b4_parameters: Mapping = None
    constants_version: str = "b4-closed-enclosure/1"

    def __post_init__(self):
        """Freeze caller parameters and validate the actual structural plane."""
        object.__setattr__(self, "xy_origin_m", tuple(self.xy_origin_m))
        object.__setattr__(self, "xy_basis", tuple(tuple(row) for row in self.xy_basis))
        if self.storey_ref is not None and (not isinstance(self.storey_ref, str) or not self.storey_ref.strip()):
            raise ValueError("structural storey reference must be a nonempty string")
        selected = tuple(self.selected_wall_refs)
        if (any(not isinstance(ref, str) or not ref.startswith("ifc-object:") or not ref.removeprefix("ifc-object:")
                for ref in selected) or len(set(selected)) != len(selected)):
            raise ValueError("selected wall refs must be unique canonical IFC source ids")
        selected = tuple(sorted(selected))
        if selected and self.storey_ref is None:
            raise ValueError("selected wall analysis requires an explicit storey")
        object.__setattr__(self, "selected_wall_refs", selected)
        object.__setattr__(self, "b4_parameters", freeze(self.b4_parameters or {
            "tolerance_mm2": 1., "contact_distance_m": 1e-6, "aperture_area_budget_m2": 1e-6}))
        digest(self.to_dict())
        self.analysis_plane

    @classmethod
    def from_plane(cls, plane, **parameters):
        """Extract XY only; occupancy Z/revision/name/camera never enter B4."""
        return cls(plane.identity or "structural-world-xy", tuple(plane.origin[:2]),
                   tuple(plane.basis), **parameters)

    @property
    def analysis_plane(self):
        """Return the independent XY carrier while datum/cut remain absolute fields."""
        return AnalysisPlane(name="B4 structural datum", identity=self.plane_uuid,
                             origin=(*self.xy_origin_m, 0.0), basis=self.xy_basis)

    def to_dict(self):
        """Serialize stable structural configuration without runtime observations."""
        return {"plane_uuid": self.plane_uuid, "xy_origin_m": self.xy_origin_m,
                "xy_basis": self.xy_basis, "datum_z_m": self.datum_z_m,
                "cut_z_m": self.cut_z_m, "storey_ref": self.storey_ref,
                "selected_wall_refs": self.selected_wall_refs,
                "b4_parameters": plain(self.b4_parameters),
                "constants_version": self.constants_version}

    @property
    def structural_frame_key(self):
        """Bind both the actual frame and structural algorithm configuration."""
        return digest(self.to_dict())


@dataclass(frozen=True)
class SupportBinding:
    """Explicit source-specific permission to treat one floor as domain support."""

    source_object_id: str
    project_global_id: str
    source_class: str
    geometry_refs: tuple
    geometry_digest: str
    capture_fingerprint: str
    confirmation_id: str


@dataclass(frozen=True)
class LegacySourceBinding:
    """Checked historical identity bridge; never a string replacement rule."""

    legacy_object_id: str
    legacy_step_id: int
    global_id: str
    project_global_id: str
    ifc_identity: str
    canonical_object_id: str
    geometry_refs: tuple
    geometry_digest: str
    scope: Mapping
    covered_owner_ids: tuple
    required: bool = True

    def __post_init__(self):
        """Detach scope geometry and identity declarations from caller-owned mappings."""
        object.__setattr__(self, "scope", freeze(self.scope))
        object.__setattr__(self, "geometry_refs", tuple(self.geometry_refs))
        object.__setattr__(self, "covered_owner_ids", tuple(self.covered_owner_ids))


@dataclass(frozen=True)
class BonsaiLiveScene:
    """Full and structural views share exact immutable evaluated mesh objects."""

    scene: NeutralSceneV2
    structural_scene: NeutralSceneV2
    structural_context: StructuralContext
    identity_map: Mapping
    domain_support_audit: Mapping
    structural_fingerprint: str
    full_fingerprint: str
    capture_fingerprint: str
    diagnostics: tuple


def authored_space_domain(scene, source_id, *, storey_ref=None):
    """Return one validated authored IfcSpace domain from captured source facts."""
    matches = [source for source in scene.source_objects if source.source_id == source_id]
    if len(matches) != 1:
        raise ValueError("selected IfcSpace identity is missing or ambiguous")
    source = matches[0]
    if source.source_class != "IfcSpace" or source.source_role != "space":
        raise ValueError("selected domain source must be an IfcSpace")
    if not isinstance(storey_ref, str) or not storey_ref.strip():
        raise ValueError("selected IfcSpace requires an explicit storey")
    if source.level_ref is None or source.level_ref != storey_ref:
        raise ValueError("selected IfcSpace storey does not match request")
    if (tuple(dict.fromkeys(source.container_refs)) != (storey_ref,)
            or source.id != "ifc-object:" + source_id
            or source.provenance.get("project_global_id") != scene.context.world_coordinate_system.get("project_global_id")):
        raise ValueError("selected IfcSpace requires one canonical native identity and storey relation")
    if len(source.geometry_refs) != 1:
        raise ValueError("selected IfcSpace requires one supported geometry ref")
    meshes = [mesh for mesh in scene.geometries if mesh.id == source.geometry_refs[0]]
    if len(meshes) != 1:
        raise ValueError("selected IfcSpace geometry is unavailable")
    mesh = meshes[0]
    if mesh.is_closed is not True or mesh.is_manifold is not True:
        raise ValueError("selected IfcSpace geometry must be closed and manifold")
    if "." in (__package__ or ""):
        from ..features.geometry_substitutes import mass_patch_from_mesh
        from ..features.geometry_views import component_shape, plan_projection
    else:
        from features.geometry_substitutes import mass_patch_from_mesh
        from features.geometry_views import component_shape, plan_projection
    projected = component_shape(plan_projection(mass_patch_from_mesh(mesh), scene.context.analysis_plane).components)
    if (projected is None or projected.geom_type != "Polygon" or not projected.is_valid
            or projected.is_empty or projected.area <= 0):
        raise ValueError("selected IfcSpace requires one valid connected polygon projection")
    return AnalysisDomain(
        id=f"ifc-domain:{source.source_id}", geometry_refs=source.geometry_refs,
        source_id=source.source_id, selection_method="explicit_bonsai_ifcspace",
        provenance={"method": "bonsai_verified_ifcspace", "source_object_id": source.id,
                    "source_class": source.source_class, "level_ref": source.level_ref},
    )


def authored_space_composition(scene, source_id, *, storey_ref=None, previous=None):
    """Observe native identity and full captured geometry in the existing result binding."""
    domain = authored_space_domain(scene, source_id, storey_ref=storey_ref)
    source = next(source for source in scene.source_objects if source.source_id == source_id)
    mesh = next(mesh for mesh in scene.geometries if mesh.id == domain.geometry_refs[0])
    observation = {"version": 1, "project_global_id": source.provenance["project_global_id"],
            "space_guid": source_id, "source_id": source.id, "storey_ref": source.level_ref,
            "geometry_digest": digest(mesh.to_dict()), "origin": "adopted",
            "provenance": {"source_step_id": source.provenance["step_id"], "source_class": source.source_class,
                           "ifc_source_identity": source.provenance["ifc_source_identity"]}}
    if previous is not None:
        previous = plain(previous)
        if (not isinstance(previous, Mapping) or set(previous) != set(observation)
                or any(previous[key] != value for key, value in observation.items() if key not in {"origin", "provenance"})
                or previous["origin"] not in {"adopted", "created_from_b4"}
                or not isinstance(previous["provenance"], Mapping)
                or any(previous["provenance"].get(key) != value for key, value in observation["provenance"].items())):
            raise ValueError("native Space observation changed")
        # A validated native recapture may carry forward the exact creation receipt, never infer one from a name.
        observation["origin"] = previous["origin"]
        observation["provenance"] = previous["provenance"]
    return observation


def _proven_other_storey(source, storey_ref, source_roles):
    """Require one typed level and no unknown or competing storey containment."""
    if source.level_ref in {None, storey_ref}:
        return False
    containers = tuple(dict.fromkeys(source.container_refs))
    if source.level_ref not in containers:
        return False
    for ref in containers:
        if ref == source.level_ref:
            continue
        role = source_roles.get(ref)
        if ref == storey_ref or role in {None, "storey"}:
            return False
    return True


def _opening_in_storey_scope(opening, *, source_ids, outside_ids, opening_sources,
                             storey_ref, source_roles):
    """Retain unresolved openings unless all available relations prove outside scope."""
    source = opening_sources.get(opening.source_id)
    if source is not None and source.level_ref == storey_ref:
        return True
    relations = (*opening.host_refs, *opening.provenance.get("filling_source_refs", ()))
    if source_ids.intersection(relations):
        return True
    if relations:
        return not all(ref in outside_ids for ref in relations)
    return source is None or not _proven_other_storey(source, storey_ref, source_roles)


def structural_b4_view(scene, *, context, source_token=None, storey_ref=None):
    """Select structural factual sources and actual independent B4 frame."""
    context_storey_ref = context.storey_ref
    if storey_ref is not None and context_storey_ref is not None and storey_ref != context_storey_ref:
        raise ValueError("structural storey scope conflicts with the frozen context")
    storey_ref = storey_ref or context_storey_ref
    source_roles = {source.id: source.source_role for source in scene.source_objects}
    outside_ids = {source.id for source in scene.source_objects
                   if storey_ref and _proven_other_storey(source, storey_ref, source_roles)}
    sources = []
    for source in scene.source_objects:
        if source.source_role not in STRUCTURAL_ROLES:
            continue
        if source.id in outside_ids:
            continue
        sources.append(source)
    sources = tuple(sorted(sources, key=lambda source: source.id))
    source_ids = {source.id for source in sources}
    opening_sources = {source.source_id: source for source in scene.source_objects if source.source_id}
    openings = scene.openings if not storey_ref else tuple(opening for opening in scene.openings
        if _opening_in_storey_scope(opening, source_ids=source_ids, outside_ids=outside_ids,
                                   opening_sources=opening_sources, storey_ref=storey_ref,
                                   source_roles=source_roles))
    refs = {ref for source in sources for ref in source.geometry_refs}
    refs.update(ref for opening in openings for ref in opening.geometry_refs)
    # Authored domain geometry remains available to the existing B4 reducer.
    if scene.analysis_domain is not None:
        refs.update(scene.analysis_domain.geometry_refs)
    flags = {"has_3d_geometry": bool(refs)}
    return replace(scene, context=replace(scene.context, analysis_plane=context.analysis_plane,
                   capability_flags=flags), source_objects=sources,
                   openings=openings,
                   geometries=tuple(sorted((mesh for mesh in scene.geometries if mesh.id in refs),
                                           key=lambda mesh: mesh.id)))


def geometry_digest(scene, source):
    """Hash exact current mesh content for explicit source binding validation."""
    return digest([mesh.to_dict() for ref in source.geometry_refs
                   for mesh in scene.geometries if mesh.id == ref])


def source_capture_fingerprint(scene):
    """Bind stable full factual identity and geometry without occupancy plane state."""
    return digest({"identity": dict(scene.context.world_coordinate_system),
                   "authored_groups": [group.to_dict() for group in sorted(scene.authored_groups, key=lambda group: group.id)],
                   "sources": [source.to_dict() for source in sorted(scene.source_objects, key=lambda source: source.id)],
                   "openings": [opening.to_dict() for opening in sorted(scene.openings, key=lambda opening: opening.id)],
                   "geometries": [mesh.to_dict() for mesh in sorted(scene.geometries, key=lambda mesh: mesh.id)]})


def validate_support_binding(scene, binding, *, capture_fingerprint):
    """Reject ambiguous, stale or class-wide floor exclusions without excluding any mass."""
    audit = {"source_id": None, "source_object_id": None, "status": "unbound"}
    if binding is None:
        return audit
    matches = [source for source in scene.source_objects if source.id == binding.source_object_id]
    project = scene.context.world_coordinate_system.get("project_global_id")
    valid = len(matches) == 1
    if valid:
        source = matches[0]
        valid = (source.source_role in {"slab", "floor"} and source.source_id is not None
                 and "IfcSlab" in ifc_ancestry(scene.context.source_schema, source.source_class)
                 and source.source_class == binding.source_class
                 and project == binding.project_global_id
                 and bool(source.geometry_refs) and source.geometry_refs == tuple(binding.geometry_refs)
                 and geometry_digest(scene, source) == binding.geometry_digest
                 and capture_fingerprint == binding.capture_fingerprint
                 and isinstance(binding.confirmation_id, str) and bool(binding.confirmation_id.strip()))
    if valid:
        audit.update(status="validated", source_id=source.source_id, source_object_id=source.id,
                     confirmation_id=binding.confirmation_id)
    else:
        audit.update(status="rejected", reason="support_binding_not_current_unique_floor")
    return audit


def _mesh(row):
    """Preserve captured indexed triangles; no retessellation or bounding-box fallback."""
    raw = row.get("mesh")
    if raw is None or row.get("status") != "extracted":
        return None
    raw = plain(raw)
    if (raw.get("units") != "m" or not raw.get("vertices")
            or not raw.get("triangle_indices", raw.get("triangles"))
            or raw.get("transform_applied", raw.get("local_to_world_provenance", {}).get("world_transform_applied")) is not True):
        raise ValueError("evaluated geometry must be nonempty world metres")
    return MeshGeometry3D(id="ifc-mesh:" + row["global_id"], vertices=raw["vertices"],
        triangle_indices=raw.get("triangle_indices", raw.get("triangles")), normals=raw.get("normals", ()),
        is_manifold=raw.get("is_manifold"), is_closed=raw.get("is_closed"), units=raw.get("units", "m"),
        source_representation_id=raw.get("source_representation_id", raw.get("representation_id")),
        tessellation_settings=raw.get("tessellation_settings", {}),
        local_to_world_provenance={"method": "bonsai_verified_evaluated_world_metres",
                                  "capture_world_transform": raw.get("world_transform"),
                                  "blender_world_to_m": raw.get("blender_world_to_m"),
                                  "quality": raw.get("quality", {}),
                                  "world_transform_applied": True})


def load_pinned_proxy(target, *, root):
    """Load the existing pinned OBJ proxy with unchanged B3 byte/topology validation."""
    import trimesh
    path = Path(root) / target["obj_ref"]["path"]
    with path.open("rb") as stream:
        checksum = file_digest(stream, "sha256").hexdigest()
    if (path.stat().st_size, checksum) != (target["obj_ref"]["bytes"], target["obj_ref"]["sha256"]):
        raise ValueError(f"proxy_fingerprint_mismatch:{target['target_id']}")
    scene = trimesh.load_scene(path, file_type="obj", process=False, maintain_order=True,
                               group_material=False, skip_materials=True)
    if len(scene.geometry) != 1:
        raise ValueError(f"proxy_geometry_count_mismatch:{target['target_id']}")
    mesh = next(iter(scene.geometry.values()))
    checks = target["generated_mesh_checks"]
    if (len(mesh.vertices), len(mesh.faces)) != (checks["vertex_count"], checks["triangle_count"]):
        raise ValueError(f"proxy_mesh_check_mismatch:{target['target_id']}")
    if not bool(mesh.is_watertight):
        raise ValueError(f"proxy_not_closed:{target['target_id']}")
    return MeshGeometry3D(id=target["mesh_id"], vertices=mesh.vertices.tolist(), triangle_indices=mesh.faces.tolist(),
        normals=(), is_manifold=True, is_closed=True, units="m", source_representation_id="GeneratedProxy",
        tessellation_settings={"method": "pinned_obj_process_false"},
        local_to_world_provenance={"world_transform_applied": True, "proxy_obj_ref": target["obj_ref"],
                                  "approximation_limit": "Convex hull fills gaps and concavities"})


def validate_legacy_applicability(scope):
    """Require one exact world-XY metre footprint and one supported operation/query."""
    applicability = scope.get("applicability")
    if not isinstance(applicability, Mapping):
        raise ValueError("legacy_scope_applicability_missing")
    if (applicability.get("frame") != {"kind": "world_xy", "units": "m"}
            or applicability.get("operation") not in {"free_space", "physical_occupancy"}):
        raise ValueError("legacy_scope_frame_or_operation_unsupported")
    polygon = _polygon(plain(applicability.get("geometry")))
    query = GeometryQuery(**plain(applicability["query"]))
    if query.kind not in {"whole_height_projection", "exact_world_xy_section"}:
        raise ValueError("legacy_scope_query_unsupported")
    return polygon, query


def _enroll_legacy(scene, bindings):
    """Enroll only complete checked owner groups; required refusal suppresses raw fallback."""
    sources = {source.id: source for source in scene.source_objects}
    legacy_ids = [binding.legacy_object_id for binding in bindings]
    canonical_ids = [binding.canonical_object_id for binding in bindings]
    if len(set(legacy_ids)) != len(legacy_ids) or len(set(canonical_ids)) != len(canonical_ids):
        raise ValueError("ambiguous legacy identity map")
    groups = {}
    for binding in bindings:
        target = binding.scope.get("target", {})
        groups.setdefault(target.get("target_id", binding.legacy_object_id), []).append(binding)
    identity = scene.context.world_coordinate_system
    enrolled, refused, legacy_map, diagnostics = {}, set(), {}, []
    meshes, proxies = [], []
    for group in groups.values():
        first = group[0]
        target = plain(first.scope.get("target", {}))
        covered = set(first.covered_owner_ids)
        # Retain the entire declared group on failure, including an owner whose
        # bridge row is missing; incomplete coverage can never enable raw mass.
        required_owners = set().union(*(set(binding.covered_owner_ids) | {binding.canonical_object_id}
                                       for binding in group if binding.required))
        target_guids = target.get("owner_global_ids", {})
        required_owners.update(source.id for source in scene.source_objects
                               if required_owners and source.source_id in target_guids.values())
        if required_owners - sources.keys():
            raise ValueError("required legacy owner missing from canonical inventory")
        reason = None
        try:
            validate_legacy_applicability(first.scope)
            if (not covered or len(first.covered_owner_ids) != len(covered)
                    or covered != {binding.canonical_object_id for binding in group}
                    or set(target.get("represented_source_ids", ())) != {binding.legacy_object_id for binding in group}
                    or len(target.get("represented_source_ids", ())) != len(group)
                    or target.get("representation_identifier") != "GeneratedProxy"):
                raise ValueError("legacy_owner_coverage_mismatch")
            for binding in group:
                source = sources.get(binding.canonical_object_id)
                if (source is None or binding.scope != first.scope or set(binding.covered_owner_ids) != covered
                        or binding.project_global_id != identity.get("project_global_id")
                        or binding.ifc_identity != identity.get("ifc_source_identity")
                        or binding.canonical_object_id != "ifc-object:" + binding.global_id
                        or source.source_id != binding.global_id
                        or source.provenance["step_id"] != binding.legacy_step_id
                        or target_guids.get(binding.legacy_object_id) != binding.global_id
                        or not source.geometry_refs or tuple(binding.geometry_refs) != source.geometry_refs
                        or binding.geometry_digest != geometry_digest(scene, source)):
                    raise ValueError("legacy_identity_geometry_or_scope_mismatch")
            proxy = load_pinned_proxy(target, root=Path(__file__).resolve().parents[1])
            if proxy.id in {mesh.id for mesh in (*scene.geometries, *meshes)} or target["target_id"] in sources:
                raise ValueError("legacy_proxy_identity_conflict")
            if covered & enrolled.keys():
                raise ValueError("legacy_owner_coverage_ambiguous")
        except (KeyError, TypeError, ValueError, OSError) as exc:
            reason = str(exc)
            refused.update(required_owners)
        if reason is None:
            meshes.append(proxy)
            # Pending records have no usable geometry refs or resolver coverage.
            # Only the request-scoped adapter may activate them after exact scope matching.
            proxies.append(SourceObject(id=target["target_id"], source_role="analysis_substitute", geometry_refs=(),
                factual_properties={"pending_legacy_occupancy": {
                    "scope": plain(first.scope), "covered_owner_ids": sorted(covered), "geometry_refs": [proxy.id],
                    "proxy_geometry_digest": digest([proxy.to_dict()]),
                    "capture_identity": dict(identity),
                    "owner_geometry": {owner: {"geometry_refs": sources[owner].geometry_refs,
                        "geometry_digest": geometry_digest(scene, sources[owner]),
                        "source_id": sources[owner].source_id, "source_class": sources[owner].source_class,
                        "step_id": sources[owner].provenance["step_id"]} for owner in covered}}},
                provenance={"representation_identifier": "GeneratedProxy", "proxy_obj_ref": target["obj_ref"]},
                uncertainties=(UncertaintyRecord(code="missing_geometry", message="Legacy proxy awaits request scope validation",
                    source_refs=tuple(sorted(covered)), operation="legacy_scope_pending", severity="warning"),)))
            enrolled.update({owner: (target["target_id"], plain(first.scope)) for owner in covered})
            for binding in group:
                legacy_map[binding.legacy_object_id] = {"legacy_object_id": binding.legacy_object_id,
                    "legacy_step_id": binding.legacy_step_id, "global_id": binding.global_id,
                    "project_global_id": binding.project_global_id, "canonical_object_id": binding.canonical_object_id,
                    "geometry_refs": binding.geometry_refs, "geometry_digest": binding.geometry_digest,
                    "capture_identity": dict(identity)}
        diagnostics.extend({"legacy_object_id": binding.legacy_object_id,
                            "status": "pending_scope_validation" if reason is None else "rejected_unresolved",
                            "reason": reason} for binding in group)
    patched = []
    for source in scene.source_objects:
        if source.id in refused:
            patched.append(replace(source, geometry_refs=(),
                factual_properties={key: value for key, value in source.factual_properties.items() if key != "OM_FunctionSubstitutes"},
                uncertainties=source.uncertainties + (
                UncertaintyRecord(code="missing_geometry", message="Required historical binding failed",
                    source_refs=(source.id,), operation="legacy_identity_bridge", severity="warning"),)))
        elif source.id in enrolled:
            patched.append(replace(source, geometry_refs=(),
                factual_properties={key: value for key, value in source.factual_properties.items() if key != "OM_FunctionSubstitutes"},
                uncertainties=source.uncertainties + (
                UncertaintyRecord(code="missing_geometry", message="Required legacy representation awaits request scope validation",
                    source_refs=(source.id,), operation="legacy_scope_pending", severity="warning"),)))
        else:
            patched.append(source)
    return replace(scene, source_objects=tuple(patched + proxies), geometries=scene.geometries + tuple(meshes)), legacy_map, diagnostics


def load_bonsai_capture(capture, *, plane, support_binding=None, legacy_bindings=()):
    """Validate factual IFC identity and retain all physical classes for occupancy."""
    if not isinstance(capture, CanonicalCaptureInput):
        raise TypeError("canonical evaluated capture required")
    if capture.capture_complete is not True:
        raise ValueError("complete canonical capture required")
    identity = plain(capture.identity)
    project, source_identity = identity.get("project_global_id"), identity.get("ifc_source_identity")
    if not project or not source_identity:
        raise ValueError("IFC identity requires project and source")
    seen, steps, sources, meshes, identity_map = set(), set(), [], [], {}
    diagnostics = list(plain(capture.diagnostics))
    for row in capture.records:
        guid, step = row.get("global_id"), row.get("step_id")
        if (not isinstance(guid, str) or not guid or guid in seen or type(step) is not int or step <= 0
                or step in steps or row.get("id") != "ifc-object:" + guid
                or row.get("project_global_id") != project or row.get("binding_verified") is not True
                or not isinstance(row.get("ifc_class"), str) or not row["ifc_class"].startswith("Ifc")):
            raise ValueError("unverified or ambiguous IFC identity")
        seen.add(guid)
        steps.add(step)
        if row.get("status") == "display_only" and is_owned_display(row.get("display_ownership", {})):
            diagnostics.append({"source_object_id": row["id"], "reason": "analyzer_owned_display_only"})
            continue
        error = row.get("error", "Evaluated IFC mesh unavailable")
        try:
            mesh = _mesh(row)
        except (KeyError, TypeError, ValueError) as exc:
            mesh, error = None, str(exc)
        if mesh is not None:
            meshes.append(mesh)
        uncertainty = () if mesh is not None else (UncertaintyRecord(code="missing_geometry",
            message=str(error), source_refs=(row["id"],),
            operation="bonsai_live_capture", severity="warning"),)
        ancestry = ifc_ancestry(identity.get("schema"), row["ifc_class"])
        if "IfcProduct" not in ancestry:
            raise ValueError("IFC source class must be a schema product")
        # The verified IFC class owns physical inclusion; a supplied display role
        # cannot turn furniture into a nonmass space or authorized floor support.
        role = next((CLASS_ROLES[cls] for cls in ancestry if cls in CLASS_ROLES), "physical_element")
        camera = row.get("native_camera")
        if camera is not None:
            from .bonsai_analysis_plane import CameraBinding
            observed = CameraBinding(**plain(camera))
            if (row["ifc_class"] != "IfcAnnotation" or observed.role != "geometry_author"
                    or observed.camera_id != "ifc:" + guid
                    or observed.provenance.get("project_global_id") != project
                    or observed.provenance.get("source_ifc_global_id") != guid
                    or observed.provenance.get("geometry_author_qualified") is not True):
                raise ValueError("unverified native drawing camera")
            role = "drawing_camera"
        source_facts = plain(row.get("properties", {}))
        if camera is not None:
            source_facts["native_camera"] = plain(camera)
        spatial_facts = plain(row.get("spatial_facts", {}))
        if isinstance(spatial_facts, Mapping):
            source_facts = {**source_facts, "spatial_facts": spatial_facts}
        sources.append(SourceObject(id=row["id"], source_id=guid, source_role=role,
            source_class=row["ifc_class"], level_ref=row.get("level_ref"),
            container_refs=tuple(row.get("container_refs", ())),
            geometry_refs=(mesh.id,) if mesh else (),
            factual_properties=source_facts, uncertainties=uncertainty,
            provenance={"adapter": "bonsai-live/1", "project_global_id": project,
                        "ifc_source_identity": source_identity, "step_id": step,
                        "ifc_class": row["ifc_class"]}))
        identity_map[row["id"]] = {"global_id": guid, "step_id": step,
                                  "project_global_id": project, "ifc_source_identity": source_identity,
                                  "canonical_object_id": row["id"], "geometry_refs": (mesh.id,) if mesh else (),
                                  "geometry_digest": digest([mesh.to_dict()] if mesh else []),
                                  "capture_identity": identity}
    context = AnalysisContext(contract_version=NEUTRAL_SCENE_V2, source_schema=identity.get("schema", "IFC"),
        adapter_version="bonsai-live/1", source_length_unit="m", analysis_length_unit="m",
        world_coordinate_system={"frame": "world", "project_global_id": project,
                                 "ifc_source_identity": source_identity}, level_references=(),
        analysis_plane=plane, geometry_tolerance=1e-6, topology_tolerance=1e-6,
        walking_body_profiles=(), visual_height_bands=(), capability_flags={"has_3d_geometry": bool(meshes)},
        input_mode="ifc")
    openings, opening_refs = [], {}
    for row in capture.records:
        if "IfcOpeningElement" not in ifc_ancestry(identity.get("schema"), row["ifc_class"]):
            continue
        source = next((source for source in sources if source.id == row["id"]), None)
        if source is None:
            continue
        facts = row.get("opening_facts", {})
        opening_id = "ifc-opening:" + source.source_id
        hosts = tuple("ifc-object:" + guid for guid in facts.get("host_source_ids", ()))
        fillings = tuple("ifc-object:" + guid for guid in facts.get("filling_source_ids", ()))
        openings.append(SourceOpening(id=opening_id, source_id=source.source_id, host_refs=hosts,
            geometry_refs=source.geometry_refs, opening_kind=row["ifc_class"],
            provenance={"method": "ifc4_voids_element", "schema": identity.get("schema", "IFC"),
                        "filling_source_refs": fillings}, uncertainties=source.uncertainties))
        for ref in (*hosts, *fillings):
            opening_refs.setdefault(ref, []).append(opening_id)
    sources = [replace(source, opening_refs=tuple(opening_refs.get(source.id, ()))) for source in sources]
    scene = NeutralSceneV2(context=context, analysis_domain=None, source_objects=tuple(sources),
                           geometries=tuple(meshes), openings=tuple(openings),
                           authored_groups=tuple(AuthoredGroup.from_dict(group) for group in identity.get("authored_groups", ())))
    scene, legacy_map, legacy_diagnostics = _enroll_legacy(scene, legacy_bindings)
    identity_map.update(legacy_map)
    diagnostics.extend(legacy_diagnostics)
    structural_context = StructuralContext.from_plane(plane)
    structural_scene = structural_b4_view(scene, context=structural_context)
    structural_fingerprint = digest({"sources": structural_source_facts(structural_scene),
                                     "context": structural_context.to_dict()})
    full_fingerprint = source_capture_fingerprint(scene)
    # A capture fingerprint describes stable facts. Volatile observation remains
    # separately available to runtime freshness guards and never affects B4 consent.
    capture_fingerprint = source_capture_fingerprint(scene)
    audit = validate_support_binding(scene, support_binding, capture_fingerprint=capture_fingerprint)
    return BonsaiLiveScene(scene, structural_scene, structural_context, freeze(identity_map), freeze(audit),
                           structural_fingerprint, full_fingerprint, capture_fingerprint, freeze(diagnostics))

