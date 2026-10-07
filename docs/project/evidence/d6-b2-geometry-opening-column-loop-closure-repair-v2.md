# D6 B2 Geometry, Opening, and Column Loop-Closure Repair v2

- Date: **2026-10-07**
- Evidence class: **bounded synthetic design evidence**
- Owner decision basis: commit `9b50bb1f44c0ae7dc2807c17da084d1ab8163393`
- Prior repair: commit `f7f71a303a6775b958c299035c650350ed2eba7a`
- Independent review: commit `02d6eda2c9f2e8179373849189bb074be4524dd5`
- B2: **REVISE pending independent review of this append-only evidence**
- Production implementation: **not approved**
- Real IFC: **not verified; not run**
- Blender: **not run**

## Purpose and boundary

This record adds the uncertainty-propagation evidence missing from the accepted nine-fixture repair. The original nine fixture definitions, original results, original repair record and manifest, independent review, owner decision, and contract source remain unchanged. The repair-v2 patch adds two synthetic fixture definitions; its separate runner reruns all nine original cases through the existing probe and appends the two new observations.

The runner reuses `_observe_fixture()` and `_topology_status()` without editing either implementation. Contact uncertainty is diagnostic input, not a production tolerance. Opening uncertainty is not resolved by selecting a host or geometry representation. Neither case promotes an AnalysisDomain, subtracts opening geometry, evaluates free-space, or makes a route claim. Local labels reuse existing vocabulary and do not establish a public status enum.

## Added uncertainty fixtures

| Fixture | Uncertain input and provenance | Propagated result |
|---|---|---|
| `B2-U01` | Two source-identified geometry observations disagree about column-wall contact. The contact fact remains unresolved, and both source IDs remain in the result. | The column remains physical occupancy. Its conditional boundary face is not support; diagnostic state is `conflict`, source connectivity is `partial` with two components, the candidate polygon remains independently `valid`, domain promotion is refused, and downstream free-space/route claims are `not_evaluated`. |
| `B2-U02` | Host relations disagree between `wall-A` and `wall-B`; geometry references disagree between valid and malformed observations. All relation and geometry source IDs are retained. | The host wall remains occupied and the opening candidate is not subtracted. The existing local state is `conflict`; source connectivity is independently `computed` with one component, candidate polygon is `not_available`, domain promotion is refused, and downstream free-space/route claims are `not_evaluated`. |

The existing nine cases continue to distinguish missing relation (`relation_state=missing`, local `not_available`), malformed or unresolved evidence (`invalid`), partial source connectivity (`partial`), contradictory evidence (`conflict`), unsupported representation (`unsupported`), review-only evidence (`diagnostic_only`), and real-IFC evidence (`not_verified`). These remain local observations, not a frozen status contract.

## Artifacts

- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/fixtures_patch.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/results.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/provenance.json`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/summary.svg`
- `outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/artifact-manifest.json`
- `docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-repair-v2.md`

The manifest records byte counts and SHA-256 for every declared artifact except itself. It does not claim a real IFC, Blender, production, or route-validation result.

## Commands and validation

Commands below ran from the repository root in PowerShell. Exit codes refer to the completed command.

1. Re-run the original nine-fixture probe into a fresh temporary directory:

   ```powershell
   $tempDir = Join-Path $env:TEMP 'd6_b2_geometry_opening_column_loop_closure_20261007_repair_v2_original_rerun'; if (Test-Path -LiteralPath $tempDir) { throw "Temporary directory already exists: $tempDir" }; pixi run python scripts/design/space_field/run_d6_b2_geometry_opening_column_loop_closure.py --output-dir $tempDir; exit $LASTEXITCODE
   ```

   Exit **0**, 9/9 fixture assertions passed. The temporary results match the original `run_001` byte-for-byte: `results.json` SHA-256 `47f4bf594874f4cf6ec7f973086dd3737884409484563d3ac3325656aaa8ba19`; `summary.svg` SHA-256 `f826956401df47afc6f405ecbc7c9a03c75dcc6f2a97f4b9f377154cd9098dab`.

2. Run repair-v2 in its declared output directory:

   ```powershell
   pixi run python outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py --output-dir outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2
   ```

   Final run exit **0**, 9 original and 2 uncertainty fixtures asserted. An earlier development invocation exited **1** because a verifier eagerly evaluated an unused fallback key; the verifier was corrected and the final invocation above passed. Final SHA-256 values: `results.json` `9c1a6a805bb19fc7bf7cc471a61d790e9a76d9ae832e6801329446246d885c12`, `summary.svg` `fe398f9066f5d0adfc6b1413666a43b910ada052c8865ccb3294432aecbccaf0`, and `provenance.json` `83f4e2e5d93a4c5498e8ae8878f141911a2eb0d67e15b1bf035750111b236869`.

3. Fresh temporary-directory reproduction:

   ```powershell
   $tempDir = Join-Path $env:TEMP 'd6_b2_geometry_opening_column_loop_closure_20261007_repair_v2_repro'; if (Test-Path -LiteralPath $tempDir) { throw "Temporary directory already exists: $tempDir" }; pixi run python outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py --output-dir $tempDir; exit $LASTEXITCODE
   ```

   Exit **0**, 11/11 fixture assertions passed. Primary and temporary `results.json`, `provenance.json`, and `summary.svg` are byte-identical with the hashes listed above.

4. The probe asserts preservation of each uncertainty source and affected fact, retained occupancy, withheld column support, no opening subtraction, refused domain promotion, and downstream `not_evaluated`. It also reruns the original nine oracles and checks the status distinctions listed above. These assertions passed in both repair-v2 runs.

5. JSON and SVG/XML parsing, manifest byte-count/SHA-256 checks, bounded whitespace checks, and Git path-scope checks are recorded in the final handoff. Only the seven artifacts listed above are declared for this repair-v2 commit; no production path is included.

This evidence addresses the uncertainty-propagation gap identified by the independent review. It does not change the review outcome or authorize geometry implementation; B2 remains `REVISE` until independently reviewed.
