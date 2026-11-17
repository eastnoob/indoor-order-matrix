# Plan C handoff — independent semantic output ports locally accepted

Prepared 2026-11-17. Plan C's implementation has independent numerical acceptance and **SPEC PASS / QUALITY APPROVED**. The accepted cumulative implementation is `4edfdb504f48f88612375471f5e9bcc68dcc45ae`. Its tree matches tested candidate `c4917bc7340cb7c21276e9a43448b1f62e66cb13`; root rechecked all 723 frozen hashes before the completion commit. This handoff is a separate documentation change. Its commit ID is identified externally by the documentation commit/bookmark, rather than embedded in its own contents.

## Result and business scope

C gives straight-line distance and route distance separate immutable semantic publications. Changing clearance or route samples reuses straight-line readings and their processed proximity; the route version changes independently. Selected processing binds exact selected raw bytes and an explicit current recipe, retaining immutable historical audit without a raw or stale numeric fallback.

Pure-axis and distance-modulated publications are also independent. Enabling modulation reuses the saved pure-axis result. Exact deletion invalidates only true descendants, while moving the sidecar reuses verified copied results without numerical producers. The retained real-data checks preserve 37 groups, 95 members and all 666 distance pairs, plus 1,369 addressed modulation cells and 1,332 nonself values.

The [C plan](../plans/2026-11-15-output-port-and-intermediate-cache.md) and [fresh A/B review](../reviews/2026-11-15-plan-c-fresh-grill.md) define this opt-in scope. Existing combined package APIs, numerical formulas and original payloads remain compatible. Task 7 is an accepted **DESIGN ONLY** boundary; no intermediate runtime was added.

## Accepted revisions and remote state

| Stage | Accepted full revision | Scope |
| --- | --- | --- |
| A implementation | `92ff7d521415c95d505c2e35eca60781e09b7f96` | Package-owned immutable parameter snapshots and independent currentness |
| A accepted handoff | `488d0d4e439a7c6674d2973f3ddbaa9b34fa2fe8` | Accepted A entry for B |
| B implementation | `3b160264c80dbba631fbe90ab02dca48bc348e0d` | Model-side CacheStore, lifecycle and migration |
| B accepted handoff / C base | `1085b5be3d7602e8a43935b5596dd656e7ee567c` | Actual accepted B entry, independently reverified in C |
| C Task 1 | `b0cc0c8b22c44a80673a5ccc14bed884e06f13eb` | Fresh actual-A/B ruling: proceed, without a B prerequisite repair |
| C Task 2 | `5a973d1c8c0e52adfa211cee267c87aea42e11ce` | Semantic raw wrapper and current-owner admission; unchanged legacy JSON |
| C Task 7 | `1c516dde499b0767b040de40ad279c3da7877586` | Independently reviewed intermediate design; runtime deferred |
| C Task 3 | `cb5c3d5138845341aa6c12d67024b4b35f7c427a` | Independent Euclidean/path producers, projections and verified combined adoption |
| C Task 4 | `ce84f3d56179f877e42cfc0ab608e8aa6c894253` | Selected-byte processing, warning audit and read-only processed loader |
| C Tasks 5/6, review repairs and accepted cumulative implementation | `4edfdb504f48f88612375471f5e9bcc68dcc45ae` | Pure/modulated ports, real lifecycle/migration proof, path-version and graph-admission repairs, and the bounded test-sentinel correction |

The accepted cumulative tree is identical to independently tested candidate `c4917bc7340cb7c21276e9a43448b1f62e66cb13`. The local completion commit is nonempty and uses the explicit three-path correction fileset: `test/test_group_axis_distance_modulation.py`, the C plan and architecture memory. The earlier cumulative implementation remains in its ancestry. The new empty working-copy revision after that completion was `a041ba52`; it is not the accepted implementation ID.

The user-authorized `jj git push --remote origin --bookmark codex/parameter-cache-b-accepted` completed for B. Root directly rechecked both local and `@origin` bookmarks at B handoff `1085b5be3d7602e8a43935b5596dd656e7ee567c`. **C is local only: no C push, owner/main integration, merge or cleanup was performed.**

C workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-c-implementation`. Root is the sole jj history writer. Rejected candidates `85d48527d918aac507f704015005127929963c5a` and `0b1789dbbb923595c8b8a763653cfd63e3f32ca6` remain preserved. No repository-wide undo/reset or source/cache deletion is part of this delivery.

## Public entry points and compatibility

The primary opt-in interfaces are:

```python
OutputPortRef(...).address  # Full B CacheAddress.
OutputPortContract(...).identity / .target_ids / .channels
RawPortPublication(contract, raw_view, parameter_snapshot=None)
ProcessedPortPublication(raw_ref, processed_output, identity)
PortRun(publication, cache_hit, status, cache_status, cache_reuse, cache_location)

