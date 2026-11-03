"""Run the complete distance scope from the pinned IFC's confirmed camera capture."""

from __future__ import annotations

import argparse
from collections import Counter
import ctypes
from dataclasses import asdict, replace
import gc
import hashlib
import json
import math
from pathlib import Path
import time

from shapely.geometry import LineString, Point, shape

from adapters.blender_analysis_capture import CanonicalCaptureInput, digest, plain
from adapters.bonsai_live import load_bonsai_capture
from features._analysis_domain_handoff import structural_source_facts
from features._authored_group_inventory import _build_authored_group_inventory
from features.field_core import FieldQuery, _json_value
from features.geometry_views import component_shape, plan_projection
from features.geometry_substitutes import mass_patch_from_mesh
from features.group_distance import (
    GridDescriptor, GroupDistanceInput, GroupProjection,
    calculate_group_pair_distances, group_distance_input_fingerprints,
    serialize_group_distance_result,
)
from features.neutral_scene_views import _resolve_boundary_member_ids, analysis_scene_view
from features.scene_contract import AnalysisDomain, AnalysisPlane, MeshGeometry3D

PINNED_SOURCE = Path("D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc")
PINNED_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
PINNED_BYTES = 408618044
STATES = {"computed", "partial", "outside", "invalid", "not_available", "unknown", "unreachable"}


def read_json(path: Path) -> dict:
    """Read retained UTF-8 JSON without importing a failed domain attempt."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    """Write strict JSON so missing readings remain null and NaN cannot escape."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    """Stream a file fingerprint without retaining source bytes in memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_identity(path: Path) -> dict:
    """Require the exact authorized IFC path and unchanged bytes."""
    if path.resolve() != PINNED_SOURCE.resolve():
        raise ValueError("this diagnostic accepts only the pinned IFC path")
    result = {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": file_hash(path)}
    if result["bytes"] != PINNED_BYTES or result["sha256"] != PINNED_SHA256:
        raise ValueError("pinned IFC byte count or SHA-256 differs")
    return result


def process_memory() -> dict:
    """Read actual process working-set peaks, including native allocations, on Windows."""
    class Counters(ctypes.Structure):
        """Match PROCESS_MEMORY_COUNTERS in the Windows process API."""
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
             "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
             "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    api = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    api.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    if not api(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"working_set_bytes": counters.WorkingSetSize,
            "peak_working_set_bytes": counters.PeakWorkingSetSize,
            "peak_commit_bytes": counters.PeakPagefileUsage,
            "scope": "current Python process lifetime; includes native allocations"}


def confirmed_domain(s4_dir: Path, source: dict, *, expected_candidate: str | None = None) -> tuple[dict, dict]:
    """Cross-check the active confirmation, candidate, source, request and mesh binding."""
    names = confirmation_names(s4_dir)
    manifest = read_json(s4_dir / names[0])
    result = read_json(s4_dir / names[1])
    binding, domain = result["confirmation_binding"], result["analysis_domain"]
    if not (manifest["status"] == "confirmed" and result["status"] == "active"
            and result["handoff_executed"] is True and manifest["selected_candidate_id"] == result["selected_candidate_id"]
            and (expected_candidate is None or result["selected_candidate_id"] == expected_candidate)
            and manifest["confirmed_domain"] == domain and manifest["confirmation_binding"] == binding
            and result["domain_request_identity"] == binding["request_id"]
            and result["session_state"]["current_binding"] == binding
            and result["current"]["status"] == "active"):
        raise ValueError("domain confirmation is not the active bound handoff")
    if manifest["source"]["sha256"] != source["sha256"] or manifest["source"]["bytes"] != source["bytes"] or Path(manifest["source"]["path"]).resolve() != Path(source["path"]).resolve():
        raise ValueError("confirmed domain belongs to another IFC source")
    provenance = domain["provenance"]
    if (provenance["candidate_version_id"] != manifest["selected_candidate_version_id"]
            or result["current"]["candidate_version_id"] != manifest["selected_candidate_version_id"]
            or provenance["source_revision"] != binding["source_revision"]
            or provenance["request_id"] != binding["request_id"]
            or domain["geometry_refs"] != [record["id"] for record in result["domain_geometries"]]
            or any(result["provenance"][key] != binding[key] for key in ("source_revision", "frame_id", "request_id"))):
        raise ValueError("candidate/domain/request/source revision binding differs")
    plane = AnalysisPlane.from_dict(manifest["analysis_plane"])
    if tuple(manifest["camera"]["origin"]) != plane.origin or tuple(map(tuple, manifest["camera"]["basis"])) != plane.basis:
        raise ValueError("confirmed camera and analysis plane differ")
    for mesh in result["domain_geometries"]:
        audit = mesh["local_to_world_provenance"]
        if audit.get("source_revision") != binding["source_revision"] or audit.get("request_id") != binding["request_id"]:
            raise ValueError("confirmed domain mesh has another source/request")
    candidates = [item for item in result["candidates"] if item["version_id"] == manifest["selected_candidate_version_id"]]
    scope = shape(result["scope_polygon"])
    if (len(candidates) != 1 or candidates[0]["id"] != result["selected_candidate_id"]
            or candidates[0]["status"] != "confirmed" or candidates[0]["identity"] != binding["candidate_identity"]
            or not shape(candidates[0]["outline"]).equals(scope)):
        raise ValueError("confirmed candidate identity or exact scope differs")
    # Reproject only the small confirmed support mesh, never the captured furniture.
    from shapely.ops import unary_union
    projected = unary_union([component_shape(plan_projection(mass_patch_from_mesh(
        MeshGeometry3D.from_dict(mesh)), plane).components) for mesh in result["domain_geometries"]])
    if projected.symmetric_difference(scope).area > 1e-8:
        raise ValueError("confirmed support mesh differs from the selected scope")
    return manifest, result


