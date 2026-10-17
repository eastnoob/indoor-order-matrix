"""Focused checks for the comparison-only 3D proxy eye-plane bridge."""

import hashlib
from pathlib import Path
import sys

import pytest
from shapely.geometry import box, Point, Polygon, shape, mapping

sys.path.insert(0, str(Path(__file__).parents[1]))
from features.discrete_space_field import load_discrete_space_field
from features.neutral_scene_views import _resolve_boundary_member_ids
from scripts.design.space_field import run_b3_proxy_eye_plane_comparison as COMP


@pytest.fixture(scope="module")
def evidence():
    """Read accepted evidence once without recomputing original sections."""
    baseline, sections, metadata, declaration = COMP.accepted_inputs()
    proxy_records = [COMP.proxy_section(group) for group in metadata["groups"]]
    return baseline, sections, metadata, proxy_records, declaration


def test_real_obj_transport_and_exact_section_qualification(evidence):
    """Accepted ordinary meshes must retain indexed topology through the exact plane path."""
    _, _, metadata, proxies, _ = evidence
    assert {p["status"] for p in proxies} <= COMP.QUALIFIED
    for group, proxy in zip(metadata["groups"], proxies):
        assert proxy["obj_transport"]["process"] is False
        assert proxy["obj_transport"]["is_watertight"] is True
        assert proxy["obj_transport"]["is_winding_consistent"] is True
        assert proxy["obj_transport"]["vertex_count"] == group["generated_mesh_checks"]["vertex_count"]
        assert proxy["obj_transport"]["triangle_count"] == group["generated_mesh_checks"]["triangle_count"]
        assert proxy["evidence_kind"] == "generated_3d_convex_mesh_section_comparison_only"
        assert proxy["analysis_enrollment"] == "deferred_excluded"


def test_override_retains_originals_and_failed_proxy_falls_back(evidence):
    """Only represented IDs with qualified proxies may lose uncertainty."""
    baseline, sections, _, proxies, declaration = evidence
    field, result = COMP.comparison_field(baseline, sections, proxies, declaration)
    assert result["records"][:358] == sections["records"]
    assert len(result["records"]) == 361
    assert len(field["scenario_overrides"]) == 7
    assert all(row["scenario_uncertainty_omitted"] for row in field["scenario_overrides"])
    failed = [{**proxy, "status": "unresolved_parity", "occupied_geometry": None} if index == 0 else proxy
              for index, proxy in enumerate(proxies)]
    fallback, _ = COMP.comparison_field(baseline, sections, failed, declaration)
    affected = set(proxies[0]["represented_source_ids"])
    assert {row["source_id"] for row in fallback["scenario_overrides"]
            if not row["scenario_uncertainty_omitted"]} == affected
    baseline_variant = baseline["variants"][2]
    fallback_variant = fallback["variants"][2]
    for before, after in zip(baseline_variant["samples"], fallback_variant["samples"]):
        if any(sid in before["unresolved_source_ids"] for sid in affected):
            assert any(sid in after["unresolved_source_ids"] for sid in affected)
    absent = [{**proxy, "status": "valid_empty_above_plane", "occupied_geometry": mapping(COMP.EYE.EMPTY)}
              if index == 0 else proxy for index, proxy in enumerate(proxies)]
    absence_field, _ = COMP.comparison_field(baseline, sections, absent, declaration)
    assert all(row["scenario_uncertainty_omitted"] for row in absence_field["scenario_overrides"])
    assert all(not affected.intersection(sample["unresolved_source_ids"])
               for variant in absence_field["variants"] for sample in variant["samples"])


def test_positive_unknown_boundary_and_outside_fixture():
    """A retained unknown cannot erase positive proxy interior or boundary ambiguity."""
    domain = Polygon([(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)])
    occupied = box(.25, .25, 1.5, .75)
    support = box(.25, .25, .75, .75)
    variant = COMP.EYE.sample_variant(domain, occupied, [("door", support)], [occupied.boundary], 1., (0., 0.))
    samples = {(s["x_m"], s["y_m"]): s for s in variant["samples"]}
    positive = samples[(.5, .5)]
    assert positive["unresolved_source_ids"] == ["door"]
    assert positive["occupancy_value"] is True and positive["status"] == "established_occupied"
    boundary = samples[(1.5, .5)]
    assert boundary["unresolved_source_ids"] == []
    assert boundary["section_boundary_ambiguity_mask"] and boundary["status"] == "unknown"
    assert samples[(1.5, 1.5)]["status"] == "outside_domain"


def test_unrelated_unknown_outside_and_positive_precedence(evidence):
    """Windows, domain mask, and positive-over-unknown semantics survive the scenario."""
    baseline, sections, _, proxies, declaration = evidence
    field, result = COMP.comparison_field(baseline, sections, proxies, declaration)
    original_by_id = {row["id"]: row for row in sections["records"]}
    scenario_by_id = {row["id"]: row for row in result["records"]}
    retained = {f"live-step-{step}" for step in (43654, 49645, 55636, 61627, 67618)}
    assert all(scenario_by_id[sid] == original_by_id[sid] for sid in retained)
    represented = {sid for p in proxies for sid in p["represented_source_ids"]}
    for before, after in zip(baseline["variants"], field["variants"]):
        for old, new in zip(before["samples"], after["samples"]):
            assert new["domain_mask"] == old["domain_mask"]
            assert new["distance_to_domain_boundary_m"] == old["distance_to_domain_boundary_m"]
            if old["status"] == "outside_domain":
                assert new["status"] == "outside_domain"
            assert (set(old["unresolved_source_ids"]) - represented
                    <= set(new["unresolved_source_ids"]))
            if new["qualified_occupied_subset_mask"]:
                assert new["occupancy_value"] is True
            if new["section_boundary_ambiguity_mask"] and not new["qualified_occupied_subset_mask"]:
                assert new["occupancy_value"] is None
            assert new["complete_physical_clearance_m"] is None
    assert field["complete_occupancy_geometry"] is None
    assert field["raw_qualified_occupied_area_m2"] >= baseline["raw_qualified_occupied_area_m2"]


