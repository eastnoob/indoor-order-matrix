---
name: ifc-bim-conversion-workflow
description: Use when the agent converts Rhino, Blender, or other 3D model content into IFC/BIM, validates IFC legality, or imports IFC into Bonsai or another BIM application.
---

# IFC/BIM Conversion Workflow

Use this skill as a small orchestrator around independently actionable and
independently reportable phases. The deterministic IFC file phases, inspection
and validation, have standalone scripts. Preprocessing, export, and import are
adapter or user-controlled phases; this skill does not itself invoke an
importer. Every phase remains independently runnable. A phase never silently invokes the next phase. Source models are read-only by default; preprocessing requires an explicit user request.

## Optional capability routing

Select only the capability the request needs:

| Need | Skill |
| --- | --- |
| Read Rhino/VisualARQ authored source facts | `visualarq-source-adapter` |
| Map complete logical products and repeated types | `bim-logical-object-mapping` |
| Find an existing analysis substitute | `analysis-substitute-discovery` |
| Create a new MassPatch substitute | `masspatch-generation` |
| Write an IFC file | `ifc-export` |
| Check IFC legality and facts | `ifc-validation` |
| Change a Bonsai scene | `bonsai-import` |
| Prove the active Bonsai mapping | `bonsai-verification` |

Discovery never calls generation. Export consumes an explicitly supplied
substitute report and remains valid with source products only. Import is never
implied by export or validation.

The default export policy is full export: every source object with usable
geometry is written once. Authored IFC classes are preserved; objects without
valid authored semantics become `IfcBuildingElementProxy` with
`analysis_participation=unknown`. This preserves visual completeness without
guessing a wall, chair, or other specific class. Untyped proxies are excluded
from layout analysis unless an explicit downstream rule includes them.

## Source decision

| Source | First choice | Fallback | BIM caution |
| --- | --- | --- | --- |
| Rhino | `visualarq-source-adapter`, then existing project adapter | native IFC exporter, then IfcOpenShell | geometry and layer names do not establish BIM semantics |
| Blender | existing project adapter | native IFC exporter, then IfcOpenShell | use Blender+Bonsai only for an IFC project import |
| Other | existing project adapter | native exporter, then IfcOpenShell | require explicit provenance and semantic evidence |

## Output contract

The output directory is optional. When omitted, use
`<current project>/outputs/<model-name>/` and keep IFC, inspection, validation,
mapping, and log artifacts together. Do not overwrite existing results; create
a distinct run directory or ask before replacing them. The output directory
and import target are separate decisions: writing an IFC never implies import.

## Phases

1. **Environment preflight**: detect Python/Pixi, optional IfcOpenShell,
   source and target applications, native exporters, Bonsai, and available
   MCP endpoints. Missing tools return `not_available` with an action.
2. **Model preflight**: inspect units, transforms, identity, roles, groups,
   types, materials, geometry validity, provenance, and coordinates. Geometry
   or names alone do not establish BIM semantics.
3. **Export**: as an adapter phase, discover and reuse an existing project
   adapter first, then a native exporter, then an IfcOpenShell adapter; generate
   a minimal exporter only when none exists. In this repository inspect and
   reuse `test/bim/convert_rhino_fixture_to_ifc.py`; do not copy it into this
   skill.
   **REQUIRED SUB-SKILL:** Use `bim-logical-object-mapping` before selecting an
   exporter. Consume its `logical_objects`, `type_families`, `occurrences`,
   `confidence`, and `geometry_reuse` report; do not duplicate its part,
   type-family, or occurrence judgment here.
   Before export, normalize source components into logical products. A chair
   or table is normally one logical furniture object; legs, seats, backs, and
   other parts are components unless the user explicitly requests part-level
   IFC objects. Do not use a global coordinate quadrant as the sole ownership
   rule. Prefer explicit grouping, blocks/instances, parent-child relations,
   and names; use spatial/geometry inference only when its evidence is coherent.
   For Rhino nested Blocks, use the existing project adapter
   `features.rhino_block_mapping.normalize_rhino_blocks()` before this phase
   consumes the report. It is a proposal-and-evidence step, not an automatic
   semantic authority. Show `manual_review` records to the supervisor and
   block automatic export until unresolved roots, representation roles, or
   substitute bindings are confirmed.
4. **Inspect and validate**: run inspection and validation independently.
   Validation failure blocks import. Validation failure or not_available blocks
   the import step before any mutation adapter can be called, even when geometry
   looks correct.
5. **Import decision**: show the validation report and ask, with no default:
   `Import mode: manual / automatic` and `Target: Rhino / Blender+Bonsai / other`.
   Manual means exact instructions only. Automatic requires explicit
    explicit confirmation immediately before changing, clearing, or saving the target.
6. **Import**: this is an adapter or user-controlled phase. The skill does not
   itself invoke an importer. Manual mode uses the target application's
   official IFC route as exact instructions; automatic mode may call a
   separately selected adapter only after confirmation. For Bonsai, load IFC
   as an IFC project; geometry-only is not BIM and must not be used as evidence
   of imported semantics.
7. **Post-import verification**: read the active `IfcStore`, schema, expected
   entity counts, relations, geometry, and object mappings. Require positive
   non-zero integer `BIMObjectProperties.ifc_definition_id` values.
   Names such as
   `IfcFurniture/chair_01` are labels, not proof. Never import, delete, clear,
   or save during verification.

