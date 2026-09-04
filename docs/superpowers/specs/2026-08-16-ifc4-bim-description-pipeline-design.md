# IFC4 BIM Description Pipeline Design

Date: 2026-08-16
Status: design specification; implementation has not started

## Goal

Add an IFC4/Bonsai input and Blender visualization route to the existing indoor
layout analyzer without moving analysis algorithms into Blender and without
making IFC or SVG semantics part of the evaluation matrix.

The pipeline must preserve spatially varying three-dimensional geometry. A
sofa, cabinet, wall, platform, or other uneven object must not be reduced to one
height or one world-axis bbox before boundary, visibility, and walkability
evidence is measured.

## Success Criteria

1. An IFC4 model and an SVG fixture can enter through separate adapters and
   produce the same versioned Neutral Scene contract.
2. IFC geometry, relationships, materials, surfaces, groups, grids, and authored
   affordance zones retain source ids and derivation provenance.
3. `MassPatch`, `SurfacePatch`, and `AffordanceZone` support task-derived plan,
   vertical, clearance, and occlusion views without becoming object-name-based
   proxy classes.
4. Boundary output separates physical continuity, walking permeability, visual
   permeability, and Gestalt continuity. It exposes no aggregate boundary
   weight or perceptual score.
5. Existing region, trend, path, network, and column-grid analysis consumes
   Neutral Scene records or their derived views, never Blender objects,
   IfcOpenShell entities, or SVG XML nodes.
6. Blender displays source geometry and analysis overlays without creating,
   repairing, reclassifying, or otherwise mutating source IFC entities.
7. All transport and description records are JSON-serializable or have an
   explicit serializer; raw Python geometry objects must not leak into adapter
   payloads.
8. A disposable, programmatically generated Blender/Bonsai acceptance scene
   exercises uneven height, surfaces, affordances, boundaries, regions, paths,
   trend frames, and column-grid relations in one end-to-end run.
9. The acceptance run writes stable, inspectable description and room-model
   JSON artifacts. Blender visualization is supporting evidence rather than the
   only proof that the analysis succeeded.

## Non-Goals

- Repairing or completing the currently open Blender research fixture.
- Automatically classifying ordinary Blender objects as IFC entities or
  silently including unselected Blender objects in an IFC analysis.
- Inferring authored affordance geometry from furniture names or classes.
- Automatically inferring the authored column grid.
- Writing dense fields, graphs, heatmaps, or inferred boundaries back to the
  factual IFC by default.
- Producing perception-calibrated weights or a final layout score.
- Supporting every IFC schema in the first implementation. IFC4 is the
  baseline; IFC4X3 extensions are guarded enhancements.
- Replacing all existing planar algorithms in one change.

## Architectural Invariants

```text
Bonsai/IFC, explicit Blender geometry, hybrid IFC/Blender geometry, or SVG
    -> source adapter
    -> Neutral Scene facts
    -> functional substitutes and task views
    -> inference and description matrix
    -> room_analysis_model
    -> Blender preview / notebook / serialized result
```

- IFC and SVG are input formats, not analysis frameworks.
- Source geometry remains authoritative. Transport meshes and 2D projections
  are derived representations with explicit provenance.
- Semantic classes select applicable extractors; they do not directly assign
  boundary strength, passability, visibility, or order.
- Missing evidence remains unavailable or uncertain. The analyzer must not
  manufacture certainty from a class name such as `IfcWall` or `glass`.
- Computational tolerances are configuration and provenance, not perceptual
  weights.
- The description registry exposes objective values. Learned combinations
  belong to a later feature/model layer.

## Explicit Input Modes

Every analysis request names one input mode. Mode selection is part of
`AnalysisContext` provenance and cannot be inferred from whichever objects are
currently visible in Blender.

- `ifc`: read only the selected IFC file and its native facts;
- `blender_geometry`: read only explicitly selected Blender geometry plus an
  explicit sidecar mapping of roles and relationships;
- `hybrid`: read the selected IFC file, then add only explicitly linked Blender
  helper geometry;
- `svg`: read the structured planar fixture and declare planar-only capability.

