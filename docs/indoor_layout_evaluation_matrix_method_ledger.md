# Indoor Layout Evaluation Matrix Method Ledger

Date: 2026-07-06

Purpose: record which theories and tool paths are adopted, deferred, or rejected for the current implementation. This is a technical decision ledger, not a literature review.

## Current Slice

The current code implements a structured SVG prototype:

- `load_structured_svg_scene()` parses authored 2D metadata.
- `evaluate_scene(scene)` emits stable metric rows.
- `matrix["graph"]` exposes entry/path/region touch evidence.

Important boundary: bbox-touch graph evidence remains a proxy. It proves that the current fixture has explicit graph-shaped evidence, not that the project has a real walk graph, visibility graph, or navigation mesh.

The current test harness now exposes embedded OCTA tests to pytest via a root `conftest.py` path shim and restores the repository cwd after legacy OCTA test modules run import-time `os.chdir`. This is test compatibility for the vendored toolbox, not a new evaluator dependency boundary.

The current path polygon clearance proxy remains a proxy. It reports the
nearest furniture or blocking-boundary bbox gap to an authored path polygon,
with bbox fallback for non-polygon paths; it does not compute medial-axis
clearance, polygon booleans, or a true negative-space route.

The current sampled occupancy grid BFS remains a proxy. It samples blocked,
reachable, component, entry-to-region grid-distance, and see-block visibility
reachability cells from authored geometry so the project can inspect walkable
space before implementing CAD boolean negative-space polygons.

The current negative-space area proxy remains a proxy. It subtracts blocker
union area from the authored room polygon area using rect-cell decomposition;
it does not produce CAD boolean room-minus-blocker polygons.

The current negative-space component proxy remains a proxy. It decomposes the
room bbox by blocker bbox edges, clips free-cell area by room polygon overlap,
subtracts polygon blocker overlap when blocker points are available, and
reports connected free rect-cells; it does not produce CAD boolean
topology.

## Method Decisions

| Method | Source Basis | Use Now | Use Later | Do Not Use For | Decision |
|---|---|---|---|---|---|
| OCTA | OCTA paper and project/manual pages | repeated comparable arrays such as north tables | size/bbox order if the wrapper exposes more OCTA features | whole-room semantic scoring | Adopt only for valid local order views. |
| Local geometry descriptors | current repo `Rect`/bbox patterns | group compactness, local axes, phase scores | PCA/minimum oriented bbox for irregular regions | replacing OCTA where a clean repeated matrix is valid | Adopt now. |
| Affordance/boundary-cue inferred regions | current repo `Rect`/bbox patterns plus structured affordance, boundary-cue metadata, and spacing-side margin evidence | candidate region bboxes and axis gap bands for missing explicit regions | alpha shapes, clustering, negative-space split/merge checks | final semantic region discovery, path certification, or BIM plugin topology | Adopt as a small auditable bridge only. |
| Path polygon clearance proxy | current repo `Rect`/bbox patterns | path-to-blocker proximity warning | true clearance field after negative-space polygons exist | circulation clearance certification | Adopt only as a temporary diagnostic. |
| Negative-space area proxy | current repo `Polygon`/`Rect` overlap helpers | room area minus rect-cell blocker union area | boolean room-minus-blocker polygon extraction | route certification, connectivity, de-overlapped free-space topology | Adopt as an area-balance bridge only. |
| Negative-space rect components | current repo `Rect` plus polygon-rect overlap helper | room-polygon-clipped rect-cell free-space components with polygon blocker overlap | true polygon components / navmesh | final route certification or skeleton topology | Adopt as a bridge component proxy only. |
| Sampled occupancy grid BFS | occupancy-grid mapping and grid-search planning practice | free-cell ratio, entry reachability, component fragmentation, entry-region grid-distance proxy, and see-block visibility reachability proxy | debugging negative-space extraction and checking fixture variants | final route certification, continuous route length, navmesh distance, isovist, ray casting, or visibility graph analysis | Adopt as bridge evidence only. |
| Isovist | Benedikt 1979 | documented concept only | visibility fields and visual exposure metrics | walking reachability or furniture order | Defer until visibility graph slice. |
| Visibility Graph Analysis | Turner et al. 2001 and depthmapX | documented concept only | visual connectivity, centrality, room traversal descriptors | sofa/table order and boundary material strength | Defer until negative-space/visibility graph geometry exists. |
| Space syntax graph metrics | depthmapX / space syntax tooling | documented concept only | integration, depth, choice after a graph exists | object-level furniture regularity | Defer. |
| Straight skeleton / medial-axis geometry | CGAL straight skeleton, scikit-image skeleton docs | not used | path centerline extraction from walkable negative space | current fixture touch evidence | Defer. Avoid dependency until polygon boolean/negative space is stable. |
| Voronoi geometry | Shapely Voronoi docs | not used | candidate centerline or clearance graph experiments | final routing without clipping and validation | Defer. |
| Perceptual grouping / uniform connectedness | Wagemans et al. 2012; Palmer and Rock 1994 | boundary/grouping uncertainty language | calibrating rug/material/color boundary weights | deterministic grouping thresholds | Use as calibration rationale, not as a hard rule. |
| RhinoCommon geometry | Rhino developer docs | adapter design only | Rhino curves, breps, points to neutral records | direct dependency inside evaluator | Adopt as future adapter layer. |
| Grasshopper DataTree | Grasshopper SDK docs | adapter design only | component IO paths for objects/groups/regions/metrics | metric function internals | Adopt as future wrapper only. |
| VisualARQ / BIM objects | VisualARQ features and API docs | adapter design only | map walls, curtain walls, doors, columns, spaces, and furniture to neutral records | direct evaluator coupling to VisualARQ document-resident APIs | Adopt as future import layer, with caution around Grasshopper. |

## Source Notes

### OCTA

Source:

- https://link.springer.com/article/10.3758/s13428-022-01900-w
- https://elinevg.github.io/OCTA/
- https://elinevg.github.io/OCTA_manual/

Decision:

OCTA is a good fit for visual order/complexity over comparable multi-element displays with explicit feature variation. In this repo, that maps cleanly to the repeated table array. It does not justify scoring tables, sofas, paths, rugs, glass, and columns as one global OCTA pattern.

Implementation consequence:

- Keep `OrderAnalyzer` for `north_tables_order`.
- Keep sofa/armchair/region rows geometry-based.
- Add more OCTA features only when a local repeated view needs them.

### Sampled Occupancy Grid BFS

Sources:

