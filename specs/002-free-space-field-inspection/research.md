# Research: Free-Space Field Inspection

**Date**: 2026-10-10

## Decision 1 - Use the successful 142454 frozen package

**Decision**: Bind the plan to
`outputs/design/b3_shared_occupancy_enrollment/run_20261009T142454Z_0d7308`
and `outputs/design/b3_real_source_field/run_001`.

**Rationale**: The delegated seam review identifies this as the successful
package with the complete distributed input set, authenticated mesh references,
three proxies, five unresolved owners, and exact boundary membership.

**Alternatives considered**: The earlier `run_20261009T141817Z_8e23c2` package
is historical evidence and is not the planned input. The existing
`preview_input.json` is a display manifest and is insufficient as a normative
Field input because it omits explicit top-level offset and direct per-proxy
binding provenance.

## Decision 2 - Normalize distributed records once before field construction

**Decision**: Read the package artifacts and construct an explicit immutable
mapping containing domain components, one whole-height occupancy record per
selected geometry, `origin_offset_m=[0.0, 0.0]`, five unresolved ids,
boundary-scoped ids, and package fingerprints.

**Rationale**: This is the smallest seam that satisfies the existing
`FreeSpaceField` constructor without changing the resolver, evaluator, room
model, B3 loader, or Field core.

**Alternatives considered**: Feeding `preview_input.json` directly would lose
normative provenance. Reusing old eye-plane geometry would confuse a `z=1.6 m`
section with whole-height occupancy. Re-running live IFC/Blender would destroy
offline determinism.

## Decision 3 - Preserve global unknown semantics

**Decision**: Pass the existing global `unresolved_source_ids` through to
`FreeSpaceField` and do not add local support masks or a second Field API.
Diagnostic hulls may be displayed as uncertainty context only.

**Rationale**: The current Field contract has global unknown propagation. The
renderer must not turn `False` into walkability or erase `unknown`.

**Alternatives considered**: Localized unknown masks would be a new semantic
contract and are explicitly out of scope. Treating unresolved supports as
free would be unsafe and contradicts the existing status vocabulary.

## Decision 4 - Render a self-contained HTML/SVG artifact

**Decision**: Inline the SVG and JSON payload in one local HTML file, with a
side-by-side source layer and field layer, a six-state legend, and a cell detail
panel.

**Rationale**: It requires no server, new dependency, Blender, or network asset
and directly supports offline owner review.

**Alternatives considered**: Blender preview is unnecessary for this 2D
checkpoint. A standalone image would lose per-cell provenance. A new web
framework would add dependency and packaging cost.

## Decision 5 - Deduplicate repeated provenance only at serialization

**Decision**: Call the existing `build_field_layer_manifest` first, then
serialize a shared provenance table once and reference it from each cell.
Provide a deterministic recovery rule that reconstructs the original per-cell
manifest records exactly.

**Rationale**: `FieldSample.provenance` contains the same global
`selected_records` inventory for each of the 0.25 m cells. Deduplication avoids
multi-thousand-copy JSON without changing core or losing audit information.

**Alternatives considered**: Copying the complete inventory into every cell is
simple but needlessly inflates the artifact. Adding a cache or spatial index
before measuring is premature and not authorized.

## Historical evidence boundary

The prior shared-enrollment result reports 9,648 samples with zero mismatch.
Those samples are historical eye-plane section validation. They support input
integrity and package history only; they are not the acceptance sample for the
new whole-height lattice. New acceptance compares every displayed/serialized
0.25 m cell to the current `FreeSpaceField.evaluate` result and verifies that
frozen input hashes remain unchanged.

## Decision 6 - Use a runner-local whole-height NeutralScene transport

**Decision**: Reuse authenticated frozen transport facts, source construction,
and shared occupancy bindings, but do not call historical `transport_scene()`
unchanged. Build a runner-local whole-height transport with explicit domain
components, `world_xy` metres, zero offset, and no section records, then pass
the resulting `NeutralSceneV2` through the existing
`analysis_scene_view(neutral)` path.

**Rationale**: The historical function fixes the `z=1.6 m` section and leaves
`AnalysisDomain.geometry_refs=()`, which cannot satisfy the whole-height
`FreeSpaceField` contract.

**Alternatives considered**: Calling `transport_scene()` unchanged would
silently reintroduce section semantics. Rebuilding a direct preview resolver
would bypass the shared resolver contract and is prohibited.

## Decision 7 - Preserve five unresolved ids before promotion

**Decision**: Carry the exact five locked unresolved ids through a qualified
whole-height handoff. Their captured mesh references/arrays may remain
audit-only provenance, while their qualified `geometry_refs` remain absent and
their source-bound uncertainty remains explicit.

**Rationale**: The current resolver can qualify whole-height originals from
geometry refs; historical section status alone does not guarantee unknown
propagation. This explicit handoff preserves the existing global
`FreeSpaceField` semantics without adding a local-unknown API.

**Owner blocker**: If the current shared handoff cannot represent this
qualified uncertainty without modifying `features/*`, implementation must
stop and return that concrete blocker for owner ruling. The planning package
assumes a runner-local handoff is sufficient and claims no production feature
change.
