# Output Ports and Explicit Intermediate Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make genuinely independent semantic outputs reusable and deletable by version, preserve verified existing results, and document an explicit intermediate-product boundary without introducing unnecessary persistence.

**Architecture:** Begin with a fresh Superpowers brainstorming/Grill review of the accepted, implemented A/B receipts and dependencies. Add a small semantic-port publication wrapper around package-projected typed raw views; keep existing `EvidencePackageOutput`, historical whole-package identities, and `EvidencePackageChannelReference.port` (`raw`/`processed`) compatible. Each package chooses the parameters, source facts, channels, and upstream references for each semantic port; Plan B's `CacheStore` owns storage and migration.

**Tech Stack:** Python `>=3.12,<3.13` through Pixi, immutable dataclasses, existing evidence serializers and processors, canonical JSON/SHA-256, Plan B `features/cache_store.py` and `features/cache_paths.py`, pytest, Jujutsu.

**Spec:** `docs/superpowers/specs/2026-11-15-parameter-owned-sidecar-cache-design.md`

## Global Constraints

- Start from the accepted **implementation** revision recorded in `docs/superpowers/handoffs/2026-11-15-plan-b-accepted.md`. A plan-document commit is not an accepted implementation revision.
- Read the architecture memory and `docs/software-architecture.md`; use an isolated `jj workspace`, preserve unrelated dirty work, and do not push, merge, or change the owner workspace.
- Package ownership: a downstream consumer selects immutable upstream references; it cannot change upstream parameters or saved bytes.
- Sidecar locality: the default cache lives next to the model and moves with it. The sidecar path is a locator, not a calculation input.
- Identity excludes paths, timestamps, parameter source labels, and current UI selection. Equal effective computation values select the same version.
- `euclidean_distance` excludes clearance policy, free-space samples/result references, route repair witnesses, lattice spacing, and route-only query/occupancy fingerprints. `path_distance` binds its actual route inputs.
- Semantic output kind and raw/processed layer are separate fields. Never reinterpret existing `EvidencePackageChannelReference.port` as a semantic output kind.
- Only complete, verified, current publications are exact hits. Stale/orphaned/unavailable dependencies never produce a numeric fallback.
- Verify a historical serialized payload's original digest before decoding it or supplying any new runtime defaults. Keep existing pinned v1 identities and serialized bytes unchanged when no new wrapper is requested.
- Use Plan B `CacheStore.migrate_to()` for relocation. Do not create another migration module or atomic writer.
- No SQLite authority, automatic function decorator, GUI manager, or unvalidated historical JSON importer. Intermediate caching is opt-in; its default outcome in this plan is a documented long-term design.
- Every new/modified project-owned function has an English docstring; computation/adapter steps explain their purpose. Each code task has a focused failing test, passing verification, and a local jj commit.

## File and Responsibility Map

| File | Responsibility |
| --- | --- |
| `features/output_port_cache.py` | Immutable semantic contracts/references, wrapper serialization, selected-port processing, and calls to the accepted `CacheStore` API. No package geometry or parameter ownership. |
| `features/group_distance_output_ports.py` | Distance-specific input/parameter projection, independent Euclidean/path runners, and pure projection of an already verified combined publication. |
| `features/group_distance.py` | Shared Euclidean reading primitive and an explicit path-only calculation entry; retain existing formula/status behavior. |
| `features/group_axis_output_ports.py` | Pure-axis and optional distance-modulated semantic publications, exact Euclidean port-reference validation, and dependency registration. |
| `features/group_distance_evidence_package.py`, `features/group_axis_potential_field.py` | Reuse/expose existing package adapters and numerical helpers; retain the existing combined APIs and receipt readers. |
| `docs/superpowers/reviews/2026-11-15-plan-c-fresh-grill.md` | Actual accepted B evidence, adversarial questions, and proceed/repair/defer decisions. |
| `docs/superpowers/designs/2026-11-15-explicit-intermediate-contract.md` | Long-term opt-in intermediate identity, storage, serializer, and lifecycle contract; no production stage by default. |
| `docs/superpowers/handoffs/2026-11-15-plan-c-complete.md` | Implemented scope or safe-split deferral, accepted revisions, checks, limitations, and remaining decisions. |

The interfaces below are the target after Task 1. If actual accepted B artifacts contradict them, Task 1 must write a narrow repair plan first and revise the affected steps; do not force a planned interface over the implementation.

## jj Checkpoints and Recovery

Before implementation, inspect installed support and the accepted parent without snapshotting unrelated files:

```powershell
jj --version
jj --ignore-working-copy workspace list
jj --ignore-working-copy status
jj --ignore-working-copy log -r '@ | @-' --no-graph
jj commit --help
jj workspace add --help
jj restore --help
```

Create a new workspace from the exact revision in the accepted B handoff using `jj workspace add --revision <accepted-B-revision> <new-workspace-path>`; these two values are read from that handoff and chosen workspace location, not guessed from this document. Record the resolved absolute workspace and accepted parent in the fresh review. Before every task, record `jj --ignore-working-copy status` and an explicit intended-file list. Only the assigned implementation workspace's writer makes the task's `jj commit`; delegated readers do not mutate jj state.

At each gate inspect `jj --ignore-working-copy diff --summary`, the actual intended files, and `jj --ignore-working-copy op log --limit 5`, then run that task's exact `jj commit` command. Record the resulting commit in the review/handoff. Recovery means create a fresh workspace at the last accepted gate, or restore only the failed task's recorded files using the installed `jj restore --from` syntax after preserving its diff. Never reset/restore the whole owner workspace. Use operation-log recovery only for the specific accidental jj operation; do not blindly undo another worker's operation.

---

### Task 1: Fresh Superpowers/Grill against accepted B

**Files:**
- Read: `docs/superpowers/handoffs/2026-11-15-plan-a-accepted.md`
- Read: `docs/superpowers/handoffs/2026-11-15-plan-b-accepted.md`
- Read: implemented `features/evidence_package_parameters.py`, `features/cache_store.py`, `features/cache_paths.py`, package adapters, and the receipts named by the B handoff
- Create: `docs/superpowers/reviews/2026-11-15-plan-c-fresh-grill.md`
- Create only if needed: `docs/superpowers/plans/2026-11-15-plan-c-prerequisite-repair.md`
- Modify production code: none

**Interfaces:**
- Consumes: accepted A `ParameterSnapshot.identity_payload()`/`to_json()` and B `CacheAddress`, `CacheValidationContext`, `CacheStore.get`, `put`, `list`, `delete_exact`, `identity_lock`, `rebuild_index`, `migrate_to`.
- Produces: an evidence-backed ruling: proceed with these semantic-port tasks, revise them into a smaller repair plan, or document why a safe split is not yet possible. Also records whether a particular completed non-output stage merits a separate intermediate proposal.

- [ ] **Step 1: Authenticate the implementation gate.** Read both handoffs, verify their named revisions/files exist, and run B's exact focused acceptance command. At minimum include:

```powershell
pixi run pytest test/test_cache_store.py test/test_cache_migration.py test/test_evidence_package_lifecycle.py -q
rg -n 'class CacheStore|def (get|put|list|delete_exact|identity_lock|migrate_to)' features/cache_store.py
rg -n 'parameter_snapshot|identity_payload|payload_fingerprint|raw_payload_fingerprint' features/field_core.py features/evidence_package_storage.py
```

Expected: accepted implementations and verifiable receipts. If a handoff is absent, references only a plan commit, or tests expose a prerequisite failure, record that finding and write the prerequisite repair plan; do not execute Tasks 2-6 as if B had passed. This is a document/review gate, so no artificial failing production test is needed here.

- [ ] **Step 2: Inventory real publications.** Use B's read-only `CacheStore.list()` and the explicit sidecar paths in the handoff. Record one receipt per available package/semantic kind/layer, the parameter snapshot, input identity, payload digest, upstream refs, lifecycle state, and validator. Use an existing verified fixture for a missing kind and clearly label fixture evidence. Do not recursively search unrelated drives or invent a receipt.

- [ ] **Step 3: Conduct the fresh Grill, one unresolved decision at a time.** Use `superpowers:brainstorming` and the user's Grill workflow. Record concrete answers to:

