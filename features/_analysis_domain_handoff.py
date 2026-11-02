"""Private, session-local AnalysisDomain choice over verified planar geometry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from hashlib import sha256
import json
from math import isfinite

from shapely import constrained_delaunay_triangles
from shapely.errors import GEOSException
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import unary_union

from .geometry_substitutes import mass_patch_from_mesh
from .geometry_views import component_shape, plan_projection
from .scene_contract import AnalysisDomain, AnalysisPlane, MeshGeometry3D, NeutralSceneV2


def _digest(value: object) -> str:
    """Bind a session choice to exact JSON-compatible input bytes."""
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def structural_source_facts(scene: NeutralSceneV2) -> dict[str, object]:
    """Bind structural source geometry independently of the active query plane."""
    refs = {ref for source in scene.source_objects for ref in source.geometry_refs}
    refs.update(ref for opening in scene.openings for ref in opening.geometry_refs)
    return {"identity": dict(scene.context.world_coordinate_system),
            "sources": [source.to_dict() for source in sorted(scene.source_objects, key=lambda source: source.id)],
            "openings": [opening.to_dict() for opening in sorted(scene.openings, key=lambda opening: opening.id)],
            "geometries": [mesh.to_dict() for mesh in sorted(scene.geometries, key=lambda mesh: mesh.id)
                           if mesh.id in refs]}


def _frame(scene: NeutralSceneV2, request: Mapping[str, object]) -> dict[str, object]:
    """Require one explicit compatible caller frame without requiring floor metadata."""
    plane = request.get("analysis_plane")
    if not isinstance(plane, AnalysisPlane) or plane != scene.context.analysis_plane:
        raise ValueError("analysis_plane must equal the scene AnalysisPlane")
    if request.get("units") != "m" or scene.context.analysis_length_unit != "m":
        raise ValueError("analysis frame requires metre analysis units")
    for key in ("datum_m", "cut_height_m"):
        value = request.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be an explicit finite number")
        try:
            valid = isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"{key} must be an explicit finite number")
    try:
        valid_height = isfinite(request["datum_m"] + request["cut_height_m"])
    except OverflowError:
        valid_height = False
    if not valid_height:
        raise ValueError("datum plus cut height must be finite")
    return {"plane": plane.to_dict(), "units": "m", "datum_m": request["datum_m"],
            "cut_height_m": request["cut_height_m"]}


def _polygon(value: object) -> Polygon:
    """Accept only one exact finite polygon, preserving any supported holes."""
    try:
        geometry = shape(value) if isinstance(value, Mapping) else value
        coordinates = [coord for ring in (geometry.exterior, *geometry.interiors)
                       for point in ring.coords for coord in point]
    except (AttributeError, TypeError, ValueError, GEOSException) as exc:
        raise ValueError("candidate_polygon_unsupported") from exc
    if (not isinstance(geometry, Polygon) or geometry.is_empty or not geometry.is_valid
            or geometry.area <= 0 or not all(isfinite(coord) for coord in coordinates)):
        raise ValueError("candidate_polygon_invalid_or_disjoint")
    return geometry


def _project_authored(scene: NeutralSceneV2, domain: AnalysisDomain, outline: object = None) -> Polygon:
    """Use the domain's actual unique mesh refs as its canonical selected shape."""
    refs = domain.geometry_refs
    if not refs or len(set(refs)) != len(refs):
        raise ValueError("authored_geometry_refs_missing_or_duplicate")
    parts = []
    for ref in refs:
        matches = [mesh for mesh in scene.geometries if mesh.id == ref]
        if len(matches) != 1 or matches[0].units != "m":
            raise ValueError("authored_geometry_ref_unresolved_or_unsupported")
        components = plan_projection(mass_patch_from_mesh(matches[0]),
                                     scene.context.analysis_plane).components
        part = component_shape(components)
        if part is None:
            raise ValueError("authored_geometry_projection_unavailable")
        parts.append(part)
    polygon = _polygon(unary_union(parts))
    if outline is not None and not polygon.equals(_polygon(outline)):
        raise ValueError("authored_outline_projection_mismatch")
    return polygon


