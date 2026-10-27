# Seed relation profile experiment v1

## Purpose and boundary

This is a diagnostic representation experiment for stage 2A of the group
attribution plan. It treats each real authored furniture group as a seed and
lists its relation to every other group in the frozen scope. It does not
choose a candidate, decide membership, compute participation, support,
potential, strength, closure, or a winner.

The experiment reads only the retained artifacts from the pinned IFC run; it
does not reload IFC, create a simulated layout, or add synthetic geometry.
The seed is a label for an organization view under discussion, not a new
production object or approved recipe.

## Run and verification

Command:

```powershell
pixi run python -m scripts.design.group_level.run_seed_candidate_profile_experiment
```

Output:

[`run_20261027T_seed_profile_v1`](../../../outputs/design/group_seed_candidate_experiment/run_20261027T_seed_profile_v1)

The retained source run is
[`run_20261027T165920Z_fb0d96`](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96).
Its IFC fingerprint is SHA-256
`1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`, and
the analysis plane is `ifc-world-plan` from the scene context.

The output self-check and external audit established:

| Check | Result |
| --- | ---: |
| Real seed groups | 37 |
| Unordered group relations | 666 |
| Relations per seed | 36 |
| Scope groups per seed | 37 |
| Seed profile JSON records | 37 |
| Plane-local seed SVG files | 37 |
| SVG XML parses successfully | 37 / 37 |
| Participation / strength formulas | `null` |
| Candidate closure | `not_evaluated` |

Every relation retains its source IDs, query plane, and source fingerprint.
Every seed view carries `participation_status: not_evaluated`, and every SVG
states that its lines show relative normalized-gap order only. The manifest
maps each seed view to one SVG.

## What the profile contains

For each seed-to-scope relation it records the existing geometry observations:
raw and normalized boundary-gap minimum/median/mean, contact and overlap
counts, raw status, source IDs, and the relative order by normalized-gap
minimum. The seed footprint and all scope footprints are drawn in the same
plane-local coordinates; line opacity encodes only that relative order.

## Limits and next decision

This run demonstrates that a seed-labelled view can carry a complete,
traceable scope profile for the current IFC. It does not establish that a seed
is a good candidate proposal rule, that distance has a selected participation
mapping, or that any profile statistic is a calibrated strength measure.
Unknown or unavailable gap states are not represented by this current all-
computed run and remain an uncovered branch. The next step is user review of
a few seed SVGs; formal recipe, participation, and strength decisions remain
blocked until that review and the remaining stage 2 gates are addressed.
