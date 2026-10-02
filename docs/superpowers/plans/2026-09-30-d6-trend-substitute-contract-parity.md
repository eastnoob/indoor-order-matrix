# D6 Trend Substitute Contract and Legacy Parity Design Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to execute this plan task-by-task. This plan is design-only and must stop at the owner review gate.

**Goal:** Establish one auditable, function-specific substitute registry, complete typed provenance for the trend probe, and directly compare the new trend estimands with the existing legacy group-frame implementation using the same Analysis geometry.

**Architecture:** Keep the registry and parity runner under `scripts/design/group_level/`; do not change production adapters, features, public APIs, or NeutralSceneV2. The registry separates stable semantic keys from editable display labels. The parity runner consumes the same typed Analysis substitute records for A/C/D and calls the existing `_furniture_group_frame` only as a read-only legacy comparator. Blender renders the saved comparison JSON and never recomputes metrics.

**Tech Stack:** Pixi Python 3.12, existing project geometry code, existing IFC extraction path, portable Blender 5.2 LTS, JSON manifests, deterministic fixtures, pytest.

**Spec:** `docs/project/evidence/d6-trend-direction-design-probe.md`, `docs/project/d6-group-level-self-description-design.md`, `docs/project/d6-overall-self-description-design-table.md`, `docs/project/d6-group-self-description-programming-prompt.md`, and `docs/project/evidence/d6-ifc-three-group-smoke-report.md`.

## Global Constraints

- This is a design-only checkpoint; do not modify `features/`, `adapters/`, `test/`, `NeutralSceneV2`, public APIs, dependencies, source IFC, or the user's open Blender/Bonsai model.
- Use only `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` and Pixi; do not install packages with pip or create a virtual environment.
- Trend calculations must consume typed Analysis substitutes; Body geometry is provenance/visual audit only and is never a fallback input.
- Do not select a production winner, default threshold, Bayesian prior, ML model, or psychological interpretation.
- Preserve all invalid, missing, partial, and not-available states; never repair holes or replace missing values with zero.
- Preserve existing untracked work. Never run `git add -A`, `git add .`, reset, clean, or revert unrelated files.
- New design scripts/functions require English-first docstrings and comments at important inference, geometry, provenance, and rendering boundaries.
- Large JSON, PNG, blend, and logs belong under `outputs/design/trend_substitute_contract_parity/`; do not auto-commit generated binaries.

## Review Focus

- A label or source name must never authorize a substitute; registry matching must require typed consumer/kind/role fields.
- One source object may have several function-specific substitutes; trend must accept only the trend contract.
- The direct legacy comparison must distinguish `_furniture_group_frame`'s final emitted result from its internal point-cloud PCA diagnostic.
- Analysis geometry, not Body geometry, must be identical across A/C/D and the legacy call.
- Real IFC coverage is a design sample, not a whole-model accuracy claim; skipped invalid groups remain visible.

### Task 1: Audit and freeze the design-only registry contract

**Files:**
- Create: `scripts/design/group_level/trend_substitute_registry.json`
- Create: `scripts/design/group_level/trend_substitute_registry.py`
- Create: `scripts/design/group_level/test_trend_substitute_registry.py`
- Create: `docs/project/evidence/d6-trend-substitute-registry-design.md`

**Interfaces:**
- `load_registry(path: Path) -> dict[str, object]`
- `resolve_contract(record: Mapping[str, object], consumer: str, registry: Mapping[str, object]) -> dict[str, object]`
- `display_spec(contract_key: str, registry: Mapping[str, object]) -> dict[str, object]`

- [ ] Define registry schema `d6-trend-substitute-registry/v1` with stable `contract_key`, `consumer`, accepted `substitute_kind`, accepted `analysis_role`, and editable display metadata. Include at minimum `trend_analysis`; reserve `clearance_analysis`, `path_analysis`, and `body_audit` only as explicit non-trend contracts if the existing evidence needs them.
- [ ] Keep instance identity out of the registry. Each instance must carry `substitute_id` and `source_object_id`; the registry only defines what a consumer accepts and how it is displayed.
- [ ] Make `resolve_contract` reject records missing `consumer`, `substitute_kind`, `analysis_role`, or `substitute_id`; reject Body-only records and label-only records; return an auditable rejection reason.
- [ ] Make display labels/colors/line styles independent from semantic matching so a label change cannot change computation.
- [ ] Add deterministic unit tests for accepted Analysis records, wrong consumer, wrong kind, wrong role, missing fields, duplicate instance IDs, and editable display labels.
- [ ] Record the contract boundary and the fact that this registry is design-only; it is not yet the production API.
- [ ] Run: `pixi run pytest scripts/design/group_level/test_trend_substitute_registry.py -q`.
- [ ] Commit only the explicitly listed design files if the execution workflow requires commits.

### Task 2: Rebuild the trend probe with typed Analysis provenance

