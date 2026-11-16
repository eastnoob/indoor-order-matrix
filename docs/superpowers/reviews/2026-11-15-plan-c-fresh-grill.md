# Plan C fresh review of accepted A/B

Date: 2026-11-16. Status: Task 1 accepted, proceed with C. Independent baseline
and static specification/quality review passed; production code is unchanged at this gate.

## Actual accepted entry

- A implementation: `92ff7d521415c95d505c2e35eca60781e09b7f96`; A handoff ancestor `488d0d4e439a7c6674d2973f3ddbaa9b34fa2fe8`.
- B implementation: `3b160264c80dbba631fbe90ab02dca48bc348e0d`; accepted handoff `1085b5be3d7602e8a43935b5596dd656e7ee567c`.
- `jj git push --remote origin --bookmark codex/parameter-cache-b-accepted` succeeded and the origin bookmark resolves to the exact handoff. This push was explicitly requested on 2026-11-16. No merge or main integration.
- C workspace: `parameter-cache-c-implementation`, `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-c-implementation`; initial change `nltxmuss`, commit `011759fa`, empty. Root alone writes jj history.
- The task-owned ignored ledger is `.superpowers/sdd/2026-11-15-output-port-and-intermediate-cache/progress.md`. No pre-existing C code/dirty edits.
- B acceptance: 786/786, no excluded/skipped outcomes; source and fixture evidence is in the [B handoff](../handoffs/2026-11-15-plan-b-accepted.md). Independent C baseline evidence lives in `D:/temp/oa-pytest-c/b-baseline-20261116`; its joint-coverage PASS is detailed below.

## Inventory of existing receipts

Inventory JSON: `.superpowers/sdd/2026-11-15-output-port-and-intermediate-cache/inventory/inventory.json`, SHA256 `ef5a35bf86a5db506934f5a55e6ff8388702d49e33127d922e47e440010d74d4`.
The independent reader copied five known B acceptance sidecars into C scratch,
compared every copied byte, listed the copies through actual B CacheStore and
validated the original acceptance contexts with current owner callbacks. Source
sidecars were rehashed unchanged. Listing is performed on copies because it may
quarantine invalid data. The JSON retains full addresses, contracts, snapshots,
payload/receipt digests, validators and the scope of currentness verification.
No secret key values are recorded.

| Existing family/kind | Verified fixture versions | Saved owner snapshot | Stored upstreams |
| --- | --- | --- | --- |
| potential combined raw | original key `12a42760a9d8...` | Historical, no A snapshot | None |
| potential combined processed | typed migration-test values 1/2; legacy recipe | Typed `migration-test/1` or historical absent | Exact combined raw |
| authenticated free-space combined raw | spacing 1/2 | Historical spacing 1; typed spacing 2 | None |
| Blender native wire combined raw | two versions | No A snapshot in wire | None |
| distance combined raw | unconstrained and clearance .2/.2/.5 | `group-distance-parameters/1` | None |

Thirteen non-demo entries are storage-complete and owner-validated in their
original fixture contexts. All are `combined`; no standalone semantic output
exists yet. Distance version fixtures use `_missing_bundle()` and demonstrate
real runner/storage behavior with missing geometry. They do not establish actual
IFC distance values. Numerical evidence will reuse `retained_trial` and
`actual_inputs` with their pinned 37 groups, 95 members and 666 pairs.

## Fresh questions, answers and rulings

1. **Where is route coupling?** `group_distance_input_fingerprints` includes clearance in query and free-space samples in occupancy. The combined source envelope, query and output provenance all retain that complete context. Filtering only output channels is insufficient.
2. **Can Euclidean stand alone?** Yes. `_group_geometry` already provides the original union centroid/audit. Extract the exact existing `math.dist` and invalid/not-available precedence into one shared primitive. New Euclidean sources retain only group/member/geometry/plane/origin evidence; path sources retain their real route/witness/uncertainty. No numerical formula changes.
3. **Can verified combined entries be adopted?** Yes, by `_run_contract`, `_distance_raw_validator`, `load_raw_bytes` and `_cached_sources_match`, using independently rebuilt current context. Reopen B bytes before projection; missing original A snapshot stays historical. No producer may run while adopting. Preserve original combined payloads/identities; provenance is external.
4. **What enters processing?** Only the selected typed view bytes/ref and explicit current processor recipe. Historical core serializers/digests remain untouched. `load_raw_port` must compare saved declarations with independently supplied current owner declarations before a processed hit.
5. **Can potential consume it?** Yes. Existing registration joins by group IDs and checks member/plane/source facts. Keep legacy full-query validation for combined inputs; add a geometry-only registration projection for semantic Euclidean. `_distance_modulated_outputs` already accepts cached pure-axis channels.
6. **Are deletion edges available?** B storage supports them, but current combined receipts lack the required path→free-space and modulation chains. They must be built and proved with nonempty actual data. Same-package pure-axis→modulation belongs to full CacheStore addresses because the old package graph forbids self-package edges.
7. **Does a completed intermediate need persistence now?** No separate reusable stage has been established that the selected outputs and existing bound route checkpoints do not serve. Task 7 documents the explicit future boundary; it does not add intermediate runtime, a generic decorator or another backend.

