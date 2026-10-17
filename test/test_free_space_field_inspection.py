"""Focused synthetic contract checks for the offline inspection runner."""

from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import Point, Polygon

_path = Path(__file__).parents[1] / "scripts/design/space_field/run_free_space_field_inspection.py"
_spec = importlib.util.spec_from_file_location("free_space_field_inspection", _path)
_runner = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_runner)


def _handoff(tmp_path: Path) -> Path:
    """Write a minimal effective-view handoff accepted by the reuse path."""
    path = tmp_path / "handoff"
    path.mkdir()
    payload = {
        "schema": "free-space-field-inspection/v1", "frame": "world_xy", "units": "m",
        "origin_offset_m": [0.25, 0.5], "source_origin_offset_m": [0.0, 0.0],
        "query_scope": "whole_height_plan", "resolution_m": 0.25,
        "domain": {"id": "b3-selected-s3-whole-height", "frame": "world_xy", "components": [{
            "exterior": [[0, 0], [1, 0], [1, 1], [0, 1]],
            "holes": [[[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]],
                      [[0.7, 0.7], [0.8, 0.7], [0.8, 0.8], [0.7, 0.8]]]}]},
        "source_layer": [
            {"id": "o1", "represented_source_ids": ["o1"], "representation_status": "original",
             "geometry_components": [{"exterior": [[0, 0], [0.25, 0], [0.25, 0.25], [0, 0.25]], "holes": []}],
             "representation_provenance": {"method": "synthetic"}, "_source_geometry_refs": ["mesh:o1"],
             "adapter_refs": {"source": "synthetic"}},
            {"id": "proxy:p", "represented_source_ids": ["owner:p"], "representation_status": "accepted",
             "geometry_components": [{"exterior": [[0.5, 0.5], [0.75, 0.5], [0.75, 0.75], [0.5, 0.75]], "holes": []}],
             "representation_provenance": {"representation_identifier": "GeneratedProxy"},
             "_source_geometry_refs": ["mesh:proxy"], "adapter_refs": {"source": "synthetic"}},
            {"id": "wall1", "represented_source_ids": ["wall1"], "representation_status": "original",
             "geometry_components": [{"exterior": [[0.8, 0], [1, 0], [1, 0.1], [0.8, 0.1]], "holes": []}],
             "representation_provenance": {"method": "synthetic"}, "_source_geometry_refs": ["mesh:wall1"],
             "adapter_refs": {"source": "synthetic"}},
            {"id": "door:interior", "represented_source_ids": ["door:interior"],
             "representation_status": "original",
             "geometry_components": [{"exterior": [[0.25, 0], [0.5, 0], [0.5, 0.25], [0.25, 0.25]],
                                      "holes": []}],
             "representation_provenance": {"method": "synthetic"}, "_source_geometry_refs": ["mesh:door"],
             "adapter_refs": {"source": "synthetic"}},
        ],
        "field_layer": {"samples": []},
        "shared_provenance": {"records": [{"provenance_ref": "selected-records", "records": []}]},
        "audit": {"unknown_source_ids": list(_runner.UNKNOWN_IDS),
                  "boundary_member_source_ids": ["door:boundary"]},
        "input_hashes": {"entries": []}, "timings": {},
    }
    (path / "inspection_manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_mass_patch_projection_preserves_two_holes() -> None:
    """The mesh substitute/projector path preserves hole interiors and area."""
    from features.geometry_substitutes import mass_patch_from_mesh
    from features.geometry_views import plan_projection

    polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                      [[(1, 1), (2, 1), (2, 2), (1, 2)],
                       [(7, 7), (8, 7), (8, 8), (7, 8)]])
    projection = plan_projection(mass_patch_from_mesh(_runner._mesh_from_polygon(polygon, "domain")),
                                 height_band=None)
    projected = Polygon(projection.components[0]["exterior"], projection.components[0]["holes"])
    assert len(projection.components[0]["holes"]) == 2
    assert projected.area == pytest.approx(polygon.area, abs=1e-6)
    assert not projected.covers(Point(1.5, 1.5))
    assert not projected.covers(Point(7.5, 7.5))


