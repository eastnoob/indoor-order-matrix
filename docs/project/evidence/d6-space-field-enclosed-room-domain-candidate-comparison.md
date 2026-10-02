# D6 封闭房间 / AnalysisDomain candidate comparison table

| Case | Class | Candidate id | Domain/evidence status | Priority | Selected |
|---|---|---|---|---|---|
| `positive_ifc4_explicit_ifcspace` | A | candidate:ifcspace:room | partial/available | explicit IFC | `candidate:ifcspace:room` |
| `negative_missing_domain` | C | candidate:diagnostic:negative_missing_domain | not_available/missing | diagnostic-only | `none` |
| `negative_domain_missing_geometry` | C | candidate:ifcspace:missing-geometry | not_available/missing | explicit IFC | `candidate:ifcspace:missing-geometry` |
| `negative_opening_host_relation_broken` | A/B evidence conflict | candidate:ifcspace:broken-opening-host | partial/partial | explicit IFC | `candidate:ifcspace:broken-opening-host` |
| `automatic_closed_wall_shell` | B | candidate:auto:automatic_closed_wall_shell | computed/available | automatic candidate | `candidate:auto:automatic_closed_wall_shell` |
| `single_large_room` | B | candidate:auto:single_large_room; candidate:user:closed-curve | computed/available; computed/available | automatic candidate; user-authored | `candidate:user:closed-curve` |
| `multi_shell_conflict` | B | candidate:auto:multi_shell_conflict | ambiguous/available | diagnostic-only | `none` |
| `open_boundary` | B | candidate:auto:open_boundary | partial/available | diagnostic-only | `none` |
| `cross_floor` | B | candidate:auto:cross_floor | invalid/available | diagnostic-only | `none` |

状态语义：`computed` 可作为候选结果；`partial` 保留 source/intent 但不能作为无条件合格 domain；`ambiguous` 不选；`invalid` 不选；`not_available` 表示没有合格 domain。`automatic candidate` 永远需要用户确认后才可成为 accepted/authored domain。
