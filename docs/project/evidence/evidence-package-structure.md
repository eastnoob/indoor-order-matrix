# Evidence Package Structure

An evidence package groups related channels for one materialized analysis
snapshot. Each channel keeps its own meaning, method, inputs, observation,
status and scale. Grouping channels does not combine them into a score.

## Current development boundary — clarified 2026-11-17

This guide and the [minimal authoring template](../../superpowers/specs/2026-10-30-evidence-package-minimal-standard.md)
describe the accepted and pushed A/B/C implementation. The [C handoff](../../superpowers/handoffs/2026-11-15-plan-c-complete.md)
records acceptance and remaining limits. The [owner integration plan](../../superpowers/plans/2026-11-17-abc-owner-integration.md) tracks adoption into the root separately. Earlier dated checkpoints below retain their history.

| Component | Responsibility | Boundary |
| --- | --- | --- |
| Package entry / builder | Prepare declared inputs, parameters and algorithms; `run_*` owns reuse/calculation and storage orchestration. | Future UI calls the business entry; no new manager or inheritance tree is required. |
| Numerical functions / existing adapter | Compute package-specific facts and supply source envelopes. | Model/session access stays in its existing layer; pure features do not import live Blender/session code. |
| `EvidencePackage` | `evaluate()` validates/publishes source and additive channels; `process_output()` processes an existing raw result. | These are its two business methods, not all package-level APIs. This frozen configurable template is not a required superclass or a model/cache/UI manager. |
| Parameter schema / snapshot | Declare legal values and impact; record immutable effective values and sources. | Resolve/bind parameters in the package entry or builder; `evaluate()` has no separate parameter-dict argument. |
| Optional processor | Apply a declared recipe to validated fresh raw. | Publish processed separately; never replace raw or choose a universal normalization. |
| Existing storage / cache modules | Validate, save and reuse exact results through package-owned contracts. | Reuse existing backends; no per-package cache framework is required. |

Inputs are **caller-prepared facts for the declared analysis scope**, plus
explicit optional upstream results. A scope may be local or room-wide. Complete
source retention means all supplied evidence, not the entire model. Keep the
context the algorithm needs: local paths still require obstacles/domain, and
complete-scope processing must retain its declared members. The shared callback
receives `FieldResultEnvelope` records, or `EvidencePackageInput` for the context
callback; existing outer facades may accept their own bundle/context. There is
no automatic whole-model/subset input router.

Composition is the current design. This responsibility map is not a full
repository coupling/quality audit and does not call for an OOP rewrite.

### Parameters and the `exposed` convention

Reuse `features/evidence_package_parameters.py`: `ParameterSpec` declares name,
type, unit, default/required, legal values and impact. `ParameterSchema.resolve()`
validates requests, expands defaults and records request/default sources in an
immutable `ParameterSnapshot`. `capture_calculated()` requires complete
historical values and explicit sources; it never fills gaps from today's defaults.

`exposed=True` labels a parameter for a future UI adjustment panel;
`exposed=False` omits that adjustment entry by convention. Current `resolve()`
accepts otherwise valid programmatic overrides for either value. This is not a
permission boundary, does not generate a UI and needs no separate `hyperparameter`
field. Keep type/range/choice validation. Existing schema-less processors remain
supported; not every numeric constant has become a caller-adjustable parameter.

### Semantic outputs and processing layers

The two core methods below describe **raw and processed layers**. C additionally
offers independent **semantic kinds**: `euclidean_distance`, `path_distance`,
`axis_potential` and opt-in `distance_modulated_axis_support`. These are separate
axes, not a fixed two-result limit for every package.

`features/output_port_cache.py` supplies `OutputPortContract`, `OutputPortRef`
and publication/run records. Each contract selects exact target/channel
addresses, parameter names and actual upstream references. Distance entries are
`run_group_distance_ports` and `run_euclidean_processed_port` in
`features/group_distance_output_ports.py`; axis/modulation uses
`run_group_axis_output_ports` in `features/group_axis_output_ports.py`.
They reuse B's `CacheStore`, addressed by
`source / package / semantic-output / raw-or-processed / identity`.
Route-only changes preserve independent Euclidean results; modulation depends
on processed Euclidean and pure-axis results, not path. Selected parameter names
control relevant reuse checks while full historical parameter audit is retained.

Existing combined APIs and raw/processed serializers remain compatible. The
combined runners return the mapping below; semantic cache runners return
`PortRun` records containing a publication, `cache_hit`, `status`, `cache_status`,
`cache_reuse` and `cache_location`, by semantic output where applicable. Do not
assume all entry points have one return type. Pure evaluation and existing
nonpersistent calls need no persistent store; C cache runners require their
explicit `CacheStore`. Intermediate-stage runtime remains design-only; no UI
is implemented here.

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

