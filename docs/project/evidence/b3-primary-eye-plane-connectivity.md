# B3 PRIMARY eye-plane connectivity comparison

**Status: OWNER ACCEPTED** — final run `run_20261008T214917Z_5c7dab`. The owner reviewed runner/tests, serialized counts and memberships, directional areas, edge diagnostics, final PNG and this completed evidence note. Acceptance is conditional on the already accepted serialized S3-clipped targets and floating-point open-interior reference. This bounded design-only package compares conditional empty under the owner-accepted PRIMARY world-z=1.6 m qualification. It does not establish complete physical occupancy, physical free space, routes, visibility, walkability, or certified exact arithmetic. B3 remains **OPEN**; next is stage 6 field-contract/minimal-handoff discussion with the user.

## Inputs and reach

The immutable accepted input is `outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/{field_samples.json,source_sections.json,artifact_manifest.json}`. Historical S3 has area 206.5209234821732 m² and two holes. The IFC storey #13 human datum of 0 m plus eye offset 1.6 m remains PRIMARY. Source qualification, height and Blender evidence are reused; meshes/sections are not regenerated.

Only the new design runner `scripts/design/space_field/run_b3_eye_plane_connectivity.py`, new focused test `test/test_b3_eye_plane_connectivity.py`, fresh connectivity output runs, this evidence note, the exploratory plan and deliverable design are touched. Existing helpers are imported unchanged. No production implementation, dependency, API/export/model/UI, IFC/live S3, Git write, agent/chat or B3 closure is included.

The runner verifies the accepted manifest byte counts/hashes of both serialized field and source-section inputs, units, PRIMARY height, historical S3 metadata and all 9,648 sample records. Original sample masks, positions, unresolved IDs and separate boundary/raw-qualified distances remain in the immutable field reference. Component memberships use `v<accepted variant index>:<cell_i>:<cell_j>` IDs. Complete physical clearance remains null.

## Reference and preserved raw-path failure

The S3 comparison uses the **accepted serialized S3-clipped qualified occupied and unknown-support targets**. The owner explicitly ruled this within scope. Polygon interiors of their difference from S3 form the floating-point conditional-empty reference. Per-source section-boundary ambiguity is still checked; an interior residual prevents the affected geometric reference from being promoted. No buffer, make_valid, snap, weld, precision change, adaptive refinement, numerical retry or positive-area deletion tolerance is applied. All positive-area components remain, including tiny ones.

The first attempt `outputs/design/b3_eye_plane_connectivity/run_20261008T214017Z_d8a0b6/` instead subtracted raw geometries. It exited 0 as an evidence run but correctly retained `geometric_reference_status=not_available`, null reference area/component count, and the original error `ValueError: Unresolved interior section-boundary linework at source-boundary indices [32]`. Its independently computed graphs survive. No figure exists for that unavailable reference. This attempt is retained and is not passed reference evidence.

One owner-requested inspection identifies boundary index 32 as source **`live-step-3556226`**, name `furnishingelement`. Residual length is **0.020493629666047758 m**, bounds `[20.64908409898817, 12.040472672855485, 20.664895719870355, 12.053510368279413]` m. The line runs from `(20.664895719870355, 12.053510368279413)` to `(20.64908409898817, 12.040472672855485)` m. This is recorded once without repair or further materiality investigation. The raw and accepted-clipped floating-point operation paths are not certified identical. Raw geometry retains its separate audit/distance meaning through the accepted field reference.

## Graph and diagnostic contract

Vertices are only accepted in-domain samples where `occupancy_value is False` and `known_free_under_qualification is True`. Unknown/outside samples never become occupied or empty. Accepted positive-over-unknown classification is preserved. Four-neighbor and unrestricted eight-neighbor BFS retain every membership; geometry diagnostics never filter edges or apply a corner-cut rule.

Samples map to **open** geometric component interiors. Accepted `domain.covers` boundary points remain vertices and are explicitly unassigned when no open interior covers them. Evidence includes individual component geometries/areas, component sizes/sample memberships, missed components, graph merges and geometric splits. Edge diagnostics count positive-length unknown/mass/outside/hole crossings, independent unknown/section/domain-boundary contacts, and differing geometric membership; each graph retains coordinate-linked examples. Domain-boundary contact includes corner tangency even when positive-length hole/outside crossing is zero.

