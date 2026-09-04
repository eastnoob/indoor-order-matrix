"""Behavior tests for generic logical-object and type-family mapping."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "normalize_logical_objects.py"


def _component(
    component_id: str,
    group_id: str,
    role: str,
    geometry_signature: str,
    center: tuple[float, float, float],
) -> dict[str, object]:
    """Build one source component with type-defining and occurrence facts."""
    return {
        "id": component_id,
        "group_ids": [group_id],
        "role": role,
        "geometry_signature": geometry_signature,
        "center": list(center),
    }


def _payload() -> dict[str, object]:
    """Build a generic scene with repeated products and one geometric variant."""
    return {
        "source_name": "generic-repetition-fixture",
        "groups": [
            {"id": "product-a", "member_ids": ["a-seat", "a-back"]},
            {"id": "product-b", "member_ids": ["b-seat", "b-back"]},
            {"id": "product-c", "member_ids": ["c-seat", "c-back"]},
        ],
        "components": [
            _component("a-seat", "product-a", "seat", "seat-v1", (0, 0, 0)),
            _component("a-back", "product-a", "back", "back-v1", (0, 1, 0)),
            _component("b-seat", "product-b", "seat", "seat-v1", (10, 0, 0)),
            _component("b-back", "product-b", "back", "back-v1", (10, 1, 0)),
            _component("c-seat", "product-c", "seat", "seat-v2", (20, 0, 0)),
            _component("c-back", "product-c", "back", "back-v1", (20, 1, 0)),
        ],
    }


def _run(payload: dict[str, object], tmp_path: Path) -> dict[str, object]:
    """Run the standalone normalizer against a temporary JSON source."""
    if not SCRIPT.exists():
        pytest.fail(f"feature missing: {SCRIPT}")
    source = tmp_path / "source.json"
    target = tmp_path / "normalized.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(source), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(target.read_text(encoding="utf-8"))


def test_repeated_products_share_one_type_family_and_keep_occurrences(
    tmp_path: Path,
) -> None:
    """Keep two identical products as occurrences under one reusable type."""
    report = _run(_payload(), tmp_path)

    assert report["status"] == "passed"
    assert len(report["logical_objects"]) == 3
    assert len(report["type_families"]) == 2
    repeated = [
        family
        for family in report["type_families"]
        if len(family["member_object_ids"]) == 2
    ]
    assert len(repeated) == 1
    assert repeated[0]["geometry_reuse"] == "shared_candidate"
    assert len(report["occurrences"]) == 3
    assert {
        occurrence["logical_object_id"] for occurrence in report["occurrences"]
    } == {"product-a", "product-b", "product-c"}


def test_occurrence_position_does_not_change_type_identity(tmp_path: Path) -> None:
    """Ignore translation and rotation-level placement facts in type matching."""
    payload = _payload()
    payload["components"][2]["center"] = [1000, -200, 500]
    payload["components"][3]["center"] = [1000, -199, 500]
    report = _run(payload, tmp_path)

    repeated = [
        family
        for family in report["type_families"]
        if len(family["member_object_ids"]) == 2
    ]
    assert len(repeated) == 1
    placements = {
        item["logical_object_id"]: item["placement"]["center"]
        for item in report["occurrences"]
    }
    assert placements["product-a"] != placements["product-b"]


def test_geometry_variant_does_not_claim_shared_geometry(tmp_path: Path) -> None:
    """Keep a functional variant separate from a shared geometry family."""
    report = _run(_payload(), tmp_path)

    variant = [
        family
        for family in report["type_families"]
        if family["member_object_ids"] == ["product-c"]
    ]
    assert len(variant) == 1
    assert variant[0]["geometry_reuse"] == "not_shared"
    assert report["ambiguous_candidates"] == []


def test_incomplete_candidate_is_reported_instead_of_exported(tmp_path: Path) -> None:
    """Reject an explicitly incomplete group without silently creating furniture."""
    payload = {
        "source_name": "fragment-fixture",
        "groups": [
            {
                "id": "fragment",
                "member_ids": ["leg-only"],
                "functional_complete": False,
            }
        ],
        "components": [
            _component("leg-only", "fragment", "leg", "leg-v1", (0, 0, 0))
        ],
    }
    report = _run(payload, tmp_path)

    assert report["logical_objects"] == []
    assert report["type_families"] == []
    assert report["ambiguous_candidates"][0]["group_id"] == "fragment"
    assert report["ambiguous_candidates"][0]["reason"] == "incomplete_candidate"


def test_mapping_prefers_meaningful_authored_names_and_ignores_generated_names(
    tmp_path: Path,
) -> None:
    """Prefer authored names, but replace generated group labels with semantic names."""
    payload = {
        "source_name": "naming-fixture",
        "groups": [
            {
                "id": "rhino-group-0",
                "name": "Chair",
                "kind": "chair",
                "member_ids": ["chair-0"],
            },
            {
                "id": "rhino-group-1",
                "name": "Chair",
                "kind": "chair",
                "member_ids": ["chair-1"],
            },
            {
                "id": "Group702",
                "name": "Group702",
                "kind": "table",
                "member_ids": ["table-0"],
            },
        ],
        "components": [
            _component("chair-0", "rhino-group-0", "chair", "chair-v1", (0, 0, 0)),
            _component("chair-1", "rhino-group-1", "chair", "chair-v1", (2, 0, 0)),
            _component("table-0", "Group702", "table", "table-v1", (1, 1, 0)),
        ],
    }

    report = _run(payload, tmp_path)

    assert [item["display_name"] for item in report["logical_objects"]] == [
        "Chair_01",
        "Chair_02",
        "Table_01",
    ]