def confirmation_names(directory: Path) -> tuple[str, str]:
    """Prefer generic corrected-domain artifacts while retaining the published S4 contract."""
    return (("confirmed_domain_manifest.json", "confirmed_domain_result.json")
            if (directory / "confirmed_domain_manifest.json").exists()
            else ("s4_confirmed_manifest.json", "s4_confirm_result.json"))


def confirmed_s4(s4_dir: Path, source: dict) -> tuple[dict, dict]:
    """Validate the historical explicit S4 package through the generic binding guard."""
    return confirmed_domain(s4_dir, source, expected_candidate="S4")


def domain_candidate_id(domain: dict) -> str:
    """Read a recorded candidate identity, including historical inferred provenance."""
    return domain.get("selected_candidate_id") or domain["provenance"]["candidate_version_id"].split(":", 2)[1]


def shift_components(components: object, offset: tuple) -> list:
    """Apply the analysis view's one translation to its already projected rings."""
    return [{"exterior": [[x + offset[0], y + offset[1]] for x, y in item["exterior"]],
             "holes": [[[x + offset[0], y + offset[1]] for x, y in ring] for ring in item.get("holes", ())]}
            for item in components]


def build_input(s4_dir: Path, source: dict, spacing: float) -> tuple[GroupDistanceInput, dict]:
    """Resolve one capture scene and one planar view for every distance dependency."""
    manifest, confirmed = confirmed_domain(s4_dir, source)
    plane = AnalysisPlane.from_dict(manifest["analysis_plane"])
    print("Loading retained canonical capture", flush=True)
    capture_path = Path(manifest.get("retained_capture_path", s4_dir / "canonical_capture.json"))
    retained = read_json(capture_path)
    if retained["analysis_plane"] != manifest["analysis_plane"] or retained["source_fingerprint"] != manifest["source"]:
        raise ValueError("retained capture wrapper has another camera plane or IFC source")
    capture = CanonicalCaptureInput(**retained["capture"])
    del retained
    if Path(capture.ifc_identity).resolve() != Path(source["path"]).resolve() or capture.project_global_id != manifest["loaded_ifc"]["project_global_id"]:
        raise ValueError("canonical capture does not identify the pinned project/source")
    live = load_bonsai_capture(capture, plane=plane)
    binding = confirmed["confirmation_binding"]
    if digest(structural_source_facts(live.structural_scene)) != binding["source_revision"]:
        raise ValueError("capture structural source revision differs from the confirmed domain")
    scene = replace(live.scene, analysis_domain=AnalysisDomain.from_dict(confirmed["analysis_domain"]),
                    geometries=live.scene.geometries + tuple(MeshGeometry3D.from_dict(row) for row in confirmed["domain_geometries"]))
    print("Projecting the confirmed scene once", flush=True)
    view = analysis_scene_view(scene)
    meta = view["_analysis_view"]
    offset = tuple(meta["origin_offset"])
    projected = meta["projected_geometry_components"]
    components = shift_components([item for ref in scene.analysis_domain.geometry_refs for item in projected[ref]], offset)
    geometry = component_shape(components)
    original = shape(confirmed["scope_polygon"])
    from shapely.affinity import translate
    if not geometry.equals_exact(translate(original, *offset), 1e-8) and geometry.symmetric_difference(translate(original, *offset)).area > 1e-8:
        raise ValueError("same-view domain geometry differs from the confirmed scope")
    inventory = _build_authored_group_inventory(scene)
    sources = {item.id: item for item in scene.source_objects}
    groups, projection_audit = [], []
    for item in sorted(inventory["eligible_groups"], key=lambda row: row["id"]):
        members = item["member_refs"]
        missing = [ref for ref in members if not sources[ref].geometry_refs or any(not projected.get(key) for key in sources[ref].geometry_refs)]
        group_components = shift_components([component for ref in members for key in sources[ref].geometry_refs for component in projected.get(key, ())], offset)
        status = "invalid" if item["unresolved_member_refs"] else "not_available" if missing else "available"
        groups.append(GroupProjection(item["id"], group_components or None, tuple(item["declared_member_refs"]), status,
                                      "unresolved authored members" if item["unresolved_member_refs"] else "missing member projection" if missing else ""))
        projection_audit.append({"group_id": item["id"], "status": status, "missing_projection_member_ids": missing,
                                 "unresolved_member_refs": item["unresolved_member_refs"], "declared_member_refs": item["declared_member_refs"]})
    if len(groups) != 37:
        raise ValueError(f"pinned IFC scope requires 37 groups, got {len(groups)}")
    # Only consumed occupancy facts cross the immutable handoff; Rect/channel objects do not.
    occupancy_keys = ("id", "geometry_components", "represented_source_ids", "representation_status",
                      "representation_provenance", "representation_diagnostics", "_source_geometry_refs", "_neutral_source_id")
    occupancy = tuple({key: record[key] for key in occupancy_keys if key in record} for record in view["physical_occupancy"])
    frame = binding["frame_id"]
    domain = {"id": scene.analysis_domain.id, "frame": frame, "components": components,
              "confirmation_binding": binding, "provenance": plain(scene.analysis_domain.provenance),
              "selected_candidate_id": manifest["selected_candidate_id"]}
    x0, y0, x1, y1 = geometry.bounds
    origin = (math.floor(x0 / spacing) * spacing, math.floor(y0 / spacing) * spacing)
    query = FieldQuery(domain_id=domain["id"], frame=frame, revision=binding["source_revision"])
    grid = GridDescriptor("domain-distance:" + digest({"domain": domain["id"], "spacing": spacing})[:20], frame, origin,
                          spacing, math.ceil((y1 - origin[1]) / spacing), math.ceil((x1 - origin[0]) / spacing))
    bundle = GroupDistanceInput(source, {**plane.to_dict(), "frame_id": frame, "units": "m"}, domain, grid, tuple(groups),
        occupancy, tuple(meta["physical_occupancy_unresolved_source_ids"]), {}, query,
        {**asdict(query), "geometry_query": "whole_height_planar_mass_patch", "algorithm_version": "free-space-field/2", "schema_version": "free-space-field/1"}, offset, {})
    fingerprints = group_distance_input_fingerprints(bundle)
    bundle = replace(bundle, query_context={**dict(bundle.query_context), "analysis_plane_fingerprint": fingerprints["analysis_plane"]})
    bundle = replace(bundle, grid=replace(grid, domain_fingerprint=fingerprints["domain"], occupancy_fingerprint=fingerprints["occupancy"]))
    bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
    audit = {"capture_sha256": file_hash(capture_path), "single_analysis_scene_view": True,
             "capture_records": len(capture.records), "source_objects": len(scene.source_objects),
             "physical_occupancy_records": len(occupancy), "unresolved_source_ids": list(bundle.unresolved_source_ids),
             "group_inventory": plain(inventory), "group_projection_completeness": projection_audit, "domain_area_m2": geometry.area,
             "domain_bounds_in_view_m": geometry.bounds, "origin_offset": offset,
             "spacing_provenance": "explicit --spacing-m; diagnostic resolution, not body-width calibration",
             "confirmation_input_hashes": {name: file_hash(s4_dir / name) for name in confirmation_names(s4_dir)}}
    del view, scene, live, capture
    gc.collect()
    return bundle, audit


