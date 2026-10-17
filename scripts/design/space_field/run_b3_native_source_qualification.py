"""Collect native indexed facts for the 13 frozen B3 exceptions without tessellation."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
CAPTURE = Path("outputs/design/b3_real_source_field/run_001")
FIELD = Path("outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3")
IFC = Path("outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc")
IFC_HASH = "018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240"
TARGETS = (
    (6231, "3y7JkDRLzPT9x47Baq5air", 15562, 15561, 15568),
    (43654, "2$pZmZTQPRNQWDdiOmzSo_", 49623, 49622, 49629),
    (49645, "1cameBqC9H4gRgew6pelrZ", 55614, 55613, 55620),
    (55636, "3Ubr6f0zfLAAxYyBdvFyju", 61605, 61604, 61611),
    (61627, "1yil0vYiLSlP7C2s8YPjLM", 67596, 67595, 67602),
    (67618, "05qK_LP$PLHfyzuz5MHWHc", 73587, 73586, 73593),
    (1992252, "1wZJY19NTU$Bn2CE1vayIo", 1996033, 1996032, 1996039),
    (2032485, "3tVuwteKLUAxI0S_ptGNQT", 2051205, 2051204, 2051211),
    (2053009, "1frmBqaGbPA9BIJetQWrfy", 2082616, 2082615, 2082622),
    (2082638, "31IHP3QHrVcfPwKvRNo$wX", 2084469, 2084468, 2084475),
    (3236022, "1ABvcEoPPOdulOu6GfO5ru", 3237853, 3237852, 3237859),
    (3237875, "0ZKIA_vCHHJB1xk3DDhXGh", 3267482, 3267481, 3267488),
    (3269286, "2s6tcXT5rR49krD_XhXIfN", 3288006, 3288005, 3288012),
)


def require(condition, message):
    """Fail explicitly rather than deriving facts from a different source."""
    if not condition:
        raise ValueError(message)


def fingerprint(path, expected=None):
    """Hash input bytes before opening them as native or serialized evidence."""
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}
    if expected is not None:
        require((result["bytes"], result["sha256"]) == (expected["bytes"], expected["sha256"]),
                f"Frozen input fingerprint mismatch: {path}")
    return result


def read_verified(path, reference):
    """Read a frozen JSON payload only after matching its recorded fingerprint."""
    fingerprint(path, reference)
    return json.loads(path.read_text(encoding="utf-8"))


def array_digest(value):
    """Identify native coordinate/index arrays without copying them into the report."""
    raw = json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def entity_ref(entity):
    """Keep an exact native STEP lookup instead of serializing an IFC entity graph."""
    return None if entity is None else {"step_id": entity.id(), "ifc_class": entity.is_a()}


def native_faces(item):
    """Read original indexed rings, applying only the authored one-based PnIndex."""
    require(item.is_a() in ("IfcPolygonalFaceSet", "IfcTriangulatedFaceSet"),
            f"Unsupported native item: {item.is_a()}")
    points = np.asarray(item.Coordinates.CoordList, dtype=float)
    require(points.ndim == 2 and points.shape[1] == 3 and len(points) > 0
            and np.isfinite(points).all(), "Invalid native coordinate list")
    pn = item.PnIndex
    if pn is not None:
        require(all(type(i) is int and 1 <= i <= len(points) for i in pn), "Invalid native PnIndex")
    raw_faces = ([(None, [tuple(face)]) for face in item.CoordIndex]
                 if item.is_a("IfcTriangulatedFaceSet") else
                 [(face.id(), [tuple(face.CoordIndex), *(getattr(face, "InnerCoordIndices", ()) or ())])
                  for face in item.Faces])
    require(bool(raw_faces), "Missing native faces")
    faces = []
    for face_id, rings in raw_faces:
        normalized = []
        for ring in rings:
            require(len(ring) >= 3, "Native face ring has fewer than three indices")
            limit = len(pn) if pn is not None else len(points)
            require(all(type(i) is int and 1 <= i <= limit for i in ring), "Invalid native face index")
            normalized.append(tuple((pn[i - 1] if pn is not None else i) - 1 for i in ring))
        faces.append((face_id, normalized))
    return points, faces


def topology(points, faces):
    """Count original index incidence and connected faces without merging coordinates."""
    edges = defaultdict(list)
    vertex_faces = defaultdict(set)
    for face_index, (_, rings) in enumerate(faces):
        for ring in rings:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                edges[tuple(sorted((a, b)))].append((face_index, a, b))
                vertex_faces[a].add(face_index)
    parent = list(range(len(faces)))

    def find(index):
        """Find the representative of an original face component."""
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for incidence in edges.values():
        for face_index, _, _ in incidence[1:]:
            parent[find(face_index)] = find(incidence[0][0])
    grouped = defaultdict(list)
    for face_index in range(len(faces)):
        grouped[find(face_index)].append(face_index)
    components = []
    for indices in grouped.values():
        vertex_ids = sorted({v for i in indices for ring in faces[i][1] for v in ring})
        used = points[vertex_ids]
        member = set(indices)
        incidence_counts = Counter(len(incidence) for incidence in edges.values() if incidence[0][0] in member)
        components.append({"face_indices_0based": indices, "vertex_count": len(vertex_ids),
                           "edge_face_counts": dict(sorted(incidence_counts.items())),
                           "bounds_world_m": [used.min(axis=0).tolist(), used.max(axis=0).tolist()],
                           "entirely_below_eye_plane": bool(used[:, 2].max() < 1.6),
                           "entirely_above_eye_plane": bool(used[:, 2].min() > 1.6)})
    counts = Counter(len(incidence) for incidence in edges.values())
    bad = [(edge, incidence) for edge, incidence in edges.items() if len(incidence) != 2]
    winding = [(edge, incidence) for edge, incidence in edges.items()
               if len(incidence) == 2 and incidence[0][1:] == incidence[1][1:]]
    # Vertex links distinguish shells meeting at a point from a manifold surface.
    nonmanifold_vertices = 0
    for vertex, adjacent in vertex_faces.items():
        links = defaultdict(set)
        for face_index in adjacent:
            for ring in faces[face_index][1]:
                for i, v in enumerate(ring):
                    if v == vertex:
                        a, b = ring[i - 1], ring[(i + 1) % len(ring)]
                        links[a].add(b)
                        links[b].add(a)
        todo = set(links)
        link_components = 0
        while todo:
            link_components += 1
            stack = [todo.pop()]
            while stack:
                for neighbor in links[stack.pop()]:
                    if neighbor in todo:
                        todo.remove(neighbor)
                        stack.append(neighbor)
        if link_components != 1 or any(len(neighbors) != 2 for neighbors in links.values()):
            nonmanifold_vertices += 1
    return {"edge_face_counts": dict(sorted(counts.items())),
            "boundary_edges": counts[1], "more_than_two_face_edges": sum(n for k, n in counts.items() if k > 2),
            "non_two_face_edges": len(bad), "non_closed_cycle_vertex_links": nonmanifold_vertices,
            "inconsistent_winding_edges": len(winding),
            "collapsed_index_edges": sum(a == b for a, b in edges),
            "edge_witnesses": [{"indices_0based": list(edge),
                                "face_indices_0based": [x[0] for x in incidence],
                                "world_xyz_m": points[list(edge)].tolist()}
                               for edge, incidence in bad[:8]],
            "face_component_count": len(components), "components": components,
            "limit": "Original indices only; vertex links require a single closed cycle (boundary links fail); no solid/material or self-intersection certificate"}


def walk_items(representation, matrix=None, lineage=(), seen=()):
    """Follow authored mapped items without tessellating or inventing geometry."""
    matrix = np.eye(4) if matrix is None else matrix
    require(representation.id() not in seen, "Cyclic mapped representation")
    for item in representation.Items:
        if item.is_a("IfcMappedItem"):
            mapped = ifcopenshell.util.placement.get_mappeditem_transformation(item)
            yield from walk_items(item.MappingSource.MappedRepresentation, matrix @ mapped,
                                  (*lineage, {"item": entity_ref(item),
                                              "mapping_source": entity_ref(item.MappingSource),
                                              "mapping_origin": entity_ref(item.MappingSource.MappingOrigin),
                                              "mapping_target": entity_ref(item.MappingTarget),
                                              "matrix_source_units": mapped.tolist()}),
                                  (*seen, representation.id()))
        else:
            yield item, matrix, list(lineage)


def triangle_signatures(points, triangles):
    """Compare transport triangle positions at float32 precision, without welding."""
    coords = np.asarray(points, dtype=np.float32)
    return Counter(tuple(sorted(tuple(float(v) for v in coords[i]) for i in triangle))
                   for triangle in triangles)


def transport_comparison(native_items, capture):
    """Compare triangle multisets without certifying float64 or material equivalence."""
    if not all(item["all_original_faces_triangular"] for item in native_items):
        return {"status": "not_available", "reason": "Native nontriangular/holed faces; no triangulation authorized"}
    native = Counter()
    for item in native_items:
        native.update(triangle_signatures(item["_points"], item["_triangles"]))
    points = np.asarray(capture["vertices"], dtype=float)
    triangles = np.asarray(capture["triangles"])
    require(points.ndim == 2 and points.shape[1] == 3 and np.isfinite(points).all(), "Invalid capture coordinates")
    require(triangles.ndim == 2 and triangles.shape[1] == 3 and triangles.dtype.kind in "iu"
            and triangles.min() >= 0 and triangles.max() < len(points), "Invalid capture indices")
    captured = triangle_signatures(points, triangles)
    return {"status": "compared", "comparison": "unordered triangle position multiset after world-metre float32 cast",
            "same_triangle_multiset_at_float32": native == captured,
            "native_unmatched_triangle_count": sum((native - captured).values()),
            "capture_unmatched_triangle_count": sum((captured - native).values()),
            "native_coordinate_count": sum(len(item["_points"]) for item in native_items),
            "capture_coordinate_count": len(points), "capture_triangle_count": len(triangles),
            "native_triangle_count": sum(native.values()),
            "capture_world_transform": capture["world_transform"],
            "capture_tessellation_settings": capture["tessellation_settings"],
            "limit": "Float32 positional comparison ignores winding/index identity; not exact geometry or solid equivalence"}


def placement_facts(placement):
    """Retain each authored local placement reference and its own transform."""
    result = []
    seen = set()
    while placement is not None:
        require(placement.id() not in seen, "Cyclic product placement")
        seen.add(placement.id())
        require(placement.is_a("IfcLocalPlacement"), "Unsupported product placement")
        relative = placement.RelativePlacement
        result.append({"placement": entity_ref(placement), "relative_placement": entity_ref(relative),
                       "location_source_units": list(relative.Location.Coordinates),
                       "axis": list(relative.Axis.DirectionRatios) if getattr(relative, "Axis", None) else None,
                       "ref_direction": list(relative.RefDirection.DirectionRatios) if relative.RefDirection else None})
        placement = placement.PlacementRelTo
    return result


def collect_source(source, target, accepted, inventory, capture, scale):
    """Bind one exact source identity and collect native item facts and blockers."""
    step, global_id, rep_step, item_step, placement_step = target
    entity = source.by_id(step)
    require(entity.GlobalId == global_id == accepted["global_id"] == inventory["global_id"], "GlobalId mismatch")
    require(entity.is_a() == accepted["ifc_class"], "IFC class mismatch")
    reps = list(entity.Representation.Representations)
    body = [rep for rep in reps if rep.id() == rep_step and rep.RepresentationIdentifier == "Body"]
    require(len(body) == 1 and inventory["loaded_representation"]["step_id"] == rep_step
            and capture["representation_id"] == str(rep_step), "Body representation mismatch")
    require([item.id() for item in body[0].Items] == [item_step], "Body item mismatch")
    require(entity.ObjectPlacement.id() == placement_step, "Product placement mismatch")
    require(capture["units"] == "m" and capture["transform_applied"] is True, "Capture frame mismatch")
    placements = placement_facts(entity.ObjectPlacement)
    product_matrix = ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement)
    items = []
    for item, mapped_matrix, lineage in walk_items(body[0]):
        record = {"item": entity_ref(item), "mapped_lineage": lineage, "status": "unsupported_native_item"}
        try:
            local, faces = native_faces(item)
            matrix = product_matrix @ mapped_matrix
            world = (np.column_stack((local, np.ones(len(local)))) @ matrix.T)[:, :3] * scale
            require(np.isfinite(world).all(), "Nonfinite transformed native coordinates")
            triangular = all(len(rings) == 1 and len(rings[0]) == 3 for _, rings in faces)
            indices = [list(rings[0]) for _, rings in faces] if triangular else None
            record.update(status="native_index_facts", declared_closed=item.Closed,
                          coordinate_list=entity_ref(item.Coordinates), coordinate_count=len(local),
                          face_count=len(faces), all_original_faces_triangular=triangular,
                          face_step_ids=[face_id for face_id, _ in faces],
                          original_coordinate_array_sha256=array_digest(local.tolist()),
                          resolved_ring_index_sha256=array_digest([rings for _, rings in faces]),
                          pn_index=list(item.PnIndex) if item.PnIndex is not None else None,
                          inner_ring_count=sum(len(rings) - 1 for _, rings in faces),
                          world_matrix_source_units=matrix.tolist(), topology=topology(world, faces),
                          _points=world, _triangles=indices)
        except (ValueError, TypeError, AttributeError, IndexError) as error:
            record.update(status="native_item_fact_failure", error=f"{type(error).__name__}: {error}")
        items.append(record)
    comparison = (transport_comparison(items, capture)
                  if items and all(item["status"] == "native_index_facts" for item in items)
                  else {"status": "not_available", "reason": "Unsupported/failed native item"})
    for item in items:
        item.pop("_points", None)
        item.pop("_triangles", None)
    owners = [("occurrence", entity)] + [("type", relation.RelatingType) for relation in entity.IsTypedBy]
    materials = [{"scope": scope, "relation": entity_ref(relation),
                  "material": entity_ref(relation.RelatingMaterial),
                  "name": getattr(relation.RelatingMaterial, "Name", None)}
                 for scope, owner in owners for relation in owner.HasAssociations
                 if relation.is_a("IfcRelAssociatesMaterial")]
    psets = ifcopenshell.util.element.get_psets(entity)
    return {"id": accepted["id"], "step_id": step, "global_id": global_id,
            "name": entity.Name, "ifc_class": entity.is_a(),
            "declared_representations": [{"step_id": rep.id(), "identifier": rep.RepresentationIdentifier,
                                          "type": rep.RepresentationType} for rep in reps],
            "body_representation_step": rep_step, "placement_chain": placements,
            "product_matrix_source_units": product_matrix.tolist(), "source_to_m": scale,
            "native_items": items, "material_associations": materials,
            "authored_property_sets": psets,
            "accepted_status": accepted["status"], "accepted_error": accepted["error"],
            "accepted_quality": accepted["quality"], "accepted_scope": accepted["scope"],
            "accepted_section_summary": {"crossing_triangle_count": accepted["crossing_triangle_count"],
                                         "face_count": accepted["section_audit"]["face_count"],
                                         "residual_lengths_m": accepted["section_audit"]["residual_lengths_m"]},
            "capture_reference": accepted["geometry"], "transport_comparison": comparison,
            "solid_qualification": "not_established_by_native_facts",
            "limit": "No sections, solid queries, repair, volume/material inference or field regeneration"}


def write_json(path, payload):
    """Write strict new evidence while preserving every frozen input."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def collect(out):
    """Verify the IFC first, then inspect only the exact frozen exception cohort."""
    native_ref = fingerprint(ROOT / IFC, {"bytes": 408617800, "sha256": IFC_HASH})
    # Fingerprint gates precede both native parsing and capture/source comparisons.
    source_ref = {"bytes": 11397078, "sha256": "57181d1dcf9b57b9386c2be036cfbdedddb641ab5242c9fdf1d01e5d7c7a56e7"}
    sections = read_verified(ROOT / FIELD / "source_sections.json", source_ref)
    inventory = read_verified(ROOT / CAPTURE / "scope_inventory.json",
                              {"bytes": 540239, "sha256": "3ad1fadec5d1cc84bf88f7180fa9edf5a597ccce072ba8d5d779f234a628eb48"})
    selected = {row["step_id"]: row for row in sections["records"]
                if row["status"] == "unresolved_open_or_nonmanifold"}
    require(set(selected) == {target[0] for target in TARGETS}, "Frozen exception cohort mismatch")
    inventory_by_step = {row["step_id"]: row for row in inventory["records"]}
    source = ifcopenshell.open(str(ROOT / IFC))
    scale = ifcopenshell.util.unit.calculate_unit_scale(source)
    require(source.schema == "IFC4" and scale == 0.001, "Native schema/unit mismatch")
    result = {"schema": "b3-native-source-facts/v1", "status": "native_facts_only_not_occupancy",
              "source_ifc": native_ref, "source_schema": source.schema,
              "source_to_m": scale, "world_units": "m", "primary_plane_world_z_m": 1.6,
              "qualified_scope_goal": "Frozen imported inventory / historical S3; not real-world completeness",
              "source_sections_reference": fingerprint(ROOT / FIELD / "source_sections.json"),
              "scope_inventory_reference": fingerprint(ROOT / CAPTURE / "scope_inventory.json"),
              "records": [], "failures": []}
    for target in TARGETS:
        step = target[0]
        try:
            accepted = selected[step]
            require(accepted["geometry"] == inventory_by_step[step]["geometry"], "Capture reference mismatch")
            capture = read_verified(ROOT / CAPTURE / accepted["geometry"]["path"], accepted["geometry"])
            result["records"].append(collect_source(source, target, accepted, inventory_by_step[step], capture, scale))
        except Exception as error:
            # One unavailable source remains explicit and cannot suppress other facts.
            result["failures"].append({"step_id": step, "error": f"{type(error).__name__}: {error}"})
    write_json(out / "native_source_facts.json", result)
    return result


