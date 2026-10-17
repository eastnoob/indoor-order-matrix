"""Analytic planar scenes for shared representation and occupancy consumers."""

from dataclasses import replace

import pytest

from ..features import analysis_substitute_discovery as discovery
from ..features.affordance.models import Rect
from ..features.group_self_description import describe_group_relations
from ..features.neutral_scene_views import analysis_scene_view
from ..features.room_analysis_model import build_room_analysis_model
from ..features.scene_contract import SourceObject, UncertaintyRecord
from ..features.scene_evaluator import (
    _inferred_region_gap_path_occupancy_row, _negative_space_descriptor, evaluate_scene,
)
from .test_neutral_scene_analysis_regression import _mesh, _neutral_scene


def _binding(owner="A", target="T", consumer="physical_occupancy"):
    """Return a source-owned binding with truthful generated provenance."""
    representation = "Analysis" if consumer == "trend" else "GeneratedProxy"
    return {
        "source_object_id": owner, "substitute_id": target, "consumer": consumer,
        "substitute_kind": "MassPatch",
        "analysis_role": "analysis_geometry_substitute" if consumer == "trend" else "physical_occupancy_substitute",
        "representation_identifier": representation,
        "provenance": {"representation_identifier": representation},
    }


def _scene(*, binding=True, original_geometry=True, coverage=("A",)):
    """Create a 100 square unit domain, two 4 unit originals, and a 9 unit proxy."""
    base = _neutral_scene()
    floor = replace(base.source_objects[2], geometry_refs=("floor",))
    a = SourceObject(id="A", source_role="furniture", geometry_refs=("a",) if original_geometry else (),
                     factual_properties={"group": "one", "OM_FunctionSubstitutes": [_binding()]} if binding else {"group": "one"},
                     uncertainties=() if original_geometry else (_missing_geometry(),))
    b = SourceObject(id="B", source_role="furniture", geometry_refs=("b",), factual_properties={"group": "two"})
    target = SourceObject(id="T", source_role="analysis_substitute", geometry_refs=("t",),
                          factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": coverage}},
                          provenance={"representation_identifier": "GeneratedProxy"})
    return replace(base, source_objects=(a, b, floor, target),
                   geometries=(_mesh("floor", Rect(5, 5, 10, 10)), _mesh("a", Rect(2, 2, 2, 2)),
                               _mesh("b", Rect(8, 8, 2, 2)), _mesh("t", Rect(3, 3, 3, 3))),
                   analysis_domain=replace(base.analysis_domain, geometry_refs=("floor",)),
                   authored_groups=(replace(base.authored_groups[0], id="one", member_refs=("A",)),
                                    replace(base.authored_groups[1], id="two", member_refs=("B",))),
                   authored_affordances=(), authored_grid_axes=(), authored_grids=(), openings=(), surfaces=(),
                   context=replace(base.context, walking_body_profiles=({"required_path_width": 1.0},)))


def _replace_source(scene, source_id, **changes):
    """Edit one immutable fixture source without altering other facts."""
    if changes.get("geometry_refs") == ():
        changes["uncertainties"] = (_missing_geometry(),)
    return replace(scene, source_objects=tuple(replace(item, **changes) if item.id == source_id else item for item in scene.source_objects))


def _missing_geometry():
    """Supply the transport contract's required missing-geometry diagnostic."""
    return UncertaintyRecord(code="missing_geometry", message="Fixture has no geometry", source_refs=(), operation="fixture", severity="warning")


def test_substitute_precedes_missing_original_projection():
    """A valid proxy replaces an original without geometry; 100 - 9 - 4 = 87."""
    view = analysis_scene_view(_scene(original_geometry=False))
    assert view["_analysis_view"]["physical_occupancy_status"] == "computed"
    assert {item["id"] for item in view["physical_occupancy"]} == {"T", "B"}
    assert _negative_space_descriptor(view)["negative_space_area"] == pytest.approx(87)


