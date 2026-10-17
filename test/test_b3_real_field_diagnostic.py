"""Focused missingness and sampling checks for the bounded real diagnostic."""

import importlib.util
import sys
from pathlib import Path

from shapely.geometry import MultiPoint, Polygon, box, shape

PATH = Path(__file__).parents[1] / "scripts/design/space_field/run_b3_real_field_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("b3_real_diagnostic", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_unsupported_mesh_remains_null_with_conservative_actual_vertex_support():
    """Unsupported sources cannot become an empty or zero occupancy channel."""
    hull = MultiPoint([(0, 0), (2, 0), (0, 2)]).convex_hull
    result, projection, support = MODULE.source_query({"solid_query_eligible": False}, None, hull, box(0, 0, 3, 3), [1.55, 1.65], True)
    assert result["raw_projection_geometry"] is None and result["raw_projection_area_m2"] is None
    assert result["complete_physical_occupancy_geometry"] is None
    assert projection is None and support.equals(hull)
    assert support.area == 2 and shape(result["clipped_uncertainty_support_geometry"]).area == 2


def test_empty_helper_with_height_candidate_stays_missing(monkeypatch):
    """Empty helper output within the height range is not certified absence."""
    from features.geometry_views import PlanProjection
    monkeypatch.setattr(MODULE, "plan_projection", lambda *args, **kwargs: PlanProjection("patch", (), None, ()))
    hull = box(0, 0, 1, 1)
    result, projection, support = MODULE.source_query({"solid_query_eligible": True}, object(), hull, hull, [.45, .55], True)
    assert result["status"] == "projection_missing" and projection is None and support.equals(hull)
    assert result["helper_uncertainty"] is None and result["raw_projection_area_m2"] is None


def test_positive_helper_never_certifies_exact_occupancy(monkeypatch):
    """A positive projection remains an approximation even without uncertainty."""
    from features.geometry_views import PlanProjection
    component = {"exterior": [(0, 0), (1, 0), (1, 1), (0, 1)], "holes": []}
    monkeypatch.setattr(MODULE, "plan_projection", lambda *args, **kwargs: PlanProjection("patch", (), None, (component,)))
    result, projection, support = MODULE.source_query({"solid_query_eligible": True}, object(), box(0, 0, 1, 1), box(0, 0, 2, 2), [.45, .55], True)
    assert projection.area == 1 and support.is_empty
    assert result["diagnostic_projection_status"] == "computed_approximation_only"
    assert result["exact_section_geometry"] is None and result["complete_physical_occupancy_geometry"] is None


def test_domain_holes_and_unknown_complete_channels_survive_sampling():
    """Qualified boundary distance includes holes without asserting known-free."""
    domain = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)], [[(1, 1), (2, 1), (2, 2), (1, 2)]])
    result = MODULE.sample_variant(domain, box(2, 0, 3, 4), box(0, 2, 1, 3), .5, (0, 0))
    cells = result["samples"]
    hole = next(c for c in cells if (c["x_m"], c["y_m"]) == (1.25, 1.25))
    near_hole = next(c for c in cells if (c["x_m"], c["y_m"]) == (.75, 1.25))
    assert not hole["domain_mask"] and hole["clearance_to_domain_boundary_m"] is None
    assert near_hole["clearance_to_domain_boundary_m"] == .25
    assert all(c["physical_occupancy_mask"] is None and c["known_free_mask"] is None and c["exact_section_mask"] is None for c in cells)
    assert all(c["complete_field_unassessed_mask"] for c in cells if c["domain_mask"])


def test_reconstruction_errors_are_against_same_diagnostic_target():
    """Directional sampling errors reference the approximation, never truth."""
    variant = MODULE.sample_variant(box(0, 0, 10, 8), box(4, 0, 6, 8), box(0, 0, 1, 1), 1, (.25, .25))
    comparison = variant["comparison"]
    assert comparison["signed_projection_point_area_error_m2"] == 0
    assert comparison["false_free_vs_diagnostic_target_m2"] > 0
    assert comparison["false_occupied_vs_diagnostic_target_m2"] > 0
    assert comparison["symmetric_difference_vs_diagnostic_target_m2"] == comparison["false_free_vs_diagnostic_target_m2"] + comparison["false_occupied_vs_diagnostic_target_m2"]
    assert "not_physical_truth" in comparison["reference"]


def test_polygonal_union_discards_zero_area_contacts():
    """The sampled area channel excludes line contacts without losing polygons."""
    from shapely.geometry import LineString
    audit = {}
    result = MODULE.polygonal_union([box(0, 0, 1, 1), LineString([(1, 0), (2, 0)])], audit)
    assert result.is_valid and result.area == 1
    assert audit["make_valid_applied"] is False and audit["removed_area_m2"] == 0
    assert audit["union_before_area_view"]["non_positive_polygon_leaf_types"] == {"LineString": 1}
    assert audit["union_before_area_view"]["removable_length_m"] == 1


def test_geos_comparison_failure_retains_masks_and_explicit_status(monkeypatch):
    """A failed overlay must preserve field samples without fabricating errors."""
    from shapely.errors import GEOSException
    def failed(*args, **kwargs):
        """Simulate the real mixed-dimensional overlay rejection."""
        raise GEOSException("observed overlay error")
    monkeypatch.setattr(MODULE.ACCEPTED, "_observation", failed)
    result = MODULE.sample_variant(box(0, 0, 4, 4), box(1, 0, 2, 4), box(0, 0, 1, 1), .5, (0, 0))
    assert result["samples"] and result["comparison"]["reconstruction_operation_error"] == "observed overlay error"
    assert result["comparison"]["false_free_vs_diagnostic_target_m2"] is None
    assert result["comparison"]["false_occupied_vs_diagnostic_target_m2"] is None
    assert result["comparison"]["reconstruction_status"] == "not_available_GEOS_overlay_error_no_scope_repair"


def test_invalid_positive_area_union_input_is_not_silently_discarded():
    """Invalid polygons must stop union rather than masquerade as absent geometry."""
    import pytest
    invalid = Polygon([(0, 0), (3, 0), (0, 2), (2, 2), (0, 0)])
    assert invalid.area > 0 and not invalid.is_valid
    with pytest.raises(ValueError, match="Invalid union input"):
        MODULE.polygonal_union([invalid])
