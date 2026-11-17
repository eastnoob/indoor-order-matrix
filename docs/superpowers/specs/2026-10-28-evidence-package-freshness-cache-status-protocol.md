# Evidence Package Freshness / Cache Status Protocol

- Date: 2026-10-28
- Status: Implemented for geometry and trend group evidence runners; UI remains deferred
- Scope: additive package contracts and read-only freshness reporting for group evidence
- Upstream boundary: `field-result-envelope/v1`

## 1. Purpose

The current group evidence deliveries are static run directories. They contain
serialized envelopes, source manifests, reports, and visual projections, but
there is no package-level contract that says how to reproduce a result or a
read-only check that says whether the saved result is still current. This
protocol adds that missing boundary without changing the existing
`FieldResultEnvelope`, recomputing evidence, or introducing a job/cache
framework.

The first version answers one UI question: **may this saved package be used as
the current result for the current scene/model request, or is recomputation
required?** The answer is status only. A separate user action or runner may
recompute later.

## 2. Existing contracts and concrete package inputs

`features/field_core.py:230` defines the immutable `FieldResultEnvelope`. Its
per-envelope cache identity is built at `features/field_core.py:322` from the
canonical target, `FieldQuery`, channel declarations, input/source
fingerprints, recipe, algorithm version, and schema version. That identity is
already the correct computation boundary for one target; it does not describe a
package or compare a saved identity with current inputs.

The current group packages are:

- `features/group_geometry_relation_field.py:48` emits one envelope per stable
  authored furniture-group pair. It uses three descriptive channels and keeps
  member-pair observations as `audit_only`; group aggregation remains
  deferred.
- `features/group_trend_alignment_field.py:57` emits one envelope per
  `furniture_group`. Its current public channels are
  `overall_group_axis` and `layout_axis`; member channels remain suppressed
  audit data.
- `scripts/design/group_level/render_group_geometry_relation_field_ifc.py`
  writes geometry `envelopes.json`, `plan_geometry.json`, pair JSON/SVG files,
  `report.json`, and `view_manifest.json`. Each pair currently serializes its
  envelope cache identity, but there is no package identity or freshness result.
- `scripts/design/group_level/run_group_trend_alignment_field_ifc.py` writes
  `source_manifest.json`, `description.json`, `envelopes.json`,
  `view_manifest.json`, and `report.json`. The v2 evidence document records
  that a fresh full IFC v2 run is still pending; historical v1 artifacts must
  not be treated as current v2 results.

The package contract must describe these existing inputs rather than inventing a
second field kernel.

## 3. Three distinct objects

### Evidence package

An evidence package is the computation contract plus the materialized result
artifacts for one package definition. It names the producer, target set,
dependency identities, active channels, recipe, algorithm/schema versions, and
artifact references. It may contain `FieldResultEnvelope` records, but it does
not replace them.

### Cache snapshot

A cache snapshot is one immutable materialization of an evidence package at a
particular dependency identity. The existing run directory is a snapshot. A
stale snapshot remains available for historical audit, but it is rejected as
the current result. File timestamps and run-directory names are not identity
inputs.

### Freshness checker

The freshness checker is a read-only comparison between a stored package
contract and the current dependency declaration. It returns a status payload
for the UI. It does not load IFC to recompute evidence, update the snapshot,
choose a target-level subset. The shared core provides a cycle validator for a
caller-supplied complete package dependency graph and rejects direct self-deps
on package outputs; it does not maintain a registry or schedule package
execution.

## 4. Package contract

The additive package record is JSON-safe and deterministic. Names below are
protocol fields, not a mandate for a new runtime registry:

```text
EvidencePackageContract {
  schema: "field-evidence-package-contract/v1",
  package_id: string,
  package_schema: string,
  producer: string,
  target_ids: [string, ...],
  dependencies: [
    {
      name: scene | model | source | plane | query | recipe | channels,
      fingerprint: string
    }, ...
  ],
  algorithm_version: string,
  schema_version: string,
  package_identity: string,
  invalidation_scope: "whole_package",
  artifacts: JSON mapping
}
```

`package_identity` is a digest of the package id, canonical target set,
dependency declarations, active channel declarations, recipe, algorithm
version, and schema version. Artifact paths, timestamps, visual renderer
metadata, and run-directory names do not change computation identity.

`producer` is an audit reference such as
`features.group_geometry_relation_field.build_group_geometry_relation_envelopes`
or the corresponding trend builder. It is not a dynamically resolved plugin
name.

The contract is stored beside the existing `envelopes.json` and manifests.
Existing artifacts remain valid historical snapshots; no migration or rewrite of
old snapshots is required for this protocol.

## 5. Dependency identity and edit/undo semantics

Every dependency that can change a result must be named and represented by a
content-derived fingerprint. The v1 comparison covers:

- `scene`: canonical authored scene identity, including relevant geometry,
  membership, semantic facts, and source bindings;
- `model`: the analysis-model/configuration identity used by the package;
- `source`: the underlying source identity, such as the current IFC SHA-256;
- `plane`: analysis-plane identity;
- `query`: domain, frame, height/demand context, tolerance, and semantic query
  revision;
- `recipe`: package representation and computation parameters;
- `channels`: admitted channel declarations and their parameters.

The package may alias two dependency roles to the same fingerprint when the
source provides one canonical identity, but the role must remain explicit. A
file mtime, process id, undo counter, or session-local revision is not a
content identity. Editing a scene and then undoing back to the same canonical
scene/model content therefore restores the original fingerprint and makes the
snapshot fresh again.

