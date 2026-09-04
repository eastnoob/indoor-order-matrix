# Analysis Description And Substitute Architecture Note

Date: 2026-08-10
Updated: 2026-09-02

## Purpose

This note records the current software boundary before BIM integration. The
project is currently building a description layer, not a perceptual feature
model or a final weighted score.

## Runtime Collaboration

The first BIM workflow is:

```text
Bonsai-authored IFC
    -> IFC/Bonsai adapter
    -> Neutral Scene
    -> order_analyzer description and inference
    -> description records, relations, and fields
    -> Blender overlays and tables
```

- Bonsai/Blender is the primary BIM authoring, inspection, and visualization
  center for the first adapter.
- IFC is the persistent factual source, not a container for every dense or
  temporary analysis result.
- `order_analyzer` is the independent calculation engine.
- The adapter only translates geometry, semantics, identifiers, measured
  properties, and provenance. It does not define matrix metrics.
- Rhino/VisualARQ remains a possible authoring adapter. It should produce the
  same Neutral Scene contract rather than becoming an analyzer dependency.
- The SVG loader is a temporary input adapter that produces the same Neutral
  Scene contract for tests.

The verified IFC/Bonsai object mapping and schema-version constraints are in
`docs/superpowers/specs/2026-08-16-ifc-bonsai-object-mapping-research.md`.
The implementation-facing pipeline design is in
`docs/superpowers/specs/2026-08-16-ifc4-bim-description-pipeline-design.md`.
The currently open Blender scene is only a research fixture; repairing or
completing that scene is not part of the adapter roadmap.

## Description Layer Boundary

The description layer records objective facts and derived geometric relations:

- geometry and projections;
- height and elevation profiles;
- thickness and openings;
- material, color, and surface continuity;
- walk and visual passability observations;
- distances, overlaps, containment, angles, closure, and connectivity;
- source identifiers, derivation method, and uncertainty.

The description layer must not contain perceptual weights, importance values,
or a final score. A directional concentration statistic may describe angular
dispersion, but it must not be interpreted as perceptual importance.

## Minimal Input Contract For The Current Simplified Scene

The first BIM/Rhino migration does not need every possible BIM property. It
only needs enough source facts for the analyzer to derive the descriptions.

### Required for every source object

- stable `id`;
- `kind` or source semantic role;
- native geometry, preferably BRep, otherwise Mesh;
- coordinate system/unit and level reference.

The transform is part of the native geometry record. It should not be copied
into several proxy-specific attributes.

### Furniture

Tables and chairs require:

- stable id, kind, and geometry;
- explicit 3D or height-aware affordance geometry when the usable space is not
  recoverable from the solid, such as a chair pull-back/sitting zone;
- an authored local frame only when the geometry is directionally ambiguous.

Furniture group membership is optional input. A table-chair group is normally
derived from semantic roles, affordance relations, proximity, and spatial
network evidence. An authored group id remains an auditable hint when present.

### Walls

Walls require only their geometry and level context. Height, thickness,
openings, and planar boundary segments should be measured from the geometry.
If a source adapter supplies only a centerline, thickness and height become
required adapter facts, and openings must be supplied as explicit gaps.

### Low bookcases

Low bookcases require only their geometry and level context. They must not
carry `is_boundary` or `boundary_strength`. Boundary evidence is derived at
analysis time from their footprint, height profile, continuity, gaps, and
relation to nearby space.

Material and transparency are not required for this restricted scenario when
the solid geometry is sufficient. They become optional source facts when a
bookcase or partition has holes, glass, screens, or other non-solid
permeability.

### Computed at analysis time

The following are not persistent source attributes in this first contract:

- plan projections of mass and affordance geometry;
- furniture groups and activity regions;
- gap paths and clearance fields;
- height/vertical profiles;
- boundary candidates and boundary evidence;
- walk and visual graph evidence;
- trend frames, directional concentration, and column-grid relations;
- heatmap samples.

These records are derived from the minimal source facts and retain source ids
and derivation provenance.

## Functional Substitute Principle

Substitutes are selected by the computation they enable, not by the source
object name. There should not be separate `GlassProxy`, `ChairProxy`, or
`WallProxy` classes.

The minimal substitute design is three long-lived analysis records. They
preserve source geometry and provenance. A 2D polygon, vertical profile, mesh,
graph, or field is a task-specific derived representation, not another source
object that must be kept in sync.

### `MassPatch`

Represents local physical mass derived from object geometry.

Minimum validity definition:

> A valid `MassPatch` is the smallest triangulated geometry, in a unified
> coordinate system and unit, that can answer whether a plan position is
> occupied, which height intervals are occupied there, and whether a queried
> line of sight is blocked.

This definition is about analysis observability rather than visual similarity.
The proxy may be much simpler than the source geometry, but it must preserve
the plan gaps, height changes, holes, and occluding surfaces that affect those
queries. A single bounding box is therefore valid only when it preserves these
observations within the declared geometric tolerance.

Derived functional representations:

- `PlanProjection2D`: a 2D polygon or polygon set derived on a named analysis
  plane. It contains physical occupancy evidence, not affordance semantics.
- `VerticalProfile`: a measured set of height intervals, base/top elevations,
  thickness, gaps, and openings. It is used by boundary and level analysis.
- `OcclusionGeometry`: BRep faces or a derived analysis mesh used to test
  visual obstruction. It is not the same thing as a subjective visibility
  weight.
- `ClearanceField2D`: a 2D clearance representation derived from the plan
  projection, openings, and an explicit moving-body profile. It is used by
  walkability and path analysis.

The same `MassPatch` can therefore describe a sofa back, cabinet, wall,
column, platform edge, or any other height-producing geometry without using
source names as the algorithm.

### `SurfacePatch`

Represents a coherent surface or surface region.

`SurfacePatch` is a two-dimensional manifold embedded in 3D space. It is not a
duplicate plan drawing: a carpet, sloped floor, wall face, and platform top may
all be surfaces with different positions and orientations.

Derived functional representations:

- `surface_identity`: material, color, finish, and texture descriptors;
- `surface_continuity`: connectedness, contrast, edge clarity, and closure;
- `SurfaceProjection2D`: a projection or section on the active analysis plane,
  used for common-region containment and grouping evidence;
- `surface_elevation`: measured elevation and slope facts used to derive
  level changes.

The same `SurfacePatch` can describe a carpet, floor-color field, material
zone, raised platform surface, or other continuous surface organization.

### `AffordanceZone`

Represents task, use, or body-operation space that is not identical to the
physical mass. It may be a 3D volume, a height-banded volume, or an authored
functional region with explicit vertical limits.

Examples include chair pull-back and sitting space, approach space in front of
a cabinet, and shared use space around a table. It must be supplied by the
source adapter or an explicitly separated test helper; normal analysis must not
silently invent it from a furniture name. A test helper may generate and save
fixture geometry, but the analyzer must subsequently read that geometry as
input rather than calling the helper during inference.

Derived functional representations:

- `AffordanceProjection2D`: projection onto the active floor or analysis plane
  for grouping, region, clearance, and path calculations;
- `AffordanceHeightRange`: occupied or required vertical intervals for
  collision, reach, and height-aware accessibility calculations.

The furniture affordance extent used by existing planar inference is therefore
the union of `MassPatch.PlanProjection2D` and the relevant
`AffordanceProjection2D`. It is a derived 2D calculation result, not the
authoritative affordance object.

## Source Geometry Versus Functional Representations

Source geometry remains authoritative:

- BRep/NURBS is preferred for exact face, edge, trim, intersection,
  thickness, and opening measurements.
- Mesh is a derived accelerator for dense sampling, ray tests, height fields,
  and heatmap generation.
- 2D polygons are projections or sections derived on an explicit analysis
  plane for plan-based operations.
- Graphs and heat fields are analysis outputs, not substitutes.

The fact that 3D contains the information needed for 2D does not make the 2D
operation unnecessary. Projection, sectioning, and height filtering define
which part of the 3D scene participates in a particular planar calculation.
These results should be cached only as derived records with source ids,
analysis-plane id, method, and tolerance provenance.

When a Rhino BRep is available, the bridge should preserve it as provenance
and derive a mesh with explicit meshing parameters for repeated field queries.
RhinoCommon provides direct Brep-to-mesh conversion and mesh-ray
intersection support for this workflow. The mesh must never silently replace
the source geometry or overwrite its measured facts.

## What Calls What

