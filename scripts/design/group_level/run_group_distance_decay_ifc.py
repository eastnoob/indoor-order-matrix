"""Replay the retained IFC group distances through one geometry-scaled decay."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import html
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping

from features.group_distance import GroupProjection, _group_geometry
from features.group_distance_evidence_package import (
    SOURCE_CHANNEL,
    build_group_distance_package_contract,
    build_group_distance_source_envelopes,
)
from features.group_self_description import _polygon_moments
from scripts.design.group_level import replay_evidence_package_readback as readback
from scripts.design.group_level.run_group_distance_ifc import file_hash, retained_input


ROOT = Path(__file__).resolve().parents[3]
BUNDLE_PATH = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge/"
    "outputs/design/group_distance_ifc/run_v4_eight_neighbor/input_bundle.json"
)
PACKAGE_PATH = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge_proxy/"
    "outputs/design/group_distance_ifc/run_global_full_current_20261106_merged/"
    "distance_evidence_package/group_distance_package_output.json"
)
ORIGINAL_IFC_PATH = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/"
    "live-rhino-10500-furniture-groups.ifc"
)
DERIVED_IFC_PATH = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache/outputs/design/"
    "free_space_prerequisite/native/analysis-plane-1p6-rna-fixed.ifc"
)
LINEAGE_PATH = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache/outputs/design/"
    "free_space_prerequisite/verification/task5-independent-lineage.json"
)
DERIVED_SAVE_PATH = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache/outputs/design/"
    "free_space_prerequisite/verification/native-derived-save.json"
)
EXPECTED_HASHES = {
    "original_ifc": "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077",
    "derived_ifc": "06400121d7a60dc5a45e64b90c5c9310900103946b2f2fff6cae477c1f935f99",
    "lineage": "8148a4ce74ac82c4b28787ae2e916d218d6f14124ade743da953575c5b99bf78",
    "derived_save": "f6b6683b07f282f6388e91adc1b2fc6cc383af8fccabedc48a96f15137935816",
    "bundle": "28e5304317ef52519d4c6d8c37ff17495032ec331f63e8333d7f15df72a1f93d",
    "package": "c4e81913d97278ce5adf59d5e4380251dbbc88ab896fca8c7aa43af9cd547a53",
    "repair_result": "c3605513bd2e9d21d5f1cb76d54801025eed7cdc2c82ba733a9b21da0319b388",
    "package_contract": "9c9f7905a2f71c746b7311260e726ce4b30a3f14651e765d0ba828b057f633b2",
    "source_integrity": "f98113f9502a4bc3019fcc82d513eb56a602211e5c9c2ac935b499b17933986d",
}
FORMULA_VERSION = "group-union-rms-rss-exp/1"
FORMULA = "ell=sqrt(rho_g^2+rho_h^2); q=d_E/ell; w=exp(-q)"
RECIPROCAL_FORMULA_VERSION = "group-union-rms-rss-reciprocal/1"
RECIPROCAL_FORMULA = "w_reciprocal=1/(1+q)"
SQRT_RECIPROCAL_FORMULA_VERSION = "group-union-rms-rss-sqrt-reciprocal/1"
SQRT_RECIPROCAL_FORMULA = "w_sqrt_reciprocal=1/sqrt(1+q)"
POWER_06_FORMULA_VERSION = "group-union-rms-rss-power-06/1"
POWER_06_FORMULA = "w_power_06=(1+q)^(-0.6)"
_EXPECTED_ADDED_ENTITY_TYPES = Counter({
    "IFCANNOTATION": 1,
    "IFCAXIS2PLACEMENT3D": 2,
    "IFCBLOCK": 1,
    "IFCCARTESIANPOINT": 2,
    "IFCCSGSOLID": 1,
    "IFCDIRECTION": 2,
    "IFCDOCUMENTINFORMATION": 1,
    "IFCDOCUMENTREFERENCE": 1,
    "IFCGROUP": 1,
    "IFCLOCALPLACEMENT": 1,
    "IFCPRODUCTDEFINITIONSHAPE": 1,
    "IFCPROPERTYSET": 2,
    "IFCPROPERTYSINGLEVALUE": 17,
    "IFCRELASSIGNSTOGROUP": 1,
    "IFCRELASSOCIATESDOCUMENT": 2,
    "IFCRELDEFINESBYPROPERTIES": 2,
    "IFCSHAPEREPRESENTATION": 1,
})
CSV_FIELDS = (
    "pair_id", "group_a_id", "group_b_id", "channel", "formula_version", "status", "raw_status", "reason",
    "distance_m", "raw_distance_reading", "rho_a_m", "rho_b_m", "ell_m", "q", "w", "source_ids",
    "centroid_refs", "geometry_audit", "lineage",
)


@dataclass(frozen=True)
class ExperimentInputs:
    """Validated retained inputs and selected Euclidean package outputs."""

    bundle: Any
    outputs: tuple[Any, ...]
    source_envelopes: tuple[Any, ...]
    geometries: Mapping[str, Any]
    scales: Mapping[str, Mapping[str, Any]]
    package_id: str
    output_identity: str
    package_freshness: str
    input_hashes: Mapping[str, str]
    source_binding: Mapping[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    """Load one strict JSON object from an evidence artifact."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _require_hash(path: Path, expected: str, label: str) -> str:
    """Require the exact retained bytes for one fixed experiment dependency."""
    if not path.is_file():
        raise ValueError(f"required {label} is missing: {path}")
    actual = file_hash(path)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch: {path}")
    return actual


def _data_entity_lines(path: Path):
    """Stream STEP entity statements without retaining a full IFC in memory."""
    in_data = False
    with path.open("rb") as stream:
        for line in stream:
            marker = line.strip()
            if marker == b"DATA;":
                in_data = True
                continue
            if in_data and marker == b"ENDSEC;":
                return
            if in_data and marker.startswith(b"#") and b"=" in marker:
                yield line.rstrip(b"\r\n")
    if not in_data:
        raise ValueError(f"IFC DATA section is missing: {path}")


def _verify_ifc_derivative(original: Path, derived: Path) -> dict[str, Any]:
    """Require original STEP entities to remain byte-identical before plane additions."""
    source_lines = iter(_data_entity_lines(original))
    derived_lines = iter(_data_entity_lines(derived))
    original_count = 0
    for source_line in source_lines:
        try:
            derived_line = next(derived_lines)
        except StopIteration as exc:
            raise ValueError("derived IFC omits original STEP entity records") from exc
        if source_line != derived_line:
            raise ValueError("derived IFC changes or reorders an original STEP entity record")
        original_count += 1

    additions = list(derived_lines)
    addition_types = Counter()
    for line in additions:
        match = re.match(rb"#\d+=([A-Z0-9_]+)\(", line)
        if not match:
            raise ValueError("derived IFC contains a malformed appended STEP entity")
        addition_types[match.group(1).decode("ascii")] += 1
    text = b"\n".join(additions)
    if (original_count != 3_597_391 or len(additions) != 39
            or addition_types != _EXPECTED_ADDED_ENTITY_TYPES
            or b"IFCANNOTATION('2JRtSsvK9DueUJ6efD5Ihg'" not in text
            or b"'OM_AnalysisPlane'" not in text
            or b"'LEVEL 1 PLAN'" not in text):
        raise ValueError("derived IFC additions do not match the reviewed analysis-plane drawing")
    return {
        "status": "verified",
        "original_data_entity_lines_preserved": original_count,
        "appended_analysis_plane_drawing_entity_lines": len(additions),
        "appended_entity_type_counts": dict(sorted(addition_types.items())),
        "comparison": "streamed byte-for-byte in entity order; original entity stream is an exact prefix",
    }


