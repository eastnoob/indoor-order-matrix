# D6 soft-field / empty-space evidence design experiment

- Date: 2026-10-02
- Status: diagnostic experiment only; no production selector or owner-confirmed partition
- Stop condition: **STOP FOR SOFT-FIELD OWNER VISUAL REVIEW**

## Scope and input

The experiment reads the real IFC `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` and retains its SHA-256 in every JSON bundle. The observed inventory is IFC4, 37 exact `ObjectType == "furniture_group"` authored groups, 95 grouped `IfcFurniture` members, 11 walls, 6 doors, no `IfcSpace`, and no `IfcOpeningElement`/void/fills relations. Group members stay indivisible. Walls and other products are retained as physical/context reference geometry; they are not promoted to an AnalysisDomain or opening state.

The displayed frame is a **provisional diagnostic frame** made from the extracted wall and furniture extents with a relative margin. It is not a room boundary, and source extent is not treated as free-space truth. Existing 1/2/3/4 hard candidates are reused as diagnostic MST relative-gap views only.

## Diagnostic representations

### A — furniture-group continuous support field

For each exact group node, pairwise footprint boundary gaps are normalized by the smaller group footprint area. Node compactness and pair support are reported as rank/relative evidence. The display field is a continuous centroid-kernel gradient whose bandwidth is derived from the median positive nearest-neighbour normalized gap; no fixed metre threshold is used. Nearest-neighbour links and group markers are overlaid on the real IFC plan.

The field is evidence of relative support/separation between authored group nodes. It does not infer a room, activity role, route, walkability, visibility, or production selector.

### B — empty-space diagnostic evidence

`empty_space_field` is an independent diagnostic attribute. It is the provisional diagnostic frame complement of the exact authored furniture-group footprint union. It is never added to furniture membership and no authored membership is rewritten.

The bundle records free area, continuity, adjacent group IDs, local width proxy quantiles, lowest relative-clearance samples, and boundary provenance. The width proxy is twice the sampled point-to-furniture-boundary clearance. It is a local geometry profile only; it is not route width, walkability, visibility, or an activity area.

The display grid is 72 × 54 for visualization. A 54 × 40 grid and a quarter-cell origin shift are also recorded as sensitivity variants. The sampled topology is explicitly not treated as true free-space topology or a production resolution.

## Evidence readout for owner review

- The upper-left compact band (G06/G20/G27/G11 in the existing display labels) is a stable local adjacency chain: adjacent authored group footprints touch in the normalized plan relation and appear as one concentrated support patch in the continuous field. This supports a local subfield interpretation, while still leaving it inside the broader field.
- The lower-left and lower-right furniture rows also contain touching/near-touching authored pairs, but the empty-space diagnostic remains one connected component in the provisional frame and the continuous field fades through the intervening layout. That supports treating these as layout variation or local clusters rather than independent zones.
- The existing 2-, 3-, and 4-region cuts remove edges with low continuous pair support (approximately 0.146–0.155; pair rank approximately 0.075–0.086). The cut ranks are close to one another, so the evidence does not show a stable, owner-independent change point. The 3-region view is therefore especially fragile as a semantic partition, consistent with the prior owner concern that it isolates two table-chair groups.
- The empty-space candidate has one bounded diagnostic component, free area approximately 355.884 m², and all 37 authored groups adjacent to its complement boundary. Its sampled local width proxy has p10 ≈ 0.499 m, p50 ≈ 3.424 m, and p90 ≈ 19.319 m. These are descriptive geometry values under the provisional frame; they do not imply a corridor, activity area, route, or walkability.

## Hard/soft relationship

The 1-region candidate is the whole provisional group field. The 2/3/4 candidates are discrete views made by successively cutting the largest positive edges in the same relative-gap MST. The soft field retains the gradient and shows that the cut edges are weakly supported relative boundaries rather than accepted spatial boundaries. No final number of regions, threshold, backend, Bayesian/ML method, production resolution, route width, or selector is chosen.

## Verification and scope

- Default run and `tmp_reproduction_20261002` both completed; core JSON hashes match.
- Six PNGs were rendered with portable Blender 5.2.0 LTS: hard 1/2/3/4-region views, `soft-field diagnostic`, and `empty-space diagnostic evidence`.
- PNG metadata, full-image crop bounds, JSON/schema/source hash, and disposable `.blend` readback passed.
- The disposable blend contains six orthographic scenes and was reopened read-only. The current user Blender file was not opened or saved by this experiment. Current Blender source identity is recorded from the existing live input inspection as observed and path-matched to the real IFC.
- Production code, adapters, formal tests, dependencies, source IFC, and the user Blender file were not modified.

Artifacts are listed in `d6-space-field-soft-field-artifact-manifest.json`; the owner-facing visual record is in `d6-space-field-soft-field-owner-visual-review.md`.
