# Task 1 correction round 1 independent review

**Specification verdict: PASS for Task 1 after this correction. I1: ADDRESSED.**

**Quality verdict: Approved. No new Important or Critical issue in the fix diff.**

## Reviewed candidate and bounded assessment

- Workspace/CWD: `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache` (`free-space-cache`).
- Frozen correction revision: `f807bd6f` (read-only jj inspection: change `slqmkxolsosx`, commit prefix `f807bd6f66db`). Original reviewed candidate: `9c38f93d`; workline base: `d08cd0eb`.
- Read the complete `task-1-fix-1-review-package.diff`, `task-1-fix-1-candidate-hashes.json`, and the appended correction section of `task-1-report.md`. Actual six-file hashes remain authoritative and matched before and after independent verification.
- Product delta is the two-line external-root Mapping guard in `blender_addon/order_analyzer_ui/board.py:160` and one parameterized regression at `test/test_blender_analysis_board.py:193`. Remaining packaged changes preserve the first review in durable evidence; they do not alter product behavior.
- No unrelated code review was reopened. No product edit, VCS mutation, live Blender action or agent spawning occurred. Root remains the version writer.

## I1 resolution and strengths

`board.py:160` now rejects parsed non-object JSON with a clear `ValueError` before passing it to the mapping-only exact reader. Existing restoration handling consequently records unavailable state and hides the affected display, while explicit selection raises before changing its descriptor or presentation. The guard validates the external-data boundary without weakening the exact-ref, identity, backend or datum checks.

The regression covers all four original roots (`[]`, `null`, `"unrelated"`, `17`), asserts unavailable status/message and hidden viewport/render state, proves a second valid board still restores, and checks a subsequent failed explicit selection preserves the previously visible mesh/descriptor. This tests the public restore/select behavior through real temporary sidecars and the established small native seam.

## Independent verification

Environment: existing Pixi environment, Python `3.12.13` (conda-forge), executable `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache/.pixi/envs/default/python.exe`; Windows 11 build 26300. All commands ran in the CWD above. No dependency changes.

Evidence directory: `outputs/design/analysis_board/verification/`.

| Command/check | Exit/result | Evidence |
| --- | --- | --- |
| Compare all six actual SHA256 hashes with the frozen fix manifest before execution | 6/6 match | `task-1-fix-1-independent-hashes-before.json` |
| Pixi Python cwd/version/executable/platform command | 0; expected environment | `task-1-fix-1-independent-environment.log` |
| `pixi run pytest test/test_blender_analysis_board.py test/test_blender_analysis_overlay.py -q` | 0; **39 passed in 0.88 s**, no reported warnings | `task-1-fix-1-independent-pytest.log` |
| `pixi run python outputs/design/analysis_board/verification/task-1-fix-1-independent-sidecar-probe.py` | 0; **all four original malformed-root cases pass**: no exception, unavailable status, viewport/render hidden | `task-1-fix-1-independent-sidecar-probe.log`, corresponding `.json` |
| Compare all six actual SHA256 hashes after suite and independent probe | 6/6 match | `task-1-fix-1-independent-hashes-after.json` |

`task-1-fix-1-independent-commands.json` records cwd, commands and exit codes; `task-1-fix-1-independent-summary.json` records hash counts and probe identity. The independently authored original probe was run as an exact byte copy under the fix-round filename so its first failing JSON/log evidence remains intact. Both original and executed copy have SHA256 `3ebf3816e549ba0495c03690d01faa901204fcc600bc00e81df8b72f358a669c`; probe logic was not changed for the fix.

## Findings and assessment

- Critical: none.
- Important: none remaining in this scoped correction; original I1 is independently verified as addressed.
- Minor: none raised in the correction diff.

Task 1 is approved within its module/API scope, carrying forward the original bounded review with I1 resolved. Runtime/UI/capture integration remains Task 2; native appearance, actual S3 alignment and real Blender save/reopen remain Task 3. This approval does not claim those later gates are complete.

Skipped broad regression and live Blender per the dispatch. Risk: actual native rendering and save persistence remain unverified until Task 3.
