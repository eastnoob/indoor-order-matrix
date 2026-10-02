"""Extract faithful read-only plan projections for source IFC wall solids."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ifcopenshell
import ifcopenshell.geom
from shapely.geometry import Polygon
from shapely.ops import triangulate, unary_union

from adapters.ifc_bonsai import _native_length_unit, _native_mesh_record, _native_source_id


def _sha256(path: Path) -> str:
    """Return a streaming SHA-256 digest for the immutable source IFC."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _projected_wall(entity: object) -> dict[str, object]:
    """Project all non-degenerate Body triangles and preserve their exact union."""
    representation = next(
        (
            item
            for item in getattr(getattr(entity, "Representation", None), "Representations", ()) or ()
            if getattr(item, "RepresentationIdentifier", None) == "Body"
        ),
        None,
    )
    source_id = _native_source_id(entity)
    if representation is None:
        return {"source_id": source_id, "status": "missing", "triangles_xy_m": []}
    mesh, uncertainty = _native_mesh_record(
        entity, f"{source_id}:wall_plan", "m", ifcopenshell, representation
    )
    if mesh is None:
        return {
            "source_id": source_id,
            "status": "missing",
            "triangles_xy_m": [],
            "uncertainty": None if uncertainty is None else uncertainty.to_dict(),
        }
    vertices = mesh.to_dict()["vertices"]
    source_triangles = mesh.to_dict()["triangle_indices"]
    projected = []
    for indices in source_triangles:
        points = [(float(vertices[index][0]), float(vertices[index][1])) for index in indices]
        polygon = Polygon(points)
        if polygon.is_valid and polygon.area > 1e-12:
            projected.append(polygon)
    if not projected:
        return {
            "source_id": source_id,
            "status": "missing",
            "triangles_xy_m": [],
            "reason": "Body tessellation had no non-degenerate XY projection.",
        }
    footprint = unary_union(projected)
    parts = list(footprint.geoms) if footprint.geom_type == "MultiPolygon" else [footprint]
    fill_triangles = []
    outlines = []
    for part in parts:
        if part.is_empty or part.area <= 1e-12:
            continue
        outlines.append([[float(x), float(y)] for x, y in part.exterior.coords])
        outlines.extend(
            [[float(x), float(y)] for x, y in ring.coords]
            for ring in part.interiors
        )
        for triangle in triangulate(part):
            if part.covers(triangle) and triangle.area > 1e-12:
                fill_triangles.append(
                    [[float(x), float(y)] for x, y in list(triangle.exterior.coords)[:3]]
                )
    return {
        "source_id": source_id,
        "status": "computed",
        "method": "union_of_non_degenerate_XY_projections_of_all_IFC_Body_triangles",
        "representation": "Body",
        "coordinate_space": "world",
        "units": "m",
        "source_triangle_count": len(source_triangles),
        "projected_triangle_count": len(projected),
        "area_m2": float(footprint.area),
        "outlines_xy_m": outlines,
        "triangles_xy_m": fill_triangles,
    }


def main() -> None:
    """Write disposable wall projection evidence without editing the source IFC."""
    output = Path(__file__).resolve().parent
    summary = json.loads((output / "source_summary.json").read_text(encoding="utf-8"))
    source_path = Path(summary["source_ifc"]["path"])
    source = ifcopenshell.open(str(source_path))
    walls = [_projected_wall(entity) for entity in source.by_type("IfcWall")]
    payload = {
        "schema": "d6-space-field-wall-plan-projection/v1",
        "source_path": str(source_path.resolve()),
        "source_sha256": _sha256(source_path),
        "projection_plane": "world XY plan",
        "projection_status": "diagnostic source-solid footprint; not a boundary or AnalysisDomain",
        "walls": sorted(walls, key=lambda item: str(item["source_id"])),
    }
    if payload["source_sha256"] != summary["source_ifc"]["sha256"]:
        raise RuntimeError("Source IFC identity changed since candidate extraction.")
    if len(walls) != 11 or any(item["status"] != "computed" for item in walls):
        raise RuntimeError("All 11 physical wall projections must be computed before rendering.")
    target = output / "physical_wall_plan_projection.json"
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "pass", "wall_count": len(walls), "path": str(target)}))


if __name__ == "__main__":
    main()