1. Which actual Euclidean source envelope/provenance fields currently include route policy, free-space, grid, or a whole-package identity?
2. Can a package build a standalone Euclidean raw view with complete geometry/member/plane evidence and no route-only lineage?
3. Can old verified combined results be projected into that view without recomputing geometry? Which validator proves their original contract first?
4. Does the processed key bind only that selected view's exact bytes, processor recipe, and semantic address?
5. Can potential consume that view and its exact processed ref while retaining group/member/plane registration and cycle checks?
6. Does deleting path/free-space leave Euclidean modulation usable, while deleting the Euclidean raw/processed version makes the relevant modulation unavailable?
7. Is a proposed intermediate a complete stable stage with a real reuse/cost reason, an explicit serializer, and manageable ownership? Is a semantic output or run-local checkpoint already sufficient?

Do not require an invented count of observed reuse events. Describe the actual stage, expected benefit, invalidation boundary, and evidence. When code can answer a question, inspect it before asking the user.

- [ ] **Step 4: Write the ruling and reconcile the plan.** The review must include accepted implementation revisions, workspace/dirty manifest, receipt table, dependency graph, tests, and one of these outcomes:

- **Proceed:** the actual B boundary supports the wrapper and independent producers; execute the reviewed Tasks 2-6.
- **Repair:** the missing prerequisite is named with exact files/test and a small new plan; review and accept that repair before resuming affected tasks.
- **Defer split:** explain the specific unsafe dependency/compatibility boundary, keep validated B behavior, complete Task 7's design and Task 8's honest handoff, and do not claim independent ports were implemented.

Intermediate integration is not required to proceed with output separation. Even when a useful stage is identified, Task 7 first creates a concrete amended plan naming that stage; it does not silently activate conditional production code from this document.

- [ ] **Step 5: Commit the review.**

```powershell
jj commit -m "docs: review accepted cache artifacts for Plan C"
```

Acceptance: a reader can verify why the remaining scope is safe, or exactly why a repair/deferral is required. A/B acceptance is not inferred from the existence of their plan files.

### Task 2: Add a semantic-port wrapper without changing legacy JSON

**Files:**
- Create: `features/output_port_cache.py`
- Create: `test/test_output_port_cache.py`
- Test unchanged compatibility: `test/test_evidence_package_output.py`, `test/test_evidence_package_processed_readback.py`
- Modify: `docs/software-architecture.md` to map the new wrapper and its dependency on B

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class OutputPortRef:
    """Address one immutable semantic publication and its exact selected bytes."""
    source_fingerprint: str
    package_id: str
    output_port: str
    identity: str
    layer: str
    payload_fingerprint: str
    processing_identity: str | None = None

@dataclass(frozen=True, slots=True)
class OutputPortContract:
    """Declare only inputs that can affect this semantic output."""
    package_id: str
    output_port: str
    source_fingerprint: str
    input_fingerprints: Mapping[str, str]
    parameter_projection: Mapping[str, Any]
    upstream_refs: tuple[OutputPortRef, ...]
    algorithm_version: str
    schema_version: str
    addresses: tuple[tuple[str, str], ...]

@dataclass(frozen=True, slots=True)
class RawPortPublication:
    """Keep a package-projected typed view beside its semantic contract."""
    contract: OutputPortContract
    raw_view: EvidencePackageOutput
    parameter_snapshot: ParameterSnapshot | None = None

@dataclass(frozen=True, slots=True)
class PortRun:
    """Report reuse separately from immutable publication content."""
    publication: RawPortPublication | ProcessedPortPublication
    cache_hit: bool
    status: str
    cache_status: Mapping[str, Any]
    cache_reuse: Literal["computed", "exact_hit", "migrated_reuse", "legacy_adopted"]
    cache_location: str | None
```

`OutputPortContract.identity` hashes its canonical declared fields. Its `target_ids` and `channels` properties return the sorted distinct values from `addresses`. `RawPortPublication.ref` has `layer="raw"`, that contract identity, and SHA-256 of the exact canonical serialized **selected** `raw_view` bytes. `OutputPortRef.address` returns B's full `CacheAddress(source_fingerprint, package_id, output_port, layer, identity)`; references and deletion never discard source, package, semantic kind, or layer. `parameter_snapshot` is complete calculated audit metadata in the package envelope; never hash it wholesale into a port identity or inject it into the projected raw view. Deep-freeze nested containers. `ProcessedPortPublication` is defined in Task 4; postponed annotations avoid a runtime forward-reference error.

Every runner returns the status separately from its immutable publication. Deep-freeze `cache_status` and preserve B's freshness-mapping keys `freshness`, `recompute_required`, `exact_match`, `reasons`, and `affected_targets`. Its `parameter_status` is A's calculated/current comparison, restricted to the port's declared parameter dependencies for the reuse decision, and includes `reuse`, `exact_match`, `recompute_required`, full historical `calculated_parameters`, current `requested_parameters`, and `warnings` records with parameter/calculated/requested/impact. For processed runs add `processed_parameter_status`, comparing the historical `processed_output.parameter_snapshot` with the current `package.output_processor.parameter_snapshot`; a warning hit retains the old inner snapshot and returns the new intent only through this mapping. Raw runs set `processed_parameter_status=None`. A layer whose owner declares no typed schema uses `None` for its parameter comparison, preserving explicit legacy semantics rather than claiming a typed comparison. Unrelated clearance/modulation values may appear in full audit maps but do not enter this port's warning/recompute decision.

Set `cache_reuse="computed"` after calculation. On a hit map the actual B `CacheEntry.reuse_origin` as `local → exact_hit`, `migrated → migrated_reuse`, and `legacy_adopted → legacy_adopted`; derive `cache_location` from that entry's sidecar location. Do not infer migration from an identity or label a warning reuse as an exact parameter match. If a new semantic receipt was projected from an authenticated combined entry, preserve that adoption provenance in B's external provenance record, not by rewriting old payload bytes.

Produce `bind_raw_port(contract, raw_view, *, parameter_snapshot=None)`, `serialize_raw_port_publication(publication) -> bytes`, `validate_port_payload(payload: bytes, context: CacheValidationContext) -> None`, `save_raw_port(store, publication)`, and `load_raw_port(store, contract, *, requested_parameters: ParameterSnapshot | None) -> RawPortPublication | None`. The requested keyword has no default: typed callers pass an independently resolved current owner snapshot; explicit `None` declares a schema-less layer. Never substitute the saved snapshot for current owner declarations. Consume B's `CacheStore(root: Path)`, `put(address, *, contract, payload, payload_format, upstream_refs, validator, auth_key_id=None)` and `get(address, *, validator)`. Do not add a semantic field to every existing `EvidenceOutputChannel`.

- [ ] **Step 1: Write the failing tests.** The following helpers are local to the new test file; the imported `_raw()` is the existing tiny valid publication, not a retained IFC dependency.

```python
from dataclasses import FrozenInstanceError, replace
import pytest

from features.output_port_cache import OutputPortContract, bind_raw_port
from .test_evidence_package_processing import _raw


def _contract(raw, output_port="reading"):
    """Declare the complete selected scope of the existing contract fixture."""
    return OutputPortContract(
        package_id=raw.package_id, output_port=output_port,
        source_fingerprint="c" * 64,
        input_fingerprints={"source": "c" * 64},
        parameter_projection={"schema": "contract/port-parameters/1", "selected_names": [],
                              "values": {}, "value_contracts": {}},
        upstream_refs=(), algorithm_version="contract-port/1", schema_version="contract-port/v1",
        addresses=tuple((item.target["identity"], item.channel) for item in raw.outputs),
    )


def test_semantic_address_is_distinct_from_calculation_layer():
    """The wrapper names a semantic kind while raw/processed keeps its old meaning."""
    raw = _raw()
    publication = bind_raw_port(_contract(raw), raw)
    assert publication.ref.output_port == "reading"
    assert publication.ref.layer == "raw"
    with pytest.raises(FrozenInstanceError):
        publication.ref.output_port = "other"
    assert bind_raw_port(_contract(raw, "other"), raw).ref.identity != publication.ref.identity


def test_wrong_selected_channel_scope_is_rejected():
    """An independently addressed view must publish exactly its declared scope."""
    raw = _raw()
    with pytest.raises(ValueError, match="channel"):
        bind_raw_port(replace(_contract(raw), addresses=tuple(
            (item.target["identity"], "foreign") for item in raw.outputs)), raw)
```

- [ ] **Step 2: Verify the new tests fail.**

Run: `pixi run pytest test/test_output_port_cache.py -q`

Expected: collection fails because the wrapper module does not exist; existing legacy tests are unchanged.

- [ ] **Step 3: Implement immutable contracts, exact binding, and B storage.** Use the existing `_freeze`, `_json_value`, `_canonical_json`, serializer/deserializer, and `fingerprint_evidence_dependency`; do not create another canonicalization scheme. Implement the identity and payload distinction explicitly:

```python
def selected_raw_bytes(raw_view: EvidencePackageOutput) -> bytes:
    """Serialize only the package-selected standalone raw view."""
    return _canonical_json(serialize_evidence_package_output(raw_view)).encode("utf-8")