def normalized_hash(result: dict) -> str:
    """Exclude measured runtime/allocation diagnostics from content determinism."""
    return digest({key: value for key, value in result.items() if key != "diagnostics"})


def validate_result(result: dict, bundle: GroupDistanceInput) -> dict:
    """Check real selected paths, full pair coverage and numerical lineage in one pass."""
    observations, index, manifest = result["observations"], result["pair_index"], result["manifest"]
    expected = manifest["expected_pair_ids"]
    observed = [row["pair_id"] for row in observations]
    indexed = [row["pair_id"] for row in index]
    if len(expected) != 666 or len(set(expected)) != 666 or set(expected) != set(observed) or set(expected) != set(indexed) or len(observed) != 666 or len(indexed) != 666:
        raise ValueError("observations, manifest and pair index are not a 666-pair bijection")
    domain = component_shape(bundle.domain["components"])
    samples = {tuple(item["cell_key"]): item for item in manifest["cell_samples"]}
    paths, nodes, edges = 0, 0, 0
    for item in index:
        observation = observations[item["observation_index"]]
        if item["pair_id"] != observation["pair_id"] or item["group_ids"] != observation["group_ids"]:
            raise ValueError("pair index resolves to the wrong observation")
    for observation in observations:
        for channel in ("center_to_center_euclidean", "centroid_free_space_hybrid"):
            value = observation[channel]["value"]
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError("reported distance is not finite and nonnegative")
        route = observation["route"]
        if route is None:
            continue
        paths += 1
        cells = route["cell_keys"]
        for cell, point, audit in zip(cells, route["points"], route["cells"], strict=True):
            sample = samples[tuple(cell)]
            if sample != audit or sample["status"] not in {"established", "conditional"} or sample["value"] is not False or not domain.covers(Point(point)):
                raise ValueError("selected route includes a non-free or outside cell")
            nodes += 1
        for a, b, edge in zip(cells[:-1], cells[1:], route["edges"], strict=True):
            if sum(abs(x - y) for x, y in zip(a, b)) != 1 or not domain.covers(LineString((samples[tuple(a)]["center"], samples[tuple(b)]["center"]))):
                raise ValueError("selected edge violates four-neighbor/domain coverage")
            if edge["from"] != a or edge["to"] != b or edge["weight"] != math.dist(samples[tuple(a)]["center"], samples[tuple(b)]["center"]):
                raise ValueError("selected edge endpoints or length differ from the recorded path")
            if edge["domain_fingerprint"] != bundle.grid.domain_fingerprint or edge["occupancy_query_refs"] != [samples[tuple(a)]["query_ref"], samples[tuple(b)]["query_ref"]] and edge["occupancy_query_refs"] != [samples[tuple(b)]["query_ref"], samples[tuple(a)]["query_ref"]]:
                raise ValueError("selected edge lineage does not match cell queries")
            edges += 1
        arithmetic = route["arithmetic"]
        if arithmetic["backend_replay"] != arithmetic["backend_hybrid_label"] or abs(arithmetic["residual"]) > arithmetic["rounding_bound"]:
            raise ValueError("selected route arithmetic is invalid")
        euclidean = observation["center_to_center_euclidean"]["value"]
        if observation["centroid_free_space_hybrid"]["value"] + arithmetic["rounding_bound"] < euclidean:
            raise ValueError("hybrid polygonal route is shorter than its fixed-endpoint Euclidean distance")
        for identity, access, component in zip(observation["group_ids"], (route["source_access"], route["target_access"]), ("source_offset", "target_offset"), strict=True):
            centroid = observation["geometry_audit"][identity]["centroid"]
            if arithmetic[component] != math.dist(centroid, access["proxy_point"]) + math.dist(access["proxy_point"], access["cell_center"]):
                raise ValueError("endpoint offset arithmetic differs from its recorded segments")
    counts = Counter(row["centroid_free_space_hybrid"]["status"] for row in observations)
    return {"expected_pair_count": 666, "observation_count": len(observations), "index_count": len(index),
            "pair_set_bijection": True, "duplicate_pair_ids": [], "missing_pair_ids": [],
            "actual_hybrid_status_counts": dict(counts), "unobserved_hybrid_statuses": sorted(STATES - set(counts)),
            "selected_paths_checked": paths, "selected_nodes_checked": nodes, "selected_edges_checked": edges,
            "tie_uncertainty_pairs": sum(bool(row["centroid_free_space_hybrid"]["tie_uncertainty"]) for row in observations),
            "optimistic_witness_pairs": sum(row["lineage"]["optimistic_lower_bound"] is not None for row in observations),
            "finite_metric_values": True, "matrix_diagonal": "null/not_applicable",
            "user_visual_review": "pending"}


