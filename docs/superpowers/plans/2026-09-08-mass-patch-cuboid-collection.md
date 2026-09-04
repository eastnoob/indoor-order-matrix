# MassPatch Cuboid Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Represent one complete logical object with the fewest safe upright cuboid `MassPatch` records that preserve its plan occupancy, height structure, important gaps, and basic occlusion behavior.

**Architecture:** Keep `MassPatch` as the only physical substitute record and keep `MassPatchGenerationResult.patches` as the public tuple. Add a small collection-query module for union semantics, then add a bounded 3D occupied-cell cover that proposes cuboids and validates the whole collection against the source. The existing exact mesh/component output remains the mandatory fallback.

**Tech Stack:** Python 3.12, Pixi, NumPy, existing Shapely and trimesh dependencies, pytest, and the existing Rhino read-only acceptance runner.

**Spec:** `docs/superpowers/specs/2026-09-08-mass-patch-cuboid-collection-design.md`

## Global Constraints

- Use Pixi only; do not create a pip/venv environment.
- Do not change `mass_patch_from_mesh()` behavior.
- Do not modify Rhino source geometry.
- Do not add a `ConvexHullPatch` type.
- Do not add perceptual weights to generation or validation.
- Do not require CoACD, V-HACD, NetworkX, or another new decomposition package.
- Use exact source geometry when simplification is uncertain or exceeds limits.
- Every new or modified project-owned function gets an English-first docstring.
- Important geometry, union, search, validation, and adapter blocks get English-first intent comments.
- Preserve unrelated dirty files and use `jj` checkpoints without absorbing unrelated artifacts.

---

### Task 1: Add collection-level union queries

**Files:**
- Create: `features/mass_patch_collection.py`
- Modify: `features/geometry_views.py` only when a shared low-level helper is clearly reusable
- Test: `test/test_mass_patch_collection.py`

**Interfaces:**
- `merge_vertical_intervals(intervals, tolerance=1e-9) -> tuple[tuple[float, float], ...]`
- `union_plan_geometry(patches, analysis_plane=None) -> object | None`
- `vertical_intervals_at_collection(patches, point, analysis_plane=None) -> VerticalIntervalResult`
- `collection_occludes(patches, query) -> bool`
- `collection_overlap_report(patches, tolerance=1e-9) -> dict[str, object]`

**Consumes:** Existing `MassPatch`, `plan_projection()`, `vertical_intervals_at()`, and `occlusion_intersections()`.

**Produces:** One source of truth for queries over multiple patches representing one logical object.

- [ ] **Step 1: Write the failing union tests.**

```python
def test_plan_union_counts_overlapping_boxes_once():
    patches = (_box_patch(0, 0, 2, 2), _box_patch(1, 0, 3, 2))
    assert union_plan_geometry(patches).area == 6.0


def test_height_union_merges_overlapping_intervals():
    assert merge_vertical_intervals(((0.0, 1.0), (0.8, 2.0))) == ((0.0, 2.0),)


def test_collection_occlusion_is_boolean():
    patches = (_box_patch(0, 0, 2, 2), _box_patch(1, 0, 3, 2))
    assert collection_occludes(patches, {"point": (1.5, 1.0)}) is True
```

- [ ] **Step 2: Run the focused tests and confirm RED.**

Run: `pixi run pytest test/test_mass_patch_collection.py -q`

Expected: import or missing-function failures because the collection module is not implemented.

- [ ] **Step 3: Implement plan union and interval merging.**

Project each patch with `plan_projection()`, convert its component rings to
Shapely polygons, and call `unary_union()`. Sort intervals by lower endpoint
and merge touching intervals within tolerance. The comments must explain that
seat/back overlap is one physical occupancy fact, not two areas or two height
bands.

- [ ] **Step 4: Implement collection height and occlusion queries.**

Use patch bounds as a broad-phase filter, query only patches that can contain
the plan point, merge their intervals, and short-circuit occlusion after the
first positive hit. Preserve uncertainty records from open or non-manifold
patches; do not turn uncertainty into a false negative.

- [ ] **Step 5: Implement overlap diagnostics and run the tests.**

Report pair count, pairwise overlap area/volume proxies, union area/volume
proxies, and overlap ratios separately from occupancy. Run:
`pixi run pytest test/test_mass_patch_collection.py -q`

