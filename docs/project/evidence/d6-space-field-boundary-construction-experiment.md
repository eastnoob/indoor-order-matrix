# D6 AnalysisDomain boundary construction bounded experiment

- Date: 2026-10-02
- Status: bounded design experiment complete; owner review required
- Scope: boundary construction evidence only
- Stop marker: `STOP FOR BOUNDARY CONSTRUCTION DESIGN REVIEW`

## Question and boundary

This experiment asks how an AnalysisDomain boundary can be constructed while
keeping the physical wall field and wall thickness as separate evidence. It
does not select a production boundary backend and does not compute free-space,
connectivity, routes, walkability, visibility, or space roles.

The four constructions are compared on the same controlled fixture:

1. inner wall face;
2. outer wall face;
3. wall centerline;
4. user-authored closed curve.

The construction unit is one rectangular wall shell with ordered centerline
segments `(0,0)–(8,0)–(8,6)–(0,6)–(0,0)`, wall thickness `0.20 m`, analysis
plane `fixture-world-plan-z=0`, and units `m`. One door opening is attached to
`wall-s`; `closed_by_assumption` is a scenario label and is not an IFC door
state.

The fixture stores these records independently for every candidate:

- `scope_enclosure_geometry`;
- `physical_wall_field_geometry` with `wall_thickness`;
- `opening_host_evidence`;
- `source_refs` and `candidate_refs`;
- `analysis_plane`, `units`, and `closure_scenario`;
- `status`, `provenance`, `user_confirmed`, `accepted`, and `diagnostic_only`.

The wall field is represented by separate rectangular wall polygons. The
candidate boundary is never written back into the source wall geometry.

## Design and evidence discipline

The controlled fixture is a fixed repeated-measures comparison: all four
constructions use the same walls, opening evidence, plane, units, and source
references. No absolute threshold, route width, mesh resolution, or perceptual
cutoff is used. The derived quantities are geometry relations, closure,
component count, area, perimeter, and explicit offset from the wall centerline.

The topology variants propagate evidence states without choosing a production
repair rule:

- `automatic_closed_wall_shell`;
- `multi_shell_conflict`;
- `open_boundary`;
- `cross_floor`.

Automatic constructions remain `user_confirmed=false` and `accepted=false`.
The authored curve is explicit and confirmed in the fixture so precedence can
be observed without changing a production selector.

Skills actually used: `experimental-design`,
`scientific-critical-thinking`, `scientific-visualization`,
`verification-before-completion`, and `stop-that-shit review`. The first three
were read from `.agents/skills/`; the verification skill was read from the
installed `superpowers` skill package; the review skill was read from the
installed `stop-that-shit` plugin. No requested skill was missing.

Skill reference: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M.
(2026). *Scientific Agent Skills: A Library of Procedural Knowledge for
Research Agents*. arXiv:2609.00065.

## Blender and real IFC observation

The current Blender UI was not observable through the available computer-use
inventory: `cua.getState()` returned no Blender application. The evidence
therefore records `current_blender_not_observed` and uses the real IFC file as
a read-only fallback. No current Blender object was moved, renamed, deleted,
saved, or overwritten.

The real IFC shadow inventory is
`outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`:

- schema: `IFC4`;
- units: `IfcSIUnit`, `LENGTHUNIT`, `METRE`, prefix `MILLI`;
- objects: 11 `IfcWall`, 1 `IfcSlab`, 6 `IfcDoor`, 95 `IfcFurniture`, 37
  `IfcGroup`, 1 `IfcBuildingStorey`;
- `IfcSpace=0`, `IfcOpeningElement=0`, `IfcRelVoidsElement=0`, and
  `IfcRelFillsElement=0`;
- placement evidence: 355 of 358 `IfcProduct` entities have
  `ObjectPlacement`; 354 have a representation;
- analysis plane, wall shell closure, and all four candidate constructions:
  `not_verified` because this shadow pass intentionally uses native inventory
  only and does not run the full geometry adapter;
- door state: not inferred from inventory.

## Results

| Candidate | Area (m²) | Wall-field relation | Status | User confirmed | Accepted |
|---|---:|---|---|---|---|
| inner wall face | 45.240 | touches inner edge of physical wall field | computed | false | false |
| outer wall face | 50.840 | touches outer edge of physical wall field | computed | false | false |
| wall centerline | 48.000 | passes through physical wall field | computed | false | false |
| authored closed curve | 39.960 | inside inner face without wall-field overlap | computed | true | true |

