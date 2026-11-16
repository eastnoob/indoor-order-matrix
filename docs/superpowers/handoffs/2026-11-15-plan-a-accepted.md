# Plan A Handoff — locally verified implementation

Date: 2026-11-16

## Accepted history

Tasks 1–4 are accepted in the following non-empty jj commits, in order.
Final implementation technical acceptance is complete. This document becomes
the B entry point only after its separate handoff child passes documentation
review and is committed. The full handoff ID is then recorded externally by
`codex/parameter-cache-a-accepted` and the jj/ledger record; it is deliberately
not self-referenced in its own content.

1. `9d39d27032752a61ac98c73a1015152d4f48c614` — retained the pre-parameter
   cache migration fixtures and verified their original readers.
2. `bba814f87fda68f1778e5c43c073b797b0d1e24e` — typed package parameter
   schemas and immutable snapshots.
3. `8ebe4e5b7e2d7eb2fddc95f5330cfa52befbda02` — typed processor parameters in
   processed receipts and shared processing identity.
4. `7f521c903c688885454359f446b260f89505a4d1` — owner schemas, contract
   snapshots, warning status, CLI clearance resolution, and bound repair
   checkpoints.
5. `418be9199f73f38443f499549eed4dfcab677933` — parameter-aware raw/processed
   lookup, strict legacy adoption, and authenticated free-space reuse.

The workline started from planning audit commit
`92350a0ecb010c6b8f43005d705069094afb4b38`. Root was the only jj/history
writer; implementation, verification, and review agents did not commit.

## Implemented A contract

- `ParameterSchema` owns type, default, unit, bounds, choices, nullability,
  exposure, and impact declarations.
- `ParameterSnapshot` stores complete effective/calculated values, source
  labels, value contracts, impact declarations, schema version, and a canonical
  fingerprint. Nested mappings and sequences are detached and frozen.
- Identity projects only `recompute_required` parameters. Source labels,
  publication metadata, paths, timestamps, and requested warning values are
  excluded from calculation identity.
- Raw contracts accept an optional typed snapshot. Legacy contracts without one
  remain readable but cannot claim an exact typed hit without owner adoption.
- `RawCacheLookup` and `ProcessedCacheLookup` preserve frozen historical
  contracts/status/origin metadata. Warning reuse retains historical calculated
  values and exposes current requested values separately.
- Legacy adoption is explicit-path/exact-key only in A. The owner must rebuild
  a complete historical snapshot from the validated receipt; defaults are never
  borrowed to fill missing history. Existing bytes remain unchanged.
- Authenticated free-space readers verify the complete HMAC envelope and compact
  document before parameter comparison or historical reconstruction.
- `free_space`, `group-walk-distance`, and `group-axis-potential` own their
  exposed schemas. Downstream packages receive immutable upstream references and
  cannot rewrite upstream parameters.
- Directional repair checkpoints bind input, baseline scope, policy, method,
  source identity, and complete pair scope before resumption.

## Retained pre-A evidence

Fixtures are under `test/fixtures/cache_migration/pre_parameter_sidecar/` and
were generated from baseline commit `92350a0ecb010c6b8f43005d705069094afb4b38`.
The manifest is `manifest.json`; it records implementation hashes and opaque
test-only authentication metadata without storing a secret value.

| Family | Relative path | SHA-256 |
| --- | --- | --- |
| raw | `raw_processed/12a42760a9d8c2a9e021ba17505ba11fa4d816f2ef92c20339cd0d0b1260a283.json` | `889765d1d747e73ea661849ccd1e6bbff35a0545dd7fb26bab4fad562f5719a5` |
| processed | `raw_processed/processed-9bfb2a3d1e34c71025b174bc673547fbf2353b5a76de32e3eecf634f4a651b26.json` | `90bd3740b0bcfc745ce0c3f3f52737fb75e808ebb86cb2c01b7293d38646eeab` |
| authenticated free-space | `authenticated_free_space/d5da2d121dcccdaffe5f28553f4b09f3de43c855849bc31b39969a264f0075e6.json` | `3aea9720df2781c722e86d824e7e3b58cb948d54f8fab6a3ac9fdc0b381de0c5` |
| Blender wire | `blender_wire/88b3ce8b9d39c3ff9488e86893d877654048be74111b81c59afab293016451e7.json` | `29ec690bdb3741d73ca68c3c94c915ce7e4c9e84ee2e33ed4a80c32ab7e2e122` |

The original raw, processed, and authenticated free-space readers passed during
the A acceptance evidence. The retained Blender-wire file is preserved, but its
backend-version contract does not match this checkout, so it is not claimed as a
current no-recompute hit.

## Final implementation and acceptance

