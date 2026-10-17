# S2 Channel Isolation Summary

Scope: read-only replay of the eight design fixtures in
`scripts/design/group_level/self_description_competition_fixtures.json` using
the existing probe-local runner. No production `Field` or evaluator code was
imported or changed.

## Result

**8/8 assertions passed.** Two consecutive canonical replays were byte
identical:

- run 1 SHA256: `c8df438eb7a47735461f58daa9b6c849c376938cef316a77b6eea94293b9dca0`
- run 2 SHA256: `c8df438eb7a47735461f58daa9b6c849c376938cef316a77b6eea94293b9dca0`

| Fixture | Assertion | Input / perturbation | Status | Evidence |
|---|---|---|---|---|
| `minority_mixed` | Soft semantic disagreement does not veto | Change `C1` label `cozy` -> `regular` | PASS | Candidate stays `computed`; semantic disagreement is recorded; geometry and occupancy are equal |
| `independent_minority` | Geometry channel survives semantic change | Change `C1/C2` labels `cozy` -> `other` | PASS | Geometry similarity `1.0 -> 1.0`; gap support `0.70211699 -> 0.70211699`; occupancy equal |
| `geometry_conflict` | Geometry mismatch remains negative evidence | Change `B` label `table` -> `chair` | PASS | Shape similarity `0.0625`; mismatch `0.9375` before and after; occupancy equal |
| `space_barrier` | Barrier is isolated from geometry | Change `W1` opening `false` -> `true` | PASS | Barrier `blocked -> opening`; status `space_conflict -> computed`; geometry and occupancy equal |
| `semantic_conflict` | Hard exclusion does not alter physical occupancy | Clear `mutual_exclusion` | PASS | Status `vetoed_mutual_exclusion -> computed`; pair geometry and occupancy equal |
| `context_reference` | Context does not invent membership | Remove context object | PASS | Status remains `computed`; context provenance `1 -> 0`; reference flag changes only; occupancy equal |
| `missing_channels` | Missing remains unavailable | Original missing domain and null label | PASS | Semantic/domain/barrier are `not_available`; no semantic negative evidence |
| `invalid_geometry` | Invalid remains distinct from missing | Original `B` size `[0,1]`, status `invalid` | PASS | Candidate `invalid`; geometry similarity `0.0`; mismatch `1.0` |

## Limits

The evidence is design-only and probe-local. It does not certify production
field behavior, free-space clearance, connectivity, live adapters, B3
promotion, opening inference, or psychological truth. Physical occupancy here
means preservation of source rectangle geometry under channel perturbation.
