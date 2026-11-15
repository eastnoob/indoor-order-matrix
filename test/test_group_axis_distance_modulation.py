"""Actual retained IFC checks for the opt-in distance-axis diagnostic."""

from dataclasses import replace

import pytest

from features import group_axis_potential_field as potential
from features.field_core import FieldResultStatus
from scripts.design.group_level.run_group_axis_distance_modulation_ifc import load_modulation_inputs


@pytest.fixture(scope="module")
def actual_inputs():
    """Authenticate the pinned axis and distance packages once for this module."""
    return load_modulation_inputs()


def _by_key(outputs):
    """Index package outputs by their stable target/channel address."""
    return {(item.target["identity"], item.channel): item for item in outputs}


def test_actual_full_scope_preserves_axis_and_adds_1369_addressed_cells(actual_inputs):
    """All 1,332 directional values use exact processed pairs and preserve pure-axis outputs."""
    _, envelopes, raw, processed, modulation, _ = actual_inputs
    baseline = potential.run_group_axis_potential_package(envelopes)["raw_output"]
    opted = potential.run_group_axis_potential_package(envelopes, distance_modulation=modulation)["raw_output"]
    base_channels = _by_key(baseline.outputs)
    opted_channels = _by_key(opted.outputs)
    assert all(opted_channels[key] == value for key, value in base_channels.items())
    diagnostic = [item for item in opted.outputs if item.channel == "distance_modulated_axis_support"]
    cells = [item for item in opted.outputs if item.channel == "axis_field_support"]
    assert len(cells) == len(diagnostic) == 37 * 37
    raw_pairs = {item.target["identity"]: item for item in raw.outputs if item.channel == "euclidean_distance"}
    proximity = {item.target["identity"]: item for item in processed.outputs
                 if item.channel == "euclidean_symmetric_reciprocal_relative_proximity"}
    pair_refs = {(ref.target_identity, ref.channel): ref for ref in modulation.dependency.channels}
    assert len(raw_pairs) == len(proximity) == len(pair_refs) == 666
    self_cells = [item for item in diagnostic if item.explanation == "distance_self_not_applicable"]
    assert len(self_cells) == 37
    assert all(item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE for item in self_cells)
    checked = 0
    for axis in cells:
        result = opted_channels[(axis.target["identity"], "distance_modulated_axis_support")]
        observation = axis.observation
        anchor, group = observation["anchor_group_id"], observation["target_group_id"]
        if anchor == group:
            continue
        pair_id, distance = next((key, value) for key, value in raw_pairs.items()
                                 if set(value.observation["group_ids"]) == {anchor, group})
        p = proximity[pair_id]
        reference = pair_refs[(pair_id, p.channel)]
        assert result.status is FieldResultStatus.COMPUTED
        assert result.observation == observation["axis_field_support"] * p.observation
        assert set(result.derived_from) == set(axis.derived_from) | {reference}
        assert p.observation > 0 and distance.observation["units"] == "m"
        checked += 1
    assert checked == 1_332


def test_current_cache_reuses_and_stale_dependency_redacts_values(actual_inputs, tmp_path):
    """A full typed hit is reusable, while stale processed input has no numeric fallback."""
    _, envelopes, _, _, modulation, _ = actual_inputs
    first = potential.run_group_axis_potential_package(envelopes, cache_directory=tmp_path,
                                                        distance_modulation=modulation)
    second = potential.run_group_axis_potential_package(envelopes, cache_directory=tmp_path,
                                                         distance_modulation=modulation)
    assert first["cache_hit"] is False and second["cache_hit"] is True
    assert first["raw_output"] == second["raw_output"]
    stale_dependency = replace(modulation.dependency, package_freshness="stale")
    stale = replace(modulation, dependency=stale_dependency)
    stale_result = potential.run_group_axis_potential_package(envelopes, cache_directory=tmp_path,
                                                               distance_modulation=stale)["raw_output"]
    unavailable = [item for item in stale_result.outputs
                   if item.channel == "distance_modulated_axis_support"
                   and item.explanation != "distance_self_not_applicable"]
    assert len(unavailable) == 1_332
    assert all(item.observation is None and item.status is FieldResultStatus.NOT_AVAILABLE for item in unavailable)


def test_compatibility_or_recipe_drift_cannot_use_prior_values(actual_inputs):
    """Changed member registration and a noncurrent fresh recipe fail closed."""
    _, envelopes, _, _, modulation, _ = actual_inputs
    changed_refs = dict(modulation.compatibility["distance_member_refs"])
    group = next(iter(changed_refs))
    changed_refs[group] = ("foreign-member",)
    invalid = replace(modulation, compatibility={**modulation.compatibility, "distance_member_refs": changed_refs})
    with pytest.raises(ValueError, match="member refs"):
        potential.run_group_axis_potential_package(envelopes, distance_modulation=invalid)
    wrong_recipe = replace(modulation, current_processing_identity="foreign-current-recipe")
    with pytest.raises(ValueError, match="does not match"):
        potential.run_group_axis_potential_package(envelopes, distance_modulation=wrong_recipe)


def test_missing_processed_address_does_not_fall_back(actual_inputs):
    """An incomplete exact pair scope is rejected rather than read as raw distance."""
    _, envelopes, _, _, modulation, _ = actual_inputs
    dependency = replace(modulation.dependency, channels=modulation.dependency.channels[:-1])
    invalid = replace(modulation, dependency=dependency)
    with pytest.raises(ValueError, match="one processed reference"):
        potential.run_group_axis_potential_package(envelopes, distance_modulation=invalid)
