---
name: ifc-export
description: Use when normalized BIM products and optional analysis substitutes must be serialized to an IFC file.
---

# IFC Export

This skill routes normalized source records to the existing project exporter;
it does not duplicate IFC serialization and does not generate missing
substitutes. **full export is the default:** every source object with usable
geometry is emitted once. Full export does not mean semantic guessing.

For Rhino/VisualARQ input, obtain the neutral source payload with
`visualarq-source-adapter` before logical-object mapping. This exporter does
not read Rhino objects directly.

## Route

Use `test/bim/export_rhino_source_ifc.py` for the current Rhino-source
workflow. Pass an explicit `substitute_mode`:

- `representation` (default): keep one logical product and attach `Body` plus
  project-convention `Analysis` to its one `IfcProductDefinitionShape`.
- `sidecar`: create a separate `IfcBuildingElementProxy` only for consumers
  that cannot preserve multiple representations.

`Body` and `Analysis` are representation roles, not IFC entity types.
Project-specific analysis properties are limited to facts needed by an
analysis representation. Source provenance belongs in the external export
report, not in a custom property set on every IFC product. A sidecar must
never be described as the same furniture product's second representation.

Export consumes an explicit substitute report, remains valid without one, and
does not imply IFC validation or Bonsai import. Run the independent validation
skill after writing the file.

When a neutral source record contains an embedded `analysis_substitutes` list
(for example, a nested Rhino `BODYPROXY` branch), route those meshes to the
same product's `Analysis` representation. Do not flatten them into `Body` and
do not create a second product occurrence. External substitute reports and
embedded substitute records use the same representation policy.

## Full-export fallback

Objects with an authored supported IFC class keep that class. Objects without a
valid authored class are exported as `IfcBuildingElementProxy` with
`SemanticStatus=untyped` and `AnalysisParticipation=unknown`. They stay in the
IFC for completeness but are not layout-analysis members by default.
The adjacent `.export.json` report contains the source-to-IFC mapping needed
for traceability. Unsupported or conflicting authored labels use the same
proxy fallback with `SemanticStatus=review`.

The exporter must not create an `OM_Source` property set. IFC-native identity
(`GlobalId`, `Name`, `ObjectType`, and `Tag` when available) remains in the
model; source ids, provider details, and export status remain in `source_map`
inside the external report.

The neutral source field remains `analysis_participation`; the IFC property is
serialized as `AnalysisParticipation`.

Full export is separate from validation and Bonsai import. A proxy fallback is
not evidence that the object is a wall, chair, or other specific BIM class.

## Authored furniture groups

Use exactly `OM.Role = furniture_group` on an outer Rhino Block container to
export an authored furniture group. The marker may live on the reusable Block Definition
as a default; a Block Instance value overrides that default. The
outer container becomes one geometry-free `IfcGroup` with
`ObjectType=furniture_group`; its already-recognized nested furniture becomes
the members of `IfcRelAssignsToGroup` and retains its own `Body` and optional
`Analysis` representations.

The exporter does not infer furniture groups from names, layers, ordinary
Rhino groups, proximity, or geometry. An unmarked Block remains on the normal
full-export path, and non-furniture children of a marked container never
become furniture members merely through nesting.

## VisualARQ grids

Rhino extraction may add a `visualarq_guides` list to the normalized source
JSON. Each record preserves the Guide instance id, visible axis label,
`*Guide{...}` definition name, and serialized curve points. The exporter routes
these records through `adapters/rhino_visualarq_grid.py`, ignores decorative
label/end-cap geometry, groups axes by their relative directions, and writes
one native `IfcGrid` with `IfcGridAxis` members.

Do not export Guides as furniture, generic proxies, or `OM_*` replacements for
IFC grid semantics. Validate the result and confirm that the consumer reports
the expected `IfcGrid` and axis count before import.

## Commands

```powershell
pixi run python test/bim/export_rhino_source_ifc.py source.json output.ifc --substitutes substitutes.json --substitute-mode representation
pixi run python test/bim/export_rhino_source_ifc.py source.json output.ifc --substitutes substitutes.json --substitute-mode sidecar
```
