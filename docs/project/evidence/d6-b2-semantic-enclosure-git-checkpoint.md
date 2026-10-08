# D6 B2 private semantic-enclosure Git checkpoint

Date: 2026-10-08 (Europe/Berlin). This record defines the separately authorized **one local checkpoint commit** on `codex/d6-analysis-domain-layout-handoff`, parent HEAD `ab55da50dfb278b639e2327008ad23a50e86973d`. The supervising chat retains checkpoint acceptance. The actual commit SHA, commands and post-commit Git state belong in the [local receipt](../../../outputs/design/d6_b2_semantic_enclosure_git_checkpoint/run_001/post_commit_receipt.json), outside this commit; no document hashes itself or embeds its own commit SHA.

## Accepted scope and gates

Root's dated [ACCEPT](d6-b2-semantic-enclosure-private-integration.md) applies to final delivery_003 / run_007: explicit private provisional B2 computation, immutable source/physical occupancy, caller-authorized default-closed doors/windows, qualified missing-only host inference and explicit conflict/unfilled refusals. [A's independent review](d6-b2-semantic-enclosure-private-integration-independent-review.md) accepts the final bytes after genuine F01-F05 repairs; the withdrawn overstrict assertion and failed intermediate artifacts remain historical. The [frozen integration plan](../../superpowers/plans/2026-10-08-d6-b2-semantic-enclosure-private-integration.md) and reports are retained verbatim, including STOP markers and uncommitted-at-delivery statements. This new authorization permits the checkpoint; it does not rewrite their earlier authority boundaries.

Pre-checkpoint inspection confirmed the expected branch/HEAD, empty index, no Git process or index lock, and completed read-only B/A/C chats. Six supplied worktree SHA256 values match; all 74 B/C manifest entries match their recorded sizes/hashes. The initial inventory has 803 tracked/nonignored untracked files. Existing dirty/untracked work remains in place. Shared source/fixture imports already exist in HEAD; the inspected production/test diff contains only this private entry and composed regression additions. No caller, config, dependency, export or adapter change is needed.

The only intended committed paths are:

- `features/_semantic_enclosure.py`
- `features/neutral_scene_views.py`
- `test/test_neutral_scene_analysis_regression.py`
- `docs/superpowers/plans/2026-10-08-d6-b2-semantic-enclosure-private-integration.md`
- `docs/project/evidence/d6-b2-semantic-enclosure-private-integration.md`
- `docs/project/evidence/d6-b2-semantic-enclosure-private-integration-independent-review.md`
- `docs/project/evidence/d6-space-field-design-progress.md`
- `docs/project/evidence/d6-b2-semantic-enclosure-git-checkpoint.md`
- `docs/project/evidence/d6-b2-semantic-enclosure-git-checkpoint-manifest.json`

## Identity, checks and ledger ownership

Exact reviewed worktree SHA256 identities (not Git blob IDs):

- `features/_semantic_enclosure.py`: `d0a5e2c2ad01e804719cebf60d0b1beb0c20f06747d763e04383320ae4ae533b`
- `features/neutral_scene_views.py`: `174e75f1097a89ef6838b1a8da01a4cbb5e74a6704ce3f390038abd964b69bf9`
- `test/test_neutral_scene_analysis_regression.py`: `0a8a6f42ff95a84d6975aeccfa564bcd5d5a67a4991ec117265e0c3896035a84`
- `outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_shadow.py`: `cb7c60c215cdb1979ae95285f0adb06ab0fba7cce7e8e1625bc2b66d256f9b72`
- `outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/delivery_003/manifest.json`: `9b871778c2acb908a2a793dc12aa1ac4297cb0e092856208f20d86ee3a33a650`
- `outputs/design/d6_b2_semantic_enclosure_private_integration/integration/delivery_manifest.json`: `40301f9b5598847b5d193e23d8c36b291ba8a8c2cd6b6f4b493474cee40f16bc`

The [scope/fingerprint manifest](d6-b2-semantic-enclosure-git-checkpoint-manifest.json) records bytes, worktree SHA256 and expected Git blob IDs for committed source/docs, plus the separate ledger index identity. Git `core.autocrlf=false`; no applicable attributes were reported. The ledger has a deliberate content difference, not line-ending normalization. Verification must compare the staged/committed blobs with these exact identities before success.

