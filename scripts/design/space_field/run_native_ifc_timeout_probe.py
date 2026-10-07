"""Observe a bounded native IFC load or run its clean adapter-to-B2 handoff."""

from __future__ import annotations

import argparse
from collections import Counter
import cProfile
from datetime import datetime, timezone
import faulthandler
import functools
import hashlib
import importlib
import json
from pathlib import Path
import pstats
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
EXPECTED = (408617800, "018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240")


def utc():
    """Return an explicit UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def fingerprint(path):
    """Fingerprint exact local bytes without loading the IFC into memory."""
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest}


def write_json(path, value):
    """Persist diagnostic JSON independently of product serializers."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def worker(args):
    """Call the original loader, with observation-only wrappers in baseline mode."""
    from adapters import ifc_bonsai as adapter
    from features import neutral_scene_views as views
    import ifcopenshell
    import ifcopenshell.geom

    out = args.output_dir
    source_fp = fingerprint(args.source)
    assert (source_fp["bytes"], source_fp["sha256"]) == EXPECTED
    modules = {}
    for name in ("adapters.ifc_bonsai", "features.neutral_scene_views", "features.scene_contract",
                 "features.geometry_views", "features.geometry_substitutes", "features.analysis_substitute_discovery"):
        modules[name] = fingerprint(Path(importlib.import_module(name).__file__))
    write_json(out / "identity.json", {"source": source_fp, "modules": modules,
               "python": sys.version, "executable": sys.executable, "ifcopenshell": ifcopenshell.version,
               "argv": sys.argv, "utc": utc(), "monotonic": time.monotonic(),
               "base_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "runner": fingerprint(Path(__file__))})
    events = (out / "events.jsonl").open("a", encoding="utf-8", buffering=1)
    counts = Counter()
    profile = cProfile.Profile()
    last_dump = time.monotonic()

    def event(stage, phase, **data):
        """Flush boundaries so termination preserves the last in-flight work."""
        events.write(json.dumps({"stage": stage, "phase": phase, "utc": utc(),
                                "monotonic": time.monotonic(), **data}) + "\n")

    def wrap(owner, name):
        """Observe exactly one original call without changing its arguments or errors."""
        original = getattr(owner, name)

        @functools.wraps(original)
        def observed(*positional, **keywords):
            """Record call identity, completion, timing and periodically saved profile."""
            nonlocal last_dump
            counts[name] += 1
            detail = {}
            if name in {"_native_mesh_record", "create_shape"}:
                entity = positional[0 if name == "_native_mesh_record" else 1]
                rep = positional[4] if name == "_native_mesh_record" and len(positional) > 4 else (positional[2] if name == "create_shape" and len(positional) > 2 else None)
                detail = {"step_id": entity.id(), "global_id": getattr(entity, "GlobalId", None),
                          "class": entity.is_a(), "representation": getattr(rep, "RepresentationIdentifier", None),
                          "representation_step_id": rep.id() if rep is not None else None}
            if name == "_triangle_topology_flags":
                detail["triangle_count"] = len(positional[0])
            tick = time.perf_counter()
            event(name, "enter", call=counts[name], **detail)
            try:
                result = original(*positional, **keywords)
            except BaseException as error:
                event(name, "exception", error=repr(error), elapsed=time.perf_counter() - tick, **detail)
                raise
            event(name, "exit", elapsed=time.perf_counter() - tick, **detail)
            if name == "_open_source":
                inventory = [{"step_id": item.id(), "global_id": getattr(item, "GlobalId", None),
                              "class": item.is_a(), "representations": [
                                  {"step_id": rep.id(), "identifier": rep.RepresentationIdentifier}
                                  for rep in (getattr(getattr(item, "Representation", None), "Representations", ()) or ())]}
                             for item in result.by_type("IfcProduct")]
                write_json(out / "native_inventory.json", inventory)
            if time.monotonic() - last_dump > 30:
                profile.dump_stats(str(out / "partial_profile.pstats"))
                write_json(out / "call_counts.json", counts)
                last_dump = time.monotonic()
            return result

        setattr(owner, name, observed)

    if args.mode == "baseline":
        for name in ("_open_source", "_native_length_unit", "_native_group_records", "_native_grid_records",
                     "_native_material_records", "_native_mesh_record", "_mesh_record", "_triangle_topology_flags",
                     "_native_opening_records", "_native_surface_records", "_native_world_transform",
                     "_native_om_properties", "_native_affordance_records", "_native_analysis_domain",
                     "_scene_from_native_ifc", "_scene_from_records"):
            wrap(adapter, name)
        wrap(ifcopenshell.geom, "create_shape")
        profile.enable()
        faulthandler.dump_traceback_later(30, repeat=True)
    try:
        tick = time.perf_counter()
        event("loader", "enter")
        scene = adapter.load_ifc_neutral_scene(args.source)
        event("loader", "exit", elapsed=time.perf_counter() - tick,
              sources=len(scene.source_objects), geometries=len(scene.geometries))
        # Save coverage before projection, so a later view timeout does not hide
        # the independently completed native extraction milestone.
        write_json(out / "scene_sources.json", [item.to_dict() for item in scene.source_objects])
        write_json(out / "scene_summary.json", {"context": scene.context.to_dict(),
                   "source_count": len(scene.source_objects), "geometry_count": len(scene.geometries),
                   "roles": Counter(s.source_role for s in scene.source_objects),
                   "geometries": [{"id": g.id, "vertices": len(g.vertices), "triangles": len(g.triangle_indices),
                                   "representation": g.source_representation_id, "units": g.units,
                                   "provenance": dict(g.local_to_world_provenance)} for g in scene.geometries],
                   "uncertainties": [u.to_dict() for u in scene.uncertainties]})
        if args.mode == "clean":
            tick = time.perf_counter()
            event("view_b2", "enter")
            view = views.analysis_scene_view(scene)
            event("view_b2", "exit", elapsed=time.perf_counter() - tick)
            b2 = view["_analysis_view"]["b2_boundary_diagnostics"]
            write_json(out / "b2_boundary_diagnostics.json", b2)
            from scripts.design.space_field.run_b2_real_input_validation import check_contract
            write_json(out / "validation.json", check_contract(scene, view, b2, out))
    except BaseException as error:
        write_json(out / "exception.json", {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
        raise
    finally:
        if args.mode == "baseline":
            profile.disable()
            profile.dump_stats(str(out / "final_profile.pstats"))
            with (out / "profile.txt").open("w", encoding="utf-8") as stream:
                pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(50)
            faulthandler.cancel_dump_traceback_later()
        write_json(out / "call_counts.json", counts)
        events.close()


def main():
    """Supervise only this task's child with separate loader and view deadlines."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("baseline", "clean"), required=True)
    parser.add_argument("--native-budget", type=float, default=300)
    parser.add_argument("--view-budget", type=float, default=180)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 < args.native_budget <= 600 or not 0 < args.view_budget <= 180:
        parser.error("native budget must be <=600s; view budget <=180s")
    if args.worker:
        worker(args)
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, args.output_dir / "runner_snapshot.py")
    write_json(args.output_dir / "git_baseline.json", {key: subprocess.check_output(command, cwd=ROOT, text=True)
               for key, command in {"head": ["git", "rev-parse", "HEAD"], "branch": ["git", "branch", "--show-current"],
                                    "status": ["git", "status", "--porcelain=v1"], "index": ["git", "diff", "--cached", "--name-status"]}.items()})
    command = [sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:], "--worker"]
    start, tick = utc(), time.monotonic()
    deadline = tick + args.native_budget
    stage, timed_out = "loader", False
    with (args.output_dir / "stdout.log").open("wb") as stdout, (args.output_dir / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        while process.poll() is None:
            # Projection receives its own bounded budget only after the loader
            # emits a flushed return; no source filtering or backend change occurs.
            event_path = args.output_dir / "events.jsonl"
            if stage == "loader" and event_path.exists():
                for line in event_path.read_text(encoding="utf-8").splitlines():
                    if '"stage": "loader", "phase": "exit"' in line:
                        deadline = json.loads(line)["monotonic"] + args.view_budget
                        stage = "view_b2" if args.mode == "clean" else "serialization"
                        break
            if time.monotonic() >= deadline:
                timed_out = True
                process.kill()
                break
            time.sleep(1)
        code = process.wait()
    record = {"argv": command, "utc_start": start, "utc_end": utc(), "monotonic_start": tick,
              "elapsed_seconds": time.monotonic() - tick, "native_budget": args.native_budget,
              "view_budget": args.view_budget, "pid": process.pid, "exit_code": code,
              "timed_out": timed_out, "last_stage": stage, "instrumented": args.mode == "baseline"}
    write_json(args.output_dir / "execution.json", record)
    print(json.dumps(record), flush=True)
    return 124 if timed_out else code


if __name__ == "__main__":
    raise SystemExit(main())
