"""Analytic request composition, immutable identity and public import compatibility."""

from dataclasses import FrozenInstanceError, replace
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon
import trimesh

from ..features import analysis_requests as requests
from ..features.analysis_requests import (
    AnalysisRequest, GeometryQuery, GridSampling, WORLD_XY_BASIS,
    execute_analysis_request, is_stale, query_capabilities, semantic_cache_key,
)
from ..features.field_core import Field, FieldStatus
from ..features.scene_contract import (
    NEUTRAL_SCENE_V2, AnalysisContext, AnalysisDomain, AnalysisPlane,
    MeshGeometry3D, NeutralSceneV2, SourceObject, UncertaintyRecord,
)


def _plane(**changes):
    """Return an independent canonical world-metre plane."""
    return AnalysisPlane(**{"name": "plan", "identity": "plane:plan", "origin": (0, 0, 0),
                            "basis": WORLD_XY_BASIS, **changes})


def _context():
    """Build a minimal factual context without historical fixture imports."""
    return AnalysisContext(
        contract_version=NEUTRAL_SCENE_V2, source_schema="IFC4", adapter_version="test/1",
        source_length_unit="m", analysis_length_unit="m", world_coordinate_system={"name": "world"},
        level_references=(), analysis_plane=_plane(), geometry_tolerance=0.001,
        topology_tolerance=0.001, walking_body_profiles=(), visual_height_bands=(),
        capability_flags={"has_3d_geometry": True}, input_mode="ifc",
    )


def _domain_mesh(origin, size, holes):
    """Triangulate the exact domain so holes reach the real projection/handoff."""
    x, y = origin
    polygon = Polygon(((x, y), (x + size, y), (x + size, y + size), (x, y + size)), holes)
    vertices, faces = [], []
    for triangle in constrained_delaunay_triangles(polygon).geoms:
        start = len(vertices)
        vertices.extend((px, py, 0.0) for px, py in list(triangle.exterior.coords)[:3])
        faces.append((start, start + 1, start + 2))
    return MeshGeometry3D(
        id="domain-mesh", vertices=vertices, triangle_indices=faces, normals=(),
        is_manifold=False, is_closed=False, units="m", source_representation_id=None,
        tessellation_settings={}, local_to_world_provenance={"world_transform_applied": True},
    )


def _object(identifier, bounds=(0, 0, 0, 1, 1, 3), *, role="furniture", **changes):
    """Return one real closed mass and its physical source record."""
    mesh = trimesh.creation.box(extents=tuple(bounds[i + 3] - bounds[i] for i in range(3)))
    mesh.apply_translation(tuple((bounds[i + 3] + bounds[i]) / 2 for i in range(3)))
    geometry = MeshGeometry3D(
        id=f"mesh:{identifier}", vertices=mesh.vertices.tolist(), triangle_indices=mesh.faces.tolist(),
        normals=(), is_manifold=True, is_closed=True, units="m", source_representation_id=None,
        tessellation_settings={}, local_to_world_provenance={"world_transform_applied": True},
    )
    source = SourceObject(**{"id": identifier, "source_id": f"ifc:{identifier}",
                             "source_role": role, "geometry_refs": (geometry.id,), **changes})
    return source, geometry


def _missing(identifier="missing"):
    """Keep a factual physical owner whose geometry is explicitly unavailable."""
    return SourceObject(id=identifier, source_role="plant", uncertainties=(UncertaintyRecord(
        code="missing_geometry", message="No mesh available", source_refs=(),
        operation="test", severity="warning"),)), None


def _scene(*objects, origin=(0, 0), size=4, holes=()):
    """Build an immutable exact domain and independently inventoried physical mass."""
    domain = AnalysisDomain(id="room", geometry_refs=("domain-mesh",), source_id=None,
                            selection_method="explicit_test_selection")
    return NeutralSceneV2(context=_context(), analysis_domain=domain,
                          source_objects=tuple(source for source, _ in objects),
                          geometries=(_domain_mesh(origin, size, holes),)
                          + tuple(mesh for _, mesh in objects if mesh is not None))


def _request(scene, **changes):
    """Select this scene's exact domain and a simple plane-local cell lattice."""
    return AnalysisRequest(**{"request_id": "test-run", "plane": scene.context.analysis_plane,
                              "domain": scene.analysis_domain,
                              "sampling": GridSampling((0, 0), 1, 4, 4), **changes})


def _binding(owner):
    """Declare one source-owned shared physical substitute binding."""
    return {"source_object_id": owner, "substitute_id": "proxy", "consumer": "physical_occupancy",
            "substitute_kind": "MassPatch", "analysis_role": "physical_occupancy_substitute",
            "representation_identifier": "GeneratedProxy",
            "provenance": {"representation_identifier": "GeneratedProxy"}}


def _proxy_scene(*, top=3):
    """Represent two missing originals with one qualified physical proxy."""
    owners = [(_missing(name)[0], None) for name in ("A", "B")]
    owners = [(replace(source, factual_properties={"OM_FunctionSubstitutes": [_binding(source.id)]}), mesh)
              for source, mesh in owners]
    proxy = _object("proxy", (1, 1, 0, 2, 2, top), role="analysis_substitute",
                    factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": ["A", "B"]}},
                    provenance={"representation_identifier": "GeneratedProxy"})
    return _scene(*owners, proxy)


