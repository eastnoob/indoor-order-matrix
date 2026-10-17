# Feature Specification: Free-Space Field Inspection

**Feature Branch**: `002-free-space-field-inspection`

**Created**: 2026-10-10

**Status**: Implemented offline inspection output; B3/evaluator/live promotion remain open

**Input**: Offline inspection package for the locked whole-height planar physical-occupancy handoff and `FreeSpaceField`.

## User Scenarios & Testing

### User Story 1 - Locked geometry and field side-by-side (Priority: P1)

As an owner or reviewer, I want one offline-openable two-dimensional inspection
view that places the locked source geometry beside the corresponding
`FreeSpaceField` cell layer, so I can compare the domain, furniture, and
physical occupancy without opening Blender.

**Why this priority**: This is the minimum useful acceptance surface for the
design package and catches geometry/frame mismatches before runtime promotion.

**Independent Test**: Open the generated HTML file from a local filesystem
without a server or external assets and identify the same domain boundary,
interior openings, furniture, non-furniture physical sources, and field lattice
in both panels.

**Acceptance Scenarios**:

1. **Given** the pinned capture and whole-height occupancy inputs, **when** the
   inspection file is opened offline, **then** it shows a source-geometry panel
   and a field panel with matching frame, datum, offset, and domain identity.
2. **Given** a source such as a table, chair, plant, or bar/counter, **when**
   the reviewer compares the panels, **then** the source remains visible as
   physical occupancy regardless of furniture-analysis eligibility.

### User Story 2 - Cell evidence and status audit (Priority: P1)

As a reviewer, I want to inspect a selected cell's value, six-state status,
source ids, explanation, support bounds, algorithm/schema versions, and query
frame, so that `conditional`, `unknown`, `outside`, and `not_available` are
not visually collapsed into `free`.

**Why this priority**: Status separation is the safety boundary of the field
contract; a visual map without this audit is not acceptance evidence.

**Independent Test**: Select or identify representative cells for occupied,
empty-established, conditional, unknown, outside, and unavailable cases and
confirm that each displays a distinct status and provenance record. If a status
is absent from the locked query, the manifest must state that it is unavailable
rather than fabricate a sample.

**Acceptance Scenarios**:

1. **Given** a cell with an accepted substitute, **when** its details are
   inspected, **then** the value is marked `conditional` with a non-empty
   approximation explanation.
2. **Given** a cell affected by unresolved support, **when** its details are
   inspected, **then** the value is `unknown` and includes the unresolved source
   id rather than being shown as known free.
3. **Given** a cell outside the explicit domain, **when** its details are
   inspected, **then** it is `outside` and carries no interior-space claim.

### User Story 3 - Deterministic offline evidence package (Priority: P2)

As an owner, I want the inspection artifact to be reproducible from pinned
inputs and to state its resolution and limits, so that the output can be
reviewed or regenerated without live IFC/Blender state.

**Why this priority**: Deterministic evidence prevents a local visual result
from being mistaken for a mutable live-scene result.

**Independent Test**: Rebuild the artifact from the same locked package and
confirm stable input hashes, stable cell records, stable source ids, and a
self-contained HTML/SVG output.

**Acceptance Scenarios**:

1. **Given** the declared `0.25 m` demonstration lattice, **when** the artifact
   is inspected, **then** the resolution and its non-production status are
   explicit.
2. **Given** a coarse/fine comparison is included, **when** it is viewed,
   **then** it is labeled as a conservatism/coverage comparison and never
   presented as a second semantic field.

### Edge Cases

- Missing or changed frozen input hashes stop generation with a diagnostic; the
  renderer must not silently substitute a live source.
- A domain hole, boundary member, or interior door remains explicit; generic
  boundary closure is inherited from exact upstream membership, while interior
  doors remain occupancy.
- Empty physical occupancy, missing domain, malformed query metadata, and
  unresolved support preserve their field contract statuses.
- Whole-height geometry must not consume or relabel the B3 `z=1.6 m` section
  values.
- Accepted proxy geometry is shown as conditional and retains represented source
  ids; proxy and original mass must not be counted twice.
- Physical sources are not filtered because they are not furniture.
- The five upstream unresolved owners remain unresolved under the current
  global `FreeSpaceField` contract; renderer-side hulls may explain uncertainty
  but must not erase `unknown`.
- The offline artifact must remain readable when optional fine/coarse comparison
  data is absent.

## Requirements

### Functional Requirements

- **FR-001**: The inspection package MUST be generated offline from the
  successful frozen package
  `outputs/design/b3_shared_occupancy_enrollment/run_20261009T142454Z_0d7308`
  and its authenticated source capture; it MUST verify recorded byte counts and
  SHA-256 hashes before using geometry.
- **FR-002**: The package MUST read the package artifacts as a set:
  `field_samples.json`, `source_sections.json`, `selection_audit.json`,
  `transport_audit.json`, `artifact_manifest.json`, and their referenced mesh
  records. `preview_input.json` alone MUST NOT be treated as a complete
  normative `FreeSpaceField` input.
- **FR-003**: The normalized input MUST explicitly carry `frame="world_xy"`,
  `units="m"`, `origin_offset_m=[0.0, 0.0]`, `query_scope="whole_height_plan"`,
  exact domain components including two holes, five unresolved source ids, the
  boundary-scoped id `live-step-6231`, package fingerprints, and one occupancy
  record per selected geometry.
