# D6 trend substitute contract and legacy parity checkpoint

This design-only report compares A (`member_orientation_consensus`), C
(`area_weighted_total_covariance_pca`), D (`between_member_centroid_pca`), and
B/legacy on the same typed `Analysis` geometry. The parity JSON is
`outputs/design/trend_substitute_contract_parity/trend_substitute_contract_parity.json`.

## Accepted evidence

- The registry accepts only `consumer=trend`, `substitute_kind=MassPatch`, and
  `analysis_role=analysis_geometry_substitute` under `trend_analysis`.
- Every selected Analysis footprint carries `substitute_id`,
  `source_object_id`, the typed fields, `contract_key`, and provenance.
- Every real IFC parity record is validated against the registry and records an
  accepted `representation_identifier="Analysis"` result.
- The real IFC probe inventories 37 exact `IfcGroup.ObjectType ==
  "furniture_group"` groups and selects three complete Analysis groups using
  the existing deterministic source-id order. Twelve scanned groups remain
  skipped with their missing/invalid/partial reasons in the saved result.

## Legacy parity

The runner calls the unchanged `features.scene_inference._furniture_group_frame`
with members and extents reconstructed from the saved Analysis polygons. It
saves the legacy final `angle`, `strength`, and `basis` separately from
`geometry_angle`, `clarity`, and extents. When member support is positive, the
legacy final basis is `member_frame_consensus`; its point-cloud PCA is a
geometry diagnostic/fallback and is not a validation of C.

Angle equivalence is explicit: A frames use modulo 90 degrees; A axes, B, C,
D, and legacy axes use modulo 180 degrees. Raw values, including near-boundary
values such as 89.987 degrees, remain in the JSON.

## Real IFC coverage

The saved inventory contains all 37 exact furniture groups. Three groups with
complete Analysis footprints were selected for the smoke comparison; the
remaining skipped groups and their reasons remain serialized and are not
treated as zeros or repaired geometry.

## Visual audit

Portable Blender 5.2 rendered synthetic and real IFC panels from the saved
parity JSON and registry only. Manual inspection recorded visible Analysis
footprints, centers, A/C/D/B vectors, contract labels, and invalid/partial
states without clipping in the visual manifest.

## Provenance and limitations

Body geometry, object names, and labels never authorize trend input. The IFC
records preserve the source hash, `Analysis` representation identifier,
extraction method, visibility policy, and world-transform status. This is a
design sample, not a whole-model accuracy claim, psychological validity claim,
or production API decision. Invalid and partial states remain visible and do
not fall back to Body geometry. No winner is selected.

## Owner decisions required

The owner must decide whether C is the formal overall trend, whether A and D
remain separate descriptors, whether B remains legacy diagnostic only, and
whether the registry may move into production design.

STOP FOR TREND ESTIMAND REVIEW
