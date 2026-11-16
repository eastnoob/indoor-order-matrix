# Plan B Handoff — locally verified model-side cache migration

Date: 2026-11-16

## Accepted implementation and workline

- Final nonempty implementation: `3b160264c80dbba631fbe90ab02dca48bc348e0d`.
- Accepted A handoff ancestor: `488d0d4e439a7c6674d2973f3ddbaa9b34fa2fe8`.
- Accepted A implementation: `92ff7d521415c95d505c2e35eca60781e09b7f96`.
- Retained unaccepted B Task 1 draft parent: `4123363af72296463fbd8f5d6f35637e9bed6f32`.
- Workspace: `parameter-cache-b-standard`,
  `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-b-standard`.
- Implementation change: `vupsowxpzuozlprtqqmyruykstpoynns`; root alone writes jj history.
- Tasks 1–4 were repaired and accepted together in the final explicit-fileset
  implementation commit. Original per-task accepted commits and unrecorded
  historical RED runs are not claimed. Earlier failures remain diagnostic evidence.
- This document is a separate child of the implementation. Its own commit ID is
  recorded externally by `codex/parameter-cache-b-accepted` and the execution
  ledger; it deliberately does not contain a guessed self-reference.

## Delivered behavior

Saved IFC/Blend calls keep caches and run files beside the model in the shared
model-stem `.order_analyzer` directory. Explicit directory overrides win; unsaved
calls use caller-owned session roots. Five group CLIs and eight Blender UI
launch seams pass these locations while trusted Pixi/import/module execution
continues from the project root.

`CacheStore` publishes immutable, validated payload/receipt directories with
source/package/combined-port/raw-or-processed/identity addresses. The package
owns numerical admission and parameter/recipe checks. Locks cover the full
lookup/calculation/publication interval; default authentication domains survive
imports. Version listing, exact deletion, index rebuilding, quarantine,
persisted source bindings, reviewed legacy lookup attestations and migration
provenance are implemented. The manifest records source/format/producer facts
and migration history without authorizing numerical reuse.

Migration copies validated old payloads, receipt bytes, credentials, closed run
logs, settings and bound route checkpoints. Source roots remain available.
Conflicts preserve destination versions/settings, active runs and scratch stay
at the source, and owner rejection of one entry does not abort unrelated entries.
Settings conflicts use named imported profiles. Five CLI journals reach complete
or failed without hiding the original publication exception.

Historical reuse accepts only independently rebuilt factual keys and the exact
reviewed original/current implementation profile with unchanged numerical
backends. Arbitrary JSON scanning and receipt self-declared-key admission were
removed. Legacy keys, publication IDs, ResultRefs and signed bytes remain original.

## Full independent acceptance

Independent verifier: `/root/b_frozen_verifier`.

- **786 collected / 786 passed**, exit 0, **807.82 seconds** pytest time
  (808.904842 seconds process wall time).
- Failure, error, skip, xfail, xpass and deselected counts are all **zero**.
- All 786 collected node IDs match XML outcomes individually; missing/extra
  sets are empty. All 32 highlighted mandatory nodes passed.
- **712** actual code/test/config/fixture file hashes match before/after execution;
  root rechecked them after the implementation commit.
- All **12** fixture files inherited from A's acceptance manifest remain byte
  identical, including the four pre-A historical payload families. The original
  fixture manifest and expected hashes were not regenerated.
- All **30** current compatibility implementation hashes and original family
  manifest hashes match their reviewed profiles.
- Final independent verdicts: **SPEC PASS / QUALITY APPROVED**. Their separate
  17/25 and 200/237 test subsets overlap and are not added to the full-suite count.

The complete 14-file command, cwd, start/end timestamps and exit code are in
`focused.meta.json`; collection uses the same paths with `--collect-only -q`.
The run uses `-q -ra --junitxml=... --import-mode=importlib`, no selection filters.
Actual test cwd is `D:/PROJECTS/understandOtherPackage/order_analyzer_b_test_alias`,
a junction to this B workspace. `environment.json` and `module-paths.json` record
Pixi 0.69.0, Python 3.12.13, unset `PYTEST_ADDOPTS`, imported B modules and the
explicit shared main-workspace OCTA source. The pytest temp root is unique.

Evidence directory:
`D:/temp/oa-pytest-b/final-20261116/frozen-2140`.

