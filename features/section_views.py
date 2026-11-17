"""Pure exact world-XY sections of factual MassPatch geometry, without mesh repair."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from math import isfinite
from numbers import Real

import numpy as np
import trimesh
from shapely.geometry import GeometryCollection, LineString, MultiPoint, mapping, shape
from shapely.ops import polygonize_full, unary_union

from .geometry_substitutes import MassPatch
from .geometry_views import _ray_intersection_distance, _triangle_height_intersections, _unique_sorted

EMPTY = GeometryCollection()
SECTION_ALGORITHM = "indexed-edge-world-xy-section/v1"
QUALIFIED_SECTION_STATUSES = frozenset({
    "qualified_closed_section", "qualified_empty_section",
    "valid_empty_below_plane", "valid_empty_above_plane",
})


def section_query_height(query):
    """Require an explicit world XY height in metres; no implicit scene-plane query."""
    if (not isinstance(query, Mapping) or query.get("frame") != "world_xy"
            or query.get("units") != "m" or isinstance(query.get("world_z_m"), bool)
            or not isinstance(query.get("world_z_m"), Real) or not isfinite(query["world_z_m"])):
        raise ValueError("invalid_exact_world_plane_query")
    return float(query["world_z_m"])


def exact_plane_section(patch: MassPatch, *, world_z_m: float) -> dict:
    """Qualify an exact horizontal section of an already-world-metre MassPatch."""
    height = section_query_height({"frame": "world_xy", "units": "m", "world_z_m": world_z_m})
    return _section_record({
        "id": patch.id, "vertices": patch.vertices, "triangles": patch.triangle_indices,
        "is_closed": patch.is_closed, "is_manifold": patch.is_manifold,
        "units": patch.provenance.get("units"),
        "transform_applied": patch.provenance.get("world_transform_applied"),
    }, height)


def section_record_rejection(record, geometry_refs, query):
    """Check a caller-qualified section record against the selected geometry and query.

    Frozen evidence authenticity is checked by its adapter before this handoff.
    Multiple meshes lack a certified material-combination rule and remain unknown.
    """
    if len(geometry_refs) != 1:
        return "unsafe_multi_mesh_section_combination"
    if record is None:
        return "missing_section_evidence"
    evidence = record.get("section_evidence", {})
    if (evidence.get("source_object_id") != record.get("id")
            or evidence.get("query") != query
            or tuple(evidence.get("geometry_refs", ())) != tuple(geometry_refs)
            or evidence.get("algorithm") != SECTION_ALGORITHM):
        return "section_evidence_binding_mismatch"
    section = record.get("section", {})
    if section.get("status") not in QUALIFIED_SECTION_STATUSES or section.get("occupied_geometry") is None:
        return "unqualified_section_evidence"
    try:
        geometry = shape(section["occupied_geometry"])
        if (not geometry.is_valid or (not geometry.is_empty and geometry.geom_type not in {"Polygon", "MultiPolygon"})
                or geometry.area != section.get("occupied_area_m2")
                or (section["status"] != "qualified_closed_section" and not geometry.is_empty)
                or (section["status"] == "qualified_closed_section" and geometry.is_empty)):
            return "invalid_section_evidence"
    except (TypeError, ValueError, KeyError):
        return "invalid_section_evidence"
    return None


def _polygon_parts(geometry):
    """Retain positive polygon leaves while auditing discarded contacts separately."""
    if geometry.geom_type == "Polygon":
        return [geometry] if geometry.area > 0 else []
    return [part for child in getattr(geometry, "geoms", ()) for part in _polygon_parts(child)]


def geometry_audit(geometry):
    """Record validity and leaf types before any derived area-view conversion."""
    def leaves(item):
        """Retain linear and point leaves so discarded contacts stay measurable."""
        return [leaf for child in item.geoms for leaf in leaves(child)] if hasattr(item, "geoms") else [item]
    parts = leaves(geometry)
    removed = [part for part in parts if part.geom_type != "Polygon" or part.area <= 0]
    return {"geometry_type": geometry.geom_type, "is_valid": bool(geometry.is_valid),
            "area_m2": geometry.area, "leaf_type_counts": dict(Counter(p.geom_type for p in parts)),
            "non_positive_polygon_leaf_types": dict(Counter(p.geom_type for p in removed)),
            "removable_area_m2": sum(p.area for p in removed),
            "removable_length_m": sum(p.length for p in removed)}


def polygonal_union(geometries, audit=None):
    """Union valid inputs and explicitly account for zero-area contact removal."""
    inputs = [geometry_audit(item) for item in geometries]
    # Invalid positive-area inputs must fail visibly rather than disappear from the field.
    if any(not item["is_valid"] for item in inputs):
        raise ValueError("Invalid union input; no repair or positive-area filtering permitted")
    # Linear contacts remain source audit evidence but cannot carry an area mask.
    union = unary_union(geometries) if geometries else EMPTY
    assert union.is_valid, "Invalid derived union; no automatic repair"
    result = unary_union(_polygon_parts(union))
    assert result.is_valid
    if audit is not None:
        audit.update(inputs=inputs, union_before_area_view=geometry_audit(union),
                     output=geometry_audit(result), make_valid_applied=False,
                     processing="unary_union_then_positive_area_polygon_view; no_precision_or_source_change",
                     removed_area_m2=union.area - result.area)
    return result


def parity_evidence(patch, xy, world_z_m, triangle_indices=None):
    """Expose all three existing parity probes rather than hiding disagreement."""
    origin = (float(xy[0]), float(xy[1]), world_z_m)
    votes, counts = [], []
    for direction in ((1.0, .371234, .173891), (.193, 1.0, .417), (.311, .271, 1.0)):
        distances = []
        for indices in patch.triangle_indices if triangle_indices is None else triangle_indices:
            distance = _ray_intersection_distance(origin, direction, *(patch.vertices[i] for i in indices))
            if distance is not None:
                distances.append(distance)
        hits = _unique_sorted(distances)
        votes.append(bool(len(hits) % 2))
        counts.append(len(hits))
    # The production helper takes a majority; this bounded qualification retains disagreement.
    return {"xy_m": list(xy), "ray_hit_counts": counts, "inside_votes": votes,
            "unanimous": len(set(votes)) == 1, "inside": votes[0] if len(set(votes)) == 1 else None}


def disjoint_shell_parity_evidence(patch, xy, shells, world_z_m):
    """Combine parity only after disjoint section interiors are established, retaining shell identity."""
    probes = [{"shell_id": shell["shell_id"], **parity_evidence(
        patch, xy, world_z_m, [patch.triangle_indices[i] for i in shell["original_face_indices"]])}
        for shell in shells if shell["crosses_plane"]]
    # Coincident distances on distinct source shells are distinct crossings, not duplicate triangle hits.
    counts = [sum(probe["ray_hit_counts"][index] for probe in probes) for index in range(3)]
    unanimous = all(probe["unanimous"] for probe in probes)
    positive_count = sum(probe["inside"] is True for probe in probes)
    unanimous = unanimous and positive_count <= 1
    return {"xy_m": list(xy), "ray_hit_counts": counts, "inside_votes": [bool(count % 2) for count in counts],
            "component_probes": probes, "unanimous": unanimous, "inside": bool(positive_count) if unanimous else None}


def indexed_edge_sections(vertices, faces, crossing_ids, world_z_m):
    """Intersect each shared source edge once, preserving indexed topology without welding."""
    edges, segments, face_edges, occurrences = {}, [], [], Counter()
    raw_segments, raw_lost, mismatches = [], [], []
    for face_id in crossing_ids:
        indices = faces[face_id]
        raw = _triangle_height_intersections(tuple(tuple(vertices[i]) for i in indices), world_z_m)
        if len(raw) == 2 and raw[0] != raw[1]:
            raw_segments.append(raw)
        else:
            raw_lost.append(int(face_id))
        keys = []
        for first, second in zip(indices, np.roll(indices, -1)):
            start, end = vertices[first], vertices[second]
            if min(start[2], end[2]) < world_z_m < max(start[2], end[2]):
                key = tuple(sorted((int(first), int(second))))
                occurrences[key] += 1
                keys.append(key)
                # Identical indexed edges represent identical source geometry; reuse is not proximity repair.
                if key not in edges:
                    low, high = vertices[key[0]], vertices[key[1]]
                    ratio = (world_z_m - low[2]) / (high[2] - low[2])
                    edges[key] = tuple(low[:2] + ratio * (high[:2] - low[:2]))
                directed = start[:2] + (world_z_m - start[2]) / (end[2] - start[2]) * (end[:2] - start[:2])
                delta = float(np.linalg.norm(directed - edges[key]))
                if delta:
                    mismatches.append({"source_edge_indices": list(key), "face_index": int(face_id),
                                       "directed_xy_m": directed.tolist(), "shared_xy_m": list(edges[key]), "difference_m": delta})
        if len(keys) != 2:
            raise ValueError(f"Strict crossing triangle {face_id} does not have two crossing source edges")
        segments.append(tuple(edges[key] for key in keys))
        face_edges.append([list(key) for key in keys])
    audit = {"algorithm": "linear plane intersection once per sorted original vertex-index edge; original triangles untouched",
             "numeric_endpoint_merge_tolerance_m": 0.0, "source_vertices_welded": False,
             "source_edge_count": len(edges), "source_edge_face_multiplicities": dict(Counter(occurrences.values())),
             "segment_source_edges": face_edges, "raw_helper_lost_triangle_indices": raw_lost,
             "directed_roundoff_mismatch_count": len(mismatches),
             "max_directed_roundoff_mismatch_m": max((item["difference_m"] for item in mismatches), default=0.0),
             "roundoff_examples": sorted(mismatches, key=lambda item: item["difference_m"], reverse=True)[:5],
             "raw_helper_linework_geometry": mapping(GeometryCollection([LineString(points) for points in raw_segments]))}
    raw_polygons, raw_cuts, raw_dangles, raw_invalid = polygonize_full(unary_union([LineString(points) for points in raw_segments]))
    audit["raw_helper_polygonization"] = {"faces": mapping(raw_polygons), "cuts": mapping(raw_cuts),
                                           "dangles": mapping(raw_dangles), "invalid_rings": mapping(raw_invalid),
                                           "residual_lengths_m": {"cuts": raw_cuts.length, "dangles": raw_dangles.length, "invalid_rings": raw_invalid.length}}
    return segments, audit


def connected_shell_audit(mesh, record, world_z_m):
    """Retain source shell orientation and reject ambiguous compound interiors at this plane."""
    components = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1)
    shells, geometries = [], []
    for shell_id, raw_face_ids in enumerate(components):
        # Normalize across Trimesh return types before indexed slicing and audit serialization.
        face_ids = np.asarray(raw_face_ids, dtype=int)
        faces = mesh.faces[face_ids]
        vertices = mesh.vertices[np.unique(faces)]
        shell = trimesh.Trimesh(vertices=mesh.vertices, faces=faces, process=False, validate=False)
        minimum, maximum = float(vertices[:, 2].min()), float(vertices[:, 2].max())
        crosses = minimum < world_z_m < maximum
        item = {"shell_id": shell_id, "original_face_indices": face_ids.tolist(),
                "signed_volume_m3": float(shell.volume), "referenced_z_range_m": [minimum, maximum],
                "crosses_plane": crosses, "is_watertight": bool(shell.is_watertight),
                "is_winding_consistent": bool(shell.is_winding_consistent)}
        if len(components) > 1 and crosses:
            # Isolate only original indexed faces; never flip orientation, weld vertices or infer a Boolean role.
            section = _section_record({**record, "triangles": faces.tolist()}, world_z_m)
            item.update(section_status=section["status"], section_geometry=section["occupied_geometry"],
                        face_parity_probes=section.get("face_parity_probes"))
            geometries.append((shell_id, None if section["occupied_geometry"] is None else shape(section["occupied_geometry"])))
        shells.append(item)
    pairs = []
    for index, (first_id, first) in enumerate(geometries):
        for second_id, second in geometries[index + 1:]:
            pairs.append({"shell_ids": [first_id, second_id],
                          "intersection_area_m2": None if first is None or second is None else first.intersection(second).area,
                          "first_contains_second": None if first is None or second is None else first.contains(second),
                          "second_contains_first": None if first is None or second is None else second.contains(first)})
    ambiguous = any(geometry is None for _, geometry in geometries) or any(pair["intersection_area_m2"] > 0 for pair in pairs if pair["intersection_area_m2"] is not None)
    return {"connectivity": "original indexed-edge face adjacency; no welding",
            "shell_count": len(shells), "crossing_shell_count": sum(s["crosses_plane"] for s in shells),
            "shells": shells, "plane_shell_pairs": pairs, "ambiguous_compound_interior": ambiguous,
            "material_policy": "Intersecting/nested shell interiors remain unknown regardless of orientation; no XOR, union or cavity inference",
            "limit": "Plane-local separation only; 3D self-intersection and material semantics not certified"}


def _section_record(record, world_z_m):
    """Extract strict section linework and qualify only fully supported closed sections."""
    result = {"status": "invalid_mesh", "error": None, "occupied_geometry": None,
              "occupied_area_m2": None, "linework_geometry": mapping(EMPTY),
              "unknown_support_geometry": None, "unknown_support_method": "actual_XY_vertex_hull_only_as_uncertainty_not_occupancy"}
    try:
        assert record["units"] == "m" and record["transform_applied"] is True
        vertices = np.asarray(record["vertices"], dtype=float)
        faces = np.asarray(record["triangles"])
        if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices) or not np.isfinite(vertices).all():
            raise ValueError("Missing, malformed or nonfinite vertices")
        if faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or faces.dtype.kind not in "iu":
            raise ValueError("Missing or malformed triangle indices")
        if faces.min() < 0 or faces.max() >= len(vertices):
            raise ValueError("Triangle index outside vertex array")
        triangles = vertices[faces]
        cross_norm = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
        degenerate_count = int(np.count_nonzero(cross_norm == 0))
        heights = triangles[:, :, 2]
        minimum, maximum = float(heights.min()), float(heights.max())
        crossing_ids = np.flatnonzero((heights.min(axis=1) < world_z_m) & (heights.max(axis=1) > world_z_m))
        near_plane = np.abs(heights - world_z_m) <= 1e-9
        result.update(vertex_count=len(vertices), triangle_count=len(faces),
                      referenced_triangle_z_range_m=[minimum, maximum],
                      crossing_triangle_count=len(crossing_ids),
                      coplanar_triangle_count=int(np.count_nonzero(near_plane.all(axis=1))),
                      plane_vertex_contact_triangle_count=int(np.count_nonzero(near_plane.any(axis=1))),
                      degenerate_triangle_count=degenerate_count,
                      source_geometry_status="invalid_degenerate_mesh" if degenerate_count else "finite_nondegenerate_indexed_triangles",
                      captured_closed_flag=record.get("is_closed"), captured_manifold_flag=record.get("is_manifold"))
        support = MultiPoint(vertices[:, :2]).convex_hull
        result["vertex_audit_xy"] = vertices[::max(1, len(vertices) // 250), :2].tolist()
        # Entire referenced triangle geometry on one side proves absence at this plane, even for open meshes.
        if maximum < world_z_m or minimum > world_z_m:
            result.update(status="valid_empty_below_plane" if maximum < world_z_m else "valid_empty_above_plane",
                          occupied_geometry=mapping(EMPTY), occupied_area_m2=0.0, unknown_support_geometry=mapping(EMPTY))
            return result
        if degenerate_count:
            result.update(status="invalid_degenerate_mesh", error="Zero-area source triangle; no removal or repair", unknown_support_geometry=mapping(support))
            return result
        result["unknown_support_geometry"] = mapping(support)
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False, validate=False)
        result["mesh_checks"] = {"process": False, "validate": False, "is_watertight": bool(mesh.is_watertight),
                                 "is_winding_consistent": bool(mesh.is_winding_consistent),
                                 "self_intersection_3D": "not_certified", "repair_weld_snap": "none"}
        segments, edge_audit = indexed_edge_sections(vertices, faces, crossing_ids, world_z_m)
        result["indexed_edge_intersection_audit"] = edge_audit
        result["segment_face_indices"] = crossing_ids.tolist()
        lines = [LineString(points) for points in segments]
        linework = GeometryCollection(lines)
        result["linework_geometry"] = mapping(linework)
        # Full polygonization exposes incomplete contours instead of silently dropping their linework.
        noded = unary_union(lines)
        polygons, cuts, dangles, invalid = polygonize_full(noded)
        degrees = Counter(point for segment in segments for point in segment)
        result["section_audit"] = {
            "input_segment_count": len(segments), "raw_endpoint_degree_counts": dict(Counter(degrees.values())),
            "raw_linework": geometry_audit(linework), "noded_linework": geometry_audit(noded),
            "polygonized_faces": mapping(polygons), "face_count": len(polygons.geoms),
            "cuts": mapping(cuts), "dangles": mapping(dangles), "invalid_rings": mapping(invalid),
            "residual_lengths_m": {"cuts": cuts.length, "dangles": dangles.length, "invalid_rings": invalid.length},
            "snapping_or_closure": "none; shared original edge identity only"}
        if result["plane_vertex_contact_triangle_count"]:
            result.update(status="unresolved_boundary_or_coplanar", error="Vertex/edge/coplanar contact within existing 1e-9 m guard; no stronger boundary convention")
            return result
        if not (mesh.is_watertight and mesh.is_winding_consistent and record.get("is_closed") is True and record.get("is_manifold") is True):
            result.update(status="unresolved_open_or_nonmanifold", error="Closed solid prerequisite fails; closed planar contours alone do not qualify open mass")
            return result
        if any(first == second for first, second in segments) or any(degree != 2 for degree in degrees.values()) or not all(g.is_empty for g in (cuts, dangles, invalid)):
            result.update(status="unresolved_section_linework", error="Indexed-edge section has collapsed segments, non-degree-2 endpoints or polygonization residuals; no closure/snapping")
            return result
        if any(not face.is_valid or face.area <= 0 for face in polygons.geoms):
            result.update(status="invalid_section_geometry", error="Invalid or nonpositive polygonized face; not discarded")
            return result
        shell_audit = connected_shell_audit(mesh, record, world_z_m)
        result["connected_shell_audit"] = shell_audit
        if shell_audit["ambiguous_compound_interior"]:
            result.update(status="unresolved_compound_shell_interior", error="Nested/overlapping or unresolved component sections; source material relationship unspecified")
            return result
        patch = MassPatch(id=record["id"], source_geometry_id=record["id"],
                          vertices=tuple(map(tuple, vertices)), triangle_indices=tuple(map(tuple, faces)),
                          is_closed=True, is_manifold=True, provenance={"frozen_actual_Body": True})
        result["whole_object_face_parity_probes"] = [parity_evidence(patch, face.representative_point().coords[0], world_z_m) for face in polygons.geoms]
        probes = [disjoint_shell_parity_evidence(patch, face.representative_point().coords[0], shell_audit["shells"], world_z_m) for face in polygons.geoms]
        result["face_parity_probes"] = probes
        if any(not probe["unanimous"] for probe in probes):
            result.update(status="unresolved_parity", error="Original connected-shell three-ray inside/outside probes disagree or contradict disjoint interiors")
            return result
        occupied_faces = [face for face, probe in zip(polygons.geoms, probes) if probe["inside"]]
        union_audit = {}
        occupied = polygonal_union(occupied_faces, union_audit)
        result.update(status="qualified_closed_section" if not occupied.is_empty else "qualified_empty_section",
                      occupied_geometry=mapping(occupied), occupied_area_m2=occupied.area,
                      occupied_union_audit=union_audit, unknown_support_geometry=mapping(EMPTY))
        return result
    except Exception as error:
        # A real error retains null occupancy and uncertainty; never turn a failed operation into valid-empty.
        result["error"] = f"{type(error).__name__}: {error}"
        result["status"] = "invalid_mesh" if "section_audit" not in result else "invalid_section_operation"
        return result


