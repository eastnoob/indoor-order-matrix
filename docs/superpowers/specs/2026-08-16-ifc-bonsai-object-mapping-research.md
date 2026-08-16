# IFC And Bonsai Object-Mapping Research

Date: 2026-08-16
Status: research decision for the BIM adapter; not an implementation claim

## Question

Determine which indoor-layout inputs should be native IFC objects, which facts
need project-defined properties, and which analysis records should remain in
`order_analyzer`. Confirm the mapping against official specifications and the
running Blender/Bonsai environment before planning an adapter.

## Method

The research used three independent evidence sources:

1. buildingSMART IFC 4.3.2 documentation for entity semantics and schema
   constraints;
2. official Bonsai and IfcOpenShell documentation for authoring and API
   capabilities;
3. isolated round-trip probes inside the user's running portable Blender,
   Bonsai, and IfcOpenShell environment.

The local probes created temporary in-memory IFC files, serialized and reopened
them, and verified entity classes, geometry, relationships, and property values.
They did not add entities to the active Bonsai project.

## Local Environment Evidence

The tested environment is:

- Blender `5.2.0 LTS`;
- Bonsai `0.8.5`;
- IfcOpenShell `0.8.5`;
- active project schema `IFC4`;
- active project entity count `140` before and after the isolated probes.

The active project currently contains one project, site, building, and storey,
plus four `IfcWall` entities. It contains no grid, column, furniture, group,
spatial zone, covering, or surface-feature entities. The Blender objects named
`IfcSlab_RoomFloor` and `IfcDoor_Entry` are not linked to IFC entities. An
IFC-looking Blender name is therefore not BIM evidence; the adapter must query
the IFC entity link and class.

The active Blender scene is a disposable research fixture, not a model-repair
target. Its missing classifications are observations used only to test adapter
assumptions. Repairing, completing, or reclassifying this scene is explicitly
outside the adapter research and implementation scope. A future adapter may
report an unlinked object, but it must not modify or repair it automatically.

The isolated IFC4 round trip successfully wrote and reopened:

- one `IfcGrid` with U/V axis lists, four tagged `IfcGridAxis` records, and
  persisted `IfcPolyline` axis curves;
- two `IfcFurniture` occurrences and one `IfcGroup` membership relation;
- one geometric `IfcSpatialZone/USERDEFINED` identified as
  `OM_AFFORDANCE_ZONE`;
- one `OM_Affordance` property set and furniture references through
  `IfcRelReferencedInSpatialStructure`;
- one `IfcCovering/FLOORING` and one geometric
  `IfcSurfaceFeature/USERDEFINED` identified as `OM_COLOR_FIELD`;
- `Pset_MaterialOptical.VisibleTransmittance=0.82` separately from viewport
  style transparency `0.75`.

A separate IFC4X3 probe verified `IfcRelAdheresToElement`. Creating that
relationship under IFC4 failed because the entity is not in that schema, which
is the expected and desired version guard.

## Verified Native IFC Semantics

### Structural grid

Use `IfcGrid` with `IfcGridAxis` records. `IfcGrid` owns U, V, and optional W
axis lists and supports rectangular, radial, and triangular grids. Each axis
has an `AxisTag`, a two-dimensional `AxisCurve`, and `SameSense`.

Grid bays, local grid fields, and region-grid relations are analyzer-derived.
They are not additional authored grid classes.

### Furniture and groups

Use `IfcFurniture` for furniture occurrences. Use `IfcGroup` and
`IfcRelAssignsToGroup` for authored furniture groups. An `IfcGroup` is logical
and non-geometric, and one object may participate in more than one group.

Automatic furniture grouping remains analyzer evidence. It must not silently
rewrite authored group membership.

### Authored affordance geometry

Use an `IfcSpatialZone` with:

