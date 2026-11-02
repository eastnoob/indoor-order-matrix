"""Canonical capture lifecycle checks using explicit synthetic native boundaries."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import json
import sys

import pytest

from ..adapters import blender_analysis_capture as capture
from .test_b3_live_scene_capture import EvaluatedObject, object_for, unknown_quality


def runtime(monkeypatch):
    """Provide two IFC products, one hidden linked mesh and one missing mesh."""
    class Entity:
        """Expose authoritative GUID, STEP and class facts only."""
        def __init__(self, step, guid, cls):
            """Store explicit canonical identity facts."""
            self.step, self.GlobalId, self.cls = step, guid, cls
        def id(self):
            """Return this entity's STEP identity."""
            return self.step
        def is_a(self):
            """Return the verified native IFC class."""
            return self.cls
    entities = [Entity(1, "wall-guid", "IfcWall"), Entity(2, "missing-guid", "IfcFurniture")]
    project = Entity(99, "project-guid", "IfcProject")
    def by_type(cls):
        """Return the complete inventory independently of Blender visibility."""
        return [project] if cls == "IfcProject" else entities
    def by_guid(guid):
        """Resolve a current entity by its authoritative GUID."""
        return next(entity for entity in entities if entity.GlobalId == guid)
    model = SimpleNamespace(by_type=by_type, by_guid=by_guid, schema="IFC4")
    evaluated = EvaluatedObject()
    obj = object_for(evaluated)
    obj.type, obj.name, obj.parent, obj.modifiers, obj.material_slots = "MESH", "hidden-wall", None, [], []
    obj.data = SimpleNamespace(name="source-mesh")
    obj.hide_viewport = True
    scene = SimpleNamespace(objects=[obj], name="scene", frame_current=12, frame_subframe=.5,
                            unit_settings=SimpleNamespace(scale_length=.01))
    def graph():
        """Return the selected evaluated dependency graph."""
        return "graph"
    context = SimpleNamespace(scene=scene, mode="OBJECT", evaluated_depsgraph_get=graph)
    def get_entity(item):
        """Bind the hidden object to its unique native entity."""
        assert item is obj
        return entities[0]
    tool = SimpleNamespace(Ifc=SimpleNamespace(get_entity=get_entity, get_object=lambda entity: obj if entity is entities[0] else None))
    store = SimpleNamespace(get_file=lambda: model, path="fixture.ifc")
    monkeypatch.setitem(sys.modules, "bpy", SimpleNamespace(app=SimpleNamespace(binary_path=str(capture.BINARY)), data=SimpleNamespace(filepath="fixture.blend")))
    monkeypatch.setitem(sys.modules, "bonsai.tool", tool)
    monkeypatch.setitem(sys.modules, "bonsai.bim.ifc", SimpleNamespace(IfcStore=store))
    import ifcopenshell.util.element
    monkeypatch.setattr(ifcopenshell.util.element, "get_psets", lambda *args, **kwargs: {"Fact": {"value": 1}})
    monkeypatch.setattr(capture, "topology_quality", unknown_quality)
    return context, entities, evaluated


