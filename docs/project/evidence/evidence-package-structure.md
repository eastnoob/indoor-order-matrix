# Evidence Package Structure

Status: design record; the structure below reuses the existing field and
package-output contracts. Cross-package readback is feasible but is not yet an
implemented runtime capability.

## Plain-language model

An evidence package is a saved analysis report. Its channels are the actual
evidence. Each channel may have its own algorithm, inputs, result, status, and
provenance. The package groups those channels under one target/query/scope
boundary and gives the group a stable identity and freshness state.

```text
EvidencePackage
├── package identity
│   ├── package_id / package_schema
│   ├── producer / schema_version
│   └── algorithm or output-function version
├── analysis boundary
│   ├── target set
│   ├── query / scope / analysis plane
│   └── dependency fingerprints and recipe
├── channels[]
│   ├── channel identity and declaration
│   ├── channel-specific algorithm and inputs
│   ├── observation/value and status
│   ├── units/scale
│   └── source ids and provenance
└── snapshot metadata
    ├── package/content identity
    ├── artifact references
    └── freshness / recompute status
```

The four responsibilities discussed during design map to this object as
follows:

1. **Calculation** belongs to each channel. `euclidean_distance` and
   `path_distance` may therefore use different algorithms and dependencies.
2. **Snapshot and cache governance** belongs to the package materialization.
   A snapshot records the package result and content identity; a cache is only
   the mechanism used to reuse that snapshot.
3. **Readback** is an access operation over a snapshot. It validates package,
   channel, target/query/plane/scope, version, and freshness before returning a
   channel.
4. **Derivation** is another channel operation. A derived channel records the
   channels it used and is appended to the result; source channels are retained
   unchanged.

## Existing implementation mapping

| Concept | Current contract | Current state |
| --- | --- | --- |
| Channel result | `EvidenceChannelRecord` inside `FieldResultEnvelope` | Implemented |
| Channel lineage | `EvidenceChannelReference` and `derived_from` | Implemented for supplied envelopes |
| Additive package output | `EvidencePackageOutput` | Implemented; source channels cannot be overwritten or removed |
| Package execution | `EvidencePackage.evaluate(source_envelopes)` | Implemented; accepts immutable envelope inputs |
| Envelope identity | `FieldResultEnvelope.cache_identity` | Implemented |
| Package identity/status | package contract and freshness helpers in `features/field_core.py` | Implemented for package-level comparison |
| Snapshot storage policy | runner artifacts and manifests | No shared storage API |
| Package readback | stable package/channel resolver | Not implemented |
| Cross-package dependency/status propagation | consumer declaration and effective status | Not implemented |

## Cross-package channel consumption

One package may consume a named channel from another package. This is
architecturally compatible with the additive output contract, but it requires a
small readback boundary that does not exist yet.

The consumer must identify the source by:

```text
source_package_id
source_package_identity
source_channel_id
target/query/analysis-plane/scope
required package/channel schema and algorithm versions
freshness requirement
```

The reader returns the selected channel together with the source package
identity, source status, freshness, and provenance. The consumer may append a
new channel, but may not overwrite or delete the source channel. It must record
the source package/channel identity as a dependency so changes to the source
invalidate the derived result.

For the planned example:

```text
distance package
├── euclidean_distance
└── path_distance

potential package
├── pure axis channels
├── relation/resultant/hierarchy channels
└── distance_conditioned_cohesion  (future additive channel)
```

Free-space inputs used by `path_distance` remain distance computation inputs;
they do not become a third distance channel unless the distance package
explicitly declares such a channel.

Source status must remain visible. A consumer may not turn stale or unavailable
source data into a computed value. The minimum propagation rule is:

| Source package/channel state | Derived channel state |
| --- | --- |
| fresh + computed | compute normally |
| fresh + partial/unknown | at most partial; retain the source reason |
| stale | not available for current computation; retain stale reason |
| unavailable / unreachable / not available | not available unless the derived algorithm explicitly defines a valid partial result |
| invalid / ambiguous | invalid or ambiguous; never silently choose or fill zero |

The source status and the consumer's own status remain separate fields. A
cross-package dependency must be explicit and acyclic; an implicit cycle or a
package reading its own downstream output is rejected. Cycle detection belongs
to the future dependency/readback boundary, not to the existing channel output
validator.

## Current conclusion

Cross-package consumption is **feasible in the current design direction** and
is already compatible with stable identities, additive outputs, lineage, and
freshness fingerprints. It is **not currently implemented**: the existing
`EvidencePackage.evaluate()` only receives `FieldResultEnvelope` values, and
`EvidencePackageOutput` validates lineage only against the envelopes supplied
to that call. A future adapter must read a source snapshot, map selected
channels into the existing envelope/output contracts, and preserve the source
package identity and status.

