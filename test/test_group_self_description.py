from __future__ import annotations

from dataclasses import replace
import json
from math import pi

import pytest

from ..features.group_self_description import describe_group_relations
from ..features.affordance.models import Rect
from ..features.scene_contract import AuthoredGroup, SourceObject, UncertaintyRecord
from .test_neutral_scene_analysis_regression import _neutral_scene


def _component(left: float, bottom: float, right: float, top: float, *, holes=()):
    """Return one explicit projected polygon component for a legacy scene."""
    return {
        "exterior": ((left, bottom), (right, bottom), (right, top), (left, top)),
        "holes": tuple(holes),
    }


def _legacy_scene(*, domain=True, objects=None):
    """Build a compact legacy planar scene with explicit group markers."""
    return {
        "source": "test:group-self-description",
        "settings": {
            "geometry_tolerance": 1e-6,
            "topology_tolerance": 1e-6,
            "analysis_plane": "xy",
            "analysis_length_unit": "m",
        },
        "analysis_domain": {"id": "room-domain", "geometry_refs": ("domain",)}
        if domain
        else None,
        "objects": objects
        if objects is not None
        else [
            {
                "id": "member-a",
                "role": "furniture",
                "furniture_group": "group-a",
                "geometry_components": [_component(0.0, 0.0, 2.0, 2.0)],
                "metadata": {"type": "table"},
                "_source_geometry_refs": ["mesh-a"],
            },
            {
                "id": "member-b",
                "role": "furniture",
                "metadata": {"furniture-group": "group-b", "type": "table"},
                "geometry_components": [_component(2.0, 0.0, 4.0, 2.0)],
                "_source_geometry_refs": ["mesh-b"],
            },
            {
                "id": "ordinary-group-member",
                "role": "furniture",
                "group_refs": ["ordinary-group"],
                "group": "ordinary-group",
                "geometry_components": [_component(8.0, 0.0, 10.0, 2.0)],
                "_source_geometry_refs": ["mesh-context"],
            },
            {
                "id": "slanted-wall",
                "role": "wall",
                "geometry_components": [_component(5.0, 0.0, 5.5, 4.0)],
                "_source_geometry_refs": ["mesh-wall"],
            },
        ],
        "channel_evidence": {},
        "boundaries": [],
        "boundary_facts": [],
        "physical_occupancy": [],
        "walk_blockers": [],
        "visibility_blockers": [],
    }


def test_exact_furniture_group_marker_is_eligible_and_candidate_is_deferred():
    """Only explicit furniture groups become nodes and candidate synthesis stays deferred."""
    result = describe_group_relations(_legacy_scene())

    assert result["schema"] == "group-self-description-evidence/v1"
    assert [item["eligible_group_id"] for item in result["eligibility"]] == [
        "group-a",
        "group-b",
    ]
    assert "ordinary-group" not in {
        item["eligible_group_id"] for item in result["eligibility"]
    }
    assert result["candidate_view_status"] == "deferred"
    assert result["candidate_views"] is None
    assert "slanted-wall" in result["space_observations"]["context_references"]


def test_neutral_scene_ordinary_authored_group_is_excluded():
    """A generic authored group remains context even when its member is furniture."""
    scene = _neutral_scene()
    scene = replace(
        scene,
        authored_groups=(
            AuthoredGroup(
                id="ordinary-authored-group",
                source_id=None,
                member_refs=("left_table",),
                group_role="logical_group",
            ),
            scene.authored_groups[1],
        ),
    )

    result = describe_group_relations(scene)

    assert [item["eligible_group_id"] for item in result["eligibility"]] == [
        "group_right"
    ]
    assert "left_table" in result["eligibility"][0]["excluded_context_object_ids"]


def test_representative_geometry_is_additive_and_area_weighted():
    """Additive area and area-weighted moments stay separate from deferred union evidence."""
    objects = [
        {
            "id": "a1",
            "role": "furniture",
            "furniture_group": "group-a",
            "geometry_components": [_component(0.0, 0.0, 2.0, 2.0)],
            "_source_geometry_refs": ["mesh-a1"],
        },
        {
            "id": "a2",
            "role": "furniture",
            "metadata": {"furniture-group": "group-a"},
            "geometry_components": [_component(4.0, 0.0, 6.0, 2.0)],
            "_source_geometry_refs": ["mesh-a2"],
        },
    ]

    geometry = describe_group_relations(
        _legacy_scene(objects=objects)
    )["group_geometry"][0]

    assert geometry["support_area"] == pytest.approx(8.0)
    assert geometry["center"] == pytest.approx((3.0, 1.0))
    assert geometry["within_member_covariance"][0][0] == pytest.approx(1.0 / 3.0)
    assert geometry["between_member_covariance"][0][0] == pytest.approx(4.0)
    assert geometry["covariance"][0][0] == pytest.approx(13.0 / 3.0)
    assert geometry["overlap_area"] is None
    assert geometry["union_area_status"] == "deferred"
    assert geometry["aggregation_status"] == "deferred"
    assert geometry["strength"] is None
    assert geometry["strength_status"] == "deferred"


