---
name: verified-agent-workflow
description: Use when planning or resuming multi-step engineering work in order_analyzer that involves delegated implementation, independent acceptance, or geometry and scene verification.
---

# Verified Agent Workflow

Use the existing Spec Kit and Superpowers capabilities with this project's jj and acceptance rules. Keep a single traceable path from requirement to task, implementation, independent evidence, and accepted local commit. This skill does not start product work when the user only requests planning or documentation.

## Establish the workline

Read project memory, then `docs/software-architecture.md`. Inspect actual callers, tests, fixtures/config and exports; distinguish current-checkout code from sibling-workspace code. Reuse the existing spec, plan, checklist and ledger rather than opening a duplicate feature.

For **every branch/workline**, record workspace name and absolute path, base, change ID, current commit ID, scope and version writer. Inspect installed jj help; use `jj --ignore-working-copy` for read-only history inspection and inspect actual file bytes separately. Those jj views may omit unsnapshotted edits.

Reuse a suitable task-owned `jj workspace`. Isolate independent implementation branches in their own jj workspaces; successive dependent tasks can stay in one workline as separate changes. A workspace is not needed for every checkbox or read-only agent. Preserve unrelated dirty work, including other edits in shared documentation. Only the designated version writer changes history; subagents do not snapshot, commit, rebase, merge or push unless explicitly assigned that role. Use Git only for a concrete jj limitation, recording the reason. Keep existing push/merge authorization boundaries.

## Check intent before implementation

Apply the available Spec Kit stages as appropriate: specify/clarify → plan/checklist/tasks → analyze. Reuse decisions already supplied by the user. Ask only for an unresolved requirement that materially changes correctness; resolve routine implementation choices autonomously.

`speckit-analyze` is read-only. Its findings go to a separate authorized correction step. Formal Spec Kit commands require their actual feature artifacts; when those are absent, apply the same coverage/consistency assessment to the existing plan and label it an assessment, not a completed command. Do not manufacture a second specification or change the constitution to unblock a task.

For each task, prepare a brief containing the requirement, allowed files, consumed/produced interfaces, acceptance assertions, commands, dependencies, and **visual decision** below. Check coverage and interface consistency before dispatch. Use `superpowers:writing-plans` for concrete implementation plans and `superpowers:subagent-driven-development` for continuous task execution.

## Decide whether a visual is necessary

Each brief records `visual: required / omitted / reuse`, the correctness question, and the evidence that answers it.

1. Identify the remaining correctness question after numerical assertions, identity checks, logs and tests. A spatial task alone does not justify a picture.
2. Require a visual when those checks cannot adequately establish the result: for example, an uncertain live transform, visible plane/domain placement, source-to-projection alignment, or whether the result depicts the user's intended real region. State what the view will resolve.
3. Omit visuals when direct evidence is sufficient: cache hits/invalidation, call counts, hashes, serialization, freshness rejection, or metadata-only changes. A picture cannot prove these properties.
4. Reuse an existing verified visual if its geometry, frame, domain and result dependencies are unchanged. Combine several questions in one view; do not regenerate a view per checkbox. A failed or doubtful spatial check can change the decision to `required`.

For a required visual, generate the smallest useful view: a plan, side/section view, or boundary close-up. Use actual data, label identity/units, and link its input/result references and hashes in the evidence record. Do not invent an unobserved scene case to fill a picture. The independent verifier checks the view against numerical/source evidence; deliver the view inline or open it for the user, with a short explanation of what to inspect.

**Visual delivery does not automatically add approval.** Continue work that does not depend on the user's answer. Wait only when the user explicitly requested approval, or when correctness depends on a still-unresolved user interpretation, such as which region was intended. Record pending user review separately from technical verification and local commits; never claim user acceptance from silence or an agent's inspection. Do not ask again for an unchanged, already confirmed region.

## Execute and accept each task

1. A fresh implementer receives the brief and necessary interfaces, makes the smallest complete change, and self-tests. Add meaningful regression/behavior checks for nontrivial logic; avoid tests that mirror implementation or ceremonial tests for prose edits.
2. Freeze the candidate: pause writers and record the actual relevant file hashes and diff. Do not use a revision ID alone as proof of uncommitted bytes.
3. A different verifier actually runs the acceptance commands and records cwd, environment, command, exit code, results, log/artifact paths and candidate hashes. Geometry expectations need an independent basis. An implementer's success report is not independent verification.
4. Using `superpowers:requesting-code-review`, obtain explicit specification and code-quality verdicts. The verifier can also review a small task, but cannot verify their own implementation. Fix substantive failures, rerun affected checks and re-review the changed candidate.
5. Apply `superpowers:verification-before-completion`. The version writer checks the tested bytes still match, commits only task-owned changes with jj, records the accepted commit and advances to the next task. Keep unrelated edits out of the accepted change, including edits in the same file. A draft snapshot/checkpoint is not accepted completion.

Run tasks continuously without asking permission at each transition. A necessary pending human interpretation blocks only its dependent work. Product reviews, irreversible operations and external side effects retain their existing authorization requirements.

## Converge and resume

After implementation, compare the actual code and artifacts with every requirement. Where a valid Spec Kit feature exists, use `speckit-converge` after its implement stage; it appends traceable remaining tasks, does not implement them or rewrite prior tasks. Otherwise perform the equivalent gap assessment in the current checklist. Do not erase a requirement to make the assessment pass.

Persist per task: requirement → brief → workspace/base/change → candidate hashes → independent test evidence → spec/quality verdicts → visual decision and any user-review state → accepted commit/artifacts/limits. Update architecture with changes. Resume from this ledger and actual history after compaction; do not repeat completed tasks. Finish with whole-scope independent review and only the affected final regressions or real-scene checks. Do not automatically push, merge or delete workspaces/evidence.

Current application: [free-space prerequisite checklist](../../docs/superpowers/plans/2026-11-04-free-space-prerequisite-checklist.md). Its S3, IFC, 1.6 m height and domain choices are task-specific, not universal workflow defaults.
