# Model-Side CacheStore and Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Keep verified cache versions and run data beside the model, migrate existing valid results without calculation, and make versions independently listable and removable.

**Architecture:** Add cache_paths.py for location and source binding, and a thin cache_store.py for immutable entries, publication, locks, catalog recovery and migration. Package serializers, parameter snapshots and authentication remain package-owned. Wrap legacy receipts unchanged in a new storage receipt instead of rewriting their calculation identity.

**Tech Stack:** Python >=3.12,<3.13 through Pixi; standard-library pathlib, json, hashlib, tempfile, os, msvcrt/fcntl; existing evidence and wire validators; pytest; Jujutsu.

**Spec:** docs/superpowers/specs/2026-11-15-parameter-owned-sidecar-cache-design.md

## Global Constraints

- Execute after Plan A implementation acceptance, using the exact commit recorded in docs/superpowers/handoffs/2026-11-15-plan-a-accepted.md. A planning-document commit is not an accepted implementation.
- Read project memory and software-architecture.md first; synchronize the architecture map in each task that changes its interfaces.
- Only the designated root version writer changes jj history. Read-only inspection uses jj --ignore-working-copy; create one implementation workspace from the accepted A revision.
- Maintain package ownership, formulas, unconstrained clearance_policy=None, existing ResultRefs and numerical backend/version checks.
- Preserve existing calculation IDs during storage migration. A path, index, source label, relocation timestamp or migration status never becomes a calculation input.
- Default saved location is model.with_suffix(".order_analyzer"); an IFC and Blender file sharing a stem share this root but remain separated by source namespace.
- Never silently fall back to a repository-global cache when the model folder is read-only. An explicit cache_directory has priority.
- No SQLite, decorators, GUI, broad legacy import, semantic port split or real intermediate stage is introduced by B.
- Only complete, package-validated entries whose upstream dependencies remain available may be exact hits.
- Every project-owned function gets an English docstring; use Pixi for tests and only the approved portable Blender if an actual Blender invocation becomes necessary.
- Visuals: omitted; hashes, round trips, call sentinels and lifecycle checks establish this change without geometry rendering.

## File responsibilities and stable storage contract

- features/cache_paths.py: sidecar locator, full entry address, path containment, SourceBinding (durable source ID plus current content verification and display locators).
- features/cache_store.py: file publication/locking, generic receipt checks, advisory catalog, exact deletion, migration. It must not import Blender adapters.
- features/evidence_package_storage.py: keep the existing atomic JSON writer and typed raw/processed codecs; add only needed byte-copy helpers.
- Adapter and package files own validator callbacks and export storage payloads without exposing mutable parameters.

The master layout is refined to include package and calculation-layer namespaces:

~~~text
model.order_analyzer/
  manifest.json
  index.json
  settings/
  auth/<key-id>/.free_space_cache_key
  locks/
  quarantine/
  runs/<pending-capture-run-id>/{logs,checkpoints,scratch}/
  sources/<source-fingerprint>/
    source.json
    outputs/<package-id>/<output-port>/<raw-or-processed>/<identity>/
      receipt.json
      payload.json
    runs/<run-id>/{logs,checkpoints,scratch}/
~~~

Source fingerprint is content-derived source/scene identity, not a request cache_key. Changing parameter versions keeps the same source namespace. Different sources under a common model-stem root cannot collide.

Core public signatures (all introduced in Tasks 1–2):

~~~python
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ContextManager, Literal

@dataclass(frozen=True, slots=True)
class CacheAddress:
    source_fingerprint: str
    package_id: str
    output_port: str
    layer: Literal["raw", "processed"]
    identity: str

@dataclass(frozen=True, slots=True)
class SourceBinding:
    source_fingerprint: str
    canonical_source_identity: str
    content_fingerprint: str
    external_dependencies: Mapping[str, str]
    current_locator: str

@dataclass(frozen=True, slots=True)
class CacheEntry:
    address: CacheAddress
    receipt: Mapping[str, Any]
    receipt_path: Path
    payload_paths: tuple[Path, ...]
    status: str
    reuse_origin: Literal["local", "migrated", "legacy_adopted"]

@dataclass(frozen=True, slots=True)
class MigrationReport:
    copied: tuple[CacheAddress, ...]
    reused: tuple[CacheAddress, ...]
    failed: tuple[tuple[str, str], ...]
    old_directory_retained: bool

