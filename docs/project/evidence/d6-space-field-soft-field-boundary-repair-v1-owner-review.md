# D6 soft-field boundary repair v1 · owner-facing visual review

Review gate: **STOP FOR SOFT-FIELD OWNER VISUAL REVIEW**<br>
Source: `live-rhino-10500-furniture-groups.ifc`<br>
Frame: **provisional diagnostic frame** · **not owner-confirmed**

The visual bundle keeps the walls and furniture context visible, labels all exact authored nodes as `furniture_group analysis node`, and labels non-node products as `context/reference only`. Orange column markers are eligible physical `IfcColumn` geometry. The boundary view distinguishes wall enclosure evidence, column internal obstacle boundaries, and the purple `column-line separation clue · virtual separation not selected` overlay.

Owner should inspect these files in order:

1. `outputs/design/space_field_soft_field_experiment/repair_v1/before_after_comparison.png` — preserved furniture-only baseline overlaid with repaired walls + columns + furniture occupancy.
2. `outputs/design/space_field_soft_field_experiment/repair_v1/boundary_evidence.png` — wall/column reuse and unselected column-line clue.
3. `outputs/design/space_field_soft_field_experiment/repair_v1/soft_field_diagnostic.png` — continuous furniture-group support field.
4. `outputs/design/space_field_soft_field_experiment/repair_v1/empty_space_diagnostic.png` — independent `empty_space_field` evidence.
5. `hard_1_regions.png` through `hard_4_regions.png` — discrete candidate overlays against the same physical context.

Current visual reading for owner confirmation:

- The upper-left compact band is supported by an exact zero-gap contact component of four groups (`G06`, `G11`, `G20`, `G27`) and a visibly continuous local field. This supports local sub-field evidence while leaving its semantic interpretation open.
- Lower-left and lower-right clusters do not show a unique physical boundary. Their repeated contact-pair pattern and the unselected column-line profile support treating them as layout variation until an owner identifies a meaningful separation.
- The repaired empty-space view describes physical occupancy and continuity. The five after-components are a bounded complement result from real wall/column/furniture geometry, not route, corridor, activity, visibility, or walkability truth.
- The 1/2/3/4 hard overlays remain ranked discrete views. The 3-region view is still the weakest owner interpretation because it isolates two desk/chair groups without a stronger continuous or physical boundary.

Please decide whether the next experiment should keep the upper-left local sub-field as a review hypothesis, and whether any lower-left or lower-right visual distinction has an owner-supported explanation. This record deliberately does not choose a final domain, region count, threshold, algorithm, or production selector.

The current Blender file was not opened or saved by this repair. The Blender identity and IFC path shown in the source record were observed previously; only the portable background Blender was used for disposable renders.
