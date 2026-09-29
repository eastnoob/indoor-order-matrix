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

  Assert that an explicitly marked furniture group is eligible, an ordinary context object is excluded from the node list, and the result reserves `candidate_views` with `status="deferred"` rather than pretending that no candidates exist.

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
- Produces: `describe_group_relations(scene, *, analysis_profile=None) -> dict[str, object]` with `eligibility`, `group_geometry`, empty deferred `candidate_views`, capabilities, and provenance.

- [ ] **Step 1: Implement the module-level contract and function docstrings**

  Keep the helper independent of SVG XML parsing and do not import adapters. Use the existing planar view as the only scene conversion boundary.

- [ ] **Step 2: Implement strict eligibility extraction**

  Use the existing explicit furniture-group relation. Preserve context source ids and geometry provenance separately. Do not infer singleton groups from ordinary objects, names, layers, or proximity.

- [ ] **Step 3: Implement additive representative geometry**

  For usable members, compute `support_area`, area-weighted `center`, `within_member_covariance`, `between_member_covariance`, and `covariance`. Preserve `excluded_member_reasons` and `geometry_completeness`.

  Keep overlap area independent; do not subtract it from `support_area`. Defer polygon union and report its capability as deferred rather than returning a fabricated union value.

- [ ] **Step 4: Implement frame/axis as independent description fields**

  Reuse existing member geometry frame evidence only as auditable description. Do not use trend, frame, coherence, or strength to create pair edges or local-neighborhood membership.

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

  Compute raw and normalized boundary gap, contact, positive-area overlap, member-pair witness, 3D/Z capability status, barrier observation, semantic channel status, and shared-member diagnostic. Keep `target_layer`/`target_id` fields on group and pair records.

- [ ] **Step 2: Add status and missingness propagation**

  Keep invalid, partial, not-available, and not-evaluated distinct. A measured relation is not a formal membership edge. Explicit mutual exclusion is retained as conflict provenance but does not trigger a candidate selector in this task.

- [ ] **Step 3: Add local-neighborhood view**

  Expose each eligible group’s pair relations and positive/negative evidence vectors. Do not rank a single nearest neighbor as “the group,” do not create connected components, and do not collapse evidence into an unapproved fixed score.

- [ ] **Step 4: Add tests for invariants**

  Assert ID/traversal-order invariance, translation invariance, ordinary label mismatch as soft negative, explicit mutual-exclusion conflict preservation, shared-member diagnostic behavior, and no candidate membership output.

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

  Compare eligibility, plan geometry, center/area, raw/normalized gap, contact, positive-area overlap, status, units, analysis plane, and provenance only where the SVG fixture declares them.

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
