# Distance module spec grill review

**Final disposition, 2026-11-03: GO for implementation readiness.** The owner accepted the corrected arithmetic contract before spec edits: NetworkX 3.6.1 scalar labels are authoritative; deterministic tight-predecessor recovery resolves ties without a second normal-path Dijkstra; component recomposition writes an explicit binary64 residual/ULP diagnostic rather than requiring impossible reassociation equality. The guarded probe passed 72 nonspatial graph-order/count/lineage checks and validated real S4 confirmation/source bindings. The input adapter, full-pair runtime/memory and visualization are implementation tasks; requiring their completed outputs before readiness was a sequencing error. [Readiness evidence](distance-readiness-2026-11-03.md) and the [implementation plan](../../superpowers/plans/2026-11-03-group-distance-module-implementation.md) supersede the historical NO-GO below. No production distance implementation or real route result is claimed.

Date: 2026-11-03  
Scope: owner self-review of `2026-11-02-group-distance-module-design.md` and checklist `.17`  
Decision: **NO-GO for readiness; GO for the next adapter-contract probe**

## What was checked

- Fixed group centroid semantics for concave, holed and disconnected group unions.
- Free-space access-cell qualification and the observed/optimistic state split.
- Deterministic shortest-path selection independent of backend predecessor order.
- Cell, edge, group and occupancy source lineage for selected routes.
- S4 confirmed-domain handoff, camera `AnalysisPlane`, grid identity and same-scene input binding.
- Full 37-group / 666-unordered-pair coverage, index bijection and route-view coverage.
- Source-batched memory behavior and bounded backend/search fallback.
- `invalid`, `not_available`, `outside`, `partial`, `computed`, `unknown` and `unreachable` precedence.

## Findings and disposition

| Finding | Disposition | Evidence / required gate |
|---|---|---|
| Union centroid can fall outside a concave, holed or disconnected group. | Resolved in the design. Keep one fixed union centroid; do not snap, split or invent a representative point. Add audit fields for area, component count, centroid relation and source ref. | Distance spec §§3.2 and 5. |
| NetworkX tied predecessors depend on insertion order. | Still an implementation gate. The spec now requires canonical `CellKey`, `AccessKey`, `EdgeKey`, tight-edge recovery, conditional-count/path-key ordering, and a second project-owned recovery search when the backend cannot expose the tight relation. | Distance spec §4.4; backend probe. |
| Selected route status and source lineage could be lost after a backend search. | Resolved as an adapter contract. Selected cells/edges must carry query state and source refs; unrelated unknown/conditional cells must not contaminate the pair; optimistic lower-bound unknown dependencies are separate. | Distance spec §4.4 and §5. |
| S4 manifest points to `domain_result.json`, but that file is `not_available` with no analysis domain. | **Blocking input risk.** The adapter must consume `s4_confirm_result.json` active `analysis_domain`/`domain_geometries` and cross-check the confirmed manifest bindings. A mismatch returns `NOT_AVAILABLE`; old `ifc-world-plan` artifacts are not S4 evidence. | Verified with a Pixi JSON probe on `run_20261102T210601Z`; distance spec §3.1; plan `.17.1c`. |
| `.superpowers/sdd/.../s4-confirmation-audit.md` still described S4 as unconfirmed. | Marked the note **SUPERSEDED** and linked the current confirmed payload; historical audit text is retained for traceability and cannot gate current distance input. | Updated historical audit note; current manifest/result pair remains the authority. |
| A plain Pixi invocation imports user-site NetworkX 3.7 before the locked package. | **Reproducibility gate added.** All probes must set `PYTHONNOUSERSITE=1` and record interpreter/module paths; unguarded probe output is invalid. | Backend probe and algorithm package review updated; locked Pixi package is NetworkX 3.6.1. |
| Existing `FreeSpaceField` checks only `domain_id/frame` and requires `plane=None`; it does not bind camera plane, grid orientation or query fingerprint. | **Blocking adapter seam.** The design now requires an immutable `AnalysisPlane + GridDescriptor + FieldQuery/query_context + occupancy/unresolved-source fingerprint` handoff from the same scene-view. | Distance spec §3.1; plan `.17.4a`. |
| 37 groups imply 666 unordered pairs. | Resolved as a measurable acceptance invariant. Build `expected_pair_ids = combinations(sorted(group_ids), 2)` and require bidirectional set equality, one JSON observation and one route-view locator per pair, including no-route states. | Distance spec §6. |
| Retaining all source distance fields may exceed memory. | Resolved as a plan requirement. Process one source at a time per graph mode, release its distance/predecessor state after target observations, and record node/edge counts, source-run count, peak memory and runtime. | Distance spec §6; plan `.17.4a`. |
| State precedence is specified, but the required-query scope was implicit. | **Resolved as a pair-local dependency rule.** Global handoff failures affect all dependent pairs; cell-level invalid/unavailable inputs affect only the source-target dependency closure and are never rewritten as occupied/free/unknown. | Distance spec §5. |
| External package search could expand without a stop condition. | Resolved. First finish the current Pixi contract probe; search GitHub/Consensus only if every current candidate fails a named contract gate, then return to the same comparison table. | Algorithm package review; plan `.17.4a`. |

## Readiness verdict

The semantic design is coherent enough to continue with the input/grid adapter and deterministic recovery probe. It is **not ready for distance implementation or IFC visualization** because the backend adapter proof, canonical arithmetic recovery, S4 input handoff implementation, full-pair resource measurement, and artifact reconciliation are still unverified. Keep `.17.4a`, `.17.8` and `.17.9` unchecked.

The user does not need to review the text spec at this point. After a real IFC run produces the S4 analysis-plane matrix and route views, request a visual review of those artifacts; the visual review is a separate acceptance gate and cannot be replaced by fixture tests or a stale plane. The readiness gate is owner/independent text acceptance before implementation; visual review follows real IFC output.

## Verification commands

```powershell
jj status
jj log -r '::@' -n 6 --no-graph
$env:PYTHONPATH='.'
pixi run python -c "import networkx, numpy; print(networkx.__version__, numpy.__version__)"
pixi run python -c "import json; from pathlib import Path; p=Path('outputs/design/wall_domain_camera_prerequisite/run_20261102T210601Z'); m=json.loads((p/'s4_confirmed_manifest.json').read_text(encoding='utf-8')); r=json.loads((p/'s4_confirm_result.json').read_text(encoding='utf-8')); d=json.loads((p/'domain_result.json').read_text(encoding='utf-8')); assert m['status']=='confirmed' and r['status']=='active' and r['handoff_executed'] is True and d['status']=='not_available' and d['analysis_domain'] is None; print('S4 handoff audit passed')"
```

No distance code, dependency, simulated scene, simulated route or IFC result was created by this review.
