# Rhino Instance Export Correction Design

## Goal

Correct the Rhino/VisualARQ-to-IFC workflow so that nested block occurrences
retain their authored world placement, furniture remains identifiable as
furniture, and display geometry and analysis substitutes stay attached to one
logical IFC product.

## Confirmed Failure

The failed live export expanded block-definition geometry without applying the
top-level occurrence transform. All 56 chair occurrences therefore shared one
definition-space center, and all 37 table occurrences shared another. The
capture also replaced the top-level furniture identity with nested preview
geometry, leaving every chair and table with `source_semantics.ifc_entity =
unknown`; the exporter consequently emitted them as
`IfcBuildingElementProxy`.

This is a source-capture and logical-product-boundary failure. Blender/Bonsai
rendered the coordinates present in the IFC and is not the source of the error.

## Architecture

The corrected handoff is:

```text
Rhino top-level occurrence
    -> transform-aware recursive capture
    -> one normalized logical occurrence with representation branches
    -> IFC product plus display/analysis representations
    -> independent validation
    -> optional Bonsai import
```

Capture, IFC serialization, validation, and import remain independent. The
capture phase is read-only and must not explode, alter, or save the Rhino
document.

## Product Boundary

A top-level Rhino document object is one source occurrence by default. A
top-level block instance remains one logical IFC product even when its block
definition contains nested blocks, meshes, Breps, or Extrusions.

Nested members create additional IFC products only when they carry explicit
product-boundary evidence. Geometry-role evidence such as `GEOMETRY`,
`GEOMATRY`, `BODYPROXY`, `preview`, or `proxy` never creates another product.
It only selects a representation branch owned by the top-level occurrence.

Ordinary ungrouped top-level objects remain separate occurrences. Full export
retains them as authored products or untyped proxies; it does not guess that
nearby components form one product.

## Transform Contract

Recursive traversal carries an accumulated Rhino transform from the top-level
occurrence to every leaf geometry item. Nested transforms are composed in Rhino
API order and applied exactly once before serialization.

The capture output uses world-coordinate vertices. The IFC exporter may then
subtract one local origin and create one corresponding `IfcLocalPlacement`.
No block transform may be applied again after world vertices have been
captured.

The implementation must support:

- translation and rotation;
- uniform and non-uniform scale;
- mirrored transforms;
- nested block instances;
- VisualARQ instance definitions whose scale is encoded in the instance
  transform.

When a transform reverses handedness, face winding is reversed so exported
surface normals retain their outward orientation.

For each captured top-level occurrence, the merged world geometry bounding box
must match Rhino's own world bounding box within a documented model-unit
tolerance. The Rhino bounding box is the acceptance ground truth; hand-written
matrix assumptions are not.

## Representation Branches

The capture record contains separate representation branches:

- `display`: visible authored geometry;
- `analysis`: hidden geometry substitutes such as `MassPatch` or `BODYPROXY`;
- `unclassified`: geometry whose role has no explicit evidence.

Role evidence is read in this order:

1. explicit `OM_GeometryRole` or `OM_AnalysisRole` property;
2. exact configured layer role;
3. configured block-definition suffix alias.

The current Rhino fixture requires migration aliases for `GEOMETRY`, the
existing misspelling `GEOMATRY`, and `BODYPROXY`, plus the authored layers
`funicture::geometry` and `funicture::proxy`. These aliases belong in a
configuration object, not scattered string tests.

Display geometry becomes the normal IFC body representation. Analysis geometry
becomes a second representation on the same IFC product and is marked with
project-owned factual metadata for analysis-only use. It must not appear as a
second furniture occurrence.

## Semantic Mapping

IFC classes come from explicit evidence, not arbitrary geometric or lexical
guessing.

The mapping order is:

1. authored `IfcEntity` or `OM.IfcEntity` on the occurrence;
2. a provider mapping for VisualARQ-owned definition kinds such as `*Door`,
   `*Column`, and `*Slab`;
3. an explicit project family rule supplied to the workflow;
4. `IfcBuildingElementProxy` with review or untyped status.

For the current fixture, the project mapping explicitly declares:

```text
CHAIR_* -> IfcFurniture
TABLE_* -> IfcFurniture
```

This is a user-approved naming convention, not a global hard-coded inference
rule. The capture preserves the top-level block definition id/name and
`OM_TargetFamily` so the mapping remains auditable. A missing rule does not
silently classify furniture.

## Source Record

Each normalized top-level occurrence records at least:

- stable Rhino object id;
- top-level block definition id and name when applicable;
- source layer and authored user text;
- complete instance path and transform evidence;
- selected IFC class, evidence source, and confidence;
- display vertices/faces;
- analysis vertices/faces when present;
- source and captured world bounding boxes;
- review reasons and analysis participation state.

The record must be JSON-compatible and remain usable without Rhino after
capture.

## Export Reporting

The exporter reports product counts using both exact classes and a furniture
family total. `IfcFurniture` and `IfcFurnishingElement` both contribute to the
furniture-family count. A report showing `furniture_count = 0` while furniture
occurrences were expected is a failed acceptance condition, not a successful
export.

The report also includes:

- source occurrence count;
- exported occurrence count;
- skipped geometry count;
- untyped and review counts;
- display and analysis representation counts;
- transform/bounding-box mismatch count;
- semantic evidence distribution.

## Failure Handling

An occurrence is not silently exported when recursive traversal fails, a block
cycle is detected, geometry cannot be meshed, or captured bounds disagree with
Rhino bounds. The occurrence receives a review record, and the run fails its
acceptance gate when the mismatch affects expected building or furniture
products.

Unknown decorative objects may still use the full-export proxy fallback when
their geometry is valid. Unknown analysis participation remains `unknown` and
does not make them layout-analysis members.

## Testing

Pure-Python tests cover transform composition, nested transforms, non-uniform
scale, mirrored winding, branch classification, product-boundary preservation,
and configured semantic mapping. Tests must fail against the old definition-
space behavior before production code is changed.

A Rhino MCP acceptance capture on port `15002` must then verify:

- the live document is not modified;
- all 56 chair and 37 table occurrences have distinct authored placements;
- each occurrence's captured world bounds match Rhino world bounds;
- one furniture block creates one IFC furniture occurrence;
- display and `BODYPROXY` geometry remain representations of that occurrence;
- no expected furniture occurrence is downgraded to an untyped proxy;
- mirrored instances retain correct normals.

The resulting IFC must pass independent IFC4 validation with no duplicate
GlobalIds. Final acceptance includes a Bonsai visual check showing the furniture
at its Rhino positions; import is performed only after export and validation
and is never implied by either.

## Non-Goals

This correction does not infer furniture groups, activity regions, paths,
trend, or layout scores. It does not generate new MassPatch geometry, repair
the Rhino model, or merge unrelated ungrouped source objects.
