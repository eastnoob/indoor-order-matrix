"""Author one exact B4 polygon through native IFC profiles, with owned recovery."""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .blender_analysis_capture import digest, freeze, plain


LENGTH_TOLERANCE = 1e-6
AREA_TOLERANCE = 1e-6
VOLUME_TOLERANCE = 1e-5


def _native_entity(model, ref, ifc_class):
    """Resolve one canonical GUID against the active model and exact requested class."""
    if not isinstance(ref, str) or not ref.startswith("ifc-object:"):
        raise ValueError("canonical native reference required")
    try:
        entity = model.by_guid(ref.removeprefix("ifc-object:"))
    except RuntimeError as error:
        raise ValueError("native reference is no longer available") from error
    if entity is None or not entity.is_a(ifc_class):
        raise ValueError("native reference must identify " + ifc_class)
    return entity


def _project(model):
    """Require a unique native project before observing any authoring parameters."""
    projects = model.by_type("IfcProject") if model is not None else ()
    if len(projects) != 1:
        raise ValueError("Space authoring requires exactly one native project")
    return projects[0]


def _length_unit_scale(unit):
    """Resolve explicit native length units without mutating the IFC to create a target unit."""
    from ifcopenshell.util.unit import get_prefix_multiplier

    if unit is None or getattr(unit, "UnitType", None) != "LENGTHUNIT":
        raise ValueError("explicit native length unit required")
    if unit.is_a("IfcSIUnit") and unit.Name == "METRE":
        scale = get_prefix_multiplier(unit.Prefix)
    elif unit.is_a("IfcConversionBasedUnit") and not unit.is_a("IfcConversionBasedUnitWithOffset"):
        factor = unit.ConversionFactor
        scale = float(factor.ValueComponent.wrappedValue) * _length_unit_scale(factor.UnitComponent)
    else:
        raise ValueError("unsupported native length unit")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("invalid native length unit scale")
    return scale


def _project_length_unit(model):
    """Reject missing or ambiguous project units instead of assuming metres."""
    assignment = _project(model).UnitsInContext
    units = [unit for unit in (assignment.Units if assignment else ())
             if getattr(unit, "UnitType", None) == "LENGTHUNIT"]
    if len(units) != 1:
        raise ValueError("one project length unit required")
    _length_unit_scale(units[0])
    return units[0]


def _receipt(model, storey, values):
    """Keep observed native identities and a digest beside the actual selected input."""
    record = {"project_global_id": _project(model).GlobalId,
              "storey_ref": "ifc-object:" + storey.GlobalId, "storey_id": storey.id(), **values}
    return record | {"observation_digest": digest(record)}


def resolve_storey_datum(model, storey_ref):
    """Read transformed native storey elevation in SI; zero is a valid datum."""
    from ifcopenshell.util.placement import get_local_placement

    storey = _native_entity(model, storey_ref, "IfcBuildingStorey")
    scale = _length_unit_scale(_project_length_unit(model))
    placement = getattr(storey, "ObjectPlacement", None)
    if placement is not None:
        matrix = np.asarray(get_local_placement(placement), dtype=float)
        if (not np.isfinite(matrix).all() or not np.allclose(matrix[:3, 2], (0, 0, 1), atol=1e-9, rtol=0)
                or not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-9, rtol=0)):
            raise ValueError("storey placement must be a horizontal rigid frame")
        value = float(matrix[2, 3]) * scale
        provenance = {"placement_id": placement.id(), "world_matrix": matrix.tolist()}
    elif getattr(storey, "Elevation", None) is not None:
        value = float(storey.Elevation) * scale
        provenance = {"elevation": storey.Elevation}
    else:
        raise ValueError("storey has no placement or elevation")
    if not math.isfinite(value):
        raise ValueError("storey elevation must be finite")
    return _receipt(model, storey, {"mode": "storey", "datum_z_m": value,
                    "length_to_m": scale, "provenance": provenance})


