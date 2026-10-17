# Data Model: Free-Space Field Inspection

## LockedInputBundle

Represents the authenticated input set assembled from the successful frozen
package and source capture.

| Field | Required | Constraint |
|---|---:|---|
| `package_root` | yes | Must resolve to `run_20261009T142454Z_0d7308` |
| `capture_root` | yes | Must resolve to `b3_real_source_field/run_001` |
| `artifact_manifest` | yes | Every consumed file must match its SHA-256 and byte count |
| `frame` | yes | Exactly `world_xy` |
| `units` | yes | Exactly `m` |
| `origin_offset_m` | yes | Two finite numbers; frozen value `[0.0, 0.0]` |
| `query_scope` | yes | Exactly `whole_height_plan` |
| `domain_components` | yes | Exact polygon components, including two holes |
| `unresolved_source_ids` | yes | The five upstream unresolved ids; no renderer filtering |
| `boundary_scoped_ids` | yes | Exact upstream membership; current value `live-step-6231` |

## SourceGeometryRecord

One selected physical occupancy geometry or accepted proxy.

| Field | Required | Constraint |
|---|---:|---|
| `id` | yes | Unique selected record id |
| `geometry_components` | yes | Whole-height plan components in world-metre XY |
| `represented_source_ids` | yes | Non-empty unique owner ids; proxy owners are not duplicated as geometry |
| `representation_status` | yes | `original` or `accepted` |
| `source_class` | yes | Retained for display; never used to remove physical occupancy |
| `capture_ref` | yes | Authenticated source mesh or proxy reference |
| `proxy_binding_provenance` | proxy only | Object ref, binding declaration hash, approximation limit |

## QualifiedWholeHeightSceneInput

Runner-local handoff into the existing Neutral Scene view path.

- `neutral_scene`: `NeutralSceneV2` with explicit world-XY domain components,
  frame, units, and zero origin offset.
- `source_objects`: authenticated source facts and shared occupancy bindings.
- `geometry_refs`: qualified whole-height refs only.
- `audit_only_capture_refs`: original capture references/arrays retained for
  audit when a locked unresolved source has no qualified `geometry_refs`.
- `uncertain_source_ids`: the exact five locked unresolved ids, preserved before
  `analysis_scene_view` can promote geometry.
- `boundary_scoped_ids`: exact upstream semantic/support scope ids, including
  `live-step-6231`; no class/name heuristic.

The handoff must be passed through `analysis_scene_view(neutral_scene)`.
Historical eye-plane section records are not part of this entity.

## FreeSpaceFieldCell

One exact lattice evaluation at `(row, column)`.

| Field | Required | Constraint |
|---|---:|---|
| `target` | yes | Integer row/column within declared lattice |
| `value` | yes | `true`, `false`, or `null` according to status |
| `status` | yes | One of `established`, `conditional`, `unknown`, `outside`, `invalid`, `not_available` |
| `source_ids` | yes | Exact field sample source ids |
| `query` | yes | Domain id, frame, revision, tolerance, and unsupported query fields |
| `support` | yes | Cell bounds, domain intersection, lattice metadata |
| `explanation` | yes | Non-empty status explanation |
| `provenance_ref` | yes | Reference into shared provenance table |

## SharedProvenanceTable

Serialization-only deduplication of repeated manifest provenance.

- `global_selected_records`: one canonical copy of the 343-record inventory.
- `record_refs`: deterministic ids for source/proxy records.
- `cell_provenance_overrides`: only per-cell fields that differ from the shared
  inventory, including occupied record ids and represented source ids.
- `recovery`: a documented deterministic merge that reproduces the original
  `build_field_layer_manifest` record exactly.

This table is not a new Field capability and must not alter `FieldSample` or
`build_field_layer_manifest`.

## InspectionManifest

The self-contained HTML/SVG payload.

- `schema`: versioned inspection schema.
- `frame`: world XY, metres, explicit offset, whole-height query.
- `domain`: exact boundary and holes.
- `source_layer`: source geometry, classes, ids, proxies, and uncertainty.
- `field_layer`: output of `build_field_layer_manifest` plus deduplicated
  references.
- `timings`: projection, field evaluation, serialization in milliseconds.
- `sizes`: JSON and HTML/SVG byte counts.
- `limits`: no walkability, clearance, connectivity, or production-resolution
  claim.
