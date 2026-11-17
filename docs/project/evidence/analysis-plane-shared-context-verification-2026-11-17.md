# Analysis-plane shared context verification — 2026-11-17

## Delivered boundary

The [design](../../superpowers/specs/2026-11-17-analysis-plane-shared-context-design.md)
and [plan](../../superpowers/plans/2026-11-17-analysis-plane-shared-context.md)
are implemented in the current owner workspace. Every package evaluation and
processing entry requires a nonempty frozen `PackageAnalysisContext`, either
explicitly supplied or narrowly derived from one complete trusted source plane.
Algorithms may ignore it without projection, grid creation or model extraction.
Multiple planes require package capability and explicit per-call permission.

`AnalysisPlane` remains an immutable coordinate fact; `AnalysisPlaneCatalog`
resolves default/override selection; native settings persist author observations.
The UI freezes request and native binding together. Packages continue composing
their own algorithms, processors and storage with the shared `EvidencePackage`
template. No model manager, inheritance tree, global context, automatic upstream
router or multi-plane numerical fusion was added.

Raw/processed v1 formats, existing result references and numerical queries remain
unchanged. Retained partial-plane scripts provide their declared scenario context
without rewriting source artifacts. Explicit unused context does not relabel raw
evidence. Warm cache paths validate context before lookup.

Full capture authentication, source binding and current support consent remain
mandatory. The adapter projects verified physical dependencies for numerical
reuse, excluding unused camera rows and derived audit identities. Physical facts,
external dependencies and saved IFC SHA remain bound. Without a verified IFC
dependency proof, saved external byte changes conservatively miss.

## Independent evidence

Commands ran in `D:/PROJECTS/understandOtherPackage/order_analyzer` using
`PYTHONPATH=.` and `pixi run python -m pytest`. Results below distinguish
accepted selections from retained failed attempts and skipped spatial acceptance.
JUnit and exact candidate hashes are under
`D:/temp/oa-plane-context-20261117/`.

| Selection | Result | JUnit |
| --- | --- | --- |
| Generic core/output/processing/readback/processed consumer/output-port tests | 396 passed | `core-independent.xml` |
| Final context and field core, including strictness repairs | 51 passed | `review-core.xml` |
| Native settings, UI, runtime and native plane adapter | 308 passed | `review-native.xml` |
| Capture, session, free-space package and live adapter | 300 passed | `cache-independent.xml` |
| Saved distance, retained/live axis handoff and modulation CLI | 4 passed | `scripts-independent.xml` |
| Repaired explicit-context CLI fixture | 1 passed | `scripts-repair-independent.xml` |
| Immutable retained-cache preflight and migration | 16 passed | `migration-independent.xml` |
| Retained modulation original attempt (failed) | 4 passed / 24 setup errors | `modulation-independent.xml` |
| Repaired affected modulation selection, exit 0 | 19 passed / 5 skipped | `modulation-repair-independent.xml` |

These overlapping executions contain **1,049 distinct passing test nodes**
and **5 distinct skipped spatial nodes**, recorded in `independent-union.json`;
this is not a single 1,049-node execution. Only successful cases from the
original failed modulation attempt contribute to the passing union.
The latest shared-core run covers the final stricter mapping validation.

Implementer supplemental runs cover a 619-pass/2-skip union across 15 files,
including retained full-scope hierarchy and processed IFC evidence. The retained
processed module was 65 passed / 2 skipped; the skips require absent
`outputs/design/group_distance_ifc/run_v3_finite_band_result/coverage_report.json`.
Logs: `D:/temp/package-context-processed-ifc.txt` and
`D:/temp/package-context-verified-union-nodes.txt`.

Failed attempts remain preserved: the first lifecycle-runner selection was
56 passed / 1 failed because a contract-only CLI fixture omitted required context.
Its test seam now supplies explicit context; independent repaired-node verification
passed. The original failure remains at `D:/temp/package-context-runners.txt`,
and the implementer's final 33-pass repair at
`D:/temp/package-context-final-repair.xml`.

