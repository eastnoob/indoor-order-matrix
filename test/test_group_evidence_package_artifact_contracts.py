"""Focused checks for group evidence package artifact declarations."""

from __future__ import annotations

from types import SimpleNamespace

from ..scripts.design.group_level import render_group_geometry_relation_field_ifc as geometry_runner
from ..scripts.design.group_level import run_group_trend_alignment_field_ifc as trend_runner


def test_geometry_contract_lists_overview_and_every_pair_artifact() -> None:
    """Geometry contracts enumerate all generated pair files and the overview."""
    envelopes = tuple(
        SimpleNamespace(
            target={"id": f"pair-{index}"},
            query={"plane": "world-xy"},
            provenance={"algorithm_version": "algo-v1", "schema_version": "schema-v1"},
            channel_set=("gap", "contact"),
        )
        for index in range(2)
    )

    contract = geometry_runner._package_contract(
        {"group_geometry": []},
        envelopes,
        {"group_selection_rule": "authored"},
        {"name": "world-xy"},
        "source-sha256",
    )

    assert contract["artifacts"]["overview"] == "overview.svg"
    assert contract["artifacts"]["pair_json"] == ["pairs/0000.json", "pairs/0001.json"]
    assert contract["artifacts"]["pair_svg"] == ["pairs/0000.svg", "pairs/0001.svg"]


def test_trend_contract_lists_each_visualization() -> None:
    """Trend contracts retain generated visualization paths as artifact references."""
    envelope = SimpleNamespace(
        target={"id": "group-1"},
        provenance={"algorithm_version": "algo-v1", "schema_version": "schema-v1"},
    )
    query = SimpleNamespace(plane="world-xy", revision="test")

    contract = trend_runner._package_contract(
        {"group_geometry": []},
        (envelope,),
        {"selection": "authored"},
        query,
        {"name": "world-xy"},
        "source-sha256",
        ["visualizations/group-1__layout.svg"],
    )

    assert contract["artifacts"]["visualizations"] == ["visualizations/group-1__layout.svg"]
