"""Behavioral checks for persistent exact-result boards without importing bpy."""

from copy import deepcopy
import importlib
from types import SimpleNamespace

import pytest

from ..adapters import blender_analysis_result_wire as wire
from .test_blender_analysis_overlay import _document


def _board_module():
    """Load the board on demand so missing implementation is an ordinary failure."""
    return importlib.import_module("..blender_addon.order_analyzer_ui.board", package=__package__)


def _result(result_id="first", **datum_changes):
    """Supply independent slab, plane and project evidence in a valid wire fixture."""
    document = _document()
    document["result_id"] = document["job_id"] = result_id
    document["binding"]["job_id"] = result_id
    datum = {"mode": "slab", "project_global_id": "project", "storey_ref": "ifc-object:storey",
             "storey_id": 2, "slab_ref": "ifc-object:slab", "slab_id": 3,
             "datum_z_m": -2.0, "geometry_digest": "a" * 64, **datum_changes}
    datum["observation_digest"] = wire.document_digest(datum)
    document["identity"]["project_source_identity"]["project_global_id"] = "project"
    document["tables"]["snapshot"]["provenance"]["project_source_identity"] = deepcopy(document["identity"]["project_source_identity"])
    request = document["tables"]["snapshot"]["request"]
    request["height_band_datum"] = datum
    request["plane"]["origin"] = [10, 20, 1.6]
    for fragment in document["display_fragments"]:
        fragment["vertices"] = [[x + 10, y + 20, 1.6] for x, y, z in fragment["vertices"]]
    document["digest"] = wire.document_digest(document)
    wire.validate_document(document)
    return wire.ValidatedAnalysisResult(document)


class _ID(dict):
    """Represent native custom properties while retaining identity comparison."""

    def __init__(self, name, data=None):
        """Keep mesh, transforms and visibility as ordinary native-like fields."""
        super().__init__()
        self.name, self.data, self.parent = name, data, None
        self.type = "EMPTY" if data is None else "MESH"
        self.location = (0, 0, 0)
        self.hide_viewport = self.hide_render = False
        self._material_slots = []

    @property
    def material_slots(self):
        """Reflect shared mesh slot changes while preserving per-object overrides."""
        count = len(self.data.materials) if self.data is not None else 0
        while len(self._material_slots) < count:
            self._material_slots.append(SimpleNamespace(link="DATA", material=None))
        return self._material_slots[:count]


class _Mesh(_ID):
    """Store geometry and source material slots in the native test seam."""

    def __init__(self, name):
        """Initialize the geometry collections expected by production builders."""
        super().__init__(name)
        self.materials, self.vertices, self.polygons = [], [], []

    def from_pydata(self, vertices, edges, faces):
        """Retain exact coordinates for independent world-unit assertions."""
        self.vertices = list(vertices)
        self.polygons = [SimpleNamespace(vertices=face, material_index=0) for face in faces]

    def update(self):
        """Match the native mesh finalization seam."""


class _Objects(list):
    """Create native objects with live slots derived from their shared mesh."""

    def new(self, name, data):
        """Return one unlinked native-like object with usable material overrides."""
        obj = _ID(name, data)
        self.append(obj)
        return obj


class _Nodes(list):
    """Build shader nodes with native input names and writable sockets."""

    def new(self, node_type):
        """Supply the Principled/output sockets used by actual material wiring."""
        node = SimpleNamespace(type="BSDF_PRINCIPLED" if node_type == "ShaderNodeBsdfPrincipled" else "OUTPUT_MATERIAL",
            inputs={name: SimpleNamespace(default_value=None) for name in ("Base Color", "Alpha", "Roughness", "Surface")},
            outputs={"BSDF": object()})
        self.append(node)
        return node


