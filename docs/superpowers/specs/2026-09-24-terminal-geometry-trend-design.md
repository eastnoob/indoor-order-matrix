# Terminal Geometry Trend Design

**Status:** Proposed; design and plan only. No implementation is included in this change.

## Goal

Make furniture and furniture-group trend analysis depend only on the object's final analysis geometry in the analysis coordinate system. Historical rotation records, authored local orientation fields, block-definition axes, and transform history must not affect trend, clarity, strength, or column-grid alignment.

## Problem

The current group-frame path can prefer `member_frame_consensus` from an `orientation` record even when that record describes a local or historical frame. A furniture group that is visibly oblique in its final room state can therefore be reported as aligned with an orthogonal column grid. Existing geometry PCA may remain diagnostic instead of being the source of the reported group trend.

## Scope

This change covers terminal single-furniture frames, terminal furniture-group trends, internal trend coherence, column-grid handoff, source contracts, comments, documentation, and regression tests. It does not add perception weights, a fitted evaluation model, a matrix result, a new visualization, automatic affordance generation, or a new IFC schema object.

## Source Of Truth

The analytical source of truth is the final world-space `Analysis` MassPatch plan projection. If an authored MassPatch is unavailable, the adapter may provide an explicitly documented geometry fallback according to the existing substitute contract. `Body` geometry may be compared for audit, but must not silently replace `Analysis` geometry in production trend computation.

The analyzer must not use historical rotation values, block-definition orientation, authored local orientation, object names/layers, or a transform merely because it existed before final geometry was produced. The adapter must preserve final geometry in a common analysis coordinate system or expose an uncertainty rather than fabricate a trend.

## Description Outputs

### Single furniture

`infer_furniture_frame(mesh)` returns primary and secondary axis angles, extents, eigenvalues, continuous orientation strength, geometry basis, and source mesh id. Strength describes directional evidence in the proxy geometry; it is not a perceptual weight and is independent of group membership or object count.

### Furniture group

Each member first receives a terminal frame from its final Analysis MassPatch. The group exposes separate, auditable evidence:

- `group terminal trend`: the frame inferred from final world-space group evidence;
- `member terminal trend coherence`: agreement of member terminal frames with the group frame;
- `group geometry clarity`: how strongly the group evidence supports one primary axis;
- `group trend basis`: the geometry evidence actually used.

Group evidence uses final member MassPatch plan geometry plus final authored affordance extents/centers. Each member contributes one normalized geometric record so tessellation density and triangle count cannot become hidden perceptual weights. If combined geometry and member-center evidence do not support a stable axis, clarity must be low rather than an angle being forced.

### Column-grid alignment

Column-grid alignment consumes the group terminal trend and never reads a disabled historical orientation field. Existing 0/180 equivalence and two-axis orthogonal-frame equivalence remain valid, but a genuinely oblique group must retain its oblique angle and receive the corresponding deviation from an orthogonal grid.

## Compatibility Contract

Fields such as `authored_orientation`, `orientation`, and `group-axis-geometry-angle` may remain in serialized input or audit metadata. They must be explicitly labeled provenance-only or legacy diagnostics and must not enter trend, strength, clarity, coherence, or alignment calculations. No compatibility alias may silently route a historical field back into analytical code.

Use names that distinguish `terminal_geometry_trend`, `group_terminal_trend`, `member_terminal_trend_coherence`, and `historical_orientation`/`authored_orientation`.

## Required Behaviors

1. A rectangular MassPatch rotated 30 degrees in final coordinates reports approximately 30 degrees with no rotation metadata.
2. A final geometry rotated 30 degrees reports approximately 30 degrees when a stale orientation field says 0 degrees.
3. An oblique furniture group reports an oblique trend and non-zero deviation from an orthogonal column grid.
4. Aligned member terminal frames produce high coherence; mixed terminal frames produce lower coherence.
5. Circular or square proxies report weak directional strength and do not become strong because of orientation metadata.
6. Missing/unusable Analysis MassPatch produces explicit uncertainty or documented fallback, not a fabricated historical-direction trend.
7. Existing region trend behavior remains separate from this group-level description.

## Documentation And Acceptance

Update architecture memory and relevant development documentation to state that terminal geometry is the analytical direction source and historical/authored orientation is audit-only. All modified project-owned functions require English-first docstrings and comments for non-obvious geometry, frame, adapter, and scoring decisions.

Acceptance requires focused tests for the behaviors above, a verified IFC/neutral-scene handoff of final Analysis geometry, a passing full suite, and no matrix-result or UI work in this change.