All four modes terminate at the same Neutral Scene validation boundary.
Downstream substitute, inference, description, and room-model code must not
branch on the source application. Capability flags and unavailable evidence,
rather than source-name checks, determine which operations can run.

## Package Boundaries

### `features/scene_contract.py`

Own the versioned pure-Python Neutral Scene v2 records and serialization. It
must not import Blender, Bonsai, IfcOpenShell, SVG libraries, or OCTA.

Initial records:

- `AnalysisContext`;
- `AnalysisDomain`;
- `SourceObject`;
- `MeshGeometry3D`;
- `MaterialFact`;
- `SurfaceFact`;
- `AuthoredGroup`;
- `AuthoredGrid` and `AuthoredGridAxis`;
- `AuthoredAffordanceZone`;
- `SourceOpening`;
- `UncertaintyRecord`.

Every function and record constructor follows the repository comment rule:
English docstrings plus comments at important geometry, inference, graph, and
adapter handoff steps.

### `adapters/ifc_bonsai.py`

Read IFC4 through IfcOpenShell. When called from Blender it may receive the
active Bonsai IFC file, but it must operate on the IFC file rather than infer
semantics from Blender names or collections.

Responsibilities:

- schema and unit validation;
- world placement resolution;
- stable `GlobalId` and representation provenance;
- triangulated transport geometry extraction with IfcOpenShell settings
  recorded in provenance;
- native group, grid, material, surface, opening, and spatial-zone relations;
- custom `OM_` factual properties;
- structured uncertainties for absent, invalid, or unsupported facts.

It must not compute regions, boundaries, paths, trend, order, or scores. The
IfcOpenShell dependency is optional at package import time; calling this
adapter without it returns a focused dependency error.

### `adapters/blender_geometry.py`

Read explicitly selected ordinary Blender mesh objects into the same Neutral
Scene v2 contract without fabricating IFC semantics. This is a geometry input
adapter, not an automatic BIM classifier.

The adapter supports two explicit modes:

- `blender_geometry`: selected Blender meshes and explicitly supplied roles,
  groups, domain, surfaces, grids, and affordance links are the source facts;
- `hybrid`: IFC remains the primary factual source and only explicitly linked
  Blender helper geometry augments named IFC records or supplies a named
  analysis domain.

`ifc` mode never includes unlinked Blender objects. `blender_geometry` mode
never pretends that a mesh has an IFC class or `GlobalId`. `hybrid` mode records
both source identifiers and the explicit link method. Missing semantics remain
unavailable; object names and collection names may be preserved as provenance
but must not silently determine furniture kind, affordance, grid, permeability,
or boundary meaning.

### `adapters/svg_scene.py`

Wrap the current `features/scene_loader.py` behavior behind the same Neutral
Scene v2 contract. Existing SVG fixtures remain useful, but planar-only input
must declare its capability limits. It must not invent three-dimensional height
or permeability evidence from a `Rect`.

The existing public SVG entry point may remain as a compatibility wrapper while
tests and notebooks migrate.

### `features/geometry_substitutes.py`

Build the three long-lived functional records from Neutral Scene facts:

- `MassPatch` from physical source geometry;
- `SurfacePatch` from coherent source surfaces and material/color/elevation
  regions;
- `AffordanceZone` from explicitly authored functional geometry.

This module is source-format independent. It may use a geometry backend, but it
must not inspect IFC class names or SVG metadata after normalized facts have
been provided.

One source object may produce multiple patches. A `MassPatch` follows a
connected physical component or another explicitly justified local partition;
a `SurfacePatch` follows an authored surface region or a connected face region
with coherent surface identity. Patch count is therefore geometric evidence,
not one hard-coded proxy per BIM object.

### `features/geometry_views.py`

Provide deterministic, cacheable operators over substitutes:

- `plan_projection(patch, analysis_plane, height_band=None)`;
- `vertical_intervals_at(patch, point, direction)`;
- `vertical_profile(patch, sample_geometry)`;
- `surface_elevation_at(surface, point)`;
- `occlusion_intersections(patch, ray_or_band)`;
- `clearance_geometry(patches, body_profile, analysis_plane)`.

