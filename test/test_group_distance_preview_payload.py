"""Verify the actual viewer payload preserves recorded visual fields only."""

import json
from pathlib import Path

import pytest

from scripts.design.group_level.render_group_distance_preview import html_document, preview_observations


@pytest.mark.parametrize("name", ["run_v3_finite_band_result", "run_v4_eight_neighbor"])
def test_actual_preview_payload_preserves_visual_data_and_omits_unused_audits(name):
    """The real 666-pair HTML uses exact routes without embedding full numerical lineage."""
    run = Path(__file__).resolve().parents[1] / "outputs/design/group_distance_ifc" / name
    if not (run / "preview/index.html").exists():
        pytest.skip("generate the actual finite-band distance preview first")
    observations = json.loads((run / "observations.json").read_text(encoding="utf-8"))
    projected = preview_observations(observations)
    html = (run / "preview/index.html").read_text(encoding="utf-8")
    payload = json.loads(html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0])
    assert payload["observations"] == projected
    assert len(projected) == len({row["pair_id"] for row in projected}) == 666
    for original, view in zip(observations, projected, strict=True):
        for key in ("pair_id", "group_ids", "center_to_center_euclidean", "centroid_free_space_hybrid", "geometry_audit"):
            assert view[key] == original[key]
        assert "lineage" not in view and "dependencies" not in view
        if original["route"] is not None:
            for key in ("points", "source_centroid", "target_centroid", "source_access", "target_access", "cell_keys", "arithmetic"):
                assert view["route"][key] == original["route"][key]
            assert "cells" not in view["route"] and "edges" not in view["route"]
        else:
            assert view["route"] is None


def test_clearance_preview_carries_exact_witness_section_and_readable_values():
    """Abstract display records retain raw witness values and expose the narrow section."""
    from .test_group_distance_blender_preview import _section_route

    route = {**_section_route(), "source_centroid": None, "target_centroid": None,
             "source_access": None, "target_access": None, "cell_keys": [[0, 0], [0, 1]], "arithmetic": {}}
    reading = {"value": None, "status": "not_available"}
    observation = {"pair_id": "contract-pair", "group_ids": ["a", "b"],
                   "center_to_center_euclidean": reading,
                   "centroid_free_space_hybrid": {**reading, "clearance": route["clearance"]},
                   "geometry_audit": {"a": {}, "b": {}}, "route": route}
    projected = preview_observations([observation])[0]["route"]
    assert projected["clearance"] == {key: value for key, value in route["clearance"].items()
                                      if key not in {"edge_witnesses", "turn_witnesses"}}
    assert projected["clearance_cross_section"]["left"] == [.5, .3]
    assert projected["clearance_bands"][0]["points"] == [[0, .1], [2, .1], [2, -.2], [0, -.2]]
    assert "edges" not in projected and "state_keys" not in projected
    domain = {"selected_candidate_id": "contract-only", "components": [{"exterior": [[0, 0], [2, 0], [0, 2]], "holes": []}]}
    manifest = {"algorithm_version": "group-distance/3", "schema_version": "group-distance/v3",
                "edge_support_version": "eight-neighbor-two-flank-occurrences-directional-clearance/1",
                "group_ids": ["a", "b"], "grid": {"spacing": 1}, "source_identity": {"sha256": "contract-only"},
                "clearance_policy": {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55}}
    html = html_document(manifest, [observation], {"domain": domain, "groups": []}, {"a": "A", "b": "B"}, "")
    assert "Directional clearance policy" in html and "same-position total ≥ 0.55 m" in html
    assert "Saved route clearance summary" in html and "Narrowest saved" in html
    assert "section.left,section.right" in html and "clearance_cross_section:section" in html
    assert "guaranteed per-edge left/right side bands" in html and "their sum is not the minimum total" in html
    payload = json.loads(html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0])
    assert payload["observations"][0]["route"] == projected
    assert payload["observations"][0]["centroid_free_space_hybrid"]["clearance"] == projected["clearance"]
    assert "side_sample_query_refs" not in html and "edge_witnesses" not in html
