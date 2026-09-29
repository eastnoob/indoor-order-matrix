# Group Self-Description First Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Stop at every checkpoint and report the verification output.

**Goal:** Implement the first clean-room evidence slice for eligible authored furniture groups: group geometry, pair relations, permitted space observations, and local-neighborhood evidence, without implementing an inferred-group selector.

**Architecture:** Add a focused inference helper that consumes the existing planar Neutral Scene view and returns a separate evidence mapping. Reuse existing authored-group extraction, boundary evidence, geometry projection, units, analysis frame, and capability/status conventions. Keep candidate views deferred and do not change `NeutralSceneV2`, adapters, or the exported room-analysis model shape.

**Tech Stack:** Python 3.12 via Pixi, existing project geometry helpers and `pytest`; no new dependencies; IFC/SVG adapter fixtures only for declared acceptance facts.

**Spec:** `docs/project/d6-group-self-description-implementation-design-review.md`

## Global Constraints

- Only explicitly marked `furniture_group` objects are eligible furniture-group nodes.
- Context objects remain context; they may contribute to permitted spatial observations but never become furniture-group members.
- Authored membership and inferred candidate membership remain separate.
- `AnalysisDomain` is required for domain-dependent negative-space/topology observations; scene bounds are not a substitute.
- Missing and invalid geometry/status values must not be converted into zero or into one another.
- Ordinary semantic label disagreement is soft negative evidence; explicit mutual exclusion is a candidate-level conflict record.
- The first slice must not implement connected-components, complete-link, max-span, a unique partition, Bayesian inference, psychological thresholds, or IFC write-back.
- All new project-owned functions require English-first docstrings and intent comments for non-obvious geometry/status logic.
- Use the portable Blender only if a diagnostic render is explicitly required; this plan does not require Blender execution.

## Frozen First-Slice Contract

The implementer must use these definitions; no task may invent a substitute.

