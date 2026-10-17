# B3 stage-4 source qualification

Date: 2026-10-08. This is bounded source reconnaissance for the exploratory B3 route. It does not select a production slice, threshold, tolerance, body size, or public API.

## Inspection basis

- Read-only serialized inputs: `outputs/design/d6_b4_live_blender/run_001/live_request.json` and `live_result.json`.
- Read-only source: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` and its inspection/export summaries.
- Live MCP inspection on 2026-10-08: `get_addon_status`, `get_scene_info`, and read-only `execute_blender_code` queries for scene identity, IFC inventory, representations, roles, slab levels, selection, and panel state. The approved executable was verified as `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` (Blender 5.2.0 LTS).
- The live MCP addon is protocol 9 while protocol 13 is expected; the read-only status and scene queries still completed. No update, operator, selection, overlay, save, or source mutation was performed.

## Domain and frame

The historical B4 capture contains five structural candidates. At the displayed 10 mm2 residual tolerance, S3 is recorded as **206.520923482 m2 with two structural holes**. `live_result.json` records `attempt.status=accepted`, `current.status=active`, and the S3 candidate identity. The later evidence note records a human-confirmed live S3 acceptance, while preserving the earlier frozen S1/A11/A12 refusals. Those are historical acceptance records, not a current live-state claim.

The current read-only MCP scene has no loaded B4 panel `STATE`, no selected object, no active object, and no B4 diagnostic overlay objects. Therefore current active/accepted S3 state is **not independently verified in this inspection**; this does not invalidate the historical human S3 acceptance. With its outline/holes and source/frame revision verified, that acceptance can support a snapshot-only planar B3 experiment carrying an explicit historical/snapshot label. The current scene is a 372-object IFC-linked `Scene`; MCP reports `dirty=false` and an empty blend path, which differs from the historical note's dirty/unsaved observation. Treat the current MCP observation and historical B4 record as separate revisions.

The B4 frame is explicit and must remain separate from B3 query policy:

- B4 scope/frame: world XY, origin/datum `z=0`, enclosure cut `1.5 m`, metre analysis units, default-closed doors/windows scenario. The `z=0` datum was a B4 task assumption, not an observed floor datum.
- B3 exploratory query/reference: configurable human-general eye-height reference above the human-confirmed Level 1 floor-top datum at world `z=0 m`; the default offset `1.6 m` remains provisional and resolves to world query `z=1.6 m`. It must not regenerate or invalidate the confirmed horizontal S3 scope solely because its query height differs.
- Reuse qualification: a future B3 field may reuse the confirmed S3 horizontal outline and its source/frame provenance, while carrying a distinct eye-height query record. The selected planar S3 outline does **not** establish a qualified 3D vertical extent for the domain.

S3 is an inferred structural enclosure from the B4 capture, not an IFC `IfcSpatialElement` domain. The IFC adapter only creates an analysis domain when an explicit spatial element is selected; no such selection is present in the captured B4 handoff. A current source/frame-qualified S3 horizontal scope can still support a planar B3 diagnostic field; lack of a qualified 3D domain extent limits volumetric claims and any dependent topology that requires such extent. It does not by itself invalidate a planar height-query diagnostic.

## Source identity, units, and frame

The observed identity tokens are IFC4 project GlobalId `2uGd6yom9GZe5$z7LfbGW0`, source path `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, serialized B4 `source_revision=e4f19cad8c7d0b6ca8e85fe5efcabbcf25ab8a619c54d938573ef9b8b0c64722`, frame id `04c8a31502b3ccf1cab94cd5b143cbe79da743c4b280d8c9f6d48ea442167ec8`, and request id `80153b2a3de0c8da18eab569c02b6ea47ed69e7aa5c1593c666be3f98aa9a44f`. The read-only live inventory query also produced a derived inventory identity hash `9c2a268fd3ef4bbbb93155c44828e6e04945feb91899ea6169c3351b07775c29`. These tokens are not a source-file hash and do not prove current geometry parity: the live query did not produce a new capture `source_revision` or compare all current meshes against the 38-record B4 capture. Current geometry revision/parity is therefore **unverified**, despite matching project/path IDs and observed counts. The live scene is metric with scale length `1.0`; the B4 capture declares metre coordinates and world transforms applied once. The IFC declares an SI length unit named `METRE` with `MILLI` prefix; the adapter preserves the source unit metadata and extracts world-coordinate analysis meshes in metres. These conversion and identity fields must remain in any B3 manifest.