def horizontal_upper_surface(mesh):
    """Identify actual upward faces of a closed solid; reject sloped and stepped tops."""
    if mesh.get("is_closed") is not True or mesh.get("is_manifold") is not True or mesh.get("units") != "m":
        raise ValueError("slab requires a closed manifold SI mesh")
    vertices = np.asarray(mesh["vertices"], dtype=float)
    triangles = np.asarray(mesh["triangles"], dtype=int)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all()
            or triangles.ndim != 2 or triangles.shape[1] != 3 or not len(triangles)
            or triangles.min() < 0 or triangles.max() >= len(vertices)):
        raise ValueError("invalid slab surface geometry")
    points = vertices[triangles]
    normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    volume = float(np.einsum("ij,ij->i", points[:, 0], normals).sum() / 6)
    if abs(volume) <= 1e-12:
        raise ValueError("slab solid volume is unavailable")
    # Winding may be uniformly reversed; signed volume identifies outward faces.
    normals *= 1 if volume > 0 else -1
    upward = points[normals[:, 2] > 1e-12]
    if not len(upward):
        raise ValueError("slab has no upward surface")
    elevation = float(upward[0, 0, 2])
    if np.any(np.abs(upward[:, :, 2] - elevation) > LENGTH_TOLERANCE):
        raise ValueError("slab upper surface is sloped or has multiple elevations")
    surface = unary_union([Polygon(face[:, :2]) for face in upward])
    if surface.geom_type != "Polygon" or not surface.is_valid or surface.area <= 0:
        raise ValueError("slab requires one connected horizontal upper surface")
    return elevation


def resolve_slab_datum(model, slab_ref, *, mesh=None):
    """Use one selected slab's actual evaluated top and unique native storey relation."""
    slab = _native_entity(model, slab_ref, "IfcSlab")
    containers = [relation.RelatingStructure for relation in getattr(slab, "ContainedInStructure", ())]
    containers += [relation.RelatingObject for relation in getattr(slab, "Decomposes", ())]
    if len(containers) != 1 or not containers[0].is_a("IfcBuildingStorey"):
        raise ValueError("selected slab requires one unique native storey relation")
    if mesh is None:
        import bpy
        import bonsai.tool as tool
        from .blender_analysis_capture import extract_evaluated_mesh

        obj = tool.Ifc.get_object(slab)
        if (obj is None or tool.Ifc.get_entity(obj) != slab
                or sum(tool.Ifc.get_entity(item) == slab for item in bpy.data.objects) != 1):
            raise ValueError("selected slab requires one verified native object link")
        mesh = extract_evaluated_mesh(obj, bpy.context.evaluated_depsgraph_get(), bpy.context.scene.unit_settings.scale_length)
    return _receipt(model, containers[0], {"mode": "slab", "slab_ref": slab_ref,
                    "slab_id": slab.id(), "datum_z_m": horizontal_upper_surface(mesh),
                    "geometry_digest": digest({key: mesh[key] for key in
                        ("vertices", "triangles", "units", "is_closed", "is_manifold")})})


def resolve_height(model, storey_ref, *, mode, manual_value=None, manual_unit="m"):
    """Use only a unique GrossHeight quantity or an independently explicit manual length."""
    storey = _native_entity(model, storey_ref, "IfcBuildingStorey")
    if mode == "manual":
        if isinstance(manual_value, bool) or not isinstance(manual_value, (int, float)) or manual_unit not in {"m", "mm"}:
            raise ValueError("manual height requires a numeric length and m or mm units")
        value = float(manual_value) * (1 if manual_unit == "m" else .001)
        record = {"raw_value": manual_value, "input_unit": manual_unit, "unit_source": "manual"}
    elif mode == "authored":
        matches = []
        for relation in getattr(storey, "IsDefinedBy", ()):
            definition = getattr(relation, "RelatingPropertyDefinition", None)
            if (definition is not None and definition.is_a("IfcElementQuantity")
                    and definition.Name == "Qto_BuildingStoreyBaseQuantities"):
                matches.extend((definition, quantity) for quantity in definition.Quantities if quantity.Name == "GrossHeight")
        if len(matches) != 1 or not matches[0][1].is_a("IfcQuantityLength"):
            raise ValueError("one valid Qto_BuildingStoreyBaseQuantities.GrossHeight IfcQuantityLength required")
        definition, quantity = matches[0]
        unit = quantity.Unit if quantity.Unit is not None else _project_length_unit(model)
        scale = _length_unit_scale(unit)
        value = float(quantity.LengthValue) * scale
        record = {"quantity_set_id": definition.id(), "quantity_id": quantity.id(),
                  "path": "Qto_BuildingStoreyBaseQuantities.GrossHeight", "raw_value": quantity.LengthValue,
                  "unit_id": unit.id(), "unit": str(unit), "length_to_m": scale,
                  "unit_source": "quantity" if quantity.Unit is not None else "project"}
    else:
        raise ValueError("height mode must be authored or manual")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("GrossHeight or manual height must be finite and positive")
    return _receipt(model, storey, {"mode": mode, "height_m": value, **record})


