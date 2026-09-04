"""Convert a live Rhino furniture arrangement into the existing IFC adapter input."""

from __future__ import annotations

import json
from pathlib import Path


def _merge_mesh_records(records: list[dict]) -> tuple[list[list[float]], list[list[int]]]:
    """Merge component meshes into one world-coordinate mesh for one logical object."""
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for record in records:
        offset = len(vertices)
        vertices.extend(record["vertices"])
        faces.extend([[index + offset for index in face] for face in record["faces"]])
    return vertices, faces


def build_canonical_source(raw_path: Path, output_path: Path) -> dict[str, object]:
    """Group read-only Rhino extraction records into four chairs and one table."""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = {"table": [], "chair_nw": [], "chair_ne": [], "chair_sw": [], "chair_se": []}
    for record in raw["objects"]:
        if record["source_group"] == 2:
            key = "table"
        else:
            x, y = record["center"][:2]
            key = ("chair_n" if y >= 0 else "chair_s") + ("e" if x >= 0 else "w")
        groups[key].append(record)
    if any(not groups[key] for key in groups):
        raise ValueError(f"Could not infer all expected logical objects: {groups.keys()}")
    objects = []
    for key, records in groups.items():
        vertices, faces = _merge_mesh_records(records)
        kind = "table" if key == "table" else "chair"
        objects.append({
            "id": key,
            "kind": kind,
            "source_group": ",".join(sorted({str(r["source_group"]) for r in records})),
            "source_ids": [r["id"] for r in records],
            "vertices": vertices,
            "faces": faces,
        })
    output = {"source": "live Rhino MCP model", "objects": objects}
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return {"target": str(output_path), "object_count": len(objects), "component_count": sum(len(v) for v in groups.values())}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("raw")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(build_canonical_source(Path(args.raw), Path(args.output)), sort_keys=True))