@pytest.mark.parametrize("kind", ["whole_height_projection", "exact_world_xy_section", "finite_height_band"])
@pytest.mark.parametrize("case", ["excluded", "refused", "shared"])
def test_occupancy_constructs_only_selected_interior_geometry(monkeypatch, kind, case):
    """Prune excluded/raw owners and construct a shared accepted target exactly once."""
    from ..features import geometry_substitutes

    owners = [_object(name) for name in ("A", "B")]
    excluded = {"A", "B"} if case == "excluded" else set()
    if case != "excluded":
        owners = [(replace(source, factual_properties={"OM_FunctionSubstitutes": [
            {**_binding(source.id), **({"substitute_kind": "Body"} if case == "refused" else {})}]}), mesh)
            for source, mesh in owners]
    proxy = _object("proxy", (1, 1, 0, 2, 2, 3), role="analysis_substitute",
        factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": ["A", "B"]}},
        provenance={"representation_identifier": "GeneratedProxy"})
    scene = _scene(*owners, proxy)
    before = scene.to_dict()
    built = []
    original = geometry_substitutes.mass_patch_from_mesh

    def track(mesh):
        """Record request geometry construction, separately from resolver qualification."""
        built.append(mesh.id)
        return original(mesh)

    monkeypatch.setattr(geometry_substitutes, "mass_patch_from_mesh", track)
    request = _request(scene, geometry_query=GeometryQuery(
        kind, world_z_m=1.6 if kind == "exact_world_xy_section" else None,
        height_band=(1.0, 2.0) if kind == "finite_height_band" else None))
    records, unknown, audit = requests._occupancy(
        scene, request, excluded, Polygon(((0, 0), (4, 0), (4, 4), (0, 4))))
    assert built == (["mesh:proxy"] if case == "shared" else [])
    assert [record["id"] for record in records] == (["proxy"] if case == "shared" else [])
    assert unknown == (["A", "B"] if case == "refused" else [])
    assert [item["source_object_id"] for item in audit["physical_source_inventory"]] == ["A", "B"]
    assert {item["status"] for item in audit["physical_source_inventory"]} == {
        "scoped_out" if case == "excluded" else "unknown" if case == "refused" else "substitute"}
    assert scene.to_dict() == before


@pytest.mark.parametrize("mutation_reason", [
    ("missing_descriptor", "unknown_operation"),
    ("missing_consumer", "invalid_operation_consumer"),
    ("missing_upstream", "invalid_operation_input"),
    ("upstream_self_input", "invalid_operation_input"),
])
def test_malformed_registry_keeps_resolver_rejection_auditable(monkeypatch, mutation_reason):
    """Malformed operation metadata skips query construction but preserves resolver refusal evidence."""
    from ..features import analysis_substitute_discovery
    from ..features import geometry_substitutes

    mutation, expected_reason = mutation_reason
    registry = requests.load_substitute_registry()
    operations = registry["operations"]
    if mutation == "missing_descriptor":
        operations.pop("free_space")
    elif mutation == "missing_consumer":
        operations["free_space"].pop("consumer")
    elif mutation == "upstream_self_input":
        operations["physical_occupancy"]["input"] = "physical_occupancy"
    else:
        operations.pop("physical_occupancy")
    monkeypatch.setattr(requests, "load_substitute_registry", lambda: registry)
    monkeypatch.setattr(analysis_substitute_discovery, "load_substitute_registry", lambda: registry)

    built = []
    original = geometry_substitutes.mass_patch_from_mesh

    def track(mesh):
        """Record query geometry construction attempts for malformed registry paths."""
        built.append(mesh.id)
        return original(mesh)

    monkeypatch.setattr(geometry_substitutes, "mass_patch_from_mesh", track)
    scene = _scene(_object("chair"))
    records, unknown, audit = requests._occupancy(
        scene, _request(scene), set(), Polygon(((0, 0), (4, 0), (4, 4), (0, 4))))

    assert records == []
    assert unknown == ["chair"]
    assert built == []
    inventory = audit["physical_source_inventory"]
    assert inventory[0]["status"] == "unknown"
    assert inventory[0]["reason"] == expected_reason
    assert inventory[0]["resolution"]["rejection_diagnostics"] == [{"reason": expected_reason}]


@pytest.mark.parametrize("kind", ["whole_height_projection", "exact_world_xy_section"])
def test_request_metadata_matches_full_sample_freeze(kind):
    """Shared audit reuse preserves the ordinary fully validated sample result."""
    from ..features.field_core import FieldSample
    from ..features.space_field_visualization import build_field_layer_manifest

    scene = _proxy_scene()
    run = execute_analysis_request(scene, _request(scene, geometry_query=GeometryQuery(kind,
        world_z_m=1.6 if kind == "exact_world_xy_section" else None)))
    for target in ((1, 1), (3, 3), (-1, 0)):
        sample = run.field.evaluate(target, run.query)
        canonical = build_field_layer_manifest(layer_id="same", channel="physical_occupancy", samples=[sample])
        record = canonical["samples"][0]
        ordinary = FieldSample(sample.value, sample.status, sample.query, support=record["support"],
            source_ids=record["source_ids"], provenance=record["provenance"], explanation=sample.explanation)
        assert ordinary == sample
        assert sample.provenance["selected_records"] is run.field.provenance["selected_records"]


def test_projection_executes_real_field_and_keeps_scene_and_run_immutable():
    """Known mass/free cells use exact Field semantics without mutating source facts."""
    scene = _scene(_object("chair"))
    before = scene.to_dict()
    request = _request(scene)
    run = execute_analysis_request(scene, request)
    assert isinstance(run.field, Field) and run.support_status is FieldStatus.ESTABLISHED
    occupied, empty = run.field.evaluate_many(((0, 0), (2, 2)), run.query)
    assert occupied.value is True and occupied.status is FieldStatus.ESTABLISHED
    assert empty.value is False and empty.status is FieldStatus.ESTABLISHED
    assert occupied.source_ids == ("chair",)
    assert occupied.query is run.query and occupied.support["plane"] == run.query.plane
    assert run.snapshot.provenance["domain_handoff"]["attempt"]["status"] == "accepted"
    assert scene.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        request.request_id = "changed"
    with pytest.raises(AttributeError):
        run.field._request = replace(request, plane=_plane(origin=(9, 9, 0)))
    with pytest.raises(TypeError):
        run.snapshot.provenance["geometry_query"]["kind"] = "changed"
    detached = run.snapshot.to_dict()
    detached["provenance"]["geometry_query"]["kind"] = "changed"
    assert run.snapshot.provenance["geometry_query"]["kind"] == "whole_height_projection"
    json.dumps(run.snapshot.to_dict(), allow_nan=False)


def test_independent_translated_rotated_planes_and_domains():
    """Multiple requests share facts while each exact grid uses its own coordinates."""
    scene = _scene(_object("chair"))
    before = scene.to_dict()
    original = execute_analysis_request(scene, _request(scene))
    translated = execute_analysis_request(scene, _request(scene,
        plane=_plane(origin=(1, 0, 7)), sampling=GridSampling((-1, 0), 1, 4, 4)))
    rotated = execute_analysis_request(scene, _request(scene,
        plane=_plane(basis=((0, 1, 0), (-1, 0, 0), (0, 0, 1))),
        sampling=GridSampling((0, -4), 1, 4, 4)))
    smaller = replace(scene.analysis_domain, id="small", geometry_refs=("mesh:chair",))
    small = execute_analysis_request(scene, _request(scene, domain=smaller))
    assert original.field.evaluate((0, 0), original.query).value is True
    assert translated.field.evaluate((0, 0), translated.query).value is True
    assert rotated.field.evaluate((3, 0), rotated.query).value is True
    assert small.field.evaluate((2, 2), small.query).status is FieldStatus.OUTSIDE
    assert scene.to_dict() == before
    assert len({run.snapshot.semantic_key for run in (original, translated, rotated, small)}) == 4


