"""Build three provisional closed 3D convex mesh substitutes from frozen sources."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import scipy
from scipy.spatial import ConvexHull

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.design.space_field.render_b3_deferred_display_hulls import GROUPS
from scripts.design.space_field.render_b3_unresolved_source_views import (
    BODY, COLORS, ROOT, fingerprint, load_inputs,
)

METHOD = "scipy.spatial.ConvexHull on all full-height world-XYZ vertices per complete group; Qt triangulation"
LIMIT = "User-selected convex approximation fills all internal gaps/concavities; not original exact physical material."


def check_mesh(vertices, faces, expected_volume):
    """Check the generated closed convex mesh's outward winding and signed volume."""
    assert vertices.ndim == 2 and vertices.shape[1] == 3 and np.isfinite(vertices).all()
    assert faces.ndim == 2 and faces.shape[1] == 3 and faces.dtype.kind in "iu"
    assert faces.min() >= 0 and faces.max() < len(vertices)
    triangles = vertices[faces]
    center = vertices.mean(axis=0)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    # A convex hull's vertex mean is interior, so every outward facet faces away from it.
    assert (np.einsum("ij,ij->i", normals, triangles.mean(axis=1) - center) > 0).all()
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    _, inverse, incidence = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    assert (incidence == 2).all()
    directions = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    assert (np.bincount(inverse, weights=directions) == 0).all()
    # Centered tetrahedra avoid cancellation from large world-coordinate offsets.
    centered = triangles - center
    volume = float(np.einsum("ij,ij->i", centered[:, 0],
                            np.cross(centered[:, 1], centered[:, 2])).sum() / 6)
    assert volume > 0 and np.isclose(volume, expected_volume, rtol=1e-10, atol=1e-12)
    return {"vertex_count": len(vertices), "triangle_count": len(faces),
            "edge_count": len(incidence), "all_edges_two_incident_faces": True,
            "consistent_outward_winding": True, "proxy_volume_m3": volume,
            "volume_matches_qhull": True}


def convex_mesh(points):
    """Triangulate a real XYZ convex hull without extrusion, jitter or source repair."""
    hull = ConvexHull(points)
    faces = hull.simplices.copy()
    triangles = points[faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    # Qhull supplies outward plane normals but its simplex index order is unspecified.
    reverse = np.einsum("ij,ij->i", normals, hull.equations[:, :3]) < 0
    faces[reverse] = faces[reverse][:, [0, 2, 1]]
    used, compact_faces = np.unique(faces, return_inverse=True)
    assert set(used) == set(hull.vertices)
    vertices = points[used].copy()
    faces = compact_faces.reshape((-1, 3))
    checks = check_mesh(vertices, faces, hull.volume)
    return {"vertices": vertices, "faces": faces, "checks": checks}


def self_check():
    """Verify a tetrahedron's convex volume is unchanged by an interior point."""
    points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.], [.1, .1, .1]])
    mesh = convex_mesh(points)
    assert mesh["checks"]["vertex_count"] == 4 and mesh["checks"]["triangle_count"] == 4
    assert np.isclose(mesh["checks"]["proxy_volume_m3"], 1 / 6, rtol=1e-12, atol=0)
    return {"tetrahedron_with_interior_point": "passed", "expected_volume_m3": 1 / 6,
            **mesh["checks"]}


def build_proxies(meshes):
    """Keep exact counter and complete assembly memberships as three separate proxies."""
    assert {key: steps for key, (_, steps) in GROUPS.items()} == {
        "counter_1992252": (1992252,),
        "assembly_A": (2032485, 2053009, 2082638),
        "assembly_B": (3269286, 3237875, 3236022),
    }
    proxies = {}
    for key, (title, steps) in GROUPS.items():
        points = np.concatenate([meshes[step]["points"] for step in steps])
        proxies[key] = {"title": title, "steps": steps,
                        "original_bounds_world_m": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
                        **convex_mesh(points)}
    return proxies


def write_obj(path, key, proxy):
    """Export an ordinary world-metre OBJ with one object and outward triangle faces."""
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(f"# World XYZ metres; provisional convex mesh, analysis enrollment deferred\no {key}\n")
        for vertex in proxy["vertices"]:
            stream.write("v " + " ".join(format(float(value), ".17g") for value in vertex) + "\n")
        for face in proxy["faces"]:
            stream.write("f " + " ".join(str(int(index) + 1) for index in face) + "\n")


