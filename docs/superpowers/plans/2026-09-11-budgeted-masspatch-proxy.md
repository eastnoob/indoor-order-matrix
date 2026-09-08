# Budgeted MassPatch Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make high-face-count and parent-open meshes produce compact MassPatch proxies under finite budgets instead of copied source meshes.

**Architecture:** Keep `MeshGeometry3D` as the adapter-neutral input and `MassPatch` as the only physical substitute. Bound component sampling by parent pitch and patch budget, then allow uncertain open-envelope collections to be selected when they provide the only practical analysis proxy.

**Tech Stack:** Python 3.12, Pixi, NumPy, trimesh, Shapely, pytest, jj.

**Spec:** `docs/superpowers/specs/2026-09-11-budgeted-masspatch-proxy-design.md`

## Global Constraints

- Use Pixi only.
- Use jj for checkpoints.
- Do not add dependencies.
- Do not add a new substitute type.
- Do not add Rhino-specific branches.
- Exact source geometry remains audit baseline and emergency fallback.
- Every new or modified project-owned function must have an English-first docstring.
- Important geometry and selection blocks need English-first intent comments.

---

### Task 1: Lock compact fallback behavior for parent-open objects

**Files:**
- Modify: `test/test_open_mass_patch_generation.py`

**Interfaces:**
- Consumes: `generate_mass_patches(mesh: MeshGeometry3D, config: MassPatchGenerationConfig | None = None) -> MassPatchGenerationResult`
- Produces: a failing test that parent-open mixed objects select non-exact proxy patches.

- [ ] Add a test fixture with a closed box component and an open plate component under an open parent.
- [ ] Assert that final selected patch provenance methods contain no `exact_component` when conservative cuboid/envelope candidates are available.
- [ ] Run the test and confirm it fails because current behavior can keep exact fallback for parent-open components.

### Task 2: Bound component-level cuboid sampling

**Files:**
- Modify: `features/mass_patch_cuboid_cover.py`
- Modify: `test/test_mass_patch_cuboid_cover.py`

**Interfaces:**
- Consumes: `_component_cover_config(component: MeshGeometry3D, parent_config: CuboidCoverConfig) -> CuboidCoverConfig`
- Produces: component pitch that cannot shrink below a budgeted fraction of parent pitch.

- [ ] Add a test proving component pitch stays bounded for a large component with one tiny thickness.
- [ ] Add a minimum component pitch rule derived from parent pitch.
- [ ] Keep the existing cell-budget loop so very large components still stay finite.
- [ ] Run cuboid cover tests.

### Task 3: Prefer uncertain compact envelopes over exact display meshes for open components

**Files:**
- Modify: `features/mass_patch_generation.py`
- Modify: `test/test_open_mass_patch_generation.py`

**Interfaces:**
- Consumes: `validate_open_mass_patch_collection_candidate(...) -> MassPatchCollectionCandidateReport`
- Produces: selected `open_envelope_collection` patches with `open_envelope_uncertain` when exact geometry would otherwise be selected only because open topology cannot support closed-solid validation.

- [ ] Adjust open component selection so accepted open-envelope candidates replace `exact_component`.
- [ ] For parent-open logical objects, allow the final selected collection to be the union of component selected proxies.
- [ ] Preserve rejected collection reports when no compact proxy is safe.
- [ ] Run open/mixed topology tests.

### Task 4: Verify pre-Rhino readiness without mutating Rhino

**Files:**
- Modify only if test failures reveal a code issue.

**Interfaces:**
- Consumes: `test/bim/run_live_mass_patch_generation.py`
- Produces: a JSON summary from the existing read-only Rhino extraction.

- [ ] Run MassPatch focused tests.
- [ ] Run `pixi run python -m compileall -q features test`.
- [ ] Run `pixi run pytest -q`.
- [ ] Run the read-only Rhino JSON generator with a new output path under `outputs/rhino_mcp_live_2026-09-09/`.
- [ ] Inspect only the summary: source mutation check, patch count, selected methods, uncertainty tags, and runtime.
- [ ] Do not connect to Rhino or write `OM_MassPatch_Live` in this plan.

## Plan Self-Review

- Spec coverage: backend-only, single substitute type, budgeted sampling, open uncertainty, tests, and no Rhino mutation are each mapped to a task.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: all function names match the existing codebase.