Final nonempty implementation commit: `92ff7d521415c95d505c2e35eca60781e09b7f96`.
It descends from the preserved audit candidates, Tasks 1–4 and the byte-pinned
pre-A fixtures above. Root alone wrote jj history. Unaccepted candidate IDs
`0733628b3d54f53b1bd35db0742b472264a64b02` and
`230fc70a3e9cc53dea4c943863122431b4cecf54` remain explicit history, not earlier
A acceptance claims.

- Final complete gate: **533 collected / 533 passed**, **520.81 seconds**,
  zero failures, errors, skips, xfail/xpass or deselected mandatory nodes.
- All **315** frozen source/test/config/fixture hashes matched before/after
  acceptance and a fresh actual-byte comparison immediately before commit.
- Independent whole-A review's seven findings are addressed by its scoped
  fix review plus the [checkpoint prerequisite](../plans/2026-11-16-checkpoint-semantic-prerequisite.md).
  Final prerequisite verdict: **SPEC PASS / QUALITY APPROVED**.
- Prerequisite TDD: **23 behavioral RED failures**, then **155/155** covering
  route/clearance/package passes. A first missing-PYTHONPATH collection error
  is retained separately and is not counted as behavioral RED.
- Additional real-search probe: base → identical → changed → restored policy
  performs exactly **two** searches, keeps two versions, and restores the
  original observations and unchanged checkpoint bytes.
- Real typed processor and grid 1 → 2 → 1 tests check execution values/counts,
  including **16 versus 64** actual lattice samples and zero recalculation on
  restoration. Persisted nested JSON type/choice incompatibilities are rejected.
- Authenticated historical contract/document checks, warning-only calculated/
  requested values, rejected-checkpoint retention errors, downstream immutability,
  retained raw/processed serialization and complete retained IFC comparisons
  are included. Historical fixture/hash expectations were not modified.

The test-only package junction and importlib mode solve detached-workspace
collection without changing application imports or omitting free-space nodes.
The retained IFC owner independently rebuilds current sources and its complete
historical contract, forwarding that context through the second axis readback.

All four pre-A families reopen with their original validated reader context.
Blender-wire preflight supplies saved backend versions for historical readability
and separately verifies a current-version mismatch misses. A does not claim
current-runner cross-implementation migration compatibility; B must prove it.

## Durable evidence

Absolute directory:
`D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-a-implementation/.superpowers/sdd/2026-11-15-package-owned-parameters`.

Authoritative receipt: `plan-a-final-acceptance.json`, SHA-256
`c097dfb3f002077cbf6afee6478ba016f4ef5549b63cdc7e869733d6f002f9d1`. It records the full implementation ID, command/cwd/environment,
exact outcome, fixture-manifest hash and evidence hashes. The final frozen run
is `task-5-semantic-final-20261116/` (collection, metadata, log, JUnit,
before/after hashes and `verified.json`).
The exact command uses Pixi/Python **3.12.13**, active-workspace PYTHONPATH,
`pytest --import-mode=importlib -q -ra`, the recorded package-name junction and
all 14 required files. PYTEST_ADDOPTS was unset.

Source review: `checkpoint-semantic-review-result.txt`.
Behavioral/covering evidence: `checkpoint-semantic-red-behavior.*` and
`checkpoint-semantic-green-2.*`.
Restoration probe: `checkpoint-semantic-policy-restoration.json`.
All rejected reviews, failed candidates and prior 458/509-node aggregates remain
in the same directory; `progress.md` is the resumption ledger.

## Verified scope and limits

This accepts A's package-owned parameters, snapshots, impact projection,
immutable raw/processed lookup metadata, strict explicit historical adoption
and checkpoint guard. No full repository suite or live large-model IFC/Blender
recomputation was executed. Large retained comparisons were copied from their
original workspace after checking their oracle hashes, rather than recalculated.

B and C remain unimplemented at this handoff. No push, merge, owner integration,
old-cache deletion, workspace cleanup or user visual acceptance is implied.

## Plan B entry

Create `parameter-cache-b-implementation` with `jj workspace add --revision`
set to this document's externally verified full accepted handoff commit. Record
that ID and the separate implementation ID above and check ancestry. Do not use
the planning revision, stale planning siblings or an empty working-copy commit.

B consumes these exact snapshots/codecs and preserved fixture bytes. It owns
model-side source/run locations, immutable CacheStore publication, locks,
catalog/list/delete, authentication domains and verified copy/migration.
Fresh-process P/Q/R proofs must cover all four families through actual
destination runners, with empty-sidecar sentinel controls. Strict historical
readability is not a substitute for those gates.

Static preflight reports `plan-b-complete-preflight-high-review.txt` and
`plan-b-runtime-integration-map-result.txt` identify durable source/lookup/
provenance bindings, capture-finalization checks, distinct trusted execution and
model storage roots, actual UI/main/worker/CLI seams and real-producer sentinels.
They are advisory planning evidence, not B acceptance.

C begins only after accepted B and fresh Superpowers/Grill on real artifacts.
Semantic output independence remains C work; completed intermediate runtime is
deferred absent a concrete accepted package need.
