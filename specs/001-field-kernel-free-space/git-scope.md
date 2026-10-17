# Git Scope for 001 Field Kernel + Free-Space Planning

## Current rule

Do not reset, clean, stage all, commit, push, or merge from this planning
workflow. The current branch is `codex/d6-analysis-domain-layout-handoff` and
already contains mixed B3/D6/architecture changes from earlier work.

## Files owned by this planning slice

Only the following new subtree belongs to this feature-planning checkpoint:

```text
specs/001-field-kernel-free-space/
├── checklist.md
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── git-scope.md
├── s0-probe-evidence.json
├── s0-probe-evidence-2.json
├── s0-session-manifest.json
├── contracts/
└── delegated/
```

The two fixture inputs and the existing probe are evidence sources, not files
to stage as part of this checkpoint.

## Explicitly excluded

- Existing modified files under `features/`, `test/`, `docs/`, and
  `scripts/design/` unless a later owner-approved implementation task names an
  exact path.
- The existing B3 serialized packages and their prior evidence outputs.
- Any live IFC/Blender artifacts.

## Planned future commits

1. Planning evidence and contracts only, after owner review of the constitution,
   public naming, and status precedence gates.
2. Pure Field core plus focused tests, with no evaluator or B3 loader changes.
3. Read-only B3 adapter plus focused tests.
4. Standalone visualization manifest/renderer plus focused tests.
5. Optional explicit evaluator bridge only after a separate promotion decision.

Each commit must stage explicit paths and inspect staged scope before creating a
checkpoint. No commit is authorized by this document.

## Audit command

Use the following before any future checkpoint:

```powershell
git status --short
git diff --name-only
git diff --cached --name-only
```

The first two commands are inspection only. The third must be empty before
staging this feature unless an owner-approved checkpoint is being prepared.