def _bpy(scale=1):
    """Provide only native storage, linking and shader seams; no numerical mocks."""
    scene_objects = []
    objects = _Objects()
    materials = []

    def material(name):
        """Create a material with an independently inspectable shader graph."""
        item = _ID(name)
        item.node_tree = _ID(name + " Nodes")
        item.node_tree.nodes = _Nodes()
        item.node_tree.links = SimpleNamespace(new=lambda output, input: None)
        item.surface_render_method = "DITHERED"
        materials.append(item)
        return item

    return SimpleNamespace(data=SimpleNamespace(objects=objects,
        meshes=SimpleNamespace(new=_Mesh), materials=SimpleNamespace(new=material)),
        context=SimpleNamespace(scene=SimpleNamespace(objects=scene_objects,
            unit_settings=SimpleNamespace(scale_length=scale),
            collection=SimpleNamespace(objects=SimpleNamespace(link=scene_objects.append)))))


def _save(result, path):
    """Write actual strict sidecar bytes through the existing atomic publisher."""
    wire.write_result_atomic(wire.plain(result.document), path=path)
    return path


def test_board_exact_ref_roundtrip_and_failed_switch_preserves_display(tmp_path):
    """Wrong external digest cannot replace a retained compatible result display."""
    board = _board_module()
    bpy = _bpy()
    first, second = _result(), _result("second")
    first_path, second_path = tmp_path / "first.json", tmp_path / "second.json"
    native = board.attach_result(first, result_path=_save(first, first_path), bpy_module=bpy)
    board.update_style(native, palette="magma", reverse=True, opacity=.3, bpy_module=bpy)
    again = board.attach_result(second, result_path=_save(second, second_path), bpy_module=bpy)
    record = board.board_record(native)
    assert again is native and len(board.scene_boards(bpy_module=bpy)) == 1
    assert record["active_result_id"] == "second" and record["style"]["palette"] == "magma"
    assert record["style"]["opacity"] == .3
    assert record["results"][0]["ref"] == {"kind": "free_space_run", "result_id": "first", "digest": first.digest}
    assert record["results"][0]["expected_identity"] == wire.plain(first.identity)
    assert record["results"][0]["backend_versions"] == wire.plain(first.backend_versions)
    board.select_result(native, "first", bpy_module=bpy)
    assert board.board_record(native)["status"] == "historical"
    before = native[board.DESCRIPTOR_PROPERTY]
    first_path.write_text(wire.canonical_json(second.document), encoding="utf-8")
    with pytest.raises(ValueError, match="ResultRef"):
        board.select_result(native, "first", bpy_module=bpy)
    assert native[board.DESCRIPTOR_PROPERTY] == before


@pytest.mark.parametrize("changed", [{"slab_ref": "ifc-object:other"}, {"datum_z_m": -1},
    {"geometry_digest": "b" * 64}, {"storey_ref": "ifc-object:other"}, {"storey_id": 99}])
def test_switch_rejects_full_datum_mismatch(tmp_path, changed):
    """A ground receipt mismatch fails before replacing the visible board."""
    board = _board_module()
    bpy = _bpy()
    first = _result()
    native = board.attach_result(first, result_path=_save(first, tmp_path / "first.json"), bpy_module=bpy)
    record = board.board_record(native)
    candidate = _result("other", **changed)
    path = _save(candidate, tmp_path / "other.json")
    entry = deepcopy(record["results"][0])
    entry.update(ref={"kind": candidate.kind, "result_id": candidate.result_id, "digest": candidate.digest},
                 path=str(path), expected_identity=wire.plain(candidate.identity))
    record["results"].append(entry)
    native[board.DESCRIPTOR_PROPERTY] = wire.canonical_json(record)
    with pytest.raises(ValueError, match="binding|datum"):
        board.select_result(native, "other", bpy_module=bpy)
    assert board.board_record(native)["active_result_id"] == "first"