def raw_port_ref(publication: RawPortPublication) -> OutputPortRef:
    """Bind the semantic input identity to the exact immutable selected payload."""
    return OutputPortRef(
        source_fingerprint=publication.contract.source_fingerprint,
        package_id=publication.contract.package_id,
        output_port=publication.contract.output_port,
        identity=publication.contract.identity,
        layer="raw",
        payload_fingerprint=hashlib.sha256(selected_raw_bytes(publication.raw_view)).hexdigest(),
    )
```

Expose `RawPortPublication.ref` through `raw_port_ref`. Reject blank ids, unsupported layers, nonfinite values, duplicate addresses/upstream refs, foreign package, undeclared output addresses, mutable nested inputs, and a processed ref without its processing identity. Validate exact `(target, channel)` coverage through `addresses` rather than assuming a Cartesian product. The same `(target, channel)` may occur in distinct semantic publications because each has its own contract/ref; a single standalone raw view still rejects duplicate addresses under existing core rules. Never concatenate such views into an ambiguous combined publication.

The package payload is a self-contained JSON envelope with `schema="semantic-output-receipt/v1"`, `layer`, `contract`, `ref`, full calculated `parameter_snapshot`, `upstream_refs`, and `raw_view` containing the unchanged selected core serialization. The B storage receipt remains `cache-receipt/v1`. Its digest hashes the complete stored package envelope bytes, while `OutputPortRef.payload_fingerprint` hashes only the exact selected inner view bytes. The existing inner serializer digest is a third, separately verified binding. Do not confuse these three digests. The package validator parses the envelope, verifies contract/ref/address, full historical snapshot shape/type/unit/impact declarations, selected digest, original inner legacy digest, and selected addresses; it returns normally or raises `ValueError`/`TypeError`. It is not a boolean receipt predicate. The write uses the accepted store API:

```python
def save_raw_port(store, publication):
    """Publish selected bytes through the sole authoritative cache store."""
    return store.put(
        publication.ref.address,
        contract={"port_contract": _json_value(publication.contract),
                  "parameter_snapshot": (None if publication.parameter_snapshot is None
                                         else publication.parameter_snapshot.to_json())},
        payload=serialize_raw_port_publication(publication),
        payload_format="json",
        upstream_refs=tuple(reference.address for reference in publication.contract.upstream_refs),
        validator=validate_port_payload,
    )
```

Call this within `store.identity_lock(publication.ref.address)` over lookup → calculate → publish; B supports `get`/`put` under that reentrant context. `validate_port_payload` checks saved shape, allowed type/impact tags, digests, and addresses; a structural validator cannot establish current owner declarations. `load_raw_port` constructs the full raw `CacheAddress` from the independent requested contract, calls `store.get(address, validator=validate_port_payload)`, then compares the decoded contract and original historical snapshot's names/schema/type/unit/nullable/impact declarations against the independently supplied current `requested_parameters` before returning a hit. A uses `parameter_value_contracts` (restricted type tag, nullable, unit) and `parameter_impacts`; never trust saved self-description as owner authority. Omission raises Python `TypeError`; explicit `None` with a saved typed snapshot raises `ValueError` mentioning `requested_parameters`. Incompatible declarations raise `ValueError` mentioning `owner schema`. Do not dynamically import a type named by a receipt.

On a hit, preserve the calculated snapshot in that immutable receipt. Validate the full snapshot's declarations against the independent current owner snapshot, but decide freshness only from the fixed port projection. Every projection contains sorted distinct `selected_names` for all selected parameters, including warning/metadata names; only recompute-required selected values/contracts enter `values`/`value_contracts`. Generic comparison uses the independent current contract's `selected_names`, never all fields or a cached list alone. A full-snapshot difference in route clearance must not make Euclidean miss; a modulation-switch difference must not make pure-axis miss. Use A's `compare_parameter_snapshots` for audit and selected warning parameters, without applying unrelated recompute decisions to this port. Current `requested_parameters` is comparison status, not a persisted mutation of old snapshots. Surface `reuse_with_warning` without rewriting bytes merely to display current source labels. `_json_value` currently serializes legacy raw channel references with four fields; adding wrapper fields must not change that serializer branch or pinned v1 bytes.

- [ ] **Step 4: Verify selected persistence and legacy compatibility.** Add a schema-less round-trip with `load_raw_port(store, contract, requested_parameters=None)` using `CacheStore(tmp_path)`, corrupt one payload byte and assert `None`. Add the independent-owner guards below:

```python
def test_typed_load_requires_independent_requested_snapshot(tmp_path):
    """Typed history cannot establish the current owner schema by itself."""
    from features.cache_store import CacheStore
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec
    from features.output_port_cache import load_raw_port, save_raw_port

    raw = _raw()
    owner = ParameterSchema("contract-package", "typed-owner/1", (
        ParameterSpec("review_m", float, 0.01, unit="m"),
    ))
    current = owner.resolve()
    selected = bind_raw_port(_contract(raw), raw, parameter_snapshot=current)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    with pytest.raises(TypeError):
        load_raw_port(store, _contract(raw))
    with pytest.raises(ValueError, match="requested_parameters"):
        load_raw_port(store, _contract(raw), requested_parameters=None)
    assert load_raw_port(store, _contract(raw), requested_parameters=owner.resolve()).ref == selected.ref


def test_typed_load_rejects_self_consistent_forged_impact(tmp_path):
    """Valid saved checksums do not authorize a changed owner impact declaration."""
    from features.cache_store import CacheStore
    from features.evidence_package_parameters import ParameterImpact, ParameterSchema, ParameterSpec
    from features.output_port_cache import load_raw_port, save_raw_port

    raw = _raw()
    owner = ParameterSchema("contract-package", "typed-owner/1", (
        ParameterSpec("review_m", float, 0.01, unit="m", impact=ParameterImpact.REUSE_WITH_WARNING),
    ))
    current = owner.resolve()
    forged_owner = replace(owner, specs=(
        replace(owner.specs[0], impact=ParameterImpact.METADATA_ONLY),
    ))
    selected = bind_raw_port(_contract(raw), raw, parameter_snapshot=forged_owner.resolve())
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    with pytest.raises(ValueError, match="owner schema"):
        load_raw_port(store, _contract(raw), requested_parameters=current)
```

Run:

```powershell
pixi run pytest test/test_output_port_cache.py test/test_evidence_package_output.py test/test_evidence_package_processed_readback.py -q
```

Expected: PASS. Retain the pinned legacy output identity `75c7c12b6e7e7fad88dbd692d919b240bb90c05bbf3f149774bc619a21652dd2` and whole-JSON digest `d3b4784491d6b6dbfac8531f63e926d6429a0d065682540ced547dbd230b837b`. Historical readers must check the original serialized digest before dataclass construction/default expansion; the wrapper does not normalize old bytes before that check.

- [ ] **Step 5: Commit.** `jj commit -m "feat: add independent semantic output publications"`

### Task 3: Give distance ports explicit projections and independent producers

**Files:**
- Create: `features/group_distance_output_ports.py`
- Modify: `features/group_distance.py` around `_group_geometry`, the inline Euclidean reading in `_calculate`, and calculation entry points
- Modify: `features/group_distance_evidence_package.py` to expose/reuse package-owned view construction without changing the old combined runner
- Create: `test/test_group_distance_output_ports.py`
- Modify: `test/test_group_distance_processed_ifc.py` for retained Euclidean parity
- Modify: `docs/software-architecture.md`

**Interfaces:**
- Consumes: A `ParameterSnapshot`, B `CacheStore`, Task 2 `OutputPortContract`/`RawPortPublication`/`PortRun`.
- Produces: `distance_port_contracts(bundle, *, parameters, repaired_result=None) -> Mapping[str, OutputPortContract]`; `evaluate_euclidean_port(bundle, *, parameters) -> RawPortPublication`; `evaluate_path_port(bundle, *, parameters, repaired_result=None) -> RawPortPublication`; `run_group_distance_ports(bundle, *, store, parameters, repaired_result=None, legacy_entry=None) -> dict[str, PortRun]`.
- Produces: `project_verified_distance_ports(entry: CacheEntry, *, bundle, parameters, store, repaired_result=None) -> dict[str, RawPortPublication]`, which reopens the B entry through the original package validator, verifies its complete original receipt/contract/payload before decoding, and never runs either producer. An arbitrary typed raw object is not proof of a verified cached entry.
- Kernel produces `EuclideanPairObservation(pair_id, group_ids, reading, geometry_audit)` and `calculate_euclidean_pairs(bundle) -> tuple[EuclideanPairObservation, ...]`; the old combined calculation and new producer share the same Euclidean primitive. A path-only entry skips the Euclidean reading primitive while preserving route code.

- [ ] **Step 1: Write the failing policy reuse test with concrete fixtures.**

```python
from dataclasses import replace
import pytest

