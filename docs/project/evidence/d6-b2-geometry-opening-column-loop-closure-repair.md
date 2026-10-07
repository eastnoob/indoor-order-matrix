# D6 B2 Geometry, Opening, and Column Loop-Closure Repair

- Date: **2026-10-07**
- Evidence class: **bounded synthetic design evidence**
- Owner decision basis: commit `9b50bb1f44c0ae7dc2807c17da084d1ab8163393`
- B2: **REVISE**; B5: **narrow APPROVE** for candidate-polygon validity/source-component separation only
- Production implementation: **not approved**
- Real IFC: **not verified; not run**
- Blender: **not run**

## Purpose and boundary

This repair supplies the bounded fixture/oracle evidence requested for B2. It keeps the physical occupancy role of every column separate from conditional boundary support, distinguishes exact endpoint contact from a nonzero fixture gap without selecting a production tolerance, and separates opening source facts from door assumptions. Candidate polygon validity and source-component connectivity are reported as independent observations under the narrow B5 decision.

The probe does not build or promote an AnalysisDomain, subtract an opening, produce free-space, infer a door's observed state, or claim clearance, connectivity for navigation, walkability, or route truth. All geometry and status labels are synthetic, local diagnostics; they are not a new public enum or production behavior.

## Existing helper and evidence limits

The probe imports `_topology_status()` from `scripts/design/space_field/run_boundary_construction_experiment.py`. That existing design helper counts connected components and closed endpoint-degree loops by exact endpoint coordinate equality. It is reused without modification. It does not resolve segment intersections, near-coincident geometry, physical contact, or production tolerance. The exact-contact and near-contact results therefore show only that the stated synthetic endpoints produce different helper outputs.

The owner decision was read from the committed overlay with `git show 9b50bb1f44c0ae7dc2807c17da084d1ab8163393:docs/project/evidence/d6-contract-closure-owner-decision.md`; that path is absent from the current checkout. The optional development notebook and contract-package markdown paths named in the earlier handoff were also absent from this checkout, so no claims rely on having read those copies. The available IFC input contract, independent geometry review, column audit, hard-column comparison, pairwise evidence, and the committed owner overlay were inspected.

## Fixture outcomes

| Fixture | Synthetic condition | Source topology | Candidate polygon | Opening/column distinction |
|---|---|---|---|---|
| B2-F01 | Interior column in a closed wall loop | One closed component | Valid | Column stays physical occupancy; no boundary-support segment |
| B2-F02 | Column face shares exact endpoints with two wall ends | One closed component | Valid | Conditional support is recorded for this fixture only; column remains occupied geometry |
| B2-F03 | Column face has a `0.125` fixture-unit gap at each end | Two components; partial | Valid | No boundary support; the gap is illustrative, not a tolerance value |
| B2-F04 | Hosted boundary opening with usable geometry references | One open component; partial | Not available | Host and geometry refs qualify for review only; no subtraction is performed |
| B2-F05 | Door shown under the default-closed scenario assumption | One closed component | Valid | Assumption is not a source fact and is not converted into opening or traversal evidence |
| B2-F06 | Missing relation, unresolved host, and conflicting host references | Not available | Not available | Local observations remain `not_available`, `invalid`, and `conflict`; subtraction refused |
| B2-F07 | Malformed geometry and unsupported representation variants | Not available | Not available | Local observations remain `invalid` and `unsupported`; subtraction refused |
| B2-F08 | Valid polygon with disconnected source segments | Two components; partial | Valid | Candidate validity does not imply source connectivity |
| B2-F09 | Invalid bow-tie polygon with a closed connected source ring | One closed component | Invalid | Source connectivity does not imply candidate validity |

The generated JSON preserves source-segment identities, occupancy roles, contact evidence, opening host/geometry provenance, candidate validity, source component count/status, and the diagnostic refusal for every fixture. The `summary.svg` is a status-card overview only; it does not depict source geometry or an IFC result.

## Status and decision boundary

The probe uses the existing helper's local `computed`, `partial`, and `not_available` results and records opening-specific `invalid`, `conflict`, `unsupported`, and `diagnostic_only` observations. These labels are scoped to this synthetic evidence and do not establish a unified public status contract. Real IFC remains `not_verified` because no real IFC geometry was run.

The evidence supports only these bounded distinctions:

- A column remains in physical occupancy whether or not a diagnostic boundary-support face is present.
- Exact shared endpoints plus a single closed diagnostic component are distinguishable from the fixture's nonzero gap. No production tolerance is selected.
- A true opening relation with host and usable geometry refs is different from a door under a closed scenario assumption. Even the qualified opening fixture is not subtracted.
- Missing, unresolved, conflicting, malformed, and unsupported opening evidence remain distinguishable and refuse subtraction.
- Candidate polygon validity and source-component connectivity/status remain independent.

The evidence does **not** close B2 by itself. B2 remains `REVISE` until an independent review accepts the repaired contract evidence. It does not authorize geometry implementation design beyond the stated guardrails, production code, IFC/UI integration, a selector, backend, threshold, resolution, route width, or Bayesian/ML model.

## Commands and validation

Commands actually run:

1. `pixi run python scripts/design/space_field/run_d6_b2_geometry_opening_column_loop_closure.py --output-dir outputs/design/d6_b2_geometry_opening_column_loop_closure/run_001` — exit **0**, 9/9 fixture assertions passed.
2. PowerShell created the fresh temporary directory `%TEMP%\d6_b2_geometry_opening_column_loop_closure_20261007_run_002`, then ran the same probe with `--output-dir "$temp"` — exit **0**, 9/9 fixture assertions passed.
3. Primary and temporary `results.json` SHA-256 values matched byte-for-byte: `47f4bf594874f4cf6ec7f973086dd3737884409484563d3ac3325656aaa8ba19`.
4. Primary and temporary `summary.svg` SHA-256 values matched byte-for-byte: `f826956401df47afc6f405ecbc7c9a03c75dcc6f2a97f4b9f377154cd9098dab`.

JSON, SVG/XML, manifest hash, scope, and whitespace checks are recorded in the companion manifest and the final handoff. No pytest, real IFC geometry, Blender, or unrelated historical experiment was run.

## Declared repair files

- `scripts/design/space_field/run_d6_b2_geometry_opening_column_loop_closure.py`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/fixtures.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/run_001/results.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/run_001/provenance.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/run_001/summary.svg`
- `docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-repair.md`
- `docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-repair-manifest.json`