@pytest.mark.parametrize("coverage", [(), ("A", "A"), ("A", "extra"), ("",), (1,)])
def test_invalid_coverage_is_unknown_without_original_fallback(coverage):
    """Exact coverage declarations cannot silently discard or invent owners."""
    view = analysis_scene_view(_scene(coverage=coverage))
    assert view["_analysis_view"]["physical_occupancy_unresolved_source_ids"] == ["A"]
    assert [item["id"] for item in view["physical_occupancy"]] == ["B"]


def test_exact_many_to_one_counts_target_once():
    """Two owners declare one exact proxy, so occupied area is 9 rather than 18."""
    scene = _replace_source(_scene(coverage=("A", "B")), "B", factual_properties={"OM_FunctionSubstitutes": [_binding("B")]})
    view = analysis_scene_view(scene)
    assert len(view["physical_occupancy"]) == 1
    assert view["physical_occupancy"][0]["represented_source_ids"] == ["A", "B"]
    assert _negative_space_descriptor(view)["negative_space_area"] == pytest.approx(91)


def test_mixed_domain_member_proxy_cannot_be_split_by_guessing():
    """A combined boundary/interior proxy leaves the interior owner unknown."""
    scene = _replace_source(_scene(coverage=("A", "B")), "B", factual_properties={"OM_FunctionSubstitutes": [_binding("B")]})
    scene = replace(scene, analysis_domain=replace(scene.analysis_domain, provenance={"boundary_member_source_ids": ["B"]}))
    view = analysis_scene_view(scene)
    assert view["physical_occupancy"] == []
    assert view["_analysis_view"]["physical_occupancy_unresolved_source_ids"] == ["A"]


@pytest.mark.parametrize("refs,reason", [((), "missing_geometry"), (("t", "lost"), "missing_geometry"), (("t", "t"), "duplicate_geometry_ref")])
def test_partial_or_duplicate_geometry_is_not_qualified(refs, reason):
    """All selected planar geometry refs must be uniquely and completely resolved."""
    scene = _replace_source(_scene(), "T", geometry_refs=refs)
    result = discovery.resolve_source_representation(scene, "A", "physical_occupancy")
    assert result["status"] == "unresolved"
    assert result["reason"] == reason


def test_unknown_propagates_and_preserves_known_evidence_and_export_shape():
    """Unlocalized uncertainty masks certificates and scores but retains known mass."""
    scene = _scene(coverage=())
    view = analysis_scene_view(scene)
    negative = _negative_space_descriptor(view)
    assert negative["status"] == "not_available"
    assert negative["blocker_evidence"] == ["B"]
    assert negative["blocker_overlap_area"] == pytest.approx(4)
    matrix = evaluate_scene(view)
    assert matrix["negative_space_graph"]["status"] == "not_available"
    dependent = [row for row in matrix["rows"] if "free_space" in row["metric"] or "negative_space" in row["metric"] or row["metric"] == "inferred_region_gap_path_occupancy_ratio"]
    assert dependent and all(row["status"] == "not_available" and row["score"] is None for row in dependent)
    assert matrix["adapter_payload"]["route_topology_handoff"]["status"] == "not_available"
    model = build_room_analysis_model(view, matrix)
    assert set(model) == {"contract", "source", "base_layer", "object_layer", "region_layer", "network_layer", "reference_layer", "metric_layer", "summary_layer"}
    assert model["network_layer"]["negative_space_graph"]["status"] == "not_available"


def test_furniture_exclusion_vetoes_direct_group_and_affordance_contribution():
    """Raw authored membership stays a fact while excluded members contribute no frame."""
    scene = _replace_source(_scene(binding=False), "A", factual_properties={"furniture_analysis_participation": "excluded", "group": "one"})
    view = analysis_scene_view(scene)
    assert [item["id"] for item in view["objects"]] == ["B"]
    assert {item["id"] for item in view["physical_occupancy"]} == {"A", "B"}
    description = describe_group_relations(scene)
    group = next(item for item in description["group_geometry"] if item["target_id"] == "one")
    assert group["support_area"] is None
    assert group["member_geometry"] == []
    assert group["trend_descriptors"]["status"] == "not_available"
    assert scene.authored_groups[0].member_refs == ("A",)