- `PredefinedType=USERDEFINED`;
- `ObjectType=OM_AFFORDANCE_ZONE`;
- explicit three-dimensional or height-banded geometry;
- `IfcRelReferencedInSpatialStructure` references to source furniture;
- a minimal `OM_Affordance` property set for task/purpose and provenance.

`IfcSpatialZone` is appropriate because it is a non-hierarchical, overlapping
functional spatial decomposition that may have independent geometry. Do not
use `IfcSpace`, which implies physical/hierarchical space, or
`IfcBuildingElementProxy`, which implies a physical product.

Production analysis must consume the authored zone. Furniture-name heuristics
may exist only in a separated fixture generator that writes test input first.

### Floor and surface organization

Use `IfcCovering` with `PredefinedType=FLOORING` for an installed carpet or
floor covering. Use `IfcSurfaceFeature` with a project-specific `ObjectType`
such as `OM_COLOR_FIELD` for a painted, marked, or treated surface region that
is not a separate covering product.

In IFC4X3, `IfcRelAdheresToElement` explicitly relates a surface feature to its
host. This relationship is unavailable in the current IFC4 project. The IFC4
baseline must therefore retain explicit geometry, spatial context, and a
stable host/source reference without pretending that the IFC4X3 relation
exists. Schema migration may replace that fallback with
`IfcRelAdheresToElement`.

### Material and optical facts

Material assignment and measured optical facts are separate from viewport
appearance. `IfcSurfaceStyleRendering.Transparency` is rendering information.
When available, `Pset_MaterialOptical.VisibleTransmittance` is the stronger
objective input for visual-permeability analysis. Missing optical facts must
remain missing or uncertain; a material name such as `glass` must not be
converted directly into a permeability score.

### Project-defined properties

The buildingSMART `Pset_` prefix is reserved for standardized property sets.
Project-owned sets use the `OM_` prefix, for example `OM_Affordance`; they must
not be named `Pset_OM_*`. Stable custom names, types, and applicability should
be defined with `IfcPropertySetTemplate` and applied as ordinary property sets.

Project-defined properties store factual intent and provenance, not perceptual
weights or final scores.

## Final Object Mapping

| Concept | IFC4 baseline | IFC4X3 enhancement | Ownership |
| --- | --- | --- | --- |
| Project/site/building/storey/room | `IfcProject`, `IfcSite`, `IfcBuilding`, `IfcBuildingStorey`, `IfcSpace` | Same | User/BIM |
| Wall, slab, door/opening, column | Native IFC product and feature classes | Same | User/BIM |
| Furniture | `IfcFurniture` | Same | User/BIM |
| Authored furniture group | `IfcGroup` + `IfcRelAssignsToGroup` | Same | User/BIM |
| Column grid and axes | `IfcGrid` + `IfcGridAxis` | Same | User/BIM |
| Carpet or installed floor finish | `IfcCovering/FLOORING` | Same | User/BIM |
| Painted/color surface field | `IfcSurfaceFeature/USERDEFINED`, geometry, spatial context, explicit host/source reference | Add `IfcRelAdheresToElement` | User/BIM |
| Authored affordance zone | `IfcSpatialZone/USERDEFINED`, `OM_AFFORDANCE_ZONE`, geometry, furniture references | Same | User/BIM |
| `MassPatch`, `SurfacePatch` | Neutral Scene records | Same | Analyzer-derived |
| Activity region and gap path | Neutral Scene geometry and graph evidence | Same | Analyzer-derived |
| Boundary evidence | Separate continuity and permeability channels | Same | Analyzer-derived |
| Trend, local-reference, and grid relation | Description rows/relations | Same | Analyzer-derived |
| Dense fields, graphs, and heatmaps | External sidecar or transient Blender visualization | Same | Analyzer-derived |

## Persistence Policy

The source IFC is the durable factual model. The Neutral Scene is the adapter
contract. `order_analyzer` owns measured and inferred descriptions.

- Persist authored geometry, semantics, groups, axes, materials, surfaces,
  affordance zones, and stable source relationships in IFC.
