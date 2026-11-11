"""Acceptance checks for the retained real-IFC group-distance decay experiment."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import csv
import hashlib
import math
import json
from pathlib import Path
import re
import sys

import pytest
from shapely import constrained_delaunay_triangles
from shapely.affinity import rotate, scale, translate

from features.group_distance_evidence_package import SOURCE_CHANNEL
from features.field_core import build_evidence_package_contract
from scripts.design.group_level import replay_evidence_package_readback as readback
from scripts.design.group_level import run_group_distance_decay_ifc as decay
from scripts.design.group_level.run_group_distance_decay_ifc import (
    build_comparison_rows, build_decay_rows, geometry_scaled_response, load_experiment_inputs,
    reciprocal_response, RECIPROCAL_FORMULA, RECIPROCAL_FORMULA_VERSION,
    _union_rms_radius, validate_euclidean_observation, _json_safe, EXPECTED_HASHES,
)


BUNDLE = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge/"
    "outputs/design/group_distance_ifc/run_v4_eight_neighbor/input_bundle.json"
)
PACKAGE = Path(
    "D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge_proxy/"
    "outputs/design/group_distance_ifc/run_global_full_current_20261106_merged/"
    "distance_evidence_package/group_distance_package_output.json"
)


@pytest.fixture(scope="module")
def experiment_inputs():
    """Authenticate the retained IFC/package inputs once for this module."""
    return load_experiment_inputs(bundle_path=BUNDLE, package_path=PACKAGE)


@pytest.fixture(scope="module")
def decay_rows(experiment_inputs):
    """Build the complete retained Euclidean response rows once."""
    return build_decay_rows(experiment_inputs)


@pytest.fixture(scope="module")
def comparison_rows(experiment_inputs):
    """Reuse the authenticated retained context for the opt-in two-curve rows."""
    return build_comparison_rows(experiment_inputs)


@pytest.fixture(scope="module")
def sqrt_comparison_rows(experiment_inputs):
    """Reuse the authenticated retained context for the opt-in third curve."""
    return build_comparison_rows(experiment_inputs, compare_sqrt_reciprocal=True)


@pytest.fixture(scope="module")
def power_06_comparison_rows(experiment_inputs):
    """Reuse the authenticated retained context for the standalone fixed-0.6 mode."""
    return build_comparison_rows(experiment_inputs, compare_power_06=True)


def _projection(group, geometry):
    """Apply a mathematical transform to a retained group's polygon components."""
    polygons = tuple(geometry.geoms) if geometry.geom_type == "MultiPolygon" else (geometry,)
    return replace(group, components=tuple({
        "exterior": tuple(polygon.exterior.coords),
        "holes": tuple(tuple(ring.coords) for ring in polygon.interiors),
    } for polygon in polygons))


def test_retained_ifc_decay_covers_all_euclidean_pairs_and_preserves_lineage(experiment_inputs, decay_rows) -> None:
    """Every nonself unordered pair retains finite values and a full channel address."""
    group_ids = {group.group_id for group in experiment_inputs.bundle.groups}
    assert len(group_ids) == 37
    assert len(decay_rows) == len({row["pair_id"] for row in decay_rows}) == 666
    assert {tuple(sorted((row["group_a_id"], row["group_b_id"]))) for row in decay_rows} == set(
        combinations(sorted(group_ids), 2)
    )
    for row in decay_rows:
        assert row["channel"] == "euclidean_distance"
        assert row["status"] == row["raw_status"] == "computed"
        assert math.isfinite(row["distance_m"]) and row["distance_m"] >= 0
        assert math.isfinite(row["ell_m"]) and row["ell_m"] > 0
        assert math.isfinite(row["q"]) and row["q"] >= 0
        assert 0 <= row["w"] <= 1
        assert row["source_ids"] and len(row["centroid_refs"]) == 2
        reference = row["lineage"]["distance_channel_ref"]
        assert reference["package_id"] == "group-walk-distance"
        assert reference["output_identity"] and reference["target_identity"] == row["pair_id"]
        assert reference["channel"] == "euclidean_distance"
        assert row["formula_version"] == "group-union-rms-rss-exp/1"
    assert experiment_inputs.source_binding["raw_step_entity_comparison"]["status"] == "verified"


def test_union_moments_ignore_duplicate_retained_component(experiment_inputs) -> None:
    """Duplicating one real component cannot double-count area or shift RMS radius."""
    group = next(group for group in experiment_inputs.bundle.groups if len(group.components) > 1)
    result = _union_rms_radius(replace(group, components=(*group.components, group.components[0])))
    baseline = experiment_inputs.scales[group.group_id]
    assert result["status"] == "computed"
    assert result["union_area_m2"] == pytest.approx(baseline["union_area_m2"], rel=1e-11)
    assert result["centroid"] == pytest.approx(baseline["centroid"], abs=1e-11)
    assert result["rho2_m2"] == pytest.approx(baseline["rho2_m2"], rel=1e-10)


