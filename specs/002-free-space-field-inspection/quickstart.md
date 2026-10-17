# Quickstart: Free-Space Field Inspection

This is the validation guide for the implemented output-only inspection
runner. It must run from the repository root with Pixi Python and must not
launch Blender.

## Inputs

- Frozen capture: `outputs/design/b3_real_source_field/run_001/`
- Successful package:
  `outputs/design/b3_shared_occupancy_enrollment/run_20261009T142454Z_0d7308/`
- Read-only seam review:
  `delegated/locked-input-seam-review.md`

The runner must authenticate `artifact_manifest.json` and every consumed mesh,
record `world_xy`, metres, explicit `[0.0, 0.0]` offset, and
`whole_height_plan`. It must build a runner-local whole-height
`NeutralSceneV2`, preserve the five unresolved ids before geometry promotion,
call `analysis_scene_view(neutral_scene)`, and only then construct
`FreeSpaceField`. It must not call the historical section `transport_scene()`
unchanged or create a direct-preview resolver.

## Run

```powershell
pixi run python scripts/design/space_field/run_free_space_field_inspection.py
```

For output-only regeneration from a validated projection handoff:

```powershell
pixi run python scripts/design/space_field/run_free_space_field_inspection.py `
  --reuse-projection outputs/design/free_space_field_inspection/run_<validated-handoff>
```

The command should write a fresh run directory under
`outputs/design/free_space_field_inspection/` containing:

- a self-contained HTML file with inline SVG;
- the normalized input audit;
- the field-layer manifest and shared provenance table;
- timing and output-size measurements;
- a refusal or success execution record.

## Expected acceptance checks

1. The HTML opens directly from disk and shows source geometry and field cells
   side-by-side.
2. The domain retains its exact holes and the boundary-scoped
   `live-step-6231` record is shown as upstream-excluded rather than inferred.
3. Tables, chairs, plants, counters/bar geometry, and other physical-context
   records remain visible; occupancy is not rebuilt from furniture only.
4. Three accepted proxies cover seven owners exactly once and retain per-proxy
   provenance.
5. The five unresolved owners remain `unknown` under the current global Field
   contract. Diagnostic hulls do not make those cells free.
6. Every displayed cell matches the current `FreeSpaceField.evaluate` result
   after shared-provenance recovery.
7. The artifact states that `0.25 m` is demonstration resolution and that
   `False` is not walkability, clearance, connectivity, or certified area.
8. Timings include projection, field evaluation, and serialization; sizes
   include JSON and HTML bytes.

Opening the generated HTML directly and clicking cells remains a manual
browser check. The current evidence includes static HTML/embedded-payload and
focused-test verification, but no successful in-app browser load because the
browser refuses `file://` URLs; no local server is required or introduced by
this slice.

The historical enrollment evidence of 9,648 samples and zero mismatch is
input-history evidence for the `z=1.6 m` section package only. It is not rerun
and is not the whole-height acceptance criterion for this feature.

## Latest Offline Evidence

The current offline delivery is
`outputs/design/free_space_field_inspection/run_20261010T160739Z_23dd5d`.
Its `inspection_manifest.json` SHA-256 is
`50dfc30f9d94097962dc5356bc86cce948b2354010a4d0857eb9a94d4ab81f9e`;
the JSON and HTML sizes are `20,236,648` and `12,745,043` bytes. The artifact
contains 3,969 cells, and the recorded SC-002 and SC-007 comparisons have zero
mismatches. The 368-entry input ledger covers 354 captured meshes, three proxy
objects, and the authenticated package records.

This evidence accepts the offline whole-height output and data-consistency
slice only. Direct browser loading and cell-click interaction remain
unverified because the in-app browser rejects local `file://` URLs; B3/live
promotion, clearance, and connectivity remain open.