def _inferred_mesh(polygon: Polygon, plane: AnalysisPlane, version_id: str,
                   source_revision: str, request_id: str) -> MeshGeometry3D:
    """Make a derived plan support only when its projection equals the scope."""
    try:
        triangles = list(constrained_delaunay_triangles(polygon).geoms)
    except GEOSException as exc:
        raise ValueError("inferred_tessellation_unsupported") from exc
    if not triangles or any(part.geom_type != "Polygon" or len(part.exterior.coords) != 4
                            for part in triangles):
        raise ValueError("inferred_tessellation_unsupported")
    vertices = []
    faces = []
    for triangle in triangles:
        face = []
        for x, y in list(triangle.exterior.coords)[:3]:
            # The B2 polygon is plane-local; reconstruct world coordinates for
            # the existing MeshGeometry3D -> MassPatch -> plan_projection path.
            vertices.append(tuple(plane.origin[i] + x * plane.basis[0][i]
                                  + y * plane.basis[1][i] for i in range(3)))
            face.append(len(vertices) - 1)
        faces.append(tuple(face))
    mesh = MeshGeometry3D(
        id=f"derived-domain:{_digest([version_id, source_revision, request_id])}",
        vertices=tuple(vertices), triangle_indices=tuple(faces), normals=(),
        is_manifold=False, is_closed=False,
        local_to_world_provenance={"method": "session_derived_scope_not_physical_mass",
                                   "candidate_version_id": version_id,
                                   "source_revision": source_revision,
                                   "analysis_plane": plane.to_dict(), "request_id": request_id},
        source_representation_id=None, tessellation_settings={}, units="m",
    )
    projected = component_shape(plan_projection(mass_patch_from_mesh(mesh), plane).components)
    if projected is None or not projected.equals(polygon):
        raise ValueError("inferred_projection_mismatch")
    return mesh


def _catalog(scene: NeutralSceneV2, authored: Sequence[Mapping[str, object]],
             b2: Mapping[str, object] | None, source_revision: str,
             frame_id: str, request_id: str) -> dict[str, dict[str, object]]:
    """Build retained candidate versions from authored refs and private B2 scopes."""
    items = list(authored)
    if scene.analysis_domain is not None:
        items.insert(0, {"analysis_domain": scene.analysis_domain})
    catalog: dict[str, dict[str, object]] = {}
    for item in items:
        domain = item.get("analysis_domain")
        if not isinstance(domain, AnalysisDomain):
            raise ValueError("authored candidate needs AnalysisDomain")
        version_id = item.get("version_id", domain.id)
        if not isinstance(version_id, str) or not version_id or version_id in catalog:
            raise ValueError("candidate_version_id_missing_or_duplicate")
        try:
            polygon = _project_authored(scene, domain, item.get("selected_polygon"))
            reason = None
        except ValueError as exc:
            polygon, reason = None, str(exc)
        catalog[version_id] = {"id": domain.id, "version_id": version_id,
                               "source": "authored", "domain": domain, "polygon": polygon,
                               "reason": reason, "source_refs": tuple(domain.geometry_refs),
                               "identity": _digest({"domain": domain.to_dict(),
                                                    "selected_polygon": item.get("selected_polygon")}),
                               "source_revision": source_revision, "frame_id": frame_id,
                               "request_id": request_id}
    if b2 is not None:
        for scope in b2["scope_proposals"]:
            version_id = f"inferred:{scope['id']}:{_digest([source_revision, request_id, scope['geometry']])}"
            if version_id in catalog:
                raise ValueError("candidate_version_id_duplicate")
            try:
                polygon = _polygon(scope["geometry"]["geojson"])
                reason = ("unresolved_local_aperture" if scope["local_unresolved_aperture_refs"]
                          else None)
            except ValueError as exc:
                polygon, reason = None, str(exc)
            # Only the matching qualified contour can declare semantic boundary
            # members; wall refs alone do not prove component membership.
            contours = [contour for contour in b2.get("enclosure_contours", ())
                        if contour.get("scope_ref") == scope["id"]]
            member_refs: tuple[str, ...] = ()
            if len(contours) == 1 and polygon is not None:
                try:
                    same_contour = _polygon(contours[0]["geometry"]["geojson"]).equals(polygon)
                except (KeyError, TypeError, ValueError):
                    same_contour = False
                refs = contours[0].get("semantic_contribution_refs", ())
                matches = ([tuple(source.id for source in scene.source_objects
                                  if ref in (source.id, source.source_id)) for ref in refs]
                           if isinstance(refs, (list, tuple)) and all(isinstance(ref, str) for ref in refs)
                           else [])
                if (same_contour and matches and all(len(group) == 1 for group in matches)
                        and len({group[0] for group in matches}) == len(matches)):
                    member_refs = tuple(refs)
            catalog[version_id] = {"id": scope["id"], "version_id": version_id,
                                   "source": "inferred", "domain": None,
                                   "polygon": polygon, "reason": reason,
                                   "identity": _digest(scope),
                                   "source_refs": tuple(scope["wall_source_refs"]),
                                   "boundary_member_source_ids": member_refs,
                                   "unresolved_aperture_refs": tuple(scope["local_unresolved_aperture_refs"]),
                                   "source_revision": source_revision, "frame_id": frame_id,
                                   "request_id": request_id}
    return catalog


