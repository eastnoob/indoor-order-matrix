"""Bind one exact saved free-space publication to the group-distance kernel."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, replace
from itertools import chain

from . import blender_analysis_result_wire as wire
from .bonsai_live import _mesh
from features.field_core import FieldQuery, _json_value, fingerprint_evidence_dependency
from features.geometry_substitutes import mass_patch_from_mesh
from features.geometry_views import plan_projection
from features.group_distance import (GridDescriptor, GroupDistanceInput, GroupProjection,
                                     group_distance_input_fingerprints)
from features.scene_contract import (AnalysisContext, AnalysisDomain, AnalysisPlane,
                                    MeshGeometry3D, NeutralSceneV2, NEUTRAL_SCENE_V2)


def _domain_meshes(capture, request, provenance, raw_meshes):
    """Authenticate exact domain mesh bytes using the producer's domain audit."""
    if (not raw_meshes or len({mesh["id"] for mesh in raw_meshes}) != len(raw_meshes)
            or {mesh["id"] for mesh in raw_meshes} != set(request["domain"]["geometry_refs"])):
        raise ValueError("retained native domain geometry refs differ from the result domain")
    identity = capture["identity"]
    plane = AnalysisPlane.from_dict(wire.plain(request["plane"]))
    context = AnalysisContext(contract_version=NEUTRAL_SCENE_V2, source_schema=identity.get("schema", "IFC"),
        adapter_version="bonsai-live/1", source_length_unit="m", analysis_length_unit="m",
        world_coordinate_system={"frame": "world", "project_global_id": identity["project_global_id"],
                                 "ifc_source_identity": identity["ifc_source_identity"]},
        level_references=(), analysis_plane=plane, geometry_tolerance=request["geometry_tolerance"],
        topology_tolerance=request["topology_tolerance"], walking_body_profiles=(), visual_height_bands=(),
        capability_flags={"has_3d_geometry": any(row.get("mesh") is not None for row in capture["records"])},
        input_mode="ifc")
    meshes = tuple(MeshGeometry3D.from_dict(mesh) for mesh in raw_meshes)
    projection = NeutralSceneV2(context=context, analysis_domain=AnalysisDomain.from_dict(wire.plain(request["domain"])),
                               geometries=meshes)
    if fingerprint_evidence_dependency(projection.to_dict()) != provenance["domain_handoff"]["source_revision"]:
        raise ValueError("retained native domain mesh bytes differ from the free-space domain audit")
    return meshes


def _group_projections(capture, authored_groups, plane):
    """Project only authored group members from the authenticated native capture."""
    by_id = defaultdict(list)
    for row in capture["records"]:
        by_id[row["id"]].append(row)
    projected, groups = {}, []
    for group in sorted(authored_groups, key=lambda item: item["id"]):
        if group["group_role"] != "furniture_group" or not group["member_refs"]:
            continue
        members = tuple(dict.fromkeys(group["member_refs"]))
        unresolved, missing, components = [], [], []
        for member in members:
            rows = by_id[member]
            if len(rows) != 1:
                unresolved.append(member)
                continue
            row = rows[0]
            if (row.get("binding_verified") is not True
                    or row.get("project_global_id") != capture["identity"]["project_global_id"]
                    or row.get("id") != "ifc-object:" + row.get("global_id", "")):
                raise ValueError("authored group member has an unverified native identity")
            if member not in projected:
                mesh = _mesh(row)
                projected[member] = (() if mesh is None else
                    plan_projection(mass_patch_from_mesh(mesh), plane).components)
            if not projected[member]:
                missing.append(member)
            components.extend(projected[member])
        status = "invalid" if unresolved else "not_available" if missing else "available"
        groups.append(GroupProjection(group["id"], components or None, members, status,
            "unresolved authored members" if unresolved else "missing member projection" if missing else ""))
    return tuple(groups)


