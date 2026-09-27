# D6 relative-order design experiment follow-up

**Status:** revised design-only evidence for owner review; Task 3b is not started
**Date:** 2026-09-28
**Scope:** harden the relative-order comparison around tie semantics, external reference order, anchor sensitivity, status states, reproducibility, and Blender diagnostics.

This artifact does not authorize production implementation and does not establish psychological or perceptual validity.

## Skills read and used

- Project experimental-design at .agents/skills/experimental-design/SKILL.md: fixed the unit of comparison, factors, deterministic fixtures, expected invariants, output measures, and decision rule before interpreting results. No randomization or seed is applicable because this is a deterministic computational probe.
- Project scientific-critical-thinking at .agents/skills/scientific-critical-thinking/SKILL.md: separated external evidence, repository facts, numerical observations, engineering interpretation, unresolved owner decisions, and unsupported claims.
- Project scientific-visualization at .agents/skills/scientific-visualization/SKILL.md: preserved input and transform provenance, added direct reference/observed labels, checked overlap and contrast in the rendered capture, and recorded the headless inspection limit.
- superpowers:verification-before-completion: required fresh oracle, Blender, checksum, diff, and file-scope commands before reporting results.
- grill-me: read at C:\Users\tianf\.codex\skills\grill-me\SKILL.md and applied its hostile reverse-review questions below. This API exposes no separate /grilling command, so the review is recorded as an explicit self-audit rather than claimed as an interactive session.

The scientific skill guidance is cited in the earlier design record and remains procedural guidance, not evidence for the metric.

Software/procedure reference: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents. arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065

## Data contract under review

The descriptor compares geometry against an externally supplied reference sequence.

    reference_order = [object_id_1, object_id_2, ..., object_id_n]

The reference sequence is not inferred from geometry. It is not:

| possible source | role in this experiment |
|---|---|
| external reference order | authoritative comparison sequence |
| IFC entity/file order | source fact only; never a semantic ordering |
| authored IfcGroup member order | source membership/provenance only; not used unless explicitly supplied as the reference |
| lexical object-ID order | metadata lookup only; never a fallback |
| geometry-inferred order | observed projection used for comparison; never the reference |

The fixture records the contract explicitly:

    reference_order: ["A", "B", "C"]
    reference_order_provenance:
      kind: external_reference_order
      source: design_fixture
      stable_key: fixture.reference_order
      not_from: [ifc_entity_order, authored_group_member_order,
                 object_id_lexical_order, geometry_inference]

A case may override the reference order with its own externally supplied list. A missing or malformed reference order returns not_evaluated. The result records the exact sequence and provenance. The non_dictionary_reference_order fixture uses zeta, alpha, middle to prove that lexical sorting is not occurring.

The observed sequence is obtained only after anchor projection. The metric therefore answers: “Does the projected geometry follow the externally provided reference order along the declared axis?” It does not discover a true or intrinsic order in an unlabelled scene.

## Inputs and transforms

Each case supplies projected plan vertices, optional explicit triangles, source unit, positive source-to-analysis scale, AnalysisFrame.origin, an explicit unit axis, tolerance 0.1 in analysis units, object records, and the external reference sequence.

The arithmetic anchor is:

    anchor = arithmetic mean of all finite projected plan vertices

The optional area-weighted anchor is computed only when explicit triangle coordinates are present:

    anchor = sum(triangle_area * triangle_centroid) / sum(triangle_area)

The scalar coordinate is:

    position_i = dot(anchor_i - AnalysisFrame.origin, AxisSpec.unit_vector)

The oracle does not infer a missing axis, multiply an unknown placement transform, or substitute an object ID or source placement point.

## Tie semantics comparison

The earlier oracle formed connected components implicitly. That is removed from the selected calculation.

### Pairwise tie edges

For each pair i < j, the pair is tied when abs(position_i - position_j) is less than or equal to tolerance. The inclusive boundary uses a small floating-point comparison guard so a mathematical equality at tolerance is not lost to binary rounding.

Candidate A then excludes only that pair from the comparable-pair denominator:

    inversions = count(non-tied pairs with position_i > position_j)
    comparable_pairs = count(non-tied pairs)
    order_consistency = 1 - inversions / comparable_pairs

The numerator is the inversion count among non-tied pairs. Tied pairs contribute neither an inversion nor a denominator term. Tie edges are retained in reference-order traversal order. If no comparable pair remains, Candidate A is undefined. A partial tie remains computed when another comparable pair exists.

### Interval/block/transitive comparison

For audit only, the direct edges are also connected into transitive blocks. A-B and B-C therefore make [A, B, C] one block even when A-C exceeds tolerance. The transitive candidate excludes all pairs inside that block. It is never silently used for the selected result.

### Chained-tie observation

The chained_ties fixture uses positions (0, 0.05, 0.11) with tolerance 0.1:

- pairwise edges: A-B and B-C;
- A-C is not tied;
- pairwise Candidate A: computed, value 1.0, one comparable pair;
- transitive-block Candidate A: undefined, because all three are merged;
- Candidate B: undefined because its mean adjacent gap is below the spacing reference threshold.

The pairwise result preserves the only directly comparable relation and avoids inventing a three-object equivalence class. This is the provisional tie semantic for relative-order/v1. Owner approval is still required because the choice changes undefined versus partial-computed behavior.

## Anchor sensitivity experiment

The tessellation_sparse and tessellation_dense fixtures describe the same rectangle triangles for object A but use different boundary vertex sampling densities. Object B is at x=0.5 and object C at x=2.5.

| fixture | arithmetic anchor A | arithmetic Candidate A | area-weighted Candidate A |
|---|---:|---:|---:|
| tessellation_sparse | x=0.0 | 1.0 | 1.0 |
| tessellation_dense | x=0.6666667 | 0.6666667 | 1.0 |

The dense boundary samples are all on one rectangle edge. The arithmetic mean therefore changes even though the explicit triangle geometry is unchanged, and the observed arithmetic order changes from fully aligned to one inversion. The area-weighted triangle centroid is invariant for the two tessellations.

Current design conclusion:

- arithmetic mean remains a simple candidate fact and is retained in the oracle for comparison;
- it is not yet safe to treat it as the final representative point because the fixture demonstrates tessellation-density sensitivity;
- area-weighted triangle centroid is the stronger geometry-preserving candidate when explicit triangles are available;
- the current canonical geometry contract can support the area-weighted method only when triangles and their coordinates are present;
- where only vertices are present, the area-weighted method is not_available rather than fabricated;
- volume-weighted centroid is outside this 2D plan slice and would require an explicit 3D solid/volume contract.

This is an anchor semantic gap. It reopens owner approval before Task 3b.

## Minimal status model

The result keeps the contract status vocabulary and uses completeness metadata for partial computation.

| condition | status | completeness | result |
|---|---|---|---|
| valid axis/reference, all members usable, comparable pairs exist | computed | complete | numeric values |
| valid axis/reference, some missing members excluded, at least two usable members remain | computed | partial | numeric values plus excluded IDs |
| fewer than two usable members | undefined | not_applicable | null values plus count/missing reasons |
| all usable positions tied or no comparable pair | undefined | not_applicable | null values plus tie edges |
| no projectable geometry for any member | not_available | not_applicable | null values plus missing reasons |
| malformed/degenerate geometry or invalid axis | invalid | not_computable | null values plus invalid reasons |
| missing/invalid external reference order or missing explicit axis | not_evaluated | not_applicable | null values plus provenance reason |

Invalid geometry is a descriptor-level failure even if other objects are usable. Missing geometry is excluded at object level; two usable objects plus one missing object is computed with completeness partial. When every object is unavailable, the descriptor is not_available. Numeric zero is never substituted for any of these states.

## Fixture coverage and oracle assertions

Fixture input, design question, expected status, expected values, and rationale are stored in scripts/design/relative_order/fixtures.json. The deterministic oracle asserts every declared expected status/value and adds focused assertions for tie edges, reference sequence, tolerance boundary, and tessellation invariance.

| fixture | design question | expected result |
|---|---|---|
| aligned | sequence direction | A=1, B=1, computed complete |
| reversed | distinguish reversal | A=0, B=1 |
| uneven_spacing | separate spacing effect | A=1, B=0.8 |
| partial_ties | pairwise partial ties | A=1, tie edge A-B |
| chained_ties | non-transitive tolerance | pairwise A=1; transitive A undefined |
| all_ties | no comparable pair | undefined |
| tolerance_boundary | inclusive boundary | A-B tie at exactly tolerance |
| translation | common translation | unchanged |
| nonzero_frame_origin | frame subtraction | unchanged |
| positive_scale_unit_conversion | positive unit conversion | unchanged |
| geometry_frame_rotation | rotate geometry and axis | unchanged |
| geometry_rotation_fixed_axis | fixed-axis sensitivity | undefined due tied projections |
| axis_reversal | explicit direction | A=0 |
| non_dictionary_reference_order | no lexical fallback | supplied zeta, alpha, middle is used verbatim |
| missing_reference_order | reference is mandatory | not_evaluated |
| axis_missing | no implicit axis | not_evaluated |
| axis_zero, axis_non_unit | axis validation | invalid |
| one_usable | insufficient object count | undefined |
| missing_geometry | two usable plus one missing | computed, completeness partial |
| all_geometry_missing | no projectable geometry | not_available |
| degenerate_geometry | malformed geometry | invalid |
| tessellation_sparse/dense | representative-point sensitivity | arithmetic changes; area-weighted remains aligned |

Reproducible oracle command:

    pixi run python scripts/design/relative_order/run_numeric_oracle.py --output docs/project/evidence/d6-relative-order-oracle.json