def test_missing_sidecar_restore_hides_display_without_recovering_authority(tmp_path):
    """Reopening refuses lost sidecar bytes even with a retained native mesh."""
    board = _board_module()
    bpy = _bpy()
    result = _result()
    path = _save(result, tmp_path / "first.json")
    native = board.attach_result(result, result_path=path, bpy_module=bpy)
    path.unlink()
    board.restore_boards(bpy_module=bpy)
    record = board.board_record(native)
    assert record["status"] == "unavailable" and record["message"]
    display = next(obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display")
    assert display.hide_viewport and display.hide_render
    _save(result, path)
    board.restore_boards(bpy_module=bpy)
    assert board.board_record(native)["status"] == "historical"
    assert not display.hide_viewport and not display.hide_render


@pytest.mark.parametrize("external_root", [[], None, "unrelated", 17])
def test_malformed_sidecar_root_hides_display_and_continues_restoring(tmp_path, external_root):
    """Non-object JSON cannot leave stale displays visible or interrupt later boards."""
    board = _board_module()
    bpy = _bpy()
    result = _result()
    path = _save(result, tmp_path / "first.json")
    native = board.attach_result(result, result_path=path, bpy_module=bpy)
    other_result = _result("other", slab_ref="ifc-object:other-slab")
    other = board.attach_result(other_result, result_path=_save(other_result, tmp_path / "other.json"), bpy_module=bpy)
    display = next(obj for obj in bpy.context.scene.objects if obj.parent is native)
    other_display = next(obj for obj in bpy.context.scene.objects if obj.parent is other)
    other_display.hide_viewport = other_display.hide_render = True
    path.write_text(wire.canonical_json(external_root), encoding="utf-8")

    board.restore_boards(bpy_module=bpy)

    record = board.board_record(native)
    assert record["status"] == "unavailable" and record["message"]
    assert display.hide_viewport and display.hide_render
    assert board.board_record(other)["status"] == "historical"
    assert not other_display.hide_viewport and not other_display.hide_render
    _save(result, path)
    board.restore_boards(bpy_module=bpy)
    previous_descriptor, previous_mesh = native[board.DESCRIPTOR_PROPERTY], display.data
    path.write_text(wire.canonical_json(external_root), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        board.select_result(native, "first", bpy_module=bpy)
    assert native[board.DESCRIPTOR_PROPERTY] == previous_descriptor and display.data is previous_mesh
    assert not display.hide_viewport and not display.hide_render


def test_board_native_placement_shares_geometry_and_converts_metres(tmp_path):
    """World XY and slab offset remain correct at a non-unit native scene scale."""
    board = _board_module()
    bpy = _bpy(.01)
    result = _result()
    native = board.attach_result(result, result_path=_save(result, tmp_path / "first.json"), bpy_module=bpy)
    source = next(obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_source")
    display = next(obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display")
    assert source.hide_viewport and source.hide_render and display.data is source.data
    assert display.parent is native
    assert source.data.vertices[0] == pytest.approx((1000, 2000, 162))
    assert display.location == pytest.approx((0, 0, -360))
    assert source.data.vertices[0][2] + display.location[2] == pytest.approx(-198)
    geometry = list(source.data.vertices)
    board.update_style(native, display_elevation_m=.1, opacity=.25, bpy_module=bpy)
    assert source.data.vertices == geometry
    assert source.data.vertices[0][2] + display.location[2] == pytest.approx(-190)


def test_historical_restore_rebuilds_geometry_for_changed_native_scale(tmp_path):
    """A saved source at another native scale cannot be reused with wrong world units."""
    board = _board_module()
    bpy = _bpy()
    result = _result()
    native = board.attach_result(result, result_path=_save(result, tmp_path / "first.json"), bpy_module=bpy)
    display = next(obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display")
    first_mesh = display.data
    bpy.context.scene.unit_settings.scale_length = .001
    board.restore_boards(bpy_module=bpy)
    assert display.data is not first_mesh
    assert display.data.vertices[0] == pytest.approx((10000, 20000, 1620))
    assert (display.data.vertices[0][2] + display.location[2]) * .001 == pytest.approx(-1.98)
    bpy.context.scene.unit_settings.scale_length = 1
    board.select_result(native, "first", bpy_module=bpy)
    assert display.data is first_mesh


def test_native_materials_wire_alpha_and_preserve_other_board_style(tmp_path):
    """Material updates reach shader inputs without modifying geometry or other objects."""
    board = _board_module()
    bpy = _bpy()
    result = _result()
    native = board.attach_result(result, result_path=_save(result, tmp_path / "first.json"), bpy_module=bpy)
    display = next(obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display")
    slots = display.material_slots
    assert all(slot.link == "OBJECT" for slot in slots)
    shader = next(node for node in slots[0].material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    assert shader.inputs["Alpha"].default_value == .5
    assert shader.inputs["Base Color"].default_value[:3] == pytest.approx((0, .016361268454, .075613426750))
    vertices = list(display.data.vertices)
    board.update_style(native, opacity=.25, reverse=True, bpy_module=bpy)
    assert shader.inputs["Alpha"].default_value == .25
    assert shader.inputs["Base Color"].default_value[:3] == pytest.approx((.990329595889, .806029348704, .038914691162))
    assert display.data.vertices == vertices
    other_display = _ID("Other board display", display.data)
    record = board.board_record(native)
    board._style_display(other_display, "other-board", {**record["style"], "opacity": .8}, record["binding"], bpy)
    assert other_display.material_slots[0].material is not slots[0].material
    assert shader.inputs["Alpha"].default_value == .25
    assert other_display.material_slots[0].material.node_tree.nodes[0].inputs["Alpha"].default_value == .8
    board._color_material(slots[0].material, (.5, .5, .5, .2))
    assert shader.inputs["Base Color"].default_value == pytest.approx((.214041140482, .214041140482, .214041140482, .2))


def test_board_requires_explicit_slab_receipt_and_rejects_invalid_units(tmp_path):
    """Legacy datum-free overlays remain valid but cannot create ground boards."""
    board = _board_module()
    with pytest.raises(ValueError, match="datum"):
        board.attach_result(wire.ValidatedAnalysisResult(_document()), result_path=tmp_path / "legacy.json", bpy_module=_bpy())
    for scale in (0, -1, float("nan"), float("inf"), True):
        with pytest.raises(ValueError, match="scale"):
            board.attach_result(_result(), result_path=tmp_path / "first.json", bpy_module=_bpy(scale))


@pytest.mark.parametrize("changes", [{"opacity": float("nan")}, {"opacity": 1.1}, {"opacity": True},
    {"reverse": 1}, {"palette": "rainbow"}, {"range_mode": "manual", "range_min": 2, "range_max": 1},
    {"range_min": float("inf")}, {"display_elevation_m": float("nan")}])
def test_invalid_style_is_atomic(tmp_path, changes):
    """Invalid finite/range/enum settings never overwrite the saved good style."""
    board = _board_module()
    bpy = _bpy()
    result = _result()
    native = board.attach_result(result, result_path=_save(result, tmp_path / "first.json"), bpy_module=bpy)
    previous = native[board.DESCRIPTOR_PROPERTY]
    with pytest.raises(ValueError):
        board.update_style(native, bpy_module=bpy, **changes)
    assert native[board.DESCRIPTOR_PROPERTY] == previous


def test_palette_endpoints_status_legend_and_numeric_constant_range():
    """Boolean categories ignore numeric range; uncertain statuses stay distinguishable."""
    palettes = importlib.import_module("..blender_addon.order_analyzer_ui.palettes", package=__package__)
    assert palettes.cell_color(False, "established") == pytest.approx((0, .135112, .304751, .5))
    assert palettes.cell_color(True, "established", reverse=True) == palettes.cell_color(False, "established")
    uncertain = [palettes.cell_color(None, status) for status in ("unknown", "outside", "invalid", "not_available")]
    assert len(set(uncertain + [palettes.cell_color(False, "established"), palettes.cell_color(False, "conditional")])) == 6
    assert len(palettes.LEGEND) == 7
    assert palettes.map_numeric([7, 7]) == [palettes.palette_color(.5), palettes.palette_color(.5)]
    assert palettes.map_numeric([0, 10], range_mode="manual", range_min=0, range_max=10)[0] == palettes.palette_color(0)
    for values in ([float("nan")], [float("inf")], [True]):
        with pytest.raises(ValueError):
            palettes.map_numeric(values)


def test_numeric_mapper_handles_finite_extremes_and_subnormal_ranges():
    """Finite scalars remain valid when subtraction overflows or halving underflows."""
    palettes = importlib.import_module("..blender_addon.order_analyzer_ui.palettes", package=__package__)
    for values in ([0., 5e-324], [-1e308, 1e308]):
        colors = palettes.map_numeric(values)
        assert colors[0] == palettes.palette_color(0)
        assert colors[1] == palettes.palette_color(1)


def test_descriptor_corruption_and_foreign_ownership_are_rejected(tmp_path):
    """Only fully described owned board objects qualify as selectable boards."""
    board = _board_module()
    bpy = _bpy()
    result = _result()
    native = board.attach_result(result, result_path=_save(result, tmp_path / "first.json"), bpy_module=bpy)
    assert board.owned_display_datablock(native)
    assert not board.owned_display_datablock({"om_analysis_owner": "order_analyzer", "om_analysis_role": "ordinary"})
    native[board.DESCRIPTOR_PROPERTY] = '{"version": 99}'
    with pytest.raises(ValueError):
        board.board_record(native)


@pytest.mark.parametrize("mismatch", ["identity", "backend"])
def test_saved_expectations_are_independent_of_external_file(tmp_path, mismatch):
    """A self-consistent replacement cannot reset the consumer's stored expectations."""
    board = _board_module()
    bpy = _bpy()
    result = _result()
    path = _save(result, tmp_path / "first.json")
    native = board.attach_result(result, result_path=path, bpy_module=bpy)
    replacement = wire.plain(result.document)
    if mismatch == "identity":
        replacement["identity"]["request_identity"] = "other-request"
        replacement["tables"]["snapshot"]["request"]["request_id"] = "other-request"
    else:
        replacement["backend_versions"]["display-test"] = "other-version"
        replacement["tables"]["snapshot"]["backend_versions"] = dict(replacement["backend_versions"])
    replacement["digest"] = wire.document_digest(replacement)
    wire.write_result_atomic(replacement, path=path)
    # Even if the saved content selector is updated, its independent expectations must still reject.
    record = board.board_record(native)
    record["results"][0]["ref"]["digest"] = replacement["digest"]
    native[board.DESCRIPTOR_PROPERTY] = wire.canonical_json(record)
    with pytest.raises(ValueError, match="identity|backend"):
        board.select_result(native, "first", bpy_module=bpy)


def test_native_switch_failure_keeps_previous_display_and_descriptor(tmp_path, monkeypatch):
    """A native material handoff error must preserve the previously selected geometry."""
    board = _board_module()
    bpy = _bpy()
    first, second = _result(), _result("second")
    native = board.attach_result(first, result_path=_save(first, tmp_path / "first.json"), bpy_module=bpy)
    board.attach_result(second, result_path=_save(second, tmp_path / "second.json"), bpy_module=bpy)
    board.select_result(native, "first", bpy_module=bpy)
    display = next(obj for obj in bpy.context.scene.objects if obj.get("om_analysis_role") == "board_display")
    previous_mesh, previous_location = display.data, display.location
    previous_descriptor = native[board.DESCRIPTOR_PROPERTY]

    def reject_style(*args, **kwargs):
        """Simulate failure at the actual native style handoff after source selection."""
        raise ValueError("native material unavailable")

    monkeypatch.setattr(board, "_style_display", reject_style)
    with pytest.raises(ValueError, match="native material"):
        board.select_result(native, "second", bpy_module=bpy)
    assert display.data is previous_mesh and display.location == previous_location
    assert native[board.DESCRIPTOR_PROPERTY] == previous_descriptor
