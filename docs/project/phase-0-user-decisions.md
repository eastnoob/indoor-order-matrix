# Phase 0 user decisions (2026-09-27)

This file records decisions supplied after the initial repository/runtime audit. It is a decision record, not a replacement for the two raw requirement sources.

## Confirmed decisions

- The project does **not** claim psychological perceptual validity. It computes quantitative layout descriptors intended to provide independent variables for later human experiments; psychological validation belongs to a separate experiment.
- The input/source architecture is an engineering decision for this project. The current recommendation is IFC4 -> NeutralScene as the production path, with SVG retained as a deterministic algorithm benchmark and generated IFC retained as adapter/acceptance coverage.
- Repairing the rich acceptance IFC EXPRESS placement relations is authorized as an independent prerequisite.
- The user reports Blender is already open and that Bonsai exposes an Open IFC Project workflow. A read-only process check found the specified portable Blender 5.2.0 LTS running with an unsaved window. CUA/MCP did not expose a targetable Windows app window, so Bonsai UI presence and live import/mapping remain unverified.
- The project path should be staged and extensible; it is not constrained to an authored-group-only final design.
- No real layouts, human group labels, order labels, or human-experiment constraints are currently available. These are not blockers for deterministic descriptor implementation; they become inputs for later stimulus selection or external construct validation.

## Current interpretation (explicitly not user-confirmed specifications)

1. Repair and validate the rich IFC fixture before treating it as a reliable acceptance fixture.
2. Freeze the IFC4 -> NeutralScene contract and use SVG as a fast oracle for algorithmic checks.
3. Stabilize authored group and geometry-based local/trend descriptors before adding inferred regions, gap paths, boundary channels, grids, and live UI integration.
4. Keep any future perception calibration outside the core descriptor engine and report descriptor evidence/provenance separately.

## Open decisions for the next gate

- Confirm whether to enter Stage 1 with the sequence above.
- Confirm the first descriptor family to prioritize after fixture repair (default recommendation: geometry/relative-order and authored-group local trend, with no psychological interpretation).
- Decide whether live Bonsai import verification should be a Stage 1 gate or a later integration gate, given the current inability to inspect the open UI through CUA/MCP.
