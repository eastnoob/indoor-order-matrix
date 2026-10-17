"""Focused occupancy-only handoff checks over accepted serialized B3 evidence."""

import hashlib

import pytest
from shapely.geometry import shape

from ..features.discrete_space_field import load_discrete_space_field
from ..scripts.design.space_field import run_b3_occupancy_only_handoff as HANDOFF


@pytest.fixture(scope="module")
def evidence():
    """Read immutable accepted sections once and build the proposed handoff in memory."""
    originals, metadata, declaration, comparison, sections = HANDOFF.accepted_inputs()
    field, records = HANDOFF.occupancy_only_field(
        originals, metadata, declaration, comparison, sections
    )
    baseline = HANDOFF.PRIOR.read_json(HANDOFF.COMP.BASE / "field_samples.json")
    return baseline, originals, metadata, declaration, comparison, sections, field, records


def test_proxy_sections_are_active_occupancy_only_without_original_double_count(evidence):
    """All three qualified proxies replace seven originals once and anchor no furniture."""
    _, originals, _, _, comparison, sections, field, records = evidence
    policy = field["occupancy_only_policy"]
    assert records["records"][:358] == originals["records"] == sections["records"][:358]
    assert len(records["records"]) == 361
    assert len(policy["active_proxy_ids"]) == 3
    assert len(policy["represented_original_source_ids"]) == 7
    assert len(set(policy["represented_original_source_ids"])) == 7
    assert all(row["occupied_geometry"] is None for row in originals["records"]
               if row["id"] in policy["represented_original_source_ids"])
    assert all(row["physical_occupancy_participation"] == "active_substitute"
               and row["furniture_analysis_participation"] == "excluded"
               and row["status"] == "qualified_closed_section"
               for row in records["records"][358:])
    assert all("analysis_enrollment" not in row for row in records["records"][358:])
    assert field["variants"] == comparison["variants"]
    assert field["domain_boundary_policy"] == comparison["domain_boundary_policy"]
    assert all(row["scenario_uncertainty_omitted"] for row in field["scenario_overrides"])


@pytest.mark.parametrize("change", ({"status": "unresolved_open_or_nonmanifold"},
                                          {"occupied_geometry": None}))
def test_failed_or_missing_proxy_refuses_occupancy_handoff(evidence, change):
    """A missing substitute cannot turn unresolved original support into free space."""
    _, originals, metadata, declaration, comparison, sections, _, _ = evidence
    records = list(sections["records"])
    records[358] = records[358] | change
    with pytest.raises(ValueError, match="proxy_unqualified"):
        HANDOFF.occupancy_only_field(originals, metadata, declaration, comparison,
                                     sections | {"records": records})


def test_ordinary_loader_exposes_proxy_obstacles_to_free_space_consumer(evidence, tmp_path):
    """Validated field geometry and samples reduce free space without furniture nodes."""
    baseline, originals, _, _, _, _, field, records = evidence
    HANDOFF.PRIOR.write_json(tmp_path / "source_sections.json", records)
    section_path = tmp_path / "source_sections.json"
    section_ref = {"path": "occupancy/source_sections.json", "bytes": section_path.stat().st_size,
                   "sha256": hashlib.sha256(section_path.read_bytes()).hexdigest()}
    packaged = field | {"source_sections": section_ref}
    HANDOFF.PRIOR.write_json(tmp_path / "field_samples.json", packaged)
    field_path = tmp_path / "field_samples.json"
    field_ref = {"path": "occupancy/field_samples.json", "bytes": field_path.stat().st_size,
                 "sha256": hashlib.sha256(field_path.read_bytes()).hexdigest()}
    HANDOFF.PRIOR.write_json(tmp_path / "artifact_manifest.json", {
        "schema": "b3-primary-eye-artifacts/v1", "artifacts": [field_ref, section_ref]})

    loaded = load_discrete_space_field(tmp_path, spacing_m=.25, origin_offset_m=(0., 0.))
    domain = shape(loaded["field"]["domain_geometry"])
    occupied = shape(loaded["field"]["clipped_qualified_occupied_geometry"])
    unknown = shape(loaded["field"]["clipped_unknown_support_geometry"])
    baseline_occupied = shape(baseline["clipped_qualified_occupied_geometry"])
    assert domain.difference(occupied).area < domain.difference(baseline_occupied).area
    assert domain.difference(occupied).difference(unknown).area > 0
    assert loaded["variant"]["status_counts"] == {
        "outside_domain": 565, "established_empty_under_qualification": 3054,
        "established_occupied": 269}
    assert all(sample["known_free_under_qualification"] is False
               for sample in loaded["variant"]["samples"]
               if sample["occupancy_value"] is True)
    assert loaded["source_sections"]["records"][:358] == originals["records"]
    assert all(not set(sample["unresolved_source_ids"]) &
               set(field["domain_boundary_policy"]["resolved_record_ids"])
               for sample in loaded["variant"]["samples"])
    assert loaded["field"]["complete_occupancy_geometry"] is None
