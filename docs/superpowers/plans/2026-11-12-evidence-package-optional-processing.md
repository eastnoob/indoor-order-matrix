# Evidence Package Optional Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Maintain this checklist during execution; the parent owner alone writes jj history.

**Goal:** Preserve every existing raw publication and add a default-disabled, package-specific processed output port with an explicit missing-function marker.

**Architecture:** Keep `EvidencePackage.evaluate()` and `EvidencePackageOutput` unchanged. A keyword-only optional processor consumes an already published raw output, returns separately validated channels, and has a separate processing identity. No formula or new persistent cache is introduced.

**Tech Stack:** Python 3.12, frozen dataclasses, existing field-core contracts, Pixi/pytest, jj workspace.

**Spec:** [Existing minimum standard](../specs/2026-10-30-evidence-package-minimal-standard.md), especially the user-confirmed optional processing boundary dated 2026-11-12; [package structure](../../project/evidence/evidence-package-structure.md).

## Global Constraints

- Inputs, calculation callbacks, algorithms, raw cache structure, units, statuses, provenance, historical output identities and JSON v1 remain compatible.
- No configured processor means `OUTPUT_FUNCTION_NOT_CONFIGURED`, empty processed channels, no identity callback or raw fallback.
- Configured callback failure is `OUTPUT_PROCESSING_FAILED`; stale/unavailable source is `OUTPUT_SOURCE_NOT_FRESH`. Neither exposes processed observations.
- No normalization, size weighting, exponent 0.6, potential integration, registry, scheduler, dependency or geometry changes.
- Workspace: `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/group-distance-decay`; workspace name `group-distance-decay`; base `prmxwzvo / 3c91eb4f4f5d`; initial empty change `yoorwylwrppv / 6dd7c1d8d449`; bookmark `codex/group-distance-decay`.
- Parent chat `01a17389-9f50-7700-a8d7-c2e0ad7b3d09` is the sole version writer. No child snapshot/new/describe/commit/bookmark/rebase/push/merge; preserve all other worklines.
- Every new or modified function has an English-first docstring. Use Pixi, not pip/venv.
- Visual: omitted. Channel routing, status gates, immutable values, identities and saved readback are directly testable; geometry and spatial results do not change.

## Task 1: Shared optional processing boundary and factory connections

**Files:**
- Modify `features/field_core.py`.
- Modify `features/free_space_evidence_package.py`, `features/group_distance_evidence_package.py`, `features/group_axis_potential_field.py` only to forward the optional processor, including both potential branches.
- Create `test/test_evidence_package_processing.py`; reuse existing contract fixture patterns.
- Update the existing minimum standard, package structure, software architecture, design index and a short architecture-memory entry. The coordinator owns prose; the implementer owns Python files.

**Interfaces:**

```python
EvidenceOutputProcessor(function_id, version, function, parameters={})
# function(raw_output: EvidencePackageOutput,
#          parameters: Mapping[str, Any]) -> Iterable[EvidenceOutputChannel]

EvidencePackage(..., *, output_processor: EvidenceOutputProcessor | None = None)
EvidencePackage.process_output(raw_output, *, package_freshness="unavailable")
# -> EvidenceProcessedOutput

EvidenceProcessedOutput(
    package_id, raw_output_identity, raw_payload_fingerprint,
    processor_id, processor_version, parameters, outputs,
    error_code, explanation="",
)
# .processing_identity distinguishes raw content, processor ID/version/parameters.

build_free_space_evidence_package(*, output_processor=None)
build_group_distance_evidence_package(*, output_processor=None)
build_group_axis_potential_package(*, scene_namespace=None, output_processor=None)
```

Reuse `EvidenceOutputChannel`, scale, statuses, canonical fingerprinting and `EvidencePackageChannelReference`. Each processed lineage reference must resolve against the exact supplied raw output, without inventing a second package or self-dependency. Validate raw package ID and legacy function ID/version before processing. Existing four/five-positional-argument construction remains valid.

