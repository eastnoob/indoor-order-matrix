# Contract: Frozen B3 Read-Only Adapter (US2 implemented)

Input is exactly the validated dictionary returned by
`features.discrete_space_field.load_discrete_space_field`.

The implementation symbol is
`features.space_field_adapter.B3AdapterView`, constructed with
`B3AdapterView.from_loaded(delivery)`. It adds a typed read-only Field view and
sample lookup, but must not alter the loader schema, variant selection, artifact
names, SHA256 checks, or return shape.

It must preserve source sections, sample statuses, counts, analysis plane,
units, provenance, and all `null`/open completeness fields. A conditional
world-XY `z=1.6 m` observation remains conditional; it cannot be certified as
complete occupancy, clearance, connectivity, or whole-height walkability.

The adapter must not import `scripts.design`, `evaluate_scene`, or the live
neutral-scene evaluator.

It does not perform interpolation, geometry reconstruction, clearance,
connectivity, whole-height walkability, source discovery, or live evaluator
promotion.
