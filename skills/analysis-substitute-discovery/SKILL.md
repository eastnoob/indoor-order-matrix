---
name: analysis-substitute-discovery
description: Use when an existing model or normalized record set may already contain analysis-only geometry substitutes that must be found without generating or exporting them.
---

# Analysis Substitute Discovery

This skill is a read-only lookup boundary for already-authored or already-generated
analysis substitutes. It may inspect object properties, collections, layers,
source bindings, and IFC proxy facts, but it does not create missing geometry.

## Contract

Input records may describe source objects and candidate substitute objects.
The discovery result is JSON-safe and contains:

- `status`: `passed`, `not_found`, or `ambiguous`;
- `substitutes`: accepted candidate bindings;
- `source_bindings`: source-to-substitute evidence;
- `missing_sources`: source IDs without a usable substitute;
- `ambiguous_candidates`: conflicting candidate IDs;
- `confidence`: per-binding confidence;
- `provenance`: evidence describing where the binding was found.

Every accepted record preserves `source_global_id`, `substitute_id`,
`substitute_kind`, `analysis_role`, `visibility_policy`, `provenance`, and
`confidence`.

## Rules

- Discovery is read-only.
- An absent substitute returns `not_found`; it does not call generation.
- A duplicate or contradictory binding returns `ambiguous`.
- `MassPatch` is a kind of substitute, not a command to generate one.
- The visible source object and analysis substitute remain separate records.
- In a nested Rhino Block, an `analysis_substitute` child is evidence attached
  to the root logical product. It must carry `OM.SourceInstanceId` or inherit
  the root instance ID; a child without an explicit representation role is
  `ambiguous`, not an automatically discovered substitute.
- Discovery may report candidates automatically, but a contradictory or
  unbound Block path requires supervisor confirmation before export.
- IFC export, validation, import, and scoring are separate skills.

See [the neutral contract](references/substitute-contract.md) for field details.