def test_descriptor_policies_are_executed(monkeypatch):
    """Changing shared fallback and query descriptors changes actual resolution."""
    registry = discovery.load_substitute_registry()
    registry["operations"]["physical_occupancy"]["fallback"] = "unresolved"
    monkeypatch.setattr(discovery, "load_substitute_registry", lambda: registry)
    assert discovery.resolve_source_representation(_scene(binding=False), "A", "physical_occupancy")["status"] == "unresolved"
    registry["operations"]["physical_occupancy"]["coverage"] = "invented_policy"
    assert discovery.resolve_source_representation(_scene(), "A", "physical_occupancy")["reason"] == "unknown_coverage_policy"


def test_invalid_sibling_binding_invalidates_shared_target():
    """An exact proxy requires every owner to qualify for the same operation."""
    binding = {**_binding("B"), "analysis_role": "analysis_geometry_substitute"}
    scene = _replace_source(_scene(coverage=("A", "B")), "B",
                            factual_properties={"OM_FunctionSubstitutes": [binding]})
    result = discovery.resolve_source_representation(scene, "A", "physical_occupancy")
    assert result["status"] == "unresolved"
    assert result["provenance"] == _binding()["provenance"]
    assert result["reason"] == "wrong_analysis_role"


@pytest.mark.parametrize("unknown", [False, True])
def test_authored_path_and_gap_export_respects_occupancy_availability(unknown):
    """Actual paths must neither crash nor certify inferred gaps over unknown mass."""
    scene = _scene(coverage=() if unknown else ("A",))
    scene = replace(scene,
                    source_objects=scene.source_objects + (SourceObject(
                        id="path", source_role="path", geometry_refs=("p",)),),
                    geometries=tuple(_mesh("b", Rect(8, 2, 2, 2)) if mesh.id == "b" else mesh
                                     for mesh in scene.geometries) + (_mesh("p", Rect(5, 2, 8, 1)),))
    matrix = evaluate_scene(scene)
    geometry = matrix["adapter_payload"]["evidence_geometry"]
    assert geometry["inferred_region_gap_paths"]["count"] > 0
    if unknown:
        for metric in ("candidate_path_area_ratio_proxy", "candidate_path_region_pair_ratio_proxy",
                       "inferred_region_gap_path_occupancy_ratio"):
            row = next(item for item in matrix["rows"] if item["metric"] == metric)
            assert row["status"] == "not_available" and row["score"] is None
        for item in geometry["inferred_region_gap_paths"]["items"]:
            assert item["clear_status"] == "unknown"
            assert item["occupancy_ratio"] is None
            assert item["free_space_overlap_ratio"] is None
        assert geometry["free_space_polygons"]["count"] is None
        handoff = matrix["adapter_payload"]["route_topology_handoff"]
        assert handoff["inferred_gap_paths"]["clear_count"] is None
        assert handoff["inferred_gap_paths"]["occupied_count"] is None
    else:
        assert matrix["negative_space_graph"].get("status") != "not_available"


def test_legacy_gap_occupiers_preserve_object_and_boundary_kinds():
    """Legacy gap consumers retain their object and physical boundary semantics."""
    view = analysis_scene_view(_scene(binding=False))
    view.pop("_analysis_view")
    view.pop("_neutral_scene")
    view["physical_blockers"] = [{**view["objects"][0], "id": "wall", "role": "wall"}]
    row = _inferred_region_gap_path_occupancy_row(view, [], [{
        "id": "gap", "region_a": "unbound_a", "region_b": "unbound_b", "rect": Rect(2, 2, 2, 2),
    }])
    assert row["inferred_region_gap_path_occupancy_evidence"][0]["occupiers"] == [
        {"id": "A", "kind": "object_footprint", "overlap_area": 4},
        {"id": "wall", "kind": "physical_boundary_geometry", "overlap_area": 4},
    ]