def test_exact_domain_hole_is_outside_and_missing_domain_is_unavailable():
    """Exact mesh holes survive the existing domain handoff without rectangle fallback."""
    scene = _scene(holes=(((1, 1), (2, 1), (2, 2), (1, 2)),))
    run = execute_analysis_request(scene, _request(scene))
    assert run.field.evaluate((1, 1), run.query).status is FieldStatus.OUTSIDE
    assert run.field.evaluate((0, 0), run.query).value is False
    for domain in (None, replace(scene.analysis_domain, geometry_refs=("missing",))):
        unavailable = execute_analysis_request(scene, _request(scene, domain=domain))
        assert unavailable.support_status is FieldStatus.NOT_AVAILABLE
        assert unavailable.field.evaluate((0, 0), unavailable.query).value is None


@pytest.mark.parametrize("role", ["furniture", "plant", "counter", "unknown"])
def test_furniture_exclusion_does_not_erase_physical_mass(role):
    """Furniture inference eligibility never removes a factual physical obstacle."""
    scene = _scene(_object("mass", role=role, factual_properties={"furniture_analysis": "excluded"}))
    run = execute_analysis_request(scene, _request(scene))
    assert run.field.evaluate((0, 0), run.query).value is True


@pytest.mark.parametrize("tokens,excluded", [([], False), (["door"], True), (["ifc:door"], True),
    (["door", "door"], False), (["unmatched"], False), ([1], False)])
def test_only_exact_confirmed_boundary_membership_excludes_doors(tokens, excluded):
    """Infill class and host-like metadata cannot establish domain membership."""
    scene = _scene(_object("door", role="door", source_class="IfcDoor",
                          factual_properties={"host_refs": ["room"]}))
    domain = replace(scene.analysis_domain, provenance={"boundary_member_source_ids": tokens})
    run = execute_analysis_request(scene, _request(scene, domain=domain))
    assert run.field.evaluate((0, 0), run.query).value is (not excluded)
    assert ("door" in run.snapshot.provenance["boundary_member_ids"]) is excluded


def test_ambiguous_boundary_token_and_furniture_domain_link_exclude_nothing():
    """An identity shared by two sources and an arbitrary domain link erase no mass."""
    scene = _scene(_object("door", source_id="same"), _object("other", source_id="same"))
    domain = replace(scene.analysis_domain, source_id="same",
                     provenance={"boundary_member_source_ids": ["same"]})
    run = execute_analysis_request(scene, _request(scene, domain=domain))
    assert run.field.evaluate((0, 0), run.query).value is True
    assert run.snapshot.provenance["boundary_member_ids"] == ()


@pytest.mark.parametrize("kind", ["whole_height_projection", "exact_world_xy_section"])
def test_proxy_covers_two_missing_owners_once(kind):
    """The shared resolver supplies one proxy and retains both represented owners."""
    scene = _proxy_scene()
    query = GeometryQuery(kind, world_z_m=1.6) if kind == "exact_world_xy_section" else GeometryQuery(kind)
    run = execute_analysis_request(scene, _request(scene, geometry_query=query))
    selected = run.snapshot.provenance["selected_records"]
    assert len(selected) == 1 and selected[0]["id"] == "proxy"
    assert selected[0]["represented_source_ids"] == ("A", "B")
    sample = run.field.evaluate((1, 1), run.query)
    assert sample.value is True and sample.status is FieldStatus.CONDITIONAL
    assert sample.source_ids == ("A", "B")
    assert run.support_status is FieldStatus.CONDITIONAL
    participation = run.snapshot.provenance["projected_domain_participation"]
    assert len(participation) == 1
    assert participation[0]["selected_source_id"] == "proxy"
    assert participation[0]["selected_geometry_refs"] == ("mesh:proxy",)
    assert participation[0]["represented_source_ids"] == ("A", "B")
    assert tuple(item["source_object_id"] for item in participation[0]["original_sources"]) == ("A", "B")
    assert all(item["geometry_refs"] == () for item in participation[0]["original_sources"])
    assert participation[0]["relation"] == "inside"
    assert participation[0]["intersection_area_m2"] == 1.0


def test_missing_source_is_unknown_while_known_positive_survives():
    """Missing support prevents free-space certification without erasing known mass."""
    scene = _scene(_object("known"), _missing())
    run = execute_analysis_request(scene, _request(scene))
    assert run.support_status is FieldStatus.UNKNOWN
    assert run.field.evaluate((0, 0), run.query).value is True
    empty = run.field.evaluate((2, 2), run.query)
    assert empty.status is FieldStatus.UNKNOWN and empty.value is None
    assert run.snapshot.provenance["unknown_source_ids"] == ("missing",)
    audit = next(item for item in run.snapshot.provenance["projected_domain_participation"]
                 if item.get("source_object_id") == "missing")
    assert audit["relation"] == "unevaluated" and audit["intersection_area_m2"] is None
    assert audit["participates"] is None and audit["reason"] == "unresolved_query_geometry"


def test_failed_projection_is_unknown_while_known_positive_survives(monkeypatch):
    """A failed mass projection keeps its factual owner unknown without aborting the run."""
    from shapely.errors import GEOSException
    from ..features import analysis_substitute_discovery, geometry_views

    scene = _scene(_object("known"), _object("broken", (1, 1, 0, 2, 2, 3)))
    before = scene.to_dict()
    original_projection = geometry_views.plan_projection

    def failing_projection(patch, plane):
        """Simulate a geometry backend failure for one mass, leaving other facts usable."""
        if patch.source_geometry_id == "mesh:broken":
            raise GEOSException("broken mass projection")
        return original_projection(patch, plane)

    monkeypatch.setattr(geometry_views, "plan_projection", failing_projection)
    monkeypatch.setattr(analysis_substitute_discovery, "plan_projection", failing_projection)
    run = execute_analysis_request(scene, _request(scene))
    assert run.support_status is FieldStatus.UNKNOWN
    assert run.field.evaluate((0, 0), run.query).value is True
    empty = run.field.evaluate((2, 2), run.query)
    assert empty.status is FieldStatus.UNKNOWN and empty.value is None
    assert run.snapshot.provenance["unknown_source_ids"] == ("broken",)
    assert run.snapshot.provenance["geometry_failures"][0]["reason"] == "broken mass projection"
    audit = next(item for item in run.snapshot.provenance["projected_domain_participation"]
                 if item.get("source_object_id") == "broken")
    assert audit["relation"] == "unevaluated" and audit["intersection_area_m2"] is None
    assert audit["participates"] is None and audit["reason"] == "unresolved_query_geometry"
    assert audit["geometry_failure_reason"] == "broken mass projection"
    assert scene.to_dict() == before


