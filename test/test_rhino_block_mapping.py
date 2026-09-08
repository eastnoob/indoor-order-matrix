"""Tests for the incremental Rhino nested-Block mapping adapter."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.rhino_block_mapping import normalize_rhino_blocks


EXAMPLE_CHAIR = {
    "instances": [
        {
            "id": "chair_001",
            "definition": "exampleChair",
            "user_text": {
                "OM.Role": "logical_product",
                "OM.IfcEntity": "IfcFurniture",
                "OM.TypeKey": "chair.standard",
                "OM.InstanceId": "chair_001",
            },
            "children": [
                {
                    "id": "chair_001_geometry",
                    "definition": "exampleChair-geometry",
                    "user_text": {"OM.RepresentationRole": "display_geometry"},
                    "components": [
                        {
                            "id": "seat",
                            "type": "Mesh",
                            "kind": "chair",
                            "geometry_signature": "chair-mesh-v1",
                        }
                    ],
                },
                {
                    "id": "chair_001_masspatch",
                    "definition": "exampleChair-MassPatch",
                    "user_text": {
                        "OM.RepresentationRole": "analysis_substitute",
                        "OM.SubstituteKind": "MassPatch",
                        "OM.VisibilityPolicy": "analysis_only",
                        "OM.SourceInstanceId": "chair_001",
                    },
                    "components": [
                        {
                            "id": "patch-seat",
                            "type": "Brep",
                            "kind": "MassPatch",
                            "geometry_signature": "chair-patch-v1",
                        }
                    ],
                },
            ],
        }
    ]
}


def test_example_chair_is_one_product_with_two_representations() -> None:
    """Keep display and analysis Blocks attached to one logical product."""
    report = normalize_rhino_blocks(EXAMPLE_CHAIR)

    assert report["status"] == "passed"
    assert len(report["logical_objects"]) == 1
    assert report["logical_objects"][0]["id"] == "chair_001"
    assert {item["representation_role"] for item in report["representations"]} == {
        "display_geometry",
        "analysis_substitute",
    }
    masspatch = next(
        item
        for item in report["representations"]
        if item["representation_role"] == "analysis_substitute"
    )
    assert masspatch["substitute_kind"] == "MassPatch"
    assert masspatch["source_instance_id"] == "chair_001"


def test_repeated_roots_share_type_but_keep_occurrences() -> None:
    """Reuse one type family while preserving two placed product occurrences."""
    second = {
        **EXAMPLE_CHAIR["instances"][0],
        "id": "chair_002",
        "user_text": {
            **EXAMPLE_CHAIR["instances"][0]["user_text"],
            "OM.InstanceId": "chair_002",
        },
    }
    report = normalize_rhino_blocks({"instances": [EXAMPLE_CHAIR["instances"][0], second]})

    assert len(report["type_families"]) == 1
    assert len(report["occurrences"]) == 2


def test_unlabelled_child_requires_supervisor_review() -> None:
    """Do not guess whether an unlabelled child is display or analysis geometry."""
    ambiguous = {
        "instances": [
            {
                "id": "chair_ambiguous",
                "definition": "Chair",
                "user_text": {
                    "OM.Role": "logical_product",
                    "OM.TypeKey": "chair.standard",
                },
                "children": [{"id": "child_without_role", "components": []}],
            }
        ]
    }

    report = normalize_rhino_blocks(ambiguous)

    assert report["status"] == "blocked"
    assert report["manual_review"][0]["reason"] == "unresolved_representation_role"
