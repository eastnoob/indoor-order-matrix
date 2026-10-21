# Authored Group Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Neutral Scene consumers one auditable inventory of explicitly authored furniture groups, resolving the confirmed input-contract mismatch as the first bounded implementation slice.

**Architecture:** Add one private inventory projection over `NeutralSceneV2` source facts and have `describe_group_relations` consume that projection. A future attribution field reads this inventory directly and never derives membership from `analysis_scene_view`'s scalar `furniture_group`. Keep the old `group`, `region`, and `furniture_group` projections unchanged for current inference/evaluator callers. The candidate×scope field and profile have already passed design-only representation checks, so this slice replays those diagnostics instead of adding a production field layer before real-scene and readout gates pass.

**Tech Stack:** Python 3.12.13, Pixi, Python standard library, pytest.

**Spec:** [Furniture group attribution evidence field and non-probabilistic strength spec](../../project/grouping-strength-spec.md)

## Global Constraints

- Only an explicit `furniture_group` role qualifies a Neutral Scene authored group; member object roles do not infer group eligibility.
- Preserve raw references and provenance; deduplicate repeated member identities only for membership and evidence counting.
- Preserve shared object membership in every authored group that names it; never reduce the inventory to one winning group.
- Keep `canonical_layout_contract` duplicate and dangling-reference rejection unchanged; source audit must occur before canonical validation when raw malformed facts need preservation.
- Keep legacy dictionary input limited to facts its per-object markers can express; do not synthesize empty groups, dangling references, or shared memberships.
- Do not add probability semantics, a scalar `M` formula, weights, thresholds, cross-candidate normalization, a winning candidate, a public API, UI, or `room_analysis_model` fields.
- Use the configured Pixi environment and `jj` for any later workspace checkpoints; preserve unrelated working-copy changes.

---

### Task 1: Specify the input inventory with regression tests

**Files:**
- Create: `test/test_authored_group_inventory.py`
- Modify only if coverage is missing: `test/test_canonical_layout_contract.py`

**Interface:**
- The tests target a private `_build_authored_group_inventory(scene: NeutralSceneV2) -> dict[str, object]` helper returning `authored_groups`, `eligible_groups`, `excluded_groups`, `input_audit`, and `member_group_ids`.
- Each authored-group record preserves `group_id`, `source_id`, `provenance`, raw `member_refs`, unique member IDs, duplicate refs, unresolved refs, and a completeness status. `authored_groups` includes explicit empty groups for audit; `eligible_groups` excludes them from candidate/field scope.

- [x] Add one Neutral Scene fixture containing an explicit empty group, an explicit group with a repeated member and one dangling reference, two explicit groups sharing one object, and one generic all-furniture group.
- [x] Assert the empty group is audit-only, the generic group is excluded with a reason, duplicates remain visible but unique membership counts once, dangling refs remain visible with partial/invalid status, and the shared object maps to both groups.
- [x] Confirm the canonical contract still rejects duplicate and dangling member refs; add only the missing rejection assertion, without relaxing validation.
- [x] Run `pixi run pytest test/test_authored_group_inventory.py test/test_canonical_layout_contract.py -q` and confirm the new inventory tests fail because the helper does not exist yet.

### Task 2: Add the private Neutral Scene group inventory

**Files:**
- Create: `features/_authored_group_inventory.py`
- Test: `test/test_authored_group_inventory.py`

**Interface:**
- Implement `_build_authored_group_inventory(scene: NeutralSceneV2) -> dict[str, object]` with the keys and per-group fields asserted in Task 1.
- `authored_groups` contains exact `group_role == "furniture_group"` source facts, including empty groups. `eligible_groups` contains only non-empty authored groups; empty explicit groups also appear in `input_audit` and never enter candidate/field scope.
- A group with both resolved and unresolved refs is `partial`; a non-empty group with no resolved refs is `invalid`; a group with all refs resolved is `computed`.
- `member_group_ids` maps each resolved source object ID to every eligible group ID that references it. Preserve authored group order in raw records and make diagnostics deterministic.

