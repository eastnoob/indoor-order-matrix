# Analysis board delivery ledger — 2026-11-04

## Workline

- Workspace: free-space-cache, `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache`.
- Base: d08cd0eb0b0d; initial empty change slqmkxol / 8e4cd236.
- Scope: approved persistent ground board, hidden results, palettes/opacity, strict historical external references and existing addon UI integration.
- Version writer: root only. Workers edit bounded files without VCS mutations.
- Remote checkpoint: `codex/free-space-cache@origin` verified at d08cd0eb by jj push then branch fetch/bookmark inspection.
- Historical empty commit 9c0b024b37b3 required `--allow-empty-description`; inspected as the sole empty-description unpushed ancestor and retained unchanged.
- New work bookmark: `codex/analysis-board` to track accepted board commits.
- Push authorization: user's explicit remote backup and development instruction. No merge requested.

## Process

Use Superpowers writing-plans/subagent-driven-development/requesting-code-review/verification-before-completion and project verified-agent-workflow. jj workspace is already isolated. Bash skill helpers require a colocated Git tree and are replaced by bounded Python/PowerShell extraction and jj diff packages. Preserve workspaces/evidence. Each accepted task records candidate hashes, actual independent commands/results, specification/quality verdicts and accepted commit.

## Decisions

- Approved design uses stable Empty plus visible child sharing hidden result geometry; no IFC entity for the board.
- Existing datum-free result APIs remain usable as hidden source-only displays; no invented ground elevation.
- Free space stays categorical. Numeric range controls are inactive for the current Boolean result.
- Visual decision: only actual native placement/alignment and palette/opacity presentation require views. Ref validation, persistence and currentness use assertions.
- Independent preflight found the existing neutral Scene-update classifier misses unit-scale changes. Added exact source-scale reuse and unit-change lifecycle checks to Tasks 1/2: invalidate factual observation/consent and restore historical display at the correct scale, or hide on failure. Preflight otherwise identified no additional Important gaps.

## Task status

- [x] Initial remote checkpoint.
- [x] Task 1 board data/style/native presentation; independently accepted after fix round 1.
- [x] Task 2 runtime/UI/capture integration; independently rerun after bounded review fixes.
- [x] Task 3 native acceptance/visual/save-reopen and whole-scope review; production fixes are covered by the focused suite and the portable Blender run below.
- Human visual review: the required native views are generated and shown in this task; no visual approval is inferred from silence.

## Task 2 independent review and bounded fixes

The independent verifier reran the focused board/runtime/UI/capture suite in the
existing workspace: **267 passed** before the review fixes. The review identified
three bounded issues: restored board resources were not classified as display-only
when runtime references had been cleared; addon re-registration discarded a missed
scene-scale change; and Boolean free-space exposed inert numeric range controls.
The accepted fixes add ownership-tag classification without broadly exempting
source materials, route startup scale changes through the existing invalidation and
historical restore path, expose only explicitly registered result IDs in the saved
result selector, and explain that numeric range is unavailable for Boolean results.
The expanded affected suite then passed **410 tests** with the OCTA source path
configured from the adjacent project checkout. The three earlier session import
errors were environment path failures, not product failures.

## Native Blender acceptance

The required portable executable was verified as Blender **5.2.0 LTS** at
`D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`. The actual stored
S3 free-space result `fe3243c13b3f45daac8744efc46f3962` was attached in a
disposable native scene. Assertions passed for one stable board Empty, one hidden
result source, one visible display child sharing the source mesh, unchanged result
digest, explicit slab datum, and the visible child at slab top plus the 0.02 m
display lift while the calculation plane remains at 1.6 m. The saved file was
reopened in a separate Blender process; the board ID, active result, historical
status and hidden-source/visible-display roles were restored without currentness
or consent recovery.

Evidence generated under `outputs/design/analysis_board/native/`:

- `analysis_board_s3.blend` — disposable native save/reopen fixture.
- `analysis_board_s3.png` — actual S3 board plan/context view.
- `analysis_board_palette_opacity.png` — cividis, viridis, magma and magma at
  full opacity comparison.

The fixture uses a neutral slab datum plane as visual context; it does not modify
the original IFC. The authoritative result remains the external JSON sidecar.

## Task 1 candidate and first independent review

Candidate change slqmkxol / 9c38f93d (base d08cd0eb), frozen six-file SHA256
manifest under `.superpowers/sdd/2026-11-04-analysis-board/`. Implementer focused
suite passed 35 tests. Different verifier independently ran the required Pixi
suite: 35 passed in 0.76 s, with all six hashes unchanged before/after. A separate
four-case malformed-sidecar probe found Important I1: a JSON list/null/scalar
root reaches the reader as a non-mapping, raising AttributeError and leaving a
historical board visible. Specification FAIL; quality Needs fixes. Root sent the
unchanged finding to the original implementer for bounded fix round 1/5. See
[the independent report](analysis-board-task-1-review.md). Task 1 is not accepted.

Fix round 1/5 adds a Mapping-root guard and a four-case restore/select regression.
The different verifier ran the full focused command again: **39 passed in 0.88 s**;
an exact copy of the original independent sidecar probe now exits 0 for all four
roots, with unavailable status and viewport/render hiding. All six candidate
hashes match before/after, and root matched them again before acceptance. I1 is
ADDRESSED; specification PASS, quality Approved, no Important/Critical findings.
See [fix review](analysis-board-task-1-fix-1-review.md). Task 1 is complete in
change slqmkxol; accepted commit is recorded at the Task 2 workline transition.
Native rendering/save and runtime integration remain later gates.
