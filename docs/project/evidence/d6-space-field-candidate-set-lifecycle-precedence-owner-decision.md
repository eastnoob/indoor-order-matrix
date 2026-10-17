# D6 Candidate-Set Lifecycle and Precedence — Owner Decision

- Date: 2026-10-05
- Independent review verdict: `REVISE`
- Scope: design evidence only

## Decision

### Artifact package — REVISE

The lifecycle experiment is not accepted as a complete review bundle yet. The
PNG is not human-readable: the real-IFC panel is rendered above the walls,
columns, and candidate outlines and therefore hides the geometry. The SVG and
machine checks do not remove this blocker.

### Semantic evidence — ACCEPT PROVISIONALLY

The following conclusions are supported provisionally and need not be
redesigned:

- real IFC and synthetic controls are separated;
- eight real-IFC candidates remain retained with explicit no-selection;
- candidate-set state is separate from per-candidate state;
- singleton does not imply a room or formal `AnalysisDomain`;
- confirmation, rejection, and replacement preserve provenance;
- authored-domain precedence retains automatic candidates as provenance;
- conflict remains visible;
- columns remain physical occupancy;
- doors are not treated as openings without IFC opening/void/fill evidence.

### Status contract — DEFER

Do not freeze `ambiguous`, `singleton`, `unassigned`, `user_confirmed`,
`rejected`, `replaced`, `conflict`, or their aggregation/serialization rules.

### Production gates — DEFER

Do not begin production implementation, selector design, formal domain
promotion, free-space, connectivity, route, walkability, Bayesian/ML,
threshold, resolution, geometry-backend, or public-API work.

## Required repair

Repair only the disposable lifecycle visualization so that the real-IFC panel
shows walls, columns, candidate outlines, and labels without occlusion. Then
rerun the bounded verifier, manifest/hash checks, PNG inspection, and Blender
readback. Do not rerun the full IFC adapter or full test suite.

After the repair passes independent review, the owner may make the final
lifecycle decision and decide whether implementation design is justified.

**STOP FOR CANDIDATE-SET LIFECYCLE REPAIR REVIEW**