@dataclass(frozen=True, slots=True)
class CacheValidationContext:
    address: CacheAddress
    auth_key_id: str | None
    auth_key: bytes | None = field(repr=False)

CacheValidator = Callable[[bytes, CacheValidationContext], None]

class CacheStore:
    def __init__(self, root: Path): ...
    def identity_lock(self, address: CacheAddress) -> ContextManager[None]: ...
    def put(self, address: CacheAddress, *, contract: Mapping[str, Any],
            payload: bytes, payload_format: str,
            upstream_refs: tuple[CacheAddress, ...] = (),
            validator: CacheValidator,
            auth_key_id: str | None = None) -> CacheEntry: ...
    def get(self, address: CacheAddress, *,
            validator: CacheValidator) -> CacheEntry | None: ...
    def register_auth_key(self, secret: bytes) -> str: ...
    def list(self, *, source_fingerprint: str | None = None,
             package_id: str | None = None,
             output_port: str | None = None) -> tuple[CacheEntry, ...]: ...
    def delete_exact(self, address: CacheAddress) -> bool: ...
    def rebuild_index(self) -> Mapping[str, Any]: ...
    def migrate_to(self, destination: Path, *,
                   validators: Mapping[str, CacheValidator]) -> MigrationReport: ...
~~~

The callable validator returns normally for valid package bytes and raises ValueError/TypeError for invalid bytes. Its dispatch key is package_id plus layer, supplied by the caller, never an arbitrary import named by the file. CacheStore checks the wrapper and key ID before passing a frozen validation context. A free-space callback uses context.auth_key with its existing HMAC validator; the secret is never serialized, logged or included in repr. register_auth_key uses SHA256(secret) as key ID, creates once under the auth/catalog lock, and refuses different bytes under that ID. get and migration resolve the entry's own key domain rather than the destination's current default.

A common receipt carries schema=cache-receipt/v1, full address, package contract including Plan A parameters, payload format/size/SHA256, upstream_refs, auth_key_id if applicable, status=complete, and a receipt fingerprint. A storage receipt can wrap the unchanged existing raw, processed, HMAC or Blender-wire JSON as payload.json. Migration provenance and derived availability are kept outside the immutable payload; no signed bytes are rewritten to mark an orphan.

Detach and deeply freeze `SourceBinding.external_dependencies` and `CacheEntry.receipt` at construction, using the existing finite JSON/freeze helpers. A frozen dataclass alone must not expose caller-owned mutable maps; extend the existing immutability assertions with a nested-map mutation attempt.

---

### Task 1: Add safe paths, source binding and immutable publication

**Files:**
- Create: features/cache_paths.py
- Create: features/cache_store.py
- Modify: features/evidence_package_storage.py at write_receipt
- Create: test/test_cache_paths.py
- Create: test/test_cache_store.py
- Modify: docs/software-architecture.md

**Interfaces:**
- Consumes existing write_receipt and Plan A ParameterSnapshot.to_json(); storage does not resolve parameters.
- Produces CacheAddress, CacheEntry, resolve_sidecar_path(model_path: Path) -> Path, and CacheStore.put/get.
- SourceBinding is introduced here as frozen (source_fingerprint, canonical_source_identity, content_fingerprint, external_dependencies, current_locator). Only locators change when moving a model; content must be verified first.

- [ ] **Step 1: Write failing location, containment and round-trip tests.**

~~~python
from dataclasses import FrozenInstanceError
import json
import pytest
from features.cache_paths import CacheAddress, resolve_sidecar_path
from features.cache_store import CacheStore, CacheValidationContext

def validate_demo(payload: bytes, context: CacheValidationContext) -> None:
    """Validate a small real JSON payload independently of its wrapper."""
    if json.loads(payload) != {"value": 1}:
        raise ValueError("invalid demo payload")

def demo_address(identity: str = "one", *, package: str = "demo") -> CacheAddress:
    """Create a full address without mixing source and request identities."""
    return CacheAddress("scene-a", package, "value", "raw", identity)

def test_saved_model_sidecar(tmp_path):
    """Saved IFC and Blender anchors use the shared model-stem convention."""
    assert resolve_sidecar_path(tmp_path / "a.ifc") == tmp_path / "a.order_analyzer"
    assert resolve_sidecar_path(tmp_path / "a.blend") == tmp_path / "a.order_analyzer"

