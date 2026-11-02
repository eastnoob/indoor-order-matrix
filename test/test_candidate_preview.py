"""Focused tests for transient candidate preview geometry and single selection."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blender_addon.order_analyzer_ui import candidate_preview, region_overlay


def _candidate(version_id="v1"):
    return {
        "version_id": version_id,
        "outline": (((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 0.0)),),
        "holes": (((0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.5, 0.5)),),
        "plane_origin": (0.0, 0.0, 0.0),
        "plane_basis": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    }


def test_eye_preview_uses_true_shell_and_hole_rings():
    """Eye preview emits shell and hole edges as GPU line data only."""
    data = region_overlay.build_line_data((), candidate_previews=(_candidate(),))
    assert len(data["indices"]) == 6
    assert all(style["preview"] for style in data["styles"])
    assert max(vertex[2] for vertex in data["vertices"]) == 0.02


def test_selection_is_single_and_eye_state_is_independent():
    """Selection accepts one cached id while eye filtering does not alter it."""
    candidates = (_candidate("v1"), _candidate("v2"))
    assert candidate_preview.select_candidate(candidates, "v2") == "v2"
    assert candidate_preview.select_candidate(candidates, "missing") is None
    assert tuple(candidate_preview.candidate_id(item) for item in candidate_preview.eye_enabled(candidates, {"v1"})) == ("v1",)


def test_geojson_outline_ignores_integer_hole_count():
    """The service's numeric holes count must not be treated as ring geometry."""
    candidate = _candidate("geo")
    candidate["outline"] = {"type": "Polygon", "coordinates": [candidate["outline"][0], candidate["holes"][0]]}
    candidate["holes"] = 1
    data = region_overlay.build_line_data((), candidate_previews=(candidate,))
    assert len(data["indices"]) == 6


def test_geojson_polygon_preview_preserves_holes():
    """Overlay accepts service GeoJSON and keeps the polygon shell plus holes."""
    candidate = _candidate()
    candidate["outline"] = {"type": "Polygon", "coordinates": [candidate["outline"][0], candidate["holes"][0]]}
    candidate.pop("holes")
    data = region_overlay.build_line_data((), candidate_previews=(candidate,))
    assert len(data["indices"]) == 6


def test_tag_redraw_requests_only_view3d_areas():
    """GPU preview refresh marks each visible 3D view for redraw."""
    calls = []
    context = type("Context", (), {"window": type("Window", (), {"screen": type("Screen", (), {
        "areas": (type("Area", (), {"type": "VIEW_3D", "tag_redraw": lambda self: calls.append("view")})(),
                  type("Area", (), {"type": "PROPERTIES", "tag_redraw": lambda self: calls.append("other")})())})()})()})()
    region_overlay.tag_redraw(context)
    assert calls == ["view"]