def test_geometry_status_preserves_holes_invalid_and_missing_geometry():
    """Unsupported holes remain invalid and unavailable members remain distinct."""
    objects = [
        {
            "id": "hole-member",
            "role": "furniture",
            "furniture_group": "group-holes",
            "geometry_components": [
                _component(
                    0.0,
                    0.0,
                    4.0,
                    4.0,
                    holes=(((1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0)),),
                )
            ],
            "_source_geometry_refs": ["mesh-hole"],
        },
        {
            "id": "missing-member",
            "role": "furniture",
            "metadata": {"furniture-group": "group-holes"},
            "geometry_components": [],
            "_source_geometry_refs": [],
        },
    ]

    geometry = describe_group_relations(
        _legacy_scene(objects=objects)
    )["group_geometry"][0]

    assert geometry["geometry_status"] == "invalid"
    assert {item["reason"] for item in geometry["excluded_member_reasons"]} >= {
        "unsupported_holes",
        "missing_geometry",
    }
    assert all(item["status"] != "missing" for item in geometry["excluded_member_reasons"])


def test_pair_observations_keep_contact_overlap_and_normalized_gap_separate():
    """Pair records preserve member witnesses without manufacturing a membership edge."""
    result = describe_group_relations(_legacy_scene())
    pair = result["group_relations"][0]

    assert pair["group_a"] == "group-a"
    assert pair["group_b"] == "group-b"
    assert pair["aggregation_status"] == "deferred"
    assert pair["raw_boundary_gap"] is None
    assert pair["contact"] is None
    assert pair["overlap"] is None
    assert pair["formal_membership_edge"] is None
    observation = pair["member_pair_observations"][0]
    assert observation["raw_boundary_gap"] == pytest.approx(0.0)
    assert observation["normalized_boundary_gap"] == pytest.approx(0.0)
    assert observation["contact"] is True
    assert observation["overlap"] is False
    assert observation["witness"]


def test_domain_missing_propagates_not_available_without_zero_fill():
    """Domain-dependent space channels remain unavailable when no domain is authored."""
    space = describe_group_relations(_legacy_scene(domain=False))["space_observations"]

    assert space["domain_status"] == "not_available"
    assert space["free_space"]["status"] == "not_available"
    assert space["connectivity"]["status"] == "not_available"
    assert space["bottleneck_profile"]["status"] == "not_available"
    assert space["free_space"].get("value") is None


def _member(member_id, components, *, group="group-a", **fields):
    """Build explicit member input without manufacturing a geometry fallback."""
    return {
        "id": member_id,
        "furniture_group": group,
        "geometry_components": components,
        "_source_geometry_refs": [f"mesh-{member_id}"],
        **fields,
    }


def test_unequal_member_areas_weight_center_and_all_covariance_entries():
    """Catch count weighting and omission of the off-diagonal between-member term."""
    objects = [
        _member("small", [_component(0, 0, 2, 2)]),
        _member("large", [_component(4, 2, 8, 4)]),
    ]
    geometry = describe_group_relations(_legacy_scene(objects=objects))["group_geometry"][0]

    # The 4:8 area ratio makes both centroid offsets contribute to xy covariance.
    assert geometry["geometry_status"] == "computed"
    assert geometry["support_area"] == pytest.approx(12)
    assert geometry["center"] == pytest.approx((13 / 3, 7 / 3))
    assert geometry["within_member_covariance"][0] == pytest.approx((1, 0))
    assert geometry["within_member_covariance"][1] == pytest.approx((0, 1 / 3))
    assert geometry["between_member_covariance"][0] == pytest.approx((50 / 9, 20 / 9))
    assert geometry["between_member_covariance"][1] == pytest.approx((20 / 9, 8 / 9))
    assert geometry["covariance"][0] == pytest.approx((59 / 9, 20 / 9))
    assert geometry["covariance"][1] == pytest.approx((20 / 9, 11 / 9))


