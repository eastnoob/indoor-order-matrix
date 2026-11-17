"""Capture one real IFC scene with a native Bonsai drawing camera."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(
    r"D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/"
    r"full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
)
BINARY = Path(r"D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe")


def fingerprint(path: Path) -> dict[str, object]:
    """Return the immutable source fingerprint used by the diagnostic run."""
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": checksum}


def write_json(path: Path, payload: object) -> None:
    """Write strict diagnostic JSON without overwriting a prior run artifact."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def capture(output: Path) -> None:
    """Load the authorized IFC, create one native camera, and persist a canonical capture."""
    import bpy

    if Path(bpy.app.binary_path).resolve() != BINARY.resolve():
        raise RuntimeError("the authorized portable Blender is required")
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    source_fingerprint = fingerprint(SOURCE)
    bpy.ops.preferences.addon_enable(module="bonsai")
    import bonsai.tool as tool
    from bonsai.bim.ifc import IfcStore
    import ifcopenshell

    result = bpy.ops.bim.load_project(
        filepath=str(SOURCE),
        use_relative_path=False,
        should_start_fresh_session=True,
        import_without_ifc_data=False,
    )
    if result != {"FINISHED"}:
        raise RuntimeError(f"Bonsai IFC load failed: {result}")
    model = IfcStore.get_file()
    if model is None or Path(IfcStore.path).resolve() != SOURCE.resolve() or model.schema != "IFC4":
        raise RuntimeError("loaded IFC identity/schema does not match the authorized source")
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1:
        raise RuntimeError(f"expected one building storey, found {len(storeys)}")

    sys.path.insert(0, str(ROOT))
    from adapters.blender_analysis_capture import begin_analysis_capture, capture_next_batch, finalize_capture
    from adapters.bonsai_analysis_plane import camera_composition, create_native_drawing, plane_from_camera, read_camera_binding

    storey_ref = "ifc-object:" + storeys[0].GlobalId
    camera = create_native_drawing(storey_ref=storey_ref)
    binding = read_camera_binding(camera, role="geometry_author")
    plane = plane_from_camera(binding, name="Analysis plane")
    job = begin_analysis_capture(
        bpy_context=bpy.context,
        scene_token=f"wall-domain-p2:{source_fingerprint['sha256']}",
        batch_size=8,
    )
    while not job.cancelled and job.next_index < len(job.entities):
        capture_next_batch(job, max_seconds=0.5)
    capture_input = finalize_capture(job)
    payload = {
        "schema": "real-ifc-wall-domain-camera-capture/v1",
        "source_fingerprint": source_fingerprint,
        "blender": {"binary": str(Path(bpy.app.binary_path).resolve()),
                     "version": bpy.app.version_string},
        "bonsai": {"ifc_path": str(Path(IfcStore.path).resolve()), "schema": model.schema,
                   "project_global_id": model.by_type("IfcProject")[0].GlobalId,
                   "storey_ref": storey_ref, "in_memory_native_authoring": True,
                   "derived_ifc_saved": False},
        "camera_binding": binding.to_dict(),
        "analysis_plane": plane.to_dict(),
        "camera_composition": camera_composition(binding, plane),
        "capture": capture_input.to_dict(),
        "observed_counts": {"IfcWall": len(model.by_type("IfcWall")),
                            "IfcDoor": len(model.by_type("IfcDoor")),
                            "IfcWindow": len(model.by_type("IfcWindow")),
                            "IfcSpace": len(model.by_type("IfcSpace")),
                            "IfcBuildingStorey": len(storeys)},
    }
    write_json(output, payload)


def main() -> None:
    """Read the output path passed after Blender's ``--`` separator."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    capture(args.output.resolve())
    print(json.dumps({"status": "captured", "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
