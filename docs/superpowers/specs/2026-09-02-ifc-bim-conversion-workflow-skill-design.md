# IFC/BIM Conversion Workflow Skill

## Status

Design approved for implementation planning on 2026-09-02.

## Purpose

Create a reusable workflow skill for converting 3D software content into
validated IFC/BIM content and optionally importing it into a target BIM tool.
The skill is an orchestrator. It must not duplicate the analysis matrix,
Rhino exporter, Bonsai importer, or IFC validator.

## Non-Negotiable Boundaries

1. Each phase is independently actionable and independently reportable:
   environment, preprocessing, export, validation, import, and post-import
   verification. Deterministic IFC file phases have standalone scripts.
   Preprocessing, export, and import are adapter or user-controlled phases.
2. A phase never silently invokes the next phase.
3. IFC validation failure or `not_available` blocks the import step before any
   mutation adapter can be called.
4. Import is never automatic by default. The agent must ask the user to choose
   `manual` or `automatic` import after presenting the validation report.
5. `manual` import produces exact user instructions and does not modify the
   target application.
6. `automatic` import requires explicit user confirmation immediately before
   modifying the target application.
7. Geometry-only data is never labelled as BIM semantics.
8. Existing project adapters and exporters are discovered and reused before a
   new script is written.
9. The workflow is read-only with respect to source models unless the user
   explicitly requests preprocessing changes.
10. This skill does not itself invoke an importer; import execution belongs to
    a separately selected adapter or to the user.

## Skill Package

```text
ifc-bim-conversion-workflow/
  SKILL.md
  references/ifc-standard-links.md
  references/bonsai-workflow-links.md
  references/software-preflight.md
  scripts/validate_ifc.py
  scripts/inspect_ifc.py
  scripts/verify_bonsai_mapping.py
  tests/pressure-scenarios.md
```

The reusable skill lives in the user's Codex skills directory. Project-specific
exporters remain in their project. For this repository, the existing
`test/bim/convert_rhino_fixture_to_ifc.py` is an adapter candidate and must be
called or referenced, not copied into the skill.

## Independent Phase Contracts

### 1. Environment preflight

Detect the source application, target application, Python runtime, Pixi or
other environment manager, `ifcopenshell`, IFC exporters, Bonsai, and available
MCP endpoints. Missing tools produce an actionable report and stop only the
dependent phase.

### 2. Model preflight

Inspect units, transforms, object identity, semantic roles, groups, types,
materials, geometry validity, source IDs, and coordinate conventions. Provide
minimal preparation advice for Rhino, Blender, or another 3D application.
The skill must not infer BIM classes from object names alone.

### 3. Export

Select an existing exporter by explicit precedence: project adapter, native
application exporter, IfcOpenShell-based adapter, then a newly generated
minimal script. The exporter must preserve provenance and use native IFC
entities where available. Export is an adapter phase and is independently
actionable and reportable.

### 4. IFC inspection and validation

`inspect_ifc.py` reports schema, entity counts, GUID uniqueness, type
assignments, spatial containment, group membership, representations, units,
and provenance. `validate_ifc.py` runs IfcOpenShell validation, including
EXPRESS rules where available. Validation results are machine-readable and
must include the file path and validator version.

### 5. Import decision gate

After validation, show a compact report and ask:

```text
Import mode: manual / automatic
Target: Rhino / Blender+Bonsai / other
```

No default is selected. If the user chooses `manual`, stop after exact import
instructions. If the user chooses `automatic`, request confirmation again if
the operation will clear, alter, or save the current model.

### 6. Import

Import is an adapter or user-controlled phase. This skill does not itself
invoke an importer. Manual mode returns exact instructions; automatic mode may
call a separately selected adapter only after the required confirmation. For
Bonsai, use its IFC project-loading operation with IFC data enabled, never
geometry-only mode. Import must not contain analysis-matrix logic.

### 7. Post-import verification

Verify active IFC state, schema, entity counts, object-to-entity mappings,
group/type relations, and geometry presence. A Blender object named
`IfcFurniture/...` is insufficient evidence; a valid non-zero IFC definition
mapping and active Bonsai IFC store are required.

## Failure States

Every phase returns one of `passed`, `failed`, `blocked`, `not_available`, or
`not_run`, with source paths, tool versions, and a short reason. A failed
validation never becomes a successful import by fallback. A missing material,
semantic class, or geometry fact is reported as unavailable rather than
silently fabricated.

## Verification Strategy

The skill must be pressure-tested before deployment using scenarios where an
agent is tempted to:

- import before validation;
- treat a named Blender mesh as a BIM element;
- use geometry-only Bonsai import;
- modify the current scene without confirmation;
- write a new exporter while an existing adapter is available;
- continue after missing `ifcopenshell`;
- conflate valid IFC syntax with valid BIM mappings.

Tests follow `superpowers:writing-skills` RED/GREEN/REFACTOR: run baseline
scenarios without the skill, record violations, write the minimal skill, then
repeat the scenarios and close remaining loopholes.

## Documentation Sources

- buildingSMART IFC lexical documentation: `https://ifc43-docs.standards.buildingsmart.org/`
- IfcOpenShell validation API: `https://docs.ifcopenshell.org/autoapi/ifcopenshell/validate/index.html`
- Bonsai documentation: `https://docs.bonsaibim.org/`
- Bonsai general project/import reference: `https://docs.bonsaibim.org/reference/general/topbar.html`
- Blender MCP Server documentation: `https://www.blender.org/lab/mcp-server/`

## Acceptance Criteria

- Every phase is independently actionable and independently reportable.
- Inspection and validation have standalone scripts.
- Preprocessing, export, and import are adapter or user-controlled phases.
- The skill does not itself invoke an importer.
- No phase silently calls another phase.
- Validation failure or `not_available` blocks the import step before any
  mutation adapter can be called.
- Manual import never changes the target application.
- Automatic import occurs only after explicit user confirmation.
- A valid IFC imported by Bonsai has an active `IfcStore` and non-zero object
  mappings.
- Existing project exporters are reused and remain outside the generic skill.
- The skill passes its baseline pressure tests after the RED/GREEN/REFACTOR
  cycle.