The cache key includes source geometry identity, geometry settings, analysis
plane, height/body profile, method, and tolerance configuration.

### `features/boundary_evidence.py`

Derive candidate interfaces and their objective channels from substitute views.
It must not define a universal `Boundary` source class or collapse channels into
one strength.

### Existing analysis modules

`features/scene_inference.py`, `features/scene_evaluator.py`,
`features/local_reference.py`, and `features/column_grid.py` remain the analysis
engine. During migration they must be changed to consume view protocols rather
than raw `Rect`, SVG metadata, or legacy authored weights.

`features/room_analysis_model.py` remains the exported description model. New
records and metrics attach to explicit `target_layer` and `target_id` values in
accordance with `docs/room_analysis_model_development_standard.md`.

If Neutral Scene v2 changes the exported `room_analysis_model` shape rather
than only adding metric evidence, update its contract version and
`docs/room_analysis_model_interface.md` in the same change.

### `adapters/blender_preview.py`

Render analysis output into a dedicated non-IFC preview collection such as
`OM_AnalysisPreview`.

It displays:

- original Blender/Bonsai source geometry without replacement;
- inferred activity-region geometry;
- both trend axes with lengths representing directional concentration;
- authored column axes and derived grid relations;
- boundary-channel geometry and compact legends;
- selected tabular descriptions in a panel or notebook-friendly payload.

Preview objects contain result ids and source `GlobalId` references but are not
assigned IFC classes. Regeneration replaces only the preview collection. It
does not alter source object geometry, materials, placement, classification, or
IFC relationships.

### `test/blender/generate_bim_acceptance_scene.py`

Build a disposable abstract three-dimensional acceptance scene by code. The
fixture is an executable test input, not a manually maintained production BIM
model and not a repair of the currently open research scene.

The generated scene contains:

- an explicit room analysis domain, floor, and walls;
- simplified table-chair groups, a sofa, and a low cabinet;
- a sofa with a low seat and high back so local height queries differ by plan
  position;
- a carpet or color surface with surface evidence but no physical mass;
- explicit three-dimensional chair affordance volumes;
- a low cabinet and a transparent partition that separate walking and visual
  evidence;
- an authored simple column grid;
- aligned, oblique, and deliberately less-ordered furniture regions.

The generator must be deterministic and safe to rerun. It may write a temporary
`.blend` or IFC fixture for inspection, but tests rebuild it from source code
and do not depend on manual edits to that file.

### End-to-end acceptance outputs

The generated scene is analyzed through the IFC route and, where applicable,
the explicit Blender-geometry route. At minimum the run writes:

```text
test/output/blender_demo_description.json
test/output/blender_demo_room_analysis_model.json
```

The description artifact includes source facts, substitutes, local vertical
interval samples, the four separate boundary channels, inferred furniture
groups and activity regions, two-axis trend frames and strengths, internal and
inter-region networks and paths, local and global column-grid relations,
provenance, tolerances, capability flags, and uncertainty. The room-model
artifact exposes the corresponding versioned `target_layer`/`target_id`
records without perceptual weights or a final score.

A minimal `OM_AnalysisPreview` shows source geometry, inferred regions, two
trend axes, authored grid axes, paths, and selected boundary evidence for human
alignment checks. The JSON artifacts and assertions remain authoritative.

## Neutral Scene V2 Contract

### Analysis context

`AnalysisContext` contains:

- contract version;
- source schema and adapter version;
- source length unit and normalized analysis unit;
- world coordinate system and level/storey references;
- named analysis plane with origin and orthonormal basis;
- geometry and topology tolerances;
- requested walking body profiles and visual height bands;
- extraction capability flags.

The adapter converts source coordinates once. It must not duplicate transforms
inside every later proxy.

### Analysis domain

`AnalysisDomain` identifies the room, space, storey portion, or explicit volume
being analyzed. Its geometry comes from a selected `IfcSpace`, another explicit
spatial container, or a user-supplied analysis volume. The source and selection
method remain auditable.

The adapter must not silently use the bbox of all loaded objects as the room.
If no explicit domain exists, domain-dependent region, free-space, and boundary
metrics are unavailable until a domain is selected. A separately requested
geometric fallback may derive a candidate domain, but it is inference evidence
with uncertainty rather than an authored room fact.

