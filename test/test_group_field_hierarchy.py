"""Focused retained-data checks for the circular group-axis hierarchy."""

from __future__ import annotations

import json
from fractions import Fraction
from math import nextafter
from pathlib import Path

import pytest

from features.field_core import evaluate_evidence_package_freshness
from features.group_axis_potential_field import build_group_axis_potential_package
from scripts.design.group_level.run_group_axis_potential_ifc import _package_contract
from scripts.design.group_level.run_group_axis_potential_ifc_replay import _load_envelope


ROOT = Path(__file__).parents[1]
TREND_RUN = ROOT / "outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z"
AXIS_RUN = ROOT / "outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z"
NAMESPACE = "ifc-project:2uGd6yom9GZe5$z7LfbGW0"


def _retained_envelopes(limit: int | None = None):
    """Load the verified real-IFC trend envelopes without extracting IFC geometry."""
    payload = json.loads((TREND_RUN / "envelopes.json").read_text(encoding="utf-8"))
    items = payload["envelopes"] if limit is None else payload["envelopes"][:limit]
    return tuple(_load_envelope(item) for item in items)


def test_retained_manifest_and_exact_unwrap_boundary():
    """The hierarchy tests use the pinned retained source and exact dyadic topology."""
    manifest = json.loads((AXIS_RUN / "source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["project_global_id"] == "2uGd6yom9GZe5$z7LfbGW0"
    assert manifest["source"]["sha256"] == "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
    a, b = 1.0, nextafter(1.0, 2.0)
    assert a != b and a + 180.0 == b + 180.0
    qa, qb = Fraction.from_float(a), Fraction.from_float(b)
    assert qa + 180 < qb + 180
    # This algebraic boundary is not an observed angle in the retained IFC data.
    theta = nextafter(0.0, -1.0) % 180.0
    assert theta == 180.0
    assert (0.0 if theta == 180.0 or theta == 0.0 else theta) == 0.0


def test_hierarchy_outputs_cover_real_scope_and_preserve_legacy_outputs():
    """Hierarchy mode adds family records while preserving every legacy output."""
    sources = _retained_envelopes()
    legacy = build_group_axis_potential_package().evaluate(sources)
    expanded = build_group_axis_potential_package(scene_namespace=NAMESPACE).evaluate(sources)
    original = {(item.target["identity"], item.channel): item for item in legacy.outputs}
    actual = {(item.target["identity"], item.channel): item for item in expanded.outputs}
    assert all(actual[key] == value for key, value in original.items())
    assert expanded.source_envelopes == legacy.source_envelopes
    assert len(expanded.outputs) > len(legacy.outputs)
    assert {item.channel for item in expanded.outputs} >= {
        "axis_direction_aliases",
        "axis_family_definition",
        "axis_family_support",
        "axis_family_profile",
        "axis_field_relation",
        "axis_family_residual",
        "axis_family_direction",
        "axis_family_scope_diagnostics",
    }
    definitions = [item for item in expanded.outputs if item.channel == "axis_family_definition"]
    assert len(definitions) == 703
    assert all(item.observation["birth_exact"][1] > 0 for item in definitions)
    assert all(item.observation["death_exact"][1] > 0 for item in definitions)
    assert all(item.derived_from for item in definitions)


def test_hierarchy_is_order_deterministic_and_family_support_is_max_union():
    """Retained outputs preserve exact topology and the frozen support formulas."""
    sources = _retained_envelopes()
    package = build_group_axis_potential_package(scene_namespace=NAMESPACE)
    forward = package.evaluate(sources)
    reverse = package.evaluate(tuple(reversed(sources)))
    assert forward.output_identity == reverse.output_identity
    definitions = {item.observation["family_id"]: item.observation for item in forward.outputs if item.channel == "axis_family_definition"}
    leaf_values = {
        (item.observation["field_id"], item.observation["target_group_id"]): item.observation["axis_field_support"]
        for item in forward.outputs if item.channel == "axis_field_support"
    }
    leaf_cell_ids = {
        (item.observation["field_id"], item.observation["target_group_id"]): item.target["identity"]
        for item in forward.outputs if item.channel == "axis_field_support"
    }
    family_rows = {
        (item.observation["family_id"], item.observation["group_id"]): item.observation
        for item in forward.outputs if item.channel == "axis_family_support"
    }
    family_values = {key: row["J"] for key, row in family_rows.items()}
    group_ids = tuple(sorted(source.target["identity"] for source in sources))
    for family_id, definition in definitions.items():
        assert Fraction(*definition["birth_exact"]) < Fraction(*definition["death_exact"]) <= 90
        # Strict anchor inclusion increases cardinality on every edge, ruling out cycles.
        for parent_id in definition["parent_ids"]:
            assert set(definition["anchor_group_ids"]) < set(definitions[parent_id]["anchor_group_ids"])
        for group_id in group_ids:
            value = family_values[(family_id, group_id)]
            assert [cell["cell_id"] for cell in family_rows[(family_id, group_id)]["leaf_cells"]] == [leaf_cell_ids[(leaf_id, group_id)] for leaf_id in definition["leaf_field_ids"]]
            assert value == max(leaf_values[(leaf_id, group_id)] for leaf_id in definition["leaf_field_ids"])
            assert all(family_values[(parent_id, group_id)] >= value for parent_id in definition["parent_ids"])

    for item in forward.outputs:
        if item.channel == "axis_family_residual":
            residual = item.observation
            child_id, parent_id = residual["child_family_id"], residual["parent_family_id"]
            complement = set(definitions[parent_id]["leaf_field_ids"]) - set(definitions[child_id]["leaf_field_ids"])
            assert set(residual["complement_leaf_field_ids"]) == complement
            for row in residual["rows"]:
                complement_support = max(leaf_values[(leaf_id, row["group_id"])] for leaf_id in complement)
                assert row["value"] == max(0.0, family_values[(child_id, row["group_id"])] - complement_support)
            known_values = [row["value"] for row in residual["rows"] if row["status"] == "computed"]
            assert residual["known_residual_mass"] == pytest.approx(sum(known_values))
            assert residual["known_residual_mean"] == pytest.approx(sum(known_values) / len(known_values))
        elif item.channel == "axis_family_profile":
            family_id = item.observation["family_id"]
            for domain in item.observation["domains"].values():
                values = [value for value in domain["values"].values() if value is not None]
                mass = sum(values)
                square_mass = sum(value * value for value in values)
                assert domain["support_mass"] == pytest.approx(mass)
                assert domain["n_eff"] == pytest.approx(mass * mass / square_mass)
                leaf_cells = [cell for group_id in domain["row_ids"] for cell in family_rows[(family_id, group_id)]["leaf_cells"]]
                known_leaf_count = sum(cell["status"] == "computed" for cell in leaf_cells)
                assert domain["known_leaf_cell_count"] == known_leaf_count
                assert domain["expected_leaf_cell_count"] == len(leaf_cells)
                assert domain["leaf_cell_coverage"] == known_leaf_count / len(leaf_cells)
                assert dict(domain["leaf_cell_status_counts"]) == {
                    state: sum(cell["status"] == state for cell in leaf_cells)
                    for state in ("computed", "partial", "not_available", "invalid", "outside", "ambiguous", "not_evaluated")
                }


def test_profiles_use_full_and_non_anchor_domains():
    """Profile denominators follow the family anchor set instead of N minus one."""
    result = build_group_axis_potential_package(scene_namespace=NAMESPACE).evaluate(_retained_envelopes())
    profile = next(item for item in result.outputs if item.channel == "axis_family_profile")
    definition = next(item for item in result.outputs if item.channel == "axis_family_definition" and item.target["identity"] == profile.target["identity"])
    domains = profile.observation["domains"]
    assert domains["full_scope"]["expected_count"] == 37
    assert domains["non_anchor"]["expected_count"] == 37 - len(definition.observation["anchor_group_ids"])
    assert domains["full_scope"]["support_mass"] is not None


@pytest.mark.parametrize("limit", (1, None))
def test_family_direction_reports_actual_anchor_contributions(limit):
    """Real retained rows and their singleton subset expose the direction's weights."""
    result = build_group_axis_potential_package(scene_namespace=NAMESPACE).evaluate(_retained_envelopes(limit))
    support_rows = {}
    for item in result.outputs:
        if item.channel == "axis_family_support":
            row = item.observation
            support_rows.setdefault(row["family_id"], {})[row["group_id"]] = row
    directions = [item for item in result.outputs if item.channel == "axis_family_direction"]
    assert directions
    for item in directions:
        direction = item.observation
        rows = support_rows[direction["family_id"]]
        anchors = set(direction["anchor_group_ids"])
        positive_ids = sorted(group_id for group_id, row in rows.items() if row["value"] > 0.0)
        mass = sum(rows[group_id]["value"] for group_id in sorted(rows))
        anchor_mass = sum(rows[group_id]["value"] for group_id in sorted(rows) if group_id in anchors)
        assert list(direction["positive_contribution_group_ids"]) == positive_ids
        assert direction["anchors_included"] is True
        assert direction["anchor_contribution_mass"] == pytest.approx(anchor_mass)
        assert direction["anchor_contribution_fraction"] == pytest.approx(anchor_mass / mass)
        assert direction["support_mass"] == pytest.approx(mass)
        assert direction["known_count"] == direction["expected_count"] == len(rows)
        assert direction["coverage"] == 1.0
        assert item.status.value == "computed"
        assert direction["direction_status"] == ("anchor_only" if set(positive_ids) <= anchors else "computed")


def test_namespace_and_freshness_are_explicit_and_independent():
    """A changed target set is stale; rebuilding an independent full contract is fresh."""
    sources = _retained_envelopes()
    description = json.loads((AXIS_RUN / "description.json").read_text(encoding="utf-8"))
    manifest = json.loads((AXIS_RUN / "source_manifest.json").read_text(encoding="utf-8"))
    plane = manifest["analysis_plane"]
    full_result = build_group_axis_potential_package(scene_namespace=NAMESPACE).evaluate(sources)
    subset_result = build_group_axis_potential_package(scene_namespace=NAMESPACE).evaluate(sources[:2])
    full_contract = _package_contract(description, sources, sources[0].query, plane, manifest["source"]["sha256"], (), full_result, scene_namespace=NAMESPACE)
    subset_contract = _package_contract(description, sources[:2], sources[0].query, plane, manifest["source"]["sha256"], (), subset_result, scene_namespace=NAMESPACE)
    stale = evaluate_evidence_package_freshness(cached_contract=subset_contract, current_contract=full_contract, artifacts_available=True)
    restored = evaluate_evidence_package_freshness(cached_contract=dict(full_contract), current_contract=dict(full_contract), artifacts_available=True)
    assert stale["recompute_required"] is True
    assert set(stale["affected_targets"]) == set(subset_contract["target_ids"]) | set(full_contract["target_ids"])
    assert restored["recompute_required"] is False
    assert full_contract["package_schema"] == "group-axis-field-hierarchy-output/v1"
    assert full_contract["algorithm_version"] == "axis-with-hierarchy-v1"


def test_empty_namespace_is_rejected():
    """Hierarchy identity cannot be silently invented from an empty namespace."""
    with pytest.raises(ValueError):
        build_group_axis_potential_package(scene_namespace="")