def test_real_union_holes_match_independent_triangle_integrals(experiment_inputs) -> None:
    """Exact triangle moments independently confirm a real hole-bearing union's RMS radius."""
    group_id, geometry = next((identity, geometry) for identity, geometry in experiment_inputs.geometries.items()
                              if any(part.interiors for part in (tuple(geometry.geoms)
                                     if geometry.geom_type == "MultiPolygon" else (geometry,))))
    triangles = tuple(constrained_delaunay_triangles(geometry).geoms)
    assert triangles and math.fsum(triangle.area for triangle in triangles) == pytest.approx(geometry.area, rel=1e-10)
    centroid = experiment_inputs.scales[group_id]["centroid"]
    integrals = []
    for triangle in triangles:
        center = tuple(triangle.centroid.coords[0])
        vertices = tuple(triangle.exterior.coords)[:-1]
        assert len(vertices) == 3
        # Uniform triangle variance uses its three squared vertex offsets divided by twelve.
        variance = math.fsum(math.dist(vertex, center) ** 2 for vertex in vertices) / 12
        integrals.append(triangle.area * (variance + math.dist(center, centroid) ** 2))
    assert experiment_inputs.scales[group_id]["rho2_m2"] == pytest.approx(
        math.fsum(integrals) / geometry.area, rel=1e-10, abs=1e-11
    )


@pytest.mark.parametrize("factor,angle,offset", ((1000.0, 0.0, (0.0, 0.0)),
                                                     (2.5, 0.0, (0.0, 0.0)),
                                                     (1.0, 37.0, (-17.0, 9.0))))
def test_retained_pair_survives_units_scaling_and_rigid_motion(experiment_inputs, decay_rows, factor, angle, offset) -> None:
    """Recomputed union moments and distance preserve response under common transforms."""
    # Use the two best-separated retained polygon boundaries so rigid transforms do not
    # collapse near-coincident tessellation vertices at binary64 coordinate precision.
    group_ids = set(sorted(experiment_inputs.geometries,
                           key=lambda identity: experiment_inputs.geometries[identity].minimum_clearance,
                           reverse=True)[:2])
    row = next(row for row in decay_rows if {row["group_a_id"], row["group_b_id"]} == group_ids)
    by_id = {group.group_id: group for group in experiment_inputs.bundle.groups}
    transformed = []
    for identity in (row["group_a_id"], row["group_b_id"]):
        geometry = scale(experiment_inputs.geometries[identity], xfact=factor, yfact=factor, origin=(0, 0))
        geometry = rotate(geometry, angle, origin=(0, 0))
        geometry = translate(geometry, xoff=offset[0], yoff=offset[1])
        moments = _union_rms_radius(_projection(by_id[identity], geometry))
        assert moments["status"] == "computed"
        assert moments["rho2_m2"] == pytest.approx(experiment_inputs.scales[identity]["rho2_m2"] * factor ** 2, rel=1e-9)
        transformed.append(moments)
    distance = math.dist(*(moments["centroid"] for moments in transformed))
    ell, q, weight = geometry_scaled_response(distance, *(moments["rho2_m2"] for moments in transformed))
    assert ell == pytest.approx(row["ell_m"] * factor, rel=1e-9)
    assert q == pytest.approx(row["q"], rel=1e-9)
    assert weight == pytest.approx(row["w"], rel=1e-9, abs=0)
    assert reciprocal_response(q) == pytest.approx(reciprocal_response(row["q"]), rel=1e-9)
    assert decay.sqrt_reciprocal_response(q) == pytest.approx(decay.sqrt_reciprocal_response(row["q"]), rel=1e-9)


def test_equal_dimensionless_distance_has_equal_response(decay_rows) -> None:
    '''Distinct retained pair scales yield identical response at the same q.'''
    first = min(decay_rows, key=lambda row: row['ell_m'])
    second = max(decay_rows, key=lambda row: row['ell_m'])
    assert not math.isclose(first['ell_m'], second['ell_m'])
    responses = []
    for row in (first, second):
        # Match q across actual group scales rather than normalizing by other scene pairs.
        distance = first['q'] * math.sqrt(row['rho2_a_m2'] + row['rho2_b_m2'])
        responses.append(geometry_scaled_response(distance, row['rho2_a_m2'], row['rho2_b_m2']))
    assert responses[0][1:] == pytest.approx(responses[1][1:], rel=1e-12)
    assert responses[0][2] == pytest.approx(first['w'], rel=1e-12)