def test_reuse_build_is_synthetic_and_deterministic(tmp_path, monkeypatch) -> None:
    """Reuse runs the current field/manifest path without fixed artifacts."""
    handoff = _handoff(tmp_path)
    source = _runner.SourceObject(id="o1", source_id="o1", source_role="IfcFurniture",
                                  source_class="IfcFurniture", geometry_refs=("mesh:o1",),
                                  factual_properties={"furniture_analysis_participation": "included"},
                                  provenance={"source": "synthetic"})
    proxy = _runner.SourceObject(id="proxy:p", source_role="analysis_substitute",
                                 geometry_refs=("mesh:proxy",),
                                 factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": ["owner:p"]}},
                                 provenance={"representation_identifier": "GeneratedProxy"})
    wall = _runner.SourceObject(id="wall1", source_id="wall1", source_role="IfcWall",
                                source_class="IfcWall", geometry_refs=("mesh:wall1",),
                                provenance={"source": "synthetic"})
    interior_door = _runner.SourceObject(
        id="door:interior", source_id="door:interior", source_role="IfcDoor",
        source_class="IfcDoor", geometry_refs=("mesh:door",), provenance={"source": "synthetic"}
    )
    unknown_sources = tuple(_runner.SourceObject(
        id=sid, source_id=sid, source_role="IfcWindow", source_class="IfcWindow",
        uncertainties=(_runner.UncertaintyRecord(
            code="missing_geometry", message="global synthetic unknown", source_refs=(sid,),
            operation="test", severity="warning"),),
        provenance={"source": "synthetic"},
    ) for sid in _runner.UNKNOWN_IDS)
    fake_scene = SimpleNamespace(
        source_objects=(source, proxy, wall, interior_door, *unknown_sources),
        analysis_domain=SimpleNamespace(id="b3-selected-s3-whole-height"),
    )
    selection = {"selected_source_ids": ["o1", "wall1", "door:interior"],
                 "unknown_source_ids": list(_runner.UNKNOWN_IDS),
                 "boundary_scoped_ids": ["door:boundary"]}
    bindings = {"targets": [{"target_id": "proxy:p", "represented_source_ids": ["owner:p"],
                             "obj_ref": {"path": "proxy.obj"}}]}
    fake_capture = {"inventory": [{"id": "o1", "geometry": None}, {"id": "wall1", "geometry": None}]}
    monkeypatch.setattr(_runner.B3, "frozen_inputs",
                        lambda: (bindings, {}, [], fake_capture, {}, {}, ["door:boundary"], {}, {}))
    source_domain = Polygon(
        [(-0.25, -0.5), (0.75, -0.5), (0.75, 0.5), (-0.25, 0.5)],
        [[(-0.15, -0.4), (-0.05, -0.4), (-0.05, -0.3), (-0.15, -0.3)],
         [(0.45, 0.2), (0.55, 0.2), (0.55, 0.3), (0.45, 0.3)]],
    )
    monkeypatch.setattr(_runner.B3.PRIOR, "read_json",
                        lambda path: {"artifacts": []} if str(path).endswith("artifact_manifest.json") else selection)
    monkeypatch.setattr(_runner.B3.PRIOR, "file_ref",
                        lambda path: {"path": str(path), "bytes": 1, "sha256": "x"})
    monkeypatch.setattr(_runner, "_whole_height_scene", lambda: (
        fake_scene, {"bindings": bindings, "selection": selection, "capture": fake_capture,
                     "originals": [], "input_hashes": [],
                     "domain_polygon": source_domain}))
    manifest = json.loads((handoff / "inspection_manifest.json").read_text(encoding="utf-8"))
    manifest["input_hashes"]["entries"] = _runner._input_hash_ledger(
        bindings, fake_capture, {"artifacts": []}
    )
    (handoff / "inspection_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    first, _ = _runner.build_inspection(projected_handoff=handoff)
    second, _ = _runner.build_inspection(projected_handoff=handoff)
    assert first["origin_offset_m"] == [0.25, 0.5]
    assert first["source_origin_offset_m"] == [0.0, 0.0]
    assert first["query_scope"] == "whole_height_plan"
    assert first["source_layer"] == second["source_layer"]
    assert len(first["uncertainty_sources"]) == 5
    assert any(item["source_class"] == "IfcWall" for item in first["source_layer"])
    assert "door:boundary" not in {item["id"] for item in first["source_layer"]}
    occupied = [
        item for item in first["field_layer"]["samples"]
        if item["value"] is True and "door:interior" in item["source_ids"]
    ]
    assert occupied and all(item["status"] == "conditional" for item in occupied)
    assert all("door:boundary" not in item["source_ids"]
               for item in first["field_layer"]["samples"])


def test_recovery_and_binary_writer_are_exact(tmp_path) -> None:
    """Nested selected-record audit, support, and final bytes round-trip exactly."""
    sample = {"target": [0, 0], "value": False, "status": "established",
              "visual_state": "established", "source_ids": [],
              "support": {"target": [0, 0], "nested": {"x": 1}},
              "provenance_ref": "selected-records",
              "provenance": {"query": {"height_band": None}, "nested": {"x": 1}}}
    payload = {"field_layer": {"samples": [sample]},
               "shared_provenance": {"records": [{"provenance_ref": "selected-records",
                                                  "records": [{"id": "a"}]}]}}
    recovered = _runner.recover_cell(payload, 0)
    assert recovered["support"] == sample["support"]
    assert recovered["provenance"]["selected_records"] == [{"id": "a"}]
    sizes = _runner._write_final_artifacts(
        tmp_path, payload, "<script type='application/json' id='inspection'>{}</script>"
    )
    disk = json.loads((tmp_path / "inspection_manifest.json").read_text())
    embedded = json.loads(re.search(r">(.*?)</script>", (tmp_path / "inspection.html").read_text(),
                                    re.S).group(1).replace("<\\/", "</"))
    assert embedded == disk
    assert sizes == {"json_bytes": (tmp_path / "inspection_manifest.json").stat().st_size,
                     "html_bytes": (tmp_path / "inspection.html").stat().st_size}


def test_field_manifest_recovery_matches_every_field_record() -> None:
    """Current Field -> manifest -> recovery preserves every semantic field."""
    from features.free_space_field import FreeSpaceField
    from features.field_core import FieldQuery
    from features.space_field_visualization import build_field_layer_manifest

    field = FreeSpaceField(
        domain={"id": "d", "frame": "world_xy",
                "components": [{"exterior": [(0, 0), (1, 0), (1, 1), (0, 1)], "holes": []}]},
        origin=(0, 0), spacing=0.25, n_rows=2, n_cols=2,
        physical_occupancy=[{"id": "mass", "representation_status": "original",
                             "represented_source_ids": ["mass"],
                             "geometry_components": [{"exterior": [(0, 0), (0.2, 0), (0.2, 0.2), (0, 0.2)], "holes": []}]}],
        unresolved_source_ids=[],
        query_context={"domain_id": "d", "frame": "world_xy", "plane": None,
                       "height_band": None, "demand": None,
                       "geometry_query": "whole_height_planar_mass_patch"},
        frame="world_xy", origin_offset=(0, 0),
    )
    query = FieldQuery(domain_id="d", frame="world_xy")
    manifest = build_field_layer_manifest(
        layer_id="x", channel="x",
        samples=field.evaluate_many(((r, c) for r in range(2) for c in range(2)), query),
    )
    selected = _runner._jsonable(field.provenance["selected_records"])
    cells = []
    for record in manifest["samples"]:
        provenance = dict(record["provenance"])
        support = provenance.pop("support", None)
        cells.append({**record, "support": support, "provenance_ref": "selected-records",
                      "provenance": provenance})
    payload = {"field_layer": {"samples": cells},
               "shared_provenance": {"records": [{"provenance_ref": "selected-records",
                                                  "records": selected}]}}
    for index, original in enumerate(manifest["samples"]):
        expected = dict(original)
        recovered = _runner.recover_cell(payload, index)
        assert recovered == expected


def test_small_field_fixture_covers_unknown_and_duplicate_owner() -> None:
    """The semantic field reports global unknown and invalid duplicate ownership."""
    from features.free_space_field import FreeSpaceField
    from features.field_core import FieldQuery

    common = dict(
        domain={"id": "d", "frame": "world_xy", "components": [{
            "exterior": [(0, 0), (1, 0), (1, 1), (0, 1)], "holes": []}]},
        origin=(0.0, 0.0), spacing=0.25, n_rows=1, n_cols=1,
        query_context={"domain_id": "d", "frame": "world_xy", "plane": None,
                       "height_band": None, "demand": None,
                       "geometry_query": "whole_height_planar_mass_patch"},
        frame="world_xy", origin_offset=(0.0, 0.0))
    unknown = FreeSpaceField(physical_occupancy=[], unresolved_source_ids=["u"], **common)
    assert unknown.evaluate((0, 0), FieldQuery(domain_id="d", frame="world_xy")).status.value == "unknown"
    duplicate = FreeSpaceField(physical_occupancy=[
        {"id": "a", "representation_status": "original", "represented_source_ids": ["o"],
         "geometry_components": [{"exterior": [(0,0),(1,0),(1,1),(0,1)], "holes": []}]},
        {"id": "b", "representation_status": "original", "represented_source_ids": ["o"],
         "geometry_components": [{"exterior": [(0,0),(1,0),(1,1),(0,1)], "holes": []}]},
    ], unresolved_source_ids=[], **common)
    assert duplicate.evaluate((0, 0), FieldQuery(domain_id="d", frame="world_xy")).status.value == "invalid"


def test_input_ledger_uses_root_resolvable_paths(monkeypatch) -> None:
    """Ledger references carry complete ROOT-relative paths and real hashes."""
    bindings = {"targets": [{"target_id": "proxy:p", "represented_source_ids": [],
                             "obj_ref": {"path": "outputs/proxy.obj"}}]}
    capture = {"inventory": [{"id": "o1", "geometry": {
        "path": "meshes/o1.json", "bytes": 4, "sha256": "mesh-hash"}}]}
    monkeypatch.setattr(_runner.B3.PRIOR, "file_ref",
                        lambda path: {"path": str(path), "bytes": 7, "sha256": "actual"})
    entries = _runner._input_hash_ledger(bindings, capture, {"artifacts": []})
    mesh = next(item for item in entries if item["kind"] == "captured_mesh")
    assert mesh["path"].replace("\\", "/").endswith(
        "b3_real_source_field/run_001/meshes/o1.json"
    )
    assert mesh["bytes"] == 4 and mesh["sha256"] == "mesh-hash"


def test_reuse_guards_refuse_bad_domain_and_hash(tmp_path, monkeypatch) -> None:
    """Reuse guards reject missing explicit domain and stale consumed hashes."""
    handoff = _handoff(tmp_path)
    source = _runner.SourceObject(id="o1", source_id="o1", source_role="IfcFurniture",
                                  source_class="IfcFurniture", geometry_refs=("mesh:o1",),
                                  provenance={"source": "synthetic"})
    proxy = _runner.SourceObject(id="proxy:p", source_role="analysis_substitute",
                                 geometry_refs=("mesh:proxy",),
                                 factual_properties={"OM_PhysicalOccupancy": {"represented_source_ids": ["owner:p"]}},
                                 provenance={"representation_identifier": "GeneratedProxy"})
    fake_scene = SimpleNamespace(
        source_objects=(source, proxy),
        analysis_domain=SimpleNamespace(id="b3-selected-s3-whole-height"),
    )
    selection = {"selected_source_ids": ["o1", "wall1", "door:interior"],
                 "unknown_source_ids": list(_runner.UNKNOWN_IDS),
                 "boundary_scoped_ids": ["door:boundary"]}
    bindings = {"targets": [{"target_id": "proxy:p", "represented_source_ids": ["owner:p"],
                             "obj_ref": {"path": "proxy.obj"}}]}
    monkeypatch.setattr(_runner.B3, "frozen_inputs",
                        lambda: (bindings, {}, [], {"inventory": [{"id": "o1", "geometry": None}]},
                                 {}, {}, ["door:boundary"], {}, {}))
    monkeypatch.setattr(
        _runner,
        "_whole_height_scene",
        lambda: (fake_scene, {"domain_polygon": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])}),
    )
    monkeypatch.setattr(_runner.B3.PRIOR, "read_json",
                        lambda path: {"artifacts": []} if str(path).endswith("artifact_manifest.json") else selection)
    monkeypatch.setattr(_runner.B3.PRIOR, "file_ref",
                        lambda path: {"path": str(path), "bytes": 1, "sha256": "x"})
    original = json.loads((handoff / "inspection_manifest.json").read_text())
    broken = json.loads(json.dumps(original))
    broken["domain"]["components"] = []
    (handoff / "inspection_manifest.json").write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="contract_mismatch"):
        _runner.build_inspection(projected_handoff=handoff)
    original["input_hashes"]["entries"] = _runner._input_hash_ledger(
        bindings, {"inventory": [{"id": "o1", "geometry": None}]}, {"artifacts": []}
    )
    (handoff / "inspection_manifest.json").write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="domain_geometry_mismatch"):
        _runner.build_inspection(projected_handoff=handoff)


