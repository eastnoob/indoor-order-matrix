from __future__ import annotations

import json
from dataclasses import replace
from math import cos, radians, sin

import pytest

from ..features.analysis_substitute_discovery import resolve_function_substitute
from ..features.affordance.models import Rect
from ..features.group_self_description import describe_group_relations
from ..features.scene_contract import SourceObject
from .test_neutral_scene_analysis_regression import _mesh, _neutral_scene


def _binding(substitute_id: str, **overrides: object) -> dict[str, object]:
    """Build one complete typed trend binding for a fixture source object."""
    binding = {
        "substitute_id": substitute_id,
        "consumer": "trend",
        "substitute_kind": "MassPatch",
        "analysis_role": "analysis_geometry_substitute",
        "representation_identifier": "Analysis",
        "provenance": {
            "source_global_id": "fixture-source",
            "extraction_method": "fixture",
            "world_transform_applied": True,
            "representation_identifier": "Analysis",
        },
    }
    binding.update(overrides)
    return binding


def _typed_scene(
    *,
    left_binding: list[dict[str, object]] | None = None,
    right_binding: list[dict[str, object]] | None = None,
    add_right_to_left_group: bool = False,
):
    """Build a two-member Neutral Scene with independent Analysis substitutes."""
    scene = _neutral_scene()
    left, right, *context = scene.source_objects
    left = replace(left, factual_properties={"OM_FunctionSubstitutes": [_binding("analysis-left")] if left_binding is None else left_binding})
    right = replace(right, factual_properties={"OM_FunctionSubstitutes": [_binding("analysis-right")] if right_binding is None else right_binding})
    substitutes = (
        SourceObject(id="analysis-left", source_role="analysis_substitute", geometry_refs=("analysis-left-mesh",), provenance={"representation_identifier": "Analysis"}),
        SourceObject(id="analysis-right", source_role="analysis_substitute", geometry_refs=("analysis-right-mesh",), provenance={"representation_identifier": "Analysis"}),
    )
    meshes = scene.geometries + (
        _mesh("analysis-left-mesh", Rect(cx=30.0, cy=50.0, width=10.0, height=30.0)),
        _mesh("analysis-right-mesh", Rect(cx=70.0, cy=50.0, width=10.0, height=30.0)),
    )
    groups = scene.authored_groups
    if add_right_to_left_group:
        groups = (replace(groups[0], member_refs=("left_table", "right_table")),)
    return replace(scene, source_objects=(left, right, *context, *substitutes), geometries=meshes, authored_groups=groups)


def _geometry(scene):
    """Return the first authored group geometry record."""
    return describe_group_relations(scene)["group_geometry"][0]


def test_typed_analysis_binding_is_accepted_and_auditable():
    """The resolver returns the selected id, source id, reason, and provenance."""
    result = resolve_function_substitute(_typed_scene(), "left_table", "trend")
    assert result["status"] == "accepted"
    assert result["selected_substitute_id"] == "analysis-left"
    assert result["source_object_id"] == "left_table"
    assert result["substitute_source_object_id"] == "analysis-left"
    assert result["reason"] == "typed_analysis_binding"
    assert result["provenance"]["extraction_method"] == "fixture"


def test_body_provenance_and_wrong_typed_fields_are_rejected():
    """Body and mismatched consumer contract values cannot authorize trend geometry."""
    for overrides, reason in (
        ({"representation_identifier": "Body"}, "wrong_representation_identifier"),
        ({"consumer": "clearance"}, "wrong_consumer"),
        ({"substitute_kind": "SurfacePatch"}, "wrong_substitute_kind"),
        ({"analysis_role": "clearance_geometry"}, "wrong_analysis_role"),
    ):
        result = resolve_function_substitute(
            _typed_scene(left_binding=[_binding("analysis-left", **overrides)]),
            "left_table",
            "trend",
        )
        assert result["status"] == "rejected"
        assert result["reason"] == reason

    body_provenance = _typed_scene(left_binding=[_binding("analysis-left", provenance={"representation_identifier": "Body"})])
    assert resolve_function_substitute(body_provenance, "left_table", "trend")["reason"] == "wrong_representation_identifier"
    target_provenance = _typed_scene()
    target = target_provenance.source_objects[-2]
    target_provenance = replace(
        target_provenance,
        source_objects=(*target_provenance.source_objects[:-2], replace(target, provenance={"representation_identifier": "Body"}), target_provenance.source_objects[-1]),
    )
    assert resolve_function_substitute(target_provenance, "left_table", "trend")["reason"] == "wrong_representation_identifier"
    role_scene = _typed_scene()
    target = role_scene.source_objects[-2]
    wrong_role = replace(role_scene, source_objects=(*role_scene.source_objects[:-2], replace(target, source_role="furniture"), role_scene.source_objects[-1]))
    assert resolve_function_substitute(wrong_role, "left_table", "trend")["reason"] == "wrong_source_role"