- **FR-004**: Each normalized occupancy record MUST carry selected id,
  whole-height plan components, `represented_source_ids`, original/accepted
  representation status, and capture/proxy provenance. A proxy MUST remain one
  geometry with seven-owner coverage split across three proxy records; it MUST
  NOT be duplicated per owner.
- **FR-005**: The package MUST construct the declared
  `NeutralSceneV2 -> analysis_scene_view -> explicit domain + whole-height
  physical_occupancy -> FreeSpaceField` handoff without invoking Blender, live
  IFC loading, or a side-effectful runner.
- **FR-006**: The package MUST reuse `FreeSpaceField` and
  `build_field_layer_manifest`; it MUST NOT introduce a second semantic field
  layer, add a local-unknown Field API, or recompute resolver/evaluator
  semantics during rendering.
- **FR-007**: The HTML/SVG view MUST show source geometry and field cells
  side-by-side with distinguishable domain boundary, holes, furniture,
  plants/counters/bar occupancy, accepted proxies, unresolved supports, and
  lattice extents.
- **FR-008**: Every displayed cell MUST preserve value, one of the six
  `FieldStatus` states, source ids, explanation, support, query frame, units,
  algorithm version, schema version, and provenance.
- **FR-009**: Visual encoding MUST keep `conditional`, `unknown`, `outside`,
  `invalid`, and `not_available` distinct from established occupied/empty
  states; no non-free state may be painted as known free.
- **FR-010**: Source geometry MUST preserve physical occupancy independently of
  furniture-analysis qualification, and represented originals MUST be counted
  exactly once through the accepted substitute record.
- **FR-011**: The package MUST label `0.25 m` as a declared demonstration
  resolution, not a production decision; any coarse/fine comparison MUST be
  explicitly diagnostic and MUST NOT create another semantic field.
- **FR-012**: The package MUST state that value `False` means empty physical
  occupancy under the declared query, not walkability, clearance, route
  connectivity, or area-certified free space.
- **FR-013**: The package MUST remain self-contained as a local HTML/SVG file
  with no new runtime dependency and no external network asset.
- **FR-014**: The package MUST stop with a clear diagnostic when required locked
  inputs, domain metadata, or occupancy records are missing, stale, ambiguous,
  or inconsistent.
- **FR-015**: Because each `FieldSample.provenance` currently carries the
  global selected-record inventory, the output layer MUST store that inventory
  once in a shared provenance table and let each cell reference it while
  preserving exact semantic recovery. It MUST NOT modify the field core or
  silently discard audit records.
- **FR-016**: The implementation MUST record projection time, field-evaluation
  time, serialization time, and output byte size. No cache or spatial-index
  framework is planned unless measurements show that offline generation fails
  or interaction is materially unusable.

### Key Entities

- **LockedInputBundle**: Hash-pinned capture manifest, structural capture,
  scope/domain evidence, binding declaration, accepted shared-enrollment
  package, and source mesh references.
- **InspectionFrame**: World XY frame, floor datum, origin offset, units,
  query kind, and declared resolution.
- **SourceGeometryRecord**: One source or accepted proxy with source id,
  represented source ids, geometry components, class/role, and provenance.
- **FreeSpaceFieldCell**: One lattice coordinate with boolean value, six-state
  status, support, source ids, explanation, query metadata, and audit versions.
- **SharedProvenanceTable**: Deduplicated global inventory and per-record
  references used to reconstruct each original manifest sample exactly.
- **InspectionManifest**: Deterministic self-contained payload consumed by the
  HTML/SVG renderer, including side-by-side layers, limits, timings, and size.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The generated artifact opens from a local filesystem with no
  network request and contains both required side-by-side layers.
- **SC-002**: For the new `0.25 m` whole-height lattice, every displayed and
  serialized cell preserves the value, status, source ids, query metadata, and
  provenance returned by the current `FreeSpaceField.evaluate` path; the
  frozen historical package hashes remain unchanged.
- **SC-003**: Every displayed cell has a valid six-state status and non-empty
  provenance fields for frame, query kind, algorithm version, and schema
  version.
- **SC-004**: At least one representative example for each non-established
  status is available in the manifest or is explicitly reported unavailable,
  never silently omitted.
- **SC-005**: The output records 358 source records, 354 frozen body mesh
  captures, three accepted proxy targets, and the exact input hashes used.
- **SC-006**: No Blender process, live IFC adapter, evaluator, room-model
  promotion, clearance, connectivity, or new dependency is required to open
  or inspect the artifact.
- **SC-007**: Deduplicated serialization can reconstruct every displayed cell's
  original manifest semantics exactly, while recording measured timings and
  final output size.

## Assumptions

- The reviewer can open a local HTML file in a modern desktop browser; browser
  automation is not part of this checkpoint.
- The frozen capture remains immutable and is treated as evidence, not as a live
  source to refresh.
- `FreeSpaceField` remains the only semantic field instance for this view.
- The constitution is still unratified; this plan makes no constitution
  compliance claim.
- B3 `z=1.6 m` section records may be shown as provenance/context only and are
  never used as whole-height cell values.
- Exact area calculations are deferred; geometric free-space area and
  conservative occupied-cell area remain separate concepts.