- **Eligibility:** For `NeutralSceneV2`, inspect `scene.authored_groups` directly and accept only `group_role == "furniture_group"`; resolve `member_refs` against `scene.source_objects`. Do not use `neutral_scene_views._group_membership()` as the eligibility predicate because its compatibility behavior can retain ordinary authored groups. For a legacy mapping, accept only a non-empty explicit `object["furniture_group"]` value or exact `metadata["furniture-group"]`; do not treat generic `group_refs` as eligibility. Add an ordinary-authored-group exclusion test.
- **Canonical planar geometry:** Prefer valid closed projected `geometry_components`/polygon exteriors. Compute polygon area, centroid, and second central moments by the shoelace formula and area weighting. A `rect` may be used only when the source record explicitly carries `geometry_basis == "rect_fallback"`; record that basis. No silent bbox substitute.
- **Representative formulas:** `support_area = Σ A_i`; `center = Σ(A_i*c_i)/ΣA_i`; `within = Σ(A_i/A)*C_i_within`; `between = Σ(A_i/A)*(c_i-center)(c_i-center)^T`; `covariance = within + between`. If no usable member exists, center/area/covariance are `null`.
- **Frame formulas:** For member principal angle `θ_i`, eigenvalues `λ1 >= λ2`, anisotropy is `(λ1-λ2)/(λ1+λ2)` when the denominator is positive, and directional weight is `A_i*anisotropy`. `group_frame` uses the weighted resultant of `4θ_i` modulo `π/2`; `group_axis` uses the weighted resultant of `2θ_i` modulo `π`. If total directional weight is zero, angle is `null`, `directional_member_support=0`, `coherence=0`, and `direction_status="undefined"`. `strength` is `null` with `strength_status="deferred"` in this slice.
- **Pair geometry:** For valid projected polygon components, raw boundary gap is the minimum Euclidean distance between exterior segments, with positive-area intersection forcing gap `0`. `overlap` means intersection area `> area_tolerance`; `contact` means gap `<= geometry_tolerance` and `overlap` is false. `normalized_boundary_gap = raw_boundary_gap / sqrt(area_a + area_b)`; if the denominator is `<= area_tolerance`, return `not_computable`. Tolerances come from `NeutralSceneV2.context.geometry_tolerance`/`topology_tolerance`, or explicit legacy settings with the same names; never use a hidden grouping threshold.
- **3D/Z:** This slice does not derive 3D clearance or Z compatibility from a planar view. For `NeutralSceneV2`, serialize only explicit capability/source facts; if no approved 3D query is available, status is `not_available`. SVG and legacy mappings are 2D-only and must never claim 3D/Z computation. Actual IFC 3D implementation is a later task.
- **Semantic input:** Read only existing factual fields: `SourceObject.type_ref` first, then scalar `factual_properties["type"]`, `factual_properties["Type"]`, or `factual_properties["OM_TypeKey"]`. Missing values are `not_available`, not disagreement. No new context or semantic marker is introduced. Read explicit mutual exclusion only from existing scalar/list `factual_properties["mutual_exclusion"]`; preserve it as provenance and do not infer it.
- **Space scope:** Serialize existing `analysis_domain`, `channel_evidence`, boundary/opening facts, occupancy/blocker provenance, and context alignment references. Do not rasterize free space, compute new connectivity/bottleneck widths, call gap-path construction, or assign a primary space role. Domain-dependent fields are `not_available` when `analysis_domain is None`; unavailable is not zero.
- **Status levels:** Group/geometry status is one of `computed`, `partial`, `not_available`, `invalid`, `not_evaluated`. Pair/channel status is one of `computed`, `partial`, `not_available`, `invalid`, `not_computable`, `diagnostic_only`, `not_evaluated`. Candidate status is not computed in this slice: emit top-level `candidate_view_status="deferred"` and `candidate_views=null`. No status may rewrite invalid as missing or unavailable as zero.
- **Evidence JSON shape:** `analysis_frame` is `{name, plane, origin, unit}`; `capabilities` maps stable channel names to `{status, source, reason}`; `uncertainties` is a list of `{code, message, source_refs, operation, severity, details}`; `provenance` is `{source_schema, adapter_version, input_mode, method, version}`. Sort group ids, pair ids, source refs, and member ids before serialization.

## Review Focus

- Exact furniture-group eligibility must exclude ordinary groups, names, layers, and legacy region fallbacks.
- Additive support area and area-weighted representative geometry must remain separate from overlap/union observations.
- Pair relation channels must preserve raw/normalized gap, contact, positive-area overlap, Z/3D status, barrier status, witness provenance, and missingness.
- Context changes allowed spatial observations without changing authored membership or eligibility.
- Domain absence must produce `not_available`, never a computed zero-node topology result.

### Task 1: Establish focused contract fixtures and failing tests

**Files:**
- Create: `test/test_group_self_description.py`
- Reuse: existing test fixture builders from `test/test_neutral_scene_analysis_regression.py` where appropriate; do not modify production code in this task.

**Interfaces:**
- Consumes: the implementation-design review and existing `AnalysisSceneInput`/legacy scene mappings.
- Produces: executable tests that pin the first-slice contract before implementation.

- [ ] **Step 1: Write tests for eligibility and output shape**

  Assert that an exact `group_role == "furniture_group"` is eligible, an ordinary authored group containing furniture members is excluded, and the result has `candidate_view_status="deferred"` with `candidate_views is None` rather than an ambiguous empty list.

- [ ] **Step 2: Write tests for representative geometry status**

  Cover additive support area, area-weighted center, within/between covariance fields, `partial`, `not_available`, and `invalid` propagation. Assert that invalid is never rewritten as missing.

- [ ] **Step 3: Write tests for pair and context channels**

  Cover positive-area overlap versus zero-gap contact, normalized gap provenance, context alignment/reference provenance, and explicit domain absence producing `not_available` for domain-dependent observations.

