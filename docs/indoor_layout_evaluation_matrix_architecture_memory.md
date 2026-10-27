# Indoor Layout Matrix Architecture Memory

## Spec008 workflow completion — planned boundary

The 2026-10-19 [Spec008 design](../specs/008-analyzer-workflow-completion/plan.md) completes the camera → Space → free-space workflow, with implementation and native acceptance still pending. Four user decisions are fixed: explicit traceable authored storey height or manual height, never adjacent elevation subtraction; selected slab's horizontal upper surface; two thin native Plane/Space composition bindings; actual Bonsai drawing-camera creation or existing-camera adoption. Native identity/geometry remain authoritative, unsupported tilt is never flattened, and base elevation/B4 cut/extrusion height are separate. B4 exact shell and holes must reach a native void-capable profile/extrusion after explicit confirmation; seed-only native re-inference and exterior-only polygon helpers do not satisfy the design. Furniture eligibility never deletes physical occupancy.

Main-tree workflow dependencies remain absent. Sibling delivery `4b332704` is an inspected integration source, not proof of main-tree availability or a clean snapshot of all current bytes; sibling workflow007 has an unresolved request conflict. First recover a bounded dependency closure in a task-owned jj workspace, preserving dirty work and version-writer boundaries. Native transaction failure recovery, loaded-byte proof and disposable save/reopen validation remain implementation gates. See the [current architecture map](software-architecture.md#spec008-analyzer-workflow-completion--design--implementation-pending); B3 stays OPEN.

## Spec004 Blender analysis workflow — APPROVED / IMPLEMENTATION IN PROGRESS

[Spec004](../specs/004-blender-analysis-workflow/spec.md) / [plan](../specs/004-blender-analysis-workflow/plan.md) were approved by the user on 2026-10-15 and are **APPROVED / IMPLEMENTATION IN PROGRESS**. They propose a lightweight Blender addon over canonical capture, independent structural B4 context and Pixi analysis/display fragments. Request/plane/live-capture dependencies from Spec003 are **CURRENT TREE ABSENT**; existing B4/domain handoff does not satisfy them. T0 requires isolated verification of Git checkpoint `23d24a3` and its approved dependency/import closure while preserving dirty history; missing Spec003 documents remain Git references. Production implementation and acceptance are not claimed here. Existing historical memory below is preserved.

Scope is the unified Analysis workbench, a station toward long-term delivery: one `N → Analysis` panel, independently collapsible Domain and Free-space sections, complete independently usable B4 capabilities plus new free-space. Preserve B4 tolerance/closed-aperture assumptions, outline/holes/area/labels/counts, selection/explicit confirmation, current/attempt/refusal/stale and significant aperture diagnostics in the original service payload. B4 retains its reducer/service and free-space retains AnalysisRequest/Field; future operations join the same UI/service incrementally using existing operation vocabulary and shared capture/identity/confirmed-domain/result access. No new framework/DSL/job-result registry; substitute registry stays substitute selection. Planned read-only metadata list/exact immutable ResultRef open/sample read handles live and restored embedded documents identically, with version/source/domain/plane/query/freshness checks, no stale-as-current or mesh-derived truth, and preserved unknown/conditional/provenance. Headless consumer tests define this seam; no real downstream consumer or future analysis is implemented. B3 OPEN.

This is the durable boundary for the indoor layout evaluation work.

## jj-first Version and Workspace Management

User decision, clarified 2026-10-15: **prefer Jujutsu (`jj`) for all future project version and workspace management**, including delegated work and remote pushes. Git remains an allowed fallback when jj is unavailable or cannot perform the required operation; do not let the tool preference block authorized work.

- Prefer jj for changes/checkpoints, bookmarks, history, integration and recovery. Prefer **`jj workspace`** over Git worktrees or app/skill tools that create managed Git worktrees for isolated or parallel working copies and their lifecycle.
- Use **`jj git push`** for remote pushes when available; Git may remain jj's storage or remote backend. Historical Git commit hashes remain valid references and do not require rewriting history.
- Check the installed jj help before choosing commands. If jj is unavailable or cannot perform the required operation, use the necessary Git command or Git worktree fallback and briefly record the concrete reason. Keep working-copy and history state consistent when switching tools; a fallback within authorized scope does not itself require another permission request.
- Use `jj --ignore-working-copy` for read-only inspection so that inspection does not snapshot unrelated working-copy changes. Preserve existing dirty work and isolate task changes before any authorized checkpoint. Existing version-specialist ownership and push/merge authorization boundaries continue to apply.
- This rule supersedes both older Git-first plans and absolute Git bans. Pixi remains the development environment manager.

## Boundary Rule

SVG is a neutral BIM proxy/base map. SVG does not define the evaluation matrix.

The SVG fixture is only a compact way to provide objective layout records while the BIM/Rhino adapter is not live yet. It may carry geometry, roles, ids, grouping keys, authored affordance geometry, material and surface facts, openings, entries, column axes, and adapter references, but those attributes are input data only.

## Reading Rule

Read this memory first when adding layout abstractions or changing inference/evaluation boundaries.
Then read [`docs/software-architecture.md`](software-architecture.md). It is the canonical project map for operation contracts, substitute selection, layer ownership, implementation placement, and architecture-sensitive verification. Any code or documentation change that crosses a shared analysis boundary must update that map before implementation and keep it consistent with this memory.
Any project work must use the software architecture map to decide what to write, how to write it, and where to place it. If the map is missing a layer or no longer matches code, tests, fixtures, configuration, or exports, inspect those actual artifacts and update the map first. Architecture and implementation changes are maintained together; an older diagram is not evidence that current code follows it.
Read `docs/room_analysis_model_development_standard.md` when adding a model layer or metric.
Read `docs/room_analysis_model_interface.md` only when changing the exported `room_analysis_model` shape.
Read `docs/superpowers/specs/2026-07-22-local-reference-field-research-note.md` before implementing local reference, boundary cue, surface cue, or subject-cue relation features.
Use `docs/indoor_layout_evaluation_matrix_task_status.md` as a history ledger only when auditing old decisions; do not load it by default for ordinary feature work.

## Layer Contract

1. `features/scene_loader.py` converts SVG into a Neutral Scene.
2. `features/scene_inference.py` converts the Neutral Scene into inference evidence.
3. `features/scene_evaluator.py` computes Evaluation Matrix rows from the Neutral Scene and inference evidence.

In contract shorthand, the matrix consumes neutral scene plus inference evidence. Input adapters do not define matrix behavior.

## Neutral Scene

Neutral Scene records are objective inputs: source objects, authored functional
geometry, entries, openings, column axes, geometry, materials, surfaces,
metadata, provenance, and uncertainty. Region, path, and boundary records may
also appear as explicitly authored hints or as clearly marked inference output.
Perceptual weights are not Neutral Scene facts. A BIM adapter should produce
this contract without changing matrix definitions.

## BIM Persistence Rule

Bonsai/Blender is the primary authoring, inspection, and visualization center
for the first BIM adapter. IFC is the durable factual source; the Neutral Scene
is the interoperability contract; `order_analyzer` owns description and
inference.

Use native IFC semantics when they exist: `IfcGrid`/`IfcGridAxis` for authored
grids, `IfcGroup` for authored furniture groups, `IfcCovering` for installed
floor coverings, `IfcSurfaceFeature` for authored surface fields, and
`IfcSpatialZone` with explicit geometry for authored affordance zones. Project
property sets use an `OM_` prefix, never the reserved standardized `Pset_`
prefix.

`MassPatch`, `SurfacePatch`, inferred activity regions, paths, boundary
evidence, graphs, fields, and heatmaps are analyzer-derived records. Do not
write them into the factual IFC by default. Compact analysis snapshots may be
exported only through an explicit command with source ids, algorithm version,
schema version, analysis plane, tolerances, and timestamp.

The current Bonsai project is IFC4. IFC4X3-only relationships must be guarded
by schema checks. Read
`docs/superpowers/specs/2026-08-16-ifc-bonsai-object-mapping-research.md` before
implementing or changing the BIM adapter.
The approved pipeline design is
`docs/superpowers/specs/2026-08-16-ifc4-bim-description-pipeline-design.md`.

The pipeline has explicit `ifc`, `blender_geometry`, `hybrid`, and `svg` input
modes. Ordinary Blender meshes enter only through explicit selection or an
explicit IFC/helper link; they are never silently classified as BIM objects.
The acceptance target is a code-generated disposable three-dimensional scene
with required description and room-model JSON artifacts, not the currently open
Blender toy scene.

## Input Priority

User-authored semantic attributes are the primary input. More precisely, user-authored factual attributes drive description: roles, ids, groups,
optional region hints, authored affordance geometry, materials, surfaces,
openings, column axes, and adapter references. Perceptual weights and final
boundary strength are not neutral-scene facts.

bbox, rect-cell, or geometric fallback algorithms are secondary. They may create computational stand-ins only when explicit semantic attributes are missing or insufficient for an operation. These stand-ins exist to make the matrix computable; they must not override user-authored semantic intent.

Production inference must not invent affordance geometry from a furniture kind. An explicitly separated fixture helper may generate affordance geometry for tests, but the saved result then enters through the same authored-input contract as BIM or SVG data.

## Inference / Evidence Layer

Inference / Evidence Layer consumes authored affordance zones and owns their task-specific projections, furniture affordance extents, inferred region candidates, inferred regions, inferred region gap paths, and inferred gap-path graph evidence. Region and path definitions belong here, not in the SVG file.

The planar inference hierarchy is physical plan projection + affordance-zone projection -> furniture affordance extent -> activity region candidate -> inter-region gap path. The physical and affordance sources remain 3D or height-aware facts; their 2D projections are temporary records tied to an explicit analysis plane. A furniture affordance extent is the union envelope of one physical projection plus its own relevant affordance projections. An activity region candidate is a group of furniture affordance extents. An inferred gap path is remaining free space between activity region candidates, evaluated against a configured body or route width rather than guessed from SVG graphics.

The legacy planar shorthand is object footprint -> furniture affordance extent -> activity region candidate -> inter-region gap path. In Neutral Scene v2,
`object footprint` means a derived `MassPatch` plan projection. The required width read from scene settings remains an explicit demand parameter; BIM input
may supply the same value through `AnalysisContext`.

Activity groups are first-class inference evidence between individual furniture extents and activity region candidates. A group affordance extent is a union envelope of member furniture affordance extents. Pairwise overlaps/intersections are relation evidence, not the definition of the group extent.

An authored IFC `IfcGroup` with `ObjectType = furniture_group` is a factual
FurnitureGroup membership declaration. It is created only from the explicit
Rhino `OM.Role = furniture_group` marker on an outer Block container and has
no product geometry of its own. It is distinct from inferred activity groups,
activity regions, paths, trends, and evaluation values. Block Definition User
Text supplies reusable defaults and Block Instance User Text overrides them;
names, layers, proximity, geometry, and ordinary Rhino groups never infer this
relationship.

Spatial networks use one shared evidence schema for different scopes. `region_internal` networks describe relationships inside one activity group, while `inter_region` networks describe gap-path connectivity between activity region candidates.

Boundary semantics are derived evidence from measured geometry, surface facts, openings, permeability observations, and spatial relations. They keep physical continuity, walk permeability, visual permeability, and Gestalt continuity separate and do not collapse them into a boundary weight or grouping strength.

Neutral planar consumers keep physical occupancy distinct from channel-specific
blocking. `physical_occupancy` contains source records with factual mass geometry
regardless of furniture, wall, partition, railing, or unknown product role. The
selected analysis-domain support geometry and conceptual path, region, entry,
opening, surface, and grid records are excluded from occupancy. `walk_blockers`
and `visibility_blockers` remain height-band/channel observations, while the
legacy `physical_blockers` field retains its boundary-only compatibility
meaning.

Physical volume contributes to interior occupancy and downstream free-space
analysis independently of furniture eligibility. This includes counters, plants,
and other non-furniture sources. A qualified, source-bound substitute may stand
for represented originals once; their raw facts remain, but their mass and
uncertainty must not be counted again. Missing or failed substitute geometry
keeps the affected source unknown, never known free. Excluding a source from
furniture, group, trend, orientation, or affordance analysis does not remove its
physical obstacle. Selected-domain boundary members follow the separate exact
membership exclusion rule below.

The shared operation registry is `scripts/design/group_level/trend_substitute_registry.json`,
loaded by `features/substitute_contract.py`. `resolve_source_representation` in
`features/analysis_substitute_discovery.py` executes its consumer, input,
representation, fallback, and exact coverage policies. `free_space` consumes
`physical_occupancy`; the trend compatibility wrapper uses the same resolver.
`_resolved_physical_occupancy` in `features/neutral_scene_views.py` accounts for
original sources independently of projection success and selects each approved
`MassPatch` once. `GeneratedProxy` describes provenance, not a new geometry kind.
The default shared query is whole-height planar projection. The B3 shared
enrollment route is now implemented for an explicit world-XY query at `z=1.6 m`
through `physical_occupancy_section`, `features/section_views.py`, and the
isolated `run_b3_shared_occupancy_enrollment.py` runner. It uses the same
physical `MassPatch` representative as the default query; a second query-specific
binding for the same consumer is ambiguous and must be rejected. Missing required
geometry prevents dependent free-space scores/topology from being certified,
while known occupied evidence remains. Arbitrary tilted planes, general
height-bands, live adapter promotion, complete occupancy, and complete clearance
remain open. See the current software architecture and
`docs/project/b3-shared-occupancy-enrollment-plan.md` for implementation scope,
validation, and remaining limits.

For a selected analysis domain, `provenance.boundary_member_source_ids` may
declare exact component membership. A token must uniquely identify one
`SourceObject.id` or `SourceObject.source_id`; unmatched, duplicated, or ambiguous
tokens exclude nothing and remain diagnostic. Occupancy inventory uses raw
source identities, so missing projected geometry does not erase an exact boundary
membership. Projected channel consumers still retain an `unprojected` diagnostic
when they have no record for that member. Qualified B2
semantic contour contribution refs may populate this provenance for the one
selected inferred scope. `SourceOpening.host_refs`, source class, name, geometry
overlap, and proximity never establish membership. Resolved members remain in
raw source, uncertainty, and channel evidence, but are omitted from interior
physical occupancy and interior blocker selections. This scope rule does not
assert physical absence, walking permeability, optical transparency, or
complete channel availability. Legacy `physical_blockers` keeps its existing
compatibility meaning.
Doors, windows, and similar infill confirmed as selected-domain boundary
members count as the closed analysis boundary for interior occupancy and
uncertainty selection; the component class never supplies that confirmation.
Serialized field consumers may use the same exact-identity resolver with a
scope- and source-bound human membership declaration, preserving original
source records and qualification errors.

Subject-interface relation scope is explicit in `AnalysisContext`.
`subject_interface_max_distance` defines the production query range;
`subject_interface_all_pairs` is an explicit validation mode. Member-owned
interfaces are outside the relation universe rather than being reported as
range-excluded `not_evaluated` pairs.

An analysis canvas or source-file extent is never a substitute for an analysis
domain. When the Neutral Scene lacks an explicit analysis domain, negative
space and all dependent topology graphs are `not_available`; adapters must not
serialize them as computed zero-node graphs. This unavailable status propagates
through evidence geometry and route-topology handoffs.

Column-grid field evidence is an additive continuous layer over the explicit axis/branch/bay scaffold. It summarizes local support, clarity, and strength at deterministic region probes, and it must not replace bay-based local profiles or force orthogonal snapping.

## BIM Preview And Handoff Rule

The Blender preview is an output-only inspection surface. It consumes a
serialized preview manifest produced from Neutral Scene source geometry and
inference evidence; it does not define regions, paths, trends, boundaries,
grids, weights, or scores. Source meshes use their authored triangle topology,
while derived overlays use separate tagged objects in `OM_AnalysisPreview`.
Repeated generation may remove only objects and materials carrying the preview
tag. Missing runtime Blender execution must remain an explicit verification
limitation rather than being inferred from a successful Python manifest build.

## Region Trend Frame Rule

Terminal furniture and furniture-group direction is derived from final
world-space `Analysis` `MassPatch` plan geometry in the analysis coordinate
system. Member terminal frames are recomputed from that geometry for group
trend and coherence; authored local orientation, placement rotation, block
axes, and transform history remain provenance-only audit fields and must not
affect trend, strength, clarity, coherence, or column-grid alignment. When
terminal geometry is unavailable, the adapter exposes an explicit uncertainty
or documented geometry fallback rather than fabricating a historical direction.

### Single-Furniture Frame Rule

Single-furniture orientation is a description-layer fact, separate from group
or region trend. Compute it from the furniture's authored or imported
`Analysis` `MassPatch` plan projection; use `Body` only as an audit comparison.
Use area-weighted 2D PCA over the MassPatch triangles so tessellation density
does not become a hidden weight. Report a primary axis, its orthogonal
secondary axis, both extents, eigenvalues, and the continuous orientation
strength `(lambda_primary - lambda_secondary) / (lambda_primary +
lambda_secondary)`. A square or circular proxy may retain a deterministic
angle for rendering, but its near-zero strength states that the direction is
not informative. Furniture count, group membership, affordance, and region
membership must not affect this single-object strength.

Region trend is a two-axis frame inferred from activity-group frame evidence. The raw activity-group/frame angle remains auditable as `axis-original-angle` when a later correction is applied.

Trend ground truth is member furniture frame consensus when directional member evidence exists. Shape geometry is separate: PCA, hulls, bbox envelopes, and affordance extents describe region shape, occupancy, and path spacing, but they should not override trend direction. A single directional furniture item can therefore have strong trend strength; evidence support should be audited separately from concentration.

Near-orthogonal visual noise should not be corrected by a hard small-angle threshold. The accepted rule is explainability-first: compare the current region frame with its nearest 0/90-equivalent frame, and correct only when the orthogonal frame Pareto-dominates the current frame. That means the orthogonal frame must keep the projection envelope no larger, explain member furniture frames at least as well, have some member-frame support, and improve at least one of area or member alignment.

This correction applies only to the region trend/frame metadata. It must not reintroduce broad region-shape candidate selection or rewrite the SVG/BIM proxy geometry. Real oblique organization, such as the oblique north tables or west lounge samples, should remain oblique when the orthogonal frame explains the members or envelope worse.

After the final region trend angle is selected, `axis-primary-extent` and `axis-secondary-extent` must be recomputed in that same final frame. Do not carry PCA extents across angle normalization or correction, because overlays and downstream audits draw lengths from these metadata fields.

## Evaluation Matrix

The current matrix organizes and audits objective description evidence. A later perception-calibrated model may select, combine, and weight those descriptions. Neither layer should depend on SVG-specific rendering, SVG element names, or hand-authored SVG overlay conventions.

## Practical Test

If a behavior still works when the scene is a plain Python dict with `Rect` geometry and no SVG parser involved, it belongs to the inference or matrix layer. If it requires `data-*` parsing or XML traversal, it belongs to the input adapter layer.

## Code Comment Rule

This is mandatory for every new or modified project-owned code path. Every
function must have an English-first docstring. Important computation or functional
blocks must have English-first comments that explain why the step exists, especially
inference, scoring, geometry conversion, graph construction, serialization,
and adapter handoff logic. Comments must clarify intent rather than restate
obvious assignments. Short Chinese annotations may be added where they improve
communication with project stakeholders, but they supplement rather than replace
the English documentation.

All new or modified project-owned code should follow this rule.
Every function should have a docstring.
Important computation steps should have comments that explain why they exist.

Before each checkpoint, audit the touched project-owned files for this rule and
repair omissions before declaring the checkpoint ready.
Vendored OCTA toolbox code is exempt unless it is edited.

## Unified Field kernel — US1/US2/US3 implemented; FreeSpaceField instance implemented

### IMPLEMENTED — Spec002 offline inspection output

Spec002 implements an output-only HTML/SVG inspection layer for the frozen
whole-height `FreeSpaceField` handoff. The implemented route is:

```text
authenticated frozen package
  -> runner-local whole-height NeutralSceneV2
  -> analysis_scene_view
  -> existing FreeSpaceField
  -> build_field_layer_manifest
  -> self-contained HTML/SVG inspection
```

This implemented layer does not create a second semantic field, alter the Field core,
rebuild a direct-preview resolver, or promote into the evaluator, room model,
B3 loader, clearance, or connectivity. It must preserve explicit world-XY
metres, frozen source-origin metadata, the effective shared-view offset, exact domain holes, upstream boundary identity,
and per-proxy provenance. The five locked unresolved ids retain canonical
`missing_geometry` uncertainty before shared-view promotion; captured
references/arrays are audit-only where qualified geometry refs are absent.
Historical `z=1.6 m` samples remain section evidence only and are not reused as
whole-height values. Serialization may deduplicate repeated global provenance
only if each original cell record remains exactly recoverable.

US1 now implements one global `Field` concept with shallow capabilities in
`features/field_core.py`: `Field`, `FieldQuery`, `FieldSample`, and the
six-state status vocabulary are production code with immutable query/sample
metadata and exact scalar/batch lookup. US2 now implements
`features/space_field_adapter.py:B3AdapterView` and
`features/space_field_visualization.py:build_field_layer_manifest` as
read-only seams over validated B3 data. The B3 loader, free-space bundle, and
live evaluator promotion remain unchanged or planned; the Spec002 runner owns
its output-only SVG/HTML renderer.
Spatial occupancy, distance, demand, influence, and object-to-candidate-group
evidence share domain/frame/query/provenance semantics but remain distinct
channels. Exact lookup and batch lookup are required; interpolation is
optional. A missing domain is `not_available`, a valid query outside an
available domain is `outside`, incomplete evidence is `unknown`, and a limited
accepted-substitute whole-height result is `conditional`; every conditional
sample must include a non-empty explanation of its representation limitation.
None may be silently
converted to known free or whole-height truth. See
`specs/001-field-kernel-free-space/owner-decision.md` and the implementation
section in `docs/software-architecture.md`.

The concrete `FreeSpaceField` instance in
`features/free_space_field.py` is an exact-cell, two-dimensional
physical-occupancy field over already resolved `analysis_scene_view` plan
components. It composes the shared `Field` core and existing geometry helper;
it does not rescan sources, call the resolver, introduce a runtime
`FieldBundle`, or alter boundary exclusion. It supports only the frozen
whole-height handoff; section/height-band/tilted-plane/demand requests remain
`not_available`. It does not change `evaluate_scene`, room-model output, B3
live promotion, clearance, connectivity, or decay semantics. Final precision
independent review is complete for this slice, with the final focused and
combined evidence recorded as 67 and 141 passed. B3/live promotion and
constitution ratification remain open.

The shared field output boundary is the immutable
`FieldResultEnvelope` (`field-result-envelope/v1`). It carries the canonical
target and query, raw result status, normalized channel set, frozen channel
records, support, projection metadata, provenance, explanation, and cache
identity. Cache identity is computed at the complete target/query/channel and
input/source/recipe/algorithm/schema boundary; a `FieldSample` or rendered
manifest is only a projection and never defines cache validity. Raw status and
unavailable channel records remain auditable even when no scalar value can be
projected.

`FieldSample` is the validated scalar projection used by existing field
consumers. `field-layer-manifest/v1` is the visualization projection. Its
adapter preserves raw status, channel set, channel records, provenance, and
mapping explanation; when the envelope cannot produce a valid sample it uses
the conservative `unknown` status and `unknown` visual state. This retains the
existing free-space compatibility semantics and does not reinterpret partial,
unavailable, invalid, outside, or ambiguous evidence as known free space.

This implementation slice has no group candidate inference, group candidate
selector, scalar aggregation, score or weight calculation, or job/result
registry. Object-to-candidate-group evidence and later scalar aggregation
remain future/design-only work and must not be described as implemented by the
field envelope.

The first geometry relation package is implemented in
`features/group_geometry_relation_field.py`. It adapts the existing
IFC-derived authored-group member-pair observations into descriptive
`FieldResultEnvelope` records. The package does not infer group membership,
support, potential, strength, or a winner. The 2026-10-27 delivery maps every
one of the 666 group-pair envelopes to pair JSON/SVG with an overview and
source/plane/unit manifest; all 667 SVG files parsed and representative PNG
views were visually reviewed. The corrected contract test passed on the
retained real IFC scene/description, not an independent geometry extraction.
Overlap, shared-member and missing/invalid/partial branches are not covered
by this source. The user accepted the geometry-field sample review on
2026-10-27 ("合理"); next clarify evidence use and rules before stage-2
comparisons. Complete candidate-by-unit attribution, strength and further
evidence packages remain pending. See the [package record](project/evidence/geometry-relation-field-package-v1.md#current-verification-and-limits).
`describe_group_relations`
reuses the unshifted geometry projections from its single `analysis_scene_view`
call to avoid projecting those meshes twice; this invocation-local cache is a
temporary performance workaround, not a shared cache contract.

The second diagnostic package is `features/group_trend_alignment_field.py`.
Its current public group-target channels are `overall_group_axis` and
`layout_axis`. The lower-level `member_frame` and `member_axis` descriptors
remain available as suppressed audit data so the single-furniture layer can be
restored without deleting history. The former four-channel IFC run remains a
historical v1 artifact; the current runner uses the v2 schema. The package
does not compose potential or strength and does not mutate group membership.

The user's 2026-10-27 plane decision is temporary world-XY supplied by
`scene.context.analysis_plane`. Group queries must match that plane and
diagnostic drawing must consume the same plane-local polygons. Do not encode
world-XY as an evidence rule or treat this as camera-plane integration.

The geometry and trend package runners also emit the shared read-only
`field-evidence-package-status/v1` payload beside their contracts. This is a
UI-facing handoff only; the future UI consumes `recompute_required`, `reasons`,
and `affected_targets` without deriving freshness from rendered views.
The runner-written status compares a new contract with itself as a write-time
receipt. Later consumers must compare the stored contract with a newly built
current contract. Artifact validation checks every declared path for non-empty
readable bytes; it does not validate content or checksums.
Automatic recomputation, cache storage/eviction, and target-level dependency
graphs are outside this boundary.