```text
source BRep / source mesh / authored functional geometry
    -> MassPatch
    -> SurfacePatch
    -> AffordanceZone

MassPatch
    -> PlanProjection2D (physical occupancy)
    -> VerticalProfile (1D/2.5D)
    -> OcclusionGeometry (BRep faces or analysis mesh)

AffordanceZone
    -> AffordanceProjection2D
    -> AffordanceHeightRange

PlanProjection2D + AffordanceProjection2D
    -> furniture affordance extent (derived 2D union)
    -> furniture group extent
    -> activity region candidate
    -> inter-region gap path

PlanProjection2D + openings + ClearanceField2D
    -> physically walkable free space
    -> walk graph geometry

AffordanceProjection2D + physically walkable free space
    -> activity-space conflict and route-interference evidence

VerticalProfile
    -> height/elevation boundary candidates
    -> level-change evidence

OcclusionGeometry
    -> visual occlusion observations
    -> visual graph evidence

SurfacePatch.surface_continuity
    -> surface cue
    -> common-region evidence
    -> surface boundary candidate

MassPatch + SurfacePatch relations
    -> boundary evidence
    -> local reference relation
    -> walk graph / visual graph evidence
```

Region, path, trend, boundary, and column-grid descriptions consume these
functional views. They must not inspect the original Rhino or SVG element name
when a neutral description is available.

## Integrated Description Hierarchy

The complete description flow has the following ownership boundaries:

1. Source facts contain room/level context, native object geometry, coherent
   surfaces and materials, authored affordance geometry, explicit openings,
   and user-authored column-grid axes.
2. Geometry preprocessing derives `MassPatch` and `SurfacePatch` records while
   preserving source ids. Authored functional geometry becomes
   `AffordanceZone` records.
3. Task operators derive plane-aware projections, vertical profiles,
   clearance fields, occlusion geometry, and surface sections.
4. Organization inference derives furniture frames, furniture groups, activity
   regions, region trend frames, and internal organization evidence. Region
   trend comes from furniture-group frame consensus; region shape geometry is
   separate evidence.
5. Network inference uses one graph contract for `region_internal` and
   `inter_region` scopes. Inter-region paths are free-space relations between
   activity regions, while physical walkability is validated independently.
6. Reference inference derives boundary interfaces, subject-boundary
   relations, column-grid bays/fields, and local/global frame relations.
   Column-grid axes are authored input; bays and influence fields are derived.
7. The description registry exposes objective values, vectors, graphs,
   provenance, methods, tolerances, and uncertainty without perceptual weights.
8. A later experiment-calibrated model may select and combine description
   variables to predict ratings or produce evaluative heatmaps.

## Boundary Continuity And Gaps

A boundary is derived interface evidence, not a binary object role and not a
synonym for an impassable obstacle. Its effect on a furniture group or region
is a separate subject-boundary relation. Boundary evidence must keep at least
four objective channels separate:

- `physical_continuity`: whether physical geometry is materially continuous;
- `walk_permeability`: whether a specified moving body can cross the interface;
- `visual_permeability`: whether sight can cross the interface at a specified
  eye-height or height band;
- `gestalt_continuity`: whether alignment, proximity, similarity, and good
  continuation organize separated pieces as one perceptual run.

A passable gap between two aligned bookcases can therefore break physical and
object continuity, permit walking, and still preserve Gestalt continuation.
Its visual permeability depends on the objects' height and the tested sight
band. No single `boundary_strength` should collapse these observations.

Gap provenance must also remain explicit:

- `opening`: a hole hosted by one physical object, such as a doorway in a wall;
- `inter_object_gap`: free space between separate objects, such as two
  bookcases;
- `inter_region_gap_path`: free space inferred between activity regions.

All three may contribute to movement or visibility graphs, but they are not
interchangeable descriptions.

## Description Values Versus Later Features

Description values include:

- `height`, `thickness`, `elevation_delta`, `opening_width`;
- `distance`, `overlap_ratio`, `containment_ratio`, `coverage_ratio`;
- `angle_delta`, `frame_clarity`, `directional_concentration`;
- `surface_contrast`, `surface_continuity`, `closure_ratio`;
- `walk_clearance`, `visual_occlusion`, `transmission_observation`;
- graph adjacency, component identity, and reachability evidence.

Later feature design may select, normalize, combine, or learn from these
values. It may not feed its learned or subjective weights back into the
description layer.

## Open Boundary

The next implementation should first stabilize the Neutral Scene and
description registry around `MassPatch`, `SurfacePatch`, `AffordanceZone`, and
their derived functional representations. The first production adapter should
target IFC4 through Bonsai/IfcOpenShell. A Rhino adapter, feature selection
model, and perception-calibrated global score remain later layers.

This note supersedes older prototype fields such as `boundary_strength`,
`grouping_strength`, and authored boundary weights as core description-layer
inputs. Historical specs retain those names only as an implementation ledger.