## Commands

```powershell
pixi run python skills/ifc-bim-conversion-workflow/scripts/inspect_ifc.py <file.ifc> --json
pixi run python skills/ifc-bim-conversion-workflow/scripts/validate_ifc.py <file.ifc> --express-rules
pixi run python skills/ifc-bim-conversion-workflow/scripts/verify_bonsai_mapping.py
pixi run python skills/ifc-bim-conversion-workflow/scripts/verify_bonsai_mapping.py --snapshot <snapshot.json>
```

Use the scripts as separate commands. A missing optional dependency keeps
validation `not_available` and import blocked; do not downgrade that status.
Each phase may return only `passed`, `failed`, `blocked`, `not_available`, or
`not_run`, with a source path, tool version when known, and actionable reason.

## Logical furniture safeguard

The smallest useful analysis unit is normally the complete logical furniture
item, not an individual mesh or manufactured part. Preserve the component-to-product
mapping in the export report. Apply this confidence policy without over-blocking:

Treat source memberships as an object-group relationship graph, not a semantic
tree: an object may belong to multiple groups, and nested groups may be only
organizational. A Block/Instance is strong evidence, not an absolute semantic
boundary; verify that the instance is a complete functional product rather than
a reusable chair leg, seat, or back. Group names are labels, not identity. Keep
source object IDs and group IDs, plus the block-instance path when available,
as the stable audit keys.

| Evidence | Action |
| --- | --- |
| Explicit user boundary rule | Use directly |
| Block/instance or explicit parent-child relation | Use as strong evidence, then check functional completeness |
| Coherent geometry and spatial clustering with no obvious fragment-only result | Auto-normalize and report the evidence |
| Ambiguous ownership, isolated parts, or a visibly incomplete candidate | Pause and ask the user to confirm |

Before asking the user, show the candidate logical product, its source object IDs,
the evidence used, and confidence (`high`, `medium`, or `low`). Do not reject an
otherwise usable model merely because it has multiple parts, unusual orientation,
shared layers, or components crossing the world origin. Do reject a result that
silently treats parts as separate furniture products.

Recommended source preparation, when available: group all parts of one furniture
item, use a Block/Instance or parent-child hierarchy, and give logical products
stable names such as `Chair_01` or `Table_01`. This is assistance, not a hard
requirement.

An authored furniture group is a separate relationship, not a furniture type
or a physical aggregate. Use exactly `OM.Role = furniture_group` on an outer
Rhino Block. A value on its Block Definition is inherited as a default; a
value on an occurrence overrides it. The exporter writes one geometry-free
`IfcGroup` with `ObjectType=furniture_group` and one `IfcRelAssignsToGroup`
relation to the nested furniture occurrences. It does not infer furniture
groups from names, layers, ordinary Rhino groups, proximity, or geometry.
Unmarked Blocks keep their normal export behavior.

For a role-bearing nested Block, export one root logical product occurrence.
`display_geometry` supplies its visible representation;
`analysis_substitute` such as `MassPatch` remains analysis evidence and must
not become a second furniture occurrence. When the target consumer supports
multiple shape representations, export it as a second representation of the
same product: `Body` for display geometry and project-convention `Analysis`
for the MassPatch. `Analysis` is not an IFC-native MassPatch type and does not
automatically hide the representation in Bonsai. A separate
`IfcBuildingElementProxy` sidecar is an explicit compatibility fallback, and
must be reported as a separate product linked to the source, never described
as the same product's second IFC representation. Use `OM_*` custom property
sets for factual project extensions, never `Pset_OM_*`. Block names alone must
not determine an IFC entity or property set. The minimum role registry includes
`OM.Role`, `OM.TypeKey`, `OM.InstanceId`, and `OM.RepresentationRole`.

For multi-representation export, the adapter must preserve one logical product
with one `IfcProductDefinitionShape` containing `Body` and `Analysis`; this is
the same product's second shape representation, not a new occurrence. Bonsai
visibility is an adapter responsibility: select `Body` as the default visible
representation and retain `Analysis` for analysis or an explicit inspection
view. Do not claim that an IFC role name or `OM.VisibilityPolicy` alone
guarantees hidden analysis geometry.

The source adapter must preserve nested analysis branches instead of merging
them into display geometry. A source record may carry an
`analysis_substitutes` list for embedded MassPatch/BODYPROXY geometry; the
exporter attaches each record to the same logical product's `Analysis`
representation. The normal result is one `IfcFurniture` with `Body` and
`Analysis`, not an additional `IfcBuildingElementProxy` furniture-like
occurrence. The `sidecar` mode remains available only when a consumer cannot
retain multiple representations.

Source-to-IFC traceability is kept in the external export report rather than
as a mandatory `OM_Source` property set on every IFC product.

Read only the reference needed for the current phase:

- [IFC standards and validation](references/ifc-standard-links.md)
- [Bonsai import workflow](references/bonsai-workflow-links.md)
- [Software preflight](references/software-preflight.md)

Live MCP verification is session-specific. When available, use only the documented
read-only query path and record fresh evidence; do not infer live success from local reports.
