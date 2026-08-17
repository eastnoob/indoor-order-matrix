# Indoor Layout Evaluation Matrix Task Status

## Source Of Truth

- Original prompt: `docs/indoor_layout_evaluation_matrix_original_prompt.md`
- Main spec target: `docs/indoor_layout_evaluation_matrix_spec.md`
- Current 2D fixture: `test/floorplan_order_fixture.svg`
- Notebook test plan: `docs/indoor_layout_evaluation_matrix_notebook_test_plan.md`
- Executable notebook fixture: `test/floorplan_order_matrix_demo.ipynb`
- Prompt coverage audit: `docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md`
- Method decision ledger: `docs/indoor_layout_evaluation_matrix_method_ledger.md`

## Current Index

- VCS: use `jj`; keep working-copy changes clean before moving `master`.
- Mainline rule: merge stable feature/fix changes often; keep `experiment:` and
  `backup-` changes out of `master` until they become a formal feature/fix.
- Stable latest change: `fix: prevent two-point position self-inference`.
- Position grammar default: two furniture groups do not self-infer a scoring
  frame from their own connecting line; demos may opt in explicitly.
- SVG/BIM boundary: SVG remains a proxy input; matrix scoring reads neutral
  furniture-group and authored metadata, not raw drawing intent.
- Furniture grouping: explicit `data-furniture-group` is the canonical test
  stand-in for BIM furniture-group semantics.
- Current visual demo rule: default demo cells show real strict behavior;
  explicit opt-in cells are marked as debug comparisons.
- Current next likely work: keep tightening public metrics around explicit
  semantic objects before adding broader BIM/Rhino plugin plumbing.
- Current saved feature change: `feat: add room analysis model foundation`.
- Current follow-up fix: reconciles SVG fixture semantics with the full suite by
  ignoring furniture-group container ids as furniture, preserving plain vertical
  rect orientation, and feeding all furniture groups into inferred-region trend
  metadata.
- RoomAnalysisModel status: focused tests, notebook execution, and full pytest
  are green; the feature is ready for jj integration after review.

## Goal Requirements

- [x] Preserve the full original task prompt as Markdown before writing the spec.
- [ ] Deliver `docs/indoor_layout_evaluation_matrix_spec.md` at full task depth.
- [ ] Include a 2D fixture / notebook test plan detailed enough to implement directly.
- [ ] Include a next implementation plan with concrete slices and acceptance checks.
- [ ] Keep the document technical and operational, not academic-paper style.
- [ ] Tie the proposal to the current `order_analyzer` / OCTA codebase with concrete code touchpoints.
- [ ] Preserve a Rhino / Grasshopper / VisualARQ / BIM migration path with object mappings.
- [ ] Review against the original prompt before claiming completion.

## Current Task State

2026-07-20, RoomAnalysisModel foundation pass:

- Added a static `RoomAnalysisModel` export at
  `evaluate_scene(scene)["room_analysis_model"]`.
- The model organizes existing outputs into:
  - `base_layer`;
  - `object_layer`;
  - `region_layer`;
  - `network_layer`;
  - `reference_layer`;
  - `metric_layer`;
  - `summary_layer`.
- Added `features/room_analysis_model.py` as a model builder that adapts current
  neutral scene and matrix rows without moving working region, trend, position,
  path, boundary, or column-grid algorithms.
- Added concise interface and development-standard notes:
  - `docs/room_analysis_model_interface.md`;
  - `docs/room_analysis_model_development_standard.md`.
- Added notebook demo:
  - `test/room_analysis_model_demo.ipynb`;
  - executed output at `test/output/room_analysis_model_demo.executed.ipynb`.
- Verification:
  - focused RoomAnalysisModel pytest checks: `6 passed`;
  - notebook execution: passed through `nbclient`;
  - full pytest after follow-up fix: `284 passed`.
- Merge boundary:
  - fixture/test drift has been reconciled in the follow-up jj change; merge can
    proceed after normal review.

2026-07-09, member-frame trend ground truth pass:

- Split trend and shape evidence:
  - `group-axis-angle` / `group-axis-strength` now come from member furniture frame consensus when directional member evidence exists;
  - geometry PCA is retained as `group-axis-geometry-angle` and shape diagnostics;
  - region polygons, affordance extents, and gap paths are unchanged.
- This makes directionality independent of furniture count:
  - a single clear directional table can have strong trend strength;
  - chaotic multi-member layouts still weaken through circular frame dispersion.
- Safety boundary:
  - no new angle thresholds;
  - no global switch to true-points PCA;
  - no change to path/region shape generation.

2026-07-09, region frame extent consistency fix:

- Fixed a trend overlay bug where a normalized final frame angle could keep stale PCA `axis-primary-extent` / `axis-secondary-extent`.
- Scope is intentionally narrow:
  - angle and strength algorithms are unchanged;
  - only final-frame extent metadata is recomputed after correction/normalization;
  - SVG remains an input proxy and notebook drawing still uses `extent * 0.65 * strength`.
- Regression:
  - `SVG_chaoticsvg.svg` `north_tables` now has final `axis-angle=86.2722`, `primary=495.1`, `secondary=830.0`;
  - the prior stale metadata had the long horizontal extent bound to the near-vertical primary axis.
- Verification:
  - focused frame tests: passed;
  - `pixi run pytest -q`: `231 passed in 54.63s`;
  - executed notebook saved to `test/output/svg_id_inference_demo.executed.ipynb`;
  - visual QA saved to `test/output/svg_id_inference_demo.visual.html` and `test/output/svg_id_inference_demo.visual.png`.

2026-07-09, region trend explainability correction pass:

- Selected the explainability-first orthogonal frame rule for inferred region trend cleanup.
- The rule compares the current region frame with the nearest 0/90-equivalent frame and corrects only when the orthogonal frame:
  - keeps the projection envelope no larger;
  - explains member furniture frames at least as well;
  - has non-zero member-frame support;
  - improves at least one of envelope area or member alignment.
- This is not a hard small-angle threshold and does not revive broad region-shape candidate selection.
- Metadata now keeps audit evidence:
  - `axis-original-angle`;
  - `axis-explainability-correction`;
  - `frame-pca-area`;
  - `frame-orthogonal-area`;
  - `frame-pca-member-alignment`;
  - `frame-orthogonal-member-alignment`;
  - `frame-snap-candidate`.
- SVG probe result:
  - `SVG_oblique.svg` `center_lounge` corrects from `6.5528` to `0.0`;
  - `SVG_chaoticsvg.svg` `center_lounge` remains `85.0265` and is not corrected;
  - `SVG_oblique.svg` `west_lounge` remains `17.9849`;
  - `SVG_oblique.svg` `north_tables` remains `84.017`.
- Verification:
  - `pixi run pytest test/test_floorplan_scene_loader.py::test_region_frame_explainability_selects_only_better_orthogonal_frames -q`: passed;
  - `pixi run pytest -q`: `230 passed`;
  - executed notebook saved to `test/output/svg_id_inference_demo.executed.ipynb`;
  - visual QA saved to `test/output/svg_id_inference_demo.visual.html` and `test/output/svg_id_inference_demo.visual.png`.
- Important boundary:
  - the correction belongs to inference trend/frame metadata;
  - SVG remains a neutral proxy input;
  - region polygon/shape selection is intentionally left on the existing conservative path.

2026-07-08, layout hierarchy/network/boundary skeleton pass:

- Added focused spec: `docs/superpowers/specs/2026-07-08-layout-hierarchy-network-boundary-skeleton-design.md`.
- Added implementation plan: `docs/superpowers/plans/2026-07-08-layout-hierarchy-network-boundary-skeleton.md`.
- Added first-class `activity_groups` inference evidence:
  - grouped by semantic region key;
  - group bbox is the union envelope of member furniture affordance extents;
  - pairwise overlap is kept as relation/conflict/common-use evidence, not as the group extent definition.
- Added shared-schema `spatial_networks` evidence:
  - `region_internal` networks describe member extent relationships inside activity groups;
  - `inter_region` network describes inferred gap-path connectivity between activity region candidates;
  - both scopes expose the same keys: `id`, `scope`, `nodes`, `edges`, `components`, and `metadata`.
- Added `boundary_semantics` evidence from authored boundary weights and metadata:
  - `walk_passable`;
  - `see_passable`;
  - `thickness`;
  - `grouping_strength`;
  - `opening_ids`;
  - `surface_identity`.
- `evaluate_scene(scene)` now exposes `activity_groups`, `spatial_networks`, and `boundary_semantics` at top level and under `adapter_payload.evidence_geometry`.
- Added plain-dict regression tests that do not depend on SVG parsing, confirming the new skeletons belong to the inference/matrix layer rather than the SVG adapter.
- Current verification: `pixi run pytest -q` reports `210 passed in 51.68s`.
- Important boundary:
  - this is an architecture skeleton and evidence contract;
  - it does not add BIM/Rhino execution, polygon boolean group extents, navmesh routing, full visual analysis, or calibrated boundary/material scoring.

2026-07-07, SVG/base-map and matrix separation pass:

- Added `docs/indoor_layout_evaluation_matrix_architecture_memory.md`.
- Architecture boundary: SVG is a neutral BIM proxy/base map; SVG does not define the evaluation matrix.
- User-authored semantic attributes are the primary input; bbox, rect-cell, or geometric fallback algorithms are secondary stand-ins used only when explicit attributes are missing or insufficient for computation.
- Added `features/scene_inference.py` as the Inference / Evidence Layer for affordance zones, inferred region candidates, inferred regions, inferred region gap paths, and inferred gap-path graph evidence.
- `evaluate_scene(scene)` now calls `infer_scene_evidence(scene)` and the matrix consumes neutral scene plus inference evidence before producing rows, overlays, and adapter payloads.
- Important boundary:
  - `scene_loader.py` remains the SVG-to-Neutral Scene adapter;
  - `scene_inference.py` owns derived region/path evidence;
  - `scene_evaluator.py` owns Evaluation Matrix rows and should not depend on SVG-specific rendering or XML traversal.
- Code comment rule recorded in architecture memory:
  - every function should have a docstring;
  - important computation steps should have English comments explaining intent, especially inference, scoring, geometry conversion, graph construction, and adapter handoff logic.
  - scope: all new or modified project-owned code; vendored OCTA toolbox code is exempt unless it is edited.

2026-07-07, affordance-expanded inferred region pass:

- Added automatic candidate region inference for objects whose `region` key has no explicit region record.
- The inferred region bbox is built from member furniture footprints plus per-object affordance metadata:
  - `affordance-left`;
  - `affordance-right`;
  - `affordance-top`;
  - `affordance-bottom`.
- When no explicit per-side affordance metadata is present, inferred regions can fall back to the existing affordance profile resolver; current tested behavior uses `chair.default` and `podium.default` front-side use zones, while `armchair.default` adds a small four-side personal-use zone and explicit per-side metadata remains the override path.
- Same-region boundary cues with positive `grouping_strength` now also expand inferred region bounds, so rugs/material/glass outline cues can participate in the automatic region envelope.
- No-boundary-cue candidate regions now get a small spacing-derived margin only when at least two candidate regions exist; facing sides are capped by nearby candidate gaps and the result is clamped to scene bounds so inferred paths keep measurable thickness.
- Candidate metadata, matrix evidence, and adapter payload now expose `spacing_side_margins`, so each inferred region shows which side was expanded by spacing evidence.
- Repeated groups with at least four member footprints cap their no-cue spacing margin by internal member gaps, preventing large furniture arrays from expanding by the whole group bbox scale.
- If a matching explicit region exists, spacing margin is accepted only when it does not reduce candidate-to-explicit IoU, so margin expansion cannot make an already-better candidate worse against current authored marks.
- Added `matrix["inferred_regions"]`.
- Added `matrix["inferred_region_candidates"]` for explicit-region overlap checks without adding those candidates to analysis regions.
- Added `matrix["affordance_zones"]` as explicit use-zone records adjacent to object footprints, so furniture footprint space and usable/occupied affordance space can be audited separately.
- Added `region_alignment.affordance_use_zone_count` with method `object_footprint_adjacent_affordance_rect_zones`.
- Added `matrix["furniture_affordance_extents"]` and `region_alignment.furniture_affordance_extent_count` with method `object_footprint_plus_own_affordance_zone_extent`, so every furniture object has one maximum bbox envelope from its footprint plus its own affordance zones before grouped activity-region inference.
- Inferred region metadata now records `geometry_basis=object_footprints_plus_affordance_zone_rects` and `affordance_zone_ids`, so region candidates can be traced back to separate furniture footprints and use-zone entities.
- Added `region_alignment.inferred_region_candidate_count` with method `affordance_zone_boundary_cue_expanded_group_candidate_bounds`, so automatic region candidates remain visible even when matching explicit region records already exist.
- Added `region_alignment.inferred_region_count` with method `affordance_zone_boundary_cue_expanded_group_bounds` (the previous `affordance_expanded_group_bounds` keyword remains the narrower footprint+affordance baseline).
- Added `region_alignment.inferred_region_explicit_iou_mean` with method `affordance_expanded_candidate_region_to_explicit_region_iou`.
- The explicit-region IoU evidence now also records candidate area, explicit area, missing explicit area, overflow candidate area, and `dominant_mismatch`, so low overlap can be read as underfill versus overflow instead of a single opaque score.
- The same IoU evidence records `candidate_boundary_cue_ids` and `candidate_has_boundary_cue`, so remaining underfilled regions can be separated into "no authored cue yet" versus "cue exists but still misfits".
- Object-region membership now checks explicit plus inferred regions, so a labeled furniture group can be evaluated without a hand-authored region rectangle.
- Added `region_alignment.inferred_region_gap_path_count` with method `affordance_region_bbox_axis_gap_band_proxy`.
- The gap-path row records axis-aligned thick bands between directly adjacent inferred candidate region bboxes when the candidates have a shared projection and a positive gap. A candidate pair is filtered out when the proposed gap band intersects a third candidate region, so the row no longer reports long cross-region shortcuts as direct paths. This remains available even when explicit region records already exist and no inferred region needs to be added to analysis.
- Added `matrix["inferred_region_gap_path_graph"]` and `route_topology_handoff.inferred_gap_path_graph` with method `inferred_gap_path_region_adjacency_graph_proxy`, so adjacent thick gap bands are also available as a region adjacency graph. Graph edges now carry `clear_status`, `occupancy_ratio`, and `free_space_overlap_ratio`; graph summaries expose clear, occupied, free-space-supported, `walkable_proxy_edge_count`, `walkable_proxy_edges`, `walkable_proxy_component_count`, `walkable_proxy_components`, `walkable_proxy_min_thickness`, `walkable_proxy_mean_thickness`, and `walkable_proxy_edge_widths`. When Shapely room-minus-blocker overlap evidence exists, graph edges also carry `cad_free_space_overlap_ratio`, and graph/handoff summaries expose `cad_free_space_supported_edge_count` and `cad_free_space_supported_edges`. `walkable_proxy_edges` lists the candidate thick bands that are both clear and supported by the current free-space proxy, `walkable_proxy_components` reports region connectivity using only those usable proxy edges, and the thickness fields expose current gap-band width evidence without certifying minimum passage width.
- Current fixture now has `7` adjacent inferred gap-path bands after the intermediate-region filter; its inferred gap-path graph has `6` nodes, `7` edges, `6` clear edges, `1` occupied edge, `7` free-space-supported edges, `6` walkable-proxy edges, `1` geometric component, and `1` walkable-proxy component. The fixture `inferred_region_gap_path_occupancy_ratio` is `0.0116`, `inferred_region_gap_path_free_space_overlap_ratio` is `0.9884`, and `inferred_region_gap_path_walkable_proxy_ratio` is `0.8571`. The authored `path_placeholder` remains a very broad reference rectangle, so `inferred_region_gap_path_explicit_path_iou_mean` is an audit signal rather than a monotonic success score.
- Added `path_connectivity.inferred_region_gap_path_walkable_proxy_ratio` with method `clear_and_free_space_supported_inferred_gap_path_edges`, so the matrix exposes a compact score and evidence list for usable inferred thick path bands.
- Added `path_connectivity.inferred_gap_path_width_free_space_clearance_ratio` with method `free_space_edge_clearance_width_over_inferred_gap_band_width`, so inferred gap-band width can be checked against rect-cell free-space shared-edge clearance. Current fixture score is `0.4628`, which flags that bbox gap bands are wider than the free-space clearance proxy and should not yet be read as certified route width.
- Added `path_connectivity.inferred_region_gap_path_min_width_pass_ratio` with manual `scene.settings.required_path_width` support. When authored, the row uses `walkable_gap_band_thickness_over_manual_required_path_width` and compares inferred actual gap-band thickness against that user-set passage width; otherwise it falls back to `walkable_gap_band_thickness_over_half_sampled_grid_resolution`. `minimum_width_basis`, `minimum_width_evidence`, `width_pass_edges`, and `width_fail_edges` are also exported through `route_topology_handoff.inferred_gap_path_graph`. The evaluator does not infer wheel/chair/body demand width from the SVG; it only evaluates whether inferred gap bands meet the configured width.
- Added `region_alignment.inferred_region_gap_path_occupancy_ratio` with method `inferred_gap_band_overlap_with_object_footprints_and_affordance_zones`, so thick inferred path bands can report object/use-zone occupation instead of being treated as automatically clear roads.
- Added `adapter_payload.evidence_geometry.inferred_region_gap_path_occupancy` and SVG layer `inferred-gap-path-occupancy`; inferred gap-path adapter items and SVG rectangles also carry occupancy summaries (`occupied`, `occupancy_ratio`, `occupied_area`, `clear_status`, `data-occupied`, `data-occupancy-ratio`, `data-clear-status`), so handoff consumers and notebooks can inspect which object/use-zone occupies an inferred thick path band.
- Added `region_alignment.inferred_region_gap_path_free_space_overlap_ratio` with method `inferred_gap_band_overlap_with_rect_cell_free_space_polygons` plus `adapter_payload.evidence_geometry.inferred_region_gap_path_free_space_overlap`, so inferred thick bands can be checked against the current free-space proxy before downstream route adapters treat them as route candidates.
- Added `path_connectivity.inferred_region_gap_path_cad_free_space_overlap_ratio` with method `inferred_gap_band_overlap_with_shapely_room_minus_blocker_polygons` plus `adapter_payload.evidence_geometry.inferred_region_gap_path_cad_free_space_overlap`, so inferred thick bands can also be checked against Shapely room-minus-blocker free-space polygons instead of only rect-cell free-space proxies.
- Added `route_topology_handoff.inferred_gap_paths`, so downstream route adapters can receive inferred thick gap-path counts, clear/occupied proxy counts, and the same gap-path summary items without rejoining evidence geometry.
- Added `region_alignment.inferred_region_gap_path_explicit_path_iou_mean` with method `affordance_gap_band_to_explicit_path_bbox_iou`, so inferred thick gap bands can be checked against authored path rectangles.
- Added `adapter_payload.evidence_geometry.affordance_zones`, `adapter_payload.evidence_geometry.furniture_affordance_extents`, `adapter_payload.evidence_geometry.inferred_region_candidates`, and `adapter_payload.evidence_geometry.inferred_region_gap_paths`, so neutral payload consumers can inspect automatic use-zone/furniture-extent/region/path-band evidence without re-running private evaluator helpers.
- Added top-level and adapter-exported `score_matrix` with method `computed_unit_interval_metric_mean_by_view_id`, so computed `[0, 1]` metric rows are grouped into dimension scores plus an unweighted overall score while count/unavailable rows remain excluded until calibrated weights exist.
- Extended `scene_metric_overlay_svg()` with:
  - `affordance-use-zone`;
  - `furniture-affordance-extent`;
  - `inferred-region`;
  - `inferred-region-candidate`;
  - `inferred-gap-path`.
- Added SVG and synthetic-scene regressions covering:
  - structured SVG affordance metadata driving region inference;
  - inferred candidate region versus explicit region IoU;
  - inferred region overlay;
  - inferred candidate overlay when an explicit region record already exists;
  - inferred candidate gap paths when explicit region records already exist;
  - inferred candidate gap path versus explicit path bbox IoU;
  - adapter payload export of inferred candidate regions and gap paths;
  - default chair affordance profile fallback versus explicit affordance override;
  - oriented default chair affordance profile fallback;
  - default armchair affordance profile fallback;
  - default podium affordance profile fallback;
  - thick path/gap band inference between two affordance-expanded regions.
- Important boundary:
  - this is candidate region and candidate path-band evidence from bbox, affordance metadata, and authored same-region boundary cues;
  - it is not alpha-shape region discovery, semantic clustering, calibrated perception, navmesh routing, medial-axis extraction, or a Rhino/Grasshopper/BIM plugin.

2026-07-07, adapter payload JSON export pass:

- Added `export_adapter_payload_json(scene, target)`.
- The helper writes `matrix["adapter_payload"]` from `evaluate_scene(scene)` to a stable UTF-8 JSON file for downstream adapter handoff checks.
- Added `validate_adapter_payload_json(target)` as a lightweight file-level contract check for the exported handoff.
- Added `handoff_contract = {"id": "neutral_adapter_payload", "version": 1}` to exported payloads so downstream adapters can reject incompatible file shapes.
- Current regression writes the fixture payload and checks `source`, `record_count`, `adapter_capability_matrix.ready_handoffs`, and `notebook_audit_manifest.status`.
- Validation regression checks required payload keys, fixture record count, ready handoff count, and notebook audit status.
- Malformed-file regression rejects empty `adapter_capability_matrix.ready_handoffs` and a notebook status other than `ordered_clean_overlay`.
- Contract regression rejects any `handoff_contract` id/version other than `neutral_adapter_payload` version `1`.
- Readiness regression rejects payloads whose `adapter_capability_matrix.ready_handoffs` omit any current handoff surface.
- Count regression rejects payloads whose `record_count` does not match `scene_records` length.
- Identity regression rejects duplicate `scene_records` ids.
- External-ref regression rejects `external_refs` targets that do not point to exported `scene_records` ids.
- Reverse-ref regression rejects `scene_records.adapter_refs` that are missing from `external_refs`.
- Stale-ref regression rejects `external_refs` entries whose target record does not declare the same adapter ref value.
- Grasshopper regression treats `grasshopper_branches` as a required DataTree-like handoff table.
- Branch-group regression rejects `grasshopper_branches` that lack any of the current required record, metric, or graph branch groups.
- Important boundary:
  - this is a file handoff for the neutral adapter payload only;
  - it is not a live Rhino/Grasshopper/BIM plugin, Grasshopper DataTree execution, VisualARQ hosting, hosted topology, or model synchronization.

2026-07-07, notebook audit manifest pass:

- Added `matrix["adapter_payload"]["notebook_audit_manifest"]`.
- The manifest records the current executable notebook display policy:
  - section order: `1. Source Fixture`, `2. Evaluation Summary`, `3. Metric Matrix`, `4. Clean Evidence Overlay`, `5. Audit Snapshot`;
  - default overlay call: `scene_metric_overlay_svg(scene, matrix)`;
  - `include_free_space_paths = False` by default;
  - optional dense layer: `free-space-graph-entry-region-path`.
- This mirrors the existing notebook-order regression so downstream users can inspect the display policy from the evaluation payload as well as from the notebook file.
- Important boundary:
  - this is a notebook audit manifest only;
  - it is not visual QA for every rendered SVG layer, a polished presentation layout, or a substitute for running the notebook.

2026-07-07, adapter capability matrix pass:

- Added `matrix["adapter_payload"]["adapter_capability_matrix"]`.
- The payload now gives downstream adapter work one compact readiness index over current handoff surfaces:
  - `host_relationships`;
  - `route_topology_handoff`;
  - `visual_analysis_handoff`;
  - `material_calibration_handoff`;
  - `column_grid_handoff`.
- It also summarizes current uncertainty-route evidence counts for:
  - `geometry_upgrade`;
  - `perception_experiment`;
  - `bim_mapping`;
  - `method_replacement`.
