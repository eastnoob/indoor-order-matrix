"""Execute the bounded D6 section, band, projection and triangle-query experiment.

All heights are explicit experiment arguments. This runner never creates an
AnalysisDomain, infers a room, modifies source geometry, or opens native IFC.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import traceback

import numpy as np
import shapely
from shapely.geometry import GeometryCollection, LineString, Polygon, box, mapping
from shapely.ops import polygonize_full, unary_union
import trimesh

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from adapters.blender_geometry import load_blender_neutral_scene
from adapters.ifc_bonsai import _triangle_topology_flags
from features.geometry_substitutes import mass_patch_from_mesh
from features.geometry_views import (
    _ray_intersection_distance, component_shape, occlusion_intersections,
    plan_projection, vertical_intervals_at,
)

SNAPSHOT = ROOT / "outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json"
SNAPSHOT_HASH = "c5659dcd99d8c4f20b97efd2cc37352d6305436e20e698ccbcf8c89abfe67867"
IFC_HASH = "018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240"
METHODS = ("section_at_1p5m", "finite_band_projection", "full_height_xy", "genuine_3d_reference")
COLORS = {"wall": "#306aa2", "column": "#df8624", "door": "#308765", "partition": "#ae4472", "beam": "#8255b2"}


def write_json(path, payload):
    """Write finite, stable JSON using LF line endings."""
    path.write_bytes((json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def fingerprint(path):
    """Stream file bytes without loading the large IFC into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(Path(path).resolve()), "bytes": Path(path).stat().st_size, "sha256": digest.hexdigest()}


def fixture_definitions():
    """Declare dimension-based oracles before any geometry algorithm runs."""
    return [
        {"id": "walls_columns", "boxes": [
            ["south_left", "wall", [0, 0, 0, 2.75, .25, 3]],
            ["south_right", "wall", [3.25, 0, 0, 6, .25, 3]],
            ["north", "wall", [0, 3.75, 0, 6, 4, 3]],
            ["west", "wall", [0, .25, 0, .25, 3.75, 3]],
            ["east", "wall", [5.75, .25, 0, 6, 3.75, 3]],
            ["boundary_column", "column", [2.75, 0, 0, 3.25, .25, 3]],
            ["interior_column", "column", [2.75, 1.75, 0, 3.25, 2.25, 3]]],
         "points": [[3.03, 2.01], [1.13, 1.37], [3.03, .11]],
         "segments": [[[1, 2.03, 1.5], [4, 2.03, 1.5]], [[1, 1, 1.5], [2, 1, 1.5]]],
         "semantics": "Boundary column contacts south walls; interior column remains mass. No room qualification."},
        {"id": "opening_lintel", "boxes": [
            ["host_left", "wall", [0, 0, 0, 1.5, .3, 3]],
            ["host_right", "wall", [2.5, 0, 0, 4, .3, 3]],
            ["lintel", "wall", [1.5, 0, 2.1, 2.5, .3, 3]]],
         "points": [[2.03, .13]],
         "segments": [[[2.03, -1, 1.5], [2.03, 1, 1.5]], [[2.03, -1, 2.5], [2.03, 1, 2.5]]],
         "opening": {"id": "authored_void", "host_refs": ["host_left", "host_right", "lintel"], "bounds_m": [1.5, 0, 0, 2.5, .3, 2.1], "scenario": "open_no_door"}},
        {"id": "low_partition", "boxes": [["low", "partition", [1, 1, 0, 3, 1.25, 1]]],
         "points": [[2.03, 1.13]],
         "segments": [[[2.03, 0, .5], [2.03, 2, .5]], [[2.03, 0, 1.5], [2.03, 2, 1.5]]]},
        {"id": "overhead_bridge", "boxes": [["bridge", "beam", [1, 1, 2.4, 3, 2, 2.8]]],
         "points": [[2.03, 1.37]],
         "segments": [[[2.03, 0, 1.5], [2.03, 3, 1.5]], [[2.03, 0, 2.6], [2.03, 3, 2.6]], [[2.03, 0, 2.6], [2.03, .8, 2.6]]]},
    ]


def analytic_segment(bounds, start, end):
    """Find segment/box surface parameters by independent slab algebra."""
    lower, upper = -float("inf"), float("inf")
    for axis in range(3):
        delta = end[axis] - start[axis]
        if delta == 0:
            if not bounds[axis] < start[axis] < bounds[axis + 3]:
                return []
        else:
            values = sorted(((bounds[axis] - start[axis]) / delta, (bounds[axis + 3] - start[axis]) / delta))
            lower, upper = max(lower, values[0]), min(upper, values[1])
    return [value for value in (lower, upper) if lower < upper and 0 <= value <= 1]