def test_response_decreases_with_distance_at_fixed_retained_scale(decay_rows) -> None:
    '''A real pair's fixed geometry scale gives unit contact and strict decay.'''
    row = next(row for row in decay_rows if row['distance_m'] > 0)
    responses = [geometry_scaled_response(factor * row['distance_m'], row['rho2_a_m2'], row['rho2_b_m2'])
                 for factor in (0.0, 0.5, 1.0, 2.0)]
    assert responses[0][1:] == (0.0, 1.0)
    assert all(earlier[2] > later[2] for earlier, later in zip(responses, responses[1:]))
    assert all(response[0] == pytest.approx(row['ell_m']) for response in responses)


def test_unrelated_real_group_transforms_do_not_change_selected_pair(experiment_inputs, decay_rows) -> None:
    '''Changing only unrelated retained unions cannot alter a selected pair response.'''
    row = decay_rows[0]
    pair_groups = (row['group_a_id'], row['group_b_id'])
    baseline = geometry_scaled_response(
        row['distance_m'], *(experiment_inputs.scales[identity]['rho2_m2'] for identity in pair_groups)
    )
    unrelated = max((group for group in experiment_inputs.bundle.groups if group.group_id not in pair_groups),
                    key=lambda group: experiment_inputs.geometries[group.group_id].minimum_clearance)
    geometry = scale(experiment_inputs.geometries[unrelated.group_id], xfact=11.0, yfact=11.0, origin=(0, 0))
    geometry = translate(geometry, xoff=-13.0, yoff=42.0)
    scales = dict(experiment_inputs.scales)
    scales[unrelated.group_id] = _union_rms_radius(_projection(unrelated, geometry))
    assert scales[unrelated.group_id]['status'] == 'computed'
    assert scales[unrelated.group_id]['rho2_m2'] == pytest.approx(
        experiment_inputs.scales[unrelated.group_id]['rho2_m2'] * 121.0, rel=1e-9
    )
    # Evaluate the production formula directly; transformed source refs are never
    # forged to pass the separate package-authentication or all-pairs replay boundary.
    changed = geometry_scaled_response(
        row['distance_m'], *(scales[identity]['rho2_m2'] for identity in pair_groups)
    )
    assert changed == baseline
    assert reciprocal_response(changed[1]) == reciprocal_response(baseline[1])
    assert decay.sqrt_reciprocal_response(changed[1]) == decay.sqrt_reciprocal_response(baseline[1])


def test_post_auth_path_readings_do_not_enter_euclidean_decay(experiment_inputs, decay_rows) -> None:
    '''Post-auth route-channel changes cannot influence Euclidean response rows.'''
    sources = []
    for source in experiment_inputs.source_envelopes:
        records = []
        for record in source.value['channels']:
            if record.channel == SOURCE_CHANNEL:
                observation = {**record.observation,
                               'centroid_free_space_hybrid': {'status': 'invalid', 'value': None},
                               'baseline_path_reading': {'status': 'invalid', 'value': None}}
                record = replace(record, observation=observation)
            records.append(record)
        sources.append(replace(source, value={**source.value, 'channels': tuple(records)}))
    # This tests the experiment layer; freshness authentication remains a separate boundary.
    changed = replace(experiment_inputs, source_envelopes=tuple(sources))
    assert build_decay_rows(changed) == decay_rows


@pytest.mark.parametrize('changes', (
    {'raw_status': 'invalid'}, {'raw_status': 'not_available'},
    {'status': 'invalid'}, {'units': 'mm'},
    {'value': -1.0}, {'value': math.inf}, {'value': math.nan},
    {'value': True}, {'value': None},
))
def test_invalid_euclidean_readings_are_rejected(experiment_inputs, changes) -> None:
    '''Invalid status, units, and numeric values cannot be evaluated as distance.'''
    observation = {'status': 'computed', **experiment_inputs.outputs[0].observation, **changes}
    with pytest.raises(ValueError):
        validate_euclidean_observation(observation)


@pytest.mark.parametrize('distance', (-1.0, math.inf, math.nan))
def test_response_rejects_invalid_distance(decay_rows, distance) -> None:
    '''The response kernel rejects invalid distances with actual retained scales.'''
    row = decay_rows[0]
    with pytest.raises(ValueError):
        geometry_scaled_response(distance, row['rho2_a_m2'], row['rho2_b_m2'])


