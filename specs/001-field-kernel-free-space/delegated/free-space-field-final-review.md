# FreeSpaceField Final Code Review

Date: 2026-10-10

## What this change does

`features/free_space_field.py` adds an exact-cell physical-occupancy field over
pre-resolved plan components. It clips cells to an explicit domain, preserves
the six-state `FieldSample` contract, keeps accepted substitutes conditional,
and avoids resolver/evaluator/source rescanning.

The core direction is right, but four data-integrity bugs and one verification
gap remain. They affect boundary truth, immutability, exact-once accounting,
and auditability.

## Must Fix

1. **Area is compared with a length tolerance** (`features/free_space_field.py:235-237`)
   - **What this is:** Domain eligibility uses `eligible.area <= query.tolerance`.
   - **Problem:** `query.tolerance` is a geometric tolerance in metres, while
     `eligible.area` is square metres. A positive sliver can therefore become
     `outside` solely because the numeric tolerance is larger. Reproduction:
     a `0.1 m × 1 m` domain against a `1 m × 1 m` cell with
     `FieldQuery(tolerance=0.2)` returns `FieldStatus.OUTSIDE`; with tolerance
     `0.0` it returns `ESTABLISHED`. Positive-area intersection is the stated
     rule, so the first result is wrong.
   - **Fix:** Do not compare area to the linear query tolerance. Use
     `eligible.area <= 0.0` for the positive-area rule, or introduce an
     explicitly area-squared tolerance with a separately defined contract.
     Keep occupancy/domain comparisons dimensionally consistent.
   - **If we skip it:** Thin boundary cells disappear as outside, and results
     change when a caller adjusts an unrelated length tolerance.

2. **Field metadata can be rebound after construction** (`features/free_space_field.py:192-200`)
   - **What this is:** The subclass `__setattr__` ends with
     `object.__setattr__`, bypassing `Field.__setattr__`.
   - **Problem:** The supposedly frozen base metadata is mutable. After a valid
     field is built, `field.provenance = {"x": 1}`, `field.domain = {"id":
     "other"}`, and `field.frame = "other"` all succeed. The field then
     evaluates using private frozen ids/frame while exposing different public
     metadata, breaking audit identity and allowing inconsistent handoff
     records.
   - **Fix:** Either delegate metadata assignments to `super().__setattr__`
     or include `domain`, `frame`, `value_schema`, and `provenance` in the
     sealed-name guard. Add a test for rebinding and nested mutation of every
     public metadata field.
   - **If we skip it:** A caller can mutate the field's audit declaration
     without changing its actual geometry, so serialized/replayed results can
     no longer be trusted.

3. **Duplicate record ids and duplicate owners are accepted** (`features/free_space_field.py:136-159`)
   - **What this is:** The constructor checks only whether owners overlap
     across prior records; it never tracks record ids, and it does not reject
     duplicate owners within one record.
   - **Problem:** Two records with the same id and disjoint owners, or one
     record with `represented_source_ids=("a", "a")`, both build a valid field
     and return `ESTABLISHED, True`. Reproduction with two same-id records
     (`same` covering owners `a` and `b`) and with one record containing
     `("a", "a")` returns `FieldStatus.ESTABLISHED`, not `INVALID`.
   - **Fix:** Track `record_ids` and reject any repeated id. Require
     `len(set(raw_owners)) == len(raw_owners)` before adding owners to the
     global set. Keep the existing cross-record overlap rejection.
   - **If we skip it:** Conflicting or duplicated handoff data can silently
     produce an apparently qualified occupancy result and violate exact-once
     owner accounting.

4. **Selected-record provenance is dropped from samples** (`features/free_space_field.py:174-175,238-277`)
   - **What this is:** `representation_provenance` is stored in
     `_occupancy_shapes` as `record_provenance`, but that value is never used
     when building `FieldSample`.
   - **Problem:** A record carrying
     `{"representation_identifier": "GeneratedProxy", "source_hash": "abc"}`
     produces a sample whose provenance has algorithm/schema/query/lattice
     facts but no `source_hash` or representation provenance. The constructor
     accepts the source audit data and then loses it at the public sample
     boundary.
   - **Fix:** Merge the provenance of every intersecting selected record into
     the sample provenance, retaining record id, representation status,
     representation provenance, and represented owner ids. For an empty or
     unknown result, include the relevant handoff provenance that explains why
     the result was qualified or refused. Keep the merge immutable and
     deterministic; reject conflicting values rather than silently choosing
     one.
   - **If we skip it:** A result cannot be traced back to the selected
     representation or source artifact, defeating the field's audit contract.

## Should Fix

5. **The initial red draft's real-view coverage used a passthrough view**
   (historical finding; current `test/test_free_space_field.py:290-307`)
   - **What this is:** The initial draft mixed synthetic records with a
     dictionary passthrough. It did not prove the `NeutralSceneV2` construction
     path.
   - **Problem:** That draft could stay green while the actual selected-record
     shape or unresolved-owner handoff drifted.
   - **Fix:** Add one small fixture using the existing scene helpers and
     `analysis_scene_view`, then pass its `physical_occupancy` and unresolved
     ids directly into the constructor. Assert furniture and non-furniture
     mass, exact-once represented owners, and preserved source provenance.
     Keep the existing synthetic geometry tests for edge cases.
   - **If we skip it:** The unit suite can stay green while the real handoff
     shape or resolver status mapping drifts.

## Verification

I ran one targeted `pixi run python -` reproduction covering the five findings:

- positive domain sliver plus `tolerance=0.2` returned `OUTSIDE`;
- `domain`, `frame`, and `provenance` rebinding all succeeded;
- duplicate record id and duplicate owner both returned `ESTABLISHED, True`;
- record `source_hash` was absent from `sample.provenance`;
- the current tests use synthetic records rather than `analysis_scene_view`.

No production code, tests, or architecture documents were changed by this
review. I did not run the full 74-test suite.

## Verdict

**Verdict: fix 1, 2, 3, and 4 first.** Finding 5 is a focused test gap that
should be closed before claiming the real handoff contract is verified.

Not checked: performance, full-suite status, evaluator promotion, and live
IFC/Blender paths. Those remain outside this review.

## Targeted Recheck

The implementation was rechecked after the repair agent's changes. The four
original blockers are resolved:

- A positive-area sliver with `tolerance=0.2` now returns `ESTABLISHED`; the
  implementation uses `eligible.area <= 0.0`, so a linear tolerance is not
  compared with an area.
- Rebinding `field.provenance`, `field.domain`, or `field.frame` now raises
  `AttributeError`; the sealed subclass delegates through `super().__setattr__`.
- Duplicate record ids and duplicate represented owners now return
  `INVALID`.
- Selected-record `representation_provenance` now appears in
  `sample.provenance["selected_records"]`.

The real-view gap is also resolved in scope. The current tests import
`analysis_scene_view`, build scenes through the existing `_scene` helper
(which returns `NeutralSceneV2`), and pass the resulting
`physical_occupancy` plus
`view["_analysis_view"]["physical_occupancy_unresolved_source_ids"]` into the
field. The targeted command
`pixi run pytest test/test_free_space_field.py -k "real_view" -q` passed
`4 passed, 58 deselected`.

### Final ruling

**No blocker remains in this review scope.** The historical findings above are
retained for audit history; all five are resolved by the current implementation
and focused tests. I did not run the full suite or alter code, tests, or Git
state.
