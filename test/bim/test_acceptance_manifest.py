"""Tests for the BIM acceptance fixture manifest contract."""

from copy import deepcopy

import pytest

from acceptance_manifest import (
    ACCEPTANCE_MANIFEST,
    validate_acceptance_manifest,
)


EXPECTED_FIXTURE_IDS = (
    "room",
    "floor",
    "wall_north",
    "table_group_aligned",
    "table_group_oblique",
    "sofa",
    "low_cabinet",
    "glass_partition",
    "carpet",
    "grid_main",
    "chair_affordance_aligned",
    "chair_affordance_oblique",
)

EXPECTED_OUTPUTS = (
    "test/output/blender_demo_description.json",
    "test/output/blender_demo_room_analysis_model.json",
)


def test_acceptance_manifest_is_valid_and_stable() -> None:
    """Require the source-independent manifest and its stable contract values."""
    assert validate_acceptance_manifest(ACCEPTANCE_MANIFEST) is None
    assert tuple(ACCEPTANCE_MANIFEST["fixture_ids"]) == EXPECTED_FIXTURE_IDS
    assert tuple(ACCEPTANCE_MANIFEST["required_outputs"]) == EXPECTED_OUTPUTS
    assert set(ACCEPTANCE_MANIFEST["allowed_input_modes"]) == {
        "ifc",
        "blender_geometry",
        "hybrid",
        "svg",
    }
    assert ACCEPTANCE_MANIFEST["regeneration"] == {
        "generator_path": "test/blender/generate_bim_acceptance_scene.py",
        "entrypoint": "generate_acceptance_scene",
        "manual_edits": False,
    }


def test_validator_rejects_duplicate_fixture_ids() -> None:
    """Reject a manifest whose generated fixture ids are ambiguous."""
    manifest = deepcopy(ACCEPTANCE_MANIFEST)
    manifest["fixture_ids"].append("sofa")

    with pytest.raises(ValueError, match="duplicate fixture id"):
        validate_acceptance_manifest(manifest)


def test_validator_rejects_a_missing_required_output() -> None:
    """Reject a manifest that cannot produce every required JSON artifact."""
    manifest = deepcopy(ACCEPTANCE_MANIFEST)
    manifest["required_outputs"].remove(EXPECTED_OUTPUTS[0])

    with pytest.raises(ValueError, match="missing required output"):
        validate_acceptance_manifest(manifest)


def test_validator_rejects_an_unsupported_input_mode() -> None:
    """Reject source modes outside the explicitly supported adapter boundary."""
    manifest = deepcopy(ACCEPTANCE_MANIFEST)
    manifest["allowed_input_modes"].append("viewport")

    with pytest.raises(ValueError, match="unsupported input mode"):
        validate_acceptance_manifest(manifest)


def test_validator_rejects_a_missing_supported_input_mode() -> None:
    """Reject a manifest that omits one of the four supported source modes."""
    manifest = deepcopy(ACCEPTANCE_MANIFEST)
    manifest["allowed_input_modes"].remove("svg")

    with pytest.raises(ValueError, match="missing supported input mode"):
        validate_acceptance_manifest(manifest)