def test_native_capture_requires_main_thread_before_import():
    """A worker cannot touch bpy even when all arguments are otherwise invalid."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(capture.begin_analysis_capture, bpy_context=None, scene_token="worker")
        with pytest.raises(RuntimeError, match="main thread"):
            future.result()


def test_full_inventory_batches_missing_hidden_and_frozen_facts(monkeypatch):
    """A missing object remains unresolved, and a hidden mesh retains evaluated facts."""
    context, entities, evaluated = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene-token", batch_size=1)
    first = capture.capture_next_batch(job)
    assert first.processed == 1 and first.total == 2 and not first.complete
    assert first.callback_seconds >= first.max_object_seconds >= 0
    final = capture.capture_next_batch(job)
    result = capture.finalize_capture(job)
    assert final.complete and not final.cancelled
    assert result.capture_complete and result.capture_id == job.capture_id
    assert result.session_token == "scene-token" and result.frame == (12, .5)
    assert len(result.source_inventory) == 2 and len(result.geometry_records) == 1
    assert len(result.unresolved_records) == 1
    assert result.records[1]["global_id"] == "wall-guid"
    assert evaluated.cleared == 1
    assert result.records[1]["mesh"]["vertices"][0] == pytest.approx([.03, .05, .05])
    assert result.observation_token
    with pytest.raises(TypeError):
        result.observation["frame"] = 0
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError, match="main thread"):
            pool.submit(capture.capture_next_batch, job).result()


def test_cancel_and_frame_drift_cannot_publish(monkeypatch):
    """Partial or mixed-frame extraction never becomes a complete canonical input."""
    context, _, _ = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene-token", batch_size=1)
    capture.capture_next_batch(job)
    context.scene.frame_current += 1
    with pytest.raises(ValueError, match="changed"):
        capture.capture_next_batch(job)
    with pytest.raises(ValueError, match="incomplete"):
        capture.finalize_capture(job)
    capture.cancel_capture(job, reason="scene changed")
    assert capture.capture_next_batch(job).cancelled
    with pytest.raises(ValueError, match="incomplete"):
        capture.finalize_capture(job)


@pytest.mark.parametrize("failure", ["allocate", "triangulate", "singular"])
def test_canonical_extraction_always_releases(failure):
    """Moving extraction into the adapter preserves its failure cleanup boundary."""
    evaluated = EvaluatedObject(failure=failure)
    if failure == "singular":
        from .test_b3_live_scene_capture import Matrix
        evaluated.matrix_world = Matrix([[0]*4]*4)
    with pytest.raises((ValueError, RuntimeError)):
        capture.extract_evaluated_mesh(object_for(evaluated), "graph", .01, quality_reader=unknown_quality)
    assert evaluated.cleared == 1


def test_native_triangle_order_is_preserved_without_retessellation():
    """Historical indexed geometry parity requires native face ordering and winding."""
    evaluated = EvaluatedObject()
    evaluated.mesh.loop_triangles = [SimpleNamespace(vertices=(2, 0, 1)), SimpleNamespace(vertices=(1, 0, 2))]
    result = capture.extract_evaluated_mesh(object_for(evaluated), "graph", 1, quality_reader=unknown_quality)
    assert result["triangles"] == [[2, 0, 1], [1, 0, 2]]


def test_native_capture_skips_owned_display_geometry(monkeypatch):
    """Linked display cameras/previews cannot add occupancy or change source digests."""
    context, _, evaluated = runtime(monkeypatch)
    obj = context.scene.objects[0]
    tags = {"om_analysis_owner": "order_analyzer", "om_analysis_role": "display_camera"}
    obj.get = tags.get
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene", batch_size=5)
    capture.capture_next_batch(job)
    result = capture.finalize_capture(job)
    row = next(row for row in result.records if row["global_id"] == "wall-guid")
    assert row["status"] == "display_only"
    assert row["display_ownership"]["om_analysis_role"] == "display_camera"
    assert evaluated.cleared == 0 and row["mesh"] is None


@pytest.mark.parametrize("direction", ["object_to_entity", "entity_to_object"])
def test_finalization_rechecks_captured_bonsai_binding(monkeypatch, direction):
    """A relink after extraction cannot publish geometry under an earlier source identity."""
    context, entities, _ = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene", batch_size=5)
    capture.capture_next_batch(job)
    if direction == "object_to_entity":
        job.tool.Ifc.get_entity = lambda obj: entities[1]
    else:
        job.tool.Ifc.get_object = lambda entity: object()
    with pytest.raises(ValueError, match="binding.*changed"):
        capture.finalize_capture(job)


def test_capture_does_not_choose_the_last_of_conflicting_space_storeys(monkeypatch):
    """Conflicting native relations remain ambiguous even when a Blender mesh is valid."""
    context, entities, _evaluated = runtime(monkeypatch)
    space = entities[0]
    space.cls = "IfcSpace"
    space.Decomposes = tuple(SimpleNamespace(RelatingObject=SimpleNamespace(
        GlobalId=guid, is_a=lambda: "IfcBuildingStorey")) for guid in ("storey-A", "storey-B"))
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene")
    capture.capture_next_batch(job)
    record = next(row for row in job.records if row["global_id"] == space.GlobalId)
    assert record["level_ref"] is None
    assert set(record["container_refs"]) == {"ifc-object:storey-A", "ifc-object:storey-B"}


def test_capture_requires_the_native_reverse_object_link(monkeypatch):
    """A one-way copied source identifier cannot qualify evaluated geometry."""
    context, entities, _evaluated = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene")
    job.tool.Ifc.get_object = lambda entity: object()
    capture.capture_next_batch(job)
    record = next(row for row in job.records if row["global_id"] == entities[0].GlobalId)
    assert record["status"] == "invalid_extraction" and record["mesh"] is None


def test_native_opening_subtype_capture_retains_relationships(monkeypatch):
    """Native capture cannot drop inherited IfcOpeningElement relation facts."""
    context, entities, _ = runtime(monkeypatch)
    entities[0].cls = "IfcOpeningStandardCase"
    entities[0].VoidsElements = [SimpleNamespace(RelatingBuildingElement=entities[1])]
    entities[0].HasFillings = [SimpleNamespace(RelatedBuildingElement=entities[1])]
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene", batch_size=5)
    capture.capture_next_batch(job)
    result = capture.finalize_capture(job)
    row = next(row for row in result.records if row["global_id"] == "wall-guid")
    assert row["opening_facts"]["host_source_ids"] == ("missing-guid",)
    assert row["opening_facts"]["filling_source_ids"] == ("missing-guid",)


def _consume_steps(steps):
    """Return a cooperative operation's value and number of suspension points."""
    count = 0
    while True:
        try:
            next(steps)
            count += 1
        except StopIteration as done:
            return done.value, count


