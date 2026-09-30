"""Compare four D6 direction estimands without changing production evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.ifc_bonsai import _native_length_unit, _native_mesh_record, _native_source_id, _native_world_transform, _scene_from_records  # noqa: E402
from features.group_self_description import _directions, _polygon_moments, _representative, describe_group_relations  # noqa: E402
from features.scene_contract import AuthoredGroup, SourceObject  # noqa: E402
from features.scene_inference import _pca_frame_stats  # noqa: E402
from trend_substitute_registry import load_registry, resolve_contract, validate_records  # noqa: E402

SCHEMA = "d6-trend-direction-design-probe/v1"
SOURCE = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
FIXTURES = Path(__file__).with_name("trend_direction_fixtures.json")
REGISTRY_PATH = Path(__file__).with_name("trend_substitute_registry.json")
OUT = ROOT / "outputs/design/trend_direction_probe"
REGISTRY = load_registry(REGISTRY_PATH)


def digest(path: Path) -> dict[str, object]:
    """Record source identity without modifying the input."""
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha.hexdigest()}


def write_json(path: Path, payload: object) -> None:
    """Write strict, deterministic experiment evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def build_typed_substitute_record(substitute_id: str, source_object_id: str, provenance: dict[str, object]) -> dict[str, object]:
    """Create one trend-authorized Analysis substitute with auditable provenance."""
    record = {
        "substitute_id": substitute_id,
        "source_object_id": source_object_id,
        "consumer": "trend",
        "substitute_kind": "MassPatch",
        "analysis_role": "analysis_geometry_substitute",
        "representation_identifier": "Analysis",
        "contract_key": "trend_analysis",
        "provenance": provenance,
    }
    resolution = resolve_contract(record, "trend", REGISTRY)
    if resolution["status"] != "accepted":
        raise ValueError(f"typed Analysis substitute rejected: {resolution}")
    return record


def select_trend_analysis_geometry(record: dict[str, object]) -> dict[str, object]:
    """Return geometry only for a complete typed trend Analysis binding."""
    resolution = resolve_contract(record, "trend", REGISTRY)
    if resolution["status"] != "accepted":
        return {"status": "not_available", "reason": resolution}
    return {"status": "accepted", "contract_key": resolution["contract_key"], "substitute_id": record["substitute_id"]}


def rectangle(spec: dict[str, object]) -> list[list[float]]:
    """Create a rectangle ring with optional boundary subdivisions."""
    cx, cy = spec["center"]
    width, height = spec["size"]
    theta = math.radians(spec.get("angle", 0.0))
    corners = [(-width / 2, -height / 2), (width / 2, -height / 2), (width / 2, height / 2), (-width / 2, height / 2)]
    steps = int(spec.get("edge_subdivisions", 1))
    points = []
    for i, first in enumerate(corners):
        second = corners[(i + 1) % 4]
        for n in range(steps):
            x = first[0] + (second[0] - first[0]) * n / steps
            y = first[1] + (second[1] - first[1]) * n / steps
            points.append([cx + x * math.cos(theta) - y * math.sin(theta), cy + x * math.sin(theta) + y * math.cos(theta)])
    return points


def axis_pca(covariance: list[list[float]]) -> dict[str, object]:
    """Return a 180 degree axis from a symmetric area or centroid covariance."""
    xx, xy, yy = covariance[0][0], covariance[0][1], covariance[1][1]
    trace = xx + yy
    delta = math.hypot(xx - yy, 2 * xy)
    if trace <= 1e-12 or delta <= 1e-12 * max(trace, 1.0):
        return {"status": "undefined", "angle_deg": None, "strength": 0.0, "eigenvalues": [(trace + delta) / 2, (trace - delta) / 2]}
    return {"status": "computed", "angle_deg": (math.degrees(math.atan2(2 * xy, xx - yy)) / 2) % 180, "strength": delta / trace, "eigenvalues": [(trace + delta) / 2, (trace - delta) / 2]}


