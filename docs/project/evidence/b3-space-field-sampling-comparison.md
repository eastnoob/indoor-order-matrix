# B3 stage-3 synthetic sampling comparison

Date: 2026-10-08. Outcome: bounded synthetic stage 1–3 diagnostic comparison complete; owner accepted its diagnostic evidence, including the 1/2/2 connector, 2/2/1 point-contact and directional reconstruction errors. No production resolution was selected; B3 remains open for real-source field/inspection and later decisions. Canonical evidence: `outputs/design/b3_space_field_exploratory/run_002/result.json` (schema v3). No production API, IFC, Blender scene, dependency, commit, push or merge changes. The accidental child's `outputs/design/b3_eye_height_baseline/run_001/result.json` is historical, unaccepted and unchanged; neither run_001 is overwritten.

## Reference and evidence contract

Twenty synthetic cases retain source ids/group identity, exterior/interior rings, absolute source z ranges, raw/clipped areas and height qualification. The datum is an explicitly authored synthetic storey-level fixture elevation, default 0.0 m, with source role, units and frame; it is not an actual IFC datum or a geometric slab inference. Eye offset defaults to 1.6 m and total comparison-band thickness to 0.10 m. Function/CLI configuration resolves offsets from the datum. Lower/eye/overhead observations and XY support frame remain distinct. Custom queries retain custom roles. Missing numeric datum is rejected, while explicit zero is valid.

The plane retains the experimental strict vertical-interior condition `z_min < plane_z < z_max`, excluding exact top/bottom faces. XY point masks use `covers`, including lateral boundaries. This is not closed-solid exact slicing. Every query/variant retains both plane and positive-overlap-band masks, occupancy clearances/statuses, domain mask/boundary clearance and physical-distance Gaussian support in complete shared-coordinate samples. Unrequested planes are null rather than empty. Bandwidth is fixed at 2.0 m; Gaussian support is not probability or evidence fusion. Boundary clearance includes exterior and hole boundaries; occupancy clearance preserves the existing raw qualifying-mass target, including outside-domain sources. These parallel diagnostics are not visibility, routes or walkability.

Each case has six comparisons: spacings 1.0, 0.5, 0.25 m (short domain bounding extent /8, /16, /32), each with origins zero and quarter-spacing shifted. Valid cases retain 80, 320 and 1280 point samples per respective variant, including masked-out hole points. Integer cell indices define adjacency; an additional test proves a 0.75 m origin includes centers at 0.25 m with negative indices. Shapely floating-point vector components count only positive-area polygon interiors. Four-neighbor and unrestricted eight-neighbor adjacency are reported independently; no corner-cut filter is hidden.

## Expected versus observed geometry

At 1 m spacing and zero origin, component tuples are `(vector, sampled4, sampled8)`. Areas below are rounded for reading; JSON retains floating-point results.

| Fixture | Expected and observed tuple | Vector occupied/free area m² | Comparison consequence |
| --- | --- | --- | --- |
| Real 0.6 m connecting passage | (1, 2, 2) | 18.8 / 61.2 | Coarse points miss the connector; shifted 1 m and every finer variant give (1, 1, 1). |
| Exact closed passage | (2, 2, 2) | 20 / 60 | Full divider is closed; all six tuples agree. |
| Edge-touch divider halves | (2, 2, 2) | 20 / 60 | Touching obstacle edges close the divider; no zero-width free connection. |
| Point-touch diagonal quadrants | (2, 2, 1) | 40 / 40 | Open free interiors remain separate; unrestricted diagonal adjacency joins sampled components at every variant. |
| Disconnected pockets | (2, 2, 2) | 72 / 8 | Two positive-area free pockets; source occupancy retains both interior rings. |
| Historical narrow-gap strips | (3, 2, 2) | 27.2 / 52.8 | This fixture has three strips, not a connector; shifted/finer variants give (3, 3, 3). |
| Domain hole and outside mass | (1, 1, 1) | 0 clipped / 76 free | Domain area 76; raw mass area 5 is entirely outside the domain (4 in the hole, 1 beyond bounds). |

