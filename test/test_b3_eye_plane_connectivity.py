"""Focused tests of conditional geometric versus sampled connectivity evidence."""

import importlib.util
import sys
from pathlib import Path

from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

PATH = Path(__file__).parents[1] / "scripts/design/space_field/run_b3_eye_plane_connectivity.py"
SPEC = importlib.util.spec_from_file_location("b3_eye_connectivity", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
EYE_SPEC = importlib.util.spec_from_file_location("b3_eye_connectivity_fixture_source", PATH.with_name("run_b3_eye_plane_field.py"))
EYE = importlib.util.module_from_spec(EYE_SPEC)
sys.modules[EYE_SPEC.name] = EYE
EYE_SPEC.loader.exec_module(EYE)
EMPTY = GeometryCollection()


def accepted_variant(domain, spacing=1, occupied=EMPTY, unknown=EMPTY, origin=(0, 0)):
    """Use the accepted sampler to author fixtures with its unchanged boundary semantics."""
    return EYE.sample_variant(domain, occupied, [("unresolved-fixture", unknown)],
                              [] if occupied.is_empty else [occupied.boundary], spacing, origin)


def compare(domain, variant, occupied=EMPTY, unknown=EMPTY):
    """Compare a fixture through the same reference and graph entry points as the runner."""
    boundaries = [] if occupied.is_empty else [occupied.boundary]
    reference = MODULE.geometric_reference(domain, occupied, unknown, boundaries)
    assert reference["status"] == "computed", reference
    return MODULE.compare_variant(variant, reference["value"], domain, occupied, unknown, boundaries, "fixture")


def test_unknown_separator_is_not_a_vertex_or_occupied():
    """A full unknown strip splits both graphs while retaining unknown point states."""
    domain, unknown = box(0, 0, 3, 2), box(1, 0, 2, 2)
    variant = accepted_variant(domain, unknown=unknown)
    result = compare(domain, variant, unknown=unknown)
    for key in ("four_neighbor", "eight_neighbor"):
        assert result[key]["vertex_count"] == 4
        assert len(result[key]["components"]) == 2
        assert not result[key]["correspondence"]["merged_graph_components"]
    assert all(sample["occupancy_value"] is None for sample in variant["samples"] if sample["unknown_mask"])


def test_unrestricted_diagonal_merges_point_contact_geometries():
    """Point contact does not connect open interiors, but unrestricted diagonal adjacency does."""
    domain = MultiPolygon([box(0, 0, 1, 1), box(1, 1, 2, 2)])
    result = compare(domain, accepted_variant(domain))
    assert len(result["four_neighbor"]["components"]) == 2
    assert len(result["eight_neighbor"]["components"]) == 1
    assert len(result["eight_neighbor"]["correspondence"]["merged_graph_components"]) == 1
    assert result["eight_neighbor"]["edge_diagnostics"]["reason_edge_counts"]["different_geometric_membership"] == 1


def test_positive_interior_overrides_unknown_and_is_excluded_from_empty_graph():
    """An overlapping unresolved support must not relabel established mass as unknown or empty."""
    domain, occupied, unknown = box(0, 0, 2, 2), box(0, 0, 1, 1), box(0, 0, 2, 1)
    variant = accepted_variant(domain, occupied=occupied, unknown=unknown)
    positive = next(sample for sample in variant["samples"] if (sample["cell_i"], sample["cell_j"]) == (0, 0))
    assert positive["occupancy_value"] is True and positive["unknown_mask"] is False
    assert positive["unresolved_source_ids"] == ["unresolved-fixture"]
    result = compare(domain, variant, occupied, unknown)
    assert result["four_neighbor"]["vertex_count"] == 2
    assert all("fixture:0:0" not in component["sample_ids"] for component in result["eight_neighbor"]["components"])


def test_narrow_missed_connector_splits_a_single_geometric_component():
    """A positive-width connector missed by all centers must remain in the vector reference."""
    domain = unary_union([box(0, 0, 1, 2), box(2, 0, 3, 2), box(.8, .95, 2.2, 1.05)])
    result = compare(domain, accepted_variant(domain))
    for key in ("four_neighbor", "eight_neighbor"):
        assert len(result[key]["components"]) == 2
        assert len(result[key]["correspondence"]["split_geometric_components"]) == 1
    assert result["area_diagnostics"]["missed_empty_area_m2"] > 0


def test_equal_counts_can_hide_a_merge_and_a_split():
    """Equal total component counts cannot substitute for membership correspondence."""
    left = unary_union([box(0, 0, 1, 2), box(2, 0, 3, 2), box(.8, .95, 2.2, 1.05)])
    domain = MultiPolygon([left, box(3, 2, 4, 3)])
    result = compare(domain, accepted_variant(domain))
    graph = result["eight_neighbor"]
    assert len(MODULE.PRIOR.ACCEPTED._polygon_parts(domain)) == len(graph["components"]) == 2
    assert len(graph["correspondence"]["merged_graph_components"]) == 1
    assert len(graph["correspondence"]["split_geometric_components"]) == 1


def test_tiny_missed_component_and_domain_boundary_sample_survive():
    """Zero deletion tolerance preserves tiny islands and graph vertices on covered boundaries."""
    domain = MultiPolygon([box(0, 0, 1, 1), box(2, 0, 2.000001, .000001)])
    variant = accepted_variant(domain)
    result = compare(domain, variant)
    assert result["four_neighbor"]["correspondence"]["missed_geometric_component_ids"]
    variant["samples"][0].update(x_m=0, y_m=.5)
    boundary_result = compare(domain, variant)
    assert boundary_result["four_neighbor"]["vertex_count"] == 1
    assert len(boundary_result["four_neighbor"]["correspondence"]["unassigned_boundary_or_reference_samples"]) == 1


def test_missing_invalid_and_interior_line_are_not_computed_empty():
    """Unavailable references retain graph evidence instead of fabricating zero components."""
    domain = box(0, 0, 2, 2)
    invalid = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])
    for occupied, boundaries in ((None, []), (invalid, []), (EMPTY, [LineString([(1, 0), (1, 2)])])):
        reference = MODULE.geometric_reference(domain, occupied, EMPTY, boundaries)
        assert reference["status"] == "not_available" and reference["value"] is None
        assert reference["error"]
        result = MODULE.compare_variant(accepted_variant(domain), None, domain, EMPTY, EMPTY, [], "fixture")
        assert result["four_neighbor"]["vertex_count"] == 4
        assert result["four_neighbor"]["correspondence"] is None
    empty = MODULE.geometric_reference(domain, domain, EMPTY, [domain.boundary])
    assert empty["status"] == "computed" and empty["value"].is_empty