def test_publication_is_readable_and_package_namespaced(tmp_path):
    """An immutable entry remains distinct from another package's same local key."""
    store = CacheStore(tmp_path)
    first = store.put(demo_address(), contract={}, payload=b'{"value":1}',
                      payload_format="json", validator=validate_demo)
    other = store.put(demo_address(package="another"), contract={}, payload=b'{"value":1}',
                      payload_format="json", validator=validate_demo)
    assert first.receipt_path != other.receipt_path
    assert store.get(demo_address(), validator=validate_demo).address == first.address

@pytest.mark.parametrize("component", ["..", "../escape", "/absolute", "C:\\x", "\\\\server\\share", "x:stream"])
def test_address_rejects_unsafe_components(component):
    """Untrusted identifiers cannot choose another directory or stream."""
    with pytest.raises((ValueError, TypeError)):
        demo_address(package=component)
~~~

Also create an outside sentinel and a junction/symlink fixture where supported; put/get/migrate/delete must refuse a resolved path outside the verified sidecar root. Do not follow directory links while scanning receipts.

- [ ] **Step 2:** Run pixi run pytest test/test_cache_paths.py test/test_cache_store.py -q. Expected: import failures because new modules do not exist.
- [ ] **Step 3: Implement the address, locator and stage-then-publish path.**

~~~python
def resolve_sidecar_path(model_path: Path) -> Path:
    """Locate a model-stem sidecar without using its path as result identity."""
    if model_path.is_dir() or model_path.suffix.lower() not in {".ifc", ".blend"}:
        raise ValueError("a saved IFC or Blender model path is required")
    return model_path.with_suffix(".order_analyzer")
~~~

Validate every address component before joining; verify resolved containment for payload paths and for copy/delete operations. Create a sibling staging directory, write and fsync payload then receipt using the existing writer, verify both, and rename the complete directory into place. The initial atomic publish refuses an existing destination and verifies any winner before reuse; Task 2 adds the shared lock around the entire calculation. Never overwrite a complete same-identity entry with differing bytes; raise CacheConflictError. A crash before publication leaves only staging data, never a hit.

- [ ] **Step 4:** Run the two test files, including injected os.replace failure retaining old bytes. Expected: PASS and no visible partial complete entries.
- [ ] **Step 5:** Root runs jj diff and commits the task-owned files with jj commit -m "feat: add safe model-side cache publication". Record revision, diff and tests in B handoff.

---

### Task 2: Lock complete calculations and recover catalogs/lifecycle

**Files:**
- Modify: features/cache_store.py
- Modify: test/test_cache_store.py
- Create: test/test_cache_store_concurrency.py
- Modify: docs/software-architecture.md

**Interfaces:**
- Produces identity_lock, list, delete_exact, rebuild_index and derived lifecycle state.
- Lock scope surrounds lookup → compute → publish, not just the final file write. A runner that acquires identity_lock can call get/put under that same reentrant context.
- Persisted entry status remains complete; stale/orphaned/unavailable derive from current contract/dependency checks. Quarantine and failed run journals are separate records.

- [ ] **Step 1: Add failing crash, catalog and deletion tests.**

~~~python
def test_corrupt_index_cannot_hide_entry(tmp_path):
    """Receipt authority survives invalid advisory catalog contents."""
    store = CacheStore(tmp_path)
    store.put(demo_address(), contract={}, payload=b'{"value":1}',
              payload_format="json", validator=validate_demo)
    (tmp_path / "index.json").write_text("[]", encoding="utf-8")
    assert [entry.address for entry in store.list()] == [demo_address()]

def test_delete_exact_preserves_neighbor(tmp_path):
    """Removing one version preserves other versions at the same output."""
    store = CacheStore(tmp_path)
    for identity in ("one", "two"):
        store.put(demo_address(identity), contract={}, payload=b'{"value":1}',
                  payload_format="json", validator=validate_demo)
    assert store.delete_exact(demo_address("one")) is True
    assert store.get(demo_address("two"), validator=validate_demo) is not None
~~~

Add tests for corrupt payload quarantine, receipt fingerprint failure, missing upstream across two sources, and unchanged signed payload bytes after orphaning. The upstream reference is the complete CacheAddress, not only an identity string.

- [ ] **Step 2:** Run pixi run pytest test/test_cache_store.py test/test_cache_store_concurrency.py -q. Expected: failures for missing locking/catalog behavior.
- [ ] **Step 3: Implement locks and catalog recovery.**

