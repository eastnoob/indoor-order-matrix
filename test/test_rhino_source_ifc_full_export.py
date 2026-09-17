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


def _export_payload(
    payload: dict[str, object], tmp_path: Path
) -> tuple[object, dict[str, object]]:
    """Run the standalone exporter for one complete source payload."""
    source = tmp_path / "source.json"
    target = tmp_path / "result.ifc"
    source.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(EXPORTER), str(source), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return ifcopenshell.open(target), json.loads(target.with_suffix(".export.json").read_text(encoding="utf-8"))


def _export(records: list[dict[str, object]], tmp_path: Path) -> tuple[object, dict[str, object]]:
    """Run the standalone exporter for ordinary source object records."""
    return _export_payload(
        {"source_name": "full-export-fixture", "objects": records}, tmp_path
    )


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


def test_repeated_type_display_names_still_have_unique_type_global_ids(tmp_path: Path) -> None:
    """Use family identity when two furniture families share one label."""
    first = _record("chair-a", ifc_entity="IfcFurniture", name="Chair")
    first.update({"kind": "chair", "type_family_id": "family-a"})
    second = _record("chair-b", ifc_entity="IfcFurniture", name="Chair")
    second.update({"kind": "chair", "type_family_id": "family-b"})
    model, _ = _export([first, second], tmp_path)

    ids = [entity.GlobalId for entity in model.by_type("IfcFurnitureType")]
    assert len(ids) == 2
    assert len(set(ids)) == 2
    rooted_ids = [entity.GlobalId for entity in model if hasattr(entity, "GlobalId")]
    assert len(rooted_ids) == len(set(rooted_ids))


def test_source_traceability_is_external_and_ifc_has_no_om_source_pset(
    tmp_path: Path,
) -> None:
    """Keep source mapping in the export report instead of custom IFC metadata."""
    model, report = _export(
        [_record("decor-1", name="Decorative object")],
        tmp_path,
    )

    assert not [
        pset
        for pset in model.by_type("IfcPropertySet")
        if pset.Name == "OM_Source"
    ]
    assert report["source_map"] == [
        {
            "source_id": "decor-1",
            "ifc_global_id": model.by_type("IfcBuildingElementProxy")[0].GlobalId,
            "ifc_entity": "IfcBuildingElementProxy",
            "semantic_status": "untyped",
        }
    ]
    layout = next(
        pset for pset in model.by_type("IfcPropertySet") if pset.Name == "OM_Layout"
    )
    values = {prop.Name: prop.NominalValue.wrappedValue for prop in layout.HasProperties}
    assert values["AnalysisParticipation"] == "unknown"


def test_embedded_masspatch_uses_same_furniture_analysis_representation(
    tmp_path: Path,
) -> None:
    """Keep a nested proxy as analysis geometry on its owning furniture product."""
    record = _record("chair-with-patch", ifc_entity="IfcFurniture", name="Chair")
    record.update(
        {
            "kind": "chair",
            "type_family_id": "chair-family",
            "analysis_substitutes": [
                {
                    "substitute_id": "chair-with-patch:masspatch",
                    "substitute_kind": "MassPatch",
                    "vertices": [[0, 0, 0], [2, 0, 0], [0, 2, 0]],
                    "triangle_indices": [[0, 1, 2]],
                }
            ],
        }
    )

    model, report = _export([record], tmp_path)

    furniture = model.by_type("IfcFurniture")
    assert len(furniture) == 1
    assert len(model.by_type("IfcBuildingElementProxy")) == 0
    contexts = {
        representation.ContextOfItems.ContextIdentifier
        for representation in furniture[0].Representation.Representations
    }
    assert contexts == {"Body", "Analysis"}
    assert report["analysis_representation_count"] == 1
    assert len(
        [pset for pset in model.by_type("IfcPropertySet") if pset.Name == "OM_AnalysisRepresentation"]
    ) == 1


