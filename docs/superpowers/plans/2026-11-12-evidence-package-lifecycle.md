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

The validated saved repair scope remains authoritative, including accepted
partial or empty observation sets. Potential may use an input contract for its
storage key and return a publication contract over actual output targets;
`cache_key` need not equal that returned contract's identity.
Keep producer order in potential's input key and audit output, but compare cached
source content independently of the canonical source-storage sequence.

For free-space, reuse session content-key/cached-run mechanisms where valid: normalize only the publication plane revision, reconstruct current strict request/query metadata on restored hits, and retain the original calculation reference. Never label the old document as a newly observed calculation. Optional processed caching uses complete raw content plus processor ID/version/parameters; reject stale recipe or foreign raw bindings.

Retain the legacy free-space publication-key formula separately from the
normalized storage key, with authenticated raw and processed receipts. Existing
old cache filenames are not migrated and may incur an initial safe miss. Exact
legacy-byte comparisons hold backend provenance equal; the existing executor
hashes implementation bytes as a backend input.

- [x] Write/run failing lifecycle tests before production edits, using small real producer inputs and sentinels proving hits skip calculation.
- [x] Implement shared storage and the three public entries, retaining old behavior and caller compatibility.
- [x] Verify compute→hit, input change→miss, restoration→hit, processor change without raw calculation, status payload, corrupted receipt rejection, atomic failure preservation, free-space current metadata plus retained origin.
- [x] Run lifecycle and affected free-space/distance/potential/processing regressions.
- [x] Freeze bytes; a different agent runs acceptance and SPEC / QUALITY review. Repair findings before a task checkpoint.

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

- [x] Write/run failing processed-consumer tests for current recipe changes, changed current sources, stale/unavailable redaction and same-name two-port selection.
- [x] Extend existing readback and relevant actual callers to use package entries while preserving historical replay recipes and bytes.
- [x] Synchronize `docs/project/evidence/evidence-package-structure.md`, `docs/software-architecture.md`, `docs/indoor_layout_evaluation_matrix_architecture_memory.md` and `docs/project/group-evidence-design-index.md` with actual behavior and limits.
- [x] Run affected shared output/processing/freshness/readback/lifecycle and producer regressions; check original bookmark/workspace and accepted formulas/defaults remain intact.
- [x] Whole-scope coverage assessment against all constraints; independent final acceptance plus SPEC / QUALITY review of the complete diff.

Closure procedure: after the final write, record the accepted local revision,
verify a clean empty next change and own bookmark, and retain workspaces/evidence
in the ignored closure ledger. No push or merge.

## Acceptance record

- [x] Design and implementation authorized by user; independent own jj workspace and baseline established.
- [x] Task 1 independently accepted: 189 tests passed, exit 0; SPEC PASS / QUALITY PASS; frozen SHA-256 values matched before and after independent execution. Review/report/probes are in the ledger directory. Nonblocking limit: individual processed selections revalidate the full processed set.
- [x] Task 2 independently accepted: final SPEC PASS / QUALITY PASS after two independently found cache-scope/order repairs, with both original defect probes passing on the final freeze.
- [x] Task 3 and whole-scope review independently accepted: final combined run 353 passed, 1 deselected in 8.65s, exit 0, with all 19 frozen file hashes matched before/after. Separate Task 3 acceptance ran 46 tests in 239.01s, exit 0, including the full retained 37-group hierarchy.

The final revision, clean next change, bookmark and preserved-original-workline
checks are recorded after the final write in the ignored closure ledger.

Actual commands, candidate hashes, findings and accepted revisions are recorded in the ledger and summarized here as tasks close.

### Accepted local checkpoints and final evidence

- Plan: `5a23140d128edbfb0673e42db85997672d297036`.
- Task 1: `e9945fd848c85155152d80e32d41dad6be2bde7a`; independent 189-pass acceptance and SPEC PASS / QUALITY PASS.
- Task 2: `bdaaefa67637093f8062d77d076dd468b31d5119`; only its five producer/storage/test paths. Final Task 2 round 2 and whole-scope SPEC PASS / QUALITY PASS are in `final-review.md` under the ledger directory.
- Task 3 plus synchronized architecture/plan: the final revision is recorded in the ignored closure ledger, avoiding a self-referential commit ID in this plan.

The final reviewer ran the eleven-file combined suite against the exact final
freeze, plus the unchanged saved-subset and reverse-producer-order probes. All
passed. The separately executed full hierarchy evidence is reused because the
later distance repair affects only saved target scope and the potential repair
affects only cached-source validation; the retained hierarchy uses no cache.
The changed distance and ordinary potential runners were rerun in the final
combined suite. Do not add the overlapping 46-pass count to 353.

The source audit checked 21 path/environment expectations with zero mismatches.
All 20 existing potential and 29 existing distance functions remain AST-equal to
the original base. The original workspace stays at `bf55db54`, its bookmark at
`b8a66a65`; Pixi manifests/lock files and all 51 retained fixture hashes are
unchanged. Final code hashes are rechecked around local checkpointing.

Limits: no full-repository suite, new IFC extraction, Blender run or new geometry
visuals. Old free-space cache filenames are not migrated and can incur one safe
miss. Individual processed selections revalidate the full set. Current sources,
contracts and processor recipe context must still be supplied independently;
saved hashes/freshness receipts alone never establish live currentness.
