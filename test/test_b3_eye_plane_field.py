"""Focused qualification tests for the fixed primary eye-plane field."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import box, shape

PATH = Path(__file__).parents[1] / "scripts/design/space_field/run_b3_eye_plane_field.py"
SPEC = importlib.util.spec_from_file_location("b3_eye_plane", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def record(mesh, *, identifier="fixture"):
    """Serialize a synthetic mesh through the same frozen world-metre boundary."""
    return {"id": identifier, "vertices": mesh.vertices.tolist(), "triangles": mesh.faces.tolist(),
            "is_closed": bool(mesh.is_watertight), "is_manifold": bool(mesh.is_watertight),
            "units": "m", "transform_applied": True}


def translated_box(extents, translation):
    """Create a closed axis-aligned solid without changing its triangle topology."""
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(translation)
    return mesh


def test_sloped_solid_section_differs_from_full_xy_projection():
    """A tetrahedron slice must shrink with height instead of using its full footprint."""
    vertices = np.array([[-2, -2, 0], [2, -2, 0], [0, 2, 0], [0, 0, 3.2]], dtype=float)
    mesh = trimesh.Trimesh(vertices=vertices, faces=[[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]], process=False)
    result = MODULE.section_source(record(mesh))
    assert result["status"] == "qualified_closed_section"
    assert 0 < result["occupied_area_m2"] < shape({"type": "Polygon", "coordinates": [[[-2, -2], [2, -2], [0, 2], [-2, -2]]]}).area


def test_nested_shells_stay_unknown_and_disconnected_components_preserve_topology():
    """Orientation alone cannot declare a cavity; disjoint sections remain supported."""
    outer = translated_box((6, 6, 4), (0, 0, 1.6))
    inner = translated_box((2, 2, 4), (0, 0, 1.6))
    inner.faces = inner.faces[:, ::-1]
    cavity = trimesh.util.concatenate([outer, inner])
    cavity_result = MODULE.section_source(record(cavity, identifier="cavity"))
    assert cavity_result["status"] == "unresolved_compound_shell_interior"
    assert cavity_result["occupied_geometry"] is None
    assert [s["signed_volume_m3"] > 0 for s in cavity_result["connected_shell_audit"]["shells"]] == [True, False]

    disconnected = trimesh.util.concatenate([translated_box((1, 1, 4), (-2, 0, 1.6)), translated_box((1, 1, 4), (2, 0, 1.6))])
    disconnected_result = MODULE.section_source(record(disconnected, identifier="disconnected"))
    disconnected_geometry = shape(disconnected_result["occupied_geometry"])
    assert disconnected_result["status"] == "qualified_closed_section"
    assert disconnected_geometry.geom_type == "MultiPolygon" and len(disconnected_geometry.geoms) == 2


def test_above_and_below_sources_are_valid_empty_without_solid_inference():
    """Triangle ranges entirely on one side prove an empty exact-plane result."""
    below = MODULE.section_source(record(translated_box((1, 1, 1), (0, 0, .5)), identifier="below"))
    above = MODULE.section_source(record(translated_box((1, 1, 1), (0, 0, 2.5)), identifier="above"))
    assert below["status"] == "valid_empty_below_plane" and below["occupied_area_m2"] == 0
    assert above["status"] == "valid_empty_above_plane" and above["occupied_area_m2"] == 0
    degenerate_below = translated_box((1, 1, 1), (0, 0, .5))
    degenerate_below.faces = np.vstack([degenerate_below.faces, [0, 0, 1]])
    invalid_but_absent = MODULE.section_source(record(degenerate_below))
    assert invalid_but_absent["source_geometry_status"] == "invalid_degenerate_mesh"
    assert invalid_but_absent["status"] == "valid_empty_below_plane"
    assert invalid_but_absent["degenerate_triangle_count"] == 1
    assert shape(invalid_but_absent["unknown_support_geometry"]).is_empty


def test_nested_positive_and_overlapping_shells_cannot_create_false_empty():
    """Whole-object XOR must not qualify nested positive solids or overlapping component interiors."""
    outer = translated_box((6, 6, 4), (0, 0, 1.6))
    for other in (translated_box((2, 2, 2), (0, 0, 1.6)), translated_box((6, 6, 4), (2, 0, 1.6))):
        result = MODULE.section_source(record(trimesh.util.concatenate([outer, other])))
        assert result["status"] == "unresolved_compound_shell_interior"
        assert result["occupied_geometry"] is None
        audit = result["connected_shell_audit"]
        assert all(s["signed_volume_m3"] > 0 for s in audit["shells"])
        assert audit["plane_shell_pairs"][0]["intersection_area_m2"] > 0
        samples = MODULE.sample_variant(box(-1, -1, 1, 1), MODULE.EMPTY,
                                       [("fixture", shape(result["unknown_support_geometry"]))], [], .5, (0, 0))
        assert all(s["occupancy_value"] is None for s in samples["samples"])


def test_cross_shell_coincident_ray_hits_are_not_deduplicated_together():
    """Separate closed boxes have near-coincident ray hits that whole-object deduplication merges."""
    first = translated_box((2, 2, 4), (0, 0, 1.6))
    second = translated_box((2, 2, 4), (2 + 1e-10, 0, 1.6))
    result = MODULE.section_source(record(trimesh.util.concatenate([first, second])))
    assert result["status"] == "qualified_closed_section"
    assert result["occupied_area_m2"] == 8
    assert result["connected_shell_audit"]["plane_shell_pairs"][0]["intersection_area_m2"] == 0
    assert any(not probe["unanimous"] for probe in result["whole_object_face_parity_probes"])
    assert all(probe["unanimous"] and probe["inside"] for probe in result["face_parity_probes"])
    assert any(sum(p["ray_hit_counts"][0] for p in probe["component_probes"]) == 3
               for probe in result["face_parity_probes"])


def test_open_coplanar_and_degenerate_inputs_stay_unresolved_or_invalid():
    """The plane path must not close open surfaces or choose a coplanar boundary side."""
    open_mesh = translated_box((2, 2, 4), (0, 0, 1.6))
    open_mesh.update_faces(np.arange(len(open_mesh.faces) - 1))
    opened = MODULE.section_source(record(open_mesh, identifier="open"))
    assert opened["status"] == "unresolved_open_or_nonmanifold" and opened["occupied_geometry"] is None

    coplanar = MODULE.section_source(record(translated_box((1, 1, 1.6), (0, 0, .8)), identifier="coplanar"))
    assert coplanar["status"] == "unresolved_boundary_or_coplanar" and coplanar["occupied_geometry"] is None

    degenerate = translated_box((1, 1, 4), (0, 0, 1.6))
    degenerate.faces = np.vstack([degenerate.faces, [0, 0, 1]])
    invalid = MODULE.section_source(record(degenerate, identifier="degenerate"))
    assert invalid["status"] == "invalid_degenerate_mesh" and invalid["occupied_geometry"] is None


def test_shared_indexed_edge_eliminates_roundoff_without_proximity_repair():
    """One computation per source edge fixes arithmetic gaps while retaining raw failure evidence."""
    cylinder = trimesh.creation.cylinder(radius=.3, height=4.5, sections=360)
    cylinder.apply_translation((0, 0, 2.25))
    result = MODULE.section_source(record(cylinder, identifier="cylinder"))
    audit = result["indexed_edge_intersection_audit"]
    assert result["status"] == "qualified_closed_section"
    assert audit["numeric_endpoint_merge_tolerance_m"] == 0 and audit["source_vertices_welded"] is False
    assert audit["directed_roundoff_mismatch_count"] > 0 and audit["max_directed_roundoff_mismatch_m"] < 1e-12
    assert all(value == 2 for value in audit["source_edge_face_multiplicities"])


def test_sampling_propagates_local_unknown_and_keeps_distances_separate():
    """Negative occupancy stays unknown under unresolved support while positive evidence survives."""
    domain = box(0, 0, 3, 2)
    occupied = box(0, 0, 1, 2)
    result = MODULE.sample_variant(domain, occupied, [("open", box(1, 0, 2, 2))], [occupied.boundary], .5, (0, 0))
    occupied_cell = next(s for s in result["samples"] if (s["x_m"], s["y_m"]) == (.25, .25))
    unknown_cell = next(s for s in result["samples"] if (s["x_m"], s["y_m"]) == (1.25, .25))
    empty_cell = next(s for s in result["samples"] if (s["x_m"], s["y_m"]) == (2.25, .25))
    assert occupied_cell["occupancy_value"] is True and occupied_cell["complete_physical_clearance_m"] is None
    assert unknown_cell["occupancy_value"] is None and unknown_cell["unresolved_source_ids"] == ["open"]
    assert empty_cell["occupancy_value"] is False and empty_cell["distance_to_domain_boundary_m"] == .25


def test_disconnected_above_below_closed_components_have_qualified_empty_section():
    """A global range straddling the plane does not imply any intersecting triangles or occupancy."""
    mesh = trimesh.util.concatenate([translated_box((1, 1, .5), (0, 0, .5)), translated_box((1, 1, .5), (0, 0, 2.5))])
    result = MODULE.section_source(record(mesh, identifier="straddle_but_empty"))
    assert result["crossing_triangle_count"] == 0 and result["status"] == "qualified_empty_section"
    assert result["occupied_area_m2"] == 0
    variant = MODULE.sample_variant(box(-1, -1, 1, 1), shape(result["occupied_geometry"]), [], [], .5, (0, 0))
    assert all(s["occupancy_value"] is False and s["distance_to_raw_qualified_occupied_subset_m"] is None for s in variant["samples"])


def test_invalid_missing_support_and_exact_section_boundary_remain_unknown():
    """Invalid input cannot prove absence, and exact boundary contacts keep their ambiguity."""
    invalid = MODULE.section_source({"units": "m", "transform_applied": True, "vertices": [], "triangles": []})
    assert invalid["status"] == "invalid_mesh" and invalid["unknown_support_geometry"] is None
    domain = box(0, 0, 2, 2)
    variant = MODULE.sample_variant(domain, domain, [("invalid", None)], [domain.boundary], .5, (0, 0))
    assert all(s["occupancy_value"] is True and s["unresolved_source_ids"] == ["invalid"] for s in variant["samples"])
    empty_variant = MODULE.sample_variant(domain, MODULE.EMPTY, [("invalid", None)], [], .5, (0, 0))
    assert all(s["occupancy_value"] is None for s in empty_variant["samples"])
    boundary_variant = MODULE.sample_variant(domain, box(.25, 0, 1, 2), [], [box(.25, 0, 1, 2).boundary], .5, (0, 0))
    assert next(s for s in boundary_variant["samples"] if s["x_m"] == .25)["occupancy_value"] is None
