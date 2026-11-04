"""Display-only overlay records and authoritative cell inspection helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

try:
    from ...adapters import blender_analysis_result_wire as wire
except ImportError:
    from adapters import blender_analysis_result_wire as wire


@dataclass(frozen=True)
class OverlayRecord:
    """Frozen native-ready geometry with presentation lift kept outside result truth."""

    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, ...], ...]
    face_cell_indices: tuple[int, ...]
    face_attributes: tuple[Mapping[str, object], ...]
    parent: object = None


STATUS_CODES = {"established": 0, "conditional": 1, "unknown": 2,
                "outside": 3, "invalid": 4, "not_available": 5}


def build_overlay_mesh(result: wire.ValidatedAnalysisResult, *, display_lift_m: float = 0.02) -> OverlayRecord:
    """Flatten validated world-metre fragments and apply only a display Z lift."""
    if not isinstance(result, wire.ValidatedAnalysisResult):
        raise TypeError("result must be a ValidatedAnalysisResult")
    if type(display_lift_m) not in (int, float) or not math.isfinite(display_lift_m) or display_lift_m < 0:
        raise ValueError("display lift must be finite and nonnegative")
    document = result.document
    lattice = document["tables"]["lattice"]
    cells = document["cells"]
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    indices: list[int] = []
    attributes: list[Mapping[str, object]] = []
    for fragment in document["display_fragments"]:
        start = len(vertices)
        vertices.extend((float(x), float(y), float(z) + float(display_lift_m)) for x, y, z in fragment["vertices"])
        cell_index = fragment["cell_index"]
        cell = cells[cell_index]
        row, column = divmod(cell_index, lattice["n_cols"])
        for face in fragment["faces"]:
            faces.append(tuple(start + index for index in face))
            indices.append(cell_index)
            attributes.append({"cell_index": cell_index, "row": row, "column": column,
                               "value": cell["value"], "status": cell["status"]})
    return OverlayRecord(tuple(vertices), tuple(faces), tuple(indices), tuple(attributes), None)


def inspect_cell(result: wire.ValidatedAnalysisResult, *, row: int, column: int) -> Mapping[str, object]:
    """Read one complete authoritative sample through the stdlib wire decoder."""
    if not isinstance(result, wire.ValidatedAnalysisResult):
        raise TypeError("result must be a ValidatedAnalysisResult")
    return wire.decode_cell(result.document, row=row, column=column)


def restore_embedded_result(text_body: str) -> wire.ValidatedAnalysisResult:
    """Restore strict JSON Text content without starting jobs or requiring a sidecar."""
    if not isinstance(text_body, str):
        raise TypeError("embedded result must be text")
    document = wire.load_json(text_body)
    wire.validate_document(document)
    return wire.ValidatedAnalysisResult(document)


def build_native_mesh(result: wire.ValidatedAnalysisResult, *, bpy_module=None,
                       name: str = "OM Analysis Overlay", display_lift_m: float = 0.02):
    """Build one unparented tagged native mesh from validated display fragments."""
    record = build_overlay_mesh(result, display_lift_m=display_lift_m)
    if bpy_module is None:
        import bpy as bpy_module
    scale = native_unit_scale(bpy_module)
    mesh = bpy_module.data.meshes.new(name)
    # Fragments are world SI; Blender coordinates use the active scene's length scale.
    mesh.from_pydata([tuple(value / scale for value in point) for point in record.vertices], [], record.faces)
    mesh.update()
    obj = bpy_module.data.objects.new(name, mesh)
    obj.parent = None
    obj["om_analysis_owner"] = "order_analyzer"
    obj["om_analysis_role"] = "overlay"
    obj["om_analysis_result_id"] = result.document["result_id"]
    attributes = getattr(mesh, "attributes", None)
    if attributes is not None:
        columns = {
            "cell_index": [item["cell_index"] for item in record.face_attributes],
            "row": [item["row"] for item in record.face_attributes],
            "column": [item["column"] for item in record.face_attributes],
            "value": [int(item["value"]) if isinstance(item["value"], bool) else -1 for item in record.face_attributes],
            "status": [STATUS_CODES[item["status"]] for item in record.face_attributes],
        }
        for attr_name, values in columns.items():
            attr = attributes.new(attr_name, "INT", "FACE")
            for index, value in enumerate(values):
                attr.data[index].value = value
    # Datablocks alone are invisible; publication must attach this display object to the scene.
    bpy_module.context.scene.collection.objects.link(obj)
    return obj


def native_unit_scale(bpy_module):
    """Read a positive finite native length scale, preserving old minimal test seams."""
    settings = getattr(bpy_module.context.scene, "unit_settings", None)
    scale = settings.scale_length if settings is not None else 1.
    if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("scene unit scale must be finite and positive")
    return float(scale)

