# D6 hard partition A/B/C column comparison

Date: 2026-10-03<br>
Status: diagnostic evidence only; stop at `STOP FOR COLUMN-AWARE HARD PARTITION REVIEW`<br>
Source: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`

## Question

This paired experiment compares the existing 37 authored `furniture_group` nodes under three views:

- A: `furniture-only hard partition` using the original `run_001/hard_candidate_alignment.json`;
- B: `wall-aware diagnostic` with physical wall boundary evidence attached to each existing cut;
- C: `wall-plus-column diagnostic` with the 16 eligible Level 1 `IfcColumn` obstacle profiles attached as a second evidence channel.

There is no owner-accepted boundary/obstacle-aware selector. B and C therefore preserve A's candidate structure and explicitly report selector effects as `deferred` / `not_computable`.

## Real IFC result

All four existing candidates keep the same region count, furniture-group membership, cut-edge set, and cut-edge ordering in A, B, and C:

| Candidate | A/B/C region count | Existing cuts | New/disappeared candidate | Cut sorting |
|---|---:|---:|---|---|
| 1 region | 1 / 1 / 1 | 0 | none / none | unchanged |
| 2 regions | 2 / 2 / 2 | 1 | none / none | unchanged |
| 3 regions | 3 / 3 / 3 | 2 | none / none | unchanged |
| 4 regions | 4 / 4 / 4 | 3 | none / none | unchanged |

Every candidate assigns each of the 37 authored groups exactly once. `ambiguous_group_ids`, `overlap_group_ids`, `unassigned_group_ids`, and singleton regions are recorded per variant in `real_ifc_comparison.json`; no authored membership changes.

The original cuts retain their furniture relation values and provenance. Their boundary gaps and relative ranks are:

| Cut | Boundary gap | Relative rank | Wall/column evidence |
|---|---:|---:|---|
| `0js6…` – `15Q2…` | 1.2914 m | 0.0857 | no exact wall or column segment intersection; profiles retained |
| `0Enn…` – `1Qmj…` | 1.4282 m | 0.0827 | no exact wall or column segment intersection; closest column profile retained |
| `02Ky…` – `1Ym1…` | 1.2544 m | 0.0752 | no exact wall or column segment intersection; closest wall and column profiles retained |

The wall-only and wall-plus-column views therefore add auditable physical evidence without replacing furniture pairwise relations. Relative distance profiles use ranks and exact intersections; no fixed metre cutoff is used. Column-line evidence remains a separate clue and `virtual separation not selected`.

The existing repair empty-space evidence changes from 355.8844 m² and one component to 326.5177 m² and five components after physical walls, eligible columns, and furniture geometry are combined. This is explicitly not a furniture region count.

The comparison render had a visual-only repair on 2026-10-03. Its region records retained membership but lacked closed display envelopes, so the first A/B/C PNGs showed only short cut segments. The regenerated `render_input.json` now carries convex-hull envelopes derived from the same indivisible furniture-group footprints. The A/B/C PNGs therefore recover the earlier closed outlines and translucent fills while keeping the envelope labeled display-only, provisional, and not owner-confirmed. This changes no hard candidate, membership, selector, or evidence result. The pre-repair PNGs and disposable blend are retained under `pre_envelope_render_20261003/`.

The required conclusion is:

`columns_affect_empty_space_but_not_furniture_hard_partition_under_current_recipe`

Under the current recipe, the hard partition still uses only furniture-group relations. A future boundary/obstacle-aware selector remains deferred; keeping the furniture relation graph and boundary/obstacle evidence graph separate is the current auditable choice.

## Synthetic fixtures

The fixture set covers isolated interior column, wall-edge column, three-column row, a column pair near a furniture-group gap, a row aligned with a wall, a row with an open gap, a different-level column, and invalid/missing column geometry.

Each fixture records A/B/C hard candidates, empty-space before/after, component counts, cut-edge change status, source provenance, virtual separation selection, and authored membership mutation. Every fixture keeps `furniture_membership_changed: false` and `virtual_separation_selected: false`. The different-level and missing-geometry cases contribute zero eligible column occupancy.

## Scope and validation

- The real IFC is read only; its SHA-256 is checked against repair v1.
- Existing `run_001` and `repair_v1` are reused and not overwritten.
- The full IFC geometry adapter is not rerun. The comparison consumes the already confirmed repair v1 wall/column projections.
- No production code, adapter, API, formal tests, dependency, source IFC, or user Blender file is modified.
- A disposable portable Blender render has 13 orthographic scenes: four A, four B, four C, and one all-cut overlay.
- The visual-envelope repair was reproduced in `tmp_reproduction_visual_repair_20261003/`; its four core JSON hashes match the repaired output.
- Default run, temporary-directory reproduction, JSON/schema/hash, PNG render/crop, blend readback, and scope audit passed.

STOP FOR COLUMN-AWARE HARD PARTITION REVIEW