def test_missing_duplicate_and_ambiguous_bindings_are_explicit():
    """Missing targets, duplicate ids, and multiple valid candidates never fall through."""
    missing = resolve_function_substitute(
        _typed_scene(left_binding=[_binding("missing")]), "left_table", "trend"
    )
    assert missing["status"] == "not_available"
    assert missing["reason"] == "unresolved_substitute_id"
    duplicate = _typed_scene(left_binding=[_binding("analysis-left")])
    duplicate = replace(
        duplicate,
        source_objects=duplicate.source_objects
        + (SourceObject(id="analysis-left", source_role="analysis_substitute", geometry_refs=("analysis-left-mesh",), provenance={"representation_identifier": "Analysis"}),),
    )
    assert resolve_function_substitute(duplicate, "left_table", "trend")["status"] == "ambiguous"
    ambiguous = _typed_scene(left_binding=[_binding("analysis-left"), _binding("analysis-right")])
    assert resolve_function_substitute(ambiguous, "left_table", "trend")["status"] == "ambiguous"


def test_missing_geometry_is_not_rewritten_as_body_fallback():
    """A missing typed target makes formal trend evidence unavailable."""
    scene = _typed_scene(left_binding=[_binding("missing")])
    result = resolve_function_substitute(scene, "left_table", "trend")
    assert result["status"] == "not_available"
    assert _geometry(scene)["trend_descriptors"]["status"] == "not_available"
    assert _geometry(scene)["trend_descriptors"]["overall_group_axis"]["angle"] is None


def test_c_a_and_d_descriptors_use_distinct_estimands():
    """Area shape, member orientation, and centroid placement remain separate."""
    geometry = _geometry(_typed_scene(add_right_to_left_group=True))
    descriptors = geometry["trend_descriptors"]
    assert descriptors["status"] == "computed"
    assert descriptors["overall_group_axis"]["basis"] == "area_weighted_total_covariance_pca"
    assert descriptors["member_frame"]["basis"] == "member_orientation_consensus"
    assert descriptors["layout_axis"]["basis"] == "between_member_centroid_pca"
    assert descriptors["overall_group_axis"]["angle"] == pytest.approx(0.0)
    assert descriptors["member_axis"]["angle"] == pytest.approx(90.0)
    assert descriptors["layout_axis"]["angle"] == pytest.approx(0.0)
    assert descriptors["overall_group_axis"]["center"] == pytest.approx((50.0, 50.0))


def test_c_uses_area_weighted_center_and_total_covariance():
    """Unequal areas weight both within-shape spread and centroid placement."""
    scene = _typed_scene(add_right_to_left_group=True)
    meshes = tuple(
        _mesh(mesh.id, Rect(cx=70.0, cy=50.0, width=20.0, height=30.0))
        if mesh.id == "analysis-right-mesh" else mesh
        for mesh in scene.geometries
    )
    descriptor = _geometry(replace(scene, geometries=meshes))["trend_descriptors"]["overall_group_axis"]
    xx = 25.0 + 3200.0 / 9.0
    yy = 75.0
    assert descriptor["center"] == pytest.approx((170.0 / 3.0, 50.0))
    assert descriptor["angle"] == pytest.approx(0.0)
    assert descriptor["strength"] == pytest.approx((xx - yy) / (xx + yy))


def test_c_is_translation_invariant_and_old_fields_remain_a_semantics():
    """Translation changes the center only; compatibility fields remain member A."""
    scene = _typed_scene(add_right_to_left_group=True)
    first = _geometry(scene)
    translated_meshes = tuple(
        replace(mesh, vertices=tuple((x + 100.0, y - 20.0, z) for x, y, z in mesh.vertices))
        if mesh.id.startswith("analysis-") else mesh
        for mesh in scene.geometries
    )
    translated = replace(scene, geometries=translated_meshes)
    second = _geometry(translated)
    assert second["trend_descriptors"]["overall_group_axis"]["angle"] == pytest.approx(
        first["trend_descriptors"]["overall_group_axis"]["angle"]
    )
    assert first["group_frame"]["angle"] == pytest.approx(0.0)
    assert first["group_axis"]["angle"] == pytest.approx(90.0)


