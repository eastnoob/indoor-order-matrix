# Indoor Layout Matrix Architecture Memory

This is the durable boundary for the indoor layout evaluation work.

## Boundary Rule

SVG is a neutral BIM proxy/base map. SVG does not define the evaluation matrix.

The SVG fixture is only a compact way to provide objective layout records while the BIM/Rhino adapter is not live yet. It may carry geometry, roles, ids, grouping keys, affordance metadata, boundary weights, entries, paths, and adapter references, but those attributes are input data only.

## Layer Contract

1. `features/scene_loader.py` converts SVG into a Neutral Scene.
2. `features/scene_inference.py` converts the Neutral Scene into inference evidence.
3. `features/scene_evaluator.py` computes Evaluation Matrix rows from the Neutral Scene and inference evidence.

## Neutral Scene

Neutral Scene records are objective inputs: objects, regions, boundaries, entries, paths, column axes, geometry, metadata, and weights. A future BIM adapter should produce the same kind of records without changing matrix definitions.

## Input Priority

User-authored semantic attributes are the primary input for evaluation. Roles, ids, groups, regions, affordance metadata, boundary weights, openings, paths, column axes, and adapter references should drive matrix computation whenever they are present.

bbox, rect-cell, or geometric fallback algorithms are secondary. They may create computational stand-ins only when explicit semantic attributes are missing or insufficient for an operation. These stand-ins exist to make the matrix computable; they must not override user-authored semantic intent.

## Inference / Evidence Layer

Inference / Evidence Layer owns derived affordance zones, inferred region candidates, inferred regions, inferred region gap paths, and inferred gap-path graph evidence. Region and path definitions belong here, not in the SVG file.

The inference hierarchy is object footprint -> furniture affordance extent -> activity region candidate -> inter-region gap path. A furniture affordance extent is the maximum envelope of one object footprint plus its own affordance zones. An activity region candidate is a group of furniture affordance extents. An inferred gap path is the remaining axis-aligned band between activity region candidates, with required width read from scene settings rather than guessed from SVG graphics.

Activity groups are first-class inference evidence between individual furniture extents and activity region candidates. A group affordance extent is a union envelope of member furniture affordance extents. Pairwise overlaps/intersections are relation evidence, not the definition of the group extent.

Spatial networks use one shared evidence schema for different scopes. `region_internal` networks describe relationships inside one activity group, while `inter_region` networks describe gap-path connectivity between activity region candidates.

Boundary semantics are normalized inference evidence from authored boundary metadata and weights. They describe walk passability, visual passability, thickness, grouping strength, openings, and surface identity without treating the SVG drawing itself as the matrix definition.

## Region Trend Frame Rule

Region trend is a two-axis frame inferred from activity-group frame evidence. The raw activity-group/frame angle remains auditable as `axis-original-angle` when a later correction is applied.

Trend ground truth is member furniture frame consensus when directional member evidence exists. Shape geometry is separate: PCA, hulls, bbox envelopes, and affordance extents describe region shape, occupancy, and path spacing, but they should not override trend direction. A single directional furniture item can therefore have strong trend strength; evidence support should be audited separately from concentration.

Near-orthogonal visual noise should not be corrected by a hard small-angle threshold. The accepted rule is explainability-first: compare the current region frame with its nearest 0/90-equivalent frame, and correct only when the orthogonal frame Pareto-dominates the current frame. That means the orthogonal frame must keep the projection envelope no larger, explain member furniture frames at least as well, have some member-frame support, and improve at least one of area or member alignment.

This correction applies only to the region trend/frame metadata. It must not reintroduce broad region-shape candidate selection or rewrite the SVG/BIM proxy geometry. Real oblique organization, such as the oblique north tables or west lounge samples, should remain oblique when the orthogonal frame explains the members or envelope worse.

After the final region trend angle is selected, `axis-primary-extent` and `axis-secondary-extent` must be recomputed in that same final frame. Do not carry PCA extents across angle normalization or correction, because overlays and downstream audits draw lengths from these metadata fields.

## Evaluation Matrix

Evaluation Matrix code scores and audits evidence. The matrix consumes neutral scene plus inference evidence; it should not depend on SVG-specific rendering, SVG element names, or hand-authored SVG overlay conventions.

## Practical Test

If a behavior still works when the scene is a plain Python dict with `Rect` geometry and no SVG parser involved, it belongs to the inference or matrix layer. If it requires `data-*` parsing or XML traversal, it belongs to the input adapter layer.

## Code Comment Rule

Every function should have a docstring. Important computation steps should have comments that explain the intent of the operation, especially inference, scoring, geometry conversion, graph construction, and adapter handoff logic. Comments should be in English and should clarify why the step exists, not restate obvious assignments.

All new or modified project-owned code should follow this rule. Vendored OCTA toolbox code is exempt unless it is edited.