def retained_input(path: Path) -> GroupDistanceInput:
    """Restore retained same-view facts after an interrupted implementation attempt."""
    data = read_json(path)
    bundle = GroupDistanceInput(**{**data, "grid": GridDescriptor(**data["grid"]),
        "query": FieldQuery(**data["query"]), "groups": tuple(GroupProjection(**row) for row in data["groups"])})
    fingerprints = group_distance_input_fingerprints(bundle)
    if (dict(bundle.dependency_fingerprints) != fingerprints or bundle.grid.domain_fingerprint != fingerprints["domain"]
            or bundle.grid.occupancy_fingerprint != fingerprints["occupancy"]):
        raise ValueError("retained input content differs from its saved dependency fingerprints")
    return bundle


def validate_retained_binding(bundle: GroupDistanceInput, audit: dict, directory: Path,
                              source: dict, spacing: float) -> tuple[dict, dict]:
    """Authenticate the saved source, confirmation and common translation before reuse."""
    manifest, confirmed = confirmed_domain(directory, source)
    binding = confirmed["confirmation_binding"]
    capture_path = Path(manifest.get("retained_capture_path", directory / "canonical_capture.json"))
    hashes = audit.get("confirmation_input_hashes", audit.get("s4_input_hashes", {}))
    stored_plane = bundle.query_context.get("analysis_plane_fingerprint")
    if (dict(bundle.source_identity) != source or bundle.grid.spacing != spacing
            or _json_value(bundle.domain["confirmation_binding"]) != binding
            or {key: _json_value(bundle.analysis_plane[key]) for key in manifest["analysis_plane"]} != manifest["analysis_plane"]
            or bundle.analysis_plane.get("frame_id") != binding["frame_id"] or bundle.analysis_plane.get("units") != "m"
            or any(frame != binding["frame_id"] for frame in (bundle.grid.frame, bundle.query.frame, bundle.domain["frame"], bundle.query_context["frame"]))
            or bundle.domain["id"] != confirmed["analysis_domain"]["id"] or bundle.query.domain_id != bundle.domain["id"]
            or bundle.query_context["domain_id"] != bundle.domain["id"] or bundle.query.revision != binding["source_revision"]
            or any(_json_value(bundle.query_context.get(key)) != _json_value(value) for key, value in asdict(bundle.query).items())
            or stored_plane is not None and stored_plane != group_distance_input_fingerprints(bundle)["analysis_plane"]
            or list(bundle.origin_offset) != audit["origin_offset"]
            or audit["capture_sha256"] != file_hash(capture_path)
            or set(hashes) != set(confirmation_names(directory))
            or any(hashes[name] != file_hash(directory / name) for name in hashes)):
        raise ValueError("retained parsed handoff does not match its pinned source/domain/spacing")
    from shapely.affinity import translate
    original = shape(confirmed["scope_polygon"])
    expected_offset = (-original.bounds[0], -original.bounds[1])
    if (tuple(bundle.origin_offset) != expected_offset
            or component_shape(bundle.domain["components"]).symmetric_difference(translate(original, *expected_offset)).area > 1e-8):
        raise ValueError("retained domain translation differs from the confirmed analysis-view offset")
    return manifest, confirmed


