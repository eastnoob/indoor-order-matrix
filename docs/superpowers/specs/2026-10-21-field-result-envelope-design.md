# Field Result Envelope Design

- Date: 2026-10-21
- Status: design review; no production implementation
- Scope: shared output contract for free-space and group-evidence field results
- Branch: `group-inference-design`

## 1. Purpose

The project needs one stable boundary between evidence computation and its
consumers. The boundary must support the same four uses for the group field
that the free-space field already targets:

1. UI handoff;
2. deterministic cache identity and replay;
3. structured analysis;
4. visualization.

The contract must preserve evidence and uncertainty instead of forcing every
result into a scalar membership score or into the six `FieldStatus` values.

The canonical output is an immutable **FieldResultEnvelope**. It is a result
transport and audit contract. It is not a new job system, channel registry,
candidate selector, scoring framework, or field kernel.

## 2. Existing boundaries to reuse

The envelope is built around existing project contracts:

- `features/field_core.py` provides `Field`, `FieldQuery`, `FieldSample`, and
  the six-state `FieldStatus` vocabulary.
- `features/space_field_visualization.py` provides the deterministic
  `field-layer-manifest/v1` visualization shape and distinct visual states.
- `features/group_self_description.py` provides auditable group evidence with
  its own raw states such as `computed`, `partial`, `not_available`,
  `invalid`, and `not_evaluated`.
- `docs/software-architecture.md` requires exact/batch lookup, immutable
  provenance, stale-result rejection, and separation of relation evidence from
  physical occupancy and free-space semantics.

`FieldSample` remains a compatibility projection. It is not the canonical
container because its validation intentionally forbids values for
`unknown`, `not_available`, `outside`, and `invalid`, while a partial relation
result may still contain useful structured evidence.

## 3. Scope

### In scope

- one JSON-safe, immutable result envelope;
- structured per-channel evidence records;
- raw result status and per-channel status preservation;
- source, algorithm, schema, query, and revision provenance;
- deterministic cache identity derived from the complete input boundary;
- optional `FieldStatus` compatibility projection with an explicit mapping
  reason;
- projection to the existing visualization manifest family;
- exact lookup and ordered batch lookup compatibility for relation fields.

Existing free-space `FieldSample` producers and consumers remain valid in this
slice. They may be wrapped or projected into the envelope, but they are not
rewritten wholesale merely to adopt the new outer contract.

Existing free-space `FieldSample` producers and consumers remain valid in this
slice. They may be wrapped or projected into the envelope, but they are not
rewritten wholesale merely to adopt the new outer contract.

### Out of scope

- generating or selecting candidate groups;
- choosing a unique partition or forcing singleton assignment;
- scalar membership strength, total score, fixed weights, or uncalibrated
  fusion;
- Bayesian posterior, ML clustering, psychological calibration, or human
  labels;
- changing the free-space Gaussian diagnostic into a probability or group
  membership model;
- a universal evidence plugin registry or a new job/result framework;
- writing derived inference results into factual IFC by default;
- implementing the relation field or UI in this design stage.

## 4. Canonical envelope

The envelope is conceptually equivalent to the following JSON-safe record.
Names are part of the v1 contract and may not be silently repurposed:

```text
FieldResultEnvelope {
  schema: "field-result-envelope/v1",
  target: {
    kind: string,
    id: string,
    identity: string
  },
  query: {
    domain_id: string | null,
    frame: string | null,
    plane: JSON value | null,
    height_band: JSON value | null,
    demand: JSON value | null,
    tolerance: non-negative finite number,
    revision: string
  },
  raw_status: computed | partial | not_evaluated | not_available |
              invalid | outside | ambiguous,
  channel_set: [string, ...] | [],
  value: {
    channels: [EvidenceChannelRecord, ...]
  } | null,
  support: JSON value | null,
  field_projection: {
    status: established | conditional | unknown | outside | invalid |
            not_available,
    mapping_reason: non-empty string
  } | null,
  source_ids: [string, ...] | [],
  provenance: {
    algorithm_version: string,
    schema_version: string,
    ... JSON-safe audit fields
  },
  cache_identity: {
    input_fingerprint: string,
    source_fingerprint: string,
    query_fingerprint: string,
    channel_fingerprint: string,
    recipe_fingerprint: string,
    algorithm_version: string,
    schema_version: string,
    identity: string
  },
  visualization_ref: {
    layer_id: string | null,
    semantic_channel: string,
    manifest_schema: "field-layer-manifest/v1"
  } | null,
  explanation: string
}
```

`value` may remain non-null for `partial` or `ambiguous` results because the
envelope is allowed to carry usable evidence alongside missing or conflicting
channels. This is the deliberate difference from `FieldSample`.

`channel_set` is the normalized, sorted set of admitted channel identifiers.
Every channel record names an identifier in this set. An admitted channel with
no usable observation still receives a record with a null observation and an
appropriate `not_available` or `not_evaluated` status, so the cache boundary
does not confuse "not admitted" with "admitted but unavailable".

