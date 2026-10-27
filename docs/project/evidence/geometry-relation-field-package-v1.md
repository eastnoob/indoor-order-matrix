# Geometry relation evidence package v1

## Scope

This package is the first evidence package in the group-attribution field. It
reads only the pinned IFC source and exposes one furniture-group pair as the
public target. The existing authored-group member-pair observations remain in
the envelope for replay and provenance, but are explicitly `audit_only` until
a reviewed group-level aggregation rule exists. The package is diagnostic
evidence: it does not decide membership, support, potential, strength,
candidate selection, or a winner.

The source boundary is `IfcGroup.ObjectType == "furniture_group"`. Group and
member identities, Body geometry, IFC placement, source units, analysis frame,
tolerance, and source references remain auditable. The adapter converts source
geometry once and projects it to `scene.context.analysis_plane`. The user's
2026-10-27 decision is to use the current IFC world-XY plane temporarily.
Neither the evidence package nor the renderer fixes that basis: queries must
match the scene plane, and drawing uses its local coordinates. A future camera
plane must enter through the same scene context; camera integration is outside
this slice.

## Input and output

`features/group_geometry_relation_field.py` exposes
`build_group_geometry_relation_envelopes`. It emits one immutable
`FieldResultEnvelope` for every stable unordered authored-group pair. The
target ID is a compact JSON array of the adapter's canonical `ifc-group:<id>`
identities, so input order cannot change the result.

Each envelope contains three descriptive channels:

- `boundary_gap`: raw and area-normalized member-pair boundary gaps;
- `contact`: tolerance-based contact observations;
- `positive_area_overlap`: overlap flag and positive intersection area.

Every channel retains member-pair status, reason, witness, source references,
units, and provenance. The channel observation also states
`group_pair_aggregation.status = deferred` and
`member_pairs_role = audit_only`. Missing or invalid geometry stays
unavailable or invalid. Shared-member dependency stays diagnostic metadata.
Historical semantic/neighborhood relation inventory is recorded in provenance;
position-grammar and column-grid evidence remain separate domains. The
envelope has no `field_projection` and no support value.

## Shared field boundary

The package uses `FieldQuery`, `EvidenceChannelRecord`,
`FieldResultEnvelope`, and `build_field_result_cache_identity` from
`features/field_core.py`. The core owns freezing, validation, status handling,
provenance, and cache identity; geometry rules remain in the existing group
description path. This keeps later evidence packages replaceable without
adding a second field kernel.

## Current verification and limits

The 2026-10-27 delivery completes implementation-plan items 1B.4 and 1B.6 for
the states present in the pinned IFC. On 2026-10-27 the user accepted the
overview, separated-pair and contact review scope with “合理”. This closes
the sample-view review gate, not the uncovered-state or strength questions.
Next comes clarification of evidence use and rules in stage 2; the complete
candidate-by-unit attribution field, strength and further evidence packages
remain pending.

The [source manifest](group-attribution-ifc-source-manifest.json) records
`outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`:
408618044 bytes, SHA-256
`1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`, IFC4,
project GlobalId `2uGd6yom9GZe5$z7LfbGW0`. Before/after hashes and independent
artifact review agree. Source millimetres are converted to analysis metres
once. The current plane is `ifc-world-plan`, origin `[0,0,0]`, identity basis.

| Observation | This IFC run |
| --- | ---: |
| Eligible authored furniture groups / members | 37 / 95 |
| Unordered group pairs / computed envelopes | 666 / 666 |
| Cross-group member pairs / computed observations | 4386 / 4386 |
| Member pairs with positive gap / contact / positive area overlap | 4370 / 16 / 0 |
| Group pairs with some positive gap / some contact | 666 / 16 |
| Shared-member dependency group pairs | 0 |
| Group pairs with traceable source references | 666 |

Group-pair relation types are not exclusive: a group pair can contain both a
contacting member pair and other separated member pairs. These counts are
geometric observations only.

The [run directory](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96)
contains `envelopes.json`, `plan_geometry.json`, `report.json`, and one JSON/SVG
per pair. The [view manifest](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/view_manifest.json)
maps all 666 envelope IDs to their pair files; all 667 SVG files, including the
overview, parsed successfully. Every pair is marked diagnostic-only and
retains its source, plane, units and status. Drawing uses this run's local
polygons and holes; it neither reloads IFC nor reprojects meshes.

Visual review passed for the [overview](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/overview.png),
[nearest separated pair](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/nearest_separated_pair.png),
[farthest separated pair](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/farthest_separated_pair.png)
and [actual contact pair](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/contact_pair.png).
All pair files received structural/manifest checks; the PNG samples received
visual review. The [artifact validation record](../../../outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/artifact_validation.json)
records these checks, verification mode and uncovered states.

Verification history is retained rather than counting failed outer commands
as passes:

- The initial envelope contract test passed independently:
  `pixi run pytest test/test_group_geometry_relation_field.py -q`,
  `1 passed in 1441.70s`. This predates the expanded audit/report assertions.
- The expanded `-q -s` run failed after 1193.51s because the test compared
  frozen tuple member IDs with the original list. The test now compares the
  status and member-ID contents separately.
- The next `-q -s --pdb` run found a second test error: the public description
  filters private `_tolerances`. The test now reads
  `scene.context.geometry_tolerance`. That outer run still ended with
  `1 failed in 1356.70s` and is not passing evidence.
- Its retained real IFC scene and description were reused in the debugger.
  After reloading the corrected test, the loader/descriptor were patched only
  to return those same real objects. The nested corrected pytest run passed:
  `1 passed in 5.88s`, exit code 0. It checked the complete pair/channel/source
  mapping and report files, replayed envelope values/cache identities from
  the same description, and recomputed forward/reverse geometry for one
  computed member pair per group pair (666 samples). This is real-result
  replay, not an independent second geometry extraction or a full rerun
  determinism claim.

Positive area overlap, shared members, missing/invalid geometry and
partial/unavailable results did not occur in this IFC and remain **not
covered**, including their state propagation. No simulated geometry was added
to fill those gaps. Only the current world-XY plane was verified; camera
integration and end-to-end verification of other planes remain pending.