def test_source_without_embedded_masspatch_keeps_body_only(tmp_path: Path) -> None:
    """Preserve the old body-only export contract when no proxy branch exists."""
    record = _record("plain-chair", ifc_entity="IfcFurniture", name="Chair")
    record.update({"kind": "chair", "type_family_id": "chair-family"})

    model, report = _export([record], tmp_path)

    furniture = model.by_type("IfcFurniture")
    contexts = {
        representation.ContextOfItems.ContextIdentifier
        for representation in furniture[0].Representation.Representations
    }
    assert contexts == {"Body"}
    assert report["analysis_representation_count"] == 0


def test_authored_furniture_group_relates_only_explicit_furniture_members(
    tmp_path: Path,
) -> None:
    """Serialize an authored furniture group without grouping other products."""
    table = _record("table", ifc_entity="IfcFurniture", name="Table")
    table.update({"kind": "table", "type_family_id": "table-family"})
    chair = _record("chair", ifc_entity="IfcFurniture", name="Chair")
    chair.update({"kind": "chair", "type_family_id": "chair-family"})
    wall = _record("wall", ifc_entity="IfcWall", name="Wall")

    model, report = _export_payload(
        {
            "source_name": "group-fixture",
            "objects": [table, chair, wall],
            "furniture_groups": [
                {"id": "table-set-1", "member_ids": ["table", "chair", "wall"]}
            ],
        },
        tmp_path,
    )

    groups = model.by_type("IfcGroup")
    assert len(groups) == 1
    assert groups[0].ObjectType == "furniture_group"
    relations = list(groups[0].IsGroupedBy)
    assert len(relations) == 1
    assert {member.Tag for member in relations[0].RelatedObjects} == {"table", "chair"}
    assert report["furniture_group_count"] == 1
    assert report["source_model_group_count"] == 0


def test_repeated_authored_groups_keep_distinct_memberships(tmp_path: Path) -> None:
    """Create one IFC group per authored outer Block occurrence."""
    records = []
    for identifier, name in (
        ("table-a", "Table A"),
        ("chair-a", "Chair A"),
        ("table-b", "Table B"),
        ("chair-b", "Chair B"),
    ):
        record = _record(identifier, ifc_entity="IfcFurniture", name=name)
        record.update({"kind": "furniture", "type_family_id": "shared-family"})
        records.append(record)

    model, report = _export_payload(
        {
            "objects": records,
            "furniture_groups": [
                {"id": "outer-a", "member_ids": ["table-a", "chair-a"]},
                {"id": "outer-b", "member_ids": ["table-b", "chair-b"]},
            ],
        },
        tmp_path,
    )

    groups = model.by_type("IfcGroup")
    assert len(groups) == 2
    assert len({group.GlobalId for group in groups}) == 2
    memberships = [
        {member.Tag for member in next(iter(group.IsGroupedBy)).RelatedObjects}
        for group in groups
    ]
    assert {frozenset(members) for members in memberships} == {
        frozenset({"table-a", "chair-a"}),
        frozenset({"table-b", "chair-b"}),
    }
    assert report["furniture_group_count"] == 2


def test_empty_authored_group_is_reported_without_creating_ifc_group(
    tmp_path: Path,
) -> None:
    """Avoid fabricating an IFC group when it has no valid furniture member."""
    model, report = _export_payload(
        {
            "objects": [_record("wall", ifc_entity="IfcWall", name="Wall")],
            "furniture_groups": [{"id": "outer-empty", "member_ids": ["wall"]}],
        },
        tmp_path,
    )

    assert not model.by_type("IfcGroup")
    assert report["furniture_group_count"] == 0
    assert report["furniture_group_review"] == [
        {
            "group_id": "outer-empty",
            "member_id": "wall",
            "reason": "missing_or_non_furniture_member",
        },
        {"group_id": "outer-empty", "reason": "no_valid_furniture_members"},
    ]