def _validate_source_binding(bundle: Any, bundle_path: Path, package_path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Authenticate the original IFC, its plane-bearing derivative, and retained artifacts."""
    hashes = {
        "original_ifc": _require_hash(ORIGINAL_IFC_PATH, EXPECTED_HASHES["original_ifc"], "original IFC"),
        "derived_ifc": _require_hash(DERIVED_IFC_PATH, EXPECTED_HASHES["derived_ifc"], "derived IFC"),
        "lineage": _require_hash(LINEAGE_PATH, EXPECTED_HASHES["lineage"], "IFC lineage receipt"),
        "derived_save": _require_hash(DERIVED_SAVE_PATH, EXPECTED_HASHES["derived_save"], "derived-save receipt"),
        "bundle": _require_hash(bundle_path, EXPECTED_HASHES["bundle"], "retained input bundle"),
        "package": _require_hash(package_path, EXPECTED_HASHES["package"], "saved distance package"),
    }
    source_integrity_path = bundle_path.parent / "source_integrity.json"
    hashes["source_integrity"] = _require_hash(
        source_integrity_path, EXPECTED_HASHES["source_integrity"], "source integrity receipt")
    original_ifc_path = str(ORIGINAL_IFC_PATH.resolve())
    derived_ifc_path = str(DERIVED_IFC_PATH.resolve())
    bundle_source_path = str(Path(bundle.source_identity["ifc_source_identity"]).resolve())
    if (bundle_source_path != derived_ifc_path
            or bundle.source_identity.get("project_global_id") != "2uGd6yom9GZe5$z7LfbGW0"):
        raise ValueError("retained bundle source identity does not match the reviewed IFC derivative")

    lineage_doc = _read_json(LINEAGE_PATH)
    lineage = lineage_doc.get("lineage", {})
    original = lineage.get("original", {})
    derived = lineage.get("derived", {})
    if (lineage_doc.get("status") != "passed_for_preparation_scope_only"
            or lineage.get("original_sha256") != hashes["original_ifc"]
            or lineage.get("derived_sha256") != hashes["derived_ifc"]
            or original.get("schema") != "IFC4" or derived.get("schema") != "IFC4"
            or original.get("project", {}).get("guid") != bundle.source_identity["project_global_id"]
            or derived.get("project", {}).get("guid") != bundle.source_identity["project_global_id"]
            or any(derived.get("groups", {}).get(key) != value
                   for key, value in original.get("groups", {}).items())
            or original.get("furniture_guids") != derived.get("furniture_guids")
            or lineage.get("original_groups_preserved") != 37
            or lineage.get("original_furniture_preserved") != 95
            or lineage.get("status") != "passed"
            or original.get("length_scale_to_m") != derived.get("length_scale_to_m")
            or len(derived.get("drawings", ())) != 1
            or len(lineage.get("extra_groups", {})) != 1):
        raise ValueError("frozen IFC lineage report does not authenticate the retained derivative")
    drawing = derived["drawings"][0]
    if (drawing.get("source_role") != "drawing_camera"
            or drawing.get("physical_inventory_eligible") is not False
            or drawing.get("physical_mass_eligible_even_with_geometry") is not False
            or drawing.get("marker", {}).get("Role") != "analysis_plane"):
        raise ValueError("analysis-plane drawing is not explicitly excluded from physical geometry")

    save_receipt = _read_json(DERIVED_SAVE_PATH)
    if (save_receipt.get("status") != "passed"
            or save_receipt.get("derived_ifc_sha256") != hashes["derived_ifc"]
            or save_receipt.get("project") != bundle.source_identity["project_global_id"]
            or save_receipt.get("native_drawings") != 1):
        raise ValueError("derived IFC save receipt does not match the retained source")
    integrity = _read_json(source_integrity_path)
    if (integrity.get("original_ifc", {}).get("sha256") != hashes["original_ifc"]
            or integrity.get("input_bundle_byte_identical") is not True
            or integrity.get("scene_geometry_byte_identical") is not True):
        raise ValueError("retained bundle integrity receipt does not match the pinned IFC")

    raw_lineage = _verify_ifc_derivative(ORIGINAL_IFC_PATH, DERIVED_IFC_PATH)
    return hashes, {
        "original_ifc": {"path": original_ifc_path, "sha256": hashes["original_ifc"]},
        "retained_geometry_ifc": {"path": derived_ifc_path, "sha256": hashes["derived_ifc"]},
        "lineage_receipt": {"path": str(LINEAGE_PATH.resolve()), "sha256": hashes["lineage"]},
        "derived_save_receipt": {"path": str(DERIVED_SAVE_PATH.resolve()), "sha256": hashes["derived_save"]},
        "raw_step_entity_comparison": raw_lineage,
        "lineage_scope": "preparation-scope identity; no tessellation or EXPRESS validation",
    }


def validate_euclidean_observation(observation: Mapping[str, Any]) -> float:
    """Require a computed finite nonnegative raw Euclidean distance in metres."""
    if observation.get("raw_status") != "computed":
        raise ValueError("raw_status must be computed before decay is evaluated")
    if observation.get("status") != "computed":
        raise ValueError("package status must be computed before decay is evaluated")
    if observation.get("units") != "m":
        raise ValueError("Euclidean distance must be reported in metres")
    value = observation.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Euclidean distance must be finite and nonnegative")
    return float(value)


def _union_rms_radius(group: GroupProjection) -> dict[str, Any]:
    """Compute the hole-aware RMS radius of a group's actual projected union."""
    resolved = _group_geometry(group)
    if resolved["status"] != "computed":
        return {"status": resolved["status"], "rho_m": None, "rho2_m2": None,
                "centroid": None, "centroid_ref": None, "explanation": resolved["explanation"]}
    geometry = resolved["shape"]
    centroid = tuple(resolved["audit"]["centroid"])
    # Center the union before polygon moments to limit cancellation in central moments.
    from shapely.affinity import translate

    centered = translate(geometry, xoff=-centroid[0], yoff=-centroid[1])
    polygons = tuple(centered.geoms) if centered.geom_type == "MultiPolygon" else (centered,)
    total_area = 0.0
    squared_radius_integral = 0.0
    for polygon in polygons:
        moments = _polygon_moments(
            polygon.exterior.coords,
            0.0,
            holes=tuple(ring.coords for ring in polygon.interiors),
        )
        if moments is None:
            return {"status": "invalid", "rho_m": None, "rho2_m2": None,
                    "centroid": centroid, "centroid_ref": resolved["audit"]["centroid_source_ref"],
                    "explanation": "union component moments are invalid"}
        area = moments["area"]
        center_x, center_y = moments["center"]
        covariance = moments["covariance"]
        # Polygon moments are combined only after union, so overlapping source members count once.
        trace_about_union_centroid = covariance[0][0] + covariance[1][1] + center_x ** 2 + center_y ** 2
        total_area += area
        squared_radius_integral += area * trace_about_union_centroid
    rho2 = squared_radius_integral / total_area if total_area > 0 else math.nan
    if not math.isfinite(rho2) or rho2 <= 0:
        return {"status": "invalid", "rho_m": None, "rho2_m2": None,
                "centroid": centroid, "centroid_ref": resolved["audit"]["centroid_source_ref"],
                "explanation": "union RMS radius is not finite and positive"}
    return {
        "status": "computed",
        "rho_m": math.sqrt(rho2),
        "rho2_m2": rho2,
        "centroid": centroid,
        "centroid_ref": resolved["audit"]["centroid_source_ref"],
        "union_area_m2": float(geometry.area),
        "component_count": len(polygons),
        "explanation": "area-uniform second moment of the complete polygon union, including holes",
    }


def load_experiment_inputs(
    *, bundle_path: Path = BUNDLE_PATH, package_path: Path = PACKAGE_PATH,
) -> ExperimentInputs:
    """Authenticate pinned IFC lineage and rebuild fresh Euclidean package context."""
    bundle_path, package_path = Path(bundle_path), Path(package_path)
    expected_contract = package_path.parent / "package_contract.json"
    repair_path = package_path.parent.parent / "repair_result.json"
    bundle = retained_input(bundle_path)
    hashes, source_binding = _validate_source_binding(bundle, bundle_path, package_path)
    hashes["repair_result"] = _require_hash(
        repair_path, EXPECTED_HASHES["repair_result"], "retained route repair result")
    hashes["package_contract"] = _require_hash(
        expected_contract, EXPECTED_HASHES["package_contract"], "cached package contract")
    cached_contract = _read_json(expected_contract)
    repair = _read_json(repair_path)
    repair["retained_result_ref"] = {
        "path": str(repair_path.resolve()),
        "sha256": hashes["repair_result"],
        "observation_lookup": "observations[*].pair_id",
    }

    current_sources = build_group_distance_source_envelopes(
        repair, bundle, repaired_result=repair)
    current_contract = build_group_distance_package_contract(
        repair,
        bundle,
        visualization_manifest=cached_contract["artifacts"]["visualization_manifest"],
    )
    selections = tuple((source.target["identity"], "euclidean_distance") for source in current_sources)
    if len(bundle.groups) != 37 or len(current_sources) != 666 or len(selections) != 666:
        raise ValueError("retained experiment must contain 37 groups and all 666 unordered pairs")
    saved = readback.consume_saved_evidence_package(
        package_path,
        expected_sha256=EXPECTED_HASHES["package"],
        cached_contract=cached_contract,
        current_contract=current_contract,
        current_source_envelopes=current_sources,
        selections=selections,
        dependency_graph={readback.PACKAGE_ID: ("group-walk-distance",), "group-walk-distance": ()},
    )
    if len(saved.outputs) != 666 or not saved.dependencies or saved.dependencies[0].package_freshness != "fresh":
        raise ValueError("saved package did not pass current-source freshness for all Euclidean channels")

    geometries: dict[str, Any] = {}
    scales: dict[str, Mapping[str, Any]] = {}
    for group in bundle.groups:
        if group.group_id in geometries:
            raise ValueError("retained bundle contains duplicate group identities")
        resolved = _group_geometry(group)
        scale = _union_rms_radius(group)
        geometries[group.group_id] = resolved.get("shape")
        scales[group.group_id] = scale
    return ExperimentInputs(
        bundle=bundle,
        outputs=tuple(saved.outputs),
        source_envelopes=tuple(saved.source_envelopes),
        geometries=geometries,
        scales=scales,
        package_id=saved.package_id,
        output_identity=saved.output_identity,
        package_freshness=saved.dependencies[0].package_freshness,
        input_hashes=dict(hashes),
        source_binding=source_binding,
    )


def _plain_reference(reference: Any) -> dict[str, str]:
    """Serialize one package-channel reference without losing its full address."""
    return {
        "package_id": reference.package_id,
        "output_identity": reference.output_identity,
        "target_identity": reference.target_identity,
        "channel": reference.channel,
    }


def geometry_scaled_response(distance: float, rho2_a: float, rho2_b: float) -> tuple[float, float, float]:
    """Evaluate the single experimental response without scene-wide normalization."""
    if any(not math.isfinite(value) or value < 0 for value in (distance, rho2_a, rho2_b)):
        raise ValueError("distance and squared radii must be finite and nonnegative")
    if rho2_a <= 0 or rho2_b <= 0:
        raise ValueError("each group squared radius must be positive")
    ell = math.sqrt(rho2_a + rho2_b)
    if not math.isfinite(ell) or ell <= 0:
        raise ValueError("pair scale must be finite and positive")
    q = distance / ell
    if not math.isfinite(q):
        raise ValueError("dimensionless distance must be finite")
    return ell, q, math.exp(-q)


def build_decay_rows(inputs: ExperimentInputs) -> list[dict[str, Any]]:
    """Build one fully traced geometry-scaled response row per Euclidean pair."""
    rows = []
    seen_pairs = set()
    sources = {source.target["identity"]: source for source in inputs.source_envelopes}
    for output in inputs.outputs:
        pair_id = output.target["identity"]
        if output.channel != "euclidean_distance":
            raise ValueError("only euclidean_distance may enter the decay experiment")
        if pair_id in seen_pairs:
            raise ValueError("saved Euclidean outputs contain duplicate pair identities")
        seen_pairs.add(pair_id)
        observation = output.observation or {}
        source = sources[pair_id]
        raw_source = next(record.observation for record in source.value["channels"]
                          if record.channel == SOURCE_CHANNEL)
        raw_status = observation.get("raw_status", output.provenance.get("raw_distance_status"))
        distance = observation.get("value")
        group_ids = tuple(raw_source["group_ids"])
        if (len(group_ids) != 2 or group_ids[0] >= group_ids[1]
                or any(group_id not in inputs.scales for group_id in group_ids)
                or raw_source["pair_id"] != pair_id
                or (observation and (observation.get("pair_id") != pair_id
                                     or tuple(observation.get("group_ids", ())) != group_ids))):
            raise ValueError("Euclidean pair identity must bind two canonical authenticated groups")
        if (source.query != inputs.bundle.query
                or output.provenance.get("analysis_plane") != inputs.bundle.analysis_plane
                or output.provenance.get("query_context") != inputs.bundle.query_context):
            raise ValueError("Euclidean plane or query differs from the retained union context")
        group_a, group_b = group_ids
        scale_a, scale_b = inputs.scales[group_a], inputs.scales[group_b]
        status = output.status.value
        reason = output.explanation
        ell = q = weight = None
        audit = {}
        centroid_refs = tuple((observation.get("distance") or {}).get("centroid_source_refs", ()))
        if status == "computed" and raw_status == "computed":
            if scale_a["status"] != "computed" or scale_b["status"] != "computed":
                status = "invalid" if "invalid" in {scale_a["status"], scale_b["status"]} else "not_available"
                reason = "union RMS radius unavailable: " + "; ".join(scale["explanation"] for scale in (scale_a, scale_b))
            else:
                expected_refs = (scale_a["centroid_ref"], scale_b["centroid_ref"])
                if centroid_refs != expected_refs:
                    raise ValueError("cached centroid references differ from the scale unions")
                # This tolerance audits binary64 replay; it never changes the distance or scale.
                retained_centroids = tuple(tuple(raw_source["geometry_audit"][group_id]["centroid"]) for group_id in group_ids)
                current_centroids = (scale_a["centroid"], scale_b["centroid"])
                if any(not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)
                       for old, current in zip(retained_centroids, current_centroids) for a, b in zip(old, current)):
                    raise ValueError("retained centroid coordinates differ from the scale unions")
                try:
                    distance = validate_euclidean_observation({
                        "status": status, "raw_status": raw_status, "value": distance,
                        "units": observation.get("units"),
                    })
                    audited_distance = math.dist(*current_centroids)
                    if not math.isclose(distance, audited_distance, rel_tol=1e-12, abs_tol=1e-9):
                        raise ValueError("cached distance differs from the scale-union centroids")
                    audit = {"union_centroids_m": current_centroids, "centroid_distance_m": audited_distance,
                             "distance_residual_m": distance - audited_distance,
                             "absolute_tolerance_m": 1e-9, "relative_tolerance": 1e-12}
                    ell, q, weight = geometry_scaled_response(distance, scale_a["rho2_m2"], scale_b["rho2_m2"])
                except ValueError as exc:
                    status, reason = "invalid", str(exc)
        elif status == "computed":
            status, reason = raw_status or "not_available", "raw Euclidean distance is not computed"
        if status != "computed" and not reason:
            reason = "Euclidean input is unavailable"
        # Preserve malformed raw values as audit text while keeping strict JSON numeric fields valid.
        raw_value = observation.get("value")
        numeric_distance = (not isinstance(raw_value, bool) and isinstance(raw_value, (int, float))
                            and math.isfinite(raw_value) and raw_value >= 0)
        raw_reading = {"value": repr(raw_value) if isinstance(raw_value, float) and not math.isfinite(raw_value) else raw_value,
                       "units": observation.get("units"), "status": raw_status}
        source_ids = tuple(output.source_ids)
        if status == "computed" and (len(centroid_refs) != 2 or not source_ids):
            raise ValueError("computed Euclidean output is missing source or centroid lineage")
        ref = output.derived_from[0] if output.derived_from else None
        if (len(output.derived_from) != 1 or ref.package_id != "group-walk-distance"
                or not ref.output_identity or ref.target_identity != pair_id or ref.channel != output.channel):
            raise ValueError("Euclidean output must retain its complete matching source-channel address")
        rows.append({
            "pair_id": pair_id,
            "group_a_id": group_a,
            "group_b_id": group_b,
            "channel": "euclidean_distance",
            "formula_version": FORMULA_VERSION,
            "status": status,
            "raw_status": raw_status,
            "reason": reason,
            "distance_m": distance if numeric_distance and observation.get("units") == "m" else None,
            "raw_distance_reading": raw_reading,
            "rho_a_m": scale_a["rho_m"],
            "rho_b_m": scale_b["rho_m"],
            "rho2_a_m2": scale_a["rho2_m2"],
            "rho2_b_m2": scale_b["rho2_m2"],
            "ell_m": ell,
            "q": q,
            "w": weight,
            "source_ids": list(source_ids),
            "centroid_refs": list(centroid_refs),
            "geometry_audit": audit,
            "lineage": {
                "distance_channel_ref": _plain_reference(ref) if ref is not None else None,
                "source_envelope_identity": source.cache_identity["identity"],
                "source_cache_identity": dict(source.cache_identity),
                "dependency_fingerprints": dict(output.provenance.get("dependency_fingerprints", {})),
                "distance_algorithm_version": output.provenance.get("distance_algorithm_version"),
                "distance_schema_version": output.provenance.get("distance_schema_version"),
                "explanation": output.explanation,
            },
        })
    if len(rows) != 666:
        raise ValueError("decay result must preserve all 666 Euclidean pair targets")
    return sorted(rows, key=lambda row: row["pair_id"])