def rebind_retained_input(bundle: GroupDistanceInput, audit: dict, *, old_directory: Path,
                          new_directory: Path, source: dict, spacing: float) -> tuple[GroupDistanceInput, dict]:
    """Rebase authenticated cached projections onto a fresh exact wall-domain confirmation."""
    old_manifest, old_result = validate_retained_binding(bundle, audit, old_directory, source, spacing)
    manifest, confirmed = confirmed_domain(new_directory, source)
    binding = confirmed["confirmation_binding"]
    # A common translation is valid only for unchanged factual capture and camera projection.
    if (manifest["analysis_plane"] != old_manifest["analysis_plane"]
            or binding["source_revision"] != old_result["confirmation_binding"]["source_revision"]
            or manifest["capture_sha256"] != audit["capture_sha256"] or bundle.unresolved_supports
            or any(item["analysis_domain"]["source_id"] is not None for item in (old_result, confirmed))):
        raise ValueError("cached rebind requires identical source/camera and explicitly translatable supports")
    polygon = shape(confirmed["scope_polygon"])
    offset = (-polygon.bounds[0], -polygon.bounds[1])
    delta = tuple(new - old for new, old in zip(offset, bundle.origin_offset, strict=True))
    components = shift_components([{"exterior": list(polygon.exterior.coords),
        "holes": [list(ring.coords) for ring in polygon.interiors]}], offset)
    domain = {"id": confirmed["analysis_domain"]["id"], "frame": binding["frame_id"], "components": components,
        "confirmation_binding": binding, "provenance": confirmed["analysis_domain"]["provenance"],
        "selected_candidate_id": manifest["selected_candidate_id"]}
    groups = tuple(replace(group, components=shift_components(group.components, delta)
                           if group.components else None) for group in bundle.groups)
    occupancy = tuple({**dict(record), "geometry_components": shift_components(record["geometry_components"], delta)}
                      if record.get("geometry_components") else dict(record) for record in bundle.physical_occupancy)
    # The new domain changes exact boundary membership independently of its coordinate translation.
    source_rows = confirmed["b4_diagnostics"]["sources"]
    source_identities = [(row["source"]["id"], row["source"]["source_id"]) for row in source_rows]
    projected_ids = {row["source_ref"] for row in source_rows if row.get("extent", {}).get("polygon_components", 0)}
    old_members, old_membership = _resolve_boundary_member_ids(
        old_result["analysis_domain"]["provenance"].get("boundary_member_source_ids", ()), source_identities, projected_ids)
    new_members, new_membership = _resolve_boundary_member_ids(
        confirmed["analysis_domain"]["provenance"].get("boundary_member_source_ids", ()), source_identities, projected_ids)
    if any(item["status"] != "resolved" for item in old_membership + new_membership):
        raise ValueError("cached rebind requires exact currently projected boundary membership")
    if old_members - new_members:
        raise ValueError("cached rebind would require restoring formerly scoped boundary geometry")
    added_members = new_members - old_members
    removed = [record for record in occupancy if added_members.intersection(record.get("represented_source_ids", ()))]
    removed_owners = {owner for record in removed for owner in record.get("represented_source_ids", ())}
    if (removed_owners != added_members
            or any(not set(record.get("represented_source_ids", ())).issubset(added_members) for record in removed)
            or any(old_members.intersection(record.get("represented_source_ids", ())) for record in occupancy)):
        raise ValueError("cached boundary scope delta contains mixed, missing or historically scoped owners")
    occupancy = tuple(record for record in occupancy if not added_members.intersection(record.get("represented_source_ids", ())))
    plane = {**dict(bundle.analysis_plane), "frame_id": binding["frame_id"]}
    query = replace(bundle.query, domain_id=domain["id"], frame=binding["frame_id"], revision=binding["source_revision"])
    geometry = component_shape(components)
    x0, y0, x1, y1 = geometry.bounds
    origin = (math.floor(x0 / spacing) * spacing, math.floor(y0 / spacing) * spacing)
    grid = GridDescriptor("domain-distance:" + digest({"domain": domain["id"], "spacing": spacing})[:20],
        binding["frame_id"], origin, spacing, math.ceil((y1 - origin[1]) / spacing), math.ceil((x1 - origin[0]) / spacing))
    rebound = replace(bundle, analysis_plane=plane, domain=domain, grid=grid, groups=groups,
        physical_occupancy=occupancy, query=query, query_context={**dict(bundle.query_context), **asdict(query)},
        origin_offset=offset, dependency_fingerprints={})
    fingerprints = group_distance_input_fingerprints(rebound)
    rebound = replace(rebound, query_context={**dict(rebound.query_context), "analysis_plane_fingerprint": fingerprints["analysis_plane"]},
        grid=replace(grid, domain_fingerprint=fingerprints["domain"], occupancy_fingerprint=fingerprints["occupancy"]))
    rebound = replace(rebound, dependency_fingerprints=group_distance_input_fingerprints(rebound))
    inventory_before = [{key: _json_value(value) for key, value in record.items() if key != "geometry_components"}
                        for record in bundle.physical_occupancy]
    inventory_after = [{key: _json_value(value) for key, value in record.items() if key != "geometry_components"}
                       for record in rebound.physical_occupancy]
    expected_inventory = [record for record in inventory_before if not added_members.intersection(record.get("represented_source_ids", ()))]
    if expected_inventory != inventory_after:
        raise ValueError("rebase changed physical occupancy beyond the exact current boundary scope")
    audit = {**audit, "origin_offset": offset, "domain_area_m2": geometry.area, "domain_bounds_in_view_m": geometry.bounds,
        "physical_occupancy_records": len(rebound.physical_occupancy),
        "confirmation_input_hashes": {name: file_hash(new_directory / name) for name in confirmation_names(new_directory)},
        "cache_rebind": {"old_confirmed_directory": str(old_directory.resolve()), "new_confirmed_directory": str(new_directory.resolve()),
            "old_physical_occupancy_records": len(bundle.physical_occupancy),
            "new_physical_occupancy_records": len(rebound.physical_occupancy),
            "old_binding": old_result["confirmation_binding"], "new_binding": binding, "delta_translation_m": delta,
            "old_physical_occupancy_inventory_sha256": digest(inventory_before),
            "physical_occupancy_inventory_sha256": digest(inventory_after),
            "retained_nonboundary_inventory_unchanged": True,
            "boundary_scope_reconciliation": {"policy": "neutral_scene_views._resolve_boundary_member_ids; exact declared selected-domain membership",
                "old_members": sorted(old_members), "new_members": sorted(new_members), "restored_source_ids": [],
                "newly_scoped_out_source_ids": sorted(added_members),
                "removed_records": [{"id": record["id"], "represented_source_ids": _json_value(record["represented_source_ids"]),
                    "reason": "selected_analysis_domain_member"} for record in removed],
                "old_resolver_diagnostics": old_membership, "new_resolver_diagnostics": new_membership},
            "old_saved_claims_validated_before_rebind": True, "capture_reparsed": False, "geometry_reprojected": False}}
    audit.pop("s4_input_hashes", None)
    return rebound, audit


