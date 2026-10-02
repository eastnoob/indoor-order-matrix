# D6 Space Field First Slice — Independent Review

**Date:** 2026-09-30  
**Mode:** read-only review and reproduction; no source, probe, dependency, IFC, Blender, or existing evidence file was modified.

## Verdict

**退回修订。** The numerical diagnostic evidence is partly reproducible and useful, but the delivered visualization is materially misleading and the probe's temporary-output/reproduction contract is weaker than the handoff requires.

## Blockers

### 1. Visualization is not a reliable rendering of the JSON evidence

The SVG was rendered to PNG with the installed `svglib`/ReportLab path and inspected visually. The figure shows green sampled cells extending beyond the dark source domain/obstacle geometry, and the red origin line extends below the displayed domain. There is no legend explaining domain, obstacles, sampled cells, or origin. The title contains resolution/origin metadata, but the visual encoding is not self-auditing. This conflicts with the requested inspection of source geometry, sampling, free region, metadata, and legend.

The underlying cause is visible in the probe: visualization cells are emitted from lattice coordinates without clipping them to the source domain, while the SVG canvas and origin line use fixed dimensions. This is a blocker for accepting the visual artifact as evidence; it does not invalidate the JSON area/topology records by itself.

### 2. Reproduction does not honor a caller-selected temporary output directory

The requested independent reproduction in a temporary output directory could not be performed through the documented command because the script derives `ROOT` from its own location and writes to the repository-relative `outputs/design/space_field`. Copying the probe to a temporary directory and running it with the project Pixi Python caused it to write to `C:\Users\tianf\AppData\outputs\design\space_field`, outside the temporary directory. The original delivery artifacts were not overwritten, but this demonstrates that the script has no explicit output-root control and that its reproduction behavior depends on script location.

## Important findings

### Area oracle is independent and numerically correct

The `wide_space_narrow_neck` geometry is a 12-by-8 domain (`96.0`) minus four disjoint obstacles totaling `63.0`, yielding `33.0`. The probe independently recomputes rectangle area from fixture geometry and asserts it equals the declared oracle. This is independent of sampled cell counts. The fine-resolution sampled result is `33.0`; the coarse 1.0 result is `36.0` with absolute error `3.0`, which is reported rather than hidden.

### Sensitivity fixture is real, but its topology result is an intentional failure mode

`subcell_gap_origin_sensitive` has a 0.8-unit geometric gap and an independently computed exact free area of `19.2`. At resolution `1.0`, origins `(0.0, 0.0)` and `(0.23, 0.17)` produce different sampled areas (`16.0` and `20.0`) while both report two components rather than the exact one. At finer settings the sampled component count remains three in this center-sampling formulation. Thus the fixture does expose resolution/origin sensitivity, but it also shows non-convergence and persistent topology distortion. `diagnostic_pass` does not mean the sampled topology is correct; it means the assertions and status propagation completed.

### Sampled free-run is not Euclidean clearance or route width

The probe finds consecutive free lattice cells on one sampled horizontal row and reports their run widths. It does not compute a Euclidean distance transform, obstacle-to-obstacle clearance, medial-axis bottleneck, or body/route-width feasibility. The source geometry neck width (`1.5`) is retained separately in the fixture/profile metadata and is not substituted for the sampled result. The report correctly limits interpretation to sampled free-run evidence, but the visualization does not label this distinction.

### Missing domain behavior is preserved

For `missing_domain`, every run returns `status: not_available` with reason `missing_explicit_analysis_domain`. No canvas or obstacle extent is used as a substitute. This agrees with the architecture memory and handoff boundary.

### Unverified geometry classes remain honestly out of scope

The result and report state that curved, oblique, rotated, hole, opening, wall-permeability, adaptive-refinement, full-distance-field, and real-IFC cases were not run. No production resolution, semantic role threshold, Bayesian/ML model, selector, or implementation API is selected.

## Actual commands and results

- `Get-Content` on AGENTS, architecture memory, handoff, owner review, report, probe, JSON, manifest, and SVG: completed.
- Read project-local `experimental-design`, `scientific-critical-thinking`, and `scientific-visualization` skills: completed and applied.
- `verification-before-completion` at the advertised project skill path: unavailable; equivalent checks were run manually.
- `pixi run python scripts/design/space_field/run_space_field_probe.py`: `diagnostic_pass`.
- Independent rectangle/oracle inspection from JSON: `33.0` recomputed for the neck fixture; `19.2` recomputed for the sensitivity fixture.
- Temporary-copy execution with the project Pixi Python: completed, but output-root control was not honored; deterministic fixture payload hash matched the delivered result payload.
- SVG render: `svglib`/ReportLab rendered PNG successfully; visual inspection found the clipping/legend defects described above.
- Manifest SHA-256 checks: script, result JSON, and SVG hashes matched the manifest at review time.
- `git diff --check`: passed.
- Git scope review: this review added only the present review file; pre-existing unrelated untracked files remain in the repository and were not attributed to this work.

## Accepted evidence

- Independent rectangle-area oracle and corrected `33.0` value.
- Explicit area error reporting for sampled results.
- Real resolution/origin sensitivity and topology disagreement in the subcell-gap fixture.
- Separation of source geometry neck width from sampled free-run output.
- Explicit `not_available` propagation for missing domain.
- Honest diagnostic-only and unverified-input boundaries.

## Conclusions not supported

The evidence does not establish a production grid resolution, convergence, Euclidean clearance, route usability, bottleneck truth, corridor/activity labels, geometric robustness beyond rectangles, real IFC capability, psychological validity, or production readiness.

## Next-slice readiness

This is **not yet sufficient to freeze an implementation-design slice** because the visualization must be corrected and the probe needs an explicit output-root/reproduction mechanism or a documented, reliable temporary-copy procedure. After those are addressed, the remaining minimum gap is a deliberate geometry-class extension (for example one rotated or hole fixture) with an independent oracle and explicit status handling.

**STOP FOR SPACE FIELD INDEPENDENT REVIEW**
