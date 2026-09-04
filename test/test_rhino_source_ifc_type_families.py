"""Regression tests for normalized IFC type-family handoff."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import ifcopenshell

ROOT = Path(__file__).parents[1]
EXPORTER = ROOT / "test" / "bim" / "export_rhino_source_ifc.py"


def _record(identifier: str, family_id: str) -> dict[str, object]:
    """Build one minimal logical product for exporter contract testing."""
    return {
        "id": identifier,
        "kind": "chair",
        "type_family_id": family_id,
        "source_model": identifier,
        "source_ids": [identifier],
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        "faces": [[0, 1, 2]],
    }


def test_exporter_preserves_distinct_normalized_type_families(tmp_path: Path) -> None:
    """Do not collapse different normalized geometries by broad semantic kind."""
    source = tmp_path / "normalized.json"
    target = tmp_path / "result.ifc"
    source.write_text(
        json.dumps(
            {
                "source_name": "type-family-fixture",
                "objects": [
                    _record("chair-a", "chair-family-v1"),
                    _record("chair-b", "chair-family-v2"),
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(EXPORTER), str(source), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(target.with_suffix(".export.json").read_text(encoding="utf-8"))
    assert report["furniture_count"] == 2
    assert report["furniture_type_count"] == 2


def test_exporter_assigns_readable_occurrence_names(tmp_path: Path) -> None:
    """Use semantic occurrence names when normalized records lack display names."""
    source = tmp_path / "normalized.json"
    target = tmp_path / "result.ifc"
    source.write_text(
        json.dumps(
            {
                "source_name": "naming-fixture",
                "objects": [
                    _record("rhino-group-0", "chair-family"),
                    _record("rhino-group-1", "chair-family"),
                    {
                        **_record("rhino-group-2", "table-family"),
                        "kind": "table",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(EXPORTER), str(source), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    model = ifcopenshell.open(target)
    assert [entity.Name for entity in model.by_type("IfcFurniture")] == [
        "Chair_01",
        "Chair_02",
        "Table_01",
    ]
    assert [entity.Name for entity in model.by_type("IfcFurnitureType")] == [
        "ChairType",
        "TableType",
    ]
