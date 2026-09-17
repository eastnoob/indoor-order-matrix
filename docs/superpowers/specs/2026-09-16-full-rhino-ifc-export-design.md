# Full Rhino IFC Export Design

## Goal

Make the Rhino/VisualARQ workflow export every source object by default while preserving authored IFC semantics and safely representing objects without semantic labels.

## Required Behavior

1. Every source object with usable geometry is exported exactly once as one IFC product occurrence.
2. An exact authored `IfcEntity` or `OM.IfcEntity` label selects the corresponding supported IFC product class.
3. An object without a valid authored IFC class is exported as `IfcBuildingElementProxy` with `semantic_status=untyped` and `analysis_participation=unknown`.
4. Existing source identity, name, layer, geometry kind, source properties, and provenance are stored as factual project properties.
5. Untyped objects are retained in the IFC but are not treated as furniture, region members, paths, or analysis inputs by default.
6. The exporter reports counts by IFC entity, untyped objects, objects lacking geometry, and review records.
7. The source adapter remains read-only. Export, IFC validation, and Bonsai import remain independent phases.

## Scope

This change modifies the generic Rhino-source exporter and adds a reusable live Rhino geometry capture helper. It does not infer missing BIM semantics, generate MassPatch, merge components into logical products, or alter the Rhino document.

## Entity Selection

The exporter uses this decision order:

```text
valid source_semantics.ifc_entity
    -> that IFC product class
otherwise
    -> IfcBuildingElementProxy
```

The registry must reject non-product classes such as `IfcGridAxis` as object occurrence classes; guides continue through the existing native `IfcGrid` path. Unsupported or conflicting labels are exported as proxies and reported for review.

The initial product registry includes `IfcFurniture`, `IfcFurnishingElement`, `IfcEquipmentElement`, `IfcElectricalElement`, `IfcWall`, `IfcDoor`, `IfcWindow`, `IfcColumn`, `IfcBeam`, `IfcSlab`, `IfcRoof`, `IfcStair`, `IfcRailing`, `IfcOpeningElement`, and `IfcBuildingElementProxy`.

## Geometry Contract

The exporter consumes source records with `vertices` and triangular `faces`. A live Rhino capture may derive these from Mesh, Brep, Extrusion, and InstanceReference geometry using RhinoCommon meshing, while preserving the source object id and transform. Unsupported or empty geometry becomes a review record and is not silently emitted as a zero-geometry product.

## Properties

Every exported object receives `OM_Source` with:

- source id;
- source name and layer;
- source geometry kind;
- authored IFC label and label source;
- semantic status: `authored`, `untyped`, or `review`;
- analysis participation: `include`, `exclude`, or `unknown`;
- source path and provider.

The properties are provenance and conversion facts. They are not a substitute for IFC relationships and do not assign perceptual weights.

## Analysis Boundary

Unyped proxy objects remain available in the IFC for visual completeness and later review. The neutral analysis adapter must filter them unless an explicit user rule includes them. Export does not decide furniture grouping or analysis participation.

## Testing and Acceptance

- Unit tests prove typed classes are preserved and unknown objects become proxies.
- Tests prove one object is not duplicated and source properties survive.
- Tests prove unsupported/non-product labels fall back to proxies with review status.
- Live Rhino MCP `15002` capture exports a full IFC without mutating Rhino.
- IFC inspection reports non-zero product counts and the expected entity distribution.
- IFC validation is run separately; import into Blender/Bonsai is not automatic.