@pytest.mark.parametrize("value", [
    {"text": "\u00e9", "values": [None, True, 1, -0.0, 1e-200]},
    {2: 7, 1: 4}, {1.5: "float key"}, {None: "null key"},
    {"bad": float("nan")}, {"bad": float("inf")}, {"bad": object()},
    {1: "integer", "mixed": "string"}, {(1, 2): "bad key"},
    {"huge": 10 ** 5000},
])
def test_capture_validation_matches_previous_json_boundary(value):
    """Removing discarded SHA work must preserve prior JSON acceptance and frozen facts."""
    try:
        expected = json.dumps(capture.plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError):
        with pytest.raises((ValueError, TypeError)):
            capture.CanonicalCaptureInput({}, (value,), (), {})
        with pytest.raises((ValueError, TypeError)):
            _consume_steps(capture.freeze_steps(value))
    else:
        result = capture.CanonicalCaptureInput({}, (value,), (), {})
        assert json.dumps(capture.plain(result.records[0]), sort_keys=True,
                          separators=(",", ":"), allow_nan=False) == expected
        frozen, _ = _consume_steps(capture.freeze_steps(value))
        assert json.dumps(capture.plain(frozen), sort_keys=True,
                          separators=(",", ":"), allow_nan=False) == expected


def test_cooperative_finalize_yields_inside_one_mesh_and_detaches(monkeypatch):
    """One mesh must suspend repeatedly and retain the synchronous immutable contract."""
    context, _, _ = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene")
    capture.capture_next_batch(job)
    mesh = next(row["mesh"] for row in job.records if row["mesh"] is not None)
    mesh["vertices"] = [[float(i), -0.0, 1e-100] for i in range(8000)]
    expected = capture.finalize_capture(job).to_dict()
    result, yields = _consume_steps(capture.finalize_capture_steps(job))
    assert yields > 10
    assert result.to_dict() == expected
    assert capture.digest(result.to_dict()) == capture.digest(expected)
    mesh["vertices"][0][0] = 999
    assert result.geometry_records[0]["vertices"][0][0] == 0
    with pytest.raises(TypeError):
        result.records[0]["global_id"] = "mutated"
    mutable = result.to_dict()
    mutable["records"].clear()
    assert len(result.records) == 2


