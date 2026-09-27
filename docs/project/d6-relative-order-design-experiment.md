# D6 relative-order candidate design experiment

**Status:** design-only evidence for owner review; Task 3a complete, Task 3b not started
**Date:** 2026-09-27
**Scope:** compare order consistency (Candidate A) with normalized spacing consistency (Candidate B) for the clean-room relative-order descriptor.

This record is an algorithm comparison. It does not establish psychological or perceptual validity and does not authorize production implementation.

## Method and skill record

- experimental-design: fixed the input unit, factors, deterministic fixture set, expected invariants, output measures, decision rule, and replication command before interpreting values. No randomization was needed because this is a deterministic computational probe; the seed is therefore not applicable.
- scientific-critical-thinking: keeps evidence, observations, interpretations, unresolved owner decisions, and claims outside scope in separate sections.
- scientific-visualization: records the source fixture, anchor transform, analysis axis, tie overlay, Blender settings, generated scene, render, and inspection limitation as provenance.
- superpowers:executing-plans: this is Checkpoint 3 design phase only. The required STOP FOR DESIGN REVIEW is preserved below; no implementation design table or production code is created.

The experimental-design workflow was used as procedural guidance. The skill library is documented by Kassis et al. (2026), [arXiv:2609.00065](https://doi.org/10.48550/arXiv.2609.00065).

## Inputs and factors

Each fixture has declared object order (A, B, C), projected plan vertices, source unit, a positive source-to-analysis scale, AnalysisFrame.origin, an explicit unit axis, and tolerance 0.1 in analysis units. The anchor is the arithmetic mean of all finite projected vertices. The scalar position is:

    position_i = dot(anchor_i - frame_origin, axis_unit)

The probe uses only the geometry transform represented in each fixture. It does not infer an axis from object IDs, drawing order, or world-X. Missing geometry is excluded with a reason when two usable objects remain; invalid geometry is a hard invalid result. This is an experiment choice that remains subject to owner review.

### Candidate formulas

**Candidate A - inversion-rate/order-consistency (relative-order/v1 candidate)**

    inversions = count(position_i > position_j for i < j and |position_i-position_j| > tolerance)
    comparable_pairs = count(the same non-tied pairs)
    value = 1 - inversions / comparable_pairs

Tied pairs are excluded from the denominator and retained as stable tie blocks. No object ID breaks a tie. If no comparable pair remains, the result is undefined.

**Candidate B - normalized adjacent spacing consistency**

    gap_i = abs(position_(i+1) - position_i)
    gap_mean = mean(gap_i)
    deviation = mean(abs(gap_i - gap_mean)) / gap_mean
    value = 1 - min(1, deviation)

If the gap mean is not positive, the result is undefined. Candidate B is included to test the spacing alternative; it is not proposed as an additional descriptor in this task.

## Expected invariants and decision rule

The probe was expected to show:

1. aligned order gives A=1;
2. reversed order gives A=0 while B may remain 1;
3. uneven gaps change B but not A when pair order is unchanged;
4. translation and positive unit conversion preserve both values;
5. rotating geometry and the explicit axis together preserves both values;
6. keeping the old axis fixed after rotation can change or remove comparability;
7. axis reversal changes directional A deliberately;
8. partial ties retain tie metadata and exclude tied A pairs;
9. all ties, fewer than two usable objects, and invalid geometry never become numeric zero.

The selection rule is to retain the candidate that answers the declared sequence-direction question, preserves the listed geometric invariants, exposes ties and failure states, and does not introduce ID ordering. A candidate that only measures spacing cannot satisfy the sequence-direction requirement; spacing remains a separate deferred question.

## Reproducible numerical oracle

Files:

- Fixture: scripts/design/relative_order/fixtures.json
- Oracle: scripts/design/relative_order/run_numeric_oracle.py
- Output: outputs/design/relative_order/numeric_oracle.json

Command:

    pixi run python scripts/design/relative_order/run_numeric_oracle.py --output outputs/design/relative_order/numeric_oracle.json

The script contains assertion-based hand checks and exits non-zero if the oracle drifts from the expected invariants.

### Numerical observations

| case | usable positions (analysis units) | Candidate A | Candidate B | status / metadata |
|---|---:|---:|---:|---|
| aligned | (0, 1, 2) | 1.0 | 1.0 | computed |
| reversed | (2, 1, 0) | 0.0 | 1.0 | B cannot distinguish reversal |
| uneven spacing | (0, 2, 5) | 1.0 | 0.8 | A ignores spacing by design |
| partial ties | (0, 0.05, 1) | 1.0 | 0.1 | tie block [A, B]; A has 2 comparable pairs |
| all ties | (1, 1, 1) | undefined | undefined | no comparable pair; zero gap reference |
| translation | (0, 1, 2) after common frame translation | 1.0 | 1.0 | same as aligned |
| positive scale / unit conversion | (0, 1, 2) after cm to m | 1.0 | 1.0 | same as aligned |
| geometry + frame rotation | (0, 1, 2) on rotated axis | 1.0 | 1.0 | same as aligned |
| geometry rotation with fixed old axis | (0, 0, 0) within tolerance | undefined | undefined | expected axis-sensitive loss of comparability |
| axis reversal | (-0, -1, -2) | 0.0 | 1.0 | direction is explicit and intentional |
| degenerate geometry | A,C usable; B invalid | invalid | invalid | malformed geometry is not silently dropped |
| missing geometry | A,C usable; B unavailable | 1.0 | 1.0 | B excluded with reason; two usable objects remain |

The raw anchors, positions, tie blocks, excluded IDs, and invalid reasons are retained in the JSON output.

## Blender geometry diagnostic

The portable Blender requirement was attempted and completed with the specified executable:

    D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe -b -noaudio -P scripts/design/relative_order/render_relative_order_blender.py -- --fixture scripts/design/relative_order/fixtures.json --output-dir outputs/design/relative_order

Generated artifacts:

- Generator: scripts/design/relative_order/render_relative_order_blender.py
- Fixture: scripts/design/relative_order/fixtures.json
- Scene: outputs/design/relative_order/relative_order_diagnostic.blend
- Render/capture: outputs/design/relative_order/relative_order_diagnostic.png
- Settings and provenance: outputs/design/relative_order/blender_metadata.json

The render shows blue anchors, green positive-axis arrows, a red reversed-axis arrow, orange tie ring, frame-origin markers, and a panel with geometry and frame rotated together. The translated-frame panel keeps the same order while changing the frame origin, making the transform convention visible.

The image was inspected in this session. Interactive Blender viewport/UI inspection was not performed. The run emitted unrelated installed-addon registration warnings in background mode; the design script itself saved the scene and render with exit code 0. Therefore this is a headless render diagnostic, not a claim of live Blender UI verification.

![Relative-order Blender diagnostic](../../outputs/design/relative_order/relative_order_diagnostic.png)

## Evidence classes

### D3-D5 external evidence

docs/project/evidence/d3-d5-synthesis.md records that the external literature and official IFC/software sources do not distinguish inversion/order consistency from spacing consistency for this project, and do not establish psychological validity for a furniture-layout descriptor. Those sources justify keeping the metric as an engineering descriptor with explicit provenance; they do not select a formula.

### Repository and runtime facts

- The clean-room contract requires an explicit AxisSpec, analysis-unit frame origin, arithmetic-mean anchor, one complete SourceGeometry3D.world_transform, explicit tie metadata, and distinct status values.
- docs/project/d6-relative-order-decision.md records Candidate A as provisional, with spacing deferred.
- The repository uses Pixi with Python 3.12. The numerical command ran through Pixi.
- The portable Blender executable reports Blender 5.2.0 LTS.

### Numerical probe observations

The table above is direct output from the deterministic oracle. The strongest discriminator is the reversed fixture: Candidate A changes from 1 to 0, while Candidate B remains 1. Translation, positive scale/unit conversion, and joint geometry/frame rotation preserve both values. Fixed-axis rotation and explicit axis reversal demonstrate that direction is a declared variable rather than an implicit world axis.

### Blender geometry diagnostics

The render makes the computational variables inspectable: axis direction, anchor positions, tie region, frame origin, and rotated geometry. It supports checking the intended inputs and transforms only. It does not measure perception or human judgments.

### Engineering interpretation

Under the stated question, Candidate A is the only candidate that directly reports agreement with the declared sequence direction. Candidate B is useful evidence that spacing is a different descriptor question: it treats aligned and reversed arrangements identically and reacts to uneven gaps. The numerical comparison therefore supports retaining the provisional Candidate A selection for relative-order/v1, while keeping spacing consistency out of this slice.

This result is conditional on the tie and missing-geometry policies written above. It does not authorize production code or the implementation design table.

### Questions still requiring owner decision

1. Should a partial tie remain computed when at least one comparable pair exists, or should any tie make the complete relative-order result undefined?
2. Is excluding not_available objects acceptable when two usable anchors remain, or should any missing member make the whole result not_available?
3. Should Candidate B remain only a deferred design reference, or should a separately named spacing descriptor be planned later?
4. Is the explicit-axis policy confirmed with no implicit default, including for adapters that author a default axis?

If any answer changes the metric meaning or status semantics, reopen the owner decision before Task 3b.

### Claims this experiment cannot support

It cannot show that people perceive a layout as ordered, regular, balanced, usable, or aesthetically coherent. It cannot validate a psychological scale, infer affordance, establish a human threshold, or transfer results from the synthetic fixtures to real rooms. A later human experiment would require a separate stimulus, task, observer, and validity design.

## Checkpoint and stop

Task 3a produced design evidence only. No features/, adapters/, or test/ module was modified. No implementation design table was created.

**STOP FOR DESIGN REVIEW** - owner review is required before creating d6-relative-order-implementation-design.md, beginning Task 3b, or writing descriptor production code.
