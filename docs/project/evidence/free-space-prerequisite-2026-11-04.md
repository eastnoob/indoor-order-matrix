# Free-space prerequisite evidence — 2026-11-04

Plan: [checklist](../../superpowers/plans/2026-11-04-free-space-prerequisite-checklist.md).
Workspace: `free-space-cache`, `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache`.
Starting base/change/revision: `9c0b024b` / `vvnuuksk` / `e77e4b99`.
Root is the only version writer; accepted changes are local jj commits.

## Task 0 baseline

Independent agent `freespace_baseline_verifier` ran the nine-file baseline command
in the checklist under Pixi Python 3.12.13 with PYTHONNOUSERSITE=1 and the main
embedded OCTA tree on PYTHONPATH. Result: 507 passed, 1 installed svgutils escape
warning, 33.84 s, exit 0. All 20 source/test hashes were unchanged before/after.

Log: `outputs/design/free_space_prerequisite/verification/task0-baseline.log`,
SHA256 `7fcaa726387a263e7c85b1093e2c41fbe66c96393c5d383d397027b60b75d46d`.
Report: `outputs/design/free_space_prerequisite/verification/task0-baseline-report.json`.
This establishes the existing baseline, not acceptance of new functionality.

Native lifecycle reconnaissance verified the installed portable Bonsai drawing
API. Native DRAWING/camera is the plane authority. Default creation can be Z=0;
an explicit world-metre pose and persistent marker are needed. Static IFC role
classification currently misses DRAWING. Live Blender was unavailable because
no Blender process was running; no live placement or save/reopen is claimed.

Task 0 visual: omitted; file identities, tests and interface assessment suffice.
Accepted local jj commit: `d591c91d`, change `vvnuuksk`; subsequent implementation
continues in the same workspace as separate changes.
Independent preflight review: specification PASS, quality PASS; preceding 78
documentation lines preserved. Original IFC hash matches the checklist. S3
manifest/result SHA256 are respectively
`21d6bc7b3164a12d51c03790febabca672b6855ebbea9f00f87224dba8d12055` and
`12c2d7e7e8729df9b6faa90afaae5f96dbe51649accf4f84d83258203d370fa7`.
The accepted active confirmation and retained capture bindings match. Independent
shoelace area is 207.2409238254956 m²; domain triangle area is
207.24092382549563 m², with no holes. Historical camera at about 4.6 m is not
accepted as the new plane; retained domain meshes are world geometry at Z=0.

The specified portable Blender was launched and the original source loaded in a
new disposable session. MCP verifies project `2uGd6yom9GZe5$z7LfbGW0`, 37 groups,
95 IfcFurniture, one reciprocally linked selected slab with bounds about
[-0.3, 0.0] m, unit scale 1, and no native DRAWING. Evidence is
`outputs/design/free_space_prerequisite/verification/native-preflight.json`.
This is runtime preparation, not new lifecycle or free-space acceptance.

## Task 1 native plane lifecycle

The frozen fix-round-1 candidate passed independent specification and quality
review. The verifier reran the four-file acceptance: **270 passed, 1 skipped in
5.57 s; exit 0**. The skip is an unavailable pre-existing real-IFC smoke fixture.
All eight candidate hashes stayed unchanged through tests and independent probes.
Source SHA256 is `dafb607a05969fee5fa68dc5057aff24e55ae5398f9f0f0388d75b51807095a9`;
its lifecycle test SHA256 is
`23febffffd19ddb7a1ddfc7305a82efccc7b0e929f60cc99d72f446516733814`.

The original review found a valid unrelated drawing could be returned through
an inconsistent native reverse map. It was corrected before acceptance. Four
independent discovered/explicit identity and same/changed elevation probes now
refuse before mutation; post-sync identity substitution recovers the owned
snapshot and a subsequent valid update succeeds. Native camera ownership is
persistent `OM_AnalysisPlane` on the native DRAWING annotation, and live/static
physical inventories exclude drawing cameras without a slab-class exemption.

Evidence under `outputs/design/free_space_prerequisite/verification/`:
`task1-fix-round1-acceptance.json`, `task1-fix-round1-acceptance.log`,
`task1-fix-round1-hashes-final.json`, and `task1-fix-round1-probes.log`.
Detailed original failure and scoped passing rereview remain in this plan's
`task-1-verification.md`. Visual omitted: exact identity/pose/role assertions
suffice here. Actual portable Blender creation, native save/reopen, loaded-byte
proof and visible alignment remain Task 5 pending. The unit seams use genuine
IFC transactions and serialization, not a completed real runtime acceptance.

Datum wiring, scope audit, content caching and real-scene acceptance remain open.

Accepted Task 1 local jj commit: `ccae2b27`, change `wlkuvxrk`;
Task 2 continues as change `tnozwwmy` in the same workspace.

## Task 2 selected slab datum and finite height band

Independent specification PASS / quality PASS after fix round 1. Required
five-file acceptance: **342 passed in 11.18 s, exit 0**. All nine actual hashes
matched the frozen manifest before and after acceptance and supplemental probes.
The optional immutable `AnalysisRequest.height_band_datum` retains the complete
verified slab receipt; the UI queries its upper surface to the selected plane.
Frozen execution validates the receipt's self/project/slab/storey/containment,
exact five-key geometry digest and recomputed top before occupancy. Generic
datum-free finite bands, whole-height and exact-section queries remain usable.

Independent review caught exact normal equality rejecting valid noncardinal
native camera rotations. The corrected feature-side frame check uses the
existing 1e-9 plane precision; the original ten-case native-reader probe now
passes, malformed inputs and actual orthonormal tilt/downward frames still
refuse. Source SHA256:
`a2cdc5806876f22c414558aac04f6b60dfdd99427cec749bcae89ddab85c3198`.
Evidence: `outputs/design/free_space_prerequisite/verification/task2-round1-*`
and this plan's `task-2-verification.md`, preserving the original failed review.
Visual omitted for the wiring; real datum/plane mapping stays Task 5.

## Early Task 5 native lifecycle finding — correction in progress

Accepted Task 1 bytes were loaded from this workspace in the specified portable
Blender (PID 23544), replacing the old spec004 adapter imports in this disposable
session. The actual creation check failed: requested 1.6 m became 0 m, and owned
recovery reported mismatched object poses. No plane success or new IFC save is
claimed. Reopening the unchanged original source resets the failed scene safely.
The independent native RNA probe proves row tuples assigned to `matrix_world`
are transposed; `mathutils.Matrix(rows)` preserves the intended translation.
The same assignment pattern affected create, scoped unit conversion and restore.
Task 1 native correction is in progress and must pass a fresh native test before
the actual free-space run. Evidence: `native-plane-create-reuse.json`,
`native-plane-diagnostic.json`, `native-matrix-assignment-probe.json`, and
`native-source-reload-after-failure.json` under the verification directory.
