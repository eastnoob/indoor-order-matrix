# Explicit intermediate contract — design only

Date: 2026-11-16. Decision: defer intermediate runtime integration.

The [fresh C review](../reviews/2026-11-15-plan-c-fresh-grill.md) found no
completed non-output stage that needs separate persistence. Selected output
reuse and the existing input-bound route checkpoints cover the current need.
This document records the boundary required by [Plan C Task 7](../plans/2026-11-15-output-port-and-intermediate-cache.md).
It introduces no production class, serializer registry, directory creation,
decorator or second storage backend.

## Existing boundary

Plan A supplies `ParameterSnapshot.to_json()`, immutable expanded audit and
independently resolved owner declarations. Plan B supplies `CacheStore`,
`SourceBinding`, identity locks, complete publication, integrity checks,
authentication domains, exact deletion, derived dependency state, rebuildable
indexes and validated migration. Its current `CacheAddress` identifies only
`source_fingerprint`, `package_id`, `output_port`, `layer` (`raw` or `processed`)
and `identity`. It has no intermediate kind or stage address.

C's semantic outputs remain package outputs. An intermediate would instead be
a package-declared completed stage with a stable restoration contract. Adding
it requires a separately reviewed B address/storage extension; a stage must
not be disguised as an output port or a third output layer.

## Future declaration and identity

The owning package declares the actual producer function, stable `stage_id`,
stage schema, explicit input projection, selected parameters, complete upstream
references, algorithm version, serializer and completion validation. Identity
uses the project's canonical JSON/SHA-256 helpers and binds:

- The distinct intermediate kind, factual `source_fingerprint`, package and stage.
- Stage schema and algorithm versions, exact declared input fingerprints.
- A versioned parameter projection with declared `selected_names`, relevant
  recompute-required effective values and their value contracts.
- Exact upstream references, including their full source/package/kind/version
  address and payload fingerprint; raw/processed layers remain explicit for
  semantic-output dependencies.
- Serializer ID/version and any geometry/array library or format versions
  required for deterministic restoration.

Paths, timestamps, current UI selection and parameter source labels stay out
of this identity. Full `ParameterSnapshot.to_json()` remains immutable audit;
hashing the whole owner snapshot would couple unrelated parameters. Warning
and metadata parameters retain their declared comparison behavior without
creating a new computation version.

The future frozen reference is
`IntermediateRef(source_fingerprint, package_id, stage_id, identity, payload_fingerprint, serializer_id, serializer_version)`.
`identity` names declared computation inputs; `payload_fingerprint` separately
authenticates exact saved bytes. Neither proves that current owner declarations
or upstream inputs still match. A read must validate those independently before
returning a reusable value, as well as storage integrity and dependency presence.

## Receipt and payload

This JSON is an illustrative field layout, not a valid published receipt or a
test fixture. Descriptive hash strings require real canonical SHA-256 values.
The empty maps illustrate a hypothetical owner with no parameters.

```json
{
  "schema": "intermediate-receipt/v1",
  "kind": "intermediate",
  "source_fingerprint": "sha256-of-factual-source",
  "package_id": "owning-package",
  "stage_id": "declared-completed-stage",
  "stage_schema_version": "stage-data/v1",
  "identity": "sha256-of-declared-stage-inputs",
  "input_fingerprints": {"geometry": "sha256-of-selected-geometry"},
  "parameter_projection": {
    "schema": "stage-parameters/1",
    "selected_names": [],
    "values": {},
    "value_contracts": {}
  },
  "parameter_snapshot": {
    "package_id": "owning-package",
    "config_schema_version": "package-parameters/1",
    "effective_parameters": {},
    "calculated_parameters": {},
    "parameter_sources": {},
    "parameter_impacts": {},
    "parameter_value_contracts": {},
    "parameter_fingerprint": "sha256-of-owner-computation-projection"
  },
  "upstream_refs": [],
  "algorithm_version": "stage-algorithm/1",
  "serializer": {"id": "json", "version": "1"},
  "payload": {
    "path": "payload.json",
    "format": "json",
    "size": 2,
    "fingerprint": "sha256-of-exact-bytes"
  },
  "status": "complete"
}
```

`schema` validates the receipt format; `stage_schema_version` describes stage
data. `input_fingerprints`, `parameter_projection` and `upstream_refs` declare
its actual dependencies. The expanded snapshot preserves calculated values,
requested effective values at publication, sources, impacts and type/unit/
nullable contracts without supplying current defaults during restoration.
`serializer` names the supported reader; `payload` records a relative file,
format, exact byte size and digest. `complete` is admitted only after payload
and owner validation; it is not a persisted assertion of current freshness.

Use JSON for small structured records. Arrays or geometry require a declared
stable binary/structured serializer and validation of versions, shape/units and
semantic invariants on restoration. Do not use untrusted pickle as the default.
Verify saved bytes before decoding or adding runtime defaults. Unsupported
schemas, serializers, damaged bytes or unavailable dependencies cannot become
numeric fallbacks.

## Storage and lifecycle after adoption

The reserved model-side namespace is
`sources/<source-fingerprint>/intermediates/<package-id>/<stage-id>/<identity>/`
under the existing sidecar root. A locator change alone does not change stage
identity. The adoption plan must extend B's address dispatch, validators and
dependency traversal for this distinct kind and reuse its existing locks,
staged atomic publication, payload verification and authentication domains.

Extend `CacheStore.list`, `delete_exact`, `rebuild_index` and `migrate_to` for
the new namespace in that same reviewed change. The index stays advisory and
rebuildable; receipts and verified payloads remain authoritative. Exact deletion
removes one version, preserves siblings, and derives dependent entries as
orphaned/unavailable without rewriting signed receipts or deleting descendants.
Owner currentness validation remains separate from recursive storage checks.
Listing may quarantine invalid entries, so evidence inventories inspect
byte-verified copies rather than assuming listing is read-only.

Relocation must copy and validate original bytes, complete references and
required authentication material before reuse. Conflicts cannot overwrite
valid destination entries, partial failures remain explicit, and the old root
is retained. Use `CacheStore.migrate_to`; do not add another migration writer.
SQLite would remain an optional advisory catalog only if measured needs justify
it, never the authority for stage content.

## Checkpoints and adoption gate

Run state belongs under `runs/<run-id>/checkpoints/`. It may be mutable or
incomplete and resumes only after exact input, parameter/policy, upstream and
algorithm bindings pass the existing owner checks. Copying a checkpoint or
renaming its directory does not make it an intermediate or authorize resume.
Promotion requires an explicitly declared completed stage, immutable payload,
validated receipt and a new publication in the intermediate namespace.

A later small adoption plan must name a real producer and consumer, expected
reuse/cost benefit, serializer, invalidation boundary, B API extension and
independent acceptance. It must prove restart restoration without producer
calls, changed-input rejection, corruption rejection, exact deletion/dependency
effects and relocation reuse. No arbitrary reuse-count threshold is required.

For current C, runtime adoption is deferred. No `IntermediateRef` Python symbol,
intermediate store API or intermediate test suite exists or is claimed tested.
This decision does not defer C's semantic-output implementation or its required
distance, processing, modulation, deletion and migration checks.
