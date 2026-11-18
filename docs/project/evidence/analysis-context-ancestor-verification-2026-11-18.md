# AnalysisContext ancestor verification — 2026-11-18

Core implementation and selected feature acceptance are complete in isolated jj
workspace `analysis-context-ancestor-20261118`. They are not integrated into the
default workspace. Whole-repository, UI, and native lifecycle acceptance are not
claimed. No merge, remote push, workspace deletion, or geometry regeneration was
performed.

## Verified contract

- Scene `AnalysisContext` owns exactly one required `analysis_plane`, its default.
- Each package admission resolves a frozen, nonempty `PackageAnalysisContext`.
- Omission inherits the scene default; explicit `package_planes` replaces it
  completely, without appending the ancestor plane.
- Multiple planes require package capability and explicit caller permission.
- Empty, duplicate, malformed, conflicting, and unauthorized selections fail
  before producer, processor, storage, or cache work.
- Packages may ignore the context without projection, grid/model extraction,
  changed output bytes, or unrelated numerical cache invalidation.
- Plane-dependent packages own plane identity/revision dependencies before cache
  lookup. The generic cache layer does not infer plane use.
- Free-space, group-axis, group-distance, port, and lifecycle callers forward
  frozen selections. Unique complete source-query inference remains a narrow
  migration path; it never invents a missing default plane.
- `EvidencePackage` composes callbacks and receives injected context; it does not
  inherit from `AnalysisContext` or own global mutable scene state.

## Final selected acceptance: 830 passed, 2 skipped

The hyphenated implementation directory does not satisfy tests that import the
repository as the `order_analyzer` Python package. Final acceptance used a
package-shaped jj checkout at the same implementation checkpoint:

```text
Implementation: D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/analysis-context-ancestor-20261118
Acceptance:     D:/temp/oa-ancestor-acceptance-20261118/order_analyzer
Acceptance workspace: ancestor-package-acceptance-20261118
Tested checkpoint: 9483866193f206019d9ec53de7c295a74e22dbe9
Acceptance working copy: 20abe4083a95 (empty child of that checkpoint)
```

All 13 task-changed Python files, including new tests, match candidate and
acceptance byte-for-byte. Import-origin checks for both namespaces resolve
project implementation to acceptance, not the default root. The follow-up is
documentation/evidence only. The physical checkouts use CRLF; checkpoint blobs
use LF. Their contents also match after that line-ending conversion alone.

| JUnit report | Selected scope | Passed | Skipped | Errors/failures |
|---|---|---:|---:|---:|
| `context-scene-free-space.xml` | package context, scene contract, free-space | 197 | 0 | 0 |
| `core-callers-cache.xml` | package output/processing, port cache, axis/distance, lifecycle/runners | 385 | 0 | 0 |
| `requests-processed-readback.xml` | requests, processed IFC, readback | 248 | 2 | 0 |
| Combined distinct nodes | Three disjoint selected runs, not one full-suite run | **830** | **2** | **0** |

All three processes exited 0. JUnit identities were independently parsed: 832
distinct nodes, no duplicates. The first run includes the formerly deselected
dual-namespace subprocess smoke test. The independent Superpowers reviewer ran
the 385-test subset.

Two nodes in `test_group_distance_processed_ifc.py` were skipped:

- `test_path_only_matches_combined_on_retained_geometry`
- `test_real_euclidean_excludes_route_only_inputs`

Both report `accepted native free-space publication is not installed`; neither
is counted as passing. Selected artifact replay is not fresh native extraction.

Reports, execution logs, code/fixture manifests and root preservation evidence
are under `D:/temp/oa-ancestor-acceptance-20261118/`. The repository retains
[the acceptance summary](analysis-context-ancestor-acceptance-summary-2026-11-18.json),
including all three report SHA256 values, skip reasons, 13 source hashes, and
11 retained fixture copies. Every fixture source and destination length/hash was
rechecked; none was recalculated. OCTA comes from the root's vendored directory.

### Reproduction setup and file sets

Run `pixi run python -` from the implementation workspace, not the environment's
Python executable directly: Windows NumPy requires Pixi's activated DLL paths.
Within Python, use this common reproduction setup before invoking
`pytest.main(...)`. This supplies root-vendored OCTA where needed; it is not a
claim that every historical run used this exact OCTA path. The independent core
run used the acceptance OCTA path, which was absent but not needed by its scope.

```python
import os
import sys
from pathlib import Path

root = Path(r'D:/temp/oa-ancestor-acceptance-20261118/order_analyzer')
os.chdir(root)
paths = [str(root.parent), str(root),
         r'D:/PROJECTS/understandOtherPackage/order_analyzer/OCTA_toolbox-master']
sys.path[:0] = paths
os.environ['PYTHONPATH'] = os.pathsep.join(paths)
import pytest
```