def test_multiple_components_add_area_without_union_even_when_overlapping():
    """Catch a silent component union or a bbox stand-in for additive support."""
    member = _member("multi", [_component(0, 0, 2, 2), _component(1, 0, 3, 2)])
    geometry = describe_group_relations(_legacy_scene(objects=[member]))["group_geometry"][0]

    assert geometry["support_area"] == pytest.approx(8)
    assert geometry["center"] == pytest.approx((1.5, 1))
    assert geometry["within_member_covariance"][0][0] == pytest.approx(7 / 12)
    assert geometry["between_member_covariance"][0][0] == pytest.approx(0)
    assert geometry["overlap_area"] is None
    assert geometry["union_area_status"] == "deferred"


@pytest.mark.parametrize("reverse_ring", [False, True])
def test_triangle_moments_use_area_integrals_instead_of_vertex_pca(reverse_ring):
    """Catch vertex averaging and orientation-dependent signed shoelace moments."""
    exterior = ((0, 0), (4, 0), (0, 2), (0, 0))
    if reverse_ring:
        exterior = tuple(reversed(exterior))
    member = _member("triangle", [{"exterior": exterior, "holes": ()}])
    geometry = describe_group_relations(_legacy_scene(objects=[member]))["group_geometry"][0]

    assert geometry["support_area"] == pytest.approx(4)
    assert geometry["center"] == pytest.approx((4 / 3, 2 / 3))
    assert geometry["covariance"][0] == pytest.approx((8 / 9, -2 / 9))
    assert geometry["covariance"][1] == pytest.approx((-2 / 9, 2 / 9))


@pytest.mark.parametrize("valid_member", [False, True])
def test_missing_geometry_is_unavailable_or_partial_without_zero_fill(valid_member):
    """Catch fabricated zero geometry and loss of usable siblings on missing input."""
    objects = [_member("missing", [])]
    if valid_member:
        objects.append(_member("usable", [_component(0, 0, 4, 2)]))
    geometry = describe_group_relations(_legacy_scene(objects=objects))["group_geometry"][0]

    assert geometry["geometry_status"] == ("partial" if valid_member else "not_available")
    missing = geometry["excluded_member_reasons"][0]
    assert missing["member_id"] == "missing"
    assert missing["status"] == "not_available"
    assert missing["reason"] == "missing_geometry"
    if valid_member:
        assert geometry["support_area"] == pytest.approx(8)
        assert geometry["center"] == pytest.approx((2, 1))
    else:
        for field in ("support_area", "center", "covariance", "within_member_covariance", "between_member_covariance"):
            assert geometry[field] is None


@pytest.mark.parametrize("component,reason", [
    ({"exterior": ((0, 0), (2, 2), (0, 2), (2, 0)), "holes": ()}, "invalid_polygon"),
    ({"exterior": ((0, 0), (1, 0), (2, 0)), "holes": ()}, "invalid_polygon"),
    ({"exterior": ((0, 0), (float("nan"), 0), (0, 1)), "holes": ()}, "non_finite_coordinates"),
    (_component(0, 0, 4, 4, holes=(((1, 1), (2, 1), (1, 2)),)), "unsupported_holes"),
])
def test_invalid_members_allow_only_diagnostic_sibling_geometry(component, reason):
    """Catch invalid-to-missing rewrites and formal use of valid siblings in an invalid group."""
    objects = [_member("bad", [component]), _member("good", [_component(0, 0, 2, 2)])]
    geometry = describe_group_relations(_legacy_scene(objects=objects))["group_geometry"][0]

    assert geometry["geometry_status"] == "invalid"
    assert geometry["excluded_member_reasons"][0]["status"] == "invalid"
    assert geometry["excluded_member_reasons"][0]["reason"] == reason
    assert geometry["excluded_member_reasons"][0]["source_refs"] == ["mesh-bad"]
    assert geometry["support_area"] is None
    assert geometry["center"] is None
    assert geometry["diagnostic_geometry"]["status"] == "diagnostic_only"
    assert geometry["diagnostic_geometry"]["support_area"] == pytest.approx(4)


@pytest.mark.parametrize("explicit_fallback", [False, True])
def test_rect_requires_explicit_fallback_basis(explicit_fallback):
    """Catch silent bbox geometry while retaining the approved explicit rect fallback."""
    member = _member("rect", [], rect=Rect(cx=2, cy=1, width=4, height=2))
    if explicit_fallback:
        member["geometry_basis"] = "rect_fallback"
    geometry = describe_group_relations(_legacy_scene(objects=[member]))["group_geometry"][0]

    assert geometry["geometry_status"] == ("computed" if explicit_fallback else "not_available")
    if explicit_fallback:
        assert geometry["support_area"] == pytest.approx(8)
        assert geometry["member_geometry"][0]["geometry_basis"] == "rect_fallback"
    else:
        assert geometry["support_area"] is None