The existing `FieldQuery.revision` participates in envelope query identity.
For this protocol it must describe a semantic query contract, not a transient
UI edit sequence, or edit/undo would create a false stale result.

## 6. Freshness and cache status

The checker returns the following UI-facing shape:

```text
EvidencePackageStatus {
  schema: "field-evidence-package-status/v1",
  package_id: string,
  cached_package_identity: string | null,
  current_package_identity: string | null,
  freshness: fresh | stale | unavailable,
  recompute_required: boolean,
  reasons: [
    {
      code: package_missing | package_invalid | scene_changed | model_changed |
            source_changed | plane_changed | query_changed | recipe_changed |
            channel_set_changed | schema_changed | algorithm_version_changed,
      dependency: string | null,
      cached: string | null,
      current: string | null
    }, ...
  ],
  affected_targets: [string, ...],
  invalidation_scope: "whole_package",
  algorithm: {
    status: same | changed | unknown,
    cached_version: string | null,
    current_version: string | null,
    recompute_required: boolean
  }
}
```

Rules:

1. Matching package identity and readable referenced artifacts produce
   `fresh`, `recompute_required=false`, empty `reasons`, and empty
   `affected_targets`.
2. Any scene, model, source, plane, query, recipe, channel, or schema mismatch
   produces `stale` and `recompute_required=true`. Multiple mismatches may be
   reported together.
3. Missing or unreadable contract/artifacts produce `unavailable`,
   `recompute_required=true`, and `package_missing` or `package_invalid`.
4. v1 invalidation is whole-package. For stale or unavailable results,
   `affected_targets` is the sorted union of cached and current target ids.
   This intentionally reports all 666 geometry-pair targets or all 37 trend
   targets when the package-wide dependency changes; it does not infer a
   target-level dependency graph.
5. `algorithm_version_changed` is reported separately from scene/model
   changes in `reasons` and the `algorithm` object. In v1 any algorithm
   mismatch is conservatively stale and requires recomputation; no compatible
   migration is inferred. A renderer-only change is outside computation
   freshness and must not invalidate the envelopes.
6. Package freshness does not rewrite an envelope's `raw_status`. A fresh
   package can contain `partial`, `invalid`, `not_available`, or
   `not_evaluated` target results, and those states remain visible to the UI.

Package freshness and channel status remain separate dimensions. Cross-package
readback binds a source package output to a target and channel. When the source
package is stale or unavailable, the readback's effective availability is
`not_available`; the source channel's original status and observation remain
attached for historical audit only and cannot be used as current numeric input.
When package freshness is fresh, the source channel status passes through
unchanged. Package-specific consumers decide what `partial`, `outside`,
`ambiguous`, or domain states such as an unreachable route mean.

The UI must receive at least `recompute_required`, `reasons`, and
`affected_targets`; it must not infer freshness by comparing visual manifests or
by treating a per-envelope `computed` status as package freshness.

## 7. Ownership boundary

The shared field core owns deterministic canonicalization, package identity
construction, status comparison, reason vocabulary, target sorting, and the
whole-package invalidation rule. It continues to own the existing immutable
`FieldResultEnvelope` and its per-envelope cache identity.

Each package owns its dependency declarations and target enumeration. The
geometry package declares the IFC/scene/source boundary, analysis plane and
tolerance, three active descriptive channels, recipe, and stable group-pair
targets. The trend package declares the corresponding source/plane/query
boundary, two active channels, suppressed audit descriptors, recipe, and
stable furniture-group targets. Geometry rules remain in
`group_geometry_relation_field.py`; trend rules remain in
`group_trend_alignment_field.py`.

This split keeps package-specific facts out of `field_core.py` without adding a
universal plugin registry, job/result registry, or centrally maintained
dependency graph. Callers that execute multiple packages supply their graph to
the shared cycle validator.

## 8. Out of scope and owner decisions

This protocol does not authorize:

- automatic recomputation or background jobs;
- cache storage, eviction, or synchronization policy;
- target-level invalidation or a target-level dependency graph;
- candidate inference, aggregation, membership, potential, strength, or winner
  selection;
- changes to `FieldResultEnvelope`, `room_analysis_model`, or factual IFC data;
- treating historical v1 artifacts as current v2 evidence.

The first implementation uses the runner's declared model/configuration
fingerprint and checks referenced artifacts for readability. A canonical
interactive model fingerprint and deeper artifact integrity validation remain
open for a future UI consumer. Algorithm mismatch remains a conservative
stale reason until compatibility policy is explicitly defined.

## 9. Acceptance criteria for this spec

1. Package contract, cache snapshot, and freshness checker remain separate
   concepts.
2. Scene/model, source, plane, query, recipe, channel, and schema changes are
   explicit invalidation reasons.
3. Content-derived identity makes edit-then-undo fresh again.
4. Algorithm-version mismatch is reported separately and conservatively stale.
5. UI status contains `recompute_required`, `reasons`, and
   `affected_targets`.
6. v1 invalidates the whole package and retains stale snapshots for audit.
7. No automatic recomputation, cache storage mechanism, or local dependency
   graph is introduced by the protocol.

The shared checker, both runner integrations, focused invalidation tests, and a
real pinned-IFC in-memory rotation diagnostic implement this protocol. UI
integration, automatic recomputation, and cache storage policy remain deferred.
