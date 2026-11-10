# Evidence Package Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add shared cross-package channel references and readback while preserving all existing evidence channels and package outputs; continue saved-snapshot rollout in the existing integration cleanup plan.

**Architecture:** Extend the existing `EvidencePackageOutput` with explicit external dependencies and stable full package/output/target/channel references. Resolver/context exposes fresh channels as usable input and stale/unavailable typed sources as redacted audit metadata. Fixed-v1 saved readers, serialized content fingerprints and complete explicit graph/declaration checks continue in the integration plan. Existing packages retain their outputs; the concrete consumer faithfully reads selected existing channels without adding a formula.

**Tech Stack:** Python 3.12, dataclasses, existing `field_core.py` contracts, pytest, JJ workspace.

**Spec:** `docs/superpowers/specs/2026-11-09-evidence-package-cross-package-readback-design.md`

## Global Constraints

- Preserve every existing source and derived channel.
- Do not introduce a registry, scheduler, new measurement layer, or package-specific algorithm.
- Missing, stale, invalid, or ambiguous external evidence must not become numeric zero.
- Keep package identity deterministic and JSON serializable.
- Use English docstrings/comments for modified code.

---

### Task 1: Shared cross-package references

**Files:**
- Modify: `features/field_core.py`
- Test: `test/test_evidence_package_output.py`
- Test: `test/test_evidence_package_freshness.py`

**Interfaces:**
- Add frozen `EvidencePackageChannelReference(package_id, output_identity, target_identity, channel)`.
- Add `EvidencePackageDependency(package_id, output_identity, channels)`.
- Add `read_evidence_package_channel(output, reference) -> EvidenceOutputChannel` and a freshness-gated resolver for package callbacks.
- Add `validate_evidence_package_dependency_graph(graph) -> None`.
- Add optional `dependencies` and `dependency_graph` to `EvidencePackageOutput`/`EvidencePackage.evaluate` execution flow without changing legacy callback signatures.

- [x] Add tests for dependency identity, readback mismatch, and cycle rejection.
- [x] Implement the dataclasses, output validation, identity inclusion, readback, and DFS validation.
- [x] Run focused output/freshness tests.

### Task 2: Documentation and package status propagation

**Files:**
- Modify: `docs/project/group-evidence-design-index.md`
- Modify: `docs/software-architecture.md`
- Add: `docs/project/evidence/evidence-package-structure.md`

- [x] Add the compact package structure diagram and plain-language explanation.
- [x] Record the initial shared-contract boundary; the 2026-11-10 integration continuation adds a distinct faithful existing-channel readback package, while distance-to-potential business integration remains unimplemented.
- [x] Record that source channel preservation and dependency-driven stale status remain mandatory.

### Task 3: Verification and checkpoint

**Files:**
- No production files beyond Tasks 1–2.

- [ ] Run focused tests for core output, freshness, free-space, distance, and potential packages.
- [ ] Run the full package test subset under Pixi.
- [x] Inspect retained IFC manifests and report whether a real replay is available without recomputation.
- [x] Create the initial task-scoped JJ checkpoint; the historical `932f5fd0` was followed by reference checkpoint `9f071266`. The isolated integration bookmark has core-subset checkpoint `51b8c6e7`; no mainline merge is implied.
- [ ] Integrate the named workline into the intended mainline only after the separate cleanup plan verifies the candidate; preserve unrelated dirty changes and leave the existing `codex/free-space-evidence-package` bookmark conflict outside this slice.

The remaining saved-output acceptance work belongs to Tasks 6–8 of the existing
[integration cleanup plan](2026-11-09-evidence-package-integration-cleanup.md),
not a new plan. It covers fixed-schema roundtrip/content integrity, current
contract gates bound through independent `current_source_envelopes` signatures, two distinct distance targets of the same channel, existing
package replay and documentation. This original checklist retains historical
verification gaps until those actual results are recorded there. Exact potential reexecution uses original producer-envelope order for the historical `per_group` audit list; saved roundtrip preserves content directly.