`target.id` is a stable canonical key. For a relation target such as
`object × candidate_group`, it is a deterministic encoding of both identities
(or another declared canonical relation key); it must not depend on input
traversal order. `target.identity` is the canonical target fingerprint used in
cache identity. A target with no single natural id must provide a stable
canonical payload fingerprint rather than an arbitrary display label.

`EvidenceChannelRecord` contains:

```text
EvidenceChannelRecord {
  channel: string,
  required: boolean,
  polarity: positive | negative | conflict | descriptive,
  observation: JSON value | null,
  support: JSON value | null,
  units: string | null,
  status: computed | partial | not_evaluated | not_available |
           invalid | outside | ambiguous,
  source_ids: [string, ...] | [],
  provenance: JSON-safe mapping,
  explanation: string
}
```

Channel identifiers are non-empty canonical strings. `required` declares
whether that channel is required for a `computed` result under the current
field declaration; it is not a numeric weight. Channel records are
sorted by canonical channel id and cannot contain duplicate channel/polarity
keys. A descriptive record is allowed to explain a grammar fit or diagnostic
pattern without becoming positive or negative membership evidence. Top-level
provenance must contain `algorithm_version` and `schema_version`; channel
provenance either contains those same required keys or explicitly declares
that it inherits the top-level versions.

The implementation exposes two adapter seams without changing the existing
`Field` API:

```text
project_field_sample(result: FieldResultEnvelope) -> FieldSample | None
build_field_result_layer_manifest(
    *, layer_id: string, channel: string,
    results: Iterable[FieldResultEnvelope]
) -> JSON mapping
```

`project_field_sample` returns `None` when the raw result cannot be represented
without discarding structured evidence. `build_field_result_layer_manifest`
uses the existing `field-layer-manifest/v1` outer shape and retains raw status
and channel records in each relation record; it may delegate compatible
records to the existing `build_field_layer_manifest` implementation.

The relation adapter adds `raw_status`, `channel_set`, and `channel_records` as
additive record fields in that existing v1 manifest. It does not change the
meaning of the existing `status`, `value`, `support`, `visual_state`, query,
or provenance fields. A future incompatible manifest shape requires a new
manifest schema version rather than silently changing v1.

For an envelope with a valid `field_projection`, the manifest's existing
`status`, `value`, `support`, and `visual_state` fields use that projection. If
no compatible projection exists, the adapter uses `status="unknown"` and
`visual_state="unknown"` as a conservative renderer fallback, records the
mapping reason in `explanation`, and preserves the actual `raw_status` and all
channel records in the additive fields. This fallback is a display state only;
it never changes the canonical envelope status.

## 5. Status semantics

`raw_status` describes the result produced by the domain computation. It must
not be inferred from whether the Python function returned normally.

| Raw status | Meaning | Compatibility projection rule |
|---|---|---|
| `computed` | Required evidence for this result is complete and valid | May project to `established` only when the field meaning is complete and original-backed |
| `partial` | Some evidence is usable and some required or requested evidence is incomplete | Preserve raw status; project only with a consumer-specific reason; never use `conditional` as a synonym |
| `not_evaluated` | Evaluation was intentionally skipped or not applicable | Preserve the cause; only project after distinguishing unavailable capability from unresolved evidence |
| `not_available` | Required domain, channel, or capability is absent | May project to `not_available` |
| `invalid` | Required input or evidence is malformed or unusable | May project to `invalid` |
| `outside` | Target is outside an explicitly available domain | May project to `outside` |
| `ambiguous` | Valid alternatives or conflicting observations remain unresolved | Preserve raw status; do not silently choose a score or winner |

`conditional` is reserved for an accepted substitute or representation
limitation, as required by the existing free-space contract. It is not a
general partial-data state.

`outside` and `ambiguous` are available in the generic vocabulary only when
the target/domain semantics support them. A group adapter must not manufacture
`outside` merely to match free-space formatting, and must retain unresolved
competition as `ambiguous` rather than selecting a winner.

The envelope always retains `raw_status`, even when a `FieldStatus` projection
exists. The projection must include a non-empty `mapping_reason`; it is an
adapter decision, not a replacement for the raw state.

Every non-computed raw result carries a non-empty `explanation` describing the
missing capability, invalid input, unresolved evidence, domain boundary, or
ambiguity. This is especially required for `not_evaluated`, which must state
whether evaluation was skipped, unsupported, or intended but incomplete.

## 6. Evidence semantics

The envelope carries evidence vectors, not a universal numeric transform.

- Geometry, pattern, semantic, space, and context remain separate channels.
- Positive and negative observations are retained independently.
- Ordinary semantic mismatch is soft negative evidence.
- Explicit mutual exclusion is a conflict or candidate-level veto with source
  provenance.
- Missing and invalid evidence remain categorical; they are never filled with
  numeric zero.
- An admitted ideal pattern may emit both `pattern_conformity` and
  `pattern_residual`; without an admitted ideal pattern, descriptive grammar
  output does not become polarity evidence.
- Adding or removing a channel changes the envelope's channel fingerprint and
  recomputes the result from the current channel set.

No channel receives an implicit weight merely because it appears in the
envelope. Any later scalar projection must be separately named, versioned, and
calibrated.

