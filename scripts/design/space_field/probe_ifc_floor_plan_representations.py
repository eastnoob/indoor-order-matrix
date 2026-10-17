"""Inventory authored IFC plan evidence without tessellating product bodies."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import time

from run_native_ifc_timeout_probe import ROOT, fingerprint, utc, write_json

SOURCE = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
SNAPSHOT = ROOT / "outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json"
EXPECTED_IFC = (408617800, "018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240")
EXPECTED_SNAPSHOT = "c5659dcd99d8c4f20b97efd2cc37352d6305436e20e698ccbcf8c89abfe67867"


def identity(entity):
    """Keep source STEP and GlobalId identities without interpreting names."""
    return {"step_id": entity.id(), "ifc_class": entity.is_a(),
            "global_id": getattr(entity, "GlobalId", None), "name": getattr(entity, "Name", None)}


def placement_record(placement, scale):
    """Record explicit local placement in metres, preserving absent placements."""
    import ifcopenshell.util.placement as placement_util

    if placement is None:
        return {"status": "not_authored", "matrix_world_m": None}
    if not placement.is_a("IfcLocalPlacement"):
        return {"status": "unsupported", "step_id": placement.id(), "type": placement.is_a()}
    matrix = placement_util.get_local_placement(placement).copy()
    # Placement translations share IFC length units; basis directions do not.
    matrix[:3, 3] *= scale
    return {"status": "observed", "step_id": placement.id(), "matrix_world_m": matrix.tolist()}


def item_record(item):
    """Inspect representation mechanisms without reading or meshing body faces."""
    row = {"step_id": item.id(), "type": item.is_a()}
    if item.is_a("IfcMappedItem"):
        row.update(mapping_source_id=item.MappingSource.id(),
                   mapped_representation_id=item.MappingSource.MappedRepresentation.id(),
                   mapping_origin=str(item.MappingSource.MappingOrigin),
                   mapping_target=str(item.MappingTarget))
    elif item.is_a("IfcGeometricSet"):
        row["elements"] = [item_record(element) for element in item.Elements]
    elif item.is_a("IfcPolyline"):
        row.update(point_count=len(item.Points), dimensions=sorted({point.Dim for point in item.Points}),
                   closed=tuple(item.Points[0].Coordinates) == tuple(item.Points[-1].Coordinates))
    elif item.is_a("IfcIndexedPolyCurve"):
        row.update(point_list_type=item.Points.is_a(), segments=str(item.Segments))
    elif item.is_a("IfcTessellatedFaceSet"):
        row.update(point_list_type=item.Coordinates.is_a(), authored_closed=item.Closed)
    elif item.is_a("IfcCurve") or item.is_a("IfcSurface"):
        row["dimension"] = getattr(item, "Dim", None)
    return row


def worker(out):
    """Parse source metadata once and account for the exact structural subset."""
    import ifcopenshell
    import ifcopenshell.util.placement as placement_util
    import ifcopenshell.util.unit as unit_util

    tick = time.perf_counter()
    source_fp, snapshot_fp = fingerprint(SOURCE), fingerprint(SNAPSHOT)
    assert (source_fp["bytes"], source_fp["sha256"]) == EXPECTED_IFC
    assert snapshot_fp["sha256"] == EXPECTED_SNAPSHOT
    hash_seconds = time.perf_counter() - tick
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    scope = snapshot["source_scope"]
    assert len(scope) == 33 and len({row["step_id"] for row in scope}) == 33
    print("metadata_parse_start", utc(), flush=True)
    tick = time.perf_counter()
    model = ifcopenshell.open(str(SOURCE))
    parse_seconds = time.perf_counter() - tick
    print("metadata_parse_returned", model.schema, parse_seconds, flush=True)
    tick = time.perf_counter()
    assert model.schema == "IFC4"
    scale = unit_util.calculate_unit_scale(model)
    contexts = []
    for context in model.by_type("IfcGeometricRepresentationContext"):
        matrix = placement_util.get_axis2placement(context.WorldCoordinateSystem).copy()
        matrix[:3, 3] *= scale
        contexts.append({"step_id": context.id(), "type": context.is_a(),
                         "identifier": context.ContextIdentifier, "context_type": context.ContextType,
                         "dimension": context.CoordinateSpaceDimension,
                         "precision_source_units": context.Precision, "precision_m": context.Precision * scale,
                         "world_coordinate_system": str(context.WorldCoordinateSystem),
                         "world_coordinate_system_matrix_m": matrix.tolist(),
                         "true_north": str(context.TrueNorth) if context.TrueNorth else None,
                         "parent_context_id": getattr(context, "ParentContext", None).id()
                         if getattr(context, "ParentContext", None) else None,
                         "target_view": getattr(context, "TargetView", None),
                         "target_scale": getattr(context, "TargetScale", None),
                         "user_defined_target_view": getattr(context, "UserDefinedTargetView", None),
                         "representation_ids": sorted(rep.id() for rep in context.RepresentationsInContext)})
    representations = []
    for rep in model.by_type("IfcRepresentation"):
        context = rep.ContextOfItems
        items = [item_record(item) for item in rep.Items]
        # Labels identify a possible native plan source, never an occupied polygon.
        candidate = (getattr(context, "TargetView", None) in {"PLAN_VIEW", "REFLECTED_PLAN_VIEW"}
                     or rep.RepresentationIdentifier in {"FootPrint", "Annotation"}
                     or rep.RepresentationType in {"Curve2D", "Surface2D", "Annotation2D", "FillArea", "Text"}
                     or context.ContextType == "Plan")
        representations.append({"step_id": rep.id(), "class": rep.is_a(),
                                "identifier": rep.RepresentationIdentifier, "type": rep.RepresentationType,
                                "context_id": context.id(), "items": items, "plan_candidate": candidate})
    rep_by_id = {row["step_id"]: row for row in representations}
    membership = {}
    for relation in model.by_type("IfcRelContainedInSpatialStructure"):
        for obj in relation.RelatedElements:
            membership.setdefault(obj.id(), []).append(identity(relation.RelatingStructure))
    structural = []
    for expected in scope:
        obj = model.by_id(expected["step_id"])
        assert obj.GlobalId == expected["global_id"] and obj.is_a() == expected["ifc_class"]
        reps = list(obj.Representation.Representations) if obj.Representation else []
        pending = list(reps)
        reached = set()
        # Follow mapped representations so a plan hidden in a mapped block is counted.
        while pending:
            rep = pending.pop()
            if rep.id() in reached:
                continue
            reached.add(rep.id())
            pending.extend(item.MappingSource.MappedRepresentation for item in rep.Items if item.is_a("IfcMappedItem"))
        plan_ids = sorted(rep_id for rep_id in reached if rep_by_id[rep_id]["plan_candidate"])
        structural.append({**identity(obj), "snapshot_object_id": expected["object_id"],
                           "placement": placement_record(obj.ObjectPlacement, scale),
                           "direct_representation_ids": [rep.id() for rep in reps],
                           "reachable_representation_ids": sorted(reached), "native_plan_candidate_ids": plan_ids,
                           "spatial_containment": membership.get(obj.id(), []),
                           "qualification": {"status": "not_available" if not plan_ids else "not_verified",
                                             "reason": "no_authored_plan_representation" if not plan_ids else "requires_geometry_qualification",
                                             "occupied_geometry": None, "authored_cut_height_m": None}})
    assert Counter(row["ifc_class"] for row in structural) == {"IfcWall": 11, "IfcColumn": 16, "IfcDoor": 6}
    actual_ids = {obj.id() for kind in ("IfcWall", "IfcColumn", "IfcDoor") for obj in model.by_type(kind)}
    assert actual_ids == {row["step_id"] for row in structural}
    storeys = [{**identity(obj), "elevation_source_units": obj.Elevation,
                "placement": placement_record(obj.ObjectPlacement, scale),
                "representation_ids": [rep.id() for rep in obj.Representation.Representations] if obj.Representation else []}
               for obj in model.by_type("IfcBuildingStorey")]
    schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name("IFC4")
    count_types = ("IfcProduct", "IfcShapeRepresentation", "IfcMappedItem", "IfcRepresentationMap",
                   "IfcGeometricSet", "IfcGeometricCurveSet", "IfcAnnotation", "IfcOpeningElement",
                   "IfcRelVoidsElement", "IfcRelFillsElement", "IfcSpace", "IfcSpatialZone", "IfcCoordinateOperation")
    inventory_seconds = time.perf_counter() - tick
    result = {"schema_version": "d6_native_plan_probe_1", "source": source_fp, "snapshot_identity_only": snapshot_fp,
              "schema": model.schema, "ifcopenshell": ifcopenshell.version, "python": sys.version,
              "length_unit_scale_to_m": scale,
              "units": [str(unit) for project in model.by_type("IfcProject") for unit in project.UnitsInContext.Units],
              "contexts": contexts, "representations": representations, "structural_objects": structural,
              "storeys": storeys, "counts": {kind: len(model.by_type(kind)) for kind in count_types},
              "representation_identifier_counts": dict(Counter(row["identifier"] for row in representations)),
              "representation_type_counts": dict(Counter(row["type"] for row in representations)),
              "native_plan_candidate_representation_ids": [row["step_id"] for row in representations if row["plan_candidate"]],
              "coverage": {"expected": 33, "accounted": len(structural),
                           "with_plan_candidates": sum(bool(row["native_plan_candidate_ids"]) for row in structural),
                           "qualified_occupied_plan_objects": 0},
              "datum": {"status": "not_verified", "reason": "storey_elevation_and_placement_must_be_evidenced",
                        "chosen_experiment_datum_m": None, "world_xy_origin_is_floor_datum": False},
              "limits": ["disk IFC and evaluated snapshot geometry parity not established",
                         "no body tessellation, adapter load, occupancy query or inference executed",
                         "context/identifier/type is a candidate signal, not geometry or cut-height qualification",
                         "no qualified AnalysisDomain, free space, routes or furniture trend"],
              "installed_ifc4_support": {"projection_enum": list(schema.declaration_by_name("IfcGeometricProjectionEnum").enumeration_items()),
                                        "subcontext_attributes": [a.name() for a in schema.declaration_by_name("IfcGeometricRepresentationSubContext").all_attributes()],
                                        "curve2d_entity": schema.declaration_by_name("IfcPolyline").name()},
              "timings_seconds": {"input_hash": hash_seconds, "ifc_metadata_parse": parse_seconds,
                                  "metadata_inventory": inventory_seconds, "geometry_extraction": None,
                                  "geometric_query": None, "inference": None, "render": None},
              "runner": fingerprint(Path(__file__)), "argv": sys.argv, "ended_utc": utc()}
    write_json(out / "inventory.json", result)
    print(json.dumps({"coverage": result["coverage"], "identifier_counts": result["representation_identifier_counts"],
                      "native_plan_candidates": result["native_plan_candidate_representation_ids"], "storeys": storeys}), flush=True)


def main():
    """Use a fresh output directory and a finite metadata-only worker budget."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker(args.output_dir)
        return 0
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    baseline = {"utc": utc(), "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
                "status": subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True),
                "index": subprocess.check_output(["git", "diff", "--cached", "--name-status"], cwd=ROOT, text=True)}
    existing = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    baseline["untracked_fingerprints"] = [fingerprint(ROOT / path) for path in existing if path]
    write_json(out / "baseline.json", baseline)
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--output-dir", str(out)]
    tick, started = time.perf_counter(), utc()
    with (out / "stdout.log").open("w", encoding="utf-8") as stdout, (out / "stderr.log").open("w", encoding="utf-8") as stderr:
        try:
            completed = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=120)
            code, timed_out = completed.returncode, False
        except subprocess.TimeoutExpired:
            code, timed_out = 124, True
    write_json(out / "execution.json", {"argv": command, "started_utc": started, "ended_utc": utc(),
                                        "elapsed_seconds": time.perf_counter() - tick, "budget_seconds": 120,
                                        "exit_code": code, "timed_out": timed_out,
                                        "method": "metadata_only_no_create_shape", "outer_argv": sys.argv})
    print((out / "stdout.log").read_text(encoding="utf-8"))
    print((out / "stderr.log").read_text(encoding="utf-8"), file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