def test_frame_and_axis_use_independent_harmonics_and_area_anisotropy_weights():
    """Catch using one harmonic or member counts for both frame and axis."""
    objects = [
        _member("horizontal", [_component(0, 0, 4, 2)]),
        _member("vertical", [_component(8, 0, 9, 2)]),
    ]
    geometry = describe_group_relations(_legacy_scene(objects=objects))["group_geometry"][0]

    # Both anisotropies are 3/5, so area 8:2 leaves a 3/5 axis resultant.
    assert geometry["directional_member_support"] == 2
    assert geometry["group_frame"]["angle"] == pytest.approx(0, abs=1e-12)
    assert geometry["group_frame"]["coherence"] == pytest.approx(1)
    assert geometry["group_axis"]["angle"] == pytest.approx(0, abs=1e-12)
    assert geometry["group_axis"]["coherence"] == pytest.approx(3 / 5)
    assert geometry["member_geometry"][0]["directional_weight"] == pytest.approx(24 / 5)
    assert geometry["strength"] is None
    assert geometry["strength_status"] == "deferred"


def test_isotropic_members_do_not_fabricate_a_direction():
    """Catch deterministic rendering angles masquerading as directional evidence."""
    geometry = describe_group_relations(_legacy_scene(objects=[
        _member("square", [_component(0, 0, 2, 2)])
    ]))["group_geometry"][0]

    assert geometry["directional_member_support"] == 0
    for direction in ("group_frame", "group_axis"):
        assert geometry[direction]["angle"] is None
        assert geometry[direction]["coherence"] == 0
        assert geometry[direction]["direction_status"] == "undefined"


def test_neutral_membership_preserves_missing_sources_and_geometry_uncertainties():
    """Catch planar-view omission erasing authored members that lack geometry."""
    scene = _neutral_scene()
    missing = SourceObject(id="missing", source_role="furniture", uncertainties=(
        UncertaintyRecord(code="missing_geometry", message="No imported geometry", source_refs=("missing",),
                          operation="import", severity="warning"),
    ))
    group = replace(scene.authored_groups[0], member_refs=("unknown-ref", "missing", "left_table"))
    scene = replace(scene, source_objects=(*scene.source_objects, missing), authored_groups=(group,))
    result = describe_group_relations(scene)

    assert result["eligibility"][0]["member_object_ids"] == ["left_table", "missing", "unknown-ref"]
    assert result["group_geometry"][0]["geometry_status"] == "invalid"
    assert {item["reason"] for item in result["group_geometry"][0]["excluded_member_reasons"]} == {
        "missing_geometry", "unresolved_member_ref",
    }
    assert any(item["code"] == "missing_geometry" for item in result["uncertainties"])


def test_geometry_uses_declared_plane_coordinates_and_json_provenance():
    """Catch view-offset leakage and frozen mapping objects escaping serialization."""
    scene = _neutral_scene()
    result = describe_group_relations(scene)
    geometry = result["group_geometry"][0]

    assert geometry["target_layer"] == "furniture_group"
    assert geometry["target_id"] == "group_left"
    assert geometry["center"] == pytest.approx((30, 50))
    assert result["analysis_frame"]["plane"] == "test-plan"
    assert result["analysis_frame"]["basis"] == [list(axis) for axis in scene.context.analysis_plane.basis]
    assert result["analysis_frame"]["unit"] == "m"
    assert result["provenance"]["source_schema"] == "synthetic"
    assert result["provenance"]["adapter_version"] == "test-neutral-scene/1.0"
    assert result["capabilities"]["3d_clearance"]["status"] == "not_available"
    assert result["capabilities"]["z_compatibility"]["status"] == "not_available"
    json.dumps(result, allow_nan=False)


def test_no_exact_authored_groups_has_explicit_not_evaluated_status():
    """Catch creation of singleton furniture nodes from names, layers, or ordinary refs."""
    scene = replace(_neutral_scene(), authored_groups=())
    result = describe_group_relations(scene)

    assert result["eligibility"] == []
    assert result["group_geometry"] == []
    assert result["status"] == "not_evaluated"
    assert result["reason"] == "no_eligible_authored_groups"
