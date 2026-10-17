"""Focused contract tests for the exact-cell FreeSpaceField instance."""

from __future__ import annotations

import pytest
from dataclasses import replace

from ..features.field_core import FieldQuery, FieldStatus
from ..features.free_space_field import FreeSpaceField
from ..features.geometry_substitutes import mass_patch_from_mesh
from ..features.geometry_views import plan_projection
from ..features.neutral_scene_views import analysis_scene_view
from ..features.scene_contract import SourceObject
from ..features.affordance.models import Rect
from .test_physical_occupancy_resolution import _binding, _mesh, _replace_source, _scene


def _query(**overrides):
    """Build a stable whole-height query for the fixture field."""
    values = {
        "domain_id": "room-a",
        "frame": "world-xy",
        "revision": "q1",
        "tolerance": 1e-9,
    }
    values.update(overrides)
    return FieldQuery(**values)


def _domain():
    """Return a square domain with a central hole."""
    return {
        "id": "room-a",
        "frame": "world-xy",
        "components": [
            {
                "exterior": ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)),
                "holes": (((1.5, 1.5), (2.5, 1.5), (2.5, 2.5), (1.5, 2.5)),),
            }
        ],
    }


def _record(identifier, exterior, *, represented=("source-1",), status="original"):
    """Build one resolved physical-occupancy record."""
    return {
        "id": identifier,
        "geometry_components": [{"exterior": exterior, "holes": ()}],
        "represented_source_ids": list(represented),
        "representation_status": status,
        "representation_provenance": {"representation_identifier": "Analysis"},
    }


def _field(records=(), **changes):
    """Build the smallest valid exact-cell field."""
    return FreeSpaceField(**{
        "domain": _domain(), "origin": (0.0, 0.0), "spacing": 1.0,
        "n_rows": 4, "n_cols": 4, "physical_occupancy": records,
        "unresolved_source_ids": (), "query_context": {"domain_id": "room-a", "frame": "world-xy"},
        "frame": "world-xy", "origin_offset": (0.0, 0.0),
        "algorithm_version": "free-space-test/1", "schema_version": "free-space-test/1", **changes,
    })