The ledger's preserved pre-phase prefix is **30,449 bytes**, SHA256 `a3cc04789272ed023d448d8f9a69329cba45339c8b8b56e9cd6ff39096288ebc`. HEAD contains its first **25,198 bytes** exactly. The remaining **5,251 bytes** are older uncommitted floor-plan, boundary-height and window-repair history. They are excluded. The staged ledger is constructed as HEAD bytes + the exact 3,526-byte accepted private-integration append + this checkpoint entry. The working file is its original 33,975 bytes + the same checkpoint entry; its original prefix is untouched. The receipt verifies both constructions and the expected remaining ledger modification. Whole-file ledger staging is forbidden.

Checks reused, not rerun: B's final focused command reports **90 passed**; the one configured `pixi run pytest` reports **874 passed / 13 skipped**, exit 0, 965.37 s pytest time / 967.5969052 s process elapsed. Reviewed source/test/harness hashes stayed unchanged. Configured testpaths are `test` and `skills/ifc-bim-conversion-workflow/tests`; the skipped optional IFC-workflow fixture checks remain skipped. This bookkeeping task freshly checks fingerprints, exact scope, JSON, links, staged whitespace, blob identities and preservation; it performs no pytest, IFC, Blender or geometry replay.

## Evidence retention and portability

Each artifact below is **external/local-only**, excluded from this checkpoint. Exact bytes/SHA256 and purpose are in the manifest. Frozen earlier runs and reports remain in their existing locations.

| Evidence | Purpose |
| --- | --- |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/integration/verification_final.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/integration/verification_final.json) | Final coordinator verification and root ACCEPT |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/integration/delivery_manifest.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/integration/delivery_manifest.json) | Frozen C final delivery |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/delivery_003/manifest.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/delivery_003/manifest.json) | Frozen B reviewed source/run delivery |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/integration/full_suite_001/execution.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/integration/full_suite_001/execution.json) | Single configured full-suite command/exit/source identities |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/integration/full_suite_001/pytest.log](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/integration/full_suite_001/pytest.log) | 874 passed / 13 skipped final summary |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/focused_008.log](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/focused_008.log) | 90 focused cases final log |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/focused_008_execution.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/focused_008_execution.json) | Focused command/exit |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/checks.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/checks.json) | 38 sources / 11 carriers / 5 contours / 1 provisional scope |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/semantic_result.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/semantic_result.json) | Complete final private result |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/strict_result.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/strict_result.json) | Separate strict-contact comparison |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/ordinary_view.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/ordinary_view.json) | Ordinary/default compatibility evidence |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/source_scene.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/source_scene.json) | Frozen adapted factual Neutral Scene input |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/request.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/request.json) | Explicit frame, budgets and scenario authority |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/provenance.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/provenance.json) | Source-only harness provenance |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/production_semantic_enclosure.png](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_007/production_semantic_enclosure.png) | Final production visualization |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_shadow.py](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/shadow/run_shadow.py) | Read-only replay harness |
| [outputs/design/d6_semantic_enclosure_window_repair/inputs/run_001/live_snapshot.json](../../../outputs/design/d6_semantic_enclosure_window_repair/inputs/run_001/live_snapshot.json) | Frozen 38-source mesh capture |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/review/final_delivery_001/verification.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/review/final_delivery_001/verification.json) | A final independent delivery verification |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/review/final_recheck_002/recheck.json](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/review/final_recheck_002/recheck.json) | A selected repaired-case evidence |
| [outputs/design/d6_b2_semantic_enclosure_private_integration/integration/d6_progress_before.md](../../../outputs/design/d6_b2_semantic_enclosure_private_integration/integration/d6_progress_before.md) | Exact preserved pre-phase ledger prefix |
| [outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc](../../../outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc) | Source IFC factual input; byte preservation only |

Git retains the reviewed code, tests and checkpoint documentation. The frozen mesh snapshot, adapted source scene, shadow runner, full result JSON, logs and PNG require those local files for full replay/visual inspection. **A hash identifies bytes; it does not preserve them or guarantee recovery after local deletion.** Source IFC, user/disposable Blender files, large snapshots, rendered binaries, temporary outputs and old experiments stay outside the commit. No force-add, copying output trees, LFS, ignore changes, archive framework or migration occurs.

Frozen evidence records 38 sources, 11 scenario closure carriers, five contours and one provisional compound scope. Unknown authored floor datum, disk/live mesh parity, self-intersection/topology certification, local diagonal residuals and shared-wall allocation remain limitations. Acceptance does not certify rooms, activate AnalysisDomain, authorize public API/UI/free-space/routes, establish global tolerance/default policy, verify native IFC/live Blender mesh parity, establish general production readiness or approve merge.

The next separately scoped stage is **AnalysisDomain handoff**. This checkpoint neither designs nor implements that stage. No push, merge, tag, amend, branch/worktree change or cleanup is authorized here.

STOP FOR D6 B2 GIT CHECKPOINT REVIEW
