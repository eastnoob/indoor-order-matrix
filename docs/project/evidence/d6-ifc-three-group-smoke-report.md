# D6 real IFC three-group smoke report

Execution date: 2026-09-29. This is a read-only input, placement, descriptor, and display smoke check; it does not change the IFC, adapters, features, tests, NeutralSceneV2, public APIs, dependencies, or the Blender source model.

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

`NeutralSceneV2` was built directly from the serialized extraction and the group descriptor ran successfully. The planar analysis frame is IFC world XY in metres and explicit `Analysis` geometry is computed. Candidate views, group aggregation, space observations, Z compatibility, and 3D clearance remain explicitly deferred or unavailable. One group is marked `invalid` because one declared member has unsupported polygon holes; the excluded member and source mesh reference are preserved in the descriptor rather than silently treated as valid.

## Blender display artifact

The renderer consumed only `sample_scene.json`, `description.json`, and `inventory.json`. It used the required executable `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` (Blender 5.2.0 LTS). The saved artifact contains separate `D6_Source_Body`, `D6_Analysis_Terminal`, `D6_Analysis_Overlays`, and `D6_Source_Labels` collections, with seven Body meshes and seven Analysis meshes. The source and analysis PNGs are 1200×800 and nonuniform. Labels use compact display text while full source identities remain in object metadata and JSON; visual inspection found no frame-edge clipping after the renderer margin fix.

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
- Blender background render: exit 0; source and analysis renders plus `.blend` saved.
- `verify`: exit 0; source hash, IFC4 schema, three selected groups, deferred fields, and placement checks passed.
- Focused tests: `52 passed`.
- `git diff --check`: pass.

## Recommendation

**APPROVE** the real-IFC three-group input, unit, placement, provenance, serialization, and display smoke evidence. **DEFER** production decisions for candidate views, group aggregation, space assignment, Z/3D compatibility, and invalid-hole repair; this run intentionally leaves those fields explicit and unresolved.

STOP FOR THREE-GROUP IFC INPUT REVIEW
