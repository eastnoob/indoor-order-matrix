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
`OM_*` properties provide project-specific provenance. A sidecar must never be
described as the same furniture product's second representation.

Export consumes an explicit substitute report, remains valid without one, and
does not imply IFC validation or Bonsai import. Run the independent validation
skill after writing the file.

## Full-export fallback

Objects with an authored supported IFC class keep that class. Objects without a
valid authored class are exported as `IfcBuildingElementProxy` with
`SemanticStatus=untyped` and `AnalysisParticipation=unknown`. Their source id,
name, layer, geometry kind, and provenance remain attached as `OM_Source`
facts. They stay in the IFC for completeness but are not layout-analysis
members by default. Unsupported or conflicting authored labels use the same
proxy fallback with `SemanticStatus=review`.

The neutral source field remains `analysis_participation`; the IFC property is
serialized as `AnalysisParticipation`.

Full export is separate from validation and Bonsai import. A proxy fallback is
not evidence that the object is a wall, chair, or other specific BIM class.

## Commands

```powershell
pixi run python test/bim/export_rhino_source_ifc.py source.json output.ifc --substitutes substitutes.json --substitute-mode representation
pixi run python test/bim/export_rhino_source_ifc.py source.json output.ifc --substitutes substitutes.json --substitute-mode sidecar
```
