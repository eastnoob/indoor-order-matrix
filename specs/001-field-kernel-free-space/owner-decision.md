# Owner-Proposed Decisions: Field Kernel Checkpoint

Date: 2026-10-10

These are the owner-level planning decisions derived from S1–S3 evidence. They
are target architecture decisions, not proof that the classes already exist.

## Public concept name

Use `Field` as the single global concept. A concrete implementation may use a
protocol or an immutable base record internally, but the project should not
create competing `FreeSpaceField` and `InferredGroupField` base hierarchies.
Concrete uses are instances/bundles selected by semantic channel and
capabilities.

## Status semantics

Do not force all states into one arbitrary numeric precedence. Evaluate them in
the following gates:

| Gate | Status | Meaning |
|---|---|---|
| Input/query validity | `invalid` | Required target, source geometry, or query is malformed or inconsistent. |
| Domain availability | `not_available` | The requested domain or channel/representation is absent, so the result cannot be evaluated. |
| Domain membership | `outside` | The query is valid and the target is outside an available selected domain. |
| Evidence sufficiency | `unknown` | The channel exists, but coverage, ambiguity, or uncertainty prevents a qualified value. |
| Qualification | `conditional` | A value is computed, but only for a declared limited scope such as a section or proxy. |
| Established result | `established` | The value is computed under the complete declared query and validation scope. |

`outside` therefore requires a valid available domain. A missing domain is
`not_available`, not `outside`. A conditional section observation is never
silently upgraded to whole-height truth.

## Evidence and decay

Evidence contributions retain support, quality, polarity, status, source refs,
and explanation. Membership strength may overlap across candidate groups and
is not automatically a probability. Decay is an explicit influence/operator
choice; physical occupancy and measured distance do not decay.

## Implementation boundary

The first implementation checkpoint is limited to the pure Field core and
read-only B3 adapter/visualization seam. It does not change the existing B3
loader, `evaluate_scene`, `room_analysis_model`, or default evaluator overlay.

## US1 Python shape

Freeze the first implementation as:

```text
FieldStatus(str, Enum)
FieldQuery(frozen record)
FieldSample[T](frozen record)
Field[Target, Value](ABC)
  evaluate(target: Target, query: FieldQuery) -> FieldSample[Value]
  evaluate_many(targets: Iterable[Target], query: FieldQuery)
      -> tuple[FieldSample[Value], ...]
```

`FieldSample` retains the exact immutable query. `FieldQuery`, `FieldSample`,
field metadata, support, source ids, and provenance are deeply immutable at
the public boundary. `evaluate_many` preserves input order and cardinality.
This is the minimum contract; spatial sampling, topology, clearance, decay,
and evaluator bridges remain separate capabilities.

## Remaining owner gates

- constitution file is still an unratified placeholder;
- the implementation must still validate the exact Python record fields and
  focused tests against this frozen shape;
- promotion into the live evaluator requires a separate decision.

## US4 exact-cell decision

US4 consumes only an already-resolved whole-height handoff containing exact
domain components, records, explicit unresolved source ids, query context,
frame, and origin offset. Missing domain/channel is `not_available`;
malformed configuration or evidence is `invalid`; unsupported section,
height-band, tilted-plane, and demand queries are `not_available`.
`original` and `accepted` are representation values, not statuses:
original-only evidence may establish a result, while any accepted substitute
makes the field decision `conditional` with an explicit limitation. Empty does
not certify walkability, and known occupied evidence remains visible alongside
unknown diagnostics.
