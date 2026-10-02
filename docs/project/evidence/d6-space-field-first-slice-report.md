# D6 Space Field First Slice — Diagnostic Probe Report

**Date:** 2026-09-30  
**Status:** final SVG legend-layout repair completed; diagnostic evidence ready for space-field design review; no production implementation authorized.

## Scope

This slice compares a small exact-rectangle oracle with a uniform multi-resolution 2D sampling probe. It checks synthetic axis-aligned fixtures, explicit missing-domain propagation, a centerline sampled free-run profile, and an explicitly unsupported rotated-rectangle boundary fixture.

The probe does not choose a production resolution, classify corridor/activity roles, infer authored furniture membership, or claim psychological validity. The SVG renders the sampled free result after obstacle subtraction; requested lattice origin and any display-only marker are distinct in JSON and legend semantics.

## Verified repository facts

- `AnalysisDomain` is an explicit scene-contract record with `geometry_refs`; `NeutralSceneV2.analysis_domain` may be absent.
- Existing neutral-scene views exclude selected domain support geometry from physical occupancy and expose explicit domain availability.
- Existing spatial-grid code is a sampling backend for occupancy/reachability and already documents that the grid is a computational approximation, not the semantic unit.
- Existing architecture records require negative-space topology to be `not_available` when no explicit domain exists.
- Existing project state contained many unrelated untracked handoff/evidence files; they were preserved.

## Representation comparison

| Representation | Strength | Boundary | Decision for this slice |
|---|---|---|---|
| Exact/vector geometry | Preserves source boundaries and holes when the geometry is valid; independent topology oracle | Requires a geometry-capable implementation and validity handling | Use as the oracle concept, not implemented as a new production dependency |
| Uniform multi-resolution grid | Small, reproducible, standard-library probe; supports area/connectivity sensitivity checks | Resolution and origin can change area and topology; no curved/oblique support here | Use for diagnostic sampling only |
| Adaptive grid | Could spend samples near boundaries and bottlenecks | Refinement/stitching policy adds another source of uncertainty | Defer until uniform sensitivity is characterized |

## Fixtures and independent oracles

- `wide_space_narrow_neck`: exact one-component domain with a 1.5-unit neck; corrected exact free area is `33.0` (`96.0 - 63.0`).
- `uniform_spacing_gap_jump`: exact one-component domain with four known rectangular obstacles and known union area.
- `disconnected_domain`: two disjoint domain rectangles; exact component count is two.
- `subcell_gap_origin_sensitive`: historical coordinates retained; independent geometry has three continuous free components (left strip, 0.8-unit gap, right strip). The earlier one-component note is superseded by the oracle-repair correction.
- `missing_domain`: no explicit domain; expected state is `not_available`.
- `rotated_rectangle_boundary`: independent area oracle is computed (`46.0`), while the rectangle sampler returns `unsupported` for every run rather than fabricating raster results.

The oracle values are authored from fixture construction and are not copied from sampled output. The script independently recomputes rectangle area and rotated-rectangle area, asserts those values against declared oracles, asserts component counts only for stable fixtures, records topology disagreement for the sensitivity fixture, and asserts `not_available`/`unsupported` states explicitly.

## Diagnostic result

The probe completed with `diagnostic_pass`, meaning the declared assertions and status checks executed successfully. It does **not** mean sampled topology matches the exact oracle. Results are in [space_field_probe_results.json](D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field\space_field_probe_results.json). The reproducible script is [run_space_field_probe.py](D:\PROJECTS\understandOtherPackage\order_analyzer\scripts\design\space_field\run_space_field_probe.py); it accepts `--output-dir` and confines generated outputs to that directory.

The current result supports only these observations:

1. A coarse uniform grid can be exercised against independent area/topology oracles without making a semantic width claim.
2. The historical subcell fixture exposes area and topology sensitivity, but its corrected exact topology is `3` components; the earlier one-component interpretation is withdrawn. A separate one-component bottleneck control is now required for neck-loss observations.
3. A sampled centerline profile can report free-run widths as diagnostic evidence. It is not Euclidean clearance, route width, or a true bottleneck width. For the neck fixture, the source geometry supplies a 1.5-unit reference neck width; sampled runs remain separate.
4. Explicit domain absence can be propagated without substituting the source canvas or obstacle extent.
5. The final SVG legend now fits within the canvas and distinguishes the requested lattice origin from a display-only edge marker. This is a presentation/reproducibility repair only; it does not validate the space-field model.

