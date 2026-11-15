# Package-Owned Parameters and Model-Side Cache Design

## Goal

Give every evidence package an explicit, typed parameter boundary and make its immutable results reusable beside the IFC or Blender model that produced them. A cache directory move must migrate validated results without changing calculation identity or forcing a recomputation.

This master design is delivered through three sequential implementation plans. Plan A covers typed configuration and receipt metadata. Plan B follows A and covers the model-side cache store, safe migration, and cache lifecycle. Plan C follows B and covers output-port identity decomposition and the explicitly declared intermediate-product boundary. Plan C begins with a fresh Superpowers review so its scope can become either a new plan or a narrowly scoped repair plan based on the accepted A/B results.

## Current Context

The repository already has three persistence families:

- `features/evidence_package_storage.py` stores ordinary evidence package receipts and processed outputs.
- `adapters/free_space_evidence_package.py` stores authenticated free-space receipts and processed results.
- `adapters/blender_analysis_session.py` stores Blender content cache entries through its wire format.

The current evidence package identities already include substantial input and recipe information. `EvidenceOutputProcessor.parameters` is frozen and persisted in processed output receipts. The missing boundary is a common package-owned configuration snapshot and a common storage/migration layer. The current `whole_package` invalidation also couples semantically separate distance outputs.

The current project uses Pixi and Python 3.12. Version and workspace management uses Jujutsu (`jj`) first. The owner worktree and unrelated dirty work must remain untouched during design and implementation.

## Design Principles

1. **Package ownership**: a package declares and validates its own parameters. A downstream package may select an upstream `ResultRef`, but cannot modify the upstream package's parameters or saved bytes.
2. **Identity by effective computation inputs**: cache identity includes the canonical `recompute_required` parameter projection, consumed input fingerprints, upstream result identities, algorithm versions, and schema versions. Every effective value remains in the audit snapshot. Warning-only values, parameter source labels, paths, timestamps, and UI selection state do not enter calculation identity.
3. **Output defines cache kind**: semantic outputs are the durable cache kinds. Raw and processed are calculation layers of one semantic output; they are not automatically separate business outputs.
4. **Sidecar locality**: the default cache lives next to the model and moves with it. The sidecar path is a locator, not a calculation input.
5. **Explicit intermediate caching**: a package may declare a reusable intermediate stage, but no generic decorator may guess which function calls are safe to cache.
6. **Evidence before reuse**: malformed, partial, unauthenticated, stale, or dependency-missing files are never exact cache hits.
7. **Recoverable progress**: each implementation gate has an isolated jj workspace, a local commit, an independently testable acceptance boundary, and a reversible history point.

## Scope and Non-Goals

### In scope

- A frozen typed configuration boundary for each package that chooses to expose parameters.
- Canonical parameter normalization, validation, fingerprints, and receipt snapshots.
- A thin `CacheStore` for sidecar paths, atomic receipt/payload writes, locks, migration, listing, deletion, and index rebuilding.
- Sidecar migration that copies validated cache material, including free-space authentication material, without changing identities.
- Lifecycle states and exact-hit versus migrated-reuse reporting.
- A stable contract for output-port identities, plus a documented intermediate boundary whose runtime implementation is conditional on an accepted real need.
- Regression tests for parameter round trips, cache migration, corrupted receipts, cache-directory changes, and the `1 → 2 → 1` reuse path.

### Deferred from Plan A

- A complete GUI or parameter platform.
- SQLite as the authoritative payload store.
- A decorator that automatically caches arbitrary functions.
- Bulk import of historical `outputs/design/...` JSON without validated receipts.
- Opening `epsilon` as a general user control.
- Cache directory migration and locking (Plan B).
- Output-port decomposition and reusable intermediate integration (Plan C).
- Changing the mathematical distance, free-space, or potential formulas.

### Plan boundaries

**Plan A — package-owned parameters and receipts.** Establish typed configuration helpers or package-local config records, canonical effective parameter snapshots, parameter fingerprints, schema versions, source labels, and validation. Preserve existing cache behavior and package identities where possible. The deliverable is independently testable receipt metadata that does not yet require a new storage backend.