def test_failed_required_proxy_never_falls_back_to_original_mass():
    """A required target failure leaves all declared owners unresolved."""
    scene = _proxy_scene()
    scene = replace(scene, geometries=tuple(replace(mesh, is_closed=False, is_manifold=False)
                    if mesh.id == "mesh:proxy" else mesh for mesh in scene.geometries))
    run = execute_analysis_request(scene, _request(scene,
        geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1.6)))
    assert run.snapshot.provenance["selected_records"] == ()
    assert run.snapshot.provenance["unknown_source_ids"] == ("A", "B")
    assert run.field.evaluate((1, 1), run.query).status is FieldStatus.UNKNOWN


def test_failed_single_owner_required_proxy_keeps_global_unknown() -> None:
    """A failed required substitute cannot certify distant empty cells from its hull."""
    owner = replace(_missing("A")[0], factual_properties={"OM_FunctionSubstitutes": [_binding("A")]})
    proxy, mesh = _object("proxy", (1, 1, 0, 2, 2, 3), role="analysis_substitute",
                          factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": ["A"]}},
                          provenance={"representation_identifier": "GeneratedProxy"})
    scene = _scene((owner, None), (proxy, replace(mesh, is_closed=False, is_manifold=False)))
    run = execute_analysis_request(scene, _request(scene,
        geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1.6)))
    assert run.snapshot.provenance["unknown_source_ids"] == ("A",)
    assert run.snapshot.provenance["trusted_unknown_supports"] == {}
    sample = run.field.evaluate((3, 3), run.query)
    assert sample.status is FieldStatus.UNKNOWN and sample.value is None


def test_unknown_support_requires_exact_selected_owner_query_and_complete_coverage(monkeypatch):
    """Only the unresolved owner's exact selected section can narrow uncertainty."""
    from ..features import neutral_scene_views

    source, mesh = _object("A", (1, 1, 0, 2, 2, 3))
    scene = _scene((source, replace(mesh, is_closed=False, is_manifold=False)))
    request = _request(scene, geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1.6))
    run = execute_analysis_request(scene, request)
    assert run.support_status is FieldStatus.UNKNOWN
    assert run.field.evaluate((1, 1), run.query).status is FieldStatus.UNKNOWN
    assert run.field.evaluate((3, 3), run.query).value is False
    assert run.snapshot.provenance["trusted_unknown_supports"]["A"]["selected_owner_ids"] == ("A",)

    original = neutral_scene_views._resolved_physical_occupancy
    for change in ({"selected_source": "other"}, {"selected_geometry": ("other-mesh",)},
                   {"coverage": ("A", "B")}, {"query": {"frame": "world_xy", "units": "m", "world_z_m": 2.0}}):
        def altered(scene_arg, records, excluded, **kwargs):
            """Tamper one resolver fact after genuine source accounting."""
            selected, unresolved, inventory = original(scene_arg, records, excluded, **kwargs)
            if inventory and inventory[0]["source_object_id"] == "A" and "resolution" in inventory[0]:
                inventory[0]["resolution"].update(change)
            return selected, unresolved, inventory

        monkeypatch.setattr(neutral_scene_views, "_resolved_physical_occupancy", altered)
        rejected = execute_analysis_request(scene, request)
        assert rejected.field.evaluate((3, 3), rejected.query).status is FieldStatus.UNKNOWN
        assert rejected.snapshot.provenance["trusted_unknown_supports"] == {}
    monkeypatch.undo()

    proxy = _proxy_scene()
    proxy = replace(proxy, geometries=tuple(replace(item, is_closed=False, is_manifold=False)
                    if item.id == "mesh:proxy" else item for item in proxy.geometries))
    refused = execute_analysis_request(proxy, _request(proxy,
        geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1.6)))
    assert refused.snapshot.provenance["trusted_unknown_supports"] == {}
    assert refused.field.evaluate((3, 3), refused.query).status is FieldStatus.UNKNOWN


def test_translated_unknown_line_and_point_touch_preserves_dimension(monkeypatch):
    """World-XY support moves once into a nonzero-origin plane-local grid."""
    from ..features import section_views

    source, mesh = _object("A", (101, 201, 0, 102, 202, 3))
    scene = _scene((source, replace(mesh, is_closed=False, is_manifold=False)),
                   origin=(100, 200))
    request = _request(scene, plane=_plane(origin=(100, 200, 99)),
                       sampling=GridSampling((0.25, 0.25), 1, 4, 4),
                       geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1.6))
    original = section_views.exact_plane_section
    for support in ({"type": "LineString", "coordinates": [(101.25, 200.5), (101.25, 201.25)]},
                    {"type": "Point", "coordinates": (101.25, 201.25)},
                    {"type": "Point", "coordinates": (108, 208)}):
        def injected(patch, *, world_z_m):
            """Replace only the helper's uncertainty geometry for coordinate coverage."""
            result = original(patch, world_z_m=world_z_m)
            result["unknown_support_geometry"] = support
            return result

        monkeypatch.setattr(section_views, "exact_plane_section", injected)
        run = execute_analysis_request(scene, request)
        touched = run.field.evaluate((0, 0), run.query)
        assert touched.status is (FieldStatus.ESTABLISHED if support["coordinates"] == (108, 208)
                                  else FieldStatus.UNKNOWN)
        assert run.field.evaluate((3, 3), run.query).value is False
        assert run.snapshot.provenance["trusted_unknown_supports"]["A"]["geometry"]["type"] == support["type"]
        assert run.snapshot.provenance["geometry_query"]["world_z_m"] == 1.6