- [ ] **Step 6: Review comments/docstrings and create a `jj` checkpoint.**

Run `jj diff --check`, inspect only touched files, then create a checkpoint
with `jj describe -m "feat: add MassPatch collection query semantics"` only if
the current dirty state can be described without capturing unrelated work.

---

### Task 2: Build a bounded upright occupancy grid

**Files:**
- Create: `features/mass_patch_cuboid_cover.py`
- Test: `test/test_mass_patch_cuboid_cover.py`

**Interfaces:**
- `CuboidCoverConfig`
- `OccupancyGrid3D`
- `build_upright_occupancy(mesh, config) -> OccupancyGrid3D`
- `cuboid_from_grid_bounds(grid, bounds) -> MassPatch`

**Consumes:** Complete `MeshGeometry3D`, source topology flags, and explicit generation tolerances.

**Produces:** Deterministic occupied/empty cells in a frame where Z remains vertical and candidate boxes can be reconstructed.

- [ ] **Step 1: Write failing grid tests.**

```python
def test_box_occupancy_has_no_empty_interior_cells():
    grid = build_upright_occupancy(_box_mesh(), CuboidCoverConfig(pitch=0.25))
    assert grid.occupied_count > 0
    assert grid.empty_count == 0


def test_hollow_source_retains_an_empty_center():
    grid = build_upright_occupancy(_hollow_frame_mesh(), CuboidCoverConfig(pitch=0.25))
    assert grid.is_occupied((2.0, 2.0, 0.5)) is False
```

- [ ] **Step 2: Run the focused tests and confirm RED.**

Run: `pixi run pytest test/test_mass_patch_cuboid_cover.py -q`

- [ ] **Step 3: Implement frame and pitch validation.**

Keep the supplied analysis-plane horizontal basis when present. Otherwise use
world Z as vertical and a deterministic plan yaw only when the generator
already has an object-local frame contract. Never let PCA tilt the vertical
axis. Require a finite positive pitch; if it is omitted, derive a bounded
pitch from `linear_tolerance` and source extent, with a maximum cell budget.

- [ ] **Step 4: Implement occupancy sampling.**

For closed, manifold sources, use the existing trimesh dependency to sample
cell centers and classify them with a conservative surface/solid test. Keep
empty cells so chair-leg gaps, hollow frames, and seat/back separation survive.
For open or non-manifold sources, mark the grid uncertain and return no
simplified cover; do not silently fill the volume.

- [ ] **Step 5: Implement deterministic grid-to-box conversion.**

Convert inclusive integer cell bounds to one closed upright box mesh in source
coordinates. Store frame, pitch, grid bounds, and source id in provenance so a
candidate can be audited without re-running the sampler.

- [ ] **Step 6: Run tests and perform the comment audit.**

Run: `pixi run pytest test/test_mass_patch_cuboid_cover.py -q`

Confirm every new function has a docstring and the occupancy/classification
blocks explain why empty cells are retained.

---

### Task 3: Extract and rank a low-count cuboid cover

**Files:**
- Modify: `features/mass_patch_cuboid_cover.py`
- Test: `test/test_mass_patch_cuboid_cover.py`

**Interfaces:**
- `maximal_upright_cuboid_candidates(grid, config) -> tuple[MassPatch, ...]`
- `greedy_cuboid_cover(grid, config) -> tuple[MassPatch, ...]`
- `cuboid_collection_from_mesh(mesh, config) -> tuple[MassPatch, ...]`

**Consumes:** `OccupancyGrid3D` from Task 2.

**Produces:** A deterministic initial collection of boxes with no furniture-specific templates.

- [ ] **Step 1: Write failing cover tests.**

```python
def test_box_source_produces_one_box():
    patches = cuboid_collection_from_mesh(_box_mesh(), CuboidCoverConfig(pitch=0.25))
    assert len(patches) == 1


def test_separated_parts_do_not_get_a_bridge_box():
    patches = cuboid_collection_from_mesh(_two_disconnected_boxes(), CuboidCoverConfig(pitch=0.25))
    assert len(patches) >= 2


def test_chair_cover_preserves_the_center_gap():
    patches = cuboid_collection_from_mesh(_chair_mesh(), CuboidCoverConfig(pitch=0.1))
    assert all(not _covers_plan_point(patch, (1.0, 1.0)) for patch in patches)
```

- [ ] **Step 2: Run the tests and confirm RED.**

