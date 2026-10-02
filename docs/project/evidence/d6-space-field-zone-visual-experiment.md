# D6 Current IFC Space-Zone Visual Experiment

- Date: 2026-10-02
- Status: STOP FOR OWNER VISUAL REVIEW
- Scope: a read-only, exploratory Blender comparison for owner visual judgment. It does not select a production partition count or algorithm.

## Scene identity and input

The currently open Blender scene was inspected read-only with Blender MCP before preview extraction. It was Scene in Blender 5.2.0 LTS, metric with millimetre display, unsaved, and identified the floor candidate as Level 1. Bonsai IfcStore.path matched the source IFC path exactly: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`. The source hash is `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240` (408,617,800 bytes). The open scene was not edited or saved. Preview scenes were built only in background mode from factory startup and saved to the disposable experiment directory.

Measured IFC facts: IFC4; project length unit mm, converted to metres by 0.001; 37 IfcGroup, 95 IfcFurniture, 11 IfcWall, 6 IfcDoor, 0 IfcSpace, 0 IfcOpeningElement, 0 IfcRelVoidsElement, and 0 IfcRelFillsElement. Analysis nodes are only groups with exact ObjectType equal to `furniture_group`; their 95 members remain indivisible. Group names are retained as diagnostic metadata and do not determine membership or cuts.

Context shown in gray includes 16 IfcColumn, 6 IfcDoor, 27 IfcFurnishingElement, 1 IfcSlab, 11 IfcWall, and 5 IfcWindow. IfcBuildingElementProxy and product classes outside the explicit extraction allowlist were not extracted into the context display; the images do not claim complete scene context. The wall display uses the XY projection of triangles from each source Body solid, retaining actual plan bends and wall thickness. Doors are context only: door geometry is not an opening relation or a known open/closed state.

## Boundary and measured relationships

There is no owner-accepted AnalysisDomain and no IfcSpace. The dashed orange frame is the source-geometry extent fallback, used only as a shared diagnostic view frame; it is not a room edge and does not clip or assign group membership. Inner-face, outer-face, and centerline boundary candidates have not been verified against this real IFC. Selecting a boundary could change clipping or how groups relate to enclosure, but the furniture-group partitions here do not depend on the display frame; boundary interpretations are not compared in these figures.

All 666 pairs of furniture groups have computed planar boundary gap, centroid distance, overlap/touch flag, and coarse Z-range compatibility. Sixteen pairs touch or overlap; all 666 Z ranges overlap. Height compatibility is diagnostic and is not used as a cut gate. Obstacle-crossing was not evaluated. Furniture relation footprints use convex hulls of member XY vertices, so holes and concavities are filled. Region fills are also display-only convex hulls of each set’s footprint union and may overlap; they are not occupied floor areas or closed partitions.

## Candidate comparison

The exploratory candidate series cuts the largest positive edges in one minimum-spanning tree over area-normalized 2D group boundary gaps. It uses no fixed metre threshold and is not a proposed production algorithm. Counts below refer to indivisible furniture-group nodes in each displayed set.

| Candidate | Group counts per set | Cut edges shown in the side panel |
|---|---:|---|
| Baseline, 1 set | 37 | None |
| 2 sets | 33, 4 | G09 ↔ G11; gap 1.291 m, relative gap 1.425 |
| 3 sets | 31, 4, 2 | Adds G04 ↔ G17; gap 1.428 m, relative gap 1.423 |
| 4 sets | 27, 4, 4, 2 | Adds G02 ↔ G18; gap 1.254 m, relative gap 1.384 |

The early relative cut weights are close. These alternatives show how one heuristic can peel off small sets while retaining a large connected set; they are not evidence that any region count is correct.

## Rendering and review

Four PNGs were rendered at 2400 × 1200 RGBA with the same top-down orthographic view. The figures label metres, boundary status, diagnostic candidate status, furniture-group nodes, context/reference, and physical wall geometry. Text bounds were checked before rendering and no labels crossed the safe camera frame. All four PNGs were opened and checked for geometry, labels, legends, and crop. A readback of the disposable blend confirmed four scenes, each containing 37 group labels, 11 physical wall meshes, candidate fills, and an orthographic camera at the same output resolution.

The render command returned exit code 0 and wrote the PNGs and blend. Blender reported an optional thumbnail-cache write warning outside the experiment directory; the requested outputs were present, non-empty, and visually inspected. The exact commands, exit codes, artifact byte counts, and SHA-256 values are in `outputs/design/space_field_zone_visual_experiment/run_001/artifact_manifest.json`.

## Scope and owner review

No room, free-space, connectivity, route, walkability/accessibility, visibility, activity function, production-space role, probability, or accuracy was inferred. No backend, threshold, grid resolution, or final partition count was selected. Production code, adapters, formal tests, API, dependencies, source IFC, and the open Blender scene were not modified.

The visualization review followed the integrity and rendered-contrast checks in the repository scientific-visualization skill. Reference: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065. DOI: 10.48550/arXiv.2609.00065.

Owner review questions:

- Which candidate best matches your understanding of how this space should be divided?
- Is anything that you consider separate still grouped with other furniture nodes?
- Do the colors read as separate areas, or as soft boundaries in one continuous field?

STOP FOR OWNER VISUAL REVIEW
