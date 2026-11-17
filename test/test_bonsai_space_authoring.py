"""Exact native Space inputs: datum, explicit height, topology and SI units."""

from copy import deepcopy

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.geometry
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.unit
import numpy as np
import pytest

from ..adapters import bonsai_space_authoring as authoring


SHELL = ((0, 0), (6, 0), (6, 5), (4, 5), (4, 3), (0, 3), (0, 0))
HOLES = (((1, 1), (2, 1), (2, 2), (1, 2), (1, 1)),)


def native_model(prefix=None):
    """Create an actual IFC model without importing Blender or changing a user file."""
    model = ifcopenshell.file(schema="IFC4")
    ifcopenshell.api.root.create_entity(model, ifc_class="IfcProject")
    unit = ifcopenshell.api.unit.add_si_unit(model, unit_type="LENGTHUNIT", prefix=prefix)
    ifcopenshell.api.unit.assign_unit(model, units=[unit])
    storey = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuildingStorey")
    ifcopenshell.api.geometry.edit_object_placement(model, product=storey, matrix=np.eye(4))
    return model, storey, "ifc-object:" + storey.GlobalId


def slab_mesh():
    """Return a closed triangulated slab whose true upper surface is 0.2 m."""
    return {"vertices": ((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0),
                         (0, 0, .2), (2, 0, .2), (2, 2, .2), (0, 2, .2)),
            "triangles": ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
                          (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
                          (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)),
            "is_closed": True, "is_manifold": True, "units": "m"}


def captured_slab_scene(*, top=.2):
    """Pair a real native datum receipt with independently captured canonical slab/storey facts."""
    from dataclasses import replace
    from ..features.scene_contract import MeshGeometry3D
    from .test_analysis_requests import _missing, _scene
    model, storey, _ref = native_model()
    slab = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSlab")
    ifcopenshell.api.aggregate.assign_object(model, products=[slab], relating_object=storey)
    mesh = slab_mesh()
    mesh["vertices"] = tuple((x + 4, y + 6, z + top - .2) for x, y, z in mesh["vertices"])
    datum = authoring.resolve_slab_datum(model, "ifc-object:" + slab.GlobalId, mesh=mesh)
    geometry = MeshGeometry3D(id="selected-slab", vertices=mesh["vertices"],
        triangle_indices=mesh["triangles"], units="m", is_closed=True, is_manifold=True,
        normals=(), source_representation_id=None, tessellation_settings={},
        local_to_world_provenance={"world_transform_applied": True})
    sources = []
    for entity, role in ((slab, "slab"), (storey, "storey")):
        source = replace(_missing()[0], id="ifc-object:" + entity.GlobalId,
            source_id=entity.GlobalId, source_class=entity.is_a(), source_role=role,
            provenance={"project_global_id": datum["project_global_id"], "step_id": entity.id()})
        if entity == slab:
            source = replace(source, level_ref=datum["storey_ref"], container_refs=(datum["storey_ref"],),
                             geometry_refs=(geometry.id,), uncertainties=())
        sources.append(source)
    scene = _scene((sources[0], geometry), (sources[1], None), origin=(4, 6))
    return replace(scene, context=replace(scene.context,
        world_coordinate_system={"project_global_id": datum["project_global_id"]})), datum


def test_slab_receipt_normalizes_integer_and_float_geometry():
    """Synthetic integer coordinates and captured SI floats describe the same receipt geometry."""
    mesh = slab_mesh()
    floating = {**mesh, "vertices": [[float(value) for value in point] for point in mesh["vertices"]]}
    assert authoring.slab_geometry_digest(mesh) == authoring.slab_geometry_digest(floating)
    scene, datum = captured_slab_scene()
    authoring.validate_captured_slab_datum(scene, datum)


@pytest.mark.parametrize("failure", ["receipt", "project", "slab_step", "storey_step", "source_guid",
    "missing_storey", "containment", "ambiguous_containment", "geometry", "ambiguous_geometry", "top", "slope", "step"])
