"""Enroll frozen B3 meshes through shared physical occupancy section accounting."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import sys

import trimesh
from shapely.geometry import MultiPoint, mapping, shape

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from features.discrete_space_field import load_discrete_space_field
from features.geometry_substitutes import mass_patch_from_mesh
from features.neutral_scene_views import _resolved_physical_occupancy
from features.scene_contract import (AnalysisContext, AnalysisDomain, AnalysisPlane,
                                     MeshGeometry3D, NeutralSceneV2, SourceObject, UncertaintyRecord, _json_value)
from features.section_views import SECTION_ALGORITHM, exact_plane_section, polygonal_union
from scripts.design.space_field import run_b3_eye_plane_field as EYE
from scripts.design.space_field import run_b3_proxy_eye_plane_comparison as COMP

PRIOR = EYE.PRIOR
CAPTURE = PRIOR.CAPTURE
BINDINGS = ROOT / "docs/project/evidence/b3-physical-occupancy-bindings.json"
ACCEPTED = ROOT / "outputs/design/b3_occupancy_only_handoff/run_20261009T091601Z_242b33"
OUTPUT = ROOT / "outputs/design/b3_shared_occupancy_enrollment"
QUERY = {"frame": "world_xy", "units": "m", "world_z_m": 1.6}


def verified_ref(ref):
    """Read a pinned repository input only when its current bytes still match."""
    path = ROOT / ref["path"]
    actual = PRIOR.file_ref(path)
    if (actual["bytes"], actual["sha256"]) != (ref["bytes"], ref["sha256"]):
        raise ValueError(f"frozen_input_fingerprint_mismatch:{ref['path']}")
    return path


def frozen_inputs():
    """Bind this run to explicit target, scope, capture, and historical section facts."""
    bindings = PRIOR.read_json(BINDINGS)
    if (bindings.get("schema") != "b3-physical-occupancy-bindings/v1"
            or bindings.get("consumer") != "physical_occupancy"
            or bindings.get("primary_plane_world_z_m") != QUERY["world_z_m"]):
        raise ValueError("invalid_b3_binding_declaration")
    pinned = {Path(ref["path"]).name: verified_ref(ref) for ref in bindings["frozen_input_refs"]}
    load_discrete_space_field(ACCEPTED, spacing_m=.25, origin_offset_m=(0., 0.))
    accepted = PRIOR.read_json(ACCEPTED / "field_samples.json")
    originals = PRIOR.read_json(pinned["source_sections.json"])["records"]
    capture = PRIOR.read_json(pinned["capture_manifest.json"])
    scope = PRIOR.read_json(pinned["s3_scope.json"])
    declaration = PRIOR.read_json(pinned["b3-domain-boundary-membership.json"])
    proxy_metadata = PRIOR.read_json(COMP.PROXIES / "mesh_proxies.json")
    accepted_rows = PRIOR.read_json(ACCEPTED / "source_sections.json")["records"]
    if (PRIOR.file_ref(COMP.PROXIES / "mesh_proxies.json")["sha256"] != bindings["proxy_metadata_sha256"]
            or accepted["scope_binding"] != bindings["scope_binding"]
            or accepted["scope_binding"] != declaration["scope_binding"]
            or len(originals) != len(capture["inventory"])
            or originals != accepted_rows[:len(originals)]
            or scope["candidate"]["outline"] != accepted["domain_geometry"]
            or [row["id"] for row in originals] != [row["id"] for row in capture["inventory"]]):
        raise ValueError("b3_scope_inventory_or_proxy_metadata_mismatch")
    baseline = PRIOR.read_json(verified_ref(accepted["baseline_field_ref"]))
    boundary, diagnostics = COMP.boundary_membership(baseline, {"records": originals}, declaration)
    groups = {"proxy:" + group["id"]: group for group in proxy_metadata["groups"]}
    targets = bindings["targets"]
    if (len(groups) != len(targets) or {item["target_id"] for item in targets} != set(groups)
            or len({sid for item in targets for sid in item["represented_source_ids"]})
            != sum(len(item["represented_source_ids"]) for item in targets)):
        raise ValueError("b3_target_identity_or_coverage_mismatch")
    return bindings, accepted, originals, capture, scope, declaration, boundary, diagnostics, groups


def transport_scene(bindings, capture, scope, originals, boundary, groups):
    """Transport all frozen products and actual meshes without resectioning originals."""
    owner_binding = {}
    for target in bindings["targets"]:
        group = groups[target["target_id"]]
        expected = ["live-step-" + str(item["step_id"]) for item in group["sources"]]
        if (target["represented_source_ids"] != expected
                or target["proxy_role"] != group["proxy_role"]
                or target["generated_mesh_checks"] != group["generated_mesh_checks"]):
            raise ValueError("b3_target_source_or_mesh_checks_mismatch")
        verified_ref(target["obj_ref"])
        for source_id in expected:
            owner_binding[source_id] = {
                "consumer": "physical_occupancy", "source_object_id": source_id,
                "substitute_id": target["target_id"], "substitute_kind": "MassPatch",
                "analysis_role": "physical_occupancy_substitute",
                "representation_identifier": "GeneratedProxy",
                "provenance": {"representation_identifier": "GeneratedProxy",
                               "binding_declaration_sha256": PRIOR.file_ref(BINDINGS)["sha256"],
                               "scope_binding": bindings["scope_binding"]},
            }
    sources, meshes, mesh_refs, nonmass = [], [], [], []
    original_by_id = {row["id"]: row for row in originals}
    for row in capture["inventory"]:
        source_id = row["id"]
        frozen = original_by_id[source_id]
        geometry_ref = row.get("geometry")
        if (frozen["global_id"] != row["global_id"] or frozen["geometry"] != geometry_ref
                or frozen["ifc_class"] != row["ifc_class"]):
            raise ValueError(f"frozen_section_capture_binding_mismatch:{source_id}")
        uncertainties = ()
        if geometry_ref is None:
            uncertainties = (UncertaintyRecord(code="missing_geometry", message="No actual Body capture was transported",
                                               source_refs=(source_id,), operation="transport", severity="warning"),)
            nonmass.append(source_id)
            if frozen["status"] != "excluded_semantic_nonmass":
                raise ValueError("nonmass_source_status_mismatch")
        else:
            path = CAPTURE / geometry_ref["path"]
            actual = PRIOR.file_ref(path)
            if (actual["bytes"], actual["sha256"]) != (geometry_ref["bytes"], geometry_ref["sha256"]):
                raise ValueError(f"capture_mesh_fingerprint_mismatch:{source_id}")
            mesh = PRIOR.read_json(path)
            if (mesh["id"] != source_id or mesh["units"] != "m" or mesh["transform_applied"] is not True
                    or row["loaded_representation"]["identifier"] != "Body"):
                raise ValueError(f"capture_mesh_identity_or_frame_mismatch:{source_id}")
            mesh_id = "capture-mesh:" + source_id
            meshes.append(MeshGeometry3D(
                id=mesh_id, vertices=mesh["vertices"], triangle_indices=mesh["triangles"], normals=(),
                is_manifold=mesh["is_manifold"], is_closed=mesh["is_closed"], units="m",
                source_representation_id=mesh["representation_id"],
                tessellation_settings=mesh["tessellation_settings"],
                local_to_world_provenance={"world_transform_applied": True,
                                           "capture_world_transform": mesh["world_transform"],
                                           "policy": capture["world_transform_policy"], "mesh_ref": geometry_ref},
            ))
            mesh_refs.append({"source_object_id": source_id, "geometry_id": mesh_id,
                              "mesh_ref": actual, "vertex_count": len(mesh["vertices"]),
                              "triangle_count": len(mesh["triangles"])})
        facts = {"frozen_capture_record": row, "frozen_section_status": frozen["status"],
                 "declared_representations": row["declared_representations"]}
        if source_id in owner_binding:
            target = next(item for item in bindings["targets"] if item["target_id"] == owner_binding[source_id]["substitute_id"])
            if (row["global_id"] != target["owner_global_ids"][source_id]
                    or geometry_ref["sha256"] != target["owner_capture_sha256"][source_id]):
                raise ValueError(f"owner_identity_or_capture_mismatch:{source_id}")
            facts["OM_FunctionSubstitutes"] = [owner_binding[source_id]]
            facts["furniture_analysis_participation"] = "excluded"
        sources.append(SourceObject(
            id=source_id, source_id=row["global_id"], source_role=row["function"] or row["ifc_class"],
            source_class=row["ifc_class"], geometry_refs=("capture-mesh:" + source_id,) if geometry_ref else (),
            factual_properties=facts,
            provenance={"capture_mesh_ref": geometry_ref, "capture_manifest_ref": PRIOR.file_ref(CAPTURE / "capture_manifest.json"),
                        "world_transform_policy": capture["world_transform_policy"]},
            uncertainties=uncertainties,
        ))
    proxy_sections = []
    for target in bindings["targets"]:
        group = groups[target["target_id"]]
        obj = verified_ref(target["obj_ref"])
        scene = trimesh.load_scene(obj, file_type="obj", process=False, maintain_order=True,
                                   group_material=False, skip_materials=True)
        if len(scene.geometry) != 1:
            raise ValueError("proxy_obj_geometry_count_mismatch")
        mesh = next(iter(scene.geometry.values()))
        checks = target["generated_mesh_checks"]
        if (len(mesh.vertices) != checks["vertex_count"] or len(mesh.faces) != checks["triangle_count"]
                or bool(mesh.is_watertight) is not True):
            raise ValueError("proxy_obj_mesh_checks_mismatch")
        transported = MeshGeometry3D(
            id=target["mesh_id"], vertices=mesh.vertices.tolist(), triangle_indices=mesh.faces.tolist(), normals=(),
            is_manifold=bool(mesh.is_watertight), is_closed=bool(mesh.is_watertight), units="m",
            source_representation_id="GeneratedProxy", tessellation_settings={"method": "accepted_obj_process_false"},
            local_to_world_provenance={"world_transform_applied": True, "obj_ref": target["obj_ref"]},
        )
        meshes.append(transported)
        sources.append(SourceObject(
            id=target["target_id"], source_role="analysis_substitute", geometry_refs=(target["mesh_id"],),
            factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": target["represented_source_ids"]},
                                "furniture_analysis_participation": "excluded"},
            provenance={"representation_identifier": "GeneratedProxy", "obj_ref": target["obj_ref"],
                        "approximation_limit": "Convex hull fills gaps and concavities; original material is not certified"},
        ))
        section = exact_plane_section(mass_patch_from_mesh(transported), world_z_m=QUERY["world_z_m"])
        proxy_sections.append({**section, "id": target["target_id"],
                               "represented_source_ids": target["represented_source_ids"],
                               "physical_occupancy_participation": "active_substitute",
                               "furniture_analysis_participation": "excluded",
                               "proxy_obj_ref": target["obj_ref"],
                               "approximation_limit": "Convex hull fills gaps and concavities; original material is not certified"})
    context = AnalysisContext(
        contract_version="neutral-scene-v2", source_schema="IFC4", adapter_version="b3-frozen-capture-v1",
        source_length_unit="mm", analysis_length_unit="m", world_coordinate_system={"frame": "world_xy", "units": "m"},
        level_references=(), analysis_plane=AnalysisPlane(name="world_xy_z_1_6", origin=(0, 0, 1.6),
                                                           basis=((1, 0, 0), (0, 1, 0), (0, 0, 1))),
        geometry_tolerance=1e-9, topology_tolerance=1e-9, walking_body_profiles=(), visual_height_bands=(),
        capability_flags={"physical_planar_occupancy": False}, input_mode="blender_geometry",
    )
    domain = AnalysisDomain(id="b3-selected-s3", geometry_refs=(), source_id=None,
                            selection_method="frozen_explicit_selected_scope",
                            provenance={"outline": scope["candidate"]["outline"],
                                        "boundary_member_source_ids": sorted(boundary),
                                        "scope_binding": bindings["scope_binding"]})
    neutral = NeutralSceneV2(context=context, analysis_domain=domain,
                             source_objects=tuple(sources), geometries=tuple(meshes))
    return neutral, proxy_sections, {"original_source_count": len(capture["inventory"]),
                                     "capture_body_mesh_count": len(mesh_refs), "proxy_mesh_count": len(proxy_sections),
                                     "semantic_nonmass_ids": nonmass, "capture_mesh_refs": mesh_refs,
                                     "context": context.to_dict(), "analysis_domain": domain.to_dict(),
                                     "source_objects": [source.to_dict() for source in sources],
                                     "proxy_meshes": [mesh.to_dict() for mesh in meshes[-len(proxy_sections):]],
                                     "binding_declaration_ref": PRIOR.file_ref(BINDINGS),
                                     "frozen_original_section_ref": PRIOR.file_ref(COMP.BASE / "source_sections.json"),
                                     "query": QUERY, "section_algorithm": SECTION_ALGORITHM,
                                     "historical_proxy_metadata_ref": PRIOR.file_ref(COMP.PROXIES / "mesh_proxies.json"),
                                     "geometry_storage": "Actual capture arrays transported in memory; immutable mesh refs retained without duplicating arrays",
                                     "not_rebound": True}


def enroll_field(scene, original_sections, proxy_sections, accepted, boundary, declaration, diagnostics):
    """Select shared records once, then derive raw occupancy and localized unknown masks."""
    section_records = []
    proxy_ids = {row["id"] for row in proxy_sections}
    for row in [*original_sections, *proxy_sections]:
        source = next(item for item in scene.source_objects if item.id == row["id"])
        if not source.geometry_refs:
            continue
        section_records.append({"id": source.id, "section": row,
                                "section_evidence": {"source_object_id": source.id,
                                                     "geometry_refs": list(source.geometry_refs),
                                                     "query": QUERY, "algorithm": SECTION_ALGORITHM}})
    scoped = {row["id"]: "semantic_nonmass" if row["status"] == "excluded_semantic_nonmass"
              else "historical_support_slab" for row in original_sections
              if row["status"] in {"excluded_semantic_nonmass", "excluded_support_slab"}}
    selected, unknown_ids, inventory = _resolved_physical_occupancy(
        scene, section_records, set(boundary), operation="physical_occupancy_section", query=QUERY,
        scoped_out_reasons=scoped)
    represented = {owner for proxy in proxy_sections for owner in proxy["represented_source_ids"]}
    if (len(selected) != len({row["id"] for row in selected})
            or {row["id"] for row in selected} & represented):
        raise ValueError("duplicate_or_covered_original_selection")
    domain = shape(accepted["domain_geometry"])
    positives = [shape(row["section"]["occupied_geometry"]) for row in selected]
    raw_audit, support_audit = {}, {}
    raw = polygonal_union(positives, raw_audit)
    by_id = {row["id"]: row for row in original_sections}
    supports = unresolved_supports(scene, unknown_ids, by_id)
    supports = [(source_id, support) for source_id, support in supports if support is None or not support.is_empty]
    unknown = polygonal_union([domain if support is None else support for _, support in supports], support_audit)
    boundaries = [part.boundary for part in positives if not part.is_empty]
    variants = [EYE.sample_variant(domain, raw, supports, boundaries, variant["spacing_m"],
                                   tuple(variant["origin_offset_m"])) for variant in accepted["variants"]]
    overrides = [{"source_id": source_id, "proxy_id": row["id"],
                  "original_status": by_id[source_id]["status"], "scenario_uncertainty_omitted": source_id not in unknown_ids,
                  "reason": "shared required physical substitute selected once"}
                 for row in proxy_sections for source_id in row["represented_source_ids"]]
    field = {**accepted, "status": "design_only_shared_occupancy_enrollment_owner_review_required",
             "algorithm": {**accepted["algorithm"],
                           "identity": "Shared physical_occupancy_section resolver selects MassPatch owners once; original sections frozen, three proxy meshes newly sectioned",
                           "endpoint_policy": "Original indexed-edge sections frozen; three proxy meshes sectioned without weld, snap, or repair",
                           "probe_policy": "Historical original probes retained; current proxy qualification runs indexed-edge and shell parity audits",
                           "qualification": "Frozen original sections bound to verified capture hashes; proxy sections qualified by current pure exact-plane helper",
                           "limit": "Convex proxy approximation and remaining unknown support prevent complete occupancy or clearance"},
             "source_integrity": {"current_run": "Pinned frozen hashes and actual 354 Body transports verified",
                                  "historical_accepted_integrity": accepted["source_integrity"]},
             "source_counts": dict(Counter(row["status"] for row in [*original_sections, *proxy_sections])),
             "original_source_record_count": len(original_sections), "proxy_record_count": len(proxy_sections),
             "scenario_overrides": overrides,
             "domain_boundary_policy": {**accepted["domain_boundary_policy"],
                                        "scope_binding": declaration["scope_binding"],
                                        "resolved_record_ids": sorted(boundary), "identity_diagnostics": diagnostics},
             "raw_qualified_occupied_geometry": mapping(raw),
             "clipped_qualified_occupied_geometry": mapping(raw.intersection(domain)),
             "raw_qualified_occupied_area_m2": raw.area,
             "clipped_qualified_occupied_area_m2": raw.intersection(domain).area,
             "raw_unknown_support_geometry": mapping(unknown),
             "clipped_unknown_support_geometry": mapping(unknown.intersection(domain)),
             "clipped_unknown_support_area_m2": unknown.intersection(domain).area,
             "qualified_occupied_union_audit": raw_audit, "unknown_support_union_audit": support_audit,
             "complete_occupancy_geometry": None,
             "channel_contract": {**accepted["channel_contract"],
                                  "unknown_propagation": "Required target failure propagates to every represented owner; exact boundary scoped out",
                                  "distance_to_raw_qualified_occupied_subset_m": "Unsigned metres to raw selected positive subset; incomplete, not clearance"},
             "occupancy_only_policy": {**accepted["occupancy_only_policy"],
                                       "shared_operation": "physical_occupancy_section",
                                       "binding_declaration_ref": PRIOR.file_ref(BINDINGS)},
             "sources": [*accepted["sources"], PRIOR.file_ref(BINDINGS),
                         PRIOR.file_ref(CAPTURE / "capture_manifest.json")],
             "code": [PRIOR.file_ref(ROOT / path) for path in (
                 "features/analysis_substitute_discovery.py", "features/neutral_scene_views.py",
                 "features/section_views.py", "features/geometry_substitutes.py",
                 "features/geometry_views.py", "features/scene_contract.py", "features/substitute_contract.py",
                 "features/discrete_space_field.py", "scripts/design/space_field/run_b3_eye_plane_field.py",
                 "scripts/design/space_field/run_b3_real_field_diagnostic.py",
                 "scripts/design/space_field/run_b3_space_field_exploratory.py",
                 "scripts/design/group_level/trend_substitute_registry.json",
                 "scripts/design/space_field/run_b3_shared_occupancy_enrollment.py")],
             "variants": variants}
    field["historical_code_provenance"] = accepted["code"]
    selected_ids = {row["id"] for row in selected}
    audit = {"schema": "b3-shared-occupancy-selection/v1", "operation": "physical_occupancy_section",
             "query": QUERY, "selected_source_ids": sorted(selected_ids), "unknown_source_ids": unknown_ids,
             "source_ledger": inventory, "semantic_scoped_ids": sorted(scoped),
             "boundary_scoped_ids": sorted(boundary), "proxy_target_ids": sorted(proxy_ids),
             "remaining_active_unknown_source_ids": unknown_ids,
             "raw_occupied_area_m2": raw.area, "clipped_occupied_area_m2": raw.intersection(domain).area,
             "clipped_unknown_support_area_m2": unknown.intersection(domain).area}
    return field, _json_value(audit, "selection_audit")


def unresolved_supports(scene, unknown_ids, original_by_id):
    """Localize failed targets over complete owner/target footprints, never empty evidence."""
    sources = {source.id: source for source in scene.source_objects}
    meshes = {mesh.id: mesh for mesh in scene.geometries}
    supports = []
    for source_id in unknown_ids:
        source = sources[source_id]
        bindings = source.factual_properties.get("OM_FunctionSubstitutes", ())
        physical = [binding for binding in bindings if binding.get("consumer") == "physical_occupancy"]
        target_ids = {binding.get("substitute_id") for binding in physical}
        target_ids.update(target.id for target in sources.values()
                          if source_id in target.factual_properties.get("OM_PhysicalOccupancy", {}).get("represented_source_ids", ()))
        if not target_ids:
            raw = original_by_id[source_id].get("unknown_support_geometry")
            supports.append((source_id, None if raw is None else shape(raw)))
            continue
        related = {source_id}
        missing_target = False
        for target_id in target_ids:
            target = sources.get(target_id)
            if target is not None:
                related.add(target.id)
                related.update(target.factual_properties.get("OM_PhysicalOccupancy", {}).get("represented_source_ids", ()))
                related.update(owner.id for owner in sources.values() if any(
                    binding.get("consumer") == "physical_occupancy" and binding.get("substitute_id") == target_id
                    for binding in owner.factual_properties.get("OM_FunctionSubstitutes", ())))
            else:
                missing_target = True
        # A footprint bounds possible missing mass; it is never promoted to positive occupancy.
        if missing_target or any(owner not in sources or not sources[owner].geometry_refs
               or any(ref not in meshes for ref in sources[owner].geometry_refs) for owner in related):
            support = None
        else:
            points = [vertex[:2] for owner in related for ref in sources[owner].geometry_refs
                      for vertex in meshes[ref].vertices]
            support = MultiPoint(points).convex_hull if points else None
            if support is not None and (support.is_empty or support.area == 0):
                support = None
        supports.append((source_id, support))
    return supports


def compare_accepted(field, accepted, original_sections, *, accepted_original_sections):
    """Check all 9,648 sample fields and frozen original rows against accepted evidence."""
    comparisons = 0
    mismatches = []
    if (len(original_sections) != field["original_source_record_count"]
            or original_sections != accepted_original_sections):
        raise ValueError("frozen_original_rows_mismatch")
    if len(accepted["variants"]) != len(field["variants"]):
        raise ValueError("sample_variant_count_mismatch")
    for variant_index, (before, after) in enumerate(zip(accepted["variants"], field["variants"])):
        if len(before["samples"]) != len(after["samples"]):
            raise ValueError("sample_lattice_length_mismatch")
        if {key: value for key, value in before.items() if key != "samples"} != {
                key: value for key, value in after.items() if key != "samples"}:
            raise ValueError("sample_variant_metadata_mismatch")
        for sample_index, (left, right) in enumerate(zip(before["samples"], after["samples"])):
            comparisons += 1
            for key in left.keys() | right.keys():
                if key not in left or key not in right or left[key] != right[key]:
                    mismatches.append({"variant": variant_index, "sample": sample_index, "field": key,
                                       "accepted": left.get(key), "current": right.get(key)})
                    if len(mismatches) >= 20:
                        raise ValueError(f"sample_field_mismatch:{mismatches}")
    if mismatches:
        raise ValueError(f"sample_field_mismatch:{mismatches}")
    area_keys = ("domain_area_m2", "raw_qualified_occupied_area_m2", "clipped_qualified_occupied_area_m2",
                 "clipped_unknown_support_area_m2")
    areas = {key: {"accepted": accepted[key], "current": field[key],
                   "delta": field[key] - accepted[key]} for key in area_keys}
    if any(abs(item["delta"]) > 1e-9 for item in areas.values()):
        raise ValueError(f"accepted_area_mismatch:{areas}")
    return {"schema": "b3-shared-occupancy-comparison/v1", "sample_count": comparisons,
            "sample_fields_compared": sorted(accepted["variants"][0]["samples"][0]),
            "sample_mismatches": mismatches, "area_comparison": areas,
            "frozen_original_rows_identical": True,
            "conditional_free_area_m2": shape(field["domain_geometry"]).difference(
                shape(field["clipped_qualified_occupied_geometry"])).difference(
                shape(field["clipped_unknown_support_geometry"])).area}


def main():
    """Write one unique A-loadable package and a full shared-accounting comparison."""
    out = OUTPUT / (datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ_") + uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    execution = {"status": "running", "output": str(out)}
    try:
        (bindings, accepted, originals, capture, scope, declaration,
         boundary, diagnostics, groups) = frozen_inputs()
        scene, proxies, transport = transport_scene(bindings, capture, scope, originals, boundary, groups)
        field, selection = enroll_field(scene, originals, proxies, accepted, boundary, declaration, diagnostics)
        accepted_rows = PRIOR.read_json(ACCEPTED / "source_sections.json")["records"][:len(originals)]
        comparison = compare_accepted(field, accepted, originals, accepted_original_sections=accepted_rows)
        if (transport["original_source_count"] != 358 or transport["capture_body_mesh_count"] != 354
                or transport["proxy_mesh_count"] != 3 or comparison["sample_count"] != 9648
                or selection["remaining_active_unknown_source_ids"] != [
                    "live-step-43654", "live-step-49645", "live-step-55636", "live-step-61627", "live-step-67618"]):
            raise ValueError("b3_acceptance_accounting_mismatch")
        PRIOR.write_json(out / "source_sections.json", {"schema": "b3-primary-eye-source-sections/v1",
                                                       "primary_plane_world_z_m": QUERY["world_z_m"],
                                                       "records": [*originals, *proxies]})
        written_rows = PRIOR.read_json(out / "source_sections.json")["records"]
        if written_rows[:len(originals)] != accepted_rows:
            raise ValueError("written_frozen_original_rows_mismatch")
        comparison["written_frozen_original_rows_identical"] = True
        field["source_sections"] = PRIOR.file_ref(out / "source_sections.json")
        PRIOR.write_json(out / "field_samples.json", field)
        PRIOR.write_json(out / "selection_audit.json", selection)
        PRIOR.write_json(out / "comparison_audit.json", comparison)
        PRIOR.write_json(out / "transport_audit.json", transport)
        execution.update(status="exit_0", source_count=transport["original_source_count"],
                         capture_mesh_count=transport["capture_body_mesh_count"], proxy_mesh_count=transport["proxy_mesh_count"],
                         semantic_nonmass_count=len(transport["semantic_nonmass_ids"]),
                         boundary_scoped_ids=selection["boundary_scoped_ids"],
                         unknown_source_ids=selection["unknown_source_ids"],
                         selected_record_count=len(selection["selected_source_ids"]),
                         sample_count=comparison["sample_count"], sample_mismatches=comparison["sample_mismatches"],
                         area_comparison=comparison["area_comparison"],
                         conditional_free_area_m2=comparison["conditional_free_area_m2"],
                         complete_physical_clearance_m=None)
    except Exception as error:
        execution.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        PRIOR.write_json(out / "execution.json", execution)
        PRIOR.write_json(out / "artifact_manifest.json", {
            "schema": "b3-primary-eye-artifacts/v1", "status": execution["status"],
            "artifacts": [PRIOR.file_ref(path) for path in out.iterdir() if path.is_file()],
            "execution": execution, "binding_declaration_ref": PRIOR.file_ref(BINDINGS)})
        print(json.dumps(execution, indent=2), flush=True)
    for variant in field["variants"]:
        load_discrete_space_field(out, spacing_m=variant["spacing_m"],
                                  origin_offset_m=tuple(variant["origin_offset_m"]))


if __name__ == "__main__":
    main()