@pytest.mark.parametrize("change", ["cancel", "frame", "binding", "inventory"])
def test_cooperative_finalize_rechecks_after_suspension(monkeypatch, change):
    """An edit during freezing cannot escape the final native identity checks."""
    context, entities, _ = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene")
    capture.capture_next_batch(job)
    mesh = next(row["mesh"] for row in job.records if row["mesh"] is not None)
    mesh["vertices"] = [[1., 2., 3.] for _ in range(3000)]
    steps = capture.finalize_capture_steps(job)
    for _ in range(6):
        next(steps)
    if change == "cancel":
        capture.cancel_capture(job, reason="cancel during freeze")
    elif change == "frame":
        context.scene.frame_current += 1
    elif change == "binding":
        job.tool.Ifc.get_entity = lambda obj: entities[1]
    else:
        entities.pop()
    with pytest.raises(ValueError):
        _consume_steps(steps)


def test_cooperative_finalize_rejects_worker_resume(monkeypatch):
    """Moving an existing generator to a worker must fail before further native access."""
    context, _, _ = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene")
    capture.capture_next_batch(job)
    next(row for row in job.records if row["mesh"] is not None)["mesh"]["vertices"] = [
        [float(i), 0.0, 0.0] for i in range(5000)]
    steps = capture.finalize_capture_steps(job)
    next(steps)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError, match="main thread"):
            pool.submit(next, steps).result()


@pytest.mark.parametrize("operation", [capture.freeze_steps, capture.plain_steps])
def test_large_array_first_yield_precedes_full_traversal(operation):
    """A cosmetic yield after a complete array walk must fail this bounded-read check."""
    class ObservedList(list):
        """Count elements consumed without changing native list values."""
        reads = 0

        def __iter__(self):
            """Expose how much of the source a single advancement actually reads."""
            for item in super().__iter__():
                self.reads += 1
                yield item

    values = ObservedList(range(10000))
    steps = operation({"mesh": {"vertices": values}})
    next(steps)
    assert 0 < values.reads < 1000
    steps.close()


def test_cooperative_capture_preserves_canonical_scene_fingerprints(monkeypatch):
    """Both finalizers must produce identical structural/full canonical identities."""
    from ..adapters.bonsai_live import load_bonsai_capture
    from .test_analysis_requests import _plane

    context, _, _ = runtime(monkeypatch)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene")
    capture.capture_next_batch(job)
    original = load_bonsai_capture(capture.finalize_capture(job), plane=_plane())
    cooperative, _ = _consume_steps(capture.finalize_capture_steps(job))
    actual = load_bonsai_capture(cooperative, plane=_plane())
    assert actual.full_fingerprint == original.full_fingerprint
    assert actual.structural_fingerprint == original.structural_fingerprint
    assert actual.capture_fingerprint == original.capture_fingerprint


def test_native_group_capture_refuses_membership_drift(monkeypatch):
    """Only explicit IFC assignments enter capture, and an edit during extraction invalidates it."""
    context, entities, _evaluated = runtime(monkeypatch)
    model = sys.modules["bonsai.bim.ifc"].IfcStore.get_file()
    original_by_type = model.by_type
    relation = SimpleNamespace(RelatedObjects=[entities[0]])
    group = SimpleNamespace(GlobalId="group-guid", ObjectType="furniture_group", IsGroupedBy=[relation])
    model.by_type = lambda kind: [group] if kind == "IfcGroup" else original_by_type(kind)
    job = capture.begin_analysis_capture(bpy_context=context, scene_token="scene")
    capture.capture_next_batch(job)
    result = capture.finalize_capture(job)
    assert result.identity["authored_groups"][0]["member_refs"] == ("ifc-object:wall-guid",)
    relation.RelatedObjects.append(entities[1])
    with pytest.raises(ValueError, match="group membership changed"):
        capture.finalize_capture(job)