def exact_polygon(outline):
    """Accept one valid closed Polygon with strict interior holes without geometric repair."""
    if not isinstance(outline, Mapping) or outline.get("type") != "Polygon":
        raise ValueError("one Polygon outline required")
    rings = outline.get("coordinates", ())
    if not rings:
        raise ValueError("polygon shell required")
    for ring in rings:
        if (len(ring) < 4 or tuple(ring[0]) != tuple(ring[-1])
                or any(len(point) != 2 or any(isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) for value in point) for point in ring)):
            raise ValueError("polygon rings must contain finite XY coordinates and be explicitly closed")
    polygon = Polygon(rings[0], rings[1:])
    shell = Polygon(rings[0])
    holes = [Polygon(ring) for ring in rings[1:]]
    if (not polygon.is_valid or polygon.is_empty or polygon.area <= 0
            or any(not shell.contains(hole) or shell.boundary.intersects(hole) for hole in holes)
            or any(hole.intersects(other) for index, hole in enumerate(holes) for other in holes[index + 1:])):
        raise ValueError("polygon rings have invalid or touching topology")
    return polygon


def freeze_candidate(document, candidate_id, *, datum, height, plane_binding, query_key):
    """Freeze one existing B4 candidate and its complete observation into a value receipt."""
    from .bonsai_live import StructuralContext

    payload, binding = document["payload"], document["binding"]
    candidates = [item for item in payload["candidates"] if item.get("version_id") == candidate_id]
    if len(candidates) != 1 or candidates[0].get("domain_kind") == "authored_ifcspace":
        raise ValueError("one current B4 candidate required")
    candidate = candidates[0]
    if (candidate.get("reason") is not None or candidate.get("status") in {"refused", "stale", "invalid"}
            or candidate.get("unresolved_aperture_refs")):
        raise ValueError("candidate is refused, stale or has unresolved apertures")
    exact_polygon(candidate["outline"])
    context = StructuralContext(**binding["structural_context"])
    if (context.datum_z_m != datum["datum_z_m"] or context.storey_ref != datum["storey_ref"]
            or height["storey_ref"] != datum["storey_ref"]
            or height["project_global_id"] != datum["project_global_id"]
            or binding["project_source_identity"]["project_global_id"] != datum["project_global_id"]
            or plane_binding["project_global_id"] != datum["project_global_id"]):
        raise ValueError("candidate frame, datum, height or project is stale")
    if not all(binding.get(key) for key in ("capture_digest", "canonical_full_fingerprint", "runtime_session", "job_id")):
        raise ValueError("candidate lacks complete capture/session identity")
    provenance = payload["provenance"]
    if provenance["frame_id"] != context.structural_frame_key:
        raise ValueError("candidate structural frame is stale")
    record = {"version": 1, "candidate": plain(candidate), "session_revision": payload["session_revision"],
              "attempt": plain(payload["attempt"]), "provenance": plain(provenance), "binding": plain(binding),
              "datum": plain(datum), "height": plain(height), "plane_binding": plain(plane_binding),
              "query_key": query_key, "outline_digest": digest(candidate["outline"])}
    return freeze(record | {"sketch_digest": digest(record)})


