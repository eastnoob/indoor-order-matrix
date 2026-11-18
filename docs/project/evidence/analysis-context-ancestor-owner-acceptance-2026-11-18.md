# AnalysisContext ancestor: owner acceptance

Date: 2026-11-18. Scope: independently review, repair and locally integrate the
delegated core increment. Native UI work, remote push and cleanup are excluded.

## Decision and integration

SPEC PASS / QUALITY PASS after repairing one independently reproduced P1:
the ancestor increment changed reviewed implementation bytes without updating
the strict legacy compatibility manifest. The result was a safe but unintended
miss for historical free-space/Blender caches, not stale-result acceptance.

Only five reviewed current content hashes and the backend `field_core` hash
were updated. Original hashes, numerical versions and the strict validator are
unchanged. An unchanged `plane_settings.py` was restored to its pinned LF bytes.
The bridge remains original-to-reviewed-current, not arbitrary-version reuse.
Unknown implementation/content and numerical versions still miss.

Owner root `d6ab0f9a9aca3746ed3125aa2b43f0078b1a5472` was a direct ancestor of
delivered `bdf2d5f12ec1cd18ce1dc42023b47c4ebdf26200`. The reviewed repair is
`bf84d25c101e46e1b249fba2d8525fb9452f4abf`. The default workspace advanced to
an empty child of that repair; no cherry-pick, squash or content merge was needed.
Recovery bookmark: `codex/analysis-context-ancestor-owner-before`.
Acceptance bookmark: `codex/analysis-context-ancestor-accepted`.

The [design](../../superpowers/specs/2026-11-18-analysis-context-ancestor-design.md),
[maintained implementation checklist](../../superpowers/plans/2026-11-18-analysis-context-ancestor-implementation.md)
and [structure guide](evidence-package-structure.md) remain the semantic authority.
Earlier isolated-delivery claims and failures remain in the
[verification history](analysis-context-ancestor-verification-2026-11-18.md).

## Maintained owner checklist

Update this list when gate evidence changes; an agent's status alone is not proof.

- [x] Read the independent chat's actual human handoff, design and plan.
- [x] Verify direct ancestry and preserve the owner's 58 existing changed paths.
- [x] Back up 1,201 tracked physical files, raw hashes and the complete original patch outside the repository; find zero unignored extra files.
- [x] Independently verify the previous 830-pass/two-skip reports, 13 changed Python hashes and 11 retained fixtures.
- [x] Run a fresh 868-test selected baseline, including pure-Python UI/settings tests.
- [x] Reproduce the legacy-cache P1, delegate its minimal repair, and independently review its exact scope.
- [x] Verify the red/green regression and real historical authenticated-free-space/Blender-wire restart tests with forbidden producers.
- [x] Run the final 1,028-node owner selection: all pass, no skips/errors/failures.
- [x] Advance the default workspace locally to the reviewed repaired candidate.
- [x] Verify all 32 current content pins and 14 changed Python files against the tested source; preserve 1,182 untouched baseline files byte-for-byte, including 42 untouched prior-dirty paths.
- [x] Verify the root runtime's strict legacy profile returns `pre-parameter-sidecar-storage/1` and run the separate 215-test root-path smoke.
- [x] Synchronize the package guide, architecture map, memory and this acceptance record; retain recovery history and the implementation workspace.

## Reproduction and evidence

Evidence root: `D:/temp/oa-ancestor-owner-20261118T101020`.
`owner-before.json`, `owner-before.patch` and `owner-before/` preserve the
1,201 original tracked files (123,972,801 bytes). Ignored runtime files were not
inventoried or cleaned. `owner-post-integration-preservation.json` records the
26-path increment and unchanged-file checks.

The owner ran `pixi run python
D:/temp/oa-ancestor-cache-repair-20261118/run_repair_tests.py` from the
implementation workspace, selecting the original 14 related files plus
Blender-session, migration-preflight and the two required migration restart
nodes. Exact invocation is retained in chat/tool history; the runner uses a
main guard, package-shaped source paths, OCTA and `--import-mode=importlib`.
`owner-final-focused.xml`: 1,028 passed in 46.44 seconds;
SHA256 `2576d15ad4e036e8b8b7b313bbd57cf88721756abf99c75dac3c6f58f499fee3`.

From the actual root, `pixi run python
D:/temp/oa-ancestor-owner-20261118T101020/run_root_smoke.py` explicitly sets the
root, its parent and OCTA import paths. It selects `test_package_analysis_context`,
`test_analysis_requests` and `test_native_plane_settings`.
`owner-root-smoke.xml`: 215 passed in 8.13 seconds;
SHA256 `1a0f53bf60947ccdfda3c37c151e3d010c0acf4f4b1d61480ca6799bc4c8ca3e`.
`owner-root-runtime.json` binds the actual root source and the successful real
profile probe to Shapely 2.1.2, Trimesh 5.1.0 and NumPy 2.4.3.

The 868, 1,028 and 215 selections overlap and are not summed. The earlier plain
root pytest invocation failed collection because `features` was absent from its
import path; `owner-root-cli-import-failure.xml/log` retain that failure. No
source change was needed for the corrected explicit-path invocation.

## Limits

This is selected core/integration acceptance, not whole-repository green status.
Earlier two native-publication skips remain skips. The attempted full run's B3
fixture was absent from its acceptance copy; the interrupted root run remains
inconclusive. No new native Blender/UI, `.blend` restart or physical IFC
recomputation was performed. Physical SHA checks must be repeated after future
checkouts because the strict manifest intentionally binds exact file bytes.