Use OS-released file locks: msvcrt.locking on Windows, fcntl.flock on POSIX, plus a per-address thread lock where the platform lock semantics need it. Leave harmless lock files in place; do not delete a "stale" lock solely from a PID or elapsed time. A short catalog lock protects manifest/index/key setup; no catalog lock may wait while acquiring an entry lock. Under entry lock, re-read before computing; failed lock acquisition raises a typed timeout error. Dependency validation reads immutable upstream snapshots without waiting for another entry lock while a downstream lock is held. Multi-entry/root operations avoid nested entry locks, or acquire every needed lock in the same resolved-root/address order.

Treat index.json as disposable acceleration. Validate direct receipt bytes regardless of index claims. Scan all source namespaces to rebuild entries and dependency availability. Catalog refresh uses its own short lock and atomic replacement; independent identities cannot lose each other's catalog entries.

- [ ] **Step 4:** Use multiprocessing.get_context("spawn") for two writers of one identity and for two different identities. Assert one computation for the former, two readable catalog entries for the latter; inject a crashed holder and prove OS lock release. Run both test files. Expected: PASS.
- [ ] **Step 5:** Root jj commit -m "feat: lock cache calculations and rebuild lifecycle catalog".

---

### Task 3: Integrate package runners, caller paths and portable source binding

**Files:**
- Modify: features/group_distance_evidence_package.py
- Modify: features/group_axis_potential_field.py
- Modify: features/evidence_package_storage.py
- Modify: adapters/free_space_evidence_package.py
- Modify: adapters/blender_analysis_session.py
- Modify: adapters/blender_analysis_capture.py at begin_analysis_capture
- Modify: adapters/bonsai_live.py only for the source-binding handoff
- Modify: blender_addon/order_analyzer_ui/__init__.py and blender_addon/order_analyzer_ui/runtime.py where the workflow payload/worker is assembled
- Modify: adapters/blender_analysis_result_wire.py only if the validated workflow envelope schema needs locator fields; preserve result digest/currentness validation
- Read only: scripts/design/space_field/run_free_space_evidence_package.py (saved historical publication; no current cache location is inferred)
- Modify: scripts/design/group_level/run_group_distance_evidence_package.py, run_group_axis_potential_ifc.py, run_group_axis_potential_ifc_replay.py, run_group_axis_distance_modulation_ifc.py and run_group_field_hierarchy_ifc.py
- Modify: test/test_evidence_package_lifecycle.py
- Modify: test/test_evidence_package_lifecycle_runners.py
- Modify: test/test_free_space_evidence_package.py
- Modify: test/test_blender_analysis_session.py
- Modify: test/test_blender_analysis_capture.py and test/test_bonsai_live.py
- Modify: test/test_blender_analysis_runtime.py
- Modify: test/test_evidence_package_lifecycle_runners.py at its existing live/replay/hierarchy runner seams
- Modify: test/test_blender_analysis_ui.py at model-anchor and locator envelope assembly
- Modify: test/test_group_axis_distance_modulation.py at the retained-run caller seam
- Modify: docs/software-architecture.md

**Interfaces:**
- Preserve existing run_* signatures while adding keyword-only model_path: Path | None = None and temporary_cache_root: Path | None = None.
- The Blender worker receives locator fields as workflow envelope metadata, outside typed AnalysisRequest and calculation-key inputs. UI uses the active saved blend path, or linked IFC path when it is the selected model anchor.
- Separate the fixed trusted execution root from the model/run root: RuntimeJob.root continues to select the Pixi executable, module imports and child cwd; RuntimeJob.directory becomes sidecar/sources/<source>/runs/<run-id>/ when a verified source binding already exists. Capture begins before its content fingerprint exists, so otherwise allocate sidecar/runs/<run-id>/ and bind the eventual source in its journal; the pending run ID never becomes a reusable source identity. request.json, result.json, stdout.log, stderr.log and terminal_diagnostics.json all follow the stable owned run directory. Validate containment against the sidecar, not the repository.
- Change adapters/blender_analysis_session.py main: its current unconditional cache_directory=CONTENT_CACHE_DIRECTORY is a legacy location, not a user override. Resolve the trusted locator envelope and pass an override only when explicitly supplied. Runtime and worker envelope allowlists accept only validated locator data; the envelope cannot choose executables or Python modules.
- With explicit cache_directory, use it. Else use model_path. Unsaved Blender requires a supplied temporary root and session namespace. Legacy pure feature calls lacking all locator context retain nonpersistent behavior; the model UI/CLI must always supply context.
- Keep cache_status as its existing freshness mapping. Add cache_reuse: "computed" | "exact_hit" | "migrated_reuse" | "legacy_adopted" and cache_location: str | None. Update RESULT_KEYS assertions in lifecycle tests.
- Package validators are callbacks passed to CacheStore; no feature imports a Blender adapter.

