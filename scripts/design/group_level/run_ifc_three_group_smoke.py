"""Run the selective, read-only D6 three-group IFC smoke check."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.ifc_bonsai import (  # noqa: E402
    IFC_ADAPTER_VERSION,
    _native_group_records,
    _native_length_unit,
    _native_mesh_record,
    _native_source_id,
    _native_world_transform,
    _scene_from_records,
)
from features.group_self_description import describe_group_relations  # noqa: E402
from features.scene_contract import AuthoredGroup, NeutralSceneV2, SourceObject  # noqa: E402


DEFAULT_IFC = "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
SCHEMA = "d6-ifc-three-group-smoke/v1"


def _json(value: object) -> object:
    """Convert IFC helper values and records to strict JSON-compatible values."""
    if hasattr(value, "to_dict"):
        return _json(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite value cannot be serialized")
        return value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _write(path: Path, payload: object) -> None:
    """Write deterministic strict JSON without changing source inputs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> dict[str, object]:
    """Capture immutable source size and SHA-256 evidence."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def _source_id(entity: object) -> str:
    """Return the adapter's stable source identity for one IFC entity."""
    return _native_source_id(entity)


def _representations(entity: object) -> list[dict[str, object]]:
    """Inventory authored IFC representation identifiers without tessellation."""
    product_representation = getattr(entity, "Representation", None)
    records = []
    for representation in getattr(product_representation, "Representations", ()) or ():
        records.append(
            {
                "step_id": f"ifc-step:{representation.id()}" if callable(getattr(representation, "id", None)) else None,
                "identifier": getattr(representation, "RepresentationIdentifier", None),
                "type": getattr(representation, "RepresentationType", None),
                "item_count": len(getattr(representation, "Items", ()) or ()),
            }
        )
    return records


