# Field Result Envelope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the shared immutable `FieldResultEnvelope` boundary for cacheable, analyzable, UI-compatible, and visualizable field results without implementing group candidate inference.

**Architecture:** Extend the existing field core with raw result status, structured channel records, deterministic cache identity, and a compatibility projection to `FieldSample`. Add an envelope-to-manifest adapter beside the existing `build_field_layer_manifest`; keep current free-space producers and consumers unchanged and preserve raw relation status in additive manifest fields.

**Tech Stack:** Python 3.12, existing dataclasses/enums and deep-freeze helper, Python standard-library JSON/SHA-256 canonicalization, pytest, Pixi.

**Spec:** `docs/superpowers/specs/2026-10-21-field-result-envelope-design.md`

## Global Constraints

- Do not implement group candidate generation, aggregation, scalar membership strength, fixed weights, Bayesian/ML inference, or a selector.
- Reuse `features.field_core._freeze` and the existing `FieldQuery`, `FieldSample`, `FieldStatus`, and manifest conventions.
- Preserve raw statuses and structured evidence; never replace missing or invalid evidence with numeric zero.
- `FieldSample` is a compatibility projection only; return no projection when it would discard structured evidence or violate status-gated values.
- Cache identity must include canonical target, query, admitted channel declarations, source/input fingerprints, recipe fingerprint, algorithm version, and schema version.
- Existing free-space APIs and `field-layer-manifest/v1` consumers remain backward compatible.
- Every new or modified project-owned function has an English-first docstring; important serialization and adapter decisions get concise why-comments.
- Use jj for checkpoints and preserve unrelated working-tree changes.

## Review Focus

- **Partial evidence with a usable value:** the envelope keeps channel records and raw `partial`; `FieldSample` projection returns `None` rather than dropping them. Test in Task 1.
- **Admitted but unavailable channel:** `channel_set` and a null-observation status record remain in the result and cache fingerprint. Test in Task 1.
- **Target and traversal-order invariance:** `object × candidate_group` target identity and channel declarations produce stable identity independent of input order. Test in Task 1.
- **Manifest compatibility without false certainty:** an unprojectable result renders with conservative `unknown` fallback while preserving `raw_status` and channel records. Test in Task 2.
- **Existing free-space regression:** the current `FieldSample` manifest output remains byte-equivalent for existing samples. Test in Task 2.

---

### Task 1: Add the immutable result envelope and cache identity to the field core

**Files:**
- Modify: `features/field_core.py`
- Test: `test/test_field_core.py`

**Interfaces:**
- Produces `FieldResultStatus(str, Enum)` with `computed`, `partial`, `not_evaluated`, `not_available`, `invalid`, `outside`, and `ambiguous`.
- Produces frozen `EvidenceChannelRecord` with `channel`, `required`, `polarity`, `observation`, `support`, `units`, `status`, `source_ids`, `provenance`, and `explanation`.
- Produces frozen `FieldResultEnvelope` with canonical target, `FieldQuery`, raw status, sorted `channel_set`, channel records, support, optional projection metadata, provenance, cache identity, visualization reference, and explanation.
- Produces `build_field_result_cache_identity(*, target, query, channel_declarations, input_fingerprint, source_fingerprint, recipe_fingerprint, algorithm_version, schema_version) -> dict[str, str]`; it returns the required fingerprint components plus a SHA-256 `identity` over canonical JSON.
- Produces `project_field_sample(result: FieldResultEnvelope) -> FieldSample[Any] | None`; it returns a sample only when the envelope projection and value obey existing `FieldSample` invariants.

- [ ] **Step 1: Write failing envelope and identity tests**

  Add focused tests for:

  - exact raw status vocabulary and immutable nested channel/query/provenance data;
  - sorted unique `channel_set`, required-channel metadata, and rejection of a record outside the set;
  - non-empty target kind/id/identity, channel names, required provenance, and non-computed explanations;
  - partial evidence retaining a structured value while `project_field_sample` returns `None`;
  - valid established projection carrying structured channel value, support, source ids, query, provenance, raw status, and mapping reason;
  - deterministic cache identity under reordered declarations and changed identity when source, channel, recipe, or query input changes;
  - admitted unavailable channels remaining represented by null-observation records.

- [ ] **Step 2: Run the focused tests and verify they fail for the missing contract**

  Run: `pixi run pytest test/test_field_core.py -q`

  Expected: failures for the new symbols and behaviors, while the existing field-core tests continue to identify the baseline behavior.

- [ ] **Step 3: Implement the minimal core contract in `features/field_core.py`**

  Add the raw-status enum and frozen channel/envelope dataclasses beside the existing field contracts. Normalize/sort channel declarations, deep-freeze JSON-safe payloads, validate status/value/explanation/provenance/cache invariants, and serialize canonical target/query/channel declarations with standard-library JSON and SHA-256 for cache identity. Keep `FieldSample` unchanged. Make `project_field_sample` construct a structured channel mapping only for a semantically valid six-state projection; otherwise return `None`.