- Current fixture:
  - all five handoff surfaces are present;
  - each uncertainty route currently exposes `8` capped evidence row ids.
- Important boundary:
  - this is a handoff readiness index only;
  - it does not prove live Rhino/GH/BIM adapter execution, hosted topology, validated CAD geometry, material calibration, full route analysis, or full visibility analysis.

2026-07-07, matrix completion audit gate pass:

- Added `adapter_readiness.matrix_completion_audit` with method `completion_gate_from_current_metric_family_status`.
- The row exposes `required_metric_family_status`, `open_core_families`, and `completion_ready` so final completion cannot be claimed only from broad passing tests or a dense notebook.
- Current open core families are:
  - `metric_matrix_rows`;
  - `route_topology`;
  - `visual_analysis`;
  - `column_grid`;
  - `material_boundary_calibration`.
- `live_bim_rhino_adapter` is marked `deferred_by_user_scope`, matching the user-approved scope that BIM/Rhino plugin execution can remain final-stage or incomplete.
- Important boundary:
  - this is a completion gate ledger inside the metric matrix;
  - it does not implement navmesh, full isovist/VGA, calibrated materials, or irregular grid interpolation.

2026-07-07, column-grid adapter handoff pass:

- Added `matrix["adapter_payload"]["column_grid_handoff"]`.
- The payload now gives downstream Rhino/BIM grid adapters one compact place to find:
  - authored column axis ids and region-axis agreement;
  - object-to-column-axis phase score and evidence count;
  - region-to-column-bay fit score, evidence count, and `column_grid_handoff.region_bays.items`;
  - object local affine position-in-bay score, evidence count, and `column_grid_handoff.object_bay_local_positions.items`.
- Current fixture:
  - `axis_count = 2`;
  - `axis_ids = ["column_axis_x", "column_axis_y"]`;
  - `region_axis_agreement = 0.9429`;
  - `object_phase.score = 0.7001`;
  - `region_bays.score = 0.446`;
  - `object_bay_local_positions.score = 0.4091`.
- Important boundary:
  - this is a column-grid handoff summary over existing authored axis and bay proxy rows;
  - it does not compute Rhino/BIM grid topology, structural bay validation, multi-axis grid cells, or irregular local grid interpolation.

2026-07-07, material calibration adapter handoff pass:

- Added `matrix["adapter_payload"]["material_calibration_handoff"]`.
- The payload now gives downstream material/perception calibration adapters one compact place to find:
  - boundary weight metadata coverage and missing ids;
  - authored `walk_block`, `see_block`, `grouping_strength`, walk/see gap, and non-blocking grouping-cue means;
  - calibration candidates for authored `glass`, `rug`, `material`, and `visual` boundary kinds with current walk/see/grouping weights and thickness metadata.
- Current fixture:
  - `weight_metadata.coverage = 1.0`;
  - `missing_ids = []`;
  - `walk_block = 0.4615`;
  - `see_block = 0.3962`;
  - `grouping_strength = 0.6077`;
  - calibration candidates include `glass_boundary`, `rug_boundary`, `material_boundary`, and `diagonal_boundary`.
- Important boundary:
  - this is a material-calibration handoff summary over authored SVG metadata;
  - it does not infer Rhino/BIM materials, lighting, glass transmittance, perceptual grouping thresholds, or validated calibration curves.

2026-07-07, visual analysis adapter handoff pass:

- Added `matrix["adapter_payload"]["visual_analysis_handoff"]`.
- The payload now gives downstream visual-analysis adapters one compact place to find:
  - centerline `visibility_graph` method, node count, edge count, visible/blocked edge ratios, and blocking-boundary count;
  - radial `isovist_radial_proxy` method, status, vantage count, ray count, blocked ray count, blocked ray ratio, mean hit distance, and `mean_hit_polygon_area`.
- Current fixture:
  - `visibility_graph.node_count = 11`;
  - `visibility_graph.edge_count = 28`;
  - `visible_edge_ratio = 0.7143`;
  - `blocked_edge_ratio = 0.2857`;
  - `blocking_boundary_count = 3`;
  - `isovist_radial_proxy.ray_count = 88`;
  - `isovist_radial_proxy.blocked_ray_count = 20`;
  - `isovist_radial_proxy.mean_hit_polygon_area = 415076.4205`.
- Important boundary:
  - this is a visual-analysis handoff summary over existing centerline visibility and radial ray proxies;
  - it does not compute full isovist polygons, Visibility Graph Analysis fields, visual integration, or calibrated visual exposure.

2026-07-07, route topology handoff export pass:

- Added `matrix["adapter_payload"]["route_topology_handoff"]`.
- The payload now gives downstream route/navmesh adapters one compact place to find:
  - Shapely CAD room-minus-blocker component graph method, node count, and edge count;
  - rect-cell `free_space_polygon_graph` method, node count, and edge count;
  - `host_relationships` method plus hosted/fallback entry counts.
- Added a regression using the synthetic adapter geometry fixture:
  - `cad_component_graph.node_count = 3`;
  - `cad_component_graph.edge_count = 2`;
  - `free_space_polygon_graph.node_count = 8`;
  - `free_space_polygon_graph.edge_count = 8`;
  - fallback entry count = `1`.
- Important boundary:
  - this is a compact route-topology handoff summary;
  - it does not compute navmesh faces, medial-axis routes, skeleton routes, route certification, detour quality, or code-compliant egress.

2026-07-07, adapter host relationships export pass:

- Added `matrix["adapter_payload"]["host_relationships"]`.
- The payload now exposes:
  - `entry_boundary_hosts`: the existing `entry_boundary_associations` from boundary metrics;
  - `hosted_entry_count`;
  - `fallback_entry_count`;
  - method `entry_boundary_associations_from_host_metadata_or_nearest_geometry`.
- This reuses the current `host-boundary` / `host_boundary` / `host` metadata path and nearest-geometry fallback instead of recomputing geometry in the adapter export.
- Important boundary:
  - this is a neutral host-relationship export for downstream Rhino/VisualARQ/BIM adapters;
  - fallback relationships remain SVG geometry proxies and must be replaced by live hosted topology in real adapters.

2026-07-07, boundary-kind adapter target hint pass:

- Preserved non-empty scene record `metadata` in `matrix["adapter_payload"]["scene_records"]`.
- Extended `adapter_targets` so authored `boundary-kind` metadata is not flattened into generic walls:
  - `glass` -> `GlassBoundary`, Rhino `Curve|Brep|GlassMaterial`, BIM `CurtainWall|Window`;
  - `rug` and `material` -> `BoundaryCue`, Rhino `Curve|Hatch|Surface`, BIM `SurfaceFinish|Annotation`;
  - `visual` -> `VisualBoundaryCue`, Rhino `Curve|Annotation`, BIM `Annotation|ZoneBoundary`.
- Added a regression covering wall, glass, rug, material, and visual boundary target hints in the neutral adapter payload.
- Important boundary:
  - these are target hints for downstream adapters;
  - they are not live Rhino material assignment, VisualARQ hosted objects, IFC family validation, or BIM authoring.

2026-07-07, notebook display order cleanup pass:

- Kept the executable notebook ordered into five inspection sections:
  - `1. Source Fixture`;
  - `2. Evaluation Summary`;
  - `3. Metric Matrix`;
  - `4. Clean Evidence Overlay`;
  - `5. Audit Snapshot`.
- Added a regression that checks:
  - the notebook section order stays stable;
  - the default overlay cell calls `scene_metric_overlay_svg(scene, matrix)`;
  - `include_free_space_paths=True` is not used in the notebook;
  - the executed clean overlay output does not contain dense `free-space-graph-entry-region-path` lines.
- Current notebook status:
  - still executable and ordered;
  - visually busy, but no longer unordered;
  - dense free-space route segments remain recorded as optional evidence, not default visual clutter.
- Remaining work after this cleanup:
  - real Rhino / Grasshopper / VisualARQ / BIM adapters;
  - hosted topology, navmesh / medial-axis / skeleton routing, full isovist / VGA, irregular column-grid interpolation, and material/perception calibration.

2026-07-07, neutral adapter payload export pass:

- Added `matrix["adapter_payload"]` to `evaluate_scene(scene)`.
- Method name:
  - `neutral_adapter_payload_export`.
- The neutral adapter payload exports:
  - `scene_records`: record id, role, group, region, bbox, and `adapter_refs`;
  - `external_refs`: reverse lookup from external ids such as `ifc_guid`, `rhino_guid`, and `source_layer` back to scene record ids;
  - `evidence_geometry`: proxy free-space polygon previews, room-minus-blocker boundary loops, and negative-space graph node/edge summaries;
  - `graph_namespaces`: compact `walk_graph` and `visibility_graph` summaries for downstream adapters;
  - `grasshopper_branches`: DataTree-like branch index strings for scene records, metric rows, and graph namespaces;
  - `adapter_targets`: per-record neutral/Rhino/Grasshopper/BIM target hints;
  - `metric_rows`: compact `view_id`, `metric`, `score`, and `status` summaries for downstream adapter handoff.
- Added synthetic regression:
  - a two-record scene exports table/wall scene records, reverse external refs, and an `adapter_reference_coverage` metric summary.
- Current fixture evidence:
  - `adapter_payload.record_count = 46`;
  - `evidence_geometry.free_space_polygons.count = 814`;
  - `evidence_geometry.free_space_polygon_graph.node_count = 814`;
  - `evidence_geometry.free_space_polygon_graph.edge_count = 1426`;
  - `evidence_geometry.free_space_polygon_graph.metrics.cycle_rank = 613`;
  - `evidence_geometry.free_space_polygon_graph.entry_region_distance_evidence` count = `32`;
  - `graph_namespaces.walk_graph.edge_count = 7`;
  - `graph_namespaces.visibility_graph.edge_count = 28`;
  - `grasshopper_branches` includes `{0;objects;0}`, `{0;boundaries;0}`, `{0;metrics;...}`, and `{0;graphs;...}` branches;
  - `validate_adapter_payload_json` rejects branch tables missing the record, metric, or graph branch groups;
  - `adapter_targets` maps fixture furniture to `FurnitureObject`, openings to `Entry`, room boundary to `Boundary`, glass to `GlassBoundary`, rug/material/visual cues to non-wall cue targets, and column axes to `ColumnGrid.axes`;
  - `evidence_geometry.room_minus_blocker_polygons.count = 1`;
  - `evidence_geometry.cad_room_minus_blocker_polygons.count = 1`;
  - `evidence_geometry.negative_space_graph.node_count = 12`;
  - `ifc_guid.ifc-room-boundary -> room_boundary`;
  - `rhino_guid.rhino-north-table-r1-c1 -> north_table_r1_c1`;
  - source layers include `A-WALL` and `I-FURN`.
- Important boundary:
  - this is a neutral adapter payload for Rhino/Grasshopper/VisualARQ/BIM handoff;
  - it is not a live Rhino document link, Grasshopper DataTree execution, VisualARQ hosted-object topology, BIM family validation, or navmesh topology.

2026-07-07, Shapely room-minus-blocker boolean evidence pass:

- Added dependency:
  - `shapely`.
- Added descriptor evidence:
  - `matrix["negative_space"]["cad_room_minus_blocker_polygons"]`.
- Added metric row:
  - `path_connectivity.cad_room_minus_blocker_polygon_count`.
- Added closure audit row:
  - `path_connectivity.cad_room_minus_blocker_area_residual_ratio`.
- Added fragmentation severity row:
  - `path_connectivity.cad_room_minus_blocker_largest_component_area_ratio`.
- Added component touch row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_region_ratio`.
- Added component entry-touched area row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_area_ratio`.
- Added component entry-touched count row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_component_ratio`.
- Added component region-pair row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_region_pair_ratio`.
- Added component graph audit row:
  - `path_connectivity.cad_room_minus_blocker_component_graph_edge_count`.
- Method name:
  - `shapely_room_polygon_difference_blocker_union`.
- Closure method name:
  - `shapely_room_minus_blocker_area_minus_negative_space_area`.
- Fragmentation method name:
  - `shapely_largest_component_area_over_total_free_area`.
- Component touch method name:
  - `shapely_component_entry_region_touch_proxy`.
- Component entry-touched area method name:
  - `shapely_component_entry_touched_area_ratio_proxy`.
- Component entry-touched count method name:
  - `shapely_component_entry_touched_component_count_proxy`.
- Component region-pair method name:
  - `shapely_component_entry_connected_region_pair_proxy`.
- Component graph method name:
  - `shapely_component_entry_region_touch_graph_proxy`.
- Added adapter evidence geometry:
  - `adapter_payload.evidence_geometry.cad_room_minus_blocker_polygons`.
  - `adapter_payload.evidence_geometry.cad_room_minus_blocker_entry_connected_area`.
- The descriptor builds a Shapely room polygon from the authored room boundary and subtracts the union of current walk blockers.
- Exported evidence includes:
  - `component_index`;
  - normalized `outer_ring`;
  - normalized `holes`;
  - `area`;
  - `source = shapely_difference`.
- Component touch evidence includes:
  - `component_index`;
  - `entry_ids`;
  - `region_ids`;
  - `region_overlap_areas`.
- Adapter entry-connected area evidence includes:
  - `entry_connected_component_ids`;
  - `non_entry_connected_component_ids`;
  - `entry_connected_component_area`;
  - `non_entry_connected_component_area`;
  - `cad_room_minus_blocker_area_total`;
  - `entry_connected_area_ratio`.
- Current fixture evidence:
  - `cad_room_minus_blocker_polygon_count`: `1`;
  - fixture `cad_room_minus_blocker_polygons[0]` has `20` hole rings and area `684736.0`;
  - `cad_room_minus_blocker_area_residual_ratio`: `0.0`;
  - `cad_room_minus_blocker_largest_component_area_ratio`: `1.0`;
  - `cad_room_minus_blocker_entry_connected_region_ratio`: `1.0`;
  - `cad_room_minus_blocker_entry_connected_area_ratio`: `1.0`;
  - `cad_room_minus_blocker_entry_connected_component_ratio`: `1.0`;
  - `cad_room_minus_blocker_entry_connected_region_pair_ratio`: `1.0`;
  - `cad_room_minus_blocker_component_graph_edge_count`: `11`;
  - `cad_room_minus_blocker_component_touch_evidence` has one component touching four entries and seven analysis regions;
  - `cad_room_minus_blocker_component_graph`: `12` nodes and `11` edges;
  - adapter payload `cad_room_minus_blocker_polygons.count = 1`.
  - adapter payload `cad_room_minus_blocker_component_touch_evidence.items` count = `1`.
- Important boundary:
  - this is true polygon difference over current authored SVG-derived polygons;
  - it is still not RhinoCommon / VisualARQ hosted topology, CAD curve cleanup, BIM family validation, navmesh faces, medial-axis clearance, or route certification.

2026-07-07, adapter reference traceability pass:

- Added normalized loader field:
  - `adapter_refs`.
- The structured SVG loader now maps external ids into stable keys:
  - `rhino_guid`;
  - `ifc_guid`;
  - `visualarq_id`;
  - `source_layer`;
  - `source_id`.
- Added metric row:
  - `adapter_readiness.adapter_reference_coverage`.
- Method name:
  - `records_with_external_adapter_refs_over_scene_records`.
- Added row evidence:
  - `adapter_reference_role_coverage`, with per-role record counts, referenced counts, coverage, evidence ids, and missing ids.
- Added synthetic regressions:
  - an SVG boundary with `data-rhino-guid`, `data-ifc-guid`, `data-visualarq-id`, and `data-source-layer` normalizes those values into `adapter_refs`;
  - a synthetic scene with one adapter-referenced record and one plain record reports `adapter_reference_coverage = 0.5`, plus per-role coverage for `table` and `boundary`.
- Current fixture evidence:
  - `room_boundary`: `ifc_guid = ifc-room-boundary`, `source_layer = A-WALL`;
  - `north_table_r1_c1`: `rhino_guid = rhino-north-table-r1-c1`, `source_layer = I-FURN`;
  - `adapter_reference_coverage = 0.0435` (`2 / 46` records).
- Important boundary:
  - adapter refs are traceability metadata for Rhino/VisualARQ/BIM migration;
  - they do not prove live hosted topology, BIM family semantics, wall/door relationships, or route graph correctness.

2026-07-06, sampled-vs-negative-space proxy consistency pass:

- Added metric row:
  - `path_connectivity.sampled_negative_space_area_ratio_delta`.
- Method name:
  - `absolute_sampled_walkable_minus_negative_space_area_ratio`.
- The row compares:
  - `sampled_walkable_cell_ratio`;
  - `negative_space_area_ratio_proxy`.
- Current fixture:
  - sampled walkable ratio: `0.8912`;
  - negative-space area ratio proxy: `0.8493`;
  - absolute delta: `0.0419`.
- Important boundary:
  - this is a disagreement disclosure between two proxy substrates;
  - it is not CAD boolean validation, a geometric truth error, navmesh validation, or resolution calibration.

2026-07-06, overlapping-polygon blocker risk pass:

- Added descriptor evidence:
  - `matrix["negative_space"]["polygon_blocker_overlap_risk_evidence"]`.
- Added metric row:
  - `path_connectivity.negative_space_polygon_overlap_risk_count`.
- Method name:
  - `nonidentical_polygon_blocker_overlap_detection`.
- Added a synthetic regression:
  - two non-identical triangle blockers overlap;
  - descriptor reports blocker pair `first_triangle` / `second_triangle`;
  - risk count row reports `1`.
- Current fixture:
  - `negative_space_polygon_overlap_risk_count`: `0`.
- Important boundary:
  - this is an explicit warning that the current rect-cell union proxy has entered a risky polygon arrangement;
  - it does not solve general polygon boolean union, CAD room-minus-blocker geometry, navmesh topology, or cleaned negative-space polygons.

2026-07-06, hosted entry-boundary association pass:

- `entry_nearest_boundary_gap_mean` evidence now records `association_method`:
  - `host_boundary_metadata` when an opening record has `host-boundary`, `host_boundary`, or `host`;
  - `nearest_boundary_geometry` as the SVG fallback.
- Added metric row:
  - `boundary_metrics.hosted_entry_boundary_ratio`.
- Method name:
  - `entries_with_explicit_host_boundary_over_entries`.
- Added a synthetic regression:
  - an opening geometrically touches `nearby_wall`;
  - its metadata hosts it on `hosted_wall`;
  - boundary association uses `hosted_wall`, and hosted ratio is `1.0`.
- Current fixture:
  - no hosted opening metadata yet;
  - `hosted_entry_boundary_ratio`: `0.0`;
  - all opening associations use `nearest_boundary_geometry`.
- Important boundary:
  - this is a neutral data-contract step toward Rhino/BIM hosted doorway topology;
  - it does not create hosted topology automatically or replace true doorway-to-negative-space routing.

2026-07-07, fallback entry-boundary association audit pass:

- Added metric row:
  - `boundary_metrics.fallback_entry_boundary_ratio`.
- Method name:
  - `entries_with_nearest_geometry_boundary_over_entries`.
- The row reuses `entry_nearest_boundary_gap_mean.entry_boundary_associations` and reports openings whose boundary association is still `nearest_boundary_geometry`.
- Added a synthetic regression:
  - one opening uses explicit `host-boundary` metadata;
  - one opening has no host and falls back to the nearest boundary;
  - fallback ratio reports `0.5` with fallback evidence `fallback_door`.
- Current fixture:
  - `hosted_entry_boundary_ratio`: `0.0`;
  - `fallback_entry_boundary_ratio`: `1.0`;
  - fallback evidence: `left_entry`, `bottom_entry`, `right_entry_arc`, and `right_entry_line`.
- Important boundary:
  - this makes SVG fallback dependence visible for Rhino/BIM migration review;
  - it does not validate hosted topology, doorway families, or true doorway-to-negative-space routing.

2026-07-06, sampled entry-to-region distance pass:

- Added sampled BFS distance evidence from entries to each region:
  - `matrix["sampled_walkable_space"]["entry_region_grid_distances"]`;
  - `mean_entry_region_grid_steps`;
  - `mean_entry_region_grid_distance`.
- Added metric row:
  - `path_connectivity.sampled_mean_entry_region_grid_distance`.
- Method name: `sampled_occupancy_grid_bfs_distance_proxy`.
- Tightened sampled entry seeding so zero-width openings use the nearest in-domain free cell rather than also seeding the next ring of cells.
- Tightened sampled BFS to stay inside the authored `boundary-kind="room"` domain.
- Current fixture sampled distance descriptor:
  - `region_north_tables`: `55.0`;
  - `region_west_lounge`: `110.0`;
  - `region_center_lounge`: `0.0`;
  - `region_east_work`: `0.0`;
  - `region_east_armchairs`: `0.0`;
  - `region_north_wall`: `385.0`;
  - `region_slanted_test`: `330.0`;
  - mean distance: `125.7143`.
- Important boundary: this is four-neighbor sampled grid distance. It is not continuous route length, not a navigation mesh, not a medial-axis route, and not a space-syntax integration metric.
- Added a disconnected synthetic regression guard:
  - a walk-blocking wall splits entry and region into separate sampled components;
  - unreachable region distance reports `None`;
  - `path_connectivity.sampled_mean_entry_region_grid_distance` reports `not_available` when no region distance exists.

2026-07-06, sampled clearance-to-blocker pass:

- Added `matrix["sampled_walkable_space"]["sampled_clearance_to_walk_blockers"]`.
- Added `path_connectivity.sampled_min_clearance_to_walk_blocker`.
- Added `path_connectivity.sampled_zero_clearance_cell_ratio`.
- Added `path_connectivity.sampled_entry_reachable_min_clearance_to_walk_blocker`.
- Added `path_connectivity.sampled_mean_entry_region_widest_clearance`.
- Added `path_connectivity.sampled_mean_entry_region_clearance_per_distance`.
- Method name: `sampled_free_cell_center_to_nearest_walk_blocker_gap`.
- Zero-clearance ratio method: `sampled_zero_clearance_cells_over_clearance_samples`.
- Entry-reachable clearance method: `sampled_entry_reachable_free_cell_center_to_nearest_walk_blocker_gap`.
- Widest path clearance method: `sampled_grid_widest_path_clearance_proxy`.
- Widest path cell evidence method: `sampled_widest_path_cell_evidence`.
- Clearance-per-distance method: `sampled_widest_clearance_over_entry_region_distance_proxy`.
- The descriptor measures every sampled free domain cell center to the nearest walk blocker and reports:
  - `min_clearance`;
  - `mean_clearance`;
  - `sample_count`;
  - `zero_clearance_sample_count`;
  - `min_clearance_samples`;
  - blocker evidence ids.
- Added a synthetic regression guard:
  - 100 x 100 room;
  - 20 x 20 central walk blocker;
  - default sampled grid from fixture-scale object size;
  - `min_clearance`: `10.0`;
  - `mean_clearance`: `26.6357`;
  - `sample_count`: `24`.
- Current fixture:
  - `min_clearance`: `0.0`;
  - `mean_clearance`: `44.3584`;
  - `zero_clearance_sample_count`: `10`;
  - `sampled_zero_clearance_cell_ratio`: `0.0382`.
- Added a split-room regression where the entry-reachable side reports `sampled_entry_reachable_min_clearance_to_walk_blocker = 10.0`, proving unreachable free-space pockets do not inflate the circulation bottleneck proxy.
- Added a widest-path regression where an entry-to-region sampled route reports `sampled_mean_entry_region_widest_clearance = 40.0`, proving the proxy maximizes bottleneck clearance rather than only reporting shortest sampled distance.
- Current fixture `sampled_mean_entry_region_widest_clearance`: `46.3776`.
- Current fixture `sampled_mean_entry_region_clearance_per_distance`: `0.5859`.
- Widest entry-to-region evidence now includes `path_cells`, reconstructed from the sampled max-min predecessor chain for the selected target cell. Long routes are capped at 32 cells and marked with `path_truncated`.
- Important boundary: this is sampled free-cell center clearance to walk blockers; not medial-axis width field or navmesh clearance.