def test_captured_slab_rejects_changed_identity_geometry_and_top(failure):
    """A frozen slab must still be the selected native solid, even when its top is unchanged."""
    from dataclasses import replace
    scene, datum = captured_slab_scene()
    slab, storey = scene.source_objects
    geometry = scene.geometries[1]
    if failure == "receipt":
        datum["slab_id"] += 1
    elif failure == "project":
        scene = replace(scene, context=replace(scene.context, world_coordinate_system={"project_global_id": "other"}))
    elif failure in {"slab_step", "storey_step", "source_guid", "containment", "ambiguous_containment"}:
        if failure == "slab_step":
            slab = replace(slab, provenance={**slab.provenance, "step_id": datum["slab_id"] + 1})
        elif failure == "storey_step":
            storey = replace(storey, provenance={**storey.provenance, "step_id": datum["storey_id"] + 1})
        elif failure == "source_guid":
            slab = replace(slab, source_id="other")
        else:
            slab = replace(slab, container_refs=("ifc-object:other",) if failure == "containment"
                           else (datum["storey_ref"], "ifc-object:other"))
        scene = replace(scene, source_objects=(slab, storey))
    elif failure == "missing_storey":
        scene = replace(scene, source_objects=(slab,))
    elif failure == "ambiguous_geometry":
        scene = replace(scene, geometries=scene.geometries + (geometry,))
    else:
        vertices = list(geometry.vertices)
        if failure == "geometry":
            vertices = [(x + .1, y, z) for x, y, z in vertices]
        elif failure == "top":
            vertices = [(x, y, z + .1) for x, y, z in vertices]
        elif failure == "slope":
            vertices[6] = (*vertices[6][:2], vertices[6][2] + .1)
        else:
            vertices += [(x + 3, y, z + .3) for x, y, z in geometry.vertices]
            geometry = replace(geometry, vertices=vertices, triangle_indices=geometry.triangle_indices
                + tuple(tuple(index + 8 for index in face) for face in geometry.triangle_indices))
        geometry = replace(geometry, vertices=vertices)
        scene = replace(scene, geometries=(scene.geometries[0], geometry))
        if failure in {"top", "slope", "step"}:
            # A self-consistent receipt digest still cannot hide an invalid or changed top.
            view = {**slab_mesh(), "vertices": vertices, "triangles": geometry.triangle_indices}
            datum["geometry_digest"] = authoring.slab_geometry_digest(view)
            datum["observation_digest"] = authoring.digest({key: value for key, value in datum.items()
                                                          if key != "observation_digest"})
    with pytest.raises(ValueError):
        authoring.validate_captured_slab_datum(scene, datum)


def test_storey_zero_and_transformed_placement_are_real_datums():
    """Zero is valid and nested native placement must be converted exactly once."""
    model, storey, ref = native_model("MILLI")
    assert authoring.resolve_storey_datum(model, ref)["datum_z_m"] == 0
    matrix = np.eye(4)
    matrix[2, 3] = .2
    ifcopenshell.api.geometry.edit_object_placement(model, product=storey, matrix=matrix)
    assert authoring.resolve_storey_datum(model, ref)["datum_z_m"] == pytest.approx(.2)
    storey.ObjectPlacement = None
    storey.Elevation = None
    with pytest.raises(ValueError, match="placement|elevation"):
        authoring.resolve_storey_datum(model, ref)


def test_slab_unique_storey_and_coplanar_upper_triangles():
    """Slab-only datum resolves its native relation without requiring a second storey selection."""
    model, storey, ref = native_model()
    slab = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSlab")
    ifcopenshell.api.aggregate.assign_object(model, products=[slab], relating_object=storey)
    result = authoring.resolve_slab_datum(model, "ifc-object:" + slab.GlobalId, mesh=slab_mesh())
    assert result["storey_ref"] == ref and result["datum_z_m"] == pytest.approx(.2)
    model.createIfcRelContainedInSpatialStructure(ifcopenshell.guid.new(), RelatedElements=[slab], RelatingStructure=storey)
    with pytest.raises(ValueError, match="unique|one"):
        authoring.resolve_slab_datum(model, "ifc-object:" + slab.GlobalId, mesh=slab_mesh())


