"""Tests for full-fidelity Rhino source IFC export."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import ifcopenshell


ROOT = Path(__file__).parents[1]
EXPORTER = ROOT / "test" / "bim" / "export_rhino_source_ifc.py"


def _record(
    identifier: str,
    *,
    ifc_entity: str | None = None,
    name: str = "",
    layer: str = "Default",
) -> dict[str, object]:
    """Build one minimal source object with a triangle that can be exported."""
    record: dict[str, object] = {
        "id": identifier,
        "name": name,
        "layer": layer,
        "source_kind": "mesh",
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        "faces": [[0, 1, 2]],
        "analysis_participation": "unknown",
    }
    if ifc_entity is not None:
        record["source_semantics"] = {
            "ifc_entity": ifc_entity,
            "ifc_entity_source": "IfcEntity",
            "confidence": "authored",
        }
    return record


def _export(records: list[dict[str, object]], tmp_path: Path) -> tuple[object, dict[str, object]]:
    """Run the standalone exporter and return the IFC model and report."""
    source = tmp_path / "source.json"
    target = tmp_path / "result.ifc"
    source.write_text(json.dumps({"source_name": "full-export-fixture", "objects": records}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(EXPORTER), str(source), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return ifcopenshell.open(target), json.loads(target.with_suffix(".export.json").read_text(encoding="utf-8"))


def test_authored_entity_classes_are_preserved_and_unknown_is_proxy(tmp_path: Path) -> None:
    """Export typed products distinctly and retain untyped geometry as a proxy."""
    model, report = _export(
        [
            _record("wall-1", ifc_entity="IfcWall", name="Wall"),
            _record("chair-1", ifc_entity="IfcFurnishingElement", name="Chair"),
            _record("unknown-1", name="Decorative object"),
        ],
        tmp_path,
    )

    assert len(model.by_type("IfcWall")) == 1
    assert len(model.by_type("IfcFurnishingElement")) == 1
    assert len(model.by_type("IfcBuildingElementProxy")) == 1
    assert report["entity_counts"] == {
        "IfcBuildingElementProxy": 1,
        "IfcFurnishingElement": 1,
        "IfcWall": 1,
    }
    assert report["untyped_count"] == 1
    assert report["source_object_count"] == 3


def test_unsupported_label_falls_back_to_review_proxy(tmp_path: Path) -> None:
    """Do not instantiate a non-product or unsupported authored class."""
    model, report = _export(
        [_record("axis-1", ifc_entity="IfcGridAxis", name="Grid axis")],
        tmp_path,
    )

    assert len(model.by_type("IfcGridAxis")) == 0
    assert len(model.by_type("IfcBuildingElementProxy")) == 1
    assert report["review_count"] == 1
    assert report["entity_counts"]["IfcBuildingElementProxy"] == 1


def test_every_source_object_is_exported_once(tmp_path: Path) -> None:
    """Prevent full-export mode from duplicating source occurrences."""
    model, report = _export(
        [_record("a"), _record("b", ifc_entity="IfcWall"), _record("c", ifc_entity="IfcDoor")],
        tmp_path,
    )
    products = [
        entity
        for entity in model.by_type("IfcProduct")
        if entity.is_a("IfcWall") or entity.is_a("IfcDoor") or entity.is_a("IfcBuildingElementProxy")
    ]
    assert len(products) == 3
    assert report["geometry_skipped_count"] == 0


def test_unusable_geometry_does_not_block_other_source_objects(tmp_path: Path) -> None:
    """Skip non-surface source records while reporting the skipped count."""
    unusable = {"id": "point-1", "name": "Reference point"}
    model, report = _export([_record("wall-1", ifc_entity="IfcWall"), unusable], tmp_path)
    assert len(model.by_type("IfcWall")) == 1
    assert report["source_object_count"] == 2
    assert report["geometry_skipped_count"] == 1


def test_repeated_display_names_still_have_unique_ifc_global_ids(tmp_path: Path) -> None:
    """Use source identity, rather than repeated Rhino names, for IFC GUIDs."""
    model, _ = _export(
        [
            _record("first", name="Object"),
            _record("second", name="Object"),
        ],
        tmp_path,
    )
    ids = [entity.GlobalId for entity in model.by_type("IfcBuildingElementProxy")]
    assert len(ids) == 2
    assert len(set(ids)) == 2
