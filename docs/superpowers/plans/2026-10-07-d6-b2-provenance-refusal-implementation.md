# D6 B2 Provenance/Refusal Plumbing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Add the smallest production-side B2 provenance/refusal projection that preserves wall, column, opening, domain, and uncertainty facts while refusing unqualified boundary promotion and subtraction.

**Architecture:** Keep \`NeutralSceneV2\`, \`SourceObject\`, \`SourceOpening\`, \`AnalysisDomain\`, and \`UncertaintyRecord\` as the source-of-truth records. Extend the private \`analysis_scene_view\` compatibility projection with a local B2 diagnostic record; keep domain shell records separate from wall/column physical occupancy, and carry opening refusal/provenance without computing loop closure, polygon connectivity, free space, or routes. Existing adapter-specific reference behavior remains intact and is tested at its current boundary.

**Tech Stack:** Python 3.12 under Pixi, frozen dataclass Neutral Scene records, existing planar projection helpers in \`features/neutral_scene_views.py\`, pytest, JSON-safe dictionaries, and existing adapter tests.

**Spec:** \`docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-owner-decision.md\`; source design \`docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-review.md\`; independent review \`docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-independent-review.md\`.

## Global Constraints

- Preserve source wall, column, opening, transform, relation, geometry-reference, provenance, and uncertainty facts.
- Keep physical column occupancy independent from conditional boundary-support evidence.
- Keep candidate polygon validity independent from source-component connectivity.
- Unresolved, invalid, partial, conflict, unsupported, and diagnostic-only opening observations retain lineage and refuse subtraction.
- Formal AnalysisDomain promotion remains refusal-first when evidence is incomplete, conflicting, ambiguous, unsupported, or unauthorized.
- In \`features/neutral_scene_views.py\`, keep an AnalysisDomain scope/enclosure shell separate from wall/column physical-field occupancy.
- Preserve the different dangling-opening behaviors of \`adapters/svg_scene.py\` and \`adapters/blender_geometry.py\`; do not normalize them into one adapter result.
- Existing \`geometry_tolerance\` and \`topology_tolerance\` must not be read by B2 loop-closure or boundary-support plumbing.
- Do not add a public status enum or public serialization contract.
- Do not add selector, ranking, score, Bayesian/ML inference, production tolerance, near-contact policy, free-space/topology backend, resolution, origin, clearance, bottleneck, route width, walkability, space roles, singleton acceptance, UI authority, real-IFC policy, or merge behavior.
- Synthetic B2 fixtures remain synthetic design evidence and must never be described as real IFC or Blender validation.
- Use English-first docstrings and comments for every new or modified project-owned function.
- Do not modify the source IFC, user Blender files, dependencies, broad test configuration, or unrelated dirty/untracked files.

---

### Task 1: Add a private B2 diagnostic projection over existing Neutral Scene facts

**Files:**
- Modify: \`features/neutral_scene_views.py\`, around \`_neutral_scene_view\`, \`_opening_records\`, and the private helper section after \`_domain_points\`.
- Test: \`test/test_neutral_scene_analysis_regression.py\`.

**Interfaces:**
- Consumes: \`NeutralSceneV2\`, projected \`records\`, \`geometry_points\`, and shifted geometry already produced by \`_neutral_scene_view\`.
- Produces: private \`_analysis_view["b2_boundary_diagnostics"]\` data only; no new \`scene_contract.py\` record and no public enum.

- [ ] **Step 1: Define the exact local diagnostic shape before writing code.**

Use a JSON-safe dictionary with these keys and meanings:

\`\`\`python
{
    "schema": "d6-b2-neutral-scene-diagnostics/v1",
    "evidence_class": "source_fact_and_refusal_plumbing",
    "domain_scope": {
        "status": "computed" | "not_available",
        "geometry_refs": [...],
        "shell_record_ids": [...],
        "promotion": "refused",
        "reason": "...",
    },
    "physical_occupancy": [
        {
            "source_id": "...",
            "source_role": "...",
            "geometry_refs": [...],
            "included": True,
        },
    ],
    "boundary_support": [
        {
            "source_id": "...",
            "candidate_segment_ids": [...],
            "conditional_support": False,
            "local_diagnostic_state": "diagnostic_only",
            "reason": "b2_loop_closure_policy_deferred",
            "source_refs": [...],
        },
    ],
    "candidate_polygon_validity": {
        "status": "not_available",
        "reason": "production_candidate_polygon_not_available",
        "source_refs": [...],
    },
    "source_components": {
        "status": "not_available",
        "reason": "production_source_connectivity_projection_not_available",
        "source_segment_ids": [...],
    },
    "openings": [...],
    "downstream": {
        "subtraction": "refused",
        "free_space": "not_evaluated",
        "route": "not_evaluated",
    },
}
\`\`\`

The strings above are local diagnostic values inside a private compatibility view. They are not a public status enum.

- [ ] **Step 2: Add \`_domain_shell_record_ids(scene, records)\` with no tolerance input.**

The helper must return only record IDs that represent the explicit domain shell. It may use exact source identity, explicit \`analysis_domain.geometry_refs\`, and source role. It must preserve records whose role is \`wall\`, \`boundary\`, or \`column\` even when their geometry references overlap a domain geometry reference.

If the existing source records do not contain enough identity to distinguish a domain shell from a wall/column, raise a documented implementation blocker in the evidence record instead of using geometric proximity, \`geometry_tolerance\`, \`topology_tolerance\`, or a guessed role.

- [ ] **Step 3: Add \`_opening_local_diagnostic_state(opening)\` and \`_b2_opening_diagnostic(opening, shifted_geometry)\`.**

Derive local diagnostic facts only from existing \`SourceOpening\` fields and \`UncertaintyRecord\` values:

- empty \`host_refs\` → \`not_available\`, reason \`missing_host_refs\`;
- empty \`geometry_refs\` → \`not_available\`, reason \`missing_geometry_refs\`;
- an explicit uncertainty code containing \`unsupported\` → \`unsupported\`;
- an explicit uncertainty code containing \`conflict\` → \`conflict\`;
- an explicit uncertainty code containing \`invalid\` or \`malformed\` → \`invalid\`;
- otherwise, with both references present, use \`diagnostic_only\` because no production opening qualification policy is approved.

Every opening diagnostic must include \`id\`, \`source_id\`, \`host_refs\`, \`geometry_refs\`, \`opening_kind\`, \`provenance\`, serialized \`uncertainties\`, \`local_diagnostic_state\`, \`source_refs\`, and \`subtraction_performed=False\`. Do not construct passage width, open/closed state, route access, or derived subtraction geometry.

- [ ] **Step 4: Add \`_b2_boundary_diagnostics(scene, records, shifted_geometry, domain_shell_record_ids)\`.**

Populate physical occupancy from the existing physical records and include every wall/column record that the view currently considers physical. Populate \`candidate_segment_ids\` only with source IDs already present in the view; do not infer contact, loop closure, polygon validity, or connectivity. Set conditional support to \`False\` with the local reason \`b2_loop_closure_policy_deferred\`.

Set candidate polygon validity and source components to \`not_available\` unless a pre-existing factual record already supplies that exact observation. Never compute a new polygon or connectivity result in this task.

Set domain promotion to \`refused\` and preserve the reason that promotion is not authorized by this B2 plumbing task. Keep downstream subtraction \`refused\` and free-space/route \`not_evaluated\`.

- [ ] **Step 5: Add focused tests for the diagnostic projection.**

Add tests in \`test/test_neutral_scene_analysis_regression.py\` that construct the existing minimal Neutral Scene fixture and assert:

\`\`\`python
view = analysis_scene_view(scene)
diagnostics = view["_analysis_view"]["b2_boundary_diagnostics"]

assert diagnostics["schema"] == "d6-b2-neutral-scene-diagnostics/v1"
assert diagnostics["downstream"]["subtraction"] == "refused"
assert diagnostics["downstream"]["free_space"] == "not_evaluated"
assert diagnostics["candidate_polygon_validity"]["status"] == "not_available"
assert diagnostics["source_components"]["status"] == "not_available"
assert all(item["conditional_support"] is False for item in diagnostics["boundary_support"])
\`\`\`

Add one fixture with a wall and a column whose source facts carry different uncertainty records; assert both source IDs and uncertainty references remain present and neither record is promoted.

- [ ] **Step 6: Run the focused test file.**

Run: \`pixi run pytest test/test_neutral_scene_analysis_regression.py -q\`

Expected: PASS for the existing tests plus the new B2 diagnostic assertions.

---

### Task 2: Separate explicit domain shell exclusion from physical occupancy and walking blockers

**Files:**
- Modify: \`features/neutral_scene_views.py\`, \`_neutral_scene_view\` and \`_channel_blocker_records\`.
- Test: \`test/test_neutral_scene_analysis_regression.py\`.

**Interfaces:**
- Consumes: \`domain_shell_record_ids\` from Task 1 and the existing \`records_by_id\`.
- Produces: unchanged legacy \`physical_blockers\` compatibility field; corrected \`physical_occupancy\` and \`walk_blockers\` membership; private domain-scope diagnostics.

- [ ] **Step 1: Extend \`_channel_blocker_records\` with record-ID exclusion.**

Use this exact shape:

\`\`\`python
def _channel_blocker_records(
    records_by_id: Mapping[str, dict],
    channel_evidence: Mapping[str, dict[str, object]],
    *,
    channel: str,
    offset: tuple[float, float],
    excluded_geometry_refs: set[str] | None = None,
    excluded_record_ids: set[str] | None = None,
) -> list[dict]:
\`\`\`

Check \`excluded_record_ids\` before the legacy geometry-reference exclusion. Keep the old reference exclusion available for existing callers; the B2 path must pass explicit shell IDs so a wall/column sharing a domain geometry reference is not removed.

- [ ] **Step 2: Change the B2 path in \`_neutral_scene_view\`.**

Compute \`domain_shell_record_ids\` once. Build \`physical_mass_records\` by excluding only those shell record IDs, while retaining wall and column records. Pass the same shell IDs to \`_channel_blocker_records\` for walking blockers. Leave visibility blocker behavior unchanged unless an existing test demonstrates that it drops a source record solely because of domain overlap.

Do not remove or rewrite the old \`physical_blockers\` field; legacy boundary consumers must continue to receive the same record bucket.

- [ ] **Step 3: Add a regression fixture for shared geometry references.**

Create a minimal scene where:

- one explicit domain geometry is present;
- a wall record and a column record reference that same domain geometry;
- a separate domain-shell record is identifiable by the explicit domain identity.

Assert that the domain shell is excluded from \`physical_occupancy\` and \`walk_blockers\`, while the wall and column remain in both collections when their channel evidence is usable.

- [ ] **Step 4: Verify no B2 helper reads tolerances.**

Use a source inspection assertion or a direct test fixture with different context tolerance values to prove the B2 diagnostic payload is unchanged. Existing channel evidence may continue to use \`geometry_tolerance\` for its already-approved height-band behavior; the new B2 diagnostic functions must not accept or read either tolerance.

- [ ] **Step 5: Run the focused regression tests.**

Run: \`pixi run pytest test/test_neutral_scene_analysis_regression.py -q\`

Expected: PASS, with explicit evidence that domain shell and wall/column physical occupancy are separate.

---

### Task 3: Preserve opening adapter distinctions while exposing refusal provenance

**Files:**
- Modify: \`features/neutral_scene_views.py\`, \`_opening_records\` only if a renderable opening record needs additional provenance fields.
- Read-only verification targets: \`adapters/ifc_bonsai.py:_native_opening_records\`, \`adapters/svg_scene.py:_source_openings\`, \`adapters/blender_geometry.py:_validate_scene_references\`.
- Tests: \`test/test_ifc_bonsai_adapter.py\`, \`test/test_svg_scene_adapter.py\`, \`test/test_blender_geometry_adapter.py\`.

**Interfaces:**
- Consumes: existing \`SourceOpening\` records and adapter-specific uncertainty/refusal behavior.
- Produces: local B2 opening diagnostics with source lineage and \`subtraction_performed=False\`; no adapter normalization.

- [ ] **Step 1: Verify current IFC source behavior before editing.**

Run the existing IFC adapter tests that cover \`IfcOpeningElement\`, missing geometry, host relations, and JSON round trips. Confirm that \`_native_opening_records\` preserves host refs, geometry refs, opening kind, provenance, and missing-geometry uncertainty.

If a required source fact is absent, add the smallest adapter-local uncertainty record in \`_native_opening_records\` with a unique source code and provenance details. Do not add a public status enum, derived subtraction field, or host inference.

- [ ] **Step 2: Add the SVG distinction test.**

Use the existing structured SVG fixture pattern with one valid host and one unresolved host reference. Assert that \`_source_openings\` keeps the valid host ref, omits only the unresolved ref, and emits the existing adapter uncertainty. Then assert the B2 diagnostic reports missing/incomplete host evidence and refuses subtraction.

- [ ] **Step 3: Add the Blender distinction test.**

Use the existing \`load_blender_neutral_scene\` fixture with a dangling opening host or geometry reference. Assert that \`_validate_scene_references\` still raises its existing validation error. Do not convert this error into an uncertain scene or silently omit the reference.

- [ ] **Step 4: Add the IFC diagnostic test.**

Use the existing IFC fixture builder in \`test/test_ifc_bonsai_adapter.py\` to create a source opening with one of the existing incomplete evidence forms. Assert that the Neutral Scene keeps the source opening record and the B2 view reports the local refusal state with all available source refs and \`subtraction_performed=False\`.

- [ ] **Step 5: Run the adapter-focused tests.**

Run:

\`\`\`bash
pixi run pytest test/test_ifc_bonsai_adapter.py test/test_svg_scene_adapter.py test/test_blender_geometry_adapter.py -q
\`\`\`

Expected: PASS, with SVG omission/uncertainty and Blender rejection remaining distinct.

---

### Task 4: Preserve downstream deferred statuses and legacy compatibility

**Files:**
- Read-only compatibility target: \`features/group_self_description.py:_space_observations\`.
- Modify only if a focused test proves refusal evidence is otherwise lost from the existing compatibility view.
- Test: \`test/test_group_self_description.py\`.

**Interfaces:**
- Consumes: \`analysis_scene_view(scene)\` and its private \`_analysis_view["b2_boundary_diagnostics"]\`.
- Produces: existing \`space_observations.free_space\`, \`connectivity\`, and \`bottleneck_profile\` statuses remain \`not_available\`; no B2 topology result is exposed as a computed value.

- [ ] **Step 1: Confirm the existing group output boundary.**

Read \`_space_observations\` and \`_json_ready\` behavior. Confirm that current public group output does not serialize private \`_analysis_view\` keys. Keep that boundary unless the existing contract tests show a loss of an already-approved refusal fact.

- [ ] **Step 2: Add a compatibility regression test.**

For a Neutral Scene with an explicit domain and a refused B2 opening/column observation, call \`describe_group_relations(scene)\` and assert:

\`\`\`python
space = result["space_observations"]
assert space["free_space"]["status"] == "not_available"
assert space["connectivity"]["status"] == "not_available"
assert space["bottleneck_profile"]["status"] == "not_available"
\`\`\`

Also assert that no \`status\` field from the private B2 diagnostic becomes a public unified enum in the returned group payload.

- [ ] **Step 3: Run the focused group tests.**

Run: \`pixi run pytest test/test_group_self_description.py -q\`

Expected: PASS with unchanged group schema and deferred space measurements.

---

### Task 5: Produce bounded implementation evidence and perform the implementation gate

**Files:**
- Create: \`docs/project/evidence/d6-b2-provenance-refusal-implementation-evidence.md\`.
- Create: \`docs/project/evidence/d6-b2-provenance-refusal-implementation-manifest.json\`.
- Modify: only the exact production/test files listed in Tasks 1–4.
- Do not modify: \`docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-owner-decision.md\`; it remains the approval baseline.

**Interfaces:**
- Consumes: focused test results, Git diff, source-scope audit, and existing B2 synthetic evidence.
- Produces: append-only evidence record and manifest that distinguish production implementation evidence from synthetic design evidence.

- [ ] **Step 1: Run only the focused validation set.**

Run:

\`\`\`bash
pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_group_self_description.py test/test_ifc_bonsai_adapter.py test/test_svg_scene_adapter.py test/test_blender_geometry_adapter.py -q
git diff --check
\`\`\`

Do not run the full suite unless a focused failure requires a broader diagnostic. Do not run real IFC geometry, Blender rendering, space-field backend, Bayesian/ML, or unrelated historical probes.

- [ ] **Step 2: Perform a declared-file scope audit.**

Confirm that only the exact implementation files, focused tests, evidence record, and manifest changed. Preserve all pre-existing dirty/untracked files. Do not use \`git add .\`.

- [ ] **Step 3: Write the evidence record.**

The record must state:

- implementation branch and commit;
- exact files changed;
- focused commands and exit codes;
- source facts preserved;
- domain shell/physical occupancy separation;
- opening refusal and adapter distinction;
- candidate polygon/source connectivity remain unavailable unless already factual;
- no production tolerance or selector was selected;
- no real IFC or Blender validation was performed;
- no free-space, route, resolution, UI, Bayesian/ML, or merge decision was made.

- [ ] **Step 4: Hash declared artifacts.**

The manifest must contain byte count and SHA-256 for each declared file, omit self-hashing, and record the validation commands and scope audit result.

- [ ] **Step 5: Stop at independent implementation review.**

Do not merge or select a production backend. Send the implementation commit and evidence record to a separate review session. Stop with:

\`STOP FOR D6 B2 PROVENANCE/REFUSAL IMPLEMENTATION REVIEW\`

---

## Self-Review

- [x] Owner-approved data boundary is covered by Tasks 1–3.
- [x] Domain shell versus wall/column physical occupancy is explicitly covered by Task 2.
- [x] SVG unresolved-host omission and Blender dangling-reference rejection remain distinct in Task 3.
- [x] Existing tolerance fields are excluded from new B2 plumbing and explicitly guarded.
- [x] Candidate polygon validity and source connectivity remain separate and unevaluated in Task 1.
- [x] Opening missing/invalid/partial/conflict/unsupported/diagnostic-only observations retain source lineage and refuse subtraction.
- [x] Legacy \`describe_group_relations\` output remains unchanged unless a focused regression proves refusal evidence is lost.
- [x] Deferred selector, public status enum, Bayesian/ML, free-space, route, resolution, UI, real-IFC, and merge decisions are explicitly excluded.
- [x] Synthetic evidence is not described as real IFC/Blender validation.
- [x] Placeholder scan performed: no \`TBD\`, \`TODO\`, or unassigned implementation step appears in this plan.
- [x] Type/function consistency checked against current signatures: \`analysis_scene_view\`, \`_neutral_scene_view\`, \`_channel_blocker_records\`, \`_opening_records\`, \`_native_opening_records\`, \`_source_openings\`, \`_validate_scene_references\`, \`_space_observations\`, and \`_json_ready\`.

Plan complete and saved to \`docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation.md\`. This plan is ready for a separately delegated implementation session after independent plan review.