### Source object

`SourceObject` contains:

- stable neutral id and source `GlobalId` or adapter id;
- normalized source role and original IFC class;
- world transform and level/container references;
- one or more `MeshGeometry3D` references;
- type, group, material, surface, and opening references;
- authored local frame when geometry is directionally ambiguous;
- provenance and uncertainties.

The original IFC class remains auditable but is not used as a boundary score.

### Mesh geometry

`MeshGeometry3D` contains numeric vertices, triangle indices, optional normals,
closed/open-manifold diagnostics, local-to-world transform provenance, source
representation id, tessellation settings, and units. It must serialize to plain
lists and numbers at adapter boundaries.

IfcOpenShell's tessellated result is a transport and query representation. The
source IFC representation remains authoritative through its ids and settings.

### Authored affordance

`AuthoredAffordanceZone` contains explicit 3D geometry, vertical extent,
purpose/task facts, source furniture references, and provenance. Missing
geometry makes the zone unavailable; the analyzer must not generate a default
zone based on furniture class.

### Materials and surfaces

Material and surface facts keep separate:

- material identity and assignment;
- measured or authored optical values such as visible transmittance;
- viewport style transparency;
- surface color, finish, and texture identity;
- host/source relationships and uncertainty.

Viewport transparency is not substituted for physical optical transmittance.

## Spatially Varying Height And Mass

`MassPatch` represents geometry, not one scalar height. The first implementation
uses the normalized triangle mesh plus a spatial index.

For a requested plan position, `vertical_intervals_at` casts a line normal to
the analysis plane, sorts mesh intersections, and pairs valid entering/exiting
hits into occupied intervals. This distinguishes a sofa seat, back, arms, feet,
and voids at different positions without random sampling and without an object
bbox height.

Important cases:

- Closed solids produce occupied intervals directly.
- Multiple disconnected components produce multiple intervals.
- Open or non-manifold meshes return observed intersections plus uncertainty;
  they must not silently claim a closed volume.
- Coplanar and duplicate hits are merged using the recorded geometric
  tolerance, not a perceptual threshold.
- Repeated queries use a spatial index; a raster, voxel field, or adaptive mesh
  may cache acceleration data but is not the authoritative record.

Plan projection derives a polygon set from projected mesh faces or sectioned
geometry at a named height band. A world-axis bbox is diagnostic/fallback data
only and cannot replace the polygon when boundary or path precision matters.

## Surface And Elevation Evidence

`SurfacePatch` is a coherent two-dimensional manifold embedded in 3D. It can
represent floor finish, carpet, paint/color field, sloped floor, platform top,
wall face, or another continuous surface.

Operators expose:

- connected surface components;
- surface identity and contrast facts;
- local elevation and slope;
- edge geometry, closure, gaps, and continuation;
- projection/section on the active analysis plane.

A step or split-level edge is derived where adjacent walk-supporting surfaces
have a measurable elevation discontinuity. A carpet or color boundary may
produce strong surface/common-region evidence while producing no physical mass
or walking obstruction.

## Boundary Evidence Contract

A boundary candidate is an analyzer-derived interface with geometry,
provenance, source ids, method, tolerances, and separate evidence channels.

Candidate interfaces may originate from:

- exterior or vertical faces and projected contours of `MassPatch` geometry;
- openings, inter-object gaps, and occupied-height discontinuities;
- elevation or slope discontinuities between walk-supporting surfaces;
- material, color, finish, or connected-surface edges;
- good continuation between separated mass or surface pieces;
- the explicit analysis-domain interface.

Candidate generation collects evidence only. It does not decide that every
object contour is an important boundary.

### Physical continuity

Expose connectedness, occupied height intervals, thickness, run length, gap
geometry, opening provenance, and continuation between source pieces.

### Walking permeability

For each named body profile expose crossing clearance, collision intervals,
opening width/height, elevation change, reachable side relation, and a factual
pass/fail/unknown result. Body dimensions are explicit analysis parameters, not
learned weights.

### Visual permeability