def revalidate_sketch(sketch):
    """Reobserve native inputs before opening a transaction; no stored digest grants authority."""
    import bonsai.tool as tool
    from .bonsai_analysis_plane import camera_composition, plane_from_camera, resolve_camera_binding
    from .bonsai_live import StructuralContext, load_bonsai_capture

    record = plain(sketch)
    claimed = record.pop("sketch_digest", None)
    if claimed != digest(record) or record["outline_digest"] != digest(record["candidate"]["outline"]):
        raise ValueError("frozen sketch digest changed")
    exact_polygon(record["candidate"]["outline"])
    model = tool.Ifc.get()
    datum = record["datum"]
    observed_datum = (resolve_storey_datum(model, datum["storey_ref"]) if datum["mode"] == "storey"
                      else resolve_slab_datum(model, datum["slab_ref"]))
    height = record["height"]
    observed_height = resolve_height(model, height["storey_ref"], mode=height["mode"],
        manual_value=height.get("raw_value"), manual_unit=height.get("input_unit", "m"))
    if observed_datum != datum or observed_height != height:
        raise ValueError("native datum or height changed; prepare the candidate again")
    plane_record = record["plane_binding"]
    camera = resolve_camera_binding(project_global_id=plane_record["project_global_id"], camera_guid=plane_record["camera_guid"])
    plane = plane_from_camera(camera, name="Analysis plane", query_kind=record["query_key"])
    observed_plane = camera_composition(camera, plane)
    if any(observed_plane[key] != plane_record[key] for key in ("project_global_id", "camera_guid", "origin", "basis")):
        raise ValueError("native camera changed; refresh and prepare the candidate again")
    capture = _canonical_recapture(record["binding"]["runtime_session"])
    context = StructuralContext(**record["binding"]["structural_context"])
    live = load_bonsai_capture(capture, plane=context.analysis_plane)
    if live.full_fingerprint != record["binding"]["canonical_full_fingerprint"]:
        raise ValueError("source geometry changed; prepare the candidate again")
    return model


def _canonical_recapture(session):
    """Use the existing complete capture boundary for authoring preflight and exact result adoption."""
    import bpy
    from .blender_analysis_capture import (begin_analysis_capture, capture_next_batch, finalize_capture,
                                           normalized_capture_steps, CanonicalCaptureInput)

    job = begin_analysis_capture(bpy_context=bpy.context, scene_token=session)
    while job.stage == "capturing":
        capture_next_batch(job)
    steps = normalized_capture_steps(finalize_capture(job))
    while True:
        try:
            next(steps)
        except StopIteration as done:
            return CanonicalCaptureInput(**done.value)


def _expected_world_polygon(sketch):
    """Transform structural XY rings to world SI once, preserving every boundary."""
    frame = sketch["binding"]["structural_context"]
    basis = np.asarray(frame["xy_basis"], dtype=float)
    origin = np.asarray(frame["xy_origin_m"], dtype=float)
    rings = [np.asarray(ring, dtype=float) @ basis[:2, :2] + origin
             for ring in sketch["candidate"]["outline"]["coordinates"]]
    return Polygon(rings[0], rings[1:])


def verify_extrusion(sketch, vertices, triangles):
    """Compare topology, each ring, SI elevations and signed volume against frozen inputs."""
    expected = _expected_world_polygon(sketch)
    vertices = np.asarray(vertices, dtype=float)
    triangles = np.asarray(triangles, dtype=int)
    if not np.isfinite(vertices).all() or not len(triangles):
        raise ValueError("native round-trip returned invalid geometry")
    faces = vertices[triangles]
    pieces = [Polygon(face[:, :2]) for face in faces]
    projection = unary_union([piece for piece in pieces if piece.area > 1e-14])
    if (projection.geom_type != "Polygon" or not projection.is_valid
            or len(projection.interiors) != len(expected.interiors)
            or abs(projection.area - expected.area) > AREA_TOLERANCE
            or projection.exterior.hausdorff_distance(expected.exterior) > LENGTH_TOLERANCE):
        raise ValueError("native round-trip shell, holes or area changed")
    remaining = list(projection.interiors)
    for ring in expected.interiors:
        matches = [observed for observed in remaining if observed.hausdorff_distance(ring) <= LENGTH_TOLERANCE]
        if len(matches) != 1:
            raise ValueError("native round-trip hole boundary changed")
        remaining.remove(matches[0])
    base = sketch["datum"]["datum_z_m"]
    height = sketch["height"]["height_m"]
    volume = abs(float(np.einsum("ij,ij->i", faces[:, 0], np.cross(faces[:, 1], faces[:, 2])).sum() / 6))
    if (abs(float(vertices[:, 2].min()) - base) > LENGTH_TOLERANCE
            or abs(float(vertices[:, 2].max()) - base - height) > LENGTH_TOLERANCE
            or abs(volume - expected.area * height) > VOLUME_TOLERANCE):
        raise ValueError("native round-trip base, top or volume changed")
    return {"area_m2": projection.area, "holes": len(projection.interiors), "base_m": base,
            "top_m": base + height, "volume_m3": volume,
            "tolerances": {"length_m": LENGTH_TOLERANCE, "area_m2": AREA_TOLERANCE, "volume_m3": VOLUME_TOLERANCE}}


