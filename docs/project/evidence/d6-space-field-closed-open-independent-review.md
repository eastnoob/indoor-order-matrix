# D6 Closed/Open Fixture Repair — Independent Review

**Date:** 2026-10-01  
**Scope:** read-only reproduction and design-experiment review  
**Final verdict:** `ACCEPT LIMITED DIAGNOSTIC EVIDENCE`

## Blockers

None for the repaired closed/open diagnostic fixture. Independent source-geometry arithmetic, Shapely boolean results, temporary rerun, sensitivity rows, deterministic payload comparison, manifest hash checks, and source-geometry rendering all passed.

This verdict does not approve production implementation.

## Important findings

- Independent hand calculation: domain `D=(0,0,6,4)` has area 24; barrier `B=(2.5,0,3.5,4)` has area 4; opening `O=(2.5,1.5,3.5,2.5)` has area 1. Therefore closed free area is `24-4=20` with two components; open free area is `24-(4-1)=21` with one component.
- Independent Shapely construction reproduced the same source results: closed geometry area 20.0 with two components; open geometry area 21.0 with one component. The result files report these as `source_area`/`source_components` in the polygon baseline and as independently computed rectangle oracle values in the rectangle path. They are not merely sampled values.
- Rectangle and polygon paths use the same effective obstacle semantics: closed subtracts the full barrier; open subtracts `B\O`, leaving a positive-area opening inside the barrier. The polygon path computes source geometry with Shapely, while the rectangle path computes its declared exact rectangle oracle independently and samples the same closed/open semantics.
- Temporary reproduction command succeeded:
  `pixi run python scripts/design/space_field/run_polygon_baseline.py --output-dir <temporary-directory>`
  Exit/result: `pass`. Temporary output contained exactly `polygon_baseline_results.json` and `polygon_baseline_manifest.json`; no repository output was overwritten.
- After removing runtime and path fields, temporary and delivered polygon payloads were deterministically equivalent.
- Manifest SHA-256 checks passed for both delivered and temporary polygon result bytes and for the runner source digest.
- The requested resolutions and origins were present: steps `1.0, 0.5, 0.25, 0.125`; origins `(0,0)` and `(0.23,0.17)`. The four settings are sensitivity observations, not four independent samples.
- Sampling does not always equal source geometry. The key observed discrepancy is closed wall at step `1.0`, origin `(0,0)`: sampled area is 24.0 and sampled component count is 1, while source is area 20.0 and 2 components. At step `0.5` and `0.25` for both origins, closed sampling is area 20.0 and 2 components; open sampling is area 21.0 and 1 component. This is correctly interpretable as resolution/origin sensitivity, not proof that the coarse grid is correct.
- The source comparison SVG rendered successfully to PNG at 1100×520. Its labels and values match the JSON: closed source area 20/components 2 and open source area 21/components 1. The figure explicitly identifies itself as source geometry rather than sampled field, with effective wall and opening semantics visible.
- `git diff --check` passed. No changes were made to runner, production code, adapters, formal tests, dependencies, source IFC, or user Blender files. Existing dirty/untracked content was preserved.

## Minor findings

- The rectangle output's visualization is inherited from the broader space-field probe and is not the closed/open source comparison figure; the source comparison SVG is the appropriate artifact for checking this repair's geometry semantics.
- The polygon baseline records Shapely 2.1.2 and synthetic coordinate units. This is adequate provenance for the constructed experiment, not evidence of production geometry-kernel capability.
- No additional fixture family, full IFC run, or full pytest run was performed, per scope.

## Skills actually used

- `experimental-design`: read from `D:\PROJECTS\understandOtherPackage\order_analyzer\.agents\skills\experimental-design\SKILL.md`; used to treat resolution/origin combinations as sensitivity factors and to avoid pseudoreplication claims.
- `scientific-critical-thinking`: read from `D:\PROJECTS\understandOtherPackage\order_analyzer\.agents\skills\scientific-critical-thinking\SKILL.md`; used to separate source measurements, sampled observations, and unsupported interpretations.
- `scientific-visualization`: read from `D:\PROJECTS\understandOtherPackage\order_analyzer\.agents\skills\scientific-visualization\SKILL.md`; used for rendered inspection, semantic labels, and source-vs-sampled distinction.
- `verification-before-completion`: searched in project, global, and plugin skill roots but not found; it was not claimed as run. Equivalent rerun, deterministic comparison, SHA-256, render, and scope checks were performed manually.

## Unverified items and conclusion boundaries

This experiment validates the geometric effect of a positive-area boundary opening on constructed 2D synthetic geometry. It does not simulate door state. “Doors generally default closed” remains an owner analysis assumption, not a verified IFC state; this result must not be used to close all boundary openings. The exact boundary range is not frozen.

The result does not establish physical traversability, visual permeability, route width, corridor/activity-area classification, production resolution, or real IFC opening acceptance. Synthetic units are coordinate units and do not represent human passage scales. No production selector, automatic-space model, Bayesian/ML model, or public API decision is supported.

## Accepted limited evidence

The repaired fixture now supplies a reproducible closed/open contrast in which the source geometry changes from two components and area 20 to one component and area 21, and the sampled comparison exposes the expected coarse-grid sensitivity without hiding it. This is sufficient as limited diagnostic evidence for the next design discussion of boundary/opening semantics.

It is not evidence to freeze a backend, resolution, threshold, door-state policy, or production implementation.

## Final verdict

`ACCEPT LIMITED DIAGNOSTIC EVIDENCE`

**STOP FOR CLOSED-OPEN FIXTURE INDEPENDENT REVIEW**