**Plan B — model-side CacheStore and migration.** Add the thin persistence layer for sidecar resolution, atomic writes, per-identity locks, receipt/payload verification, listing, exact deletion, index rebuilding, lifecycle states, and migration. Migrate validated existing cache material without recomputation, including free-space authentication material. Plan B starts from Plan A's accepted receipts and must not invent a second parameter identity format.

**Plan C — output ports and conditional intermediates.** After Plan B acceptance, run a new Superpowers brainstorming/Grill pass over the actual receipts and dependencies. Then implement the smallest accepted change that separates independent output identities and proves that deleting or changing one output does not corrupt unrelated outputs. Keep `IntermediateRef` and reusable intermediate persistence in the long-term design unless that review accepts a concrete package need. C may be replaced by a repair plan; it must not be assumed complete by A or B.

## Package Configuration Contract

Each package may expose a frozen typed configuration object. The object owns:

- parameter name and Python type;
- default value;
- SI unit or explicit dimensionless marker;
- finite range or enumeration validation;
- whether the parameter is user-exposed;
- impact class: `recompute_required`, `reuse_with_warning`, or `metadata_only`;
- configuration schema version.

The package resolves a caller's partial values into a complete `effective_parameters` record. Resolution rejects unknown fields, missing required values, booleans used as numbers, `NaN`, infinity, negative values where prohibited, and noncanonical units. Canonical JSON uses one stable representation for equivalent values.

The sidecar may contain an editable current profile, for example `settings/<package_id>.json`. A profile is an input convenience and can be changed without mutating any historical result. Every typed immutable output receipt stores the complete resolved snapshot. The constrained distance snapshot has this shape; the real fingerprint is calculated from its computation projection:

```json
{
  "package_id": "group-walk-distance",
  "config_schema_version": "group-distance/parameters/1",
  "effective_parameters": {
    "clearance_mode": "constrained",
    "min_left_m": 0.225,
    "min_right_m": 0.225,
    "min_total_m": 0.55
  },
  "calculated_parameters": {
    "clearance_mode": "constrained",
    "min_left_m": 0.225,
    "min_right_m": 0.225,
    "min_total_m": 0.55
  },
  "parameter_sources": {
    "clearance_mode": "request",
    "min_left_m": "default",
    "min_right_m": "cli",
    "min_total_m": "cli"
  },
  "parameter_impacts": {
    "clearance_mode": "recompute_required",
    "min_left_m": "recompute_required",
    "min_right_m": "recompute_required",
    "min_total_m": "recompute_required"
  },
  "parameter_value_contracts": {
    "clearance_mode": {"type": "str", "nullable": false, "unit": "dimensionless"},
    "min_left_m": {"type": "float", "nullable": false, "unit": "m"},
    "min_right_m": {"type": "float", "nullable": false, "unit": "m"},
    "min_total_m": {"type": "float", "nullable": false, "unit": "m"}
  },
  "parameter_fingerprint": "..."
}
```

`parameter_sources` is audit metadata. It does not affect identity. `calculated_parameters` in a historical receipt are authoritative for that result; `requested_parameters` are current user intent and may be compared to show `reuse_with_warning`. Persisted value contracts use only restricted type tags, nullable flags and canonical units. Current reuse compares their complete declarations and impacts with an independently resolved current owner snapshot; a historical file cannot certify its own schema or live currentness.

Changing a default value changes the effective configuration for new runs. Existing receipts retain their expanded values and remain interpretable. A semantic schema change increments `config_schema_version` and prevents accidental reuse across incompatible meanings.

Initial package ownership is:

| Parameter | Owning package |
| --- | --- |
| left/right/total clearance | `group_distance` route output |
| grid spacing | `free_space` |
| height band, slab, analysis plane | `free_space` request |
| geometry/topology tolerances | `free_space` |
| distance modulation switch | `group_axis_potential` |
| `epsilon` | the proximity processor that uses it; fixed trial value initially |

Derived scope statistics (`min`, `max`, `median`), source fingerprints, algorithm versions, and package identities are not user parameters.

## Result and Output-Port Identity

An output identity is a canonical digest of:

- package id and output port;
- source fingerprint and external dependency fingerprints;
- the output's recompute_required effective parameter projection and configuration schema version;
- upstream `ResultRef` identities, when present;
- algorithm and output schema versions;
- declared channel or target scope.

The identity excludes cache directory, source path, display labels, timestamps, parameter source labels, and current UI selection.

