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
