# D6 real IFC three-group smoke report

Execution date: 2026-09-30 (corrective rerun). This is a read-only input, placement, descriptor, and display smoke check; it does not change the IFC, adapters, features, tests, NeutralSceneV2, public APIs, dependencies, or the Blender source model.

## Source and selection

The source is `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` (IFC4, 408,617,800 bytes, SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`). The inventory found 358 `IfcProduct`, 37 `IfcGroup`, and 37 groups with the exact `ObjectType` value `furniture_group`. Units are explicitly millimetres with scale `0.001` to metres.

The frozen policy selected the first three non-empty exact-role groups sorted by source identity:

| Group | Name | Members |
| --- | --- | ---: |
| `ifc-group:0$9EwHOwDKmu25$icFA5wm` | `2CozyChairsWithTable` | 3 |
| `ifc-group:02Kyw_DsPG5BC3j07wct$4` | `1CozyChairAndTable` | 2 |
| `ifc-group:0AG_FU1oHHxh9s_mH9GMgP` | `1CozyChairAndTable` | 2 |

Selective extraction produced seven unique members. Every selected member has one computed `Body` mesh and one computed `Analysis` mesh. No full-room loader or context tessellation was used.

## Placement and descriptor observations

One `Analysis` member per selected group was checked independently against the IFC local geometry plus placement matrix. All three checks passed with `max_abs_vertex_error_m = 0.0` and matching vertex counts.

`NeutralSceneV2` was built directly from the selective extraction and the group descriptor ran. The planar analysis frame is IFC world XY in metres, and all seven `Analysis` meshes were extracted. **All three selected groups have `geometry_status=invalid`**: each contains one declared member excluded from planar group geometry because of `unsupported_holes`. The excluded member and its source mesh reference remain in `description.json`.

| Group | Geometry status | Usable / declared | Excluded member (`unsupported_holes`) |
| --- | --- | ---: | --- |
| `G1` | `invalid` | 2 / 3 | `ifc-object:3hQEaFtvjG092HW56vRYCV` |
| `G2` | `invalid` | 1 / 2 | `ifc-object:1acyT4JwbKp9$NF3I5PN6A` |
| `G3` | `invalid` | 1 / 2 | `ifc-object:0UGldJHiXIFAJg6rXLNAXO` |

The reported `group_frame` and `group_axis` angles use only those usable members. They are **partial diagnostic directions**, not a complete group trend, formal aggregation, or inferred group result. In particular, the single-member directions for `G2` and `G3` cannot establish agreement across their declared groups. Candidate views and aggregation remain `deferred`; space, Z compatibility, and 3D clearance remain unavailable.

## Blender display artifact

The renderer consumed only `sample_scene.json`, `description.json`, and `inventory.json`; it did not recalculate descriptor metrics. It used the required executable `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` (Blender 5.2.0 LTS). The saved artifact has separate `D6_Source_Body`, `D6_Analysis_Terminal`, `D6_Analysis_Overlays`, `D6_Source_Labels`, and `D6_Analysis_Labels` collections, with seven Body meshes and seven Analysis meshes. The analysis overlay keeps footprint, center, group-frame, and group-axis roles distinct; its two direction roles are tagged `partial_usable_members_only`.

Both PNGs are 1200×800 and nonuniform. `source_sample.png` shows gray IFC Body meshes; `analysis_sample.png` shows blue IFC Analysis meshes with display-only green footprints, yellow centers, orange group frames, and red group axes. These colors and glyphs are not additional calculations. `G1`–`G3` follow the table order above, while compact member keys such as `1a` follow `inventory.json` member order. Complete IFC source identities remain in object metadata and JSON. The corrected orthographic framing checked all geometry and label bounds in normalized image coordinates (`x=0.323–0.677`, `y=0.115–0.885`); visual inspection confirms the bottom furniture is fully visible and the analysis labels are separated.

Artifacts:

- `outputs/design/ifc_three_group_smoke/source_sample.png`
- `outputs/design/ifc_three_group_smoke/analysis_sample.png`
- `outputs/design/ifc_three_group_smoke/three_group_smoke.blend`
- `outputs/design/ifc_three_group_smoke/inventory.json`
- `outputs/design/ifc_three_group_smoke/sample_scene.json`
- `outputs/design/ifc_three_group_smoke/description.json`
- `outputs/design/ifc_three_group_smoke/audit.json`

## Verification

- `self-check`: pass.
- `inventory` and selective `probe`: pass; source hash was rechecked before probing.
- Blender 5.2 portable background render with `--python-exit-code 1`: exit 0; source and analysis renders plus `.blend` saved; camera bounds check passed.
- `verify`: exit 0; source hash, IFC4 schema, three selected groups, deferred fields, and placement checks passed.
- Focused tests: `52 passed`.
- `git diff --check`: pass.

## Recommendation

**ACCEPT** the real-IFC three-group input, unit, placement, provenance, serialization, and display smoke evidence. **DEFER** complete group geometry and direction claims until `unsupported_holes` is handled and rerun; defer candidate views, formal aggregation, inferred grouping, space assignment, selector, Z/3D compatibility, and Bayesian/ML work. No production grouping policy is selected by this smoke check.

STOP FOR THREE-GROUP IFC INPUT REVIEW
