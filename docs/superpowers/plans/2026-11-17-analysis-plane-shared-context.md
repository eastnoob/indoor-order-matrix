# Analysis Plane Shared Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a required immutable analysis-plane context to evidence-package calls while preserving package ownership, old wire formats, and unused-plane behavior.

**Architecture:** Add one pure frozen context/resolver module. Extend the shared `EvidencePackage` template at its two business methods, then migrate package/cache/native callers at their existing boundaries. Keep scene/UI selection and native lifecycle in the adapter/UI layer; keep numeric dependency projection in the cache/session adapter and preserve full capture authentication.

**Tech Stack:** Python 3.12 via Pixi, pytest, existing Blender/Bonsai adapters, existing CacheStore and evidence-package serializers.

**Spec:** `docs/superpowers/specs/2026-11-17-analysis-plane-shared-context-design.md`

## Global Constraints

- Preserve the first five `EvidencePackage` constructor positions and existing callback signatures.
- Do not add a `uses_plane` flag, global mutable context, ancestor package, automatic model router, or new numerical algorithm.
- Do not change raw/processed v1 bytes, result references, or existing numerical query identities merely because context was passed.
- Validate context before producer, processor, cache-hit, native request, and job-binding work.
- All modified project-owned functions have English docstrings; important validation/identity steps have why comments.
- Use Pixi for tests; do not launch a non-portable Blender.
- Do not write jj/Git history, push, merge, delete workspaces, or alter unrelated dirty files.

### Task 1: Shared context and EvidencePackage contract

**Files:** `features/package_analysis_context.py`, `features/field_core.py`, related `features/__init__.py` exports and focused field/core tests.

**Interfaces:** Produce `PackageAnalysisContext`, `AnalysisPlaneCatalog`, and `resolve_package_analysis_context(...)`. Extend `EvidencePackage.evaluate()` and `.process_output()` with keyword-only `analysis_context` and `allow_multiple_planes`; pass the frozen context to `EvidencePackageInput` callbacks.

- [x] Add non-empty/type/identity/freeze validation and single/multiple-plane gates.
- [x] Infer only one complete trusted source query plane when context is omitted.
- [x] Run focused contract tests, including callbacks that ignore the context.

### Task 2: Package and output-port call migration

**Files:** `features/group_axis_potential_field.py`, `features/group_axis_output_ports.py`, `features/output_port_cache.py`, other feature package entry points and their tests.

**Interfaces:** Every evaluate/process call resolves or receives the context before cache lookup, producer, or processor execution; cache hits use the same validation path.

- [x] Migrate axis/distance/output-port calls without changing numerical query or wire identity.
- [x] Preserve package-specific geometry/query registration checks.
- [x] Add a cache-hit test showing invalid context is rejected before reuse.

### Task 3: Native/UI plane directory and lifecycle

**Files:** `adapters/bonsai_analysis_plane.py`, `blender_addon/order_analyzer_ui/plane_settings.py`, `blender_addon/order_analyzer_ui/__init__.py`, `blender_addon/order_analyzer_ui/runtime.py`, focused native/UI tests.

**Interfaces:** Native creation remains transactional; settings resolve scene default/package override to one frozen context; request and job binding consume the same resolution; observations and review state are tracked per native identity; undo/redo/load invalidate review as required.

- [x] Allow explicit creation/selection of multiple managed drawings while retaining unambiguous legacy ensure behavior.
- [x] Preserve per-identity observation revisions and old singular property mirrors.
- [x] Test default/override, P1→P2→P1, request-binding consistency, and redo invalidation.

### Task 4: Capture/session numeric dependency projection

**Files:** `adapters/blender_analysis_capture.py`, `adapters/bonsai_live.py`, `adapters/blender_analysis_session.py`, `adapters/free_space_evidence_package.py`, focused cache/session tests.

**Interfaces:** Keep complete capture/source/support authentication and freshness gates. Add only adapter-owned verified physical dependency projection for numeric reuse; old captures without proof remain conservative misses.

- [x] Prove that unused native-camera changes do not alter the numeric physical dependency digest after current consent is re-established.
- [x] Keep external IFC and non-camera dependencies in the numeric digest.
- [x] Verify physical changes still invalidate reuse and no Store-wide admission rule is weakened.

Saved external IFC byte changes remain conservative misses. No camera-private
IFC closure proof or broad source-adoption relaxation was implemented.

### Task 5: Script/readback migration and documentation synchronization

**Files:** Direct script call sites, package contract tests, `docs/software-architecture.md`, and this plan's progress ledger.

- [x] Pass explicit contexts to no-plane readback fixtures without changing fixture bytes.
- [x] Run focused tests for all four tasks, then an independent integration selection.
- [x] Update architecture current/planned boundaries with actual implemented behavior and record unverified native/IFC limits.

Acceptance evidence, exact candidate bytes, review verdicts and the retained
failed-attempt history are recorded in
`docs/project/evidence/analysis-plane-shared-context-verification-2026-11-17.md`.
No task delivery commit or push was authorized or performed.

## Acceptance commands

```text
$env:PYTHONPATH='.'
pixi run python -m pytest test/test_field_core.py test/test_evidence_package_output.py test/test_evidence_package_processing.py -q
pixi run python -m pytest test/test_output_port_cache.py test/test_group_axis_potential_field.py test/test_group_distance_output_ports.py -q
pixi run python -m pytest test/test_bonsai_analysis_plane.py test/test_blender_analysis_ui.py test/test_blender_analysis_runtime.py -q
pixi run python -m pytest test/test_blender_analysis_capture.py test/test_blender_analysis_session.py test/test_free_space_evidence_package.py -q
```

The final report must distinguish tests actually run from native/real-IFC
checks not run. No completion claim is valid without fresh command output.
