---
name: ifc-export
description: Use when normalized BIM products and optional analysis substitutes must be serialized to an IFC file.
---

# IFC Export

This skill routes normalized source records to the existing project exporter;
it does not duplicate IFC serialization and does not generate missing
substitutes.

## Route

Use `test/bim/export_rhino_source_ifc.py` for the current Rhino-source
workflow. Pass an explicit `substitute_mode`:

- `representation` (default): keep one logical product and attach `Body` plus
  project-convention `Analysis` to its one `IfcProductDefinitionShape`.
- `sidecar`: create a separate `IfcBuildingElementProxy` only for consumers
  that cannot preserve multiple representations.

`Body` and `Analysis` are representation roles, not IFC entity types.
`OM_*` properties provide project-specific provenance. A sidecar must never be
described as the same furniture product's second representation.

Export consumes an explicit substitute report, remains valid without one, and
does not imply IFC validation or Bonsai import. Run the independent validation
skill after writing the file.

## Commands

```powershell
pixi run python test/bim/export_rhino_source_ifc.py source.json output.ifc --substitutes substitutes.json --substitute-mode representation
pixi run python test/bim/export_rhino_source_ifc.py source.json output.ifc --substitutes substitutes.json --substitute-mode sidecar
```