- [ ] **Step 4: Run the focused tests and confirm they fail for the missing helper**

  Run: `pixi run pytest test/test_group_self_description.py -q`

  Expected: collection/import failure because `features.group_self_description` has not been implemented yet. Do not weaken assertions to make the test pass.

### Task 2: Implement eligibility and representative geometry

**Files:**
- Create: `features/group_self_description.py`
- Modify: `test/test_group_self_description.py`

**Interfaces:**
- Consumes: `AnalysisSceneInput`, `analysis_scene_view`, existing furniture-group provenance and projected geometry records.
- Produces: `describe_group_relations(scene) -> dict[str, object]` with `eligibility`, `group_geometry`, `candidate_view_status="deferred"`, `candidate_views=None`, capabilities, and provenance. No analysis-profile configuration is introduced in this slice.

- [ ] **Step 1: Implement the module-level contract and function docstrings**

  Keep the helper independent of SVG XML parsing and do not import adapters. Use the existing planar view as the only scene conversion boundary.

- [ ] **Step 2: Implement strict eligibility extraction**

  Inspect `NeutralSceneV2.authored_groups` directly and accept only `group_role == "furniture_group"`; for legacy mappings accept only the two exact explicit fields in the frozen contract. Preserve context source ids and geometry provenance separately. Do not infer singleton groups from ordinary authored groups, names, layers, or proximity.

- [ ] **Step 3: Implement additive representative geometry**

  For usable members, compute `support_area`, area-weighted `center`, `within_member_covariance`, `between_member_covariance`, and `covariance` using the frozen formulas. Output `overlap_area` separately and `union_area_status="deferred"`; preserve `excluded_member_reasons` and `geometry_completeness`.

  Keep overlap area independent; do not subtract it from `support_area`. Defer polygon union and report its capability as deferred rather than returning a fabricated union value.

- [ ] **Step 4: Implement frame/axis as independent description fields**

  Compute `group_frame` and `group_axis` using the frozen four-angle/two-angle resultants. Output `strength=null` and `strength_status="deferred"` in this slice. Do not use trend, frame, coherence, or strength to create pair edges or local-neighborhood membership.

- [ ] **Step 5: Run focused tests**

  Run: `pixi run pytest test/test_group_self_description.py -q`

  Expected: PASS for eligibility, geometry formulas, status propagation, and deferred candidate output.

- [ ] **Step 6: Commit the focused implementation**

  ```bash
  git add features/group_self_description.py test/test_group_self_description.py
  git commit -m "feat: add authored group self-description geometry"
  ```

### Task 3: Implement pair relations and local-neighborhood evidence

**Files:**
- Modify: `features/group_self_description.py`
- Modify: `test/test_group_self_description.py`

**Interfaces:**
- Consumes: representative group records from Task 2 and existing boundary/opening/context evidence.
- Produces: `group_relations` and `local_neighborhood` records with channel-level status and provenance.

- [ ] **Step 1: Add pairwise relation records**

  Compute raw and normalized boundary gap, contact, positive-area overlap, member-pair witness, and barrier/semantic channel statuses using the frozen polygon rules and tolerances. Serialize 3D/Z as explicit capability facts or `not_available`; do not derive them from planar geometry. Keep `target_layer`/`target_id` fields on group and pair records.

- [ ] **Step 2: Add status and missingness propagation**

  Keep invalid, partial, not-available, and not-evaluated distinct. A measured relation is not a formal membership edge. Explicit mutual exclusion is retained as conflict provenance but does not trigger a candidate selector in this task.

- [ ] **Step 3: Add local-neighborhood view**

  Expose each eligible group’s pair relations and positive/negative evidence vectors. Do not rank a single nearest neighbor as “the group,” do not create connected components, and do not collapse evidence into an unapproved fixed score.

