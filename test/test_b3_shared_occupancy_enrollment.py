"""Focused frozen-input and conservative failure tests for the isolated B3 runner."""

from copy import deepcopy
import pytest
from shapely.geometry import Point

from ..scripts.design.space_field import run_b3_shared_occupancy_enrollment as RUN
from .test_physical_occupancy_section import _section_scene, _replace_source


def test_frozen_identity_scope_and_accepted_original_sections_are_bound():
    """Current binding pins agree with immutable accepted inventory and exact scope."""
    bindings, accepted, originals, capture, _, _, boundary, _, groups = RUN.frozen_inputs()
    assert len(originals) == len(capture["inventory"]) == 358
    assert len(groups) == len(bindings["targets"]) == 3
    assert sum(len(target["represented_source_ids"]) for target in bindings["targets"]) == 7
    assert boundary == {"live-step-6231"}
    assert accepted["primary_plane_world_z_m"] == RUN.QUERY["world_z_m"]


def test_failed_target_support_covers_every_owner_and_target_even_if_frozen_empty():
    """Failed required mass cannot inherit legal-empty support from its originals."""
    scene = _section_scene()
    supports = RUN.unresolved_supports(scene, ["A", "B"], {"A": {}, "B": {}})
    for _, support in supports:
        assert support is not None
        assert all(support.covers(Point(vertex[:2])) for mesh in scene.geometries
                   if mesh.id in {"a", "b", "t"} for vertex in mesh.vertices)


def test_failed_declared_owner_without_binding_still_uses_complete_group_support():
    """Declared coverage failure cannot reuse that owner's empty original evidence."""
    scene = _replace_source(_section_scene(), "B", factual_properties={})
    supports = RUN.unresolved_supports(scene, ["A", "B"], {"A": {}, "B": {}})
    assert supports[0][1].equals(supports[1][1])
    assert supports[1][1].area > 0


def test_missing_required_target_has_domain_wide_unknown_support():
    """An absent target has no certified footprint, even when originals have meshes."""
    scene = _replace_source(_section_scene(), "T", id="unrelated")
    assert RUN.unresolved_supports(scene, ["A"], {"A": {}}) == [("A", None)]


@pytest.mark.parametrize("mutation", ["value", "missing_null", "variant"])
def test_comparison_refuses_any_changed_sample_field_or_missing_variant(mutation):
    """Every field includes explicit null keys and all lattice variants."""
    sample = {"x_m": 1., "occupancy_value": None}
    accepted = {"variants": [{"spacing_m": .25, "samples": [sample]}]}
    field = deepcopy(accepted)
    field["original_source_record_count"] = 0
    if mutation == "value":
        field["variants"][0]["samples"][0]["x_m"] = 2.
    elif mutation == "missing_null":
        del field["variants"][0]["samples"][0]["occupancy_value"]
    else:
        field["variants"] = []
    with pytest.raises(ValueError, match="sample_"):
        RUN.compare_accepted(field, accepted, [], accepted_original_sections=[])


def test_pinned_ref_refuses_mutated_bytes():
    """A fresh hash cannot silently recertify different frozen input bytes."""
    ref = {**RUN.PRIOR.file_ref(RUN.BINDINGS), "sha256": "wrong"}
    with pytest.raises(ValueError, match="fingerprint_mismatch"):
        RUN.verified_ref(ref)


def test_comparison_checks_original_content_instead_of_only_count():
    """A same-length historical row mutation cannot be labeled identical."""
    with pytest.raises(ValueError, match="frozen_original_rows_mismatch"):
        RUN.compare_accepted({"original_source_record_count": 1}, {}, [{"id": "changed"}],
                             accepted_original_sections=[{"id": "original"}])
