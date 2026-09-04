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

## Source decision

| Source | First choice | Fallback | BIM caution |
| --- | --- | --- | --- |
| Rhino | existing project adapter | native IFC exporter, then IfcOpenShell | geometry and layer names do not establish BIM semantics |
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

Read only the reference needed for the current phase:

- [IFC standards and validation](references/ifc-standard-links.md)
- [Bonsai import workflow](references/bonsai-workflow-links.md)
- [Software preflight](references/software-preflight.md)

Live MCP verification is session-specific. When available, use only the documented
read-only query path and record fresh evidence; do not infer live success from local reports.
