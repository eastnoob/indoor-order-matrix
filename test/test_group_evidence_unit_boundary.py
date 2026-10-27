"""Focused contract checks for the furniture-group evidence boundary."""

from __future__ import annotations

from types import SimpleNamespace

from ..features.field_core import FieldQuery, FieldResultStatus
from ..features.scene_contract import AnalysisPlane


def _scene_and_query():
    """Return the smallest scene/query pair accepted by the field adapters."""
    plane = AnalysisPlane(
        name="test-plan",
        origin=(0.0, 0.0, 0.0),
        basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    )
    return SimpleNamespace(context=SimpleNamespace(analysis_plane=plane)), FieldQuery(
        plane=plane,
        frame=plane.name,
        revision="test",
    )


def test_trend_package_suppresses_member_channels(monkeypatch):
    """Member direction descriptors remain audit data, not public channels."""
    from ..features import group_trend_alignment_field as module

    scene, query = _scene_and_query()
    monkeypatch.setattr(
        module,
        "describe_group_relations",
        lambda _scene: {
            "status": "computed",
            "analysis_frame": {"plane": "test-plan"},
            "group_geometry": [
                {
                    "target_id": "group-a",
                    "member_geometry": [{"member_id": "member-a"}],
                    "trend_descriptors": {
                        "status": "computed",
                        "overall_group_axis": {"angle": 0.0, "strength": 1.0},
                        "layout_axis": {"angle": 0.0, "strength": 1.0},
                        "member_frame": {"angle": 0.0, "strength": 1.0},
                        "member_axis": {"angle": 0.0, "strength": 1.0},
                        "member_bindings": [{"source_object_id": "member-a"}],
                    },
                }
            ],
        },
    )
    envelopes = module.build_group_trend_alignment_envelopes(
        scene,
        query=query,
        input_fingerprint="input",
        source_fingerprint="source",
        recipe_fingerprint="recipe",
        algorithm_version="algorithm",
        schema_version="schema",
    )

    assert len(envelopes) == 1
    envelope = envelopes[0]
    assert set(envelope.channel_set) == {"overall_group_axis", "layout_axis"}
    assert "member_frame" not in envelope.channel_set
    assert "member_axis" not in envelope.channel_set
    assert set(envelope.provenance["suppressed_channels"]) == {"member_frame", "member_axis"}
    assert all(
        "suppressed_member_channels" in record.observation
        and "member_bindings_audit" in record.observation
        for record in envelope.value["channels"]
    )


def test_geometry_package_marks_member_pairs_as_audit_only(monkeypatch):
    """Raw member observations remain replayable without becoming group answers."""
    from ..features import group_geometry_relation_field as module

    scene, query = _scene_and_query()
    monkeypatch.setattr(
        module,
        "describe_group_relations",
        lambda _scene: {
            "status": "computed",
            "group_relations": [
                {
                    "group_a": "group-a",
                    "group_b": "group-b",
                    "status": "computed",
                    "unit": "m",
                    "analysis_frame": "test-plan",
                    "tolerance": {"geometry": 1e-6},
                    "shared_member_dependency": {"status": "not_applicable", "member_ids": []},
                    "member_pair_observations": [
                        {
                            "member_a": "member-a",
                            "member_b": "member-b",
                            "status": "computed",
                            "raw_boundary_gap": 1.0,
                            "normalized_boundary_gap": 0.5,
                            "normalization": {"method": "test", "denominator": 2.0},
                            "contact": False,
                            "overlap": False,
                            "overlap_area": 0.0,
                            "witness": {"source_refs": ["mesh-a", "mesh-b"]},
                        }
                    ],
                }
            ],
        },
    )
    envelope = module.build_group_geometry_relation_envelopes(
        scene,
        query=query,
        input_fingerprint="input",
        source_fingerprint="source",
        recipe_fingerprint="recipe",
        algorithm_version="algorithm",
        schema_version="schema",
    )[0]

    assert envelope.raw_status is FieldResultStatus.COMPUTED
    assert all(record.observation["member_pairs_role"] == "audit_only" for record in envelope.value["channels"])
    assert all(
        record.observation["group_pair_aggregation"]["status"] == "deferred"
        for record in envelope.value["channels"]
    )
    assert envelope.provenance["member_pair_role"] == "audit_only"
    assert envelope.provenance["historical_relation_inventory"]["position_grammar"]["status"] == "not_attached"
