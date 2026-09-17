"""Capture a Rhino/VisualARQ document into the neutral IFC export source format.

This script is executed inside Rhino through MCP.  It deliberately keeps the
Rhino document read-only: block instances are expanded in memory, while the
source object itself remains one logical occurrence in the exported payload.
"""

import json
import os
import re
import sys
from pathlib import Path

import Rhino

OUTPUT_PATH = r"D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\full-rhino-ifc-2026-09-21\live-rhino-10500-source.json"

# Rhino MCP runs this script from a temporary location. Add the repository root
# explicitly so the shared metadata rule is identical in tests and live capture.
REPOSITORY_ROOT = Path(OUTPUT_PATH).parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from rhino_block_metadata import (
    effective_block_user_text,
    is_furniture_group,
)

AUTHORED_CLASSES = {
    "IfcFurniture",
    "IfcFurnishingElement",
    "IfcEquipmentElement",
    "IfcElectricalElement",
    "IfcWall",
    "IfcDoor",
    "IfcWindow",
    "IfcColumn",
    "IfcBeam",
    "IfcSlab",
    "IfcRoof",
    "IfcStair",
    "IfcRailing",
    "IfcOpeningElement",
    "IfcBuildingElementProxy",
}

VISUALARQ_PREFIX_CLASSES = {
    "*Wall{": "IfcWall",
    "*Door{": "IfcDoor",
    "*Window{": "IfcWindow",
    "*Column{": "IfcColumn",
    "*Beam{": "IfcBeam",
    "*Slab{": "IfcSlab",
    "*Roof{": "IfcRoof",
    "*Stair{": "IfcStair",
    "*Railing{": "IfcRailing",
}


def _point(point):
    """Convert a Rhino point to JSON-safe millimetre coordinates."""
    return [float(point.X), float(point.Y), float(point.Z)]


def _user_text(attributes):
    """Read Rhino user strings without modifying authored attributes."""
    result = {}
    try:
        values = attributes.GetUserStrings()
        for key in values.Keys:
            result[str(key)] = str(values[key])
    except Exception:
        pass
    return result


def _definition_name(doc, geometry):
    """Return the authored block definition name for an instance geometry."""
    if not isinstance(geometry, Rhino.Geometry.InstanceReferenceGeometry):
        return ""
    definition = doc.InstanceDefinitions.FindId(geometry.ParentIdefId)
    return definition.Name if definition else ""


def _definition_user_text(doc, geometry):
    """Read reusable User Text authored on one Block Definition."""
    if not isinstance(geometry, Rhino.Geometry.InstanceReferenceGeometry):
        return {}
    definition = doc.InstanceDefinitions.FindId(geometry.ParentIdefId)
    return _user_text(definition) if definition else {}


def _effective_user_text(doc, instance):
    """Resolve Definition metadata first, then apply instance-specific overrides."""
    return effective_block_user_text(
        _definition_user_text(doc, instance.Geometry), _user_text(instance.Attributes)
    )


def _mesh_parts(geometry):
    """Tessellate one Rhino geometry into analysis/export mesh parts."""
    if isinstance(geometry, Rhino.Geometry.Mesh):
        return [geometry.DuplicateMesh()]
    if isinstance(geometry, Rhino.Geometry.Brep):
        meshes = Rhino.Geometry.Mesh.CreateFromBrep(
            geometry, Rhino.Geometry.MeshingParameters.Default
        )
        return list(meshes or [])
    if isinstance(geometry, Rhino.Geometry.Extrusion):
        brep = geometry.ToBrep(True)
        return _mesh_parts(brep) if brep else []
    return []


