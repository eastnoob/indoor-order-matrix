# Data Model: Field Kernel and Free-Space Read-Only Slice

## `FieldQuery`

Describes one request context:

- `domain_id`: selected analysis domain identity, or null when the query is
  relation-scoped/non-spatial
- `frame`: coordinate frame identifier and dimensionality (2D or 3D), or null
  for a non-spatial relation scope
- `plane` / `height_band`: optional section or projection definition
- `demand`: optional body, route, clearance, or tolerance requirements
- `tolerance`: declared geometric comparison tolerance
- `revision`: query/configuration revision

The query context is part of provenance. A world-XY `z=1.6 m` section is not
silently interpreted as whole-height walkability.

## `FieldSample`

One exact result contains:

- `value`: categorical, scalar, vector, or relation-native value
- `query`: the exact immutable `FieldQuery` used for the result
- `status`: `established`, `conditional`, `unknown`, `outside`, `invalid`, or
  `not_available`
- `support`: optional channel-native support/measurement with units where
  meaningful
- `source_ids`: stable source identities or artifact references
- `provenance`: source, algorithm, schema, tolerance, and query metadata
- `explanation`: short reason for the status/value

`unknown`, `outside`, and `not_available` are not numeric zero. `invalid` is a
diagnostic state and is not the same as missing data. `invalid`,
`not_available`, `outside`, and `unknown` carry no qualified value; `conditional`
and `established` carry a value.

## `Field`

The global semantic contract is a generic abstract class and exposes:

```text
domain
frame
value_schema
representation
provenance
evaluate(target, query) -> FieldSample
evaluate_many(targets, query) -> tuple[FieldSample, ...]
```

Spatial interpolation, topology, distance transforms, and sparse/dense storage
are optional capabilities. A relation field may support exact object/candidate
lookup without spatial sampling or a coordinate frame.

## `FreeSpaceField`

The first concrete instance consumes an explicit domain, fixed finite lattice,
fixed whole-height query context, pre-resolved occupancy records, explicit
unresolved source ids, frame, and origin-offset provenance. It clips each cell
to the domain using positive-area intersection while preserving disconnected
components and holes. Missing domain/channel is `not_available`; malformed
domain/grid/query/geometry is `invalid`; unsupported section/height-band,
tilted-plane, or demand requests are `not_available`. `original` and
`accepted` are representation values: accepted substitutes make results
`conditional`, unresolved support remains `unknown`, and empty is not a
walkability claim.

## `FieldBundle`

Groups separate channels that share domain/frame/query context:

- physical occupancy
- boundary distance
- occupancy clearance
- human/route demand qualification
- influence or decay
- later relation evidence

The bundle does not combine channels into a single score.

## `B3AdapterView`

Read-only mapping of the existing loader result. It preserves:

- serialized schema and selected variant
- source sections and artifact manifest
- package hashes and sample status/counts
- analysis plane and units
- conditional/open completeness fields

It does not add interpolation, inferred geometry, clearance certification, or
live-source discovery.

## `EvidenceContribution` (later relation-field use)

An auditable contribution targets an object, pair, candidate group, or
object-to-group relation and records provider, channel, polarity, support,
quality, status, provenance references, and explanation. Pairwise evidence is a
lower-level observation; membership strength may overlap across groups and is
not required to sum to one.

## Invariants

1. Samples from different frames or domains cannot be compared without an
   explicit operator.
2. A missing or invalid physical source cannot become known free.
3. A section result cannot be promoted to whole-height truth without a declared
   projection/height-band operation.
4. Exact lookup and batch lookup must agree after canonicalization.
5. Source ids and algorithm/schema versions survive adapter and visualization
   boundaries.
