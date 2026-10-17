# Implementation Plan: Free-Space Field Inspection

**Branch**: `002-free-space-field-inspection` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

## Summary

Build one offline inspection seam that authenticates the successful frozen
whole-height package, normalizes its distributed records into an explicit
`FreeSpaceField` input, evaluates the declared demonstration lattice, and
writes a self-contained HTML/SVG view. The seam is output-only: it does not
promote the field into `evaluate_scene`, `room_analysis_model`, the B3 loader,
or any live adapter.

The normative input is the package artifact set, not `preview_input.json` alone.
The normalizer adds explicit zero offset and per-proxy binding provenance, then
reuses `FreeSpaceField` and `build_field_layer_manifest`. Rendering may
deduplicate repeated global provenance into a shared table with exact
per-sample references. It must not add local-unknown semantics to the Field API.

## Technical Context

**Language/Version**: Python 3.12.13

**Primary Dependencies**: Existing standard library, Shapely, existing
`features.free_space_field.FreeSpaceField`, and
`features.space_field_visualization.build_field_layer_manifest`; no new dependency

**Storage**: Immutable JSON package inputs and one self-contained HTML/SVG
artifact under a fresh `outputs/design/` run directory

**Testing**: Focused pytest tests for normalization, provenance recovery,
status rendering, and the offline artifact contract; no Blender or live IFC
test. Browser loading/cell-click verification remains a manual quickstart
check and was not performed in the current evidence.

**Target Platform**: Offline local filesystem and modern desktop browser

**Project Type**: Design runner plus static inspection artifact

**Performance Goals**: Measure projection, field evaluation, serialization, and
output bytes for the pinned demonstration run; do not set a premature
optimization budget

**Constraints**: No live Blender/IFC, no side-effectful runner import, no
semantic recomputation during rendering, no new Field API, no second semantic
field, explicit whole-height query only, zero offset recorded explicitly

**Scale/Scope**: 358 source records, 354 captured body meshes, 343 selected
whole-height records, 95 furniture records, 245 physical-context records,
three accepted proxies covering seven owners, five unresolved owners, and a
declared `0.25 m` demonstration lattice

## Constitution Check

The repository constitution is an unratified placeholder. This plan records no
constitution compliance claim. The output-only runner and renderer are
implemented under review; final artifact acceptance remains separate. Existing
project rules still apply: preserve
source ids/provenance/uncertainty, keep physical occupancy separate from
furniture eligibility, keep live/evaluator/B3 promotion out of this
implementation-under-review checkpoint, and keep architecture documentation
synchronized.

## Input Evidence and Seam

The locked entry is:

```text
outputs/design/b3_shared_occupancy_enrollment/run_20261009T142454Z_0d7308/
```

The source capture is:

```text
outputs/design/b3_real_source_field/run_001/
```

Observed evidence:

- `capture_manifest.json`: schema
  `b3-real-evaluated-body-capture/v1`, Blender `5.2.0 LTS`, source IFC in
  millimetres, `source_to_m=0.001`, world units metres, source IFC SHA-256
  `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`,
  408,617,800 bytes, and 358 inventory records.
- `structural_capture.json` SHA-256
  `42e60698acef956364eb2b441051f0c22d019b4f9a672492678e0ee8097fba25`.
- `s3_scope.json` SHA-256
  `94a28a5f513091e683303fa091081d519769b5a38980cff2438d91a2cfc5591`;
  floor datum `0.0 m`, world XY, outline digest
  `65ae4d9ce2d5f64109fe9165a06aad5cf1cfbcc7ad7639c8fe19de8ad1a20287`,
  recomputed area `206.5209234821732 m2`, historical eye offset `1.6 m`.
- `b3-physical-occupancy-bindings.json` SHA-256
  `d5db7aa3669d476893e078459d757ea6edd00d42becab0d8931acf5ea3e74903`;
  it declares three proxy targets and the historical section query at `z=1.6 m`.
- Successful enrollment `execution.json` is `exit_0`; it records 358 source
  records, 354 captured meshes, three proxies, 9,648 compared samples, and
  zero sample mismatches. The 9,648/zero-mismatch result is historical
  eye-plane section evidence only, not the new whole-height acceptance sample.

The normalizer consumes `field_samples.json`, `source_sections.json`,
`selection_audit.json`, `transport_audit.json`, `artifact_manifest.json`, the
authenticated capture manifest, and referenced mesh/proxy records. It
constructs:

```text
frame = "world_xy"
units = "m"
origin_offset_m = [0.0, 0.0]
query_scope = "whole_height_plan"
domain = exact components with holes
physical_occupancy = one record per selected geometry
unresolved_source_ids = exact five ids
boundary_scoped_ids = ["live-step-6231"]  # audit; already excluded upstream
```

`transport_scene()` from the historical enrollment runner is **not** reused
unchanged: it fixes the `z=1.6 m` section plane and leaves
`AnalysisDomain.geometry_refs=()`. A runner-local sibling transport must reuse
authenticated `SourceObject`/mesh construction and shared occupancy bindings,
omit section records, explicitly carry domain components/frame/units/offset,
and then call the existing `analysis_scene_view(neutral)` path. It must not
create a direct-preview resolver.

Whole-height plan projections use `plan_projection(..., height_band=None)`.
Historical `z=1.6 m` section values remain provenance/context only. Unknown
support remains global because current `FreeSpaceField` accepts only global
`unresolved_source_ids`; renderer-side diagnostic hulls must not erase unknown
or convert `False` into walkability.

The five locked unresolved ids must be preserved before any shared view can
promote captured meshes. The qualified whole-height handoff may expose no
qualified `geometry_refs` for those five while retaining original capture
references/arrays as audit-only provenance and explicit source-bound
uncertainty. If the current resolver cannot preserve this fact through the
existing handoff without changing `features/*`, stop and return that concrete
blocker to the owner before implementation. The current plan assumes a
runner-local qualified handoff is sufficient and makes no production feature
change.

## Project Structure

```text
specs/002-free-space-field-inspection/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
├── checklist.md
├── contracts/
│   └── inspection-manifest.md
└── delegated/
    └── locked-input-seam-review.md  # read-only external evidence

scripts/design/space_field/
└── run_free_space_field_inspection.py  # implemented offline runner under review

test/
└── test_free_space_field_inspection.py # focused contract tests under review
```

No existing evaluator, resolver, room model, B3 loader, or Field core is
changed by this implementation. Live evaluator promotion and B3 closure remain
open.

## Phased Design

### Phase 0 - Locked input normalization

1. Verify package and mesh hashes from `artifact_manifest.json`.
2. Read distributed package records and build explicit domain and occupancy
   records.
3. Preserve per-proxy object/binding reference, approximation limit, and
   represented owner ids.
4. Recompute whole-height plan components only from authenticated meshes using
   the existing projection helper; never use historical eye-plane geometry.
5. Preserve the five upstream unresolved ids and exact boundary membership.
6. Do not treat historical `frozen_section_status` as sufficient evidence that
   the current resolver will preserve uncertainty; establish the explicit
   qualified handoff before constructing the field.

### Phase 1 - Field and manifest handoff

1. Instantiate the existing `FreeSpaceField` with explicit offset, domain,
   selected occupancy, query context, and unresolved ids.
2. Evaluate the declared lattice and call `build_field_layer_manifest`.
3. Keep the raw manifest semantically recoverable.
4. Deduplicate repeated global `selected_records` into a shared provenance table
   plus per-cell references only at the serialization boundary.
5. Record projection/evaluation/serialization timings and output bytes.

### Phase 2 - Static inspection output

1. Write inline SVG layers for domain, holes, physical occupancy, furniture
   outlines, accepted proxies, unresolved supports, and field cells.
2. Add a small HTML shell with status legend, resolution/limit metadata, and a
   cell detail panel driven by embedded JSON.
3. Keep status colors and labels distinct for all six states.
4. Include audit metadata and a note that `False` is not walkability or
   clearance.

### Phase 3 - Focused verification

1. Test hash refusal, frame/offset preservation, source coverage, exact-once
   proxy ownership, and whole-height/section separation.
2. Test all six statuses, global unknown propagation, scalar/manifest
   equivalence, and provenance recovery.
3. Test self-contained HTML/SVG output and deterministic ordering.
4. Measure the pinned run; return optimization questions to the owner only if
   actual timing or interaction evidence shows a blocker.

## Complexity Tracking

No constitution violation is being claimed. The shared provenance table is a
serialization optimization required to avoid duplicating the 343-record global
inventory in every cell; it does not change the Field core or audit semantics.