The target dependency boundary is:

```text
free_space(effective parameters A)
        ↓ immutable ResultRef
group_distance(effective parameters B)
        ↓ immutable ResultRef
group_axis_potential(effective parameters C)
```

For the distance outputs, `euclidean_distance` should not depend on route clearance or free-space search, while `path_distance` should depend on the selected free-space result, clearance policy, and route algorithm. An output-port split may be implemented after the first plan; the contract must be designed so that a path parameter change does not require an unrelated Euclidean result to change identity.

## Sidecar Layout

For a saved model:

```text
apartment.ifc
apartment.order_analyzer/
```

or:

```text
apartment.blend
apartment.order_analyzer/
```

The initial target layout is:

```text
apartment.order_analyzer/
  manifest.json
  index.json
  settings/
    <package-id>.json
  auth/
    <key-id>/.free_space_cache_key
  locks/
  quarantine/
  sources/
    <source-fingerprint>/
      source.json
      outputs/
        <package-id>/
          <output-port>/
            <raw-or-processed>/
              <version-key>/
                receipt.json
                payload.json | payload.bin
      intermediates/
        <package-id>/
          <stage-id>/
            <version-key>/
              receipt.json
              payload.json | payload.bin
      runs/
        <run-id>/
          logs/
          checkpoints/
          scratch/
```

`manifest.json` records source and external dependency fingerprints, cache format version, producer/tool versions, and migration history. `index.json` is an advisory, rebuildable catalog. Receipt files and payload fingerprints are the content authority. The `intermediates/` tree is reserved documentation, not a directory or API that A/B must create. Source namespaces do not change when only a request parameter changes.

For unsaved Blender scenes, a temporary sidecar is allowed until the model is saved; saving the model migrates the temporary material to the model-side sidecar. A read-only model directory requires an explicit alternate cache location. Moving or renaming the model does not change identity when the sidecar moves with it.

## CacheStore Boundary

`CacheStore` is infrastructure, not an evidence-package framework. It provides:

- sidecar and source-root resolution;
- atomic write through temporary files and rename;
- per-identity locking to prevent concurrent duplicate writes;
- receipt and payload fingerprint verification;
- exact `get`, `list`, `delete`, `copy/migrate`, and index rebuild operations;
- quarantine of malformed, partial, or unverifiable entries.

The package remains responsible for:

- typed configuration and default resolution;
- package identity and dependency selection;
- output semantics;
- serialization and deserialization of its payload;
- validation of its own contract and upstream references.

A common receipt shell is:

```json
{
  "schema": "cache-receipt/v1",
  "source_fingerprint": "...",
  "package_id": "group_distance",
  "output_port": "path_distance",
  "layer": "raw",
  "identity": "...",
  "contract": {
    "effective_parameters": {},
    "parameter_fingerprint": "...",
    "config_schema_version": "...",
    "dependencies": [],
    "algorithm_version": "...",
    "schema_version": "..."
  },
  "upstream_refs": [],
  "payload": {
    "path": "payload.bin",
    "format": "json",
    "size_bytes": 123,
    "fingerprint": "..."
  },
  "status": "complete"
}
```

Small payloads may remain JSON. Large lattices, arrays, and geometry records may use a separate binary or structured payload file; the receipt always declares its format, size, and fingerprint.

## Intermediate Products

Plan C re-evaluates whether any completed intermediate needs independent reuse. The default is to document the boundary without adding an unused class, serializer registry or runtime store. If a concrete need is accepted, the package declares a stable stage id, serializer, dependencies, effective parameters, algorithm/schema versions, and completion status; its `IntermediateRef` is immutable after publication.

Intermediate products are distinct from run-local checkpoints:

- **Semantic output**: long-lived public result, indexed under `outputs/<package>/<port>/<layer>/`.
- **Reusable intermediate**: package-declared completed stage, indexed under `intermediates/`.
- **Checkpoint/scratch**: mutable run state, valid only for exact input/policy/upstream/algorithm fingerprints; never treated as a completed output.

SQLite is deferred. If introduced later, it may index receipts, dependencies, status, and garbage-collection queries. Payload files and receipt fingerprints remain the content source of truth.

## Migration and Lifecycle

Changing the cache directory is a storage migration, never a computation input change. Migration:

1. Reads the old manifest, receipts, payloads, indexes, logs, checkpoints, and authentication material.
2. Validates cache identity, contract, payload fingerprint, upstream references, authentication, and supported schema.
3. Copies validated material to temporary files in the new sidecar and atomically publishes it.
4. Rebuilds or updates the new index with source, destination, verification, and migration status.
5. Reuses the copied identity before scheduling computation.

The free-space directory authentication key (`.free_space_cache_key` in the current implementation) must move with the authenticated cache. Distinct old and destination keys coexist under explicit key IDs; migration cannot overwrite a destination key or resign the retained bytes. Copying JSON without the matching key is an invalid migration.

Migration is allowed to partially succeed. A failed output is marked `migration_failed` or `unavailable`; successful independent outputs remain reusable. The old directory is retained until validation completes and is not deleted automatically.

Lifecycle states are:

`running`, `complete`, `failed`, `stale`, `orphaned`, `quarantined`, `migration_failed`, and `unavailable`.

Only a complete verified receipt with matching calculation inputs and available dependencies is a calculation hit. Warning-only differences remain reusable with explicit calculated/requested values and `exact_match=False`. `migrated_reuse` and `legacy_adopted` describe lookup provenance, separate from stored lifecycle status and the existing freshness mapping. Historical evidence remains `historical` and cannot silently become current. Deleting an upstream version derives dependent entries as `orphaned` or `unavailable`; it does not rewrite signed receipts or payloads.

The sidecar must survive a missing or corrupt `index.json` by scanning receipts. Partial files from a crash are cleaned or quarantined and never treated as hits. A per-identity lock prevents two processes from publishing the same identity concurrently.

## Legacy and External Dependencies

Historical `outputs/design/...` JSON without a complete receipt, contract, and fingerprint is not automatically imported into the new cache. It remains historical evidence unless an explicit validated legacy importer creates a new receipt.

The source manifest records content fingerprints for the IFC/Blender source and every external file that affects analysis. Display paths and modification times are retained for diagnostics but are not identity inputs.

## jj Safety and Rollback Design

Design and implementation use jj workspaces derived from the accepted parent, without modifying the owner worktree. The design workspace records the spec, A, B, C and rollout notes as local documentation checkpoints. Implementation uses a fresh workspace from the approved spec/plan commit, with one commit per independently testable gate:

1. typed configuration and receipt snapshots;
2. `CacheStore` sidecar persistence and locking;
3. migration and free-space authentication preservation;
4. lifecycle/index/delete behavior and regression tests;
5. semantic-output independence after C's fresh review; intermediate runtime support only if that review accepts a real need.

Before each gate, record the workspace path, parent revision, dirty-file manifest, and intended files. After each gate, run the focused Pixi tests, inspect `jj diff`, and create a local jj commit. Preserve a failed candidate before recovering in a fresh task workspace from its accepted parent, or restore only named task files after checking for unrelated edits. Inspect `jj op log` for diagnosis; do not run a repository-wide undo or operation restore across other active workspaces. B starts from the actual accepted A implementation commit, and C from the actual accepted B implementation commit. No push, merge, or owner-worktree integration is part of this spec.

## Acceptance Conditions

The design is implemented only when all of the following have observable evidence:

- A package rejects invalid or unknown parameter values and emits a complete canonical effective-parameter snapshot.
- Equal effective values from default, CLI, and GUI sources produce the same parameter fingerprint.
- Different computation-affecting effective values produce different identities; restoring an old value reuses its old receipt without recalculation. Warning-only and metadata-only changes retain calculation identity and historical values.
- A downstream package cannot alter an upstream package's parameters or payload through its `ResultRef`.
- Sidecar relocation copies validated results, free-space authentication material, indexes, and supported checkpoints without changing identity.
- A missing or damaged index is rebuilt from receipts.
- Partial, corrupt, stale, orphaned, and historical entries are not reported as exact current hits.
- Concurrent writers do not publish duplicate or partially readable entries.
- Independent output ports do not invalidate one another when their dependency sets are disjoint.
- Intermediate artifacts remain deferred by default. If separately accepted, they are opt-in, explicitly declared, separately referenced, and never confused with checkpoints.
- Existing `outputs/design/...` historical artifacts remain readable as history and are not silently imported.

## Grill Findings and Dispositions