2026-07-06, sampled region-pair distance pass:

- Added sampled region-pair grid distance evidence:
  - `matrix["sampled_walkable_space"]["region_pair_grid_distances"]`;
  - `mean_region_pair_grid_steps`;
  - `mean_region_pair_grid_distance`.
- Added metric rows:
  - `path_connectivity.sampled_mean_region_pair_grid_distance`;
  - `path_connectivity.sampled_region_pair_reachable_ratio`.
- Method name:
  - `sampled_region_pair_grid_bfs_distance_proxy`.
- Synthetic 1D regression:
  - two regions at opposite ends of a 200x50 room;
  - region-pair distance: `3` sampled steps, `150.0` scene units.
- Current fixture:
  - total region pairs: `21`;
  - finite sampled region-pair distances: `21`;
  - mean sampled region-pair distance: `288.0952`;
  - `sampled_region_pair_reachable_ratio`: `1.0`.
- Important boundary:
  - this is four-neighbor sampled cell distance between region sampled cells;
  - it is not continuous route length, not a navigation mesh, not a medial-axis route, and not space-syntax integration.

2026-07-06, sampled visibility channel pass:

- Added a sampled visibility reachability proxy beside sampled walkability:
  - `matrix["sampled_walkable_space"]["visibility_reachable_region_ratio"]`;
  - `matrix["sampled_walkable_space"]["visibility_region_grid_distances"]`;
  - `mean_visibility_region_grid_steps`;
  - `mean_visibility_region_grid_distance`;
  - `visibility_only_region_ratio`;
  - `walk_only_region_ratio`;
  - `walk_visibility_disagreement_region_ratio`;
  - `matrix["sampled_walkable_space"]["visibility_blocker_evidence"]`;
  - `path_connectivity.sampled_visibility_reachable_region_ratio`;
  - `path_connectivity.sampled_visibility_only_region_ratio`;
  - `path_connectivity.sampled_walk_only_region_ratio`;
  - `path_connectivity.sampled_walk_visibility_disagreement_region_ratio`;
  - `path_connectivity.sampled_mean_visibility_region_grid_distance`.
- Method names:
  - `sampled_visibility_grid_bfs_proxy`;
  - `sampled_visibility_grid_bfs_distance_proxy`.
- The sampled visibility grid reuses the same room domain and entry seeds, but marks blockers from `see_block` instead of `walk_block`.
- Added a synthetic glass-boundary regression:
  - glass has `walk_block=1.0` and `see_block=0.0`;
  - walk reachability to the region is `0.0`;
  - visibility reachability to the same region is `1.0`.
  - visibility-only region ratio is `1.0`.
  - walk/visibility disagreement ratio is `1.0`.
- Added the symmetric visual-screen regression:
  - screen has `walk_block=0.0` and `see_block=1.0`;
  - walk reachability to the region is `1.0`;
  - visibility reachability to the same region is `0.0`;
  - walk-only region ratio is `1.0`.
  - walk/visibility disagreement ratio is `1.0`.
- Current fixture visibility reachable region ratio: `1.0`.
- Current fixture visibility-only region ratio: `0.0`.
- Current fixture walk-only region ratio: `0.0`.
- Current fixture walk/visibility disagreement ratio: `0.0`.
- Current fixture mean visibility grid distance: `125.7143`.
- Important boundary: this is a see-block weighted sampled BFS proxy. It is not isovist, ray casting, visibility graph analysis, visual distance, or a calibrated transparency perception model.

2026-07-06, sampled visibility region-pair pass:

- Added sampled visibility pair evidence:
  - `matrix["sampled_walkable_space"]["sampled_visibility_reachable_region_pair_ratio"]`;
  - `matrix["sampled_walkable_space"]["sampled_visibility_reachable_region_pair_evidence"]`;
  - `matrix["sampled_walkable_space"]["sampled_visibility_unreachable_region_pair_evidence"]`.
- Added metric row:
  - `path_connectivity.sampled_visibility_reachable_region_pair_ratio`.
- Synthetic glass regression:
  - a `walk_block=1.0`, `see_block=0.0` glass boundary splits walk reachability but not visibility reachability;
  - `sampled_entry_reachable_region_pair_ratio`: `0.0`;
  - `sampled_visibility_reachable_region_pair_ratio`: `1.0`.
- Current fixture:
  - all seven analysis regions are sampled-visibility reachable;
  - total region pairs: `21`;
  - `sampled_visibility_reachable_region_pair_ratio`: `1.0`.
- Added pair-level walk/visibility contrast rows:
  - `path_connectivity.sampled_visibility_only_region_pair_ratio`;
  - `path_connectivity.sampled_walk_only_region_pair_ratio`;
  - `path_connectivity.sampled_walk_visibility_disagreement_region_pair_ratio`.
- The same synthetic glass regression reports:
  - `sampled_visibility_only_region_pair_ratio`: `1.0`;
  - `sampled_walk_only_region_pair_ratio`: `0.0`;
  - `sampled_walk_visibility_disagreement_region_pair_ratio`: `1.0`.
- Current fixture pair contrast:
  - `sampled_visibility_only_region_pair_ratio`: `0.0`;
  - `sampled_walk_only_region_pair_ratio`: `0.0`;
  - `sampled_walk_visibility_disagreement_region_pair_ratio`: `0.0`.
- Important boundary:
  - this pair row summarizes sampled see-block BFS region reachability;
  - the contrast rows are set differences between sampled walk and visibility pair evidence;
  - they are not isovist, Visibility Graph Analysis, route distance, visual integration, or calibrated transparency perception.

2026-07-06, line-of-sight visibility evidence pass:

- Added metric row:
  - `path_connectivity.line_of_sight_entry_region_ratio`.
  - `path_connectivity.line_of_sight_region_pair_ratio`.
- Method name:
  - `entry_region_centerline_see_block_intersection`.
  - `region_pair_centerline_see_block_intersection`.
- The row tests each analysis region against entry-to-region centerlines and reports whether at least one entry centerline is not intersected by authored `see_block` boundaries.
- The region-pair row tests each analysis region pair against the centerline between their region bbox centers.
- `line_of_sight_evidence` and `line_of_sight_region_pair_evidence` now include `blocking_boundary_evidence` with `intersection_points`, `intersection_distances_from_start`, and `intersection_distance_ratios` for each blocking boundary, so the centerline hit can be inspected rather than only named by id.
- Added a synthetic regression where:
  - an entry-hosting wall touches the opening but does not count as a visual blocker for that entry;
  - a separate `see_block=1.0` visual screen crosses the entry-to-region centerline;
  - `line_of_sight_entry_region_ratio`: `0.0`;
  - `line_of_sight_evidence` reports `blocking_boundary_ids=["visual_screen"]`.
- Added a region-pair synthetic regression where a `see_block=1.0` visual screen crosses the centerline between two regions:
  - `line_of_sight_region_pair_ratio`: `0.0`;
  - `line_of_sight_region_pair_evidence` reports `blocking_boundary_ids=["visual_screen"]`.
- Added distance evidence regressions:
  - entry-to-region visual screen hit distance `120.0` and ratio `0.6`;
  - region-pair visual screen hit distance `60.0` and ratio `0.5`.
- Current fixture:
  - `line_of_sight_entry_region_ratio`: `1.0`;
  - `line_of_sight_region_pair_ratio`: `0.619`;
  - region-pair evidence count: `21`.
- Important boundary:
  - this is a centerline ray/intersection proxy, not an isovist field, not full Visibility Graph Analysis, and not material transparency calibration;
  - hosted opening relationships are still inferred by rect contact, so Rhino/BIM adapters should replace that with explicit wall/opening hosts.

2026-07-07, line-of-sight blocker overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with `line-of-sight-blocker-hit` circles for `blocking_boundary_evidence` intersection points.
- The same overlay now draws `line-of-sight-centerline` segments for entry-region and region-pair centerline samples, with `data-visible` and `data-blocker-count`.
- The overlay records:
  - `data-boundary`;
  - `data-x` and `data-y`;
  - `data-distance`;
  - `data-distance-ratio`.
- Current fixture overlay includes a `glass_boundary` hit at `(690.0, 679.48)` with `data-distance-ratio="0.6240"`.
- Important boundary:
  - this visualizes existing centerline blocker evidence only;
  - it is not an isovist polygon, visibility graph, or calibrated visual exposure field.

2026-07-07, line-of-sight centerline overlay evidence pass:

- Added a regression that requires the fixture overlay to expose the blocked centerline from `region_north_tables` to `region_east_armchairs`.
- The line carries `data-visible="false"` and `data-blocker-count="1"` and uses the region bbox centers as endpoints.
- This makes the tested sight segment auditable alongside the blocker hit marker.

2026-07-07, line-of-sight graph evidence pass:

- Added `matrix["line_of_sight_graph"]` as graph-shaped evidence over the direct centerline visibility proxy.
- Graph contents:
  - `entry` and `region` nodes with bbox-center points;
  - `entry_region_centerline_visibility` edges;
  - `region_pair_centerline_visibility` edges.
- Each edge carries:
  - `visible`;
  - `centerline` start/end/length;
  - `blocking_boundary_ids`;
  - `blocking_boundary_evidence`.
- The graph now includes `metrics`:
  - `visible_edge_ratio`;
  - `blocked_edge_ratio`;
  - `visible_edge_ids`;
  - `blocked_edge_ids`;
  - `blocking_boundary_ids`;
  - `blocking_boundary_edge_evidence`;
  - `mean_centerline_length`.
- Added metric rows:
  - `path_connectivity.line_of_sight_graph_visible_edge_ratio`;
  - `path_connectivity.line_of_sight_graph_blocked_edge_ratio`;
  - `path_connectivity.line_of_sight_graph_blocking_boundary_count`.
- Added a synthetic regression where `left_region` to `right_region` is blocked by `visual_screen`, producing one `region_pair_centerline_visibility` edge with the same intersection evidence used by the metric row.
- Important boundary:
  - this is explicit graph-shaped evidence for centerline visibility only;
  - it is not a full visibility graph analysis, isovist polygon field, or visual integration metric.

2026-07-07, line-of-sight graph blocker audit row:

- Added `path_connectivity.line_of_sight_graph_blocking_boundary_count`.
- Method: `line_of_sight_graph_unique_blocking_boundary_count`.
- The row reports the count and ids of unique authored `see_block` boundaries intersecting blocked centerline graph edges.
- It reuses `line_of_sight_graph.metrics.blocking_boundary_ids`, `blocked_edge_ids`, and `blocking_boundary_edge_evidence`, so each blocker-level visibility obstruction can be traced to the centerline graph edges it blocks.
- Important boundary:
  - this is unique blocker attribution for the centerline graph proxy only;
  - it is not obstacle attribution from full Visibility Graph Analysis, isovist fields, or calibrated material perception.

2026-07-07, radial isovist proxy pass:

- Added `matrix["isovist_radial_proxy"]`.
- Method name:
  - `radial_isovist_see_block_ray_intersection_proxy`.
- The proxy samples eight room-bounded rays from each entry and analysis-region center.
- Each ray records:
  - `vantage_id`;
  - `vantage_kind`;
  - `angle_degrees`;
  - `start`;
  - `hit_point`;
  - `hit_distance`;
  - `hit_boundary_id`;
  - `hit_boundary_kind`;
  - `blocked_by_see_block`.
- Added metric row:
  - `path_connectivity.isovist_radial_blocked_ray_ratio`.
- Added area proxy row:
  - `path_connectivity.isovist_radial_hit_polygon_area_mean`.
- Method name:
  - `radial_isovist_hit_point_polygon_area_proxy`.
- Added a synthetic regression where one visual screen blocks only the east ray from a center region:
  - `ray_count = 8`;
  - `blocked_ray_count = 1`;
  - `isovist_radial_blocked_ray_ratio = 0.125`;
  - blocked evidence `center_region:0` hits `visual_screen` at `(150.0, 50.0)`.
- Current fixture:
  - `vantage_count`: `11`;
  - `ray_count`: `88`;
  - `blocked_ray_count`: `20`;
  - `isovist_radial_blocked_ray_ratio`: `0.2273`;
  - `mean_hit_distance`: `332.0904`;
  - `mean_hit_polygon_area`: `415076.4205`;
  - `isovist_area_evidence` covers `11` vantages.
- Updated the notebook audit output with:
  - `isovist_radial_proxy`;
  - `isovist_radial_blocked_ray_ratio`;
  - `isovist_radial_hit_polygon_area_mean`;
  - `mean_hit_polygon_area`;
  - `isovist_area_evidence`.
- Important boundary:
  - this is an 8-direction radial ray sampling proxy using authored `see_block` boundaries;
  - the area row connects ordered radial hit points into a polygon area proxy;
  - it is not a full isovist polygon, Visibility Graph Analysis, visual integration, or calibrated visual exposure field.

2026-07-07, visual-analysis adapter handoff detail pass:

- Added existing evidence details to `matrix["adapter_payload"]["visual_analysis_handoff"]`:
  - `visual_analysis_handoff.visibility_graph.items`;
  - `visual_analysis_handoff.isovist_radial_proxy.ray_items`;
  - `visual_analysis_handoff.isovist_radial_proxy.area_items`.
- Current fixture counts:
  - `visibility_graph.items` count = `28`;
  - `isovist_radial_proxy.ray_items` count = `88`;
  - `isovist_radial_proxy.area_items` count = `11`.
- Important boundary:
  - this only forwards existing centerline visibility and radial isovist proxy evidence;
  - it is not a new full VGA, full isovist polygon, or calibrated visual integration algorithm.

2026-07-07, route-topology adapter handoff detail pass:

- Added existing graph details to `matrix["adapter_payload"]["route_topology_handoff"]`:
  - `route_topology_handoff.cad_component_graph.items`;
  - `route_topology_handoff.free_space_polygon_graph.items`.
- These fields carry the current graph nodes and edges already exported in `evidence_geometry`.
- Important boundary:
  - this only forwards existing Shapely component graph and rect-cell free-space graph evidence;
  - it is not a navmesh, medial axis, skeleton graph, hosted-door topology, or route solver.

2026-07-06, sampled walkable-space proxy pass:

- Added `matrix["sampled_walkable_space"]` to `evaluate_scene(scene)`.
- Added path-connectivity rows:
  - `sampled_walkable_cell_ratio`;
  - `sampled_entry_reachable_cell_ratio`;
  - `sampled_path_reachable_region_ratio`.
- Method name: `sampled_occupancy_grid_bfs_proxy`.
- Implementation reuses the existing `SpatialGridBackend` with an adaptive default resolution:
  - measurable furniture present: median shortest furniture side;
  - no measurable furniture: 50 scene units;
  - furniture and walk-blocking non-room boundaries mark occupied cells;
  - door/opening records seed four-neighbor BFS;
  - regions report whether any sampled free cell is reachable;
  - `sampled_path_reachable_region_ratio` requires both entry-reachable cells and sampled contact with the authored path cells.
- This is a sampled walkable-space proxy, not CAD boolean negative space, not a navmesh, and not a medial-axis or visibility graph.
- Notebook audit now exposes the sampled descriptor so the table row count and descriptor can be inspected together.
- Grill-me correction: the path-region sampled metric was tightened after a synthetic test showed that plain entry reachability was too broad for the metric name.
- Still open:
  - true room-minus-blocker negative-space polygons;
  - boundary-aware graph edges instead of cell adjacency only;
  - width field / medial-axis route sampling;
  - fixture variants where sampled resolution changes the result.

2026-07-06, sampled room-domain mask pass:

- Fixed the sampled walkable-space proxy so ratios use the authored `boundary-kind="room"` domain rather than the whole SVG viewBox.
- Added a synthetic regression test proving a 100x100 room inside a 200x100 SVG counts 4 domain cells and 4 outside-domain cells at 50-unit resolution.
- Current fixture sampled descriptor:
  - `resolution`: `55.0`;
  - `total_cells`: 361;
  - `domain_cells`: 294;
  - `outside_domain_cells`: 67;
  - `blocked_cells`: 32;
  - `walkable_cell_ratio`: `0.8912`;
  - `entry_reachable_cell_ratio`: `0.8912`;
  - `entry_reachable_region_ratio`: `1.0`;
  - `path_reachable_region_ratio`: `0.7143`.
- This is still a sampled proxy. The next real step remains continuous room-minus-blocker negative-space geometry.

2026-07-06, sampled component fragmentation pass:

- Added sampled free-space component descriptors to `matrix["sampled_walkable_space"]`:
  - `component_count`;
  - `component_sizes`;
  - `largest_component_cell_ratio`;
  - `entry_reachable_component_ratio`.
- Added metric rows:
  - `path_connectivity.sampled_component_count`;
  - `path_connectivity.sampled_largest_component_cell_ratio`.
- Added a synthetic regression test where a walk-blocking wall splits four free sampled cells into two components.
- Current fixture remains one sampled free-space component:
  - `component_count`: `1`;
  - `component_sizes`: `[262]`;
  - `largest_component_cell_ratio`: `1.0`;
  - `entry_reachable_component_ratio`: `1.0`.
- Important boundary: this is sampled fragmentation evidence, not a continuous route graph, medial axis, or space syntax graph.

2026-07-06, sampled entry-reachable region-pair pass:

- Added sampled component pair evidence:
  - `matrix["sampled_walkable_space"]["sampled_entry_reachable_region_pair_ratio"]`;
  - `matrix["sampled_walkable_space"]["sampled_entry_reachable_region_pair_evidence"]`;
  - `matrix["sampled_walkable_space"]["sampled_unreachable_region_pair_evidence"]`.
- Added metric row:
  - `path_connectivity.sampled_entry_reachable_region_pair_ratio`.
- The row reports the share of region pairs that share an entry-reachable sampled walk component, with connected pair evidence, unreachable pair evidence, numerator, and denominator.
- Synthetic split-room regression:
  - total region pairs: `3`;
  - entry-reachable sampled same-component pairs: `1`;
  - `sampled_entry_reachable_region_pair_ratio`: `0.3333`.
- Current fixture:
  - one entry-reachable sampled component touches all seven analysis regions;
  - total region pairs: `21`;
  - `sampled_entry_reachable_region_pair_ratio`: `1.0`.
- Important boundary:
  - this is sampled component evidence over four-neighbor cells;
  - it is not navmesh routing, route distance, route quality, shortest-path routing, or path certification.

2026-07-06, sampled entry-to-region matrix row pass:

- Exposed the existing sampled descriptor `entry_reachable_region_ratio` as a metric row:
  - `path_connectivity.sampled_entry_reachable_region_ratio`.
- Current fixture score: `1.0`.
- This complements `sampled_path_reachable_region_ratio`:
  - entry-reachable region ratio asks whether a region has any entry-reachable sampled free cell;
  - path-reachable region ratio additionally requires sampled contact with authored path cells.
- Important boundary: both rows are sampled proxies, not continuous negative-space route certification.

2026-07-06, correction after user audit:

- The previous completion claim was too broad.
- Current deliverables are useful, but they do not yet meet the user's full requirement because the executable notebook still manually declares fixture objects.
- Correct status:
  - documentation and manual fixture notebook: present;
  - automatic structured-SVG-to-Scene loading: not implemented;
  - automatic `evaluate_scene(scene)` metric matrix pipeline: not implemented;
  - notebook using the automatic loader instead of a hand-written object table: not implemented;
  - Rhino / Grasshopper / VisualARQ migration: designed only, not implemented.
- The controlling next spec is `docs/indoor_layout_evaluation_matrix_spec.md` section 26.
- Completion is allowed only after the test-fix loop in section 26 passes.

2026-07-06, structured SVG automation pass:

- Implemented `load_structured_svg_scene()` for the current structured SVG fixture.
- Implemented `evaluate_scene(scene)` and `scene_metric_overlay_svg()`.
- Updated `test/floorplan_order_matrix_demo.ipynb` to use the automatic loader/evaluator path.
- Correction: this pass completes only the structured SVG automation prototype. It does not complete the full evaluation matrix.
- Current `evaluate_scene(scene)` covers:
  - OCTA-backed north table order;
  - simple group compactness for lounge / armchair areas;
  - opening count;
  - uncertainty log.
- Still open for full matrix completion:
  - region-to-region alignment;
  - region-to-column-grid alignment;
  - whole-space force aggregation;
  - path / negative-space connectivity descriptors;
  - boundary walk/see/grouping strength metrics beyond opening count;
  - evidence overlays for each full metric family;
  - fixture variants proving slanted regions, irregular rooms, rug/material boundaries, and glass/walk-vs-see separation.
- Added focused tests in `test/test_floorplan_scene_loader.py` for:
  - SVG metadata;
  - scene loading;
  - stable metric rows;
  - overlay evidence;
  - notebook source using the automatic path;
  - audit/status evidence.
- Remaining deferred work:
  - arbitrary PNG/image recognition;
  - Rhino / VisualARQ plugin adapters;
  - perception-calibrated weights;
  - broader fixture variants beyond the current test plan.

2026-07-06, evaluator family expansion pass:

- Added structured SVG `data-role="path"` metadata for the fixture path placeholder.
- Extended `load_structured_svg_scene()` so parsed scenes include `paths`.
- Extended `evaluate_scene(scene)` to emit stable rows for the requested matrix families:
  - `north_tables_order`: OCTA-backed repeated-table order;
  - `west_lounge_geometry`, `center_lounge_geometry`, `east_armchair_geometry`: geometry-backed compactness;
  - `region_alignment`: region bbox axis agreement prototype;
  - `column_alignment`: explicit `not_available` row when no column-grid metadata exists;
  - `whole_space_force`: furniture-group bbox axis concentration prototype;
  - `path_connectivity`: path-placeholder area ratio with entry evidence;
  - `boundary_connectivity` and `boundary_metrics`: opening count / opening ratio descriptors;
  - `uncertainties`: records missing negative-space graph and missing column-grid metadata.
- Re-executed `test/floorplan_order_matrix_demo.ipynb` after the evaluator expansion.
- This is still a prototype expansion, not the final evaluation matrix. The weak rows are deliberate placeholders with explicit method/status/uncertainty fields.
- Still open for full matrix completion:
  - robust region axes for slanted and irregular regions;
  - real column-grid metadata and local grid phase scoring;
  - path graph / medial-axis / visibility graph connectivity;
  - boundary walk/see/grouping weights from explicit metadata;
  - evidence overlays per metric family;
  - fixture variants for rug/material, glass, non-orthogonal grid, and irregular room cases.

2026-07-06, boundary/column/path strengthening pass:

- Added authored continuous boundary weights to the structured SVG fixture:
  - `data-walk-block`;
  - `data-see-block`;
  - `data-grouping-strength`.
- `load_structured_svg_scene()` now exposes parsed `weights` for boundaries, openings, and path placeholders.
- Added minimal column-grid reference axes in the fixture and parsed them into `scene["column_axes"]`.
- Replaced the previous `column_alignment` `not_available` row for this fixture with a computed region-axis-to-column-axis similarity score.
- Expanded `boundary_metrics` from opening ratio only to:
  - `opening_ratio`;
  - `closed_blocking_boundary_ratio`;
  - `walk_block_mean`;
  - `see_block_mean`;
  - `walk_see_block_gap_mean`;
  - `non_blocking_grouping_cue_mean`;
  - `grouping_strength_mean`.
- Expanded `path_connectivity` with `entry_touch_ratio`, a fixture-level entry/path bbox intersection descriptor.
- Current `closed_blocking_boundary_ratio`: `0.5556`, covering room/outer wall, north short wall, bottom partition, and internal partition as authored walk-and-see blocking boundaries.
- These are still low-cost structured-geometry descriptors. They do not replace:
  - real boundary material mapping;
  - column bay / local-grid phase scoring;
  - medial-axis, visibility graph, or navigation graph connectivity.

2026-07-07, boundary weight metadata coverage pass:

- Added metric row:
  - `boundary_metrics.boundary_weight_metadata_coverage`.
