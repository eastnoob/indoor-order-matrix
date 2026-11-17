# Accepted A/B/C Owner Integration Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` with the project verified-agent workflow. Root is the sole jj history writer.

**Goal:** Integrate the accepted A/B/C delivery into the existing owner root while preserving both the owner's hierarchy behavior and the accepted parameter/cache/semantic-port contracts.

**Architecture:** Merge the two pinned histories in an isolated jj workspace. Resolve only actual conflicts and current-status documentation, reuse existing implementations and tests, and promote the verified tree to the owner root without rewriting accepted history.

**Tech Stack:** Python 3.12, Pixi, pytest, Jujutsu; existing OCTA and geometry dependencies.

**Spec:** Existing [parameter/cache design](../specs/2026-11-15-parameter-owned-sidecar-cache-design.md), [C plan](2026-11-15-output-port-and-intermediate-cache.md), and the user's 2026-11-17 instruction to deliver a usable, clean integration without functional regression. This is integration, not new feature design.

## Global Constraints

- Owner source: `default` at `e54867c22066a5d6475de8c9ff62d04ca13aae3e`; accepted source: `codex/parameter-cache-c-accepted` at `3f9e6c45b7f3ffbf099e519b4d70e31bebe2c3e3`.
- Workspace: `abc-owner-integration-20261117`, `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/abc-owner-integration-20261117`; initial merge change `tptrxvqqktyzswnqwttrptrzyvkrqwnp`, candidate snapshot `1dd2f744d9ca81d465b53bcd062637e7029ff27e`.
- Root alone snapshots, commits, edits workspace revisions/bookmarks, or promotes the candidate. Other agents edit only explicitly assigned files or write independent verification reports.
- Preserve four owner-only research/evidence files and unrelated workspace contents. Keep accepted A/B/C and rejected historical candidates intact; exclude unaccepted draft `f9194090`.
- Preserve hierarchy, combined APIs, pure-axis/modulation, Euclidean/path separation, cache integrity/migration/lifecycle, and ordinary CLI omission meaning unconstrained clearance.
- Use Pixi with the existing locked environment; no dependency installation, pip/venv, live IFC/Blender run, numerical formula change, UI work, new parameter platform, or remote push.
- All modified project functions retain English-first docstrings and meaningful why-comments. No blanket style changes or whole-tree overwrite.
- Visual decision: reuse existing scene evidence. Integration correctness is established by source preservation, exact data hashes, and existing regression tests; no geometry or placement change is intended.

### Task 1: Resolve the cumulative integration

**Files:** Eleven conflicted paths listed by `jj resolve --list`, the automatically merged potential runner, current C status documents, and only regression tests needed for actual resolution changes.

**Interfaces:** Preserve root hierarchy/replay call signatures and C processor, cache, and semantic-port entry points. Do not expose new knobs or switch legacy CLIs to semantic ports.

- [x] Resolve the two code conflicts against both pinned parents; inspect all callers and keep the accepted implementation where it already preserves root behavior. Add a regression only for a concrete uncovered merge behavior.
- [x] Resolve nine document conflicts, retain historical evidence, fix obsolete C push state, and state the actual integrated implementation versus unverified native workflow boundaries.
- [x] Preserve the four owner-only files and exclude the incidental `global_diag1.log` from the resulting tree without deleting historical evidence.
- [x] Run focused self-checks for the resolved potential/hierarchy behavior. Record files, commands, results, and any remaining issues.

### Task 2: Independently verify the final candidate

**Files:** Existing parameter/cache/port/distance/free-space/potential/hierarchy tests, retained test artifacts, and plan-scoped evidence reports.

- [x] Freeze and hash the final relevant candidate. A different agent runs the affected regression gates in the integration workspace with exact commands, exit codes, node outcomes, runtime, and retained-artifact hashes.
- [x] Obtain explicit SPEC PASS and QUALITY APPROVED review covering root behavior preservation, accepted contracts, imports/exports, documentation, and scope.
- [x] Repair substantive failures and rerun only affected checks; do not infer integration success from historical A/B/C acceptance.

### Task 3: Commit and reconnect the owner root

**Files:** Accepted integration change and owner root workspace; no remote branch changes.

- [x] Recheck the tested bytes, absence of conflicts/markers, preserved owner files, and immutable accepted bookmarks. Commit the accepted integration and create `codex/abc-owner-integration-accepted`.
- [x] Verify the owner root still matches its pinned clean source, then advance its empty working copy onto the accepted integration. Preserve ignored/untracked artifacts and verify the resulting source bytes match the accepted candidate.
- [x] Run a root-path import/CLI smoke check and a small relevant regression selection. Record clean status, accepted commit, rollback source, and untested boundaries.

## Preflight assessment and rulings

