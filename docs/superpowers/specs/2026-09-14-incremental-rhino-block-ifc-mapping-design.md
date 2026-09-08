# Incremental Rhino Block to IFC Mapping Design

Date: 2026-09-14
Status: Design specification; no implementation claim

## Purpose

Extend the existing BIM conversion skills so Rhino nested Blocks can describe
one complete logical BIM product with multiple representations. This is an
increment to the existing `bim-logical-object-mapping`,
`analysis-substitute-discovery`, `masspatch-generation`, and
`ifc-bim-conversion-workflow` skills. It is not a new parallel BIM system.

The workflow must combine automation, explicit user editing, and supervisor
judgment. Automation produces inspectable evidence and candidates; it must not
silently decide ambiguous product ownership or IFC meaning.

## Existing Contracts To Preserve

- A chair, table, or similar complete product is one logical object.
- Source components are not automatically separate furniture products.
- A repeated BIM type is distinct from its placed occurrences.
- `MassPatch` discovery and generation remain independent skills.
- IFC export, validation, import, and verification remain separate phases.
- User-authored semantic facts take priority over geometric fallbacks.
- `OM_*` properties are project-owned factual extensions; standardized `Pset_*`
  names are not reused for custom properties.

## Rhino Authoring Contract

The recommended authoring shape is:

```text
Root product Block instance
|-- display geometry Block instance       [required for visible products]
|-- analysis substitute Block instance    [optional, e.g. MassPatch]
|-- affordance representation             [optional]
`-- metadata carrier Block instance       [optional, empty geometry allowed]
```

The root Block represents one complete logical product occurrence. Its child
Blocks represent roles or representations, not additional furniture products.
Nested Blocks are traversed recursively until geometry or a declared metadata
carrier is reached.

An empty metadata carrier is allowed when a property scope must be separated
from geometry. It is not required for every scalar: properties that describe
the root product may be stored directly on the root Block instance. Geometry
roles must be explicit when more than one representation exists.

Block names are human-readable labels and fallback evidence only. They are not
the authoritative IFC mapping mechanism.

## Property Registry

The adapter recognizes a small, namespaced factual registry. Rhino UserText,
IFC property sets, or an equivalent adapter payload may carry these keys.

### Root product properties

```text
OM.Role = logical_product
OM.IfcEntity = IfcFurniture
OM.TypeKey = chair.standard
OM.InstanceId = chair_001
OM.DisplayName = Chair
```

### Representation properties

```text
OM.RepresentationRole = display_geometry | analysis_substitute | affordance
OM.SubstituteKind = MassPatch
OM.VisibilityPolicy = visible | analysis_only
OM.SourceInstanceId = chair_001
```

### Optional traceability properties

```text
OM.SourceDefinitionId = ...
OM.SourceInstancePath = ...
OM.AuthoringStatus = authored | generated | reviewed
OM.ReviewStatus = pending | confirmed | rejected
```

Values are factual or procedural provenance. They must not contain perceptual
weights, fitted model coefficients, or final scores.

The implementation must maintain one registry mapping these keys to normalized
fields. It must not scatter string comparisons across exporters.

## IFC Mapping Rules

The exporter consumes the normalized logical-object report produced by the
existing mapping skill.

| Normalized evidence | IFC result |
| --- | --- |
| Root product with `IfcFurniture` role | One `IfcFurniture` occurrence |
| Equal `TypeKey` and compatible type evidence | One `IfcFurnitureType` family |
| Placed root occurrences | `IfcRelDefinesByType` links to the family |
| Display geometry child | Main occurrence representation |
| Authored affordance child | Explicit authored affordance input, normally `IfcSpatialZone` in the existing IFC4 contract |
| MassPatch child | Analysis substitute input/sidecar, not silently a second furniture product |
| Project-owned factual attributes | `OM_*` property set, not `Pset_OM_*` |

Representation reuse is a separate decision from type sameness. A shared
`IfcRepresentationMap`/`IfcMappedItem` is permitted only when the normalized
report confirms compatible reusable geometry.

The exporter must preserve the source instance ID and nested Block path in its
audit output even when the IFC file contains only one furniture occurrence.

## Human and Automation Boundary

### Automation may

- traverse Block definitions and instances;
- collect child geometry, transforms, names, UserText, and block paths;
- propose complete logical products and repeated type families;
- discover explicitly bound MassPatch children;
- produce a mapping report with evidence and confidence;
- reject contradictory or duplicate bindings as ambiguous;
- export only after the mapping report is accepted.

### Supervisor judgment is required when

- a root Block may be only a part rather than a complete product;
- nested Blocks contain multiple plausible product roots;
- a child has no role property and its geometry could be display or analysis geometry;
- repeated instances have similar but not identical geometry;
- a name conflicts with geometry or authored properties;
- a MassPatch is present but its source instance cannot be established.

The report must show the candidate root, source component IDs, block path,
proposed role, evidence, and confidence. The supervisor may confirm, edit, or
reject the proposal. A script must never resolve these cases by silently
flattening all nested Blocks or exporting every leaf geometry.

### Manual operation is supported for

- adding or correcting UserText;
- renaming a meaningful root Block or type definition;
- selecting the logical product root;
- assigning a representation role;
- confirming a type family;
- explicitly binding a MassPatch to a source instance.

Manual edits are fed back into the same normalized report; they do not create a
second export path.

## Failure and Safety Rules

- Missing role evidence is `unknown`, not permission to invent an IFC class.
- Contradictory root/child evidence is `ambiguous` and blocks automatic export.
- A nested Block is not automatically a product boundary.
- A visible geometry child and an analysis child must not be exported as two
  furniture occurrences.
- Validation failure or unavailable IFC validation blocks import as required by
  the existing conversion workflow.
- Source Rhino documents remain read-only unless the user explicitly requests
  a preprocessing edit.

## Acceptance Examples

For `exampleChair`:

```text
exampleChair
|-- exampleChair-geometry   -> one display representation, 11 Mesh members
`-- exampleChair-MassPatch  -> one analysis representation, 4 Brep members
```

The normalized result must contain one logical chair occurrence, one display
representation, and one MassPatch representation. It must not contain 15
furniture occurrences or 2 furniture occurrences.

The acceptance test must cover:

1. repeated `exampleChair` instances sharing one type family;
2. nested geometry and MassPatch Blocks;
3. an ambiguous unlabelled child requiring supervisor confirmation;
4. a manually supplied role property overriding a weak name heuristic;
5. exporter output retaining source IDs and representation roles;
6. validation remaining independent from import.

## References

- Existing `skills/bim-logical-object-mapping/SKILL.md`.
- Existing `skills/analysis-substitute-discovery/SKILL.md`.
- Existing `skills/masspatch-generation/SKILL.md`.
- Existing `skills/ifc-bim-conversion-workflow/SKILL.md`.
- buildingSMART IFC lexical documentation: https://ifc43-docs.standards.buildingsmart.org/
- IfcOpenShell validation API: https://docs.ifcopenshell.org/autoapi/ifcopenshell/validate/index.html