The public entries are `run_free_space_package` in
`adapters/free_space_evidence_package.py`, `run_group_distance_package` in
`features/group_distance_evidence_package.py`, and
`run_group_axis_potential_package` in `features/group_axis_potential_field.py`.
They return `raw_output`, `processed_output`, `contract`, `status`, `cache_key`,
`cache_hit` and `cache_status`. `status` describes the returned publication;
`cache_status` retains the earlier reuse/recompute decision and its reasons and
affected targets. A potential input-cache key may differ from the returned
publication contract identity, which uses the actual output targets.

`features/evidence_package_storage.py` supplies small JSON receipt and atomic
storage functions. The free-space adapter retains its authenticated document
boundary, separates the content storage key from the legacy publication ID,
and reconstructs current request metadata while retaining the original
calculation reference on revision-only reuse. Pure feature packages do not
import that adapter. Existing `evaluate` APIs remain available.

```text
Caller -> package run_* entry
          |-- algorithm -> raw publication ---------> explicit raw selection
          |-- storage adapter <-> validated cache
          `-- optional processor -> processed ------> explicit processed selection
                                      |
                              separate saved JSON
```

Implementation and independent acceptance are tracked in the
[lifecycle plan](../../superpowers/plans/2026-11-12-evidence-package-lifecycle.md).
The lifecycle implementation is locally verified: SPEC PASS / QUALITY PASS,
353 combined tests passed and one unchanged hierarchy test excluded, with the
full retained hierarchy covered by a separate independent 46-pass run.

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
unchanged. This identity is not a live-currentness receipt. A processor must use
the supplied raw publication and declared
parameters, rather than hidden mutable inputs, and version changes to its
behavior.

The original [optional-processing checkpoint](../../superpowers/plans/2026-11-12-evidence-package-optional-processing.md)
provided runtime processing. The lifecycle extension adds a separate
`evidence-processed-output/v1` serializer/decoder and explicit processed
cross-package references. Saved processed JSON requires both the processing
identity and a full payload fingerprint; decoding binds the complete supplied
raw publication and reuses channel validation without executing a callback.
Package entries cache successful processed results separately, against the
current raw content and processor ID/version/parameters. Processing errors
remain empty results and are not reused as successful cache hits. No default
formula is selected.

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
└── Optional processed port: EvidenceProcessedOutput
    ├── raw_output_identity / raw_payload_fingerprint
    ├── processor identity / version / parameters / processing_identity
    ├── outputs, or fixed error_code with no channels
    └── separate saved JSON / complete payload_fingerprint
```

The channel responsibilities use existing fields, not additional nested types:

| Responsibility | Existing representation |
| --- | --- |
| Algorithm/recipe | Channel provenance `method`, `algorithm_version`, `schema_version` and formula when declared; otherwise package `output_function` and `output_function_version`, scoped to the named channel. Source records may explicitly inherit top-level envelope provenance. |
| Actual inputs | `derived_from`, source-envelope `cache_identity` input/source/query/recipe/channel fingerprints, and explicit external dependencies. A package such as potential may declare `distance_modulation` as a typed processed dependency while retaining the distance package's raw and processed ports separately. |
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
`target_identity`, `channel` address and keyword-only `port="raw"` by default.
Historical raw JSON references retain exactly their original four fields.
A processed reference additionally requires `port="processed"` and the exact
`processing_identity`; its `output_identity` still identifies the raw
publication. Two targets may publish the same channel name and may both be
consumed, as may both ports at the same address. Readers select only the named
port, validate its raw-content binding and never fall back. The resolver
separately gates caller-supplied freshness; fresh
channels retain their observation, status and scale. Stale/unavailable channels
provide no usable channel; an available typed source contributes only an
observation-redacted audit record. Every derived output that uses such a
dependency must have `observation=None`, including `partial` outputs. Missing
or mismatched references are rejected, rather than filled with zero.

Published dependencies keep compact references; evaluation-time
`source_output` and `source_processed_output` handles are not recursively
serialized. Graph declarations remain on the raw `source_output`. If a dependency graph
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
the retained world-plane potential/trend/geometry snapshots. That 2026-11-10
output-only rollout did not implement distance-to-potential business integration.
The current separately opted-in distance modulation is described above; it does
not permit mixing incompatible analysis planes.

`consume_saved_evidence_package` keeps its original raw selections and accepts
`processed_path`, a separate `expected_processed_sha256`, independently supplied
`current_processing_identity`, and `processed_selections` triples
`(target_identity, saved_channel, output_alias)`. Aliases keep consumer addresses
distinct when raw and processed ports share a target/channel. Missing or changed
current recipe context redacts processed observations while independently fresh
raw selections remain usable. Current-source/contract checks and explicit graph
validation apply to both ports; decoding never infers currentness from saved
metadata or executes the processor.

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