@pytest.mark.parametrize('radius_index', (0, 1))
@pytest.mark.parametrize('invalid_radius', (0.0, -1.0, math.inf, math.nan))
def test_response_requires_each_positive_finite_group_radius(decay_rows, radius_index, invalid_radius) -> None:
    '''Each retained group must contribute its own finite positive squared radius.'''
    row = decay_rows[0]
    radii = [row['rho2_a_m2'], row['rho2_b_m2']]
    radii[radius_index] = invalid_radius
    with pytest.raises(ValueError):
        geometry_scaled_response(row['distance_m'], *radii)


@pytest.mark.parametrize('mode', ('missing_sources', 'missing_contract', 'stale_query', 'mismatched_query'))
def test_real_package_refuses_unverified_context(experiment_inputs, mode) -> None:
    """Pinned real package bytes cannot bypass missing, stale or mismatched current context."""
    cached = json.loads((PACKAGE.parent / 'package_contract.json').read_text(encoding='utf-8'))
    current, sources = cached, experiment_inputs.source_envelopes
    if mode == 'missing_sources':
        sources = None
    elif mode == 'missing_contract':
        current = None
    elif mode == 'stale_query':
        dependencies = [{**item, 'fingerprint': '0' * 64} if item['name'] == 'query' else item
                        for item in cached['dependencies']]
        current = build_evidence_package_contract(**{
            key: dependencies if key == 'dependencies' else cached[key]
            for key in ('package_id', 'package_schema', 'producer', 'target_ids', 'dependencies',
                        'algorithm_version', 'schema_version', 'artifacts')
        })
        assert current['package_identity'] != cached['package_identity']
    else:
        source = sources[0]
        sources = (replace(source, query=replace(source.query, revision='changed-query')), *sources[1:])
    arguments = dict(expected_sha256=EXPECTED_HASHES['package'], cached_contract=cached,
                     current_contract=current, current_source_envelopes=sources,
                     selections=tuple((output.target['identity'], 'euclidean_distance')
                                      for output in experiment_inputs.outputs[:2]),
                     dependency_graph={readback.PACKAGE_ID: ('group-walk-distance',), 'group-walk-distance': ()})
    if mode == 'mismatched_query':
        with pytest.raises(ValueError, match='source context'):
            readback.consume_saved_evidence_package(PACKAGE, **arguments)
    else:
        result = readback.consume_saved_evidence_package(PACKAGE, **arguments)
        assert len(result.outputs) == 2
        assert all(output.observation is None and output.status.value == 'not_available' for output in result.outputs)
        reason = {'missing_sources': 'current_source_context_missing', 'missing_contract': 'package_invalid',
                  'stale_query': 'query_changed'}[mode]
        assert all(reason in output.explanation for output in result.outputs)


@pytest.mark.parametrize('changes', ({'value': None},
                                     {'raw_status': 'not_available', 'value': None}))
def test_invalid_raw_reading_preserves_serializable_null_response(experiment_inputs, changes) -> None:
    """Malformed or unavailable raw values retain a reason and never become zero support."""
    first, *remaining = experiment_inputs.outputs
    changed = replace(first, observation={**first.observation, **changes})
    rows = build_decay_rows(replace(experiment_inputs, outputs=(changed, *remaining)))
    row = next(row for row in rows if row['pair_id'] == first.target['identity'])
    assert row['status'] != 'computed' and row['reason']
    assert row['distance_m'] is None
    assert row['ell_m'] is row['q'] is row['w'] is None
    assert row['raw_distance_reading']['status'] == changes.get('raw_status', 'computed')
    json.dumps(_json_safe(rows), allow_nan=False)
    compared = next(row for row in build_comparison_rows(replace(
        experiment_inputs, outputs=(changed, *remaining))) if row['pair_id'] == first.target['identity'])
    assert compared['w_reciprocal'] is None
    assert {key: value for key, value in compared.items()
            if key not in {'w_reciprocal', 'reciprocal_formula_version'}} == row
    json.dumps(_json_safe(compared), allow_nan=False)
    third = next(row for row in build_comparison_rows(replace(
        experiment_inputs, outputs=(changed, *remaining)), compare_sqrt_reciprocal=True)
                 if row['pair_id'] == first.target['identity'])
    assert third['w_sqrt_reciprocal'] is None
    assert {key: third[key] for key in compared} == compared
    json.dumps(_json_safe(third), allow_nan=False)


@pytest.mark.parametrize('value', (math.nan, math.inf))
def test_typed_boundary_refuses_nonfinite_raw_distance(experiment_inputs, value) -> None:
    """Native immutable channel records reject nonfinite readings before experiment evaluation."""
    first = experiment_inputs.outputs[0]
    with pytest.raises(ValueError, match='non-finite'):
        replace(first, observation={**first.observation, 'value': value})