def test_geometry_failure_retains_original_error_and_graph(monkeypatch):
    """A reconstruction error must not erase unaffected graph memberships."""
    def fail(*args):
        """Simulate one original geometry failure without a fallback or retry."""
        raise RuntimeError("original geometry error")
    monkeypatch.setattr(MODULE, "reconstruction", fail)
    result = compare(box(0, 0, 2, 2), accepted_variant(box(0, 0, 2, 2)))
    assert result["area_diagnostics"] is None
    assert result["area_diagnostics_status"]["error"] == "RuntimeError: original geometry error"
    assert result["eight_neighbor"]["vertex_count"] == 4


def test_edges_cross_unknown_and_holes_without_filtering():
    """Thin exclusions can be crossed by graph edges while their endpoints remain conditional empty."""
    domain = Polygon([(0, 0), (3, 0), (3, 2), (0, 2)], holes=[[(.9, .4), (1.1, .4), (1.1, .6), (.9, .6)]])
    unknown = box(1.9, 0, 2.1, 2)
    result = compare(domain, accepted_variant(domain, unknown=unknown), unknown=unknown)
    diagnostics = result["four_neighbor"]["edge_diagnostics"]
    assert diagnostics["reason_edge_counts"]["unknown_support"] == 2
    assert diagnostics["reason_edge_counts"]["domain_hole"] == 1
    assert diagnostics["affected_edge_count"] == 3
    assert len(result["four_neighbor"]["components"]) == 1


def test_edge_tangent_to_hole_corner_retains_boundary_contact():
    """A corner tangent touches excluded open-interior boundary without a positive-length crossing."""
    domain = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)],
                     holes=[[(1, 1), (2, 1), (2, 2), (1, 2)]])
    variant = accepted_variant(domain)
    graph, vertices, edges = MODULE.build_sample_graph(variant, "fixture", True)
    tangent = [((0, 1), (1, 0))]
    assert tangent[0] in edges
    diagnostics = MODULE.edge_diagnostics(tangent, vertices, domain, EMPTY, EMPTY, [], None, "fixture")
    assert diagnostics["affected_edge_count"] == 1
    assert diagnostics["reason_edge_counts"] == {"domain_boundary_contact": 1}
    assert diagnostics["examples"][0]["coordinates_m"] == [(0.5, 1.5), (1.5, 0.5)]
    assert graph["edge_count"] == len(edges)


def test_zero_area_mass_contact_is_boundary_diagnostic_only():
    """Linear clipping contacts cannot be counted as positive-area qualified mass crossings."""
    domain = box(0, 0, 2, 2)
    variant = accepted_variant(domain)
    _, vertices, _ = MODULE.build_sample_graph(variant, "fixture", False)
    contact = LineString([(.5, .5), (1.5, .5)])
    diagnostics = MODULE.edge_diagnostics([((0, 0), (1, 0))], vertices, domain, EMPTY,
                                          GeometryCollection([contact]), [contact], None, "fixture")
    assert diagnostics["reason_edge_counts"] == {"section_boundary_contact": 1}
