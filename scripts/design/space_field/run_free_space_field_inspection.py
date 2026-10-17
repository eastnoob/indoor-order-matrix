"""Build the locked whole-height FreeSpaceField inspection artifact."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import html
import json
import re
import argparse
from pathlib import Path
import sys
import time
from typing import Any
from uuid import uuid4

from shapely.affinity import translate
from shapely.geometry import Polygon, shape
from shapely.ops import triangulate

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from features.free_space_field import FreeSpaceField
from features.geometry_substitutes import mass_patch_from_mesh
from features.geometry_views import plan_projection
from features.neutral_scene_views import analysis_scene_view
from features.scene_contract import (
    AnalysisContext,
    AnalysisDomain,
    AnalysisPlane,
    MeshGeometry3D,
    NeutralSceneV2,
    SourceObject,
    UncertaintyRecord,
)
from features.space_field_visualization import build_field_layer_manifest
from features.field_core import FieldQuery
from features.scene_contract import MISSING_GEOMETRY_UNCERTAINTY
import trimesh
from scripts.design.space_field import run_b3_shared_occupancy_enrollment as B3

PACKAGE = B3.OUTPUT / "run_20261009T142454Z_0d7308"
OUTPUT = ROOT / "outputs/design/free_space_field_inspection"
SPACING_M = 0.25
UNKNOWN_IDS = (
    "live-step-43654",
    "live-step-49645",
    "live-step-55636",
    "live-step-61627",
    "live-step-67618",
)


def _mesh_from_polygon(polygon: Polygon, mesh_id: str) -> MeshGeometry3D:
    """Extrude a polygon just enough for the shared plan projector to preserve holes."""
    vertices: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []
    for triangle in triangulate(polygon):
        clipped = polygon.intersection(triangle)
        pieces = [clipped] if clipped.geom_type == "Polygon" else list(getattr(clipped, "geoms", ()))
        for piece in pieces:
            for face in triangulate(piece):
                if face.is_empty or not piece.covers(face.representative_point()):
                    continue
                coords = list(face.exterior.coords)[:3]
                base = len(vertices)
                vertices.extend([(x, y, 0.0) for x, y in coords])
                vertices.extend([(x, y, 0.01) for x, y in coords])
                triangles.extend(
                    [
                        (base, base + 1, base + 2), (base + 3, base + 5, base + 4),
                        (base, base + 3, base + 4), (base, base + 4, base + 1),
                        (base + 1, base + 4, base + 5), (base + 1, base + 5, base + 2),
                        (base + 2, base + 5, base + 3), (base + 2, base + 3, base),
                    ]
                )
    return MeshGeometry3D(
        id=mesh_id,
        vertices=vertices,
        triangle_indices=triangles,
        normals=(),
        is_manifold=True,
        is_closed=True,
        local_to_world_provenance={"world_transform_applied": True, "method": "frozen_domain_polygon"},
        source_representation_id="frozen-domain",
        tessellation_settings={"method": "shapely-triangulate"},
        units="m",
    )


def _whole_height_scene() -> tuple[NeutralSceneV2, dict[str, Any]]:
    """Normalize the authenticated B3 products into a whole-height scene handoff."""
    bindings, accepted, originals, capture, scope, declaration, boundary, _, groups = B3.frozen_inputs()
    artifact_manifest = B3.PRIOR.read_json(PACKAGE / "artifact_manifest.json")
    if artifact_manifest["schema"] != "b3-primary-eye-artifacts/v1" or artifact_manifest["status"] != "exit_0":
        raise ValueError("inspection_package_not_authenticated")
    for ref in artifact_manifest["artifacts"]:
        path = ROOT / ref["path"]
        actual = B3.PRIOR.file_ref(path)
        if (actual["bytes"], actual["sha256"]) != (ref["bytes"], ref["sha256"]):
            raise ValueError(f"inspection_artifact_fingerprint_mismatch:{path.name}")
    selection = B3.PRIOR.read_json(PACKAGE / "selection_audit.json")
    if tuple(selection["unknown_source_ids"]) != UNKNOWN_IDS:
        raise ValueError("locked_unknown_ids_mismatch")
    if selection["boundary_scoped_ids"] != ["live-step-6231"]:
        raise ValueError("locked_boundary_membership_mismatch")
    original_by_id = {row["id"]: row for row in originals}
    meshes: list[MeshGeometry3D] = []
    domain_polygon = shape(accepted["domain_geometry"])
    domain_mesh = _mesh_from_polygon(domain_polygon, "frozen-domain-mesh")
    for row in capture["inventory"]:
        source_id = row["id"]
        geometry_ref = row.get("geometry")
        if geometry_ref is None:
            continue
        path = B3.CAPTURE / geometry_ref["path"]
        actual = B3.PRIOR.file_ref(path)
        if (actual["bytes"], actual["sha256"]) != (geometry_ref["bytes"], geometry_ref["sha256"]):
            raise ValueError(f"capture_mesh_fingerprint_mismatch:{source_id}")
        mesh = B3.PRIOR.read_json(path)
        meshes.append(MeshGeometry3D(
            id=f"capture-mesh:{source_id}", vertices=mesh["vertices"],
            triangle_indices=mesh["triangles"], normals=(),
            is_manifold=mesh["is_manifold"], is_closed=mesh["is_closed"], units="m",
            source_representation_id=mesh["representation_id"],
            tessellation_settings=mesh["tessellation_settings"],
            local_to_world_provenance={"world_transform_applied": True, "mesh_ref": geometry_ref},
        ))
    proxy_metadata = B3.PRIOR.read_json(B3.COMP.PROXIES / "mesh_proxies.json")
    for target in bindings["targets"]:
        obj = B3.verified_ref(target["obj_ref"])
        loaded = trimesh.load_scene(obj, file_type="obj", process=False, maintain_order=True,
                                    group_material=False, skip_materials=True)
        mesh = next(iter(loaded.geometry.values()))
        checks = target["generated_mesh_checks"]
        if len(mesh.vertices) != checks["vertex_count"] or len(mesh.faces) != checks["triangle_count"]:
            raise ValueError(f"proxy_mesh_check_mismatch:{target['target_id']}")
        meshes.append(MeshGeometry3D(
            id=target["mesh_id"], vertices=mesh.vertices.tolist(), triangle_indices=mesh.faces.tolist(),
            normals=(), is_manifold=True, is_closed=True, units="m",
            source_representation_id="GeneratedProxy",
            tessellation_settings={"method": "accepted_obj_process_false"},
            local_to_world_provenance={"world_transform_applied": True, "obj_ref": target["obj_ref"]},
        ))
    mesh_by_source = {mesh.id.removeprefix("capture-mesh:"): mesh for mesh in meshes if mesh.id.startswith("capture-mesh:")}
    sources = []
    owner_bindings = {
        source_id: target
        for target in bindings["targets"]
        for source_id in target["represented_source_ids"]
    }
    unknown = set(selection["unknown_source_ids"])
    scoped_nonmass = {row["id"] for row in originals if row["status"] == "excluded_semantic_nonmass"}
    support_slab = {row["id"] for row in originals if row["status"] == "excluded_support_slab"}
    for row in capture["inventory"]:
        source_id = row["id"]
        original = original_by_id[source_id]
        geometry_ref = row.get("geometry")
        geometry_id = f"capture-mesh:{source_id}" if geometry_ref else None
        if source_id in unknown:
            sources.append(SourceObject(
                id=source_id, source_id=row["global_id"], source_role=row["function"] or row["ifc_class"],
                source_class=row["ifc_class"], factual_properties={"frozen_status": original["status"],
                "capture_ref": geometry_ref}, provenance={"capture_ref": geometry_ref},
                uncertainties=(UncertaintyRecord(code=MISSING_GEOMETRY_UNCERTAINTY,
                    message="Whole-height physical occupancy geometry is unresolved", source_refs=(source_id,),
                    operation="whole_height_transport", severity="warning"),)))
            continue
        if source_id in scoped_nonmass or source_id in support_slab:
            sources.append(SourceObject(
                id=source_id, source_id=row["global_id"],
                source_role="analysis_domain" if source_id in support_slab or source_id in scoped_nonmass
                else row["function"] or row["ifc_class"],
                source_class=row["ifc_class"], geometry_refs=(geometry_id,) if geometry_id else (),
                factual_properties={"frozen_status": original["status"], "occupancy_exclusion": "upstream_scope"},
                provenance={"capture_ref": geometry_ref},
                uncertainties=() if geometry_id else (UncertaintyRecord(code=MISSING_GEOMETRY_UNCERTAINTY,
                    message="Excluded by upstream semantic scope", source_refs=(source_id,),
                    operation="whole_height_transport", severity="info"),)))
            continue
        sources.append(SourceObject(
            id=source_id, source_id=row["global_id"], source_role=row["function"] or row["ifc_class"],
            source_class=row["ifc_class"], geometry_refs=(geometry_id,) if geometry_id else (),
            factual_properties={
                "frozen_status": original["status"], "capture_ref": geometry_ref,
                **({
                    "OM_FunctionSubstitutes": [{
                        "consumer": "physical_occupancy",
                        "source_object_id": source_id,
                        "substitute_id": owner_bindings[source_id]["target_id"],
                        "substitute_kind": "MassPatch",
                        "analysis_role": "physical_occupancy_substitute",
                        "representation_identifier": "GeneratedProxy",
                        "provenance": {
                            "representation_identifier": "GeneratedProxy",
                            "binding_declaration_sha256": B3.PRIOR.file_ref(B3.BINDINGS)["sha256"],
                            "scope_binding": bindings["scope_binding"],
                        },
                    }]
                } if source_id in owner_bindings else {}),
                **({"furniture_analysis_participation": "excluded"} if source_id in owner_bindings else {}),
            },
            provenance={"capture_ref": geometry_ref},
            uncertainties=() if geometry_id else (UncertaintyRecord(code=MISSING_GEOMETRY_UNCERTAINTY,
                message="No captured body geometry", source_refs=(source_id,),
                operation="whole_height_transport", severity="warning"),)))
    for target in bindings["targets"]:
        sources.append(SourceObject(
            id=target["target_id"], source_role="analysis_substitute",
            geometry_refs=(target["mesh_id"],),
            factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": target["represented_source_ids"]},
                                "furniture_analysis_participation": "excluded"},
            provenance={"representation_identifier": "GeneratedProxy", "obj_ref": target["obj_ref"],
                        "approximation_limit": "Convex hull fills gaps and concavities; original material is not certified"},
        ))
    context = AnalysisContext(
        contract_version="neutral-scene-v2",
        source_schema="IFC4",
        adapter_version="b3-whole-height-inspection-v1",
        source_length_unit="mm",
        analysis_length_unit="m",
        world_coordinate_system={"frame": "world_xy", "units": "m", "origin_offset_m": [0.0, 0.0]},
        level_references=(),
        analysis_plane=AnalysisPlane(
            name="world_xy_whole_height",
            origin=(0.0, 0.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        geometry_tolerance=1e-9,
        topology_tolerance=1e-9,
        walking_body_profiles=(),
        visual_height_bands=(),
        capability_flags={"physical_planar_occupancy": False},
        input_mode="blender_geometry",
    )
    domain = AnalysisDomain(
        id="b3-selected-s3-whole-height",
        geometry_refs=(domain_mesh.id,),
        source_id="frozen-domain-source",
        selection_method="frozen_explicit_selected_scope",
        provenance={
            "boundary_member_source_ids": sorted(boundary),
            "scope_binding": bindings["scope_binding"],
            "frame": "world_xy",
            "units": "m",
            "origin_offset_m": [0.0, 0.0],
        },
    )
    domain_source = SourceObject(
        id="frozen-domain-source",
        source_id="frozen-domain-source",
        source_role="analysis_domain",
        source_class="AnalysisDomain",
        geometry_refs=(domain_mesh.id,),
        factual_properties={"domain_support": True},
        provenance={"method": "frozen_domain_polygon"},
    )
    scene = NeutralSceneV2(
        context=context,
        analysis_domain=domain,
        source_objects=tuple([*sources, domain_source]),
        geometries=tuple([*meshes, domain_mesh]),
    )
    return scene, {
        "bindings": bindings,
        "accepted": accepted,
        "selection": selection,
        "capture": capture,
        "transport": {"original_source_count": len(capture["inventory"]),
                      "capture_body_mesh_count": len([m for m in meshes if m.id.startswith("capture-mesh:")]),
                      "proxy_mesh_count": len(bindings["targets"])},
        "originals": originals,
        "artifact_manifest": artifact_manifest,
        "input_hashes": _input_hash_ledger(bindings, capture, artifact_manifest),
        "domain_polygon": domain_polygon,
    }


def _components(geometry: object) -> list[dict[str, object]]:
    """Convert a shapely polygon or multipolygon into field component rings."""
    items = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    return [
        {
            "exterior": tuple((float(x), float(y)) for x, y in item.exterior.coords),
            "holes": tuple(
                tuple((float(x), float(y)) for x, y in ring.coords) for ring in item.interiors
            ),
        }
        for item in items
    ]


def _jsonable(value: object) -> object:
    """Convert immutable mapping/tuple metadata without changing its values."""
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _merge_selected_audit(
    source_layer: list[dict[str, object]],
    selected_records: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Join the complete selected-record audit back onto serialized geometry."""
    audit_by_id = {
        record.get("id"): record for record in selected_records if isinstance(record, Mapping)
    }
    return [
        {
            **record,
            **{
                key: value
                for key, value in audit_by_id.get(record.get("id"), {}).items()
                if key not in {"id", "geometry_components"}
            },
        }
        for record in source_layer
    ]


