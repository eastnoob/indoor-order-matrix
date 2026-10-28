"""Contract checks for the multi-group candidate-set diagnostic."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ..scripts.design.group_level.run_group_set_candidate_diagnostic import (  # noqa: E402
    RECIPES,
    build_set_candidate_diagnostic,
    write_diagnostic,
)


SEED_RUN = ROOT / "outputs/design/group_seed_candidate_experiment/run_20261027T_seed_profile_v1"
GEOMETRY_RUN = ROOT / "outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96"


def test_set_candidate_diagnostic_emits_multi_group_views_without_strength() -> None:
    """The retained real IFC relations produce set-level candidate proposals."""
    document = json.loads((SEED_RUN / "seed_profiles.json").read_text(encoding="utf-8"))
    diagnostic = build_set_candidate_diagnostic(document)
    assert diagnostic["recipes"] == list(RECIPES)
    assert diagnostic["scope_group_count"] == 37
    assert diagnostic["group_pair_count"] == 666
    assert len(diagnostic["candidates_by_recipe"]["nearest-neighbour-components"]) == 14
    assert len(diagnostic["candidates_by_recipe"]["contact-components"]) == 21
    assert len(diagnostic["candidates_by_recipe"]["nearest-neighbour-complete-link"]) == 23
    assert len(diagnostic["candidates_by_recipe"]["contact-complete-link"]) == 24
    for recipe in RECIPES:
        candidates = diagnostic["candidates_by_recipe"][recipe]
        assert {group for item in candidates for group in item["proposal_extent"]} == set(document["views"][0]["scope_group_ids"])
        assert all(item["closure_status"] == "not_evaluated" for item in candidates)
        assert all(item["participation"] is None and item["strength"] is None and item["winner"] is None for item in candidates)
        if recipe.endswith("components"):
            assert any(len(item["proposal_extent"]) >= 3 for item in candidates)
        else:
            assert all(len(item["proposal_extent"]) <= 2 for item in candidates)


def test_set_candidate_diagnostic_writes_all_plane_views(tmp_path: Path) -> None:
    """Every emitted set candidate has a parseable SVG and manifest entry."""
    output = write_diagnostic(SEED_RUN, GEOMETRY_RUN, tmp_path)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["candidate_count"] == 82
    for item in manifest["views"]:
        ET.parse(output / item["svg"])