def point_pca(points: list[list[float]]) -> dict[str, object]:
    """Apply the historical equal-point PCA to the exact assembled point list."""
    stats = _pca_frame_stats([tuple(point) for point in points])
    return {"status": "computed" if stats["clarity"] > 1e-12 else "undefined", "angle_deg": stats["angle"] if stats["clarity"] > 1e-12 else None, "strength": stats["clarity"], "center": [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)] if points else None, "point_count": len(points)}


def compare_group(group_id: str, members: list[dict[str, object]], excluded: list[dict[str, object]], extents: list[list[list[float]]], *, source: str) -> dict[str, object]:
    """Keep complete estimands separate from partial usable-subset diagnostics."""
    invalid = any(item["status"] == "invalid" for item in excluded)
    status = "invalid" if invalid else "partial" if excluded else "computed" if members else "not_available"
    result = {"id": group_id, "source": source, "status": status, "member_count": len(members) + len(excluded), "usable_member_count": len(members), "excluded_member_reasons": excluded, "footprints": [{"member_id": item["member_id"], "polygons": item["polygons"], "area": item["area"], "center": item["center"], "substitute": item["substitute"]} for item in members], "analysis_substitutes": [item["substitute"] for item in members], "typed_binding": validate_records([item["substitute"] for item in members], "trend", REGISTRY) if members else {"status": "not_available", "reason_code": "no_analysis_members"}, "affordance_extents": extents, "estimands": None, "usable_subset": None}
    if not members:
        return result
    # The descriptor's area moments are reused so the probe compares estimands,
    # not two competing implementations of polygon integration.
    support = sum(item["area"] for item in members)
    representative = _representative(members, support)
    consensus = _directions(members)
    anisotropies = []
    for item in members:
        xx, xy, yy = item["covariance"][0][0], item["covariance"][0][1], item["covariance"][1][1]
        trace = xx + yy
        anisotropies.append(math.hypot(xx - yy, 2 * xy) / trace if trace > 0 else 0.0)
    cloud = [point for extent in extents for point in extent] + [point for item in members for point in item["points"]]
    legacy = point_pca(cloud)
    legacy["input"] = {"affordance_extent_point_count": sum(len(extent) for extent in extents), "member_footprint_point_count": sum(len(item["points"]) for item in members), "point_weight": "one_per_recorded_vertex_including_extent_closure", "extent_count": len(extents), "member_count": len(members)}
    frame = consensus["group_frame"]
    axis = consensus["group_axis"]
    estimands = {
        "member_orientation_consensus": {"status": frame["direction_status"], "frame_angle_deg": frame["angle"], "frame_coherence": frame["coherence"], "axis_angle_deg": axis["angle"], "axis_coherence": axis["coherence"], "directional_member_support": consensus["directional_member_support"], "weight": "member_area_times_polygon_anisotropy", "member_anisotropy": anisotropies, "near_isotropic_diagnostic": bool(anisotropies) and max(anisotropies) < 1e-8},
        "legacy_projected_point_cloud_pca": legacy,
        "area_weighted_total_covariance_pca": {**axis_pca(representative["covariance"]), "center": representative["center"], "support_area": support, "within_member_covariance": representative["within_member_covariance"], "between_member_covariance": representative["between_member_covariance"], "total_covariance": representative["covariance"]},
        "between_member_centroid_pca": {**axis_pca(representative["between_member_covariance"]), "center": representative["center"], "weight": "member_area_divided_by_total_support_area", "covariance": representative["between_member_covariance"]},
    }
    if status == "computed":
        result["estimands"] = estimands
    else:
        result["usable_subset"] = {"status": "partial_diagnostic", "excluded_from_winner_decision": True, "estimands": estimands}
    return result


