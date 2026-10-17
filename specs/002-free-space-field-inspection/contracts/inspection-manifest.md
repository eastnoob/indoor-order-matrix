# Contract: Offline Inspection Manifest

## Purpose

Define the output-only handoff from the locked whole-height `FreeSpaceField`
evaluation to a self-contained HTML/SVG inspection artifact.

The producer must first construct a runner-local whole-height `NeutralSceneV2`
handoff and pass it through `analysis_scene_view`. The historical section
transport is not a normative input path.

## Required top-level fields

```text
schema: "free-space-field-inspection/v1"
frame: "world_xy"
units: "m"
source_origin_offset_m: [0.0, 0.0]
origin_offset_m: effective offset returned by `analysis_scene_view`
query_scope: "whole_height_plan"
resolution_m: 0.25
domain: exact polygon components with holes
source_layer: array[SourceGeometryRecord]
input_hashes: object
status_availability: object
field_layer: object
shared_provenance: object
timings: object
sizes: object
limits: array[string]
```

The status vocabulary is exactly:

```text
established
conditional
unknown
outside
invalid
not_available
```

`field_layer.samples[*].visual_state` must map one-to-one to those six
values: `established`, `conditional`, `unknown`, `outside`, `invalid`, and
`not_available`. The renderer may add semantic sub-states such as
`established_occupied` and `established_empty` only as visual refinements of
`established`; they do not create additional `FieldStatus` values. Every
status must have a distinct legend/visual mapping, and `status_availability`
must state whether that status is present in the emitted sample set.

## `source_layer`

Must include source ids, source class/role, whole-height geometry, represented
owner ids, original/accepted status, capture/proxy references, and uncertainty
supports. The layer must include physical sources that are not furniture.

## `field_layer`

Must be derived by calling `build_field_layer_manifest`. Every displayed cell
must retain:

- target and boolean/null value;
- one of the six `FieldStatus` values;
- source ids;
- query domain/frame/revision/tolerance;
- support;
- algorithm and schema versions;
- explanation;
- provenance reference.

`unknown`, `conditional`, `outside`, `invalid`, and `not_available` must have
distinct visual states. No display state may imply walkability or clearance.

## `shared_provenance`

The global selected-record inventory is stored once. Each cell references it
with a deterministic `provenance_ref` and carries only fields that differ from
the shared record. A recovery routine must be able to reconstruct the exact
pre-deduplication manifest record for any cell.

## Timing and size contract

`timings` must contain measured `projection_ms`, `field_evaluation_ms`, and
`serialization_ms`. `sizes` must contain at least `json_bytes` and `html_bytes`.
No optimization framework is required before measurements show a real blocker.

## Refusal conditions

The producer must refuse output when any consumed hash changes, the explicit
domain is missing or inconsistent, a selected record lacks geometry/provenance,
a proxy owner is duplicated, the query is not whole-height, or the frozen
boundary membership cannot be resolved exactly.

Before the view handoff, the producer must preserve the five locked unresolved
source ids. A source may retain capture references/arrays only as audit
provenance while exposing no qualified `geometry_refs`; those sources remain
source-bound uncertainty. If this cannot be represented without changing
`features/*`, implementation stops for owner ruling instead of silently
promoting the source or rebuilding a direct-preview resolver.
