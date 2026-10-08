"""Check the three repaired handoff failures and their nearby valid controls."""

import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from order_analyzer.features.affordance.models import Rect  # noqa: E402
from order_analyzer.features.neutral_scene_views import (  # noqa: E402
    _analysis_scene_view_with_domain_handoff as handoff,
    analysis_scene_view,
)
from order_analyzer.features.scene_contract import AnalysisDomain  # noqa: E402
from order_analyzer.test.test_neutral_scene_analysis_regression import (  # noqa: E402
    _enclosure_request, _enclosure_scene, _handoff_confirm, _handoff_frame,
    _mesh, _neutral_scene,
)

scene = _neutral_scene()
frame = _handoff_frame(scene)
start = handoff(scene, frame_request=frame)
candidate = start["candidates"][0]
forged = {
    "revision": 1, "current_version_id": candidate["version_id"],
    "current_binding": {
        "source_revision": start["provenance"]["source_revision"],
        "frame_id": start["provenance"]["frame_id"],
        "request_id": start["provenance"]["request_id"],
        "candidate_identity": candidate["identity"],
        "acknowledged_conflicts": [],
    },
    "conflict": False, "invalidated": False, "events": [],
}
denied = handoff(scene, frame_request=frame, session_state=forged)
assert denied["attempt"]["reason"] == "inconsistent_session_state"
assert denied["current"]["status"] == "not_available" and denied["analysis_domain"] is None
active = handoff(
    scene, frame_request=frame, session_state=start["session_state"],
    action=_handoff_confirm(start, candidate["version_id"]), expected_session_revision=0,
    expected_source_revision=start["provenance"]["source_revision"],
)
assert active["current"]["status"] == "active"
bad_binding = active["session_state"] | {"current_binding": forged["current_binding"] | {
    "candidate_identity": "changed"}}
denied_binding = handoff(scene, frame_request=frame, session_state=bad_binding)
assert denied_binding["attempt"]["reason"] == "inconsistent_session_state"

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
candidates = ({"analysis_domain": authored},)
later = handoff(
    scene, frame_request=frame, b2_request=request, session_state=active["session_state"],
    candidates=candidates,
)
assert later["current"]["status"] == "not_available" and later["analysis_domain"] is None
assert later["session_revision"] == active["session_revision"] + 1
stale = handoff(
    scene, frame_request=frame, b2_request=request, session_state=later["session_state"],
    candidates=candidates,
    action=_handoff_confirm(active, inferred["version_id"], action_id="stale-review",
                            acknowledged_conflict_ids=[authored.id]),
    expected_session_revision=active["session_revision"],
    expected_source_revision=active["provenance"]["source_revision"],
)
assert stale["attempt"]["reason"] == "stale_session_revision"
fresh = handoff(
    scene, frame_request=frame, b2_request=request, session_state=later["session_state"],
    candidates=candidates,
    action=_handoff_confirm(later, inferred["version_id"], action_id="fresh-review",
                            acknowledged_conflict_ids=[authored.id]),
    expected_session_revision=later["session_revision"],
    expected_source_revision=later["provenance"]["source_revision"],
)
assert fresh["current"]["status"] == "active" and fresh["analysis_domain"] is not None

equal_scene = replace(scene, geometries=scene.geometries + (
    _mesh("equal-scope-review", Rect(cx=3, cy=3, width=6, height=6)),))
equal_request = _enclosure_request(equal_scene)
equal_frame = _handoff_frame(equal_scene)
equal_start = handoff(equal_scene, frame_request=equal_frame, b2_request=equal_request)
equal_inferred = equal_start["candidates"][0]
equal_active = handoff(
    equal_scene, frame_request=equal_frame, b2_request=equal_request,
    session_state=equal_start["session_state"],
    action=_handoff_confirm(equal_start, equal_inferred["version_id"]),
    expected_session_revision=0,
    expected_source_revision=equal_start["provenance"]["source_revision"],
)
equal_authored = AnalysisDomain(
    id="equal-authored-review", geometry_refs=("equal-scope-review",),
    source_id=None, selection_method="explicit",
)
equal_later = handoff(
    equal_scene, frame_request=equal_frame, b2_request=equal_request,
    session_state=equal_active["session_state"],
    candidates=({"analysis_domain": equal_authored},),
)
assert equal_later["current"]["status"] == "active"
assert equal_later["session_revision"] == equal_active["session_revision"]

base = _neutral_scene()
scene = replace(
    base, analysis_domain=None,
    source_objects=(replace(base.source_objects[0], source_id="table-src"),) + base.source_objects[1:],
)
facts = scene.to_dict()
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
assert active["current"]["status"] == "active" and "left_table" in ordinary_ids & handoff_ids
assert active["analysis_domain"].source_id == "table-src" and scene.to_dict() == facts
slab = _neutral_scene()
slab_start = handoff(slab, frame_request=_handoff_frame(slab))
slab_active = handoff(
    slab, frame_request=_handoff_frame(slab), session_state=slab_start["session_state"],
    action=_handoff_confirm(slab_start, "domain_room"), expected_session_revision=0,
    expected_source_revision=slab_start["provenance"]["source_revision"],
)
slab_ids = {item["id"] for item in slab_active["preview"]["physical_occupancy"]}
assert slab_active["current"]["status"] == "active" and "floor_slab" not in slab_ids

print(json.dumps({
    "F1": denied["attempt"]["reason"],
    "F2": {"later": later["current"]["status"], "stale": stale["attempt"]["reason"],
           "fresh": fresh["current"]["status"], "equal": equal_later["current"]["status"]},
    "F3": {"furniture_retained": "left_table" in handoff_ids,
           "slab_support_excluded": "floor_slab" not in slab_ids},
}, sort_keys=True))