Point-center count times spacing² is nonconservative. Clipped center-labelled cells are diagnostic only; directional false-empty/missed-empty and symmetric differences are independent operations. Uncovered-domain area uses footprints of all **in-domain** sample centers, including unknown/occupied centers. A geometry failure preserves original exception text and null/not_available affected outputs while independent graphs survive. No field cell is conservatively certified empty by these areas.

## Completed output and results

Final output: [`run_20261008T214917Z_5c7dab/connectivity.json`](../../../outputs/design/b3_eye_plane_connectivity/run_20261008T214917Z_5c7dab/connectivity.json), [`artifact_manifest.json`](../../../outputs/design/b3_eye_plane_connectivity/run_20261008T214917Z_5c7dab/artifact_manifest.json), [`execution_review.json`](../../../outputs/design/b3_eye_plane_connectivity/run_20261008T214917Z_5c7dab/execution_review.json) and [`connectivity_comparison.png`](../../../outputs/design/b3_eye_plane_connectivity/run_20261008T214917Z_5c7dab/connectivity_comparison.png).

The reference has **one** positive-area component, area **187.43674928287297 m²**. Its complete geometry and individual area are serialized. Both 0.25 m four-neighbor graphs split that same reference into a large component and a small top-boundary group. These are sampled splits, not vector isolated pockets. Eight-neighbor total counts agree with the reference but retain crossing/contact disagreements; count agreement does not certify connectivity or stability.

| Variant | Spacing / XY shift (m) | Empty vertices | Geometric / 4 / 8 components | 4-component sizes | Center area (m²) | Missed / merged / split under 4 |
|---|---|---:|---|---|---:|---|
| v0 | 0.5 / 0 | 744 | 1 / 1 / 1 | 744 | 186.0000 | 0 / 0 / 0 |
| v1 | 0.5 / 0.125 | 745 | 1 / 1 / 1 | 745 | 186.2500 | 0 / 0 / 0 |
| v2 | 0.25 / 0 | 3015 | 1 / 2 / 1 | 3014 + 1 | 188.4375 | 0 / 0 / 1 |
| v3 | 0.25 / 0.0625 | 2978 | 1 / 2 / 1 | 2975 + 3 | 186.1250 | 0 / 0 / 1 |

Every eight-neighbor correspondence has zero missed/merged/split components; every graph has zero unassigned boundary/reference samples. The membership check matched all **7,482** conditional-empty vertices exactly once per adjacency, excluding all 749 unknown and 1,417 outside samples across the 9,648 accepted records. Zero occupied centers does not erase the tiny positive qualified geometry. All per-source boundaries remain checked, with no interior residual on this accepted-clipped reference.

The isolated 4-vertex `v2:38:47` is at `(14.775000095367432, 12.175000011920929)` m. The three-point `v3:4c1` is `v3:36:47`, `v3:37:47`, `v3:38:47`, at X `14.337500095367432`, `14.587500095367432`, `14.837500095367432` and Y `12.237500011920929` m. These complete memberships and open-interior assignment to component 0 are explicit evidence beyond total counts.

| Variant | Clipped reconstructed empty (m²) | False-empty (m²) | Missed-empty (m²) | Symmetric difference (m²) | Uncovered domain (m²) |
|---|---:|---:|---:|---:|---:|
| v0 | 183.977296 | 1.001014 | 4.460467 | 5.461481 | 4.838628 |
| v1 | 182.775824 | 1.173604 | 5.834528 | 7.008132 | 5.870099 |
| v2 | 186.773052 | 0.656886 | 1.320584 | 1.977470 | 1.010373 |
| v3 | 184.787190 | 0.360678 | 3.010237 | 3.370915 | 3.191858 |

All final area operations computed without error. Values in this table are rounded; JSON retains original floats. Center-area errors are respectively -1.4367492828729667, -1.1867492828729667, +1.0007507171270333, -1.3117492828729667 m². These do not cancel the directional disagreements.

| Variant | 4 / 8 edges | Affected 4 / 8 edges | Unknown crossing 4 / 8 | Outside or hole crossing 4 / 8 | Hole crossing 4 / 8 | Domain-boundary contact 4 / 8 |
|---|---|---|---|---|---|---|
| v0 | 1399 / 2747 | 1 / 3 | 1 / 2 | 0 / 1 | 0 / 0 | 0 / 1 |
| v1 | 1405 / 2757 | 0 / 5 | 0 / 2 | 0 / 3 | 0 / 1 | 0 / 3 |
| v2 | 5852 / 11587 | 1 / 10 | 1 / 1 | 0 / 9 | 0 / 2 | 0 / 9 |
| v3 | 5779 / 11446 | 0 / 11 | 0 / 2 | 0 / 9 | 0 / 3 | 0 / 9 |

