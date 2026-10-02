# D6 boundary construction candidate comparison

## Controlled fixture

The controlled shell is 8 m × 6 m with 0.20 m wall thickness. All candidates
use `fixture-world-plan-z=0`, units `m`, and the same opening evidence.

| Candidate | Geometry source | Closed | Area (m²) | Relation to physical wall field | Candidate state |
|---|---|---:|---:|---|---|
| inner wall face | derived offset by half recorded wall thickness | yes | 45.240 | touches inner edge | automatic, not accepted |
| outer wall face | derived offset by half recorded wall thickness | yes | 50.840 | touches outer edge | automatic, not accepted |
| wall centerline | source wall centerline | yes | 48.000 | passes through wall field | automatic, not accepted |
| authored closed curve | user-authored points | yes | 39.960 | inside inner face; no wall-field overlap in fixture | user-confirmed, accepted |

## Topology propagation

| Case | Inner | Outer | Centerline | Authored curve | Selection |
|---|---|---|---|---|---|
| automatic closed wall shell | computed | computed | computed | not_available | provisional candidates; user confirmation required |
| multi-shell conflict | ambiguous | ambiguous | ambiguous | not_available | no selected domain |
| open boundary | partial | partial | partial | not_available | no selected domain |
| cross-floor | invalid | invalid | invalid | not_available | no selected domain |
| real IFC shadow | not_verified | not_verified | not_verified | not_verified | native inventory only |

The table is descriptive evidence, not a production selector. Wall thickness is
always retained in the independent physical wall field record.