Empty and fully occupied fixtures give (1,1,1) and (0,0,0). Overhang support/canopy share source identity while lower/eye/overhead areas are 1/0/9 m². Eye-face-contact has band area 8 m² and plane area 0: shared-coordinate mask disagreements are 8,8,32,32,128,128 across the six variants. This demonstrates the preserved experimental face convention without changing it.

Point-center area estimates are non-conservative. Reconstructed center-labeled occupied cells are clipped to the exact domain including holes and are diagnostic only; samples remain the primary discrete output. For the shifted 1 m vertical-obstacle case, signed point occupancy area error is 0, but false-free and false-occupied reconstructed areas are each 1.4375 m², symmetric difference 2.875 m². This balanced error would be hidden by totals. The same shifted lattice leaves 4.4375 m² of domain without reconstructed cells; smaller shifted spacings leave 2.234375 and 1.12109375 m². The artifact reports this explicitly rather than implying coverage. Every observation/variant records all three geometric errors, signed area errors, clearance summaries and component discrepancies. Agreement of component counts is only an observation; no passed stability threshold is asserted.

Missing domain/obstacles are `not_available`; missing groups are `partial`, suppressing only Gaussian support. Invalid geometry, nonfinite heights and nonfinite groups are `invalid` with null fields, never known-empty. Valid empty sources retain `known_empty` clearance status and null distance.

## Validation and scope

Final commands from repository root:

```powershell
pixi run pytest test/test_b3_space_field_exploratory.py -q
pixi run python scripts/design/space_field/run_b3_space_field_exploratory.py --output outputs/design/b3_space_field_exploratory/run_002/result.json
```

Both exit 0; the final-tree focused suite passed 22 tests in 22.59 s. `pixi run python -` strict validation exits 0 after parsing with rejection of NaN/Infinity and duplicate keys, redumping with `allow_nan=False`, and checking all twenty cases have six variants; the artifact is 53,101,683 bytes. A second read-only `pixi run python -` inspects the table, plane-band disagreements, reconstruction errors, overhang areas and clearance summaries; exit 0. Earlier focused validation found one obsolete assertion expecting missing groups to suppress the entire result (1 failed, 10 passed, exit 1); correcting it to `partial` restored the intended channel-local contract. Subsequent focused validations passed 21 and then 22 cases.

Focused whitespace/docstring audit via `pixi run python -` checked all five owned text paths and found no issues; all 18 runner functions and 17 test functions have docstrings. `git diff --check` exits 0 for the owned paths, with the Python scan covering their untracked contents. Scope inspection via `git status --short` records existing unrelated dirty files without touching them. Owned writes are only the canonical runner, focused test, two B3 design docs, this note and `run_002/result.json`. The latest human datum confirmation changed prose only; synthetic code and result were unchanged. No full pytest or Blender execution was requested or performed.

## Remaining owner work

No exact-section or clearance semantic change was made; no additional consequential design ruling is requested by this package. Connectivity discrepancies block the affected stability claims. Final query policy, resolution, stability criteria and production handoff remain undecided. The [separate source qualification](b3-space-field-source-qualification.md) records storey #13 with both Elevation and ObjectPlacement missing, slab #4884 containment relation #3556490, and unit scale 0.001 m/source unit. The human-confirmed analysis datum binds 0.0 m and the floor-top reference plane to that storey, so the default 1.6 m eye offset resolves to analysis world z=1.6 m; no source property was populated or changed. Slab placement -0.3 m and mesh top near 0 are audit only. Current source geometry parity, all-object extraction quality, selected occupancy, and S3 vertical extent remain unresolved. Existing historical S3 horizontal scope is not regenerated or reconfirmed by these synthetic eye queries. No real-source field is generated here.