- [ ] **Step 1: Add failing real-fixture tests.**

In test_blender_analysis_session.py use existing _cache_payload(); in lifecycle tests use _missing_bundle(), _potential_sources(), _scene(), _request() and _forbidden. Do not create a second synthetic geometry fixture.

~~~python
def test_blender_explicit_override_has_wire_hit(tmp_path):
    """A caller's chosen directory carries the actual wire content cache."""
    from ..adapters import blender_analysis_session as service
    payload = _cache_payload()
    location = tmp_path / "chosen"
    first = service._execute_workflow_payload(payload, cache_directory=location)
    second = service._execute_workflow_payload(payload, cache_directory=location)
    assert first["content_cache"]["hit"] is False
    assert second["content_cache"]["hit"] is True
~~~

Add separate tests for model_path resolving a sibling sidecar, explicit override winning, read-only location raising a clear error, temporary-to-saved locator, and changed parameter preserving source namespace. Exercise main(argv) with a real request file and captured result path, not only _execute_workflow_payload; assert it uses the sidecar instead of CONTENT_CACHE_DIRECTORY. Extend the existing runtime _native_job test seam for domain_session and free_space_run: assert every job artifact is under the model sidecar while child cwd/Pixi/PYTHONPATH still use the trusted repository root. Update the old test_child_launch_uses_validated_root_for_job_and_module_resolution assertion that currently forces jobs into repository outputs.

The potential live/replay CLIs currently default --output-root to repository outputs/design. Make omitted output roots resolve to the model-side run directory; explicit user output roots still win. A replay without a model locator may use a verified source-manifest locator or an explicit temporary/output root, but must not infer the model from the retained artifact directory. Test actual parsed CLI defaults reaching run_dir for each caller in test_evidence_package_lifecycle_runners.py, including the distance-modulation runner. Explicit exports to outputs/design remain supported. Do not move a running worker's open directory on save/rename; finish or cancel it, preserve its evidence, then migrate closed artifacts and set the next run's locator.

- [ ] **Step 2:** Run the modified package/session/capture tests. Expected: failures for new locator arguments and return metadata.
- [ ] **Step 3: Wire one store and existing codecs at each runner.**

Hold identity lock over hit checking, calculation and publication. Preserve current package keys, processed keys, wire versions and HMAC validation. Update test file-discovery assumptions from flat glob("*.json") to exact store addresses and manifest paths.

The current capture puts absolute IFC path in ifc_source_identity, and downstream source hashes include it. Do not merely declare paths excluded. Add an optional SourceBinding handoff to begin_analysis_capture; when its content and external fingerprints match the current file/scene, reuse canonical_source_identity while updating only current_locator. On the first legacy adoption, preserve the authenticated original source ID. New portable bindings derive their source identity from content/project identity rather than a display path. Reject binding reuse when source bytes, captured geometry or external dependencies change.

- [ ] **Step 4: Verify model relocation through the real capture/session seam.**

Write a regression using the existing capture fixture: move/rename IFC and its sidecar, change the display locator, retain project/geometry bytes, and assert unchanged calculation keys and old ResultRefs. Changing IFC content at the same path must miss. Do not hash a live Blend file on every UI metadata edit; retain the existing validated scene-content capture for analysis identity and record file hashes separately as provenance.

- [ ] **Step 5:** Run:
~~~text
pixi run pytest test/test_evidence_package_lifecycle.py test/test_evidence_package_lifecycle_runners.py test/test_free_space_evidence_package.py test/test_blender_analysis_session.py test/test_blender_analysis_capture.py test/test_bonsai_live.py test/test_blender_analysis_runtime.py test/test_blender_analysis_ui.py test/test_group_axis_distance_modulation.py -q
~~~
Expected: PASS, with original formulas and old no-locator nonpersistent callers preserved. Root jj commit -m "feat: connect package caches to model locators".

---

### Task 4: Adopt/migrate valid existing bytes and retain authentication domains

