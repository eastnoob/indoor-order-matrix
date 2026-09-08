# Open Mesh MassPatch Substitutes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix MassPatch generation so mixed/open topology meshes produce auditable component topology and conservative envelope substitutes when safe.

**Architecture:** Keep MassPatch as the only substitute record. Fix topology at the component split source, add an open-envelope validation/report branch, then allow `generate_mass_patches()` to select componentwise envelope collections for uncertain meshes without changing closed-solid behavior.

**Tech Stack:** Python 3.12, Pixi, NumPy, trimesh, Shapely, pytest, jj.

**Spec:** `docs/superpowers/specs/2026-09-08-open-mesh-masspatch-substitutes-design.md`

## Global Constraints

- Use Pixi only.
- Use jj for checkpoints.
- Do not add dependencies.
- Do not add a new substitute type.
- Do not touch BIM, Rhino UI, Blender UI, or IFC persistence.
- Open geometry must be labeled uncertain and must not claim closed-solid occupancy truth.
- Every new or modified project-owned function must have an English-first docstring.
- Important geometry and selection blocks need English-first intent comments.

---

### Task 1: Prove and fix per-component topology

**Files:**
- Modify: `features/mass_patch_generation.py`
- Create: `test/test_open_mass_patch_generation.py`

**Interfaces:**
- Consumes: `_component_meshes(mesh, linear_tolerance)`
- Produces: component `MeshGeometry3D.is_closed` and `is_manifold` from each split component

- [x] Add a failing mixed-topology test.
- [x] Run it and confirm that every component inherits the parent uncertainty.
- [x] Change `_component_meshes()` to use each split component's topology, while preserving an explicit uncertain flag for a single-component source.
- [x] Re-run the focused tests.
- [x] Grill Me: the fix is at the shared split source, so component reports and collection validation receive the same corrected facts.

### Task 2: Add open-envelope acceptance

**Files:**
- Modify: `features/mass_patch_generation.py`
- Modify: `test/test_open_mass_patch_generation.py`

**Interfaces:**
- Produces: `validate_open_mass_patch_collection_candidate(source, candidates, config)`
- Produces: `selected_collection_method="open_envelope_collection"`

- [x] Add a failing open-mesh selection test.
- [x] Run it and confirm current behavior falls back to exact/topology uncertainty.
- [x] Implement plan-envelope validation that skips closed-solid height and occlusion claims and records `open_envelope_uncertain`.
- [x] Let `generate_mass_patches()` try component AABB candidates for uncertain sources.
- [x] Verify uncertainty reaches both the collection report and selected patch provenance.
- [x] Grill Me: candidates remain componentwise, so the branch cannot replace a multi-part chair with one whole-object box.

### Task 3: Regression and documentation gate

**Files:**
- Modify: `docs/superpowers/specs/2026-09-08-open-mesh-masspatch-substitutes-design.md`
- Modify: `docs/superpowers/plans/2026-09-08-open-mesh-masspatch-substitutes.md`

- [x] Run `pixi run pytest test/test_open_mass_patch_generation.py test/test_mass_patch_generation.py test/test_mass_patch_cuboid_cover.py test/test_mass_patch_collection.py -q`.
- [x] Run `pixi run pytest test/test_boundary_evidence.py test/test_geometry_views.py -q`.
- [x] Run `pixi run python -m compileall -q features test/test_open_mass_patch_generation.py`.
- [x] Run `git diff --check`.
- [x] Run `pixi run pytest -q`.
- [x] Audit the final diff and create the jj checkpoint after the full suite passes.
- [x] Grill Me: no completion claim until the full suite and final diff audit are green.

## Deliberate Scope Boundary

This change fixes open/mixed topology handling and componentwise conservative envelopes. Curved or bent single components that need segmented cuboid chains remain a separate change with dedicated fixtures; silently adding a heuristic here would weaken the current acceptance guarantees.