@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("kind", ["exact_world_xy_section", "finite_height_band"])
def test_qualified_empty_query_proves_empty_and_preserves_acceptance(proxy, kind):
    """Legal empty originals are established; accepted proxy empties remain conditional."""
    scene = _proxy_scene(top=1) if proxy else _scene(_object("low", (0, 0, 0, 1, 1, 1)))
    run = execute_analysis_request(scene, _request(scene, geometry_query=GeometryQuery(kind,
        world_z_m=1.6 if kind == "exact_world_xy_section" else None,
        height_band=(1, 2) if kind == "finite_height_band" else None)))
    sample = run.field.evaluate((1, 1), run.query)
    assert sample.value is False
    assert sample.status is (FieldStatus.CONDITIONAL if proxy else FieldStatus.ESTABLISHED)
    assert sample.source_ids == (("A", "B") if proxy else ("low",))
    assert len(run.snapshot.provenance["legal_empty_sections"]) == 1
    assert run.snapshot.provenance["unknown_source_ids"] == ()
    audit = run.snapshot.provenance["projected_domain_participation"][0]
    assert audit["relation"] == "unevaluated" and audit["intersection_area_m2"] is None
    assert audit["reason"] == ("qualified_empty_section" if kind == "exact_world_xy_section" else
                               "no_positive_vertical_overlap_with_height_band")
    assert audit["participates"] is False


def test_exact_section_uses_absolute_world_z_with_translated_xy_and_origin_z():
    """A plane origin Z of 99 never changes an explicit absolute world-Z cut at 1.6."""
    scene = _scene(_object("tall", (10, 20, 0, 11, 21, 3)), origin=(10, 20))
    request = _request(scene, plane=_plane(origin=(10, 20, 99)),
                       geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1.6))
    run = execute_analysis_request(scene, request)
    assert run.field.evaluate((0, 0), run.query).value is True
    assert run.field.evaluate((2, 2), run.query).value is False
    assert run.snapshot.provenance["section_thickness_m"] == 0
    evidence = run.snapshot.provenance["selected_records"][0]["section_evidence"]
    assert evidence["query"]["world_z_m"] == 1.6
    above = execute_analysis_request(scene, replace(request,
        geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=3.1), geometry_tolerance=0.5))
    assert above.field.evaluate((0, 0), above.query).value is False


def test_finite_height_band_uses_analysis_plane_local_z_for_occupancy():
    """Only a mass intersecting the local band contributes to the field."""
    low = _object("low", (0, 0, 0, 1, 1, 0.5))
    band = _object("band", (1, 0, 1.5, 2, 1, 2.5))
    scene = _scene(low, band)
    run = execute_analysis_request(scene, _request(scene,
        geometry_query=GeometryQuery("finite_height_band", height_band=(1.0, 2.0))))
    assert run.support_status is FieldStatus.ESTABLISHED
    assert run.field.evaluate((0, 0), run.query).value is False
    assert run.field.evaluate((0, 1), run.query).value is True
    audit = {item["selected_source_id"]: item
             for item in run.snapshot.provenance["projected_domain_participation"]}
    assert audit["low"]["relation"] == "unevaluated"
    assert audit["low"]["intersection_area_m2"] is None
    assert audit["low"]["reason"] == "no_positive_vertical_overlap_with_height_band"
    assert audit["low"]["participates"] is False
    assert run.snapshot.provenance["unknown_source_ids"] == ()


@pytest.mark.parametrize("kind", ["whole_height_projection", "finite_height_band", "exact_world_xy_section"])
@pytest.mark.parametrize("origin", [(0, 0), (100, 200)])
@pytest.mark.parametrize("bounds,relation,area,target,occupied", [
    ((.25, .25, .75, .75), "inside", .25, (0, 0), True),
    ((0, 2, 1, 3), "inside", 1.0, (2, 0), True),
    ((3.5, 2.5, 4.5, 3.5), "crossing", .5, (2, 3), True),
    ((4, 2, 5, 3), "boundary_contact", 0.0, (2, 3), False),
    ((4, 4, 5, 5), "boundary_contact", 0.0, (3, 3), False),
    ((5, 2, 6, 3), "disjoint", 0.0, (2, 3), False),
    ((1.25, 1.25, 1.75, 1.75), "disjoint", 0.0, (1, 0), False),
    ((1, 1.25, 1.5, 1.75), "boundary_contact", 0.0, (1, 0), False),
    ((.75, 1.25, 1.25, 1.75), "crossing", .125, (1, 0), True),
    ((.5, .5, 2.5, 2.5), "crossing", 3.0, (0, 0), True),
    ((4.000001, 2, 5, 3), "disjoint", 0.0, (2, 3), False),
    ((3.999999, 2, 5, 3), "crossing", .000001, (2, 3), True),
])
def test_exact_projected_domain_participation_preserves_holes_and_contacts(
        kind, origin, bounds, relation, area, target, occupied):
    """Rectangle areas against a four-metre square and one-metre hole are analytic."""
    x, y = origin
    xmin, ymin, xmax, ymax = bounds
    scene = _scene(_object("mass", (x + xmin, y + ymin, 0, x + xmax, y + ymax, 3)),
                   origin=origin, holes=[[(x + 1, y + 1), (x + 2, y + 1),
                                          (x + 2, y + 2), (x + 1, y + 2)]])
    query = GeometryQuery(kind, world_z_m=1.6 if kind == "exact_world_xy_section" else None,
                          height_band=(1, 2) if kind == "finite_height_band" else None)
    # A deliberately large length tolerance must neither bridge the gap nor
    # discard the narrow positive-area strip at the outer boundary.
    request = _request(scene, plane=_plane(origin=(x, y, 0)), geometry_query=query,
                       geometry_tolerance=.1, topology_tolerance=.1)
    run = execute_analysis_request(scene, request)
    audit = run.snapshot.provenance["projected_domain_participation"]
    assert len(audit) == 1
    item = audit[0]
    assert item["relation"] == relation
    assert item["intersection_area_m2"] == pytest.approx(area, abs=1e-12)
    assert item["participates"] is (relation != "disjoint")
    assert item["field_input"] is (area > 0)
    assert item["selected_source_id"] == "mass"
    assert item["selected_geometry_refs"] == ("mesh:mass",)
    assert item["represented_source_ids"] == ("mass",)
    assert item["original_sources"] == ({"source_object_id": "mass", "source_id": "ifc:mass",
                                          "geometry_refs": ("mesh:mass",)},)
    expected_reason = ("disjoint_from_qualified_domain" if relation == "disjoint" else
                       "boundary_only_domain_contact" if relation == "boundary_contact" else
                       "positive_area_domain_intersection")
    assert item["reason"] == expected_reason
    assert run.snapshot.provenance["physical_source_inventory"][0]["status"] == "original"
    assert len(run.snapshot.provenance["selected_records"]) == 1
    assert len(run.field._delegate.physical_occupancy) == int(area > 0)
    assert run.field.evaluate(target, run.query).value is occupied
    assert run.field.evaluate((1, 1), run.query).status is FieldStatus.OUTSIDE


