---
name: visualarq-source-adapter
description: Use when a Rhino or VisualARQ model must be read as a traceable source before BIM mapping, IFC export, or layout analysis.
---

# VisualARQ Source Adapter

## Overview

This skill is the read-only boundary between a Rhino/VisualARQ document and the project’s neutral BIM source records. It preserves authored IFC labels, geometry facts, block/instance relationships, guides, and provenance; it does not decide product grouping or run later phases.

## When to Use

Use it for:

- VisualARQ or Rhino object listings with `IfcEntity`, `OM.IfcEntity`, user text, or object properties;
- mixed furniture, walls, doors, windows, columns, beams, slabs, grids, equipment, and decorations;
- repeated blocks or nested instances that must remain auditable;
- a live Rhino MCP read on port `15002` before mapping or export.

This adapter does not export IFC, generate MassPatch, infer regions or paths, import Bonsai, or mutate the Rhino document; it does not import Bonsai.

## Contract

Call `adapters.rhino_visualarq_source.normalize_visualarq_source(records, source_metadata=None)`.

The result is JSON-compatible and includes:

- `schema_version: visualarq-source-1`;
- one `objects` record per source object;
- preserved `source_properties` and `provenance`;
- `source_semantics.ifc_entity`, its source property, and confidence;
- `relationships` for blocks, instances, parents, and groups;
- `analysis_participation` as `include`, `exclude`, or `unknown`;
- separate `visualarq_guides`;
- `review_records` for missing, malformed, conflicting, or unsupported evidence;
- `exported_ifc: false` and `imported_bonsai: false`.

## Semantic Rules

Read an exact authored `IfcEntity` first, then `OM.IfcEntity`. Keep the raw value. Supported evidence includes furniture/furnishing, equipment, electrical, wall, door, window, column, beam, slab, roof, stair, railing, opening, grid, grid axis, and proxy classes. An absent, conflicting, or unsupported label becomes `unknown` with a review record.

Names, layers, geometry, proximity, identical meshes, and Block definitions are evidence only. They never establish an IFC class and never merge products. Hand off the result to `bim-logical-object-mapping` for complete logical products, type families, occurrences, and confidence.

Decorative objects stay in the payload. An explicit exclusion changes only `analysis_participation`; it never deletes the source object. Guides remain separate for `adapters.rhino_visualarq_grid` and must not become furniture.

## Live Use

Use the documented read-only Rhino MCP query on `http://localhost:15002/`, save a distinct source JSON report under the project output directory, and record the query source. Do not call mutation, delete, export, or save operations during adaptation.

## Handoff

```text
Rhino/VisualARQ -> visualarq-source-adapter -> bim-logical-object-mapping -> ifc-export
```

Each arrow is an explicit handoff. Export, IFC validation, Bonsai import, and post-import verification are separate skills or scripts and are never implied by this adapter.

The next export phase is full-export by default. It consumes usable geometry
from the source/mapping payload, preserves authored IFC classes, and sends
untyped objects to `IfcBuildingElementProxy`; this adapter itself still does
not export anything.

## Common Mistakes

- exporting every Rhino mesh as furniture;
- treating a VisualARQ label as proof of all IFC relations;
- collapsing repeated instances in the source phase;
- deleting plants or other decorations because they are excluded from analysis;
- using a layer or object name as semantic authority;
- claiming IFC/Bonsai work was completed when only a source payload was produced.
