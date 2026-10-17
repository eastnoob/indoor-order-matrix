# D6 Candidate-Set Lifecycle Visualization Repair v1

- Date: 2026-10-05
- Scope: disposable design-evidence render repair only
- Output: outputs/design/live_ifc_candidate_set_lifecycle_experiment/repair_v1/

## Cause and visual change

The original Blender renderer placed its real-IFC panel across the same XY
footprint as the real plan: the panel started at the plan's left edge and
extended past the plan's right edge. The scene therefore combined display
panels, labels, and controls in the geometry's viewport, where the panel and
synthetic tiles competed with the evidence for visibility. A nominal PNG size
check did not detect the resulting readability failure.

The repaired composition gives the real-IFC plan its own left pane, the
candidate and furniture-group index its own right pane, and the lifecycle
examples a separate lower strip. The IFC pane has no opaque legend or control
panel over its footprint. Walls are blue with light edge strokes, columns are
orange, and all eight automatic candidates have separate colored outlines and
matching legend swatches. Coral furniture-group membership envelopes are
labeled G01–G37 and linked to their serialized group names and IDs in the
index.

The serialized input contains group member placements but not furniture meshes.
Accordingly, each coral outline is only an axis-aligned envelope around the
serialized member placement origins with 0.14 m of display padding. The render
labels that limitation and does not present the envelope as furniture geometry.

The lower strip labels user_confirmed, rejected, replaced,
authored-domain precedence, conflict, and singleton. It is explicitly
marked SYNTHETIC CONTROL EXAMPLES | NOT REAL IFC OBSERVATIONS; the singleton
is separately marked as an owner scenario. The real-IFC pane labels
provisional_diagnostic_only and ambiguous as observed/proposed respectively.

## Design-only boundary

The renderer read only real_ifc_case.json,
candidate_lifecycle_comparison.json, and synthetic_control_cases.json from
the existing experiment. It did not reopen the source IFC or rerun its adapter.
No production code, adapter, NeutralSceneV2, public API, test, dependency,
source IFC, or user Blender file was modified. No production selector was
chosen, no lifecycle status contract was frozen, and no candidate was promoted
to AnalysisDomain. No room, free-space, connectivity, route, walkability,
Bayesian/ML behavior, threshold, or resolution was inferred.

## Verification

The portable Blender at
D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe generated the
repaired .blend, PNG, and SVG. The saved Blend was reopened by that Blender
for scene readback. JSON parsing, SVG/XML parsing, PNG decoding and framing,
deterministic PNG rerender comparison, and bounded whitespace and scope checks
are recorded in verification_report.json. Per-file byte counts are recorded in
artifact_manifest.json. SHA-256 generation and manifest hash verification remain
blocked: the Stop That Shit Guard denied the requested digest operation and
requires explicit `hash=allow` authority. The manifest records that unresolved
check instead of claiming digest verification passed.

The PNG was opened and visually inspected at full-frame and crop scale for the
plan, candidate/group index, and separate lifecycle strip. Walls, columns,
candidate outlines, group labels, lifecycle terms, and the complete camera
frame and legend were visible. This is a human-readable artifact check in
addition to machine parsing and Blender readback.

The change is limited to disposable design visualization. The original
occlusion/readability finding remains the review target; lifecycle semantics
remain provisional and design-only.

STOP FOR CANDIDATE-SET LIFECYCLE RENDER REPAIR REVIEW