def _append_mesh(mesh, transform, vertices, faces):
    """Append a transformed mesh into one logical object's triangle payload."""
    start = len(vertices)
    transformed = mesh.DuplicateMesh()
    transformed.Transform(transform)
    for vertex in transformed.Vertices:
        vertices.append([float(vertex.X), float(vertex.Y), float(vertex.Z)])
    for mesh_face in transformed.Faces:
        if mesh_face.IsQuad:
            faces.append([start + mesh_face.A, start + mesh_face.B, start + mesh_face.C])
            faces.append([start + mesh_face.A, start + mesh_face.C, start + mesh_face.D])
        else:
            faces.append([start + mesh_face.A, start + mesh_face.B, start + mesh_face.C])


def _collect_geometry(doc, geometry, transform, vertices, faces, stack, depth=0):
    """Recursively expand nested block instances without creating extra products."""
    if geometry is None or depth > 12:
        return
    if isinstance(geometry, Rhino.Geometry.InstanceReferenceGeometry):
        definition_id = str(geometry.ParentIdefId)
        if definition_id in stack:
            return
        definition = doc.InstanceDefinitions.FindId(geometry.ParentIdefId)
        if not definition:
            return
        next_transform = transform * geometry.Xform
        for child in definition.GetObjects():
            _collect_geometry(
                doc,
                child.Geometry,
                next_transform,
                vertices,
                faces,
                stack | {definition_id},
                depth + 1,
            )
        return
    for mesh in _mesh_parts(geometry):
        _append_mesh(mesh, transform, vertices, faces)


def _nested_branch_role(doc, child):
    """Classify an authored furniture child as Body or Analysis geometry."""
    geometry = child.Geometry
    layer = doc.Layers[child.Attributes.LayerIndex].FullPath.lower()
    definition = _definition_name(doc, geometry).upper()
    user_text = _user_text(child.Attributes)
    explicit = str(
        user_text.get("OM_RepresentationRole")
        or user_text.get("OM_AnalysisRole")
        or ""
    ).lower()
    if explicit in {"analysis", "analysis_only", "masspatch", "proxy"}:
        return "analysis"
    # VisualARQ/Rhino-authored branch markers are evaluated only inside an
    # already identified furniture instance; they do not guess IFC classes.
    if "::proxy" in layer or "PROXY" in definition:
        return "analysis"
    return "body"


def _collect_furniture_branches(
    doc,
    geometry,
    transform,
    body_vertices,
    body_faces,
    proxy_vertices,
    proxy_faces,
):
    """Expand one furniture block while keeping Body and MassPatch separate."""
    if not isinstance(geometry, Rhino.Geometry.InstanceReferenceGeometry):
        _collect_geometry(
            doc,
            geometry,
            transform,
            body_vertices,
            body_faces,
            set(),
        )
        return
    definition = doc.InstanceDefinitions.FindId(geometry.ParentIdefId)
    if not definition:
        return
    next_transform = transform * geometry.Xform
    for child in definition.GetObjects():
        target_vertices, target_faces = (
            (proxy_vertices, proxy_faces)
            if _nested_branch_role(doc, child) == "analysis"
            else (body_vertices, body_faces)
        )
        _collect_geometry(
            doc,
            child.Geometry,
            next_transform,
            target_vertices,
            target_faces,
            {str(geometry.ParentIdefId)},
        )


def _curve_points(curve, transform):
    """Capture a stable start/end representation for an authored Guide curve."""
    start = curve.PointAtStart
    end = curve.PointAtEnd
    start.Transform(transform)
    end.Transform(transform)
    if start.DistanceTo(end) <= 1e-9:
        return None
    return {"points": [_point(start), _point(end)]}


def _guide_record(doc, instance):
    """Serialize one VisualARQ Guide instance as grid evidence, not a product."""
    geometry = instance.Geometry
    definition = doc.InstanceDefinitions.FindId(geometry.ParentIdefId)
    if not definition:
        return None
    curves = []
    for child in definition.GetObjects():
        if isinstance(child.Geometry, Rhino.Geometry.Curve):
            points = _curve_points(child.Geometry, geometry.Xform)
            if points:
                curves.append(points)
    if not curves:
        return None
    return {
        "id": str(instance.Id),
        "name": instance.Attributes.Name or str(instance.Id),
        "definition_name": definition.Name,
        "curves": curves,
    }


