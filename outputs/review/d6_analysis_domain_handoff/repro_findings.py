"""Reproduce three bounded private handoff review findings on frozen code."""

import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from order_analyzer.features.neutral_scene_views import (  # noqa: E402
    _analysis_scene_view_with_domain_handoff as handoff,
    analysis_scene_view,
)
from order_analyzer.features.scene_contract import AnalysisDomain  # noqa: E402
from order_analyzer.test.test_neutral_scene_analysis_regression import (  # noqa: E402
    _enclosure_request,
    _enclosure_scene,
    _handoff_confirm,
    _handoff_frame,
    _neutral_scene,
)

scene = _neutral_scene()
start = handoff(scene, frame_request=_handoff_frame(scene))
candidate = start["candidates"][0]
forged = {
    "revision": 1,
    "current_version_id": candidate["version_id"],
    "current_binding": {
        "source_revision": start["provenance"]["source_revision"],
        "frame_id": start["provenance"]["frame_id"],
        "request_id": start["provenance"]["request_id"],
        "candidate_identity": candidate["identity"],
    },
    "events": [],
}
without_confirmation = handoff(scene, frame_request=_handoff_frame(scene), session_state=forged)
assert without_confirmation["current"]["status"] == "active"
assert not without_confirmation["session_state"]["events"]

scene = _enclosure_scene()
request = _enclosure_request(scene)
frame = _handoff_frame(scene)
start = handoff(scene, frame_request=frame, b2_request=request)
inferred = next(item for item in start["candidates"] if item["source"] == "inferred")
active = handoff(
    scene, frame_request=frame, b2_request=request, session_state=start["session_state"],
    action=_handoff_confirm(start, inferred["version_id"]), expected_session_revision=0,
    expected_source_revision=start["provenance"]["source_revision"],
)
authored = AnalysisDomain(
    id="later-authored", geometry_refs=("furniture",), source_id=None,
    selection_method="explicit",
)
later = handoff(
    scene, frame_request=frame, b2_request=request, session_state=active["session_state"],
    candidates=({"analysis_domain": authored},),
)
assert later["current"]["status"] == "active"
assert later["analysis_domain"] is not None

base = _neutral_scene()
scene = replace(
    base, analysis_domain=None,
    source_objects=(replace(base.source_objects[0], source_id="table-src"),) + base.source_objects[1:],
)
authored = AnalysisDomain(
    id="table-domain", geometry_refs=("mesh_left",), source_id="table-src",
    selection_method="explicit",
)
start = handoff(scene, frame_request=_handoff_frame(scene), candidates=({"analysis_domain": authored},))
active = handoff(
    scene, frame_request=_handoff_frame(scene), candidates=({"analysis_domain": authored},),
    session_state=start["session_state"], action=_handoff_confirm(start, authored.id),
    expected_session_revision=0, expected_source_revision=start["provenance"]["source_revision"],
)
ordinary_ids = {item["id"] for item in analysis_scene_view(scene)["physical_occupancy"]}
handoff_ids = {item["id"] for item in active["preview"]["physical_occupancy"]}
assert active["current"]["status"] == "active" and "left_table" in ordinary_ids - handoff_ids

print(json.dumps({
    "unconfirmed_handoff": without_confirmation["current"]["status"],
    "introduced_conflict_handoff": later["current"]["status"],
    "dropped_occupancy_ids": sorted(ordinary_ids - handoff_ids),
}, sort_keys=True))