def run(source: Path, s4_dir: Path, spacing: float, output: Path, *, parsed_input: Path | None = None,
        previous_domain_dir: Path | None = None, replay: bool = True) -> dict:
    """Retain a complete real-source run, optionally replaying the immutable bundle."""
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError("--spacing-m must be positive and finite")
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    before = source_identity(source)
    try:
        if parsed_input is None:
            bundle, audit = build_input(s4_dir, before, spacing)
        else:
            bundle, audit = retained_input(parsed_input), read_json(parsed_input.parent / "adapter_audit.json")
            if previous_domain_dir is not None:
                bundle, audit = rebind_retained_input(bundle, audit, old_directory=previous_domain_dir,
                    new_directory=s4_dir, source=before, spacing=spacing)
            else:
                validate_retained_binding(bundle, audit, s4_dir, before, spacing)
            # Only the implementation-era missing plane binding is upgraded after all saved claims match.
            plane_fingerprint = group_distance_input_fingerprints(bundle)["analysis_plane"]
            stored_binding = bundle.query_context.get("analysis_plane_fingerprint")
            if stored_binding is not None and stored_binding != plane_fingerprint:
                raise ValueError("retained query context declares another analysis plane")
            if stored_binding is None:
                bundle = replace(bundle, query_context={**dict(bundle.query_context), "analysis_plane_fingerprint": plane_fingerprint})
                bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
                audit = {**audit, "retained_input_upgrade": "added missing analysis_plane_fingerprint after source/plane/frame/domain/offset/dependency validation"}
            previous = read_json(parsed_input.parent / "run_manifest.json") if (parsed_input.parent / "run_manifest.json").exists() else read_json(parsed_input.parent / "failure.json")
            audit = {**audit, "retained_adapter_input": str(parsed_input.resolve()), "retained_adapter_input_sha256": file_hash(parsed_input),
                     "prior_process_resources": previous.get("resources", previous.get("memory")),
                     "prior_kernel_version_attempt": str(parsed_input.parent.resolve())}
        write_json(output / "input_bundle.json", _json_value(bundle))
        write_json(output / "scene_geometry.json", {"analysis_plane": _json_value(bundle.analysis_plane), "origin_offset": bundle.origin_offset,
            "domain": _json_value(bundle.domain), "groups": _json_value(bundle.groups), "physical_occupancy": _json_value(bundle.physical_occupancy),
            "unresolved_source_ids": list(bundle.unresolved_source_ids), "unresolved_supports": _json_value(bundle.unresolved_supports)})
        write_json(output / "adapter_audit.json", audit)
        memory_before = process_memory()
        print(f"Calculating {len(bundle.groups)} groups / 666 pairs on {bundle.grid.n_rows} x {bundle.grid.n_cols}", flush=True)
        first = serialize_group_distance_result(calculate_group_pair_distances(bundle))
        if first["diagnostics"]["global_status"] is not None:
            raise ValueError("kernel rejected the complete adapter handoff: " + first["diagnostics"]["global_explanation"])
        coverage = validate_result(first, bundle)
        first_hash = normalized_hash(first)
        second_hash = None
        if replay:
            print("Replaying the same immutable bundle for determinism", flush=True)
            repeated = serialize_group_distance_result(calculate_group_pair_distances(bundle))
            second_hash = normalized_hash(repeated)
            if first_hash != second_hash:
                raise ValueError("same-bundle replay normalized result differs")
        memory_after = process_memory()
        for item in first["pair_index"]:
            item["observation_locator"] = f"observations.json#/{item['observation_index']}"
            item["route_view_locator"] = f"preview/index.html#{item['pair_id']}"
        write_json(output / "observations.json", first["observations"])
        write_json(output / "pair_index.json", first["pair_index"])
        write_json(output / "run_manifest.json", {**first["manifest"], "adapter_audit": audit, "source_before": before,
            "source_after": source_identity(source), "kernel_diagnostics": first["diagnostics"],
            "same_bundle_replay": {"normalized_sha256": first_hash, "repeated_normalized_sha256": second_hash,
                                   "performed": replay, "equal": first_hash == second_hash if replay else None,
                                   "scope": "same immutable parsed input; runtime/allocation diagnostics excluded" if replay else "explicitly skipped for corrected domain; prior unchanged-kernel replay retained"},
            "selected_candidate_id": domain_candidate_id(bundle.domain),
            "resources": {"runner_runtime_s": time.perf_counter() - started,
                          "before_kernel": memory_before, "after_second_kernel": memory_after,
                          "kernel_memory_scope": "kernel tracemalloc only; process records include performed kernel runs",
                          "adapter_memory_scope": "same current process" if parsed_input is None else "retained prior process resource record in adapter_audit",
                          "parsed_input_reused": parsed_input is not None}})
        coverage.update(same_bundle_replay_equal=first_hash == second_hash if replay else None, normalized_result_sha256=first_hash,
                        source_unchanged=True, output_hashes={name: file_hash(output / name) for name in
                            ("observations.json", "pair_index.json", "run_manifest.json", "scene_geometry.json", "input_bundle.json", "adapter_audit.json")})
        write_json(output / "coverage_report.json", coverage)
        return coverage
    except Exception as exc:
        write_json(output / "failure.json", {"type": type(exc).__name__, "message": str(exc), "elapsed_s": time.perf_counter() - started,
                   "source_before": before, "source_after": source_identity(source), "memory": process_memory()})
        raise


def main() -> None:
    """Require explicit source, confirmed domain, resolution and fresh output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ifc", type=Path, required=True)
    parser.add_argument("--domain-dir", "--s4-dir", dest="domain_dir", type=Path, required=True)
    parser.add_argument("--parsed-input", type=Path)
    parser.add_argument("--previous-domain-dir", type=Path)
    parser.add_argument("--skip-replay", action="store_true")
    parser.add_argument("--spacing-m", type=float, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source_ifc, args.domain_dir, args.spacing_m, args.output_dir,
        parsed_input=args.parsed_input, previous_domain_dir=args.previous_domain_dir, replay=not args.skip_replay), indent=2))


if __name__ == "__main__":
    main()
