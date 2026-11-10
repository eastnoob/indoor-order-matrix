# Evidence Package Structure

An evidence package groups related channels for one materialized analysis
snapshot. Each channel keeps its own meaning, method, inputs, observation,
status and scale. Grouping channels does not combine them into a score.

```text
Evidence package
├── Publication records
│   ├── contract: target/query/scope/plane, recipe and input fingerprints
│   ├── status: freshness, recompute reasons and affected targets
│   └── manifest: published data and existing visualization locators
├── EvidencePackageOutput
│   ├── source_envelopes: complete immutable original evidence
│   ├── outputs: additive channels with method, input lineage and results
│   ├── dependencies: explicit package/output/target/channel addresses
│   └── output_identity: computation identity
└── Saved JSON
    └── payload_fingerprint: complete serialized content fingerprint
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
