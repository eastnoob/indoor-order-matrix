"""Focused checks for the diagnostic B3 exploratory slice."""

import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).parents[1]
    / "scripts/design/space_field/run_b3_space_field_exploratory.py"
)
_SPEC = importlib.util.spec_from_file_location("b3_exploratory", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules["b3_exploratory"] = _MODULE
_SPEC.loader.exec_module(_MODULE)
evaluate_case = _MODULE.evaluate_case
fixture_cases = _MODULE.fixture_cases
run_experiment = _MODULE.run_experiment


def test_height_band_keeps_low_and_high_blockers_distinct():
    """Low and high blockers affect only their qualifying height bands."""
    cases = fixture_cases()
    low_lower = evaluate_case("low_blocker", cases["low_blocker"], band=(0, 1.5))
    low_upper = evaluate_case("low_blocker", cases["low_blocker"], band=(2, 3.5))
    high_lower = evaluate_case("high_blocker", cases["high_blocker"], band=(0, 1.5))
    high_upper = evaluate_case("high_blocker", cases["high_blocker"], band=(2, 3.5))
    assert low_lower["exact"]["positive_overlap_band_occupancy_area_m2"] > 0
    assert low_upper["exact"]["positive_overlap_band_occupancy_area_m2"] == 0
    assert high_lower["exact"]["positive_overlap_band_occupancy_area_m2"] == 0
    assert high_upper["exact"]["positive_overlap_band_occupancy_area_m2"] > 0


def test_parallel_channels_and_missing_domain_status_are_preserved():
    """Raw channels stay separate and missing domain is not encoded as zero."""
    result = evaluate_case("vertical_obstacle", fixture_cases()["vertical_obstacle"])
    sample = result["channels"][0]
    assert {"domain_mask", "occupancy_mask", "clearance_to_occupancy_m", "clearance_to_domain_boundary_m", "gaussian_group_support_raw"} <= sample.keys()
    missing = evaluate_case("missing_domain", fixture_cases()["missing_domain"])
    assert missing["provenance"]["status"] == "not_available"
    assert "analysis_domain" in missing["provenance"]["missingness"]
    assert missing["channels"] is None


def test_experiment_records_resolution_origin_variants_and_overhang_fixture():
    """The bundle retains 3D overhang coverage and sampling sensitivity evidence."""
    bundle = run_experiment()
    assert "overhang" in bundle["cases"]
    assert len(bundle["cases"]["overhang"]["sensitivity"]) == 6
    assert bundle["cases"]["overhang"]["sensitivity"][0]["channels"]
    assert bundle["interpretation"]["primary_field"] == "complete_coordinate_indexed_point_samples"


def test_eye_query_is_provisional_occupancy_and_not_visibility_or_walkability():
    """Eye-level evidence remains separate from visibility and walkability claims."""
    eye = run_experiment()["cases"]["vertical_obstacle"]["queries"]["eye_level_reference"]
    assert eye["provenance"]["frame"]["floor_datum_z_m"] == 0.0
    assert eye["provenance"]["visibility"]["status"] == "not_computed"
    assert eye["provenance"]["query"]["id"] == "eye_level_reference"


def test_eye_height_is_the_configurable_default_analysis_reference():
    """The default baseline follows a configured eye plane and band above floor."""
    bundle = run_experiment(1.7, (1.65, 1.75))
    assert bundle["floor_datum_z_m"] == 0.0
    assert bundle["default_analysis_reference"]["status"] == "provisional_configurable_not_anthropometric_standard"
    queries = bundle["cases"]["vertical_obstacle"]["queries"]
    assert {"lower_height_reference", "eye_level_reference", "overhead_reference"} == set(queries)
    assert queries["eye_level_reference"]["provenance"]["query"]["plane_z_m"] == 1.7
    assert queries["eye_level_reference"]["provenance"]["query"]["band_z_m"] == [1.65, 1.75]
    assert queries["eye_level_reference"]["provenance"]["frame"]["projection_support_plane"]["id"] == "world_xy"


def test_plane_section_and_positive_overlap_band_are_recorded_separately():
    """A boundary plane can differ from a band with positive source overlap."""
    result = evaluate_case("low_blocker", fixture_cases()["low_blocker"], query={"id": "edge", "plane_z_m": 1.0, "band_z_m": (0.9, 1.1)})
    assert result["exact"]["positive_overlap_band_occupancy_area_m2"] > 0
    assert result["exact"]["plane_section_occupancy_area_m2"] == 0


def test_overhang_preserves_shared_source_identity_and_layer_difference():
    """Lower support and upper canopy retain one identity while differing by query."""
    case = fixture_cases()["overhang"]
    body = evaluate_case("overhang", case, query={"id": "body", "band_z_m": (0, 1.5)})
    overhead = evaluate_case("overhang", case, query={"id": "overhead", "band_z_m": (2, 3.5)})
    assert body["audit_geometry"]["source_occupancy"]["area_m2"] < overhead["audit_geometry"]["source_occupancy"]["area_m2"]
    assert {item["source_identity"] for item in body["provenance"]["source_volumes"]} == {"overhang"}


def test_missing_invalid_and_known_empty_inputs_are_distinct():
    """Validation propagates unavailable and invalid evidence without empty aliases."""
    cases = fixture_cases()
    assert evaluate_case("missing_obstacles", cases["missing_obstacles"])["provenance"]["status"] == "not_available"
    assert evaluate_case("missing_groups", cases["missing_groups"])["provenance"]["status"] == "partial"
    empty = evaluate_case("empty", cases["empty"])
    assert empty["channels"][0]["clearance_to_occupancy_status"] == "known_empty"
    invalid = {"domain": cases["empty"]["domain"], "obstacles": [object()], "groups": []}
    assert evaluate_case("invalid", invalid)["provenance"]["status"] == "invalid"


def test_narrow_gap_sensitivity_and_gaussian_physical_distance_invariance():
    """Grid changes remain explicit while Gaussian support stays distance based."""
    case = fixture_cases()["narrow_gap"]
    coarse = evaluate_case("narrow_gap", case, spacing=1.0, origin=(0, 0))
    shifted = evaluate_case("narrow_gap", case, spacing=1.0, origin=(0.25, 0.25))
    assert coarse["exact"]["sampling_origin_offset_m"] != shifted["exact"]["sampling_origin_offset_m"]
    first = evaluate_case("vertical_obstacle", fixture_cases()["vertical_obstacle"], spacing=1.0)
    second = evaluate_case("vertical_obstacle", fixture_cases()["vertical_obstacle"], spacing=0.5, origin=(0.25, 0.25))
    first_value = next(cell["gaussian_group_support_raw"] for cell in first["channels"] if (cell["x_m"], cell["y_m"]) == (4.5, 3.5))
    second_value = next(cell["gaussian_group_support_raw"] for cell in second["channels"] if (cell["x_m"], cell["y_m"]) == (4.5, 3.5))
    assert first_value == second_value


def test_stage_three_fixtures_and_indexed_connectivity_are_auditable():
    """Stage-three fixtures expose vector and sampled connectivity separately."""
    bundle = run_experiment()
    assert {"connecting_passage", "exact_closed_passage", "edge_touch", "point_touch", "disconnected_pockets", "domain_hole_out_of_domain", "eye_face_contact"} <= set(bundle["cases"])
    result = bundle["cases"]["connecting_passage"]["sensitivity"][0]
    assert all({"cell_i", "cell_j", "plane_occupancy_mask", "band_occupancy_mask"} <= cell.keys() for cell in result["channels"])
    assert "vector_free_components" in result["exact"]
    assert "sampled_4_neighbor_free_components" in result["exact"]
    assert "sampled_8_neighbor_free_components" in result["exact"]
    assert result["exact"]["area_estimate_method"].endswith("non_conservative")
    comparison = result["observations"]["positive_overlap_band"]["reconstructed_center_labeled_cells"]
    assert {"symmetric_difference_area_m2", "false_free_area_m2", "false_occupied_area_m2"} <= comparison.keys()


def test_floor_datum_is_explicit_and_eye_offset_is_relative():
    """Eye query heights resolve from the configured floor datum and offset."""
    bundle = run_experiment(1.6, (1.55, 1.65), 0.4)
    eye = bundle["cases"]["vertical_obstacle"]["queries"]["eye_level_reference"]
    assert eye["provenance"]["frame"]["floor_datum_z_m"] == 0.4
    assert eye["provenance"]["query"]["plane_z_m"] == 2.0
    assert eye["provenance"]["query"]["eye_offset_m"] == 1.6
    assert eye["provenance"]["query"]["plane_convention"].startswith("experimental_open_interior")
    assert bundle["level_reference"] == {"source_role": "synthetic_authored_storey_level_fixture", "elevation": 0.4, "units": "m", "frame": "synthetic_cartesian_xy_z_up", "qualification_status": "explicit_authored_fixture_value_not_actual_ifc", "geometric_slab_z_role": "audit_only_not_datum_inference"}


def test_holes_clipping_and_invalid_fixtures_remain_explicit():
    """Domain holes, outside mass, and invalid inputs retain distinct evidence."""
    cases = fixture_cases()
    clipped = evaluate_case("domain_hole_out_of_domain", cases["domain_hole_out_of_domain"])
    assert clipped["provenance"]["domain_holes_m"]
    assert clipped["observations"]["positive_overlap_band"]["outside_domain_occupancy_area_m2"] > 0
    assert clipped["observations"]["positive_overlap_band"]["clipped_occupancy_area_m2"] == 0
    for name in ("invalid_geometry", "nonfinite_height", "nonfinite_group"):
        assert evaluate_case(name, cases[name])["provenance"]["status"] == "invalid"


@pytest.mark.parametrize("name,vector,four,eight", [("connecting_passage", 1, 2, 2), ("exact_closed_passage", 2, 2, 2), ("edge_touch", 2, 2, 2), ("point_touch", 2, 2, 1), ("disconnected_pockets", 2, 2, 2), ("fully_occupied", 0, 0, 0)])
def test_decisive_fixture_component_expectations(name, vector, four, eight):
    """Separate open free interiors from grid adjacency on decisive fixtures."""
    result = evaluate_case(name, fixture_cases()[name])["observations"]["positive_overlap_band"]
    assert (result["vector_free_components"], result["sampled_4_neighbor_free_components"], result["sampled_8_neighbor_free_components"]) == (vector, four, eight)


def test_refinement_and_shift_can_reveal_the_connecting_passage():
    """A real connector survives vector geometry while coarse points can miss it."""
    case = fixture_cases()["connecting_passage"]
    fine = evaluate_case("connecting_passage", case, spacing=0.5)
    shifted = evaluate_case("connecting_passage", case, origin=(0.25, 0.25))
    assert fine["exact"]["sampled_4_neighbor_free_components"] == 1
    assert shifted["exact"]["sampled_4_neighbor_free_components"] == 1


def test_shifted_lattice_includes_negative_indices_inside_the_extent():
    """Integer lattice bounds include centers on the previously skipped side."""
    cells = evaluate_case("empty", fixture_cases()["empty"], origin=(0.75, 0.75))["channels"]
    assert min(cell["x_m"] for cell in cells) == 0.25
    assert min(cell["y_m"] for cell in cells) == 0.25
    assert any(cell["cell_i"] == -1 and cell["cell_j"] == -1 for cell in cells)


def test_eye_face_disagreement_and_balanced_reconstruction_error_are_visible():
    """Plane faces and cancelled signed error remain inspectable in samples."""
    face = evaluate_case("eye_face_contact", fixture_cases()["eye_face_contact"])
    assert face["exact"]["eye_plane_band_mask_disagreement_count"] == 8
    assert face["observations"]["open_interior_plane"]["clipped_occupancy_area_m2"] == 0
    shifted = evaluate_case("vertical_obstacle", fixture_cases()["vertical_obstacle"], origin=(0.25, 0.25))
    band = shifted["observations"]["positive_overlap_band"]
    reconstruction = band["reconstructed_center_labeled_cells"]
    assert band["occupancy_area_error_m2"] == 0
    assert reconstruction["false_free_area_m2"] > 0
    assert reconstruction["false_occupied_area_m2"] > 0
    assert reconstruction["symmetric_difference_area_m2"] == reconstruction["false_free_area_m2"] + reconstruction["false_occupied_area_m2"]


def test_missing_authored_level_elevation_is_not_zero():
    """A missing numeric datum is rejected while explicitly authored zero works."""
    assert _MODULE.height_queries(floor_datum_z_m=0.0)[1]["plane_z_m"] == 1.6
    with pytest.raises(ValueError):
        _MODULE.height_queries(floor_datum_z_m=None)
