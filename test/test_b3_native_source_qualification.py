"""Focused native-index, transport and frozen-binding checks for B1 only."""

import importlib.util
from pathlib import Path

import ifcopenshell
import numpy as np
import pytest


PATH = Path(__file__).parents[1] / "scripts/design/space_field/run_b3_native_source_qualification.py"
SPEC = importlib.util.spec_from_file_location("b3_native_facts", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
POINTS = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]
TETRA = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)]


def indexed_item(source, kind="IfcPolygonalFaceSet", indices=((1, 2, 3),), pn=None):
    """Author native arrays directly so tests never pass through tessellation."""
    coordinates = source.create_entity("IfcCartesianPointList3D", CoordList=POINTS)
    if kind == "IfcTriangulatedFaceSet":
        return source.create_entity(kind, Coordinates=coordinates, CoordIndex=indices, PnIndex=pn)
    faces = [source.create_entity("IfcIndexedPolygonalFace", CoordIndex=ring) for ring in indices]
    return source.create_entity(kind, Coordinates=coordinates, Faces=faces, PnIndex=pn)


@pytest.mark.parametrize("kind", ["IfcPolygonalFaceSet", "IfcTriangulatedFaceSet"])
def test_original_indices_and_pn_mapping(kind):
    """PnIndex remaps authored one-based references without joining coordinates."""
    source = ifcopenshell.file(schema="IFC4")
    item = indexed_item(source, kind, pn=(4, 2, 1))
    points, faces = MODULE.native_faces(item)
    assert points.tolist() == [list(point) for point in POINTS]
    assert faces[0][1] == [(3, 1, 0)]
    assert (faces[0][0] is None) == (kind == "IfcTriangulatedFaceSet")


@pytest.mark.parametrize("indices,pn,message", [
    (((0, 2, 3),), None, "face index"),
    (((1, 2, 5),), None, "face index"),
    (((1, 2, 3),), (1, 2), "face index"),
    (((1, 2, 3),), (1, 2, 5), "PnIndex"),
    (((1, 2),), None, "fewer than three"),
])
def test_invalid_native_indices_fail(indices, pn, message):
    """Malformed references remain unavailable instead of indexing other vertices."""
    item = indexed_item(ifcopenshell.file(schema="IFC4"), indices=indices, pn=pn)
    with pytest.raises(ValueError, match=message):
        MODULE.native_faces(item)


def test_native_hole_is_retained_without_triangulation():
    """Original inner rings remain separate evidence, with no generated fill."""
    source = ifcopenshell.file(schema="IFC4")
    item = indexed_item(source)
    face = source.create_entity("IfcIndexedPolygonalFaceWithVoids", CoordIndex=(1, 2, 3),
                                InnerCoordIndices=((1, 3, 4),))
    item.Faces = [face]
    _, faces = MODULE.native_faces(item)
    assert faces == [(face.id(), [(0, 1, 2), (0, 2, 3)])]


def face_records(triangles):
    """Wrap original zero-based rings for topology-only fixtures."""
    return [(None, [tuple(face)]) for face in triangles]


def test_closed_and_open_index_topology():
    """Closed-cycle links and edge counts expose removal of one tetra face."""
    closed = MODULE.topology(np.array(POINTS), face_records(TETRA))
    assert closed["edge_face_counts"] == {2: 6}
    assert closed["non_closed_cycle_vertex_links"] == closed["inconsistent_winding_edges"] == 0
    opened = MODULE.topology(np.array(POINTS), face_records(TETRA[:-1]))
    assert opened["boundary_edges"] == 3
    assert opened["non_closed_cycle_vertex_links"] == 3
    reversed_face = [tuple(reversed(TETRA[0])), *TETRA[1:]]
    assert MODULE.topology(np.array(POINTS), face_records(reversed_face))["inconsistent_winding_edges"] == 3


def test_coincident_indices_are_never_welded():
    """Two coincident indexed shells stay two components without an inferred union."""
    points = np.array(POINTS + POINTS)
    faces = TETRA + [tuple(i + 4 for i in face) for face in TETRA]
    facts = MODULE.topology(points, face_records(faces))
    assert facts["face_component_count"] == 2
    assert facts["edge_face_counts"] == {2: 12}
    assert all(part["edge_face_counts"] == {2: 6} for part in facts["components"])


def test_multiply_incident_edge_and_disconnected_vertex_link():
    """Edge incidence and point-only shell contact retain distinct failure facts."""
    points = np.array(POINTS + [(0., -1., 0.)])
    facts = MODULE.topology(points, face_records([(0, 1, 2), (1, 0, 3), (0, 1, 4)]))
    assert facts["more_than_two_face_edges"] == 1
    # Sharing only a vertex cannot connect face components through an edge.
    points = np.array(POINTS + POINTS[1:])
    other = [tuple(0 if i == 0 else i + 3 for i in face) for face in TETRA]
    facts = MODULE.topology(points, face_records(TETRA + other))
    assert facts["face_component_count"] == 2
    assert facts["non_closed_cycle_vertex_links"] == 1


def axis(source, location):
    """Author a source-unit placement with default orthogonal directions."""
    point = source.create_entity("IfcCartesianPoint", Coordinates=location)
    return source.create_entity("IfcAxis2Placement3D", Location=point)