**Files:**
- Modify: features/cache_store.py
- Modify: features/evidence_package_storage.py
- Modify: adapters/free_space_evidence_package.py
- Modify: adapters/blender_analysis_session.py
- Modify: features/analysis_requests.py only at the reviewed legacy-compatibility validation seam; retain numerical dependency/version checks
- Modify: features/group_distance_repair.py at checkpoint validation/migration, building on A's fail-closed guard
- Create: test/test_cache_migration.py
- Modify: test/test_free_space_evidence_package.py and test/test_blender_analysis_session.py
- Modify: test/test_group_distance_route_repair.py
- Read and preserve: test/fixtures/cache_migration/pre_parameter_sidecar/ inherited from A, containing small pre-refactor validated receipts, their original implementation/backend hash manifest and origin file hashes; add migration assertions without regenerating the historical bytes
- Modify: docs/software-architecture.md

**Interfaces:**
- Produces CacheStore.migrate_to and package-specific explicit import functions for the current flat receipt families.
- Import validates legacy keys/contracts, current supplied sources and payload digests; preserves the original bytes/ResultRefs and records a lookup binding. No output-generation callback is invoked to "import" a cache.
- A legacy parameter receipt may be expanded only from saved explicit effective input values under the verified old algorithm/schema. If these cannot be proven, keep it historical/unavailable and report the exact missing evidence.

- [ ] **Step 1: Write failing byte-preserving migration tests.**

~~~python
from features.cache_store import CacheStore
from .test_cache_store import demo_address, validate_demo

def test_migration_preserves_payload_and_old_root(tmp_path):
    """Migration copies verified bytes and retains a rollback source."""
    source, destination = tmp_path / "old", tmp_path / "new"
    store = CacheStore(source)
    prior = store.put(demo_address(), contract={}, payload=b'{"value":1}',
                      payload_format="json", validator=validate_demo)
    prior_bytes = prior.payload_paths[0].read_bytes()
    report = store.migrate_to(destination, validators={"demo:raw": validate_demo})
    copied = CacheStore(destination).get(demo_address(), validator=validate_demo)
    assert copied.payload_paths[0].read_bytes() == prior_bytes
    assert copied.address == prior.address
    assert copied.reuse_origin == "migrated"
    assert report.old_directory_retained
    assert prior.receipt_path.exists()
~~~

Add valid-plus-corrupt partial migration, missing/corrupt index, interrupted publication, repeat migration, two versions, and same-identity/different-bytes conflict tests. A must already reject mismatched/unbound checkpoints before exposing variable CLI thresholds. B adds validated checkpoint copy/resumption with method/schema, exact input/clearance/upstream fingerprints, ordered group scope and requested pair scope. Old unbound checkpoints remain nonresumable; policy 1 -> 2 -> 1 must resume only the matching bound checkpoint. Inspect the sibling proxy fingerprint implementation as reference evidence, without merging its unrelated route algorithm changes.

- [ ] **Step 2: Add HMAC collision tests using the existing free-space fixtures.**

Create independent old and destination stores with different valid secrets and different entry identities. Migration must retain both credentials under auth/<key-id>/, preserve both receipt byte streams, and reuse both after verification. If the same immutable address instead contains differing authenticated bytes, keep the normal conflict rule and retain the old root; two auth tags do not justify overwriting one address. Copying JSON without its key must fail authentication. Concurrent _cache_secret initialization must not overwrite the winning key: protect initialization with the auth/catalog lock and create-once publication; current os.replace-over-existing behavior is not safe.

- [ ] **Step 3:** Run pixi run pytest test/test_cache_migration.py test/test_free_space_evidence_package.py test/test_blender_analysis_session.py test/test_group_distance_route_repair.py -q. Expected: new migration/auth tests fail before implementation.
- [ ] **Step 4: Implement verified copy and explicit legacy adoption.**

Copy a verified immutable snapshot under the source lock, release that lock, then verify/publish under destination locks; never hold source and destination entry locks in opposite migration orders. Retain old root on success and failure. If any upstream/auth/schema dependency is missing, mark that entry migration_failed/unavailable and continue independent entries. Never overwrite a destination HMAC key or a complete conflicting identity; key-id references select the matching auth domain through CacheValidationContext.

Copy supported settings/logs/checkpoints with their complete bindings; keep scratch run-local and never promote it to a hit. A resumed checkpoint requires exact input, parameters, upstream and algorithm fingerprints. Settings for an existing destination profile are not overwritten silently; retain imported settings as a named imported profile.