@pytest.mark.parametrize('mismatch', ('channel', 'pair', 'centroid', 'plane'))
def test_decay_rejects_wrong_euclidean_geometry_binding(experiment_inputs, mismatch) -> None:
    """The experiment refuses channels and geometry context that do not match its retained unions."""
    first, *remaining = experiment_inputs.outputs
    if mismatch == 'channel':
        changed = replace(first, channel='path_distance')
    elif mismatch == 'pair':
        changed = replace(first, observation={**first.observation, 'pair_id': 'wrong-pair'})
    elif mismatch == 'centroid':
        distance = first.observation['distance']
        changed = replace(first, observation={**first.observation, 'distance': {
            **distance, 'centroid_source_refs': tuple(reversed(distance['centroid_source_refs']))}})
    else:
        changed = replace(first, provenance={**first.provenance, 'analysis_plane': {'identity': 'wrong-plane'}})
    with pytest.raises(ValueError):
        build_decay_rows(replace(experiment_inputs, outputs=(changed, *remaining)))


def test_reciprocal_comparison_preserves_all_pinned_v3_rows(decay_rows, comparison_rows) -> None:
    """The comparison adds only its named response/version to all unchanged v3 evidence."""
    baseline = Path(__file__).resolve().parents[1] / (
        'outputs/design/group_distance_decay_ifc/run_20261111_rms_rss_v3/decay_rows.json'
    )
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == (
        '76b7ac1883f7c19f7d6353e9b71eb406f14152927ca1fb2261ca2acb49b71854'
    )
    saved = json.loads(baseline.read_text(encoding='utf-8'))
    assert saved['schema'] == 'group-distance-decay-rows/1'
    assert _json_safe(decay_rows) == saved['rows']
    assert len(comparison_rows) == len(decay_rows) == 666
    for original, compared in zip(decay_rows, comparison_rows):
        assert set(compared) - set(original) == {'w_reciprocal', 'reciprocal_formula_version'}
        assert {key: compared[key] for key in original} == original
        assert compared['reciprocal_formula_version'] == RECIPROCAL_FORMULA_VERSION
        assert compared['w_reciprocal'] == 1.0 / (1.0 + original['q'])
        assert 0 < compared['w_reciprocal'] <= 1


