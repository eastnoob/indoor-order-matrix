# Contract: Global Field Core (US1 implemented)

The implemented US1 core exposes one small semantic contract as a generic
abstract base class plus deeply immutable query/sample records in
`features/field_core.py`. The public concept is `Field[Target, Value]`; the
target is not assumed to be a coordinate. B3 adaptation, channel bundles,
visualization, and live evaluator promotion remain future work.

## Required fields

`Field` exposes `domain`, `frame`, `value_schema`, `representation`, and
field-level `provenance`. `FieldQuery` carries the complete request context:
domain identity, optional frame/plane/height-band, demand, tolerance, and
revision. `FieldSample` retains the exact immutable query that produced it.

## Required operations

`evaluate(target, query)` and `evaluate_many(targets, query)`. The default batch
implementation calls exact `evaluate` in input order and returns a tuple. A
concrete field may override it for batching only if cardinality and canonical
semantics remain identical.

## Required semantics

- preserve categorical, scalar, vector, and relation-native values;
- preserve `established`, `conditional`, `unknown`, `outside`, `invalid`, and
  `not_available` distinctions;
- keep `source_ids`, query metadata, support, and provenance deeply immutable;
- require `value is None` for `invalid`, `not_available`, `outside`, and
  `unknown`; require a value for `conditional` and `established`;
- require every `conditional` sample to carry a non-empty explanation of its
  scope or limitation;
- require provenance to retain algorithm and schema versions;
- never infer a value merely because a representation lacks a sample;
- keep source ids, algorithm version, schema version, units, plane/height band,
  and tolerances auditable;
- allow optional capabilities without forcing relation fields to interpolate.

## Explicit non-contracts

No default decay, no implicit Bayesian probability, no dense 3D allocation, no
automatic domain inference, no implicit conversion of section occupancy to
whole-height free space, and no forced coordinate target for relation fields.
