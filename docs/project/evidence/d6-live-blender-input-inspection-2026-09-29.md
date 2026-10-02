# Live Blender input inspection: 2026-09-29

## Scope and method

Owner requested inspection of the currently open portable Blender model and a readiness assessment, not execution of contract repair or IFC shadow validation.

Blender MCP addon status failed with `Incomplete JSON response received`; scene-info did not return usable data and was cancelled. This does not establish an outdated addon. The computer-use skill was read and used as fallback: inspect the window, temporarily select Python Console, query the already-loaded Bonsai `IfcStore.file`, then restore 3D Viewport. No model save, IFC reopen, tessellation, analyzer execution, dependency installation, or production edit was performed.

## Directly observed live facts

- Executable: `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`.
- UI: Blender 5.2.0 LTS, Bonsai 0.8.5; model visible in 3D Viewport.
- Blender console Python: 3.13.13 (project Pixi Python is 3.12.13).
- Loaded path: `D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`.
- IFC schema: IFC4.
- `IfcGroup`: 37; exact `ObjectType == "furniture_group"`: 37.
- Unique grouped members: 95, all `IfcFurniture`.
- All 95 members declare both `Analysis` and `Body` representations. Presence is not proof of extractability or polygon validity.
- `IfcWall`: 11; `IfcDoor`: 6.
- `IfcOpeningElement`, `IfcRelVoidsElement`, `IfcRelFillsElement`: all 0.
- `IfcSpace`: 0.
- Length unit: `MILLI METRE`.

Counts were read from the live IFC backend, not copied from a historical report. Door geometry does not establish opening relationships. Zero spaces does not establish that every possible IFC spatial analysis domain is unavailable.

## Code readiness and remaining limits

- `adapters/ifc_bonsai.py::_open_source` accepts an already-loaded backend; `load_ifc_neutral_scene` exposes the IFC input route. The native adapter still extracts geometry across products.
- Exact furniture-group extraction exists in `_native_group_records`.
- `_native_analysis_domain` requires an explicit IFC spatial source ID; no validated analysis domain was selected during this inspection.
- `features/group_self_description.py::describe_group_relations` accepts the neutral scene and computes planar group/member observations. Candidate views remain deferred/null. Holes remain unsupported.
- The standalone descriptor is not an established live Bonsai UI integration. Current-model units, placement, extracted geometry, numeric results and source-linked visual overlays were not tested end to end here.
- Blender/Pixi Python versions differ: compiled dependencies must not be assumed interchangeable.
- 3D/Z/barrier and final inferred membership are not established by this inspection. Whole-scene exhaustive candidate diagnostics should not be run without addressing their combinatorial cost.

## Assessment, not authorization

Real IFC input/geometry validation is timely; final inferred-group acceptance is premature. The model has the declared inputs for a small read-only geometry smoke check, but interface compatibility is not execution proof.

Recommended next validation: extract a small source-linked sample (for example three authored groups), check representation validity, metre conversion and placement, compute existing planar observations, and display labeled footprint/center/direction overlays in a separate diagnostic scene. Preserve missing/unsupported statuses; do not infer a room domain or openings from appearances. Sampling establishes sample readiness only, not whole-model accuracy.

This recommendation does not authorize Checkpoint A/B, production integration, a selector, Bayesian/ML execution, or model modification. No tests were run in this inspection. Existing dirty/untracked work was left untouched.

STOP FOR DESIGN REVIEW