def test_exact_boundary_membership_removes_only_declared_interior_support(evidence):
    """Two arbitrary exact members leave a nearby unrelated unknown intact."""
    baseline, sections, _, proxies, declaration = evidence
    ordinary, _ = COMP.comparison_field(baseline, sections, proxies, declaration)
    occupied = shape(ordinary["raw_qualified_occupied_geometry"])
    sample = next(row for row in ordinary["variants"][2]["samples"]
                  if row["status"] == "established_empty_under_qualification"
                  and Point(row["x_m"], row["y_m"]).distance(occupied) > .05)
    support = mapping(box(sample["x_m"] - .02, sample["y_m"] - .02,
                          sample["x_m"] + .02, sample["y_m"] + .02))
    extra_member = "boundary-component-with-arbitrary-id"
    unrelated = "live-step-49645"
    records = [({**row, "id": extra_member, "unknown_support_geometry": support,
                 "occupied_geometry": support}
                if row["id"] == "live-step-43654" else
                {**row, "unknown_support_geometry": support}
                if row["id"] in (declaration["boundary_member_source_ids"][0], unrelated)
                else row) for row in sections["records"]]
    modified = sections | {"records": records}
    selected = declaration | {"boundary_member_source_ids":
                              [*declaration["boundary_member_source_ids"], extra_member]}
    identities = ((row["id"], row.get("source_id")) for row in records)
    direct = _resolve_boundary_member_ids(selected["boundary_member_source_ids"], identities,
                                          {row["id"] for row in records})
    assert COMP.boundary_membership(baseline, modified, selected) == direct
    assert direct[0] == set(selected["boundary_member_source_ids"])
    supports, _ = COMP.scenario_geometry(records, set(), direct[0])
    assert {sid for sid, _ in supports}.isdisjoint(direct[0])
    assert unrelated in {sid for sid, _ in supports}
    field, result = COMP.comparison_field(baseline, modified, proxies, selected)
    assert result["records"][:358] == records
    assert shape(field["raw_qualified_occupied_geometry"]).intersection(shape(support)).area == 0
    after = next(row for row in field["variants"][2]["samples"]
                 if (row["cell_i"], row["cell_j"]) == (sample["cell_i"], sample["cell_j"]))
    assert after["unresolved_source_ids"] == [unrelated]
    assert after["status"] == "unknown" and after["occupancy_value"] is None


def test_boundary_membership_rejects_scope_and_source_drift(evidence):
    """A human declaration is valid only for its frozen scope and sections."""
    baseline, sections, _, _, declaration = evidence
    with pytest.raises(ValueError, match="scope_or_source_mismatch"):
        COMP.boundary_membership(baseline, sections, declaration | {
            "scope_binding": declaration["scope_binding"] | {"source_revision": "different"}})
    with pytest.raises(ValueError, match="scope_or_source_mismatch"):
        COMP.boundary_membership(baseline, sections, declaration | {
            "baseline_source_sections_ref": declaration["baseline_source_sections_ref"] | {"sha256": "different"}})
    with pytest.raises(ValueError, match="identity_unresolved"):
        COMP.boundary_membership(baseline, sections, declaration | {
            "boundary_member_source_ids": ["unmatched-source"]})


def test_ordinary_a_loader_reads_independent_comparison_package(evidence, tmp_path):
    """The unmodified A loader must accept package references and proxy provenance."""
    baseline, sections, _, proxies, declaration = evidence
    field, result = COMP.comparison_field(baseline, sections, proxies, declaration)
    COMP.PRIOR.write_json(tmp_path / "source_sections.json", result)
    field["source_sections"] = {"path": "comparison/source_sections.json",
                                "bytes": (tmp_path / "source_sections.json").stat().st_size,
                                "sha256": hashlib.sha256((tmp_path / "source_sections.json").read_bytes()).hexdigest()}
    COMP.PRIOR.write_json(tmp_path / "field_samples.json", field)
    field_ref = {"path": "comparison/field_samples.json", "bytes": (tmp_path / "field_samples.json").stat().st_size,
                 "sha256": hashlib.sha256((tmp_path / "field_samples.json").read_bytes()).hexdigest()}
    COMP.PRIOR.write_json(tmp_path / "artifact_manifest.json", {"schema": "b3-primary-eye-artifacts/v1",
                         "artifacts": [field_ref, field["source_sections"]]})
    loaded = load_discrete_space_field(tmp_path, spacing_m=.25, origin_offset_m=(0., 0.))
    assert loaded["variant"]["status_counts"] == field["variants"][2]["status_counts"]
    assert loaded["source_sections"]["records"][:358] == sections["records"]
    assert loaded["field"]["scenario_overrides"] == field["scenario_overrides"]
    assert loaded["field"]["domain_boundary_policy"] == field["domain_boundary_policy"]
    assert all(p["analysis_enrollment"] == "deferred_excluded" for p in loaded["source_sections"]["records"][358:])