def reciprocal_response(q: float) -> float:
    """Map finite nonnegative size-relative distance to the opt-in reciprocal trial."""
    if not math.isfinite(q) or q < 0:
        raise ValueError("dimensionless distance must be finite and nonnegative")
    return 1.0 / (1.0 + q)


def sqrt_reciprocal_response(q: float) -> float:
    """Map finite nonnegative q to the opt-in square-root reciprocal trial."""
    if not math.isfinite(q) or q < 0:
        raise ValueError("dimensionless distance must be finite and nonnegative")
    return 1.0 / math.sqrt(1.0 + q)


def power_06_response(q: float) -> float:
    """Map finite nonnegative q to the fixed exponent-0.6 reciprocal trial."""
    if not math.isfinite(q) or q < 0:
        raise ValueError("dimensionless distance must be finite and nonnegative")
    return (1.0 + q) ** -0.6


def build_comparison_rows(inputs: ExperimentInputs, *, compare_sqrt_reciprocal: bool = False,
                          compare_power_06: bool = False) -> list[dict[str, Any]]:
    """Append opt-in responses while retaining every validated exponential field."""
    # Reuse the existing status and provenance gate before adding a second response.
    rows = [{**row,
             "w_reciprocal": reciprocal_response(row["q"]) if row["status"] == "computed" else None,
             "reciprocal_formula_version": RECIPROCAL_FORMULA_VERSION}
            for row in build_decay_rows(inputs)]
    if compare_sqrt_reciprocal or compare_power_06:
        # A third curve uses the same gate and q; it does not reinterpret unavailable input as zero.
        for row in rows:
            row["w_sqrt_reciprocal"] = sqrt_reciprocal_response(row["q"]) if row["status"] == "computed" else None
            row["sqrt_reciprocal_formula_version"] = SQRT_RECIPROCAL_FORMULA_VERSION
    if compare_power_06:
        for row in rows:
            row["w_power_06"] = power_06_response(row["q"]) if row["status"] == "computed" else None
            row["power_06_formula_version"] = POWER_06_FORMULA_VERSION
    return rows


