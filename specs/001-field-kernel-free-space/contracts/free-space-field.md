# Contract: Exact-Cell FreeSpaceField

`FreeSpaceField` is a concrete `Field` for physical occupancy. It consumes
already-resolved planar occupancy records and never scans source objects,
invokes substitute resolution, reads B3 JSON, or calls `scene_evaluator`.

The constructor requires explicit domain components, pre-resolved records,
explicit `unresolved_source_ids`, a fixed whole-height query context, view
frame, and origin-offset provenance. It also requires finite positive spacing
and positive integer row/column counts. A missing domain is `not_available`;
malformed domain, grid, query, or geometry is `invalid`. No bounding-box
fallback is allowed.

Targets are exact `(row, column)` keys. Batch lookup preserves input order,
duplicates, and cardinality. The query domain id, frame, plane, and supported
whole-height projection must match the field's frozen input context. Any
section, height-band, or tilted-plane request is `not_available` in this slice;
malformed versions are `invalid`. A plane request must never be relabeled
`conditional` without a qualified section handoff.

For each cell, occupancy is evaluated on the positive-area intersection of the
cell and explicit domain. Holes are excluded. Shared boundary line or point
contact alone is not occupancy. Positive-area overlap with a resolved
occupancy component is `value=True`; an eligible empty cell is
`value=False` and does not imply walkability, clearance, or connectivity.
`original` records with valid non-empty components may establish values.
`accepted` substitute records conservatively make field decisions
`conditional`, with an explicit explanation that no physical calibration or
exact envelope is inferred. A selected record without components is not empty:
missing geometry adds its owner to unknown support, while malformed geometry is
invalid. Unresolved support remains `unknown` and never becomes known free;
known occupied evidence is retained.

Boundary-member exclusion and represented-source exact-once accounting are
upstream responsibilities. The field consumes the resulting records and
preserves immutable query, support, source ids, component ids, algorithm
version, and schema version provenance.

Non-goals: evaluator promotion, source scanning, substitute resolution, B3
loading, dense 3D storage, interpolation, clearance, route demand,
connectivity, probability, and decay.
