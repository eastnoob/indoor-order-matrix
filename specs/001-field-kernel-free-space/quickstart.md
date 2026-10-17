# Quickstart validation guide

This guide validates planning artifacts and design-only fixture behavior. It
does not run the live IFC evaluator or promote B3.

## Prerequisites

From the repository root, use the Pixi environment described in `AGENTS.md`.

```powershell
pixi install
```

## Baseline probe

```powershell
pixi run python scripts/design/group_level/run_self_description_competition_probe.py `
  --fixtures scripts/design/group_level/self_description_competition_fixtures.json `
  --output specs/001-field-kernel-free-space/s0-probe-evidence.json
```

Expected result: 8 checks and 8 passes, with
`formula_scope: probe_only_not_production`.

## Deterministic replay

Run the same command to a second output path, then compare canonical JSON
content or SHA256 after normalizing only the output path. The fixture and runner
hashes must be recorded in the session manifest.

## Planned field-core checks

When implementation begins, run the focused contract tests for scalar lookup,
batch lookup, status preservation, provenance, outside-domain behavior, and
unknown-versus-free refusal. Do not add a public export or evaluator bridge
until these pass.

## Planned adapter checks

Use a temporary accepted B3 package fixture. Verify that the adapter preserves
the existing loader return shape and all package identity fields. Assert that
complete occupancy geometry and complete clearance remain unavailable where the
package says so.

## Planned fixture sessions

- **S0:** existing probe replay and artifact manifest.
- **S1:** field-record mapping and scalar/batch canonical equivalence.
- **S2:** channel isolation across geometry, space, semantic, and context.
- **S3:** translation/rotation/id-order and missing/invalid/opening perturbations.

Every session writes a manifest, canonical observations, assertions, status
matrix, perturbation diff (if applicable), artifact hashes, and a short summary.

## Exact-cell FreeSpaceField

The isolated US4 check is:

```powershell
$env:PYTHONPATH='.'
pixi run pytest test/test_free_space_field.py -q
pixi run python -m py_compile features/free_space_field.py test/test_free_space_field.py
```

The instance consumes only the explicit domain and pre-resolved
`physical_occupancy` handoff. It does not scan sources, resolve substitutes,
load B3 JSON, or call `scene_evaluator`. A minimal direct call uses the frozen
whole-height context:

```python
from features.field_core import FieldQuery
from features.free_space_field import FreeSpaceField

domain_components = {
    "id": "room-a",
    "frame": "world-xy",
    "components": [{
        "exterior": ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)),
        "holes": (),
    }],
}
resolved_records = [{
    "id": "table-1",
    "geometry_components": [{
        "exterior": ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        "holes": (),
    }],
    "represented_source_ids": ["table-1"],
    "representation_status": "original",
    "representation_provenance": {"source": "quickstart"},
}]
field = FreeSpaceField(
    domain=domain_components,
    origin=(0.0, 0.0),
    spacing=1.0,
    n_rows=2,
    n_cols=2,
    physical_occupancy=resolved_records,
    unresolved_source_ids=(),
    query_context={"domain_id": "room-a", "frame": "world-xy"},
    frame="world-xy",
    origin_offset=(0.0, 0.0),
)
sample = field.evaluate((0, 0), FieldQuery(domain_id="room-a", frame="world-xy"))
```

For the current repository checkout, the focused plus historical owner suite
is:

```powershell
$env:PYTHONPATH='.'
pixi run pytest test/test_free_space_field.py test/test_field_core.py `
  test/test_space_field_adapter.py test/test_space_field_visualization.py `
  test/test_discrete_space_field.py test/test_field_fixture_replay.py -q
```

