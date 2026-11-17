# Task 1 independent review

**Specification verdict: FAIL — one Important external-sidecar restoration defect.**

**Quality verdict: Needs fixes — the invalid external-root path escapes error handling and leaves stale presentation visible.**

## Candidate and scope

- Workspace: `free-space-cache`, `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache`.
- Base: `d08cd0eb`; frozen revision supplied by root: `9c38f93d` (change `slqmkxolsosx`). Read-only installed-command inspection confirmed that revision exists. The supplied six-file SHA256 manifest, checked against actual bytes, is authoritative for this review.
- Reviewed brief, implementer report, the full packaged diff, and the six-file candidate manifest. Product review is limited to Task 1 board/style/native API work. Root remains the sole version writer; no product edits or VCS mutations were made.
- Applied Superpowers task-reviewer spec/quality criteria and project `skills/verified-agent-workflow/SKILL.md`. The project requirement to independently rerun acceptance overrides the generic template's instruction to rely on implementer test results.
- The packaged diff includes design/plan/ledger/architecture groundwork outside the six product/test files. Their Task 2/3 integration and acceptance items are deferred, not treated as Task 1 omissions. The initial architecture text still labels implementation as pending; Task 2 owns its synchronization per the bounded dispatch.

## Strengths

- `blender_addon/order_analyzer_ui/board.py:157` saves and uses independent identity/backend expectations alongside an exact external ResultRef, and compares the complete project/domain/datum binding after historical opening. The real-file replacement checks at `test/test_blender_analysis_board.py:128` and `:320` exercise digest and independently stored expectations.
- `board.py:178` reuses exact-ref sources only at a matching native unit scale; `board.py:251` applies object material overrides and a slab-relative Z offset. `test/test_blender_analysis_board.py:193` checks nonzero XY, negative slab datum, shared geometry and metre conversion; its scale restoration test exercises `1 -> 0.001 -> 1` reuse.
- `board.py:214` and `:231` wire actual shader inputs with alpha and sRGB conversion. `test/test_blender_analysis_board.py:230` verifies shader socket values and separate object style over shared geometry. Actual rendering remains a Task 3 gate.
- `blender_addon/order_analyzer_ui/palettes.py:33` keeps the seven legend categories explicit, and its finite mapper covers constant ranges, overflow and subnormal widths (`test/test_blender_analysis_board.py:297`). Runtime imports use existing stdlib/lightweight seams; sampled palette attribution/license is present.
- The required focused suite passes independently, and all six candidate hashes match before and after verification.

## Findings

### Critical

None identified in this task scope.

### Important — I1: malformed sidecar roots leave historical displays visible

**Location:** `blender_addon/order_analyzer_ui/board.py:159`–`:160`, with the incomplete recovery boundary at `board.py:385`.

`_open_entry` parses the external JSON and passes the resulting value straight to `wire.open_analysis_result([document], ...)`. That reader assumes each entry is a mapping and calls `.get`. Syntactically valid JSON roots such as `[]`, `null`, a string, or an integer therefore raise `AttributeError`. `restore_boards` catches only `OSError`, `ValueError`, and `TypeError`, so restoration aborts without hiding the old display or recording an unavailable state. This directly violates the binding requirement that missing or mismatched sidecars be reported with their display hidden. It also prevents later boards in the loop from restoring.

**Independent reproduction:** attach a valid saved result using the existing small fake-bpy seam, overwrite only its external file with each of `[]`, `null`, `"unrelated"`, and `17`, then call `restore_boards`. Every case raises `AttributeError`, leaves descriptor `status="historical"`, and leaves both `display.hide_viewport` and `display.hide_render` false. The probe's contract assertion exits 1. Original result and product files are unchanged; the probe uses disposable temporary sidecars.

**Correction:** reject a non-mapping root with a clear `ValueError` at the board's external-file boundary before exact opening (or validate the parsed document through the existing validator). Add a regression that restores malformed external roots and asserts no escaping exception, explicit unavailable status/message, hidden display, and continued restoration of another valid board. Keep failed explicit selection's previous display intact.

**Evidence:** `outputs/design/analysis_board/verification/task-1-independent-sidecar-probe.py`, corresponding `.json` and `.log`, and `task-1-independent-sidecar-command.json`.

### Minor

None raised. Review was not broadened after the concrete blocker was established.

## Independent commands and evidence

All commands ran from `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache` using PowerShell and the existing Pixi environment. Python is `3.12.13`, conda-forge, executable `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache/.pixi/envs/default/python.exe`; OS reports Windows 11 build 26300. No dependency installation occurred.

| Command/check | Exit/result | Evidence under `outputs/design/analysis_board/verification/` |
| --- | --- | --- |
| SHA256 comparison of the six supplied candidate files before testing | 6/6 match | `task-1-independent-hashes-before.json` |
| `pixi run python -c "import os,platform,sys; ..."` for cwd/version/executable/platform | 0; Python 3.12.13, expected workspace | `task-1-independent-environment.log` |
| `pixi run pytest test/test_blender_analysis_board.py test/test_blender_analysis_overlay.py -q` | 0; **35 passed in 0.76 s**, no reported warnings | `task-1-independent-pytest.log`, `task-1-independent-test-command.json` |
| `pixi run python outputs/design/analysis_board/verification/task-1-independent-sidecar-probe.py` | 1; contract assertion fails for all four malformed external roots | `task-1-independent-sidecar-probe.log`, `task-1-independent-sidecar-probe.json`, `task-1-independent-sidecar-command.json` |
| SHA256 comparison after suite and independent probe | 6/6 match, same frozen bytes | `task-1-independent-hashes-after.json` |
| `jj --help`; `jj --ignore-working-copy log -r 9c38f93d --no-graph ...` | 0; installed command checked, frozen revision confirmed | Read-only tool transcript; no snapshot or history write |

Focused inspection outside the packaged diff was limited to named risks: wire parsing/opening behavior for malformed external roots; `ValidatedAnalysisResult` access semantics to rule out repeated deep copies in the fragment loop; the slab producer/validator's receipt hash recipe; and existing native mesh callers to assess the changed SI handoff. No broader codebase crawl or additional suite was run. The first 290 lines of board.py had been read during initial preparation before loading the task-reviewer template; the packaged diff then supplied the complete review context, and no separate repeat read of that file was needed.

## Scope limitations and assessment

**Task quality: Needs fixes.** The architecture and normal-path tests are focused and coherent, but I1 is a directly reproduced violation at the external-data trust boundary. The unchanged focused suite does not cover malformed JSON roots.

Cannot verify from this task diff: runtime publication/UI/capture invalidation integration (Task 2), actual native appearance, actual S3 alignment and material persistence through real Blender save/reopen (Task 3). No live Blender was launched, and no currentness, Domain consent, native appearance or user visual acceptance is claimed.

Skipped broad regression and live Blender as outside this dispatch. Risk: this frozen candidate can retain a visible historical board after a malformed sidecar restore until I1 is fixed and independently reverified.