def _write_native_space(sketch):
    """Create exact void-capable native geometry and return the native entity and object."""
    import bpy
    import bonsai.tool as tool
    import bonsai.core.root
    import bonsai.core.geometry
    import ifcopenshell.geom
    from ifcopenshell.util.representation import get_context
    from ifcopenshell.util.shape_builder import ShapeBuilder
    from mathutils import Matrix

    model = tool.Ifc.get()
    unit_scale = _length_unit_scale(_project_length_unit(model))
    frame = sketch["binding"]["structural_context"]
    product_matrix = np.eye(4)
    # Keep rotation in the profile so Blender's Euler decomposition cannot perturb exact right angles.
    product_matrix[:3, 3] = (*frame["xy_origin_m"], sketch["datum"]["datum_z_m"])
    world_polygon = _expected_world_polygon(sketch)
    inverse = np.linalg.inv(product_matrix)
    builder = ShapeBuilder(model)
    curves = []
    # SI world to product-local to IFC length units is a single explicit boundary.
    for ring in (world_polygon.exterior, *world_polygon.interiors):
        points = np.asarray([[*point, sketch["datum"]["datum_z_m"], 1.] for point in ring.coords[:-1]])
        local = (points @ inverse.T)[:, :2] / unit_scale
        curves.append(builder.polyline(local, closed=True))
    profile = builder.profile(curves[0], inner_curves=curves[1:])
    solid = builder.extrude(profile, magnitude=sketch["height"]["height_m"] / unit_scale)
    body_context = get_context(model, "Model", "Body", "MODEL_VIEW")
    if body_context is None:
        raise ValueError("native Model/Body context required")
    representation = builder.get_representation(body_context, solid)
    mesh = bpy.data.meshes.new("Analyzer Space")
    obj = bpy.data.objects.new("Analyzer Space", mesh)
    bpy.context.scene.collection.objects.link(obj)
    entity = bonsai.core.root.assign_class(tool.Ifc, tool.Collector, tool.Root,
        obj=obj, ifc_class="IfcSpace", should_add_representation=False)
    storey = _native_entity(model, sketch["datum"]["storey_ref"], "IfcBuildingStorey")
    tool.Ifc.run("aggregate.assign_object", products=[entity], relating_object=storey)
    tool.Ifc.run("geometry.edit_object_placement", product=entity, matrix=product_matrix, is_si=True)
    tool.Ifc.run("geometry.assign_representation", product=entity, representation=representation)
    bonsai.core.geometry.switch_representation(tool.Ifc, tool.Geometry, obj=obj, representation=representation)
    tool.Collector.assign(obj)
    scene_scale = bpy.context.scene.unit_settings.scale_length
    blender_matrix = product_matrix.copy()
    blender_matrix[:3, :] /= scene_scale
    obj.matrix_world = Matrix(blender_matrix)
    bpy.context.view_layer.update()
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    shape = ifcopenshell.geom.create_shape(settings, entity)
    geometry = verify_extrusion(sketch, np.asarray(shape.geometry.verts).reshape(-1, 3),
                                np.asarray(shape.geometry.faces).reshape(-1, 3))
    return entity, obj, geometry


def _invoke_space_operation(operator, context):
    """Keep native transaction execution as a single fault-injectable seam."""
    from bonsai.bim.ifc import IfcStore

    return IfcStore.execute_ifc_operator(operator, context)


