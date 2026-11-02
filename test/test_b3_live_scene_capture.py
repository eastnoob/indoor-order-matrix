"""Check live capture boundaries without reading or changing the user's scene."""

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest


PATH = Path(__file__).parents[1] / "scripts/design/space_field/capture_b3_live_scene.py"
SPEC = importlib.util.spec_from_file_location("b3_live_capture_test", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Matrix:
    """Provide the native matrix operations needed by the capture seam."""

    def __init__(self, values):
        """Keep an affine matrix independent of source and evaluated objects."""
        self.values = np.array(values, dtype=float)

    def __matmul__(self, vertex):
        """Apply translation, scale and rotation to one local vertex."""
        return (self.values @ np.array([*vertex, 1]))[:3]

    def __iter__(self):
        """Expose matrix rows as Blender does for provenance serialization."""
        return iter(self.values)

    def copy(self):
        """Freeze evaluated transform values for this extraction."""
        return Matrix(self.values.copy())

    def to_3x3(self):
        """Expose the linear part for singular-transform rejection."""
        return Matrix(self.values[:3, :3])

    def determinant(self):
        """Compute the linear determinant without faking transform validity."""
        return float(np.linalg.det(self.values))


class EvaluatedObject:
    """Track temporary mesh allocation and cleanup through failures."""

    def __init__(self, *, failure=None, matrix=None):
        """Build a small asymmetric mesh with a distinct evaluated transform."""
        self.failure, self.cleared = failure, 0
        self.matrix_world = Matrix(matrix if matrix is not None else
                                   [[0, -2, 0, 3], [1, 0, 0, 4], [0, 0, 3, 5], [0, 0, 0, 1]])
        self.mesh = SimpleNamespace(vertices=[SimpleNamespace(co=point) for point in
                                              [(1, 0, 0), (0, 1, 0), (0, 0, 1)]],
                                    loop_triangles=[SimpleNamespace(vertices=(0, 1, 2))],
                                    polygons=[object()], calc_loop_triangles=self.triangulate)

    def triangulate(self):
        """Simulate a native triangulation failure after mesh allocation."""
        if self.failure == "triangulate":
            raise RuntimeError("triangulation failed")

    def to_mesh(self):
        """Simulate allocation errors as well as a successful temporary mesh."""
        if self.failure == "allocate":
            raise RuntimeError("allocation failed")
        return self.mesh

    def to_mesh_clear(self):
        """Count releases without touching source geometry."""
        self.cleared += 1


def source_row():
    """Provide the factual metadata required by the extraction seam."""
    return {"id": "live-step-1", "step_id": 1, "global_id": "guid-1",
            "properties": {"SourceLengthUnit": "MILLIMETRE"},
            "loaded_representation": {"step_id": 10, "identifier": "Body"},
            "declared_representations": [{"step_id": 10, "identifier": "Body", "type": "Tessellation"}]}


def object_for(evaluated):
    """Expose evaluated geometry while giving the original a different matrix."""
    def evaluated_get(depsgraph):
        """Return the native evaluation stand-in for the requested graph."""
        assert depsgraph == "graph"
        return evaluated
    return SimpleNamespace(name="source", evaluated_get=evaluated_get,
                           matrix_world=Matrix(np.eye(4) * 99))


def unknown_quality(mesh):
    """Represent an unqualified mesh without borrowing frozen topology flags."""
    return {"is_closed": None, "is_manifold": None, "solid_query_eligible": None}


def test_exec_loading_needs_no_file_and_performs_no_native_import():
    """The owner can exec into a persistent module without starting capture."""
    namespace = {"__name__": "owner_capture"}
    exec(compile(PATH.read_text(encoding="utf-8"), str(PATH), "exec"), namespace)
    assert "__file__" not in namespace and namespace["_CAPTURE"] is None
    assert callable(namespace["begin_capture"]) and callable(namespace["capture_next_batch"])


@pytest.mark.parametrize("scale", [1.0, 0.01])
def test_evaluated_transform_once_then_blender_units_not_ifc_units(monkeypatch, scale):
    """Evaluated translation and rotation are neither skipped nor applied twice."""
    evaluated = EvaluatedObject()
    monkeypatch.setattr(MODULE, "topology_quality", unknown_quality)
    snapshot = MODULE.extract_mesh(object_for(evaluated), "graph", scale, source_row())
    assert np.allclose(snapshot["vertices"], np.array([[3, 5, 5], [1, 4, 5], [3, 4, 8]]) * scale)
    assert snapshot["units"] == "m" and snapshot["transform_applied"] is True
    assert snapshot["is_closed"] is None and snapshot["world_transform"] == evaluated.matrix_world.values.tolist()
    assert snapshot["representation_id"] == "10" and evaluated.cleared == 1


@pytest.mark.parametrize("failure", ["allocate", "triangulate", "nonfinite", "invalid_indices", "singular"])
def test_mesh_release_on_every_extraction_failure(monkeypatch, failure):
    """All failures release temporary meshes and refuse fabricated geometry."""
    evaluated = EvaluatedObject(failure=failure)
    if failure == "nonfinite":
        evaluated.mesh.vertices[0].co = (float("nan"), 0, 0)
    if failure == "invalid_indices":
        evaluated.mesh.loop_triangles[0].vertices = (0, 1, 3)
    if failure == "singular":
        evaluated.matrix_world = Matrix(np.zeros((4, 4)))
    monkeypatch.setattr(MODULE, "topology_quality", unknown_quality)
    with pytest.raises((ValueError, RuntimeError)):
        MODULE.extract_mesh(object_for(evaluated), "graph", 1.0, source_row())
    assert evaluated.cleared == 1


def test_topology_error_retains_fresh_mesh_with_null_flags(monkeypatch):
    """A quality-check failure remains visible without discarding geometry."""
    def fail_quality(mesh):
        """Simulate a failed native topology inspection."""
        raise RuntimeError("quality unavailable")
    monkeypatch.setattr(MODULE, "topology_quality", fail_quality)
    evaluated = EvaluatedObject()
    snapshot = MODULE.extract_mesh(object_for(evaluated), "graph", 1.0, source_row())
    assert snapshot["vertices"] and snapshot["is_closed"] is None and snapshot["is_manifold"] is None
    assert snapshot["quality"]["solid_query_eligible"] is None
    assert "quality unavailable" in snapshot["quality"]["error"] and evaluated.cleared == 1


def test_enrollment_requires_unique_step_and_guid_preserves_extras_and_missing():
    """Reused STEP ids, duplicated links and out-of-scene objects cannot enroll."""
    expected = [{"id": f"original-{step}", "step_id": step, "global_id": f"g-{step}"} for step in range(1, 8)]
    pairs = [(1, "g-1"), (2, "wrong"), (3, "g-3"), (3, "g-3"),
             (4, "g-4"), (99, "g-4"), (50, "extra"), (60, "g-7"), (6, "g-6")]
    live = [{"step_id": step, "global_id": guid, "blender_name": f"object-{index}",
             "in_scene": step != 6} for index, (step, guid) in enumerate(pairs)]
    records, diagnostics = MODULE.match_inventory(expected, live)
    assert [row["status"] for row in records] == ["pending", "identity_mismatch", "duplicate_identity",
                                                 "duplicate_identity", "missing_identity", "missing_identity", "identity_mismatch"]
    assert all(row["geometry"] is None and row["is_closed"] is None for row in records)
    assert diagnostics["duplicates"]["step_id"]["3"] == ["object-2", "object-3"]
    assert diagnostics["duplicates"]["global_id"]["g-4"] == ["object-4", "object-5"]
    assert len(diagnostics["extras"]) == 5 and diagnostics["missing_identities"] == ["original-5", "original-6"]


def batch_session(tmp_path):
    """Create a two-source session whose real per-source capture will fail."""
    def failed_entity(step):
        """Model a source lookup error that must survive in the inventory."""
        raise RuntimeError("entity unavailable")
    def graph():
        """Supply a graph token without using any Blender scene."""
        return "graph"
    model = SimpleNamespace(by_id=failed_entity)
    def get_file():
        """Keep the same model identity between batches."""
        return model
    return {"out": tmp_path, "records": [{"id": str(step), "step_id": step, "global_id": str(step),
                                           "status": "pending", "geometry": None} for step in (1, 2)],
            "manifest": {"status": "in_progress", "state_before": {"unchanged": True}, "batches": [],
                         "capture_errors": [], "frozen_identity_source": {}, "historical_scope": {}},
            "model": model, "store": SimpleNamespace(get_file=get_file), "tool": None,
            "bpy": SimpleNamespace(context=SimpleNamespace(evaluated_depsgraph_get=graph)),
            "diagnostics": {}, "started_clock": MODULE.time.perf_counter()}


def test_batches_checkpoint_failures_finalize_and_return_no_arrays(tmp_path, monkeypatch):
    """An object failure consumes only its batch slot and leaves an audited run."""
    def unchanged(*args):
        """Keep source invariants steady across both small batches."""
        return {"unchanged": True}
    session = batch_session(tmp_path)
    monkeypatch.setattr(MODULE, "_CAPTURE", session)
    monkeypatch.setattr(MODULE, "scene_state", unchanged)
    first = MODULE.capture_next_batch(max_objects=1)
    assert first["remaining"] == 1 and first["done"] is False
    inventory = json.loads((tmp_path / "scope_inventory.json").read_text())
    assert inventory["records"][0]["status"] == "invalid_extraction"
    assert inventory["records"][0]["geometry"] is None and "entity unavailable" in inventory["records"][0]["error"]
    second = MODULE.capture_next_batch(max_objects=1)
    assert second["done"] and second["status"] == "complete_with_failures"
    manifest = json.loads((tmp_path / "capture_manifest.json").read_text())
    assert manifest["scene_preserved"] and manifest["ended_utc"] and len(manifest["batches"]) == 2
    assert MODULE.capture_next_batch(1) == second and "vertices" not in json.dumps(second)


def test_scene_change_aborts_before_capture_and_retains_pending(tmp_path, monkeypatch):
    """Changing source state stops enrollment without attempting source reads."""
    def changed(*args):
        """Represent an observed source matrix or selection change."""
        return {"unchanged": False}
    session = batch_session(tmp_path)
    monkeypatch.setattr(MODULE, "_CAPTURE", session)
    monkeypatch.setattr(MODULE, "scene_state", changed)
    result = MODULE.capture_next_batch(1)
    assert result["done"] and result["status"] == "aborted_scene_changed" and result["remaining"] == 2
    manifest = json.loads((tmp_path / "capture_manifest.json").read_text())
    assert manifest["state_after"] == {"unchanged": False} and manifest["scene_preserved"] is False
    assert manifest["batches"][0]["ids"] == [] and manifest["capture_errors"]


@pytest.mark.parametrize("size", [0, -1, True, 1.5])
def test_invalid_batch_limit_rejected(size):
    """Reject malformed batch requests before any native or filesystem access."""
    with pytest.raises(ValueError, match="positive integer"):
        MODULE.capture_next_batch(size)


def begin_fixture(tmp_path, monkeypatch):
    """Isolate capture bootstrap while using real identity and output logic."""
    import ifcopenshell.util.unit

    source, frozen = tmp_path / "source.ifc", tmp_path / "scope_inventory.json"
    source.write_text("disposable source identity only", encoding="utf-8")
    expected = [{"id": f"original-{step}", "step_id": step, "global_id": f"guid-{step}",
                 "geometry": {"path": "forbidden-frozen-mesh"}, "is_closed": True,
                 "category": "forbidden-frozen-category"} for step in range(1, 359)]
    frozen.write_text(json.dumps({"records": expected, "scope": {"path": "historical-s3"}}), encoding="utf-8")
    project = SimpleNamespace(GlobalId="project", UnitsInContext=SimpleNamespace(Units=[
        SimpleNamespace(UnitType="LENGTHUNIT", Name="METRE", Prefix="MILLI")]))
    def by_type(kind):
        """Return the factual IFC unit assignment without native geometry."""
        assert kind == "IfcProject"
        return [project]
    model = SimpleNamespace(schema="IFC4", by_type=by_type)
    def get_file():
        """Provide one stable in-memory IFC model for bootstrap."""
        return model
    store = SimpleNamespace(path=str(source), get_file=get_file)
    bpy = ModuleType("bpy")
    bpy.app = SimpleNamespace(binary_path=str(MODULE.BINARY), version_string="fixture")
    bpy.context = SimpleNamespace(mode="OBJECT", scene=SimpleNamespace(
        unit_settings=SimpleNamespace(system="METRIC", scale_length=1.0)))
    bonsai, tool, bim, ifc = [ModuleType(name) for name in ("bonsai", "bonsai.tool", "bonsai.bim", "bonsai.bim.ifc")]
    bonsai.tool, bonsai.bim, bim.ifc, ifc.IfcStore = tool, bim, ifc, store
    for name, module in [("bpy", bpy), ("bonsai", bonsai), ("bonsai.tool", tool),
                         ("bonsai.bim", bim), ("bonsai.bim.ifc", ifc)]:
        monkeypatch.setitem(sys.modules, name, module)
    def source_scale(model):
        """Keep authored millimetres distinct from live Blender metres."""
        return 0.001
    def state(*args):
        """Supply inexpensive disk and scene facts for bootstrap."""
        return {"source_ifc_bytes": source.stat().st_size, "unchanged": True}
    def inventory(*args):
        """Match all 358 identities while retaining one non-enrolled extra."""
        return [{"step_id": row["step_id"], "global_id": row["global_id"],
                 "blender_name": row["id"], "type": "MESH", "in_scene": True} for row in expected] + [
            {"step_id": 1000, "global_id": "extra", "blender_name": "extra", "type": "MESH", "in_scene": True}]
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    monkeypatch.setattr(MODULE, "SOURCE", source)
    monkeypatch.setattr(MODULE, "FROZEN", frozen)
    monkeypatch.setattr(MODULE, "_CAPTURE", None)
    monkeypatch.setattr(MODULE, "scene_state", state)
    monkeypatch.setattr(MODULE, "live_inventory", inventory)
    monkeypatch.setattr(ifcopenshell.util.unit, "calculate_unit_scale", source_scale)
    return bpy, store, model, expected


def test_begin_unique_directory_full_scope_and_no_frozen_geometry(tmp_path, monkeypatch):
    """Bootstrap preserves exactly the identity list and no historical quality."""
    begin_fixture(tmp_path, monkeypatch)
    result = MODULE.begin_capture()
    directory = Path(result["directory"])
    manifest = json.loads((directory / "capture_manifest.json").read_text())
    inventory = json.loads((directory / "scope_inventory.json").read_text())
    assert result["remaining"] == 358 and len(inventory["records"]) == 358
    assert manifest["live_counts"] == {"MESH": 359} and len(manifest["extras"]) == 1
    assert manifest["source_to_m"] == 0.001 and manifest["blender_world_to_m"] == 1
    assert manifest["source_ifc_sha256"] is None and manifest["historical_scope"]["current_reconfirmation"] is False
    assert not list((directory / "meshes").iterdir()) and "forbidden-frozen" not in json.dumps(inventory)
    assert all(row["geometry"] is None and row["is_closed"] is None for row in inventory["records"])
    with pytest.raises(RuntimeError, match="already active"):
        MODULE.begin_capture()
    MODULE._CAPTURE["manifest"]["status"] = "complete"
    assert MODULE.begin_capture()["directory"] != str(directory)


@pytest.mark.parametrize("invalid", ["binary", "ifc_path", "schema", "mode", "units", "count", "duplicate_guid"])
def test_begin_rejects_invalid_session_before_output(tmp_path, monkeypatch, invalid):
    """Unauthorized sessions and ambiguous frozen enrollment cannot start a run."""
    bpy, store, model, expected = begin_fixture(tmp_path, monkeypatch)
    if invalid == "binary":
        bpy.app.binary_path = str(tmp_path / "other-blender.exe")
    elif invalid == "ifc_path":
        store.path = str(tmp_path / "other.ifc")
    elif invalid == "schema":
        model.schema = "IFC2X3"
    elif invalid == "mode":
        bpy.context.mode = "EDIT_MESH"
    elif invalid == "units":
        bpy.context.scene.unit_settings.scale_length = 0
    else:
        if invalid == "count":
            expected.pop()
        else:
            expected[1]["global_id"] = expected[0]["global_id"]
        MODULE.FROZEN.write_text(json.dumps({"records": expected, "scope": {}}), encoding="utf-8")
    with pytest.raises(ValueError):
        MODULE.begin_capture()
    assert not (tmp_path / "outputs").exists()

