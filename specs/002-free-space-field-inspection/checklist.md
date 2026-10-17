# Living Checklist: Free-Space Field Inspection

**Purpose**: Track planning readiness and owner acceptance boundaries.
**Created**: 2026-10-10
**Feature**: [spec.md](spec.md)

## Input Integrity

- [X] `run_20261009T142454Z_0d7308` is the only normative package named by the
  plan.
- [X] Capture and package hashes are authenticated before projection.
- [X] Explicit frame, units, datum, effective view offset, and domain holes are preserved.
- [X] Per-proxy binding/object provenance is present on normalized records.

## Semantic Boundaries

- [X] Whole-height projection is separate from historical `z=1.6 m` sections.
- [X] Runner-local transport builds `NeutralSceneV2`, calls
  `analysis_scene_view`, and only then constructs `FreeSpaceField`.
- [X] Physical occupancy includes non-furniture sources.
- [X] Boundary membership is consumed from upstream exact identity.
- [X] The exact five unresolved owners carry canonical `missing_geometry`
  uncertainty before shared-view promotion; captured refs/arrays are
  audit-only and renderer diagnostics cannot erase global `unknown`.
- [X] Explicit domain geometry retains both holes and frozen source-origin metadata.
- [X] `False` is documented as empty physical occupancy, not walkability.
- [X] No Field API, resolver, evaluator, room-model, B3 loader, clearance, or
  connectivity expansion is planned; live promotion and B3 remain open.

## Output Contract

- [X] Side-by-side source and field layers are specified.
- [X] All six statuses have distinct visual states.
- [X] `build_field_layer_manifest` remains the semantic source.
- [X] Shared provenance deduplication has exact recovery semantics.
- [X] Timings and output sizes are recorded.
- [X] `0.25 m` is labeled demonstration-only.

## Verification Gate

- [X] Focused tests are written only during implementation.
- [X] Revised artifact records exact final JSON/HTML bytes, accepted proxy
  coverage, frozen unknown ids, and embedded payload presence.
- [X] Output-only offline evidence is saved under the final run directory;
  B3 remains open and no Field/resolver core was changed.
- [X] Formal reuse mode re-authenticates frozen inputs and routes field,
  manifest, renderer, and final writing through the shared runner path.
- [X] Synthetic focused tests cover two-hole projection, reuse offsets,
  provenance recovery, binary embedded-payload equality, global unknown,
  duplicate ownership, and ROOT-resolvable ledger paths.
- [X] New whole-height cells are compared to current `FreeSpaceField.evaluate`.
- [X] SC-002 compares current displayed/serialized cell records, not the
  historical 9,648 eye-plane samples.
- [X] Frozen input hashes remain unchanged.
- [X] Frozen input hashes are recorded in the replayed acceptance manifest.
- [X] SC-002/SC-007 replay compares all 3,969 cells with zero mismatches.
- [X] No Blender/live IFC run is required for this checkpoint.

## Notes

The historical 9,648-sample, zero-mismatch result belongs to the eye-plane
section package and is retained as input evidence only, not as the new
whole-height acceptance sample.

## Verification Boundary

T025 was not triggered: canonical `missing_geometry` uncertainty preserved all
five unresolved owners without changing `features/*`. Static HTML, embedded
payload, and focused-test evidence are available, but direct browser
load/cell-click verification was not completed because the in-app browser
rejects `file://` URLs. This remains a manual quickstart check; no local
server was introduced.

The final offline evidence is
`outputs/design/free_space_field_inspection/run_20261010T160739Z_23dd5d`:
manifest SHA-256
`50dfc30f9d94097962dc5356bc86cce948b2354010a4d0857eb9a94d4ab81f9e`,
JSON `20,236,648` bytes, HTML `12,745,043` bytes, and 3,969 cells.
SC-002 and SC-007 report zero mismatches; the ledger contains 368 entries
(354 captured meshes, 3 proxy objects, and the authenticated package records).
The final focused test run reports 8 passed and runner `py_compile` succeeded;
these are offline checks, not browser interaction evidence.
