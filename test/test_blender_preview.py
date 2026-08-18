"""Tests for the output-only Blender description preview."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ..adapters.blender_preview import build_preview_manifest, write_preview_script


def _fixture_inputs() -> tuple[dict, dict]:
    """Return a small source-independent preview fixture."""
    scene = {
        "source_objects": [
            {
                "id": "table-1",
                "label": "Table",
                "role": "furniture",
                "geometry_refs": ["mesh-1"],
            }
        ],
        "geometries": [
            {
                "id": "mesh-1",
                "vertices": [[0, 0, 0], [2, 0, 0], [2, 1, 0], [0, 1, 0]],
                "triangle_indices": [[0, 1, 2], [0, 2, 3]],
            }
        ],
        "authored_grid_axes": [
            {"id": "axis-x", "curve_points": [[0, 0, 0], [4, 0, 0]]}
        ],
    }
    matrix = {
        "inferred_regions": [
            {
                "id": "region-1",
                "bounds": [0, 0, 2, 1],
                "trend": {
                    "primary_angle": 0,
                    "secondary_angle": 90,
                    "primary_strength": 0.8,
                    "secondary_strength": 0.2,
                },
            }
        ],
        "gap_paths": [
            {"id": "path-1", "region_a": "region-1", "region_b": "region-2", "thickness": 0.6}
        ],
        "boundary_channels": [
            {
                "id": "wall-1",
                "source_geometry_refs": ["mesh-1"],
                "walking": "blocked",
                "visual": "blocked",
            }
        ],
    }
    return scene, matrix


def test_preview_manifest_contains_source_and_derived_evidence() -> None:
    """Expose geometry, regions, both trend axes, grid, paths, and channels."""
    scene, matrix = _fixture_inputs()
    manifest = build_preview_manifest(scene, matrix)

    assert manifest["collection"] == "OM_AnalysisPreview"
    assert manifest["source_geometry"][0]["geometry_id"] == "mesh-1"
    assert manifest["source_geometry"][0]["faces"] == [[0, 1, 2], [0, 2, 3]]
    assert manifest["regions"][0]["trend_axes"][0]["strength"] == 0.8
    assert len(manifest["regions"][0]["trend_axes"]) == 2
    assert manifest["grid_axes"][0]["id"] == "axis-x"
    assert manifest["paths"][0]["thickness"] == 0.6
    assert manifest["paths"][0]["region_ids"] == ["region-1", "region-2"]
    assert manifest["boundary_channels"][0]["walking"] == "blocked"
    assert manifest["boundary_channels"][0]["geometry_refs"] == ["mesh-1"]


def test_preview_generation_does_not_mutate_source() -> None:
    """Repeated preview generation must leave the input scene and matrix unchanged."""
    scene, matrix = _fixture_inputs()
    original_scene = copy.deepcopy(scene)
    original_matrix = copy.deepcopy(matrix)

    build_preview_manifest(scene, matrix)

    assert scene == original_scene
    assert matrix == original_matrix


def test_preview_script_is_deterministic_and_output_only(tmp_path: Path) -> None:
    """Emit a Blender script that creates only the named preview collection."""
    scene, matrix = _fixture_inputs()
    first = write_preview_script(scene, matrix, tmp_path / "preview.py")
    second = write_preview_script(scene, matrix, tmp_path / "preview-again.py")

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    script = first.read_text(encoding="utf-8")
    assert "OM_AnalysisPreview" in script
    assert "source_geometry" in script
    assert "for obj in tuple(collection.objects)" in script
    assert "obj.get(\"om_analysis_preview\")" in script
    assert "OM_Boundary_" in script


def test_preview_html_contains_spatial_svg(tmp_path: Path) -> None:
    """Render source footprints and overlays together, not only as a table."""
    from ..adapters.blender_preview import write_preview_html

    scene, matrix = _fixture_inputs()
    manifest = build_preview_manifest(scene, matrix)
    output = write_preview_html(manifest, tmp_path / "preview.html")
    html = output.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "data-layer='source-geometry'" in html
    assert "data-layer='region'" in html
    assert "data-layer='trend-axis'" in html
    assert "data-layer='grid-axis'" in html
    assert "data-layer='gap-path'" in html
    assert "data-layer='boundary-channel'" in html


def test_bim_description_notebook_is_present() -> None:
    """Keep the executable notebook as the primary human inspection entry point."""
    notebook = json.loads(Path("test/bim_description_demo.ipynb").read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "build_preview_manifest" in source
    assert "boundary_channels" in source
    assert "trend_axes" in source
