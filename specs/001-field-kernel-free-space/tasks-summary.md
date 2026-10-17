# Tasks Summary: Field Kernel and Free-Space Read-Only Slice

## Counts

- Total tasks: **43**
- User Story 1 (P1, Field core): **8** tasks (`T009-T016`)
- User Story 2 (P2, B3 read-only adapter + standalone visualization): **9** tasks (`T017-T025`)
- User Story 3 (P3, fixture replay and channel isolation): **7** tasks (`T026-T032`)
- User Story 4 (P2, exact-cell physical occupancy field): **6** tasks (`T038-T043`)
- Setup: **4** tasks (`T001-T004`)
- Foundational: **4** tasks (`T005-T008`)
- Polish and cross-cutting: **5** tasks (`T033-T037`)

## Dependency order

`Setup -> Foundational -> US1 -> (US2 || US3) -> US4 -> Polish`

US1 is the MVP and the only story required before an owner checkpoint. US2 depends on the Field sample contract for typed adapter output. US3 depends on the same canonical status/provenance semantics but can run in parallel with US2.

## Parallel opportunities

- Setup evidence checks: `T003-T004`
- Foundational fixtures: `T006-T007`
- US1 tests: `T009-T011`
- US2 tests: `T017-T020`
- US3 tests: `T026-T028`
- After US1, the US2 and US3 phases can be staffed in parallel because they use separate implementation/test files.

## Independent test criteria

- **US1**: `pixi run pytest test/test_field_core.py -q`; scalar and batch lookup canonicalize identically, and all six statuses remain distinct.
- **US2**: `pixi run pytest test/test_space_field_adapter.py test/test_space_field_visualization.py -q`; accepted B3 identity and limitations survive adaptation, and visual states do not collapse unknown/invalid/outside/conditional into free.
- **US3**: `pixi run pytest test/test_field_fixture_replay.py -q` twice; normalized replay outputs match and perturbations remain channel-local.

## Current implementation checkpoint

- US1 and US2 focused tests plus the unchanged B3 loader baseline pass with the
  owner command: `PYTHONPATH=. pixi run pytest test/test_field_core.py
  test/test_space_field_adapter.py test/test_space_field_visualization.py
  test/test_discrete_space_field.py -q` (**74 passed**, including the US3 replay tests).
- `features/field_core.py`, `features/space_field_adapter.py`, and
  `features/space_field_visualization.py` compile successfully.
- US3 replay tests pass in a two-run owner check; both manifests share the
  canonical SHA `a734362f...019a04`, and the three unsupported transitions are
  explicitly blocked/design-only.
- Precision-repair evidence reports **67 new + 74 existing = 141 passed in
  5.53s**. This is recorded evidence for the accepted isolated slice. The
  quickstart probe reports 8/8 with
  `formula_scope=probe_only_not_production`.
- No staged files; no loader, evaluator, room-model, default-overlay, or live
  promotion changes. SVG/HTML rendering, `FreeSpaceFieldBundle`, and the
  constitution gate remain open.

## MVP scope

The MVP was **US1**: a pure `features/field_core.py` contract plus `test/test_field_core.py`. The current completed slice also includes US2's read-only B3 adapter and JSON-friendly field-layer manifest. It still does not create a free-space evaluator, change `evaluate_scene`, change `room_analysis_model`, alter the existing B3 loader, or claim production occupancy/clearance.

## Explicit exclusions

No tasks schedule:

- live evaluator promotion or changes to `features/scene_evaluator.py`;
- complete occupancy, clearance, route width, connectivity, door-state, or whole-height certification;
- Bayesian calibration, final inferred-group selection, or probability claims;
- changes to `features/discrete_space_field.py` or its return shape;
- changes to the public `room_analysis_model`;
- changes to existing default evaluator visualization;
- Git add/commit/push/merge during this planning workflow.
- The full end-to-end Field framework demonstration is a later, non-blocking
  architecture/communication artifact; it is not required for this feature's
  MVP or acceptance gate.

## Unresolved gates

1. `.specify/memory/constitution.md` is still a placeholder; owner review or explicit waiver is required before any implementation checkpoint can be marked compliant.
2. Exact Python symbol/protocol shape for `Field`, `B3AdapterView`, and the field-layer manifest is frozen and implemented in US1/US2; later capability composition still requires a separate owner decision.
3. Future analysis-domain/opening semantics, numeric batch-performance target, and evidence aggregation rule remain open.
4. B3 remains a conditional, read-only section seam; complete occupancy and clearance remain unavailable.

## File and checkpoint map

| Story | Planned implementation files | Planned tests | Future checkpoint rule |
|---|---|---|---|
| US1 | `features/field_core.py` | `test/test_field_core.py` | Explicit paths only; constitution gate unresolved |
| US2 | `features/space_field_adapter.py`, `features/space_field_visualization.py` | `test/test_space_field_adapter.py`, `test/test_space_field_visualization.py` | Existing loader/evaluator untouched |
| US3 | `scripts/design/group_level/run_field_fixture_replay.py` | `test/test_field_fixture_replay.py` | Implemented diagnostic replay; no production promotion |
| US4 | `features/free_space_field.py` | `test/test_free_space_field.py` | Implemented; 67 new + 74 existing = 141 evidence recorded; B3/live promotion remains open |

## Scope audit

The task-generation workflow itself only produced `tasks.md` and this summary;
later US1/US2/US3 implementation and architecture updates are recorded above.
No Git index mutation was performed by either workflow.
