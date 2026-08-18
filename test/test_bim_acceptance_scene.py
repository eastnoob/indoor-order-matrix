"""End-to-end assertions for the generated three-dimensional BIM fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .bim.acceptance_manifest import ACCEPTANCE_MANIFEST


ROOT = Path(__file__).parents[1]


def _load_output(path: Path) -> dict:
    """Load one generated acceptance artifact as a standard JSON object."""
    assert path.exists(), f"missing generated acceptance artifact: {path}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _forbidden_keys(value: object) -> set[str]:
    """Collect prohibited scoring keys recursively from a JSON value."""
    forbidden = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = key.lower()
            if "weight" in lowered or "score" in lowered:
                forbidden.add(key)
            forbidden.update(_forbidden_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            forbidden.update(_forbidden_keys(nested))
    return forbidden


@pytest.fixture(scope="module")
def acceptance_artifacts(tmp_path_factory):
    """Generate fresh acceptance artifacts for semantic assertions."""
    from .blender.run_bim_acceptance import run_acceptance

    return run_acceptance(tmp_path_factory.mktemp("gate8-acceptance"))


@pytest.fixture(scope="module")
def description(acceptance_artifacts) -> dict:
    """Return the fresh neutral description artifact from this test session."""
    return _load_output(acceptance_artifacts["description"])


@pytest.fixture(scope="module")
def room_model(acceptance_artifacts) -> dict:
    """Return the fresh room-analysis-model artifact from this test session."""
    return _load_output(acceptance_artifacts["room_model"])


def test_required_output_artifacts_are_generated(acceptance_artifacts):
    """The acceptance run must return both manifest-required JSON artifacts."""
    returned_paths = {
        acceptance_artifacts["description"].name,
        acceptance_artifacts["room_model"].name,
    }
    expected_names = {
        Path(relative_path).name
        for relative_path in ACCEPTANCE_MANIFEST["required_outputs"]
    }
    assert returned_paths == expected_names
    assert all(
        acceptance_artifacts[key].exists()
        for key in ("description", "room_model")
    )


def test_generated_description_covers_manifest_and_both_geometry_paths(description):
    """The fixture must preserve stable ids and compare IFC with explicit Blender facts."""
    assert set(ACCEPTANCE_MANIFEST["fixture_ids"]).issubset(description["fixture_ids"])
    assert description["input_modes"] == ["ifc", "blender_geometry"]
    assert description["shared_facts"]["all_match"] is True
    assert description["shared_facts"]["compared_ids"]


def test_sofa_queries_preserve_spatially_varying_height(description):
    """Seat and back probes must return different occupied vertical intervals."""
    queries = description["height_queries"]["sofa"]
    assert queries["seat_probe"]["intervals"] == [[0.2, 0.65]]
    assert queries["back_probe"]["intervals"] == [[0.0, 1.2]]
    assert queries["seat_probe"] != queries["back_probe"]


def test_surface_mass_and_channel_evidence_remain_separate(description):
    """Carpet, cabinet, and transparent partition must retain distinct factual roles."""
    carpet = description["surface_evidence"]["carpet"]
    assert carpet["surface_geometry_refs"]
    assert carpet["mass_geometry_refs"] == []
    channels = description["channel_evidence"]
    assert channels["low_cabinet"]["walking"]["status"] == "blocked"
    assert channels["low_cabinet"]["visual"]["status"] == "clear"
    assert channels["glass_partition"]["walking"]["status"] == "blocked"
    assert channels["glass_partition"]["visual"]["status"] == "transmitting"


def test_authored_affordances_ordering_networks_and_grid_are_auditable(description):
    """Higher-level descriptions must retain authored and derived evidence without scoring."""
    assert set(description["authored_affordances"]) == {
        "chair_affordance_aligned",
        "chair_affordance_oblique",
    }
    ordering = description["ordering_cases"]
    assert ordering["aligned"]["primary_angle"] == pytest.approx(0.0)
    assert ordering["oblique"]["primary_angle"] == pytest.approx(30.0)
    assert ordering["mixed"]["concentration"] < ordering["aligned"]["concentration"]
    assert {item["scope"] for item in description["spatial_networks"]} >= {
        "region_internal",
        "inter_region",
    }
    assert description["grid_relations"]["local"]
    assert description["grid_relations"]["global"]


def test_ifc_and_blender_paths_share_high_level_analysis_signatures(description):
    """Both explicit input paths must expose equivalent authored and derived signatures."""
    paths = description["path_analyses"]
    assert set(paths) == {"ifc", "blender_geometry"}
    for path in paths.values():
        assert path["ordering_cases"]
        assert set(path["network_scopes"]) >= {"region_internal", "inter_region"}
        assert set(path["authored_affordance_ids"]) == {
            "chair_affordance_aligned",
            "chair_affordance_oblique",
        }
        assert path["grid_relations"]["local"]
        assert path["grid_relations"]["global"]
    assert description["cross_path_signatures"]["ordering_equivalent"] is True
    assert description["cross_path_signatures"]["network_scopes_equivalent"] is True
    assert description["cross_path_signatures"]["authored_affordances_equivalent"] is True
    assert description["cross_path_signatures"]["grid_relations_equivalent"] is True


def test_outputs_are_json_native_auditable_and_weight_free(description, room_model):
    """Artifacts must expose methods, tolerances, uncertainty, and no fitted score fields."""
    assert description["provenance"]["methods"]
    assert description["provenance"]["source_ids"]
    assert description["provenance"]["geometry_tolerance"] > 0.0
    assert description["provenance"]["topology_tolerance"] > 0.0
    assert "uncertainties" in description
    assert room_model["contract"] == {"id": "room_analysis_model", "version": 1}
    assert not _forbidden_keys(description)
    assert not _forbidden_keys(room_model)


def test_acceptance_generation_is_deterministic(tmp_path):
    """Two fresh runs must produce byte-identical neutral JSON artifacts."""
    from .blender.run_bim_acceptance import run_acceptance

    first = run_acceptance(tmp_path / "first")
    second = run_acceptance(tmp_path / "second")
    assert first["description"].read_bytes() == second["description"].read_bytes()
    assert first["room_model"].read_bytes() == second["room_model"].read_bytes()