- A. Elfes, "Using occupancy grids for mobile robot perception and navigation" (IEEE Computer, 1989).
- S. M. LaValle, "Planning Algorithms", grid search / graph search planning chapters: https://lavalle.pl/planning/

Decision:

An occupancy grid is appropriate as an intermediate sampled representation of
blocked/free space, and BFS over the grid is appropriate as reachability
evidence. It is not a replacement for the continuous room-minus-blocker
geometry the full system needs.

Implementation consequence:

- `matrix["sampled_walkable_space"]` reports sampled cell counts and ratios.
- `path_connectivity` rows with `sampled_*` names must remain explicitly proxy-labeled.
- `sampled_resolution_sensitivity` reports the max half/base/double cell-size range across selected sampled ratios. It is a disclosure that sampled proxy rows are grid-size dependent, not a full multi-resolution validation framework.
- `sampled_negative_space_area_ratio_delta` reports the absolute difference between `sampled_walkable_cell_ratio` and `negative_space_area_ratio_proxy`. It is a proxy-consistency warning, not CAD boolean validation, geometric truth, navmesh validation, or resolution calibration.
- `sampled_mean_entry_region_grid_distance` is four-neighbor grid distance in scene units, not a continuous route length.
- `sampled_mean_region_pair_grid_distance` is four-neighbor grid distance between sampled region cells, and `sampled_region_pair_reachable_ratio` is the share of finite pair distances. They are pairwise sampled-distance descriptors, not continuous route lengths, navmesh paths, medial-axis routes, or space-syntax integration.
- `sampled_visibility_reachable_region_ratio` uses the `see_block` channel only; it is not a visibility graph or isovist metric.
- `sampled_visibility_only_region_ratio` compares see-block and walk-block sampled reachability; it is a boundary-channel contrast, not a perception verdict.
- `sampled_walk_only_region_ratio` is the symmetric walk-block vs see-block contrast for walkable-but-not-visible separation.
- `sampled_walk_visibility_disagreement_region_ratio` is the XOR of the two sampled channel reachability states at region level.
- `sampled_mean_visibility_region_grid_distance` is see-block weighted grid distance, not visual distance, isovist depth, or VGA integration.
- `sampled_entry_reachable_region_pair_ratio` is the share of region pairs that share an entry-reachable sampled walk component. It reports connected pair evidence and `sampled_unreachable_region_pair_evidence`, but remains four-neighbor sampled component evidence, not navmesh routing, route distance, route quality, or shortest-path routing.
- `sampled_visibility_reachable_region_pair_ratio` is the share of region pairs where both regions are reachable in sampled see-block BFS. It is useful for glass/screen contrasts against walk reachability, but it is not an isovist, Visibility Graph Analysis, visual integration, route distance, or calibrated transparency model.
- `sampled_visibility_only_region_pair_ratio`, `sampled_walk_only_region_pair_ratio`, and `sampled_walk_visibility_disagreement_region_pair_ratio` are set differences/XOR between sampled walk pair evidence and sampled visibility pair evidence. They flag boundary-channel contrasts, but they are not a final route or perceptual-visibility judgment.
- `line_of_sight_entry_region_ratio` checks entry-to-region centerlines against authored `see_block` boundaries and records blocking boundary ids. It also records `blocking_boundary_evidence` with `intersection_points`, `intersection_distances_from_start`, and `intersection_distance_ratios` for each hit so the centerline obstruction is inspectable. It is stronger than sampled BFS for direct sight evidence, but still not an isovist field, full Visibility Graph Analysis, or calibrated transparency model.
- `line_of_sight_region_pair_ratio` applies the same authored `see_block` centerline test between region bbox centers and carries the same `blocking_boundary_evidence` / intersection-distance structure. It is direct pair visibility evidence, not an isovist field, full Visibility Graph Analysis, visual integration, or calibrated perception model.
- `line_of_sight_graph` packages the same entry-region and region-pair centerline evidence as nodes and visibility edges, including `visible`, centerline length, and blocker evidence. Its `metrics` report `visible_edge_ratio`, `blocked_edge_ids`, blocker ids, blocker-to-edge incidence evidence, and mean centerline length; `line_of_sight_graph_visible_edge_ratio`, `line_of_sight_graph_blocked_edge_ratio`, and `line_of_sight_graph_blocking_boundary_count` expose edge and unique blocker audit rows. `visual_analysis_handoff.visibility_graph.items` carries the visibility edges for adapter consumers. It is graph-shaped direct-sight evidence, not full VGA adjacency, isovist polygon sampling, visual integration, or perception calibration.
- `isovist_radial_blocked_ray_ratio` uses `radial_isovist_see_block_ray_intersection_proxy`: eight room-bounded radial rays from each entry and analysis-region center, clipped by the nearest authored room boundary or `see_block` boundary. It is executable isovist-style sampling evidence, but it is not a full isovist polygon, Visibility Graph Analysis, visual integration, or calibrated exposure field.
- `isovist_radial_hit_polygon_area_mean` uses `radial_isovist_hit_point_polygon_area_proxy`: for each radial vantage, ordered ray hit points are connected into a polygon, and `mean_hit_polygon_area` averages those polygon areas. `visual_analysis_handoff.isovist_radial_proxy.ray_items` and `visual_analysis_handoff.isovist_radial_proxy.area_items` carry the per-ray and per-vantage area evidence for adapter consumers. This exposes an area-like visual openness proxy and `isovist_area_evidence`, but it is not a full isovist polygon, VGA cell field, visual integration, or calibrated visual exposure model.
- `path_blocker_overlap_area_ratio` uses `path_polygon_blocker_union_overlap_area`: blocker union overlap area inside the authored path polygon. It avoids aggregate double-counting for overlapping blocker bboxes, but it remains a path-conflict proxy rather than negative-space route geometry.
- `graph_entry_region_reachability` now carries `reached_region_ids` and `unreached_region_ids`. This makes the proxy BFS numerator and misses explicit, but it remains bbox-touch graph reachability, not route certification.
- `graph_entry_region_capacity_proxy` multiplies bbox-touch entry-region reachability by authored path width continuity and average walk passability. It tracks the spec's capacity idea as an auditable proxy, but it is not max-flow, route capacity, or clearance-weighted shortest path.
- `graph_dead_end_ratio` now carries `dead_end_nodes` with node id, kind, and degree. This makes proxy graph termini auditable, but dead ends remain bbox-touch graph degree evidence, not extracted route termini from a navigation graph.
- `graph_component_count` exposes connected components over the bbox-touch graph. It is useful for auditing isolated entries/regions, but it is not a CAD negative-space island, navmesh component, or route graph connectivity result.
- `graph_loop_count` and `graph_loop_ratio` now carry `cycle_rank_inputs` with node count, edge count, and component count. This makes the cycle-rank formula traceable, but loops remain bbox-touch proxy graph evidence, not circulation loops from a navmesh or medial-axis graph.
- `negative_space_area_ratio_proxy` uses `room_polygon_minus_blocker_union_area_proxy`: room polygon area minus blocker union area via rect-cell decomposition. It avoids aggregate double-counting for overlapping blocker bboxes, sums separate polygon blockers within a cell, and de-duplicates identical blocker geometry, but the result is still not a CAD boolean free-space polygon.
- `negative_space_polygon_overlap_risk_count` detects overlapping non-identical polygon blockers and exposes the blocker pairs as evidence. It is a CAD-boolean upgrade trigger, not a fix for arbitrary polygon union.
- `negative_space_component_count` and `negative_space_largest_component_area_ratio` come from `room_polygon_rect_cell_decomposition_proxy`: room-bbox rect-cell decomposition around blocker bboxes with cell areas clipped by room polygon overlap and reduced by blocker coverage per cell; they are continuous proxy components, not CAD boolean topology. `component_rects` adds each component bbox, `cell_count`, `cell_rects`, and area as inspectable geometry evidence for the proxy. `component_area_total`, `component_cell_area_sum_total`, `negative_space_component_area_residual`, and `negative_space_component_area_residual_ratio` audit whether the descriptor's negative-space area and decomposed component cells close under the current rect-cell proxy; this is still not CAD boolean validation.
- `negative_space_free_polygon_count` uses `room_polygon_rect_cell_free_space_polygons_proxy`: each current free rect-cell is exported as a four-point polygon with component/cell ids and area. This is a stable polygon-evidence interface for later CAD/navmesh adapters, not a CAD boolean room-minus-blocker result or cleaned free-space topology.
- `negative_space_room_minus_blocker_polygon_count` uses `rect_cell_room_minus_blocker_boundary_union_proxy`: shared rect-cell edges are canceled inside each negative-space component, then remaining boundary edges are merged into `room_minus_blocker_polygons` with one outer ring and any inner hole rings. This is a stronger boundary-loop export for adapter handoff, but still not CAD boolean room-minus-blocker topology, curve cleanup, or a navmesh polygon set.
- `cad_room_minus_blocker_polygon_count` uses `shapely_room_polygon_difference_blocker_union`: build a Shapely polygon from the authored room boundary and subtract the union of current walk blockers, then export `cad_room_minus_blocker_polygons` with normalized rings, holes, area, and `source = shapely_difference`. This is the first real polygon-difference slice, but it is still not RhinoCommon / VisualARQ hosted topology, BIM family validation, CAD curve cleanup, navmesh faces, medial-axis clearance, or route certification.
- `cad_room_minus_blocker_area_residual_ratio` uses `shapely_room_minus_blocker_area_minus_negative_space_area`: compare summed Shapely room-minus-blocker area with the current `negative_space_area` and expose the residual. This is an engineering closure check between two current geometry paths, not a layout-quality score, hosted-model validation, navmesh validation, or proof that CAD curves are clean.
- `cad_room_minus_blocker_largest_component_area_ratio` uses `shapely_largest_component_area_over_total_free_area`: divide the largest Shapely free-space component area by total Shapely free-space area. This is a fragmentation severity descriptor, not route reachability, shortest-path routing, route quality, or navmesh island validation.
- `cad_room_minus_blocker_entry_connected_region_ratio` uses `shapely_component_entry_region_touch_proxy`: intersect each Shapely free-space component with analysis regions and test entry touches, then report `cad_room_minus_blocker_component_touch_evidence`. This is component-level evidence for adapter handoff, not hosted doorway topology, navmesh reachability, shortest-path routing, or route quality.
- `cad_room_minus_blocker_entry_connected_area_ratio` uses `shapely_component_entry_touched_area_ratio_proxy`: divide the area of Shapely free-space components touching at least one entry by total Shapely free-space area. This is component-level area coverage, not route reachability, shortest-path routing, route quality, or code-compliant egress.
- `cad_room_minus_blocker_entry_connected_component_ratio` uses `shapely_component_entry_touched_component_count_proxy`: divide the number of Shapely free-space components touching at least one entry by total Shapely free-space component count. This is component-count coverage, not route reachability, shortest-path routing, route quality, or hosted doorway topology.
- `adapter_payload.evidence_geometry.cad_room_minus_blocker_entry_connected_area` exports the same Shapely entry-touched area evidence for downstream adapters, so they can inspect component ids and area totals without parsing matrix rows.
- `cad_room_minus_blocker_entry_connected_region_pair_ratio` uses `shapely_component_entry_connected_region_pair_proxy`: count analysis-region pairs that share an entry-touched Shapely component. This is a coarse component-level connectivity audit, not path routing, shortest distance, navmesh connectivity, or route quality.
- `cad_room_minus_blocker_component_graph` uses `shapely_component_entry_region_touch_graph_proxy`: package the same Shapely component/entry/region touch evidence as component, entry, and region nodes plus touch/overlap edges. `route_topology_handoff.cad_component_graph.items` carries those nodes/edges for adapter consumers. This is a neutral graph-shaped handoff, not a navmesh, skeleton graph, hosted-door graph, or route solver.
- `cad_room_minus_blocker_component_graph_edge_count` surfaces the Shapely component graph edge count and node-type counts as a matrix row, so notebooks and downstream adapters can audit the graph handoff without opening the payload.
- `negative_space_free_polygon_adjacency_count` uses `room_polygon_rect_cell_shared_edge_adjacency_proxy`: it links exported free rect-cell polygons that share a nonzero-length edge and records the shared segment in `free_space_polygon_adjacency`. This is graph-shaped adjacency evidence for later navmesh/skeleton replacement, not shortest-path routing, route quality, medial-axis geometry, or a true navmesh.
- `free_space_polygon_graph` uses `room_polygon_rect_cell_shared_edge_graph_proxy`: it packages the same rect-cell free-space polygons as nodes and shared-edge adjacencies as edges with center-to-center distance, graph `weight`, and shared-edge `clearance_width`. It reports `component_count`, `cycle_rank`, `dead_end_node_count`, `dead_end_nodes`, and `free_space_polygon_graph_cycle_rank` as a matrix row. It also attaches entry/region anchors and `free_space_polygon_graph_mean_entry_region_distance` using `room_polygon_rect_cell_shared_edge_graph_distance_proxy`, plus `free_space_polygon_graph_mean_edge_clearance_width` using `room_polygon_rect_cell_shared_edge_width_proxy`. Entry-region shortest-path evidence carries `path_edge_ids` and `min_clearance_width`, surfaced as `free_space_polygon_graph_mean_entry_region_min_clearance_width` with `room_polygon_rect_cell_shared_edge_path_bottleneck_width_proxy`. Entry-region widest-path evidence uses a max-min shared-edge search and is surfaced as `free_space_polygon_graph_mean_entry_region_widest_clearance_width` with `room_polygon_rect_cell_shared_edge_widest_path_width_proxy`; zero-edge overlaps are retained as evidence but excluded from the mean. `route_topology_handoff.free_space_polygon_graph.items` carries the graph nodes/edges for adapter consumers. `scene_metric_overlay_svg()` shows `free-space-graph-entry-anchor` and `free-space-graph-region-anchor` by default, while dense `free-space-graph-entry-region-path` segments are available only with `include_free_space_paths=True`. This is a neutral graph handoff shape for later navmesh replacement, not navmesh topology, medial-axis clearance, navmesh portal width, route certification, or true circulation loop detection.
- `negative_space_mean_entry_region_free_polygon_distance` uses `entry_to_region_rect_cell_adjacency_shortest_path_proxy`: it runs shortest edge-count reachability over the current shared-edge free-cell graph from entry-touch cells to region-overlap cells and records `entry_region_free_polygon_distance_evidence`. This is a route-graph bridge metric, not weighted path distance, route quality, medial-axis routing, or a true navmesh.
- `negative_space_mean_entry_region_free_polygon_path_length` uses `entry_to_region_rect_cell_centerline_length_proxy`: it reconstructs `path_cells` for each entry-to-region free-cell path and sums center-to-center cell distances. This gives a length-like bridge metric, but it is not a navmesh polyline, route quality score, medial-axis path, or CAD-certified circulation distance.
- polygon blocker support means authored polygon `points` are used for overlap area when available; it is still not a general polygon-polygon arrangement.
- `negative_space_entry_connected_component_ratio` is the share of decomposed negative-space components that touch entries; it is a component-count fragmentation descriptor, not route reachability over a navmesh.
- `negative_space_entry_connected_area_ratio` is the share of decomposed negative-space component area whose component touches at least one entry; entry contact is rect-touch proxy, not hosted doorway topology or graph routing.
- `negative_space_non_entry_connected_area_ratio` is the complementary share of decomposed negative-space area that does not touch entries. It makes "leftover space is not automatically road" auditable, but it is not a semantic dead-space classifier.
- `candidate_path_area_ratio_proxy` multiplies entry-connected negative-space area by authored path width continuity. It is a continuous "more road-like" descriptor, not a road classifier, skeleton, navmesh, or route graph.
- `negative_space_graph` exposes component nodes with copied component bbox, `cell_count`, and `cell_rects`, plus entry-component and component-region touch edges and graph `metrics` for entry-connected component ids, region ids, component-count ratios, area ratios, `component_cell_counts`, `component_cell_area_sums`, `component_cell_area_residuals`, `max_component_cell_area_residual_ratio`, and region-pair evidence so candidate path-space evidence is traceable by node, edge, and summary id lists; it is not a navmesh, VGA graph, or route graph. The residual ratio is an internal rect-cell area closure check, not CAD boolean validation.
- `negative_space_component_cell_area_residual_ratio` surfaces `max_component_cell_area_residual_ratio` as a matrix row so exports can detect rect-cell decomposition drift without inspecting graph internals. It is an engineering consistency metric, not a layout-quality score or CAD boolean proof.
- `negative_space_entry_connected_region_ratio` is the share of regions touched by entry-connected negative-space components; component-region touch is bbox/rect-cell evidence, not shortest-path routing or route quality.
- `negative_space_entry_connected_region_ratio` now also carries `entry_connected_region_ids` and `non_entry_connected_region_ids`, so the ratio's numerator and misses are explicit while remaining rect-cell component-touch evidence.
- `negative_space_entry_connected_region_pair_ratio` is the share of region pairs that share an entry-connected negative-space component; graph metrics report the pair numerator, denominator, ratio, `entry_connected_region_pair_evidence`, and `unconnected_region_pair_evidence`, while the row reuses those graph-native lists. Same-component pair evidence is bbox/rect-cell evidence, not route distance, route quality, detour, or shortest-path routing.
- `candidate_path_region_pair_ratio_proxy` multiplies `candidate_path_area_ratio_proxy` by the entry-connected region-pair numerator over denominator from `negative_space_graph.metrics`, exposing `candidate_path_pair_inputs` so pair-level candidate-path evidence stays traceable. It is still a combined proxy, not a navmesh, shortest-path route, route distance, route quality, or path certification metric.
- `negative_space_component_region_touch` graph edges carry `overlap_area` and `region_area_ratio`; `negative_space_entry_connected_region_area_coverage_ratio` reuses those edge ids to report the mean share of region bbox area overlapped by entry-connected negative-space components. This turns component-region touch into a continuous area proxy, but still depends on bbox/rect-cell decomposition and is not semantic region membership, route distance, or route quality.
- `object_column_axis_phase_alignment` scores furniture/object centers by distance to the nearest authored column axis, normalized by same-direction axis spacing. It is a continuous phase proxy for object-grid relation, not bay containment, column-cell overlap, or irregular grid interpolation.
- `region_centroid_phase_alignment` projects region bbox centers onto the mean region axis and scores projected gap regularity with a coefficient-of-variation score. It adds position phase evidence to region alignment, but is not region overlap, local frame containment, or fuzzy region membership.
- `region_centroid_trend_alignment` uses `region_centroid_pca_axis_cross_deviation_score`: measurable region bbox centers define a PCA trend axis, then each region center reports projection and cross-axis deviation; the score is `1 / (1 + mean_cross_axis_deviation / trend_span)`. This is a first independent `trend` row for dominant layout direction, not semantic procession, circulation intent, or time-series trend.
- Region polygon axes use a point-cloud PCA major axis (`polygon_pca_axis`) for region records with polygon points; boundary and path polygon direction evidence still uses `polygon_longest_edge` where directional cue segments matter.
- `affordance_use_zone_count` uses `object_footprint_adjacent_affordance_rect_zones`: explicit per-side affordance metadata or affordance profile fallback becomes a separate axis-aligned use-zone rectangle adjacent to the furniture footprint. This keeps furniture footprint and usable/occupied affordance space auditable as different entities, but it is not posture simulation, swept human motion, or arbitrary-angle affordance geometry.
- `furniture_affordance_extent_count` uses `object_footprint_plus_own_affordance_zone_extent`: each furniture object gets one maximum bbox envelope from its footprint plus its own affordance zones before objects are grouped into region candidates. Matrix rows, SVG overlay layer `furniture-affordance-extent`, and `adapter_payload.evidence_geometry.furniture_affordance_extents` expose this intermediate hierarchy level. This is a bbox hierarchy bridge from object to activity region, not posture simulation, swept human motion, alpha-shape grouping, or final semantic region discovery.
- `inferred_region_candidate_count` uses `affordance_zone_boundary_cue_expanded_group_candidate_bounds` to count every automatic region candidate before explicit-region suppression, so candidate evidence remains visible even when matching explicit region records already exist.
- `inferred_region_count` uses `affordance_zone_boundary_cue_expanded_group_bounds`: when object `region` labels have no explicit region record, same-region furniture is grouped and bounded by its footprint, explicit per-side affordance use zones, default affordance profile fallback where available (`chair.default` and `podium.default` map `front` to the nearest orthogonal side from object `orientation`; `armchair.default` adds a small four-side personal-use zone), same-region boundary cues with positive grouping strength, and a small spacing-derived margin for no-cue multi-region candidates. Candidate metadata records `geometry_basis=object_footprints_plus_affordance_zone_rects`, `affordance_zone_ids`, and `spacing_side_margins` for traceability. Facing margins are capped by neighboring candidate gaps, repeated groups with at least four footprints are capped by internal member spacing, clamped to scene bounds, and rejected when they reduce IoU against a matching explicit region, so candidate gap paths remain measurable. `affordance_expanded_group_bounds` is the narrower footprint+affordance baseline. This is candidate region evidence, not alpha-shape clustering, semantic region discovery, arbitrary-angle posture inference, or perception-calibrated grouping.
- `inferred_region_explicit_iou_mean` uses `affordance_expanded_candidate_region_to_explicit_region_iou`: it compares affordance-expanded candidate region bboxes with matching explicit region records so automatic inference can be checked against current hand-authored marks. Its evidence decomposes low overlap into candidate underfill versus candidate overflow by area and carries boundary-cue presence for the candidate. This is an overlap audit, not semantic validation or a final region-discovery score.
- `inferred_region_gap_path_count` uses `affordance_region_bbox_axis_gap_band_proxy`: directly adjacent inferred region candidates with a shared x/y projection and positive bbox gap produce a thick axis-aligned candidate path band with thickness and overlap-span evidence, even when explicit region records already exist. Candidate pairs are filtered out when the proposed gap band intersects a third candidate region, preventing cross-region shortcuts from being reported as direct roads. This is the first "regions leave a road between them" proxy, not a navmesh, medial axis, route certification, or final split/merge classifier.
- `inferred_region_gap_path_graph` uses `inferred_gap_path_region_adjacency_graph_proxy`: inferred region candidates become nodes and directly adjacent thick gap bands become edges. Each edge reuses the gap-band occupancy and free-space-overlap evidence (`clear_status`, `occupancy_ratio`, `free_space_overlap_ratio`), and the graph exposes node, edge, clear-edge, occupied-edge, free-space-supported-edge, `walkable_proxy_edge_count`, `walkable_proxy_edges`, `walkable_proxy_component_count`, `walkable_proxy_components`, `walkable_proxy_min_thickness`, `walkable_proxy_mean_thickness`, `walkable_proxy_edge_widths`, and component counts plus component membership for route-topology handoff. When Shapely room-minus-blocker overlap evidence exists, graph edges also carry `cad_free_space_overlap_ratio` and the graph/handoff expose `cad_free_space_supported_edge_count` plus `cad_free_space_supported_edges`. A walkable proxy edge means the inferred thick band is currently clear and overlaps the free-space proxy; this is a graph summary over bbox gap bands, not a route solver, navmesh, medial-axis skeleton, or walkability proof.
- `inferred_region_gap_path_walkable_proxy_ratio` uses `clear_and_free_space_supported_inferred_gap_path_edges`: the path-connectivity row scores clear, free-space-supported inferred gap edges over all inferred gap edges and carries the resulting edge/component/width evidence. `walkable_proxy_edge_widths` records each usable thick band with `thickness` and `overlap_span`, while `walkable_proxy_min_thickness` and `walkable_proxy_mean_thickness` summarize the current bottleneck and average gap-band width. This is the current handoff-friendly proxy for "regions have road-like separations between them", not a shortest path, route quality score, minimum-width proof, or final walkability certification.
- `inferred_gap_path_width_free_space_clearance_ratio` uses `free_space_edge_clearance_width_over_inferred_gap_band_width`: compare the existing rect-cell free-space graph mean shared-edge clearance width against inferred walkable gap-band mean thickness. Values below 1 flag that bbox gap bands are wider than the current free-space clearance proxy. This is a proxy consistency check, not route certification, code-compliant width, or medial-axis clearance.
- `inferred_region_gap_path_min_width_pass_ratio` uses `walkable_gap_band_thickness_over_manual_required_path_width` when `scene.settings.required_path_width` is authored: walkable inferred gap bands pass when their bbox thickness is at least the manually supplied required passage width. Without that setting it falls back to `walkable_gap_band_thickness_over_half_sampled_grid_resolution`. The row and `route_topology_handoff.inferred_gap_path_graph` expose `minimum_width_basis`, `minimum_width_evidence`, `width_pass_edges`, and `width_fail_edges`. This compares inferred actual gap thickness against a user-set demand width; it does not infer wheel/chair/body clearance demand from the SVG, and it is not code-compliant egress width, BIM-unit calibration, navmesh clearance, or a final circulation capacity model.
- `inferred_region_gap_path_occupancy_ratio` uses `inferred_gap_band_overlap_with_object_footprints_and_affordance_zones`: inferred thick gap bands are checked against non-source object footprints and affordance use zones, reporting occupied area, occupancy ratio, occupier ids, SVG overlay layer `inferred-gap-path-occupancy`, gap-path rectangle attributes `data-occupied` / `data-occupancy-ratio` / `data-clear-status`, and adapter gap-path item summaries (`occupied`, `occupancy_ratio`, `occupied_area`, `clear_status`). This prevents "gap exists" from being read as "path is clear", but it is still bbox overlap accounting, not CAD union, navmesh clearance, or route certification.
- `inferred_region_gap_path_free_space_overlap_ratio` uses `inferred_gap_band_overlap_with_rect_cell_free_space_polygons`: inferred thick gap bands are checked against the current rect-cell free-space polygons, reporting overlap area, ratio, and overlapped cell ids; adapter evidence also exposes `adapter_payload.evidence_geometry.inferred_region_gap_path_free_space_overlap` and per-gap-path `free_space_overlap_ratio`. This says whether the inferred band is consistent with the current free-space proxy, not whether a real route is certified.
- `inferred_region_gap_path_cad_free_space_overlap_ratio` uses `inferred_gap_band_overlap_with_shapely_room_minus_blocker_polygons`: inferred thick gap bands are checked against Shapely room-minus-blocker free-space polygons, reporting CAD free-space overlap area, ratio, and component ids; adapter evidence also exposes `adapter_payload.evidence_geometry.inferred_region_gap_path_cad_free_space_overlap`, per-gap-path `cad_free_space_overlap_ratio`, and graph-level `cad_free_space_supported_edge_count` / `cad_free_space_supported_edges`. This is stronger than the rect-cell overlap proxy, but still not navmesh route certification or hosted BIM topology.
- `inferred_region_gap_path_explicit_path_iou_mean` uses `affordance_gap_band_to_explicit_path_bbox_iou`: each inferred gap band is compared with its best matching authored path bbox by IoU, so the current hand-authored path layer can be used as a regression target for automatic route-space inference. A broad authored path rectangle can give higher IoU to overlarge shortcut bands, so this row is an overlap audit, not route validation, shortest-path evidence, navmesh alignment, or a monotonic success score.
- `object_region_membership_coverage` checks authored object-region metadata against measurable explicit or inferred region geometry by object footprint overlap share. It is a metadata/geometry consistency row, not fuzzy membership inference or final semantic region discovery.
- `object_region_assignment_coverage` separately reports how many object records have a matching explicit or inferred region record, so a high geometry-overlap score is not mistaken for complete authored region metadata.
- Regions with `data-analysis-region="false"` remain valid metadata targets for object-region coverage, but are filtered out of analytical region, column-bay, path, sampled, and negative-space region metrics so fallback room/misc catch-all regions do not dominate the matrix.
- `region_column_bay_fit` builds simple bay strips between adjacent same-direction authored column axes: axis-aligned strips for horizontal/vertical axes and four-point polygons for paired parallel slanted axes. It scores region bbox overlap share as a first continuous region-to-bay proxy, and `column_grid_handoff.region_bays.items` now carries the per-region bay evidence for adapter consumers, not only aggregate counts. This is not full structural grid topology, multi-axis bay decomposition, or irregular grid interpolation.
- `object_column_bay_local_position_coverage` computes each object center's affine `(local_u, local_v)` in the nearest authored adjacent column bay and scores whether both coordinates lie inside `[0, 1]`. `column_grid_handoff.object_bay_local_positions.items` carries those per-object local coordinates for downstream grid adapters. It is a local-frame containment proxy, not full irregular grid interpolation, bay topology validation, or structural column-cell reasoning.
- Future negative-space work can compare polygon-derived results against this sampled debug layer, but should not be constrained by it.

