# Constrained MassPatch Generation Design

**Date:** 2026-09-04

## Goal

Add a source-independent backend generator that can replace detailed source
geometry with the smallest validated collection of `MassPatch` geometries
needed for plan occupancy, height-aware occupancy, and visibility queries.

The generator must run inside the existing Pixi Python environment and must be
usable before any Rhino plugin or standalone packaging work. Rhino integration
will call this backend later; it must not own the algorithm.

## Scope

### Included

- Conversion of a validated `MeshGeometry3D` into one or more candidate
  `MassPatch` records.
- Conservative connected-component handling.
- Candidate oriented-box construction for geometrically simple components.
- Exact-mesh fallback for components whose simplification would lose evidence.
- Geometry-only validation of plan occupancy, height intervals, gaps, and
  basic ray occlusion.
- Deterministic provenance and validation reports.
- Pytest fixtures for chairs, boxes, hollow objects, sloped objects, and
  disconnected components.
- A notebook or executable visual comparison using the live Rhino source
  geometry after the backend contract is green.

### Excluded

- Rhino UI, C# plugin implementation, or standalone packaging.
- IFC persistence of generated patches.
- Furniture-kind templates or semantic naming.
- Affordance-zone generation.
- Perceptual weights or evaluation-matrix scores.
- CoACD as a required dependency or final authority.

## Existing Contracts

The generator consumes the existing `MeshGeometry3D` record from
`features.scene_contract`. It produces the existing `MassPatch` record from
`features.geometry_substitutes` and must not change the behavior of
`mass_patch_from_mesh`.

The public generation API is:

```python
def generate_mass_patches(
    mesh: MeshGeometry3D,
    config: MassPatchGenerationConfig | None = None,
) -> MassPatchGenerationResult:
    """Generate validated analysis substitutes for one source mesh."""
```

The public records contain:

- `MassPatchGenerationConfig`: geometry tolerances and sampling settings;
- `MassPatchCandidateReport`: one candidate's measured errors and decision;
- `MassPatchComponentReport`: source component identity, candidate reports, and
  selected candidate;
- `MassPatchGenerationResult`: ordered patches, component reports, source mesh
  id, and method version.

The configuration contains geometry tolerances only. It must not contain
perceptual weights:

- `linear_tolerance`;
- `sample_spacing`, default `4 * linear_tolerance`;
- `minimum_plan_recall`, default `0.98`;
- `maximum_plan_overreach`, default `0.02`;
- `maximum_vertical_endpoint_error`, default `2 * linear_tolerance`;
- `maximum_occlusion_disagreement`, default `0.02`.

These values are engineering acceptance tolerances, not layout-quality
weights. They may be changed for unit scale or source tessellation, and the
effective values must be written into provenance.

## Algorithm

### 1. Normalize and audit the source

The generator copies source vertices and triangles into a deterministic
working representation. It rejects empty meshes, invalid indices, non-finite
coordinates, and degenerate-only geometry. It preserves source units and
`local_to_world_provenance`; it never edits the source record.

The implementation may use `trimesh` for mesh inspection and connected
components, but all output and validation must remain expressed through the
project-owned `MeshGeometry3D` and `MassPatch` contracts.

### 2. Split only by factual connectivity

The first decomposition boundary is a true mesh connected component. This
does not use object names, furniture kinds, Rhino groups, or semantic guesses.
Each component receives a stable derived id based on source id and component
index.

Components remain separate unless a later candidate operation proves that
merging them preserves every required observation. The first implementation
does not perform speculative cross-component merging.

### 3. Generate conservative candidates

For each connected component, construct candidates in this order:

1. The exact component mesh.
2. An oriented bounding box candidate when the component has a non-degenerate
   three-dimensional extent.

No object-kind threshold decides whether the box is acceptable. The oriented
box is only a candidate, and its geometry is accepted or rejected solely by
the source comparison below. A box that bridges a chair-leg gap, fills a
hollow frame, or creates a false high blocker is rejected.

If a component is not safely replaceable, its exact triangulated component
becomes the resulting `MassPatch`. This is intentionally conservative: exact
geometry is a valid substitute, while false occupancy is not.

### 4. Validate candidates against the source

Validation uses deterministic samples derived from the union of source and
candidate plan bounds. Grid spacing is `sample_spacing`; every source and
candidate plan vertex is also included as a sample, so narrow component edges
are not represented only by a distant grid point. It compares source and
candidate independently in the analysis plane:

- **Plan recall:** source-occupied sample positions also occupied by candidate.
- **Plan overreach:** candidate-occupied positions absent from the source.
- **Height interval agreement:** lower and upper occupied intervals at sampled
  plan positions.
- **Gap preservation:** source-empty positions inside the combined bounds remain
  empty in the candidate.
- **Occlusion agreement:** deterministic rays and height bands have the same
  blocked/unblocked result.

The candidate is accepted only if all configured hard tolerances pass. The
report records sample counts, observed errors, rejection reasons, and the
accepted candidate kind.

The exact component candidate is the mandatory baseline. If the source is
valid but its query state is too uncertain for a simplification decision, the
exact candidate is selected and the report records the uncertainty rather than
inventing a simplified result.

### 5. Select the result

Selection is lexicographic, not weighted:

1. Reject candidates that fail any hard geometry constraint.
2. Prefer the candidate with lower plan/height/occlusion error.
3. Among candidates with equivalent accepted evidence, prefer fewer triangles.
4. Preserve deterministic source/component ordering.

This keeps “minimum geometry” subordinate to factual analysis fidelity.

## Data And Provenance Rules

Every generated patch records:

- source mesh id;
- source component index;
- candidate method;
- coordinate/unit context;
- validation configuration;
- measured validation results;
- whether the result is exact fallback or simplified geometry.

Generated patches are analysis records. They are not automatically written into
IFC, Rhino, Blender, or the source model.

## Testing

The implementation must follow TDD. For each behavior:

1. Write a focused failing test.
2. Run it and confirm the failure is caused by the missing behavior.
3. Implement the smallest code that passes.
4. Run the focused test and the complete relevant suite.

Required cases:

- A box accepts an oriented-box candidate with near-zero error.
- A chair-like object retains separate seat/back/leg evidence when gaps exist.
- A hollow frame is not filled by a bounding box.
- A sloped component falls back when a box exceeds height or plan tolerance.
- Disconnected components remain independently addressable.
- A source with uncertain topology selects the exact component and reports the
  uncertainty instead of silently simplifying.
- Degenerate and invalid input fails explicitly.
- Results are deterministic across repeated runs.
- Existing `MassPatch`, scene-contract, inference, and adapter tests remain
  green.

## Live Rhino Acceptance

After backend tests pass, use the active Rhino MCP source model as a
read-only fixture:

1. Extract the selected/source geometry into the neutral mesh contract.
2. Run `generate_mass_patches`.
3. Save a JSON result and validation report outside the source model.
4. Produce a visual comparison of source geometry and generated patches.
5. Confirm the result does not mutate, rename, delete, or replace Rhino source
   objects.

The live test is an integration acceptance test, not a substitute for the
unit tests. Packaging is a separate final phase after this end-to-end run is
stable.

## Code Quality

All new or modified project-owned functions require English-first docstrings.
Important geometry, candidate-selection, validation, serialization, and
adapter-handoff blocks require English-first intent comments. Short Chinese
annotations may supplement those comments but may not replace them.