def dimension_oracles(definitions):
    """Archive independently known numeric expectations before query execution."""
    return {"walls_columns": {"section_band_full_area_m2": 5, "components": 2, "holes": 1, "disjoint_volume_m3": 15,
                               "boundary_column_contacts": ["south_left", "south_right"], "interior_column_remains_occupancy": True},
            "opening_lintel": {"section_band_area_m2": .9, "section_band_components": 2, "full_area_m2": 1.2,
                               "full_components": 1, "opening_vertical_interval_m": [2.1, 3], "disjoint_volume_m3": 2.97},
            "low_partition": {"section_area_m2": 0, "band_full_area_m2": .5, "vertical_interval_m": [0, 1], "volume_m3": .5},
            "overhead_bridge": {"section_band_area_m2": 0, "full_area_m2": 2, "vertical_interval_m": [2.4, 2.8], "volume_m3": .8},
            "formulas": {"plan": "rectangle union selected by declared z range", "volume": "sum dx*dy*dz of disjoint boxes",
                         "vertical": "[zmin,zmax] iff xmin<x<xmax and ymin<y<ymax",
                         "segment": "independent axis slab interval intersection, surface parameters restricted to [0,1]"},
            "fixture_count": len(definitions)}


def qualify(patch, mesh):
    """Report measured topology separately from unchanged transport flags."""
    manifold, closed = _triangle_topology_flags(patch.triangle_indices)
    return {"source_is_closed": patch.is_closed, "source_is_manifold": patch.is_manifold,
            "triangle_topology_manifold": manifold, "triangle_topology_closed": closed,
            "trimesh_watertight": bool(mesh.is_watertight), "winding_consistent": bool(mesh.is_winding_consistent),
            "degenerate_faces": int(np.count_nonzero(mesh.area_faces <= 1e-14)),
            "qualification_limit": "triangle connectivity and winding only; self-intersections not independently audited",
            "solid_interval_qualified": bool(manifold and closed and mesh.is_watertight and mesh.is_winding_consistent)}


def normalize(snapshot):
    """Reuse the adapter and keep already-world metre vertices unchanged."""
    scene = load_blender_neutral_scene(snapshot, mode="blender_geometry",
                                      selected_ids=[o["id"] for o in snapshot["objects"]], roles=snapshot["roles"])
    assert scene.analysis_domain is None and not scene.openings
    scope = {row["object_id"]: row for row in snapshot["source_scope"]}
    rows = []
    for source, geometry, original in zip(scene.source_objects, scene.geometries, snapshot["objects"]):
        assert source.source_id is None and source.source_class is None
        assert geometry.units == "m" and original["transform_applied"] is True
        assert np.array_equal(geometry.vertices, original["vertices"])
        patch = mass_patch_from_mesh(geometry)
        mesh = trimesh.Trimesh(patch.vertices, patch.triangle_indices, process=False)
        rows.append({"id": original["id"], "role": source.source_role, "identity": scope[original["id"]],
                     "source_record_id": source.id, "source_id": source.source_id,
                     "patch": patch, "mesh": mesh, "qualification": qualify(patch, mesh)})
    return rows


def build_fixture(definition):
    """Make disjoint watertight box shells from declared synthetic dimensions."""
    from features.scene_contract import MeshGeometry3D
    rows = []
    for name, role, bounds in definition["boxes"]:
        low, high = np.asarray(bounds[:3]), np.asarray(bounds[3:])
        mesh = trimesh.creation.box(extents=high - low)
        # Set shared dimension endpoints directly; centre translation can
        # introduce tiny gaps between analytically touching fixture boxes.
        mesh.vertices = np.where(mesh.vertices < 0, low, high)
        geometry = MeshGeometry3D(id=name, vertices=tuple(map(tuple, mesh.vertices)),
                                  triangle_indices=tuple(tuple(int(i) for i in face) for face in mesh.faces), is_closed=True,
                                  is_manifold=True, units="m", normals=(),
                                  local_to_world_provenance={"method": "synthetic_dimensions_world_metres"},
                                  source_representation_id=name, tessellation_settings={})
        patch = mass_patch_from_mesh(geometry)
        rows.append({"id": name, "role": role, "patch": patch, "mesh": mesh,
                     "qualification": qualify(patch, mesh), "analytic_bounds_m": bounds})
    return rows


def geometry_report(geometry):
    """Keep polygon validity, component count and holes as distinct observations."""
    polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else ([geometry] if geometry.geom_type == "Polygon" else [])
    return {"geojson": mapping(geometry), "area_m2": float(geometry.area), "valid": bool(geometry.is_valid),
            "polygon_components": len(polygons), "hole_count": sum(len(p.interiors) for p in polygons)}