Run: `pixi run pytest test/test_mass_patch_cuboid_cover.py -q`

- [ ] **Step 3: Enumerate maximal candidate boxes.**

Enumerate occupied seeds and grow axis-aligned integer bounds through contiguous
occupied runs in X, Y, and Z. Reject candidates with empty cells, disconnected
components, or a cell budget above the configured limit. Candidates may
overlap, but the ranking penalizes redundant covered cells so overlap is used
only where it preserves a real joint such as seat/back contact.

- [ ] **Step 4: Implement greedy selection.**

Maintain uncovered occupied cells. Select the candidate with the lexicographic
key `(newly_covered_cells, false_positive_cells negated, volume, -x, -y, -z)`.
After selection, remove only newly covered source cells; keep candidate
geometry unchanged. Stop when all required occupied cells are covered or the
candidate/patch budget is reached.

- [ ] **Step 5: Implement minimal local refinement.**

Try adjacent-pair merges in deterministic id order. Keep a merge only when it
does not introduce empty cells in the sampled grid and the resulting union
still passes later source validation. Do not add a general combinatorial
optimizer; the greedy cover plus bounded pair merges is the intentional
approximation.

- [ ] **Step 6: Run focused tests and verify deterministic output.**

Run: `pixi run pytest test/test_mass_patch_cuboid_cover.py -q`

Generate the same source twice and compare patch vertices, indices, ids, and
provenance byte-for-byte.

---

### Task 4: Validate collections and refine by split/fallback

**Files:**
- Modify: `features/mass_patch_generation.py`
- Modify: `features/mass_patch_cuboid_cover.py`
- Test: `test/test_mass_patch_generation.py`

**Interfaces:**
- `MassPatchCollectionCandidateReport`
- `validate_mass_patch_collection_candidate(source, candidates, config) -> MassPatchCollectionCandidateReport`
- `refine_cuboid_collection(source, candidates, config) -> tuple[MassPatch, ...] | None`

**Consumes:** Collection queries from Task 1 and cover candidates from Task 3.

**Produces:** An accepted low-count collection or an explicit exact fallback.

- [ ] **Step 1: Write failing collection validation tests.**

```python
def test_overlapping_seat_and_back_boxes_are_validated_as_one_collection():
    report = validate_mass_patch_collection_candidate(
        _chair_mesh(), _seat_back_candidates(), MassPatchGenerationConfig()
    )
    assert report.union_overlap_ratio >= 0.0
    assert report.plan_overreach <= 0.02


def test_enclosing_box_that_fills_leg_gap_is_rejected():
    report = validate_mass_patch_collection_candidate(
        _chair_mesh(), (_enclosing_box_patch(),), MassPatchGenerationConfig()
    )
    assert report.accepted is False
    assert report.rejection_reason in {"plan_overreach", "height_profile", "occlusion_disagreement"}
```

- [ ] **Step 2: Run tests and confirm RED.**

Run: `pixi run pytest test/test_mass_patch_generation.py -q`

- [ ] **Step 3: Implement collection-state comparison.**

Sample source and candidate plan points from both geometry envelopes plus a
bounded interior grid. Compute plan recall/overreach from union occupancy,
height error from merged intervals, gap preservation from empty source samples,
and occlusion disagreement from boolean collection ray queries. Keep these as
hard geometric tolerances, not weighted scores.

- [ ] **Step 4: Implement candidate selection and pair merges.**

Reject candidates violating any hard tolerance. Among feasible collections,
choose lexicographically by patch count, plan/height/occlusion error,
triangle/vertex complexity, and deterministic ids. Preserve overlap diagnostics
separately from the selection key.

- [ ] **Step 5: Implement bounded split refinement.**

When a candidate fails, find the first deterministic sample with disagreement,
split the responsible box along each eligible local axis, and retain only
splits that reduce the failing error. Stop after a fixed number of refinement
rounds or when no split improves the report; then return `None` so the caller
uses exact source geometry.

- [ ] **Step 6: Integrate full logical-object generation.**

Change `generate_mass_patches()` to build exact component patches first, run
the collection cover over the complete source mesh, and select the accepted
collection as one logical result. Keep component identities in provenance and
reports. If the source is uncertain or the cover is rejected, return the
existing exact component tuple unchanged.

- [ ] **Step 7: Run focused regression tests.**

