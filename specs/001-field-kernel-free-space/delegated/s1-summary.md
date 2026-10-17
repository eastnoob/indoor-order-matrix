# S1 Field Record Audit Summary

## Scope

This is a design-only, read-only audit of the eight records in
`scripts/design/group_level/self_description_competition_fixtures.json`.
The temporary in-memory harness defined a minimal exact-lookup record with
`evaluate` and `evaluate_many`; it did not import `scripts.design` or add a
production `Field` implementation.

## Command

```powershell
$code = @' ... temporary in-memory DesignFieldRecord/DesignField audit ... '@
$json = $code | pixi run python -
```

The harness was run twice in the same process from the same fixture bytes and
compared using sorted, compact JSON canonicalization.

## Results

- Fixtures audited: **8/8**
- Per-fixture scalar/batch equivalence: **8/8 passed**
- Source-id and provenance retention: **8/8 passed**
- Canonical replay equality: **passed**
- Replay SHA-256 (both runs):
  `ecd60c712f42d6014d7afa62d489dc5e9eb0a283ca7d7bcf8571ce460a535822`
- Fixture SHA-256:
  `8a9253de9294138292e2a47463b847eaef96152793826dd00965b7d95de9b74d`

Observed statuses were `established`, `conditional`, `invalid`,
`not_available`, and `outside`. `unknown` was not present in these eight
fixtures; no synthetic unknown value was introduced.

## Files

- `s1-field-record-audit.json`: full explicit field records, samples,
  provenance, status coverage, assertions, and replay hashes.
- `s1-summary.md`: this concise report.

## Blocked / Owner Decisions

- Public name/location remains unfrozen: `Field` versus internal
  `SpatialField` protocol.
- Status precedence remains unfrozen for combinations such as invalid geometry
  plus missing domain.
- This audit does not certify a production API, free-space score, clearance,
  complete occupancy, or B3 promotion.

No production files, tests, fixtures, exports, or architecture documents were
modified.
