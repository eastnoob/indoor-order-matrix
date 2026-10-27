# Seed evidence layer visualization v1

## Purpose

This output-only view shows the separate evidence channels for one real
authored furniture-group seed. It reuses the retained IFC-derived
`plan_geometry.json` and `envelopes.json`; it does not reload IFC, create
geometry, infer membership, or derive strength.

## Selected source and seed

- Source run: [`run_20261027T165920Z_fb0d96`](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96)
- IFC SHA-256: `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`
- Analysis plane: `ifc-world-plan`
- Seed: `ifc-group:0$9EwHOwDKmu25$icFA5wm`
- Scope: 37 groups; 36 seed-to-scope relations

The selected seed is deterministic: it is the lexicographically first group
from the first contact relation in the retained envelope set. Across its 36
relations, the source contains one contact member-pair observation and no
positive-area overlap observation. All 36 relations retain source IDs.

## Layers

The renderer is
[`render_seed_evidence_layers.py`](../../../scripts/design/group_level/render_seed_evidence_layers.py).
The output manifest is
[`manifest.json`](../../../outputs/design/group_seed_evidence_layers/run_20261027T_seed_layers_v1/manifest.json).

| Layer | Meaning | SVG |
| --- | --- | --- |
| Distance | Seed-to-scope lines ranked by minimum normalized boundary gap | [`distance.svg`](../../../outputs/design/group_seed_evidence_layers/run_20261027T_seed_layers_v1/distance.svg) |
| Contact | Green markers for contact observations only | [`contact.svg`](../../../outputs/design/group_seed_evidence_layers/run_20261027T_seed_layers_v1/contact.svg) |
| Positive-area overlap | Magenta intersection areas when present; this seed has none | [`overlap.svg`](../../../outputs/design/group_seed_evidence_layers/run_20261027T_seed_layers_v1/overlap.svg) |
| Source/status audit | Same projected footprints with source, status, plane and coverage text | [`audit.svg`](../../../outputs/design/group_seed_evidence_layers/run_20261027T_seed_layers_v1/audit.svg) |

Every SVG uses the same plane-local real footprints and marks itself
diagnostic-only. The layers are separate views of the same seed; they are not
combined into a membership or strength score.

## Verification

Command:

```powershell
pixi run python -m py_compile scripts/design/group_level/render_seed_evidence_layers.py
pixi run python -m scripts.design.group_level.render_seed_evidence_layers
```

The renderer self-checks the 36 relations, writes four layer files, and parses
each SVG with the standard XML parser. The output manifest records the source
fingerprint, plane, seed, scope count and layer mapping.