For each named eye height or height band expose ray/sample support, occluded
fraction, unobstructed openings, optical transmittance when available, and an
unknown state when material evidence is insufficient. Geometry blocking and
material transmission remain separate fields.

### Gestalt continuity

Expose alignment, gap ratio, good continuation, repetition/spacing regularity,
closure, common-region containment, and surface similarity/contrast. These are
descriptions, not a learned perceptual importance score.

No core record may contain `boundary_strength`, `walk_block`, `see_block`, or
`grouping_strength` as authored final weights. Legacy SVG rows may remain only
behind an explicit compatibility flag until their consumers are migrated.

### Subject-boundary relations

Boundary evidence and its effect on a furniture group or activity region are
different records. For every relevant subject-interface pair, expose distance,
nearest side, angular/frame agreement, parallel coverage, containment/common-
region relation, intervening gaps/openings, and which permeability observations
apply. Candidate pairs are selected by spatial indexing and explicit analysis
range parameters. A range limit controls computation only: relations outside
the evaluated range are marked `not_evaluated`, never assigned a zero value.
An all-pairs mode remains available for validation and small scenes.

Do not output one boundary-influence weight. A later perception model may learn
how distance, coverage, orientation, continuity, height, and permeability
combine.

## Relation To Existing Region And Path Logic

The existing planar hierarchy remains valid after changing its inputs:

```text
MassPatch plan projection
    + authored AffordanceZone projection
    -> furniture affordance extent
    -> furniture group extent
    -> activity region candidate
    -> inter-region free-space path
```

- Furniture groups may be authored through `IfcGroup` or inferred from semantic,
  geometric, affordance, and network evidence. Authored and inferred provenance
  stays separate.
- Region trend continues to come from furniture-group frame consensus, not from
  the region bbox or IFC world axes.
- Region geometry uses polygonal projections. `Rect` remains a compatibility
  optimization only when the polygon is genuinely axis-aligned rectangular.
- Inter-region paths are remaining free-space geometry between activity regions
  and have explicit route/body width parameters.
- Internal and inter-region networks continue to use the same graph schema with
  different scopes.

## IFC4 Mapping

The adapter applies the verified mapping from
`2026-08-16-ifc-bonsai-object-mapping-research.md`:

- `IfcFurniture` -> source furniture;
- `IfcGroup`/`IfcRelAssignsToGroup` -> authored furniture group;
- `IfcGrid`/`IfcGridAxis` -> authored grid and axes;
- `IfcSpatialZone/USERDEFINED` with `OM_AFFORDANCE_ZONE` -> authored affordance;
- `IfcCovering/FLOORING` -> installed floor covering;
- `IfcSurfaceFeature/USERDEFINED` -> authored color/treated surface field;
- native walls, slabs, doors/openings, columns, spaces, and containers -> source
  geometry and topology facts;
- standard material/optical properties plus minimal `OM_` factual properties ->
  material, task, and provenance facts.

IFC4X3-only relationships such as `IfcRelAdheresToElement` are accessed only
after a schema capability check. IFC4 retains explicit geometry, context, and
stable host/source references without fabricating an IFC4X3 entity.

## Error And Uncertainty Behavior

- Unsupported schema: stop adapter creation with the schema and supported
  baseline in the error.
- Missing IFC geometry: emit a source record with unavailable geometry and an
  uncertainty; do not substitute a Blender name or bbox silently.
- Invalid/open mesh: retain observable surface evidence and mark solid/volume
  queries uncertain.
- Missing affordance geometry: omit the affordance view and report the source
  zone id; do not infer a replacement.
- Missing optical facts: report geometric occlusion and optical uncertainty
  separately.
- Missing grid: column-grid metrics are unavailable; do not infer a grid by
  default.
- Missing analysis domain: domain-dependent free-space, region, and boundary
  metrics are unavailable; do not use a whole-scene bbox silently.
- Plain Blender object with no IFC link: ignore it in `ifc` mode. In
  `blender_geometry` mode, include it only when explicitly selected and retain
  absent semantics as unavailable. In `hybrid` mode, require an explicit source
  link or helper role. Never classify or repair it automatically.
