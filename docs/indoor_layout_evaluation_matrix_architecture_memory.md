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

## Evaluation Matrix

Evaluation Matrix code scores and audits evidence. The matrix consumes neutral scene plus inference evidence; it should not depend on SVG-specific rendering, SVG element names, or hand-authored SVG overlay conventions.

## Practical Test

If a behavior still works when the scene is a plain Python dict with `Rect` geometry and no SVG parser involved, it belongs to the inference or matrix layer. If it requires `data-*` parsing or XML traversal, it belongs to the input adapter layer.

## Code Comment Rule

Every function should have a docstring. Important computation steps should have comments that explain the intent of the operation, especially inference, scoring, geometry conversion, graph construction, and adapter handoff logic. Comments should be in English and should clarify why the step exists, not restate obvious assignments.

All new or modified project-owned code should follow this rule. Vendored OCTA toolbox code is exempt unless it is edited.