def _group_inventory(source: object) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Inventory every group and its direct authored membership in stable order."""
    records = []
    for group in source.by_type("IfcGroup"):
        members = []
        for relation in getattr(group, "IsGroupedBy", ()) or ():
            members.extend(_source_id(item) for item in getattr(relation, "RelatedObjects", ()) or ())
        source_id = _source_id(group)
        records.append(
            {
                "id": f"ifc-group:{source_id}",
                "source_id": source_id,
                "name": getattr(group, "Name", None),
                "object_type": getattr(group, "ObjectType", None),
                "eligible_exact_role": getattr(group, "ObjectType", None) == "furniture_group",
                "member_refs": [f"ifc-object:{member}" for member in members],
                "member_source_ids": members,
                "member_count": len(members),
                "membership_relation_count": len(getattr(group, "IsGroupedBy", ()) or ()),
            }
        )
    records.sort(key=lambda item: str(item["source_id"]))
    eligible = [item for item in records if item["eligible_exact_role"] and item["member_count"]]
    eligible.sort(key=lambda item: str(item["source_id"]))
    return records, eligible[:3]


def _context_counts(source: object) -> dict[str, int]:
    """Record omitted context classes so the sample cannot imply a full room."""
    names = ("IfcProduct", "IfcWall", "IfcDoor", "IfcSpace", "IfcOpeningElement", "IfcSpatialZone", "IfcGroup")
    return {name: len(source.by_type(name)) for name in names}


def _inventory(args: argparse.Namespace) -> None:
    """Freeze source hash, all group identities, representations, and the first three groups."""
    import ifcopenshell

    source_path = Path(args.ifc).resolve()
    source = ifcopenshell.open(str(source_path))
    groups, selected = _group_inventory(source)
    products = []
    for entity in source.by_type("IfcProduct"):
        source_id = _source_id(entity)
        products.append(
            {
                "id": f"ifc-object:{source_id}",
                "source_id": source_id,
                "class": entity.is_a(),
                "role": getattr(entity, "ObjectType", None),
                "representations": _representations(entity),
            }
        )
    products.sort(key=lambda item: str(item["source_id"]))
    units, scale, has_unit, metadata = _native_length_unit(source)
    payload = {
        "schema": SCHEMA,
        "stage": "inventory",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": _sha256(source_path),
        "ifc_schema": source.schema,
        "adapter_version": IFC_ADAPTER_VERSION,
        "ifcopenshell_version": getattr(importlib.import_module("ifcopenshell"), "version", None),
        "units": {"token": units, "scale_to_metres": scale, "explicit": has_unit, "metadata": metadata},
        "context_counts": _context_counts(source),
        "groups": groups,
        "selected_groups": selected,
        "products": products,
        "selection_policy": "first_three_nonempty_exact_ObjectType_furniture_group_sorted_by_source_id",
        "tessellation": {"performed": False, "scope": "none_during_inventory"},
    }
    _write(Path(args.output_dir) / "inventory.json", payload)
    print(json.dumps({"selected_groups": [item["id"] for item in selected], "groups": len(groups), "products": len(products)}, sort_keys=True))


def _representation(entity: object, identifier: str) -> object | None:
    """Find one authored representation by its exact IFC identifier."""
    product_representation = getattr(entity, "Representation", None)
    return next((item for item in getattr(product_representation, "Representations", ()) or () if getattr(item, "RepresentationIdentifier", None) == identifier), None)


def _matrix_point(matrix: object, point: tuple[float, float, float]) -> tuple[float, float, float]:
    """Apply a 4x4 homogeneous matrix to a three-dimensional point."""
    return tuple(sum(float(matrix[row][column]) * point[column] for column in range(3)) + float(matrix[row][3]) for row in range(3))


def _local_world_check(entity: object, representation: object, world_mesh: object, source_id: str, ifc_module: object) -> dict[str, object]:
    """Independently validate local Analysis coordinates plus the placement matrix."""
    settings = ifc_module.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, False)
    shape = ifc_module.geom.create_shape(settings, entity, representation)
    matrix = ifc_module.util.shape.get_shape_matrix(shape)
    raw = tuple(shape.geometry.verts)
    local = [tuple(float(raw[i + offset]) for offset in range(3)) for i in range(0, len(raw), 3)]
    world = list(world_mesh.vertices)
    transformed = [_matrix_point(matrix, point) for point in local]
    count = min(len(transformed), len(world))
    error = max((max(abs(transformed[i][j] - world[i][j]) for j in range(3)) for i in range(count)), default=None)
    return {
        "member_source_id": source_id,
        "representation": "Analysis",
        "local_units": "m(SI from IfcOpenShell local extraction)",
        "placement_matrix": [[float(matrix[row][column]) for column in range(4)] for row in range(4)],
        "local_vertex_count": len(local),
        "world_vertex_count": len(world),
        "max_abs_vertex_error_m": error,
        "status": "pass" if error is not None and error <= 1e-7 and len(local) == len(world) else "fail",
        "source_id": source_id,
    }


def _probe(args: argparse.Namespace) -> None:
    """Tessellate only selected members, build NeutralSceneV2, and run the descriptor."""
    import ifcopenshell
    import ifcopenshell.geom  # noqa: F401
    import ifcopenshell.util.shape  # noqa: F401

    output_dir = Path(args.output_dir).resolve()
    inventory = json.loads((output_dir / "inventory.json").read_text(encoding="utf-8"))
    source_path = Path(args.ifc).resolve()
    current_hash = _sha256(source_path)
    if current_hash != inventory["source"]:
        raise RuntimeError("source IFC hash changed after inventory; refusing probe")
    source = ifcopenshell.open(str(source_path))
    module = importlib.import_module("ifcopenshell")
    units = str(inventory["units"]["token"])
    group_records = tuple(
        AuthoredGroup(
            id=item["id"], source_id=item["source_id"], member_refs=tuple(item["member_refs"]), group_role="furniture_group",
            provenance={"method": "ifc4_group_assignment", "schema": "IFC4", "selection": "inventory_frozen"},
        )
        for item in inventory["selected_groups"]
    )
    member_ids = sorted({member for group in inventory["selected_groups"] for member in group["member_source_ids"]})
    by_id = {_source_id(entity): entity for entity in source.by_type("IfcProduct")}
    analysis_meshes = []
    body_meshes = []
    source_objects = []
    member_audit = []
    placement_checks = []
    for member_id in member_ids:
        entity = by_id[member_id]
        body_rep = _representation(entity, "Body")
        analysis_rep = _representation(entity, "Analysis")
        body_mesh, body_uncertainty = (None, None) if body_rep is None else _native_mesh_record(entity, f"{member_id}:body", units, module, body_rep)
        analysis_mesh, analysis_uncertainty = (None, None) if analysis_rep is None else _native_mesh_record(entity, f"{member_id}:analysis", units, module, analysis_rep)
        if analysis_mesh is not None:
            analysis_meshes.append(analysis_mesh)
        if body_mesh is not None:
            body_meshes.append({"source_id": member_id, "representation": "Body", "mesh": body_mesh.to_dict()})
        world_transform, placement_uncertainty = _native_world_transform(entity, float(inventory["units"]["scale_to_metres"]), member_id)
        geometry_refs = (analysis_mesh.id,) if analysis_mesh is not None else ()
        uncertainties = tuple(item for item in (analysis_uncertainty, placement_uncertainty) if item is not None)
        source_objects.append(SourceObject(
            id=f"ifc-object:{member_id}", source_id=member_id, source_role="furniture", source_class=entity.is_a(), world_transform=world_transform,
            geometry_refs=geometry_refs, group_refs=tuple(group["id"] for group in inventory["selected_groups"] if member_id in group["member_source_ids"]),
            factual_properties={"representations": _representations(entity), "analysis_authoritative": analysis_mesh is not None},
            provenance={"method": "d6_selective_ifc_extraction", "analysis_representation": "Analysis", "body_representation": "Body"}, uncertainties=uncertainties,
        ))
        member_audit.append({
            "source_id": member_id, "source_object_id": f"ifc-object:{member_id}", "class": entity.is_a(), "representations": _representations(entity),
            "analysis": {"status": "computed" if analysis_mesh else "missing", "mesh_id": analysis_mesh.id if analysis_mesh else None, "vertices": len(analysis_mesh.vertices) if analysis_mesh else 0, "triangles": len(analysis_mesh.triangle_indices) if analysis_mesh else 0, "uncertainty": _json(analysis_uncertainty)},
            "body": {"status": "computed" if body_mesh else "missing", "mesh_id": body_mesh.id if body_mesh else None, "vertices": len(body_mesh.vertices) if body_mesh else 0, "triangles": len(body_mesh.triangle_indices) if body_mesh else 0, "uncertainty": _json(body_uncertainty)},
        })
    for group in inventory["selected_groups"]:
        candidate = next((item for item in group["member_source_ids"] if any(a["source_id"] == item and a["analysis"]["status"] == "computed" for a in member_audit)), None)
        if candidate:
            entity = by_id[candidate]
            analysis_rep = _representation(entity, "Analysis")
            mesh = next(item for item in analysis_meshes if item.id == f"ifc-mesh:{candidate}:analysis")
            placement_checks.append(_local_world_check(entity, analysis_rep, mesh, candidate, module))
    scene = _scene_from_records(units, source_objects, analysis_meshes, authored_groups=group_records, analysis_units="m")
    description = describe_group_relations(scene)
    scene_payload = {"scene": scene.to_dict(), "body_meshes": body_meshes, "sample_source": inventory["source"], "selected_groups": [item["id"] for item in inventory["selected_groups"]]}
    _write(output_dir / "sample_scene.json", scene_payload)
    _write(output_dir / "description.json", description)
    audit = {
        "schema": SCHEMA, "stage": "probe", "source": current_hash, "selected_groups": inventory["selected_groups"], "members": member_audit,
        "placement_checks": placement_checks, "analysis_mesh_count": len(analysis_meshes), "body_mesh_count": len(body_meshes),
        "descriptor_status": description.get("status"), "candidate_view_status": description.get("candidate_view_status"), "candidate_views": description.get("candidate_views"),
        "deferred_fields": {"aggregation_status": all(item.get("aggregation_status") == "deferred" for item in description.get("group_relations", ())), "space_status": description.get("space_observations", {}).get("domain_status"), "three_dimensional": description.get("capabilities", {}).get("3d_clearance", {}).get("status")},
        "read_only": True, "full_loader_used": False, "context_tessellated": False,
    }
    _write(output_dir / "audit.json", audit)
    print(json.dumps({"analysis_meshes": len(analysis_meshes), "body_meshes": len(body_meshes), "placement_checks": placement_checks}, sort_keys=True))


def _verify(args: argparse.Namespace) -> None:
    """Verify saved artifacts, source immutability, and deferred contract fields."""
    import ifcopenshell

    output_dir = Path(args.output_dir).resolve()
    inventory = json.loads((output_dir / "inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((output_dir / "audit.json").read_text(encoding="utf-8"))
    description = json.loads((output_dir / "description.json").read_text(encoding="utf-8"))
    source_hash = _sha256(Path(args.ifc).resolve())
    assert source_hash == inventory["source"] == audit["source"]
    assert len(inventory["selected_groups"]) == 3
    assert description["candidate_views"] is None and description["candidate_view_status"] == "deferred"
    assert all(row["aggregation_status"] == "deferred" for row in description["group_relations"])
    assert all(row["formal_membership_edge"] is None for row in description["group_relations"])
    assert audit["read_only"] and not audit["full_loader_used"]
    assert all(item["status"] == "pass" for item in audit["placement_checks"])
    assert importlib.import_module("ifcopenshell").open(str(Path(args.ifc).resolve())).schema == "IFC4"
    print(json.dumps({"status": "pass", "source_sha256": source_hash["sha256"], "selected_groups": [item["id"] for item in inventory["selected_groups"]]}, sort_keys=True))


def _self_check() -> None:
    """Run a small IFC-free check for selection, transforms, and strict JSON."""
    assert _matrix_point(((1, 0, 0, 2), (0, 1, 0, 3), (0, 0, 1, 4), (0, 0, 0, 1)), (1, 2, 3)) == (3.0, 5.0, 7.0)
    assert json.loads(json.dumps(_json({"x": (1, 2), "y": None}), allow_nan=False))["x"] == [1, 2]
    print(json.dumps({"status": "pass", "checks": ["matrix_transform", "strict_json"]}))


def main() -> None:
    """Dispatch one explicit smoke-check stage."""
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("self-check", "inventory", "probe", "verify"))
    parser.add_argument("--ifc", default=DEFAULT_IFC)
    parser.add_argument("--output-dir", default="outputs/design/ifc_three_group_smoke")
    args = parser.parse_args()
    {"self-check": _self_check, "inventory": lambda: _inventory(args), "probe": lambda: _probe(args), "verify": lambda: _verify(args)}[args.stage]()


if __name__ == "__main__":
    main()
