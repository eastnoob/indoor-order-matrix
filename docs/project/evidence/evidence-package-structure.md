# Evidence Package Structure

An evidence package groups related channels for one materialized analysis
snapshot. Each channel keeps its own meaning, method, inputs, observation,
status and scale. Grouping channels does not combine them into a score.

## Package-owned lifecycle — approved 2026-11-12

The user approved implementation of a package-owned execution boundary after
discussion with the parent chat. A complete package includes its public entry,
channel algorithms, raw/processed artifacts, cache policy and storage adapter.
The existing frozen `EvidencePackage` remains the shared publication/validation/
processing template within that capability. Compose existing functions; no
inheritance hierarchy, manager or wrapper is required. Storage code may stay in
its existing adapter layer; pure features do not import Blender/session code.

The package decides artifact ownership, content identity, freshness and reuse or
recomputation. The storage adapter performs authenticated/validated reads and
atomic writes. Callers use package-level entry functions for raw and optional
processed output plus `recompute_required`, `reasons` and `affected_targets`.
Raw values remain intact. Processing recipes have independent identities and
optional cache entries; changing a processor must not recompute valid raw data.

Content identity is not proof of currentness. Restoring equal calculation input
may reuse retained artifacts, while current request metadata is reconstructed
and original calculation provenance remains explicit. Normalize only revisions
known to be publication metadata, preserving semantic query revisions. Saved
processed readback must verify current raw content and an independently supplied
current processing recipe. Raw JSON v1 and default-off processing remain intact.

This section is the approved target; implementation and independent acceptance
are tracked in the [lifecycle plan](../../superpowers/plans/2026-11-12-evidence-package-lifecycle.md).
The runtime-only limitations below describe the baseline until that plan closes.

## Two output ports — user decision 2026-11-12

The common template keeps its existing inputs, algorithms and raw computation
cache. The raw port remains `EvidencePackage.evaluate(...)`, which returns the
existing `EvidencePackageOutput`. Its historical `output_function` or
`context_output_function` still performs the required publication step: the
word "raw" here includes those existing published derived channels, alongside
the complete original source envelopes. Their values, units, statuses,
provenance, output identities and saved JSON v1 are preserved.

The second port is `package.process_output(raw_output,
package_freshness="fresh")`. It reads an already computed or deserialized raw
publication; it does not rerun `evaluate()` or the original algorithm. Each
package may explicitly configure its own `EvidenceOutputProcessor`, containing
`function_id`, `version`, `function` and immutable JSON-compatible `parameters`.
The callback receives `(raw_output, parameters)` and returns existing
`EvidenceOutputChannel` records. The three current factories accept the
keyword-only `output_processor=` argument, including both potential variants.

Every package defaults to `output_processor=None`. The processed result is a
separate `EvidenceProcessedOutput`; it never appends to the historical raw
`.outputs` or replaces original channels.

| Processed-port condition | `error_code` | `outputs` |
| --- | --- | --- |
| No processor configured, regardless of freshness | `OUTPUT_FUNCTION_NOT_CONFIGURED` | Empty; no usable value |
| Configured, but source freshness is stale/unavailable | `OUTPUT_SOURCE_NOT_FRESH` | Empty; callback not run |
| Configured callback raises or returns invalid channels | `OUTPUT_PROCESSING_FAILED` | Empty; no raw fallback |
| Configured, fresh, valid callback result | `None` | Validated processed channels |

`package_freshness` defaults to `"unavailable"`. Callers obtain a fresh receipt
through the existing contract comparison; a saved output identity is not that
receipt. Invalid source type, package/producer identity or freshness argument
is an API error, distinct from callback failure. The fixed marker and empty
channels let a UI or runtime consumer reliably identify a closed port. There
is no implicit identity transformation and no universal normalization formula.

Processed channels declare their own names, scales, units and statuses. Their
`derived_from` uses complete `EvidencePackageChannelReference` addresses into
the exact supplied raw publication. The boundary rejects unknown lineage and
duplicate target/channel addresses. A missing or unusable referenced reading
cannot become a usable observation; a noncomputed source cannot be promoted
to computed. Finite values and declared scalar bounds are validated without
requiring every package to use `[0,1]`.

The separate `processing_identity` binds the package, raw `output_identity`,
complete raw payload fingerprint, processor ID/version and immutable
parameters. Different processing recipes or changed raw readings/statuses
therefore have distinguishable identities while the original cache key stays
unchanged. This identity is not a live-currentness receipt or a new persistent
cache. A processor must use the supplied raw publication and declared
parameters, rather than hidden mutable inputs, and version changes to its
behavior.

This implementation exposes runtime processing only. The historical serializer,
saved reader, adapters and cross-package dependency resolver still consume raw
`EvidencePackageOutput`. Processed-result persistence, processed cross-package
dependencies and formula selection have no new implementation in this change.
Execution and acceptance are recorded in the
[optional-processing plan](../../superpowers/plans/2026-11-12-evidence-package-optional-processing.md).