Reason counts overlap and do not sum to affected-edge counts. Section-boundary contacts follow the domain-boundary counts above; unknown-boundary contacts follow the unknown-crossing counts. Qualified mass-interior crossings and differing geometric membership are zero for all final graphs. A diagnostic example is v0's axis edge `(14.900000095367432, 11.550000011920929)` to `(14.900000095367432, 12.050000011920929)` m crossing unknown support even while endpoints remain accepted conditional empty. Another is v1's diagonal `(15.525000095367432, 6.675000011920929)` to `(16.02500009536743, 6.175000011920929)` m crossing a hole and contacting domain/section boundaries. Graphs retain both edges. JSON stores up to eight examples per adjacency/variant.

## Attempts and figure inspection

`run_20261008T214127Z_c430a5` was interrupted (observed exit 1) while diagnostics repeatedly used zero-area clipped contact fragments as positive mass crossings; its `execution.json` records the reason and absence of a completed result/figure. The final implementation uses every positive-area occupied polygon interior for mass crossing, retaining original source boundary contacts and the reference ambiguity guard. No tolerance, repair, new dependency, spatial filtering or prepared-predicate mechanism was introduced. This correction also removed the observed runtime bottleneck.

`run_20261008T214816Z_f6b504` completed (exit 0), and its PNG was viewed once. Its lower subplot titles overlapped the preceding panels. The only following code change increased subplot vertical padding; a fresh run `run_20261008T214917Z_5c7dab` was already executing when the owner advised render-only reuse, so that run was allowed to finish (exit 0) and no further numeric runs/tests were started. Both earlier result and PNG remain. The final PNG was viewed once: orange unknown support, both holes, known-empty samples, geometric component and red coordinate-linked diagnostic edges are readable, axes are in metres, and titles are separated. Tiny qualified mass is below overview scale; its accepted geometry/reference remains available, with no refinement for display. No Blender rerun is needed.

## Verification and step-6 boundary

The first focused test invocation exited 1 on the valid-empty geometry boundary edge case (8 passed, 1 failed). The implementation now returns a computed empty reference before testing nonexistent empty boundaries. The next invocation exited 0 with 9 passed in 0.45 s. Owner review added independent domain-boundary contact and metre plot axes; its direct square-hole corner-tangent regression is included (10 passed in 0.46 s). After the zero-area mass-contact correction, the final affected check was `pixi run pytest test/test_b3_eye_plane_connectivity.py -q`, exit 0: **11 passed in 0.48 s**. Tests also cover unknown separators, positive override, unrestricted diagonal versus point contact, a narrow missed connector, equal-count membership merge/split discrepancy, tiny missed components, covered boundary samples, and unavailable/error propagation without graph loss. The subsequent plot-padding-only edit reused this numeric/test evidence.

`pixi run python scripts/design/space_field/run_b3_eye_plane_connectivity.py` final exit is 0. One bounded output inspection via Pixi checked complete graph memberships and computed correspondence/edge statuses, both manifest artifact byte counts/hashes, and the final runner hash; it exited 0. Accepted artifacts were consumed unchanged. No general Git cleanliness or unrelated-change ownership claim is made.

The smallest supported step-6 discussion is a serialized conditional tri-state sample/provenance/status handoff with connectivity retained as separate diagnostics. The owner still needs to decide whether this conditional qualification is sufficient for the intended consumer, how boundary/unassigned samples should be exposed, and whether any graph adjacency is appropriate for that consumer. No resolution, stability tolerance, route semantics or production topology policy is selected here; unresolved source qualification must remain visible.

The owner acceptance preserves the raw-path unavailable reference, original boundary residual/error, interrupted attempt and rendering history above. Unrestricted 4/8 adjacency and reconstructed cells are not promoted to production topology, routes or certified empty cells. Artifact producer/review-record statuses reflect their generation before this ruling; this documentation records the subsequent owner acceptance. No checks, numeric/Blender reruns, implementation or optimization followed the ruling.

Full suite and Blender rerun are skipped; accepted source/Blender evidence is reused. Floating-point path sensitivity and incomplete physical occupancy remain material limits. **OWNER ACCEPTED — B3 OPEN; next: stage 6 field contract/minimal handoff discussion.**
