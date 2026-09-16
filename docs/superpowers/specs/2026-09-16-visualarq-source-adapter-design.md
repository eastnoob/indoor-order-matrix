# VisualARQ Source Adapter Design

## Status

Approved design for implementation on `codex/visualarq-source-adapter`.

## Goal

Create a reusable, read-only adapter that extracts Rhino/VisualARQ object facts and authored IFC labels into a neutral source payload that downstream logical-object mapping and IFC export can consume without copying Rhino-specific logic.

## Non-goals

- No IFC serialization, validation, Bonsai import, MassPatch generation, region inference, path inference, or layout scoring.
- No mutation of the Rhino document.
- No silent semantic guessing from geometry, layer names, object names, or spatial proximity.
- No automatic merging of source objects into logical furniture products.

## Architecture

```text
Rhino/VisualARQ live document
    -> visualarq-source-adapter
    -> neutral source payload + provenance + review records
    -> bim-logical-object-mapping
    -> ifc-export
```

The adapter is an evidence-preserving boundary. It records what the source application exposes and normalizes field names, but it does not decide whether several components are one product. The mapping skill remains the authority for product, type-family, and occurrence decisions.

## Input Contract

The adapter accepts a provider interface rather than importing Rhino APIs directly into the core normalizer. A provider returns object records with any available fields:

- `id`: stable source GUID or provider identity;
- `name`, `layer`, `object_type`, and `instance_definition`;
- `geometry_type`, `vertices`, `faces`, or a geometry summary;
- authored IFC data from `IfcEntity`, `OM.IfcEntity`, or equivalent property paths;
- instance/block path and parent-child references;
- arbitrary source properties retained under `source_properties`;
- optional `analysis_participation` authored by the user.

Provider failures are represented as an adapter error record with the object id when available. One malformed object must not silently disappear from the payload.

## Output Contract

The normalized payload is JSON-serializable and contains:

```json
{
  "schema_version": "visualarq-source-1",
  "source_application": "Rhino",
  "source_name": "...",
  "source_path": "...",
  "objects": [
    {
      "id": "...",
      "source_name": "...",
      "display_name": "...",
      "source_kind": "mesh|brep|extrusion|instance_reference|curve|unknown",
      "geometry": {"available": true, "summary": {}},
      "source_semantics": {
        "ifc_entity": "IfcWall|IfcDoor|...|unknown",
        "ifc_entity_source": "IfcEntity|OM.IfcEntity|none",
        "confidence": "authored|unknown"
      },
      "relationships": {
        "block_definition": "...",
        "instance_path": [],
        "parent_ids": [],
        "group_ids": []
      },
      "analysis_participation": "include|exclude|unknown",
      "provenance": {"provider": "...", "raw_id": "..."}
    }
  ],
  "review_records": []
}
```

The exact implementation may add fields, but it must preserve these meanings and remain backward-compatible with the existing normalized source format. Raw authored values remain available for audit; normalized semantic values never replace them.

## Semantic Rules

1. `IfcEntity` and `OM.IfcEntity` are authored evidence, not proof of complete IFC relationships.
2. A recognized authored IFC entity is copied into `source_semantics.ifc_entity` only when it matches the allowlisted IFC entity-name grammar. Unsupported or malformed values become `unknown` and produce a review record.
3. The adapter must support at least furniture, furnishing, equipment, electrical, wall, door, window, column, beam, slab, roof, stair, railing, opening, grid, and proxy labels without converting them into one broad furniture class.
4. A source object with no IFC label is `unknown`; geometry and names may be retained as evidence but cannot establish an IFC class.
5. Decorative objects such as plants remain in the source payload. They default to `analysis_participation: unknown` unless an authored project rule marks them `exclude`; the adapter never decides their analytical role from the word “plant”.
6. `analysis_participation` is a source fact or explicit policy result, not a computed layout judgment. If absent, emit `unknown` and let the downstream analysis-selection step decide.
7. Block and instance data is preserved as relationship evidence. It is not treated as a complete product boundary, and repeated instances are not collapsed here.
8. Rhino groups, layers, names, and identical definitions are never used as the sole semantic authority.
9. Curves that represent authored grids/guides are preserved in a separate `visualarq_guides` payload and are not emitted as furniture or generic proxies.

## Name Handling

Preserve authored names in `source_name`. A separate `display_name` may be generated only for presentation, and generated names must never become identity or IFC semantic evidence. Name inference belongs to logical-object mapping, not this adapter.

## Error and Review Policy

The adapter returns a complete payload plus `review_records` for missing identity, malformed IFC labels, unavailable geometry, unsupported provider fields, and ambiguous relationships. It must fail loudly for invalid top-level provider output, but continue with per-object review records where safe. Downstream automation may block on review records; the adapter itself does not export or import.

## Testing and Acceptance

Tests must prove:

- authored IFC labels survive with their source and normalized forms;
- wall/door/window/column/beam/slab/grid labels are not rewritten as furniture;
- unlabelled objects become `unknown`, not guessed classes;
- decorative objects are preserved and can be explicitly excluded from analysis without deletion;
- block and instance paths are preserved without duplicate product creation;
- malformed records produce review evidence or a clear top-level error;
- the adapter is read-only with respect to its provider;
- a live Rhino MCP capture from port `15002` can be converted to the neutral payload without requiring IFC export.

The acceptance artifact is a source JSON report and a concise summary of object counts by geometry type, authored IFC label, and analysis-participation state. Export, validation, and Bonsai import remain separate acceptance stages.

## Documentation Contract

The skill must state the independent phase boundary, the input/output contract, the semantic evidence rules, the read-only guarantee, and the handoff to the existing mapping and export skills. Every new or modified project-owned function must have an English-first docstring; core extraction, normalization, semantic classification, provenance, and handoff logic must have English-first comments.
