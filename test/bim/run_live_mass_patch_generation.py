"""Run MassPatch generation against a read-only Rhino mesh extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from ...features.mass_patch_generation import (
        MassPatchGenerationConfig,
        generate_mass_patches,
    )
    from ...features.scene_contract import MeshGeometry3D
except ImportError:
    # Direct script execution has no package parent; keep the runner usable
    # from the repository root without duplicating backend code.
    # Add the repository root explicitly because Python otherwise searches
    # only test/bim when this file is launched as a standalone script.
    import sys

    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from features.mass_patch_generation import (
        MassPatchGenerationConfig,
        generate_mass_patches,
    )
    from features.scene_contract import MeshGeometry3D


def _source_digest(path: Path) -> str:
    """Return a stable digest used to prove the input file was not edited."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mesh_from_record(record: dict[str, Any]) -> MeshGeometry3D:
    """Convert one Rhino-style vertices/faces record to the neutral mesh contract."""
    object_id = str(record["id"])
    vertices = tuple(
        tuple(float(value) for value in vertex)
        for vertex in record["vertices"]
    )
    triangles = tuple(
        tuple(int(value) for value in face)
        for face in record["faces"]
    )
    # Keep the adapter as transport only: the backend receives source
    # geometry, units, and provenance without inheriting Rhino object logic.
    return MeshGeometry3D(
        id=object_id,
        vertices=vertices,
        triangle_indices=triangles,
        normals=(),
        is_manifold=record.get("is_manifold"),
        is_closed=record.get("is_closed"),
        local_to_world_provenance={
            "source": "rhino_mcp_json",
            "object_id": object_id,
        },
        source_representation_id=object_id,
        tessellation_settings=record.get("tessellation_settings", {}),
        units=str(record.get("units", "m")),
    )


def run_generation(source_path: Path, output_path: Path) -> dict[str, object]:
    """Generate and serialize MassPatch results without mutating the source."""
    before_digest = _source_digest(source_path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    records = payload.get("objects")
    if not isinstance(records, list) or not records:
        raise ValueError("source payload must contain a non-empty objects list")

    object_results = []
    # Generate one auditable result per logical source object; never merge
    # objects here because grouping is outside this MassPatch operation.
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each source object must be a JSON object")
        mesh = _mesh_from_record(record)
        source_tolerance = record.get("linear_tolerance")
        config = (
            MassPatchGenerationConfig(linear_tolerance=float(source_tolerance))
            if source_tolerance is not None
            else None
        )
        result = generate_mass_patches(mesh, config)
        object_results.append(
            {
                "source_object_id": mesh.id,
                "result": result.to_dict(),
            }
        )

    after_digest = _source_digest(source_path)
    # A second digest detects accidental edits to the read-only extraction
    # while generation was running.
    result_payload: dict[str, object] = {
        "source_path": str(source_path),
        "source_mutation_check": before_digest == after_digest,
        "source_sha256": before_digest,
        "object_count": len(object_results),
        "object_results": object_results,
    }
    if len(object_results) == 1:
        result_payload["source_mesh_id"] = object_results[0]["result"]["source_mesh_id"]
        result_payload["patches"] = object_results[0]["result"]["patches"]
        result_payload["component_reports"] = object_results[0]["result"]["component_reports"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Stable JSON makes live acceptance artifacts diffable across reruns.
    output_path.write_text(
        json.dumps(result_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "target": str(output_path),
        "object_count": len(object_results),
        "patch_count": sum(
            len(item["result"]["patches"]) for item in object_results
        ),
        "source_mutation_check": before_digest == after_digest,
    }


def main() -> None:
    """Parse paths and run the read-only acceptance conversion."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_generation(args.source, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