- [x] Implement the helper using the existing `NeutralSceneV2.authored_groups` and `source_objects`; do not infer eligibility from furniture roles or names.
- [x] Preserve each group's original references, while deriving unique membership IDs and duplicate/unresolved diagnostics separately.
- [x] Run `pixi run pytest test/test_authored_group_inventory.py test/test_canonical_layout_contract.py -q` and require all tests to pass.

### Task 3: Connect authored group description to the shared inventory

**Files:**
- Modify: `features/group_self_description.py:_neutral_inputs`
- Modify: `docs/software-architecture.md`
- Test: `test/test_group_self_description.py`
- Test only if existing coverage does not lock it: `test/test_neutral_scene_analysis_regression.py`

- [x] Make `_neutral_inputs` build Neutral Scene group descriptions from `authored_groups`, using unique member identities for calculations and retaining unresolved/duplicate facts in its input inventory.
- [x] Add focused tests proving the standalone group result excludes generic groups, retains empty-group audit and shared membership, and does not double-count repeated references in geometry.
- [x] Keep `analysis_scene_view` scalar outputs unchanged and add no new view fields; if needed, add one regression assertion for the existing generic/shared-group compatibility projection. Never use that lossy view to build attribution records.
- [x] Update the architecture map to show the private inventory helper and its consumer; leave `neutral_scene_views.py`, `scene_inference`, evaluator outputs, canonical validation, public exports, and `room_analysis_model` shape unchanged.
- [x] Run `pixi run pytest test/test_authored_group_inventory.py test/test_scene_contract.py test/test_canonical_layout_contract.py test/test_group_self_description.py -q`.

### Task 4: Replay the reviewed design diagnostics

**Files:**
- Read/replay: `scripts/design/group_level/run_group_attribution_field_slice.py`
- Read/replay: `scripts/design/group_level/run_group_attribution_protocol_followup.py`
- Update only if an invariant fails: corresponding fixture, result report, and runner.

- [x] Run `pixi run python scripts/design/group_level/run_group_attribution_field_slice.py` and `pixi run python scripts/design/group_level/run_group_attribution_protocol_followup.py` twice each.
- [x] Confirm the logical result hashes are stable and retain the existing design-only limits: supplied readouts do not validate an evidence mapping; endpoint fixtures do not validate production veto propagation; fixture profiles do not calibrate real intensity.
- [x] Add a fixture case only for a newly exposed gap between the shared inventory and the already-tested candidate×scope field; do not duplicate the existing driver, modifier, status, coverage, singleton, or profile matrices.
- [x] Record any production-path gap as unresolved rather than rewriting the fixture result as production validation.

## Gates after this plan

- Before selecting a scalar readout or implementing a production strength recipe, compare same-source, proposal-source-ablated, and independent evidence using a defensible readout mapping. If that mapping or independent evidence is unavailable, keep leakage and strength interpretation unresolved.
- Blind-review a suitable independent real scene with authored group labels masked. If no suitable scene is available, leave real-scene interpretability open.
- Measure search cost against Stage A's 37-node baseline only after candidate recipe semantics are stable; report bounded searches as incomplete.
- Any scalar `M`, weights, threshold, recipe winner, or exported field API requires a later reviewed spec and explicit authorization.

## Self-review

- Spec coverage: input qualification and identity are Tasks 1–3; full field/profile representation is already exercised by the two replayed design diagnostics; this first slice does not create a production candidate or strength layer. Real-scene interpretation, leakage, scalar mapping, and search cost remain explicit gates.
- Boundary check: the plan does not alter strict canonical validation or the legacy scalar view, broaden the legacy mapping, change inference/evaluator behavior, or add a public model field.
- No production strength formula, probability model, winner rule, or calibration threshold is selected.
