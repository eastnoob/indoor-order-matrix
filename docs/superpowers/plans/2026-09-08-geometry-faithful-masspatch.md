# Geometry-Faithful MassPatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or the approved subagent-driven workflow) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve meaningful MassPatch empty space and correct generated cuboid normals while keeping conservative exact fallback behavior.

**Architecture:** Closed/manifold source geometry uses the existing occupancy-grid and greedy cuboid decomposition as the primary collection candidate. Open or mixed topology keeps the existing componentwise envelope path. The existing hard validators decide whether a simplified collection can replace exact source components.

**Tech Stack:** Python 3.12, Pixi, NumPy, trimesh, Shapely, pytest, jj.

**Spec:** `docs/superpowers/specs/2026-09-08-geometry-faithful-masspatch-design.md`

## Global Constraints

- Use Pixi only.
- Use jj for checkpoints.
- Do not add dependencies.
- Do not add a new substitute type.
- Do not touch BIM, Rhino UI, Blender UI, or IFC persistence.
- Open and mixed topology must remain explicitly uncertain.
- Every new or modified project-owned function must have an English-first docstring.
- Important geometry and selection blocks need English-first intent comments.
- Do not snapshot generated JSON artifacts larger than 1 MiB.

---

### Task 1: Lock the geometry regressions with failing tests

**Files:**
- Modify: `test/test_mass_patch_cuboid_cover.py`
- Modify: `test/test_mass_patch_generation.py`

**Interfaces:**
- Consumes: `cuboid_collection_from_mesh()`, `cuboid_from_grid_bounds()`,
  `_box_patch_from_coordinates()`, and `generate_mass_patches()`.
- Produces: regression tests proving ring openings and outward winding.

- [ ] Add a test that `cuboid_collection_from_mesh(_hollow_frame_mesh())`
  returns more than one patch and leaves `(2.0, 2.0, 0.5)` without vertical
  occupancy.
- [ ] Add a signed-volume helper in the test module and assert that both
  `cuboid_from_grid_bounds()` and `split_cuboid_patch()` produce positive
  volume.
- [ ] Run:

```text
pixi run pytest test/test_mass_patch_cuboid_cover.py::test_hollow_frame_collection_preserves_center_opening test/test_mass_patch_generation.py::test_generated_cuboids_have_outward_winding -q
```

- [ ] Confirm the new tests fail for the current implementation: the ring is
  currently returned as one filled component AABB and the signed volume is
  negative.
- [ ] Grill Me check: the tests observe user-visible geometry facts, not
  implementation branch names. If either test passes before production edits,
  strengthen the fixture/assertion rather than weakening the requirement.

### Task 2: Make closed-source cuboid collection occupancy-first

**Files:**
- Modify: `features/mass_patch_cuboid_cover.py`
- Modify: `test/test_mass_patch_cuboid_cover.py`

**Interfaces:**
- Consumes: `build_upright_occupancy()`,
  `greedy_cuboid_cover()`, and existing component AABB fallback.
- Produces: `cuboid_collection_from_mesh(mesh, config) -> tuple[MassPatch, ...]`
  that preserves closed-source empty cells.

- [ ] Change `cuboid_collection_from_mesh()` so a source that is explicitly
  closed and manifold first builds occupancy and returns its greedy cuboid
  cover when non-empty.
- [ ] Keep component AABB candidates only for uncertain open or mixed topology.
- [ ] Preserve deterministic ordering and the existing `max_patches` limit.
- [ ] Derive a component-scale pitch bounded by the parent pitch so small
  closed parts retain openings without forcing the whole logical object to use
  a fine grid.
- [ ] Add an English intent comment explaining why empty cells are retained
  before decomposition.
- [ ] Run the focused cuboid-cover tests and verify the ring and chair-gap
  tests pass.
- [ ] Grill Me check:
  - A connected ring is decomposed from occupied cells, not enveloped.
  - A solid box still collapses to one cuboid.
  - A chair's floor gap stays empty.
  - Open-top input still uses conservative component envelopes.