## Limitations and deferred fixtures

Curved and oblique boundaries, holes, openings, wall permeability, rotated grids, multi-size obstacles, full distance fields, and adaptive refinement were not executed. Rotated rectangle input is represented only by an independent area oracle and explicit `unsupported` sampler status. The sampled profile is not a route-width oracle or role classifier. Memory measurement is unavailable in the portable standard-library probe; runtime is recorded. No real IFC geometry was used, so no IFC capability is claimed. The SVG is an inspection aid, not a validation certificate.

## Skills actually used

- `speckit-assess-intake`, `speckit-assess-define`, `speckit-assess-research`, `speckit-assess-shape`, `speckit-assess-decide`: inspected for applicability; not executed because this repository lacks the required `.specify/` assessment structure and the handoff is a bounded design task, not a product assessment.
- `experimental-design`: used to keep fixture construction, independent oracle, resolution/origin factors, and acceptance assertions explicit.
- `scientific-critical-thinking`: used to separate observed diagnostic output from production or psychological claims and to record alternative explanations and missing evidence.
- `scientific-visualization`: used to keep source geometry, sampled cells, free-space encoding, metadata, and diagnostic limitations visible in a self-contained SVG.
- `verification-before-completion`: no readable project-local `SKILL.md` was found at the advertised path; equivalent verification was performed manually with rerun, SHA-256 manifest, and diff-scope audit.

## Artifact manifest

See [artifact_manifest.json](D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field\artifact_manifest.json). It hashes the probe script, result JSON, and visualization SVG; artifact paths are relative to the selected output directory except for the source script identity. Existing dirty/untracked content was not included or modified.

Visualization: [space_field_visualization.svg](D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field\space_field_visualization.svg). It shows source domain/obstacles and obstacle-subtracted sampled free cells. JSON records `requested_lattice_origin`; a display-only edge marker is explicitly not the sampling origin.

## Final SVG repair verification

- Default probe: `pixi run python scripts/design/space_field/run_space_field_probe.py --output-dir outputs/design/space_field` — exit 0, `diagnostic_pass`.
- Temporary probe: `pixi run python scripts/design/space_field/run_space_field_probe.py --output-dir <temporary-directory>` — exit 0; all three outputs remained in the caller-selected directory.
- Deterministic payload comparison: equal after removing runtime and output-path fields.
- SVG XML parse: passed.
- Actual SVG-to-PNG render with `svglib`/ReportLab: passed; the full legend and bottom limitation text were visible without right or bottom clipping.
- SVG geometry audit: 135 sampled-cell rectangles, 5 displayed obstacle rectangles, 0 positive-area intersections; sampled cells stayed within the displayed domain bounds. The legend swatch was excluded by its explicit `legend-swatch` class.
- SVG semantics text audit: passed for requested lattice origin, display-only marker distinction, and sampled-free-run limitation.
- Manifest SHA-256: source script, JSON, and SVG matched the regenerated manifest.
- `git diff --check`: passed. Scope remained limited to the permitted design/evidence/output paths; no production files were touched.

This final change is only a legend/canvas layout repair. It does not turn diagnostic results into model validation, does not remove the persistent sampled-topology distortion, and does not freeze a production resolution or semantic threshold.

## Review boundary

**Approved in this slice:** a bounded diagnostic probe, independent rectangle and rotated-area oracles, sensitivity fixture, sampled free-run diagnostic, clipped/legend-bearing visualization, explicit `not_available`/`unsupported` states, and status/limitation record.  
**Still requires owner decision:** exact/vector geometry backend, grid/adaptive representation, convergence criteria, full clearance/distance/bottleneck evidence schema, and any future block or graph extraction.  
**Unavailable or failed inputs:** no explicit real IFC analysis-domain sample was used; portable process-memory measurement was unavailable.  
**Diagnostic only:** all numeric errors, component counts, and sensitivity observations.

**STOP FOR SPACE FIELD DESIGN REVIEW**

## Oracle repair correction — 2026-10-01

The historical `subcell_gap_origin_sensitive` coordinates are unchanged. Independent geometry gives free area 19.2 and three components, so the previous one-component oracle and “persistent fine-grid distortion proves an implementation defect” interpretation are withdrawn. A separate `connected_bottleneck_opening` fixture carries the one-component neck intent.