The neutral IFC adapter's analysis frame is `ifc-world-plan`, origin `(0,0,0)`, orthonormal world XYZ basis, analysis units `m`, geometry/topology tolerances `1e-6`. The Blender snapshot adapter uses the same world XY basis and metre analysis units. This is frame-consistent for horizontal reuse; it is not evidence that `z=0` is the physical floor.

## Physical occupancy and context inventory

The B4 `live_request.json` is deliberately structure-only: its 38 objects are walls/columns/doors/windows and it supplies no furniture occupancy. It must not be used to claim an empty room or to qualify B3 furniture blocking.

The current linked IFC does contain actual object geometry and identities, independently inspected read-only:

- 95 `IfcFurniture` products are present in the IFC with GlobalId/STEP identity and `Body` plus `Analysis` representation declarations in the inspected inventory. This is representation/inventory evidence, not proof that all 95 Body and Analysis meshes were successfully extracted, closed, or manifold; the B4 capture successfully checked only its 38 structural mesh records.
- 27 `IfcFurnishingElement` products and 193 `IfcBuildingElementProxy` products are present with `Body` representation declarations in the inspected inventory; the focused query checked representation/role metadata, not successful mesh extraction for every record. Physical occupancy is factual mass geometry regardless of product class or known furniture role. `AnalysisParticipation` and semantic roles govern declared channel inclusion, not whether a mass exists. Excluded/context masses must remain in audit records, separate from analysis-domain support, helper geometry, and affordance geometry.
- 37 authored `IfcGroup` memberships and one `IfcGrid` with nine axes are present in the IFC. No `IfcOpeningElement` records are present.
- The IFC contains one `IfcSlab` (`IfcSlab/Slab`) with `Body` geometry and `OM_Layout` participation `exclude`. Its live mesh has world Z levels at approximately `0`, `-0.075`, `-0.15`, `-0.225`, and `-0.3 m`; this is geometry evidence, not an authored storey datum.

The source therefore has enough object identity and declared 3D representation coverage to continue a future occupancy extraction, but not enough checked extraction evidence to qualify every object as usable occupancy. The B4 structure capture and current S3 handoff do not provide a selected B3 occupancy set. Objective physical occupancy must be separated from analysis-domain support, helper geometry, and semantic affordance/context records while retaining excluded/context masses for audit. No affordance zones were qualified in this inspection.

## Floor datum policy and remaining qualification

The accepted B3 policy is to use the slab-linked IFC layer concept: the authoritative floor datum comes from the relevant `IfcBuildingStorey` elevation, with its IFC units and world-frame provenance carried into the query record. The narrow IFC inspection recorded these exact facts:

- `IfcBuildingStorey` STEP `#13`, GlobalId `2udSq8mkbQwxg0XrW$uM_r`, Name `Level 1`, `Elevation=None`, and `ObjectPlacement=None`.
- `IfcSlab` STEP `#4884`, GlobalId `2mbfCNlr9T48ZweNBN3dyn`, Name `Slab`, with `IfcLocalPlacement #6215` (`PlacementRelTo=None`) and `IfcAxis2Placement3D #6214`. Its local-to-world matrix has identity rotation and translation `(0, 4.3655745685100555e-11, -300)` in source units.
- The slab is contained by the storey through `IfcRelContainedInSpatialStructure` STEP `#3556490`, GlobalId `0Mk100p2HLI95wNlsiIwT1` (`RelatingStructure=#13`; `#4884` is a related element). This linkage is observed, not inferred.
- The IFC declares SI length unit `METRE` with prefix `MILLI`; `ifcopenshell.util.unit.calculate_unit_scale` returns `0.001` metres per source length unit. Thus the observed slab placement translation is approximately `(0, 0, -0.3 m)` in the world frame.