- Method name:
  - `records_with_explicit_walk_see_grouping_weights_over_weighted_boundary_records`.
- The row audits whether each boundary/opening record has explicit metadata for:
  - `walk_block`;
  - `see_block`;
  - `grouping_strength`.
- Evidence includes:
  - `weight_metadata_evidence`;
  - `missing_weight_metadata_ids`.
- Added a synthetic regression with one authored glass boundary and one default wall:
  - coverage score `0.5`;
  - missing id `default_wall`.
- Current fixture:
  - `boundary_weight_metadata_coverage`: `1.0`;
  - weighted records audited: `13`;
  - `missing_weight_metadata_ids`: `[]`.
- Updated the notebook audit output with:
  - `boundary_weight_metadata_coverage`;
  - `missing_weight_metadata_ids`.
- Important boundary:
  - this verifies explicit weight provenance for the structured fixture;
  - it is not material calibration, perception validation, or BIM material mapping.

2026-07-06, slanted-region and multi-channel-boundary pass:

- Added a slanted polygon region fixture with `data-axis-angle="30"` and point parsing.
- `load_structured_svg_scene()` now preserves `points` for polygon/path records.
- `region_alignment` and `column_alignment` now use authored/local axis metadata when present, instead of only bbox orientation.
- Added glass, rug, and material boundary fixtures:
  - glass: high walk block, low see block, high grouping strength;
  - rug: no walk/see block, high grouping strength.
  - material: no walk/see block, medium grouping strength.
- Expanded `boundary_metrics` with:
  - `glass_walk_see_gap`;
  - `rug_grouping_without_block`.
- Added `walk_see_block_gap_mean` as a global boundary-channel split score.
- Added `non_blocking_grouping_cue_mean` as a general soft-boundary cue score for rug/material/color/surface grouping that does not block walking or sight.
- Added `closed_blocking_boundary_ratio` as a direct closed-wall / fully blocking boundary fixture descriptor.
- This directly covers the original prompt's glass-wall and rug-boundary cases at structured-fixture level.
- Still open:
  - deriving local axes from arbitrary polygons without authored `data-axis-angle`;
  - curved wall/path parsing beyond bbox evidence;
  - perception-calibrated material/surface cue weights.

2026-07-06, polygon-axis and path-region touch pass:

- Removed the authored `data-axis-angle` from the slanted polygon region fixture.
- `evaluate_scene(scene)` now derives a region local axis from polygon longest edge before falling back to bbox orientation.
- Updated `region_alignment` and `column_alignment` scores to reflect the automatically inferred slanted region axis.
- Added `path_region_touch_ratio` to `path_connectivity`, reporting how many region records the current path placeholder touches.
- This reduces manual axis annotation for slanted regions, but still does not implement:
  - PCA / oriented minimum bounding box for complex irregular regions;
  - real negative-space graph extraction;
  - medial-axis or visibility graph routing.

2026-07-06, entry-to-region reachability proxy pass:

- Added `entry_to_region_reachability` to `path_connectivity`.
- The current score combines:
  - entry/path touch coverage;
  - path/region touch coverage.
- This is a minimal entry -> path -> region graph proxy, not a final navigation graph.
- Still open:
  - build a true graph with nodes for entries, path junctions, openings, and regions;
  - compute shortest path, detour ratio, dead ends, loops, and width continuity;
  - split walk graph and visibility graph.

2026-07-06, path graph evidence proxy pass:

- `evaluate_scene(scene)` now returns `matrix["graph"]` with explicit path graph evidence proxy records.
- The graph contains:
  - entry nodes;
  - path nodes;
  - region nodes;
  - `entry_path_touch` edges;
  - `path_region_touch` edges.
- `path_connectivity` evidence now references graph edge ids for touch and reachability proxy rows, instead of only listing touched object ids.
- Re-executed `test/floorplan_order_matrix_demo.ipynb` after adding graph evidence.
- Verified:
  - `pixi run pytest test/test_floorplan_scene_loader.py::test_evaluate_scene_returns_path_graph_evidence -q`
  - `pixi run pytest test/test_floorplan_scene_loader.py -q`
  - `pixi run pytest test/ -q`
  - `pixi run python -c "...nbformat/nbclient execution..."`
- This is still bbox-touch graph evidence, not a navigation graph.
- Still open:
  - derive walkable negative-space geometry;
  - split walk and visibility graphs;
  - compute shortest path, detour ratio, dead ends, loops, and width continuity;
  - account for boundary walk/see weights in graph edges.

2026-07-06, method decision ledger pass:

- Added `docs/indoor_layout_evaluation_matrix_method_ledger.md`.
- Recorded source-backed decisions for:
  - OCTA;
  - isovist / Visibility Graph Analysis;
  - space syntax graph metrics;
  - straight skeleton / medial-axis / Voronoi path extraction;
  - perceptual grouping and uniform connectedness;
  - RhinoCommon / Grasshopper / VisualARQ adapter boundaries.
- Current decision:
  - adopt OCTA only for comparable local order views;
  - keep current path graph as bbox-touch graph evidence;
  - defer real walk/visibility graph metrics until negative-space geometry exists;
  - keep Rhino/GH/VisualARQ as adapter layers around neutral records.

2026-07-06, path graph overlay pass:

- `scene_metric_overlay_svg(scene, matrix)` now draws:
  - `data-layer="path-graph-node"` circles for entry/path/region graph nodes;
  - `data-layer="path-graph-edge"` dashed lines for bbox-touch graph edges.
- The overlay includes graph edge ids in SVG attributes/titles so notebook evidence can be traced back to `path_connectivity` row evidence.
- This improves evidence inspection only. It does not change the current path scores and still does not claim real navigation, shortest path, detour, or visibility metrics.

2026-07-06, SVG path endpoint parsing fix:

- Fixed the structured SVG loader's path bbox proxy for arc commands.
- Root cause: the previous path parser used a raw number regex, so SVG arc radius/flag values such as `A95 95 0 0 1 505 835` were misread as coordinate points.
- The loader now extracts fixture path endpoints for `M/L/H/V/A/Z` commands and uses arc endpoints rather than arc parameters for bbox evidence.
- Verified `bottom_entry` and `right_entry_arc` now have bbox centers near the authored door arcs.
- This remains endpoint/bbox geometry, not exact curve geometry or CAD boolean geometry.

2026-07-06, walk/visibility graph namespace pass:

- `evaluate_scene(scene)` now returns `matrix["graphs"]` with two modal graph namespaces:
  - `matrix["graphs"]["walk"]`;
  - `matrix["graphs"]["visibility"]`.
- The legacy `matrix["graph"]` remains as shared bbox-touch evidence for existing notebook/tests.
- Modal edges now carry:
  - `mode="walk"` plus `walk_cost`;
  - `mode="visibility"` plus `visibility_cost`.
- Added `path_connectivity.walk_visibility_cost_gap`, currently computed from authored boundary/opening `walk_block` and `see_block` weights.
- Current fixture score: `0.0708`.
- This is a graph-evidence interface, not a final spatial analysis engine:
  - no negative-space polygon extraction yet;
  - no true visibility graph / isovist sampling yet;
  - shortest path, detour, loop, dead-end, and width-continuity rows remain proxy descriptors until the graph is derived from negative-space geometry.

2026-07-06, basic graph topology metrics pass:

- Added minimal graph statistics over the current bbox-touch walk graph:
  - `graph_entry_region_reachability`;
  - `graph_entry_region_capacity_proxy`;
  - `graph_mean_entry_region_hops`;
  - `graph_dead_end_ratio`;
  - `graph_loop_count`;
  - `graph_loop_ratio`.
- `matrix["graphs"]["walk"]["metrics"]` and `matrix["graphs"]["visibility"]["metrics"]` now expose the same topology keys for their modal graph namespaces.
- `path_connectivity.graph_dead_end_ratio` now exposes `dead_end_nodes` with node id, kind, and degree.
- Current fixture values:
  - entry-region reachability: `0.7143`;
  - entry-region capacity proxy: `0.2386`;
  - mean entry-region hops: `2`;
  - dead-end ratio: `0.9167`;
  - loop count: `0`;
  - loop ratio: `0.0`.
- Important boundary:
  - capacity proxy is `reachability * path_width_continuity * walk_passability`, not max-flow or route capacity;
  - hop count is graph edge count, not metric walking distance;
  - dead ends are degree counts in the proxy graph, not extracted path termini;
  - loop count and loop ratio are undirected cycle-rank descriptors on bbox-touch evidence, not circulation loop analysis.
- Still open:
  - negative-space polygon graph;
  - shortest path / detour ratio from continuous geometry;
  - path width continuity;
  - true visibility graph / isovist metrics.

2026-07-06, path width-continuity geometry pass:

- `evaluate_scene(scene)` now returns `matrix["path_geometry"]`.
- Current descriptor for `path_placeholder`:
  - `width_samples`: `[305.0, 150.0, 90.0, 65.0]`;
  - `width_continuity`: `0.6204`.
- Added metric row:
  - `path_connectivity.path_width_continuity`.
- Current method is intentionally small:
  - infer local width samples from adjacent edges of the authored path polygon;
  - score continuity with the existing coefficient-of-variation score.
- Important boundary:
  - this is a continuous-geometry descriptor, but not a medial-axis width field;
  - it does not compute minimum clearance against furniture/boundaries;
  - it does not yet support curved paths or path junction widths.

2026-07-06, proxy shortest-path and detour pass:

- Added Dijkstra-based proxy distance metrics over the current bbox-touch walk graph:
  - `graph_mean_entry_region_shortest_distance`;
  - `graph_mean_entry_region_detour_ratio`.
- `matrix["graphs"]["walk"]["metrics"]` now includes:
  - `entry_region_mean_shortest_distance`: `581.1641`;
  - `entry_region_mean_detour_ratio`: `2.8983`.
- These metrics use Euclidean distances between graph node centers as edge weights.
- Important boundary:
  - this is not a true walking shortest path;
  - the detour ratio is proxy graph length divided by direct node distance;
  - a high ratio can reveal suspicious proxy geometry, but it is not yet a final circulation judgment.
- Still open:
  - derive negative-space graph edges from actual clearance geometry;
  - route around blockers instead of through node-center proxy edges;
  - compute detour against continuous path/network length.

2026-07-06, path clearance proxy pass:

- Corrected `path_connectivity.entry_path_placeholder` to use authored path polygon area instead of path bbox area.
  - Current fixture score changed from bbox proxy `0.2409` to polygon-area ratio `0.1463`.
- Added a path polygon-to-blocker clearance proxy to `evaluate_scene(scene)`.
- `matrix["path_geometry"]["path_placeholder"]` now includes:
  - `clearance_samples`;
  - `min_clearance_to_blocker`;
  - `mean_clearance_to_blocker`.
- Added metric row:
  - `path_connectivity.path_min_clearance_to_blocker`.
- Added path blocker overlap ratio:
  - `path_connectivity.path_blocker_overlap_ratio`.
  - `path_connectivity.path_blocker_overlap_area_ratio` for path blocker overlap area ratio.
- Added overlay evidence:
  - `scene_metric_overlay_svg()` now draws `data-layer="path-blocker-conflict"` lines for zero-gap path/blocker samples.
  - conflict lines now include `data-overlap-area` and scale stroke width from overlap area.
- Current fixture result:
  - `path_min_clearance_to_blocker`: `0.0`;
  - `path_blocker_overlap_ratio`: `0.4231`;
  - `path_blocker_overlap_area_ratio`: `0.1828`;
  - evidence includes `path_placeholder` and overlapping blocker records such as `center_misc_fixture`.
- Important boundary:
  - this uses authored path polygon edges against furniture and blocking boundary bboxes, with bbox fallback for non-polygon paths;
  - it is a blocker proximity warning, not a medial-axis clearance field;
  - this original overlap area was summed over blocker bboxes and could double-count overlapping blockers;
  - it does not derive true walkable negative-space polygons or route around blockers.
- Still open:
  - true negative-space polygon extraction;
  - blocker-aware route graph construction;
  - medial-axis or skeleton clearance width sampling;
  - fixture variants where a path is close to but not overlapping blockers.

2026-07-06, path blocker-union overlap area pass:

- Tightened authored path overlap area so `path_blocker_overlap_area_ratio` uses blocker union overlap area instead of summed per-blocker overlap.
- Kept `summed_blocker_overlap_area` in `matrix["path_geometry"][path_id]` as diagnostic evidence.
- Method name:
  - `path_polygon_blocker_union_overlap_area`.
- Added an overlapping-rect-blocker path regression:
  - path area: `10000.0`;
  - summed blocker overlap area: `7200.0`;
  - de-duplicated blocker union overlap area: `4800.0`;
  - `path_blocker_overlap_area_ratio`: `0.48`.
- Current fixture path descriptor:
  - `blocker_overlap_area`: `26748.0`;
  - `summed_blocker_overlap_area`: `26748.0`;
  - `blocker_overlap_area_ratio`: `0.1828`.
- Important boundary:
  - this removes aggregate double-counting for authored path overlap warnings;
  - it is still a path-polygon/blocker proxy, not negative-space conflict geometry or route certification.

2026-07-06:

- Saved the original long-form task prompt.
- Existing SVG fixture already approximates the supplied floor plan:
  - north repeated table-chair groups;
  - west lounge with two sofas and one coffee table;
  - center lower area with two sofa groups;
  - east lower small armchairs and coffee table;
  - east work/podium-like furniture;
  - north small table;
  - room boundary, door hints, candidate regions.
- Next: write the main technical specification and test plan.

2026-07-06, pass 2:

- Added `docs/indoor_layout_evaluation_matrix_spec.md`.
- The spec now includes:
  - project goal;
  - core concept table;
  - data structures;
  - hierarchy model;
  - evaluation matrix;
  - no-hard-threshold strategy;
  - resolution/unit design;
  - implementation flow;
  - IPYNB test plan;
  - Rhino / Grasshopper / BIM migration plan;
  - uncertainty register;
  - current fixture interpretation;
  - next implementation plan.
- Important distinction: the notebook is currently specified, not yet implemented.

2026-07-06, pass 3:

- Added `docs/indoor_layout_evaluation_matrix_notebook_test_plan.md`.
- Linked the notebook plan from the main spec.
- The notebook plan explicitly states:
  - use the current SVG fixture;
  - manually declare objects first;
  - output a metric matrix table;
  - separate OCTA-compatible table order from sofa/group geometry metrics;
  - include uncertainty rows;
  - avoid automatic image recognition in the first slice.

2026-07-06, failed completion audit:

- Required files exist:
  - `docs/indoor_layout_evaluation_matrix_original_prompt.md`
  - `docs/indoor_layout_evaluation_matrix_spec.md`
  - `docs/indoor_layout_evaluation_matrix_notebook_test_plan.md`
  - `test/floorplan_order_fixture.svg`
- Completion claim was premature. Existing documents are a v0.1 scaffold, not the full requested deliverable.
- Gaps to close:
  - theory/method search is only lightly cited; it does not yet explain which methods are adopted, rejected, or deferred;
  - metrics are named but not specified with enough formulas, inputs, outputs, normalization, and failure modes;
  - no sufficiently explicit treatment of path/region split, positive-negative space, and boundary cue ambiguity;
  - notebook plan is useful but still not detailed enough to implement without further design decisions;
  - Rhino / Grasshopper / BIM migration needs more precise object and data-tree mappings;
  - uncertainty register needs decision paths: paper search, perception experiment, user parameter, or continuous output;
  - current spec does not yet answer every "咋整" issue at the requested technical depth.
- Current status: continue improving; do not mark complete.

2026-07-06, pass 4:

- Reopened the work after the premature completion claim.
- Added stronger technical content to `docs/indoor_layout_evaluation_matrix_spec.md`:
  - method selection matrix;
  - metric cards with inputs, outputs, formulas, normalization, and failure modes;
  - positive/negative space protocol;
  - path-likeness and region split formula;
  - region construction protocol;
  - fixture object table;
  - validation and perception-experiment route;
  - concrete next work items.
- Expanded `docs/indoor_layout_evaluation_matrix_notebook_test_plan.md`:
  - executable notebook skeleton;
  - fixture object declarations;
  - minimal metric helper functions;
  - first metric matrix rows;
  - required output table;
  - overlay requirements.
- Current status: v0.2 technical deliverable. It is materially stronger than v0.1, but should still be reviewed against the original prompt before any completion claim.

2026-07-06, pass 5:

- Added `docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md`.
- Added more spec sections:
  - section 21: reverse analysis and forward design protocol;
  - section 22: whole-space force aggregation recipe;
  - section 23: Rhino / Grasshopper / VisualARQ / BIM adapter payload examples;
  - section 24: uncertainty decision table;
  - section 25: final deliverables checklist.
- Updated the coverage audit so each original prompt requirement maps to evidence.
- Current status: v0.3 documentation-level deliverable. Remaining strategic question: whether this goal requires an actual executable notebook now, or whether the notebook test plan is sufficient for this documentation milestone.

2026-07-06, pass 6:

- Added executable notebook fixture: `test/floorplan_order_matrix_demo.ipynb`.
- Executed notebook with `nbformat` / `nbclient` and saved outputs.
- Verification result:
  - 7 cells;
  - 2 SVG outputs;
  - 2 HTML table outputs;
  - source contains `north_tables_order`, `west_lounge_geometry`, `center_lounge_geometry`, `east_armchair_geometry`, `uncertainties`, and `floorplan_order_fixture.svg`.
- Updated spec, notebook test plan, and prompt coverage audit to reference the executed notebook.
- Current status: v0.4 with actual fixture notebook. Do a final prompt-level completion audit before any completion claim.

2026-07-06, uncertainty-route matrix pass:

- Added `uncertainties.uncertainty_routes`.
- The row scans declared metric uncertainty text and summarizes four action routes:
  - `geometry_upgrade`;
  - `perception_experiment`;
  - `bim_mapping`;
  - `method_replacement`.
- Current fixture score: `4`, meaning all four route classes are present in the prototype matrix.
- The notebook audit now prints the route list, so unresolved method choices are visible in executable evidence instead of only in prose.
- Important boundary:
  - route assignment is keyword-based over already declared uncertainty strings;
  - it is a triage ledger, not a validation method or literature substitute.

2026-07-06, superseded final completion audit:

- Verified deliverable files exist:
  - `docs/indoor_layout_evaluation_matrix_original_prompt.md`
  - `docs/indoor_layout_evaluation_matrix_spec.md`
  - `docs/indoor_layout_evaluation_matrix_notebook_test_plan.md`
  - `docs/indoor_layout_evaluation_matrix_prompt_coverage_audit.md`
  - `test/floorplan_order_fixture.svg`
  - `test/floorplan_order_matrix_demo.ipynb`
- Verified prompt coverage audit has no unresolved coverage items.
- Verified notebook execution evidence:
  - 7 cells;
  - 2 SVG outputs;
  - 2 HTML table outputs;
  - required view/source tokens present.
- Verified spec includes:
  - theory/method selection;
  - metric definitions and formulas;
  - operation flow;
  - fixture/notebook route;
  - Rhino / Grasshopper / BIM migration route;
  - uncertainty and validation route;
  - next work items.
- Superseded status: documentation plus executable fixture notebook satisfied only a documentation/prototype milestone. It does not satisfy the full automatic evaluation matrix goal.

2026-07-06, sampled-resolution disclosure pass:

- Added `path_connectivity.sampled_grid_resolution` so the evaluator reports the sampled grid cell size used by walkability/visibility proxy rows.
- Current fixture score: `55.0` scene units per sampled cell.
- This answers the prompt's "resolution/unit" concern only at the disclosure level:
  - the sampled grid unit is visible in the metric matrix;
  - it now adapts to the median shortest furniture side when measurable furniture exists;
  - it is not yet adaptive to human body, path width, column grid, or BIM/Rhino units;
  - half/base/double sampled sensitivity is now reported separately;
  - robust adaptive multi-resolution validation remains open.

2026-07-06, sampled-resolution adaptive default pass:

- Changed `_sampled_walkable_space(scene)` so omitted resolution uses current layout scale instead of an unconditional 50-unit default.
- Added a synthetic regression where a 100x100 scene with one 20x20 furniture object reports `resolution=20.0`.
- Kept explicit resolution overrides and no-furniture fallback behavior intact, so older synthetic domain tests still use 50 scene units.
- Current default rule is intentionally simple: median shortest side of measurable furniture, or 50 scene units if no measurable furniture exists.
- Still open:
  - human-body/profile scale;
  - path-width and column-grid scale;
  - Rhino/BIM model-unit normalization;
  - full multi-resolution validation beyond the current half/base/double sampled-ratio range.

2026-07-06, sampled-resolution evidence pass:

- Added `resolution_basis` and `resolution_evidence` to `matrix["sampled_walkable_space"]`.
- `path_connectivity.sampled_grid_resolution` now uses the same evidence ids instead of only reporting scene size.
- Current fixture basis: `median_shortest_furniture_side`.
- Current fixture evidence includes the 55-unit furniture records that selected the median scale.
- This makes the chosen sampled unit inspectable, but it is still a proxy policy rather than a validated ergonomic or BIM unit standard.

2026-07-06, sampled-resolution sensitivity pass:

- Added `matrix["sampled_walkable_space"]["resolution_sensitivity"]`.
- Added `path_connectivity.sampled_resolution_sensitivity`.
- The metric reports the max range across selected sampled ratios at half/base/double cell sizes:
  - `entry_reachable_cell_ratio_range`;
  - `entry_reachable_region_ratio_range`;
  - `path_reachable_region_ratio_range`.
- Current fixture tested resolutions: `27.5`, `55.0`, and `110.0` scene units.
- Current fixture score: `0.1329`, driven by `entry_reachable_cell_ratio_range`.
- This is a sensitivity disclosure for sampled proxy rows, not CAD boolean validation, navmesh validation, human-scale calibration, or BIM/Rhino unit normalization.

2026-07-06, axis-evidence pass:

- Added `axis_evidence` to `region_alignment` rows.
- Added `region_axis_evidence` and `column_axis_evidence` to `column_alignment` rows.
- Each axis descriptor records:
  - source record id;
  - selected angle;
  - basis: `authored_axis_angle`, `polygon_pca_axis`, `polygon_longest_edge`, or `bbox_long_axis`.
- Current slanted fixture region reports `basis="polygon_pca_axis"` and angle `26.5651`.
- This makes local-axis scoring auditable, but does not yet replace bbox fallback with minimum oriented bounding box or local field interpolation for irregular/multi-direction regions.

2026-07-06, whole-space-force evidence pass:

- Added `axis_evidence` to the `whole_space_force.group_axis_concentration` row.
- Each group-axis descriptor records:
  - group id;
  - selected bbox long-axis angle;
  - basis: `group_bbox_long_axis`;
  - member count.
- This makes the current whole-space force proxy inspectable, but it is still only a furniture-group bbox axis histogram.
- Still open:
  - weighted combination with region axes, path tangents, boundary axes, and column-grid axes;
  - local force maps by region;
  - multi-direction/global-vs-local force reporting.

2026-07-06, whole-space-force column agreement pass:

- Added `whole_space_force.group_column_axis_agreement`.
- The row compares furniture group bbox axes against available column-grid axes using the same continuous axis-pair score as region/column alignment.
- Current fixture score: `1.0`, because the authored column grid has both 0-degree and 90-degree axes and every current group bbox axis matches one of them.
- Evidence includes both `group_axis_evidence` and `column_axis_evidence`.
- This is still a proxy agreement row, not a full whole-space force model with path, boundary, region, and column weights.

2026-07-06, whole-space-force path agreement pass:

- Added `whole_space_force.group_path_axis_agreement`.
- The row compares furniture group bbox axes against authored path polygon axes using the same continuous axis-pair score as region/column alignment.
- Current fixture score: `1.0`, because the current path polygon's longest edge is horizontal and all group bbox axes are horizontal/vertical.
- Evidence includes both `group_axis_evidence` and `path_axis_evidence`.
- This adds path direction to the whole-space force evidence chain, but it is still a path-polygon axis proxy rather than a route field, movement model, or medial-axis tangent field.