def indexed_section_segments(mesh, height):
    """Intersect shared indexed edges once, avoiding reversed-edge roundoff gaps.

    No vertices are welded, rounded or moved. Fully coplanar triangles are
    recorded separately by section() and never promoted to an occupied area.
    """
    vertices = mesh.vertices
    offsets = vertices[:, 2] - height
    cache, segments = {}, []
    selected = np.flatnonzero((offsets[mesh.faces].min(axis=1) <= 0) & (offsets[mesh.faces].max(axis=1) >= 0))
    for face in mesh.faces[selected]:
        if np.all(offsets[face] == 0):
            continue
        points = []
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            key = tuple(sorted((int(a), int(b))))
            if key not in cache:
                first, second = key
                oa, ob = offsets[first], offsets[second]
                if oa == 0 and ob == 0:
                    hits = [vertices[first].tolist(), vertices[second].tolist()]
                elif oa == 0:
                    hits = [vertices[first].tolist()]
                elif ob == 0:
                    hits = [vertices[second].tolist()]
                elif oa * ob < 0:
                    ratio = -oa / (ob - oa)
                    hit = vertices[first] + ratio * (vertices[second] - vertices[first])
                    hit[2] = height
                    hits = [hit.tolist()]
                else:
                    hits = []
                cache[key] = hits
            for hit in cache[key]:
                if hit not in points:
                    points.append(hit)
        if len(points) == 2 and points[0] != points[1]:
            segments.append(points)
    return segments


def section(row, height):
    """Intersect the exact plane; preserve open contours and refuse coplanar area."""
    mesh, patch = row["mesh"], row["patch"]
    z = mesh.vertices[:, 2]
    coplanar = int(np.count_nonzero(np.all(np.abs(z[mesh.faces] - height) <= trimesh.constants.tol.merge, axis=1)))
    lines = trimesh.intersections.mesh_plane(mesh, (0, 0, 1), (0, 0, height))
    assembled = indexed_section_segments(mesh, height)
    linework = unary_union([LineString([point[:2] for point in line]) for line in assembled])
    raw_linework = unary_union([LineString(line[:, :2]) for line in lines if np.linalg.norm(line[1] - line[0]) > 1e-12])
    _, raw_cuts, raw_dangles, raw_invalid = polygonize_full(raw_linework)
    polygons, cuts, dangles, invalid = polygonize_full(linework)
    qualified = row["qualification"]["solid_interval_qualified"] and coplanar == 0
    residuals = len(cuts.geoms) + len(dangles.geoms) + len(invalid.geoms)
    occupied = []
    if qualified:
        # Polygonization can fill enclosed voids. Actual local triangle/Z
        # crossings select occupied faces rather than treating every loop as mass.
        for polygon in polygons.geoms:
            point = polygon.representative_point()
            intervals = vertical_intervals_at(patch, (point.x, point.y)).intervals
            if any(lower < height < upper for lower, upper in intervals):
                occupied.append(polygon)
    geometry = unary_union(occupied)
    return {"id": row["id"], "status": ("partial_section_unclosed_contours" if residuals else "qualified_section") if qualified else "contours_only_unqualified",
            "reason": "coplanar_faces_area_unsupported" if coplanar else (None if qualified else "solid_topology_unqualified"),
            "coplanar_faces": coplanar, "raw_segments_xyz": lines.tolist(),
            "contour_segments_xyz": assembled,
            "contour_method": "shared_indexed_source_edge_intersection_once_no_snapping",
            "raw_trimesh_residuals": {"cuts": len(raw_cuts.geoms), "dangles": len(raw_dangles.geoms), "invalid": len(raw_invalid.geoms)},
            "cut_edges": len(cuts.geoms), "dangles": len(dangles.geoms), "invalid_rings": len(invalid.geoms),
            "polygonized_faces": len(polygons.geoms), "geometry": geometry_report(geometry)}


def segment_crossings(patch, start, end):
    """Filter existing triangle-ray parameters to a bounded segment [0,1]."""
    direction = tuple(end[i] - start[i] for i in range(3))
    distances = []
    for triangle in patch.triangle_indices:
        value = _ray_intersection_distance(start, direction, *(patch.vertices[i] for i in triangle))
        if value is not None and 0 <= value <= 1:
            distances.append(value)
    unique = []
    for value in sorted(distances):
        if not unique or abs(value - unique[-1]) > 1e-9:
            unique.append(value)
    return unique


