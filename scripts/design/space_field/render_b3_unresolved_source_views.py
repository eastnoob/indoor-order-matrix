"""Identify eight unresolved sources from frozen captured triangles without derivation."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LightSource
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.design.space_field.run_b3_real_field_diagnostic import draw_geometry

CAPTURE = ROOT / "outputs/design/b3_real_source_field/run_001"
SECTIONS = ROOT / "outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/source_sections.json"
GROUPS = {
    "door_6231": ("Door", (6231,)),
    "counter_1992252": ("BarCounterAndShelves", (1992252,)),
    "assembly_A": ("Assembly A", (2032485, 2053009, 2082638)),
    "assembly_B": ("Assembly B", (3269286, 3237875, 3236022)),
}
COLORS = {6231: "#0072B2", 1992252: "#D55E00", 2032485: "#E69F00", 2053009: "#009E73",
          2082638: "#CC79A7", 3269286: "#B29A00", 3237875: "#56B4E9", 3236022: "#7950A5"}
BODY = {6231: 15562, 1992252: 1996033, 2032485: 2051205, 2053009: 2082616,
        2082638: 2084469, 3269286: 3288006, 3237875: 3267482, 3236022: 3237853}
LIMIT = "Captured-source identification view; not native equivalence or occupancy proof."


def fingerprint(path):
    """Retain byte identity for each consumed input and newly written image."""
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}


def read_verified(path, expected):
    """Assert frozen bytes before decoding a capture or accepted source reference."""
    actual = fingerprint(path)
    assert (actual["bytes"], actual["sha256"]) == (expected["bytes"], expected["sha256"]), path
    return json.loads(path.read_text(encoding="utf-8")), actual


def load_inputs():
    """Load only settled S3 and the eight explicitly requested frozen capture meshes."""
    sections, section_ref = read_verified(SECTIONS, {
        "bytes": 11397078, "sha256": "57181d1dcf9b57b9386c2be036cfbdedddb641ab5242c9fdf1d01e5d7c7a56e7"})
    scope, scope_ref = read_verified(CAPTURE / "s3_scope.json", {
        "bytes": 244945, "sha256": "94a28a5f513091e683303faf091081d519769b5a38980cff2438d91a2cfc5591"})
    domain = shape(scope["candidate"]["outline"])
    assert domain.is_valid and domain.geom_type == "Polygon" and len(domain.interiors) == 2
    assert scope["candidate"]["area_m2"] == 206.5209234821732
    assert scope["frame"]["units"] == "m" and scope["frame"]["datum_m"] == 0
    assert sections["primary_plane_world_z_m"] == 1.6
    records = {row["step_id"]: row for row in sections["records"]}
    meshes, refs = {}, [section_ref, scope_ref]
    for step in COLORS:
        row = records[step]
        assert row["status"] == "unresolved_open_or_nonmanifold"
        assert row["scope"]["status"] == "positive_area_overlap"
        capture, ref = read_verified(CAPTURE / row["geometry"]["path"], row["geometry"])
        assert capture["id"] == row["id"] == f"live-step-{step}"
        assert capture["representation_id"] == str(BODY[step])
        assert capture["units"] == "m" and capture["transform_applied"] is True
        points, faces = np.asarray(capture["vertices"], dtype=float), np.asarray(capture["triangles"])
        assert points.ndim == 2 and points.shape[1] == 3 and np.isfinite(points).all()
        assert faces.ndim == 2 and faces.shape[1] == 3 and faces.dtype.kind in "iu" and len(faces)
        assert faces.min() >= 0 and faces.max() < len(points)
        # Use every original captured triangle, preserving openings and disconnected parts.
        meshes[step] = {"points": points, "triangles": points[faces], "source": row, "capture_ref": ref}
        refs.append(ref)
    outside = [records[step] for step in (43654, 49645, 55636, 61627, 67618)]
    assert all(row["status"] == "unresolved_open_or_nonmanifold" for row in outside)
    return domain, scope, meshes, refs, outside


def group_bounds(meshes, steps):
    """Find camera bounds only, without creating a source envelope or replacement mesh."""
    points = np.concatenate([meshes[step]["points"] for step in steps])
    return points.min(axis=0), points.max(axis=0)


def plan_sources(ax, meshes, steps):
    """Draw original triangles in XY as full-height source identification projections."""
    for step in steps:
        ax.add_collection(PolyCollection(meshes[step]["triangles"][:, :, :2],
                                         facecolor=COLORS[step], edgecolor="none", linewidth=0))
    ax.set_aspect("equal", adjustable="box")
    ax.set(xlabel="World X (m)", ylabel="World Y (m)")
    ax.grid(alpha=.18)


def render_plan(out, domain, meshes):
    """Locate all eight sources with historical S3 holes and separately labelled assemblies."""
    fig = plt.figure(figsize=(16, 10))
    ax = fig.add_axes((.055, .14, .61, .75))
    draw_geometry(ax, domain, "#edf1f2", fill=True)
    plan_sources(ax, meshes, COLORS)
    draw_geometry(ax, domain, "#344955", linewidth=1.3)
    for index, ring in enumerate(domain.interiors, 1):
        center = shape({"type": "Polygon", "coordinates": [list(ring.coords)]}).representative_point()
        ax.annotate(f"S3 hole {index}", (center.x, center.y), fontsize=9, ha="center",
                    bbox={"facecolor": "white", "edgecolor": "#344955", "alpha": .85})
    lower, upper = group_bounds(meshes, COLORS)
    xmin, ymin, xmax, ymax = domain.bounds
    ax.set(xlim=(min(xmin, lower[0]) - 1, max(xmax, upper[0]) + 1),
           ylim=(min(ymin, lower[1]) - 1.2, max(ymax, upper[1]) + 1))
    offsets = ((-100, -40), (-80, 45), (-80, -55), (25, 45))
    for (title, steps), offset in zip(GROUPS.values(), offsets):
        low, high = group_bounds(meshes, steps)
        center = (low + high) / 2
        ax.annotate(title + "\n" + " / ".join(f"#{step}" for step in steps), center[:2], xytext=offset,
                    textcoords="offset points", fontsize=10, ha="center",
                    arrowprops={"arrowstyle": "->", "color": "#344955"},
                    bbox={"facecolor": "white", "edgecolor": "#aab8bf", "alpha": .95})
    ax.set_title("Historical S3: 206.5209234821732 m², two holes\nFull-height XY source projections; not an eye-plane section", fontsize=12)
    for index, key in enumerate(("assembly_A", "assembly_B")):
        title, steps = GROUPS[key]
        detail = fig.add_axes((.73, .57 - index * .40, .24, .29))
        plan_sources(detail, meshes, steps)
        low, high = group_bounds(meshes, steps)
        detail.set(xlim=(low[0] - .18, high[0] + .18), ylim=(low[1] - .18, high[1] + .18))
        detail.set_title(title + " | XY detail", fontsize=11)
        detail.tick_params(labelsize=8)
        for step, offset in zip(steps, ((-55, 46), (35, -30), (30, 55))):
            points = meshes[step]["points"]
            center = (points.min(axis=0) + points.max(axis=0)) / 2
            detail.annotate(f"#{step}", center[:2], xytext=offset, textcoords="offset points", fontsize=9,
                            arrowprops={"arrowstyle": "->", "color": COLORS[step]},
                            bbox={"facecolor": "white", "edgecolor": COLORS[step], "alpha": .9})
    fig.suptitle("Eight unresolved sources | captured-source identification", fontsize=18, y=.98)
    handles = [Patch(color=COLORS[step], label=f"#{step} {meshes[step]['source']['name']}") for step in COLORS]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=9, bbox_to_anchor=(.5, .045))
    fig.text(.5, .018, LIMIT + " Identity colours only; surfaces are not clipped to S3.", ha="center", fontsize=10)
    fig.savefig(out / "plan_context.png", dpi=170)
    plt.close(fig)


def render_closeup(out, key, title, steps, meshes):
    """Show all captured surfaces from two orthographic angles with isotropic metre axes."""
    fig = plt.figure(figsize=(15, 8.5))
    low, high = group_bounds(meshes, steps)
    low[2], high[2] = min(low[2], 0., 1.6), max(high[2], 1.6)
    padding = .08 * max(high - low)
    low, high = low - padding, high + padding
    span = high - low
    for index, azimuth in enumerate((-58, 122), 1):
        ax = fig.add_subplot(1, 2, index, projection="3d", proj_type="ortho")
        for step in steps:
            ax.add_collection3d(Poly3DCollection(meshes[step]["triangles"], facecolors=COLORS[step],
                                                edgecolors=COLORS[step], linewidths=0, shade=True,
                                                lightsource=LightSource(azdeg=315, altdeg=45)))
        plane = [[low[0], low[1], 1.6], [high[0], low[1], 1.6],
                 [high[0], high[1], 1.6], [low[0], high[1], 1.6]]
        # The reference plane is a separate translucent overlay, never source material.
        ax.add_collection3d(Poly3DCollection([plane], facecolors="#30BFC5", edgecolors="#118188",
                                            linewidths=1, linestyles="--", alpha=.12))
        ax.set(xlim=(low[0], high[0]), ylim=(low[1], high[1]), zlim=(low[2], high[2]),
               xlabel="World X (m)", ylabel="World Y (m)", zlabel="World Z (m)")
        ax.set_box_aspect(span)
        ax.view_init(elev=23, azim=azimuth)
        ax.tick_params(labelsize=9)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=3))
        ax.set_title(f"View {index} | azimuth {azimuth}°", fontsize=12)
    fig.suptitle(title + " | " + " / ".join(f"#{step}" for step in steps), fontsize=18, y=.97)
    handles = [Patch(color=COLORS[step], label=f"#{step} {meshes[step]['source']['name']}") for step in steps]
    handles.append(Patch(facecolor="#30BFC5", alpha=.3, label="Reference plane: world z = 1.6 m"))
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=11, bbox_to_anchor=(.5, .065))
    fig.text(.5, .032, "Equal scale along X/Y/Z; zoom is specific to this object/assembly. All original triangles shown.", ha="center", fontsize=10)
    fig.text(.5, .009, LIMIT, ha="center", fontsize=10)
    fig.subplots_adjust(left=.01, right=.99, top=.88, bottom=.17, wspace=.03)
    fig.savefig(out / f"{key}.png", dpi=170)
    plt.close(fig)
    return {"steps": list(steps), "camera_bounds_world_m": [low.tolist(), high.tolist()],
            "projection": "orthographic", "azimuth_degrees": [-58, 122], "elevation_degrees": 23,
            "equal_xyz_metre_scale": True, "image": f"{key}.png"}


def main():
    """Write a unique bounded identification package with input assertions and provenance."""
    assert __debug__, "Input assertions require ordinary Python execution"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "outputs/design/b3_unresolved_source_views" / f"run_{stamp}_{uuid.uuid4().hex[:6]}"
    out.mkdir(parents=True, exist_ok=False)
    execution = {"status": "running", "output": str(out)}
    try:
        domain, scope, meshes, refs, outside = load_inputs()
        render_plan(out, domain, meshes)
        views = [render_closeup(out, key, title, steps, meshes) for key, (title, steps) in GROUPS.items()]
        manifest = {"schema": "b3-captured-source-identification/v1", "limit": LIMIT,
                    "inputs": refs, "code": fingerprint(Path(__file__)),
                    "plot_helper": fingerprint(ROOT / "scripts/design/space_field/run_b3_real_field_diagnostic.py"),
                    "domain": {"id": "S3", "area_m2": scope["candidate"]["area_m2"], "holes": 2,
                               "frame": scope["frame"], "vertical_extent": "unknown"},
                    "primary_plane_world_z_m": 1.6, "input_assertions": "passed",
                    "sources": [{"step_id": step, "global_id": mesh["source"]["global_id"],
                                 "body_step": BODY[step], "name": mesh["source"]["name"],
                                 "identity_color": COLORS[step], "triangle_count": len(mesh["triangles"]),
                                 "status": mesh["source"]["status"]} for step, mesh in meshes.items()],
                    "outside_windows_not_rendered": [{"step_id": row["step_id"], "status": row["status"],
                                                       "scope": row["scope"]} for row in outside],
                    "views": views, "artifacts": [fingerprint(path) for path in sorted(out.glob("*.png"))],
                    "mesh_changes": "none", "native_parsing_tessellation_blender_field_generation": "not_invoked"}
        (out / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        execution.update(status="completed", images=len(manifest["artifacts"]), input_assertions="passed")
    except Exception as error:
        execution.update(status="failed", error=f"{type(error).__name__}: {error}")
    (out / "execution.json").write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(execution))
    return 0 if execution["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