Each run passes its file set below plus `-q -p no:cacheprovider` and a separate
`--junitxml=D:/temp/oa-ancestor-acceptance-20261118/<report>` argument:

For `core-callers-cache.xml`, also pass `--import-mode=importlib`, as used by
the independent 385-test run. The other two selected runs used default import
mode with the explicit paths above.

```text
context-scene-free-space.xml:
  test/test_package_analysis_context.py
  test/test_scene_contract.py
  test/test_free_space_evidence_package.py
core-callers-cache.xml:
  test/test_evidence_package_output.py
  test/test_evidence_package_processing.py
  test/test_output_port_cache.py
  test/test_group_axis_potential_field.py
  test/test_group_distance_evidence_package.py
  test/test_group_distance_output_ports.py
  test/test_evidence_package_lifecycle.py
  test/test_evidence_package_lifecycle_runners.py
requests-processed-readback.xml:
  test/test_analysis_requests.py
  test/test_group_distance_processed_ifc.py
  test/test_evidence_package_readback.py
```

## Full-repository attempts and historical failures

Earlier nested-workspace runs produced 48 collection errors, a namespace smoke
failure and missing retained axis artifacts. Those runs remain failed historical
evidence. Package-shaped runs above resolve these feature path/fixture issues
without source edits. Earlier subsets are not added to the distinct final count.

The package-shaped whole-suite attempt with OCTA, `test/ -q --maxfail=1`, stopped
at **317 passed, 1 setup error**. It lacked:

```text
outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/artifact_manifest.json
test/test_b3_occupancy_only_handoff.py::test_proxy_sections_are_active_occupancy_only_without_original_double_count
```

Report: `full-suite-first-failure-with-octa.xml`. No later whole-suite result is
claimed. A separate default-root run terminated at exit `1073807364` around
65%, without a final report and with two unidentified failure markers. That run
is inconclusive, does not test this candidate, and cannot establish a passing
baseline or classify candidate failures.

## Static and review gates

- Direct-call audit: `rg -n "\.evaluate\(|\.process_output\(" features adapters
  blender_addon --glob "*.py"` returned 21 matches. Package calls forward resolved
  context; other field/affordance/geometry evaluators use different APIs. Script
  callers were migrated and reviewed with runner/readback coverage.
- Compile check passed: `pixi run python -m compileall -q features adapters
  scripts/design/group_level test/test_package_analysis_context.py`.
- Tasks 0–4 received self-review and independent Grill-Me review. Final
  implementation Grill-Me: PASS. Superpowers: SPEC PASS / QUALITY PASS.
- Documentation/evidence follow-up: independent Grill-Me PASS; Superpowers
  SPEC PASS / QUALITY PASS after repair and scoped rereview of the reproduction
  flag/setup precision. No implementation changes were needed.

## jj checkpoints and non-destructive recovery

Installed jj verified: `0.46.0-7d382314f9420b4b8d932245b49c99492c812b9f`.
The existing linear checkpoints are preserved:

| Revision | Checkpoint |
|---|---|
| `d6ab0f9a9aca3746ed3125aa2b43f0078b1a5472` | default-root starting snapshot; unrelated dirty work retained |
| `c3065a40e1c7b0b7b74f01751d24b8da9ae82ff4` | context-root |
| `5987140969889fd67148609649fb1ea3024ef0a3` | package-contract |
| `79fd386535b96e7b8714ccc5c83c58b1fa2faa0b` | caller-migration |
| `56c120e4de1653ac8bd686d2118e843affe96e8d` | dependency-and-tests |
| `9483866193f206019d9ec53de7c295a74e22dbe9` | documentation-and-verification; tested code baseline |

The follow-up is named `acceptance-evidence: record package-shaped verification
and rollback limits`, followed by an empty child. Its final hash is reported
separately, since a commit cannot include its own hash. No existing checkpoint
is rewritten.

To inspect/recover the tested candidate without rewriting another workspace:

```powershell
jj --ignore-working-copy log -r 'ancestors(@, 8)' --no-graph
jj workspace add --name ancestor-recovery-check -r 9483866193f206019d9ec53de7c295a74e22dbe9 D:/temp/oa-ancestor-recovery-check
```

Choose an unused destination/name. Substitute another checkpoint to recover that
stage. This creates an empty child of the chosen revision. Do not reset,
abandon, globally undo, or rewrite the default workspace.

### Default-root preservation and limits

Default root remains `d6ab0f9a9aca3746ed3125aa2b43f0078b1a5472`.
Saved preflight patch SHA256:
`a6d515cd4984ddd29343baf2e26bbb37f5e327ea3d4f749dc03b71b1700dfc5d`
(424,986 bytes, 6,067 CRLFs). Direct current jj diff SHA256:
`94e805c371c6064678dbfa0eb17c0bca76f21ca43031f93c7e953d32a4edc2db`
(418,919 bytes, LF). They match exactly after CRLF-to-LF conversion only;
`working-copy.eol-conversion = input-output` explains the representation change.

