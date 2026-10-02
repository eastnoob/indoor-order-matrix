# D6 trend estimand owner design review

Status: **APPROVE DESIGN; DEFER PRODUCTION IMPLEMENTATION**

Evidence reviewed:

- `docs/project/evidence/d6-trend-substitute-contract-parity.md`
- `outputs/design/trend_substitute_contract_parity/trend_substitute_contract_parity.json`
- `outputs/design/trend_substitute_contract_parity/d6-trend-substitute-contract-parity-visual-manifest.json`
- `docs/project/evidence/d6-trend-direction-design-probe.md`
- `docs/project/d6-group-level-self-description-design.md`
- existing `features/scene_inference.py` legacy frame implementation

## Decision basis

The decision is semantic and contract-level. It selects the descriptor that best
matches the project meaning of “furniture-group overall orientation”. It is not
a claim that one estimator is empirically more psychologically valid or more
accurate on the full IFC model. The probe demonstrates that A, B, C, and D are
different quantities and must not be silently collapsed.

## Estimand decisions

### C is the overall group geometric trend

Approve `area_weighted_total_covariance_pca` as the design definition of the
overall furniture-group axis:

- input: typed trend Analysis substitutes only;
- center: area-weighted representative center;
- covariance: `within_member_covariance + between_member_covariance`;
- direction: major eigenvector, modulo 180 degrees;
- strength: deterministic covariance anisotropy, never a probability;
- degenerate/isotropic covariance: direction is undefined under the existing
  status contract;
- invalid, missing, partial, and not-available states remain explicit.

This matches the intended meaning that the group direction belongs to the
occupied group geometry and that its axis passes through the group
representative center.

### A remains an independent member-orientation descriptor

Approve `member_orientation_consensus` as a separate descriptor:

- `member_frame`: four-angle frame, modulo 90 degrees;
- `member_axis`: two-angle axis, modulo 180 degrees;
- weights: area multiplied by member polygon anisotropy;
- meaning: agreement among member-body orientations;
- it does not replace the overall group axis and does not use member placement
  spread as its primary evidence.

### D remains an independent layout descriptor

Approve `between_member_centroid_pca` as a separate placement descriptor:

- input: member centroid placement only;
- center: area-weighted group representative center;
- direction: major eigenvector, modulo 180 degrees;
- meaning: how member positions are arranged;
- singleton or coincident-member layouts have no usable placement direction.

### B remains legacy diagnostic only

Approve `legacy_projected_point_cloud_pca` and the legacy
`_furniture_group_frame` output as compatibility diagnostics. They must not
define the new trend contract because their result depends on legacy point
selection, vertex density, extent mixing, and historical member-frame logic.

The direct parity result is evidence about semantic difference, not a failure:
the legacy final output, legacy geometry PCA, A, C, and D can legitimately
disagree on the same Analysis polygons.

## Input and provenance decision

Approve the design-only `trend_analysis` registry contract:

- `consumer == "trend"`;
- `substitute_kind == "MassPatch"`;
- `analysis_role == "analysis_geometry_substitute"`;
- provenance representation identifier must be `Analysis`;
- Body is never a trend fallback;
- labels and source names never authorize semantics;
- each substitute keeps a unique `substitute_id` and its source provenance.

The registry may move into implementation design. It is not yet a production
module or public API.

## State and evidence boundary

Formal consumers must honor the existing status contract. Numeric values kept
for a usable subset in an invalid or partial case are diagnostic evidence only;
they must not be exposed as a complete formal trend. No missing geometry is
converted to zero and no unsupported hole is repaired in this slice.

The current IFC sample supports input/provenance and estimator-separation
claims. It does not establish full-model accuracy, Bayesian posterior
calibration, or psychological validity.

## Next gate

The next stage may write an implementation design for:

1. typed substitute registry integration;
2. formal C overall group axis;
3. independent A member orientation descriptors;
4. independent D placement descriptors;
5. status propagation and test fixtures;
6. IFC/SVG 2D parity boundaries and Blender audit output.

It may not yet modify production code. Production implementation begins only
after that implementation design receives its own review.

**STOP FOR IMPLEMENTATION DESIGN REVIEW**