2026-07-06, whole-space-force boundary agreement pass:

- Added `whole_space_force.group_boundary_axis_agreement`.
- The row compares furniture group bbox axes against room/internal/soft boundary axes using the same continuous axis-pair score.
- Current fixture score: `1.0`, because the current boundary evidence includes horizontal and vertical axes and all group bbox axes are horizontal/vertical.
- Evidence includes both `group_axis_evidence` and `boundary_axis_evidence`.
- This brings boundary axes into the whole-space force evidence chain, but it is still an unweighted axis-agreement proxy rather than a boundary force field with continuity, thickness, walk/see blocking, and grouping weights.

2026-07-06, weighted boundary-axis force pass:

- Added `whole_space_force.weighted_boundary_axis_concentration`.
- Current fixture score: `0.2826`.
- The row weights each boundary axis by the mean of:
  - `walk_block`;
  - `see_block`;
  - `grouping_strength`.
- This lets hard walls, glass, rugs, and material boundaries contribute differently to the boundary-force axis concentration.
- Important boundary:
  - the channel weights are authored fixture metadata;
  - this is not perception-calibrated and does not yet include boundary length/thickness weighting.

2026-07-06, length-weighted boundary-axis force pass:

- Added `whole_space_force.length_weighted_boundary_axis_concentration`.
- Current fixture score: `0.7614`.
- The row uses:
  - boundary axis;
  - boundary length;
  - mean authored `walk_block` / `see_block` / `grouping_strength` weight;
  - `influence = length * weight`.
- This shows how long room/wall boundaries dominate the current boundary-force axis field compared with short soft/material boundaries.
- Important boundary:
  - lengths are parsed polyline length or bbox long side fallback;
  - curved length, thickness, and calibrated perceptual weights are still pending.

2026-07-06, thickness-weighted boundary-axis force pass:

- Added `whole_space_force.thickness_weighted_boundary_axis_concentration`.
- Current fixture score: `0.8463`.
- The row uses:
  - boundary axis;
  - boundary length;
  - authored `data-thickness`;
  - mean authored `walk_block` / `see_block` / `grouping_strength` weight;
  - `influence = length * thickness * weight`.
- Current evidence includes:
  - `room_boundary`: length `3720.0`, thickness `8.0`, influence `29760.0`;
  - `glass_boundary`: length `305.0`, thickness `3.0`, influence `625.25`;
  - `rug_boundary` and `material_boundary`: thickness `0.0`, influence `0.0`.
- Implementation note:
  - influence is computed from raw length and raw channel weight, then rounded once, so chained rounding does not drift evidence values.
- Important boundary:
  - thickness is authored fixture metadata, not inferred from SVG stroke width;
  - curved length and perception-calibrated channel weights are still pending.

2026-07-06, boundary entrance-width evidence pass:

- Added `boundary_metrics.entry_width_mean`.
- Current fixture score: `93.75` scene units.
- The row reports per-entry evidence with:
  - entry id;
  - authored edge label;
  - bbox max dimension as current opening-width proxy;
  - bbox center as current opening-location proxy.
- This directly addresses the prompt's boundary questions about entrance width and location at the structured-SVG level.
- Important boundary:
  - width is currently derived from the parsed opening bbox, not true arc length, clear door width, or wall-hosted BIM opening geometry;
  - future Rhino/BIM adapters should prefer explicit door/opening width attributes or curve length when available.

2026-07-06, boundary thickness metadata pass:

- Added authored `data-thickness` metadata to structured boundary fixtures.
- Added `boundary_metrics.boundary_thickness_mean`.
- Current fixture score: `4.4444` scene units.
- Thickness evidence:
  - room/wall boundaries: `8.0`;
  - internal partition: `5.0`;
  - glass boundary: `3.0`;
  - rug/material/visual boundaries: `0.0`.
- This directly covers the prompt's "是否有厚度 / 厚度是多少" boundary requirement at structured-SVG level.
- Important boundary:
  - thickness is authored metadata, not inferred from SVG stroke width;
  - future Rhino/BIM adapters should prefer wall/door/material object thickness.

2026-07-06, entry-path opening evidence pass:

- Extended `path_connectivity.entry_touch_ratio` with `entry_touch_evidence`.
- The evidence now lists every opening, its authored edge, its current width proxy, and the path ids it touches.
- Current fixture evidence:
  - `bottom_entry` and `right_entry_arc` touch `path_placeholder`;
  - `left_entry` and `right_entry_line` do not touch the current path placeholder.
- This connects entrance location/width evidence to path connectivity, but it is still bbox-touch evidence rather than a true doorway-to-negative-space graph.

2026-07-06, entry path-boundary evidence join pass:

- Enriched `path_connectivity.entry_touch_ratio.entry_touch_evidence` with nearest boundary association fields:
  - `boundary_id`;
  - `boundary_gap`.
- Current fixture evidence now lets a single row answer:
  - which opening touches the path proxy;
  - how wide that opening is;
  - which authored boundary it belongs to by nearest geometry;
  - how far the opening center is from that boundary.
- Current path-touch result is unchanged:
  - `bottom_entry` and `right_entry_arc` touch `path_placeholder`;
  - `left_entry` and `right_entry_line` do not.
- Important boundary:
  - path touching is still bbox contact;
  - boundary association is still nearest parsed SVG geometry, not hosted BIM topology.

2026-07-06, disconnected-entry matrix pass:

- Added `path_connectivity.disconnected_entry_ratio`.
- Added `path_connectivity.disconnected_path_ratio`.
- The row reports openings that do not touch the current path proxy, reusing `entry_touch_evidence`.
- Current fixture score: `0.5`.
- Current fixture disconnected openings:
  - `left_entry`;
  - `right_entry_line`.
- This makes disconnected entry evidence visible as a direct matrix row, while `boundary_metrics.boundary_path_connected_opening_ratio_max` keeps the per-boundary grouping view.
- Current `disconnected_path_ratio` fixture score: `0.0`; `path_placeholder` touches `bottom_entry` and `right_entry_arc`.
- Important boundary:
  - this is still bbox path contact;
  - hosted doorway topology and negative-space graph routing remain pending.

2026-07-06, opening-width continuity proxy pass:

- Added `boundary_metrics.opening_width_room_perimeter_ratio`.
- Current fixture score: `0.1027`.
- Formula: sum of opening bbox max dimensions divided by the room-boundary bbox perimeter.
- This gives a continuous opening/continuity descriptor instead of judging whether the boundary is "open enough".
- Important boundary:
  - room perimeter is currently the room boundary bbox perimeter;
  - irregular/curved rooms need true boundary curve length from SVG/Rhino/BIM geometry.

2026-07-06, opening-width boundary-length pass:

- Added `boundary_metrics.opening_width_room_boundary_length_ratio`.
- Current fixture score: `0.1008`.
- Formula: sum of opening bbox max dimensions divided by parsed room-boundary polyline length.
- Current room-boundary polyline length: `3720.0` scene units.
- This improves the opening-continuity descriptor for non-rectangular room outlines.
- Important boundary:
  - the length uses parsed SVG path command endpoints;
  - curved walls and arcs still need curve-aware length from SVG/Rhino/BIM geometry.

2026-07-06, entry boundary-position pass:

- Added `boundary_metrics.entry_boundary_position_coverage`.
- Current fixture score: `0.5289`.
- The row projects each entry center to the nearest room-boundary polyline segment and records:
  - along-boundary distance;
  - normalized boundary ratio;
  - projected point;
  - projection gap.
- This turns "入口在哪里" into continuous boundary-parameter evidence instead of only a 2D center point.
- Important boundary:
  - projection is to parsed SVG polyline segments;
  - curved walls/openings need curve-aware projection from SVG/Rhino/BIM geometry.

2026-07-06, entry-to-boundary association pass:

- Added `boundary_metrics.entry_nearest_boundary_gap_mean`.
- Current fixture score: `31.25` scene units.
- The row records, for each opening:
  - current width proxy;
  - opening center;
  - nearest authored boundary id and kind;
  - nearest projected point;
  - center-to-boundary gap.
- Current fixture associations:
  - `left_entry`, `bottom_entry`, `right_entry_arc`, and `right_entry_line` all associate to `room_boundary`;
  - gaps are `17.5`, `47.5`, `60.0`, and `0.0` scene units.
- This turns "入口属于哪条边界 / 离边界多远" into explicit evidence instead of relying only on the authored `data-edge` label.
- Important boundary:
  - association uses nearest geometry from parsed SVG records;
  - Rhino/BIM adapters should replace this with hosted opening relationships on wall/room objects.

2026-07-06, explicit opening-width metadata pass:

- Updated `boundary_metrics.entry_width_mean` to use `opening_width_metadata_or_rect_max_dimension_mean`.
- Opening width now prefers explicit `opening-width`, `opening_width`, or `width` metadata, then falls back to the opening bbox max dimension.
- Each opening descriptor and entry-boundary association records `width_source`:
  - `opening_width_metadata` for explicit authored/BIM adapter width;
  - `opening_bbox_max_dimension` for current fixture fallback geometry.
- Current fixture score remains `93.75` because the fixture still uses bbox-derived opening widths.
- Added a synthetic regression where a 20-unit bbox opening with `opening-width="90"` reports width `90.0`, `width_source="opening_width_metadata"`, and updates the boundary opening ratio from metadata.
- Important boundary:
  - this is an adapter contract for authored openings;
  - true curve length, hosted wall topology, and door-family semantics still belong in SVG/Rhino/BIM adapters.

2026-07-06, per-boundary opening ratio pass:

- Added `boundary_metrics.boundary_opening_width_ratio_max`.
- Current fixture score: `0.1008`.
- The row groups openings by their nearest authored boundary association and reports per-boundary evidence:
  - boundary id and kind;
  - parsed boundary length;
  - sum of associated opening widths;
  - `opening_ratio = opening_width / boundary_length`;
  - associated opening ids.
- Current fixture evidence:
  - `room_boundary`: length `3720.0`, opening width `375.0`, opening ratio `0.1008`;
  - `glass_boundary`, `rug_boundary`, and `material_boundary`: no associated openings, opening ratio `0.0`.
- This keeps "boundary continuity / opening load" local to each boundary instead of only reporting a room-level aggregate.
- Important boundary:
  - opening association still uses nearest parsed SVG geometry;
  - hosted openings and true curve lengths should replace this proxy in Rhino/BIM.

2026-07-06, per-boundary path-connected opening pass:

- Added `boundary_metrics.boundary_path_connected_opening_ratio_max`.
- Current fixture score: `0.5`.
- The row groups openings by associated boundary, then reports:
  - number of associated openings;
  - number of associated openings that touch the current path proxy;
  - `path_connected_opening_ratio`;
  - all opening ids, path-connected opening ids, and `path_disconnected_opening_ids`.
- Current fixture evidence:
  - `room_boundary`: four associated openings, two path-connected openings (`bottom_entry`, `right_entry_arc`), ratio `0.5`;
  - `room_boundary.path_disconnected_opening_ids`: `left_entry` and `right_entry_line`;
  - other authored boundaries have no associated openings and ratio `0.0`.
- This separates "a boundary has openings" from "those openings actually connect to the path proxy".
- Important boundary:
  - path-connected opening uses bbox path contact;
  - true doorway-to-negative-space graph remains pending.

2026-07-06, slanted line-boundary evidence pass:

- Added `diagonal_boundary`, a 45-degree authored visual boundary, to the structured SVG fixture.
- Extended the structured SVG loader so `<line>` elements expose their two endpoint `points`, not only their bbox.
- Current evidence:
  - `diagonal_boundary`: points `[(635.0, 305.0), (825.0, 495.0)]`;
  - `group_boundary_axis_agreement.boundary_axis_evidence`: angle `45.0`, basis `polygon_longest_edge`;
  - `length_weighted_boundary_axis_concentration`: length `268.7006`, weight `0.2`, influence `53.7401`.
- This makes boundary-force evidence nontrivial beyond horizontal/vertical boundary axes.
- Important boundary:
  - this is still a straight-line SVG fixture case;
  - curved or segmented boundaries still need curve-aware geometry from SVG/Rhino/BIM.

2026-07-06, region-boundary axis agreement pass:

- Added `region_alignment.region_boundary_axis_agreement`.
- Current fixture score: `0.9714`.
- The row matches each measurable region axis to its best boundary axis using the same continuous axis similarity used elsewhere.
- Current evidence:
  - orthogonal regions match available horizontal/vertical room or wall boundaries with score `1.0`;
  - `region_slanted_test` has PCA angle `26.5651` and now matches `diagonal_boundary` at `45.0` with score `0.8`.
- This connects slanted region local frame evidence to slanted boundary evidence without adding a hard angle threshold.
- Important boundary:
  - this is axis-only agreement;
  - it does not yet weight boundary distance, containment, continuity, thickness, or cue strength.

2026-07-06, region-scoped boundary axis agreement pass:

- Added `region_alignment.region_source_boundary_axis_agreement`.
- Current fixture score: `0.9333`.
- Unlike the global boundary-axis match, this row only compares a region with boundaries carrying the same authored `data-region`.
- Current fixture evidence:
  - `region_west_lounge` matches `rug_boundary` with score `1.0`;
  - `region_center_lounge` matches `glass_boundary` with score `1.0`;
  - `region_slanted_test` matches `diagonal_boundary` with score `0.8`.
- Regions without same-region boundary metadata are omitted instead of receiving a fake zero or global-best match.
- Important boundary:
  - this depends on authored region labels;
  - it still does not model boundary distance, containment, continuity, thickness, or cue strength.

2026-07-06, weighted region-scoped boundary axis pass:

- Added `region_alignment.region_source_boundary_weighted_axis_agreement`.
- Current fixture score: `0.9333`.
- The row compares each region axis to same-`data-region` boundaries and weights every boundary contribution by:
  - parsed boundary length;
  - authored `grouping_strength`;
  - `influence = length * grouping_strength`.
- Current fixture evidence:
  - `region_west_lounge`: `rug_boundary`, total influence `255.0`, score `1.0`;
  - `region_center_lounge`: `glass_boundary` influence `274.5` and `material_boundary` influence `154.0`, score `1.0`;
  - `region_slanted_test`: `diagonal_boundary` influence `161.2203`, score `0.8`.
- This starts separating weak/short same-region cues from stronger/longer boundary cues while keeping output continuous.
- Important boundary:
  - `grouping_strength` is authored metadata, not calibrated perception;
  - distance, containment, continuity, and thickness are still not part of this row.

2026-07-06, region-scoped boundary proximity pass:

- Added `region_alignment.region_source_boundary_proximity`.
- Current fixture score: `0.9964`.
- The row uses same-`data-region` boundaries and reports a continuous bbox-gap proximity:
  - `gap = bbox distance between region and boundary`;
  - `region_scale = max(region width, region height)`;
  - `proximity = 1 / (1 + gap / region_scale)`;
  - boundary influence is still `length * grouping_strength`.
- Current fixture evidence:
  - `region_west_lounge` / `rug_boundary`: gap `0.0`, proximity `1.0`;
  - `region_center_lounge` / `glass_boundary`: gap `5.0`, proximity `0.9833`;
  - `region_center_lounge` / `material_boundary`: gap `0.0`, proximity `1.0`;
  - `region_slanted_test` / `diagonal_boundary`: gap `0.0`, proximity `1.0`.
- This checks whether same-region boundary labels are geometrically near the region instead of trusting labels alone.
- Important boundary:
  - this is a bbox-gap proxy;
  - Rhino/BIM should replace it with curve/polygon distance, containment, and hosted boundary relationships.

2026-07-06, path-touched region boundary-cue pass:

- Added `path_connectivity.path_touched_region_boundary_cue_ratio`.
- Current fixture score: `0.4`.
- The row combines:
  - regions touched by the current path proxy;
  - whether each touched region has same-`data-region` boundary proximity evidence.
- Current fixture evidence:
  - `region_north_tables`: touched by `path_placeholder`, no same-region boundary cue;
  - `region_west_lounge`: touched by `path_placeholder`, boundary cue present with proximity `1.0`;
  - `region_center_lounge`: touched by `path_placeholder`, boundary cue present with proximity `0.9893`;
  - `region_east_work`: touched by `path_placeholder`, no same-region boundary cue;
  - `region_east_armchairs`: touched by `path_placeholder`, no same-region boundary cue.
- This starts operationalizing the prompt question "when path splits regions, can boundary pull them back together?" as explicit evidence rather than a hard split decision.
- Important boundary:
  - path touch is bbox contact;
  - boundary cue is same-region bbox proximity;
  - no automatic region split/merge decision is made yet.

2026-07-06, path-touched region boundary-cue strength pass:

- Added `path_connectivity.path_touched_region_boundary_cue_strength_mean`.
- Current fixture score: `0.3979`.
- The row reuses `path_region_boundary_cue_evidence` and computes the mean same-region boundary proximity across path-touched regions:
  - regions with a same-region boundary cue contribute their `boundary_proximity`;
  - regions without a same-region boundary cue contribute `0.0`.
- Current fixture evidence:
  - `region_north_tables`: `0.0`;
  - `region_west_lounge`: `1.0`;
  - `region_center_lounge`: `0.9893`;
  - `region_east_work`: `0.0`;
  - `region_east_armchairs`: `0.0`.
- This complements `path_touched_region_boundary_cue_ratio`:
  - the ratio asks how many touched regions have a cue;
  - the strength mean asks how strong those cues are after missing cues are counted.
- Important boundary:
  - this is still bbox path-region touch plus same-region bbox proximity;
  - it is not a region split/merge decision, route continuity score, or calibrated perceptual grouping model.

2026-07-06, path-touched region boundary-cue perimeter influence pass:

- Added `path_connectivity.path_touched_region_boundary_cue_perimeter_influence_mean`.
- Current fixture score: `0.1209`.
- The row reuses same-region boundary proximity evidence and exposes boundary cue amount as:
  - `boundary_total_influence = sum(boundary_length * grouping_strength)` for same-region boundary cues;
  - `boundary_influence_per_region_perimeter = boundary_total_influence / region_bbox_perimeter`.
- Current path-touched fixture evidence:
  - `region_north_tables`: no same-region cue, normalized influence `0.0`;
  - `region_west_lounge`: influence `255.0`, normalized influence `0.2318`;
  - `region_center_lounge`: influence `428.5`, normalized influence `0.3726`;
  - `region_east_work`: no same-region cue, normalized influence `0.0`;
  - `region_east_armchairs`: no same-region cue, normalized influence `0.0`.
- This complements proximity strength:
  - proximity asks whether the cue sits near the region;
  - perimeter-normalized influence asks how much same-region boundary cue exists relative to region scale.
- Important boundary:
  - region bbox perimeter is a scale proxy, not true region perimeter;
  - grouping strength is authored metadata, not calibrated perception;
  - this does not decide whether a path split should be merged back into one region.

2026-07-06, path-touched region boundary-cue identity pass:

- Added `boundary_cue_ids`, `boundary_cue_kinds`, and `boundary_cue_count` to `path_region_boundary_cue_evidence`.
- Added `path_connectivity.path_touched_region_boundary_cue_count_mean`.
- Current fixture score: `0.6`.
- Current path-touched cue identity evidence:
  - `region_north_tables`: no same-region boundary cue;
  - `region_west_lounge`: `rug_boundary` with kind `rug`;
  - `region_center_lounge`: `glass_boundary` with kind `glass`, `material_boundary` with kind `material`;
  - `region_east_work`: no same-region boundary cue;
  - `region_east_armchairs`: no same-region boundary cue.
- This makes the path/region/boundary coupling traceable to concrete boundary records instead of only reporting aggregate proximity.
- Important boundary:
  - `boundary_cue_kinds` comes from authored `data-boundary-kind` metadata, not material recognition;
  - cue count is evidence identity, not quality;
  - one strong continuous boundary and two weak fragmented boundaries should not be treated as equivalent without later continuity/calibration metrics.

2026-07-06, path-touched region boundary grouping-strength pass:

- Added `boundary_grouping_strength` to `path_region_boundary_cue_evidence`.
- Added `path_connectivity.path_touched_region_boundary_grouping_strength_mean`.
- Current fixture score: `0.3165`.
- Formula:
  - for each path-touched region with same-region boundary cues, compute length-weighted authored `grouping_strength`;
  - path-touched regions without same-region boundary cues contribute `0.0`;
  - mean the result across path-touched regions.
- Current path-touched region values:
  - `region_north_tables`: `0.0`;
  - `region_west_lounge`: `0.85` from `rug_boundary`;
  - `region_center_lounge`: `0.7325` from `glass_boundary` and `material_boundary`;
  - `region_east_work`: `0.0`;
  - `region_east_armchairs`: `0.0`.
- Important boundary:
  - this uses authored `grouping_strength`, not calibrated perceptual grouping;
  - boundary length comes from parsed SVG points or bbox fallback;
  - it supports later split/merge scoring but is not itself a split/merge decision.

2026-07-06, path-touched region boundary walk/see channel pass:

- Added path-touched same-region boundary channel evidence:
  - `boundary_walk_block`;
  - `boundary_see_block`;
  - `boundary_walk_see_gap`.
- Added metric rows:
  - `path_connectivity.path_touched_region_boundary_walk_block_mean`;
  - `path_connectivity.path_touched_region_boundary_see_block_mean`;
  - `path_connectivity.path_touched_region_boundary_walk_see_gap_mean`.
- Current fixture scores:
  - walk block mean: `0.1043`;
  - see block mean: `0.0156`;
  - walk/see gap mean: `0.0886`.
- Current path-touched region evidence:
  - `region_west_lounge`: rug cue has walk `0.0`, see `0.0`, grouping `0.85`;
  - `region_center_lounge`: glass/material cues have length-weighted walk `0.5214`, see `0.0782`, gap `0.4432`;
  - touched regions without same-region boundary cues contribute zero.
- Important boundary:
  - channels use authored `walk_block` and `see_block`, not visibility rays or material simulation;
  - this separates action and sight constraints for path-touched regions but still uses bbox path-region touch.

2026-07-06, path-touched region boundary cue profile pass:

- Added `boundary_cue_profiles` to `path_region_boundary_cue_evidence`.
- Each same-region cue profile now records:
  - boundary id;
  - `boundary-kind`;
  - parsed length;
  - authored `walk_block`;
  - authored `see_block`;
  - authored `grouping_strength`;
  - `influence = length * grouping_strength`.
- Current fixture examples:
  - `region_west_lounge`: `rug_boundary`, kind `rug`, grouping `0.85`, walk/see `0.0`;
  - `region_center_lounge`: `glass_boundary` plus `material_boundary`, showing glass walk/see split separately from material grouping.
- This is an explainability layer for the path/region/boundary coupling rows, not a new aggregate score.
- Important boundary:
  - profiles still use structured SVG metadata;
  - future Rhino/BIM adapters should populate these fields from object/material/hosted-boundary data rather than hand-authored SVG attributes.

2026-07-06, path-region split tendency proxy pass:

- Added `path_connectivity.path_region_split_tendency_proxy`.
- Added `path_connectivity.candidate_path_area_ratio_proxy`.
- Current fixture score: `0.3029`.
- Formula:
  - `candidate_path_area_ratio_proxy = negative_space_entry_connected_area_ratio * path_width_continuity`;
  - `path_likeness = path_region_touch_ratio * path_width_continuity`;
  - `split_tendency = path_likeness * (1 - path_touched_region_boundary_grouping_strength_mean)`.
- Current fixture inputs:
  - `negative_space_entry_connected_area_ratio`: `1.0`;
  - `path_region_touch_ratio`: `0.7143`;
  - `path_width_continuity`: `0.6204`;
  - `path_touched_region_boundary_grouping_strength_mean`: `0.3165`.
