"""In-session Blender controls for private B4 interior-domain diagnostics."""

from collections import Counter
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
import subprocess
import uuid

import bpy


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/design/d6_b4_live_blender/run_001"
HOST = Path(__file__).with_name("run_live_domain.py")
PYTHON = ROOT / ".pixi/envs/default/python.exe"
COLLECTION = "OM_AnalysisPreview_B4"
STATE = {"result": None, "selected": None, "error": None, "stale": False,
         "sidebar_prior": []}
COLORS = ((0.95, 0.30, 0.22, 1), (0.18, 0.72, 0.94, 1), (0.42, 0.82, 0.38, 1),
          (0.98, 0.75, 0.20, 1), (0.72, 0.43, 0.96, 1))


def capture(scene) -> dict:
    """Capture only live IFC structural meshes, preserving every source object."""
    from bonsai.bim.ifc import IfcStore
    from ifcopenshell.util.element import get_psets

    if bpy.app.binary_path.lower().replace("\\", "/") != "d:/blender/blenderportablelts5.2/app/blender64/blender.exe":
        raise ValueError("This task requires the configured portable Blender 5.2 executable")
    if scene.unit_settings.system != "METRIC" or scene.unit_settings.scale_length != 1:
        raise ValueError("Live scene must use world metres at unit scale 1")
    source = IfcStore.get_file()
    if source is None:
        raise ValueError("No live Bonsai IFC file is linked")
    if source.by_type("IfcOpeningElement"):
        raise ValueError("Authored IFC openings need explicit capture before B4 inference")
    role_by_class = {"IfcWall": "wall", "IfcColumn": "column", "IfcDoor": "door", "IfcWindow": "window"}
    objects, roles, scope = [], {}, []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in scene.objects:
        step_id = getattr(getattr(obj, "BIMObjectProperties", None), "ifc_definition_id", 0)
        if not step_id:
            continue
        entity = source.by_id(step_id)
        role = role_by_class.get(entity.is_a())
        if role is None:
            continue
        if obj.type != "MESH":
            raise ValueError(f"{obj.name} has no mesh for structural capture")
        object_id = f"live-step-{step_id}"
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            # Evaluated vertices enter the neutral adapter in world metres once;
            # matrix_world remains provenance and is never applied by the adapter.
            vertices = [list(obj.matrix_world @ vert.co) for vert in mesh.vertices]
            triangles = [list(tri.vertices) for tri in mesh.loop_triangles]
        finally:
            evaluated.to_mesh_clear()
        objects.append({"id": object_id, "name": obj.name, "selected": True,
                        "vertices": vertices, "triangles": triangles, "units": "m",
                        "transform_applied": True, "world_transform": [list(row) for row in obj.matrix_world],
                        "representation_id": f"live-evaluated-step-{step_id}",
                        "tessellation_settings": {"method": "evaluated_mesh_loop_triangles"},
                        "factual_properties": get_psets(entity, psets_only=True)})
        roles[object_id] = role
        scope.append({"id": object_id, "name": obj.name, "step_id": step_id,
                      "global_id": entity.GlobalId, "ifc_class": entity.is_a(),
                      "vertices": len(vertices), "triangles": len(triangles)})
    if not objects:
        raise ValueError("No live IFC walls, columns, doors or windows were found")
    identity = {"binary": bpy.app.binary_path, "blend_path": bpy.data.filepath,
                "dirty": bpy.data.is_dirty, "scene": scene.name,
                "ifc_path": IfcStore.path, "ifc_schema": source.schema,
                "project_global_id": source.by_type("IfcProject")[0].GlobalId,
                "unit_scale": scene.unit_settings.scale_length,
                "counts": dict(Counter(roles.values())), "scope": scope}
    return {"identity": identity, "objects": objects, "roles": roles, "source_length_unit": "m"}


def _clear_overlays(scene) -> bpy.types.Collection:
    """Replace only objects carrying this diagnostic collection tag."""
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION)
        scene.collection.children.link(collection)
    for obj in tuple(collection.objects):
        if obj.get("OM_B4_Diagnostic"):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and data.users == 0:
                bpy.data.curves.remove(data)
    return collection