The additional full retained modulation module initially reported 4 passed /
24 setup errors (`modulation-independent.xml`). Its four combined numerical
checks passed; the semantic fixture and sibling processor still omitted context
for historical partial-plane sources. Those two test calls were migrated to
explicit context without changing production code or retained evidence. The
affected selection completed with **19 passed / 5 skipped**, exit **0**, in
1,748.63 seconds. Its 19 successful nodes and the unchanged original four
cover 23 distinct passing modulation nodes. The original failed attempt stays
failed. All five skips are dependency-deletion/mixed-migration cases gated by
`stored_distance_free_space`, because the accepted finite-band coverage report
is absent (`execute the accepted free-space distance run before spatial
acceptance`). They are not spatial passes. A supplemental fixture smoke was
1 passed in 529.98 seconds; its log/JUnit are
`D:/temp/package-context-modulation-fixture-repair.{txt,xml}`.

Final static review also found the skipped mixed-migration test's legacy
`process_unconfigured` forwarding seam needed the new required keyword. The
test-only signature and forwarding call were migrated; a scratch check of the
actual nested wrapper verifies missing-keyword rejection and same-object context
forwarding. Production code and all 23 successful modulation test bodies remain
unchanged. The implementer check log is
`D:/temp/package-context-modulation-wrapper-delta.txt`. An independent repeat
also exited zero. Stripping the single wrapper from both the 19-pass candidate
and final file yields SHA256
`23009b68d81411ebc4e50761b9461f071ce12512d91b7915e0f2ede507741079`;
the final test-file SHA256 is
`f1aae326d127947724a9f62193201716e2c91a28b87ab204f9f91d0b471bacf7`.
This lightweight check does not substitute for the five skipped spatial cases.

## Compatibility review

Independent native/UI, cache/session and whole-scope reviews all returned
**SPEC PASS / QUALITY APPROVED**, with no blocking finding. Final review included
the shared OOP boundaries, public callers, scenario-context scripts and the
test-only CLI fixture repair. The final wrapper delta independently returned
**SPEC PASS / QUALITY APPROVED**, explicitly retaining the five skipped spatial
lifecycle cases as unaccepted.

The exact compatibility profile was refreshed only after review. All 32
`current_content_implementations` hashes match actual candidate bytes; two new
current-only guards cover context and native settings. Both historical
`original_*` mappings, numerical package versions and executor remain unchanged.
The old complete-fact key still uses `numeric_projection=False`; CacheStore
admission was not relaxed. The independent 16-pass migration run verifies the
refreshed candidate. Initial migration failures before hash refresh remain
diagnostic history rather than accepted results.

## Real native lifecycle check

A different agent executed the actual approved IFC copy in a fresh background
process using only
`D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe` (5.2.0 LTS).
Exit code was **0**. Receipt:
`D:/temp/oa-plane-native-20261117/native-receipt-attempt2.json`, SHA256
`63f900c345a1cba2bbccd32188ab240f6bc1f1839ee8c02bfd045ec7dd071a9e`.

The check created two independent managed drawings, rejected ambiguous ensure,
updated only P1 and advanced its revision to two, serialized/reopened IFC in
memory and restored exact P2. Only the actual IfcProject metadata was linked;
linked physical mesh count stayed zero. All 354 original IfcElement declarations
retained digest
`f4628639f8c76eca3962c25b559a13469511a8805be9f690b045156866bc1038`.
Original and scratch IFC stayed byte-identical at SHA256
`1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`
(408,618,044 bytes).

The first attempt failed before native authoring because factory startup omitted
the same portable installation's dependency path. Only the scratch harness was
adjusted; both attempts, launch arguments, exact final exit and logs remain in
`D:/temp/oa-plane-native-20261117/`. No project source repair was required.

## Workspace and limits

Workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer`; owner change
`uplswssp`, implementation baseline `a636b71f`, parent `575e0b9b`.
Baseline SHA256 checks cover 310 paths: 266 remained unchanged, 44 are explicit
task edits and none are missing. New context/settings/tests/spec/plan and the
updated compatibility profile are recorded separately in `candidate-hashes.json`.
Existing CRLF bytes were preserved. Retained fixture preflight passed; no model,
fixture or saved evidence bytes were rewritten by this implementation.

The owner retains history-writing authority. One accidental `jj status` omitted
`--ignore-working-copy` and automatically snapshotted the same change as
`f457f56f`; that event is retained in the progress ledger. No task delivery
commit, describe/new/bookmark, push, merge, reset or cleanup is claimed.

Unchecked: live UI interaction, `.blend` save/reopen, physical geometry
recomputation, the five retained modulation lifecycle cases and the two
processed IFC spatial cases gated by the missing coverage report. Saved IFC SHA
changes can still invalidate numerical cache despite camera-only intent; no
unsafe source equivalence is inferred.