- [x] Write behavior tests first and observe a meaningful failure before production edits. Start with the existing source-envelope helper pattern:

  ```python
  package = EvidencePackage("contract-package", "contract-output", "1", produce)
  raw = package.evaluate(sources)
  result = package.process_output(raw)
  assert result.error_code == "OUTPUT_FUNCTION_NOT_CONFIGURED"
  assert result.outputs == ()
  ```

- [x] Implement immutable processor configuration and separate result, then the method. Freeze JSON-compatible parameters; nonfinite values are rejected by existing validation. Missing processor takes priority over freshness. Configured stale/unavailable inputs skip the callback. A callback exception or invalid callback output yields the separate failure marker, with no channels or raw fallback.
- [x] Validate nonempty typed output channels, unique target/channel addresses and actual raw lineage. Referenced raw channels with no observation or status outside `computed`/`partial` cannot produce a usable observation; noncomputed references cannot be promoted to `computed`. Processed observations likewise require `computed`/`partial`. Respect declared scalar ranges without imposing a universal normalization range.
- [x] Fingerprint complete raw content plus processing ID/version/parameters separately; leave raw object, calculation identity and serialization unchanged. Runtime processing has no disk writer or new saved schema. Processed ports are not yet inputs to the historical cross-package resolver.
- [x] Forward processor configuration through three factories, with no default processor. No adapter/executor/export changes unless a concrete existing caller requires them.
- [x] Test missing/configured/failing/stale paths, callback call counts and no recomputation, different package processors, immutable parameters, recipe identity changes, raw-reading identity changes, malformed lineage/duplicates/nonfinite/range outputs and missing raw readings. Confirm raw serialization/identity unchanged for configured and unconfigured instances; preserve positional and context consumers.
- [x] Run implementer checks:

  ```powershell
  $env:PYTHONPATH='.'
  pixi run pytest test/test_evidence_package_processing.py -q
  pixi run pytest test/test_evidence_package_output.py test/test_field_core.py test/test_evidence_package_freshness.py test/test_evidence_package_readback.py test/test_group_distance_evidence_package.py -q
  ```

- [x] Complete documentation with the actual API and explicit runtime-only scope. Do not reopen historical rollout tasks or replace the existing standard.

## Task 2: Freeze, independent review and owner acceptance

**Consumes:** Actual Task 1 bytes and test logs, not an implementer's success assertion.
**Produces:** Hash-bound acceptance evidence, specification verdict, quality verdict and parent-owned local acceptance record.

- [x] Coordinator compares the implementation with every constraint and maintains this checklist. Inspect installed `jj` commands read-only, actual file bytes and touched callers. No local history write by this chat.
- [x] Freeze Python writers, record SHA-256 of every changed file and the diff; independent reviewer actually reruns the new behavior suite and explicitly returns specification and quality verdicts.
- [x] Resolve substantive findings, rerun affected checks and re-review changed bytes when necessary. No findings were reported, so no repair rerun was needed. Actual cwd, Pixi Python version, commands, exit codes, test totals, logs and candidate hashes are recorded below.
- [x] Freeze all writers after documentation and local review. Report all changed paths and exact hashes to parent through the candidate handoff manifest.
- [ ] Parent completes its assigned whole-candidate independent core regression and retained raw roundtrip, without duplicating the complete new suite.
- [ ] Parent checks accepted bytes and records the local jj checkpoint. This child stops writes at handoff, and does not claim acceptance/commit before parent records it. No push, merge or workspace deletion.

## Plan assessment and execution record

2026-11-12: User explicitly confirmed implementation and documentation. Parent confirmed the latest default-disabled template and selected the existing workline. Code inspection found the old `output_function` is required publication logic; disabling it would break every existing package. Its behavior therefore remains the raw port. Appending processed channels to old `.outputs` would change historical identities, so the new port has its own result.