| Hostile question | Required disposition |
| --- | --- |
| Can copying only JSON make a free-space cache look valid? | No; authentication material and receipt verification are part of migration. |
| Can a damaged index hide a valid result or invent one? | No; index is rebuildable and receipts are authoritative. |
| Can a default-value change make old results ambiguous? | No; receipts store expanded effective values and schema versions. |
| Can a downstream package mutate an upstream parameter? | No; it receives only an immutable `ResultRef`. |
| Can a partial checkpoint be published as a completed output? | No; checkpoints and outputs have separate stores and states. |
| Can two GUI workers write the same identity simultaneously? | No; per-identity locking and atomic publication are required. |
| Can old historical JSON enter the current cache without provenance? | No; explicit legacy import and validation are required. |
| Can a path change alter calculation identity? | No; paths are display metadata, not identity inputs. |

## Plan Handoff and Acceptance Gates

Each plan has a separate jj workspace and local commit lineage. The working copy for Plan B is created from the accepted Plan A implementation commit; the working copy for Plan C is created from the accepted Plan B implementation commit and begins its fresh Superpowers review there. Preserve a failed candidate before restarting in a fresh task workspace at its preceding accepted gate, or restore only its recorded task paths after checking for unrelated edits. Do not reset a shared workspace or repository.

Plan A may hand off only when effective parameter snapshots, canonical fingerprints, validation errors, default expansion, and source-independent identity tests are present. Plan B may hand off only when sidecar relocation reuses validated results, preserves free-space authentication, rebuilds a damaged index, and prevents duplicate concurrent publication. Plan C may hand off only when its fresh review identifies exact output dependencies and its focused tests demonstrate independent version reuse or document why a safe split is not yet possible.

No plan may silently broaden the next plan's scope. The handoff artifact must name the accepted jj commit, changed files, focused tests, unresolved risks, and the exact next-plan entry point.

## Planning Review Refinements

These refinements resolve implementation ambiguities; they do not mark the planned behavior as implemented.

- Parameter snapshots retain every effective/calculated/requested value. The calculation fingerprint projects only recompute_required parameters; reuse_with_warning fields are compared against the historical calculation snapshot and reported with an explicit warning, while metadata_only fields do not change calculation identity. No existing geometry/topology tolerance is downgraded merely to avoid recomputation. Type hints complement runtime checks.
- A semantic output port is separate from the existing raw/processed layer. Port identities and processed payload fingerprints project only the declared port dependency/parameter/content subset. Clearance and free-space are excluded from Euclidean identity. Existing digest-bearing v1 JSON is validated before compatibility defaults are materialized.
- Sidecar output addresses include source, package, semantic port, raw/processed layer and identity; each operation verifies resolved containment and refuses traversal or symlink/junction escapes.
- Parameter versions share a source namespace. A source fingerprint is not the request/cache key. Same-stem IFC and Blender anchors may share the sidecar root only with distinct verified source namespaces.
- Current IFC capture includes an absolute path in ifc_source_identity. B must add verified portable SourceBinding handoff and relocation tests; relocating authenticated legacy inputs retains their original source ID and ResultRefs. Copying a directory alone does not correct a new capture's path-derived identity.
- An entry is published as one verified staging generation; a different payload under an existing identity is a conflict. Entry locks cover lookup, calculation and publication. Catalog/manifest/authentication initialization needs a separate short lock.
- migrated_reuse and legacy_adopted describe lookup provenance, not persisted computation-completion states. Existing runner cache_status remains a freshness mapping.
- Authentication keys from distinct old/destination directories coexist under explicit key IDs. Migration never overwrites a different destination key or resigns immutable old payloads.
- Index rebuilding derives dependency availability across every source namespace. Deleting an upstream cannot rewrite authenticated dependent receipts or cascade-delete other versions.
- Existing checkpoints without a complete input/parameter/upstream/algorithm binding remain historical or quarantined; copying them does not authorize resumption. B must fix the current unguarded group_distance_repair checkpoint reader before declaring checkpoint reuse.
- Plan C is a conditional implementation plan: its first action after accepted A/B is fresh brainstorming/Grill. It may be replaced by a repair plan based on actual outputs; no arbitrary two-use threshold is required to justify an intermediate. Completed intermediates stay deferred unless a real package need is accepted.