def test_whole_height_scene_refuses_tampered_artifact(tmp_path, monkeypatch) -> None:
    """Authenticated package artifacts are rejected when their bytes or hash drift."""
    handle = tempfile.NamedTemporaryFile(
        dir=_runner.ROOT, prefix=".tmp-fingerprint-", suffix=".json", delete=False
    )
    actual_path = Path(handle.name)
    handle.write(b"original")
    handle.close()
    relative = actual_path.relative_to(_runner.ROOT)
    expected_ref = _runner.B3.PRIOR.file_ref(actual_path)
    actual_path.write_bytes(b"tampered")
    artifact_manifest = {
        "schema": "b3-primary-eye-artifacts/v1",
        "status": "exit_0",
        "artifacts": [{
            "path": str(relative).replace("\\", "/"),
            "bytes": expected_ref["bytes"],
            "sha256": expected_ref["sha256"],
        }],
    }
    monkeypatch.setattr(
        _runner.B3,
        "frozen_inputs",
        lambda: ({}, {}, [], {"inventory": []}, {}, {}, [], {}, {}),
    )
    monkeypatch.setattr(
        _runner.B3.PRIOR,
        "read_json",
        lambda path: artifact_manifest
        if str(path).endswith("artifact_manifest.json")
        else {"unknown_source_ids": list(_runner.UNKNOWN_IDS), "boundary_scoped_ids": ["live-step-6231"]},
    )
    try:
        with pytest.raises(ValueError, match="inspection_artifact_fingerprint_mismatch"):
            _runner._whole_height_scene()
    finally:
        actual_path.unlink(missing_ok=True)