### Task 3: Correct shared cuboid winding

**Files:**
- Modify: `features/mass_patch_cuboid_cover.py`
- Modify: `test/test_mass_patch_generation.py`

**Interfaces:**
- Consumes: `_box_patch_from_coordinates()` and
  `cuboid_from_grid_bounds()`.
- Produces: outward-facing closed cuboids with positive signed volume.

- [ ] Reverse only the face winding needed by the two shared cuboid factories.
- [ ] Keep vertex coordinates, ids, bounds, provenance, and patch topology
  unchanged.
- [ ] Run the focused winding test and all cuboid-cover tests.
- [ ] Grill Me check: the fix is centralized in the shared constructors, so
  split patches and occupancy patches receive the same orientation without
  caller-specific branches.

### Task 4: Route production generation through the corrected candidate path

**Files:**
- Modify: `features/mass_patch_generation.py`
- Modify: `test/test_mass_patch_generation.py`
- Modify: `test/test_open_mass_patch_generation.py`

**Interfaces:**
- Consumes: corrected `cuboid_collection_from_mesh()`.
- Produces: validated `MassPatchGenerationResult` selection behavior.

- [ ] Run the hollow-frame, chair-gap, sloped, open-top, and mixed-topology
  tests against the changed candidate path.
- [ ] If a closed collection is rejected because the current validator samples
  insufficiently, add only the smallest source-driven sampling adjustment
  needed to measure the opening; do not add a ring-specific branch.
- [ ] When a closed occupancy collection passes validation, select it as the
  MassPatch proxy even if its raw triangle count exceeds the exact source
  component; exact source geometry is the fallback, not a competing cuboid
  candidate.
- [ ] Keep open-envelope selection labeled `open_envelope_collection` and
  preserve `open_envelope_uncertain`.
- [ ] Preserve a rejected open-envelope report, including its hard rejection
  reason, when exact components remain selected.
- [ ] Add or update one focused assertion that a rejected simplified
  collection leaves `selected_collection_method="componentwise"` or exact
  component output.
- [ ] Grill Me check: no candidate can replace exact geometry unless hard
  plan, height, and occlusion checks accept it.

### Task 5: Verification, documentation, and jj checkpoint

**Files:**
- Modify: `docs/superpowers/specs/2026-09-08-geometry-faithful-masspatch-design.md`
- Modify: `docs/superpowers/plans/2026-09-08-geometry-faithful-masspatch.md`

- [ ] Run focused tests:

```text
pixi run pytest test/test_mass_patch_cuboid_cover.py test/test_mass_patch_generation.py test/test_open_mass_patch_generation.py -q
```

- [ ] Run related geometry and boundary tests:

```text
pixi run pytest test/test_boundary_evidence.py test/test_geometry_views.py test/test_mass_patch_collection.py -q
```

- [ ] Run the full suite:

```text
pixi run pytest -q
```

- [ ] Run syntax and whitespace checks:

```text
pixi run python -m compileall -q features test
jj diff --check
```

- [ ] Audit every modified project-owned function for an English-first
  docstring and every non-obvious geometry/selection block for an intent
  comment.
- [ ] Run the Rhino live MassPatch test against slot `aardvark`, port
  `10501`, replacing only the `OM_MassPatch_Live` layer after code tests pass.
- [ ] Inspect the live result for preserved ring openings and normal direction.
- [ ] Create a jj checkpoint only after all evidence is green; do not include
  generated JSON files above the repository snapshot size limit.
- [ ] Final Grill Me check: report any remaining limitation explicitly, and do
  not claim full completion if Rhino MCP execution or visual inspection was
  unavailable.

## Deliberate Scope Boundary

This plan does not add rotated cuboid chains, convex-hull substitutes,
semantic furniture templates, or a new empty-space object type. Those are not
needed to fix the current filled-ring and reversed-normal failures and would
weaken the geometry-only contract.