- Current fixture `candidate_path_area_ratio_proxy`: `0.6204`.
- This turns the prompt's "path separates, but boundary can pull things back together" idea into a continuous evidence row.
- It also turns "leftover space is not automatically road" into an auditable candidate-path proxy: entry connection and width continuity both have to contribute.
- Important boundary:
  - this is an existing-evidence proxy over bbox path-region touch and authored boundary grouping;
  - it is not an automatic road classifier or region split/merge decision;
  - true negative-space geometry should replace the path-likeness inputs later.

2026-07-06, candidate path region-pair proxy pass:

- Added metric row:
  - `path_connectivity.candidate_path_region_pair_ratio_proxy`.
- Formula:
  - `candidate_path_region_pair_ratio_proxy = candidate_path_area_ratio_proxy * negative_space_entry_connected_region_pair_ratio`.
- The row exposes `candidate_path_pair_inputs` so the candidate-path area proxy, same-component region-pair ratio, pair numerator, and pair denominator are auditable separately.
- Synthetic split-room regression:
  - `candidate_path_area_ratio_proxy`: `0.5`;
  - `negative_space_entry_connected_region_pair_ratio`: `0.3333`;
  - `candidate_path_region_pair_ratio_proxy`: `0.1667`.
- Current fixture:
  - `candidate_path_area_ratio_proxy`: `0.6204`;
  - `negative_space_entry_connected_region_pair_ratio`: `1.0`;
  - `candidate_path_region_pair_ratio_proxy`: `0.6204`.
- Important boundary:
  - this combines existing candidate-path area and same-component pair evidence;
  - it is not navmesh routing, shortest-path routing, route distance, route quality, or path certification.

2026-07-06, full-repo verification unblock pass:

- Added `matplotlib` to the Pixi environment because embedded OCTA tests import it directly.
- Added root `conftest.py` for pytest only:
  - puts `OCTA_toolbox-master` on `sys.path` so embedded OCTA tests can import `octa`;
  - restores cwd to the repo root after legacy OCTA test collection, because `OCTA_toolbox-master/tests/test_positions.py` calls `os.chdir('..')` at module import time.
- Added compatibility alias:
  - `Positions.CreateRandomPattern = Positions.CreateRandomPositions`;
  - this preserves the old OCTA test/API name without changing random-position generation logic.
- Verified:
  - `pixi run pytest OCTA_toolbox-master/tests/test_positions.py test/test_floorplan_scene_loader.py::test_floorplan_fixture_has_structured_metadata test/test_affordance_aisle.py::test_analyzer_does_not_own_affordance_geometry_rules -q`: `2 passed`;
  - `pixi run pytest -q`: `112 passed`;
  - `pixi run pytest test/ -q`: `112 passed`;
  - notebook execution for `test/floorplan_order_matrix_demo.ipynb`: exits `0` with the known Windows/ZMQ warning;
  - wrapper import check: `matplotlib 3.11.0` and embedded `octa` import via `features.analyzer`.
- Important boundary:
  - bare `pixi run python -c "import octa"` still does not import `octa` unless the embedded OCTA source path is added; public project usage continues through `features.analyzer` / `OrderAnalyzer` or pytest `conftest.py`.

2026-07-06, negative-space area proxy pass:

- Added `matrix["negative_space"]` with `negative_space_area_ratio_proxy`.
- Added metric row:
  - `path_connectivity.negative_space_area_ratio_proxy`.
- Original formula:
  - room area from the authored `boundary-kind="room"` polygon when available, otherwise room/scene bbox fallback;
  - blocker area from summed furniture and walk-blocking boundary bbox overlap inside that room;
  - `negative_space_area_ratio_proxy = max(0, room_area - blocker_overlap_area) / room_area`.
- Current fixture descriptor:
  - `room_area`: `806275.0`;
  - `blocker_overlap_area`: `123387.0`;
  - `negative_space_area`: `682888.0`;
  - `negative_space_area_ratio_proxy`: `0.847`.
- Added a synthetic regression guard where a `10000.0` area room and one `1000.0` area blocker produce a ratio of `0.9`.
- Important boundary:
  - this original pass summed blocker rectangles and could double-count overlaps;
  - this is not CAD boolean negative space, not a cleaned polygon set, and not a path skeleton or navigation graph;
  - it is a continuous area-balance proxy to compare with the sampled grid layer while real room-minus-blocker geometry remains pending.

2026-07-06, negative-space rect-component proxy pass:

- Added continuous rect-cell component descriptors to `matrix["negative_space"]`:
  - `component_count`;
  - `component_areas`;
  - `component_rects`;
  - `largest_component_area_ratio`;
  - `component_method = room_polygon_rect_cell_decomposition_proxy`.
- Added metric rows:
  - `path_connectivity.negative_space_component_count`;
  - `path_connectivity.negative_space_largest_component_area_ratio`.
- Added a synthetic regression where a full-height blocker splits a rectangular room into two equal `9000.0` area components.
- `component_rects` records each decomposed component bbox, `cell_count`, `cell_rects`, and area so the proxy geometry can be inspected before true CAD boolean polygons exist.
- Current fixture descriptor:
  - `component_count`: `1`;
  - `component_areas`: `[684736.0]`;
  - `largest_component_area_ratio`: `1.0`.
- Important boundary:
  - this is a continuous rectangle decomposition using blocker bbox edges and room-polygon-overlapped cell area;
  - it is not a CAD boolean polygon topology and does not produce skeleton/navmesh edges;
  - use it as bridge evidence toward explicit negative-space components only.

2026-07-06, negative-space component polygon-area clipping pass:

- Tightened `room_polygon_rect_cell_decomposition_proxy` so component areas are clipped by overlap with the room polygon.
- Added a triangular-room regression:
  - room polygon area: `5000.0`;
  - component count: `1`;
  - component area: `[5000.0]`;
  - largest component area ratio: `1.0`.
- This removes the previous room-bbox overcount for irregular rooms while keeping the implementation dependency-free.
- Important boundary:
  - component adjacency is still based on rect-cell shared edges;
  - blocker geometry supports rect and polygon blocker overlap, but still uses rect-cell decomposition;
  - this is not a full polygon boolean decomposition.

2026-07-06, negative-space polygon blocker overlap pass:

- Tightened negative-space blocker accounting so records with polygon `points` use polygon overlap instead of their full bbox.
- Component cell area now subtracts partial polygon blocker overlap inside each rect-cell.
- Added a triangular polygon blocker regression:
  - room area: `10000.0`;
  - blocker overlap area: `5000.0`;
  - negative-space area: `5000.0`;
  - component area: `[5000.0]`.
- Current fixture values before blocker-union de-duplication:
  - `blocker_overlap_area`: `123387.0`;
  - `negative_space_area_ratio_proxy`: `0.847`;
  - `component_areas`: `[684736.0]`.
- Important boundary:
  - this is polygon blocker overlap inside rect-cells, not a general polygon-polygon boolean arrangement;
  - this pass still allowed overlapping blockers to double-count in the aggregate area row;
  - true negative-space polygons/navmesh remain pending.

2026-07-06, negative-space blocker-union area pass:

- Tightened aggregate negative-space area so `blocker_overlap_area` uses rect-cell blocker union area instead of summed per-blocker overlap.
- Kept `summed_blocker_overlap_area` as diagnostic evidence for how much the old summed proxy would subtract.
- Method name:
  - `room_polygon_minus_blocker_union_area_proxy`.
- Added an overlapping-rect-blocker regression:
  - two `60 x 60` blocker bboxes overlap inside a `100 x 100` room;
  - summed blocker overlap area: `7200.0`;
  - de-duplicated blocker union area: `4800.0`;
  - component area: `[5200.0]`;
  - `negative_space_area_ratio_proxy`: `0.52`.
- Added a separate-polygon-blocker regression:
  - two non-overlapping triangle blockers share the same full-room bbox;
  - blocker union area: `5000.0`;
  - this prevents cell-level union from undercounting by taking only the largest polygon overlap.
- Added a duplicate-polygon-blocker regression:
  - two identical triangle blockers share the same geometry;
  - summed blocker overlap area: `10000.0`;
  - blocker union area: `5000.0`;
  - component area remains `[5000.0]`.
- Current fixture descriptor:
  - `blocker_overlap_area`: `121539.0`;
  - `summed_blocker_overlap_area`: `123387.0`;
  - `negative_space_area`: `684736.0`;
  - `negative_space_area_ratio_proxy`: `0.8493`.
- Important boundary:
  - this removes aggregate double-counting, handles separate polygon blockers within a rect cell, and de-duplicates identical blocker geometry;
  - it is still not CAD boolean room-minus-blocker geometry, not a navmesh, and not a cleaned polygon set.

2026-07-06, negative-space entry-connected component pass:

- Added entry connectivity descriptors to `matrix["negative_space"]`:
  - `entry_connected_component_count`;
  - `entry_connected_component_area`;
  - `entry_connected_area_ratio`;
  - `non_entry_connected_component_area`;
  - `non_entry_connected_area_ratio`;
  - `entry_component_evidence`.
- Added metric rows:
  - `path_connectivity.negative_space_entry_connected_component_count`;
  - `path_connectivity.negative_space_entry_connected_component_ratio`;
  - `path_connectivity.negative_space_entry_connected_area_ratio`;
  - `path_connectivity.negative_space_non_entry_connected_area_ratio`.
- Added a synthetic regression where a full-height wall splits a room into two equal negative-space components and a single left entry connects only one component:
  - `entry_connected_component_count`: `1`;
  - `negative_space_entry_connected_component_ratio`: `0.5`;
  - `entry_connected_component_area`: `9000.0`;
  - `entry_connected_area_ratio`: `0.5`;
  - `non_entry_connected_area_ratio`: `0.5`.
- Current fixture descriptor:
  - `entry_connected_component_count`: `1`;
  - `entry_connected_component_area`: `684736.0`;
  - `entry_connected_area_ratio`: `1.0`;
  - `non_entry_connected_area_ratio`: `0.0`;
  - all four fixture entries touch the single current negative-space component.
- Important boundary:
  - entry association is rect-touch against decomposed negative-space cells;
  - non-entry-connected area is leftover negative-space evidence, not a semantic dead-space classifier;
  - this is candidate path-space evidence, not hosted doorway topology, not shortest-path reachability, and not route certification.

2026-07-06, negative-space graph evidence pass:

- Added `matrix["negative_space_graph"]` as explicit graph-shaped evidence over the negative-space component proxy.
- Graph contents:
  - `negative_space_component` nodes for decomposed component records;
  - `entry` nodes for entry/opening records;
  - `entry_negative_space_component_touch` edges for entry-component rect-touch evidence.
- Graph `metrics` now include:
  - `node_count`;
  - `edge_count`;
  - `component_node_count`;
  - `entry_component_edge_count`;
  - `entry_connected_component_ids`;
  - `non_entry_connected_component_ids`;
  - `entry_connected_component_ratio`;
  - `component_area`;
  - `entry_connected_component_area`;
  - `non_entry_connected_component_area`;
  - `entry_connected_area_ratio`;
  - `non_entry_connected_area_ratio`;
  - `entry_connected_region_ids`;
  - `non_entry_connected_region_ids`;
  - `entry_connected_region_ratio`;
  - `entry_connected_region_pair_count`;
  - `total_region_pair_count`;
  - `entry_connected_region_pair_ratio`;
  - `entry_connected_region_pair_evidence`;
  - `unconnected_region_pair_evidence`.
- Updated `path_connectivity.negative_space_entry_connected_component_count`, `path_connectivity.negative_space_entry_connected_component_ratio`, `path_connectivity.negative_space_entry_connected_area_ratio`, and `path_connectivity.negative_space_non_entry_connected_area_ratio` so row evidence references negative-space graph edge ids.
- Current fixture graph:
  - one `negative_space_component` node;
  - four entry nodes;
  - four `entry_negative_space_component_touch` edges from `bottom_entry`, `left_entry`, `right_entry_arc`, and `right_entry_line` to component `0`.
- Important boundary:
  - this is graph-shaped traceability evidence for current component touch, not a navmesh, not a visibility graph, and not shortest-path routing.

2026-07-07, negative-space graph component geometry pass:

- Extended `negative_space_component` graph nodes with:
  - `bbox`;
  - `cell_count`;
  - `cell_rects`.
- Extended `matrix["negative_space_graph"]["metrics"]` with:
  - `component_cell_counts`;
  - `component_cell_area_sums`;
  - `component_cell_area_residuals`;
  - `max_component_cell_area_residual_ratio`.
- These fields are copied from `component_rects`, so graph consumers can inspect each component's proxy geometry without separately joining back to `matrix["negative_space"]`.
- Added a split-room regression where the two component nodes expose:
  - left component bbox `(0.0, 0.0, 90.0, 100.0)` with `cell_count: 1`;
  - right component bbox `(110.0, 0.0, 200.0, 100.0)` with `cell_count: 1`.
- Each split-room component now also exposes one `cell_rects` item with the same bbox and `9000.0` area, proving the component is traceable back to its free rect-cell evidence instead of only an aggregate bbox.
- Important boundary:
  - this is still rect-cell component geometry evidence, not CAD boolean polygons, navmesh nodes, or medial-axis route geometry.

2026-07-07, negative-space component area closure pass:

- Extended `matrix["negative_space"]` with descriptor-level closure fields:
  - `component_area_total`;
  - `component_cell_count_total`;
  - `component_cell_area_sum_total`;
  - `negative_space_component_area_residual`;
  - `negative_space_component_area_residual_ratio`.
- Extended `path_connectivity.negative_space_component_count` with the same closure fields so exports can audit the negative-space descriptor without opening graph internals.
- Added metric row:
  - `path_connectivity.negative_space_component_area_residual_ratio`.
- Added split-room regression coverage:
  - two free components;
  - two total rect-cells;
  - `component_area_total = 18000.0`;
  - `component_cell_area_sum_total = 18000.0`;
  - `negative_space_component_area_residual = 0.0`.
- Current fixture descriptor:
  - `component_area_total`: `684736.0`;
  - `component_cell_count_total`: `814`;
  - `component_cell_area_sum_total`: `684736.0`;
  - `negative_space_component_area_residual`: `0.0`;
  - `negative_space_component_area_residual_ratio`: `0.0`.
- Current fixture score:
  - `negative_space_component_area_residual_ratio`: `0.0`.
- Updated the notebook audit output with:
  - `negative_space_component_closure`.
- Important boundary:
  - this checks agreement between the current rect-cell component decomposition and the negative-space area proxy;
  - it is not CAD boolean room-minus-blocker validation, cleaned free-space polygons, a navmesh, or a medial-axis route graph.

2026-07-07, negative-space free polygon evidence pass:

- Added descriptor evidence:
  - `matrix["negative_space"]["free_space_polygons"]`.
- Added metric row:
  - `path_connectivity.negative_space_free_polygon_count`.
- Added merged boundary-loop row:
  - `path_connectivity.negative_space_room_minus_blocker_polygon_count`.
- Added Shapely room-minus-blocker row:
  - `path_connectivity.cad_room_minus_blocker_polygon_count`.
- Added Shapely area closure row:
  - `path_connectivity.cad_room_minus_blocker_area_residual_ratio`.
- Added Shapely fragmentation severity row:
  - `path_connectivity.cad_room_minus_blocker_largest_component_area_ratio`.