Self-check: Task 1 covers both ports, defaults, errors, lineage/status/identity, factories, compatibility and docs. Task 2 consumes exactly those files/commands and owns freeze/review evidence. No unresolved formula or user decision is needed. The Bash SDD helper uses `git rev-parse` and would identify the outer checkout here; use the known `jj root` workspace and native plan-local scratch directory instead.

Implementation self-checks passed under Pixi Python 3.12.13, cwd equal to the workspace above. The initial red test failed for missing `process_output`; the final full preimplementation log records **55 failed / 1 passed** (the earlier progress message counted 53 before two additional cases). The output-status repair independently failed two cases before the fix. Final new suite: **58 passed**; the exact core command above: **165 passed**. All commands completed with exit code 0 on the passing runs.

The additional existing `test/test_free_space_evidence_package.py` suite passed **24 tests** with a temporary in-memory package alias. A direct combined run and the first alias attempt failed during collection because this hyphenated workspace makes existing `..adapters` imports resolve beyond top-level `test`; they did not report product test failures. No production/test runner configuration or source file was changed to hide this condition. Parent handoff includes the successful invocation and retained failure logs.

The successful alias invocation was (same workspace, exit 0):

```powershell
$env:PYTHONPATH='.'
@'
import importlib
import importlib.util
from pathlib import Path
import sys
import pytest

root = Path.cwd()
spec = importlib.util.spec_from_file_location('processing_candidate', root / '__init__.py', submodule_search_locations=[str(root)])
module = importlib.util.module_from_spec(spec)
sys.modules['processing_candidate'] = module
spec.loader.exec_module(module)
test_module = importlib.import_module('processing_candidate.test.test_free_space_evidence_package')
sys.modules['test.test_free_space_evidence_package'] = test_module
raise SystemExit(pytest.main(['--import-mode=importlib', 'test/test_free_space_evidence_package.py', '-q']))
'@ | pixi run python -
```

Plan-local scratch receipts are in `.superpowers/sdd/2026-11-12-evidence-package-optional-processing/`: `implementer-red.log`, `implementer-red-full.log`, `implementer-status-red.log`, `implementer-new-suite.log`, `implementer-core-regression.log`, `implementer-free-space-alias-regression.log` and `implementer-python-freeze.json`. The latter pins all five Python files and records that every function has a docstring. Owner acceptance remains unchecked until the parent records it.

Coordinator scope check: `source-compatibility.json` records 11 exact AST
preservation checks against base `3c91eb4f`: `EvidencePackageOutput`,
`EvidencePackage.evaluate`, raw serializer/deserializer, raw reader/resolver,
raw cache identity and freshness functions, plus all three package computation
callbacks are unchanged. `candidate.diff` records the 11 task-owned changed
paths from actual unsnapshotted bytes. Neither check writes jj history.

Independent task reviewer returned **SPEC PASS / QUALITY Approved, no
findings**. Its actual new-suite rerun passed **58 tests in 0.41s**, exit 0,
under the same cwd and Pixi Python 3.12.13. Additional assert probes passed for
deserialized-raw delivery without recomputation and for rejecting a partial
numeric output whose lineage includes a missing raw source. All five Python
hashes match before/after and the implementer freeze. See
`independent-review.md`, `reviewer-new-suite-result.json`,
`reviewer-one-off-probe.json` and `review-before.json` / `review-after.json` in
the scratch directory.

Final child handoff: all 11 task-owned Python/documentation paths and their
actual SHA-256 values are in `candidate-handoff.json` in that directory;
`candidate.diff` records their final bytes against base. All child writers are
stopped. Parent's independent verifier is running the core regression and real
retained raw roundtrip on the frozen Python hashes; parent alone records that
result and any accepted local jj checkpoint. This child has made no history
write and does not claim the parent acceptance is complete.

Limits: runtime processing uses caller-supplied freshness from the existing
contract check. No production processor/formula, processed persistence/cache
storage, processed cross-package routing, full-suite run or IFC/Blender
regeneration is included. The existing free-space test collection limitation
and all failure logs remain visible above.