All 58 recorded dirty paths and their normalized physical content remain
(11 files also match raw snapshot bytes). The 1,201 recorded snapshot paths match
the current inventory and physically exist. Independent preservation review and
root recheck agree. No original per-file raw-byte hash manifest or ignored/
untracked inventory was recorded, so those broader preservation claims are not
proven. This limits the original plan's more ambitious inventory intention.

## Remaining acceptance boundaries

No UI, native multi-plane management, settings persistence, `.blend` save/reopen,
fresh IFC extraction, or large model recomputation was performed. Whole-repository
green status remains unverified due to the B3 fixture error; two selected native
publication tests were skipped. This is isolated core delivery, unmerged/unpushed.

## Bounded legacy compatibility repair for owner integration — 2026-11-18

This is a later repair of delivered candidate `bdf2d5f12ec1cd18ce1dc42023b47c4ebdf26200`,
not a replacement for the preceding 830-pass/two-skip scope or failed/inconclusive
historical runs. No full-suite, fresh Blender/IFC, UI, or mainline acceptance is
claimed by this addendum. Owner alone owns version writes and integration.

### Reproduction and exact repair boundary

Using actual files and `_backend_versions()` in the implementation workspace,
Pixi reports Shapely `2.1.2`, Trimesh `5.1.0`, NumPy `2.4.3`, and executor
`planar-analysis-request/2`, exactly the profile's numerical stack. Before repair,
`legacy_backend_compatibility(profile["original_backend_versions"])` returned
`None`. Five current content pins and backend `field_core` were stale after the
ancestor implementation. An additional native helper mismatch was only checkout
line endings.

`blender_addon/order_analyzer_ui/plane_settings.py` was verified against both
physical default-root bytes and `jj --ignore-working-copy file show -r d6ab0f9a`
before restoration. Both equal the existing pinned LF SHA256
`e92c4e1560b7354d7887c3cf044f68c29b94568c22c8eee8a0ab235778a44d3b`.
The implementation helper was restored to those bytes; the CRLF form
`cc822caab439c27894f032f39424af46e2994f8c59ef29a20ce55119c5d5e4cc` was not approved
as a new implementation.

Only these reviewed current content pins changed:

| Physical source | Reviewed candidate SHA256 | Compatibility review |
|---|---|---|
| `adapters/free_space_evidence_package.py` | `6cf04696af7e9a6785f352c20d8c4a5e78cc1ba5bfc18dc8b3741a45dee8d8e4` | Selection admission/forwarding; original request, keys, authentication and codecs unchanged. |
| `features/field_core.py` | `0c7bd3a668bd2b1a1059acda6f1861819e20b3ee4fd4a4c6d6b0406c9899cce2` | Boundary resolution only; original numerical/publication/processing identities unchanged. Also updated in current backend implementation pins. |
| `features/group_axis_potential_field.py` | `38264c41766c3d09c64769eb7642a44a124339a0b0c8bc0af61adbdd5cd11cf7` | Runner forwards selection/permission; original contracts, dependencies and potential calculations unchanged. |
| `features/group_distance_evidence_package.py` | `1e94d867d1d86bbc5157c4254cd59e1f4531feba35488bab16ebcbf60e979df9` | Evaluation/run wrappers forward selection/permission; original distances, repair adaptation and contracts unchanged. |
| `features/package_analysis_context.py` | `c54e75ebc324750f34f71d5935927b34df1d1136bdc659a44c49de5ee545cce6` | Ancestor/default/override admission extension; old frozen-context/query inference and multi-plane gates retained; no numerical calculation. |

Static comparison against d6 found nine changed wrapper/resolver functions and
no module assignment/version constant changes in these five files. This supports
reuse of original numerical artifacts; the ancestor admission API has deliberately
changed and has its separate context tests.

Both `original_backend_versions` and `original_content_implementations` remain
unchanged. Current numerical/executor versions, schema/profile IDs and map
membership remain unchanged. `features/analysis_requests.py` and its strict
validator were not modified: saved/original equality, actual/current equality,
all real content hashes, and version checks still apply. No wildcard, bypass,
automatic trust, intermediate-cache bridge or migration framework was added.
The runtime consumers remain the central validator, Blender historical-key
reconstruction and free-space adoption/readback.

### Fresh tests, source identity and reproduction

The five new request-test nodes use actual `_backend_versions()` and real source
bytes. The content-only negative alters only the read of
`package_analysis_context.py`, leaving all backend and other content reads real.
Unknown caller-supplied implementation/numerical versions also return `None`.