def _write_overview(inputs: ExperimentInputs, rows: list[dict[str, Any]], output_dir: Path,
                    *, compare_reciprocal: bool = False, compare_sqrt_reciprocal: bool = False,
                    compare_power_06: bool = False) -> None:
    """Color actual unions on one absolute scale with the selected trial plans."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from matplotlib.path import Path as PlotPath
    from matplotlib.patches import PathPatch
    from shapely.geometry.polygon import orient

    compare_sqrt_reciprocal = compare_sqrt_reciprocal or compare_power_06
    compare_reciprocal = compare_reciprocal or compare_sqrt_reciprocal
    group_ids = sorted(inputs.geometries)
    source = group_ids[0]
    selected = {row["group_b_id"] if row["group_a_id"] == source else row["group_a_id"]: row
                for row in rows if source in (row["group_a_id"], row["group_b_id"])}
    if compare_reciprocal:
        figure, (axes, reciprocal_axes, response_axes) = plt.subplots(
            1, 3, figsize=(20, 7.5), gridspec_kw={"width_ratios": (1, 1, 0.65)}, constrained_layout=True)
        plans = ((axes, "w", "Exponential: exp(-q)"),
                 (reciprocal_axes, "w_reciprocal", "Reciprocal: 1 / (1 + q)"))
        if compare_sqrt_reciprocal:
            plans = ((axes, "w_reciprocal", "Reciprocal: 1 / (1 + q)"),
                     (reciprocal_axes, "w_sqrt_reciprocal", "Square-root reciprocal: 1 / sqrt(1 + q)"))
        if compare_power_06:
            plans = ((axes, "w_sqrt_reciprocal", "Exponent 0.5: 1 / sqrt(1 + q)"),
                     (reciprocal_axes, "w_power_06", "Exponent 0.6: (1 + q)^(-0.6)"))
    else:
        figure, (axes, response_axes) = plt.subplots(1, 2, figsize=(15, 8),
                                                    gridspec_kw={"width_ratios": (2, 1)}, constrained_layout=True)
        plans = ((axes, "w", "Source 01 (red hatch); 36 target unions"),)
    colormap = plt.get_cmap("cividis")
    for axes, response_field, title in plans:
        for index, group_id in enumerate(group_ids, 1):
            geometry = inputs.geometries[group_id]
            if geometry is None:
                continue
            row = selected.get(group_id)
            weight = row[response_field] if row else None
            fill = "white" if group_id == source else colormap(weight) if weight is not None else "#cccccc"
            polygons = tuple(geometry.geoms) if geometry.geom_type == "MultiPolygon" else (geometry,)
            for polygon in polygons:
                vertices, codes = [], []
                # Opposite ring winding preserves real voids under the nonzero fill rule.
                polygon = orient(polygon, sign=1.0)
                for ring in (polygon.exterior, *polygon.interiors):
                    coordinates = list(ring.coords)
                    vertices.extend(coordinates)
                    codes.extend([PlotPath.MOVETO] + [PlotPath.LINETO] * (len(coordinates) - 2) + [PlotPath.CLOSEPOLY])
                axes.add_patch(PathPatch(PlotPath(vertices, codes), facecolor=fill,
                                         edgecolor="#c62828" if group_id == source else "#777777",
                                         linewidth=2 if group_id == source else 0.5,
                                         hatch="///" if group_id == source else None))
            center = inputs.scales[group_id]["centroid"]
            axes.text(*center, f"{index:02d}", ha="center", va="center", fontsize=8,
                      color="#c62828" if group_id == source else "white",
                      bbox={"facecolor": "white" if group_id == source else "#333333", "alpha": 0.8, "pad": 1, "edgecolor": "none"})
        axes.autoscale_view()
        axes.margins(0.05)
        axes.set_aspect("equal", adjustable="box")
        axes.set_xlabel("Analysis-plane X (m)")
        axes.set_ylabel("Analysis-plane Y (m)")
        axes.set_title(title)
    colorbar = figure.colorbar(ScalarMappable(norm=Normalize(0, 1), cmap=colormap),
                              ax=[plan[0] for plan in plans] if compare_reciprocal else axes,
                              fraction=0.035, pad=0.02)
    colorbar.set_label("Absolute response w [0, 1]")
    computed = [row for row in rows if row["w"] is not None]
    if compare_reciprocal:
        # Shared q separates the amplitude choice from geometry and scale changes.
        curves = (("w", "exp(-q)", "#006ba4"), ("w_reciprocal", "1 / (1 + q)", "#d97800"))
        if compare_sqrt_reciprocal:
            curves += (("w_sqrt_reciprocal", "1 / sqrt(1 + q)", "#208040"),)
        if compare_power_06:
            curves += (("w_power_06", "(1 + q)^(-0.6)", "#7b2cbf"),)
        for field, label, color in curves:
            response_axes.scatter([row["q"] for row in computed], [row[field] for row in computed],
                                  c=color, s=13, alpha=0.7, label=label)
        response_axes.legend()
        response_axes.set_xlabel("Size-relative distance q = d_E / ell")
    else:
        response_axes.scatter([row["distance_m"] for row in computed], [row["w"] for row in computed],
                              c=[row["w"] for row in computed], cmap=colormap, vmin=0, vmax=1, s=13, alpha=0.8)
        response_axes.set_xlabel("Cached centroid distance d_E (m)")
    response_axes.set(ylabel="Geometry-scaled response w", title="All 666 retained pairs", ylim=(0, 1))
    response_axes.grid(color="#dddddd", linewidth=0.45)
    title = ("Real IFC comparison: same source 01, rho, ell and q; absolute [0,1] colors\n"
             if compare_reciprocal else "Real IFC experiment: w = exp(-d_E / sqrt(rho_g^2 + rho_h^2))\n")
    figure.suptitle(title + source + " | not calibrated; no path input", fontsize=12, parse_math=False)
    figure.savefig(output_dir / "overview.svg", format="svg")
    figure.savefig(output_dir / "overview.png", dpi=180, format="png")
    plt.close(figure)


def _write_html(inputs: ExperimentInputs, rows: list[dict[str, Any]], output_dir: Path,
                *, compare_reciprocal: bool = False, compare_sqrt_reciprocal: bool = False,
                compare_power_06: bool = False) -> None:
    """Write the actual-union viewer with explicit opt-in curve choices."""
    from matplotlib import colormaps
    from matplotlib.colors import to_hex

    compare_sqrt_reciprocal = compare_sqrt_reciprocal or compare_power_06
    compare_reciprocal = compare_reciprocal or compare_sqrt_reciprocal
    options, paths = [], []
    for index, group_id in enumerate(sorted(inputs.geometries), 1):
        label = f"{index:02d} | {group_id}"
        options.append(f'<option value="{html.escape(group_id)}">{html.escape(label)}</option>')
        geometry = inputs.geometries[group_id]
        if geometry is None:
            continue
        polygons = tuple(geometry.geoms) if geometry.geom_type == "MultiPolygon" else (geometry,)
        commands = []
        for polygon in polygons:
            for ring in (polygon.exterior, *polygon.interiors):
                coordinates = list(ring.coords)
                commands.append("M" + " L".join(f"{x:.12g},{-y:.12g}" for x, y in coordinates) + " Z")
        center_x, center_y = inputs.scales[group_id]["centroid"]
        paths.append(f'<g data-group="{html.escape(group_id)}" tabindex="0" role="button" '
                     f'aria-label="Select target {html.escape(label)}">'
                     f'<path d="{" ".join(commands)}" fill-rule="evenodd"><title>{html.escape(label)}</title></path>'
                     f'<text x="{center_x:.12g}" y="{-center_y:.12g}">{index:02d}</text></g>')
    bounds = [shape.bounds for shape in inputs.geometries.values() if shape is not None]
    xmin, ymin = min(b[0] for b in bounds), min(b[1] for b in bounds)
    xmax, ymax = max(b[2] for b in bounds), max(b[3] for b in bounds)
    margin = max(xmax - xmin, ymax - ymin) * 0.04
    viewbox = f"{xmin-margin} {-ymax-margin} {xmax-xmin+2*margin} {ymax-ymin+2*margin}"
    table_rows = []
    for row in rows:
        pair_id = html.escape(row["pair_id"])
        values = (row["group_a_id"], row["group_b_id"], row["status"], row["distance_m"],
                  row["rho_a_m"], row["rho_b_m"], row["ell_m"], row["q"], row["w"])
        if compare_reciprocal:
            values += (row["w_reciprocal"],)
        if compare_sqrt_reciprocal:
            values += (row["w_sqrt_reciprocal"],)
        if compare_power_06:
            values += (row["w_power_06"],)
        cells = "".join(f"<td>{html.escape('' if value is None else str(value))}</td>" for value in values)
        table_rows.append(f'<tr id="{pair_id}"><td><a href="#{pair_id}" data-pair="{pair_id}">{pair_id}</a></td>{cells}</tr>')
    payload = json.dumps(_json_safe(rows), ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    colors = json.dumps([to_hex(colormaps["cividis"](index / 255)) for index in range(256)])
    document = r"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
body{font:14px/1.45 system-ui,sans-serif;margin:24px;color:#202124}h1{font-size:22px;margin:0 0 8px}
p{max-width:1050px}.links{display:flex;gap:16px;margin:12px 0}select,input{font:inherit;padding:6px;margin:6px}
#plan{display:block;width:100%;max-width:1100px;height:65vh;border:1px solid #ddd;background:#fafafa}
#plan g[data-group]{outline:none} /* The blue focused-path stroke is the keyboard focus indicator. */
#plan g[data-group] path{stroke:#777;stroke-width:.015;cursor:pointer}#plan text{font-size:.2px;text-anchor:middle;dominant-baseline:middle;fill:white;paint-order:stroke;stroke:#333;stroke-width:.045;pointer-events:none}
#plan g:focus path{stroke:#087fce;stroke-width:.08}#readout{white-space:pre-wrap;min-height:5em;background:#f4f5f6;padding:10px}
.legend{display:flex;gap:10px;align-items:center;max-width:650px;margin:8px}.gradient{height:16px;flex:1;background:linear-gradient(to right,__GRADIENT__)}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid #ddd;padding:5px 7px;text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:#f4f5f6}.table-wrap{overflow:auto;max-height:60vh}tr:target{background:#fff4bf}
</style>
<h1>__HEADING__</h1>
<p>Choose a source; its 36 target unions use the same absolute w scale. Red hatch marks the source (self response is N/A); gray means unavailable. Click or focus a target to inspect d_E, q and w. Click any pair below to select its endpoints. Labels use the source selector's stable 01–37 index.</p>
<p id="formula">w = exp(-d_E / sqrt(rho_g² + rho_h²)), using area-uniform RMS radii of actual projected unions. Overlap counts once and holes stay empty. This is an uncalibrated experiment, not a probability or production rule. Path values are not used. Plan coordinates are metres on the retained camera analysis plane.</p>
__CURVE_NOTES__
<nav class="links"><a href="overview.png">PNG</a><a href="overview.svg">SVG</a><a href="decay_rows.csv">CSV</a><a href="decay_rows.json">JSON</a><a href="run_manifest.json">Manifest</a></nav>
<label for="source">Source group</label><select id="source">__OPTIONS__</select>
__CURVE_SELECTOR__
<div class="legend"><span>0</span><div class="gradient"></div><span id="legend-response">1 (absolute w)</span><span>red hatch: source</span></div>
<svg id="plan" viewBox="__VIEWBOX__" aria-label="Actual retained furniture unions on the camera analysis plane">
<defs><pattern id="source-hatch" width=".12" height=".12" patternUnits="userSpaceOnUse"><rect width=".12" height=".12" fill="white"/><path d="M0,0 L.12,.12" stroke="#c62828" stroke-width=".025"/></pattern></defs>__PATHS__</svg>
<pre id="readout" aria-live="polite"></pre>
<label for="filter">Filter all 666 pairs</label><input id="filter" type="search" placeholder="Pair or group ID">
<div class="table-wrap"><table id="rows"><thead><tr><th>Pair anchor</th><th>Group A</th><th>Group B</th><th>Status</th><th>d_E (m)</th><th>rho_A (m)</th><th>rho_B (m)</th><th>ell (m)</th><th>q</th>__RESPONSE_HEADERS__</tr></thead><tbody>__ROWS__</tbody></table></div>
<script>
const rows=__DATA__, colors=__COLORS__, source=document.getElementById('source'), readout=document.getElementById('readout');
const groups=[...document.querySelectorAll('#plan g[data-group]')], byPair=new Map(rows.map(r=>[r.pair_id,r]));
const curve=document.getElementById('curve');
let selectedTarget=null;
/** Find the retained unordered pair for the selected source and target. */
function pairFor(target){return rows.find(r=>(r.group_a_id===source.value&&r.group_b_id===target)||(r.group_b_id===source.value&&r.group_a_id===target));}
/** Show original distance, scale and continuous response together. */
function describe(target){
  const r=pairFor(target);
  if(!r)return target+' | source group; self response N/A';
  return r.pair_id+'\n'+source.value+' -> '+target+'\nstatus='+r.status+' | d_E='+r.distance_m+' m | ell='+r.ell_m+' m | q='+r.q+(curve?' | w_exp='+r.w+' | w_reciprocal='+r.w_reciprocal+('w_sqrt_reciprocal' in r?' | w_sqrt_reciprocal='+r.w_sqrt_reciprocal:'')+('w_power_06' in r?' | w_power_06='+r.w_power_06:'')+' | displayed='+curve.options[curve.selectedIndex].text:' | w='+r.w)+(r.reason?' | '+r.reason:'');
}
/** Apply the same absolute color scale after every source selection. */
function render(){
  const field=curve?curve.value:'w';
  if(curve){
    document.getElementById('formula').textContent=field==='w_power_06'?'Displayed: w_power_06 = (1 + q)^(-0.6)':field==='w_sqrt_reciprocal'?'Displayed: w_sqrt_reciprocal = 1 / sqrt(1 + q)':field==='w_reciprocal'?'Displayed: w_reciprocal = 1 / (1 + q)':'Displayed: w_exp = exp(-q)';
    const version=document.getElementById('formula-version');
    if(version)version.textContent='Formula version: '+curve.options[curve.selectedIndex].dataset.formulaVersion;
    document.getElementById('legend-response').textContent='1 (absolute '+(field==='w'?'w_exp':field)+')';
  }
  for(const g of groups){const id=g.dataset.group,p=g.querySelector('path'),r=pairFor(id);
    p.style.fill=id===source.value?'url(#source-hatch)':r&&r[field]!==null?colors[Math.round(r[field]*255)]:'#ccc';
    p.style.stroke=id===source.value?'#c62828':id===selectedTarget?'#087fce':'#777';
    p.style.strokeWidth=id===source.value||id===selectedTarget?'.07':'.015';
    p.querySelector('title').textContent=describe(id);
  }
  readout.textContent=selectedTarget?describe(selectedTarget):source.value+' | select one of 36 targets';
}
/** Follow a saved pair anchor to its two authenticated group endpoints. */
function selectPair(id){const r=byPair.get(id);if(r){source.value=r.group_a_id;selectedTarget=r.group_b_id;render();}}
source.addEventListener('change',()=>{selectedTarget=null;render();});
if(curve)curve.addEventListener('change',render);
for(const g of groups){const inspect=()=>{selectedTarget=g.dataset.group;render();};g.addEventListener('click',inspect);g.addEventListener('focus',inspect);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect();}});}
document.querySelectorAll('[data-pair]').forEach(a=>a.addEventListener('click',()=>selectPair(a.dataset.pair)));
window.addEventListener('hashchange',()=>selectPair(decodeURIComponent(location.hash.slice(1))));
document.getElementById('filter').addEventListener('input',e=>{const q=e.target.value.toLowerCase();for(const r of document.querySelectorAll('#rows tbody tr'))r.hidden=!r.textContent.toLowerCase().includes(q);});
render();selectPair(decodeURIComponent(location.hash.slice(1)));
</script></html>
"""
    power_option = (f'<option value="w_power_06" data-formula-version="{POWER_06_FORMULA_VERSION}" selected>Reciprocal power 0.6: (1 + q)^(-0.6)</option>'
                    if compare_power_06 else "")
    sqrt_selected = "" if compare_power_06 else " selected"
    sqrt_option = (f'<option value="w_sqrt_reciprocal" data-formula-version="{SQRT_RECIPROCAL_FORMULA_VERSION}"{sqrt_selected}>Square-root reciprocal: 1 / sqrt(1 + q)</option>'
                   if compare_sqrt_reciprocal else "")
    reciprocal_selected = "" if compare_sqrt_reciprocal else " selected"
    curve_selector = (f'<label for="curve">Displayed curve</label><select id="curve">{power_option}{sqrt_option}'
                      f'<option value="w_reciprocal" data-formula-version="{RECIPROCAL_FORMULA_VERSION}"{reciprocal_selected}>Reciprocal: 1 / (1 + q)</option>'
                      f'<option value="w" data-formula-version="{FORMULA_VERSION}">Exponential: exp(-q)</option></select>'
                      if compare_reciprocal else "")
    curve_notes = ("<p>Both curves use the same q = d_E / sqrt(rho_g² + rho_h²), from area-uniform RMS radii of the actual projected unions. "
                   "Overlap counts once; holes stay empty. q is size-relative distance, so ordering across different group sizes need not follow metres. "
                   "This is an uncalibrated comparison; a positive tail does not establish real interaction. No fixed positive floor or path input. "
                   "Plan coordinates are metres on the retained camera analysis plane.</p>" if compare_reciprocal else "")
    if compare_sqrt_reciprocal:
        curve_notes = curve_notes.replace("Both curves", "All three curves")
        curve_notes += "<p>The exponent 1/2 is a modeling choice for this reversible gradient trial.</p>"
    if compare_power_06:
        curve_notes = curve_notes.replace("All three curves", "All four curves")
        curve_notes += '<p>The fixed exponent 0.6 is a modeling choice for slightly stronger attenuation than 0.5.</p><p id="formula-version"></p>'
    response_headers = "<th>w_exp</th><th>w_reciprocal</th>" if compare_reciprocal else "<th>w</th>"
    if compare_sqrt_reciprocal:
        response_headers += "<th>w_sqrt_reciprocal</th>"
    if compare_power_06:
        response_headers += "<th>w_power_06</th>"
    for key, value in {"OPTIONS": "".join(options), "VIEWBOX": viewbox, "PATHS": "".join(paths),
                       "ROWS": "\n".join(table_rows), "DATA": payload, "COLORS": colors,
                       "TITLE": "Group distance decay comparison" if compare_reciprocal else "Group distance decay experiment",
                       "HEADING": ("Reciprocal power 0.6 vs 0.5 with all four curves | same real IFC" if compare_power_06 else
                                   "Square-root reciprocal vs reciprocal vs exponential | same real IFC" if compare_sqrt_reciprocal else
                                   "Reciprocal vs exponential | same real IFC" if compare_reciprocal else "Geometry-scaled Euclidean response | real IFC"),
                       "CURVE_SELECTOR": curve_selector, "CURVE_NOTES": curve_notes,
                       "RESPONSE_HEADERS": response_headers,
                       "GRADIENT": ",".join(json.loads(colors)[::17])}.items():
        document = document.replace("__" + key + "__", value)
    (output_dir / "index.html").write_text(document, encoding="utf-8")