def _semantic_class(name, layer, user_text, definition):
    """Resolve only explicit labels or authored VisualARQ definition families."""
    for key in ("IfcEntity", "OM.IfcEntity"):
        value = str(user_text.get(key, "")).strip()
        if value in AUTHORED_CLASSES:
            return value, "authored_user_text"
    for prefix, value in VISUALARQ_PREFIX_CLASSES.items():
        if definition.startswith(prefix):
            return value, "authored_visualarq_definition"
    target_family = str(user_text.get("OM_TargetFamily", "")).upper()
    upper_name = str(name).upper()
    if target_family.startswith("TABLE_") or target_family.startswith("CHAIR_"):
        return "IfcFurniture", "authored_project_furniture_marker"
    if definition.upper().startswith(("TABLE_", "CHAIR_")) or upper_name.startswith(
        ("TABLE_", "CHAIR_")
    ):
        return "IfcFurniture", "authored_project_furniture_name"
    if layer in {"OM_REPLACED_Table", "OM_PREVIEW_Chair_Replacements"}:
        return "IfcFurniture", "authored_project_furniture_layer"
    return "unknown", "none"


def _kind(ifc_entity, definition, name, user_text):
    """Assign a neutral role for downstream analysis without changing IFC semantics."""
    if ifc_entity == "IfcFurniture":
        family = user_text.get("OM_TargetFamily", "")
        return "table" if "TABLE" in family.upper() or "TABLE" in name.upper() else "chair"
    if ifc_entity == "unknown":
        return "other"
    return ifc_entity.removeprefix("Ifc").lower()


def _source_record(doc, instance, source_id, transform, user_text, group_id=None):
    """Capture one logical source product using a composed world transform."""
    geometry = instance.Geometry
    name = instance.Attributes.Name or ""
    layer = doc.Layers[instance.Attributes.LayerIndex].FullPath
    definition = _definition_name(doc, geometry)
    ifc_entity, evidence = _semantic_class(name, layer, user_text, definition)
    vertices = []
    faces = []
    proxy_vertices = []
    proxy_faces = []
    if ifc_entity == "IfcFurniture":
        # Furniture keeps its rendered Body and nested MassPatch separate so
        # the IFC writer can attach both representations to one occurrence.
        _collect_furniture_branches(
            doc,
            geometry,
            transform,
            vertices,
            faces,
            proxy_vertices,
            proxy_faces,
        )
    else:
        _collect_geometry(doc, geometry, transform, vertices, faces, set())
    role = _kind(ifc_entity, definition, name, user_text)
    family = user_text.get("OM_TargetFamily") or definition or role
    display_name = (
        name
        or user_text.get("OM_TargetFamily")
        or definition.split("{")[0].lstrip("*")
        or role
    )
    record = {
        "id": str(source_id),
        "name": display_name,
        "display_name": display_name,
        "layer": layer,
        "object_type": geometry.ObjectType.ToString() if geometry else "None",
        "source_definition": definition,
        "source_model": doc.Name,
        "user_text": user_text,
        "vertices": vertices,
        "faces": faces,
        "kind": role,
        "type_family_id": family,
        "source_semantics": {
            "ifc_entity": ifc_entity,
            "ifc_entity_source": evidence,
            "confidence": "authored" if ifc_entity != "unknown" else "unknown",
        },
        "analysis_participation": "include" if ifc_entity == "IfcFurniture" else "exclude",
    }
    if group_id is not None:
        record["authored_furniture_group_id"] = str(group_id)
    if proxy_vertices and proxy_faces:
        # Nested proxy vertices remain in the composed world coordinate frame.
        # The IFC writer localizes them to this product's placement later.
        record["analysis_substitutes"] = [
            {
                "substitute_id": str(source_id) + ":masspatch",
                "substitute_kind": "MassPatch",
                "analysis_role": "analysis_geometry_substitute",
                "visibility_policy": "analysis_only",
                "vertices": proxy_vertices,
                "triangle_indices": proxy_faces,
            }
        ]
    return record