| Report | Observed result | SHA256 |
|---|---|---|
| `red-profile.xml` | 2 expected failures, 3 passes before manifest repair | `c68fda4511b5fb8a2e943887f4de2b72938a580133a19565f68bb18d0f73012d` |
| `green-profile.xml` | 5 passes after manifest repair | `b613d026218829173b426cf5089b9808ce6f0de768a1650054622a83e604b715` |
| `focused-repair.xml` | 417 passes, zero failures/errors/skips | `ade6d8bf973028e7632e0421c9adaa917ca8d237e71e9ec241cd96405fedb223` |

The red assertions failed specifically at stale real `field_core` pins and
`None` versus the expected profile ID, not import/setup errors. Two preliminary
nested-workspace collection probes failed at relative imports, including one
`--import-mode=importlib --rootdir=..` attempt; those are environment diagnostics,
not test executions or candidate regressions.

Original acceptance remains frozen. The owner-authorized new package-shaped
copy and reports are under `D:/temp/oa-ancestor-cache-repair-20261118/`, with source
at `order_analyzer/`. Copy setup omitted `.jj`, `.pixi`, `__pycache__`, and
`.pytest_cache`. Before tests, the added test and restored helper were copied
from the candidate; after repair, only the repaired profile also needed copying.
All 215 Python files under candidate `features`, `adapters`, `blender_addon`, and
`test`, plus the profile, were checked byte-for-byte against the test copy after
the run. Test source therefore is the repaired candidate, not old default-root
or frozen acceptance code.

The temporary `run_repair_tests.py` starts via `pixi run python` from the
implementation workspace, changes to the new package directory, sets both
`sys.path` and `PYTHONPATH` to its parent, itself, and root-vendored OCTA, then
calls `pytest.main()` with `--import-mode=importlib -q -p no:cacheprovider`.
It uses a main guard for Windows spawned processes. Exact focused command:

```powershell
pixi run python D:/temp/oa-ancestor-cache-repair-20261118/run_repair_tests.py `
  test/test_analysis_requests.py `
  test/test_package_analysis_context.py `
  test/test_free_space_evidence_package.py `
  test/test_blender_analysis_session.py `
  test/test_cache_migration_preflight.py `
  'test/test_cache_migration.py::test_migrated_legacy_runner_reuse_survives_process_restart[auth_free_space]' `
  'test/test_cache_migration.py::test_migrated_legacy_runner_reuse_survives_process_restart[blender_wire]' `
  --junitxml=D:/temp/oa-ancestor-cache-repair-20261118/focused-repair.xml
```

For red/green reproduction the test selection was
`test/test_analysis_requests.py -k legacy_profile`, with the corresponding
`--junitxml` report above. Focused counts by file are 166 requests, 45 context,
51 free-space, 151 Blender-session, two migration preflight and two restart
nodes. The focused process exited 0 in 29.04 seconds. The five green-profile
nodes are included in the 417, not additional distinct acceptance nodes.

Both requested historical families passed real retained-fixture import and P/Q/R
process restarts with executor sentinels, unchanged historical payload hashes/
origin refs, index rebuilding, and unknown numerical/implementation rejection.
This restores only the original-to-reviewed-candidate bridge; it does not promise
zero recomputation for arbitrary intermediate d6 caches or other numerical stacks.

`repair-verification.json` in that temporary evidence directory records all 32
current physical content hashes, the 11 backend hashes, numerical versions,
report hashes/counts and source-equality count. Fresh runtime checks in candidate
and test copy return `pre-parameter-sidecar-storage/1`; every content and backend
pin matches. The compatibility manifest's old bytes are retained separately as
`profile-before.json` for independent delta checking.

### Review, documentation and integration boundary

Independent bounded Grill-Me review: PASS. Independent Superpowers review:
SPEC PASS / QUALITY PASS. Both independently checked the six-value manifest
delta, originals/version preservation, all 32 content/11 backend pins, unchanged
strict validator, meaningful negatives and requested structure section. Report
parsing is explicitly review evidence, not a second execution of the 417 tests.

Only the structure guide's "Required analysis-plane call context" section was
corrected: `AnalysisContext` is the one-default-plane ancestor, explicit
`package_planes` replaces that default, `PackageAnalysisContext` is the frozen
per-call snapshot, and native settings/catalog remain adapter helpers. Dual
multi-plane permission and package-owned true dependencies are retained.

No jj history write occurred during this repair. Read-only inspection still shows
candidate child `a8c2f3fe7080b4805d98a649e9c636a44f99e782` over delivered `bdf2d5f1`
and default root `d6ab0f9a9aca3746ed3125aa2b43f0078b1a5472`. Physical repairs remain
unsnapshotted for owner review. Neither the root nor original acceptance checkout
was modified. Owner must recheck actual physical SHA256 values after checkout and
integration, particularly the mixed existing CRLF/LF boundaries; unknown bytes
must continue to miss. No mainline merge or remote push was performed here.