```text
Evidence package
├── Publication records
│   ├── contract: target/query/scope/plane, recipe and input fingerprints
│   ├── status: freshness, recompute reasons and affected targets
│   └── manifest: published data and existing visualization locators
├── Raw port: EvidencePackageOutput (existing publication)
│   ├── source_envelopes: complete immutable original evidence
│   ├── outputs: additive channels with method, input lineage and results
│   ├── dependencies: explicit package/output/target/channel addresses
│   └── output_identity: computation identity
├── Saved raw JSON
│   └── payload_fingerprint: complete serialized content fingerprint
└── Optional processed port: EvidenceProcessedOutput (runtime)
    ├── raw_output_identity / raw_payload_fingerprint
    ├── processor identity / version / parameters / processing_identity
    └── outputs, or fixed error_code with no channels
```

The channel responsibilities use existing fields, not additional nested types:

| Responsibility | Existing representation |
| --- | --- |
| Algorithm/recipe | Channel provenance `method`, `algorithm_version`, `schema_version` and formula when declared; otherwise package `output_function` and `output_function_version`, scoped to the named channel. Source records may explicitly inherit top-level envelope provenance. |
| Actual inputs | `derived_from`, source-envelope `cache_identity` input/source/query/recipe/channel fingerprints, and explicit external dependencies. |
| Output | Channel `observation`, `status`, `scale`, explanation and source IDs. |
| Content integrity | `fingerprint_evidence_dependency(output_channel)` fingerprints one complete channel; serialized `payload_fingerprint` covers the complete package. |

The outer contract/status/manifest remains separate from the runtime output.
Freshness is calculated by comparing the saved contract with a freshly built
current contract. A saved status receipt only records its earlier comparison.
The consumer's `current_source_envelopes` must be independently supplied;
matching package IDs cannot bind a saved output to that contract. Numeric use
compares a binding signature over `target`, `query`, `channel_set`,
`cache_identity`, `raw_status`, `value`, `support` and `source_ids`, including
source readings. Missing current context yields unavailable; input/query/plane
mismatch is rejected. Outer provenance audit fields such as
`source_freshness` or visualization do not enter this input signature; channel
records inside `value` remain included.

`output_identity` hashes source result identities, output declarations, scale,
function/version and nonempty dependencies. It deliberately excludes reading
and status bytes, so equality alone does not prove equal observations. Empty
dependencies are omitted from this computation hash to preserve historical
publication IDs. The serialized `payload_fingerprint` is SHA-256 of canonical
complete output JSON excluding its own field; it includes observations,
statuses, provenance, source fingerprints and `output_identity`. A pinned file
SHA-256 binds the actual artifact bytes. None of these hashes establishes
currentness without the current-contract comparison.

The rollout adds fixed known-v1 readers:
`deserialize_field_result_envelope(payload)` and
`deserialize_evidence_package_output(payload)`. They rebuild existing validated
types from JSON values, require and validate the saved output identity, reject
unsupported schemas and unknown structural fields, and check a payload
fingerprint when present. They do not load arbitrary classes or objects.
Historical publications without dependencies or the new fingerprint remain
readable; their exact file bytes must be pinned by the replay consumer.

An external read uses the full `package_id`, `output_identity`,
`target_identity`, `channel` address. Two targets may publish the same channel
name and may both be consumed. The raw reader checks that address against a
typed output. The resolver separately gates caller-supplied freshness; fresh
channels retain their observation, status and scale. Stale/unavailable channels
provide no usable channel; an available typed source contributes only an
observation-redacted audit record. Every derived output that uses such a
dependency must have `observation=None`, including `partial` outputs. Missing
or mismatched references are rejected, rather than filled with zero.

Published dependencies keep compact references; evaluation-time
`source_output` handles are not recursively serialized. If a dependency graph
is supplied, it must cover every referenced node, match the current package's
declared edges and the declarations of available typed upstream outputs, and
be acyclic before the callback runs. The legacy no-graph call remains valid;
it rejects direct self-dependencies but makes no complete-graph or global-cycle
guarantee. The core owns no registry or scheduler.

The concrete rollout consumer is the distinct, output-only readback package in
`scripts/design/group_level/replay_evidence_package_readback.py`. It selects
existing published channels with explicit references, artifact hashes, current
contracts and a complete graph. Its fresh outputs faithfully preserve the
selected observation/status/scale; stale/unavailable outputs have no
observation. Original free-space, distance and potential outputs remain intact;
geometry and trend use the same envelope reader as source adapters, preserving
their public/audit boundary. This exercises shared readback without defining a
new metric. The camera-plane free-space/distance snapshots cannot be mixed with
the retained world-plane potential/trend/geometry snapshots. Distance-to-potential
business integration remains unimplemented and needs its own agreed meaning.

Readback preserves saved source/output content without rerunning a formula.
Reexecution also preserves the original producer input order when that order
appears in an audit list: potential's historical `per_group` list came from
the pinned original `envelopes.json`, while runtime source storage sorts by
cache identity. Reexecuting sorted storage may permute that audit list; it is
not the byte-equivalent original-order replay. See the evidence record for the
observed failure and corrected comparison.

Implementation and saved-artifact verification are tracked in the existing
[integration plan](../../superpowers/plans/2026-11-09-evidence-package-integration-cleanup.md)
and [evidence record](evidence-package-integration-cleanup-2026-11-09.md).