These facts were checked read-only against the named IFC using the existing Pixi environment and IfcOpenShell placement/unit utilities; no geometry extraction was required.

On 2026-10-08, the human explicitly confirmed: “标高是0米，标高基面在地板的上平面” (elevation is 0 m and the reference plane is the floor top surface). This supplied datum is bound to `IfcBuildingStorey #13` / GlobalId `2udSq8mkbQwxg0XrW$uM_r` (Level 1), with semantic reference `floor top surface`, units `m`, and analysis world `z=0`. Its qualification provenance is explicit human confirmation; it is not a populated authored IFC property or a geometry-derived fallback. The numeric datum is therefore resolved for analysis, and the provisional eye offset `1.6 m` resolves to world query `z=1.6 m`.

The source IFC still has `Elevation=None` and `ObjectPlacement=None` for this storey; no IFC write was performed. The slab placement and mesh Z levels remain geometry audit evidence only. No precedence is chosen between a future authored elevation and placement-derived evidence if they disagree; such disagreement remains for owner review. The human-confirmed datum does not resolve current source geometry parity, all-object extraction quality, or S3's 3D extent, and the historical horizontal S3 confirmation remains valid.

## Existing height-aware reuse and limits

Existing source-independent geometry helpers are sufficient for an exploratory height query when supplied qualified 3D meshes:

- `features.geometry_views.plan_projection(..., height_band=...)` clips triangles to a band and preserves components/holes where supported.
- `vertical_intervals_at`, `vertical_profile`, and `features.mass_patch_collection.vertical_intervals_at_collection` expose local occupied height intervals.
- `occlusion_intersections` and `collection_occludes` provide conservative ray/band occlusion evidence.
- `mass_patch_from_mesh` preserves 3D vertices, triangle topology, closure/manifold flags, units, and representation provenance. The IFC adapter separately extracts `Body` and `Analysis` representations and records their source linkage.

These APIs do not supply a qualified 3D S3 domain, a floor datum, anthropometric eye height, body envelope, sightline visibility, walkability, route width, or a production slice policy. Vertical interval pairing reports explicit uncertainty for open/non-manifold meshes and no interval; non-vertical query directions are unsupported. A full horizontal plan projection cannot substitute for a height-aware slice. Missingness must remain channel-local (`missing`/`unsupported`/`not_available`) rather than becoming an empty or zero occupancy field.

## Qualification outcome and user decisions

**Qualified for exploratory reuse:** observed source identity tokens, metre normalization, world-XY frame, historical S3 horizontal outline/holes, the explicit human-confirmed Level 1 floor-top datum at world `z=0 m`, and IFC inventory/representation provenance sufficient to continue qualification. Current geometry revision/parity and all-object extraction quality remain unverified.

**Not qualified:** a claim about the current live S3 selection, a populated authored IFC floor datum property, S3's 3D vertical extent, a selected furniture/object occupancy slice, affordance semantics, and any anthropometric or production height policy. The historical/snapshot S3 acceptance remains usable for the bounded planar experiment described above.

Owner decisions required before B3 field handoff:

1. Carry the resolved human-confirmed Level 1 datum (`0 m`, floor top surface, analysis world `z=0`, confirmation date 2026-10-08, storey GlobalId above) and observed `#3556490` slab containment relation into the B3 handoff; preserve the empty IFC properties and report any future placement/elevation disagreement for owner review.
2. Reobserve or re-confirm the current S3 handoff only if the claim concerns the current live selection; bind a newly observed source revision and frame because matching IDs/counts alone are insufficient. A snapshot-only planar experiment may use the historical acceptance with its explicit snapshot label.
3. Select and document which IFC roles/participation facts form objective occupancy versus excluded support/helper/context geometry; preserve per-object missingness.
4. Keep the B3 eye-height reference configurable and separate from B4's `cut_height_m=1.5` enclosure parameter; do not infer a 3D domain extent from the planar S3 polygon.

Verification: `git diff --check -- docs/project/evidence/b3-space-field-source-qualification.md` completed with no whitespace errors. No tests, JSON output, scene changes, or source writes were performed.

