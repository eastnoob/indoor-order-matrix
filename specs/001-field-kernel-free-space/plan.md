# Implementation Plan: Field Kernel and Free-Space Read-Only Slice

**Feature ID**: `001-field-kernel-free-space` | **Current Git branch**: `codex/d6-analysis-domain-layout-handoff` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-field-kernel-free-space/spec.md`.

**Note**: This template is filled in by the `$speckit-plan` command; its definition describes the execution workflow.

## Summary

Define one small, global field contract that can represent spatial and
relational evidence while keeping domain, frame, query context, status, and
provenance explicit. US1-US3 provide the core, B3 read-only seam, and
diagnostic replay. US4 adds the exact-cell `FreeSpaceField` over pre-resolved
whole-height plan components. The plan still stops before live evaluator
promotion, complete clearance, or a final inferred-group algorithm.

## Technical Context

**Language/Version**: Python 3.12.13 via Pixi (`>=3.12,<3.13`).

**Primary Dependencies**: Existing project dependencies, standard library
dataclasses/typing, Shapely already installed in the project environment, and
current pytest/Pixi tooling. No new runtime dependency.

**Storage**: Versioned Markdown/JSON evidence artifacts; no database.

**Testing**: `pixi run pytest` plus deterministic fixture replay commands.

**Target Platform**: Windows development workspace; portable Blender only for a
later explicitly requested visual check.

**Project Type**: Python analysis library with design/probe scripts.

**Performance Goals**: Keep scalar lookup cheap and make batch lookup the normal
path; do not allocate a dense 3D field by default. A numeric production
threshold is NEEDS CLARIFICATION and belongs to a later benchmark gate.

**Constraints**: Preserve B3 JSON/schema/hash compatibility; preserve unknown,
outside, invalid, and not-available semantics; do not import `scripts.design`
from production features; do not change `evaluate_scene` or public room-model
shape in this slice.

**Scale/Scope**: One field core, one read-only B3 adapter seam, one standalone
visualization manifest contract, eight synthetic design fixtures, and one
exact-cell `FreeSpaceField` instance.

## Constitution Check

*GATE: pending. `.specify/memory/constitution.md` is still the generated
placeholder template, so this plan cannot claim a ratified constitution pass.*

- Existing project constraints from `AGENTS.md` and the two architecture
  documents are treated as working constraints.
- No implementation or merge gate may be marked constitution-compliant until
  the owner reviews a project-specific constitution or explicitly waives it.
- This is a planning blocker, not a reason to invent principles or silently
  modify the constitution file.



## Project Structure

### Documentation (this feature)

```text
specs/001-field-kernel-free-space/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)
```text
features/
├── field_core.py                     # implemented pure Field contract
├── discrete_space_field.py           # existing B3 loader; unchanged
├── space_field_adapter.py            # implemented read-only B3 -> Field adapter
├── space_field_visualization.py      # implemented JSON manifest; renderer future
└── free_space_field.py               # US4 exact-cell occupancy instance

specs/001-field-kernel-free-space/
├── checklist.md
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── owner-decision.md
├── git-scope.md
├── contracts/
└── delegated/

test/
├── test_field_core.py                # implemented contract tests
├── test_space_field_adapter.py       # implemented adapter tests
├── test_space_field_visualization.py # implemented manifest/state tests
└── test_free_space_field.py          # US4 focused contract tests
```

**Structure Decision**: Add one concrete composition over `Field`, using
existing geometry helpers and pre-resolved components. Do not add a second
base hierarchy, runtime `FieldBundle`, source scanning, resolver calls, or
evaluator bridge. Existing B3 loader and live evaluator boundaries remain
intact.

## Phases and gates

1. **Baseline** — run the existing probe twice, freeze hashes, and retain the
   `probe_only_not_production` label.
2. **Research** — resolve the minimum core contract and document alternatives.
3. **Data model/contracts** — specify samples, status, provenance, adapter, and
   visualization manifest without changing production callers.
4. **Fixture validation** — run S0–S3 replay and channel-isolation checks.
5. **Architecture sync** — keep the architecture map aligned with implemented
   core/adapter/manifest/replay boundaries.
6. **US4 implementation** — exact-cell field and focused tests are present;
   final evidence is 67 focused plus 74 existing tests, 141 total in 5.53s,
   and the isolated slice is owner-accepted.
7. **Promotion gate** — B3/live evaluator promotion remains open;
   constitution remains unratified.

The detailed living checklist is [checklist.md](checklist.md).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution gate remains pending | The repository constitution is an unfilled template | Do not fabricate or silently ratify governance while planning |


