"""Focused pure tests for the T4 display-only overlay boundary."""

import json
from types import SimpleNamespace
import pytest
from shapely.geometry import Polygon

from ..adapters import blender_analysis_result_wire as wire
from ..adapters.blender_analysis_session import build_display_fragments
from ..blender_addon.order_analyzer_ui import overlay
from .test_analysis_requests import _domain_mesh


def _document():
    """Build a small validated free-space document with two display fragments."""
    document = {
        "kind": "free_space_run", "result_id": "job", "job_id": "job",
        "schema_version": wire.SCHEMA_VERSION, "algorithm_version": wire.ALGORITHM_VERSION,
        "plane_uuid": "plane", "plane_revision": 1, "semantic_key": "semantic",
        "backend_versions": {"executor": wire.REQUEST_VERSION},
        "identity": {"project_source_identity": {"request_source_fingerprint": "source"},
                     "request_source_fingerprint": "source", "domain_identity": {"id": "domain"}, "plane_uuid": "plane",
                     "plane_revision": 1, "semantic_key": "semantic", "operation": "free_space",
                     "query_key": {"kind": "whole_height_projection"}, "request_identity": "request"},
        "binding": {"job_id": "job"},
        "tables": {"snapshot": {"request": {"domain": {"id": "domain"}, "sampling": {"n_rows": 1, "n_cols": 1},
                                      "plane": {"identity": "plane", "revision": 1},
                                      "geometry_query": {"kind": "whole_height_projection"}, "request_id": "request",
                                      "operation": "free_space"}, "semantic_key": "semantic", "backend_versions": {"executor": wire.REQUEST_VERSION},
                                      "source_fingerprint": "source",
                                      "provenance": {"algorithm_version": wire.REQUEST_VERSION, "schema_version": wire.REQUEST_VERSION,
                                                      "project_source_identity": {"request_source_fingerprint": "source"}}},
                   "lattice": {"n_rows": 1, "n_cols": 1}, "source_audit": {}, "sample_support": {},
                   "sample_provenance": {"algorithm_version": 3, "schema_version": 3},
                   "values": [{"domain_id": "domain", "frame": "frame", "plane": {"identity": "plane"},
                               "height_band": None, "demand": None, "tolerance": 0.0, "revision": "1"}, [], "", wire.REQUEST_VERSION]},
        "support_status": "established", "explanation": None,
        "cells": [{"row": 0, "column": 0, "value": False, "status": "established", "query_ref": 0,
                   "support_delta": {"changes": {}, "removed": []}, "source_ids_ref": 1, "provenance_delta": {"changes": {"algorithm_version": 3, "schema_version": 3}, "removed": []},
                   "provenance_support": False, "explanation_ref": 2}],
        "display_fragments": [
            {"cell_index": 0, "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "faces": [[0, 1, 2]]},
            {"cell_index": 0, "vertices": [[1, 1, 0], [2, 1, 0], [1, 2, 0]], "faces": [[0, 1, 2]]},
    ]}
    document["digest"] = wire.document_digest(document)
    wire.validate_document(document)
    return document


def test_build_overlay_mesh_keeps_multiple_faces_and_frozen_world_pose():
    """Overlay fragments retain one cell identity and are not parented to a plane."""
    result = wire.ValidatedAnalysisResult(_document())
    record = overlay.build_overlay_mesh(result, display_lift_m=0.02)
    assert record.faces
    assert record.face_cell_indices == (0, 0)
    assert record.parent is None
    assert all(vertex[2] == pytest.approx(0.02) for vertex in record.vertices)


@pytest.mark.parametrize("lift", [float("nan"), float("inf"), -1, True])
def test_overlay_rejects_nonfinite_or_invalid_lift(lift):
    """Invalid display offsets must fail before generating native geometry."""
    with pytest.raises(ValueError, match="finite"):
        overlay.build_overlay_mesh(wire.ValidatedAnalysisResult(_document()), display_lift_m=lift)


def test_native_overlay_converts_world_metres_to_scene_units():
    """A centimetre-scale scene receives coordinates in centimetres, not metres."""
    vertices = []
    mesh = SimpleNamespace(from_pydata=lambda points, edges, faces: vertices.extend(points), update=lambda: None)
    class NativeObject(dict):
        """Support native custom properties without importing Blender."""
    bpy = SimpleNamespace(data=SimpleNamespace(meshes=SimpleNamespace(new=lambda name: mesh),
        objects=SimpleNamespace(new=lambda name, data: NativeObject())),
        context=SimpleNamespace(scene=SimpleNamespace(unit_settings=SimpleNamespace(scale_length=.01),
        collection=SimpleNamespace(objects=SimpleNamespace(link=lambda obj: None)))))
    overlay.build_native_mesh(wire.ValidatedAnalysisResult(_document()), bpy_module=bpy)
    assert vertices[1] == pytest.approx((100, 0, 2))


def test_inspect_cell_reads_authoritative_wire_record():
    """Inspection returns the complete authoritative cell rather than mesh color."""
    result = wire.ValidatedAnalysisResult(_document())
    inspected = overlay.inspect_cell(result, row=0, column=0)
    assert inspected["value"] is False
    assert inspected["status"] == "established"


def test_native_overlay_is_linked_into_the_active_scene():
    """Published overlay geometry must belong to the visible scene, not just bpy.data."""
    linked = []
    mesh = SimpleNamespace(from_pydata=lambda *args: None, update=lambda: None)
    class NativeObject(dict):
        """Expose Blender-style custom properties and an ordinary parent field."""

    native_object = NativeObject()
    bpy = SimpleNamespace(
        data=SimpleNamespace(meshes=SimpleNamespace(new=lambda name: mesh),
                             objects=SimpleNamespace(new=lambda name, data: native_object)),
        context=SimpleNamespace(scene=SimpleNamespace(collection=SimpleNamespace(
            objects=SimpleNamespace(link=linked.append)))))

    created = overlay.build_native_mesh(wire.ValidatedAnalysisResult(_document()), bpy_module=bpy)

    assert linked == [created]
    assert created["om_analysis_role"] == "overlay" and created.parent is None


def test_restore_embedded_result_uses_strict_wire_reader():
    """Embedded JSON restores as an immutable validated result without a sidecar."""
    restored = overlay.restore_embedded_result(json.dumps(_document(), separators=(",", ":")))
    assert isinstance(restored, wire.ValidatedAnalysisResult)
    with pytest.raises(ValueError):
        overlay.restore_embedded_result(json.dumps({"schema_version": "future"}))


def test_fragments_clip_exact_domain_and_holes():
    """Pixi fragments cover the cell/domain intersection without filling a hole."""
    mesh = _domain_mesh((0, 0), 2, [[(0.75, 0.75), (1.25, 0.75), (1.25, 1.25), (0.75, 1.25), (0.75, 0.75)]])
    request = SimpleNamespace(sampling=SimpleNamespace(origin=(0.0, 0.0), spacing=0.5, n_rows=4, n_cols=4),
                             plane=SimpleNamespace(origin=(0.0, 0.0, 1.6)))
    fragments = build_display_fragments(SimpleNamespace(snapshot=SimpleNamespace(request=request)), (mesh,))
    hole = Polygon([(0.75, 0.75), (1.25, 0.75), (1.25, 1.25), (0.75, 1.25)])
    area = 0.0
    for fragment in fragments:
        for face in fragment["faces"]:
            points = [fragment["vertices"][index] for index in face]
            triangle = Polygon([(point[0], point[1]) for point in points])
            assert not hole.contains(triangle.representative_point())
            area += triangle.area
    assert area == pytest.approx(4.0 - hole.area)


def test_fragments_project_local_lattice_back_to_translated_rotated_world_plane():
    """Translated and XY-rotated planes keep local cell coverage and world placement."""
    plane = SimpleNamespace(origin=(10.0, 20.0, 5.0),
                            basis=((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    local = [(0., 0.), (1., 0.), (1., 1.), (0., 1.)]
    vertices = tuple((10.0 - y, 20.0 + x, 5.0) for x, y in local)
    mesh = SimpleNamespace(vertices=vertices, triangle_indices=((0, 1, 2), (0, 2, 3)))
    request = SimpleNamespace(sampling=SimpleNamespace(origin=(0.0, 0.0), spacing=.5, n_rows=2, n_cols=2),
                             plane=plane)
    fragments = build_display_fragments(SimpleNamespace(snapshot=SimpleNamespace(request=request)), (mesh,))
    assert fragments
    points = [point for fragment in fragments for point in fragment["vertices"]]
    assert all(point[2] == pytest.approx(5.0) for point in points)
    assert min(point[0] for point in points) == pytest.approx(9.0)
    assert max(point[0] for point in points) == pytest.approx(10.0)
    assert min(point[1] for point in points) == pytest.approx(20.0)
    assert max(point[1] for point in points) == pytest.approx(21.0)

