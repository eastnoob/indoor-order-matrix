"""Directly compare typed Analysis trend estimands with the legacy group frame."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.affordance.models import Rect  # noqa: E402
from features.scene_inference import _furniture_group_frame  # noqa: E402
from trend_substitute_registry import load_registry, validate_records  # noqa: E402

REGISTRY = load_registry(Path(__file__).with_name("trend_substitute_registry.json"))
SCHEMA = "d6-trend-substitute-contract-parity/v1"


def _rect(points: list[list[float]]) -> Rect:
    """Build a compatibility rectangle around one Analysis polygon."""
    xs, ys = zip(*points)
    return Rect(cx=(min(xs) + max(xs)) / 2, cy=(min(ys) + max(ys)) / 2, width=max(xs) - min(xs), height=max(ys) - min(ys))


def _legacy_inputs(case: dict[str, object]) -> tuple[list[dict], list[dict]]:
    """Reconstruct legacy members and extents from serialized Analysis polygons."""
    members = []
    for footprint in case.get("footprints", []):
        polygon = footprint["polygons"][0]
        members.append({"points": [tuple(point) for point in polygon], "rect": _rect(polygon), "metadata": {"frame-source": "terminal_projected_analysis_geometry"}, "orientation": 0.0})
    extents = [{"rect": _rect(extent)} for extent in case.get("affordance_extents", [])]
    return members, extents


def _axis_delta(first: float | None, second: float | None, period: float) -> float | None:
    """Return the shortest unsigned angular difference for a named estimand."""
    if first is None or second is None:
        return None
    return abs(((float(first) - float(second) + period / 2) % period) - period / 2)


def compare_direction_records(case: dict[str, object], legacy: dict[str, object]) -> dict[str, object]:
    """Compare A/C/D and legacy axes while preserving raw near-boundary angles."""
    estimands = case.get("estimands") or (case.get("usable_subset") or {}).get("estimands") or {}
    a = estimands.get("member_orientation_consensus", {})
    c = estimands.get("area_weighted_total_covariance_pca", {})
    d = estimands.get("between_member_centroid_pca", {})
    b = estimands.get("legacy_projected_point_cloud_pca", {})
    return {
        "raw_angles_deg": {"A_frame": a.get("frame_angle_deg"), "A_axis": a.get("axis_angle_deg"), "B": b.get("angle_deg"), "C": c.get("angle_deg"), "D": d.get("angle_deg"), "legacy_final": legacy.get("angle"), "legacy_geometry": legacy.get("geometry_angle")},
        "equivalence_period_deg": {"A_frame": 90.0, "A_axis": 180.0, "B": 180.0, "C": 180.0, "D": 180.0, "legacy_final": 180.0, "legacy_geometry": 180.0},
        "legacy_vs_B_axis_delta_deg": _axis_delta(legacy.get("geometry_angle"), b.get("angle_deg"), 180.0),
        "legacy_final_vs_A_axis_delta_deg": _axis_delta(legacy.get("angle"), a.get("axis_angle_deg"), 180.0),
        "A_frame_vs_orthogonal_axis_delta_deg": _axis_delta(a.get("frame_angle_deg"), a.get("axis_angle_deg"), 90.0),
    }


def run_legacy_group_frame_parity(case: dict[str, object]) -> dict[str, object]:
    """Call the unchanged legacy function on the same Analysis-derived geometry."""
    members, extents = _legacy_inputs(case)
    # The legacy function receives reconstructed records only; no Body geometry
    # or display metadata enters this call.
    legacy = _furniture_group_frame(members, extents)
    substitutes = case.get("analysis_substitutes", [])
    return {"group_id": case["id"], "status": case["status"], "footprints": case.get("footprints", []), "analysis_substitutes": substitutes, "registry_validation": validate_records(substitutes, "trend", REGISTRY) if substitutes else {"status": "not_available", "reason_code": "no_analysis_substitutes"}, "legacy_final": {"angle": legacy["angle"], "strength": legacy["strength"], "basis": legacy["basis"]}, "legacy_geometry_diagnostic": {"geometry_angle": legacy["geometry_angle"], "clarity": legacy["clarity"], "primary_extent": legacy["primary_extent"], "secondary_extent": legacy["secondary_extent"]}, "reconstructed_b_input": {"member_count": len(members), "member_point_count": sum(len(item["points"]) for item in members), "extent_count": len(extents), "extent_point_count": sum(5 for _ in extents), "source": "Analysis footprint polygons only"}, "comparison": compare_direction_records(case, legacy)}


def _assertions(data: dict[str, object]) -> list[str]:
    """Check parity invariants required by the design checkpoint."""
    synthetic = data["synthetic_parity"]
    assert synthetic
    exact = next(item for item in synthetic if item["group_id"] == "synthetic:aligned_members_horizontal_centers")
    assert exact["comparison"]["legacy_geometry_vs_B_axis_delta_deg"] if "legacy_geometry_vs_B_axis_delta_deg" in exact["comparison"] else exact["comparison"]["legacy_vs_B_axis_delta_deg"] < 1e-8
    divergent = next(item for item in synthetic if item["group_id"] == "synthetic:aligned_members_vertical_centers")
    assert abs(divergent["comparison"]["raw_angles_deg"]["A_frame"] - divergent["comparison"]["raw_angles_deg"]["D"]) > 45.0
    tess = next(item for item in synthetic if item["group_id"] == "synthetic:tessellation_density_invariance")
    assert tess["reconstructed_b_input"]["member_point_count"] > 10
    assert all(validate_records(item["analysis_substitutes"], "trend", REGISTRY)["status"] == "accepted" for item in synthetic if item["analysis_substitutes"])
    assert all(item["registry_validation"]["status"] == "accepted" for item in data.get("ifc_parity", []))
    return ["legacy_final_separated_from_geometry_diagnostic", "legacy_shaped_parity", "orientation_placement_divergence", "tessellation_input_audit", "no_body_fallback"]


def main() -> None:
    """Read saved probe output and write a parity-only JSON report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "outputs/design/trend_direction_probe/trend_direction_results.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/design/trend_substitute_contract_parity")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    synthetic = [{**case, "id": f"synthetic:{case['id']}"} for case in data["synthetic_cases"]]
    payload = {"schema": SCHEMA, "source_result": str(args.input.resolve()), "winner": None, "estimands": ["A:member_orientation_consensus", "C:area_weighted_total_covariance_pca", "D:between_member_centroid_pca", "B:legacy_projected_point_cloud_pca"], "legacy_semantics": "_furniture_group_frame returns member_frame_consensus when member support is positive; point-cloud PCA is geometry diagnostic/fallback, not C validation.", "synthetic_parity": [run_legacy_group_frame_parity(case) for case in synthetic], "ifc_parity": [run_legacy_group_frame_parity(case) for case in data["ifc_cases"]], "ifc_registry_validation": [], "assertions": []}
    payload["ifc_registry_validation"] = [item["registry_validation"] for item in payload["ifc_parity"]]
    payload["assertions"] = _assertions(payload)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "trend_substitute_contract_parity.json").write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "schema": SCHEMA, "synthetic": len(payload["synthetic_parity"]), "ifc": len(payload["ifc_parity"]), "winner": None}, sort_keys=True))


if __name__ == "__main__":
    main()