def _capture_furniture_group(doc, outer_instance, user_text):
    """Expand one explicit group container into products and member references."""
    geometry = outer_instance.Geometry
    definition = doc.InstanceDefinitions.FindId(geometry.ParentIdefId)
    if not definition:
        return [], None
    group_id = str(outer_instance.Id)
    records = []
    member_ids = []
    # Definition children are a stable authored membership order. Pairing this
    # path with the outer instance GUID yields unique occurrences for repeats.
    for child_index, child in enumerate(definition.GetObjects()):
        child_id = f"{group_id}:member:{child_index}"
        child_user_text = _effective_user_text(doc, child)
        record = _source_record(
            doc,
            child,
            child_id,
            geometry.Xform,
            child_user_text,
            group_id=group_id,
        )
        records.append(record)
        if record["source_semantics"]["ifc_entity"] in {
            "IfcFurniture",
            "IfcFurnishingElement",
        }:
            member_ids.append(child_id)
    group = {
        "id": group_id,
        "name": outer_instance.Attributes.Name or definition.Name,
        "member_ids": member_ids,
        "source_definition": definition.Name,
        "user_text": user_text,
    }
    return records, group


def capture():
    """Capture all Rhino objects and write one complete source payload."""
    doc = __rhino_doc__
    objects = []
    furniture_groups = []
    guides = []
    excluded_facts = {"point_or_curve": 0, "guide_instances": 0, "empty_geometry": 0}
    for index, instance in enumerate(doc.Objects):
        geometry = instance.Geometry
        name = instance.Attributes.Name or ""
        layer = doc.Layers[instance.Attributes.LayerIndex].FullPath
        user_text = _effective_user_text(doc, instance)
        definition = _definition_name(doc, geometry)
        if definition.startswith("*Guide{"):
            guide = _guide_record(doc, instance)
            if guide:
                guides.append(guide)
            excluded_facts["guide_instances"] += 1
            continue

        if is_furniture_group(user_text):
            # An explicit outer Block is a relationship container. Capture its
            # nested logical products but never flatten the container itself.
            member_records, group = _capture_furniture_group(doc, instance, user_text)
            objects.extend(member_records)
            if group is not None:
                furniture_groups.append(group)
            continue

        record = _source_record(
            doc,
            instance,
            str(instance.Id),
            Rhino.Geometry.Transform.Identity,
            user_text,
        )
        if not record["vertices"] or not record["faces"]:
            excluded_facts["empty_geometry"] += 1
            if not isinstance(geometry, Rhino.Geometry.Mesh) and not isinstance(
                geometry, Rhino.Geometry.Brep
            ):
                excluded_facts["point_or_curve"] += 1
        objects.append(record)

    payload = {
        "schema_version": "visualarq-source-1",
        "source_application": "Rhino",
        "source_name": doc.Name,
        "source_path": doc.Path or "",
        "provider": "rhino_mcp_10500",
        "objects": objects,
        "furniture_groups": furniture_groups,
        "visualarq_guides": guides,
        "excluded_source_facts": excluded_facts,
    }
    parent = os.path.dirname(OUTPUT_PATH)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    counts = {}
    for record in objects:
        value = record.get("source_semantics", {}).get("ifc_entity", "unknown")
        counts[value] = counts.get(value, 0) + 1
    print(json.dumps({"path": OUTPUT_PATH, "objects": len(objects), "furniture_groups": len(furniture_groups), "guides": len(guides), "semantic_counts": counts, "excluded": excluded_facts}, ensure_ascii=False))


capture()