| Shared boundary | Assessment |
| --- | --- |
| Task 1 code / Task 2 tests | Root hierarchy and accepted cache/modulation behavior must both survive; test the actual resolved bytes. |
| Task 1 docs / Task 3 promotion | Describe isolated implementation before promotion, then record actual root integration without claiming native Blender acceptance. |
| Task 2 freeze / Task 3 commit | Only evidence/status prose may change after executable verification; recheck all frozen production/test bytes before commit. |

Ruling: The user's local integration instruction authorizes the final root reconnection after verification; no repeated merge approval is needed. Remote push is not part of this instruction.

Ruling: Use native jj workspaces rather than the skill's Git-worktree helper. Its shell helper derives a Git root and can target the wrong tree in a non-colocated jj workspace; create equivalent plan-scoped briefs/reports with explicit absolute paths.

Ruling: Run complete affected test files and retained acceptance gates, not the full repository or live geometry. This follows the user's targeted integration scope; broaden checks only for a concrete touched dependency or failure.

Ruling: The first workspace-add invocation used `--ignore-working-copy` and created only an empty registered workspace before refusing checkout. Inspection confirmed no files and a root-parent empty revision; a normal `jj new` inside that task-owned workspace then created the intended two-parent merge. The owner source was untouched.

## Execution record

- 2026-11-17: Two-parent integration workspace created; native jj reports the same eleven conflicts predicted by the read-only audit. Implementation and acceptance pending.

- 2026-11-17 Task 1 complete: both code conflicts resolve to accepted C, which retains the owner hierarchy/namespace/replay behavior. Nine document conflicts resolved without dropping owner decisions; four owner-only files preserved and incidental log excluded. Implementer self-checks: 68 processing/lifecycle PASS plus 12 scalar PASS; the initial missing-basetemp setup attempt remains documented separately.
- 2026-11-17 Task 2 complete: independent fresh acceptance is **84 distinct PASS / 84 executions**, comprising 78 integration tests (650.80 s) plus six backend-sensitive tests (1.65 s), both exit 0 with no exclusions. All 1,191 frozen files, 30 profile hashes, 74 fixture/source checks and retained evidence remain unchanged. Independent review is **SPEC PASS / QUALITY APPROVED**, with its two status-only corrections applied before commit.
- Evidence: `D:/temp/oa-abc-integration-20261117/independent/integration-acceptance.json` and `D:/temp/oa-abc-integration-20261117/review/verdict.json`. Historical C acceptance remains the explicit 619+1 union; B remains its original 786 PASS. These are retained evidence, not fresh reruns.
- Environment qualification: root and B/C use NumPy 2.4.3 but different binary distributions; SciPy is absent from root. The six added existing tests cover the actual clearance, exact-section, enclosure/fallback and free-space reuse seams. Neither environment was changed, and binary-build identity is not claimed.

- 2026-11-17 Task 3 complete: accepted integration merge `fae03b2a2a7fb92cc3bea68587af0e65d7c054b8` joins owner `e54867c22066a5d6475de8c9ff62d04ca13aae3e` and accepted C `3f9e6c45b7f3ffbf099e519b4d70e31bebe2c3e3`. The local `codex/abc-owner-integration-accepted` bookmark follows the final documentation-only completion commit. Accepted C history and the excluded draft remain unchanged.
- The owner root is reconnected. All 359 executable/configuration paths and the fixed test inputs match the tested candidate's actual bytes; all 1,191 promoted paths match its normalized content before this completion prose. Existing unrelated document/artifact line endings are preserved. All 30 compatibility-profile hashes match and the real legacy-backend admission succeeds. All four owner-only files retain their original bytes.
- Root-path acceptance: **23/23 PASS** (4.672 s), five CLI `--help` entries exit 0, and actual package imports resolve to the owner root. Receipt: `D:/temp/oa-abc-integration-20261117/root-smoke/acceptance-result.json`; XML and exact commands are beside it. The root smoke repeats a small path-sensitive subset; do not add its count to the independent 84 as distinct tests.
- Finalization setup records are preserved: the raw-byte post-checkout guard stopped at an unrelated historical patch, then read-back established EOL-only differences and alignment was narrowed to functional source/config/fixtures. The first smoke import probe used the obsolete top-level `analyzer` path; the probe was corrected to the actual public `.features.analyzer` export before tests ran. Neither case required a product or test change.
- Local source rollback remains available at `e54867c22066a5d6475de8c9ff62d04ca13aae3e`; use a new jj change from that source after preserving any later work. This source checkpoint is not a claim of automatic IFC/Blender/runtime rollback. No workspace, model cache or historical evidence was deleted; no integration push was performed.
- Final IDs and clean status are recorded externally in `D:/temp/oa-abc-integration-20261117/completion.json`, avoiding a self-referential commit hash in this file. Whole-repository and fresh native/visual acceptance remain outside this integration.
