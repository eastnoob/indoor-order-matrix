# Directional clearance-constrained group routing design

Date: 2026-11-04  
Workline: `free-space-distance-bridge`  
Workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge`  
Base: accepted eight-neighbor v4 (`b188a4c4`, jj change `lzorkszw`)  
Version writer: root agent only

## Goal

Add an opt-in route model that chooses the shortest route in the current eight-neighbor grid whose every positive-length segment satisfies:

- left clearance `L >= 0.225 m`;
- right clearance `R >= 0.225 m`;
- same-position total clearance `L + R >= 0.55 m`.

The result is shortest in the current grid/candidate model. It is not a claim about a globally shortest route in continuous space.

## Fixed decisions

### Geometry authority

The route skeleton, known-empty/unknown state and exact domain coverage remain the retained free-space lattice. Directional clearance is evaluated from the authenticated retained projected physical polygons in `physical_occupancy[*].geometry_components` and the exact projected analysis-domain boundary. The cached known-empty cell union is support evidence only; it cannot provide first-obstacle distances. No subcell routing, isotropic erosion, body length, turning radius or invented human outline is introduced.

A ray starts at a route position and measures the first intersection with the physical occupancy union or the domain boundary in the requested normal direction. The source or target furniture can therefore be a side obstacle only when it lies on that normal ray; being behind the travel direction does not make it an obstacle.

Selected events retain their original binary64 ray origin and direction during full-index rechecks; reconstructing them from a scalar route distance can lose a silhouette vertex. Complete-index seeds remain eligible minima. First-hit visibility envelopes remove occluded turn events, with collapsed angular silhouettes retained as explicit vertex candidates.

### Segment and turn rule

A route edge is a positive-length center-to-center segment. Its tangent is the edge heading and its left/right normals are evaluated over the whole segment. Polygon-vertex projection events split the segment into intervals; each interval is checked at both ends and its midpoint, with the first-hit distances recomputed from the exact geometry. The recorded minimum is the minimum at one position, never an independent left minimum plus a right minimum from different positions.

At a grid vertex, a transition from heading `h1` to `h2` checks the zero-length cross-section while the normal rotates along the shortest angular arc between headings. Noded boundary vertex events split the arc into fixed nearest-segment intervals. Each positive side distance is a secant on an interval and their sum is strictly convex. Endpoints, midpoints, single-side stationary directions and the unique interior stationary total minimum are checked. The stationary root uses binary64 bisection and the existing threshold tolerance. Vertex events retain the actual boundary vertex distance, so a rounded trigonometric ray cannot miss its own endpoint; ordinary rays are not geometrically buffered. There is no zero-cost turn edge and no body or turn radius. A turn is therefore bound to the next positive-length move.

### State and access semantics

The constrained graph state is `(cell_key, incoming_heading)`. A source access seeds a free cell with the outward heading from footprint cell to free cell. Access candidates remain direction-specific; they are not deduplicated solely by free cell. A target access is eligible only when its approach heading matches the final route heading (the route's final move points toward the target footprint). The centroid → shared-edge proxy → free-cell offset remains a metric endpoint offset and is never treated as a verified walkable corridor.

The graph still uses NetworkX weighted Dijkstra, exact `math.dist` edge weights, deterministic predecessor recovery, source-batched searches and the existing strict-increasing binary64 audit. Tie keys add heading/state path terms.

All four shared-edge source-access headings exist at each eligible center, including a direction absent from neighboring feasible moves. Such a source can turn onto a positive-length edge only through the same complete turn check. Access-only states use the ordinary center occupancy/status gate: observed accepts established/conditional known-empty cells; optimistic may additionally accept unknown cells. Endpoint-only unknown support therefore remains an optimistic lower bound.

### Support and statuses

Every selected constrained edge records center/diagonal flank cells, clearance side sample cell keys, and physical/domain witness references. Turn witnesses are recorded separately. Any `unknown`, `conditional`, `invalid` or `not_available` support is carried into the route and pair status. Observed routing accepts established/conditional center/flank/side support, retaining conditional support as partial; optimistic routing may additionally use unknown support only as a lower-bound witness. Failed side samples are included in the same pair failure frontier. Side support gates query status rather than its occupancy value: a coarse occupied cell may still contain part of a geometrically empty cross-section.

Positive swept area is an interior/interior intersection of dimension two (DE-9IM `2********`); no area threshold is added. Degenerate rays use positive intersection length and retain both cells when lying on a grid boundary. Endpoint-only routes with one heading state and no positive edge have no clearance record, because metric offsets do not certify a corridor.

### Identity and compatibility

`GroupDistanceInput.clearance_policy` is optional and defaults to `None`. `None` preserves the v4 kernel, manifest identity, route fields and historical readers. The constrained model is versioned as:

- algorithm: `group-distance/3`;
- schema: `group-distance/v3`;
- edge support: `eight-neighbor-two-flank-occurrences-directional-clearance/1`;
- policy: `directional-clearance/1`.

The policy thresholds and geometry/turn rule fingerprints participate in the input and manifest identity. Existing v1/v2 artifacts remain readable and unchanged.

## Output contract

Constrained routes add a compact `clearance` record:

- `min_left_m`, `min_right_m`, `min_total_m`;
- `limiting_segment_index`, `limiting_position_m`;
- `limiting_left_m`, `limiting_right_m`, `limiting_total_m`;
- `edge_witnesses`, `turn_witnesses`;
- `support_cell_keys`, `support_query_refs`, `support_statuses`.

The pair observation keeps the existing Euclidean and hybrid channels. Hybrid status is `computed` only when all selected support is established; `partial` when conditional support is selected; `unknown` when only the optimistic route exists; `invalid`/`not_available` preserve their existing precedence. An unreachable constrained route remains `unreachable` with a reason that states the clearance model.

## Performance boundary

The constrained graph expands headings only when the policy is enabled and retains one source search at a time. Full physical geometry is loaded once per calculation. Only selected route witness data is serialized; the full numeric graph is not embedded in HTML.

## Visual decision

Visual is required because numerical checks cannot establish that the user sees the intended same real S3 region and the corridor bands/narrowest cross-section. Reuse the existing v4 route board inputs, render old/new routes for the fixed pair when reachable, and choose another real reachable pair from the new result if the fixed pair becomes unreachable. User visual review remains a separate pending gate.

The displayed band uses each edge's independent left/right minima as a conservative rectangle. Their sum is not the same-position minimum total; that value belongs to the separately displayed limiting edge/turn cross-section. Complete side evidence remains in numerical output while the HTML contains only the summary and display coordinates.