### Isovist And Visibility Graph Analysis

Sources:

- Benedikt, "To Take Hold of Space: Isovists and Isovist Fields": https://journals.sagepub.com/doi/10.1068/b060047
- Turner, Doxa, O'Sullivan, Penn, "From Isovists to Visibility Graphs": https://journals.sagepub.com/doi/10.1068/b2684
- UCL PDF copy: https://discovery.ucl.ac.uk/id/eprint/160/1/turner-doxa-osullivan-penn-2001.pdf
- depthmapX official page: https://spacegroupucl.github.io/depthmapX/

Decision:

Isovists and Visibility Graph Analysis are relevant to seeing, visual accessibility, and spatial centrality. They are not the same thing as walkability and they are not furniture order metrics.

Implementation consequence:

- Split future graph families into `walk_graph` and `visibility_graph`.
- Keep current `matrix["graph"]` named and documented as touch evidence.
- Do not claim shortest path, detour, loops, or visibility until those graph edges are generated from geometry and boundary weights.

### Skeleton, Medial Axis, And Voronoi

Sources:

- CGAL 2D Straight Skeleton and Polygon Offsetting: https://doc.cgal.org/latest/Straight_skeleton_2/index.html
- scikit-image skeletonization example: https://scikit-image.org/docs/0.25.x/auto_examples/edges/plot_skeleton.html
- Shapely Voronoi polygons: https://shapely.readthedocs.io/en/latest/reference/shapely.voronoi_polygons.html

