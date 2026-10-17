"""Run the private enclosure and domain handoff for one live Blender capture."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path
import sys

from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from adapters.blender_geometry import load_blender_neutral_scene
from features._analysis_domain_handoff import domain_handoff
from features.neutral_scene_views import _analysis_scene_view_with_semantic_enclosure


def tolerance_m2(value: object) -> float:
    """Convert a finite nonnegative square-millimetre UI value once."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise ValueError("residual tolerance must be a finite nonnegative number of mm²")
    return float(value) / 1_000_000


def evaluate(payload: dict) -> dict:
    """Evaluate actual captured geometry with the existing private B2 and handoff seams."""
    snapshot = payload["snapshot"]
    ids = [row["id"] for row in snapshot["objects"]]
    scene = load_blender_neutral_scene(snapshot, selected_ids=ids, roles=snapshot["roles"])
    plane = scene.context.analysis_plane
    frame = {"analysis_plane": plane, "units": "m", "datum_m": 0.0, "cut_height_m": 1.5}
    # The closed-leaf scenario is explicit authority for enclosure evidence only.
    request = frame | {"contact_distance_m": 1e-6, "aperture_area_budget_m2": 1e-6,
                       "aperture_residual_tolerance_m2": tolerance_m2(payload["tolerance_mm2"]),
                       "source_ifc_path": snapshot["identity"]["ifc_path"],
                       "source_project_global_id": snapshot["identity"]["project_global_id"],
                       "default_closed_authority": "B4 user-authorized closed door/window scenario; state not observed",
                       "exclude_override_authority": "B4 task-only structural/window/door enclosure; source exclusion retained"}
    b2 = _analysis_scene_view_with_semantic_enclosure(scene, request=request)["_analysis_view"]["b2_boundary_diagnostics"]["semantic_enclosure"]
    previous = payload.get("previous") or {}
    result = domain_handoff(scene, candidates=(), session_state=previous.get("session_state"),
                            action=payload.get("action"),
                            expected_session_revision=previous.get("session_revision"),
                            expected_source_revision=(previous.get("provenance") or {}).get("source_revision"),
                            frame_request=frame, b2=b2, b2_request=request)
    candidates = []
    for item in result["candidates"]:
        polygon = shape(item["outline"]) if item["outline"] else None
        candidates.append(item | {"area_m2": polygon.area if polygon else None,
                                  "holes": len(polygon.interiors) if polygon else None,
                                  "label_xy": list(polygon.representative_point().coords[0]) if polygon else None})
    # The UI receives the reducer's actual attempt/current state; no display-only activation.
    return {"session_state": result["session_state"], "session_revision": result["session_revision"],
            "provenance": result["provenance"], "attempt": result["attempt"], "current": result["current"],
            "candidates": candidates, "selected_candidate_id": result["selected_candidate_id"],
            "handoff_executed": result["analysis_domain"] is not None,
            "downstream": result["downstream"],
            "apertures": [{"id": item["id"], "area_m2": item["geometry"]["area_m2"],
                           "significant_residual": item["significant_residual"],
                           "affected_scope_ids": item["affected_scope_ids"]} for item in b2["apertures"]],
            "source_count": len(scene.source_objects), "geometry_count": len(scene.geometries),
            "source_identity": snapshot["identity"], "scenario": "default closed doors/windows; observed leaf states unknown",
            "tolerance_mm2": payload["tolerance_mm2"]}


def main() -> None:
    """Read one JSON request and write the bounded result for Blender."""
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.request.read_text(encoding="utf-8"))
    result = evaluate(payload)
    args.result.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(json.dumps({"candidates": len(result["candidates"]), "attempt": result["attempt"],
                      "current": result["current"], "handoff_executed": result["handoff_executed"]}))


if __name__ == "__main__":
    main()