def test_body_geometry_cannot_change_typed_trend_descriptors():
    """Changing Body meshes leaves canonical A/C/D unchanged."""
    scene = _typed_scene(add_right_to_left_group=True)
    baseline = _geometry(scene)["trend_descriptors"]
    body_changed = tuple(
        _mesh(mesh.id, Rect(cx=500.0, cy=-300.0, width=200.0, height=2.0))
        if mesh.id in {"mesh_left", "mesh_right"} else mesh
        for mesh in scene.geometries
    )
    changed = _geometry(replace(scene, geometries=body_changed))["trend_descriptors"]
    assert changed["overall_group_axis"] == baseline["overall_group_axis"]
    assert changed["member_frame"] == baseline["member_frame"]
    assert changed["member_axis"] == baseline["member_axis"]
    assert changed["layout_axis"] == baseline["layout_axis"]
    assert _geometry(scene)["group_axis"]["angle"] == pytest.approx(90.0)


def test_c_rotates_with_geometry_and_ignores_triangle_density():
    """A rigid turn rotates C; a denser triangulation preserves its moments."""
    scene = _typed_scene(add_right_to_left_group=True)
    baseline = _geometry(scene)["trend_descriptors"]["overall_group_axis"]
    angle = radians(90.0)
    rotated = tuple(
        replace(mesh, vertices=tuple((x * cos(angle) - y * sin(angle), x * sin(angle) + y * cos(angle), z) for x, y, z in mesh.vertices))
        if mesh.id.startswith("analysis-") else mesh
        for mesh in scene.geometries
    )
    rotated_axis = _geometry(replace(scene, geometries=rotated))["trend_descriptors"]["overall_group_axis"]
    assert rotated_axis["angle"] == pytest.approx(90.0)
    assert rotated_axis["strength"] == pytest.approx(baseline["strength"])

    def densify(mesh):
        """Split a rectangular mesh into four triangles with the same boundary."""
        if not mesh.id.startswith("analysis-"):
            return mesh
        center = tuple(sum(vertex[index] for vertex in mesh.vertices) / 4.0 for index in range(3))
        return replace(
            mesh,
            vertices=(*mesh.vertices, center),
            normals=(*mesh.normals, (0.0, 0.0, 1.0)),
            triangle_indices=((0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)),
        )

    dense = replace(scene, geometries=tuple(densify(mesh) for mesh in scene.geometries))
    dense_axis = _geometry(dense)["trend_descriptors"]["overall_group_axis"]
    assert dense_axis["angle"] == pytest.approx(baseline["angle"])
    assert dense_axis["strength"] == pytest.approx(baseline["strength"])


def test_isotropic_c_and_d_directions_are_undefined():
    """Zero anisotropy and one-member placement do not fabricate angles."""
    scene = _typed_scene(add_right_to_left_group=True)
    # Identical square substitutes make total covariance isotropic around the center.
    square_meshes = tuple(
        _mesh(mesh.id, Rect(cx=50.0, cy=50.0, width=10.0, height=10.0))
        if mesh.id.startswith("analysis-") else mesh
        for mesh in scene.geometries
    )
    descriptors = _geometry(replace(scene, geometries=square_meshes))["trend_descriptors"]
    assert descriptors["overall_group_axis"]["angle"] is None
    assert descriptors["overall_group_axis"]["strength"] is None
    assert descriptors["overall_group_axis"]["direction_status"] == "undefined"
    assert descriptors["layout_axis"]["angle"] is None
    assert descriptors["layout_axis"]["direction_status"] == "undefined"


def test_partial_invalid_and_not_available_have_no_formal_numeric_descriptor():
    """Usable siblings stay diagnostic and never complete a partial group."""
    partial = _typed_scene(right_binding=None, add_right_to_left_group=True)
    # Remove the right binding while retaining its body geometry.
    right = replace(partial.source_objects[1], factual_properties={})
    partial = replace(partial, source_objects=(partial.source_objects[0], right, *partial.source_objects[2:]))
    partial_desc = _geometry(partial)["trend_descriptors"]
    assert partial_desc["status"] == "partial"
    assert partial_desc["overall_group_axis"]["angle"] is None
    assert partial_desc["diagnostic_evidence"]["status"] == "diagnostic_only"
    invalid = _typed_scene(
        left_binding=[_binding("analysis-left", representation_identifier="Body")],
        add_right_to_left_group=True,
    )
    invalid_desc = _geometry(invalid)["trend_descriptors"]
    assert invalid_desc["status"] == "partial"
    assert invalid_desc["member_axis"]["angle"] is None
    unavailable = _geometry(_typed_scene(left_binding=[], right_binding=[], add_right_to_left_group=True))["trend_descriptors"]
    assert unavailable["status"] == "not_available"
    assert unavailable["layout_axis"]["strength"] is None


def test_json_serialization_rejects_nonfinite_trend_values():
    """The complete evidence record remains strict JSON serializable."""
    result = describe_group_relations(_typed_scene(add_right_to_left_group=True))
    json.dumps(result, allow_nan=False)