Decision:

These are plausible methods for deriving path centerlines or clearance graphs from negative space, but they require a more precise geometry substrate than the current bbox fixture. Adding them now would create dependency and validation debt.

Implementation consequence:

- Next graph slice should first build explicit negative-space polygons.
- Only after that, choose one centerline method and test it against fixture variants.
- Continue using bbox-touch graph evidence only as a traceability proxy.

### Perceptual Grouping And Boundary Cues

Sources:

- Wagemans et al., "A Century of Gestalt Psychology in Visual Perception I": https://pubmed.ncbi.nlm.nih.gov/22845751/
- Palmer and Rock, "Rethinking perceptual organization: The role of uniform connectedness": https://link.springer.com/article/10.3758/BF03200760

Decision:

Gestalt grouping and uniform connectedness support why rugs, material continuity, color fields, and surface cues can create region identity without blocking walking or sight. They do not provide a universal numeric boundary weight for this project.

Implementation consequence:

- Keep `grouping_strength`, `walk_block`, and `see_block` separate.
- Track `walk_see_block_gap_mean` as an authored boundary-channel split, not as a calibrated perceptual transparency score.
- Track `non_blocking_grouping_cue_mean` as an authored non-blocking grouping cue, not as proof that a rug/material/color field creates a perceived region.
- Track `boundary_weight_metadata_coverage` with `records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records` so downstream review can distinguish explicitly authored boundary/opening weights from defaults. This is calibration readiness only, not material calibration, perception validation, or BIM material mapping.
- Track `entry_width_mean` with `opening_width_metadata_or_rect_max_dimension_mean`: prefer `opening-width`, `opening_width`, or `width` metadata, otherwise fall back to the opening rectangle max dimension, and record `width_source` as `opening_width_metadata` or `opening_bbox_max_dimension`.
- Track `boundary_thickness_mean` from authored `data-thickness`; do not infer architectural thickness from SVG stroke width.
- Track `adapter_reference_coverage` from normalized `adapter_refs` (`rhino_guid`, `ifc_guid`, `visualarq_id`, `source_layer`, `source_id`) so SVG prototype records can be audited for Rhino/VisualARQ/BIM traceability. Keep `adapter_reference_role_coverage` to show which record roles still lack external references. This is not hosted topology, BIM family validation, or a live model link.
- Export `score_matrix` with `computed_unit_interval_metric_mean_by_view_id`: computed scalar metric rows whose scores are already in `[0, 1]` are grouped by `view_id`, counts/unavailable rows are excluded, and `overall_score` is the unweighted mean of dimension scores. This is a compact score summary for review and adapters, not a calibrated weighting model or final decision rubric.
- Export `adapter_payload` with `neutral_adapter_payload_export`: flatten neutral scene records to id/role/group/region/bbox/`adapter_refs` and non-empty `metadata`, add reverse `external_refs`, include `handoff_contract` id/version metadata, include `evidence_geometry` summaries for inferred candidate regions/gap paths, inferred gap-path occupancy, inferred gap-path free-space overlap, proxy free-space polygons, `free_space_polygon_graph`, rect-cell room-minus-blocker boundary loops, Shapely `cad_room_minus_blocker_polygons`, `cad_room_minus_blocker_component_touch_evidence`, `cad_room_minus_blocker_component_graph`, and negative-space graph nodes/edges, include compact `graph_namespaces.walk_graph` / `graph_namespaces.visibility_graph` summaries, include DataTree-like `grasshopper_branches` branch indexes, include per-record `adapter_targets`, include `host_relationships` from entry-boundary host metadata or nearest-geometry fallback, include compact `route_topology_handoff` counts and `route_topology_handoff.cad_component_graph.items` / `route_topology_handoff.free_space_polygon_graph.items` for the CAD component graph, rect-cell graph, inferred gap-path clear/occupied proxies, and hosted/fallback entries, include `visual_analysis_handoff` summaries and `visual_analysis_handoff.visibility_graph.items` / `visual_analysis_handoff.isovist_radial_proxy.ray_items` / `visual_analysis_handoff.isovist_radial_proxy.area_items` from existing centerline visibility and radial isovist proxy metrics, include `material_calibration_handoff` summaries from authored boundary weights, thickness metadata, and glass/rug/material/visual calibration candidates, include `column_grid_handoff` summaries and `column_grid_handoff.region_bays.items` / `column_grid_handoff.object_bay_local_positions.items` from existing column-axis, object-phase, region-bay, and object-local-position proxy rows, include `adapter_capability_matrix` as a readiness index over current handoff surfaces plus uncertainty-route counts, include `adapter_readiness.matrix_completion_audit` with method `completion_gate_from_current_metric_family_status` so implemented/prototype/deferred metric families remain machine-readable, include `notebook_audit_manifest` to expose the ordered clean-overlay notebook display policy, and include compact metric row summaries. `export_adapter_payload_json(scene, target)` serializes this neutral payload to stable UTF-8 JSON for downstream adapter checks; `validate_adapter_payload_json(target)` gives a lightweight required-key and summary check for that exported file, including missing or unsupported contract metadata, missing Grasshopper branch table, missing Grasshopper record/metric/graph branch groups, empty or incomplete `ready_handoffs`, record-count mismatches, duplicate scene record ids, orphan `external_refs` targets, missing or stale reverse adapter refs, and non-ordered notebook status errors. Boundary target hints distinguish authored `glass`, `rug`, `material`, and `visual` boundary kinds from generic wall targets. This is an adapter handoff contract and file export for Rhino/Grasshopper/VisualARQ/BIM wrappers, not live document topology, Grasshopper DataTree execution, VisualARQ object hosting, BIM family validation, material assignment, navmesh topology, medial-axis routing, route certification, full isovist polygons, Visibility Graph Analysis fields, calibrated visual integration, material/perception calibration, irregular structural grid interpolation, proof of live adapter execution, plugin execution, model synchronization, or visual QA of the notebook rendering.
- Attach the same opening width and nearest-boundary association evidence to `entry_touch_ratio` so connectivity rows can explain which openings connect to the current path proxy and which boundary each opening belongs to.
- Track `disconnected_entry_ratio` as the share of openings with no path touch in the current proxy graph; this is a direct warning row for authored openings not connected to candidate circulation, not hosted doorway topology or route certification.
- Track `disconnected_path_ratio` as the share of authored path polygons with no entry touch in the current proxy graph; this catches floating candidate circulation before any navmesh or negative-space graph exists.
- Track `sampled_min_clearance_to_walk_blocker` with `sampled_free_cell_center_to_nearest_walk_blocker_gap`: for every sampled free domain cell, measure cell-center distance to the nearest walk blocker and report the bottleneck clearance. Keep `zero_clearance_sample_count` and `min_clearance_samples` so zero or near-zero scores remain inspectable. This is not medial-axis width field or navmesh clearance.
- Track `sampled_zero_clearance_cell_ratio` with `sampled_zero_clearance_cells_over_clearance_samples` as an occupancy-threshold disagreement warning: sampled cells counted free by coverage threshold can still have center-point zero clearance to blocker geometry.
- Track `sampled_entry_reachable_min_clearance_to_walk_blocker` with `sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap`; it reuses the same sampled BFS entry-reachable cells so unreachable free-space pockets do not inflate the reported circulation bottleneck.
- Track `sampled_mean_entry_region_widest_clearance` with `sampled_grid_widest_path_clearance_proxy`; this runs a max-min clearance search over sampled grid cells from entries to regions, giving a route-capacity proxy without claiming medial-axis width field or navmesh routing. Each evidence item includes `path_cells` from `sampled_widest_path_cell_evidence`, reconstructed by replaying the sampled predecessor chain for the selected max-min target cell; long routes are capped at 32 cells with `path_truncated`.
- Track `sampled_mean_entry_region_clearance_per_distance` with `sampled_widest_clearance_over_entry_region_distance_proxy`; this normalizes sampled widest clearance by sampled entry-region distance as a compact route-capacity-density proxy, not code-compliant egress capacity.
- Track `opening_width_room_perimeter_ratio` as a continuous boundary-opening descriptor; current denominator is room-boundary bbox perimeter, not true irregular-wall length.
- Track `opening_width_room_boundary_length_ratio` against parsed room-boundary polyline length; curved walls still need curve-aware length.
- Track `entry_boundary_position_coverage` as entry-center projections on parsed room-boundary polyline; Rhino/BIM should replace this with curve parameters on hosted openings.
- Track `entry_nearest_boundary_gap_mean` as opening-center association to the nearest authored boundary geometry; Rhino/BIM should replace this with hosted opening topology.
- Track `hosted_entry_boundary_ratio` as the share of openings whose boundary association comes from explicit host metadata. `host-boundary`, `host_boundary`, or `host` is preferred when present; nearest-geometry association remains the SVG fallback. This is a neutral adapter contract, not automatic hosted topology.
- Track `fallback_entry_boundary_ratio` as the share of openings whose boundary association still uses nearest authored geometry. This is an adapter-readiness audit for SVG/prototype inputs, not a hosted-door validation.
- Track `boundary_opening_width_ratio_max` as the largest per-boundary sum of associated opening widths divided by parsed boundary length; this is local continuity evidence, not a pass/fail threshold.
- Track `boundary_path_connected_opening_ratio_max` as the largest per-boundary share of associated openings that touch the current path proxy; keep `path_disconnected_opening_ids` in the evidence so unconnected openings are explicit. This distinguishes opening presence from path-connected access without claiming route certification.
- Track `path_touched_region_boundary_cue_ratio` as the share of path-touched regions that also have same-region boundary proximity evidence; this is evidence for path split versus boundary grouping, not a split/merge decision.
- Track `boundary_cue_kinds` on path-region boundary evidence from authored `data-boundary-kind` metadata so rug, glass, material, and visual cues remain separate in downstream review.
- Track `path_touched_region_boundary_cue_count_mean` as the number of same-region boundary cue records attached to path-touched regions; this is traceability evidence and should not be interpreted as quality without continuity and calibration.
- Track `path_touched_region_boundary_cue_strength_mean` as the mean same-region boundary proximity over path-touched regions, with missing cues counted as zero; this is cue-strength evidence, not a calibrated grouping or region merge decision.
- Track `path_touched_region_boundary_grouping_strength_mean` as the length-weighted authored grouping strength of same-region boundary cues touching path-touched regions; this keeps the grouping channel separate from walk and visibility channels.
- Track `path_touched_region_boundary_walk_see_gap_mean` with separate length-weighted authored `walk_block` and `see_block` channels for path-touched same-region boundary cues; this is not isovist or material transparency simulation.
- Track `closed_blocking_boundary_ratio` as the share of authored boundaries with both `walk_block` and `see_block` at full block. This is a direct closed-wall/solid-partition descriptor, not wall topology, code compliance, or hosted BIM closure.
- Track `boundary_cue_profiles` on path-region boundary evidence so every aggregate cue row can be traced back to boundary id, kind, length, authored walk/see/grouping channels, and grouping influence.
- Track `path_touched_region_boundary_cue_perimeter_influence_mean` as same-region boundary cue influence normalized by region bbox perimeter; this keeps raw boundary length from dominating across differently scaled regions, but remains a bbox-scale proxy.
- Track `path_region_split_tendency_proxy` as `path_region_touch_ratio * path_width_continuity * (1 - boundary_grouping_strength)`; this is a continuous evidence row for split pressure, not an automatic split/merge classifier.
- Track `region_boundary_axis_agreement` as each region axis matched to its best boundary axis; this is continuous axis evidence, not a distance/containment/strength model.
- Track `region_source_boundary_axis_agreement` as each region axis matched only to same-`data-region` boundary axes; omit regions without scoped boundary metadata rather than inventing a score.
- Track `region_source_boundary_weighted_axis_agreement` with same-region boundary contributions weighted by parsed length times authored `grouping_strength`.
- Track `region_source_boundary_proximity` with same-region boundary bbox gaps normalized by region scale and weighted by parsed length times authored `grouping_strength`; Rhino/BIM should replace bbox gap with curve/polygon distance.
- Track `group_path_axis_agreement` as group bbox axes versus path polygon longest-edge axes; true route fields need negative-space centerlines or sampled tangent fields.
- Track `group_boundary_axis_agreement` as group bbox axes versus boundary axes; true boundary force needs weighting by continuity, thickness, walk/see block, and grouping strength.
- Track `weighted_boundary_axis_concentration` with mean authored walk/see/grouping weights; later replace or augment with perception-calibrated, length/thickness-aware weights.
- Parse SVG `<line>` boundary endpoints as points so straight visual/material/glass boundaries use `polygon_longest_edge` evidence instead of bbox-only axis fallback.
- Keep boundary/path polygon axes on `polygon_longest_edge`; the PCA axis upgrade is scoped to region records so slanted or irregular zones get a more stable local frame without weakening explicit segment direction cues.
- Track `length_weighted_boundary_axis_concentration` with boundary length times authored channel weight; curved length remains pending.
- Track `thickness_weighted_boundary_axis_concentration` with boundary length times authored thickness times authored channel weight; thickness is explicit metadata, not SVG stroke width, and still needs BIM/object calibration.
- Treat rug/material/color weights as authored or experimentally calibrated.
- Do not turn grouping cues into hard region-split thresholds.