from features.cache_store import CacheStore
from features.group_distance_evidence_package import build_group_distance_parameter_snapshot
from features import group_distance_output_ports as ports
from .test_group_distance import _missing_bundle


def _parameters(total):
    """Resolve explicit route values using Plan A's typed package contract."""
    return build_group_distance_parameter_snapshot(_bundle(total))


def _bundle(total):
    """Vary only policy; missing geometry remains explicitly unavailable."""
    return replace(_missing_bundle(), clearance_policy={
        "min_left_m": 0.225, "min_right_m": 0.225, "min_total_m": total,
    })


def _forbidden(*args, **kwargs):
    """Fail if a cached semantic producer is invoked again."""
    pytest.fail("an independently cached producer ran again")


def _store(path):
    """Keep a sidecar root independent of each publication's full cache address."""
    return CacheStore(path)


def test_policy_one_two_one_reuses_euclidean_and_restores_path(tmp_path, monkeypatch):
    """Policy changes fork path versions without recalculating Euclidean output."""
    store = _store(tmp_path)
    first = ports.run_group_distance_ports(_bundle(1.0), store=store, parameters=_parameters(1.0))
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    second = ports.run_group_distance_ports(_bundle(2.0), store=store, parameters=_parameters(2.0))
    assert second["euclidean_distance"].cache_hit is True
    assert second["path_distance"].cache_hit is False
    assert first["euclidean_distance"].publication.ref == second["euclidean_distance"].publication.ref
    assert first["path_distance"].publication.ref.identity != second["path_distance"].publication.ref.identity
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    restored = ports.run_group_distance_ports(_bundle(1.0), store=store, parameters=_parameters(1.0))
    assert all(result.cache_hit for result in restored.values())
    assert restored["path_distance"].publication.ref == first["path_distance"].publication.ref
```

This fixture proves identity, status, and callback isolation, not valid route geometry. It consumes the exact owner snapshot builder introduced by A and does not register a competing schema.

- [ ] **Step 2: Verify the new tests fail.** Run `pixi run pytest test/test_group_distance_output_ports.py -q`; expect the missing runner/module to fail.

- [ ] **Step 3: Implement package-owned projections and selective evaluation.** Use this reviewed dependency table, with exact projected fields covered by tests:

| Semantic port | Identity and selected payload facts | Excluded facts |
| --- | --- | --- |
| `euclidean_distance` | Geometry source content/member ids, canonical analysis plane/frame/origin transform, sorted group ids and projection components/status, exact pair/channel scope, shared centroid/Euclidean algorithm/schema, an empty distance-parameter projection when no Euclidean knob exists | Clearance snapshot values/fingerprint, free-space ref/samples, physical occupancy, grid, route graph/repair metadata, route-only query/lineage |
| `path_distance` | Required source/group/plane/domain/grid/occupancy/query facts, validated selected free-space ref when present, route clearance parameter projection, route/repair algorithm/schema and witness identity | Parameter source labels, storage location, unrelated Euclidean serialized publication |

Do not reuse `group_distance_input_fingerprints(bundle)["query"]` or `["occupancy"]` as Euclidean fingerprints: the current query includes clearance and the occupancy includes free-space samples. Do not hash the complete `ParameterSnapshot` or `snapshot.identity_payload()` for Euclidean. Project explicit names and a port-specific projection schema:

```python
def project_port_parameters(snapshot, *, names, schema):
    """Declare every selected name while hashing only recompute-required values."""
    unknown = set(names) - set(snapshot.effective_parameters)
    if unknown:
        raise ValueError(f"unknown projected parameters: {sorted(unknown)}")
    selected_names = tuple(sorted(set(names)))
    selected = tuple(name for name in selected_names
                     if snapshot.parameter_impacts[name] == ParameterImpact.RECOMPUTE_REQUIRED.value)
    return {"schema": schema, "selected_names": list(selected_names), "values": {
        name: snapshot.effective_parameters[name]
        for name in selected
    }, "value_contracts": {
        name: snapshot.parameter_value_contracts[name] for name in selected
    }}
```

Import `ParameterImpact` from accepted A. The Euclidean call selects `names=()` (thus `selected_names=[]`) and `schema="group-distance/euclidean-parameters/1"`; route selects `clearance_mode` plus the three clearance names in constrained mode, or only `clearance_mode` for the preserved `clearance_policy=None` unconstrained mode. Use `schema="group-distance/path-parameters/1"`. Names with warning/metadata impact remain declared without placing their non-recompute values into the projection; the generic layer uses current `selected_names` to limit warning/recompute comparison. Reject disagreement between bundle/repair policy and the resolved owner snapshot. Full snapshot schema/audit stays in the receipt; increment the port projection schema when a selected parameter's meaning changes.

Extract the Euclidean reading from `_calculate` into one documented primitive using its existing `invalid`/`not_available`/`computed` precedence and `math.dist` centroid calculation. Both combined and standalone Euclidean calculation use that primitive; do not introduce different centroid mathematics. Add an explicit `include_euclidean=False` path-only branch to the internal route calculation so a route miss cannot invoke the Euclidean producer. Geometry preparation still needed by route offsets is permitted; recomputing the independent Euclidean observation is not.

Build fresh **projected** source envelopes/channel provenance/lineage for each standalone port. Copying a filtered channel while retaining its old source envelope identity or full provenance would reintroduce route coupling. Euclidean provenance keeps centroid/member/plane evidence; it omits free-space refs, path observations, full query/grid audit, and combined raw identities. The path port never depends on the Euclidean output merely because both share geometry inputs. Keep the old combined runner/serializer unchanged; export the new CacheStore-bound runner as the independent-port API.

`run_group_distance_ports` acquires the accepted B identity lock, validates each existing selected receipt, computes only missing ports, and reports separate `PortRun` values. Its independently resolved owner snapshot is mandatory; a rejected saved declaration is a diagnosed cache miss, retaining the original bytes and computing only that missing port. Probe B's existing combined kind using the exact accepted B adapter before scheduling either producer; use an explicitly supplied `legacy_entry` to select a known entry without scanning ambiguous history. The projector reopens the entry through B's original package validator and checks the original contract, source/target scope, dependencies, original expanded calculated parameter snapshot, supported schema and original payload digest before decoding. It rebuilds selected lineage without numerical evaluation and saves new wrapper receipts with that historical calculated audit. A missing A snapshot is not an exact typed hit: retain it as historical, rather than inventing values from current defaults. Reject mismatched/tampered entries. Loose historical JSON remains historical.

- [ ] **Step 4: Verify both identity isolation and real Euclidean parity.** Add the following concrete test to the existing retained-IFC file (its `retained_trial` fixture already returns `(inputs, raw, processed)`):

```python
def test_standalone_euclidean_matches_retained_readings(retained_trial):
    """Extracted Euclidean calculation preserves actual saved pair values/status."""
    from features.group_distance import calculate_euclidean_pairs
    inputs, raw, _ = retained_trial
    expected = {item.target["identity"]: item for item in raw.outputs
                if item.channel == "euclidean_distance"}
    actual = {item.pair_id: item for item in calculate_euclidean_pairs(inputs.bundle)}
    assert set(actual) == set(expected)
    for pair_id, item in actual.items():
        assert item.reading["value"] == expected[pair_id].observation["value"]
        assert item.reading["status"] == expected[pair_id].observation["raw_status"]