def _input_hash_ledger(
    bindings: Mapping[str, object],
    capture: Mapping[str, object],
    artifact_manifest: Mapping[str, object],
) -> list[dict[str, object]]:
    """Return every consumed package, capture-mesh, and proxy-object fingerprint."""
    entries = [
        {"kind": "package_artifact", **{
            key: ref[key] for key in ("path", "bytes", "sha256")
        }}
        for ref in artifact_manifest["artifacts"]
    ]
    entries.append({"kind": "binding_declaration", **B3.PRIOR.file_ref(B3.BINDINGS)})
    for path, kind in (
        (B3.CAPTURE / "capture_manifest.json", "capture_manifest"),
        (B3.CAPTURE / "structural_capture.json", "structural_capture"),
        (B3.CAPTURE / "s3_scope.json", "scope"),
        (B3.COMP.PROXIES / "mesh_proxies.json", "proxy_metadata"),
    ):
        entries.append({"kind": kind, **B3.PRIOR.file_ref(path)})
    for row in capture["inventory"]:
        geometry = row.get("geometry")
        if geometry:
            entries.append({
                "kind": "captured_mesh",
                "source_id": row["id"],
                "path": str((B3.CAPTURE / geometry["path"]).relative_to(ROOT)),
                "bytes": geometry["bytes"],
                "sha256": geometry["sha256"],
            })
    for target in bindings["targets"]:
        entries.append({"kind": "proxy_object", "target_id": target["target_id"],
                        **B3.PRIOR.file_ref(B3.ROOT / target["obj_ref"]["path"])})
    return entries


