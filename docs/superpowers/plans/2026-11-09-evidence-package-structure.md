# Evidence Package Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small shared contract for cross-package channel references and readback while preserving all existing evidence channels and package outputs.

**Architecture:** Extend the existing `EvidencePackageOutput` with explicit external dependencies and stable `EvidencePackageChannelReference` values. Readback validates package/output/target/channel identity; only fresh channels are exposed as usable input, while stale channels remain audit-only. Published outputs retain dependency references, not source output objects. Output identity includes dependencies, direct self-dependencies are rejected, and a DFS helper rejects cycles when given the complete graph. Existing packages remain unchanged unless they opt into dependencies.

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
- Add optional `dependencies` to `EvidencePackageOutput` and `EvidencePackage.evaluate(..., dependencies=())`.

- [x] Add tests for dependency identity, readback mismatch, and cycle rejection.
- [x] Implement the dataclasses, output validation, identity inclusion, readback, and DFS validation.
- [x] Run focused output/freshness tests.

### Task 2: Documentation and package status propagation

**Files:**
- Modify: `docs/project/group-evidence-design-index.md`
- Modify: `docs/software-architecture.md`
- Add: `docs/project/evidence/evidence-package-structure.md`

- [x] Add the compact package structure diagram and plain-language explanation.
- [x] Record that cross-package readback is supported by the shared contract but no current package consumes distance/potential across package boundaries.
- [x] Record that source channel preservation and dependency-driven stale status remain mandatory.

### Task 3: Verification and checkpoint

**Files:**
- No production files beyond Tasks 1–2.

- [ ] Run focused tests for core output, freshness, free-space, distance, and potential packages.
- [ ] Run the full package test subset under Pixi.
- [x] Inspect retained IFC manifests and report whether a real replay is available without recomputation.
- [x] Create a task-scoped JJ checkpoint and report the exact commit and remaining risk: bookmark `codex/evidence-package-cross-package-readback` points to `932f5fd0`; the line is based on `e86c8cd1` and has not been integrated into the current main worktree.
- [ ] Integrate the named workline into the intended mainline after comparing `e86c8cd1`/`a336524b`/`932f5fd0` with the current main worktree, preserving unrelated dirty changes and resolving the existing `codex/free-space-evidence-package` bookmark conflict; rerun the package test subset after integration.