def render_preview(path, meshes, proxies):
    """Show original captured triangles inside translucent faceted 3D convex meshes."""
    fig = plt.figure(figsize=(18, 9))
    fig.subplots_adjust(left=.01, right=.99, bottom=.23, top=.85, wspace=.03)
    for index, proxy in enumerate(proxies.values(), 1):
        ax = fig.add_subplot(1, 3, index, projection="3d", proj_type="ortho")
        for step in proxy["steps"]:
            ax.add_collection3d(Poly3DCollection(meshes[step]["triangles"], facecolors=COLORS[step],
                                                edgecolors="none", linewidths=0, alpha=.7))
        ax.add_collection3d(Poly3DCollection(proxy["vertices"][proxy["faces"]],
                                            facecolors="#17A6A1", edgecolors="#087F8C",
                                            linewidths=.6, alpha=.18))
        low, high = np.array(proxy["original_bounds_world_m"])
        padding = .08 * max(high - low)
        low, high = low - padding, high + padding
        ax.set(xlim=(low[0], high[0]), ylim=(low[1], high[1]), zlim=(low[2], high[2]),
               xlabel="World X (m)", ylabel="World Y (m)", zlabel="World Z (m)")
        ax.set_box_aspect(high - low)
        ax.view_init(elev=23, azim=-58)
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.set_major_locator(MaxNLocator(nbins=3))
        ax.tick_params(labelsize=8)
        ax.set_title(proxy["title"] + "\n" + " / ".join(f"#{step}" for step in proxy["steps"]), fontsize=12)
        ax.text2D(.04, .94, f"Proxy volume: {proxy['checks']['proxy_volume_m3']:.3f} m³",
                  transform=ax.transAxes, ha="left", va="top", fontsize=10,
                  bbox={"facecolor": "white", "edgecolor": "#087F8C", "alpha": .85})
    handles = [Patch(color=COLORS[step], label=f"Source #{step}")
               for step in sorted({step for proxy in proxies.values() for step in proxy["steps"]})]
    handles.append(Patch(facecolor="#17A6A1", edgecolor="#087F8C", alpha=.3, label="3D convex mesh proxy"))
    fig.suptitle("Three closed 3D convex mesh proxies | original sources + translucent hull facets", fontsize=17)
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=10, bbox_to_anchor=(.5, .08))
    fig.text(.5, .06, "Equal X/Y/Z metre scale per orthographic panel; panel zoom differs. Overall-analysis enrollment remains deferred.",
             ha="center", fontsize=10)
    fig.text(.5, .025, LIMIT, ha="center", fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    """Write a unique mesh/preview package with focused generated-geometry checks."""
    assert __debug__, "Input and geometry checks require ordinary Python execution"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "outputs/design/b3_deferred_convex_meshes" / f"run_{stamp}_{uuid.uuid4().hex[:6]}"
    out.mkdir(parents=True, exist_ok=False)
    execution = {"status": "running", "output": str(out)}
    try:
        fixture_checks = self_check()
        _, _, meshes, refs, _ = load_inputs()
        proxies = build_proxies(meshes)
        records = []
        for key, proxy in proxies.items():
            write_obj(out / f"{key}.obj", key, proxy)
            records.append({"id": key, "name": proxy["title"], "obj": f"{key}.obj",
                            "proxy_role": "provisional_3d_convex_mesh_substitute",
                            "analysis_enrollment": "deferred_excluded",
                            "sources": [{"step_id": step, "global_id": meshes[step]["source"]["global_id"],
                                         "body_step": BODY[step], "capture": meshes[step]["capture_ref"],
                                         "status": meshes[step]["source"]["status"]} for step in proxy["steps"]],
                            "original_bounds_world_m": proxy["original_bounds_world_m"],
                            "observed_source_z_range_m": [bound[2] for bound in proxy["original_bounds_world_m"]],
                            "generated_mesh_checks": proxy["checks"]})
        metadata = {"method": METHOD, "scipy_version": scipy.__version__, "limit": LIMIT,
                    "frame": {"units": "m", "coordinates": "world XYZ", "source_transform_already_applied": True},
                    "qhull_random_perturbation_or_repair": "none; no QJ or custom options",
                    "user_scope": "three provisional ordinary mesh substitutes; future dedicated analysis enrollment deferred",
                    "groups": records}
        (out / "mesh_proxies.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        render_preview(out / "convex_mesh_preview.png", meshes, proxies)
        manifest = {"limit": LIMIT, "inputs": refs, "code": fingerprint(Path(__file__)),
                    "verified_loader": fingerprint(ROOT / "scripts/design/space_field/render_b3_unresolved_source_views.py"),
                    "group_definitions": fingerprint(ROOT / "scripts/design/space_field/render_b3_deferred_display_hulls.py"),
                    "method": METHOD, "tetrahedron_self_check": fixture_checks,
                    "input_and_exact_group_membership_assertions": "passed",
                    "generated_mesh_checks": {key: proxy["checks"] for key, proxy in proxies.items()},
                    "artifacts": [fingerprint(path) for path in sorted(out.iterdir())],
                    "source_live_analysis_occupancy_changes": "none",
                    "ifc_parse_tessellation_blender_field_generation": "not_invoked"}
        (out / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        execution.update(status="completed", objects=3, images=1, input_assertions="passed",
                         tetrahedron_self_check="passed", generated_mesh_checks="passed")
    except Exception as error:
        execution.update(status="failed", error=f"{type(error).__name__}: {error}")
    (out / "execution.json").write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(execution))
    return 0 if execution["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