@pytest.mark.parametrize("failure", ["slope", "step", "open", "nan"])
def test_slab_rejects_unsupported_upper_surfaces(failure):
    """Neither maximum elevation nor a bounding box repairs a sloped or ambiguous surface."""
    mesh = deepcopy(slab_mesh())
    mesh["vertices"] = [list(point) for point in mesh["vertices"]]
    if failure == "slope":
        mesh["vertices"][6][2] = .4
    elif failure == "step":
        second = slab_mesh()
        mesh["vertices"] += [[point[0] + 3, point[1], point[2] + .3] for point in second["vertices"]]
        mesh["triangles"] += tuple(tuple(index + 8 for index in triangle) for triangle in second["triangles"])
    elif failure == "open":
        mesh["is_closed"] = False
    else:
        mesh["vertices"][0][0] = float("nan")
    with pytest.raises(ValueError):
        authoring.horizontal_upper_surface(mesh)


@pytest.mark.parametrize("prefix,override", [(None, False), ("MILLI", False), (None, True), ("MILLI", True)])
def test_unique_gross_height_converts_quantity_unit_before_project_unit(prefix, override):
    """An explicit quantity unit owns the conversion even when the project uses metres."""
    model, storey, ref = native_model(prefix)
    quantity_set = ifcopenshell.api.pset.add_qto(model, product=storey, name="Qto_BuildingStoreyBaseQuantities")
    unit = ifcopenshell.api.unit.add_si_unit(model, unit_type="LENGTHUNIT", prefix="MILLI") if override else None
    raw = 3200. if prefix == "MILLI" or override else 3.2
    quantity = model.createIfcQuantityLength("GrossHeight", None, unit, raw)
    quantity_set.Quantities = [quantity]
    before = tuple(str(entity) for entity in model)
    result = authoring.resolve_height(model, ref, mode="authored")
    assert result["height_m"] == pytest.approx(3.2)
    assert result["quantity_id"] == quantity.id() and result["raw_value"] == raw
    assert result["unit_source"] == ("quantity" if override else "project")
    assert tuple(str(entity) for entity in model) == before


@pytest.mark.parametrize("failure", ["missing", "duplicate", "zero", "negative", "wrong_type"])
def test_authored_height_never_invents_a_fallback(failure):
    """Adjacent elevations and NetHeight do not become an authored GrossHeight."""
    model, storey, ref = native_model()
    storey.Elevation = 0.
    other = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuildingStorey")
    other.Elevation = 3.
    quantity_set = ifcopenshell.api.pset.add_qto(model, product=storey, name="Qto_BuildingStoreyBaseQuantities")
    quantities = [model.createIfcQuantityLength("NetHeight", None, None, 3.)]
    if failure != "missing":
        value = {"zero": 0., "negative": -1.}.get(failure, 3.)
        kind = "IfcQuantityArea" if failure == "wrong_type" else "IfcQuantityLength"
        quantities.append(model.create_entity(kind, "GrossHeight", None, None, value))
    if failure == "duplicate":
        quantities.append(model.createIfcQuantityLength("GrossHeight", None, None, 3.))
    quantity_set.Quantities = quantities
    with pytest.raises(ValueError, match="GrossHeight"):
        authoring.resolve_height(model, ref, mode="authored")
    assert authoring.resolve_height(model, ref, mode="manual", manual_value=3000, manual_unit="mm")["height_m"] == 3


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, None])
def test_manual_height_requires_explicit_finite_positive_length(value):
    """Manual input is independent but is never a default or a boolean length."""
    model, _storey, ref = native_model()
    with pytest.raises(ValueError):
        authoring.resolve_height(model, ref, mode="manual", manual_value=value, manual_unit="m")


def test_exact_polygon_keeps_concavity_hole_and_predeclared_area():
    """The accepted shell/hole have exactly 21 square metres without repair."""
    polygon = authoring.exact_polygon({"type": "Polygon", "coordinates": [SHELL, *HOLES]})
    assert polygon.area == 21 and len(polygon.interiors) == 1


