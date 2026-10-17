# Feature Specification: Field Kernel and Free-Space Read-Only Slice

**Feature ID**: `001-field-kernel-free-space` (Speckit feature directory; no Git branch switch performed)

**Created**: 2026-10-10

**Status**: US4 isolated implementation accepted; constitution remains unratified

**Input**: Establish one global field contract, validate the narrow B3
read-only seam, and provide the exact-cell `FreeSpaceField` over pre-resolved
whole-height plan inputs. Do not promote B3 or change the live evaluator in
this feature slice.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Read and audit a field sample (Priority: P1)

As an analysis developer, I need one field contract that can return a value, status, query context, and provenance so that physical and relational fields can be inspected without losing why a result exists.

**Why this priority**: Every later field instance depends on stable domain, status, and provenance semantics.

**Independent Test**: A synthetic field record can be queried once and in a batch, producing equivalent canonical samples while preserving `unknown`, `outside`, `invalid`, and `not_available`.

**Acceptance Scenarios**:

1. **Given** a point inside a declared domain, **When** it is queried, **Then** the result contains value, status, source ids, query context, and provenance.
2. **Given** a point outside the domain or a missing channel, **When** it is queried, **Then** the result remains outside or not-available and is never converted to known free or numeric zero.

---

### User Story 2 - Adapt the frozen B3 package without promotion (Priority: P2)

As an analysis developer, I need a read-only adapter from the validated B3 serialized package to the field contract so that samples, hashes, source ids, and limitations remain auditable.

**Why this priority**: It gives the existing B3 work a stable inspection seam while protecting the live evaluator and package compatibility boundary.

**Independent Test**: A synthetic accepted B3 package can be loaded through the existing loader and adapted without changing the loader return shape or claiming complete occupancy/clearance.

**Acceptance Scenarios**:

1. **Given** an accepted B3 package, **When** it is adapted, **Then** the adapter preserves schema, variant, source sections, hashes, statuses, and the conditional/open limitations.

---

### User Story 3 - Validate evidence-channel isolation (Priority: P3)

As an analysis developer, I need fixture-driven replay to show that physical occupancy, space barriers, semantic evidence, and context remain separate channels before any group or free-space score is promoted.

**Why this priority**: The current fixtures are useful design probes, but they must not leak candidate labels or probe-local formulas into production semantics.

**Independent Test**: Replaying all eight fixtures twice and applying declared perturbations produces deterministic, channel-local changes with no unexplained diff.

**Acceptance Scenarios**:

1. **Given** a closed barrier, **When** only the barrier is changed to an opening, **Then** the space channel changes while geometry observations remain unchanged.
2. **Given** missing semantic or domain data, **When** the fixture is replayed, **Then** the affected channel is unavailable/unknown rather than negative or free.

### User Story 4 - Query exact physical occupancy cells (Priority: P2)

As an analysis developer, I need exact-cell physical occupancy over an
explicit domain and pre-resolved whole-height plan records so that empty cells
remain auditable without being mislabeled walkable or clear.

**Independent Test**: Focused tests prove domain clipping/holes, finite lattice
validation, original versus accepted representation status, unknown
propagation, fixed query context, and ordered batch lookup without invoking the
evaluator or source resolver.

---

### Edge Cases

- The analysis point is outside the selected domain.
- A source has invalid geometry versus absent geometry.
- A B3 sample is conditional or unknown at `z=1.6 m`.
- A fixture candidate contains a hard mutual-exclusion conflict.
- Input order, object ids, translation, or rotation changes without changing the declared geometry relation.
- A field supports batch queries but a relation field does not support spatial interpolation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST define one global field contract with domain, frame, query context, value schema, representation, status, and provenance.
- **FR-002**: The contract MUST support exact scalar lookup and batch lookup; spatial sampling/interpolation is optional and must not be required by relation fields.
- **FR-003**: The contract MUST distinguish `established`, `conditional`, `unknown`, `outside`, `invalid`, and `not_available` where applicable.
- **FR-004**: The B3 adapter MUST consume the existing validated loader output without changing its JSON schema, hashes, variant selection, or return shape.
- **FR-005**: The first free-space seam MUST consume physical occupancy and preserve uncertainty; it MUST NOT certify complete occupancy, clearance, connectivity, or whole-height walkability.
- **FR-006**: Fixture validation MUST preserve channel provenance and MUST label probe formulas as design-only.
- **FR-007**: The feature MUST NOT change `evaluate_scene`, `room_analysis_model`, or default evaluator visualization behavior in this planning slice.
- **FR-008**: Any decay MUST be an explicit influence/operator parameter; occupancy and physical distance MUST retain their physical semantics.
- **FR-009**: The exact-cell instance MUST evaluate positive-area `cell ∩ domain`; holes and line/point-only contact MUST not count as occupied area.
- **FR-010**: Missing domain/channel MUST be `not_available`; malformed domain, grid, query, or geometry MUST be `invalid`; no bbox fallback is permitted.
- **FR-011**: The instance MUST consume explicit whole-height plan inputs only; section, height-band, or tilted-plane requests MUST be `not_available` unless separately qualified upstream.
- **FR-012**: Known occupied evidence MUST survive unresolved support; unresolved support MUST remain `unknown` rather than known free.
- **FR-013**: `original` records may establish whole-height values; `accepted` substitutes make results `conditional` with explicit limitation provenance.

### Key Entities *(include if feature involves data)*

- **Field**: A semantic mapping over a declared domain, frame, query context, and representation.
- **FieldQuery**: A point/collection query with plane, height band, demand, and tolerance context.
- **FieldSample**: Value plus status, support, source ids, units, and provenance.
- **FieldBundle**: Future separate channels sharing domain/frame/query context; no runtime bundle is introduced by US4.
- **B3AdapterView**: A read-only mapping of the frozen serialized package to field samples, retaining package identity and limitations.
- **EvidenceFixtureRun**: A deterministic replay record for the eight design-only fixtures and declared perturbations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two consecutive replays of all eight fixtures produce identical canonical observations, statuses, and assertion results.
- **SC-002**: All declared status/provenance invariants pass without converting missing, invalid, or outside records into known free.
- **SC-003**: The adapter preserves every accepted B3 package identity field and keeps complete occupancy/clearance unavailable where the package says so.
- **SC-004**: Channel perturbation tests change only the declared channel and do not change unrelated geometry or semantic observations.

## Assumptions

- The selected field domain and analysis frame are explicit; a scene bounding box is not silently treated as an analysis domain.
- B3's world-XY `z=1.6 m` samples are conditional section observations, not whole-height free-space truth.
- Existing `MassPatch`/physical occupancy policy remains the source of physical volume; furniture eligibility does not remove volume.
- The eight self-description fixtures are synthetic design probes; they provide no psychological ground truth or complete room geometry.
- The constitution file is not ratified yet, so planning completion requires an explicit pending-review note.

## Out of scope for this feature

- Production `FreeSpaceField` promotion into `evaluate_scene`.
- Complete occupancy, clearance, connectivity, route-width, door-state, or height-band certification.
- A Bayesian probability model, calibrated membership probability, or a final inferred-group selector.
- Changes to the public `room_analysis_model` shape or existing B3 loader return shape.
- Live evaluator promotion of the exact-cell instance.