@pytest.mark.parametrize("bounds,relation", [((4, 1, 0, 5, 2, 3), "boundary_contact"),
                                           ((5, 1, 0, 6, 2, 3), "disjoint")])
def test_omitted_proxy_retains_exact_once_owner_audit_and_conditional_evidence(bounds, relation):
    """A shared substitute outside occupied area remains one traceable bounded result."""
    scene = _proxy_scene()
    _, proxy_mesh = _object("proxy", bounds)
    scene = replace(scene, geometries=tuple(proxy_mesh if mesh.id == "mesh:proxy" else mesh
                                           for mesh in scene.geometries))
    run = execute_analysis_request(scene, _request(scene))
    audit = run.snapshot.provenance["projected_domain_participation"]
    assert len(audit) == 1
    assert audit[0]["selected_source_id"] == "proxy"
    assert audit[0]["represented_source_ids"] == ("A", "B")
    assert audit[0]["relation"] == relation and audit[0]["intersection_area_m2"] == 0.0
    assert audit[0]["participates"] is (relation == "boundary_contact")
    assert audit[0]["field_input"] is False
    assert run.field._delegate.physical_occupancy == ()
    sample = run.field.evaluate((1, 3), run.query)
    assert sample.value is False and sample.status is FieldStatus.CONDITIONAL
    assert sample.source_ids == ("A", "B")
    assert run.support_status is FieldStatus.CONDITIONAL


@pytest.mark.parametrize("role", ["drawing_camera", "opening", "analysis_substitute"])
def test_nonphysical_sources_are_explicitly_audited_without_domain_claims(role):
    """Excluded reference geometry remains factual and does not become occupied mass."""
    scene = _scene(_object("reference", role=role))
    run = execute_analysis_request(scene, _request(scene))
    audit = run.snapshot.provenance["projected_domain_participation"]
    assert len(audit) == 1 and audit[0]["source_object_id"] == "reference"
    assert audit[0]["source_role"] == role
    assert audit[0]["original_geometry_refs"] == ("mesh:reference",)
    assert audit[0]["reason"] == "nonphysical_source"
    assert audit[0]["relation"] == "unevaluated" and audit[0]["intersection_area_m2"] is None
    assert audit[0]["participates"] is False
    assert run.snapshot.provenance["physical_source_inventory"] == ()
    assert run.field.evaluate((0, 0), run.query).value is False


@pytest.mark.parametrize("reason", ["selected_analysis_domain_member", "verified_support_binding"])
def test_exact_source_exclusions_remain_audited_before_domain_intersection(reason):
    """Exact boundary or support exclusion explains missing geometry without guessing location."""
    source = _missing("excluded")[0]
    if reason == "verified_support_binding":
        source = replace(source, factual_properties={"analysis_scope_exclusion": {"reason": reason}})
    scene = _scene((source, None))
    domain = (replace(scene.analysis_domain, provenance={"boundary_member_source_ids": ["excluded"]})
              if reason == "selected_analysis_domain_member" else scene.analysis_domain)
    run = execute_analysis_request(scene, _request(scene, domain=domain))
    audit = run.snapshot.provenance["projected_domain_participation"][0]
    assert audit["source_object_id"] == "excluded" and audit["reason"] == reason
    assert audit["status"] == "scoped_out"
    assert audit["relation"] == "unevaluated" and audit["intersection_area_m2"] is None
    assert audit["participates"] is False
    assert run.snapshot.provenance["unknown_source_ids"] == ()
    assert run.field.evaluate((0, 0), run.query).value is False


@pytest.mark.parametrize("empty_projection", [False, True])
def test_failed_outside_projection_cannot_invent_disjoint_domain_relation(monkeypatch, empty_projection):
    """A failure at an apparently distant mass leaves unsupported free cells unknown."""
    from shapely.errors import GEOSException
    from ..features import geometry_views
    scene = _scene(_object("distant", (50, 50, 0, 51, 51, 3)))

    def fail(patch, plane):
        """Refuse the query footprint before an exact intersection can establish scope."""
        if empty_projection:
            return geometry_views.PlanProjection("query-projection", (), uncertainty="projection unavailable")
        raise GEOSException("query projection unavailable")

    monkeypatch.setattr(geometry_views, "plan_projection", fail)
    run = execute_analysis_request(scene, _request(scene))
    audit = run.snapshot.provenance["projected_domain_participation"][0]
    assert audit["relation"] == "unevaluated" and audit["intersection_area_m2"] is None
    if empty_projection:
        assert audit["reason"] == "no_qualified_query_footprint"
        assert audit["selected_source_id"] == "distant"
    else:
        assert audit["geometry_failure_reason"] == "query projection unavailable"
    assert audit["participates"] is None and audit["field_input"] is False
    assert run.snapshot.provenance["unknown_source_ids"] == ("distant",)
    assert run.field.evaluate((0, 0), run.query).status is FieldStatus.UNKNOWN


def test_projected_domain_audit_survives_complete_serializer_and_nested_freeze():
    """The existing wire carries source scope verbatim without mutable authority."""
    from ..adapters import blender_analysis_session as service, blender_analysis_result_wire as wire
    scene = _scene(_object("inside"), _object("outside", (5, 1, 0, 6, 2, 3)),
                   _object("contact", (4, 2, 0, 5, 3, 3)), _missing(),
                   _object("camera", role="drawing_camera"))
    run = execute_analysis_request(scene, _request(scene))
    audit = run.snapshot.provenance["projected_domain_participation"]
    with pytest.raises(TypeError):
        audit[0]["reason"] = "changed"
    with pytest.raises(TypeError):
        audit[0]["original_sources"][0]["geometry_refs"][0] = "changed"
    document = service.serialize_analysis_result(run, job_id="scope-roundtrip", plane_uuid="plane:plan",
        plane_revision=1, domain_request_id="confirmed-room", domain_session_revision=1)
    restored = wire.load_json(wire.canonical_json(document))
    wire.validate_document(restored)
    assert restored["tables"]["snapshot"]["provenance"]["projected_domain_participation"] == wire.plain(audit)
    for row in range(4):
        for column in range(4):
            sample = service.reconstruct_field_sample(restored, row=row, column=column)
            assert sample == run.field.evaluate((row, column), run.query)
            assert sample.provenance["projected_domain_participation"] == audit


