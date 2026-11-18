# AnalysisContext Ancestor Plan Grill-Me Review

Date: 2026-11-18
Reviewer: independent planning reviewer
Scope: \`docs/superpowers/specs/2026-11-18-analysis-context-ancestor-design.md\` and \`docs/superpowers/plans/2026-11-18-analysis-context-ancestor-implementation.md\`

## Decision

The design direction is accepted after the corrections below. Task 1 was held until the resolver precedence, caller propagation, cache ownership, compatibility boundary, and jj preservation evidence were made explicit in the plan.

## Rulings

1. \`AnalysisContext\` is the scene ancestor and owns exactly one required default \`AnalysisPlane\`. \`PackageAnalysisContext\` is a per-call frozen snapshot.
2. A non-empty explicit \`package_planes\` set replaces the ancestor plane and is never merged with it.
3. The resolver precedence matrix is:
   - scene \`AnalysisContext\` without package planes -> its default plane;
   - scene \`AnalysisContext\` with explicit package planes -> explicit set;
   - \`PackageAnalysisContext\` without package planes -> its frozen set;
   - \`PackageAnalysisContext\` plus package planes -> reject conflicting sources;
   - no context with explicit package planes -> explicit set;
   - no context and no package planes -> unique complete source-query inference only.
4. Empty, duplicate, non-plane, malformed, and unauthorized multi-plane inputs fail before producer, processor, storage, or cache work.
5. \`package_planes\` is propagated through all evidence-package and port runner boundaries. The free-space request plane is an explicit package override when a scene context is also supplied.
6. The generic cache layer does not infer whether an algorithm used a plane. Ignored-context packages preserve bytes and identities; plane-using packages declare plane identity and revision in their own output or dependency contract before lookup.
7. Explicit context is a trusted selection boundary. Source-query compatibility remains the responsibility of plane-dependent packages; the legacy inference path remains strict.
8. The existing default workspace revision and dirty work are preserved. The isolated workspace records a complete patch, path list, snapshot file list, and hash before implementation checkpoints.

## Risks accepted

The current nested jj workspace path makes one namespace-isolation test unable to import \`order_analyzer\` because that test assumes the repository's original parent directory. This is an execution-environment limitation; the same test must be rerun from a package-shaped checkout or with the original repository path before final acceptance.