bind_raw_port(contract, raw_view, *, parameter_snapshot=None)
save_raw_port(store, publication)
load_raw_port(store, contract, *, requested_parameters)
processed_port_key(raw, processor)
run_port_processor(raw, package, *, store, current_raw_contract, requested_raw_parameters)
load_processed_port(store, reference, *, current_raw_contract, requested_raw_parameters, processor)
validate_port_payload(payload, context, *, raw_publication=None)

euclidean_port_contract(bundle, *, parameters)
distance_port_contracts(bundle, *, parameters, repaired_result=None, free_space_ref=None)
evaluate_euclidean_port(bundle, *, parameters)
evaluate_path_port(bundle, *, parameters, repaired_result=None, store=None,
                   free_space_ref=None, free_space_validator=None)
run_group_distance_ports(bundle, *, store, parameters, repaired_result=None,
                         legacy_entry=None, free_space_ref=None, free_space_validator=None)
run_euclidean_processed_port(bundle, *, store, parameters, processor)

bind_port_distance_modulation(raw_port, processed_port, *, store, processor,
    current_raw_contract, requested_raw_parameters, compatibility, dependency_graph)
run_group_axis_output_ports(envelopes, *, store, parameters, distance_raw=None,
    distance_processed=None, distance_processor=None, current_distance_contract=None,
    requested_distance_parameters=REQUIRED, compatibility=None, dependency_graph=None)