## Current Prototype Gap

The present SVG implementation has not yet reached this contract. It still
uses axis-aligned `Rect`/bbox records in several inference paths, reads authored
`walk_block`, `see_block`, and `grouping_strength` weights, and exposes a legacy
aggregate score projection. `MassPatch`, `SurfacePatch`, `AffordanceZone`, and
their plane-aware derived representations are the migration target, not names
for capabilities already completed.

## Grill-Me Correction: Clean Rhino/BIM Canonicalization

The previous plan needed one important correction: a clean BIM model must not
be created by deleting source layers, flattening every group, or assigning
meaning from names alone. Cleaning is a non-destructive canonicalization step.
It produces a small, typed BIM representation while preserving the original
Rhino file and source identifiers for audit.

The corrected decision is:

1. Keep the imported Rhino document as a read-only source archive.
2. Build a canonical BIM view from explicit VisualARQ/IFC semantics first.
3. Use geometry and grouping only as secondary evidence for candidate
   assemblies and classification.
4. Send ambiguous candidates to a review list instead of silently guessing.
5. Keep analyzer-derived regions, paths, trends, boundaries, fields, and
   heatmaps outside the factual BIM model unless the user explicitly exports
   an analysis snapshot.

This prevents three common failures:

- Rhino layers become mistaken for BIM classes.
- Nested or overlapping Rhino groups cause duplicate furniture counts.
- Detailed manufacturer meshes become dozens of false analysis objects.

### Rhino Responsibilities

Rhino layers control visibility, selection, display, and print organization.
They are not the semantic model. Rhino groups are named/nestable selection
sets, and blocks are reusable component definitions/instances. They are useful
for source organization and repeated geometry, but neither one alone proves
that an object is a wall, furniture item, assembly, or analysis region.

The preferred source-to-BIM order is:

```text
VisualARQ object / explicit IFC type or tag
    > explicit source metadata
    > block definition and stable group evidence
    > geometry heuristic
    > manual review
```

The geometry heuristic can propose a result, but it must not overwrite
explicit semantic input. Every canonical object keeps `source_ids`,
`source_layer`, `source_group_ids`, `classification_method`, and
`classification_confidence` so that the clean view remains reversible.

### Canonical Rhino Layer Layout

The clean view uses a deliberately small layer taxonomy:

```text
00_SOURCE_ARCHIVE       locked source import; never edited by the cleaner
10_BIM
  11_ARCHITECTURE       walls, slabs, openings, structural elements
  12_FURNITURE          canonical furniture and furniture assemblies
  13_SURFACES           floor finishes, carpets, surface fields
  14_SITE_DECOR         plants and non-architectural scene elements
  15_COMPONENTS         retained child parts that are not counted separately
90_REFERENCE            authored axes, guides, source links, review marks
99_ANALYSIS_PREVIEW     hidden derived overlays and disposable diagnostics
```

These layers are display containers only. Direct object/type metadata is the
semantic source. A layer-to-IFC mapping may be used as an export fallback for
untyped Rhino geometry, but it must be reported as lower-confidence provenance.

### Canonical Object Boundary

One canonical BIM object represents one functional physical unit for the
analysis domain. A table with attached legs is one furniture object; a
table-and-chair arrangement can additionally be represented as an authored
assembly or group. Small meshes, fasteners, door hardware, and decorative
parts remain child/source geometry unless they have independent spatial or
functional meaning.

For repeated furniture, prefer one reusable block/style definition plus
instances. For a complex single object, keep the detailed geometry as its
visual representation and derive hidden analysis representations from it.
The canonical object boundary is therefore based on functional identity and
analysis relevance, not on mesh count.

### VisualARQ Decision

VisualARQ is suitable for the Rhino-side authoring and normalization pass:

- use native Wall, Slab, Door, Window, Column, Furniture, and Element objects
  where their semantics fit;
- use Furniture or Element styles backed by 3D/2D blocks for reusable objects;
- use typed custom parameters for source ids, assembly roles, level, material,
  and analysis handoff metadata;
- use the VisualARQ IFC tag/type mechanism for objects that need an IFC export
  category;
- run persistent document mutation through a Rhino/VisualARQ command or
  RhinoCommon script, not as an implicit Grasshopper-side mutation.

VisualARQ custom parameters can be attached to ordinary Rhino geometry and
exported as IFC properties. This makes them useful for traceability and
project-specific facts, but they do not replace native IFC semantics where a
native class exists.