def _normalized_ledger(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    """Normalize legacy capture mesh paths before comparing handoff fingerprints."""
    normalized = []
    for entry in entries:
        item = dict(entry)
        path = str(item.get("path", "")).replace("\\", "/")
        if item.get("kind") == "captured_mesh" and path.startswith("meshes/"):
            item["path"] = str((B3.CAPTURE / path).relative_to(ROOT)).replace("\\", "/")
        else:
            item["path"] = path
        normalized.append(item)
    return sorted(normalized, key=lambda value: (value.get("kind", ""), value.get("path", "")))


def _write_final_artifacts(
    output: Path, payload: dict[str, object], html_template: str
) -> dict[str, int]:
    """Write binary JSON/HTML outputs whose embedded payload and byte sizes agree."""
    payload["sizes"] = {"json_bytes": 0, "html_bytes": 0}
    for _ in range(12):
        manifest_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        safe_json = json.dumps(payload, sort_keys=True).replace("</", "<\\/")
        html_text = re.sub(
            r"(<script type='application/json' id='inspection'>).*?(</script>)",
            lambda match: match.group(1) + safe_json + match.group(2),
            html_template,
            flags=re.S,
        )
        sizes = {"json_bytes": len(manifest_bytes), "html_bytes": len(html_text.encode("utf-8"))}
        if payload.get("sizes") == sizes:
            break
        payload["sizes"] = sizes
    else:
        raise ValueError("final_artifact_sizes_did_not_converge")
    manifest_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    (output / "inspection_manifest.json").write_bytes(manifest_bytes)
    (output / "inspection.html").write_bytes(html_text.encode("utf-8"))
    return payload["sizes"]



def recover_cell(payload: Mapping[str, object], index: int) -> dict[str, object]:
    """Recover the exact manifest cell record from shared provenance storage."""
    cell = dict(payload["field_layer"]["samples"][index])
    cell.pop("provenance_ref", None)
    cell.pop("target", None)
    provenance = dict(cell.get("provenance", {}))
    provenance["selected_records"] = next(
        item["records"] for item in payload["shared_provenance"]["records"]
        if item["provenance_ref"] == "selected-records"
    )
    if cell.get("support") is not None:
        provenance["support"] = cell["support"]
    cell["provenance"] = provenance
    return cell


def build_inspection(projected_handoff: Path | None = None) -> tuple[dict[str, Any], FreeSpaceField]:
    """Build the field, exact manifest, deduplicated payload, and self-contained HTML."""
    projection_start = time.perf_counter()
    if projected_handoff is None:
        scene, facts = _whole_height_scene()
        view = analysis_scene_view(scene)
        projection_ms = (time.perf_counter() - projection_start) * 1000.0
        domain_id = scene.analysis_domain.id
        offset = tuple(view["_analysis_view"]["origin_offset"])
        source_layer_handoff = None
    else:
        handoff = json.loads((projected_handoff / "inspection_manifest.json").read_text(encoding="utf-8"))
        bindings, accepted, originals, capture, scope, declaration, boundary, diagnostics, groups = B3.frozen_inputs()
        artifact_manifest = B3.PRIOR.read_json(PACKAGE / "artifact_manifest.json")
        authenticated_scene, authenticated_facts = _whole_height_scene()
        domain_components = handoff.get("domain", {}).get("components", ())
        expected_domain_id = authenticated_scene.analysis_domain.id
        if (
            handoff.get("schema") != "free-space-field-inspection/v1"
            or handoff.get("frame") != "world_xy"
            or handoff.get("units") != "m"
            or handoff.get("query_scope") != "whole_height_plan"
            or handoff.get("source_origin_offset_m") != [0.0, 0.0]
            or handoff.get("resolution_m") != SPACING_M
            or handoff.get("domain", {}).get("id") != expected_domain_id
            or handoff.get("domain", {}).get("frame") != "world_xy"
            or len(domain_components) != 1
            or len(domain_components[0].get("holes", ())) != 2
        ):
            raise ValueError("projection_handoff_contract_mismatch")
        fresh_ledger = _input_hash_ledger(bindings, capture, artifact_manifest)
        if _normalized_ledger(handoff.get("input_hashes", {}).get("entries", [])) != _normalized_ledger(fresh_ledger):
            raise ValueError("projection_handoff_ledger_mismatch")
        expected_ids = set(
            B3.PRIOR.read_json(PACKAGE / "selection_audit.json")["selected_source_ids"]
        ) | {target["target_id"] for target in bindings["targets"]}
        if set(item["id"] for item in handoff["source_layer"]) != expected_ids:
            raise ValueError("projection_handoff_source_identity_mismatch")
        if handoff["audit"]["boundary_member_source_ids"] != sorted(boundary):
            raise ValueError("projection_handoff_boundary_membership_mismatch")
        if tuple(handoff["audit"]["unknown_source_ids"]) != tuple(
            B3.PRIOR.read_json(PACKAGE / "selection_audit.json")["unknown_source_ids"]
        ):
            raise ValueError("projection_handoff_unknown_identity_mismatch")
        facts = {
            "bindings": bindings,
            "selection": B3.PRIOR.read_json(PACKAGE / "selection_audit.json"),
            "capture": capture,
            "originals": originals,
            "input_hashes": _input_hash_ledger(bindings, capture, artifact_manifest),
            "transport": {
                "original_source_count": handoff.get("input_hashes", {}).get("source_record_count", 358),
                "capture_body_mesh_count": handoff.get("input_hashes", {}).get("captured_body_mesh_count", 354),
                "proxy_mesh_count": handoff.get("input_hashes", {}).get("proxy_target_count", 3),
            },
            "domain_polygon": Polygon(
                handoff["domain"]["components"][0]["exterior"],
                handoff["domain"]["components"][0].get("holes", ()),
            ),
        }
        effective_domain = translate(
            authenticated_facts["domain_polygon"],
            xoff=handoff["origin_offset_m"][0],
            yoff=handoff["origin_offset_m"][1],
        )
        handoff_domain = facts["domain_polygon"]
        if effective_domain.symmetric_difference(handoff_domain).area > 1e-8:
            raise ValueError("projection_handoff_domain_geometry_mismatch")
        view = {
            "physical_occupancy": handoff["source_layer"],
            "_analysis_view": {
                "origin_offset": tuple(handoff["origin_offset_m"]),
                "physical_occupancy_unresolved_source_ids": tuple(
                    handoff["audit"]["unknown_source_ids"]
                ),
            },
        }
        projection_ms = handoff.get("timings", {}).get("projection_ms", 0.0)
        domain_id = handoff["domain"]["id"]
        offset = tuple(handoff["origin_offset_m"])
        source_layer_handoff = handoff["source_layer"]
        domain_already_shifted = True
        source_facts_from_scene = {source.id: source for source in authenticated_scene.source_objects}
    unresolved = tuple(view["_analysis_view"]["physical_occupancy_unresolved_source_ids"])
    if unresolved != tuple(sorted(UNKNOWN_IDS)):
        raise ValueError(f"whole_height_unresolved_drift:{unresolved}")
    accepted_ids = {
        record["id"] for record in view["physical_occupancy"]
        if record.get("representation_status") == "accepted"
    }
    expected_proxy_ids = {target["target_id"] for target in facts["bindings"]["targets"]}
    if accepted_ids != expected_proxy_ids:
        raise ValueError(f"whole_height_proxy_drift:{sorted(accepted_ids)}")
    represented = [
        owner for record in view["physical_occupancy"] if record["id"] in expected_proxy_ids
        for owner in record.get("represented_source_ids", ())
    ]
    expected_owners = [owner for target in facts["bindings"]["targets"]
                       for owner in target["represented_source_ids"]]
    if sorted(represented) != sorted(expected_owners) or len(represented) != len(set(represented)):
        raise ValueError("whole_height_proxy_owner_coverage_drift")
    domain = (
        facts["domain_polygon"]
        if projected_handoff is not None
        else translate(facts["domain_polygon"], xoff=offset[0], yoff=offset[1])
    )
    bounds = domain.bounds
    n_cols = int((bounds[2] - bounds[0]) / SPACING_M) + 1
    n_rows = int((bounds[3] - bounds[1]) / SPACING_M) + 1
    physical = list(view["physical_occupancy"])
    field = FreeSpaceField(
        domain={
            "id": domain_id,
            "frame": "world_xy",
            "components": _components(domain),
        },
        origin=(bounds[0], bounds[1]),
        spacing=SPACING_M,
        n_rows=n_rows,
        n_cols=n_cols,
        physical_occupancy=physical,
        unresolved_source_ids=UNKNOWN_IDS,
        query_context={
            "domain_id": domain_id,
            "frame": "world_xy",
            "plane": None,
            "height_band": None,
            "demand": None,
            "geometry_query": "whole_height_planar_mass_patch",
        },
        frame="world_xy",
        origin_offset=offset,
    )
    query = FieldQuery(
        domain_id=domain_id,
        frame="world_xy",
        plane=None,
        height_band=None,
        demand=None,
    )
    evaluation_start = time.perf_counter()
    samples = field.evaluate_many(
        ((row, column) for row in range(n_rows) for column in range(n_cols)), query
    )
    field_evaluation_ms = (time.perf_counter() - evaluation_start) * 1000.0
    layer = build_field_layer_manifest(layer_id="physical-occupancy", channel="occupancy", samples=samples)
    for sample in layer["samples"]:
        sample["target"] = sample["support"]["target"]
    selected_records = _jsonable(field.provenance["selected_records"])
    shared = {"selected_records": {"provenance_ref": "selected-records",
                                   "records": selected_records}}
    shared_records = list(shared.values())
    cells = []
    for sample in layer["samples"]:
        cell_provenance = dict(sample["provenance"])
        cell_provenance.pop("selected_records", None)
        support = cell_provenance.pop("support", None)
        cells.append({**sample, "support": support, "provenance_ref": "selected-records",
                      "provenance": cell_provenance})
    recovery_mismatches = []
    for index, (cell, original) in enumerate(zip(cells, layer["samples"])):
        recovered = recover_cell(
            {"field_layer": {"samples": cells}, "shared_provenance": {"records": shared_records}},
            index,
        )
        expected = dict(original)
        expected.pop("target", None)
        if _jsonable(recovered) != _jsonable(expected):
            recovery_mismatches.append(index)
    source_layer = source_layer_handoff or [
        {
            key: _jsonable(record.get(key))
            for key in (
                "id", "represented_source_ids", "representation_status",
                "geometry_components", "representation_provenance",
                "representation_diagnostics", "_neutral_source_id",
                "_source_geometry_refs", "adapter_refs", "provenance",
            )
            if key in record
        }
        for record in view["physical_occupancy"]
    ]
    source_layer = _merge_selected_audit(source_layer, selected_records)
    source_facts = (
        {source.id: source for source in scene.source_objects}
        if projected_handoff is None
        else source_facts_from_scene
    )
    source_layer = source_layer if projected_handoff is not None else [
        {
            **record,
            "source_class": source_facts[record["id"]].source_class,
            "source_role": source_facts[record["id"]].source_role,
            "furniture_analysis_participation": (
                source_facts[record["id"]].factual_properties.get(
                    "furniture_analysis_participation"
                )
            ),
            "source_refs": {
                "geometry_refs": list(source_facts[record["id"]].geometry_refs),
                "provenance": _jsonable(source_facts[record["id"]].provenance),
            },
        }
        for record in source_layer
    ]
    if projected_handoff is not None:
        for record in source_layer:
            source = source_facts[record["id"]]
            record.update(
                source_class=source.source_class,
                source_role=source.source_role,
                furniture_analysis_participation=source.factual_properties.get(
                    "furniture_analysis_participation"
                ),
                source_refs={
                    "geometry_refs": list(source.geometry_refs),
                    "provenance": _jsonable(source.provenance),
                    "_source_geometry_refs": record.get("_source_geometry_refs", []),
                    "adapter_refs": record.get("adapter_refs", {}),
                },
            )
    original_categories = {row["id"]: row.get("category") for row in facts["originals"]}
    for record in source_layer:
        if record.get("representation_status") == "accepted":
            record["display_category"] = "accepted_proxy"
        elif str(original_categories.get(record["id"], "")).startswith("furniture"):
            record["display_category"] = "furniture"
        else:
            record["display_category"] = "physical_context"
    uncertainty_sources = [
        {
            "source_id": source.id,
            "source_class": source.source_class,
            "source_role": source.source_role,
            "uncertainties": [item.to_dict() for item in source.uncertainties],
            "source_refs": {
                "capture": _jsonable(source.provenance.get("capture_ref")),
            },
        }
        for source in (
            scene.source_objects if projected_handoff is None
            else authenticated_scene.source_objects
        )
        if source.id in UNKNOWN_IDS
    ]
    payload = {
        "schema": "free-space-field-inspection/v1",
        "frame": "world_xy",
        "units": "m",
        "origin_offset_m": list(offset),
        "source_origin_offset_m": [0.0, 0.0],
        "query_scope": "whole_height_plan",
        "resolution_m": SPACING_M,
        "domain": {"id": domain_id, "frame": "world_xy", "components": _components(domain)},
        "source_layer": source_layer,
        "uncertainty_sources": uncertainty_sources,
        "input_hashes": {
            "schema": "input-hash-ledger/v1",
            "source_record_count": 358,
            "captured_body_mesh_count": 354,
            "proxy_target_count": 3,
            "entries": facts["input_hashes"],
        },
        "resolution": {
            "value_m": SPACING_M,
            "label": "demonstration-only",
            "query_scope": "whole_height_plan",
            "historical_section_z_m": 1.6,
            "historical_section_not_used": True,
        },
        "status_availability": {
            status: {"available": any(
                sample["status"] == status for sample in layer["samples"]
            )}
            for status in (
                "established", "conditional", "unknown",
                "outside", "invalid", "not_available",
            )
        },
        "field_layer": {"schema": layer["schema"], "samples": cells},
        "shared_provenance": {"records": shared_records},
        "acceptance": {
            "schema": "free-space-field-inspection-acceptance/v3",
            "cell_count": len(cells),
            "sc002_mismatch_count": len(recovery_mismatches),
            "sc007_recovery_mismatch_count": len(recovery_mismatches),
            "historical_samples_not_used": True,
        },
        "timings": {"projection_ms": projection_ms, "field_evaluation_ms": field_evaluation_ms},
        "limits": [
            "False means empty physical occupancy only, never walkability, clearance, or connectivity.",
            "Historical 9648-sample zero-mismatch evidence is eye-plane-only.",
        ],
        "audit": {
            "unknown_source_ids": list(UNKNOWN_IDS),
            "boundary_member_source_ids": list(
                facts["selection"].get(
                    "boundary_scoped_ids",
                    facts["selection"].get("boundary_member_source_ids", []),
                )
            ),
            "source_counts": facts["transport"],
            "scope_normalization": [
                {
                    "source_id": row["id"],
                    "original_source_role": next(
                        (item.get("function") or item.get("ifc_class")
                         for item in facts["capture"]["inventory"] if item["id"] == row["id"]),
                        None,
                    ),
                    "upstream_status": row["status"],
                    "normalized_role": "analysis_domain" if row["status"] in {
                        "excluded_semantic_nonmass", "excluded_support_slab"
                    } else row.get("function") or row.get("ifc_class"),
                    "reason": "upstream semantic/support-slab scope exclusion",
                }
                for row in facts["originals"]
                if row.get("status") in {"excluded_semantic_nonmass", "excluded_support_slab"}
            ],
            "source_display_counts": {
                "furniture": sum(item.get("display_category") == "furniture" for item in source_layer),
                "physical_context": sum(item.get("display_category") == "physical_context" for item in source_layer),
                "accepted_proxies": sum(item.get("display_category") == "accepted_proxy" for item in source_layer),
            },
        },
    }
    serialization_start = time.perf_counter()
    json_bytes = len(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    colors = {
        "established": "#86efac", "established_occupied": "#16a34a",
        "established_empty": "#bbf7d0", "conditional": "#fde68a",
        "unknown": "#fca5a5", "outside": "#cbd5e1",
        "invalid": "#c4b5fd", "not_available": "#fdba74",
    }
    scale = min(430.0 / max(bounds[2] - bounds[0], 1e-9), 580.0 / max(bounds[3] - bounds[1], 1e-9))
    def point(x: float, y: float, ox: float) -> tuple[float, float]:
        """Map world coordinates into the fixed SVG viewport."""
        return ox + (x - bounds[0]) * scale, 640.0 - (y - bounds[1]) * scale
    def path_for(component: Mapping[str, object], ox: float) -> str:
        """Serialize one polygon component, including holes, as SVG paths."""
        rings = [component["exterior"], *component.get("holes", ())]
        return " ".join(
            "M " + " L ".join(f"{point(x, y, ox)[0]:.2f},{point(x, y, ox)[1]:.2f}" for x, y in ring) + " Z"
            for ring in rings
        )
    domain_paths = "".join(f"<path d='{path_for(component, 20)}' fill='#dbeafe' fill-rule='evenodd' stroke='#334155'/>"
                           for component in _components(domain))
    source_paths = ""
    source_colors = {
        "furniture": ("#2563eb", "#dbeafe"),
        "physical_context": ("#15803d", "#dcfce7"),
        "proxy": ("#c2410c", "#ffedd5"),
        "unknown": ("#7c3aed", "none"),
    }
    source_display_counts = {"furniture": 0, "physical_context": 0, "proxy": 0}
    for record in source_layer:
        if record.get("display_category") == "accepted_proxy":
            category = "proxy"
        elif record.get("display_category") == "furniture":
            category = "furniture"
        else:
            category = "physical_context"
        source_display_counts[category] += 1
        stroke, fill = source_colors[category]
        source_paths += "".join(
            f"<path d='{path_for(component, 20)}' fill='{fill}' fill-opacity='.35' stroke='{stroke}'/>"
            for component in record.get("geometry_components", ())
        )
    cells_svg = []
    for sample in cells:
        row, col = sample["target"]
        x0, y0 = point(bounds[0] + col * SPACING_M, bounds[1] + row * SPACING_M, 520)
        x1, y1 = point(bounds[0] + (col + 1) * SPACING_M, bounds[1] + (row + 1) * SPACING_M, 520)
        state = sample["visual_state"]
        if state == "established":
            state = "established_occupied" if sample["value"] is True else "established_empty"
        cells_svg.append(f"<rect class='cell' data-index='{len(cells_svg)}' x='{x0:.2f}' y='{y1:.2f}' width='{x1-x0:.2f}' height='{y0-y1:.2f}' fill='{colors.get(state, '#fff')}'/>")
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 700'>"
        "<rect width='1000' height='700' fill='white'/><text x='20' y='28'>Sources</text>"
        "<text x='520' y='28'>Whole-height field cells</text>"
        "<rect x='20' y='45' width='450' height='600' fill='#eef2f7' stroke='#334155'/>"
        + domain_paths + source_paths + "<g>" + "".join(cells_svg) + "</g></svg>"
    )
    safe_json = json.dumps(payload, sort_keys=True).replace("</", "<\\/")
    html_text = (
        "<!doctype html><meta charset='utf-8'><title>Free-space field inspection</title>"
        "<style>.cell{cursor:pointer}.legend span{margin-right:1em}</style>"
        "<h1>Whole-height physical occupancy</h1><p>False is empty occupancy, not walkability.</p>"
        "<div class='legend'><span>established</span><span>conditional</span><span>unknown</span>"
        "<span>outside</span><span>invalid (unavailable)</span><span>not_available (unavailable)</span>"
        "<span>occupied</span><span>empty</span></div>"
        f"{svg}<pre id='details'>Select a field cell.</pre>"
        f"<script type='application/json' id='inspection'>{safe_json}</script>"
        "<script>const p=JSON.parse(document.getElementById('inspection').textContent);"
        "document.querySelectorAll('.cell').forEach(e=>e.onclick=()=>{"
        "const c=p.field_layer.samples[Number(e.dataset.index)];"
        "document.getElementById('details').textContent=JSON.stringify(c,null,2);});</script>"
    )
    payload["timings"]["serialization_ms"] = (time.perf_counter() - serialization_start) * 1000.0
    manifest_bytes = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    payload["sizes"] = {"json_bytes": len(manifest_bytes), "html_bytes": len(html_text.encode("utf-8"))}
    payload["_html"] = html_text
    return payload, field


def _reuse_projection(source: Path, output: Path) -> None:
    """Re-emit a validated projection handoff without invoking scene projection."""
    payload, _ = build_inspection(projected_handoff=source)
    payload["lineage"] = {
        "mode": "reuse_projection",
        "source_handoff": str(source.resolve()),
        "source_handoff_bytes": (source / "inspection_manifest.json").stat().st_size,
        "source_handoff_sha256": hashlib.sha256(
            (source / "inspection_manifest.json").read_bytes()
        ).hexdigest(),
        "projection_reused": True,
    }
    html_template = payload.pop("_html")
    sizes = _write_final_artifacts(output, payload, html_template)
    execution = {
        "status": "exit_0",
        "mode": "reuse_projection",
        "output": str(output.resolve()),
        "sizes": sizes,
        "manifest_sha256": hashlib.sha256(
            (output / "inspection_manifest.json").read_bytes()
        ).hexdigest(),
    }
    (output / "execution.json").write_bytes(json.dumps(execution, indent=2).encode("utf-8"))


def main() -> None:
    """Write one deterministic inspection package from authenticated frozen inputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-projection", type=Path)
    args = parser.parse_args()
    output = OUTPUT / (datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ_") + uuid4().hex[:6])
    output.mkdir(parents=True, exist_ok=False)
    if args.reuse_projection:
        _reuse_projection(args.reuse_projection, output)
        print(json.dumps({"status": "exit_0", "output": str(output.resolve()), "mode": "reuse_projection"}, indent=2))
        return
    payload, _ = build_inspection()
    html_text = payload.pop("_html")
    sizes = _write_final_artifacts(output, payload, html_text)
    execution = {
        "status": "exit_0",
        "output": str(output),
        "sizes": sizes,
        "manifest_sha256": hashlib.sha256((output / "inspection_manifest.json").read_bytes()).hexdigest(),
    }
    (output / "execution.json").write_bytes(json.dumps(execution, indent=2).encode("utf-8"))
    print(json.dumps(execution, indent=2))


if __name__ == "__main__":
    main()
