# D6 real-IFC boundary-candidate comparison design experiment

- Date: 2026-10-04
- Status: bounded design experiment complete; owner review required
- Scope: comparison of retained real-IFC boundary candidates only
- Stop marker: `STOP FOR REAL IFC BOUNDARY CANDIDATE COMPARISON DESIGN REVIEW`

## Blockers

- The real IFC has no qualified authored `AnalysisDomain`. The source inventory has `IfcSpace=0`, `IfcSpatialZone=0`, and no `OM_AnalysisProxy` domain marker. No candidate is promoted to `AnalysisDomain`.
- The source has six `IfcDoor` objects but zero `IfcOpeningElement`, `IfcRelVoidsElement`, and `IfcRelFillsElement` records. Door geometry is therefore not treated as an opening, and door state is not inferred.
- The retained candidate set contains several plausible candidates. The source wall union has 13 disconnected components and the wall-plus-column union has 3. The experiment preserves that ambiguity and performs no merge, ranking, or winner selection.
- The comparison uses the existing serialized native IFC evidence. It does not claim a live adapter result or live Blender/MCP correspondence; the existing bounded adapter attempt did not produce a scene result.

## Important findings

The source file is IFC4 with millimetre length units serialized as metres in the evidence. The verified source file is 408,617,800 bytes with SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`. The retained inventory is 11 walls, 16 columns, 6 doors, 95 furniture members, and 37 exact furniture-group nodes on Level 1.

The independent diagnostics recomputed valid 2D polygon geometry for all eight candidates. Every candidate geometry is a single connected polygon, while the referenced source footprints remain multi-component in most candidate records. This distinction is recorded explicitly: candidate geometry was not silently merged, and the existing `multiple_components` flag remains diagnostic evidence rather than a frozen status enum.

The physical wall union is 23.754079 m² across 13 components. The wall-plus-column union is 29.514079 m² across 3 components. All 16 eligible columns remain physical occupancy. Exact boundary contact supports a column boundary-support role for two candidates: C05 uses one column and C08 uses ten columns. Other columns remain occupancy context only. Support references and occupancy-context references are separate fields in the diagnostics.

The disposable Blender scene was built only from serialized evidence with the approved portable executable. It contains 11 wall objects, 16 column objects, all eight candidate IDs, and the required legend. The SVG contains 35 geometry paths (27 physical source footprints and 8 candidate outlines) and all required labels. The PNG was inspected as a 2200 × 1400 image.

## Minor findings and limits

- A real-IFC centerline construction is unavailable from the retained extraction; no centerline is inferred from hulls or bounds.
- The analysis plane is a diagnostic world-XY projection. It is not a selected production plane or coordinate contract.
- The exact-contact, weld, area, and volume values are inherited diagnostic tolerances. They are not production thresholds.
- The visualization is disposable evidence. It does not open, move, rename, save, or claim correspondence with a user Blender file.

## Candidate-by-candidate comparison

All rows retain `candidate_status = provisional_diagnostic_only`, `units = m`, the diagnostic world-XY plane, source IDs, source roles, level, and provenance. `support columns` counts exact column boundary contacts; `occupancy columns` counts intersecting column footprints kept as physical context.

| ID | Exact candidate ID | Construction | Area (m²) | Source-ref components | Support columns | Occupancy columns | Diagnostic interpretation |
|---|---|---|---:|---:|---:|---:|---|
| C01 | `wall_only:outer_face:outer:04` | wall-only / outer face | 17.057034 | 4 | 0 | 4 | Valid single polygon; existing multi-component ambiguity retained |
| C02 | `wall_only:inner_face:inner:04:01` | wall-only / inner face | 4.802091 | 4 | 0 | 0 | Valid single polygon; source-reference union is multi-component |
| C03 | `wall_only:inner_face:inner:04:02` | wall-only / inner face | 6.172443 | 4 | 0 | 0 | Valid single polygon; source-reference union is multi-component |
| C04 | `wall_plus_column:outer_face:outer:01` | wall-plus-column / outer face | 251.520001 | 1 | 0 | 16 | Valid single polygon; covers the diagnostic physical union and remains unassigned |
| C05 | `column_assisted_closure:inner_face:inner:01:01` | column-assisted / inner face | 4.510466 | 3 | 1 | 1 | Exact column contact closes a diagnostic loop; remains provisional |
| C06 | `wall_plus_column:inner_face:inner:01:02` | wall-plus-column / inner face | 4.802091 | 4 | 0 | 0 | Valid single polygon; no column boundary-support contribution |
| C07 | `wall_plus_column:inner_face:inner:01:03` | wall-plus-column / inner face | 6.172443 | 4 | 0 | 0 | Valid single polygon; no column boundary-support contribution |
| C08 | `column_assisted_closure:inner_face:inner:01:04` | column-assisted / inner face | 207.240923 | 2 | 10 | 12 | Exact contact supports a larger diagnostic loop; all columns still occupancy |

The detailed records, including polygon coordinates, source wall IDs, source column IDs, roles, tolerances, bounds, union relations, validity, and provenance, are in [`candidate_comparison.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_comparison.json) and [`candidate_diagnostics.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_diagnostics.json).

## Candidate semantics

The experiment retains the existing `provisional_diagnostic_only` status. No candidate is an accepted room, formal AnalysisDomain, or production boundary. The candidate set has no selector and records `selection = none`. Disconnected or ambiguous evidence is retained as evidence. No disconnected components are merged.

Columns have two separate meanings. A column footprint is always physical occupancy. A column receives a boundary-support role only when the candidate boundary has exact geometric contact and the contact participates in a closed diagnostic loop. C05 and C08 meet that limited diagnostic condition. This role does not remove the column from occupancy and does not establish a room boundary.

## Ambiguity and status proposal (not frozen)

The separate [`candidate_status_proposal.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_status_proposal.json) proposes a future representation without changing production APIs:

- Keep `multiple_components` as a diagnostic fact. It may feed a future `ambiguous` status when several components or interpretations remain, but the relationship must be an owner decision.
- Represent several plausible candidates as one candidate-set record containing stable candidate IDs, shared source context, per-candidate diagnostics, and an explicit no-selection state. Retain every candidate rather than ranking or collapsing them.
- Distinguish `singleton` (one candidate in the set), `unassigned` (no authored or owner-confirmed association), `provisional` (automatic diagnostic evidence), and `user_confirmed` (explicit owner action tied to a stable ID). The names, aggregation rules, and lifecycle remain undecided.
- Keep the synthetic authored-boundary precedence fixture separate from real-IFC evidence. It demonstrates how a future authored boundary could take precedence while retaining automatic candidates as provenance; it does not freeze a selector.

Evidence already present includes stable candidate IDs, source roles, units, level, diagnostic plane, tolerances, `provisional_diagnostic_only`, `multiple_components`, and the absence of a qualified authored domain. Owner decisions remain the future enum names, candidate-set serialization, ambiguity aggregation, singleton/unassigned lifecycle, user confirmation semantics, and authored-domain precedence.

## Real IFC evidence versus synthetic control evidence

The real-IFC result is the eight-candidate set and the physical wall/column diagnostics. The real IFC has no qualified authored AnalysisDomain, so no authored precedence fact can be observed in that file.

[`synthetic_control_authored_precedence.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/synthetic_control_authored_precedence.json) is a deliberately separate control fixture. It contains two automatic provisional candidates and one explicitly user-confirmed authored curve to show a possible future precedence interaction. It is not real-IFC evidence, not a production selector, and not a change to the public contract.

## Verification

The experiment-specific verification passed:

- all 10 output JSON artifacts parsed;
- all eight candidate IDs were preserved exactly and matched the diagnostic records;
- all candidate geometries were valid single polygons;
- wall and wall-plus-column union relations, component counts, area, and bounds were recomputed;
- two exact column-assisted loop contributions were observed, with all columns retained as occupancy;
- SVG XML parsed with all required legend labels, candidate IDs, construction names, and 35 paths;
- the disposable `.blend` read back with 11 wall objects, 16 column objects, all eight candidate IDs, and required labels;
- a deterministic repeat into a temporary directory produced identical core JSON SHA-256 values;
- all 16 manifest entries had recomputed byte counts and SHA-256 values matching [`artifact_manifest.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/artifact_manifest.json);
- the bounded Git scope audit found no new production-scope status entries, and no `git add` or commit was performed.

## Next design gate

The evidence permits a later owner review of candidate precedence as a design-only step. It does not permit implementation of a production selector, formal domain promotion, free-space construction, connectivity, route, walkability, or a finalized ambiguity/status contract. Production implementation remains deferred.

Artifacts: [`candidate_comparison.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_comparison.json), [`candidate_diagnostics.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_diagnostics.json), [`candidate_status_proposal.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_status_proposal.json), [`candidate_comparison.svg`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_comparison.svg), [`candidate_comparison.png`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_comparison.png), [`candidate_comparison.blend`](../../../outputs/design/live_ifc_boundary_candidate_comparison/candidate_comparison.blend), [`verification_report.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/verification_report.json), and [`artifact_manifest.json`](../../../outputs/design/live_ifc_boundary_candidate_comparison/artifact_manifest.json).

STOP FOR REAL IFC BOUNDARY CANDIDATE COMPARISON DESIGN REVIEW
