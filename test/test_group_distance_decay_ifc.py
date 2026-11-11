"""Acceptance checks for the retained real-IFC group-distance decay experiment."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import math
import json
from pathlib import Path

import pytest
from shapely import constrained_delaunay_triangles
from shapely.affinity import rotate, scale, translate

from features.group_distance_evidence_package import SOURCE_CHANNEL
from features.field_core import build_evidence_package_contract
from scripts.design.group_level import replay_evidence_package_readback as readback
from scripts.design.group_level.run_group_distance_decay_ifc import (
    build_decay_rows, geometry_scaled_response, load_experiment_inputs,
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
    assert geometry_scaled_response(
        row['distance_m'], *(scales[identity]['rho2_m2'] for identity in pair_groups)
    ) == baseline


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

