# D6 B2 Real IFC Shadow Validation

- Date: **2026-10-07**
- Evidence class: **read-only real-IFC shadow diagnostic**
- B2 owner decision: **REVISE**
- Production implementation: **not approved**
- Result: **source verified; domain promotion refused**

## Source and method

The existing D6 input-mapping and boundary-candidate provenance records identify the same IFC path, byte count, schema, and SHA-256. The file's current fingerprint matches those records, so no alternative IFC path was selected:

- Path: outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc
- Size: 408,617,800 bytes
- SHA-256: 018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240

IfcOpenShell read the source directly under Pixi. Candidate polygon validity and source-footprint components were recomputed independently with Shapely from the matching serialized geometry snapshot. The existing boundary renderer and Blend readback helper were reused in a disposable run. Blender 5.2.0 LTS was invoked only from D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe; its scene was made from serialized evidence and did not open the IFC or a user Blender file.

## Inventory

The source is IFC4. Its length unit is millimetres (IfcSIUnit METRE with MILLI prefix; scale 0.001 to metres). Model representation contexts use three-dimensional Cartesian coordinates with world-coordinate origin [0, 0, 0]; the recorded true-north vector is [0, 1]. No IfcMapConversion is present. The one storey is **Level 1** (STEP #13, GlobalId 2udSq8mkbQwxg0XrW$uM_r), but its elevation is null and it has no object placement. The evidence therefore does not establish a vertical datum or production work plane. World XY is used only for the inherited diagnostic projection.

| IFC fact | Count |
|---|---:|
| IfcWall | 11 |
| IfcColumn | 16 |
| IfcDoor | 6 |
| IfcOpeningElement | 0 |
| IfcRelVoidsElement | 0 |
| IfcRelFillsElement | 0 |
| IfcSpace / IfcSpatialZone | 0 / 0 |

All inspected walls, columns, and doors are contained in Level 1. The inventory JSON preserves their STEP IDs, GlobalIds, names, representation presence, placements, and storey containment.

No qualified authored AnalysisDomain is available: there are no spaces, spatial zones, or explicit OM_AnalysisProxy domain markers. The 95 OM_AnalysisRepresentation records in the source inventory are furniture substitutes, not domains. Promotion is refused.

## B2 observations

- **Columns:** All 16 remain physical occupancy. In the diagnostic XY footprints, 20 wall-column footprint contact pairs span 14 columns. The saved candidate evidence and independent contact check distinguish contact from support: only two candidate-specific loop cases carry conditional support references—column_assisted_closure:inner_face:inner:01:01 (1 column) and column_assisted_closure:inner_face:inner:01:04 (10 columns). Five columns have no conditional loop-support reference. Contact or support does not turn a column into a wall.
- **Connectivity:** The planar wall union has 13 components; the wall-plus-column union has 3. The eight candidate polygons are valid single polygons, while their source-reference unions have component counts 4, 4, 4, 1, 3, 4, 4, 2. The validity and component observations were recomputed separately and match the retained candidate diagnostics. The two conditional support cases still have multi-component source-reference unions, so loop-support evidence does not establish overall source connectivity.
- **Doors and openings:** Six represented IfcDoor objects are present. They are not treated as openings, are not assumed closed, and have no inferred current state. The source has no opening element, void/host relation, or fill relation. Opening-host status is missing; opening geometry is not_available; malformed, conflicting, or unsupported relation status is not_verified because there is no relation or opening geometry to inspect. A closed-door scenario in prior design evidence is an unapplied assumption, not an IFC fact.
- **Candidate/domain state:** Eight candidates remain provisional_diagnostic_only; the set remains ambiguous. Candidate validity is not used to infer a room or domain. Domain promotion is refused; free-space, walkability, route, and clearance results were not computed.

The 1e-9 m boundary-contact length used for the independent planar comparison is the existing numerical diagnostic rule. It is not a production tolerance.

## Artifacts and validation

Artifacts are under [outputs/design/d6_b2_real_ifc_shadow_validation](../../../outputs/design/d6_b2_real_ifc_shadow_validation/). The diagnostic view visibly states **REAL IFC SHADOW DIAGNOSTIC**, **NOT PRODUCTION IMPLEMENTATION**, **NO DOMAIN PROMOTION**, and **NO FREE-SPACE OR WALKABILITY RESULT**.

- real_ifc_inventory.json — direct IFC facts and object identities.
- boundary_candidate_shadow_results.json — independent validity, contact, support, component, and refusal observations.
- candidate_comparison.svg, candidate_comparison.png, and disposable candidate_comparison.blend.
- blend_readback.json, provenance.json, validation_report.json, and artifact_manifest.json.
- The output folder also contains the bounded runner and the serialized evidence/helper inputs used by its render and readback.

Validation passed: all 9 output JSON files parsed; SVG/XML parsed with all four required labels; PNG decoded at 2200 × 1400; portable Blender readback matched 8 candidate IDs, 11 wall objects, 16 column objects, and the required scene labels. Candidate analysis JSON and a second Blender SVG render were byte-identical. The artifact manifest contains 14 entries and every listed byte count and SHA-256 was recomputed. The source IFC fingerprint remained unchanged.

The Git-scope comparison preserved all 44 pre-existing untracked entries; this evidence note is the only new status entry. The outputs directory is locally excluded and no files were staged or committed. Both diff whitespace checks passed, and the new text artifacts have no trailing whitespace.

No production code, adapter, NeutralSceneV2, API, formal test, dependency, source IFC, or user Blender file was modified. No selector, threshold, resolution, route width, space backend, or Bayesian/ML behavior was changed. This shadow validation does not prove production correctness and does not close B2.

Manifest SHA-256: 76e39781da78bd66c7f6a5bc60f841b22179f759f9d32c20560e23cb4a980e45

STOP FOR D6 REAL IFC B2 SHADOW VALIDATION REVIEW