- Serialization failure: identify the record path and unsupported value type;
  never pass raw `Rect`, mesh wrapper, or IFC entity objects to JSON.

## Migration Sequence

1. Lock the trustworthy 295-test baseline and add a machine-readable acceptance
   manifest without changing analysis behavior.
2. Introduce Neutral Scene v2 records, validators, and serializers without
   changing current metric behavior.
3. Adapt SVG input to v2 with explicit planar-only capability declarations and
   cross-contract regression fixtures.
4. Add pure geometry substitutes and deterministic local height/vertical query
   tests using synthetic meshes.
5. Add surface/elevation operators and four-channel boundary evidence over
   substitute views.
6. Add the IFC4 adapter and in-memory IFC fixtures.
7. Add explicit `blender_geometry` and `hybrid` adapter modes while proving that
   `ifc` mode ignores unlinked Blender objects.
8. Migrate region, path, trend, local-reference, and grid consumers away from
   raw SVG metadata, bbox assumptions, and authored weights.
9. Generate the disposable Blender/Bonsai acceptance scene from the spatial
   organization exercised by the existing SVG examples, then run the complete
   description pipeline and write the two required JSON artifacts.
10. Add Blender preview rendering as an output-only adapter and perform visual
    alignment checks against the acceptance artifacts.
11. Run cross-adapter, no-mutation, full pytest, notebook, JSON schema, and
    portable-Blender verification before considering the pipeline complete.

Each numbered migration item is a review gate and normally one jj change. A
gate may be split into a short coherent series, but the next gate cannot start
until focused tests, the full accepted regression suite, artifact inspection,
and Grill Me-style self-review pass. Fixes stay in that gate's change before it
is described and checkpointed. Do not combine the migration into one
unreviewable change or postpone all commits until the end.

## Test Strategy

### Contract tests

- All v2 records serialize and reopen without Python object leakage.
- Units, transforms, ids, geometry provenance, analysis planes, and tolerances
  survive round trip.
- SVG and IFC adapters produce contract-valid records without importing each
  other's dependencies.

### Geometry substitute tests

Use generated meshes with known answers:

- a box with constant height;
- a sofa-like stepped solid with low seat, high back, arms, and bottom void;
- a low cabinet that blocks walking but not a higher visual band;
- a transparent partition with geometric blocking and optical transmission;
- a platform and split-level floor;
- a carpet/color surface with no mass;
- two aligned objects separated by a walkable gap;
- an open/non-manifold mesh that must return uncertainty.

Verify local vertical intervals at multiple positions, plan projections,
surface elevations, opening/gap provenance, and channel separation.

### IFC adapter tests

Build IFC4 fixtures in memory, serialize, reopen, and load through the adapter.
Cover furniture, group membership, grid axes, walls/slabs/openings, coverings,
surface features, authored affordance zones, materials, units, placements, and
missing facts. Add a focused IFC4/IFC4X3 schema-guard test.

### Analysis regression tests

- Existing SVG region, trend, path, network, and column-grid fixtures remain
  behaviorally stable when routed through v2.
- Equivalent planar IFC and SVG fixtures produce equivalent derived plan
  evidence within recorded geometric tolerances.
- Height-aware metrics remain unavailable for planar-only SVG rather than being
  fabricated.

### Blender/Bonsai integration tests

- Run against a disposable generated IFC fixture in the user's configured
  portable Blender only.
- Compare source IFC entity count and a stable source-entity digest before and
  after analysis.
- Verify preview collection regeneration changes only preview objects.
- Visually inspect source geometry, regions, two trend axes, grids, boundary
  channels, and compact tables from several viewpoints and plan view.
- Do not repair or use the user's current toy scene as an acceptance fixture.

### Generated acceptance-scene assertions

The generator exposes stable source ids and the test asserts facts that are
independent of rendering:

- the room domain, floor, walls, furniture, surface patch, partition, grid,
  and affordance zones are present;
- the sofa produces different occupied vertical intervals at seat and back
  probe positions;
- the carpet/color surface contributes surface evidence without contributing
  physical mass;
- the low cabinet and transparent partition produce distinct walking and visual
  channel observations;