def query_3d(rows, points, segments):
    """Run actual triangle/Z and bounded segment/surface intersection queries."""
    return {"vertical": [{"point_xy_m": point, "objects": [
                {"id": row["id"], "result": vertical_intervals_at(row["patch"], tuple(point)).to_dict(),
                 "solid_interval_qualified": row["qualification"]["solid_interval_qualified"]} for row in rows]}
            for point in points],
            "segments": [{"start_m": start, "end_m": end, "objects": [
                {"id": row["id"], "surface_crossing_parameters": segment_crossings(row["patch"], start, end)} for row in rows]}
            for start, end in segments],
            "semantics": "Surface crossings include contacts; no claim about wholly-inside or coplanar segments. Vertical intervals require topology qualification."}


def run_method(method, rows, args, points, segments):
    """Execute one method without timing I/O or rendering inside its query."""
    if method == "genuine_3d_reference":
        return query_3d(rows, points, segments)
    if method == "section_at_1p5m":
        objects = [section(row, args.datum + args.cut_height) for row in rows]
        shapes = [shapely.geometry.shape(item["geometry"]["geojson"]) for item in objects]
    else:
        band = (args.datum + args.band_low, args.datum + args.band_high) if method == "finite_band_projection" else None
        objects, shapes = [], []
        for row in rows:
            projection = plan_projection(row["patch"], height_band=band, height_tolerance=1e-9)
            geometry = component_shape(projection.components)
            geometry = geometry if geometry is not None else GeometryCollection()
            objects.append({"id": row["id"], "uncertainty": projection.uncertainty, "geometry": geometry_report(geometry)})
            shapes.append(geometry)
    result = {"objects": objects, "union": geometry_report(unary_union(shapes))}
    if method == "section_at_1p5m":
        result["mask_completeness"] = "partial" if any(item["status"] != "qualified_section" for item in objects) else "complete_for_qualified_sources"
        result["union_area_semantics"] = "observed_qualified_faces_only; partial when residual/open contours remain"
    return result


def oracle_check(definition, rows, methods, args):
    """Check section masks, occupied Z, crossings and volume against dimensions."""
    checks = []
    for method in METHODS[:3]:
        rectangles = []
        for _, _, b in definition["boxes"]:
            selected = (b[2] < args.datum + args.cut_height < b[5]) if method == METHODS[0] else (
                min(b[5], args.datum + args.band_high) - max(b[2], args.datum + args.band_low) > 1e-9 if method == METHODS[1] else True)
            if selected:
                rectangles.append(box(b[0], b[1], b[3], b[4]))
        expected = unary_union(rectangles)
        observed = shapely.geometry.shape(methods[method]["union"]["geojson"])
        error = float(expected.symmetric_difference(observed).area)
        assert error <= 1e-6, (definition["id"], method, error)
        expected_report, observed_report = geometry_report(expected), geometry_report(observed)
        assert (expected_report["polygon_components"], expected_report["hole_count"]) == (observed_report["polygon_components"], observed_report["hole_count"]), (definition["id"], method, "topology_mismatch")
        checks.append({"method": method, "expected_area_m2": expected.area, "symmetric_difference_m2": error,
                       "expected_geometry": geometry_report(expected)})
    reference = methods["genuine_3d_reference"]
    for query in reference["vertical"]:
        x, y = query["point_xy_m"]
        for row, object_result in zip(rows, query["objects"]):
            b = row["analytic_bounds_m"]
            expected = [[b[2], b[5]]] if b[0] < x < b[3] and b[1] < y < b[4] else []
            actual = object_result["result"]["intervals"]
            assert np.shape(expected) == np.shape(actual) and (not expected or np.max(np.abs(np.asarray(expected) - actual)) <= 1e-6)
            object_result["analytic_expected_intervals_m"] = expected
    for query in reference["segments"]:
        for row, result in zip(rows, query["objects"]):
            expected = analytic_segment(row["analytic_bounds_m"], query["start_m"], query["end_m"])
            actual = result["surface_crossing_parameters"]
            assert len(actual) == len(expected) and (not expected or np.max(np.abs(np.asarray(actual) - expected)) <= 1e-6)
            result["analytic_expected_parameters"] = expected
    expected_volume = sum(np.prod(np.asarray(b[3:]) - b[:3]) for _, _, b in definition["boxes"])
    observed_volume = sum(abs(row["mesh"].volume) for row in rows)
    assert abs(expected_volume - observed_volume) <= 1e-6
    return {"mask_checks": checks, "volume": {"expected_m3": float(expected_volume), "observed_m3": float(observed_volume),
             "qualification": "disjoint watertight boxes; volume fact, not enclosure or room inference"}, "passed": True}