Migrate the existing known locations, including Blender CONTENT_CACHE_DIRECTORY and caller-selected free-space/raw/processed directories, using explicit source-root inputs. Do not scan arbitrary outputs/design JSON or claim those large historical artifacts are reusable without their validators/receipts.

The refactor itself changes files hashed by _content_cache_key and analysis_requests._backend_versions, including field_core, session, capture, runtime and UI. Preserve a small real pre-A/B receipt set and its exact old implementation/backend manifest before execution; a fixture generated only after B changes cannot prove historical reuse. Add a package-owned, reviewed compatibility/lookup binding from those explicitly recognized old implementation hashes to the current storage-only changes. Validate old receipt digests/HMAC, old recipe/schema/numerical backend versions, full independent current factual inputs, effective parameters and upstream refs before adoption. Preserve original cache keys, publication IDs and payload bytes; a new storage lookup binding may map the current request to that immutable legacy result. Do not remove version checks, whitelist unknown hashes, or equate a genuine numerical dependency/algorithm change. Those cases safely miss with an explicit reason.

- [ ] **Step 5: Prove migration did no calculation.**

Use both the pinned pre-refactor receipts and a post-A two-version fixture; patch calculation/generator callbacks to _forbidden after fixture creation. Request parameter values 1, then 2, then 1 in the destination. Assert both copied versions hit, unchanged origin keys/payload hashes/ResultRefs, cache_status["freshness"] == "fresh", cache_reuse == "migrated_reuse", and old bytes still exist. A current request key may use an explicit validated lookup binding; never relabel the legacy result as originally computed under that new key. Mutating an algorithm hash outside the reviewed compatibility set or a numerical package version must reject adoption. Run migration, route-repair and package lifecycle suites. Root jj commit -m "feat: migrate validated caches and authentication domains".

---

### Task 5: Freeze acceptance and prepare C's fresh review

**Files:**
- Create: docs/superpowers/handoffs/2026-11-15-plan-b-accepted.md
- Modify: docs/software-architecture.md
- Modify: docs/indoor_layout_evaluation_matrix_architecture_memory.md with a concise implemented-state entry after actual acceptance

- [ ] **Step 1:** Run all B focused tests once on a frozen candidate:
~~~text
pixi run pytest test/test_cache_paths.py test/test_cache_store.py test/test_cache_store_concurrency.py test/test_cache_migration.py test/test_evidence_package_lifecycle.py test/test_evidence_package_lifecycle_runners.py test/test_free_space_evidence_package.py test/test_blender_analysis_session.py test/test_blender_analysis_capture.py test/test_bonsai_live.py test/test_blender_analysis_runtime.py test/test_blender_analysis_ui.py test/test_group_distance_route_repair.py test/test_group_axis_distance_modulation.py -q
~~~
Expected: PASS. A different verifier records cwd, command, exit code, pass count and hashes.
- [ ] **Step 2:** Root inspects jj diff --git, checks touched bytes for whitespace/errors, and verifies the frozen tested bytes match. Obtain separate spec and quality review per verified-agent-workflow. Failures are repaired and reverified before acceptance.
- [ ] **Step 3:** Record accepted implementation commit, source/path binding, unchanged legacy keys/refs, source versus request fingerprint example, HMAC migration into an already-used destination, two-process lock evidence, index rebuilding, exact deletion across sources and partial migration results.
- [ ] **Step 4:** Set next entry point to C Task 1: fresh Superpowers brainstorming/Grill over actual accepted A/B receipts, dependencies and costs; select a new plan or repair plan and reassess the intermediate need.
- [ ] **Step 5:** Root jj commit -m "docs: accept model-side cache migration and hand off to C".

## Self-review and deferred work

Spec coverage: Tasks 1–2 cover sidecar paths, atomicity, locks, namespace isolation, lifecycle/index/delete; Task 3 covers all current callers and actual source-path coupling; Task 4 covers no-calculation legacy adoption, HMAC domains, checkpoints and partial migration; Task 5 provides the C evidence gate.

Type consistency: A's ParameterSnapshot remains package-owned. B uses one CacheAddress everywhere; migrated_reuse is lookup provenance, complete is stored lifecycle status, and existing cache_status remains a mapping. C's semantic-port split is not assumed implemented by B.

Scope: UI receives location wiring only. Version-manager GUI, SQLite, semantic port decomposition and real reusable intermediates remain outside B.
