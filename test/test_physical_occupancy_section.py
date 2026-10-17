"""Generic exact-plane qualification and once-only physical owner accounting."""

from dataclasses import replace

import pytest
import trimesh
from shapely.geometry import GeometryCollection, mapping

from ..features.analysis_substitute_discovery import resolve_source_representation
from ..features.geometry_substitutes import mass_patch_from_mesh
from ..features.neutral_scene_views import _resolved_physical_occupancy
from ..features import neutral_scene_views as views
from ..features.scene_contract import MeshGeometry3D, SourceObject
from ..features.section_views import SECTION_ALGORITHM, exact_plane_section
from .test_physical_occupancy_resolution import _binding, _replace_source, _scene


QUERY = {"frame": "world_xy", "units": "m", "world_z_m": 1.6}


def _section_scene(*, top=3.0, shared=True):
    """Give an arbitrary two-owner fixture one real three-dimensional representative."""
    scene = _scene(coverage=("A", "B") if shared else ("A",))
    if shared:
        scene = _replace_source(scene, "B", factual_properties={"OM_FunctionSubstitutes": [_binding("B")]})
    mesh = trimesh.creation.box(extents=(2, 2, top))
    mesh.apply_translation((3, 3, top / 2))
    proxy = MeshGeometry3D(
        id="t", vertices=mesh.vertices.tolist(), triangle_indices=mesh.faces.tolist(), normals=(),
        is_manifold=True, is_closed=True, units="m", source_representation_id="GeneratedProxy",
        tessellation_settings={}, local_to_world_provenance={"world_transform_applied": True},
    )
    return replace(scene, geometries=tuple(proxy if item.id == "t" else replace(
        item, local_to_world_provenance={"world_transform_applied": True}) for item in scene.geometries))


def _record(scene, source_id="T", query=QUERY):
    """Bind pure section qualification to its selected source, mesh, and query."""
    source = next(item for item in scene.source_objects if item.id == source_id)
    mesh = next(item for item in scene.geometries if item.id == source.geometry_refs[0])
    return {"id": source_id, "section": exact_plane_section(mass_patch_from_mesh(mesh), world_z_m=query["world_z_m"]),
            "section_evidence": {"source_object_id": source_id, "geometry_refs": list(source.geometry_refs),
                                 "query": query, "algorithm": SECTION_ALGORITHM}}


def _account(scene, records, *, boundary=(), scoped=None):
    """Exercise the shared accounting seam without routing through the public evaluator."""
    return _resolved_physical_occupancy(scene, records, set(boundary),
                                       operation="physical_occupancy_section", query=QUERY,
                                       scoped_out_reasons=scoped)


def test_one_physical_binding_selects_same_target_for_both_queries():
    """The query changes geometry evidence rather than the three-dimensional representative."""
    scene = _section_scene()
    whole = resolve_source_representation(scene, "A", "physical_occupancy")
    section = resolve_source_representation(scene, "A", "physical_occupancy_section", query=QUERY)
    assert whole["selected_source"] == section["selected_source"] == "T"
    assert whole["coverage"] == section["coverage"] == ("A", "B")
    records, unknown, inventory = _account(scene, [_record(scene)])
    assert [row["id"] for row in records] == ["T"] and unknown == ["floor_slab"]
    assert [row["status"] for row in inventory[:2]] == ["substitute", "substitute"]


def test_legal_empty_is_eligible_and_accounted_without_xy_components():
    """An open degenerate below-plane mesh remains known empty with diagnostics intact."""
    scene = _section_scene(top=1)
    proxy = next(mesh for mesh in scene.geometries if mesh.id == "t")
    proxy = replace(proxy, triangle_indices=((0, 0, 1),), is_closed=False, is_manifold=False)
    scene = replace(scene, geometries=tuple(proxy if mesh.id == "t" else mesh for mesh in scene.geometries))
    result = resolve_source_representation(scene, "A", "physical_occupancy_section", query=QUERY)
    assert result["status"] == "accepted"
    record = _record(scene)
    assert record["section"]["status"] == "valid_empty_below_plane"
    assert record["section"]["degenerate_triangle_count"] == 1
    selected, unknown, _ = _account(scene, [record], scoped={"floor_slab": "support_slab"})
    assert len(selected) == 1 and unknown == []
    assert selected[0]["section"]["occupied_area_m2"] == 0


@pytest.mark.parametrize("failure", ["missing", "open", "binding", "query", "geometry", "algorithm", "multiple_refs", "duplicate_record"])
def test_failed_target_keeps_every_owner_unknown_without_original_fallback(failure):
    """A real original positive must never replace failed required target evidence."""
    scene = _section_scene()
    records = [_record(scene, "A"), _record(scene, "B")]
    target = _record(scene)
    if failure == "missing":
        target = None
    elif failure == "open":
        target["section"].update(status="unresolved_open_or_nonmanifold", occupied_geometry=None)
    elif failure == "binding":
        scene = _replace_source(scene, "B", factual_properties={"OM_FunctionSubstitutes": [{**_binding("B"), "source_object_id": "wrong"}]})
    elif failure in {"query", "geometry", "algorithm"}:
        key = {"query": "query", "geometry": "geometry_refs", "algorithm": "algorithm"}[failure]
        target["section_evidence"][key] = {**QUERY, "world_z_m": 9} if failure == "query" else ["wrong"] if failure == "geometry" else "unknown"
    elif failure == "multiple_refs":
        scene = _replace_source(scene, "T", geometry_refs=("t", "a"))
        target["section_evidence"]["geometry_refs"] = ["t", "a"]
    if target:
        records.append(target)
    if failure == "duplicate_record":
        records.append(target)
    selected, unknown, _ = _account(scene, records, scoped={"floor_slab": "support_slab"})
    assert selected == [] and unknown == ["A", "B"]


