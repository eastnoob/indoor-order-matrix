# D6 relative-order decision record

**Status:** owner decision required before production implementation

**Scope:** the first clean-room relative arrangement descriptor
**Contract boundary:** this document defines computable layout evidence. It
does not claim psychological or perceptual validity.

## Decision question

The clean-room contract needs one `relative-order` algorithm, but the D3–D5
evidence does not distinguish the two candidate families below. The choice
must therefore be made by the owner after reviewing the hand-calculable
comparison. No existing evaluator row is used as a selection criterion.

> **OWNER DECISION QUESTION:** Should the first descriptor report (A)
> sequence/order consistency, (B) normalized spacing deviation, or retain both
> as separately named descriptors? Until this is answered, no
> `compute_relative_order(...)` production implementation may be written.

## Shared input contract

### Objects and anchors

The descriptor receives an ordered `object_ids` sequence. That sequence is the
declared comparison sequence; it is not inferred from SVG traversal, source
element names, drawing order, or legacy evaluator keys.

Each object contributes one usable `PlanGeometry` and one anchor:

```text
anchor(object) = arithmetic mean of all finite projected plan vertices
```

The anchor is expressed in the `AnalysisFrame.analysis_unit`. A non-computed
plan geometry has no anchor. The first implementation must not silently switch
to a bounding-box center, source placement origin, or transform-history point.
Those are separate candidate facts and would require an explicit contract
change.

### Axis and direction

The descriptor requires an explicit `AxisSpec` whose unit vector is expressed in
the referenced frame. Coordinate position is the dot product of the anchor
offset from the frame origin with that unit vector:

```text
position_i = dot(anchor_i - AnalysisFrame.origin, AxisSpec.unit_vector)
```

The positive direction is the direction of the declared unit vector. Reversing
that vector reverses the reported sequence; the first slice is directional and
does not treat axes as undirected lines.

There is no global world-X or SVG-horizontal fallback. The default-axis policy
is **no implicit default**: callers must provide `AxisSpec`. An adapter may
author a documented default axis as an explicit `AxisSpec` tied to the frame,
but the descriptor must still receive and record that axis. Missing axis input
is `not_evaluated`, not a silently selected axis.

### Coordinate and transform semantics

- `AnalysisFrame.origin` is stored in `analysis_unit`. It is never interpreted
  as a source-unit value during projection.
- `SourceGeometry3D.world_transform` is the one authoritative transform from
  the geometry vertices' local source coordinates into source world coordinates
  for the selected representation. The canonical projection then applies the
  declared source-to-analysis unit conversion and the analysis-frame projection.
- `SourceObjectFact.world_transform` remains a factual placement record and
  provenance. It is **not** implicitly multiplied with
  `SourceGeometry3D.world_transform`.
- If an adapter starts with a local-to-object geometry transform, it must
  explicitly precompose the object placement before constructing
  `SourceGeometry3D`, and record that handoff in provenance. The descriptor and
  projection layer must never guess whether the two transforms have already
  been combined.

This single-transform rule prevents duplicated object placement and makes IFC
and SVG geometry comparable before descriptor computation.

### Tolerance, ties, and statuses

`tolerance` is a positive distance in `analysis_unit`. Two scalar positions are
tied when their absolute difference is less than or equal to `tolerance`.
Ties are retained as ordered metadata blocks keyed by stable object id; no
arbitrary order is invented inside a tie.

The result status vocabulary is:

| condition | status | value |
|---|---|---|
| usable inputs and selected formula evaluated | `computed` | numeric value in the formula's declared range |
| fewer than two usable objects; all usable positions tied; or spacing has no positive reference gap | `undefined` | `null` |
| non-finite coordinate, invalid transform, or malformed geometry reaches the descriptor | `invalid` | `null` |
| geometry is absent or cannot be projected by the source representation | `not_available` | `null` |
| no explicit axis or no approved algorithm selection | `not_evaluated` | `null` |

The reason, tolerance, axis, unit, usable/excluded object ids, tie blocks, and
geometry provenance are recorded in result parameters/provenance. Numeric zero
is never substituted for a missing or undefined result.

## Candidate A: inversion-rate / order-consistency

### Definition

Project the usable anchors onto the explicit axis. Let the declared sequence be
`o_1, ..., o_n`; let `p_i` be each object's scalar position. For every pair
`i < j` that is not tied, count an inversion when `p_i > p_j`:

```text
inversions = count(p_i > p_j for non-tied pairs i < j)
comparable_pairs = count(non-tied pairs)
order_consistency = 1 - inversions / comparable_pairs
```

The value is in `[0, 1]`, where `1` means every comparable pair follows the
declared sequence and `0` means every comparable pair is reversed. A result
with no comparable pair is `undefined`; a partial tie set remains auditable,
but the first slice should return `undefined` whenever a tie prevents a stable
sequence rather than filling the tie with an id-based order.

This is a sequence agreement summary. It does not measure equal spacing.

### Hand calculation on one point set