```

Also use `_bundle`/`_parameters` above to assert a changed grid or free-space-only fingerprint leaves Euclidean **ref and serialized selected bytes** unchanged, while path identity changes. For combined-cache adoption, use accepted B's `run_group_distance_package(_bundle(1.0), cache_directory=tmp_path)` to create a complete typed combined entry, obtain that exact `CacheEntry` through B's `list`, then patch both new producers to `_forbidden`. Project the entry and assert both new runner ports hit. Assert a changed original payload byte is rejected before projection. This test uses a freshly verified A/B receipt, not an unreceipted retained experiment JSON.

Run:

```powershell
pixi run pytest test/test_group_distance_output_ports.py test/test_group_distance.py test/test_group_distance_evidence_package.py test/test_group_distance_processed_ifc.py -q
```

Expected: PASS. If the actual retained fixture is absent, record that exact missing artifact and the resulting test limitation; do not replace it with fabricated spatial data or claim real-geometry acceptance.

- [ ] **Step 5: Commit.** `jj commit -m "feat: cache Euclidean and route outputs independently"`

### Task 4: Bind processing to selected-port bytes and recipe

**Files:**
- Modify: `features/output_port_cache.py`
- Modify: `features/group_distance_output_ports.py` to expose an optional selected Euclidean processor path
- Modify: `test/test_output_port_cache.py`
- Modify: `test/test_group_distance_output_ports.py`
- Modify: `test/test_group_distance_processed_ifc.py`
- Test unchanged legacy processing: `test/test_evidence_package_processing.py`, `test/test_evidence_package_processed_readback.py`

**Interfaces:**
- Produces `ProcessedPortPublication(raw_ref: OutputPortRef, processed_output: EvidenceProcessedOutput, identity: str)` with `.ref` and selected bytes; `identity` must equal the recomputed `processed_port_key`, `.ref.layer="processed"`, and `.ref.output_port` is the same semantic kind as `raw_ref`. `.ref.processing_identity` retains the verified inner `processed_output.processing_identity`.
- Produces `processed_port_key(raw: RawPortPublication, processor: EvidenceOutputProcessor) -> str` and `run_port_processor(raw, package: EvidencePackage, *, store: CacheStore, current_raw_contract: OutputPortContract, requested_raw_parameters: ParameterSnapshot | None) -> PortRun`. Both currentness keywords are required with no defaults. A controller independently builds the current upstream contract and current owner snapshot; explicit `None` declares schema-less raw. Historical raw metadata never substitutes for current intent. Processed intent always comes from the current processor, never from the cached processor receipt.
- Existing `processed_cache_key(raw_output, processor)` remains the historical whole-publication path; callers must explicitly select the new API for independent-port processing.

- [ ] **Step 1: Write the failing selected processing cache test.** Add to `test/test_output_port_cache.py`; `_contract` is defined in Task 2 and `_package`/`_process` are existing concrete fixture helpers.

```python
from features.cache_store import CacheStore
from features.field_core import EvidenceOutputProcessor
from features.output_port_cache import run_port_processor, save_raw_port
from .test_evidence_package_processing import _package, _process


