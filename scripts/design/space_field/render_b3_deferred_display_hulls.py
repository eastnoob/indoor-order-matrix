"""Render display-only XY convex hulls for three deferred source groups."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
from shapely.geometry import MultiPoint, mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.design.space_field.render_b3_unresolved_source_views import (
    COLORS,
    ROOT,
    fingerprint,
    load_inputs,
    plan_sources,
)
from scripts.design.space_field.run_b3_real_field_diagnostic import draw_geometry


GROUPS = {
    "counter_1992252": ("Counter / shelves", (1992252,)),
    "assembly_A": ("Plant assembly A", (2032485, 2053009, 2082638)),
    "assembly_B": ("Plant assembly B", (3269286, 3237875, 3236022)),
}
LIMIT = (
    "Display-only full-height XY convex hull; not an eye-plane section, material, "
    "orientation inference, occupancy, or analysis enrollment."
)


def build_group_hulls(meshes):
    """Build one display hull from all world-XY vertices within each exact group."""
    assert {key: steps for key, (_, steps) in GROUPS.items()} == {
        "counter_1992252": (1992252,),
        "assembly_A": (2032485, 2053009, 2082638),
        "assembly_B": (3269286, 3237875, 3236022),
    }
    hulls = {}
    for key, (title, steps) in GROUPS.items():
        points = np.concatenate([meshes[step]["points"] for step in steps])
        hull = MultiPoint(points[:, :2]).convex_hull
        # The display summary must cover every member vertex without merging groups.
        assert hull.geom_type == "Polygon" and hull.is_valid
        assert hull.covers(MultiPoint(points[:, :2]))
        hulls[key] = {
            "title": title,
            "steps": steps,
            "points": points,
            "hull": hull,
        }
    return hulls


def render_summary(path, meshes, hulls):
    """Render original full-height projections beneath their separate display hulls."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 8))
    fig.subplots_adjust(left=.05, right=.985, bottom=.24, top=.84, wspace=.24)
    for ax, record in zip(axes, hulls.values()):
        plan_sources(ax, meshes, record["steps"])
        draw_geometry(ax, record["hull"], "#17A6A1", fill=True, alpha=.24, linewidth=2.4)
        draw_geometry(ax, record["hull"], "#087F8C", linewidth=2.0)
        minx, miny, maxx, maxy = record["hull"].bounds
        padding = max(maxx - minx, maxy - miny) * .12
        ax.set(xlim=(minx - padding, maxx + padding), ylim=(miny - padding, maxy + padding))
        ax.set_title(record["title"] + "\n" + " / ".join(f"#{step}" for step in record["steps"]),
                     fontsize=13)
        ax.text(.5, .02, f"Hull area: {record['hull'].area:.3f} m²",
                transform=ax.transAxes, ha="center", va="bottom", fontsize=10,
                bbox={"facecolor": "white", "edgecolor": "#86BDBA", "alpha": .9})
    source_handles = [Patch(color=COLORS[step], label=f"Source #{step}")
                      for step in sorted({step for record in hulls.values() for step in record["steps"]})]
    source_handles.append(Patch(facecolor="#17A6A1", edgecolor="#17A6A1", alpha=.24,
                                label="Display convex hull"))
    fig.suptitle("Deferred counter and plant assemblies | original XY projection + display hull",
                 fontsize=18)
    fig.legend(handles=source_handles, loc="lower center", ncol=4, fontsize=9,
               bbox_to_anchor=(.5, .075))
    fig.text(.5, .055, "Equal XY metre axes per panel; panel zoom differs. Hulls fill holes and concavities for display.",
             ha="center", fontsize=10)
    fig.text(.5, .025, LIMIT, ha="center", fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def serialize_hulls(path, hulls, meshes):
    """Write group membership, hull geometry, observed height range, and scope limits."""
    payload = {
        "schema": "b3-deferred-display-hulls/v1",
        "method": "MultiPoint(all full-height world-XY vertices per complete group).convex_hull",
        "scope": "display_only_deferred_sources",
        "limit": LIMIT,
        "analysis_participation": "unchanged_excluded",
        "groups": [],
    }
    for key, record in hulls.items():
        z_values = record["points"][:, 2]
        payload["groups"].append({
            "id": key,
            "title": record["title"],
            "step_ids": list(record["steps"]),
            "global_ids": [meshes[step]["source"]["global_id"] for step in record["steps"]],
            "observed_source_z_range_m": [float(z_values.min()), float(z_values.max())],
            "xy_hull": mapping(record["hull"]),
            "xy_hull_area_m2": record["hull"].area,
            "source_statuses": [meshes[step]["source"]["status"] for step in record["steps"]],
        })
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main():
    """Write one unique display-only hull package from frozen verified inputs."""
    assert __debug__, "Input assertions require ordinary Python execution"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "outputs/design/b3_deferred_display_hulls" / f"run_{stamp}_{uuid.uuid4().hex[:6]}"
    out.mkdir(parents=True, exist_ok=False)
    execution = {"status": "running", "output": str(out)}
    try:
        _, _, meshes, refs, _ = load_inputs()
        hulls = build_group_hulls(meshes)
        render_summary(out / "deferred_display_hulls.png", meshes, hulls)
        serialize_hulls(out / "display_hulls.json", hulls, meshes)
        manifest = {
            "schema": "b3-deferred-display-hull-package/v1",
            "limit": LIMIT,
            "inputs": refs,
            "code": fingerprint(Path(__file__)),
            "verified_loader": fingerprint(ROOT / "scripts/design/space_field/render_b3_unresolved_source_views.py"),
            "plot_helper": fingerprint(ROOT / "scripts/design/space_field/run_b3_real_field_diagnostic.py"),
            "groups": [{"id": key, "step_ids": list(record["steps"])} for key, record in hulls.items()],
            "input_assertions": "passed",
            "hull_membership_and_containment_checks": "passed",
            "artifacts": [fingerprint(out / "deferred_display_hulls.png"),
                          fingerprint(out / "display_hulls.json")],
            "source_mesh_changes": "none",
            "occupancy_live_analysis_promotion": "not_performed",
            "ifc_parsing_tessellation_blender_field_generation": "not_invoked",
        }
        (out / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        execution.update(status="completed", images=1, groups=3,
                         input_assertions="passed", hull_checks="passed")
    except Exception as error:
        execution.update(status="failed", error=f"{type(error).__name__}: {error}")
    (out / "execution.json").write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(execution))
    return 0 if execution["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