def test_invalid_declared_owner_cannot_fall_back_to_original():
    """An owner named in failed exact coverage remains unknown even without its binding."""
    scene = _section_scene()
    scene = _replace_source(scene, "B", factual_properties={})
    selected, unknown, inventory = _account(scene, [_record(scene), _record(scene, "B")], scoped={"floor_slab": "support_slab"})
    assert selected == [] and unknown == ["A", "B"]
    assert next(row for row in inventory if row["source_object_id"] == "B")["status"] == "unknown"


def test_mixed_boundary_coverage_does_not_reintroduce_boundary_uncertainty():
    """Only the interior owner is unknown when a combined target covers a boundary owner."""
    selected, unknown, inventory = _account(_section_scene(), [_record(_section_scene())], boundary=("B",), scoped={"floor_slab": "support_slab"})
    assert selected == [] and unknown == ["A"]
    assert next(row for row in inventory if row["source_object_id"] == "B")["reason"] == "selected_analysis_domain_member"


def test_explicit_scoped_reason_wins_over_default_boundary_label():
    """A caller's precise reason survives overlapping exclusion inputs."""
    _, _, inventory = _account(_section_scene(), [], boundary=("B",),
                               scoped={"B": "explicit_boundary_authority", "floor_slab": "support_slab"})
    assert next(row for row in inventory if row["source_object_id"] == "B")["reason"] == "explicit_boundary_authority"


def test_unknown_coverage_propagates_before_any_selected_record_survives(monkeypatch):
    """Later overlapping failures invalidate records selected earlier in source order."""
    scene = _replace_source(_section_scene(), "floor_slab", id="C")

    def resolution(scene, source_id, operation, *, query=None):
        """Supply overlapping groups to isolate the accounting closure seam."""
        if source_id == "C":
            return {"status": "unresolved", "reason": "missing_evidence"}
        return {"status": "accepted", "reason": "fixture", "selected_source": source_id,
                "selected_geometry": (), "coverage": ("A", "B") if source_id == "A" else ("B", "C"),
                "rejection_diagnostics": []}

    monkeypatch.setattr(views, "resolve_source_representation", resolution)
    selected, unknown, _ = _resolved_physical_occupancy(scene, [{"id": "A"}, {"id": "B"}], set())
    assert selected == [] and unknown == ["A", "B", "C"]


def test_duplicate_query_specific_bindings_are_ambiguous():
    """Two bindings of the same consumer cannot select a target per query."""
    scene = _section_scene()
    scene = _replace_source(scene, "A", factual_properties={"OM_FunctionSubstitutes": [_binding(), _binding()]})
    for operation, kwargs in [("physical_occupancy", {}), ("physical_occupancy_section", {"query": QUERY})]:
        result = resolve_source_representation(scene, "A", operation, **kwargs)
        assert result["status"] == "unresolved" and result["reason"] == "multiple_valid_substitutes"


@pytest.mark.parametrize("query", [None, {}, {**QUERY, "world_z_m": float("nan")}, {**QUERY, "world_z_m": True}, {**QUERY, "frame": "tilted"}, {**QUERY, "units": "mm"}])
def test_exact_query_requires_explicit_finite_world_metre_height(query):
    """No scene-plane default or malformed query can qualify a section."""
    result = resolve_source_representation(_section_scene(), "A", "physical_occupancy_section", query=query)
    assert result["status"] == "unresolved" and result["reason"] == "invalid_exact_world_plane_query"


def test_trend_only_binding_leaves_original_mass_and_helper_out_of_occupancy():
    """Trend's independent consumer cannot replace or erase physical originals."""
    scene = _section_scene(shared=False)
    scene = _replace_source(scene, "A", factual_properties={"OM_FunctionSubstitutes": [_binding(consumer="trend")]})
    scene = _replace_source(scene, "T", provenance={"representation_identifier": "Analysis"})
    selected, unknown, _ = _account(scene, [_record(scene, "A"), _record(scene, "B"), _record(scene)], scoped={"floor_slab": "support_slab"})
    assert {row["id"] for row in selected} == {"A", "B"} and unknown == []


def test_empty_array_without_qualified_status_is_unknown():
    """A zero-area payload alone cannot prove the plane is empty."""
    scene = _section_scene()
    record = _record(scene)
    record["section"].update(status="invalid_mesh", occupied_geometry=mapping(GeometryCollection()), occupied_area_m2=0)
    selected, unknown, _ = _account(scene, [record], scoped={"floor_slab": "support_slab"})
    assert selected == [] and unknown == ["A", "B"]