- aligned, oblique, and mixed furniture groups produce distinct two-axis trend
  angles and concentration values;
- internal and inter-region network records are present and remain the same
  graph schema with different scope values;
- grid relations include both local and global evidence;
- both required JSON artifacts reopen using only standard JSON types and contain
  source ids, methods, tolerances, and uncertainty fields;
- running analysis twice produces equivalent description payloads apart from
  explicitly timestamped provenance;
- source IFC entity count and source-entity digest are unchanged after preview
  regeneration.

The assertions must fail when the analyzer silently falls back to one world
bbox, invents affordance geometry, treats a surface as physical mass, collapses
the boundary channels, or includes unselected Blender objects.

### Completion gate

Completion requires:

- focused tests for each new component;
- the full project pytest suite with zero failures attributable to the accepted
  baseline;
- executed notebook examples for serialized description output;
- Blender visual verification and source-IFC no-mutation evidence;
- documentation of known unavailable evidence and schema limitations.

## Rollout And Compatibility

Neutral Scene v2 is introduced alongside the current dict contract. A
serializer/compatibility adapter supplies legacy planar fields while consumers
are migrated. It must label compatibility-derived values and must not invent
height or optical evidence.

The public matrix output changes only through versioned additions until the
legacy score/weight rows have explicit replacements. Removing legacy output is
a later, separately reviewed change.

## Design Decisions Requiring No Further Brainstorming

- Bonsai/Blender is the first BIM authoring and visualization center.
- IFC4 is the baseline schema.
- IFC remains factual and read-only during normal analysis.
- Affordance geometry is authored input.
- Column axes are authored input.
- Boundary is derived evidence, not an IFC class or authored weight.
- Spatially varying height comes from geometry queries, not one object height.
- Mesh is a transport/query accelerator with source provenance, not semantic
  truth.
- SVG and IFC remain separate adapters to one analysis core.

## Preview Delivery Contract

The Blender description preview is a read-only presentation adapter over the
serialized Neutral Scene and inference records. It must preserve source mesh
triangle topology, show source geometry together with inferred regions, both
trend axes, authored grid axes, gap paths, and boundary-channel markers, and
write a deterministic preview manifest that the notebook reads back. Preview
objects and materials are tagged and may be regenerated idempotently without
touching unrelated source objects or materials. A generated Python script or
HTML/PNG artifact is not evidence that Blender itself executed successfully;
runtime smoke verification must be reported separately.

## Grill Me Self-Review

- **Does the design reduce an uneven object to one height or bbox?** No. Local
  occupied intervals come from geometry queries, and one source may yield
  multiple patches.
- **Does an IFC class directly decide boundary or permeability?** No. Classes
  select factual extraction; geometry, surfaces, openings, materials, and
  relations supply evidence.
- **Can missing material or geometry facts become false certainty?** No. They
  produce unavailable or uncertain channels.
- **Can a performance cutoff masquerade as zero influence?** No. Unevaluated
  relations remain explicitly unevaluated.
- **Can the adapter or preview repair the user's model?** No. Normal analysis
  is read-only and preview objects are non-IFC output.
- **Does the design duplicate the matrix inside Blender?** No. Blender is an
  authoring/preview surface; the analyzer remains independent.
- **Is the migration a dangerous big-bang rewrite?** No. V2 coexists with a
  labeled compatibility adapter while consumers migrate in small jj changes.
- **Are version and provenance changes auditable?** Yes. Contracts, geometry
  settings, units, analysis planes, methods, tolerances, source ids, and schema
  capabilities are explicit.
- **Can a normal Blender mesh be analyzed without turning Blender into a second
  BIM authority?** Yes. Only explicit `blender_geometry` or `hybrid` requests
  admit it, and the neutral adapter preserves missing semantics as unavailable.
- **Is the three-dimensional acceptance model a hidden manual dependency?** No.
  It is rebuilt deterministically from code, has stable ids, and produces JSON
  artifacts whose assertions do not depend on a viewport screenshot.
- **Can a large migration lose its place or become impossible to review?** No.
  Every migration gate has focused tests, regression tests, artifact checks,
  self-review, and a jj checkpoint before the next gate.
