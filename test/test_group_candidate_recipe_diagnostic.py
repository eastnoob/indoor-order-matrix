"""Contract checks for the retained real-IFC candidate recipe diagnostic."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ..scripts.design.group_level.run_group_candidate_recipe_diagnostic import (
    RECIPES,
    build_recipe_diagnostic,
)


SEED_RUN = ROOT / "outputs/design/group_seed_candidate_experiment/run_20261027T_seed_profile_v1"


def test_parallel_recipe_diagnostic_preserves_full_scope_and_no_strength() -> None:
    """Use the pinned IFC-derived seed artifact to check both proposal views."""
    document = json.loads((SEED_RUN / "seed_profiles.json").read_text(encoding="utf-8"))
    diagnostic = build_recipe_diagnostic(document)
    assert diagnostic["recipes"] == list(RECIPES)
    assert diagnostic["scope_group_count"] == 37
    assert diagnostic["group_pair_count"] == 666
    assert diagnostic["recipe_selection"] == "parallel-unresolved"
    assert diagnostic["prohibited_outputs"]
    for recipe in RECIPES:
        views = diagnostic["views_by_recipe"][recipe]
        assert len(views) == 37
        for view in views:
            assert len(view["scope_group_ids"]) == 37
            assert view["closure_status"] == "not_evaluated"
            assert view["participation_formula"] is None
            assert view["strength_formula"] is None
            assert view["winner"] is None
            assert set(view["proposal_extent"]) <= set(view["scope_group_ids"])
            assert len(view["members"]) == 37


def test_candidate_recipe_svg_manifest_is_plane_local_when_rendered(tmp_path: Path) -> None:
    """Render from retained artifacts and ensure every view is valid SVG."""
    from ..scripts.design.group_level.run_group_candidate_recipe_diagnostic import write_diagnostic

    output = write_diagnostic(
        SEED_RUN,
        ROOT / "outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96",
        tmp_path,
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["view_count"] == 74
    for item in manifest["views"]:
        svg = output / item["svg"]
        ET.parse(svg)
