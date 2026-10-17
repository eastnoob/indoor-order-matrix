"""Check the B4 UI boundary against one captured, disposable live session."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

from shapely.geometry import shape

from run_live_domain import evaluate, tolerance_m2


def check(request_path: Path, output_path: Path) -> dict:
    """Exercise select, confirm, tolerance drift and source drift without bpy writes."""
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    initial = evaluate(payload)
    assert len(initial["candidates"]) == 5
    assert initial["current"]["status"] == "not_available"
    assert initial["selected_candidate_id"] is None
    assert sum(item["holes"] for item in initial["candidates"]) == 2
    for value in (-1, float("nan"), float("inf"), True):
        try:
            tolerance_m2(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid tolerance accepted: {value!r}")
    assert tolerance_m2(10) == 1e-5 and tolerance_m2(0) == 0

    # Each live polygon must survive the same derived mesh handoff exactly.
    from adapters.blender_geometry import load_blender_neutral_scene
    from features._analysis_domain_handoff import _inferred_mesh
    scene = load_blender_neutral_scene(payload["snapshot"],
                                       selected_ids=[row["id"] for row in payload["snapshot"]["objects"]],
                                       roles=payload["snapshot"]["roles"])
    for candidate in initial["candidates"]:
        _inferred_mesh(shape(candidate["outline"]), scene.context.analysis_plane,
                       candidate["version_id"], "disposable", "default")

    target = initial["candidates"][0]
    selected = evaluate(payload | {"previous": initial,
                                   "action": {"kind": "select", "candidate_version_id": target["version_id"]}})
    assert selected["attempt"]["status"] == "selected"
    assert selected["current"]["status"] == "not_available"
    provenance = selected["provenance"]
    action = {"kind": "confirm", "candidate_version_id": target["version_id"],
              "action_id": str(uuid.uuid4()), "actor": "disposable B4 self-check",
              "time": datetime.now(timezone.utc).isoformat(), "reason": "verify explicit UI handoff",
              "expected_session_revision": selected["session_revision"],
              "expected_source_revision": provenance["source_revision"],
              "expected_plane_identity": provenance["frame_id"],
              "expected_request_identity": provenance["request_id"],
              "expected_candidate_identity": target["identity"],
              "acknowledged_conflict_ids": []}
    confirmed = evaluate(payload | {"previous": selected, "action": action})
    assert confirmed["attempt"]["status"] == "accepted"
    assert confirmed["current"]["status"] == "active" and confirmed["handoff_executed"]
    strict = evaluate(payload | {"previous": confirmed, "tolerance_mm2": 0})
    assert strict["current"]["status"] == "not_available"
    assert any(item["id"] == "S3" and item["reason"] == "unresolved_local_aperture"
               for item in strict["candidates"])
    restored = evaluate(payload | {"previous": strict})
    assert restored["current"]["status"] == "not_available"
    changed = deepcopy(payload)
    changed["snapshot"]["objects"][0]["vertices"][0][0] += 0.0001
    changed["previous"] = confirmed
    drift = evaluate(changed)
    assert drift["current"]["status"] == "not_available"
    relinked = deepcopy(payload)
    relinked["snapshot"]["identity"]["ifc_path"] += ".relinked"
    relinked["previous"] = confirmed
    link_drift = evaluate(relinked)
    assert link_drift["current"]["status"] == "not_available"
    summary = {"live_source": payload["snapshot"]["identity"],
               "candidate_areas_m2": {item["id"]: item["area_m2"] for item in initial["candidates"]},
               "holes": {item["id"]: item["holes"] for item in initial["candidates"]},
               "projection_round_trip": "all_five_exact",
               "select": selected["attempt"], "confirm": confirmed["attempt"],
               "confirmed_current": confirmed["current"],
               "strict_current": strict["current"], "restored_current": restored["current"],
               "source_drift_current": drift["current"],
               "ifc_link_drift_current": link_drift["current"],
               "default_unconfirmed_current": initial["current"],
               "source_objects_in_disposable_scene": len(scene.source_objects)}
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    """Run the disposable check on an explicit captured request path."""
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_live_capture.py REQUEST_JSON RESULT_JSON")
    result = check(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({key: result[key] for key in ("projection_round_trip", "select", "confirm",
                                                      "confirmed_current", "strict_current", "source_drift_current")}))


if __name__ == "__main__":
    main()
