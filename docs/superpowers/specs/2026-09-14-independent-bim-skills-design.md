# Independent BIM Skills Design

**Date:** 2026-09-14

## Goal

Extend the current BIM workflow into a small set of independently runnable
skills without making MassPatch generation, discovery, IFC export, validation,
or Bonsai import a mandatory fixed pipeline.

## Design Decision

Keep `ifc-bim-conversion-workflow` as an optional coordinator, never a required
pipeline stage. It selects and
orders only the capabilities required by the current request. The coordinator
must not duplicate the implementation of any capability.

The repository keeps these independently usable skill boundaries:

```text
bim-logical-object-mapping
analysis-substitute-discovery
masspatch-generation
ifc-export
ifc-validation
bonsai-import
bonsai-verification
ifc-bim-conversion-workflow  # optional coordinator
```

The existing `bim-logical-object-mapping` and
`ifc-bim-conversion-workflow` skills remain compatible entry points. New
boundaries are added only where the current responsibilities are genuinely
different.

## Responsibility Boundaries

### `bim-logical-object-mapping`

Maps source components and groups to complete logical products, type families,
and occurrences. It does not generate substitutes, export IFC, validate IFC,
import into Bonsai, or score a layout.

### `masspatch-generation`

Generates analysis-oriented `MassPatch` geometry from source geometry when
explicitly requested. It is an upstream producer and does not mutate the
visible source model or perform IFC export.

### `analysis-substitute-discovery`

Reads already-authored or already-generated analysis substitutes from a source
model. It does not create missing substitutes. It returns discovered records,
source references, role evidence, visibility metadata, and missing or
ambiguous bindings.

The default result for an absent substitute is `not_found`. It does not trigger
automatic generation and does not make the source model invalid.

### `ifc-export`

Consumes normalized logical products and, when available, discovered
substitute records. It exports authoritative BIM products and, when supported,
places an analysis substitute in the same product's second shape representation
(`Body` plus project-convention `Analysis`). A separate proxy is only a
compatibility fallback. It does not generate substitutes, infer missing
semantic products, import the result, or score a layout.

### `ifc-validation`

Inspects and validates an IFC file read-only. It reports parser status,
schema, entity counts, identifiers, relationships, units, representations,
errors, and warnings. Validation failure blocks only workflows that require
validated IFC, not unrelated source inspection or substitute generation.

### `bonsai-import`

Imports a validated IFC into Blender+Bonsai only after the user chooses the
target and import mode. It owns mutation and import operations, not IFC
generation or analysis.

### `bonsai-verification`

Read-only verification of the active Bonsai `IfcStore`, IFC schema, entity
mappings, relationships, and non-zero `ifc_definition_id` values. It never
imports, clears, deletes, or saves a Blender scene.

### `ifc-bim-conversion-workflow`

Provides routing, phase status, prerequisite checks, and user-facing
coordination. It may call the independent skills, but it must preserve their
standalone behavior and must not turn optional capabilities into mandatory
steps.

## Shared Data Contracts

Each skill communicates through JSON-safe records or project-neutral Python
data structures. At minimum:

```text
LogicalObjectReport
  logical_objects
  type_families
  occurrences
  ambiguous_candidates
  confidence
  geometry_reuse

SubstituteDiscoveryReport
  substitutes
  source_bindings
  missing_sources
  ambiguous_candidates
  confidence
  provenance

IFCExportReport
  target
  schema
  source_object_count
  proxy_object_count
  bindings
  warnings
  import_status
```

Every substitute binding must preserve:

```text
source_global_id
substitute_id
substitute_kind = MassPatch
analysis_role = analysis_geometry_substitute
visibility_policy = analysis_only
provenance
confidence
```

Absence, uncertainty, and validation failure remain explicit statuses. A
consumer must not fabricate a substitute, semantic object, or successful
import from a missing record.

## MassPatch IFC Policy

When an IFC export explicitly includes discovered MassPatch records:

- the visible logical product remains the authoritative `IfcFurniture` or
  other appropriate IFC product;
- the preferred form is one `IfcProductDefinitionShape` on that product with
  `Body` for display geometry and project-convention `Analysis` for MassPatch;
- this is the same product's second shape representation, not a second
  furniture occurrence;
- an independent `IfcBuildingElementProxy` with `OM_AnalysisProxy` is only a
  compatibility fallback for consumers that cannot preserve multiple
  representations;
- in fallback mode, `OM_SourceGlobalId` links the separate proxy to the source;
- source-to-proxy linkage is metadata and indexed by the analyzer, not a
  physical aggregation relationship;
- representation visibility is advisory in IFC; the Bonsai adapter must make
  `Body` the default visible representation and keep `Analysis` for analysis
  or explicit inspection.

Exporting a source-only IFC remains valid when no substitute is present.

## Non-Goals

This change does not:

- require every model to contain a MassPatch;
- automatically generate a missing MassPatch during IFC export;
- make IFC export imply Bonsai import;
- merge visible furniture geometry with analysis geometry;
- move scoring, weighting, or perception-model fitting into the description or
  conversion skills;
- add a Rhino-specific semantic rule to the shared backend.

## Migration

The current combined workflow remains usable during migration. Existing
scripts and tests continue to be valid. The implementation adds or extracts
only the smallest reusable entry points needed to expose the independent
boundaries, then updates the coordinator to delegate to them.

No existing source model is modified by discovery, inspection, validation, or
export. Import remains the only mutating phase and requires explicit user
choice.

## Testing Requirements

Each independent skill receives focused contract tests:

1. discovery finds an existing MassPatch and reports a missing one without
   generating it;
2. generation remains independently callable and source-read-only;
3. logical mapping keeps a complete chair as one product;
4. IFC export succeeds with and without discovered substitutes;
5. exported proxy bindings preserve source GlobalIds and property values;
6. validation remains read-only and blocks invalid IFC only at the import gate;
7. Bonsai import and verification remain separate operations;
8. coordinator selects only requested capabilities and does not silently invoke
   generation or import.

All modified project-owned functions require English-first docstrings.
Important discovery, proxy binding, IFC serialization, routing, and import
gates require concise English-first intent comments.

## Self-Check

- The design extends the current workflow instead of replacing it.
- Optional skills are independently runnable.
- MassPatch generation and discovery are separate.
- Missing substitutes do not cause silent generation.
- Export and import remain separate.
- The coordinator does not own domain calculations.
- No perceptual weights are introduced.
- No placeholder requirements remain.