- [ ] **Step 4: Add tests for invariants**

  Assert ID/traversal-order invariance, translation invariance, and rotation invariance only when the analysis plane is rotated with the scene. Also assert ordinary label mismatch as soft negative, explicit mutual-exclusion conflict preservation, shared-member diagnostic behavior, and no candidate membership output.

- [ ] **Step 5: Run focused tests and the prior regression slices**

  Run: `pixi run pytest test/test_group_self_description.py test/test_neutral_scene_analysis_regression.py -q`

  Expected: PASS with no changes to legacy furniture-group or gap-path semantics.

- [ ] **Step 6: Commit the relation slice**

  ```bash
  git add features/group_self_description.py test/test_group_self_description.py
  git commit -m "feat: add group relation and neighborhood evidence"
  ```

### Task 4: Add declared IFC/SVG 2D acceptance coverage

**Files:**
- Modify: `test/test_group_self_description.py`
- Reuse: existing independent SVG fixture and live IFC fixture paths already recorded in D6 evidence; do not modify adapters.

**Interfaces:**
- Consumes: `load_svg_neutral_scene`, IFC loader path, and `describe_group_relations`.
- Produces: parity assertions limited to declared planar canonical facts.

- [ ] **Step 1: Add SVG canonical-fact assertions**

  Compare eligibility, plan geometry, center/area, raw/normalized gap, contact, positive-area overlap, status, units, analysis plane, and provenance only where the SVG fixture declares them. Use the existing `load_svg_neutral_scene` path; use the IFC loader only for declared source/capability facts. Do not compare 3D/Z fields across SVG and IFC.

- [ ] **Step 2: Add IFC capability assertions**

  Keep 3D/Z/clearance/opening capabilities IFC-only. If the fixture lacks actual `IfcOpeningElement`/void/fill relations, assert `not_available` rather than interpreting door geometry as an opening relation.

- [ ] **Step 3: Run adapter acceptance tests**

  Run: `pixi run pytest test/test_group_self_description.py test/test_svg_scene_adapter.py test/test_neutral_scene_analysis_regression.py -q`

  Expected: PASS for declared parity only; no adapter files or production IFC/SVG paths are changed.

- [ ] **Step 4: Commit acceptance coverage**

  ```bash
  git add test/test_group_self_description.py
  git commit -m "test: cover group self-description planar acceptance"
  ```

### Task 5: Integration gate and whole-suite verification

**Files:**
- Modify only after review: `features/scene_inference.py` if an explicit opt-in evidence hook is approved.
- Test: `test/test_group_self_description.py` and affected regression tests.

**Interfaces:**
- Consumes: the standalone helper and its focused tests.
- Produces: either a documented standalone evidence entry point or an explicitly opt-in `infer_scene_evidence` hook. No automatic candidate selector.

- [ ] **Step 1: Review whether integration is needed**

  Do not add a public model field or automatic call merely for convenience. If integration is approved, use an explicit opt-in parameter or a clearly versioned evidence key and preserve existing output behavior by default.

- [ ] **Step 2: Run the full suite**

  Run: `pixi run pytest -q`

  Expected: all existing tests pass; any skipped tests remain explainable; no production API shape changes are hidden in adapter payloads.

- [ ] **Step 3: Audit scope and comments**

  Run: `git diff --check`, inspect changed files, and verify every new function has an English-first docstring and non-obvious geometry/status blocks have intent comments.

- [ ] **Step 4: Stop for checkpoint review**

  Report changed files, focused test output, full-suite output, capability limitations, and the fact that candidate synthesis remains deferred. Do not start Task 6 or Bayesian work in the same turn.

## Handoff Notes

The implementation agent must read the implementation-design review and this plan before coding. If a requested behavior requires choosing a candidate selector, fixed score, threshold, prior, or new context marker, stop and return a design question instead of inventing a default.

The first implementation checkpoint is complete only when relation/local-neighborhood evidence is independently reviewable and the full regression suite passes. A passing test suite does not approve an inferred-group objective.