| Evidence file | SHA256 |
| --- | --- |
| `acceptance-result.json` | `924b67f4c8880f2d8d8bac3df9cfca11b81b915806d716968ef8b873519b5162` |
| `focused.xml` | `bb068eb1183f958cd58b92d599577abac8b5d2e664605d0991e0c688037acaa3` |
| `focused.log` | `b27fbd43bb3e921cd24b1b1b50d7afcbe0b8d08f12d8e6e02b2518cf6277c2b3` |
| `collect.log` | `3275930d8765aaf70894961974154111a066f09fbcabdfe553d859e927a752a6` |
| `candidate-before.json` | `bba2441f0da6531da1c08044ba883f383f3e0094e8558e341dce04538e374c16` |
| `candidate-after.json` | `bba2441f0da6531da1c08044ba883f383f3e0094e8558e341dce04538e374c16` |
| `per-node-match.json` | `2d9c9e5fe8c8dd4858affcbd60c8c3e7b2de53e1fb742d1a3cc1af34e54fb978` |
| `evidence-sha256.json` | `eb5b0c8aa917e2373427d87df29b77efd2704bf4c009f35419768d1337fd8b99` |
| `review-verdicts.json` | `e4cd499f724f48e37abc02a20553f7911924f30cb7ab89d4ecd193a1fc911535` |
| `source-request-example.json` | `158da0187eedbea952d166994c5859a72d947d304322ac5b72b8443846b9d7cc` |
| `implementation-eol-verification.json` | `ded0ee93a4b781d8cc496d1f30108b45ab0ecbd7fffd62ab4144b4f14384ec84` |
| `implementation-byte-verification.json` | `56c1dd778a6e635644dba1ceb2b88ed22ce5548fea5d64e0c2ada7f562b3975f` |

The jj repository has `working-copy.eol-conversion="input-output"`: committed LF
source reconstructs the tested Windows CRLF working bytes. Root verified all 26
changed code/test/config contents against the implementation and all 30
hash-profile files reconstruct exactly. Raw `jj file show` LF hashes must not be
mistaken for the tested Windows checkout hashes. The implementation/EOL receipts
record both forms; no source or tests changed after acceptance.

## Requirement evidence

| Required behavior | Actual acceptance |
| --- | --- |
| Model locations, override priority, temporary roots, trusted child execution | Six distance/potential locator cases; eight runtime/UI launch cases; real request-file main boundaries |
| Portable factual source, path movement and content invalidation | Synchronous and cooperative capture→session move/rename hits preserve refs/bytes; changed same-path IFC bytes reject old binding |
| Source distinct from request | Distance clearance versions share source `578328914e6f5302f18bb3765dd5600879ca6594951e9d604d87d735ba905cfa` while calculation identities differ; exact values in `source-request-example.json` |
| Complete immutable publication, containment, lifecycle and recovery | Cache path/store suite covers staged failures, conflicts, receipt/payload checks, rebuild and exact deletion |
| Actual producer concurrency | Distance/free-space/Blender same-address first miss each calculates once; two versions each calculate once and remain catalogued; crash releases OS lock and timeout is typed |
| Four-family no-calculation migration | Raw, processed, authenticated free-space and Blender wire each execute P import/migrate → Q read/rebuild → R read with producer sentinels and isolated cold-miss controls |
| Original identities and numerical eligibility | Original key/ref/byte assertions, effective values 1→2→1, changed implementation/numerical version misses; two actual free-space lattices have 16/64 samples |
| Multiple authentication domains | Already-used destination retains its key and new default; migrated old authenticated payloads use their own preserved key ID |
| Partial migration and precise deletion | Corrupt wrapper and owner rejection do not erase independent entries; source-scoped exact delete preserves namesakes and signed orphan bytes |
| Run/settings/checkpoint migration | Ten CLI success/failure journal cases, terminal artifacts copied byte-for-byte; active/scratch excluded; policy 1→2→1 reuses only matching bound route checkpoints |
| Existing retained business calculations | Complete 37-group hierarchy guard, actual full-scope modulation and 1369 addressed cells remain in the executed gate |

`per-node-match.json` gives exact mandatory node names/outcomes;
`node-outcomes.json` gives every executed case. The approved
[Plan B](../plans/2026-11-15-model-side-cache-store-migration.md) and
[architecture map](../../software-architecture.md) are synchronized.

The restart test's P process also creates the two post-A parameter versions as
fixture setup, outside the forbidden-producer context. Historical adoption,
the migration itself and all Q/R destination reads invoke no calculation; the
claim does not mean that version-fixture creation performs zero calculations.

## Recovery, scope and next entry

The accepted A ancestor, retained B draft, accepted B implementation and this
handoff are separate durable jj revisions. No accepted parent was rewritten.
Source cache roots and immutable payload bytes remain available; no workspace,
source cache or evidence cleanup occurred. No push, merge or owner/main workspace
integration is included. To inspect or continue an earlier stage, use its fixed
revision in a separate jj workspace; do not run a global operation undo.

This is the full specified B focused gate, not an entire-repository test claim.
No live Blender launch, large-model geometry recomputation or new geometry visual
was performed; cache byte/counter/current-input checks provide the needed proof.
Filesystem acceptance ran on Windows/Pixi. Unknown historical implementation or
numerical versions intentionally remain unavailable rather than being adopted.

**Next entry is C Task 1:** fresh Superpowers brainstorming/Grill against these
actual accepted A/B artifacts and costs. Reassess whether semantic splitting needs
a new plan or a repair plan. B uses combined semantic publications with distinct
raw/processed layers; semantic output splitting and reusable intermediates have
not been implemented. Do not start C implementation from the earlier drafts.