def synthetic_cases() -> list[dict[str, object]]:
    """Evaluate deterministic footprints and propagate invalid/partial states."""
    fixture = json.loads(FIXTURES.read_text(encoding="utf-8"))
    results = []
    for case in fixture["cases"]:
        valid, excluded, extents = [], [], []
        for spec in case["members"]:
            member_id = spec["id"]
            if spec.get("status") == "missing":
                excluded.append({"member_id": member_id, "status": "not_available", "reason": "missing_geometry"})
                continue
            if spec.get("holes"):
                excluded.append({"member_id": member_id, "status": "invalid", "reason": "unsupported_holes"})
                continue
            polygon = spec.get("polygon") or rectangle(spec)
            moments = _polygon_moments(polygon, 1e-9)
            if moments is None:
                excluded.append({"member_id": member_id, "status": "invalid", "reason": "invalid_polygon"})
                continue
            valid.append({"member_id": member_id, "area": moments["area"], "center": moments["center"], "covariance": moments["covariance"], "points": moments["points"], "polygons": [moments["points"]], "directional_weight": None, "substitute": build_typed_substitute_record(f"fixture:{case['id']}:{member_id}:analysis", f"fixture-object:{member_id}", {"representation_identifier": "Analysis", "extraction_method": "deterministic_fixture_polygon", "visibility_policy": "analysis_only", "world_transform_applied": True})})
            # Legacy extents were rect corners with a repeated closure point.
            for extent in spec.get("affordance_extents", []):
                ring = rectangle(extent)
                extents.append(ring + [ring[0]])
        record = compare_group(case["id"], valid, excluded, extents, source="deterministic_fixture")
        record["description"] = case["description"]
        record["truth"] = case["truth"]
        results.append(record)
    return results


def representation(entity: object, name: str) -> object | None:
    """Find only the named authored representation, without a Body fallback."""
    return next((item for item in getattr(getattr(entity, "Representation", None), "Representations", ()) or () if getattr(item, "RepresentationIdentifier", None) == name), None)


