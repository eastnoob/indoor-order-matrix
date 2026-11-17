"""Explicit, private semantic enclosure diagnostics over unchanged source meshes."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from math import isfinite

import numpy as np
import trimesh
from shapely.geometry import GeometryCollection, LineString, Polygon, mapping, shape
from shapely.ops import linemerge, polygonize_full, unary_union

from .geometry_substitutes import mass_patch_from_mesh
from .geometry_views import _project_to_plane, component_shape, plan_projection, vertical_intervals_at
from .scene_contract import AnalysisPlane, NeutralSceneV2


# Ten square millimetres filters measured mesh slivers without treating a door-sized gap as closed.
DEFAULT_APERTURE_RESIDUAL_TOLERANCE_M2 = 1e-5


def validate_request(scene, request):
    """Reject incomplete measurement/task authority before computing any view."""
    if not isinstance(scene, NeutralSceneV2) or not isinstance(request, Mapping):
        raise TypeError("semantic enclosure requires NeutralSceneV2 and a request mapping")
    required = {"analysis_plane", "units", "datum_m", "cut_height_m", "contact_distance_m",
                "aperture_area_budget_m2", "default_closed_authority", "exclude_override_authority"}
    if required - request.keys():
        raise ValueError(f"missing semantic enclosure request fields: {sorted(required - request.keys())}")
    if not isinstance(request["analysis_plane"], AnalysisPlane) or request["analysis_plane"] != scene.context.analysis_plane:
        raise ValueError("analysis_plane must equal the scene AnalysisPlane")
    if request["units"] != "m" or scene.context.analysis_length_unit != "m":
        raise ValueError("semantic enclosure supports metre analysis units only")
    for key in ("datum_m", "cut_height_m", "contact_distance_m", "aperture_area_budget_m2",
                "aperture_residual_tolerance_m2"):
        if key not in request and key == "aperture_residual_tolerance_m2":
            continue
        value = request[key]
        try:
            finite = not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{key} must be a finite number, not a boolean")
        if key in {"contact_distance_m", "aperture_area_budget_m2", "aperture_residual_tolerance_m2"} and value < 0:
            raise ValueError(f"{key} must be nonnegative")
    try:
        finite_height = isfinite(request["datum_m"] + request["cut_height_m"])
    except OverflowError:
        finite_height = False
    if not finite_height:
        raise ValueError("datum plus cut height must be finite")
    authority = request["default_closed_authority"]
    override = request["exclude_override_authority"]
    if not isinstance(authority, str) or not authority.strip():
        raise ValueError("default_closed_authority must name the caller's scenario authority")
    if override is not None and (not isinstance(override, str) or not override.strip()):
        raise ValueError("exclude_override_authority must be an explicit authority string or None")


def _polygons(geometry):
    """Keep actual positive-area polygon components in deterministic order."""
    if geometry.geom_type == "Polygon":
        return [geometry] if geometry.area > 0 else []
    return sorted([polygon for part in getattr(geometry, "geoms", ()) for polygon in _polygons(part)],
                  key=lambda polygon: (polygon.bounds, polygon.area, polygon.wkb_hex))


def _geometry(geometry):
    """Serialize actual geometry with measured topology, without simplification."""
    polygons = _polygons(geometry)
    return {"geojson": mapping(geometry), "area_m2": geometry.area, "length_m": geometry.length,
            "polygon_components": len(polygons), "hole_count": sum(len(p.interiors) for p in polygons)}


def _jambs(geometry):
    """Merge tessellated segments so a connected jamb is counted once."""
    pending, lines = [geometry], []
    while pending:
        part = pending.pop()
        if part.geom_type in {"LineString", "LinearRing"} and part.length > 0:
            lines.append(LineString(part.coords))
        else:
            pending.extend(getattr(part, "geoms", ()))
    if not lines:
        return []
    merged = linemerge(lines)
    return sorted([merged] if merged.geom_type == "LineString" else list(merged.geoms),
                  key=lambda line: (line.bounds, line.wkb_hex))


def _aperture_span(extent, polygon, jambs, contact_budget, area_budget):
    """Measure the same local aperture span for leaves and authored openings."""
    overlap = extent.intersection(polygon)
    contacts = [{"jamb_index": index, "distance_m": extent.distance(jamb),
                 "exact_intersection": not extent.intersection(jamb).is_empty,
                 "exact_contact_length_m": extent.intersection(jamb).length,
                 "jamb_length_m": jamb.length, "within_contact_budget": extent.distance(jamb) <= contact_budget}
                for index, jamb in enumerate(jambs)]
    reached = [c for c in contacts if c["within_contact_budget"] and c["jamb_length_m"] > 0]
    return {"overlap": _geometry(overlap), "jamb_contacts": contacts,
            "qualified": bool(extent.is_valid and polygon.is_valid and polygon.area > area_budget
                              and (overlap.area > 0 or overlap.length > 0) and len(reached) >= 2)}


def _section(patch, mesh, height, solid):
    """Intersect each indexed edge once, then select actual occupied cut faces."""
    offsets = mesh.vertices[:, 2] - height
    cache, segments = {}, []
    coplanar = int(np.count_nonzero(np.all(offsets[mesh.faces] == 0, axis=1)))
    for face in mesh.faces:
        values = offsets[face]
        if min(values) > 0 or max(values) < 0 or np.all(values == 0):
            continue
        points = []
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            key = tuple(sorted((int(a), int(b))))
            if key not in cache:
                first, second = key
                oa, ob = offsets[first], offsets[second]
                if oa == 0 and ob == 0:
                    hits = [mesh.vertices[first].tolist(), mesh.vertices[second].tolist()]
                elif oa == 0 or ob == 0:
                    hits = [mesh.vertices[first if oa == 0 else second].tolist()]
                elif oa * ob < 0:
                    hit = mesh.vertices[first] + (-oa / (ob - oa)) * (mesh.vertices[second] - mesh.vertices[first])
                    hit[2] = height
                    hits = [hit.tolist()]
                else:
                    hits = []
                cache[key] = hits
            for hit in cache[key]:
                if hit not in points:
                    points.append(hit)
        if len(points) == 2 and points[0] != points[1]:
            segments.append(points)
    linework = unary_union([LineString([p[:2] for p in segment]) for segment in segments])
    polygons, cuts, dangles, invalid = polygonize_full(linework)
    residuals = {"cuts": len(cuts.geoms), "dangles": len(dangles.geoms), "invalid_rings": len(invalid.geoms)}
    occupied = []
    if solid and not coplanar:
        # Closed loops can surround voids. Triangle/Z crossings decide which
        # polygonized faces are material, instead of filling every loop.
        for polygon in polygons.geoms:
            point = polygon.representative_point()
            intervals = vertical_intervals_at(patch, (point.x, point.y)).intervals
            if any(lower < height < upper for lower, upper in intervals):
                occupied.append(polygon)
    qualified = solid and not coplanar and not any(residuals.values())
    return unary_union(occupied), {"qualified": qualified, "coplanar_faces": coplanar, **residuals,
                                   "segments_plane_xyz": segments,
                                   "method": "shared_indexed_edge_once_exact_plane_no_snap",
                                   "reason": None if qualified else "coplanar_or_unclosed_or_unqualified_solid"}


def _observe_mesh(geometry, plane, height):
    """Measure a mesh without repairs, placement reapplication or flag mutation."""
    if geometry.units != "m" or not geometry.vertices or not geometry.triangle_indices:
        return {"geometry_ref": geometry.id, "refusal": "missing_or_non_metre_geometry"}, GeometryCollection(), GeometryCollection()
    patch = mass_patch_from_mesh(geometry)
    patch = replace(patch, vertices=tuple(_project_to_plane(vertex, plane) for vertex in patch.vertices))
    mesh = trimesh.Trimesh(patch.vertices, patch.triangle_indices, process=False)
    duplicate = len({tuple(sorted(face)) for face in patch.triangle_indices}) != len(patch.triangle_indices)
    degenerate = int(np.count_nonzero(mesh.area_faces == 0))
    nonmanifold_edges = bool(np.any(np.bincount(mesh.edges_unique_inverse) > 2))
    components = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)))
    vertices = [set(mesh.faces[part].ravel()) for part in components]
    pinched = any(first.intersection(second) for i, first in enumerate(vertices) for second in vertices[i + 1:])
    valid_faces = not (duplicate or degenerate)
    solid = bool(valid_faces and not pinched and not nonmanifold_edges and mesh.is_watertight and mesh.is_winding_consistent
                 and patch.is_closed is not False and patch.is_manifold is not False)
    # Surface spans have independent qualification; a thin leaf need not be a
    # closed volume. Actual projected faces/edges supply extent, never a hull.
    extent = component_shape(plan_projection(patch).components)
    method = "actual_projected_triangle_faces"
    if extent is None:
        edges = [LineString([patch.vertices[a][:2], patch.vertices[b][:2]])
                 for face in patch.triangle_indices for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0]))
                 if patch.vertices[a][:2] != patch.vertices[b][:2]]
        extent = unary_union(edges)
        method = "actual_projected_triangle_edges"
    cut, section = _section(patch, mesh, height, solid)
    observation = {"geometry_ref": geometry.id, "source_is_closed": geometry.is_closed,
                   "source_is_manifold": geometry.is_manifold, "watertight": bool(mesh.is_watertight),
                   "winding_consistent": bool(mesh.is_winding_consistent), "duplicate_faces": duplicate,
                   "degenerate_faces": degenerate, "pinched_components": bool(pinched),
                   "nonmanifold_edges": nonmanifold_edges,
                   "solid_qualified": solid, "span_qualified": valid_faces and extent.is_valid and not extent.is_empty,
                   "span_basis": "actual_nondegenerate_faces_independent_of_solid_connectivity",
                   "extent_method": method, "extent": _geometry(extent), "section": section | {"geometry": _geometry(cut)},
                   "qualification_limit": "indexed_connectivity_and_winding; self_intersections_not_certified"}
    return observation, extent, cut


def _kind(source):
    """Use declared class/role only, retaining conflicts instead of guessing."""
    classes = {"ifcwall": "wall", "ifcwallstandardcase": "wall", "ifccolumn": "column",
               "ifcdoor": "door", "ifcwindow": "window", "ifcbeam": "beam", "ifcfurnishingelement": "furniture"}
    role = (source.source_role or "").lower()
    declared = classes.get((source.source_class or "").lower())
    if declared and role and declared != role:
        return "conflict"
    return declared or role or "unknown"


def _source_uncertainty_refusal(uncertainties):
    """Respect explicit invalid/missing evidence while retaining other limits."""
    return any(any(word in uncertainty.code.lower() for word in ("conflict", "invalid", "malformed", "unsupported", "missing_geometry", "partial_geometry"))
               for uncertainty in uncertainties)


def semantic_enclosure_diagnostics(scene, request, opening_diagnostics):
    """Compute unselected scenario evidence; never promote or subtract sources."""
    plane = request["analysis_plane"]
    height = request["datum_m"] + request["cut_height_m"]
    contact_budget, area_budget = request["contact_distance_m"], request["aperture_area_budget_m2"]
    residual_tolerance = request.get("aperture_residual_tolerance_m2", DEFAULT_APERTURE_RESIDUAL_TOLERANCE_M2)
    geometries, duplicate_ids = {}, set()
    for geometry in scene.geometries:
        if geometry.id in geometries:
            duplicate_ids.add(geometry.id)
        geometries[geometry.id] = geometry
    observed = {ref: _observe_mesh(geometry, plane, height) for ref, geometry in geometries.items() if ref not in duplicate_ids}
    source_ids = [source.id for source in scene.source_objects]
    duplicate_sources = {ref for ref in source_ids if source_ids.count(ref) > 1}
    rows, sources = [], {}
    for source in scene.source_objects:
        refs = source.geometry_refs
        missing = [ref for ref in refs if ref not in observed]
        parts = [observed[ref] for ref in refs if ref in observed]
        extent = unary_union([part[1] for part in parts])
        cut = unary_union([part[2] for part in parts])
        layout_facts = source.factual_properties.get("OM_Layout", {})
        excluded = isinstance(layout_facts, Mapping) and layout_facts.get("AnalysisParticipation") == "exclude"
        uncertainties = source.uncertainties + tuple(u for u in scene.uncertainties if source.id in u.source_refs)
        refusal = ("duplicate_source_identity" if source.id in duplicate_sources else
                   "missing_or_duplicate_geometry_refs" if missing or not refs else
                   "source_uncertainty_refuses_qualification" if _source_uncertainty_refusal(uncertainties) else
                   "authored_exclude_without_task_override" if excluded and request["exclude_override_authority"] is None else
                   "declared_class_role_conflict" if _kind(source) == "conflict" else None)
        usable = not refusal and all(part[0].get("section", {}).get("qualified", False) for part in parts)
        span = not refusal and all(part[0].get("span_qualified", False) for part in parts)
        row = {"source": source.to_dict(), "source_ref": source.id, "kind": _kind(source),
               "missing_geometry_refs": missing, "mesh_observations": [part[0] for part in parts],
               "refusal": refusal, "authored_excluded": excluded,
               "task_exclude_override_authority": request["exclude_override_authority"] if excluded else None,
               "section_qualified": usable, "span_qualified": span,
               "physical_section": _geometry(cut), "extent": _geometry(extent),
               "enclosure_support_eligible": usable and _kind(source) in {"wall", "column"}}
        rows.append(row)
        sources[source.id] = (source, row, extent, cut)
    apertures, aperture_shapes, jamb_shapes = [], {}, {}
    for source, row, extent, cut in sources.values():
        if row["kind"] != "wall" or not row["enclosure_support_eligible"]:
            continue
        # Full-height mass is only a locator. Each residual needs its own
        # source span and local jamb evidence before becoming a carrier.
        for polygon in _polygons(extent.difference(cut)):
            ref = f"A{len(apertures) + 1}"
            jambs = _jambs(polygon.boundary.intersection(cut.boundary))
            apertures.append({"id": ref, "host_ref": source.id, "geometry": _geometry(polygon),
                              "jamb_sides": [mapping(jamb) for jamb in jambs], "above_area_budget": polygon.area > area_budget,
                              "significant_residual": polygon.area > residual_tolerance,
                              "classification": "host_projection_minus_cut_locator_residual", "scenario_closed": False,
                              "affected_scope_ids": [], "affected_contour_ids": []})
            aperture_shapes[ref], jamb_shapes[ref] = polygon, jambs
    openings = {}
    for opening in scene.openings:
        openings.setdefault(opening.id, []).append(opening)
    duplicate_openings = {ref for ref, records in openings.items() if len(records) > 1}
    opening_states = {record["id"]: record for record in opening_diagnostics if record["id"] not in duplicate_openings}
    opening_spans = {}
    for ref, records in openings.items():
        if ref in duplicate_openings:
            continue
        opening = records[0]
        parts = [(geometry_ref, observed[geometry_ref]) for geometry_ref in opening.geometry_refs if geometry_ref in observed]
        extent = unary_union([part[1][1] for part in parts])
        valid = bool(parts) and len(parts) == len(opening.geometry_refs) and all(part[1][0].get("span_qualified", False) for part in parts)
        alternatives = []
        for aperture in apertures:
            if opening.host_refs and aperture["host_ref"] not in opening.host_refs:
                continue
            polygon = aperture_shapes[aperture["id"]]
            evidence = _aperture_span(extent, polygon, jamb_shapes[aperture["id"]], contact_budget, area_budget)
            part_overlaps = [{"geometry_ref": geometry_ref, "overlap": _geometry(part[1].intersection(polygon))}
                             for geometry_ref, part in parts]
            # An authored opening must demonstrate the relevant whole span;
            # a remote/partial reference cannot be replaced by a leaf's fit.
            qualified = valid and evidence["qualified"] and all(p["overlap"]["area_m2"] > 0 or p["overlap"]["length_m"] > 0 for p in part_overlaps)
            alternatives.append(evidence | {"aperture_ref": aperture["id"], "host_ref": aperture["host_ref"],
                                            "geometry_ref_overlaps": part_overlaps, "qualified": qualified})
        opening_spans[ref] = {"source": opening.to_dict(), "alternatives": alternatives,
                              "qualified_aperture_refs": [a["aperture_ref"] for a in alternatives if a["qualified"]]}
    treatments, carriers = [], []
    for source, row, extent, cut in sources.values():
        if row["kind"] not in {"window", "door"}:
            continue
        linked = [opening for ref in source.opening_refs for opening in openings.get(ref, ())]
        authored_hosts = {host for opening in linked for host in opening.host_refs}
        authored_bad = (any(ref in duplicate_openings for ref in source.opening_refs)
                        or len(linked) != len(source.opening_refs) or bool(linked) and
                        (len(authored_hosts) > 1 or any(opening_states[o.id]["local_diagnostic_state"] not in {"diagnostic_only", "partial"}
                         or bool(opening_states[o.id]["omitted_host_refs"]) or _source_uncertainty_refusal(o.uncertainties)
                         or any(ref not in sources for ref in o.host_refs)
                         or any(ref not in observed or not observed[ref][0].get("span_qualified", False) for ref in o.geometry_refs)
                         for o in linked)))
        alternatives = []
        for aperture in apertures:
            polygon = aperture_shapes[aperture["id"]]
            overlap = extent.intersection(polygon)
            if overlap.area <= 0 and overlap.length <= 0:
                continue
            span = _aperture_span(extent, polygon, jamb_shapes[aperture["id"]], contact_budget, area_budget)
            contacts = span["jamb_contacts"]
            authored_span_consistent = all(opening.id not in duplicate_openings
                                           and opening_spans[opening.id]["qualified_aperture_refs"] == [aperture["id"]] for opening in linked)
            veto_refs = []
            veto_evidence = []
            contextual_openings = []
            for opening in scene.openings:
                opening_extent = unary_union([observed[ref][1] for ref in opening.geometry_refs if ref in observed])
                opening_overlap = opening_extent.intersection(polygon)
                local = opening_overlap.area > 0 or opening_overlap.length > 0
                valid_extent = bool(opening.geometry_refs) and all(ref in observed and observed[ref][0].get("span_qualified", False)
                                                                  for ref in opening.geometry_refs)
                declared_host = aperture["host_ref"] in opening.host_refs
                # Consider valid local evidence before filtering host IDs. A
                # conflicting relation refuses locally without inventing a link
                # or relabelling an unknown filling state as confirmed unfilled.
                local_unfilled = valid_extent and local and opening.opening_kind.lower() in {"unfilled", "unfilled_opening"}
                if not declared_host and not (valid_extent and local):
                    continue
                missing_only = (valid_extent and local and not local_unfilled and opening.id not in duplicate_openings
                                and not any(ref in sources for ref in opening.host_refs)
                                and opening_states[opening.id]["local_diagnostic_state"] in {"partial", "diagnostic_only"})
                # Missing contextual linkage does not invalidate independently
                # qualified leaf geometry. Preserve it without authoring a host;
                # the usual unique-candidate gate still decides the carrier.
                if missing_only:
                    contextual_openings.append({"opening_ref": opening.id, "authored_host_refs": list(opening.host_refs),
                                                "local_diagnostic_state": opening_states[opening.id]["local_diagnostic_state"],
                                                "source_reason": opening_states[opening.id]["reason"],
                                                "local_overlap": _geometry(opening_overlap), "host_mapping_inferred": False,
                                                "reason": "missing_contextual_host_relation_not_a_leaf_geometry_veto"})
                    continue
                unresolved_host = not declared_host or len(opening.host_refs) != 1 or any(ref not in sources for ref in opening.host_refs)
                unresolved = (opening.id in duplicate_openings or opening_states[opening.id]["local_diagnostic_state"] != "diagnostic_only"
                              or unresolved_host
                              or any(ref not in observed or not observed[ref][0].get("span_qualified", False) for ref in opening.geometry_refs))
                if local_unfilled or unresolved or local and opening.opening_kind.lower() not in {"door", "window"}:
                    veto_refs.append(opening.id)
                    veto_evidence.append({"opening_ref": opening.id, "authored_host_refs": list(opening.host_refs),
                                          "declared_host_matches": declared_host, "host_mapping_inferred": False,
                                          "local_overlap": _geometry(opening_overlap), "valid_extent": valid_extent,
                                          "reason": "explicit_local_unfilled_extent" if local_unfilled else
                                            "unresolved_local_opening_host_relation" if unresolved_host else "authored_opening_unresolved_or_unsupported"})
            qualified = bool(row["span_qualified"] and not authored_bad and authored_span_consistent
                             and span["qualified"] and not veto_refs
                             and (not authored_hosts or aperture["host_ref"] in authored_hosts))
            alternatives.append({"aperture_ref": aperture["id"], "host_ref": aperture["host_ref"],
                                 "overlap": _geometry(overlap), "jamb_contacts": contacts,
                                 "qualified": qualified, "opening_veto_refs": sorted(set(veto_refs)),
                                 "opening_veto_evidence": veto_evidence,
                                 "unresolved_contextual_opening_evidence": contextual_openings,
                                 "authored_span_consistent": authored_span_consistent,
                                 "literal_contact_qualified": qualified and sum(c["exact_intersection"] for c in contacts) >= 2})
        qualified = [a for a in alternatives if a["qualified"]]
        chosen = qualified[0] if len(qualified) == 1 else None
        association = "authored" if chosen and linked and authored_hosts else "inferred" if chosen else "ambiguous" if len(qualified) > 1 else "unresolved"
        authored_span_bad = bool(linked) and not any(a["authored_span_consistent"] for a in alternatives)
        treatment = {"source_ref": source.id, "host_mapping": association, "authored_opening_refs": list(source.opening_refs),
                     "authored_host_refs": sorted(authored_hosts), "alternatives": alternatives,
                     "selected_aperture_ref": chosen["aperture_ref"] if chosen else None,
                     "refusal": None if chosen else row["refusal"] or ("authored_opening_mapping_unresolved" if authored_bad else
                       "authored_opening_span_inconsistent" if authored_span_bad else "no_unique_qualified_aperture"),
                     "duplicate_opening_refs": sorted(set(source.opening_refs).intersection(duplicate_openings)),
                     "scenario_authority": request["default_closed_authority"], "observed_state": None,
                     "affected_scope_ids": [], "affected_contour_ids": []}
        treatments.append(treatment)
        if chosen:
            ref = chosen["aperture_ref"]
            carriers.append({"id": f"closed:{source.id}", "source_ref": source.id, "host_ref": chosen["host_ref"],
                             "aperture_ref": ref, "association": association, "geometry": _geometry(aperture_shapes[ref]),
                             "scenario": "authorized_default_closed_not_observed", "physical_mass_added": False})
            next(a for a in apertures if a["id"] == ref)["scenario_closed"] = True
    structural = [(row["source_ref"], sources[row["source_ref"]][3]) for row in rows if row["enclosure_support_eligible"]]
    rows_by_ref = {row["source_ref"]: row for row in rows}
    assembly = unary_union([cut for _, cut in structural] + [aperture_shapes[c["aperture_ref"]] for c in carriers])
    scopes, contours = [], []
    structural_mass = unary_union([cut for _, cut in structural])
    wall_mass = unary_union([cut for ref, cut in structural if rows_by_ref[ref]["kind"] == "wall"])
    column_components = _polygons(unary_union([
        cut for ref, cut in structural if rows_by_ref[ref]["kind"] == "column"
    ]))
    wall_components = [(component, [row["source_ref"] for row in rows
                                    if row["kind"] == "wall" and row["enclosure_support_eligible"]
                                    and component.intersection(sources[row["source_ref"]][3]).area > 0])
                       for component in _polygons(assembly)]
    wall_components = [(component, walls) for component, walls in wall_components if walls and component.interiors]
    for component, walls in wall_components:
        for ring in component.interiors:
            polygon = Polygon(ring)
            # A detached nested wall shell owns its interior; remove its filled exterior
            # from the parent before retaining structural islands as holes.
            nested = [Polygon(other.exterior) for other, _ in wall_components
                      if other is not component and polygon.covers(other)]
            # Only columns connected to a supporting shell close that shell; detached columns stay occupancy.
            supporting_mass = unary_union([wall_mass] + [
                part for part in column_components if not polygon.boundary.intersection(part).is_empty
            ])
            for scope in _polygons(polygon.difference(unary_union(nested)).difference(supporting_mass)):
                scope_ref = f"S{len(scopes) + 1}"
                scopes.append({"id": scope_ref, "geometry": _geometry(scope), "supporting_carrier": _geometry(component),
                               "wall_source_refs": walls, "provisional": True, "selected": False, "active": False,
                               "construction": "enclosed_interior_minus_structural_section",
                               "occupancy_source_refs": [ref for ref, cut in structural if polygon.intersection(cut).area > 0],
                               "local_unresolved_aperture_refs": [a["id"] for a in apertures if not a["scenario_closed"]
                                 and a["significant_residual"] and not scope.boundary.intersection(aperture_shapes[a["id"]]).is_empty]})
                contours.append({"id": f"C{len(contours) + 1}", "scope_ref": scope_ref, "geometry": _geometry(scope),
                                 "provisional": True, "selected": False,
                                 "semantic_contribution_refs": [c["source_ref"] for c in carriers
                                  if scope.boundary.intersection(aperture_shapes[c["aperture_ref"]].boundary).length > 0]})
    for aperture in apertures:
        geometry = aperture_shapes[aperture["id"]]
        # Dependencies stay local to measured contact, including unresolved
        # residuals. This does not declare them authored openings or rooms.
        aperture["affected_scope_ids"] = [s["id"] for s in scopes if not shape(s["geometry"]["geojson"]).intersection(geometry).is_empty]
        aperture["affected_contour_ids"] = [c["id"] for c in contours if not shape(c["geometry"]["geojson"]).boundary.intersection(geometry).is_empty]
    for treatment in treatments:
        related = [a for a in apertures if any(alt["aperture_ref"] == a["id"] for alt in treatment["alternatives"])]
        treatment["affected_scope_ids"] = sorted({ref for a in related for ref in a["affected_scope_ids"]})
        treatment["affected_contour_ids"] = [c["id"] for c in contours if treatment["source_ref"] in c["semantic_contribution_refs"]]
    return {"schema": "d6-b2-private-semantic-enclosure/v1", "request": dict(request) | {
                "analysis_plane": plane.to_dict(), "aperture_residual_tolerance_m2": residual_tolerance},
            "coordinate_frame": "scene_analysis_plane_local_metres_unshifted", "sources": rows,
            "apertures": apertures, "treatments": treatments, "carriers": carriers,
            "authored_opening_spans": opening_spans,
            "opening_identity_conflicts": [{"id": ref, "reason": "duplicate_opening_identity",
                                             "source_records": [opening.to_dict() for opening in openings[ref]]} for ref in sorted(duplicate_openings)],
            "enclosure_carrier": _geometry(assembly), "physical_structural_section": _geometry(structural_mass),
            "enclosure_contours": contours, "scope_proposals": scopes,
            "physical_sources_unchanged": True, "candidate_promotion": "refused", "selected": False, "active": False,
            "downstream": {"subtraction": "refused", "free_space": "not_evaluated", "route": "not_evaluated"},
            "limits": ["default_closed_scenario_not_observed", "self_intersections_not_certified",
                       "host_projection_residuals_not_authored_openings", "shared_wall_and_room_allocation_unresolved"]}
