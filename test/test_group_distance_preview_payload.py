"""Verify the actual viewer payload preserves recorded visual fields only."""

import json
from pathlib import Path

import pytest

from scripts.design.group_level.render_group_distance_preview import preview_observations


def test_actual_preview_payload_preserves_visual_data_and_omits_unused_audits():
    """The real 666-pair HTML uses exact routes without embedding full numerical lineage."""
    run = Path(__file__).resolve().parents[1] / "outputs/design/group_distance_ifc/run_v3_finite_band_result"
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