def _add_ring(collection, name: str, points, color, *, hole: bool) -> None:
    """Show a measured polygon ring as a tagged, nonselectable curve."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.045 if not hole else 0.025
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xy in zip(spline.points, points):
        point.co = (xy[0], xy[1], 0.12, 1)
    spline.use_cyclic_u = True
    obj = bpy.data.objects.new(name, curve)
    obj["OM_B4_Diagnostic"] = True
    obj["OM_B4_Hole"] = hole
    obj.hide_select = True
    obj.show_in_front = True
    obj.color = color
    collection.objects.link(obj)


def _draw_overlays(scene, candidates) -> None:
    """Draw each actual interior and its holes without touching source meshes."""
    collection = _clear_overlays(scene)
    for index, candidate in enumerate(candidates):
        outline = candidate.get("outline")
        if not outline or outline.get("type") != "Polygon":
            continue
        color = COLORS[index % len(COLORS)]
        for ring_index, ring in enumerate(outline["coordinates"]):
            _add_ring(collection, f"B4 {candidate['id']} {'hole' if ring_index else 'interior'} {ring_index}",
                      ring[:-1] if ring and ring[0] == ring[-1] else ring, color, hole=bool(ring_index))
        if candidate.get("label_xy"):
            label = bpy.data.curves.new(f"B4 {candidate['id']} label", "FONT")
            label.body = f"{candidate['id']}  {candidate['area_m2']:.1f} m²"
            label.size = 0.5
            label.align_x = "CENTER"
            obj = bpy.data.objects.new(label.name, label)
            obj.location = (*candidate["label_xy"], 0.22)
            obj.show_in_front = True
            obj.hide_select = True
            obj.color = color
            obj["OM_B4_Diagnostic"] = True
            collection.objects.link(obj)


def _run(scene, action=None) -> None:
    """Reobserve the live source and let the existing reducer decide state."""
    tolerance = scene.om_b4_tolerance_mm2
    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError("Residual tolerance must be finite and nonnegative")
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"snapshot": capture(scene), "tolerance_mm2": tolerance,
               "previous": STATE["result"], "action": action}
    request_path, result_path = OUT / "live_request.json", OUT / "live_result.json"
    request_path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    process = subprocess.run([str(PYTHON), str(HOST), str(request_path), str(result_path)],
                             cwd=ROOT, capture_output=True, text=True, timeout=180)
    if process.returncode:
        raise RuntimeError((process.stderr or process.stdout).strip()[-1200:])
    result = json.loads(result_path.read_text(encoding="utf-8"))
    _draw_overlays(scene, result["candidates"])
    STATE.update(result=result, error=None, stale=False)
    if STATE["selected"] not in {item["version_id"] for item in result["candidates"]}:
        STATE["selected"] = None


def _tolerance_changed(self, context) -> None:
    """Observe every changed request so a reverted edit cannot revive consent."""
    if STATE["result"] is None:
        return
    STATE["stale"] = True
    try:
        _run(context.scene)
    except Exception as exc:
        STATE["error"] = str(exc)


class OM_B4_OT_refresh(bpy.types.Operator):
    """Recompute enclosure candidates from the currently open IFC scene."""

    bl_idname = "om_b4.refresh"
    bl_label = "Refresh live interiors"

    def execute(self, context):
        """Run the live capture and report a bounded failure in the panel."""
        STATE["stale"] = True
        try:
            _run(context.scene)
        except Exception as exc:
            STATE["error"] = str(exc)
            self.report({"ERROR"}, str(exc)[:240])
            return {"CANCELLED"}
        return {"FINISHED"}


class OM_B4_OT_select(bpy.types.Operator):
    """Focus one candidate without confirming an AnalysisDomain."""

    bl_idname = "om_b4.select"
    bl_label = "Select interior"
    version_id: bpy.props.StringProperty()

    def execute(self, context):
        """Use the reducer's read-only select action on fresh source data."""
        STATE["stale"] = True
        try:
            _run(context.scene, {"kind": "select", "candidate_version_id": self.version_id})
            if STATE["result"]["attempt"]["status"] == "selected":
                STATE["selected"] = self.version_id
        except Exception as exc:
            STATE["error"] = str(exc)
            self.report({"ERROR"}, str(exc)[:240])
            return {"CANCELLED"}
        return {"FINISHED"}


