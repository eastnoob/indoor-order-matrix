"""Render frozen B3 rings and discrete samples in a fresh background Blender."""

import argparse
from collections import Counter
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from render_b3_real_field_blender import collection, curve_object, label, rings


PACKAGE = Path("outputs/design/b3_shared_occupancy_enrollment/run_20261009T142454Z_0d7308")
MANIFEST_SHA256 = "7029c01cf0883ce30819194aa75f66bbb6d991140794c704632abe067a777118"
BLENDER = Path("D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")
COLORS = {
    "established_empty_under_qualification": (.55, .82, .64),
    "established_occupied": (.78, .03, .55),
    "unknown": (.95, .42, .02),
    "outside_domain": (.72, .73, .75),
}
SAMPLE_SIZE_M = .06


def sha256(path):
    """Fingerprint the immutable package artifacts before and after rendering."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_locked_package(root):
    """Verify the pinned manifest and read only serialized preview inputs."""
    package = root / PACKAGE
    manifest_path = package / "artifact_manifest.json"
    if sha256(manifest_path) != MANIFEST_SHA256:
        raise ValueError("Locked manifest fingerprint mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fingerprints = {"artifact_manifest.json": MANIFEST_SHA256}
    # The pinned manifest authenticates every package artifact, including the audit.
    for item in manifest["artifacts"]:
        path = root / item["path"]
        if path.parent != package or sha256(path) != item["sha256"]:
            raise ValueError(f"Locked artifact fingerprint mismatch: {path.name}")
        fingerprints[path.name] = item["sha256"]
    inputs = [json.loads((package / name).read_text(encoding="utf-8"))
              for name in ("field_samples.json", "source_sections.json", "selection_audit.json")]
    return package, inputs, fingerprints


def sample_markers(variant, target):
    """Draw tiny display squares at saved samples without filling entire cells."""
    counts = Counter()
    for status, color in COLORS.items():
        vertices, faces = [], []
        for sample in variant["samples"]:
            if sample["status"] != status:
                continue
            x, y, z = sample["x_m"], sample["y_m"], sample["world_z_m"]
            half = SAMPLE_SIZE_M / 2
            index = len(vertices)
            vertices.extend([(x-half, y-half, z), (x+half, y-half, z),
                             (x+half, y+half, z), (x-half, y+half, z)])
            faces.append((index, index+1, index+2, index+3))
            counts[status] += 1
        mesh = bpy.data.meshes.new(f"Samples:{status}")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(f"Samples:{status} / {len(faces)}", mesh)
        target.objects.link(obj)
        obj.color = (*color, 1)
        obj["b3_preview"] = True
        obj["geometry_role"] = "sample_marker_only_not_entire_cell_geometry"
        obj["marker_side_m"] = SAMPLE_SIZE_M
    # A future unknown status must fail here rather than silently disappear.
    assert sum(counts.values()) == variant["sample_count"] == len(variant["samples"])
    assert dict(counts) == variant["status_counts"]
    return dict(counts)


def main():
    """Save an independent plan and audited metadata without opening a live scene."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]).out.resolve()
    root = Path(__file__).resolve().parents[3]
    if out.parent != root / "outputs/design/b3_shared_occupancy_enrollment" or not out.name.startswith("preview_"):
        raise ValueError("Output must be a new b3_shared_occupancy_enrollment/preview_<timestamp> directory")
    if not bpy.app.background or Path(bpy.app.binary_path).resolve() != BLENDER.resolve():
        raise RuntimeError("Use the specified portable Blender in background mode")
    package, (field, sections, audit), fingerprints = load_locked_package(root)
    by_id = {row["id"]: row for row in sections["records"]}
    variant = next(row for row in field["variants"]
                   if row["spacing_m"] == .25 and row["origin_offset_m"] == [0, 0])
    proxies = [by_id[source_id] for source_id in audit["proxy_target_ids"]]
    owners = sorted({owner for row in proxies for owner in row["represented_source_ids"]})
    assert audit["query"] == {"frame": "world_xy", "units": "m", "world_z_m": 1.6}
    assert field["primary_plane_world_z_m"] == 1.6 and field["units"] == "m"
    assert field["domain_holes"] == len(field["domain_geometry"]["coordinates"]) - 1 == 2
    assert field["complete_occupancy_geometry"] is None
    assert len(proxies) == 3 and len(owners) == 7 and len(audit["unknown_source_ids"]) == 5
    assert audit["boundary_scoped_ids"] == ["live-step-6231"]
    assert set(audit["boundary_scoped_ids"]).isdisjoint(audit["unknown_source_ids"])
    assert set(audit["boundary_scoped_ids"]).isdisjoint(audit["selected_source_ids"])
    assert field["clipped_unknown_support_area_m2"] == 0
    assert all(sample["complete_physical_clearance_m"] is None for sample in variant["samples"])
    assert all(not sample["unknown_mask"] for sample in variant["samples"])
    out.mkdir(parents=True, exist_ok=False)

    # Factory reset affects this new background process only; no blend or IFC is read.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["analysis_plane"] = "world XY; z=1.6 m"
    scene["complete_occupancy_and_clearance"] = "null"
    domain = collection("B3_S3_Analysis_Domain_Two_Holes")
    occupied = collection("B3_Clipped_Occupied_Subset_Magenta")
    unknown = collection("B3_Raw_Unknown_Support_Outside_S3_Orange")
    proxy_display = collection("B3_Raw_Proxy_Section_Reference_Purple")
    boundary = collection("B3_Boundary_Door_Scoped_Out_Black")
    labels = collection("B3_Inspection_Labels")
    counts = sample_markers(variant, collection("B3_Saved_Discrete_Samples"))
    # Original rings retain concavities and holes; raised strokes are display only.
    curve_object("S3 exterior + two holes", rings(field["domain_geometry"]), (0, .45, .60), domain, z=1.72, width=.025)
    curve_object("Clipped occupied subset", rings(field["clipped_qualified_occupied_geometry"]), COLORS["established_occupied"], occupied, z=1.76, width=.017)
    for source_id in audit["unknown_source_ids"]:
        obj = curve_object(f"Raw unknown {source_id}", rings(by_id[source_id]["unknown_support_geometry"]), COLORS["unknown"], unknown, z=1.80, width=.023)
        obj["source_id"] = source_id
        obj["geometry_role"] = "raw_uncertainty_support_outside_selected_domain_not_free_or_mass"
    for source_id in audit["boundary_scoped_ids"]:
        obj = curve_object(f"Boundary door {source_id}", rings(by_id[source_id]["unknown_support_geometry"]), (.05, .06, .08), boundary, z=1.84, width=.035)
        obj["geometry_role"] = "boundary_scoped_out_reference_support_not_interior_mass_or_unknown"
    proxy_positions = {"proxy:counter_1992252": (7.4, 4.2),
                       "proxy:assembly_A": (13.65, 11.8),
                       "proxy:assembly_B": (25.35, 5.2)}
    for index, row in enumerate(proxies, 1):
        obj = curve_object(f"P{index} {row['id']}", rings(row["occupied_geometry"]), (.43, .13, .66), proxy_display, z=1.88, width=.014)
        obj["represented_owner_ids"] = json.dumps(row["represented_source_ids"])
        label(f"P{index}", proxy_positions[row["id"]], labels, size=.24, color=(.43, .13, .66))
    label("Door 6231 / scoped out", (5.8, -.35), labels, size=.23)
    label("S3", (21, 9.8), labels, size=.30, color=(0, .45, .60))
    for ring in field["domain_geometry"]["coordinates"][1:]:
        label("hole", (min(p[0] for p in ring)+.04, min(p[1] for p in ring)+.1), labels, size=.16, color=(0, .45, .60))

    camera_data = bpy.data.cameras.new("B3_Independent_Top_Camera")
    camera = bpy.data.objects.new("B3_Independent_Top_Camera", camera_data)
    labels.objects.link(camera)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 29
    camera.location = (15.1, 6.1, 60)
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.display.shading.background_type = "WORLD"
    scene.world = bpy.data.worlds.new("B3_White_World")
    scene.world.color = (.96, .97, .99)
    scene.render.resolution_x = 2400
    scene.render.resolution_y = 1600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    label("B3 / world XY / z=1.6 m / conditional design package", (4.2, 14.45), labels, size=.38)
    label("Complete occupancy=null | complete clearance=null | S3 with two holes", (4.2, 13.8), labels, size=.29)
    label(f"Samples: {counts.get('established_empty_under_qualification', 0):,} conditional empty | "
          f"{counts.get('established_occupied', 0)} occupied | {counts.get('unknown', 0)} unknown | "
          f"{counts.get('outside_domain', 0)} outside", (4.2, 13.2), labels, size=.27)
    label("Green: conditional empty samples | Magenta: occupied | Gray: outside | Teal: S3 + holes", (4.2, -.95), labels, size=.25)
    label(f"Orange: {len(audit['unknown_source_ids'])} raw unknown source supports OUTSIDE S3; clipped unknown area=0; domain unknown samples=0", (4.2, -1.45), labels, size=.23)
    label(f"Purple: {len(proxies)} raw proxy sections / {len(owners)} owners | Black: live-step-6231, excluded from interior mass and unknown", (4.2, -1.95), labels, size=.23)
    label("0.06 m markers at saved 0.25 m / [0,0] samples; each marker describes a point, NOT an entire free cell.", (4.2, -2.45), labels, size=.23)
    label("Raised rings are display only. Query remains z=1.6 m. Live Blender scene not loaded or modified.", (4.2, -2.95), labels, size=.23)
    for x in range(5, 26, 5):
        label(str(x), (x, -.55), labels, size=.20)
    label("X (m)", (26, -.55), labels, size=.20)
    for y in range(2, 13, 2):
        label(str(y), (4.6, y), labels, size=.20)
    label("Y (m)", (4.2, 12.6), labels, size=.20)

    scene.render.filepath = str(out / "b3_shared_occupancy_world_xy_z1p6.png")
    if bpy.ops.render.render(write_still=True) != {"FINISHED"}:
        raise RuntimeError("Blender render did not finish")
    blend_path = out / "b3_shared_occupancy_disposable.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    assert all(sha256(package / name) == digest for name, digest in fingerprints.items())
    metadata = {
        "schema": "b3-shared-occupancy-preview/v1", "package": str(package),
        "package_fingerprints": fingerprints, "package_integrity_before_and_after": "verified",
        "blender_executable": str(BLENDER), "blender_version": bpy.app.version_string,
        "render_operator_status": "FINISHED", "render": scene.render.filepath,
        "blend": str(blend_path), "analysis_plane": "world XY; z=1.6 m",
        "conditional_design_package": True, "complete_occupancy": None, "complete_clearance": None,
        "domain_holes": 2, "selected_record_count": len(audit["selected_source_ids"]),
        "selected_records_policy": "Includes qualified occupied and legal-empty records",
        "unknown_source_ids": audit["unknown_source_ids"], "unknown_source_count": len(audit["unknown_source_ids"]),
        "unknown_display_policy": "Raw orange supports outside S3; not indoor unknown, free space, or occupied mass",
        "clipped_unknown_support_area_m2": field["clipped_unknown_support_area_m2"],
        "sample_variant": {"spacing_m": .25, "origin_offset_m": [0, 0], "status_counts": counts},
        "domain_unknown_sample_count": 0,
        "sample_marker_side_m": SAMPLE_SIZE_M, "sample_display_policy": "Point samples only; no whole-cell free claim",
        "proxy_ids": audit["proxy_target_ids"], "proxy_count": len(proxies),
        "proxy_display_labels": {f"P{index}": row["id"] for index, row in enumerate(proxies, 1)},
        "represented_owner_ids": owners, "represented_owner_count": len(owners),
        "boundary_scoped_ids": audit["boundary_scoped_ids"],
        "overlay_elevation_policy": "Samples z=1.6 m; rings z=1.72-1.88 m and labels z=6 m are display only; query unchanged",
        "live_blender_scene": "not_loaded_or_modified", "source_geometry_retessellation": "none",
    }
    with (out / "preview_metadata.json").open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, allow_nan=False, indent=2)
    print(json.dumps(metadata), flush=True)


if __name__ == "__main__":
    main()