### Concrete plan reconciliation

- Actual owner keys are `grid`, `query_context`, `free_space_result_ref`, `clearance_mode`, `clearance_policy`. The three metre thresholds are nested in the last field. Euclidean selects no owner knobs; path declares the five existing keys. Full historical audit stays available.
- B `cache_directory` alone preserves the legacy flat API. Combined adoption tests provide `temporary_cache_root` or a saved model locator as well. No B compatibility repair is needed.
- Historical source mappings can contain an absolute IFC locator and session-sensitive capture digests. C will explicitly project recognized factual source forms and actual sorted group geometry. New semantic targets use that canonical source; historical `_pair_id`, combined APIs and the kernel's historical-pair observation API remain unchanged. Compare new C numerical views by sorted group IDs; record legacy target mapping only as external adoption provenance. Unknown source forms require a meaningful explicit factual identity, never a broad string scrub.
- A legacy wire `ResultRef(kind, result_id, digest)` cannot identify its B address. Path callers with saved samples must explicitly supply the exact current owner-validated full storage reference and its existing owner callback. Verify original bytes, document ref and matching current lattice/query/sample binding. No fabricated upstream or ambiguous history scan. Euclidean needs neither path selector nor callback. This is a narrow C controller/adapter seam, not a B storage change.
- Mixed-sidecar callbacks dispatch only explicit supported legacy/semantic schemas. The existing `CacheStore.migrate_to` remains authoritative.
- After reviewed numerical/serializer parity, update only changed `current_content_implementations` hashes in `legacy_cache_compatibility.json`. Preserve original hashes, fixture bytes and numerical-version rejection.

## Intended dependency graph

```text
path raw --------------------> exact owner-validated free-space B entry
Euclidean processed ---------> Euclidean raw
modulation raw --------------> Euclidean processed
modulation raw --------------> pure-axis raw
```

No route/free-space edge reaches Euclidean or its modulation. Each arrow is a
complete source/package/kind/layer/version address and must survive relocation
or become explicitly unavailable after actual deletion.

## Gate and limits

Independent static reviewers: `c_distance_review`, `c_potential_review`;
incremental document review `c_task1_review`: **SPEC PASS / QUALITY APPROVED**.
No B production blocker found. Exact native upstream callbacks, canonical target
joins, scratch-copy inventory and adapter verification were reconciled in the plan.

Independent verifier `c_b_baseline` ran all fourteen B files: 786 collected,
780 passed and six failed in 479.52 seconds. Five failures were missing retained
hierarchy artifacts; one was C's absent `.pixi` Python path. After byte-verified
fixture copies and a junction to accepted B's Pixi environment, only those exact
six nodes were rerun: six passed in 468.51 seconds, exit 0. Joint coverage is
786 distinct passing nodes, including all 32 mandatory nodes, with no skip,
xfail, error or exclusion in the accepted union. This is not a second complete
786-pass execution. Both original and corrected XML/log/metadata remain retained.
All 712 frozen code/test/config hashes remained unchanged; 30 compatibility
source hashes and 12 inherited fixture hashes match. Two checkout test files
differ from B only in LF/CRLF and have independently recorded normalized equality.

Acceptance receipt: `D:/temp/oa-pytest-c/b-baseline-20261116/acceptance-result.json`,
SHA256 `adb156d30dc26116aa42def5ff427fd1bd08a2aa9d86fdea355846122e9d92e7`.
Corrected-node XML SHA256 `3a3f0ad1e7f0d0958d9be1204b32613fe0da7f51fbf886c683c67736d804c6b4`.
Exact failed IDs, commands, cwd, Python/Pixi/module paths and per-node union are
in the same evidence directory. No production edits preceded this gate.

Visuals are omitted because exact bytes, real numerical parity, callback
sentinels, currentness and nonempty deletion chains establish the required
behavior. No new Blender launch or large-model geometry extraction is needed.
