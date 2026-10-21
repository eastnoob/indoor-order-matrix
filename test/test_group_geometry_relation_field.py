"""IFC-driven contract tests for the geometry-only group relation field."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest


def test_specified_ifc_group_pairs_produce_descriptive_envelopes(monkeypatch) -> None:
    """Check the envelope contract against authored pairs from the pinned IFC."""
    from ..adapters.ifc_bonsai import load_ifc_neutral_scene
    from ..features.field_core import FieldQuery, FieldResultStatus
    from ..features.group_self_description import (
        _member_pair_observation,
        _member_record,
        describe_group_relations,
    )
    from ..features.group_geometry_relation_field import (
        _result_status,
        build_group_geometry_relation_envelopes,
    )
    from ..features import group_geometry_relation_field
    from ..scripts.design.group_level import render_group_geometry_relation_field_ifc

    repository = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (repository / "docs/project/evidence/group-attribution-ifc-source-manifest.json")
        .read_text(encoding="utf-8")
    )
    source = repository / manifest["source"]["workspace_relative_path"]
    before = render_group_geometry_relation_field_ifc.fingerprint(source)
    assert before == {
        "path": str(source.resolve()),
        "byte_length": manifest["source"]["byte_length"],
        "sha256": manifest["source"]["sha256_before"],
    }
    digest = before["sha256"]

    scene = load_ifc_neutral_scene(source)
    query = FieldQuery(
        domain_id=None,
        frame=scene.context.analysis_plane.name,
        plane=scene.context.analysis_plane,
        tolerance=float(scene.context.geometry_tolerance),
        revision="group-geometry-relation/v1",
    )
    mismatched_query = replace(
        query,
        plane=replace(query.plane, name=f"{query.plane.name}-mismatch"),
    )
    with pytest.raises(ValueError, match="query plane must equal the scene analysis plane"):
        build_group_geometry_relation_envelopes(
            scene,
            query=mismatched_query,
            input_fingerprint=digest,
            source_fingerprint=digest,
            recipe_fingerprint="geometry-only-relation/v1",
            algorithm_version="group-geometry-relation/v1",
            schema_version="group-geometry-relation-field/v1",
        )

    description = describe_group_relations(scene)
    monkeypatch.setattr(
        group_geometry_relation_field,
        "describe_group_relations",
        lambda _scene: description,
    )
    envelopes = build_group_geometry_relation_envelopes(
        scene,
        query=query,
        input_fingerprint=digest,
        source_fingerprint=digest,
        recipe_fingerprint="geometry-only-relation/v1",
        algorithm_version="group-geometry-relation/v1",
        schema_version="group-geometry-relation-field/v1",
    )
    replayed_envelopes = build_group_geometry_relation_envelopes(
        scene,
        query=query,
        input_fingerprint=digest,
        source_fingerprint=digest,
        recipe_fingerprint="geometry-only-relation/v1",
        algorithm_version="group-geometry-relation/v1",
        schema_version="group-geometry-relation-field/v1",
    )
    assert replayed_envelopes == envelopes
    assert [envelope.cache_identity for envelope in replayed_envelopes] == [
        envelope.cache_identity for envelope in envelopes
    ]

    expected_members_by_group = {
        f"ifc-group:{group['global_id']}": sorted(
            f"ifc-object:{member['global_id']}" for member in group["members"]
        )
        for group in manifest["groups"]
    }
    group_ids = sorted(expected_members_by_group)
    assert [item["eligible_group_id"] for item in description["eligibility"]] == group_ids
    assert {
        item["eligible_group_id"]: item["member_object_ids"]
        for item in description["eligibility"]
    } == expected_members_by_group
    assert [item["target_id"] for item in description["group_geometry"]] == group_ids
    assert all(
        item["geometry_completeness"]["declared_members"]
        == len(expected_members_by_group[item["target_id"]])
        and item["geometry_completeness"]["usable_members"]
        == len(item["member_geometry"])
        for item in description["group_geometry"]
    )

    expected_ids = {
        json.dumps(
            list(pair),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for pair in itertools.combinations(sorted(group_ids), 2)
    }
    relation_ids = [
        json.dumps(
            sorted((relation["group_a"], relation["group_b"])),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for relation in description["group_relations"]
    ]
    assert relation_ids == sorted(relation_ids)
    assert [envelope.target["id"] for envelope in envelopes] == sorted(expected_ids)
    assert {envelope.target["id"] for envelope in envelopes} == expected_ids
    assert all(envelope.target["kind"] == "furniture_group_pair" for envelope in envelopes)
    assert all(envelope.target["identity"] for envelope in envelopes)
    assert all(envelope.query == query for envelope in envelopes)
    assert all(envelope.field_projection is None for envelope in envelopes)
    assert all(envelope.support is None for envelope in envelopes)
    assert all(
        set(envelope.channel_set)
        == {"boundary_gap", "contact", "positive_area_overlap"}
        for envelope in envelopes
    )
    assert all(
        record.polarity == "descriptive" and record.support is None
        for envelope in envelopes
        for record in envelope.value["channels"]
    )
    assert all(
        envelope.cache_identity["source_fingerprint"] == digest
        and envelope.cache_identity["input_fingerprint"] == digest
        and envelope.cache_identity["identity"]
        for envelope in envelopes
    )

    sources_by_id = {source_record.id: source_record for source_record in scene.source_objects}
    geometry_refs_by_member = {
        member_id: tuple(sorted(sources_by_id[member_id].geometry_refs))
        for member_ids in expected_members_by_group.values()
        for member_id in member_ids
    }
    relation_by_id = dict(zip(relation_ids, description["group_relations"], strict=True))
    for envelope in envelopes:
        relation = relation_by_id[envelope.target["id"]]
        observations = relation["member_pair_observations"]
        assert [
            (observation["member_a"], observation["member_b"])
            for observation in observations
        ] == sorted(
            (member_a, member_b)
            for member_a in expected_members_by_group[relation["group_a"]]
            for member_b in expected_members_by_group[relation["group_b"]]
        )
        for observation in observations:
            if observation["status"] == "computed":
                expected_source_refs = sorted(
                    set(geometry_refs_by_member[observation["member_a"]])
                    | set(geometry_refs_by_member[observation["member_b"]])
                )
                assert observation["witness"]["source_refs"] == expected_source_refs
        expected_relation_sources = tuple(
            sorted(
                {
                    source_ref
                    for observation in observations
                    for source_ref in observation["witness"]["source_refs"]
                }
            )
        )
        assert envelope.source_ids == expected_relation_sources
        assert envelope.provenance["analysis_frame"] == relation["analysis_frame"]
        assert envelope.provenance["unit"] == relation["unit"]
        assert envelope.provenance["tolerance"] == relation["tolerance"]
        dependency = envelope.provenance["shared_member_dependency"]
        assert dependency["status"] == relation["shared_member_dependency"]["status"]
        assert list(dependency["member_ids"]) == relation["shared_member_dependency"]["member_ids"]
        assert envelope.provenance["relation_status"] == relation["status"]
        assert envelope.raw_status is {
            "computed": FieldResultStatus.COMPUTED,
            "partial": FieldResultStatus.PARTIAL,
            "invalid": FieldResultStatus.INVALID,
            "not_available": FieldResultStatus.NOT_AVAILABLE,
            "diagnostic_only": FieldResultStatus.AMBIGUOUS,
        }.get(relation["status"], FieldResultStatus.NOT_EVALUATED)
        expected_channel_status = _result_status(
            [observation["status"] for observation in observations]
        )
        assert all(
            record.status is expected_channel_status
            for record in envelope.value["channels"]
        )

    relation_status_counts = Counter(
        relation["status"] for relation in description["group_relations"]
    )
    member_status_counts = Counter(
        observation["status"]
        for relation in description["group_relations"]
        for observation in relation["member_pair_observations"]
    )
    channel_status_counts = Counter(
        record.status.value
        for envelope in envelopes
        for record in envelope.value["channels"]
    )
    channel_counts = Counter(
        record.channel
        for envelope in envelopes
        for record in envelope.value["channels"]
    )
    member_pair_count = sum(
        len(relation["member_pair_observations"])
        for relation in description["group_relations"]
    )
    assert sum(relation_status_counts.values()) == len(expected_ids)
    assert sum(member_status_counts.values()) == member_pair_count
    assert sum(channel_status_counts.values()) == len(expected_ids) * 3
    assert channel_counts == Counter(
        {
            "boundary_gap": len(expected_ids),
            "contact": len(expected_ids),
            "positive_area_overlap": len(expected_ids),
        }
    )
    geometry_by_group = {
        item["target_id"]: item for item in description["group_geometry"]
    }
    object_by_id = {
        member_id: {"geometry_refs": list(geometry_refs)}
        for member_id, geometry_refs in geometry_refs_by_member.items()
    }
    symmetry_sample_count = 0
    for relation in description["group_relations"]:
        shared_members = sorted(
            set(expected_members_by_group[relation["group_a"]])
            & set(expected_members_by_group[relation["group_b"]])
        )
        assert relation["shared_member_dependency"]["member_ids"] == shared_members
        if (
            shared_members
            and len(shared_members)
            == len(expected_members_by_group[relation["group_a"]])
            == len(expected_members_by_group[relation["group_b"]])
        ):
            assert relation["status"] == "diagnostic_only"

        observation = next(
            (
                item
                for item in relation["member_pair_observations"]
                if item["status"] == "computed"
            ),
            None,
        )
        if observation is None:
            continue
        left = _member_record(
            geometry_by_group[relation["group_a"]], observation["member_a"]
        )
        right = _member_record(
            geometry_by_group[relation["group_b"]], observation["member_b"]
        )
        forward = _member_pair_observation(
            left, right, object_by_id, scene.context.geometry_tolerance
        )
        reverse = _member_pair_observation(
            right, left, object_by_id, scene.context.geometry_tolerance
        )
        for result in (forward, reverse):
            assert result["status"] == observation["status"]
            assert result["reason"] == observation["reason"]
            assert result["contact"] == observation["contact"]
            assert result["overlap"] == observation["overlap"]
            assert result["raw_boundary_gap"] == pytest.approx(
                observation["raw_boundary_gap"]
            )
            assert result["normalized_boundary_gap"] == pytest.approx(
                observation["normalized_boundary_gap"]
            )
            assert result["overlap_area"] == pytest.approx(observation["overlap_area"])
            assert (
                result["normalization"]["method"]
                == observation["normalization"]["method"]
            )
            assert result["normalization"]["denominator"] == pytest.approx(
                observation["normalization"]["denominator"]
            )
            assert (
                result["witness"]["source_refs"]
                == observation["witness"]["source_refs"]
            )
        symmetry_sample_count += 1

    assert symmetry_sample_count == sum(
        any(item["status"] == "computed" for item in relation["member_pair_observations"])
        for relation in description["group_relations"]
    )

    assert len(envelopes) == len(expected_ids) == 666
    assert all(
        record.observation["member_pairs"]
        for envelope in envelopes
        for record in envelope.value["channels"]
    )

    after = render_group_geometry_relation_field_ifc.fingerprint(source)
    assert after == before
    assert after["sha256"] == manifest["source"]["sha256_after"]
    report_directory = render_group_geometry_relation_field_ifc.write_report(
        description,
        envelopes,
        manifest,
        before,
        after,
        scene.context.analysis_plane,
    )
    view_manifest = json.loads(
        (report_directory / "view_manifest.json").read_text(encoding="utf-8")
    )
    assert len(view_manifest["pairs"]) == len(expected_ids)
    assert {item["pair_id"] for item in view_manifest["pairs"]} == expected_ids
    assert (report_directory / view_manifest["overview"]).is_file()
    for item in view_manifest["pairs"]:
        svg_path = report_directory / item["svg"]
        json_path = report_directory / item["json"]
        assert svg_path.is_file()
        assert json_path.is_file()
        pair_report = json.loads(json_path.read_text(encoding="utf-8"))
        assert pair_report["pair_id"] == item["pair_id"]
    print(
        f"group geometry relation IFC report: {report_directory}; "
        f"symmetry samples: {symmetry_sample_count}/{len(description['group_relations'])}"
    )
