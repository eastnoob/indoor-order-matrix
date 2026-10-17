# B3 frozen real-source partial field / visual review evidence

Date: 2026-10-08. Status: **partial diagnostic delivered for owner review; B3 remains open**. The primary plane rule is settled: IFC storey-bound datum + eye-height offset, here 0 + 1.6 = **world z=1.6 m**. Reliable real-mesh occupancy on this plane remains unsupported/partial. Eye band 1.55–1.65 m is comparison evidence; lower band 0.45–0.55 m is auxiliary diagnostic only. Neither replaces the exact eye-plane contract or creates a height-choice decision. Existing frozen A and attempt labels remain historical diagnostic metadata; no regeneration was performed to change labels.

Successful output: [`worker_b/attempt_004`](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/). Failed attempts 001–003 and their actual failures remain preserved. Worker A's capture, qualification and index are unchanged.

## Inspectable artifacts

- [Matplotlib overview](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/real_field_overview.png), [eye](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/provisional_eye_diagnostic.png), [lower](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/independent_lower_diagnostic_diagnostic.png).
- [Blender source + S3](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/blender_source_domain.png), [eye](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/blender_provisional_eye.png), [lower](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/blender_independent_lower_diagnostic.png), [disposable blend](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/b3_real_partial_disposable.blend).
- [Full samples and per-source geometry/provenance](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/field_samples.json), [final visualization manifest](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/field_visualization_manifest.json), [verification and hashes](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/final_verification.json), [execution](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/execution.json).

## Frozen inputs and channel limits

[Worker A qualification](b3-real-source-capture-qualification.md) supplies 354 actual evaluated Body meshes: 1,802,274 vertices and 3,543,857 triangles. All 38 historical structural geometries/transforms/roles/properties match; S3 retains **206.5209234821732 m² and two holes**. Its horizontal historical binding is retained, with no current live S3 rebinding or vertical-extent inference. Human Level 1 datum is world z=0 m at floor top, storey #13 / `2udSq8mkbQwxg0XrW$uM_r`; eye reference 1.6 m. Frozen vertices already use world metres and applied transforms. Slab support and semantic nonmass are excluded; canonical Analysis substitution policy is unchanged.

Both queries retain 189 eligible-mesh diagnostic projection records (including valid-empty helper results), 164 unsupported mesh records and no missing eligible helper output. Global closed/manifold eligibility is 190 including the excluded slab; A records 159 positive-area in-scope unsupported sources. Eligible flags do not certify exact solid queries. Complete occupancy, exact plane section, known-free and complete physical occupancy distance remain null/unsupported; the whole in-domain complete field remains unassessed. Group Gaussian is not_available without qualified groups.

| Query / world band | Raw approximation m² | Clipped approximation m² | In-scope unsupported height candidates | Clipped uncertainty support m² |
|---|---:|---:|---:|---:|
| Eye / 1.55–1.65 m | 19.539299333729176 | 0.014987329164664116 | 10 | 20.646636738299506 |
| Independent lower / 0.45–0.55 m | 27.669366581447175 | 10.70892965338737 | 72 | 33.70256360857361 |

Unsupported lists exactly match A. Uncertainty support is a full-height convex hull of actual XY vertices gated by observed height-range overlap; it localizes conservative support for unassessed candidates, never occupancy or total error. Approximation complement is not known free. Distances are separately measured to raw diagnostic projection and S3 boundary including holes, in metres. Neither is complete occupancy clearance, body clearance, width, visibility, perception, route or walkability.

## Sampling and directional evidence

Both queries keep four full variants: spacing 0.5/0.25 m and zero/quarter-spacing shifts. Coordinates and integer indexes match the accepted synthetic lattice helper. Each query contains 9,648 bounding-lattice points across its variants, with 8,231 domain points. Eight-neighbor adjacency permits all diagonals with no corner-cut filter.

| Spacing m / XY shift m | Total / domain points | Eye projection points | Eye vector / 4 / 8 components | Lower projection points | Lower vector / 4 / 8 components | Lower false-free / false-occupied / symmetric error m² |
|---|---|---:|---|---:|---|---|
| 0.5 / 0 | 960 / 815 | 0 | 1 / 1 / 1 | 33 | 2 / 1 / 1 | 2.743929 / 0.149999 / 2.893928 |
| 0.5 / 0.125 | 960 / 817 | 0 | 1 / 1 / 1 | 45 | 2 / 1 / 1 | 1.821428 / 1.251249 / 3.072677 |
| 0.25 / 0 | 3888 / 3323 | 0 | 1 / 1 / 1 | 168 | 2 / 1 / 1 | 1.724909 / 1.010979 / 2.735888 |
| 0.25 / 0.0625 | 3840 / 3276 | 0 | 1 / 1 / 1 | 154 | 2 / 1 / 1 | 1.685803 / 0.403124 / 2.088927 |