**Files:**
- Modify: `scripts/design/group_level/run_trend_direction_probe.py`
- Modify or create: `scripts/design/group_level/trend_direction_fixtures.json`
- Modify or create: `scripts/design/group_level/trend_direction_truth.json`
- Create: `scripts/design/group_level/trend_substitute_contract_parity_fixtures.json`
- Create: `scripts/design/group_level/trend_substitute_contract_parity_truth.json`

**Interfaces:**
- `build_typed_substitute_record(...) -> dict[str, object]`
- `select_trend_analysis_geometry(...) -> dict[str, object]`

- [ ] Load the shared registry and attach a `contract_key` plus complete typed fields to every Analysis substitute record: `substitute_id`, `source_object_id`, `consumer`, `substitute_kind`, `analysis_role`, and provenance.
- [ ] Preserve raw IFC representation/property identifiers in provenance, including source IFC hash, representation identifier, extraction method, visibility policy, and world-transform application status.
- [ ] Do not infer semantic authorization from object names, `source_role`, display labels, or Body geometry.
- [ ] Keep exact `ObjectType == "furniture_group"` qualification and the existing deterministic selection policy. Inventory all 37 groups, select three complete Analysis groups for the smoke sample, and preserve every skipped invalid group and reason.
- [ ] Add negative fixtures for untyped Analysis, Body-only, wrong consumer, and duplicate substitute identity. These must be rejected or marked unavailable without silently falling back.
- [ ] Keep A, C, and D calculations unchanged in meaning; only their input binding and provenance are revised.
- [ ] Run the probe and assert source IFC hash before/after is unchanged.

### Task 3: Add direct legacy parity on the same typed Analysis input

**Files:**
- Modify: `scripts/design/group_level/run_trend_direction_probe.py`
- Create: `scripts/design/group_level/trend_substitute_contract_parity_report.py`
- Create: `docs/project/evidence/d6-trend-substitute-contract-parity.md`

**Interfaces:**
- `run_legacy_group_frame_parity(...) -> dict[str, object]`
- `compare_direction_records(...) -> dict[str, object]`

- [ ] Construct the exact legacy `members` and `extents` records from the same Analysis-derived planar geometry used by A/C/D.
- [ ] Call `features.scene_inference._furniture_group_frame` directly in the design runner without editing that function.
- [ ] Record separately: legacy final `angle`, `strength`, `basis`; legacy `geometry_angle`, `clarity`, and extents; the reconstructed B point-cloud inputs; and A/C/D results.
- [ ] Explicitly document that `_furniture_group_frame` returns `member_frame_consensus` when member support is positive and uses point-cloud PCA as fallback/diagnostic otherwise. Do not call this equality a validation of C.
- [ ] Compare angles with the correct equivalence: A frame uses modulo 90 degrees; legacy/B/C/D axes use modulo 180 degrees. Record near-boundary cases such as 89.987 degrees without silently rounding them into a different estimand.
- [ ] Add fixture assertions for: exact legacy parity on a legacy-shaped input, divergence between member orientation and placement, tessellation sensitivity of B, and no Body fallback.
- [ ] Keep A/C/D as distinct named estimands and leave `winner` null.

### Task 4: Render the comparison using registry display metadata

**Files:**
- Create or modify: `scripts/design/group_level/render_trend_substitute_contract_parity.py`
- Create: `docs/project/evidence/d6-trend-substitute-contract-parity-visual-manifest.json`

- [ ] Read only the saved parity JSON and registry; do not recompute angles or select a winner in Blender.
- [ ] Render synthetic and real-IFC panels showing Analysis footprints, area-weighted center, A/C/D/legacy vectors, contract labels, invalid/partial states, and provenance identifiers.
- [ ] Use color plus line style/label so the figure remains interpretable without color alone; avoid clipping and overlap.
- [ ] Save PNGs, one `.blend`, metadata, and hashes under `outputs/design/trend_substitute_contract_parity/`.
- [ ] Manually inspect both PNGs and record the inspection result in the manifest.

### Task 5: Verification and stop gate

- [ ] Run the registry tests, trend probe, parity report, Blender render, JSON/schema verification, manifest/hash verification, and `git diff --check`.
- [ ] Run focused regression tests: `pixi run pytest test/test_group_self_description.py test/test_blender_preview.py -q`.
- [ ] Audit staged scope explicitly; no production/API/adapter/NeutralSceneV2 changes are allowed.
- [ ] Produce a final report with sections: accepted evidence, provenance audit, legacy parity, real IFC coverage, visual audit, limitations, and owner decisions required.
- [ ] Stop exactly at `STOP FOR TREND ESTIMAND REVIEW`.

## Owner Decision After This Checkpoint

The execution agent must not decide these items:

1. Whether C becomes the formal overall furniture-group trend.
2. Whether A remains an independent member-orientation descriptor.
3. Whether D remains an independent placement/layout descriptor.
4. Whether B remains legacy diagnostic only.
5. Whether the registry is promoted from design-only scripts into a production shared module.

