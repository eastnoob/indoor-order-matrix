# D6 Progress and Git Provenance Checkpoint Plan

> **For agentic workers:** This is a documentation and provenance audit plan. It does not authorize production implementation. Steps use checkbox syntax for tracking.

**Goal:** Reconcile the D6 analysis-domain/layout-handoff branch with its lifecycle checkpoints, preserve all existing design evidence, and produce a reproducible Git provenance checkpoint plus a design-only AnalysisDomain/UI handoff.

**Architecture:** Inspect the current checkout in place because existing untracked evidence must not be copied or discarded. Record a baseline inventory of every pre-existing untracked path, then append one dated progress section and create a report/manifest whose hashes and scope checks are independently verifiable. The next-stage handoff remains a design gate and explicitly defers production selector, public API, backend, threshold, resolution, Bayesian/ML, and live IFC integration choices.

**Tech Stack:** Git, PowerShell, SHA-256, JSON parsing, Markdown evidence records, and repository-local documentation.

**Spec:** `docs/project/space-field-ifc-neutral-scene-input-contract.md` and the D6 evidence records listed in the task request.

## Global Constraints

- Do not modify historical contract text.
- Do not run full pytest, Blender, full IFC adapter, Bayesian/ML, or selector work.
- Do not run `git clean`, `git add .`, reset, rebase, squash, force push, branch deletion, or bulk move/delete.
- Preserve every baseline untracked path and do not overwrite, move, or delete it.
- Add only explicitly named completed-checkpoint evidence and new audit artifacts.
- Stop at `STOP FOR D6 PROGRESS AND GIT PROVENANCE CHECKPOINT REVIEW`.

---

### Task 1: Freeze repository and checkpoint baseline

**Files:**
- Read: `AGENTS.md`, the neutral-scene contract, D6 progress/evidence records, and related review/manifest/verification files.
- Create: `docs/superpowers/plans/2026-10-06-d6-progress-git-provenance-checkpoint.md`

- [ ] Record branch, HEAD, branch tracking, upstream, commit graph, worktrees, status, and command exit codes.
- [ ] Verify the three lifecycle checkpoint commits are ancestors of the current branch and document their purposes.
- [ ] Capture the complete pre-existing `git ls-files --others --exclude-standard` list before creating new artifacts.
- [ ] Hash every baseline untracked path and classify its type, evidence relationship, integrity state, and keep/commit recommendation.

### Task 2: Update the dated progress record

**Files:**
- Modify: `docs/project/evidence/d6-space-field-design-progress.md`

- [ ] Append a 2026-10-06 section without rewriting earlier text.
- [ ] Record limited acceptance of lifecycle amendment and conflict-preservation design evidence.
- [ ] State that authored-domain precedence, unresolved-conflict gating, duplicate-event idempotence, and replacement lineage are design principles only.
- [ ] Define AnalysisDomain/UI handoff as the next gate and list its design-only inputs, lifecycle, UI states, scope roles, and downstream refusal rule.
- [ ] Keep production implementation, selector, public API, Bayesian/ML, and real IFC production integration deferred.
- [ ] Record the provenance audit location, command scope, and limitations.

### Task 3: Write provenance report and manifest

**Files:**
- Create: `docs/project/evidence/d6-space-field-git-provenance-checkpoint-2026-10-06.md`
- Create: `docs/project/evidence/d6-space-field-git-provenance-manifest-2026-10-06.json`

- [ ] Include branch, HEAD, checkpoint ancestry, branch purpose, worktree list, audit commands, exit codes, baseline untracked inventory, hashes/bytes/types, recommendations, scope audit, whitespace check, JSON parse check, and manifest self-consistency rules.
- [ ] Record the exact named paths that are committed and why.
- [ ] Keep uncertain or temporary artifacts untracked and explain why.
- [ ] Include the AnalysisDomain/UI handoff design gate without selecting production policy.

### Task 4: Explicitly stage only the bounded evidence set

**Files:**
- Add by explicit path only: the updated progress file, the plan, the provenance report, and the provenance manifest.
- Add other existing untracked files only if direct evidence shows they are complete checkpoint artifacts and their companion review/manifest/verification are present.

- [ ] Record pre-commit `git diff --cached --name-status` and `git diff --cached --check`.
- [ ] Commit the bounded set with a descriptive D6 provenance message.
- [ ] Record commit SHA and post-commit `git status --short --branch`.

### Task 5: Final verification and stop

**Files:**
- Read/verify: all created and modified artifacts plus unchanged historical contract.

- [ ] Parse every new JSON file.
- [ ] Recompute every listed byte count and SHA-256.
- [ ] Verify manifest rows match the baseline inventory and no baseline untracked path disappeared or changed.
- [ ] Verify historical contract hash/content is unchanged.
- [ ] Run only the audit, documentation, JSON, hash, byte, whitespace, and scope checks listed in the task.
- [ ] Report gates, evidence, correction rule, limitations, unresolved questions, exact commits, complete retained-untracked inventory, and stop at the requested review marker.