- Added Shapely component touch row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_region_ratio`.
- Added Shapely component entry-touched area row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_area_ratio`.
- Added Shapely component entry-touched count row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_component_ratio`.
- Added Shapely component region-pair row:
  - `path_connectivity.cad_room_minus_blocker_entry_connected_region_pair_ratio`.
- Added Shapely component graph row:
  - `path_connectivity.cad_room_minus_blocker_component_graph_edge_count`.
- Added shared-edge adjacency row:
  - `path_connectivity.negative_space_free_polygon_adjacency_count`.
- Added shared-edge graph descriptor:
  - `matrix["negative_space"]["free_space_polygon_graph"]`.
- Added metric row:
  - `path_connectivity.free_space_polygon_graph_cycle_rank`.
- Added entry-region distance row:
  - `path_connectivity.free_space_polygon_graph_mean_entry_region_distance`.
- Added shared-edge width row:
  - `path_connectivity.free_space_polygon_graph_mean_edge_clearance_width`.
- Added entry-region path bottleneck width row:
  - `path_connectivity.free_space_polygon_graph_mean_entry_region_min_clearance_width`.
- Added entry-region widest-path width row:
  - `path_connectivity.free_space_polygon_graph_mean_entry_region_widest_clearance_width`.
- Added entry-to-region distance row:
  - `path_connectivity.negative_space_mean_entry_region_free_polygon_distance`.
- Added entry-to-region path-length row:
  - `path_connectivity.negative_space_mean_entry_region_free_polygon_path_length`.
- The row exposes each current free rect-cell as a four-point polygon with `component_index`, `cell_index`, `points`, and `area`.
- The merged boundary-loop row exposes `room_minus_blocker_polygons` with `outer_ring`, `holes`, `area`, and `cell_count`, built by canceling shared rect-cell edges inside each component.
- The Shapely boolean row exposes `cad_room_minus_blocker_polygons` with `outer_ring`, `holes`, `area`, and `source = shapely_difference`.
- The Shapely closure row compares summed `cad_room_minus_blocker_area_total` with current `negative_space_area` and exposes `cad_room_minus_blocker_area_residual`.
- The Shapely fragmentation row reports largest free-space component area over total Shapely free-space area.
- The Shapely component touch row exposes `cad_room_minus_blocker_component_touch_evidence`, connecting Shapely free-space components to entry touches and region overlap areas.
- The Shapely component entry-touched area row reports the share of Shapely free-space polygon area whose component touches at least one entry.
- The Shapely component entry-touched count row reports the share of Shapely free-space components that touch at least one entry.
- The Shapely region-pair row counts analysis-region pairs that share an entry-touched Shapely component.
- The Shapely component graph row exposes the graph edge count and node-type counts for the same component/entry/region evidence.
- The adapter payload also exposes `cad_room_minus_blocker_component_graph`, a graph-shaped handoff over the same Shapely component/entry/region evidence.
- The adjacency row exposes direct shared-edge links between those free rect-cell polygons with `from_cell`, `to_cell`, `shared_edge`, and `length`.
- The graph descriptor exports the same rect-cell free-space polygons as graph nodes and shared-edge links as graph edges with center-to-center `distance`, `weight`, and shared-edge `clearance_width`; this is a handoff shape for later navmesh replacement.
- The graph descriptor includes `component_count`, `cycle_rank`, `dead_end_node_count`, and `dead_end_nodes`.
- The graph descriptor also anchors entries and regions to free-space polygon nodes and records entry-to-region shortest centerline distance evidence over the same graph, including `path_edge_ids` and per-path `min_clearance_width`.
- The graph descriptor records `entry_region_widest_path_evidence`, a max-min shared-edge-width path over the same rect-cell graph. Zero-edge entry/region overlaps keep `widest_clearance_width = None` and do not enter the mean.
- The overlay SVG now exposes the same graph evidence with:
  - `data-layer="free-space-graph-entry-region-path"`;
  - `data-layer="free-space-graph-entry-anchor"`;
  - `data-layer="free-space-graph-region-anchor"`.
- The distance row uses `entry_to_region_rect_cell_adjacency_shortest_path_proxy` to count shortest shared-edge hops from entry-touch free cells to region-overlap free cells.
- The path-length row uses `entry_to_region_rect_cell_centerline_length_proxy` to sum center-to-center distances along each reconstructed `path_cells` sequence.
- Current fixture descriptor:
  - `free_space_polygon_count`: `814`.
  - `negative_space_room_minus_blocker_polygon_count`: `1`.
  - `cad_room_minus_blocker_polygon_count`: `1`.
  - fixture `room_minus_blocker_polygons[0]` has `20` hole rings and area `684736.0`.
  - fixture `cad_room_minus_blocker_polygons[0]` has `20` hole rings and area `684736.0`.
  - `cad_room_minus_blocker_area_residual_ratio`: `0.0`.
  - `cad_room_minus_blocker_largest_component_area_ratio`: `1.0`.
  - `cad_room_minus_blocker_entry_connected_region_ratio`: `1.0`.
  - `cad_room_minus_blocker_entry_connected_area_ratio`: `1.0`.
  - `cad_room_minus_blocker_entry_connected_component_ratio`: `1.0`.
  - `cad_room_minus_blocker_entry_connected_region_pair_ratio`: `1.0`.
  - `cad_room_minus_blocker_component_graph_edge_count`: `11`.
  - `cad_room_minus_blocker_component_graph`: `12` nodes and `11` edges.
  - `free_space_polygon_adjacency_count`: `1426`.
  - `free_space_polygon_graph.node_count`: `814`;
  - `free_space_polygon_graph.edge_count`: `1426`;
  - `free_space_polygon_graph_cycle_rank`: `613`;
  - `free_space_polygon_graph.dead_end_node_count`: `0`;
  - `free_space_polygon_graph_mean_entry_region_distance`: `349.3438`;
  - `free_space_polygon_graph_mean_edge_clearance_width`: `29.6985`;
  - `free_space_polygon_graph_mean_entry_region_min_clearance_width`: `30.6957`;
  - `free_space_polygon_graph_mean_entry_region_widest_clearance_width`: `57.2609`;
  - `free_space_polygon_graph.entry_region_distance_evidence` count: `32`;
  - `negative_space_mean_entry_region_free_polygon_distance`: `3.1429`;
  - `negative_space_mean_entry_region_free_polygon_path_length`: `95.7857`;
  - distance evidence covers seven analysis regions.
- Important boundary:
  - this is a stable polygon-evidence interface for downstream geometry adapters;
  - `rect_cell_room_minus_blocker_boundary_union_proxy` is a merged rect-cell boundary-loop export, not CAD boolean room-minus-blocker topology;
  - `shapely_room_polygon_difference_blocker_union` is polygon difference evidence over current authored polygons, not Rhino/VisualARQ hosted topology or navmesh faces;
  - `shapely_room_minus_blocker_area_minus_negative_space_area` is an area closure check, not a layout-quality score or hosted-model validation;
  - `shapely_largest_component_area_over_total_free_area` reports fragmentation severity only, not route reachability, shortest-path routing, or route quality;
  - `shapely_component_entry_region_touch_proxy` reports component-level touch/overlap only, not hosted doorway topology, route reachability, or route quality;
  - `shapely_component_entry_touched_area_ratio_proxy` reports entry-touched component area share only, not route reachability, shortest-path routing, or route quality;
  - `shapely_component_entry_touched_component_count_proxy` reports entry-touched component count share only, not route reachability, shortest-path routing, or route quality;
  - `shapely_component_entry_connected_region_pair_proxy` counts analysis-region pairs sharing an entry-touched component only; it is not route reachability, shortest-path routing, or route quality;
  - `shapely_component_entry_region_touch_graph_proxy` packages the same evidence as a graph, not a navmesh, skeleton, or route graph;
  - the overlay layers visualize already-computed evidence only; they are not a separate path solver;
  - entry-region widest-path width maximizes the minimum shared-edge width on the current rect-cell graph; it is not medial-axis clearance, navmesh portal width, route optimization, code-compliant passage width, CAD boolean room-minus-blocker polygons, cleaned free-space regions, navmesh faces, shortest-path routing, or medial-axis route geometry.

2026-07-07, negative-space graph region-pair evidence consolidation pass:

- Extended `matrix["negative_space_graph"]["metrics"]` with:
  - `entry_connected_region_pair_evidence`;
  - `unconnected_region_pair_evidence`.
- `path_connectivity.negative_space_entry_connected_region_pair_ratio` and `path_connectivity.candidate_path_region_pair_ratio_proxy` now reuse the graph metric evidence instead of rebuilding pair evidence inside row assembly.
- Updated the notebook audit output under `negative_space_graph_metrics` with:
  - `entry_connected_region_pair_count`;
  - `total_region_pair_count`;
  - `entry_connected_region_pair_ratio`;
  - `entry_connected_region_pair_evidence`;
  - `unconnected_region_pair_evidence`.
- Important boundary:
  - evidence is still same-component rect-cell evidence;
  - it is not shortest-path routing, route quality, detour, graph centrality, or path certification.

2026-07-06, negative-space component-to-region graph pass:

- Extended `matrix["negative_space_graph"]` with:
  - `region` nodes;
  - `negative_space_component_region_touch` edges from decomposed components to region records.
- Added metric row:
  - `path_connectivity.negative_space_entry_connected_region_ratio`.
- The row reports the share of regions touched by a negative-space component that is also entry-connected.
- Added a synthetic regression where a split room has one entry-connected component touching only the left region:
  - two component-region edges;
  - one entry-connected component-region edge;
  - `negative_space_entry_connected_region_ratio`: `0.5`.
- Current fixture descriptor:
  - the single entry-connected negative-space component touches all seven analysis fixture regions;
  - `negative_space_entry_connected_region_ratio`: `1.0`.
- Important boundary:
  - component-region touch is rect-cell-to-region bbox contact;
  - this is not shortest-path routing, route quality, detour, or graph centrality.

2026-07-06, negative-space entry-connected region-pair pass:

- Added metric row:
  - `path_connectivity.negative_space_entry_connected_region_pair_ratio`.
- The row reports the share of region pairs that share an entry-connected negative-space component.
- The graph metrics and row expose `entry_connected_region_pair_count`, `total_region_pair_count`, `entry_connected_region_pair_evidence`, and `unconnected_region_pair_evidence` so the numerator, denominator, connected same-component pairs, and missing same-component pairs are auditable.
- Added a synthetic regression with three regions split across two negative-space components:
  - total region pairs: `3`;
  - entry-connected same-component region pairs: `1`;
  - unconnected same-component region pairs: `2`;
  - `negative_space_entry_connected_region_pair_ratio`: `0.3333`;
  - pair evidence: `left_lower_region` and `left_upper_region` share component `0`.
- Current fixture descriptor:
  - the single entry-connected negative-space component touches all seven analysis fixture regions;
  - total region pairs: `21`;
  - entry-connected same-component region pairs: `21`;
  - `negative_space_entry_connected_region_pair_ratio`: `1.0`.
- Important boundary:
  - pair evidence means same decomposed component only;
  - this is not shortest-path routing, route distance, route quality, detour, graph centrality, or path certification.

2026-07-06, negative-space entry-connected region area coverage pass:

- Added metric row:
  - `path_connectivity.negative_space_entry_connected_region_area_coverage_ratio`.
- The row reports the mean share of each region bbox area overlapped by entry-connected negative-space components.
- `negative_space_component_region_touch` graph edges now carry `overlap_area` and `region_area_ratio`, and the coverage row records `edge_ids` for traceability.
- Added a synthetic regression where a region spans both sides of a split room:
  - region bbox area: `18000.0`;
  - entry-connected negative-space overlap: `9000.0`;
  - `negative_space_entry_connected_region_area_coverage_ratio`: `0.5`.
- Current fixture descriptor:
  - the single entry-connected negative-space component touches all seven analysis fixture regions;
  - mean region-area coverage is `0.6996`, because furniture and boundary blockers occupy part of the region bboxes.
- Important boundary:
  - coverage is computed over region bboxes and decomposed negative-space cells;
  - this is a continuous proxy for how much of a region is exposed to entry-connected free space, not semantic region membership, route quality, or shortest-path reachability.

2026-07-06, negative-space overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with negative-space graph evidence layers:
  - `negative-space-component`;
  - `negative-space-graph-node`;
  - `negative-space-graph-edge`.
- Component bbox rectangles expose `data-bbox-left`, `data-bbox-top`, `data-bbox-right`, `data-bbox-bottom`, `data-cell-count`, and component area so notebook overlays can be matched to `negative_space_graph` nodes; notebook audit also reports `component_cell_counts`, `component_cell_area_sums`, and `max_component_cell_area_residual_ratio` from graph metrics.
- `max_component_cell_area_residual_ratio` is an internal closure check between component node area and summed `cell_rects` area; a non-zero value would flag proxy decomposition drift, not prove CAD boolean correctness.
- Added metric row:
  - `path_connectivity.negative_space_component_cell_area_residual_ratio`.
- The row exposes `component_cell_counts`, `component_cell_area_sums`, and residual evidence from `negative_space_graph.metrics`.
- Current fixture score:
  - `negative_space_component_cell_area_residual_ratio`: `0.0`.
- Negative-space graph edge SVG output includes `data-overlap-area` when a component-region overlap area exists.
- Current fixture overlay includes edge id `edge_negative_space_component_region_component_0_region_north_tables` with overlap area `337125.0`.
- Important boundary:
  - this is a notebook/debug trace layer for the proxy graph;
  - it is not a floor-plan visualization standard, not a navmesh viewer, and not a CAD/BIM display adapter.

2026-07-07, negative-space component bbox overlay evidence pass:

- Added a regression that requires `scene_metric_overlay_svg()` to render the `negative-space-component` layer with `data-component`, `data-cell-count`, and `data-bbox-left` attributes.
- This keeps component proxy geometry inspectable in the notebook before true CAD room-minus-blocker polygons exist.

2026-07-06, column-grid object phase pass:

- Added metric row:
  - `column_alignment.object_column_axis_phase_alignment`.
- The row scores each furniture/object center against its nearest authored column axis with `1 / (1 + distance / axis_spacing)`.
- Added a synthetic regression with two vertical column axes:
  - object on axis: score `1.0`;
  - object halfway between axes: score `0.6667`;
  - mean row score: `0.8334`.
- Current fixture descriptor:
  - `object_column_axis_phase_alignment`: `0.7001`;
  - evidence covers all 22 parsed object records.
- Important boundary:
  - `axis_spacing` is derived from same-direction authored column-axis center spacing;
  - this is a continuous phase proxy, not bay containment, not column-cell overlap, and not local interpolation for irregular grids.

2026-07-06, region centroid phase pass:

- Added metric row:
  - `region_alignment.region_centroid_phase_alignment`.
- The row projects region bbox centers onto the mean region axis and scores spacing regularity using a gap coefficient-of-variation score.
- Added a synthetic regression with three regions at projections `0.0`, `100.0`, and `300.0`:
  - gap lengths: `100.0` and `200.0`;
  - `region_centroid_phase_alignment`: `0.75`.
- Current fixture descriptor:
  - `region_centroid_phase_alignment`: `0.6508`;
  - evidence covers all seven analysis region records.
- Important boundary:
  - this is a centroid phase proxy for region alignment;
  - it is not region overlap, not local frame containment, and not a fuzzy region-membership model.

2026-07-07, region centroid trend pass:

- Added independent metric row:
  - `trend.region_centroid_trend_alignment`.
- The row uses `region_centroid_pca_axis_cross_deviation_score`: measurable region bbox centers define a PCA trend axis, each region center reports projection and cross-axis deviation, and the score is `1 / (1 + mean_cross_axis_deviation / trend_span)`.
- Added a synthetic regression with four regions near a diagonal sequence:
  - `region_centroid_trend_alignment`: `0.9652`;
  - trend axis angle: `38.8153`;
  - evidence records per-region projection and cross-axis deviation.
- Important boundary:
  - this is the first standalone `trend` metric family row;
  - it is not semantic procession, circulation intent, time-series trend, or final route topology.

2026-07-06, column-grid region bay fit pass:

- Added metric row:
  - `column_alignment.region_column_bay_fit`.
- The row builds simple adjacent-axis bay strips from authored column axes and scores each region by `region bbox overlap area / region bbox area`.
- Added a synthetic regression with two vertical column axes:
  - one region fully inside the bay: score `1.0`;
  - one region straddling inside/outside the bay: score `0.5`;
  - mean row score: `0.75`.
- Added a non-orthogonal regression with two parallel diagonal column axes:
  - the bay is represented as a four-point polygon from the paired axis endpoints;
  - a region enclosing that slanted strip has overlap area `10000.0`;
  - `region_column_bay_fit`: `0.5`.
- Current fixture descriptor:
  - `region_column_bay_fit`: `0.446`;
  - evidence covers all seven analysis region records.
- Important boundary:
 - current bay geometry is either an axis-aligned strip between adjacent same-direction authored axes or a simple four-point polygon between two parallel slanted axes;
 - this is a continuous region-to-bay fit proxy, not full structural grid topology, not multi-axis bay decomposition, and not irregular grid interpolation.

2026-07-07, object column-bay local position pass:

- Added metric row:
  - `column_alignment.object_column_bay_local_position_coverage`.
- The row uses `object_center_affine_position_in_nearest_column_bay` to compute each object center's local affine coordinates in the nearest authored adjacent column bay.
- Added a synthetic regression with two parallel diagonal column axes:
  - one object at local `(0.5, 0.5)` inside the bay: score `1.0`;
  - one object at local `(0.5, 1.5)` outside the bay span: score `0.0`;
  - mean row score: `0.5`.
- Current fixture descriptor:
  - `object_column_bay_local_position_coverage`: `0.4091`;
  - evidence covers all 22 object records.
- Important boundary:
  - this is a local-frame object-center containment proxy for authored adjacent bays;
  - it is not full irregular grid interpolation, bay topology validation, or structural column-cell reasoning.

2026-07-06, object-region membership coverage pass:

- Added metric row:
  - `region_alignment.object_region_membership_coverage`.
- Added companion data-quality row:
  - `region_alignment.object_region_assignment_coverage`.
- The row checks authored object `region` metadata against measurable region geometry by `object footprint overlap area / object footprint area`.
- The assignment row separately reports the share of objects whose authored region id has a matching region record.
- Added a synthetic regression:
  - one object fully inside its authored region: score `1.0`;
  - one object half inside: score `0.5`;
  - one object with no matching region record appears in `missing_region_evidence`;
  - mean row score over measurable memberships: `0.75`;
  - assignment coverage: `0.6667`.
- Current fixture descriptor:
  - `object_region_membership_coverage`: `1.0`;
  - `object_region_assignment_coverage`: `1.0`;
  - evidence covers all 22 objects with matching authored region records;
  - current fixture `missing_region_evidence` is empty.
- Important boundary:
  - this is a metadata/geometry consistency check;
  - it is not automatic region discovery, not semantic membership inference, and not fuzzy region belonging.

2026-07-06, analysis-region metadata pass:

- Added missing fixture region records for `east_armchairs`, `north_wall`, and the fallback `room`/misc group so authored object-region metadata is complete.
- Marked the fallback room/misc region with `data-analysis-region="false"`.
- Current behavior:
  - object-region membership and assignment coverage use the full region list, so metadata completeness is checked against all authored regions;
  - alignment, column bay, path, sampled, and negative-space region metrics filter out metadata-only regions;
  - current fixture has seven analysis regions plus one metadata-only room/misc region.
- Current fixture descriptor:
  - `object_region_membership_coverage`: `1.0`;
  - `object_region_assignment_coverage`: `1.0`;
  - `region_alignment.region_axis_agreement`: `0.2304`;
  - `column_alignment.region_column_bay_fit`: `0.446`;
  - `path_connectivity.path_region_touch_ratio`: `0.7143`.
- Important boundary:
  - `data-analysis-region="false"` is a fixture/adapter data-quality flag, not a spatial semantics model;
  - it prevents large fallback catch-all regions from distorting region alignment, bay fit, path, and negative-space metrics while preserving metadata coverage checks.

2026-07-06, column-grid overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with column-grid evidence layers:
  - `column-axis`;
  - `column-bay`.
- Column bay SVG elements now expose bay-level aggregate attributes from `region_column_bay_fit.region_bay_fit_evidence`:
  - `data-score-max`;
  - `data-score-count`.
- Current fixture overlay includes bay id `column_axis_x__column_axis_y` with `data-score-max="1.0000"` and `data-score-count="2"`.
- Important boundary:
  - this is a notebook/debug trace layer for authored column-axis and bay-fit proxy evidence;
 - region-level bay scores remain in the matrix evidence rows;
  - this is not a CAD/BIM column-grid viewer, not a structural topology renderer, and not a per-region color map.

2026-07-06, region-axis overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with a `region-axis` evidence layer.
- Each rendered region axis exposes:
  - `data-region`;
  - `data-basis`;
  - `data-angle`.
- The overlay reuses the same `_record_axis_descriptor()` logic as the region alignment rows, so debug lines match the matrix evidence source.
- Current fixture overlay records `region_slanted_test` with `data-basis="polygon_pca_axis"` and `data-angle="26.5651"`.
- Important boundary:
  - this is a local-frame/debug evidence line, not a full region force field;
  - bbox-axis regions remain bbox proxies until minimum-OBB or richer polygon frames are implemented.

2026-07-06, boundary-axis overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with a `boundary-axis` evidence layer.
- Each rendered boundary axis exposes:
  - `data-boundary`;
  - `data-kind`;
  - `data-basis`;
  - `data-angle`;
  - `data-walk-block`;
  - `data-see-block`;
  - `data-grouping-strength`.
- Current fixture overlay makes glass/rug/material/visual boundary cue metadata inspectable in the notebook overlay:
  - `glass_boundary` keeps walk `1.0000` and see `0.1500`;
  - `rug_boundary` keeps grouping strength `0.8500`.
- Important boundary:
  - this reuses authored structured-SVG metadata and axis descriptors;
  - it is not material simulation, visibility ray casting, or a CAD/BIM boundary viewer.

2026-07-06, region-boundary cue overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with a `region-boundary-cue` evidence layer.
- The layer renders proximity evidence from `region_alignment.region_source_boundary_proximity` as dashed region-center to boundary-center links.
- Each link exposes:
  - `data-region`;
  - `data-boundary`;
  - `data-gap`;
  - `data-proximity`.
- Current fixture overlay includes `region_center_lounge` to `glass_boundary` with gap `5.0000` and proximity `0.9833`.
- Important boundary:
  - this is traceability for same-region boundary cue evidence;
  - it is still bbox-gap proximity, not curve distance, containment, material simulation, or a region merge/split decision.

2026-07-06, object-region membership overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with an `object-region-membership` evidence layer.
- The layer renders links from object centers to their matched authored region centers using `object_region_membership_coverage.object_region_membership_evidence`.
- Each link exposes:
  - `data-object`;
  - `data-region`;
  - `data-score`.
- Current fixture overlay includes `north_table_r1_c1` to `region_north_tables` with score `1.0000`.
- Important boundary:
  - this is traceability for region metadata consistency;
  - synthetic missing-region cases remain listed in matrix evidence and styled by the companion overlay layer.

2026-07-06, missing-region overlay evidence pass:

- Extended `scene_metric_overlay_svg()` with an `object-missing-region` evidence layer.
- The layer marks objects listed in `object_region_membership_coverage.missing_region_evidence`.
- Each marker exposes:
  - `data-object`;
  - `data-region-key`.
- Current fixture now has no missing-region markers; the overlay behavior remains covered by a synthetic missing-region regression.
- Important boundary:
  - this is a metadata completeness warning, not a geometric error by itself;
  - it should guide fixture/Rhino/BIM region authoring before interpreting region membership scores.

2026-07-06, graph cycle-rank evidence pass:

- Added `cycle_rank_inputs` to bbox-touch graph topology metrics:
  - `node_count`;
  - `edge_count`;
  - `component_count`.
- Added the same `cycle_rank_inputs` evidence to:
  - `path_connectivity.graph_loop_count`;
  - `path_connectivity.graph_loop_ratio`.
- Current fixture cycle-rank inputs:
  - `node_count`: `12`;
  - `edge_count`: `7`;
  - `component_count`: `5`.
- Important boundary:
  - this makes the loop proxy auditable;
  - it does not turn bbox-touch graph loops into true circulation loops, navmesh loops, or medial-axis route loops.

2026-07-06, graph component evidence pass:

- Added graph connected-component evidence to bbox-touch path topology:
  - `matrix["graphs"]["walk"]["metrics"]["component_count"]`;
  - `matrix["graphs"]["walk"]["metrics"]["components"]`;
  - `path_connectivity.graph_component_count`.
- Current fixture `graph_component_count`: `5`.
- The component evidence exposes the isolated left entry, isolated right line entry, isolated north-wall region, and isolated slanted-test region separately from the main path-touch component.
- Important boundary:
  - this is connected-component evidence over the current bbox-touch graph only;
  - it is not a route graph component, navmesh island, CAD negative-space component, or hosted doorway topology.

2026-07-06, graph entry-region reachability evidence pass:

- Added explicit region-id evidence to `graph_entry_region_reachability`:
  - `reached_region_ids`;
  - `unreached_region_ids`.
- Current fixture reached regions:
  - `region_center_lounge`;
  - `region_east_armchairs`;
  - `region_east_work`;
  - `region_north_tables`;
  - `region_west_lounge`.
- Current fixture unreached regions:
  - `region_north_wall`;
  - `region_slanted_test`.
- Important boundary:
  - this makes the current BFS reachability row auditable;
  - it is still bbox-touch graph reachability, not route certification or continuous negative-space reachability.

2026-07-06, negative-space entry-connected region-id evidence pass:

- Added explicit region-id evidence to `negative_space_entry_connected_region_ratio`:
  - `entry_connected_region_ids`;
  - `non_entry_connected_region_ids`.
- Synthetic split-room regression:
  - `entry_connected_region_ids`: `["left_region"]`;
  - `non_entry_connected_region_ids`: `["right_region"]`.
- Current fixture:
  - all seven analysis regions are touched by the single entry-connected negative-space component;
  - `non_entry_connected_region_ids` is empty.
- Important boundary:
  - this is still rect-cell negative-space component touch evidence;
  - it is not shortest-path routing, route quality, semantic region membership, or CAD boolean topology.

2026-08-16, `JJ-00-baseline` BIM acceptance-manifest checkpoint:

- The accepted pre-Gate baseline was `295 passed in 785.92s` under the observed
  Pixi runtime `Python 3.12.13`; the environment was not changed despite the
  planned Python version differing from this observed runtime.
- Strict TDD evidence:
  - the first focused run failed during collection with
    `ModuleNotFoundError: No module named 'test.bim'` because the acceptance
    manifest did not exist;
  - the deterministic-regeneration repair test then failed with
    `KeyError: 'regeneration'` before the regeneration contract was added.
  - the repository-relative generator-path test failed while the manifest
    still exposed the shadowable `generator_module` key;
  - the exact-mode-set test failed with `DID NOT RAISE` before missing supported
    modes were rejected.
- Final focused verification: `5 passed in 0.02s`.
- Final full verification: `300 passed in 816.39s (0:13:36)`.
- The manifest locks stable fixture ids, the two required JSON artifacts, the
  four explicit input modes, and a programmatic regeneration entrypoint that
  forbids manual edits.
- The manifest contains no viewport-name dependency, perceptual weight, score,
  or inferred semantic result.

2026-08-16, Gate 0 code-quality repair checkpoint:

- Parent Gate 0 checkpoint: change `ltxoqrkpqpkppzuttnszwnozpzsxszkl`,
  commit `26c7329c`.
- Import-boundary RED evidence:
  - `pixi run pytest test/bim/test_acceptance_manifest.py -q
    --import-mode=importlib` produced `1 failed, 5 passed`;
  - the fresh repository-root subprocess failed with
    `ModuleNotFoundError: No module named 'test.bim'`.
- Import-boundary repair:
  - `test` and `test.bim` are explicit packages;
  - the test module uses a relative import;
  - a fresh Python subprocess proves the package-qualified manifest API imports
    from the repository root without pytest path injection.
- Structural-validation RED evidence:
  - the parameterized malformed-input run produced `12 failed, 6 passed`;
  - missing keys, strings, mappings, and non-string members were accepted,
    misreported, or leaked into later collection logic before the repair.
- Structural-validation repair:
  - `fixture_ids`, `required_outputs`, and `allowed_input_modes` must each exist
    and contain a list of strings before any list/set conversion;
  - malformed values now raise focused `ValueError` messages.
- Final focused verification:
  - importlib mode: `18 passed in 0.21s`;
  - normal mode: `18 passed in 0.20s`.
- Final full verification: `313 passed in 923.37s (0:15:23)` under the observed
  Pixi runtime `Python 3.12.13`; the environment was not changed.
- Self-review found no Gate 1 implementation, Blender-scene modification,
  perceptual weight, score, or inferred semantic addition.

2026-08-16, `JJ-01-contract` Neutral Scene v2 checkpoint:

- Scope remained Gate 1 only: one pure-Python contract module and one focused
  contract test module. No SVG, IFC, Blender, substitute, inference, analysis,
  or exported `room_analysis_model` implementation was changed.
- Strict TDD RED evidence:
  - the initial test collection exposed a package-relative test import issue
    after Gate 0 made `test` an explicit package;
  - after correcting only that test harness import, collection failed for the
    intended reason with `ModuleNotFoundError: No module named
    'order_analyzer.features.scene_contract'`.
- The contract defines the explicit `neutral-scene-v2` version, the four exact
  input modes, `AnalysisContext`, optional `AnalysisDomain`, all required
  source/fact/authored records, `UncertaintyRecord`, and the top-level
  `NeutralSceneV2` aggregate.
- Serialization and validation evidence covers a complete recursive JSON
  round trip, source ordering and provenance, finite units/transforms/geometry,
  orthonormal analysis planes, positive tolerances, triangle arity/range,
  stable ids, explicit absent domain/capabilities, and path-specific rejection
  of unsupported raw application objects.
- Ponytail/YAGNI review removed repeated per-record serializer/deserializer
  machinery and the subsequent type-dispatch registry. The module decreased
  from about 54 KB/1203 lines to about 37 KB/833 lines while each concrete
  record retained its own explicit `from_dict` method. Remaining helpers are
  limited to shared JSON traversal, strict dataclass loading, and repeated
  primitive validation; no factory, backend, dependency, or future adapter
  abstraction was added.
- Final focused verification: `42 passed in 0.07s`; importlib-mode focused
  verification: `42 passed in 0.04s`.
- Final full verification: `355 passed in 931.64s (0:15:31)` under the observed
  Pixi runtime Python `3.12.13`; the environment was not changed.
- Grill Me self-review found:
  - raw Blender/IFC/SVG/custom geometry objects cannot pass the recursive JSON
    boundary and report their exact record path;
  - missing domain and evidence remain `None`, false capability flags, and/or
    uncertainty records rather than numeric zero;
  - the module imports only Python standard-library modules;
  - no perceptual weight, final score, collapsed boundary field, source adapter,
    or speculative analysis abstraction is present.

2026-08-16, Gate 1 contract-invariant repair checkpoint:

- Scope remained Gate 1 only. The repair changes the Neutral Scene contract,
  its focused tests, and this evidence ledger; Gate 2 was not started.
- Strict TDD evidence by defect:
  - shared-mutation RED: the new provenance regression failed with `DID NOT
    RAISE TypeError`, proving frozen dataclasses still exposed mutable nested
    JSON containers;
  - nested-path RED: invalid material transmittance reported only
    `material.visible_transmittance must be between 0 and 1`, not the required
    `neutral_scene.materials[0].visible_transmittance` path;
  - overflow RED: `10**400` leaked `OverflowError: int too large to convert to
    float` from `_number`;
  - geometry-invariant RED: a `SourceObject` with empty `geometry_refs` and no
    uncertainty was silently accepted (`DID NOT RAISE ValueError`).
- The weak method-name-only deserialization test was replaced by 14
  representative direct JSON round trips, one for every concrete record type.
  Its first characterization run was `14 passed in 0.05s`; there was no
  behavior failure to manufacture for this coverage-only correction.
- Open JSON facts are now recursively copied and frozen with standard-library
  tuples and `MappingProxyType`. Shared provenance/details cannot be mutated
  through either owner, surface facts and capability flags are also frozen,
  and `to_dict()` still returns ordinary JSON lists and dictionaries. No
  hashability claim is made.
- `_load` now rewrites constructor-local validation locations to the complete
  enclosing path without adding serialized metadata. `_number` converts
  integer-to-float overflow into a path-qualified `ValueError`.
- The geometry contradiction is resolved with one stable uncertainty code:
  `SourceObject.geometry_refs` must be non-empty unless its uncertainties
  explicitly include `missing_geometry`. Both legitimate branches and the
  rejected silent-empty branch have focused tests.
- Final focused verification: `61 passed in 0.07s`.
- Final importlib-focused verification: `61 passed in 0.06s`.
- Final full verification: `374 passed in 818.20s (0:13:38)` under the observed
  Pixi runtime Python `3.12.13`; the environment was not changed.
- Final self-review found no source-application imports, weights, scores,
  adapter work, hidden payload fields, schema framework, or speculative
  feature. All project-owned functions retain English docstrings.

2026-08-16, Gate 1 validation-edge repair checkpoint:

- Scope remained Gate 1 only; Gate 2 was not started.
- Strict TDD RED evidence:
  - the 24-case vocabulary test failed all 24 cases before repair;
  - list/dict values for source and analysis units, mesh units, and input mode
    leaked unhashable `TypeError` from membership checks;
  - other non-string values raised messages without the required
    `context.*` or `mesh.*` record path;
  - the 14-record hashability test failed all 14 cases because frozen
    dataclasses advertised `collections.abc.Hashable` even when mapping fields
    made generated hashes fail at runtime.
- `_unit` and input-mode validation now reject non-strings before set
  membership and use explicit `context.source_length_unit`,
  `context.analysis_length_unit`, `mesh.units`, and `context.input_mode`
  locations. The existing nested `_load` path qualification remains intact.
- Every concrete record explicitly defines `__hash__ = None`. Equality and
  frozen-field behavior remain unchanged; no structural hash, frozen-dict
  framework, `unsafe_hash`, or hashability claim was added.
- Targeted GREEN evidence:
  - vocabulary type/path cases: `24 passed in 0.04s`;
  - concrete-record unhashability: `14 passed in 0.04s`.
- Final focused verification: `99 passed in 0.08s`.
- Final importlib-focused verification: `99 passed in 0.08s`.
- Final full verification: `412 passed in 932.85s (0:15:32)` under the observed
  Pixi runtime Python `3.12.13`; the environment was not changed.
- Self-review confirmed exactly 14 explicit unhashable declarations, no custom
  hash implementation, no source-application imports, no weights or scores,
  and no missing project-owned function docstrings.

2026-08-17, `JJ-02-svg-adapter` Neutral Scene v2 SVG adapter checkpoint:

- Scope remained Gate 2 only. Added the `adapters` package and focused adapter
  tests; `features/scene_loader.py` changed only through an opt-in
  `include_source_order` compatibility channel whose default dictionary shape
  remains unchanged. No geometry substitutes, boundary evidence, IFC,
  Blender, inference consumer, evaluator, OCTA, or SVG fixture was changed.
- Strict TDD RED evidence:
  - the initial public-API test failed with `ModuleNotFoundError: No module
    named 'adapters'` before the package existed;
  - analysis-unit consistency failed because converted centimetre coordinates
    still advertised mesh unit `m`;
  - cross-bucket source order failed with `chair-second` before `wall-first`;
  - a point-free zero-extent record incorrectly produced a degenerate mesh;
  - the existing top-level import mode failed with `attempted relative import
    beyond top-level package`;
  - an open three-point boundary path incorrectly produced triangle
    `(0, 1, 2)`;
  - an explicit planar affordance without z metadata was dropped instead of
    retained with `vertical_extent_unavailable` uncertainty.
- Adapter behavior:
  - explicit source and analysis units are contract-validated and coordinates
    are normalized without inferring physical scale from the viewBox;
  - SVG y-down coordinates, viewBox size, XY analysis plane, adapter version,
    tolerances, input mode, and planar-only capabilities are explicit;
  - source ids and global XML order, z=0 transport geometry, authored furniture
    groups, explicit grid axes/grids, openings, affordances, domain selection,
    metadata, adapter references, and provenance are preserved when present;
  - room boundaries never become an analysis domain, columns never create
    axes, furniture names never create affordances, and region/path records are
    source hints rather than inferred outputs;
  - legacy weights and all walk/see/grouping/boundary-strength key spellings
    are absent from serialized Neutral Scene output.
- Pre-full static checks found no fixture-name-specific branch, no XML parser or
  traversal in the adapter beyond one call to `load_structured_svg_scene`, and
  no evaluator, inference, OCTA, IFC, Blender, or `bpy` import.
- Final focused verification:
  - Gate 0, Gate 1, and Gate 2 importlib run: `137 passed in 6.20s`;
  - relevant legacy loader compatibility run: `8 passed, 203 deselected in
    0.37s`;
  - adapter-only final run before full verification: `20 passed`.
- Final full verification: `432 passed in 811.60s (0:13:31)` under the observed
  Pixi runtime Python `3.12.13`; the environment was not changed.
- Grill Me self-review found no adapter-authored analysis behavior, fabricated
  3D solid/height/optical/permeability/domain/affordance fact, legacy weight,
  duplicate parser, or source-name branch. Missing physical vertical extent is
  a z=0 representation with explicit uncertainty and unavailable vertical
  capability, not a numeric height claim.
- Ponytail review removed an unused bucket-order constant and unnecessary
  `OrderedDict` use. The remaining helpers correspond directly to contract
  record families or repeated metadata/geometry normalization; no dependency,
  generic adapter framework, parser, inference abstraction, or compatibility
  rewrite was added.
- An external read-only Codex diff review was attempted, but platform policy
  rejected sending uncommitted repository contents to an external model
  without explicit data-disclosure authorization. Local static review and all
  required tests completed; this is the only review-process concern.

2026-08-17, Gate 2 rejected-review repair checkpoint:

- Scope remained Gate 2 only. The five HIGH review findings did not conflict
  with the approved Gate 2 architecture. The earlier allowance for fan
  triangulation was narrowed because it is not correct for arbitrary concave
  polygons; no Gate 3 substitute, boundary-evidence, IFC, Blender, evaluator,
  inference-consumer, or OCTA work was started.
- Strict TDD RED evidence:
  - the initial repair run was `9 failed, 19 passed`; failures demonstrated a
    leaked `Rect` import, promotion of id-derived axes and fixture-name groups,
    lost affine transforms, bbox-derived curves, invalid concave fan faces,
    bbox fabrication for unresolved `use`, accepted duplicate ids, and
    colliding role-derived ids;
  - after correcting a test-harness use of nested `pytest.approx`, the affine
    RED showed source point `(1.0, 2.0, 0.0)` instead of transformed
    `(2.0, 6.0, 0.0)`;
  - a final identity-edge RED showed generated `svg-element-000001` shadowing
    a later explicit id of the same value.
- The opt-in loader handoff now carries explicit source/authorship facts,
  composed SVG affine transforms, and actual planar geometry from the single
  existing XML traversal. The default compatibility output remains unchanged.
- The adapter now accepts authored `data-*` roles and groups only. Legacy
  id/name-derived roles and grouping remain provenance-marked compatibility
  facts, unknown roles carry uncertainty, and columns never create axes.
- Scale, shear, nested transforms, and centered rotation are composed once
  before physical-unit conversion. Analytic circles and ellipses are sampled
  from their authored curves; concave polygons use the already-installed
  Shapely triangulator with interior and area checks; open polylines remain
  unfilled. Unsupported geometry preserves uncertainty instead of a bbox.
- Duplicate explicit source ids fail at the adapter boundary. Missing ids use
  stable traversal-based Neutral Scene ids that reserve every authored id,
  while the missing original source id remains `None` with uncertainty.
- Pre-full static review found no fixture-name-specific branch, duplicate XML
  parser, raw `Rect` adapter import, forbidden analysis import, or missing
  project-owned function docstring. JSON round trips and fixture tests found no
  raw compatibility object or forbidden legacy weight in Neutral Scene output.
- Focused GREEN evidence:
  - adapter-only: `29 passed in 2.56s`;
  - relevant legacy loader compatibility: `8 passed, 203 deselected in 0.17s`;
  - Gate 0, Gate 1, and Gate 2 importlib set: `146 passed in 3.21s`;
  - post-docstring adapter/loader set: `37 passed, 203 deselected in 2.69s`.
- First full-suite verification after behavioral repair: `441 passed in
  775.71s (0:12:55)` under Pixi runtime Python `3.12.13`; the environment was
  not changed.
- Grill Me review found no analysis behavior, fabricated 3D/affordance/domain,
  implicit physical units, authored compatibility semantics, or ambiguous
  source identity crossing the adapter boundary. Ponytail review retained one
  shared parser, the installed geometry primitive, and contract-specific
  helpers only; no new dependency or speculative adapter framework was added.

2026-08-17, Gate 2 architecture and integrity re-review repair checkpoint:

- Scope remained Gate 2 only. The seven review findings agree with the formal
  Gate 2 plan. This re-review corrects the earlier interpretation that the V2
  adapter must reuse the legacy XML traversal: the approved plan places
  XML/data-attribute parsing in `adapters/svg_scene.py` and leaves
  `features/scene_loader.py` as legacy compatibility behavior.
- Strict TDD RED evidence:
  - the initial re-review run was `13 failed, 27 passed`; failures covered
    role-filtered generic geometry, ignored duplicate generic ids, dangling
    material/surface/affordance/opening refs, ambiguous domains, lost
    stroke-only and multi-subpath paths, invalid curve dimensions, absent path
    sampling provenance, and the reversed parser boundary;
  - the provenance-version RED was `3 failed`, with every real fixture still
    reporting `svg-scene-adapter/0.1.0` instead of the required `0.2.0` after
    the semantic parser change.
- The adapter now parses every supported visible geometry element regardless
  of role. Missing roles remain `unknown` with uncertainty; duplicate explicit
  ids are checked across this complete source set, and all explicit ids are
  reserved before deterministic traversal ids are assigned.
- XML, inherited `data-*`, presentation fill facts, full affine composition,
  curve/path sampling, and V2 geometry extraction now live in the SVG adapter.
  V2-only handoff state and extraction helpers were removed from the legacy
  loader; its default public shape and representative values remain unchanged.
- A final adapter integrity pass checks geometry, group, axis/grid, opening,
  affordance-owner, domain, container, material, and surface refs against the
  actual emitted record sets. Unknown refs are omitted with structured
  uncertainty. Gate 2 emits no material or surface records and therefore emits
  no material or surface refs.
- `fill:none` closed paths remain faceless. Ambiguous open or multi-subpath
  filled paths retain sampled line geometry and
  `unsupported_path_fill_topology` uncertainty rather than fabricated faces.
  Fill, fill-rule, subpath offsets, fixed curve sampling count, sampled vertex
  count, and the absence of a tolerance criterion are serialized in mesh
  tessellation settings.
- Nonfinite or nonpositive circle/ellipse radii produce source objects with
  missing geometry and `invalid_curve_dimensions` uncertainty. Multiple
  explicit analysis domains raise a focused ambiguity error.
- Focused GREEN evidence:
  - adapter-only after behavior repair: `40 passed in 2.37s`;
  - relevant legacy loader compatibility: `8 passed, 203 deselected in 0.17s`;
  - Gate 0, Gate 1, and Gate 2 importlib set: `157 passed in 2.93s`;
  - adapter provenance version cycle: `3 passed`, then `40 passed in 2.40s`.
- First full-suite verification before the provenance-only version bump:
  `452 passed in 774.80s (0:12:54)` under Pixi runtime Python `3.12.13`.
- Grill Me review found no role-gated source loss, dangling Neutral Scene ref,
  fabricated path surface, ambiguous domain selection, invalid curve mesh,
  implicit unit inference, or Gate 3 behavior. Ponytail review retained the
  already-installed SVG/path and Shapely primitives, one adapter parser, and
  one compact integrity validator; it added no dependency or generic parser
  framework. All modified/new functions have English docstrings.

2026-08-17, Gate 2 SVG document-semantics re-review repair checkpoint:

- Scope remained Gate 2 only. The four findings agree with the formal Gate 2
  boundary: they strengthen source-document integrity and conservative planar
  extraction without adding analysis, substitutes, IFC, Blender, or migrated
  consumers.
- Strict TDD RED evidence:
  - the initial adversarial run was `9 failed, 37 passed`; failures covered the
    adapter version, duplicate/resource-owned ids, resource-container leakage,
    stylesheet-controlled fill topology, unresolved CSS, and nested viewport
    coordinates;
  - an additional empty-id boundary test failed with `DID NOT RAISE` before an
    explicitly present `id=""` was distinguished from a missing id.
- Every explicit `id` in the complete SVG document is now validated before
  emission and reserved before fallback ids are assigned. Resource descendants
  under defs, clip paths, masks, markers, patterns, symbols, filters, and
  gradients participate in id integrity but do not become ordinary source
  geometry.
- A deliberately small local stylesheet parser resolves tag, class, and id
  rules for `fill` and `fill-rule` with deterministic specificity/order. An
  unsupported fill-affecting selector causes faceless geometry plus
  `unresolved_css_presentation` uncertainty rather than a fabricated surface.
- Nested SVG viewport descendants are conservatively retained as source objects
  with `unsupported_nested_svg_viewport` and no geometry; untransformed child
  coordinates never enter Neutral Scene. Adapter provenance is versioned as
  `svg-scene-adapter/0.3.0`.
- Pre-full checks found no fixture-name branch, Gate 3 import, V2 helper in the
  legacy loader, duplicate parse within the V2 call path, forbidden weight, or
  missing function docstring. `features/scene_loader.py` and all SVG fixtures
  remained unchanged.
- Focused GREEN evidence:
  - adapter-only: `47 passed in 2.40s`;
  - relevant legacy loader compatibility: `8 passed, 203 deselected in 0.18s`;
  - Gate 0, Gate 1, and Gate 2 importlib set: `164 passed in 3.52s`.
- Final full verification: `459 passed in 776.45s (0:12:56)` under the observed
  Pixi runtime Python `3.12.13`; the environment was not changed.
- Grill Me review found no resource geometry leak, id collision path, silently
  transformed nested viewport, fabricated CSS-dependent face, or Gate 3
  behavior. Ponytail review kept the CSS support to the requested local subset
  and standard-library parsing, with no dependency or browser-style CSS engine.

2026-08-17, Gate 2 CSS, identity, and namespace re-review repair checkpoint:

- Scope remained Gate 2 only. The three findings are compatible with the
  approved adapter boundary and add no geometry substitutes, boundary evidence,
  IFC, Blender, inference, evaluation, or consumer migration.
- Strict TDD RED evidence:
  - the initial adapter run was `12 failed, 48 passed`; failures showed faces
    fabricated from `var(...)`, CSS-wide values, inline `!important`, and an
    external stylesheet marker, accepted whitespace/non-NFC ids, and emitted
    foreign/`foreignObject` geometry;
  - adapter provenance then failed all three real fixtures at `0.3.0` before
    the semantic version advanced to `svg-scene-adapter/0.4.0`;
  - a separate adversarial test proved `fill: context-fill` still fabricated a
    triangle before context-dependent simple values were made unresolved.
- CSS topology decisions now accept only a deliberately small deterministic
  subset. CSS-wide keywords, variables, functions, context-dependent values,
  `!important`, `@import`, SVG stylesheet links, and XML stylesheet processing
  instructions force faceless geometry with `unresolved_css_presentation`.
  No external stylesheet is fetched and no browser CSS engine was added.
- Every plain SVG `id` is validated once before emission. Empty ids retain the
  existing focused error; ids containing whitespace or changing under NFC are
  rejected. The same validated value drives global duplicate checks, fallback
  reservation, source identity, and neutral identity.
- Traversal retains namespace URI and local name separately. Only elements in
  the SVG namespace can become source geometry; foreign namespaces and the
  complete `foreignObject` subtree are excluded. Their explicit ids still take
  part in global duplicate detection and fallback-id reservation. Emitted
  source and mesh provenance records the SVG namespace.
- Focused GREEN evidence:
  - adapter-only final run: `61 passed in 2.48s`;
  - relevant legacy loader compatibility: `8 passed, 203 deselected in 0.17s`;
  - Gate 0, Gate 1, and Gate 2 importlib set: `178 passed in 3.06s`.
- Final full verification: `473 passed in 771.24s (0:12:51)` under the observed
  Pixi runtime Python `3.12.13`; the environment was not changed.
- Grill Me review found no unresolved CSS value that can create a face, no id
  normalization ambiguity, no foreign geometry leak, no fixture-name branch,
  and no Gate 3 behavior. Ponytail review retained only standard-library NFC,
  byte-marker, and namespace helpers plus the small required fill subset; it
  removed the obsolete local-name-only helper and added no dependency or CSS
  framework. All project-owned functions have English docstrings.
2026-08-17, Gate 2 parser compatibility and malformed-input repair checkpoint:

- Scope remained Gate 2 only. No Neutral Scene schema, inference, evaluation,
  geometry substitutes, IFC, Blender, or consumer behavior was changed.
- RED tests covered the legacy opt-in `_source_records` contract, malformed
  polygon points, malformed transform suffixes, repeated number-list commas,
  and parser `IndexError`/`AssertionError` from malformed SVG paths.
- The legacy loader now accepts `include_source_order=False` and exposes a
  traversal-ordered `_source_records` list only when explicitly requested.
  Existing default scene keys remain unchanged.
- Legacy number parsing is separator-aware: repeated/leading/trailing commas,
  malformed decimal fragments, nonfinite values, and transform garbage are
  rejected instead of being partially converted.
- Malformed modern SVG paths are converted to `path_parse_failed` uncertainty,
  including parser `IndexError` and `AssertionError`, rather than escaping as
  adapter crashes.
- Focused GREEN evidence: adapter-only `62 passed`; Gate 2 legacy regression
  set `4 passed` after the independent review repair.
- Full verification after the final repair: `478 passed in 775.37s`
  (`0:12:55`) under the Pixi runtime Python `3.12.13`; no environment change.
- Independent review found one P1 repeated-comma defect, which was fixed and
  covered before the final full-suite run. No remaining review finding was
  reported for scope, compatibility, uncertainty handling, or comments.

2026-08-17, Gate 3 functional geometry substitutes and task views checkpoint:

- Gate 3 now exposes source-independent `MassPatch`, `SurfacePatch`, and
  `AffordanceZone` records plus deterministic plan, vertical, occlusion, and
  clearance views. These records retain source ids and provenance and contain
  no perceptual weights or final scores.
- Plan projection unions triangulated faces, preserving disconnected
  components and interior rings instead of connecting source vertices across
  empty space. Coordinates are canonically oriented and ordered for stable
  JSON/test output.
- Ray evidence now respects origin, direction sign, zero-vector rejection,
  and height-band occupancy. Height bands test occupied ray segments rather
  than merely surface hits; tangent contacts are rejected by midpoint
  classification, and point-in-mesh parity is independent of triangle winding.
- Strict TDD RED evidence covered disconnected solids, upward/downward/zero
  rays, out-of-band intersections, tangent vertex contact, and mixed triangle
  winding. Final focused evidence: `17 passed`.
- Final full verification: `495 passed in 879.09s` (`0:14:39`) under Pixi
  runtime Python `3.12.13`; compileall and `git diff --check` also passed.
- Independent review initially found disconnected/holed topology, ray origin
  and direction, height-band bypass, tangent contact, and winding assumptions;
  each was repaired with a regression test. Final review approved Gate 3 with
  no blocking or important findings.

2026-08-17, Gate 4 weight-free multi-channel boundary evidence checkpoint:

- Gate 4 adds `features/boundary_evidence.py`: analyzer-derived evidence
  records over neutral `MassPatch` and `SurfacePatch` substitutes. Every record
  retains source refs, method, substitute provenance, geometric projection,
  tolerances, and explicit uncertainty, with no aggregate boundary weight.
- Physical continuity, walking permeability, visual permeability, and Gestalt
  continuity remain independent serialized channels. Body and visual queries
  use validated, finite, ordered height bands. A carpet-like surface can obtain
  location from referenced geometry while remaining non-mass and non-blocking.
- Subject relations use the nearest projected exterior or hole boundary point,
  not an interior centroid. Computation range produces `not_evaluated`, never a
  fabricated zero score. Disconnected geometry contributes all components'
  local height intervals.
- Strict TDD RED evidence covered four-channel low-cabinet semantics, a
  mass-free carpet, out-of-range relations, disconnected components, provenance
  serialization, referenced surface geometry, nearest-boundary distance, and
  malformed height queries. Final focused result: `9 passed`.
- Independent review found and verified repairs for first-component sampling,
  missing provenance, surface spatial location, interior-sample range distance,
  and invalid height-band inputs. Final review approved Gate 4 with no
  blocking or important findings.
- Final full verification: `504 passed in 914.83s` (`0:15:14`) under Pixi
  runtime Python `3.12.13`; `compileall` and `git diff --check` also passed.

2026-08-17, Gate 5 IFC4/Bonsai adapter checkpoint:

- Added the read-only IFC4 adapter and deterministic IFC4 fixture. IFC facts
  now terminate at Neutral Scene v2 with stable source ids, world-coordinate
  mesh provenance, placements, units, grids, groups, openings, materials,
  surfaces, explicit affordance zones, and structured uncertainty records.
- The adapter does not infer regions, paths, trends, boundaries, order, scores,
  weights, or column grids. Authored affordance geometry and purpose remain
  explicit facts; missing geometry, purpose, or furniture references remain
  auditable rather than becoming inferred defaults.
- `OM_Surface` type defaults and occurrence overrides are source-traceable;
  elevations are normalized to metres, non-length units are rejected, invalid
  occurrence overrides clear inherited values, and raw surface facts are not
  duplicated in unqualified SourceObject properties. Authored affordances
  retain an explicit optional `source_id` for cross-adapter handoff.
- Strict TDD RED/GREEN evidence covered invalid `IfcReal` optical values,
  non-length property units, type-level surface inheritance, invalid surface
  overrides, missing affordance purpose, source-id round trips, and reference
  auditing with and without geometry. All new/modified project-owned functions
  retain English-first docstrings and important-step English comments; short
  Chinese annotations remain supplementary only.
- Final focused verification: `225 passed in 5.45s` for scene contract, IFC,
  and SVG adapter compatibility tests. Three independent read-only reviews
  ended with no Critical or Important findings after repair.
- Final full verification: `568 passed in 879.64s` (`0:14:39`) under Pixi
  Python `3.12.13`; compileall, docstring audit, JSON/no-mutation checks, and
  `git diff --check` passed. Checkpoint: `JJ-05-ifc-adapter`.

2026-08-17, Gate 6 explicit Blender geometry and hybrid input checkpoint:

- Added `adapters/blender_geometry.py` as a source adapter for evaluated
  Blender mesh snapshots. It does not import `bpy`, does not classify ordinary
  meshes as IFC objects, and does not infer roles from names, visibility,
  collections, or bbox substitutes.
- `ifc` mode returns the selected IFC Neutral Scene unchanged. The
  `blender_geometry` mode uses only explicit selection and role mappings;
  `hybrid` mode keeps IFC as the base and adds only explicitly linked helpers.
  Explicit groups, grids, surfaces, affordances, openings, and domains are
  passed through with cross-record reference validation.
- Missing mesh, unknown selection/role/helper ids, duplicate record ids,
  dangling references, and invalid modes are rejected or represented as
  structured uncertainty. A valid explicit analysis domain updates the
  capability flags consistently. Hybrid composition uses immutable scene
  replacement and leaves the IFC source scene unchanged.
- Strict TDD RED/GREEN evidence covered mode isolation, no-payload IFC
  short-circuit, selection/link/role allowlists, missing mesh, JSON round trip,
  domain capability, duplicate ids, and dangling references. All new/modified
  project-owned functions retain English-first docstrings and important-step
  English comments.
- Final focused verification: `240 passed in 4.98s` for Blender, contract, IFC,
  and SVG adapter compatibility tests. Final independent review reported no
  Critical or Important findings.
- Final full verification: `583 passed in 811.86s` (`0:13:31`) under Pixi
  Python `3.12.13`; compileall, docstring audit, JSON/no-mutation checks, and
  `git diff --check` passed. Checkpoint: `JJ-06-blender-input-modes`.
