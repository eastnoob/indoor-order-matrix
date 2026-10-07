"""Capture actual private B2 diagnostics from one bounded real-input ingress."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT = "8fd6f75d8d4444adac53588f642187d489e14831"
IFC_BYTES = 408617800
IFC_SHA256 = "018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240"
sys.path.insert(0, str(ROOT))


def utc() -> str:
    """Return an explicit UTC timestamp independent of the host timezone."""
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    """Read UTF-8 evidence, tolerating a Windows-created BOM."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    """Write stable diagnostic JSON without changing any product serializer."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def fingerprint(path: Path) -> dict:
    """Record bytes and a streaming SHA-256 for a local evidence file."""
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest}


def imported_modules() -> dict:
    """Identify the actual executed adapter/view dependencies and checkpoint bytes."""
    modules = {}
    for name in ("adapters.ifc_bonsai", "adapters.blender_geometry",
                 "features.neutral_scene_views", "features.scene_contract",
                 "features.geometry_views", "features.geometry_substitutes",
                 "features.group_self_description", "features.analysis_substitute_discovery"):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        record = fingerprint(path)
        # Compare imported bytes with Git, so a dirty or foreign module cannot
        # masquerade as the newly checkpointed private implementation.
        committed = subprocess.check_output(
            ["git", "show", f"{CHECKPOINT}:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT)
        record["checkpoint_blob_sha256"] = hashlib.sha256(committed).hexdigest()
        # Existing Windows files have CRLF although autocrlf is disabled; raw
        # hashes stay exact, and only CRLF->LF is excluded from content equality.
        normalized = path.read_bytes().replace(b"\r\n", b"\n")
        record["worktree_lf_sha256"] = hashlib.sha256(normalized).hexdigest()
        record["equality_normalization"] = "CRLF to LF only"
        record["matches_checkpoint"] = normalized == committed.replace(b"\r\n", b"\n")
        assert record["matches_checkpoint"], name
        modules[name] = record
    return modules


def check_contract(scene, view: dict, b2: dict, out: Path) -> dict:
    """Assert observable B2 refusal and occupancy without inventing live branches."""
    from features.group_self_description import _json_ready

    geometry_ids = {item.id for item in scene.geometries}
    sources = {item.id: item for item in scene.source_objects}
    projected = {item["id"]: item for item in view["physical_occupancy"]}
    structural = []
    for source in scene.source_objects:
        if source.source_role not in {"wall", "column", "door"}:
            continue
        record = projected.get(source.id)
        structural.append({"source": source.to_dict(), "projected": record is not None,
                           "omission_reason": None if record else "no_physical_projection",
                           "uncertainties": [u.to_dict() for u in source.uncertainties]})
        if record is None:
            continue
        assert set(record["_source_geometry_refs"]) <= geometry_ids
        matching = [row for row in b2["physical_occupancy"]
                    if row["source_id"] == source.source_id
                    and row["geometry_refs"] == list(source.geometry_refs)]
        assert len(matching) == 1 and matching[0]["included"] is True, source.id
    # Save omissions alongside successful rows; an empty success list is not
    # evidence that all expected structural sources survived projection.
    write_json(out / "structural_projection_audit.json", structural)
    for support in b2["boundary_support"]:
        assert support["conditional_support"] is False
        assert support["reason"] == "b2_loop_closure_policy_deferred"
        assert all(ref in sources or ref in geometry_ids
                   or any(s.source_id == ref for s in sources.values())
                   for ref in support["source_refs"])
    assert scene.analysis_domain is None
    assert b2["domain_scope"]["availability"] == "not_available"
    assert not b2["domain_scope"]["shell_record_ids"]
    assert view["_analysis_view"]["domain_available"] is False
    assert view["_analysis_view"]["view_bounds_basis"] == "scene_geometry_fallback_not_analysis_domain"
    assert b2["candidate_promotion"]["status"] == "refused"
    assert b2["candidate_polygon_validity"]["status"] == "not_available"
    assert b2["source_components"]["status"] == "not_available"
    assert b2["downstream"] == {"subtraction": "refused", "free_space": "not_evaluated", "route": "not_evaluated"}
    assert scene.openings == () and b2["openings"] == []
    public_projection = _json_ready({"_analysis_view": view["_analysis_view"],
                                    "uncertainties": view["uncertainties"]})
    assert "b2_boundary_diagnostics" not in json.dumps(public_projection)
    return {"assertions": "pass", "structural_sources": len(structural),
            "projected_structural_sources": sum(row["projected"] for row in structural),
            "structural_omissions": [row["source"]["id"] for row in structural if not row["projected"]],
            "opening_branches_live_coverage": "absent_zero_openings",
            "public_boundary_check": "existing_private_key_filter_only",
            "furniture_trend": "not_recomputed; typed substitutes remain required"}


def plot_geometry(records: list[dict], b2: dict, route: str, out: Path) -> None:
    """Render only this invocation's physical projection and actual refusal fields."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Patch
    from PIL import Image

    colors = {"wall": "#405675", "column": "#d58a22", "door": "#56856a"}
    fig = plt.figure(figsize=(16, 10), facecolor="#f6f7f9")
    ax = fig.add_axes((0.045, 0.14, 0.68, 0.72))
    key = fig.add_axes((0.76, 0.13, 0.23, 0.70))
    key.axis("off")
    counters = Counter()
    key_rows = []
    for record in records:
        role = record["role"]
        counters[role] += 1
        label = role[0].upper() + f"{counters[role]:02d}"
        # Components/holes come from the actual view, rather than bbox or old
        # candidate outlines. The same origin_offset applies to all records.
        for component in record["geometry_components"]:
            ax.add_patch(Polygon(component["exterior"], closed=True, facecolor=colors[role],
                                 edgecolor=colors[role], linewidth=0.5, alpha=0.82))
            for hole in component["holes"]:
                ax.add_patch(Polygon(hole, closed=True, facecolor="#f6f7f9", edgecolor=colors[role]))
        xs, ys = zip(*record["points"])
        ax.annotate(label, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2),
                    xytext=(3, 4), textcoords="offset points", fontsize=9, weight="bold",
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1})
        identity = record.get("identity", {})
        key_rows.append(f"{label}  #{identity.get('step_id', '?')}  {identity.get('global_id', record['id'])[:10]}")
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.margins(0.035)
    ax.set_xlabel("Analysis-view X (m; shifted world XY)")
    ax.set_ylabel("Analysis-view Y (m)")
    ax.grid(alpha=0.15)
    ax.legend(handles=[Patch(color=v, label=f"{k}: physical occupancy") for k, v in colors.items()],
              loc="lower left", fontsize=10)
    key.text(0, 1, "KEY: label / IFC STEP / GlobalId prefix\nFull identities in view_geometry.json\n\n" + "\n".join(key_rows),
             va="top", fontsize=10, family="monospace")
    fig.text(0.045, 0.955, "B2 SOURCE / PROVENANCE / REFUSAL VALIDATION", fontsize=19, weight="bold")
    fig.text(0.045, 0.915, f"{route.upper()}  |  accepted IFC SHA-256 018fca31c0d5...  |  structural subset", fontsize=11)
    fig.text(0.045, 0.075, "NO QUALIFIED ANALYSIS DOMAIN    |    NO FREE-SPACE / ROUTE RESULT", fontsize=16, weight="bold", color="#a33b29")
    fig.text(0.045, 0.04, f"Occupancy retained; boundary_support conditional=False ({len(b2['boundary_support'])} sources). No contact / loop closure computed.", fontsize=11)
    fig.text(0.045, 0.017, "Diagnostic source geometry only. No new room partition. Live snapshot is unsaved; IFC geometry parity is unverified.", fontsize=10)
    fig.savefig(out / "b2_occupancy_refusal.png", dpi=150)
    plt.close(fig)
    with Image.open(out / "b2_occupancy_refusal.png") as png:
        png.load()
        assert png.size == (2400, 1500)


def probe(args) -> None:
    """Invoke the existing loader and canonical view, retaining original failures."""
    from adapters.blender_geometry import load_blender_neutral_scene
    from adapters.ifc_bonsai import load_ifc_neutral_scene
    from features.neutral_scene_views import analysis_scene_view

    out = args.output_dir
    write_json(out / "executed_modules.json", imported_modules())
    write_json(out / "runner_identity.json", {"checkpoint_commit": CHECKPOINT,
               "runner": fingerprint(Path(__file__)), "python": sys.executable, "started_utc": utc()})
    snapshot = read_json(args.snapshot) if args.snapshot else None
    source = args.source if snapshot is None else Path(snapshot["source_ifc"]["path"])
    source_fp = fingerprint(source)
    assert (source_fp["bytes"], source_fp["sha256"]) == (IFC_BYTES, IFC_SHA256)
    write_json(out / "input_provenance.json", {"source_ifc": source_fp, "route": args.route,
               "snapshot": fingerprint(args.snapshot) if snapshot else None,
               "live_identity": snapshot["identity"] if snapshot else None,
               "checkpoint_commit": CHECKPOINT})
    print(f"{utc()} loader_start route={args.route}", flush=True)
    if args.route == "native":
        # No selectors, fabricated domain ID, injected module or hybrid shortcut.
        scene = load_ifc_neutral_scene(source)
        identities = {}
    else:
        ids = [row["id"] for row in snapshot["objects"]]
        scene = load_blender_neutral_scene(snapshot, mode="blender_geometry", selected_ids=ids, roles=snapshot["roles"])
        identities = {"blender-object:" + row["object_id"]: row for row in snapshot["source_scope"] if row["status"] == "present"}
        assert all(item.source_id is None for item in scene.source_objects)
        assert len(scene.source_objects) == len(ids)
    print(f"{utc()} loader_returned sources={len(scene.source_objects)} geometries={len(scene.geometries)}", flush=True)
    view = analysis_scene_view(scene)
    b2 = view["_analysis_view"]["b2_boundary_diagnostics"]
    # Write real output before assertions, preserving a minimal reproduction if
    # the observed contract differs from the bounded expectation.
    write_json(out / "b2_boundary_diagnostics.json", b2)
    geometry = []
    for record in view["physical_occupancy"]:
        if record["role"] in {"wall", "column", "door"}:
            geometry.append({key: record[key] for key in ("id", "role", "points", "geometry_components", "_source_geometry_refs", "_neutral_source_id")} | {"identity": identities.get(record["id"], {})})
    write_json(out / "view_geometry.json", {"records": geometry, "origin_offset": view["_analysis_view"]["origin_offset"],
               "analysis_plane": scene.context.analysis_plane.to_dict()})
    write_json(out / "scene_summary.json", {"context": scene.context.to_dict(), "source_count": len(scene.source_objects),
               "geometry_count": len(scene.geometries), "roles": dict(Counter(s.source_role for s in scene.source_objects)),
               "uncertainties": [u.to_dict() for u in scene.uncertainties], "opening_count": len(scene.openings),
               "domain": scene.analysis_domain.to_dict() if scene.analysis_domain else None})
    checks = check_contract(scene, view, b2, out)
    plot_geometry(geometry, b2, args.route, out)
    write_json(out / "validation.json", checks)
    print(f"{utc()} actual_b2_returned {json.dumps(checks)}", flush=True)


def main() -> int:
    """Supervise one fresh run, capping only the native attempt at 300 seconds."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=("native", "blender"), required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if (args.route == "native" and not args.source) or (args.route == "blender" and not args.snapshot):
        parser.error("native requires --source; blender requires --snapshot")
    if args.worker:
        try:
            probe(args)
        except Exception as error:
            write_json(args.output_dir / "exception.json", {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
            raise
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:], "--worker"]
    start, tick = utc(), time.monotonic()
    timed_out = False
    budget = 300 if args.route == "native" else 180
    with (args.output_dir / "stdout.log").open("wb") as stdout, (args.output_dir / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            timed_out = True
            # The worker uses native libraries in this process, not the user's
            # Blender; kill only the PID started above and retain partial logs.
            process.kill()
            code = process.wait()
    execution = {"route": args.route, "parent_argv": sys.argv, "worker_argv": command, "cwd": str(ROOT),
                 "started_utc": start, "ended_utc": utc(), "elapsed_seconds": time.monotonic() - tick,
                 "budget_seconds": budget, "worker_pid": process.pid, "worker_exit_code": code, "timed_out": timed_out,
                 "coverage": "not_verified_timeout" if timed_out else ("actual_b2_exercised" if code == 0 else "failed_attempt"),
                 "checkpoint_commit": CHECKPOINT}
    write_json(args.output_dir / "execution.json", execution)
    print(json.dumps(execution), flush=True)
    return 124 if timed_out else code


if __name__ == "__main__":
    raise SystemExit(main())
