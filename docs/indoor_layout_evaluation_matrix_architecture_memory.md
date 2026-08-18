# Indoor Layout Matrix Architecture Memory

This is the durable boundary for the indoor layout evaluation work.

## Boundary Rule

SVG is a neutral BIM proxy/base map. SVG does not define the evaluation matrix.

The SVG fixture is only a compact way to provide objective layout records while the BIM/Rhino adapter is not live yet. It may carry geometry, roles, ids, grouping keys, authored affordance geometry, material and surface facts, openings, entries, column axes, and adapter references, but those attributes are input data only.

## Reading Rule

Read this memory first when adding layout abstractions or changing inference/evaluation boundaries.
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

## Region Trend Frame Rule

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