@pytest.mark.parametrize("failure", ["open", "self_cross", "touch", "outside", "nan", "multi"])
def test_exact_polygon_rejects_invalid_topology_without_repair(failure):
    """Ring closure and topology are trust boundaries, not suggestions to a geometry fixer."""
    outline = {"type": "Polygon", "coordinates": [SHELL, *HOLES]}
    if failure == "open":
        outline["coordinates"][0] = SHELL[:-1]
    elif failure == "self_cross":
        outline["coordinates"][0] = ((0, 0), (3, 3), (0, 3), (3, 0), (0, 0))
    elif failure == "touch":
        outline["coordinates"][1] = ((0, 1), (1, 1), (1, 2), (0, 2), (0, 1))
    elif failure == "outside":
        outline["coordinates"][1] = ((8, 8), (9, 8), (9, 9), (8, 8))
    elif failure == "nan":
        outline["coordinates"][1] = ((1, 1), (2, float("nan")), (2, 2), (1, 1))
    else:
        outline = {"type": "MultiPolygon", "coordinates": [outline["coordinates"]]}
    with pytest.raises(ValueError):
        authoring.exact_polygon(outline)


@pytest.mark.parametrize("failure", [None, "frame", "project", "storey", "capture", "candidate", "refused", "reason", "aperture"])
def test_freeze_retains_full_candidate_and_refuses_stale_identity(failure):
    """The immutable receipt binds source, capture, attempt, all rings and explicit authoring inputs."""
    from ..adapters.bonsai_live import StructuralContext
    from ..adapters.blender_analysis_capture import plain

    model, _storey, ref = native_model()
    datum = authoring.resolve_storey_datum(model, ref)
    height = authoring.resolve_height(model, ref, mode="manual", manual_value=3.)
    context = StructuralContext("P", (10., -4.), ((0, 1, 0), (-1, 0, 0), (0, 0, 1)), storey_ref=ref)
    document = {"payload": {"candidates": [{"version_id": "candidate", "identity": {"outline": "observed"},
        "outline": {"type": "Polygon", "coordinates": [SHELL, *HOLES]}}], "session_revision": 1,
        "attempt": {"id": "attempt"}, "provenance": {"frame_id": context.structural_frame_key}},
        "binding": {"structural_context": context.to_dict(), "project_source_identity": {
        "project_global_id": datum["project_global_id"]}, "capture_digest": "capture", "canonical_full_fingerprint": "full",
        "runtime_session": "session", "job_id": "job"}}
    if failure == "frame":
        document["payload"]["provenance"]["frame_id"] = "old"
    elif failure == "project":
        height["project_global_id"] = "different"
    elif failure == "storey":
        height["storey_ref"] = "different"
    elif failure == "capture":
        document["binding"]["capture_digest"] = None
    elif failure == "candidate":
        document["payload"]["candidates"] = []
    elif failure in {"refused", "reason", "aperture"}:
        document["payload"]["candidates"][0].update({
            "refused": {"status": "refused"}, "reason": {"reason": "gap"},
            "aperture": {"unresolved_aperture_refs": ["opening"]}}[failure])
    arguments = {"datum": datum, "height": height, "plane_binding": {"project_global_id": datum["project_global_id"]},
                 "query_key": "whole_height_projection"}
    if failure:
        with pytest.raises(ValueError):
            authoring.freeze_candidate(document, "candidate", **arguments)
    else:
        sketch = authoring.freeze_candidate(document, "candidate", **arguments)
        assert authoring.exact_polygon(sketch["candidate"]["outline"]).area == 21
        assert sketch["binding"]["runtime_session"] == "session" and sketch["attempt"]["id"] == "attempt"
        document["payload"]["candidates"][0]["outline"]["coordinates"] = []
        assert len(sketch["candidate"]["outline"]["coordinates"]) == 2
        assert sketch["sketch_digest"] == authoring.digest({key: value for key, value in plain(sketch).items() if key != "sketch_digest"})