The tracked oracle output includes the fixture SHA-256, reference-order provenance, selected tie semantics, all raw result metadata, and both anchor methods.

## Blender diagnostic review

The portable Blender command is:

    D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe -b -noaudio -P scripts/design/relative_order/render_relative_order_blender.py -- --fixture scripts/design/relative_order/fixtures.json --output-dir outputs/design/relative_order

The scene now labels reference order and observed +axis projection order separately. It shows:

- blue anchors and labels;
- green declared positive axis and direction arrow;
- red reversed axis;
- orange pairwise tie ring;
- frame-origin markers;
- aligned, rotated-plus-translated, and partial-tie panels;
- explicit text distinguishing reference A -> B -> C from observed order.

The output files are:

- outputs/design/relative_order/relative_order_diagnostic.blend
- outputs/design/relative_order/relative_order_diagnostic.png
- outputs/design/relative_order/blender_metadata.json
- outputs/design/relative_order/blender_run.log

The image is a computational variable diagnostic only. It does not depict a human judgment, perceptual order, usability, or psychological effect. Headless image inspection was performed; interactive Blender viewport/UI inspection was not performed. Installed add-ons emit background registration warnings, but the design script must still exit zero and save the scene/render.

## Persistent provenance and artifact policy

outputs/design/relative_order is Git-ignored. It remains a replay workspace for the binary scene, render, and logs. The tracked artifacts are:

- docs/project/evidence/d6-relative-order-oracle.json
- docs/project/evidence/d6-relative-order-artifact-manifest.json

The manifest records the exact regeneration commands, portable Blender version, Python/Pixi command, input fixture SHA-256, script SHA-256 values, tracked oracle SHA-256, and the ignored scene/render/metadata/log paths with their SHA-256 values. Another session can verify the tracked inputs and regenerate the ignored binary outputs. Binary files are intentionally not committed; their retention and verification are limited by the manifest and local output directory.

## Evidence classes

### D3-D5 external evidence

docs/project/evidence/d3-d5-synthesis.md does not select inversion consistency over spacing consistency and does not establish psychological validity for a furniture-layout metric. It supports keeping this as an auditable engineering descriptor only.

### Repository and runtime facts

The clean-room contract requires explicit AxisSpec, analysis-unit frame origin, provenance, distinct status values, and no production implementation before owner approval. The repository uses Pixi Python 3.12 and the required portable Blender 5.2.0 LTS.

### Numerical observations

Pairwise tie edges preserve A-C in the chained fixture; transitive blocks do not. Arithmetic anchors change under uneven vertex sampling; area-weighted triangle centroids do not for the supplied same triangles. Translation, non-zero frame origin, positive unit conversion, joint rotation, and explicit axis reversal retain their expected behavior.

### Engineering interpretation

Candidate A remains the better answer to the declared reference-sequence question than spacing consistency. Its final tie semantics and anchor representative are not approved. The experiment now exposes the anchor counterexample instead of hiding it.

### Owner decisions still required

1. Select pairwise tie edges or interval/block/transitive ties for the final descriptor.
2. Decide whether missing geometry is excluded with computed/partial when two usable objects remain, and confirm invalid geometry is descriptor-level invalid.
3. Select arithmetic vertex mean or area-weighted triangle centroid as the normative anchor; decide whether vertex-only inputs may use the former as an explicit fallback.
4. Approve the formal reference-order input contract and provenance fields.
5. Approve the tracked-manifest plus ignored-binary retention strategy.
6. Approve whether the design is mature enough to enter Task 3b implementation design.

### Claims this experiment cannot support

It cannot establish that people perceive a layout as ordered, regular, balanced, usable, or aesthetically coherent. It cannot validate a psychological scale, infer affordance, set human thresholds, or transfer synthetic-fixture behavior to real rooms.

## Grill-me reverse review

- Did the record turn a provisional selection into a production specification? No; the anchor and tie decisions are explicitly reopened.
- Did it confuse reference order with intrinsic order? No; reference order is an external input with provenance, and missing order is not_evaluated.
- Did it silently retain connected-component ties? No; pairwise edges are selected provisionally and transitive blocks are comparison-only.
- Did it omit edge cases? The fixture table includes every requested boundary and the oracle asserts each expected state/value.
- Did it smuggle psychological validity into the metric? No; the interpretation and limitation sections reject that inference.
- Can another session reproduce the evidence? Yes for tracked inputs and oracle; ignored Blender binaries are verified/recreated through the tracked manifest.
- Did it modify production code, adapters, tests, IFC, Bonsai, or dependencies? The intended diff is restricted to design documents, design scripts/fixtures, and the manifest/oracle evidence.

## Stop condition

This follow-up remains design-only. Do not create d6-relative-order-implementation-design.md and do not begin Task 3b.

**STOP FOR DESIGN REVIEW**