def create_native_space(sketch):
    """Validate, create and recapture one exact Space, recovering only this operation on failure."""
    import bpy
    import bonsai.tool as tool
    from bonsai.bim.ifc import IfcStore
    from bonsai.tool.brick import BrickStore
    from types import SimpleNamespace
    from .bonsai_analysis_plane import _drawing_snapshot, _recover_drawing
    from .bonsai_live import StructuralContext, load_bonsai_capture, authored_space_composition

    model = tool.Ifc.get()
    if bpy.context.scene.get("om_analysis_authoring_recovery_error"):
        raise ValueError("native authoring blocked after failed recovery; reopen a verified file")
    if model is None or IfcStore.current_transaction or IfcStore.modal_in_progress or model.transaction is not None:
        raise ValueError("finish the unrelated native transaction before creating a Space")
    if model.history_size <= 0 or bpy.context.mode != "OBJECT":
        raise ValueError("Space creation requires Object mode and native IFC history")
    if sketch["sketch_digest"] in bpy.context.scene.get("om_analysis_created_sketches", ()):
        raise ValueError("this sketch has already created a native Space")
    revalidate_sketch(sketch)
    # The proven camera recovery boundary also covers every resource this narrow writer owns.
    before = _drawing_snapshot(bpy, tool, IfcStore, BrickStore)
    created = []
    transaction_key = None
    begin_descriptor = IfcStore.__dict__["begin_transaction"]
    native_begin = IfcStore.begin_transaction

    def begin(operator):
        """Retain our exact native transaction key before class/link operations begin."""
        nonlocal transaction_key
        if transaction_key is not None:
            raise RuntimeError("Space writer attempted another top-level transaction")
        native_begin(operator)
        transaction_key = operator.transaction_key

    def execute(_context):
        """Keep native creation and geometry validation in the same owned transaction."""
        created.append(_write_native_space(sketch))
        return {"FINISHED"}

    IfcStore.begin_transaction = staticmethod(begin)
    try:
        status = _invoke_space_operation(SimpleNamespace(bl_idname="om_analysis.exact_space", _execute=execute), bpy.context)
        if status != {"FINISHED"} or len(created) != 1 or model.transaction is not None or IfcStore.current_transaction:
            raise ValueError("native Space creation cancelled or left an incomplete transaction")
        entity, obj, geometry = created[0]
        if tool.Ifc.get_object(entity) is not obj or tool.Ifc.get_entity(obj) != entity:
            raise ValueError("native Space identity handoff changed")
        context = StructuralContext(**plain(sketch["binding"]["structural_context"]))
        live = load_bonsai_capture(_canonical_recapture(sketch["binding"]["runtime_session"]), plane=context.analysis_plane)
        source = next(source for source in live.scene.source_objects if source.source_id == entity.GlobalId)
        if not source.geometry_refs:
            raise ValueError("native Space recapture failed: " + "; ".join(item.message for item in source.uncertainties))
        binding = authored_space_composition(live.scene, entity.GlobalId, storey_ref=sketch["datum"]["storey_ref"])
        source = next(source for source in live.scene.source_objects if source.id == binding["source_id"])
        mesh = next(mesh for mesh in live.scene.geometries if mesh.id == source.geometry_refs[0])
        verify_extrusion(sketch, mesh.vertices, mesh.triangle_indices)
        binding["origin"] = "created_from_b4"
        binding["provenance"] = {**binding["provenance"], "authoring": plain(sketch), "round_trip": geometry}
        bpy.context.scene["om_analysis_created_sketches"] = [*bpy.context.scene.get("om_analysis_created_sketches", ()), sketch["sketch_digest"]]
        return {"entity": entity, "object": obj, "guid": entity.GlobalId, "space_binding": binding, "geometry": geometry}
    except Exception as error:
        try:
            _recover_drawing(before, transaction_key, bpy, tool, IfcStore, BrickStore)
        except Exception as recovery_error:
            bpy.context.scene["om_analysis_authoring_recovery_error"] = str(recovery_error)
            raise RuntimeError("native Space recovery failed: " + str(recovery_error)) from error
        raise
    finally:
        IfcStore.begin_transaction = begin_descriptor