`support` is an audit/support payload such as witness ids, measured support
geometry, or contributing source references. It is not a membership strength,
probability, or hidden score.

## 7. Cache and freshness contract

The `identity` value is a deterministic digest of the canonical target, query,
channel set, source and input fingerprints, algorithm version, schema version,
recipe/representation parameters, and all other inputs that affect the
computation. It is derived by the producer and is not an arbitrary caller
label. `source_ids` are audit references and are not a substitute for the
source fingerprint.

`channel_fingerprint` is computed from the normalized admitted channel ids and
their declared channel parameters/versions, including an explicit record for
an admitted but unavailable channel. It is not computed from display order or
from a scalar result.

The top-level `schema` identifies this envelope contract. The
`provenance.schema_version` and `cache_identity.schema_version` identify the
producer's value/provenance schema used for the computation. They may have the
same string in a simple implementation, but they have different meanings and
must not be used interchangeably.

A cached envelope is reusable only when all of these match:

- target identity;
- query/domain/frame/revision;
- source and input fingerprints;
- admitted channel set and channel fingerprint;
- algorithm and schema versions;
- declared recipe or representation parameters and recipe fingerprint.

If a channel is removed, its source fingerprint and identity must change. A
cache hit must never retain influence from a removed channel. A stale or
version-mismatched envelope is rejected as current but may remain available as
historical audit data.

## 8. Consumer projections

### UI and visualization

The UI consumes a deterministic manifest projection, not channel-private
Python objects. The projection reuses the outer `field-layer-manifest/v1`
shape, preserves the raw status and channel records, and supplies a renderer
visual state at projection time. The envelope itself contains only a manifest
reference, never UI colors, HTML, SVG payload, or renderer state. A relation
result that cannot satisfy `FieldSample` value/status
validation remains an envelope-backed manifest record; it is not forced into a
false six-state sample.

### Analysis

Analysis consumers read the structured `value.channels`, raw status,
provenance, and source ids. They must not reconstruct evidence by parsing
`visual_state` or by treating `field_projection.status` as a probability.

### Field API compatibility

An adapter may create a `FieldSample` only when the projected status and value
obey the existing `FieldSample` invariants. Exact lookup and ordered batch
lookup remain the shared API. The envelope is still retained as the canonical
audit result behind that projection.

## 9. Immutability and validation invariants

The eventual implementation must reuse the existing deep-freeze/JSON-safe
rules from `features/field_core.py` rather than introduce a second serializer.
It must reject:

- non-string target, channel, or source identifiers;
- non-finite numbers or non-JSON-safe values;
- missing algorithm or schema provenance;
- duplicate canonical channel records;
- an empty channel identifier or a channel record outside `channel_set`;
- an invalid `FieldStatus` projection or an empty mapping reason;
- empty cache-identity components or cache identities that do not include the
  declared input, source, channel, and recipe fingerprints.

The envelope is immutable after construction. Serialization order is
deterministic so that equal inputs produce equal cache identity and manifest
bytes.

At minimum, a `computed` result has a non-null structured value with at least
one channel record and a non-empty `channel_set`. A `partial` or `ambiguous`
result may carry a non-null structured value, but the raw status and
incomplete/conflicting channels must remain visible. When `channel_set` is
non-empty, `value.channels` contains at least one record for every admitted
channel, even when every observation is null. For `not_available`, `outside`,
`not_evaluated`, or `invalid`, those records are status-bearing diagnostics and
are never presented as a valid field observation. A completely empty
`channel_set` may use `value=null`.

The optional `field_projection` does not duplicate the projected payload. When
`project_field_sample` succeeds, its `FieldSample.value` is the envelope's
structured `value`, its `support` and `source_ids` come from the corresponding
envelope fields, its `query` is reconstructed from the envelope query, and its
provenance includes the envelope provenance plus the raw-status and mapping
reason. The projection is rejected if those values would violate any existing
`FieldSample` invariant.

## 10. Acceptance criteria for this contract

The design is accepted for implementation when the owner confirms:

1. `FieldResultEnvelope` is the canonical output and `FieldSample` is a
   compatibility projection;
2. the v1 field names and requiredness in Section 4 are correct;
3. raw status is never discarded by a projection;
4. partial and ambiguous evidence can remain structured and non-null;
5. cache identity includes the complete input and channel boundary;
6. UI/visualization uses a manifest projection while analysis uses the
   structured envelope;
7. implementation remains limited to this contract and its focused tests.

Approval of this spec does not approve implementation of group candidate
generation, aggregation, membership scoring, or selection. Those require a
separate design review and implementation plan.

## 11. Review checklist

- No scalar membership score is hidden in `value`.
- No fixed weights or thresholds are introduced.
- `partial`, `ambiguous`, `not_evaluated`, and `not_available` remain
  distinguishable.
- Existing free-space `FieldSample` and manifest consumers can continue to
  operate through adapters.
- UI does not depend on private channel mapping.
- Cache invalidation follows channel add/remove and source changes.
- No factual IFC data is mutated by this output contract.

**STOP FOR OWNER REVIEW.**
