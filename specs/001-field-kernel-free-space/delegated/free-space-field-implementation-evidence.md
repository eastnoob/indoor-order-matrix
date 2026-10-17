# FreeSpaceField Implementation Evidence

Date: 2026-10-10

## Pre-implementation baseline

The repository contains unrelated mixed dirty changes from earlier work. No
reset, clean, add, commit, push, or branch switch was performed. The Git index
was inspected and not mutated.

Protected-file SHA256 baseline:

```text
AGENTS.md 82E0F9FED85951F4444CC8A60AA87EE0578EE370862A2EE645E6E19735646112
docs/indoor_layout_evaluation_matrix_architecture_memory.md E67C01B30DBC0D51E2E88EF71D57AE9A221AE44746992860D7D4C92058CF0C37
docs/software-architecture.md 781C6252FED83F32CB6E59EA9ABD0894C6E9CA96CB8EC0F8528D97996B75E368
docs/project/free-space-field-instance-design.md A703CCE325B58A8C791B7D919B65C31DC1BD77D1F1DAFE83655342B481CD03E7
features/field_core.py F711988F8BC80A6474EB54FFEC92291AA75F07178F67087848C66DC3D91ECF2C
features/neutral_scene_views.py B804901AB43D9E61B4AC60C8C14325E87CE9E41A658A87B63E91260E27A84F73
features/geometry_views.py 63BC5734F9D6FD6169DD94C75EE01D66F08ADFBDD746ACB84303F0FBF90E0578
```

Speckit prerequisites passed with
`check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`; extensions exist
but have no executable hooks. The constitution remains a template
placeholder and is still pending.

## Scope

Only these implementation paths are allowed:

```text
features/free_space_field.py
test/test_free_space_field.py
```

No evaluator, room model, B3 loader, source scan, substitute resolver,
dependency, Blender, IFC, or public export changes are permitted.

## US4 execution evidence

Red test before implementation:

```text
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py -q
exit 1
ModuleNotFoundError: No module named 'features.free_space_field'
```

Green focused result after implementation:

```text
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py -q
10 passed
```

Compilation:

```text
$env:PYTHONPATH='.'; pixi run python -m py_compile features/free_space_field.py test/test_free_space_field.py
exit 0
```

Affected owner suite:

```text
$env:PYTHONPATH='.'; pixi run pytest test/test_field_core.py test/test_space_field_adapter.py test/test_space_field_visualization.py test/test_discrete_space_field.py test/test_field_fixture_replay.py -q
74 passed in 4.60s
```

The focused tests cover positive-area domain clipping, complete holes, source
line/point behavior, invalid versus unavailable, unsupported section queries,
accepted substitute conditional status, unresolved-source propagation,
immutable handoff state, duplicate owner refusal, and consumption of a
canonical `analysis_scene_view` mapping. The field does not rescan sources or
invoke a resolver.

## Owner review follow-up

Writing is stopped at this point for a subsequent precision-fix task. The
following issues remain open and are intentionally not changed in this turn:

- The current “analysis_scene_view” test passes a synthetic legacy mapping
  through the passthrough branch; it does not exercise a `NeutralSceneV2`
  resolver handoff.
- `eligible.area` is currently compared with the query tolerance in the
  domain-membership gate; the owner requires positive-area semantics without
  silently dropping a positive sliver.
- The subclass `__setattr__` needs an independent audit against the core
  metadata-freeze behavior; the current implementation may bypass or diverge
  from that contract.
- Geometry/component provenance is not yet carried into every returned sample's
  support/provenance payload.

These are review findings, not claims of completion or owner acceptance.

## Superseding precision-repair record

The section above is retained as historical intermediate evidence. It is
superseded by `delegated/free-space-field-precision-repair.md` and the final
review record. The final focused result is **67 passed in 0.19s** and the
combined result is **141 passed in 5.53s** (67 new plus the original 74,
exit 0). The intermediate 10/74 and 62/136 counts remain historical only.

The final review reports the original findings and the historical passthrough
view gap resolved, with 4 targeted real-view checks passing and no remaining
blocker in scope. B3/live promotion and constitution ratification remain open.

Final documentation-sync compile check:

```text
$env:PYTHONPATH='.'; pixi run python -m py_compile features/free_space_field.py test/test_free_space_field.py
exit 0
```

Self-contained quickstart example:

```text
$env:PYTHONPATH='.'; <inline quickstart construction> | pixi run python -
stdout: established True
exit 0
```