def test_slab_datum_is_immutable_and_changes_request_identity():
    """Full native receipt bytes participate in identity and remain detached from caller edits."""
    from ..adapters.blender_analysis_capture import digest
    from .test_bonsai_space_authoring import captured_slab_scene
    scene, datum = captured_slab_scene()
    datum["audit"] = {"note": "楼板", "observations": ["native"]}
    datum["observation_digest"] = digest({key: value for key, value in datum.items() if key != "observation_digest"})
    request = _request(scene, plane=_plane(origin=(4, 6, 2)), height_band_datum=datum,
                       geometry_query=GeometryQuery("finite_height_band", height_band=(-1.8, 0)))
    original = request.to_dict()["height_band_datum"]
    datum["audit"]["observations"].append("changed")
    assert request.to_dict()["height_band_datum"] == original
    with pytest.raises(TypeError):
        request.height_band_datum["audit"]["note"] = "changed"
    changed = replace(request, height_band_datum=datum)
    assert semantic_cache_key(scene, changed) != semantic_cache_key(scene, request)
    # Moving the slab top and matching the local band must also change semantic identity.
    raised = replace(request, height_band_datum={**original, "datum_z_m": .4},
                     geometry_query=GeometryQuery("finite_height_band", height_band=(-1.6, 0)))
    assert semantic_cache_key(scene, raised) != semantic_cache_key(scene, request)


@pytest.mark.parametrize("degrees", [10, 43])
@pytest.mark.parametrize("top,plane_z", [(.2, 2.0), (-3.0, -1.2)])
def test_native_noncardinal_rotation_accepts_slab_band(monkeypatch, degrees, top, plane_z):
    """Native XY camera rotations retain their validated floating frame and translated SI band."""
    import math
    from ..adapters.bonsai_analysis_plane import read_camera_binding, plane_from_camera
    from .test_bonsai_analysis_plane import _camera, _runtime
    from .test_bonsai_space_authoring import captured_slab_scene
    cosine, sine = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    matrix = [[cosine, -sine, 0, 4], [sine, cosine, 0, 6],
              [0, 0, 1, plane_z], [0, 0, 0, 1]]
    _runtime(monkeypatch, resolved=matrix)
    binding = read_camera_binding(_camera(matrix), role="geometry_author")
    plane = plane_from_camera(binding, name="rotated native plane",
                              query_kind="ground_to_analysis_plane_band")
    scene, datum = captured_slab_scene(top=top)
    request = _request(scene, plane=plane, height_band_datum=datum,
        geometry_query=GeometryQuery("finite_height_band", height_band=(top - plane_z, 0)))
    assert request.plane.origin == (4, 6, plane_z)
    assert request.plane.basis == binding.basis
    assert request.geometry_query.height_band == (top - plane_z, 0)


@pytest.mark.parametrize("failure", ["whole", "section", "tilt", "downward", "bounds", "nonfinite"])
def test_native_slab_band_rejects_contradictory_request(failure):
    """Native datum metadata is valid only for its matching horizontal upward slab-to-plane band."""
    from .test_bonsai_space_authoring import captured_slab_scene
    scene, datum = captured_slab_scene()
    changes = {"height_band_datum": datum, "plane": _plane(origin=(0, 0, 2)),
               "geometry_query": GeometryQuery("finite_height_band", height_band=(-1.8, 0))}
    if failure == "whole":
        changes["geometry_query"] = GeometryQuery()
    elif failure == "section":
        changes["geometry_query"] = GeometryQuery("exact_world_xy_section", world_z_m=1)
    elif failure == "tilt":
        changes["plane"] = _plane(basis=((1, 0, 0), (0, 0, 1), (0, -1, 0)))
    elif failure == "downward":
        changes["plane"] = _plane(basis=((1, 0, 0), (0, -1, 0), (0, 0, -1)))
    elif failure == "bounds":
        changes["geometry_query"] = GeometryQuery("finite_height_band", height_band=(-2, 0))
    else:
        changes["height_band_datum"] = {**datum, "datum_z_m": float("inf")}
    with pytest.raises(ValueError):
        _request(scene, **changes)


@pytest.mark.parametrize("changes", [
    {"geometry_query": GeometryQuery("tilted_section", world_z_m=1)},
    {"geometry_query": GeometryQuery("volume_3d")}, {"operation": "future_operation"},
    {"demand": {"body_radius_m": 0.3}}, {"source_rules": {"registry": "custom"}},
    {"plane": _plane(basis=((0, 1, 0), (-1, 0, 0), (0, 0, 1))),
     "geometry_query": GeometryQuery("exact_world_xy_section", world_z_m=1)},
])
def test_unsupported_semantics_return_not_available_field(changes):
    """Unsupported execution is explicit and carries no approximation or conditional value."""
    scene = _scene()
    run = execute_analysis_request(scene, _request(scene, **changes))
    assert run.support_status is FieldStatus.NOT_AVAILABLE
    sample = run.field.evaluate((0, 0), run.query)
    assert sample.status is FieldStatus.NOT_AVAILABLE and sample.value is None


def test_capabilities_and_query_binding_are_profile_specific():
    """Capabilities stay immutable and a run refuses mismatched queries or grid targets."""
    assert dict(query_capabilities()) == {"whole_height_projection": True, "exact_world_xy_section": True,
        "finite_height_band": True, "tilted_section": False, "volume_3d": False}
    with pytest.raises(TypeError):
        query_capabilities()["volume_3d"] = True
    scene = _scene()
    run = execute_analysis_request(scene, _request(scene))
    for target in ((True, 0), (4, 0), (0,), [0, 0]):
        assert run.field.evaluate(target, run.query).status is FieldStatus.INVALID
    assert run.field.evaluate((0, 0), replace(run.query, revision="other")).status is FieldStatus.INVALID