```

`project_verified_distance_ports` reopens an exact original combined B entry through its original owner validator before pure projection; neither semantic producer runs. Its independently supplied current bundle, owner intent and native selector prevent a saved contract from authorizing itself. `adapters/free_space_distance.py::build_distance_free_space_validator` owns the original native wire/request/context and exact-sample checks. `features/group_axis_potential_field.py::project_distance_geometry_registration` supplies the geometry/member/plane registration projection while retaining historical combined-query admission.

`OutputPortRef.output_port` names semantic kind, such as `euclidean_distance`; `.layer` names `raw` or `processed`. Existing `EvidencePackageChannelReference.port` retains its historical raw/processed meaning. Input identity, inner serializer content digest, selected-view byte digest and full storage-envelope byte digest remain distinct bindings. Full owner snapshots are immutable audit rather than wholesale inputs to a selected port key. Storage locators and current UI selections do not define computation identity.

`run_port_processor`, `load_processed_port` and the modulation binder require independently supplied current raw-owner intent. Explicit `None` declares a schema-less raw owner; a historical snapshot cannot replace a current typed declaration. `run_group_axis_output_ports` requires explicit distance intent when modulation is enabled; its disabled pure-axis request can omit distance arguments and `requested_distance_parameters`. Potential's own parameter snapshot cannot substitute for the upstream distance owner's intent.

The read-only processed loader returns a saved publication or a miss/diagnostic failure and never calculates or quarantines. Owning runners retain corrupt selected bytes through B quarantine before recalculating only the responsible port. Warning/metadata reuse keeps original result bytes and calculated snapshots while `PortRun.cache_status` separately reports requested/current values. B reuse origin and storage location remain visible.

## Per-port parameter and dependency table

Each upstream is a complete `CacheAddress(source_fingerprint, package_id, output_port, layer, identity)`; semantic references additionally bind the exact selected payload bytes.

| Semantic kind / layer | Identity inputs and selected owner parameters | B upstream addresses | Verified independence |
| --- | --- | --- | --- |
| `euclidean_distance` / raw | Factual source/group/member geometry, canonical plane/frame/origin, centroid/status components, exact pair/channel scope and Euclidean algorithm/schema; empty owner parameter selection | None | Excludes clearance, route grid, samples, free-space, route query/occupancy and repair |
| `path_distance` / raw | Actual route graph/grid/query/occupancy/witness/repair scope; `grid`, `query_context`, `free_space_result_ref`, `clearance_mode`, `clearance_policy`; NetworkX and Shapely recipe versions | Exact independently owner-validated native free-space entry when saved samples are used | Route-only changes create another path version while Euclidean remains reusable |
| `euclidean_distance` / processed | Complete selected raw ref/byte SHA256, processor ID/version and effective computation projection | Exact Euclidean raw | No unrelated route/full-owner audit dependency; warning/metadata values do not fork the calculation key |
| `axis_potential` / raw | Existing axis inputs/scope; no modulation-switch selection | None | Modulation switch and distance availability do not recalculate pure axes |
| `distance_modulated_axis_support` / raw | Existing support-times-processed-proximity formula, own enable switch, exact pure/processed refs and geometry/member/plane registration | Exact pure-axis raw and processed Euclidean | No path/free-space edge; unavailable Euclidean inputs redact nonself values |

The same-package pure-axis-to-modulation edge belongs to B's full-address graph; historical package-graph self-edge rules remain intact. The binder materializes adjacency once and reuses core closure/cycle plus current/upstream declared-edge checks before cache admission, so warm hits and misses have the same graph gate. Package owners admit numerical currentness; B owns byte integrity, immutable storage, migration and derived orphan state.

## Independent numerical acceptance and evidence

The authoritative receipt is `D:/temp/oa-pytest-c/final-repair-20261117/independent/verified-union.json`, with the accompanying `review-union.md`. Independent verifier `c_task5_acceptance` reconciled exact collection/XML node identities and every required scope. Implementation reviewer `c_whole_review` returned **SPEC PASS / QUALITY APPROVED**. The same reviewer completed the bounded final five-document delivery review with **SPEC PASS / QUALITY APPROVED**, no outstanding Critical/Important finding; receipt: `D:/temp/oa-pytest-c/final-repair-20261117/delivery-review.json`. The separate documentation commit and local accepted bookmark identify this handoff.

| Final execution / scope | Actual result | Time / interpretation |
| --- | --- | --- |
| Original fourteen-file run on `0b1789dbbb923595c8b8a763653cfd63e3f32ca6` | 620 collected/executed; 619 passed, one failed; exit 1 | 3590.063 s; retained failed run |
| Complete corrected mixed-migration node on `c4917bc7340cb7c21276e9a43448b1f62e66cb13` | One collected/executed; one passed; exit 0 | 768.234 s, with fresh scratch and the accepted environment |
| Full fourteen-file evidence union | 620 distinct required passing nodes | 619 original passes plus one corrected pass; 621 testcase executions across both runs |
| Task 5 three-file union | 70/70 passed | 69 original passes plus the corrected node |
| Task 6 five-file union | 211/211 passed | 210 original passes plus the corrected node |
| Original Task 8 thirteen-file union | 600/600 passed | 599 original passes plus the corrected node |

This is an explicit evidence union, **not a second full 620-node run**. The original failed execution is not relabelled as passing. The accepted union has no missing, skipped, xfailed, xpassed, deselected or otherwise excluded required nodes. All seven Task 6 additions, both repaired-behavior regressions and the original Task 5 62-node scope are individually mapped in the union receipt.

The independent verifier checked the same 723 frozen paths before/after execution and after review, all 41 fixed fixture files, and the 23 sealed original-evidence files. Only the corrected test function and the two named plan/memory documents differ between original and corrected candidates; outside-function bytes, other module AST, signature and decorators match. Root subsequently verified zero tree difference between tested `c4917bc7340cb7c21276e9a43448b1f62e66cb13` and accepted completion `4edfdb504f48f88612375471f5e9bcc68dcc45ae`, with all 723 actual frozen hashes equal. Final handoff documentation is recorded separately from that implementation freeze.

| Evidence artifact | SHA256 |
| --- | --- |
| `final-repair-20261117/independent/verified-union.json` | `b1a738ef0482c9e8a4393a094c191fca065351820055e690453bc54559c97536` |
| `final-repair-20261117/independent/review-union.md` | `7a935f9b853d446096fcc0d4ecd03c48ed0516c23782474cd0bb67e3e0891496` |
| Original 723-path manifest, `final-20261116/frozen.json` | `2c4e39ae27f738f4cf79ba683fc67ea5e804ec8f7e09a5e27d8b5ec50d094679` |
| Corrected 723-path manifest, `final-repair-20261117/frozen.json` | `197d428e08227962733a51e28419c76cfcf6b61a8870efdcb6b133129267417c` |
| Seal of 23 original evidence files, `final-repair-20261117/original-evidence-seal.json` | `8656538f00c9ad9c8f38569bbdefa78228105338779bfdf2d50f26d7b7a489ae` |
| Original failed-run XML, `final-20261116/independent/focused.xml` | `fa36b8c6656af34249052cfd2c5a034a20bd59fbc65331df2ffd20d5f14e5bb0` |
| Corrected-node XML, `final-repair-20261117/independent/focused.xml` | `a80212fc7ff97027bd9c188484ed39fe6ebb003c1f813d15dd714d6ea1398ec6` |

Paths in this table are relative to `D:/temp/oa-pytest-c`. Each independent directory also retains `collect.log`, `focused.log`, command metadata, environment/module paths, node outcomes or reconciliation, and before/after/review hash records. `final-repair-20261117/root-precommit.json` records all 723 matching paths, the exact cumulative changed files and no whitespace issues; `root-precommit-whole-c.diff` preserves the complete precommit delta. These existing receipts, rather than prepared driver files or author reports, establish acceptance.

Earlier independent gates remain accepted:

| Gate | Actual outcome | Frozen files | Receipt under `D:/temp/oa-pytest-c` |
| --- | --- | --- | --- |
| B rebaseline in C | 786 distinct passes: 780 initial plus six repaired setup-node reruns; no second full run | 712 exact | `b-baseline-20261116/acceptance-result.json` |
| Task 2 prescribed three files | 182/182 passed; SPEC PASS / QUALITY APPROVED | 715 exact | `task2-20261116/independent/verified.json` |
| Task 3 prescribed five files | 170/170 passed in 733.734 s; SPEC PASS / QUALITY APPROVED | 721 exact | `task3-20261116/independent/verified.json`, `review.md` |
| Task 4 prescribed five files | 314/314 passed in 665.281 s; SPEC PASS / QUALITY APPROVED | 721 exact before/after/review | `task4-20261116/independent/verified.json`, `review.md`, `node-outcomes.json` |

Task 4's exact independent file counts are `test_output_port_cache.py` 99, `test_group_distance_output_ports.py` 19, `test_group_distance_processed_ifc.py` 67, `test_evidence_package_processing.py` 60 and `test_evidence_package_processed_readback.py` 69. Its manifest SHA256 is `de789992d4726d92a1b3e7e97e272d7a0a3746079999b83259deeb6b3aefa0e9`; XML SHA256 is `2ad142f9cb8ce5b3a1a9f574e52e47d6c13b12f72db14d2016351bfef32d5887`.

## Verified business behavior

- Clearance `1 → 2 → 1` versions retain the common Euclidean publication and restore the original path cache version. Shapely-version changes invalidate path identity; restoring the original recipe reuses saved refs. Euclidean producer callbacks remain forbidden during the independent reuse probes.
- All 666 standalone Euclidean readings match retained real geometry. A bounded actual path/witness case matches the existing route calculation with the Euclidean primitive forbidden. Alternate native sampling changes 0.1 m / 24,442 cells to 0.2 m / 6,222 cells, with new-owner acceptance, old-owner rejection, changed route context and unchanged Euclidean selected refs/bytes/processed key.
- Verified combined adoption runs no semantic producer, preserves original combined bytes and calculated audit, and rejects wrong current inputs or tampered originals. A missing original typed snapshot stays historical.
- All 666 processed proximity readings reuse under clearance 1.0 to 2.0 with the processor forbidden, exact refs/bytes and separate historical/current parameter maps. Schema/field/type/unit/nullable/impact and typed/None checks precede callbacks; refreshed outer hashes cannot authorize unknown schemas or invalid inner references/digests.
- Actual modulation retains 1,369 addressed cells, including the existing self-cell interpretation, and 1,332 computed nonself support-times-proximity values. Cold, warm and one-shot adjacency requests pass the same graph admission. The pure-axis evaluator stays forbidden while the modulation switch changes. Current-owner/current-recipe drift and missing Euclidean prerequisites cannot expose prior nonself numeric values.

### Nonempty lifecycle graph and mixed-codec migration

Task 6's seed contains nine real owner-readable B entries: original native wire, one nonempty path, selected Euclidean raw/processed, pure-axis, modulation, an independent three-group Euclidean raw/processed sibling, and an unchanged legacy combined-axis publication. Before deletion all entries are complete; the native document has 24,442 cells and modulation has 1,332 usable nonself values. The stored edges are exactly:

```text
path raw --------------------> exact native free-space B address
Euclidean processed ---------> exact Euclidean raw address
modulation raw --------------> exact Euclidean processed address
modulation raw --------------> exact pure-axis raw address
```

Every deletion uses a fresh copied seed and requires `delete_exact(address) is True`:

| Deleted actual address | Observed result |
| --- | --- |
| Path raw | Euclidean raw/processed, pure-axis, modulation and independent versions remain usable with original refs/bytes |
| Native free-space | Path is orphaned/unavailable as a positive dependency-validation control; Euclidean, pure-axis and modulation remain usable |
| Euclidean raw | Its processed and modulation descendants become orphaned/unavailable; all 1,332 nonself observations are `None`; pure-axis and independent versions still hit |
| Euclidean processed | Modulation becomes orphaned/unavailable with all 1,332 nonself observations `None`; Euclidean raw, pure-axis and independent versions still hit |

Surviving receipt/payload bytes, including orphaned descendants, remain unchanged. Unavailable results are not persisted as complete replacements. Source seed and original native fixture-store bytes remain intact. Path/free-space deletion probes forbid numeric modulation as well as unrelated producers; true Euclidean deletion uses the existing unavailable-value redaction helper.

Mixed migration uses B's existing `migrate_to` with explicit `package:layer` callbacks: known semantic schemas use their semantic validator, legacy combined bytes retain their original owner decoder, and native wire retains its independent native owner validator. All nine exact addresses copy successfully, source remains a rollback copy, destination entries are owner-readable, and ordinary selected/raw/processed/pure/modulation/legacy requests return original refs with `cache_hit` and `migrated_reuse`. Payload/receipt bytes and source-binding equality are checked. Inherited B migration tests retain authenticated key-domain coverage; C does not replace those owner codecs or authentication boundaries.

Raw Euclidean, path, pure-axis, numeric modulation and configured processing remain forbidden throughout migration and semantic reuse. The final ordinary legacy request has no configured processor. Only that call receives a scoped proxy which first asserts `package.output_processor is None`, delegates the original status facade exactly once with `package_freshness="fresh"`, and requires `OUTPUT_FUNCTION_NOT_CONFIGURED` with `outputs == ()`. The facade validates/serializes existing raw content but never calls `processor.function`; the strict processing sentinel is restored when the scoped context exits. The corrected full node executed its legacy hit/ref and all source/destination/native byte assertions successfully.

## Environment, commands and warnings

The actual environment is Windows 11, Python 3.12.13 through accepted B's Pixi environment, with no new installation:

- Manifest: `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-b-standard/pixi.toml`.
- Python: `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-b-standard/.pixi/envs/default/python.exe`.
- C alias/cwd: `D:/PROJECTS/understandOtherPackage/order_analyzer_c_test_alias`.
- `PYTHONPATH`: `D:/PROJECTS/understandOtherPackage;D:/PROJECTS/understandOtherPackage/order_analyzer_c_test_alias;D:/PROJECTS/understandOtherPackage/order_analyzer/OCTA_toolbox-master`.
- `PYTEST_ADDOPTS` removed; `--import-mode=importlib`, file-backed logs, unique scratch and JUnit XML retained.

The original numerical command covered these fourteen files through the accepted manifest; exact absolute arguments are in `final-20261116/independent/focused.meta.json`:

```powershell
pixi run --manifest-path "D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-b-standard/pixi.toml" pytest --import-mode=importlib test/test_output_port_cache.py test/test_group_distance_output_ports.py test/test_group_distance.py test/test_group_distance_evidence_package.py test/test_group_distance_processed_ifc.py test/test_free_space_distance.py test/test_group_axis_distance_modulation.py test/test_group_axis_potential_field.py test/test_evidence_package_output.py test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py test/test_evidence_package_lifecycle.py test/test_cache_store.py test/test_cache_migration.py -q -ra --junitxml=D:/temp/oa-pytest-c/final-20261116/independent/focused.xml --basetemp=D:/temp/oa-pytest-c/final-20261116/independent/pytest-temp
```

The corrected-node command is recorded in `final-repair-20261117/independent/focused.meta.json`:

```powershell
pixi run --manifest-path "D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-b-standard/pixi.toml" pytest --import-mode=importlib test/test_group_axis_distance_modulation.py::test_mixed_port_cache_migrates_original_owner_codecs_without_producers -q -ra --junitxml=D:/temp/oa-pytest-c/final-repair-20261117/independent/focused.xml --basetemp=D:/temp/oa-pytest-c/final-repair-20261117/independent/pytest-temp
```

Both invocations emitted Pixi's existing `WARN ignoring SSL_CERT_DIR: no certificates found` for the accepted environment's `Library/ssl/certs` directory. The original run also emitted `geometry_views.py:124: RuntimeWarning: Plan face union topology retry on a 1e-12 plane-unit grid`; corresponding nodes passed. The corrected node had no geometry RuntimeWarning. These warnings remain recorded rather than suppressed. No mandatory missing retained artifact was waived.

## Preserved failures and bounded repairs

Task 5 diagnostic candidate `85d48527d918aac507f704015005127929963c5a` ran 62 exact collection/XML nodes in 1807.437 seconds: 54 passed and eight failed during setup because one retained trend-envelope file was absent. All 23 modulation and 19 distance-port nodes passed, but source review also found that a warm modulation hit bypassed graph admission; the candidate was not accepted. Root copied only `outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/envelopes.json` from accepted B. Main/B/C SHA256 is `de0434b947e562b0ed9f486fe134da118e5d25b81199582dc9374903336534c0`, with originals unchanged. The diagnostic was not retried.

The cumulative source repair adds Shapely to the path recipe and applies existing core graph normalization, cycle and declared-edge admission before modulation hits or misses. It changes no numerical formula, field core, storage backend or legacy codec. Both repaired behaviors passed the original fourteen-file run.

The original final candidate `0b1789dbbb923595c8b8a763653cfd63e3f32ca6` then had the single test-sentinel failure described above, after all nine migration entries and semantic reuse assertions passed. The correction changes only that test function plus the necessary plan/memory records; all original numerical producer, ref and byte assertions remain. The full corrected node passed independently, allowing the explicit 619+1 union. Both failed candidates and original receipts remain available; acceptance does not erase their failures.

## Whole-C modified files and compatibility profile

The final C delivery has these 18 paths relative to accepted B, including this separate handoff document:

```text
adapters/free_space_distance.py
docs/indoor_layout_evaluation_matrix_architecture_memory.md
docs/software-architecture.md
docs/superpowers/designs/2026-11-15-explicit-intermediate-contract.md
docs/superpowers/handoffs/2026-11-15-plan-c-complete.md
docs/superpowers/plans/2026-11-15-output-port-and-intermediate-cache.md
docs/superpowers/reviews/2026-11-15-plan-c-fresh-grill.md
features/group_axis_output_ports.py
features/group_axis_potential_field.py
features/group_distance.py
features/group_distance_output_ports.py
features/legacy_cache_compatibility.json
features/output_port_cache.py
test/test_free_space_distance.py
test/test_group_axis_distance_modulation.py
test/test_group_distance_output_ports.py
test/test_group_distance_processed_ifc.py
test/test_output_port_cache.py
```

Within `legacy_cache_compatibility.json`, the only changed mapping is `current_content_implementations["features/group_axis_potential_field.py"]`, from `420e312c98ee5fc5e72813ef236a693f70e329e4e7d47ee2c73701987d576f35` to `f64835b17ce3358eed89bc3baee6f73ba961d80b12942ba42a6d93c793ee350d`. Original implementation hashes, numerical dependency/version rejection and fixture bytes remain unchanged. This is the narrow reviewed content-implementation allowance, not a new universal legacy-acceptance rule.

## Intermediate decision and remaining boundaries

Task 7 accepted the [explicit intermediate contract](../designs/2026-11-15-explicit-intermediate-contract.md), SHA256 `4fe4c73e508c88b8c2d0113077874b27cbd669de3ff0ef0f39124ec9c6558462`, with independent SPEC PASS / QUALITY APPROVED. Selected output reuse and existing bound route checkpoints satisfy the current need. **DESIGN ONLY:** no `IntermediateRef` runtime symbol, intermediate namespace/API extension, serializer registry, second backend or intermediate test suite is implemented or claimed.

A later adoption names a real completed stage/producer/consumer and receives its own reviewed B namespace/API-extension plan. Mutable or incomplete run checkpoints remain under `runs/<run-id>/checkpoints/`; renaming a checkpoint does not make it a complete publication.

Visuals were omitted because retained numerical parity, exact bytes, currentness rejection, nonempty dependency chains, lifecycle states and zero-producer sentinels establish the cache behavior directly. No uncertain new spatial placement or extraction required another image. This delivery does not claim a full-repository suite, live Blender execution, current-scene geometry extraction, user visual approval or cross-scene calibration. Retained artifact evidence is labelled retained, not proof of live currentness.

The implementation and final delivery documents are locally accepted. Local bookmark `codex/parameter-cache-c-accepted` identifies the separate documentation-only handoff commit; its ID is recorded externally rather than embedded here. C remote push, owner/main integration and cleanup remain outside this delivery.