There is no accepted rule here that a Rhino layer, block, or VisualARQ style
is itself a furniture group, activity region, boundary, or column-grid field.
Those concepts remain Neutral Scene or analyzer records unless explicitly
authored as factual BIM input.

### Coffee-Shop Conversion Strategy

For a model such as `materials/caffee-normal.3dm`, the first pass should be:

1. Preserve the original file unchanged.
2. Inventory layers, groups, blocks, object types, transforms, and source ids.
3. Collapse repeated or nested source groups into candidate functional units.
4. Classify obvious architectural objects and furniture through explicit
   semantics before geometry heuristics.
5. Attach detailed meshes as child/source geometry rather than counting each
   mesh as a furniture object.
6. Keep plants and decorative elements in a separate category; include them
   in analysis only when the selected analysis policy allows it.
7. Create a review report for untyped walls, doors, columns, groups, and
   ambiguous assemblies.
8. Export only the reviewed canonical view to IFC/Neutral Scene.

The cleaner must not infer a column grid merely from a regular-looking set of
objects. A user-authored grid remains an explicit reference input. If the
source contains only Rhino curves, they can be imported as authored axis
records; deriving a grid from columns is a later, clearly labeled inference
mode.

### Rejected Alternatives

- **Delete-and-rebuild:** rejected because it destroys provenance and makes
  classification errors irreversible.
- **Layer-only BIM conversion:** rejected because layers are organization and
  display controls, not a complete semantic contract.
- **Every-group-is-an-object:** rejected because groups can be nested,
  overlapping, or created only for selection.
- **Every-mesh-is-an-object:** rejected because detailed parts would corrupt
  furniture counts, regions, and paths.
- **Grasshopper-only persistence:** rejected for the canonical document pass;
  Grasshopper is useful for generation, but the persistent object handoff must
  be explicit and auditable.

### Research Record (2026-09-02)

The official documentation supports the following operational conclusions:

| Finding | Consequence |
|---|---|
| Rhino layers organize visibility, selection, display, and print | Do not use layer names as the sole BIM classifier |
| Rhino groups are named/nestable selection sets | Treat groups as evidence, not guaranteed semantic objects |
| Rhino blocks are reusable named component definitions and instances | Use blocks for repeated furniture/component geometry |
| VisualARQ Furniture and Element support 2D/3D block-based styles | Use styles for canonical reusable visual/BIM representations |
| VisualARQ custom parameters are typed and can be assigned to Rhino geometry | Store traceability and project facts without inventing native IFC classes |
| VisualARQ IFC export can assign types by object or layer | Prefer object-level typing; use layer mapping only as a fallback |
| VisualARQ API targets document-resident objects and is not recommended for ordinary Grasshopper temporary geometry | Run the canonicalization handoff as an explicit Rhino command/script |
| Current VisualARQ pages advertise IFC 2x3 and IFC 4 support | Verify the installed translator and target schema before promising round-trip fidelity |

Primary references:

- Rhino layers: `https://docs.mcneel.com/rhino/8/help/en-us/commands/layer.htm`
- Rhino blocks and groups: `https://docs.mcneel.com/rhino/8/help/en-us/seealso/sak_blocksgroups.htm`
- VisualARQ features: `https://www.visualarq.com/features/`
- VisualARQ Furniture styles: `https://help.visualarq.com/architectural-objects/furniture/furniture-styles/`
- VisualARQ Element: `https://help.visualarq.com/architectural-objects/element/`
- VisualARQ custom parameters and IFC export: `https://www.visualarq.com/feature/documentation/`
- VisualARQ IFC translator: `https://help.visualarq.com/visualarq-tools/ifc-translator/`
- VisualARQ API boundary: `https://www.visualarq.com/support/tip/is-there-an-api-or-sdk-for-visualarq/`

### Grill-Me Self-Check Result

- **Does cleaning alter the factual source?** No; the source archive is
  immutable and canonical objects retain provenance.
- **Can a wrong group or layer silently become a BIM object?** No; semantic
  precedence and review status are explicit.
- **Can detailed meshes be double-counted?** No; canonical functional units
  own child/source geometry.
- **Are analysis concepts being smuggled into BIM?** No; regions, paths,
  trends, boundaries, fields, and heatmaps remain derived analyzer evidence.
- **Can the same handoff work for Rhino, SVG, and IFC?** Yes; all adapters
  target the Neutral Scene contract.
- **Is the design overly complex?** No; it adds only canonicalization,
  provenance, and review states; it does not add new proxy classes or a
  second evaluator.
