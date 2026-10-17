# D6 AnalysisDomain handoff real IFC shadow validation

Date: **2026-10-08 (Europe/Berlin)**  
Evidence class: **bounded, read-only real-IFC/Blender-associated shadow validation**  
Result: **no qualified real AnalysisDomain; promotion refused**

This run checked the accepted private `AnalysisDomain` handoff against the frozen real-IFC-associated geometry already captured by the accepted B2 evidence. It did not modify production code, tests, adapters, dependencies, the source IFC, any user Blender file, or Git history. It stopped at evidence and did not begin B3/B4.

## Verified

- Checkout: branch `codex/d6-analysis-domain-layout-handoff`, HEAD `a856391f512fa427c6c37dd61b13dcf3debe4b78`; the index was not changed.
- Real IFC: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, 408,617,800 bytes, SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`, schema IFC4. A read-only STEP scan found 1 `IfcBuildingStorey`, 11 `IfcWall`, 16 `IfcColumn`, 6 `IfcDoor`, 5 `IfcWindow`, 0 `IfcOpeningElement`, 0 `IfcRelVoidsElement`, 0 `IfcRelFillsElement`, 0 `IfcSpace`, and 0 `IfcSpatialZone` records.
- The frozen Blender-associated input is `outputs/design/d6_semantic_enclosure_window_repair/inputs/run_001/live_snapshot.json`, 5,692,042 bytes, SHA-256 `96f40383297fdebb12ed7a26ef9dac38188ed05fcfa7def43c202fceaeb3daad`. Its saved provenance identifies Blender 5.2.0 LTS at `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`, the same IFC path/project identity, and an unsaved live scene. Disk IFC geometry parity remains unverified.
- The replayed NeutralSceneV2 contains 38 source objects and 38 meshes: 11 walls, 16 columns, 6 doors, and 5 windows. The external STEP/GlobalId mapping matches those scene records. No authored `AnalysisDomain` is present.
- The current semantic-enclosure helper reproduced the accepted B2 S1 geometry exactly. S1 is one valid positive-area polygon with area `307.5600036764141 m²`, bounds `[0.0, 0.0, 25.600000381469727, 12.600000381469727]`, one polygon component, no holes, and exact equality to the accepted saved B2 scope geometry.
- The current handoff catalog retained one inferred candidate, `S1`, with its wall and column source references and unresolved aperture references `A11` and `A12`. No automatic winner or authored candidate was introduced.
- Physical occupancy was unchanged across the replay: 38 records before and after, with role counts wall 11, column 16, door 6, window 5. The source scene JSON was byte-stable after canonical serialization.

## Inferred and exercised

- Read-only preview with no action: one inferred S1 candidate, session revision 0, current status `not_available`.
- Ephemeral `select`: candidate focus changed without changing the revision or activating a domain.
- `confirm`: refused with `unresolved_local_aperture`; no `AnalysisDomain` was created and formal field, topology, and route outputs remained `not_available`.
- Reusing the same action ID with different content: refused as `conflicting_action_id`, current status `conflict`, revision 1.
- A confirmation using the old revision after that conflict: refused as `stale_session_revision`.
- The exact inferred support-mesh projection path was attempted from the actual S1 polygon. The current helper returned `inferred_projection_mismatch`; no derived support mesh was accepted. This is retained as a geometry qualification limit, not repaired or softened in the shadow run.
- A separate synthetic authored-confirmation control (`test_private_domain_handoff_authored_confirmation_and_default_compatibility`) passed 1 test with 60 deselected. It verifies the valid private seam only; it is not real-IFC evidence.

## Not available

- A qualified real confirmation or active real `AnalysisDomain`.
- A real authored candidate: the IFC/Blender-associated scene has no authored domain record.
- A genuine real authored/inferred candidate conflict: no authored real candidate exists to form one.
- Active-child occupancy comparison: no candidate qualified, so no consumable child handoff was produced.
- Current live Blender scene inspection. The live Blender MCP status probe failed with `WinError 10053` during addon handshake; no scene read or mutation was attempted.
- Native IFC geometry-adapter parity. The replay used the accepted saved Blender-associated NeutralSceneV2 and current private helpers; it did not run the native IFC loader.

## Blockers and limits

The concrete real-input blocker is the accepted B2 evidence for local unresolved apertures A11/A12. The current exact inferred support-mesh round trip also refuses S1 with `inferred_projection_mismatch`. The source has no IFC spaces or spatial zones, no opening/void/fill relations, and no observed door/window state that could authorize a stronger domain claim. The valid polygon and its diagnostic enclosure evidence therefore remain provisional diagnostic evidence, not a certified room, floor, free-space field, topology graph, route, or walkability result.

The full test suite, native IFC loader, Blender executable, and B3/B4 work were intentionally not run. The run artifacts, provenance, validation assertions, and hashes are in [run_001](../../../outputs/design/d6_analysis_domain_handoff_real_ifc_shadow/run_001/); the companion documentation manifest is [d6-analysis-domain-handoff-real-ifc-shadow-manifest.json](d6-analysis-domain-handoff-real-ifc-shadow-manifest.json).

## Recommendation

Keep the real candidate in `not_available` / refusal state and do not promote S1 or start B3/B4 from this evidence. A future bounded repair would need to resolve or explicitly reclassify A11/A12 and explain the exact support-mesh projection mismatch before any real confirmation is reconsidered.

STOP FOR D6 ANALYSISDOMAIN HANDOFF REAL IFC SHADOW VALIDATION