def test_selected_processing_hits_without_reinvoking_callback(tmp_path):
    """The persisted processor binds selected raw bytes and explicit recipe."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    calls = []

    def process(view, parameters):
        """Count exact selected views passed to the existing typed callback."""
        calls.append(view)
        return _process(view, parameters)

    package = _package(EvidenceOutputProcessor("selected-process", "1", process, {"value": 0.75}))
    first = run_port_processor(selected, package, store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    second = run_port_processor(selected, package, store=store,
        current_raw_contract=_contract(raw), requested_raw_parameters=None)
    assert first.cache_hit is False and second.cache_hit is True
    assert calls == [selected.raw_view]
    assert first.publication.raw_ref == selected.ref
    assert second.publication.ref.output_port == "reading"
    assert second.publication.ref.layer == "processed"
    assert first.cache_reuse == "computed"
    assert second.cache_reuse == "exact_hit"
    assert second.cache_status["freshness"] == "fresh"
    assert second.cache_status["recompute_required"] is False


def test_processing_rejects_changed_independent_current_contract(tmp_path):
    """A historical raw object cannot authorize processing after inputs change."""
    raw = _raw()
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    changed = replace(_contract(raw), input_fingerprints={"source": "d" * 64})

    def forbidden(view, parameters):
        """Reject a callback before the independent raw-currentness gate passes."""
        pytest.fail("changed current raw contract invoked processing")

    package = _package(EvidenceOutputProcessor("selected-process", "1", forbidden, {"value": 0.75}))
    with pytest.raises(ValueError, match="current raw contract"):
        run_port_processor(selected, package, store=store,
            current_raw_contract=changed, requested_raw_parameters=None)
    assert not any(entry.address.layer == "processed" for entry in store.list())
```

- [ ] **Step 2: Verify failure.** Run `pixi run pytest test/test_output_port_cache.py -q`; expect the new processor API to be absent.

- [ ] **Step 3: Implement selected processing using the existing typed processor.** The key must contain the selected raw ref and bytes:

```python
def processed_port_key(raw, processor):
    """Bind semantic address, selected raw bytes, and effective processor recipe."""
    snapshot = processor.parameter_snapshot
    recipe_parameters = (processor.parameters if snapshot is None else snapshot.identity_payload())
    return fingerprint_evidence_dependency({
        "schema": "semantic-output-processing/1",
        "raw_ref": _json_value(raw.ref),
        "processor_id": processor.function_id,
        "processor_version": processor.version,
        "parameters": recipe_parameters,
    })
```

Consume A's resolved immutable `processor.parameter_snapshot`. Do not hash full audit snapshots or the original combined raw publication. Before processed lookup or callback, `run_port_processor` calls `load_raw_port(store, current_raw_contract, requested_parameters=requested_raw_parameters)` and requires that verified current publication/ref to match the supplied raw. A changed independent current input contract, missing current raw, or mismatch raises `ValueError` containing `current raw contract`; no callback or processed publication is allowed. The required nullable snapshot obeys Task 2's typed/schema-less guard. Only after this gate and a verified selected processed-cache miss does it call `package.process_output(raw.raw_view, package_freshness="fresh")`; the existing processing code therefore binds the complete standalone view, not all distance channels. Validate inner `raw_output_identity` against `raw.raw_view.output_identity` and inner `raw_payload_fingerprint` against the selected view serializer's internal digest. The outer `raw_ref.payload_fingerprint` additionally binds the exact stored selected bytes.

After loading a processed entry, return its unchanged historical snapshot and compute `cache_status["processed_parameter_status"]` through A's `compare_parameter_snapshots(cached_snapshot, current_processor_snapshot)`. A `reuse_with_warning` comparison keeps the cached result, sets `exact_match=False`, and returns both parameter maps and warning records; a recompute-required mismatch cannot be a hit. Populate raw `parameter_status` from the historical raw snapshot and `requested_raw_parameters`, applying only `current_raw_contract.parameter_projection["selected_names"]` to the warning/recompute decision. Propagate B's entry `reuse_origin` into `cache_reuse` on this processed path as well.

Store processed publications under the same source/package/semantic `output_port`, their distinct `processed_port_key` identity, and explicit `layer="processed"` in a full B `CacheAddress`. Require that `store.get(raw.ref.address, validator=validate_port_payload)` currently resolves to a complete verified entry before processing or accepting a processed hit. Publish with `store.put(processed.ref.address, contract=recipe_contract, payload=serialized_processed_envelope, payload_format="json", upstream_refs=(raw.ref.address,), validator=validate_port_payload)`; `recipe_contract` is the canonical raw ref plus processor id/version/effective parameter identity used by `processed_port_key`, and `serialized_processed_envelope` includes the same raw ref and inner processed serialization. B deletion can then orphan it. On load verify semantic kind, raw ref, selected bytes, processor recipe/identity, output addresses and serializer-internal digest. A path port may not satisfy a Euclidean processed request even when target ids overlap. Failed/stale processing is an explicit non-hit with no raw-value fallback.

- [ ] **Step 4: Verify independent processing with valid actual Euclidean values.** Keep Task 3's missing-geometry fixture limited to structural/status reuse. Add this test to the existing `test/test_group_distance_processed_ifc.py`, whose `retained_trial` fixture supplies authenticated actual geometry. It changes route policy without running a route calculation:

```python
def test_route_policy_change_preserves_actual_processed_port(retained_trial, tmp_path):
    """Real Euclidean proximity reuses selected bytes when only route policy changes."""
    from dataclasses import replace
    from features.cache_store import CacheStore
    from features.group_distance_output_ports import distance_port_contracts, evaluate_euclidean_port
    from features.group_distance_evidence_package import (
        build_group_distance_evidence_package, build_group_distance_parameter_snapshot,
        build_euclidean_median_proximity_processor,
    )
    from features.output_port_cache import load_raw_port, run_port_processor, save_raw_port

    inputs, _, _ = retained_trial
    first_bundle = replace(inputs.bundle, clearance_policy={
        "min_left_m": 0.225, "min_right_m": 0.225, "min_total_m": 1.0,
    })
    first_parameters = build_group_distance_parameter_snapshot(first_bundle)
    first_contract = distance_port_contracts(first_bundle, parameters=first_parameters)["euclidean_distance"]
    first_raw = evaluate_euclidean_port(first_bundle, parameters=first_parameters)
    store = CacheStore(tmp_path)
    save_raw_port(store, first_raw)
    processor = build_euclidean_median_proximity_processor(
        expected_target_ids=first_raw.contract.target_ids,
    )
    first = run_port_processor(first_raw,
        build_group_distance_evidence_package(output_processor=processor), store=store,
        current_raw_contract=first_contract, requested_raw_parameters=first_parameters)
    assert first.publication.processed_output.error_code is None
    assert len(first.publication.processed_output.outputs) == len(first_raw.contract.target_ids)

    second_bundle = replace(first_bundle, clearance_policy={
        "min_left_m": 0.225, "min_right_m": 0.225, "min_total_m": 2.0,
    })
    second_parameters = build_group_distance_parameter_snapshot(second_bundle)
    second_contract = distance_port_contracts(second_bundle, parameters=second_parameters)["euclidean_distance"]
    second_raw = load_raw_port(store, second_contract, requested_parameters=second_parameters)
    assert second_raw is not None and second_raw.ref == first_raw.ref

    def forbidden(view, parameters):
        """Expose an unexpected callback on a valid processed cache hit."""
        pytest.fail("route policy change reran Euclidean processing")

    blocked = replace(processor, function=forbidden)
    second = run_port_processor(second_raw,
        build_group_distance_evidence_package(output_processor=blocked), store=store,
        current_raw_contract=second_contract, requested_raw_parameters=second_parameters)
    assert second.cache_hit is True and second.cache_reuse == "exact_hit"
    assert second.publication.ref == first.publication.ref
    raw_status = second.cache_status["parameter_status"]
    assert raw_status["calculated_parameters"]["min_total_m"] == 1.0
    assert raw_status["requested_parameters"]["min_total_m"] == 2.0
    assert raw_status["recompute_required"] is False
```

Add this successful contract-only warning test to `test/test_output_port_cache.py`; it uses the concrete `_raw()`/`_process()` helpers and A's declared impact semantics:

```python
def test_processed_warning_hit_reports_historical_and_requested_values(tmp_path):
    """Warning reuse exposes current intent without rewriting the saved calculation."""
    from dataclasses import replace
    from features.evidence_package_parameters import ParameterImpact, ParameterSchema, ParameterSpec

    selected = bind_raw_port(_contract(_raw()), _raw())
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    schema = ParameterSchema(package_id="contract-package", schema_version="warning-process/1", specs=(
        ParameterSpec("value", float, 0.75),
        ParameterSpec("review_m", float, 0.01, unit="m", impact=ParameterImpact.REUSE_WITH_WARNING),
    ))
    processor = EvidenceOutputProcessor("warning-process", "1", _process,
        {"value": 0.75, "review_m": 0.01}, parameter_schema=schema)
    first = run_port_processor(selected, _package(processor), store=store,
        current_raw_contract=_contract(_raw()), requested_raw_parameters=None)

    def forbidden(view, parameters):
        """Reject recalculation when only a declared warning parameter changes."""
        pytest.fail("warning-only change reran the processor")

    requested = replace(processor, function=forbidden,
                        parameters={"value": 0.75, "review_m": 0.02})
    second = run_port_processor(selected, _package(requested), store=store,
        current_raw_contract=_contract(_raw()), requested_raw_parameters=None)
    assert second.cache_hit is True and second.cache_reuse == "exact_hit"
    assert second.publication.ref == first.publication.ref
    assert second.publication.processed_output.parameter_snapshot.calculated_parameters["review_m"] == 0.01
    status = second.cache_status["processed_parameter_status"]
    assert status["reuse"] == "reuse_with_warning" and status["exact_match"] is False
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert [warning["parameter"] for warning in status["warnings"]] == ["review_m"]
```

This tests the actual returned warning channel without presenting unavailable geometry as a successful numeric transform. Change processor version/effective computation parameter or one selected raw observation and assert a miss/different processed key. Change an unrelated route observation and assert no selected bytes/key change. Run:

```powershell
pixi run pytest test/test_output_port_cache.py test/test_group_distance_output_ports.py test/test_group_distance_processed_ifc.py test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py -q
```

Expected: PASS, including unchanged legacy raw/processed reference semantics and tamper rejection.

- [ ] **Step 5: Commit.** `jj commit -m "feat: process exact selected output-port payloads"`

### Task 5: Bind potential to immutable Euclidean references

**Files:**
- Create: `features/group_axis_output_ports.py`
- Modify: `features/group_axis_potential_field.py` only to reuse existing registration and modulation helpers
- Modify: `test/test_group_axis_distance_modulation.py`
- Modify: `docs/software-architecture.md`

**Interfaces:**
- Produces `bind_port_distance_modulation(raw_port, processed_port, *, store, processor, current_raw_contract: OutputPortContract, requested_raw_parameters: ParameterSnapshot | None, compatibility, dependency_graph) -> DistanceModulationInput`. The independent current raw contract and nullable snapshot are required keywords with no defaults; explicit `None` declares schema-less raw. `processor` is the explicit current upstream `EvidenceOutputProcessor`; recompute its expected selected recipe key before accepting the processed ref. Validate immutable semantic refs through B first and then adapt standalone typed views to the existing numerical consumer. A raw Euclidean ref alone never substitutes for processed proximity.
- Produces `run_group_axis_output_ports(envelopes, *, store, parameters, distance_raw=None, distance_processed=None, distance_processor=None, current_distance_contract=None, requested_distance_parameters=REQUIRED, compatibility=None, dependency_graph=None) -> dict[str, PortRun]`. Reuse A's `REQUIRED` sentinel. Enabling modulation requires explicit raw/processed/processor arguments plus the independently built current distance contract and current distance-owner snapshot (explicit `None` only when that owner is schema-less), and compatible registration facts. Reject the unchanged sentinel before loading or processing anything; omission must not silently declare a schema-less upstream. Forward those separate distance currentness inputs to the binding gate; potential's own `parameters` cannot stand in for upstream distance declarations. When disabled, no distance inputs are needed.
- Pure semantic `axis_potential` has no Euclidean/route dependency or modulation-switch parameter. Optional `distance_modulated_axis_support` binds the potential package's own effective enable switch, exact pure-axis ref, and exact processed Euclidean ref. Raw/processed are still layers of each kind.

- [ ] **Step 1: Write the failing reference validation test using real existing helpers.** Add to the existing module, which owns `actual_inputs()`; use A's owner resolver on the actual retained bundle.

```python
def test_port_modulation_rejects_route_ref_and_freezes_upstream(actual_inputs, tmp_path):
    """The downstream adapter cannot substitute a route result for Euclidean evidence."""
    from dataclasses import FrozenInstanceError
    from features.cache_store import CacheStore
    from features.group_distance_output_ports import distance_port_contracts, evaluate_euclidean_port
    from features.group_axis_output_ports import bind_port_distance_modulation, run_group_axis_output_ports
    from features.output_port_cache import run_port_processor, save_raw_port
    from features.group_distance_evidence_package import (
        build_group_distance_evidence_package, build_group_distance_parameter_snapshot,
    )
    from scripts.design.group_level.run_group_distance_processed_ifc import load_trial

    _, envelopes, _, _, modulation, _ = actual_inputs
    inputs, _, _ = load_trial()
    bundle = inputs.bundle
    parameters = build_group_distance_parameter_snapshot(bundle)
    current_contract = distance_port_contracts(bundle, parameters=parameters)["euclidean_distance"]
    store = CacheStore(tmp_path)
    euclidean = evaluate_euclidean_port(bundle, parameters=parameters)
    save_raw_port(store, euclidean)
    wrong_kind = replace(euclidean, contract=replace(euclidean.contract, output_port="path_distance"))
    recipe = potential_processor_for_port(euclidean)
    processed = run_port_processor(euclidean, build_group_distance_evidence_package(output_processor=recipe),
        store=store, current_raw_contract=current_contract, requested_raw_parameters=parameters).publication
    axis_parameters = potential.build_group_axis_parameter_snapshot(distance_modulation_enabled=True)
    with pytest.raises(ValueError, match="requested_distance_parameters"):
        run_group_axis_output_ports(envelopes, store=store, parameters=axis_parameters,
            distance_raw=euclidean, distance_processed=processed, distance_processor=recipe,
            current_distance_contract=current_contract, compatibility=modulation.compatibility,
            dependency_graph=modulation.dependency_graph)
    with pytest.raises(ValueError, match="euclidean_distance"):
        bind_port_distance_modulation(wrong_kind, processed,
            store=store, processor=recipe, current_raw_contract=current_contract,
            requested_raw_parameters=parameters, compatibility=modulation.compatibility,
            dependency_graph=modulation.dependency_graph)
    with pytest.raises(FrozenInstanceError):
        euclidean.ref.identity = "changed"
```

Define this helper in the same test file; it uses an existing real processor builder, not an undefined `_modulation` fixture:

```python
def potential_processor_for_port(publication):
    """Configure the actual symmetric processor for this complete selected scope."""
    from features.group_distance_evidence_package import build_euclidean_symmetric_reciprocal_proximity_processor
    return build_euclidean_symmetric_reciprocal_proximity_processor(
        expected_target_ids=publication.contract.target_ids,
    )
```

The existing builder's exact exported name is `build_euclidean_symmetric_reciprocal_proximity_processor`. The retained `load_trial()` returns experiment inputs whose `.bundle` supplies the actual `GroupDistanceInput`; do not pass the experiment-input wrapper to the geometry kernel or invent clearance defaults for it.

- [ ] **Step 2: Verify failure.** Run `pixi run pytest test/test_group_axis_distance_modulation.py -q`; expect missing semantic adapter APIs.

- [ ] **Step 3: Implement port registration and independent potential publication.** The binding adapter requires package `group-walk-distance`, semantic `euclidean_distance`, raw layer plus matching processed layer, selected payload digests, exact raw ref, complete pair scope, current processing identity, source/member registration, canonical plane/origin compatibility, and acyclic semantic dependencies. Before recipe validation or numeric use, call `load_raw_port(store, current_raw_contract, requested_parameters=requested_raw_parameters)` and require its verified selected publication/ref to match the supplied raw; use Task 4's fail-closed currentness errors. Then recompute `processed_port_key(raw_port, processor)` from the caller's explicit current recipe and require equality with the selected processed identity; reject a stale/wrong processor version before using values. It resolves both refs through the accepted B store immediately before numeric use; a caller-provided typed object alone cannot override a deleted/unavailable receipt. `compatibility` proves source/member/plane registration; it does not replace independently current input or owner declarations.

Project compatibility facts to the geometry/member/plane facts actually required by Euclidean registration. Do not keep route-only `distance_query`/free-space fields in the new Euclidean view merely to satisfy the old full-query comparison. Add one documented geometry-registration projection used by both the adapter and validator; preserve the full historical comparison for historical combined inputs. Bind the standalone typed `EvidencePackageOutput`/`EvidenceProcessedOutput` to the existing immutable `DistanceModulationInput` internally, then reuse current cycle, membership, status, and formula checks.

The pure-axis port reuses the existing base evaluator. The optional modulation producer consumes cached pure-axis channels and the exact processed Euclidean view via existing `_distance_modulated_outputs`; it must not recalculate pure-axis output on a modulation-only change. A raw combined publication remains available through the historical API; changing the new wrapper's semantic kind must not mutate it.

- [ ] **Step 4: Verify numeric behavior and immutability.** Extend the actual-input test to bind the valid Euclidean raw/processed pair and compare all available nonself modulation values with the existing `axis_field_support * processed proximity` behavior. Toggle the potential package's own switch using its accepted A schema and assert the pure-axis identity/ref remains unchanged. For a stale/missing Euclidean dependency assert nonself values are `None` and effective status unavailable/orphaned. Retain all original 1,369-cell/1,332-nonself assertions. Run:

```powershell
pixi run pytest test/test_group_axis_distance_modulation.py test/test_group_axis_potential_field.py test/test_group_distance_output_ports.py -q
```

Expected: PASS with retained numeric registration intact. Record any actual missing retained fixture without claiming full real-data acceptance.

- [ ] **Step 5: Commit.** `jj commit -m "feat: consume exact Euclidean ports in axis modulation"`

### Task 6: Prove exact deletion and relocation isolation

**Files:**
- Modify: `test/test_output_port_cache.py`
- Modify: `test/test_group_distance_output_ports.py`
- Modify: `test/test_group_axis_distance_modulation.py`
- Modify: `features/output_port_cache.py` only for package validators/dependency registration exposed by these tests
- Modify: `features/cache_store.py` only if a demonstrated B prerequisite defect is repaired through the Task 1 repair gate

**Interfaces:**
- Consumes the accepted B `CacheStore.list`, `delete_exact`, `migrate_to`, and authoritative lifecycle/dependency validation. Receipt bytes stay immutable; lifecycle changes belong to B's advisory/derived state.
- Produces separately listable/deletable versions and migration that returns the same selected refs before any producer is scheduled.

- [ ] **Step 1: Write the failing independent-version tests.** Use the concrete `_bundle`, `_parameters`, `_forbidden` from Task 3 in `test/test_group_distance_output_ports.py`:

```python
def test_delete_path_version_preserves_euclidean_and_other_path(tmp_path):
    """Exact deletion affects only its semantic address and true dependents."""
    store = _store(tmp_path)
    one = ports.run_group_distance_ports(_bundle(1.0), store=store, parameters=_parameters(1.0))
    two = ports.run_group_distance_ports(_bundle(2.0), store=store, parameters=_parameters(2.0))
    removed = one["path_distance"].publication.ref
    assert store.delete_exact(removed.address)
    remaining = store.list(source_fingerprint=removed.source_fingerprint, package_id=removed.package_id)
    addresses = {item.address for item in remaining if item.status == "complete"}
    assert two["path_distance"].publication.ref.address in addresses
    assert one["euclidean_distance"].publication.ref.address in addresses


def test_move_port_cache_reuses_without_producers(tmp_path, monkeypatch):
    """Directory migration preserves refs and probes copied entries before calculation."""
    source = _store(tmp_path / "old")
    first = ports.run_group_distance_ports(_bundle(1.0), store=source, parameters=_parameters(1.0))
    from features.output_port_cache import validate_port_payload
    source.migrate_to(tmp_path / "new", validators={
        "group-walk-distance:raw": validate_port_payload,
        "group-walk-distance:processed": validate_port_payload,
    })
    destination = _store(tmp_path / "new")
    monkeypatch.setattr(ports, "evaluate_euclidean_port", _forbidden)
    monkeypatch.setattr(ports, "evaluate_path_port", _forbidden)
    moved = ports.run_group_distance_ports(_bundle(1.0), store=destination, parameters=_parameters(1.0))
    assert all(result.cache_hit for result in moved.values())
    assert all(result.cache_reuse == "migrated_reuse" for result in moved.values())
    assert {name: result.publication.ref for name, result in moved.items()} == {
        name: result.publication.ref for name, result in first.items()
    }
```

- [ ] **Step 2: Verify failure before fixing registration.** Run `pixi run pytest test/test_group_distance_output_ports.py -q`; a registration/migration defect must fail in the new assertion rather than being hidden by recalculation.

- [ ] **Step 3: Register true refs with B.** Put exact semantic upstream refs in each wrapper receipt and use B's package-validator dispatch for `semantic-output-receipt/v1`. Processed Euclidean depends only on its exact Euclidean raw ref; optional axis modulation depends on its pure-axis ref and processed Euclidean ref. A path receipt includes its actual free-space result ref when used. Do not add path/free-space edges to Euclidean or modulation. Use accepted B's full-source dependency scan and locks; do not rewrite signed upstream receipts to mark them orphaned.

The migration test passes Task 2's concrete `validate_port_payload` through B's `validators` mapping keyed by package plus layer. For a mixed sidecar, extend each existing package validator callback to recognize its explicit known semantic-envelope schema and dispatch to this validator while preserving its legacy-codec branch. Include free-space/Blender callbacks in the mapping for their own families. Never import a validator named by untrusted file data or apply a semantic-only predicate to all entries. B resolves each authenticated entry's own `auth_key_id` through `CacheValidationContext`; this plan neither overwrites keys nor passes secrets through contracts. Preserve `migrated_reuse` reporting; the test asserts hit/ref equivalence, not that every move looks like a never-moved current receipt.

- [ ] **Step 4: Verify dependency deletion on actual modulation.** In the existing `actual_inputs` module, create selected ports using Task 5's concrete setup. Delete the selected **path** version and, where present, its free-space upstream version; assert Euclidean raw/processed refs still resolve and the exact modulation result remains usable. Then delete the selected **Euclidean raw** version; assert its processed descendant and the dependent modulation are orphaned/unavailable, no nonself numeric values are returned, and pure-axis output still hits. Repeat deletion of only the processed Euclidean version. These are distinct cases; deleting route-only free-space must not orphan Euclidean modulation.

Run:

```powershell
pixi run pytest test/test_output_port_cache.py test/test_group_distance_output_ports.py test/test_group_axis_distance_modulation.py test/test_cache_store.py test/test_cache_migration.py -q
```

Expected: PASS, including multi-version listing, exact deletion, selected-byte verification, relocation reuse, and downstream unavailability.

- [ ] **Step 5: Commit.** `jj commit -m "test: verify independent port deletion and migration reuse"`

### Task 7: Record the opt-in intermediate boundary and adoption decision

**Files:**
- Create: `docs/superpowers/designs/2026-11-15-explicit-intermediate-contract.md`
- Modify: `docs/superpowers/reviews/2026-11-15-plan-c-fresh-grill.md`
- Create only if the review names a warranted stage: `docs/superpowers/plans/2026-11-15-reviewed-intermediate-stage.md`
- Production modules/tests: none by default

**Interfaces:**
- Consumes: the actual stage inventory from Task 1, A snapshots, B storage/lifecycle, and C immutable semantic references.
- Produces a complete long-term design. A later opt-in implementation would expose frozen `IntermediateRef(source_fingerprint, package_id, stage_id, identity, payload_fingerprint, serializer_id, serializer_version)` and a receipt with explicit stage dependencies; this task does not pretend those Python symbols already exist. Its future address includes source/package/stage/identity and a distinct intermediate kind; do not squeeze it into B's output-only raw/processed address without the separate adoption plan's reviewed API extension.

- [ ] **Step 1: Write the concrete storage/identity design.** Include this example and the explicit field meanings:

```json
{
  "schema": "intermediate-receipt/v1",
  "kind": "intermediate",
  "package_id": "owning-package",
  "stage_id": "declared-completed-stage",
  "identity": "sha256-of-declared-stage-inputs",
  "parameter_projection": {"schema": "stage-parameters/1", "values": {}},
  "parameter_snapshot": {"package_id": "owning-package", "config_schema_version": "package-parameters/1", "effective_parameters": {}, "calculated_parameters": {}, "parameter_sources": {}, "parameter_fingerprint": "sha256", "parameter_impacts": {}, "parameter_value_contracts": {}},
  "upstream_refs": [],
  "algorithm_version": "stage-algorithm/1",
  "serializer": {"id": "json", "version": "1"},
  "payload": {"path": "payload.json", "format": "json", "size": 2, "fingerprint": "sha256-of-exact-bytes"},
  "status": "complete"
}
```

The example is illustrative, not an accepted cache fixture. The owning package declares input projection, selected recompute parameters, upstream refs, algorithm, stage schema, serializer and deterministic restoration. Full resolved A snapshot is audit; only relevant effective computation values enter stage identity. A restored geometry/graph must validate library/format versions and semantic invariants; never use untrusted pickle as a default serializer.

Use `sources/<source-fingerprint>/intermediates/<package-id>/<stage-id>/<identity>/` beside the model. Reuse B's path safety, per-identity and catalog locks, staged atomic publication, payload verification, exact deletion, derived orphaning, index rebuild and migration; extend its explicit `kind="intermediate"` namespace only in a separately reviewed adoption plan. No second storage backend or automatic decorator is required. JSON is the first choice for small structured records; arrays or geometry use a declared stable binary/structured serializer plus a verified payload file. SQLite remains a possible future advisory catalog when demonstrated query/scale needs warrant it.

- [ ] **Step 2: State the checkpoint boundary.** A resumable job checkpoint remains under `runs/<run-id>/checkpoints/`, may be mutable/incomplete, and must bind exact inputs/policy/upstream/algorithm before resume. It is never indexed or returned as a complete intermediate or semantic output. Promotion requires a package-declared complete stage, validated receipt, immutable payload, and explicit new publication; renaming a checkpoint is insufficient.

- [ ] **Step 3: Record adoption or deferral.** If Task 1 found no warranted stage, state that output-port reuse meets the current requirement and leave production intermediate persistence unimplemented. If a real stage warrants it, write a new small Superpowers plan naming the actual producer function, serializer, dependencies, cache API extension, restart/changed-input/corruption tests, and jj gates; Grill that plan before execution. Evidence and engineering judgment determine the decision, not a fixed number of reuse events.

- [ ] **Step 4: Validate the document against actual A/B/C names.** Review the stage identity, complete snapshot fields, storage namespace, serializer compatibility, deletion graph, relocation and checkpoint rules. Record which parts exist and which are design only; do not run a nonexistent `test_intermediate_receipts.py` or claim intermediate code passed tests.

- [ ] **Step 5: Commit.** `jj commit -m "docs: define explicit intermediate cache adoption boundary"`

### Task 8: Verify and publish the Plan C handoff

**Files:**
- Create: `docs/superpowers/handoffs/2026-11-15-plan-c-complete.md`
- Modify: `docs/superpowers/reviews/2026-11-15-plan-c-fresh-grill.md` with final evidence
- Modify: `docs/software-architecture.md` for final implemented boundaries

**Interfaces:**
- Consumes: accepted B implementation revision, the fresh ruling, completed task commits/tests, and any separately reviewed repair/intermediate plan.
- Produces: a verifiable delivery record that distinguishes implementation, compatible historical APIs, deferred work, and fixture limitations.

- [ ] **Step 1: Run the focused implemented scope once.** When Tasks 2-6 proceeded, run:

```powershell
pixi run pytest test/test_output_port_cache.py test/test_group_distance_output_ports.py test/test_group_distance.py test/test_group_distance_evidence_package.py test/test_group_distance_processed_ifc.py test/test_group_axis_distance_modulation.py test/test_evidence_package_output.py test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py test/test_evidence_package_lifecycle.py test/test_cache_store.py test/test_cache_migration.py -q
```

Expected: PASS for the implemented scope, with any unavailable real artifact explicitly reported. If the fresh ruling deferred the split, instead run the accepted B regression set and document that no C output split was implemented. Add an intermediate test file only if its separately accepted adoption plan actually created it.

- [ ] **Step 2: Check files and compatibility.** Use installed jj inspection commands; `jj diff --check` is not supported by the current installation. Check whitespace directly with the existing Pixi Python runtime, using the intended changed-file list from each gate, and inspect `jj --ignore-working-copy diff --summary` plus the relevant diff. Scan this plan for vague executable placeholders and fix them before its implementation. Recheck pinned legacy digests, digest-before-default ordering, selected source/parameter projection, processing exact-byte binding, and absence of route/free-space edges on Euclidean modulation.

- [ ] **Step 3: Write the handoff.** Include accepted A/B implementation revisions, C task commit ids, actual workspace, modified files, new public entry points, semantic kind versus raw/processed layer, per-port parameter/dependency table, verified combined-result adoption, `1 → 2 → 1` evidence, selected processing hits, exact deletion, model-side relocation, orphan behavior, intermediate adoption/deferral, commands/results, and remaining limitations. A safe-split deferral is an explicit result; it must not be labeled an implemented split.

- [ ] **Step 4: Commit.** `jj commit -m "docs: record Plan C acceptance and remaining boundaries"`

## Plan C Self-Review

Spec coverage: Task 1 enforces a fresh review of implemented B and supports a repair or documented safe deferral. Tasks 2-4 define independent semantic identities, package-owned projections, selected-payload processing, verified old-result adoption and historical compatibility. Tasks 5-6 cover immutable upstream selection, pure-axis independence, correct deletion edges, version listing and relocation reuse. Task 7 defines explicit intermediate storage and checkpoints while leaving unwarranted production integration deferred. Task 8 records honest acceptance evidence and jj recovery points.

Type consistency: `OutputPortRef.output_port` is semantic and `layer` is raw/processed; the old channel reference's `port` keeps its existing meaning. `ParameterSnapshot` comes only from A, persistence/migration only from B, and selected numerical views only from their owning packages. Internal legacy serializer digests, selected byte digests, and input/processor identities are separately named and verified.

Implementation precondition: this file is a forward plan, not proof that A, B, C, or an intermediate stage has been implemented. Its first gate must reconcile signatures with accepted artifacts before production edits.
