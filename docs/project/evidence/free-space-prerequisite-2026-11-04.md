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

Accepted Task 2 local jj commit: `e02d899b`, change `tnozwwmy`;
Task 3 continues as change `uvwnnrun`.

## Native matrix correction accepted

The corrected matrix assignment and bounded recovery passed independent
specification and quality review: **279 passed, 1 existing skip**, exit 0;
the two frozen file hashes remained unchanged. Accepted local jj commit
`a951c761` (change `uvwnnrun`). The earlier failure evidence remains historical.
Actual portable Blender checks now establish one stable managed drawing GUID
`2JRtSsvK9DueUJ6efD5Ihg`, repeated reuse, world Z 1.600000023841858 m,
native IFC SI agreement, non-unit handoff, injected post-sync rollback and
subsequent valid updates. No unrelated poses changed in the corrected update.
The verifier independently audited these root-executed native records; this
does not claim that the verifier executed the native mutations.

Native serialization saved a new derived file at
`outputs/design/free_space_prerequisite/native/analysis-plane-1p6-rna-fixed.ifc`:
408620997 bytes, SHA256
`06400121d7a60dc5a45e64b90c5c9310900103946b2f2fff6cae477c1f935f99`.
It retains the original project, 95 furniture objects and adds one drawing group
(38 total groups). The original IFC was not overwritten. Evidence:
`native-plane-rna-fix-create-reuse.json`, `native-plane-update-restore.json`,
`native-plane-nonunit-handoff.json`, `native-plane-fault-recovery.json` and
`native-derived-save.json` in the verification directory. IFC-only reopen and
the final native result/visual acceptance remain Task 5.

## Task 3 projected-domain participation accepted

Independent specification PASS / quality PASS; **314 passed in 11.64 s**,
exit 0. An additional independent analytic run passed 54 geometry/query/frame
cases, three audit/status invariants and six hole-point serialization roundtrips.
All three frozen candidate hashes remained unchanged. Exact domain shell/holes,
inclusive contact participation, positive-area occupancy, original/substitute
ownership, exclusions and conservative unknown states are retained. Evidence:
`task-3-verification.md`, `task3-independent-tests.log`,
`task3-independent-analytic-results.json` and before/after hash manifests.
Visual omitted for analytic cases. Fresh actual S3 binding/alignment and new
free-space values remain Task 5; no new real-scene result is claimed here.

## Saved native camera restoration accepted

The ordinary Bonsai IFC importer retains the managed drawing annotation but
omits its Blender camera. The observed original ensure failure is retained in
`native-ensure-missing-camera.json`; it is not treated as a successful reopen.
The bounded correction imports that same drawing through Bonsai inside the
existing owned transaction and recovery boundary. Corrupt native maps or extant
BIM bindings reject before import, rather than authorize a duplicate object.
Independent specification PASS / quality PASS: **306 passed, 1 existing skip
in 6.57 s**, exit 0, with both frozen hashes unchanged. Accepted local jj commit
`ca47cb83` (change `opyzytwx`); the separate cache candidate remains uncommitted.

Actual portable Blender restoration retained GUID `2JRtSsvK9DueUJ6efD5Ihg`,
STEP 3597397, one managed annotation and SI/world Z 1.600000023841858 m.
Repeated ensure reused the same camera; no unrelated object pose changed.
After reopening again, an injected failure after the real native importer had
allocated and linked its camera recovered the entire retained snapshot:
`snapshot_differences=[]`, 372 objects, no camera and no recovery block. A later
valid ensure restored/reused the same drawing successfully (373 objects).
Native evidence: `native-managed-camera-restored.json`,
`native-managed-import-fault-recovery.json`,
`native-managed-restore-after-fault.json`; independent scoped review:
`task-1-native-restore-verification.md`. Root executed the native mutations;
the independent verifier ran regressions and audited the receipts separately.

An additional independent bounded IFC audit verified both original/derived
hashes, all 95 furniture GUIDs, every original 37 group identity/membership and
the extra drawing-only group. Static source classification excludes the drawing
while retaining the slab's physical facts. Historical S3 support independently
equals its saved complete polygon: one component, no holes, 207.24092382549588 m²,
11 wall/member refs, zero symmetric difference and boundary distance. See
`task5-independent-lineage.json` and `task5-independent-s3-baseline.json`.
Fresh S3 confirmation, finite-band result, cache/native and visual acceptance
remain pending; this is not whole Task 5 completion.

## Task 4 persistent content cache accepted

Independent specification PASS / quality PASS. Exact acceptance: **416 passed
in 38.12 s**, exit 0; all 16 frozen candidate/dependency hashes stayed unchanged.
Independent artifact-only probes additionally counted the actual generation
boundaries and forbade all six, including legacy activation, on a fresh-process
disk hit. Pose restoration at audit revision 13 reused the original cache bytes
while publishing a new exact ResultRef with current query/support/binding.
Six Field states, deliberate per-cell metadata overrides/deletions and nested
calculation strings survived. Old/unverified/mismatched observations rejected;
fact/geometry/receipt changes, malformed entries and write/generation failures
received the expected miss/refusal/preservation behavior.

Production uses `outputs/blender_analysis/content_cache/v1/<content-key>.json`
through the existing fixed CLI and result wire. Validation precedes lookup;
cache hits skip projection, Field and display generation. Native recapture and
publication freshness checks remain mandatory. Cache retention has no eviction
policy; distinct content adds local files. Actual native S3 miss/hit/invalidation
and the source/result alignment view remain Task 5, not this code acceptance.
Evidence: `task-4-report.md`, `task-4-verification.md`, candidate hash manifests,
`task4-independent-*` executable probes/logs and the recorded exact suite log.