def plot_polygon(ax, geometry, color):
    """Draw exteriors and voids without replacing polygon topology."""
    from matplotlib.patches import Polygon as PlotPolygon
    for polygon in ([geometry] if geometry.geom_type == "Polygon" else getattr(geometry, "geoms", [])):
        if polygon.geom_type != "Polygon":
            continue
        ax.add_patch(PlotPolygon(polygon.exterior.coords, color=color, alpha=.8, linewidth=.6))
        for interior in polygon.interiors:
            ax.add_patch(PlotPolygon(interior.coords, facecolor="white", edgecolor=color, linewidth=.5))


def render(results, scenes, args, out):
    """Render source-derived comparisons and an explicit 3D analytic contrast."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    real = results["real_structural_snapshot"]
    rows = scenes["real_structural_snapshot"]
    extent = np.vstack([row["mesh"].vertices for row in rows])
    low, high = extent[:, :2].min(axis=0) - .6, extent[:, :2].max(axis=0) + .6
    fig, axes = plt.subplots(1, 3, figsize=(18, 9))
    titles = [f"Exact section z={args.datum + args.cut_height:g} m", f"Band [{args.datum + args.band_low:g}, {args.datum + args.band_high:g}] m", "Full-height XY"]
    for ax, method, title in zip(axes, METHODS[:3], titles):
        for row, item in zip(rows, real["methods"][method]["objects"]):
            color = COLORS[row["role"]]
            plot_polygon(ax, shapely.geometry.shape(item["geometry"]["geojson"]), color)
            if method == METHODS[0] and item["status"] != "qualified_section":
                for line in item["contour_segments_xyz"]:
                    ax.plot([p[0] for p in line], [p[1] for p in line], color=color, linewidth=.7, linestyle="--")
        ax.set(xlim=(low[0], high[0]), ylim=(low[1], high[1]), title=title, xlabel="World X (m)", ylabel="World Y (m)")
        ax.set_aspect("equal")
        ax.grid(alpha=.15)
    fig.suptitle("Frozen IFC-derived structural geometry | 11 walls, 16 columns, 6 doors\nWorld z=0 datum is assumed; disk/snapshot geometry parity unverified", fontsize=15)
    fig.legend(handles=[Patch(color=COLORS[role], label=role) for role in ("wall", "column", "door")], loc="lower center", ncol=3, bbox_to_anchor=(.5, .07))
    fig.text(.5, .025, "Dashed: partial/unqualified section contours. Section mask is partial. No qualified domain, free-space, routes, or room inference.", ha="center", fontsize=11)
    fig.subplots_adjust(top=.82, bottom=.15, wspace=.3)
    fig.savefig(out / "real_top_comparison.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(14, 10))
    for axrow, scene_id in zip(axes, ("low_partition", "overhead_bridge")):
        for ax, method, title in zip(axrow, METHODS[:3], titles):
            geometry = shapely.geometry.shape(results[scene_id]["methods"][method]["union"]["geojson"])
            plot_polygon(ax, geometry, COLORS["partition" if scene_id == "low_partition" else "beam"])
            ax.plot(2.03, 1.13 if scene_id == "low_partition" else 1.37, "kx", label="3D probe XY")
            ax.set(xlim=(0, 4), ylim=(0, 3), title=f"{scene_id}\n{title}", xlabel="X (m)", ylabel="Y (m)")
            ax.set_aspect("equal")
            ax.grid(alpha=.2)
    fig.suptitle("Section, finite band, and full-height projection answer different questions", fontsize=15)
    fig.legend(handles=[Patch(color=COLORS["partition"], label="Low mass [0,1] m"), Patch(color=COLORS["beam"], label="Overhead mass [2.4,2.8] m")], loc="lower center", ncol=2)
    fig.subplots_adjust(top=.85, bottom=.1, hspace=.6, wspace=.27)
    fig.savefig(out / "analytic_masks.png", dpi=150)
    plt.close(fig)

    fig = plt.figure(figsize=(13, 8))
    ax = fig.add_subplot(111, projection="3d")
    for scene_id in ("low_partition", "overhead_bridge"):
        row = scenes[scene_id][0]
        ax.add_collection3d(Poly3DCollection(row["mesh"].triangles, facecolor=COLORS[row["role"]], edgecolor="black", linewidth=.4, alpha=.65))
    z = args.datum + args.cut_height
    ax.add_collection3d(Poly3DCollection([[(0, 0, z), (4, 0, z), (4, 3, z), (0, 3, z)]], facecolor="#5acbd0", alpha=.18))
    ax.plot([2.03, 2.03], [1.13, 1.13], [0, 3.1], "k--", linewidth=2)
    for height, color in ((.5, "#ae4472"), (1.5, "#288383"), (2.6, "#8255b2")):
        ax.plot([2.03, 2.03], [0, 3], [height, height], color=color, linewidth=2)
    ax.set(xlim=(0, 4), ylim=(0, 3), zlim=(0, 3.2), xlabel="X (m)", ylabel="Y (m)", zlabel="Z above synthetic datum (m)")
    ax.view_init(elev=24, azim=-58)
    ax.set_title("Analytic contrast overlay (two separate fixture scenes)\nLow mass [0,1] m; overhead bridge [2.4,2.8] m; exact cut at 1.5 m", pad=25)
    fig.legend(handles=[Patch(color=COLORS["partition"], label="Low obstacle + z=.5 segment"), Patch(color=COLORS["beam"], label="Overhead + z=2.6 segment"), Patch(color="#5acbd0", label="Cut plane / clear z=1.5 segment")], loc="lower center", ncol=3)
    fig.subplots_adjust(bottom=.13, top=.83)
    fig.savefig(out / "analytic_3d_cut_and_queries.png", dpi=150)
    plt.close(fig)


def input_and_parameters(args):
    """Verify identity and state every experimental coordinate convention."""
    snapshot_fp = fingerprint(args.snapshot)
    assert snapshot_fp["sha256"] == SNAPSHOT_HASH
    data = args.snapshot.read_bytes()
    snapshot = json.loads(data)
    ifc = fingerprint(Path(snapshot["source_ifc"]["path"]))
    assert ifc["bytes"] == 408617800 and ifc["sha256"] == IFC_HASH
    return snapshot, {"snapshot": snapshot_fp, "disk_ifc": ifc, "geometry_parity": "not_established",
                      "method_backends": {"exact_section": "design_only_shared_indexed_edge_intersection_once; raw_trimesh_mesh_plane_reference_retained",
                                           "band": "existing_plan_projection_triangle_clipping_with_existing_closed_shell_fallback",
                                           "full_xy": "existing_plan_projection_triangle_face_union",
                                           "vertical": "existing_vertical_intervals_at_triangle_Z_intersections",
                                           "bounded_segment": "existing_private_ray_intersection_distance_filtered_to_[0,1]"},
                      "geometry_source": "frozen_evaluated_world_metres_snapshot", "parameters": {
                          "datum_world_z_m": args.datum, "datum_status": "experiment_only_assumption",
                          "cut_height_relative_m": args.cut_height, "band_relative_m": [args.band_low, args.band_high],
                          "analysis_plane": {"origin": [0, 0, args.datum], "basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
                          "section_world_z_m": args.datum + args.cut_height, "units": "m", "area_units": "m2",
                          "band_question": "XY surface projection of source geometry overlapping [datum+0,datum+2]; diagnostic vertical occupancy envelope, not a walkability proof",
                          "analytic_linear_tolerance_m": 1e-6, "analytic_area_tolerance_m2": 1e-6,
                          "positive_band_overlap_tolerance_m": 1e-9, "trimesh_plane_classification_tolerance_m": trimesh.constants.tol.merge}}


def real_probes(rows):
    """Declare a bounded geometry-driven probe set without interpreting room use."""
    points = [row["mesh"].bounds.mean(axis=0)[:2].tolist() for row in rows]
    bounds = np.vstack([row["mesh"].vertices for row in rows])
    low, high = bounds.min(axis=0), bounds.max(axis=0)
    middle_y = float((low[1] + high[1]) / 2 + .013)
    segments = [[[float(low[0] - 1), middle_y, h], [float(high[0] + 1), middle_y, h]] for h in (.5, 1.5, 2.6)]
    return points, segments


def experiment(args, out):
    """Write pre-query fixture definitions, run numerical checks, then render."""
    tick = time.perf_counter()
    snapshot, provenance = input_and_parameters(args)
    ingest_seconds = time.perf_counter() - tick
    write_json(out / "provenance.json", provenance)
    definitions = fixture_definitions()
    write_json(out / "fixture_definitions_before_queries.json", definitions)
    write_json(out / "dimension_oracles_before_queries.json", dimension_oracles(definitions))
    tick = time.perf_counter()
    rows = normalize(snapshot)
    scenes = {definition["id"]: build_fixture(definition) for definition in definitions}
    scenes["real_structural_snapshot"] = rows
    extraction = time.perf_counter() - tick
    results, timings = {}, {}
    for name, scene in scenes.items():
        definition = next((d for d in definitions if d["id"] == name), None)
        points, segments = (definition["points"], definition["segments"]) if definition else real_probes(scene)
        methods = {}
        for method in METHODS:
            tick = time.perf_counter()
            methods[method] = run_method(method, scene, args, points, segments)
            timings[f"{name}/{method}"] = time.perf_counter() - tick
            print(f"completed {name}/{method}", flush=True)
        inventory = [{"id": row["id"], "role": row["role"], "identity": row.get("identity"),
                      "bounds_xyz_m": row["mesh"].bounds.tolist(), "vertices": len(row["mesh"].vertices),
                      "triangles": len(row["mesh"].faces), "qualification": row["qualification"]} for row in scene]
        results[name] = {"methods": methods, "inventory": inventory,
                         "qualification": "analytic_fixture" if definition else "real_snapshot_structural_only",
                         "query_definition": {"vertical_xy": points, "segments": segments}}
        write_json(out / f"{name}_before_assertions.json", results[name])
        if definition:
            results[name]["analytic_checks"] = oracle_check(definition, scene, methods, args)
    # A coplanar cut is preserved as unsupported area, rather than quietly
    # shifting the requested plane or using a finite band as an exact cut.
    coplanar = section(scenes["low_partition"][0], 0.0)
    assert coplanar["coplanar_faces"] == 2 and coplanar["reason"] == "coplanar_faces_area_unsupported"
    write_json(out / "coplanar_self_check.json", coplanar)
    ray_row = scenes["overhead_bridge"][0]
    ray = occlusion_intersections(ray_row["patch"], {"origin": [2.03, 0, 2.6], "direction": [0, .8, 0]})
    assert ray == ("occluded",) and not segment_crossings(ray_row["patch"], [2.03, 0, 2.6], [2.03, .8, 2.6])
    write_json(out / "ray_vs_bounded_segment_self_check.json", {"forward_ray": ray, "bounded_segment_crossings": [], "expected": "object beyond endpoint hits ray only"})
    write_json(out / "comparison.json", results)
    tick = time.perf_counter()
    render(results, scenes, args, out)
    render_seconds = time.perf_counter() - tick
    write_json(out / "exploratory_stage_timings.json", {"identity_hash_read_decode_seconds": ingest_seconds,
              "adapter_patch_topology_fixture_extraction_seconds": extraction,
              "geometric_queries_seconds": timings, "render_seconds": render_seconds,
              "inference": {"status": "not_executed", "reason": "prior runner consumes frozen candidates; no new-mask candidate integration"},
              "timing_status": "exploratory; final serial timing is a separate mode"})
    write_json(out / "coverage.json", {"objects": len(rows), "roles": dict(Counter(r["role"] for r in rows)),
              "solid_topology_qualified": sum(r["qualification"]["solid_interval_qualified"] for r in rows),
              "source_topology_flags_preserved": True, "unqualified": [r["id"] for r in rows if not r["qualification"]["solid_interval_qualified"]],
              "authored_ifc_plan": native_plan_evidence(args),
              "unsupported": ["complete_3d_room_inference", "qualified_AnalysisDomain", "free_space", "walkability", "route_width", "opening_host_inference", "observed_door_state", "furniture_trend", "disk_snapshot_geometry_parity", "coplanar_section_area", "solid_intervals_on_unqualified_mesh"]})


def native_plan_evidence(args):
    """Retain A's actually executed unavailable finding without synthesizing Body."""
    if args.native_inventory is None:
        return {"status": "not_available", "reason": "native_inventory_not_supplied"}
    inventory = json.loads(args.native_inventory.read_bytes())
    assert inventory["source"]["sha256"] == IFC_HASH
    candidates = inventory["native_plan_candidate_representation_ids"]
    assert candidates == [], "An authored candidate needs independent extraction and qualification before use"
    return {"status": "not_available", "reason": "no_authored_plan_representation",
            "inventory": fingerprint(args.native_inventory), "candidate_representation_ids": candidates,
            "datum_evidence": inventory["datum"], "not_synthesized_from_body": True}


