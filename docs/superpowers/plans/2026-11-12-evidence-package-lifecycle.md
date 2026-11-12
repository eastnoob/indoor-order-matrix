# Evidence Package Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each package own computation, cache reuse and raw/processed access, including saved processed-channel consumption.

**Architecture:** Compose package-level entry functions, the existing frozen `EvidencePackage`, algorithms and storage functions. Adapters belong to the package capability boundary but keep their present layering; pure features never import Blender/session adapters.

**Tech Stack:** Python 3.12.13, existing Pixi lock, standard-library JSON/hash/path/atomic-file facilities and pytest. No new dependency.

**Spec:** [Package structure](../../project/evidence/evidence-package-structure.md#package-owned-lifecycle--approved-2026-11-12). The user approved this design and authorized writing the plan followed directly by development; no additional design approval is pending.

## Global Constraints

- Preserve `EvidencePackage.evaluate(source_envelopes)`, raw JSON v1, historical raw identities, positional constructors, algorithms and factory defaults.
- `output_processor=None` stays the default. No raw fallback, new default formula, size weighting or distance-to-potential business integration.
- Raw and processed results remain separate. Processor recipe changes must reuse valid raw calculation caches.
- Content identity and current freshness are distinct. Saved fresh receipts and hashes alone do not establish currentness.
- Whole-package invalidation is sufficient. Report `recompute_required`, `reasons`, `affected_targets`; restored identical input content permits reuse.
- Normalize only proven publication/audit revisions. Preserve meaningful `FieldQuery.revision`, geometry, actual values/status/support/source IDs and exact upstream references.
- Preserve authentication, fixed-schema readers, finite/range/status/lineage checks, error handling and atomic writes.
- English docstrings for every new/modified function; English comments explain nonobvious identity and adapter handoffs.
- jj-first. This chat is sole version writer on its own bookmark. Workers never change history. No source-workspace edits, push, merge or cleanup.
- Visual: omitted. Cache calls, hashes, saved values and freshness tests establish correctness; spatial algorithms and geometry are unchanged.

## Workline

- Workspace: `evidence-package-lifecycle`, `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/evidence-package-lifecycle`.
- Base: `b8a66a6593fd86e7af5551df05200999aaee4495` (`codex/group-distance-decay`).
- Initial change: `lrxmxrprurqsurksomyqttwuwqzqtoxs`; initial commit: `62f889fda4f9bf238141a81754ec93d671342d34`.
- Own bookmark: `codex/evidence-package-lifecycle`. Original working copy `bf55db54` and original bookmark remain untouched.
- Baseline: 113 shared publication/processing tests passed before implementation.
- Ledger/briefs/reports/review evidence: `.superpowers/sdd/2026-11-12-evidence-package-lifecycle/`.
- Environment: reuse the already locked parent Pixi runtime, explicitly select this workspace as Python cwd/import root; do not change manifests/locks or install another environment.

Test command prefix (append the listed pytest arguments):

```powershell
pixi run --manifest-path 'D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/group-distance-decay/pixi.toml' --as-is python -c "import os,sys,pytest; os.chdir(r'D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/evidence-package-lifecycle'); sys.path.insert(0,os.getcwd()); raise SystemExit(pytest.main(sys.argv[1:]))"
```

## Task 1: Processed persistence and explicit two-port dependencies

**Files:** `features/field_core.py`; existing output/processing tests and focused `test/test_evidence_package_processed_readback.py` if useful.

**Consumes:** Existing raw/processed outputs, scales, lineage validation, dependencies and fixed-schema reader.

**Produces:**

```python
EvidencePackageChannelReference(package_id, output_identity, target_identity, channel,
                                *, port="raw", processing_identity=None)
EvidencePackageDependency(..., *, source_processed_output=None)
serialize_evidence_processed_output(result) -> dict
deserialize_evidence_processed_output(payload, *, raw_output) -> EvidenceProcessedOutput
read_evidence_package_channel(output, reference, *, processed_output=None)
resolve_evidence_package_channel(output, reference, *, package_freshness,
                                 processed_output=None)
```

`output_identity` always identifies raw publication. Processed references require a matching processing identity; raw references forbid one. Serialize raw references with exactly the original four keys. Address uniqueness/sorting distinguishes ports. Strip both runtime upstream handles from published dependencies; keep graph declarations on the matching raw publication.

Separate `evidence-processed-output/v1` JSON contains existing processed fields, required processing identity and complete payload fingerprint. Validate known JSON fields, both identities, raw-content binding and channel rules without executing callbacks. Extract/reuse current processing validation. Errors remain empty results and successful decoding does not prove freshness.

- [x] Write and run failing tests first: historical raw identity/JSON unchanged; both ports at identical target/channel; valid/error roundtrip; malformed/tampered/foreign bytes; finite/range/lineage/status limits; freshness redaction and dependency consumption.
- [x] Implement the above using existing validation; no numerical/default changes.
- [x] Run shared output/processing and new processed-readback tests.
- [x] Freeze relevant bytes; a different agent runs acceptance and gives explicit SPEC / QUALITY verdicts. Repair substantive findings, then the designated writer checkpoints the accepted task.

Acceptance example:

```python
saved = serialize_evidence_processed_output(processed)
restored = deserialize_evidence_processed_output(saved, raw_output=raw)
assert restored == processed
assert read_evidence_package_channel(raw, reference,
                                     processed_output=restored) == processed.outputs[0]
```

## Task 2: Package-owned execution and content cache

**Files:** `adapters/free_space_evidence_package.py`, `features/group_distance_evidence_package.py`, `features/group_axis_potential_field.py`, small shared `features/evidence_package_storage.py`, `test/test_evidence_package_lifecycle.py` and affected producer tests.

**Consumes:** Task 1 saved-output APIs and existing freshness helpers. Preserve free-space's authenticated receipt and session separation.

**Produces:**

```python
run_free_space_package(scene, request, *, cache_directory=None, output_processor=None)
run_group_distance_package(bundle, *, repaired_result=None,
                           cache_directory=None, output_processor=None)
run_group_axis_potential_package(source_envelopes, *, scene_namespace=None,
                                 cache_directory=None, output_processor=None)
```

Each returns an ordinary mapping: `raw_output`, `processed_output`, `contract`, `status`, `cache_key`, `cache_hit`, `cache_status`. `status` describes the returned current publication; `cache_status` retains the read-only precomputation decision (recompute Boolean, reasons and affected targets). This prevents a newly computed valid result from being labeled stale while preserving the UI explanation for why it was recomputed. Existing evaluate functions keep their return types. Storage functions validate receipts and save atomically; no manager/wrapper, registry or scheduler.

Raw keys bind producer/version and complete calculation content, excluding processor configuration. Potential binds actual source values/status/support/source IDs/query, not only cache IDs; add its feature-owned contract builder rather than importing a runner. Distance binds complete input fingerprints and supplied repair content, preserving meaningful revisions and exact result references.

For free-space, reuse session content-key/cached-run mechanisms where valid: normalize only the publication plane revision, reconstruct current strict request/query metadata on restored hits, and retain the original calculation reference. Never label the old document as a newly observed calculation. Optional processed caching uses complete raw content plus processor ID/version/parameters; reject stale recipe or foreign raw bindings.

- [ ] Write/run failing lifecycle tests before production edits, using small real producer inputs and sentinels proving hits skip calculation.
- [ ] Implement shared storage and the three public entries, retaining old behavior and caller compatibility.
- [ ] Verify compute→hit, input change→miss, restoration→hit, processor change without raw calculation, status payload, corrupted receipt rejection, atomic failure preservation, free-space current metadata plus retained origin.
- [ ] Run lifecycle and affected free-space/distance/potential/processing regressions.
- [ ] Freeze bytes; a different agent runs acceptance and SPEC / QUALITY review. Repair findings before a task checkpoint.

Acceptance example:

```python
first = run_group_axis_potential_package(sources, cache_directory=cache)
again = run_group_axis_potential_package(sources, cache_directory=cache)
assert again["cache_hit"] is True
assert again["raw_output"] == first["raw_output"]
assert again["status"]["recompute_required"] is False
```

## Task 3: Actual consumer/callers and final convergence

**Files:** `scripts/design/group_level/replay_evidence_package_readback.py`, its tests, relevant package runner/processor callers, and the architecture documents listed below.

**Consumes:** Tasks 1/2. Old raw-reader calls remain valid.

**Produces:** Explicit processed saved-selection with separately SHA-pinned bytes and independently supplied current processor identity/metadata. Check raw current-source binding and contract freshness, processed raw-content binding and current recipe before numeric use. Equal raw contracts cannot admit an obsolete recipe. Select raw/processed channels and distinct same-channel targets while preserving values/status/scale/lineage/provenance. No business fusion.

- [ ] Write/run failing processed-consumer tests for current recipe changes, changed current sources, stale/unavailable redaction and same-name two-port selection.
- [ ] Extend existing readback and relevant actual callers to use package entries while preserving historical replay recipes and bytes.
- [ ] Synchronize `docs/project/evidence/evidence-package-structure.md`, `docs/software-architecture.md`, `docs/indoor_layout_evaluation_matrix_architecture_memory.md` and `docs/project/group-evidence-design-index.md` with actual behavior and limits.
- [ ] Run affected shared output/processing/freshness/readback/lifecycle and producer regressions; check original bookmark/workspace and accepted formulas/defaults remain intact.
- [ ] Whole-scope coverage assessment against all constraints; independent final acceptance plus SPEC / QUALITY review of the complete diff.
- [ ] Record accepted local commit, leave a clean empty next change and own bookmark at acceptance. Retain workspaces/evidence; no push/merge.

## Acceptance record

- [x] Design and implementation authorized by user; independent own jj workspace and baseline established.
- [x] Task 1 independently accepted: 189 tests passed, exit 0; SPEC PASS / QUALITY PASS; frozen SHA-256 values matched before and after independent execution. Review/report/probes are in the ledger directory. Nonblocking limit: individual processed selections revalidate the full processed set.
- [ ] Task 2 independently accepted.
- [ ] Task 3 and whole-scope review independently accepted.
- [ ] Final commit, clean next change and preserved original workline recorded.

Actual commands, candidate hashes, findings and accepted revisions are recorded in the ledger and summarized here as tasks close.