def _write_csv(rows: list[dict[str, Any]], output_dir: Path, *, compare_reciprocal: bool = False,
               compare_sqrt_reciprocal: bool = False, compare_power_06: bool = False) -> None:
    """Write original fields and only opt-in comparison fields as strict CSV."""
    fields = CSV_FIELDS + (("w_reciprocal", "reciprocal_formula_version")
                           if compare_reciprocal or compare_sqrt_reciprocal or compare_power_06 else ())
    if compare_sqrt_reciprocal or compare_power_06:
        fields += ("w_sqrt_reciprocal", "sqrt_reciprocal_formula_version")
    if compare_power_06:
        fields += ("w_power_06", "power_06_formula_version")
    with (output_dir / "decay_rows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            record = dict(row)
            for field in ("raw_distance_reading", "source_ids", "centroid_refs", "geometry_audit", "lineage"):
                record[field] = json.dumps(record[field], ensure_ascii=False, allow_nan=False, sort_keys=True)
            writer.writerow({field: record.get(field) for field in fields})


def _json_safe(value: Any) -> Any:
    """Convert immutable nested records into strict JSON-compatible values."""
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite values cannot be serialized")
    return value


def run_experiment(output_dir: Path, *, bundle_path: Path = BUNDLE_PATH,
                   package_path: Path = PACKAGE_PATH, compare_reciprocal: bool = False,
                   compare_sqrt_reciprocal: bool = False, compare_power_06: bool = False) -> dict[str, Any]:
    """Replay exponential defaults or explicit same-input comparison modes."""
    output_dir = Path(output_dir).resolve()
    output_root = (ROOT / "outputs" / "design").resolve()
    if not output_dir.is_relative_to(output_root):
        raise ValueError("output directory must be under outputs/design in this workspace")
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    inputs = load_experiment_inputs(bundle_path=bundle_path, package_path=package_path)
    # The new standalone flag includes the prior curve without changing either older mode.
    compare_sqrt_reciprocal = compare_sqrt_reciprocal or compare_power_06
    compare_reciprocal = compare_reciprocal or compare_sqrt_reciprocal
    rows = (build_comparison_rows(inputs, compare_sqrt_reciprocal=compare_sqrt_reciprocal,
                                  compare_power_06=compare_power_06)
            if compare_reciprocal else build_decay_rows(inputs))
    comparison = ({"reciprocal_formula_version": RECIPROCAL_FORMULA_VERSION,
                   "reciprocal_formula": RECIPROCAL_FORMULA,
                   "default_curve": "reciprocal", "color_scale": [0, 1]}
                  if compare_reciprocal else {})
    if compare_sqrt_reciprocal:
        comparison.update(sqrt_reciprocal_formula_version=SQRT_RECIPROCAL_FORMULA_VERSION,
                          sqrt_reciprocal_formula=SQRT_RECIPROCAL_FORMULA,
                          default_curve="sqrt_reciprocal")
    if compare_power_06:
        comparison.update(power_06_formula_version=POWER_06_FORMULA_VERSION,
                          power_06_formula=POWER_06_FORMULA, power_06_exponent=0.6,
                          default_curve="power_06")
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_csv(rows, output_dir, compare_reciprocal=compare_reciprocal,
               compare_sqrt_reciprocal=compare_sqrt_reciprocal, compare_power_06=compare_power_06)
    (output_dir / "decay_rows.json").write_text(
        json.dumps(_json_safe({
            "schema": ("group-distance-decay-four-curve-rows/1" if compare_power_06 else
                       "group-distance-decay-three-curve-rows/1" if compare_sqrt_reciprocal else
                       "group-distance-decay-comparison-rows/1" if compare_reciprocal else "group-distance-decay-rows/1"),
            "formula_version": FORMULA_VERSION,
            "formula": FORMULA,
            **comparison,
            "distance_channel": "euclidean_distance",
            "rows": rows,
        }), indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_overview(inputs, rows, output_dir, compare_reciprocal=compare_reciprocal,
                    compare_sqrt_reciprocal=compare_sqrt_reciprocal, compare_power_06=compare_power_06)
    _write_html(inputs, rows, output_dir, compare_reciprocal=compare_reciprocal,
                compare_sqrt_reciprocal=compare_sqrt_reciprocal, compare_power_06=compare_power_06)
    statuses = Counter(row["status"] for row in rows)
    artifacts = ("decay_rows.csv", "decay_rows.json", "overview.svg", "overview.png", "index.html")
    manifest = {
        "schema": ("group-distance-decay-four-curve-run/1" if compare_power_06 else
                   "group-distance-decay-three-curve-run/1" if compare_sqrt_reciprocal else
                   "group-distance-decay-comparison-run/1" if compare_reciprocal else "group-distance-decay-run/1"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "formula_version": FORMULA_VERSION,
        "formula": FORMULA,
        **comparison,
        "interpretation": "continuous geometry-relative response; not calibrated and not a hard radius",
        "distance_channel": "euclidean_distance",
        "path_distance_used": False,
        "group_count": len(inputs.bundle.groups),
        "pair_count": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "package_id": inputs.package_id,
        "package_output_identity": inputs.output_identity,
        "package_freshness": inputs.package_freshness,
        "input_hashes": dict(inputs.input_hashes),
        "source_binding": dict(inputs.source_binding),
        "retained_bundle_path": str(Path(bundle_path).resolve()),
        "retained_package_path": str(Path(package_path).resolve()),
        "analysis_plane": _json_safe(inputs.bundle.analysis_plane),
        "query_context": _json_safe(inputs.bundle.query_context),
        "group_scales": _json_safe(inputs.scales),
        "default_source_group_id": sorted(inputs.scales)[0],
        "moment_definition": "rho^2 = trace(area-uniform covariance of the hole-aware projected union)",
        "scale_definition": "ell(g,h) = sqrt(rho_g^2 + rho_h^2)",
        "visualization": ("same-source exponent-0.5/exponent-0.6 union plans and all-four q scatter; HTML curve switch defaults to power 0.6; absolute [0,1] colors; all 666 pair anchors retained"
                          if compare_power_06 else
                          "same-source reciprocal/square-root reciprocal union plans and all-three q scatter; HTML curve switch defaults to square-root reciprocal; absolute [0,1] colors; all 666 pair anchors retained"
                          if compare_sqrt_reciprocal else
                          "same-source exponential/reciprocal union plans and q scatter; HTML curve switch defaults to reciprocal; absolute [0,1] colors; all 666 pair anchors retained"
                          if compare_reciprocal else "selected-source actual union plan; 36 targets use absolute w [0,1]; all 666 pair anchors retained"),
        "runner_sha256": file_hash(Path(__file__)),
        "artifact_hashes": {name: file_hash(output_dir / name) for name in artifacts},
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    """Run one pinned replay into a new workspace output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, default=BUNDLE_PATH)
    parser.add_argument("--package", type=Path, default=PACKAGE_PATH)
    parser.add_argument("--compare-reciprocal", action="store_true",
                        help="compare reciprocal 1/(1+q) with the unchanged exponential response")
    parser.add_argument("--compare-sqrt-reciprocal", action="store_true",
                        help="compare square-root reciprocal 1/sqrt(1+q) with both existing responses")
    parser.add_argument("--compare-power-06", action="store_true",
                        help="compare fixed power (1+q)^(-0.6) with all three existing responses")
    args = parser.parse_args()
    print(json.dumps(run_experiment(args.output_dir, bundle_path=args.bundle, package_path=args.package,
                                    compare_reciprocal=args.compare_reciprocal,
                                    compare_sqrt_reciprocal=args.compare_sqrt_reciprocal,
                                    compare_power_06=args.compare_power_06),
                     indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