def test_reciprocal_response_domain_and_retained_q_order(comparison_rows) -> None:
    """Finite nonnegative q keeps a positive reciprocal tail and the retained q ordering."""
    assert reciprocal_response(0.0) == 1.0
    largest_q = sys.float_info.max
    assert 0 < reciprocal_response(largest_q) == 1.0 / (1.0 + largest_q) < 1
    ordered = sorted({row['q'] for row in comparison_rows})
    responses = [reciprocal_response(q) for q in ordered]
    # Adjacent binary64 q values may round to one weight; separated retained samples must decrease.
    assert all(earlier >= later for earlier, later in zip(responses, responses[1:]))
    assert responses[0] > responses[len(responses) // 2] > responses[-1]
    assert all(reciprocal_response(row['q']) >= row['w'] for row in comparison_rows)


@pytest.mark.parametrize('q', (-1.0, math.nan, math.inf, -math.inf))
def test_reciprocal_response_rejects_invalid_q(q) -> None:
    """The opt-in response refuses nonfinite and negative dimensionless distance."""
    with pytest.raises(ValueError):
        reciprocal_response(q)


def test_sqrt_reciprocal_response_domain() -> None:
    """The third curve keeps unit contact, a stronger tail and finite large-q support."""
    assert decay.sqrt_reciprocal_response(0.0) == 1.0
    assert decay.sqrt_reciprocal_response(3.0) == 0.5
    assert decay.sqrt_reciprocal_response(15.0) == 0.25
    assert 0 < decay.sqrt_reciprocal_response(sys.float_info.max) < 1


@pytest.mark.parametrize('q', (-1.0, math.nan, math.inf, -math.inf))
def test_sqrt_reciprocal_response_rejects_invalid_q(q) -> None:
    """The third curve refuses invalid q rather than returning a fabricated response."""
    with pytest.raises(ValueError):
        decay.sqrt_reciprocal_response(q)


def test_sqrt_comparison_preserves_pinned_reciprocal_rows(comparison_rows, sqrt_comparison_rows) -> None:
    """All third-curve rows retain the complete previously accepted two-curve evidence."""
    baseline = Path(__file__).resolve().parents[1] / (
        'outputs/design/group_distance_decay_ifc/run_20261111_rms_rss_reciprocal_comparison_v1/decay_rows.json'
    )
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == (
        'fa940d82c7121a810c0c8ba48e6a8edbf21646ebedbd6e6c03b2bbeb3bc0b67a'
    )
    assert _json_safe(comparison_rows) == json.loads(baseline.read_text(encoding='utf-8'))['rows']
    assert len(sqrt_comparison_rows) == 666
    for original, third in zip(comparison_rows, sqrt_comparison_rows):
        assert set(third) - set(original) == {'w_sqrt_reciprocal', 'sqrt_reciprocal_formula_version'}
        assert {key: third[key] for key in original} == original
        assert third['sqrt_reciprocal_formula_version'] == 'group-union-rms-rss-sqrt-reciprocal/1'
        assert third['w_sqrt_reciprocal'] == 1.0 / math.sqrt(1.0 + third['q'])
        assert third['w_sqrt_reciprocal'] ** 2 == pytest.approx(third['w_reciprocal'], rel=1e-15)
        assert 0 < third['w'] <= third['w_reciprocal'] <= third['w_sqrt_reciprocal'] <= 1
    ordered = sorted(sqrt_comparison_rows, key=lambda row: row['q'])
    assert all(a['w_sqrt_reciprocal'] >= b['w_sqrt_reciprocal'] for a, b in zip(ordered, ordered[1:]))
    assert ordered[0]['w_sqrt_reciprocal'] > ordered[333]['w_sqrt_reciprocal'] > ordered[-1]['w_sqrt_reciprocal']


@pytest.mark.parametrize('compare,sqrt_compare,power_06', ((False, False, False), (True, False, False),
                                                        (True, True, False), (True, True, True)))
def test_power_06_and_old_comparison_exports_keep_explicit_modes(
    experiment_inputs, decay_rows, comparison_rows, sqrt_comparison_rows, power_06_comparison_rows,
    monkeypatch, tmp_path, compare, sqrt_compare, power_06,
) -> None:
    """Real HTML/CSV/JSON bind the selected mode while the existing output guard still applies."""
    loads = []

    def retained_inputs(**paths):
        """Reuse this module's already authenticated context instead of reauditing source files."""
        loads.append(paths)
        return experiment_inputs

    def overview(inputs, rows, output_dir, *, compare_reciprocal=False, compare_sqrt_reciprocal=False,
                 compare_power_06=False):
        """Leave static rendering to the actual trial and test only its export handoff here."""
        assert inputs is experiment_inputs and compare_reciprocal is compare
        assert compare_sqrt_reciprocal is sqrt_compare
        assert compare_power_06 is power_06
        for name in ('overview.svg', 'overview.png'):
            (output_dir / name).write_bytes(b'static rendering checked in the real retained trial')

    monkeypatch.setattr(decay, 'ROOT', tmp_path)
    monkeypatch.setattr(decay, 'load_experiment_inputs', retained_inputs)
    monkeypatch.setattr(decay, '_write_overview', overview)
    destination = tmp_path / 'outputs/design/comparison-export'
    options = ({'compare_power_06': True} if power_06 else {'compare_sqrt_reciprocal': True} if sqrt_compare else
               {'compare_reciprocal': True} if compare else {})
    manifest = decay.run_experiment(destination, **options)
    assert loads == [{'bundle_path': decay.BUNDLE_PATH, 'package_path': decay.PACKAGE_PATH}]
    expected_rows = (power_06_comparison_rows if power_06 else sqrt_comparison_rows if sqrt_compare else
                     comparison_rows if compare else decay_rows)
    payload = json.loads((destination / 'decay_rows.json').read_text(encoding='utf-8'))
    assert payload['rows'] == _json_safe(expected_rows)
    assert payload['schema'] == ('group-distance-decay-four-curve-rows/1' if power_06 else
                                 'group-distance-decay-three-curve-rows/1' if sqrt_compare else
                                 'group-distance-decay-comparison-rows/1' if compare else 'group-distance-decay-rows/1')
    assert manifest['schema'] == ('group-distance-decay-four-curve-run/1' if power_06 else
                                  'group-distance-decay-three-curve-run/1' if sqrt_compare else
                                  'group-distance-decay-comparison-run/1' if compare else 'group-distance-decay-run/1')
    assert payload['formula_version'] == manifest['formula_version'] == 'group-union-rms-rss-exp/1'
    assert manifest['path_distance_used'] is False
    for metadata in (payload, manifest):
        if compare:
            assert metadata['reciprocal_formula_version'] == RECIPROCAL_FORMULA_VERSION
            assert metadata['reciprocal_formula'] == RECIPROCAL_FORMULA
            assert metadata['default_curve'] == ('power_06' if power_06 else 'sqrt_reciprocal' if sqrt_compare else 'reciprocal')
            assert metadata['color_scale'] == [0, 1]
        else:
            assert not {'reciprocal_formula_version', 'reciprocal_formula', 'default_curve'} & metadata.keys()
        if sqrt_compare:
            assert metadata['sqrt_reciprocal_formula_version'] == 'group-union-rms-rss-sqrt-reciprocal/1'
            assert metadata['sqrt_reciprocal_formula'] == 'w_sqrt_reciprocal=1/sqrt(1+q)'
        else:
            assert 'sqrt_reciprocal_formula_version' not in metadata
        if power_06:
            assert metadata['power_06_formula_version'] == 'group-union-rms-rss-power-06/1'
            assert metadata['power_06_formula'] == 'w_power_06=(1+q)^(-0.6)'
            assert metadata['power_06_exponent'] == 0.6
        else:
            assert not {'power_06_formula_version', 'power_06_formula', 'power_06_exponent'} & metadata.keys()

    with (destination / 'decay_rows.csv').open(newline='', encoding='utf-8') as stream:
        exported = list(csv.DictReader(stream))
    assert len(exported) == 666
    for record, expected in zip(exported, expected_rows):
        assert record['pair_id'] == expected['pair_id']
        assert float(record['w']) == expected['w']
        assert json.loads(record['lineage']) == _json_safe(expected['lineage'])
        if compare:
            assert float(record['w_reciprocal']) == expected['w_reciprocal']
            assert record['reciprocal_formula_version'] == RECIPROCAL_FORMULA_VERSION
        else:
            assert 'w_reciprocal' not in record
        if sqrt_compare:
            assert float(record['w_sqrt_reciprocal']) == expected['w_sqrt_reciprocal']
            assert record['sqrt_reciprocal_formula_version'] == 'group-union-rms-rss-sqrt-reciprocal/1'
        else:
            assert 'w_sqrt_reciprocal' not in record
        if power_06:
            assert float(record['w_power_06']) == expected['w_power_06']
            assert record['power_06_formula_version'] == 'group-union-rms-rss-power-06/1'
        else:
            assert 'w_power_06' not in record

    document = (destination / 'index.html').read_text(encoding='utf-8')
    assert document.count('<g data-group=') == 37
    assert document.count('data-pair=') == 666
    assert document.count('fill-rule="evenodd"') == 37
    assert '#plan g[data-group]{outline:none}' in document
    embedded = re.search(r'const rows=(.*?), colors=', document)
    assert embedded and json.loads(embedded.group(1)) == _json_safe(expected_rows)
    if compare:
        assert 'id="curve"' in document
        selected = 'w_power_06' if power_06 else 'w_sqrt_reciprocal' if sqrt_compare else 'w_reciprocal'
        assert re.search(r'<option(?=[^>]*value="' + selected + r'")(?=[^>]*selected)[^>]*>', document)
        assert 'value="w"' in document
        assert 'w_exp' in document and 'w_reciprocal' in document
        if power_06:
            assert document.count('<option value="w') == 4
            assert '<th>w_power_06</th>' in document
            assert 'id="formula-version"' in document
            assert 'w_power_06 = (1 + q)^(-0.6)' in document
            assert 'data-formula-version="group-union-rms-rss-power-06/1" selected' in document
    else:
        assert 'id="curve"' not in document
    for name, expected_hash in manifest['artifact_hashes'].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected_hash
    with pytest.raises(FileExistsError):
        decay.run_experiment(destination, **options)
    assert len(loads) == 1


def test_sqrt_reciprocal_cli_flag_is_standalone(monkeypatch, tmp_path, capsys) -> None:
    """The new CLI flag alone opts in without silently changing the older flag."""
    calls = []

    def capture(output_dir, **options):
        """Observe the CLI handoff without another authenticated IFC generation."""
        calls.append((output_dir, options))
        return {}

    monkeypatch.setattr(decay, 'run_experiment', capture)
    monkeypatch.setattr(sys, 'argv', ['decay', '--output-dir', str(tmp_path), '--compare-sqrt-reciprocal'])
    decay.main()
    assert calls == [(tmp_path, {'bundle_path': decay.BUNDLE_PATH, 'package_path': decay.PACKAGE_PATH,
                                'compare_reciprocal': False, 'compare_sqrt_reciprocal': True,
                                'compare_power_06': False})]
    assert json.loads(capsys.readouterr().out) == {}


def test_power_06_response_domain() -> None:
    """The fixed trial keeps unit contact and a finite positive tail at the largest q."""
    assert decay.power_06_response(0.0) == 1.0
    assert decay.power_06_response(31.0) == pytest.approx(0.125)
    assert 0 < decay.power_06_response(sys.float_info.max) < 1


@pytest.mark.parametrize('q', (-1.0, math.nan, math.inf, -math.inf))
def test_power_06_response_rejects_invalid_q(q) -> None:
    """Invalid dimensionless readings cannot become a usable fixed-power response."""
    with pytest.raises(ValueError, match='finite and nonnegative'):
        decay.power_06_response(q)


def test_power_06_preserves_all_accepted_rows_and_owner_oracle(sqrt_comparison_rows, power_06_comparison_rows) -> None:
    """All 666 rows append only the fixed response and match the preimplementation oracle."""
    root = Path(__file__).resolve().parents[1]
    baseline = root / 'outputs/design/group_distance_decay_ifc/verification_power_06_20261111/owner-baseline.json'
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == (
        '988c2e9ab778b886c526086d1c2f46a7df80fe8817ad82ddc80c801e39df71a9')
    oracle = json.loads(baseline.read_text(encoding='utf-8'))
    for relative, expected_hash in oracle['historical_hashes'].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected_hash
    accepted = root / 'outputs/design/group_distance_decay_ifc/run_20261111_rms_rss_sqrt_reciprocal_comparison_v1/decay_rows.json'
    assert _json_safe(sqrt_comparison_rows) == json.loads(accepted.read_text(encoding='utf-8'))['rows']
    assert len(power_06_comparison_rows) == len(oracle['oracle']) == 666
    for original, fourth, expected in zip(sqrt_comparison_rows, power_06_comparison_rows, oracle['oracle']):
        assert set(fourth) - set(original) == {'w_power_06', 'power_06_formula_version'}
        assert {key: fourth[key] for key in original} == original
        assert fourth['pair_id'] == expected['pair_id'] and fourth['q'] == expected['q']
        assert fourth['w_power_06'] == pytest.approx(expected['expected_power_06'], rel=2e-15)
        assert fourth['power_06_formula_version'] == 'group-union-rms-rss-power-06/1'
        assert 0 < fourth['w'] <= fourth['w_reciprocal'] <= fourth['w_power_06'] <= fourth['w_sqrt_reciprocal'] <= 1
    ordered = sorted(power_06_comparison_rows, key=lambda row: row['q'])
    assert all(a['w_power_06'] >= b['w_power_06'] for a, b in zip(ordered, ordered[1:]))
    assert ordered[0]['w_power_06'] > ordered[333]['w_power_06'] > ordered[-1]['w_power_06']


@pytest.mark.parametrize('status', ('unavailable', 'invalid', 'partial', 'unknown'))
def test_power_06_preserves_unavailable_status_and_nulls(experiment_inputs, status) -> None:
    """A fourth response cannot bypass the existing raw-reading status gate."""
    first, *remaining = experiment_inputs.outputs
    changed = replace(first, observation={**first.observation, 'raw_status': status, 'value': None})
    context = replace(experiment_inputs, outputs=(changed, *remaining))
    original = build_comparison_rows(context, compare_sqrt_reciprocal=True)
    fourth = build_comparison_rows(context, compare_power_06=True)
    row = next(row for row in fourth if row['pair_id'] == first.target['identity'])
    assert row['status'] != 'computed' and row['reason']
    assert row['w_power_06'] is row['w_sqrt_reciprocal'] is row['w_reciprocal'] is row['w'] is None
    assert [{key: row[key] for key in previous} for previous, row in zip(original, fourth)] == original
    json.dumps(_json_safe(fourth), allow_nan=False)


def test_power_06_cli_flag_is_standalone(monkeypatch, tmp_path, capsys) -> None:
    """The fixed-power CLI flag alone opts in and leaves older flags at their defaults."""
    calls = []

    def capture(output_dir, **options):
        """Observe the parser handoff without repeating IFC authentication."""
        calls.append((output_dir, options))
        return {}

    monkeypatch.setattr(decay, 'run_experiment', capture)
    monkeypatch.setattr(sys, 'argv', ['decay', '--output-dir', str(tmp_path), '--compare-power-06'])
    decay.main()
    assert calls == [(tmp_path, {'bundle_path': decay.BUNDLE_PATH, 'package_path': decay.PACKAGE_PATH,
                                'compare_reciprocal': False, 'compare_sqrt_reciprocal': False,
                                'compare_power_06': True})]
    assert json.loads(capsys.readouterr().out) == {}