def distance_input_from_free_space(snapshot, native_request):
    """Use exact saved samples; project only same-capture group/domain geometry.

    Callers open the ResultRef with independently supplied consumer expectations
    and explicit freshness policy. The native request is authenticated against
    the publication, so another capture cannot supply convenient group geometry.
    No free-space computation or Blender display data is read here.
    """
    if not isinstance(snapshot, wire.ReadOnlyResultSnapshot) or snapshot.ref.kind != "free_space_run":
        raise TypeError("an opened free-space result snapshot is required")
    document = snapshot.payload
    saved = document["tables"]["snapshot"]
    binding = document["binding"]
    if (native_request.get("kind") != "free_space_run"
            or not native_request.get("job_binding")
            or wire.plain(native_request.get("request")) != wire.plain(saved["request"])
            or any(key not in binding or wire.plain(value) != wire.plain(binding[key])
                   for key, value in native_request.get("job_binding", {}).items())):
        raise ValueError("retained native request does not match the exact free-space publication")
    capture = native_request["canonical_capture"]
    identity = capture["identity"]
    source = document["identity"]["project_source_identity"]
    if (capture.get("capture_complete") is not True
            or wire.document_digest(capture) != binding.get("capture_digest")
            or identity.get("project_global_id") != source.get("project_global_id")
            or identity.get("ifc_source_identity") != source.get("ifc_source_identity")
            or wire.plain(identity.get("authored_groups")) != wire.plain(binding.get("authored_groups"))):
        raise ValueError("retained native capture or authored groups differ from the free-space source")
    request = saved["request"]
    if request["geometry_query"]["kind"] not in {"whole_height_projection", "finite_height_band"}:
        raise ValueError("group distance requires a planar mass-projection result")
    plane = AnalysisPlane.from_dict(wire.plain(request["plane"]))
    meshes = _domain_meshes(capture, request, saved["provenance"], native_request["domain_geometries"])
    # These exact confirmed support meshes define the domain. Display fragments,
    # board meshes and colors cannot supply or repair its geometry.
    components = tuple(component for mesh in meshes for component in plan_projection(
        mass_patch_from_mesh(mesh), plane).components)
    samples = wire.iter_analysis_samples(snapshot)
    first = next(samples)
    query = FieldQuery(**wire.plain(first["query"]))
    analysis_plane = wire.plain(first["query"]["plane"])
    domain = {**wire.plain(request["domain"]), "frame": query.frame, "components": components,
              "confirmation_binding": wire.plain(binding["confirmation_binding"])}
    candidate = domain["provenance"].get("candidate_version_id", "").split(":")
    domain["selected_candidate_id"] = candidate[1] if len(candidate) > 1 else domain["id"]
    reference = asdict(snapshot.ref)
    source_identity = {**wire.plain(source), "capture_digest": binding["capture_digest"],
        "canonical_full_fingerprint": document["identity"]["canonical_full_fingerprint"],
        "canonical_structural_fingerprint": document["identity"]["canonical_structural_fingerprint"]}
    lattice = wire.plain(document["tables"]["lattice"])
    cells, source_ids, source_indices = [], [], {}
    shared_support_keys = {"frame", "geometry_query", "height_band", "lattice", "plane"}
    support_context = {key: value for key, value in (first["support"] or {}).items() if key in shared_support_keys}
    for index, sample in enumerate(chain((first,), samples)):
        if wire.plain(sample["query"]) != _json_value(query):
            raise ValueError("saved free-space cells do not share the exact frozen query")
        row, column = divmod(index, lattice["n_cols"])
        locator = f"free-space:{snapshot.ref.result_id}:{snapshot.ref.digest}:cell:{row}:{column}"
        # Known-empty samples can reference the complete source inventory. Keep
        # each exact list once, using the wire's existing integer-table pattern.
        wire_source_ref = wire.plain(document["cells"][index]["source_ids_ref"])
        source_key = wire.canonical_json(wire_source_ref)
        if source_key not in source_indices:
            source_indices[source_key] = len(source_ids)
            source_ids.append(sample["source_ids"])
        support = None
        if sample["support"] is not None:
            local = {key: value for key, value in sample["support"].items()
                     if key not in support_context or support_context[key] != value}
            support = {**local, "context_ref": "free_space_result.support_context",
                "removed_context_keys": tuple(key for key in support_context if key not in sample["support"]),
                "exact_sample_ref": locator}
        cells.append({"cell_key": (row, column), "query_ref": locator,
            "status": sample["status"], "value": sample["value"],
            "source_refs": {"table": "free_space_result.source_ids", "index": source_indices[source_key]},
            "wire_source_ids_ref": wire_source_ref, "support": support,
            "explanation": sample["explanation"], "provenance_ref": locator})
    context = {**_json_value(query), "geometry_query": wire.plain(request["geometry_query"]),
        "height_band_datum": wire.plain(request["height_band_datum"]),
        "algorithm_version": saved["provenance"]["algorithm_version"],
        "schema_version": saved["provenance"]["schema_version"], "result_ref": reference}
    exact = {"kind": "exact_free_space_samples/1", "result_ref": reference,
        "freshness": snapshot.freshness, "identity": wire.plain(document["identity"]),
        "backend_versions": wire.plain(document["backend_versions"]),
        "content_cache": wire.plain(document.get("content_cache")),
        "calculation_provenance": wire.plain(saved["provenance"]),
        "source_identity": source_identity, "analysis_plane": analysis_plane,
        "domain": domain, "lattice": lattice, "query": _json_value(query), "cells": cells,
        "source_ids": source_ids, "support_context": support_context}
    grid = GridDescriptor(f"free-space:{snapshot.ref.result_id}:{snapshot.ref.digest}",
        query.frame, tuple(lattice["origin"]), lattice["spacing"], lattice["n_rows"], lattice["n_cols"])
    bundle = GroupDistanceInput(source_identity, analysis_plane, domain, grid,
        _group_projections(capture, binding["authored_groups"], plane),
        saved["provenance"]["selected_records"], tuple(saved["provenance"]["unknown_source_ids"]),
        saved["provenance"]["trusted_unknown_supports"], query, context, (0, 0), {}, exact)
    fingerprints = group_distance_input_fingerprints(bundle)
    bundle = replace(bundle, query_context={**context, "analysis_plane_fingerprint": fingerprints["analysis_plane"]},
        grid=replace(grid, domain_fingerprint=fingerprints["domain"], occupancy_fingerprint=fingerprints["occupancy"]))
    return replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