Run:
`pixi run pytest test/test_mass_patch_collection.py test/test_mass_patch_cuboid_cover.py test/test_mass_patch_generation.py -q`

---

### Task 5: Route existing consumers through collection semantics

**Files:**
- Modify: `features/boundary_evidence.py`
- Modify: `features/neutral_scene_views.py`
- Modify: `features/scene_evaluator.py` only at callers that aggregate one logical object's patches
- Test: `test/test_boundary_evidence.py`
- Test: `test/test_geometry_views.py`

**Interfaces:** Existing public signatures remain compatible; collection-aware behavior is internal or optional.

**Consumes:** The shared collection query functions from Task 1.

**Produces:** No double-counting of one logical object's overlapping patches in downstream evidence.

- [ ] **Step 1: Add overlap regressions.**

Test one logical object with overlapping patches for plan area, height
intervals, path overlap, and visibility. Assert that single-patch behavior is
unchanged.

- [ ] **Step 2: Replace duplicated multi-patch aggregation.**

Use plan union for 2D area/path consumers, merged intervals for height
consumers, and boolean OR for occlusion consumers. Keep pairwise overlap data
as diagnostics rather than adding it to occupancy.

- [ ] **Step 3: Run the spatial suite.**

Run:
`pixi run pytest test/test_boundary_evidence.py test/test_geometry_views.py test/test_scene_inference.py -q`

- [ ] **Step 4: Audit docstrings/comments and create a `jj` checkpoint.**

Run `jj diff --check` and record a checkpoint only after the focused suite is green.

---

### Task 6: Live Rhino acceptance and visual verification

**Files:**
- Modify: `test/bim/run_live_mass_patch_generation.py`
- Modify: `test/test_live_mass_patch_generation.py`
- Modify or create: `test/output/mass_patch_generation_live.ipynb`
- Create: `test/output/mass_patch_cuboid_collection_live.json`
- Create: `test/output/mass_patch_cuboid_collection_live.png`

**Interfaces:** The read-only runner continues to use Rhino MCP port `10500`, slot `aardvark`.

**Consumes:** Accepted collection output from `generate_mass_patches()`.

**Produces:** A reproducible live acceptance artifact and visual comparison.

- [ ] **Step 1: Assert source immutability.**

Digest the extracted source before and after generation and assert that the
source record is unchanged. Keep extraction and generation separate.

- [ ] **Step 2: Run table, chair_1, and chair_2 through the generator.**

Record selected method, patch count, collection overlap report, validation
errors, and exact-fallback reason in JSON.

- [ ] **Step 3: Update the notebook visualization.**

Show source geometry and generated cuboids together, with compact labels and a
small table outside the drawing. Do not render a convex hull as physical mass.

- [ ] **Step 4: Inspect the rendered image.**

Confirm the table uses a few boxes, chair seat/back/legs do not become one
filled bridge box, and overlapping boxes do not create duplicate occupancy in
the reported union.

- [ ] **Step 5: Run the live test and save the checkpoint.**

Run the existing Pixi live test command and save a `jj` checkpoint after the
artifact and source immutability assertions pass.

---

### Task 7: Full verification and delivery gate

**Files:**
- Modify: `docs/superpowers/notes/2026-09-08-mass-patch-collection-overlap-defense.md`
- Modify: `docs/superpowers/specs/2026-09-08-mass-patch-cuboid-collection-design.md` only if an implementation detail changes the public contract
- Modify: `docs/indoor_layout_evaluation_matrix_architecture_memory.md` only if the final public contract changes

- [ ] **Step 1: Run the complete test suite.**

Run: `pixi run pytest -q`

Expected: existing tests pass, with only already-known skips.

- [ ] **Step 2: Run the comment/docstring audit.**

Inspect every new or modified project-owned function and every non-trivial
geometry block for English-first documentation and intent comments.

- [ ] **Step 3: Verify deterministic repeated outputs.**

Run synthetic and live generation twice and compare serialized patch ids,
vertices, reports, and provenance.

- [ ] **Step 4: Review the final diff.**

Run `jj diff --stat`, `jj diff --check`, and inspect only the intended files.
Leave unrelated oversized artifacts untouched.

- [ ] **Step 5: Record the final `jj` checkpoint.**

Use `jj describe -m "feat: add validated low-count MassPatch cuboid collections"` only when the working-copy diff contains only this feature's changes.