Use the same declared sequence `(A, B, C)` and `tolerance = 0.1`:

| fixture | positions `(A, B, C)` | non-tied pair order | inversions / comparable pairs | order-consistency |
|---|---:|---|---:|---:|
| A1 aligned | `(0, 1, 2)` | all forward | `0 / 3` | `1` |
| A2 reversed | `(2, 1, 0)` | all reversed | `3 / 3` | `0` |
| A3 partial tie | `(0, 0.05, 1)` | `A~B`, `A<C`, `B<C` | tie blocks prevent a stable sequence | `undefined` |
| A4 duplicate | `(1, 1, 1)` | all tied | `0 / 0` | `undefined` |

The same points translated by `+10` become `(10, 11, 12)` and retain value `1`.
A positive scale factor multiplies all positions but retains pair signs and the
value. A negative scale factor reverses the declared direction and therefore
changes the value; that is intentional and must be recorded with the axis
direction.

## Candidate B: normalized spacing deviation

### Definition

Use the declared sequence, but compare adjacent absolute gaps rather than pair
order:

```text
g_i = abs(p_(i+1) - p_i), i = 1 ... n-1
g_bar = mean(g_i)
spacing_deviation = mean(abs(g_i - g_bar)) / g_bar
spacing_consistency = 1 - min(1, spacing_deviation)
```

The reported candidate value is `spacing_consistency` in `[0, 1]`. It is
invariant to translation and positive unit scale because the numerator and
denominator scale together. If `g_bar <= tolerance`, the result is `undefined`
because no positive spacing reference exists. A tie creates a zero adjacent
gap; it is retained in the gap/tie metadata and is not converted to a tiny
positive distance. If the owner instead wants ties to invalidate the whole
spacing result, that must be stated in the approval decision.

### Hand calculation on the same point set

| fixture | positions `(A, B, C)` | gaps `g` | `g_bar` | deviation | spacing-consistency |
|---|---:|---:|---:|---:|---:|
| B1 aligned | `(0, 1, 2)` | `(1, 1)` | `1` | `0` | `1` |
| B2 reversed | `(2, 1, 0)` | `(1, 1)` | `1` | `0` | `1` |
| B3 uneven | `(0, 2, 5)` | `(2, 3)` | `2.5` | `0.2` | `0.8` |
| B4 duplicate at first pair | `(0, 0, 2)` | `(0, 2)` | `1` | `1` | `0` |
| B5 all tied | `(1, 1, 1)` | `(0, 0)` | `0` | undefined | `undefined` |

The reversed arrangement demonstrates the key distinction: spacing deviation
can be perfect while order is fully reversed. Spacing alone cannot answer the
sequence-consistency question.

## Comparison and interpretation limits

The hand set shows that the candidates answer different questions:

| question | inversion/order consistency | spacing deviation |
|---|---|---|
| Does the declared sequence run along the positive axis? | yes | no |
| Are adjacent separations uniform? | no | yes |
| Is reversal distinguishable from alignment? | yes | no |
| Is translation invariant? | yes | yes |
| Is positive unit scaling invariant? | yes | yes |
| Does a tie require explicit handling? | yes, tie block/no invented order | yes, zero gap metadata |

Neither candidate is established by the current evidence as a psychologically
valid order or regularity measure. The existing evaluator is reference
material only and does not resolve this algorithm question.

## Invariant and failure checklist

The implementation review must check these examples before accepting a formula:

1. **Moved frame / translation:** translate every anchor and the frame origin by
   the same vector; positions shift by a common constant and the result is
   unchanged. Keeping the frame origin fixed also leaves pair differences and
   order unchanged.
2. **Explicit rotation:** rotate geometry and the declared axis together; the
   result is unchanged. Rotate geometry while keeping the axis fixed; the
   projected order/gaps may change and that change is expected.
3. **Axis reversal:** replacing the unit vector with its negative reverses
   directional order and is not silently normalized away.
4. **Duplicate/tied positions:** preserve tie blocks and return the documented
   undefined behavior where the formula cannot determine a unique order.
5. **Fewer than two objects:** return `undefined` with no numeric substitute.
6. **Missing geometry:** return `not_available` with source and geometry
   provenance; do not create an anchor at `(0, 0)`.
7. **Non-finite or invalid geometry:** return `invalid` with a reason, or reject
   it at canonical record construction before descriptor evaluation.
8. **Stable input order:** the declared `object_ids` order is the comparison
   basis; object ids are only tie metadata and must not become an accidental
   semantic ordering.

## Owner approval record

This document intentionally leaves the formula selection open. The owner must
record:

- selected algorithm id and formula;
- whether ties make the complete result `undefined` or permit a partial
  spacing summary;
- whether the descriptor is named `relative-order` only or whether a separate
  spacing descriptor is approved;
- confirmation of the explicit-axis/no-implicit-default policy;
- any changed anchor or transform semantics.

Only after that approval may Task 4 add production code or descriptor tests.
