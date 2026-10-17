# US1 API Architecture Review

Date: 2026-10-10

## Verdict

**Accept the direction, with small API corrections before implementation.**

The proposed `FieldStatus` / immutable `FieldQuery` / immutable `FieldSample` /
`Field` core matches the planned architecture. It keeps exact lookup separate
from optional spatial capabilities, supports relation targets that are not
coordinates, avoids dense 3D allocation, and does not couple the core to an
evaluator. It is the right MVP boundary for US1.

The design should not be implemented exactly as a loose collection of typed
records, however. The following details need to be frozen in the contract so
different field implementations cannot silently disagree about missingness,
query identity, or mutability.

## Required API Corrections

### 1. Make the six statuses an unordered `str, Enum`

Define exactly:

```text
established, conditional, unknown, outside, invalid, not_available
```

Do not encode precedence by enum declaration order or numeric ranking. The
owner decision defines gates, not a total ordering:

1. malformed target/query/source -> `invalid`
2. absent requested domain/channel/representation -> `not_available`
3. valid target outside an available domain -> `outside`
4. available channel with insufficient or ambiguous evidence -> `unknown`
5. computed only for a declared limited scope -> `conditional`
6. complete declared and validated scope -> `established`

The implementation should validate the required evidence for each gate. In
particular, `outside` is illegal when the domain is absent, and `conditional`
must carry an explicit limitation/scope explanation. The enum itself should
not attempt to resolve conflicting evidence; the concrete field must apply the
gate rules and report the reason.

### 2. Define immutability as deep, not only `frozen=True`

`FieldQuery` and `FieldSample` should be frozen records, but nested values must
also be immutable at the public boundary:

- `source_ids`: `tuple[str, ...]`, never a mutable list;
- provenance/query metadata: an immutable, JSON-safe mapping (or the
  repository's existing frozen JSON-value convention);
- support/units/explanation: immutable values;
- batch results: a tuple preserving target order.

`Mapping[str, Any]` inside a frozen dataclass is not immutable and would let a
caller mutate audit history after the sample was returned. Do not make
provenance an arbitrary object graph; raw scene objects, live adapters, and
mutable geometry handles must not enter this record.

### 3. Separate field declaration metadata from the concrete query instance

The documents use `query_context` both as field metadata and as a per-request
query. Freeze the distinction:

- `FieldQuery` is the complete immutable request: domain identity, frame or
  relation scope, plane/height band, demand, tolerance, and revision.
- `FieldSample` must retain that exact query (or an immutable canonical query
  identity plus the same fields), so a returned value is replayable.
- `Field` metadata should describe the field's supported domain/frame,
  `value_schema`, `representation`, and field-level provenance. It should not
  expose a mutable “current query”.

This avoids a hidden ambient context and makes scalar/batch equivalence
auditable. A sample's provenance should include algorithm/schema version,
representation, source ids or artifact references, and the query revision or
canonical query identity.

### 4. Make value availability explicit by status

Use `value: T | None`; do not use numeric zero or an implicit sentinel for
missingness. For the first contract, enforce:

- `invalid`, `not_available`, and `outside`: no qualified value (`None`);
- `unknown`: no qualified value (`None`); retain support/diagnostic evidence
  and explanation instead;
- `conditional` and `established`: a value is present and its scope is stated.

If a later use needs a partial estimate while remaining `unknown`, add an
explicit evidence/support type rather than allowing consumers to interpret an
unknown value as free, empty, or zero. This is the smallest rule that protects
the status gate from downstream numeric coercion.

### 5. Resolve the `Field`/`evaluate_many` contract explicitly

Use a generic protocol or abstract contract with a target type independent of
coordinates, for example conceptually:

```text
Field[Target, Value]
  evaluate(target: Target, query: FieldQuery) -> FieldSample[Value]
  evaluate_many(targets: Iterable[Target], query: FieldQuery)
      -> tuple[FieldSample[Value], ...]
```

The default `evaluate_many` should call exact `evaluate` in input order and
return a tuple. It must not sort, deduplicate, coerce targets to points, or
infer interpolation. Concrete fields may override it for batching, but the
override must preserve one result per input target and the same canonical
semantics as repeated scalar evaluation.

There is one contract ambiguity to remove before coding: if `Field` is a
`Protocol`, both methods are structural requirements and a shared default
method is awkward; if it is an ABC, `evaluate` can be abstract and
`evaluate_many` can have the default implementation. Either is viable, but
the public choice must be recorded. For the smallest implementation, prefer a
generic ABC with abstract `evaluate` plus the concrete ordered default
`evaluate_many`, while keeping optional sampling/topology capabilities out of
the base type.

### 6. Keep relation targets first-class

Do not type `target` as a point, tuple of coordinates, or hashable coordinate
key. Use a generic `Target` type. Spatial fields can instantiate it with a
coordinate record; relation fields can use an object id, pair, or typed
relation target. `FieldQuery` may carry spatial plane/height data when
applicable, but those fields must be optional or represented by an explicit
non-spatial scope. A relation field must not need a fake coordinate frame or
an interpolation method merely to satisfy the core.

### 7. Keep provenance typed enough to audit, but not a second domain model

At minimum, distinguish these stable facts:

- source/artifact identifiers;
- representation identifier;
- algorithm version;
- schema version;
- units where meaningful;
- tolerance/configuration revision;
- query identity or revision;
- limitation/scope notes for `conditional`.

`source_ids` should remain a direct sample field for cheap inspection; the
provenance payload may contain richer source records and derivation details.
Do not require every concrete field to invent a large provenance hierarchy in
US1. A small immutable JSON-safe mapping with required-key validation is
enough, and it leaves room for later adapters without coupling the core to
IFC, B3, or `evaluate_scene`.

## What the Minimal Core Must Not Add

The proposed exclusions are correct and should remain explicit:

- no default interpolation or sampling method;
- no dense 3D storage/allocation;
- no default decay, probability, or aggregate score;
- no automatic domain inference from a scene bounding box;
- no evaluator import or `evaluate_scene` bridge;
- no B3 loader mutation or whole-height promotion;
- no requirement that every field expose topology, distance, or clearance.

Optional capabilities should be separate protocols/functions later. The base
contract should remain exact lookup plus ordered batch lookup.

## Verification Expectations for US1

The focused tests should cover more than method presence:

1. frozen records reject top-level and nested mutation;
2. scalar and batch calls produce canonical-equivalent samples, including
   duplicate and relation-native targets;
3. batch output preserves input order and cardinality;
4. all six statuses remain distinct and obey the gate rules;
5. invalid, unavailable, outside, and unknown never become numeric zero/free;
6. conditional samples preserve explicit section/proxy scope;
7. source ids, query identity, units, tolerances, algorithm version, and schema
   version survive canonicalization;
8. malformed record construction is rejected, while a valid query that cannot
   be answered returns a status-bearing sample rather than silently raising.

The last point should be implemented consistently: structural API misuse may
raise `TypeError`/`ValueError` at construction, but ordinary field evidence
failure is represented by `FieldSample.status`.

## Final Assessment

With the corrections above, US1 is a minimal and architecture-compatible
checkpoint. It provides the common audit envelope for spatial and relational
fields without pretending that either field has interpolation, complete
occupancy, or evaluator authority. No production caller, test outside the
future US1 contract tests, B3 loader, architecture document, or public
`room_analysis_model` export needs to change for this review.

This review did not implement or run the planned Field core tests; the
constitution gate and exact public Python symbol shape remain owner decisions.