The two wall faces retain wall thickness because the physical wall field is
saved separately. The centerline is a useful source/reference construction but
it passes through the physical wall field, so it cannot be treated as an
interior occupancy-free boundary by this experiment. The authored curve is an
explicit user input and is the only candidate marked accepted in the controlled
precedence demonstration.

State propagation is:

- one connected closed shell: automatic inner/outer/centerline candidates are
  `computed` and provisional;
- multiple closed shells: all automatic candidates are `ambiguous` and
  diagnostic-only;
- open or disconnected boundary: all automatic candidates are `partial` and
  diagnostic-only;
- mixed levels: all automatic candidates are `invalid` with
  `cross_floor_or_analysis_plane_conflict`;
- no authored curve in those variants: authored candidate is
  `not_available`.

## Answers to the required questions

1. The inner and outer faces differ from the centerline by the recorded half
   wall thickness; their areas are 45.240, 50.840, and 48.000 m². The authored
   curve is independently specified and has area 39.960 m².
2. Inner and outer faces preserve the wall thickness in the physical field and
   remain on its corresponding side. The centerline crosses the field. The
   authored curve remains separate and does not overlap the field in this
   fixture.
3. In the real IFC, none of the four constructions is promoted to a generated
   candidate: all remain `not_verified`. Native inventory confirms source,
   schema, units, placement counts, walls, doors, furniture, and groups only.
4. A single connected closed shell may be exposed as a provisional automatic
   candidate, but it must remain unconfirmed and unaccepted. It is not a real
   room or a frozen AnalysisDomain backend.
5. A user-authored closed curve has higher experimental precedence, is selected
   in the controlled case, and suppresses automatic selection while retaining
   automatic candidates as provenance.
6. Multi-shell, open-boundary, and cross-floor evidence propagates as
   `ambiguous`, `partial`, and `invalid`; no silent repair or fallback is
   performed. Missing authored geometry is `not_available`.
7. Future UI hover/accept/edit contract must expose candidate id and source
   kind, source/candidate refs, wall refs and thickness, opening/host evidence,
   analysis plane and units, closure scenario, status/evidence status,
   provenance, uncertainty, and `user_confirmed`/`accepted`/`diagnostic_only`.
   Accept/reject must be explicit; edit/redraw and split/merge must preserve
   source geometry and prior candidate provenance.
8. Owner decisions remain: production boundary construction, whether inner or
   outer face is the default view, how partial/ambiguous candidates aggregate,
   accepted-candidate lifecycle, multi-floor and opening semantics, and the
   gate into free-space design.

## Next-stage gate

This evidence supports a limited provisional-candidate design. It does not
authorize free-space design. Owner review must decide boundary construction and
candidate lifecycle before any free-space backend, mesh/polygon choice,
resolution, route width, or threshold is proposed.

Artifacts:

- [boundary_comparison.json](../../../outputs/design/space_field_boundary_construction_experiment/boundary_comparison.json)
- [fixture_manifest.json](../../../outputs/design/space_field_boundary_construction_experiment/fixture_manifest.json)
- [source_geometry.json](../../../outputs/design/space_field_boundary_construction_experiment/source_geometry.json)
- [real_ifc_shadow_inspection.json](../../../outputs/design/space_field_boundary_construction_experiment/real_ifc_shadow_inspection.json)
- [boundary_construction_diagnostic.svg](../../../outputs/design/space_field_boundary_construction_experiment/boundary_construction_diagnostic.svg)
- [boundary_construction_preview.blend](../../../outputs/design/space_field_boundary_construction_experiment/boundary_construction_preview.blend)
- [boundary_construction_preview.png](../../../outputs/design/space_field_boundary_construction_experiment/boundary_construction_preview.png)
- [artifact_manifest.json](../../../outputs/design/space_field_boundary_construction_experiment/artifact_manifest.json)
- [verification_report.json](../../../outputs/design/space_field_boundary_construction_experiment/verification_report.json)

No `git add`, commit, or cleanup of existing dirty/untracked files was run.

STOP FOR BOUNDARY CONSTRUCTION DESIGN REVIEW