def serial_timing(args, out):
    """Warm once, then alternate method order on the same frozen scene."""
    snapshot, provenance = input_and_parameters(args)
    write_json(out / "provenance.json", provenance)
    rows = normalize(snapshot)
    points, segments = real_probes(rows)
    # Timing uses three fixed object-local vertical queries and three full-scene
    # segments, reducing repeated work without pretending to time room inference.
    points = points[:3]
    for method in METHODS:
        run_method(method, rows, args, points, segments)
    rounds = []
    for index in range(args.rounds):
        tick = time.perf_counter()
        raw = args.snapshot.read_bytes()
        read_seconds = time.perf_counter() - tick
        tick = time.perf_counter()
        decoded = json.loads(raw)
        decode_seconds = time.perf_counter() - tick
        tick = time.perf_counter()
        current = normalize(decoded)
        adapter_seconds = time.perf_counter() - tick
        methods, payloads = {}, {}
        order = METHODS if index % 2 == 0 else tuple(reversed(METHODS))
        for method in order:
            tick = time.perf_counter()
            payloads[method] = run_method(method, current, args, points, segments)
            methods[method] = time.perf_counter() - tick
        tick = time.perf_counter()
        encoded = json.dumps(payloads, sort_keys=True, allow_nan=False).encode()
        serialization = time.perf_counter() - tick
        rounds.append({"round": index + 1, "method_order": order, "snapshot_read_seconds": read_seconds,
                       "json_decode_seconds": decode_seconds, "adapter_patch_topology_seconds": adapter_seconds,
                       "query_seconds": methods, "serialization_seconds": serialization,
                       "geometry_payload_sha256": hashlib.sha256(encoded).hexdigest()})
        print(f"completed serial round {index + 1}", flush=True)
    assert len({r["geometry_payload_sha256"] for r in rounds}) == 1
    summaries = {method: {"min": min(values := [r["query_seconds"][method] for r in rounds]),
                          "median": statistics.median(values), "max": max(values)} for method in METHODS}
    write_json(out / "serial_timings.json", {"rounds": rounds, "summary_seconds": summaries,
              "warmups": 1, "scene_units": 1, "timing_repeats_not_independent_scenes": True,
              "3d_workload": {"vertical_queries_all_objects": points, "segments_all_objects": segments},
              "inference": "not_executed", "render": "not_in_timing_loop; see comparison run",
              "no_speedup_ratio": "3D queries and 2D masks answer different estimands"})