def _qualified(scene: NeutralSceneV2, candidate: Mapping[str, object],
               source_revision: str, request_id: str) -> tuple[AnalysisDomain, Polygon, MeshGeometry3D | None]:
    """Recheck exact authored or inferred shape immediately before consumption."""
    if candidate["reason"]:
        raise ValueError(str(candidate["reason"]))
    polygon = _polygon(candidate["polygon"])
    if candidate["source"] == "authored":
        domain = candidate["domain"]
        current = _project_authored(scene, domain, polygon)
        return domain, current, None
    mesh = _inferred_mesh(polygon, scene.context.analysis_plane,
                          str(candidate["version_id"]), source_revision, request_id)
    if any(existing.id == mesh.id for existing in scene.geometries):
        raise ValueError("derived_geometry_ref_conflict")
    domain = AnalysisDomain(
        id=f"selected:{_digest(candidate['version_id'])}", geometry_refs=(mesh.id,),
        source_id=None, selection_method="explicit_session_confirmation_of_inferred_candidate",
        provenance={"candidate_version_id": candidate["version_id"],
                    "source_revision": source_revision, "request_id": request_id,
                    "source_refs": candidate["source_refs"],
                    **({"boundary_member_source_ids": candidate["boundary_member_source_ids"]}
                       if candidate["boundary_member_source_ids"] else {})},
    )
    return domain, polygon, mesh


def _conflicts(candidate: Mapping[str, object], catalog: Mapping[str, Mapping[str, object]]) -> list[dict[str, str]]:
    """Identify only opposite-source outlines that disagree with this choice."""
    return sorted(({"id": str(other["version_id"]), "identity": str(other["identity"])}
                   for other in catalog.values() if other["source"] != candidate["source"]
                   and other["polygon"] is not None
                   and not other["polygon"].equals(candidate["polygon"])), key=lambda item: item["id"])


