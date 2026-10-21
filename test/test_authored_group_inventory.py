from __future__ import annotations

from dataclasses import replace

from ..features._authored_group_inventory import _build_authored_group_inventory
from ..features.scene_contract import AuthoredGroup
from .test_neutral_scene_analysis_regression import _neutral_scene


def _scene_with_group_edge_cases():
    """Build authored group facts covering empty, malformed, shared, and generic input."""
    scene = _neutral_scene()
    return replace(
        scene,
        authored_groups=(
            AuthoredGroup("empty", "ifc-empty", (), "furniture_group", {"source": "fixture"}),
            AuthoredGroup("mixed", "ifc-mixed", ("left_table", "left_table", "missing"), "furniture_group"),
            AuthoredGroup("shared-a", "ifc-a", ("right_table",), "furniture_group"),
            AuthoredGroup("shared-b", "ifc-b", ("right_table",), "furniture_group"),
            AuthoredGroup("generic", "ifc-generic", ("left_table", "right_table"), "logical_group"),
        ),
    )


def test_inventory_preserves_authored_group_edges_without_collapsing_shared_members():
    """Keep raw group facts auditable while deriving unique, multi-group memberships."""
    inventory = _build_authored_group_inventory(_scene_with_group_edge_cases())

    by_id = {item["group_id"]: item for item in inventory["authored_groups"]}
    assert by_id["empty"]["member_refs"] == []
    assert by_id["empty"]["completeness_status"] == "empty_group"
    assert "empty" not in {item["group_id"] for item in inventory["eligible_groups"]}
    assert by_id["empty"] in inventory["input_audit"]

    mixed = by_id["mixed"]
    assert mixed["member_refs"] == ["left_table", "left_table", "missing"]
    assert mixed["unique_member_ids"] == ["left_table"]
    assert mixed["duplicate_refs"] == ["left_table"]
    assert mixed["unresolved_refs"] == ["missing"]
    assert mixed["completeness_status"] == "partial"

    assert inventory["member_group_ids"]["right_table"] == ["shared-a", "shared-b"]
    assert inventory["member_group_ids"]["left_table"] == ["mixed"]
    excluded = {item["group_id"]: item for item in inventory["excluded_groups"]}
    assert excluded["generic"]["reason"] == "non_furniture_group_role"
    assert excluded["generic"]["provenance"] == {}
    assert excluded["generic"]["member_refs"] == ["left_table", "right_table"]
    assert excluded["empty"]["provenance"] == {"source": "fixture"}
    assert excluded["empty"]["member_refs"] == []


def test_inventory_keeps_duplicate_source_ids_ambiguous():
    """Do not select an arbitrary object when a referenced source ID is duplicated."""
    scene = _scene_with_group_edge_cases()
    scene = replace(scene, source_objects=scene.source_objects + (scene.source_objects[0],))

    inventory = _build_authored_group_inventory(scene)
    record = next(
        item for item in inventory["authored_groups"]
        if item["group_id"] == "mixed"
    )
    eligible = next(item for item in inventory["eligible_groups"] if item["group_id"] == "mixed")

    assert record["ambiguous_refs"] == ["left_table"]
    assert "left_table" in record["unresolved_refs"]
    assert eligible["member_refs"] == []