class OM_B4_OT_confirm(bpy.types.Operator):
    """Submit an explicit candidate confirmation to the private handoff."""

    bl_idname = "om_b4.confirm"
    bl_label = "Confirm selected interior"

    def execute(self, context):
        """Bind source, frame, request, candidate and revision at click time."""
        previous = STATE["result"]
        candidate = next((item for item in previous["candidates"]
                          if item["version_id"] == STATE["selected"]), None) if previous else None
        if candidate is None or STATE["stale"]:
            self.report({"ERROR"}, "Refresh and select a current interior first")
            return {"CANCELLED"}
        provenance = previous["provenance"]
        action = {"kind": "confirm", "candidate_version_id": candidate["version_id"],
                  "action_id": str(uuid.uuid4()), "actor": "Blender user",
                  "time": datetime.now(timezone.utc).isoformat(), "reason": "explicit UI confirmation",
                  "expected_session_revision": previous["session_revision"],
                  "expected_source_revision": provenance["source_revision"],
                  "expected_plane_identity": provenance["frame_id"],
                  "expected_request_identity": provenance["request_id"],
                  "expected_candidate_identity": candidate["identity"],
                  "acknowledged_conflict_ids": []}
        STATE["stale"] = True
        try:
            _run(context.scene, action)
        except Exception as exc:
            STATE["error"] = str(exc)
            self.report({"ERROR"}, str(exc)[:240])
            return {"CANCELLED"}
        if STATE["result"]["attempt"]["status"] != "accepted":
            self.report({"WARNING"}, STATE["result"]["attempt"]["reason"] or "Confirmation refused")
        return {"FINISHED"}


class OM_B4_PT_domain(bpy.types.Panel):
    """Show measured candidates and the explicit session handoff state."""

    bl_label = "B4 Interior Domain"
    bl_idname = "OM_B4_PT_domain"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Domain B4"

    def draw(self, context):
        """Keep area, holes, refusal and current state readable without color."""
        layout = self.layout
        layout.label(text="World XY; datum 0 m; cut 1.5 m")
        layout.label(text="Doors/windows assumed closed")
        layout.prop(context.scene, "om_b4_tolerance_mm2", text="Residual tolerance (mm²)")
        layout.operator("om_b4.refresh")
        if STATE["error"]:
            layout.label(text="Error: " + STATE["error"][:75], icon="ERROR")
        result = STATE["result"]
        if result is None:
            layout.label(text="Refresh to inspect live candidates")
            return
        if STATE["stale"]:
            layout.label(text="Source/request changed; refresh required", icon="ERROR")
        else:
            layout.label(text="State at last live refresh")
        layout.label(text=f"{len(result['candidates'])} interiors; {result['source_count']} source meshes")
        for candidate in result["candidates"]:
            row = layout.row(align=True)
            marker = "●" if candidate["version_id"] == STATE["selected"] else "○"
            op = row.operator("om_b4.select", text=f"{marker} {candidate['id']}")
            op.version_id = candidate["version_id"]
            area = candidate["area_m2"]
            row.label(text=f"{area:.3f} m² / {candidate['holes']} holes" if area is not None else "invalid")
            if candidate["reason"]:
                layout.label(text=f"{candidate['id']}: {candidate['reason']}", icon="ERROR")
        if STATE["selected"]:
            layout.operator("om_b4.confirm")
        current = result["current"]
        layout.label(text=f"Current: {'stale' if STATE['stale'] else current['status']}")
        if current["candidate_version_id"]:
            layout.label(text=str(current["candidate_version_id"]).split(":")[1])
        if current["reason"]:
            layout.label(text="Reason: " + current["reason"])
        attempt = result["attempt"]
        if attempt["status"] not in {"none", "selected"}:
            layout.label(text=f"Last attempt: {attempt['status']} {attempt['reason'] or ''}")
        ignored = [a for a in result["apertures"] if not a["significant_residual"]]
        if ignored:
            layout.label(text=f"Ignored tiny residuals: {len(ignored)}")


CLASSES = (OM_B4_OT_refresh, OM_B4_OT_select, OM_B4_OT_confirm, OM_B4_PT_domain)


def register() -> None:
    """Register only reversible session-local UI classes and the tolerance field."""
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.om_b4_tolerance_mm2 = bpy.props.FloatProperty(
        name="Residual tolerance (mm²)", default=10.0, min=0.0, precision=6,
        update=_tolerance_changed)
    screen = bpy.context.window.screen
    for area in screen.areas:
        if area.type == "VIEW_3D":
            STATE["sidebar_prior"].append((area, area.spaces.active.show_region_ui))
            area.spaces.active.show_region_ui = True


def unregister() -> None:
    """Remove the panel and controls without changing source or preview data."""
    for area, previous in STATE["sidebar_prior"]:
        if area.type == "VIEW_3D":
            area.spaces.active.show_region_ui = previous
    del bpy.types.Scene.om_b4_tolerance_mm2
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