def _session(snapshot: Mapping[str, object] | None) -> dict[str, object]:
    """Reduce the event log and reject a claimed projection it cannot produce."""
    old = dict(snapshot or {})
    events = old.get("events", ())
    if not isinstance(events, (list, tuple)):
        raise ValueError("inconsistent_session_state")
    state = {"revision": 0, "current_version_id": None, "current_binding": None,
             "conflict": False, "invalidated": False, "events": list(events)}
    seen: dict[str, Mapping[str, object]] = {}
    for event in events:
        if not isinstance(event, Mapping) or not isinstance(event.get("action"), Mapping):
            raise ValueError("inconsistent_session_state")
        action, status = event["action"], event.get("status")
        kind = action.get("kind")
        if status == "accepted" and kind in {"confirm", "replace"}:
            event_id = action.get("action_id")
            if (not isinstance(event_id, str) or event_id in seen
                    or action.get("expected_session_revision") != state["revision"]
                    or not all(isinstance(action.get(key), str) and action[key]
                               for key in ("actor", "time", "reason", "expected_source_revision",
                                           "expected_plane_identity", "expected_request_identity",
                                           "expected_candidate_identity"))):
                raise ValueError("inconsistent_session_state")
            seen[event_id] = action
            if kind == "confirm":
                version = action.get("candidate_version_id")
                binding = event.get("binding")
                conflicts = event.get("acknowledged_conflicts", [])
                acknowledged = action.get("acknowledged_conflict_ids", ())
                if (not isinstance(conflicts, list) or not isinstance(acknowledged, (list, tuple))
                        or any(not isinstance(item, str) for item in acknowledged)
                        or any(not isinstance(item, Mapping) or not isinstance(item.get("id"), str)
                               or not isinstance(item.get("identity"), str) for item in conflicts)
                        or [item["id"] for item in conflicts] != sorted(acknowledged)):
                    raise ValueError("inconsistent_session_state")
                expected = {"source_revision": action["expected_source_revision"],
                            "frame_id": action["expected_plane_identity"],
                            "request_id": action["expected_request_identity"],
                            "candidate_identity": action["expected_candidate_identity"],
                            "acknowledged_conflicts": conflicts}
                if not isinstance(version, str) or binding != expected:
                    raise ValueError("inconsistent_session_state")
                if (state["current_version_id"] != version or state["invalidated"]
                        or state["current_binding"] != binding):
                    state["revision"] += 1
                state.update(current_version_id=version, current_binding=binding, invalidated=False)
            else:
                if (not isinstance(action.get("old_version_id"), str)
                        or not isinstance(action.get("new_version_id"), str)):
                    raise ValueError("inconsistent_session_state")
                state["revision"] += 1
                if state["current_version_id"] == action["old_version_id"]:
                    state.update(current_version_id=None, current_binding=None)
        elif status == "refused" and kind in {"confirm", "replace"}:
            event_id = action.get("action_id")
            if not isinstance(event_id, str) or event_id in seen:
                raise ValueError("inconsistent_session_state")
            seen[event_id] = action
        elif status == "conflict" and kind in {"confirm", "replace"}:
            event_id = action.get("action_id")
            if event_id not in seen or seen[event_id] == action:
                raise ValueError("inconsistent_session_state")
            if not state["conflict"]:
                state["revision"] += 1
            state["conflict"] = True
        elif status == "observed" and kind == "input_invalidated":
            if (action.get("candidate_version_id") != state["current_version_id"]
                    or state["invalidated"]
                    or event.get("reason") not in {"current_input_changed", "current_conflict_changed"}):
                raise ValueError("inconsistent_session_state")
            state["invalidated"] = True
            if event["reason"] == "current_conflict_changed":
                state["revision"] += 1
        else:
            raise ValueError("inconsistent_session_state")
    if snapshot is not None and any(old.get(key, value) != value for key, value in state.items()):
        raise ValueError("inconsistent_session_state")
    return state


