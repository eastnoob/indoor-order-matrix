# Group Frame package preflight v1

Date: 2026-10-29

This is a read-only design preflight for the next furniture-group evidence
package. It does not activate a package, run IFC extraction, or create test
geometry.

## Confirmed boundary

- The public unit remains one authored furniture group.
- `features/furniture_frame.py:infer_furniture_frame` is a single-furniture
  MassPatch PCA function. It remains suppressed/audit-only for this work.
- The active axis package continues to use the whole-group
  `overall_group_axis`; Frame is a separate package and must not change axis
  semantics.

## Reusable group-level inputs

Existing group descriptions expose the whole-group support area, center,
within-member covariance, between-member covariance, total covariance,
analysis plane, units, status, and source references. These are sufficient to
design a group-level Frame adapter without reusing the single-furniture frame
function.

## Historical distinction

The code and older design notes distinguish an undirected group axis (`2θ`,
0°/180° equivalent) from an orthogonal group frame (`4θ`, 0°/90° equivalent).
They must remain separate observations. Existing member-frame aggregation is
not evidence that the group Frame package is implemented.

## Rules still requiring review

1. Use whole-group total covariance as the Frame source, or explicitly approve
   a different group-level construction.
2. Decide whether Frame outputs only the two orthogonal axes or also extents,
   `λ1`, `λ2`, and support/clarity observations.
3. Define undefined/degenerate/partial status propagation.
4. Decide whether group-to-group Frame comparison is relation-only, with no
   pairing, membership, threshold, or winner.
5. Define overlap/union handling if the source group geometry is incomplete.
6. Define the plane-local visualization: group footprint plus frame axes, or a
   neutral footprint with axes available through query overlays.

No rule above is frozen by this preflight. Implementation begins only after
the user reviews the Frame contract and the plan checklist is updated.
