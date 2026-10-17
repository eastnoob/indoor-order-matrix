# D6 B2 Geometry, Opening, and Column Loop-Closure Repair v2 Independent Review

- Review date: 2026-10-07
- Reviewed commit: `82d08fe` (`docs: add D6 B2 uncertainty propagation evidence`)
- Evidence class: bounded synthetic design evidence
- Review mode: read-only independent verification
- Real IFC: not run / not verified
- Blender: not run
- Production implementation: not approved

## Scope

This review checks whether repair-v2 adds and propagates the two missing uncertainty cases identified by the prior review, while preserving the original nine-fixture evidence. It does not validate a production geometry algorithm, tolerance policy, AnalysisDomain selector, free-space backend, route computation, real IFC adapter, or Blender integration.

## Source material read

- `AGENTS.md`
- `docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-repair-v2.md`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/fixtures_patch.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/results.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/provenance.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/summary.svg`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/artifact-manifest.json`
- original `fixtures.json`, `run_001` results/SVG, and the prior B2 repair record
- commit `82d08fe` and its parent

## Commands and exit codes

All commands ran from `D:\PROJECTS\understandOtherPackage\order_analyzer`.

1. Original nine-fixture rerun in a fresh temporary directory:

   ```powershell
   pixi run python scripts/design/space_field/run_d6_b2_geometry_opening_column_loop_closure.py --output-dir C:\Users\tianf\AppData\Local\Temp\d6_b2_uncertainty_review_20261007111027901\original
   ```

   Exit code: **0**; 9/9 fixture assertions passed.

2. Repair-v2 rerun in a separate fresh temporary directory:

   ```powershell
   pixi run python outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py --output-dir C:\Users\tianf\AppData\Local\Temp\d6_b2_uncertainty_review_20261007111027901\repair_v2
   ```

   Exit code: **0**; 11/11 cases passed, including 2 uncertainty cases.

3. Deterministic comparison and artifact verification:

   - Original rerun `results.json`: byte-identical to `run_001`, SHA-256 `47f4bf594874f4cf6ec7f973086dd3737884409484563d3ac3325656aaa8ba19`.
   - Original rerun `summary.svg`: byte-identical to `run_001`, SHA-256 `f826956401df47afc6f405ecbc7c9a03c75dcc6f2a97f4b9f377154cd9098dab`.
   - Repair-v2 `results.json`, `provenance.json`, and `summary.svg`: byte-identical to the committed artifacts.
   - JSON parsing and SVG/XML parsing: passed.
   - Manifest bytes/SHA-256 checks for all six declared artifacts: passed. The manifest intentionally excludes its own self-hash.
   - Critical uncertainty assertions: passed.

4. Commit scope audit:

   ```powershell
   git diff 82d08fe^ 82d08fe --name-only
   ```

   Exit code: **0**. The commit contains only the repair-v2 evidence record, manifest, patch, probe, results, provenance, and summary SVG. No `features/`, `adapters/`, public API, formal tests, dependency, IFC, or user Blender path was changed.

## Findings

### Uncertainty fixtures

The patch adds exactly two append-only fixtures, `B2-U01` and `B2-U02`, and declares the original fixture SHA-256 and count. The original nine definitions remain unchanged.

### Uncertain column-wall contact

`B2-U01` preserves both conflicting contact observations and their source IDs. The column remains included as physical occupancy. The result explicitly sets conditional boundary support to `false`, local diagnostic state to `conflict`, source topology to `partial` with two components, formal domain promotion to `refused`, and downstream free-space/route claims to `not_evaluated`.

The result still lists the uncertain face in `candidate_segment_ids`; the separate boolean `conditional_support_in_this_fixture=false` and refusal fields make clear that this is a diagnostic candidate record, not granted production boundary support. This is acceptable for the bounded evidence, but the distinction must remain explicit in any later implementation design.

### Conflicting opening host and geometry

`B2-U02` preserves both host references, both geometry references, and all uncertainty source IDs. The host wall remains occupied, the opening candidate is not subtracted, local state remains `conflict`, candidate polygon status is `not_available`, domain promotion is refused, and downstream free-space/route claims remain `not_evaluated`.

### Separation of validity and connectivity

The 9 original fixtures retain independent `candidate_polygon_validity` and `source_components` fields. The rerun also rechecks the established distinctions for missing, invalid, conflict, unsupported, diagnostic-only, and partial observations. No unified public status enum is introduced.

### Overclaim and scope

The evidence and provenance explicitly identify this as synthetic design evidence. They state `real_ifc=not_verified_not_run`, `blender=not_run`, and `production_code_modified=false`. No production policy, tolerance, selector, free-space result, route result, or Bayesian/ML claim is made.

One wording issue remains: the report says “seven artifacts listed above,” while the artifact list has six declared files and the manifest itself is the seventh committed path but is intentionally excluded from its file list. This does not affect the hashes or evidence, but should be corrected in a future documentation cleanup.

## Limitations

- No real IFC or Blender execution was performed, by instruction.
- The reused `_topology_status` helper is an exact-endpoint diagnostic, not a production geometry algorithm or tolerance policy.
- The uncertainty cases demonstrate refusal and provenance propagation only; they do not establish a production boundary/opening policy.
- The summary SVG is a diagnostic status summary, not a geometric validation render.

## Decision

**ACCEPT LIMITED DESIGN EVIDENCE**

The missing uncertainty-propagation evidence is present, deterministic, and bounded. The repair may proceed to a bounded implementation-design review only. It does not authorize production implementation, real IFC integration, Blender validation, status-enum publication, selector/tolerance decisions, free-space computation, route computation, or merge.

STOP FOR D6 B2 UNCERTAINTY PROPAGATION REPAIR-V2 INDEPENDENT REVIEW