def main():
    """Create one unique evidence run and retain failures without repairing inputs."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "outputs/design/b3_native_source_qualification" / f"run_{stamp}_{uuid.uuid4().hex[:6]}"
    out.mkdir(parents=True, exist_ok=False)
    execution = {"status": "running", "output": str(out), "tessellation": "not_invoked",
                 "repair_or_field_generation": "none"}
    try:
        result = collect(out)
        item_failures = [{"step_id": row["step_id"], "item": item["item"], "error": item.get("error")}
                         for row in result["records"] for item in row["native_items"]
                         if item["status"] != "native_index_facts"]
        execution.update(status="completed_with_failures" if result["failures"] or item_failures else "completed",
                         source_records=len(result["records"]), failures=result["failures"], item_failures=item_failures)
        write_json(out / "artifact_manifest.json", {
            "schema": "b3-native-source-artifacts/v1", "artifacts": [fingerprint(out / "native_source_facts.json")],
            "code": fingerprint(Path(__file__)), "test": fingerprint(ROOT / "test/test_b3_native_source_qualification.py"),
        })
    except Exception as error:
        execution.update(status="failed", error=f"{type(error).__name__}: {error}")
    write_json(out / "execution.json", execution)
    print(json.dumps(execution, ensure_ascii=True))
    return 0 if execution["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
