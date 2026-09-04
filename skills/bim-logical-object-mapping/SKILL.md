---
name: bim-logical-object-mapping
description: Use when a 3D model must be normalized into complete logical products, repeated BIM type families, and placed occurrences before IFC export.
---

# BIM Logical Object Mapping

## Purpose

Separate source components from complete functional products, then determine
which products share one BIM type and which are separate occurrences. This
skill is an evidence-producing boundary between model inspection and IFC
export. It does not export, validate, import, or score a layout.

## Required Output

Return a JSON report with:

- `logical_objects`: complete products with source component IDs and evidence;
- `type_families`: type-defining families and their member product IDs;
- `occurrences`: one record per placed product with independent placement facts;
- `ambiguous_candidates`: candidates that must not be silently exported;
- `confidence` on every decision;
- `geometry_reuse`: `shared_candidate`, `not_shared`, or `unknown`;
- `display_name`: a human-readable occurrence label, separate from source IDs.

The three levels are distinct:

```text
source components -> logical_object -> type_family + occurrence
```

## Meaning Of "Same"

Products share one type family only when all type-defining evidence agrees:

1. compatible functional role or authored semantic class;
2. compatible component/part-role composition;
3. canonical geometry signature equal within the declared tolerance;
4. equal type-level attributes, such as type material or manufacturer data.

Translation, rotation, and occurrence placement do not affect sameness.
Occurrence-level attributes do not split a type unless the source declares them
type-defining. A functional match with different canonical geometry is not a
shared-geometry candidate.

Names are presentation and traceability fields, not identity evidence. Prefer
an authored object or definition name when it is meaningful. Generated labels
such as `rhino-group-0`, numeric group labels, `Object001`, and UUID-like values are
source evidence only; infer a semantic name such as `Chair` or `Table` and add
a stable occurrence suffix when needed. Keep the original source ID in its own
field.

## Decision Rules

1. Prefer explicit BIM types, blocks/instances, parent-child relations, and
   authored group membership.
2. Treat group names, layer names, and identical mesh names as evidence only.
3. A complete chair, table, or similar product is one `logical_object`; legs,
   seats, backs, and fasteners are components unless explicitly authored as
   products.
4. Ignore source position when forming a type signature.
5. Do not use world quadrants as an ownership rule.
6. Nested or overlapping groups are a relationship graph. If a container is
   only the union of child groups, report it as organizational evidence rather
   than creating a duplicate product.
7. An explicitly incomplete, fragment-only, or contradictory candidate is
   `ambiguous`; preserve its source IDs and reason.
8. Missing evidence is `unknown`, not permission to fabricate a type.

## IFC Handoff

For each type family, the exporter may create one `IfcFurnitureType` (or the
appropriate IFC type) and one occurrence entity per `logical_object`, linked by
`IfcRelDefinesByType`. Only a family with `shared_candidate` geometry should
use `IfcRepresentationMap` and `IfcMappedItem`. Type identity and geometry
reuse are separate decisions.

## Automation

Use `scripts/normalize_logical_objects.py` with a JSON source containing
`groups` and `components` (or compatible `objects` records). The script is
stdlib-only and emits the required normalized JSON plus merged geometry when
source meshes are present.

The conversion workflow must run this skill before selecting an IFC exporter.
The exporter consumes the normalized report; export, validation, and import
remain independent phases.

## Common Mistakes

- exporting every mesh as furniture;
- grouping by generated names or world quadrants;
- merging all products of one broad semantic kind despite different type
  geometry;
- claiming shared geometry merely because two objects are both chairs;
- treating one `IfcFurniture` containing two placements as two occurrences.