@pytest.mark.parametrize("changes", [{"spacing": 0}, {"spacing": float("nan")}, {"n_rows": True},
    {"n_cols": 1.5}, {"origin": (0,)}, {"origin": (float("inf"), 0)},
    {"spacing": 1e308, "n_cols": 10}])
def test_grid_validation_rejects_malformed_or_unbounded_lattices(changes):
    """Reject invalid lattice dimensions and finite values whose final bounds overflow."""
    with pytest.raises(ValueError):
        GridSampling(**{"origin": (0, 0), "spacing": 1, "n_rows": 4, "n_cols": 4, **changes})


@pytest.mark.parametrize("changes", [{"kind": "unknown"}, {"world_z_m": 1},
    {"kind": "exact_world_xy_section"}, {"kind": "exact_world_xy_section", "world_z_m": True},
    {"kind": "finite_height_band", "height_band": (1, 1)}, {"height_band": (0, 1)}])
def test_geometry_query_rejects_contradictory_or_nonfinite_parameters(changes):
    """A recognized unsupported request is retained only when its parameters are valid."""
    with pytest.raises(ValueError):
        GeometryQuery(**changes)


def test_request_deep_freezes_nested_parameters():
    """Caller-owned demand/rules cannot change the retained immutable request."""
    scene = _scene()
    rules, demand = {"custom": {"owners": ["A"]}}, {"profile": {"radius": [0.3]}}
    request = _request(scene, source_rules=rules, demand=demand)
    rules["custom"]["owners"].append("B")
    demand["profile"]["radius"][0] = 9
    assert request.source_rules["custom"]["owners"] == ("A",)
    assert request.demand["profile"]["radius"] == (0.3,)


def test_key_excludes_request_ids_and_display_but_tracks_semantics(monkeypatch):
    """Facts, membership, grid, rules and backend changes invalidate reuse; labels do not."""
    scene = _scene(_object("chair"))
    request = _request(scene)
    key = semantic_cache_key(scene, request)
    run = execute_analysis_request(scene, request)
    display = replace(scene, source_objects=(replace(scene.source_objects[0],
        factual_properties={"display_name": "pretty", "color": "red"},
        provenance={"display_name": "pretty", "camera_scale": 99}),))
    renamed = replace(request, request_id="random-other-id", plane=replace(request.plane, name="pretty"))
    assert semantic_cache_key(display, renamed) == key and not is_stale(run.snapshot, display, renamed)
    for changed in (replace(request, plane=replace(request.plane, revision=2)),
                    replace(request, plane=replace(request.plane, origin=(1, 0, 0))),
                    replace(request, sampling=replace(request.sampling, spacing=0.5)),
                    replace(request, domain=replace(request.domain, provenance={"boundary_member_source_ids": ["chair"]})),
                    replace(request, geometry_tolerance=0.002), replace(request, topology_tolerance=0.002),
                    replace(request, source_rules={"custom": True}),
                    replace(request, geometry_query=GeometryQuery("exact_world_xy_section", world_z_m=1))):
        assert semantic_cache_key(scene, changed) != key and is_stale(run.snapshot, scene, changed)
    moved = replace(scene, geometries=tuple(replace(mesh, vertices=tuple((x + 0.1, y, z)
        for x, y, z in mesh.vertices)) if mesh.id == "mesh:chair" else mesh for mesh in scene.geometries))
    assert is_stale(run.snapshot, moved, request)
    registry = requests.load_substitute_registry()
    monkeypatch.setattr(requests, "load_substitute_registry", lambda: registry)
    registry["operations"]["physical_occupancy"]["display"] = {"color": "new"}
    assert semantic_cache_key(scene, request) == key
    registry["operations"]["physical_occupancy"]["fallback"] = "unresolved"
    assert semantic_cache_key(scene, request) != key
    monkeypatch.undo()
    monkeypatch.setattr(requests, "_backend_versions", lambda: {"executor": "changed"})
    assert semantic_cache_key(scene, request) != key


def test_fingerprint_recipe_preserves_strict_identity_and_query():
    """Cache publication shares the live recipe without relaxing plane revision checks."""
    scene = _scene(_object("chair"))
    request = _request(scene)
    run = execute_analysis_request(scene, request)
    fingerprint, key, versions = requests._run_identity(scene, request)
    assert requests._request_key(fingerprint, request, versions) == key == run.snapshot.semantic_key
    assert requests._request_query(request, key) == run.query
    current = replace(request, request_id="new-job", plane=replace(request.plane, revision=4))
    current_key = requests._request_key(fingerprint, current, versions)
    assert current_key != key and is_stale(run.snapshot, scene, current)
    assert current_key == semantic_cache_key(scene, current)
    assert requests._request_query(current, current_key).frame.endswith(":4")


def test_native_core_imports_avoid_legacy_heavy_modules():
    """A fresh standalone interpreter can import requests without OCTA or numerical backends."""
    root = Path(__file__).resolve().parents[1]
    code = """
import importlib.abc
import sys
class BlockHeavy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        '''Reject heavy imports before any legacy initialization can occur.'''
        if fullname.split('.')[0] in {'octa', 'numpy', 'shapely', 'trimesh', 'colour'} or fullname in {'features.analyzer', 'features.scene_evaluator'}:
            raise AssertionError('unexpected heavy import: ' + fullname)
sys.meta_path.insert(0, BlockHeavy())
import features.scene_contract
import features.analysis_requests
assert 'features.analyzer' not in sys.modules
assert 'features.scene_evaluator' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_original_public_exports_and_star_import_remain_compatible():
    """The static lazy map preserves each original public name and caches its real object."""
    package = importlib.import_module(requests.__package__)
    expected = ["OrderAnalyzer", "Table", "Chair", "Entry", "Road", "TableTemplate", "TableGrid",
                "evaluate_scene", "export_adapter_payload_json", "load_structured_svg_scene",
                "scene_metric_overlay_svg", "validate_adapter_payload_json", "build_room_analysis_model"]
    assert package.__all__ == expected
    namespace = {}
    exec(f"from {package.__name__} import *", namespace)
    for name in expected:
        module = importlib.import_module(package._EXPORT_MODULES[name], package.__name__)
        assert namespace[name] is getattr(module, name) is getattr(package, name) is package.__dict__[name]
    with pytest.raises(AttributeError):
        getattr(package, "nonexistent_export")