Components describe the diagnostic complement, not known-free space. Eye lattices miss the tiny clipped approximation; signed projection point-area error is -0.014987329164664116 m² for every variant. All eye directional reconstruction metrics are **null/not_available** with actual error `AssertionFailedException: Should never reach here: Unable to determine overlay result geometry dimension`. Working masks, boundary distance, approximation distance and complement components remain available. Owner ruling permits these explicit failed channels; no replacement overlay/slicing backend, S3 precision change or area-only retry was added. Lower reconstruction uses the existing accepted helper successfully and compares against the same approximation, never physical truth. No stability threshold or production resolution is selected.

Focused owner clarification: the two positive-area lower vector complement components measure **195.81199198035506 m²** and **0.0000018484299999996234 m²** (the latter is about **1.84843 mm²**). Thus the count discrepancy includes a microscopic component and does not establish a material isolated pocket. [Component inspection record](../../../outputs/design/b3_real_source_field/run_001/worker_b/attempt_004/lower_complement_component_inspection.json) includes validity, bounds and the unchanged field hash. Areas were measured from the saved complement only; no threshold, geometry repair, field/render regeneration or synthetic rerun was performed.

## Derived union processing and visual inspection

`projection_union_processing` and `support_union_processing` record every input's validity/type/area and leaf types, pre-area-view union and output validity/types, removable component lengths/areas, actual area deltas, and `make_valid_applied=false`. Invalid inputs fail visibly. No invalid positive-area parts are discarded. Actual pre-area-view unions contain only valid polygons: eye projection/support each 11 parts, lower projection 53 and support 64. No line/point components were removed in this run. Repeating polygon union changes only the recorded floating-point projection areas by 3.552713678800501e-15 m² (eye) and 1.0658141036401503e-14 m² (lower); support deltas are zero. Raw per-source geometry, helper projection/uncertainty and frozen mesh references remain in the field evidence.

All six PNGs were actually viewed by the agent: nonblank content; visible S3 exterior and two holes; distinct magenta approximation and orange uncertainty; metre axes/equal aspect; readable partial/unknown-complement labels; no incoherent overlap or clipped labels. Three Blender renders visibly contain actual Body furniture/structure, with source-only, eye and lower views distinguishable. Blender uses ring strokes whose width is display-only. The overview shows vertex hull audits rather than claiming an actual source mesh render. Owner accepted this package as a bounded partial diagnostic, not B3 completion; the final verification owner-review record supersedes earlier pending-review labels. Runtime metadata preserves its original pre-inspection state; finalized inspection findings are in execution, visualization manifest and final verification.

## Commands, integrity and boundary

- `pixi run pytest test/test_b3_real_field_diagnostic.py -q`: exit 0, **8 passed in 0.14s** after the owner-directed repair.
- `pixi run python scripts/design/space_field/run_b3_real_field_diagnostic.py --attempt 4`: exit 0. Portable Blender **5.2.0 LTS** exit 0 via `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe --background --factory-startup --python scripts/design/space_field/render_b3_real_field_blender.py -- <attempt_004>` (full absolute command retained in execution).
- `pixi run python outputs/design/b3_real_source_field/run_001/worker_b/verify_real_field.py`: exit 0. Strict JSON rejects duplicate keys and NaN/Infinity and re-dumps with `allow_nan=False`; all lattice coordinates/indexes/counts and unknown channels checked; 381 unique references checked, 366 A package entries unchanged, 74 unrelated baseline files unchanged. Function docstrings and trailing whitespace pass. Manifest plus separate final verification avoids circular self-hashing.

Writes are bounded to two new design scripts, focused tests, the two B3 documents, this evidence note, and worker B artifacts/verification script. No agent, fork, chat message, commit/push/merge, full pytest, live Blender/IFC/source mutation, other Blender installation, or new dependency was used. Accepted synthetic runner/tests and run_002 are unchanged. Original IFC current bytes and live S3 selection were not rebound; frozen capture hashes and source identity remain the evidence boundary. The saved `.blend` was runtime-created and hashed; it was not interactively reopened.

Remaining review concerns reliable real-mesh occupancy on the settled eye plane, missingness contract, resolution/origin, tolerance/stability claims, backend/geometry capability, and minimal field handoff; route, body, perception and Bayesian choices remain unfrozen. **This partial diagnostic does not close B3.**

Owner handback scope limitation: `scripts/design/live_domain/` was observed as unrelated external state during the final Git scope check. Its three visible files (`blender_panel.py`, `check_live_capture.py`, `run_live_domain.py`) were not altered, deleted or adopted. Repository Git status contains unrelated work, so this package makes no claim that all new Git paths belong to worker B. The earlier 366 immutable A entries and 74 unrelated baseline-file checks remain recorded evidence, not a repository-wide cleanliness claim. Finalization updates only this note and final metadata; no additional test, render, field generation or broad audit loop was run. Existing eight passing tests and Blender exit 0 remain the validation evidence. Remaining work is reliable occupancy on fixed world z=1.6 m, never selecting another height.

STOP FOR B3 REAL-SOURCE FIELD AND VISUAL INSPECTION REVIEW