- Persist only compact derived summaries when a user explicitly exports an
  analysis snapshot. Mark schema version, algorithm version, source ids,
  analysis plane, tolerances, and timestamp.
- Keep dense meshes, sampled fields, walk/visual graphs, and heatmaps external
  or transient. They are reproducible outputs and would bloat and stale the
  factual BIM model.
- Do not use `IfcRelSpaceBoundary` for the project's emergent boundary
  evidence. IFC space boundaries describe building-space relationships, not
  the full physical, visual, walk, and Gestalt evidence vector.

## Bonsai Workflow Decision

Bonsai/Blender is the most complete BIM authoring, inspection, and
visualization center for the first adapter. IFC is the persistent factual
source, and `order_analyzer` is an independent description engine.

```text
Bonsai-authored IFC
    -> IFC/Bonsai adapter
    -> Neutral Scene
    -> order_analyzer
    -> description records, relations, fields
    -> Blender overlays and tables
    -> optional explicit analysis-snapshot export
```

Bonsai can assign an arbitrary valid IFC class to Blender geometry and expose
IFC attributes, containers, materials, and property sets. IfcOpenShell provides
dedicated APIs for grid, group, property-set, and property-template operations.
Dedicated Bonsai panels for every target class are not required and must not be
assumed: uncommon records may be authored through generic class assignment or
a focused project operator while remaining native IFC.

## Adapter Validation Gates

1. Treat Blender objects with no IFC entity link as non-IFC input and report
   that fact when relevant. Do not repair or classify them automatically.
2. Report schema incompatibilities explicitly, especially IFC4 versus IFC4X3
   relationships.
3. Preserve `GlobalId`, source relationships, geometry provenance, units,
   placement, and level context through the Neutral Scene.
4. Round-trip each authored class through write/reopen before relying on it.
5. Verify that running analysis does not mutate the source IFC unless an
   explicit export command is invoked.
6. Compare Blender overlays against the source geometry and inspect the
   exported description table; unit tests alone are insufficient.

## Grill Me Self-Review

- **Are custom classes being invented where IFC already has semantics?** No.
  Grid, axes, groups, furniture, coverings, surface features, and spatial zones
  use native classes.
- **Is affordance inferred from a furniture label?** No. It is explicit
  functional geometry with provenance.
- **Are derived boundaries being mislabeled as IFC space boundaries?** No.
- **Does viewport transparency become optical truth?** No.
- **Are IFC4X3 relations promised in the current IFC4 file?** No; the mapping
  states a baseline and an enhancement separately.
- **Can derived data silently stale the source BIM?** No; source mutation is
  opt-in and dense outputs remain external/transient.
- **Are hidden perceptual weights introduced?** No. The mapping carries only
  facts, measurements, uncertainty, and provenance.
- **Was API success confused with dedicated UI support?** No. Generic authoring
  and API support are recorded separately from specialized panels.

## Sources

- buildingSMART, `IfcGrid`:
  https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcGrid.htm
- buildingSMART, `IfcGridAxis`:
  https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcGridAxis.htm
- buildingSMART, `IfcGroup`:
  https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcGroup.htm
- buildingSMART, `IfcSpatialZone`:
  https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcSpatialZone.htm
- buildingSMART, `IfcCovering`:
  https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcCovering.htm
- buildingSMART, `IfcSurfaceFeature`:
  https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcSurfaceFeature.htm
- buildingSMART, `IfcSurfaceStyleRendering`:
  https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcSurfaceStyleRendering.htm
- Bonsai, create a model:
  https://docs.bonsaibim.org/quickstart/create_model.html
- IfcOpenShell grid API:
  https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/grid/index.html
- IfcOpenShell group API:
  https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/group/index.html
- IfcOpenShell property-set API:
  https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/pset/index.html
- IfcOpenShell property-template API:
  https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/pset_template/index.html
