"""Bounded nonspatial backend and retained S4 metadata feasibility checks only."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path

import networkx as nx
from shapely.geometry import box, shape
from features.field_core import FieldQuery

ROOT = Path(__file__).resolve().parents[3]
S4 = ROOT / 'outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z'
PIN = '1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077'


def fingerprint(value):
    """Hash immutable handoff contents, retaining explicit null query fields."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def recover(edges, states, optimistic=False):
    """Recover a stable abstract path from exact backend predecessor labels."""
    graph = nx.Graph()
    for a, b in edges:
        graph.add_edge(a, b, weight=0.25, source_ref=f'edge:{min(a,b)}:{max(a,b)}')
    # Duplicate abstract accesses retain the minimum cost, then stable identity.
    accesses = [('access:z', 's', 0.5), ('access:b', 's', 0.125), ('access:a', 's', 0.125)]
    seed = min(accesses, key=lambda item: (item[2], item[0]))
    graph.add_edge('root', seed[1], weight=seed[2])
    pred, distance = nx.dijkstra_predecessor_and_distance(graph, 'root')
    best = {}
    for node in sorted((n for n in distance if n != 'root'), key=lambda n: (distance[n], n)):
        candidates = []
        for parent in pred[node]:
            assert distance[parent] + graph[parent][node]['weight'] == distance[node]
            assert distance[parent] < distance[node], 'non-increasing float label is a contract failure'
            if parent == 'root':
                previous = (0, 0, seed[0], ())
            else:
                previous = best[parent]
            unknown, conditional, access, path = previous
            candidates.append((unknown + (states.get(node) == 'unknown'),
                               conditional + (states.get(node) == 'conditional'), access, path + (node,)))
        best[node] = min(candidates, key=lambda label: label if optimistic else label[1:])
    selected = best['t']
    route = selected[-1]
    lineage = tuple(f'node:{n}' for n in route) + tuple(graph[a][b]['source_ref'] for a, b in itertools.pairwise(route))
    return selected, distance['t'], lineage


def main():
    """Exercise graph logic and real retained S4 metadata without IFC distances."""
    assert nx.__version__ == '3.6.1'
    tracemalloc.start()
    started = time.perf_counter()
    edges = [('s', 'a'), ('a', 't'), ('s', 'b'), ('b', 't')]
    checks = 0
    for order in itertools.permutations(edges):
        plain = recover(order, {})
        conditional = recover(order, {'a': 'conditional'})
        optimistic = recover(order, {'a': 'unknown'}, True)
        assert plain[0] == (0, 0, 'access:a', ('s', 'a', 't'))
        assert conditional[0] == optimistic[0] == (0, 0, 'access:a', ('s', 'b', 't'))
        assert plain[1] == conditional[1] == optimistic[1] == 0.625
        assert 'node:a' not in conditional[2] and 'edge:a:s' not in conditional[2]
        checks += 3
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    manifest = json.loads((S4 / 's4_confirmed_manifest.json').read_text(encoding='utf-8'))
    result = json.loads((S4 / 's4_confirm_result.json').read_text(encoding='utf-8'))
    failed = json.loads((S4 / 'domain_result.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'confirmed' and result['status'] == 'active' and result['handoff_executed']
    assert failed['analysis_domain'] is None and failed['status'] == 'not_available'
    assert result['analysis_domain'] == manifest['confirmed_domain']
    assert result['confirmation_binding'] == manifest['confirmation_binding']
    binding = result['confirmation_binding']
    assert result['domain_request_identity'] == binding['request_id']
    assert result['selected_candidate_id'] == manifest['selected_candidate_id'] == 'S4'
    assert result['analysis_domain']['provenance']['candidate_version_id'] == manifest['selected_candidate_version_id']
    assert result['analysis_domain']['geometry_refs'] == [record['id'] for record in result['domain_geometries']]
    source = Path(manifest['source']['path'])
    with source.open('rb') as stream:
        actual_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert actual_hash == manifest['source']['sha256'] == PIN
    assert source.stat().st_size == manifest['source']['bytes']
    domain = shape(result['scope_polygon'])
    assert domain.is_valid and not domain.is_empty
    spacing = 0.1  # Explicit diagnostic feasibility parameter, not a production grid.
    x0, y0, x1, y1 = domain.bounds
    origin = (math.floor(x0 / spacing) * spacing, math.floor(y0 / spacing) * spacing)
    rows = math.ceil((y1 - origin[1]) / spacing)
    cols = math.ceil((x1 - origin[0]) / spacing)
    assert box(*origin, origin[0] + cols * spacing, origin[1] + rows * spacing).covers(domain)
    query = asdict(FieldQuery(domain_id=result['analysis_domain']['id'], frame=binding['frame_id'], revision=binding['source_revision']))
    assert set(query) == {'domain_id','frame','plane','height_band','demand','tolerance','revision'}
    assert query['plane'] is query['height_band'] is query['demand'] is None
    seam = {'analysis_plane': manifest['analysis_plane'], 'query': query,
            'grid': {'origin': origin, 'spacing': spacing, 'n_rows': rows, 'n_cols': cols,
                     'columns': '+plane_x', 'rows': '+plane_y', 'cell_rule': 'axis_aligned_square'},
            'domain_content': fingerprint(result['scope_polygon']), 'source_sha256': actual_hash}
    assert fingerprint(seam) == fingerprint(json.loads(json.dumps(seam)))
    assert fingerprint(seam) != fingerprint({**seam, 'analysis_plane': {**manifest['analysis_plane'], 'revision': 2}})
    forward = (0.1 + 0.2) + 0.3
    regrouped = 0.1 + (0.2 + 0.3)
    assert forward != regrouped
    print(json.dumps({'environment': {'python': sys.executable, 'networkx': nx.__version__, 'networkx_path': nx.__file__},
        'graph_logic': {'permutation_checks': checks, 'runtime_s': elapsed, 'tracemalloc_peak_bytes': peak,
                        'nonspatial': True, 'second_dijkstra': False, 'selected_lineage_checks': True},
        's4': {'source_sha256': actual_hash, 'source_bytes': source.stat().st_size,
               'area_m2': domain.area, 'bounds': domain.bounds, 'metadata_grid': seam['grid'],
               'query': query, 'metadata_fingerprint': fingerprint(seam),
               'occupancy_grid_construction': 'implementation_task_not_run'},
        'arithmetic': {'left_sum': forward, 'regrouped_sum': regrouped, 'residual': forward-regrouped}}, indent=2))


if __name__ == '__main__':
    main()
