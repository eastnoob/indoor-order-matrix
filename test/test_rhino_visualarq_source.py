"""Tests for the provider-neutral VisualARQ/Rhino source adapter."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.rhino_visualarq_source import normalize_visualarq_source


def test_normalize_preserves_identity_geometry_and_provenance() -> None:
    """Keep source facts while exposing authored IFC evidence separately."""
    report = normalize_visualarq_source(
        [
            {
                "id": "chair-1",
                "name": "Chair",
                "layer": "Furniture",
                "object_type": "Mesh",
                "vertices": [[0, 0, 0], [1, 0, 0]],
                "faces": [[0, 1, 1]],
                "user_text": {"IfcEntity": "IfcFurnishingElement"},
            }
        ],
        {"source_name": "room.3dm"},
    )

    item = report["objects"][0]
    assert report["schema_version"] == "visualarq-source-1"
    assert report["source_name"] == "room.3dm"
    assert item["id"] == "chair-1"
    assert item["source_name"] == "Chair"
    assert item["source_semantics"]["ifc_entity"] == "IfcFurnishingElement"
    assert item["provenance"]["raw_id"] == "chair-1"
    assert item["geometry"]["available"] is True


def test_missing_ifc_label_is_unknown_and_not_guessed() -> None:
    """Never infer an IFC class from a mesh type or a human-facing name."""
    report = normalize_visualarq_source(
        [{"id": "x", "name": "Wall maybe", "object_type": "Mesh"}]
    )

    item = report["objects"][0]
    assert item["source_semantics"]["ifc_entity"] == "unknown"
    assert item["source_semantics"]["confidence"] == "unknown"
    assert item["analysis_participation"] == "unknown"
    assert report["review_records"]


def test_malformed_top_level_input_fails_clearly() -> None:
    """Reject a non-record iterable before attempting partial normalization."""
    with pytest.raises(ValueError, match="records"):
        normalize_visualarq_source({"id": "not-a-record-list"})  # type: ignore[arg-type]


def test_om_ifc_entity_is_used_when_plain_ifc_entity_is_absent() -> None:
    """Read the VisualARQ-prefixed property when no plain label exists."""
    report = normalize_visualarq_source(
        [{"id": "wall-1", "user_text": {"OM.IfcEntity": "IfcWall"}}]
    )
    semantics = report["objects"][0]["source_semantics"]
    assert semantics == {
        "ifc_entity": "IfcWall",
        "ifc_entity_source": "OM.IfcEntity",
        "confidence": "authored",
    }


def test_invalid_label_becomes_unknown_with_review() -> None:
    """Keep unsupported authored values auditable instead of exporting guesses."""
    report = normalize_visualarq_source(
        [{"id": "x", "user_text": {"IfcEntity": "ChairMaybe"}}]
    )
    assert report["objects"][0]["source_semantics"]["ifc_entity"] == "unknown"
    assert report["review_records"][0]["reason"] == "unsupported_ifc_entity"


def test_required_building_and_grid_labels_stay_distinct() -> None:
    """Preserve authored building and grid classes without furniture fallback."""
    labels = [
        "IfcWall",
        "IfcDoor",
        "IfcWindow",
        "IfcColumn",
        "IfcBeam",
        "IfcSlab",
        "IfcGrid",
    ]
    report = normalize_visualarq_source(
        [{"id": label, "user_text": {"IfcEntity": label}} for label in labels]
    )
    assert [
        item["source_semantics"]["ifc_entity"] for item in report["objects"]
    ] == labels


def test_nested_instance_path_is_preserved_without_merging() -> None:
    """Keep repeated source instances separate for the later mapping phase."""
    report = normalize_visualarq_source(
        [
            {
                "id": "chair-a",
                "instance_definition": "Chair",
                "instance_path": ["Room", "Furniture", "Chair"],
                "analysis_participation": "include",
            },
            {
                "id": "chair-b",
                "instance_definition": "Chair",
                "instance_path": ["Room", "Furniture", "Chair"],
            },
        ]
    )
    assert len(report["objects"]) == 2
    assert report["objects"][0]["relationships"]["instance_path"] == [
        "Room",
        "Furniture",
        "Chair",
    ]
    assert report["objects"][0]["analysis_participation"] == "include"


def test_guides_are_separate_from_objects() -> None:
    """Keep authored guide records available for the dedicated grid adapter."""
    report = normalize_visualarq_source(
        [], {"visualarq_guides": [{"id": "axis-a", "name": "A"}]}
    )
    assert report["objects"] == []
    assert report["visualarq_guides"] == [{"id": "axis-a", "name": "A"}]


def test_decorative_object_can_be_excluded_without_being_deleted() -> None:
    """Represent an explicit analysis exclusion while retaining the source item."""
    report = normalize_visualarq_source(
        [{"id": "plant", "name": "Plant", "analysis_participation": "exclude"}]
    )
    assert len(report["objects"]) == 1
    assert report["objects"][0]["analysis_participation"] == "exclude"


def test_adapter_declares_that_downstream_phases_were_not_run() -> None:
    """Make the independent phase boundary machine-checkable."""
    report = normalize_visualarq_source([])
    assert report["exported_ifc"] is False
    assert report["imported_bonsai"] is False