def ifc_cases() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Scan exact groups in source order until three complete Analysis groups exist."""
    import ifcopenshell
    import ifcopenshell.geom  # noqa: F401
    import ifcopenshell.util.shape  # noqa: F401

    source_hash = digest(SOURCE)
    source = ifcopenshell.open(str(SOURCE))
    module = importlib.import_module("ifcopenshell")
    units, scale, _, _ = _native_length_unit(source)
    products = {_native_source_id(item): item for item in source.by_type("IfcProduct")}
    groups = []
    for group in source.by_type("IfcGroup"):
        if getattr(group, "ObjectType", None) != "furniture_group":
            continue
        members = [_native_source_id(item) for relation in getattr(group, "IsGroupedBy", ()) or () for item in getattr(relation, "RelatedObjects", ()) or ()]
        groups.append((str(_native_source_id(group)), members))
    groups.sort(key=lambda pair: pair[0])
    inventory_records = [{"id": f"ifc-group:{group_id}", "source_id": group_id, "object_type": "furniture_group", "member_source_ids": member_ids, "member_count": len(member_ids), "eligible_exact_role": True} for group_id, member_ids in groups]
    results, skipped, scanned = [], [], []
    for group_id, member_ids in groups:
        if len(results) >= 3:
            break
        if not member_ids:
            skipped.append({"group_id": group_id, "reason": "empty_authored_membership"})
            continue
        source_objects, meshes, extraction_reasons, typed_by_member = [], [], [], {}
        for member_id in member_ids:
            entity = products.get(member_id)
            selected = representation(entity, "Analysis") if entity is not None else None
            if entity is None:
                extraction_reasons.append({"member_id": f"ifc-object:{member_id}", "status": "invalid", "reason": "unresolved_member_ref"})
                continue
            if selected is None:
                extraction_reasons.append({"member_id": f"ifc-object:{member_id}", "status": "not_available", "reason": "missing_Analysis_representation"})
                continue
            mesh, uncertainty = _native_mesh_record(entity, f"{member_id}:analysis", units, module, selected)
            if mesh is None:
                extraction_reasons.append({"member_id": f"ifc-object:{member_id}", "status": "invalid", "reason": "Analysis_extraction_failed", "details": uncertainty.to_dict() if uncertainty else None})
                continue
            meshes.append(mesh)
            transform, _ = _native_world_transform(entity, float(scale), member_id)
            typed_by_member[member_id] = build_typed_substitute_record(f"ifc-object:{member_id}:analysis", f"ifc-object:{member_id}", {"source_ifc_sha256": source_hash["sha256"], "source_global_id": member_id, "representation_identifier": getattr(selected, "RepresentationIdentifier", None), "representation_type": selected.is_a(), "extraction_method": "ifcopenshell_analysis_representation", "visibility_policy": "analysis_only", "world_transform_applied": True, "raw_property_identifiers": ["ObjectType", "GlobalId"], "raw_property_values": {"ObjectType": getattr(entity, "ObjectType", None), "GlobalId": member_id}})
            source_objects.append(SourceObject(id=f"ifc-object:{member_id}", source_id=member_id, source_role="furniture", source_class=entity.is_a(), world_transform=transform, geometry_refs=(mesh.id,), group_refs=(f"ifc-group:{group_id}",), factual_properties={"analysis_authoritative": True}, provenance={"method": "design_selective_Analysis_extraction"}, uncertainties=()))
        authored = AuthoredGroup(id=f"ifc-group:{group_id}", source_id=group_id, member_refs=tuple(f"ifc-object:{member_id}" for member_id in member_ids), group_role="furniture_group", provenance={"method": "ifc4_group_assignment"})
        scene = _scene_from_records(units, source_objects, meshes, authored_groups=(authored,), analysis_units="m")
        descriptor = describe_group_relations(scene)["group_geometry"][0]
        valid = [dict(item, substitute=typed_by_member[item["member_id"].split(":")[-1]]) for item in descriptor["member_geometry"] if item["member_id"].split(":")[-1] in typed_by_member]
        excluded = list(descriptor["excluded_member_reasons"]) + extraction_reasons
        # Descriptor already marks unextracted authored members invalid; dedupe
        # by member id and keep the more specific extraction reason.
        by_member = {item["member_id"]: item for item in descriptor["excluded_member_reasons"]}
        by_member.update({item["member_id"]: item for item in extraction_reasons})
        excluded = list(by_member.values())
        record = compare_group(f"ifc-group:{group_id}", valid, excluded, [], source="real_IFC_Analysis")
        record["typed_binding"] = validate_records(record["analysis_substitutes"], "trend", REGISTRY)
        record["descriptor_geometry_status"] = descriptor["geometry_status"]
        record["source_member_ids"] = member_ids
        scanned.append({"group_id": group_id, "status": record["status"], "member_count": len(member_ids), "usable_member_count": len(valid), "excluded_member_reasons": excluded})
        if record["status"] == "computed" and descriptor["geometry_status"] == "computed":
            results.append(record)
        else:
            skipped.append(scanned[-1])
    return results, skipped, {"source": source_hash, "source_schema": source.schema, "source_unit": units, "analysis_unit": "m", "exact_group_count": len(groups), "scanned_group_count": len(scanned), "selection_policy": "first_three_complete_Analysis_footprint_groups_after_full_exact_role_metadata_inventory_sorted_by_source_id", "selected_group_ids": [item["id"] for item in results], "records": inventory_records, "context_counts": {name: len(source.by_type(name)) for name in ("IfcProduct", "IfcWall", "IfcDoor", "IfcSpace", "IfcOpeningElement", "IfcSpatialZone", "IfcGroup")}}


def assertions(synthetic: list[dict[str, object]], real: list[dict[str, object]]) -> list[str]:
    """Check semantic separation, status propagation, and tessellation invariance."""
    by_id = {item["id"]: item for item in synthetic}
    first = by_id["aligned_members_vertical_centers"]["estimands"]
    assert first["member_orientation_consensus"]["frame_angle_deg"] < 1e-8
    assert abs(first["between_member_centroid_pca"]["angle_deg"] - 90) < 1e-8
    second = by_id["aligned_members_horizontal_centers"]["estimands"]
    assert second["between_member_centroid_pca"]["angle_deg"] < 1e-8
    assert by_id["near_isotropic_members"]["estimands"]["member_orientation_consensus"]["near_isotropic_diagnostic"]
    assert by_id["holes_invalid_member"]["estimands"] is None
    assert by_id["holes_invalid_member"]["usable_subset"]["status"] == "partial_diagnostic"
    assert by_id["missing_partial_member"]["status"] == "partial"
    assert by_id["self_intersecting_invalid_member"]["status"] == "invalid"
    tess = by_id["tessellation_density_invariance"]["estimands"]
    assert tess["legacy_projected_point_cloud_pca"]["input"]["member_footprint_point_count"] == 52
    assert all(item["status"] == "computed" and item["estimands"] for item in real)
    assert all(item["typed_binding"]["status"] == "accepted" for item in real)
    negative = json.loads((Path(__file__).with_name("trend_substitute_contract_parity_fixtures.json")).read_text(encoding="utf-8"))
    expected = json.loads((Path(__file__).with_name("trend_substitute_contract_parity_truth.json")).read_text(encoding="utf-8"))["negative_reason_codes"]
    for item in negative["negative_records"]:
        records = item["records"] if "records" in item else [item["record"]]
        result = validate_records(records, "trend", REGISTRY)
        assert result["status"] == "rejected" and result["reason_code"] == expected[item["name"]]
    return ["orientation_layout_divergence", "orientation_layout_alignment", "isotropic_undefined", "invalid_and_partial_propagation", "tessellation_point_count", "typed_analysis_binding", "negative_contract_rejections", "real_groups_complete"]


def verify(output_dir: Path) -> None:
    """Validate saved JSON, source identity, and rendered image payloads."""
    result = json.loads((output_dir / "trend_direction_results.json").read_text(encoding="utf-8"))
    assert result["schema"] == SCHEMA
    assert result["winner"] is None and result["production_api_changed"] is False
    assert len(result["ifc_cases"]) >= 3
    assert digest(SOURCE) == result["ifc_inventory"]["source"]
    for name in ("synthetic_trend_direction.png", "ifc_trend_direction.png"):
        from PIL import Image
        with Image.open(output_dir / name) as image:
            assert image.width >= 1000 and image.height >= 600 and image.getbbox() is not None
    print(json.dumps({"status": "pass", "schema": result["schema"], "source_sha256": result["ifc_inventory"]["source"]["sha256"], "images": ["synthetic_trend_direction.png", "ifc_trend_direction.png"]}, sort_keys=True))


def main() -> None:
    """Run the design probe and serialize its complete audit."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(args.output_dir)
        return
    before = digest(SOURCE)
    synthetic = synthetic_cases()
    real, skipped, inventory = ifc_cases()
    checks = assertions(synthetic, real) if len(real) >= 3 else ["real_groups_insufficient"]
    after = digest(SOURCE)
    assert before == after
    result = {"schema": SCHEMA, "purpose": "design_only_estimand_comparison", "fixture_source": digest(FIXTURES), "ifc_inventory": inventory, "source_hash_unchanged": True, "synthetic_cases": synthetic, "ifc_cases": real, "skipped_ifc_groups": skipped, "assertions": checks, "winner": None, "production_api_changed": False}
    write_json(args.output_dir / "trend_direction_results.json", result)
    write_json(args.output_dir / "trend_direction_inventory.json", {"schema": "d6-trend-direction-inventory/v1", "source": inventory["source"], "exact_group_count": inventory["exact_group_count"], "records": inventory["records"], "selection_policy": inventory["selection_policy"], "selected_group_ids": inventory["selected_group_ids"], "skipped_ifc_groups": skipped, "context_counts": inventory["context_counts"]})
    print(json.dumps({"status": "pass" if len(real) >= 3 else "insufficient_valid_ifc_groups", "selected": inventory["selected_group_ids"], "skipped": len(skipped), "assertions": checks}, sort_keys=True))


if __name__ == "__main__":
    main()