def _whole_hole_domain():
    """Return a domain whose central lattice cell is entirely a hole."""
    return {
        "id": "room-a",
        "frame": "world-xy",
        "components": [
            {
                "exterior": ((0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (0.0, 3.0)),
                "holes": (((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)),),
            }
        ],
    }


def test_partial_domain_cell_uses_positive_intersection_and_hole_is_outside() -> None:
    """Partial domain area is eligible, while a fully holed cell is outside."""
    field = _field(
        [
            _record(
                "wall",
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            )
        ]
    )
    result = field.evaluate((0, 0), _query())
    assert result.status is FieldStatus.ESTABLISHED
    assert result.value is True
    hole_field = FreeSpaceField(
        domain=_whole_hole_domain(),
        origin=(0.0, 0.0),
        spacing=1.0,
        n_rows=3,
        n_cols=3,
        physical_occupancy=[],
        unresolved_source_ids=(),
        query_context={"domain_id": "room-a", "frame": "world-xy"},
        frame="world-xy",
        origin_offset=(0.0, 0.0),
    )
    assert hole_field.evaluate((1, 1), _query()).status is FieldStatus.OUTSIDE


def test_grid_and_domain_validation_distinguish_invalid_from_unavailable() -> None:
    """Malformed domains/grids are invalid while an absent domain is unavailable."""
    with pytest.raises(ValueError):
        FreeSpaceField(
            domain=_domain(),
            origin=(0.0, 0.0),
            spacing=0.0,
            n_rows=4,
            n_cols=4,
            physical_occupancy=[],
            unresolved_source_ids=(),
            query_context={"domain_id": "room-a", "frame": "world-xy"},
            frame="world-xy",
            origin_offset=(0.0, 0.0),
        )
    invalid = FreeSpaceField(
        domain={"id": "room-a", "components": [{"exterior": ((0, 0), (1, 0))}]},
        origin=(0.0, 0.0),
        spacing=1.0,
        n_rows=1,
        n_cols=1,
        physical_occupancy=[],
        unresolved_source_ids=(),
        query_context={"domain_id": "room-a", "frame": "world-xy"},
        frame="world-xy",
        origin_offset=(0.0, 0.0),
    )
    assert invalid.evaluate((0, 0), _query()).status is FieldStatus.INVALID
    unavailable = FreeSpaceField(
        domain=None,
        origin=(0.0, 0.0),
        spacing=1.0,
        n_rows=1,
        n_cols=1,
        physical_occupancy=[],
        unresolved_source_ids=(),
        query_context={"domain_id": "room-a", "frame": "world-xy"},
        frame="world-xy",
        origin_offset=(0.0, 0.0),
    )
    assert unavailable.evaluate((0, 0), _query()).status is FieldStatus.NOT_AVAILABLE


def test_unknown_support_does_not_erase_known_occupied_cells() -> None:
    """Known positive occupancy wins while unresolved support keeps other cells unknown."""
    field = _field(
        [
            _record(
                "known",
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            )
        ]
    )
    field_with_unknown = FreeSpaceField(
        domain=_domain(),
        origin=(0.0, 0.0),
        spacing=1.0,
        n_rows=4,
        n_cols=4,
        physical_occupancy=field.physical_occupancy,
        unresolved_source_ids=("missing-source",),
        query_context={"domain_id": "room-a", "frame": "world-xy"},
        frame="world-xy",
        origin_offset=(0.0, 0.0),
    )
    assert field_with_unknown.evaluate((0, 0), _query()).value is True
    unknown = field_with_unknown.evaluate((3, 3), _query())
    assert unknown.status is FieldStatus.UNKNOWN
    assert unknown.value is None


def test_unsupported_section_is_unavailable_and_query_context_must_match() -> None:
    """Whole-height fields reject unsupported sections and mismatched context."""
    field = _field()
    section = field.evaluate(
        (3, 3),
        _query(plane={"axis": "z", "value": 1.6}, revision="section"),
    )
    assert section.status is FieldStatus.NOT_AVAILABLE
    assert field.evaluate((0, 0), _query(domain_id="other")).status is FieldStatus.INVALID
    assert field.evaluate((0, 0), _query(frame="other")).status is FieldStatus.INVALID


def test_batch_preserves_order_duplicates_and_empty_is_not_walkability() -> None:
    """Batch lookup is exact and ordered; empty occupancy is not a walkability claim."""
    field = _field()
    query = _query()
    targets = [(3, 3), (3, 3), (0, 0)]
    samples = field.evaluate_many(targets, query)
    assert len(samples) == len(targets)
    assert tuple(sample.value for sample in samples) == (False, False, False)
    assert all(sample.status is FieldStatus.ESTABLISHED for sample in samples)
    assert all(sample.provenance["algorithm_version"] == "free-space-test/1" for sample in samples)


def test_missing_occupancy_channel_is_not_available_and_bad_geometry_is_invalid() -> None:
    """Absent occupancy is unavailable while malformed occupancy geometry is invalid."""
    missing = FreeSpaceField(
        domain=_domain(),
        origin=(0.0, 0.0),
        spacing=1.0,
        n_rows=4,
        n_cols=4,
        physical_occupancy=None,
        unresolved_source_ids=(),
        query_context={"domain_id": "room-a", "frame": "world-xy"},
        frame="world-xy",
        origin_offset=(0.0, 0.0),
    )
    assert missing.evaluate((0, 0), _query()).status is FieldStatus.NOT_AVAILABLE
    bad = _field(
        [
            {
                "id": "bad",
                "geometry_components": [{"exterior": ((0.0, 0.0), (1.0, 0.0))}],
                "represented_source_ids": ["bad-source"],
            }
        ]
    )
    assert bad.evaluate((0, 0), _query()).status is FieldStatus.INVALID


def test_invalid_origin_and_duplicate_or_out_of_range_targets_are_rejected() -> None:
    """Non-finite lattice data and malformed exact targets remain invalid."""
    with pytest.raises(ValueError):
        FreeSpaceField(
            domain=_domain(),
            origin=(float("nan"), 0.0),
            spacing=1.0,
            n_rows=4,
            n_cols=4,
            physical_occupancy=[],
            unresolved_source_ids=(),
            query_context={"domain_id": "room-a", "frame": "world-xy"},
            frame="world-xy",
            origin_offset=(0.0, 0.0),
        )
    field = _field()
    assert field.evaluate((4, 0), _query()).status is FieldStatus.INVALID
    assert field.evaluate((0, 0, 0), _query()).status is FieldStatus.INVALID


def test_accepted_substitute_is_conditional_and_retains_unknown_support() -> None:
    """Accepted proxy geometry limits both occupied and empty conclusions."""
    field = _field(
        [
            _record(
                "proxy",
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                represented=("chair-1", "plant-1"),
                status="accepted",
            )
        ]
    )
    sample = field.evaluate((0, 0), _query())
    assert sample.status is FieldStatus.CONDITIONAL
    assert sample.value is True
    assert sample.source_ids == ("chair-1", "plant-1")
    assert "accepted substitute" in sample.explanation


def test_public_handoff_inputs_are_immutable_and_duplicate_owners_are_invalid() -> None:
    """Frozen handoff metadata cannot be reassigned and owner overlap is refused."""
    field = _field()
    with pytest.raises(AttributeError):
        field.origin_offset = (1.0, 1.0)
    with pytest.raises(TypeError):
        field.query_context["frame"] = "other"
    duplicate = _field(
        [
            _record("a", ((0, 0), (1, 0), (1, 1), (0, 1))),
            _record("b", ((2, 0), (3, 0), (3, 1), (2, 1))),
        ]
    )
    assert duplicate.evaluate((0, 0), _query()).status is FieldStatus.INVALID


def _component(left=0.0, bottom=0.0, right=4.0, top=4.0):
    """Return explicit rectangle polygon geometry."""
    return {"exterior": [(left, bottom), (right, bottom), (right, top), (left, top)], "holes": []}


def _from_scene(scene):
    """Pass a real resolved view and a separately explicit domain into the field."""
    view = analysis_scene_view(scene)
    frame = view["_analysis_view"]["analysis_plane"]
    offset = view["_analysis_view"]["origin_offset"]
    # Project only the explicit domain refs, using the same frame/translation as occupancy.
    components = []
    for mesh in scene.geometries:
        if mesh.id in scene.analysis_domain.geometry_refs:
            for component in plan_projection(mass_patch_from_mesh(mesh), scene.context.analysis_plane).components:
                components.append({"exterior": [(x + offset[0], y + offset[1]) for x, y in component["exterior"]],
                    "holes": [[(x + offset[0], y + offset[1]) for x, y in ring] for ring in component.get("holes", ())]})
    field = _field(view["physical_occupancy"],
        domain={"id": scene.analysis_domain.id, "frame": frame, "components": components},
        frame=frame, query_context={"domain_id": scene.analysis_domain.id, "frame": frame},
        origin_offset=view["_analysis_view"]["origin_offset"], n_rows=10, n_cols=10,
        unresolved_source_ids=view["_analysis_view"]["physical_occupancy_unresolved_source_ids"])
    return view, field, _query(domain_id=scene.analysis_domain.id, frame=frame)


def test_positive_sliver_is_not_compared_to_length_tolerance():
    """Any positive domain/occupied area survives a larger linear tolerance."""
    sliver = _component(0, 0, 1e-10, 1)
    field = _field([_record("sliver", sliver["exterior"])],
                   domain={"id": "room-a", "frame": "world-xy", "components": [sliver]})
    sample = field.evaluate((0, 0), _query(tolerance=0.1))
    assert sample.status is FieldStatus.ESTABLISHED and sample.value is True
    assert sample.support["domain_intersection_area"] == pytest.approx(1e-10)


def test_line_contact_and_clipped_out_occupancy_do_not_fill_a_cell():
    """Only mass within the positive-area domain intersection counts."""
    field = _field([_record("touch", _component(1, 0, 2, 1)["exterior"])])
    assert field.evaluate((0, 0), _query()).value is False
    clipped = _field([_record("outside", _component(0.7, 0, 1, 1)["exterior"])],
        domain={"id": "room-a", "frame": "world-xy", "components": [_component(0, 0, 0.5, 1)]})
    assert clipped.evaluate((0, 0), _query()).value is False
    assert clipped.evaluate((0, 1), _query()).status is FieldStatus.OUTSIDE
    point_touch = _field([_record("touch", _component(1, 1, 1.4, 1.4)["exterior"])])
    assert point_touch.evaluate((0, 0), _query()).value is False


def test_domain_hole_excludes_mass_and_retains_outside_support():
    """Mass inside a domain hole cannot establish interior occupancy."""
    field = _field([_record("hole", _component(1, 1, 2, 2)["exterior"])], domain=_whole_hole_domain())
    sample = field.evaluate((1, 1), _query())
    assert sample.status is FieldStatus.OUTSIDE and sample.value is None
    assert sample.support["target"] == (1, 1)
    assert sample.support["cell_bounds"] == (1, 1, 2, 2)
    assert sample.support["domain_intersection_area"] == 0
    assert field.evaluate((1, 0), _query()).value is False


@pytest.mark.parametrize("context", [
    {"plane": {"axis": "z", "value": 1.6}}, {"height_band": (0, 2)},
    {"demand": {"width": 1}}, {"geometry_query": "exact_world_plane_section"}, {"domain_id": ""},
])
def test_constructor_cannot_relabel_section_or_demand_as_whole_height(context):
    """The constructor requires a coherent whole-height context."""
    with pytest.raises(ValueError):
        _field(query_context={"domain_id": "room-a", "frame": "world-xy", **context})


@pytest.mark.parametrize("changes,status", [
    ({"domain_id": "other"}, FieldStatus.INVALID), ({"frame": "other"}, FieldStatus.INVALID),
    ({"plane": {}}, FieldStatus.INVALID),
    ({"plane": {"axis": "z", "value": "high"}}, FieldStatus.INVALID),
    ({"plane": {"origin": (0, 0, 0), "normal": (0, 0, 0)}}, FieldStatus.INVALID),
    ({"plane": {"axis": "z", "value": 1.6}}, FieldStatus.NOT_AVAILABLE),
    ({"plane": {"origin": (0, 0, 0), "normal": (1, 0, 1)}}, FieldStatus.NOT_AVAILABLE),
    ({"height_band": (0, 2)}, FieldStatus.NOT_AVAILABLE),
    ({"height_band": (2, 0)}, FieldStatus.INVALID), ({"height_band": "head"}, FieldStatus.INVALID),
    ({"demand": {"required_path_width": 0.9}}, FieldStatus.NOT_AVAILABLE), ({"demand": 1}, FieldStatus.INVALID),
])
def test_query_refusals_precede_missing_channel_and_never_compute(changes, status):
    """Invalid and unsupported requests precede channel availability."""
    for field in (_field(), _field(domain=None)):
        sample = field.evaluate((0, 0), _query(**changes))
        assert sample.status is status and sample.value is None


def test_non_field_query_has_an_explicit_type_error():
    """The sample contract requires FieldQuery rather than arbitrary attributes."""
    with pytest.raises(TypeError, match="FieldQuery"):
        _field().evaluate((0, 0), {})


@pytest.mark.parametrize("ids,owners", [([""], [("a",)]), ([4], [("a",)]),
    (["x"], [("a", "a")]), (["x"], [(4,)]), (["x"], [()]),
    (["x", "x"], [("a",), ("b",)]), (["x", "y"], [("a",), ("a",)])])
def test_selected_and_represented_identities_are_unique_strings(ids, owners):
    """Duplicate selected IDs or original owners invalidate exact-once accounting."""
    records = [_record(identifier, _component(0, 0, 1, 1)["exterior"], represented=coverage)
               for identifier, coverage in zip(ids, owners)]
    assert _field(records).evaluate((0, 0), _query()).status is FieldStatus.INVALID


@pytest.mark.parametrize("geometry", [None, [], "absent"])
def test_absent_or_empty_selected_geometry_is_unknown(geometry):
    """Absent selected geometry does not prove physical emptiness."""
    record = _record("missing", _component()["exterior"])
    if geometry == "absent":
        record.pop("geometry_components")
    else:
        record["geometry_components"] = geometry
    sample = _field([record]).evaluate((0, 0), _query())
    assert sample.status is FieldStatus.UNKNOWN and sample.source_ids == ("source-1",)


@pytest.mark.parametrize("geometry", [[{"exterior": [(0, 0), (1, 0)]}], [_component(0, 0, float("nan"), 1)], "polygon"])
def test_malformed_geometry_is_invalid_not_unknown(geometry):
    """Malformed topology or coordinates cannot supply an occupancy claim."""
    record = _record("bad", _component()["exterior"])
    record["geometry_components"] = geometry
    assert _field([record]).evaluate((0, 0), _query()).status is FieldStatus.INVALID


def test_public_metadata_and_sample_snapshots_are_fully_immutable():
    """Input mutation cannot alter geometry, evidence, or cached collections."""
    records = [_record("table", _component(0, 0, 1, 1)["exterior"])]
    records[0]["representation_provenance"]["audit"] = ["original"]
    domain = _domain()
    context = {"domain_id": "room-a", "frame": "world-xy", "audit": ["frozen"]}
    field = _field(records, domain=domain, query_context=context)
    before = field.evaluate((0, 0), _query())
    records[0]["geometry_components"].clear()
    records[0]["representation_provenance"]["audit"].append("changed")
    domain["components"].clear()
    context["audit"].append("changed")
    assert field.evaluate((0, 0), _query()) == before
    for name in ("domain", "frame", "provenance", "representation", "value_schema", "query_context",
                 "physical_occupancy", "unresolved_source_ids", "origin_offset", "_sealed"):
        with pytest.raises(AttributeError):
            setattr(field, name, None)
    with pytest.raises(AttributeError):
        del field.domain
    with pytest.raises(TypeError):
        before.provenance["selected_records"][0]["representation_provenance"]["audit"][0] = "changed"
    assert isinstance(field._occupancy_shapes, tuple)
    assert isinstance(field._unknown_owners, (tuple, frozenset))


def test_empty_keeps_query_evidence_and_scalar_batch_equivalence():
    """Empty has traceable physical evidence without a clearance certificate."""
    record = _record("table", _component(0, 0, 1, 1)["exterior"])
    field = _field([record], origin_offset=(10, 20))
    query = _query(revision="audit-q", tolerance=0.005)
    targets = [(3, 3), (0, 0), (3, 3)]
    batch = field.evaluate_many(targets, query)
    assert batch == tuple(field.evaluate(target, query) for target in targets)
    sample = batch[0]
    assert sample.value is False and sample.status is FieldStatus.ESTABLISHED
    assert "not a walkability or clearance claim" in sample.explanation
    assert sample.query is query and sample.source_ids == ("source-1",)
    assert sample.provenance["frame"] == "world-xy"
    assert sample.provenance["origin_offset"] == (10, 20)
    assert sample.provenance["input_query_context"] == field.query_context
    assert sample.provenance["units"] == "boolean" and sample.provenance["geometry_units"] == "m"
    assert sample.provenance["tolerance"] == 0.005
    assert sample.provenance["selected_records"][0]["representation_provenance"] == record["representation_provenance"]
    assert sample.support["cell_bounds"] == (3, 3, 4, 4)
    assert sample.support["lattice"]["spacing"] == 1


def test_real_view_keeps_furniture_plant_counter_mass_with_nonzero_offset():
    """Real resolved geometry retains excluded non-furniture mass in the translated frame."""
    scene = _scene(binding=False)
    scene = replace(scene, source_objects=scene.source_objects + (
        SourceObject(id="plant", source_role="plant", geometry_refs=("plant-mesh",),
                     factual_properties={"furniture_analysis_participation": "excluded"}),
        SourceObject(id="counter", source_role="furniture", geometry_refs=("counter-mesh",),
                     factual_properties={"furniture_analysis_participation": "excluded"}),),
        geometries=scene.geometries + (_mesh("plant-mesh", Rect(5.5, 1.5, 1, 1)), _mesh("counter-mesh", Rect(6.5, 3.5, 1, 1))))
    scene = replace(scene, geometries=tuple(replace(mesh, vertices=tuple((x + 20, y - 30, z) for x, y, z in mesh.vertices)) for mesh in scene.geometries))
    view, field, query = _from_scene(scene)
    assert {record["id"] for record in view["objects"]} == {"A", "B"}
    assert field.origin_offset == (-20, 30)
    for target, owner in [((1, 1), "A"), ((1, 5), "plant"), ((3, 6), "counter")]:
        sample = field.evaluate(target, query)
        assert sample.status is FieldStatus.ESTABLISHED and sample.value is True
        assert sample.source_ids == (owner,)
        audit = next(record for record in sample.provenance["selected_records"] if record["id"] == owner)
        assert audit["representation_provenance"] == {}
        assert audit["_source_geometry_refs"]
    assert field.evaluate((0, 0), query).value is False


def test_real_view_selects_many_to_one_once():
    """Two originals share one accepted geometry and retain representation evidence."""
    scene = _replace_source(_scene(coverage=("A", "B")), "B", factual_properties={"OM_FunctionSubstitutes": [_binding("B")]})
    view, field, query = _from_scene(scene)
    assert len(view["physical_occupancy"]) == len(field.physical_occupancy) == 1
    sample = field.evaluate((2, 2), query)
    assert sample.status is FieldStatus.CONDITIONAL and sample.source_ids == ("A", "B")
    assert sample.provenance["occupied_record_ids"] == ("T",)
    assert sample.provenance["selected_records"][0]["representation_provenance"] == _binding()["provenance"]
    assert field.evaluate((9, 9), query).status is FieldStatus.CONDITIONAL


def test_real_view_boundary_door_is_support_and_interior_door_counts():
    """Exact boundary membership excludes a door; the same interior role keeps mass."""
    scene = _scene(binding=False)
    scene = replace(scene, source_objects=scene.source_objects + (
        SourceObject(id="boundary-door", source_role="door", geometry_refs=("boundary-door-mesh",)),
        SourceObject(id="interior-door", source_role="door", geometry_refs=("interior-door-mesh",)),),
        geometries=scene.geometries + (_mesh("boundary-door-mesh", Rect(0.25, 5.5, 0.5, 1)), _mesh("interior-door-mesh", Rect(5.5, 5.5, 1, 1))),
        analysis_domain=replace(scene.analysis_domain, provenance={"boundary_member_source_ids": ["boundary-door"]}))
    view, field, query = _from_scene(scene)
    assert "boundary-door" not in {record["id"] for record in view["physical_occupancy"]}
    assert field.evaluate((5, 0), query).value is False
    sample = field.evaluate((5, 5), query)
    assert sample.value is True and sample.source_ids == ("interior-door",)


def test_real_view_missing_source_stays_unknown_and_known_mass_survives():
    """Actual upstream missing-geometry inventory reaches the field unchanged."""
    view, field, query = _from_scene(_scene(binding=False, original_geometry=False))
    assert view["_analysis_view"]["physical_occupancy_unresolved_source_ids"] == ["A"]
    assert field.evaluate((0, 0), query).status is FieldStatus.UNKNOWN
    sample = field.evaluate((7, 7), query)
    assert sample.value is True and sample.provenance["unknown_source_ids"] == ("A",)


@pytest.mark.parametrize("changes", [
    {"origin": (True, 0)}, {"spacing": True}, {"n_rows": True}, {"n_cols": -1},
    {"origin_offset": (0, float("nan"))}, {"spacing": 1e308},
])
def test_invalid_lattice_numbers_are_rejected_before_geometry(changes):
    """Boolean, nonfinite, and overflowing lattice parameters cannot reach GEOS."""
    with pytest.raises(ValueError):
        _field(**changes)


@pytest.mark.parametrize("domain", [
    {"id": "other", "frame": "world-xy", "components": [_component()]},
    {"id": "room-a", "frame": "other", "components": [_component()]},
    {"id": "room-a", "frame": "world-xy", "components": []},
    {"id": "room-a", "frame": "world-xy", "components": [{"exterior": [(0, 0), (1, 1), (1, 0), (0, 1)]}]},
])
def test_domain_identity_frame_and_topology_are_validated(domain):
    """Invalid explicit domains cannot fall back to a rectangle or repaired polygon."""
    assert _field(domain=domain).evaluate((0, 0), _query()).status is FieldStatus.INVALID


def test_nonzero_lattice_origin_uses_row_then_column_and_audits_original_geometry():
    """Exact target coordinates advance X by column and Y by row."""
    domain = {"id": "room-a", "frame": "world-xy", "components": [_component(10, 20, 12, 22)]}
    field = _field([_record("table", _component(11, 20, 12, 21)["exterior"])],
                   domain=domain, origin=(10, 20), n_rows=2, n_cols=2)
    assert field.evaluate((0, 1), _query()).value is True
    assert field.evaluate((1, 0), _query()).value is False
    assert field.domain["components"][0]["exterior"] == tuple(domain["components"][0]["exterior"])
    for target in ((-1, 0), (2, 0), (0, 2), (True, 0), [0, 0]):
        assert field.evaluate(target, _query()).status is FieldStatus.INVALID


def test_mixed_original_and_proxy_field_keeps_all_estimates_conditional():
    """A field-wide proxy limitation remains truthful at cells occupied by originals."""
    field = _field([
        _record("table", _component(0, 0, 1, 1)["exterior"]),
        _record("proxy", _component(3, 0, 4, 1)["exterior"], represented=("plant",), status="accepted"),
    ])
    samples = field.evaluate_many([(0, 0), (0, 3), (3, 3)], _query())
    assert [sample.value for sample in samples] == [True, True, False]
    assert all(sample.status is FieldStatus.CONDITIONAL for sample in samples)
    assert all("accepted substitute" in sample.explanation for sample in samples)


def test_evidence_manifest_preserves_the_boolean_units_and_selected_record_provenance():
    """The existing output-only manifest accepts actual concrete Field samples."""
    import json
    from ..features.space_field_visualization import build_field_layer_manifest

    field = _field([_record("table", _component(0, 0, 1, 1)["exterior"])])
    manifest = build_field_layer_manifest(layer_id="physical", channel="occupancy",
        samples=field.evaluate_many([(0, 0), (3, 3)], _query()))
    serialized = json.loads(json.dumps(manifest))
    assert [sample["value"] for sample in serialized["samples"]] == [True, False]
    assert serialized["samples"][1]["units"] == "boolean"
    assert serialized["samples"][0]["provenance"]["selected_records"][0]["id"] == "table"


@pytest.mark.parametrize("container", [{}, "", b"", 0])
def test_malformed_occupancy_container_cannot_establish_empty(container):
    """Falsey malformed input is not an explicitly empty record sequence."""
    with pytest.raises(TypeError, match="physical_occupancy"):
        _field(physical_occupancy=container)


def test_occupancy_accepts_empty_sequences_and_generic_record_iterables():
    """The container guard preserves both empty channels and lazy record input."""
    assert _field([]).evaluate((0, 0), _query()).value is False
    records = (_record("table", _component(0, 0, 1, 1)["exterior"]) for _ in range(1))
    assert _field(records).evaluate((0, 0), _query()).value is True
