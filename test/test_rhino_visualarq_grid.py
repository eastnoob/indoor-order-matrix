"""Tests for converting VisualARQ Guide evidence into native IFC grids."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test" / "bim"))

from adapters.ifc_bonsai import load_ifc_neutral_scene
from adapters.rhino_visualarq_grid import normalize_visualarq_guides
from export_rhino_source_ifc import write_ifc


def _guide(
    identifier: str,
    tag: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> dict[str, object]:
    """Build one compact serialized VisualARQ Guide fixture."""
    return {
        "id": identifier,
        "name": tag,
        "definition_name": f"*Guide{{{identifier}}}",
        "curves": [
            {"kind": "ArcCurve", "points": [[0, 0, 0], [4, 0, 0]]},
            {"kind": "LineCurve", "points": [list(start), list(end)]},
        ],
    }


def _source_payload() -> dict[str, object]:
    """Return one furniture object plus a rotated two-axis VisualARQ grid."""
    return {
        "source_name": "visualarq-grid-test",
        "objects": [
            {
                "id": "chair-1",
                "kind": "chair",
                "vertices": [[0, 0, 0], [1000, 0, 0], [0, 1000, 0]],
                "faces": [[0, 1, 2]],
                "source_ids": ["chair-1"],
            }
        ],
        "visualarq_guides": [
            _guide("guide-3", "3", (0, 0, 0), (10000, 10000, 0)),
            _guide("guide-k", "K", (0, 10000, 0), (10000, 0, 0)),
        ],
    }


def test_normalizer_extracts_axes_and_groups_relative_directions() -> None:
    """Guide labels and long axis geometry survive rotation-independent grouping."""
    grid = normalize_visualarq_guides(_source_payload()["visualarq_guides"])

    assert grid["id"] == "visualarq-grid"
    assert [axis["tag"] for axis in grid["u_axes"]] == ["3"]
    assert [axis["tag"] for axis in grid["v_axes"]] == ["K"]
    assert grid["u_axes"][0]["curve_points"] == (
        (0.0, 0.0, 0.0),
        (10000.0, 10000.0, 0.0),
    )


def test_exported_visualarq_guides_round_trip_as_authored_grid(tmp_path: Path) -> None:
    """Native IFC grid output remains readable by the existing Bonsai adapter."""
    source = tmp_path / "source.json"
    target = tmp_path / "grid.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")

    report = write_ifc(source, target)

    import ifcopenshell

    model = ifcopenshell.open(str(target))
    grids = model.by_type("IfcGrid")
    assert report["grid_count"] == 1
    assert len(grids) == 1
    assert [axis.AxisTag for axis in grids[0].UAxes] == ["3"]
    assert [axis.AxisTag for axis in grids[0].VAxes] == ["K"]
    assert grids[0].WAxes is None
    assert grids[0].ObjectPlacement is not None

    scene = load_ifc_neutral_scene(target)
    assert len(scene.authored_grids) == 1
    assert len(scene.authored_grid_axes) == 2
    assert scene.context.capability_flags["authored_grid"] is True


def test_grid_exporter_command_can_import_project_adapter(tmp_path: Path) -> None:
    """The documented standalone exporter command must resolve project adapters."""
    source = tmp_path / "source.json"
    target = tmp_path / "grid.ifc"
    source.write_text(json.dumps(_source_payload()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "test" / "bim" / "export_rhino_source_ifc.py"),
            str(source),
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