- [ ] **Step 4: Run the focused core tests and verify they pass**

  Run: `pixi run pytest test/test_field_core.py -q`

  Expected: PASS, including all pre-existing field-core tests and the new envelope tests.

- [ ] **Step 5: Commit the core contract**

  ```text
  jj commit -m "feat: add immutable field result envelope"
  ```

### Task 2: Add the relation-aware visualization manifest adapter

**Files:**
- Modify: `features/space_field_visualization.py`
- Test: `test/test_space_field_visualization.py`

**Interfaces:**
- Produces `build_field_result_layer_manifest(*, layer_id: str, channel: str, results: Iterable[FieldResultEnvelope]) -> dict[str, Any]`.
- Keeps the existing `build_field_layer_manifest` signature and output behavior unchanged for `FieldSample` inputs.
- Emits additive relation record fields `raw_status`, `channel_set`, and `channel_records`; preserves existing manifest fields and uses `status="unknown"` plus `visual_state="unknown"` as the conservative display fallback when no `FieldSample` projection exists.

- [ ] **Step 1: Write failing manifest adapter tests**

  Add tests for established projected envelopes, partial/unprojectable envelopes, admitted unavailable channels, raw status/channel-record preservation, deterministic JSON serialization, and the unchanged existing `FieldSample` manifest cases.

- [ ] **Step 2: Run the visualization tests and verify the new adapter tests fail**

  Run: `pixi run pytest test/test_space_field_visualization.py -q`

  Expected: failures only for the new envelope adapter behavior; existing manifest tests remain the regression baseline.

- [ ] **Step 3: Implement `build_field_result_layer_manifest`**

  Reuse `_json_value`, existing manifest field names, and `_visual_state`. For each envelope, use `project_field_sample` when available; otherwise emit conservative `unknown` display fields, the mapping explanation, raw status, normalized channel set, and serialized channel records. Do not add UI-specific payloads to the envelope and do not modify existing free-space record semantics.

- [ ] **Step 4: Run the visualization tests and verify they pass**

  Run: `pixi run pytest test/test_space_field_visualization.py -q`

  Expected: PASS for the old `FieldSample` manifest contract and all new envelope projection cases.

- [ ] **Step 5: Commit the manifest adapter**

  ```text
  jj commit -m "feat: adapt field result envelopes to visualization manifests"
  ```

### Task 3: Synchronize the architecture map and contract references

**Files:**
- Modify: `docs/software-architecture.md`
- Modify: `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- Test: none (documentation consistency is checked in the final verification task)

**Interfaces:**
- Documents `FieldResultEnvelope` as the shared output/audit boundary, with `FieldSample` and `field-layer-manifest/v1` as projections.
- Records that the implementation slice does not add group inference, candidate selection, scoring, or a job/result registry.

- [ ] **Step 1: Update the unified Field-kernel section**

  State the new module symbols, raw-status preservation, cache identity boundary, conservative manifest fallback, and unchanged free-space compatibility. Keep planned group inference and scalar aggregation explicitly future/design-only.

- [ ] **Step 2: Update the durable architecture memory**

  Add the same boundary and non-goals to the shared field-kernel memory without claiming that group inference is implemented.

- [ ] **Step 3: Run the documentation consistency checks**

  Run: `rg -n "FieldResultEnvelope|field-result-envelope/v1|group candidate|scalar|job/result" docs/software-architecture.md docs/indoor_layout_evaluation_matrix_architecture_memory.md`

  Expected: both architecture documents identify the envelope boundary and retain the explicit non-goals.

- [ ] **Step 4: Commit the architecture synchronization**

  ```text
  jj commit -m "docs: record field result envelope architecture boundary"
  ```

### Task 4: Run the bounded contract verification and close the plan checkpoint

**Files:**
- Test: `test/test_field_core.py`
- Test: `test/test_space_field_visualization.py`

**Interfaces:**
- Verifies only the shared output contract and its projections. It must not call or alter group candidate generation.

- [ ] **Step 1: Run the bounded test suite**

  Run: `pixi run pytest test/test_field_core.py test/test_space_field_visualization.py -q`

  Expected: PASS with no changes to group-inference algorithm behavior.

- [ ] **Step 2: Run whitespace and placeholder checks on changed documentation**

  Check the changed Markdown files for trailing whitespace, unbalanced code fences, and unfinished placeholder markers.

  Expected: no findings.

- [ ] **Step 3: Inspect the final jj diff and status**

  Run: `jj status --no-pager` and `jj diff --no-pager --stat`.

  Expected: only the planned core, manifest, tests, and architecture-document paths are present; no group inference algorithm or Spec008 files are touched. No additional commit is needed when this verification is clean.