### Rhino, Grasshopper, And VisualARQ

Sources:

- RhinoCommon API: https://developer.rhino3d.com/api/RhinoCommon/
- Rhino.Geometry namespace: https://developer.rhino3d.com/api/rhinocommon/rhino.geometry
- Grasshopper `DataTree<T>`: https://developer.rhino3d.com/api/grasshopper/html/T_Grasshopper_DataTree_1.htm
- Grasshopper `DataTree<T>.Add`: https://developer.rhino3d.com/api/grasshopper/html/M_Grasshopper_DataTree_1_Add_1.htm
- VisualARQ features: https://www.visualarq.com/features/
- VisualARQ API note: https://www.visualarq.com/support/tip/is-there-an-api-or-sdk-for-visualarq/

Decision:

Rhino, Grasshopper, and VisualARQ should be import/export adapters around the neutral scene. VisualARQ's API is document-object oriented, while Grasshopper often works with temporary in-memory geometry, so the evaluator should not depend directly on VisualARQ objects.

Implementation consequence:

- Keep metric functions pure Python over neutral records.
- Current evaluator returns a neutral `adapter_payload` with `evidence_geometry`; future plugins should consume or produce that payload rather than binding metric code to Rhino/Grasshopper/VisualARQ APIs.
- Future Rhino adapter maps curves, breps, points, walls, doors, columns, rooms, and furniture into scene records.
- Future Grasshopper component returns metric rows and evidence geometry through DataTree-like branches.

## Next Method Gate

Before replacing the current path proxy, the next implementation slice must pass this gate:

1. Build or import walkable negative-space polygons.
2. Attach boundary `walk_block` and `see_block` to candidate edges.
3. Produce two graph namespaces: `walk_graph` and `visibility_graph`.
4. Add fixture cases for glass, rug, closed wall, opening, and disconnected path.
5. Only then compute shortest path, detour ratio, dead ends, loops, and width continuity.