def test_mapped_lineage_transform_and_cycle_guard():
    """Authored mapping transforms are retained and cyclic maps fail explicitly."""
    source = ifcopenshell.file(schema="IFC4")
    item = indexed_item(source)
    inner = source.create_entity("IfcShapeRepresentation", Items=[item])
    mapping = source.create_entity("IfcRepresentationMap", MappingOrigin=axis(source, (0., 0., 0.)),
                                   MappedRepresentation=inner)
    target = source.create_entity("IfcCartesianTransformationOperator3D",
                                  LocalOrigin=source.create_entity("IfcCartesianPoint", Coordinates=(10., 20., 30.)))
    mapped = source.create_entity("IfcMappedItem", MappingSource=mapping, MappingTarget=target)
    outer = source.create_entity("IfcShapeRepresentation", Items=[mapped])
    leaf, matrix, lineage = list(MODULE.walk_items(outer))[0]
    assert leaf == item
    assert matrix[:3, 3].tolist() == [10., 20., 30.]
    assert lineage[0]["item"]["step_id"] == mapped.id()
    inner.Items = [mapped]
    with pytest.raises(ValueError, match="Cyclic mapped"):
        list(MODULE.walk_items(outer))


def test_transport_multiset_precision_multiplicity_and_unavailable():
    """Comparison tolerates only the stated float32 cast and retains multiplicity."""
    points = np.array(POINTS)
    native = [{"all_original_faces_triangular": True, "_points": points, "_triangles": [(0, 1, 2)]}]
    capture = {"vertices": points.tolist(), "triangles": [(2, 1, 0)],
               "world_transform": np.eye(4).tolist(), "tessellation_settings": {}}
    assert MODULE.transport_comparison(native, capture)["same_triangle_multiset_at_float32"]
    capture["triangles"] *= 2
    facts = MODULE.transport_comparison(native, capture)
    assert not facts["same_triangle_multiset_at_float32"]
    assert facts["capture_unmatched_triangle_count"] == 1
    capture["triangles"] = [(0, 1, 4)]
    with pytest.raises(ValueError, match="capture indices"):
        MODULE.transport_comparison(native, capture)
    assert MODULE.transport_comparison([{"all_original_faces_triangular": False}], {})["status"] == "not_available"
    assert MODULE.triangle_signatures([[1. + 1e-9, 0, 0]] * 3, [(0, 1, 2)]) == MODULE.triangle_signatures([[1., 0, 0]] * 3, [(0, 1, 2)])


def source_fixture():
    """Bind a minimal actual IFC occurrence to accepted and captured dictionaries."""
    source = ifcopenshell.file(schema="IFC4")
    item = indexed_item(source)
    body = source.create_entity("IfcShapeRepresentation", RepresentationIdentifier="Body",
                                RepresentationType="Tessellation", Items=[item])
    placement = source.create_entity("IfcLocalPlacement", RelativePlacement=axis(source, (1000., 0., 0.)))
    entity = source.create_entity("IfcBuildingElementProxy", GlobalId=ifcopenshell.guid.new(),
                                  ObjectPlacement=placement,
                                  Representation=source.create_entity("IfcProductDefinitionShape", Representations=[body]))
    accepted = {"id": "fixture", "global_id": entity.GlobalId, "ifc_class": entity.is_a(), "status": "unresolved",
                "error": "original error", "quality": {}, "scope": {}, "crossing_triangle_count": 0,
                "section_audit": {"face_count": 0, "residual_lengths_m": {}}, "geometry": {}}
    inventory = {"global_id": entity.GlobalId, "loaded_representation": {"step_id": body.id()}}
    capture = {"representation_id": str(body.id()), "units": "m", "transform_applied": True,
               "vertices": [[1., 0., 0.], [1.001, 0., 0.], [1., .001, 0.]], "triangles": [(0, 1, 2)],
               "world_transform": np.eye(4).tolist(), "tessellation_settings": {}}
    target = (entity.id(), entity.GlobalId, body.id(), item.id(), placement.id())
    return source, target, accepted, inventory, capture


def test_source_placement_scale_and_unqualified_semantics():
    """Only native source units are scaled; a matched capture does not certify a solid."""
    args = source_fixture()
    result = MODULE.collect_source(*args, .001)
    assert result["transport_comparison"]["same_triangle_multiset_at_float32"]
    assert result["native_items"][0]["topology"]["components"][0]["bounds_world_m"][0] == [1., 0., 0.]
    assert result["solid_qualification"] == "not_established_by_native_facts"
    assert result["accepted_error"] == "original error"
    assert result["material_associations"] == []


@pytest.mark.parametrize("mismatch", ["global", "class", "body", "item", "placement", "frame"])
def test_source_binding_rejects_mismatches(mismatch):
    """Frozen identity, native representation and capture-frame mismatches stop a row."""
    source, target, accepted, inventory, capture = source_fixture()
    target = list(target)
    if mismatch == "global":
        accepted["global_id"] = "different"
    elif mismatch == "class":
        accepted["ifc_class"] = "IfcDoor"
    elif mismatch == "body":
        capture["representation_id"] = -1
    elif mismatch == "item":
        target[3] = -1
    elif mismatch == "placement":
        target[4] = -1
    else:
        capture["transform_applied"] = False
    with pytest.raises(ValueError, match="mismatch"):
        MODULE.collect_source(source, target, accepted, inventory, capture, .001)


def test_hash_gate_precedes_native_open(tmp_path, monkeypatch):
    """A wrong frozen IFC cannot reach native parsing or downstream evidence reads."""
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    path = tmp_path / MODULE.IFC
    path.parent.mkdir(parents=True)
    path.write_bytes(b"wrong source")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        MODULE.collect(tmp_path)
    assert not (tmp_path / "native_source_facts.json").exists()