def worker(args):
    """Run one bounded worker and preserve its imported helper provenance."""
    out = args.output_dir
    modules = ["features.geometry_views", "features.geometry_substitutes", "adapters.blender_geometry", "adapters.ifc_bonsai", "trimesh.intersections"]
    write_json(out / "imported_helpers.json", {"modules": {name: fingerprint(importlib.import_module(name).__file__) for name in modules},
              "runner": fingerprint(__file__), "versions": {"python": sys.version, "trimesh": trimesh.__version__, "shapely": shapely.__version__},
              "python_executable": sys.executable})
    (serial_timing if args.mode == "timing" else experiment)(args, out)


def main():
    """Supervise a fresh directory; timeout only this runner's child process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--native-inventory", type=Path)
    parser.add_argument("--mode", choices=("compare", "timing"), default="compare")
    parser.add_argument("--datum", type=float, required=True)
    parser.add_argument("--cut-height", type=float, required=True)
    parser.add_argument("--band-low", type=float, required=True)
    parser.add_argument("--band-high", type=float, required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--budget-seconds", type=int, default=180)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not all(np.isfinite(v) for v in (args.datum, args.cut_height, args.band_low, args.band_high)) or args.band_low >= args.band_high or args.rounds < 1:
        parser.error("finite heights, increasing band and positive rounds required")
    # The declared matrix fixes these IDs; other parameter experiments need
    # different method IDs rather than silently changing section_at_1p5m.
    if (args.datum, args.cut_height, args.band_low, args.band_high) != (0, 1.5, 0, 2):
        parser.error("this bounded matrix supports only explicitly supplied 0 / 1.5 / [0,2] settings")
    if args.worker:
        try:
            worker(args)
        except Exception:
            (args.output_dir / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "runner_snapshot.py").write_bytes(Path(__file__).read_bytes())
    command = [sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:], "--worker"]
    started = datetime.now(timezone.utc).isoformat()
    tick = time.perf_counter()
    timed_out = False
    with (args.output_dir / "stdout.log").open("wb") as stdout, (args.output_dir / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=args.budget_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait()
    write_json(args.output_dir / "execution.json", {"parent_argv": sys.argv, "worker_argv": command, "cwd": str(ROOT),
               "started_utc": started, "ended_utc": datetime.now(timezone.utc).isoformat(), "worker_pid": process.pid,
               "worker_exit_code": code, "timed_out": timed_out, "budget_seconds": args.budget_seconds,
               "elapsed_seconds": time.perf_counter() - tick})
    write_json(args.output_dir / "manifest.json", {"artifacts": [fingerprint(path) for path in sorted(args.output_dir.iterdir()) if path.is_file()],
               "storage": "local-only evidence; hashes do not retain the source IFC or snapshot", "manifest_self_hash": "excluded"})
    print(json.dumps({"worker_exit_code": code, "timed_out": timed_out, "output_dir": str(args.output_dir)}), flush=True)
    return 124 if timed_out else code


if __name__ == "__main__":
    raise SystemExit(main())