def domain_handoff(scene: NeutralSceneV2, *, candidates: Sequence[Mapping[str, object]],
                   session_state: Mapping[str, object] | None, action: Mapping[str, object] | None,
                   expected_session_revision: int | None, expected_source_revision: str | None,
                   frame_request: Mapping[str, object], b2: Mapping[str, object] | None = None,
                   b2_request: Mapping[str, object] | None = None,
                   source_revision: str | None = None, frame_id: str | None = None) -> dict[str, object]:
    """Apply one bounded action and expose only a qualified current-domain preview."""
    if not isinstance(scene, NeutralSceneV2):
        raise TypeError("domain handoff requires NeutralSceneV2")
    frame = _frame(scene, frame_request)
    if b2_request is not None and any(frame_request.get(key) != b2_request.get(key)
                                      for key in ("analysis_plane", "units", "datum_m", "cut_height_m")):
        raise ValueError("B2 request must use the same explicit frame")
    # Explicit structural/frame identities separate stable source from camera query identity.
    source_revision = source_revision if source_revision is not None else _digest(scene.to_dict())
    frame_id = frame_id if frame_id is not None else _digest(frame)
    if not all(isinstance(value, str) and value.strip() for value in (source_revision, frame_id)):
        raise ValueError("source_revision and frame_id must be nonempty identities")
    request_id = _digest({key: (value.to_dict() if isinstance(value, AnalysisPlane) else value)
                          for key, value in b2_request.items()}) if b2_request is not None else frame_id
    catalog = _catalog(scene, candidates, b2, source_revision, frame_id, request_id)
    qualified = {}

    def qualify(candidate):
        """Reuse one exact qualification result across consent and preview."""
        version = candidate["version_id"]
        if version not in qualified:
            qualified[version] = _qualified(scene, candidate, source_revision, request_id)
        return qualified[version]
    try:
        state = _session(session_state)
        attempt = {"status": "none", "reason": None}
        session_error = False
    except ValueError:
        # Discard the untrusted projection; a fresh session requires confirmation.
        state = _session(None)
        attempt = {"status": "refused", "reason": "inconsistent_session_state"}
        session_error = True
    focused_version_id = None
    if action is not None and not session_error:
        kind = action.get("kind")
        if kind in {"hover", "select"}:
            focused_version_id = action.get("candidate_version_id")
            attempt = ({"status": "preview" if kind == "hover" else "selected", "reason": None}
                       if focused_version_id in catalog else
                       {"status": "refused", "reason": "candidate_version_unavailable"})
        elif kind in {"confirm", "replace"}:
            event_id = action.get("action_id")
            if not isinstance(event_id, str) or not event_id.strip():
                raise ValueError("state-changing action requires action_id")
            if not all(isinstance(action.get(key), str) and action[key].strip()
                       for key in ("actor", "time", "reason")):
                raise ValueError("state-changing action requires actor, time and reason")
            payload = dict(action)
            prior = [event for event in state["events"] if event["action"].get("action_id") == event_id]
            reason = None
            if prior:
                if all(event["action"] == payload for event in prior):
                    attempt = {"status": "duplicate", "reason": None}
                else:
                    state["events"].append({"action": payload, "status": "conflict"})
                    if not state["conflict"]:
                        state["revision"] += 1
                    state["conflict"] = True
                    attempt = {"status": "refused", "reason": "conflicting_action_id"}
            else:
                target_id = action.get("candidate_version_id") if kind == "confirm" else action.get("new_version_id")
                candidate = catalog.get(target_id)
                if (expected_session_revision != action.get("expected_session_revision")
                        or expected_session_revision != state["revision"]):
                    reason = "stale_session_revision"
                elif (expected_source_revision != action.get("expected_source_revision")
                      or expected_source_revision != source_revision):
                    reason = "stale_source_revision"
                elif action.get("expected_plane_identity") != frame_id:
                    reason = "stale_or_incompatible_plane"
                elif action.get("expected_request_identity") != request_id:
                    reason = "stale_request_identity"
                elif state["conflict"]:
                    reason = "unresolved_session_conflict"
                elif candidate is None:
                    reason = "candidate_version_unavailable"
                elif action.get("expected_candidate_identity") != candidate["identity"]:
                    reason = "stale_candidate_identity"
                elif kind == "replace" and (action.get("old_version_id") not in catalog
                                            or action.get("old_version_id") == target_id):
                    reason = "replacement_target_unavailable"
                else:
                    try:
                        qualify(candidate)
                    except ValueError as exc:
                        reason = str(exc)
                if reason is None and kind == "confirm" and candidate is not None:
                    disagreements = _conflicts(candidate, catalog)
                    if [item["id"] for item in disagreements] != sorted(action.get("acknowledged_conflict_ids", ())):
                        reason = "authored_inferred_conflict_unacknowledged"
                if reason is None:
                    if kind == "confirm":
                        new_binding = {"source_revision": source_revision,
                                       "frame_id": frame_id, "request_id": request_id,
                                       "candidate_identity": candidate["identity"],
                                       "acknowledged_conflicts": disagreements}
                        if (state["current_version_id"] != target_id or state["invalidated"]
                                or state["current_binding"] != new_binding):
                            state["revision"] += 1
                        state["current_version_id"] = target_id
                        state["current_binding"] = new_binding
                        state["invalidated"] = False
                    else:
                        state["revision"] += 1
                        if state["current_version_id"] == action["old_version_id"]:
                            state["current_version_id"] = None
                            state["current_binding"] = None
                    attempt = {"status": "accepted", "reason": None}
                else:
                    attempt = {"status": "refused", "reason": reason}
                event = {"action": payload, **attempt}
                if attempt["status"] == "accepted" and kind == "confirm":
                    event.update(binding=state["current_binding"], acknowledged_conflicts=disagreements)
                state["events"].append(event)
        else:
            raise ValueError("unsupported session action")
    active = catalog.get(state["current_version_id"])
    binding = {"source_revision": source_revision, "frame_id": frame_id, "request_id": request_id,
               "candidate_identity": active["identity"] if active is not None else None,
               "acknowledged_conflicts": state["current_binding"].get("acknowledged_conflicts", [])
               if isinstance(state["current_binding"], Mapping) else []}
    if (state["current_version_id"] is not None and not state["invalidated"]
            and state["current_binding"] != binding):
        # Record observed input drift once so restoring earlier bytes cannot
        # silently resurrect a confirmation made for a different observation.
        state["invalidated"] = True
        state["events"].append({"action": {"kind": "input_invalidated",
                                            "candidate_version_id": state["current_version_id"]},
                                "status": "observed", "reason": "current_input_changed"})
    if (active is not None and not state["invalidated"] and state["current_binding"] == binding
            and _conflicts(active, catalog) != binding["acknowledged_conflicts"]):
        # A new or changed disagreement needs fresh consent before consumption.
        state["invalidated"] = True
        state["revision"] += 1
        state["events"].append({"action": {"kind": "input_invalidated",
                                            "candidate_version_id": state["current_version_id"]},
                                "status": "observed", "reason": "current_conflict_changed"})
    current = {"status": "not_available", "candidate_version_id": state["current_version_id"],
               "reason": "no_qualified_current_choice"}
    domain = polygon = preview = None
    domain_geometries = ()
    if state["conflict"]:
        current.update(status="conflict", reason="unresolved_session_conflict")
    elif active is not None and not state["invalidated"] and state["current_binding"] == binding:
        try:
            domain, polygon, mesh = qualify(active)
            child_domain = domain
            if domain.source_id is not None:
                matches = [source for source in scene.source_objects if source.source_id == domain.source_id]
                if len(matches) != 1 or (matches[0].source_role or "").strip().lower() not in {
                        "slab", "floor", "space", "spatial_zone", "spatial_container"}:
                    # Provenance is not permission to erase a physical source from occupancy.
                    child_domain = replace(domain, source_id=None,
                                           provenance={**domain.provenance,
                                                       "authored_source_id": domain.source_id})
            child = replace(scene, analysis_domain=child_domain,
                            geometries=scene.geometries + ((mesh,) if mesh is not None else ()))
            # Keep the full view private: its rectangle fallback is not an
            # authorized exact-domain free-space/topology input.
            from .neutral_scene_views import analysis_scene_view
            view = analysis_scene_view(child)
            domain_geometries = ((mesh,) if mesh is not None else
                                 tuple(next(mesh for mesh in scene.geometries if mesh.id == ref)
                                       for ref in domain.geometry_refs))
            preview = {"label": f"Active: {active['id']} ({active['source']})",
                       "candidate_version_id": active["version_id"],
                       "outline": mapping(polygon), "physical_occupancy": view["physical_occupancy"],
                       "view_bounds": view["size"]}
            current.update(status="active", reason=None)
        except ValueError as exc:
            current["reason"] = str(exc)
    elif state["current_version_id"] is not None:
        current["reason"] = "current_input_changed_or_candidate_unavailable"
    candidate_previews = [{"id": item["id"], "version_id": item["version_id"],
                           "source": item["source"],
                           "status": ("refused" if item["reason"] is not None else
                                      "confirmed" if current["status"] == "active" and item["version_id"] == active["version_id"] else
                                      "selected" if attempt["status"] == "selected" and item["version_id"] == focused_version_id else
                                      "preview" if attempt["status"] == "preview" and item["version_id"] == focused_version_id else
                                      "provisional"),
                           "identity": item["identity"],
                           "reason": item["reason"],
                           "outline": mapping(item["polygon"]) if item["polygon"] is not None else None,
                           "source_refs": item["source_refs"],
                           "unresolved_aperture_refs": item.get("unresolved_aperture_refs", ())}
                          for item in catalog.values()]
    return {"attempt": attempt, "current": current, "session_revision": state["revision"],
            "session_state": state, "candidates": candidate_previews,
            "selected_candidate_id": active["id"] if current["status"] == "active" else None,
            "analysis_domain": domain, "domain_geometries": domain_geometries,
            "scope_polygon": mapping(polygon) if polygon is not None else None,
            "preview": preview, "provenance": {"source_revision": source_revision,
                                               "frame_id": frame_id, "request_id": request_id},
            "downstream": {"formal_field": "not_available", "topology": "not_available",
                           "route": "not_available"}}
